#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for git-workflow.py - consolidated git workflow script.

Tier 2 (direct import) tests with subprocess tests for CLI plumbing.
"""

from __future__ import annotations

import os
import re
import subprocess
from argparse import Namespace
from pathlib import Path

import pytest
from toon_parser import parse_toon

from conftest import get_script_path, load_script_module, run_script

# Script under test (for subprocess CLI plumbing tests)
SCRIPT_PATH = get_script_path('plan-marshall', 'workflow-integration-git', 'git-workflow.py')

# The entrypoint filename is kebab-case (git-workflow.py), which is not a
# valid Python module identifier — load it via importlib instead of `import`.
git_workflow = load_script_module('plan-marshall', 'workflow-integration-git', 'git-workflow.py', 'git_workflow')
_SKIP_DIRS = git_workflow._SKIP_DIRS
SAFE_ARTIFACT_PATTERNS = git_workflow.SAFE_ARTIFACT_PATTERNS
UNCERTAIN_ARTIFACT_PATTERNS = git_workflow.UNCERTAIN_ARTIFACT_PATTERNS
VALID_TYPES = git_workflow.VALID_TYPES

# ⛔ Vacuity guard — the vocabulary is production's, so emptying it there collects zero
# cases at the parametrize below and still reports green.
assert VALID_TYPES, 'git_workflow.VALID_TYPES is empty'
analyze_diff = git_workflow.analyze_diff
cmd_detect_artifacts = git_workflow.cmd_detect_artifacts
cmd_format_commit = git_workflow.cmd_format_commit
evaluate_source_commit_gate = git_workflow.evaluate_source_commit_gate
get_tracked_files = git_workflow.get_tracked_files
has_open_fix_task = git_workflow.has_open_fix_task
has_section6_record = git_workflow.has_section6_record
_source_gate_finding_texts = git_workflow._source_gate_finding_texts
is_plan_only_path = git_workflow.is_plan_only_path
is_source_commit = git_workflow.is_source_commit
scan_artifacts = git_workflow.scan_artifacts
wrap_text = git_workflow.wrap_text


def run_git_script(args: list) -> tuple:
    """Run git_workflow.py with args and return (stdout, stderr, returncode)."""
    result = run_script(SCRIPT_PATH, *args)
    return result.stdout, result.stderr, result.returncode


def _format_commit_args(**overrides) -> Namespace:
    """Build a cmd_format_commit Namespace with sensible defaults for unset fields."""
    fields = {
        'commit_type': 'feat',
        'scope': None,
        'subject': 'subject',
        'body': None,
        'breaking': None,
        'footer': None,
    }
    fields.update(overrides)
    return Namespace(**fields)


def _create_file(root: Path, relpath: str) -> None:
    """Create a file (with parents) within ``root``."""
    full = root / relpath
    full.parent.mkdir(parents=True, exist_ok=True)
    full.write_text('test')


def _git_init_with_identity(repo: Path) -> None:
    """Initialise a git repo with a throwaway committer identity."""
    subprocess.run(['git', 'init'], cwd=repo, capture_output=True)
    subprocess.run(['git', 'config', 'user.email', 'test@test.com'], cwd=repo, capture_output=True)
    subprocess.run(['git', 'config', 'user.name', 'Test'], cwd=repo, capture_output=True)


def _repo_with_live_worktree(root: Path, worktree_path: Path, branch: str = 'feature/EXAMPLE-PLAN') -> Path:
    """Init ``root`` as a repo with one commit and a linked worktree at ``worktree_path``.

    Models how plan-marshall runs a plan: in a linked git worktree that
    ``git ls-files`` treats as a separate-checkout boundary (it never
    enumerates the worktree's contents), while ``os.walk`` descends into it.
    Returns ``worktree_path`` for convenience.
    """
    _git_init_with_identity(root)
    _create_file(root, 'README.md')
    subprocess.run(['git', 'add', '.'], cwd=root, capture_output=True)
    subprocess.run(['git', 'commit', '-m', 'init'], cwd=root, capture_output=True)
    subprocess.run(['git', 'branch', branch], cwd=root, capture_output=True)
    worktree_path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(['git', 'worktree', 'add', str(worktree_path), branch], cwd=root, capture_output=True)
    return worktree_path


#: A running plan's live audit trail, sited directly under the scan root.
_PLAN_STATE_WORKLOG = '.plan/local/plans/EXAMPLE-PLAN/logs/work.log'


def _plan_worktree_scan_root(root: Path) -> None:
    """Model a plan worktree as the scan ROOT: live plan state plus a control artifact.

    Distinct from :func:`_repo_with_live_worktree`, which sites the plan checkout
    *beneath* the scan root where the nested-boundary pruning already covers it.
    Here the plan state is a plain directory directly under the root, so no
    boundary pruning applies and only the unconditional plan-state exclusion can
    keep it out of the offered buckets.
    """
    _git_init_with_identity(root)
    _create_file(root, 'README.md')
    subprocess.run(['git', 'add', 'README.md'], cwd=root, capture_output=True)
    subprocess.run(['git', 'commit', '-m', 'init'], cwd=root, capture_output=True)
    _create_file(root, _PLAN_STATE_WORKLOG)
    _create_file(root, 'scratch.temp')


def _assert_plan_state_excluded_control_safe(result: dict) -> None:
    """The plan's own work.log is offered nowhere, while the control still reaches ``safe``.

    The control assertion is the non-vacuity guard: an empty scan would satisfy
    the negative on its own, which is precisely the confusion this epic is named
    for.
    """
    offered = result['safe'] + result['uncertain']
    assert not any('work.log' in f for f in offered), (
        f"the scan root's own live plan state was offered for deletion: {offered}"
    )
    assert 'scratch.temp' in result['safe'], (
        f'control artifact missing from safe — the exclusion above would be vacuous on an empty scan: {result["safe"]}'
    )


# The identity an unconfigured checkout commits under. Owned by
# manage-run-config (COMMIT_TRAILER_*_DEFAULT) and documented in CLAUDE.md
# § "Commit Trailer"; restated here as the executable form of it.
DEFAULT_COAUTHOR_TRAILER = 'Co-Authored-By: plan-marshall <noreply@cuioss.de>'

# Assistant and vendor names that must never appear in a trailer, whatever the
# configured identity is. The trailer names the system that produced the commit,
# so any of these in one means the convention has been reverted somewhere.
FORBIDDEN_COAUTHOR_TOKENS = (
    'anthropic',
    'claude',
    'openai',
    'chatgpt',
    'gpt-',
    'copilot',
    'gemini',
    'codex',
    'cursor',
)

# Matches a trailer wherever it appears — in a commit template, a skill's worked
# example, or a test fixture's expected output — and captures the identity ONLY,
# not the line around it. Matching the whole line would flag prose that merely
# names a file (CLAUDE.md) beside a perfectly canonical trailer. Assembled from
# concatenated pieces so this pattern does not itself match the sweep.
_TRAILER_PATTERN = re.compile('Co-Authored' + r'-By:\s*[^<>\n]*<[^<>\n]*>')


def _repo_root() -> Path:
    """Repository root, resolved from git rather than from __file__ depth."""
    result = subprocess.run(
        ['git', 'rev-parse', '--show-toplevel'],
        cwd=Path(__file__).resolve().parent,
        capture_output=True,
        text=True,
        check=True,
    )
    return Path(result.stdout.strip())


def _tracked_trailer_lines() -> tuple[list[tuple[str, str]], int]:
    """Every stated co-author trailer in tracked files, with the files scanned.

    Returns ``(occurrences, files_scanned)`` where each occurrence is
    ``(repo-relative path, the trailer text)`` — the trailer alone, so
    surrounding prose cannot be mistaken for part of the identity.
    ``files_scanned`` is published so an empty or truncated sweep cannot pass as
    a clean result.

    A trailer carrying a ``{placeholder}`` is a composition template rather than
    a stated identity, and is excluded: the value it renders is decided at
    runtime, so judging the template against a literal identity would be a
    category error.
    """
    root = _repo_root()
    listing = subprocess.run(
        ['git', 'ls-files', '-z'],
        cwd=root,
        capture_output=True,
        text=True,
        check=True,
    )
    occurrences: list[tuple[str, str]] = []
    scanned = 0
    for rel in listing.stdout.split('\0'):
        if not rel:
            continue
        path = root / rel
        try:
            content = path.read_text(encoding='utf-8')
        except (OSError, UnicodeDecodeError):
            continue  # binary or unreadable — carries no trailer
        scanned += 1
        for match in _TRAILER_PATTERN.finditer(content):
            trailer = match.group(0)
            if '{' in trailer:
                continue
            occurrences.append((rel, trailer))
    return occurrences, scanned


class TestFormatCommit:
    """Test git_workflow.py format-commit via direct import."""

    def test_basic_format(self):
        """Basic commit message formatting."""
        result = cmd_format_commit(_format_commit_args(commit_type='feat', subject='add new feature'))

        assert result['type'] == 'feat'
        assert result['subject'] == 'add new feature'
        assert 'feat: add new feature' in result['formatted_message']
        assert result['status'] == 'success'

    def test_format_with_scope(self):
        """Commit message with scope."""
        result = cmd_format_commit(_format_commit_args(commit_type='fix', scope='auth', subject='fix login bug'))

        assert result['scope'] == 'auth'
        assert 'fix(auth):' in result['formatted_message']

    def test_format_with_body(self):
        """Commit message with body."""
        result = cmd_format_commit(
            _format_commit_args(commit_type='docs', subject='update readme', body='Added installation instructions')
        )

        assert result['body'] == 'Added installation instructions'

    def test_format_with_breaking_change(self):
        """Commit message with breaking change."""
        result = cmd_format_commit(
            _format_commit_args(commit_type='feat', subject='change api', breaking='API signature changed')
        )

        assert 'feat!:' in result['formatted_message']
        assert 'BREAKING CHANGE:' in result['formatted_message']

    def test_format_with_footer(self):
        """Commit message with footer."""
        result = cmd_format_commit(_format_commit_args(commit_type='fix', subject='fix crash', footer='Fixes #123'))

        assert 'Fixes #123' in result['formatted_message']

    @pytest.mark.parametrize('commit_type', sorted(VALID_TYPES))
    def test_valid_commit_type_accepted(self, commit_type):
        """Every valid commit type is accepted and echoed back."""
        result = cmd_format_commit(_format_commit_args(commit_type=commit_type, subject='test subject'))

        assert result['type'] == commit_type

    def test_validation_warning_long_subject(self):
        """Subject over 50 chars warns but stays valid."""
        long_subject = 'a' * 55  # Exceeds 50 chars

        result = cmd_format_commit(_format_commit_args(commit_type='fix', subject=long_subject))

        assert result['validation']['valid']
        assert any('50 chars' in w for w in result['validation']['warnings'])

    def test_validation_error_very_long_subject(self):
        """Subject over 72 chars fails validation."""
        very_long_subject = 'a' * 75  # Exceeds 72 chars

        result = cmd_format_commit(_format_commit_args(commit_type='fix', subject=very_long_subject))

        assert not result['validation']['valid']

    def test_validation_warning_past_tense(self):
        """Past-tense verb produces an imperative-mood warning."""
        result = cmd_format_commit(_format_commit_args(commit_type='fix', subject='fixed the bug'))

        assert any('imperative' in w.lower() for w in result['validation']['warnings'])

    def test_co_authored_by_not_appended_by_script(self):
        """format-commit does NOT append Co-Authored-By."""
        result = cmd_format_commit(_format_commit_args(commit_type='feat', subject='add feature'))

        assert 'Co-Authored-By' not in result['formatted_message']

    def test_ci_commit_type(self):
        """'ci' is a valid commit type."""
        result = cmd_format_commit(_format_commit_args(commit_type='ci', subject='update workflow'))

        assert result['type'] == 'ci'
        assert 'ci: update workflow' in result['formatted_message']

    @pytest.mark.parametrize(
        'word',
        ['embed', 'spread', 'thread', 'overhead', 'string', 'bring', 'caching', 'hashing', 'nothing'],
    )
    def test_imperative_allowlist_word_no_false_warning(self, word):
        """Allowlisted words must not trigger a past-tense imperative warning."""
        result = cmd_format_commit(_format_commit_args(commit_type='fix', subject=f'{word} the module'))

        imperative_warnings = [w for w in result['validation']['warnings'] if 'imperative' in w.lower()]
        assert imperative_warnings == []

    def test_breaking_and_footer_combined(self):
        """Commit message with both --breaking and --footer simultaneously."""
        result = cmd_format_commit(
            _format_commit_args(
                commit_type='feat',
                scope='api',
                subject='change auth endpoint',
                breaking='Old /auth endpoint removed',
                footer='Fixes #123',
            )
        )

        assert 'feat(api)!:' in result['formatted_message']
        assert 'BREAKING CHANGE:' in result['formatted_message']
        assert 'Fixes #123' in result['formatted_message']

    def test_all_params_combined(self):
        """Commit message with body + breaking + footer + scope."""
        result = cmd_format_commit(
            _format_commit_args(
                commit_type='feat',
                scope='api',
                subject='change auth endpoint',
                body='Migrated to OAuth 2.0 flow',
                breaking='Old /auth endpoint removed',
                footer='Fixes #123',
            )
        )

        assert 'feat(api)!:' in result['formatted_message']
        assert 'BREAKING CHANGE:' in result['formatted_message']
        assert 'Fixes #123' in result['formatted_message']
        assert 'Migrated to OAuth 2.0 flow' in result['formatted_message']

    def test_long_scope_plus_subject_exceeds_72(self):
        """Header exceeding 72 chars fails validation."""
        long_scope = 'very-long-module-name'
        long_subject = 'a' * 50  # type(scope): subject -> 5 + 23 + 4 + 50 = 82 chars

        result = cmd_format_commit(_format_commit_args(commit_type='feat', scope=long_scope, subject=long_subject))

        assert not result['validation']['valid']
        assert any('Header' in w for w in result['validation']['warnings'])


class TestWrapText:
    """Test wrap_text function directly."""

    def test_short_line_unchanged(self):
        """Lines within width are not wrapped."""
        assert wrap_text('short line', 72) == 'short line'

    def test_long_line_wrapped(self):
        """Lines exceeding width are wrapped at word boundaries."""
        text = 'a ' * 40  # 80 chars

        result = wrap_text(text.strip(), 72)

        assert all(len(line) <= 72 for line in result.split('\n'))

    def test_preserves_bullet_indentation(self):
        """Wrapped lines preserve leading indentation."""
        text_indented = '  - ' + 'word ' * 20

        result_indented = wrap_text(text_indented, 72)

        assert all(line.startswith('  ') for line in result_indented.split('\n'))

    def test_deep_indent_not_wrapped(self):
        """Lines with >52 chars indent are kept as-is (effective_width < 20)."""
        text = ' ' * 55 + 'deeply indented content that should not be wrapped'

        assert wrap_text(text, 72) == text

    def test_very_long_word_not_broken(self):
        """A single word longer than width is not split."""
        url = 'https://example.com/very/long/path/that/exceeds/seventy/two/characters/easily'

        assert wrap_text(url, 72) == url

    def test_multiline_preserves_paragraphs(self):
        """Multiple paragraphs separated by newlines are handled independently."""
        text = 'First paragraph.\nSecond paragraph.'

        assert wrap_text(text, 72) == text


class TestSourceCommitGate:
    """Test git_workflow.py source-commit-gate (PLAN-LB-56 deliverable 2).

    Covers the three gate pins from the deliverable contract —
    allow-with-open-fix-task, allow-with-section-6-record, deny-with-neither —
    plus the plan-only and non-finalize allow paths and the CLI plumbing.
    """

    @staticmethod
    def _fix_task(status='pending', origin='fix'):
        """A minimal task record carrying the fields the gate reads."""
        return {'number': 7, 'title': 'Fix: loop-back correction', 'status': status, 'origin': origin}

    @staticmethod
    def _section6_finding():
        """A finding record citing the rubric section-6 inline-correction allowance."""
        return {
            'title': 'Functional review: inline correction per review-rubric',
            'detail': 'Correction to the diff in hand approved for the 6-finalize target (section-6)',
            'resolution_detail': '',
        }

    def test_non_finalize_phase_allows_source_commit(self):
        """Outside 6-finalize every commit is allowed — the gate is finalize-only."""
        result = evaluate_source_commit_gate('5-execute', ['src/a.py'], [], [])

        assert result['status'] == 'success'
        assert result['allowed'] is True
        assert result['reason'] == 'not_finalize'

    def test_plan_only_commit_passes_in_finalize(self):
        """A .plan/-only commit passes with neither signal present."""
        result = evaluate_source_commit_gate(
            '6-finalize', ['.plan/local/plans/EXAMPLE/status.json', '.plan/temp/guard.log'], [], []
        )

        assert result['allowed'] is True
        assert result['reason'] == 'plan_only'

    def test_deny_with_neither_signal(self):
        """A finalize-phase source commit with neither signal is refused."""
        result = evaluate_source_commit_gate('6-finalize', ['src/a.py'], [], [])

        assert result['allowed'] is False
        assert result['reason'] == 'no_sanction'
        assert 'loop-back' in result['message']

    def test_plan_origin_task_does_not_sanction(self):
        """An unfinished deliverable task is not a sanction to commit around it."""
        tasks = [self._fix_task(origin='plan')]

        assert has_open_fix_task(tasks) is False
        result = evaluate_source_commit_gate('6-finalize', ['src/a.py'], tasks, [])

        assert result['allowed'] is False

    def test_allow_with_open_fix_task(self):
        """An open loop-back fix task sanctions the source commit."""
        tasks = [self._fix_task(status='pending', origin='fix')]

        assert has_open_fix_task(tasks) is True
        result = evaluate_source_commit_gate('6-finalize', ['src/a.py'], tasks, [])

        assert result['allowed'] is True
        assert result['reason'] == 'open_fix_task'

    def test_closed_fix_task_does_not_sanction(self):
        """A done fix task no longer sanctions — the sanction ends with the task."""
        tasks = [self._fix_task(status='done', origin='fix')]

        assert has_open_fix_task(tasks) is False
        result = evaluate_source_commit_gate('6-finalize', ['src/a.py'], tasks, [])

        assert result['allowed'] is False

    def test_allow_with_section6_record(self):
        """A finding record citing the section-6 allowance sanctions the commit."""
        findings = [self._section6_finding()]

        assert has_section6_record(findings) is True
        result = evaluate_source_commit_gate('6-finalize', ['src/a.py'], [], findings)

        assert result['allowed'] is True
        assert result['reason'] == 'section6_record'

    def test_rubric_citation_without_allowance_does_not_sanction(self):
        """A rubric citation for another section carries no inline-correction allowance."""
        findings = [
            {
                'title': 'Code review finding per review-rubric section 3',
                'detail': 'Substantiated failure scenario with no sanction recorded',
                'resolution_detail': '',
            }
        ]

        assert has_section6_record(findings) is False

    def test_bare_phase_mention_does_not_sanction(self):
        """A rubric citation plus a bare 6-finalize phase mention, without
        inline-correction words, carries no allowance."""
        findings = [
            {
                'title': 'Code review finding per review-rubric section 3',
                'detail': 'Loop back to 6-finalize for re-review (section-6)',
                'resolution_detail': '',
            }
        ]

        assert has_section6_record(findings) is False
        result = evaluate_source_commit_gate('6-finalize', ['src/a.py'], [], findings)

        assert result['allowed'] is False
        assert result['reason'] == 'no_sanction'

    def test_split_markers_across_records_do_not_sanction(self):
        """Cross-record bleed: the rubric half in one record and the allowance
        half in another must not combine into a sanction."""
        findings = [
            {
                'title': 'Code review finding per review-rubric section 3',
                'detail': 'Substantiated failure scenario with no sanction recorded',
                'resolution_detail': '',
            },
            {
                'title': 'Unrelated triage note',
                'detail': 'Deferred inline-correction for a later pass',
                'resolution_detail': '',
            },
        ]

        assert has_section6_record(findings) is False
        result = evaluate_source_commit_gate('6-finalize', ['src/a.py'], [], findings)

        assert result['allowed'] is False
        assert result['reason'] == 'no_sanction'

    @staticmethod
    def _findings_plan_dir(root: Path) -> Path:
        """A minimal plan directory carrying a findings store under ``root``."""
        plan_dir = root / '.plan' / 'local' / 'plans' / 'FIXTURE'
        (plan_dir / 'artifacts' / 'findings').mkdir(parents=True)
        return plan_dir

    def test_loader_keeps_jsonl_lines_as_separate_records(self, tmp_path):
        """File-level bleed pin: markers split across JSONL lines refuse."""
        import json

        plan_dir = self._findings_plan_dir(tmp_path)
        (plan_dir / 'artifacts' / 'findings' / 'qgate-6-finalize.jsonl').write_text(
            '\n'.join(
                [
                    json.dumps(
                        {
                            'title': 'Code review finding per review-rubric section 3',
                            'detail': 'no sanction recorded',
                        }
                    ),
                    json.dumps(
                        {
                            'title': 'Unrelated triage note',
                            'detail': 'deferred inline-correction for a later pass',
                        }
                    ),
                ]
            )
            + '\n',
            encoding='utf-8',
        )

        texts, count = _source_gate_finding_texts(plan_dir)

        assert count == 2
        assert has_section6_record(texts) is False

    def test_loader_single_jsonl_line_with_both_halves_sanctions(self, tmp_path):
        """Positive control: both halves in one JSONL record still sanction."""
        import json

        plan_dir = self._findings_plan_dir(tmp_path)
        (plan_dir / 'artifacts' / 'findings' / 'qgate-6-finalize.jsonl').write_text(
            json.dumps(self._section6_finding()) + '\n',
            encoding='utf-8',
        )

        texts, count = _source_gate_finding_texts(plan_dir)

        assert count == 1
        assert has_section6_record(texts) is True

    def test_loader_splits_json_list_into_records(self, tmp_path):
        """A JSON file holding a record list splits per record, not per file."""
        import json

        plan_dir = self._findings_plan_dir(tmp_path)
        (plan_dir / 'artifacts' / 'findings' / 'notes.json').write_text(
            json.dumps(
                [
                    {
                        'title': 'Code review finding per review-rubric section 3',
                        'detail': 'no sanction recorded',
                    },
                    {
                        'title': 'Unrelated triage note',
                        'detail': 'deferred inline-correction for a later pass',
                    },
                ]
            ),
            encoding='utf-8',
        )

        texts, count = _source_gate_finding_texts(plan_dir)

        assert count == 2
        assert has_section6_record(texts) is False

    def test_plan_state_prefix_only_matches_first_segment(self):
        """A .plan infix elsewhere in the path is still a source path."""
        assert is_plan_only_path('.plan/a.json') is True
        assert is_plan_only_path('./.plan/a.json') is True
        assert is_plan_only_path('src/.plan_notes.md') is False
        assert is_source_commit(['.plan/a.json']) is False
        assert is_source_commit(['.plan/a.json', 'src/a.py']) is True
        assert is_source_commit([]) is False

    def test_cli_deny_with_neither(self, tmp_path):
        """CLI plumbing: source change with no plan signals is refused, exit 0."""
        stdout, stderr, returncode = run_git_script(
            [
                'source-commit-gate',
                '--phase',
                '6-finalize',
                '--changed-paths',
                'src/foo.py',
                '--project-dir',
                str(tmp_path),
            ]
        )

        assert returncode == 0
        result = parse_toon(stdout)
        assert result['status'] == 'success'
        assert result['allowed'] is False
        assert result['reason'] == 'no_sanction'
        assert result['signals_resolved'] is False

    def test_cli_plan_only_passes(self, tmp_path):
        """CLI plumbing: a plan-state-only change passes without signals."""
        stdout, stderr, returncode = run_git_script(
            [
                'source-commit-gate',
                '--phase',
                '6-finalize',
                '--changed-paths',
                '.plan/a.json',
                '--project-dir',
                str(tmp_path),
            ]
        )

        assert returncode == 0
        result = parse_toon(stdout)
        assert result['allowed'] is True
        assert result['reason'] == 'plan_only'

    def test_cli_allow_with_open_fix_task(self, tmp_path):
        """CLI plumbing: the gate reads an open fix task from the MAIN-ANCHORED plan dir."""
        import json

        # The gate resolves the plan directory main-anchored (ADR-002), so the
        # tasks live under the PLAN_BASE_DIR the sandbox installed, not under the
        # worktree-local ``<project-dir>/.plan/local/plans``.
        plan_dir = Path(os.environ['PLAN_BASE_DIR']) / 'plans' / 'FIXTURE'
        tasks_dir = plan_dir / 'tasks'
        tasks_dir.mkdir(parents=True)
        (plan_dir / 'status.json').write_text(
            json.dumps({'plan_id': 'FIXTURE', 'current_phase': '6-finalize'}), encoding='utf-8'
        )
        (tasks_dir / 'TASK-001.json').write_text(
            json.dumps({'number': 1, 'title': 'Fix: loop-back', 'status': 'pending', 'origin': 'fix'}),
            encoding='utf-8',
        )
        stdout, stderr, returncode = run_git_script(
            [
                'source-commit-gate',
                '--plan-id',
                'FIXTURE',
                '--phase',
                '6-finalize',
                '--changed-paths',
                'src/foo.py',
                '--project-dir',
                str(tmp_path),
            ]
        )

        assert returncode == 0
        result = parse_toon(stdout)
        assert result['allowed'] is True
        assert result['reason'] == 'open_fix_task'
        assert result['signals_resolved'] is True

    def test_cli_untracked_source_file_is_refused(self, tmp_path):
        """Git derivation unions untracked files: an untracked source file refuses."""
        subprocess.run(['git', 'init', str(tmp_path)], check=True, capture_output=True)
        subprocess.run(
            ['git', '-C', str(tmp_path), 'config', 'user.email', 'test@example.com'],
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ['git', '-C', str(tmp_path), 'config', 'user.name', 'Test'],
            check=True,
            capture_output=True,
        )
        _create_file(tmp_path, 'baseline.txt')
        subprocess.run(['git', '-C', str(tmp_path), 'add', 'baseline.txt'], check=True, capture_output=True)
        subprocess.run(['git', '-C', str(tmp_path), 'commit', '-m', 'baseline'], check=True, capture_output=True)
        _create_file(tmp_path, 'src/new.py')
        stdout, stderr, returncode = run_git_script(
            [
                'source-commit-gate',
                '--phase',
                '6-finalize',
                '--project-dir',
                str(tmp_path),
            ]
        )

        assert returncode == 0
        result = parse_toon(stdout)
        assert result['allowed'] is False
        assert result['reason'] == 'no_sanction'

    def test_source_gate_uses_nul_separation(self):
        """The git derivation passes -z on both calls and splits on NUL."""
        import inspect

        source = inspect.getsource(git_workflow._source_gate_changed_paths)
        assert "'-z'" in source or '"-z"' in source
        assert "split('\\0')" in source or 'split("\\0")' in source
        assert 'splitlines()' not in source

    def test_source_gate_preserves_space_padded_paths(self, tmp_path):
        """Space-padded and non-ASCII paths survive the git derivation verbatim."""
        subprocess.run(['git', 'init', str(tmp_path)], check=True, capture_output=True)
        subprocess.run(
            ['git', '-C', str(tmp_path), 'config', 'user.email', 'test@example.com'],
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ['git', '-C', str(tmp_path), 'config', 'user.name', 'Test'],
            check=True,
            capture_output=True,
        )
        _create_file(tmp_path, 'baseline.txt')
        subprocess.run(['git', '-C', str(tmp_path), 'add', 'baseline.txt'], check=True, capture_output=True)
        subprocess.run(['git', '-C', str(tmp_path), 'commit', '-m', 'baseline'], check=True, capture_output=True)
        padded = tmp_path / ' leading-and-trailing '
        padded.write_text('x', encoding='utf-8')
        changed, err = git_workflow._source_gate_changed_paths(tmp_path, None)
        assert err is None
        assert ' leading-and-trailing ' in (changed or [])
