#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for git-workflow.py - consolidated git workflow script.

Tier 2 (direct import) tests with subprocess tests for CLI plumbing.
"""

from __future__ import annotations

import os
import re
import subprocess
from argparse import Namespace
from pathlib import Path

import pytest
from toon_parser import parse_toon

from conftest import get_script_path, load_script_module, run_script

# Script under test (for subprocess CLI plumbing tests)
SCRIPT_PATH = get_script_path('plan-marshall', 'workflow-integration-git', 'git-workflow.py')

# The entrypoint filename is kebab-case (git-workflow.py), which is not a
# valid Python module identifier — load it via importlib instead of `import`.
git_workflow = load_script_module('plan-marshall', 'workflow-integration-git', 'git-workflow.py', 'git_workflow')
_SKIP_DIRS = git_workflow._SKIP_DIRS
SAFE_ARTIFACT_PATTERNS = git_workflow.SAFE_ARTIFACT_PATTERNS
UNCERTAIN_ARTIFACT_PATTERNS = git_workflow.UNCERTAIN_ARTIFACT_PATTERNS
VALID_TYPES = git_workflow.VALID_TYPES

# ⛔ Vacuity guard — the vocabulary is production's, so emptying it there collects zero
# cases at the parametrize below and still reports green.
assert VALID_TYPES, 'git_workflow.VALID_TYPES is empty'
analyze_diff = git_workflow.analyze_diff
cmd_detect_artifacts = git_workflow.cmd_detect_artifacts
cmd_format_commit = git_workflow.cmd_format_commit
get_tracked_files = git_workflow.get_tracked_files
scan_artifacts = git_workflow.scan_artifacts
wrap_text = git_workflow.wrap_text


def run_git_script(args: list) -> tuple:
    """Run git_workflow.py with args and return (stdout, stderr, returncode)."""
    result = run_script(SCRIPT_PATH, *args)
    return result.stdout, result.stderr, result.returncode


def _format_commit_args(**overrides) -> Namespace:
    """Build a cmd_format_commit Namespace with sensible defaults for unset fields."""
    fields = {
        'commit_type': 'feat',
        'scope': None,
        'subject': 'subject',
        'body': None,
        'breaking': None,
        'footer': None,
    }
    fields.update(overrides)
    return Namespace(**fields)


def _create_file(root: Path, relpath: str) -> None:
    """Create a file (with parents) within ``root``."""
    full = root / relpath
    full.parent.mkdir(parents=True, exist_ok=True)
    full.write_text('test')


def _git_init_with_identity(repo: Path) -> None:
    """Initialise a git repo with a throwaway committer identity."""
    subprocess.run(['git', 'init'], cwd=repo, capture_output=True)
    subprocess.run(['git', 'config', 'user.email', 'test@test.com'], cwd=repo, capture_output=True)
    subprocess.run(['git', 'config', 'user.name', 'Test'], cwd=repo, capture_output=True)


def _repo_with_live_worktree(root: Path, worktree_path: Path, branch: str = 'feature/EXAMPLE-PLAN') -> Path:
    """Init ``root`` as a repo with one commit and a linked worktree at ``worktree_path``.

    Models how plan-marshall runs a plan: in a linked git worktree that
    ``git ls-files`` treats as a separate-checkout boundary (it never
    enumerates the worktree's contents), while ``os.walk`` descends into it.
    Returns ``worktree_path`` for convenience.
    """
    _git_init_with_identity(root)
    _create_file(root, 'README.md')
    subprocess.run(['git', 'add', '.'], cwd=root, capture_output=True)
    subprocess.run(['git', 'commit', '-m', 'init'], cwd=root, capture_output=True)
    subprocess.run(['git', 'branch', branch], cwd=root, capture_output=True)
    worktree_path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(['git', 'worktree', 'add', str(worktree_path), branch], cwd=root, capture_output=True)
    return worktree_path


#: A running plan's live audit trail, sited directly under the scan root.
_PLAN_STATE_WORKLOG = '.plan/local/plans/EXAMPLE-PLAN/logs/work.log'


def _plan_worktree_scan_root(root: Path) -> None:
    """Model a plan worktree as the scan ROOT: live plan state plus a control artifact.

    Distinct from :func:`_repo_with_live_worktree`, which sites the plan checkout
    *beneath* the scan root where the nested-boundary pruning already covers it.
    Here the plan state is a plain directory directly under the root, so no
    boundary pruning applies and only the unconditional plan-state exclusion can
    keep it out of the offered buckets.
    """
    _git_init_with_identity(root)
    _create_file(root, 'README.md')
    subprocess.run(['git', 'add', 'README.md'], cwd=root, capture_output=True)
    subprocess.run(['git', 'commit', '-m', 'init'], cwd=root, capture_output=True)
    _create_file(root, _PLAN_STATE_WORKLOG)
    _create_file(root, 'scratch.temp')


def _assert_plan_state_excluded_control_safe(result: dict) -> None:
    """The plan's own work.log is offered nowhere, while the control still reaches ``safe``.

    The control assertion is the non-vacuity guard: an empty scan would satisfy
    the negative on its own, which is precisely the confusion this epic is named
    for.
    """
    offered = result['safe'] + result['uncertain']
    assert not any('work.log' in f for f in offered), (
        f"the scan root's own live plan state was offered for deletion: {offered}"
    )
    assert 'scratch.temp' in result['safe'], (
        f'control artifact missing from safe — the exclusion above would be vacuous on an empty scan: {result["safe"]}'
    )



# The identity an unconfigured checkout commits under. Owned by
# manage-run-config (COMMIT_TRAILER_*_DEFAULT) and documented in CLAUDE.md
# § "Commit Trailer"; restated here as the executable form of it.
DEFAULT_COAUTHOR_TRAILER = 'Co-Authored-By: plan-marshall <noreply@cuioss.de>'

# Assistant and vendor names that must never appear in a trailer, whatever the
# configured identity is. The trailer names the system that produced the commit,
# so any of these in one means the convention has been reverted somewhere.
FORBIDDEN_COAUTHOR_TOKENS = (
    'anthropic',
    'claude',
    'openai',
    'chatgpt',
    'gpt-',
    'copilot',
    'gemini',
    'codex',
    'cursor',
)

# Matches a trailer wherever it appears — in a commit template, a skill's worked
# example, or a test fixture's expected output — and captures the identity ONLY,
# not the line around it. Matching the whole line would flag prose that merely
# names a file (CLAUDE.md) beside a perfectly canonical trailer. Assembled from
# concatenated pieces so this pattern does not itself match the sweep.
_TRAILER_PATTERN = re.compile('Co-Authored' + r'-By:\s*[^<>\n]*<[^<>\n]*>')


def _repo_root() -> Path:
    """Repository root, resolved from git rather than from __file__ depth."""
    result = subprocess.run(
        ['git', 'rev-parse', '--show-toplevel'],
        cwd=Path(__file__).resolve().parent,
        capture_output=True,
        text=True,
        check=True,
    )
    return Path(result.stdout.strip())


def _tracked_trailer_lines() -> tuple[list[tuple[str, str]], int]:
    """Every stated co-author trailer in tracked files, with the files scanned.

    Returns ``(occurrences, files_scanned)`` where each occurrence is
    ``(repo-relative path, the trailer text)`` — the trailer alone, so
    surrounding prose cannot be mistaken for part of the identity.
    ``files_scanned`` is published so an empty or truncated sweep cannot pass as
    a clean result.

    A trailer carrying a ``{placeholder}`` is a composition template rather than
    a stated identity, and is excluded: the value it renders is decided at
    runtime, so judging the template against a literal identity would be a
    category error.
    """
    root = _repo_root()
    listing = subprocess.run(
        ['git', 'ls-files', '-z'],
        cwd=root,
        capture_output=True,
        text=True,
        check=True,
    )
    occurrences: list[tuple[str, str]] = []
    scanned = 0
    for rel in listing.stdout.split('\0'):
        if not rel:
            continue
        path = root / rel
        try:
            content = path.read_text(encoding='utf-8')
        except (OSError, UnicodeDecodeError):
            continue  # binary or unreadable — carries no trailer
        scanned += 1
        for match in _TRAILER_PATTERN.finditer(content):
            trailer = match.group(0)
            if '{' in trailer:
                continue
            occurrences.append((rel, trailer))
    return occurrences, scanned



class TestBranchSyncState:
    """branch-sync-state — push-parity verdicts driving the barrier re-fire rule.

    Repo-fixture tests reproducing the observed nifi shape: a work repo with a
    ``file://`` bare origin. Metadata resolution (worktree path + branch) is
    monkeypatched onto the real fixture repo; the git comparison itself runs
    against real refs.
    """

    BRANCH = 'feature/sync-plan'

    def _seed_repo_with_origin(self, tmp_path: Path) -> Path:
        """Create a work repo on BRANCH with a ``file://`` bare origin."""
        origin = tmp_path / 'origin.git'
        origin.mkdir()
        subprocess.run(['git', 'init', '--bare'], cwd=origin, capture_output=True)
        work = tmp_path / 'work'
        work.mkdir()
        _git_init_with_identity(work)
        # Worktree fixtures carry a .gitignore covering .plan/ per the
        # established fixture convention.
        (work / '.gitignore').write_text('.plan/\n')
        (work / 'file.txt').write_text('one')
        subprocess.run(['git', 'add', '.'], cwd=work, capture_output=True)
        subprocess.run(['git', 'commit', '-m', 'init'], cwd=work, capture_output=True)
        subprocess.run(['git', 'checkout', '-b', self.BRANCH], cwd=work, capture_output=True)
        subprocess.run(['git', 'remote', 'add', 'origin', f'file://{origin}'], cwd=work, capture_output=True)
        return work

    def _push(self, work: Path) -> None:
        subprocess.run(['git', 'push', '-u', 'origin', self.BRANCH], cwd=work, capture_output=True)

    def _seed_merged_and_deleted(self, tmp_path: Path) -> Path:
        """Feature branch whose work LANDED on ``origin/main`` with no
        ``origin/{branch}`` tracking ref — the merged-and-deleted shape.

        HEAD is an ancestor of ``origin/main`` (the feature commit was
        fast-forward-merged into main and pushed) and the feature branch itself
        was never pushed, so ``origin/{branch}`` does not resolve.
        """
        origin = tmp_path / 'origin.git'
        origin.mkdir()
        subprocess.run(['git', 'init', '--bare'], cwd=origin, capture_output=True)
        work = tmp_path / 'work'
        work.mkdir()
        _git_init_with_identity(work)
        (work / '.gitignore').write_text('.plan/\n')
        (work / 'file.txt').write_text('one')
        subprocess.run(['git', 'add', '.'], cwd=work, capture_output=True)
        subprocess.run(['git', 'commit', '-m', 'init'], cwd=work, capture_output=True)
        # Deterministic base branch name regardless of the git default.
        subprocess.run(['git', 'branch', '-M', 'main'], cwd=work, capture_output=True)
        subprocess.run(['git', 'remote', 'add', 'origin', f'file://{origin}'], cwd=work, capture_output=True)
        subprocess.run(['git', 'push', '-u', 'origin', 'main'], cwd=work, capture_output=True)
        # Feature branch with a commit, fast-forward-merged into main and pushed.
        subprocess.run(['git', 'checkout', '-b', self.BRANCH], cwd=work, capture_output=True)
        (work / 'feature.txt').write_text('feat')
        subprocess.run(['git', 'add', '.'], cwd=work, capture_output=True)
        subprocess.run(['git', 'commit', '-m', 'feature work'], cwd=work, capture_output=True)
        feature_tip = self._rev_parse(work, 'HEAD')
        subprocess.run(['git', 'checkout', 'main'], cwd=work, capture_output=True)
        subprocess.run(['git', 'merge', '--ff-only', self.BRANCH], cwd=work, capture_output=True)
        subprocess.run(['git', 'push', 'origin', 'main'], cwd=work, capture_output=True)
        # Return to the feature branch; its tip is now an ancestor of origin/main
        # and origin/{BRANCH} was never pushed.
        subprocess.run(['git', 'checkout', self.BRANCH], cwd=work, capture_output=True)
        assert self._rev_parse(work, 'HEAD') == feature_tip
        return work

    def _commit_past_origin(self, work: Path) -> None:
        (work / 'file.txt').write_text('two')
        subprocess.run(['git', 'commit', '-am', 'local-only'], cwd=work, capture_output=True)

    def _rev_parse(self, work: Path, ref: str) -> str:
        result = subprocess.run(['git', 'rev-parse', ref], cwd=work, capture_output=True, text=True)
        return result.stdout.strip()

    def _state(self, monkeypatch, work: Path) -> dict:
        monkeypatch.setattr(git_workflow, '_resolve_worktree_path_for_plan', lambda plan_id: (work, None))
        monkeypatch.setattr(git_workflow, '_read_metadata_field', lambda plan_id, field: self.BRANCH)
        return dict(git_workflow.cmd_branch_sync_state(Namespace(plan_id='sync-plan')))

    def test_synced_after_push(self, tmp_path: Path, monkeypatch):
        """Local HEAD equal to origin/{branch} reports state: synced."""
        work = self._seed_repo_with_origin(tmp_path)
        self._push(work)

        result = self._state(monkeypatch, work)

        assert result['status'] == 'success'
        assert result['state'] == 'synced'
        assert result['branch'] == self.BRANCH
        assert result['head_sha'] == self._rev_parse(work, 'HEAD')
        assert result['remote_sha'] == result['head_sha']

    def test_ahead_after_local_commit(self, tmp_path: Path, monkeypatch):
        """A local commit past origin reports state: ahead (re-fire verdict)."""
        work = self._seed_repo_with_origin(tmp_path)
        self._push(work)
        self._commit_past_origin(work)

        result = self._state(monkeypatch, work)

        assert result['status'] == 'success'
        assert result['state'] == 'ahead'
        assert result['head_sha'] == self._rev_parse(work, 'HEAD')
        assert result['remote_sha'] == self._rev_parse(work, f'origin/{self.BRANCH}')
        assert result['head_sha'] != result['remote_sha']

    def test_remote_absent_unverified_when_never_pushed(self, tmp_path: Path, monkeypatch):
        """A never-pushed branch with no resolvable base ref reports
        ``remote_absent_unverified`` — the DECLINE verdict, not a re-fire.

        An absent tracking ref is ambiguous: never-pushed and
        squash-merged-and-deleted are indistinguishable from local state alone.
        With no ``origin/main`` to prove containment, the verb declines to
        assert "safe to re-push" rather than routing to a resurrecting re-fire.
        """
        work = self._seed_repo_with_origin(tmp_path)

        result = self._state(monkeypatch, work)

        assert result['status'] == 'success'
        assert result['state'] == 'remote_absent_unverified'
        assert result['head_sha'] == self._rev_parse(work, 'HEAD')
        assert 'remote_sha' not in result

    def test_remote_absent_landed_when_merged_and_deleted(self, tmp_path: Path, monkeypatch):
        """A merged-and-deleted branch reports ``remote_absent_landed`` — never a
        re-fire verdict.

        The branch's work is contained in ``origin/main`` (HEAD is an ancestor)
        and its remote branch was deleted after the merge. Re-pushing here would
        resurrect a landed branch, so the verdict is disambiguated as landed and
        the consumer must NOT re-fire.
        """
        work = self._seed_merged_and_deleted(tmp_path)

        result = self._state(monkeypatch, work)

        assert result['status'] == 'success'
        assert result['state'] == 'remote_absent_landed'
        assert result['base_branch'] == 'main'
        assert 'remote_sha' not in result

    def test_missing_branch_metadata_is_error(self, tmp_path: Path, monkeypatch):
        """Absent worktree_branch metadata surfaces worktree_not_materialized."""
        work = self._seed_repo_with_origin(tmp_path)
        monkeypatch.setattr(git_workflow, '_resolve_worktree_path_for_plan', lambda plan_id: (work, None))
        monkeypatch.setattr(git_workflow, '_read_metadata_field', lambda plan_id, field: '')

        result = git_workflow.cmd_branch_sync_state(Namespace(plan_id='sync-plan'))

        assert result['status'] == 'error'
        assert result['error'] == 'worktree_not_materialized'

    def test_verdict_token_drives_refire_skip_mapping(self, tmp_path: Path, monkeypatch):
        """The PRODUCTION mapping — not a local oracle — decides the barrier action.

        Per phase-6-finalize/SKILL.md the push barrier re-fires ONLY on a
        present-but-behind tracking ref (``ahead``). A ref-absent verdict never
        re-fires: ``synced`` skips, ``remote_absent_landed`` skips (the work is
        already on the base — re-pushing would resurrect it), and
        ``remote_absent_unverified`` DECLINES (the ambiguity is surfaced, not
        resolved by a resurrecting re-push). Only ``ahead`` is a re-fire.

        The mapping under assertion is ``git_workflow.push_barrier_action`` —
        the function the payload's ``barrier_action`` field is computed by and
        the dispatcher branches on. A local ``def verdict(state)`` here would
        assert this module's own restatement of the rule against itself, leaving
        the shipped mapping free to disagree with the prose in both directions.
        """
        # remote_absent_unverified: never pushed, no base ref to prove landing.
        work = self._seed_repo_with_origin(tmp_path)
        unverified = self._state(monkeypatch, work)
        assert unverified['state'] == 'remote_absent_unverified'
        # synced: pushed, no local commits.
        self._push(work)
        synced = self._state(monkeypatch, work)
        # ahead: committed locally past origin.
        self._commit_past_origin(work)
        ahead = self._state(monkeypatch, work)
        # remote_absent_landed: merged into origin/main, feature ref deleted.
        # A distinct subdir avoids colliding with the first fixture's origin.git.
        merged_root = tmp_path / 'merged'
        merged_root.mkdir()
        merged_work = self._seed_merged_and_deleted(merged_root)
        landed = self._state(monkeypatch, merged_work)
        assert landed['state'] == 'remote_absent_landed'

        payloads = (unverified, synced, ahead, landed)
        assert {p['state']: git_workflow.push_barrier_action(p['state']) for p in payloads} == {
            'remote_absent_unverified': 'skip',
            'synced': 'skip',
            'ahead': 're-fire',
            'remote_absent_landed': 'skip',
        }

        # Every success payload PUBLISHES the action, so the dispatcher reads it
        # rather than re-deriving the mapping from the state token.
        for payload in payloads:
            assert payload['barrier_action'] == git_workflow.push_barrier_action(payload['state']), (
                f'branch-sync-state published barrier_action={payload["barrier_action"]!r} for '
                f'state={payload["state"]!r}, which disagrees with push_barrier_action. The '
                f'published field and the mapping must not drift.'
            )

        # The resurrection defect this fix closes: NEITHER ref-absent state maps
        # to a re-fire.
        assert git_workflow.push_barrier_action(unverified['state']) != 're-fire'
        assert git_workflow.push_barrier_action(landed['state']) != 're-fire'

    def test_unrecognised_state_fails_toward_skip(self):
        """An unmapped state is not evidence a push is safe, so it skips.

        Re-firing is a PUSH, so the asymmetry is deliberate: an over-broad
        re-fire resurrects a landed branch, while an over-broad skip leaves a
        genuinely-unpushed branch for the operator to notice.
        """
        assert git_workflow.push_barrier_action('some_state_added_later') == 'skip'

    def test_error_payload_publishes_no_barrier_action(self, tmp_path: Path, monkeypatch):
        """An unresolvable state is not a verdict to map, so no action is published.

        The consumer's own ``status: error`` branch (fail toward pushing) governs
        that path; publishing a ``skip`` here would route an error to the
        opposite action.
        """
        work = self._seed_repo_with_origin(tmp_path)
        monkeypatch.setattr(git_workflow, '_resolve_worktree_path_for_plan', lambda plan_id: (work, None))
        monkeypatch.setattr(git_workflow, '_read_metadata_field', lambda plan_id, field: '')

        result = git_workflow.cmd_branch_sync_state(Namespace(plan_id='sync-plan'))

        assert result['status'] == 'error'
        assert 'barrier_action' not in result
