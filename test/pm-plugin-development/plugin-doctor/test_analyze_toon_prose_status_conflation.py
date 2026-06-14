# ruff: noqa: I001, E402
"""Unit tests for _analyze_toon_prose_status_conflation.py.

Covers the MANAGE_STATUS_PROSE_CONFLATION analyzer, which flags inline-code
prose of the form ``status: {specific_code}`` that conflates the two-tier TOON
error envelope.

The canonical failure envelope writes the discriminator on ``status`` (always
the literal ``error``) and the specific failure code on the ``error`` field.
Prose that writes ``status: plan_not_found`` (or any ``status: {code}`` where
``{code}`` is neither ``error`` nor ``success``) collapses the two tiers into
one and misdescribes the contract.

Detection scope (inline-code spans ONLY):

- A ``status: {code}`` shape inside a backtick-wrapped inline-code span is
  flagged when ``{code}`` is neither ``error`` nor ``success``.

Context exemptions (never flagged):

- ``status: error`` / ``status: success`` inside inline-code spans (the two
  correct top-level discriminator values)
- ``status: {code}`` in plain prose (outside any inline-code span)
- ``status: {code}`` inside a fenced code block (any info-string)

Finding-shape coverage:

- All required fields present and correctly typed
- 1-based line numbers
- Absolute file paths

Scope: a markdown file outside the plan-marshall bundle is NOT scanned.

Clean baseline: a clean tree yields an empty finding list.
"""
from pathlib import Path

from conftest import load_script_module


def _load_module(name: str, filename: str):
    return load_script_module('pm-plugin-development', 'plugin-doctor', filename, name)


_atp = _load_module(
    '_analyze_toon_prose_status_conflation',
    '_analyze_toon_prose_status_conflation.py',
)
analyze_toon_prose_status_conflation = _atp.analyze_toon_prose_status_conflation
RULE_ID = _atp.RULE_ID
RULE_NAME = _atp.RULE_NAME
FINDING_TYPE = _atp.FINDING_TYPE


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


def _make_other_bundle_md(tmp_path: Path, content: str) -> Path:
    """Create a fake skill markdown file in a NON-plan-marshall bundle.

    The analyzer only walks ``<marketplace_root>/plan-marshall/...`` — a file
    under another bundle (e.g. ``pm-dev-java``) must never be scanned.
    """
    skill_dir = tmp_path / 'pm-dev-java' / 'skills' / 'java-core'
    skill_dir.mkdir(parents=True, exist_ok=True)
    md = skill_dir / 'SKILL.md'
    md.write_text(content, encoding='utf-8')
    return md


# ---------------------------------------------------------------------------
# Positive detection: conflated inline-code status code
# ---------------------------------------------------------------------------


class TestConflationDetected:
    def test_status_not_found_in_inline_code_flagged(self, tmp_path):
        content = (
            '# Test Skill\n'
            '\n'
            'On a missing plan the script returns `status: not_found`.\n'
        )
        _make_skill_md(tmp_path, content)
        findings = analyze_toon_prose_status_conflation(tmp_path)
        assert len(findings) == 1
        assert findings[0]['rule_id'] == RULE_ID

    def test_status_plan_not_found_in_inline_code_flagged(self, tmp_path):
        content = (
            'When the plan dir is absent it emits `status: plan_not_found`.\n'
        )
        _make_skill_md(tmp_path, content)
        findings = analyze_toon_prose_status_conflation(tmp_path)
        assert len(findings) == 1
        assert findings[0]['rule_id'] == RULE_ID

    def test_status_code_in_agent_md_flagged(self, tmp_path):
        content = (
            'The dispatcher surfaces `status: dispatch_failure` on a bad route.\n'
        )
        _make_agent_md(tmp_path, content)
        findings = analyze_toon_prose_status_conflation(tmp_path)
        assert len(findings) == 1

    def test_multiple_conflated_spans_each_flagged(self, tmp_path):
        content = (
            'It can return `status: not_found` or `status: plan_not_found`.\n'
        )
        _make_skill_md(tmp_path, content)
        findings = analyze_toon_prose_status_conflation(tmp_path)
        assert len(findings) == 2


# ---------------------------------------------------------------------------
# Exempt: the two correct top-level discriminator values
# ---------------------------------------------------------------------------


class TestCorrectDiscriminatorClean:
    def test_status_error_in_inline_code_not_flagged(self, tmp_path):
        content = (
            'On failure the envelope carries `status: error` plus an error field.\n'
        )
        _make_skill_md(tmp_path, content)
        findings = analyze_toon_prose_status_conflation(tmp_path)
        assert findings == []

    def test_status_success_in_inline_code_not_flagged(self, tmp_path):
        content = (
            'A clean run reports `status: success` at the top level.\n'
        )
        _make_skill_md(tmp_path, content)
        findings = analyze_toon_prose_status_conflation(tmp_path)
        assert findings == []


# ---------------------------------------------------------------------------
# Out-of-scope sites (deliberate exclusions)
# ---------------------------------------------------------------------------


class TestOutOfScopeExclusions:
    def test_status_code_in_plain_prose_not_flagged(self, tmp_path):
        # No backticks — narrative text describing a value, not a contract
        # misdescription anchored to an inline-code span.
        content = (
            'On a missing plan the script returns status: not_found to the caller.\n'
        )
        _make_skill_md(tmp_path, content)
        findings = analyze_toon_prose_status_conflation(tmp_path)
        assert findings == []

    def test_status_code_in_fenced_block_not_flagged(self, tmp_path):
        # A fenced block (any info-string) illustrates a literal payload — exempt.
        content = (
            '```toon\n'
            'status: foo\n'
            '```\n'
        )
        _make_skill_md(tmp_path, content)
        findings = analyze_toon_prose_status_conflation(tmp_path)
        assert findings == []

    def test_status_code_in_info_string_fence_not_flagged(self, tmp_path):
        content = (
            '```python\n'
            'result = "status: not_found"\n'
            '```\n'
        )
        _make_skill_md(tmp_path, content)
        findings = analyze_toon_prose_status_conflation(tmp_path)
        assert findings == []


# ---------------------------------------------------------------------------
# Scope: only the plan-marshall bundle is scanned
# ---------------------------------------------------------------------------


class TestScopeRestriction:
    def test_other_bundle_md_not_scanned(self, tmp_path):
        # An offending inline-code span inside a non-plan-marshall bundle must
        # not be reported — TOON contracts are plan-marshall-owned prose.
        content = (
            'A foreign skill writes `status: not_found` but is out of scope.\n'
        )
        _make_other_bundle_md(tmp_path, content)
        findings = analyze_toon_prose_status_conflation(tmp_path)
        assert findings == []


# ---------------------------------------------------------------------------
# Finding shape
# ---------------------------------------------------------------------------


class TestFindingShape:
    def test_required_fields_present(self, tmp_path):
        content = (
            'On a missing plan the script returns `status: plan_not_found`.\n'
        )
        _make_skill_md(tmp_path, content)
        findings = analyze_toon_prose_status_conflation(tmp_path)
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
        content = (
            'Intro text.\n'
            '\n'
            'On a missing plan the script returns `status: not_found`.\n'
        )
        _make_skill_md(tmp_path, content)
        findings = analyze_toon_prose_status_conflation(tmp_path)
        assert len(findings) == 1
        # The conflated inline-code span is on the 3rd line (1-based).
        assert findings[0]['line'] == 3

    def test_file_path_is_absolute(self, tmp_path):
        content = (
            'On a missing plan the script returns `status: not_found`.\n'
        )
        _make_skill_md(tmp_path, content)
        findings = analyze_toon_prose_status_conflation(tmp_path)
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
            'On failure the envelope carries `status: error` and an error code.\n'
            'A clean run reports `status: success`.\n'
        )
        _make_skill_md(tmp_path, content)
        findings = analyze_toon_prose_status_conflation(tmp_path)
        assert findings == []

    def test_empty_marketplace_root_no_findings(self, tmp_path):
        # No plan-marshall bundle directory at all.
        findings = analyze_toon_prose_status_conflation(tmp_path)
        assert findings == []
