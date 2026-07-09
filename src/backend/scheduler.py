"""
Screening Scheduler

Runs a background job that periodically checks for requisitions ready for
automated batch screening (new CVs) or interview-triggered rescreening.

Trigger conditions (checked every SCREENING_POLL_INTERVAL_MINUTES):
    New-CV screening:
        is_active AND NOT screening_in_progress
        AND new_candidate_counter >= new_candidate_threshold

    Interview rescreen:
        is_active AND NOT screening_in_progress
        AND every screened candidate has a completed interview
        AND new interview activity since last_screening_at

Requisitions are processed sequentially — candidate-ready first, then
interview-ready — to avoid hammering the LLM API with concurrent batch calls.

Environment variables:
    SCREENING_POLL_INTERVAL_MINUTES — poll interval (default: 15)
"""

import logging
from datetime import datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from helpers.config import get_settings
from models.database import AsyncSessionLocal
from models.crud.requisition_crud import (
    get_requisitions_ready_for_screening,
    get_requisitions_ready_for_interview_rescreen,
)
from services.screening_runner import run_screening

logger = logging.getLogger(__name__)

_POLL_INTERVAL = get_settings().SCREENING_POLL_INTERVAL_MINUTES


async def screening_poll_job() -> None:
    """Find qualifying requisitions and process them one at a time."""
    logger.info("[Scheduler] Poll tick — checking for requisitions ready for screening")

    async with AsyncSessionLocal() as db:
        try:
            candidate_ready = await get_requisitions_ready_for_screening(db)
            interview_ready = await get_requisitions_ready_for_interview_rescreen(db)
        except Exception as exc:
            logger.error(f"[Scheduler] DB query failed during poll: {exc}", exc_info=True)
            return

    if not candidate_ready and not interview_ready:
        logger.debug("[Scheduler] No requisitions ready this tick")
        return

    if candidate_ready:
        logger.info(
            f"[Scheduler] {len(candidate_ready)} requisition(s) ready for new-CV screening: "
            f"{[r.id for r in candidate_ready]}"
        )
    if interview_ready:
        logger.info(
            f"[Scheduler] {len(interview_ready)} requisition(s) ready for interview rescreen: "
            f"{[r.id for r in interview_ready]}"
        )

    for req in candidate_ready:
        try:
            await run_screening(req.id, "new_candidates")
        except Exception as exc:
            logger.error(
                f"[Scheduler] Candidate screening failed for requisition_id={req.id}: {exc}",
                exc_info=True,
            )

    for req in interview_ready:
        try:
            await run_screening(req.id, "interview_rescreen")
        except Exception as exc:
            logger.error(
                f"[Scheduler] Interview rescreen failed for requisition_id={req.id}: {exc}",
                exc_info=True,
            )


def create_scheduler() -> AsyncIOScheduler:
    """Build and return the APScheduler instance (not started)."""
    scheduler = AsyncIOScheduler()

    scheduler.add_job(
        screening_poll_job,
        trigger=IntervalTrigger(minutes=_POLL_INTERVAL),
        id="screening_poll",
        name=f"Screening poll (every {_POLL_INTERVAL} min)",
        replace_existing=True,
        next_run_time=datetime.now(timezone.utc),
    )

    logger.info(
        f"[Scheduler] Configured — poll interval={_POLL_INTERVAL} min, "
        f"first run: immediate on startup"
    )
    return scheduler


scheduler = create_scheduler()
