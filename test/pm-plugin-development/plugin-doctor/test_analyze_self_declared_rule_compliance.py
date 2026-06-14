# ruff: noqa: I001, E402
"""Tests for the ``skill-self-declared-rule-violation`` rule analyzer.

The analyzer detects a self-referential defect: a ``SKILL.md`` that
*declares* a numbering-discipline rule in its own body (a passage
prohibiting sub-numbering / mandating flat step numbering) yet *violates*
that same rule with sub-numbered (``1a``/``3a``/``5a``-style) step headings
in that same file.

The check is self-referential, NOT a global numbering ban:

- A ``SKILL.md`` that DECLARES the rule and OBEYS it (flat headings) → no finding.
- A ``SKILL.md`` that DECLARES the rule and VIOLATES it → one finding per offending heading.
- A ``SKILL.md`` that uses sub-numbering WITHOUT declaring such a rule → NOT flagged.

Only ``SKILL.md`` is scanned — the numbering rule is a property of a skill's
workflow document. Heading-shaped lines inside YAML frontmatter and fenced
code blocks are exempt, and a per-file
``plugin-doctor-disable: [skill-self-declared-rule-violation]`` frontmatter key
suppresses every finding in that file (Granularity-3). The retired
``<!-- doctor-ignore: self-declared-rule -->`` inline marker is no longer
honored.

Scope:

1. ``marketplace/bundles/*/{skills,agents,commands}/**/SKILL.md``.
2. The project-local ``.claude/skills/**/SKILL.md`` tree (resolved relative
   to the marketplace bundles root).

Test layers:
  * (a) Positive cases — declared rule + sub-numbered heading triggers a finding.
  * (b) No-violation cases — declares-and-obeys; no declaration; flat headings.
  * (c) Exemption cases — frontmatter, fenced code blocks, per-file disable.
  * (d) Detection-shape cases — heading forms and declaration-phrase variants.
  * (e) Scope cases — agents/commands dirs, non-SKILL.md, out-of-scope paths.
  * (f) Project-local ``.claude/skills/**`` cases.
  * (g) Finding-shape case.
  * (h) Inline-marker removal guard — the analyzer source references none of
        the retired ``_SUPPRESS_MARKER`` / ``_IGNORE_MARKER`` / ``doctor-ignore``
        markers.
"""

from pathlib import Path

from conftest import get_script_path, load_script_module


def _load_module(name: str, filename: str):
    return load_script_module('pm-plugin-development', 'plugin-doctor', filename, name)


_asdrc = _load_module(
    '_analyze_self_declared_rule_compliance',
    '_analyze_self_declared_rule_compliance.py',
)

analyze_self_declared_rule_compliance = _asdrc.analyze_self_declared_rule_compliance
RULE_ID = _asdrc.RULE_ID
RULE_NAME = _asdrc.RULE_NAME
FINDING_TYPE = _asdrc.FINDING_TYPE


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# A body passage that declares the flat-numbering / no-sub-numbering rule.
_DECLARATION = (
    'Skill workflows must use flat-numbering for steps — sub-numbering like '
    '`2b` is prohibited.\n'
)


def _make_skill_md(
    tmp_path: Path,
    content: str,
    bundle: str = 'test-bundle',
    skill: str = 'test-skill',
    sub: str = 'skills',
    filename: str = 'SKILL.md',
) -> tuple[Path, Path]:
    """Create a ``{bundle}/{sub}/{skill}/{filename}`` under ``tmp_path``.

    Mirrors the layout scanned by ``_skill_source_targets``:
    ``marketplace_root/*/{skills,agents,commands}/**/SKILL.md``.

    Returns ``(marketplace_root, md_path)``.
    """
    comp_dir = tmp_path / bundle / sub / skill
    comp_dir.mkdir(parents=True)
    md = comp_dir / filename
    md.write_text(content, encoding='utf-8')
    return tmp_path, md


def _make_claude_skill_md(
    tmp_path: Path,
    content: str,
    skill: str = 'audit-skill',
    filename: str = 'SKILL.md',
) -> tuple[Path, Path]:
    """Create a project-local ``.claude/skills/{skill}/{filename}`` + bundles root.

    The analyzer resolves the ``.claude/skills`` tree as
    ``marketplace_root.parent.parent / '.claude' / 'skills'``. To exercise
    that resolution the marketplace bundles root must live at
    ``tmp_path/marketplace/bundles`` so two levels up lands on ``tmp_path``,
    where ``.claude/skills`` is created.

    Returns ``(marketplace_root, claude_file_path)``.
    """
    bundles_root = tmp_path / 'marketplace' / 'bundles'
    bundles_root.mkdir(parents=True)
    claude_dir = tmp_path / '.claude' / 'skills' / skill
    claude_dir.mkdir(parents=True)
    target = claude_dir / filename
    target.write_text(content, encoding='utf-8')
    return bundles_root, target


def _doc(body: str, declaration: str = _DECLARATION) -> str:
    """Compose a SKILL.md with frontmatter, the rule declaration, and a body.

    The ``declaration`` defaults to the flat-numbering rule passage; pass an
    empty string to build a document that declares no numbering rule.
    """
    return f'---\nname: test-skill\n---\n{declaration}{body}'


def _doc_disable(body: str, disable: str, declaration: str = _DECLARATION) -> str:
    """Compose a SKILL.md carrying a ``plugin-doctor-disable`` frontmatter key.

    ``disable`` is the raw value placed after ``plugin-doctor-disable:`` (inline
    list form, e.g. ``[skill-self-declared-rule-violation]``).
    """
    return (
        f'---\nname: test-skill\n'
        f'plugin-doctor-disable: {disable}\n'
        f'---\n{declaration}{body}'
    )


# ===========================================================================
# (a) Positive cases — declared rule + sub-numbered heading
# ===========================================================================


class TestPositiveViolation:
    """A declared numbering rule + a sub-numbered heading is flagged."""

    def test_declares_rule_and_violates_with_step_heading(self, tmp_path: Path) -> None:
        """A `### Step 1a` heading in a rule-declaring file drifts."""
        content = _doc('### Step 1a Initialize\n')
        marketplace_root, _ = _make_skill_md(tmp_path, content)
        findings = analyze_self_declared_rule_compliance(marketplace_root)
        assert len(findings) == 1
        assert findings[0]['rule_id'] == RULE_ID
        assert 'Step 1a' in findings[0]['snippet']

    def test_declares_rule_and_violates_with_bare_label(self, tmp_path: Path) -> None:
        """A bare `#### 3b` label heading is also a violation."""
        content = _doc('#### 3b Run the secondary check\n')
        marketplace_root, _ = _make_skill_md(tmp_path, content)
        findings = analyze_self_declared_rule_compliance(marketplace_root)
        assert len(findings) == 1
        assert '3b' in findings[0]['snippet']

    def test_multiple_violating_headings_produce_multiple_findings(
        self, tmp_path: Path
    ) -> None:
        """Two sub-numbered headings yield two findings."""
        content = _doc('### Step 1a First\n\nbody\n\n### Step 5a Second\n')
        marketplace_root, _ = _make_skill_md(tmp_path, content)
        findings = analyze_self_declared_rule_compliance(marketplace_root)
        assert len(findings) == 2
        snippets = sorted(f['snippet'] for f in findings)
        assert 'Step 1a' in snippets[0]
        assert 'Step 5a' in snippets[1]

    def test_finding_line_is_one_based_absolute(self, tmp_path: Path) -> None:
        """The reported line is the 1-based absolute position in the file."""
        # Lines: 1 '---', 2 name, 3 '---', 4 declaration, 5 violating heading.
        content = _doc('### Step 2a Configure\n')
        marketplace_root, _ = _make_skill_md(tmp_path, content)
        findings = analyze_self_declared_rule_compliance(marketplace_root)
        assert len(findings) == 1
        assert findings[0]['line'] == 5

    def test_multi_digit_step_label_is_detected(self, tmp_path: Path) -> None:
        """A two-digit `## Step 12a` label is a violation."""
        content = _doc('## Step 12a Late step\n')
        marketplace_root, _ = _make_skill_md(tmp_path, content)
        findings = analyze_self_declared_rule_compliance(marketplace_root)
        assert len(findings) == 1


# ===========================================================================
# (b) No-violation cases — clean / out-of-rule-scope
# ===========================================================================


class TestNoViolation:
    """Declares-and-obeys, no declaration, and flat headings are clean."""

    def test_declares_rule_and_obeys_flat_headings(self, tmp_path: Path) -> None:
        """A rule-declaring file with flat (`### Step 1`) headings is clean."""
        content = _doc('### Step 1 Initialize\n\nbody\n\n### Step 2 Verify\n')
        marketplace_root, _ = _make_skill_md(tmp_path, content)
        findings = analyze_self_declared_rule_compliance(marketplace_root)
        assert findings == []

    def test_sub_numbering_without_declaration_is_not_flagged(
        self, tmp_path: Path
    ) -> None:
        """Sub-numbering WITHOUT a declared rule is not flagged (self-referential)."""
        content = _doc('### Step 1a Initialize\n', declaration='')
        marketplace_root, _ = _make_skill_md(tmp_path, content)
        findings = analyze_self_declared_rule_compliance(marketplace_root)
        assert findings == []

    def test_no_headings_at_all_is_clean(self, tmp_path: Path) -> None:
        """A rule-declaring file with no step headings has nothing to violate."""
        content = _doc('Just prose with no step headings whatsoever.\n')
        marketplace_root, _ = _make_skill_md(tmp_path, content)
        findings = analyze_self_declared_rule_compliance(marketplace_root)
        assert findings == []

    def test_flat_heading_with_trailing_letter_word_is_not_a_violation(
        self, tmp_path: Path
    ) -> None:
        """`### Step 1 Apply` (digit then space then word) is flat, not sub-numbered."""
        content = _doc('### Step 1 Apply the migration\n')
        marketplace_root, _ = _make_skill_md(tmp_path, content)
        findings = analyze_self_declared_rule_compliance(marketplace_root)
        assert findings == []


# ===========================================================================
# (c) Exemption cases — frontmatter, fenced blocks, suppression marker
# ===========================================================================


class TestExemptions:
    """Frontmatter, fenced blocks, and per-file frontmatter disable exempt matches."""

    def test_violating_heading_inside_fenced_block_is_exempt(
        self, tmp_path: Path
    ) -> None:
        """A `### Step 1a` line inside a fence is an example, not a live heading."""
        content = _doc('```markdown\n### Step 1a example inside a fence\n```\n')
        marketplace_root, _ = _make_skill_md(tmp_path, content)
        findings = analyze_self_declared_rule_compliance(marketplace_root)
        assert findings == []

    def test_declaration_only_inside_fence_does_not_arm_rule(
        self, tmp_path: Path
    ) -> None:
        """A declaration phrase only inside a fence is not an authored rule.

        With the declaration confined to a fenced example, the file does not
        DECLARE the rule, so a live sub-numbered heading is not flagged.
        """
        content = (
            '---\nname: test-skill\n---\n'
            '```text\nflat-numbering is required here in this example\n```\n'
            '### Step 1a Initialize\n'
        )
        marketplace_root, _ = _make_skill_md(tmp_path, content)
        findings = analyze_self_declared_rule_compliance(marketplace_root)
        assert findings == []

    def test_frontmatter_disable_suppresses_whole_file(self, tmp_path: Path) -> None:
        """A ``plugin-doctor-disable`` naming the rule suppresses every violation."""
        content = _doc_disable(
            '### Step 1a First\n\nbody\n\n### Step 5a Second\n',
            '[skill-self-declared-rule-violation]',
        )
        marketplace_root, _ = _make_skill_md(tmp_path, content)
        findings = analyze_self_declared_rule_compliance(marketplace_root)
        assert findings == []

    def test_frontmatter_disable_block_list_form(self, tmp_path: Path) -> None:
        """The YAML block-list ``plugin-doctor-disable`` form is honored."""
        content = (
            '---\n'
            'name: test-skill\n'
            'plugin-doctor-disable:\n'
            '  - skill-self-declared-rule-violation\n'
            '---\n'
            f'{_DECLARATION}### Step 1a Initialize\n'
        )
        marketplace_root, _ = _make_skill_md(tmp_path, content)
        findings = analyze_self_declared_rule_compliance(marketplace_root)
        assert findings == []

    def test_frontmatter_disable_for_other_rule_does_not_suppress(
        self, tmp_path: Path
    ) -> None:
        """A disable list naming a DIFFERENT rule leaves the violation flagged."""
        content = _doc_disable(
            '### Step 1a Initialize\n',
            '[some-other-rule]',
        )
        marketplace_root, _ = _make_skill_md(tmp_path, content)
        findings = analyze_self_declared_rule_compliance(marketplace_root)
        assert len(findings) == 1
        assert 'Step 1a' in findings[0]['snippet']

    def test_retired_inline_marker_no_longer_suppresses(self, tmp_path: Path) -> None:
        """The retired ``<!-- doctor-ignore: self-declared-rule -->`` marker is ignored."""
        content = _doc(
            '### Step 1a Initialize <!-- doctor-ignore: self-declared-rule -->\n'
        )
        marketplace_root, _ = _make_skill_md(tmp_path, content)
        findings = analyze_self_declared_rule_compliance(marketplace_root)
        assert len(findings) == 1
        assert 'Step 1a' in findings[0]['snippet']


# ===========================================================================
# (d) Detection-shape cases — heading forms and declaration variants
# ===========================================================================


class TestDetectionShape:
    """Heading-shape and declaration-phrase variants."""

    def test_no_sub_numbering_phrase_arms_the_rule(self, tmp_path: Path) -> None:
        """The `no sub-numbering` declaration phrase arms the rule."""
        content = _doc(
            '### Step 1a Initialize\n',
            declaration='Steps follow a flat sequence with no sub-numbering.\n',
        )
        marketplace_root, _ = _make_skill_md(tmp_path, content)
        findings = analyze_self_declared_rule_compliance(marketplace_root)
        assert len(findings) == 1

    def test_h2_heading_is_in_range(self, tmp_path: Path) -> None:
        """A `## Step 1a` (h2) heading is detected."""
        content = _doc('## Step 1a Top-level step\n')
        marketplace_root, _ = _make_skill_md(tmp_path, content)
        findings = analyze_self_declared_rule_compliance(marketplace_root)
        assert len(findings) == 1

    def test_h1_heading_is_out_of_range(self, tmp_path: Path) -> None:
        """A `# Step 1a` (h1) heading is below the `##`..`####` range and ignored."""
        content = _doc('# Step 1a Document title\n')
        marketplace_root, _ = _make_skill_md(tmp_path, content)
        findings = analyze_self_declared_rule_compliance(marketplace_root)
        assert findings == []

    def test_prose_mention_of_sub_numbered_label_is_not_a_heading(
        self, tmp_path: Path
    ) -> None:
        """A `2b`-shaped token in prose (not a heading) is not flagged."""
        content = _doc('See step 1a above for the prerequisite detail.\n')
        marketplace_root, _ = _make_skill_md(tmp_path, content)
        findings = analyze_self_declared_rule_compliance(marketplace_root)
        assert findings == []


# ===========================================================================
# (e) Scope cases — agents/commands dirs, non-SKILL.md, out-of-scope paths
# ===========================================================================


class TestScope:
    """The bundles scope spans skills/agents/commands SKILL.md only."""

    def test_agents_directory_is_scanned(self, tmp_path: Path) -> None:
        """A `SKILL.md` under `{bundle}/agents/` is in scope."""
        content = _doc('### Step 1a Initialize\n')
        marketplace_root, _ = _make_skill_md(tmp_path, content, sub='agents')
        findings = analyze_self_declared_rule_compliance(marketplace_root)
        assert len(findings) == 1

    def test_commands_directory_is_scanned(self, tmp_path: Path) -> None:
        """A `SKILL.md` under `{bundle}/commands/` is in scope."""
        content = _doc('### Step 1a Initialize\n')
        marketplace_root, _ = _make_skill_md(tmp_path, content, sub='commands')
        findings = analyze_self_declared_rule_compliance(marketplace_root)
        assert len(findings) == 1

    def test_non_skill_md_file_is_not_scanned(self, tmp_path: Path) -> None:
        """A non-`SKILL.md` markdown file is out of scope (only SKILL.md scans)."""
        content = _doc('### Step 1a Initialize\n')
        marketplace_root, _ = _make_skill_md(
            tmp_path, content, filename='standards.md'
        )
        findings = analyze_self_declared_rule_compliance(marketplace_root)
        assert findings == []

    def test_out_of_scope_path_not_scanned(self, tmp_path: Path) -> None:
        """A `SKILL.md` under the bundle root but not in a scanned sub is ignored."""
        bundle_dir = tmp_path / 'some-bundle'
        bundle_dir.mkdir(parents=True)
        (bundle_dir / 'SKILL.md').write_text(
            _doc('### Step 1a Initialize\n'), encoding='utf-8'
        )
        findings = analyze_self_declared_rule_compliance(tmp_path)
        assert findings == []


# ===========================================================================
# (f) Project-local .claude/skills/** cases
# ===========================================================================


class TestClaudeSkillsTree:
    """The project-local ``.claude/skills/**`` tree is scanned too."""

    def test_claude_skill_violation_triggers_finding(self, tmp_path: Path) -> None:
        """A violating SKILL.md under ``.claude/skills/`` is flagged."""
        content = _doc('### Step 1a Initialize\n')
        marketplace_root, target = _make_claude_skill_md(tmp_path, content)
        findings = analyze_self_declared_rule_compliance(marketplace_root)
        assert len(findings) == 1
        assert findings[0]['file'] == str(target)

    def test_missing_claude_skills_tree_is_tolerated(self, tmp_path: Path) -> None:
        """When no ``.claude/skills`` tree exists, only the bundles tree scans."""
        content = _doc('### Step 1a Initialize\n')
        marketplace_root, _ = _make_skill_md(tmp_path, content)
        findings = analyze_self_declared_rule_compliance(marketplace_root)
        assert len(findings) == 1

    def test_claude_and_bundles_findings_combine(self, tmp_path: Path) -> None:
        """Findings from the bundles tree and ``.claude/skills`` combine."""
        bundles_root = tmp_path / 'marketplace' / 'bundles'
        skill_dir = bundles_root / 'test-bundle' / 'skills' / 'test-skill'
        skill_dir.mkdir(parents=True)
        skill_dir.joinpath('SKILL.md').write_text(
            _doc('### Step 1a Bundle step\n'), encoding='utf-8'
        )
        claude_dir = tmp_path / '.claude' / 'skills' / 'audit-skill'
        claude_dir.mkdir(parents=True)
        claude_dir.joinpath('SKILL.md').write_text(
            _doc('### Step 3a Project-local step\n'), encoding='utf-8'
        )
        findings = analyze_self_declared_rule_compliance(bundles_root)
        assert len(findings) == 2


# ===========================================================================
# (g) Finding-shape case
# ===========================================================================


def test_finding_shape(tmp_path: Path) -> None:
    """A finding carries the documented shape fields."""
    content = _doc('### Step 1a Initialize\n')
    marketplace_root, md_path = _make_skill_md(tmp_path, content)
    findings = analyze_self_declared_rule_compliance(marketplace_root)
    assert len(findings) == 1
    f = findings[0]
    assert f['rule_id'] == RULE_ID
    assert f['type'] == FINDING_TYPE
    assert f['rule'] == RULE_NAME
    assert f['file'] == str(md_path)
    assert isinstance(f['line'], int) and f['line'] >= 1
    assert f['severity'] == 'warning'
    assert f['fixable'] is False
    assert 'Step 1a' in f['snippet']
    assert 'description' in f and f['description']


# ===========================================================================
# (h) Inline-marker removal guard
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
        '_analyze_self_declared_rule_compliance.py',
    ).read_text(encoding='utf-8')
    for marker in ('_SUPPRESS_MARKER', '_IGNORE_MARKER', 'doctor-ignore'):
        assert marker not in source, (
            f'Retired inline marker {marker!r} still present in analyzer source'
        )
