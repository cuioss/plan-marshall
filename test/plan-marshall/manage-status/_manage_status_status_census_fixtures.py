#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Suite for ``manage-status census`` — the main-anchored per-cohort plan census.

Several properties carry this verb, and each needs a shape of test the others cannot
substitute for.

Main-anchoring is decided by where the calling process stands
-------------------------------------------------------------
``cmd_census`` resolves every cohort through
``marketplace_paths.resolve_main_anchored_path``, which names MAIN from any linked
worktree. A cwd-relative resolver (the ``get_plans_dir()`` / ``get_worktree_root()``
family ``cmd_list`` uses) answers differently only when the process is standing
somewhere other than main — so a test that patched a path resolver could not observe
the difference at all: a patched resolver returns whatever the test told it to and
cannot report where the process is. ``TestMainAnchoredFromAWorktreeCwd`` therefore
stages a real ``git init`` main checkout with a real ``git worktree add`` linked
worktree, pins cwd INSIDE the worktree with ``monkeypatch.chdir``, and neutralises
**both** override spellings (``PLAN_BASE_DIR`` unset AND
``file_ops._BASE_DIR_OVERRIDE`` cleared) so the production git-common-dir branch is
the one that runs. ``resolve_main_anchored_path`` and ``_main_checkout_root`` are
never patched — they are the deliverable, not an implementation detail.

Neutralising both spellings is load-bearing rather than belt-and-braces: either one
alone diverts the resolver to its override branch, where the answer comes from a
directory the test named instead of from the repository, and the cwd the test went to
the trouble of pinning would stop mattering.

``unevaluated`` is not zero, and only a matched pair shows it
------------------------------------------------------------
The verb's honesty property is that a cohort it could not enumerate publishes NO
count keys, rather than ``0``. A test asserting only the unevaluated case would pass
just as well against a verb that reported nothing for EVERY cohort — including one
that had enumerated a store perfectly well. ``TestUnevaluatedIsNotZero`` is therefore
a pair differing along one axis, what is at the cohort path:

* a regular FILE at the cohort path ⇒ ``iterdir`` raises ``NotADirectoryError``, the
  cohort was never enumerated ⇒ ``coverage: unevaluated`` with ``population`` ABSENT;
* the cohort directory genuinely absent, anchor resolved ⇒ it was enumerated and
  holds nothing ⇒ ``coverage: complete`` with ``population: 0``.

The second cell is the half that gives the first its meaning: it is the only place a
``0`` population is legitimate, so it pins the verb to publishing a real figure where
one was actually measured.

The open-phase predicate is the status set, never the loop-back marker
---------------------------------------------------------------------
``TestOpenPhaseRecords`` pairs a record holding two ``in_progress`` phases (which must
be reported, with BOTH names) against a record whose phases are all ``done`` but which
still carries ``metadata.loop_back_reentry`` (which must not be). The marker records
that a loop-back was SCHEDULED, which is neither necessary nor sufficient for a phase
being left open; the control pins the predicate to ``phases[]`` status rather than to
the refuted marker.

An entry nobody could examine is a shortfall, not a skip
--------------------------------------------------------
The membership probe (``is_dir`` plus the ``status.json`` presence check) can itself
fail, on either level of the walk: a cohort entry, or a worktree entry one level up.
``TestAnUnexaminableEntryIsCredited`` pins both to ``partial`` with a non-zero
``unreadable_count``, against a control holding the identical readable tree MINUS the
unexaminable entry, which must still report ``complete`` with ``unreadable_count: 0``.
The control is what gives the positives their meaning: without it they pass equally
against a verb that degrades every cohort it is ever handed to ``partial``.

Its ``deny_probe`` fixture emulates **Python 3.14**: ``Path.stat`` raises ``EACCES`` for
the named entry while ``is_dir`` / ``is_file`` return ``False`` for it, which is the
3.14 predicate contract. The injection has to sit where production probes, or the cells
pass while testing nothing — and pinning the predicates to their 3.14 answer is what
makes the class fail on today's interpreter too if production ever reverts to them.

``open_phase_count`` names phases, not plans
--------------------------------------------
``_scan_plan_container`` emits one record per PLAN, so a count taken over the records
reads correctly for every single-open-phase plan and under-reports exactly the
multi-open-phase ones — the loop-back state (``5-execute`` and ``6-finalize`` both
``in_progress``) this verb exists to surface. ``TestOpenPhaseCountNamesPhasesNotPlans``
holds the plan count fixed at one and varies only the open phases inside it, so a
passing verdict cannot come from the two figures coinciding, and covers both
accumulators — the single-container cohorts and the worktree cohort sum independently.

A member whose phases will not read is a member, and a shortfall
----------------------------------------------------------------
``TestUnexaminablePhasesDegradeTheCohort`` covers the third shortfall kind, one level
in from the other two: the ``status.json`` parsed — so the directory IS an established
plan and belongs in ``population`` — but a phase row is unreadable, so the open-phase
SET could not be determined. Publishing ``open_phase_count`` over such a record as
though it had been read is the same false zero in miniature. Both cohorts that
accumulate counts (single-container and worktree) get their own cell, because they
sum independently, and the matched control is the identical tree minus the affected
member.

The affected member's readable row is ``in_progress``, so the cells also exercise the
RETENTION path: an open phase the scan positively established survives an unexaminable
phase list, and the assertion locates that record by the broken plan's own id rather
than counting — a ``done`` row would leave the count satisfiable by the readable
sibling alone, and the retention would go untested. The class additionally carries a
row whose ``name`` is missing: such a row would be classified open on its status alone
and rendered as the phase named ``''`` on a cohort still claiming ``complete``, so it
must degrade the cohort and appear in no record at all.

``worktrees`` is one scalar with two consumers
----------------------------------------------
``TestTheWorktreeSegmentHasOneDefinition`` pins the single definition by identity and
then pins that the census actually keys on it — an identity assertion alone would pass
against a builder that imported the name and ignored it. Its second behavioural cell
deliberately asserts a CORRECT zero over a store placed outside the composed path: the
point is that that zero is byte-identical to the one a divergent spelling would
produce, which is the whole reason the scalar has a single home.

Cohorts are counted separately, never blended
---------------------------------------------
``TestCohortsAreCountedSeparately`` gives the three stores deliberately DIFFERENT
populations and open-phase counts, so a row carrying another cohort's figure — or the
sum of all three — fails. Equal populations would make a blended total indistinguishable
from three correct ones.

The override-anchored fixture and the real-geometry one are both deliberate: the
real-git class asserts the production anchor (``anchor: main``), and the override-based
classes additionally pin the second anchor label (``anchor: override``), which is the
branch every fixture-driven caller in the suite takes.
"""

from __future__ import annotations

import json
import subprocess
from argparse import Namespace
from pathlib import Path
from typing import Any

import pytest

from conftest import load_script_module

#: The script under test, hoisted as three module-level constants and passed as NAMED
#: positionals rather than star-unpacked from a tuple: the loader-contract guard
#: resolves each registration statically, and an unpacking leaves the script position
#: unreadable to it. ``register=False`` publishes nothing in ``sys.modules`` — this
#: suite only needs the returned object, and ``_status_query`` is imported plainly
#: elsewhere in the tree, so publishing it here would displace that copy.
_BUNDLE = 'plan-marshall'
_SKILL = 'manage-status'
_SCRIPT = '_status_query.py'

status_query = load_script_module(_BUNDLE, _SKILL, _SCRIPT, register=False)

_MAIN_PLAN = 'main-resident-plan'
_WT_PLAN = 'worktree-resident-plan'

#: A FIXED archive date, deliberately not "today". ``cmd_archive`` writes the archive
#: destination as ``{YYYY-MM-DD}-{plan_id}``, so pinning an arbitrary past date shows
#: the census reports the directory name it FOUND rather than one it recomputed.
_ARCHIVE_DATE = '2026-01-15'

#: The one entry whose membership probe is made to fail. Named rather than positional so
#: every other entry in the same tree keeps the real probe, which is what confines the
#: injected denial to a single axis.
_UNEXAMINABLE = 'denied-entry'

#: The phase left ``in_progress`` on the member whose phase LIST is unexaminable. The
#: scan establishes it positively and RETAINS it, so it is the name the retained record
#: must carry. The cells below reach that record by the plan's id rather than by this
#: name, because a sibling plan in the same fixture legitimately holds the same phase
#: open — a name-only lookup would be satisfied by the wrong record.
_RETAINED_OPEN_PHASE = '5-execute'


def _write_plan(plan_dir: Path, phases: dict[str, str], metadata: dict[str, Any] | None = None) -> Path:
    """Seed one plan directory carrying a readable ``status.json``.

    ``phases`` maps phase name to status, in insertion order, so a cell can state
    exactly which phases it expects reported as open.
    """
    plan_dir.mkdir(parents=True)
    document: dict[str, Any] = {
        'title': plan_dir.name,
        'current_phase': next(iter(phases), 'unknown'),
        'phases': [{'name': name, 'status': status} for name, status in phases.items()],
    }
    if metadata is not None:
        document['metadata'] = metadata
    (plan_dir / 'status.json').write_text(f'{json.dumps(document)}\n')
    return plan_dir


def _write_unreadable_phases_plan(plan_dir: Path) -> Path:
    """Seed a plan whose ``status.json`` PARSES but whose ``phases`` will not read in full.

    Deliberately distinct from the unparseable member ``TestPartialCoverage`` uses:
    that one fails at the JSON layer, so nothing about it is known. This one parses
    cleanly and is established as a plan — one of its phase rows simply is not a phase
    record, so the open-phase SET is what could not be determined.

    The readable row is deliberately ``in_progress``, not ``done``. ``_scan_plan_container``
    RETAINS a positively-established open phase even when the phase list is unexaminable,
    and that retention is the behaviour the cells below are about; a ``done`` row leaves
    the plan contributing nothing, so the fixture would exercise the shortfall path while
    never reaching the retained-record path at all — and the ``open_phase_count``
    assertion would be satisfied by the readable sibling plan alone.
    """
    plan_dir.mkdir(parents=True)
    document: dict[str, Any] = {
        'title': plan_dir.name,
        'current_phase': _RETAINED_OPEN_PHASE,
        'phases': [{'name': _RETAINED_OPEN_PHASE, 'status': 'in_progress'}, 'not-a-phase-record'],
    }
    (plan_dir / 'status.json').write_text(f'{json.dumps(document)}\n')
    return plan_dir


def _write_unnamed_phase_plan(plan_dir: Path) -> Path:
    """Seed a plan carrying an ``in_progress`` row whose ``name`` is missing.

    The row is otherwise well-formed and would be classified OPEN on its status alone,
    so without the name validation the projection renders it as the phase named ``''``
    — a record no consumer can act on — while the scan still reads examinable and the
    cohort publishes ``coverage: complete`` over it.
    """
    plan_dir.mkdir(parents=True)
    document: dict[str, Any] = {
        'title': plan_dir.name,
        'current_phase': '5-execute',
        'phases': [{'name': '1-init', 'status': 'done'}, {'status': 'in_progress'}],
    }
    (plan_dir / 'status.json').write_text(f'{json.dumps(document)}\n')
    return plan_dir


def _census() -> dict[str, Any]:
    """Invoke the verb. It declares no flags, so its namespace carries none."""
    result: dict[str, Any] = status_query.cmd_census(Namespace())
    return result


def _cohort(result: dict[str, Any], cohort: str) -> dict[str, Any]:
    """Return the single row for ``cohort``, asserting it is reported exactly once."""
    rows: list[dict[str, Any]] = [row for row in result['cohorts'] if row['cohort'] == cohort]
    assert len(rows) == 1, f'Expected exactly one {cohort!r} row, got {rows!r}.'
    return rows[0]


def _records_for(result: dict[str, Any], cohort: str) -> list[dict[str, Any]]:
    return [record for record in result['open_phase_records'] if record['cohort'] == cohort]


@pytest.fixture
def store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Anchor the census at an override store — the ``anchor: override`` branch.

    The override directory IS the ``.plan/local`` stand-in, so each cohort sits
    directly beneath it with no ``.plan/local`` segment of its own. No cohort
    directory is created here: every class below creates only the ones its claim is
    about, so an untouched cohort's verdict is the verb's own answer for an absent
    store rather than something the fixture arranged.
    """
    base = (tmp_path / 'plan-store').resolve()
    base.mkdir()
    monkeypatch.setenv('PLAN_BASE_DIR', str(base))
    import file_ops

    # The env var is only one of the two override spellings; a stale in-process
    # ``set_base_dir()`` override would outrank it and silently relocate the store.
    monkeypatch.setattr(file_ops, '_BASE_DIR_OVERRIDE', None)
    return base


def _init_main_repo(main: Path) -> None:
    """Seed a real main checkout whose ``.gitignore`` covers ``.plan/``.

    The ignore rule keeps the worktree-resident plan state untracked-but-ignored, so
    ``git worktree add`` and the repository itself stay indifferent to the fixture's
    plan directories.
    """
    subprocess.run(['git', 'init', '-q', '-b', 'main', str(main)], check=True)
    subprocess.run(['git', '-C', str(main), 'config', 'user.email', 't@t.test'], check=True)
    subprocess.run(['git', '-C', str(main), 'config', 'user.name', 'Test'], check=True)
    (main / '.gitignore').write_text('.plan/\n')
    (main / 'file.txt').write_text('one\n')
    subprocess.run(['git', '-C', str(main), 'add', '.'], check=True, capture_output=True)
    subprocess.run(['git', '-C', str(main), 'commit', '-q', '-m', 'init'], check=True, capture_output=True)


@pytest.fixture
def real_geometry(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Path]:
    """A real main checkout, a real linked worktree, and cwd pinned INSIDE the worktree.

    The geometry mirrors production: the worktree is nested under the main checkout at
    ``main/.plan/local/worktrees/{plan_id}``, and the plan that is executing has its
    directory MOVED into that worktree (ADR-002) while a second plan stays resident on
    main. Both override spellings are neutralised so the production git-common-dir
    branch of ``resolve_main_anchored_path`` is what answers.

    Every path is ``resolve()``d: the resolver returns physical paths, so a fixture
    holding the symlinked spelling of ``tmp_path`` would compare two spellings of one
    directory and reach a verdict about the platform rather than about the code.
    """
    main = tmp_path / 'main'
    main.mkdir()
    main = main.resolve()
    _init_main_repo(main)

    main_local = main / '.plan' / 'local'
    worktree = main_local / 'worktrees' / _WT_PLAN
    worktree.parent.mkdir(parents=True)
    subprocess.run(
        ['git', '-C', str(main), 'worktree', 'add', '-q', '-b', f'feature/{_WT_PLAN}', str(worktree)],
        check=True,
        capture_output=True,
    )
    worktree = worktree.resolve()

    # Main's live cohort, and the moved-in plan inside the worktree. The two carry
    # DIFFERENT ids so the cohort a plan is reported under is observable.
    _write_plan(main_local / 'plans' / _MAIN_PLAN, {'1-init': 'done', '2-refine': 'in_progress'})
    _write_plan(worktree / '.plan' / 'local' / 'plans' / _WT_PLAN, {'1-init': 'done', '5-execute': 'in_progress'})

    monkeypatch.delenv('PLAN_BASE_DIR', raising=False)
    import file_ops

    monkeypatch.setattr(file_ops, '_BASE_DIR_OVERRIDE', None)
    monkeypatch.chdir(worktree)

    return {'main': main, 'main_local': main_local, 'worktree': worktree}
