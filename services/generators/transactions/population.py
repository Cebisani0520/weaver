"""Synthetic customers with stable habits: home province, devices, payees, spend."""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from services.generators.transactions.model import PROVINCES, Channel, hashed_id

# Rough channel mix for a South African retail banking customer.
CHANNEL_WEIGHTS: dict[Channel, float] = {
    Channel.CARD_PRESENT: 0.45,
    Channel.CARD_ONLINE: 0.20,
    Channel.PAYSHAP: 0.15,
    Channel.EFT: 0.10,
    Channel.WALLET: 0.10,
}

# ISO 18245 merchant category codes common in everyday spend.
MERCHANT_CATEGORIES = ("5411", "5541", "5812", "5912", "5311", "4121", "5999", "4814")

# Province weights, roughly by population.
PROVINCE_WEIGHTS = (0.26, 0.12, 0.19, 0.11, 0.05, 0.08, 0.10, 0.07, 0.02)


@dataclass(frozen=True, slots=True)
class Customer:
    index: int
    customer_id: str
    account_id: str
    home_province: str
    devices: tuple[str, ...]
    beneficiaries: tuple[str, ...]
    merchants: tuple[str, ...]
    typical_amount_cents: int
    payments_per_day: float
    channel_weights: dict[Channel, float] = field(default_factory=lambda: dict(CHANNEL_WEIGHTS))


def make_customer(index: int, rng: random.Random, prefix: str = "") -> Customer:
    """One customer. `prefix` namespaces IDs, so separate runs never share customers."""
    name = f"{prefix}{index}"
    return Customer(
        index=index,
        customer_id=hashed_id("cust", name),
        account_id=hashed_id("acct", name),
        home_province=rng.choices(PROVINCES, weights=PROVINCE_WEIGHTS)[0],
        devices=tuple(hashed_id("dev", f"{name}-{d}") for d in range(rng.randint(1, 2))),
        beneficiaries=tuple(hashed_id("bene", f"{name}-{b}") for b in range(rng.randint(2, 6))),
        merchants=tuple(hashed_id("merch", f"{rng.randint(0, 499)}") for _ in range(8)),
        # Median spend about R350, with a long tail.
        typical_amount_cents=int(rng.lognormvariate(10.4, 0.6)),
        payments_per_day=rng.uniform(1.5, 6.0),
    )


def build_population(size: int, seed: int = 7, prefix: str = "") -> list[Customer]:
    rng = random.Random(seed)
    return [make_customer(i, rng, prefix) for i in range(size)]
