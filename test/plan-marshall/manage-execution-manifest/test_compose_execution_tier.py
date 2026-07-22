#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the compose-time per-step ``execution_tier`` stamping pass.

``_stamp_phase_5_step_execution_tier`` records every FINAL
``phase_5.verification_steps`` entry's ``execution_tier`` (``per_task`` |
``orchestrator``) as a uniform-array record list (``{step_id, tier}`` per step).

**The stamp is ADVISORY, not the routing authority.** The tier derives from
``bash_timeout_seconds``, which ``manage-architecture``'s ``_lookup_bash_timeout``
computes from ``timeout_get(command_key, ...)`` — the adaptive learned build
duration, which every intervening build updates. A step whose learned duration
sits near the 600s Bash ceiling therefore crosses the ceiling between compose and
execute in ordinary operation, so a compose-time snapshot cannot be a durable
routing fact. ``phase-5-execute`` re-resolves the tier LIVE before running each
verification step and routes on that verdict; the stamp serves planning and
observability. ``TestStampReflectsALiveResolvedCeilingVerdict`` below pins that
volatility with the production producers.

The contract properties the stamping guarantees:

1. **Totality** — the record list is total over ``verification_steps``: one
   ``{step_id, tier}`` record per input step, in list order, every record carrying
   a resolved tier.
2. **Default per_task** — a built-in canonical-verify step (``verify:{canonical}``)
   resolves its tier via ``architecture resolve``; every OTHER step id (external
   ``project:`` / ``bundle:skill`` step, or a ``verify:{canonical}`` whose canonical
   is unresolvable) AND every resolve failure defaults to ``per_task``. This is the
   PERMISSIVE default, not a safe floor — ``per_task`` is the value that would put a
   long build inline where the host platform auto-backgrounds it and a leaf cannot
   reap it. It is acceptable only because the leaf re-resolves live before running.
3. **Fidelity at the ceiling** — a resolve that reports ``orchestrator`` is stamped
   ``orchestrator``; the stamping pass never downgrades it to ``per_task``.

The record-list form (rather than a keyed map) is dictated by the TOON storage
format: a step id (``verify:quality-gate``) contains a colon, which does NOT
round-trip as a TOON object key (``parse_toon`` mis-splits on the first colon),
whereas a quoted string value inside a uniform array round-trips exactly. The
round-trip regression test at the bottom of this file guards that design choice.

These tests drive the transform functions directly via importlib (Tier 2),
mirroring ``test_manage_execution_manifest_compose.py``. No live worktree, git history, or
architecture-resolve subprocess is involved: the resolver is monkeypatched, and the
ceiling-boundary tests obtain their resolve envelope from the REAL production
producers (``_classify_build_executable`` / ``_lookup_bash_timeout`` /
``_compute_execution_tier_fields`` in ``manage-architecture``'s
``_cmd_client_build.py``) rather than a hand-authored resolve-shaped dict literal —
a hand-built fixture is what let the four-field contract drift away from its
consumer unnoticed.
"""

import importlib.util
import json
from argparse import Namespace
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
import run_config

from conftest import load_script_module

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

# The PRODUCTION producers of the four-field execution-tier envelope. The
# ceiling-boundary regressions below assert against the fields these emit, so the
# assertions stay coupled to production rather than to a hand-authored literal.
_arch_build = load_script_module(
    'plan-marshall',
    'manage-architecture',
    '_cmd_client_build.py',
    '_arch_client_build_execution_tier',
)

_stamp = _mem._stamp_phase_5_step_execution_tier
_resolve_step_execution_tier = _mem._resolve_step_execution_tier


@pytest.fixture(autouse=True)
def _clear_arch_resolve_cache():
    """Reset the compose-scoped memos before/after each test.

    Two module-level memos live on the once-loaded module instances, so without a
    per-test reset a prior test's cached value would leak into a later test:

    - ``_invoke_architecture_resolve`` is lru-cached (keyed by ``(argv tuple, plan_id)``)
      and the memo lives on ``_mem``; a prior test's cached resolve would leak into a
      later test reusing the same ``(canonical, plan_id)`` key.
    - ``_manifest_validation._domain_appended_canonicals`` is ``@lru_cache(maxsize=1)``
      over ``discover_all_extensions()``; a prior test's cached domain-seeded canonical
      set would leak into a later test that re-mocks the extension discovery.

    ``cmd_compose`` clears BOTH in production; these direct-seam tests clear them here so
    each exercises its own stub.
    """
    _mem._invoke_architecture_resolve_cached.cache_clear()
    _mem._manifest_validation._domain_appended_canonicals.cache_clear()
    yield
    _mem._invoke_architecture_resolve_cached.cache_clear()
    _mem._manifest_validation._domain_appended_canonicals.cache_clear()


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


class TestStampTotalityInvariantLock:
    """Regression lock: the stamp is TOTAL over ``verification_steps``.

    Totality is a property of ONE compose: the stamp is composed over the full
    step list in a single pass, so the persisted record list has no gaps — every
    phase-5 dispatch that reads that manifest sees a resolved tier for every step,
    never an un-stamped entry.

    Totality is NOT a durability claim. It does not assert that the recorded tier
    still describes execute-time reality: the tier derives from the adaptive
    learned build duration, so a ceiling-adjacent step's true tier moves between
    compose and execute (see ``TestStampReflectsALiveResolvedCeilingVerdict`` and
    ``TestStampIsASnapshotNotADurableFact``). What keeps a long build off a leaf
    is the leaf's LIVE re-resolve before running each step, not the completeness of
    this record list. The guarantees locked here, over a list mixing
    canonical-verify steps and an external ``project:`` / ``bundle:skill`` step:

    * exactly one record per input step, in input order (totality + ordering);
    * every record carries a resolved, non-empty tier (``per_task`` |
      ``orchestrator``) — never absent/empty;
    * an orchestrator-tier canonical (``verify:module-tests`` / ``verify:coverage``)
      is stamped ``orchestrator``;
    * an external / unresolvable step defaults to ``per_task``.
    """

    _MIXED_STEPS = [
        'default:verify:quality-gate',
        'verify:module-tests',
        'verify:coverage',
        'project:finalize-step-plugin-doctor',
        'my-bundle:my-verify-step',
    ]

    def test_stamp_is_total_over_mixed_step_list(self, monkeypatch):
        monkeypatch.setattr(_mem, '_resolve_step_execution_tier', _fake_resolver)

        records = _stamp('mixed-plan', self._MIXED_STEPS)

        # Totality + ordering: one record per input step, in list order.
        assert [r['step_id'] for r in records] == self._MIXED_STEPS
        assert len(records) == len(self._MIXED_STEPS)
        # Every record carries a resolved, non-empty tier.
        for rec in records:
            assert set(rec.keys()) == {'step_id', 'tier'}
            assert rec['tier'] in ('per_task', 'orchestrator')
            assert rec['tier']  # non-empty
        # Orchestrator-tier canonicals stamp orchestrator; external/unresolvable
        # steps default to per_task.
        tier_by_id = {r['step_id']: r['tier'] for r in records}
        assert tier_by_id['default:verify:quality-gate'] == 'per_task'
        assert tier_by_id['verify:module-tests'] == 'orchestrator'
        assert tier_by_id['verify:coverage'] == 'orchestrator'
        assert tier_by_id['project:finalize-step-plugin-doctor'] == 'per_task'
        assert tier_by_id['my-bundle:my-verify-step'] == 'per_task'

    def test_stamp_is_dispatch_invariant_composed_once_over_full_list(self, monkeypatch):
        """The stamp is a pure function of (step list, resolver) — re-running it with
        the SAME resolver yields a byte-identical total record list, so nothing in the
        stamping pass itself introduces per-dispatch asymmetry. Purity over a fixed
        resolver is all this pins; when the underlying resolve verdict changes the
        stamp changes with it, which is exactly what
        ``TestStampIsASnapshotNotADurableFact`` asserts."""
        monkeypatch.setattr(_mem, '_resolve_step_execution_tier', _fake_resolver)

        first = _stamp('mixed-plan', self._MIXED_STEPS)
        second = _stamp('mixed-plan', self._MIXED_STEPS)

        assert first == second
        # No step is left without a tier across either read.
        assert all(r['tier'] for r in first)
        assert all(r['tier'] for r in second)


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
    """``_resolve_step_execution_tier`` falls back to per_task on every failure path.

    ``per_task`` is the PERMISSIVE default, NOT a safe floor: it is the value that
    would put a long build inline, where the host platform auto-backgrounds it past
    the Bash ceiling and a dispatched leaf cannot reap it. The fallback is
    acceptable only because the stamp is advisory — ``phase-5-execute`` re-resolves
    the tier live before running each step and routes on that verdict, so a
    permissive compose-time default cannot by itself send a long build inline.

    The assertions below therefore pin the composer's obligation to emit SOME
    resolved tier on every failure path (never an absent or unresolved value), not a
    claim that ``per_task`` is the conservative choice.
    """

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


class TestStampReflectsALiveResolvedCeilingVerdict:
    """The ceiling boundary, driven end-to-end by the PRODUCTION resolve producers.

    The regression this class exists for: a whole-tree step that resolves
    ``orchestrator`` / ``exceeds_bash_ceiling`` MUST NOT be stamped ``per_task`` in a
    form the leaf is instructed to trust inline. Every asserted field is produced by
    ``manage-architecture``'s real ``_classify_build_executable`` /
    ``_lookup_bash_timeout`` / ``_compute_execution_tier_fields``, and the resolve
    TOON the composer parses is serialized from those fields with the production
    ``serialize_toon`` — no hand-authored resolve-shaped dict literal appears
    anywhere in this class, so the four-field contract cannot drift away from its
    consumer without failing here.
    """

    # The literal shape ``architecture resolve --command coverage`` emits for this
    # repo's whole-tree coverage canonical. Fed to the production classifier rather
    # than being decomposed by hand.
    _RESOLVED_EXECUTABLE = (
        'python3 .plan/execute-script.py plan-marshall:build-pyproject:pyproject_build '
        'run --command-args "coverage"'
    )

    # A learned duration far above the ceiling — the seed for the crossing test.
    # Its exact value is never asserted; only which side of the ceiling the
    # production arithmetic lands on.
    _WELL_ABOVE_CEILING_SECONDS = 3600

    @staticmethod
    def _production_tier_fields() -> dict[str, Any]:
        """Run the full production producer chain for the whole-tree coverage canonical."""
        classified = _arch_build._classify_build_executable(
            TestStampReflectsALiveResolvedCeilingVerdict._RESOLVED_EXECUTABLE
        )
        assert classified is not None, 'production classifier rejected a real resolved executable'
        tool_name, command_args = classified
        bash_timeout = _arch_build._lookup_bash_timeout(tool_name, command_args, '.')
        assert isinstance(bash_timeout, int), 'production timeout lookup returned no int'
        fields: dict[str, Any] = _arch_build._compute_execution_tier_fields(bash_timeout)
        return fields

    @staticmethod
    def _resolve_toon_for(fields: dict[str, Any]) -> str:
        """Serialize a status-success resolve TOON carrying the production fields."""
        toon: str = _core.serialize_toon({'status': 'success', **fields})
        return toon

    @staticmethod
    def _patch_resolve_with(monkeypatch, toon: str) -> None:
        monkeypatch.setattr(_mem, '_resolve_executor', lambda: Path('/dev/null'))
        monkeypatch.setattr(
            _mem.subprocess, 'run', lambda *a, **k: SimpleNamespace(returncode=0, stdout=toon)
        )

    def test_production_producers_emit_the_four_field_envelope(self):
        """The producer chain yields exactly the four fields the composer consumes."""
        fields = self._production_tier_fields()

        assert set(fields) == {
            'bash_timeout_seconds',
            'exceeds_bash_ceiling',
            'execution_tier',
            'hint',
        }
        assert isinstance(fields['bash_timeout_seconds'], int)
        assert fields['execution_tier'] in ('per_task', 'orchestrator')
        # The three derived fields agree with each other and with the ceiling.
        expected_exceeds = fields['bash_timeout_seconds'] > _arch_build._BASH_CEILING_SECONDS
        assert fields['exceeds_bash_ceiling'] is expected_exceeds
        assert fields['execution_tier'] == ('orchestrator' if expected_exceeds else 'per_task')

    def test_ceiling_boundary_is_strictly_above(self):
        """At the ceiling → per_task; one second above it → orchestrator.

        Both envelopes come from the production ``_compute_execution_tier_fields``
        and the production ``_BASH_CEILING_SECONDS`` constant, so a threshold change
        moves this assertion with it instead of silently invalidating it.
        """
        ceiling = _arch_build._BASH_CEILING_SECONDS

        at_ceiling = _arch_build._compute_execution_tier_fields(ceiling)
        above_ceiling = _arch_build._compute_execution_tier_fields(ceiling + 1)

        assert at_ceiling['exceeds_bash_ceiling'] is False
        assert at_ceiling['execution_tier'] == 'per_task'
        assert above_ceiling['exceeds_bash_ceiling'] is True
        assert above_ceiling['execution_tier'] == 'orchestrator'

    def test_above_ceiling_resolve_is_never_stamped_per_task(self, monkeypatch):
        """THE regression: an orchestrator-tier resolve stamps orchestrator, never per_task."""
        fields = _arch_build._compute_execution_tier_fields(_arch_build._BASH_CEILING_SECONDS + 1)
        assert fields['execution_tier'] == 'orchestrator'
        self._patch_resolve_with(monkeypatch, self._resolve_toon_for(fields))

        records = _stamp('plan-39-above-ceiling-stamp', ['verify:coverage'])

        assert records == [{'step_id': 'verify:coverage', 'tier': 'orchestrator'}]

    def test_at_ceiling_resolve_stamps_per_task(self, monkeypatch):
        """The other side of the boundary, through the same production envelope."""
        fields = _arch_build._compute_execution_tier_fields(_arch_build._BASH_CEILING_SECONDS)
        assert fields['execution_tier'] == 'per_task'
        self._patch_resolve_with(monkeypatch, self._resolve_toon_for(fields))

        records = _stamp('plan-39-at-ceiling-stamp', ['verify:coverage'])

        assert records == [{'step_id': 'verify:coverage', 'tier': 'per_task'}]

    def test_learned_duration_crossing_the_ceiling_flips_the_resolved_tier(self):
        """The volatility that makes the stamp advisory, pinned against production code.

        Reads the production tier for the whole-tree coverage canonical, records an
        observed duration far above the ceiling through the production
        ``run_config.timeout_set`` writer, and reads the tier again. The verdict
        flips ``per_task`` → ``orchestrator`` with no code change — exactly the
        compose-vs-execute divergence this plan diagnosed. The autouse
        ``_plan_base_dir_sandbox`` fixture redirects the run-config store into a
        per-test tmp sandbox, so the seed never touches the real learned durations
        and the pre-seed read starts from the unmeasured default.
        """
        classified = _arch_build._classify_build_executable(self._RESOLVED_EXECUTABLE)
        assert classified is not None
        tool_name, command_args = classified
        config = _arch_build._load_build_config(tool_name)
        assert config is not None, 'production build config did not load'
        from _build_execute_factory import compute_command_key

        command_key = compute_command_key(config, command_args)

        before = _arch_build._compute_execution_tier_fields(
            _arch_build._lookup_bash_timeout(tool_name, command_args, '.')
        )
        assert before['execution_tier'] == 'per_task', (
            'unmeasured command should start inside the Bash ceiling'
        )

        run_config.timeout_set(command_key, self._WELL_ABOVE_CEILING_SECONDS)

        after = _arch_build._compute_execution_tier_fields(
            _arch_build._lookup_bash_timeout(tool_name, command_args, '.')
        )
        assert after['execution_tier'] == 'orchestrator'
        assert after['bash_timeout_seconds'] > before['bash_timeout_seconds']


class TestRouteUnmappedOrchestratorVerbs:
    """Orchestrator-tier commands with a NON-canonical verb route to ``verify:{verb}``.

    The canonical map (``_VERB_TO_PHASE_5_STEP``) is only the fast path: an
    orchestrator-tier build command whose parseable verb is unmapped generalizes
    to the bare ``verify:{verb}`` step ID and is REMOVED from the task, so no
    leaf ever runs an orchestrator-tier command inline. Only an unparseable
    (raw-shell / non-``plan-marshall:build-``) command survives per-task.
    """

    _CUSTOM_VERB_CMD = (
        'python3 .plan/execute-script.py plan-marshall:build-pyproject:pyproject_build '
        "run --command-args 'perf-suite plan-marshall'"
    )
    _RAW_SHELL_CMD = 'grep -r TODO src/'

    @staticmethod
    def _write_task(tasks_dir: Path, number: int, commands: list) -> Path:
        tasks_dir.mkdir(parents=True, exist_ok=True)
        task_path = tasks_dir / f'TASK-{number:03d}.json'
        task_path.write_text(
            json.dumps({'number': number, 'verification': {'commands': commands}}),
            encoding='utf-8',
        )
        return task_path

    @staticmethod
    def _patch_routing(monkeypatch, tmp_path: Path) -> list[str]:
        """Point the routing pass at ``tmp_path`` with an all-orchestrator classifier."""
        captured: list[str] = []
        monkeypatch.setattr(_mem, 'get_plan_dir', lambda pid: tmp_path)
        monkeypatch.setattr(
            _mem, '_resolve_command_tier', lambda cmd, pid: {'execution_tier': 'orchestrator'}
        )
        monkeypatch.setattr(_mem, '_emit_decision_log', lambda pid, msg: captured.append(msg))
        return captured

    def test_unmapped_verb_routes_to_verify_verb_and_leaves_no_inline_command(
        self, monkeypatch, tmp_path
    ):
        """(i) The custom-verb command lands as ``verify:{verb}`` and is dropped per-task."""
        task_path = self._write_task(tmp_path / 'tasks', 1, [self._CUSTOM_VERB_CMD])
        captured = self._patch_routing(monkeypatch, tmp_path)

        body: dict = {}
        mutated, pending = _mem._route_task_verification_commands('X', body)
        # The routing pass STAGES the task rewrite; persistence is deferred to the
        # caller after the compose-time resolution gate. Commit the staged writes
        # so the on-disk assertion below observes the routed state.
        _mem._persist_task_rewrites(pending)

        assert mutated == 1
        assert body['phase_5']['verification_steps'] == ['verify:perf-suite']
        rewritten = json.loads(task_path.read_text(encoding='utf-8'))
        assert rewritten['verification']['commands'] == []
        # Diagnostic-mute fix: the routed non-canonical verb is named in decision.log.
        assert any("'perf-suite'" in msg and "'verify:perf-suite'" in msg for msg in captured)

    def test_recompose_is_idempotent_appends_nothing(self, monkeypatch, tmp_path):
        """(ii) A second routing pass over the routed state appends and mutates nothing."""
        self._write_task(tmp_path / 'tasks', 1, [self._CUSTOM_VERB_CMD])
        self._patch_routing(monkeypatch, tmp_path)

        body: dict = {}
        first, first_pending = _mem._route_task_verification_commands('X', body)
        assert first == 1
        # Persist between passes to model a real re-compose: the second compose
        # reads the persisted (already-routed) task files from disk.
        _mem._persist_task_rewrites(first_pending)
        second, second_pending = _mem._route_task_verification_commands('X', body)
        assert second == 0
        assert second_pending == []
        assert body['phase_5']['verification_steps'] == ['verify:perf-suite']

    def test_same_verb_across_tasks_dedups_through_seen_steps(self, monkeypatch, tmp_path):
        """Two tasks carrying the same custom verb produce ONE routed step."""
        self._write_task(tmp_path / 'tasks', 1, [self._CUSTOM_VERB_CMD])
        self._write_task(tmp_path / 'tasks', 2, [self._CUSTOM_VERB_CMD])
        self._patch_routing(monkeypatch, tmp_path)

        body: dict = {}
        mutated, pending = _mem._route_task_verification_commands('X', body)

        assert mutated == 2
        assert len(pending) == 2
        assert body['phase_5']['verification_steps'] == ['verify:perf-suite']

    def test_raw_shell_command_stays_per_task_untouched(self, monkeypatch, tmp_path):
        """(iii) An orchestrator-classified raw-shell command (unparseable verb) is kept."""
        task_path = self._write_task(tmp_path / 'tasks', 1, [self._RAW_SHELL_CMD])
        self._patch_routing(monkeypatch, tmp_path)

        body: dict = {}
        mutated, pending = _mem._route_task_verification_commands('X', body)

        assert mutated == 0
        assert pending == []
        assert body['phase_5']['verification_steps'] == []
        unchanged = json.loads(task_path.read_text(encoding='utf-8'))
        assert unchanged['verification']['commands'] == [self._RAW_SHELL_CMD]

    def test_canonical_verb_still_uses_fast_path_map(self, monkeypatch, tmp_path):
        """A canonical verb routes through ``_VERB_TO_PHASE_5_STEP``, not the generalization."""
        cmd = (
            'python3 .plan/execute-script.py plan-marshall:build-pyproject:pyproject_build '
            "run --command-args 'module-tests plan-marshall'"
        )
        self._write_task(tmp_path / 'tasks', 1, [cmd])
        captured = self._patch_routing(monkeypatch, tmp_path)

        body: dict = {}
        mutated, pending = _mem._route_task_verification_commands('X', body)

        assert mutated == 1
        assert len(pending) == 1
        assert body['phase_5']['verification_steps'] == ['verify:module-tests']
        # The canonical fast path emits NO per-verb non-canonical routing line.
        assert not any('non-canonical' in msg for msg in captured)


class TestValidateAcceptsRoutedGeneralizedStep:
    """(iv) ``validate`` passes when the allow-list includes the routed ``verify:{verb}`` ID."""

    def test_validate_passes_with_routed_id_in_allow_list(self, plan_context):
        plan_id = 'route-validate-allow'
        body = {
            'manifest_version': _core.MANIFEST_VERSION,
            'plan_id': plan_id,
            'phase_5': {'early_terminate': False, 'verification_steps': ['verify:perf-suite']},
            'phase_6': {'steps': []},
        }
        _mem.write_manifest(plan_id, body)

        result = _mem.cmd_validate(
            Namespace(
                plan_id=plan_id,
                phase_5_steps='default:verify:perf-suite',
                phase_6_steps=None,
            )
        )

        assert result is not None
        assert result['status'] == 'success'
        assert result['valid'] is True
        assert result['phase_5_unknown_steps_count'] == 0


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


class TestInvokeArchitectureResolveCaching:
    """``_invoke_architecture_resolve`` memoizes per ``(argv_extra, plan_id)`` within one compose.

    The same ``default:verify:arch-gate`` canonical is probed twice in one compose —
    once by ``_apply_domain_seeded_step_resolvability`` and again by
    ``_resolve_step_execution_tier`` when the step survives — so a repeated identical
    resolve must reuse the first result instead of re-spawning the subprocess. Distinct
    keys still each spawn their own subprocess.
    """

    _SUCCESS_TOON = 'status: success\nexecution_tier: per_task\n'

    @staticmethod
    def _patch_counting_run(monkeypatch) -> list[list[str]]:
        calls: list[list[str]] = []

        def _counting_run(argv, *a, **k):
            calls.append(argv)
            return SimpleNamespace(
                returncode=0,
                stdout=TestInvokeArchitectureResolveCaching._SUCCESS_TOON,
            )

        monkeypatch.setattr(_mem, '_resolve_executor', lambda: Path('/dev/null'))
        monkeypatch.setattr(_mem.subprocess, 'run', _counting_run)
        return calls

    def test_repeated_identical_resolve_spawns_subprocess_once(self, monkeypatch):
        calls = self._patch_counting_run(monkeypatch)

        first = _mem._invoke_architecture_resolve(['--command', 'arch-gate'], 'PLAN')
        second = _mem._invoke_architecture_resolve(['--command', 'arch-gate'], 'PLAN')

        assert first == second == {'status': 'success', 'execution_tier': 'per_task'}
        # The second identical resolve is served from the memo — no re-spawn.
        assert len(calls) == 1

    def test_distinct_keys_each_spawn_subprocess(self, monkeypatch):
        calls = self._patch_counting_run(monkeypatch)

        _mem._invoke_architecture_resolve(['--command', 'arch-gate'], 'PLAN')
        _mem._invoke_architecture_resolve(['--command', 'quality-gate'], 'PLAN')
        _mem._invoke_architecture_resolve(['--command', 'arch-gate'], 'OTHER')

        # Distinct canonical or distinct plan_id → distinct cache key → distinct spawn.
        assert len(calls) == 3

    def test_cache_clear_forces_re_resolution(self, monkeypatch):
        calls = self._patch_counting_run(monkeypatch)

        _mem._invoke_architecture_resolve(['--command', 'arch-gate'], 'PLAN')
        _mem._invoke_architecture_resolve_cached.cache_clear()
        _mem._invoke_architecture_resolve(['--command', 'arch-gate'], 'PLAN')

        # cache_clear (as cmd_compose runs per compose) drops the memo → a re-spawn.
        assert len(calls) == 2


class TestCmdComposeClearsDomainAppendedCanonicalsMemo:
    """``cmd_compose`` clears the domain-appended-canonicals ``@lru_cache(maxsize=1)`` at entry.

    ``_manifest_validation._domain_appended_canonicals`` memoizes over
    ``discover_all_extensions()``. In a long-lived process (the marshalld build
    daemon) ``cmd_compose`` runs repeatedly; if the active domains/extensions change
    between composes, a stale memo would keep the wrong domain-seeded canonical set
    and mis-filter D5 domain-seeded verify steps. ``cmd_compose`` must therefore clear
    that memo at entry, alongside the architecture-resolve memo.
    """

    def test_cmd_compose_clears_domain_canonicals_memo_at_entry(self, monkeypatch):
        """The domain memo's ``cache_clear`` fires at ``cmd_compose`` entry.

        An invalid ``change_type`` short-circuits ``cmd_compose`` immediately after the
        two entry-time cache clears, so the assertion needs no plan / marshal.json
        fixture — it observes only the entry-time clear via a spy standing in for the
        memo on the ``_manifest_validation`` module.
        """
        cleared: list[str] = []
        spy = SimpleNamespace(cache_clear=lambda: cleared.append('cleared'))
        monkeypatch.setattr(_mem._manifest_validation, '_domain_appended_canonicals', spy)

        result = _mem.cmd_compose(
            Namespace(
                plan_id='domain-canon-clear',
                change_type='__not_a_valid_change_type__',
                scope_estimate='surgical',
                track='simple',
                commit_and_push=None,
            )
        )

        # Short-circuited on the invalid change_type — but only AFTER the entry-time
        # clear fired.
        assert result is not None
        assert result['error'] == 'invalid_change_type'
        assert cleared == ['cleared']
