#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Behavioral tests for permission_doctor.py uncovered branches.

Complements ``test_permission.py`` (exact-duplicate / marketplace / suspicious
happy paths) by exercising the wildcard-coverage matcher, the permission-parts
parser edge, the approved-permissions loader across all its branches, the
already-approved and error branches of detect-suspicious, the covered-by-wildcard
and load-error branches of detect-redundant, and the marketplace-permission
classifier edges. All read-only: every call is driven against synthetic
``tmp_path`` settings files via explicit ``--settings`` paths (``scope=None``) so
no real ``~/.claude`` or project settings are read.
"""

import json

import permission_common

from conftest import load_script_module, parse_ns

pd = load_script_module('plan-marshall', 'tools-permission-doctor', 'permission_doctor.py', 'pd_behavior')


def _write_settings(path, allow):
    """Write a minimal settings.json with the given allow list."""
    path.write_text(json.dumps({'permissions': {'allow': allow, 'deny': [], 'ask': []}}))


# =============================================================================
# is_covered_by_wildcard — the matcher
# =============================================================================


class TestIsCoveredByWildcard:
    """Test is_covered_by_wildcard across its matching and non-matching branches."""

    def test_colon_star_prefix_covers_specific(self):
        """A 'name:*' wildcard covers a more specific same-prefix permission."""
        assert pd.is_covered_by_wildcard('Bash(git:status)', 'Bash(git:*)') is True

    def test_path_prefix_covers_nested_path(self):
        """A Read/Write/Edit path wildcard covers a deeper nested path."""
        assert pd.is_covered_by_wildcard('Read(src/lib/file.txt)', 'Read(src/**)') is True

    def test_type_mismatch_not_covered(self):
        """Differing permission types are never covered."""
        assert pd.is_covered_by_wildcard('Read(src/x)', 'Write(src/**)') is False

    def test_unrelated_specific_not_covered(self):
        """A non-overlapping path is not covered by the wildcard."""
        assert pd.is_covered_by_wildcard('Read(other/x)', 'Read(src/**)') is False


# =============================================================================
# extract_permission_parts — non-matching branch
# =============================================================================


class TestExtractPermissionParts:
    """Test extract_permission_parts parsing."""

    def test_well_formed_permission(self):
        """A well-formed permission splits into type and pattern."""
        assert pd.extract_permission_parts('Bash(git:*)') == ('Bash', 'git:*')

    def test_malformed_permission_returns_empty_pattern(self):
        """A string without the type(pattern) shape returns an empty pattern."""
        assert pd.extract_permission_parts('garbage') == ('garbage', '')


# =============================================================================
# is_marketplace_permission — classifier edges
# =============================================================================


class TestIsMarketplacePermission:
    """Test is_marketplace_permission classification branches."""

    def test_non_marketplace_bash(self):
        """A plain Bash permission is not a marketplace permission."""
        assert pd.is_marketplace_permission('Bash(git:*)') is False

    def test_malformed_slashcommand_assumed_marketplace(self):
        """A SlashCommand string that fails the regex falls through to marketplace=True."""
        assert pd.is_marketplace_permission('SlashCommand(/unterminated') is True


# =============================================================================
# load_approved_permissions — all branches
# =============================================================================


class TestLoadApprovedPermissions:
    """Test load_approved_permissions across its four return branches."""

    def test_none_path_returns_empty(self):
        """A None path yields an empty set."""
        assert pd.load_approved_permissions(None) == set()

    def test_missing_file_returns_empty(self, tmp_path):
        """A non-existent file yields an empty set."""
        assert pd.load_approved_permissions(str(tmp_path / 'nope.json')) == set()

    def test_valid_file_returns_approved_set(self, tmp_path):
        """A well-formed run-config returns the approved permissions as a set."""
        approved = tmp_path / 'run-config.json'
        approved.write_text(
            json.dumps(
                {
                    'commands': {
                        'setup-project-permissions': {
                            'user_approved_permissions': ['Bash(sudo:*)', 'Write(/etc/**)']
                        }
                    }
                }
            )
        )

        result = pd.load_approved_permissions(str(approved))

        assert result == {'Bash(sudo:*)', 'Write(/etc/**)'}

    def test_malformed_json_returns_empty(self, tmp_path):
        """A malformed run-config file yields an empty set rather than raising."""
        approved = tmp_path / 'run-config.json'
        approved.write_text('{not valid json')

        assert pd.load_approved_permissions(str(approved)) == set()


# =============================================================================
# detect-redundant — covered-by-wildcard and load-error branches
# =============================================================================


class TestDetectRedundantBranches:
    """Test cmd_detect_redundant branches the happy-path suite omits."""

    def test_covered_by_wildcard_is_redundant(self, tmp_path):
        """A local permission covered by a broader global wildcard is flagged redundant."""
        global_file = tmp_path / 'global.json'
        _write_settings(global_file, ['Read(src/**)'])
        local_file = tmp_path / 'local.json'
        _write_settings(local_file, ['Read(src/lib/file.txt)'])

        result = pd.cmd_detect_redundant(
            parse_ns('plan-marshall', 'tools-permission-doctor', 'permission_doctor.py', 'detect-redundant', '--global-settings', str(global_file), '--local-settings', str(local_file))
        )

        assert result['status'] == 'success'
        entry = next(r for r in result['redundant'] if r['permission'] == 'Read(src/lib/file.txt)')
        assert entry['type'] == 'covered_by_wildcard'
        assert entry['covered_by'] == 'Read(src/**)'

    def test_global_load_error(self, tmp_path):
        """A missing global settings file surfaces a structured error."""
        local_file = tmp_path / 'local.json'
        _write_settings(local_file, [])

        result = pd.cmd_detect_redundant(
            parse_ns('plan-marshall', 'tools-permission-doctor', 'permission_doctor.py', 'detect-redundant', '--global-settings', str(tmp_path / 'missing.json'), '--local-settings', str(local_file))
        )

        assert result['status'] == 'error'
        assert result['global_exists'] is False

    def test_local_load_error(self, tmp_path):
        """A missing local settings file surfaces a structured error."""
        global_file = tmp_path / 'global.json'
        _write_settings(global_file, [])

        result = pd.cmd_detect_redundant(
            parse_ns('plan-marshall', 'tools-permission-doctor', 'permission_doctor.py', 'detect-redundant', '--global-settings', str(global_file), '--local-settings', str(tmp_path / 'missing.json'))
        )

        assert result['status'] == 'error'
        assert result['local_exists'] is False


# =============================================================================
# detect-suspicious — already-approved, error, and approved_file branches
# =============================================================================


class TestDetectSuspiciousBranches:
    """Test cmd_detect_suspicious approved-permission and error branches."""

    def test_approved_suspicious_moved_to_already_approved(self, tmp_path):
        """A suspicious permission present in the approved set is reported as already-approved."""
        settings_file = tmp_path / 'settings.json'
        _write_settings(settings_file, ['Bash(sudo:*)'])
        approved = tmp_path / 'run-config.json'
        approved.write_text(
            json.dumps(
                {'commands': {'setup-project-permissions': {'user_approved_permissions': ['Bash(sudo:*)']}}}
            )
        )

        result = pd.cmd_detect_suspicious(
            parse_ns('plan-marshall', 'tools-permission-doctor', 'permission_doctor.py', 'detect-suspicious', '--settings', str(settings_file), '--approved-file', str(approved))
        )

        assert result['status'] == 'success'
        assert 'Bash(sudo:*)' in result['already_approved']
        suspicious_perms = [s['permission'] for s in result['suspicious']]
        assert 'Bash(sudo:*)' not in suspicious_perms
        assert result['approved_file'] == str(approved)

    def test_error_on_missing_settings(self, tmp_path):
        """A missing settings file surfaces a structured error."""
        result = pd.cmd_detect_suspicious(
            parse_ns('plan-marshall', 'tools-permission-doctor', 'permission_doctor.py', 'detect-suspicious', '--settings', str(tmp_path / 'missing.json'))
        )

        assert result['status'] == 'error'

    def test_severity_breakdown_counts(self, tmp_path):
        """The summary tallies suspicious findings by severity bucket."""
        settings_file = tmp_path / 'settings.json'
        # one high (sudo), one low (curl) — exercises two severity buckets.
        _write_settings(settings_file, ['Bash(sudo:*)', 'Bash(curl:*)', 'Bash(git:*)'])

        result = pd.cmd_detect_suspicious(
            parse_ns('plan-marshall', 'tools-permission-doctor', 'permission_doctor.py', 'detect-suspicious', '--settings', str(settings_file))
        )

        assert result['status'] == 'success'
        by_severity = result['summary']['by_severity']
        assert by_severity['high'] == 1
        assert by_severity['low'] == 1


# =============================================================================
# detect-missing-project-step-permissions — settings load error
# =============================================================================


def test_detect_missing_settings_load_error(tmp_path):
    """A valid marshal but a missing settings file surfaces a structured error."""
    marshal_file = tmp_path / 'marshal.json'
    marshal_file.write_text(
        json.dumps({'plan': {'phase-6-finalize': {'steps': ['project:finalize-step-plugin-doctor']}}})
    )

    result = pd.cmd_detect_missing_project_step_permissions(
        parse_ns('plan-marshall', 'tools-permission-doctor', 'permission_doctor.py', 'detect-missing-project-step-permissions', '--marshal', str(marshal_file), '--settings', str(tmp_path / 'missing.json'))
    )

    assert result['status'] == 'error'


# =============================================================================
# Non-Claude target: detect-* route must not report a FALSE ZERO
# =============================================================================
# These tests pin the ADR-019 obligation: the Claude rule-pack analysis does
# not apply to a non-Claude target, so the direct-script detect-* route must
# return a ``skipped`` third state rather than walking empty allow lists and
# reporting a clean zero.  Red-first: each assertion fails against current HEAD.


class TestDetectNonClaudeSkipped:
    """On a non-Claude target the direct detect-* route returns 'skipped'."""

    @staticmethod
    def _make_opencode_runtime():
        from opencode_runtime import OpenCodeRuntime
        return OpenCodeRuntime()

    @staticmethod
    def _force_opencode(monkeypatch):
        """Point the runtime-resolution seam at the OpenCode runtime.

        Both ``permission_common.is_claude_target`` and ``permission_common.load_settings``
        resolve the active runtime through ``permission_common._runtime_for_target``,
        so patching that seam makes the whole route behave as a non-Claude target.
        """
        monkeypatch.setattr(permission_common, '_runtime_for_target', TestDetectNonClaudeSkipped._make_opencode_runtime)

    def test_detect_suspicious_skipped_on_opencode(self, monkeypatch, tmp_path):
        """detect-suspicious on a non-Claude target: 'skipped', not 'success' with zero."""
        settings_file = tmp_path / 'settings.json'
        _write_settings(settings_file, ['Read(**)'])

        self._force_opencode(monkeypatch)

        result = pd.cmd_detect_suspicious(
            parse_ns('plan-marshall', 'tools-permission-doctor', 'permission_doctor.py',
                     'detect-suspicious', '--settings', str(settings_file))
        )

        assert result['status'] == 'skipped'
        assert 'suspicious' not in result or result.get('summary', {}).get('total_suspicious', -1) == -1

    def test_detect_redundant_skipped_on_opencode(self, monkeypatch, tmp_path):
        """detect-redundant on a non-Claude target: 'skipped', not 'success' with zero."""
        global_file = tmp_path / 'global.json'
        local_file = tmp_path / 'local.json'
        _write_settings(global_file, ['Read(src/**)'])
        _write_settings(local_file, ['Read(src/**)'])

        self._force_opencode(monkeypatch)

        result = pd.cmd_detect_redundant(
            parse_ns('plan-marshall', 'tools-permission-doctor', 'permission_doctor.py',
                     'detect-redundant', '--global-settings', str(global_file),
                     '--local-settings', str(local_file))
        )

        assert result['status'] == 'skipped'

    def test_detect_missing_steps_skipped_on_opencode(self, monkeypatch, tmp_path):
        """detect-missing-project-step-permissions on non-Claude: 'skipped'."""
        marshal_file = tmp_path / 'marshal.json'
        marshal_file.write_text(
            json.dumps({'plan': {'phase-6-finalize': {'steps': ['project:finalize-step-plugin-doctor']}}})
        )
        settings_file = tmp_path / 'settings.json'
        _write_settings(settings_file, [])

        self._force_opencode(monkeypatch)

        result = pd.cmd_detect_missing_project_step_permissions(
            parse_ns('plan-marshall', 'tools-permission-doctor', 'permission_doctor.py',
                     'detect-missing-project-step-permissions',
                     '--marshal', str(marshal_file),
                     '--settings', str(settings_file))
        )

        assert result['status'] == 'skipped'

    def test_detect_suspicious_genuine_zero_on_claude(self, monkeypatch, tmp_path):
        """On a Claude target with empty allow list: 'success' with zero (genuine zero)."""
        settings_file = tmp_path / 'settings.json'
        _write_settings(settings_file, [])

        # No monkeypatch — _active_runtime resolves to the default (Claude) target.

        result = pd.cmd_detect_suspicious(
            parse_ns('plan-marshall', 'tools-permission-doctor', 'permission_doctor.py',
                     'detect-suspicious', '--settings', str(settings_file))
        )

        assert result['status'] == 'success'
        assert result['summary']['total_suspicious'] == 0
