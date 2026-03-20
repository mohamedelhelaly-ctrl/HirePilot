# Live Interview Copilot — Technical Documentation

## Overview

The live interview copilot is a real-time AI assistant that sits alongside the interviewer during a candidate interview. It transcribes speech to text, generates contextual follow-up questions every N seconds, and produces a structured post-interview evaluation automatically when the session ends.

The feature is built in two distinct layers:

- **A WebSocket endpoint** that owns everything real-time: audio ingestion, transcription, follow-up generation, and in-memory session state.
- **A LangGraph post-processing subgraph** that runs once when the interview ends: summary generation, Q&A extraction and scoring, and DB persistence.

The main orchestration graph (`main_graph.py`) is not involved in the live loop at all. The WebSocket handler invokes the LangGraph subgraph directly at the end.

---

## Architecture

```
Frontend (browser)
    │
    │  WebSocket  ws://api/interview/stream
    │
    ▼
FastAPI WebSocket endpoint  (api/routers/interview.py)
    │
    ├── audio chunk received
    │       └── WhisperService (local model, CPU/GPU)
    │               └── transcript text → pushed to frontend
    │               └── saved to TranscriptChunk table
    │               └── 30s timer check → LLM follow-up → pushed to frontend
    │
    └── "end_interview" received
            └── LiveInterviewState assembled
                    └── LangGraph subgraph (subgraphs/live_interview/)
                            ├── Node 1: generate_summary  (LLM)
                            └── Node 2: save_interview    (DB)
                                    └── summary pushed to frontend
```

---

## Files Added

| File | Location | Purpose |
|---|---|---|
| `whisper_service.py` | `services/` | Singleton Whisper model, transcribe + translate to English |
| `interview.py` | `api/routers/` | WebSocket endpoint + REST session endpoints |
| `follow_up_prompts.py` | `utils/` | HR and technical follow-up question prompt builders |
| `live_interview/state.py` | `graphs/subgraphs/live_interview/` | Post-interview subgraph state schema |
| `live_interview/graph.py` | `graphs/subgraphs/live_interview/` | 2-node compiled LangGraph subgraph |
| `live_interview/nodes/generate_summary.py` | `graphs/subgraphs/live_interview/nodes/` | LLM summary + Q&A extraction node |
| `live_interview/nodes/save_interview.py` | `graphs/subgraphs/live_interview/nodes/` | DB persistence + counter increment node |
| `live_interview.py` | `graphs/nodes/` | Updated stub node in main orchestrator graph |

### Files Modified

| File | What changed |
|---|---|
| `main.py` | Whisper loaded on startup, interview router registered |
| `db/models/interview_session.py` | `interviewer_id` made nullable |
| `schemas/__init__.py` | `InterviewSessionCreate` + response schemas updated |
| `requirements.txt` | Added `sounddevice`, `soundfile`, `websockets`, `numpy` |

---

## How It Works Step by Step

### 1. Session Initialisation

Before the interview starts, the frontend calls:

```
GET  /api/interview/sessions/{application_id}
```

This returns any existing `scheduled` or `in_progress` session for that application. If none exists, the frontend calls:

```
POST /api/interview/sessions
Body: { application_id, requisition_id, interview_type }
```

This creates a minimal `InterviewSession` row. In production (once the scheduling subgraph is built), this row will already exist with pre-generated questions attached. The endpoint is a convenience fallback.

The response includes the session ID and any pre-generated questions, which the frontend displays to the interviewer before they start.

### 2. WebSocket Connection

The frontend opens a WebSocket to `ws://api/interview/stream` and sends an `init` message:

```json
{
  "type": "init",
  "session_id": 3,
  "application_id": 5,
  "requisition_id": 1,
  "interview_type": "technical"
}
```

The server loads the full context from the DB — job description, candidate name, pre-generated questions — and responds with `init_ok`. From this point, all real-time communication happens over this WebSocket connection.

### 3. Audio Streaming

The frontend captures microphone audio in chunks (typically 5–10 seconds each) and sends them as base64-encoded audio:

```json
{
  "type": "audio_chunk",
  "audio_data": "<base64 WAV or WebM>",
  "audio_format": "wav"
}
```

On the server:
1. The audio bytes are passed to the local Whisper model via `ffmpeg` for decoding.
2. Whisper runs in **translate mode** — it handles Arabic, English, or mixed speech and always outputs English text.
3. An overlap buffer of 2 previous chunks is prepended to each new chunk to avoid word cut-offs at boundaries.
4. The transcribed text is pushed back to the frontend immediately as a `transcript` message.
5. The chunk is saved to the `TranscriptChunk` table as a background task (non-blocking).
6. The 30-second timer is checked — if enough time has passed and enough new content exists, a follow-up question is generated.

### 4. Follow-up Question Generation

Every 30 seconds (configurable via `FOLLOWUP_INTERVAL_SECONDS`), if at least 150 new characters have been transcribed since the last follow-up, the server fires an async LLM call.

The prompt differs by interview type:
- **HR / behavioral / final**: probes for STAR format, asks for specific examples, digs into situations the candidate described.
- **Technical**: probes for implementation details, trade-offs, edge cases, debugging approaches.

The follow-up question is pushed to the frontend as a `followup_question` message and logged in memory for context in future prompts. The generation is fully non-blocking — if it fails or is slow, transcription continues unaffected.

### 5. Ending the Interview

When the interviewer clicks "End Interview", the frontend sends:

```json
{ "type": "end_interview" }
```

The server assembles the complete in-memory session state and invokes the LangGraph post-processing subgraph.

**Node 1 — generate_summary:**

For **HR interviews**: extracts Q&A pairs from the transcript, writes a holistic summary, assigns a `recommendation_score` (0–10), and lists key strengths and concerns.

For **technical interviews**: does all of the above plus scores each Q&A pair individually (0–5) with per-question feedback, and assigns a separate `technical_depth_score`.

**Node 2 — save_interview:**

- Updates the `InterviewSession` row: full transcript, summary, scores, status → `COMPLETED`.
- Updates the `Application` row: `overall_interview_score`, `last_interview_completed_at`, status → `INTERVIEW_COMPLETED`.
- Increments `new_interview_counter` on the `Requisition`.
- If `new_interview_counter >= new_interview_threshold`, triggers batch re-screening in the background (fire-and-forget `asyncio.create_task`).

The final summary is pushed to the frontend as a `summary` message, and the WebSocket connection closes.

---

## WebSocket Message Reference

### Client → Server

| Type | Required fields | Description |
|---|---|---|
| `init` | `session_id`, `application_id`, `requisition_id`, `interview_type` | Must be first message after connecting |
| `audio_chunk` | `audio_data` (base64), `audio_format` | One chunk of mic audio |
| `ping` | — | Heartbeat, server responds with `pong` |
| `end_interview` | — | Signals end of session, triggers summary |

### Server → Client

| Type | Key fields | Description |
|---|---|---|
| `init_ok` | `candidate_name`, `questions`, `interview_type` | Session ready, pre-generated questions |
| `transcript` | `text`, `sequence` | Transcribed text chunk |
| `followup_question` | `question`, `timestamp` | AI-generated follow-up for the interviewer |
| `status` | `status` | Processing status indicators |
| `summary` | `data` object | Full post-interview evaluation |
| `pong` | `timestamp` | Response to ping |
| `error` | `message` | Error description |

### Summary Data Object

```json
{
  "summary": "3-4 sentence holistic evaluation",
  "overall_assessment": "One-sentence recommendation",
  "key_strengths": ["strength 1", "strength 2"],
  "key_concerns": ["concern 1", "concern 2"],
  "recommendation_score": 7.5,
  "technical_depth_score": 6.0,
  "qa_pairs": [
    {
      "question": "...",
      "answer": "...",
      "score": 4.0,
      "feedback": "..."
    }
  ]
}
```

`technical_depth_score` and per-question `score`/`feedback` are only populated for technical interviews. HR interviews return `null` for `technical_depth_score` and Q&A pairs without scores.

---

## What the Frontend Needs to Build

### Before the Interview

1. Fetch sessions for the candidate's application: `GET /api/interview/sessions/{application_id}`.
2. If none exist in `scheduled` status, create one: `POST /api/interview/sessions`.
3. Show the interviewer the pre-generated questions (from `init_ok`) before they start recording.
4. Let the interviewer select `hr_screen` or `technical` — this controls follow-up and scoring behaviour.

### During the Interview

1. Open a WebSocket to `ws://api/interview/stream`.
2. Send `init` with session details.
3. Start capturing microphone audio using the browser's `MediaRecorder` API in 5–10 second chunks.
4. Send each chunk as `audio_chunk` with the audio encoded as base64.
5. Render incoming `transcript` messages as a live scrolling transcript panel.
6. Render incoming `followup_question` messages prominently — these are real-time coaching suggestions for the interviewer.
7. Show a "End Interview" button that sends `end_interview` and shows a loading state.
8. On `summary` message, navigate to or display the evaluation view.

### After the Interview

The summary data is already stored in the DB and linked to the application. The evaluation view can be rendered directly from:

```
GET /api/interview/sessions/{application_id}
```

or from the screening response when viewing the candidate's full profile.

---

## What Still Needs to Be Built / Integrated

### Authentication

Currently `interviewer_id` on `InterviewSession` is nullable — it is set to `null` when created via the test endpoint. Once auth is integrated, the WebSocket init flow should pass a JWT and the server should:
1. Validate the token.
2. Extract `user_id` and set it as `interviewer_id` on session creation.
3. Verify the user has access to the given application/requisition.

### Interview Scheduling Subgraph

The scheduling subgraph (not yet built) will create the `InterviewSession` row with:
- Pre-generated questions tailored to the candidate's CV and assessment score.
- `interviewer_id` set to the assigned hiring manager.
- `scheduled_start_time` / `scheduled_end_time`.
- Google Calendar event ID and Meet link.

Once that subgraph exists, the `POST /api/interview/sessions` convenience endpoint used for testing will no longer be the primary session creation path.

### Lever Sync

After the interview completes, Node 2 (`save_interview`) should push the interview summary as a note to the candidate's Lever profile. The Lever API integration is not yet implemented. The hook is already in the right place — add it to `save_interview_node` after the DB updates.

### Frontend Audio Capture

The test script uses Python `sounddevice` for mic capture. The browser frontend will use the `MediaRecorder` API. Key considerations:
- `MediaRecorder` outputs WebM/Opus by default — the server already handles this via ffmpeg.
- Chunk interval should match the server's `FOLLOWUP_INTERVAL_SECONDS` so a meaningful amount of speech is included per chunk. 5–10 seconds is the right range.
- Handle WebSocket reconnection gracefully — chunks are saved to `TranscriptChunk` as they arrive, so content is never lost even if the connection drops.

### Whisper Model Upgrade

The current setup uses `openai/whisper-small` which is fast but makes errors on technical jargon (e.g. "Chrome the VectorStore" instead of "ChromaDB"). When a fine-tuned Arabic/English technical model becomes available, swap the model name via the `WHISPER_MODEL_NAME` environment variable — no code changes needed.

GPU deployment will also significantly improve transcription speed. Set `WHISPER_DEVICE=cuda` in `.env` if a GPU is available.

---

## Data Model Summary

The live interview feature reads and writes the following tables:

| Table | What is read | What is written |
|---|---|---|
| `interview_sessions` | pre-generated questions, session metadata | status, transcript, summary, scores, follow-up log |
| `transcript_chunks` | — | one row per audio chunk, ordered by sequence number |
| `applications` | candidate name, requisition | `overall_interview_score`, `last_interview_completed_at`, status |
| `requisitions` | `new_interview_threshold` | `new_interview_counter` incremented |
| `candidates` | `full_name` for display | — |

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `WHISPER_MODEL_NAME` | `openai/whisper-small` | HuggingFace model ID or local path |
| `WHISPER_DEVICE` | auto-detected | `cuda` or `cpu` |