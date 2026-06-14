# ruff: noqa: I001, E402
"""Unit tests for _analyze_markdown_link_bare_filename.py.

Covers the MARKDOWN_LINK_BARE_FILENAME analyzer, which flags two high-precision
cross-reference defects in skill / agent / command markdown across all bundles:

Pattern 1 — broken parent-relative link (filesystem-verified):

- A ``[text](sibling.md)`` link whose ``.md`` target has no path separator and
  resolves in the PARENT directory but NOT the referencing file's own directory
  is flagged (the ``../`` parent-escape prefix is missing).
- A correct same-dir ``[text](sibling.md)`` link (target exists alongside the
  file) is NOT flagged.
- A correct ``[text](../sibling.md)`` escape link is NOT flagged.
- A ``[text](dir/file.md)`` link with a directory separator is NOT flagged.
- A target that exists in NEITHER directory is NOT flagged (out of scope).

Pattern 2 — odd-one-out plain-text cross-reference in a link list:

- A bare ``name.md`` plain-text token on a list-item line is flagged WHEN at
  least one other item in the same contiguous list block is a ``.md`` link.
- A list of pure prose items (no ``.md`` link among them) with a bare ``.md``
  token is NOT flagged.

Dropped blanket prose detection (now NEGATIVE assertions):

- A bare ``.md`` token in plain prose (not a list, not a broken link) is NOT
  flagged. This was the source of the false-positive flood and is no longer a
  defect this rule reports.

Context exemptions (never flagged):

- ``.md`` inside a fenced code block (any info-string)
- ``.md`` inside an inline-code span
- ``.md`` inside an HTML comment

Finding-shape coverage:

- All required fields present and correctly typed
- 1-based line numbers
- Absolute file paths

Clean baseline: a clean tree yields an empty finding list.
"""
from pathlib import Path

from conftest import load_script_module


def _load_module(name: str, filename: str):
    return load_script_module('pm-plugin-development', 'plugin-doctor', filename, name)


_aml = _load_module(
    '_analyze_markdown_link_bare_filename',
    '_analyze_markdown_link_bare_filename.py',
)
analyze_markdown_link_bare_filename = _aml.analyze_markdown_link_bare_filename
RULE_ID = _aml.RULE_ID
RULE_NAME = _aml.RULE_NAME
FINDING_TYPE = _aml.FINDING_TYPE


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _standards_dir(tmp_path: Path) -> Path:
    """Return the fake ``standards/`` subdirectory path (creating its parents)."""
    standards_dir = tmp_path / 'plan-marshall' / 'skills' / 'test-skill' / 'standards'
    standards_dir.mkdir(parents=True, exist_ok=True)
    return standards_dir


def _make_standards_md(tmp_path: Path, content: str) -> Path:
    """Create a fake standards markdown file under a ``standards/`` subdirectory.

    Replicates ``<marketplace_root>/plan-marshall/skills/<skill>/standards/<doc>.md``.
    """
    standards_dir = _standards_dir(tmp_path)
    md = standards_dir / 'detail.md'
    md.write_text(content, encoding='utf-8')
    return md


def _make_skill_md(tmp_path: Path, content: str) -> Path:
    """Create a fake plan-marshall skill markdown file under tmp_path.

    Replicates ``<marketplace_root>/plan-marshall/skills/<skill>/SKILL.md``.
    """
    skill_dir = tmp_path / 'plan-marshall' / 'skills' / 'test-skill'
    skill_dir.mkdir(parents=True, exist_ok=True)
    md = skill_dir / 'SKILL.md'
    md.write_text(content, encoding='utf-8')
    return md


def _place_parent_sibling(tmp_path: Path, name: str) -> Path:
    """Create ``name`` in the skill dir (the PARENT of ``standards/``)."""
    skill_dir = tmp_path / 'plan-marshall' / 'skills' / 'test-skill'
    skill_dir.mkdir(parents=True, exist_ok=True)
    sibling = skill_dir / name
    sibling.write_text('# parent sibling\n', encoding='utf-8')
    return sibling


def _place_same_dir_sibling(tmp_path: Path, name: str) -> Path:
    """Create ``name`` alongside the standards detail file (same dir)."""
    sibling = _standards_dir(tmp_path) / name
    sibling.write_text('# same-dir sibling\n', encoding='utf-8')
    return sibling


def _make_agent_md(tmp_path: Path, content: str) -> Path:
    """Create a fake plan-marshall agent markdown file under tmp_path."""
    agents_dir = tmp_path / 'plan-marshall' / 'agents'
    agents_dir.mkdir(parents=True, exist_ok=True)
    md = agents_dir / 'test-agent.md'
    md.write_text(content, encoding='utf-8')
    return md


# ---------------------------------------------------------------------------
# Pattern 1: broken parent-relative link (filesystem-verified)
# ---------------------------------------------------------------------------


class TestBrokenParentLinkDetected:
    def test_bare_sibling_link_resolving_in_parent_flagged(self, tmp_path):
        # sibling.md exists ONLY in the parent dir → the bare target is broken.
        _place_parent_sibling(tmp_path, 'sibling.md')
        content = 'See [the sibling doc](sibling.md) for the contract.\n'
        _make_standards_md(tmp_path, content)
        findings = analyze_markdown_link_bare_filename(tmp_path)
        assert len(findings) == 1
        assert findings[0]['rule_id'] == RULE_ID

    def test_same_dir_link_not_flagged(self, tmp_path):
        # sibling.md exists in the SAME dir as the referencing file → correct.
        _place_same_dir_sibling(tmp_path, 'sibling.md')
        content = 'See [the sibling doc](sibling.md) for the contract.\n'
        _make_standards_md(tmp_path, content)
        findings = analyze_markdown_link_bare_filename(tmp_path)
        assert findings == []

    def test_escape_link_not_flagged(self, tmp_path):
        # A correct ../sibling.md escape link has a path separator → out of
        # pattern 1's no-separator scope, and is not flagged.
        _place_parent_sibling(tmp_path, 'sibling.md')
        content = 'See [the sibling doc](../sibling.md) for the contract.\n'
        _make_standards_md(tmp_path, content)
        findings = analyze_markdown_link_bare_filename(tmp_path)
        assert findings == []

    def test_separator_link_not_flagged(self, tmp_path):
        content = 'See [the nested doc](dir/file.md) for the contract.\n'
        _make_standards_md(tmp_path, content)
        findings = analyze_markdown_link_bare_filename(tmp_path)
        assert findings == []

    def test_target_in_neither_dir_not_flagged(self, tmp_path):
        # No sibling.md on disk anywhere → out of scope (renamed/external).
        content = 'See [the sibling doc](sibling.md) for the contract.\n'
        _make_standards_md(tmp_path, content)
        findings = analyze_markdown_link_bare_filename(tmp_path)
        assert findings == []


# ---------------------------------------------------------------------------
# Pattern 2: odd-one-out plain-text cross-reference in a link list
# ---------------------------------------------------------------------------


class TestOddOneOutListDetected:
    def test_plain_text_sibling_among_md_links_flagged(self, tmp_path):
        content = (
            'See also:\n'
            '\n'
            '- [Coverage contract](../thoroughness.md)\n'
            '- [Scope rules](../scope.md)\n'
            '- siblings.md\n'
        )
        _make_skill_md(tmp_path, content)
        findings = analyze_markdown_link_bare_filename(tmp_path)
        assert len(findings) == 1
        assert findings[0]['rule_id'] == RULE_ID
        assert findings[0]['line'] == 5

    def test_pure_prose_list_with_bare_md_not_flagged(self, tmp_path):
        # No item in this list is a .md link → not a cross-reference list.
        content = (
            'Steps:\n'
            '\n'
            '- Read the config\n'
            '- Update siblings.md if present\n'
            '- Run the gate\n'
        )
        _make_skill_md(tmp_path, content)
        findings = analyze_markdown_link_bare_filename(tmp_path)
        assert findings == []

    def test_uniform_link_list_not_flagged(self, tmp_path):
        # Every item is a navigable link → no odd-one-out.
        content = (
            'See also:\n'
            '\n'
            '- [Coverage contract](../thoroughness.md)\n'
            '- [Scope rules](../scope.md)\n'
        )
        _make_skill_md(tmp_path, content)
        findings = analyze_markdown_link_bare_filename(tmp_path)
        assert findings == []


# ---------------------------------------------------------------------------
# Dropped blanket prose detection (now NEGATIVE assertions)
# ---------------------------------------------------------------------------


class TestBareProseTokenNotFlagged:
    def test_bare_md_token_in_prose_not_flagged(self, tmp_path):
        content = (
            '# Test Skill\n'
            '\n'
            'See thoroughness.md for the coverage contract.\n'
        )
        _make_skill_md(tmp_path, content)
        findings = analyze_markdown_link_bare_filename(tmp_path)
        assert findings == []

    def test_bare_md_token_in_agent_md_not_flagged(self, tmp_path):
        content = 'The dispatcher loads agents.md before any work begins.\n'
        _make_agent_md(tmp_path, content)
        findings = analyze_markdown_link_bare_filename(tmp_path)
        assert findings == []

    def test_subpath_named_token_in_prose_not_flagged(self, tmp_path):
        content = 'Refer to release.notes.md for details.\n'
        _make_skill_md(tmp_path, content)
        findings = analyze_markdown_link_bare_filename(tmp_path)
        assert findings == []


# ---------------------------------------------------------------------------
# Context exemptions (never flagged)
# ---------------------------------------------------------------------------


class TestContextExemptions:
    def test_md_link_in_fenced_code_block_not_flagged(self, tmp_path):
        # A would-be odd-one-out list inside a fence is exempt.
        _place_parent_sibling(tmp_path, 'sibling.md')
        content = (
            '```\n'
            '- [Coverage contract](../thoroughness.md)\n'
            '- siblings.md\n'
            '```\n'
        )
        _make_skill_md(tmp_path, content)
        findings = analyze_markdown_link_bare_filename(tmp_path)
        assert findings == []

    def test_broken_link_in_info_string_fence_not_flagged(self, tmp_path):
        _place_parent_sibling(tmp_path, 'sibling.md')
        content = (
            '```python\n'
            'link = "[the sibling doc](sibling.md)"\n'
            '```\n'
        )
        _make_standards_md(tmp_path, content)
        findings = analyze_markdown_link_bare_filename(tmp_path)
        assert findings == []

    def test_bare_md_in_inline_code_span_not_flagged(self, tmp_path):
        # An inline-code list item among .md links is exempt.
        content = (
            'See also:\n'
            '\n'
            '- [Coverage contract](../thoroughness.md)\n'
            '- `siblings.md`\n'
        )
        _make_skill_md(tmp_path, content)
        findings = analyze_markdown_link_bare_filename(tmp_path)
        assert findings == []

    def test_broken_link_in_html_comment_not_flagged(self, tmp_path):
        _place_parent_sibling(tmp_path, 'sibling.md')
        content = (
            '<!-- See [the sibling doc](sibling.md) for the contract. -->\n'
            'Visible prose with no bare token.\n'
        )
        _make_standards_md(tmp_path, content)
        findings = analyze_markdown_link_bare_filename(tmp_path)
        assert findings == []

    def test_broken_link_in_multiline_html_comment_not_flagged(self, tmp_path):
        _place_parent_sibling(tmp_path, 'sibling.md')
        content = (
            '<!--\n'
            'See [the sibling doc](sibling.md) for the contract.\n'
            '-->\n'
            'Visible prose with no bare token.\n'
        )
        _make_standards_md(tmp_path, content)
        findings = analyze_markdown_link_bare_filename(tmp_path)
        assert findings == []

    def test_correct_navigable_link_not_flagged(self, tmp_path):
        content = (
            'See [the coverage contract](../thoroughness.md) for details.\n'
        )
        _make_skill_md(tmp_path, content)
        findings = analyze_markdown_link_bare_filename(tmp_path)
        assert findings == []


# ---------------------------------------------------------------------------
# Finding shape
# ---------------------------------------------------------------------------


class TestFindingShape:
    def test_required_fields_present(self, tmp_path):
        _place_parent_sibling(tmp_path, 'sibling.md')
        content = 'See [the sibling doc](sibling.md) for the contract.\n'
        _make_standards_md(tmp_path, content)
        findings = analyze_markdown_link_bare_filename(tmp_path)
        assert len(findings) == 1
        f = findings[0]
        assert f['rule_id'] == RULE_ID
        assert f['type'] == FINDING_TYPE
        assert f['rule'] == RULE_NAME
        assert isinstance(f['file'], str)
        assert isinstance(f['line'], int)
        assert f['severity'] == 'error'
        assert f['fixable'] is False
        assert isinstance(f['snippet'], str)
        assert isinstance(f['description'], str)

    def test_line_number_is_one_based(self, tmp_path):
        _place_parent_sibling(tmp_path, 'sibling.md')
        content = (
            'Intro text.\n'
            '\n'
            'See [the sibling doc](sibling.md) for the contract.\n'
        )
        _make_standards_md(tmp_path, content)
        findings = analyze_markdown_link_bare_filename(tmp_path)
        assert len(findings) == 1
        assert findings[0]['line'] == 3

    def test_file_path_is_absolute(self, tmp_path):
        _place_parent_sibling(tmp_path, 'sibling.md')
        content = 'See [the sibling doc](sibling.md) for the contract.\n'
        _make_standards_md(tmp_path, content)
        findings = analyze_markdown_link_bare_filename(tmp_path)
        assert len(findings) == 1
        assert Path(findings[0]['file']).is_absolute()


# ---------------------------------------------------------------------------
# Clean baseline
# ---------------------------------------------------------------------------


class TestCleanBaseline:
    def test_clean_tree_no_findings(self, tmp_path):
        content = (
            '# My Skill\n'
            '\n'
            'This skill does things and references no bare filenames.\n'
            'See [the coverage contract](../thoroughness.md) for details.\n'
        )
        _make_skill_md(tmp_path, content)
        findings = analyze_markdown_link_bare_filename(tmp_path)
        assert findings == []

    def test_empty_marketplace_root_no_findings(self, tmp_path):
        findings = analyze_markdown_link_bare_filename(tmp_path)
        assert findings == []
