"""Small helpers for reading Terraform files with python-hcl2."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import hcl2


def load(path: Path) -> dict[str, Any]:
    """Parse one .tf file into python-hcl2's dictionary form."""
    with path.open(encoding="utf-8") as handle:
        parsed: dict[str, Any] = hcl2.load(handle)
    return parsed


def tf_files(directory: Path) -> list[Path]:
    """The .tf files Terraform would load from one directory (not recursive)."""
    return sorted(p for p in directory.glob("*.tf") if p.is_file())


def unquote(value: str) -> str:
    """python-hcl2 keeps quotes on some labels and values; strip them."""
    return value.strip().strip('"')


def resource_types(directory: Path) -> Iterator[tuple[Path, str, str]]:
    """Yield (file, type, name) for every resource block in a directory."""
    for path in tf_files(directory):
        for block in load(path).get("resource", []):
            for rtype, instances in block.items():
                for name in instances:
                    yield path, unquote(rtype), unquote(name)


def module_sources(directory: Path) -> Iterator[tuple[str, str]]:
    """Yield (module name, source) for every module block in a directory."""
    for path in tf_files(directory):
        for block in load(path).get("module", []):
            for name, body in block.items():
                source = body.get("source")
                if isinstance(source, str):
                    yield unquote(name), unquote(source)
