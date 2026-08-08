"""Turning token counts into an estimated cost.

An *estimate*, and named that way everywhere it appears. Prices change, the
provider bills on its own meter, and a per-model table in an application is
always slightly out of date. The number is here to make spend legible on a
dashboard and to give the cap something human to report — not to reconcile an
invoice.

The cap itself is enforced on **tokens**, not on this figure, precisely because
tokens are what the provider actually reported. Enforcing on a derived price
would mean a stale table silently moving the limit.
"""

from decimal import Decimal


# USD per million tokens, as published for these models. Kept as strings and
# converted to Decimal: a price summed over millions of tokens is money, and
# money in binary floating point accumulates error.
PRICES_PER_MILLION: dict[str, dict[str, str]] = {
    "text-embedding-3-small": {"input": "0.02", "output": "0"},
    "text-embedding-3-large": {"input": "0.13", "output": "0"},
    "gpt-4o-mini": {"input": "0.15", "output": "0.60"},
    "gpt-4o": {"input": "2.50", "output": "10.00"},
}

# What an unknown model costs. Zero, so a model nobody priced does not invent
# spend — and the fact that it is unpriced is logged rather than guessed at.
UNKNOWN = {"input": "0", "output": "0"}

MILLION = Decimal(1_000_000)


def _prices(model: str) -> dict[str, str]:
    if model in PRICES_PER_MILLION:
        return PRICES_PER_MILLION[model]
    # Providers append a dated suffix to a model name — "gpt-4o-mini-2024-07-18"
    # is the same price as "gpt-4o-mini", and an exact-match table would treat
    # every pinned deployment as unpriced.
    for known, prices in PRICES_PER_MILLION.items():
        if model.startswith(known):
            return prices
    return UNKNOWN


def is_priced(model: str) -> bool:
    return _prices(model) is not UNKNOWN


def estimate_cost_usd(
    *,
    model: str,
    input_tokens: int = 0,
    output_tokens: int = 0,
) -> Decimal:
    prices = _prices(model)
    return (
        Decimal(input_tokens) * Decimal(prices["input"])
        + Decimal(output_tokens) * Decimal(prices["output"])
    ) / MILLION
