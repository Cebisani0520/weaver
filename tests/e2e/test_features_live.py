"""Gate 2, live: events through Kafka and CMF come back as the expected features.

Sends live traffic for a fresh set of customers plus the account-takeover
scenario, reads `txn-features`, and compares every row with the reference
implementation. Run with `mise run gate2` once `mise run deploy local` has the
feature statement RUNNING.
"""

from __future__ import annotations

import math
import random
import socket
import time
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from services.flink_sql.fraud_score.reference_features import compute
from services.generators.transactions.model import Transaction
from services.generators.transactions.player import LivePlan, play_live
from services.generators.transactions.population import build_population
from services.generators.transactions.sinks import ListSink, TeeSink
from services.generators.transactions.traffic import normal_payment

BOOTSTRAP = "localhost:9092"
SCHEMA_REGISTRY = "http://localhost:8081"
FEATURES_TOPIC = "txn-features"
WAIT_FOR_FEATURES = timedelta(minutes=3)


def _listening(port: int) -> bool:
    try:
        with socket.create_connection(("localhost", port), timeout=1):
            return True
    except OSError:
        return False


confluent_kafka = pytest.importorskip("confluent_kafka")
pytestmark = [
    pytest.mark.e2e,
    pytest.mark.skipif(
        not (_listening(9092) and _listening(8081)), reason="local runtime is not up"
    ),
]


def _consumer(start: datetime) -> Any:
    from confluent_kafka import Consumer, TopicPartition

    consumer = Consumer(
        {
            "bootstrap.servers": BOOTSTRAP,
            "group.id": f"weaver-gate2-{uuid.uuid4().hex[:8]}",
            "enable.auto.commit": False,
            "auto.offset.reset": "earliest",
        }
    )
    metadata = consumer.list_topics(FEATURES_TOPIC, timeout=10)
    partitions = metadata.topics[FEATURES_TOPIC].partitions
    start_ms = int(start.timestamp() * 1000)
    wanted = [TopicPartition(FEATURES_TOPIC, p, start_ms) for p in partitions]
    consumer.assign(consumer.offsets_for_times(wanted, timeout=10))
    return consumer


def test_live_features_match_the_reference() -> None:
    from confluent_kafka.schema_registry import SchemaRegistryClient
    from confluent_kafka.schema_registry.avro import AvroDeserializer
    from confluent_kafka.serialization import MessageField, SerializationContext

    from services.generators.transactions.sinks import KafkaSink

    run = uuid.uuid4().hex[:8]
    customers = build_population(30, seed=21, prefix=f"gate2-{run}-")
    victim = customers[-1]
    start = datetime.now(UTC) - timedelta(seconds=5)

    record = ListSink()
    kafka = KafkaSink(BOOTSTRAP, SCHEMA_REGISTRY)
    plan = LivePlan(
        rate_per_second=10,
        duration=timedelta(seconds=35),
        scenario="account-takeover",
        scenario_after=timedelta(seconds=5),
        time_scale=60,
    )
    play_live(customers, plan, TeeSink([kafka, record]), scenario_customer=victim)
    kafka.flush()

    expected = compute(record.events)
    sent = {e.transaction_id for e in record.events if isinstance(e, Transaction)}
    assert set(expected) == sent

    deserializer = AvroDeserializer(SchemaRegistryClient({"url": SCHEMA_REGISTRY}))
    context = SerializationContext(FEATURES_TOPIC, MessageField.VALUE)
    consumer = _consumer(start)

    # Keep traffic flowing for other customers, so the watermark passes our
    # last events. Sent from this thread, after the run, to stay in time order.
    filler = build_population(20, seed=22, prefix=f"gate2-filler-{run}-")
    rng = random.Random(5)
    rows: dict[str, dict[str, Any]] = {}
    deadline = time.monotonic() + WAIT_FOR_FEATURES.total_seconds()
    try:
        while not sent <= rows.keys() and time.monotonic() < deadline:
            kafka.send(normal_payment(rng.choice(filler), datetime.now(UTC), rng))
            message = consumer.poll(0.2)
            if message is None or message.error():
                continue
            value = deserializer(message.value(), context)
            if value and value["transaction_id"] in sent:
                rows[value["transaction_id"]] = value
    finally:
        consumer.close()
        kafka.close()

    missing = sent - rows.keys()
    if missing:
        times = {
            e.transaction_id: e.event_time for e in record.events if isinstance(e, Transaction)
        }
        last = max(times.values())
        lines = []
        for tid in sorted(missing, key=times.__getitem__):
            before = (last - times[tid]).total_seconds()
            lines.append(f"  {tid} at {times[tid].isoformat()} ({before:.1f}s before the last)")
        pytest.fail(
            f"{len(missing)} of {len(sent)} transactions have no features. Late events dropped "
            "by the watermark, or still behind it:\n" + "\n".join(lines)
        )

    mismatches = []
    for tid, want in expected.items():
        got = rows[tid]
        for name in want.__dataclass_fields__:
            if name == "transaction_id":
                continue
            w, g = getattr(want, name), got[name]
            same = math.isclose(w, g, rel_tol=1e-9) if isinstance(w, float) else w == g
            if not same:
                mismatches.append(f"{tid} {name}: live={g!r} reference={w!r}")
    assert not mismatches, "\n".join(mismatches[:20])

    takeover = [
        rows[e.transaction_id]
        for e in record.events
        if isinstance(e, Transaction) and e.customer_id == victim.customer_id
    ]
    assert len(takeover) == 6
    assert all(
        r["sim_swap_72h"] and r["is_new_beneficiary"] and r["is_new_device"] for r in takeover
    )
