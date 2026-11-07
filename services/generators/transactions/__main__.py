"""Command line for the transaction generator.

    python -m services.generators.transactions --history-hours 24 --live 120 --rate 20 \
        --scenario account-takeover --output kafka

Run `--help` for every option. `--output jsonl` prints events instead of sending them.
"""

from __future__ import annotations

import argparse
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

from services.generators.transactions.player import LivePlan, play_history, play_live
from services.generators.transactions.population import build_population
from services.generators.transactions.scenarios import SCENARIOS
from services.generators.transactions.sinks import JsonLinesSink, KafkaSink, Sink, TeeSink


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="python -m services.generators.transactions",
        description="Synthetic ZAR payments and account events for Weaver.",
    )
    parser.add_argument("--customers", type=int, default=200, help="population size")
    parser.add_argument("--seed", type=int, default=7, help="population seed")
    parser.add_argument(
        "--id-prefix",
        default="",
        help="namespace for customer IDs, so a run does not reuse earlier runs' customers",
    )
    parser.add_argument(
        "--history-hours",
        type=float,
        default=0,
        help=(
            "back-dated normal traffic to send first, for 30-day baselines. Only on fresh "
            "topics: back-dated events behind newer ones on a partition are late and dropped"
        ),
    )
    parser.add_argument(
        "--live", type=float, default=0, help="seconds of real-time traffic after the history"
    )
    parser.add_argument("--rate", type=float, default=10, help="live payments per second")
    parser.add_argument("--scenario", choices=sorted(SCENARIOS), help="inject a fraud scenario")
    parser.add_argument(
        "--scenario-after", type=float, default=10, help="seconds into the live run"
    )
    parser.add_argument(
        "--time-scale",
        type=float,
        default=60,
        help="scenario speed-up: 60 plays the 17-minute takeover in 17 seconds",
    )
    parser.add_argument("--output", choices=("kafka", "jsonl"), default="jsonl")
    parser.add_argument("--record", type=Path, help="also write every event sent to this JSONL")
    parser.add_argument("--bootstrap", default="localhost:9092")
    parser.add_argument("--schema-registry", default="http://localhost:8081")
    return parser.parse_args(argv)


def build_sink(args: argparse.Namespace) -> Sink:
    primary: Sink = (
        KafkaSink(args.bootstrap, args.schema_registry)
        if args.output == "kafka"
        else JsonLinesSink(sys.stdout)
    )
    if args.record:
        return TeeSink([primary, JsonLinesSink(path=args.record)])
    return primary


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    if args.scenario and args.live <= args.scenario_after:
        print("--live must run past --scenario-after for the scenario to play", file=sys.stderr)
        return 2

    customers = build_population(args.customers, seed=args.seed, prefix=args.id_prefix)
    # The last customer plays the victim, so the scenario never collides with
    # live traffic for the same customer.
    victim = customers[-1] if args.scenario else None
    sink = build_sink(args)
    sent = 0
    try:
        if args.history_hours > 0:
            sent += play_history(customers, args.history_hours, sink, end=datetime.now(UTC))
        if args.live > 0:
            plan = LivePlan(
                rate_per_second=args.rate,
                duration=timedelta(seconds=args.live),
                scenario=args.scenario,
                scenario_after=timedelta(seconds=args.scenario_after),
                time_scale=args.time_scale,
            )
            sent += play_live(customers, plan, sink, scenario_customer=victim)
    finally:
        sink.close()

    print(f"sent {sent} events", file=sys.stderr)
    if victim is not None:
        print(f"scenario victim customer_id={victim.customer_id}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
