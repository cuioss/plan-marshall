#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""No reachable archive leaves a phase in progress — asserted over a derived population.

This module is the cross-cutting assertion over the combined post-state of
deliverables 2-4. The per-deliverable suites each pin one named case; this one pins
the *property* over a population it derives rather than over cases someone
remembered to write.

Why a derived population rather than a handful of cases
------------------------------------------------------
The defect this plan fixes was invisible to a green suite because the existing
assertion read ``phases[-1]`` — one slot of one case. Any fixed list of cases has
the same weakness in principle: it covers the states its author thought of. The
population here is the full cartesian product of the declared status vocabulary
(``constants.VALID_PHASE_STATUSES``) over a phase list, so every combination of
open / closed / never-started phases is covered by construction, including the
multi-open-phase states that motivated the fix and the pending-tail states that
motivated its other half.

⛔ The population is **built in-fixture**, through production verbs only. It is
never read from a live plan store, and the ``census`` verb added by deliverable 7
does not license such a read here: a test that surveyed real archived plans would
assert over whatever that machine happens to hold, which is neither reproducible
nor a statement about reachable states.

Why the population SIZE is published
------------------------------------
A sweep that enumerated nothing would report zero failures and be indistinguishable
from a clean one. ``test_the_enumerated_population_is_the_full_status_product``
pins the population to its derived size first, so the zero-failure verdict below is
known to have been drawn from a real population.

Why the failure set is compared to an allow-list rather than asserted empty
--------------------------------------------------------------------------
``_KNOWN_BAD`` names the enumerated states the post-condition cannot yet satisfy.
It is currently **empty** — the implementation satisfies every enumerated state. The
sweep asserts the failing set EQUALS the allow-list, which fails in both
directions: a regression appears as an unexpected failure, and an allow-list entry
that has since started passing appears as a stale entry to prune. A known-bad state
is therefore carried explicitly by name and never by loosening the predicate.

Why the matched controls are here
---------------------------------
The sweep's verdict treats a refused archive as a failure, so an archiver that
refused everything could not pass it. That is asserted directly anyway by
``test_a_single_open_phase_plan_still_archives_normally``: without a cell pinning
the ordinary archive to a real success, a reader cannot tell a post-condition that
is *satisfied* from one that is merely *unreachable*. The deliverable-4 refusal pair
is likewise carried as a positive/negative pair, because a split that produced one
code for both conditions would otherwise still look correct from here.

No ``skip``, ``skipif`` or ``xfail`` appears in this module, and
``test/conftest.py``'s ``_SKIP_EXCEPTIONS`` registry is neither consulted nor
modified: every case either holds or fails.
"""

from __future__ import annotations

import itertools
import json
import subprocess
from argparse import Namespace
from pathlib import Path

from _manage_status_transition_fixtures import (
    _seed_early_archive_plan,
    cmd_archive,
    cmd_create,
    cmd_update_phase,
)
from constants import (
    PHASE_STATUS_DONE,
    PHASE_STATUS_IN_PROGRESS,
    PHASE_STATUS_PENDING,
    VALID_PHASE_STATUSES,
)

from conftest import load_script_module

_lifecycle = load_script_module('plan-marshall', 'manage-status', '_cmd_lifecycle.py', '_status_lifecycle_population')

#: The status vocabulary the population is drawn from, read from the declared
#: constant rather than spelled as a literal triple. A status added to the
#: vocabulary therefore widens this sweep automatically instead of leaving a new
#: value silently unexercised.
_STATUS_VOCABULARY: tuple[str, ...] = tuple(sorted(VALID_PHASE_STATUSES))

#: A deliberately SHORT phase list. The archive post-condition is phase-name
#: agnostic — it reads only each phase's status — so three slots already span every
#: structural shape the property is about: zero, one, several and all phases open, a
#: pending tail, a pending phase wedged between closed ones. Three slots over a
#: three-value vocabulary is 27 plans built and archived per sweep; the canonical
#: six-phase list would be 729 for no additional structural coverage.
#:
#: No ``6-finalize`` slot, deliberately: ``cmd_archive``'s blocking-findings gate
#: fires only while ``current_phase == '6-finalize'``, and that gate is a different
#: deliverable's subject. Excluding the name keeps this sweep measuring the phase
#: closure alone. The realistic six-phase shapes are pinned by the named cases in
#: ``test_manage_status_transition_archive.py``.
_PHASES: tuple[str, ...] = ('1-init', '2-refine', '3-outline')

#: Enumerated states whose post-condition is known NOT to hold, each mapped to the
#: reason it is carried. EMPTY: every enumerated state currently satisfies the
#: post-condition. An entry here is a named, reviewable exception — never a reason
#: to weaken the assertion.
_KNOWN_BAD: dict[tuple[str, ...], str] = {}


def _enumerate_states() -> list[tuple[str, ...]]:
    """Every assignment of the status vocabulary across ``_PHASES``.

    All of them are reachable: ``cmd_update_phase`` sets any phase to any declared
    status, and ``cmd_archive`` imposes no precondition on the phase states it is
    handed, so each assignment is a state a plan can genuinely be archived in.
    """
    return list(itertools.product(_STATUS_VOCABULARY, repeat=len(_PHASES)))


def _build_state(plan_id: str, assignment: tuple[str, ...]) -> None:
    """Materialize one enumerated state through production verbs only.

    ``cmd_create`` seeds the phase list (opening phase 0), then one
    ``cmd_update_phase`` per slot drives each phase to its assigned status. Nothing
    is hand-written into ``status.json``.
    """
    cmd_create(
        Namespace(
            plan_id=plan_id,
            title='Archive Open-Phase Population',
            phases=','.join(_PHASES),
            force=False,
        )
    )
    for phase, status in zip(_PHASES, assignment, strict=True):
        cmd_update_phase(Namespace(plan_id=plan_id, phase=phase, status=status))


def _post_condition_failure(assignment: tuple[str, ...], result: dict) -> str | None:
    """Return why the post-condition failed for one case, or ``None`` when it held.

    Three conjuncts, matching the three parts of the archive post-condition: no
    phase remains ``in_progress``, every phase that was ``pending`` is still
    ``pending``, and ``current_phase`` reaches ``complete``. A refused archive is
    itself a failure — the post-condition must be satisfied, not merely unreachable.
    """
    if result.get('status') != 'success':
        return f'archive did not succeed: {result!r}'

    archived = json.loads((Path(result['archived_to']) / 'status.json').read_text(encoding='utf-8'))
    observed = {phase['name']: phase['status'] for phase in archived['phases']}

    still_open = [name for name, status in observed.items() if status == PHASE_STATUS_IN_PROGRESS]
    if still_open:
        return f'phases still in_progress after archive: {still_open!r}'

    was_pending = [phase for phase, status in zip(_PHASES, assignment, strict=True) if status == PHASE_STATUS_PENDING]
    overwritten = [phase for phase in was_pending if observed[phase] != PHASE_STATUS_PENDING]
    if overwritten:
        return f'phases that never started were written: {[(p, observed[p]) for p in overwritten]!r}'

    if archived.get('current_phase') != 'complete':
        return f'current_phase is {archived.get("current_phase")!r}, expected complete'

    return None


def test_the_enumerated_population_is_the_full_status_product():
    """The population is derived from the vocabulary, and its size is pinned.

    Guards the sweep below against the vacuous case: an enumeration that produced
    nothing — or silently produced fewer cases than the vocabulary implies — would
    report zero failures and read as clean.
    """
    population = _enumerate_states()
    expected_size = len(_STATUS_VOCABULARY) ** len(_PHASES)

    assert _STATUS_VOCABULARY, 'the declared status vocabulary is empty'
    assert len(population) == expected_size, (
        f'The population must be the full cartesian product of {len(_STATUS_VOCABULARY)} '
        f'status value(s) over {len(_PHASES)} phase slot(s) = {expected_size}; got {len(population)}.'
    )
    assert len(set(population)) == len(population), 'the enumeration must not repeat a case'
    assert expected_size > 1, 'a single-case population would make the sweep a single example'
    assert set(_STATUS_VOCABULARY) == {PHASE_STATUS_PENDING, PHASE_STATUS_IN_PROGRESS, PHASE_STATUS_DONE}, (
        f'The sweep assumes the three-valued vocabulary it reads from constants; got {_STATUS_VOCABULARY!r}.'
    )


def test_no_reachable_archive_leaves_a_phase_in_progress(plan_context):
    """The property, over every enumerated state: archive closes what ran and only that.

    Builds each state through production verbs, archives it, and records any
    post-condition failure. The failing set must EQUAL ``_KNOWN_BAD`` — so a
    regression surfaces as an unexpected failure and a stale allow-list entry
    surfaces as one to prune.
    """
    population = _enumerate_states()
    assert population, 'empty population — the sweep below would be vacuous'

    failures: dict[tuple[str, ...], str] = {}
    for index, assignment in enumerate(population):
        plan_id = f'archive-population-{index}'
        _build_state(plan_id, assignment)
        result = cmd_archive(Namespace(plan_id=plan_id, dry_run=False, reason=None))
        failure = _post_condition_failure(assignment, result)
        if failure is not None:
            failures[assignment] = failure

    unexpected = sorted(set(failures) - set(_KNOWN_BAD))
    stale = sorted(set(_KNOWN_BAD) - set(failures))
    detail = {assignment: failures[assignment] for assignment in unexpected}

    assert set(failures) == set(_KNOWN_BAD), (
        f'Archive post-condition swept {len(population)} enumerated state(s) '
        f'(population = {len(_STATUS_VOCABULARY)}**{len(_PHASES)}). '
        f'Unexpected failures: {unexpected!r}. '
        f'Allow-list entries that now pass and must be pruned: {stale!r}. '
        f'Failure detail: {detail!r}'
    )


def test_a_single_open_phase_plan_still_archives_normally(plan_context):
    """Matched control: the ordinary one-open-phase archive really does succeed.

    Without this cell, the sweep above is consistent with an archiver whose
    post-condition is *unreachable* rather than satisfied — and a reader cannot tell
    "no phase was left open" from "nothing was ever archived". Here one phase is
    open, it is closed, the pending tail survives, and the plan reaches ``complete``.
    """
    plan_id = 'archive-population-single-open-control'
    _seed_early_archive_plan(plan_id)

    result = cmd_archive(Namespace(plan_id=plan_id, dry_run=False, reason=None))

    assert result['status'] == 'success', f'The ordinary single-open-phase archive must succeed: {result!r}'
    archived = json.loads((Path(result['archived_to']) / 'status.json').read_text(encoding='utf-8'))
    observed = {phase['name']: phase['status'] for phase in archived['phases']}

    assert observed['2-refine'] == PHASE_STATUS_DONE, f'the one open phase must be closed; got {observed!r}'
    assert observed['1-init'] == PHASE_STATUS_DONE, f'an already-closed phase must stay closed; got {observed!r}'
    assert [observed[name] for name in ('3-outline', '4-plan', '5-execute', '6-finalize')] == [
        PHASE_STATUS_PENDING
    ] * 4, f'the never-started tail must survive archive unchanged; got {observed!r}'
    assert archived['current_phase'] == 'complete', archived['current_phase']


def test_the_two_worktree_state_refusals_are_a_distinct_pair(tmp_path: Path, outside_repo_dir: Path):
    """Paired positive/negative control over deliverable 4's refusal split.

    One question — what did the porcelain read find — with two answers that must not
    collapse into one code, because their remedies differ. The pair is what makes
    the split observable: asserting only the unreadable case would pass equally
    against a guard that reported ``worktree_unreadable_at_boundary`` for a
    genuinely dirty tree too.
    """
    repo = tmp_path / 'dirty-wt'
    repo.mkdir()
    subprocess.run(['git', 'init', '-q', '-b', 'main', str(repo)], check=True)
    subprocess.run(['git', '-C', str(repo), 'config', 'user.email', 't@t.test'], check=True)
    subprocess.run(['git', '-C', str(repo), 'config', 'user.name', 'Test'], check=True)
    (repo / 'src.py').write_text('x = 1\n')
    subprocess.run(['git', '-C', str(repo), 'add', '.'], check=True, capture_output=True)
    subprocess.run(['git', '-C', str(repo), 'commit', '-q', '-m', 'init'], check=True, capture_output=True)
    (repo / 'src.py').write_text('x = 2\n')

    dirty = _lifecycle._clean_tree_refusal(
        'population-dirty', {'metadata': {'use_worktree': True, 'worktree_path': str(repo)}}
    )

    # POSITIVE half: the tree WAS read, so the refusal names the dirty condition and
    # carries the enumerated paths that make it actionable.
    assert dirty is not None
    assert dirty['error'] == 'worktree_dirty_at_boundary', dirty
    assert dirty['dirty_files'] == ['src.py'], (
        f'A tree that was read must enumerate what made it dirty; got {dirty!r}.'
    )

    # NEGATIVE half: git status fails, so nothing was read — a different code, and no
    # dirty_files key at all rather than an empty list standing in for a real zero.
    unreadable_path = outside_repo_dir / 'population-not-a-repo'
    unreadable_path.mkdir()
    unreadable = _lifecycle._clean_tree_refusal(
        'population-unreadable', {'metadata': {'use_worktree': True, 'worktree_path': str(unreadable_path)}}
    )

    assert unreadable is not None
    assert unreadable['error'] == 'worktree_unreadable_at_boundary', unreadable
    assert 'dirty_files' not in unreadable, (
        f'An unenumerated tree must publish no dirty_files key; got {unreadable!r}.'
    )

    assert dirty['error'] != unreadable['error'], 'the two conditions must not collapse into one code'
    for refusal in (dirty, unreadable):
        assert _lifecycle.verify_blocks_transition(refusal) is True, (
            f'Both codes must block the transition, or the guard fails open for one; got {refusal!r}.'
        )
