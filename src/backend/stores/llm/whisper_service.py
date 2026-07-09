"""
Whisper Service — Local Model Singleton

Handles real-time audio transcription and Arabic/English → English translation
using a local HuggingFace Whisper model loaded once at startup.

Mirrors talent-acquisition-agent/src/services/local_whisper_service.py:
- ffmpeg -i pipe:0 (auto-detect format; no byte-concatenation of chunks)
- Session buffer for deduplication only
- Tempfile fallback when pipe decode fails (extension hint, no forced -f)

Environment variables:
    WHISPER_MODEL_NAME   — HuggingFace model ID or local path (default: openai/whisper-small)
    WHISPER_DEVICE       — "cuda" or "cpu" (default: auto-detect)
    FFMPEG_PATH          — Path to ffmpeg binary (default: ffmpeg on PATH)
"""

import hashlib
import logging
import os
import shutil
import subprocess
import tempfile
from collections import deque

import numpy as np
import torch
from transformers import WhisperForConditionalGeneration, WhisperProcessor

logger = logging.getLogger(__name__)

# ── Configuration ─────────────────────────────────────────────────────────────
MODEL_NAME = os.getenv("WHISPER_MODEL_NAME", "openai/whisper-small")
DEVICE     = os.getenv("WHISPER_DEVICE", "cuda" if torch.cuda.is_available() else "cpu")
FFMPEG_BIN = os.getenv("FFMPEG_PATH", "ffmpeg")

OVERLAP_BUFFER_SIZE = 2

_CHUNK_SAMPLES  = 25 * 16000
_STRIDE_SAMPLES = 2 * 16000

_FORMAT_EXTENSIONS = {
    "webm": ".webm",
    "ogg":  ".ogg",
    "mp4":  ".mp4",
    "wav":  ".wav",
    "mp3":  ".mp3",
}

# ── Singleton state ───────────────────────────────────────────────────────────
_processor: WhisperProcessor | None = None
_model: WhisperForConditionalGeneration | None = None
_ffmpeg_path: str | None = None
_session_buffers: dict[str, deque] = {}


def _resolve_ffmpeg() -> str:
    global _ffmpeg_path
    if _ffmpeg_path:
        return _ffmpeg_path

    candidate = shutil.which(FFMPEG_BIN) or (
        FFMPEG_BIN if os.path.isfile(FFMPEG_BIN) else None
    )
    if not candidate:
        raise RuntimeError(
            "ffmpeg is required but not found. Install ffmpeg or set FFMPEG_PATH in .env"
        )
    _ffmpeg_path = candidate
    return _ffmpeg_path


def load_whisper() -> None:
    global _processor, _model

    if _processor is not None and _model is not None:
        return

    logger.info(f"[Whisper] Using ffmpeg at: {_resolve_ffmpeg()}")
    logger.info(f"[Whisper] Loading model '{MODEL_NAME}' on {DEVICE}...")
    _processor = WhisperProcessor.from_pretrained(MODEL_NAME)
    _model = WhisperForConditionalGeneration.from_pretrained(MODEL_NAME).to(DEVICE)
    _model.config.forced_decoder_ids = None
    logger.info(f"[Whisper] Model loaded successfully on {DEVICE}")


def unload_whisper() -> None:
    global _processor, _model
    if _model is not None:
        del _model
        _model = None
    if _processor is not None:
        del _processor
        _processor = None


def _get_processor() -> WhisperProcessor:
    if _processor is None:
        raise RuntimeError("[Whisper] Model not loaded — call load_whisper() first")
    return _processor


def _get_model() -> WhisperForConditionalGeneration:
    if _model is None:
        raise RuntimeError("[Whisper] Model not loaded — call load_whisper() first")
    return _model


def _chunk_hash(audio_data: bytes) -> str:
    return hashlib.md5(audio_data).hexdigest()


def _pcm_to_tensor(pcm_data: bytes) -> torch.Tensor:
    if not pcm_data:
        return torch.tensor([])
    audio_array = np.frombuffer(pcm_data, dtype=np.int16).astype(np.float32) / 32768.0
    return torch.from_numpy(audio_array).float()


def load_audio_from_bytes(audio_data: bytes, audio_format: str = "webm") -> torch.Tensor:
    """
    Decode audio bytes to a mono 16 kHz float32 tensor.

    Primary path matches the Talent reference: ffmpeg reads from stdin and
    auto-detects the container (WebM/WAV/OGG/MP4).

    If pipe decode fails, retry via a tempfile with the client format extension
    so ffmpeg can probe from the filename — never force-decode WebM as WAV.
    """
    if not audio_data:
        return torch.tensor([])

    ffmpeg = _resolve_ffmpeg()
    output_args = ["-f", "s16le", "-ac", "1", "-ar", "16000", "pipe:1"]
    errors: list[str] = []

    # ── Strategy 1: stdin pipe (Talent reference) ─────────────────────────────
    process = subprocess.Popen(
        [ffmpeg, "-i", "pipe:0", *output_args],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    pcm_data, stderr = process.communicate(input=audio_data)
    if process.returncode == 0 and pcm_data:
        return _pcm_to_tensor(pcm_data)
    if stderr:
        errors.append(f"pipe: {stderr.decode(errors='replace')[:300]}")

    # ── Strategy 2: tempfile with format extension (auto-detect) ────────────
    fmt = (audio_format or "webm").lower().lstrip(".")
    ext = _FORMAT_EXTENSIONS.get(fmt, ".webm")
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
            tmp.write(audio_data)
            tmp_path = tmp.name

        result = subprocess.run(
            [ffmpeg, "-y", "-i", tmp_path, *output_args],
            capture_output=True,
            check=False,
        )
        if result.returncode == 0 and result.stdout:
            return _pcm_to_tensor(result.stdout)
        if result.stderr:
            errors.append(f"file({ext}): {result.stderr.decode(errors='replace')[:300]}")
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)

    raise RuntimeError(
        f"ffmpeg decode failed ({len(audio_data)} bytes, fmt={fmt}): "
        + " | ".join(errors) or "unknown error"
    )


def _transcribe_tensor_chunk(chunk: torch.Tensor) -> str:
    processor = _get_processor()
    model     = _get_model()

    input_features = processor(
        chunk,
        sampling_rate=16000,
        return_tensors="pt",
    ).input_features.to(DEVICE)

    with torch.no_grad():
        forced_decoder_ids = processor.get_decoder_prompt_ids(
            language="english",
            task="translate",
        )
        predicted_ids = model.generate(
            input_features,
            forced_decoder_ids=forced_decoder_ids,
        )

    return processor.batch_decode(predicted_ids, skip_special_tokens=True)[0].strip()


def _transcribe_full_tensor(audio_tensor: torch.Tensor) -> str:
    total = audio_tensor.shape[0]
    if total <= _CHUNK_SAMPLES:
        return _transcribe_tensor_chunk(audio_tensor)

    parts: list[str] = []
    start = 0
    while start < total:
        end = min(start + _CHUNK_SAMPLES, total)
        text = _transcribe_tensor_chunk(audio_tensor[start:end])
        if text:
            parts.append(text)
        start += _CHUNK_SAMPLES - _STRIDE_SAMPLES

    return " ".join(parts)


async def transcribe_chunk(
    audio_data: bytes,
    session_id: str,
    audio_format: str = "webm",
) -> str:
    """
    Transcribe and translate one self-contained audio chunk to English.

    Each chunk is processed independently (no byte concatenation).
    """
    if not audio_data:
        return ""

    if session_id not in _session_buffers:
        _session_buffers[session_id] = deque(maxlen=OVERLAP_BUFFER_SIZE)

    buf = _session_buffers[session_id]
    chunk_hash = _chunk_hash(audio_data)

    if chunk_hash in {h for h, _ in buf}:
        logger.debug(f"[Whisper] Duplicate chunk skipped (session={session_id[:8]})")
        return ""

    try:
        audio_tensor = load_audio_from_bytes(audio_data, audio_format)
    except RuntimeError as exc:
        logger.warning(f"[Whisper] Audio decode failed (session={session_id[:8]}): {exc}")
        return ""

    # Record only after successful decode (allows format retries upstream)
    buf.append((chunk_hash, audio_data))

    if audio_tensor.numel() == 0:
        return ""

    try:
        text = _transcribe_full_tensor(audio_tensor)
    except Exception as exc:
        logger.warning(f"[Whisper] Transcription failed (session={session_id[:8]}): {exc}")
        return ""

    if text:
        logger.info(
            f"[Whisper] Transcribed (session={session_id[:8]}, fmt={audio_format}, "
            f"{len(audio_data)} bytes, {audio_tensor.shape[0] / 16000:.1f}s): {text[:80]}"
        )
    return text


def clear_session_buffer(session_id: str) -> None:
    _session_buffers.pop(session_id, None)
