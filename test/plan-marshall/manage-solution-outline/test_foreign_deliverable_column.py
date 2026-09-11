#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001
"""Tests for the foreign-vs-host discriminator and the list-deliverables ``foreign`` column.

Covers:

* :func:`_plan_parsing.is_foreign_path` — the single lexical predicate that
  decides whether a declared path lands outside the project root (host relative,
  host absolute-under-root, foreign absolute, ``../`` escape, sibling-prefix
  trap, and the empty path);
* :func:`_plan_parsing.declares_change` — the single definition of whether a
  declared entry states a change (``read`` does not; every other intent, and a
  missing or unrecognised one, does);
* ``manage-solution-outline``'s ``_annotate_foreign`` — the per-entry ``foreign``
  flag (purely lexical, whatever the intent: the split that keeps a coverage
  ratio from pooling host and foreign paths) and the deliverable roll-up (this
  deliverable declares a foreign CHANGE — lexically foreign AND
  ``declares_change``), which is the same rule the pre-archive landing gate
  applies to its population.
"""

import pytest
from _plan_parsing import declares_change, is_foreign_path
from conftest import load_script_module

mso = load_script_module(
    'plan-marshall', 'manage-solution-outline', 'manage-solution-outline.py', 'manage_solution_outline'
)


# --------------------------------------------------------------------------- #
# is_foreign_path — the lexical outside-the-project-root predicate
# --------------------------------------------------------------------------- #

_ROOT = '/repo'


def test_relative_host_path_is_not_foreign():
    assert is_foreign_path('src/main/Foo.java', _ROOT) is False


def test_absolute_path_under_root_is_not_foreign():
    assert is_foreign_path('/repo/src/main/Foo.java', _ROOT) is False


def test_root_itself_is_not_foreign():
    assert is_foreign_path('/repo', _ROOT) is False


def test_absolute_path_outside_root_is_foreign():
    assert is_foreign_path('/other-repo/src/Foo.java', _ROOT) is True


def test_relative_escape_is_foreign():
    assert is_foreign_path('../other-repo/src/Foo.java', _ROOT) is True


def test_sibling_prefix_is_not_mistaken_for_host():
    # '/repo-other' shares the '/repo' string prefix but is NOT under '/repo';
    # a naive startswith would misclassify it as host. commonpath does not.
    assert is_foreign_path('/repo-other/src/Foo.java', _ROOT) is True


def test_empty_path_is_not_foreign():
    assert is_foreign_path('', _ROOT) is False
    assert is_foreign_path('   ', _ROOT) is False


# --------------------------------------------------------------------------- #
# declares_change — the single declares-a-change predicate
# --------------------------------------------------------------------------- #


def test_a_read_entry_declares_no_change():
    assert declares_change({'path': 'src/a.py', 'intent': 'read'}) is False


@pytest.mark.parametrize(
    'intent',
    ['write-new', 'write-replace', 'delete', None, 'not-an-intent'],
    ids=['write-new', 'write-replace', 'delete', 'no-marker', 'unrecognised-marker'],
)
def test_every_non_read_entry_declares_a_change(intent):
    """Only ``read`` is excluded — an unmarked or unrecognised intent counts as a change.

    The missing-marker and unrecognised-marker cases are the conservative
    direction: an entry that declared no valid intent must never be quieter than
    one that declared a write.
    """
    assert declares_change({'path': 'src/a.py', 'intent': intent}) is True


def test_an_entry_with_no_intent_key_declares_a_change():
    # Absent key, not just a None value: the predicate must not require the key.
    assert declares_change({'path': 'src/a.py'}) is True


# --------------------------------------------------------------------------- #
# _annotate_foreign — the list-deliverables foreign column
# --------------------------------------------------------------------------- #


def _deliverable(number, paths):
    return {
        'number': number,
        'title': f'D{number}',
        'affected_files': [{'path': p, 'intent': 'write-new'} for p in paths],
    }


def test_annotate_stamps_per_entry_and_rollup(monkeypatch):
    monkeypatch.setattr(mso, 'cwd_checkout_root', lambda: '/repo')
    deliverables = [
        _deliverable(1, ['src/Host.java']),  # host only
        _deliverable(2, ['/foreign/Other.java']),  # foreign only
        _deliverable(3, ['src/Host.java', '/foreign/Mixed.java']),  # mixed
    ]

    mso._annotate_foreign(deliverables)

    # Per-entry flags.
    assert deliverables[0]['affected_files'][0]['foreign'] is False
    assert deliverables[1]['affected_files'][0]['foreign'] is True
    assert deliverables[2]['affected_files'][0]['foreign'] is False
    assert deliverables[2]['affected_files'][1]['foreign'] is True

    # Deliverable-level roll-up: true iff ANY entry is foreign AND declares a
    # change (every entry here is `write-new`).
    assert deliverables[0]['foreign'] is False
    assert deliverables[1]['foreign'] is True
    assert deliverables[2]['foreign'] is True


def test_annotate_separates_the_two_populations(monkeypatch):
    # The whole point of the column: a coverage count can distinguish host paths
    # from foreign paths instead of pooling them.
    monkeypatch.setattr(mso, 'cwd_checkout_root', lambda: '/repo')
    deliverables = [_deliverable(1, ['src/a.py', 'src/b.py', '/elsewhere/c.py'])]

    mso._annotate_foreign(deliverables)

    entries = deliverables[0]['affected_files']
    host = [e for e in entries if not e['foreign']]
    foreign = [e for e in entries if e['foreign']]
    assert [e['path'] for e in host] == ['src/a.py', 'src/b.py']
    assert [e['path'] for e in foreign] == ['/elsewhere/c.py']


def test_annotate_fails_open_when_root_unresolvable(monkeypatch):
    # No git checkout ⇒ every path classified host (advisory column; the blocking
    # decision lives in the landing gate, which resolves the root explicitly).
    def boom():
        raise RuntimeError('not a git checkout')

    monkeypatch.setattr(mso, 'cwd_checkout_root', boom)
    deliverables = [_deliverable(1, ['/foreign/Other.java'])]

    mso._annotate_foreign(deliverables)

    assert deliverables[0]['affected_files'][0]['foreign'] is False
    assert deliverables[0]['foreign'] is False


def test_annotate_handles_deliverable_with_no_affected_files(monkeypatch):
    monkeypatch.setattr(mso, 'cwd_checkout_root', lambda: '/repo')
    deliverables = [{'number': 1, 'title': 'D1', 'affected_files': []}]
    mso._annotate_foreign(deliverables)
    assert deliverables[0]['foreign'] is False


def test_annotate_stamps_the_survey_scope_pair_not_only_affected_files(monkeypatch):
    """A survey-scope deliverable's foreign paths reach the landing gate.

    ``_annotate_foreign`` stamps the population the phase-6 pre-archive landing
    gate iterates. A deliverable that declares ``Files to survey:`` +
    ``Files expected to mutate:`` instead of a flat ``Affected files:`` list has
    a real write-set, and stamping only the flat field left that surface
    invisible to the gate — an incomplete derived set inside the check that
    guards landings.

    The roll-up is asserted through a deliverable whose ONLY foreign path is in
    the mutation scope, so a regression to the flat-field-only scan reaches the
    opposite verdict rather than a different count.
    """
    monkeypatch.setattr(mso, 'cwd_checkout_root', lambda: '/repo')
    deliverables = [
        {
            'number': 1,
            'title': 'Survey and classify',
            'affected_files': [],
            'survey_scope': [{'path': 'src/surveyed.py', 'intent': 'read'}],
            'mutation_scope': [{'path': '/foreign/Mutated.java', 'intent': None}],
        }
    ]

    mso._annotate_foreign(deliverables)

    assert deliverables[0]['mutation_scope'][0]['foreign'] is True
    assert deliverables[0]['survey_scope'][0]['foreign'] is False
    assert deliverables[0]['foreign'] is True


# --------------------------------------------------------------------------- #
# The roll-up means "declares a foreign CHANGE", not "names a foreign path"
# --------------------------------------------------------------------------- #


def test_a_read_only_foreign_entry_does_not_roll_up_but_keeps_its_own_flag(monkeypatch):
    """Consulting a foreign file is not a foreign change.

    The deliverable's only foreign entry is ``read``, so the roll-up is ``false``
    — while that entry's own flag stays ``true``, because the per-entry flag is
    the raw lexical host-vs-foreign split and must not be narrowed with it.
    """
    monkeypatch.setattr(mso, 'cwd_checkout_root', lambda: '/repo')
    deliverables = [
        {
            'number': 1,
            'title': 'D1',
            'affected_files': [
                {'path': 'src/Host.java', 'intent': 'write-replace'},
                {'path': '/foreign/Reference.java', 'intent': 'read'},
            ],
        }
    ]

    mso._annotate_foreign(deliverables)

    assert deliverables[0]['affected_files'][1]['foreign'] is True
    assert deliverables[0]['foreign'] is False


def test_a_foreign_write_entry_still_rolls_up_true(monkeypatch):
    """The positive control for the narrowing: a foreign write keeps the roll-up.

    The same deliverable shape as above plus one foreign write, so the only
    difference between a ``false`` and a ``true`` roll-up is the declared intent.
    """
    monkeypatch.setattr(mso, 'cwd_checkout_root', lambda: '/repo')
    deliverables = [
        {
            'number': 1,
            'title': 'D1',
            'affected_files': [
                {'path': '/foreign/Reference.java', 'intent': 'read'},
                {'path': '/foreign/Changed.java', 'intent': 'write-replace'},
            ],
        }
    ]

    mso._annotate_foreign(deliverables)

    assert deliverables[0]['foreign'] is True


def test_a_marker_less_foreign_affected_file_still_rolls_up_true(monkeypatch):
    """An entry with no intent marker is a change — never quieter than a marked one."""
    monkeypatch.setattr(mso, 'cwd_checkout_root', lambda: '/repo')
    deliverables = [
        {
            'number': 1,
            'title': 'D1',
            'affected_files': [{'path': '/foreign/Unmarked.java', 'intent': None}],
        }
    ]

    mso._annotate_foreign(deliverables)

    assert deliverables[0]['foreign'] is True


def test_the_survey_exclusion_is_decided_by_intent_not_by_field(monkeypatch):
    """A survey bullet rolls up by its parsed intent, never by the field it sits in.

    A marker-less ``Files to survey`` bullet parses as ``read`` and does not roll
    up; the same field carrying an explicit write marker does. Both entries are
    foreign by their own per-entry flag either way.
    """
    monkeypatch.setattr(mso, 'cwd_checkout_root', lambda: '/repo')
    deliverables = [
        {
            'number': 1,
            'title': 'Survey default',
            'affected_files': [],
            'survey_scope': [{'path': '/foreign/pool/a.py', 'intent': 'read'}],
            'mutation_scope': [{'path': 'src/host.py', 'intent': None}],
        },
        {
            'number': 2,
            'title': 'Survey with an explicit write marker',
            'affected_files': [],
            'survey_scope': [{'path': '/foreign/pool/b.py', 'intent': 'write-new'}],
            'mutation_scope': [{'path': 'src/host.py', 'intent': None}],
        },
    ]

    mso._annotate_foreign(deliverables)

    assert deliverables[0]['survey_scope'][0]['foreign'] is True
    assert deliverables[1]['survey_scope'][0]['foreign'] is True
    assert deliverables[0]['foreign'] is False
    assert deliverables[1]['foreign'] is True


def test_the_roll_up_consumes_the_shared_predicate(monkeypatch):
    """The roll-up routes through ``declares_change`` rather than a local copy of the rule.

    Replacing the imported predicate with one that rejects everything must flip
    a foreign write's roll-up to ``false``. A roll-up that re-derived the rule
    inline would stay ``true`` and let the column drift from the gate.
    """
    monkeypatch.setattr(mso, 'cwd_checkout_root', lambda: '/repo')
    monkeypatch.setattr(mso, 'declares_change', lambda _entry: False)
    deliverables = [_deliverable(1, ['/foreign/Changed.java'])]

    mso._annotate_foreign(deliverables)

    assert deliverables[0]['affected_files'][0]['foreign'] is True
    assert deliverables[0]['foreign'] is False
