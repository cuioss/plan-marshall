# ruff: noqa: I001, E402
"""Unit tests for _analyze_skill_relative_temp_path.py.

Covers:
- Detection of a relative ``.plan/temp/…`` path consumed by ``git -C … commit -F``
  inside bash/sh fences
- Worktree-absolute ``-F {worktree_path}/.plan/temp/…`` form is NOT flagged
- ``.plan/temp`` references NOT combined with ``git -C`` are NOT flagged
- ``git -C … commit -F`` with a non-``.plan/temp`` ``-F`` argument is NOT flagged
- Prose lines outside fenced blocks are NOT scanned
- Non-bash fences (python, text) are NOT scanned
- Comment lines (``#``) inside bash fences are exempt
- Finding shape: all required fields present and correctly typed
- Multiple findings across lines / a clean baseline produces no findings
- Agent and command markdown are scanned alongside skill markdown
"""
from pathlib import Path

from conftest import load_script_module


def _load_module(name: str, filename: str):
    return load_script_module('pm-plugin-development', 'plugin-doctor', filename, name)


_asrtp = _load_module(
    '_analyze_skill_relative_temp_path',
    '_analyze_skill_relative_temp_path.py',
)
analyze_skill_relative_temp_path = _asrtp.analyze_skill_relative_temp_path
RULE_ID = _asrtp.RULE_ID
RULE_NAME = _asrtp.RULE_NAME
FINDING_TYPE = _asrtp.FINDING_TYPE


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


def _make_command_md(tmp_path: Path, content: str) -> Path:
    """Create a fake plan-marshall command markdown file under tmp_path."""
    commands_dir = tmp_path / 'plan-marshall' / 'commands'
    commands_dir.mkdir(parents=True, exist_ok=True)
    md = commands_dir / 'test-command.md'
    md.write_text(content, encoding='utf-8')
    return md


# ---------------------------------------------------------------------------
# Detection: relative .plan/temp consumed by git -C ... commit -F
# ---------------------------------------------------------------------------


class TestRelativeTempGitCDetected:
    def test_relative_temp_commit_f_detected(self, tmp_path):
        content = (
            'Some prose.\n'
            '```bash\n'
            'git -C {worktree_path} commit -F .plan/temp/{plan_id}-commit-msg.txt\n'
            '```\n'
        )
        _make_skill_md(tmp_path, content)
        findings = analyze_skill_relative_temp_path(tmp_path)
        assert len(findings) == 1
        assert findings[0]['temp_path'] == '.plan/temp/{plan_id}-commit-msg.txt'

    def test_relative_temp_in_sh_fence(self, tmp_path):
        content = (
            '```sh\n'
            'git -C {worktree_path} commit -F .plan/temp/msg.txt\n'
            '```\n'
        )
        _make_skill_md(tmp_path, content)
        findings = analyze_skill_relative_temp_path(tmp_path)
        assert len(findings) == 1
        assert findings[0]['temp_path'] == '.plan/temp/msg.txt'

    def test_relative_temp_with_concrete_worktree_path(self, tmp_path):
        content = (
            '```bash\n'
            'git -C /tmp/wt commit -F .plan/temp/commit-msg.txt\n'
            '```\n'
        )
        _make_skill_md(tmp_path, content)
        findings = analyze_skill_relative_temp_path(tmp_path)
        assert len(findings) == 1
        assert findings[0]['temp_path'] == '.plan/temp/commit-msg.txt'


# ---------------------------------------------------------------------------
# Worktree-absolute form is NOT flagged
# ---------------------------------------------------------------------------


class TestWorktreeAbsoluteNotFlagged:
    def test_worktree_absolute_temp_not_flagged(self, tmp_path):
        content = (
            '```bash\n'
            'git -C {worktree_path} commit -F {worktree_path}/.plan/temp/msg.txt\n'
            '```\n'
        )
        _make_skill_md(tmp_path, content)
        findings = analyze_skill_relative_temp_path(tmp_path)
        assert findings == []


# ---------------------------------------------------------------------------
# .plan/temp NOT combined with git -C is NOT flagged
# ---------------------------------------------------------------------------


class TestPlanTempWithoutGitCNotFlagged:
    def test_plain_write_to_plan_temp_not_flagged(self, tmp_path):
        content = (
            '```bash\n'
            'python3 script.py --output .plan/temp/plan_id-result.json\n'
            '```\n'
        )
        _make_skill_md(tmp_path, content)
        findings = analyze_skill_relative_temp_path(tmp_path)
        assert findings == []

    def test_git_without_dash_c_not_flagged(self, tmp_path):
        content = (
            '```bash\n'
            'git commit -F .plan/temp/msg.txt\n'
            '```\n'
        )
        _make_skill_md(tmp_path, content)
        findings = analyze_skill_relative_temp_path(tmp_path)
        assert findings == []

    def test_git_c_commit_non_temp_message_not_flagged(self, tmp_path):
        content = (
            '```bash\n'
            'git -C {worktree_path} commit -F /var/folders/msg.txt\n'
            '```\n'
        )
        _make_skill_md(tmp_path, content)
        findings = analyze_skill_relative_temp_path(tmp_path)
        assert findings == []


# ---------------------------------------------------------------------------
# Prose / non-bash fences not scanned
# ---------------------------------------------------------------------------


class TestProseAndNonBashNotScanned:
    def test_prose_line_not_flagged(self, tmp_path):
        content = (
            'Run `git -C {worktree_path} commit -F .plan/temp/msg.txt` carefully.\n'
            'Another mention: git -C wt commit -F .plan/temp/other.txt here.\n'
        )
        _make_skill_md(tmp_path, content)
        findings = analyze_skill_relative_temp_path(tmp_path)
        assert findings == []

    def test_python_fence_not_scanned(self, tmp_path):
        content = (
            '```python\n'
            'subprocess.run(["git", "-C", wt, "commit", "-F", ".plan/temp/m.txt"])\n'
            '```\n'
        )
        _make_skill_md(tmp_path, content)
        findings = analyze_skill_relative_temp_path(tmp_path)
        assert findings == []

    def test_text_fence_not_scanned(self, tmp_path):
        content = (
            '```text\n'
            'git -C {worktree_path} commit -F .plan/temp/msg.txt\n'
            '```\n'
        )
        _make_skill_md(tmp_path, content)
        findings = analyze_skill_relative_temp_path(tmp_path)
        assert findings == []


# ---------------------------------------------------------------------------
# Comment-line exemption
# ---------------------------------------------------------------------------


class TestCommentLinesExempt:
    def test_comment_line_not_flagged(self, tmp_path):
        content = (
            '```bash\n'
            '# git -C {worktree_path} commit -F .plan/temp/msg.txt\n'
            '```\n'
        )
        _make_skill_md(tmp_path, content)
        findings = analyze_skill_relative_temp_path(tmp_path)
        assert findings == []

    def test_indented_comment_line_not_flagged(self, tmp_path):
        content = (
            '```bash\n'
            '  # git -C {worktree_path} commit -F .plan/temp/msg.txt\n'
            '```\n'
        )
        _make_skill_md(tmp_path, content)
        findings = analyze_skill_relative_temp_path(tmp_path)
        assert findings == []


# ---------------------------------------------------------------------------
# Finding shape
# ---------------------------------------------------------------------------


class TestFindingShape:
    def test_required_fields_present(self, tmp_path):
        content = (
            '```bash\n'
            'git -C {worktree_path} commit -F .plan/temp/commit-msg.txt\n'
            '```\n'
        )
        _make_skill_md(tmp_path, content)
        findings = analyze_skill_relative_temp_path(tmp_path)
        assert len(findings) == 1
        f = findings[0]
        assert f['rule_id'] == RULE_ID
        assert f['type'] == FINDING_TYPE
        assert f['rule'] == RULE_NAME
        assert isinstance(f['file'], str)
        assert isinstance(f['line'], int)
        assert f['line'] == 2
        assert f['severity'] == 'warning'
        assert f['fixable'] is False
        assert f['temp_path'] == '.plan/temp/commit-msg.txt'
        assert isinstance(f['snippet'], str)
        assert isinstance(f['description'], str)

    def test_line_number_correct(self, tmp_path):
        content = (
            'Some intro text.\n'
            '\n'
            '```bash\n'
            'git -C {worktree_path} commit -F .plan/temp/m.txt\n'
            '```\n'
        )
        _make_skill_md(tmp_path, content)
        findings = analyze_skill_relative_temp_path(tmp_path)
        assert len(findings) == 1
        assert findings[0]['line'] == 4

    def test_file_path_is_absolute(self, tmp_path):
        content = (
            '```bash\n'
            'git -C {worktree_path} commit -F .plan/temp/m.txt\n'
            '```\n'
        )
        _make_skill_md(tmp_path, content)
        findings = analyze_skill_relative_temp_path(tmp_path)
        assert len(findings) == 1
        assert Path(findings[0]['file']).is_absolute()


# ---------------------------------------------------------------------------
# Multiple findings
# ---------------------------------------------------------------------------


class TestMultipleFindings:
    def test_two_violations_across_lines(self, tmp_path):
        content = (
            '```bash\n'
            'git -C {worktree_path} commit -F .plan/temp/a.txt\n'
            'git -C {worktree_path} commit -F .plan/temp/b.txt\n'
            '```\n'
        )
        _make_skill_md(tmp_path, content)
        findings = analyze_skill_relative_temp_path(tmp_path)
        assert len(findings) == 2
        temp_paths = {f['temp_path'] for f in findings}
        assert temp_paths == {'.plan/temp/a.txt', '.plan/temp/b.txt'}


# ---------------------------------------------------------------------------
# Agent and command markdown scanned
# ---------------------------------------------------------------------------


class TestAgentAndCommandScanned:
    def test_agent_md_is_scanned(self, tmp_path):
        content = (
            '```bash\n'
            'git -C {worktree_path} commit -F .plan/temp/agent-msg.txt\n'
            '```\n'
        )
        _make_agent_md(tmp_path, content)
        findings = analyze_skill_relative_temp_path(tmp_path)
        assert len(findings) == 1

    def test_command_md_is_scanned(self, tmp_path):
        content = (
            '```bash\n'
            'git -C {worktree_path} commit -F .plan/temp/cmd-msg.txt\n'
            '```\n'
        )
        _make_command_md(tmp_path, content)
        findings = analyze_skill_relative_temp_path(tmp_path)
        assert len(findings) == 1


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
            'Reference: use `{worktree_path}/.plan/temp/msg.txt`\n'
        )
        _make_skill_md(tmp_path, content)
        findings = analyze_skill_relative_temp_path(tmp_path)
        assert findings == []

    def test_empty_marketplace_root_no_findings(self, tmp_path):
        # No plan-marshall bundle directory at all
        findings = analyze_skill_relative_temp_path(tmp_path)
        assert findings == []
