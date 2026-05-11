# ruff: noqa: I001, E402
"""Tests for the file-bloat frontmatter ack mechanism in ``_doctor_analysis.py``.

The ack mechanism suppresses ``file-bloat`` and ``subdoc-bloat`` issue
emission when the analyzed file carries a valid
``quality.file-bloat: ack-<rationale-slug>`` key in its YAML frontmatter.

Three fixture scenarios per the solution outline:
  a. Bloated file WITHOUT ack — finding emitted (regression check on existing
     behavior, i.e. the ack did NOT silently change the no-ack path).
  b. Bloated file WITH valid ack ``ack-validator-registry`` — no finding,
     ``bloat_ack_tag`` key surfaces in analysis output.
  c. Bloated file with MALFORMED ack value (``quality.file-bloat: yes``) —
     finding still emitted (malformed values do not suppress).

Additional cases:
  d. NORMAL-sized file — no finding regardless of ack presence.
  e. ``subdoc-bloat`` path — same ack logic applies to sub-documents.
"""

import importlib.util
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
_SCRIPTS_DIR = (
    PROJECT_ROOT
    / 'marketplace'
    / 'bundles'
    / 'pm-plugin-development'
    / 'skills'
    / 'plugin-doctor'
    / 'scripts'
)

sys.path.insert(0, str(_SCRIPTS_DIR))

# file_ops lives in a different bundle; add its dir to sys.path so
# `from file_ops import ...` resolves via the normal import machinery
# (this is the same arrangement conftest/PYTHONPATH provides at runtime).
_FILE_OPS_DIR = (
    PROJECT_ROOT
    / 'marketplace'
    / 'bundles'
    / 'plan-marshall'
    / 'skills'
    / 'tools-file-ops'
    / 'scripts'
)
sys.path.insert(0, str(_FILE_OPS_DIR))


def _load_module(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, _SCRIPTS_DIR / filename)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


# Load dependency chain in order
_load_module('_analyze_shared', '_analyze_shared.py')
_load_module('_analyze_markdown', '_analyze_markdown.py')
_load_module('_analyze_structure', '_analyze_structure.py')
_load_module('_analyze_coverage', '_analyze_coverage.py')
_load_module('_analyze_crossfile', '_analyze_crossfile.py')
_load_module('_analyze_verb_chains', '_analyze_verb_chains.py')
_load_module('_analyze_shell_active_tokens', '_analyze_shell_active_tokens.py')
_load_module('_analyze_metadata_field_validity', '_analyze_metadata_field_validity.py')
_load_module('_analyze_resolution_branch_markers', '_analyze_resolution_branch_markers.py')
_load_module('_analyze_executor_path_in_production', '_analyze_executor_path_in_production.py')
_load_module('_analyze_orphan_argparse_flags', '_analyze_orphan_argparse_flags.py')
_load_module('_analyze_cmd_root_anchoring', '_analyze_cmd_root_anchoring.py')
_load_module('_analyze_argument_naming', '_analyze_argument_naming.py')
_load_module('_analyze', '_analyze.py')
_da = _load_module('_doctor_analysis', '_doctor_analysis.py')

_has_file_bloat_ack = _da._has_file_bloat_ack
_read_file_bloat_ack_tag = _da._read_file_bloat_ack_tag
extract_issues_from_markdown_analysis = _da.extract_issues_from_markdown_analysis
analyze_subdocuments = _da.analyze_subdocuments
extract_issues_from_subdoc_analysis = _da.extract_issues_from_subdoc_analysis


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# 800-line bloated content body (exceeds BLOATED threshold for agents/commands).
_BLOAT_BODY = 'line\n' * 800


def _bloated_agent_content(frontmatter_extra: str = '') -> str:
    """Create a minimal agent markdown that is BLOATED (800 lines)."""
    fm = (
        '---\n'
        'name: test-agent\n'
        'description: A test agent for bloat testing.\n'
        'tools:\n'
        '  - Read\n'
    )
    if frontmatter_extra:
        fm += frontmatter_extra
    fm += '---\n'
    return fm + _BLOAT_BODY


def _fake_analysis(bloat_class: str, line_count: int) -> dict:
    """Build a minimal analysis dict matching what analyze_markdown_file returns."""
    return {
        'frontmatter': {
            'present': True,
            'yaml_valid': True,
            'required_fields': {
                'name': {'present': True},
                'description': {'present': True},
                'tools': {'present': True, 'field_type': 'tools'},
                'user_invocable': {'present': False, 'misspelled': False, 'value': None},
            },
        },
        'metrics': {'line_count': line_count},
        'bloat': {'classification': bloat_class},
        'rules': {
            'agent_task_tool_prohibited': False,
            'agent_maven_restricted': False,
            'workflow_hardcoded_script_path': False,
            'agent_skill_tool_visibility': False,
            'workflow_prose_param_violations': [],
            'mark_step_done_violations': [],
            'resolver_gap_violations': [],
            'display_detail_violations': [],
            'hardcoded_model_on_canonical_violations': [],
        },
        'continuous_improvement_rule': {'format': {}},
        'checklist_patterns': {'has_checklists': False},
        'content_mode': {'is_reference': False},
    }


# ===========================================================================
# Unit tests for _has_file_bloat_ack and _read_file_bloat_ack_tag
# ===========================================================================


class TestAckHelpers:
    """Unit tests for the frontmatter ack extraction helpers."""

    def test_valid_ack_nested(self) -> None:
        """Nested quality block with valid ack tag returns True + tag."""
        content = (
            '---\n'
            'name: foo\n'
            'quality:\n'
            '  file-bloat: ack-validator-registry\n'
            '---\n'
            'body\n'
        )
        ack_present, tag = _has_file_bloat_ack(content)
        assert ack_present is True
        assert tag == 'validator-registry'

    def test_malformed_ack_value(self) -> None:
        """Malformed ack value (e.g. 'yes') does not suppress."""
        content = (
            '---\n'
            'name: foo\n'
            'quality:\n'
            '  file-bloat: yes\n'
            '---\n'
            'body\n'
        )
        ack_present, tag = _has_file_bloat_ack(content)
        assert ack_present is False
        assert tag is None

    def test_no_frontmatter(self) -> None:
        """File without frontmatter has no ack."""
        content = '# Just a heading\nbody\n'
        ack_present, tag = _has_file_bloat_ack(content)
        assert ack_present is False
        assert tag is None

    def test_no_quality_block(self) -> None:
        """Frontmatter without quality block has no ack."""
        content = '---\nname: foo\ndescription: bar\n---\nbody\n'
        ack_present, tag = _has_file_bloat_ack(content)
        assert ack_present is False
        assert tag is None

    def test_ack_tag_with_numbers(self) -> None:
        """Ack tag with numbers is valid."""
        content = (
            '---\nname: foo\nquality:\n  file-bloat: ack-large-doc-v2\n---\nbody\n'
        )
        ack_present, tag = _has_file_bloat_ack(content)
        assert ack_present is True
        assert tag == 'large-doc-v2'

    def test_ack_without_rationale_slug_invalid(self) -> None:
        """Bare 'ack-' without a following slug is invalid."""
        content = '---\nname: foo\nquality:\n  file-bloat: ack-\n---\nbody\n'
        ack_present, tag = _has_file_bloat_ack(content)
        assert ack_present is False


# ===========================================================================
# Fixture a: Bloated file without ack — finding emitted
# ===========================================================================


class TestBloatWithoutAck:
    """Regression: existing file-bloat behavior unchanged for no-ack files."""

    def test_bloated_agent_without_ack_emits_finding(self, tmp_path: Path) -> None:
        """BLOATED file without ack tag produces a file-bloat finding."""
        content = _bloated_agent_content()
        md_file = tmp_path / 'agent.md'
        md_file.write_text(content, encoding='utf-8')

        analysis = _fake_analysis('BLOATED', 800)
        issues = extract_issues_from_markdown_analysis(analysis, str(md_file), 'agent')
        bloat_issues = [i for i in issues if i['type'] == 'file-bloat']
        assert len(bloat_issues) == 1
        assert bloat_issues[0]['classification'] == 'BLOATED'

    def test_critical_file_without_ack_emits_error_finding(self, tmp_path: Path) -> None:
        """CRITICAL file without ack tag produces a file-bloat finding with severity error."""
        content = _bloated_agent_content()
        md_file = tmp_path / 'agent.md'
        md_file.write_text(content, encoding='utf-8')

        analysis = _fake_analysis('CRITICAL', 1200)
        issues = extract_issues_from_markdown_analysis(analysis, str(md_file), 'agent')
        bloat_issues = [i for i in issues if i['type'] == 'file-bloat']
        assert len(bloat_issues) == 1
        assert bloat_issues[0]['severity'] == 'error'


# ===========================================================================
# Fixture b: Bloated file WITH valid ack — no finding, bloat_ack_tag in output
# ===========================================================================


class TestBloatWithValidAck:
    """Valid ack suppresses the finding and surfaces bloat_ack_tag."""

    def test_valid_ack_suppresses_finding(self, tmp_path: Path) -> None:
        """File with valid ack produces no file-bloat finding."""
        content = _bloated_agent_content(
            frontmatter_extra='quality:\n  file-bloat: ack-validator-registry\n'
        )
        md_file = tmp_path / 'agent.md'
        md_file.write_text(content, encoding='utf-8')

        analysis = _fake_analysis('BLOATED', 800)
        issues = extract_issues_from_markdown_analysis(analysis, str(md_file), 'agent')
        bloat_issues = [i for i in issues if i['type'] == 'file-bloat']
        assert bloat_issues == []

    def test_ack_tag_surfaced_in_analysis(self, tmp_path: Path) -> None:
        """After suppression, the ack tag is stored in the analysis dict."""
        content = _bloated_agent_content(
            frontmatter_extra='quality:\n  file-bloat: ack-validator-registry\n'
        )
        md_file = tmp_path / 'agent.md'
        md_file.write_text(content, encoding='utf-8')

        analysis = _fake_analysis('BLOATED', 800)
        extract_issues_from_markdown_analysis(analysis, str(md_file), 'agent')
        assert analysis.get('bloat_ack_tag') == 'validator-registry'

    def test_critical_with_valid_ack_also_suppressed(self, tmp_path: Path) -> None:
        """CRITICAL bloat is also suppressed by a valid ack."""
        content = _bloated_agent_content(
            frontmatter_extra='quality:\n  file-bloat: ack-huge-legacy\n'
        )
        md_file = tmp_path / 'agent.md'
        md_file.write_text(content, encoding='utf-8')

        analysis = _fake_analysis('CRITICAL', 1200)
        issues = extract_issues_from_markdown_analysis(analysis, str(md_file), 'agent')
        bloat_issues = [i for i in issues if i['type'] == 'file-bloat']
        assert bloat_issues == []


# ===========================================================================
# Fixture c: Bloated file with MALFORMED ack — finding still emitted
# ===========================================================================


class TestBloatWithMalformedAck:
    """Malformed ack values do not suppress the finding."""

    def test_malformed_ack_yes_does_not_suppress(self, tmp_path: Path) -> None:
        """``quality.file-bloat: yes`` is not a valid ack — finding still emitted."""
        content = _bloated_agent_content(
            frontmatter_extra='quality:\n  file-bloat: yes\n'
        )
        md_file = tmp_path / 'agent.md'
        md_file.write_text(content, encoding='utf-8')

        analysis = _fake_analysis('BLOATED', 800)
        issues = extract_issues_from_markdown_analysis(analysis, str(md_file), 'agent')
        bloat_issues = [i for i in issues if i['type'] == 'file-bloat']
        assert len(bloat_issues) == 1

    def test_malformed_ack_true_does_not_suppress(self, tmp_path: Path) -> None:
        """``quality.file-bloat: true`` is not a valid ack — finding still emitted."""
        content = _bloated_agent_content(
            frontmatter_extra='quality:\n  file-bloat: true\n'
        )
        md_file = tmp_path / 'agent.md'
        md_file.write_text(content, encoding='utf-8')

        analysis = _fake_analysis('BLOATED', 800)
        issues = extract_issues_from_markdown_analysis(analysis, str(md_file), 'agent')
        bloat_issues = [i for i in issues if i['type'] == 'file-bloat']
        assert len(bloat_issues) == 1

    def test_malformed_bare_ack_does_not_suppress(self, tmp_path: Path) -> None:
        """``quality.file-bloat: ack-`` (no rationale slug) is not valid."""
        content = _bloated_agent_content(
            frontmatter_extra='quality:\n  file-bloat: ack-\n'
        )
        md_file = tmp_path / 'agent.md'
        md_file.write_text(content, encoding='utf-8')

        analysis = _fake_analysis('BLOATED', 800)
        issues = extract_issues_from_markdown_analysis(analysis, str(md_file), 'agent')
        bloat_issues = [i for i in issues if i['type'] == 'file-bloat']
        assert len(bloat_issues) == 1


# ===========================================================================
# Fixture d: NORMAL-sized file — no finding
# ===========================================================================


class TestNormalSizedFile:
    """NORMAL-sized files produce no file-bloat finding regardless of ack."""

    def test_normal_file_no_finding(self, tmp_path: Path) -> None:
        content = '---\nname: foo\ndescription: bar\ntools:\n  - Read\n---\nbody\n'
        md_file = tmp_path / 'agent.md'
        md_file.write_text(content, encoding='utf-8')

        analysis = _fake_analysis('NORMAL', 20)
        issues = extract_issues_from_markdown_analysis(analysis, str(md_file), 'agent')
        bloat_issues = [i for i in issues if i['type'] == 'file-bloat']
        assert bloat_issues == []


# ===========================================================================
# Fixture e: subdoc-bloat path honors the ack
# ===========================================================================


class TestSubdocBloatAck:
    """The subdoc-bloat path in analyze_subdocuments honors the ack."""

    def _make_bloated_subdoc(self, skill_dir: Path, subdir: str, ack_tag: str | None) -> Path:
        """Create a bloated sub-document under ``skill_dir/<subdir>/``."""
        sub = skill_dir / subdir
        sub.mkdir(parents=True, exist_ok=True)
        if ack_tag:
            frontmatter = f'---\nname: doc\nquality:\n  file-bloat: {ack_tag}\n---\n'
        else:
            frontmatter = '---\nname: doc\n---\n'
        # Subdoc BLOATED threshold is >600 lines (see _analyze_markdown.get_bloat_classification).
        content = frontmatter + 'body\n' * 650
        md = sub / 'big.md'
        md.write_text(content, encoding='utf-8')
        return md

    def test_subdoc_bloat_without_ack_emits_issue(self, tmp_path: Path) -> None:
        """Bloated subdoc without ack produces a subdoc-bloat issue."""
        skill_dir = tmp_path / 'skill'
        self._make_bloated_subdoc(skill_dir, 'references', None)
        subdoc_results = analyze_subdocuments(skill_dir)
        issues = extract_issues_from_subdoc_analysis(subdoc_results, str(skill_dir))
        bloat_issues = [i for i in issues if i['type'] == 'subdoc-bloat']
        assert len(bloat_issues) >= 1

    def test_subdoc_bloat_with_valid_ack_suppressed(self, tmp_path: Path) -> None:
        """Bloated subdoc with valid ack produces no subdoc-bloat issue."""
        skill_dir = tmp_path / 'skill'
        self._make_bloated_subdoc(skill_dir, 'references', 'ack-large-ref-doc')
        subdoc_results = analyze_subdocuments(skill_dir)
        issues = extract_issues_from_subdoc_analysis(subdoc_results, str(skill_dir))
        bloat_issues = [i for i in issues if i['type'] == 'subdoc-bloat']
        assert bloat_issues == []
