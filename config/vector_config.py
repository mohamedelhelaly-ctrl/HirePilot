import os
from sentence_transformers import SentenceTransformer
from langchain_community.vectorstores import Chroma  # Updated import
from dotenv import load_dotenv

load_dotenv()

ENCODER_MODEL_DIR = os.getenv("ENCODER_MODEL_DIR", "database/store/encoder_model")
INDEX_STORE_PATH = os.getenv("INDEX_STORE_PATH", "database/store/index_store")

class SentenceTransformerEmbeddings:
    """Wrapper for SentenceTransformer to match LangChain interface"""
    
    def __init__(self, model):
        self.model = model
    
    def embed_documents(self, texts):
        return self.model.encode(texts, convert_to_tensor=False).tolist()
    
    def embed_query(self, text):
        return self.model.encode(text, convert_to_tensor=False).tolist()

def get_vector_index():
    """Create fresh vector index connection"""
    os.makedirs(INDEX_STORE_PATH, exist_ok=True)
    
    # Download model if not exists
    if not os.path.exists(ENCODER_MODEL_DIR):
        print("Downloading sentence transformer model...")
        model = SentenceTransformer('all-MiniLM-L6-v2')
        model.save(ENCODER_MODEL_DIR)
    
    sentence_transformer_model = SentenceTransformer(ENCODER_MODEL_DIR, device="cpu")
    embeddings_model = SentenceTransformerEmbeddings(sentence_transformer_model)
    
    return Chroma(
        persist_directory=INDEX_STORE_PATH,
        embedding_function=embeddings_model
    )