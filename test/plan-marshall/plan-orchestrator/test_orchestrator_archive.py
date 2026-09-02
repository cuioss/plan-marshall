#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the plan-orchestrator ``archive`` verb and the archived-epic
read-fallback across the store-resolver seam.

Covers the fourth deterministic ``orchestrator.py`` operation plus the
read-fallback flags threaded through ``file_ops.get_store_dir`` /
``manage-status``'s orchestrator handlers, all under ``PLAN_BASE_DIR``
isolation (via ``plan_context``):

- ``cmd_archive``: relocate a ``phase=closed`` epic (active → archived);
  refuse a non-closed epic (``not_closed``, no move); idempotent re-run of an
  already-archived slug (``already_archived``); refuse when no epic exists
  (``not_found``); refuse to clobber (``archive_conflict``); reject an invalid
  slug.
- Read-fallback: after archiving, ``orchestrator.py resume-summary`` and
  ``manage-status read --store orchestrator`` still resolve the epic from
  ``archived-orchestrators/``.
- Write-refusal: ``manage-status update-field --store orchestrator`` against an
  archived-only epic refuses with ``file_not_found`` (no resurrection at the
  active path).
- CLI boundary: ``archive`` driven through the ``orchestrator.py`` entry point
  with constructed argv at the subprocess boundary (``run_script``).
"""

import argparse
import copy
import json
from pathlib import Path
from typing import Any

from plan_logging import log_entry

from conftest import get_script_path, load_script_module, parse_ns, run_script

#: The orchestrator script's address, as module-level string constants so every
#: ``parse_ns`` call below stays statically resolvable.
_ORCH_BUNDLE = 'plan-marshall'
_ORCH_SKILL = 'plan-orchestrator'
_ORCH_SCRIPT = 'orchestrator.py'

ORCH_SCRIPT_PATH = get_script_path(_ORCH_BUNDLE, _ORCH_SKILL, _ORCH_SCRIPT)
STATUS_SCRIPT_PATH = get_script_path('plan-marshall', 'manage-status', 'manage-status.py')

_orch = load_script_module(
    _ORCH_BUNDLE, _ORCH_SKILL, _ORCH_SCRIPT, 'orchestrator_script'
)

cmd_archive = _orch.cmd_archive
cmd_resume_summary = _orch.cmd_resume_summary
cmd_scaffold = _orch.cmd_scaffold

FIXED_TIMESTAMP = '2020-01-01T00:00:00Z'

#: The slug every hoisted base below is parsed with. Each caller overrides it
#: through :func:`_variant`, so the value is a placeholder rather than a fixture.
_BASE_SLUG = 'base-epic'


# =============================================================================
# Parser-derived argument namespaces
# =============================================================================
#
# One hoisted namespace per verb, built by the orchestrator's OWN parser so each
# carries every default the production CLI applies. ``parse_ns`` re-executes the
# script module on every call, so these live at module scope and each caller
# derives its own slug through :func:`_variant` instead of parsing again.
# ``register=False`` throughout: only the namespace is wanted, and publishing
# ``orchestrator`` in ``sys.modules`` would displace the explicitly-named
# registration above.


def _variant(base: argparse.Namespace, **overrides: Any) -> argparse.Namespace:
    """Derive a namespace from a hoisted parser-derived base.

    The base supplies every parser default; ``overrides`` names only the fields
    this call differs in. A shallow copy is enough because a namespace's values
    are the parser's own scalars, and the base must stay unmutated for the other
    callers sharing it.
    """
    derived = copy.copy(base)
    for field, value in overrides.items():
        setattr(derived, field, value)
    return derived


_ARCHIVE_ARGS = parse_ns(
    _ORCH_BUNDLE, _ORCH_SKILL, _ORCH_SCRIPT,
    'archive', '--slug', _BASE_SLUG,
    register=False,
)

_SCAFFOLD_ARGS = parse_ns(
    _ORCH_BUNDLE, _ORCH_SKILL, _ORCH_SCRIPT,
    'scaffold', '--slug', _BASE_SLUG,
    register=False,
)

_RESUME_SUMMARY_ARGS = parse_ns(
    _ORCH_BUNDLE, _ORCH_SKILL, _ORCH_SCRIPT,
    'resume-summary', '--slug', _BASE_SLUG,
    register=False,
)


def _active_epic_dir(plan_context, slug: str) -> Path:
    return Path(plan_context.fixture_dir) / 'orchestrator' / slug


def _archived_epic_dir(plan_context, slug: str) -> Path:
    return Path(plan_context.fixture_dir) / 'archived-orchestrators' / slug


def _write_epic_status(epic_dir: Path, phase: str = 'closed') -> Path:
    """Write a minimal kind=orchestrator status.json into ``epic_dir``."""
    doc = {
        'kind': 'orchestrator',
        'title': 'Fixture Epic',
        'phase': phase,
        'workstreams': ['WS-01'],
        'plans': [],
        'resume_anchor': 'audit record',
        'metadata': {},
        'created': FIXED_TIMESTAMP,
        'updated': FIXED_TIMESTAMP,
    }
    epic_dir.mkdir(parents=True, exist_ok=True)
    path = epic_dir / 'status.json'
    path.write_text(json.dumps(doc, indent=2), encoding='utf-8')
    return path


def _seed_active_epic(plan_context, slug: str, phase: str = 'closed') -> Path:
    """Scaffold the active epic tree and write its status.json at ``phase``."""
    cmd_scaffold(_variant(_SCAFFOLD_ARGS, slug=slug))
    return _write_epic_status(_active_epic_dir(plan_context, slug), phase=phase)


# =============================================================================
# cmd_archive — relocation
# =============================================================================


class TestArchiveRelocation:
    def test_should_move_closed_epic_to_archived(self, plan_context):
        _seed_active_epic(plan_context, 'closed-epic', phase='closed')
        active = _active_epic_dir(plan_context, 'closed-epic')
        archived = _archived_epic_dir(plan_context, 'closed-epic')

        result = cmd_archive(_variant(_ARCHIVE_ARGS, slug='closed-epic'))

        assert result['status'] == 'success'
        assert result['operation'] == 'archive'
        assert result['already_archived'] is False
        assert result['archived_to'] == str(archived)
        assert not active.exists()
        assert (archived / 'status.json').is_file()

    def test_should_preserve_status_json_across_the_move(self, plan_context):
        _seed_active_epic(plan_context, 'preserve-epic', phase='closed')

        cmd_archive(_variant(_ARCHIVE_ARGS, slug='preserve-epic'))

        moved = _archived_epic_dir(plan_context, 'preserve-epic') / 'status.json'
        doc = json.loads(moved.read_text(encoding='utf-8'))
        assert doc['phase'] == 'closed'
        assert doc['kind'] == 'orchestrator'


# =============================================================================
# cmd_archive — refusals
# =============================================================================


class TestArchiveRefusals:
    def test_should_refuse_non_closed_epic_with_no_move(self, plan_context):
        _seed_active_epic(plan_context, 'busy-epic', phase='orchestrating')
        active = _active_epic_dir(plan_context, 'busy-epic')

        result = cmd_archive(_variant(_ARCHIVE_ARGS, slug='busy-epic'))

        assert result['status'] == 'error'
        assert result['error'] == 'not_closed'
        assert result['phase'] == 'orchestrating'
        assert 'run close first' in result['message']
        # No move performed: active tree intact, archived tree absent.
        assert (active / 'status.json').is_file()
        assert not _archived_epic_dir(plan_context, 'busy-epic').exists()

    def test_should_error_when_no_epic_exists(self, plan_context):
        result = cmd_archive(_variant(_ARCHIVE_ARGS, slug='ghost-epic'))

        assert result['status'] == 'error'
        assert result['error'] == 'not_found'

    def test_should_refuse_to_clobber_existing_archive(self, plan_context):
        _seed_active_epic(plan_context, 'dup-epic', phase='closed')
        # An archived tree already exists for the same slug.
        _write_epic_status(_archived_epic_dir(plan_context, 'dup-epic'), phase='closed')
        active = _active_epic_dir(plan_context, 'dup-epic')

        result = cmd_archive(_variant(_ARCHIVE_ARGS, slug='dup-epic'))

        assert result['status'] == 'error'
        assert result['error'] == 'archive_conflict'
        # Neither tree is destroyed.
        assert (active / 'status.json').is_file()
        assert (_archived_epic_dir(plan_context, 'dup-epic') / 'status.json').is_file()

    def test_should_reject_invalid_slug(self, plan_context):
        result = cmd_archive(_variant(_ARCHIVE_ARGS, slug='../evil'))

        assert result['status'] == 'error'
        assert result['error'] == 'invalid_slug'


# =============================================================================
# cmd_archive — idempotency
# =============================================================================


class TestArchiveIdempotency:
    def test_should_report_already_archived_when_only_archived_exists(self, plan_context):
        # No active tree; only the archived tree is present.
        _write_epic_status(_archived_epic_dir(plan_context, 'done-epic'), phase='closed')
        archived = _archived_epic_dir(plan_context, 'done-epic')

        result = cmd_archive(_variant(_ARCHIVE_ARGS, slug='done-epic'))

        assert result['status'] == 'success'
        assert result['already_archived'] is True
        assert result['archived_to'] == str(archived)
        assert (archived / 'status.json').is_file()

    def test_should_be_idempotent_on_repeated_archive(self, plan_context):
        _seed_active_epic(plan_context, 'twice-epic', phase='closed')

        first = cmd_archive(_variant(_ARCHIVE_ARGS, slug='twice-epic'))
        second = cmd_archive(_variant(_ARCHIVE_ARGS, slug='twice-epic'))

        assert first['status'] == 'success'
        assert first['already_archived'] is False
        assert second['status'] == 'success'
        assert second['already_archived'] is True
        assert second['archived_to'] == first['archived_to']

    def test_repeated_log_then_archive_stays_idempotent_and_never_resurrects_active(self, plan_context):
        # Concrete regression for the CodeRabbit finding: mirror archive.md's
        # Step 3 (log a decision, --store orchestrator) THEN Step 4 (cmd_archive)
        # twice in a row. The second pass's log write must resolve the archived
        # tree via the allow_archived read-fallback rather than scaffolding an
        # empty active-path directory — otherwise the resurrected active tree
        # makes cmd_archive's source.exists() probe misread the epic as
        # not-yet-archived and fall into the not_closed refusal instead of the
        # idempotent already_archived path.
        slug = 'log-then-archive-epic'
        _seed_active_epic(plan_context, slug, phase='closed')
        active = _active_epic_dir(plan_context, slug)

        # First request: Step 3 (log) then Step 4 (archive).
        log_entry('decision', slug, 'INFO', 'archive decision (first)', store='orchestrator')
        first = cmd_archive(_variant(_ARCHIVE_ARGS, slug=slug))

        # Repeated request: Step 3 (log) then Step 4 (archive) again.
        log_entry('decision', slug, 'INFO', 'archive decision (repeat)', store='orchestrator')
        second = cmd_archive(_variant(_ARCHIVE_ARGS, slug=slug))

        assert first['status'] == 'success'
        assert first['already_archived'] is False
        assert second['status'] == 'success'
        assert second['already_archived'] is True
        # The repeat's log write did NOT resurrect the active tree.
        assert not active.exists()


# =============================================================================
# Read-fallback — archived epics stay resolvable by the read verbs
# =============================================================================


class TestReadFallback:
    def test_resume_summary_resolves_archived_epic(self, plan_context):
        _seed_active_epic(plan_context, 'summary-epic', phase='closed')
        cmd_archive(_variant(_ARCHIVE_ARGS, slug='summary-epic'))

        result = cmd_resume_summary(_variant(_RESUME_SUMMARY_ARGS, slug='summary-epic'))

        assert result['status'] == 'success'
        assert result['operation'] == 'resume-summary'
        assert '**Phase**: closed' in result['summary']

    def test_manage_status_read_resolves_archived_epic_via_cli(self, plan_context):
        env = {'PLAN_BASE_DIR': str(plan_context.fixture_dir)}
        _seed_active_epic(plan_context, 'read-epic', phase='closed')
        run_script(ORCH_SCRIPT_PATH, 'archive', '--slug', 'read-epic', env_overrides=env)

        read = run_script(
            STATUS_SCRIPT_PATH,
            'read',
            '--store',
            'orchestrator',
            '--plan-id',
            'read-epic',
            env_overrides=env,
        )

        assert read.returncode == 0
        assert 'status: success' in read.stdout
        assert 'closed' in read.stdout


# =============================================================================
# Write-refusal — writes never resurrect an archived-only epic
# =============================================================================


class TestWriteRefusal:
    def test_manage_status_update_field_refuses_archived_only_epic(self, plan_context):
        env = {'PLAN_BASE_DIR': str(plan_context.fixture_dir)}
        _seed_active_epic(plan_context, 'frozen-epic', phase='closed')
        run_script(ORCH_SCRIPT_PATH, 'archive', '--slug', 'frozen-epic', env_overrides=env)

        update = run_script(
            STATUS_SCRIPT_PATH,
            'update-field',
            '--plan-id',
            'frozen-epic',
            '--field',
            'resume_anchor',
            '--value',
            'reopened',
            env_overrides=env,
        )

        assert 'file_not_found' in update.stdout
        # No active tree was recreated by the refused write.
        assert not _active_epic_dir(plan_context, 'frozen-epic').exists()


# =============================================================================
# CLI boundary (constructed argv at the subprocess boundary)
# =============================================================================


class TestCli:
    def test_should_archive_through_cli(self, plan_context):
        env = {'PLAN_BASE_DIR': str(plan_context.fixture_dir)}
        _seed_active_epic(plan_context, 'cli-epic', phase='closed')

        result = run_script(ORCH_SCRIPT_PATH, 'archive', '--slug', 'cli-epic', env_overrides=env)

        assert result.returncode == 0
        assert 'status: success' in result.stdout
        assert 'already_archived: false' in result.stdout
        assert (_archived_epic_dir(plan_context, 'cli-epic') / 'status.json').is_file()
        assert not _active_epic_dir(plan_context, 'cli-epic').exists()

    def test_should_refuse_non_closed_epic_through_cli(self, plan_context):
        env = {'PLAN_BASE_DIR': str(plan_context.fixture_dir)}
        _seed_active_epic(plan_context, 'cli-busy-epic', phase='orchestrating')

        result = run_script(
            ORCH_SCRIPT_PATH, 'archive', '--slug', 'cli-busy-epic', env_overrides=env
        )

        assert result.returncode == 0
        assert 'error: not_closed' in result.stdout
        assert (_active_epic_dir(plan_context, 'cli-busy-epic') / 'status.json').is_file()
