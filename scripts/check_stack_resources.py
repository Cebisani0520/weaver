"""Fail if any stack under infra/stacks defines a resource directly.

Repository rule: stacks compose modules; every resource (terraform_data
included) lives in infra/modules. Data sources, locals and outputs are allowed.

Usage: python scripts/check_stack_resources.py [stacks_dir]
"""

from __future__ import annotations

import sys
from pathlib import Path

from scripts.tfparse import resource_types

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_STACKS = REPO_ROOT / "infra" / "stacks"


def find_violations(stacks_dir: Path) -> list[str]:
    """Return one message per resource block found in any stack."""
    violations: list[str] = []
    for stack in sorted(p for p in stacks_dir.iterdir() if p.is_dir()):
        for path, rtype, name in resource_types(stack):
            violations.append(
                f'{_rel(path)}: resource "{rtype}" "{name}" belongs in a module under infra/modules'
            )
    return violations


def _rel(path: Path) -> Path:
    try:
        return path.resolve().relative_to(REPO_ROOT)
    except ValueError:
        return path


def main(argv: list[str]) -> int:
    stacks_dir = Path(argv[1]) if len(argv) > 1 else DEFAULT_STACKS
    if not stacks_dir.is_dir():
        print(f"No stacks directory at {stacks_dir}", file=sys.stderr)
        return 1
    violations = find_violations(stacks_dir)
    for message in violations:
        print(message, file=sys.stderr)
    if violations:
        print(f"\n{len(violations)} resource block(s) found in stacks.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
