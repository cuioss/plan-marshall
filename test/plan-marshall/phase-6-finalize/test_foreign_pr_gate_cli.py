#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
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

import pytest
from _plan_parsing import extract_deliverables
from toon_parser import parse_toon, serialize_toon

from conftest import load_script_module

gate = load_script_module('plan-marshall', 'phase-6-finalize', 'foreign_pr_gate.py', 'foreign_pr_gate')
mso = load_script_module(
    'plan-marshall', 'manage-solution-outline', 'manage-solution-outline.py', 'manage_solution_outline_foreign_gate'
)


# --------------------------------------------------------------------------- #
# Fixtures / builders
# --------------------------------------------------------------------------- #


def _listed(deliverables):
    return {'status': 'success', 'plan_id': 'p', 'deliverable_count': len(deliverables), 'deliverables': deliverables}


def _deliverable(number, *, foreign, paths, intent='write-replace'):
    """One deliverable whose every ``affected_files`` entry carries ``intent``.

    The default is a write intent, so a test that does not name an intent is
    asserting about a declared CHANGE — the population the gate exists to guard.
    """
    return {
        'number': number,
        'foreign': foreign,
        'affected_files': [{'path': p, 'intent': intent, 'foreign': foreign} for p in paths],
    }


def _run(deliverables, *, roots=None, landings=None, resolved_paths=None):
    """Drive gate.check with fully in-memory seams.

    ``roots`` maps a declared path to its resolved repo root. ``landings`` maps a
    repo root to a landing state string. ``resolved_paths``, when given, is a list
    the root resolver appends every path it is asked about to — the observable
    that a path did or did not enter the population.
    """
    roots = roots or {}
    landings = landings or {}

    def loader(_plan_id):
        return _listed(deliverables)

    def root_resolver(path):
        if resolved_paths is not None:
            resolved_paths.append(path)
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


_FOREIGN_OUTLINE_DELIVERABLES = """### 1. Change a foreign repository

**Affected files:**
- `/foreign/repo/src/Changed.java` (write-replace)
- `/foreign/repo/src/Reference.java` (read)

### 2. Survey a foreign repository

**Files to survey:**
- `/foreign/pool/Surveyed.java`

**Files expected to mutate:**
- `/foreign/other/Mutated.java`
"""


def test_merged_foreign_deliverable_clears():
    deliverables = [_deliverable(1, foreign=True, paths=['/foreign/repo/a.py'])]
    result = _run(deliverables, roots={'/foreign/repo/a.py': '/foreign/repo'}, landings={'/foreign/repo': 'merged'})
    assert result['status'] == 'clear'
    assert result['repos'] == [{'repo_root': '/foreign/repo', 'landing_state': 'merged', 'deliverables': [1]}]


def test_unpushed_foreign_deliverable_clears():
    # unpushed is not the blocking state (the plan refuses only on pushed_no_pr);
    # a positively-read unpushed clears, unlike an unreadable state.
    deliverables = [_deliverable(1, foreign=True, paths=['/foreign/repo/a.py'])]
    result = _run(deliverables, roots={'/foreign/repo/a.py': '/foreign/repo'}, landings={'/foreign/repo': 'unpushed'})
    assert result['status'] == 'clear'
    assert result['repos'] == [{'repo_root': '/foreign/repo', 'landing_state': 'unpushed', 'deliverables': [1]}]


def test_unlistable_outline_is_error_and_fails_closed():
    def loader(_plan_id):
        return {'status': 'error', 'error': 'document_not_found'}

    result = gate.check('p', deliverables_loader=loader, root_resolver=lambda p: None, landing_resolver=lambda r: {})
    assert result['status'] == 'error'


def test_landing_state_failure_fails_closed():
    # A repo whose landing-state verb fails cannot be certified landed; the gate
    # surfaces it as unresolved AND refuses to clear — indeterminate is not clear.
    deliverables = [_deliverable(1, foreign=True, paths=['/foreign/repo/a.py'])]
    result = _run(deliverables, roots={'/foreign/repo/a.py': '/foreign/repo'}, landings={})  # no state → verb error
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


def test_the_population_selects_only_foreign_entries():
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
    extracted = gate._partition_foreign_paths(deliverables).by_deliverable
    assert extracted == [(2, ['/foreign/a.py'])]


def test_blocking_landing_state_constant_is_pushed_no_pr():
    assert gate.BLOCKING_LANDING_STATE == 'pushed_no_pr'


@pytest.mark.parametrize(
    'intent',
    ['write-new', 'write-replace', 'delete', None],
    ids=['write-new', 'write-replace', 'delete', 'no-marker'],
)
def test_every_change_intent_on_a_pushed_no_pr_foreign_path_blocks(intent):
    deliverables = [_deliverable(1, foreign=True, paths=['/foreign/repo/a.py'], intent=intent)]

    result = _run(
        deliverables, roots={'/foreign/repo/a.py': '/foreign/repo'}, landings={'/foreign/repo': 'pushed_no_pr'}
    )

    assert result['status'] == 'blocked'
    assert result['blocking'] == [{'repo_root': '/foreign/repo', 'deliverables': [1]}]


def test_a_marker_less_survey_path_is_excluded_while_its_mutation_sibling_blocks():
    """The survey pool parses as ``read``; the mutation subset is the change.

    Both paths sit in the SAME ``pushed_no_pr`` repository, so the blocking row
    is produced by the mutation path alone — and the survey path is named as an
    exclusion rather than dropped.
    """
    resolved: list[str] = []
    deliverables = [
        {
            'number': 1,
            'foreign': True,
            'affected_files': [],
            'survey_scope': [{'path': '/foreign/repo/pool.py', 'intent': 'read', 'foreign': True}],
            'mutation_scope': [{'path': '/foreign/repo/mutated.py', 'intent': None, 'foreign': True}],
        }
    ]

    result = _run(
        deliverables,
        roots={'/foreign/repo/pool.py': '/foreign/repo', '/foreign/repo/mutated.py': '/foreign/repo'},
        landings={'/foreign/repo': 'pushed_no_pr'},
        resolved_paths=resolved,
    )

    assert result['status'] == 'blocked'
    assert resolved == ['/foreign/repo/mutated.py']
    assert result['excluded_read_only'] == [{'deliverable': 1, 'path': '/foreign/repo/pool.py'}]


def test_an_entry_with_no_intent_marker_still_blocks():
    """The conservative direction, pinned against a "filter everything unmarked" regression.

    The entry carries no ``intent`` key at all. An unmarked foreign change is the
    hidden-foreign-commit case this gate exists for, so it must stay in the
    population.
    """
    deliverables = [{'number': 1, 'foreign': True, 'affected_files': [{'path': '/foreign/repo/a.py', 'foreign': True}]}]

    result = _run(
        deliverables, roots={'/foreign/repo/a.py': '/foreign/repo'}, landings={'/foreign/repo': 'pushed_no_pr'}
    )

    assert result['status'] == 'blocked'


def test_a_path_gated_through_one_deliverable_is_not_excluded_through_another():
    """The exclusion test spans the whole population, not one deliverable's slice.

    Deliverable 1 only reads the path; deliverable 2 changes it. The gate
    evaluates it through deliverable 2, so an exclusion row naming it through
    deliverable 1 would tell the operator the gate skipped a path it evaluated.
    """
    deliverables = [
        _deliverable(1, foreign=True, paths=['/foreign/repo/shared.py'], intent='read'),
        _deliverable(2, foreign=True, paths=['/foreign/repo/shared.py']),
    ]
    resolved: list[str] = []

    result = _run(
        deliverables,
        roots={'/foreign/repo/shared.py': '/foreign/repo'},
        landings={'/foreign/repo': 'merged'},
        resolved_paths=resolved,
    )

    assert result['status'] == 'clear'
    assert resolved == ['/foreign/repo/shared.py']
    assert result['excluded_read_only_count'] == 0
    assert result['excluded_read_only'] == []


def test_a_clear_reached_after_exclusions_names_the_excluded_paths():
    """Rows are keyed by (deliverable, path): ref.py, read by both, appears twice."""
    deliverables = [
        _deliverable(1, foreign=True, paths=['/foreign/repo/ref.py'], intent='read'),
        _deliverable(2, foreign=True, paths=['/foreign/repo/other.py', '/foreign/repo/ref.py'], intent='read'),
    ]

    result = _run(deliverables)

    assert result['status'] == 'clear'
    assert result['foreign_deliverable_count'] == 0
    assert result['excluded_read_only_count'] == 3
    assert result['excluded_read_only'] == [
        {'deliverable': 1, 'path': '/foreign/repo/ref.py'},
        {'deliverable': 2, 'path': '/foreign/repo/other.py'},
        {'deliverable': 2, 'path': '/foreign/repo/ref.py'},
    ]


def test_exclusions_ride_on_a_blocked_result_too():
    deliverables = [
        {
            'number': 1,
            'foreign': True,
            'affected_files': [
                {'path': '/foreign/repo/changed.py', 'intent': 'write-replace', 'foreign': True},
                {'path': '/foreign/repo/ref.py', 'intent': 'read', 'foreign': True},
            ],
        }
    ]

    result = _run(
        deliverables,
        roots={'/foreign/repo/changed.py': '/foreign/repo'},
        landings={'/foreign/repo': 'pushed_no_pr'},
    )

    assert result['status'] == 'blocked'
    assert result['excluded_read_only'] == [{'deliverable': 1, 'path': '/foreign/repo/ref.py'}]


def test_the_real_parser_and_column_feed_the_gate_the_narrowed_population(monkeypatch):
    """The intents the gate reads are the ones the parser produced, after a TOON round trip.

    The fixture-level tests above hand the gate hand-built intents. This one
    derives them from outline markdown — including the ``read`` default a
    marker-less survey bullet receives at parse time — stamps the column, and
    passes the payload through the same serialize/parse boundary the CLI uses, so
    a regression anywhere on that path (a lost default, a flag that stops
    round-tripping) reaches a different verdict.
    """
    monkeypatch.setattr(mso, 'cwd_checkout_root', lambda: '/repo')
    deliverables = extract_deliverables(_FOREIGN_OUTLINE_DELIVERABLES)
    mso._annotate_foreign(deliverables)
    payload = parse_toon(serialize_toon(_listed(deliverables)))
    roots = {'/foreign/repo/src/Changed.java': '/foreign/repo', '/foreign/other/Mutated.java': '/foreign/other'}
    landings = {'/foreign/repo': 'pushed_no_pr', '/foreign/other': 'merged'}
    resolved: list[str] = []

    def root_resolver(path):
        resolved.append(path)
        return roots.get(path)

    result = gate.check(
        'p',
        deliverables_loader=lambda _p: payload,
        root_resolver=root_resolver,
        landing_resolver=lambda root: {'landing_state': landings[root]},
    )

    assert result['status'] == 'blocked'
    assert result['blocking'] == [{'repo_root': '/foreign/repo', 'deliverables': [1]}]
    assert sorted(resolved) == ['/foreign/other/Mutated.java', '/foreign/repo/src/Changed.java']
    assert result['excluded_read_only'] == [
        {'deliverable': 1, 'path': '/foreign/repo/src/Reference.java'},
        {'deliverable': 2, 'path': '/foreign/pool/Surveyed.java'},
    ]
