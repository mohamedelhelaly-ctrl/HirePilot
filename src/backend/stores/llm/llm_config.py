import logging
import os
import requests
import time
from dotenv import load_dotenv
from langchain_groq import ChatGroq

load_dotenv()

logger = logging.getLogger(__name__)
BASE_URL = os.getenv("BASE_URL", "http://localhost:11434")
MODEL = os.getenv("BASE_MODEL", "qwen2.5:3b-instruct")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

class UnifiedLLM:
    def __init__(self, model_name=MODEL, temperature=0.7, max_tokens=2048, provider="groq"):
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
                logger.debug(
                    "LLM generate attempt %d/%d provider=%s model=%s prompt_len=%d",
                    attempt + 1,
                    self.max_retries,
                    self.provider,
                    self.model_name,
                    len(prompt),
                )
                if self.provider == "groq":
                    return self._generate_groq(prompt)
                elif self.provider == "ollama":
                    return self._generate_ollama(prompt)
                elif self.provider == "langchain-groq":
                    return self._generate_langchain_groq(prompt)
                else:
                    raise ValueError(f"Unsupported provider: {self.provider}")
            except Exception as e:
                logger.warning(
                    "LLM generate failed on attempt %d/%d: %s",
                    attempt + 1,
                    self.max_retries,
                    e,
                    exc_info=True,
                )
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                    continue
                logger.error(
                    "LLM generate final failure after %d attempts: %s",
                    self.max_retries,
                    e,
                )
                break

        logger.error("%s generation failed, returning empty result", self.provider)
        return {"results": [{"generated_text": ""}]}

    def _generate_ollama(self, prompt: str):
        """Generate using local Ollama (OpenAI-compatible endpoint)"""
        url = f"{BASE_URL}/v1/chat/completions"
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

    def _generate_groq(self, prompt: str):
        """Generate using Groq API (OpenAI-compatible endpoint)"""
        url = f"{BASE_URL}/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {GROQ_API_KEY}"
        }
        data = {
            "model": self.model_name,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens
        }

        r = requests.post(url, headers=headers, json=data, timeout=120)
        if r.status_code != 200:
            logger.error(
                "GROQ API request failed status=%s response=%s",
                r.status_code,
                r.text[:1000],
            )
        r.raise_for_status()
        res = r.json()
        text = res["choices"][0]["message"]["content"]
        logger.debug("GROQ response length=%d", len(text))
        logger.debug("GROQ response preview=%s", text[:1000])
        return {"results": [{"generated_text": text}]}

    def _generate_langchain_groq(self, prompt: str):
        """Generate using LangChain's Groq integration"""
        llm = ChatGroq(
            model=self.model_name,
            api_key=GROQ_API_KEY,
            temperature=self.temperature,
            max_tokens=self.max_tokens
        )
        response = llm.invoke(prompt)
        return {"results": [{"generated_text": response.content}]}

### Model Instances ###

# Fast classification / routing (low temp for determinism)
llm_routing = UnifiedLLM(MODEL, temperature=0.1, provider="groq")

# General reasoning / chat
llm_generic = UnifiedLLM(MODEL, temperature=0.7, provider="ollama")

# Structured extraction
llm_extraction = UnifiedLLM(MODEL, temperature=0.3, provider="ollama")

# Retrieval-Augmented Generation (larger model for context)
llm_rag = UnifiedLLM(
    model_name=MODEL,
    temperature=0.7,
    provider="langchain-groq"
)

# SQL / deterministic (low temp for precision)
llm_sql = UnifiedLLM(MODEL, temperature=0.1, provider="groq")

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
#
#     for name, model, prompt in prompts:
#         print(f"\n=== 🧩 Testing {name} Model ===")
#         result = model.generate(prompt)
#         print(result["results"][0]["generated_text"])