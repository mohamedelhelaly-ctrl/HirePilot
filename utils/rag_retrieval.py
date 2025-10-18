import os
import json
import chromadb
from sentence_transformers import SentenceTransformer
from config.vector_config import ENCODER_MODEL_DIR, INDEX_STORE_PATH
from database.schema import get_db_connection

class RAGRetrieval:
    """RAG system for candidate explanation"""
    
    def __init__(self, thread_id: str):
        self.thread_id = thread_id
        self.embedding_model = SentenceTransformer(ENCODER_MODEL_DIR, device="cpu")
        
        # Initialize Chroma client
        self.client = chromadb.PersistentClient(path=INDEX_STORE_PATH)
        self.collection = self.client.get_or_create_collection(
            name="cv_rag",
            metadata={"hnsw:space": "cosine"}
        )
    
    def index_candidate(self, candidate_id: int):
        """Index a single candidate for RAG queries"""
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Fetch candidate data
        cursor.execute(
            "SELECT * FROM candidates WHERE candidate_id = ? AND thread_id = ?",
            (candidate_id, self.thread_id)
        )
        
        row = cursor.fetchone()
        if not row:
            conn.close()
            return False
        
        columns = [desc[0] for desc in cursor.description]
        candidate_data = dict(zip(columns, row))
        conn.close()
        
        # Build text representation
        text_parts = [
            f"Candidate ID: {candidate_data.get('candidate_id', 'N/A')}",
            f"Name: {candidate_data.get('english_name', 'N/A')}",
            f"Email: {candidate_data.get('email', 'N/A')}",
            f"Years of Experience: {candidate_data.get('years_of_experience', 'N/A')}",
            f"Education: {candidate_data.get('study_field', 'N/A')} from {candidate_data.get('universities', 'N/A')}",
            f"Technical Skills: {candidate_data.get('technical_skills', 'N/A')}",
            f"Soft Skills: {candidate_data.get('soft_skills', 'N/A')}",
            f"Languages: {candidate_data.get('Languages', 'N/A')}",
            f"Certifications: {candidate_data.get('Certifications', 'N/A')}",
            f"Match Score: {candidate_data.get('score', 'N/A')}",
            f"Justification: {candidate_data.get('justification', 'N/A')}"
        ]
        
        full_text = "\n".join(text_parts)
        
        # Generate embedding
        embedding = self.embedding_model.encode(full_text, convert_to_tensor=False, show_progress_bar=False).tolist()
        
        # Store in Chroma
        doc_id = f"candidate_{candidate_id}"
        self.collection.upsert(
            ids=[doc_id],
            documents=[full_text],
            embeddings=[embedding],
            metadatas=[{
                "candidate_id": candidate_id,
                "thread_id": self.thread_id,
                "name": candidate_data.get('english_name', 'Unknown')
            }]
        )
        
        return True
    
    def ensure_indexed(self, candidate_ids: list):
        """Ensure candidates are indexed"""
        for cid in candidate_ids:
            try:
                self.index_candidate(cid)
            except Exception as e:
                print(f"Error indexing candidate {cid}: {e}")
    
    def retrieve_candidates(self, query: str, candidate_ids: list = None, top_k: int = 5):
        """Retrieve relevant candidate information"""
        
        # Generate query embedding
        query_embedding = self.embedding_model.encode(query, convert_to_tensor=False, show_progress_bar=False).tolist()
        
        # Build filter - ChromaDB requires specific format
        where_filter = None
        if candidate_ids and len(candidate_ids) == 1:
            # Single candidate
            where_filter = {
                "$and": [
                    {"thread_id": {"$eq": self.thread_id}},
                    {"candidate_id": {"$eq": candidate_ids[0]}}
                ]
            }
        elif candidate_ids and len(candidate_ids) > 1:
            # Multiple candidates - use $or
            or_conditions = [{"candidate_id": {"$eq": cid}} for cid in candidate_ids]
            where_filter = {
                "$and": [
                    {"thread_id": {"$eq": self.thread_id}},
                    {"$or": or_conditions}
                ]
            }
        else:
            # No specific candidates - just filter by thread
            where_filter = {"thread_id": {"$eq": self.thread_id}}
        
        # Query collection
        try:
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=min(top_k, self.collection.count()),
                where=where_filter
            )
        except Exception as e:
            print(f"⚠️ ChromaDB query error: {e}")
            # Fallback: query without candidate filter
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=min(top_k, self.collection.count()),
                where={"thread_id": {"$eq": self.thread_id}}
            )
        
        retrieved_docs = []
        if results['ids'][0]:
            for i in range(len(results['ids'][0])):
                retrieved_docs.append({
                    'id': results['ids'][0][i],
                    'content': results['documents'][0][i],
                    'metadata': results['metadatas'][0][i],
                    'distance': results['distances'][0][i] if 'distances' in results else None
                })
        
        return retrieved_docs

def index_all_candidates_for_thread(thread_id: str):
    """Index all screened candidates for a thread"""
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT candidate_id FROM candidates WHERE thread_id = ?",
        (thread_id,)
    )
    candidate_ids = [row[0] for row in cursor.fetchall()]
    conn.close()
    
    if not candidate_ids:
        return 0
    
    rag = RAGRetrieval(thread_id)
    indexed_count = 0
    
    for cid in candidate_ids:
        if rag.index_candidate(cid):
            indexed_count += 1
    
    return indexed_count