#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Behavioral tests for permission_fix.py uncovered branches.

Complements ``test_permission_fix.py`` (which covers the happy-path dry-run and
subprocess plumbing) by exercising the write-applied paths, the error paths, and
the small pure helpers (normalization, wildcard generation, bundle-shape probes,
prefix extraction, inventory scanning) against synthetic ``tmp_path`` settings
files. The module is loaded in-process via ``load_script_module`` so coverage is
attributed; the WRITE-capable subcommands are driven only against tmp settings
copies (explicit ``--settings`` paths, or ``monkeypatch.chdir`` into ``tmp_path``
for the ``--target project`` resolvers) — never the developer's real settings.
"""

import ast
import json
from argparse import Namespace
from pathlib import Path

import pytest

from conftest import load_script_module, parse_ns

# Unique module name so the load is isolated and coverage is attributed to the
# permission_fix.py source file in this session.
pf = load_script_module('plan-marshall', 'tools-permission-fix', 'permission_fix.py', 'pf_behavior')


def _write_settings(path, allow):
    """Write a minimal settings.json with the given allow list."""
    path.write_text(json.dumps({'permissions': {'allow': allow, 'deny': [], 'ask': []}}))


def _read_allow(path):
    """Read back the allow list from a settings file."""
    return json.loads(path.read_text())['permissions']['allow']


# =============================================================================
# normalize_path_perm — pure helper
# =============================================================================


class TestNormalizePathPerm:
    """Test normalize_path_perm path normalization rules."""

    @pytest.mark.parametrize(
        ('permission', 'expected', 'expect_changed'),
        [
            ('Read(src/)', 'Read(src)', True),
            ('Read(src)', 'Read(src)', False),
            # The path component ends with '*', so the trailing-slash rewrite is skipped.
            ('Read(src/*/)', 'Read(src/*/)', False),
            ('not-a-permission', 'not-a-permission', False),
        ],
        ids=[
            'a-directory-trailing-slash-is-stripped',
            'a-path-without-a-trailing-slash-is-already-normal',
            'a-wildcard-path-keeps-its-trailing-slash',
            'a-string-outside-the-permission-shape-is-returned-verbatim',
        ],
    )
    def test_normalize_path_perm(self, permission, expected, expect_changed):
        """The changed flag is True exactly when the returned string differs from the input."""
        result, changed = pf.normalize_path_perm(permission)

        assert result == expected
        assert changed is expect_changed


# =============================================================================
# apply-fixes — write-applied and error paths
# =============================================================================


class TestApplyFixesApplied:
    """Test cmd_apply_fixes write path and error path."""

    def test_applies_path_fix_and_writes_file(self, tmp_path):
        """Non-dry-run normalizes a trailing-slash path, writes, and reports applied."""
        # Arrange
        settings_file = tmp_path / 'settings.json'
        _write_settings(settings_file, ['Read(src/)', 'Bash(git:*)'])

        # Act
        result = pf.cmd_apply_fixes(
            parse_ns(
                'plan-marshall',
                'tools-permission-fix',
                'permission_fix.py',
                'apply-fixes',
                '--settings',
                str(settings_file),
            )
        )

        # Assert
        assert result['status'] == 'success'
        assert result['paths_fixed'] == 1
        assert result['applied'] is True
        allow = _read_allow(settings_file)
        assert 'Read(src)' in allow
        assert 'Read(src/)' not in allow

    def test_error_on_missing_settings_file(self, tmp_path):
        """A non-existent settings path surfaces a structured error."""
        result = pf.cmd_apply_fixes(
            parse_ns(
                'plan-marshall',
                'tools-permission-fix',
                'permission_fix.py',
                'apply-fixes',
                '--settings',
                str(tmp_path / 'nope.json'),
            )
        )

        assert result['status'] == 'error'
        assert 'not found' in result['error']

    def test_no_changes_reports_not_applied(self, tmp_path):
        """An already-clean, already-sorted, default-complete file makes no changes."""
        settings_file = tmp_path / 'settings.json'
        # Pre-seed with all defaults + a sorted extra so nothing is added/sorted/fixed.
        _write_settings(
            settings_file,
            sorted(['Bash(git:*)', 'Edit(.plan/**)', 'Read(~/.claude/plugins/cache/**)']),
        )

        result = pf.cmd_apply_fixes(
            parse_ns(
                'plan-marshall',
                'tools-permission-fix',
                'permission_fix.py',
                'apply-fixes',
                '--settings',
                str(settings_file),
            )
        )

        assert result['status'] == 'success'
        assert result['changes_made'] is False
        assert result['applied'] is False


# =============================================================================
# resolve_settings_arg — the settings seam four subcommands share
# =============================================================================


class TestResolveSettingsArg:
    """``resolve_settings_arg`` resolves the project file whose entries take effect.

    Claude lets ``.claude/settings.local.json`` override ``.claude/settings.json``,
    so when both exist a change written to the shared file is overridden and never
    observed. Every subcommand sharing this helper MUTATES what it resolves, so the
    helper resolves the read preference — the local file — on both the
    ``--scope project`` arm and the no-flag fall-through.

    Driven against a REAL ``.claude`` tree under a chdir'd ``tmp_path`` rather than
    a stubbed resolver. The defect this seam was moved to fix IS a resolver
    preference, and a test that monkeypatches the resolver away cannot observe
    which preference the code asks for.
    """

    def _project(self, tmp_path, monkeypatch, *, local: bool):
        """Build a project tree with a shared settings file and optionally a local one."""
        claude = tmp_path / '.claude'
        claude.mkdir(parents=True, exist_ok=True)
        _write_settings(claude / 'settings.json', [])
        if local:
            _write_settings(claude / 'settings.local.json', [])
        monkeypatch.chdir(tmp_path)
        return claude

    def test_both_arms_resolve_the_overriding_local_file(self, tmp_path, monkeypatch):
        """``--scope project`` and the no-flag fall-through agree, and both pick the local file.

        Asserting them together is the point: they are separate branches in the
        helper, and letting them disagree is how one subcommand comes to edit a
        different file from the next.
        """
        claude = self._project(tmp_path, monkeypatch, local=True)

        assert pf.resolve_settings_arg(Namespace(settings=None, scope='project')) == str(claude / 'settings.local.json')
        assert pf.resolve_settings_arg(Namespace(settings=None, scope=None)) == str(claude / 'settings.local.json')

    def test_without_a_local_file_both_arms_fall_back_to_the_shared_one(self, tmp_path, monkeypatch):
        """The control: the preference is a preference, not a hard-wired filename."""
        claude = self._project(tmp_path, monkeypatch, local=False)

        assert pf.resolve_settings_arg(Namespace(settings=None, scope='project')) == str(claude / 'settings.json')
        assert pf.resolve_settings_arg(Namespace(settings=None, scope=None)) == str(claude / 'settings.json')

    def test_an_explicit_settings_path_is_honoured_untouched(self, tmp_path, monkeypatch):
        """``--settings`` outranks both arms — the operator named a file."""
        self._project(tmp_path, monkeypatch, local=True)
        explicit = tmp_path / 'elsewhere.json'

        assert pf.resolve_settings_arg(Namespace(settings=explicit, scope=None)) == str(explicit)

    def test_scope_global_still_resolves_outside_the_project(self, tmp_path, monkeypatch):
        """Boundary: only the project arm moved; ``--scope global`` keeps ``get_settings_path``."""
        claude = self._project(tmp_path, monkeypatch, local=True)

        resolved = pf.resolve_settings_arg(Namespace(settings=None, scope='global'))

        assert not resolved.startswith(str(claude))


class TestSharedSeamCallSites:
    """Each subcommand routed through ``resolve_settings_arg`` resolves the same file.

    The helper is shared, so one call site could be re-pointed at a different
    resolver without any helper-level test noticing. One row per call site is what
    makes that divergence visible.
    """

    def _dual_file_project(self, tmp_path, monkeypatch):
        """A project where BOTH settings files exist, so the preference is observable."""
        claude = tmp_path / '.claude'
        claude.mkdir(parents=True, exist_ok=True)
        _write_settings(claude / 'settings.json', [])
        _write_settings(claude / 'settings.local.json', [])
        monkeypatch.chdir(tmp_path)
        return claude / 'settings.local.json'

    def test_apply_fixes_resolves_the_local_file(self, tmp_path, monkeypatch):
        """apply-fixes — call site 1 of 4."""
        local = self._dual_file_project(tmp_path, monkeypatch)

        result = pf.cmd_apply_fixes(
            parse_ns('plan-marshall', 'tools-permission-fix', 'permission_fix.py', 'apply-fixes', '--scope', 'project')
        )

        assert result['settings_path'] == str(local)

    def test_consolidate_resolves_the_local_file(self, tmp_path, monkeypatch):
        """consolidate — call site 2 of 4."""
        local = self._dual_file_project(tmp_path, monkeypatch)

        result = pf.cmd_consolidate(
            parse_ns(
                'plan-marshall',
                'tools-permission-fix',
                'permission_fix.py',
                'consolidate',
                '--scope',
                'project',
                '--dry-run',
            )
        )

        assert result['settings_path'] == str(local)

    def test_ensure_wildcards_resolves_the_local_file_and_writes_through_it(self, tmp_path, monkeypatch):
        """ensure-wildcards — call site 3 of 4.

        This one also asserts the WRITE landed, because a ``--scope`` call must
        never fall back to a ``None`` settings path for the save; resolving
        correctly and then saving somewhere else would satisfy a path-only check.
        """
        local = self._dual_file_project(tmp_path, monkeypatch)
        marketplace_file = tmp_path / 'marketplace.json'
        marketplace_file.write_text(json.dumps({'bundles': {'foo': {'skills': ['s'], 'commands': ['c']}}}))

        result = pf.cmd_ensure_wildcards(
            parse_ns(
                'plan-marshall',
                'tools-permission-fix',
                'permission_fix.py',
                'ensure-wildcards',
                '--scope',
                'project',
                '--marketplace-json',
                str(marketplace_file),
            )
        )

        assert result['status'] == 'success'
        assert result['applied'] is True
        assert result['settings_path'] == str(local)
        assert 'Skill(foo:*)' in _read_allow(local)

    def test_apply_project_step_permissions_resolves_the_local_file(self, tmp_path, monkeypatch):
        """apply-project-step-permissions — call site 4 of 4."""
        local = self._dual_file_project(tmp_path, monkeypatch)
        marshal_file = tmp_path / 'marshal.json'
        marshal_file.write_text(
            json.dumps({'plan': {'phase-6-finalize': {'steps': ['project:finalize-step-plugin-doctor']}}})
        )

        result = pf.cmd_apply_project_step_permissions(
            parse_ns(
                'plan-marshall',
                'tools-permission-fix',
                'permission_fix.py',
                'apply-project-step-permissions',
                '--marshal',
                str(marshal_file),
                '--scope',
                'project',
                '--dry-run',
            )
        )

        assert result['settings_path'] == str(local)

    def test_target_project_on_add_still_resolves_the_shared_file(self, tmp_path, monkeypatch):
        """Boundary control: ``--target`` was deliberately NOT moved to the read preference.

        ``resolve_settings_arg`` serves these four subcommands; ``get_settings_path``
        serves them plus six more reached through ``--target``. Only the first seam
        moved, and that four-vs-ten line is the scope of the change — without this
        row the switch could silently widen to all ten and every row above would
        still pass.
        """
        local = self._dual_file_project(tmp_path, monkeypatch)
        shared = local.parent / 'settings.json'
        local_before = local.read_bytes()

        pf.cmd_add(
            parse_ns(
                'plan-marshall',
                'tools-permission-fix',
                'permission_fix.py',
                'add',
                '--permission',
                'Bash(npm:*)',
                '--target',
                'project',
            )
        )

        assert 'Bash(npm:*)' in _read_allow(shared)
        assert local.read_bytes() == local_before


class TestSharedSeamCallSiteRosterIsDerived:
    """``TestSharedSeamCallSites`` carries a row for every ``resolve_settings_arg`` caller.

    The class above is a hand-written roster: one method per call site. A fifth
    subcommand routed through the seam would add a call site that no method
    exercises, and every existing method would still pass — the roster would be
    silently short. This guard closes that by deriving BOTH sides from source:
    the callers from ``permission_fix.py``, the covered handlers from this
    module. Neither side is transcribed, so neither can fall behind the other.

    The comparison is a SUBSET, not an equality. ``TestSharedSeamCallSites`` also
    drives ``pf.cmd_add`` as the four-vs-ten boundary control, and ``cmd_add`` is
    deliberately not a seam caller — so the covered set is legitimately a proper
    superset and equality would fail on the control.

    Both sides are read statically rather than by inspecting live function
    objects: a runtime inspection cannot see a call site that never executes,
    which is precisely the drift this guard exists to catch.
    """

    #: The shared helper whose call sites the roster above must cover.
    SEAM = 'resolve_settings_arg'

    #: The roster class whose methods are the coverage being checked.
    ROSTER_CLASS = 'TestSharedSeamCallSites'

    @staticmethod
    def _seam_callers(source: str, seam: str) -> set[str]:
        """Names of the functions in ``source`` whose body calls ``seam`` by name.

        The seam's own definition is excluded, so a future recursive call cannot
        make the helper report itself as one of its own callers.
        """
        callers = set()
        for node in ast.walk(ast.parse(source)):
            if not isinstance(node, ast.FunctionDef) or node.name == seam:
                continue
            for inner in ast.walk(node):
                if isinstance(inner, ast.Call) and isinstance(inner.func, ast.Name) and inner.func.id == seam:
                    callers.add(node.name)
                    break
        return callers

    @staticmethod
    def _roster_handlers(source: str, class_name: str) -> set[str]:
        """Names of the ``pf.cmd_*`` handlers driven inside ``class_name``."""
        covered = set()
        for node in ast.walk(ast.parse(source)):
            if not isinstance(node, ast.ClassDef) or node.name != class_name:
                continue
            for inner in ast.walk(node):
                func = inner.func if isinstance(inner, ast.Call) else None
                if (
                    isinstance(func, ast.Attribute)
                    and isinstance(func.value, ast.Name)
                    and func.value.id == 'pf'
                    and func.attr.startswith('cmd_')
                ):
                    covered.add(func.attr)
        return covered

    def test_every_seam_caller_has_a_roster_row(self):
        """Every derived ``resolve_settings_arg`` caller is driven by the roster class."""
        module_path = Path(pf.__file__)
        callers = self._seam_callers(module_path.read_text(encoding='utf-8'), self.SEAM)
        covered = self._roster_handlers(Path(__file__).read_text(encoding='utf-8'), self.ROSTER_CLASS)

        # Non-vacuity FIRST: a subset assertion over an empty left side passes no
        # matter what the right side holds, so a derivation that silently stopped
        # matching would turn this guard green rather than red.
        assert callers, (
            f'Derived ZERO callers of {self.SEAM}() from {module_path.name}, so the subset '
            f'check below would pass vacuously. Population sizes: callers=0, '
            f'covered={len(covered)}. The derivation, not the roster, is what broke.'
        )

        uncovered = callers - covered
        assert not uncovered, (
            f'{len(uncovered)} of {len(callers)} {self.SEAM}() call site(s) have no row in '
            f'{self.ROSTER_CLASS}: {sorted(uncovered)}. Population sizes: '
            f'callers={len(callers)}, covered={len(covered)}. Add one method per '
            f'uncovered handler asserting it resolves the overriding local file.'
        )

    def test_the_derivation_reports_a_fifth_caller_as_uncovered(self):
        """The matched negative control: a caller with no roster row is derived as uncovered.

        The guard above can only ever be observed PASSING against the real tree,
        so a derivation that quietly stopped matching would look exactly like a
        roster that is complete. Driving both derivations over synthetic sources
        is what makes the failure path itself observable — and it pins the two
        behaviours the guard rests on: the seam's own definition is not counted
        as a caller, and a handler absent from the roster survives the
        subtraction.
        """
        module_source = (
            'def resolve_settings_arg(args):\n'
            '    return str(args)\n'
            'def cmd_on_the_roster(args):\n'
            '    return resolve_settings_arg(args)\n'
            'def cmd_added_without_a_row(args):\n'
            '    return resolve_settings_arg(args)\n'
        )
        roster_source = 'class Roster:\n    def test_one(self):\n        pf.cmd_on_the_roster(None)\n'

        callers = self._seam_callers(module_source, self.SEAM)
        covered = self._roster_handlers(roster_source, 'Roster')

        assert callers == {'cmd_on_the_roster', 'cmd_added_without_a_row'}
        assert self.SEAM not in callers
        assert covered == {'cmd_on_the_roster'}
        assert callers - covered == {'cmd_added_without_a_row'}


# =============================================================================
# consolidate — timestamp/date parsing, wildcard generation, write path
# =============================================================================


class TestParseTimestampedPermission:
    """Test parse_timestamped_permission across its three branches."""

    def test_full_timestamp_parsed(self):
        """A YYYY-MM-DD-HHMMSS suffix parses via the timestamp pattern."""
        parsed = pf.parse_timestamped_permission('Read(target/build-2025-11-20-174411.log)')

        assert parsed is not None
        assert parsed['base_name'] == 'build'
        assert parsed['extension'] == 'log'
        assert parsed['path_prefix'] == 'target/'

    def test_date_only_parsed(self):
        """A date-only YYYY-MM-DD suffix parses via the date pattern."""
        parsed = pf.parse_timestamped_permission('Read(logs/app-2025-11-20.log)')

        assert parsed is not None
        assert parsed['base_name'] == 'app'
        assert parsed['timestamp'] == '2025-11-20'

    def test_non_timestamped_returns_none(self):
        """A plain permission with no timestamp returns None."""
        assert pf.parse_timestamped_permission('Bash(git:*)') is None


class TestGenerateWildcard:
    """Test generate_wildcard prefix collapsing."""

    @pytest.mark.parametrize(
        ('group', 'expected'),
        [
            ([], ''),
            (
                [
                    {'type': 'Read', 'base_name': 'build', 'extension': 'log', 'path_prefix': 'target/'},
                    {'type': 'Read', 'base_name': 'build', 'extension': 'log', 'path_prefix': 'target/'},
                ],
                'Read(target/build-*.log)',
            ),
            (
                [
                    {'type': 'Read', 'base_name': 'build', 'extension': 'log', 'path_prefix': 'a/'},
                    {'type': 'Read', 'base_name': 'build', 'extension': 'log', 'path_prefix': 'b/'},
                ],
                'Read(**/build-*.log)',
            ),
        ],
        ids=[
            'an-empty-group-produces-no-wildcard',
            'one-shared-prefix-is-preserved-verbatim',
            'differing-prefixes-collapse-to-a-recursive-double-star',
        ],
    )
    def test_generate_wildcard(self, group, expected):
        """How many distinct path prefixes the group carries decides the emitted path."""
        assert pf.generate_wildcard(group) == expected


class TestConsolidateApplied:
    """Test cmd_consolidate write path, date-only grouping, and error path."""

    def test_applies_consolidation_and_writes(self, tmp_path):
        """Non-dry-run removes timestamped entries, adds the wildcard, and writes the file."""
        # Arrange
        settings_file = tmp_path / 'settings.json'
        _write_settings(
            settings_file,
            [
                'Bash(git:*)',
                'Read(target/build-2025-11-20-174411.log)',
                'Read(target/build-2025-11-21-093000.log)',
            ],
        )

        # Act
        result = pf.cmd_consolidate(
            parse_ns(
                'plan-marshall',
                'tools-permission-fix',
                'permission_fix.py',
                'consolidate',
                '--settings',
                str(settings_file),
            )
        )

        # Assert
        assert result['status'] == 'success'
        assert result['applied'] is True
        assert result['consolidated'] == 2
        allow = _read_allow(settings_file)
        assert 'Read(target/build-*.log)' in allow
        assert 'Read(target/build-2025-11-20-174411.log)' not in allow
        assert 'Bash(git:*)' in allow

    def test_date_only_group_consolidated(self, tmp_path):
        """Two date-only-suffixed permissions in one group consolidate to a wildcard."""
        settings_file = tmp_path / 'settings.json'
        _write_settings(
            settings_file,
            ['Read(logs/app-2025-11-20.log)', 'Read(logs/app-2025-11-21.log)'],
        )

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
        assert result['consolidated'] == 2
        assert 'Read(logs/app-*.log)' in result['wildcards_added']

    def test_error_on_missing_settings(self, tmp_path):
        """A non-existent settings path surfaces a structured error."""
        result = pf.cmd_consolidate(
            parse_ns(
                'plan-marshall',
                'tools-permission-fix',
                'permission_fix.py',
                'consolidate',
                '--settings',
                str(tmp_path / 'missing.json'),
            )
        )

        assert result['status'] == 'error'
        assert 'not found' in result['error']


# =============================================================================
# has_skills / has_commands / generate_required_wildcards — bundle-shape probes
# =============================================================================


class TestBundleShapeProbes:
    """Test the marketplace bundle-shape predicate helpers."""

    def test_has_skills_empty_list_is_false(self):
        """An explicit empty skills list means the bundle has no skills."""
        assert pf.has_skills({'skills': []}) is False

    def test_has_skills_none_with_commands_present_is_false(self):
        """Skills absent but commands present means skills are genuinely absent."""
        assert pf.has_skills({'commands': ['c']}) is False

    def test_has_skills_both_absent_assumes_present(self):
        """When neither key exists, the real marketplace.json shape assumes skills."""
        assert pf.has_skills({}) is True

    def test_has_commands_empty_list_is_false(self):
        """An explicit empty commands list means the bundle has no commands."""
        assert pf.has_commands({'commands': []}) is False

    def test_has_commands_none_with_skills_present_is_false(self):
        """Commands absent but skills present means commands are genuinely absent."""
        assert pf.has_commands({'skills': ['s']}) is False

    def test_generate_required_wildcards_skips_blank_bundle_name(self):
        """A blank bundle name is skipped while real bundles still produce wildcards."""
        marketplace = {'bundles': {'': {'skills': ['s']}, 'foo': {'skills': ['s'], 'commands': ['c']}}}

        wildcards = pf.generate_required_wildcards(marketplace)

        assert 'Skill(foo:*)' in wildcards
        assert 'SlashCommand(/foo:*)' in wildcards
        assert not any(w.startswith('Skill(:') for w in wildcards)


# =============================================================================
# ensure-wildcards — write path and error paths
# =============================================================================


class TestEnsureWildcardsApplied:
    """Test cmd_ensure_wildcards write path and its error branches."""

    def test_applies_and_writes(self, tmp_path):
        """Non-dry-run appends the missing wildcards to the settings file."""
        settings_file = tmp_path / 'settings.json'
        _write_settings(settings_file, ['Bash(git:*)'])
        marketplace_file = tmp_path / 'marketplace.json'
        marketplace_file.write_text(json.dumps({'bundles': {'foo': {'skills': ['s'], 'commands': ['c']}}}))

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
            )
        )

        assert result['status'] == 'success'
        assert result['applied'] is True
        allow = _read_allow(settings_file)
        assert 'Skill(foo:*)' in allow
        assert 'SlashCommand(/foo:*)' in allow

    def test_error_on_missing_settings(self, tmp_path):
        """A missing settings file surfaces a structured error before reading the marketplace."""
        result = pf.cmd_ensure_wildcards(
            parse_ns(
                'plan-marshall',
                'tools-permission-fix',
                'permission_fix.py',
                'ensure-wildcards',
                '--settings',
                str(tmp_path / 'none.json'),
                '--marketplace-json',
                str(tmp_path / 'm.json'),
                '--dry-run',
            )
        )

        assert result['status'] == 'error'
        assert 'not found' in result['error']

    def test_error_on_missing_marketplace_file(self, tmp_path):
        """A missing marketplace.json surfaces a marketplace-not-found error."""
        settings_file = tmp_path / 'settings.json'
        _write_settings(settings_file, [])

        result = pf.cmd_ensure_wildcards(
            parse_ns(
                'plan-marshall',
                'tools-permission-fix',
                'permission_fix.py',
                'ensure-wildcards',
                '--settings',
                str(settings_file),
                '--marketplace-json',
                str(tmp_path / 'missing.json'),
                '--dry-run',
            )
        )

        assert result['status'] == 'error'
        assert 'Marketplace file not found' in result['error']

    def test_error_on_invalid_marketplace_json(self, tmp_path):
        """Malformed marketplace JSON surfaces an invalid-JSON error."""
        settings_file = tmp_path / 'settings.json'
        _write_settings(settings_file, [])
        marketplace_file = tmp_path / 'marketplace.json'
        marketplace_file.write_text('{not json')

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

        assert result['status'] == 'error'
        assert 'Invalid JSON' in result['error']

    def test_scope_project_resolves_settings_via_ops(self, tmp_path, monkeypatch):
        """ensure-wildcards accepts --scope, resolves through the permission ops, and
        WRITES through the resolved path — a --scope call must never fall back to a
        None settings path for the save.

        The single-file arm: only ``.claude/settings.json`` exists, so the read
        preference falls back to it. The dual-file arm — where the preference is
        actually observable — is ``TestSharedSeamCallSites``; keeping this one
        single-file is what makes the pair discriminate a preference from a
        hard-wired filename.
        """
        claude = tmp_path / '.claude'
        claude.mkdir(parents=True, exist_ok=True)
        settings_file = claude / 'settings.json'
        _write_settings(settings_file, [])
        marketplace_file = tmp_path / 'marketplace.json'
        marketplace_file.write_text(json.dumps({'bundles': {'foo': {'skills': ['s'], 'commands': ['c']}}}))
        monkeypatch.chdir(tmp_path)

        result = pf.cmd_ensure_wildcards(
            parse_ns(
                'plan-marshall',
                'tools-permission-fix',
                'permission_fix.py',
                'ensure-wildcards',
                '--scope',
                'project',
                '--marketplace-json',
                str(marketplace_file),
            )
        )

        assert result['status'] == 'success'
        assert result['applied'] is True
        assert result['settings_path'] == str(settings_file)
        allow = _read_allow(settings_file)
        assert 'Skill(foo:*)' in allow


# =============================================================================
# prefix extraction — single-token branch
# =============================================================================


class TestPrefixExtraction:
    """Test extract_command_prefix / extract_skill_prefix edge behavior."""

    def test_command_prefix_hyphenated(self):
        """A hyphenated command name yields its first segment."""
        assert pf.extract_command_prefix('plan-manage') == 'plan'

    def test_command_prefix_single_token(self):
        """A single-token command name is returned whole."""
        assert pf.extract_command_prefix('verify') == 'verify'

    def test_skill_prefix_single_token(self):
        """A single-token skill name is returned whole."""
        assert pf.extract_skill_prefix('planning') == 'planning'


# =============================================================================
# scan_marketplace_dir — JSON-error and no-source branches
# =============================================================================


class TestScanMarketplaceDirEdges:
    """Test scan_marketplace_dir error and fallback branches."""

    def test_invalid_marketplace_json(self, tmp_path):
        """A malformed marketplace.json surfaces an invalid-JSON error."""
        plugin_dir = tmp_path / '.claude-plugin'
        plugin_dir.mkdir(parents=True)
        (plugin_dir / 'marketplace.json').write_text('{broken')

        result = pf.scan_marketplace_dir(str(tmp_path))

        assert result['status'] == 'error'
        assert 'Invalid JSON' in result['error']

    def test_invalid_plugin_json_yields_empty_lists(self, tmp_path):
        """A bundle with malformed plugin.json contributes empty skills/commands."""
        plugin_dir = tmp_path / '.claude-plugin'
        plugin_dir.mkdir(parents=True)
        (plugin_dir / 'marketplace.json').write_text(json.dumps({'plugins': [{'name': 'b', 'source': './bundles/b'}]}))
        bundle_plugin = tmp_path / 'bundles' / 'b' / '.claude-plugin'
        bundle_plugin.mkdir(parents=True)
        (bundle_plugin / 'plugin.json').write_text('{not valid')

        result = pf.scan_marketplace_dir(str(tmp_path))

        bundle = result['bundles'][0]
        assert bundle['skills'] == []
        assert bundle['commands'] == []

    def test_bundle_without_source_resolves_default_path(self, tmp_path):
        """A plugin entry lacking 'source' resolves under bundles/<name>."""
        plugin_dir = tmp_path / '.claude-plugin'
        plugin_dir.mkdir(parents=True)
        (plugin_dir / 'marketplace.json').write_text(json.dumps({'plugins': [{'name': 'b'}]}))
        bundle_plugin = tmp_path / 'bundles' / 'b' / '.claude-plugin'
        bundle_plugin.mkdir(parents=True)
        (bundle_plugin / 'plugin.json').write_text(json.dumps({'skills': ['./skills/s.md'], 'commands': []}))

        result = pf.scan_marketplace_dir(str(tmp_path))

        bundle = result['bundles'][0]
        assert len(bundle['skills']) == 1


# =============================================================================
# generate-wildcards — empty inventory and input error branches
# =============================================================================


class TestGenerateWildcardsEdges:
    """Test cmd_generate_wildcards empty-inventory and input-error branches."""

    def test_empty_bundles_reports_error_field(self, tmp_path):
        """An inventory with no bundles reports the 'No bundles found' diagnostic."""
        inventory = tmp_path / 'inv.json'
        inventory.write_text(json.dumps({'bundles': []}))

        result = pf.cmd_generate_wildcards(
            parse_ns(
                'plan-marshall',
                'tools-permission-fix',
                'permission_fix.py',
                'generate-wildcards',
                '--input',
                str(inventory),
            )
        )

        assert result['status'] == 'success'
        assert result['error'] == 'No bundles found in inventory'
        assert result['statistics']['bundles_scanned'] == 0

    def test_missing_input_file_errors(self, tmp_path):
        """A non-existent input file surfaces an input-not-found error."""
        result = pf.cmd_generate_wildcards(
            parse_ns(
                'plan-marshall',
                'tools-permission-fix',
                'permission_fix.py',
                'generate-wildcards',
                '--input',
                str(tmp_path / 'nope.json'),
            )
        )

        assert result['status'] == 'error'
        assert 'Input file not found' in result['error']

    def test_invalid_input_json_errors(self, tmp_path):
        """A malformed input file surfaces an invalid-JSON error."""
        inventory = tmp_path / 'inv.json'
        inventory.write_text('{broken json')

        result = pf.cmd_generate_wildcards(
            parse_ns(
                'plan-marshall',
                'tools-permission-fix',
                'permission_fix.py',
                'generate-wildcards',
                '--input',
                str(inventory),
            )
        )

        assert result['status'] == 'error'
        assert 'Invalid JSON' in result['error']


# =============================================================================
# ensure-executor / cleanup-scripts / migrate-executor — dry-run + extra branches
# =============================================================================


class TestExecutorSubcommandsInProcess:
    """Test executor-pattern subcommands against a chdir'd tmp project dir."""

    @pytest.fixture()
    def in_tmp_cwd(self, tmp_path, monkeypatch):
        """Run with the process working directory inside an isolated tmp_path."""
        monkeypatch.chdir(tmp_path)

    def _setup_project(self, tmp_path, allow):
        """Create tmp_path/.claude/settings.json and return its path."""
        claude_dir = tmp_path / '.claude'
        claude_dir.mkdir()
        settings_file = claude_dir / 'settings.json'
        _write_settings(settings_file, allow)
        return settings_file

    def test_ensure_executor_dry_run_would_add(self, tmp_path, in_tmp_cwd):
        """Dry-run reports 'would_add' and leaves the file untouched."""
        settings_file = self._setup_project(tmp_path, ['Bash(git:*)'])

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

        assert result['action'] == 'would_add'
        assert result['success'] is True
        assert pf.EXECUTOR_PERMISSION not in _read_allow(settings_file)

    def test_cleanup_scripts_nothing_to_remove(self, tmp_path, in_tmp_cwd):
        """With no individual script perms, cleanup reports nothing to remove."""
        self._setup_project(tmp_path, ['Bash(git:*)'])

        result = pf.cmd_cleanup_scripts(
            parse_ns(
                'plan-marshall', 'tools-permission-fix', 'permission_fix.py', 'cleanup-scripts', '--target', 'project'
            )
        )

        assert result['action'] == 'nothing_to_remove'
        assert result['success'] is True

    def test_cleanup_scripts_dry_run_would_remove(self, tmp_path, in_tmp_cwd):
        """Dry-run reports the would-remove count without modifying the file."""
        script_perm = 'Bash(python3 /x/marketplace/bundles/b/skills/s/scripts/run.py:*)'
        settings_file = self._setup_project(tmp_path, ['Bash(git:*)', script_perm])

        result = pf.cmd_cleanup_scripts(
            parse_ns(
                'plan-marshall',
                'tools-permission-fix',
                'permission_fix.py',
                'cleanup-scripts',
                '--target',
                'project',
                '--dry-run',
            )
        )

        assert result['action'] == 'would_remove'
        assert result['total_would_remove'] == 1
        assert script_perm in _read_allow(settings_file)

    def test_cleanup_scripts_removes_broad_python(self, tmp_path, in_tmp_cwd):
        """With --remove-broad-python the overly broad python wildcard is removed."""
        settings_file = self._setup_project(tmp_path, ['Bash(git:*)', pf.OVERLY_BROAD_PYTHON])

        result = pf.cmd_cleanup_scripts(
            parse_ns(
                'plan-marshall',
                'tools-permission-fix',
                'permission_fix.py',
                'cleanup-scripts',
                '--target',
                'project',
                '--remove-broad-python',
            )
        )

        assert result['success'] is True
        assert result['broad_python_removed'] is True
        assert pf.OVERLY_BROAD_PYTHON not in _read_allow(settings_file)

    def test_migrate_executor_dry_run(self, tmp_path, in_tmp_cwd):
        """Dry-run reports planned would-add/would-remove without writing."""
        script_perm = 'Bash(python3 /x/marketplace/bundles/b/skills/s/scripts/run.py:*)'
        settings_file = self._setup_project(tmp_path, ['Bash(git:*)', script_perm])

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

        assert result['success'] is True
        assert result['executor']['action'] == 'would_add'
        assert result['cleanup']['individual_would_remove'] == 1
        # Dry-run leaves the file unchanged.
        assert pf.EXECUTOR_PERMISSION not in _read_allow(settings_file)

    def test_migrate_executor_executor_already_present_removes_broad_python(self, tmp_path, in_tmp_cwd):
        """When the executor perm already exists, migration only cleans up extras."""
        settings_file = self._setup_project(tmp_path, ['Bash(git:*)', pf.EXECUTOR_PERMISSION, pf.OVERLY_BROAD_PYTHON])

        result = pf.cmd_migrate_executor(
            parse_ns(
                'plan-marshall',
                'tools-permission-fix',
                'permission_fix.py',
                'migrate-executor',
                '--target',
                'project',
                '--remove-broad-python',
            )
        )

        assert result['success'] is True
        assert result['executor']['action'] == 'already_exists'
        allow = _read_allow(settings_file)
        assert pf.OVERLY_BROAD_PYTHON not in allow
        assert pf.EXECUTOR_PERMISSION in allow


# =============================================================================
# add / remove — in-process write paths against a chdir'd tmp project dir
# =============================================================================


class TestAddRemoveInProcess:
    """Test cmd_add / cmd_remove write and idempotent branches in-process."""

    @pytest.fixture()
    def in_tmp_cwd(self, tmp_path, monkeypatch):
        """Run with the process working directory inside an isolated tmp_path."""
        monkeypatch.chdir(tmp_path)

    def _setup_project(self, tmp_path, allow):
        claude_dir = tmp_path / '.claude'
        claude_dir.mkdir()
        settings_file = claude_dir / 'settings.json'
        _write_settings(settings_file, allow)
        return settings_file

    def test_add_writes_new_permission(self, tmp_path, in_tmp_cwd):
        """Adding a new permission writes it and reports 'added'."""
        settings_file = self._setup_project(tmp_path, ['Bash(git:*)'])

        result = pf.cmd_add(
            parse_ns(
                'plan-marshall',
                'tools-permission-fix',
                'permission_fix.py',
                'add',
                '--permission',
                'Bash(npm:*)',
                '--target',
                'project',
            )
        )

        assert result['action'] == 'added'
        assert result['success'] is True
        assert 'Bash(npm:*)' in _read_allow(settings_file)

    def test_add_existing_is_noop(self, tmp_path, in_tmp_cwd):
        """Adding an existing permission reports 'already_exists'."""
        self._setup_project(tmp_path, ['Bash(git:*)'])

        result = pf.cmd_add(
            parse_ns(
                'plan-marshall',
                'tools-permission-fix',
                'permission_fix.py',
                'add',
                '--permission',
                'Bash(git:*)',
                '--target',
                'project',
            )
        )

        assert result['action'] == 'already_exists'

    def test_remove_deletes_permission(self, tmp_path, in_tmp_cwd):
        """Removing an existing permission deletes it and reports 'removed'."""
        settings_file = self._setup_project(tmp_path, ['Bash(git:*)', 'Bash(npm:*)'])

        result = pf.cmd_remove(
            parse_ns(
                'plan-marshall',
                'tools-permission-fix',
                'permission_fix.py',
                'remove',
                '--permission',
                'Bash(npm:*)',
                '--target',
                'project',
            )
        )

        assert result['action'] == 'removed'
        assert 'Bash(npm:*)' not in _read_allow(settings_file)

    def test_remove_absent_is_noop(self, tmp_path, in_tmp_cwd):
        """Removing a missing permission reports 'not_found'."""
        self._setup_project(tmp_path, ['Bash(git:*)'])

        result = pf.cmd_remove(
            parse_ns(
                'plan-marshall',
                'tools-permission-fix',
                'permission_fix.py',
                'remove',
                '--permission',
                'Bash(absent:*)',
                '--target',
                'project',
            )
        )

        assert result['action'] == 'not_found'


# =============================================================================
# remove-redundant — scope resolution and error branches
# =============================================================================


class TestRemoveRedundantErrors:
    """Test cmd_remove_redundant error branches that the happy-path suite omits."""

    def test_global_load_error(self, tmp_path):
        """A missing global settings file surfaces a structured error."""
        local_file = tmp_path / 'local.json'
        _write_settings(local_file, ['Bash(git:*)'])

        result = pf.cmd_remove_redundant(
            parse_ns(
                'plan-marshall',
                'tools-permission-fix',
                'permission_fix.py',
                'remove-redundant',
                '--global-settings',
                str(tmp_path / 'missing-global.json'),
                '--local-settings',
                str(local_file),
            )
        )

        assert result['status'] == 'error'
        assert 'not found' in result['error']

    def test_local_load_error(self, tmp_path):
        """A missing local settings file surfaces a structured error."""
        global_file = tmp_path / 'global.json'
        _write_settings(global_file, ['Bash(git:*)'])

        result = pf.cmd_remove_redundant(
            parse_ns(
                'plan-marshall',
                'tools-permission-fix',
                'permission_fix.py',
                'remove-redundant',
                '--global-settings',
                str(global_file),
                '--local-settings',
                str(tmp_path / 'missing-local.json'),
            )
        )

        assert result['status'] == 'error'


# =============================================================================
# apply-project-step-permissions — error branches
# =============================================================================


class TestApplyProjectStepPermissionsErrors:
    """Test cmd_apply_project_step_permissions error branches."""

    def test_marshal_load_error(self, tmp_path):
        """A missing marshal.json surfaces a structured error."""
        settings_file = tmp_path / 'settings.json'
        _write_settings(settings_file, [])

        result = pf.cmd_apply_project_step_permissions(
            parse_ns(
                'plan-marshall',
                'tools-permission-fix',
                'permission_fix.py',
                'apply-project-step-permissions',
                '--marshal',
                str(tmp_path / 'missing.json'),
                '--settings',
                str(settings_file),
                '--dry-run',
            )
        )

        assert result['status'] == 'error'

    def test_settings_load_error(self, tmp_path):
        """A missing settings file surfaces a structured error after marshal loads."""
        marshal_file = tmp_path / 'marshal.json'
        marshal_file.write_text(json.dumps({'plan': {'phase-6-finalize': {'steps': []}}}))

        result = pf.cmd_apply_project_step_permissions(
            parse_ns(
                'plan-marshall',
                'tools-permission-fix',
                'permission_fix.py',
                'apply-project-step-permissions',
                '--marshal',
                str(marshal_file),
                '--settings',
                str(tmp_path / 'missing.json'),
                '--dry-run',
            )
        )

        assert result['status'] == 'error'


# =============================================================================
# Non-Claude target: permission-DSL-emitting subcommands decline (D1)
# =============================================================================
# The Claude permission-DSL residue (EXECUTOR_PERMISSION, OVERLY_BROAD_PYTHON,
# the Skill(...)/SlashCommand(...) wildcard generators, the timestamp patterns,
# path normalization, individual-script detection) renders Claude grammar inside
# a general script. On a non-Claude target each emitting subcommand must return
# an honest no-op rather than render. Red-first: each assertion fails against
# current HEAD.


class TestPermissionDslDeclinesOnNonClaude:
    """The permission-DSL-emitting direct subcommands decline on a non-Claude target."""

    @pytest.fixture()
    def in_tmp_cwd(self, tmp_path, monkeypatch):
        """Run with the process working directory inside an isolated tmp_path."""
        monkeypatch.chdir(tmp_path)

    @staticmethod
    def _force_opencode(monkeypatch):
        """Point the runtime-resolution seam at the OpenCode runtime."""
        import permission_common
        from opencode_runtime import OpenCodeRuntime

        monkeypatch.setattr(permission_common, '_runtime_for_target', lambda: OpenCodeRuntime())

    @staticmethod
    def _assert_declines(result):
        assert result.get('status') == 'no-op'
        assert 'reason' in result
        # No Claude permission-DSL output may be produced.
        serialized = str(result)
        assert 'Bash(' not in serialized
        assert 'Skill(' not in serialized
        assert 'SlashCommand(' not in serialized

    def test_apply_fixes_declines_on_opencode(self, monkeypatch, tmp_path):
        """apply-fixes on a non-Claude target returns a no-op, not a normalized render."""
        settings_file = tmp_path / 'settings.json'
        _write_settings(
            settings_file, ['Read(target/build-2025-11-20-174411.log)', 'Read(target/build-2025-11-20-174411.log)']
        )

        self._force_opencode(monkeypatch)

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

        self._assert_declines(result)

    def test_consolidate_declines_on_opencode(self, monkeypatch, tmp_path):
        """consolidate on a non-Claude target returns a no-op, not timestamp wildcards."""
        settings_file = tmp_path / 'settings.json'
        _write_settings(
            settings_file, ['Read(target/build-2025-11-20-174411.log)', 'Read(target/build-2025-11-20-174412.log)']
        )

        self._force_opencode(monkeypatch)

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

        self._assert_declines(result)

    def test_ensure_wildcards_declines_on_opencode(self, monkeypatch, tmp_path):
        """ensure-wildcards on a non-Claude target returns a no-op, not Skill(...) rules."""
        settings_file = tmp_path / 'settings.json'
        _write_settings(settings_file, [])
        marketplace_file = tmp_path / 'marketplace.json'
        marketplace_file.write_text(json.dumps({'bundles': {'plan-marshall': {'skills': {'manage-files': {}}}}}))

        self._force_opencode(monkeypatch)

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

        self._assert_declines(result)

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

        self._force_opencode(monkeypatch)

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

        self._assert_declines(result)

    def test_ensure_executor_declines_on_opencode(self, monkeypatch, tmp_path, in_tmp_cwd):
        """ensure-executor on a non-Claude target returns a no-op, not the executor permission."""
        self._force_opencode(monkeypatch)

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

        self._assert_declines(result)

    def test_cleanup_scripts_declines_on_opencode(self, monkeypatch, tmp_path, in_tmp_cwd):
        """cleanup-scripts on a non-Claude target returns a no-op, not removal lists."""
        self._force_opencode(monkeypatch)

        result = pf.cmd_cleanup_scripts(
            parse_ns(
                'plan-marshall', 'tools-permission-fix', 'permission_fix.py', 'cleanup-scripts', '--target', 'project'
            )
        )

        self._assert_declines(result)

    def test_migrate_executor_declines_on_opencode(self, monkeypatch, tmp_path, in_tmp_cwd):
        """migrate-executor on a non-Claude target returns a no-op, not executor migration."""
        self._force_opencode(monkeypatch)

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

        self._assert_declines(result)

    def test_apply_project_step_permissions_declines_on_opencode(self, monkeypatch, tmp_path):
        """apply-project-step-permissions on a non-Claude target returns a no-op, not Skill(...) rules."""
        marshal_file = tmp_path / 'marshal.json'
        marshal_file.write_text(
            json.dumps({'plan': {'phase-6-finalize': {'steps': ['project:finalize-step-plugin-doctor']}}})
        )
        settings_file = tmp_path / 'settings.json'
        _write_settings(settings_file, [])

        self._force_opencode(monkeypatch)

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

        self._assert_declines(result)

    def test_remove_redundant_propagates_skipped_on_opencode(self, monkeypatch, tmp_path):
        """remove-redundant on a non-Claude target propagates the skipped third state, not success."""
        global_file = tmp_path / 'global.json'
        local_file = tmp_path / 'local.json'
        _write_settings(global_file, ['Read(src/**)'])
        _write_settings(local_file, ['Read(src/**)'])

        self._force_opencode(monkeypatch)

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
        self._force_opencode(monkeypatch)

        result = pf.cmd_remove_redundant(
            parse_ns(
                'plan-marshall', 'tools-permission-fix', 'permission_fix.py', 'remove-redundant', '--scope', 'both'
            )
        )

        assert result.get('status') == 'skipped'
        assert 'Could not resolve' not in str(result)
