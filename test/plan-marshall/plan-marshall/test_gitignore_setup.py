#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""
Tests for the gitignore_setup.py script.

Tier 2 (direct import) tests with 2 subprocess tests for CLI plumbing.

Tests .gitignore configuration for the planning system:
- Creates new .gitignore if not present
- Updates existing .gitignore with planning entries
- Reports unchanged when entries already exist
- Supports dry-run mode
"""

import pytest

# Import shared infrastructure (conftest.py sets up PYTHONPATH)
from conftest import MARKETPLACE_ROOT, run_script

# Script path to gitignore_setup.py
SCRIPT_PATH = MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'marshall-steward' / 'scripts' / 'gitignore_setup.py'

# Tier 2 direct imports — conftest sets up PYTHONPATH for cross-skill imports
from gitignore_setup import (  # noqa: E402, I001
    GITIGNORE_PLAN_LOCAL_WORKTREES,
    check_gitignore_status,
    consolidate_managed_blocks,
    setup_gitignore,
)

# Managed-block header comments — pinned here so the consolidation tests assert
# against the exact strings the script emits.
_MANAGED_COMMENT = '# Planning system (managed by /marshall-steward)'
_LOCAL_COMMENT = (
    '# Runtime state (plans, run-configuration, lessons-learned, memory, logs '
    '— managed by plan-marshall)'
)


# =============================================================================
# Constant pin: worktree path migrated from .claude/worktrees/ to
# .plan/local/worktrees/ (compatibility: breaking — no fallback retained)
# =============================================================================


def test_gitignore_plan_local_worktrees_constant_value():
    """The exported constant pins to the new .plan/local/worktrees/ path."""
    assert GITIGNORE_PLAN_LOCAL_WORKTREES == '.plan/local/worktrees/'


class TestGitignoreSetupCreate:
    """Test gitignore_setup.py creating new .gitignore via direct import."""

    def test_creates_gitignore_when_missing(self, tmp_path):
        """Should create new .gitignore with planning entries."""
        result = setup_gitignore(tmp_path)
        assert result['status'] == 'created'
        # .plan/*, !marshal.json, !project-architecture/
        assert result['entries_added'] == 3

        # Verify file was created
        gitignore_path = tmp_path / '.gitignore'
        assert gitignore_path.exists()

        content = gitignore_path.read_text()
        assert '.plan/' in content
        assert '!.plan/marshal.json' in content
        assert '!.plan/project-architecture/' in content
        # The plugin-doctor negation and .plan/local/worktrees/ ignore are no
        # longer emitted — the latter is redundant under .plan/*, and the former
        # is left to projects that opt into a project-level plugin-doctor config.
        assert '!.plan/plugin-doctor.yml' not in content
        assert '.plan/local/worktrees/' not in content
        assert '.claude/worktrees/' not in content
        assert '# Planning system' in content


class TestGitignoreSetupUpdate:
    """Test gitignore_setup.py updating existing .gitignore via direct import."""

    def test_updates_existing_gitignore(self, tmp_path):
        """Should add planning entries to existing .gitignore."""
        gitignore_path = tmp_path / '.gitignore'
        gitignore_path.write_text('# Existing content\nnode_modules/\n*.log\n')

        result = setup_gitignore(tmp_path)
        assert result['status'] == 'updated'
        assert result['entries_added'] == 3

        # Verify existing content preserved and new content added
        content = gitignore_path.read_text()
        assert 'node_modules/' in content
        assert '*.log' in content
        assert '.plan/' in content
        assert '!.plan/marshal.json' in content
        assert '!.plan/project-architecture/' in content
        assert '!.plan/plugin-doctor.yml' not in content
        assert '.plan/local/worktrees/' not in content
        assert '.claude/worktrees/' not in content

    def test_adds_only_missing_entries(self, tmp_path):
        """Should only add entries that are missing."""
        gitignore_path = tmp_path / '.gitignore'
        gitignore_path.write_text('.plan/\n')

        result = setup_gitignore(tmp_path)
        assert result['status'] == 'updated'
        # !marshal.json + !project-architecture/
        assert result['entries_added'] == 2

        content = gitignore_path.read_text()
        assert '!.plan/marshal.json' in content
        assert '!.plan/project-architecture/' in content
        assert '!.plan/plugin-doctor.yml' not in content
        assert '.plan/local/worktrees/' not in content
        assert '.claude/worktrees/' not in content


class TestGitignoreSetupUnchanged:
    """Test gitignore_setup.py when no changes needed via direct import."""

    def test_unchanged_when_all_entries_exist(self, tmp_path):
        """Should report unchanged when all entries and comments already present.

        Both managed comments must be present for an unchanged verdict: after the
        duplicate-comment fix, a missing ``# Planning system`` header makes the
        run an update (it appends the absent comment), so the fixture pins both
        comment headers alongside the entries.
        """
        gitignore_path = tmp_path / '.gitignore'
        gitignore_path.write_text(
            '# Planning system (managed by /marshall-steward)\n'
            '# Runtime state (plans, run-configuration, lessons-learned, memory, logs '
            '— managed by plan-marshall)\n'
            '.plan/\n!.plan/marshal.json\n!.plan/project-architecture/\n'
            '!.plan/plugin-doctor.yml\n.plan/local/worktrees/\n'
        )

        result = setup_gitignore(tmp_path)
        assert result['status'] == 'unchanged'
        assert result['entries_added'] == 0

    def test_recognizes_alternate_plan_format(self, tmp_path):
        """Should recognize .plan without trailing slash."""
        gitignore_path = tmp_path / '.gitignore'
        gitignore_path.write_text(
            '# Runtime state (plans, run-configuration, lessons-learned, memory, logs '
            '— managed by plan-marshall)\n'
            '.plan\n!.plan/marshal.json\n!.plan/project-architecture/\n'
            '!.plan/plugin-doctor.yml\n.plan/local/worktrees/\n'
        )

        result = setup_gitignore(tmp_path)
        # .plan (without slash) should be recognized as .plan/
        assert result['entries_added'] == 0

    def test_recognizes_plan_local_worktrees_without_trailing_slash(self, tmp_path):
        """Should recognize .plan/local/worktrees without trailing slash."""
        gitignore_path = tmp_path / '.gitignore'
        gitignore_path.write_text(
            '# Runtime state (plans, run-configuration, lessons-learned, memory, logs '
            '— managed by plan-marshall)\n'
            '.plan/\n!.plan/marshal.json\n!.plan/project-architecture/\n'
            '!.plan/plugin-doctor.yml\n.plan/local/worktrees\n'
        )

        result = setup_gitignore(tmp_path)
        assert result['entries_added'] == 0


class TestGitignoreSetupIdempotency:
    """Test gitignore_setup.py does not duplicate managed comments on re-run.

    Regression for the duplicate-comment defect: setup_gitignore emitted the
    ``# Planning system`` and ``# Runtime state`` header comments unconditionally
    on every update, so a second run over a partially-populated .gitignore
    appended a duplicate comment header. The fix guards each comment behind a
    not-already-present check (needs_managed_comment / needs_local_comment).
    """

    def test_managed_comment_not_duplicated_on_second_run(self, tmp_path):
        """Running setup twice must not duplicate the managed-comment header."""
        # Arrange / Act — first run creates the file, second run is a no-op.
        setup_gitignore(tmp_path)
        second = setup_gitignore(tmp_path)

        # Assert — second run is unchanged; the comment appears exactly once.
        assert second['status'] == 'unchanged'
        assert second['entries_added'] == 0
        content = (tmp_path / '.gitignore').read_text()
        assert content.count('# Planning system (managed by /marshall-steward)') == 1
        assert content.count(
            '# Runtime state (plans, run-configuration, lessons-learned, memory, logs '
            '— managed by plan-marshall)'
        ) == 1

    def test_comment_not_re_emitted_when_entries_added_to_commented_file(self, tmp_path):
        """An update that adds missing entries must not re-emit an existing comment.

        A .gitignore that already carries the managed comment but is missing some
        entries gets the entries added WITHOUT a second copy of the comment.
        """
        # Arrange — managed comment present, but the project-architecture
        # negation is missing.
        gitignore_path = tmp_path / '.gitignore'
        gitignore_path.write_text(
            '# Planning system (managed by /marshall-steward)\n'
            '# Runtime state (plans, run-configuration, lessons-learned, memory, logs '
            '— managed by plan-marshall)\n'
            '.plan/*\n!.plan/marshal.json\n'
        )

        # Act — adds the missing !.plan/project-architecture/ entry.
        result = setup_gitignore(tmp_path)

        # Assert — entry added, but neither comment is duplicated.
        assert result['status'] == 'updated'
        assert result['entries_added'] == 1
        content = gitignore_path.read_text()
        assert content.count('# Planning system (managed by /marshall-steward)') == 1
        assert content.count(
            '# Runtime state (plans, run-configuration, lessons-learned, memory, logs '
            '— managed by plan-marshall)'
        ) == 1
        assert '!.plan/project-architecture/' in content


class TestGitignoreSetupDryRun:
    """Test gitignore_setup.py dry-run mode via direct import."""

    def test_dry_run_does_not_create_file(self, tmp_path):
        """Dry-run should not create .gitignore."""
        result = setup_gitignore(tmp_path, dry_run=True)
        assert result['status'] == 'created'
        assert result['dry_run']

        # Verify file was NOT created
        gitignore_path = tmp_path / '.gitignore'
        assert not gitignore_path.exists()

    def test_dry_run_does_not_modify_file(self, tmp_path):
        """Dry-run should not modify existing .gitignore."""
        gitignore_path = tmp_path / '.gitignore'
        original_content = '# Original\nnode_modules/\n'
        gitignore_path.write_text(original_content)

        result = setup_gitignore(tmp_path, dry_run=True)
        assert result['status'] == 'updated'
        assert result['dry_run']

        # Verify file was NOT modified
        assert gitignore_path.read_text() == original_content


class TestGitignoreSetupEdgeCases:
    """Test gitignore_setup.py edge cases via direct import."""

    def test_preserves_newline_formatting(self, tmp_path):
        """Should preserve proper newline formatting."""
        gitignore_path = tmp_path / '.gitignore'
        gitignore_path.write_text('node_modules/')  # No trailing newline

        result = setup_gitignore(tmp_path)
        assert result['status'] == 'updated'

        content = gitignore_path.read_text()
        # Should have proper newlines between sections
        assert 'node_modules/#' not in content  # Should not run together

    def test_check_gitignore_status_function(self, tmp_path):
        """Test the raw check_gitignore_status function."""
        gitignore_path = tmp_path / '.gitignore'
        gitignore_path.write_text('.plan/*\n!.plan/marshal.json\n')

        status = check_gitignore_status(gitignore_path)
        assert status['exists']
        assert status['has_plan_dir']
        assert status['has_marshal_exception']
        assert not status['has_architecture_exception']


class TestGitignoreConsolidation:
    """Test consolidation of duplicate managed blocks into a single block.

    Pre-PR#666 projects accumulated several ``# Planning system`` managed-block
    headers (one per re-run). ``consolidate_managed_blocks`` merges every
    managed block into one, preserving the union of managed rules
    (de-duplicated, order-stable), and ``setup_gitignore`` runs the pass
    unconditionally on every invocation.
    """

    def _two_block_content(self) -> str:
        """A .gitignore with two duplicate managed blocks, split across rules."""
        return (
            'node_modules/\n'
            f'{_MANAGED_COMMENT}\n'
            f'{_LOCAL_COMMENT}\n'
            '.plan/*\n'
            '!.plan/marshal.json\n'
            '*.log\n'
            f'{_MANAGED_COMMENT}\n'
            f'{_LOCAL_COMMENT}\n'
            '!.plan/project-architecture/\n'
            '.plan/local/worktrees/\n'
        )

    def test_two_duplicate_blocks_consolidated_to_one(self, tmp_path):
        """Two managed blocks merge into one; the union of rules is preserved."""
        # Arrange — file with two managed-block headers.
        gitignore_path = tmp_path / '.gitignore'
        gitignore_path.write_text(self._two_block_content())

        # Act — consolidation runs unconditionally inside setup_gitignore.
        result = setup_gitignore(tmp_path)

        # Assert — exactly one managed-block header survives, no rule lost.
        content = gitignore_path.read_text()
        assert result['status'] == 'updated'
        assert content.count(_MANAGED_COMMENT) == 1
        assert content.count(_LOCAL_COMMENT) == 1
        assert '.plan/*' in content
        assert '!.plan/marshal.json' in content
        assert '!.plan/project-architecture/' in content
        assert '.plan/local/worktrees/' in content

    def test_single_block_file_is_unchanged(self, tmp_path):
        """A file that is already a single managed block is left byte-stable."""
        # Arrange — canonical single-block file.
        gitignore_path = tmp_path / '.gitignore'
        original = (
            f'{_MANAGED_COMMENT}\n'
            f'{_LOCAL_COMMENT}\n'
            '.plan/*\n'
            '!.plan/marshal.json\n'
            '!.plan/project-architecture/\n'
            '!.plan/plugin-doctor.yml\n'
            '.plan/local/worktrees/\n'
        )
        gitignore_path.write_text(original)

        # Act
        result = setup_gitignore(tmp_path)

        # Assert — unchanged status and byte-identical content.
        assert result['status'] == 'unchanged'
        assert result['entries_added'] == 0
        assert gitignore_path.read_text() == original

    def test_consolidation_is_idempotent(self, tmp_path):
        """A second run over a consolidated file is unchanged and byte-stable."""
        # Arrange — consolidate the two-block file once.
        gitignore_path = tmp_path / '.gitignore'
        gitignore_path.write_text(self._two_block_content())
        setup_gitignore(tmp_path)
        after_first = gitignore_path.read_text()

        # Act — run again.
        second = setup_gitignore(tmp_path)

        # Assert — second run is a no-op; content unchanged.
        assert second['status'] == 'unchanged'
        assert second['entries_added'] == 0
        assert gitignore_path.read_text() == after_first
        assert after_first.count(_MANAGED_COMMENT) == 1

    def test_user_content_above_and_below_preserved(self, tmp_path):
        """Non-managed user content above/below the managed block is preserved."""
        # Arrange — user lines bracket a duplicated managed block.
        gitignore_path = tmp_path / '.gitignore'
        gitignore_path.write_text(
            '# user header\n'
            'build/\n'
            f'{_MANAGED_COMMENT}\n'
            f'{_LOCAL_COMMENT}\n'
            '.plan/*\n'
            '!.plan/marshal.json\n'
            f'{_MANAGED_COMMENT}\n'
            '!.plan/project-architecture/\n'
            '.plan/local/worktrees/\n'
            '# user footer\n'
            'dist/\n'
        )

        # Act
        setup_gitignore(tmp_path)

        # Assert — user content verbatim, single managed block.
        content = gitignore_path.read_text()
        assert '# user header' in content
        assert 'build/' in content
        assert '# user footer' in content
        assert 'dist/' in content
        assert content.count(_MANAGED_COMMENT) == 1
        # User content order preserved: header before managed block, footer after.
        assert content.index('build/') < content.index(_MANAGED_COMMENT)
        assert content.index('dist/') > content.index('.plan/local/worktrees/')

    def test_helper_no_managed_lines_is_noop(self):
        """consolidate_managed_blocks leaves a file with no managed lines as-is."""
        content = '# just user content\nnode_modules/\n*.log\n'
        assert consolidate_managed_blocks(content) == content

    def test_helper_empty_content_is_noop(self):
        """consolidate_managed_blocks returns empty input unchanged."""
        assert consolidate_managed_blocks('') == ''


# =============================================================================
# Subprocess (Tier 3) tests -- CLI plumbing only
# =============================================================================


class TestGitignoreSetupCLI:
    """Test CLI plumbing for gitignore_setup.py."""

    @pytest.fixture
    def isolated_env(self, tmp_path):
        """Env overrides that redirect run-configuration + credential paths.

        Subprocess-invoking tests redirect ``PLAN_BASE_DIR`` and ``HOME``
        via ``run_script(env_overrides=...)``. The subprocess reads both at
        import time, so this pins every path-resolving computation to
        ``tmp_path`` — no leaks into the real
        ``.plan/local/run-configuration.json`` or
        ``~/.plan-marshall-credentials/``.
        """
        return {
            'PLAN_BASE_DIR': str(tmp_path / '.plan'),
            'HOME': str(tmp_path),
        }

    def test_nonexistent_project_root_fails(self, tmp_path, isolated_env):
        """Should fail when project root doesn't exist."""
        nonexistent = tmp_path / 'nonexistent'

        result = run_script(
            SCRIPT_PATH,
            '--project-root',
            str(nonexistent),
            env_overrides=isolated_env,
        )
        assert result.success, f'Script failed: {result.stderr}'
        assert 'project_root_not_found' in result.stdout

    def test_toon_output_format(self, tmp_path, isolated_env):
        """Output should be valid TOON format."""
        result = run_script(
            SCRIPT_PATH,
            '--project-root',
            str(tmp_path),
            env_overrides=isolated_env,
        )
        assert result.success, f'Script failed: {result.stderr}'

        lines = result.stdout.strip().split('\n')
        assert len(lines) >= 3
        for line in lines:
            assert ': ' in line, f'Line should contain colon-space separator: {line}'
