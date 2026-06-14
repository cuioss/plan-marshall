# ruff: noqa: I001, E402
"""Tests for the ``allowed-tools-body-drift`` rule analyzer.

The analyzer detects a *drift* between a component's declared
``allowed-tools`` / ``tools`` frontmatter list and the tools its workflow
body actually invokes. The drift is one-directional: a tool the body
invokes that is absent from a declared, non-empty tool list is flagged.

What is NOT flagged (consistency check, not schema prohibition):

- A component that omits ``allowed-tools`` / ``tools`` entirely (the
  "inherit all tools" default).
- A declared list that COVERS every body-invoked tool.
- A declared tool the body never invokes (unused declarations are a
  separate, out-of-scope concern — the rule is one-directional).

Body-invocation detection only matches the Claude Code tool vocabulary
(``Read``, ``Write``, ``Edit``, ``Glob``, ``Grep``, ``Bash``,
``AskUserQuestion``, ``Skill``, ``Task``, ``WebFetch``) in directive shape:
``{ToolName}:`` at a line start (with optional list bullet) or the
``Tool: {ToolName}`` prefixed form. Fenced code blocks exempt matches, and a
per-file ``plugin-doctor-disable: [allowed-tools-body-drift]`` frontmatter key
suppresses every finding in that file (Granularity-3). The retired
``<!-- doctor-ignore: allowed-tools-drift -->`` inline marker is no longer
honored.

Scope:

1. ``marketplace/bundles/*/{skills,agents,commands}/**/*.md``.
2. The project-local ``.claude/skills/**/*.md`` tree (resolved relative to
   the marketplace bundles root).

Test layers:
  * (a) Positive cases — a body-invoked tool absent from a declared,
        non-empty list triggers a finding (both declaration forms).
  * (b) No-drift cases — declared list covers every invoked tool; missing
        declaration; empty declaration; unused declaration (one-directional).
  * (c) Exemption cases — fenced code blocks and per-file frontmatter disable.
  * (d) Detection-shape cases — directive forms and the known-tool gate.
  * (e) Scope cases — agents/commands dirs, out-of-scope paths.
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


_aatd = _load_module(
    '_analyze_allowed_tools_drift',
    '_analyze_allowed_tools_drift.py',
)

analyze_allowed_tools_drift = _aatd.analyze_allowed_tools_drift
RULE_ID = _aatd.RULE_ID
RULE_NAME = _aatd.RULE_NAME
FINDING_TYPE = _aatd.FINDING_TYPE


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_skill_md(
    tmp_path: Path,
    content: str,
    bundle: str = 'test-bundle',
    skill: str = 'test-skill',
    sub: str = 'skills',
    filename: str = 'SKILL.md',
) -> tuple[Path, Path]:
    """Create a ``{bundle}/{sub}/{skill}/{filename}`` under ``tmp_path``.

    Mirrors the actual layout scanned by ``_skill_source_targets``:
    ``marketplace_root/*/{skills,agents,commands}/**/*.md``.

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


def _fm(declared: str, body: str) -> str:
    """Compose a markdown component with a frontmatter ``allowed-tools`` line.

    ``declared`` is the raw value placed after ``allowed-tools:`` (inline or
    empty); ``body`` is the workflow prose below the closing fence.
    """
    return f'---\nname: test-skill\nallowed-tools: {declared}\n---\n{body}'


def _fm_disable(declared: str, disable: str, body: str) -> str:
    """Compose a component carrying both ``allowed-tools`` and ``plugin-doctor-disable``.

    ``disable`` is the raw value placed after ``plugin-doctor-disable:`` (inline
    list form, e.g. ``[allowed-tools-body-drift]``).
    """
    return (
        f'---\nname: test-skill\n'
        f'allowed-tools: {declared}\n'
        f'plugin-doctor-disable: {disable}\n'
        f'---\n{body}'
    )


# ===========================================================================
# (a) Positive cases — body-invoked tool absent from declared list
# ===========================================================================


class TestPositiveDrift:
    """A body-invoked tool absent from a declared, non-empty list is flagged."""

    def test_inline_declaration_missing_invoked_tool(self, tmp_path: Path) -> None:
        """Inline ``allowed-tools: Read`` + body ``Write:`` directive drifts."""
        content = _fm('Read', 'Write: produce the output file.\n')
        marketplace_root, _ = _make_skill_md(tmp_path, content)
        findings = analyze_allowed_tools_drift(marketplace_root)
        assert len(findings) == 1
        assert findings[0]['rule_id'] == RULE_ID
        assert findings[0]['snippet'] == 'Write'

    def test_yaml_list_declaration_missing_invoked_tool(self, tmp_path: Path) -> None:
        """YAML-list declaration form is parsed; an absent invoked tool drifts."""
        content = (
            '---\n'
            'name: test-skill\n'
            'allowed-tools:\n'
            '  - Read\n'
            '  - Edit\n'
            '---\n'
            'Bash: run the verification command.\n'
        )
        marketplace_root, _ = _make_skill_md(tmp_path, content)
        findings = analyze_allowed_tools_drift(marketplace_root)
        assert len(findings) == 1
        assert findings[0]['snippet'] == 'Bash'

    def test_multiple_drifting_tools_produce_multiple_findings(
        self, tmp_path: Path
    ) -> None:
        """Two undeclared invoked tools on different lines yield two findings."""
        content = _fm(
            'Read',
            'Write: emit the file.\nBash: run the command.\n',
        )
        marketplace_root, _ = _make_skill_md(tmp_path, content)
        findings = analyze_allowed_tools_drift(marketplace_root)
        assert len(findings) == 2
        snippets = sorted(f['snippet'] for f in findings)
        assert snippets == ['Bash', 'Write']

    def test_list_bullet_directive_is_detected(self, tmp_path: Path) -> None:
        """A list-bulleted ``- Skill:`` directive counts as an invocation."""
        content = _fm('Read', '- Skill: plan-marshall:dev-agent-behavior-rules\n')
        marketplace_root, _ = _make_skill_md(tmp_path, content)
        findings = analyze_allowed_tools_drift(marketplace_root)
        assert len(findings) == 1
        assert findings[0]['snippet'] == 'Skill'

    def test_finding_line_is_one_based_absolute(self, tmp_path: Path) -> None:
        """The reported line is the 1-based absolute position in the file."""
        # Lines: 1 '---', 2 name, 3 allowed-tools, 4 '---', 5 intro, 6 'Write:'.
        content = _fm('Read', 'Intro paragraph with no invocation.\nWrite: emit.\n')
        marketplace_root, _ = _make_skill_md(tmp_path, content)
        findings = analyze_allowed_tools_drift(marketplace_root)
        assert len(findings) == 1
        assert findings[0]['line'] == 6


# ===========================================================================
# (b) No-drift cases — clean / out-of-rule-scope
# ===========================================================================


class TestNoDrift:
    """Coverage, missing/empty declarations, and unused declarations are clean."""

    def test_declared_list_covers_invoked_tool(self, tmp_path: Path) -> None:
        """When the declaration covers every invoked tool there is no drift."""
        content = _fm('Read, Write', 'Write: emit the file.\nRead: load context.\n')
        marketplace_root, _ = _make_skill_md(tmp_path, content)
        findings = analyze_allowed_tools_drift(marketplace_root)
        assert findings == []

    def test_no_frontmatter_is_not_flagged(self, tmp_path: Path) -> None:
        """A component with no frontmatter has no declared list to drift against."""
        content = 'Write: emit the file.\nBash: run the command.\n'
        marketplace_root, _ = _make_skill_md(tmp_path, content)
        findings = analyze_allowed_tools_drift(marketplace_root)
        assert findings == []

    def test_missing_allowed_tools_field_is_not_flagged(
        self, tmp_path: Path
    ) -> None:
        """Frontmatter without ``allowed-tools`` is the inherit-all default."""
        content = (
            '---\n'
            'name: test-skill\n'
            'description: a skill with no tool declaration\n'
            '---\n'
            'Write: emit the file.\n'
        )
        marketplace_root, _ = _make_skill_md(tmp_path, content)
        findings = analyze_allowed_tools_drift(marketplace_root)
        assert findings == []

    def test_empty_allowed_tools_value_is_not_flagged(self, tmp_path: Path) -> None:
        """An ``allowed-tools:`` field with no value parses to an empty list.

        An empty declaration is the inherit-all default (the retired
        ``unsupported-skill-tools-field`` behaviour must not return).
        """
        content = _fm('', 'Write: emit the file.\n')
        marketplace_root, _ = _make_skill_md(tmp_path, content)
        findings = analyze_allowed_tools_drift(marketplace_root)
        assert findings == []

    def test_unused_declared_tool_is_not_flagged(self, tmp_path: Path) -> None:
        """A declared tool the body never invokes is NOT a drift (one-directional).

        The rule fires only on body-invoked-but-undeclared tools, never on
        declared-but-unused tools.
        """
        content = _fm('Read, Write, Bash', 'Read: load context.\n')
        marketplace_root, _ = _make_skill_md(tmp_path, content)
        findings = analyze_allowed_tools_drift(marketplace_root)
        assert findings == []


# ===========================================================================
# (c) Exemption cases — fenced code blocks and suppression marker
# ===========================================================================


class TestExemptions:
    """Fenced blocks and the per-file frontmatter disable exempt matches."""

    def test_invocation_inside_fenced_block_is_exempt(self, tmp_path: Path) -> None:
        """A tool directive inside a fenced block is an example, not an invocation."""
        content = _fm(
            'Read',
            '```bash\nWrite: this is example text inside a fence.\n```\n',
        )
        marketplace_root, _ = _make_skill_md(tmp_path, content)
        findings = analyze_allowed_tools_drift(marketplace_root)
        assert findings == []

    def test_fenced_block_with_info_string_is_exempt(self, tmp_path: Path) -> None:
        """A fence with any info-string still exempts its body lines."""
        content = _fm(
            'Read',
            '```text\nBash: example invocation inside a fence.\n```\n',
        )
        marketplace_root, _ = _make_skill_md(tmp_path, content)
        findings = analyze_allowed_tools_drift(marketplace_root)
        assert findings == []

    def test_frontmatter_disable_suppresses_whole_file(self, tmp_path: Path) -> None:
        """A ``plugin-doctor-disable`` naming the rule suppresses every drift in the file."""
        content = _fm_disable(
            'Read',
            '[allowed-tools-body-drift]',
            'Write: emit the file.\nBash: run the command.\n',
        )
        marketplace_root, _ = _make_skill_md(tmp_path, content)
        findings = analyze_allowed_tools_drift(marketplace_root)
        assert findings == []

    def test_frontmatter_disable_block_list_form(self, tmp_path: Path) -> None:
        """The YAML block-list ``plugin-doctor-disable`` form is honored."""
        content = (
            '---\n'
            'name: test-skill\n'
            'allowed-tools: Read\n'
            'plugin-doctor-disable:\n'
            '  - allowed-tools-body-drift\n'
            '---\n'
            'Write: emit the file.\n'
        )
        marketplace_root, _ = _make_skill_md(tmp_path, content)
        findings = analyze_allowed_tools_drift(marketplace_root)
        assert findings == []

    def test_frontmatter_disable_for_other_rule_does_not_suppress(
        self, tmp_path: Path
    ) -> None:
        """A disable list naming a DIFFERENT rule leaves the drift flagged."""
        content = _fm_disable(
            'Read',
            '[some-other-rule]',
            'Write: emit the file.\n',
        )
        marketplace_root, _ = _make_skill_md(tmp_path, content)
        findings = analyze_allowed_tools_drift(marketplace_root)
        assert len(findings) == 1
        assert findings[0]['snippet'] == 'Write'

    def test_retired_inline_marker_no_longer_suppresses(self, tmp_path: Path) -> None:
        """The retired ``<!-- doctor-ignore: allowed-tools-drift -->`` marker is ignored."""
        content = _fm(
            'Read',
            'Write: emit the file. <!-- doctor-ignore: allowed-tools-drift -->\n',
        )
        marketplace_root, _ = _make_skill_md(tmp_path, content)
        findings = analyze_allowed_tools_drift(marketplace_root)
        assert len(findings) == 1
        assert findings[0]['snippet'] == 'Write'


# ===========================================================================
# (d) Detection-shape cases — directive forms and known-tool gate
# ===========================================================================


class TestDetectionShape:
    """Only directive-shaped invocations of known tools count."""

    def test_tool_prefixed_directive_form_is_detected(self, tmp_path: Path) -> None:
        """The ``Tool: Bash`` prefixed form yields the payload tool name."""
        content = _fm('Read', 'Tool: Bash\n')
        marketplace_root, _ = _make_skill_md(tmp_path, content)
        findings = analyze_allowed_tools_drift(marketplace_root)
        assert len(findings) == 1
        assert findings[0]['snippet'] == 'Bash'

    def test_prose_mention_without_directive_is_not_flagged(
        self, tmp_path: Path
    ) -> None:
        """A bullet/heading prose mention (``Use Write to …``) is not an invocation."""
        content = _fm('Read', 'Use Write to produce the output file.\n')
        marketplace_root, _ = _make_skill_md(tmp_path, content)
        findings = analyze_allowed_tools_drift(marketplace_root)
        assert findings == []

    def test_unknown_capitalised_token_is_not_a_tool(self, tmp_path: Path) -> None:
        """A directive-shaped line for a non-tool word is not flagged."""
        content = _fm('Read', 'Note: this is a documentation note, not a tool.\n')
        marketplace_root, _ = _make_skill_md(tmp_path, content)
        findings = analyze_allowed_tools_drift(marketplace_root)
        assert findings == []


# ===========================================================================
# (e) Scope cases — agents/commands dirs and out-of-scope paths
# ===========================================================================


class TestScope:
    """The bundles scope spans skills/agents/commands; other paths are excluded."""

    def test_agents_directory_is_scanned(self, tmp_path: Path) -> None:
        """A file under ``{bundle}/agents/`` is in scope."""
        content = _fm('Read', 'Write: emit the agent output.\n')
        marketplace_root, _ = _make_skill_md(
            tmp_path, content, sub='agents', filename='agent.md'
        )
        findings = analyze_allowed_tools_drift(marketplace_root)
        assert len(findings) == 1

    def test_commands_directory_is_scanned(self, tmp_path: Path) -> None:
        """A file under ``{bundle}/commands/`` is in scope."""
        content = _fm('Read', 'Bash: run the slash command body.\n')
        marketplace_root, _ = _make_skill_md(
            tmp_path, content, sub='commands', filename='cmd.md'
        )
        findings = analyze_allowed_tools_drift(marketplace_root)
        assert len(findings) == 1

    def test_out_of_scope_path_not_scanned(self, tmp_path: Path) -> None:
        """A file under the bundle root but not in a scanned sub is ignored."""
        bundle_dir = tmp_path / 'some-bundle'
        bundle_dir.mkdir(parents=True)
        (bundle_dir / 'README.md').write_text(
            _fm('Read', 'Write: emit the file.\n'), encoding='utf-8'
        )
        findings = analyze_allowed_tools_drift(tmp_path)
        assert findings == []


# ===========================================================================
# (f) Project-local .claude/skills/** cases
# ===========================================================================


class TestClaudeSkillsTree:
    """The project-local ``.claude/skills/**`` tree is scanned too."""

    def test_claude_skill_drift_triggers_finding(self, tmp_path: Path) -> None:
        """A drifting invocation under ``.claude/skills/`` is flagged."""
        content = _fm('Read', 'Write: emit the project-local skill output.\n')
        marketplace_root, target = _make_claude_skill_md(tmp_path, content)
        findings = analyze_allowed_tools_drift(marketplace_root)
        assert len(findings) == 1
        assert findings[0]['file'] == str(target)

    def test_missing_claude_skills_tree_is_tolerated(self, tmp_path: Path) -> None:
        """When no ``.claude/skills`` tree exists, only the bundles tree scans.

        The bundles-only ``tmp_path`` layout has no sibling ``.claude/skills``
        directory, so the project-local enumerator returns an empty list
        rather than raising.
        """
        content = _fm('Read', 'Write: emit the file.\n')
        marketplace_root, _ = _make_skill_md(tmp_path, content)
        findings = analyze_allowed_tools_drift(marketplace_root)
        assert len(findings) == 1

    def test_claude_and_bundles_findings_combine(self, tmp_path: Path) -> None:
        """Findings from the bundles tree and ``.claude/skills`` combine."""
        bundles_root = tmp_path / 'marketplace' / 'bundles'
        skill_dir = bundles_root / 'test-bundle' / 'skills' / 'test-skill'
        skill_dir.mkdir(parents=True)
        skill_dir.joinpath('SKILL.md').write_text(
            _fm('Read', 'Write: emit the bundle output.\n'), encoding='utf-8'
        )
        claude_dir = tmp_path / '.claude' / 'skills' / 'audit-skill'
        claude_dir.mkdir(parents=True)
        claude_dir.joinpath('SKILL.md').write_text(
            _fm('Read', 'Bash: run the project-local command.\n'), encoding='utf-8'
        )
        findings = analyze_allowed_tools_drift(bundles_root)
        assert len(findings) == 2


# ===========================================================================
# (g) Finding-shape case
# ===========================================================================


def test_finding_shape(tmp_path: Path) -> None:
    """A finding carries the documented shape fields."""
    content = _fm('Read', 'Write: emit the file.\n')
    marketplace_root, md_path = _make_skill_md(tmp_path, content)
    findings = analyze_allowed_tools_drift(marketplace_root)
    assert len(findings) == 1
    f = findings[0]
    assert f['rule_id'] == RULE_ID
    assert f['type'] == FINDING_TYPE
    assert f['rule'] == RULE_NAME
    assert f['file'] == str(md_path)
    assert isinstance(f['line'], int) and f['line'] >= 1
    assert f['severity'] == 'warning'
    assert f['fixable'] is False
    assert f['snippet'] == 'Write'
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
        '_analyze_allowed_tools_drift.py',
    ).read_text(encoding='utf-8')
    for marker in ('_SUPPRESS_MARKER', '_IGNORE_MARKER', 'doctor-ignore'):
        assert marker not in source, (
            f'Retired inline marker {marker!r} still present in analyzer source'
        )
