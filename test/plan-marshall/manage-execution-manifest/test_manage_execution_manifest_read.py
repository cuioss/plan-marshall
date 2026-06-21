#!/usr/bin/env python3
"""Tests for the ``read`` subcommand of manage-execution-manifest.py.

Split from test_manage_execution_manifest.py — tier 2 direct-import tests for
the read path plus the CLI roundtrip for the missing-manifest error case.
"""

import importlib.util
import json
from argparse import Namespace
from pathlib import Path

from conftest import get_script_path, run_script

# Script path for subprocess (CLI plumbing) tests.
SCRIPT_PATH = get_script_path('plan-marshall', 'manage-execution-manifest', 'manage-execution-manifest.py')

# Tier 2 direct imports via importlib (scripts loaded via PYTHONPATH at runtime).
_SCRIPTS_DIR = (
    Path(__file__).parent.parent.parent.parent
    / 'marketplace'
    / 'bundles'
    / 'plan-marshall'
    / 'skills'
    / 'manage-execution-manifest'
    / 'scripts'
)


def _load_module(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, _SCRIPTS_DIR / filename)
    assert spec is not None, f'Failed to load module spec for {filename}'
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


_mem = _load_module('_mem_script', 'manage-execution-manifest.py')
cmd_compose = _mem.cmd_compose
cmd_read = _mem.cmd_read
_read_marshal_phase_step_map = _mem._read_marshal_phase_step_map
DEFAULT_PHASE_5_STEPS = _mem.DEFAULT_PHASE_5_STEPS
DEFAULT_PHASE_6_STEPS = _mem.DEFAULT_PHASE_6_STEPS

# Quiet down the best-effort decision-log subprocess so tests don't depend on a
# running executor. The handler is wrapped in try/except so failures are
# already silent, but we replace it with a no-op for clarity and speed.
_mem._log_decision = lambda *a, **kw: None  # type: ignore[attr-defined]


# =============================================================================
# Namespace Helpers
# =============================================================================


def _compose_ns(
    plan_id: str = 'test-plan',
    change_type: str = 'feature',
    track: str = 'complex',
    scope_estimate: str = 'multi_module',
    recipe_key: str | None = None,
    affected_files_count: int = 5,
    phase_5_steps: str | None = 'quality-gate,module-tests',
    phase_6_steps: str | None = ','.join(DEFAULT_PHASE_6_STEPS),
    commit_and_push: str | None = None,
) -> Namespace:
    return Namespace(
        plan_id=plan_id,
        change_type=change_type,
        track=track,
        scope_estimate=scope_estimate,
        recipe_key=recipe_key,
        affected_files_count=affected_files_count,
        phase_5_steps=phase_5_steps,
        phase_6_steps=phase_6_steps,
        commit_and_push=commit_and_push,
    )


def _read_ns(plan_id: str = 'test-plan') -> Namespace:
    return Namespace(plan_id=plan_id)


# =============================================================================
# read subcommand tests
# =============================================================================


def test_read_returns_full_manifest(plan_context):
    cmd_compose(_compose_ns(plan_id='io-read'))
    result = cmd_read(_read_ns(plan_id='io-read'))
    assert result is not None and result['status'] == 'success'
    assert result['plan_id'] == 'io-read'
    assert 'phase_5' in result
    assert 'phase_6' in result


def test_read_missing_manifest_returns_none_with_toon_error(plan_context, capsys):
    result = cmd_read(_read_ns(plan_id='io-missing'))
    assert result is None
    captured = capsys.readouterr()
    assert 'file_not_found' in captured.out


def test_read_returns_all_manifest_keys(plan_context):
    """read echoes every manifest field the composer wrote."""
    cmd_compose(_compose_ns(plan_id='io-read-fields'))
    result = cmd_read(_read_ns(plan_id='io-read-fields'))
    assert result is not None
    # Mandatory schema keys.
    assert result['manifest_version'] == 1
    assert 'phase_5' in result and 'phase_6' in result
    # phase_5 sub-keys.
    assert 'early_terminate' in result['phase_5']
    assert 'verification_steps' in result['phase_5']
    # The composer snapshots each selected step's resolved params into the
    # manifest body under step_params (keyed by the in-manifest step id).
    assert 'step_params' in result['phase_5']
    assert isinstance(result['phase_5']['step_params'], dict)
    # phase_6 sub-keys.
    assert 'steps' in result['phase_6']
    assert 'step_params' in result['phase_6']
    assert isinstance(result['phase_6']['step_params'], dict)


def test_read_snapshots_step_params_for_each_selected_step(plan_context):
    """The phase_5 step_params snapshot carries one entry per selected verify step."""
    cmd_compose(_compose_ns(plan_id='io-read-snapshot'))
    result = cmd_read(_read_ns(plan_id='io-read-snapshot'))
    assert result is not None

    verification_steps = result['phase_5']['verification_steps']
    step_params = result['phase_5']['step_params']
    # one snapshot entry per selected step; verify steps own no params (CSV path
    # seeds empty param objects since no marshal.json keyed map is present)
    assert set(step_params.keys()) == set(verification_steps)
    assert all(params == {} for params in step_params.values())


# =============================================================================
# Dual-form READER tests: _read_marshal_phase_step_map normalizes LIST and
# keyed-map on-disk forms to the SAME internal {step_id: {params}} dict.
# =============================================================================
#
# The reader reads marshal.json from get_marshal_path(), which honours
# PLAN_BASE_DIR (set to tmp_path by the plan_context fixture). Each test writes
# a marshal.json carrying the phase's step field in one of the two on-disk
# serial forms and asserts the normalized internal dict.


def _write_marshal_phase(fixture_dir: Path, phase_key: str, step_value) -> None:
    """Write a minimal marshal.json with ``plan.{phase_key}.{field} = step_value``.

    ``field`` is ``verification_steps`` for ``phase-5-execute`` and ``steps``
    otherwise — matching the reader's phase-aware field selection. The marshal
    lands at ``{fixture_dir}/marshal.json``, which is where ``get_marshal_path()``
    resolves under the ``plan_context`` ``PLAN_BASE_DIR=tmp_path`` redirect.
    """
    field = 'verification_steps' if phase_key == 'phase-5-execute' else 'steps'
    data = {'plan': {phase_key: {field: step_value}}}
    (fixture_dir / 'marshal.json').write_text(json.dumps(data, indent=2))


def test_read_step_map_list_form_round_trips_unchanged(plan_context):
    """A LIST input (bare strings + single-key objects) normalizes to the internal dict."""
    _write_marshal_phase(
        plan_context.fixture_dir,
        'phase-6-finalize',
        [
            'default:commit-push',
            {'default:automated-review': {'review_bot_buffer_seconds': 300}},
            'default:archive-plan',
        ],
    )

    result = _read_marshal_phase_step_map('phase-6-finalize')

    assert result == {
        'default:commit-push': {},
        'default:automated-review': {'review_bot_buffer_seconds': 300},
        'default:archive-plan': {},
    }


def test_read_step_map_keyed_and_list_forms_normalize_identically_finalize(plan_context):
    """keyed-map and LIST inputs produce IDENTICAL internal dicts for phase-6 steps."""
    list_form = [
        'default:commit-push',
        {'default:automated-review': {'review_bot_buffer_seconds': 300}},
        'default:archive-plan',
    ]
    keyed_form = {
        'default:commit-push': {},
        'default:automated-review': {'review_bot_buffer_seconds': 300},
        'default:archive-plan': {},
    }

    _write_marshal_phase(plan_context.fixture_dir, 'phase-6-finalize', list_form)
    from_list = _read_marshal_phase_step_map('phase-6-finalize')

    _write_marshal_phase(plan_context.fixture_dir, 'phase-6-finalize', keyed_form)
    from_keyed = _read_marshal_phase_step_map('phase-6-finalize')

    assert from_list == from_keyed
    assert from_list == keyed_form


def test_read_step_map_keyed_and_list_forms_normalize_identically_execute(plan_context):
    """keyed-map and LIST inputs produce IDENTICAL internal dicts for phase-5 verification_steps."""
    list_form = ['default:verify:quality-gate', 'default:verify:module-tests']
    keyed_form = {
        'default:verify:quality-gate': {},
        'default:verify:module-tests': {},
    }

    _write_marshal_phase(plan_context.fixture_dir, 'phase-5-execute', list_form)
    from_list = _read_marshal_phase_step_map('phase-5-execute')

    _write_marshal_phase(plan_context.fixture_dir, 'phase-5-execute', keyed_form)
    from_keyed = _read_marshal_phase_step_map('phase-5-execute')

    assert from_list == from_keyed
    assert from_list == keyed_form


def test_read_step_map_list_form_preserves_execution_order(plan_context):
    """LIST array order is the execution order — the internal dict preserves it."""
    _write_marshal_phase(
        plan_context.fixture_dir,
        'phase-6-finalize',
        ['default:archive-plan', 'default:commit-push', 'default:create-pr'],
    )

    result = _read_marshal_phase_step_map('phase-6-finalize')

    assert list(result.keys()) == [
        'default:archive-plan',
        'default:commit-push',
        'default:create-pr',
    ]


def test_read_step_map_empty_list_normalizes_to_empty_dict(plan_context):
    """An empty LIST normalizes to an empty internal dict (edge case)."""
    _write_marshal_phase(plan_context.fixture_dir, 'phase-6-finalize', [])

    result = _read_marshal_phase_step_map('phase-6-finalize')

    assert result == {}


def test_read_step_map_single_entry_list_forms(plan_context):
    """Single-entry LIST forms — one bare string and one single-key object (edge case)."""
    _write_marshal_phase(plan_context.fixture_dir, 'phase-6-finalize', ['default:commit-push'])
    bare = _read_marshal_phase_step_map('phase-6-finalize')
    assert bare == {'default:commit-push': {}}

    _write_marshal_phase(
        plan_context.fixture_dir,
        'phase-6-finalize',
        [{'default:automated-review': {'review_bot_buffer_seconds': 300}}],
    )
    keyed = _read_marshal_phase_step_map('phase-6-finalize')
    assert keyed == {'default:automated-review': {'review_bot_buffer_seconds': 300}}


def test_read_step_map_neither_list_nor_dict_returns_none(plan_context):
    """A scalar step value (neither list nor dict) returns None — malformed input."""
    _write_marshal_phase(plan_context.fixture_dir, 'phase-6-finalize', 'not-a-collection')

    assert _read_marshal_phase_step_map('phase-6-finalize') is None


# =============================================================================
# CLI plumbing (subprocess) tests for read
# =============================================================================


def test_cli_read_missing_manifest_emits_toon_error(plan_context):
    """read without a prior compose emits file_not_found via TOON."""
    result = run_script(SCRIPT_PATH, 'read', '--plan-id', 'cli-no-manifest')
    # Script exits 0 on missing-file errors (TOON contract).
    assert result.returncode == 0
    data = result.toon()
    assert data['status'] == 'error'
    assert data['error'] == 'file_not_found'
