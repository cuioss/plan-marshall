#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the phase-4-plan mechanical Q-Gate's CLOSURE checks.

Existence and closure are different questions, and the end-to-end fixtures are
built so that difference is actually exercised rather than merely asserted.

⛔ ``files_exist`` applies an INTENT-DEPENDENT predicate: it skips
``write-replace`` outright, requires existence for ``read`` and ``delete``, and
inverts for ``write-new``. A fixture whose steps all carry ``write-replace``
therefore reports ``files_exist: 0`` no matter what its paths are — including
paths that do not exist — so asserting that zero would prove nothing about
existence. The end-to-end fixtures below use ``read`` intent on their steps and
real repository files, which makes the existence check actually run and actually
pass; ``test_files_exist_zero_is_load_bearing_not_vacuous`` pins that by
replacing the paths with absent ones and asserting ``files_exist`` goes
non-zero.
"""

from __future__ import annotations

import json
import os
from argparse import Namespace
from fnmatch import fnmatch
from functools import lru_cache
from pathlib import Path
from typing import Any

from conftest import PROJECT_ROOT, load_script_module

_closure = load_script_module('plan-marshall', 'manage-tasks', '_qgate_closure.py', '_qgate_closure')
_qgate = load_script_module(
    'plan-marshall', 'manage-tasks', '_cmd_qgate_mechanical.py', '_cmd_qgate_mechanical_closure'
)

check_declared_set_closure = _closure.check_declared_set_closure
check_declared_scope_reconciliation = _closure.check_declared_scope_reconciliation
compute_projection_gaps = _closure.compute_projection_gaps
compute_referrer_gaps = _closure.compute_referrer_gaps
expand_declared_glob = _closure.expand_declared_glob
declared_paths = _closure.declared_paths
normalize_declared_path = _closure.normalize_declared_path
is_glob = _closure.is_glob
cmd_qgate_mechanical = _qgate.cmd_qgate_mechanical

_parsing = load_script_module(
    'plan-marshall', 'manage-solution-outline', '_plan_parsing.py', '_plan_parsing_closure'
)
extract_deliverables = _parsing.extract_deliverables
parse_document_sections = _parsing.parse_document_sections

#: Two real repository files. Paired with ``read``-intent steps (see
#: :func:`_task`), they make ``files_exist`` run its existence predicate and
#: pass, so a closure finding in the same result can never be an existence
#: finding wearing another name.
_REAL_A = 'marketplace/bundles/plan-marshall/skills/manage-tasks/SKILL.md'
_REAL_B = 'marketplace/bundles/plan-marshall/skills/manage-tasks/scripts/_qgate_closure.py'

#: A glob whose expansion is stable and small, used for the claim-vs-index
#: cases. Its enumeration is re-derived from the tree at assert time rather
#: than hard-coded, so the test cannot go stale when a file is added.
_STANDARDS_GLOB = 'marketplace/bundles/plan-marshall/skills/manage-tasks/standards/*.md'

#: A glob matching MANY files. Every other glob fixture here expands to exactly
#: one, which cannot exercise a ceiling, a remainder summary, or a truncation
#: disclosure — a fixture set sharing the implementation's scale cannot see a
#: scale defect. Its cardinality is re-derived from the tree at assert time,
#: never written as a literal.
_MULTI_HIT_GLOB = 'marketplace/bundles/plan-marshall/skills/manage-tasks/scripts/*.py'

#: Trees the independent oracle's walk skips — VCS internals, the virtualenv,
#: dependency and build output, caches, and the git-ignored plan state. None of
#: them holds a file any pattern under test targets. Pruning keeps the walk
#: cheap; the exclusion is stated rather than silent because it bounds where the
#: oracle is faithful.
_WALK_PRUNED_DIRS = frozenset({'.git', '.venv', 'node_modules', 'target', '__pycache__', '.plan'})


@lru_cache(maxsize=1)
def _repo_file_index() -> tuple[str, ...]:
    """Every repo-relative file path, walked once per session.

    Cached because :func:`_independent_expansion` is called by several tests and
    a full-tree walk each time dominates the suite's runtime.
    """
    paths: list[str] = []
    for dirpath, dirnames, filenames in os.walk(PROJECT_ROOT):
        dirnames[:] = [d for d in dirnames if d not in _WALK_PRUNED_DIRS]
        for name in filenames:
            paths.append((Path(dirpath) / name).relative_to(PROJECT_ROOT).as_posix())
    return tuple(sorted(paths))


def _independent_expansion(pattern: str) -> list[str]:
    """Enumerate a pattern's matching files WITHOUT calling ``Path.glob``.

    The production expander is ``repo_root.glob(pattern)``. A test expectation
    computed with that same call agrees with the implementation by construction
    — it cannot disagree, so it verifies nothing about the expansion. This walks
    the tree and matches with :func:`fnmatch` instead, so the two computations
    are genuinely independent and CAN contradict each other.

    ⚠ It is a faithful oracle under TWO stated bounds, both of which every
    caller here satisfies:

    1. The walk prunes :data:`_WALK_PRUNED_DIRS`, so a pattern rooted inside one
       of those trees would see fewer files than ``Path.glob`` does. Every
       caller targets ``marketplace/bundles/…``, which no pruned directory
       contains.
    2. ``fnmatch``'s ``*`` crosses ``/`` while ``Path.glob``'s does not, so the
       two agree only while no SUBDIRECTORY under the pattern's parent holds a
       match. Both patterns used here name a single directory of files
       (``…/standards/*.md``, ``…/scripts/*.py``); a pattern over a nested tree
       would need a different oracle.
    """
    return [rel for rel in _repo_file_index() if fnmatch(rel, pattern)]


def _deliverable(
    number: int,
    *,
    title: str = 'D',
    affected: list[str] | None = None,
    survey: list[str] | None = None,
    mutate: list[str] | None = None,
) -> dict[str, Any]:
    """Build a deliverable record in the shape ``extract_deliverables`` returns."""
    return {
        'number': number,
        'title': title,
        'affected_files': [{'path': p, 'intent': 'write-replace'} for p in (affected or [])],
        'survey_scope': [{'path': p, 'intent': 'read'} for p in (survey or [])],
        'mutation_scope': [{'path': p, 'intent': None} for p in (mutate or [])],
    }


def _task(
    number: int,
    deliverable: int,
    targets: list[str],
    *,
    profile: str = 'implementation',
    title: str = 'T',
    intent: str = 'read',
) -> dict[str, Any]:
    """Build a task record whose steps carry an EXISTENCE-CHECKED intent.

    ``read`` is the default deliberately. ``write-replace`` — the obvious choice
    for a step that edits a file — is the one intent ``files_exist`` skips
    entirely, so a fixture built on it reports ``files_exist: 0`` for absent
    paths just as readily as for present ones, and any test asserting that zero
    would be measuring nothing.
    """
    return {
        'number': number,
        'title': title,
        'profile': profile,
        'deliverable': deliverable,
        'steps': [
            {'number': i + 1, 'target': t, 'intent': intent} for i, t in enumerate(targets)
        ],
    }


# =============================================================================
# Path normalization — the comparison's own precondition
# =============================================================================


def test_normalize_strips_leading_dot_slash_and_trailing_separator():
    """``./a/b.py`` and ``a/b.py/`` name the same file as ``a/b.py``."""
    assert normalize_declared_path('./a/b.py') == 'a/b.py'
    assert normalize_declared_path('a/b.py/') == 'a/b.py'
    assert normalize_declared_path('  ./a/b.py  ') == 'a/b.py'


def test_normalize_preserves_a_leading_dot_directory():
    """A dotfile tree keeps its leading dot — only ``./`` prefixes are stripped."""
    assert normalize_declared_path('.claude/skills/x/SKILL.md') == '.claude/skills/x/SKILL.md'


# =============================================================================
# Projection closure — declared write path that no task targets
# =============================================================================


def test_projection_gap_when_a_declared_write_is_never_targeted():
    """A declared write path no step names is reported, even though it exists."""
    deliverable = _deliverable(1, affected=[_REAL_A, _REAL_B])
    tasks = [_task(1, 1, [_REAL_A])]

    gaps = compute_projection_gaps(deliverable, tasks)

    assert gaps == [_REAL_B], 'the unprojected declared write must be named, positively'


def test_projection_closed_when_every_declared_write_is_targeted():
    """A fully projected write-set yields no gap."""
    deliverable = _deliverable(1, affected=[_REAL_A, _REAL_B])
    tasks = [_task(1, 1, [_REAL_A]), _task(2, 1, [_REAL_B])]

    assert compute_projection_gaps(deliverable, tasks) == []


def test_projection_ignores_read_intent_declarations():
    """A ``read`` declaration is not a write, so it is never owed a step."""
    deliverable = {
        'number': 1,
        'title': 'D',
        'affected_files': [
            {'path': _REAL_A, 'intent': 'write-replace'},
            {'path': _REAL_B, 'intent': 'read'},
        ],
        'survey_scope': [],
        'mutation_scope': [],
    }

    assert compute_projection_gaps(deliverable, [_task(1, 1, [_REAL_A])]) == []


def test_projection_covers_the_mutation_scope_of_a_survey_deliverable():
    """``Files expected to mutate:`` is a write-set member and is owed a step.

    This is the survey-scope deliverable authored exactly as the outline
    standard mandates — no ``Affected files:`` list at all. Before the write-set
    unioned the mutation scope, this deliverable's write-set was EMPTY, so the
    projection had nothing to be incomplete about and the gap was unreportable
    by construction.
    """
    deliverable = _deliverable(1, survey=[_REAL_A], mutate=[_REAL_B])

    gaps = compute_projection_gaps(deliverable, [_task(1, 1, [])])

    assert gaps == [_REAL_B]


# =============================================================================
# Referrer closure — step target the deliverable never declared
# =============================================================================


def test_referrer_gap_when_a_step_targets_an_undeclared_path():
    """A step target absent from every declared heading is reported."""
    deliverable = _deliverable(1, affected=[_REAL_A])

    gaps = compute_referrer_gaps(_task(1, 1, [_REAL_B]), declared_paths(deliverable))

    assert gaps == [_REAL_B]


def test_referrer_accepts_a_target_declared_under_files_to_survey():
    """The survey pool is part of the declared surface, so a read step is covered."""
    deliverable = _deliverable(1, survey=[_REAL_B], mutate=[_REAL_A])

    assert compute_referrer_gaps(_task(1, 1, [_REAL_B]), declared_paths(deliverable)) == []


def test_referrer_reports_a_target_covered_only_by_a_glob():
    """A step target a declared PATTERN would match is still reported.

    The step is where a pattern must have become a concrete enumerated path.
    Accepting glob coverage here would let ``{declared scope wide, write-set
    narrow}`` pass as closure — the exact pair the reconciliation check exists
    to surface.

    The fixture pins the precondition it depends on: the pattern really does
    match the target under ``fnmatch``, so a referrer closure that matched
    patterns would fall silent here. Without that assertion the test would pass
    for the uninteresting reason that the glob was irrelevant to the target.
    """
    pattern = 'marketplace/bundles/plan-marshall/skills/*/SKILL.md'
    assert fnmatch(_REAL_A, pattern), 'precondition: the declared glob matches the step target'
    deliverable = _deliverable(1, survey=[pattern])

    gaps = compute_referrer_gaps(_task(1, 1, [_REAL_A]), declared_paths(deliverable))

    assert gaps == [_REAL_A]


def test_projection_leaves_a_declared_glob_to_the_reconciliation_check():
    """A declared glob in the write-set is not reported as an unprojected write.

    A pattern cannot be a step target, so reporting it as "no task targets this"
    would emit a finding on every survey-scope deliverable that declares a
    pattern — noise the author cannot act on. The claim-versus-index check owns
    patterns; the projection check owns literal paths.
    """
    deliverable = _deliverable(1, mutate=[_STANDARDS_GLOB, _REAL_A])

    gaps = compute_projection_gaps(deliverable, [_task(1, 1, [_REAL_A])])

    assert gaps == []


# =============================================================================
# Claim-versus-index closure — a declared glob against the enumerated list
# =============================================================================


def test_declared_glob_wider_than_the_enumeration_is_reported():
    """A declared glob matching files the deliverable never enumerates fires.

    The expected hit set is re-derived from the tree at assert time rather than
    written as a literal, so the assertion cannot drift from what the glob
    actually matches.
    """
    expected_hits = _independent_expansion(_STANDARDS_GLOB)
    assert expected_hits, 'positive-population guard: the glob must match something'
    deliverable = _deliverable(1, survey=[_STANDARDS_GLOB], mutate=[_REAL_A])

    gaps, population = check_declared_scope_reconciliation([deliverable], PROJECT_ROOT)

    assert population['globs_declared'] == 1
    assert population['globs_expanded'] == 1
    assert population['matches_enumerated'] == len(expected_hits)
    assert [g['kind'] for g in gaps] == ['claim_vs_index']
    # Every KNOWN hit is named — the positive half of the population guard, which
    # a cardinality assertion alone cannot express.
    for hit in expected_hits:
        assert hit in gaps[0]['detail'], hit


def test_declared_glob_fully_enumerated_is_closed():
    """When every match is also enumerated, the claim and the index agree."""
    expected_hits = _independent_expansion(_STANDARDS_GLOB)
    assert expected_hits, 'positive-population guard: the glob must match something'
    deliverable = _deliverable(1, survey=[_STANDARDS_GLOB, *expected_hits])

    gaps, population = check_declared_scope_reconciliation([deliverable], PROJECT_ROOT)

    assert gaps == []
    assert population['globs_expanded'] == 1
    assert population['matches_enumerated'] == len(expected_hits)
    assert population['population_complete'] is True


def test_unexpandable_glob_is_reported_not_silently_zero():
    """An absolute pattern is an UNMEASURED scope, never an empty one."""
    deliverable = _deliverable(1, survey=['/etc/*.conf'])

    gaps, population = check_declared_scope_reconciliation([deliverable], PROJECT_ROOT)

    assert [g['kind'] for g in gaps] == ['unexpandable_glob']
    assert population['globs_unexpandable'] == 1
    assert population['globs_expanded'] == 0
    assert population['population_complete'] is False


def test_a_home_relative_glob_is_unmeasured_not_empty():
    """``~/…`` raises NOTHING and matches nothing — the silent half of the guard.

    An absolute pattern raises inside ``Path.glob`` and is caught either way, so
    guarding it is a statement of intent. ``~`` is different: pathlib treats it
    as an ordinary directory name, so the expansion succeeds, returns zero
    matches, and would be reported as a measured-empty scope. Only the explicit
    guard separates that from a pattern that genuinely matches nothing.
    """
    assert list(PROJECT_ROOT.glob('~/x/*.py')) == [], 'precondition: pathlib does not raise here'

    expansion = expand_declared_glob('~/x/*.py', PROJECT_ROOT)

    assert expansion.expandable is False
    _gaps, population = check_declared_scope_reconciliation(
        [_deliverable(1, survey=['~/x/*.py'])], PROJECT_ROOT
    )
    assert population['globs_unexpandable'] == 1
    assert population['population_complete'] is False


def test_expand_declared_glob_reports_expandability_separately_from_emptiness():
    """A pattern matching nothing and a pattern that cannot expand differ."""
    empty = expand_declared_glob(
        'marketplace/bundles/plan-marshall/skills/manage-tasks/no-such-dir/*.md', PROJECT_ROOT
    )
    absolute = expand_declared_glob('/etc/*.conf', PROJECT_ROOT)

    assert empty.matches == [] and empty.expandable is True and empty.truncated is False
    assert empty.directories_matched == 0
    assert absolute.matches == [] and absolute.expandable is False


# =============================================================================
# Population — the positive-population guard (D3)
# =============================================================================


def test_population_is_incomplete_when_a_task_names_a_missing_deliverable():
    """``detector_population ⊇ fix_set_population`` fails loudly, not silently."""
    deliverables = [_deliverable(1, affected=[_REAL_A])]
    tasks = [_task(1, 1, [_REAL_A]), _task(2, 99, [_REAL_B])]

    _gaps, population = check_declared_set_closure(tasks, deliverables)

    assert population['population_complete'] is False
    assert population['unmapped_tasks'] == [2]


def test_population_reports_what_was_actually_scanned():
    """A non-empty scanned population is asserted positively, not inferred."""
    deliverables = [_deliverable(1, affected=[_REAL_A], survey=[_REAL_B])]
    tasks = [_task(1, 1, [_REAL_A, _REAL_B])]

    _gaps, population = check_declared_set_closure(tasks, deliverables)

    assert population['deliverables_scanned'] == 1
    assert population['declared_paths_scanned'] == 2
    assert population['tasks_scanned'] == 1
    assert population['step_targets_scanned'] == 2
    assert population['population_complete'] is True


def test_verification_tasks_are_excluded_from_the_scanned_population():
    """A verification task's steps are commands, not paths, so it is skipped."""
    deliverables = [_deliverable(1, affected=[_REAL_A])]
    tasks = [_task(1, 1, [_REAL_A]), _task(2, 1, ['./pw verify'], profile='verification')]

    gaps, population = check_declared_set_closure(tasks, deliverables)

    assert gaps == []
    assert population['tasks_scanned'] == 1


# =============================================================================
# End-to-end through the mechanical Q-Gate
# =============================================================================


def _write_task_file(task_dir: Path, task: dict[str, Any]) -> None:
    task_dir.mkdir(parents=True, exist_ok=True)
    record = {
        'number': task['number'],
        'title': task['title'],
        'status': 'pending',
        'profile': task['profile'],
        'domain': 'plan-marshall-plugin-dev',
        'origin': 'plan',
        'deliverable': task['deliverable'],
        'depends_on': [],
        'skills': ['plan-marshall:manage-tasks'],
        'description': '',
        'steps': [{**s, 'status': 'pending'} for s in task['steps']],
        'verification': {'commands': [], 'criteria': '', 'manual': False},
    }
    (task_dir / f'TASK-{task["number"]:03d}.json').write_text(
        json.dumps(record, indent=2), encoding='utf-8'
    )


def _write_outline(plan_dir: Path, body: str) -> None:
    (plan_dir / 'solution_outline.md').write_text(
        '# Solution Outline\n\n## Deliverables\n\n' + body, encoding='utf-8'
    )


def test_qgate_reports_closure_gap_while_files_exist_stays_clean(plan_context):
    """Every declared path resolves, and the set is still incomplete.

    This is the fixture the plan names: existence passes, closure does not. The
    steps carry ``read`` intent, so ``files_exist`` runs its existence predicate
    over real files and passes on the merits — its zero is a measured verdict,
    not the skip ``write-replace`` would have produced. The companion test below
    proves that zero can move.
    """
    plan_dir = plan_context.plan_dir_for('closure-e2e')
    _write_outline(
        plan_dir,
        f'### 1. Widen the sweep\n\n'
        f'**Affected files:**\n- `{_REAL_A}` (write-replace)\n- `{_REAL_B}` (write-replace)\n',
    )
    _write_task_file(plan_dir / 'tasks', _task(1, 1, [_REAL_A]))

    result = cmd_qgate_mechanical(Namespace(plan_id='closure-e2e', no_emit=True))

    assert result['checks']['files_exist']['failed'] == 0
    assert result['checks']['declared_set_closure']['failed'] == 1
    assert result['population']['declared_set_closure']['population_complete'] is True


def test_qgate_reads_the_survey_scope_pair_from_the_outline(plan_context):
    """A survey-scope deliverable's declaration reaches the mechanical Q-Gate.

    Authored per ``outline-workflow-detail.md`` — the two disjoint fields and no
    ``Affected files:`` list. The mutation-scope path is unprojected, so the
    closure fires; before the parser read these headings the deliverable's
    declared surface was empty and nothing could fire at all.
    """
    plan_dir = plan_context.plan_dir_for('closure-survey')
    _write_outline(
        plan_dir,
        f'### 1. Survey the standards and classify each\n\n'
        f'**Files to survey:**\n- `{_REAL_A}`\n\n'
        f'**Files expected to mutate:**\n- `{_REAL_B}`\n',
    )
    _write_task_file(plan_dir / 'tasks', _task(1, 1, [_REAL_A]))

    result = cmd_qgate_mechanical(Namespace(plan_id='closure-survey', no_emit=True))

    population = result['population']['declared_set_closure']
    assert population['declared_paths_scanned'] == 2, 'the survey pair must be scanned'
    assert result['checks']['declared_set_closure']['failed'] == 1


def test_files_exist_zero_is_load_bearing_not_vacuous(plan_context):
    """The end-to-end fixture's ``files_exist: 0`` moves when the paths vanish.

    Without this, ``files_exist: 0`` could not be told from the skip that
    ``write-replace`` intent produces, and the "existence passes, closure does
    not" claim would be unearned. The SAME shape as the fixture above, with the
    declared and targeted paths swapped for absent ones: the existence check
    must now report, which is what makes its zero elsewhere a measurement.
    """
    plan_dir = plan_context.plan_dir_for('closure-files-exist-control')
    absent_a, absent_b = 'src/ABSENT-A.java', 'src/ABSENT-B.java'
    assert not (PROJECT_ROOT / absent_a).exists(), 'precondition: the control path must be absent'
    _write_outline(
        plan_dir,
        f'### 1. Widen the sweep\n\n'
        f'**Affected files:**\n- `{absent_a}` (write-replace)\n- `{absent_b}` (write-replace)\n',
    )
    _write_task_file(plan_dir / 'tasks', _task(1, 1, [absent_a]))

    result = cmd_qgate_mechanical(Namespace(plan_id='closure-files-exist-control', no_emit=True))

    assert result['checks']['files_exist']['failed'] == 1
    assert result['checks']['declared_set_closure']['failed'] == 1


def test_a_declared_glob_escaping_the_repo_is_unmeasured_not_empty():
    """An escaping pattern is rejected, and the escape target really exists.

    The precondition is asserted rather than assumed: the pattern must resolve
    to a directory that is BOTH outside the repository and populated, or the
    test would pass for the uninteresting reason that there was nothing out
    there to find either way. ``PROJECT_ROOT`` is three levels below ``/``, so
    ``../../../etc`` is ``/etc``.

    Left unnormalised, ``Path.glob`` walks out of the repository and returns
    nothing, so a scope nothing examined reports a clean zero — the very defect
    this module reports on outlines, committed by the module itself.
    """
    escape = '../../../etc/*.conf'
    outside = (PROJECT_ROOT / '../../../etc').resolve()
    assert outside == Path('/etc'), 'precondition: the pattern must leave the repo'
    assert list(outside.glob('*.conf')), 'precondition: the escape target must be populated'

    expansion = expand_declared_glob(escape, PROJECT_ROOT)
    assert expansion.expandable is False

    deliverable = _deliverable(1, survey=[escape])
    gaps, population = check_declared_scope_reconciliation([deliverable], PROJECT_ROOT)

    assert [g['kind'] for g in gaps] == ['unexpandable_glob']
    assert population['globs_unexpandable'] == 1
    assert population['population_complete'] is False


def test_an_in_repo_dotdot_glob_expands_to_canonical_paths():
    """``doc/../marketplace/…`` and the plain path name the same file.

    Without normalisation the expansion returned the literal ``doc/../…``
    spelling, which compares unequal to the canonical declaration — so the check
    manufactured a claim_vs_index finding against a path the deliverable HAD
    enumerated.
    """
    canonical = sorted(
        p.relative_to(PROJECT_ROOT).as_posix() for p in PROJECT_ROOT.glob(_STANDARDS_GLOB)
    )
    assert canonical, 'positive-population guard: the glob must match something'
    detoured = 'doc/../' + _STANDARDS_GLOB

    expansion = expand_declared_glob(detoured, PROJECT_ROOT)

    assert expansion.matches == canonical
    gaps, _population = check_declared_scope_reconciliation(
        [_deliverable(1, survey=[detoured, *canonical])], PROJECT_ROOT
    )
    assert gaps == []


def test_a_directory_only_scope_is_unmeasured_not_a_clean_zero():
    """``marketplace/bundles/*/`` matches only directories, which is/was dropped.

    Every match falling to the ``is_file()`` filter left an empty file list and
    a ``population_complete: True`` — a measured-looking verdict over a scope
    that was never reconciled.
    """
    expansion = expand_declared_glob('marketplace/bundles/*/', PROJECT_ROOT)
    assert expansion.matches == []
    assert expansion.directories_matched > 0, 'precondition: the pattern must match directories'

    gaps, population = check_declared_scope_reconciliation(
        [_deliverable(1, survey=['marketplace/bundles/*/'])], PROJECT_ROOT
    )

    assert [g['kind'] for g in gaps] == ['unexpandable_glob']
    assert population['directories_matched'] > 0
    assert population['population_complete'] is False


def test_a_declaration_normalizing_to_nothing_is_dropped():
    """``./`` is a non-empty string that normalizes to ``''``.

    Guarding the raw string let the empty path into the comparison, where it was
    reported as a gap named ``''``.
    """
    assert normalize_declared_path('./') == ''
    deliverable = _deliverable(1, survey=['./'], mutate=[_REAL_A])

    assert declared_paths(deliverable) == {_REAL_A}
    assert compute_referrer_gaps(_task(1, 1, ['./']), declared_paths(deliverable)) == []


def test_truncated_enumeration_is_disclosed_and_bounds_the_hit_list(monkeypatch):
    """A capped expansion is a LOWER BOUND, and says so.

    The match ceiling and the hit-naming cap are both lowered here rather than
    building a fixture large enough to reach the shipped values — the property
    under test is the disclosure, not the constants. The glob is asserted to
    match MORE than the lowered ceiling, so the cap is genuinely reached.
    """
    monkeypatch.setattr(_closure, '_MAX_GLOB_MATCHES', 1)
    all_hits = _independent_expansion(_MULTI_HIT_GLOB)
    assert len(all_hits) > 1, 'precondition: the glob must exceed the lowered ceiling'

    expansion = expand_declared_glob(_MULTI_HIT_GLOB, PROJECT_ROOT)
    assert expansion.truncated is True
    assert len(expansion.matches) == 1

    gaps, population = check_declared_scope_reconciliation(
        [_deliverable(1, survey=[_MULTI_HIT_GLOB])], PROJECT_ROOT
    )
    assert population['enumeration_truncated'] is True
    assert population['population_complete'] is False
    assert 'LOWER BOUND' in gaps[0]['detail']


def test_the_hit_list_names_a_bounded_set_and_discloses_the_remainder(monkeypatch):
    """Above the naming cap the finding still states the TOTAL.

    A silent truncation would read as "these are the hits"; the ``+N more``
    summary and the unenumerated count keep the finding honest about its own
    elision.
    """
    monkeypatch.setattr(_closure, '_MAX_HITS_NAMED', 1)
    hits = _independent_expansion(_MULTI_HIT_GLOB)
    assert len(hits) > 1, 'precondition: the glob must exceed the lowered naming cap'

    gaps, _population = check_declared_scope_reconciliation(
        [_deliverable(1, survey=[_MULTI_HIT_GLOB])], PROJECT_ROOT
    )

    assert len(gaps) == 1
    detail, title = gaps[0]['detail'], gaps[0]['title']
    assert f'+{len(hits) - 1} more' in detail
    assert f'{len(hits)} of them appear in no declared list' in detail
    # ⛔ The TITLE must state the same TOTAL, not the count it managed to name.
    # This is the only place the two diverge — below the cap they are equal, so
    # a fixture there cannot tell a total from a named count, and a mutant
    # substituting one for the other survives it.
    assert f'{len(hits)} fewer file(s)' in title
    assert f'{len(hits) - 1} fewer file(s)' not in title


def test_the_finding_names_every_hit_and_states_the_true_total():
    """The hit list and the title are pinned against a REAL multi-hit glob.

    Both other claim-vs-index tests are blind to this: one uses a glob that
    expands to a single file (a population of one cannot see a slicing bug), and
    the other lowers ``_MAX_HITS_NAMED`` by monkeypatch (which cannot see a
    hard-coded slice). Two mutants survived the whole suite because of it —
    ``unenumerated[:1]`` for the named list, and a title reporting the NAMED
    count where it claims the total.

    The title's number is the disclosure-integrity claim D2 makes about its own
    finding text, so it is asserted against an independently derived total
    rather than against the length of whatever the finding chose to name.
    """
    hits = _independent_expansion(_MULTI_HIT_GLOB)
    assert len(hits) > 2, 'precondition: more hits than a slice-of-1 mutant would name'
    assert len(hits) <= _closure._MAX_HITS_NAMED, (
        'precondition: below the naming cap, so every hit must appear un-elided'
    )

    gaps, _population = check_declared_scope_reconciliation(
        [_deliverable(1, survey=[_MULTI_HIT_GLOB])], PROJECT_ROOT
    )

    assert len(gaps) == 1
    detail, title = gaps[0]['detail'], gaps[0]['title']
    for hit in hits:
        assert hit in detail, hit
    assert 'more, not named here' not in detail, 'below the cap nothing is elided'
    # The TOTAL, not the named count — the two coincide only below the cap, and
    # a mutant substituting one for the other is what this pins.
    assert f'{len(hits)} fewer file(s)' in title
    assert f'{len(hits)} of them appear in no declared list' in detail


def test_population_publishes_member_identities_not_only_counts():
    """The positive-population assertion needs the members, not the cardinality.

    A count answers "was the population non-empty?". Only the members answer
    "did it contain the element at risk?" — the half of the guard the plan asks
    for and a count cannot express.
    """
    deliverables = [_deliverable(1, affected=[_REAL_A], survey=[_REAL_B])]

    _gaps, population = check_declared_set_closure([_task(1, 1, [_REAL_A])], deliverables)

    assert population['scanned_paths'] == sorted([_REAL_A, _REAL_B])
    assert population['scanned_paths_truncated'] is False


def test_scanned_paths_truncation_is_disclosed_not_silent(monkeypatch):
    """The published-member cap says when it bit. (B1)

    ``scanned_paths`` is D3's own discharge mechanism: it carries the member
    identities a positive-population assertion needs. A cap applied silently
    would present a PARTIAL population as a complete one — the plan's own defect
    class, reached inside the field that exists to prevent it.

    The cap is lowered rather than building a 200-path fixture; the property
    under test is the disclosure, not the constant. The unlowered case is
    asserted alongside it, so a mutant hard-coding either verdict is caught.
    """
    deliverable = _deliverable(1, affected=[_REAL_A, _REAL_B])
    tasks = [_task(1, 1, [_REAL_A, _REAL_B])]

    _gaps, full = check_declared_set_closure(tasks, [deliverable])
    assert full['scanned_paths_truncated'] is False
    assert len(full['scanned_paths']) == 2

    monkeypatch.setattr(_closure, '_MAX_SCANNED_PATHS_PUBLISHED', 1)
    _gaps, capped = check_declared_set_closure(tasks, [deliverable])

    assert capped['scanned_paths_truncated'] is True
    assert len(capped['scanned_paths']) == 1
    # The COUNT is unaffected by the publication cap — a reader can still tell
    # how large the population was, which is what makes the cap a disclosure
    # rather than a shrunken population.
    assert capped['declared_paths_scanned'] == 2


def test_a_bracket_pattern_is_not_treated_as_a_declared_glob():
    """``[`` is deliberately outside the metacharacter set. (B5)

    A character class is legal glob syntax but vanishingly rare in a declared
    scope and common in prose, so reading a prose bracket as a pattern would
    manufacture findings. The decision is documented at
    ``_GLOB_METACHARACTERS``; this pins it, so a future widening has to change a
    test rather than only a comment.
    """
    assert is_glob('src/a[0-9].py') is False
    assert is_glob('src/*.py') is True
    assert is_glob('src/a?.py') is True

    # A bracketed path is therefore a LITERAL declaration: it takes part in the
    # projection closure (which skips patterns) rather than the reconciliation.
    deliverable = _deliverable(1, mutate=['src/a[0-9].py'])
    assert compute_projection_gaps(deliverable, [_task(1, 1, [])]) == ['src/a[0-9].py']


def test_a_holistic_task_is_exempt_and_not_counted_as_scanned():
    """``deliverable == 0`` is EXEMPT — neither unmapped nor scanned.

    ``_check_coverage`` already whitelists the sentinel ("do not flag as
    orphan"), and the closure pass must agree: a holistic task belongs to no
    deliverable, so no declared set exists to check it against, and counting it
    as unmapped would flip ``ambiguous`` on a correctly-shaped plan.

    ⛔ But exemption must not INFLATE the scanned population. An earlier version
    of this carve-out skipped the closure after the accounting had already
    counted the task's targets, so the population claimed three targets scanned
    while one entered the check — a ``population_complete: True`` over a surface
    the closure never examined, which is the defect this module reports on
    outlines. The three counts are asserted together for exactly that reason: a
    regression that re-inflates them changes numbers this test reads.
    """
    deliverables = [_deliverable(1, affected=[_REAL_A])]
    mapped = _task(1, 1, [_REAL_A])
    holistic = _task(2, 0, ['src/undeclared-a.py', 'src/undeclared-b.py'])

    gaps, population = check_declared_set_closure([mapped, holistic], deliverables)

    assert gaps == [], 'the holistic task owes no referrer closure'
    assert population['holistic_tasks'] == [2], 'the exemption is published, not silent'
    assert population['unmapped_tasks'] == []
    # Only the mapped task and its single target entered the closure.
    assert population['tasks_scanned'] == 1
    assert population['step_targets_scanned'] == 1
    assert population['population_complete'] is True


def test_ambiguous_flips_when_the_closure_population_is_incomplete(plan_context):
    """The mechanism q-gate-validation.md §2.9a names as discharging D3.

    ``population_complete: False`` MUST reach the caller as ``ambiguous``, or the
    normative line `detector_population ⊇ fix_set_population` is documentation
    with nothing behind it: the orchestrator would read a clean mechanical pass
    over a population the check could not fully scan.
    """
    plan_dir = plan_context.plan_dir_for('closure-ambiguous')
    _write_outline(
        plan_dir,
        f'### 1. One deliverable\n\n**Affected files:**\n- `{_REAL_A}` (read)\n',
    )
    _write_task_file(plan_dir / 'tasks', _task(1, 1, [_REAL_A]))
    # TASK-002 names deliverable 99, which the outline does not contain.
    _write_task_file(plan_dir / 'tasks', _task(2, 99, [_REAL_A]))

    result = cmd_qgate_mechanical(Namespace(plan_id='closure-ambiguous', no_emit=True))

    assert result['population']['declared_set_closure']['population_complete'] is False
    assert result['population_complete'] is False
    assert result['ambiguous'] is True


def test_closure_check_runs_under_the_surgical_scope_bypass_shape(plan_context):
    """ADVERSARIAL: a plan shaped exactly like the Step 8b bypass is still checked.

    phase-4-plan's B2 predicate — ``scope_estimate == surgical`` AND at most two
    declared affected files — suppresses the DISPATCHED q-gate-validation. This
    fixture satisfies BOTH conjuncts, and asserts the closure check still runs
    and still fires, because it lives in Step 8, which has no bypass. A closure
    claim is a hint; it may never be a licence to skip the check that would test
    it.

    Both conjuncts are asserted as PRECONDITIONS, re-derived from the artifacts
    the fixture just wrote — the persisted ``scope_estimate`` and the declared
    cardinality the predicate actually reads. Without that, the fixture could
    drift out of the bypass shape and the test would keep passing while
    verifying nothing about the bypass at all.
    """
    plan_dir = plan_context.plan_dir_for('closure-bypass')
    (plan_dir / 'references.json').write_text(
        json.dumps({'scope_estimate': 'surgical'}), encoding='utf-8'
    )
    _write_outline(
        plan_dir,
        f'### 1. Surgical fix\n\n'
        f'**Metadata:**\n- change_type: bug_fix\n\n'
        f'**Affected files:**\n- `{_REAL_A}` (read)\n- `{_REAL_B}` (write-replace)\n',
    )
    _write_task_file(plan_dir / 'tasks', _task(1, 1, [_REAL_A]))

    # Precondition 1 — the persisted scope_estimate the B2 predicate reads.
    references = json.loads((plan_dir / 'references.json').read_text(encoding='utf-8'))
    assert references['scope_estimate'] == 'surgical'

    # Precondition 2 — the deduplicated declared cardinality, re-derived through
    # the SAME parser phase-4-plan uses, never by counting bullet lines.
    #
    # This fixture declares only `Affected files:`, so the flat count and the
    # widened declared-surface count B2 actually reads coincide here. They do
    # NOT coincide for a survey-scope deliverable, which is why the surface is
    # summed explicitly rather than reading `affected_files` alone: a fixture
    # that later grew a survey pair would otherwise keep asserting a number the
    # predicate no longer uses.
    outline = (plan_dir / 'solution_outline.md').read_text(encoding='utf-8')
    deliverables = extract_deliverables(parse_document_sections(outline)['deliverables'])
    affected_files_count = len(
        {
            entry['path']
            for d in deliverables
            for field in ('affected_files', 'survey_scope', 'mutation_scope')
            for entry in d[field]
        }
    )
    assert affected_files_count <= 2, 'precondition: the fixture must satisfy the bypass predicate'

    result = cmd_qgate_mechanical(Namespace(plan_id='closure-bypass', no_emit=True))

    assert result['checks']['declared_set_closure']['failed'] == 1
