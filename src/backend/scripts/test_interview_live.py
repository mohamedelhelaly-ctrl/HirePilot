"""
Live Interview WebSocket Test — Microphone Input

Captures real microphone audio in chunks and streams it to the
live interview WebSocket endpoint. Auto-creates an InterviewSession
if one doesn't exist for the given application.

Usage (from repo root):
    python -m src.backend.scripts.test_interview_live

Requirements:
    pip install websockets sounddevice soundfile numpy requests

The script will:
    1. Hit the REST API to find or create an InterviewSession for the
       given APPLICATION_ID + REQUISITION_ID
    2. Connect to ws://localhost:8000/api/interview/stream
    3. Send "init" with the session details
    4. Capture mic audio in CHUNK_SECONDS-second chunks
    5. Send each chunk as base64 WAV
    6. Print transcripts and follow-up questions as they arrive
    7. Press ENTER to end the interview and receive the summary
"""

import asyncio
import base64
import io
import json
import os
import sys
import threading
import time

import numpy as np
import requests
import sounddevice as sd
import soundfile as sf
import websockets

# ── Configure these ───────────────────────────────────────────────────────────
BASE_URL       = os.getenv("API_BASE_URL", "http://localhost:8000/api")
WS_URL         = BASE_URL.replace("http", "ws") + "/interview/stream"

APPLICATION_ID = int(os.getenv("TEST_APPLICATION_ID", "5"))
REQUISITION_ID = int(os.getenv("TEST_REQUISITION_ID", "3"))
INTERVIEW_TYPE = os.getenv("TEST_INTERVIEW_TYPE", "technical")

CHUNK_SECONDS  = 5
SAMPLE_RATE    = 16000
CHANNELS       = 1

AUTH_TOKEN = os.getenv("AUTH_TOKEN", "")
# ─────────────────────────────────────────────────────────────────────────────


GREEN  = "\033[92m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
RED    = "\033[91m"
BOLD   = "\033[1m"
RESET  = "\033[0m"


def _print(colour: str, prefix: str, msg: str):
    print(f"{colour}{BOLD}[{prefix}]{RESET} {msg}")


def info(msg):          _print(CYAN,   "INFO",       msg)
def ok(msg):            _print(GREEN,  "✓",          msg)
def warn(msg):          _print(YELLOW, "WARNING",    msg)
def error(msg):         _print(RED,    "ERROR",      msg)
def transcript(msg):    _print(GREEN,  "TRANSCRIPT", msg)
def followup(msg):      _print(YELLOW, "FOLLOW-UP",  msg)
def summary_print(msg): _print(CYAN, "SUMMARY",      msg)


def _headers() -> dict:
    h = {"Content-Type": "application/json"}
    if AUTH_TOKEN:
        h["Authorization"] = f"Bearer {AUTH_TOKEN}"
    return h


def get_or_create_session() -> dict:
    """Find an existing InterviewSession or create a new one."""
    info(f"Looking up application_id={APPLICATION_ID} ...")

    try:
        resp = requests.get(
            f"{BASE_URL}/interview/sessions/{APPLICATION_ID}",
            headers=_headers(),
            timeout=10,
        )
        if resp.status_code == 200:
            sessions = resp.json()
            for s in sessions:
                if s.get("status") in ("scheduled", "in_progress"):
                    ok(f"Found existing session id={s['id']} status={s['status']}")
                    return {
                        "session_id":     s["id"],
                        "candidate_name": s.get("candidate_name", "Candidate"),
                        "interview_type": s.get("interview_type", INTERVIEW_TYPE),
                    }
    except Exception as exc:
        warn(f"Session lookup failed: {exc} — will create new session")

    info("Creating new InterviewSession ...")
    payload = {
        "application_id": APPLICATION_ID,
        "requisition_id": REQUISITION_ID,
        "interview_type": INTERVIEW_TYPE,
    }
    try:
        resp = requests.post(
            f"{BASE_URL}/interview/sessions",
            json=payload,
            headers=_headers(),
            timeout=10,
        )
        resp.raise_for_status()
        s = resp.json()
        ok(f"Created session id={s['id']}")
        return {
            "session_id":     s["id"],
            "candidate_name": s.get("candidate_name", "Candidate"),
            "interview_type": INTERVIEW_TYPE,
        }
    except Exception as exc:
        error(f"Could not create session: {exc}")
        sys.exit(1)


class MicCapture:
    """Captures microphone audio in a background thread."""

    def __init__(self, sample_rate: int = SAMPLE_RATE, channels: int = CHANNELS):
        self.sample_rate = sample_rate
        self.channels    = channels
        self._buffer: list[np.ndarray] = []
        self._lock       = threading.Lock()
        self._stream     = None

    def start(self):
        self._stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=self.channels,
            dtype="int16",
            callback=self._callback,
        )
        self._stream.start()
        ok("Microphone capture started")

    def stop(self):
        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None

    def _callback(self, indata, frames, time_info, status):
        if status:
            warn(f"Mic status: {status}")
        with self._lock:
            self._buffer.append(indata.copy())

    def get_chunk_wav(self) -> bytes | None:
        with self._lock:
            if not self._buffer:
                return None
            frames = np.concatenate(self._buffer, axis=0)
            self._buffer.clear()

        rms = np.sqrt(np.mean(frames.astype(np.float32) ** 2))
        if rms < 100:
            return None

        buf = io.BytesIO()
        sf.write(buf, frames, self.sample_rate, format="WAV", subtype="PCM_16")
        buf.seek(0)
        return buf.read()


_end_flag = threading.Event()


def _wait_for_enter():
    input()
    _end_flag.set()


async def run(session_info: dict):
    session_id     = session_info["session_id"]
    candidate      = session_info["candidate_name"]
    interview_type = session_info["interview_type"]

    print()
    print(f"{BOLD}{'='*60}{RESET}")
    print(f"{BOLD}  Live Interview Copilot Test{RESET}")
    print(f"  Candidate:      {candidate}")
    print(f"  Session ID:     {session_id}")
    print(f"  Interview type: {interview_type}")
    print(f"  WebSocket:      {WS_URL}")
    print(f"  Chunk size:     {CHUNK_SECONDS}s")
    print(f"{BOLD}{'='*60}{RESET}")
    print()
    print(f"{YELLOW}Press ENTER at any time to end the interview.{RESET}")
    print()

    threading.Thread(target=_wait_for_enter, daemon=True).start()

    mic = MicCapture()
    mic.start()

    async with websockets.connect(WS_URL) as ws:
        info(f"Connected to {WS_URL}")

        await ws.send(json.dumps({
            "type":           "init",
            "session_id":     session_id,
            "application_id": APPLICATION_ID,
            "requisition_id": REQUISITION_ID,
            "interview_type": interview_type,
        }))

        raw = await asyncio.wait_for(ws.recv(), timeout=15)
        msg = json.loads(raw)
        if msg.get("type") == "error":
            error(f"Init failed: {msg.get('message')}")
            mic.stop()
            return
        if msg.get("type") != "init_ok":
            warn(f"Unexpected response to init: {msg}")

        ok(f"Session initialised — candidate: {msg.get('candidate_name')}")
        questions = msg.get("questions", [])
        if questions:
            print()
            print(f"{BOLD}Pre-generated questions:{RESET}")
            for i, q in enumerate(questions, 1):
                print(f"  {i}. {q}")
            print()

        chunk_number  = 0
        last_chunk_at = time.time()

        async def _listen():
            async for raw_msg in ws:
                msg = json.loads(raw_msg)
                t   = msg.get("type")

                if t == "transcript":
                    transcript(msg.get("text", ""))
                elif t == "followup_question":
                    print()
                    followup(f"💡 {msg.get('question')}")
                    print()
                elif t == "status":
                    info(f"Status: {msg.get('status')}")
                elif t == "summary":
                    data = msg.get("data", {})
                    print()
                    print(f"{BOLD}{'='*60}{RESET}")
                    summary_print(f"Summary:\n  {data.get('summary')}")
                    summary_print(f"Assessment:\n  {data.get('overall_assessment')}")
                    summary_print(
                        f"Recommendation score: {data.get('recommendation_score')}/10"
                    )
                    if data.get("technical_depth_score") is not None:
                        summary_print(
                            f"Technical depth score: {data.get('technical_depth_score')}/10"
                        )
                    strengths = data.get("key_strengths", [])
                    concerns  = data.get("key_concerns", [])
                    if strengths:
                        summary_print(f"Key strengths: {', '.join(strengths)}")
                    if concerns:
                        summary_print(f"Key concerns:  {', '.join(concerns)}")
                    qa_pairs = data.get("qa_pairs", [])
                    if qa_pairs:
                        print()
                        print(f"{BOLD}Q&A Breakdown:{RESET}")
                        for i, qa in enumerate(qa_pairs, 1):
                            score_str = (
                                f"  [{qa.get('score')}/5]" if qa.get("score") is not None
                                else ""
                            )
                            print(f"  Q{i}:{score_str} {qa.get('question')}")
                            print(f"       A: {qa.get('answer', '')[:120]}")
                            if qa.get("feedback"):
                                print(f"       Feedback: {qa.get('feedback')}")
                    print(f"{BOLD}{'='*60}{RESET}")
                    return
                elif t == "error":
                    error(f"Server error: {msg.get('message')}")
                elif t == "pong":
                    pass

        listen_task = asyncio.create_task(_listen())

        try:
            while not _end_flag.is_set():
                now = time.time()
                if now - last_chunk_at >= CHUNK_SECONDS:
                    wav_bytes = mic.get_chunk_wav()
                    if wav_bytes:
                        chunk_number += 1
                        encoded = base64.b64encode(wav_bytes).decode("utf-8")
                        await ws.send(json.dumps({
                            "type":         "audio_chunk",
                            "audio_data":   encoded,
                            "audio_format": "wav",
                        }))
                        info(f"Chunk {chunk_number} sent ({len(wav_bytes):,} bytes)")
                    else:
                        info("Chunk skipped — silence detected")
                    last_chunk_at = now

                if chunk_number > 0 and chunk_number % 10 == 0:
                    await ws.send(json.dumps({"type": "ping"}))

                await asyncio.sleep(0.1)

            print()
            info("Ending interview — generating summary, please wait...")
            await ws.send(json.dumps({"type": "end_interview"}))

            try:
                await asyncio.wait_for(listen_task, timeout=120)
            except asyncio.TimeoutError:
                error("Timed out waiting for summary")

        except KeyboardInterrupt:
            info("Interrupted")
        finally:
            listen_task.cancel()
            mic.stop()
            ok("Mic stopped")


if __name__ == "__main__":
    try:
        import sounddevice  # noqa: F401
        import soundfile    # noqa: F401
        import websockets   # noqa: F401
    except ImportError:
        print("Missing dependencies. Run:")
        print("  pip install websockets sounddevice soundfile numpy requests")
        sys.exit(1)

    print(f"{BOLD}Available audio input devices:{RESET}")
    devices = sd.query_devices()
    for i, d in enumerate(devices):
        if d["max_input_channels"] > 0:
            default = " ← default" if i == sd.default.device[0] else ""
            print(f"  [{i}] {d['name']}{default}")
    print()

    session_info = get_or_create_session()
    asyncio.run(run(session_info))
