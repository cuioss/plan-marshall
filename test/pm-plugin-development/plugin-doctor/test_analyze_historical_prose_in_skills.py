# ruff: noqa: I001, E402
"""Tests for the ``no-historical-prose-in-skills`` rule analyzer.

The analyzer detects historical and transitional narrative patterns inside
marketplace bundle skill markdown files. Seven pattern families are checked:

1. driving_lesson_prefix — ``Driving lesson:`` bullet/inline annotation.
2. back_reference_prefix — ``Back-reference:`` or ``Back-reference—``.
3. earlier_proposal — "an earlier proposal", "the earlier approach", etc.
4. historical_activation — "activated end-to-end by lesson", "introduced by plan".
5. seed_failure_observation — "seed failure", "seed observation", "seed gap".
6. plan_task_authorship — "added in TASK-NNN of plan", "added by deliverable N".
7. guard_introduction — "guard introduced in", "rule introduced in", etc.

Structural exemptions mirror those of the lesson-id rule: allowlisted file
paths (manage-lessons/**, phase-6-finalize/workflow/lessons-*.md,
phase-6-finalize/standards/lessons-*.md, plan-retrospective/**,
plugin-doctor/references/rule-provenance.md, plugin-doctor/references/rule-catalog.md,
plan-doctor/standards/**), plus per-line exemptions for YAML frontmatter,
fenced code blocks, Source: provenance lines, and inline-code spans.

Test layers:
  * (a) Positive cases — each pattern family triggers a finding.
  * (b) Allowlist cases — files inside allowlisted paths produce zero findings.
  * (c) Skip-context cases — patterns inside fenced blocks, frontmatter, etc.
        produce no findings.
  * (d) Suppression marker cases.
  * (e) Boundary/negative cases — non-matching prose produces no findings.
  * (f) ``test_real_marketplace_has_zero_findings`` invariant.
"""

from pathlib import Path

from conftest import load_script_module

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent


def _load_module(name: str, filename: str):
    return load_script_module('pm-plugin-development', 'plugin-doctor', filename, name)


_ahps = _load_module(
    '_analyze_historical_prose_in_skills',
    '_analyze_historical_prose_in_skills.py',
)

analyze_historical_prose_in_skills = _ahps.analyze_historical_prose_in_skills
RULE_ID = _ahps.RULE_ID

MARKETPLACE_BUNDLES = PROJECT_ROOT / 'marketplace' / 'bundles'


def _make_skill_md(
    tmp_path: Path,
    content: str,
    bundle: str = 'test-bundle',
    skill: str = 'test-skill',
    filename: str = 'SKILL.md',
) -> tuple[Path, Path]:
    """Create a ``{bundle}/skills/{skill}/{filename}`` under ``tmp_path``."""
    skill_dir = tmp_path / bundle / 'skills' / skill
    skill_dir.mkdir(parents=True)
    md = skill_dir / filename
    md.write_text(content, encoding='utf-8')
    return tmp_path, md


# ===========================================================================
# (a) Positive cases — each pattern family triggers a finding
# ===========================================================================


class TestPositiveDetection:
    """Each historical-prose pattern family must be flagged."""

    def test_driving_lesson_prefix_triggers_finding(self, tmp_path: Path) -> None:
        """'Driving lesson:' annotation is a finding."""
        content = '- Driving lesson: `2026-04-30-23-001` (scope expanded silently).\n'
        marketplace_root, _ = _make_skill_md(tmp_path, content)
        findings = analyze_historical_prose_in_skills(marketplace_root)
        assert len(findings) == 1
        assert findings[0]['rule_id'] == RULE_ID
        assert findings[0]['pattern_family'] == 'driving_lesson_prefix'

    def test_driving_lesson_inline_triggers_finding(self, tmp_path: Path) -> None:
        """Inline 'driving lesson:' is also detected."""
        content = 'Driving lesson: the recurring failure mode documented here.\n'
        marketplace_root, _ = _make_skill_md(tmp_path, content)
        findings = analyze_historical_prose_in_skills(marketplace_root)
        assert len(findings) == 1
        assert findings[0]['pattern_family'] == 'driving_lesson_prefix'

    def test_back_reference_prefix_triggers_finding(self, tmp_path: Path) -> None:
        """'Back-reference:' annotation is a finding."""
        content = 'd. **Back-reference**: this rule originates from lesson `2026-05-18-10-001`.\n'
        marketplace_root, _ = _make_skill_md(tmp_path, content)
        findings = analyze_historical_prose_in_skills(marketplace_root)
        assert any(f['pattern_family'] == 'back_reference_prefix' for f in findings)

    def test_earlier_proposal_triggers_finding(self, tmp_path: Path) -> None:
        """'An earlier proposal' is a finding."""
        content = 'An earlier proposal suggested intercepting tool calls via a hook.\n'
        marketplace_root, _ = _make_skill_md(tmp_path, content)
        findings = analyze_historical_prose_in_skills(marketplace_root)
        assert len(findings) == 1
        assert findings[0]['pattern_family'] == 'earlier_proposal'

    def test_earlier_approach_triggers_finding(self, tmp_path: Path) -> None:
        """'the earlier approach' is a finding."""
        content = 'That approach was rejected because the earlier approach was brittle.\n'
        marketplace_root, _ = _make_skill_md(tmp_path, content)
        findings = analyze_historical_prose_in_skills(marketplace_root)
        assert any(f['pattern_family'] == 'earlier_proposal' for f in findings)

    def test_historical_activation_triggers_finding(self, tmp_path: Path) -> None:
        """'activated end-to-end by lesson' is a finding."""
        content = 'The contract was activated end-to-end by lesson `2026-05-05-11-001`.\n'
        marketplace_root, _ = _make_skill_md(tmp_path, content)
        findings = analyze_historical_prose_in_skills(marketplace_root)
        assert any(f['pattern_family'] == 'historical_activation' for f in findings)

    def test_seed_failure_triggers_finding(self, tmp_path: Path) -> None:
        """'seed failure' is a finding."""
        content = 'The seed failure (`lesson 2026-05-24-22-001`) is the canonical instance.\n'
        marketplace_root, _ = _make_skill_md(tmp_path, content)
        findings = analyze_historical_prose_in_skills(marketplace_root)
        assert any(f['pattern_family'] == 'seed_failure_observation' for f in findings)

    def test_seed_observation_triggers_finding(self, tmp_path: Path) -> None:
        """'seed observation' is a finding."""
        content = 'See lesson for the seed observation (PR #456 — orchestrator dispatched).\n'
        marketplace_root, _ = _make_skill_md(tmp_path, content)
        findings = analyze_historical_prose_in_skills(marketplace_root)
        assert any(f['pattern_family'] == 'seed_failure_observation' for f in findings)

    def test_plan_task_authorship_triggers_finding(self, tmp_path: Path) -> None:
        """'added in TASK-007 of plan' is a finding."""
        content = 'Two registry rows (added in TASK-007 of plan `lesson-2026-05-05-11-001`).\n'
        marketplace_root, _ = _make_skill_md(tmp_path, content)
        findings = analyze_historical_prose_in_skills(marketplace_root)
        assert any(f['pattern_family'] == 'plan_task_authorship' for f in findings)

    def test_guard_introduction_triggers_finding(self, tmp_path: Path) -> None:
        """'guard introduced in' is a finding."""
        content = 'guard introduced in `manage-tasks finalize-step`.\n'
        marketplace_root, _ = _make_skill_md(tmp_path, content)
        findings = analyze_historical_prose_in_skills(marketplace_root)
        assert any(f['pattern_family'] == 'guard_introduction' for f in findings)

    def test_finding_shape(self, tmp_path: Path) -> None:
        """Finding carries the expected shape fields."""
        content = '- Driving lesson: see context.\n'
        marketplace_root, md_path = _make_skill_md(tmp_path, content)
        findings = analyze_historical_prose_in_skills(marketplace_root)
        assert len(findings) == 1
        f = findings[0]
        assert f['rule_id'] == RULE_ID
        assert f['type'] == 'historical_prose_in_skills'
        assert f['rule'] == 'analyze_historical_prose_in_skills'
        assert f['file'] == str(md_path)
        assert isinstance(f['line'], int) and f['line'] >= 1
        assert f['severity'] == 'warning'
        assert f['fixable'] is False
        assert 'snippet' in f
        assert 'description' in f
        assert 'pattern_family' in f


# ===========================================================================
# (b) Allowlist cases
# ===========================================================================


class TestAllowlistExemption:
    """Files under allowlisted paths produce zero findings."""

    def test_manage_lessons_is_exempt(self, tmp_path: Path) -> None:
        content = 'Driving lesson: the lesson-handling skill uses historical context.\n'
        skill_dir = tmp_path / 'plan-marshall' / 'skills' / 'manage-lessons'
        skill_dir.mkdir(parents=True)
        (skill_dir / 'SKILL.md').write_text(content, encoding='utf-8')
        findings = analyze_historical_prose_in_skills(tmp_path)
        assert findings == []

    def test_plan_retrospective_is_exempt(self, tmp_path: Path) -> None:
        content = 'An earlier proposal suggested this approach.\n'
        skill_dir = tmp_path / 'plan-marshall' / 'skills' / 'plan-retrospective'
        skill_dir.mkdir(parents=True)
        (skill_dir / 'SKILL.md').write_text(content, encoding='utf-8')
        findings = analyze_historical_prose_in_skills(tmp_path)
        assert findings == []

    def test_plugin_doctor_rule_provenance_is_exempt(self, tmp_path: Path) -> None:
        content = 'Driving lesson: `2026-04-29-23-002` — recurrence of stale flags.\n'
        ref_dir = (
            tmp_path
            / 'pm-plugin-development'
            / 'skills'
            / 'plugin-doctor'
            / 'references'
        )
        ref_dir.mkdir(parents=True)
        (ref_dir / 'rule-provenance.md').write_text(content, encoding='utf-8')
        findings = analyze_historical_prose_in_skills(tmp_path)
        assert findings == []

    def test_plugin_doctor_rule_catalog_is_exempt(self, tmp_path: Path) -> None:
        content = 'Driving lesson: rule catalog describes rule context.\n'
        ref_dir = (
            tmp_path
            / 'pm-plugin-development'
            / 'skills'
            / 'plugin-doctor'
            / 'references'
        )
        ref_dir.mkdir(parents=True)
        (ref_dir / 'rule-catalog.md').write_text(content, encoding='utf-8')
        findings = analyze_historical_prose_in_skills(tmp_path)
        assert findings == []

    def test_plan_doctor_standards_is_exempt(self, tmp_path: Path) -> None:
        content = 'Back-reference: check-lesson-id-references standard.\n'
        std_dir = (
            tmp_path / 'plan-marshall' / 'skills' / 'plan-doctor' / 'standards'
        )
        std_dir.mkdir(parents=True)
        (std_dir / 'check-lesson-id-references.md').write_text(content, encoding='utf-8')
        findings = analyze_historical_prose_in_skills(tmp_path)
        assert findings == []


# ===========================================================================
# (c) Skip-context cases
# ===========================================================================


class TestSkipContextExemption:
    """Historical patterns in structured contexts produce no findings."""

    def test_yaml_frontmatter_is_exempt(self, tmp_path: Path) -> None:
        content = (
            '---\n'
            'name: test\n'
            'back-reference: some-plan\n'
            '---\n'
            'Normal body content.\n'
        )
        marketplace_root, _ = _make_skill_md(tmp_path, content)
        findings = analyze_historical_prose_in_skills(marketplace_root)
        assert findings == []

    def test_fenced_code_block_is_exempt(self, tmp_path: Path) -> None:
        content = (
            '```bash\n'
            '# Driving lesson: this is inside a code block\n'
            '```\n'
        )
        marketplace_root, _ = _make_skill_md(tmp_path, content)
        findings = analyze_historical_prose_in_skills(marketplace_root)
        assert findings == []

    def test_source_line_is_exempt(self, tmp_path: Path) -> None:
        content = 'Source: Driving lesson `2026-04-29-23-002` provenance.\n'
        marketplace_root, _ = _make_skill_md(tmp_path, content)
        findings = analyze_historical_prose_in_skills(marketplace_root)
        assert findings == []


# ===========================================================================
# (d) Suppression marker cases
# ===========================================================================


class TestSuppressionMarker:
    """The ``<!-- doctor-ignore: historical-prose -->`` marker suppresses findings."""

    def test_same_line_suppression(self, tmp_path: Path) -> None:
        content = 'Driving lesson: context. <!-- doctor-ignore: historical-prose -->\n'
        marketplace_root, _ = _make_skill_md(tmp_path, content)
        findings = analyze_historical_prose_in_skills(marketplace_root)
        assert findings == []

    def test_preceding_line_suppression(self, tmp_path: Path) -> None:
        content = (
            '<!-- doctor-ignore: historical-prose -->\n'
            'Driving lesson: this should be suppressed.\n'
        )
        marketplace_root, _ = _make_skill_md(tmp_path, content)
        findings = analyze_historical_prose_in_skills(marketplace_root)
        assert findings == []

    def test_marker_only_suppresses_marked_line(self, tmp_path: Path) -> None:
        content = (
            'Driving lesson: suppressed. <!-- doctor-ignore: historical-prose -->\n'
            'An earlier proposal was not suppressed.\n'
        )
        marketplace_root, _ = _make_skill_md(tmp_path, content)
        findings = analyze_historical_prose_in_skills(marketplace_root)
        assert len(findings) == 1
        assert findings[0]['line'] == 2


# ===========================================================================
# (e) Boundary / negative cases
# ===========================================================================


class TestBoundaryCases:
    """Non-matching prose and out-of-scope paths produce no findings."""

    def test_clean_present_tense_prose_no_finding(self, tmp_path: Path) -> None:
        content = (
            'Check sibling directories when scope changes touch a shared symbol.\n'
            'Do not reuse prose across skills — extract to a central reference.\n'
        )
        marketplace_root, _ = _make_skill_md(tmp_path, content)
        findings = analyze_historical_prose_in_skills(marketplace_root)
        assert findings == []

    def test_out_of_scope_readme_not_scanned(self, tmp_path: Path) -> None:
        bundle_dir = tmp_path / 'some-bundle'
        bundle_dir.mkdir(parents=True)
        (bundle_dir / 'README.md').write_text(
            'Driving lesson: not in scope.\n', encoding='utf-8'
        )
        findings = analyze_historical_prose_in_skills(tmp_path)
        assert findings == []

    def test_word_driving_alone_no_finding(self, tmp_path: Path) -> None:
        """The word 'driving' alone without 'lesson:' is not flagged."""
        content = 'The driving constraint is isolation.\n'
        marketplace_root, _ = _make_skill_md(tmp_path, content)
        findings = analyze_historical_prose_in_skills(marketplace_root)
        assert findings == []


# ===========================================================================
# (f) Real-marketplace zero-findings invariant
# ===========================================================================


class TestRealMarketplace:
    """The cleaned marketplace tree produces zero findings."""

    def test_real_marketplace_has_zero_findings(self) -> None:
        """Invariant: the real ``marketplace/bundles/`` tree is clean."""
        if not MARKETPLACE_BUNDLES.is_dir():
            return
        findings = analyze_historical_prose_in_skills(MARKETPLACE_BUNDLES)
        assert findings == [], (
            f'Real marketplace contains {len(findings)} unexpected '
            'historical-prose-in-skills findings: '
            + ', '.join(
                f"{f['file']}:{f['line']} ({f['snippet']!r}, family={f['pattern_family']})"
                for f in findings[:5]
            )
        )
