"""OpenAIProvider tests. All of these inject a fake SDK client — none call
the real OpenAI API or the network."""

import httpx
import openai
import pytest

from app.llm.openai_provider import OpenAIProvider
from app.llm.provider import ProviderError, ProviderTimeoutError


class _FakeUsage:
    def __init__(self, input_tokens: int, output_tokens: int, total_tokens: int) -> None:
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        self.total_tokens = total_tokens


class _FakeResponse:
    def __init__(self, output_text: str, usage: _FakeUsage) -> None:
        self.output_text = output_text
        self.usage = usage


class _FakeResponsesResource:
    def __init__(self, outcome) -> None:
        self._outcome = outcome
        self.calls: list[dict] = []

    def create(self, *, model: str, input: str):
        self.calls.append({"model": model, "input": input})
        if isinstance(self._outcome, Exception):
            raise self._outcome
        return self._outcome


class _FakeOpenAIClient:
    def __init__(self, outcome) -> None:
        self.responses = _FakeResponsesResource(outcome)


def _dummy_request() -> httpx.Request:
    return httpx.Request("POST", "https://api.openai.com/v1/responses")


class TestOpenAIProviderSuccess:
    def test_maps_raw_response_and_tokens(self) -> None:
        fake_client = _FakeOpenAIClient(
            _FakeResponse(
                '{"category": "billing", "priority": "high", "summary": "x", '
                '"recommended_action": "y"}',
                _FakeUsage(input_tokens=42, output_tokens=17, total_tokens=59),
            )
        )
        provider = OpenAIProvider(api_key="sk-test", client=fake_client)

        result = provider.generate(prompt="rendered prompt", model="gpt-5-mini")

        assert result.raw_response == fake_client.responses._outcome.output_text
        assert result.input_tokens == 42
        assert result.output_tokens == 17
        assert result.total_tokens == 59

    def test_sends_rendered_prompt_and_model(self) -> None:
        fake_client = _FakeOpenAIClient(_FakeResponse("{}", _FakeUsage(1, 1, 2)))
        provider = OpenAIProvider(api_key="sk-test", client=fake_client)

        provider.generate(prompt="rendered prompt text", model="gpt-5-nano")

        assert fake_client.responses.calls == [
            {"model": "gpt-5-nano", "input": "rendered prompt text"}
        ]

    def test_captures_latency_via_monotonic_timer(self, monkeypatch) -> None:
        fake_client = _FakeOpenAIClient(_FakeResponse("{}", _FakeUsage(1, 1, 2)))
        provider = OpenAIProvider(api_key="sk-test", client=fake_client)

        ticks = iter([100.0, 100.25])
        monkeypatch.setattr(
            "app.llm.openai_provider.time.monotonic", lambda: next(ticks)
        )

        result = provider.generate(prompt="p", model="gpt-5-mini")

        assert result.latency_ms == 250

    def test_does_not_pass_structured_output_format(self) -> None:
        # Requesting an ordinary text response is load-bearing for this
        # project: strict Structured Outputs would guarantee valid JSON,
        # which defeats the point of measuring schema-validity failures.
        fake_client = _FakeOpenAIClient(_FakeResponse("{}", _FakeUsage(1, 1, 2)))
        provider = OpenAIProvider(api_key="sk-test", client=fake_client)

        provider.generate(prompt="p", model="gpt-5-mini")

        call = fake_client.responses.calls[0]
        assert "format" not in call
        assert "text" not in call
        assert "response_format" not in call


class TestOpenAIProviderFailureClassification:
    def test_missing_usage_is_handled_as_provider_error_not_a_crash(self) -> None:
        # response.usage is typed Optional in the SDK and can genuinely be
        # None (e.g. an incomplete/errored generation). This must be
        # classified like any other provider failure, not raise a bare
        # AttributeError that would escape per-run failure handling.
        fake_client = _FakeOpenAIClient(_FakeResponse("", usage=None))
        provider = OpenAIProvider(api_key="sk-test", client=fake_client)

        with pytest.raises(ProviderError) as excinfo:
            provider.generate(prompt="p", model="gpt-5-mini")

        assert not isinstance(excinfo.value, ProviderTimeoutError)

    def test_timeout_is_classified_as_provider_timeout_error(self) -> None:
        fake_client = _FakeOpenAIClient(openai.APITimeoutError(_dummy_request()))
        provider = OpenAIProvider(api_key="sk-test", client=fake_client)

        with pytest.raises(ProviderTimeoutError):
            provider.generate(prompt="p", model="gpt-5-mini")

    def test_other_provider_error_is_classified_separately_from_timeout(self) -> None:
        fake_client = _FakeOpenAIClient(
            openai.APIConnectionError(request=_dummy_request())
        )
        provider = OpenAIProvider(api_key="sk-test", client=fake_client)

        with pytest.raises(ProviderError) as excinfo:
            provider.generate(prompt="p", model="gpt-5-mini")

        assert not isinstance(excinfo.value, ProviderTimeoutError)

    def test_error_message_is_sanitized(self) -> None:
        secret_laden_message = (
            "Authorization: Bearer sk-super-secret-key-do-not-leak; "
            "payload={'ticket_text': 'private customer data'}"
        )
        fake_client = _FakeOpenAIClient(
            openai.APIConnectionError(
                message=secret_laden_message, request=_dummy_request()
            )
        )
        provider = OpenAIProvider(api_key="sk-test", client=fake_client)

        with pytest.raises(ProviderError) as excinfo:
            provider.generate(prompt="p", model="gpt-5-mini")

        assert "sk-super-secret-key-do-not-leak" not in str(excinfo.value)
        assert "private customer data" not in str(excinfo.value)
        assert len(str(excinfo.value)) < 200
