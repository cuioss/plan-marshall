#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the ``record-step`` subcommand of manage-execution-manifest.py.

The ``record-step`` subcommand appends per-step execution-log rows (outcome +
token attribution) to the manifest's ``execution_log[]`` section. These tests
cover:

- appending ``executed`` / ``skipped`` / ``error`` rows with token attribution;
- the three-state token columns: an explicitly-passed value (including ``0``) is a
  MEASURED value, an OMITTED flag records the ``unmeasured`` token, and the two
  differ in the file bytes;
- the five-way outcome partition — a productive ``loop_back``, a clean run with a
  negative verdict (``failed``), and a dispatch that raised (``error``) are three
  different situations and are recorded as three different values;
- the ordered append-log semantics (re-recording the same step appends another
  row; reading back reflects the recorded sequence);
- ``execution_log_count`` tracking the running row count;
- the missing-manifest error path (TOON ``file_not_found``);
- input-validation rejection of an unknown phase / outcome / malformed step_id
  (a comma or any line separator in --step-id is refused, mirroring the
  record-dispatch-boundary writer so the two writers accept the identical key
  space);
- a CLI subprocess roundtrip exercising the executor plumbing.

Mirrors the tier-2 direct-import + CLI-subprocess split used by the sibling
``test_manage_execution_manifest_read.py`` / ``_validate.py`` suites.
"""

from argparse import Namespace

import pytest

from conftest import get_script_path, load_script_module, parse_ns, run_script

# Script path for subprocess (CLI plumbing) tests. Split into module-level string
# constants so the `parse_ns` calls below stay statically resolvable for the
# loader-registration walker in `test_conftest_loader_contract`.
_BUNDLE = 'plan-marshall'
_SKILL = 'manage-execution-manifest'
_SCRIPT_NAME = 'manage-execution-manifest.py'

SCRIPT_PATH = get_script_path(_BUNDLE, _SKILL, _SCRIPT_NAME)

# Tier 2 direct imports, resolved by (bundle, skill, script).


_mem = load_script_module(
    'plan-marshall', 'manage-execution-manifest', 'manage-execution-manifest.py', module_name='_mem_script'
)
cmd_compose = _mem.cmd_compose
cmd_record_step = _mem.cmd_record_step
read_manifest = _mem.read_manifest
get_plan_dir = _mem.get_plan_dir
EXECUTION_LOG_KEY = _mem.EXECUTION_LOG_KEY
MANIFEST_FILENAME = _mem.MANIFEST_FILENAME
UNMEASURED_COLUMN_TOKEN = _mem.UNMEASURED_COLUMN_TOKEN
VALID_RECORD_PHASES = _mem.VALID_RECORD_PHASES
VALID_RECORD_OUTCOMES = _mem.VALID_RECORD_OUTCOMES
DEFAULT_PHASE_6_STEPS = _mem.DEFAULT_PHASE_6_STEPS

# Step-ownership routing primitives live in _manifest_core (loaded directly:
# the hyphenated entry does not re-export them). See the "Step ownership"
# section in _manifest_core.py.
_core = load_script_module('plan-marshall', 'manage-execution-manifest', '_manifest_core.py', module_name='_mem_core')
owner_of = _core.owner_of
is_leaf_dispatchable = _core.is_leaf_dispatchable
validate_step_owner = _core.validate_step_owner
VALID_STEP_OWNERS = _core.VALID_STEP_OWNERS
DEFAULT_STEP_OWNER = _core.DEFAULT_STEP_OWNER
ORCHESTRATOR_OWNED_STEPS = _core.ORCHESTRATOR_OWNED_STEPS

# Quiet down the best-effort decision-log writes so tests don't depend on a
# running executor / a resolvable plan log dir.
_mem._log_decision = lambda *a, **kw: None
_mem._log_record_step = lambda *a, **kw: None

# =============================================================================
# Namespace Helpers
# =============================================================================


def _compose_ns(
    plan_id: str = 'rec-plan',
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


def _record_ns(
    plan_id: str = 'rec-plan',
    step_id: str = 'verify:quality-gate',
    phase: str = '5-execute',
    outcome: str = 'executed',
    total_tokens: int | None = None,
    tool_uses: int | None = None,
    duration_ms: int | None = None,
) -> Namespace:
    """Build ``record-step`` args through the script's OWN parser.

    ``None`` means the flag is OMITTED from the argv — the state the writer
    records as the ``unmeasured`` token. That distinction cannot be expressed by a
    hand-built ``argparse.Namespace``: the whole discriminator lives in the
    parser's ``default=None``, so a namespace assembled by hand bypasses the one
    thing under test and would let the omitted case pass against a writer that
    still defaults to ``0``.
    """
    argv = [
        'record-step',
        '--plan-id',
        plan_id,
        '--step-id',
        step_id,
        '--phase',
        phase,
        '--outcome',
        outcome,
    ]
    for flag, value in (
        ('--total-tokens', total_tokens),
        ('--tool-uses', tool_uses),
        ('--duration-ms', duration_ms),
    ):
        if value is not None:
            argv += [flag, str(value)]
    ns: Namespace = parse_ns(_BUNDLE, _SKILL, _SCRIPT_NAME, *argv, register=False)
    return ns


def _compose(plan_id: str) -> None:
    """Materialize a manifest for ``plan_id`` (record-step requires one)."""
    cmd_compose(_compose_ns(plan_id=plan_id))
