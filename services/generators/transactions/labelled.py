"""Labelled scenarios for training data: fraud patterns and the benign look-alikes.

Every fraud scenario has a benign twin that shares its most obvious signal, so
the model has to combine features rather than learn one rule:

  fraud                                 benign look-alike
  account takeover (SIM swap or not)    phone upgrade: SIM swap, new device, sometimes a new payee
  authorised push payment scam          paying a new payee: new beneficiary, larger amount
  card testing                          a burst of small everyday purchases
  one card-not-present purchase         (none needed: it already looks normal)
                                        travel: payments from another province

Builders are randomised by the rng they are given, and return offsets from
midnight SAST of the day the dataset places them on; each builder chooses its
own time of day. `tag` keeps IDs unique when a customer gets several scenarios.
"""

from __future__ import annotations

import random
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from services.generators.transactions.model import (
    PROVINCES,
    AccountEvent,
    AccountEventType,
    Channel,
    Transaction,
    hashed_id,
)
from services.generators.transactions.population import MERCHANT_CATEGORIES, Customer
from services.generators.transactions.scenarios import ScheduledEvent

_UNSCHEDULED = datetime(1970, 1, 1, tzinfo=UTC)

Builder = Callable[[Customer, random.Random, str], list[ScheduledEvent]]


@dataclass(frozen=True, slots=True)
class LabelledScenario:
    name: str
    fraud: bool
    build: Builder


class _Script:
    """Collects one scenario's events with unique, reproducible IDs."""

    def __init__(self, scenario: str, customer: Customer, tag: str) -> None:
        self.prefix = f"{scenario}-{customer.customer_id}-{tag}"
        self.customer = customer
        self.events: list[ScheduledEvent] = []

    def id(self, kind: str, part: str) -> str:
        return hashed_id(kind, f"{self.prefix}-{part}")

    def account(
        self,
        at: timedelta,
        event_type: AccountEventType,
        *,
        device: str | None = None,
        beneficiary: str | None = None,
    ) -> None:
        event = AccountEvent(
            event_id=self.id("evt", f"{len(self.events)}"),
            event_time=_UNSCHEDULED,
            customer_id=self.customer.customer_id,
            event_type=event_type,
            device_id=device,
            beneficiary_id=beneficiary,
        )
        self.events.append(ScheduledEvent(at, event))

    def pay(
        self,
        at: timedelta,
        channel: Channel,
        amount_cents: int,
        *,
        device: str | None,
        province: str | None = None,
        beneficiary: str | None = None,
        merchant: str | None = None,
        merchant_category: str | None = None,
    ) -> None:
        event = Transaction(
            transaction_id=self.id("txn", f"{len(self.events)}"),
            event_time=_UNSCHEDULED,
            customer_id=self.customer.customer_id,
            account_id=self.customer.account_id,
            device_id=device,
            channel=channel,
            amount_cents=max(100, amount_cents),
            province=province or self.customer.home_province,
            merchant_category=merchant_category,
            merchant_id=merchant,
            beneficiary_id=beneficiary,
        )
        self.events.append(ScheduledEvent(at, event))

    def done(self) -> list[ScheduledEvent]:
        return sorted(self.events, key=lambda item: item.offset)


def _time_of_day(rng: random.Random, night_probability: float) -> timedelta:
    """A start time after midnight SAST: 00:00-05:00 with the given probability, else daytime."""
    if rng.random() < night_probability:
        return timedelta(minutes=rng.uniform(0, 4.5 * 60))
    return timedelta(minutes=rng.uniform(7 * 60, 21 * 60))


def _other_province(customer: Customer, rng: random.Random) -> str:
    return rng.choice([p for p in PROVINCES if p != customer.home_province])


# --- fraud ------------------------------------------------------------------


def account_takeover(customer: Customer, rng: random.Random, tag: str) -> list[ScheduledEvent]:
    """Takeover, randomised: SIM swap (usually) or phished credentials, new device,
    new mule payees, then a fast drain by PayShap or EFT."""
    s = _Script("ato", customer, tag)
    t = _time_of_day(rng, night_probability=0.6)
    device = s.id("dev", "fraudster")
    if rng.random() < 0.8:
        s.account(t, AccountEventType.SIM_SWAP)
        t += timedelta(minutes=rng.uniform(2, 30))
    if rng.random() < 0.4:
        s.account(t, AccountEventType.PASSWORD_RESET)
        t += timedelta(minutes=rng.uniform(1, 5))
    s.account(t, AccountEventType.NEW_DEVICE_LOGIN, device=device)
    province = customer.home_province if rng.random() < 0.5 else _other_province(customer, rng)
    channel = Channel.PAYSHAP if rng.random() < 0.8 else Channel.EFT

    mules = [s.id("bene", f"mule-{m}") for m in range(rng.randint(1, 3))]
    for mule in mules:
        t += timedelta(minutes=rng.uniform(0.5, 6))
        s.account(t, AccountEventType.BENEFICIARY_ADDED, beneficiary=mule)
    for _ in range(rng.randint(2, 8)):
        t += timedelta(minutes=rng.uniform(0.5, 6))
        s.pay(
            t,
            channel,
            rng.randint(1_500, 9_900) * 100,
            device=device,
            province=province,
            beneficiary=rng.choice(mules),
        )
    return s.done()


def payment_scam(customer: Customer, rng: random.Random, tag: str) -> list[ScheduledEvent]:
    """Authorised push payment scam: the customer, on their own device, is talked
    into adding the scammer and sending large amounts. No SIM swap, no new device."""
    s = _Script("app-scam", customer, tag)
    t = _time_of_day(rng, night_probability=0.1)
    device = rng.choice(customer.devices)
    scammer = s.id("bene", "scammer")
    s.account(t, AccountEventType.BENEFICIARY_ADDED, beneficiary=scammer)
    channel = rng.choice((Channel.PAYSHAP, Channel.EFT))
    for _ in range(rng.randint(1, 3)):
        t += timedelta(minutes=rng.uniform(1, 40))
        multiple = rng.uniform(4, 25)
        s.pay(
            t,
            channel,
            int(customer.typical_amount_cents * multiple),
            device=device,
            beneficiary=scammer,
        )
    return s.done()


def card_testing(customer: Customer, rng: random.Random, tag: str) -> list[ScheduledEvent]:
    """Stolen card details: many tiny online payments at different merchants within
    minutes, then large purchases. Card not present, so no customer device."""
    s = _Script("card-testing", customer, tag)
    t = _time_of_day(rng, night_probability=0.5)
    province = _other_province(customer, rng) if rng.random() < 0.6 else customer.home_province
    for probe in range(rng.randint(4, 12)):
        t += timedelta(seconds=rng.uniform(10, 90))
        s.pay(
            t,
            Channel.CARD_ONLINE,
            rng.randint(200, 3_000),
            device=None,
            province=province,
            merchant=s.id("merch", f"probe-{probe}"),
            merchant_category=rng.choice(("5999", "5815", "5816")),
        )
    for buy in range(rng.randint(1, 2)):
        t += timedelta(minutes=rng.uniform(1, 20))
        s.pay(
            t,
            Channel.CARD_ONLINE,
            rng.randint(3_000, 15_000) * 100,
            device=None,
            province=province,
            merchant=s.id("merch", f"cashout-{buy}"),
            merchant_category=rng.choice(("5732", "5944", "5311")),
        )
    return s.done()


def card_not_present(customer: Customer, rng: random.Random, tag: str) -> list[ScheduledEvent]:
    """A single fraudulent online purchase that looks like the customer's own:
    home province, daytime, a plausible amount. Mostly undetectable from these
    features, as in real data; it keeps recall honest."""
    s = _Script("card-not-present", customer, tag)
    t = _time_of_day(rng, night_probability=0.2)
    s.pay(
        t,
        Channel.CARD_ONLINE,
        int(customer.typical_amount_cents * rng.uniform(0.8, 4)),
        device=None,
        merchant=s.id("merch", "cnp"),
        merchant_category=rng.choice(MERCHANT_CATEGORIES),
    )
    return s.done()


# --- benign look-alikes -----------------------------------------------------


def phone_upgrade(customer: Customer, rng: random.Random, tag: str) -> list[ScheduledEvent]:
    """A real SIM swap: new phone, new device login, then ordinary spend from it."""
    s = _Script("phone-upgrade", customer, tag)
    t = _time_of_day(rng, night_probability=0.05)
    device = s.id("dev", "new-phone")
    s.account(t, AccountEventType.SIM_SWAP)
    t += timedelta(minutes=rng.uniform(10, 180))
    s.account(t, AccountEventType.NEW_DEVICE_LOGIN, device=device)
    for _ in range(rng.randint(2, 6)):
        t += timedelta(hours=rng.uniform(0.5, 10))
        channel = rng.choice((Channel.CARD_ONLINE, Channel.PAYSHAP, Channel.WALLET))
        transfer = channel is Channel.PAYSHAP
        s.pay(
            t,
            channel,
            int(customer.typical_amount_cents * rng.lognormvariate(0, 0.5)),
            device=device,
            beneficiary=rng.choice(customer.beneficiaries) if transfer else None,
            merchant=None if transfer else rng.choice(customer.merchants),
            merchant_category=None if transfer else rng.choice(MERCHANT_CATEGORIES),
        )
    if rng.random() < 0.3:
        # New phone, then paying someone new from it: every takeover signal, legitimately.
        payee = s.id("bene", "payee")
        t += timedelta(hours=rng.uniform(0.5, 6))
        s.account(t, AccountEventType.BENEFICIARY_ADDED, beneficiary=payee)
        t += timedelta(minutes=rng.uniform(1, 30))
        s.pay(
            t,
            Channel.PAYSHAP,
            int(customer.typical_amount_cents * rng.uniform(1, 10)),
            device=device,
            beneficiary=payee,
        )
    return s.done()


def new_payee(customer: Customer, rng: random.Random, tag: str) -> list[ScheduledEvent]:
    """Paying someone new, legitimately: a builder, a landlord, a school."""
    s = _Script("new-payee", customer, tag)
    t = _time_of_day(rng, night_probability=0.03)
    payee = s.id("bene", "payee")
    s.account(t, AccountEventType.BENEFICIARY_ADDED, beneficiary=payee)
    t += timedelta(minutes=rng.uniform(1, 90))
    s.pay(
        t,
        rng.choice((Channel.EFT, Channel.PAYSHAP)),
        int(customer.typical_amount_cents * rng.uniform(1, 12)),
        device=rng.choice(customer.devices),
        beneficiary=payee,
    )
    return s.done()


def small_purchases(customer: Customer, rng: random.Random, tag: str) -> list[ScheduledEvent]:
    """A burst of small, real purchases: taxi fares, vending, a market stall."""
    s = _Script("small-purchases", customer, tag)
    t = _time_of_day(rng, night_probability=0.15)
    for _ in range(rng.randint(3, 8)):
        t += timedelta(minutes=rng.uniform(0.5, 12))
        channel = rng.choice((Channel.CARD_PRESENT, Channel.WALLET, Channel.CARD_ONLINE))
        s.pay(
            t,
            channel,
            rng.randint(500, 6_000),
            device=None if channel is Channel.CARD_PRESENT else rng.choice(customer.devices),
            merchant=s.id("merch", f"small-{len(s.events)}"),
            merchant_category=rng.choice(("4121", "5814", "5499", "5815", "4814")),
        )
    return s.done()


def travel(customer: Customer, rng: random.Random, tag: str) -> list[ScheduledEvent]:
    """A trip: ordinary spend from another province over a day or two."""
    s = _Script("travel", customer, tag)
    t = _time_of_day(rng, night_probability=0.0)
    province = _other_province(customer, rng)
    for _ in range(rng.randint(3, 6)):
        t += timedelta(hours=rng.uniform(0.5, 8))
        channel = rng.choice((Channel.CARD_PRESENT, Channel.CARD_ONLINE))
        s.pay(
            t,
            channel,
            int(customer.typical_amount_cents * rng.lognormvariate(0.3, 0.5)),
            device=None if channel is Channel.CARD_PRESENT else rng.choice(customer.devices),
            province=province,
            merchant=s.id("merch", f"trip-{len(s.events)}"),
            merchant_category=rng.choice(("7011", "5812", "5541")),
        )
    return s.done()


FRAUD_SCENARIOS = (
    LabelledScenario("account-takeover", fraud=True, build=account_takeover),
    LabelledScenario("payment-scam", fraud=True, build=payment_scam),
    LabelledScenario("card-testing", fraud=True, build=card_testing),
    LabelledScenario("card-not-present", fraud=True, build=card_not_present),
)

BENIGN_SCENARIOS = (
    LabelledScenario("phone-upgrade", fraud=False, build=phone_upgrade),
    LabelledScenario("new-payee", fraud=False, build=new_payee),
    LabelledScenario("small-purchases", fraud=False, build=small_purchases),
    LabelledScenario("travel", fraud=False, build=travel),
)
