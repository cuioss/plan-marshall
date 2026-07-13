# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""Tests for the marshall-steward ``upgrade`` stage-plan / gate-decision emitter.

``upgrade.py`` is a pure deterministic planner: its ``plan`` subcommand emits
the fixed four-stage post-change-reconciliation plan with per-stage gate
dispositions as a function of ``--integrate``. These tests drive the planner's
``main`` entry directly with constructed argv, capture stdout, and parse the
emitted TOON with the canonical parser to assert the stage order, the
top-level-gate suppression semantics, and the ``integrate``-invariance of the
nested gates.

``upgrade.py`` is a marshall-steward skill script, not on ``PYTHONPATH`` during
pytest collection; the canonical ``sys.path.insert`` prologue (see
``pm-plugin-development:plugin-script-architecture`` test-scaffolding.md) makes
it and the shared TOON parser importable.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# test/plan-marshall/marshall-steward/ -> repo root is three parents up.
_REPO_ROOT = Path(__file__).resolve().parents[3]
_SCRIPTS_DIR = (
    _REPO_ROOT / 'marketplace' / 'bundles' / 'plan-marshall' / 'skills' / 'marshall-steward' / 'scripts'
)
_TOON_SCRIPTS = _REPO_ROOT / 'marketplace' / 'bundles' / 'plan-marshall' / 'skills' / 'ref-toon-format' / 'scripts'
for _dir in (_SCRIPTS_DIR, _TOON_SCRIPTS):
    if str(_dir) not in sys.path:
        sys.path.insert(0, str(_dir))

import upgrade  # noqa: E402
from toon_parser import parse_toon  # noqa: E402

_EXPECTED_STAGE_KEYS = ['regenerate-targets', 'reconcile-config', 'verify', 'land']
_EXPECTED_STAGE_ORDERS = [1, 2, 3, 4]
_EXPECTED_NESTED_GATES = {
    'regenerate-targets': set(),
    'reconcile-config': {'build-map-reseed'},
    'verify': set(),
    'land': {'land-leave', 'branch-reuse'},
}
_STAGE_ROW_KEYS = {'order', 'key', 'name', 'mutating', 'top_level_gate', 'nested_gates'}


def _run(argv: list[str], capsys: pytest.CaptureFixture[str]) -> tuple[int, dict]:
    """Drive ``upgrade.main`` with constructed argv, returning ``(exit_code, parsed_toon)``."""
    exit_code = upgrade.main(argv)
    captured = capsys.readouterr()
    parsed = parse_toon(captured.out)
    return exit_code, parsed


def test_default_emits_four_stages_in_documented_order(capsys: pytest.CaptureFixture[str]):
    """The default invocation exits 0 and emits the four stages in the exact
    documented order (by both ``key`` and ``order``).
    """
    exit_code, parsed = _run(['plan'], capsys)

    assert exit_code == 0
    assert parsed['integrate'] is False
    stages = parsed['stages']
    assert [stage['key'] for stage in stages] == _EXPECTED_STAGE_KEYS
    assert [stage['order'] for stage in stages] == _EXPECTED_STAGE_ORDERS


def test_integrate_true_suppresses_all_top_level_gates(capsys: pytest.CaptureFixture[str]):
    """``--integrate true`` exits 0 and yields ``top_level_gate == suppressed``
    for all four stages.
    """
    exit_code, parsed = _run(['plan', '--integrate', 'true'], capsys)

    assert exit_code == 0
    assert parsed['integrate'] is True
    assert [stage['top_level_gate'] for stage in parsed['stages']] == ['suppressed'] * 4


@pytest.mark.parametrize('argv', [['plan'], ['plan', '--integrate', 'false']])
def test_plain_mode_prompts_all_top_level_gates(argv: list[str], capsys: pytest.CaptureFixture[str]):
    """The default and the explicit ``--integrate false`` both yield
    ``top_level_gate == prompt`` for all four stages.
    """
    exit_code, parsed = _run(argv, capsys)

    assert exit_code == 0
    assert [stage['top_level_gate'] for stage in parsed['stages']] == ['prompt'] * 4


def test_nested_gates_are_integrate_invariant(capsys: pytest.CaptureFixture[str]):
    """The nested-gate sets are identical under ``integrate`` true and false —
    ``integrate`` suppresses only the top-level stage gates, never the nested
    ones — and match the documented mapping.
    """
    _true_exit, true_parsed = _run(['plan', '--integrate', 'true'], capsys)
    _false_exit, false_parsed = _run(['plan', '--integrate', 'false'], capsys)

    true_nested = {stage['key']: set(stage['nested_gates']) for stage in true_parsed['stages']}
    false_nested = {stage['key']: set(stage['nested_gates']) for stage in false_parsed['stages']}

    assert true_nested == false_nested
    assert true_nested == _EXPECTED_NESTED_GATES


def test_toon_carries_documented_keys(capsys: pytest.CaptureFixture[str]):
    """The emitted TOON parses and carries the documented top-level keys and
    per-stage row keys.
    """
    _exit_code, parsed = _run(['plan', '--integrate', 'true'], capsys)

    assert {'status', 'integrate', 'stages'}.issubset(parsed.keys())
    assert parsed['status'] == 'success'
    for stage in parsed['stages']:
        assert _STAGE_ROW_KEYS.issubset(stage.keys())
        assert isinstance(stage['nested_gates'], list)
