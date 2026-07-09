"""
Post-process RAG Final Answer text so recruiters never see raw JSON tool output.
"""

import json
import re
from datetime import datetime
from typing import Any, List, Optional


_STATUS_LABELS = {
    "applied": "Applied",
    "screening": "Screening",
    "screened": "Screened",
    "interview_scheduled": "Interview scheduled",
    "interview_completed": "Interview completed",
    "offered": "Offered",
    "hired": "Hired",
    "rejected": "Rejected",
}

_JSON_ARRAY_RE = re.compile(r"\[[\s\S]*?\]")
_JSON_OBJECT_RE = re.compile(r"\{[\s\S]*?\}")


def _format_status(value: Optional[str]) -> str:
    if not value:
        return "—"
    return _STATUS_LABELS.get(value, value.replace("_", " ").title())


def _format_score(value: Any) -> str:
    if value is None:
        return "—"
    try:
        num = float(value)
    except (TypeError, ValueError):
        return str(value)
    if 0 <= num <= 1:
        return f"{round(num * 100)}%"
    return f"{round(num)}%"


def _format_date(value: Optional[str]) -> str:
    if not value:
        return "—"
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return dt.strftime("%b %d, %Y")
    except ValueError:
        return value[:10] if len(value) >= 10 else value


def _is_candidate_summary(item: dict) -> bool:
    return isinstance(item, dict) and "candidate_id" in item and "name" in item


def _candidates_to_table(candidates: List[dict]) -> str:
    if not candidates:
        return "No candidates found for this requisition."

    lines = [
        "| Name | Email | Status | Score | Applied |",
        "| --- | --- | --- | --- | --- |",
    ]
    for c in candidates:
        lines.append(
            "| {name} | {email} | {status} | {score} | {applied} |".format(
                name=c.get("name") or "—",
                email=c.get("email") or "—",
                status=_format_status(c.get("status")),
                score=_format_score(c.get("combined_score") or c.get("score")),
                applied=_format_date(c.get("applied_at")),
            )
        )
    return "\n".join(lines)


def _candidate_details_to_markdown(data: dict) -> str:
    parts: List[str] = []

    candidate = data.get("candidate") or {}
    application = data.get("application") or {}
    extracted = data.get("extracted_details") or data.get("details") or {}
    screening = data.get("screening_result") or data.get("screening") or {}

    name = candidate.get("full_name") or candidate.get("name") or "Candidate"
    parts.append(f"**{name}**")

    meta = []
    if candidate.get("email"):
        meta.append(f"Email: {candidate['email']}")
    if application.get("status"):
        meta.append(f"Status: {_format_status(application['status'])}")
    score = application.get("combined_score")
    if score is not None:
        meta.append(f"Score: {_format_score(score)}")
    if meta:
        parts.append("\n".join(f"- {m}" for m in meta))

    skills = extracted.get("skills") or extracted.get("key_skills")
    if skills:
        if isinstance(skills, list):
            skill_text = ", ".join(str(s) for s in skills)
        else:
            skill_text = str(skills)
        parts.append(f"\n**Skills**\n- {skill_text}")

    education = extracted.get("education")
    if education:
        if isinstance(education, list):
            edu_lines = []
            for edu in education:
                if isinstance(edu, dict):
                    edu_lines.append(
                        ", ".join(
                            str(edu.get(k))
                            for k in ("degree", "institution", "field")
                            if edu.get(k)
                        )
                        or str(edu)
                    )
                else:
                    edu_lines.append(str(edu))
            parts.append("\n**Education**\n" + "\n".join(f"- {e}" for e in edu_lines))
        else:
            parts.append(f"\n**Education**\n- {education}")

    experience = extracted.get("experience") or extracted.get("work_experience")
    if experience:
        if isinstance(experience, list):
            exp_lines = [str(e) if not isinstance(e, dict) else e.get("title") or str(e) for e in experience]
            parts.append("\n**Experience**\n" + "\n".join(f"- {e}" for e in exp_lines if e))
        else:
            parts.append(f"\n**Experience**\n- {experience}")

    justification = screening.get("justification") or screening.get("summary")
    if justification:
        parts.append(f"\n**Screening notes**\n{justification}")

    return "\n".join(parts) if parts else json.dumps(data, ensure_ascii=False, indent=2)


def _requisition_to_markdown(data: dict) -> str:
    title = data.get("title") or "Requisition"
    lines = [f"**{title}**"]
    for label, key in (
        ("Department", "department"),
        ("Location", "location"),
        ("Status", "is_active"),
    ):
        value = data.get(key)
        if value is None:
            continue
        if key == "is_active":
            value = "Active" if value else "Inactive"
        lines.append(f"- **{label}:** {value}")
    if data.get("description"):
        lines.append(f"\n{data['description']}")
    return "\n".join(lines)


def _json_value_to_markdown(value: Any) -> Optional[str]:
    if isinstance(value, list) and value and all(_is_candidate_summary(x) for x in value):
        return _candidates_to_table(value)
    if isinstance(value, dict):
        if "candidate_id" in value and "name" in value:
            return _candidates_to_table([value])
        if value.get("candidate") or value.get("application"):
            return _candidate_details_to_markdown(value)
        if value.get("title") and ("description" in value or "department" in value):
            return _requisition_to_markdown(value)
    return None


def _try_parse_json_blob(blob: str) -> Optional[Any]:
    try:
        return json.loads(blob)
    except json.JSONDecodeError:
        return None


def _replace_json_blobs(text: str) -> str:
    def replace_match(match: re.Match) -> str:
        parsed = _try_parse_json_blob(match.group(0))
        if parsed is None:
            return match.group(0)
        formatted = _json_value_to_markdown(parsed)
        return formatted if formatted else match.group(0)

    # Arrays first (longer spans), then objects
    text = _JSON_ARRAY_RE.sub(replace_match, text)
    text = _JSON_OBJECT_RE.sub(replace_match, text)
    return text


def humanize_final_answer(answer: str) -> str:
    """
    Ensure Final Answer text is recruiter-friendly markdown, not raw tool JSON.
    """
    if not answer:
        return answer

    stripped = answer.strip()

    # Entire answer is JSON
    parsed = _try_parse_json_blob(stripped)
    if parsed is not None:
        formatted = _json_value_to_markdown(parsed)
        if formatted:
            return formatted

    # Strip common LLM prefixes then replace embedded JSON
    cleaned = re.sub(
        r"^(?:Here is (?:the )?(?:list of )?candidates?(?: for (?:the )?current requisition)?[:\s]*)+",
        "",
        stripped,
        flags=re.IGNORECASE,
    ).strip()

    if cleaned != stripped:
        parsed = _try_parse_json_blob(cleaned)
        if parsed is not None:
            formatted = _json_value_to_markdown(parsed)
            if formatted:
                return formatted

    result = _replace_json_blobs(cleaned)

    # Drop leftover "Here is the list..." intros when a table follows
    result = re.sub(
        r"^Here is (?:the )?(?:list of )?candidates?(?: for (?:the )?current requisition)?[:\s]*\n+",
        "",
        result,
        flags=re.IGNORECASE,
    ).strip()

    return result or stripped
