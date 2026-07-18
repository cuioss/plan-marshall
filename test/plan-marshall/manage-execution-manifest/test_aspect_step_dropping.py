#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the request-aspect step-dropping pre-filter.

``_apply_aspect_step_dropping`` clears the ENTIRE composed phase-5 verification
list when the request aspect (resolved by the ``manage-config aspect-classify``
verb) is ``analysis`` or ``planning``. The composer resolves that aspect by
precedence: an explicit ``--aspect`` argument wins, and when it is absent the
composer self-reads ``status.metadata.request_aspect`` via
``_read_request_aspect(plan_id)`` (mirroring the ``recipe_key`` /
``_read_recipe_source`` precedent). The rationale is the inverse of the footprint
pre-filter: an analysis / planning request carries no production / test footprint
to gate, so running (and failing) build / quality-gate / test commands against a
code-free change is pure waste.

The full-clear (rather than a role-only drop of the build/verify canonicals) is
load-bearing for the phase-5-execute Step 11b contract: Step 11b fires a
``quality-gate`` sweep whenever ``phase_5.verification_steps`` is non-empty. A
role-only filter that left any external (``project:`` / ``bundle:skill``)
``None``-role step in the list would keep it non-empty and re-trigger
``quality-gate`` via Step 11b for an analysis / planning request — exactly the
build the aspect drop exists to prevent. Clearing the full list keeps the
enforcement at the manifest layer where it belongs.

An ``implementation`` aspect (the classifier's safe sub-threshold fallback) is a
no-op: every step is retained. An absent ``--aspect`` argument is a no-op only
when the persisted ``status.metadata.request_aspect`` is also unset or
``implementation`` — otherwise the self-read fallback drives the drop.

The ``_apply_aspect_step_dropping`` cases here drive the function directly via
importlib (Tier 2), mirroring ``test_canonical_verify_inactive.py`` — that pure
transform needs no live worktree. The file additionally covers the D1 self-read
wiring: ``TestReadRequestAspect`` exercises ``_read_request_aspect`` against a
real ``status.json`` (present / absent / corrupt), and
``TestComposeSelfReadsRequestAspect`` drives the real ``cmd_compose`` to prove an
absent ``--aspect`` argument still drops the build gates when
``status.metadata.request_aspect`` is ``analysis`` / ``planning``.
"""

import importlib.util
import json
from argparse import Namespace
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


_mem = _load_module('_mem_aspect_step_dropping', 'manage-execution-manifest.py')
_dec = _load_module('_dec_aspect_step_dropping', '_manifest_decide.py')
_apply_aspect_step_dropping = _mem._apply_aspect_step_dropping
_BUILD_DROPPING_ASPECTS = _mem._BUILD_DROPPING_ASPECTS
_read_request_aspect = _dec._read_request_aspect


# The full build/verify step set an implementation request retains and an
# analysis/planning request drops — one canonical per build-dropping role.
_BUILD_STEPS = [
    'default:verify:quality-gate',
    'default:verify:module-tests',
    'default:verify:coverage',
]


class TestConstants:
    """The membership tables encode the documented contract."""

    def test_build_dropping_aspects_are_analysis_and_planning(self):
        assert _BUILD_DROPPING_ASPECTS == frozenset({'analysis', 'planning'})

    def test_implementation_is_not_a_build_dropping_aspect(self):
        assert 'implementation' not in _BUILD_DROPPING_ASPECTS


class TestAnalysisPlanningClearsEntireList:
    """An analysis / planning aspect clears the ENTIRE phase-5 verification list."""

    def test_analysis_drops_all_build_steps(self):
        kept, dropped = _apply_aspect_step_dropping(list(_BUILD_STEPS), 'analysis', {})
        assert kept == []
        assert dropped == _BUILD_STEPS

    def test_planning_drops_all_build_steps(self):
        kept, dropped = _apply_aspect_step_dropping(list(_BUILD_STEPS), 'planning', {})
        assert kept == []
        assert dropped == _BUILD_STEPS

    def test_bare_canonical_verify_form_is_also_dropped(self):
        """The bare ``verify:{canonical}`` form is dropped identically to the prefixed form."""
        steps = ['verify:quality-gate', 'verify:module-tests']
        kept, dropped = _apply_aspect_step_dropping(steps, 'analysis', {})
        assert kept == []
        assert dropped == steps

    def test_verify_canonical_is_dropped(self):
        """``default:verify:verify`` (the ``module-tests`` role) is dropped."""
        kept, dropped = _apply_aspect_step_dropping(['default:verify:verify'], 'planning', {})
        assert kept == []
        assert dropped == ['default:verify:verify']

    def test_external_none_role_step_does_not_survive_role_drop(self):
        """REGRESSION (CodeRabbit 10709d): an external (project:/bundle:skill) step
        whose derived role is ``None`` must ALSO drop under analysis/planning. A
        role-only filter would leave it in place, keeping the list non-empty and
        re-triggering quality-gate via phase-5 Step 11b. The full-clear path
        ensures the list ends empty even when the only surviving candidate is an
        external None-role step."""
        # The list contains ONLY external/unknown None-role steps — no build/verify
        # canonical to drop via the old role filter. The list must still end empty.
        steps = [
            'project:finalize-step-plugin-doctor',
            'my-bundle:my-verify-step',
            'default:verify:not-a-canonical',
        ]
        kept, dropped = _apply_aspect_step_dropping(steps, 'analysis', {})
        assert kept == []
        assert dropped == steps

    def test_mixed_build_and_external_steps_all_drop_under_analysis(self):
        """A mix of build/verify canonicals, footprint-gated whole-tree canonicals,
        and external None-role steps ALL drop under an analysis aspect — the list
        ends empty regardless of step kind."""
        steps = [
            'default:verify:quality-gate',
            'project:finalize-step-plugin-doctor',
            'my-bundle:my-verify-step',
            'default:verify:not-a-canonical',
            'default:verify:integration-tests',
            'default:verify:e2e',
        ]
        kept, dropped = _apply_aspect_step_dropping(steps, 'analysis', {})
        assert kept == []
        assert dropped == steps

    def test_mixed_steps_all_drop_under_planning(self):
        """Symmetric coverage for the ``planning`` aspect over a mixed list."""
        steps = [
            'default:verify:module-tests',
            'project:finalize-step-plugin-doctor',
            'default:verify:coverage',
        ]
        kept, dropped = _apply_aspect_step_dropping(steps, 'planning', {})
        assert kept == []
        assert dropped == steps


class TestImplementationRetainsAllSteps:
    """An implementation aspect (or absent aspect) retains every step."""

    def test_implementation_retains_all_build_steps(self):
        kept, dropped = _apply_aspect_step_dropping(list(_BUILD_STEPS), 'implementation', {})
        assert kept == _BUILD_STEPS
        assert dropped == []

    def test_implementation_retains_external_none_role_steps(self):
        """An implementation aspect retains external None-role steps untouched —
        the full-clear path is gated strictly on the build-dropping aspects."""
        steps = [
            'default:verify:quality-gate',
            'project:finalize-step-plugin-doctor',
            'my-bundle:my-verify-step',
        ]
        kept, dropped = _apply_aspect_step_dropping(steps, 'implementation', {})
        assert kept == steps
        assert dropped == []

    def test_none_aspect_is_a_noop(self):
        """An absent aspect (``--aspect`` omitted) retains every step."""
        kept, dropped = _apply_aspect_step_dropping(list(_BUILD_STEPS), None, {})
        assert kept == _BUILD_STEPS
        assert dropped == []

    def test_unrecognized_aspect_is_a_noop(self):
        """An aspect value outside the build-dropping set retains every step."""
        kept, dropped = _apply_aspect_step_dropping(list(_BUILD_STEPS), 'unknown-aspect', {})
        assert kept == _BUILD_STEPS
        assert dropped == []

    def test_empty_step_list_is_a_noop_for_every_aspect(self):
        for aspect in ('analysis', 'planning', 'implementation', None):
            kept, dropped = _apply_aspect_step_dropping([], aspect, {})
            assert kept == []
            assert dropped == []


class TestReadRequestAspect:
    """Direct unit coverage for the ``_read_request_aspect`` status-metadata self-read.

    The helper resolves ``status.metadata.request_aspect`` directly so the composer
    no longer depends on the ``phase-4-plan`` agent forwarding ``--aspect``. It
    mirrors ``_read_recipe_source``'s corruption-guard shape exactly: an absent
    ``status.json`` yields ``None``, a corrupt-but-present file degrades to ``None``
    (rather than crashing compose), and a present value is returned trimmed.
    """

    @staticmethod
    def _write_status(plan_context, plan_id, metadata):
        plan_dir = plan_context.plan_dir_for(plan_id)
        (plan_dir / _dec.FILE_STATUS).write_text(
            json.dumps({'metadata': metadata}), encoding='utf-8'
        )

    def test_reads_persisted_request_aspect(self, plan_context):
        self._write_status(plan_context, 'aspect-present', {'request_aspect': 'analysis'})
        assert _read_request_aspect('aspect-present') == 'analysis'

    def test_trims_surrounding_whitespace(self, plan_context):
        self._write_status(plan_context, 'aspect-trim', {'request_aspect': '  planning  '})
        assert _read_request_aspect('aspect-trim') == 'planning'

    def test_absent_status_file_is_none(self, plan_context):
        # Plan dir exists but no status.json is written — read_json's default path.
        plan_context.plan_dir_for('aspect-absent')
        assert _read_request_aspect('aspect-absent') is None

    def test_missing_request_aspect_key_is_none(self, plan_context):
        self._write_status(plan_context, 'aspect-nokey', {'plan_source': 'recipe'})
        assert _read_request_aspect('aspect-nokey') is None

    def test_empty_request_aspect_is_none(self, plan_context):
        self._write_status(plan_context, 'aspect-empty', {'request_aspect': '   '})
        assert _read_request_aspect('aspect-empty') is None

    def test_corrupt_status_file_degrades_to_none(self, plan_context):
        plan_dir = plan_context.plan_dir_for('aspect-corrupt')
        (plan_dir / _dec.FILE_STATUS).write_text('{ not valid json', encoding='utf-8')
        assert _read_request_aspect('aspect-corrupt') is None

    def test_non_dict_metadata_is_none(self, plan_context):
        plan_dir = plan_context.plan_dir_for('aspect-badmeta')
        (plan_dir / _dec.FILE_STATUS).write_text(
            json.dumps({'metadata': 'not-a-dict'}), encoding='utf-8'
        )
        assert _read_request_aspect('aspect-badmeta') is None


class TestComposeSelfReadsRequestAspect:
    """``cmd_compose`` falls back to persisted ``status.metadata.request_aspect``
    when no ``--aspect`` argument is supplied — the consumer self-read wiring.

    These tests drive the REAL ``cmd_compose`` so the ``aspect = getattr(args,
    'aspect', None) or _read_request_aspect(plan_id)`` seam and the real
    ``_apply_aspect_step_dropping`` transform both execute. Every collaborator that
    would spawn a subprocess, read git, or hit the discovery registry is stubbed so
    the assertion isolates the aspect-resolution wiring, mirroring the
    monkeypatched-resolver style of ``test_compose_execution_tier.py``.
    """

    _FULL_GATES = ['verify:quality-gate', 'verify:module-tests', 'verify:coverage']

    @staticmethod
    def _neutralize_external_collaborators(monkeypatch, captured):
        monkeypatch.setattr(_mem, '_route_task_verification_commands', lambda pid, body: (0, []))
        monkeypatch.setattr(
            _mem, '_apply_canonical_verify_inactive', lambda steps, pid, cache: (list(steps), [])
        )
        monkeypatch.setattr(
            _mem,
            '_stamp_phase_5_step_execution_tier',
            lambda pid, steps: [{'step_id': s, 'tier': 'per_task'} for s in steps],
        )
        monkeypatch.setattr(_mem, 'check_emitted_steps_resolvable', lambda a, b, c, d: None)
        monkeypatch.setattr(
            _mem, '_apply_pre_push_quality_gate_inactive', lambda cands, pid: (list(cands), False)
        )
        monkeypatch.setattr(
            _mem, '_apply_pre_submission_self_review_inactive', lambda cands, pid: (list(cands), False)
        )
        monkeypatch.setattr(
            _mem, '_apply_unresolved_ask_provider_drop', lambda cands, m, ci, sonar: (list(cands), [])
        )
        monkeypatch.setattr(
            _mem, '_apply_lane_resolution', lambda steps, prof, m, pid: (list(steps), [], [])
        )
        monkeypatch.setattr(_mem, '_sort_steps_by_frontmatter_order', lambda steps: list(steps))
        monkeypatch.setattr(_mem, '_apply_ceremony_finalize_selection', lambda steps, gates: ([], []))

        def _capture(pid, manifest):
            captured['manifest'] = manifest

        monkeypatch.setattr(_mem, 'write_manifest', _capture)

    @staticmethod
    def _compose_args(plan_id, aspect):
        # change_type=feature + single_module + non-recipe + non-docs → Rule 7
        # (default), whose phase_5 verification list is the full candidate set.
        return Namespace(
            plan_id=plan_id,
            change_type='feature',
            track='complex',
            scope_estimate='single_module',
            recipe_key=None,
            affected_files_count=1,
            phase_5_steps='default:verify:quality-gate,default:verify:module-tests,default:verify:coverage',
            phase_6_steps='lessons-capture,archive-plan',
            aspect=aspect,
            commit_and_push=True,
            envelope_count=1,
        )

    @staticmethod
    def _write_status(plan_context, plan_id, metadata):
        plan_dir = plan_context.plan_dir_for(plan_id)
        (plan_dir / _dec.FILE_STATUS).write_text(
            json.dumps({'metadata': metadata}), encoding='utf-8'
        )

    def test_analysis_metadata_clears_verification_steps_without_arg(self, plan_context, monkeypatch):
        captured: dict = {}
        self._neutralize_external_collaborators(monkeypatch, captured)
        self._write_status(plan_context, 'compose-analysis', {'request_aspect': 'analysis'})

        result = _mem.cmd_compose(self._compose_args('compose-analysis', None))

        assert result['status'] == 'success'
        assert result['phase_5']['verification_steps_count'] == 0
        assert captured['manifest']['phase_5']['verification_steps'] == []

    def test_planning_metadata_clears_verification_steps_without_arg(self, plan_context, monkeypatch):
        captured: dict = {}
        self._neutralize_external_collaborators(monkeypatch, captured)
        self._write_status(plan_context, 'compose-planning', {'request_aspect': 'planning'})

        result = _mem.cmd_compose(self._compose_args('compose-planning', None))

        assert result['status'] == 'success'
        assert result['phase_5']['verification_steps_count'] == 0
        assert captured['manifest']['phase_5']['verification_steps'] == []

    def test_implementation_metadata_retains_all_gates(self, plan_context, monkeypatch):
        captured: dict = {}
        self._neutralize_external_collaborators(monkeypatch, captured)
        self._write_status(plan_context, 'compose-impl', {'request_aspect': 'implementation'})

        result = _mem.cmd_compose(self._compose_args('compose-impl', None))

        assert result['status'] == 'success'
        assert result['phase_5']['verification_steps_count'] == 3
        assert captured['manifest']['phase_5']['verification_steps'] == self._FULL_GATES

    def test_absent_metadata_retains_all_gates(self, plan_context, monkeypatch):
        captured: dict = {}
        self._neutralize_external_collaborators(monkeypatch, captured)
        # No status.json at all → self-read yields None → no-op → full retention.
        plan_context.plan_dir_for('compose-absent')

        _mem.cmd_compose(self._compose_args('compose-absent', None))

        assert captured['manifest']['phase_5']['verification_steps'] == self._FULL_GATES

    def test_explicit_arg_wins_over_persisted_metadata(self, plan_context, monkeypatch):
        captured: dict = {}
        self._neutralize_external_collaborators(monkeypatch, captured)
        # Persisted analysis metadata would clear the list, but an explicit
        # --aspect implementation takes precedence (mirroring --recipe-key over
        # _read_recipe_source) — the self-read is never consulted.
        self._write_status(plan_context, 'compose-argwins', {'request_aspect': 'analysis'})

        _mem.cmd_compose(self._compose_args('compose-argwins', 'implementation'))

        assert captured['manifest']['phase_5']['verification_steps'] == self._FULL_GATES
