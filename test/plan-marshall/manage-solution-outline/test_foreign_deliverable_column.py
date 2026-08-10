#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""Tests for the foreign-vs-host discriminator and the list-deliverables ``foreign`` column.

Covers:

* :func:`_plan_parsing.is_foreign_path` — the single lexical predicate that
  decides whether a declared path lands outside the project root (host relative,
  host absolute-under-root, foreign absolute, ``../`` escape, sibling-prefix
  trap, and the empty path);
* ``manage-solution-outline``'s ``_annotate_foreign`` — the per-entry and
  roll-up ``foreign`` flags stamped onto ``list-deliverables`` output, which is
  the population the pre-archive landing gate iterates and the split that keeps a
  coverage ratio from pooling host and foreign paths.
"""

from _plan_parsing import is_foreign_path
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

    # Deliverable-level roll-up: true iff ANY entry is foreign.
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
