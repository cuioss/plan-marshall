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
_STAGE_ROW_KEYS = {'order', 'key', 'name', 'mutating', 'top_level_gate', 'nested_gates', 'sub_steps'}

# The meta/consumer sub-step matrix (keyed by stage key). Consumer drops the
# meta-only sub-steps (regenerate-target-tree in Stage 1, content-drift-report
# in Stage 3) and gains the consumer-only cache-freshness gate as Stage 1's
# FIRST sub-step; Stages 2 and 4 are kind-invariant.
_EXPECTED_SUB_STEPS = {
    'meta': {
        'regenerate-targets': ['regenerate-target-tree', 'regenerate-executor'],
        'reconcile-config': ['reconcile-marshal-json'],
        'verify': ['executor-preflight', 'content-drift-report'],
        'land': ['run-landing-cycle'],
    },
    'consumer': {
        'regenerate-targets': ['cache-freshness-check', 'regenerate-executor'],
        'reconcile-config': ['reconcile-marshal-json'],
        'verify': ['executor-preflight'],
        'land': ['run-landing-cycle'],
    },
}


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

    assert {'status', 'integrate', 'project_kind', 'stages'}.issubset(parsed.keys())
    assert parsed['status'] == 'success'
    for stage in parsed['stages']:
        assert _STAGE_ROW_KEYS.issubset(stage.keys())
        assert isinstance(stage['nested_gates'], list)
        assert isinstance(stage['sub_steps'], list)


# ============================================================================
# Deliverable 2: project-kind detection and the kind-aware sub-step matrix
# ============================================================================


@pytest.mark.parametrize('project_kind', ['meta', 'consumer'])
def test_build_plan_sub_steps_match_kind_matrix(project_kind: str):
    """build_plan(integrate, project_kind) emits each stage's per-kind sub_steps:
    consumer drops the meta-only sub-steps (regenerate-target-tree, content-drift-report).
    """
    plan = upgrade.build_plan(False, project_kind)

    assert plan['project_kind'] == project_kind
    actual = {stage['key']: stage['sub_steps'] for stage in plan['stages']}
    assert actual == _EXPECTED_SUB_STEPS[project_kind]


def test_build_plan_consumer_excludes_meta_only_sub_steps():
    """A consumer plan's Stage 3 sub_steps are exactly [executor-preflight] and
    its Stage 1 carries neither meta-only sub-step — the meta-only sub-steps are
    absent."""
    plan = upgrade.build_plan(False, 'consumer')
    by_key = {stage['key']: stage['sub_steps'] for stage in plan['stages']}

    assert by_key['verify'] == ['executor-preflight']
    assert 'regenerate-target-tree' not in by_key['regenerate-targets']
    assert 'content-drift-report' not in by_key['verify']


def test_consumer_stage_1_leads_with_cache_freshness_check():
    """The consumer kind gates on plugin-cache freshness as Stage 1's FIRST
    sub-step, ahead of regenerate-executor — it is regenerate-executor that
    reads the unrefreshed cache."""
    by_key = {s['key']: s['sub_steps'] for s in upgrade.build_plan(False, 'consumer')['stages']}

    stage_1 = by_key['regenerate-targets']
    assert stage_1[0] == 'cache-freshness-check'
    assert stage_1.index('cache-freshness-check') < stage_1.index('regenerate-executor')


def test_meta_kind_does_not_gain_cache_freshness_check():
    """The freshness gate is consumer-scoped: the meta project refreshes its own
    cache via project:finalize-step-sync-plugin-cache, so no meta stage carries
    cache-freshness-check."""
    plan = upgrade.build_plan(False, 'meta')

    for stage in plan['stages']:
        assert 'cache-freshness-check' not in stage['sub_steps']


def test_build_plan_rejects_unknown_project_kind():
    """build_plan raises on a project_kind that is neither meta nor consumer."""
    with pytest.raises(ValueError):
        upgrade.build_plan(False, 'not-a-kind')


def test_build_plan_preserves_stage_order_and_gates_across_kinds():
    """Stage order, keys, top-level-gate suppression, and nested-gate invariance
    are unchanged across both project kinds — the kind only varies sub_steps."""
    for project_kind in ('meta', 'consumer'):
        plain = upgrade.build_plan(False, project_kind)
        integrated = upgrade.build_plan(True, project_kind)

        assert [s['key'] for s in plain['stages']] == _EXPECTED_STAGE_KEYS
        assert [s['order'] for s in plain['stages']] == _EXPECTED_STAGE_ORDERS
        assert [s['top_level_gate'] for s in plain['stages']] == ['prompt'] * 4
        assert [s['top_level_gate'] for s in integrated['stages']] == ['suppressed'] * 4
        nested = {s['key']: set(s['nested_gates']) for s in plain['stages']}
        assert nested == _EXPECTED_NESTED_GATES


def test_detect_project_kind_meta_when_marketplace_tree_present(tmp_path: Path):
    """detect_project_kind classifies a dir WITH marketplace/targets/generate.py
    AND marketplace/bundles/ as meta (the plan-marshall meta-project shape)."""
    (tmp_path / 'marketplace' / 'targets').mkdir(parents=True)
    (tmp_path / 'marketplace' / 'targets' / 'generate.py').write_text('# fixture generator\n', encoding='utf-8')
    (tmp_path / 'marketplace' / 'bundles').mkdir(parents=True)

    assert upgrade.detect_project_kind(tmp_path) == 'meta'


def test_detect_project_kind_consumer_when_marketplace_absent(tmp_path: Path):
    """detect_project_kind classifies a dir WITHOUT the marketplace tree as
    consumer (the downstream-consumer shape) — the Leg A acceptance assertion."""
    (tmp_path / 'src').mkdir()

    assert upgrade.detect_project_kind(tmp_path) == 'consumer'


def test_detect_project_kind_consumer_when_only_one_marker_present(tmp_path: Path):
    """Presence of only ONE of the two markers is still consumer — both the
    generator AND the bundle tree are required for meta."""
    (tmp_path / 'marketplace' / 'bundles').mkdir(parents=True)  # bundles only, no generate.py

    assert upgrade.detect_project_kind(tmp_path) == 'consumer'


@pytest.mark.parametrize('project_kind', ['meta', 'consumer'])
def test_project_kind_flag_honored_verbatim(project_kind: str, capsys: pytest.CaptureFixture[str]):
    """--project-kind {meta|consumer} is honored verbatim (no cwd detection)."""
    _exit_code, parsed = _run(['plan', '--project-kind', project_kind], capsys)

    assert parsed['project_kind'] == project_kind
    actual = {stage['key']: stage['sub_steps'] for stage in parsed['stages']}
    assert actual == _EXPECTED_SUB_STEPS[project_kind]


def test_project_kind_auto_invokes_detector(monkeypatch, capsys: pytest.CaptureFixture[str]):
    """--project-kind auto (the default) resolves the kind via detect_project_kind
    against the cwd rather than a hard-coded value."""
    monkeypatch.setattr(upgrade, 'detect_project_kind', lambda root: 'consumer')

    _exit_code, parsed = _run(['plan', '--project-kind', 'auto'], capsys)

    assert parsed['project_kind'] == 'consumer'
    by_key = {stage['key']: stage['sub_steps'] for stage in parsed['stages']}
    assert by_key['regenerate-targets'] == _EXPECTED_SUB_STEPS['consumer']['regenerate-targets']
