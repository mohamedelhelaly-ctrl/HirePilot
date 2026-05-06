import os
from dotenv import load_dotenv
from langchain_ollama import ChatOllama

load_dotenv()

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

llm = ChatOllama(
    model="qwen2.5:3b-instruct",
    base_url=OLLAMA_BASE_URL,
    temperature=0.2,
    num_predict=2048
)