#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the landing's optional Sonar fact — the measured figure, not the gate's word.

A lane run that reported "quality gate passed" while the pull request's own open
issues stayed open could not be checked, because its landing carried no figure.
The landing now carries the open-issue count measured at the merge head on the
optional per-step channel, with two sentinels that are not the same claim:
``unknown`` for a read that failed (never ``0``), and ``n/a`` for a project that
does not analyse with Sonar.

The required key set is pinned here as an exact tuple: the fact is OPTIONAL, so
adding it must leave every earlier landing complete.
"""

from __future__ import annotations

import pytest
from test_runbook_lane import _PYPROJECT_EXEC, _run_resolve, _seed_fixture

from conftest import get_scripts_dir, load_script_module, parse_ns, run_script

lane = load_script_module('plan-marshall', 'runbook-lane', 'runbook_lane.py', 'runbook_lane_facts_mod')

cmd_sonar_facts = lane.cmd_sonar_facts

_inbox = load_script_module('plan-marshall', 'plan-orchestrator', '_orchestrator_inbox.py', 'orchestrator_inbox_facts')

check_landing_completeness = _inbox.check_landing_completeness
LANDING_REQUIRED_KEYS = _inbox.LANDING_REQUIRED_KEYS

_SCRIPT = get_scripts_dir('plan-marshall', 'runbook-lane') / 'runbook_lane.py'

_COUNT_FACT = 'step.sonar-roundtrip.open_issue_count'
_RULES_FACT = 'step.sonar-roundtrip.open_issue_rules'


def _facts_args(state: str = 'configured', count_status: str | None = 'confirmed', **flags: str):
    argv = ['sonar-facts', '--state', state]
    if count_status is not None:
        argv += ['--count-status', count_status]
    for name, value in flags.items():
        argv += [f'--{name.replace("_", "-")}', value]
    return parse_ns('plan-marshall', 'runbook-lane', 'runbook_lane.py', *argv)


def _landing(fact_lines: list[str]) -> str:
    """A landing in the shape section 8 prescribes, carrying the given extra fact lines."""
    required = [
        'schema=landing-facts/1',
        'plan_id=rb-fixture',
        'epic=fixture-epic',
        'pr=#1',
        'merge_state=merged',
        'cleanup_owed=false',
        'deliverables_total=1',
        'deliverables_done=1',
        'total_tokens=512000',
        'harness=opencode',
        'model=deepseek-v4.1-flash/high',
        'effort=high',
        'plugin_version=0.1',
        'steps=setup:done,implement:done,build-gate:done,self-review:clear,pr:done,reviews:done,merge:done',
    ]
    body = '\n'.join(required + fact_lines)
    return f'```landing-facts\n{body}\n```\n\n## Residue\n\nnone\n'


def test_the_facts_follow_the_resolve_state_for_a_configured_project(tmp_path) -> None:
    """The lane's own chain: resolve says configured, and the landing renders that state."""
    spec = _seed_fixture(
        tmp_path,
        executable=_PYPROJECT_EXEC,
        required_bots='x',
        credentials_config={'workflow-integration-sonar': {'project_key': 'com.example:proj'}},
    )
    resolved = _run_resolve(spec, tmp_path)

    facts = cmd_sonar_facts(
        _facts_args(state=resolved['sonar'], count_status='confirmed', open_count='0'),
    )

    assert resolved['sonar'] == 'configured'
    assert facts['open_issue_count'] == '0'


def test_a_confirmed_count_carries_the_measured_figure() -> None:
    facts = cmd_sonar_facts(_facts_args(open_count='3', rules='java:S1234,java:S5678'))

    assert facts['open_issue_count'] == '3'
    assert facts['open_issue_rules'] == 'java:S1234,java:S5678'
    assert facts['fact_lines'] == [
        f'{_COUNT_FACT}=3',
        f'{_RULES_FACT}=java:S1234,java:S5678',
    ]


def test_a_confirmed_zero_carries_a_measured_zero() -> None:
    facts = cmd_sonar_facts(_facts_args(open_count='0'))

    assert facts['open_issue_count'] == '0'
    assert facts['open_issue_rules'] == 'none', 'no rule is left open, which is not the same as unknown'


def test_an_undecidable_read_carries_unknown_and_never_zero() -> None:
    facts = cmd_sonar_facts(_facts_args(count_status='undecidable'))

    assert facts['open_issue_count'] == 'unknown'
    assert facts['open_issue_count'] != '0'
    assert facts['open_issue_rules'] == 'unknown'


def test_an_unconfigured_read_carries_unknown_not_zero() -> None:
    """A read that could not authenticate is a failed read, same class as undecidable."""
    facts = cmd_sonar_facts(_facts_args(count_status='unconfigured'))

    assert facts['open_issue_count'] == 'unknown'
    assert facts['open_issue_rules'] == 'unknown'


def test_a_project_without_sonar_carries_the_answered_absence() -> None:
    facts = cmd_sonar_facts(_facts_args(state='not_configured', count_status=None))

    assert facts['open_issue_count'] == 'n/a'
    assert facts['open_issue_rules'] == 'n/a'


def test_a_landing_carrying_the_confirmed_fact_is_complete() -> None:
    facts = cmd_sonar_facts(_facts_args(open_count='3', rules='java:S1234'))

    assert check_landing_completeness(_landing(list(facts['fact_lines']))) == (True, [])


def test_a_landing_carrying_the_unknown_fact_is_complete() -> None:
    """The fact is optional, so an unknown Sonar figure never makes a landing incomplete."""
    facts = cmd_sonar_facts(_facts_args(count_status='undecidable'))

    assert check_landing_completeness(_landing(list(facts['fact_lines']))) == (True, [])


def test_the_required_landing_key_set_is_unchanged() -> None:
    assert LANDING_REQUIRED_KEYS == (
        'schema',
        'plan_id',
        'pr',
        'merge_state',
        'cleanup_owed',
        'deliverables_total',
        'deliverables_done',
        'total_tokens',
        'harness',
        'model',
        'effort',
        'plugin_version',
        'steps',
    )
    assert not any('sonar' in key for key in LANDING_REQUIRED_KEYS)


@pytest.mark.parametrize(
    ('kwargs', 'error'),
    [
        ({'state': 'maybe'}, 'invalid_sonar_state'),
        ({'count_status': None}, 'invalid_count_status'),
        ({}, 'confirmed_read_without_count'),
    ],
)
def test_the_verb_fails_closed_on_an_input_it_cannot_render(kwargs, error) -> None:
    verdict = cmd_sonar_facts(_facts_args(**kwargs))

    assert verdict['status'] == 'error'
    assert verdict['error'] == error


def test_the_verb_is_reachable_through_its_cli_surface() -> None:
    result = run_script(
        _SCRIPT,
        'sonar-facts',
        '--state',
        'configured',
        '--count-status',
        'confirmed',
        '--open-count',
        '4',
        '--rules',
        'java:S1',
    )

    assert result.success, result.stderr
    assert result.toon()['open_issue_count'] == '4'
