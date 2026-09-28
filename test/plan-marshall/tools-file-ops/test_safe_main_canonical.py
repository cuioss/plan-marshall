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
failure) cannot silently drift between subsystems.

These tests fail if a new ``def safe_main`` reappears anywhere else, catching a
re-duplication at review time.

The rendering half pins the one typed exception ``safe_main`` does NOT treat as a
crash: the orchestrator store seam's ``OrchestratorStoreUnavailable`` renders its
own ``error`` code and fields with exit 0, while every other exception keeps the
``internal_error`` / exit 1 path.
"""

import re

import pytest
from file_ops import OrchestratorStoreUnavailable, safe_main
from toon_parser import parse_toon

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
    """The build, workflow, and CI barrels expose the canonical object, not a copy."""
    import _build_cli
    import ci_base
    import file_ops
    import triage_helpers

    assert _build_cli.safe_main is file_ops.safe_main
    assert ci_base.safe_main is file_ops.safe_main
    assert triage_helpers.safe_main is file_ops.safe_main


def _run_wrapped(raised: BaseException, capsys) -> tuple[object, dict]:
    """Run a ``safe_main``-wrapped entry point that raises ``raised``.

    Returns the exit code and the TOON payload the wrapper printed on stdout.
    """

    @safe_main
    def main() -> int:
        raise raised

    with pytest.raises(SystemExit) as exit_info:
        main()
    payload = parse_toon(capsys.readouterr().out)
    return exit_info.value.code, payload


def test_store_refusal_renders_its_own_code_and_fields_with_exit_zero(capsys):
    """A store-seam refusal is an operation failure: its code and fields, exit 0."""
    refusal = OrchestratorStoreUnavailable(
        'ledger_cutover_refused',
        'the main checkout holds 1 uncommitted or unlanded ledger path(s)',
        dirty_paths=['.plan/orchestrator/epic-a/epic.md'],
        branch='chore/orchestrator-ledger',
    )

    code, payload = _run_wrapped(refusal, capsys)

    assert code == 0
    assert payload['status'] == 'error'
    assert payload['error'] == 'ledger_cutover_refused'
    assert payload['message'] == 'the main checkout holds 1 uncommitted or unlanded ledger path(s)'
    assert payload['dirty_paths'] == ['.plan/orchestrator/epic-a/epic.md']
    assert payload['branch'] == 'chore/orchestrator-ledger'


@pytest.mark.parametrize(
    'raised',
    [RuntimeError('boom'), ValueError('bad value'), OSError('disk gone')],
    ids=['runtime-error', 'value-error', 'os-error'],
)
def test_any_other_exception_still_renders_internal_error_with_exit_one(raised, capsys):
    """Every exception other than the store refusal keeps the crash path."""
    code, payload = _run_wrapped(raised, capsys)

    assert code == 1
    assert payload['status'] == 'error'
    assert payload['error'] == 'internal_error'
    assert payload['message'] == str(raised)
