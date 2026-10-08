#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the rule-keyed Q-Gate resolver and its ``qgate resolve-by-rule`` verb.

Subject: ``_findings_core.resolve_qgate_findings_by_rule`` and the CLI verb
``manage-findings.py`` registers over it.

The property under test is a SELECTION, so every positive is paired with the
control it must not swallow: the resolver reaches every pending finding carrying
the named rule key, and reaches nothing else — not a finding with another rule,
not a finding with no rule, and not a finding filed after the call returned.

The fixture shape mirrors the producer the resolver exists for: one finding per
non-closing self-review state, all filed under one fixed rule key and none
naming a file, beside one ordinary structural finding that carries no rule.
"""

from __future__ import annotations

import sys
from typing import Any

import pytest
from _findings_store_fixtures import (
    _findings_core,
    add_qgate_finding,
    query_qgate_findings,
    resolve_qgate_finding,
)
from toon_parser import parse_toon

from conftest import load_script_module

resolve_qgate_findings_by_rule = _findings_core.resolve_qgate_findings_by_rule

# Plan ids this module's tests file findings against — seeded by the autouse
# ``_materialize_declared_plan_dirs`` fixture in ``test/conftest.py``.
PLAN_IDS = (
    'rule-resolve-all-states',
    'rule-resolve-ordinary-survives',
    'rule-resolve-other-rule',
    'rule-resolve-already-resolved',
    'rule-resolve-filed-after',
    'rule-resolve-refiled-after',
    'rule-resolve-record',
    'rule-resolve-empty',
    'rule-resolve-other-phase',
    'rule-resolve-bad-args',
    'rule-resolve-cli',
    'rule-resolve-cli-required',
)

#: A plan id deliberately ABSENT from ``PLAN_IDS`` — nothing seeds its directory.
_ABSENT_PLAN_ID = 'rule-resolve-plan-absent'

_PHASE = '6-finalize'
_RULE = 'pre-submission-self-review-state'
_STATES = ('verdict_refused', 'further_round_owed', 'verifier_unavailable')
_STORE_STATE_KEYS = frozenset({'store_resolution', 'store_path', 'findings_store_state', 'unresolved_store'})

# Distinct sys.modules name so this in-process load never clobbers the module a
# sibling test file registers.
_cli = load_script_module('plan-marshall', 'manage-findings', 'manage-findings.py', 'manage_findings_resolve_by_rule')


def _file_state_findings(plan_id: str) -> dict[str, str]:
    """File one finding per self-review state under the rule key.

    Returns ``{state: hash_id}``. No finding names a file — that absence is what
    puts these findings out of the evidence resolver's reach.
    """
    hashes: dict[str, str] = {}
    for state in _STATES:
        result = add_qgate_finding(
            plan_id,
            _PHASE,
            'qgate',
            'bug',
            f'{state} at pre-submission-self-review',
            f'rationale for {state}',
            severity='warning',
            rule=_RULE,
        )
        assert result['status'] == 'success', result
        hashes[state] = result['hash_id']
    return hashes


def _file_ordinary_finding(plan_id: str) -> str:
    """File one structural finding that carries NO rule; return its hash."""
    result = add_qgate_finding(
        plan_id,
        _PHASE,
        'qgate',
        'bug',
        'duplicate_prose at doc/a.md:12',
        'Two sections state one contract',
        file_path='doc/a.md',
        severity='warning',
    )
    assert result['status'] == 'success', result
    return str(result['hash_id'])


def _pending_hashes(plan_id: str, phase: str = _PHASE) -> set[str]:
    """Return the hash ids the store reports as pending for ``phase``."""
    return {f['hash_id'] for f in query_qgate_findings(plan_id, phase, resolution='pending')['findings']}


def _resolve(plan_id: str) -> dict[str, Any]:
    """Resolve the rule key on ``plan_id`` the way the closing round does."""
    result: dict[str, Any] = resolve_qgate_findings_by_rule(
        plan_id, _PHASE, _RULE, 'taken_into_account', 'self-review closed at abc123'
    )
    return result


# =============================================================================
# Test: the selection
# =============================================================================


def test_resolving_by_rule_leaves_no_state_finding_pending(plan_context):
    plan_id = 'rule-resolve-all-states'
    state_hashes = _file_state_findings(plan_id)

    result = _resolve(plan_id)

    assert result['status'] == 'success'
    assert {entry['hash_id'] for entry in result['resolved']} == set(state_hashes.values())
    assert _pending_hashes(plan_id) & set(state_hashes.values()) == set()


def test_resolving_by_rule_leaves_the_ordinary_finding_pending(plan_context):
    """Matched control: the finding carrying no rule is reported and untouched."""
    plan_id = 'rule-resolve-ordinary-survives'
    _file_state_findings(plan_id)
    ordinary_hash = _file_ordinary_finding(plan_id)

    result = _resolve(plan_id)

    assert _pending_hashes(plan_id) == {ordinary_hash}
    assert result['untouched'] == [{'hash_id': ordinary_hash, 'rule': ''}]
    assert len(result['resolved']) == len(_STATES)


def test_a_finding_carrying_a_different_rule_is_left_untouched(plan_context):
    plan_id = 'rule-resolve-other-rule'
    _file_state_findings(plan_id)
    other = add_qgate_finding(plan_id, _PHASE, 'qgate', 'bug', 'Other rule', 'Detail', rule='some-other-rule')

    result = _resolve(plan_id)

    assert other['hash_id'] in _pending_hashes(plan_id)
    assert {'hash_id': other['hash_id'], 'rule': 'some-other-rule'} in result['untouched']
    assert other['hash_id'] not in {entry['hash_id'] for entry in result['resolved']}


def test_an_already_resolved_finding_is_neither_rewritten_nor_reported(plan_context):
    """Only PENDING findings are considered — a prior resolution is not overwritten."""
    plan_id = 'rule-resolve-already-resolved'
    state_hashes = _file_state_findings(plan_id)
    resolved_earlier = state_hashes['verdict_refused']
    resolve_qgate_finding(plan_id, _PHASE, resolved_earlier, 'accepted', detail='decided earlier')

    result = _resolve(plan_id)

    reported = {entry['hash_id'] for entry in result['resolved'] + result['untouched']}
    assert resolved_earlier not in reported
    record = next(f for f in query_qgate_findings(plan_id, _PHASE)['findings'] if f['hash_id'] == resolved_earlier)
    assert record['resolution'] == 'accepted'
    assert record['resolution_detail'] == 'decided earlier'


def test_a_state_finding_filed_after_the_resolution_stays_pending(plan_context):
    """The call resolves what was pending when it ran, not what is filed later."""
    plan_id = 'rule-resolve-filed-after'
    _file_state_findings(plan_id)
    _resolve(plan_id)

    later = add_qgate_finding(
        plan_id,
        _PHASE,
        'qgate',
        'bug',
        'further_round_owed at pre-submission-self-review',
        'a later round was refused for a new reason',
        rule=_RULE,
    )

    assert later['status'] == 'success'
    assert _pending_hashes(plan_id) == {later['hash_id']}


def test_a_state_finding_refiled_identically_after_the_resolution_is_reopened(plan_context):
    """An identical re-detection reopens the resolved record rather than vanishing."""
    plan_id = 'rule-resolve-refiled-after'
    state_hashes = _file_state_findings(plan_id)
    _resolve(plan_id)

    refiled = add_qgate_finding(
        plan_id,
        _PHASE,
        'qgate',
        'bug',
        'verdict_refused at pre-submission-self-review',
        'rationale for verdict_refused',
        severity='warning',
        rule=_RULE,
    )

    assert refiled['status'] == 'reopened'
    assert refiled['hash_id'] == state_hashes['verdict_refused']
    assert _pending_hashes(plan_id) == {state_hashes['verdict_refused']}


def test_the_resolution_and_detail_are_written_to_each_matched_record(plan_context):
    plan_id = 'rule-resolve-record'
    state_hashes = _file_state_findings(plan_id)

    _resolve(plan_id)

    records = {f['hash_id']: f for f in query_qgate_findings(plan_id, _PHASE)['findings']}
    for hash_id in state_hashes.values():
        assert records[hash_id]['resolution'] == 'taken_into_account'
        assert records[hash_id]['resolution_detail'] == 'self-review closed at abc123'
        assert records[hash_id]['resolution_timestamp']


def test_a_finding_in_another_phase_is_not_reached(plan_context):
    plan_id = 'rule-resolve-other-phase'
    other_phase = add_qgate_finding(plan_id, '5-execute', 'qgate', 'bug', 'Other phase', 'Detail', rule=_RULE)

    result = _resolve(plan_id)

    assert result['resolved'] == []
    assert _pending_hashes(plan_id, '5-execute') == {other_phase['hash_id']}


# =============================================================================
# Test: the return shape and the store-state contract
# =============================================================================


def test_the_return_echoes_the_selector_and_carries_the_store_state_fields(plan_context):
    plan_id = 'rule-resolve-all-states'
    _file_state_findings(plan_id)

    result = _resolve(plan_id)

    assert result['plan_id'] == plan_id
    assert result['phase'] == _PHASE
    assert result['rule'] == _RULE
    assert result['resolution'] == 'taken_into_account'
    assert _STORE_STATE_KEYS <= set(result)
    assert result['findings_store_state'] == 'present'
    assert all(entry == {'hash_id': entry['hash_id'], 'rule': _RULE} for entry in result['resolved'])


def test_a_plan_that_filed_nothing_is_a_genuine_empty_success(plan_context):
    """Matched control for the refusal below: a reached-but-empty store succeeds."""
    result = _resolve('rule-resolve-empty')

    assert result['status'] == 'success'
    assert result['resolved'] == []
    assert result['untouched'] == []
    assert result['findings_store_state'] == 'missing'
    assert result['unresolved_store'] is False


def test_an_absent_plan_directory_is_refused_rather_than_reported_as_zero_resolved(plan_context):
    assert not (plan_context.plans_dir / _ABSENT_PLAN_ID).exists(), 'fixture must not seed this plan'

    result = _resolve(_ABSENT_PLAN_ID)

    assert result['status'] == 'error'
    assert result['error'] == 'findings_store_unresolved'
    assert result['findings_store_state'] == 'plan_absent'
    assert result['unresolved_store'] is True
    assert 'resolved' not in result
    assert 'untouched' not in result
    assert not (plan_context.plans_dir / _ABSENT_PLAN_ID).exists(), 'the refusal manufactured the plan directory'


# =============================================================================
# Test: argument validation
# =============================================================================


@pytest.mark.parametrize('blank_rule', ['', '   '])
def test_a_blank_rule_is_refused_and_resolves_nothing(plan_context, blank_rule):
    plan_id = 'rule-resolve-bad-args'
    ordinary_hash = _file_ordinary_finding(plan_id)

    result = resolve_qgate_findings_by_rule(plan_id, _PHASE, blank_rule, 'fixed', 'Detail')

    assert result['status'] == 'error'
    assert 'rule' in result['message']
    assert _pending_hashes(plan_id) == {ordinary_hash}


def test_an_invalid_resolution_is_refused(plan_context):
    result = resolve_qgate_findings_by_rule('rule-resolve-bad-args', _PHASE, _RULE, 'not-a-resolution', 'Detail')

    assert result['status'] == 'error'
    assert 'Invalid resolution' in result['message']


def test_an_invalid_phase_is_refused(plan_context):
    result = resolve_qgate_findings_by_rule('rule-resolve-bad-args', '1-init', _RULE, 'fixed', 'Detail')

    assert result['status'] == 'error'
    assert 'Invalid Q-Gate phase' in result['message']


# =============================================================================
# Test: the CLI verb
# =============================================================================


def _run_main(monkeypatch, capsys, argv):
    """Drive ``main()`` with a patched argv and return ``(exit_code, stdout)``."""
    monkeypatch.setattr(sys, 'argv', ['manage-findings', *argv])
    with pytest.raises(SystemExit) as exc:
        _cli.main()
    code = exc.value.code if exc.value.code is not None else 0
    return code, capsys.readouterr().out


def test_the_cli_verb_resolves_the_state_findings_and_reports_both_lists(plan_context, monkeypatch, capsys):
    plan_id = 'rule-resolve-cli'
    state_hashes = _file_state_findings(plan_id)
    ordinary_hash = _file_ordinary_finding(plan_id)

    code, out = _run_main(
        monkeypatch,
        capsys,
        [
            'qgate',
            'resolve-by-rule',
            '--plan-id',
            plan_id,
            '--phase',
            _PHASE,
            '--rule',
            _RULE,
            '--resolution',
            'taken_into_account',
            '--detail',
            'self-review closed at abc123',
        ],
    )

    payload = parse_toon(out)
    assert code == 0
    assert payload['status'] == 'success'
    assert payload['rule'] == _RULE
    # Cardinality is read off the emitted payload; identity is read off the store.
    # A six-hex-char hash id that happens to be all digits does not survive a
    # TOON round trip as a string, so comparing ids through the payload would
    # make this test depend on which ids the run happened to generate.
    assert len(payload['resolved']) == len(state_hashes)
    assert len(payload['untouched']) == 1
    assert _pending_hashes(plan_id) == {ordinary_hash}


@pytest.mark.parametrize('omitted', ['--rule', '--resolution', '--detail'])
def test_the_cli_verb_requires_rule_resolution_and_detail(plan_context, monkeypatch, capsys, omitted):
    plan_id = 'rule-resolve-cli-required'
    state_hashes = _file_state_findings(plan_id)
    flags = {
        '--rule': _RULE,
        '--resolution': 'taken_into_account',
        '--detail': 'self-review closed at abc123',
    }
    argv = ['qgate', 'resolve-by-rule', '--plan-id', plan_id, '--phase', _PHASE]
    for flag, value in flags.items():
        if flag != omitted:
            argv.extend([flag, value])

    code, _out = _run_main(monkeypatch, capsys, argv)

    assert code != 0
    assert _pending_hashes(plan_id) == set(state_hashes.values())
