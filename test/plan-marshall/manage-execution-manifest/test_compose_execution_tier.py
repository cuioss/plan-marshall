#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the compose-time per-step ``execution_tier`` stamping pass.

``_stamp_phase_5_step_execution_tier`` resolves every FINAL
``phase_5.verification_steps`` entry to a deterministic ``execution_tier``
(``per_task`` | ``orchestrator``) and records it as a uniform-array record list
(``{step_id, tier}`` per step). This is the compose-time structural enforcement of
the leaf-no-background-build invariant — a leaf runs only ``per_task``-tier
verification steps inline; ``orchestrator``-tier steps are yielded to the
main-context orchestrator's ``await-long-running`` seam.

The two contract properties the stamping guarantees:

1. **Totality** — the record list is total over ``verification_steps``: one
   ``{step_id, tier}`` record per input step, in list order, every record carrying
   a resolved tier.
2. **Default per_task** — a built-in canonical-verify step (``verify:{canonical}``)
   resolves its tier via ``architecture resolve``; every OTHER step id (external
   ``project:`` / ``bundle:skill`` step, or a ``verify:{canonical}`` whose canonical
   is unresolvable) AND every resolve failure defaults to ``per_task`` — the
   composer never emits an unresolved tier.

The record-list form (rather than a keyed map) is dictated by the TOON storage
format: a step id (``verify:quality-gate``) contains a colon, which does NOT
round-trip as a TOON object key (``parse_toon`` mis-splits on the first colon),
whereas a quoted string value inside a uniform array round-trips exactly. The
round-trip regression test at the bottom of this file guards that design choice.

These tests drive the transform functions directly via importlib (Tier 2),
mirroring ``test_aspect_step_dropping.py``. No live worktree, git history, or
architecture-resolve subprocess is involved — the resolver is monkeypatched so the
tests assert the pure stamping logic and the fail-safe defaults.
"""

import importlib.util
from pathlib import Path
from types import SimpleNamespace

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


_mem = _load_module('_mem_execution_tier', 'manage-execution-manifest.py')
_core = _load_module('_core_execution_tier', '_manifest_core.py')

_stamp = _mem._stamp_phase_5_step_execution_tier
_resolve_step_execution_tier = _mem._resolve_step_execution_tier


# A fake resolver keyed by canonical — a ceiling-exceeding module verify /
# coverage resolves orchestrator; the fast quality-gate resolves per_task.
_FAKE_TIER_BY_CANONICAL = {
    'quality-gate': 'per_task',
    'module-tests': 'orchestrator',
    'coverage': 'orchestrator',
    'verify': 'orchestrator',
}


def _fake_resolver(canonical: str, plan_id: str) -> str:
    return _FAKE_TIER_BY_CANONICAL.get(canonical, 'per_task')


class TestStampTotalityAndOrdering:
    """The record list is total over ``verification_steps`` and preserves order."""

    def test_one_record_per_step_in_order(self, monkeypatch):
        monkeypatch.setattr(_mem, '_resolve_step_execution_tier', _fake_resolver)
        steps = ['verify:quality-gate', 'verify:module-tests', 'verify:coverage']
        records = _stamp('X', steps)
        assert [r['step_id'] for r in records] == steps
        assert len(records) == len(steps)

    def test_every_record_has_step_id_and_tier(self, monkeypatch):
        monkeypatch.setattr(_mem, '_resolve_step_execution_tier', _fake_resolver)
        records = _stamp('X', ['verify:quality-gate', 'verify:module-tests'])
        for rec in records:
            assert set(rec.keys()) == {'step_id', 'tier'}
            assert rec['tier'] in ('per_task', 'orchestrator')

    def test_empty_verification_steps_yields_empty_list(self, monkeypatch):
        monkeypatch.setattr(_mem, '_resolve_step_execution_tier', _fake_resolver)
        assert _stamp('X', []) == []


class TestOrchestratorTierForCeilingExceedingVerify:
    """A ceiling-exceeding module verify stamps orchestrator; quality-gate stamps per_task."""

    def test_module_verify_is_orchestrator_tier(self, monkeypatch):
        monkeypatch.setattr(_mem, '_resolve_step_execution_tier', _fake_resolver)
        records = _stamp('X', ['verify:module-tests', 'verify:coverage'])
        tier_by_id = {r['step_id']: r['tier'] for r in records}
        assert tier_by_id['verify:module-tests'] == 'orchestrator'
        assert tier_by_id['verify:coverage'] == 'orchestrator'

    def test_quality_gate_is_per_task_tier(self, monkeypatch):
        monkeypatch.setattr(_mem, '_resolve_step_execution_tier', _fake_resolver)
        records = _stamp('X', ['verify:quality-gate'])
        assert records == [{'step_id': 'verify:quality-gate', 'tier': 'per_task'}]

    def test_mixed_tiers_stamped_per_step(self, monkeypatch):
        monkeypatch.setattr(_mem, '_resolve_step_execution_tier', _fake_resolver)
        steps = ['verify:quality-gate', 'verify:module-tests', 'verify:coverage']
        records = _stamp('X', steps)
        assert records == [
            {'step_id': 'verify:quality-gate', 'tier': 'per_task'},
            {'step_id': 'verify:module-tests', 'tier': 'orchestrator'},
            {'step_id': 'verify:coverage', 'tier': 'orchestrator'},
        ]

    def test_default_prefixed_canonical_resolves_via_canonical(self, monkeypatch):
        """A ``default:verify:{canonical}`` id is bare-normalized before the canonical lookup."""
        monkeypatch.setattr(_mem, '_resolve_step_execution_tier', _fake_resolver)
        records = _stamp('X', ['default:verify:module-tests'])
        assert records == [{'step_id': 'default:verify:module-tests', 'tier': 'orchestrator'}]


class TestNonCanonicalStepsDefaultPerTask:
    """External / non-canonical steps default to per_task WITHOUT invoking the resolver."""

    def test_external_project_step_defaults_per_task(self, monkeypatch):
        called: list[str] = []

        def _spy(canonical: str, plan_id: str) -> str:
            called.append(canonical)
            return 'orchestrator'

        monkeypatch.setattr(_mem, '_resolve_step_execution_tier', _spy)
        records = _stamp('X', ['project:finalize-step-plugin-doctor', 'my-bundle:my-verify-step'])
        assert records == [
            {'step_id': 'project:finalize-step-plugin-doctor', 'tier': 'per_task'},
            {'step_id': 'my-bundle:my-verify-step', 'tier': 'per_task'},
        ]
        # The resolver is a whole-tree canonical resolver — it must NOT be invoked
        # for non-canonical step ids.
        assert called == []

    def test_mixed_canonical_and_external_steps(self, monkeypatch):
        monkeypatch.setattr(_mem, '_resolve_step_execution_tier', _fake_resolver)
        steps = ['verify:module-tests', 'project:finalize-step-plugin-doctor']
        records = _stamp('X', steps)
        assert records == [
            {'step_id': 'verify:module-tests', 'tier': 'orchestrator'},
            {'step_id': 'project:finalize-step-plugin-doctor', 'tier': 'per_task'},
        ]


class TestResolveStepExecutionTierDefaultsPerTask:
    """``_resolve_step_execution_tier`` fails safe to per_task on every failure path."""

    def test_unresolvable_executor_defaults_per_task(self, monkeypatch):
        monkeypatch.setattr(_mem, '_resolve_executor', lambda: None)
        assert _resolve_step_execution_tier('module-tests', 'X') == 'per_task'

    def test_nonzero_exit_defaults_per_task(self, monkeypatch):
        monkeypatch.setattr(_mem, '_resolve_executor', lambda: Path('/dev/null'))
        monkeypatch.setattr(
            _mem.subprocess, 'run', lambda *a, **k: SimpleNamespace(returncode=1, stdout='')
        )
        assert _resolve_step_execution_tier('module-tests', 'X') == 'per_task'

    def test_subprocess_error_defaults_per_task(self, monkeypatch):
        monkeypatch.setattr(_mem, '_resolve_executor', lambda: Path('/dev/null'))

        def _boom(*a, **k):
            raise OSError('boom')

        monkeypatch.setattr(_mem.subprocess, 'run', _boom)
        assert _resolve_step_execution_tier('module-tests', 'X') == 'per_task'

    def test_non_success_status_defaults_per_task(self, monkeypatch):
        monkeypatch.setattr(_mem, '_resolve_executor', lambda: Path('/dev/null'))
        toon = 'status: error\nexecution_tier: orchestrator\n'
        monkeypatch.setattr(
            _mem.subprocess, 'run', lambda *a, **k: SimpleNamespace(returncode=0, stdout=toon)
        )
        assert _resolve_step_execution_tier('module-tests', 'X') == 'per_task'

    def test_unknown_tier_value_defaults_per_task(self, monkeypatch):
        monkeypatch.setattr(_mem, '_resolve_executor', lambda: Path('/dev/null'))
        toon = 'status: success\nexecution_tier: something-else\n'
        monkeypatch.setattr(
            _mem.subprocess, 'run', lambda *a, **k: SimpleNamespace(returncode=0, stdout=toon)
        )
        assert _resolve_step_execution_tier('module-tests', 'X') == 'per_task'

    def test_absent_tier_field_defaults_per_task(self, monkeypatch):
        monkeypatch.setattr(_mem, '_resolve_executor', lambda: Path('/dev/null'))
        toon = 'status: success\nmodule: default\n'
        monkeypatch.setattr(
            _mem.subprocess, 'run', lambda *a, **k: SimpleNamespace(returncode=0, stdout=toon)
        )
        assert _resolve_step_execution_tier('quality-gate', 'X') == 'per_task'

    def test_orchestrator_tier_is_read_from_resolve_toon(self, monkeypatch):
        monkeypatch.setattr(_mem, '_resolve_executor', lambda: Path('/dev/null'))
        toon = 'status: success\nexecution_tier: orchestrator\nbash_timeout_seconds: 2065\n'
        monkeypatch.setattr(
            _mem.subprocess, 'run', lambda *a, **k: SimpleNamespace(returncode=0, stdout=toon)
        )
        assert _resolve_step_execution_tier('verify', 'X') == 'orchestrator'

    def test_per_task_tier_is_read_from_resolve_toon(self, monkeypatch):
        monkeypatch.setattr(_mem, '_resolve_executor', lambda: Path('/dev/null'))
        toon = 'status: success\nexecution_tier: per_task\nbash_timeout_seconds: 150\n'
        monkeypatch.setattr(
            _mem.subprocess, 'run', lambda *a, **k: SimpleNamespace(returncode=0, stdout=toon)
        )
        assert _resolve_step_execution_tier('quality-gate', 'X') == 'per_task'


class TestStepExecutionTierToonRoundTrip:
    """The record-list form round-trips through TOON exactly (colon-key design guard)."""

    def test_record_list_round_trips_through_toon(self):
        """A colon-bearing step id survives serialize→parse as a QUOTED value inside a
        uniform array. This is the load-bearing reason the stamp is a record list and
        NOT a TOON object map keyed by step id (a colon-bearing object KEY mis-splits
        on ``parse_toon``)."""
        body = {
            'phase_5': {
                'step_execution_tier': [
                    {'step_id': 'verify:quality-gate', 'tier': 'per_task'},
                    {'step_id': 'verify:module-tests', 'tier': 'orchestrator'},
                    {'step_id': 'verify:coverage', 'tier': 'orchestrator'},
                ],
            },
        }
        serialized = _core.serialize_toon(body)
        parsed = _core.parse_toon(serialized)
        assert parsed['phase_5']['step_execution_tier'] == body['phase_5']['step_execution_tier']
