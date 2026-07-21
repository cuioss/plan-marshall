#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Regression tests for the cmd_validate prefix-normalization fix.

Folded into this plan per operator decision. Two regressions are pinned here:

(a) **Prefix-agnostic validation**: ``compose`` boundary-normalizes manifest
    step IDs to BARE names (``canonicalize_step_key`` at intake), while a
    caller's ``--phase-{5,6}-steps`` allow-list CSV may still carry the optional
    ``default:`` prefix (e.g. ``default:verify:module-tests`` straight out of a
    project ``marshal.json`` step registry). ``cmd_validate`` strips the prefix
    from BOTH the allow-list and the manifest step IDs before the set-membership
    test, so a bare manifest ID validates SUCCESSFULLY against a
    ``default:``-prefixed allow-list (and vice versa). Before the fix this was
    a spurious ``invalid_manifest`` — every bare manifest ID looked "unknown"
    against the prefixed allow-list.

(b) **execution_tier routing appends BARE step IDs**: the composer's
    ``execution_tier`` routing maps an orchestrator-tier verb to a phase-5 step
    ID via ``_VERB_TO_PHASE_5_STEP``, which emits BARE names. The appended ID
    must match the boundary-normalized phase-5 list and never produce a stray
    ``default:verify:module-tests``.

These tests drive ``cmd_compose`` + ``cmd_validate`` directly (tier 2), staging
a ``marshal.json`` whose step registry carries ``default:``-prefixed IDs.
"""

import importlib.util
import json
from argparse import Namespace
from collections.abc import Callable
from pathlib import Path

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


_mem = _load_module('_mem_validate_prefix', 'manage-execution-manifest.py')
cmd_compose = _mem.cmd_compose
cmd_validate = _mem.cmd_validate
read_manifest = _mem.read_manifest
DEFAULT_PHASE_6_STEPS = _mem.DEFAULT_PHASE_6_STEPS

# Quiet down the best-effort decision-log subprocess.
_mem._log_decision = lambda *a, **kw: None
_mem._log_execution_tier_routing = lambda *a, **kw: None

# =============================================================================
# Namespace + fixture helpers
# =============================================================================


def _compose_ns(
    plan_id: str = 'test-plan',
    change_type: str = 'feature',
    track: str = 'complex',
    scope_estimate: str = 'multi_module',
    recipe_key: str | None = None,
    affected_files_count: int = 5,
    phase_5_steps: str | None = 'verify:quality-gate,verify:module-tests',
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


def _validate_ns(
    plan_id: str,
    phase_5_steps: str | None = None,
    phase_6_steps: str | None = None,
) -> Namespace:
    return Namespace(plan_id=plan_id, phase_5_steps=phase_5_steps, phase_6_steps=phase_6_steps)


def _write_full_marshal(
    fixture_dir: Path,
    *,
    phase_6_steps: list[str],
    phase_5_steps: list[str] | None = None,
) -> None:
    """Write a marshal.json with the given phase-5/6 step lists (prefixes preserved).

    The phase-5 list lands under ``phase-5-execute.verification_steps`` and the
    phase-6 list under ``phase-6-finalize.steps``, both in the clean-slate
    keyed-map shape (``{step_id: {param: value, ...}, ...}``) the migrated
    ``_read_marshal_phase_step_map`` requires. Each step gets an empty param
    object; dict-comprehension over the input list preserves insertion order
    (= execution order). No CI provider is declared for these fixtures.
    """
    marshal_path = fixture_dir / 'marshal.json'
    plan_block: dict = {'phase-6-finalize': {'steps': {step_id: {} for step_id in phase_6_steps}}}
    if phase_5_steps is not None:
        plan_block['phase-5-execute'] = {
            'verification_steps': {step_id: {} for step_id in phase_5_steps}
        }
    marshal_path.write_text(json.dumps({'plan': plan_block}), encoding='utf-8')


def _write_task(plans_root: Path, plan_id: str, number: int, commands: list[str]) -> None:
    """Write a minimal TASK-*.json with the supplied verification commands."""
    task = {
        'number': number,
        'title': f'Task {number}',
        'status': 'pending',
        'verification': {'commands': list(commands), 'manual': False},
        'steps': [],
    }
    tasks_dir = plans_root / plan_id / 'tasks'
    tasks_dir.mkdir(parents=True, exist_ok=True)
    (tasks_dir / f'TASK-{number:03d}.json').write_text(json.dumps(task, indent=2) + '\n', encoding='utf-8')


def _make_orchestrator_tier_stub() -> Callable[[str, str], dict | None]:
    """Fake ``_resolve_command_tier`` routing every build verb to orchestrator."""

    def _stub(cmd: str, plan_id: str) -> dict | None:
        parsed = _mem._parse_verification_command(cmd)
        if parsed is None:
            return None
        return {
            'status': 'success',
            'bash_timeout_seconds': 900,
            'exceeds_bash_ceiling': True,
            'execution_tier': 'orchestrator',
            'hint': 'Exceeds Bash ceiling; orchestrator-tier only',
        }

    return _stub


# =============================================================================
# (a) Prefix-agnostic validation: prefixed allow-list vs bare manifest IDs
# =============================================================================


def test_compose_then_validate_succeeds_with_prefixed_marshal_steps(plan_context):
    """compose+validate SUCCEEDS when marshal.json carries default:-prefixed step
    IDs while the manifest emits bare IDs.

    The marshal.json step registry lists ``default:``-prefixed phase-5 and
    phase-6 IDs. ``compose`` boundary-normalizes them to bare names in the
    manifest. ``cmd_validate`` is then handed a ``default:``-prefixed allow-list
    (the same prefixed shape the registry carries) and MUST report success —
    the bare-vs-prefixed match that previously raised a spurious
    ``invalid_manifest``.
    """
    plan_id = 'validate-prefix-ok'
    prefixed_phase_5 = ['default:verify:quality-gate', 'default:verify:module-tests']
    prefixed_phase_6 = [
        'default:push',
        'default:create-pr',
        'plan-marshall:automatic-review',
        'default:lessons-capture',
        'default:archive-plan',
    ]
    _write_full_marshal(
        plan_context.fixture_dir,
        phase_5_steps=prefixed_phase_5,
        phase_6_steps=prefixed_phase_6,
    )

    compose_result = cmd_compose(_compose_ns(plan_id=plan_id, affected_files_count=8))
    assert compose_result is not None and compose_result['status'] == 'success'

    # Sanity: the manifest carries BARE IDs (boundary-normalized).
    manifest = read_manifest(plan_id)
    assert manifest is not None
    assert not any(s.startswith('default:') for s in manifest['phase_5']['verification_steps'])
    assert not any(s.startswith('default:') for s in manifest['phase_6']['steps'])

    # Validate with a default:-PREFIXED allow-list — prefix-agnostic membership
    # must accept the bare manifest IDs.
    result = cmd_validate(
        _validate_ns(
            plan_id=plan_id,
            phase_5_steps=','.join(prefixed_phase_5),
            phase_6_steps=','.join(prefixed_phase_6),
        )
    )
    assert result is not None and result['status'] == 'success'
    assert result['valid'] is True
    assert result['phase_5_unknown_steps_count'] == 0
    assert result['phase_6_unknown_steps_count'] == 0


def test_validate_bare_manifest_against_bare_allowlist_still_succeeds(plan_context):
    """Sanity: the bare-vs-bare path is unaffected by the prefix-stripping fix."""
    plan_id = 'validate-bare-ok'
    _write_full_marshal(
        plan_context.fixture_dir,
        phase_5_steps=['verify:quality-gate', 'verify:module-tests'],
        phase_6_steps=['push', 'create-pr', 'lessons-capture', 'archive-plan'],
    )
    compose_result = cmd_compose(_compose_ns(plan_id=plan_id, affected_files_count=8))
    assert compose_result is not None and compose_result['status'] == 'success'

    result = cmd_validate(
        _validate_ns(
            plan_id=plan_id,
            phase_5_steps='verify:quality-gate,verify:module-tests',
            phase_6_steps='push,create-pr,lessons-capture,archive-plan',
        )
    )
    assert result is not None and result['status'] == 'success'
    assert result['valid'] is True


def test_validate_flags_genuinely_unknown_step_despite_prefix_stripping(plan_context):
    """Prefix stripping must NOT mask a genuinely unknown step ID.

    A manifest carrying ``verify:module-tests`` validated against an allow-list
    that only permits ``verify:quality-gate`` (even prefixed) is still flagged —
    the fix normalizes prefixes, it does not make every ID match.
    """
    plan_id = 'validate-prefix-unknown'
    _write_full_marshal(
        plan_context.fixture_dir,
        phase_5_steps=['default:verify:quality-gate', 'default:verify:module-tests'],
        phase_6_steps=['default:push', 'default:archive-plan'],
    )
    compose_result = cmd_compose(_compose_ns(plan_id=plan_id, affected_files_count=8))
    assert compose_result is not None and compose_result['status'] == 'success'

    # Allow-list omits verify:module-tests — it must surface as unknown.
    result = cmd_validate(
        _validate_ns(
            plan_id=plan_id,
            phase_5_steps='default:verify:quality-gate',
        )
    )
    assert result is not None and result['status'] == 'error'
    assert result['error'] == 'invalid_manifest'
    assert result['phase_5_unknown_steps_count'] == 1
    assert 'verify:module-tests' in result['phase_5_unknown_steps']


# =============================================================================
# (b) execution_tier routing appends BARE step IDs (no stray default:verify:module-tests)
# =============================================================================


def test_execution_tier_routing_appends_bare_step_id(plan_context, monkeypatch):
    """An orchestrator-tier verify command appends a BARE ``verify:module-tests`` to
    ``phase_5.verification_steps`` — never a ``default:verify:module-tests`` stray."""
    plan_id = 'tier-bare-id'
    _write_task(
        plan_context.plans_dir,
        plan_id,
        1,
        [
            'python3 .plan/execute-script.py plan-marshall:build-pyproject:pyproject_build run '
            '--command-args "verify plan-marshall"',
        ],
    )
    monkeypatch.setattr(_mem, '_resolve_command_tier', _make_orchestrator_tier_stub())

    result = cmd_compose(_compose_ns(plan_id=plan_id, affected_files_count=3))
    assert result is not None and result['status'] == 'success'

    manifest = read_manifest(plan_id)
    assert manifest is not None
    steps = manifest['phase_5']['verification_steps']
    assert 'verify:module-tests' in steps
    assert 'default:verify:module-tests' not in steps
    # No phase-5 entry carries a default: prefix anywhere.
    assert not any(s.startswith('default:') for s in steps)


def test_routed_bare_id_validates_against_default_prefixed_allowlist(plan_context, monkeypatch):
    """The bare ID appended by execution_tier routing validates cleanly against a
    default:-prefixed allow-list — the (a) and (b) regressions compose.

    This is the end-to-end shape the operator note pins: routing emits the bare
    ``verify:module-tests``, and a subsequent validate with a prefixed allow-list
    must accept it (no stray default:verify:module-tests produced, no spurious
    unknown).
    """
    plan_id = 'tier-bare-validate'
    _write_task(
        plan_context.plans_dir,
        plan_id,
        1,
        [
            'python3 .plan/execute-script.py plan-marshall:build-pyproject:pyproject_build run '
            '--command-args "verify plan-marshall"',
        ],
    )
    monkeypatch.setattr(_mem, '_resolve_command_tier', _make_orchestrator_tier_stub())

    compose_result = cmd_compose(
        _compose_ns(plan_id=plan_id, affected_files_count=3, phase_5_steps='verify:quality-gate')
    )
    assert compose_result is not None and compose_result['status'] == 'success'

    # Allow-list includes the prefixed forms of both the seed step
    # (``verify:quality-gate``) and the routed step (``verify:module-tests``). The
    # routed bare verify:module-tests must validate against
    # default:verify:module-tests.
    result = cmd_validate(
        _validate_ns(
            plan_id=plan_id,
            phase_5_steps='default:verify:quality-gate,default:verify:module-tests',
        )
    )
    assert result is not None and result['status'] == 'success'
    assert result['valid'] is True
    assert result['phase_5_unknown_steps_count'] == 0
