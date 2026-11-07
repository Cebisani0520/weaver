"""Scripted fraud scenarios, as ordered events relative to a start time.

Offsets are scenario time. A player can compress them (time_scale) and stamp
events with the moment they are emitted, so events stay in order on Kafka.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta

from services.generators.transactions.model import (
    AccountEvent,
    AccountEventType,
    Channel,
    Event,
    Transaction,
    hashed_id,
)
from services.generators.transactions.population import Customer

# Placeholder until at() stamps a real time onto the event.
_UNSCHEDULED = datetime(1970, 1, 1, tzinfo=UTC)


@dataclass(frozen=True, slots=True)
class ScheduledEvent:
    offset: timedelta
    event: Event


def _txn(
    customer: Customer, tag: str, amount_rands: int, beneficiary: str, device: str
) -> Transaction:
    return Transaction(
        transaction_id=hashed_id("txn", f"ato-{customer.customer_id}-{tag}"),
        event_time=_UNSCHEDULED,
        customer_id=customer.customer_id,
        account_id=customer.account_id,
        device_id=device,
        channel=Channel.PAYSHAP,
        amount_cents=amount_rands * 100,
        province=customer.home_province,
        beneficiary_id=beneficiary,
    )


def _acct(
    customer: Customer,
    tag: str,
    event_type: AccountEventType,
    *,
    device: str | None = None,
    beneficiary: str | None = None,
) -> AccountEvent:
    return AccountEvent(
        event_id=hashed_id("evt", f"ato-{customer.customer_id}-{tag}"),
        event_time=_UNSCHEDULED,
        customer_id=customer.customer_id,
        event_type=event_type,
        device_id=device,
        beneficiary_id=beneficiary,
    )


def account_takeover(customer: Customer) -> list[ScheduledEvent]:
    """Journey 2 from the plan: SIM swap, new device, new payees, rapid PayShap drain.

    Offsets are from the SIM swap (01:52 SAST in the plan's example).
    """
    device = hashed_id("dev", f"ato-{customer.customer_id}-fraudster")
    mule_a = hashed_id("bene", f"ato-{customer.customer_id}-mule-a")
    mule_b = hashed_id("bene", f"ato-{customer.customer_id}-mule-b")
    mule_c = hashed_id("bene", f"ato-{customer.customer_id}-mule-c")
    m = timedelta(minutes=1)
    s = timedelta(seconds=1)
    return [
        ScheduledEvent(0 * m, _acct(customer, "sim", AccountEventType.SIM_SWAP)),
        ScheduledEvent(
            6 * m, _acct(customer, "login", AccountEventType.NEW_DEVICE_LOGIN, device=device)
        ),
        ScheduledEvent(
            10 * m,
            _acct(customer, "bene-a", AccountEventType.BENEFICIARY_ADDED, beneficiary=mule_a),
        ),
        ScheduledEvent(11 * m, _txn(customer, "t1", 4_800, mule_a, device)),
        ScheduledEvent(13 * m, _txn(customer, "t2", 4_900, mule_a, device)),
        ScheduledEvent(
            13 * m + 30 * s,
            _acct(customer, "bene-b", AccountEventType.BENEFICIARY_ADDED, beneficiary=mule_b),
        ),
        ScheduledEvent(
            13 * m + 40 * s,
            _acct(customer, "bene-c", AccountEventType.BENEFICIARY_ADDED, beneficiary=mule_c),
        ),
        ScheduledEvent(14 * m, _txn(customer, "t3", 4_850, mule_b, device)),
        ScheduledEvent(15 * m, _txn(customer, "t4", 4_950, mule_c, device)),
        ScheduledEvent(16 * m, _txn(customer, "t5", 4_700, mule_b, device)),
        ScheduledEvent(17 * m, _txn(customer, "t6", 4_800, mule_c, device)),
    ]


SCENARIOS = {"account-takeover": account_takeover}


def at(scheduled: list[ScheduledEvent], start: datetime, time_scale: float = 1.0) -> list[Event]:
    """Stamp a scenario onto real time: start + offset / time_scale."""
    if start.tzinfo is None:
        raise ValueError("start must be timezone-aware")
    return [replace(item.event, event_time=start + item.offset / time_scale) for item in scheduled]
