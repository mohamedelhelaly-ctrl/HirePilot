import os
import requests
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

# Configure Gemini API (optional, as fallback)
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

import time
from typing import Optional

class UnifiedLLM:
    def __init__(self, model_name, temperature=0.7, max_tokens=2048, provider="groq"):
        self.model_name = model_name
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.provider = provider
        self.model = None
        self.max_retries = 3
        self.retry_delay = 2  # seconds

        if provider == "gemini":
            try:
                self.model = genai.GenerativeModel(model_name)
            except Exception as e:
                print(f"⚠️ Gemini init error: {e}")

    def generate(self, prompt: str):
        """Generate with retries and fallback logic"""
        
        # Try primary provider with retries
        for attempt in range(self.max_retries):
            try:
                if self.provider == "groq":
                    return self._generate_groq(prompt)
                elif self.provider == "openrouter":
                    return self._generate_openrouter(prompt)
                elif self.provider == "gemini":
                    return self._generate_gemini(prompt)
            except Exception as e:
                if "429" in str(e):  # Rate limit
                    wait_time = self.retry_delay * (attempt + 1)
                    print(f"⏳ Rate limit hit. Waiting {wait_time}s before retry {attempt + 1}/{self.max_retries}")
                    time.sleep(wait_time)
                    continue
                elif "400" in str(e):  # Bad request - don't retry
                    break
                else:
                    if attempt < self.max_retries - 1:
                        time.sleep(self.retry_delay)
                        continue
                    break
        
        # Fallback chain: Groq → OpenRouter → Gemini
        print(f"⚠️ {self.provider} failed after retries. Trying fallbacks...")
        
        if self.provider == "groq":
            try:
                print("🔄 Falling back to OpenRouter...")
                result = self._generate_openrouter(prompt)
                if result and result["results"][0]["generated_text"]:
                    return result
            except Exception as e:
                print(f"⚠️ OpenRouter fallback failed: {e}")
        
        # Final fallback to Gemini
        try:
            print("🔄 Final fallback to Gemini...")
            return self._generate_gemini(prompt)
        except Exception as e:
            print(f"❌ All providers failed: {e}")
            return {"results": [{"generated_text": ""}]}

    def _generate_gemini(self, prompt: str):
        """Generate using Gemini"""
        if not self.model:
            raise ValueError("Gemini model not initialized")
        
        response = self.model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=self.temperature,
                max_output_tokens=self.max_tokens,
            )
        )
        text = getattr(response, "text", "")
        return {"results": [{"generated_text": text}]}

    def _generate_groq(self, prompt: str):
        """Generate using Groq API"""
        if not GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY not set")
        
        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }
        url = "https://api.groq.com/openai/v1/chat/completions"  # Fixed URL (removed space)
        data = {
            "model": self.model_name,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens
        }

        r = requests.post(url, headers=headers, json=data, timeout=30)
        r.raise_for_status()
        res = r.json()
        text = res["choices"][0]["message"]["content"]
        return {"results": [{"generated_text": text}]}

    def _generate_openrouter(self, prompt: str):
        """Generate using OpenRouter"""
        if not OPENROUTER_API_KEY:
            raise ValueError("OPENROUTER_API_KEY not set")
        
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost",
            "X-Title": "Incorta-HR Assistant"
        }
        url = "https://openrouter.ai/api/v1/chat/completions"  # Fixed URL
        
        # Use a different model that's more reliable
        data = {
            "model": "mistralai/mistral-7b-instruct",  # More reliable model
            "messages": [{"role": "user", "content": prompt}],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens
        }

        r = requests.post(url, headers=headers, json=data, timeout=30)
        r.raise_for_status()
        res = r.json()
        text = res["choices"][0]["message"]["content"]
        return {"results": [{"generated_text": text}]}


# ==========================================================
# 🧠 Model Instances (Prioritizing Groq for speed and limits)
# ==========================================================

# Fast classification / routing (low temp for determinism)
llm_routing = UnifiedLLM("llama-3.1-8b-instant", temperature=0.1, provider="groq")

# General reasoning / chat
llm_generic = UnifiedLLM("openai/gpt-oss-20b", temperature=0.7, provider="groq")

# Structured extraction
llm_extraction = UnifiedLLM("llama-3.1-8b-instant", temperature=0.3, provider="groq")

# Retrieval-Augmented Generation (larger model for context)
llm_rag = UnifiedLLM(
    model_name="llama-3.3-70b-versatile",
    temperature=0.7,
    provider="groq"
)

# SQL / deterministic (low temp for precision)
llm_sql = UnifiedLLM("llama-3.1-8b-instant", temperature=0.1, provider="groq")


# ==========================================================
# 🔍 Test Run
# ==========================================================
if __name__ == "__main__":
    prompts = [
        ("Routing", llm_routing, "Classify: The user wants to fetch HR data."),
        ("Generic", llm_generic, "Explain supervised learning simply."),
        ("Extraction", llm_extraction, "Extract all skills: Python, AI, ML."),
        ("RAG", llm_rag, "Explain how RAG combines search and generation."),
        ("SQL", llm_sql, "Write SQL to find top 3 salaries per department."),
    ]

    for name, model, prompt in prompts:
        print(f"\n=== 🧩 Testing {name} Model ===")
        result = model.generate(prompt)
        print(result["results"][0]["generated_text"])