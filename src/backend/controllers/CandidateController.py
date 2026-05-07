from typing import List, Optional
from .BaseController import BaseController
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends, HTTPException, UploadFile, status, File, Form
from pathlib import Path
import logging
logger = logging.getLogger(__name__)
from stores.vectordb.vectorize_cv import process_and_vectorize_cv
BASE_DIR = Path(__file__).resolve()

for parent in BASE_DIR.parents:
    if (parent / "src").exists():
        PROJECT_ROOT = parent
        break

_CV_ROOT = PROJECT_ROOT / "src" / "backend" / "assets" / "cvs"
ALLOWED_EXTENSIONS = {".pdf", ".docx"}

from models.schemas.candidate_schemas import (
    Candidate,
    CandidateCreate,
    CandidateUpdate,
)
from models.crud import (
    create_candidate,
    list_candidates,
    get_candidate_by_id,
    get_candidate_by_email,
    get_candidate_by_lever_id,
    get_or_create_candidate,
    get_candidates_by_requisition_id,
    increment_requisition_counter,
)


class CandidateController(BaseController):
    def __init__(self):
        super().__init__()

    async def create_candidate(
        self,
        request: CandidateCreate,
        db: AsyncSession,
    ) -> Candidate:
        try:
            candidate = await create_candidate(db, request)
            return candidate
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create candidate: {exc}"
            )

    async def list_candidates(
        self,
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Candidate]:
        return await list_candidates(db, skip=skip, limit=limit)

    async def get_candidate(
        self,
        candidate_id: int,
        db: AsyncSession,
    ) -> Candidate:
        candidate = await get_candidate_by_id(db, candidate_id)
        if not candidate:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Candidate with ID {candidate_id} not found"
            )
        return candidate
    
    async def get_candidate_by_email(
        self,
        db: AsyncSession,
        email: str
    )-> Optional[Candidate]:
        return await get_candidate_by_email(db, email)

    async def update_candidate(
        self,
        candidate_id: int,
        updates: CandidateUpdate,
        db: AsyncSession,
    ) -> Candidate:
        candidate = await get_candidate_by_id(db, candidate_id)
        if not candidate:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Candidate with ID {candidate_id} not found"
            )

        update_data = updates.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(candidate, field, value)

        await db.commit()
        await db.refresh(candidate)
        return candidate

    async def get_candidates_by_requisition(
        self,
        requisition_id: int,
        db: AsyncSession,
    ) -> list[Candidate]:
        return await get_candidates_by_requisition_id(db, requisition_id)
    
    async def get_or_create_candidate(
        self,
        db: AsyncSession,
        candidate: CandidateCreate
    ) -> Candidate:
        return await get_or_create_candidate(db, candidate)
    
#########################################################
    async def upload_cvs(
            self,
            db: AsyncSession,
            requisition_id: int = Form(..., description="ID of the requisition these CVs belong to"),
            files: List[UploadFile] = File(..., description="One or more CV files (.pdf or .docx)"),
    ):
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
                    await increment_requisition_counter(db, requisition_id, "candidate")
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