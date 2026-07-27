"""Centralized OpenAI pricing registry for supported models.

This is a *pricing snapshot*, not a live lookup. OpenAI pricing changes over
time; the figures below must be reviewed and updated by hand as they drift
from https://openai.com/api/pricing/. Do not add a model here without also
adding its confirmed per-token pricing.

Snapshot date: 2026-07-27.
"""

from dataclasses import dataclass
from decimal import Decimal

_MILLION = Decimal("1000000")


@dataclass(frozen=True)
class ModelPricing:
    input_usd_per_million_tokens: Decimal
    output_usd_per_million_tokens: Decimal


PRICING_USD_PER_MILLION_TOKENS: dict[str, ModelPricing] = {
    "gpt-5-mini": ModelPricing(
        input_usd_per_million_tokens=Decimal("0.25"),
        output_usd_per_million_tokens=Decimal("2.00"),
    ),
    "gpt-5-nano": ModelPricing(
        input_usd_per_million_tokens=Decimal("0.05"),
        output_usd_per_million_tokens=Decimal("0.40"),
    ),
}

SUPPORTED_MODELS: frozenset[str] = frozenset(PRICING_USD_PER_MILLION_TOKENS)


class UnsupportedModelError(Exception):
    """Raised when pricing or cost is requested for a model not in the registry."""


def get_pricing(model_name: str) -> ModelPricing:
    try:
        return PRICING_USD_PER_MILLION_TOKENS[model_name]
    except KeyError:
        raise UnsupportedModelError(f"Unsupported model: {model_name}") from None


def calculate_cost_usd(
    model_name: str, input_tokens: int, output_tokens: int
) -> Decimal:
    """Compute exact cost using Decimal arithmetic (never binary float)."""
    pricing = get_pricing(model_name)
    input_cost = Decimal(input_tokens) * pricing.input_usd_per_million_tokens / _MILLION
    output_cost = (
        Decimal(output_tokens) * pricing.output_usd_per_million_tokens / _MILLION
    )
    return input_cost + output_cost
