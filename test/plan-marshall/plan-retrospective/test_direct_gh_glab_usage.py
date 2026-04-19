"""Tests for ``direct_gh_glab_usage.py``.

Covers the five detection scenarios required by the aspect:

(a) Fixture log files containing ``gh``/``glab`` invocations (positive
    detection) — surface ``log_leak``.
(b) Fixture diff with added ``gh``/``glab`` lines (positive detection)
    — surface ``diff_leak``.
(c) Fixture wrapper scripts with an abstraction-leak pattern — a
    ``subprocess`` args list containing both the CLI name AND a local
    git mutation token (``checkout``, ``branch -d``, ``--delete-branch``,
    ...) — surface ``wrapper_tangle``.
(d) Fixture where ``gh`` appears only in a comment — negative, must NOT
    trip the diff or wrapper scanners.
(e) Fixture with a pure remote-API ``gh api repos/...`` call and no
    local-git mutation tokens — negative for the wrapper-tangle
    heuristic (class-a remote only).
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from _fixtures import setup_broken_plan, setup_live_plan  # noqa: E402

from conftest import MARKETPLACE_ROOT, run_script  # noqa: E402

SCRIPT_PATH = (
    MARKETPLACE_ROOT
    / 'plan-marshall'
    / 'skills'
    / 'plan-retrospective'
    / 'scripts'
    / 'direct_gh_glab_usage.py'
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _init_git_repo(repo_dir: Path) -> None:
    """Initialise a minimal git repo with a ``main`` branch and one commit.

    The diff scanner (surface B) calls ``git diff {base}...HEAD`` against
    the given ``--project-root``. We need a real repo with a ``main``
    branch so the three-dot syntax resolves cleanly. The initial commit
    is empty so subsequent per-test commits become the HEAD diff.
    """
    env = {
        'GIT_AUTHOR_NAME': 'Test',
        'GIT_AUTHOR_EMAIL': 'test@example.com',
        'GIT_COMMITTER_NAME': 'Test',
        'GIT_COMMITTER_EMAIL': 'test@example.com',
    }
    subprocess.run(
        ['git', 'init', '-q', '-b', 'main', str(repo_dir)],
        check=True, capture_output=True, env={**env},
    )
    subprocess.run(
        ['git', '-C', str(repo_dir), 'commit', '--allow-empty', '-q', '-m', 'init'],
        check=True, capture_output=True, env={**env},
    )


def _commit_file(repo_dir: Path, rel_path: str, content: str) -> None:
    """Create ``rel_path`` under ``repo_dir`` with ``content`` and commit it.

    The commit lands on HEAD so ``main...HEAD`` exposes the file as an
    all-added diff.
    """
    env = {
        'GIT_AUTHOR_NAME': 'Test',
        'GIT_AUTHOR_EMAIL': 'test@example.com',
        'GIT_COMMITTER_NAME': 'Test',
        'GIT_COMMITTER_EMAIL': 'test@example.com',
    }
    file_path = repo_dir / rel_path
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content, encoding='utf-8')
    subprocess.run(
        ['git', '-C', str(repo_dir), 'checkout', '-q', '-b', 'feature'],
        check=False, capture_output=True, env={**env},
    )
    subprocess.run(
        ['git', '-C', str(repo_dir), 'add', rel_path],
        check=True, capture_output=True, env={**env},
    )
    subprocess.run(
        ['git', '-C', str(repo_dir), 'commit', '-q', '-m', f'add {rel_path}'],
        check=True, capture_output=True, env={**env},
    )


def _write_wrapper(project_root: Path, rel_path: str, content: str) -> None:
    """Write a wrapper-scope Python file whose path matches one of the three
    directories ``direct_gh_glab_usage.py`` scans (surface C).
    """
    target = project_root / rel_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding='utf-8')


# ---------------------------------------------------------------------------
# Surface A: log leaks
# ---------------------------------------------------------------------------


class TestLogLeaks:
    """Surface A — ``logs/work.log`` and ``logs/script-execution.log``."""

    def test_positive_gh_invocation_in_work_log(self, tmp_path, monkeypatch):
        """Case (a): a work.log line containing ``gh pr view`` is flagged."""
        plan_id, plan_dir = setup_live_plan(tmp_path, monkeypatch, plan_id='retro-ghglab-a')
        # Append a line that unambiguously invokes the gh CLI. The fixture
        # line already uses production shape `[ts] [LEVEL] [hash] [CAT] (caller) msg`.
        work_log = plan_dir / 'logs' / 'work.log'
        work_log.write_text(
            work_log.read_text(encoding='utf-8')
            + '[2026-04-17T10:03:00Z] [INFO] [999999] [STATUS] '
              '(plan-marshall:phase-6-finalize) ran gh pr view 42\n',
            encoding='utf-8',
        )

        result = run_script(
            SCRIPT_PATH, 'run', '--plan-id', plan_id, '--mode', 'live',
            '--project-root', str(tmp_path),
        )
        assert result.success, result.stderr
        data = result.toon()

        assert data['aspect'] == 'direct_gh_glab_usage'
        log_findings = [f for f in data['findings'] if f['surface'] == 'log_leak']
        assert len(log_findings) >= 1, (
            'Expected at least one log_leak finding for "gh pr view" in work.log'
        )
        assert any('work.log' in f['file'] for f in log_findings)
        assert any('gh pr view' in f['snippet'] for f in log_findings)

    def test_positive_glab_invocation_in_script_execution_log(self, tmp_path, monkeypatch):
        """Case (a, glab variant): glab lines in script-execution.log are flagged."""
        plan_id, plan_dir = setup_live_plan(tmp_path, monkeypatch, plan_id='retro-ghglab-glab')
        script_log = plan_dir / 'logs' / 'script-execution.log'
        script_log.write_text(
            script_log.read_text(encoding='utf-8')
            + '[2026-04-17T10:04:00Z] [INFO] [aaaaa1] '
              'direct call: glab mr view 17 (0.20s)\n',
            encoding='utf-8',
        )

        result = run_script(
            SCRIPT_PATH, 'run', '--plan-id', plan_id, '--mode', 'live',
            '--project-root', str(tmp_path),
        )
        assert result.success, result.stderr
        data = result.toon()
        log_findings = [f for f in data['findings'] if f['surface'] == 'log_leak']
        assert any('glab mr view' in f['snippet'] for f in log_findings)
        assert any('script-execution.log' in f['file'] for f in log_findings)

    def test_github_com_substring_not_flagged(self, tmp_path, monkeypatch):
        """Regression: ``github.com`` and ``github_pr`` identifiers must not
        trip the log scanner — the regex uses flanking rules to reject them.
        """
        plan_id, plan_dir = setup_live_plan(tmp_path, monkeypatch, plan_id='retro-ghglab-noop')
        work_log = plan_dir / 'logs' / 'work.log'
        # Overwrite the fixture content to a clean set of lines that contain
        # 'github' and 'github_pr' substrings but no real gh/glab invocation.
        work_log.write_text(
            '[2026-04-17T11:00:00Z] [INFO] [777777] [STATUS] '
            '(plan-marshall:phase-5-execute) fetched from github.com/foo/bar\n'
            '[2026-04-17T11:01:00Z] [INFO] [888888] [STATUS] '
            '(plan-marshall:phase-5-execute) loaded module github_pr\n',
            encoding='utf-8',
        )
        # Also clear script-execution.log so the other happy-path fixture lines
        # do not add unrelated findings.
        (plan_dir / 'logs' / 'script-execution.log').write_text('', encoding='utf-8')

        result = run_script(
            SCRIPT_PATH, 'run', '--plan-id', plan_id, '--mode', 'live',
            '--project-root', str(tmp_path),
        )
        assert result.success, result.stderr
        data = result.toon()
        log_findings = [f for f in data['findings'] if f['surface'] == 'log_leak']
        assert log_findings == [], (
            f'Expected no log_leak findings for github.com/github_pr substrings, '
            f'got: {log_findings}'
        )


# ---------------------------------------------------------------------------
# Surface B: diff leaks
# ---------------------------------------------------------------------------


class TestDiffLeaks:
    """Surface B — ``git diff {base}...HEAD`` added-line scan."""

    def test_positive_added_gh_call_in_python(self, tmp_path, monkeypatch):
        """Case (b): a Python file added on a feature branch that invokes
        ``gh pr view`` surfaces a ``diff_leak`` finding.
        """
        plan_id, _ = setup_live_plan(tmp_path, monkeypatch, plan_id='retro-ghglab-diff')
        repo_dir = tmp_path / 'repo'
        _init_git_repo(repo_dir)
        _commit_file(
            repo_dir,
            'src/leaky.py',
            'import subprocess\n'
            'def pull():\n'
            "    subprocess.run(['gh', 'pr', 'view', '42'])\n",
        )

        result = run_script(
            SCRIPT_PATH, 'run', '--plan-id', plan_id, '--mode', 'live',
            '--project-root', str(repo_dir), '--base', 'main',
        )
        assert result.success, result.stderr
        data = result.toon()
        diff_findings = [f for f in data['findings'] if f['surface'] == 'diff_leak']
        assert len(diff_findings) >= 1, (
            f"Expected at least one diff_leak finding for added gh call; got "
            f"{diff_findings}. Full findings: {data['findings']}"
        )
        assert any('leaky.py' in f['file'] for f in diff_findings)
        assert any("gh" in f['snippet'] for f in diff_findings)

    def test_gh_in_comment_not_flagged_as_diff_leak(self, tmp_path, monkeypatch):
        """Case (d): a Python comment mentioning ``gh`` must NOT trip the
        diff scanner — ``is_comment_or_blank`` filters comment-only lines.
        """
        plan_id, _ = setup_live_plan(tmp_path, monkeypatch, plan_id='retro-ghglab-comment')
        repo_dir = tmp_path / 'repo'
        _init_git_repo(repo_dir)
        _commit_file(
            repo_dir,
            'src/clean.py',
            'import subprocess\n'
            '# TODO: stop using gh directly here\n'
            'def pull():\n'
            '    pass\n',
        )

        result = run_script(
            SCRIPT_PATH, 'run', '--plan-id', plan_id, '--mode', 'live',
            '--project-root', str(repo_dir), '--base', 'main',
        )
        assert result.success, result.stderr
        data = result.toon()
        diff_findings = [f for f in data['findings'] if f['surface'] == 'diff_leak']
        assert diff_findings == [], (
            f'Expected no diff_leak finding for comment-only gh mention, got: '
            f'{diff_findings}'
        )


# ---------------------------------------------------------------------------
# Surface C: wrapper-tangle
# ---------------------------------------------------------------------------


class TestWrapperTangle:
    """Surface C — subprocess args lists that mix a CLI invocation with a
    local-git mutation token (``checkout``, ``branch -d`` / ``-D``,
    ``--delete-branch``, ``--remove-source-branch``).
    """

    def test_positive_gh_plus_delete_branch_flag(self, tmp_path, monkeypatch):
        """Case (c): ``subprocess.run(['gh', 'pr', 'merge', '--delete-branch'])``
        is a wrapper tangle — CLI name and mutation token appear in the same
        multi-line args window, so the wrapper scanner flags it.
        """
        plan_id, _ = setup_broken_plan(
            tmp_path, monkeypatch, plan_id='retro-ghglab-tangle'
        )
        # Build a project-root layout that matches one of the three dirs the
        # scanner walks. We choose the github wrapper directory.
        wrapper_rel = (
            'marketplace/bundles/plan-marshall/skills/'
            'workflow-integration-github/scripts/leaky_wrapper.py'
        )
        _write_wrapper(
            tmp_path,
            wrapper_rel,
            '"""Leaky wrapper fixture."""\n'
            'import subprocess\n'
            'def merge(pr_number: str) -> None:\n'
            '    subprocess.run([\n'
            "        'gh', 'pr', 'merge', pr_number, '--delete-branch',\n"
            '    ], check=True)\n',
        )

        result = run_script(
            SCRIPT_PATH, 'run', '--plan-id', plan_id, '--mode', 'live',
            '--project-root', str(tmp_path),
        )
        assert result.success, result.stderr
        data = result.toon()
        tangles = [f for f in data['findings'] if f['surface'] == 'wrapper_tangle']
        assert len(tangles) >= 1, (
            f'Expected wrapper_tangle finding for gh+--delete-branch call; '
            f'got {tangles}. Full findings: {data["findings"]}'
        )
        assert any('leaky_wrapper.py' in f['file'] for f in tangles)

    def test_positive_glab_plus_checkout(self, tmp_path, monkeypatch):
        """Case (c, glab variant): ``checkout`` is a mutation token too."""
        plan_id, _ = setup_broken_plan(
            tmp_path, monkeypatch, plan_id='retro-ghglab-glab-tangle'
        )
        wrapper_rel = (
            'marketplace/bundles/plan-marshall/skills/'
            'workflow-integration-gitlab/scripts/leaky_glab.py'
        )
        _write_wrapper(
            tmp_path,
            wrapper_rel,
            '"""Leaky glab wrapper fixture."""\n'
            'import subprocess\n'
            'def checkout_branch(ref: str) -> None:\n'
            "    subprocess.run(['glab', 'mr', 'checkout', ref], check=True)\n",
        )

        result = run_script(
            SCRIPT_PATH, 'run', '--plan-id', plan_id, '--mode', 'live',
            '--project-root', str(tmp_path),
        )
        assert result.success, result.stderr
        data = result.toon()
        tangles = [f for f in data['findings'] if f['surface'] == 'wrapper_tangle']
        assert any('leaky_glab.py' in f['file'] for f in tangles), (
            f'Expected wrapper_tangle finding for glab+checkout call; '
            f'got {tangles}'
        )

    def test_negative_pure_remote_gh_api_not_flagged(self, tmp_path, monkeypatch):
        """Case (e): ``gh api repos/...`` with no local-git mutation token
        is a class-A remote-only call — the wrapper-tangle heuristic MUST NOT
        trip. Documents the intentional scope of the abstraction-leak check.
        """
        plan_id, _ = setup_broken_plan(
            tmp_path, monkeypatch, plan_id='retro-ghglab-remote-only'
        )
        wrapper_rel = (
            'marketplace/bundles/plan-marshall/skills/'
            'tools-integration-ci/scripts/remote_only.py'
        )
        _write_wrapper(
            tmp_path,
            wrapper_rel,
            '"""Pure remote-API wrapper — no local-git side effects."""\n'
            'import subprocess\n'
            'def list_issues(repo: str) -> None:\n'
            "    subprocess.run(['gh', 'api', f'repos/{repo}/issues'], check=True)\n",
        )

        result = run_script(
            SCRIPT_PATH, 'run', '--plan-id', plan_id, '--mode', 'live',
            '--project-root', str(tmp_path),
        )
        assert result.success, result.stderr
        data = result.toon()
        tangles = [f for f in data['findings'] if f['surface'] == 'wrapper_tangle']
        assert tangles == [], (
            f'Pure remote-only gh api call must NOT be flagged as a wrapper '
            f'tangle; the heuristic is scoped to CLI+local-git-mutation '
            f'combinations. Got unexpected tangles: {tangles}'
        )


# ---------------------------------------------------------------------------
# Top-level aggregate contract
# ---------------------------------------------------------------------------


class TestAggregateContract:
    """The script's output shape must remain stable even when findings exist."""

    def test_counts_by_surface_reflect_findings(self, tmp_path, monkeypatch):
        """All three counters must appear and equal the findings actually emitted."""
        plan_id, plan_dir = setup_live_plan(
            tmp_path, monkeypatch, plan_id='retro-ghglab-aggregate'
        )
        # One log leak.
        work_log = plan_dir / 'logs' / 'work.log'
        work_log.write_text(
            '[2026-04-17T12:00:00Z] [INFO] [abcabc] [STATUS] '
            '(plan-marshall:phase-6-finalize) ran gh pr list\n',
            encoding='utf-8',
        )
        (plan_dir / 'logs' / 'script-execution.log').write_text('', encoding='utf-8')

        # One wrapper tangle.
        wrapper_rel = (
            'marketplace/bundles/plan-marshall/skills/'
            'workflow-integration-github/scripts/aggregate_leak.py'
        )
        _write_wrapper(
            tmp_path,
            wrapper_rel,
            '"""Aggregate fixture."""\n'
            'import subprocess\n'
            'def merge() -> None:\n'
            "    subprocess.run(['gh', 'pr', 'merge', '--delete-branch'], check=True)\n",
        )

        result = run_script(
            SCRIPT_PATH, 'run', '--plan-id', plan_id, '--mode', 'live',
            '--project-root', str(tmp_path),
        )
        assert result.success, result.stderr
        data = result.toon()
        counts = data['counts']['by_surface']
        findings = data['findings']

        log_n = sum(1 for f in findings if f['surface'] == 'log_leak')
        tangle_n = sum(1 for f in findings if f['surface'] == 'wrapper_tangle')
        diff_n = sum(1 for f in findings if f['surface'] == 'diff_leak')

        assert int(counts['log_leak']) == log_n
        assert int(counts['wrapper_tangle']) == tangle_n
        assert int(counts['diff_leak']) == diff_n
        assert int(data['counts']['total']) == log_n + tangle_n + diff_n
        assert log_n >= 1
        assert tangle_n >= 1
