# SPDX-License-Identifier: FSL-1.1-ALv2
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
  * (d) Per-file frontmatter disable (Granularity-3) — a
        ``plugin-doctor-disable: [no-historical-prose-in-skills]`` frontmatter
        key suppresses every finding in that file; a file whose disable list
        names a different rule (or that is not in the list at all) is still
        flagged. The retired ``<!-- doctor-ignore: ... -->`` inline-marker
        mechanism is no longer honored.
  * (e) Boundary/negative cases — non-matching prose produces no findings.
  * (f) ``test_real_marketplace_has_zero_findings`` invariant.
  * (i) Suppression-aware cases — the allowlist delegates to the shipped
        default suppression config (Granularity-1) via the shared
        ``_config_layer_suppresses`` predicate. Paths registered in the config
        remain suppressed; paths not registered are still flagged.
  * (j) Inline-marker removal guard — the analyzer source references none of
        the retired ``_SUPPRESS_MARKER`` / ``_IGNORE_MARKER`` / ``doctor-ignore``
        markers.
"""

from pathlib import Path

from conftest import get_script_path, load_script_module


def _load_module(name: str, filename: str):
    return load_script_module('pm-plugin-development', 'plugin-doctor', filename, name)


_ahps = _load_module(
    '_analyze_historical_prose_in_skills',
    '_analyze_historical_prose_in_skills.py',
)

analyze_historical_prose_in_skills = _ahps.analyze_historical_prose_in_skills
RULE_ID = _ahps.RULE_ID
_is_allowlisted = _ahps._is_allowlisted
load_default_suppression_config = _ahps.load_default_suppression_config


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
# (d) Per-file frontmatter disable (Granularity-3)
# ===========================================================================


class TestFrontmatterDisable:
    """A ``plugin-doctor-disable: [no-historical-prose-in-skills]`` frontmatter
    key suppresses every finding in that file; a file not naming this rule in
    its disable list is still flagged.

    Granularity-3 (per-file frontmatter) is the highest-precedence suppression
    layer and supersedes the retired ``<!-- doctor-ignore: ... -->`` inline
    marker, which is no longer honored.
    """

    def test_inline_list_disable_suppresses_whole_file(self, tmp_path: Path) -> None:
        """An inline-list ``plugin-doctor-disable`` naming the rule suppresses all findings."""
        content = (
            '---\n'
            'name: test-skill\n'
            'plugin-doctor-disable: [no-historical-prose-in-skills]\n'
            '---\n'
            'Driving lesson: context.\n'
            'An earlier proposal was rejected.\n'
        )
        marketplace_root, _ = _make_skill_md(tmp_path, content)
        findings = analyze_historical_prose_in_skills(marketplace_root)
        assert findings == []

    def test_block_list_disable_suppresses_whole_file(self, tmp_path: Path) -> None:
        """A YAML block-list ``plugin-doctor-disable`` form is also honored."""
        content = (
            '---\n'
            'name: test-skill\n'
            'plugin-doctor-disable:\n'
            '  - no-historical-prose-in-skills\n'
            '---\n'
            'Driving lesson: context here is disabled per-file.\n'
        )
        marketplace_root, _ = _make_skill_md(tmp_path, content)
        findings = analyze_historical_prose_in_skills(marketplace_root)
        assert findings == []

    def test_disable_list_for_other_rule_does_not_suppress(self, tmp_path: Path) -> None:
        """A disable list naming a DIFFERENT rule leaves this rule's findings flagged."""
        content = (
            '---\n'
            'name: test-skill\n'
            'plugin-doctor-disable: [some-other-rule]\n'
            '---\n'
            'Driving lesson: this rule is NOT in the disable list.\n'
        )
        marketplace_root, _ = _make_skill_md(tmp_path, content)
        findings = analyze_historical_prose_in_skills(marketplace_root)
        assert len(findings) == 1
        assert findings[0]['rule_id'] == RULE_ID

    def test_no_disable_key_is_still_flagged(self, tmp_path: Path) -> None:
        """Frontmatter without ``plugin-doctor-disable`` leaves findings flagged."""
        content = (
            '---\n'
            'name: test-skill\n'
            '---\n'
            'Driving lesson: no disable key present.\n'
        )
        marketplace_root, _ = _make_skill_md(tmp_path, content)
        findings = analyze_historical_prose_in_skills(marketplace_root)
        assert len(findings) == 1

    def test_disable_does_not_bleed_across_files(self, tmp_path: Path) -> None:
        """A per-file disable in one file has no effect on a sibling file."""
        # File 1: disabled via frontmatter.
        skill_a = tmp_path / 'bundle-a' / 'skills' / 'skill-a'
        skill_a.mkdir(parents=True)
        (skill_a / 'SKILL.md').write_text(
            '---\n'
            'plugin-doctor-disable: [no-historical-prose-in-skills]\n'
            '---\n'
            'Driving lesson: suppressed in file A.\n',
            encoding='utf-8',
        )
        # File 2: no disable key — must still be flagged.
        skill_b = tmp_path / 'bundle-b' / 'skills' / 'skill-b'
        skill_b.mkdir(parents=True)
        (skill_b / 'SKILL.md').write_text(
            'Driving lesson: flagged in file B.\n', encoding='utf-8'
        )
        findings = analyze_historical_prose_in_skills(tmp_path)
        assert len(findings) == 1
        assert findings[0]['file'].endswith('bundle-b/skills/skill-b/SKILL.md')

    def test_retired_inline_marker_no_longer_suppresses(self, tmp_path: Path) -> None:
        """The retired ``<!-- doctor-ignore: historical-prose -->`` marker is ignored.

        The inline-marker mechanism was removed in favor of the config-based
        substrate; a line carrying the old marker is now flagged like any other.
        """
        content = 'Driving lesson: context. <!-- doctor-ignore: historical-prose -->\n'
        marketplace_root, _ = _make_skill_md(tmp_path, content)
        findings = analyze_historical_prose_in_skills(marketplace_root)
        assert len(findings) == 1
        assert findings[0]['rule_id'] == RULE_ID


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
# (i) Suppression-aware cases — config-driven Granularity-1 delegation
# ===========================================================================


class TestSuppressionAwareAllowlist:
    """The allowlist is no longer a hardcoded table — it delegates to the
    shipped default suppression config (Granularity-1) through the shared
    ``_config_layer_suppresses`` predicate.

    These cases pin the contract that the TASK-2 refactor preserves:

    * Every path the former hardcoded table exempted is still exempt, now
      because it is registered under ``RULE_ID`` in
      ``config/default-suppression.yml`` (the analyzer loads the *real*
      shipped config — resolved relative to the module, not ``tmp_path`` —
      so these assertions exercise the live config).
    * A path that resembles an allowlisted directory but is NOT a registered
      prefix is still flagged.
    * The ``_is_allowlisted`` delegation path returns True/False purely from
      the config, with no private list left in the analyzer.
    """

    def test_default_config_carries_rule_prefixes(self) -> None:
        """The shipped default config registers prefixes under ``RULE_ID``.

        Confirms the exemption table moved into the config rather than being
        dropped: the analyzer's rule-id key must exist with a non-empty
        prefix list.
        """
        config = load_default_suppression_config()
        assert RULE_ID in config
        assert config[RULE_ID], 'default config must carry exemption prefixes'

    def test_is_allowlisted_true_for_each_config_prefix(self) -> None:
        """``_is_allowlisted`` returns True for every prefix in the config.

        Drives the ``_is_allowlisted`` → ``_config_layer_suppresses``
        delegation directly: each registered prefix must match itself
        (``startswith`` is reflexive), proving suppression flows from the
        config and not a private list.
        """
        config = load_default_suppression_config()
        for prefix in config[RULE_ID]:
            assert _is_allowlisted(prefix, config) is True

    def test_is_allowlisted_false_for_unregistered_path(self) -> None:
        """A path not registered under ``RULE_ID`` is NOT exempt."""
        config = load_default_suppression_config()
        unregistered = 'some-bundle/skills/some-other-skill/SKILL.md'
        assert _is_allowlisted(unregistered, config) is False

    def test_previously_exempt_path_remains_suppressed(
        self, tmp_path: Path
    ) -> None:
        """A historical-prose file under an exempt prefix yields zero findings.

        Builds a file at ``manage-lessons/`` — a prefix the former hardcoded
        table exempted and the shipped config still registers — and asserts
        the analyzer suppresses the finding via the loaded default config.
        """
        config = load_default_suppression_config()
        # Pick the first registered prefix that names a skill directory so the
        # constructed path lands inside the scanned {skills} sub-tree.
        prefix = next(
            p for p in config[RULE_ID] if '/skills/' in p and p.endswith('/')
        )
        target = tmp_path / prefix / 'SKILL.md'
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            'Driving lesson: historical context lives here legitimately.\n',
            encoding='utf-8',
        )
        findings = analyze_historical_prose_in_skills(tmp_path)
        assert findings == []

    def test_path_not_in_config_is_still_flagged(self, tmp_path: Path) -> None:
        """A historical-prose file outside every exempt prefix is flagged.

        Guards against an over-broad suppression: a sibling skill that merely
        shares a bundle with an exempt skill but is NOT registered must still
        produce a finding.
        """
        # 'plan-marshall/skills/manage-lessons/' is exempt, but a sibling
        # skill 'manage-tasks' under the same bundle is not.
        skill_dir = tmp_path / 'plan-marshall' / 'skills' / 'manage-tasks'
        skill_dir.mkdir(parents=True)
        (skill_dir / 'SKILL.md').write_text(
            'Driving lesson: this sibling skill is NOT exempt.\n',
            encoding='utf-8',
        )
        findings = analyze_historical_prose_in_skills(tmp_path)
        assert len(findings) == 1
        assert findings[0]['rule_id'] == RULE_ID


# ===========================================================================
# (j) Inline-marker removal guard
# ===========================================================================


def test_analyzer_source_has_no_inline_marker_references() -> None:
    """The analyzer source references none of the retired inline markers.

    The inline-marker suppression mechanism (``_SUPPRESS_MARKER`` /
    ``_IGNORE_MARKER`` / ``doctor-ignore``) was removed in favor of the
    config-based declarative-suppression substrate. This guard reads the live
    analyzer source and asserts none of the retired tokens survive.
    """
    source = get_script_path(
        'pm-plugin-development',
        'plugin-doctor',
        '_analyze_historical_prose_in_skills.py',
    ).read_text(encoding='utf-8')
    for marker in ('_SUPPRESS_MARKER', '_IGNORE_MARKER', 'doctor-ignore'):
        assert marker not in source, (
            f'Retired inline marker {marker!r} still present in analyzer source'
        )
