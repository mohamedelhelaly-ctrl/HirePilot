"""
Static competency-based interview (CBI) questions using the STAR method.

Returned when HR generates CBI questions for a candidate — no LLM call.
"""

from typing import Dict, List

from sqlalchemy.ext.asyncio import AsyncSession

from models.crud import get_application_by_id, update_application
from models.schemas.application_schemas import ApplicationUpdate

# STAR = Situation, Task, Action, Result
STATIC_STAR_CBI_QUESTIONS: List[Dict[str, str]] = [
    {
        "question": "Tell me about a time you faced a significant challenge or problem at work. How did you handle it?",
        "competency": "Problem Solving",
        "star_guide": "Situation: Set the context. Task: Your responsibility. Action: Steps you took. Result: Outcome and impact.",
    },
    {
        "question": "Describe a situation where you had a conflict or disagreement with a colleague or manager. What did you do?",
        "competency": "Conflict Resolution",
        "star_guide": "Situation: The conflict context. Task: What needed to be resolved. Action: How you addressed it. Result: Resolution and relationship outcome.",
    },
    {
        "question": "Give an example of when you took initiative or led a project without being formally asked.",
        "competency": "Leadership & Initiative",
        "star_guide": "Situation: Background. Task: The goal you set. Action: How you mobilized others or drove progress. Result: What was achieved.",
    },
    {
        "question": "Tell me about a time you failed or made a mistake. What happened and what did you learn?",
        "competency": "Accountability & Growth",
        "star_guide": "Situation: What went wrong. Task: What was at stake. Action: How you responded and fixed it. Result: Lessons learned and changes made.",
    },
    {
        "question": "Describe a time when you had to meet a tight deadline or prioritize competing demands.",
        "competency": "Time Management",
        "star_guide": "Situation: Pressure or competing priorities. Task: What had to be delivered. Action: How you prioritized and executed. Result: Delivery and trade-offs.",
    },
    {
        "question": "Tell me about a time you worked on a difficult team project. What was your role and contribution?",
        "competency": "Teamwork",
        "star_guide": "Situation: Team context. Task: Shared goal. Action: Your specific contribution. Result: Team outcome.",
    },
    {
        "question": "Give an example of when you had to adapt quickly to a major change at work.",
        "competency": "Adaptability",
        "star_guide": "Situation: What changed. Task: New expectations. Action: How you adjusted. Result: How you and the team moved forward.",
    },
    {
        "question": "Tell me about a time you went above and beyond what was expected in your role.",
        "competency": "Ownership",
        "star_guide": "Situation: Normal expectations. Task: The extra need you saw. Action: What you did beyond the minimum. Result: Impact on team or business.",
    },
]


async def generate_cbi_questions_for_application(
    db: AsyncSession,
    application_id: int,
    *,
    force: bool = False,
) -> List[Dict[str, str]]:
    """Return static STAR CBI questions, persisting them on the application once."""
    application = await get_application_by_id(db, application_id)
    if application is None:
        raise ValueError(f"Application with ID {application_id} not found.")

    if application.cbi_questions and not force:
        return application.cbi_questions

    questions = list(STATIC_STAR_CBI_QUESTIONS)
    saved = await update_application(
        db,
        application_id,
        ApplicationUpdate(cbi_questions=questions),
    )
    if saved is None:
        raise ValueError(f"Failed to persist CBI questions for application {application_id}.")

    return questions
