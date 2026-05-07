import os
import requests
from dotenv import load_dotenv

load_dotenv()

import time

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:3b-instruct")

class UnifiedLLM:
    def __init__(self, model_name=OLLAMA_MODEL, temperature=0.7, max_tokens=2048, provider="ollama"):
        self.model_name = model_name
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.provider = provider
        self.model = None
        self.max_retries = 3
        self.retry_delay = 2  # seconds

    def generate(self, prompt: str):
        """Generate with retries"""
        for attempt in range(self.max_retries):
            try:
                return self._generate_ollama(prompt)
            except Exception as e:
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                    continue
                break

        print("Ollama generation failed")
        return {"results": [{"generated_text": ""}]}

    def _generate_ollama(self, prompt: str):
        """Generate using local Ollama (OpenAI-compatible endpoint)"""
        url = f"{OLLAMA_BASE_URL}/v1/chat/completions"
        headers = {"Content-Type": "application/json"}
        data = {
            "model": self.model_name,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens
        }

        r = requests.post(url, headers=headers, json=data, timeout=120)
        r.raise_for_status()
        res = r.json()
        text = res["choices"][0]["message"]["content"]
        return {"results": [{"generated_text": text}]}


### Model Instances ###

# Fast classification / routing (low temp for determinism)
llm_routing = UnifiedLLM(OLLAMA_MODEL, temperature=0.1, provider="ollama")

# General reasoning / chat
llm_generic = UnifiedLLM(OLLAMA_MODEL, temperature=0.7, provider="ollama")

# Structured extraction
llm_extraction = UnifiedLLM(OLLAMA_MODEL, temperature=0.3, provider="ollama")

# Retrieval-Augmented Generation (larger model for context)
llm_rag = UnifiedLLM(
    model_name=OLLAMA_MODEL,
    temperature=0.7,
    provider="ollama"
)

# SQL / deterministic (low temp for precision)
llm_sql = UnifiedLLM(OLLAMA_MODEL, temperature=0.1, provider="ollama")


# ==========================================================
# 🔍 Test Run
# ==========================================================
# if __name__ == "__main__":
#     prompts = [
#         ("Routing", llm_routing, "Classify: The user wants to fetch HR data."),
#         ("Generic", llm_generic, "Explain supervised learning simply."),
#         ("Extraction", llm_extraction, "Extract all skills: Python, AI, ML."),
#         ("RAG", llm_rag, "Explain how RAG combines search and generation."),
#         ("SQL", llm_sql, "Write SQL to find top 3 salaries per department."),
#     ]

#     for name, model, prompt in prompts:
#         print(f"\n=== 🧩 Testing {name} Model ===")
#         result = model.generate(prompt)
#         print(result["results"][0]["generated_text"])