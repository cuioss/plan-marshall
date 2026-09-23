#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Cross-machine merge regression for the per-concern orchestrator ledger.

The epic ledger is git-tracked, so two sessions on two machines each commit
their own ledger writes and those commits have to merge. This module proves the
property the per-concern layout exists for, over a REAL temporary git
repository, with every write going through the production seams —
``manage-status create`` / ``update-field`` through the ``manage-status.py`` CLI,
and ``orchestrator queue`` / ``regenerate-view`` through the orchestrator's own
command functions. Each branch of the repository stands for one machine.

Three arms, a matched set:

- **Positive arm (per-concern layout).** Two machines staging two DIFFERENT
  plans write two different row files, so ``git merge`` completes with no
  conflict, no ledger file carries a conflict marker, and the production
  assembled reader returns both new rows beside the seed rows, unchanged. Two
  further scenarios run on the same harness: one machine stages a plan while the
  other moves the resume anchor, and one transitions ``PLAN-01`` while the other
  stamps ``pr`` on ``PLAN-02``. This arm commits source files only and never
  regenerates ``queue-view.md``, so it measures the source layout on its own.
- **Generated-view arm.** With ``queue-view.md`` committed and regenerated on
  both machines, the merge conflicts on exactly ONE path — the view — while
  every source file merges cleanly. Running the production ``regenerate-view``
  on the merged tree removes every conflict marker and writes a view
  byte-identical to a fresh render of the merged ledger; ``git add`` then
  completes the merge. A determinism control shows that two machines rendering
  the SAME ledger state write byte-identical views that do not conflict at all.
- **Negative arm (monolithic layout).** A test-local legacy writer models the
  retired whole-document write — append to ``plans[]`` and restamp ``updated`` —
  and the identical two-machine staging scenario over a legacy ``status.json``
  conflicts. That proves the scenario CAN produce a conflict, so the positive
  arm's clean merge is a property of the layout rather than of a weak scenario.

Every arm asserts the writer population it actually ran, and the generated-view
arm asserts the size of its conflicted-path population, so a run in which no
writer fired, or no conflict existed, cannot pass.

Git isolation: every git call is ``git -C {repo}`` with the global and system
configuration disabled, and the committer identity is set per repository.
"""

import argparse
import copy
import json
import os
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Any

from _ledger_fixtures import ledger

from conftest import get_script_path, load_script_module, parse_ns, run_script

_ORCH_BUNDLE = 'plan-marshall'
_ORCH_SKILL = 'plan-orchestrator'
_ORCH_SCRIPT = 'orchestrator.py'

ORCH_SCRIPT_PATH = get_script_path(_ORCH_BUNDLE, _ORCH_SKILL, _ORCH_SCRIPT)
STATUS_SCRIPT_PATH = get_script_path('plan-marshall', 'manage-status', 'manage-status.py')

_orch = load_script_module(_ORCH_BUNDLE, _ORCH_SKILL, _ORCH_SCRIPT, 'orchestrator_cross_machine_script')

cmd_queue = _orch.cmd_queue
cmd_regenerate_view = _orch.cmd_regenerate_view
render_queue_view = _orch.render_queue_view

SLUG = 'merge-epic'
MACHINE_A = 'machine-a'
MACHINE_B = 'machine-b'
BASE_BRANCH = 'main'

#: The seed queue every arm starts from, staged on the base branch.
SEED_ROWS: tuple[tuple[str, str], ...] = (('PLAN-01', 'plan-one'), ('PLAN-02', 'plan-two'))

#: The files git must not track. ``logs/`` is git-ignored in the real store, and
#: the lock and temp files are transient artefacts of the atomic writers.
GITIGNORE = 'logs/\n*.lock\n*.tmp\n'

CONFLICT_MARKER = '<<<<<<<'

_QUEUE_ARGS = parse_ns(_ORCH_BUNDLE, _ORCH_SKILL, _ORCH_SCRIPT, 'queue', '--slug', SLUG, register=False)
_REGENERATE_ARGS = parse_ns(_ORCH_BUNDLE, _ORCH_SKILL, _ORCH_SCRIPT, 'regenerate-view', '--slug', SLUG, register=False)


# =============================================================================
# Git harness — one repository, one branch per machine
# =============================================================================


def _git_env() -> dict[str, str]:
    """The process environment with every git configuration file outside the repo disabled."""
    return {
        **os.environ,
        'GIT_CONFIG_GLOBAL': os.devnull,
        'GIT_CONFIG_NOSYSTEM': '1',
        'GIT_TERMINAL_PROMPT': '0',
    }


def _git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    """Run one ``git -C {repo}`` command; assert success unless ``check`` is off."""
    result = subprocess.run(
        ['git', '-C', str(repo), *args],
        capture_output=True,
        text=True,
        env=_git_env(),
        check=False,
    )
    if check:
        assert result.returncode == 0, f'git {" ".join(args)} failed: {result.stderr}'
    return result


def _init_repo(repo: Path) -> None:
    """Initialise ``repo`` with a per-repository identity and the store's ignore rules."""
    _git(repo, 'init', '-q', '-b', BASE_BRANCH)
    _git(repo, 'config', 'user.name', 'Cross Machine Fixture')
    _git(repo, 'config', 'user.email', 'cross-machine@example.invalid')
    _git(repo, 'config', 'commit.gpgsign', 'false')
    (repo / '.gitignore').write_text(GITIGNORE, encoding='utf-8')


def _commit_all(repo: Path, message: str) -> None:
    _git(repo, 'add', '-A')
    _git(repo, 'commit', '-q', '-m', message)


def _conflicted_paths(repo: Path) -> list[str]:
    output = _git(repo, 'diff', '--name-only', '--diff-filter=U').stdout
    return sorted(line for line in output.splitlines() if line)


def _two_machines(
    repo: Path, on_a: Callable[[], list[Any]], on_b: Callable[[], list[Any]]
) -> tuple[subprocess.CompletedProcess[str], list[Any], list[Any]]:
    """Run ``on_a`` on one branch and ``on_b`` on another, commit each, merge B into A.

    Returns the merge result and the writer outcomes each machine reported, so
    the caller can assert the writer population it actually ran.
    """
    _git(repo, 'checkout', '-q', '-b', MACHINE_A)
    outcomes_a = on_a()
    _commit_all(repo, 'machine A ledger write')
    _git(repo, 'checkout', '-q', BASE_BRANCH)
    _git(repo, 'checkout', '-q', '-b', MACHINE_B)
    outcomes_b = on_b()
    _commit_all(repo, 'machine B ledger write')
    _git(repo, 'checkout', '-q', MACHINE_A)
    merged = _git(repo, 'merge', '--no-edit', '-q', MACHINE_B, check=False)
    return merged, outcomes_a, outcomes_b


# =============================================================================
# Production writers
# =============================================================================


def _env(plan_context) -> dict[str, str]:
    return {'PLAN_BASE_DIR': str(plan_context.fixture_dir)}


def _epic_dir(plan_context) -> Path:
    return Path(plan_context.fixture_dir) / 'orchestrator' / SLUG


def _variant(base: argparse.Namespace, **overrides: Any) -> argparse.Namespace:
    derived = copy.copy(base)
    for field, value in overrides.items():
        setattr(derived, field, value)
    return derived


def _add_row(plan_id: str, slug_value: str) -> dict[str, Any]:
    result: dict[str, Any] = cmd_queue(
        _variant(
            _QUEUE_ARGS,
            transition=None,
            status=None,
            set_row=None,
            field=None,
            value=None,
            add_row=plan_id,
            slug_value=slug_value,
            workstream='WS-01',
        )
    )
    return result


def _transition(plan_id: str, status: str) -> dict[str, Any]:
    result: dict[str, Any] = cmd_queue(_variant(_QUEUE_ARGS, transition=plan_id, status=status))
    return result


def _set_row(plan_id: str, field: str, value: str) -> dict[str, Any]:
    result: dict[str, Any] = cmd_queue(_variant(_QUEUE_ARGS, set_row=plan_id, field=field, value=value))
    return result


def _regenerate() -> dict[str, Any]:
    result: dict[str, Any] = cmd_regenerate_view(_REGENERATE_ARGS)
    return result


def _write_anchor(plan_context, text: str) -> dict[str, Any]:
    result = run_script(
        STATUS_SCRIPT_PATH,
        'update-field',
        '--plan-id',
        SLUG,
        '--field',
        'resume_anchor',
        '--value',
        text,
        '--store',
        'orchestrator',
        env_overrides=_env(plan_context),
    )
    payload: dict[str, Any] = result.toon()
    return payload


def _seed_epic(plan_context, *, with_view: bool) -> Path:
    """Create the epic and its seed queue through the production seams, then commit it."""
    env = _env(plan_context)
    scaffolded = run_script(ORCH_SCRIPT_PATH, 'scaffold', '--slug', SLUG, env_overrides=env)
    assert scaffolded.toon()['status'] == 'success', scaffolded.stdout
    created = run_script(
        STATUS_SCRIPT_PATH,
        'create',
        '--plan-id',
        SLUG,
        '--title',
        'Merge Epic',
        '--store',
        'orchestrator',
        env_overrides=env,
    )
    assert created.toon()['status'] == 'success', created.stdout
    for plan_id, slug_value in SEED_ROWS:
        staged = _add_row(plan_id, slug_value)
        assert staged['status'] == 'success', staged
    root = _epic_dir(plan_context)
    if with_view:
        assert _regenerate()['written'] is True
    _init_repo(root)
    _commit_all(root, 'seed the epic ledger')
    return root


# =============================================================================
# Readers
# =============================================================================


def _ledger_files(root: Path) -> list[Path]:
    """Every ledger file a merge can touch: header, anchor, rows, and the view."""
    candidates = [root / 'status.json', root / 'resume_anchor.md', root / 'queue-view.md']
    rows = sorted((root / 'queue').glob('*.json'))
    return [path for path in (*candidates, *rows) if path.is_file()]


def _files_with_conflict_markers(root: Path) -> list[str]:
    return [path.name for path in _ledger_files(root) if CONFLICT_MARKER in path.read_text(encoding='utf-8')]


def _assembled_rows(root: Path) -> dict[str, dict[str, Any]]:
    """The queue as the production assembled reader returns it, keyed by plan id."""
    read = ledger.assemble_view(root)
    assert read.state == ledger.LEDGER_OK, read.detail
    assert read.unreadable_rows == (), read.unreadable_rows
    return {str(row['id']): dict(row) for row in read.document['plans']}


def _fresh_render(root: Path) -> str:
    """A fresh render of the ledger at ``root`` through the production renderer."""
    view = ledger.assemble_view(root).document
    rendered: str = render_queue_view(view, _orch._resolve_row_surfaces(view, root), slug=SLUG)
    return rendered


def _successes(outcomes: list[Any]) -> int:
    return sum(1 for outcome in outcomes if outcome.get('status') == 'success')


# =============================================================================
# Positive arm — the per-concern layout merges cleanly
# =============================================================================


class TestPerConcernLayoutMergesCleanly:
    def test_two_machines_staging_different_plans_merge_without_conflict(self, plan_context):
        root = _seed_epic(plan_context, with_view=False)
        seed_rows = _assembled_rows(root)

        merged, outcomes_a, outcomes_b = _two_machines(
            root,
            lambda: [_add_row('PLAN-03', 'plan-three')],
            lambda: [_add_row('PLAN-04', 'plan-four')],
        )

        assert (_successes(outcomes_a), _successes(outcomes_b)) == (1, 1), (outcomes_a, outcomes_b)
        assert merged.returncode == 0, merged.stdout + merged.stderr
        assert _conflicted_paths(root) == []
        assert _files_with_conflict_markers(root) == []
        rows = _assembled_rows(root)
        assert set(rows) == {'PLAN-01', 'PLAN-02', 'PLAN-03', 'PLAN-04'}
        for plan_id, seed_row in seed_rows.items():
            assert rows[plan_id] == seed_row, plan_id
        assert not (root / 'queue-view.md').exists(), 'this arm measures the source layout alone'

    def test_staging_on_one_machine_and_an_anchor_move_on_the_other_merge_cleanly(self, plan_context):
        root = _seed_epic(plan_context, with_view=False)
        anchor = 'await PLAN-03 landing, then analyze'

        merged, outcomes_a, outcomes_b = _two_machines(
            root,
            lambda: [_add_row('PLAN-03', 'plan-three')],
            lambda: [_write_anchor(plan_context, anchor)],
        )

        assert (_successes(outcomes_a), _successes(outcomes_b)) == (1, 1), (outcomes_a, outcomes_b)
        assert merged.returncode == 0, merged.stdout + merged.stderr
        assert _conflicted_paths(root) == []
        assert _files_with_conflict_markers(root) == []
        assert 'PLAN-03' in _assembled_rows(root)
        assert ledger.assemble_view(root).document['resume_anchor'] == anchor

    def test_a_transition_and_a_stamp_on_different_rows_merge_cleanly(self, plan_context):
        root = _seed_epic(plan_context, with_view=False)

        merged, outcomes_a, outcomes_b = _two_machines(
            root,
            lambda: [_transition('PLAN-01', 'running')],
            lambda: [_set_row('PLAN-02', 'pr', '#912')],
        )

        assert (_successes(outcomes_a), _successes(outcomes_b)) == (1, 1), (outcomes_a, outcomes_b)
        assert merged.returncode == 0, merged.stdout + merged.stderr
        assert _conflicted_paths(root) == []
        assert _files_with_conflict_markers(root) == []
        rows = _assembled_rows(root)
        assert rows['PLAN-01']['status'] == 'running'
        assert rows['PLAN-02']['pr'] == '#912'


# =============================================================================
# Generated-view arm — the view conflicts, and regeneration resolves it
# =============================================================================


class TestGeneratedViewConflictIsResolvedByRegeneration:
    def test_only_the_view_conflicts_and_regenerate_view_completes_the_merge(self, plan_context):
        root = _seed_epic(plan_context, with_view=True)

        def _stage_and_render(plan_id: str, slug_value: str) -> list[dict[str, Any]]:
            return [_add_row(plan_id, slug_value), _regenerate()]

        merged, outcomes_a, outcomes_b = _two_machines(
            root,
            lambda: _stage_and_render('PLAN-03', 'plan-three'),
            lambda: _stage_and_render('PLAN-04', 'plan-four'),
        )

        assert (_successes(outcomes_a), _successes(outcomes_b)) == (2, 2), (outcomes_a, outcomes_b)
        assert [outcome['written'] for outcome in (outcomes_a[1], outcomes_b[1])] == [True, True]
        assert merged.returncode != 0, 'two different regenerations were expected to conflict on the view'
        conflicted = _conflicted_paths(root)
        assert len(conflicted) == 1, conflicted
        assert conflicted == ['queue-view.md']
        assert _files_with_conflict_markers(root) == ['queue-view.md']

        regenerated = _regenerate()

        assert regenerated['status'] == 'success', regenerated
        assert regenerated['written'] is True
        view = (root / 'queue-view.md').read_text(encoding='utf-8')
        assert CONFLICT_MARKER not in view
        for plan_id in ('PLAN-01', 'PLAN-02', 'PLAN-03', 'PLAN-04'):
            assert f'| {plan_id} |' in view, plan_id
        assert view == _fresh_render(root)

        _git(root, 'add', 'queue-view.md')
        completed = _git(root, 'commit', '-q', '--no-edit', check=False)

        assert completed.returncode == 0, completed.stderr
        assert _conflicted_paths(root) == []
        assert _git(root, 'status', '--porcelain').stdout == ''

    def test_two_machines_rendering_the_same_state_write_identical_views_that_do_not_conflict(self, plan_context):
        # Determinism control: the same staged row on both machines is the same
        # ledger state, so the two renders are byte-identical and git has nothing
        # to reconcile — the view conflicts only when the ledger states differ.
        root = _seed_epic(plan_context, with_view=True)

        def _stage_same_and_render() -> list[dict[str, Any]]:
            return [_add_row('PLAN-03', 'plan-three'), _regenerate()]

        merged, outcomes_a, outcomes_b = _two_machines(root, _stage_same_and_render, _stage_same_and_render)

        assert (_successes(outcomes_a), _successes(outcomes_b)) == (2, 2), (outcomes_a, outcomes_b)
        assert merged.returncode == 0, merged.stdout + merged.stderr
        # HEAD^1 is machine A's own commit, the first parent of the merge.
        view_a = _git(root, 'show', 'HEAD^1:queue-view.md').stdout
        view_b = _git(root, 'show', f'{MACHINE_B}:queue-view.md').stdout
        assert view_a == view_b
        assert _conflicted_paths(root) == []
        assert _files_with_conflict_markers(root) == []


# =============================================================================
# Negative arm — the monolithic layout conflicts under the same scenario
# =============================================================================


def _legacy_stage(status_path: Path, plan_id: str, slug_value: str, stamp: str) -> dict[str, Any]:
    """The retired whole-document write: append to ``plans[]`` and restamp ``updated``."""
    document = json.loads(status_path.read_text(encoding='utf-8'))
    document['plans'].append(
        {
            'id': plan_id,
            'slug': slug_value,
            'workstream': 'WS-01',
            'status': 'staged',
            'plan_marshall_plan_id': '',
            'pr': '',
            'landing': '',
        }
    )
    document['updated'] = stamp
    status_path.write_text(json.dumps(document, indent=2), encoding='utf-8')
    return {'status': 'success', 'plan_id': plan_id}


class TestMonolithicLayoutConflicts:
    def test_the_same_two_machine_staging_conflicts_on_a_legacy_status_json(self, tmp_path):
        repo = tmp_path / 'legacy-epic'
        repo.mkdir()
        status_path = repo / 'status.json'
        seed = {
            'kind': 'orchestrator',
            'title': 'Legacy Epic',
            'phase': 'orchestrating',
            'workstreams': ['WS-01'],
            'plans': [
                {
                    'id': plan_id,
                    'slug': slug_value,
                    'workstream': 'WS-01',
                    'status': 'staged',
                    'plan_marshall_plan_id': '',
                    'pr': '',
                    'landing': '',
                }
                for plan_id, slug_value in SEED_ROWS
            ],
            'resume_anchor': 'seeded',
            'metadata': {},
            'created': '2020-01-01T00:00:00Z',
            'updated': '2020-01-01T00:00:00Z',
        }
        status_path.write_text(json.dumps(seed, indent=2), encoding='utf-8')
        _init_repo(repo)
        _commit_all(repo, 'seed the legacy ledger')

        merged, outcomes_a, outcomes_b = _two_machines(
            repo,
            lambda: [_legacy_stage(status_path, 'PLAN-03', 'plan-three', '2020-01-02T00:00:00Z')],
            lambda: [_legacy_stage(status_path, 'PLAN-04', 'plan-four', '2020-01-03T00:00:00Z')],
        )

        assert (_successes(outcomes_a), _successes(outcomes_b)) == (1, 1), (outcomes_a, outcomes_b)
        assert merged.returncode != 0, 'the monolithic layout merged cleanly, so the scenario proves nothing'
        assert _conflicted_paths(repo) == ['status.json']
        assert CONFLICT_MARKER in status_path.read_text(encoding='utf-8')
