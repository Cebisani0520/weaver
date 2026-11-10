"""Scoring cases shared by the model unit tests and Gate 3.

The plan's account-takeover journey (SIM swap, new device, new payees, PayShap
drain) played after three days of a small population's normal traffic, with the
reference features for every payment. A fraud model worth deploying scores
the drain payments high and the everyday payments low.
"""

from __future__ import annotations

import random
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from services.flink_sql.fraud_score.reference_features import compute
from services.generators.transactions.model import Event, Transaction
from services.generators.transactions.population import build_population
from services.generators.transactions.scenarios import account_takeover, at
from services.generators.transactions.traffic import history

TAKEOVER_SIGNALS = {"sim_swap_72h", "is_new_beneficiary", "is_new_device"}


@dataclass(frozen=True, slots=True)
class Cases:
    takeover: list[dict[str, Any]]  # feature records of the drain payments
    normal: list[dict[str, Any]]  # feature records of everyday payments


def build_cases(normal_sample: int = 40, seed: int = 5) -> Cases:
    end = datetime(2026, 10, 15, tzinfo=UTC)
    customers = build_population(30, seed=seed, prefix="gate3-")
    victim = customers[-1]
    events: list[Event] = list(history(customers, end - timedelta(days=3), end, seed=seed))
    # 01:52 SAST on the last day, as in the plan's journey.
    takeover = at(account_takeover(victim), end - timedelta(hours=24) + timedelta(minutes=-8))
    events.extend(takeover)
    features = compute(events)

    takeover_ids = {e.transaction_id for e in takeover if isinstance(e, Transaction)}
    takeover_rows = [asdict(features[i]) for i in sorted(takeover_ids)]
    normal_ids = sorted(i for i in features if i not in takeover_ids)
    picked = random.Random(seed).sample(normal_ids, min(normal_sample, len(normal_ids)))
    return Cases(takeover=takeover_rows, normal=[asdict(features[i]) for i in picked])


def median(values: list[float]) -> float:
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / 2


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int(fraction * len(ordered)))]
