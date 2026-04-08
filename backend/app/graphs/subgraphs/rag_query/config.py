import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq

load_dotenv()

llm = ChatGroq(
    model="openai/gpt-oss-20b",  # or "mixtral-8x7b-32768", "gemma2-9b-it", etc.
    api_key=os.getenv("GROQ_API_KEY"),
    temperature=0.2,
    max_tokens=2048
)