# ruff: noqa: I001, E402
"""Tests for the ``bash-chain-shapes-in-skills`` rule analyzer.

The analyzer detects compound Bash command sequences (``&&``, ``;``,
trailing ``&``) inside fenced ``bash``/``sh`` blocks in plan-marshall
skill/agent/command markdown files.  Such patterns violate the
persona-plan-marshall-agent "Bash: one command per call" hard rule.

Detection scope: only fenced ``bash`` or ``sh`` blocks (prose, python fences,
etc. are not scanned).

Exemptions:
  1. Comment lines (first non-whitespace char is ``#``).
  2. All lines outside ``bash``/``sh`` fenced blocks.
  Note: backtick spans inside bash fences are command substitutions, NOT inline-code
  exemptions — they are scanned for chain-shape violations.

Test layers:
  (a) Detection of ``&&`` chains inside bash/sh fences.
  (b) Detection of ``;`` chains inside bash/sh fences.
  (c) Detection of trailing ``&`` (background dispatch) inside bash/sh fences.
  (d) Non-detection: prose outside fences is NOT scanned.
  (e) Non-detection: comment lines inside bash fences are exempt.
  (f) Backtick spans inside bash fences are flagged (command substitutions, not markdown).
  (g) Non-detection: backslash-escaped ``\\&`` is exempt from trailing-& rule.
  (h) Finding shape validation.
  (i) Multiple findings on a single line.
  (j) Clean baseline (no findings).
"""

from pathlib import Path

from conftest import load_script_module


def _load_module(name: str, filename: str):
    return load_script_module('pm-plugin-development', 'plugin-doctor', filename, name)


_abcs = _load_module(
    '_analyze_bash_chain_shapes_in_skills',
    '_analyze_bash_chain_shapes_in_skills.py',
)

analyze_bash_chain_shapes_in_skills = _abcs.analyze_bash_chain_shapes_in_skills
RULE_ID = _abcs.RULE_ID


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_skill_md(tmp_path: Path, content: str) -> tuple[Path, Path]:
    """Create a ``plan-marshall/skills/test-skill/SKILL.md`` fixture.

    Returns ``(marketplace_root, md_path)``.
    The analyzer scans ``marketplace_root/plan-marshall/{skills,agents,commands}/``.
    """
    skill_dir = tmp_path / 'plan-marshall' / 'skills' / 'test-skill'
    skill_dir.mkdir(parents=True)
    md = skill_dir / 'SKILL.md'
    md.write_text(content, encoding='utf-8')
    return tmp_path, md


def _make_agent_md(tmp_path: Path, content: str) -> tuple[Path, Path]:
    """Create a ``plan-marshall/agents/test-agent.md`` fixture."""
    agents_dir = tmp_path / 'plan-marshall' / 'agents'
    agents_dir.mkdir(parents=True)
    md = agents_dir / 'test-agent.md'
    md.write_text(content, encoding='utf-8')
    return tmp_path, md


# ===========================================================================
# (a) Detection of && chains in bash/sh fences
# ===========================================================================


class TestAndAndDetection:
    """``&&`` inside a fenced bash/sh block must be flagged."""

    def test_and_and_in_bash_fence_triggers_finding(self, tmp_path: Path) -> None:
        """``cmd1 && cmd2`` inside bash fence is a finding."""
        content = '```bash\ncmd1 && cmd2\n```\n'
        marketplace_root, _ = _make_skill_md(tmp_path, content)
        findings = analyze_bash_chain_shapes_in_skills(marketplace_root)
        assert len(findings) == 1
        assert findings[0]['rule_id'] == RULE_ID
        assert findings[0]['chain_type'] == 'and_and'

    def test_and_and_in_sh_fence_triggers_finding(self, tmp_path: Path) -> None:
        """``&&`` inside ```sh``` block is a finding."""
        content = '```sh\ngit fetch origin main && git checkout main\n```\n'
        marketplace_root, _ = _make_skill_md(tmp_path, content)
        findings = analyze_bash_chain_shapes_in_skills(marketplace_root)
        assert len(findings) == 1
        assert findings[0]['chain_type'] == 'and_and'

    def test_and_and_canonical_violation_example(self, tmp_path: Path) -> None:
        """The canonical violation example from the source incident is detected."""
        content = (
            '```bash\n'
            'python3 .plan/execute-script.py plan-marshall:build-pyproject:pyproject_build run '
            '--command-args "verify" > /tmp/output.json 2>&1 && grep result /tmp/output.json\n'
            '```\n'
        )
        marketplace_root, _ = _make_skill_md(tmp_path, content)
        findings = analyze_bash_chain_shapes_in_skills(marketplace_root)
        # Should detect &&
        and_and_findings = [f for f in findings if f['chain_type'] == 'and_and']
        assert len(and_and_findings) >= 1

    def test_and_and_not_detected_in_prose(self, tmp_path: Path) -> None:
        """``&&`` in narrative prose (outside bash fence) is NOT flagged."""
        content = 'Run cmd1 && cmd2 to do the thing.\n'
        marketplace_root, _ = _make_skill_md(tmp_path, content)
        findings = analyze_bash_chain_shapes_in_skills(marketplace_root)
        assert findings == []

    def test_and_and_not_detected_in_python_fence(self, tmp_path: Path) -> None:
        """``&&`` inside a python fence is NOT scanned (only bash/sh fences)."""
        content = '```python\nif a and b and c:\n    pass  # and-and\n```\n'
        marketplace_root, _ = _make_skill_md(tmp_path, content)
        findings = analyze_bash_chain_shapes_in_skills(marketplace_root)
        assert findings == []


# ===========================================================================
# (b) Detection of ; chains in bash/sh fences
# ===========================================================================


class TestSemicolonDetection:
    """Semicolons inside a fenced bash/sh block must be flagged."""

    def test_semicolon_in_bash_fence_triggers_finding(self, tmp_path: Path) -> None:
        """``;`` inside bash fence is a finding."""
        content = '```bash\ncmd1; cmd2\n```\n'
        marketplace_root, _ = _make_skill_md(tmp_path, content)
        findings = analyze_bash_chain_shapes_in_skills(marketplace_root)
        assert any(f['chain_type'] == 'semicolon' for f in findings)

    def test_semicolon_canonical_violation_example(self, tmp_path: Path) -> None:
        """The ``> /tmp/...; grep`` canonical violation is detected as semicolon chain."""
        content = (
            '```bash\n'
            'python3 .plan/execute-script.py plan-marshall:build-pyproject:pyproject_build run '
            '--command-args "verify" > /tmp/output.json 2>&1; grep result /tmp/output.json\n'
            '```\n'
        )
        marketplace_root, _ = _make_skill_md(tmp_path, content)
        findings = analyze_bash_chain_shapes_in_skills(marketplace_root)
        semicolon_findings = [f for f in findings if f['chain_type'] == 'semicolon']
        assert len(semicolon_findings) >= 1

    def test_semicolon_not_detected_in_prose(self, tmp_path: Path) -> None:
        """Semicolons in narrative prose are NOT flagged (out of bash fence scope)."""
        content = 'Note: run cmd1; run cmd2 if needed.\n'
        marketplace_root, _ = _make_skill_md(tmp_path, content)
        findings = analyze_bash_chain_shapes_in_skills(marketplace_root)
        assert findings == []


# ===========================================================================
# (c) Detection of trailing & (background dispatch) in bash/sh fences
# ===========================================================================


class TestTrailingAmpersandDetection:
    """Trailing ``&`` (background dispatch) inside a fenced bash/sh block must be flagged."""

    def test_trailing_ampersand_in_bash_fence_triggers_finding(self, tmp_path: Path) -> None:
        """Trailing ``&`` inside bash fence is a finding."""
        content = '```bash\npython3 long_task.py &\n```\n'
        marketplace_root, _ = _make_skill_md(tmp_path, content)
        findings = analyze_bash_chain_shapes_in_skills(marketplace_root)
        bg_findings = [f for f in findings if f['chain_type'] == 'background']
        assert len(bg_findings) == 1

    def test_trailing_ampersand_with_whitespace_in_bash_fence(self, tmp_path: Path) -> None:
        """Trailing ``&  `` (with trailing whitespace) inside bash fence is still detected."""
        content = '```bash\npython3 script.py &  \n```\n'
        marketplace_root, _ = _make_skill_md(tmp_path, content)
        findings = analyze_bash_chain_shapes_in_skills(marketplace_root)
        bg_findings = [f for f in findings if f['chain_type'] == 'background']
        assert len(bg_findings) == 1


# ===========================================================================
# (d) Non-detection: prose lines are NOT scanned
# ===========================================================================


class TestProseNotScanned:
    """Lines outside bash/sh fenced blocks are not scanned."""

    def test_and_and_in_narrative_prose_not_flagged(self, tmp_path: Path) -> None:
        content = 'Run cmd1 && cmd2 together.\n'
        marketplace_root, _ = _make_skill_md(tmp_path, content)
        assert analyze_bash_chain_shapes_in_skills(marketplace_root) == []

    def test_and_and_in_json_fence_not_flagged(self, tmp_path: Path) -> None:
        content = '```json\n{"key": "val && other"}\n```\n'
        marketplace_root, _ = _make_skill_md(tmp_path, content)
        assert analyze_bash_chain_shapes_in_skills(marketplace_root) == []

    def test_and_and_in_markdown_fence_not_flagged(self, tmp_path: Path) -> None:
        content = '```markdown\n```bash\ncmd1 && cmd2\n```\n```\n'
        marketplace_root, _ = _make_skill_md(tmp_path, content)
        assert analyze_bash_chain_shapes_in_skills(marketplace_root) == []

    def test_and_and_in_text_fence_not_flagged(self, tmp_path: Path) -> None:
        content = '```text\ncmd1 && cmd2\n```\n'
        marketplace_root, _ = _make_skill_md(tmp_path, content)
        assert analyze_bash_chain_shapes_in_skills(marketplace_root) == []


# ===========================================================================
# (e) Comment lines inside bash fences are exempt
# ===========================================================================


class TestCommentLinesExempt:
    """Lines starting with ``#`` inside bash fences are skipped."""

    def test_comment_line_with_and_and_is_exempt(self, tmp_path: Path) -> None:
        """A ``# cmd1 && cmd2`` comment line produces no finding."""
        content = '```bash\n# Run: cmd1 && cmd2\npython3 cmd.py\n```\n'
        marketplace_root, _ = _make_skill_md(tmp_path, content)
        findings = analyze_bash_chain_shapes_in_skills(marketplace_root)
        assert findings == []

    def test_comment_line_with_semicolon_is_exempt(self, tmp_path: Path) -> None:
        """A ``# cmd1; cmd2`` comment line produces no finding."""
        content = '```bash\n# example: cmd1; cmd2\npython3 cmd.py\n```\n'
        marketplace_root, _ = _make_skill_md(tmp_path, content)
        findings = analyze_bash_chain_shapes_in_skills(marketplace_root)
        assert findings == []

    def test_indented_comment_line_is_exempt(self, tmp_path: Path) -> None:
        """A comment line with leading whitespace is still exempt."""
        content = '```bash\n  # Run: cmd1 && cmd2\npython3 cmd.py\n```\n'
        marketplace_root, _ = _make_skill_md(tmp_path, content)
        findings = analyze_bash_chain_shapes_in_skills(marketplace_root)
        assert findings == []

    def test_non_comment_line_with_and_and_is_still_flagged(self, tmp_path: Path) -> None:
        """A non-comment line with ``&&`` is still flagged."""
        content = '```bash\ncmd1 && cmd2\n# comment\n```\n'
        marketplace_root, _ = _make_skill_md(tmp_path, content)
        findings = analyze_bash_chain_shapes_in_skills(marketplace_root)
        assert len(findings) >= 1
        assert any(f['chain_type'] == 'and_and' for f in findings)


# ===========================================================================
# (f) Inline-code spans inside bash fences are exempt
# ===========================================================================


class TestBacktickSpanInBashFence:
    """Backtick spans inside bash fences are bash command substitutions, not markdown inline-code.

    Unlike prose sections, backticks inside a fenced bash block denote command substitution
    (e.g. ``result=`cmd1 && cmd2```) and are therefore NOT exempt from chain-shape detection.
    """

    def test_and_and_in_backtick_span_inside_bash_fence_is_flagged(self, tmp_path: Path) -> None:
        """``&&`` inside a backtick span inside a bash fence is a command substitution and IS flagged."""
        content = '```bash\nresult=`cmd1 && cmd2`\n```\n'
        marketplace_root, _ = _make_skill_md(tmp_path, content)
        findings = analyze_bash_chain_shapes_in_skills(marketplace_root)
        and_and_findings = [f for f in findings if f['chain_type'] == 'and_and']
        assert len(and_and_findings) >= 1

    def test_and_and_comment_with_backtick_is_skipped(self, tmp_path: Path) -> None:
        """A comment line containing a backtick span with ``&&`` is still skipped (comment exemption)."""
        content = '```bash\n# document: `cmd1 && cmd2` is forbidden\npython3 safe.py\n```\n'
        marketplace_root, _ = _make_skill_md(tmp_path, content)
        findings = analyze_bash_chain_shapes_in_skills(marketplace_root)
        assert findings == []

    def test_and_and_bare_is_flagged_alongside_backtick_span(
        self, tmp_path: Path
    ) -> None:
        """Both the bare ``&&`` and any ``&&`` inside a backtick span on the same line are flagged."""
        content = '```bash\ncmd1 && cmd2  # see `a && b` doc\n```\n'
        marketplace_root, _ = _make_skill_md(tmp_path, content)
        findings = analyze_bash_chain_shapes_in_skills(marketplace_root)
        and_and_findings = [f for f in findings if f['chain_type'] == 'and_and']
        # cmd1 && cmd2 is flagged; `a && b` in a comment-suffix backtick is also flagged.
        assert len(and_and_findings) >= 1


# ===========================================================================
# (g) Backslash-escaped \& is NOT a trailing-& finding
# ===========================================================================


class TestBackslashEscapedAmpersand:
    """A ``\\&`` (backslash-escaped ampersand) is not a trailing-& finding."""

    def test_backslash_ampersand_is_not_background_dispatch(self, tmp_path: Path) -> None:
        """A trailing backslash-escaped ampersand does not trigger a background-dispatch finding."""
        content = '```bash\necho "hello" \\&\n```\n'
        marketplace_root, _ = _make_skill_md(tmp_path, content)
        findings = analyze_bash_chain_shapes_in_skills(marketplace_root)
        bg_findings = [f for f in findings if f['chain_type'] == 'background']
        assert bg_findings == []


# ===========================================================================
# (h) Finding shape validation
# ===========================================================================


class TestFindingShape:
    """Findings carry the expected shape fields."""

    def test_and_and_finding_shape(self, tmp_path: Path) -> None:
        """``&&`` finding carries all required fields."""
        content = '```bash\ncmd1 && cmd2\n```\n'
        marketplace_root, md_path = _make_skill_md(tmp_path, content)
        findings = analyze_bash_chain_shapes_in_skills(marketplace_root)
        assert len(findings) >= 1
        f = next(f for f in findings if f['chain_type'] == 'and_and')
        assert f['rule_id'] == RULE_ID
        assert f['type'] == 'bash_chain_shapes_in_skills'
        assert f['rule'] == 'analyze_bash_chain_shapes_in_skills'
        assert f['file'] == str(md_path)
        assert isinstance(f['line'], int) and f['line'] >= 1
        assert f['severity'] == 'error'
        assert f['fixable'] is False
        assert 'snippet' in f
        assert 'description' in f
        assert 'chain_type' in f

    def test_line_number_correct(self, tmp_path: Path) -> None:
        """Line number reported correctly relative to file start."""
        content = '# Title\n\nSome prose.\n\n```bash\ncmd1 && cmd2\n```\n'
        marketplace_root, _ = _make_skill_md(tmp_path, content)
        findings = analyze_bash_chain_shapes_in_skills(marketplace_root)
        and_and_findings = [f for f in findings if f['chain_type'] == 'and_and']
        assert len(and_and_findings) == 1
        assert and_and_findings[0]['line'] == 6  # 6th line of file


# ===========================================================================
# (i) Multiple findings on a single line
# ===========================================================================


class TestMultipleFindingsPerLine:
    """Multiple compound operators on a single line produce multiple findings."""

    def test_and_and_and_semicolon_on_same_line(self, tmp_path: Path) -> None:
        """``cmd1; cmd2 && cmd3`` produces findings for both operator types."""
        content = '```bash\ncmd1; cmd2 && cmd3\n```\n'
        marketplace_root, _ = _make_skill_md(tmp_path, content)
        findings = analyze_bash_chain_shapes_in_skills(marketplace_root)
        types = {f['chain_type'] for f in findings}
        assert 'semicolon' in types
        assert 'and_and' in types


# ===========================================================================
# (j) Clean baseline: files with no violations
# ===========================================================================


class TestCleanBaseline:
    """Files and trees with no compound-chain violations produce no findings."""

    def test_clean_bash_fence_produces_no_findings(self, tmp_path: Path) -> None:
        content = (
            '```bash\n'
            'python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \\\n'
            '  work --plan-id my-plan --level INFO --message "hello world"\n'
            '```\n'
        )
        marketplace_root, _ = _make_skill_md(tmp_path, content)
        assert analyze_bash_chain_shapes_in_skills(marketplace_root) == []

    def test_missing_plan_marshall_dir_returns_empty(self, tmp_path: Path) -> None:
        """marketplace_root without plan-marshall/ returns empty list."""
        marketplace_root = tmp_path / 'empty'
        marketplace_root.mkdir()
        assert analyze_bash_chain_shapes_in_skills(marketplace_root) == []

    def test_multiple_skill_files_scanned(self, tmp_path: Path) -> None:
        """Multiple *.md files are all scanned."""
        base = tmp_path / 'plan-marshall' / 'skills'

        skill_a = base / 'skill-a'
        skill_a.mkdir(parents=True)
        (skill_a / 'SKILL.md').write_text('```bash\ncmd1 && cmd2\n```\n', encoding='utf-8')

        skill_b = base / 'skill-b'
        skill_b.mkdir(parents=True)
        (skill_b / 'SKILL.md').write_text('Clean content.\n', encoding='utf-8')

        findings = analyze_bash_chain_shapes_in_skills(tmp_path)
        and_and_findings = [f for f in findings if f['chain_type'] == 'and_and']
        assert len(and_and_findings) == 1

    def test_agents_directory_scanned(self, tmp_path: Path) -> None:
        """Files under plan-marshall/agents/ are scanned."""
        marketplace_root, _ = _make_agent_md(tmp_path, '```bash\ncmd1 && cmd2\n```\n')
        findings = analyze_bash_chain_shapes_in_skills(marketplace_root)
        assert any(f['chain_type'] == 'and_and' for f in findings)
