"""Normal customer behaviour: payments spread over a time range, in time order."""

from __future__ import annotations

import itertools
import random
from collections.abc import Iterator
from datetime import datetime, timedelta

from services.generators.transactions.model import (
    PROVINCES,
    Channel,
    Event,
    Transaction,
    hashed_id,
)
from services.generators.transactions.population import MERCHANT_CATEGORIES, Customer

# Share of payments a customer makes outside their home province.
TRAVEL_RATE = 0.03

_sequence = itertools.count()


def _transaction_id(customer: Customer, moment: datetime) -> str:
    return hashed_id("txn", f"{customer.customer_id}-{moment.timestamp()}-{next(_sequence)}")


def normal_payment(customer: Customer, moment: datetime, rng: random.Random) -> Transaction:
    """One ordinary payment, in the customer's usual pattern."""
    channel = rng.choices(
        list(customer.channel_weights), weights=list(customer.channel_weights.values())
    )[0]
    amount = max(500, int(rng.lognormvariate(0, 0.5) * customer.typical_amount_cents))
    province = customer.home_province
    if rng.random() < TRAVEL_RATE:
        province = rng.choice([p for p in PROVINCES if p != customer.home_province])

    card = channel in (Channel.CARD_PRESENT, Channel.CARD_ONLINE)
    transfer = channel in (Channel.PAYSHAP, Channel.EFT)
    return Transaction(
        transaction_id=_transaction_id(customer, moment),
        event_time=moment,
        customer_id=customer.customer_id,
        account_id=customer.account_id,
        device_id=None if channel is Channel.CARD_PRESENT else rng.choice(customer.devices),
        channel=channel,
        amount_cents=amount,
        province=province,
        merchant_category=rng.choice(MERCHANT_CATEGORIES) if card else None,
        merchant_id=rng.choice(customer.merchants) if card else None,
        beneficiary_id=rng.choice(customer.beneficiaries) if transfer else None,
    )


def payment_times(
    customer: Customer, start: datetime, end: datetime, rng: random.Random
) -> list[datetime]:
    """Poisson arrivals at the customer's daily rate, mostly in waking hours."""
    times: list[datetime] = []
    rate_per_second = customer.payments_per_day / 86_400
    moment = start
    while True:
        moment += timedelta(seconds=rng.expovariate(rate_per_second))
        if moment >= end:
            return times
        # Thin out night-time payments (00:00-05:00 SAST is 22:00-03:00 UTC).
        sast_hour = (moment.hour + 2) % 24
        if sast_hour < 5 and rng.random() < 0.85:
            continue
        times.append(moment)


def history(
    customers: list[Customer], start: datetime, end: datetime, seed: int = 11
) -> Iterator[Event]:
    """Every customer's normal payments between start and end, in time order."""
    rng = random.Random(seed)
    events: list[Event] = []
    for customer in customers:
        for moment in payment_times(customer, start, end, rng):
            events.append(normal_payment(customer, moment, rng))
    events.sort(key=lambda e: e.event_time)
    yield from events
