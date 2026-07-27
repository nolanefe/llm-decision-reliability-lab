"""OpenAI implementation of the provider abstraction.

Uses the Responses API in plain-text mode: no ``response_format``/structured
outputs are requested, because this project measures whether a prompt
reliably produces valid JSON on its own. The raw text the model returns is
captured as-is; nothing here parses, repairs, or validates it — that is the
executor's job.
"""

import logging
import time
from typing import Any, Protocol

import openai
from openai import OpenAI

from app.llm.provider import ProviderError, ProviderResult, ProviderTimeoutError

logger = logging.getLogger(__name__)


class _ResponsesClient(Protocol):
    """The minimal surface of the OpenAI SDK client this provider needs.

    Tests inject a fake object satisfying this shape instead of a real
    ``openai.OpenAI`` client, so no test ever makes a network call.
    """

    responses: Any


class OpenAIProvider:
    def __init__(
        self,
        *,
        api_key: str,
        timeout_seconds: float | None = None,
        client: _ResponsesClient | None = None,
    ) -> None:
        self._client: _ResponsesClient = client or OpenAI(
            api_key=api_key, timeout=timeout_seconds
        )

    def generate(self, *, prompt: str, model: str) -> ProviderResult:
        start = time.monotonic()
        try:
            response = self._client.responses.create(model=model, input=prompt)
        except openai.APITimeoutError as exc:
            logger.warning("openai provider timeout model=%s", model)
            raise ProviderTimeoutError("The OpenAI request timed out.") from exc
        except openai.APIError as exc:
            logger.warning(
                "openai provider error model=%s error_type=%s",
                model,
                type(exc).__name__,
            )
            raise ProviderError(
                f"The OpenAI request failed ({type(exc).__name__})."
            ) from exc
        latency_ms = int((time.monotonic() - start) * 1000)

        usage = response.usage
        if usage is None:
            # The Responses API types usage as optional; a response can come
            # back without it (e.g. an incomplete/errored generation). There
            # is no valid token/cost data to report, so this is a provider
            # error rather than a crash that would abort the whole run loop.
            logger.warning("openai response missing usage data model=%s", model)
            raise ProviderError("The OpenAI response did not include usage data.")

        return ProviderResult(
            raw_response=response.output_text,
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            total_tokens=usage.total_tokens,
            latency_ms=latency_ms,
        )
