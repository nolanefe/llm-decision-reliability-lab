"""Provider-neutral contract for LLM runner implementations.

The executor depends only on this module, never on a concrete SDK, so tests
can inject a fake provider instead of calling a real model API.
"""

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class ProviderResult:
    """The outcome of a single successful provider call."""

    raw_response: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    latency_ms: int


class ProviderError(Exception):
    """A provider call failed for a reason other than a timeout.

    The message must already be short and sanitized: never include API
    keys, request/response payloads, or raw SDK exception text.
    """


class ProviderTimeoutError(ProviderError):
    """A provider call did not complete within the configured timeout."""


class LLMProvider(Protocol):
    """A model provider capable of generating a single text completion."""

    def generate(self, *, prompt: str, model: str) -> ProviderResult:
        """Send ``prompt`` to ``model`` and return the raw text result.

        Raises ``ProviderTimeoutError`` on a timeout and ``ProviderError``
        for any other provider failure.
        """
        ...
