"""
Centralized CV Vector Store Singleton
Single source of truth for CV vectorization ChromaDB instance

This module provides a singleton ChromaDB instance for CV vectorization,
ensuring only one connection per process and preventing duplicate instances.
"""
import os
import logging
from dotenv import load_dotenv
from langchain_community.vectorstores import Chroma

# Import the embedding model singleton — shared across all modules
from .embedding_model import get_embedding_model

load_dotenv()

logger = logging.getLogger(__name__)

# ==================== SINGLETON STATE ====================
# Module-level variable — persists for the lifetime of the process
_CV_VECTOR_INDEX: Chroma | None = None


class SentenceTransformerEmbeddingWrapper:
    """
    Wraps SentenceTransformer to match LangChain's embedding interface.

    LangChain's Chroma expects an object with:
    - embed_documents(texts: List[str]) -> List[List[float]]
    - embed_query(text: str) -> List[float]

    SentenceTransformer has .encode() — this wrapper bridges the two.
    This way we reuse the singleton model instead of LangChain loading its own copy.
    """

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Embed a list of documents (used when storing CVs in Chroma)"""
        model = get_embedding_model()
        # convert_to_tensor=False returns numpy arrays, tolist() converts to plain Python lists
        return model.encode(texts, convert_to_tensor=False).tolist()

    def embed_query(self, text: str) -> list[float]:
        """Embed a single query string (used during similarity search)"""
        model = get_embedding_model()
        return model.encode(text, convert_to_tensor=False).tolist()


def get_cv_vector_index() -> Chroma:
    """
    Get the singleton ChromaDB instance for CV vectorization.
    Lazy initialization — only loads on first call.

    Uses the shared embedding model singleton via SentenceTransformerEmbeddingWrapper,
    so the model is loaded only once even if both this and other modules need it.

    Returns:
        Chroma: Vector store instance ready for .add_texts() and .similarity_search()

    Note:
        - Used for CV upload vectorization
        - Used for semantic search during screening
        - Used by RAG query subgraph for candidate lookup

    Example:
        index = get_cv_vector_index()
        index.add_texts(["cv text..."], metadatas=[{"application_id": 42}])
        results = index.similarity_search("Python engineer", k=10)
    """
    global _CV_VECTOR_INDEX

    # ==================== ALREADY INITIALIZED ====================
    if _CV_VECTOR_INDEX is not None:
        logger.debug("Returning cached CV vector index")
        return _CV_VECTOR_INDEX

    # ==================== INITIALIZE ====================
    index_store_path = os.getenv("INDEX_STORE_PATH", "backend/app/db/vector_index")

    logger.info(f"Initializing CV Vector Index at {index_store_path}")

    # Use our wrapper so Chroma uses the shared singleton model
    embedding_function = SentenceTransformerEmbeddingWrapper()

    _CV_VECTOR_INDEX = Chroma(
        persist_directory=index_store_path,
        embedding_function=embedding_function,
        collection_name="cv_embeddings"   # explicit name avoids Chroma default confusion
    )

    logger.info(f"✅ CV Vector Index initialized at {index_store_path}")
    return _CV_VECTOR_INDEX