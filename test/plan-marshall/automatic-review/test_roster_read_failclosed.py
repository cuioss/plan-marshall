#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""An unreadable review-bot roster is an ERROR, never an empty roster (D1).

``required_bots`` / ``optional_bots`` were prose reads: the step ran
``manage-execution-manifest step-params get`` and then treated both lists as
"default EMPTY". That collapses two different answers into one. A roster that was READ
and configures nobody is a decided, vacuously-satisfied quorum. A roster that could not
be read (``execution.toon not found``, no such step, an unparseable payload) says
nothing at all — and rendering it as empty turns "nobody could observe the
configuration" into "nobody is required", so every required-bot gate downstream passes
on a roster that was never read.

``review_completeness roster`` is the fail-closed read both consumers use. Its contract
is pinned here in both directions, together with the prose that obliges the two
consumers to stop on its error:

* an unreadable read is ``status: error`` / ``error: roster_unreadable`` /
  ``roster_read: false`` with NO bot list at all — an absent list must not be
  readable as an empty one;
* a READ roster is ``roster_read: true`` with both lists, empty when nobody is
  configured;
* the ``automatic-review`` step and the pre-merge barrier both route the error to a
  hard stop rather than forwarding empty lists.
"""

from __future__ import annotations

import re

import pytest

from conftest import get_skill_dir, load_script_module

rc = load_script_module('plan-marshall', 'automatic-review', 'review_completeness.py', register=False)

_AR_SKILL = get_skill_dir('plan-marshall', 'automatic-review') / 'SKILL.md'
_BRANCH_CLEANUP = get_skill_dir('plan-marshall', 'phase-6-finalize') / 'standards' / 'branch-cleanup.md'

#: The markers a consumer's roster read must carry to be fail-closed. The verb name is
#: what routes the read; ``roster_unreadable`` is the error it must route; and the
#: sentence states what the error MEANS, so a reader cannot mistake it for a warning.
_FAIL_CLOSED_MARKERS = (
    'review_completeness roster',
    'roster_unreadable',
    'never an empty roster',
)


def _unreadable_runner(plan_id: str) -> dict:
    del plan_id
    return {'status': 'error', 'error': 'file_not_found', 'detail': 'execution.toon not found'}


def _readable_runner(required: str = '', optional: str = ''):
    def runner(plan_id: str) -> dict:
        del plan_id
        return {'status': 'success', 'params': {'required_bots': required, 'optional_bots': optional}}

    return runner


class TestTheReadDistinguishesUnreadableFromEmpty:
    def test_an_unreadable_read_is_an_error_carrying_no_bot_list(self):
        payload = rc.read_roster('any-plan', runner=_unreadable_runner)

        assert payload['status'] == 'error'
        assert payload['error'] == 'roster_unreadable'
        assert payload['roster_read'] is False
        # ⛔ The load-bearing assertion: an absent list must not be readable as empty.
        assert 'required_bots' not in payload
        assert 'optional_bots' not in payload
        assert 'roster' in payload['reason']

    def test_a_readable_empty_roster_is_a_success_with_empty_lists(self):
        payload = rc.read_roster('any-plan', runner=_readable_runner())

        assert payload == {
            'status': 'success',
            'roster_read': True,
            'required_bots': [],
            'optional_bots': [],
        }

    def test_the_two_records_are_distinguishable_on_the_read_flag(self):
        """The distinction the callers route on, asserted directly."""
        unreadable = rc.read_roster('any-plan', runner=_unreadable_runner)
        empty = rc.read_roster('any-plan', runner=_readable_runner())

        assert unreadable['roster_read'] is not empty['roster_read']
        assert unreadable['status'] != empty['status']

    def test_a_readable_roster_is_parsed_into_bare_kinds(self):
        payload = rc.read_roster('any-plan', runner=_readable_runner('coderabbit, cuioss-review-bot', 'sourcery'))

        assert payload['required_bots'] == ['coderabbit', 'cuioss-review-bot']
        assert payload['optional_bots'] == ['sourcery']

    def test_a_params_object_that_is_not_a_mapping_is_unreadable(self):
        """A step that answered without a param object is a failed read, not an empty one."""
        payload = rc.read_roster('any-plan', runner=lambda _plan: {'status': 'success', 'params': None})

        assert payload['status'] == 'error'
        assert payload['error'] == 'roster_unreadable'
        assert 'required_bots' not in payload

    def test_a_list_shaped_roster_override_is_read(self):
        """A per-plan override may carry a real list; that is a roster, not a parse failure."""
        payload = rc.read_roster(
            'any-plan',
            runner=lambda _plan: {
                'status': 'success',
                'params': {'required_bots': ['coderabbit', 'cuioss-review-bot'], 'optional_bots': ['sourcery']},
            },
        )

        assert payload['status'] == 'success'
        assert payload['required_bots'] == ['coderabbit', 'cuioss-review-bot']
        assert payload['optional_bots'] == ['sourcery']

    def test_a_non_zero_exit_is_an_error_even_when_its_stdout_parses(self):
        """⛔ A failed call whose output happens to be TOON is still a failed read.

        Parsing first would let a manifest call that reported failure change the
        required-reviewer quorum — the one thing a roster read must never do.
        """
        from types import SimpleNamespace

        completed = SimpleNamespace(
            returncode=1,
            stdout='status: success\nparams:\n  required_bots: coderabbit\n',
            stderr='boom',
        )

        result = rc._manifest_result(completed)

        assert result['status'] == 'error'
        assert result['error'] == 'roster_unreadable'
        assert 'exited with code 1' in result['detail']

    def test_a_zero_exit_with_a_parseable_payload_is_read(self):
        """Matched positive control: the same helper accepts a successful call."""
        from types import SimpleNamespace

        completed = SimpleNamespace(
            returncode=0,
            stdout='status: success\nparams:\n  required_bots: coderabbit\n',
            stderr='',
        )

        result = rc._manifest_result(completed)

        assert result['status'] == 'success'
        assert result['params']['required_bots'] == 'coderabbit'

    def test_a_roster_that_cannot_be_parsed_is_unreadable(self):
        """A malformed token must not escape as a traceback, nor as a partly-read roster."""
        payload = rc.read_roster('any-plan', runner=_readable_runner('coderabbit:sourcery', ''))

        assert payload['status'] == 'error'
        assert payload['error'] == 'roster_unreadable'
        assert 'required_bots' not in payload
        assert 'could not be parsed' in payload['reason']


class TestTheCommandLineFailsClosed:
    def test_the_verb_is_registered(self, capsys):
        """The subcommand is on the REAL parser, read off its own help output."""
        with pytest.raises(SystemExit) as exit_info:
            rc.main(['--help'])

        assert exit_info.value.code == 0
        assert 'roster' in capsys.readouterr().out

    def test_the_command_returns_non_zero_on_an_unreadable_roster(self, monkeypatch, capsys):
        original = rc.read_roster
        monkeypatch.setattr(rc, 'read_roster', lambda plan_id: original(plan_id, runner=_unreadable_runner))

        exit_code = rc.main(['roster', '--plan-id', 'any-plan'])

        assert exit_code == 1
        emitted = capsys.readouterr().out
        assert 'roster_unreadable' in emitted
        assert 'roster_read: false' in emitted
        assert 'required_bots' not in emitted

    def test_the_command_returns_zero_and_prints_both_lists_on_a_read_roster(self, monkeypatch, capsys):
        original = rc.read_roster
        monkeypatch.setattr(
            rc,
            'read_roster',
            lambda plan_id: original(plan_id, runner=_readable_runner('coderabbit', '')),
        )

        exit_code = rc.main(['roster', '--plan-id', 'any-plan'])

        assert exit_code == 0
        emitted = capsys.readouterr().out
        assert 'roster_read: true' in emitted
        assert 'coderabbit' in emitted
        # The empty optional list is rendered, so "configured nobody" is a recorded
        # answer rather than an absent line.
        assert 'optional_bots' in emitted


class TestBothConsumersAreObligedToStop:
    def test_the_fail_closed_rule_rejects_the_old_default_EMPTY_prose(self):
        """⛔ Negative control: the rule must be able to FAIL on the shipped defect.

        The pre-fix prose is reproduced verbatim enough to carry its markers
        (``step-params get`` plus "both default EMPTY") and none of the fail-closed
        ones, so a rule that accepts it is not a rule.
        """
        old = (
            'Read `required_bots` and `optional_bots` off the same execution-manifest '
            'step-params snapshot (`manage-execution-manifest step-params get --plan-id '
            '{plan_id} --phase 6-finalize --step-id plan-marshall:automatic-review`; both '
            'default EMPTY) and forward them.\n'
        )

        with pytest.raises(AssertionError):
            _assert_fail_closed(old, 'old-automatic-review')

    @pytest.mark.parametrize(
        ('document', 'minimum_sites'),
        [
            (_AR_SKILL, 3),  # FIND, the participation guard, and trigger B
            (_BRANCH_CLEANUP, 1),  # the pre-merge barrier's own roster read
        ],
        ids=['automatic-review', 'branch-cleanup'],
    )
    def test_the_consumer_document_is_fail_closed(self, document, minimum_sites):
        _assert_fail_closed(document.read_text(encoding='utf-8'), document.name, minimum_sites)

    def test_neither_document_still_forwards_both_lists_as_defaulting_to_empty(self):
        """The exact sentence the fix replaces is gone from both sites, per site."""
        skill = _AR_SKILL.read_text(encoding='utf-8')
        barrier = _BRANCH_CLEANUP.read_text(encoding='utf-8')

        assert not re.search(r'Both default EMPTY', barrier), (
            'the barrier still tells its roster read that both lists default EMPTY'
        )
        roster_sentences = [line for line in skill.splitlines() if 'required_bots' in line and 'default EMPTY' in line]
        assert not roster_sentences, f'the SKILL still defaults a roster read to EMPTY: {roster_sentences}'


def _assert_fail_closed(text: str, name: str, minimum_sites: int = 1) -> None:
    """THE rule — one definition, called by the guard and its control.

    A document is fail-closed when it names the fail-closed verb, names the error it
    returns, and states what the error means ("never an empty roster"), at least
    ``minimum_sites`` times. Living in a function rather than inline is what lets the
    negative control execute the guard's own assertions against a planted document.
    """
    missing = [marker for marker in _FAIL_CLOSED_MARKERS if marker not in text]
    assert not missing, f'{name} is not fail-closed on an unreadable roster: missing {missing}'
    sites = text.count('review_completeness roster')
    assert sites >= minimum_sites, (
        f'{name} carries {sites} fail-closed roster read(s), expected at least {minimum_sites}'
    )
