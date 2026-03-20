"""
Interview Router

WebSocket endpoint for the live interview copilot.

Flow:
1. Frontend connects to ws://.../api/interview/stream
2. Frontend sends "init" message with session_id, interview_type,
   application_id, requisition_id
3. Server loads interview context from DB (pre-generated questions, JD,
   candidate name) and initialises in-memory session state
4. Frontend sends "audio_chunk" messages (base64-encoded audio)
5. Server transcribes each chunk via local Whisper, appends to transcript,
   saves TranscriptChunk to DB, checks 30-second follow-up timer
6. Every 30 seconds (if new content exists), LLM generates a follow-up
   question and pushes it to the frontend
7. Frontend sends "end_interview" message
8. Server invokes the live interview LangGraph subgraph (summary + save)
9. Server sends "summary" message to frontend and closes

Message protocol (client → server):
    {"type": "init",          "session_id": int, "interview_type": str,
                               "application_id": int, "requisition_id": int}
    {"type": "audio_chunk",   "audio_data": "<base64>", "audio_format": "webm"}
    {"type": "ping"}
    {"type": "end_interview"}

Message protocol (server → client):
    {"type": "init_ok",          "candidate_name": str, "questions": [...]}
    {"type": "transcript",        "text": str, "sequence": int}
    {"type": "followup_question", "question": str, "timestamp": float}
    {"type": "status",            "status": str}
    {"type": "summary",           "data": {...}}
    {"type": "pong",              "timestamp": float}
    {"type": "error",             "message": str}
"""

import asyncio
import base64
import json
import logging
import time
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from db.database import AsyncSessionLocal
from db import crud
from schemas import TranscriptChunkCreate
from services.whisper_service import transcribe_chunk, clear_session_buffer
from utils.llm_config import llm_generic
from utils.follow_up_prompts import build_followup_prompt
from graphs.subgraphs.live_interview.graph import live_interview_subgraph
from graphs.subgraphs.live_interview.state import LiveInterviewState

logger = logging.getLogger(__name__)

router = APIRouter()

# ── Configuration ─────────────────────────────────────────────────────────────
FOLLOWUP_INTERVAL_SECONDS = 30   # How often to generate a follow-up question
MIN_NEW_CHARS_FOR_FOLLOWUP = 150  # Don't fire if barely anything new was said


# ── In-memory session store ───────────────────────────────────────────────────
# Keyed by WebSocket object (one per active connection).
# Cleared when the interview ends or the connection drops.

class _Session:
    """Per-connection live interview state held in memory."""
    __slots__ = (
        "session_id", "application_id", "requisition_id",
        "interview_type", "job_description", "candidate_name",
        "pre_generated_questions",
        "transcript_chunks",        # list[str] — raw text of each chunk
        "followup_questions_log",   # list[{question, timestamp}]
        "chunk_sequence",
        "last_followup_time",       # unix timestamp
        "last_followup_question",   # str | None
        "transcript_at_last_followup",  # how many chars were in transcript when we last fired
        "interview_start_time",     # datetime
    )

    def __init__(self):
        self.session_id: int = 0
        self.application_id: int = 0
        self.requisition_id: int = 0
        self.interview_type: str = "hr_screen"
        self.job_description: str = ""
        self.candidate_name: str = ""
        self.pre_generated_questions: list[str] = []
        self.transcript_chunks: list[str] = []
        self.followup_questions_log: list[dict] = []
        self.chunk_sequence: int = 0
        self.last_followup_time: float = 0.0
        self.last_followup_question: str | None = None
        self.transcript_at_last_followup: int = 0
        self.interview_start_time: datetime = datetime.now(timezone.utc)

    @property
    def full_transcript(self) -> str:
        return " ".join(self.transcript_chunks)


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _send(ws: WebSocket, msg: dict) -> None:
    """Send a JSON message to the frontend. Silently ignores closed connections."""
    try:
        await ws.send_text(json.dumps(msg))
    except Exception:
        pass


async def _load_session_context(
    sess: _Session,
    session_id: int,
    application_id: int,
    requisition_id: int,
    interview_type: str,
) -> str | None:
    """
    Load interview context from the DB into the in-memory session.
    Returns an error string on failure, None on success.
    """
    try:
        async with AsyncSessionLocal() as db:
            # Load InterviewSession (pre-generated questions)
            db_session = await crud.get_interview_session_by_id(db, session_id)
            if not db_session:
                return f"InterviewSession {session_id} not found"

            # Load Application → Candidate + Requisition
            application = await crud.get_application_by_id(
                db, application_id, include_relations=True
            )
            if not application:
                return f"Application {application_id} not found"

            requisition = await crud.get_requisition_by_id(db, requisition_id)
            if not requisition:
                return f"Requisition {requisition_id} not found"

            sess.session_id             = session_id
            sess.application_id         = application_id
            sess.requisition_id         = requisition_id
            sess.interview_type         = interview_type
            sess.job_description        = requisition.description or ""
            sess.candidate_name         = (
                application.candidate.full_name
                if application.candidate else "Candidate"
            )
            sess.pre_generated_questions = db_session.questions or []

            # Mark session as in_progress
            from db.models import InterviewStatus
            from schemas import InterviewSessionUpdate
            await crud.update_interview_session(
                db, session_id,
                InterviewSessionUpdate(
                    status=InterviewStatus.IN_PROGRESS,
                    actual_start_time=sess.interview_start_time,
                )
            )

        return None  # success

    except Exception as exc:
        return f"DB context load failed: {exc}"


async def _generate_followup(sess: _Session, ws: WebSocket) -> None:
    """
    Fire an async LLM call to generate one follow-up question.
    Push the result to the frontend. Non-blocking — errors are swallowed
    so the transcription loop is never interrupted.
    """
    try:
        prompt = build_followup_prompt(
            interview_type=sess.interview_type,
            job_description=sess.job_description,
            pre_generated_questions=sess.pre_generated_questions,
            transcript_so_far=sess.full_transcript,
            last_followup=sess.last_followup_question,
        )

        result = await asyncio.to_thread(llm_generic.generate, prompt)
        question = result["results"][0]["generated_text"].strip()

        if not question:
            return

        # Strip any accidental quotes the LLM may have added
        question = question.strip('"\'')

        ts = time.time()
        sess.last_followup_question        = question
        sess.last_followup_time            = ts
        sess.transcript_at_last_followup   = len(sess.full_transcript)
        sess.followup_questions_log.append({"question": question, "timestamp": ts})

        await _send(ws, {
            "type":      "followup_question",
            "question":  question,
            "timestamp": ts,
        })

        logger.info(
            f"[Interview {sess.session_id}] Follow-up generated: {question[:80]}"
        )

    except Exception as exc:
        logger.warning(
            f"[Interview {sess.session_id}] Follow-up generation failed: {exc}"
        )


def _should_generate_followup(sess: _Session) -> bool:
    """
    True if enough time has passed AND enough new content exists
    since the last follow-up question was generated.
    """
    elapsed      = time.time() - sess.last_followup_time
    new_chars    = len(sess.full_transcript) - sess.transcript_at_last_followup
    return elapsed >= FOLLOWUP_INTERVAL_SECONDS and new_chars >= MIN_NEW_CHARS_FOR_FOLLOWUP


# ── WebSocket endpoint ────────────────────────────────────────────────────────

@router.websocket("/stream")
async def interview_stream(websocket: WebSocket):
    """
    Live interview WebSocket endpoint.

    URL: ws://api/interview/stream

    Lifecycle:
        connect → init → [audio_chunk*] → end_interview → disconnect
    """
    await websocket.accept()
    logger.info("[Interview] WebSocket connected")

    sess = _Session()
    initialised = False
    ws_session_key = str(id(websocket))  # unique key for Whisper buffer

    try:
        while True:
            raw = await websocket.receive_text()
            msg = json.loads(raw)
            msg_type = msg.get("type")

            # ── ping ──────────────────────────────────────────────────────────
            if msg_type == "ping":
                await _send(websocket, {"type": "pong", "timestamp": time.time()})
                continue

            # ── init ──────────────────────────────────────────────────────────
            if msg_type == "init":
                session_id     = int(msg.get("session_id", 0))
                application_id = int(msg.get("application_id", 0))
                requisition_id = int(msg.get("requisition_id", 0))
                interview_type = msg.get("interview_type", "hr_screen")

                if not all([session_id, application_id, requisition_id]):
                    await _send(websocket, {
                        "type":    "error",
                        "message": "init requires session_id, application_id, requisition_id",
                    })
                    continue

                err = await _load_session_context(
                    sess, session_id, application_id, requisition_id, interview_type
                )
                if err:
                    await _send(websocket, {"type": "error", "message": err})
                    continue

                initialised = True
                sess.last_followup_time = time.time()  # start the follow-up clock

                await _send(websocket, {
                    "type":           "init_ok",
                    "candidate_name": sess.candidate_name,
                    "questions":      sess.pre_generated_questions,
                    "interview_type": sess.interview_type,
                })
                logger.info(
                    f"[Interview {sess.session_id}] Initialised — "
                    f"type={sess.interview_type}, "
                    f"candidate={sess.candidate_name}"
                )
                continue

            # ── require init before anything else ─────────────────────────────
            if not initialised:
                await _send(websocket, {
                    "type":    "error",
                    "message": "Send 'init' message before sending audio",
                })
                continue

            # ── audio_chunk ───────────────────────────────────────────────────
            if msg_type == "audio_chunk":
                audio_b64    = msg.get("audio_data", "")
                audio_format = msg.get("audio_format", "webm")

                if not audio_b64:
                    await _send(websocket, {
                        "type": "error", "message": "audio_data is required"
                    })
                    continue

                try:
                    audio_bytes = base64.b64decode(audio_b64)
                except Exception as exc:
                    await _send(websocket, {
                        "type": "error", "message": f"base64 decode failed: {exc}"
                    })
                    continue

                # ── Transcribe ────────────────────────────────────────────────
                await _send(websocket, {"type": "status", "status": "transcribing"})
                try:
                    text = await transcribe_chunk(
                        audio_bytes,
                        session_id=ws_session_key,
                        audio_format=audio_format,
                    )
                except Exception as exc:
                    logger.warning(
                        f"[Interview {sess.session_id}] Transcription error: {exc}"
                    )
                    text = ""

                if not text:
                    continue  # silent chunk — nothing to do

                # ── Accumulate ────────────────────────────────────────────────
                sess.transcript_chunks.append(text)
                sess.chunk_sequence += 1

                # Push transcript to frontend immediately
                await _send(websocket, {
                    "type":     "transcript",
                    "text":     text,
                    "sequence": sess.chunk_sequence,
                })

                # ── Persist chunk to DB (non-blocking) ────────────────────────
                async def _save_chunk(t: str, seq: int):
                    try:
                        async with AsyncSessionLocal() as db:
                            await crud.create_transcript_chunk(
                                db,
                                TranscriptChunkCreate(
                                    session_id=sess.session_id,
                                    text=t,
                                    sequence_number=seq,
                                    offset_seconds=time.time() - sess.interview_start_time.timestamp(),
                                )
                            )
                    except Exception as exc:
                        logger.warning(
                            f"[Interview {sess.session_id}] Chunk DB save failed: {exc}"
                        )

                asyncio.create_task(_save_chunk(text, sess.chunk_sequence))

                # ── Follow-up timer check ─────────────────────────────────────
                if _should_generate_followup(sess):
                    asyncio.create_task(_generate_followup(sess, websocket))

                continue

            # ── end_interview ─────────────────────────────────────────────────
            if msg_type == "end_interview":
                logger.info(
                    f"[Interview {sess.session_id}] End interview received — "
                    f"transcript length={len(sess.full_transcript)} chars"
                )

                await _send(websocket, {
                    "type": "status", "status": "generating_summary"
                })

                end_time = datetime.now(timezone.utc)

                # Invoke post-interview subgraph
                subgraph_input = LiveInterviewState(
                    session_id=sess.session_id,
                    application_id=sess.application_id,
                    requisition_id=sess.requisition_id,
                    interview_type=sess.interview_type,
                    full_transcript=sess.full_transcript,
                    pre_generated_questions=sess.pre_generated_questions,
                    job_description=sess.job_description,
                    candidate_name=sess.candidate_name,
                    followup_questions_log=sess.followup_questions_log,
                    interview_start_time=sess.interview_start_time.isoformat(),
                    interview_end_time=end_time.isoformat(),
                )

                try:
                    raw_result = await live_interview_subgraph.ainvoke(subgraph_input)
                    final: LiveInterviewState = (
                        raw_result
                        if isinstance(raw_result, LiveInterviewState)
                        else LiveInterviewState(**raw_result)
                    )
                except Exception as exc:
                    logger.error(
                        f"[Interview {sess.session_id}] Subgraph failed: {exc}",
                        exc_info=True,
                    )
                    await _send(websocket, {
                        "type": "error",
                        "message": f"Summary generation failed: {exc}",
                    })
                    break

                if final.error:
                    await _send(websocket, {
                        "type": "error", "message": final.error
                    })
                    break

                # Push summary to frontend
                await _send(websocket, {
                    "type": "summary",
                    "data": {
                        "summary":               final.summary,
                        "overall_assessment":    final.overall_assessment,
                        "key_strengths":         final.key_strengths,
                        "key_concerns":          final.key_concerns,
                        "recommendation_score":  final.recommendation_score,
                        "technical_depth_score": final.technical_depth_score,
                        "qa_pairs": [
                            {
                                "question": qa.question,
                                "answer":   qa.answer,
                                "score":    qa.score,
                                "feedback": qa.feedback,
                            }
                            for qa in final.qa_pairs
                        ],
                    },
                })
                break

            # ── unknown message type ──────────────────────────────────────────
            await _send(websocket, {
                "type": "error",
                "message": f"Unknown message type: {msg_type}",
            })

    except WebSocketDisconnect:
        logger.info(
            f"[Interview {sess.session_id}] WebSocket disconnected "
            f"(transcript saved: {sess.chunk_sequence} chunks)"
        )
    except Exception as exc:
        logger.error(f"[Interview {sess.session_id}] Unexpected error: {exc}", exc_info=True)
        await _send(websocket, {"type": "error", "message": str(exc)})

    finally:
        # Always clean up the Whisper overlap buffer
        clear_session_buffer(ws_session_key)
        logger.info(f"[Interview {sess.session_id}] Session cleaned up")


# ── REST endpoints ────────────────────────────────────────────────────────────
# Used by the test script (and eventually the frontend) to manage sessions
# without going through the WebSocket.

from fastapi import HTTPException, status as http_status
from pydantic import BaseModel as _BaseModel


class CreateSessionRequest(_BaseModel):
    application_id: int
    requisition_id: int
    interview_type: str = "hr_screen"  # "hr_screen" | "technical" | "behavioral" | "final"


@router.get(
    "/sessions/{application_id}",
    summary="List interview sessions for an application",
)
async def list_sessions(application_id: int):
    """
    Return all InterviewSession rows for a given application,
    ordered by scheduled_start_time descending.
    Includes candidate_name for display convenience.
    """
    try:
        async with AsyncSessionLocal() as db:
            sessions = await crud.get_interview_sessions_by_application(db, application_id)
            application = await crud.get_application_by_id(
                db, application_id, include_relations=True
            )
            candidate_name = (
                application.candidate.full_name
                if application and application.candidate
                else "Unknown"
            )

        return [
            {
                "id":                  s.id,
                "application_id":      s.application_id,
                "interview_type":      s.interview_type,
                "status":              s.status,
                "scheduled_start_time": s.scheduled_start_time.isoformat()
                    if s.scheduled_start_time else None,
                "candidate_name":      candidate_name,
                "questions":           s.questions or [],
            }
            for s in sessions
        ]
    except Exception as exc:
        logger.error(f"[GET /sessions/{application_id}] {exc}", exc_info=True)
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )


@router.post(
    "/sessions",
    summary="Create a new interview session",
    status_code=http_status.HTTP_201_CREATED,
)
async def create_session(req: CreateSessionRequest):
    """
    Create a minimal InterviewSession row for testing or manual scheduling.

    In production, sessions are created by the interview scheduling subgraph
    (which also generates questions and creates the calendar event).
    This endpoint is a convenience shortcut for testing.

    The interviewer_id is set to 1 (first user) as a placeholder — update
    once auth is fully wired up.
    """
    from db.models import InterviewType as DBInterviewType, InterviewStatus as DBInterviewStatus
    from schemas import InterviewSessionCreate

    # Map string to enum
    type_map = {
        "hr_screen":  DBInterviewType.HR_SCREEN,
        "technical":  DBInterviewType.TECHNICAL,
        "behavioral": DBInterviewType.BEHAVIORAL,
        "final":      DBInterviewType.FINAL,
    }
    db_interview_type = type_map.get(req.interview_type, DBInterviewType.HR_SCREEN)

    try:
        async with AsyncSessionLocal() as db:
            # Validate application exists
            application = await crud.get_application_by_id(
                db, req.application_id, include_relations=True
            )
            if not application:
                raise HTTPException(
                    status_code=http_status.HTTP_404_NOT_FOUND,
                    detail=f"Application {req.application_id} not found",
                )

            candidate_name = (
                application.candidate.full_name
                if application.candidate else "Unknown"
            )

            session_data = InterviewSessionCreate(
                application_id=req.application_id,
                interviewer_id=None,  # nullable — set properly once auth is wired
                interview_type=db_interview_type,
                questions=[],
            )
            db_session = await crud.create_interview_session(db, session_data)

            logger.info(
                f"[POST /sessions] Created session id={db_session.id} "
                f"for application_id={req.application_id}"
            )

            return {
                "id":             db_session.id,
                "application_id": db_session.application_id,
                "interview_type": db_session.interview_type,
                "status":         db_session.status,
                "candidate_name": candidate_name,
                "questions":      db_session.questions or [],
            }

    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"[POST /sessions] {exc}", exc_info=True)
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )