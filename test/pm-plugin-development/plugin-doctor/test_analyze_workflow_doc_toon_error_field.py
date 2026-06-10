# ruff: noqa: I001, E402
"""Unit tests for _analyze_workflow_doc_toon_error_field.py.

Covers the WORKFLOW_DOC_TOON_ERROR_FIELD analyzer:

- Detection of ``error_type:`` (colon-style) inside fenced ``toon`` blocks
- Detection of ``error_type\\t`` (tab-style) inside fenced ``toon`` blocks
- No false-positive on the canonical ``error:`` discriminator
- No false-positive on inline ``{status: error, error_type: ...}`` brace shorthands
- Prose ``error_type:`` references outside any fence are NOT scanned
- ``error_type`` inside a non-``toon`` fence (python/json) is NOT scanned
- Finding shape: all required fields present and correctly typed
- Agent markdown is scanned alongside skill markdown
- Clean baseline: no fenced TOON error_type produces no findings
- The rule appears in the doctor-marketplace rule registry (provenance table)
"""
from pathlib import Path

from conftest import load_script_module


def _load_module(name: str, filename: str):
    return load_script_module('pm-plugin-development', 'plugin-doctor', filename, name)


_awd = _load_module(
    '_analyze_workflow_doc_toon_error_field',
    '_analyze_workflow_doc_toon_error_field.py',
)
analyze_workflow_doc_toon_error_field = _awd.analyze_workflow_doc_toon_error_field
RULE_ID = _awd.RULE_ID
RULE_NAME = _awd.RULE_NAME
FINDING_TYPE = _awd.FINDING_TYPE

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
PROVENANCE_PATH = (
    PROJECT_ROOT
    / 'marketplace'
    / 'bundles'
    / 'pm-plugin-development'
    / 'skills'
    / 'plugin-doctor'
    / 'references'
    / 'rule-provenance.md'
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_skill_md(tmp_path: Path, content: str) -> Path:
    """Create a fake plan-marshall skill markdown file under tmp_path.

    Replicates the directory structure the scanner walks:
    ``<marketplace_root>/plan-marshall/skills/<skill>/SKILL.md``.
    """
    skill_dir = tmp_path / 'plan-marshall' / 'skills' / 'test-skill'
    skill_dir.mkdir(parents=True, exist_ok=True)
    md = skill_dir / 'SKILL.md'
    md.write_text(content, encoding='utf-8')
    return md


def _make_agent_md(tmp_path: Path, content: str) -> Path:
    """Create a fake plan-marshall agent markdown file under tmp_path."""
    agents_dir = tmp_path / 'plan-marshall' / 'agents'
    agents_dir.mkdir(parents=True, exist_ok=True)
    md = agents_dir / 'test-agent.md'
    md.write_text(content, encoding='utf-8')
    return md


# ---------------------------------------------------------------------------
# Detection inside fenced toon blocks
# ---------------------------------------------------------------------------


class TestErrorTypeDetected:
    def test_colon_style_error_type_detected(self, tmp_path):
        content = (
            'Some prose.\n'
            '```toon\n'
            'status: error\n'
            'error_type: refine_contract_violation\n'
            '```\n'
        )
        _make_skill_md(tmp_path, content)
        findings = analyze_workflow_doc_toon_error_field(tmp_path)
        assert len(findings) == 1
        assert findings[0]['rule_id'] == RULE_ID

    def test_tab_style_error_type_detected(self, tmp_path):
        content = (
            '```toon\n'
            'status\terror\n'
            'error_type\trefine_contract_violation\n'
            '```\n'
        )
        _make_skill_md(tmp_path, content)
        findings = analyze_workflow_doc_toon_error_field(tmp_path)
        assert len(findings) == 1

    def test_indented_error_type_detected(self, tmp_path):
        content = (
            '```toon\n'
            'result:\n'
            '  status: error\n'
            '  error_type: validation_failure\n'
            '```\n'
        )
        _make_skill_md(tmp_path, content)
        findings = analyze_workflow_doc_toon_error_field(tmp_path)
        assert len(findings) == 1

    def test_multiple_error_type_keys_each_flagged(self, tmp_path):
        content = (
            '```toon\n'
            'error_type: first\n'
            '```\n'
            'Prose between blocks.\n'
            '```toon\n'
            'error_type: second\n'
            '```\n'
        )
        _make_skill_md(tmp_path, content)
        findings = analyze_workflow_doc_toon_error_field(tmp_path)
        assert len(findings) == 2

    def test_agent_md_is_scanned(self, tmp_path):
        content = (
            '```toon\n'
            'status: error\n'
            'error_type: dispatch_failure\n'
            '```\n'
        )
        _make_agent_md(tmp_path, content)
        findings = analyze_workflow_doc_toon_error_field(tmp_path)
        assert len(findings) == 1


# ---------------------------------------------------------------------------
# No false-positive on the canonical error: key
# ---------------------------------------------------------------------------


class TestCanonicalErrorKeyClean:
    def test_canonical_error_key_not_flagged(self, tmp_path):
        content = (
            '```toon\n'
            'status: error\n'
            'error: refine_contract_violation\n'
            'display_detail: "Human-readable message"\n'
            '```\n'
        )
        _make_skill_md(tmp_path, content)
        findings = analyze_workflow_doc_toon_error_field(tmp_path)
        assert findings == []

    def test_error_substring_key_not_flagged(self, tmp_path):
        # A key that merely starts with ``error`` but is not ``error_type``
        # must not trip the anchored matcher.
        content = (
            '```toon\n'
            'status: error\n'
            'error_context: some detail\n'
            '```\n'
        )
        _make_skill_md(tmp_path, content)
        findings = analyze_workflow_doc_toon_error_field(tmp_path)
        assert findings == []


# ---------------------------------------------------------------------------
# Out-of-scope sites (deliberate exclusions)
# ---------------------------------------------------------------------------


class TestOutOfScopeExclusions:
    def test_inline_brace_shorthand_not_flagged(self, tmp_path):
        content = (
            '```toon\n'
            'errors[1]{status,error_type}:\n'
            '  error,validation_failure\n'
            '```\n'
        )
        _make_skill_md(tmp_path, content)
        findings = analyze_workflow_doc_toon_error_field(tmp_path)
        assert findings == []

    def test_prose_error_type_not_flagged(self, tmp_path):
        content = (
            'The workflow returns `error_type:` in its TOON block.\n'
            'Another line mentioning error_type: as a field name.\n'
        )
        _make_skill_md(tmp_path, content)
        findings = analyze_workflow_doc_toon_error_field(tmp_path)
        assert findings == []

    def test_error_type_in_python_fence_not_flagged(self, tmp_path):
        content = (
            '```python\n'
            'error_type: str = "validation_failure"\n'
            '```\n'
        )
        _make_skill_md(tmp_path, content)
        findings = analyze_workflow_doc_toon_error_field(tmp_path)
        assert findings == []

    def test_error_type_in_json_fence_not_flagged(self, tmp_path):
        content = (
            '```json\n'
            '{"error_type": "validation_failure"}\n'
            '```\n'
        )
        _make_skill_md(tmp_path, content)
        findings = analyze_workflow_doc_toon_error_field(tmp_path)
        assert findings == []


# ---------------------------------------------------------------------------
# Finding shape
# ---------------------------------------------------------------------------


class TestFindingShape:
    def test_required_fields_present(self, tmp_path):
        content = (
            '```toon\n'
            'status: error\n'
            'error_type: refine_contract_violation\n'
            '```\n'
        )
        _make_skill_md(tmp_path, content)
        findings = analyze_workflow_doc_toon_error_field(tmp_path)
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

    def test_line_number_correct(self, tmp_path):
        content = (
            'Intro text.\n'
            '\n'
            '```toon\n'
            'status: error\n'
            'error_type: validation_failure\n'
            '```\n'
        )
        _make_skill_md(tmp_path, content)
        findings = analyze_workflow_doc_toon_error_field(tmp_path)
        assert len(findings) == 1
        # error_type is on the 5th line (1-based).
        assert findings[0]['line'] == 5

    def test_file_path_is_absolute(self, tmp_path):
        content = (
            '```toon\n'
            'error_type: validation_failure\n'
            '```\n'
        )
        _make_skill_md(tmp_path, content)
        findings = analyze_workflow_doc_toon_error_field(tmp_path)
        assert len(findings) == 1
        assert Path(findings[0]['file']).is_absolute()


# ---------------------------------------------------------------------------
# Clean baseline
# ---------------------------------------------------------------------------


class TestCleanBaseline:
    def test_no_toon_fences_no_findings(self, tmp_path):
        content = (
            '# My Skill\n'
            '\n'
            'This skill does things and returns an error envelope.\n'
        )
        _make_skill_md(tmp_path, content)
        findings = analyze_workflow_doc_toon_error_field(tmp_path)
        assert findings == []

    def test_empty_marketplace_root_no_findings(self, tmp_path):
        # No plan-marshall bundle directory at all.
        findings = analyze_workflow_doc_toon_error_field(tmp_path)
        assert findings == []


# ---------------------------------------------------------------------------
# Rule registry presence
# ---------------------------------------------------------------------------


class TestRuleRegistry:
    """The rule must be registered in the doctor-marketplace provenance table.

    ``rule-provenance.md`` is the source-of-truth registry that
    ``test_rule_provenance_table.py`` audits against every emitted rule_id.
    This pins the WORKFLOW_DOC_TOON_ERROR_FIELD row directly so the rule's
    registration cannot silently regress.
    """

    def test_rule_id_in_provenance_table(self):
        content = PROVENANCE_PATH.read_text(encoding='utf-8')
        assert RULE_ID in content, (
            f'{RULE_ID} must appear in rule-provenance.md (the doctor-marketplace '
            f'rule registry) so the provenance audit recognizes the emitted rule.'
        )

    def test_rule_id_appears_in_a_table_row(self):
        content = PROVENANCE_PATH.read_text(encoding='utf-8')
        rows = [
            line
            for line in content.splitlines()
            if line.startswith('|') and RULE_ID in line
        ]
        assert rows, (
            f'{RULE_ID} must appear in a pipe-delimited table row in '
            f'rule-provenance.md, not only in prose.'
        )
        # The first cell must carry the rule ID (backtick-wrapped per the table convention).
        first_cell = rows[0].split('|')[1].strip().strip('`')
        assert first_cell == RULE_ID
