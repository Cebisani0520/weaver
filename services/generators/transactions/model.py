"""Event types, matching the Avro value schemas in infra/environments/*/schemas."""

from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any


class Channel(StrEnum):
    CARD_PRESENT = "CARD_PRESENT"
    CARD_ONLINE = "CARD_ONLINE"
    PAYSHAP = "PAYSHAP"
    EFT = "EFT"
    WALLET = "WALLET"


class AccountEventType(StrEnum):
    SIM_SWAP = "SIM_SWAP"
    NEW_DEVICE_LOGIN = "NEW_DEVICE_LOGIN"
    BENEFICIARY_ADDED = "BENEFICIARY_ADDED"
    PASSWORD_RESET = "PASSWORD_RESET"  # noqa: S105  # nosec B105 - an event type, not a secret


PROVINCES = ("GP", "WC", "KZN", "EC", "FS", "MP", "LP", "NW", "NC")

TRANSACTIONS_TOPIC = "transactions"
ACCOUNT_EVENTS_TOPIC = "account-events"


def hashed_id(kind: str, value: str) -> str:
    """Stable, non-reversible synthetic ID, e.g. hashed_id("cust", "42")."""
    digest = hashlib.sha256(f"weaver:{kind}:{value}".encode()).hexdigest()
    return f"{kind}_{digest[:16]}"


def epoch_ms(moment: datetime) -> int:
    if moment.tzinfo is None:
        raise ValueError("event times must be timezone-aware")
    return int(moment.astimezone(UTC).timestamp() * 1000)


@dataclass(frozen=True, slots=True)
class Transaction:
    transaction_id: str
    event_time: datetime
    customer_id: str
    account_id: str
    device_id: str | None
    channel: Channel
    amount_cents: int
    province: str
    merchant_category: str | None = None
    merchant_id: str | None = None
    beneficiary_id: str | None = None
    currency: str = "ZAR"

    topic = TRANSACTIONS_TOPIC

    @property
    def key(self) -> str:
        return self.customer_id

    def to_record(self) -> dict[str, Any]:
        """Avro-ready dict: event_time stays a datetime (timestamp-millis)."""
        record = asdict(self)
        record["channel"] = str(self.channel)
        return record


@dataclass(frozen=True, slots=True)
class AccountEvent:
    event_id: str
    event_time: datetime
    customer_id: str
    event_type: AccountEventType
    device_id: str | None = None
    beneficiary_id: str | None = None

    topic = ACCOUNT_EVENTS_TOPIC

    @property
    def key(self) -> str:
        return self.customer_id

    def to_record(self) -> dict[str, Any]:
        record = asdict(self)
        record["event_type"] = str(self.event_type)
        return record


Event = Transaction | AccountEvent


def to_json_record(event: Event) -> dict[str, Any]:
    """JSON-friendly dict: event_time as epoch milliseconds, plus the topic."""
    record = event.to_record()
    record["event_time"] = epoch_ms(event.event_time)
    record["topic"] = event.topic
    return record
