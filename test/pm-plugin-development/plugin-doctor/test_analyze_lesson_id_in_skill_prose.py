# ruff: noqa: I001, E402
"""Tests for the ``no-lesson-id-in-skill-prose`` rule analyzer.

The analyzer detects narrative lesson-ID citations across three file classes:

1. Markdown (``*.md``) under
   ``marketplace/bundles/*/{skills,agents,commands}/**``.
2. Python (``*.py``) under
   ``marketplace/bundles/*/{skills,agents,commands}/**`` — comments,
   docstrings, and string literals.
3. Both markdown and Python under the project-local ``.claude/skills/**``
   tree (resolved relative to the marketplace bundles root).

Two lesson-ID format families are recognised:

1. ``YYYY-MM-DD-NNN`` (e.g., ``2026-04-17-012``)
2. ``YYYY-MM-DD-HH-NNN`` (e.g., ``2026-04-29-23-002``)

Prose-prefixed forms ``lesson XXX`` and ``lesson-XXX`` are also recognised.

For **markdown** sources, five structurally-defined documentary contexts are
exempt:

1. Allowlisted skill path (file-level skip).
2. YAML frontmatter.
3. Fenced code block (any info-string).
4. ``Source:`` provenance line.
5. Inline-code span (backticks).

For **Python** sources, the markdown-only structural exemptions (frontmatter,
fenced code block, ``Source:`` line, inline-code span) do NOT apply — the
whole point of scanning ``.py`` is to catch lesson IDs in comments,
docstrings, and string literals. Only the path-allowlist and the inline
suppression marker apply.

For both file classes an inline suppression marker
``<!-- doctor-ignore: lesson-id-prose -->`` (same-line or preceding line)
suppresses the finding on the marked line only.

Test layers:
  * (a) Positive cases — narrative citation triggers a finding for each
        recognised format family and prefix form (markdown).
  * (b) Allowlist cases — files inside lesson-domain allowlisted paths
        produce zero findings regardless of citation density.
  * (c) Skip-context cases — lesson IDs inside YAML frontmatter, ``Source:``
        lines, fenced code blocks, and inline-code spans produce no findings.
  * (d) Suppression cases — the ``<!-- doctor-ignore: lesson-id-prose -->``
        marker (same-line and prior-line) suppresses the finding.
  * (e) Boundary cases — non-lesson date-like tokens and out-of-scope paths
        produce no findings.
  * (g) Python-source cases — citations in ``.py`` comments, docstrings, and
        string literals are flagged; markdown-only exemptions do NOT apply;
        the path-allowlist and suppression marker still apply.
  * (h) Project-local ``.claude/skills/**`` cases — both ``*.md`` and
        ``*.py`` under the sibling project-local tree are scanned.
"""

from pathlib import Path

from conftest import load_script_module


def _load_module(name: str, filename: str):
    return load_script_module('pm-plugin-development', 'plugin-doctor', filename, name)


_alisp = _load_module(
    '_analyze_lesson_id_in_skill_prose',
    '_analyze_lesson_id_in_skill_prose.py',
)

analyze_lesson_id_in_skill_prose = _alisp.analyze_lesson_id_in_skill_prose
RULE_ID = _alisp.RULE_ID


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_skill_md(
    tmp_path: Path,
    content: str,
    bundle: str = 'test-bundle',
    skill: str = 'test-skill',
    filename: str = 'SKILL.md',
) -> tuple[Path, Path]:
    """Create a ``{bundle}/skills/{skill}/{filename}`` under ``tmp_path``.

    Mirrors the actual layout scanned by ``_skill_markdown_targets``:
    ``marketplace_root/*/{skills,agents,commands}/**/*.md``.

    Returns ``(marketplace_root, md_path)``.
    """
    skill_dir = tmp_path / bundle / 'skills' / skill
    skill_dir.mkdir(parents=True)
    md = skill_dir / filename
    md.write_text(content, encoding='utf-8')
    return tmp_path, md


def _make_skill_py(
    tmp_path: Path,
    content: str,
    bundle: str = 'test-bundle',
    skill: str = 'test-skill',
    filename: str = 'script.py',
) -> tuple[Path, Path]:
    """Create a ``{bundle}/skills/{skill}/scripts/{filename}`` under ``tmp_path``.

    Mirrors the actual layout scanned by ``_skill_source_targets`` for the
    Python file class: ``marketplace_root/*/{skills,agents,commands}/**/*.py``.

    Returns ``(marketplace_root, py_path)``.
    """
    scripts_dir = tmp_path / bundle / 'skills' / skill / 'scripts'
    scripts_dir.mkdir(parents=True)
    py = scripts_dir / filename
    py.write_text(content, encoding='utf-8')
    return tmp_path, py


def _make_claude_skill_file(
    tmp_path: Path,
    content: str,
    skill: str = 'audit-skill',
    filename: str = 'SKILL.md',
) -> tuple[Path, Path]:
    """Create a project-local ``.claude/skills/{skill}/{filename}`` + bundles root.

    The analyzer resolves the ``.claude/skills`` tree as
    ``marketplace_root.parent.parent / '.claude' / 'skills'``. To exercise
    that resolution the marketplace bundles root must live at
    ``tmp_path/marketplace/bundles`` so that two levels up lands on
    ``tmp_path``, where ``.claude/skills`` is created.

    Returns ``(marketplace_root, claude_file_path)`` where ``marketplace_root``
    is the bundles directory to pass to the analyzer.
    """
    bundles_root = tmp_path / 'marketplace' / 'bundles'
    bundles_root.mkdir(parents=True)
    claude_dir = tmp_path / '.claude' / 'skills' / skill
    claude_dir.mkdir(parents=True)
    target = claude_dir / filename
    target.write_text(content, encoding='utf-8')
    return bundles_root, target


# ===========================================================================
# (a) Positive cases — citation triggers a finding
# ===========================================================================


class TestPositiveDetection:
    """Narrative lesson-ID citation in skill prose must be flagged."""

    def test_short_format_in_prose_triggers_finding(self, tmp_path: Path) -> None:
        """A bare YYYY-MM-DD-NNN id in prose is a finding."""
        content = 'See driving lesson 2026-04-17-012 for the rationale.\n'
        marketplace_root, _ = _make_skill_md(tmp_path, content)
        findings = analyze_lesson_id_in_skill_prose(marketplace_root)
        assert len(findings) == 1
        assert findings[0]['rule_id'] == RULE_ID

    def test_long_format_in_prose_triggers_finding(self, tmp_path: Path) -> None:
        """A bare YYYY-MM-DD-HH-NNN id in prose is a finding."""
        content = 'This was added per lesson 2026-04-29-23-002.\n'
        marketplace_root, _ = _make_skill_md(tmp_path, content)
        findings = analyze_lesson_id_in_skill_prose(marketplace_root)
        assert len(findings) == 1

    def test_lesson_dash_prefix_form_triggers_finding(
        self, tmp_path: Path
    ) -> None:
        """The ``lesson-XXX`` prefix form is recognised in prose."""
        content = 'The cross-bundle sweep (lesson-2026-04-29-08-003) migrated all.\n'
        marketplace_root, _ = _make_skill_md(tmp_path, content)
        findings = analyze_lesson_id_in_skill_prose(marketplace_root)
        assert len(findings) == 1

    def test_lesson_space_prefix_form_triggers_finding(
        self, tmp_path: Path
    ) -> None:
        """The ``lesson XXX`` prefix form is recognised in prose."""
        content = 'Worked example (lesson 2026-04-18-05-002): plan-retrospective.\n'
        marketplace_root, _ = _make_skill_md(tmp_path, content)
        findings = analyze_lesson_id_in_skill_prose(marketplace_root)
        assert len(findings) == 1

    def test_multiple_ids_in_one_file_produce_multiple_findings(
        self, tmp_path: Path
    ) -> None:
        """Two ids on different lines produce two findings."""
        content = (
            'First match per lesson 2026-04-17-012.\n'
            'Second match per lesson 2026-04-29-23-002.\n'
        )
        marketplace_root, _ = _make_skill_md(tmp_path, content)
        findings = analyze_lesson_id_in_skill_prose(marketplace_root)
        assert len(findings) == 2
        assert findings[0]['line'] == 1
        assert findings[1]['line'] == 2

    def test_finding_shape(self, tmp_path: Path) -> None:
        """Finding carries the expected shape fields."""
        content = 'See lesson 2026-04-17-012 for context.\n'
        marketplace_root, md_path = _make_skill_md(tmp_path, content)
        findings = analyze_lesson_id_in_skill_prose(marketplace_root)
        assert len(findings) == 1
        f = findings[0]
        assert f['rule_id'] == RULE_ID
        assert f['type'] == 'lesson_id_in_skill_prose'
        assert f['rule'] == 'analyze_lesson_id_in_skill_prose'
        assert f['file'] == str(md_path)
        assert isinstance(f['line'], int) and f['line'] >= 1
        assert f['severity'] == 'warning'
        assert f['fixable'] is False
        assert 'snippet' in f
        assert 'description' in f


# ===========================================================================
# (b) Allowlist cases — file is exempt regardless of citation density
# ===========================================================================


class TestAllowlistExemption:
    """Files under lesson-domain allowlisted paths produce zero findings."""

    def test_manage_lessons_skill_md_is_exempt(self, tmp_path: Path) -> None:
        """A ``manage-lessons/SKILL.md`` file under plan-marshall is exempt."""
        content = (
            'Lessons can reference 2026-04-17-012, 2026-04-29-23-002, '
            'or lesson-2026-05-15-13-001 — none should trigger findings.\n'
        )
        skill_dir = tmp_path / 'plan-marshall' / 'skills' / 'manage-lessons'
        skill_dir.mkdir(parents=True)
        (skill_dir / 'SKILL.md').write_text(content, encoding='utf-8')
        findings = analyze_lesson_id_in_skill_prose(tmp_path)
        assert findings == []

    def test_manage_lessons_standards_doc_is_exempt(
        self, tmp_path: Path
    ) -> None:
        """A standards doc under ``manage-lessons/`` is exempt."""
        content = 'Reference lesson 2026-04-17-012 multiple times.\n'
        std_dir = (
            tmp_path
            / 'plan-marshall'
            / 'skills'
            / 'manage-lessons'
            / 'standards'
        )
        std_dir.mkdir(parents=True)
        (std_dir / 'format.md').write_text(content, encoding='utf-8')
        findings = analyze_lesson_id_in_skill_prose(tmp_path)
        assert findings == []

    def test_phase6_finalize_lessons_workflow_is_exempt(
        self, tmp_path: Path
    ) -> None:
        """A ``phase-6-finalize/workflow/lessons-capture.md`` file is exempt."""
        content = 'See lesson 2026-04-29-23-002 (capture step).\n'
        wf_dir = (
            tmp_path
            / 'plan-marshall'
            / 'skills'
            / 'phase-6-finalize'
            / 'workflow'
        )
        wf_dir.mkdir(parents=True)
        (wf_dir / 'lessons-capture.md').write_text(content, encoding='utf-8')
        findings = analyze_lesson_id_in_skill_prose(tmp_path)
        assert findings == []

    def test_phase6_finalize_lessons_standard_is_exempt(
        self, tmp_path: Path
    ) -> None:
        """A ``phase-6-finalize/standards/lessons-*.md`` file is exempt."""
        content = 'See lesson 2026-04-29-23-002 (standard).\n'
        std_dir = (
            tmp_path
            / 'plan-marshall'
            / 'skills'
            / 'phase-6-finalize'
            / 'standards'
        )
        std_dir.mkdir(parents=True)
        (std_dir / 'lessons-format.md').write_text(content, encoding='utf-8')
        findings = analyze_lesson_id_in_skill_prose(tmp_path)
        assert findings == []

    def test_plugin_doctor_rule_provenance_is_exempt(
        self, tmp_path: Path
    ) -> None:
        """The plugin-doctor rule-provenance.md is exempt."""
        content = (
            'Sources: lesson 2026-04-17-012, lesson 2026-04-29-23-002, '
            'lesson 2026-05-15-13-001.\n'
        )
        ref_dir = (
            tmp_path
            / 'pm-plugin-development'
            / 'skills'
            / 'plugin-doctor'
            / 'references'
        )
        ref_dir.mkdir(parents=True)
        (ref_dir / 'rule-provenance.md').write_text(content, encoding='utf-8')
        findings = analyze_lesson_id_in_skill_prose(tmp_path)
        assert findings == []


# ===========================================================================
# (c) Skip-context cases
# ===========================================================================


class TestSkipContextExemption:
    """Lesson IDs in structured-provenance contexts produce no findings."""

    def test_yaml_frontmatter_is_exempt(self, tmp_path: Path) -> None:
        """A lesson ID inside YAML frontmatter is exempt."""
        content = (
            '---\n'
            'name: test-skill\n'
            'lesson: 2026-04-17-012\n'
            '---\n'
            'Body content with no citations.\n'
        )
        marketplace_root, _ = _make_skill_md(tmp_path, content)
        findings = analyze_lesson_id_in_skill_prose(marketplace_root)
        assert findings == []

    def test_fenced_code_block_is_exempt(self, tmp_path: Path) -> None:
        """A lesson ID inside a fenced code block is exempt."""
        content = (
            '# Standards doc\n\n'
            '```bash\n'
            'echo "see lesson 2026-04-17-012"\n'
            '```\n'
        )
        marketplace_root, _ = _make_skill_md(tmp_path, content)
        findings = analyze_lesson_id_in_skill_prose(marketplace_root)
        assert findings == []

    def test_fenced_block_with_any_info_string_is_exempt(
        self, tmp_path: Path
    ) -> None:
        """A fenced block with any info-string (e.g., python) is exempt."""
        content = (
            '```python\n'
            "# lesson 2026-04-29-23-002 provenance\n"
            '```\n'
        )
        marketplace_root, _ = _make_skill_md(tmp_path, content)
        findings = analyze_lesson_id_in_skill_prose(marketplace_root)
        assert findings == []

    def test_source_line_is_exempt(self, tmp_path: Path) -> None:
        """A line whose payload is a ``Source:`` provenance citation is exempt."""
        content = (
            '# Heading\n\n'
            'Source: lesson 2026-04-17-012\n\n'
            'Body text with no citations.\n'
        )
        marketplace_root, _ = _make_skill_md(tmp_path, content)
        findings = analyze_lesson_id_in_skill_prose(marketplace_root)
        assert findings == []

    def test_bare_inline_code_span_is_exempt(self, tmp_path: Path) -> None:
        """A bare lesson ID inside an inline-code span (no prose prefix) is exempt."""
        content = 'Driving lessons: `2026-04-17-012`, `2026-04-29-23-002`.\n'
        marketplace_root, _ = _make_skill_md(tmp_path, content)
        findings = analyze_lesson_id_in_skill_prose(marketplace_root)
        assert findings == []

    def test_lesson_backtick_prefix_form_triggers_finding(
        self, tmp_path: Path
    ) -> None:
        """``lesson `YYYY-...` `` where 'lesson' is outside the backtick is flagged.

        This is the common prose pattern that the original rule missed because the
        ID token itself is inside backticks. The word 'lesson' outside the backtick
        establishes narrative context — the reader is being pointed at an ephemeral
        lesson file — so the citation must be stripped regardless of the backtick.
        """
        content = 'The motivating gap (lesson `2026-05-08-14-001`) was that the emission was lost.\n'
        marketplace_root, _ = _make_skill_md(tmp_path, content)
        findings = analyze_lesson_id_in_skill_prose(marketplace_root)
        assert len(findings) >= 1

    def test_lesson_backtick_long_format_triggers_finding(
        self, tmp_path: Path
    ) -> None:
        """Long format ``lesson `YYYY-MM-DD-HH-NNN` `` is also flagged."""
        content = 'Unconditionally active per lesson `2026-04-29-23-002`.\n'
        marketplace_root, _ = _make_skill_md(tmp_path, content)
        findings = analyze_lesson_id_in_skill_prose(marketplace_root)
        assert len(findings) >= 1

    def test_bare_id_outside_inline_code_on_same_line_is_flagged(
        self, tmp_path: Path
    ) -> None:
        """Only the span-internal id is exempt; the bare one is flagged."""
        content = (
            'See `2026-04-17-012` and also 2026-04-29-23-002 outside.\n'
        )
        marketplace_root, _ = _make_skill_md(tmp_path, content)
        findings = analyze_lesson_id_in_skill_prose(marketplace_root)
        assert len(findings) == 1


# ===========================================================================
# (d) Suppression marker cases
# ===========================================================================


class TestSuppressionMarker:
    """The ``<!-- doctor-ignore: lesson-id-prose -->`` marker suppresses
    findings on the marked line only."""

    def test_same_line_suppression(self, tmp_path: Path) -> None:
        """Marker on the same line suppresses the finding."""
        content = (
            'See lesson 2026-04-17-012. <!-- doctor-ignore: lesson-id-prose -->\n'
        )
        marketplace_root, _ = _make_skill_md(tmp_path, content)
        findings = analyze_lesson_id_in_skill_prose(marketplace_root)
        assert findings == []

    def test_preceding_line_suppression(self, tmp_path: Path) -> None:
        """Marker on the preceding line suppresses the finding."""
        content = (
            '<!-- doctor-ignore: lesson-id-prose -->\n'
            'See lesson 2026-04-17-012 for context.\n'
        )
        marketplace_root, _ = _make_skill_md(tmp_path, content)
        findings = analyze_lesson_id_in_skill_prose(marketplace_root)
        assert findings == []

    def test_marker_only_suppresses_the_marked_line(
        self, tmp_path: Path
    ) -> None:
        """The marker is per-line — adjacent unmarked lines still produce findings."""
        content = (
            'See lesson 2026-04-17-012. <!-- doctor-ignore: lesson-id-prose -->\n'
            'Also see lesson 2026-04-29-23-002.\n'
        )
        marketplace_root, _ = _make_skill_md(tmp_path, content)
        findings = analyze_lesson_id_in_skill_prose(marketplace_root)
        assert len(findings) == 1
        assert findings[0]['line'] == 2


# ===========================================================================
# (d.1) Standalone-marker scoping — regression guards
# ===========================================================================


class TestStandaloneMarkerScoping:
    """Regression: the suppression marker MUST scope to its own line (and the
    immediately following one), and MUST NOT bleed across sections or files.

    The marker semantics are line-local — a standalone marker at the top of a
    section does NOT suppress lesson IDs deeper in the same section, and a
    marker in one file has zero effect on findings in a sibling file.
    """

    def test_marker_does_not_bleed_two_lines_below(self, tmp_path: Path) -> None:
        """Marker two lines above the citation does NOT suppress the finding."""
        content = (
            '<!-- doctor-ignore: lesson-id-prose -->\n'
            '\n'
            'See lesson 2026-04-17-012 for context.\n'
        )
        marketplace_root, _ = _make_skill_md(tmp_path, content)
        findings = analyze_lesson_id_in_skill_prose(marketplace_root)
        assert len(findings) == 1
        assert findings[0]['line'] == 3

    def test_marker_does_not_bleed_across_section_boundary(
        self, tmp_path: Path
    ) -> None:
        """A marker in one section MUST NOT suppress citations in the next section."""
        content = (
            '## Section A\n'
            '<!-- doctor-ignore: lesson-id-prose -->\n'
            'See lesson 2026-04-17-012 (suppressed by marker above).\n'
            '\n'
            '## Section B\n'
            'See lesson 2026-04-29-23-002 (must be flagged).\n'
        )
        marketplace_root, _ = _make_skill_md(tmp_path, content)
        findings = analyze_lesson_id_in_skill_prose(marketplace_root)
        assert len(findings) == 1
        assert findings[0]['line'] == 6

    def test_standalone_marker_at_top_of_file_does_not_blanket_file(
        self, tmp_path: Path
    ) -> None:
        """A single marker at file top does NOT act as a file-wide suppression."""
        content = (
            '<!-- doctor-ignore: lesson-id-prose -->\n'
            '\n'
            '## Heading\n'
            'See lesson 2026-04-17-012 here.\n'
            'And another: lesson 2026-04-29-23-002.\n'
        )
        marketplace_root, _ = _make_skill_md(tmp_path, content)
        findings = analyze_lesson_id_in_skill_prose(marketplace_root)
        assert len(findings) == 2

    def test_marker_does_not_bleed_across_files(self, tmp_path: Path) -> None:
        """A marker in one skill file does NOT affect findings in a sibling file."""
        # File 1: has marker + citation (suppressed).
        skill_a_dir = tmp_path / 'bundle-a' / 'skills' / 'skill-a'
        skill_a_dir.mkdir(parents=True)
        (skill_a_dir / 'SKILL.md').write_text(
            '<!-- doctor-ignore: lesson-id-prose -->\n'
            'See lesson 2026-04-17-012.\n',
            encoding='utf-8',
        )
        # File 2: citation without marker (must be flagged).
        skill_b_dir = tmp_path / 'bundle-b' / 'skills' / 'skill-b'
        skill_b_dir.mkdir(parents=True)
        (skill_b_dir / 'SKILL.md').write_text(
            'See lesson 2026-04-29-23-002.\n',
            encoding='utf-8',
        )
        findings = analyze_lesson_id_in_skill_prose(tmp_path)
        assert len(findings) == 1
        assert findings[0]['file'].endswith('bundle-b/skills/skill-b/SKILL.md')


# ===========================================================================
# (e) Boundary cases
# ===========================================================================


class TestBoundaryCases:
    """Non-lesson tokens and out-of-scope paths produce no findings."""

    def test_date_only_token_not_flagged(self, tmp_path: Path) -> None:
        """A bare ``YYYY-MM-DD`` date is not a lesson-ID format."""
        content = 'The decision was recorded on 2026-04-29.\n'
        marketplace_root, _ = _make_skill_md(tmp_path, content)
        findings = analyze_lesson_id_in_skill_prose(marketplace_root)
        assert findings == []

    def test_partial_date_hour_token_not_flagged(self, tmp_path: Path) -> None:
        """``YYYY-MM-DD-HH`` without the trailing ``-NNN`` is not flagged."""
        content = 'Reference 2026-04-29-23 without the trailing index.\n'
        marketplace_root, _ = _make_skill_md(tmp_path, content)
        findings = analyze_lesson_id_in_skill_prose(marketplace_root)
        assert findings == []

    def test_out_of_scope_path_not_scanned(self, tmp_path: Path) -> None:
        """A file outside ``{skills,agents,commands}/`` is not scanned."""
        # File under bundle root but not in a scanned sub.
        bundle_dir = tmp_path / 'some-bundle'
        bundle_dir.mkdir(parents=True)
        (bundle_dir / 'README.md').write_text(
            'See lesson 2026-04-17-012.\n', encoding='utf-8'
        )
        findings = analyze_lesson_id_in_skill_prose(tmp_path)
        assert findings == []

    def test_agents_directory_is_scanned(self, tmp_path: Path) -> None:
        """A file under ``{bundle}/agents/`` is in scope."""
        agent_dir = tmp_path / 'test-bundle' / 'agents'
        agent_dir.mkdir(parents=True)
        (agent_dir / 'agent.md').write_text(
            'See lesson 2026-04-17-012.\n', encoding='utf-8'
        )
        findings = analyze_lesson_id_in_skill_prose(tmp_path)
        assert len(findings) == 1

    def test_commands_directory_is_scanned(self, tmp_path: Path) -> None:
        """A file under ``{bundle}/commands/`` is in scope."""
        cmd_dir = tmp_path / 'test-bundle' / 'commands'
        cmd_dir.mkdir(parents=True)
        (cmd_dir / 'cmd.md').write_text(
            'Reference lesson 2026-04-17-012.\n', encoding='utf-8'
        )
        findings = analyze_lesson_id_in_skill_prose(tmp_path)
        assert len(findings) == 1


# ===========================================================================
# (g) Python-source cases — comments, docstrings, string literals
# ===========================================================================


class TestPythonSourceDetection:
    """Narrative lesson-ID citations in ``.py`` sources must be flagged."""

    def test_py_comment_citation_triggers_finding(self, tmp_path: Path) -> None:
        """A lesson-ID in a ``#`` comment is a finding."""
        content = '# Guard added per lesson 2026-04-17-012 for the rationale.\n'
        marketplace_root, py_path = _make_skill_py(tmp_path, content)
        findings = analyze_lesson_id_in_skill_prose(marketplace_root)
        assert len(findings) == 1
        assert findings[0]['rule_id'] == RULE_ID
        assert findings[0]['file'] == str(py_path)

    def test_py_docstring_citation_triggers_finding(self, tmp_path: Path) -> None:
        """A lesson-ID inside a module docstring is a finding."""
        content = (
            '"""Module summary.\n\n'
            'This dedup logic was added per lesson 2026-04-29-23-002.\n'
            '"""\n'
        )
        marketplace_root, _ = _make_skill_py(tmp_path, content)
        findings = analyze_lesson_id_in_skill_prose(marketplace_root)
        assert len(findings) == 1

    def test_py_string_literal_citation_triggers_finding(
        self, tmp_path: Path
    ) -> None:
        """A lesson-ID inside a string literal is a finding."""
        content = "MESSAGE = 'See lesson 2026-04-17-012 for context.'\n"
        marketplace_root, _ = _make_skill_py(tmp_path, content)
        findings = analyze_lesson_id_in_skill_prose(marketplace_root)
        assert len(findings) == 1

    def test_py_lesson_dash_prefix_triggers_finding(self, tmp_path: Path) -> None:
        """The ``lesson-XXX`` prefix form is recognised in Python prose."""
        content = '# Cross-bundle sweep (lesson-2026-04-29-08-003) migrated all.\n'
        marketplace_root, _ = _make_skill_py(tmp_path, content)
        findings = analyze_lesson_id_in_skill_prose(marketplace_root)
        assert len(findings) == 1

    def test_py_markdown_fence_exemption_does_not_apply(
        self, tmp_path: Path
    ) -> None:
        """A ``` ``` ``` line in Python is NOT a fence exemption — still flagged.

        Markdown-only structural exemptions must not leak into Python scanning.
        A line that merely looks like a markdown fence delimiter in a ``.py``
        file does not gate the citation that follows.
        """
        content = (
            '# ```python\n'
            '# Provenance: lesson 2026-04-17-012\n'
            '# ```\n'
        )
        marketplace_root, _ = _make_skill_py(tmp_path, content)
        findings = analyze_lesson_id_in_skill_prose(marketplace_root)
        assert len(findings) == 1

    def test_py_source_line_exemption_does_not_apply(
        self, tmp_path: Path
    ) -> None:
        """A ``Source:`` line in Python is NOT exempt — still flagged."""
        content = '# Source: lesson 2026-04-17-012\n'
        marketplace_root, _ = _make_skill_py(tmp_path, content)
        findings = analyze_lesson_id_in_skill_prose(marketplace_root)
        assert len(findings) == 1

    def test_py_backtick_wrapped_id_still_flagged(self, tmp_path: Path) -> None:
        """Backtick has no inline-code meaning in Python — the ID is flagged.

        Counted exactly once (Pass 1 catches the bare ID; the markdown-only
        backtick Pass 2 is disabled for Python so there is no double-count).
        """
        content = '# Per lesson `2026-04-29-23-002` the emission was lost.\n'
        marketplace_root, _ = _make_skill_py(tmp_path, content)
        findings = analyze_lesson_id_in_skill_prose(marketplace_root)
        assert len(findings) == 1

    def test_py_allowlisted_path_is_exempt(self, tmp_path: Path) -> None:
        """A ``.py`` under an allowlisted skill path produces zero findings."""
        content = '# Validates lesson 2026-04-17-012 references.\n'
        scripts_dir = (
            tmp_path
            / 'plan-marshall'
            / 'skills'
            / 'manage-lessons'
            / 'scripts'
        )
        scripts_dir.mkdir(parents=True)
        (scripts_dir / 'manage_lessons.py').write_text(content, encoding='utf-8')
        findings = analyze_lesson_id_in_skill_prose(tmp_path)
        assert findings == []

    def test_py_suppression_marker_applies(self, tmp_path: Path) -> None:
        """The inline suppression marker suppresses a finding in Python prose."""
        content = (
            '# See lesson 2026-04-17-012. <!-- doctor-ignore: lesson-id-prose -->\n'
        )
        marketplace_root, _ = _make_skill_py(tmp_path, content)
        findings = analyze_lesson_id_in_skill_prose(marketplace_root)
        assert findings == []

    def test_py_bare_date_token_not_flagged(self, tmp_path: Path) -> None:
        """A bare ``YYYY-MM-DD`` date in Python is not a lesson-ID format."""
        content = '# Recorded on 2026-04-29.\n'
        marketplace_root, _ = _make_skill_py(tmp_path, content)
        findings = analyze_lesson_id_in_skill_prose(marketplace_root)
        assert findings == []


# ===========================================================================
# (h) Project-local .claude/skills/** cases
# ===========================================================================


class TestClaudeSkillsTree:
    """The project-local ``.claude/skills/**`` tree (both ``*.md`` and
    ``*.py``) is scanned in addition to the marketplace bundles tree."""

    def test_claude_skill_md_citation_triggers_finding(
        self, tmp_path: Path
    ) -> None:
        """A markdown citation under ``.claude/skills/`` is flagged."""
        content = 'Covered by lesson 2026-06-01-12-001 (Gate-1 dedup).\n'
        marketplace_root, target = _make_claude_skill_file(tmp_path, content)
        findings = analyze_lesson_id_in_skill_prose(marketplace_root)
        assert len(findings) == 1
        assert findings[0]['file'] == str(target)

    def test_claude_skill_py_citation_triggers_finding(
        self, tmp_path: Path
    ) -> None:
        """A Python citation under ``.claude/skills/`` is flagged."""
        content = '# Gate-1 dedup against lesson 2026-05-31-21-001.\n'
        marketplace_root, target = _make_claude_skill_file(
            tmp_path, content, filename='audit.py'
        )
        findings = analyze_lesson_id_in_skill_prose(marketplace_root)
        assert len(findings) == 1
        assert findings[0]['file'] == str(target)

    def test_claude_skill_nested_check_doc_is_scanned(
        self, tmp_path: Path
    ) -> None:
        """A nested ``.claude/skills/{skill}/checks/*.md`` file is scanned."""
        bundles_root = tmp_path / 'marketplace' / 'bundles'
        bundles_root.mkdir(parents=True)
        checks_dir = (
            tmp_path / '.claude' / 'skills' / 'audit-skill' / 'checks'
        )
        checks_dir.mkdir(parents=True)
        (checks_dir / 'quality-chain.md').write_text(
            'See lesson 2026-05-31-20-002 for the chain rule.\n',
            encoding='utf-8',
        )
        findings = analyze_lesson_id_in_skill_prose(bundles_root)
        assert len(findings) == 1

    def test_claude_skill_clean_tree_produces_no_findings(
        self, tmp_path: Path
    ) -> None:
        """A clean ``.claude/skills/`` tree produces zero findings."""
        content = 'This prose names the codified rule, not any lesson ID.\n'
        marketplace_root, _ = _make_claude_skill_file(tmp_path, content)
        findings = analyze_lesson_id_in_skill_prose(marketplace_root)
        assert findings == []

    def test_missing_claude_skills_tree_is_tolerated(
        self, tmp_path: Path
    ) -> None:
        """When no ``.claude/skills`` tree exists, only the bundles tree scans.

        The bundles-only ``tmp_path`` layout used by the markdown tests has no
        sibling ``.claude/skills`` directory, so the project-local enumerator
        must return an empty list rather than raising.
        """
        content = 'See lesson 2026-04-17-012 for context.\n'
        marketplace_root, _ = _make_skill_md(tmp_path, content)
        findings = analyze_lesson_id_in_skill_prose(marketplace_root)
        # Exactly the one markdown finding; the absent .claude/skills tree
        # contributes nothing and does not raise.
        assert len(findings) == 1

    def test_claude_and_bundles_findings_combine(self, tmp_path: Path) -> None:
        """Findings from both the bundles tree and ``.claude/skills`` combine."""
        bundles_root = tmp_path / 'marketplace' / 'bundles'
        skill_dir = bundles_root / 'test-bundle' / 'skills' / 'test-skill'
        skill_dir.mkdir(parents=True)
        (skill_dir / 'SKILL.md').write_text(
            'See lesson 2026-04-17-012 here.\n', encoding='utf-8'
        )
        claude_dir = tmp_path / '.claude' / 'skills' / 'audit-skill'
        claude_dir.mkdir(parents=True)
        (claude_dir / 'SKILL.md').write_text(
            'Covered by lesson 2026-06-01-12-001.\n', encoding='utf-8'
        )
        findings = analyze_lesson_id_in_skill_prose(bundles_root)
        assert len(findings) == 2
