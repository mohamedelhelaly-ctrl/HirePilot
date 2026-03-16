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
from ..subgraphs.batch_screening.graph import batch_screening_subgraph
from ..subgraphs.batch_screening.state import BatchScreeningState
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
        f"manual_trigger={state.manual_trigger}"
    )

    # ── Input validation ──────────────────────────────────────────────────────
    if not state.requisition_id:
        logger.error("Batch screening triggered without requisition_id")
        state.error = "Missing requisition_id for batch screening"
        return state

    # ── Invoke the subgraph ───────────────────────────────────────────────────
    try:
        subgraph_input = BatchScreeningState(requisition_id=state.requisition_id)

        # ainvoke is the async variant — required because subgraph nodes are async
        # LangGraph ainvoke returns the final state as a plain dict, not a Pydantic
        # model instance, so we reconstruct BatchScreeningState from it.
        raw_result = await batch_screening_subgraph.ainvoke(subgraph_input)
        final = (
            raw_result
            if isinstance(raw_result, BatchScreeningState)
            else BatchScreeningState(**raw_result)
        )

    except Exception as exc:
        logger.error(f"Batch screening subgraph raised an unexpected exception: {exc}")
        state.error = f"Batch screening failed: {exc}"
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
                "source":             final.comparative_scores[0].source,
                "application_id":     final.comparative_scores[0].application_id,
                "combined_score":     final.comparative_scores[0].combined_score,
                "recommended_action": final.comparative_scores[0].recommended_action,
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
