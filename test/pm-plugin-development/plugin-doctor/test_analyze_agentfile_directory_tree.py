# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""Tests for the ``agentfile-directory-tree-present`` rule analyzer.

The analyzer discovers every always-on agentfile (``CLAUDE.md`` at any nesting
level plus ``AGENTS.md``) under the repository root derived from the supplied
marketplace (``bundles/``) root, and flags each fenced code block that contains
a directory-tree box-drawing glyph (``├──``, ``│``, ``└──``). The rule is
analyze-surfaced only — registered in ``doctor-marketplace.py``'s
``cmd_analyze`` and intentionally absent from ``cmd_quality_gate``.

Fixture shape: the analyzer derives the repo root as ``marketplace_root.parent.parent``,
so each fixture nests ``{repo}/marketplace/bundles`` as the marketplace root and
writes agentfiles under ``{repo}``.
"""

from pathlib import Path

from conftest import get_scripts_dir, load_script_module
from _fixtures import _function_body

_adt = load_script_module(
    'pm-plugin-development',
    'plugin-doctor',
    '_analyze_agentfile_directory_tree.py',
    '_analyze_agentfile_directory_tree',
)

analyze_agentfile_directory_tree = _adt.analyze_agentfile_directory_tree
RULE_ID = _adt.RULE_ID


# ---------------------------------------------------------------------------
# Helpers — build a minimal fake repo with a marketplace/bundles root.
# ---------------------------------------------------------------------------


def _make_repo(tmp_path: Path) -> tuple[Path, Path]:
    """Return ``(repo_root, marketplace_root)`` for a fresh fixture tree."""
    repo = tmp_path / 'repo'
    bundles = repo / 'marketplace' / 'bundles'
    bundles.mkdir(parents=True, exist_ok=True)
    return repo, bundles


def _write_agentfile(repo: Path, relpath: str, content: str) -> Path:
    """Write an agentfile with ``content`` at ``{repo}/{relpath}``."""
    path = repo / relpath
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')
    return path


# A fenced block drawing a directory tree with all three glyphs.
_TREE_FENCE = (
    '# Project\n'
    '\n'
    '```\n'
    'repo/\n'
    '├── src/\n'
    '│   └── main.py\n'
    '└── README.md\n'
    '```\n'
)


# ===========================================================================
# Positive cases — a fenced directory tree produces one finding per block.
# ===========================================================================


class TestFencedTreeFlagged:
    """A fenced block containing tree glyphs produces one finding."""

    def test_fenced_tree_in_claude_md_flagged(self, tmp_path: Path) -> None:
        repo, bundles = _make_repo(tmp_path)
        path = _write_agentfile(repo, 'CLAUDE.md', _TREE_FENCE)

        findings = analyze_agentfile_directory_tree(bundles)

        assert len(findings) == 1
        assert Path(findings[0]['file']).resolve() == path.resolve()

    def test_finding_anchored_at_first_glyph_line(self, tmp_path: Path) -> None:
        repo, bundles = _make_repo(tmp_path)
        _write_agentfile(repo, 'CLAUDE.md', _TREE_FENCE)

        findings = analyze_agentfile_directory_tree(bundles)

        # Lines (1-based): 1 '# Project', 2 '', 3 '```', 4 'repo/',
        # 5 '├── src/' — the first glyph line.
        assert findings[0]['line'] == 5
        assert '├──' in findings[0]['snippet']

    def test_tilde_fence_tree_flagged(self, tmp_path: Path) -> None:
        repo, bundles = _make_repo(tmp_path)
        content = '~~~\nrepo/\n└── file.py\n~~~\n'
        _write_agentfile(repo, 'AGENTS.md', content)

        findings = analyze_agentfile_directory_tree(bundles)

        assert len(findings) == 1

    def test_multiple_fenced_trees_each_flagged(self, tmp_path: Path) -> None:
        repo, bundles = _make_repo(tmp_path)
        content = _TREE_FENCE + '\nMiddle prose\n\n' + _TREE_FENCE
        _write_agentfile(repo, 'CLAUDE.md', content)

        findings = analyze_agentfile_directory_tree(bundles)

        assert len(findings) == 2

    def test_pipe_glyph_only_in_fence_flagged(self, tmp_path: Path) -> None:
        repo, bundles = _make_repo(tmp_path)
        content = '```\nsrc/\n│   app.py\n```\n'
        _write_agentfile(repo, 'CLAUDE.md', content)

        findings = analyze_agentfile_directory_tree(bundles)

        assert len(findings) == 1

    def test_finding_shape(self, tmp_path: Path) -> None:
        repo, bundles = _make_repo(tmp_path)
        _write_agentfile(repo, 'CLAUDE.md', _TREE_FENCE)

        finding = analyze_agentfile_directory_tree(bundles)[0]

        assert finding['rule_id'] == RULE_ID
        assert finding['type'] == RULE_ID
        assert finding['rule'] == 'analyze_agentfile_directory_tree'
        assert finding['severity'] == 'warning'
        assert finding['fixable'] is False


# ===========================================================================
# Negative cases — no fenced tree produces no finding.
# ===========================================================================


class TestNoTreeNotFlagged:
    """An agentfile without a fenced tree produces no findings."""

    def test_plain_fenced_block_not_flagged(self, tmp_path: Path) -> None:
        repo, bundles = _make_repo(tmp_path)
        content = '# Title\n\n```bash\npython3 run.py\n```\n'
        _write_agentfile(repo, 'CLAUDE.md', content)

        findings = analyze_agentfile_directory_tree(bundles)

        assert findings == []

    def test_glyph_in_prose_outside_fence_not_flagged(self, tmp_path: Path) -> None:
        """A tree glyph in ordinary prose (no fence) is not scanned."""
        repo, bundles = _make_repo(tmp_path)
        content = '# Title\n\nThe layout is src/ ├── main.py in prose.\n'
        _write_agentfile(repo, 'CLAUDE.md', content)

        findings = analyze_agentfile_directory_tree(bundles)

        assert findings == []

    def test_ascii_pipe_table_in_fence_not_flagged(self, tmp_path: Path) -> None:
        """An ASCII-pipe table inside a fence does not match the box-drawing glyph."""
        repo, bundles = _make_repo(tmp_path)
        content = '```\n| col-a | col-b |\n| ----- | ----- |\n| x | y |\n```\n'
        _write_agentfile(repo, 'CLAUDE.md', content)

        findings = analyze_agentfile_directory_tree(bundles)

        assert findings == []

    def test_no_agentfiles_no_findings(self, tmp_path: Path) -> None:
        _repo, bundles = _make_repo(tmp_path)

        findings = analyze_agentfile_directory_tree(bundles)

        assert findings == []


# ===========================================================================
# Excluded directories — generated / vendored / scratch trees are pruned.
# ===========================================================================


class TestExcludedDirectories:
    """Agentfiles under pruned directories are never discovered."""

    def test_excluded_dirs_pruned(self, tmp_path: Path) -> None:
        repo, bundles = _make_repo(tmp_path)
        _write_agentfile(repo, 'target/CLAUDE.md', _TREE_FENCE)
        _write_agentfile(repo, '.plan/AGENTS.md', _TREE_FENCE)
        _write_agentfile(repo, 'node_modules/pkg/CLAUDE.md', _TREE_FENCE)

        findings = analyze_agentfile_directory_tree(bundles)

        assert findings == []


# ===========================================================================
# Registration — analyze-surfaced only (present in cmd_analyze, absent from
# cmd_quality_gate).
# ===========================================================================


class TestAnalyzeOnlyRegistration:
    """The rule is wired into cmd_analyze but NOT cmd_quality_gate."""

    def test_call_present_in_cmd_analyze_absent_in_quality_gate(self) -> None:
        driver = get_scripts_dir('pm-plugin-development', 'plugin-doctor') / 'doctor-marketplace.py'
        source = driver.read_text(encoding='utf-8')

        analyze_body = _function_body(source, 'cmd_analyze')
        quality_gate_body = _function_body(source, 'cmd_quality_gate')

        assert 'analyze_agentfile_directory_tree(' in analyze_body
        assert 'analyze_agentfile_directory_tree(' not in quality_gate_body
