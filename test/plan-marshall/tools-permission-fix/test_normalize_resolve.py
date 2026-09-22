#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Normalize + resolve seam (carve 2 split)."""

import ast
import json
from argparse import Namespace
from pathlib import Path

import pytest
from _permission_fix_fixtures import (
    RETIRED_DEFAULT,
    allow_list,
    assert_declines,
    build_project,
    dual_file_project,
    force_opencode,
    force_unsupported_runtime,
    in_tmp_cwd,
    read_allow,
    roster_handlers,
    seam_callers,
    seed_retired,
    setup_project,
    write_marshal,
    write_settings,
    write_settings_str,
)

from conftest import load_script_module, parse_ns

pf = load_script_module('plan-marshall', 'tools-permission-fix', 'permission_fix.py', 'pf_behavior')


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


class TestApplyFixesApplied:
    """Test cmd_apply_fixes write path and error path."""

    def test_applies_path_fix_and_writes_file(self, tmp_path):
        """Non-dry-run normalizes a trailing-slash path, writes, and reports applied."""
        # Arrange
        settings_file = tmp_path / 'settings.json'
        write_settings(settings_file, ['Read(src/)', 'Bash(git:*)'])

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
        allow = read_allow(settings_file)
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
        write_settings(
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

    def test_both_arms_resolve_the_overriding_local_file(self, tmp_path, monkeypatch):
        """``--scope project`` and the no-flag fall-through agree, and both pick the local file.

        Asserting them together is the point: they are separate branches in the
        helper, and letting them disagree is how one subcommand comes to edit a
        different file from the next.
        """
        claude = build_project(tmp_path, monkeypatch, local=True)

        assert pf.resolve_settings_arg(Namespace(settings=None, scope='project')) == str(claude / 'settings.local.json')
        assert pf.resolve_settings_arg(Namespace(settings=None, scope=None)) == str(claude / 'settings.local.json')

    def test_without_a_local_file_both_arms_fall_back_to_the_shared_one(self, tmp_path, monkeypatch):
        """The control: the preference is a preference, not a hard-wired filename."""
        claude = build_project(tmp_path, monkeypatch, local=False)

        assert pf.resolve_settings_arg(Namespace(settings=None, scope='project')) == str(claude / 'settings.json')
        assert pf.resolve_settings_arg(Namespace(settings=None, scope=None)) == str(claude / 'settings.json')

    def test_an_explicit_settings_path_is_honoured_untouched(self, tmp_path, monkeypatch):
        """``--settings`` outranks both arms — the operator named a file."""
        build_project(tmp_path, monkeypatch, local=True)
        explicit = tmp_path / 'elsewhere.json'

        assert pf.resolve_settings_arg(Namespace(settings=explicit, scope=None)) == str(explicit)

    def test_scope_global_still_resolves_outside_the_project(self, tmp_path, monkeypatch):
        """Boundary: only the project arm moved; ``--scope global`` keeps ``get_settings_path``."""
        claude = build_project(tmp_path, monkeypatch, local=True)

        resolved = pf.resolve_settings_arg(Namespace(settings=None, scope='global'))

        assert not resolved.startswith(str(claude))


class TestSharedSeamCallSites:
    """Each subcommand routed through ``resolve_settings_arg`` resolves the same file.

    The helper is shared, so one call site could be re-pointed at a different
    resolver without any helper-level test noticing. One row per call site is what
    makes that divergence visible.
    """

    def test_apply_fixes_resolves_the_local_file(self, tmp_path, monkeypatch):
        """apply-fixes — call site 1 of 4."""
        local = dual_file_project(tmp_path, monkeypatch)

        result = pf.cmd_apply_fixes(
            parse_ns('plan-marshall', 'tools-permission-fix', 'permission_fix.py', 'apply-fixes', '--scope', 'project')
        )

        assert result['settings_path'] == str(local)

    def test_consolidate_resolves_the_local_file(self, tmp_path, monkeypatch):
        """consolidate — call site 2 of 4."""
        local = dual_file_project(tmp_path, monkeypatch)

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
        local = dual_file_project(tmp_path, monkeypatch)
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
        assert 'Skill(foo:*)' in read_allow(local)

    def test_apply_project_step_permissions_resolves_the_local_file(self, tmp_path, monkeypatch):
        """apply-project-step-permissions — call site 4 of 4."""
        local = dual_file_project(tmp_path, monkeypatch)
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
        local = dual_file_project(tmp_path, monkeypatch)
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

        assert 'Bash(npm:*)' in read_allow(shared)
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

    def test_every_seam_caller_has_a_roster_row(self):
        """Every derived ``resolve_settings_arg`` caller is driven by the roster class."""
        module_path = Path(pf.__file__)
        callers = seam_callers(module_path.read_text(encoding='utf-8'), self.SEAM)
        covered = roster_handlers(Path(__file__).read_text(encoding='utf-8'), self.ROSTER_CLASS)

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

        callers = seam_callers(module_source, self.SEAM)
        covered = roster_handlers(roster_source, 'Roster')

        assert callers == {'cmd_on_the_roster', 'cmd_added_without_a_row'}
        assert self.SEAM not in callers
        assert covered == {'cmd_on_the_roster'}
        assert callers - covered == {'cmd_added_without_a_row'}
