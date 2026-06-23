# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""Tests for the ``manage-findings-invocation-invalid`` rule analyzer.

The analyzer detects three invalid invocation shapes for the
``plan-marshall:manage-findings:manage-findings`` notation:

  * Script-position underscore (``manage_findings``).
  * Invalid top-level subcommands (e.g. ``list-qgate``).
  * Invalid ``qgate`` sub-verbs (e.g. the legacy ``qgate query``).

Test layers mirror the requirements documented in the deliverable:
  (a) Kebab-vs-underscore script position — positive + negative.
  (b) ``list-qgate`` top-level subcommand — positive.
  (c) ``qgate query`` legacy sub-verb — positive.
  (d) Valid ``qgate list`` invocation — negative.
  (e) Valid ``assessment add`` invocation — negative.
  (f) Unrelated notation reference — negative (no false positive).
  (g) Finding payload shape — rule key, canonical-form hint, line number,
      file path.
"""

from pathlib import Path

from conftest import load_script_module


def _load_module(name: str, filename: str):
    return load_script_module('pm-plugin-development', 'plugin-doctor', filename, name)


_amfi = _load_module(
    '_analyze_manage_findings_invocation',
    '_analyze_manage_findings_invocation.py',
)

analyze_manage_findings_invocation = _amfi.analyze_manage_findings_invocation
scan_skill_for_manage_findings_invocation = _amfi.scan_skill_for_manage_findings_invocation
RULE_ID = _amfi.RULE_ID
VALID_TOP_LEVEL_SUBCOMMANDS = _amfi.VALID_TOP_LEVEL_SUBCOMMANDS
VALID_QGATE_SUBVERBS = _amfi.VALID_QGATE_SUBVERBS


# ---------------------------------------------------------------------------
# Fixture (a): kebab-vs-underscore script position
# ---------------------------------------------------------------------------


class TestScriptPositionUnderscore:
    """Catch snake_case in the script segment; accept kebab-case."""

    def test_underscore_script_position_is_flagged(self) -> None:
        content = (
            '# Workflow doc\n'
            'Run:\n'
            'python3 .plan/execute-script.py plan-marshall:manage-findings:manage_findings list --plan-id foo\n'
        )
        findings = analyze_manage_findings_invocation(content, '/fake/SKILL.md')
        assert len(findings) == 1
        f = findings[0]
        assert f['rule_id'] == RULE_ID
        assert f['details']['reason'] == 'script_position_underscore'
        assert f['details']['notation'] == 'plan-marshall:manage-findings:manage_findings'

    def test_kebab_script_position_is_clean(self) -> None:
        content = (
            'Run:\n'
            'python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings qgate list --plan-id foo --phase phase-5-execute\n'
        )
        findings = analyze_manage_findings_invocation(content, '/fake/SKILL.md')
        assert findings == []


# ---------------------------------------------------------------------------
# Fixture (b): list-qgate top-level subcommand
# ---------------------------------------------------------------------------


class TestListQgateTopLevelSubcommand:
    """``list-qgate`` is not a registered top-level subcommand — flag it."""

    def test_list_qgate_is_flagged(self) -> None:
        content = (
            'Step:\n'
            'python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings list-qgate --plan-id foo\n'
        )
        findings = analyze_manage_findings_invocation(content, '/fake/SKILL.md')
        assert len(findings) == 1
        f = findings[0]
        assert f['rule_id'] == RULE_ID
        assert f['details']['reason'] == 'top_level_subcommand_unknown'
        assert f['details']['subcommand'] == 'list-qgate'
        assert 'qgate list' in f['details']['canonical_hint']

    def test_list_qgate_known_subcommands_in_payload(self) -> None:
        content = (
            'python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings list-qgate\n'
        )
        findings = analyze_manage_findings_invocation(content, '/fake/SKILL.md')
        assert findings
        known = findings[0]['details']['known_subcommands']
        assert set(known) == set(VALID_TOP_LEVEL_SUBCOMMANDS)


# ---------------------------------------------------------------------------
# Fixture (c): qgate query legacy sub-verb
# ---------------------------------------------------------------------------


class TestQgateQuerySubVerb:
    """``qgate query`` is the legacy verb — flag it (canonical is ``list``)."""

    def test_qgate_query_is_flagged(self) -> None:
        content = (
            'python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings qgate query --plan-id foo\n'
        )
        findings = analyze_manage_findings_invocation(content, '/fake/SKILL.md')
        assert len(findings) == 1
        f = findings[0]
        assert f['rule_id'] == RULE_ID
        assert f['details']['reason'] == 'qgate_sub_verb_unknown'
        assert f['details']['sub_verb'] == 'query'
        assert 'qgate list' in f['details']['canonical_hint']

    def test_qgate_query_known_sub_verbs_in_payload(self) -> None:
        content = (
            'python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings qgate query\n'
        )
        findings = analyze_manage_findings_invocation(content, '/fake/SKILL.md')
        assert findings
        known = findings[0]['details']['known_sub_verbs']
        assert set(known) == set(VALID_QGATE_SUBVERBS)


# ---------------------------------------------------------------------------
# Fixture (d): valid qgate list — negative
# ---------------------------------------------------------------------------


class TestValidQgateList:
    """``qgate list`` is registered — must not produce a finding."""

    def test_qgate_list_clean(self) -> None:
        content = (
            'python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings qgate list --plan-id foo --phase phase-5-execute\n'
        )
        findings = analyze_manage_findings_invocation(content, '/fake/SKILL.md')
        assert findings == []

    def test_qgate_add_clean(self) -> None:
        content = (
            'python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings qgate add --plan-id foo --phase phase-5-execute --source qgate --type build-error --title t --detail d\n'
        )
        findings = analyze_manage_findings_invocation(content, '/fake/SKILL.md')
        assert findings == []

    def test_qgate_resolve_clean(self) -> None:
        content = (
            'python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings qgate resolve --plan-id foo --phase phase-5-execute --id 1 --resolution fixed\n'
        )
        findings = analyze_manage_findings_invocation(content, '/fake/SKILL.md')
        assert findings == []


# ---------------------------------------------------------------------------
# Fixture (e): valid assessment add — negative
# ---------------------------------------------------------------------------


class TestValidAssessmentAdd:
    """``assessment add`` is registered — must not produce a finding."""

    def test_assessment_add_clean(self) -> None:
        content = (
            'python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings assessment add --plan-id foo --file-path src/Foo.java --certainty high --confidence 90\n'
        )
        findings = analyze_manage_findings_invocation(content, '/fake/SKILL.md')
        assert findings == []

    def test_assessment_list_clean(self) -> None:
        content = (
            'python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings assessment list --plan-id foo\n'
        )
        findings = analyze_manage_findings_invocation(content, '/fake/SKILL.md')
        assert findings == []

    def test_assessment_invalid_sub_verb_flagged(self) -> None:
        # Defence-in-depth — invented sub-verbs under assessment are caught.
        content = (
            'python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings assessment promote --plan-id foo\n'
        )
        findings = analyze_manage_findings_invocation(content, '/fake/SKILL.md')
        assert len(findings) == 1
        f = findings[0]
        assert f['details']['reason'] == 'assessment_sub_verb_unknown'
        assert f['details']['sub_verb'] == 'promote'


# ---------------------------------------------------------------------------
# Fixture (f): unrelated notation reference — no false positive
# ---------------------------------------------------------------------------


class TestUnrelatedNotation:
    """Invocations against other notations must not trigger the rule."""

    def test_manage_tasks_invocation_clean(self) -> None:
        content = (
            'python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks list --plan-id foo --status pending\n'
        )
        findings = analyze_manage_findings_invocation(content, '/fake/SKILL.md')
        assert findings == []

    def test_manage_status_invocation_clean(self) -> None:
        content = (
            'python3 .plan/execute-script.py plan-marshall:manage-status:manage_status read --plan-id foo\n'
        )
        findings = analyze_manage_findings_invocation(content, '/fake/SKILL.md')
        assert findings == []

    def test_manage_logging_invocation_clean(self) -> None:
        content = (
            'python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging work --plan-id foo --level INFO --message "[STATUS] testing"\n'
        )
        findings = analyze_manage_findings_invocation(content, '/fake/SKILL.md')
        assert findings == []


# ---------------------------------------------------------------------------
# Fixture (g): finding payload shape
# ---------------------------------------------------------------------------


class TestFindingPayloadShape:
    """Every finding carries the documented schema fields."""

    def test_payload_contains_required_keys(self) -> None:
        content = (
            'python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings list-qgate --plan-id foo\n'
        )
        findings = analyze_manage_findings_invocation(content, '/path/to/SKILL.md')
        assert findings
        f = findings[0]
        for key in ('rule_id', 'type', 'file', 'line', 'severity', 'fixable', 'description', 'details'):
            assert key in f, f'finding missing required key {key}'
        assert f['rule_id'] == RULE_ID
        assert f['type'] == RULE_ID
        assert f['file'] == '/path/to/SKILL.md'
        assert isinstance(f['line'], int)
        assert f['line'] >= 1
        assert f['severity'] == 'error'
        assert f['fixable'] is False

    def test_canonical_hint_present_in_details(self) -> None:
        content = (
            'python3 .plan/execute-script.py plan-marshall:manage-findings:manage_findings list --plan-id foo\n'
        )
        findings = analyze_manage_findings_invocation(content, '/fake/SKILL.md')
        assert findings
        details = findings[0]['details']
        assert 'canonical_hint' in details
        assert 'manage-findings' in details['canonical_hint']

    def test_line_number_anchored(self) -> None:
        content = (
            '# Title\n'
            '\n'
            '\n'
            'python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings list-qgate\n'
        )
        findings = analyze_manage_findings_invocation(content, '/fake/SKILL.md')
        assert findings
        assert findings[0]['line'] == 4


# ---------------------------------------------------------------------------
# Per-skill scanner — end-to-end
# ---------------------------------------------------------------------------


class TestSkillScanner:
    """``scan_skill_for_manage_findings_invocation`` walks SKILL.md +
    standards/references/workflow/recipes and aggregates findings."""

    def test_scanner_picks_up_skill_md_invocations(self, tmp_path: Path) -> None:
        skill_dir = tmp_path / 'my-skill'
        skill_dir.mkdir()
        skill_md = skill_dir / 'SKILL.md'
        skill_md.write_text(
            '# My Skill\n'
            'python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings list-qgate\n',
            encoding='utf-8',
        )
        findings = scan_skill_for_manage_findings_invocation(skill_dir)
        assert len(findings) == 1
        assert findings[0]['file'].endswith('SKILL.md')

    def test_scanner_aggregates_subdoc_findings(self, tmp_path: Path) -> None:
        skill_dir = tmp_path / 'my-skill'
        (skill_dir / 'standards').mkdir(parents=True)
        skill_md = skill_dir / 'SKILL.md'
        skill_md.write_text('# clean\n', encoding='utf-8')
        standard = skill_dir / 'standards' / 'rules.md'
        standard.write_text(
            'python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings qgate query\n',
            encoding='utf-8',
        )
        findings = scan_skill_for_manage_findings_invocation(skill_dir)
        assert len(findings) == 1
        assert findings[0]['details']['reason'] == 'qgate_sub_verb_unknown'

    def test_scanner_returns_empty_for_clean_skill(self, tmp_path: Path) -> None:
        skill_dir = tmp_path / 'my-skill'
        skill_dir.mkdir()
        (skill_dir / 'SKILL.md').write_text('# clean\nno invocations here\n', encoding='utf-8')
        findings = scan_skill_for_manage_findings_invocation(skill_dir)
        assert findings == []

    def test_scanner_handles_missing_directory(self, tmp_path: Path) -> None:
        findings = scan_skill_for_manage_findings_invocation(tmp_path / 'nonexistent')
        assert findings == []
