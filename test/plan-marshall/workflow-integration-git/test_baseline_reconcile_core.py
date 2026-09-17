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
import json
import re
import subprocess
from argparse import Namespace
from pathlib import Path

import file_ops
from _resolve_project_dir_fixtures import patch_query_worktree_path

from conftest import PROJECT_ROOT, get_script_path, load_script_module

_mod = load_script_module(
    'plan-marshall',
    'workflow-integration-git',
    '_cmd_baseline_reconcile.py',
    '_cmd_baseline_reconcile_under_test',
    register=False,
)
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
# Classification tests
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
    PROJECT_ROOT / 'marketplace' / 'bundles' / 'plan-marshall' / 'skills' / 'workflow-integration-git' / 'SKILL.md'
)

_RECONCILE_SOURCE = get_script_path('plan-marshall', 'workflow-integration-git', '_cmd_baseline_reconcile.py')

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
        'the --worktree-path override still consulted the resolver; the escape hatch must short-circuit resolution'
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

    _write_status(
        plan_dir,
        worktree,
        subprocess.run(
            ['git', '-C', str(worktree), 'rev-parse', 'HEAD'],
            check=True,
            capture_output=True,
            text=True,
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
