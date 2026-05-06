"""
Whisper Service — Local Model Singleton

Handles real-time audio transcription and Arabic/English → English translation
using a local HuggingFace Whisper model loaded once at startup.

Adapted from the work project's local_whisper_service.py with:
- Proper async/await (no asyncio.run inside async context)
- Session buffer management for overlap handling
- Clean singleton pattern matching the rest of this codebase
- Graceful degradation on ffmpeg/model errors

Environment variables:
    WHISPER_MODEL_NAME   — HuggingFace model ID or local path (default: openai/whisper-small)
    WHISPER_DEVICE       — "cuda" or "cpu" (default: auto-detect)
"""

import hashlib
import logging
import os
import subprocess
from collections import deque

import numpy as np
import torch
from transformers import WhisperForConditionalGeneration, WhisperProcessor

logger = logging.getLogger(__name__)

# ── Configuration ─────────────────────────────────────────────────────────────
MODEL_NAME = os.getenv("WHISPER_MODEL_NAME", "openai/whisper-small")
DEVICE     = os.getenv("WHISPER_DEVICE", "cuda" if torch.cuda.is_available() else "cpu")

# How many previous audio chunks to prepend for overlap handling
# (reduces word cut-off at chunk boundaries)
OVERLAP_BUFFER_SIZE = 2

# ── Singleton state ───────────────────────────────────────────────────────────
_processor: WhisperProcessor | None = None
_model: WhisperForConditionalGeneration | None = None

# Per-session overlap buffers: session_id → deque of (hash, bytes)
_session_buffers: dict[str, deque] = {}


def load_whisper() -> None:
    """
    Load the Whisper model and processor into memory.
    Called once at application startup via the FastAPI lifespan.
    Subsequent calls are no-ops.
    """
    global _processor, _model

    if _processor is not None and _model is not None:
        logger.debug("[Whisper] Model already loaded — skipping")
        return

    logger.info(f"[Whisper] Loading model '{MODEL_NAME}' on {DEVICE}...")
    _processor = WhisperProcessor.from_pretrained(MODEL_NAME)
    _model = WhisperForConditionalGeneration.from_pretrained(MODEL_NAME).to(DEVICE)
    _model.config.forced_decoder_ids = None
    logger.info(f"[Whisper] ✅ Model loaded successfully on {DEVICE}")


def unload_whisper() -> None:
    """Release model from memory on shutdown."""
    global _processor, _model
    if _model is not None:
        del _model
        _model = None
    if _processor is not None:
        del _processor
        _processor = None
    logger.info("[Whisper] Model unloaded")


# ── Internal helpers ──────────────────────────────────────────────────────────

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


def _load_audio_tensor(audio_data: bytes) -> torch.Tensor:
    """
    Decode audio bytes (any format: webm, wav, mp3, ogg…) to a
    mono 16 kHz float32 tensor using ffmpeg.

    Raises:
        RuntimeError: if ffmpeg is not installed or conversion fails.
    """
    process = subprocess.Popen(
        [
            "ffmpeg",
            "-i", "pipe:0",
            "-f", "s16le",
            "-ac", "1",
            "-ar", "16000",
            "-loglevel", "quiet",
            "pipe:1",
        ],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    pcm_data, stderr = process.communicate(input=audio_data)

    if process.returncode != 0:
        raise RuntimeError(f"ffmpeg conversion failed: {stderr.decode()[:200]}")

    audio_array = np.frombuffer(pcm_data, dtype=np.int16).astype(np.float32) / 32768.0
    return torch.from_numpy(audio_array).float()


# ── Public API ────────────────────────────────────────────────────────────────

async def transcribe_chunk(
    audio_data: bytes,
    session_id: str,
    audio_format: str = "webm",
) -> str:
    """
    Transcribe and translate one audio chunk to English.

    Handles Arabic, English, and mixed-language audio by forcing
    Whisper into translate mode (always outputs English).

    Uses a per-session overlap buffer to prepend the last
    OVERLAP_BUFFER_SIZE chunks before the current one, reducing
    word cut-offs at chunk boundaries.  Duplicate chunks (same hash)
    are silently skipped.

    Args:
        audio_data:   Raw audio bytes (any format supported by ffmpeg).
        session_id:   Unique identifier for this interview session.
                      Used to maintain the overlap buffer.
        audio_format: Hint for logging only — ffmpeg auto-detects.

    Returns:
        Transcribed/translated text in English, or "" on empty/silent input.

    Raises:
        RuntimeError: if model not loaded or ffmpeg not available.
    """
    if not audio_data:
        return ""

    # ── Overlap buffer management ─────────────────────────────────────────────
    if session_id not in _session_buffers:
        _session_buffers[session_id] = deque(maxlen=OVERLAP_BUFFER_SIZE)

    buf = _session_buffers[session_id]
    chunk_hash = _chunk_hash(audio_data)

    # Skip exact duplicates (client may resend on reconnect)
    existing_hashes = {h for h, _ in buf}
    if chunk_hash in existing_hashes:
        logger.debug(f"[Whisper] Duplicate chunk skipped (session={session_id[:8]})")
        return ""

    # Build audio with overlap context
    buffered = b"".join(chunk for _, chunk in buf) + audio_data
    buf.append((chunk_hash, audio_data))

    # ── Audio → tensor ────────────────────────────────────────────────────────
    try:
        audio_tensor = _load_audio_tensor(buffered)
    except RuntimeError as exc:
        logger.warning(f"[Whisper] Audio decode failed (session={session_id[:8]}): {exc}")
        return ""

    if audio_tensor.numel() == 0:
        return ""

    # ── Inference ─────────────────────────────────────────────────────────────
    processor = _get_processor()
    model     = _get_model()

    input_features = processor(
        audio_tensor,
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

    text = processor.batch_decode(predicted_ids, skip_special_tokens=True)[0].strip()
    logger.debug(f"[Whisper] Transcribed (session={session_id[:8]}): {text[:80]}")
    return text


def clear_session_buffer(session_id: str) -> None:
    """Remove the overlap buffer for a session when it ends."""
    _session_buffers.pop(session_id, None)
    logger.debug(f"[Whisper] Buffer cleared for session={session_id[:8]}")