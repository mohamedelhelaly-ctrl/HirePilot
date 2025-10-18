from sentence_transformers import SentenceTransformer

class SentenceTransformerEmbeddings:
    """Wrapper for SentenceTransformer to match LangChain interface"""
    
    def __init__(self, model):
        self.model = model
    
    def embed_documents(self, texts):
        return self.model.encode(texts, convert_to_tensor=False).tolist()
    
    def embed_query(self, text):
        return self.model.encode(text, convert_to_tensor=False).tolist()