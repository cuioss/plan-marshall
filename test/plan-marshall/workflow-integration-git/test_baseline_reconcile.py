#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for git-workflow.py baseline-reconcile subcommand.

The subcommand is the mechanical predicate for phase-2-refine Step 3d:
fetches origin/{base_branch}, lists upstream commits since the
**merge-base of HEAD and origin/{base_branch}** (recomputed per call, never
read from a stored SHA), and runs ``git merge-tree`` to detect potential
conflicts. It **moves no refs and touches no working-tree file** on any path
— though it is not side-effect-free: on the stale-base path it rewrites
``base_branch`` in ``references.json`` and emits a decision-log entry. Each
conflicted file becomes a Q-Gate finding (under --source qgate) so the
existing phase-2-refine iterate-to-confidence loop addresses the drift.
"""

from __future__ import annotations

import argparse
import ast
import importlib.util
import json
import re
import subprocess
from argparse import Namespace
from pathlib import Path

import file_ops
from _resolve_project_dir_fixtures import patch_query_worktree_path

from conftest import PROJECT_ROOT

_SCRIPTS_DIR = (
    PROJECT_ROOT
    / 'marketplace'
    / 'bundles'
    / 'plan-marshall'
    / 'skills'
    / 'workflow-integration-git'
    / 'scripts'
)


def _load_module(name, filename):
    spec = importlib.util.spec_from_file_location(name, _SCRIPTS_DIR / filename)
    assert spec is not None
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


_mod = _load_module('_cmd_baseline_reconcile_under_test', '_cmd_baseline_reconcile.py')
cmd_baseline_reconcile = _mod.cmd_baseline_reconcile


# =============================================================================
# Helpers — git fixtures
# =============================================================================


def _git(cwd: Path, *args: str) -> None:
    """Run a git command in ``cwd``; fail the test on non-zero exit."""
    subprocess.run(
        ['git', '-C', str(cwd), *args],
        check=True,
        capture_output=True,
        text=True,
    )


def _git_init_repo(repo: Path, *, default_branch: str = 'main') -> None:
    repo.mkdir(parents=True, exist_ok=True)
    _git(repo, 'init', '-q', '-b', default_branch)
    _git(repo, 'config', 'user.email', 'tests@example.com')
    _git(repo, 'config', 'user.name', 'Test')


def _commit_file(repo: Path, name: str, content: str, message: str) -> str:
    (repo / name).write_text(content, encoding='utf-8')
    _git(repo, 'add', name)
    _git(repo, 'commit', '-q', '-m', message)
    return subprocess.run(
        ['git', '-C', str(repo), 'rev-parse', 'HEAD'],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _setup_remote_and_worktree(
    fixture_root: Path,
    *,
    base_branch: str = 'main',
    upstream_commits: int = 0,
    upstream_conflicts: bool = False,
) -> tuple[Path, Path, str]:
    """Build a (bare-remote, local-clone) fixture and return paths + baseline SHA.

    The local clone simulates the worktree: it cloned at ``baseline_sha``
    and may have diverged on its branch. ``upstream_commits`` add commits
    on the remote-tracking branch after the clone; ``upstream_conflicts``
    additionally rewrites the same line in ``shared.txt`` on the local
    side so ``git merge-tree`` reports a conflict.
    """
    remote = fixture_root / 'remote.git'
    seed = fixture_root / 'seed'
    worktree = fixture_root / 'worktree'

    # Seed repo (used to bootstrap the remote with one commit).
    _git_init_repo(seed, default_branch=base_branch)
    _commit_file(seed, 'shared.txt', 'line 1\n', 'seed: initial')

    # Build the bare remote from the seed.
    subprocess.run(
        ['git', 'clone', '--bare', '-q', str(seed), str(remote)],
        check=True,
        capture_output=True,
        text=True,
    )

    # Local clone — this is what the test passes as worktree_path.
    subprocess.run(
        ['git', 'clone', '-q', str(remote), str(worktree)],
        check=True,
        capture_output=True,
        text=True,
    )
    _git(worktree, 'config', 'user.email', 'tests@example.com')
    _git(worktree, 'config', 'user.name', 'Test')
    baseline_sha = subprocess.run(
        ['git', '-C', str(worktree), 'rev-parse', 'HEAD'],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()

    # Optionally diverge the local branch (line conflict).
    if upstream_conflicts:
        _commit_file(worktree, 'shared.txt', 'line 1 (local edit)\n', 'local: edit shared')

    # Optionally land commits on the remote after the local cloned.
    if upstream_commits > 0:
        # Push from the seed repo (still on default_branch).
        for i in range(upstream_commits):
            new_content = 'line 1 (upstream)\n' if upstream_conflicts else f'extra {i}\n'
            target = 'shared.txt' if upstream_conflicts else f'upstream-{i}.txt'
            _commit_file(seed, target, new_content, f'upstream: change {i}')
        _git(seed, 'push', '-q', str(remote), base_branch)

        # The local clone needs to fetch — done by the script.

    return remote, worktree, baseline_sha


# =============================================================================
# Tests
# =============================================================================


def test_clean_no_upstream_commits(plan_context):
    """Zero upstream commits → status: success, no conflicts, no findings."""
    plan_dir = plan_context.plan_dir_for('br-clean')
    fixture_root = plan_dir / 'fixture'
    fixture_root.mkdir(parents=True, exist_ok=True)
    _, worktree, baseline_sha = _setup_remote_and_worktree(fixture_root)
    # Seed status.json so the script reads metadata.worktree_path.
    _write_status(plan_dir, worktree, baseline_sha)

    args = Namespace(
        plan_id='br-clean',
        base_branch='main',
        worktree_path=str(worktree),
        no_emit=True,
        skip_fetch=False,
    )
    result = cmd_baseline_reconcile(args)

    assert result['status'] == 'success'
    assert result['upstream_commit_count'] == 0
    assert result['conflict_count'] == 0
    assert result['findings_emitted'] == 0


def test_upstream_commits_listed_no_conflicts(plan_context):
    """N non-conflicting upstream commits → listed but no conflicts."""
    plan_dir = plan_context.plan_dir_for('br-noncfl')
    fixture_root = plan_dir / 'fixture'
    fixture_root.mkdir(parents=True, exist_ok=True)
    _, worktree, baseline_sha = _setup_remote_and_worktree(
        fixture_root,
        upstream_commits=2,
        upstream_conflicts=False,
    )
    _write_status(plan_dir, worktree, baseline_sha)

    args = Namespace(
        plan_id='br-noncfl',
        base_branch='main',
        worktree_path=str(worktree),
        no_emit=True,
        skip_fetch=False,
    )
    result = cmd_baseline_reconcile(args)

    assert result['status'] == 'success'
    assert result['upstream_commit_count'] == 2
    # Per-commit touched-files captured.
    files_seen = {f for c in result['upstream_commits'] for f in c['files']}
    assert {'upstream-0.txt', 'upstream-1.txt'}.issubset(files_seen)
    assert result['conflict_count'] == 0


def test_known_conflict_emits_finding(plan_context):
    """One conflicting upstream commit → 1 conflict, finding emitted."""
    plan_dir = plan_context.plan_dir_for('br-conflict')
    fixture_root = plan_dir / 'fixture'
    fixture_root.mkdir(parents=True, exist_ok=True)
    _, worktree, baseline_sha = _setup_remote_and_worktree(
        fixture_root,
        upstream_commits=1,
        upstream_conflicts=True,
    )
    _write_status(plan_dir, worktree, baseline_sha)

    args = Namespace(
        plan_id='br-conflict',
        base_branch='main',
        worktree_path=str(worktree),
        no_emit=False,  # exercise the emission path
        skip_fetch=False,
    )
    result = cmd_baseline_reconcile(args)

    assert result['status'] == 'success'
    assert result['conflict_count'] >= 1
    assert 'shared.txt' in result['conflicts']
    # One finding per conflicted file.
    assert result['findings_emitted'] == result['conflict_count']

    # The Q-Gate JSONL store recorded the finding under phase 2-refine.
    findings_path = plan_dir / 'artifacts' / 'findings' / 'qgate-2-refine.jsonl'
    assert findings_path.exists()
    records = [json.loads(line) for line in findings_path.read_text().splitlines() if line.strip()]
    assert any('shared.txt' in rec.get('title', '') for rec in records)


def test_main_checkout_flow_skips(plan_context):
    """``use_worktree=false`` skips entirely with reason=main_checkout_flow.

    The verdict is now derived STRUCTURALLY from the resolver's ``has_worktree``
    face, not from a hand-read of ``status.metadata.use_worktree``, so the seam
    stubbed here is ``file_ops._query_worktree_path`` — the one place the
    ``get-worktree-path`` channel is invoked. The ``status.json`` written below
    is a decoy that must not steer the outcome.
    """
    plan_dir = plan_context.plan_dir_for('br-mainco')
    _write_status_main_checkout(plan_dir)
    args = Namespace(
        plan_id='br-mainco',
        base_branch='main',
        worktree_path=None,
        no_emit=True,
        skip_fetch=True,
    )
    with patch_query_worktree_path(False) as mock:
        result = cmd_baseline_reconcile(args)

    assert result['status'] == 'skipped'
    assert result['reason'] == 'main_checkout_flow'
    assert mock.call_count == 1, (
        'the skip verdict did not come from the resolver seam — the reason is '
        'still being derived from a local status read'
    )


def test_unresolvable_plan_skips_as_status_not_found(plan_context, monkeypatch):
    """An unresolvable plan maps to ``status_not_found``, derived structurally.

    The skip-reason vocabulary is unchanged by the migration, but it is now
    reached by CATCHING ``WorktreeResolutionError`` rather than by matching the
    resolver's error TEXT. Raising an error whose message shares no wording with
    the reason proves the mapping is structural: a text-matching implementation
    would fall through to a different reason.
    """
    plan_context.plan_dir_for('br-unresolvable')

    def _raise(_plan_id):
        raise file_ops.WorktreeResolutionError('totally unrelated wording')

    monkeypatch.setattr(file_ops, '_query_worktree_path', _raise)
    args = Namespace(
        plan_id='br-unresolvable',
        base_branch='main',
        worktree_path=None,
        no_emit=True,
        skip_fetch=True,
    )
    result = cmd_baseline_reconcile(args)

    assert result['status'] == 'skipped'
    assert result['reason'] == 'status_not_found'


def test_unmaterialized_worktree_skips_as_not_materialized(plan_context):
    """A worktree opted into but not yet created gets its OWN skip reason.

    The producer publishes this state as ``worktree_state: pending``. Both it
    and a plan with no worktree at all read ``has_worktree`` false, so a reason
    selected from that boolean would report this plan as
    ``main_checkout_flow`` — telling the operator it runs against the main
    checkout when it is in fact bound to a worktree nobody has created yet.

    The paired case (``test_main_checkout_flow_skips``) changes only the
    worktree state and gets the other reason, so this arm is carried by the
    discriminator rather than by a reason that stopped varying.
    """
    plan_context.plan_dir_for('br-empty-worktree')
    args = Namespace(
        plan_id='br-empty-worktree',
        base_branch='main',
        worktree_path=None,
        no_emit=True,
        skip_fetch=True,
    )
    with patch_query_worktree_path(True, ''):
        result = cmd_baseline_reconcile(args)

    assert result['status'] == 'skipped'
    assert result['reason'] == 'worktree_not_materialized', (
        'a pending worktree was reported as a main-checkout plan, losing the '
        'distinction between "no worktree" and "no worktree YET"'
    )


def test_non_directory_worktree_path_skips_as_not_a_directory(plan_context):
    """A NON-EMPTY path that is not a directory is the guard's reachable case.

    This is the scenario the surviving ``is_dir()`` predicate exists for — a
    worktree removed or relocated after its path was persisted — and running it
    proves the classification is live rather than vestigial.
    """
    plan_dir = plan_context.plan_dir_for('br-stale-worktree')
    missing_worktree = plan_dir / 'removed-worktree'
    assert not missing_worktree.exists()
    args = Namespace(
        plan_id='br-stale-worktree',
        base_branch='main',
        worktree_path=None,
        no_emit=True,
        skip_fetch=True,
    )
    with patch_query_worktree_path(True, str(missing_worktree)):
        result = cmd_baseline_reconcile(args)

    assert result['status'] == 'skipped'
    assert result['reason'] == 'worktree_path_not_a_directory'


def test_worktree_path_override_bypasses_the_resolver_entirely(plan_context):
    """``--worktree-path`` is the escape hatch: it short-circuits resolution.

    ``_worktree_target`` keeps its argument-adapter role after the migration —
    the override is applied BEFORE the resolver is consulted, so a caller with an
    explicit path never pays (or fails on) a plan resolution. Pinning the
    zero-call count is what distinguishes the adapter from a re-deriver.
    """
    plan_dir = plan_context.plan_dir_for('br-override-noresolve')
    fixture_root = plan_dir / 'fixture'
    fixture_root.mkdir(parents=True, exist_ok=True)
    _, worktree, _ = _setup_remote_and_worktree(fixture_root)

    args = Namespace(
        plan_id='br-override-noresolve',
        base_branch='main',
        worktree_path=str(worktree),
        no_emit=True,
        skip_fetch=False,
    )
    with patch_query_worktree_path(True) as mock:
        result = cmd_baseline_reconcile(args)

    assert result['status'] == 'success'
    assert result['worktree_path'] == str(worktree)
    assert mock.call_count == 0, (
        'the --worktree-path override still consulted the resolver; the escape '
        'hatch must short-circuit resolution'
    )


def test_worktree_path_override_used_without_status(plan_context):
    """Explicit --worktree-path bypasses the status.json read."""
    plan_dir = plan_context.plan_dir_for('br-override')
    fixture_root = plan_dir / 'fixture'
    fixture_root.mkdir(parents=True, exist_ok=True)
    _, worktree, _ = _setup_remote_and_worktree(fixture_root)
    # NO status.json — override should still resolve worktree_path.
    args = Namespace(
        plan_id='br-override',
        base_branch='main',
        worktree_path=str(worktree),
        no_emit=True,
        skip_fetch=False,
    )
    result = cmd_baseline_reconcile(args)
    assert result['status'] == 'success'
    assert result['worktree_path'] == str(worktree)


def test_no_remote_skips(plan_context):
    """A repo without a remote configures returns skipped: no_remote."""
    plan_dir = plan_context.plan_dir_for('br-noremote')
    repo = plan_dir / 'repo'
    _git_init_repo(repo)
    _commit_file(repo, 'a.txt', 'a\n', 'seed')

    args = Namespace(
        plan_id='br-noremote',
        base_branch='main',
        worktree_path=str(repo),
        no_emit=True,
        skip_fetch=True,
    )
    result = cmd_baseline_reconcile(args)
    assert result['status'] == 'skipped'
    assert result['reason'] == 'no_remote'


def test_stale_base_branch_auto_updated_to_remote_default(plan_context):
    """A base_branch that no longer resolves on origin is swapped for the remote default.

    Pre-conditions: clone fixture has `origin/main` configured. Passing the
    stale ``feature/gone`` branch should trigger detection, update
    references.json, and the return TOON should report ``base_branch_updated:
    True`` plus the original branch.
    """
    plan_dir = plan_context.plan_dir_for('br-stale')
    fixture_root = plan_dir / 'fixture'
    fixture_root.mkdir(parents=True, exist_ok=True)
    _, worktree, baseline_sha = _setup_remote_and_worktree(fixture_root)
    _write_status(plan_dir, worktree, baseline_sha)
    # Seed references.json with the stale value so the auto-update has
    # something to persist over.
    (plan_dir / 'references.json').write_text(
        json.dumps({'base_branch': 'feature/gone'}),
        encoding='utf-8',
    )

    args = Namespace(
        plan_id='br-stale',
        base_branch='feature/gone',
        worktree_path=str(worktree),
        no_emit=True,
        skip_fetch=False,
    )
    result = cmd_baseline_reconcile(args)

    assert result['status'] == 'success'
    assert result['base_branch_updated'] is True
    assert result['original_base_branch'] == 'feature/gone'
    assert result['base_branch'] == 'main'

    # references.json now carries the detected default.
    refs = json.loads((plan_dir / 'references.json').read_text(encoding='utf-8'))
    assert refs['base_branch'] == 'main'


def test_current_base_branch_not_updated(plan_context):
    """When ``origin/{base_branch}`` resolves, ``base_branch_updated`` stays False."""
    plan_dir = plan_context.plan_dir_for('br-current')
    fixture_root = plan_dir / 'fixture'
    fixture_root.mkdir(parents=True, exist_ok=True)
    _, worktree, baseline_sha = _setup_remote_and_worktree(fixture_root)
    _write_status(plan_dir, worktree, baseline_sha)

    args = Namespace(
        plan_id='br-current',
        base_branch='main',
        worktree_path=str(worktree),
        no_emit=True,
        skip_fetch=False,
    )
    result = cmd_baseline_reconcile(args)

    assert result['status'] == 'success'
    assert result['base_branch_updated'] is False
    assert 'original_base_branch' not in result
    assert result['base_branch'] == 'main'


def test_stale_base_branch_no_detectable_default(plan_context):
    """When no remote default can be detected, the value is left alone.

    Pre-conditions: bare remote contains only ``feature/x`` (no ``main`` or
    ``master``). Passing a different stale branch should leave the value alone
    and bubble up the downstream fetch_failed surface.
    """
    plan_dir = plan_context.plan_dir_for('br-no-default')
    fixture_root = plan_dir / 'fixture'
    fixture_root.mkdir(parents=True, exist_ok=True)

    # Build a remote whose only branch is ``feature/x``.
    remote = fixture_root / 'remote.git'
    seed = fixture_root / 'seed'
    worktree = fixture_root / 'worktree'

    _git_init_repo(seed, default_branch='feature/x')
    _commit_file(seed, 'shared.txt', 'line 1\n', 'seed: initial')

    subprocess.run(
        ['git', 'clone', '--bare', '-q', str(seed), str(remote)],
        check=True, capture_output=True, text=True,
    )
    subprocess.run(
        ['git', 'clone', '-q', str(remote), str(worktree)],
        check=True, capture_output=True, text=True,
    )
    _git(worktree, 'config', 'user.email', 'tests@example.com')
    _git(worktree, 'config', 'user.name', 'Test')

    _write_status(
        plan_dir, worktree,
        subprocess.run(
            ['git', '-C', str(worktree), 'rev-parse', 'HEAD'],
            check=True, capture_output=True, text=True,
        ).stdout.strip(),
    )

    # feature/x is the only branch; ask for the stale ``main``.
    args = Namespace(
        plan_id='br-no-default',
        base_branch='main',
        worktree_path=str(worktree),
        no_emit=True,
        skip_fetch=False,
    )
    result = cmd_baseline_reconcile(args)

    # Auto-update should detect feature/x as the default and switch.
    assert result['base_branch'] == 'feature/x'
    assert result['base_branch_updated'] is True
    assert result['original_base_branch'] == 'main'


def test_default_base_branch_is_main(plan_context):
    """Without override or plan config, base_branch defaults to main."""
    plan_dir = plan_context.plan_dir_for('br-default-branch')
    fixture_root = plan_dir / 'fixture'
    fixture_root.mkdir(parents=True, exist_ok=True)
    _, worktree, baseline_sha = _setup_remote_and_worktree(fixture_root)
    _write_status(plan_dir, worktree, baseline_sha)

    args = Namespace(
        plan_id='br-default-branch',
        base_branch=None,
        worktree_path=str(worktree),
        no_emit=True,
        skip_fetch=False,
    )
    result = cmd_baseline_reconcile(args)
    assert result['base_branch'] == 'main'
    assert result['base_branch_source'] == 'default'


def test_baseline_reconcile_registered_in_git_workflow_cli():
    """argparse subparser routes 'baseline-reconcile' to cmd_baseline_reconcile."""
    git_workflow = _load_module('_git_workflow_dispatch_check', 'git-workflow.py')
    assert git_workflow.cmd_baseline_reconcile is cmd_baseline_reconcile or callable(
        git_workflow.cmd_baseline_reconcile
    )

    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest='cmd')
    leaf = sub.add_parser('baseline-reconcile')
    leaf.set_defaults(func=git_workflow.cmd_baseline_reconcile)
    ns = parser.parse_args(['baseline-reconcile'])
    assert ns.func is git_workflow.cmd_baseline_reconcile


# =============================================================================
# status.json helpers
# =============================================================================


def _write_status(plan_dir: Path, worktree: Path, baseline_sha: str) -> None:
    plan_dir.mkdir(parents=True, exist_ok=True)
    (plan_dir / 'status.json').write_text(
        json.dumps(
            {
                'plan_id': plan_dir.name,
                'phases': [],
                'metadata': {
                    'use_worktree': True,
                    'worktree_path': str(worktree),
                    'worktree_branch': 'feature/test',
                    'worktree_sha': baseline_sha,
                },
            }
        ),
        encoding='utf-8',
    )


def _write_status_main_checkout(plan_dir: Path) -> None:
    plan_dir.mkdir(parents=True, exist_ok=True)
    (plan_dir / 'status.json').write_text(
        json.dumps(
            {
                'plan_id': plan_dir.name,
                'phases': [],
                'metadata': {'use_worktree': False},
            }
        ),
        encoding='utf-8',
    )


# =============================================================================
# Classification tests (deliverable 6)
# =============================================================================


def _setup_overlap_no_conflict(fixture_root: Path) -> tuple[Path, Path, str]:
    """Build a fixture where upstream and in-flight touch the SAME file but
    different lines, so merge-tree predicts no conflict yet there is overlap.
    """
    remote = fixture_root / 'remote.git'
    seed = fixture_root / 'seed'
    worktree = fixture_root / 'worktree'

    _git_init_repo(seed, default_branch='main')
    _commit_file(
        seed,
        'shared.txt',
        'A\nB\nC\nD\nE\nF\nG\nH\n',
        'seed: initial',
    )
    subprocess.run(
        ['git', 'clone', '--bare', '-q', str(seed), str(remote)],
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        ['git', 'clone', '-q', str(remote), str(worktree)],
        check=True,
        capture_output=True,
        text=True,
    )
    _git(worktree, 'config', 'user.email', 'tests@example.com')
    _git(worktree, 'config', 'user.name', 'Test')
    baseline_sha = subprocess.run(
        ['git', '-C', str(worktree), 'rev-parse', 'HEAD'],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()

    # In-flight change: edit the FIRST line of shared.txt.
    _commit_file(
        worktree,
        'shared.txt',
        'A-local\nB\nC\nD\nE\nF\nG\nH\n',
        'local: edit first line',
    )
    # Upstream change: edit the LAST line of shared.txt — non-overlapping.
    _commit_file(
        seed,
        'shared.txt',
        'A\nB\nC\nD\nE\nF\nG\nH-upstream\n',
        'upstream: edit last line',
    )
    _git(seed, 'push', '-q', str(remote), 'main')

    return remote, worktree, baseline_sha


def test_classification_no_overlap(plan_context):
    """Upstream commits touch disjoint files -> classification: no_overlap."""
    plan_dir = plan_context.plan_dir_for('br-class-none')
    fixture_root = plan_dir / 'fixture'
    fixture_root.mkdir(parents=True, exist_ok=True)
    # upstream_commits=2 with upstream_conflicts=False writes
    # upstream-0.txt and upstream-1.txt; the local clone has no
    # in-flight commits, so the in-flight set is empty -> no_overlap.
    _, worktree, baseline_sha = _setup_remote_and_worktree(
        fixture_root,
        upstream_commits=2,
        upstream_conflicts=False,
    )
    _write_status(plan_dir, worktree, baseline_sha)
    args = Namespace(
        plan_id='br-class-none',
        base_branch='main',
        worktree_path=str(worktree),
        no_emit=True,
        skip_fetch=False,
    )
    result = cmd_baseline_reconcile(args)
    assert result['status'] == 'success'
    assert result['classification'] == 'no_overlap'
    assert result['auto_reconcilable'] is False
    assert result['findings_emitted'] == 0


def test_classification_overlap_no_content_conflict_is_non_mutating(plan_context):
    """Same-file non-overlapping line edits -> overlap_no_content_conflict and
    auto_reconcilable, but the probe performs NO merge: HEAD is unchanged, no
    merge_commit_sha is reported, and the working tree is untouched.

    ``auto_reconcilable`` is a truthful capability signal (the overlap CAN be
    reconciled cleanly), never a claim that a merge happened — the reconcile is
    owned by the caller's rebase step, not by this classifier.
    """
    plan_dir = plan_context.plan_dir_for('br-class-overlap-ok')
    fixture_root = plan_dir / 'fixture'
    fixture_root.mkdir(parents=True, exist_ok=True)
    _, worktree, baseline_sha = _setup_overlap_no_conflict(fixture_root)
    _write_status(plan_dir, worktree, baseline_sha)
    head_before = subprocess.run(
        ['git', '-C', str(worktree), 'rev-parse', 'HEAD'],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    args = Namespace(
        plan_id='br-class-overlap-ok',
        base_branch='main',
        worktree_path=str(worktree),
        no_emit=False,  # would emit if classification mis-routed
        skip_fetch=False,
    )
    result = cmd_baseline_reconcile(args)
    assert result['status'] == 'success'
    assert result['classification'] == 'overlap_no_content_conflict'
    assert result['auto_reconcilable'] is True
    assert result['findings_emitted'] == 0
    # Non-mutating: the real-merge focused-reconcile was removed, so there is no
    # merge commit and the ref never moved.
    assert 'merge_commit_sha' not in result
    head_after = subprocess.run(
        ['git', '-C', str(worktree), 'rev-parse', 'HEAD'],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    assert head_before == head_after, 'the probe moved HEAD on overlap_no_content_conflict'
    # The worktree file still carries only the local edit — the upstream edit
    # was NOT merged in.
    head_text = (worktree / 'shared.txt').read_text(encoding='utf-8')
    assert 'A-local' in head_text
    assert 'H-upstream' not in head_text


def test_classification_overlap_with_content_conflict_keeps_loop_entry(plan_context):
    """Conflicting line edits -> classification stays overlap_with_content_conflict,
    findings emitted, no auto-reconcile (worktree unchanged).
    """
    plan_dir = plan_context.plan_dir_for('br-class-overlap-conflict')
    fixture_root = plan_dir / 'fixture'
    fixture_root.mkdir(parents=True, exist_ok=True)
    _, worktree, baseline_sha = _setup_remote_and_worktree(
        fixture_root,
        upstream_commits=1,
        upstream_conflicts=True,
    )
    _write_status(plan_dir, worktree, baseline_sha)
    head_before = subprocess.run(
        ['git', '-C', str(worktree), 'rev-parse', 'HEAD'],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    args = Namespace(
        plan_id='br-class-overlap-conflict',
        base_branch='main',
        worktree_path=str(worktree),
        no_emit=False,
        skip_fetch=False,
    )
    result = cmd_baseline_reconcile(args)
    assert result['status'] == 'success'
    assert result['classification'] == 'overlap_with_content_conflict'
    assert result['auto_reconcilable'] is False
    assert result['findings_emitted'] >= 1
    # Worktree HEAD must be unchanged (no merge attempted).
    head_after = subprocess.run(
        ['git', '-C', str(worktree), 'rev-parse', 'HEAD'],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    assert head_before == head_after
    # A landed conflict finding reports no persist failure.
    assert 'qgate_persist_failed' not in result


# =============================================================================
# Rejected persist (P4) — the conflict finding IS this path's primary output
# =============================================================================


def test_rejected_persist_flips_status_and_carries_finding_content(plan_context, monkeypatch):
    """A REJECTED conflict-finding persist flips the status and inlines the finding.

    The conflict finding IS this path's primary output, so a lost persist must
    surface as an error carrying the rejected content inline — never a clean
    result with findings_emitted: 0 (fail-closed rule f, write direction). The
    probe no longer performs a real merge, so its only emitted finding_type
    (``triage``) is valid; the store-rejection path is exercised by stubbing the
    persist call, which is the boundary the rule actually governs.
    """
    plan_dir = plan_context.plan_dir_for('br-persist-reject')
    fixture_root = plan_dir / 'fixture'
    fixture_root.mkdir(parents=True, exist_ok=True)
    _, worktree, baseline_sha = _setup_remote_and_worktree(
        fixture_root,
        upstream_commits=1,
        upstream_conflicts=True,
    )
    _write_status(plan_dir, worktree, baseline_sha)

    def _reject(**kwargs):
        return {'status': 'error', 'message': 'Simulated store rejection'}

    monkeypatch.setattr(_mod, 'add_qgate_finding', _reject)

    args = Namespace(
        plan_id='br-persist-reject',
        base_branch='main',
        worktree_path=str(worktree),
        no_emit=False,
        skip_fetch=False,
    )
    result = cmd_baseline_reconcile(args)

    assert result['classification'] == 'overlap_with_content_conflict'
    # The finding is this path's primary output — a lost persist is an error,
    # never a clean result with findings_emitted: 0.
    assert result['status'] == 'error'
    assert result['error'] == 'finding_persist_failed'
    assert result['qgate_persist_failed'] is True
    assert result['findings_emitted'] == 0

    failure = result['qgate_persist_failures'][0]
    assert failure['finding_type'] == 'triage'
    assert 'Simulated store rejection' in failure['message']
    # The rejected finding's own content travels inline.
    assert 'merge conflict' in failure['title']
    assert 'origin/main' in failure['detail']


def test_deduplicated_conflict_finding_stays_benign(plan_context):
    """A ``deduplicated`` re-persist is benign and must not read as a rejection."""
    plan_dir = plan_context.plan_dir_for('br-persist-dedup')
    fixture_root = plan_dir / 'fixture'
    fixture_root.mkdir(parents=True, exist_ok=True)
    _, worktree, baseline_sha = _setup_remote_and_worktree(
        fixture_root,
        upstream_commits=1,
        upstream_conflicts=True,
    )
    _write_status(plan_dir, worktree, baseline_sha)
    args = Namespace(
        plan_id='br-persist-dedup',
        base_branch='main',
        worktree_path=str(worktree),
        no_emit=False,
        skip_fetch=False,
    )

    first = cmd_baseline_reconcile(args)
    assert first['status'] == 'success'
    assert first['findings_emitted'] >= 1

    second = cmd_baseline_reconcile(args)

    # Re-detection dedups: the record is still in the store, so the run stays
    # a clean success — the benign zero must never collapse onto a rejection.
    assert second['status'] == 'success'
    assert 'error' not in second
    assert 'qgate_persist_failed' not in second
    assert second['findings_emitted'] == 0


# =============================================================================
# Merge-base anchor + non-mutation (D1–D5)
# =============================================================================


def _setup_disjoint_upstream_and_local(fixture_root: Path) -> tuple[Path, Path, str]:
    """A disjoint fixture: upstream edits ``upstream.txt``; the branch edits
    ``local.txt``. Returns ``(remote, worktree, baseline_sha)``.

    The worktree carries ONE in-flight commit on ``local.txt``; the remote main
    carries ONE upstream commit on ``upstream.txt`` landed after the clone. The
    two file sets are disjoint, so a correct classifier reports ``no_overlap``.
    """
    remote = fixture_root / 'remote.git'
    seed = fixture_root / 'seed'
    worktree = fixture_root / 'worktree'

    _git_init_repo(seed, default_branch='main')
    _commit_file(seed, 'base.txt', 'base\n', 'seed: initial')
    subprocess.run(
        ['git', 'clone', '--bare', '-q', str(seed), str(remote)],
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        ['git', 'clone', '-q', str(remote), str(worktree)],
        check=True,
        capture_output=True,
        text=True,
    )
    _git(worktree, 'config', 'user.email', 'tests@example.com')
    _git(worktree, 'config', 'user.name', 'Test')
    baseline_sha = subprocess.run(
        ['git', '-C', str(worktree), 'rev-parse', 'HEAD'],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()

    # In-flight: the branch adds local.txt.
    _commit_file(worktree, 'local.txt', 'local change\n', 'local: add local.txt')
    # Upstream: a disjoint commit adds upstream.txt on the remote main.
    _commit_file(seed, 'upstream.txt', 'upstream change\n', 'upstream: add upstream.txt')
    _git(seed, 'push', '-q', str(remote), 'main')
    return remote, worktree, baseline_sha


def _behind_count(worktree: Path) -> int:
    """Number of commits ``origin/main`` is ahead of HEAD (the branch's behind-count)."""
    out = subprocess.run(
        ['git', '-C', str(worktree), 'rev-list', '--count', 'HEAD..origin/main'],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    return int(out)


def test_two_calls_after_reconcile_agree_zero_upstream_no_overlap(plan_context):
    """D5(a) + D5(d): after a focused reconcile leaves the branch 0 commits
    behind, BOTH call sites report zero upstream and ``no_overlap``, and the two
    verdicts do not contradict.

    Pre-fix (stale stored anchor) the second call — issued after ``origin/main``
    was merged into HEAD — re-lists the merged-in upstream commit as still
    upstream and flips ``no_overlap`` -> ``overlap_no_content_conflict``,
    contradicting the first call AND misreporting a 0-behind branch as 1
    upstream. Post-fix (merge-base anchor) both calls agree: 0 upstream,
    ``no_overlap``.
    """
    plan_dir = plan_context.plan_dir_for('br-two-call')
    fixture_root = plan_dir / 'fixture'
    fixture_root.mkdir(parents=True, exist_ok=True)
    _, worktree, baseline_sha = _setup_disjoint_upstream_and_local(fixture_root)
    _write_status(plan_dir, worktree, baseline_sha)

    args = Namespace(
        plan_id='br-two-call',
        base_branch='main',
        worktree_path=str(worktree),
        no_emit=True,
        skip_fetch=False,
    )

    # First call (the baseline-sync analog), BEFORE the reconcile: the branch is
    # genuinely 1 behind and the file sets are disjoint.
    first = cmd_baseline_reconcile(args)
    assert first['status'] == 'success'
    assert first['classification'] == 'no_overlap'
    assert first['upstream_commit_count'] == 1

    # Simulate the focused reconcile: merge origin/main into HEAD. The branch is
    # now 0 commits behind origin/main — the exact ground truth of the live run.
    _git(worktree, 'merge', 'origin/main', '--no-edit')
    assert _behind_count(worktree) == 0, 'fixture precondition: 0 behind after the reconcile'

    # Second call (the branch-cleanup analog) against the SAME unchanged state.
    second = cmd_baseline_reconcile(args)
    assert second['status'] == 'success'
    # D5(a): a 0-behind branch reports zero upstream and no overlap.
    assert second['upstream_commit_count'] == 0, (
        'a 0-behind branch reported upstream commits — the anchor re-listed the '
        'merged-in commit as upstream'
    )
    assert second['classification'] == 'no_overlap'
    # D5(d): the two verdicts against one unchanged state do not contradict.
    assert first['classification'] == second['classification']


def test_in_flight_set_excludes_files_the_plan_never_touched(plan_context):
    """D5(b): after a reconcile brings origin/main into HEAD, the in-flight set
    contains only the plan's own file (``local.txt``) — never the upstream file
    the plan never touched (``upstream.txt``).

    A stale anchor would diff ``{init SHA}..HEAD``, folding in the merged-in
    upstream file and inflating the in-flight set with a file the plan never
    touched.
    """
    plan_dir = plan_context.plan_dir_for('br-inflight')
    fixture_root = plan_dir / 'fixture'
    fixture_root.mkdir(parents=True, exist_ok=True)
    _, worktree, baseline_sha = _setup_disjoint_upstream_and_local(fixture_root)
    _write_status(plan_dir, worktree, baseline_sha)

    args = Namespace(
        plan_id='br-inflight',
        base_branch='main',
        worktree_path=str(worktree),
        no_emit=True,
        skip_fetch=False,
    )
    cmd_baseline_reconcile(args)  # first call fetches origin/main
    _git(worktree, 'merge', 'origin/main', '--no-edit')  # focused reconcile
    result = cmd_baseline_reconcile(args)

    assert result['status'] == 'success'
    assert 'in_flight_files' in result
    assert 'local.txt' in result['in_flight_files']
    assert 'upstream.txt' not in result['in_flight_files'], (
        'the in-flight set folded in an upstream file the plan never touched — '
        'the anchor is stale, not the merge-base'
    )


def test_merge_base_recomputed_not_read_from_stored_status(plan_context):
    """D5(c): a bogus stored ``worktree_sha`` is ignored — the anchor is the
    recomputed merge-base, so the upstream count is correct despite the poison.

    If the resolver still read ``status.metadata.worktree_sha``, the all-zero
    SHA below would make ``{sha}..origin/main`` fail and the branch read as
    0-behind. The correct answer (1 upstream) can only come from a recomputed
    merge-base.
    """
    plan_dir = plan_context.plan_dir_for('br-recompute')
    fixture_root = plan_dir / 'fixture'
    fixture_root.mkdir(parents=True, exist_ok=True)
    _, worktree, _ = _setup_disjoint_upstream_and_local(fixture_root)
    # Poison the stored anchor.
    _write_status(plan_dir, worktree, '0' * 40)

    args = Namespace(
        plan_id='br-recompute',
        base_branch='main',
        worktree_path=str(worktree),
        no_emit=True,
        skip_fetch=False,
    )
    result = cmd_baseline_reconcile(args)

    assert result['status'] == 'success'
    assert result['upstream_commit_count'] == 1, (
        'the anchor came from the poisoned stored worktree_sha, not the '
        'recomputed merge-base'
    )
    assert result.get('merge_base_source') == 'merge_base'


def test_classify_only_never_moves_head_on_every_classification(plan_context):
    """D5(e): the probe leaves HEAD byte-for-byte unchanged on EVERY
    classification — including overlap_no_content_conflict, which previously ran
    a real merge that moved the ref.
    """
    cases = [
        (
            'no_overlap',
            lambda root: _setup_remote_and_worktree(
                root, upstream_commits=2, upstream_conflicts=False
            ),
        ),
        ('overlap_no_content_conflict', _setup_overlap_no_conflict),
        (
            'overlap_with_content_conflict',
            lambda root: _setup_remote_and_worktree(
                root, upstream_commits=1, upstream_conflicts=True
            ),
        ),
    ]
    for expected, builder in cases:
        plan_dir = plan_context.plan_dir_for(f'br-nomut-{expected}')
        fixture_root = plan_dir / 'fixture'
        fixture_root.mkdir(parents=True, exist_ok=True)
        _, worktree, baseline_sha = builder(fixture_root)
        _write_status(plan_dir, worktree, baseline_sha)
        head_before = subprocess.run(
            ['git', '-C', str(worktree), 'rev-parse', 'HEAD'],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        args = Namespace(
            plan_id=f'br-nomut-{expected}',
            base_branch='main',
            worktree_path=str(worktree),
            no_emit=True,
            skip_fetch=False,
        )
        result = cmd_baseline_reconcile(args)
        head_after = subprocess.run(
            ['git', '-C', str(worktree), 'rev-parse', 'HEAD'],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        assert result['status'] == 'success'
        assert result['classification'] == expected
        assert head_before == head_after, f'the probe moved HEAD on {expected}'


def test_d3_guard_fires_when_probe_moves_head(plan_context, monkeypatch):
    """D3: a deliberate ref move DURING the probe is caught AT the probe as a
    fail-loud ``probe_mutated_head`` error — not discovered later at the landing.

    A guard never seen to fail is indistinguishable from one that cannot, so
    this test injects a ref move mid-classification (via a stubbed
    ``_detect_merge_conflicts``) and confirms the post-probe assertion fires.
    """
    plan_dir = plan_context.plan_dir_for('br-guard')
    fixture_root = plan_dir / 'fixture'
    fixture_root.mkdir(parents=True, exist_ok=True)
    _, worktree, baseline_sha = _setup_remote_and_worktree(fixture_root)
    _write_status(plan_dir, worktree, baseline_sha)

    real_detect = _mod._detect_merge_conflicts

    def _moving_detect(worktree_path, base_branch):
        # Regression stand-in: move HEAD mid-probe.
        (Path(worktree_path) / 'sneaky.txt').write_text('x\n', encoding='utf-8')
        subprocess.run(
            ['git', '-C', worktree_path, 'add', 'sneaky.txt'],
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ['git', '-C', worktree_path, 'commit', '-q', '-m', 'sneaky mid-probe commit'],
            check=True,
            capture_output=True,
        )
        return real_detect(worktree_path, base_branch)

    monkeypatch.setattr(_mod, '_detect_merge_conflicts', _moving_detect)

    args = Namespace(
        plan_id='br-guard',
        base_branch='main',
        worktree_path=str(worktree),
        no_emit=True,
        skip_fetch=False,
    )
    result = cmd_baseline_reconcile(args)

    assert result['status'] == 'error'
    assert result['error'] == 'probe_mutated_head'
    assert result['head_before'] != result['head_after']


# ---------------------------------------------------------------------------
# The stale-base auto-update is authoritative for the NEXT call
# ---------------------------------------------------------------------------
#
# Raised by automated review on the PR that added the return-contract docs:
# `_maybe_auto_update_stale_base_branch` persisted a corrected `base_branch`
# into references.json, but `_resolve_base_branch` read only the marshal config
# and never the references file. The write was therefore inert -- every call
# re-resolved the stale configured branch, re-detected it as stale, and
# rewrote the same correction, so the "auto-update" never governed anything.
#
# These pin the resolution ORDER rather than one call's return value, because
# the defect was only observable across two calls.


def test_persisted_base_branch_outranks_the_configured_one(monkeypatch):
    """The value the auto-update wrote is what the next call resolves.

    This is the regression: with resolution reading only the config, the
    persisted correction is invisible and this returns the stale configured
    branch instead.
    """
    monkeypatch.setattr(_mod, '_read_references_base_branch', lambda plan_id: 'release-2')
    monkeypatch.setattr(
        _mod, 'load_config', lambda: {'plan': {'phase-2-refine': {'base_branch': 'stale-main'}}},
        raising=False,
    )

    branch, source = _mod._resolve_base_branch('some-plan', None)

    assert (branch, source) == ('release-2', 'plan_references'), (
        'the persisted per-plan base_branch must outrank the project-wide config, '
        'otherwise the stale-base auto-update can never become authoritative'
    )


def test_cli_override_still_outranks_the_persisted_value(monkeypatch):
    """An explicit operator argument beats persisted state.

    The control on the test above: raising the reference above the config must
    not raise it above `--base-branch`, which is the one source a human typed.
    """
    monkeypatch.setattr(_mod, '_read_references_base_branch', lambda plan_id: 'release-2')

    assert _mod._resolve_base_branch('some-plan', 'explicit') == ('explicit', 'cli')


def test_resolution_falls_through_to_config_when_no_reference_is_persisted(monkeypatch):
    """A plan with no persisted base_branch still resolves from the config.

    Anti-regression for the fail-soft path: reading references must not become a
    precondition, or every plan without a references entry would resolve to the
    hardcoded default and silently ignore its configured branch.
    """
    import _config_core

    monkeypatch.setattr(_mod, '_read_references_base_branch', lambda plan_id: None)
    # `load_config` is imported INSIDE `_resolve_base_branch`, so the patch has to
    # land on the source module -- patching `_mod.load_config` is silently
    # ineffective and would make this test pass for the wrong reason.
    monkeypatch.setattr(
        _config_core, 'load_config',
        lambda: {'plan': {'phase-2-refine': {'base_branch': 'configured'}}},
    )

    branch, source = _mod._resolve_base_branch('some-plan', None)

    assert (branch, source) == ('configured', 'plan_config')


def test_reader_is_fail_soft_on_every_unavailability_path(monkeypatch):
    """A missing, unreadable or malformed references body yields None, never a raise.

    The probe must stay usable on a plan that has no references file; an
    exception here would turn a soft fallback into a hard failure of the whole
    baseline-reconcile call.
    """
    import _references_core

    # `read_references` is imported INSIDE the function, so the patch must land on
    # `_references_core` -- patching `_mod.read_references` sets a module attribute
    # nothing reads, and every assertion below would pass without exercising the
    # bodies at all. That vacuous form shipped once and was caught in review; the
    # sibling config test carries the same warning for the same reason.
    #
    # Every exception the guard catches is raised here, not just the first. A test
    # named "every unavailability path" that exercises one of three is the same
    # over-claim in a different shape: a narrowed `except FileNotFoundError` would
    # let the other two escape as hard failures and this test would stay green.
    for exc in (FileNotFoundError, OSError, ValueError):
        def _raises(plan_id, e=exc):
            raise e(plan_id)

        monkeypatch.setattr(_references_core, 'read_references', _raises)
        assert _mod._read_references_base_branch('absent-plan') is None, (
            f'{exc.__name__} must be caught and yield None, not propagate'
        )

    for body in ({}, {'base_branch': ''}, {'base_branch': '   '}, {'base_branch': 42}, []):
        monkeypatch.setattr(_references_core, 'read_references', lambda plan_id, b=body: b)
        assert _mod._read_references_base_branch('p') is None, f'body {body!r} must yield None'


# =============================================================================
# The documented reason / error vocabularies are BOUND to the emitting script (D4)
# =============================================================================
#
# ``workflow-integration-git/SKILL.md`` tables every ``status: skipped`` reason and
# every ``status: error`` token this subcommand can return. Nothing compared the
# two: a token added, renamed, or removed in ``_cmd_baseline_reconcile.py`` left
# the table quietly wrong, and a reader consulting the documented vocabulary would
# act on a token the script no longer emits — or miss one it does.
#
# Both sides are DERIVED. The documented side is parsed out of the tables (a
# transcription here would be a third copy that can drift from both); the emitted
# side is read from the module's own AST (a second literal list would be exactly
# the restatement this guard exists to forbid).

_SKILL_DOC = (
    PROJECT_ROOT
    / 'marketplace'
    / 'bundles'
    / 'plan-marshall'
    / 'skills'
    / 'workflow-integration-git'
    / 'SKILL.md'
)

_RECONCILE_SOURCE = _SCRIPTS_DIR / '_cmd_baseline_reconcile.py'

#: The function whose ``return None, '<token>'`` tuples ARE the worktree-resolution
#: skip reasons. Six of the eleven documented reasons reach the payload only
#: through this helper, so an emitted-side derivation that looked solely at
#: ``'reason': …`` dict literals would miss them and pass while the table drifted.
_SKIP_REASON_FUNCTION = '_worktree_target'


def _table_tokens(heading_cell: str, doc_text: str | None = None) -> set[str]:
    """Parse the backticked tokens from the first column of one SKILL.md table.

    ``heading_cell`` is the table's first header cell (``reason`` / ``error``),
    which is what distinguishes the two tables from every other table in the doc.

    A first column may group several tokens in ONE slash-joined cell — the
    worktree-resolution row does exactly that, listing four reasons together — so
    every backticked run in the cell is collected rather than the cell being read
    as a single token. A parser that took the cell verbatim would yield one
    unmatchable string and make the comparison vacuous for those four.

    ``doc_text`` overrides the document read, and exists so the control below can
    drive THIS parser over an injected row rather than restating set algebra over
    a locally-built set. The default is the real doc, so every caller that omits
    it is unaffected.
    """
    lines = (doc_text or _SKILL_DOC.read_text(encoding='utf-8')).splitlines()
    tokens: set[str] = set()
    index = 0
    while index < len(lines):
        line = lines[index].strip()
        if line.startswith('|') and index + 1 < len(lines):
            cells = [c.strip() for c in line.strip('|').split('|')]
            delimiter = lines[index + 1].strip()
            if (
                cells
                and cells[0].strip('`') == heading_cell
                and delimiter.startswith('|')
                and set(delimiter) <= set('|-: ')
            ):
                row = index + 2
                while row < len(lines) and lines[row].strip().startswith('|'):
                    first = lines[row].strip().strip('|').split('|')[0]
                    tokens.update(re.findall(r'`([a-z0-9_]+)`', first))
                    row += 1
                index = row
                continue
        index += 1
    return tokens


def _emitted_tokens(source_text: str | None = None) -> tuple[set[str], set[str]]:
    """The ``reason`` and ``error`` tokens the script actually emits, from its AST.

    Three emission shapes are recognised, which together cover every site:

    * a ``{'reason': '<token>'}`` / ``{'error': '<token>'}`` dict entry — including
      the ``skip_reason or '<fallback>'`` form, whose constant operand is the
      fallback reason;
    * a ``payload['error'] = '<token>'`` subscript assignment;
    * a ``return None, '<token>'`` tuple inside :data:`_SKIP_REASON_FUNCTION`, the
      helper that owns the six worktree-resolution reasons.

    ``source_text`` overrides the source read, and exists so the control below can
    drive THIS AST derivation over an injected emission site. The default is the
    real script, so every caller that omits it is unaffected.
    """
    tree = ast.parse(source_text or _RECONCILE_SOURCE.read_text(encoding='utf-8'))
    reasons: set[str] = set()
    errors: set[str] = set()

    def _constants(node: ast.AST) -> list[str]:
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return [node.value]
        if isinstance(node, ast.BoolOp):
            found: list[str] = []
            for operand in node.values:
                found.extend(_constants(operand))
            return found
        return []

    for node in ast.walk(tree):
        if isinstance(node, ast.Dict):
            for key, value in zip(node.keys, node.values, strict=True):
                if not (isinstance(key, ast.Constant) and isinstance(key.value, str)):
                    continue
                if key.value == 'reason':
                    reasons.update(_constants(value))
                elif key.value == 'error':
                    errors.update(_constants(value))
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if (
                    isinstance(target, ast.Subscript)
                    and isinstance(target.slice, ast.Constant)
                    and target.slice.value in ('reason', 'error')
                ):
                    bucket = reasons if target.slice.value == 'reason' else errors
                    bucket.update(_constants(node.value))

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == _SKIP_REASON_FUNCTION:
            for inner in ast.walk(node):
                if isinstance(inner, ast.Return) and isinstance(inner.value, ast.Tuple):
                    elements = inner.value.elts
                    if len(elements) == 2:
                        reasons.update(_constants(elements[1]))

    return reasons, errors


def test_documented_reason_and_error_vocabularies_match_the_script():
    """The two documented tables equal the token sets the script emits.

    Compared as SETS in both directions: a documented token the script never
    emits sends a reader chasing a state that cannot occur, and an emitted token
    the table omits leaves a real outcome undocumented.
    """
    documented_reasons = _table_tokens('reason')
    documented_errors = _table_tokens('error')
    emitted_reasons, emitted_errors = _emitted_tokens()

    # Vacuity guard FIRST — an empty parse on either side would make every set
    # comparison below trivially true (or trivially false) for the wrong reason.
    assert documented_reasons, (
        f'parsed no `reason` tokens out of {_SKILL_DOC}; the table moved, was '
        f'renamed, or the parser broke — the comparison would be vacuous'
    )
    assert documented_errors, f'parsed no `error` tokens out of {_SKILL_DOC}'
    assert emitted_reasons, (
        f'derived no reason tokens from {_RECONCILE_SOURCE}; the emission shapes '
        f'changed and the AST derivation no longer recognises them'
    )
    assert emitted_errors, f'derived no error tokens from {_RECONCILE_SOURCE}'

    # Published on a clean run, so the run states how much it compared.
    print(
        f'baseline-reconcile vocabulary: documented_reasons={len(documented_reasons)} '
        f'emitted_reasons={len(emitted_reasons)} '
        f'documented_errors={len(documented_errors)} '
        f'emitted_errors={len(emitted_errors)}'
    )

    assert documented_reasons == emitted_reasons, (
        f'the documented skip-reason vocabulary and the one the script emits '
        f'disagree (examined {len(documented_reasons)} documented, '
        f'{len(emitted_reasons)} emitted). '
        f'Documented but never emitted: {sorted(documented_reasons - emitted_reasons)}; '
        f'emitted but undocumented: {sorted(emitted_reasons - documented_reasons)}'
    )
    assert documented_errors == emitted_errors, (
        f'the documented error vocabulary and the one the script emits disagree '
        f'(examined {len(documented_errors)} documented, {len(emitted_errors)} '
        f'emitted). '
        f'Documented but never emitted: {sorted(documented_errors - emitted_errors)}; '
        f'emitted but undocumented: {sorted(emitted_errors - documented_errors)}'
    )


def test_the_slash_joined_reason_row_expands_to_every_token_it_groups():
    """The grouped cell is expanded, not read as one unmatchable string.

    One documented row lists four worktree-resolution reasons in a single
    slash-joined cell. A parser that took the cell verbatim would produce one
    token matching nothing, and the equality above would then fail for a parsing
    reason while those four reasons went effectively unchecked. Pinning the
    expansion keeps the row's four members inside the compared set.
    """
    documented = _table_tokens('reason')
    grouped = {
        'status_not_found',
        'status_module_unavailable',
        'worktree_path_missing',
        'worktree_path_not_a_directory',
    }

    assert grouped <= documented, (
        f'the slash-joined row did not expand; missing {sorted(grouped - documented)}. '
        f'Parsed: {sorted(documented)}'
    )
    # The row really is joined — otherwise this asserts nothing about grouping.
    text = _SKILL_DOC.read_text(encoding='utf-8')
    assert '`status_not_found` / `status_module_unavailable`' in text, (
        'the grouped row is no longer slash-joined, so this test no longer '
        'demonstrates that the parser expands such a cell'
    )


#: A table row injected into the doc for a reason the script never emits. Written
#: as a whole table so the injection exercises the parser's header match,
#: delimiter check, and backtick extraction — not just its row loop.
_INJECTED_DOC_ROW = (
    '\n| `reason` | Meaning |\n'
    '|---|---|\n'
    '| `control_only_documented_reason` | a state the script cannot reach |\n'
)

#: An emission site appended to the script source for a reason the table omits.
#: A ``{'reason': …}`` dict literal — one of the three shapes the AST derivation
#: claims to recognise — so the injection tests that recognition.
_INJECTED_EMISSION_SITE = (
    "\n\ndef _control_only_emission():\n"
    "    return {'reason': 'control_only_emitted_reason'}\n"
)


def test_an_injected_token_on_either_side_is_derived_and_flagged():
    """Matched control pair: BOTH derivations resolve an injected divergence.

    The guard compares two DERIVED sets, so a control that builds two sets
    locally and unions a phantom into one of them controls the ``-`` operator
    and nothing else: given the matched case immediately below, such an
    assertion reduces to "the phantom is not in the other set", which is true of
    any string nobody uses. It cannot fail for any change to
    :func:`_table_tokens` or :func:`_emitted_tokens` — the parts that can
    actually break.

    Each direction here injects into the SUBSTRATE instead, and each fails for
    its own reason:

    * DOCUMENTED side — a table row for a state the script cannot reach. Red if
      :func:`_table_tokens` stops parsing a table (header match, delimiter
      check, or backtick extraction), which is also what would make the guard
      silently compare an empty documented set.
    * EMITTED side — a ``{'reason': …}`` emission site the table omits. Red if
      :func:`_emitted_tokens` stops recognising that dict shape, which is what
      would make the guard silently compare an empty emitted set.

    The matched (uninjected) pair is asserted first, so a divergence already
    present in the real corpus cannot masquerade as the injected one.
    """
    documented_reasons = _table_tokens('reason')
    emitted_reasons, _emitted_errors = _emitted_tokens()

    # The matched (unmodified) case: no divergence in either direction.
    assert documented_reasons == emitted_reasons, (
        f'the real corpus already diverges, so neither injection below is '
        f'attributable to the injection. Documented but never emitted: '
        f'{sorted(documented_reasons - emitted_reasons)}; emitted but '
        f'undocumented: {sorted(emitted_reasons - documented_reasons)}'
    )

    # DOCUMENTED side — parse a doc carrying one extra row, through the real parser.
    injected_doc = _SKILL_DOC.read_text(encoding='utf-8') + _INJECTED_DOC_ROW
    documented_with_phantom = _table_tokens('reason', doc_text=injected_doc)

    assert documented_with_phantom - documented_reasons == {
        'control_only_documented_reason'
    }, (
        f'the table parser did not pick up the injected row, so the '
        f'documented-side derivation is not being driven. Parsed: '
        f'{sorted(documented_with_phantom - documented_reasons)}'
    )
    assert documented_with_phantom != emitted_reasons, (
        'a documented-but-never-emitted token left the guard equality intact'
    )
    assert documented_with_phantom - emitted_reasons == {
        'control_only_documented_reason'
    }, 'a documented-but-never-emitted token was not detected'

    # EMITTED side — derive from a source carrying one extra emission site.
    injected_source = _RECONCILE_SOURCE.read_text(encoding='utf-8') + _INJECTED_EMISSION_SITE
    emitted_with_phantom, _ = _emitted_tokens(source_text=injected_source)

    assert emitted_with_phantom - emitted_reasons == {'control_only_emitted_reason'}, (
        f'the AST derivation did not pick up the injected emission site, so the '
        f'emitted-side derivation is not being driven. Derived: '
        f'{sorted(emitted_with_phantom - emitted_reasons)}'
    )
    assert emitted_with_phantom != documented_reasons, (
        'an emitted-but-undocumented token left the guard equality intact'
    )
    assert emitted_with_phantom - documented_reasons == {'control_only_emitted_reason'}, (
        'an emitted-but-undocumented token was not detected'
    )
