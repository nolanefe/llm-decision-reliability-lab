"""Shared test doubles. No test may import the real openai SDK client."""

from dataclasses import dataclass, field

from app.llm.provider import ProviderResult


def make_result(
    raw_response: str,
    *,
    input_tokens: int = 10,
    output_tokens: int = 20,
    latency_ms: int = 100,
) -> ProviderResult:
    return ProviderResult(
        raw_response=raw_response,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=input_tokens + output_tokens,
        latency_ms=latency_ms,
    )


@dataclass
class ScriptedCall:
    prompt: str
    model: str


@dataclass
class ScriptedProvider:
    """A fake LLMProvider that replays one scripted outcome per call, in
    order. Each item in ``outcomes`` is either a ``ProviderResult`` to
    return or an ``Exception`` instance to raise."""

    outcomes: list
    calls: list[ScriptedCall] = field(default_factory=list)

    def generate(self, *, prompt: str, model: str) -> ProviderResult:
        self.calls.append(ScriptedCall(prompt=prompt, model=model))
        outcome = self.outcomes[len(self.calls) - 1]
        if isinstance(outcome, Exception):
            raise outcome
        return outcome
