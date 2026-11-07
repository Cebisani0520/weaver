"""Unit tests for the transaction generator."""

from __future__ import annotations

import io
import itertools
import json
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from services.generators.transactions.__main__ import main
from services.generators.transactions.model import (
    AccountEvent,
    AccountEventType,
    Channel,
    Transaction,
    to_json_record,
)
from services.generators.transactions.player import LivePlan, play_history, play_live
from services.generators.transactions.population import build_population
from services.generators.transactions.scenarios import account_takeover, at
from services.generators.transactions.sinks import JsonLinesSink, ListSink
from services.generators.transactions.traffic import history

START = datetime(2026, 11, 2, 0, 0, tzinfo=UTC)


def avro_fields(repo_root: Path, topic: str) -> set[str]:
    schema = json.loads(
        (repo_root / f"infra/environments/local/schemas/{topic}/value.avsc").read_text()
    )
    return {field["name"] for field in schema["fields"]}


def test_population_is_deterministic() -> None:
    assert build_population(10, seed=3) == build_population(10, seed=3)
    ids = [c.customer_id for c in build_population(50)]
    assert len(set(ids)) == 50
    assert all(re.fullmatch(r"cust_[0-9a-f]{16}", i) for i in ids)


def test_history_is_time_ordered_and_in_range() -> None:
    events = list(history(build_population(30), START, START + timedelta(hours=48)))
    assert events, "48 hours for 30 customers should produce payments"
    times = [e.event_time for e in events]
    assert times == sorted(times)
    assert times[0] >= START and times[-1] < START + timedelta(hours=48)


def test_normal_payments_are_well_formed() -> None:
    for event in history(build_population(30), START, START + timedelta(hours=48)):
        assert isinstance(event, Transaction)
        assert event.amount_cents >= 500
        assert event.currency == "ZAR"
        card = event.channel in (Channel.CARD_PRESENT, Channel.CARD_ONLINE)
        transfer = event.channel in (Channel.PAYSHAP, Channel.EFT)
        assert (event.merchant_category is not None) == card
        assert (event.beneficiary_id is not None) == transfer
        assert (event.device_id is None) == (event.channel is Channel.CARD_PRESENT)


def test_records_match_avro_schemas(repo_root: Path) -> None:
    customer = build_population(1)[0]
    events = at(account_takeover(customer), START)
    txn = next(e for e in events if isinstance(e, Transaction))
    acct = next(e for e in events if isinstance(e, AccountEvent))
    assert set(txn.to_record()) == avro_fields(repo_root, "transactions")
    assert set(acct.to_record()) == avro_fields(repo_root, "account-events")


def test_account_takeover_follows_the_plan() -> None:
    customer = build_population(5)[-1]
    events = at(account_takeover(customer), START)
    kinds = [e.event_type if isinstance(e, AccountEvent) else Channel(e.channel) for e in events]
    assert kinds[:3] == [
        AccountEventType.SIM_SWAP,
        AccountEventType.NEW_DEVICE_LOGIN,
        AccountEventType.BENEFICIARY_ADDED,
    ]
    payments = [e for e in events if isinstance(e, Transaction)]
    assert len(payments) == 6
    assert {p.channel for p in payments} == {Channel.PAYSHAP}
    assert len({p.beneficiary_id for p in payments}) == 3
    assert [p.amount_cents for p in payments[:2]] == [480_000, 490_000]
    assert events[-1].event_time - events[0].event_time == timedelta(minutes=17)


def test_time_scale_compresses_the_scenario() -> None:
    customer = build_population(1)[0]
    events = at(account_takeover(customer), START, time_scale=60)
    assert events[-1].event_time - events[0].event_time == timedelta(seconds=17)


def test_naive_start_is_rejected() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        at(account_takeover(build_population(1)[0]), datetime(2026, 1, 1))


def test_json_record_uses_epoch_millis() -> None:
    customer = build_population(1)[0]
    event = at(account_takeover(customer), START)[0]
    record = to_json_record(event)
    assert record["event_time"] == int(START.timestamp() * 1000)
    assert record["topic"] == "account-events"


class FakeClock:
    def __init__(self, start: datetime) -> None:
        self.now = start

    def __call__(self) -> datetime:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.now += timedelta(seconds=seconds)


def test_live_play_is_ordered_and_includes_the_scenario() -> None:
    customers = build_population(20)
    victim = customers[-1]
    clock = FakeClock(START)
    sink = ListSink()
    plan = LivePlan(
        rate_per_second=5,
        duration=timedelta(seconds=30),
        scenario="account-takeover",
        scenario_after=timedelta(seconds=5),
        time_scale=60,
    )
    sent = play_live(customers, plan, sink, victim, clock=clock, sleep=clock.sleep)
    assert sent == len(sink.events)
    times = [e.event_time for e in sink.events]
    assert all(a < b for a, b in itertools.pairwise(times)), "strictly increasing"
    victim_events = [e for e in sink.events if e.customer_id == victim.customer_id]
    assert len(victim_events) == 11
    assert isinstance(victim_events[0], AccountEvent)
    others = [e for e in sink.events if e.customer_id != victim.customer_id]
    assert others and all(isinstance(e, Transaction) for e in others)


def test_history_then_live_stays_ordered() -> None:
    customers = build_population(10)
    clock = FakeClock(START + timedelta(hours=6))
    sink = ListSink()
    play_history(customers, 6, sink, end=clock())
    play_live(
        customers,
        LivePlan(rate_per_second=2, duration=timedelta(seconds=10)),
        sink,
        clock=clock,
        sleep=clock.sleep,
    )
    times = [e.event_time for e in sink.events]
    assert times == sorted(times)


def test_jsonl_sink_and_cli(capsys: pytest.CaptureFixture[str]) -> None:
    stream = io.StringIO()
    sink = JsonLinesSink(stream)
    sink.send(at(account_takeover(build_population(1)[0]), START)[0])
    sink.close()
    assert json.loads(stream.getvalue())["event_type"] == "SIM_SWAP"

    assert main(["--customers", "5", "--history-hours", "48"]) == 0
    lines = capsys.readouterr().out.strip().splitlines()
    assert lines and all(json.loads(line)["topic"] == "transactions" for line in lines)


def test_cli_rejects_a_scenario_that_cannot_play() -> None:
    assert main(["--scenario", "account-takeover", "--live", "5", "--scenario-after", "10"]) == 2
