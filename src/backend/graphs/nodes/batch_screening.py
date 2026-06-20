"""
Batch screening node - initiates the batch screening subgraph.

This node is the ENTRY POINT for the batch screening workflow.
It validates inputs, then invokes the batch screening subgraph.

Triggered by:
- Manual: HR clicks "Trigger Screening" button (manual_trigger=True)
- Automated: new_candidate_counter hits threshold (manual_trigger=False)
- Scheduled: 24-hour background job (manual_trigger=False)
"""
from ..state import OrchestratorState  # Import state schema
from ..subgraphs.batchScreening import batch_screening_subgraph, BatchScreeningState
from models.database import AsyncSessionLocal
from models.crud.requisition_crud import get_requisition_by_id, set_screening_in_progress
import logging  # For debug/info logging

# Create a logger instance for this module
# Logs will be prefixed with the module name for easy filtering
logger = logging.getLogger(__name__)


async def batch_screening_node(state: OrchestratorState) -> OrchestratorState:
    """
    Initiates the batch screening subgraph for a requisition.

    This node acts as a WRAPPER around the batch screening subgraph.
    It validates required context, invokes the subgraph, then maps the
    subgraph result back onto the orchestrator state.

    The batch screening subgraph runs 4 sequential nodes:
    1. similarity_search  — ChromaDB top-20 CV retrieval for the job description
    2. cv_extraction      — GROQ LLM structured data extraction per candidate (parallel)
    3. comparative_scoring — GROQ LLM comparative scoring of all candidates (single call)
    4. save_results       — PostgreSQL upsert (Application, ScreeningResult, ApplicationDetail)

    Args:
        state: Current orchestrator state
               REQUIRED: state.requisition_id must be set
               OPTIONAL: state.manual_trigger (logged for audit, not used by subgraph)

    Returns:
        Updated state with either:
        - state.result populated (if successful)
        - state.error populated (if validation failed or subgraph errored)
    """
    logger.info(
        f"Batch screening node triggered — requisition_id={state.requisition_id}, "
        f"manual_trigger={state.manual_trigger}, mode={state.screening_mode}"
    )

    # ── Input validation ──────────────────────────────────────────────────────
    if not state.requisition_id:
        logger.error("Batch screening triggered without requisition_id")
        state.error = "Missing requisition_id for batch screening"
        return state

    # ── Lock for manual runs (background runner acquires lock before invoke) ───
    lock_owned = False
    if state.intent != "background_job":
        async with AsyncSessionLocal() as db:
            requisition = await get_requisition_by_id(db, state.requisition_id)
            if requisition and requisition.screening_in_progress:
                state.error = "Screening already in progress for this requisition"
                logger.warning(state.error)
                return state
            if requisition:
                await set_screening_in_progress(db, state.requisition_id, value=True)
                lock_owned = True

    # ── Invoke the subgraph ───────────────────────────────────────────────────
    try:
        subgraph_input = BatchScreeningState(
            requisition_id=state.requisition_id,
            screening_mode=state.screening_mode or "new_candidates",
        )

        raw_result = await batch_screening_subgraph.ainvoke(subgraph_input)
        final = (
            raw_result
            if isinstance(raw_result, BatchScreeningState)
            else BatchScreeningState(**raw_result)
        )

    except Exception as exc:
        logger.error(f"Batch screening subgraph raised an unexpected exception: {exc}")
        state.error = f"Batch screening failed: {exc}"
        final = None
    finally:
        if lock_owned:
            async with AsyncSessionLocal() as db:
                try:
                    await set_screening_in_progress(db, state.requisition_id, value=False)
                except Exception as exc:
                    logger.error(
                        f"Failed to clear screening_in_progress for "
                        f"requisition_id={state.requisition_id}: {exc}"
                    )

    if final is None:
        return state

    # ── Map subgraph result back to orchestrator state ────────────────────────
    if final.error:
        logger.error(f"Batch screening subgraph returned error: {final.error}")
        state.error = final.error
        return state

    state.result = {
        "status":           "completed",
        "requisition_id":   state.requisition_id,
        "candidates_scored": len(final.comparative_scores),
        "candidates_saved":  final.saved_count,
        "top_candidate": (
            {
                "source":         final.comparative_scores[0].source,
                "application_id": final.comparative_scores[0].application_id,
                "combined_score": final.comparative_scores[0].combined_score,
            }
            if final.comparative_scores else None
        ),
        "manual_trigger": state.manual_trigger,
    }

    logger.info(
        f"Batch screening completed — {final.saved_count} candidates saved, "
        f"requisition_id={state.requisition_id}"
    )

    return state
