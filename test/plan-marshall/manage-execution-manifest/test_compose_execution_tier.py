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
import json
from argparse import Namespace
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
