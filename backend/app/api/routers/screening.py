"""
Screening Router

Provides the HTTP entry point for triggering the batch screening pipeline.

POST /{requisition_id}/trigger
    - Checks screening_in_progress flag — returns 409 if already running
    - Invokes the main LangGraph orchestrator with intent="batch_screening"
    - Blocks until all 4 subgraph nodes complete (synchronous execution)
    - Fetches and returns the full screening report for the requisition:
        • Every candidate ever screened for this requisition
        • Their application with all scores and status
        • Detailed ScreeningResult (justifications, strengths, concerns)
        • ApplicationDetail rows (skills, education, roles)

Candidates are returned ordered by combined_score descending so the
top-ranked candidate is always first in the list.
"""

import logging
from datetime import datetime, timezone
from typing import Optional, List, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from db.database import get_db
from db import crud
from db.models import Application, ApplicationStatus
from graphs.main_graph import main_graph
from graphs.state import OrchestratorState

logger = logging.getLogger(__name__)

router = APIRouter()


# ── Response schemas ──────────────────────────────────────────────────────────

class CandidateOut(BaseModel):
    id: int
    full_name: str
    email: str
    phone: Optional[str] = None
    linkedin_url: Optional[str] = None
    lever_id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ApplicationDetailOut(BaseModel):
    id: int
    key: str
    value: Any
    relevance: Optional[str] = None
    extracted_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ApplicationOut(BaseModel):
    id: int
    lever_opportunity_id: str
    status: ApplicationStatus
    cv_url: Optional[str] = None
    combined_score: Optional[float] = None
    applied_at: datetime
    last_activity_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ScreeningResultOut(BaseModel):
    id: int
    score: float
    justification: Optional[str] = None
    recommended_action: Optional[str] = None
    key_strengths: Optional[List[str]] = None
    key_concerns: Optional[List[str]] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ScreenedCandidateOut(BaseModel):
    """Aggregated view of one candidate's screening record for a requisition."""
    candidate: CandidateOut
    application: ApplicationOut
    screening_result: Optional[ScreeningResultOut] = None
    application_details: List[ApplicationDetailOut] = []


class ScreeningRunSummary(BaseModel):
    candidates_scored_this_run: int
    candidates_saved_this_run: int
    top_candidate_source: Optional[str] = None
    top_candidate_application_id: Optional[int] = None
    top_candidate_combined_score: Optional[float] = None
    top_candidate_recommended_action: Optional[str] = None


class TriggerScreeningResponse(BaseModel):
    requisition_id: int
    triggered_at: datetime
    status: str  # "completed" | "failed"
    error: Optional[str] = None
    run_summary: Optional[ScreeningRunSummary] = None
    total_screened_candidates: int = 0
    candidates: List[ScreenedCandidateOut] = []


# ── Endpoint ──────────────────────────────────────────────────────────────────

@router.post(
    "/{requisition_id}/trigger",
    response_model=TriggerScreeningResponse,
    summary="Trigger batch screening for a requisition",
    description=(
        "Invokes the full batch screening pipeline (4-node LangGraph subgraph): "
        "similarity search → CV extraction → comparative scoring → DB persistence. "
        "Blocks until complete, then returns all screening results for this requisition. "
        "Returns 409 if a screening run is already in progress for this requisition."
    ),
)
async def trigger_screening(
    requisition_id: int,
    manual_trigger: bool = True,
    db: AsyncSession = Depends(get_db),
):
    triggered_at = datetime.now(timezone.utc)

    logger.info(
        f"[POST /screening/{requisition_id}/trigger] "
        f"Invoking main graph — manual_trigger={manual_trigger}"
    )

    # ── 0. Guard: check screening_in_progress ─────────────────────────────────
    requisition = await crud.get_requisition_by_id(db, requisition_id)
    if not requisition:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Requisition {requisition_id} not found.",
        )

    if requisition.screening_in_progress:
        logger.warning(
            f"[POST /screening/{requisition_id}/trigger] "
            "Rejected — screening already in progress"
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Screening is already in progress for requisition {requisition_id}. "
                "Please wait for the current run to complete before triggering again."
            ),
        )

    # ── 1. Set flag before running ────────────────────────────────────────────
    await crud.set_screening_in_progress(db, requisition_id, value=True)

    # ── 2. Run the LangGraph pipeline ─────────────────────────────────────────
    success = False
    try:
        graph_state = OrchestratorState(
            intent="batch_screening",
            requisition_id=requisition_id,
            manual_trigger=manual_trigger,
        )

        try:
            raw_state = await main_graph.ainvoke(graph_state)
            final_state: OrchestratorState = (
                raw_state
                if isinstance(raw_state, OrchestratorState)
                else OrchestratorState(**raw_state)
            )
        except Exception as exc:
            logger.error(
                f"[screening trigger] Graph raised unexpected exception: {exc}",
                exc_info=True,
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Screening pipeline failed with an unexpected error: {exc}",
            )

        # ── 3. Check graph-level error ─────────────────────────────────────────
        if final_state.error:
            logger.error(f"[screening trigger] Graph returned error: {final_state.error}")
            return TriggerScreeningResponse(
                requisition_id=requisition_id,
                triggered_at=triggered_at,
                status="failed",
                error=final_state.error,
            )

        success = True

        # ── 4. Build run summary ───────────────────────────────────────────────
        run_result: dict = final_state.result or {}
        top = run_result.get("top_candidate") or {}
        run_summary = ScreeningRunSummary(
            candidates_scored_this_run=run_result.get("candidates_scored", 0),
            candidates_saved_this_run=run_result.get("candidates_saved", 0),
            top_candidate_source=top.get("source"),
            top_candidate_application_id=top.get("application_id"),
            top_candidate_combined_score=top.get("combined_score"),
            top_candidate_recommended_action=top.get("recommended_action"),
        )

        # ── 5. Fetch ALL screened candidates for this requisition ──────────────
        query = (
            select(Application)
            .where(Application.requisition_id == requisition_id)
            .options(
                joinedload(Application.candidate),
                joinedload(Application.screening_result),
                selectinload(Application.details),
            )
            .order_by(desc(Application.combined_score))
        )
        result = await db.execute(query)
        applications = list(result.unique().scalars().all())

        # ── 6. Shape into response ─────────────────────────────────────────────
        screened: List[ScreenedCandidateOut] = []
        for app in applications:
            screened.append(
                ScreenedCandidateOut(
                    candidate=CandidateOut.model_validate(app.candidate),
                    application=ApplicationOut.model_validate(app),
                    screening_result=(
                        ScreeningResultOut.model_validate(app.screening_result)
                        if app.screening_result else None
                    ),
                    application_details=[
                        ApplicationDetailOut.model_validate(d) for d in app.details
                    ],
                )
            )

        logger.info(
            f"[screening trigger] Done — "
            f"run saved {run_summary.candidates_saved_this_run}, "
            f"total in DB for req {requisition_id}: {len(screened)}"
        )

        return TriggerScreeningResponse(
            requisition_id=requisition_id,
            triggered_at=triggered_at,
            status="completed",
            run_summary=run_summary,
            total_screened_candidates=len(screened),
            candidates=screened,
        )

    finally:
        # ── Always clear the flag ──────────────────────────────────────────────
        # Manual trigger resets the counter on success (same as scheduler).
        # On failure the counter is preserved so the scheduler can retry.
        try:
            await crud.set_screening_in_progress(
                db,
                requisition_id,
                value=False,
                reset_counter=success,
            )
        except Exception as exc:
            logger.error(
                f"[screening trigger] CRITICAL — could not clear screening_in_progress "
                f"for requisition_id={requisition_id}: {exc}. "
                "Requisition may be stuck. Investigate manually."
            )