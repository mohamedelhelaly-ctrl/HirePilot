"""
Download the sentence transformer model before running the app
"""
import os
from sentence_transformers import SentenceTransformer
BASE_DIR = os.path.dirname(__file__)
MODEL_DIR = os.path.join(BASE_DIR, "encoder_model")

def download_model():
    """Download and save the sentence transformer model"""
    
    print("📥 Downloading sentence transformer model...")
    print("   Model: BAAI/bge-m3")
    print("   This is a one-time download (~100MB)")
    print()
    
    # If the model already exists, skip download
    if os.path.isdir(MODEL_DIR) and os.listdir(MODEL_DIR):
        print(f"✅ Model already exists at {MODEL_DIR}, skipping download.")
        return

    # Create directory
    os.makedirs(MODEL_DIR, exist_ok=True)
    
    # Download model
    model = SentenceTransformer('BAAI/bge-m3', device="cpu")

    
    # Save locally
    print(f"💾 Saving model to {MODEL_DIR}...")
    model.save(MODEL_DIR)
    
    print("✅ Model downloaded and saved successfully!")
    print(f"   Location: {os.path.abspath(MODEL_DIR)}")

if __name__ == "__main__":
    download_model()