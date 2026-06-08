import json
import logging
import re
from typing import List, Dict, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from models.crud import (
    get_application_by_id,
    update_application,
    get_application_details,
    get_requisition_by_id,
)
from models.schemas.application_schemas import ApplicationUpdate
from stores.llm.llm_config import llm_generic

logger = logging.getLogger(__name__)


def _format_application_details(details: list) -> str:
    """Serialize application detail records into a readable input section."""
    if not details:
        return "No applicant details available."

    lines = []
    for detail in details:
        value = detail.value
        if isinstance(value, (dict, list)):
            value = json.dumps(value, ensure_ascii=False)
        lines.append(f"- {detail.key}: {value}")

    return "\n".join(lines)


def _extract_json_array_from_text(text: str) -> Optional[List[Dict[str, str]]]:
    """Try to extract a JSON array from the LLM text output."""
    if not text:
        return None

    # Attempt to isolate the first JSON array in the output.
    first_bracket = text.find("[")
    last_bracket = text.rfind("]")
    if first_bracket != -1 and last_bracket != -1 and last_bracket > first_bracket:
        candidate = text[first_bracket:last_bracket + 1]
        try:
            parsed = json.loads(candidate)
            if isinstance(parsed, list):
                return parsed
        except json.JSONDecodeError:
            pass

    return None


def _parse_question_answer_pairs(text: str) -> List[Dict[str, str]]:
    """Fallback parser that extracts question/answer pairs from plain text."""
    questions = []
    current_question = None
    current_answer = []

    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue

        # Detect explicit question lines.
        question_match = re.match(r"^(?:Q(?:uestion)?\s*\d*[:\.)]?\s*)(.+?)(?:\s*-\s*Answer[:\.]?)?$", stripped, flags=re.I)
        answer_match = re.match(r"^(?:A(?:nswer)?\s*[:\.)]?\s*)(.+)$", stripped, flags=re.I)

        if question_match and not answer_match:
            if current_question and current_answer:
                questions.append({
                    "question": current_question,
                    "answer": " ".join(current_answer).strip(),
                })
            current_question = question_match.group(1).strip()
            current_answer = []
            continue

        if answer_match and current_question:
            current_answer.append(answer_match.group(1).strip())
            continue

        # If the line begins with a dash and includes a colon, treat it as a question/answer pair.
        pair_match = re.match(r"^[-*]\s*(.+?):\s*(.+)$", stripped)
        if pair_match:
            if current_question and current_answer:
                questions.append({
                    "question": current_question,
                    "answer": " ".join(current_answer).strip(),
                })
            current_question = pair_match.group(1).strip()
            current_answer = [pair_match.group(2).strip()]
            continue

        if current_question:
            current_answer.append(stripped)

    if current_question and current_answer:
        questions.append({
            "question": current_question,
            "answer": " ".join(current_answer).strip(),
        })

    return questions


def _build_generate_questions_prompt(
    title: str,
    description: str,
    details_text: str,
) -> str:
    """Create a prompt for the LLM that explains the input and expected JSON response."""
    return (
        "You are a technical recruiter. Generate 8 interview-style technical questions with model answers "
        "for a candidate applying to a specific requisition. Use the requisition title and description plus the applicant details."\
        "\n\n"
        "Input structure:\n"
        "- Requisition title: a short job title.\n"
        "- Requisition description: the full job description, responsibilities, and requirements.\n"
        "- Applicant details: key/value pairs containing skills, experience, and other facts specific to this candidate.\n\n"
        "Please produce a JSON array of objects only. Each object must have exactly two keys: \"question\" and \"answer\".\n"
        "Do not wrap the output in markdown code fences. Do not include any additional text outside the JSON array.\n"
        "If a detail is missing, still generate relevant technical questions from the requisition information.\n\n"
        "Example response format:\n"
        "[\n"
        "  {\n"
        "    \"question\": \"What is your experience building scalable REST APIs?\",\n"
        "    \"answer\": \"I have designed and maintained REST APIs using Python, FastAPI, and SQLAlchemy...\"\n"
        "  },\n"
        "  {\n"
        "    \"question\": \"How would you approach optimizing a database query for a large dataset?\",\n"
        "    \"answer\": \"I would analyze indexes, use query profiling, and consider denormalization when necessary...\"\n"
        "  }\n"
        "]\n\n"
        "Requisition title:\n"
        f"{title}\n\n"
        "Requisition description:\n"
        f"{description}\n\n"
        "Applicant details:\n"
        f"{details_text}\n"
    )


async def generate_questions_for_application(
    db: AsyncSession,
    application_id: int,
) -> List[Dict[str, str]]:
    """Generate and persist tailored tech questions for an application."""
    # Step 1: Fetch the application record by ID.
    application = await get_application_by_id(db, application_id)
    if application is None:
        raise ValueError(f"Application with ID {application_id} not found.")

    # Step 2: Return existing tech questions if they already exist.
    if application.tech_questions:
        logger.debug("Returning cached tech_questions for application %s", application_id)
        return application.tech_questions

    # Step 3: Fetch the requisition that owns the application.
    requisition = await get_requisition_by_id(db, application.requisition_id)
    if requisition is None:
        raise ValueError(
            f"Requisition with ID {application.requisition_id} not found for application {application_id}."
        )

    # Step 4: Fetch applicant-specific details for this application.
    details = await get_application_details(db, application_id)
    details_text = _format_application_details(details)

    # Step 5: Build a prompt that explains the input structure and required JSON response.
    prompt = _build_generate_questions_prompt(
        title=requisition.title,
        description=requisition.description,
        details_text=details_text,
    )

    # Step 6: Call the generic LLM and read the generated text.
    llm_response = llm_generic.generate(prompt)
    raw_text = llm_response.get("results", [{}])[0].get("generated_text", "")
    logger.debug("LLM raw output for application %s: %s", application_id, raw_text[:1000])

    # Step 7: Parse the output into a structured list of question/answer objects.
    questions = _extract_json_array_from_text(raw_text)
    if questions is None:
        questions = _parse_question_answer_pairs(raw_text)

    # Ensure the returned value is a list of dicts.
    if not isinstance(questions, list):
        questions = []

    # Step 8: Persist the generated tech questions on the application record.
    updates = ApplicationUpdate(tech_questions=questions)
    saved_application = await update_application(db, application_id, updates)
    if saved_application is None:
        raise ValueError(f"Failed to persist tech questions for application {application_id}.")

    return saved_application.tech_questions or []
