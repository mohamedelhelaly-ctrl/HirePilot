import logging
from typing import Dict, List

from sqlalchemy.ext.asyncio import AsyncSession

from models.crud import get_application_by_id, update_application
from models.schemas.application_schemas import ApplicationUpdate
from stores.llm.llm_config import llm_generic

from .question_context import load_application_question_context, build_candidate_jd_context_block
from .question_parsing import (
    extract_json_array_from_text,
    normalize_tech_questions,
    parse_question_answer_pairs,
)

logger = logging.getLogger(__name__)


def _build_generate_questions_prompt(context_block: str, candidate_name: str) -> str:
    return (
        "You are a senior technical interviewer preparing a candidate-specific technical interview guide.\n\n"
        "Your task: generate exactly 8 technical interview questions with model answers tailored to "
        f"THIS candidate ({candidate_name}) and THIS job only.\n\n"
        "Tailoring rules (mandatory):\n"
        "1. Read the job description and identify the top technical requirements for the role.\n"
        "2. Read the candidate's CV profile and screening summary — reference their actual skills, "
        "projects, roles, certifications, and experience level by name where possible.\n"
        "3. At least 5 questions must explicitly probe how THIS candidate's background maps to "
        "specific JD requirements (strengths to validate OR gaps to explore).\n"
        "4. At least 2 questions should go deeper on the candidate's most relevant project or role "
        "listed in their CV.\n"
        "5. Calibrate difficulty to the candidate's seniority and the role level implied by the JD.\n"
        "6. Do NOT ask generic textbook questions that could apply to any candidate.\n"
        "7. Model answers should describe what a strong answer from someone with THIS background "
        "would sound like — not a generic textbook answer.\n\n"
        "Output format:\n"
        "- Return ONLY a JSON array (no markdown fences, no extra text).\n"
        "- Each object must have exactly: \"question\" and \"answer\".\n\n"
        "Example:\n"
        "[\n"
        "  {\n"
        "    \"question\": \"You listed FastAPI and PostgreSQL on your CV — how did you design API "
        "pagination and indexing for a high-volume endpoint in your logistics project?\",\n"
        "    \"answer\": \"A strong answer references their specific project, explains query/index "
        "choices, trade-offs, and measurable performance impact.\"\n"
        "  }\n"
        "]\n\n"
        f"{context_block}"
    )


async def generate_questions_for_application(
    db: AsyncSession,
    application_id: int,
    *,
    force: bool = False,
) -> List[Dict[str, str]]:
    """Generate and persist tailored tech questions for a single application."""
    application = await get_application_by_id(db, application_id)
    if application is None:
        raise ValueError(f"Application with ID {application_id} not found.")

    if application.tech_questions and not force:
        logger.debug("Returning cached tech_questions for application %s", application_id)
        return application.tech_questions

    ctx = await load_application_question_context(db, application_id)
    context_block = build_candidate_jd_context_block(ctx)
    prompt = _build_generate_questions_prompt(context_block, ctx.candidate_name)

    llm_response = llm_generic.generate(prompt)
    raw_text = llm_response.get("results", [{}])[0].get("generated_text", "")
    logger.debug("LLM raw tech output for application %s: %s", application_id, raw_text[:1000])

    parsed = extract_json_array_from_text(raw_text)
    if parsed is None:
        parsed = parse_question_answer_pairs(raw_text)

    questions = normalize_tech_questions(parsed if isinstance(parsed, list) else [])

    updates = ApplicationUpdate(tech_questions=questions)
    saved_application = await update_application(db, application_id, updates)
    if saved_application is None:
        raise ValueError(f"Failed to persist tech questions for application {application_id}.")

    return saved_application.tech_questions or []
