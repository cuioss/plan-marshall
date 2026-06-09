#!/usr/bin/env python3
"""
Tests for the determine_mode.py script.

Tier 2 (direct import) tests with 2 subprocess tests for CLI plumbing.

Tests both subcommands:
- mode: Determine wizard vs menu mode based on existing files
- check-docs: Check if project docs need required documentation content
"""

from argparse import Namespace

# Import shared infrastructure (conftest.py sets up PYTHONPATH)
from conftest import MARKETPLACE_ROOT, run_script

# Script path to determine_mode.py
SCRIPT_PATH = MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'marshall-steward' / 'scripts' / 'determine_mode.py'

# Tier 2 direct imports — conftest sets up PYTHONPATH for cross-skill imports
from _config_defaults import DEFAULT_PROJECT  # type: ignore[import-not-found]  # noqa: E402
from determine_mode import (  # type: ignore[import-not-found]  # noqa: E402
    check_docs,
    cmd_check_docs,
    cmd_check_working_prefixes,
    cmd_fix_docs,
    cmd_mode,
    detect_working_prefixes_drift,
    determine_mode,
    fix_docs,
)


class TestModeSubcommand:
    """Test the 'mode' subcommand via direct import."""

    def test_wizard_mode_when_executor_missing(self, tmp_path):
        """Should return wizard mode when executor is missing."""
        plan_dir = tmp_path / '.plan'
        plan_dir.mkdir(parents=True)
        (plan_dir / 'marshal.json').write_text('{}')

        result = cmd_mode(Namespace(plan_dir=str(plan_dir)))
        assert result['status'] == 'success'
        assert result['mode'] == 'wizard'
        assert result['reason'] == 'executor_missing'

    def test_wizard_mode_when_marshal_missing(self, tmp_path):
        """Should return wizard mode when marshal.json is missing."""
        plan_dir = tmp_path / '.plan'
        plan_dir.mkdir(parents=True)
        (plan_dir / 'execute-script.py').write_text('# executor script')

        result = cmd_mode(Namespace(plan_dir=str(plan_dir)))
        assert result['status'] == 'success'
        assert result['mode'] == 'wizard'
        assert result['reason'] == 'marshal_missing'

    def test_wizard_mode_when_both_missing(self, tmp_path):
        """Should return wizard mode when both are missing."""
        plan_dir = tmp_path / '.plan'
        plan_dir.mkdir(parents=True)

        result = cmd_mode(Namespace(plan_dir=str(plan_dir)))
        assert result['status'] == 'success'
        assert result['mode'] == 'wizard'
        assert result['reason'] == 'executor_missing'

    def test_menu_mode_when_both_exist(self, tmp_path):
        """Should return menu mode when both exist."""
        plan_dir = tmp_path / '.plan'
        plan_dir.mkdir(parents=True)
        (plan_dir / 'execute-script.py').write_text('# executor script')
        (plan_dir / 'marshal.json').write_text('{}')

        result = cmd_mode(Namespace(plan_dir=str(plan_dir)))
        assert result['status'] == 'success'
        assert result['mode'] == 'menu'
        assert result['reason'] == 'both_exist'

    def test_nonexistent_plan_dir(self, tmp_path):
        """Should return wizard mode for non-existent plan directory."""
        nonexistent_dir = tmp_path / 'nonexistent'

        result = cmd_mode(Namespace(plan_dir=str(nonexistent_dir)))
        assert result['status'] == 'success'
        assert result['mode'] == 'wizard'
        assert result['reason'] == 'executor_missing'

    def test_determine_mode_function_directly(self, tmp_path):
        """Test the raw determine_mode function."""
        plan_dir = tmp_path / '.plan'
        plan_dir.mkdir(parents=True)
        mode, reason = determine_mode(plan_dir)
        assert mode == 'wizard'
        assert reason == 'executor_missing'


class TestCheckDocsSubcommand:
    """Test the 'check-docs' subcommand via direct import."""

    def test_ok_when_no_docs_exist(self, tmp_path):
        """Should return ok when no documentation files exist."""
        result = cmd_check_docs(Namespace(project_root=str(tmp_path)))
        assert result['status'] == 'success'
        assert result['check_status'] == 'ok'
        assert result['missing_count'] == 0

    def test_ok_when_docs_have_all_patterns(self, tmp_path):
        """Should return ok when docs have all required content."""
        claude_md = tmp_path / 'CLAUDE.md'
        claude_md.write_text(
            '# Project\n\nUse `.plan/temp/` for temporary files.\n\n'
            'For file operations use Glob, Read, Grep tools.\n'
        )

        result = cmd_check_docs(Namespace(project_root=str(tmp_path)))
        assert result['status'] == 'success'
        assert result['check_status'] == 'ok'
        assert result['missing_count'] == 0

    def test_needs_update_when_claude_md_missing_plan_temp(self, tmp_path):
        """Should detect missing plan_temp pattern in CLAUDE.md."""
        claude_md = tmp_path / 'CLAUDE.md'
        claude_md.write_text('# Project\n\nFor file operations use Glob, Read, Grep tools.\n')

        result = cmd_check_docs(Namespace(project_root=str(tmp_path)))
        assert result['status'] == 'success'
        assert result['check_status'] == 'needs_update'
        assert 'CLAUDE.md' in result.get('plan_temp', '')

    def test_needs_update_when_claude_md_missing_file_ops(self, tmp_path):
        """Should detect missing file_ops pattern in CLAUDE.md."""
        claude_md = tmp_path / 'CLAUDE.md'
        claude_md.write_text('# Project\n\nUse .plan/temp for files.\n')

        result = cmd_check_docs(Namespace(project_root=str(tmp_path)))
        assert result['status'] == 'success'
        assert result['check_status'] == 'needs_update'
        assert 'CLAUDE.md' in result.get('file_ops', '')

    def test_needs_update_when_agents_md_missing_plan_temp(self, tmp_path):
        """Should detect missing plan_temp in agents.md."""
        agents_md = tmp_path / 'agents.md'
        agents_md.write_text('# Agents\n\nSome other content.\n')

        result = cmd_check_docs(Namespace(project_root=str(tmp_path)))
        assert result['status'] == 'success'
        assert result['check_status'] == 'needs_update'
        assert 'agents.md' in result.get('plan_temp', '')

    def test_needs_update_when_both_missing_all(self, tmp_path):
        """Should list all missing checks across both files."""
        (tmp_path / 'CLAUDE.md').write_text('# Project\n')
        (tmp_path / 'agents.md').write_text('# Agents\n')

        result = cmd_check_docs(Namespace(project_root=str(tmp_path)))
        assert result['status'] == 'success'
        assert result['check_status'] == 'needs_update'
        # plan_temp missing from both files
        assert 'CLAUDE.md' in result.get('plan_temp', '')
        assert 'agents.md' in result.get('plan_temp', '')
        # file_ops missing from CLAUDE.md
        assert 'CLAUDE.md' in result.get('file_ops', '')

    def test_file_ops_not_checked_for_agents_md(self, tmp_path):
        """file_ops should only be checked for CLAUDE.md, not agents.md."""
        (tmp_path / 'agents.md').write_text('Use .plan/temp for files.\n')

        result = cmd_check_docs(Namespace(project_root=str(tmp_path)))
        assert result['status'] == 'success'
        assert result['check_status'] == 'ok'

    def test_mixed_files_one_ok_one_missing(self, tmp_path):
        """Should only list files that need updating."""
        (tmp_path / 'CLAUDE.md').write_text(
            'Use .plan/temp for temp files\n'
            'For file operations use Glob, Read, Grep tools\n'
        )
        (tmp_path / 'agents.md').write_text('# Agents\n')

        result = cmd_check_docs(Namespace(project_root=str(tmp_path)))
        assert result['status'] == 'success'
        assert result['check_status'] == 'needs_update'
        assert result['missing_count'] == 1
        assert 'agents.md' in result.get('plan_temp', '')

    def test_missing_count_reflects_total_entries(self, tmp_path):
        """missing_count should reflect total number of missing check entries."""
        # CLAUDE.md missing both checks (plan_temp, file_ops), agents.md missing plan_temp = 3 entries
        (tmp_path / 'CLAUDE.md').write_text('# Project\n')
        (tmp_path / 'agents.md').write_text('# Agents\n')

        result = cmd_check_docs(Namespace(project_root=str(tmp_path)))
        assert result['status'] == 'success'
        assert result['missing_count'] == 3

    def test_check_docs_function_directly(self, tmp_path):
        """Test the raw check_docs function."""
        status, missing = check_docs(tmp_path)
        assert status == 'ok'
        assert missing == []


class TestFixDocsSubcommand:
    """Test the 'fix-docs' subcommand via direct import."""

    def test_ok_when_no_docs_exist(self, tmp_path):
        """Should return ok when no documentation files exist."""
        result = cmd_fix_docs(Namespace(project_root=str(tmp_path)))
        assert result['status'] == 'success'
        assert result['fix_status'] == 'ok'
        assert result['fixed_count'] == 0

    def test_ok_when_docs_already_complete(self, tmp_path):
        """Should return ok when docs already have all required content."""
        claude_md = tmp_path / 'CLAUDE.md'
        claude_md.write_text(
            '# Project\n\nUse `.plan/temp/` for temporary files.\n\n'
            'use Glob, Read, Grep tools.\n'
        )
        result = cmd_fix_docs(Namespace(project_root=str(tmp_path)))
        assert result['fix_status'] == 'ok'
        assert result['fixed_count'] == 0

    def test_fixes_missing_plan_temp_in_claude_md(self, tmp_path):
        """Should append plan_temp content to CLAUDE.md."""
        claude_md = tmp_path / 'CLAUDE.md'
        claude_md.write_text('# Project\n\nuse Glob, Read, Grep tools.\n')
        result = cmd_fix_docs(Namespace(project_root=str(tmp_path)))
        assert result['fix_status'] == 'fixed'
        assert 'plan_temp:CLAUDE.md' in result['fixes']

        content = claude_md.read_text()
        assert '.plan/temp/' in content
        assert 'Write(.plan/**)' in content

    def test_fixes_missing_file_ops(self, tmp_path):
        """Should append file_ops content to CLAUDE.md."""
        claude_md = tmp_path / 'CLAUDE.md'
        claude_md.write_text('# Project\n\nUse .plan/temp for files.\n')
        result = cmd_fix_docs(Namespace(project_root=str(tmp_path)))
        assert result['fix_status'] == 'fixed'
        assert 'file_ops:CLAUDE.md' in result['fixes']

        content = claude_md.read_text()
        assert 'use Glob, Read, Grep' in content

    def test_fixes_multiple_missing_checks(self, tmp_path):
        """Should fix all missing checks in one call."""
        claude_md = tmp_path / 'CLAUDE.md'
        claude_md.write_text('# Project\n')
        result = cmd_fix_docs(Namespace(project_root=str(tmp_path)))
        assert result['fix_status'] == 'fixed'
        assert result['fixed_count'] == 2

        content = claude_md.read_text()
        assert '.plan/temp/' in content
        assert 'use Glob, Read, Grep' in content

    def test_fixes_agents_md_plan_temp(self, tmp_path):
        """Should append plan_temp to agents.md when missing."""
        agents_md = tmp_path / 'agents.md'
        agents_md.write_text('# Agents\n')
        result = cmd_fix_docs(Namespace(project_root=str(tmp_path)))
        assert result['fix_status'] == 'fixed'
        assert 'plan_temp:agents.md' in result['fixes']

        content = agents_md.read_text()
        assert '.plan/temp/' in content

    def test_idempotent_on_second_run(self, tmp_path):
        """Running fix-docs twice should be idempotent."""
        claude_md = tmp_path / 'CLAUDE.md'
        claude_md.write_text('# Project\n')

        cmd_fix_docs(Namespace(project_root=str(tmp_path)))
        result2 = cmd_fix_docs(Namespace(project_root=str(tmp_path)))
        assert result2['fix_status'] == 'ok'
        assert result2['fixed_count'] == 0

    def test_fix_docs_function_directly(self, tmp_path):
        """Test the raw fix_docs function."""
        status, fixes = fix_docs(tmp_path)
        assert status == 'ok'
        assert fixes == []


# =============================================================================
# Subprocess (Tier 3) tests — CLI plumbing only
# =============================================================================


class TestSubcommandRequired:
    """Test that subcommand is required (CLI plumbing)."""

    def test_error_without_subcommand(self):
        """Should error when no subcommand is provided."""
        result = run_script(SCRIPT_PATH)
        assert result.returncode != 0

    def test_toon_output_format(self, tmp_path):
        """Output should be valid TOON format (colon-space key-value pairs)."""
        plan_dir = tmp_path / '.plan'
        plan_dir.mkdir(parents=True)

        result = run_script(SCRIPT_PATH, 'mode', cwd=tmp_path)
        assert result.success, f'Script failed: {result.stderr}'

        lines = result.stdout.strip().split('\n')
        # status, mode, reason = 3 lines
        assert len(lines) == 3
        for line in lines:
            assert ': ' in line, f'Line should contain colon-space separator: {line}'


# =============================================================================
# D4: Blocking-types mapping (dict[str, Callable]) shape tests
# =============================================================================


import determine_mode as _determine_mode_module  # type: ignore[import-not-found]  # noqa: E402, I001
import pytest  # noqa: E402, I001


def test_global_blocking_types_is_dict():
    """``_GLOBAL_BLOCKING_TYPES`` is a ``dict[str, Callable]`` (D4 shape contract)."""
    # Arrange + Act
    blocking_types = _determine_mode_module._GLOBAL_BLOCKING_TYPES

    # Assert
    assert isinstance(blocking_types, dict), (
        f'_GLOBAL_BLOCKING_TYPES must be a dict per the D4 typed-mapping refactor, '
        f'got {type(blocking_types).__name__}'
    )


def test_global_blocking_types_keys_preserve_legacy_string_set():
    """Dict keys preserve the previous flat-list string set verbatim."""
    # Arrange
    expected = {'build-error', 'test-failure', 'lint-issue', 'sonar-issue', 'qgate'}

    # Act
    actual = set(_determine_mode_module._GLOBAL_BLOCKING_TYPES.keys())

    # Assert
    assert actual == expected, (
        f'Dict keys must preserve the legacy blocking-type set. Expected {expected}, got {actual}'
    )


def test_global_blocking_types_every_value_is_callable():
    """Every value in the mapping is callable (no string-only fallback shape)."""
    # Arrange + Act
    blocking_types = _determine_mode_module._GLOBAL_BLOCKING_TYPES

    # Assert
    for key, value in blocking_types.items():
        assert callable(value), f"Blocking-type {key!r} has non-callable value {value!r}"


def test_finalize_blocking_types_is_dict_and_includes_pr_comment():
    """``_FINALIZE_BLOCKING_TYPES`` is a dict and extends with pr-comment."""
    # Arrange + Act
    finalize_types = _determine_mode_module._FINALIZE_BLOCKING_TYPES

    # Assert
    assert isinstance(finalize_types, dict)
    assert 'pr-comment' in finalize_types
    # Every base type also appears.
    for key in _determine_mode_module._GLOBAL_BLOCKING_TYPES:
        assert key in finalize_types, f'_FINALIZE_BLOCKING_TYPES missing base type {key!r}'


def test_default_blocking_partition_seeds_from_dict_keys():
    """``_DEFAULT_BLOCKING_PARTITION`` consumes ``list(_GLOBAL_BLOCKING_TYPES)`` for non-finalize phases."""
    # Arrange + Act
    partition = _determine_mode_module._DEFAULT_BLOCKING_PARTITION
    expected_keys = set(_determine_mode_module._GLOBAL_BLOCKING_TYPES.keys())

    # Assert — non-finalize phases get the global key set.
    for phase in ('phase-1-init', 'phase-2-refine', 'phase-3-outline', 'phase-4-plan', 'phase-5-execute'):
        actual = set(partition[phase])
        assert actual == expected_keys, (
            f'Phase {phase} partition diverged from _GLOBAL_BLOCKING_TYPES keys: '
            f'expected {expected_keys}, got {actual}'
        )

    # Finalize phase extends with pr-comment.
    finalize_actual = set(partition['phase-6-finalize'])
    finalize_expected = expected_keys | {'pr-comment'}
    assert finalize_actual == finalize_expected


def test_validate_blocking_types_mapping_rejects_non_callable():
    """Adding a string entry without a callable raises ``TypeError`` (import-time invariant)."""
    # Arrange
    bad_mapping = {'new-type': 'not_a_callable'}

    # Act / Assert
    with pytest.raises(TypeError) as excinfo:
        _determine_mode_module._validate_blocking_types_mapping(bad_mapping)
    assert 'new-type' in str(excinfo.value)
    assert 'non-callable' in str(excinfo.value).lower()


def test_validate_blocking_types_mapping_rejects_unregistered_callable():
    """Mapping to an unknown callable also raises — only registered thunks allowed."""
    # Arrange — a callable that is NOT in BLOCKING_TYPE_CALLABLE_NAMES.
    def rogue_callable(plan_id, finding_type):
        return 0

    bad_mapping = {'rogue-type': rogue_callable}

    # Act / Assert
    with pytest.raises(TypeError) as excinfo:
        _determine_mode_module._validate_blocking_types_mapping(bad_mapping)
    message = str(excinfo.value)
    assert 'rogue-type' in message
    assert 'unregistered callable' in message.lower()


def test_validate_blocking_types_mapping_accepts_registered_thunks():
    """Mapping every entry to a registered thunk passes validation."""
    # Arrange — mirror the in-module mapping using only registered thunks.
    good_mapping = {
        'foo': _determine_mode_module._generic_query_thunk,
        'bar': _determine_mode_module._qgate_aggregated_query_thunk,
    }

    # Act / Assert — no exception.
    _determine_mode_module._validate_blocking_types_mapping(good_mapping)


def test_blocking_type_callable_names_registry_lists_both_thunks():
    """The registry maps each registered thunk to its canonical name."""
    # Arrange
    registry = _determine_mode_module.BLOCKING_TYPE_CALLABLE_NAMES

    # Act + Assert
    assert _determine_mode_module._generic_query_thunk in registry
    assert _determine_mode_module._qgate_aggregated_query_thunk in registry
    assert registry[_determine_mode_module._generic_query_thunk] == _determine_mode_module.GENERIC_PENDING_QUERY
    assert registry[_determine_mode_module._qgate_aggregated_query_thunk] == _determine_mode_module.QGATE_AGGREGATED_QUERY


# =============================================================================
# check-working-prefixes subcommand (project.working_prefixes presence/drift)
# =============================================================================


import copy  # noqa: E402, I001
import json  # noqa: E402, I001

_DEFAULT_WORKING_PREFIXES = DEFAULT_PROJECT['working_prefixes']


def _write_marshal(plan_dir, config: dict) -> None:
    """Write a marshal.json fixture under ``plan_dir`` (created on demand)."""
    plan_dir.mkdir(parents=True, exist_ok=True)
    (plan_dir / 'marshal.json').write_text(json.dumps(config, indent=2), encoding='utf-8')


class TestCheckWorkingPrefixesSubcommand:
    """Test the 'check-working-prefixes' subcommand and its detector."""

    def test_present_and_current_not_flagged(self, tmp_path):
        """A marshal.json whose project.working_prefixes equals the default returns ok."""
        # Arrange
        plan_dir = tmp_path / '.plan'
        _write_marshal(plan_dir, {'project': {'working_prefixes': copy.deepcopy(_DEFAULT_WORKING_PREFIXES)}})

        # Act
        result = cmd_check_working_prefixes(Namespace(plan_dir=str(plan_dir)))

        # Assert
        assert result == {'status': 'ok'}

    def test_absent_key_flagged(self, tmp_path):
        """A project block lacking working_prefixes returns missing/absent."""
        # Arrange — project present but no working_prefixes key
        plan_dir = tmp_path / '.plan'
        _write_marshal(plan_dir, {'project': {'default_base_branch': 'main'}})

        # Act
        result = cmd_check_working_prefixes(Namespace(plan_dir=str(plan_dir)))

        # Assert
        assert result['status'] == 'missing'
        assert result['detail'] == 'absent'
        assert result['missing_keys'] == 'working_prefixes'

    def test_customized_superset_not_clobbered(self, tmp_path):
        """An operator superset (added prefixes) is honoured — never flagged."""
        # Arrange — working_prefixes is a strict superset of the default
        superset = [*copy.deepcopy(_DEFAULT_WORKING_PREFIXES), 'spike/']
        plan_dir = tmp_path / '.plan'
        _write_marshal(plan_dir, {'project': {'working_prefixes': superset}})

        # Act
        result = cmd_check_working_prefixes(Namespace(plan_dir=str(plan_dir)))

        # Assert — additions are honoured (non-clobbering)
        assert result == {'status': 'ok'}

    def test_drift_missing_default_entry_flagged(self, tmp_path):
        """A working_prefixes missing a default entry returns missing/drift."""
        # Arrange — drop 'chore/' from working_prefixes
        drifted = [e for e in copy.deepcopy(_DEFAULT_WORKING_PREFIXES) if e != 'chore/']
        plan_dir = tmp_path / '.plan'
        _write_marshal(plan_dir, {'project': {'working_prefixes': drifted}})

        # Act
        result = cmd_check_working_prefixes(Namespace(plan_dir=str(plan_dir)))

        # Assert — working_prefixes drifted
        assert result['status'] == 'missing'
        assert result['detail'] == 'drift'
        assert result['missing_keys'] == 'working_prefixes'

    def test_missing_marshal_not_flagged(self, tmp_path):
        """No marshal.json present returns ok (graceful degrade)."""
        # Arrange — empty plan dir, no marshal.json
        plan_dir = tmp_path / '.plan'
        plan_dir.mkdir(parents=True)

        # Act
        result = cmd_check_working_prefixes(Namespace(plan_dir=str(plan_dir)))

        # Assert
        assert result == {'status': 'ok'}

    def test_detect_returns_structured_outcome_for_absent(self, tmp_path):
        """detect_working_prefixes_drift returns the absent outcome with working_prefixes key."""
        # Arrange
        plan_dir = tmp_path / '.plan'
        _write_marshal(plan_dir, {'project': {}})

        # Act
        result = detect_working_prefixes_drift(plan_dir)

        # Assert
        assert result == {'outcome': 'absent', 'missing_keys': ['working_prefixes']}

    def test_cli_plumbing_emits_toon(self, tmp_path):
        """check-working-prefixes via subprocess emits valid TOON for the absent case."""
        # Arrange
        plan_dir = tmp_path / '.plan'
        _write_marshal(plan_dir, {'project': {}})

        # Act
        result = run_script(SCRIPT_PATH, 'check-working-prefixes', '--plan-dir', str(plan_dir))

        # Assert — exit 0 and TOON colon-space key-value lines
        assert result.success, f'Script failed: {result.stderr}'
        parsed = result.toon()
        assert parsed['status'] == 'missing'
        assert parsed['detail'] == 'absent'
        assert str(parsed['missing_keys']) == 'working_prefixes'
