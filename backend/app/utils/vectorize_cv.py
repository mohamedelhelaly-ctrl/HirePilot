"""
CV Vectorization Utility

Extracts text from a CV file (PDF or DOCX) and stores it as a single
embedding in ChromaDB, linked to the application via metadata.

This is called:
- During batch screening (after CVs are downloaded from Lever)
- When a new application arrives via webhook

Each CV is stored as ONE chunk (full document) to preserve
context for cosine similarity scoring against the job description.
"""

import os
import logging
import tempfile
from typing import Any

from langchain_core.documents import Document

from .text_extraction import extract_text_from_pdf, extract_text_from_docx
from .load_vectordb import get_cv_vector_index

logger = logging.getLogger(__name__)

# Minimum character threshold — CVs shorter than this are likely corrupt/empty
MIN_CV_LENGTH = 50


def process_and_vectorize_cv(
    file_input: Any,
    requisition_id: int,
) -> bool:
    """
    Extracts text from a CV and stores the full document as a single
    embedding in ChromaDB.

    Accepts either:
    - A file path (str) — CV already saved to disk (e.g. downloaded from Lever)
    - An UploadedFile object — CV uploaded directly via API (FastAPI UploadFile)

    Does NOT save the file to disk — assumes caller handles persistence.
    Supports: .pdf, .docx

    The CV is stored as ONE embedding (not chunked) so that cosine similarity
    against the job description embedding reflects the whole candidate profile.

    Candidate and Application IDs are NOT stored at this stage — those records
    are created in the database only when batch screening runs.  The Chroma
    document ID is derived deterministically from requisition_id + filename so
    that re-uploads are idempotent.

    Metadata stored with each embedding:
    - requisition_id: links back to the requisitions table
    - source: original filename (used by downstream nodes to identify the file)

    Args:
        file_input:     File path (str) or FastAPI UploadFile object
        requisition_id: DB ID of the requisition this CV belongs to

    Returns:
        True  — vectorization succeeded
        False — extraction failed, content too short, or unsupported format
    """

    # ==================== RESOLVE FILE PATH ====================
    # Normalize both input types to a local file path for text extraction

    if isinstance(file_input, str):
        # Already a path — use directly
        file_path = file_input
        filename = os.path.basename(file_path)
        _temp_file_path = None  # nothing to clean up
    else:
        # FastAPI UploadFile — write to a temp file for processing
        uploaded_file = file_input
        filename = uploaded_file.filename
        file_extension = os.path.splitext(filename)[1].lower()

        # NamedTemporaryFile with delete=False so we can close and still read it
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=file_extension)
        try:
            uploaded_file.file.seek(0)        # reset pointer in case it was read before
            tmp.write(uploaded_file.file.read())
        finally:
            tmp.close()

        file_path = tmp.name
        _temp_file_path = file_path           # remember to clean up later

    # ==================== TEXT EXTRACTION ====================
    try:
        logger.info(
            f"Extracting text from CV: {filename} "
            f"(requisition_id={requisition_id})"
        )

        file_extension = os.path.splitext(filename)[1].lower()

        if file_extension == ".pdf":
            extracted_pages = extract_text_from_pdf(file_path)
        elif file_extension == ".docx":
            extracted_pages = extract_text_from_docx(file_path)
        else:
            logger.error(
                f"Unsupported file type '{file_extension}' for CV: {filename}"
            )
            return False

        # ==================== VALIDATE CONTENT ====================
        # Guard against empty or corrupt files before attempting vectorization

        if not extracted_pages:
            logger.error(f"No text extracted from CV: {filename}")
            return False

        full_cv_text = " ".join(
            page["text"] for page in extracted_pages if page.get("text")
        )

        if len(full_cv_text.strip()) < MIN_CV_LENGTH:
            logger.error(
                f"CV content too short ({len(full_cv_text)} chars) — "
                f"skipping vectorization for {filename}"
            )
            return False

        # ==================== BUILD SINGLE DOCUMENT ====================
        # Combine all pages into one string — stored as a single Chroma document
        # This preserves full context for cosine similarity against job description

        combined_text = "\n\n".join(
            page["text"].strip()
            for page in extracted_pages
            if page.get("text", "").strip()
        )

        document = Document(
            page_content=combined_text,
            metadata={
                "requisition_id": requisition_id,   # FK → requisitions table
                "source":         filename,          # original filename
            },
        )

        # ==================== VECTORIZE & STORE ====================
        # Use the singleton Chroma instance — embedding happens inside add_documents()
        # via SentenceTransformerEmbeddingWrapper → get_embedding_model()

        vector_index = get_cv_vector_index()

        # Stable Chroma doc ID: re-uploading the same CV for the same
        # requisition overwrites rather than duplicating the embedding.
        doc_id = f"req_{requisition_id}__{os.path.splitext(filename)[0]}"

        vector_index.add_documents(
            documents=[document],
            ids=[doc_id],
        )

        logger.info(
            f"✅ CV vectorized and stored: {filename} "
            f"(doc_id={doc_id}, chars={len(combined_text)})"
        )
        return True

    except Exception as e:
        logger.error(
            f"❌ Failed to vectorize CV {filename} "
            f"(requisition_id={requisition_id}): {e}",
            exc_info=True,
        )
        return False

    finally:
        # ==================== CLEANUP ====================
        # Remove temp file if we created one (UploadFile path)
        if _temp_file_path and os.path.exists(_temp_file_path):
            os.unlink(_temp_file_path)
            logger.debug(f"Cleaned up temp file: {_temp_file_path}")


def delete_cv_embedding(application_id: int) -> bool:
    """
    Removes a CV embedding from ChromaDB by application_id.

    Used when:
    - An application is withdrawn or deleted
    - A CV is re-uploaded (delete old before re-vectorizing)

    Args:
        application_id: DB ID of the application whose embedding to remove

    Returns:
        True  — deletion succeeded or document didn't exist
        False — unexpected error during deletion
    """
    try:
        vector_index = get_cv_vector_index()
        doc_id = f"application_{application_id}"

        vector_index.delete(ids=[doc_id])

        logger.info(f"✅ CV embedding deleted for application_id={application_id}")
        return True

    except Exception as e:
        logger.error(
            f"❌ Failed to delete CV embedding for application_id={application_id}: {e}",
            exc_info=True,
        )
        return False
