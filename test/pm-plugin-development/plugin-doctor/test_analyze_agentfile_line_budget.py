# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""Tests for the ``agentfile-line-count-over-budget`` rule analyzer.

The analyzer discovers every always-on agentfile (``CLAUDE.md`` at any nesting
level plus ``AGENTS.md``) under the repository root derived from the supplied
marketplace (``bundles/``) root, and flags each one whose total line count
exceeds the always-on line budget (default 200, configurable per call). The
rule is analyze-surfaced only — registered in ``doctor-marketplace.py``'s
``cmd_analyze`` and intentionally absent from ``cmd_quality_gate``.

Fixture shape: the analyzer derives the repo root as ``marketplace_root.parent.parent``,
so each fixture nests ``{repo}/marketplace/bundles`` as the marketplace root and
writes agentfiles under ``{repo}`` (and its subdirectories).
"""

from pathlib import Path

from conftest import get_scripts_dir, load_script_module

_alb = load_script_module(
    'pm-plugin-development', 'plugin-doctor', '_analyze_agentfile_line_budget.py', '_analyze_agentfile_line_budget'
)

analyze_agentfile_line_budget = _alb.analyze_agentfile_line_budget
RULE_ID = _alb.RULE_ID
DEFAULT_LINE_BUDGET = _alb.DEFAULT_LINE_BUDGET


# ---------------------------------------------------------------------------
# Helpers — build a minimal fake repo with a marketplace/bundles root.
# ---------------------------------------------------------------------------


def _make_repo(tmp_path: Path) -> tuple[Path, Path]:
    """Return ``(repo_root, marketplace_root)`` for a fresh fixture tree.

    ``marketplace_root`` is ``{repo}/marketplace/bundles`` so the analyzer's
    ``repo_root_from_marketplace_root`` (``parent.parent``) resolves back to
    ``{repo}``, where the agentfiles live.
    """
    repo = tmp_path / 'repo'
    bundles = repo / 'marketplace' / 'bundles'
    bundles.mkdir(parents=True, exist_ok=True)
    return repo, bundles


def _lines(n: int) -> str:
    """Return file content with exactly ``n`` newline-delimited lines."""
    return '\n'.join(['# line'] * n) + '\n' if n else ''


def _write_agentfile(repo: Path, relpath: str, n_lines: int) -> Path:
    """Write an agentfile with ``n_lines`` lines at ``{repo}/{relpath}``."""
    path = repo / relpath
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_lines(n_lines), encoding='utf-8')
    return path


# ===========================================================================
# Positive cases — over-budget agentfile produces one finding.
# ===========================================================================


class TestOverBudgetFlagged:
    """An agentfile whose line count exceeds the budget produces one finding."""

    def test_over_budget_claude_md_flagged(self, tmp_path: Path) -> None:
        repo, bundles = _make_repo(tmp_path)
        path = _write_agentfile(repo, 'CLAUDE.md', DEFAULT_LINE_BUDGET + 50)

        findings = analyze_agentfile_line_budget(bundles)

        assert len(findings) == 1
        assert Path(findings[0]['file']).resolve() == path.resolve()

    def test_over_budget_agents_md_flagged(self, tmp_path: Path) -> None:
        repo, bundles = _make_repo(tmp_path)
        _write_agentfile(repo, 'AGENTS.md', DEFAULT_LINE_BUDGET + 1)

        findings = analyze_agentfile_line_budget(bundles)

        assert len(findings) == 1

    def test_nested_agentfile_flagged(self, tmp_path: Path) -> None:
        repo, bundles = _make_repo(tmp_path)
        path = _write_agentfile(repo, 'sub/dir/CLAUDE.md', DEFAULT_LINE_BUDGET + 5)

        findings = analyze_agentfile_line_budget(bundles)

        assert len(findings) == 1
        assert Path(findings[0]['file']).resolve() == path.resolve()

    def test_multiple_over_budget_agentfiles(self, tmp_path: Path) -> None:
        repo, bundles = _make_repo(tmp_path)
        _write_agentfile(repo, 'CLAUDE.md', DEFAULT_LINE_BUDGET + 10)
        _write_agentfile(repo, 'pkg/AGENTS.md', DEFAULT_LINE_BUDGET + 10)

        findings = analyze_agentfile_line_budget(bundles)

        assert len(findings) == 2

    def test_finding_shape(self, tmp_path: Path) -> None:
        repo, bundles = _make_repo(tmp_path)
        count = DEFAULT_LINE_BUDGET + 7
        _write_agentfile(repo, 'CLAUDE.md', count)

        findings = analyze_agentfile_line_budget(bundles)

        finding = findings[0]
        assert finding['rule_id'] == RULE_ID
        assert finding['type'] == RULE_ID
        assert finding['rule'] == 'analyze_agentfile_line_budget'
        assert finding['line'] == 1
        assert finding['severity'] == 'warning'
        assert finding['fixable'] is False
        assert str(count) in finding['snippet']
        assert str(DEFAULT_LINE_BUDGET) in finding['snippet']


# ===========================================================================
# Negative cases — within-budget agentfile produces no finding.
# ===========================================================================


class TestWithinBudgetNotFlagged:
    """An agentfile at or under the budget produces no findings."""

    def test_small_agentfile_not_flagged(self, tmp_path: Path) -> None:
        repo, bundles = _make_repo(tmp_path)
        _write_agentfile(repo, 'CLAUDE.md', 10)

        findings = analyze_agentfile_line_budget(bundles)

        assert findings == []

    def test_exactly_at_budget_not_flagged(self, tmp_path: Path) -> None:
        """The budget is inclusive — exactly ``budget`` lines is compliant."""
        repo, bundles = _make_repo(tmp_path)
        _write_agentfile(repo, 'CLAUDE.md', DEFAULT_LINE_BUDGET)

        findings = analyze_agentfile_line_budget(bundles)

        assert findings == []

    def test_one_over_budget_flagged(self, tmp_path: Path) -> None:
        """One line over the budget is the boundary that flags."""
        repo, bundles = _make_repo(tmp_path)
        _write_agentfile(repo, 'CLAUDE.md', DEFAULT_LINE_BUDGET + 1)

        findings = analyze_agentfile_line_budget(bundles)

        assert len(findings) == 1

    def test_no_agentfiles_no_findings(self, tmp_path: Path) -> None:
        _repo, bundles = _make_repo(tmp_path)

        findings = analyze_agentfile_line_budget(bundles)

        assert findings == []


# ===========================================================================
# Excluded directories — generated / vendored / scratch trees are pruned.
# ===========================================================================


class TestExcludedDirectories:
    """Agentfiles under pruned directories are never discovered."""

    def test_target_dir_pruned(self, tmp_path: Path) -> None:
        repo, bundles = _make_repo(tmp_path)
        _write_agentfile(repo, 'target/CLAUDE.md', DEFAULT_LINE_BUDGET + 100)

        findings = analyze_agentfile_line_budget(bundles)

        assert findings == []

    def test_plan_and_git_and_node_modules_pruned(self, tmp_path: Path) -> None:
        repo, bundles = _make_repo(tmp_path)
        _write_agentfile(repo, '.plan/CLAUDE.md', DEFAULT_LINE_BUDGET + 100)
        _write_agentfile(repo, '.git/CLAUDE.md', DEFAULT_LINE_BUDGET + 100)
        _write_agentfile(repo, 'node_modules/pkg/AGENTS.md', DEFAULT_LINE_BUDGET + 100)

        findings = analyze_agentfile_line_budget(bundles)

        assert findings == []


# ===========================================================================
# Configurable budget — a caller may tune the threshold.
# ===========================================================================


class TestConfigurableBudget:
    """The budget is a single configurable default the caller may override."""

    def test_custom_budget_flags_above(self, tmp_path: Path) -> None:
        repo, bundles = _make_repo(tmp_path)
        _write_agentfile(repo, 'CLAUDE.md', 6)

        findings = analyze_agentfile_line_budget(bundles, budget=5)

        assert len(findings) == 1
        assert '(budget 5)' in findings[0]['snippet']

    def test_custom_budget_compliant_below(self, tmp_path: Path) -> None:
        repo, bundles = _make_repo(tmp_path)
        _write_agentfile(repo, 'CLAUDE.md', 5)

        findings = analyze_agentfile_line_budget(bundles, budget=5)

        assert findings == []


# ===========================================================================
# Registration — analyze-surfaced only (present in cmd_analyze, absent from
# cmd_quality_gate).
# ===========================================================================


def _function_body(source: str, func_name: str) -> str:
    """Return the source slice of a top-level ``def func_name(`` block."""
    marker = f'\ndef {func_name}('
    start = source.index(marker)
    rest = source[start + len(marker):]
    next_def = rest.find('\ndef ')
    return rest if next_def == -1 else rest[:next_def]


class TestAnalyzeOnlyRegistration:
    """The rule is wired into cmd_analyze but NOT cmd_quality_gate."""

    def test_call_present_in_cmd_analyze_absent_in_quality_gate(self) -> None:
        driver = get_scripts_dir('pm-plugin-development', 'plugin-doctor') / 'doctor-marketplace.py'
        source = driver.read_text(encoding='utf-8')

        analyze_body = _function_body(source, 'cmd_analyze')
        quality_gate_body = _function_body(source, 'cmd_quality_gate')

        assert 'analyze_agentfile_line_budget(' in analyze_body
        assert 'analyze_agentfile_line_budget(' not in quality_gate_body
