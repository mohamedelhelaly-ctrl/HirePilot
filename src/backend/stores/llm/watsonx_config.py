"""
Temporary Watsonx LLM config for local/testing use.

Mirrors talent-acquisition-agent/src/llms/watsonx_config.py.
Enable via .env:  LLM_PROVIDER=watsonx
Requires:         WATSON_APIKEY, PROJECT_ID
"""

import logging
import os
import time
from enum import Enum

import requests
from dotenv import load_dotenv
from requests.exceptions import RequestException

load_dotenv()

logger = logging.getLogger(__name__)


class ModelType(Enum):
    EXTRACTION = "openai/gpt-oss-120b"
    CLASSIFICATION = "openai/gpt-oss-120b"
    GENERIC = "meta-llama/llama-3-3-70b-instruct"
    JD = "meta-llama/llama-3-3-70b-instruct"


class WatsonxLLM:
    """Watsonx chat API wrapper — same generate() shape as UnifiedLLM."""

    def __init__(
        self,
        default_model: ModelType = ModelType.CLASSIFICATION,
        temperature: float = 0,
        max_tokens: int = 8192,
        project_id: str | None = None,
    ):
        self.default_model = default_model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.project_id = project_id or os.getenv("PROJECT_ID")
        self.url = "https://us-south.ml.cloud.ibm.com/ml/v1/text/chat?version=2023-05-29"

        self.max_retries = int(os.getenv("WATSONX_MAX_RETRIES", "3"))
        self.retry_delay_seconds = float(os.getenv("WATSONX_RETRY_DELAY_SECONDS", "1.0"))
        self.retry_backoff_multiplier = float(os.getenv("WATSONX_RETRY_BACKOFF_MULTIPLIER", "2.0"))
        self.request_timeout_seconds = int(os.getenv("WATSONX_REQUEST_TIMEOUT_SECONDS", "500"))

        self._token: str | None = None
        self._refresh_token()

    @property
    def model_name(self) -> str:
        return self.default_model.value

    @property
    def provider(self) -> str:
        return "watsonx"

    def _build_fallback_chain(self, selected_model: ModelType) -> list[str]:
        default_fallbacks = {
            ModelType.JD: [ModelType.EXTRACTION.value, ModelType.GENERIC.value],
            ModelType.EXTRACTION: [ModelType.GENERIC.value],
            ModelType.CLASSIFICATION: [ModelType.GENERIC.value],
            ModelType.GENERIC: [ModelType.EXTRACTION.value],
        }

        raw_fallbacks = os.getenv("WATSONX_FALLBACK_MODELS", "").strip()
        env_fallbacks = [m.strip() for m in raw_fallbacks.split(",") if m.strip()] if raw_fallbacks else []

        chain = [selected_model.value]
        for model_id in env_fallbacks + default_fallbacks.get(selected_model, []):
            if model_id not in chain:
                chain.append(model_id)
        return chain

    def _is_retryable_status(self, status_code: int) -> bool:
        return status_code in {408, 409, 425, 429, 500, 502, 503, 504}

    def _is_model_endpoint_down(self, error_text: str) -> bool:
        lowered = (error_text or "").lower()
        markers = [
            "downstream_request_failed",
            "connection refused",
            "connect: connection refused",
            "dial tcp",
            "upstream connect",
        ]
        return any(marker in lowered for marker in markers)

    def _get_iam_token(self) -> str:
        apikey = os.getenv("WATSON_APIKEY")
        if not apikey:
            raise ValueError("WATSON_APIKEY is not set")

        resp = requests.post(
            "https://iam.cloud.ibm.com/identity/token",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data={
                "grant_type": "urn:ibm:params:oauth:grant-type:apikey",
                "apikey": apikey,
            },
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()["access_token"]

    def _refresh_token(self) -> None:
        self._token = self._get_iam_token()

    def generate(
        self,
        prompt: str,
        model_type: ModelType | None = None,
        params: dict | None = None,
    ) -> dict:
        if not self.project_id:
            raise ValueError("PROJECT_ID is not set")

        selected_model = model_type or self.default_model
        model_chain = self._build_fallback_chain(selected_model)
        last_error: Exception | None = None
        response_data: dict | None = None
        used_model_id = selected_model.value

        temperature = params.get("temperature", self.temperature) if params else self.temperature
        if selected_model in (ModelType.CLASSIFICATION, ModelType.GENERIC):
            temperature = min(temperature + 0.1, 1.0) if temperature < 1.0 else temperature

        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._token}",
        }

        for model_id in model_chain:
            logger.info("Watsonx using model: %s", model_id)

            body = {
                "messages": [
                    {"role": "user", "content": [{"type": "text", "text": prompt}]}
                ],
                "project_id": self.project_id,
                "model_id": model_id,
                "frequency_penalty": 0,
                "max_tokens": params.get("max_tokens", self.max_tokens) if params else self.max_tokens,
                "presence_penalty": 0,
                "temperature": temperature,
                "top_p": 1,
            }

            delay = self.retry_delay_seconds
            for attempt in range(1, self.max_retries + 1):
                try:
                    response = requests.post(
                        self.url,
                        headers=headers,
                        json=body,
                        timeout=self.request_timeout_seconds,
                    )
                except RequestException as exc:
                    last_error = Exception(
                        f"Network error for model {model_id} "
                        f"on attempt {attempt}/{self.max_retries}: {exc}"
                    )
                    if attempt < self.max_retries:
                        logger.warning("%s. Retrying in %.1fs...", last_error, delay)
                        time.sleep(delay)
                        delay *= self.retry_backoff_multiplier
                        continue
                    break

                if response.status_code == 401:
                    self._refresh_token()
                    headers["Authorization"] = f"Bearer {self._token}"
                    response = requests.post(
                        self.url,
                        headers=headers,
                        json=body,
                        timeout=self.request_timeout_seconds,
                    )

                if response.status_code == 200:
                    response_data = response.json()
                    used_model_id = model_id
                    break

                error_msg = f"Non-200 response ({response.status_code}): {response.text}"
                last_error = Exception(error_msg)

                if self._is_model_endpoint_down(response.text):
                    logger.warning("Model endpoint appears down for %s: %s", model_id, error_msg)
                    break

                if self._is_retryable_status(response.status_code) and attempt < self.max_retries:
                    logger.warning("%s. Retrying in %.1fs...", error_msg, delay)
                    time.sleep(delay)
                    delay *= self.retry_backoff_multiplier
                    continue
                break

            if isinstance(response_data, dict):
                break

            response_data = None
            logger.warning("Switching to fallback model after failures on %s", model_id)

        if not isinstance(response_data, dict):
            raise last_error or Exception("Watsonx generation failed after retries and fallbacks")

        choice = (response_data.get("choices") or [{}])[0]
        usage = response_data.get("usage", {})

        generated_text = None
        if isinstance(choice, dict):
            message = choice.get("message", {}) if isinstance(choice.get("message", {}), dict) else {}
            generated_text = (
                (message.get("content") if isinstance(message.get("content", ""), str) else None)
                or choice.get("text")
                or choice.get("content")
            )

        if not generated_text:
            if isinstance(response_data.get("results"), list) and response_data["results"]:
                generated_text = (
                    response_data["results"][0].get("generated_text")
                    or response_data["results"][0].get("text")
                )
            generated_text = generated_text or response_data.get("generated_text")

        if not isinstance(generated_text, str):
            generated_text = str(response_data)

        logger.debug(
            "Watsonx response model=%s length=%d",
            used_model_id,
            len(generated_text),
        )

        output_tokens = int(
            usage.get("completion_tokens", usage.get("output_tokens", usage.get("generated_token_count", 0))) or 0
        )
        input_tokens = int(
            usage.get("prompt_tokens", usage.get("input_tokens", usage.get("input_token_count", 0))) or 0
        )

        return {
            "results": [{
                "generated_text": generated_text,
                "generated_token_count": output_tokens,
                "input_token_count": input_tokens,
                "stop_reason": (
                    (choice.get("finish_reason") or choice.get("stop_reason") if isinstance(choice, dict) else None)
                    or "completed"
                ),
            }]
        }


# Task-specific instances (aligned with talent-acquisition-agent)
llm_classification = WatsonxLLM(
    default_model=ModelType.CLASSIFICATION,
    temperature=0,
    max_tokens=200,
)

llm_extraction = WatsonxLLM(
    default_model=ModelType.EXTRACTION,
    temperature=0,
    max_tokens=8192,
)

llm_generic = WatsonxLLM(
    default_model=ModelType.GENERIC,
    temperature=0.1,
    max_tokens=8192,
)

llm = WatsonxLLM(
    default_model=ModelType.EXTRACTION,
    temperature=0,
    max_tokens=8192,
)

llmjd = WatsonxLLM(
    default_model=ModelType.JD,
    temperature=0,
    max_tokens=8192,
)
