"""Plays history, live traffic and scenarios into a sink, in event-time order.

The default CMF watermark has no lateness allowance, so every event on a
partition must be newer than the last. The player guarantees that by emitting
one merged, time-ordered stream: history first (back-dated), then live events
stamped with the moment they are sent.
"""

from __future__ import annotations

import random
import time
from collections.abc import Callable, Iterator
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta

from services.generators.transactions.model import Event
from services.generators.transactions.population import Customer
from services.generators.transactions.scenarios import SCENARIOS, ScheduledEvent
from services.generators.transactions.sinks import Sink
from services.generators.transactions.traffic import history, normal_payment


@dataclass(frozen=True, slots=True)
class LivePlan:
    rate_per_second: float
    duration: timedelta
    scenario: str | None = None
    scenario_after: timedelta = timedelta(seconds=10)
    time_scale: float = 60.0
    seed: int = 13


def play_history(customers: list[Customer], hours: float, sink: Sink, end: datetime) -> int:
    """Back-dated normal traffic for every customer, ending at `end`."""
    count = 0
    for event in history(customers, end - timedelta(hours=hours), end):
        sink.send(event)
        count += 1
    return count


def live_schedule(
    customers: list[Customer], plan: LivePlan, scenario_customer: Customer | None
) -> Iterator[tuple[timedelta, Event]]:
    """(offset from start, event) pairs in offset order; event_time is set on send."""
    rng = random.Random(plan.seed)
    items: list[tuple[timedelta, Event]] = []

    offset = timedelta()
    gap_mean = 1.0 / plan.rate_per_second
    pool = [c for c in customers if c is not scenario_customer]
    while offset < plan.duration:
        offset += timedelta(seconds=rng.expovariate(1.0 / gap_mean))
        customer = rng.choice(pool)
        items.append((offset, normal_payment(customer, datetime.now(UTC), rng)))

    if plan.scenario and scenario_customer is not None:
        steps: list[ScheduledEvent] = SCENARIOS[plan.scenario](scenario_customer)
        for step in steps:
            items.append((plan.scenario_after + step.offset / plan.time_scale, step.event))

    items.sort(key=lambda pair: pair[0])
    yield from items


def play_live(
    customers: list[Customer],
    plan: LivePlan,
    sink: Sink,
    scenario_customer: Customer | None = None,
    clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    sleep: Callable[[float], None] = time.sleep,
) -> int:
    """Send live traffic in real time, stamping each event when it is sent."""
    start = clock()
    last = start
    count = 0
    for offset, event in live_schedule(customers, plan, scenario_customer):
        due = start + offset
        wait = (due - clock()).total_seconds()
        if wait > 0:
            sleep(wait)
        # Never stamp backwards, even if the clock jitters.
        stamp = max(clock(), last + timedelta(milliseconds=1))
        last = stamp
        sink.send(replace(event, event_time=stamp))
        count += 1
    return count
