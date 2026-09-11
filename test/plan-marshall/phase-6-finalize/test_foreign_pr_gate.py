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
    foreign paths at all) rather than a shorter list. Every entry declares a
    change — the survey bullet through an explicit write marker — so both
    fields' paths belong to the population and the assertion still pins that
    the survey field is traversed at all.
    """
    deliverables = [
        {
            'number': 1,
            'foreign': True,
            'affected_files': [],
            'survey_scope': [{'path': '/foreign/surveyed.py', 'intent': 'write-new', 'foreign': True}],
            'mutation_scope': [
                {'path': 'host.py', 'intent': 'write-replace', 'foreign': False},
                {'path': '/foreign/mutated.py', 'intent': 'write-replace', 'foreign': True},
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
            'survey_scope': [{'path': '/foreign/both.py', 'intent': 'write-new', 'foreign': True}],
            'mutation_scope': [{'path': '/foreign/both.py', 'intent': 'write-replace', 'foreign': True}],
        },
    ]

    extracted = gate._foreign_paths_by_deliverable(deliverables)

    assert extracted == [(1, ['/foreign/both.py'])]


# --------------------------------------------------------------------------- #
# The population is foreign AND declares a change
# --------------------------------------------------------------------------- #


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


def test_a_read_foreign_path_does_not_enter_the_population():
    """A consulted foreign file has no commit, so no PR could ever clear it.

    Its repository is ``pushed_no_pr``, so had the path entered the population
    the verdict would be ``blocked``. The resolver log pins the mechanism: the
    path was never even resolved.
    """
    resolved: list[str] = []
    deliverables = [_deliverable(1, foreign=True, paths=['/foreign/repo/ref.py'], intent='read')]

    result = _run(
        deliverables,
        roots={'/foreign/repo/ref.py': '/foreign/repo'},
        landings={'/foreign/repo': 'pushed_no_pr'},
        resolved_paths=resolved,
    )

    assert result['status'] == 'clear'
    assert result['foreign_deliverable_count'] == 0
    assert 'blocking' not in result
    assert resolved == []
    assert result['excluded_read_only'] == [{'deliverable': 1, 'path': '/foreign/repo/ref.py'}]


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


def test_a_survey_path_with_an_explicit_write_marker_blocks():
    """The exclusion is decided by the parsed intent, never by the field name."""
    deliverables = [
        {
            'number': 1,
            'foreign': True,
            'affected_files': [],
            'survey_scope': [{'path': '/foreign/repo/pool.py', 'intent': 'write-new', 'foreign': True}],
            'mutation_scope': [],
        }
    ]

    result = _run(
        deliverables,
        roots={'/foreign/repo/pool.py': '/foreign/repo'},
        landings={'/foreign/repo': 'pushed_no_pr'},
    )

    assert result['status'] == 'blocked'
    assert result['excluded_read_only_count'] == 0


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


def test_a_path_declared_read_and_write_is_gated_not_excluded():
    """A path one field declares as a change is in the population, not an exclusion.

    Reporting it as excluded would tell the operator the gate skipped a path it
    in fact evaluated.
    """
    deliverables = [
        {
            'number': 1,
            'foreign': True,
            'affected_files': [],
            'survey_scope': [{'path': '/foreign/repo/both.py', 'intent': 'read', 'foreign': True}],
            'mutation_scope': [{'path': '/foreign/repo/both.py', 'intent': 'write-replace', 'foreign': True}],
        }
    ]

    result = _run(deliverables, roots={'/foreign/repo/both.py': '/foreign/repo'}, landings={'/foreign/repo': 'merged'})

    assert result['status'] == 'clear'
    assert result['foreign_deliverable_count'] == 1
    assert result['excluded_read_only_count'] == 0
    assert result['excluded_read_only'] == []


def test_the_population_consumes_the_shared_predicate(monkeypatch):
    """The gate routes through ``declares_change`` rather than a local copy of the rule.

    Replacing the imported predicate with one that accepts everything must pull a
    ``read`` path into the population. A gate that re-derived the rule inline
    would keep excluding it and drift from the column.
    """
    monkeypatch.setattr(gate, 'declares_change', lambda _entry: True)
    deliverables = [_deliverable(1, foreign=True, paths=['/foreign/repo/ref.py'], intent='read')]

    result = _run(
        deliverables, roots={'/foreign/repo/ref.py': '/foreign/repo'}, landings={'/foreign/repo': 'pushed_no_pr'}
    )

    assert result['status'] == 'blocked'


# --------------------------------------------------------------------------- #
# Exclusions are named on the result — a filtered clear is not an empty clear
# --------------------------------------------------------------------------- #


def test_a_clear_reached_after_exclusions_names_the_excluded_paths():
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


def test_a_clear_over_a_genuinely_empty_foreign_population_names_none():
    """The negative control: the same clear verdict, with nothing excluded to name."""
    deliverables = [_deliverable(1, foreign=False, paths=['src/host.py'], intent='read')]

    result = _run(deliverables)

    assert result['status'] == 'clear'
    assert result['foreign_deliverable_count'] == 0
    assert result['excluded_read_only_count'] == 0
    assert result['excluded_read_only'] == []


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


def test_the_pre_walk_errors_carry_no_exclusion_fields():
    """Nothing was evaluated before the walk, so no exclusion count is published.

    A zero there would read as "walked, and excluded nothing".
    """

    def loader(_plan_id):
        return {'status': 'error', 'error': 'document_not_found'}

    result = gate.check('p', deliverables_loader=loader, root_resolver=lambda p: None, landing_resolver=lambda r: {})

    assert result['status'] == 'error'
    assert 'excluded_read_only_count' not in result
    assert 'excluded_read_only' not in result


# --------------------------------------------------------------------------- #
# End to end: outline markdown → parser → foreign column → TOON → gate
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
