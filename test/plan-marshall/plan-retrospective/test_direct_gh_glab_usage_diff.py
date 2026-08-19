# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the generic ``direct-gh-glab-usage.py`` aspect (Surfaces A+B) and
the retrospective-aspect extension point that homes the former Surface C.

Covers the domain-invariant detection scenarios for the generic aspect:

(a) Fixture log files containing ``gh``/``glab`` invocations (positive
    detection) — surface ``log_leak``.
(b) Fixture diff with added ``gh``/``glab`` lines (positive detection)
    — surface ``diff_leak``.
(d) Fixture where ``gh`` appears only in a comment — negative, must NOT
    trip the diff scanner.

Plus the Surface C split contract, scoped to this file per the deliverable:

* Surfaces A+B remain in the generic, domain-invariant ``direct-gh-glab-usage``
  aspect; ``wrapper_tangle`` is no longer emitted there.
* Surface C moved to the ``plan-marshall-plugin-dev`` domain aspect
  ``pm-plugin-development:plan-marshall-plugin:wrapper-tangle-scan``,
  contributed via the ``provides_retrospective_aspects()`` extension point.
* ``extension_discovery.py`` discovers the hook and surfaces it through the
  ``list-retrospective-aspects`` CLI (the deterministic backing for
  plan-retrospective Step 3's domain-aspect merge).
* ``pm-plugin-development``'s ``extension.py`` contributes the aspect gated by
  the ``plan-marshall-plugin-dev`` domain only; ``ExtensionBase`` returns ``[]``
  by default.
* plan-retrospective Step 3 merges domain aspects per domain — modelled here as
  the deterministic ``filter list-retrospective-aspects by plan domain``
  predicate the workflow step relies on.

The wrapper-tangle DETECTION behaviour itself lives in
``test/pm-plugin-development/plan-marshall-plugin/test_wrapper_tangle_scan.py``.
"""


from __future__ import annotations

from _direct_gh_glab_usage_fixtures import SCRIPT_PATH, _commit_file, _init_git_repo
from _plan_retrospective_fixtures import setup_live_plan  # noqa: E402

from conftest import run_script  # noqa: E402

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
            work_log.read_text(encoding='utf-8') + '[2026-04-17T10:03:00Z] [INFO] [999999] [STATUS] '
            '(plan-marshall:phase-6-finalize) ran gh pr view 42\n',
            encoding='utf-8',
        )

        result = run_script(
            SCRIPT_PATH,
            'run',
            '--plan-id',
            plan_id,
            '--mode',
            'live',
            '--project-root',
            str(tmp_path),
        )
        assert result.success, result.stderr
        data = result.toon()

        assert data['aspect'] == 'direct-gh-glab-usage'
        log_findings = [f for f in data['findings'] if f['surface'] == 'log_leak']
        assert len(log_findings) >= 1, 'Expected at least one log_leak finding for "gh pr view" in work.log'
        assert any('work.log' in f['file'] for f in log_findings)
        assert any('gh pr view' in f['snippet'] for f in log_findings)

    def test_positive_glab_invocation_in_script_execution_log(self, tmp_path, monkeypatch):
        """Case (a, glab variant): glab lines in script-execution.log are flagged."""
        plan_id, plan_dir = setup_live_plan(tmp_path, monkeypatch, plan_id='retro-ghglab-glab')
        script_log = plan_dir / 'logs' / 'script-execution.log'
        script_log.write_text(
            script_log.read_text(encoding='utf-8') + '[2026-04-17T10:04:00Z] [INFO] [aaaaa1] '
            'direct call: glab mr view 17 (0.20s)\n',
            encoding='utf-8',
        )

        result = run_script(
            SCRIPT_PATH,
            'run',
            '--plan-id',
            plan_id,
            '--mode',
            'live',
            '--project-root',
            str(tmp_path),
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
            SCRIPT_PATH,
            'run',
            '--plan-id',
            plan_id,
            '--mode',
            'live',
            '--project-root',
            str(tmp_path),
        )
        assert result.success, result.stderr
        data = result.toon()
        log_findings = [f for f in data['findings'] if f['surface'] == 'log_leak']
        assert log_findings == [], (
            f'Expected no log_leak findings for github.com/github_pr substrings, got: {log_findings}'
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
            "import subprocess\ndef pull():\n    subprocess.run(['gh', 'pr', 'view', '42'])\n",
        )

        result = run_script(
            SCRIPT_PATH,
            'run',
            '--plan-id',
            plan_id,
            '--mode',
            'live',
            '--project-root',
            str(repo_dir),
            '--base',
            'main',
        )
        assert result.success, result.stderr
        data = result.toon()
        diff_findings = [f for f in data['findings'] if f['surface'] == 'diff_leak']
        assert len(diff_findings) >= 1, (
            f'Expected at least one diff_leak finding for added gh call; got '
            f'{diff_findings}. Full findings: {data["findings"]}'
        )
        assert any('leaky.py' in f['file'] for f in diff_findings)
        assert any('gh' in f['snippet'] for f in diff_findings)

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
            'import subprocess\n# TODO: stop using gh directly here\ndef pull():\n    pass\n',
        )

        result = run_script(
            SCRIPT_PATH,
            'run',
            '--plan-id',
            plan_id,
            '--mode',
            'live',
            '--project-root',
            str(repo_dir),
            '--base',
            'main',
        )
        assert result.success, result.stderr
        data = result.toon()
        diff_findings = [f for f in data['findings'] if f['surface'] == 'diff_leak']
        assert diff_findings == [], f'Expected no diff_leak finding for comment-only gh mention, got: {diff_findings}'
