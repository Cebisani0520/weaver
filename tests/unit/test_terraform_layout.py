"""Structural checks on the Terraform tree that need no Terraform binary."""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.tfparse import load, tf_files

MODULE_FILES = {"main.tf", "variables.tf", "outputs.tf", "versions.tf"}


def all_tf(repo_root: Path) -> list[Path]:
    return sorted((repo_root / "infra").rglob("*.tf"))


def modules(repo_root: Path) -> list[Path]:
    return sorted(p for p in (repo_root / "infra/modules").iterdir() if p.is_dir())


def test_every_tf_file_parses(repo_root: Path) -> None:
    for path in all_tf(repo_root):
        load(path)  # raises on a syntax error


@pytest.mark.parametrize("name", sorted(MODULE_FILES))
def test_modules_have_standard_files(repo_root: Path, name: str) -> None:
    missing = [m.name for m in modules(repo_root) if not (m / name).is_file()]
    assert missing == [], f"modules missing {name}: {missing}"


def test_no_provider_blocks_below_environment_roots(repo_root: Path) -> None:
    offenders = []
    for directory in ("modules", "stacks"):
        for path in (repo_root / "infra" / directory).rglob("*.tf"):
            if load(path).get("provider"):
                offenders.append(str(path.relative_to(repo_root)))
    assert offenders == [], f"provider blocks belong in environment roots: {offenders}"


def test_variables_and_outputs_are_described(repo_root: Path) -> None:
    undocumented = []
    for path in all_tf(repo_root):
        parsed = load(path)
        for kind in ("variable", "output"):
            for block in parsed.get(kind, []):
                for name, body in block.items():
                    if not body.get("description"):
                        undocumented.append(f"{path.relative_to(repo_root)}: {kind} {name}")
    assert undocumented == []


def test_module_and_stack_dirs_pin_required_version(repo_root: Path) -> None:
    unpinned = []
    for base in ("modules", "stacks"):
        for directory in sorted(p for p in (repo_root / "infra" / base).iterdir() if p.is_dir()):
            versions = [load(p).get("terraform", []) for p in tf_files(directory)]
            blocks = [b for group in versions for b in group]
            if not any("required_version" in b for b in blocks):
                unpinned.append(directory.name)
    assert unpinned == []
