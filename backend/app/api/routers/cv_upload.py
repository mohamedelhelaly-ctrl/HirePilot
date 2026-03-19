"""
CV Upload Router

POST /api/cvs/upload

Accepts one or more CV files (PDF or DOCX) together with a requisition_id.

Responsibilities:
1. Save each file to:
       backend/app/db/cvs/{requisition_id}/{original_filename}
   (directory is created automatically if it does not exist)
2. Call process_and_vectorize_cv() for each saved file so it is indexed
   in ChromaDB and becomes available for similarity search during batch
   screening.
3. Increment the requisition's new_candidate_counter for each successfully
   vectorized CV — this is what the scheduler watches to decide when to
   trigger screening.

Notes:
- No Candidate / Application DB rows are created here — those records are
  created during the batch-screening pipeline.
- Chroma document IDs are derived from requisition_id + filename stem,
  making re-uploads idempotent. The counter is still incremented on
  re-upload so the scheduler knows fresh data is available.
"""

import logging
from pathlib import Path
from typing import List

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from db.database import get_db
from db import crud
from utils.vectorize_cv import process_and_vectorize_cv

logger = logging.getLogger(__name__)

router = APIRouter()

# Root directory where CVs are persisted on disk
# Resolves to:  <repo>/backend/app/db/cvs/
_CV_ROOT = Path(__file__).resolve().parents[3] / "app" / "db" / "cvs"

ALLOWED_EXTENSIONS = {".pdf", ".docx"}


@router.post(
    "/upload",
    summary="Upload and vectorize CVs for a requisition",
    response_model=dict,
    status_code=status.HTTP_200_OK,
)
async def upload_cvs(
    requisition_id: int = Form(..., description="ID of the requisition these CVs belong to"),
    files: List[UploadFile] = File(..., description="One or more CV files (.pdf or .docx)"),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload one or more CV files for a given requisition.

    - Saves each file to `backend/app/db/cvs/{requisition_id}/`
    - Vectorizes and indexes each CV in ChromaDB
    - Increments new_candidate_counter for each successfully vectorized CV
    - Returns a per-file status report
    """
    if not files:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="At least one file must be provided.",
        )

    # Ensure storage directory exists
    save_dir = _CV_ROOT / str(requisition_id)
    save_dir.mkdir(parents=True, exist_ok=True)
    logger.info(
        f"[CV Upload] requisition_id={requisition_id} | "
        f"receiving {len(files)} file(s) → {save_dir}"
    )

    results = []

    for upload in files:
        filename = upload.filename or "unknown"
        suffix = Path(filename).suffix.lower()

        # ── Validate extension ────────────────────────────────────────────────
        if suffix not in ALLOWED_EXTENSIONS:
            logger.warning(f"[CV Upload] Rejected unsupported file: {filename}")
            results.append(
                {
                    "filename": filename,
                    "status": "rejected",
                    "reason": f"Unsupported file type '{suffix}'. Allowed: {sorted(ALLOWED_EXTENSIONS)}",
                }
            )
            continue

        dest_path = save_dir / filename

        # ── Save file to disk ─────────────────────────────────────────────────
        try:
            content = await upload.read()
            dest_path.write_bytes(content)
            logger.info(f"[CV Upload] Saved: {dest_path} ({len(content)} bytes)")
        except Exception as exc:
            logger.error(f"[CV Upload] Failed to save {filename}: {exc}")
            results.append(
                {"filename": filename, "status": "error", "reason": f"File save failed: {exc}"}
            )
            continue

        # ── Vectorize ─────────────────────────────────────────────────────────
        try:
            success = process_and_vectorize_cv(
                file_input=str(dest_path),
                requisition_id=requisition_id,
            )
        except Exception as exc:
            logger.error(f"[CV Upload] Vectorization error for {filename}: {exc}")
            results.append(
                {
                    "filename": filename,
                    "status": "error",
                    "reason": f"Vectorization raised an exception: {exc}",
                }
            )
            continue

        if success:
            # ── Increment counter ─────────────────────────────────────────────
            # Counter is the scheduler's signal that new CVs are ready.
            # We increment here regardless of whether this is a new CV or a
            # re-upload — re-uploads mean updated content and warrant re-screening.
            try:
                await crud.increment_requisition_counter(db, requisition_id, "candidate")
                logger.info(
                    f"[CV Upload] Counter incremented for requisition_id={requisition_id}"
                )
            except Exception as exc:
                # Non-fatal — CV is vectorized and usable; counter miss will be
                # caught on next upload or via manual trigger.
                logger.warning(
                    f"[CV Upload] Counter increment failed for requisition_id={requisition_id}: {exc}"
                )

            results.append(
                {
                    "filename": filename,
                    "status": "ok",
                    "saved_to": str(dest_path),
                }
            )
        else:
            results.append(
                {
                    "filename": filename,
                    "status": "error",
                    "reason": "Vectorization returned False — check CV content / logs.",
                }
            )

    ok_count = sum(1 for r in results if r["status"] == "ok")
    logger.info(
        f"[CV Upload] Done: {ok_count}/{len(results)} files vectorized successfully "
        f"(requisition_id={requisition_id})"
    )

    return {
        "requisition_id": requisition_id,
        "total": len(results),
        "succeeded": ok_count,
        "failed": len(results) - ok_count,
        "files": results,
    }