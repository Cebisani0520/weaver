"""SageMaker inference server: `serve` in the container runs this module.

Contract (SageMaker, and Floci's emulation of it):
  GET  /ping          200 once the model is loaded
  POST /invocations   scores; port 8080 unless SAGEMAKER_BIND_TO_PORT says otherwise
  /opt/ml/model/      the model artifact

Floci downloads ModelDataUrl into /opt/ml/model, and it is not documented
whether it extracts the tarball. Both layouts load: extracted files, or a
model.tar.gz that is unpacked here.

Request bodies:
  application/json  {"instances": [{"amount_cents": 480000, "channel": "PAYSHAP", ...}]}
                    (a bare list or a single object also work); missing fields are NaN
  text/csv          one row per payment, the spec's vector columns in order, no header

Response: {"model", "model_version", "feature_version", "predictions": [{"score", "reasons"}]}.
`reasons` are the inputs that pushed this score up most (XGBoost SHAP
contributions, summed per input field), for the alert and the analyst.

Standard library HTTP server: one process, a thread per request. Enough for the
POC; a production image would put gunicorn or the SageMaker inference toolkit
in front of the same Model class.

Runs on Python 3.12 in the container: no 3.13-only syntax or stdlib.
"""

from __future__ import annotations

import csv
import io
import json
import os
import sys
import tarfile
import tempfile
import threading
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import numpy as np
import numpy.typing as npt
import xgboost as xgb

from .spec import FeatureSpec, parse

DEFAULT_MODEL_DIR = Path("/opt/ml/model")
MAX_BODY_BYTES = 6 * 1024 * 1024  # SageMaker's real-time payload limit
TOP_REASONS = 3


def _find_model_json(directory: Path) -> Path | None:
    found = sorted(directory.rglob("model.json"), key=lambda p: len(p.parts))
    return found[0].parent if found else None


def resolve_model_dir(model_dir: Path) -> Path:
    """The directory holding model.json, unpacking a model.tar.gz if that is what arrived.

    model.json may sit at the root or one level down, depending on how the
    artifact was packed; the shallowest one wins.
    """
    found = _find_model_json(model_dir)
    if found is not None:
        return found
    archives = sorted(model_dir.rglob("*.tar.gz"))
    if not archives:
        raise FileNotFoundError(f"neither model.json nor a .tar.gz in {model_dir}")
    target = Path(tempfile.mkdtemp(prefix="model-"))
    with tarfile.open(archives[0], "r:gz") as archive:
        # The "data" filter refuses absolute paths, links out of the target and devices.
        archive.extractall(target, filter="data")  # nosec B202
    found = _find_model_json(target)
    if found is None:
        raise FileNotFoundError(f"{archives[0].name} has no model.json")
    return found


class Model:
    """A trained booster with the feature spec and metadata it was trained with."""

    def __init__(self, model_dir: Path) -> None:
        directory = resolve_model_dir(model_dir)
        self.spec: FeatureSpec = parse((directory / "feature_spec.json").read_text("utf-8"))
        self.booster = xgb.Booster()
        self.booster.load_model(str(directory / "model.json"))
        self.metadata: dict[str, Any] = _read_json(directory / "metadata.json")
        release = _read_json(directory / "model_version.json")
        # Written by the approve step; the endpoint's Environment is a fallback,
        # because Floci does not document passing it to the container.
        self.version = str(
            release.get("version") or os.environ.get("MODEL_VERSION") or "unreleased"
        )
        self._lock = threading.Lock()

    def score(self, matrix: npt.NDArray[np.float32]) -> list[dict[str, Any]]:
        if matrix.ndim != 2 or matrix.shape[1] != len(self.spec.columns):
            raise ValueError(
                f"expected {len(self.spec.columns)} columns ({', '.join(self.spec.columns)}), "
                f"got {matrix.shape[1] if matrix.ndim == 2 else matrix.shape}"
            )
        data = xgb.DMatrix(matrix, feature_names=self.spec.columns)
        with self._lock:
            scores = self.booster.predict(data)
            contributions = self.booster.predict(data, pred_contribs=True)
        return [
            {"score": round(float(s), 6), "reasons": self._reasons(c)}
            for s, c in zip(scores, contributions, strict=True)
        ]

    def _reasons(self, row: npt.NDArray[np.float32]) -> list[dict[str, Any]]:
        per_input: dict[str, float] = {}
        # The last contribution is the bias term.
        for source, value in zip(self.spec.column_sources, row[:-1], strict=True):
            per_input[source] = per_input.get(source, 0.0) + float(value)
        ranked = sorted(per_input.items(), key=lambda item: item[1], reverse=True)
        return [
            {"feature": name, "contribution": round(value, 4)}
            for name, value in ranked[:TOP_REASONS]
            if value > 0
        ]

    def describe(self) -> dict[str, Any]:
        return {
            "model": self.spec.model,
            "model_version": self.version,
            "feature_version": self.spec.feature_version,
        }


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    loaded = json.loads(path.read_text(encoding="utf-8"))
    return loaded if isinstance(loaded, dict) else {}


def parse_request(model: Model, content_type: str, body: bytes) -> npt.NDArray[np.float32]:
    media_type = content_type.split(";")[0].strip().lower()
    if media_type == "text/csv":
        rows = [
            [float(v) if v.strip() else float("nan") for v in row]
            for row in csv.reader(io.StringIO(body.decode("utf-8")))
            if row
        ]
        return np.asarray(rows, dtype=np.float32).reshape(len(rows), -1)
    if media_type in ("application/json", ""):
        payload = json.loads(body)
        if isinstance(payload, dict) and "instances" in payload:
            payload = payload["instances"]
        records = payload if isinstance(payload, list) else [payload]
        if not all(isinstance(r, dict) for r in records):
            raise ValueError("JSON instances must be objects of named features")
        return model.spec.matrix(records)
    raise ValueError(f"unsupported content type {content_type!r}; use application/json or text/csv")


def make_handler(model: Model) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        server_version = "weaver-model"
        protocol_version = "HTTP/1.1"

        def do_GET(self) -> None:
            if self.path == "/ping":
                self._send(HTTPStatus.OK, model.describe())
            else:
                self._send(HTTPStatus.NOT_FOUND, {"error": "not found"})

        def do_POST(self) -> None:
            if self.path != "/invocations":
                self._send(HTTPStatus.NOT_FOUND, {"error": "not found"})
                return
            length = int(self.headers.get("Content-Length") or 0)
            if length > MAX_BODY_BYTES:
                self._send(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, {"error": "payload too large"})
                return
            body = self.rfile.read(length)
            try:
                matrix = parse_request(model, self.headers.get("Content-Type", ""), body)
                predictions = model.score(matrix)
            except (ValueError, json.JSONDecodeError) as error:
                self._send(HTTPStatus.BAD_REQUEST, {"error": str(error)})
                return
            self._send(HTTPStatus.OK, {**model.describe(), "predictions": predictions})

        def _send(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
            data = json.dumps(payload).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, format: str, *args: Any) -> None:
            # /ping is polled constantly; log only invocations and errors.
            if self.path != "/ping":
                super().log_message(format, *args)

    return Handler


def make_server(model: Model, host: str, port: int) -> ThreadingHTTPServer:
    return ThreadingHTTPServer((host, port), make_handler(model))


def main() -> int:
    model_dir = Path(os.environ.get("SM_MODEL_DIR", str(DEFAULT_MODEL_DIR)))
    port = int(os.environ.get("SAGEMAKER_BIND_TO_PORT", "8080"))
    model = Model(model_dir)
    # All interfaces: SageMaker (and Floci) reach the container over its network.
    server = make_server(model, "0.0.0.0", port)  # noqa: S104  # nosec B104
    print(f"serving {model.describe()} on port {port}", file=sys.stderr)
    server.serve_forever()
    return 0


if __name__ == "__main__":
    sys.exit(main())
