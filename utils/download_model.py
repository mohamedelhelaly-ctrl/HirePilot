"""
Download the sentence transformer model before running the app
"""
import os
from sentence_transformers import SentenceTransformer

MODEL_DIR = "database/store/encoder_model"

def download_model():
    """Download and save the sentence transformer model"""
    
    print("📥 Downloading sentence transformer model...")
    print("   Model: all-MiniLM-L6-v2")
    print("   This is a one-time download (~100MB)")
    print()
    
    # Create directory
    os.makedirs(MODEL_DIR, exist_ok=True)
    
    # Download model
    model = SentenceTransformer('all-MiniLM-L6-v2', device="cpu")
    
    # Save locally
    print(f"💾 Saving model to {MODEL_DIR}...")
    model.save(MODEL_DIR)
    
    print("✅ Model downloaded and saved successfully!")
    print(f"   Location: {os.path.abspath(MODEL_DIR)}")

if __name__ == "__main__":
    download_model()