#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Runtime DSL declines (carve 2 split)."""

import json

from _permission_fix_fixtures import (
    assert_declines,
    build_project,
    dual_file_project,
    force_opencode,
    force_unsupported_runtime,
    in_tmp_cwd,
    roster_handlers,
    seam_callers,
    setup_project,
    write_settings,
)

from conftest import load_script_module, parse_ns

pf = load_script_module('plan-marshall', 'tools-permission-fix', 'permission_fix.py', 'pf_behavior')


class TestPermissionDslDeclinesOnNonClaude:
    """The permission-DSL-emitting direct subcommands decline on a non-Claude target."""

    def test_apply_fixes_declines_on_unsupported_runtime(self, monkeypatch, tmp_path):
        """apply-fixes on an unsupported non-Claude target returns a no-op, not a normalized render."""
        settings_file = tmp_path / 'settings.json'
        write_settings(
            settings_file, ['Read(target/build-2025-11-20-174411.log)', 'Read(target/build-2025-11-20-174411.log)']
        )

        force_unsupported_runtime(monkeypatch)

        result = pf.cmd_apply_fixes(
            parse_ns(
                'plan-marshall',
                'tools-permission-fix',
                'permission_fix.py',
                'apply-fixes',
                '--settings',
                str(settings_file),
                '--dry-run',
            )
        )

        assert_declines(result)

    def test_apply_fixes_succeeds_on_opencode(self, monkeypatch, tmp_path):
        """apply-fixes on OpenCode succeeds and ensures defaults."""
        settings_file = tmp_path / 'opencode.json'
        settings_file.write_text('{"permission": {}}')
        force_opencode(monkeypatch)

        result = pf.cmd_apply_fixes(
            parse_ns(
                'plan-marshall',
                'tools-permission-fix',
                'permission_fix.py',
                'apply-fixes',
                '--settings',
                str(settings_file),
                '--dry-run',
            )
        )

        assert result['status'] == 'success'
        assert result['defaults_added_count'] > 0

    def test_consolidate_declines_on_unsupported_runtime(self, monkeypatch, tmp_path):
        """consolidate on an unsupported non-Claude target returns a no-op, not timestamp wildcards."""
        settings_file = tmp_path / 'settings.json'
        write_settings(
            settings_file, ['Read(target/build-2025-11-20-174411.log)', 'Read(target/build-2025-11-20-174412.log)']
        )

        force_unsupported_runtime(monkeypatch)

        result = pf.cmd_consolidate(
            parse_ns(
                'plan-marshall',
                'tools-permission-fix',
                'permission_fix.py',
                'consolidate',
                '--settings',
                str(settings_file),
                '--dry-run',
            )
        )

        assert_declines(result)

    def test_consolidate_succeeds_on_opencode(self, monkeypatch, tmp_path):
        """consolidate on OpenCode returns success."""
        settings_file = tmp_path / 'opencode.json'
        settings_file.write_text('{"permission": {}}')
        force_opencode(monkeypatch)

        result = pf.cmd_consolidate(
            parse_ns(
                'plan-marshall',
                'tools-permission-fix',
                'permission_fix.py',
                'consolidate',
                '--settings',
                str(settings_file),
                '--dry-run',
            )
        )

        assert result['status'] == 'success'

    def test_ensure_wildcards_declines_on_unsupported_runtime(self, monkeypatch, tmp_path):
        """ensure-wildcards on an unsupported non-Claude target returns a no-op, not Skill(...) rules."""
        settings_file = tmp_path / 'settings.json'
        write_settings(settings_file, [])
        marketplace_file = tmp_path / 'marketplace.json'
        marketplace_file.write_text(json.dumps({'bundles': {'plan-marshall': {'skills': {'manage-files': {}}}}}))

        force_unsupported_runtime(monkeypatch)

        result = pf.cmd_ensure_wildcards(
            parse_ns(
                'plan-marshall',
                'tools-permission-fix',
                'permission_fix.py',
                'ensure-wildcards',
                '--settings',
                str(settings_file),
                '--marketplace-json',
                str(marketplace_file),
                '--dry-run',
            )
        )

        assert_declines(result)

    def test_ensure_wildcards_succeeds_on_opencode(self, monkeypatch, tmp_path):
        """ensure-wildcards on OpenCode succeeds and ensures defaults."""
        settings_file = tmp_path / 'opencode.json'
        settings_file.write_text('{"permission": {}}')
        marketplace_file = tmp_path / 'marketplace.json'
        marketplace_file.write_text(json.dumps({'bundles': {}}))
        force_opencode(monkeypatch)

        result = pf.cmd_ensure_wildcards(
            parse_ns(
                'plan-marshall',
                'tools-permission-fix',
                'permission_fix.py',
                'ensure-wildcards',
                '--settings',
                str(settings_file),
                '--marketplace-json',
                str(marketplace_file),
                '--dry-run',
            )
        )

        assert result['status'] == 'success'

    def test_generate_wildcards_declines_on_opencode(self, monkeypatch, tmp_path):
        """generate-wildcards on a non-Claude target returns a no-op, not wildcard lists."""
        inventory_file = tmp_path / 'inventory.json'
        inventory_file.write_text(
            json.dumps(
                {
                    'bundles': [{'name': 'plan-marshall', 'skills': [{'name': 'manage-files'}]}],
                    'statistics': {'total_bundles': 1, 'total_skills': 1, 'total_commands': 0},
                }
            )
        )

        force_opencode(monkeypatch)

        result = pf.cmd_generate_wildcards(
            parse_ns(
                'plan-marshall',
                'tools-permission-fix',
                'permission_fix.py',
                'generate-wildcards',
                '--input',
                str(inventory_file),
            )
        )

        assert_declines(result)

    def test_ensure_executor_declines_on_unsupported_runtime(self, monkeypatch, tmp_path, in_tmp_cwd):
        """ensure-executor on an unsupported non-Claude target returns a no-op, not the executor permission."""
        force_unsupported_runtime(monkeypatch)

        result = pf.cmd_ensure_executor(
            parse_ns(
                'plan-marshall',
                'tools-permission-fix',
                'permission_fix.py',
                'ensure-executor',
                '--target',
                'project',
                '--dry-run',
            )
        )

        assert_declines(result)

    def test_ensure_executor_succeeds_on_opencode(self, monkeypatch, tmp_path, in_tmp_cwd):
        """ensure-executor on OpenCode succeeds and sets executor permission."""
        force_opencode(monkeypatch)

        result = pf.cmd_ensure_executor(
            parse_ns(
                'plan-marshall',
                'tools-permission-fix',
                'permission_fix.py',
                'ensure-executor',
                '--target',
                'project',
                '--dry-run',
            )
        )

        assert result['status'] == 'success'
        assert 'python3 .plan/execute-script.py *' in result['executor_permission']

    def test_cleanup_scripts_declines_on_opencode(self, monkeypatch, tmp_path, in_tmp_cwd):
        """cleanup-scripts on a non-Claude target returns a no-op, not removal lists."""
        force_opencode(monkeypatch)

        result = pf.cmd_cleanup_scripts(
            parse_ns(
                'plan-marshall', 'tools-permission-fix', 'permission_fix.py', 'cleanup-scripts', '--target', 'project'
            )
        )

        assert_declines(result)

    def test_migrate_executor_declines_on_opencode(self, monkeypatch, tmp_path, in_tmp_cwd):
        """migrate-executor on a non-Claude target returns a no-op, not executor migration."""
        force_opencode(monkeypatch)

        result = pf.cmd_migrate_executor(
            parse_ns(
                'plan-marshall',
                'tools-permission-fix',
                'permission_fix.py',
                'migrate-executor',
                '--target',
                'project',
                '--dry-run',
            )
        )

        assert_declines(result)

    def test_apply_project_step_permissions_declines_on_opencode(self, monkeypatch, tmp_path):
        """apply-project-step-permissions on a non-Claude target returns a no-op, not Skill(...) rules."""
        marshal_file = tmp_path / 'marshal.json'
        marshal_file.write_text(
            json.dumps({'plan': {'phase-6-finalize': {'steps': ['project:finalize-step-plugin-doctor']}}})
        )
        settings_file = tmp_path / 'settings.json'
        write_settings(settings_file, [])

        force_opencode(monkeypatch)

        result = pf.cmd_apply_project_step_permissions(
            parse_ns(
                'plan-marshall',
                'tools-permission-fix',
                'permission_fix.py',
                'apply-project-step-permissions',
                '--marshal',
                str(marshal_file),
                '--settings',
                str(settings_file),
                '--dry-run',
            )
        )

        assert_declines(result)

    def test_remove_redundant_propagates_skipped_on_opencode(self, monkeypatch, tmp_path):
        """remove-redundant on a non-Claude target propagates the skipped third state, not success."""
        global_file = tmp_path / 'global.json'
        local_file = tmp_path / 'local.json'
        write_settings(global_file, ['Read(src/**)'])
        write_settings(local_file, ['Read(src/**)'])

        force_opencode(monkeypatch)

        result = pf.cmd_remove_redundant(
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

        assert result.get('status') == 'skipped'
        assert 'redundant' not in result

    def test_remove_redundant_scope_both_skipped_on_opencode(self, monkeypatch, tmp_path, in_tmp_cwd):
        """remove-redundant --scope both on a non-Claude target returns skipped, not a scope-resolution error."""
        force_opencode(monkeypatch)

        result = pf.cmd_remove_redundant(
            parse_ns(
                'plan-marshall', 'tools-permission-fix', 'permission_fix.py', 'remove-redundant', '--scope', 'both'
            )
        )

        assert result.get('status') == 'skipped'
        assert 'Could not resolve' not in str(result)


class TestOpenCodePermissionWritesUseTheListShape:
    """The OpenCode branches read and write the ``permissions`` list, never a map beside it."""

    CATCH_ALL = {'action': 'shell', 'resource': '*', 'effect': 'ask'}

    def _list_settings(self, tmp_path):
        config = tmp_path / 'opencode.json'
        config.write_text(
            json.dumps({'$schema': 'https://opencode.ai/config.json', 'permissions': [dict(self.CATCH_ALL)]}, indent=2)
            + '\n'
        )
        return config

    @staticmethod
    def _rules(config):
        data = json.loads(config.read_text())
        assert 'permission' not in data, 'a `permission` map must never be added beside a `permissions` list'
        return data['permissions']

    def test_ensure_wildcards_writes_into_the_list(self, monkeypatch, tmp_path):
        config = self._list_settings(tmp_path)
        marketplace_file = tmp_path / 'marketplace.json'
        marketplace_file.write_text(json.dumps({'bundles': {}}))
        force_opencode(monkeypatch)

        result = pf.cmd_ensure_wildcards(
            parse_ns(
                'plan-marshall',
                'tools-permission-fix',
                'permission_fix.py',
                'ensure-wildcards',
                '--settings',
                str(config),
                '--marketplace-json',
                str(marketplace_file),
            )
        )

        assert result['status'] == 'success'
        rules = self._rules(config)
        assert rules[0] == self.CATCH_ALL, 'the catch-all must stay first'
        executors = [
            index
            for index, rule in enumerate(rules)
            if rule['action'] == 'shell'
            and rule['resource'] == 'python3 .plan/execute-script.py *'
            and rule['effect'] == 'allow'
        ]
        assert executors and executors[0] > 0, 'the executor allow must land after the catch-all'

    def test_ensure_executor_writes_into_the_list(self, monkeypatch, tmp_path, in_tmp_cwd):
        config = self._list_settings(tmp_path)
        force_opencode(monkeypatch)

        result = pf.cmd_ensure_executor(
            parse_ns(
                'plan-marshall', 'tools-permission-fix', 'permission_fix.py', 'ensure-executor', '--target', 'project'
            )
        )

        assert result['action'] == 'added'
        rules = self._rules(config)
        assert any(
            rule['action'] == 'shell'
            and rule['resource'] == 'python3 .plan/execute-script.py *'
            and rule['effect'] == 'allow'
            for rule in rules
        )

    def test_ensure_writes_into_the_list(self, monkeypatch, tmp_path, in_tmp_cwd):
        config = self._list_settings(tmp_path)
        force_opencode(monkeypatch)

        result = pf.cmd_ensure(
            parse_ns(
                'plan-marshall',
                'tools-permission-fix',
                'permission_fix.py',
                'ensure',
                '--permissions',
                'deny(git push *)',
                '--target',
                'project',
            )
        )

        assert result['status'] == 'success'
        rules = self._rules(config)
        assert any(
            rule['action'] == 'shell' and rule['resource'] == 'git push *' and rule['effect'] == 'deny'
            for rule in rules
        )

    def test_ensure_writes_the_list_into_a_config_with_neither_shape(self, monkeypatch, tmp_path, in_tmp_cwd):
        config = tmp_path / 'opencode.json'
        config.write_text(json.dumps({'$schema': 'https://opencode.ai/config.json'}), encoding='utf-8')
        force_opencode(monkeypatch)

        pf.cmd_ensure(
            parse_ns(
                'plan-marshall',
                'tools-permission-fix',
                'permission_fix.py',
                'ensure',
                '--permissions',
                'read',
                '--target',
                'project',
            )
        )

        rules = self._rules(config)
        assert any(rule['action'] == 'read' and rule['effect'] == 'allow' for rule in rules)
