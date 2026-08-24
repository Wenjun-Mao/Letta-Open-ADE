from __future__ import annotations

from typing import Any

from ade_api.integrations.model_router.openai_chat import (
    RETRYABLE_OPENAI_CHAT_EXCEPTIONS,
    OpenAIChatClient,
    chat_completions_url,
    parse_sse_chat_completion_response,
    resolve_provider_model,
)
from ade_api.platform.settings import get_settings
from ade_api.features.comment_lab.request_builder import (
    build_comment_request_payload,
    build_structured_output_compatibility_payload,
)
from ade_api.features.comment_lab.response_mapper import (
    map_comment_provider_response,
)


DEFAULT_COMMENTING_RETRY_COUNT = 0
MAX_COMMENTING_RETRY_COUNT = 5
DEFAULT_COMMENTING_CACHE_PROMPT = False
DEFAULT_COMMENTING_TEMPERATURE = 0.6
DEFAULT_COMMENTING_TOP_P = 1.0
DEFAULT_COMMENTING_TOP_K: int | None = None
_RETRYABLE_COMMENTING_EXCEPTIONS = RETRYABLE_OPENAI_CHAT_EXCEPTIONS


class CommentingService:
    """Stateless comment generation through an OpenAI-compatible chat completions API."""

    _TASK_SHAPES = {"classic", "all_in_system", "structured_output"}

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
            # `0` is treated as "no max_tokens parameter" for provider requests.
            return 0
        return max(64, min(8192, int(value)))

    @staticmethod
    def _clamp_timeout_seconds(value: float) -> float:
        return max(5.0, min(600.0, float(value)))

    @staticmethod
    def _clamp_retry_count(value: int | None) -> int:
        if value is None:
            return DEFAULT_COMMENTING_RETRY_COUNT
        return max(0, min(MAX_COMMENTING_RETRY_COUNT, int(value)))

    @staticmethod
    def _clamp_temperature(value: float | None) -> float:
        return (
            DEFAULT_COMMENTING_TEMPERATURE
            if value is None
            else max(0.0, min(2.0, float(value)))
        )

    @staticmethod
    def _clamp_top_p(value: float | None) -> float:
        return (
            DEFAULT_COMMENTING_TOP_P
            if value is None
            else max(0.01, min(1.0, float(value)))
        )

    @staticmethod
    def _clamp_top_k(value: int | None) -> int | None:
        if value is None:
            return DEFAULT_COMMENTING_TOP_K
        return max(1, min(1000, int(value)))

    @classmethod
    def _resolve_task_shape(cls, value: str | None) -> str:
        resolved = str(value or "").strip().lower()
        if not resolved:
            return "classic"
        if resolved in cls._TASK_SHAPES:
            return resolved
        raise ValueError(f"Unsupported task_shape: {resolved}")

    def runtime_defaults(self) -> dict[str, Any]:
        settings = self._settings_factory()
        return {
            "max_tokens": self._clamp_max_tokens(settings.comment_lab_max_tokens),
            "timeout_seconds": self._clamp_timeout_seconds(
                settings.comment_lab_timeout_seconds
            ),
            "task_shape": self._resolve_task_shape(settings.comment_lab_task_shape),
            "cache_prompt": bool(settings.comment_lab_cache_prompt),
            "temperature": self._clamp_temperature(settings.comment_lab_temperature),
            "top_p": self._clamp_top_p(settings.comment_lab_top_p),
            "top_k": self._clamp_top_k(settings.comment_lab_top_k),
        }

    @staticmethod
    def _chat_completions_url(base_url: str) -> str:
        return chat_completions_url(base_url)

    @classmethod
    def _resolve_provider_model(cls, model: str) -> str:
        return resolve_provider_model(model)

    def _post_chat_completions_once(
        self,
        payload: dict[str, Any],
        *,
        base_url: str,
        api_key: str,
        timeout_seconds: float,
    ) -> dict[str, Any]:
        return self._provider_client.post_chat_completions_once(
            payload,
            base_url=base_url,
            api_key=api_key,
            timeout_seconds=timeout_seconds,
        )

    def _post_chat_completions(
        self,
        payload: dict[str, Any],
        *,
        base_url: str,
        api_key: str,
        timeout_seconds: float,
        retry_count: int,
    ) -> dict[str, Any]:
        return self._provider_client.run_with_retries(
            lambda: self._post_chat_completions_once(
                payload,
                base_url=base_url,
                api_key=api_key,
                timeout_seconds=timeout_seconds,
            ),
            self._build_retrying(retry_count),
        )

    def _build_retrying(self, retry_count: int):
        return self._provider_client.build_retrying(
            self._clamp_retry_count(retry_count)
        )

    def generate_comment(
        self,
        *,
        base_url: str,
        api_key: str = "",
        model: str,
        system_prompt: str,
        persona_prompt: str,
        news_input: str,
        max_tokens: int | None = None,
        timeout_seconds: float | None = None,
        retry_count: int | None = None,
        task_shape: str | None = None,
        source_adapter: str | None = None,
        cache_prompt: bool | None = None,
        enable_thinking: bool | None = None,
        temperature: float | None = None,
        top_p: float | None = None,
        top_k: int | None = None,
    ) -> dict[str, Any]:
        resolved_base_url = str(base_url or "").strip()
        if not resolved_base_url:
            raise ValueError("base_url is required")

        resolved_model = self._resolve_provider_model(str(model or ""))
        if not resolved_model:
            raise ValueError("model is required")

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
        resolved_retry_count = self._clamp_retry_count(retry_count)
        resolved_task_shape = (
            runtime_defaults["task_shape"]
            if task_shape is None
            else self._resolve_task_shape(task_shape)
        )
        resolved_cache_prompt = (
            bool(runtime_defaults["cache_prompt"])
            if cache_prompt is None
            else bool(cache_prompt)
        )
        resolved_enable_thinking = (
            False if enable_thinking is None else bool(enable_thinking)
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
        response_runtime = {
            "max_tokens": resolved_max_tokens,
            "timeout_seconds": resolved_timeout_seconds,
            "task_shape": resolved_task_shape,
            "cache_prompt": resolved_cache_prompt,
            "enable_thinking": resolved_enable_thinking,
            "temperature": resolved_temperature,
            "top_p": resolved_top_p,
            "top_k": resolved_top_k,
        }

        payload = build_comment_request_payload(
            model=resolved_model,
            system_prompt=system_prompt,
            persona_prompt=persona_prompt,
            news_input=news_input,
            task_shape=resolved_task_shape,
            max_tokens=resolved_max_tokens,
            cache_prompt=resolved_cache_prompt,
            source_adapter=source_adapter,
            enable_thinking=resolved_enable_thinking,
            enable_thinking_is_explicit=enable_thinking is not None,
            temperature=resolved_temperature,
            top_p=resolved_top_p,
            top_k=resolved_top_k,
        )

        try:
            data = self._post_chat_completions(
                payload,
                base_url=resolved_base_url,
                api_key=str(api_key or "").strip(),
                timeout_seconds=resolved_timeout_seconds,
                retry_count=resolved_retry_count,
            )
        except ValueError as exc:
            # Some OpenAI-compatible runtimes reject `response_format` when strict
            # structured decoding is disabled. Fall back to prompt-enforced JSON.
            if resolved_task_shape != "structured_output":
                raise

            error_text = str(exc).lower()
            if "response_format" not in error_text and "json_schema" not in error_text:
                raise

            payload = build_structured_output_compatibility_payload(payload)
            data = self._post_chat_completions(
                payload,
                base_url=resolved_base_url,
                api_key=str(api_key or "").strip(),
                timeout_seconds=resolved_timeout_seconds,
                retry_count=resolved_retry_count,
            )

        return map_comment_provider_response(
            data=data,
            payload=payload,
            runtime=response_runtime,
            task_shape=resolved_task_shape,
            max_tokens=resolved_max_tokens,
        )

    @staticmethod
    def _parse_sse_chat_completion_response(raw_text: str) -> dict[str, Any] | None:
        return parse_sse_chat_completion_response(raw_text)
