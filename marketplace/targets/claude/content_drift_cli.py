#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""CLI wrapper exposing the Claude-target content-drift check as a verb.

Thin argparse front end over
``marketplace.targets.claude.content_drift.run_content_drift_check``. It
performs NO drift detection of its own — it resolves the two directory
arguments, calls the existing engine, and serializes the returned
``ContentDriftResult`` to TOON. This exists so the ``marshall-steward``
``upgrade`` verb (Stage 3 — verify) can run the content-drift report as a
direct ``python3 marketplace/targets/claude/content_drift_cli.py``
invocation, exactly as ``generate.py`` is invoked for the emit step.

Exit codes follow the gate convention ``generate.py`` uses (non-zero on a
failing gate so a CI/steward step surfaces the failure):

* ``0`` — the check passed (no ``.md`` content drift).
* ``1`` — drift was detected, or ``target/claude`` is not generated.
* ``2`` — argparse rejection (automatic).

Both ``--target-dir`` (default ``target/claude``) and ``--marketplace-dir``
(default ``marketplace/bundles``) are resolved relative to the repo root
when given as relative paths.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# content_drift_cli.py lives at marketplace/targets/claude/; the repo root is
# four parents up. Put it on sys.path so `import marketplace.targets...`
# resolves, mirroring generate.py's bootstrap.
_repo_root = Path(__file__).resolve().parents[3]
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

# The shared TOON serializer lives in the ref-toon-format skill's scripts
# directory (the executor normally puts these on PYTHONPATH); add it so the
# canonical serializer is used instead of hand-rolled TOON (ref-toon-format
# forbids bypassing toon_parser).
_toon_scripts = (
    _repo_root
    / 'marketplace'
    / 'bundles'
    / 'plan-marshall'
    / 'skills'
    / 'ref-toon-format'
    / 'scripts'
)
if str(_toon_scripts) not in sys.path:
    sys.path.insert(0, str(_toon_scripts))

from marketplace.targets.claude.content_drift import (  # noqa: E402
    ContentDriftResult,
    run_content_drift_check,
)
from toon_parser import serialize_toon  # noqa: E402

DEFAULT_TARGET_DIR = 'target/claude'
DEFAULT_MARKETPLACE_DIR = 'marketplace/bundles'

EXIT_PASSED = 0
EXIT_DRIFT = 1


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog='content-drift-cli',
        description=(
            'Report Claude-target markdown content drift (regen-first diff of '
            'target/claude/ against a fresh emit of marketplace/bundles/).'
        ),
        allow_abbrev=False,
    )
    parser.add_argument(
        '--target-dir',
        type=Path,
        default=Path(DEFAULT_TARGET_DIR),
        help=(
            'On-disk emitted Claude target root. Relative paths resolve against '
            f'the repo root. Default: {DEFAULT_TARGET_DIR}.'
        ),
    )
    parser.add_argument(
        '--marketplace-dir',
        type=Path,
        default=Path(DEFAULT_MARKETPLACE_DIR),
        help=(
            'Bundle root the emitter walks. Relative paths resolve against the '
            f'repo root. Default: {DEFAULT_MARKETPLACE_DIR}.'
        ),
    )
    return parser


def _resolve_relative_to_root(path: Path, root: Path) -> Path:
    """Resolve ``path`` against ``root`` when relative; leave absolute paths as-is."""
    resolved = path if path.is_absolute() else root / path
    return resolved.resolve()


def _result_to_toon(result: ContentDriftResult) -> str:
    """Serialize a ``ContentDriftResult`` to the documented TOON report shape."""
    payload = {
        'status': 'success' if result.passed else 'error',
        'passed': result.passed,
        'drifted_count': len(result.drifted_files),
        'missing_count': len(result.missing_in_target),
        'orphan_count': len(result.orphan_in_target),
        'drifted_files': result.drifted_files,
        'missing_in_target': result.missing_in_target,
        'orphan_in_target': result.orphan_in_target,
        'summary': result.summary,
    }
    return serialize_toon(payload)


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    target_dir = _resolve_relative_to_root(args.target_dir, _repo_root)
    marketplace_dir = _resolve_relative_to_root(args.marketplace_dir, _repo_root)

    result = run_content_drift_check(target_dir, marketplace_dir)
    print(_result_to_toon(result))

    return EXIT_PASSED if result.passed else EXIT_DRIFT


if __name__ == '__main__':
    sys.exit(main())
