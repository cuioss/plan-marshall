#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Regression tests for the domain-seeded verify-step resolvability filter.

Covers the arch-gate seed/resolve mismatch fix: ``skill-domains configure`` seeds
``default:verify:arch-gate`` for any project whose configured domains declare a
``provides_arch_gate()`` tool (the availability axis), but whether the plan's own
footprint wires an in-scope module that resolves the ``arch-gate`` command is a
per-plan/per-footprint property. The compose-layer filter
(``_apply_domain_seeded_step_resolvability``) drops the seeded step with a
diagnosable ``[STATUS]`` warning when the command is unresolvable, and keeps it
when a module wires it — the ADR-010 status-bearing-gate visibility semantic (a
diagnosable skip, never a silent drop and never a hard compose block).

Both the ``architecture resolve`` seam (``_invoke_architecture_resolve``) and the
domain-appended-canonical set (``_manifest_validation._domain_appended_canonicals``,
which marks ``arch-gate`` as a legitimate domain canonical so it is not confused
with a typo'd/unknown canonical the resolution gate hard-fails) are patched, so
the assertions do not depend on real domain wiring.
"""

import contextlib
import importlib.util
from argparse import Namespace
from pathlib import Path

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


_mem = _load_module('_mem_domain_seeded', 'manage-execution-manifest.py')
cmd_compose = _mem.cmd_compose
read_manifest = _mem.read_manifest

# Silence the best-effort decision-log subprocess (mirrors the compose test file).
_mem._log_decision = lambda *a, **kw: None


@contextlib.contextmanager
def _capture_decision_log():
    """Capture ``_emit_decision_log`` calls; yield the (plan_id, message) list."""
    captured: list[tuple[str, str]] = []
    original = _mem._emit_decision_log
    _mem._emit_decision_log = lambda pid, msg: captured.append((pid, msg))
    try:
        yield captured
    finally:
        _mem._emit_decision_log = original


def _compose_ns(
    plan_id: str,
    phase_5_steps: str,
    change_type: str = 'feature',
    track: str = 'complex',
    scope_estimate: str = 'multi_module',
    affected_files_count: int = 5,
) -> Namespace:
    return Namespace(
        plan_id=plan_id,
        change_type=change_type,
        track=track,
        scope_estimate=scope_estimate,
        recipe_key=None,
        affected_files_count=affected_files_count,
        phase_5_steps=phase_5_steps,
        phase_6_steps=None,
        commit_and_push=None,
    )


def _make_resolve_stub(resolvable_canonicals: set[str]):
    """Stub ``_invoke_architecture_resolve``: resolve iff the ``--command`` verb is listed.

    Returns a status-success resolve TOON (per_task tier) for a canonical in
    ``resolvable_canonicals`` and ``None`` (unresolvable) otherwise, exactly as the
    real seam returns ``None`` on a ``Command not found`` resolve error.
    """

    def stub(argv_extra: list[str], plan_id: str):
        canonical = argv_extra[1] if len(argv_extra) >= 2 and argv_extra[0] == '--command' else None
        if canonical in resolvable_canonicals:
            return {
                'status': 'success',
                'execution_tier': 'per_task',
                'bash_timeout_seconds': 150,
            }
        return None

    return stub


def test_domain_active_but_no_arch_gate_command_drops_step_with_warning(plan_context, monkeypatch):
    """java domain active, but no in-scope module wires arch-gate → step DROPPED + warning.

    ``default:verify:arch-gate`` is seeded and ``arch-gate`` is a recognized
    domain-appended canonical, but ``architecture resolve --command arch-gate`` is
    unresolvable for the whole footprint. The compose-layer filter drops the step,
    emits a diagnosable ``[STATUS]`` warning naming it, and compose SUCCEEDS (never
    a hard block).
    """
    plan_id = 'domain-seeded-arch-gate-unresolvable'
    monkeypatch.setattr(
        _mem._manifest_validation, '_domain_appended_canonicals', lambda: {'arch-gate'}
    )
    # quality-gate resolves (a real gate); arch-gate does NOT (no module wires it).
    monkeypatch.setattr(
        _mem, '_invoke_architecture_resolve', _make_resolve_stub({'quality-gate', 'module-tests'})
    )

    with _capture_decision_log() as captured:
        result = cmd_compose(
            _compose_ns(
                plan_id=plan_id,
                phase_5_steps='default:verify:quality-gate,default:verify:arch-gate',
            )
        )

    # Compose succeeds — a diagnosable skip, not a hard compose block.
    assert result is not None and result['status'] == 'success'

    manifest = read_manifest(plan_id)
    assert manifest is not None
    steps = manifest['phase_5']['verification_steps']
    # The unresolvable domain-seeded step is dropped; the resolvable core gate stays.
    assert 'verify:arch-gate' not in steps
    assert 'verify:quality-gate' in steps

    # A diagnosable [STATUS] warning named the dropped step and the reason.
    messages = [msg for _pid, msg in captured]
    assert any(
        '[STATUS]' in msg
        and 'domain_seeded_step_unresolvable' in msg
        and 'verify:arch-gate' in msg
        for msg in messages
    ), messages


def test_module_that_wires_arch_gate_keeps_step(plan_context, monkeypatch):
    """java domain active AND an in-scope module wires arch-gate → step KEPT.

    The same ``default:verify:arch-gate`` seed, but ``architecture resolve --command
    arch-gate`` resolves for the footprint, so the filter keeps the step. Because
    ``arch-gate`` is a recognized domain-appended canonical it is also in the
    verify-canonicals universe, so the KEPT step passes the compose-time resolution
    gate and compose succeeds with the step present.
    """
    plan_id = 'domain-seeded-arch-gate-resolvable'
    monkeypatch.setattr(
        _mem._manifest_validation, '_domain_appended_canonicals', lambda: {'arch-gate'}
    )
    # arch-gate resolves this time (a module wires the command).
    monkeypatch.setattr(
        _mem,
        '_invoke_architecture_resolve',
        _make_resolve_stub({'quality-gate', 'module-tests', 'arch-gate'}),
    )

    with _capture_decision_log() as captured:
        result = cmd_compose(
            _compose_ns(
                plan_id=plan_id,
                phase_5_steps='default:verify:quality-gate,default:verify:arch-gate',
            )
        )

    assert result is not None and result['status'] == 'success'

    manifest = read_manifest(plan_id)
    assert manifest is not None
    steps = manifest['phase_5']['verification_steps']
    # The resolvable domain-seeded step is kept.
    assert 'verify:arch-gate' in steps
    assert 'verify:quality-gate' in steps

    # No drop warning was emitted for the kept step.
    messages = [msg for _pid, msg in captured]
    assert not any(
        'domain_seeded_step_unresolvable' in msg and 'verify:arch-gate' in msg for msg in messages
    ), messages
