#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Remove-redundant + scope + executor (carve 2 split)."""

import json
from pathlib import Path

import pytest
from _permission_fix_fixtures import (
    RETIRED_DEFAULT,
    allow_list,
    create_marketplace,
    in_tmp_cwd,
    read_allow,
    read_settings,
    seed_retired,
    write_marshal,
    write_settings,
    write_settings_str,
)

from conftest import MARKETPLACE_ROOT, parse_ns, run_script

SCRIPT_PATH = MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'tools-permission-fix' / 'scripts' / 'permission_fix.py'

from permission_fix import (  # noqa: E402
    cmd_apply_fixes,
    cmd_apply_project_step_permissions,
    cmd_consolidate,
    cmd_ensure_wildcards,
    cmd_generate_wildcards,
    cmd_remove_redundant,
    scan_marketplace_dir,
)


class TestRemoveRedundant:
    """Test permission_fix.py remove-redundant subcommand via direct import."""

    def write_settings(self, path, allow: list[str]) -> None:
        path.write_text(json.dumps({'permissions': {'allow': allow, 'deny': [], 'ask': []}}))

    def read_allow(self, path) -> list[str]:
        allow: list = json.loads(path.read_text())['permissions']['allow']
        return allow

    def test_dry_run_removes_nothing(self, tmp_path):
        """Dry-run should not modify any settings file."""
        global_file = tmp_path / 'global_settings.json'
        local_file = tmp_path / 'local_settings.json'
        write_settings(global_file, ['Bash(git:*)', 'Bash(npm:*)'])
        write_settings(local_file, ['Bash(git:*)', 'Bash(npm:*)'])

        result = cmd_remove_redundant(
            parse_ns(
                'plan-marshall',
                'tools-permission-fix',
                'permission_fix.py',
                'remove-redundant',
                '--global-settings',
                str(global_file),
                '--local-settings',
                str(local_file),
                '--dry-run',
            )
        )

        assert result['status'] == 'success'
        assert result['dry_run']
        assert not result['applied']
        # Files should be unchanged
        assert read_allow(local_file) == ['Bash(git:*)', 'Bash(npm:*)']

    def test_removes_exact_duplicates_from_local(self, tmp_path):
        """Should remove permissions from local that are exact duplicates in global."""
        global_file = tmp_path / 'global_settings.json'
        local_file = tmp_path / 'local_settings.json'
        write_settings(global_file, ['Bash(git:*)', 'Bash(npm:*)'])
        write_settings(local_file, ['Bash(git:*)', 'Edit(.plan/**)'])

        result = cmd_remove_redundant(
            parse_ns(
                'plan-marshall',
                'tools-permission-fix',
                'permission_fix.py',
                'remove-redundant',
                '--global-settings',
                str(global_file),
                '--local-settings',
                str(local_file),
                '--no-move-marketplace',
            )
        )

        assert result['status'] == 'success'
        assert result['applied']
        assert 'Bash(git:*)' in result['removed_redundant']
        local_allow = read_allow(local_file)
        assert 'Bash(git:*)' not in local_allow
        assert 'Edit(.plan/**)' in local_allow

    def test_moves_marketplace_permissions_to_global(self, tmp_path):
        """Should move Skill() and SlashCommand() perms from local to global."""
        global_file = tmp_path / 'global_settings.json'
        local_file = tmp_path / 'local_settings.json'
        write_settings(global_file, ['Bash(git:*)'])
        write_settings(local_file, ['Bash(git:*)', 'Skill(pm-dev-java:*)', 'Edit(.plan/**)'])

        result = cmd_remove_redundant(
            parse_ns(
                'plan-marshall',
                'tools-permission-fix',
                'permission_fix.py',
                'remove-redundant',
                '--global-settings',
                str(global_file),
                '--local-settings',
                str(local_file),
            )
        )

        assert result['status'] == 'success'
        assert result['applied']
        # Exact duplicate removed from local
        assert 'Bash(git:*)' in result['removed_redundant']
        # Marketplace perm moved to global
        assert 'Skill(pm-dev-java:*)' in result['moved_to_global']
        local_allow = read_allow(local_file)
        assert 'Skill(pm-dev-java:*)' not in local_allow
        global_allow = read_allow(global_file)
        assert 'Skill(pm-dev-java:*)' in global_allow

    def test_no_move_marketplace_skips_marketplace_perms(self, tmp_path):
        """--no-move-marketplace should leave marketplace permissions in local."""
        global_file = tmp_path / 'global_settings.json'
        local_file = tmp_path / 'local_settings.json'
        write_settings(global_file, ['Bash(git:*)'])
        write_settings(local_file, ['Bash(git:*)', 'Skill(pm-dev-java:*)'])

        result = cmd_remove_redundant(
            parse_ns(
                'plan-marshall',
                'tools-permission-fix',
                'permission_fix.py',
                'remove-redundant',
                '--global-settings',
                str(global_file),
                '--local-settings',
                str(local_file),
                '--no-move-marketplace',
            )
        )

        assert result['status'] == 'success'
        assert result['moved_to_global'] == []
        local_allow = read_allow(local_file)
        assert 'Skill(pm-dev-java:*)' in local_allow

    def test_already_in_global_removes_from_local_without_duplicate(self, tmp_path):
        """Marketplace perm already in global: remove from local, not re-added to global."""
        global_file = tmp_path / 'global_settings.json'
        local_file = tmp_path / 'local_settings.json'
        write_settings(global_file, ['Bash(git:*)', 'Skill(pm-dev-java:*)'])
        write_settings(local_file, ['Skill(pm-dev-java:*)'])

        result = cmd_remove_redundant(
            parse_ns(
                'plan-marshall',
                'tools-permission-fix',
                'permission_fix.py',
                'remove-redundant',
                '--global-settings',
                str(global_file),
                '--local-settings',
                str(local_file),
            )
        )

        assert result['status'] == 'success'
        local_allow = read_allow(local_file)
        assert 'Skill(pm-dev-java:*)' not in local_allow
        # Not duplicated in global
        global_allow = read_allow(global_file)
        assert global_allow.count('Skill(pm-dev-java:*)') == 1

    def test_no_changes_when_already_clean(self, tmp_path):
        """Should report no changes when local has no redundancies."""
        global_file = tmp_path / 'global_settings.json'
        local_file = tmp_path / 'local_settings.json'
        write_settings(global_file, ['Bash(git:*)'])
        write_settings(local_file, ['Edit(.plan/**)', 'Read(docs/**)'])

        result = cmd_remove_redundant(
            parse_ns(
                'plan-marshall',
                'tools-permission-fix',
                'permission_fix.py',
                'remove-redundant',
                '--global-settings',
                str(global_file),
                '--local-settings',
                str(local_file),
            )
        )

        assert result['status'] == 'success'
        assert not result['changes_made']
        assert not result['applied']


class TestScopeProjectResolvesTheOverridingFile:
    """``--scope project`` must edit the file an operator's configuration actually reads.

    Claude lets ``.claude/settings.local.json`` override ``.claude/settings.json``,
    so when both exist the local one is the only place a change can land AND be
    observed. Writing the shared file instead reports a change the operator never
    sees — a silent no-op that looks like success.

    The class drives the real script through a subprocess, so the resolution is
    exercised end-to-end through argument parsing rather than against a
    monkeypatched helper, and both files are checked so "wrote the right one" and
    "left the other one alone" are separate, independently failing claims.
    """

    #: The retired default whose pruning gives every run below observable work.
    #: Any run that resolves a file will strip it, so which file lost it is the
    #: measurement — a seed with nothing to do could not tell the two apart.
    RETIRED_DEFAULT = 'Write(.plan/**)'

    def _seed(self, path: Path) -> bytes:
        """Write a settings file carrying the retired rule; return its bytes."""
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({'permissions': {'allow': [RETIRED_DEFAULT], 'deny': [], 'ask': []}}))
        return path.read_bytes()

    def _allow(self, path: Path) -> list[str]:
        allow: list[str] = json.loads(path.read_text())['permissions']['allow']
        return allow

    def test_with_both_files_present_the_prune_lands_in_the_local_one(self, tmp_path):
        """The overriding file is pruned and the shared file is left byte-identical.

        Both halves are asserted because either alone is satisfiable by a
        defect: "local was pruned" passes for an implementation that writes
        both, and "shared is untouched" passes for one that writes neither.
        Together they also establish that EXACTLY ONE of the two files was
        written, which is the property the seam claims.
        """
        shared = tmp_path / '.claude' / 'settings.json'
        local = tmp_path / '.claude' / 'settings.local.json'
        shared_before = seed_retired(shared)
        seed_retired(local)

        result = run_script(SCRIPT_PATH, 'apply-fixes', '--scope', 'project', cwd=tmp_path)
        assert result.success, f'Script failed: {result.stderr}'
        data = result.toon()

        assert str(local) in data['settings_path']
        assert RETIRED_DEFAULT not in allow_list(local)
        # The shadowed file is untouched, down to its bytes — so the run wrote one
        # file, not two, and did not merely happen to leave the same content.
        assert shared.read_bytes() == shared_before
        assert RETIRED_DEFAULT in allow_list(shared)

    def test_with_only_the_shared_file_present_it_falls_back_to_it(self, tmp_path):
        """The fallback arm: no local file, so the shared file is the one edited.

        This is the control that keeps the test above from passing for a
        resolver hard-wired to ``settings.local.json`` — under that defect this
        run would edit or create the wrong file.
        """
        shared = tmp_path / '.claude' / 'settings.json'
        local = tmp_path / '.claude' / 'settings.local.json'
        seed_retired(shared)

        result = run_script(SCRIPT_PATH, 'apply-fixes', '--scope', 'project', cwd=tmp_path)
        assert result.success, f'Script failed: {result.stderr}'
        data = result.toon()

        assert str(shared) in data['settings_path']
        assert RETIRED_DEFAULT not in allow_list(shared)
        # Preferring a file it did not find is not a reason to create it.
        assert not local.exists()

    def test_target_project_on_add_still_resolves_the_shared_file(self, tmp_path):
        """Boundary control: ``--target`` was deliberately NOT switched.

        ``resolve_settings_arg`` serves four subcommands; ``get_settings_path``
        serves those plus six more reached by ``--target``. Only the first seam
        moved to the read preference, and that four-vs-ten line is load-bearing
        — without this row the switch could silently widen to all ten and every
        other test here would still pass.
        """
        shared = tmp_path / '.claude' / 'settings.json'
        local = tmp_path / '.claude' / 'settings.local.json'
        seed_retired(shared)
        local_before = seed_retired(local)

        result = run_script(SCRIPT_PATH, 'add', '--permission', 'Bash(npm:*)', '--target', 'project', cwd=tmp_path)
        assert result.success, f'Script failed: {result.stderr}'

        assert 'Bash(npm:*)' in allow_list(shared)
        assert local.read_bytes() == local_before
