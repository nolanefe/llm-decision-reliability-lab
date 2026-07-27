from decimal import Decimal

import pytest

from app.llm.pricing import SUPPORTED_MODELS, UnsupportedModelError, calculate_cost_usd


class TestSupportedModels:
    def test_supported_models_are_exactly_v0_1_set(self) -> None:
        assert SUPPORTED_MODELS == frozenset({"gpt-5-mini", "gpt-5-nano"})


class TestCalculateCostUsd:
    def test_gpt_5_mini_pricing(self) -> None:
        cost = calculate_cost_usd("gpt-5-mini", input_tokens=1_000_000, output_tokens=1_000_000)

        assert cost == Decimal("2.25")

    def test_gpt_5_nano_pricing(self) -> None:
        cost = calculate_cost_usd("gpt-5-nano", input_tokens=1_000_000, output_tokens=1_000_000)

        assert cost == Decimal("0.45")

    def test_uses_exact_decimal_arithmetic_not_binary_float(self) -> None:
        # 333 input tokens @ $0.25/1M + 777 output tokens @ $2.00/1M.
        # Computed with binary floats this would drift from the exact value.
        cost = calculate_cost_usd("gpt-5-mini", input_tokens=333, output_tokens=777)

        assert cost == Decimal("0.00163725")
        assert isinstance(cost, Decimal)

    def test_zero_tokens_is_zero_cost(self) -> None:
        cost = calculate_cost_usd("gpt-5-mini", input_tokens=0, output_tokens=0)

        assert cost == Decimal("0")

    def test_unsupported_model_is_rejected_not_silently_zero(self) -> None:
        with pytest.raises(UnsupportedModelError):
            calculate_cost_usd("gpt-4o-mini", input_tokens=100, output_tokens=100)
