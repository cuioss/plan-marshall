#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the lane's Sonar state and the merge condition it gates on.

The lane's job here is the half the merge gate was missing: a pull request whose
Sonar analysis still carries open issues is not ready, even when the SonarCloud
gate passes (that gate judges thresholds on new code, so it passes with issues
open). ``resolve`` reports the project's Sonar state beside its reviewers, the
lane reads the pull request's open issues through the provider's plan-less read,
and the merge is admitted only when the read is a confirmed zero or every
remaining issue carries a recorded dismissal.

Two failure modes are pinned here because each looks clean and is not:

* a Sonar block the resolve cannot read must fail closed, never drain as "this
  project does not use Sonar";
* an ``undecidable`` read must block the merge. It is the state that reads like
  zero, and the lane's merge text binds the merge to the gate's verdict rather
  than to a reader's judgement.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from test_runbook_lane import (
    _PYPROJECT_EXEC,
    _run_resolve,
    _section,
    _seed_fixture,
    _skill_text,
)

from conftest import get_scripts_dir, load_script_module, parse_ns, run_script

lane = load_script_module('plan-marshall', 'runbook-lane', 'runbook_lane.py', 'runbook_lane_sonar_mod')

cmd_sonar_gate = lane.cmd_sonar_gate

_PROJECT_KEY = 'com.example:proj'
_SONAR_BLOCK = {'workflow-integration-sonar': {'organization': 'example', 'project_key': _PROJECT_KEY}}

_SCRIPT = get_scripts_dir('plan-marshall', 'runbook-lane') / 'runbook_lane.py'


# =============================================================================
# resolve — the Sonar state
# =============================================================================
def test_resolve_reports_configured_with_the_project_key(tmp_path: Path) -> None:
    spec = _seed_fixture(
        tmp_path,
        executable=_PYPROJECT_EXEC,
        required_bots='x',
        credentials_config=_SONAR_BLOCK,
    )

    data = _run_resolve(spec, tmp_path)

    assert data['sonar'] == 'configured'
    assert data['sonar_project_key'] == _PROJECT_KEY


def test_resolve_reports_not_configured_without_a_sonar_block(tmp_path: Path) -> None:
    spec = _seed_fixture(tmp_path, executable=_PYPROJECT_EXEC, required_bots='x')

    data = _run_resolve(spec, tmp_path)

    assert data['sonar'] == 'not_configured'
    assert 'sonar_project_key' not in data


def test_resolve_reports_not_configured_for_a_block_without_a_project_key(tmp_path: Path) -> None:
    """An organization alone names no analysable project, so there is nothing to read."""
    spec = _seed_fixture(
        tmp_path,
        executable=_PYPROJECT_EXEC,
        required_bots='x',
        credentials_config={'workflow-integration-sonar': {'organization': 'example'}},
    )

    data = _run_resolve(spec, tmp_path)

    assert data['sonar'] == 'not_configured'
    assert 'sonar_project_key' not in data


@pytest.mark.parametrize('block', ['not-an-object', ['not', 'an', 'object']])
def test_resolve_fails_closed_on_an_unreadable_sonar_block(tmp_path: Path, block) -> None:
    spec = _seed_fixture(
        tmp_path,
        executable=_PYPROJECT_EXEC,
        required_bots='x',
        credentials_config={'workflow-integration-sonar': block},
    )

    data = _run_resolve(spec, tmp_path)

    assert data['status'] == 'error'
    assert data['error'] == 'sonar_config_unreadable'


# =============================================================================
# the gate — an undecidable read never reaches the merge
# =============================================================================
def _gate_args(state: str = 'configured', count_status: str | None = 'confirmed', **flags: str) -> object:
    """Build the namespace through the verb's own parser."""
    argv = ['sonar-gate', '--state', state]
    if count_status is not None:
        argv += ['--count-status', count_status]
    for name, value in flags.items():
        argv += [f'--{name.replace("_", "-")}', value]
    return parse_ns('plan-marshall', 'runbook-lane', 'runbook_lane.py', *argv)


def test_an_undecidable_read_does_not_admit_the_merge() -> None:
    verdict = cmd_sonar_gate(_gate_args(count_status='undecidable'))

    assert verdict['merge_allowed'] is False
    assert verdict['reason'] == 'undecidable_read'
    assert verdict['open_issue_count'] is None


def test_an_unconfigured_read_does_not_admit_the_merge() -> None:
    """resolve said the project uses Sonar, so a read that cannot authenticate blocks."""
    verdict = cmd_sonar_gate(_gate_args(count_status='unconfigured'))

    assert verdict['merge_allowed'] is False
    assert verdict['reason'] == 'unconfigured_read'


def test_a_project_without_sonar_admits_the_merge() -> None:
    verdict = cmd_sonar_gate(_gate_args(state='not_configured', count_status=None))

    assert verdict['merge_allowed'] is True
    assert verdict['reason'] == 'not_configured'


def test_a_confirmed_zero_admits_the_merge() -> None:
    verdict = cmd_sonar_gate(_gate_args(open_count='0'))

    assert verdict['merge_allowed'] is True
    assert verdict['reason'] == 'no_open_issues'


def test_every_open_issue_dismissed_with_a_reason_admits_the_merge() -> None:
    verdict = cmd_sonar_gate(_gate_args(open_count='2', open_keys='K1,K2', dismissed_keys='K1,K2'))

    assert verdict['merge_allowed'] is True
    assert verdict['reason'] == 'all_open_issues_dismissed'


def test_an_open_issue_without_a_dismissal_blocks_the_merge() -> None:
    verdict = cmd_sonar_gate(_gate_args(open_count='2', open_keys='K1,K2', dismissed_keys='K1'))

    assert verdict['merge_allowed'] is False
    assert verdict['reason'] == 'open_issues_undismissed'
    assert verdict['undismissed_keys'] == ['K2']


def test_a_count_with_no_enumerated_keys_cannot_be_verified() -> None:
    """A count alone is not a per-issue disposition, so it is refused rather than passed."""
    verdict = cmd_sonar_gate(_gate_args(open_count='3'))

    assert verdict['merge_allowed'] is False
    assert verdict['reason'] == 'open_issue_keys_missing'


def test_a_confirmed_read_without_a_count_blocks_the_merge() -> None:
    verdict = cmd_sonar_gate(_gate_args())

    assert verdict['merge_allowed'] is False
    assert verdict['reason'] == 'confirmed_read_without_count'


def test_the_gate_rejects_a_state_outside_the_closed_set() -> None:
    verdict = cmd_sonar_gate(_gate_args(state='maybe'))

    assert verdict['status'] == 'error'
    assert verdict['error'] == 'invalid_sonar_state'


def test_the_gate_rejects_a_missing_count_status_for_a_configured_project() -> None:
    verdict = cmd_sonar_gate(_gate_args(count_status=None))

    assert verdict['status'] == 'error'
    assert verdict['error'] == 'invalid_count_status'


def test_the_gate_verb_is_reachable_through_its_cli_surface() -> None:
    result = run_script(_SCRIPT, 'sonar-gate', '--state', 'configured', '--count-status', 'undecidable')

    assert result.success, result.stderr
    assert result.toon()['merge_allowed'] is False


# =============================================================================
# the lane text binds § 6's read to § 7's condition
# =============================================================================
def test_the_read_step_names_the_provider_read_and_the_gate() -> None:
    section = _section('## 6. Pull request and reviews')

    assert 'read_open_issues' in section, '§ 6 must name the plan-less provider read'
    assert 'sonar-gate' in section, '§ 6 must bind the read to the gate verdict'


def test_the_merge_condition_binds_the_merge_to_the_gate_verdict() -> None:
    section = _section('## 7. Merge gate')

    assert 'sonar-gate' in section, '§ 7 must carry the Sonar merge condition'
    assert 'merge_allowed' in section, '§ 7 must name the verdict it merges on'
    assert 'undecidable' in section, '§ 7 must state that an undecidable read blocks'


def test_the_lane_text_states_the_not_configured_skip() -> None:
    assert 'not_configured' in _skill_text()
