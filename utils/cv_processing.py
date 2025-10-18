import os
import tempfile
from langchain.schema import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from utils.cv_text_parser import extract_text_from_pdf

def process_and_vectorize_cv(file_content: bytes, filename: str, vector_index, 
                             thread_id: str) -> tuple:
    """Process and vectorize a single CV"""
    
    try:
        # Create temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
            temp_file.write(file_content)
            temp_path = temp_file.name
        
        # Extract text
        extraction_result = extract_text_from_pdf(temp_path)
        cv_text = extraction_result.get("text", "")
        
        # Clean up temp file
        os.unlink(temp_path)
        
        if not cv_text.strip():
            print(f"⚠️ No text found in {filename}")
            return ("failed", filename)
        
        # Split text into chunks
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200
        )
        chunks = text_splitter.split_text(cv_text)
        
        # Create documents with metadata
        documents = [
            Document(
                page_content=chunk,
                metadata={
                    "source": filename,
                    "thread_id": thread_id,
                    "filtered": True,  # Start as True, will be updated by initial filtration
                    "chunk_index": i
                }
            )
            for i, chunk in enumerate(chunks)
        ]
        
        if documents:
            vector_index.add_documents(documents)
            print(f"✅ Vectorized {filename} ({len(documents)} chunks)")
            return ("success", filename)
        else:
            return ("failed", filename)
    
    except Exception as e:
        print(f"❌ Error processing {filename}: {e}")
        return ("failed", filename)