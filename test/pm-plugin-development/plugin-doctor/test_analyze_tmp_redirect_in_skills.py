# ruff: noqa: I001, E402
"""Unit tests for _analyze_tmp_redirect_in_skills.py.

Covers:
- Detection of ``> /tmp/…`` (overwrite) inside bash fences
- Detection of ``>> /tmp/…`` (append) inside bash fences
- Detection of ``> /var/tmp/…`` and ``>> /var/tmp/…`` variants
- Prose lines outside fenced blocks are NOT scanned
- Comment lines (``#``) inside bash fences are exempt
- Backtick spans inside bash fences are command substitutions and ARE scanned (not exempt)
- Finding shape: all required fields present and correctly typed
- Multiple findings on the same line (two redirects)
- Clean baseline: markdown with no tmp redirects produces no findings
"""
from pathlib import Path

from conftest import load_script_module


def _load_module(name: str, filename: str):
    return load_script_module('pm-plugin-development', 'plugin-doctor', filename, name)


_atrs = _load_module(
    '_analyze_tmp_redirect_in_skills',
    '_analyze_tmp_redirect_in_skills.py',
)
analyze_tmp_redirect_in_skills = _atrs.analyze_tmp_redirect_in_skills
RULE_ID = _atrs.RULE_ID
FINDING_TYPE = _atrs.FINDING_TYPE


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_skill_md(tmp_path: Path, content: str) -> Path:
    """Create a fake plan-marshall skill markdown file under tmp_path.

    Replicates the directory structure that the scanner walks:
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


# ---------------------------------------------------------------------------
# Overwrite redirect (> /tmp/)
# ---------------------------------------------------------------------------


class TestOverwriteTmpRedirect:
    def test_overwrite_tmp_detected(self, tmp_path):
        content = (
            'Some prose.\n'
            '```bash\n'
            'python3 script.py > /tmp/output.json\n'
            '```\n'
        )
        _make_skill_md(tmp_path, content)
        findings = analyze_tmp_redirect_in_skills(tmp_path)
        assert len(findings) == 1
        assert findings[0]['redirect_type'] == 'overwrite'

    def test_overwrite_var_tmp_detected(self, tmp_path):
        content = (
            '```bash\n'
            'cat input > /var/tmp/scratch.txt\n'
            '```\n'
        )
        _make_skill_md(tmp_path, content)
        findings = analyze_tmp_redirect_in_skills(tmp_path)
        assert len(findings) == 1
        assert findings[0]['target_prefix'] == '/var/tmp/'

    def test_overwrite_tmp_in_sh_fence(self, tmp_path):
        content = (
            '```sh\n'
            'echo hello > /tmp/hello.txt\n'
            '```\n'
        )
        _make_skill_md(tmp_path, content)
        findings = analyze_tmp_redirect_in_skills(tmp_path)
        assert len(findings) == 1
        assert findings[0]['redirect_type'] == 'overwrite'


# ---------------------------------------------------------------------------
# Append redirect (>> /tmp/)
# ---------------------------------------------------------------------------


class TestAppendTmpRedirect:
    def test_append_tmp_detected(self, tmp_path):
        content = (
            '```bash\n'
            'echo line >> /tmp/log.txt\n'
            '```\n'
        )
        _make_skill_md(tmp_path, content)
        findings = analyze_tmp_redirect_in_skills(tmp_path)
        assert len(findings) == 1
        assert findings[0]['redirect_type'] == 'append'

    def test_append_var_tmp_detected(self, tmp_path):
        content = (
            '```bash\n'
            'python3 tool.py >> /var/tmp/result.txt\n'
            '```\n'
        )
        _make_skill_md(tmp_path, content)
        findings = analyze_tmp_redirect_in_skills(tmp_path)
        assert len(findings) == 1
        assert findings[0]['redirect_type'] == 'append'
        assert findings[0]['target_prefix'] == '/var/tmp/'


# ---------------------------------------------------------------------------
# Prose lines outside fenced blocks
# ---------------------------------------------------------------------------


class TestProseNotScanned:
    def test_prose_redirect_not_flagged(self, tmp_path):
        content = (
            'Use ``> /tmp/output.json`` as a redirect target.\n'
            'Another line with > /tmp/data.txt mention.\n'
        )
        _make_skill_md(tmp_path, content)
        findings = analyze_tmp_redirect_in_skills(tmp_path)
        assert findings == []

    def test_non_bash_fence_not_scanned(self, tmp_path):
        content = (
            '```python\n'
            '# redirect\n'
            'open("/tmp/out.txt", "w")\n'
            '```\n'
        )
        _make_skill_md(tmp_path, content)
        findings = analyze_tmp_redirect_in_skills(tmp_path)
        assert findings == []

    def test_text_fence_not_scanned(self, tmp_path):
        content = (
            '```text\n'
            'cmd > /tmp/out.txt\n'
            '```\n'
        )
        _make_skill_md(tmp_path, content)
        findings = analyze_tmp_redirect_in_skills(tmp_path)
        assert findings == []


# ---------------------------------------------------------------------------
# Comment-line exemption
# ---------------------------------------------------------------------------


class TestCommentLinesExempt:
    def test_comment_line_not_flagged(self, tmp_path):
        content = (
            '```bash\n'
            '# cmd > /tmp/output.txt\n'
            '```\n'
        )
        _make_skill_md(tmp_path, content)
        findings = analyze_tmp_redirect_in_skills(tmp_path)
        assert findings == []

    def test_indented_comment_line_not_flagged(self, tmp_path):
        content = (
            '```bash\n'
            '  # echo data >> /tmp/log.txt\n'
            '```\n'
        )
        _make_skill_md(tmp_path, content)
        findings = analyze_tmp_redirect_in_skills(tmp_path)
        assert findings == []


# ---------------------------------------------------------------------------
# Backtick span behaviour inside bash fences
# ---------------------------------------------------------------------------


class TestBacktickSpanInBashFence:
    """Backtick spans inside bash fences are command substitutions, not markdown inline-code.

    They are scanned for /tmp/ redirects just like any other bash construct.
    """

    def test_redirect_inside_backtick_span_is_flagged(self, tmp_path):
        """A /tmp/ redirect inside a backtick command substitution IS flagged."""
        content = (
            '```bash\n'
            'echo `> /tmp/data.txt`\n'
            '```\n'
        )
        _make_skill_md(tmp_path, content)
        findings = analyze_tmp_redirect_in_skills(tmp_path)
        assert len(findings) == 1

    def test_redirect_outside_backtick_span_flagged(self, tmp_path):
        """A /tmp/ redirect outside a backtick span on the same line is also flagged."""
        content = (
            '```bash\n'
            'cmd `note` > /tmp/out.txt\n'
            '```\n'
        )
        _make_skill_md(tmp_path, content)
        findings = analyze_tmp_redirect_in_skills(tmp_path)
        assert len(findings) == 1


# ---------------------------------------------------------------------------
# Finding shape
# ---------------------------------------------------------------------------


class TestFindingShape:
    def test_required_fields_present(self, tmp_path):
        content = (
            '```bash\n'
            'python3 script.py > /tmp/out.json\n'
            '```\n'
        )
        _make_skill_md(tmp_path, content)
        findings = analyze_tmp_redirect_in_skills(tmp_path)
        assert len(findings) == 1
        f = findings[0]
        assert f['rule_id'] == RULE_ID
        assert f['type'] == FINDING_TYPE
        assert isinstance(f['file'], str)
        assert isinstance(f['line'], int)
        assert f['line'] == 2
        assert f['severity'] == 'error'
        assert f['fixable'] is False
        assert f['redirect_type'] in ('overwrite', 'append')
        assert f['target_prefix'] in ('/tmp/', '/var/tmp/')
        assert isinstance(f['snippet'], str)
        assert isinstance(f['description'], str)

    def test_line_number_correct(self, tmp_path):
        content = (
            'Some intro text.\n'
            '\n'
            '```bash\n'
            'echo data > /tmp/file.txt\n'
            '```\n'
        )
        _make_skill_md(tmp_path, content)
        findings = analyze_tmp_redirect_in_skills(tmp_path)
        assert len(findings) == 1
        assert findings[0]['line'] == 4

    def test_file_path_is_absolute(self, tmp_path):
        content = (
            '```bash\n'
            'cmd >> /tmp/log.txt\n'
            '```\n'
        )
        _make_skill_md(tmp_path, content)
        findings = analyze_tmp_redirect_in_skills(tmp_path)
        assert len(findings) == 1
        assert Path(findings[0]['file']).is_absolute()


# ---------------------------------------------------------------------------
# Multiple findings per line
# ---------------------------------------------------------------------------


class TestMultipleFindingsPerLine:
    def test_two_redirects_on_one_line(self, tmp_path):
        content = (
            '```bash\n'
            'cmd1 > /tmp/a.txt; cmd2 > /tmp/b.txt\n'
            '```\n'
        )
        _make_skill_md(tmp_path, content)
        findings = analyze_tmp_redirect_in_skills(tmp_path)
        assert len(findings) == 2
        assert all(f['redirect_type'] == 'overwrite' for f in findings)

    def test_mixed_append_and_overwrite_on_one_line(self, tmp_path):
        content = (
            '```bash\n'
            'cmd > /tmp/a.txt && cmd2 >> /tmp/b.txt\n'
            '```\n'
        )
        _make_skill_md(tmp_path, content)
        findings = analyze_tmp_redirect_in_skills(tmp_path)
        assert len(findings) == 2
        types = {f['redirect_type'] for f in findings}
        assert types == {'overwrite', 'append'}


# ---------------------------------------------------------------------------
# Agent markdown scanned
# ---------------------------------------------------------------------------


class TestAgentMarkdownScanned:
    def test_agent_md_is_scanned(self, tmp_path):
        content = (
            '```bash\n'
            'python3 agent.py > /tmp/result.json\n'
            '```\n'
        )
        _make_agent_md(tmp_path, content)
        findings = analyze_tmp_redirect_in_skills(tmp_path)
        assert len(findings) == 1

    def test_agent_md_clean_no_findings(self, tmp_path):
        content = (
            '```bash\n'
            'python3 agent.py --output .plan/temp/plan_id-result.json\n'
            '```\n'
        )
        _make_agent_md(tmp_path, content)
        findings = analyze_tmp_redirect_in_skills(tmp_path)
        assert findings == []


# ---------------------------------------------------------------------------
# Clean baseline
# ---------------------------------------------------------------------------


class TestCleanBaseline:
    def test_no_bash_fences_no_findings(self, tmp_path):
        content = (
            '# My Skill\n'
            '\n'
            'This skill does things.\n'
            '\n'
            'Reference: use `.plan/temp/plan_id-output.txt`\n'
        )
        _make_skill_md(tmp_path, content)
        findings = analyze_tmp_redirect_in_skills(tmp_path)
        assert findings == []

    def test_bash_fence_plan_temp_no_findings(self, tmp_path):
        content = (
            '```bash\n'
            'python3 script.py --output .plan/temp/plan_id-result.json\n'
            '```\n'
        )
        _make_skill_md(tmp_path, content)
        findings = analyze_tmp_redirect_in_skills(tmp_path)
        assert findings == []

    def test_bash_fence_pipe_no_findings(self, tmp_path):
        content = (
            '```bash\n'
            'python3 script.py | grep pattern\n'
            '```\n'
        )
        _make_skill_md(tmp_path, content)
        findings = analyze_tmp_redirect_in_skills(tmp_path)
        assert findings == []

    def test_empty_marketplace_root_no_findings(self, tmp_path):
        # No plan-marshall bundle directory at all
        findings = analyze_tmp_redirect_in_skills(tmp_path)
        assert findings == []
