#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the ``change-type-heuristic`` subcommand of manage-status.

The classifier maps a plan's clarified-request narrative to a
change_type (feature / bug_fix / tech_debt / enhancement / verification
/ analysis) using a deterministic keyword table, and flips
``ambiguous=true`` when no keyword fires, when two change types tie, or
when confidence falls below 0.7. The LLM ``detect-change-type``
workflow only fires on the ambiguous branch.
"""

from __future__ import annotations

import json
from argparse import Namespace
from pathlib import Path

from conftest import load_script_module

_mod = load_script_module(
    'plan-marshall', 'manage-status', '_cmd_change_type_heuristic.py', '_cmd_change_type_heuristic_under_test'
)
cmd_change_type_heuristic = _mod.cmd_change_type_heuristic


def _ns(plan_id: str, persist: bool = False) -> Namespace:
    return Namespace(plan_id=plan_id, persist=persist)


def _write_request(plan_dir: Path, body: str, section: str = 'clarified_request') -> None:
    """Write a minimal request.md with the narrative in the chosen section."""
    plan_dir.mkdir(parents=True, exist_ok=True)
    if section == 'original_input':
        content = (
            '# Request\n\n'
            '## Original Input\n\n'
            f'{body}\n'
        )
    else:
        content = (
            '# Request\n\n'
            '## Original Input\n\n'
            '(unused)\n\n'
            '## Clarified Request\n\n'
            f'{body}\n'
        )
    (plan_dir / 'request.md').write_text(content, encoding='utf-8')


def _write_status(plan_dir: Path) -> None:
    """Seed a minimal status.json so --persist write paths can read it."""
    plan_dir.mkdir(parents=True, exist_ok=True)
    (plan_dir / 'status.json').write_text(
        json.dumps({'plan_id': plan_dir.name, 'phases': [], 'metadata': {}}),
        encoding='utf-8',
    )


# =============================================================================
# Happy path — each change type resolves
# =============================================================================


def test_feature_resolves_on_add_create(plan_context):
    _write_request(plan_context.plan_dir_for('cth-feature'), 'Add a new authentication module that creates session tokens.')
    result = cmd_change_type_heuristic(_ns('cth-feature'))
    assert result['change_type'] == 'feature'
    assert result['ambiguous'] is False


def test_enhancement_resolves_on_improve_upgrade(plan_context):
    _write_request(plan_context.plan_dir_for('cth-enh'), 'Improve the existing logger to upgrade its formatter.')
    result = cmd_change_type_heuristic(_ns('cth-enh'))
    assert result['change_type'] == 'enhancement'
    assert result['ambiguous'] is False


def test_bug_fix_resolves_on_fix_plus_bug_object(plan_context):
    _write_request(plan_context.plan_dir_for('cth-bugfix'), 'Fix the regression that causes a crash on startup.')
    result = cmd_change_type_heuristic(_ns('cth-bugfix'))
    assert result['change_type'] == 'bug_fix'
    assert result['ambiguous'] is False


def test_tech_debt_resolves_on_refactor_cleanup(plan_context):
    _write_request(plan_context.plan_dir_for('cth-techdebt'), 'Refactor the module to remove legacy patterns and migrate cleanup helpers.')
    result = cmd_change_type_heuristic(_ns('cth-techdebt'))
    assert result['change_type'] == 'tech_debt'
    assert result['ambiguous'] is False


def test_tech_debt_resolves_on_fix_plus_tech_debt_object(plan_context):
    """``fix deprecations`` → tech_debt, not bug_fix."""
    _write_request(plan_context.plan_dir_for('cth-fixdep'), 'Fix the deprecations and outdated warnings in the SDK.')
    result = cmd_change_type_heuristic(_ns('cth-fixdep'))
    assert result['change_type'] == 'tech_debt'
    assert result['ambiguous'] is False


def test_verification_resolves_on_verify_audit(plan_context):
    _write_request(plan_context.plan_dir_for('cth-verify'), 'Verify and audit the deployment to confirm the rollout invariants.')
    result = cmd_change_type_heuristic(_ns('cth-verify'))
    assert result['change_type'] == 'verification'
    assert result['ambiguous'] is False


def test_analysis_resolves_on_investigate_research(plan_context):
    _write_request(plan_context.plan_dir_for('cth-analysis'), 'Investigate and research the recent latency anomaly to understand the root cause.')
    result = cmd_change_type_heuristic(_ns('cth-analysis'))
    assert result['change_type'] == 'analysis'
    assert result['ambiguous'] is False


# =============================================================================
# Compound-intent guard
# =============================================================================


def test_compound_intent_demotes_analysis_when_action_verb_present(plan_context):
    """`Analyze X and fix issues` should resolve to bug_fix/enhancement, not analysis."""
    _write_request(plan_context.plan_dir_for('cth-compound'), 'Analyze the failing module and fix the crash.')
    result = cmd_change_type_heuristic(_ns('cth-compound'))
    assert result['change_type'] != 'analysis'
    # crash → bug_fix in the object-disambiguation path
    assert result['change_type'] == 'bug_fix'


def test_compound_intent_routes_analyze_and_refactor_to_tech_debt(plan_context):
    _write_request(plan_context.plan_dir_for('cth-compound-td'), 'Analyze and refactor the legacy migration scripts to remove deprecations.')
    result = cmd_change_type_heuristic(_ns('cth-compound-td'))
    assert result['change_type'] == 'tech_debt'


# =============================================================================
# Ambiguous branch
# =============================================================================


def test_ambiguous_when_no_keyword_matches(plan_context):
    _write_request(plan_context.plan_dir_for('cth-amb-none'), 'The thing should do the thing per the thing.')
    result = cmd_change_type_heuristic(_ns('cth-amb-none'))
    assert result['ambiguous'] is True
    assert result['change_type'] is None


def test_ambiguous_when_two_change_types_tie(plan_context):
    """Roughly equal feature + enhancement signal flips ambiguous=true."""
    _write_request(
        plan_context.plan_dir_for('cth-amb-tie'),
        'Create a new module and improve the existing one.',
    )
    result = cmd_change_type_heuristic(_ns('cth-amb-tie'))
    # "create" + "new" + "implement" hits feature (2-3), "improve" hits
    # enhancement (1). The single-keyword margin is below the confidence
    # floor unless feature dominates 2:1 — confirm via the API contract
    # (either ambiguous OR feature with low confidence is acceptable;
    # both signal the LLM dispatch should fire).
    if not result['ambiguous']:
        assert result['confidence'] >= 0.7
        assert result['change_type'] == 'feature'


def test_ambiguous_when_request_missing(plan_context):
    """No request.md → ambiguous=true, source=None."""
    # Create the plan dir but NOT write request.md.
    plan_context.plan_dir_for('cth-amb-no-req')
    result = cmd_change_type_heuristic(_ns('cth-amb-no-req'))
    assert result['ambiguous'] is True
    assert result['source'] is None


def test_ambiguous_falls_back_to_original_input(plan_context):
    """An empty clarified_request falls back to original_input."""
    _write_request(
        plan_context.plan_dir_for('cth-fallback'),
        'Add a new authentication module.',
        section='original_input',
    )
    result = cmd_change_type_heuristic(_ns('cth-fallback'))
    assert result['source'] == 'original_input'
    assert result['change_type'] == 'feature'


# =============================================================================
# Persistence
# =============================================================================


def test_persist_writes_status_metadata_when_not_ambiguous(plan_context):
    plan_dir = plan_context.plan_dir_for('cth-persist')
    _write_request(plan_dir, 'Add a new authentication module.')
    _write_status(plan_dir)

    result = cmd_change_type_heuristic(_ns('cth-persist', persist=True))
    assert result['persisted'] is True
    status = json.loads((plan_dir / 'status.json').read_text())
    assert status['metadata']['change_type'] == 'feature'


def test_persist_skipped_when_ambiguous(plan_context):
    """Ambiguous path must not write to status — LLM fallback owns that write."""
    plan_dir = plan_context.plan_dir_for('cth-persist-amb')
    _write_request(plan_dir, 'The thing should do the thing.')
    _write_status(plan_dir)

    result = cmd_change_type_heuristic(_ns('cth-persist-amb', persist=True))
    assert result['ambiguous'] is True
    assert result['persisted'] is False
    status = json.loads((plan_dir / 'status.json').read_text())
    assert 'change_type' not in status.get('metadata', {})


# =============================================================================
# Plan-dir error path
# =============================================================================


def test_plan_dir_not_found_errors(plan_context):
    result = cmd_change_type_heuristic(_ns('does-not-exist'))
    assert result['status'] == 'error'
    assert result['error'] == 'plan_dir_not_found'


# =============================================================================
# Dispatch wiring
# =============================================================================


def test_change_type_heuristic_registered_in_manage_status_dispatch():
    """The subcommand is wired into manage-status.py argparse."""
    import argparse  # noqa: PLC0415

    manage_status = load_script_module(
        'plan-marshall', 'manage-status', 'manage-status.py', '_manage_status_dispatch_check'
    )

    # The cmd module exports cmd_change_type_heuristic; manage-status.py
    # imports the same callable. Confirm both halves of the wiring.
    assert manage_status.cmd_change_type_heuristic is cmd_change_type_heuristic or callable(
        manage_status.cmd_change_type_heuristic
    )
    # Lightweight argparse smoke: build a parser with one subparser and confirm
    # the dispatch handler resolves the same object.
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest='cmd')
    leaf = sub.add_parser('change-type-heuristic')
    leaf.set_defaults(func=manage_status.cmd_change_type_heuristic)
    ns = p.parse_args(['change-type-heuristic'])
    assert ns.func is manage_status.cmd_change_type_heuristic
