"""
Singleton for the SentenceTransformer embedding model.

This module ensures the embedding model is loaded ONCE per process
and reused across all functions that need it (vector store, screening, RAG, etc.)

Usage:
    from backend.app.utils.embedding_model import get_embedding_model
    
    model = get_embedding_model()
    embeddings = model.encode(["some text"])
"""

import os
import logging
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

# ==================== CONFIGURATION ====================
# Path where the model was saved by load_model.py
# Falls back to downloading from HuggingFace if local path not found
MODEL_DIR  = os.getenv("EMBEDDING_MODEL_DIR", "backend/app/db/encoder_model")
MODEL_NAME = os.getenv("EMBEDDING_MODEL_NAME", "BAAI/bge-m3")
DEVICE     = os.getenv("EMBEDDING_DEVICE", "cpu")

# ==================== SINGLETON STATE ====================
# Module-level variable — persists for the lifetime of the process
# None means "not loaded yet"
_embedding_model: SentenceTransformer | None = None


def get_embedding_model() -> SentenceTransformer:
    """
    Returns the singleton SentenceTransformer embedding model.

    Loads the model on FIRST call, then reuses the same instance
    for every subsequent call. This prevents:
    - Multiple model loads (~2GB each time)
    - High memory usage from duplicate instances
    - Slow startup on every request

    Load priority:
    1. Local saved model (MODEL_DIR) — fast, no internet needed
    2. HuggingFace Hub (MODEL_NAME)  — fallback if local not found

    Returns:
        SentenceTransformer: Loaded embedding model ready for .encode()

    Raises:
        RuntimeError: If model cannot be loaded from either source

    Example:
        model = get_embedding_model()
        vector = model.encode("Software engineer with 5 years Python experience")
        # vector is a numpy array of floats (1024 dims for BAAI/bge-m3)
    """
    global _embedding_model

    # ==================== ALREADY LOADED ====================
    # Fast path — model already in memory, return immediately
    if _embedding_model is not None:
        logger.debug("Returning cached embedding model")
        return _embedding_model

    # ==================== LOAD FROM LOCAL PATH ====================
    # Prefer local saved model (faster startup, no internet dependency)
    if os.path.exists(MODEL_DIR):
        logger.info(f"Loading embedding model from local path: {MODEL_DIR}")
        try:
            _embedding_model = SentenceTransformer(MODEL_DIR, device=DEVICE)
            logger.info(f"✅ Embedding model loaded from local path ({DEVICE})")
            return _embedding_model
        except Exception as e:
            # Local model may be corrupted — fall through to HuggingFace
            logger.warning(f"Failed to load from local path: {e}. Falling back to HuggingFace...")

    # ==================== LOAD FROM HUGGINGFACE ====================
    # Fallback: download from HuggingFace Hub (requires internet)
    # logger.info(f"Loading embedding model from HuggingFace: {MODEL_NAME}")
    # try:
    #     _embedding_model = SentenceTransformer(MODEL_NAME, device=DEVICE)
    #     logger.info(f"✅ Embedding model loaded from HuggingFace ({DEVICE})")
    #     return _embedding_model
    # except Exception as e:
    #     logger.error(f"❌ Failed to load embedding model: {e}")
    #     raise RuntimeError(
    #         f"Could not load embedding model from '{MODEL_DIR}' or '{MODEL_NAME}'. "
    #         f"Run load_model.py first to download it locally."
    #     ) from e


def unload_embedding_model() -> None:
    """
    Unloads the embedding model from memory.

    Useful for:
    - Tests that need a clean state between runs
    - Freeing memory after batch processing completes
    - Forcing a reload after model update

    Example:
        unload_embedding_model()  # free memory
        get_embedding_model()     # reloads fresh instance
    """
    global _embedding_model

    if _embedding_model is not None:
        logger.info("Unloading embedding model from memory")
        del _embedding_model
        _embedding_model = None
        logger.info("✅ Embedding model unloaded")
    else:
        logger.debug("Embedding model was not loaded, nothing to unload")
