import os
import logging
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

# ==================== CONFIGURATION ====================
# Path where the model was saved by load_model.py
# Falls back to downloading from HuggingFace if local path not found
BASE_DIR = os.path.dirname(__file__)
MODEL_DIR = os.path.join(BASE_DIR, "encoder_model")
MODEL_NAME = os.getenv("EMBEDDING_MODEL_NAME", "BAAI/bge-m3")
DEVICE     = os.getenv("EMBEDDING_DEVICE", "cpu")

# ==================== SINGLETON STATE ====================
# Module-level variable — persists for the lifetime of the process
# None means "not loaded yet"
_embedding_model: SentenceTransformer | None = None


def get_embedding_model() -> SentenceTransformer:
    
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
