#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the landing's Sonar fact — the measured figure, not the gate's word.

A lane run that reported "quality gate passed" while the pull request's own open
issues stayed open could not be checked, because its landing carried no figure.
The landing now carries the open-finding count measured at the merge head as the
REQUIRED ``sonar_open_new_issues`` key, with the rules it left open on the
OPTIONAL per-step channel beside it, and with two sentinels that are not the same
claim: ``unknown`` for a read that failed (never ``0``) — which leaves the
landing INCOMPLETE, because the number is required — and ``n/a`` for a project
that does not analyse with Sonar, the answered absence.

The required key set is pinned here as an exact tuple, so a key added to or
removed from the schema turns this red.
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

_COUNT_FACT = 'sonar_open_new_issues'
_RULES_FACT = 'step.sonar-roundtrip.open_issue_rules'


def _facts_args(state: str = 'configured', count_status: str | None = 'confirmed', **flags: str):
    argv = ['sonar-facts', '--state', state]
    if count_status is not None:
        argv += ['--count-status', count_status]
    for name, value in flags.items():
        argv += [f'--{name.replace("_", "-")}', value]
    return parse_ns('plan-marshall', 'runbook-lane', 'runbook_lane.py', *argv)


def _landing(fact_lines: list[str]) -> str:
    """A landing in the shape section 8 prescribes, carrying the given extra fact lines.

    The four review-and-Sonar numbers are REQUIRED, so the base block carries an
    all-zero/``n/a`` sample and the Sonar lines a caller passes override it — one
    block, no duplicate key for the parser to choose between.
    """
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
        'unresolved_review_threads=0',
        'review_body_findings_total=0',
        'review_body_findings_handled=0',
        'sonar_open_new_issues=n/a',
    ]
    merged = dict(line.split('=', 1) for line in required)
    merged.update(dict(line.split('=', 1) for line in fact_lines))
    body = '\n'.join(f'{key}={value}' for key, value in merged.items())
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


def test_a_project_without_sonar_carries_the_answered_absence(tmp_path) -> None:
    """The not_configured state reaches the facts through the resolve result."""
    spec = _seed_fixture(tmp_path, executable=_PYPROJECT_EXEC, required_bots='x')
    resolved = _run_resolve(spec, tmp_path)

    facts = cmd_sonar_facts(_facts_args(state=resolved['sonar'], count_status=None))

    assert resolved['sonar'] == 'not_configured'
    assert facts['open_issue_count'] == 'n/a'
    assert facts['open_issue_rules'] == 'n/a'


def test_a_non_zero_count_without_rules_is_refused() -> None:
    """`none` means a measured zero, so a non-zero count must carry its rules."""
    verdict = cmd_sonar_facts(_facts_args(open_count='3'))

    assert verdict['status'] == 'error'
    assert verdict['error'] == 'confirmed_read_without_rules'


def test_a_measured_zero_with_rules_is_refused() -> None:
    """The mirror guard: a zero leaves no rule open, so a rule beside it is another read."""
    verdict = cmd_sonar_facts(_facts_args(open_count='0', rules='java:S1'))

    assert verdict['status'] == 'error'
    assert verdict['error'] == 'confirmed_zero_with_rules'


def test_a_not_configured_state_refuses_a_read_supplied_beside_it() -> None:
    verdict = cmd_sonar_facts(_facts_args(state='not_configured', count_status=None, rules='java:S1'))

    assert verdict['status'] == 'error'
    assert verdict['error'] == 'state_contradicts_read'


def test_a_landing_carrying_the_confirmed_fact_is_complete() -> None:
    facts = cmd_sonar_facts(_facts_args(open_count='3', rules='java:S1234'))

    assert check_landing_completeness(_landing(list(facts['fact_lines']))) == (True, [])


def test_a_landing_whose_sonar_read_failed_is_incomplete() -> None:
    """`sonar_open_new_issues` is REQUIRED: `unknown` is a failed read, never `0`."""
    facts = cmd_sonar_facts(_facts_args(count_status='undecidable'))

    complete, missing = check_landing_completeness(_landing(list(facts['fact_lines'])))

    assert facts['fact_lines'][0] == f'{_COUNT_FACT}=unknown'
    assert complete is False
    assert missing == [_COUNT_FACT]


def test_a_project_without_sonar_still_drains_complete() -> None:
    """`n/a` at the required count is the answered absence, not a gap."""
    facts = cmd_sonar_facts(_facts_args(state='not_configured', count_status=None))

    assert check_landing_completeness(_landing(list(facts['fact_lines']))) == (True, [])


def test_the_required_landing_key_set_names_the_review_and_sonar_numbers() -> None:
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
        'unresolved_review_threads',
        'review_body_findings_total',
        'review_body_findings_handled',
        'sonar_open_new_issues',
    )


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
