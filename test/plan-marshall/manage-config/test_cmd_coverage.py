#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for `manage-config coverage read` / `coverage resolve` resolver.

Covers the per-field polymorphic resolver walk
(``plan.<phase>.coverage.<field>`` -> ``plan.coverage.<field>`` ->
``inherit``), the polymorphic per-phase-vs-plan-wide shape, the
``inherit`` default, the resolved-cell output shape, and the load-bearing
scope<->thoroughness coupling-violation rejection
(``thoroughness >= T4 AND scope < component``).

Isolation: each test uses the ``plan_context`` fixture (tmp_path-scoped
``MARSHAL_PATH`` monkeypatch), so every test gets a fresh marshal.json with
no cross-test contamination.
"""

import importlib.util
import json
import sys
from argparse import Namespace
from pathlib import Path

from test_helpers import create_marshal_json

_MANAGE_CONFIG_SCRIPTS_DIR = (
    Path(__file__).parent.parent.parent.parent
    / 'marketplace'
    / 'bundles'
    / 'plan-marshall'
    / 'skills'
    / 'manage-config'
    / 'scripts'
)

if str(_MANAGE_CONFIG_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_MANAGE_CONFIG_SCRIPTS_DIR))


def _load_module(name: str, filename: str, scripts_dir: Path):
    spec = importlib.util.spec_from_file_location(name, scripts_dir / filename)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


_cmd_coverage_mod = _load_module(
    '_cmd_coverage', '_cmd_coverage.py', _MANAGE_CONFIG_SCRIPTS_DIR
)
cmd_coverage_read = _cmd_coverage_mod.cmd_coverage_read
cmd_coverage_resolve = _cmd_coverage_mod.cmd_coverage_resolve
ALLOWED_THOROUGHNESS = _cmd_coverage_mod.ALLOWED_THOROUGHNESS
ALLOWED_SCOPE = _cmd_coverage_mod.ALLOWED_SCOPE


def _write_coverage_config(
    fixture_dir: Path,
    *,
    plan_wide: dict | None = None,
    per_phase: dict | None = None,
) -> None:
    """Write marshal.json with optional coverage config.

    Args:
        fixture_dir: The plan_context fixture directory (tmp_path).
        plan_wide: Object written at ``plan.coverage`` (plan-wide fallback).
        per_phase: Mapping of phase name -> coverage object, written at
            ``plan.<phase>.coverage``.
    """
    create_marshal_json(fixture_dir)
    marshal_path = fixture_dir / 'marshal.json'
    config = json.loads(marshal_path.read_text(encoding='utf-8'))
    plan_block = config.setdefault('plan', {})
    if plan_wide is not None:
        plan_block['coverage'] = plan_wide
    if per_phase is not None:
        for phase, coverage in per_phase.items():
            phase_entry = plan_block.setdefault(phase, {})
            phase_entry['coverage'] = coverage
    marshal_path.write_text(json.dumps(config, indent=2), encoding='utf-8')


def _read_args(*, phase=None, role=None, default=False) -> Namespace:
    return Namespace(phase=phase, role=role, default=default)


# =============================================================================
# Enum lock-step with the thoroughness.md ladders
# =============================================================================


def test_allowed_enums_match_ladders():
    assert ALLOWED_THOROUGHNESS == ('T1', 'T2', 'T3', 'T4', 'T5', 'inherit')
    assert ALLOWED_SCOPE == (
        'change-set',
        'artifact',
        'component',
        'module',
        'overall',
        'inherit',
    )


# =============================================================================
# (1) Per-phase resolution — a configured phase cell resolves directly
# =============================================================================


def test_read_resolves_per_phase_cell(plan_context):
    _write_coverage_config(
        plan_context.fixture_dir,
        per_phase={'phase-5-execute': {'thoroughness': 'T3', 'scope': 'component'}},
    )

    result = cmd_coverage_read(_read_args(phase='phase-5-execute'))

    assert result['status'] == 'success'
    assert result['thoroughness'] == 'T3'
    assert result['scope'] == 'component'
    assert result['thoroughness_source'] == 'plan.phase-5-execute.coverage.thoroughness'
    assert result['scope_source'] == 'plan.phase-5-execute.coverage.scope'


def test_read_role_is_synonym_for_phase(plan_context):
    _write_coverage_config(
        plan_context.fixture_dir,
        per_phase={'phase-4-plan': {'thoroughness': 'T2', 'scope': 'module'}},
    )

    result = cmd_coverage_read(_read_args(role='phase-4-plan'))

    assert result['status'] == 'success'
    assert result['thoroughness'] == 'T2'
    assert result['scope'] == 'module'


def test_read_dotted_role_reduces_to_group(plan_context):
    _write_coverage_config(
        plan_context.fixture_dir,
        per_phase={'phase-5-execute': {'thoroughness': 'T2', 'scope': 'module'}},
    )

    result = cmd_coverage_read(_read_args(role='phase-5-execute.default'))

    assert result['status'] == 'success'
    assert result['thoroughness'] == 'T2'
    assert result['scope'] == 'module'


# =============================================================================
# (2) Plan-wide fallback — fields not set per-phase fall back to plan.coverage
# =============================================================================


def test_read_falls_back_to_plan_wide(plan_context):
    _write_coverage_config(
        plan_context.fixture_dir,
        plan_wide={'thoroughness': 'T2', 'scope': 'module'},
    )

    result = cmd_coverage_read(_read_args(phase='phase-5-execute'))

    assert result['status'] == 'success'
    assert result['thoroughness'] == 'T2'
    assert result['scope'] == 'module'
    assert result['thoroughness_source'] == 'plan.coverage.thoroughness'
    assert result['scope_source'] == 'plan.coverage.scope'


def test_read_mixed_per_phase_and_plan_wide_resolve_independently(plan_context):
    # thoroughness set per-phase, scope only plan-wide: each field walks
    # independently, so thoroughness comes from the phase and scope from
    # the plan-wide fallback.
    _write_coverage_config(
        plan_context.fixture_dir,
        plan_wide={'scope': 'overall'},
        per_phase={'phase-5-execute': {'thoroughness': 'T2'}},
    )

    result = cmd_coverage_read(_read_args(phase='phase-5-execute'))

    assert result['status'] == 'success'
    assert result['thoroughness'] == 'T2'
    assert result['thoroughness_source'] == 'plan.phase-5-execute.coverage.thoroughness'
    assert result['scope'] == 'overall'
    assert result['scope_source'] == 'plan.coverage.scope'


# =============================================================================
# (3) inherit default — unconfigured fields resolve to inherit
# =============================================================================


def test_read_unconfigured_resolves_to_inherit(plan_context):
    _write_coverage_config(plan_context.fixture_dir)

    result = cmd_coverage_read(_read_args(phase='phase-5-execute'))

    assert result['status'] == 'success'
    assert result['thoroughness'] == 'inherit'
    assert result['scope'] == 'inherit'
    assert result['thoroughness_source'] == 'implicit_default'
    assert result['scope_source'] == 'implicit_default'


def test_read_default_flag_reads_plan_wide(plan_context):
    _write_coverage_config(
        plan_context.fixture_dir,
        plan_wide={'thoroughness': 'T3', 'scope': 'component'},
    )

    result = cmd_coverage_read(_read_args(default=True))

    assert result['status'] == 'success'
    assert result['role'] == 'plan.coverage'
    assert result['thoroughness'] == 'T3'
    assert result['scope'] == 'component'


def test_read_default_flag_unconfigured_is_inherit(plan_context):
    _write_coverage_config(plan_context.fixture_dir)

    result = cmd_coverage_read(_read_args(default=True))

    assert result['status'] == 'success'
    assert result['thoroughness'] == 'inherit'
    assert result['scope'] == 'inherit'


# =============================================================================
# (4) Coupling-violation rejection — T4+ AND scope < component is a hard error
# =============================================================================


def test_read_rejects_t4_at_change_set(plan_context):
    _write_coverage_config(
        plan_context.fixture_dir,
        per_phase={'phase-5-execute': {'thoroughness': 'T4', 'scope': 'change-set'}},
    )

    result = cmd_coverage_read(_read_args(phase='phase-5-execute'))

    assert result['status'] == 'error'
    assert result['error_type'] == 'coverage_coupling_violation'
    assert 'T4' in result['error']
    assert 'component' in result['error']


def test_read_rejects_t5_at_artifact(plan_context):
    _write_coverage_config(
        plan_context.fixture_dir,
        per_phase={'phase-5-execute': {'thoroughness': 'T5', 'scope': 'artifact'}},
    )

    result = cmd_coverage_read(_read_args(phase='phase-5-execute'))

    assert result['status'] == 'error'
    assert result['error_type'] == 'coverage_coupling_violation'


def test_t4_at_component_is_coherent(plan_context):
    # T4 at component scope is the boundary case that MUST pass — component
    # is the coupling floor.
    _write_coverage_config(
        plan_context.fixture_dir,
        per_phase={'phase-5-execute': {'thoroughness': 'T4', 'scope': 'component'}},
    )

    result = cmd_coverage_read(_read_args(phase='phase-5-execute'))

    assert result['status'] == 'success'
    assert result['thoroughness'] == 'T4'
    assert result['scope'] == 'component'


def test_t3_at_change_set_is_coherent(plan_context):
    # T3 (one-hop local relations) does not require component scope.
    _write_coverage_config(
        plan_context.fixture_dir,
        per_phase={'phase-5-execute': {'thoroughness': 'T3', 'scope': 'change-set'}},
    )

    result = cmd_coverage_read(_read_args(phase='phase-5-execute'))

    assert result['status'] == 'success'
    assert result['thoroughness'] == 'T3'
    assert result['scope'] == 'change-set'


def test_inherit_thoroughness_with_narrow_scope_is_coherent(plan_context):
    # An unresolved thoroughness cannot violate the coupling.
    _write_coverage_config(
        plan_context.fixture_dir,
        per_phase={'phase-5-execute': {'scope': 'change-set'}},
    )

    result = cmd_coverage_read(_read_args(phase='phase-5-execute'))

    assert result['status'] == 'success'
    assert result['thoroughness'] == 'inherit'
    assert result['scope'] == 'change-set'


# =============================================================================
# (5) Enum validation — out-of-ladder values are rejected
# =============================================================================


def test_read_rejects_invalid_thoroughness(plan_context):
    _write_coverage_config(
        plan_context.fixture_dir,
        per_phase={'phase-5-execute': {'thoroughness': 'T9', 'scope': 'module'}},
    )

    result = cmd_coverage_read(_read_args(phase='phase-5-execute'))

    assert result['status'] == 'error'
    assert 'invalid thoroughness' in result['error']


def test_read_rejects_invalid_scope(plan_context):
    _write_coverage_config(
        plan_context.fixture_dir,
        per_phase={'phase-5-execute': {'thoroughness': 'T2', 'scope': 'galaxy'}},
    )

    result = cmd_coverage_read(_read_args(phase='phase-5-execute'))

    assert result['status'] == 'error'
    assert 'invalid scope' in result['error']


def test_read_rejects_unknown_phase(plan_context):
    _write_coverage_config(plan_context.fixture_dir)

    result = cmd_coverage_read(_read_args(phase='phase-99-bogus'))

    assert result['status'] == 'error'
    assert 'not a known phase' in result['error']


def test_read_requires_a_selector(plan_context):
    _write_coverage_config(plan_context.fixture_dir)

    result = cmd_coverage_read(_read_args())

    assert result['status'] == 'error'
    assert '--role' in result['error'] or '--phase' in result['error']


# =============================================================================
# (6) resolve verb — same cell plus a coupling: ok field
# =============================================================================


def test_resolve_returns_cell_and_coupling_ok(plan_context):
    _write_coverage_config(
        plan_context.fixture_dir,
        per_phase={'phase-5-execute': {'thoroughness': 'T4', 'scope': 'module'}},
    )

    result = cmd_coverage_resolve(_read_args(phase='phase-5-execute'))

    assert result['status'] == 'success'
    assert result['thoroughness'] == 'T4'
    assert result['scope'] == 'module'
    assert result['coupling'] == 'ok'
    assert result['thoroughness_source'] == 'plan.phase-5-execute.coverage.thoroughness'
    assert result['scope_source'] == 'plan.phase-5-execute.coverage.scope'


def test_resolve_propagates_coupling_violation(plan_context):
    _write_coverage_config(
        plan_context.fixture_dir,
        per_phase={'phase-5-execute': {'thoroughness': 'T4', 'scope': 'change-set'}},
    )

    result = cmd_coverage_resolve(_read_args(phase='phase-5-execute'))

    assert result['status'] == 'error'
    assert result['error_type'] == 'coverage_coupling_violation'
    assert 'coupling' not in result


# =============================================================================
# (7) non-string config values propagate to a clear validation error
# =============================================================================


def test_non_string_thoroughness_is_rejected_not_silently_inherited(plan_context):
    """A non-string thoroughness in marshal.json must fail loudly, not collapse.

    Regression guard for the ``isinstance(value, str)`` drop in ``_resolve_field``:
    a number written to the thoroughness slot previously fell through to
    ``inherit`` silently. It must now propagate to ``_validate_thoroughness``
    and surface a clear ``invalid thoroughness`` error.
    """
    _write_coverage_config(
        plan_context.fixture_dir,
        per_phase={'phase-5-execute': {'thoroughness': 4, 'scope': 'module'}},
    )

    result = cmd_coverage_read(_read_args(phase='phase-5-execute'))

    assert result['status'] == 'error'
    assert 'invalid thoroughness' in result['error']


def test_non_string_scope_is_rejected_not_silently_inherited(plan_context):
    """A non-string scope in marshal.json must fail loudly, not collapse to inherit."""
    _write_coverage_config(
        plan_context.fixture_dir,
        per_phase={'phase-5-execute': {'thoroughness': 'T2', 'scope': ['module']}},
    )

    result = cmd_coverage_read(_read_args(phase='phase-5-execute'))

    assert result['status'] == 'error'
    assert 'invalid scope' in result['error']
