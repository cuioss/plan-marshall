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


def _deliverable(number, *, foreign, paths, intent='write-replace', branch=None):
    """One deliverable whose every ``affected_files`` entry carries ``intent``.

    The default is a write intent, so a test that does not name an intent is
    asserting about a declared CHANGE — the population the gate exists to guard.
    ``branch`` declares the foreign branch the way an outline does, through the
    deliverable's ``**Metadata:**`` block.
    """
    deliverable = {
        'number': number,
        'foreign': foreign,
        'affected_files': [{'path': p, 'intent': intent, 'foreign': foreign} for p in paths],
    }
    if branch is not None:
        deliverable['metadata'] = {'foreign_branch': branch}
    return deliverable


def _run(deliverables, *, roots=None, landings=None, resolved_paths=None, branches=None, landing_branches=None):
    """Drive gate.check with fully in-memory seams.

    ``roots`` maps a declared path to its resolved repo root. ``landings`` maps a
    repo root to a landing state, either a plain state string or a
    ``{branch: state}`` map so a fixture can answer DIFFERENTLY per branch — the
    red-at-HEAD shape, where the plan's own branch name reads ``pushed_no_pr``
    and the branch the change is actually on reads ``merged``. ``branches`` maps a
    repo root to the branch its checkout is on (absent or ``None`` for a detached
    or unreadable checkout). ``resolved_paths``, when given, is a list the root
    resolver appends every path it is asked about to — the observable that a path
    did or did not enter the population. ``landing_branches``, when given, records
    the branch each landing read was made for.
    """
    roots = roots or {}
    landings = landings or {}
    # Every resolved root sits on a readable branch unless a test says otherwise:
    # the checkout is one of the two branch sources, so a default of "no branch"
    # would turn every unrelated fixture into a branch_unreadable error.
    if branches is None:
        branches = {root: 'fix/foreign-branch' for root in roots.values() if root}

    def loader(_plan_id):
        return _listed(deliverables)

    def root_resolver(path):
        if resolved_paths is not None:
            resolved_paths.append(path)
        return roots.get(path)

    def branch_resolver(root):
        return branches.get(root)

    def landing_resolver(root, branch):
        if landing_branches is not None:
            landing_branches.setdefault(root, branch)
        state = landings.get(root)
        if isinstance(state, dict):
            state = state.get(branch)
        return {'landing_state': state} if state is not None else {'status': 'error', 'error': 'no state'}

    return gate.check(
        'p',
        deliverables_loader=loader,
        root_resolver=root_resolver,
        landing_resolver=landing_resolver,
        branch_resolver=branch_resolver,
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


def test_pr_open_foreign_deliverable_clears():
    deliverables = [_deliverable(1, foreign=True, paths=['/foreign/repo/a.py'])]
    result = _run(deliverables, roots={'/foreign/repo/a.py': '/foreign/repo'}, landings={'/foreign/repo': 'pr_open'})
    assert result['status'] == 'clear'


def test_no_foreign_deliverables_clears():
    deliverables = [_deliverable(1, foreign=False, paths=['src/host.py'])]
    result = _run(deliverables)
    assert result['status'] == 'clear'
    assert result['foreign_deliverable_count'] == 0


def test_unresolvable_repo_root_fails_closed():
    # A foreign repo whose root cannot be resolved cannot be certified landed, so
    # its landing state is indeterminate and the gate refuses to archive rather
    # than clear on absent evidence.
    deliverables = [_deliverable(1, foreign=True, paths=['/gone/a.py'])]
    result = _run(deliverables, roots={'/gone/a.py': None})
    assert result['status'] == 'error'
    assert result['unresolved'][0]['path'] == '/gone/a.py'


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


def test_the_population_reads_the_survey_scope_pair():
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

    extracted = gate._partition_foreign_paths(deliverables).by_deliverable

    assert extracted == [(1, ['/foreign/mutated.py', '/foreign/surveyed.py'])]


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

    extracted = gate._partition_foreign_paths(deliverables).by_deliverable

    assert extracted == [(1, ['/foreign/both.py'])]


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


def test_a_clear_over_a_genuinely_empty_foreign_population_names_none():
    """The negative control: the same clear verdict, with nothing excluded to name."""
    deliverables = [_deliverable(1, foreign=False, paths=['src/host.py'], intent='read')]

    result = _run(deliverables)

    assert result['status'] == 'clear'
    assert result['foreign_deliverable_count'] == 0
    assert result['excluded_read_only_count'] == 0
    assert result['excluded_read_only'] == []


def test_the_pre_walk_errors_carry_no_exclusion_fields():
    """Nothing was evaluated before the walk, so no exclusion count is published.

    A zero there would read as "walked, and excluded nothing".
    """

    def loader(_plan_id):
        return {'status': 'error', 'error': 'document_not_found'}

    result = gate.check('p', deliverables_loader=loader, root_resolver=lambda p: None, landing_resolver=lambda r, b: {})

    assert result['status'] == 'error'
    assert 'excluded_read_only_count' not in result
    assert 'excluded_read_only' not in result


# --------------------------------------------------------------------------- #
# The branch a foreign repository is classified on
# --------------------------------------------------------------------------- #


def test_a_foreign_change_on_a_branch_the_plan_id_does_not_name_is_clear():
    """The red-at-HEAD fixture: the change is on a branch, and the plan id is not it.

    The landing resolver answers PER BRANCH, and it answers ``pushed_no_pr`` for
    the plan's own ``feature/p`` — the branch the gate assumed at HEAD. So the
    verdict distinguishes "read the wrong branch" (blocked) from "read the
    foreign branch" (clear) rather than passing on either.
    """
    deliverables = [_deliverable(1, foreign=True, paths=['/foreign/repo/a.py'], branch='docs/workflow-dsl')]
    result = _run(
        deliverables,
        roots={'/foreign/repo/a.py': '/foreign/repo'},
        branches={'/foreign/repo': 'docs/workflow-dsl'},
        landings={'/foreign/repo': {'docs/workflow-dsl': 'merged', 'feature/p': 'pushed_no_pr'}},
    )

    assert result['status'] == 'clear'
    assert result['repos'] == [
        {
            'repo_root': '/foreign/repo',
            'branch': 'docs/workflow-dsl',
            'landing_state': 'merged',
            'deliverables': [1],
        }
    ]


def test_the_same_change_without_a_pr_is_still_blocked():
    """Control: the correct branch name does not weaken the block.

    ``pushed_no_pr`` on the foreign branch is exactly the state the gate exists
    to refuse, so reading the RIGHT branch must still block.
    """
    deliverables = [_deliverable(1, foreign=True, paths=['/foreign/repo/a.py'], branch='docs/workflow-dsl')]
    result = _run(
        deliverables,
        roots={'/foreign/repo/a.py': '/foreign/repo'},
        branches={'/foreign/repo': 'docs/workflow-dsl'},
        landings={'/foreign/repo': {'docs/workflow-dsl': 'pushed_no_pr'}},
    )

    assert result['status'] == 'blocked'
    assert result['blocking'] == [{'repo_root': '/foreign/repo', 'deliverables': [1]}]


def test_a_declared_branch_that_disagrees_with_the_checkout_is_unresolved():
    """Two sources that say different things are an error, never a preference."""
    deliverables = [_deliverable(1, foreign=True, paths=['/foreign/repo/a.py'], branch='docs/workflow-dsl')]
    result = _run(
        deliverables,
        roots={'/foreign/repo/a.py': '/foreign/repo'},
        branches={'/foreign/repo': 'main'},
        landings={'/foreign/repo': {'docs/workflow-dsl': 'merged', 'main': 'merged'}},
    )

    assert result['status'] == 'error'
    assert result['error'] == 'foreign_landing_indeterminate'
    assert any(str(item['reason']).startswith('branch_disagreement') for item in result['unresolved']), result[
        'unresolved'
    ]


def test_deliverables_declaring_different_branches_for_one_repo_disagree():
    """One repository, two declared branches: the gate has no basis to pick one."""
    deliverables = [
        _deliverable(1, foreign=True, paths=['/foreign/repo/a.py'], branch='docs/one'),
        _deliverable(2, foreign=True, paths=['/foreign/repo/b.py'], branch='docs/two'),
    ]
    result = _run(
        deliverables,
        roots={'/foreign/repo/a.py': '/foreign/repo', '/foreign/repo/b.py': '/foreign/repo'},
        branches={'/foreign/repo': 'docs/one'},
        landings={'/foreign/repo': {'docs/one': 'merged', 'docs/two': 'merged'}},
    )

    assert result['status'] == 'error'
    assert result['error'] == 'foreign_landing_indeterminate'
    assert any(str(item['reason']).startswith('branch_disagreement') for item in result['unresolved']), result[
        'unresolved'
    ]


def test_an_unreadable_branch_is_a_named_unresolved_row():
    """No declaration and a checkout that reports no branch: fail closed, named."""
    deliverables = [_deliverable(1, foreign=True, paths=['/foreign/repo/a.py'])]
    result = _run(
        deliverables,
        roots={'/foreign/repo/a.py': '/foreign/repo'},
        branches={},
        landings={'/foreign/repo': 'merged'},
    )

    assert result['status'] == 'error'
    assert [str(item['reason']).split(':')[0] for item in result['unresolved']] == ['branch_unreadable']
    assert result['unresolved'][0]['path'] == '/foreign/repo'
    assert 'repos' in result and result['repos'] == []


def test_the_checkout_branch_is_used_when_nothing_is_declared():
    """No declaration: the branch the foreign checkout is on is the answer."""
    branches_seen: dict[str, str] = {}
    deliverables = [_deliverable(1, foreign=True, paths=['/foreign/repo/a.py'])]
    result = _run(
        deliverables,
        roots={'/foreign/repo/a.py': '/foreign/repo'},
        branches={'/foreign/repo': 'docs/workflow-dsl'},
        landings={'/foreign/repo': {'docs/workflow-dsl': 'merged', 'feature/p': 'pushed_no_pr'}},
        landing_branches=branches_seen,
    )

    assert result['status'] == 'clear'
    assert result['repos'][0]['branch'] == 'docs/workflow-dsl'
    assert branches_seen == {'/foreign/repo': 'docs/workflow-dsl'}


def test_the_plan_id_branch_is_never_the_fallback():
    """A repository whose checkout names a branch is read on THAT branch only.

    ``feature/p`` is the plan's own name (the plan id in this suite is ``p``), and
    the landing fixture answers it ``pushed_no_pr``. Any fall-back to it would
    turn this clear into a block, so the verdict pins the absence of a fall-back.
    """
    branches_seen: dict[str, str] = {}
    deliverables = [_deliverable(1, foreign=True, paths=['/foreign/repo/a.py'])]
    result = _run(
        deliverables,
        roots={'/foreign/repo/a.py': '/foreign/repo'},
        branches={'/foreign/repo': 'main'},
        landings={'/foreign/repo': {'main': 'merged', 'feature/p': 'pushed_no_pr'}},
        landing_branches=branches_seen,
    )

    assert result['status'] == 'clear'
    assert branches_seen == {'/foreign/repo': 'main'}
