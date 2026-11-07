"""Run services/flink_sql/fraud_score/features.sql on a local Flink and check every row.

The SQL file runs unchanged in streaming mode against tables shaped like the
ones CMF infers from Schema Registry (same columns, same `$rowtime` and default
watermark), fed with generated history plus the account-takeover scenario. Each
output row is compared with the reference implementation.

Needs PyFlink 2.3 (Python 3.12) and Java 17+. Run with `mise run test-flink`;
the normal suite skips it.
"""

from __future__ import annotations

import json
import math
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

pyflink_table = pytest.importorskip("pyflink.table")

from services.flink_sql.fraud_score.reference_features import compute  # noqa: E402
from services.generators.transactions.model import (  # noqa: E402
    Event,
    Transaction,
    to_json_record,
)
from services.generators.transactions.population import build_population  # noqa: E402
from services.generators.transactions.scenarios import account_takeover, at  # noqa: E402
from services.generators.transactions.traffic import history  # noqa: E402

pytestmark = pytest.mark.flink

REPO = Path(__file__).resolve().parents[2]
SCHEMAS = REPO / "infra/environments/local/schemas"
FEATURES_SQL = REPO / "services/flink_sql/fraud_score/features.sql"
ATO_START = datetime(2026, 11, 1, 23, 52, tzinfo=UTC)  # 01:52 SAST

AVRO_TO_FLINK = {
    "string": "STRING",
    "long": "BIGINT",
    "int": "INT",
    "double": "DOUBLE",
    "boolean": "BOOLEAN",
}


def flink_type(avro: Any, *, timestamps_as_epoch: bool) -> tuple[str, bool]:
    """(Flink type, nullable) for an Avro field type, as CMF infers it."""
    if isinstance(avro, list):
        (inner,) = [t for t in avro if t != "null"]
        return flink_type(inner, timestamps_as_epoch=timestamps_as_epoch)[0], True
    if isinstance(avro, dict) and avro.get("logicalType") == "timestamp-millis":
        return ("BIGINT" if timestamps_as_epoch else "TIMESTAMP_LTZ(3)"), False
    return AVRO_TO_FLINK[avro], False


def columns(topic: str, *, timestamps_as_epoch: bool) -> list[str]:
    """Columns as CMF infers them for a topic with only a value schema.

    A raw `key` BYTES column comes first, then every value field. CMF makes all
    of them nullable, whatever the Avro type says.
    """
    schema = json.loads((SCHEMAS / topic / "value.avsc").read_text())
    out = ["`key` BYTES"]
    for field in schema["fields"]:
        ftype, _ = flink_type(field["type"], timestamps_as_epoch=timestamps_as_epoch)
        out.append(f"`{field['name']}` {ftype}")
    return out


def source_ddl(topic: str, path: Path) -> str:
    """A table like CMF's inferred one, reading JSON lines instead of Kafka.

    The JSON carries event_time as epoch millis; `$rowtime` stands in for the
    Kafka record timestamp, which producers set to event_time.
    """
    cols = columns(topic, timestamps_as_epoch=True)
    return f"""
        CREATE TABLE `{topic}` (
          {", ".join(cols)},
          `$rowtime` AS TO_TIMESTAMP_LTZ(`event_time`, 3),
          WATERMARK FOR `$rowtime` AS `$rowtime`
        ) WITH ('connector' = 'filesystem', 'path' = '{path}', 'format' = 'json')
    """


def write_topic(path: Path, events: list[Event], topic: str) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for event in events:
            if event.topic == topic:
                record = to_json_record(event)
                record.pop("topic")
                handle.write(json.dumps(record) + "\n")


@pytest.fixture(scope="module")
def dataset() -> list[Event]:
    customers = build_population(25)
    baseline = list(history(customers, ATO_START - timedelta(days=4), ATO_START))
    scenario = at(account_takeover(customers[-1]), ATO_START)
    after = list(
        history(customers[:-1], ATO_START + timedelta(minutes=18), ATO_START + timedelta(hours=3))
    )
    return baseline + scenario + after


@pytest.fixture(scope="module")
def table_env(dataset: list[Event], tmp_path_factory: pytest.TempPathFactory) -> Any:
    tmp = tmp_path_factory.mktemp("flink")
    env = pyflink_table.TableEnvironment.create(
        pyflink_table.EnvironmentSettings.in_streaming_mode()
    )
    config = env.get_config()
    config.set("parallelism.default", "1")
    config.set("table.local-time-zone", "UTC")  # the statement pins the same
    for topic in ("transactions", "account-events"):
        path = tmp / f"{topic}.jsonl"
        write_topic(path, dataset, topic)
        env.execute_sql(source_ddl(topic, path))
    sink_cols = columns("txn-features", timestamps_as_epoch=False)
    env.execute_sql(
        f"CREATE TABLE `txn-features` ({', '.join(sink_cols)}) WITH ('connector' = 'blackhole')"
    )
    return env


def select_part(sql: str) -> str:
    _head, _, body = sql.partition("INSERT INTO `txn-features`")
    assert body, "features.sql must insert into `txn-features`"
    return body.strip().rstrip(";")


def test_insert_matches_the_txn_features_schema(table_env: Any) -> None:
    """Planning the full INSERT fails if a column, type or nullability is off."""
    plan = table_env.explain_sql(FEATURES_SQL.read_text().strip().rstrip(";"))
    assert "txn-features" in plan


@pytest.fixture(scope="module")
def flink_rows(table_env: Any) -> dict[str, dict[str, Any]]:
    # PyFlink cannot hand TIMESTAMP_LTZ values to Python on recent JVMs, so the
    # query is wrapped to return event_time as text; everything else is as-is.
    wanted = ", ".join(f"`{name}`" for name in ("transaction_id", *FIELDS))
    query = (
        f"SELECT {wanted}, CAST(`event_time` AS STRING) AS `event_time` "
        f"FROM ({select_part(FEATURES_SQL.read_text())})"
    )
    result = table_env.execute_sql(query)
    names = result.get_table_schema().get_field_names()
    rows: dict[str, dict[str, Any]] = {}
    with result.collect() as results:
        for row in results:
            record = dict(zip(names, row, strict=True))
            assert record["transaction_id"] not in rows, "one row per transaction"
            rows[record["transaction_id"]] = record
    return rows


def test_one_row_per_transaction(dataset: list[Event], flink_rows: dict[str, Any]) -> None:
    expected = {e.transaction_id for e in dataset if isinstance(e, Transaction)}
    assert set(flink_rows) == expected


FIELDS = (
    "customer_id",
    "amount_cents",
    "channel",
    "province",
    "txn_count_1h",
    "txn_count_24h",
    "distinct_provinces_24h",
    "avg_amount_30d_cents",
    "amount_to_avg_30d",
    "is_new_beneficiary",
    "sim_swap_72h",
    "is_new_device",
    "is_night_sast",
    "feature_version",
)


def test_every_feature_matches_the_reference(
    dataset: list[Event], flink_rows: dict[str, dict[str, Any]]
) -> None:
    expected = compute(dataset)
    mismatches = []
    for tid, want in expected.items():
        got = flink_rows[tid]
        for name in FIELDS:
            w, g = getattr(want, name), got[name]
            same = math.isclose(w, g, rel_tol=1e-9) if isinstance(w, float) else w == g
            if not same:
                mismatches.append(f"{tid} {name}: flink={g!r} reference={w!r}")
    assert not mismatches, "\n".join(mismatches[:20])


def test_takeover_rows_flag_every_signal(
    dataset: list[Event], flink_rows: dict[str, dict[str, Any]]
) -> None:
    victim = build_population(25)[-1].customer_id
    takeover = sorted(
        (r for r in flink_rows.values() if r["customer_id"] == victim and r["sim_swap_72h"]),
        key=lambda r: r["event_time"],
    )
    assert len(takeover) == 6
    assert all(
        r["is_new_beneficiary"] and r["is_new_device"] and r["is_night_sast"] for r in takeover
    )
    assert [r["txn_count_1h"] for r in takeover] == [1, 2, 3, 4, 5, 6]
