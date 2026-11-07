"""Where generated events go: JSON lines (tests, dry runs) or Kafka with Avro."""

from __future__ import annotations

import json
import sys
from collections.abc import Iterable
from pathlib import Path
from typing import Any, Protocol, TextIO

from services.generators.transactions.model import Event, epoch_ms, to_json_record


class Sink(Protocol):
    def send(self, event: Event) -> None: ...

    def close(self) -> None: ...


class JsonLinesSink:
    """One JSON object per line; event_time as epoch milliseconds."""

    def __init__(self, stream: TextIO | None = None, path: Path | None = None) -> None:
        self._owned = path is not None
        self._stream: TextIO = path.open("w", encoding="utf-8") if path else (stream or sys.stdout)

    def send(self, event: Event) -> None:
        self._stream.write(json.dumps(to_json_record(event), sort_keys=True) + "\n")

    def close(self) -> None:
        if self._owned:
            self._stream.close()
        else:
            self._stream.flush()


class ListSink:
    """Keeps events in memory, for tests."""

    def __init__(self) -> None:
        self.events: list[Event] = []

    def send(self, event: Event) -> None:
        self.events.append(event)

    def close(self) -> None:
        return None


class KafkaSink:
    """Avro values via Schema Registry; key = customer ID bytes; timestamp = event_time.

    Schemas are never registered from here: Terraform owns them, and the
    serializer uses the latest registered version of each subject.
    """

    def __init__(self, bootstrap_servers: str, schema_registry_url: str) -> None:
        # Imported here so tests and dry runs do not need confluent-kafka.
        from confluent_kafka import Producer
        from confluent_kafka.schema_registry import SchemaRegistryClient
        from confluent_kafka.schema_registry.avro import AvroSerializer
        from confluent_kafka.serialization import MessageField, SerializationContext

        self._context = SerializationContext
        self._value_field = MessageField.VALUE
        registry = SchemaRegistryClient({"url": schema_registry_url})
        config = {"auto.register.schemas": False, "use.latest.version": True}
        self._serializers: dict[str, Any] = {
            topic: AvroSerializer(registry, None, conf=config)
            for topic in ("transactions", "account-events")
        }
        self._producer = Producer(
            {
                "bootstrap.servers": bootstrap_servers,
                "enable.idempotence": True,
                "linger.ms": 5,
            }
        )
        self.sent = 0

    def send(self, event: Event) -> None:
        value = self._serializers[event.topic](
            event.to_record(), self._context(event.topic, self._value_field)
        )
        self._producer.produce(
            event.topic,
            key=event.key.encode(),
            value=value,
            timestamp=epoch_ms(event.event_time),
            on_delivery=_raise_on_error,
        )
        self._producer.poll(0)
        self.sent += 1

    def flush(self, timeout: float = 30) -> None:
        remaining = self._producer.flush(timeout)
        if remaining:
            raise RuntimeError(f"{remaining} messages were not delivered")

    def close(self) -> None:
        self.flush()


def _raise_on_error(error: Any, _message: Any) -> None:
    if error is not None:
        raise RuntimeError(f"delivery failed: {error}")


class TeeSink:
    """Sends every event to several sinks (for example Kafka and a JSONL record)."""

    def __init__(self, sinks: Iterable[Sink]) -> None:
        self._sinks = list(sinks)

    def send(self, event: Event) -> None:
        for sink in self._sinks:
            sink.send(event)

    def close(self) -> None:
        for sink in self._sinks:
            sink.close()
