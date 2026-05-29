# ruff: noqa: I001, E402
"""Tests for the ``shell-substitution-in-skills`` rule analyzer.

The analyzer detects ``$(`` command-substitution patterns inside plan-marshall
skill markdown files. Such patterns violate the dev-agent-behavior-rules
"Bash: no shell constructs" hard rule.

Two documentary contexts are exempt:

1. **Inline-code span** — ``$(`` inside a markdown inline-code span
   (`` `...` ``). The structural placement inside the span makes the
   occurrence non-executable; no surrounding-keyword check is required.

2. **Verbatim-source fenced block** — ``$(`` inside a fenced block whose
   info-string is ``markdown`` or ``text``. These hold verbatim examples
   that subagents do not interpret as runnable commands.

Every other occurrence — narrative prose, bash/sh fenced blocks, other
code-language fenced blocks, unfenced blocks — is a finding.

Test layers:
  * (a) Detection inside a fenced bash block.
  * (b) Detection in non-bash narrative prose.
  * (c) Exemption inside an inline-code span, even on a line with
        rule-documentation keywords (forbidden, must not, anti-pattern, rule).
  * (d) Exemption inside a ``markdown`` info-string fenced block.
  * (e) ``test_real_marketplace_has_zero_findings`` invariant: the actual
        marketplace/bundles/plan-marshall/skills/ tree produces no findings.
"""

from pathlib import Path

from conftest import load_script_module

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent


def _load_module(name: str, filename: str):
    return load_script_module('pm-plugin-development', 'plugin-doctor', filename, name)


_asss = _load_module(
    '_analyze_shell_substitution_in_skills',
    '_analyze_shell_substitution_in_skills.py',
)

analyze_shell_substitution_in_skills = _asss.analyze_shell_substitution_in_skills
RULE_ID = _asss.RULE_ID


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

MARKETPLACE_BUNDLES = PROJECT_ROOT / 'marketplace' / 'bundles'


def _make_skill_md(tmp_path: Path, content: str) -> tuple[Path, Path]:
    """Create a ``plan-marshall/skills/test-skill/SKILL.md`` under ``tmp_path``.

    Mirrors the actual layout scanned by ``_skill_markdown_targets``:
    ``marketplace_root/plan-marshall/skills/**/*.md``.

    Returns ``(marketplace_root, md_path)``.
    """
    skill_dir = (
        tmp_path / 'plan-marshall' / 'skills' / 'test-skill'
    )
    skill_dir.mkdir(parents=True)
    md = skill_dir / 'SKILL.md'
    md.write_text(content, encoding='utf-8')
    return tmp_path, md


# ===========================================================================
# (a) Detection inside fenced bash block
# ===========================================================================


class TestDetectionInBashFence:
    """$(  inside a fenced bash block must be flagged."""

    def test_dollar_paren_in_bash_fence_triggers_finding(self, tmp_path: Path) -> None:
        """$(  inside ```bash``` block is a finding."""
        content = '```bash\nresult=$(git rev-parse HEAD)\n```\n'
        marketplace_root, _ = _make_skill_md(tmp_path, content)
        findings = analyze_shell_substitution_in_skills(marketplace_root)
        assert len(findings) == 1
        assert findings[0]['rule_id'] == RULE_ID

    def test_dollar_paren_in_sh_fence_triggers_finding(self, tmp_path: Path) -> None:
        """$(  inside ```sh``` block is a finding (sh treated same as bash)."""
        content = '```sh\nval=$(echo hello)\n```\n'
        marketplace_root, _ = _make_skill_md(tmp_path, content)
        findings = analyze_shell_substitution_in_skills(marketplace_root)
        assert len(findings) == 1

    def test_dollar_paren_in_python_fence_triggers_finding(self, tmp_path: Path) -> None:
        """$(  inside a non-bash code fence is still a finding."""
        content = '```python\n# shell call: $(some_cmd)\n```\n'
        marketplace_root, _ = _make_skill_md(tmp_path, content)
        findings = analyze_shell_substitution_in_skills(marketplace_root)
        assert len(findings) == 1

    def test_finding_shape_in_bash_fence(self, tmp_path: Path) -> None:
        """Finding carries expected shape fields."""
        content = '```bash\noutput=$(cat file.txt)\n```\n'
        marketplace_root, md_path = _make_skill_md(tmp_path, content)
        findings = analyze_shell_substitution_in_skills(marketplace_root)
        assert len(findings) == 1
        f = findings[0]
        assert f['rule_id'] == RULE_ID
        assert f['type'] == 'shell_substitution_in_skills'
        assert f['rule'] == 'analyze_shell_substitution_in_skills'
        assert f['file'] == str(md_path)
        assert isinstance(f['line'], int) and f['line'] >= 1
        assert f['severity'] == 'error'
        assert f['fixable'] is False
        assert 'snippet' in f
        assert 'description' in f

    def test_multiple_dollar_paren_in_fence_produces_multiple_findings(
        self, tmp_path: Path
    ) -> None:
        """Two ``$(`` on the same fenced-block line produce two findings."""
        content = '```bash\na=$(cmd1) b=$(cmd2)\n```\n'
        marketplace_root, _ = _make_skill_md(tmp_path, content)
        findings = analyze_shell_substitution_in_skills(marketplace_root)
        assert len(findings) == 2


# ===========================================================================
# (b) Detection in non-bash narrative line
# ===========================================================================


class TestDetectionInNarrativeProse:
    """$(  appearing in plain narrative prose (outside any fence or inline code)
    must be flagged."""

    def test_dollar_paren_in_narrative_triggers_finding(self, tmp_path: Path) -> None:
        """Bare $(  in prose is a finding."""
        content = 'Do not use $(git log) in your command strings.\n'
        marketplace_root, _ = _make_skill_md(tmp_path, content)
        findings = analyze_shell_substitution_in_skills(marketplace_root)
        assert len(findings) == 1
        assert findings[0]['rule_id'] == RULE_ID

    def test_dollar_paren_line_number_in_narrative(self, tmp_path: Path) -> None:
        """Line number is correctly reported for narrative occurrences."""
        content = 'First line.\nSecond line with $(subshell) call.\nThird line.\n'
        marketplace_root, _ = _make_skill_md(tmp_path, content)
        findings = analyze_shell_substitution_in_skills(marketplace_root)
        assert len(findings) == 1
        assert findings[0]['line'] == 2

    def test_multiple_dollar_paren_in_narrative(self, tmp_path: Path) -> None:
        """Two ``$(`` on the same narrative line produce two findings."""
        content = 'The pattern $(a) and $(b) are both forbidden.\n'
        marketplace_root, _ = _make_skill_md(tmp_path, content)
        findings = analyze_shell_substitution_in_skills(marketplace_root)
        assert len(findings) == 2

    def test_clean_narrative_no_finding(self, tmp_path: Path) -> None:
        """Narrative prose without ``$(`` produces no findings."""
        content = (
            '# Standards document\n\n'
            'Use the executor script to run commands.\n\n'
            'No shell substitution here.\n'
        )
        marketplace_root, _ = _make_skill_md(tmp_path, content)
        findings = analyze_shell_substitution_in_skills(marketplace_root)
        assert findings == []


# ===========================================================================
# (c) Exemption inside documentary inline-code span (keyword-line variant)
# ===========================================================================


class TestExemptionInInlineCodeSpan:
    """$(  inside a backtick inline-code span is exempt, even when the line
    contains rule-documentation keywords such as 'forbidden', 'must not',
    'anti-pattern', or 'rule'."""

    def test_dollar_paren_in_inline_code_is_exempt(self, tmp_path: Path) -> None:
        """$(  inside backtick span produces no finding."""
        content = 'Use `$(git rev-parse HEAD)` carefully.\n'
        marketplace_root, _ = _make_skill_md(tmp_path, content)
        findings = analyze_shell_substitution_in_skills(marketplace_root)
        assert findings == []

    def test_inline_code_exempt_on_forbidden_keyword_line(self, tmp_path: Path) -> None:
        """Inline-code span is exempt even when line mentions 'forbidden'."""
        content = 'The anti-pattern `$(...)` is forbidden in skill docs.\n'
        marketplace_root, _ = _make_skill_md(tmp_path, content)
        findings = analyze_shell_substitution_in_skills(marketplace_root)
        assert findings == []

    def test_inline_code_exempt_on_must_not_line(self, tmp_path: Path) -> None:
        """Inline-code span exempt when line contains 'must not'."""
        content = 'You must not write `$(some_command)` in skill markdown.\n'
        marketplace_root, _ = _make_skill_md(tmp_path, content)
        findings = analyze_shell_substitution_in_skills(marketplace_root)
        assert findings == []

    def test_inline_code_exempt_on_anti_pattern_line(self, tmp_path: Path) -> None:
        """Inline-code span exempt when line contains 'anti-pattern'."""
        content = '**Anti-pattern**: `$(git log)` expands in the shell.\n'
        marketplace_root, _ = _make_skill_md(tmp_path, content)
        findings = analyze_shell_substitution_in_skills(marketplace_root)
        assert findings == []

    def test_inline_code_exempt_on_rule_line(self, tmp_path: Path) -> None:
        """Inline-code span exempt when line mentions 'rule'."""
        content = 'This rule forbids using `$(...)` constructs.\n'
        marketplace_root, _ = _make_skill_md(tmp_path, content)
        findings = analyze_shell_substitution_in_skills(marketplace_root)
        assert findings == []

    def test_dollar_paren_outside_inline_code_on_same_line_is_flagged(
        self, tmp_path: Path
    ) -> None:
        """Only the span-internal occurrence is exempt; the bare one is flagged."""
        content = 'Use `$(cmd)` not $(cmd) directly.\n'
        marketplace_root, _ = _make_skill_md(tmp_path, content)
        findings = analyze_shell_substitution_in_skills(marketplace_root)
        # The bare $(cmd) after "not" is outside the span and must be flagged
        assert len(findings) == 1


# ===========================================================================
# (d) Exemption inside markdown/text info-string fenced block
# ===========================================================================


class TestExemptionInDocumentaryFence:
    """$(  inside fenced blocks with info-string ``markdown`` or ``text`` is
    exempt — these hold verbatim source examples."""

    def test_dollar_paren_in_markdown_fence_is_exempt(self, tmp_path: Path) -> None:
        """$(  inside ```markdown``` block produces no finding."""
        content = '```markdown\n```bash\nresult=$(git rev-parse HEAD)\n```\n```\n'
        marketplace_root, _ = _make_skill_md(tmp_path, content)
        findings = analyze_shell_substitution_in_skills(marketplace_root)
        assert findings == []

    def test_dollar_paren_in_text_fence_is_exempt(self, tmp_path: Path) -> None:
        """$(  inside ```text``` block produces no finding."""
        content = '```text\noutput=$(whoami)\n```\n'
        marketplace_root, _ = _make_skill_md(tmp_path, content)
        findings = analyze_shell_substitution_in_skills(marketplace_root)
        assert findings == []

    def test_markdown_fence_case_insensitive(self, tmp_path: Path) -> None:
        """Info-string matching is case-insensitive (``MARKDOWN`` still exempt)."""
        content = '```MARKDOWN\nresult=$(cmd)\n```\n'
        marketplace_root, _ = _make_skill_md(tmp_path, content)
        findings = analyze_shell_substitution_in_skills(marketplace_root)
        assert findings == []

    def test_text_fence_case_insensitive(self, tmp_path: Path) -> None:
        """Info-string matching is case-insensitive (``TEXT`` still exempt)."""
        content = '```TEXT\nresult=$(cmd)\n```\n'
        marketplace_root, _ = _make_skill_md(tmp_path, content)
        findings = analyze_shell_substitution_in_skills(marketplace_root)
        assert findings == []

    def test_bash_fence_not_exempt(self, tmp_path: Path) -> None:
        """``bash`` info-string is NOT in the exempt set — finding expected."""
        content = '```bash\nresult=$(cmd)\n```\n'
        marketplace_root, _ = _make_skill_md(tmp_path, content)
        findings = analyze_shell_substitution_in_skills(marketplace_root)
        assert len(findings) == 1

    def test_unfenced_block_not_exempt(self, tmp_path: Path) -> None:
        """No info-string (bare ````` ``` `````) is not exempt."""
        content = '```\nresult=$(cmd)\n```\n'
        marketplace_root, _ = _make_skill_md(tmp_path, content)
        findings = analyze_shell_substitution_in_skills(marketplace_root)
        assert len(findings) == 1


# ===========================================================================
# Clean-baseline: empty tree and no findings
# ===========================================================================


class TestCleanBaseline:
    """Edge cases and clean-tree baselines."""

    def test_missing_skills_directory_returns_empty(self, tmp_path: Path) -> None:
        """marketplace_root with no plan-marshall/skills/ dir returns empty list."""
        marketplace_root = tmp_path / 'empty-marketplace'
        marketplace_root.mkdir()
        findings = analyze_shell_substitution_in_skills(marketplace_root)
        assert findings == []

    def test_empty_skills_directory_returns_empty(self, tmp_path: Path) -> None:
        """plan-marshall/skills/ dir with no *.md files returns empty list."""
        skills_root = tmp_path / 'plan-marshall' / 'skills'
        skills_root.mkdir(parents=True)
        findings = analyze_shell_substitution_in_skills(tmp_path)
        assert findings == []

    def test_markdown_file_without_dollar_paren(self, tmp_path: Path) -> None:
        """Clean markdown file with no $(  produces no findings."""
        content = (
            '# Skill\n\n'
            'Run the executor:\n\n'
            '```bash\n'
            'python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \\\n'
            '  work --plan-id my-plan --level INFO --message "hello world"\n'
            '```\n\n'
            'No substitutions here.\n'
        )
        marketplace_root, _ = _make_skill_md(tmp_path, content)
        findings = analyze_shell_substitution_in_skills(marketplace_root)
        assert findings == []

    def test_multiple_skill_files_scanned(self, tmp_path: Path) -> None:
        """Multiple *.md files under plan-marshall/skills/ are all scanned."""
        base = tmp_path / 'plan-marshall' / 'skills'

        skill_a = base / 'skill-a'
        skill_a.mkdir(parents=True)
        (skill_a / 'SKILL.md').write_text(
            '```bash\nresult=$(cmd_a)\n```\n', encoding='utf-8'
        )

        skill_b = base / 'skill-b'
        skill_b.mkdir(parents=True)
        (skill_b / 'SKILL.md').write_text(
            'Clean content, no issues.\n', encoding='utf-8'
        )

        skill_c = base / 'skill-c'
        skill_c.mkdir(parents=True)
        (skill_c / 'SKILL.md').write_text(
            'Another violation: $(cmd_c) here.\n', encoding='utf-8'
        )

        findings = analyze_shell_substitution_in_skills(tmp_path)
        assert len(findings) == 2


# ===========================================================================
# (e) Real-marketplace invariant: zero findings against actual skills tree
# ===========================================================================


class TestRealMarketplaceHasZeroFindings:
    """Invariant: the actual marketplace/bundles tree has no
    shell-substitution violations in plan-marshall skill markdown."""

    def test_real_marketplace_has_zero_findings(self) -> None:
        """Scan the real marketplace/bundles directory — must return empty list.

        This invariant confirms that TASK-002 (the implementation) did not
        introduce any ``$(`` violations into the plan-marshall skills tree, and
        that no pre-existing violations exist.
        """
        assert MARKETPLACE_BUNDLES.is_dir(), (
            f'Marketplace bundles directory not found: {MARKETPLACE_BUNDLES}'
        )
        findings = analyze_shell_substitution_in_skills(MARKETPLACE_BUNDLES)
        # Surface actionable detail on failure
        if findings:
            lines = [
                f"  {f['file']}:{f['line']} — {f['snippet']!r}"
                for f in findings
            ]
            detail = '\n'.join(lines)
            raise AssertionError(
                f'Expected zero shell-substitution findings in the real marketplace, '
                f'but got {len(findings)}:\n{detail}'
            )
        assert findings == []
