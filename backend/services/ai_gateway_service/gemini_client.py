from __future__ import annotations

import json
import urllib.error
import urllib.request

from django.conf import settings

from .exceptions import AIProviderError, AIProviderUnavailable, parse_gemini_error_body
from .json_extraction import parse_json_response
from .schemas import PROFILE_ASSESSMENT_RESPONSE_SCHEMA, PROFILE_ASSESSMENT_SYSTEM_PROMPT


class GeminiProfileAssessmentClient:
    provider_name = "gemini"

    def __init__(
        self,
        *,
        api_key: str | None = None,
        model_name: str | None = None,
        timeout_seconds: int | None = None,
        max_output_tokens: int | None = None,
    ) -> None:
        self.api_key = api_key if api_key is not None else settings.GEMINI_API_KEY
        self.model_name = model_name or settings.AI_PROFILE_ASSESSMENT_MODEL
        self.timeout_seconds = timeout_seconds or settings.AI_TIMEOUT_SECONDS
        self.max_output_tokens = max_output_tokens or settings.AI_MAX_OUTPUT_TOKENS

    def generate_profile_assessment(self, input_summary: dict, *, repair_reason: str | None = None) -> dict:
        if not self.api_key:
            raise AIProviderUnavailable("Gemini API key is not configured.")

        prompt = {
            "system": PROFILE_ASSESSMENT_SYSTEM_PROMPT,
            "response_schema": PROFILE_ASSESSMENT_RESPONSE_SCHEMA,
            "student_profile": input_summary,
            "output_rules": [
                "Return JSON only.",
                "Use only the supplied profile data.",
                "Do not include admission probability, chance, odds, or promises.",
                "Do not write or rewrite essays.",
            ],
        }
        if repair_reason:
            # A single repair retry (PROTOCOL-008 PART 3): the previous
            # response failed schema validation, so tell the model exactly
            # why and ask for a corrected reply. `repair_reason` only ever
            # contains a schema field/value description (see
            # `AssessmentValidationError` call sites) -- never raw profile
            # text -- so it is safe to echo back into the prompt.
            prompt["repair_instructions"] = (
                "Your previous response was rejected for this reason: "
                f"{repair_reason}. Return corrected JSON that strictly matches response_schema."
            )
        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.model_name}:generateContent?key={self.api_key}"
        )
        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": json.dumps(prompt, sort_keys=True)}],
                }
            ],
            "generationConfig": {
                "temperature": 0.2,
                "maxOutputTokens": self.max_output_tokens,
                "responseMimeType": "application/json",
            },
        }
        request = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                data = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            try:
                body = error.read().decode("utf-8", errors="replace")
            except Exception:
                body = ""
            provider_code, provider_status = parse_gemini_error_body(body)
            raise AIProviderError(
                "Gemini profile assessment request failed.",
                status_code=error.code,
                error_body=body,
                cause_class=type(error).__name__,
                provider_code=provider_code,
                provider_status=provider_status,
            ) from error
        except TimeoutError as error:
            raise AIProviderError(
                "Gemini profile assessment request timed out.",
                error_body="timeout while calling Gemini",
                cause_class=type(error).__name__,
            ) from error
        except urllib.error.URLError as error:
            raise AIProviderError(
                "Gemini profile assessment request failed.",
                error_body=f"network error contacting Gemini: {error.reason}",
                cause_class=type(error).__name__,
            ) from error
        except json.JSONDecodeError as error:
            raise AIProviderError(
                "Gemini returned an invalid JSON response.",
                error_body=f"invalid Gemini JSON response: {error}",
                cause_class=type(error).__name__,
            ) from error

        text = self._extract_text(data)
        try:
            return parse_json_response(text)
        except json.JSONDecodeError as error:
            raise AIProviderError(
                "Gemini returned non-JSON profile assessment output.",
                error_body=f"json decode failed: {error.msg} at pos {error.pos}",
                cause_class=type(error).__name__,
            ) from error

    @staticmethod
    def _extract_text(data: dict) -> str:
        candidates = data.get("candidates")
        if not isinstance(candidates, list) or not candidates:
            raise AIProviderError("Gemini response did not include candidates.")
        parts = candidates[0].get("content", {}).get("parts", [])
        if not isinstance(parts, list) or not parts:
            raise AIProviderError("Gemini response did not include content parts.")
        text = parts[0].get("text", "")
        if not isinstance(text, str) or not text.strip():
            raise AIProviderError("Gemini response text was empty.")
        return text
