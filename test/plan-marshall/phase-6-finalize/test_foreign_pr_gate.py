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


def test_unpushed_foreign_deliverable_clears():
    # unpushed is not the blocking state (the plan refuses only on pushed_no_pr);
    # a positively-read unpushed clears, unlike an unreadable state.
    deliverables = [_deliverable(1, foreign=True, paths=['/foreign/repo/a.py'])]
    result = _run(deliverables, roots={'/foreign/repo/a.py': '/foreign/repo'}, landings={'/foreign/repo': 'unpushed'})
    assert result['status'] == 'clear'
    assert result['repos'] == [{'repo_root': '/foreign/repo', 'landing_state': 'unpushed', 'deliverables': [1]}]


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


def test_unresolvable_repo_root_fails_closed():
    # A foreign repo whose root cannot be resolved cannot be certified landed, so
    # its landing state is indeterminate and the gate refuses to archive rather
    # than clear on absent evidence.
    deliverables = [_deliverable(1, foreign=True, paths=['/gone/a.py'])]
    result = _run(deliverables, roots={'/gone/a.py': None})
    assert result['status'] == 'error'
    assert result['unresolved'][0]['path'] == '/gone/a.py'


def test_landing_state_failure_fails_closed():
    # A repo whose landing-state verb fails cannot be certified landed; the gate
    # surfaces it as unresolved AND refuses to clear — indeterminate is not clear.
    deliverables = [_deliverable(1, foreign=True, paths=['/foreign/repo/a.py'])]
    result = _run(deliverables, roots={'/foreign/repo/a.py': '/foreign/repo'}, landings={})  # no state → verb error
    assert result['status'] == 'error'
    assert any('landing-state unresolved' in u['reason'] for u in result['unresolved'])


def test_unknown_landing_state_fails_closed():
    # An unknown-but-truthy state outside the declared model must NOT clear — the
    # gate validates against ci_base.LANDING_STATES rather than truthiness.
    deliverables = [_deliverable(1, foreign=True, paths=['/foreign/repo/a.py'])]
    result = _run(
        deliverables,
        roots={'/foreign/repo/a.py': '/foreign/repo'},
        landings={'/foreign/repo': 'definitely-landed'},
    )
    assert result['status'] == 'error'
    assert any('landing-state unresolved' in u['reason'] for u in result['unresolved'])


def test_unresolvable_project_root_fails_closed(monkeypatch):
    # If the gate cannot establish the project root, the advisory foreign column
    # may have stamped everything host; the gate must not clear on that.
    def boom():
        raise RuntimeError('not a git checkout')

    monkeypatch.setattr(gate, 'cwd_checkout_root', boom)
    result = gate.check(
        'p',
        deliverables_loader=lambda _p: _listed([_deliverable(1, foreign=True, paths=['/foreign/a.py'])]),
        root_resolver=lambda _path: '/foreign',
        landing_resolver=lambda _root: {'landing_state': 'merged'},
    )
    assert result['status'] == 'error'
    assert result['error'] == 'project_root_unresolvable'


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


def test_foreign_paths_by_deliverable_reads_the_survey_scope_pair():
    """A survey-scope deliverable's foreign paths reach the landing gate.

    A discovery-style deliverable declares ``Files to survey:`` +
    ``Files expected to mutate:`` INSTEAD of a flat ``Affected files:`` list, so
    a gate reading only the flat field sees an EMPTY path list for a deliverable
    that has a real foreign write-set — and clears a landing it should block.
    The population this gate iterates must be the whole declared surface, not
    the subset one field happens to carry.

    The fixture gives the deliverable an empty ``affected_files``, so a
    regression to the flat-field-only read reaches the opposite verdict (no
    foreign paths at all) rather than a shorter list.
    """
    deliverables = [
        {
            'number': 1,
            'foreign': True,
            'affected_files': [],
            'survey_scope': [{'path': '/foreign/surveyed.py', 'foreign': True}],
            'mutation_scope': [
                {'path': 'host.py', 'foreign': False},
                {'path': '/foreign/mutated.py', 'foreign': True},
            ],
        },
    ]

    extracted = gate._foreign_paths_by_deliverable(deliverables)

    assert extracted == [(1, ['/foreign/mutated.py', '/foreign/surveyed.py'])]


def test_blocking_landing_state_constant_is_pushed_no_pr():
    assert gate.BLOCKING_LANDING_STATE == 'pushed_no_pr'


def test_a_doubly_declared_foreign_path_is_named_once():
    """A path declared under two headings appears once in the blocking message.

    The survey-scope convention requires `Files to survey:` and `Files expected
    to mutate:` to be disjoint, but that is an AUTHORING rule and no check
    enforces it — `validate_deliverable_contract` does not compare the two
    lists. So the gate must dedupe rather than assume: a path declared under
    both would otherwise be named twice to the operator, in a message whose job
    is to tell them exactly which foreign paths are unlanded.

    The verdict is unaffected either way (`if paths:`), which is precisely why
    this needs its own guard — no existing assertion could see the duplicate.
    """
    deliverables = [
        {
            'number': 1,
            'foreign': True,
            'affected_files': [],
            'survey_scope': [{'path': '/foreign/both.py', 'foreign': True}],
            'mutation_scope': [{'path': '/foreign/both.py', 'foreign': True}],
        },
    ]

    extracted = gate._foreign_paths_by_deliverable(deliverables)

    assert extracted == [(1, ['/foreign/both.py'])]
