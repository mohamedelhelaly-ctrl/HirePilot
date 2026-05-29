# test_ws_interview.py
"""
Simple WebSocket test client for the live interview endpoint.
Supports two modes:
 - --mic : capture live microphone in short WAV chunks and stream them
 - --file : send a single audio file as one chunk (legacy behavior)

Usage examples:
  python src/backend/test_ws_interview.py --mic --session-id 1 --application-id 2 --requisition-id 3
  python src/backend/test_ws_interview.py --file test.webm --session-id 1 --application-id 2 --requisition-id 3

Notes:
- Ensure the server is running at ws://localhost:8000/api/interview/stream
- For mic mode you need `sounddevice` and `soundfile` installed and PortAudio available on your system.
"""

import argparse
import asyncio
import base64
import io
import json
import logging
import sys

import websockets

# Optional audio dependencies for mic capture
try:
    import sounddevice as sd
    import soundfile as sf
    HAS_AUDIO = True
except Exception:
    HAS_AUDIO = False

# Defaults
URI = "ws://localhost:8000/api/interview/stream"
DEFAULT_SAMPLE_RATE = 16000
DEFAULT_CHUNK_SECONDS = 2.0

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def send_init(ws, session_id, application_id, requisition_id, interview_type="hr_screen"):
    init_msg = {
        "type": "init",
        "session_id": int(session_id),
        "application_id": int(application_id),
        "requisition_id": int(requisition_id),
        "interview_type": interview_type,
    }
    await ws.send(json.dumps(init_msg))
    # read one reply (init_ok or error)
    resp = await ws.recv()
    logger.info(f"init response: {resp}")
    return json.loads(resp)


async def stream_file(ws, audio_file, audio_format="webm"):
    with open(audio_file, "rb") as f:
        data = f.read()
    audio_b64 = base64.b64encode(data).decode()
    await ws.send(json.dumps({
        "type": "audio_chunk",
        "audio_data": audio_b64,
        "audio_format": audio_format,
    }))
    logger.info("sent file chunk")


async def stream_mic(ws, sample_rate=DEFAULT_SAMPLE_RATE, chunk_seconds=DEFAULT_CHUNK_SECONDS):
    if not HAS_AUDIO:
        raise RuntimeError("sounddevice/soundfile not available — install them to use --mic")

    channels = 1
    logger.info(f"Recording microphone: {sample_rate} Hz, {chunk_seconds}s chunks")

    try:
        while True:
            # record chunk
            logger.info("Recording chunk...")
            data = sd.rec(int(sample_rate * chunk_seconds), samplerate=sample_rate, channels=channels, dtype='int16')
            sd.wait()
            # write WAV into buffer
            buf = io.BytesIO()
            sf.write(buf, data, samplerate=sample_rate, format='WAV', subtype='PCM_16')
            buf.seek(0)
            audio_b64 = base64.b64encode(buf.read()).decode()

            msg = {
                "type": "audio_chunk",
                "audio_data": audio_b64,
                "audio_format": "wav",
            }
            await ws.send(json.dumps(msg))
            logger.info("sent audio chunk")

            # non-blocking read of any server messages (transcript, followup, etc.)
            try:
                while True:
                    resp = await asyncio.wait_for(ws.recv(), timeout=0.2)
                    logger.info(f"server: {resp}")
                    # continue reading until timeout
            except asyncio.TimeoutError:
                pass

    except KeyboardInterrupt:
        logger.info("Interrupted by user — stopping mic capture")


async def run_client(args):
    async with websockets.connect(URI) as ws:
        # send init
        init_resp = await send_init(ws, args.session_id, args.application_id, args.requisition_id, args.interview_type)
        if init_resp.get("type") == "error":
            logger.error(f"Server returned error on init: {init_resp.get('message')}")
            return

        # optional ping
        await ws.send(json.dumps({"type":"ping"}))
        try:
            pong = await asyncio.wait_for(ws.recv(), timeout=1.0)
            logger.info(f"pong: {pong}")
        except asyncio.TimeoutError:
            pass

        # choose mode
        if args.mode == "file":
            await stream_file(ws, args.file, audio_format=args.file_format)

            # read messages until timeout or summary
            try:
                while True:
                    msg = await asyncio.wait_for(ws.recv(), timeout=10)
                    logger.info(f"recv: {msg}")
                    j = json.loads(msg)
                    if j.get("type") == "summary":
                        break
            except asyncio.TimeoutError:
                logger.info("no more messages within timeout")

        else:  # mic
            await stream_mic(ws, sample_rate=args.sample_rate, chunk_seconds=args.chunk_seconds)

        # send end_interview
        try:
            await ws.send(json.dumps({"type":"end_interview"}))
            # read final messages until summary or timeout
            try:
                resp = await asyncio.wait_for(ws.recv(), timeout=10)
                logger.info(f"final response: {resp}")
            except asyncio.TimeoutError:
                logger.info("no final response within timeout")
        except Exception as exc:
            logger.warning(f"error sending end_interview: {exc}")


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--session-id", required=True, type=int)
    p.add_argument("--application-id", required=True, type=int)
    p.add_argument("--requisition-id", required=True, type=int)
    p.add_argument("--mode", choices=("mic", "file"), default="file", help="Stream from microphone or send a file")
    p.add_argument("--file", default="test.webm", help="Audio file to send when mode=file")
    p.add_argument("--file-format", dest="file_format", default="webm", help="Format label sent with file chunks (webm, wav, etc.)")
    p.add_argument("--sample-rate", dest="sample_rate", type=int, default=DEFAULT_SAMPLE_RATE)
    p.add_argument("--chunk-seconds", dest="chunk_seconds", type=float, default=DEFAULT_CHUNK_SECONDS)
    p.add_argument("--interview-type", dest="interview_type", default="hr_screen")
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()

    if args.mode == "mic" and not HAS_AUDIO:
        print("Microphone mode requires sounddevice and soundfile. Install with:")
        print("  pip install sounddevice soundfile numpy")
        print("On macOS you may also need: brew install portaudio")
        sys.exit(1)

    try:
        asyncio.run(run_client(args))
    except Exception as e:
        logger.exception("Client error:", exc_info=e)