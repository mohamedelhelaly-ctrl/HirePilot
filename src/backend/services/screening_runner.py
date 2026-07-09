"""
Shared screening runner — used by APScheduler and post-interview triggers.

Acquires the screening_in_progress lock, invokes the batch screening graph,
and clears the lock when done. Counter resets are handled by save_results (Node 4).
"""

import logging
from typing import Literal

from models.database import AsyncSessionLocal
from models.crud.requisition_crud import get_requisition_by_id, set_screening_in_progress
from graphs.maingraph import main_graph
from graphs.state import OrchestratorState

logger = logging.getLogger(__name__)

ScreeningMode = Literal["new_candidates", "interview_rescreen"]


async def run_screening(
    requisition_id: int,
    mode: ScreeningMode,
    *,
    manual_trigger: bool = False,
) -> bool:
    """
    Run batch screening for a single requisition.

    Returns True on success, False on any failure or if already in progress.
    """
    logger.info(
        f"[ScreeningRunner] Starting mode={mode} requisition_id={requisition_id} "
        f"manual_trigger={manual_trigger}"
    )

    async with AsyncSessionLocal() as db:
        requisition = await get_requisition_by_id(db, requisition_id)
        if not requisition:
            logger.error(f"[ScreeningRunner] Requisition {requisition_id} not found")
            return False
        if requisition.screening_in_progress:
            logger.info(
                f"[ScreeningRunner] Skipping requisition_id={requisition_id} — "
                "screening already in progress"
            )
            return False
        try:
            await set_screening_in_progress(db, requisition_id, value=True)
        except Exception as exc:
            logger.error(
                f"[ScreeningRunner] Could not set screening_in_progress=True "
                f"for requisition_id={requisition_id}: {exc}"
            )
            return False

    graph_state = OrchestratorState(
        intent="background_job",
        requisition_id=requisition_id,
        screening_mode=mode,
        manual_trigger=manual_trigger,
    )

    success = False
    try:
        raw_result = await main_graph.ainvoke(graph_state)
        final_state: OrchestratorState = (
            raw_result
            if isinstance(raw_result, OrchestratorState)
            else OrchestratorState(**raw_result)
        )
        if final_state.error:
            logger.error(
                f"[ScreeningRunner] Graph returned error for "
                f"requisition_id={requisition_id}: {final_state.error}"
            )
        else:
            success = True
            result = final_state.result or {}
            logger.info(
                f"[ScreeningRunner] Complete mode={mode} requisition_id={requisition_id} — "
                f"scored={result.get('candidates_scored', 0)}, "
                f"saved={result.get('candidates_saved', 0)}"
            )
    except Exception as exc:
        logger.error(
            f"[ScreeningRunner] Graph raised unexpected exception for "
            f"requisition_id={requisition_id}: {exc}",
            exc_info=True,
        )

    async with AsyncSessionLocal() as db:
        try:
            await set_screening_in_progress(db, requisition_id, value=False)
            logger.info(
                f"[ScreeningRunner] Flag cleared for requisition_id={requisition_id} "
                f"(success={success})"
            )
        except Exception as exc:
            logger.error(
                f"[ScreeningRunner] CRITICAL — could not clear screening_in_progress "
                f"for requisition_id={requisition_id}: {exc}. "
                "Requisition may be stuck. Investigate manually."
            )

    return success
