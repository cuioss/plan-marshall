#!/usr/bin/env python3
"""Tests for git-workflow.py baseline-reconcile subcommand.

The subcommand is the mechanical predicate for phase-2-refine Step 3d:
fetches origin/{base_branch}, lists upstream commits since the plan's
captured worktree SHA, and runs ``git merge-tree`` to detect potential
conflicts — without modifying the worktree. Each conflicted file becomes
a Q-Gate finding (under --source qgate) so the existing phase-2-refine
iterate-to-confidence loop addresses the drift.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
from argparse import Namespace
from pathlib import Path

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
    """use_worktree=false skips entirely with reason=main_checkout_flow."""
    plan_dir = plan_context.plan_dir_for('br-mainco')
    _write_status_main_checkout(plan_dir)
    args = Namespace(
        plan_id='br-mainco',
        base_branch='main',
        worktree_path=None,
        no_emit=True,
        skip_fetch=True,
    )
    result = cmd_baseline_reconcile(args)
    assert result['status'] == 'skipped'
    assert result['reason'] == 'main_checkout_flow'


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
    import argparse  # noqa: PLC0415

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
    assert result['auto_reconciled'] is False
    assert result['findings_emitted'] == 0


def test_classification_overlap_no_content_conflict_auto_reconciles(plan_context):
    """Same-file non-overlapping line edits -> auto-merge, no findings, no loop re-entry."""
    plan_dir = plan_context.plan_dir_for('br-class-overlap-ok')
    fixture_root = plan_dir / 'fixture'
    fixture_root.mkdir(parents=True, exist_ok=True)
    _, worktree, baseline_sha = _setup_overlap_no_conflict(fixture_root)
    _write_status(plan_dir, worktree, baseline_sha)
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
    assert result['auto_reconciled'] is True
    assert result.get('merge_commit_sha')
    assert result['findings_emitted'] == 0
    # The auto-merge path no longer writes back a modified_files ledger (D4):
    # the reconcile/write-back call site was removed, so the payload must NOT
    # carry the legacy reconciled_modified_files_count observability field.
    assert 'reconciled_modified_files_count' not in result
    # The worktree HEAD should now contain both changes.
    head_text = (worktree / 'shared.txt').read_text(encoding='utf-8')
    assert 'A-local' in head_text
    assert 'H-upstream' in head_text


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
    assert result['auto_reconciled'] is False
    assert result['findings_emitted'] >= 1
    # Worktree HEAD must be unchanged (no merge attempted).
    head_after = subprocess.run(
        ['git', '-C', str(worktree), 'rev-parse', 'HEAD'],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    assert head_before == head_after
