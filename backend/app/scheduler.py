"""
Screening Scheduler

Runs a single background job that periodically checks for requisitions
that have accumulated enough new CVs to warrant a screening run.

Trigger condition (checked every SCREENING_POLL_INTERVAL_MINUTES):
    requisition.is_active = True
    AND requisition.screening_in_progress = False
    AND requisition.new_candidate_counter >= requisition.new_candidate_threshold

For each qualifying requisition the job:
    1. Sets screening_in_progress = True  (blocks concurrent runs)
    2. Invokes the main LangGraph orchestrator with intent="background_job"
    3. On success: resets counter + updates last_screening_at + clears flag
    4. On failure: clears the flag WITHOUT resetting the counter so the
       next poll picks it up again and retries automatically

Requisitions are processed SEQUENTIALLY — one at a time — to avoid
hammering the LLM API with simultaneous batch calls when multiple
requisitions hit their threshold at the same time.

Environment variables:
    SCREENING_POLL_INTERVAL_MINUTES — how often to poll (default: 15)
"""

import asyncio
import logging
import os
from datetime import datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from db.database import AsyncSessionLocal
from db import crud
from graphs.main_graph import main_graph
from graphs.state import OrchestratorState

logger = logging.getLogger(__name__)

_POLL_INTERVAL = int(os.getenv("SCREENING_POLL_INTERVAL_MINUTES", "15"))


async def _run_screening_for_requisition(requisition_id: int) -> bool:
    """
    Invoke the screening graph for a single requisition.

    Returns True on success, False on any failure.
    The caller is responsible for the screening_in_progress flag.
    """
    logger.info(f"[Scheduler] Starting screening for requisition_id={requisition_id}")

    graph_state = OrchestratorState(
        intent="background_job",
        requisition_id=requisition_id,
        manual_trigger=False,
    )

    try:
        raw_result = await main_graph.ainvoke(graph_state)
        final_state: OrchestratorState = (
            raw_result
            if isinstance(raw_result, OrchestratorState)
            else OrchestratorState(**raw_result)
        )
    except Exception as exc:
        logger.error(
            f"[Scheduler] Graph raised unexpected exception for "
            f"requisition_id={requisition_id}: {exc}",
            exc_info=True,
        )
        return False

    if final_state.error:
        logger.error(
            f"[Scheduler] Graph returned error for requisition_id={requisition_id}: "
            f"{final_state.error}"
        )
        return False

    result = final_state.result or {}
    logger.info(
        f"[Scheduler] Screening complete for requisition_id={requisition_id} — "
        f"scored={result.get('candidates_scored', 0)}, "
        f"saved={result.get('candidates_saved', 0)}"
    )
    return True


async def screening_poll_job() -> None:
    """
    The scheduled job function — called every SCREENING_POLL_INTERVAL_MINUTES.

    Finds all requisitions ready for screening and processes them one by one.
    Each requisition is wrapped in its own try/finally so a failure on one
    never blocks the others.
    """
    logger.info("[Scheduler] Poll tick — checking for requisitions ready for screening")

    async with AsyncSessionLocal() as db:
        try:
            ready = await crud.get_requisitions_ready_for_screening(db)
        except Exception as exc:
            logger.error(f"[Scheduler] DB query failed during poll: {exc}", exc_info=True)
            return

    if not ready:
        logger.debug("[Scheduler] No requisitions ready for screening this tick")
        return

    logger.info(
        f"[Scheduler] {len(ready)} requisition(s) ready: "
        f"{[r.id for r in ready]}"
    )

    # Process sequentially — one at a time to avoid concurrent LLM batch calls
    for req in ready:
        requisition_id = req.id

        # ── Mark as in-progress ───────────────────────────────────────────────
        async with AsyncSessionLocal() as db:
            try:
                await crud.set_screening_in_progress(db, requisition_id, value=True)
            except Exception as exc:
                logger.error(
                    f"[Scheduler] Could not set screening_in_progress=True for "
                    f"requisition_id={requisition_id}: {exc}"
                )
                continue  # skip this req — don't run without the lock

        # ── Run the graph ─────────────────────────────────────────────────────
        success = False
        try:
            success = await _run_screening_for_requisition(requisition_id)
        finally:
            # ── Always clear the flag ─────────────────────────────────────────
            # On success: reset counter + update last_screening_at
            # On failure: clear flag but KEEP counter so next poll retries
            async with AsyncSessionLocal() as db:
                try:
                    await crud.set_screening_in_progress(
                        db,
                        requisition_id,
                        value=False,
                        reset_counter=success,
                    )
                    logger.info(
                        f"[Scheduler] Flag cleared for requisition_id={requisition_id} "
                        f"(success={success}, counter_reset={success})"
                    )
                except Exception as exc:
                    logger.error(
                        f"[Scheduler] CRITICAL — could not clear screening_in_progress "
                        f"for requisition_id={requisition_id}: {exc}. "
                        "Requisition may be stuck. Investigate manually."
                    )


def create_scheduler() -> AsyncIOScheduler:
    """
    Build and return the APScheduler AsyncIOScheduler instance.

    The scheduler is NOT started here — call scheduler.start() in the
    FastAPI lifespan so it runs on the same event loop as the app.
    """
    scheduler = AsyncIOScheduler()

    scheduler.add_job(
        screening_poll_job,
        trigger=IntervalTrigger(minutes=_POLL_INTERVAL),
        id="screening_poll",
        name=f"Screening poll (every {_POLL_INTERVAL} min)",
        replace_existing=True,
        # Fire immediately on startup so we don't wait a full interval
        # before the first check after a server restart.
        next_run_time=datetime.now(timezone.utc),
    )

    logger.info(
        f"[Scheduler] Configured — poll interval={_POLL_INTERVAL} min, "
        f"first run: immediate on startup"
    )
    return scheduler


# ── Singleton instance ────────────────────────────────────────────────────────
# Created once at import time. Started/stopped by the FastAPI lifespan.
scheduler = create_scheduler()