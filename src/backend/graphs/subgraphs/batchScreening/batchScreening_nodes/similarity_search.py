"""
Node 1 — Similarity Search

Responsibilities:
1. Fetch the job description from the Requisition table (PostgreSQL).
2. Run a cosine similarity search in ChromaDB against all indexed CVs
   for this requisition, returning the top K most relevant candidates.
3. Populate state.job_description and state.top_candidates.

Candidates are identified by *source* (filename) throughout the pipeline.
"""

import sys
import logging
from pathlib import Path
from controllers.RequisitonController import RequisitionController
from ..batchScreening_state import BatchScreeningState, CandidateDoc
from models.database import AsyncSessionLocal
from stores.vectordb.load_vectordb import get_cv_vector_index

# from db import crud                              # noqa: E402
# from utils.load_vectordb import get_cv_vector_index  # noqa: E402

req_controller = RequisitionController()

logger = logging.getLogger(__name__)

# How many top CVs to retrieve from ChromaDB
TOP_K = 20


async def similarity_search_node(state: BatchScreeningState) -> BatchScreeningState:
    """
    Node 1: Fetch job description and retrieve top-K similar CVs from ChromaDB.

    Reads:
        state.requisition_id

    Writes:
        state.job_description  — text of the job description
        state.top_candidates   — list of CandidateDoc (up to TOP_K entries)

    Sets state.error on:
        - DB fetch failure
        - Requisition not found
        - ChromaDB search failure
        - Zero results returned
    """
    logger.info(f"[Node 1: similarity_search] requisition_id={state.requisition_id}")

    # ── 1. Fetch job description from PostgreSQL ──────────────────────────────
    try:
        async with AsyncSessionLocal() as db:
            # requisition = await crud.get_requisition_by_id(db, state.requisition_id)
            requisition = await req_controller.get_requisition(state.requisition_id, db)
    except Exception as exc:
        state.error = f"[Node 1] DB fetch failed: {exc}"
        logger.error(state.error)
        return state

    if not requisition:
        state.error = f"[Node 1] Requisition {state.requisition_id} not found"
        logger.error(state.error)
        return state

    state.job_description = requisition.description
    logger.info(
        f"[Node 1] Job description fetched: '{requisition.title}' "
        f"({len(state.job_description)} chars)"
    )

    # ── 2. Similarity search in ChromaDB ──────────────────────────────────────
    try:
        index = get_cv_vector_index()

        # similarity_search_with_score returns List[Tuple[Document, float]]
        # where float is the distance (lower = more similar for cosine distance)
        docs_with_scores = index.similarity_search_with_score(
            state.job_description,
            k=TOP_K,
            filter={"requisition_id": state.requisition_id},
        )
    except Exception as exc:
        state.error = f"[Node 1] ChromaDB search failed: {exc}"
        logger.error(state.error)
        return state

    if not docs_with_scores:
        state.error = (
            f"[Node 1] No indexed CVs found for requisition {state.requisition_id}. "
            "Make sure CVs have been vectorized before running batch screening."
        )
        logger.warning(state.error)
        return state

    # ── 3. Build CandidateDoc list ────────────────────────────────────────────
    candidates: list[CandidateDoc] = []
    for doc, score in docs_with_scores:
        source = doc.metadata.get("source")
        if not source:
            logger.warning(
                "[Node 1] CV document missing 'source' in metadata — skipping. "
                f"Metadata keys present: {list(doc.metadata.keys())}"
            )
            continue
        candidates.append(
            CandidateDoc(
                source=source,
                cv_text=doc.page_content,
                cosine_score=float(score),
            )
        )

    if not candidates:
        state.error = (
            "[Node 1] All retrieved documents were missing 'source' metadata. "
            "Re-index CVs with correct metadata."
        )
        logger.error(state.error)
        return state

    state.top_candidates = candidates
    logger.info(
        f"[Node 1] Retrieved {len(candidates)} candidate CVs "
        f"(cosine distances: {min(c.cosine_score for c in candidates):.4f} - "
        f"{max(c.cosine_score for c in candidates):.4f})"
    )

    return state
