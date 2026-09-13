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


class TestMainAnchoredFromAWorktreeCwd:
    """Called from inside a worktree, the census still reports MAIN's stores."""

    def test_the_anchor_is_main_not_the_worktree_the_caller_stands_in(self, real_geometry: dict[str, Path]) -> None:
        """The resolved anchor is the main checkout's ``.plan/local``.

        This is the assertion a cwd-relative resolver fails: standing in the worktree,
        the uniform walk-up finds ``worktree/.plan/local`` first and anchors there.
        """
        result = _census()

        assert result['status'] == 'success', result
        assert result['anchor'] == 'main', (
            'Both override spellings were neutralised, so the production '
            f'git-common-dir branch must be the one that answered; got {result!r}.'
        )
        assert Path(result['anchor_path']) == real_geometry['main_local']
        assert Path(result['anchor_path']) != real_geometry['worktree'] / '.plan' / 'local', (
            'Anchoring on the cwd worktree is the defect this verb exists to avoid.'
        )

    def test_each_plan_is_reported_under_the_store_it_actually_lives_in(self, real_geometry: dict[str, Path]) -> None:
        """Main's plan is ``live``; the moved-in plan is ``worktree``.

        Under a cwd-relative resolution the moved-in plan would be the LIVE cohort (it
        is what ``{cwd}/.plan/local/plans`` holds) and main's plan would be invisible.
        Asserting which cohort each id lands in is what separates the two resolutions;
        a bare population count of 1 and 1 would not.
        """
        del real_geometry  # The fixture's effect is the cwd and the tree it built.

        result = _census()

        live = _cohort(result, 'live')
        worktree = _cohort(result, 'worktree')
        assert live['coverage'] == 'complete', live
        assert worktree['coverage'] == 'complete', worktree
        assert live['population'] == 1, live
        assert worktree['population'] == 1, worktree

        assert [record['id'] for record in _records_for(result, 'live')] == [_MAIN_PLAN]
        assert [record['id'] for record in _records_for(result, 'worktree')] == [_WT_PLAN]
        assert _WT_PLAN not in [record['id'] for record in _records_for(result, 'live')], (
            'The moved-in plan belongs to the worktree cohort; reporting it as live is '
            'precisely what a cwd-anchored enumeration does from this cwd.'
        )


class TestUnevaluatedIsNotZero:
    """Matched pair: a cohort nobody could enumerate vs one that is verifiably empty.

    Both cells ask about the SAME cohort and differ only in what sits at its path, so
    the contrast is attributable to that and nothing else.
    """

    def test_an_unlistable_cohort_omits_the_population_key_entirely(self, store: Path) -> None:
        """A regular FILE at the cohort path ⇒ ``unevaluated``, with no counts at all.

        ``iterdir`` raises ``NotADirectoryError`` (an ``OSError``), so nothing was
        enumerated. Publishing ``population: 0`` here would be byte-identical to the
        control below, where the store really is empty — which is the confusion the
        key's ABSENCE exists to make unreachable.
        """
        (store / 'plans').write_text('not a directory\n')

        result = _census()

        live = _cohort(result, 'live')
        assert live['coverage'] == 'unevaluated', live
        assert 'population' not in live, f'An unevaluated cohort must publish no population at all, got {live!r}.'
        assert 'open_phase_count' not in live, live
        assert 'unreadable_count' not in live, (
            'On a store that was never enumerated, "zero unreadable members" is a '
            f'claim about members nobody examined; got {live!r}.'
        )
        assert live['reason'], 'An unevaluated cohort must name the condition.'

    def test_a_genuinely_absent_cohort_reports_a_real_zero_population(self, store: Path) -> None:
        """Matched control: directory absent, anchor resolved ⇒ ``complete``, ``0``.

        The load-bearing half. Without it, the assertion above is equally consistent
        with a verb that omits the counts for every cohort, evaluated or not — so the
        honesty property would be untested and a verb reporting nothing anywhere would
        pass. Here the anchor resolved and the store demonstrably holds nothing, which
        is the one case where a zero IS evidence.
        """
        assert not (store / 'plans').exists(), 'The control must leave the cohort path absent.'

        result = _census()

        live = _cohort(result, 'live')
        assert live['coverage'] == 'complete', live
        assert live['population'] == 0, (
            f'An absent cohort under a resolved anchor is a verified empty store; got {live!r}.'
        )
        assert live['open_phase_count'] == 0, live
        assert live['unreadable_count'] == 0, live
        assert 'reason' not in live, f'A complete cohort has no shortfall to name; got {live!r}.'


class TestOpenPhaseRecords:
    """The open-phase predicate is ``phases[]`` status — never the loop-back marker."""

    @pytest.fixture
    def archived_pair(self, store: Path) -> dict[str, str]:
        """Two archived records differing in the one thing the predicate may read.

        ``still-open`` holds two ``in_progress`` phases. ``closed-with-marker`` holds
        none — every phase is ``done`` — but still carries
        ``metadata.loop_back_reentry``, the shape a plan is left in after a sanctioned
        loop-back that later completed.
        """
        archived_root = store / 'archived-plans'
        open_id = f'{_ARCHIVE_DATE}-still-open'
        closed_id = f'{_ARCHIVE_DATE}-closed-with-marker'
        _write_plan(
            archived_root / open_id,
            {'1-init': 'done', '5-execute': 'in_progress', '6-finalize': 'in_progress'},
        )
        _write_plan(
            archived_root / closed_id,
            {'1-init': 'done', '5-execute': 'done', '6-finalize': 'done'},
            metadata={'loop_back_reentry': {'from_phase': '5-execute', 'to_phase': '3-outline'}},
        )
        return {'open_id': open_id, 'closed_id': closed_id}

    def test_every_in_progress_phase_of_a_record_is_reported(self, archived_pair: dict[str, str]) -> None:
        """A record with two open phases is reported once, naming BOTH phases.

        Reporting only the first would under-report exactly the population this verb
        exists to surface — and is the shape of the single-closure defect that motivated
        it.
        """
        result = _census()

        records = _records_for(result, 'archived')
        open_records = [record for record in records if record['id'] == archived_pair['open_id']]
        assert len(open_records) == 1, f'Expected one record for the open plan, got {records!r}.'
        assert set(open_records[0]['open_phases']) == {'5-execute', '6-finalize'}, open_records[0]
        assert _cohort(result, 'archived')['open_phase_count'] == 1, (
            'One of the two archived records holds open phases, and the per-cohort '
            'count is derived from the records rather than asserted independently.'
        )

    def test_a_closed_record_carrying_the_loop_back_marker_is_not_reported(self, archived_pair: dict[str, str]) -> None:
        """Matched control: the marker is present, every phase is ``done`` ⇒ absent.

        A predicate keyed on ``metadata.loop_back_reentry`` would report this record,
        which has nothing open. The marker says a loop-back was scheduled, not that a
        phase was left running.
        """
        result = _census()

        reported = [record['id'] for record in _records_for(result, 'archived')]
        assert archived_pair['closed_id'] not in reported, (
            'A record whose phases are all done holds no open phase, whatever marker '
            f'its metadata carries; got {reported!r}.'
        )

    def test_the_archived_id_is_the_dated_directory_name(self, archived_pair: dict[str, str]) -> None:
        """The reported id is the ``{YYYY-MM-DD}-{plan_id}`` directory ``archive`` writes.

        The date is a fixed past one, so an id reported as the bare plan id — or rebuilt
        from today's date — fails.
        """
        result = _census()

        reported = [record['id'] for record in _records_for(result, 'archived')]
        assert archived_pair['open_id'] in reported, reported
        assert archived_pair['open_id'].startswith(f'{_ARCHIVE_DATE}-'), archived_pair['open_id']
        assert 'still-open' not in reported, (
            'The archived cohort is keyed by the dated directory name, not by the bare plan id.'
        )


class TestCohortsAreCountedSeparately:
    """Three stores, three deliberately different figures, never blended."""

    @pytest.fixture
    def three_cohorts(self, store: Path) -> Path:
        """Populations 3 / 2 / 1 with open-phase counts 2 / 1 / 0.

        Both axes differ per cohort. Equal figures would leave a row carrying its
        neighbour's number — or the 6-plan total — indistinguishable from three correct
        rows.
        """
        open_phases = {'1-init': 'done', '5-execute': 'in_progress'}
        closed_phases = {'1-init': 'done', '5-execute': 'done'}

        for index in range(3):
            phases = open_phases if index < 2 else closed_phases
            _write_plan(store / 'plans' / f'live-plan-{index}', phases)

        for index in range(2):
            phases = open_phases if index < 1 else closed_phases
            worktree_plans = store / 'worktrees' / f'wt-{index}' / '.plan' / 'local' / 'plans'
            _write_plan(worktree_plans / f'wt-plan-{index}', phases)

        _write_plan(store / 'archived-plans' / f'{_ARCHIVE_DATE}-archived-plan', closed_phases)
        return store

    def test_each_cohort_reports_its_own_population_and_open_count(self, three_cohorts: Path) -> None:
        del three_cohorts  # The fixture's effect is the tree it seeded.

        result = _census()

        assert [row['cohort'] for row in result['cohorts']] == ['live', 'worktree', 'archived'], result
        assert [row['population'] for row in result['cohorts']] == [3, 2, 1], (
            f'Each cohort must report its OWN population, never a blended total; got {result["cohorts"]!r}.'
        )
        assert [row['open_phase_count'] for row in result['cohorts']] == [2, 1, 0], result['cohorts']
        assert all(row['coverage'] == 'complete' for row in result['cohorts']), result['cohorts']
        assert all(row['unreadable_count'] == 0 for row in result['cohorts']), result['cohorts']

    def test_the_open_phase_records_are_attributed_to_their_cohorts(self, three_cohorts: Path) -> None:
        """Each record names the store it came from, so the rows stay unblended."""
        del three_cohorts

        result = _census()

        assert sorted(record['id'] for record in _records_for(result, 'live')) == ['live-plan-0', 'live-plan-1']
        assert [record['id'] for record in _records_for(result, 'worktree')] == ['wt-plan-0']
        assert _records_for(result, 'archived') == []

    def test_the_anchor_reports_the_override_branch(self, three_cohorts: Path) -> None:
        """The second anchor label: a redirected store says so rather than claiming main.

        A reader must be able to tell a census of a real checkout from one of a
        stand-in store, which is what makes ``anchor`` worth reporting at all.
        """
        result = _census()

        assert result['anchor'] == 'override', result
        assert Path(result['anchor_path']) == three_cohorts


class TestPartialCoverage:
    """An unreadable member degrades its cohort without erasing what WAS counted."""

    def test_an_unparseable_status_json_is_counted_and_named(self, store: Path) -> None:
        """Population keeps the member; ``unreadable_count`` and ``reason`` expose it.

        The shortfall must be visible rather than absorbed: a cohort that silently
        dropped the unreadable plan would report ``complete`` over a population it had
        not fully read.
        """
        _write_plan(store / 'plans' / 'readable-plan', {'1-init': 'done', '5-execute': 'in_progress'})
        broken = store / 'plans' / 'broken-plan'
        broken.mkdir(parents=True)
        (broken / 'status.json').write_text('{not json\n')

        result = _census()

        live = _cohort(result, 'live')
        assert live['coverage'] == 'partial', live
        assert live['population'] == 2, f'The unreadable plan is still a member; got {live!r}.'
        assert live['unreadable_count'] == 1, live
        assert 'broken-plan' in live['reason'], live
        assert live['open_phase_count'] == 1, live

    def test_a_directory_without_a_status_json_is_not_a_plan(self, store: Path) -> None:
        """Matched control: an orphan directory is neither a member nor unreadable.

        Without this, the cell above is consistent with the census counting every
        directory it sees and calling the ones it cannot parse unreadable — which would
        report the orphan population (``list-orphans``' surface) as broken plans.
        """
        _write_plan(store / 'plans' / 'readable-plan', {'1-init': 'done'})
        (store / 'plans' / 'orphan-dir').mkdir(parents=True)

        result = _census()

        live = _cohort(result, 'live')
        assert live['coverage'] == 'complete', live
        assert live['population'] == 1, f'The orphan directory is not a plan; got {live!r}.'
        assert live['unreadable_count'] == 0, live


class TestAnUnexaminableEntryIsCredited:
    """An entry the probe cannot complete degrades its cohort instead of vanishing.

    Both positives and the control run under the SAME injected denial, so the only
    thing that differs between them is whether the tree holds the unexaminable entry.
    """

    @pytest.fixture
    def deny_probe(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Make the membership probe RAISE for the single entry named ``_UNEXAMINABLE``.

        The production condition is a search-bit denial on the containing directory:
        ``iterdir`` still lists the names (that needs read) while stat-ing each child
        fails with ``EACCES`` (that needs search). Staging it with ``chmod`` would make
        the verdict depend on the uid running the suite — root bypasses the permission
        check outright and the entry would probe cleanly — so the denial is injected at
        the probe, narrowed by name. Every other entry keeps the real ``is_dir``.
        """
        real_is_dir = Path.is_dir

        def denying_is_dir(path: Path, *args: Any, **kwargs: Any) -> bool:
            if path.name == _UNEXAMINABLE:
                raise PermissionError(13, 'Permission denied')
            return bool(real_is_dir(path, *args, **kwargs))

        monkeypatch.setattr(Path, 'is_dir', denying_is_dir)

    def test_an_unexaminable_cohort_entry_degrades_the_cohort(self, store: Path, deny_probe: None) -> None:
        """``partial`` plus a non-zero ``unreadable_count``, with the entry named.

        The entry is NOT added to ``population``: nothing established it is a plan, so
        counting it as one would be a second false claim. It is the ``unreadable_count``
        and the ``reason`` that carry it — a silent ``continue`` here is what would let
        this cohort publish ``complete`` over an entry it never looked at.
        """
        del deny_probe
        _write_plan(store / 'plans' / 'readable-plan', {'1-init': 'done', '5-execute': 'in_progress'})
        (store / 'plans' / _UNEXAMINABLE).mkdir(parents=True)

        result = _census()

        live = _cohort(result, 'live')
        assert live['coverage'] == 'partial', live
        assert live['unreadable_count'] == 1, f'The unexaminable entry must be credited; got {live!r}.'
        assert live['population'] == 1, f'Only the established member counts as a member; got {live!r}.'
        assert live['open_phase_count'] == 1, live
        assert _UNEXAMINABLE in live['reason'], live

    def test_an_unexaminable_worktree_entry_degrades_the_worktree_cohort(self, store: Path, deny_probe: None) -> None:
        """The same credit one level up, where the unknown is a whole plan store.

        A worktree entry that cannot be examined may hold any number of plans, none of
        them seen, so it counts as one unreadable unit. This is the second discard site
        and it needs its own cell: a fix applied to the inner loop alone leaves this one
        reporting ``complete``.
        """
        del deny_probe
        _write_plan(store / 'worktrees' / 'wt-0' / '.plan' / 'local' / 'plans' / 'wt-plan-0', {'1-init': 'done'})
        (store / 'worktrees' / _UNEXAMINABLE).mkdir(parents=True)

        result = _census()

        worktree = _cohort(result, 'worktree')
        assert worktree['coverage'] == 'partial', worktree
        assert worktree['unreadable_count'] == 1, worktree
        assert worktree['population'] == 1, f'The readable store still contributes its member; got {worktree!r}.'
        assert _UNEXAMINABLE in worktree['reason'], worktree

    def test_a_fully_examinable_cohort_still_reports_complete(self, store: Path, deny_probe: None) -> None:
        """Matched control: the identical tree MINUS the unexaminable entry.

        The load-bearing half. The denial is still installed, so what differs is only
        that no entry triggers it. Without this cell both positives are equally
        consistent with a verb that reports ``partial`` for everything — which would
        make the tri-state worthless in the opposite direction.
        """
        del deny_probe
        _write_plan(store / 'plans' / 'readable-plan', {'1-init': 'done', '5-execute': 'in_progress'})

        result = _census()

        live = _cohort(result, 'live')
        assert live['coverage'] == 'complete', live
        assert live['unreadable_count'] == 0, live
        assert live['population'] == 1, live
        assert 'reason' not in live, f'A complete cohort has no shortfall to name; got {live!r}.'


class TestAnchorUnresolvedFailsClosed:
    """No anchor ⇒ no cohort rows, rather than three thoroughly-surveyed zeros."""

    def test_an_unresolvable_anchor_returns_no_cohorts(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """The resolver raising must surface as ``anchor_unresolved`` with no rows.

        Emitting ``population: 0`` for all three cohorts here would report an empty
        machine on the strength of a resolution that never happened — the same
        false-zero the ``unevaluated`` coverage state exists to prevent, one level up.
        """
        monkeypatch.setattr(
            status_query,
            'resolve_main_anchored_path',
            lambda _subpath: (_ for _ in ()).throw(RuntimeError('cannot resolve main checkout')),
        )

        result = _census()

        assert result['status'] == 'error', result
        assert result['error'] == 'anchor_unresolved', result
        assert 'cohorts' not in result, f'A failed anchor resolution may report no cohort rows; got {result!r}.'
        assert 'open_phase_records' not in result, result
        assert 'cannot resolve main checkout' in result['message'], (
            "The resolver's own diagnosis must survive into the message."
        )
