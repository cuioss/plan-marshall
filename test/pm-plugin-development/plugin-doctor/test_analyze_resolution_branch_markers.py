# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""Tests for the ``resolution-branch-side-effect-undocumented`` rule analyzer.

The analyzer checks that every named branch inside a ``## Resolution`` section
of a skill's ``standards/*.md`` documents at least one observable side effect
(log, metadata, status, artifact, etc.).

Test layers:
  * Compliant branch that mentions decision.log → no finding.
  * Non-compliant branch with no side-effect keyword → finding emitted.
  * Section outside standards/ (SKILL.md) → out of scope, no finding.
  * Multiple branches in one file — mixed compliant/non-compliant.
  * Branch body spans multiple paragraphs.
  * Non-allowlist branch heading inside Resolution section → ignored.
  * No Resolution section at all → no finding.
"""

from pathlib import Path

from conftest import load_script_module


def _load_module(name: str, filename: str):
    return load_script_module('pm-plugin-development', 'plugin-doctor', filename, name)


_arbm = _load_module('_analyze_resolution_branch_markers', '_analyze_resolution_branch_markers.py')

analyze_resolution_branch_markers = _arbm.analyze_resolution_branch_markers
RULE_ID = _arbm.RULE_ID


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_standards_file(tmp_path: Path, content: str, filename: str = 'workflow.md') -> tuple[Path, Path]:
    """Create ``standards/<filename>`` under a skill directory.

    Returns ``(skill_dir, file_path)``.
    """
    skill_dir = tmp_path / 'skill'
    standards_dir = skill_dir / 'standards'
    standards_dir.mkdir(parents=True)
    md = standards_dir / filename
    md.write_text(content, encoding='utf-8')
    return skill_dir, md


# ===========================================================================
# 1. Compliant branch
# ===========================================================================


class TestCompliantBranch:
    """Branches that contain at least one side-effect keyword produce no findings."""

    def test_mentions_decision_log(self, tmp_path: Path) -> None:
        content = (
            '## Resolution\n\n'
            '### Hold\n\n'
            'Record the decision to decision.log and pause execution.\n'
        )
        skill_dir, _ = _make_standards_file(tmp_path, content)
        findings = analyze_resolution_branch_markers(skill_dir)
        assert findings == []

    def test_mentions_metadata(self, tmp_path: Path) -> None:
        content = (
            '## Resolution\n\n'
            '### Accept\n\n'
            'Write acceptance to the metadata store for audit purposes.\n'
        )
        skill_dir, _ = _make_standards_file(tmp_path, content)
        findings = analyze_resolution_branch_markers(skill_dir)
        assert findings == []

    def test_mentions_status(self, tmp_path: Path) -> None:
        content = (
            '## Resolution\n\n'
            '### Defer\n\n'
            'Update the task status to deferred and re-schedule.\n'
        )
        skill_dir, _ = _make_standards_file(tmp_path, content)
        findings = analyze_resolution_branch_markers(skill_dir)
        assert findings == []

    def test_mentions_artifact(self, tmp_path: Path) -> None:
        content = (
            '## Resolution\n\n'
            '### Split\n\n'
            'Emit an artifact containing the split plan.\n'
        )
        skill_dir, _ = _make_standards_file(tmp_path, content)
        findings = analyze_resolution_branch_markers(skill_dir)
        assert findings == []

    def test_multi_paragraph_body(self, tmp_path: Path) -> None:
        """Side-effect keyword found in later paragraph — still compliant."""
        content = (
            '## Resolution\n\n'
            '### Reject\n\n'
            'First, evaluate the rationale.\n\n'
            'Then review the context.\n\n'
            'Finally, write the rejection to work.log for the audit trail.\n'
        )
        skill_dir, _ = _make_standards_file(tmp_path, content)
        findings = analyze_resolution_branch_markers(skill_dir)
        assert findings == []


# ===========================================================================
# 2. Non-compliant branch
# ===========================================================================


class TestNonCompliantBranch:
    """Branches with no side-effect keyword trigger a finding."""

    def test_no_side_effect_keyword(self, tmp_path: Path) -> None:
        content = (
            '## Resolution\n\n'
            '### Hold\n\n'
            'Pause execution and await further instructions.\n'
        )
        skill_dir, _ = _make_standards_file(tmp_path, content)
        findings = analyze_resolution_branch_markers(skill_dir)
        assert len(findings) == 1
        f = findings[0]
        assert f['rule_id'] == RULE_ID
        assert f['branch_name'] == 'Hold'
        assert isinstance(f['line'], int)
        assert f['line'] >= 1

    def test_finding_shape(self, tmp_path: Path) -> None:
        """Each finding carries rule_id, file, line, branch_name."""
        content = (
            '## Resolution\n\n'
            '### Accept\n\n'
            'Do something unspecified.\n'
        )
        skill_dir, md_path = _make_standards_file(tmp_path, content)
        findings = analyze_resolution_branch_markers(skill_dir)
        assert findings
        f = findings[0]
        for key in ('rule_id', 'file', 'line', 'branch_name'):
            assert key in f


# ===========================================================================
# 3. Out-of-scope: SKILL.md not scanned
# ===========================================================================


class TestOutOfScope:
    """Resolution sections outside standards/*.md are not scanned."""

    def test_skill_md_not_scanned(self, tmp_path: Path) -> None:
        """Violation in SKILL.md (not inside standards/) is out of scope."""
        skill_dir = tmp_path / 'skill'
        (skill_dir / 'standards').mkdir(parents=True)
        (skill_dir / 'SKILL.md').write_text(
            '## Resolution\n\n'
            '### Hold\n\n'
            'Pause without any side-effect documentation.\n',
            encoding='utf-8',
        )
        # No standards files → no findings
        findings = analyze_resolution_branch_markers(skill_dir)
        assert findings == []


# ===========================================================================
# 4. Mixed compliance
# ===========================================================================


class TestMixedCompliance:
    """Multiple branches in one file — only non-compliant ones trigger findings."""

    def test_one_compliant_one_non_compliant(self, tmp_path: Path) -> None:
        content = (
            '## Resolution\n\n'
            '### Hold\n\n'
            'Pause — no side-effect documented.\n\n'
            '### Accept\n\n'
            'Record acceptance in decision.log for auditing.\n'
        )
        skill_dir, _ = _make_standards_file(tmp_path, content)
        findings = analyze_resolution_branch_markers(skill_dir)
        # Only "Hold" should be flagged
        assert len(findings) == 1
        assert findings[0]['branch_name'] == 'Hold'

    def test_two_non_compliant_branches(self, tmp_path: Path) -> None:
        content = (
            '## Resolution\n\n'
            '### Hold\n\n'
            'Pause execution.\n\n'
            '### Reject\n\n'
            'Discard the request.\n'
        )
        skill_dir, _ = _make_standards_file(tmp_path, content)
        findings = analyze_resolution_branch_markers(skill_dir)
        assert len(findings) == 2
        branch_names = {f['branch_name'] for f in findings}
        assert branch_names == {'Hold', 'Reject'}


# ===========================================================================
# 5. Non-allowlist headings inside Resolution section
# ===========================================================================


class TestNonAllowlistHeading:
    """Non-allowlist H3 headings inside a Resolution section are ignored."""

    def test_custom_heading_not_flagged(self, tmp_path: Path) -> None:
        """A heading like "### Background" inside Resolution is not a branch."""
        content = (
            '## Resolution\n\n'
            '### Background\n\n'
            'General context — not a decision branch.\n\n'
            '### Hold\n\n'
            'Pause with a log entry to work.log.\n'
        )
        skill_dir, _ = _make_standards_file(tmp_path, content)
        findings = analyze_resolution_branch_markers(skill_dir)
        # Background not on allowlist → ignored; Hold is compliant → no findings
        assert findings == []


# ===========================================================================
# 6. No Resolution section
# ===========================================================================


class TestNoResolutionSection:
    """Files with no ## Resolution section produce no findings."""

    def test_no_resolution_section(self, tmp_path: Path) -> None:
        content = (
            '# Overview\n\n'
            'Some text about the skill.\n\n'
            '## Workflow\n\n'
            '### Hold\n\n'
            'Pause without logging.\n'
        )
        skill_dir, _ = _make_standards_file(tmp_path, content)
        findings = analyze_resolution_branch_markers(skill_dir)
        # "Hold" is inside a "## Workflow" section, not "## Resolution"
        assert findings == []

    def test_empty_file(self, tmp_path: Path) -> None:
        skill_dir, _ = _make_standards_file(tmp_path, '')
        findings = analyze_resolution_branch_markers(skill_dir)
        assert findings == []

    def test_no_standards_directory(self, tmp_path: Path) -> None:
        skill_dir = tmp_path / 'skill-no-standards'
        skill_dir.mkdir()
        findings = analyze_resolution_branch_markers(skill_dir)
        assert findings == []


# ===========================================================================
# 7. Multiple standards files
# ===========================================================================


class TestMultipleStandardsFiles:
    """Multiple standards/*.md files are all scanned."""

    def test_finding_in_second_file(self, tmp_path: Path) -> None:
        skill_dir = tmp_path / 'skill'
        standards_dir = skill_dir / 'standards'
        standards_dir.mkdir(parents=True)
        (standards_dir / 'a.md').write_text(
            '# Section\nNo resolution here.\n', encoding='utf-8'
        )
        # Body deliberately omits the side-effect keyword set
        # (log/metadata/status/artifact/record/emit/persist/update/write).
        (standards_dir / 'b.md').write_text(
            '## Resolution\n\n### Skip\n\nSimply move on.\n',
            encoding='utf-8',
        )
        findings = analyze_resolution_branch_markers(skill_dir)
        assert len(findings) == 1
        assert findings[0]['branch_name'] == 'Skip'
