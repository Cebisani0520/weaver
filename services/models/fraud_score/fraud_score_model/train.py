"""SageMaker training entry point: `train` in the container runs this module.

Follows the SageMaker container contract, which Floci also implements:
  /opt/ml/input/config/hyperparameters.json   hyperparameters (all values are strings)
  /opt/ml/input/data/<channel>/               channel files: train and validation
  /opt/ml/model/                              everything here becomes model.tar.gz
  /opt/ml/output/failure                      reason, if training fails

Channels hold CSV files with a header: `label` followed by the spec's vector
columns, in order. The header is checked, so data built for another feature
version fails loudly instead of training a silently wrong model.

Runs on Python 3.12 in the container: no 3.13-only syntax or stdlib.
"""

from __future__ import annotations

import csv
import json
import os
import sys
import traceback
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import numpy.typing as npt
import xgboost as xgb

from . import metrics
from .spec import FeatureSpec, load

DEFAULT_BASE = Path("/opt/ml")

DEFAULT_HYPERPARAMETERS: dict[str, Any] = {
    "max_depth": 4,
    "eta": 0.1,
    "num_round": 400,
    "early_stopping_rounds": 30,
    "min_child_weight": 1.0,
    "subsample": 0.9,
    "colsample_bytree": 0.9,
    # 1 keeps scores calibrated as probabilities; the decision threshold handles
    # the class imbalance instead.
    "scale_pos_weight": 1.0,
    "seed": 42,
}

# Floats unless listed here.
_INTEGER_HYPERPARAMETERS = {"max_depth", "num_round", "early_stopping_rounds", "seed"}


def hyperparameters(config_dir: Path) -> dict[str, Any]:
    """Defaults, overridden by hyperparameters.json when SageMaker provides one."""
    params = dict(DEFAULT_HYPERPARAMETERS)
    path = config_dir / "hyperparameters.json"
    if path.exists():
        for key, value in json.loads(path.read_text(encoding="utf-8")).items():
            if key not in DEFAULT_HYPERPARAMETERS:
                raise ValueError(f"unknown hyperparameter {key!r}")
            params[key] = int(value) if key in _INTEGER_HYPERPARAMETERS else float(value)
    return params


def read_channel(
    channel_dir: Path, spec: FeatureSpec
) -> tuple[npt.NDArray[np.float32], npt.NDArray[np.float32]]:
    """All CSV files under a channel directory as (features, labels)."""
    files = sorted(channel_dir.rglob("*.csv"))
    if not files:
        raise FileNotFoundError(f"no CSV files under {channel_dir}")
    expected = ["label", *spec.columns]
    rows: list[list[float]] = []
    for path in files:
        with path.open(newline="", encoding="utf-8") as handle:
            reader = csv.reader(handle)
            header = next(reader)
            if header != expected:
                raise ValueError(
                    f"{path.name}: header does not match feature spec {spec.feature_version}; "
                    f"expected {expected}, got {header}"
                )
            rows.extend([float(v) if v != "" else float("nan") for v in row] for row in reader)
    data = np.asarray(rows, dtype=np.float32)
    return data[:, 1:], data[:, 0]


def train(base: Path = DEFAULT_BASE) -> dict[str, Any]:
    """Train, evaluate on validation and write the model directory. Returns the metadata."""
    spec = load()
    params = hyperparameters(base / "input" / "config")
    x_train, y_train = read_channel(base / "input" / "data" / "train", spec)
    x_valid, y_valid = read_channel(base / "input" / "data" / "validation", spec)

    dtrain = xgb.DMatrix(x_train, label=y_train, feature_names=spec.columns)
    dvalid = xgb.DMatrix(x_valid, label=y_valid, feature_names=spec.columns)
    booster = xgb.train(
        {
            "objective": "binary:logistic",
            "eval_metric": ["aucpr", "logloss"],
            "tree_method": "hist",
            "max_depth": params["max_depth"],
            "eta": params["eta"],
            "min_child_weight": params["min_child_weight"],
            "subsample": params["subsample"],
            "colsample_bytree": params["colsample_bytree"],
            "scale_pos_weight": params["scale_pos_weight"],
            "seed": params["seed"],
        },
        dtrain,
        num_boost_round=params["num_round"],
        evals=[(dtrain, "train"), (dvalid, "validation")],
        early_stopping_rounds=params["early_stopping_rounds"],
        verbose_eval=50,
    )

    best = booster.best_iteration
    window = (0, best + 1)
    result = {
        **metrics.evaluate(y_train, booster.predict(dtrain, iteration_range=window), "train"),
        **metrics.evaluate(y_valid, booster.predict(dvalid, iteration_range=window), "validation"),
    }

    model_dir = base / "model"
    model_dir.mkdir(parents=True, exist_ok=True)
    # Keep only the trees up to the best iteration, so serving needs no range.
    booster[: best + 1].save_model(str(model_dir / "model.json"))
    (model_dir / "feature_spec.json").write_text(spec.to_json(), encoding="utf-8")
    metadata = {
        "model": spec.model,
        "feature_version": spec.feature_version,
        "trained_at": datetime.now(UTC).isoformat(),
        "training_job_name": os.environ.get("TRAINING_JOB_NAME"),
        "xgboost_version": xgb.__version__,
        "hyperparameters": params,
        "best_iteration": best,
        "metrics": result,
    }
    (model_dir / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return metadata


def main() -> int:
    base = Path(os.environ.get("SM_BASE_DIR", str(DEFAULT_BASE)))
    try:
        metadata = train(base)
    except Exception as error:
        failure = base / "output" / "failure"
        failure.parent.mkdir(parents=True, exist_ok=True)
        failure.write_text(f"{error}\n{traceback.format_exc()}", encoding="utf-8")
        print(f"training failed: {error}", file=sys.stderr)
        return 1
    print(json.dumps(metadata["metrics"], indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
