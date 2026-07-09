"""
Build rich candidate + requisition context for tailored interview question generation.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from models.crud import (
    get_application_by_id,
    get_application_details,
    get_requisition_by_id,
)


@dataclass
class ApplicationQuestionContext:
    application_id: int
    candidate_name: str
    requisition_title: str
    job_description: str
    years_of_experience: float | None
    combined_score: float | None
    screening_justification: str | None
    cv_details_text: str


def _format_detail_value(value: Any) -> str:
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, indent=2)
    return str(value)


def format_application_details(details: list) -> str:
    """Serialize application detail records into a readable CV profile section."""
    if not details:
        return "No structured CV profile is available for this candidate yet."

    lines: list[str] = []
    for detail in details:
        lines.append(f"### {detail.key}\n{_format_detail_value(detail.value)}")

    return "\n\n".join(lines)


async def load_application_question_context(
    db: AsyncSession,
    application_id: int,
) -> ApplicationQuestionContext:
    application = await get_application_by_id(db, application_id, include_relations=True)
    if application is None:
        raise ValueError(f"Application with ID {application_id} not found.")

    requisition = await get_requisition_by_id(db, application.requisition_id)
    if requisition is None:
        raise ValueError(
            f"Requisition with ID {application.requisition_id} not found for application {application_id}."
        )

    details = await get_application_details(db, application_id)
    candidate_name = (
        application.candidate.full_name
        if getattr(application, "candidate", None)
        else "Candidate"
    )

    screening_justification = None
    screening = getattr(application, "screening_result", None)
    if screening is not None and getattr(screening, "justification", None):
        screening_justification = screening.justification

    return ApplicationQuestionContext(
        application_id=application_id,
        candidate_name=candidate_name,
        requisition_title=requisition.title or "",
        job_description=requisition.description or "",
        years_of_experience=application.years_of_experience,
        combined_score=application.combined_score,
        screening_justification=screening_justification,
        cv_details_text=format_application_details(details),
    )


def build_candidate_jd_context_block(ctx: ApplicationQuestionContext) -> str:
    """Shared context block injected into tech and CBI generation prompts."""
    experience = (
        f"{ctx.years_of_experience:.1f} years"
        if ctx.years_of_experience is not None
        else "Not specified"
    )
    score = (
        f"{ctx.combined_score:.1f}/100"
        if ctx.combined_score is not None
        else "Not screened yet"
    )
    screening = (
        ctx.screening_justification.strip()
        if ctx.screening_justification
        else "No screening summary available."
    )

    return (
        f"CANDIDATE NAME: {ctx.candidate_name}\n"
        f"APPLICATION ID: {ctx.application_id}\n"
        f"REQUISITION TITLE: {ctx.requisition_title}\n"
        f"TOTAL EXPERIENCE: {experience}\n"
        f"SCREENING SCORE: {score}\n\n"
        f"JOB DESCRIPTION:\n{ctx.job_description}\n\n"
        f"SCREENING SUMMARY (fit vs this role):\n{screening}\n\n"
        f"CANDIDATE CV PROFILE (extracted for this application only):\n{ctx.cv_details_text}\n"
    )
