#!/usr/bin/env python3
"""Tests for the modifier-session_id capture path in ``cmd_transition``.

The self-host fence (``project:finalize-step-self-host-fence``) consumes
``status.metadata.plan_marshall_modifier_session_id`` as its canonical
freshness anchor (per lesson 2026-05-20-08-002 § Canonical freshness
anchor). The anchor is written by ``cmd_transition`` when phase-5-execute
completes AND any entry in ``references.modified_files`` starts with
``marketplace/bundles/plan-marshall/``.

These tests pin the four contract cases:

1. plan-marshall path triggers capture
2. sibling-bundle-only path does not trigger
3. idempotence — second transition does not overwrite
4. ``session_id_unavailable`` resolver result produces no capture and no
   exception (fence's safe-default branch handles it)
"""

# ruff: noqa: I001, E402

import importlib.util
import json
from argparse import Namespace
from pathlib import Path

from conftest import PlanContext

# Tier 2 direct imports via importlib so the lifecycle module sees the same
# fixture-bound HOME/cwd state as the existing test_manage_status.py suite.
_SCRIPTS_DIR = (
    Path(__file__).parent.parent.parent.parent
    / 'marketplace'
    / 'bundles'
    / 'plan-marshall'
    / 'skills'
    / 'manage-status'
    / 'scripts'
)


def _load_module(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, _SCRIPTS_DIR / filename)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_lifecycle = _load_module('_status_cmd_lifecycle_capture', '_cmd_lifecycle.py')
_query = _load_module('_status_cmd_query_capture', '_status_query.py')

cmd_create = _lifecycle.cmd_create
cmd_transition = _lifecycle.cmd_transition
cmd_update_phase = _query.cmd_update_phase
cmd_set_phase = _query.cmd_set_phase


# =============================================================================
# Fixture builder — seed a plan at phase 5-execute with custom modified_files
# =============================================================================


def _seed_plan_at_execute(ctx, plan_id: str, modified_files: list[str]) -> None:
    """Create a plan with 1-init..4-plan done, 5-execute in_progress, base_branch
    set, and references.modified_files pre-populated.
    """
    cmd_create(
        Namespace(
            plan_id=plan_id,
            title='Modifier Session Capture Test',
            phases='1-init,2-refine,3-outline,4-plan,5-execute,6-finalize',
            force=False,
        )
    )
    for phase in ('1-init', '2-refine', '3-outline', '4-plan'):
        cmd_update_phase(Namespace(plan_id=plan_id, phase=phase, status='done'))
    cmd_set_phase(Namespace(plan_id=plan_id, phase='5-execute'))

    refs = {'base_branch': 'main', 'modified_files': list(modified_files)}
    refs_path = ctx.plan_dir / 'references.json'
    refs_path.write_text(json.dumps(refs), encoding='utf-8')


def _read_status_metadata(ctx) -> dict:
    status_path = ctx.plan_dir / 'status.json'
    return json.loads(status_path.read_text(encoding='utf-8')).get('metadata', {})


# =============================================================================
# Case 1: plan-marshall path triggers capture
# =============================================================================


def test_transition_5_execute_captures_session_id_for_plan_marshall_path(monkeypatch):
    """A modified file under marketplace/bundles/plan-marshall/ must trigger
    capture of the active session_id into status.metadata.
    """
    plan_id = 'capture-plan-marshall-path'
    with PlanContext(plan_id=plan_id) as ctx:
        _seed_plan_at_execute(
            ctx,
            plan_id,
            ['marketplace/bundles/plan-marshall/skills/some-skill/SKILL.md'],
        )

        # Stub _collect_modified_files so the guard does not overwrite the
        # pre-populated list and the prefix-intersection logic runs against
        # the values we seeded. Stub resolve_current_session_id by injecting
        # a fake ``manage_session`` module into the import path so the lazy
        # ``from manage_session import resolve_current_session_id`` inside
        # ``_capture_modifier_session_id`` resolves to the stub.
        monkeypatch.setattr(
            _lifecycle, '_collect_modified_files', lambda *args, **kwargs: []
        )

        import sys
        import types

        fake_module = types.ModuleType('manage_session')
        fake_module.resolve_current_session_id = lambda: 'sess-aaaaaaaa-1111-2222-3333-444444444444'  # type: ignore[attr-defined]
        monkeypatch.setitem(sys.modules, 'manage_session', fake_module)

        result = cmd_transition(Namespace(plan_id=plan_id, completed='5-execute'))
        assert result['status'] == 'success'

        metadata = _read_status_metadata(ctx)
        assert metadata.get('plan_marshall_modifier_session_id') == (
            'sess-aaaaaaaa-1111-2222-3333-444444444444'
        ), (
            'plan-marshall path in modified_files must trigger session_id '
            f'capture into status.metadata, got metadata={metadata}.'
        )


# =============================================================================
# Case 2: sibling-bundle-only path does not trigger
# =============================================================================


def test_transition_5_execute_sibling_bundle_does_not_trigger_capture(monkeypatch):
    """A modified file under a sibling bundle (e.g. pm-dev-java) must NOT
    trigger capture — only plan-marshall bundle paths qualify.
    """
    plan_id = 'capture-sibling-bundle'
    with PlanContext(plan_id=plan_id) as ctx:
        _seed_plan_at_execute(
            ctx,
            plan_id,
            ['marketplace/bundles/pm-dev-java/skills/java-core/SKILL.md'],
        )

        monkeypatch.setattr(
            _lifecycle, '_collect_modified_files', lambda *args, **kwargs: []
        )

        import sys
        import types

        fake_module = types.ModuleType('manage_session')
        # If resolve_current_session_id is called the test should fail —
        # the helper must NOT be invoked for non-plan-marshall paths.
        def _fail_called():
            raise AssertionError(
                'resolve_current_session_id called for sibling-bundle path'
            )
        fake_module.resolve_current_session_id = _fail_called  # type: ignore[attr-defined]
        monkeypatch.setitem(sys.modules, 'manage_session', fake_module)

        result = cmd_transition(Namespace(plan_id=plan_id, completed='5-execute'))
        assert result['status'] == 'success'

        metadata = _read_status_metadata(ctx)
        assert 'plan_marshall_modifier_session_id' not in metadata, (
            'Sibling-bundle-only modifications must NOT seed '
            f'plan_marshall_modifier_session_id, got metadata={metadata}.'
        )


# =============================================================================
# Case 3: idempotence — second transition does not overwrite
# =============================================================================


def test_transition_5_execute_capture_is_idempotent(monkeypatch):
    """A second transition with a different session_id must NOT overwrite an
    already-populated plan_marshall_modifier_session_id — the field anchors the
    ORIGINAL modifier session.
    """
    plan_id = 'capture-idempotent'
    with PlanContext(plan_id=plan_id) as ctx:
        _seed_plan_at_execute(
            ctx,
            plan_id,
            ['marketplace/bundles/plan-marshall/skills/manage-status/scripts/_cmd_lifecycle.py'],
        )

        monkeypatch.setattr(
            _lifecycle, '_collect_modified_files', lambda *args, **kwargs: []
        )

        import sys
        import types

        first_session = 'sess-original-1111-2222-3333-444444444444'
        second_session = 'sess-replaced-aaaa-bbbb-cccc-dddddddddddd'

        fake_module = types.ModuleType('manage_session')
        fake_module.resolve_current_session_id = lambda: first_session  # type: ignore[attr-defined]
        monkeypatch.setitem(sys.modules, 'manage_session', fake_module)

        # First transition — captures the original session_id.
        result1 = cmd_transition(Namespace(plan_id=plan_id, completed='5-execute'))
        assert result1['status'] == 'success'

        # Re-seed to 5-execute so we can transition again; mutate the helper
        # so it would write a DIFFERENT value if idempotence were broken.
        cmd_set_phase(Namespace(plan_id=plan_id, phase='5-execute'))
        fake_module.resolve_current_session_id = lambda: second_session  # type: ignore[attr-defined]

        result2 = cmd_transition(Namespace(plan_id=plan_id, completed='5-execute'))
        assert result2['status'] == 'success'

        metadata = _read_status_metadata(ctx)
        assert metadata.get('plan_marshall_modifier_session_id') == first_session, (
            'Idempotence broken: re-transition overwrote the original '
            f'modifier session anchor. Expected {first_session}, got '
            f"{metadata.get('plan_marshall_modifier_session_id')}."
        )


# =============================================================================
# Case 4: session_id_unavailable → no capture, no exception
# =============================================================================


def test_transition_5_execute_session_unavailable_yields_no_capture(monkeypatch):
    """When manage_session.resolve_current_session_id returns ``None`` (no hook
    cache, no HOME), the capture path must log a WARNING and proceed without
    writing the anchor — the fence's ``absent → fire on first dispatch`` safe
    default covers correctness.
    """
    plan_id = 'capture-session-unavailable'
    with PlanContext(plan_id=plan_id) as ctx:
        _seed_plan_at_execute(
            ctx,
            plan_id,
            ['marketplace/bundles/plan-marshall/skills/foo/SKILL.md'],
        )

        monkeypatch.setattr(
            _lifecycle, '_collect_modified_files', lambda *args, **kwargs: []
        )

        import sys
        import types

        fake_module = types.ModuleType('manage_session')
        fake_module.resolve_current_session_id = lambda: None  # type: ignore[attr-defined]
        monkeypatch.setitem(sys.modules, 'manage_session', fake_module)

        # Must not raise.
        result = cmd_transition(Namespace(plan_id=plan_id, completed='5-execute'))
        assert result['status'] == 'success'

        metadata = _read_status_metadata(ctx)
        assert 'plan_marshall_modifier_session_id' not in metadata, (
            'session_id_unavailable must NOT seed '
            f'plan_marshall_modifier_session_id, got metadata={metadata}.'
        )
