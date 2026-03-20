"""
Node 1 — Generate Interview Summary

Responsibilities:
- Parse the full interview transcript into Q&A pairs using the LLM
- Generate a holistic summary covering overall fit, strengths, concerns
- Produce a recommendation_score (0–10)
- For technical interviews: score each Q&A pair and produce technical_depth_score

Two separate prompts are used:
    HR / behavioral / final  → holistic summary + Q&A extraction (no reference answers)
    Technical                → holistic summary + Q&A extraction + per-question scores
"""

import sys
import json
import asyncio
import logging
from pathlib import Path

import json_repair

sys.path.insert(0, str(Path(__file__).resolve().parents[5]))

from utils.llm_config import llm_generic
from ..state import LiveInterviewState, QAPair

logger = logging.getLogger(__name__)


# ── Prompt builders ───────────────────────────────────────────────────────────

def _build_hr_prompt(state: LiveInterviewState) -> str:
    questions_str = (
        "\n".join(f"- {q}" for q in state.pre_generated_questions)
        if state.pre_generated_questions
        else "No pre-generated questions were used for this interview."
    )
    followups_str = "\n".join(
        f"- {fq['question']}" for fq in state.followup_questions_log
    ) if state.followup_questions_log else "None"

    system = """\
You are a senior HR evaluator reviewing a completed interview transcript.

Your tasks:
1. Extract all question/answer pairs from the transcript.
2. Write a concise holistic summary of the candidate (3-4 sentences).
3. Write an overall assessment sentence.
4. List up to 5 key strengths and up to 5 key concerns.
5. Assign a recommendation_score from 0–10 reflecting overall interview performance.

Return ONLY valid JSON (no markdown, no commentary):
{
  "qa_pairs": [
    {"question": "...", "answer": "..."}
  ],
  "summary": "...",
  "overall_assessment": "...",
  "key_strengths": ["...", "..."],
  "key_concerns": ["...", "..."],
  "recommendation_score": <float 0-10>
}

Scoring guide:
  8–10 = exceptional candidate, strong hire recommendation
  6–7  = good candidate, recommend with minor reservations
  4–5  = average, needs review
  0–3  = poor fit, not recommended"""

    user = f"""CANDIDATE: {state.candidate_name}
JOB DESCRIPTION: {state.job_description[:600]}

PRE-GENERATED QUESTIONS:
{questions_str}

FOLLOW-UP QUESTIONS ASKED DURING INTERVIEW:
{followups_str}

FULL INTERVIEW TRANSCRIPT:
{state.full_transcript}"""

    return f"SYSTEM:\n{system}\n\nUSER:\n{user}"


def _build_technical_prompt(state: LiveInterviewState) -> str:
    questions_str = (
        "\n".join(f"- {q}" for q in state.pre_generated_questions)
        if state.pre_generated_questions
        else "No pre-generated questions were used for this interview."
    )
    followups_str = "\n".join(
        f"- {fq['question']}" for fq in state.followup_questions_log
    ) if state.followup_questions_log else "None"

    system = """\
You are an expert technical interviewer evaluating a completed technical interview.

Your tasks:
1. Extract all question/answer pairs from the transcript.
2. For each Q&A pair, assign a score (0–5) and brief feedback based on technical accuracy,
   depth, and relevance to the job description.
3. Write a concise holistic summary of the candidate's technical abilities (3-4 sentences).
4. Write an overall assessment sentence.
5. List up to 5 key technical strengths and up to 5 key technical concerns.
6. Assign a recommendation_score (0–10) reflecting overall interview performance.
7. Assign a technical_depth_score (0–10) reflecting depth of technical knowledge specifically.

Scoring guide for individual Q&A pairs (0–5):
  5 = Excellent — deep understanding, specific examples, best practices mentioned
  4 = Good — correct and relevant, minor gaps
  3 = Satisfactory — basic understanding, partial answer
  2 = Below average — vague or superficial
  1 = Poor — off-topic or very weak
  0 = Not answered / completely irrelevant

Return ONLY valid JSON (no markdown, no commentary):
{
  "qa_pairs": [
    {
      "question": "...",
      "answer": "...",
      "score": <float 0-5>,
      "feedback": "..."
    }
  ],
  "summary": "...",
  "overall_assessment": "...",
  "key_strengths": ["...", "..."],
  "key_concerns": ["...", "..."],
  "recommendation_score": <float 0-10>,
  "technical_depth_score": <float 0-10>
}"""

    user = f"""CANDIDATE: {state.candidate_name}
JOB DESCRIPTION: {state.job_description[:600]}

PRE-GENERATED TECHNICAL QUESTIONS:
{questions_str}

FOLLOW-UP QUESTIONS ASKED DURING INTERVIEW:
{followups_str}

FULL INTERVIEW TRANSCRIPT:
{state.full_transcript}"""

    return f"SYSTEM:\n{system}\n\nUSER:\n{user}"


# ── JSON parsing ──────────────────────────────────────────────────────────────

def _parse_response(raw: str) -> dict:
    clean = raw.strip()
    if clean.startswith("```"):
        parts = clean.split("```")
        inner = parts[1]
        if inner.startswith("json"):
            inner = inner[4:]
        clean = inner.strip()
    try:
        return json.loads(clean)
    except json.JSONDecodeError:
        result = json_repair.loads(clean)
        if not isinstance(result, dict):
            raise ValueError(f"json_repair returned {type(result).__name__} instead of dict")
        return result


# ── Node ──────────────────────────────────────────────────────────────────────

async def generate_summary_node(state: LiveInterviewState) -> LiveInterviewState:
    """
    Node 1: Generate holistic summary and Q&A analysis from the full transcript.

    Reads:
        state.full_transcript
        state.interview_type
        state.job_description
        state.pre_generated_questions
        state.followup_questions_log
        state.candidate_name

    Writes:
        state.summary
        state.overall_assessment
        state.key_strengths
        state.key_concerns
        state.recommendation_score
        state.technical_depth_score  (technical interviews only)
        state.qa_pairs
    """
    if state.error:
        return state

    if not state.full_transcript or len(state.full_transcript.strip()) < 50:
        state.error = "[Node 1] Transcript is too short to generate a meaningful summary"
        logger.error(state.error)
        return state

    is_technical = state.interview_type == "technical"

    prompt = (
        _build_technical_prompt(state)
        if is_technical
        else _build_hr_prompt(state)
    )

    logger.info(
        f"[Node 1: generate_summary] interview_type={state.interview_type}, "
        f"transcript_length={len(state.full_transcript)} chars"
    )

    try:
        result = await asyncio.to_thread(llm_generic.generate, prompt)
        raw = result["results"][0]["generated_text"]
        data = _parse_response(raw)
    except Exception as exc:
        state.error = f"[Node 1] LLM call failed: {exc}"
        logger.error(state.error)
        return state

    # ── Populate state from parsed response ───────────────────────────────────
    state.summary             = data.get("summary", "")
    state.overall_assessment  = data.get("overall_assessment", "")
    state.key_strengths       = data.get("key_strengths", [])
    state.key_concerns        = data.get("key_concerns", [])
    state.recommendation_score = float(data.get("recommendation_score", 0.0))

    if is_technical:
        state.technical_depth_score = float(data.get("technical_depth_score", 0.0))

    # Build QAPair objects
    qa_pairs: list[QAPair] = []
    for item in data.get("qa_pairs", []):
        qa_pairs.append(QAPair(
            question=item.get("question", ""),
            answer=item.get("answer", ""),
            score=float(item["score"]) if "score" in item else None,
            feedback=item.get("feedback"),
        ))
    state.qa_pairs = qa_pairs

    logger.info(
        f"[Node 1] Summary generated — "
        f"recommendation_score={state.recommendation_score}, "
        f"qa_pairs={len(qa_pairs)}, "
        f"technical_depth_score={state.technical_depth_score}"
    )

    return state