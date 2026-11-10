"""Feature spec: the named inputs of the model and how they become a vector.

The spec ships inside the container and inside every model artifact, so the
endpoint always vectorises with the spec the model was trained on.

Runs on Python 3.12 in the container: no 3.13-only syntax or stdlib.
"""

from __future__ import annotations

import json
import math
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import numpy.typing as npt

SPEC_FILE = Path(__file__).with_name("feature_spec.json")


@dataclass(frozen=True, slots=True)
class Feature:
    name: str
    kind: str  # numeric, boolean or categorical
    values: tuple[str, ...] = ()

    @property
    def columns(self) -> list[str]:
        if self.kind == "categorical":
            return [f"{self.name}={value}" for value in self.values]
        return [self.name]


@dataclass(frozen=True, slots=True)
class FeatureSpec:
    model: str
    feature_version: str
    features: tuple[Feature, ...]

    @property
    def names(self) -> list[str]:
        """Input field names, in spec order."""
        return [f.name for f in self.features]

    @property
    def columns(self) -> list[str]:
        """Vector column names: one per numeric or boolean, one per category value."""
        return [column for f in self.features for column in f.columns]

    @property
    def column_sources(self) -> list[str]:
        """For each vector column, the input field it came from."""
        return [f.name for f in self.features for _ in f.columns]

    def vector(self, record: Mapping[str, Any]) -> list[float]:
        """One record of named inputs as a vector. Missing values become NaN."""
        row: list[float] = []
        for feature in self.features:
            value = record.get(feature.name)
            if feature.kind == "categorical":
                row.extend(
                    math.nan if value is None else float(value == option)
                    for option in feature.values
                )
            elif value is None:
                row.append(math.nan)
            elif feature.kind == "boolean":
                row.append(float(_as_bool(value)))
            else:
                row.append(float(value))
        return row

    def matrix(self, records: Iterable[Mapping[str, Any]]) -> npt.NDArray[np.float32]:
        rows = [self.vector(r) for r in records]
        return np.asarray(rows, dtype=np.float32).reshape(len(rows), len(self.columns))

    def to_json(self) -> str:
        return json.dumps(
            {
                "model": self.model,
                "feature_version": self.feature_version,
                "features": [_feature_json(f) for f in self.features],
            },
            indent=2,
        )


def _feature_json(feature: Feature) -> dict[str, Any]:
    result: dict[str, Any] = {"name": feature.name, "kind": feature.kind}
    if feature.values:
        result["values"] = list(feature.values)
    return result


def _as_bool(value: Any) -> bool:
    if isinstance(value, str):
        return value.strip().lower() in ("1", "true", "t", "yes")
    return bool(value)


def parse(text: str) -> FeatureSpec:
    raw = json.loads(text)
    features = tuple(
        Feature(name=f["name"], kind=f["kind"], values=tuple(f.get("values", ())))
        for f in raw["features"]
    )
    for feature in features:
        if feature.kind not in ("numeric", "boolean", "categorical"):
            raise ValueError(f"unknown feature kind {feature.kind!r} for {feature.name}")
        if feature.kind == "categorical" and not feature.values:
            raise ValueError(f"categorical feature {feature.name} needs values")
    return FeatureSpec(
        model=raw["model"], feature_version=raw["feature_version"], features=features
    )


def load(path: Path = SPEC_FILE) -> FeatureSpec:
    return parse(path.read_text(encoding="utf-8"))
