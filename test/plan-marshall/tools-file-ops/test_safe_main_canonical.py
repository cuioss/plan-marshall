#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Guard: ``safe_main`` has a single definition across the marketplace.

``safe_main`` is the CLI entry-point wrapper that renders an uncaught exception
as a ``status: error`` TOON on stdout, maps ``KeyboardInterrupt`` to 130, and
preserves exit code 1 for genuine crashes. It is defined once, in
``tools-file-ops/scripts/file_ops.py``. Every other module that exposes it — the
build barrel ``_build_cli``, the workflow barrel ``triage_helpers``, and the CI
barrel ``ci_base`` — re-exports the canonical object instead of defining its own
copy, so error-handling behaviour (exit codes, error formatting, TOON output on
failure) cannot silently drift between subsystems (#821).

These tests fail if a new ``def safe_main`` reappears anywhere else, catching a
re-duplication at review time.
"""

import re

from conftest import MARKETPLACE_ROOT

_DEF_SAFE_MAIN = re.compile(r'^def safe_main\b', re.MULTILINE)

CANONICAL = 'tools-file-ops/scripts/file_ops.py'


def test_safe_main_defined_only_in_file_ops():
    """No module other than file_ops.py may define its own safe_main."""
    definers = [
        path
        for path in MARKETPLACE_ROOT.rglob('*.py')
        if '__pycache__' not in path.parts and _DEF_SAFE_MAIN.search(path.read_text(encoding='utf-8'))
    ]

    rel = sorted(str(p.relative_to(MARKETPLACE_ROOT)) for p in definers)
    assert len(rel) == 1, f'safe_main must be defined exactly once (in {CANONICAL}); found definitions in: {rel}'
    assert rel[0].endswith(CANONICAL), f'the sole safe_main definition must live in {CANONICAL}; found {rel[0]}'


def test_barrels_reexport_canonical_safe_main():
    """The build and workflow barrels expose the canonical object, not a copy."""
    import _build_cli
    import file_ops
    import triage_helpers

    assert _build_cli.safe_main is file_ops.safe_main
    assert triage_helpers.safe_main is file_ops.safe_main
