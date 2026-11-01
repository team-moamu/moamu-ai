import base64
from pathlib import Path
from time import perf_counter
from typing import Optional

import httpx
from pydantic import ValidationError

from moamu_ai.errors import InvalidModelOutputError, ModelProviderError
from moamu_ai.prompts import build_verification_prompt
from moamu_ai.providers.base import InferenceResult, InferenceUsage
from moamu_ai.schemas import ConditionSnapshot, PhotoVerificationResponse


class OllamaPhotoJudge:
    def __init__(
        self,
        base_url: str,
        model: str,
        timeout_seconds: float = 45.0,
        client: Optional[httpx.Client] = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.client = client or httpx.Client(timeout=timeout_seconds)

    def evaluate(self, image_path: Path, conditions: list[ConditionSnapshot]) -> InferenceResult:
        try:
            image_bytes = image_path.read_bytes()
        except OSError as exc:
            raise ModelProviderError("validated image could not be read") from exc
        encoded_image = base64.b64encode(image_bytes).decode("ascii")
        prompt = build_verification_prompt(conditions)
        schema = PhotoVerificationResponse.model_json_schema()
        started = perf_counter()
        try:
            response = self.client.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": self.model,
                    "messages": [
                        {
                            "role": "user",
                            "content": prompt,
                            "images": [encoded_image],
                        }
                    ],
                    "format": schema,
                    "options": {"temperature": 0},
                    "stream": False,
                },
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise ModelProviderError("Ollama request failed") from exc

        latency_ms = (perf_counter() - started) * 1000
        response_text = payload.get("message", {}).get("content")
        if not isinstance(response_text, str) or not response_text:
            raise InvalidModelOutputError("Ollama returned no structured result")
        try:
            parsed = PhotoVerificationResponse.model_validate_json(response_text)
        except (ValidationError, ValueError) as exc:
            raise InvalidModelOutputError("Ollama returned an invalid result") from exc

        prompt_tokens = payload.get("prompt_eval_count")
        output_tokens = payload.get("eval_count")
        total_tokens = None
        if isinstance(prompt_tokens, int) and isinstance(output_tokens, int):
            total_tokens = prompt_tokens + output_tokens
        return InferenceResult(
            results=parsed.results,
            usage=InferenceUsage(
                model=self.model,
                latency_ms=latency_ms,
                prompt_tokens=prompt_tokens,
                output_tokens=output_tokens,
                total_tokens=total_tokens,
            ),
        )
