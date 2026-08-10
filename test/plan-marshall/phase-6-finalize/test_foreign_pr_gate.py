#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""Tests for the pre-archive foreign-PR landing gate.

The gate is the enforcement point that stops a foreign task from reaching
``done`` (and its plan from archiving) while its change is ``pushed_no_pr`` — a
commit pushed to a branch that no PR carries anywhere. The central test proves a
plan with a ``pushed_no_pr`` foreign deliverable is REFUSED at the gate; before
this change there was no gate, so archiving proceeded unconditionally. The seams
(``deliverables_loader`` / ``root_resolver`` / ``landing_resolver``) let the
orchestration be driven without a live outline, a live foreign checkout, or a
live CI provider.
"""

from conftest import load_script_module

gate = load_script_module('plan-marshall', 'phase-6-finalize', 'foreign_pr_gate.py', 'foreign_pr_gate')


# --------------------------------------------------------------------------- #
# Fixtures / builders
# --------------------------------------------------------------------------- #


def _listed(deliverables):
    return {'status': 'success', 'plan_id': 'p', 'deliverable_count': len(deliverables), 'deliverables': deliverables}


def _deliverable(number, *, foreign, paths):
    return {
        'number': number,
        'foreign': foreign,
        'affected_files': [{'path': p, 'foreign': foreign} for p in paths],
    }


def _run(deliverables, *, roots=None, landings=None):
    """Drive gate.check with fully in-memory seams.

    ``roots`` maps a declared path to its resolved repo root (default: the path's
    parent stands in as the root). ``landings`` maps a repo root to a landing
    state string.
    """
    roots = roots or {}
    landings = landings or {}

    def loader(_plan_id):
        return _listed(deliverables)

    def root_resolver(path):
        return roots.get(path)

    def landing_resolver(root):
        state = landings.get(root)
        return {'landing_state': state} if state is not None else {'status': 'error', 'error': 'no state'}

    return gate.check(
        'p',
        deliverables_loader=loader,
        root_resolver=root_resolver,
        landing_resolver=landing_resolver,
    )


# --------------------------------------------------------------------------- #
# The central refusal (fails before the change: no gate module existed)
# --------------------------------------------------------------------------- #


def test_pushed_no_pr_foreign_deliverable_is_refused_at_archive():
    deliverables = [_deliverable(3, foreign=True, paths=['/foreign/repo/src/Foo.java'])]
    result = _run(
        deliverables,
        roots={'/foreign/repo/src/Foo.java': '/foreign/repo'},
        landings={'/foreign/repo': 'pushed_no_pr'},
    )
    assert result['status'] == 'blocked'
    assert result['blocking'] == [{'repo_root': '/foreign/repo', 'deliverables': [3]}]
    assert 'pushed_no_pr' in result['message']


# --------------------------------------------------------------------------- #
# Clearing states — a foreign change that landed / is in review / never pushed
# --------------------------------------------------------------------------- #


def test_merged_foreign_deliverable_clears():
    deliverables = [_deliverable(1, foreign=True, paths=['/foreign/repo/a.py'])]
    result = _run(deliverables, roots={'/foreign/repo/a.py': '/foreign/repo'}, landings={'/foreign/repo': 'merged'})
    assert result['status'] == 'clear'
    assert result['repos'] == [{'repo_root': '/foreign/repo', 'landing_state': 'merged', 'deliverables': [1]}]


def test_pr_open_foreign_deliverable_clears():
    deliverables = [_deliverable(1, foreign=True, paths=['/foreign/repo/a.py'])]
    result = _run(deliverables, roots={'/foreign/repo/a.py': '/foreign/repo'}, landings={'/foreign/repo': 'pr_open'})
    assert result['status'] == 'clear'


def test_no_foreign_deliverables_clears():
    deliverables = [_deliverable(1, foreign=False, paths=['src/host.py'])]
    result = _run(deliverables)
    assert result['status'] == 'clear'
    assert result['foreign_deliverable_count'] == 0


# --------------------------------------------------------------------------- #
# Error / unresolved handling
# --------------------------------------------------------------------------- #


def test_unlistable_outline_is_error_and_fails_closed():
    def loader(_plan_id):
        return {'status': 'error', 'error': 'document_not_found'}

    result = gate.check('p', deliverables_loader=loader, root_resolver=lambda p: None, landing_resolver=lambda r: {})
    assert result['status'] == 'error'


def test_unresolvable_repo_root_is_reported_not_blocking():
    deliverables = [_deliverable(1, foreign=True, paths=['/gone/a.py'])]
    result = _run(deliverables, roots={'/gone/a.py': None})
    assert result['status'] == 'clear'
    assert result['unresolved'][0]['path'] == '/gone/a.py'


def test_landing_state_failure_is_reported_not_blocking():
    # A repo whose landing-state verb fails cannot be certified landed, but a
    # failure is not pushed_no_pr — it is surfaced as unresolved, never cleared
    # silently and never counted as a block.
    deliverables = [_deliverable(1, foreign=True, paths=['/foreign/repo/a.py'])]
    result = _run(deliverables, roots={'/foreign/repo/a.py': '/foreign/repo'}, landings={})  # no state → verb error
    assert result['status'] == 'clear'
    assert any('landing-state unresolved' in u['reason'] for u in result['unresolved'])


def test_one_pushed_no_pr_among_several_repos_blocks():
    deliverables = [
        _deliverable(1, foreign=True, paths=['/repo-a/x.py']),
        _deliverable(2, foreign=True, paths=['/repo-b/y.py']),
    ]
    result = _run(
        deliverables,
        roots={'/repo-a/x.py': '/repo-a', '/repo-b/y.py': '/repo-b'},
        landings={'/repo-a': 'merged', '/repo-b': 'pushed_no_pr'},
    )
    assert result['status'] == 'blocked'
    assert [b['repo_root'] for b in result['blocking']] == ['/repo-b']


# --------------------------------------------------------------------------- #
# Pure foreign-path extraction
# --------------------------------------------------------------------------- #


def test_foreign_paths_by_deliverable_selects_only_foreign_entries():
    deliverables = [
        {'number': 1, 'foreign': False, 'affected_files': [{'path': 'host.py', 'foreign': False}]},
        {
            'number': 2,
            'foreign': True,
            'affected_files': [
                {'path': 'host.py', 'foreign': False},
                {'path': '/foreign/a.py', 'foreign': True},
            ],
        },
    ]
    extracted = gate._foreign_paths_by_deliverable(deliverables)
    assert extracted == [(2, ['/foreign/a.py'])]


def test_blocking_landing_state_constant_is_pushed_no_pr():
    assert gate.BLOCKING_LANDING_STATE == 'pushed_no_pr'
