"""Labelled training data for the fraud score model.

Synthetic, reproducible from a seed: a population's normal traffic over N days,
with fraud scenarios and benign look-alikes placed on random customers and days.
Features come from the reference implementation, the same specification the
Flink statement is tested against, so training and serving see identical
definitions (no training/serving skew by construction).

Rows are split by time, not at random: the model is validated on payments that
happen after the ones it learnt from, as it will be in production.

    python -m services.models.fraud_score.dataset --out data/fraud-score
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import random
import sys
from collections import Counter
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from services.flink_sql.fraud_score.reference_features import FEATURE_VERSION, compute
from services.generators.transactions.labelled import (
    BENIGN_SCENARIOS,
    FRAUD_SCENARIOS,
    LabelledScenario,
)
from services.generators.transactions.model import Event, Transaction
from services.generators.transactions.population import build_population
from services.generators.transactions.scenarios import at
from services.generators.transactions.traffic import history
from services.models.fraud_score.fraud_score_model.spec import FeatureSpec, load

SPLITS = ("train", "validation", "test")
SAST = timedelta(hours=2)


@dataclass(frozen=True, slots=True)
class DatasetConfig:
    customers: int = 300
    days: int = 35
    fraud_scenarios: int = 160
    benign_scenarios: int = 320
    seed: int = 21
    # Fixed, so the same config always builds the same rows.
    end: datetime = datetime(2026, 10, 1, tzinfo=UTC)
    split: tuple[float, float, float] = (0.70, 0.15, 0.15)

    @property
    def dataset_id(self) -> str:
        return (
            f"{FEATURE_VERSION}-s{self.seed}-c{self.customers}-d{self.days}"
            f"-f{self.fraud_scenarios}-b{self.benign_scenarios}"
        )


@dataclass(frozen=True, slots=True)
class Row:
    event_time: datetime
    transaction_id: str
    label: int
    scenario: str
    features: dict[str, Any]


@dataclass(slots=True)
class Dataset:
    config: DatasetConfig
    rows: list[Row] = field(default_factory=list)

    def split(self) -> dict[str, list[Row]]:
        """Contiguous time ranges: the first 70% of the period trains, and so on."""
        start = self.config.end - timedelta(days=self.config.days)
        span = self.config.end - start
        cut_1 = start + span * self.config.split[0]
        cut_2 = cut_1 + span * self.config.split[1]
        parts: dict[str, list[Row]] = {name: [] for name in SPLITS}
        for row in self.rows:
            if row.event_time < cut_1:
                parts["train"].append(row)
            elif row.event_time < cut_2:
                parts["validation"].append(row)
            else:
                parts["test"].append(row)
        return parts


def _place(
    scenario: LabelledScenario,
    config: DatasetConfig,
    rng: random.Random,
    customers: list[Any],
    index: int,
) -> list[Event]:
    customer = rng.choice(customers)
    start = config.end - timedelta(days=config.days)
    # Midnight SAST of a random day, leaving two days at each end for the
    # scenario to unfold and for windows to fill.
    day = rng.randint(2, config.days - 2)
    midnight_sast = datetime(start.year, start.month, start.day, tzinfo=UTC) + timedelta(days=day)
    return at(scenario.build(customer, rng, f"{index}"), midnight_sast - SAST)


def build(config: DatasetConfig) -> Dataset:
    rng = random.Random(config.seed)
    customers = build_population(config.customers, seed=config.seed, prefix=f"ds{config.seed}-")
    start = config.end - timedelta(days=config.days)
    events: list[Event] = list(history(customers, start, config.end, seed=config.seed + 1))

    scenario_of: dict[str, str] = {}
    fraud_ids: set[str] = set()
    plan = [rng.choice(FRAUD_SCENARIOS) for _ in range(config.fraud_scenarios)] + [
        rng.choice(BENIGN_SCENARIOS) for _ in range(config.benign_scenarios)
    ]
    for index, scenario in enumerate(plan):
        for event in _place(scenario, config, rng, customers, index):
            events.append(event)
            if isinstance(event, Transaction):
                scenario_of[event.transaction_id] = scenario.name
                if scenario.fraud:
                    fraud_ids.add(event.transaction_id)

    by_id = {e.transaction_id: e for e in events if isinstance(e, Transaction)}
    dataset = Dataset(config)
    for transaction_id, features in compute(events).items():
        txn = by_id[transaction_id]
        if not start <= txn.event_time < config.end:
            continue
        dataset.rows.append(
            Row(
                event_time=txn.event_time,
                transaction_id=transaction_id,
                label=int(transaction_id in fraud_ids),
                scenario=scenario_of.get(transaction_id, "normal"),
                features=asdict(features),
            )
        )
    dataset.rows.sort(key=lambda row: (row.event_time, row.transaction_id))
    return dataset


def _cell(value: float) -> str:
    return "" if math.isnan(value) else repr(value)


def write(dataset: Dataset, out_dir: Path, spec: FeatureSpec | None = None) -> dict[str, Any]:
    """Write <out>/<dataset_id>/{train,validation,test}/<split>.csv and manifest.json."""
    spec = spec or load()
    root = out_dir / dataset.config.dataset_id
    manifest: dict[str, Any] = {
        "dataset_id": dataset.config.dataset_id,
        "model": spec.model,
        "feature_version": spec.feature_version,
        "columns": ["label", *spec.columns],
        "config": {
            **asdict(dataset.config),
            "end": dataset.config.end.isoformat(),
        },
        "splits": {},
    }
    for name, rows in dataset.split().items():
        path = root / name / f"{name}.csv"
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(manifest["columns"])
            for row in rows:
                writer.writerow([row.label, *(_cell(v) for v in spec.vector(row.features))])
        manifest["splits"][name] = {
            "file": str(path.relative_to(root)),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "rows": len(rows),
            "positives": sum(row.label for row in rows),
            "from": rows[0].event_time.isoformat() if rows else None,
            "to": rows[-1].event_time.isoformat() if rows else None,
            "scenarios": dict(sorted(Counter(row.scenario for row in rows).items())),
        }
    (root / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def main(argv: list[str]) -> int:
    defaults = DatasetConfig()
    parser = argparse.ArgumentParser(description="Build labelled fraud score training data.")
    parser.add_argument("--out", type=Path, default=Path("data/fraud-score"))
    parser.add_argument("--customers", type=int, default=defaults.customers)
    parser.add_argument("--days", type=int, default=defaults.days)
    parser.add_argument("--fraud", type=int, default=defaults.fraud_scenarios)
    parser.add_argument("--benign", type=int, default=defaults.benign_scenarios)
    parser.add_argument("--seed", type=int, default=defaults.seed)
    args = parser.parse_args(argv)
    config = DatasetConfig(
        customers=args.customers,
        days=args.days,
        fraud_scenarios=args.fraud,
        benign_scenarios=args.benign,
        seed=args.seed,
    )
    manifest = write(build(config), args.out)
    print(json.dumps(manifest["splits"], indent=2))
    print(args.out / config.dataset_id)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
