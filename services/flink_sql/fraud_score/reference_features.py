"""Reference implementation of the fraud features in plain Python.

This is the specification features.sql must match. It is deliberately simple:
for each transaction it scans the customer's events directly. Tests compare the
Flink output (local PyFlink, or the live txn-features topic) against it.

Window semantics follow Flink's RANGE OVER windows: an event at time e is in the
window of a transaction at time t when t - range <= e <= t, so events with the
same timestamp as the transaction are included.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta

from services.generators.transactions.model import (
    AccountEvent,
    AccountEventType,
    Event,
    Transaction,
)

FEATURE_VERSION = "v1"
SAST_OFFSET = timedelta(hours=2)  # South Africa has no daylight saving


@dataclass(frozen=True, slots=True)
class Features:
    transaction_id: str
    customer_id: str
    amount_cents: int
    channel: str
    province: str
    txn_count_1h: int
    txn_count_24h: int
    distinct_provinces_24h: int
    avg_amount_30d_cents: float
    amount_to_avg_30d: float
    is_new_beneficiary: bool
    sim_swap_72h: bool
    is_new_device: bool
    is_night_sast: bool
    feature_version: str = FEATURE_VERSION


def _txns_in(own: list[Transaction], end: datetime, hours: float) -> list[Transaction]:
    start = end - timedelta(hours=hours)
    return [o for o in own if start <= o.event_time <= end]


def _acct_in(events: list[AccountEvent], end: datetime, hours: float) -> list[AccountEvent]:
    start = end - timedelta(hours=hours)
    return [a for a in events if start <= a.event_time <= end]


def compute(events: list[Event]) -> dict[str, Features]:
    """Features for every transaction in `events`, keyed by transaction_id."""
    txns: dict[str, list[Transaction]] = defaultdict(list)
    acct: dict[str, list[AccountEvent]] = defaultdict(list)
    for event in events:
        if isinstance(event, Transaction):
            txns[event.customer_id].append(event)
        else:
            acct[event.customer_id].append(event)

    result: dict[str, Features] = {}
    for customer_id, own in txns.items():
        account_events = acct.get(customer_id, [])
        for txn in own:
            t = txn.event_time
            last_30d = _txns_in(own, t, 24 * 30)
            avg = sum(o.amount_cents for o in last_30d) / len(last_30d)
            last_24h = _txns_in(own, t, 24)
            acct_24h = _acct_in(account_events, t, 24)

            result[txn.transaction_id] = Features(
                transaction_id=txn.transaction_id,
                customer_id=customer_id,
                amount_cents=txn.amount_cents,
                channel=str(txn.channel),
                province=txn.province,
                txn_count_1h=len(_txns_in(own, t, 1)),
                txn_count_24h=len(last_24h),
                distinct_provinces_24h=len({o.province for o in last_24h}),
                avg_amount_30d_cents=avg,
                amount_to_avg_30d=txn.amount_cents / avg,
                is_new_beneficiary=txn.beneficiary_id is not None
                and any(
                    a.event_type is AccountEventType.BENEFICIARY_ADDED
                    and a.beneficiary_id == txn.beneficiary_id
                    for a in acct_24h
                ),
                sim_swap_72h=any(
                    a.event_type is AccountEventType.SIM_SWAP
                    for a in _acct_in(account_events, t, 72)
                ),
                is_new_device=txn.device_id is not None
                and any(
                    a.event_type is AccountEventType.NEW_DEVICE_LOGIN
                    and a.device_id == txn.device_id
                    for a in acct_24h
                ),
                is_night_sast=(t + SAST_OFFSET).hour < 5,
            )
    return result
