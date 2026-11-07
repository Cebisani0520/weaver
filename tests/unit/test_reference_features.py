"""The reference feature definitions, checked against hand-worked cases."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from services.flink_sql.fraud_score.reference_features import compute
from services.generators.transactions.model import (
    AccountEvent,
    AccountEventType,
    Channel,
    Event,
    Transaction,
)
from services.generators.transactions.population import build_population
from services.generators.transactions.scenarios import account_takeover, at
from services.generators.transactions.traffic import history

# 01:52 SAST on 2 November 2026, the plan's example time.
ATO_START = datetime(2026, 11, 1, 23, 52, tzinfo=UTC)


def txn(
    tid: str,
    when: datetime,
    amount: int = 10_000,
    province: str = "GP",
    beneficiary: str | None = None,
    device: str | None = "dev_1",
    customer: str = "cust_a",
) -> Transaction:
    return Transaction(
        transaction_id=tid,
        event_time=when,
        customer_id=customer,
        account_id="acct_a",
        device_id=device,
        channel=Channel.PAYSHAP if beneficiary else Channel.CARD_ONLINE,
        amount_cents=amount,
        province=province,
        beneficiary_id=beneficiary,
    )


def acct(
    eid: str,
    when: datetime,
    kind: AccountEventType,
    device: str | None = None,
    beneficiary: str | None = None,
) -> AccountEvent:
    return AccountEvent(
        event_id=eid,
        event_time=when,
        customer_id="cust_a",
        event_type=kind,
        device_id=device,
        beneficiary_id=beneficiary,
    )


T0 = datetime(2026, 11, 2, 12, 0, tzinfo=UTC)


def test_velocity_windows_include_the_current_payment() -> None:
    events: list[Event] = [
        txn("t1", T0 - timedelta(hours=30)),
        txn("t2", T0 - timedelta(hours=5)),
        txn("t3", T0 - timedelta(minutes=30)),
        txn("t4", T0),
    ]
    f = compute(events)["t4"]
    assert (f.txn_count_1h, f.txn_count_24h) == (2, 3)


def test_amount_ratio_against_the_30_day_mean() -> None:
    events: list[Event] = [
        txn("t1", T0 - timedelta(days=40), amount=1_000_000),  # outside 30 days
        txn("t2", T0 - timedelta(days=2), amount=10_000),
        txn("t3", T0, amount=40_000),
    ]
    f = compute(events)["t3"]
    assert f.avg_amount_30d_cents == 25_000
    assert f.amount_to_avg_30d == 1.6


def test_distinct_provinces_in_24_hours() -> None:
    events: list[Event] = [
        txn("t1", T0 - timedelta(hours=26), province="NC"),
        txn("t2", T0 - timedelta(hours=3), province="WC"),
        txn("t3", T0, province="GP"),
    ]
    assert compute(events)["t3"].distinct_provinces_24h == 2


def test_account_event_flags_respect_their_windows_and_ids() -> None:
    events: list[Event] = [
        acct("e1", T0 - timedelta(hours=80), AccountEventType.SIM_SWAP),
        acct("e2", T0 - timedelta(hours=2), AccountEventType.BENEFICIARY_ADDED, beneficiary="b1"),
        acct("e3", T0 - timedelta(hours=30), AccountEventType.NEW_DEVICE_LOGIN, device="dev_9"),
        txn("t1", T0, beneficiary="b1", device="dev_9"),
        txn("t2", T0 + timedelta(minutes=1), beneficiary="b2", device="dev_9"),
    ]
    f1, f2 = compute(events)["t1"], compute(events)["t2"]
    assert f1.is_new_beneficiary and not f2.is_new_beneficiary
    assert not f1.sim_swap_72h, "the SIM swap was 80 hours earlier"
    assert not f1.is_new_device, "the device login was 30 hours earlier"


def test_night_flag_uses_sast() -> None:
    late = datetime(2026, 11, 2, 1, 30, tzinfo=UTC)  # 03:30 SAST
    day = datetime(2026, 11, 2, 3, 30, tzinfo=UTC)  # 05:30 SAST
    events: list[Event] = [txn("n", late), txn("d", day)]
    features = compute(events)
    assert features["n"].is_night_sast and not features["d"].is_night_sast


def test_account_takeover_lights_up_every_signal() -> None:
    customers = build_population(20)
    victim = customers[-1]
    baseline = list(history(customers, ATO_START - timedelta(days=3), ATO_START))
    scenario = at(account_takeover(victim), ATO_START)
    features = compute(baseline + scenario)

    drained = [f for f in features.values() if f.transaction_id.startswith("txn_")]
    takeover = [features[e.transaction_id] for e in scenario if isinstance(e, Transaction)]
    assert len(takeover) == 6 and drained
    assert all(f.sim_swap_72h for f in takeover)
    assert all(f.is_new_device for f in takeover)
    assert all(f.is_new_beneficiary for f in takeover)
    assert all(f.is_night_sast for f in takeover)
    assert [f.txn_count_1h for f in takeover] == [1, 2, 3, 4, 5, 6]
    assert takeover[0].amount_to_avg_30d > 3, "R4,800 is far above this customer's mean"
