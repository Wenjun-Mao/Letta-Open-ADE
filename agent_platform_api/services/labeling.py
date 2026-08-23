from __future__ import annotations

import re
from typing import Any

from agent_platform_api.clients.openai_chat import (
    OpenAIChatClient,
    resolve_provider_model,
)
from agent_platform_api.settings import get_settings
from agent_platform_api.services.labeling_helpers import (
    resolve_label_output_schema,
)
from agent_platform_api.services.labeling_requests import (
    build_label_repair_request_payload,
    build_label_request_payload,
)
from agent_platform_api.services.labeling_responses import (
    append_finish_reason_diagnostic,
    build_label_generation_result,
    extract_validated_label_response,
)


class LabelingValidationError(ValueError):
    def __init__(
        self,
        message: str,
        *,
        validation_errors: list[str],
        raw_request: dict[str, Any] | None = None,
        raw_reply: dict[str, Any] | None = None,
    ):
        super().__init__(message)
        self.validation_errors = list(validation_errors)
        self.raw_request = dict(raw_request or {})
        self.raw_reply = dict(raw_reply or {})


DEFAULT_LABELING_REPAIR_RETRY_COUNT = 1
MAX_LABELING_REPAIR_RETRY_COUNT = 3
DEFAULT_LABELING_TEMPERATURE = 0.0
DEFAULT_LABELING_TOP_P = 1.0
DEFAULT_LABELING_TOP_K: int | None = None


class LabelingService:
    """Stateless structured labeling through an OpenAI-compatible chat completions API."""

    _OUTPUT_MODES = {"strict_json_schema", "json_schema", "best_effort_prompt_json"}

    def __init__(
        self,
        *,
        settings_factory=get_settings,
        provider_client: OpenAIChatClient | None = None,
    ):
        self._settings_factory = settings_factory
        self._provider_client = provider_client or OpenAIChatClient()

    @staticmethod
    def _clamp_max_tokens(value: int) -> int:
        if int(value) <= 0:
            return 0
        return max(64, min(8192, int(value)))

    @staticmethod
    def _clamp_timeout_seconds(value: float) -> float:
        return max(5.0, min(600.0, float(value)))

    @staticmethod
    def _clamp_repair_retry_count(value: int | None) -> int:
        if value is None:
            return DEFAULT_LABELING_REPAIR_RETRY_COUNT
        return max(0, min(MAX_LABELING_REPAIR_RETRY_COUNT, int(value)))

    @staticmethod
    def _clamp_temperature(value: float | None) -> float:
        return (
            DEFAULT_LABELING_TEMPERATURE
            if value is None
            else max(0.0, min(2.0, float(value)))
        )

    @staticmethod
    def _clamp_top_p(value: float | None) -> float:
        return (
            DEFAULT_LABELING_TOP_P
            if value is None
            else max(0.01, min(1.0, float(value)))
        )

    @staticmethod
    def _clamp_top_k(value: int | None) -> int | None:
        if value is None:
            return DEFAULT_LABELING_TOP_K
        return max(1, min(1000, int(value)))

    @classmethod
    def _resolve_output_mode(cls, value: str | None) -> str:
        resolved = str(value or "").strip().lower()
        if not resolved:
            return "best_effort_prompt_json"
        if resolved in cls._OUTPUT_MODES:
            return resolved
        raise ValueError(f"Unsupported output_mode: {resolved}")

    @staticmethod
    def _normalize_response_format_name(value: str) -> str:
        normalized = re.sub(r"[^A-Za-z0-9_-]+", "_", str(value or "").strip())
        normalized = normalized.strip("_")
        return normalized[:64] or "label_output"

    def runtime_defaults(self) -> dict[str, Any]:
        settings = self._settings_factory()
        return {
            "max_tokens": self._clamp_max_tokens(settings.labeling_max_tokens),
            "timeout_seconds": self._clamp_timeout_seconds(
                settings.labeling_timeout_seconds
            ),
            "repair_retry_count": self._clamp_repair_retry_count(
                settings.labeling_repair_retry_count
            ),
            "temperature": self._clamp_temperature(settings.labeling_temperature),
            "top_p": self._clamp_top_p(settings.labeling_top_p),
            "top_k": self._clamp_top_k(settings.labeling_top_k),
        }

    def _post_chat_completions(
        self,
        payload: dict[str, Any],
        *,
        base_url: str,
        api_key: str,
        timeout_seconds: float,
    ) -> dict[str, Any]:
        return self._provider_client.post_chat_completions(
            payload,
            base_url=base_url,
            api_key=api_key,
            timeout_seconds=timeout_seconds,
            retry_count=0,
        )

    def generate_labels(
        self,
        *,
        base_url: str,
        api_key: str = "",
        model: str,
        system_prompt: str,
        article_input: str,
        output_mode: str,
        output_schema_raw: str | None = None,
        output_schema_name: str = "label_output",
        max_tokens: int | None = None,
        timeout_seconds: float | None = None,
        repair_retry_count: int | None = None,
        temperature: float | None = None,
        top_p: float | None = None,
        top_k: int | None = None,
    ) -> dict[str, Any]:
        resolved_base_url = str(base_url or "").strip()
        if not resolved_base_url:
            raise ValueError("base_url is required")

        resolved_model = resolve_provider_model(str(model or ""))
        if not resolved_model:
            raise ValueError("model is required")

        article = str(article_input or "").strip()
        if not article:
            raise ValueError("input is required")

        output_schema = resolve_label_output_schema(output_schema_raw)
        resolved_output_schema_name = self._normalize_response_format_name(
            output_schema_name
        )
        runtime_defaults = self.runtime_defaults()
        resolved_max_tokens = (
            runtime_defaults["max_tokens"]
            if max_tokens is None
            else self._clamp_max_tokens(max_tokens)
        )
        resolved_timeout_seconds = (
            runtime_defaults["timeout_seconds"]
            if timeout_seconds is None
            else self._clamp_timeout_seconds(timeout_seconds)
        )
        resolved_repair_retry_count = (
            runtime_defaults["repair_retry_count"]
            if repair_retry_count is None
            else self._clamp_repair_retry_count(repair_retry_count)
        )
        resolved_temperature = (
            float(runtime_defaults["temperature"])
            if temperature is None
            else self._clamp_temperature(temperature)
        )
        resolved_top_p = (
            float(runtime_defaults["top_p"])
            if top_p is None
            else self._clamp_top_p(top_p)
        )
        resolved_top_k = (
            runtime_defaults["top_k"] if top_k is None else self._clamp_top_k(top_k)
        )
        resolved_output_mode = self._resolve_output_mode(output_mode)

        attempts: list[tuple[str, dict[str, Any]]] = [
            (
                "primary",
                build_label_request_payload(
                    model=resolved_model,
                    system_prompt=system_prompt,
                    article_input=article,
                    output_schema=output_schema,
                    output_schema_name=resolved_output_schema_name,
                    output_mode=resolved_output_mode,
                    max_tokens=resolved_max_tokens,
                    temperature=resolved_temperature,
                    top_p=resolved_top_p,
                    top_k=resolved_top_k,
                ),
            )
        ]

        last_payload: dict[str, Any] = {}
        last_data: dict[str, Any] = {}
        last_errors: list[str] = []
        last_invalid_output = ""
        last_finish_reason: str | None = None

        repairs_remaining = resolved_repair_retry_count
        while attempts:
            attempt_name, payload = attempts.pop(0)
            data = self._post_chat_completions(
                payload,
                base_url=resolved_base_url,
                api_key=str(api_key or "").strip(),
                timeout_seconds=resolved_timeout_seconds,
            )
            result, invalid_output, validation_errors, finish_reason = (
                extract_validated_label_response(
                    data=data,
                    article_input=article,
                    output_schema=output_schema,
                )
            )
            last_payload = payload
            last_data = data
            last_errors = validation_errors
            last_invalid_output = invalid_output
            last_finish_reason = finish_reason

            if result is not None:
                return build_label_generation_result(
                    result=result,
                    output_mode=resolved_output_mode,
                    selected_attempt=attempt_name,
                    finish_reason=finish_reason,
                    data=data,
                    payload=payload,
                    runtime={
                        "max_tokens": resolved_max_tokens,
                        "timeout_seconds": resolved_timeout_seconds,
                        "repair_retry_count": resolved_repair_retry_count,
                        "temperature": resolved_temperature,
                        "top_p": resolved_top_p,
                        "top_k": resolved_top_k,
                    },
                )

            if repairs_remaining > 0:
                attempts.append(
                    (
                        "repair",
                        build_label_repair_request_payload(
                            model=resolved_model,
                            system_prompt=system_prompt,
                            article_input=article,
                            output_schema=output_schema,
                            output_schema_name=resolved_output_schema_name,
                            output_mode=resolved_output_mode,
                            max_tokens=resolved_max_tokens,
                            temperature=resolved_temperature,
                            top_p=resolved_top_p,
                            top_k=resolved_top_k,
                            invalid_output=last_invalid_output,
                            validation_errors=last_errors,
                        ),
                    )
                )
                repairs_remaining -= 1

        append_finish_reason_diagnostic(last_errors, last_finish_reason)
        raise LabelingValidationError(
            "Label provider returned invalid structured output.",
            validation_errors=last_errors,
            raw_request=last_payload,
            raw_reply=last_data,
        )
