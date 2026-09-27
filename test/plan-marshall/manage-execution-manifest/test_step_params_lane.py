# SPDX-License-Identifier: FSL-1.1-ALv2

from _manage_execution_manifest_step_params_fixtures import (
    _compose_ns,
    _mem,
    _patch_lane_resolution,
    _seed_marshal_with_lane_overrides,
    cmd_compose,
    get_manifest_path,
)


def test_lane_snapshot_leaves_an_ownerless_step_as_null(plan_context, monkeypatch):
    """An ownerless step still snapshots as ``null`` once lanes are resolved.

    The lane rewrite must not materialize a param object for a step that owns
    none — ``push`` carries no params at all, so the no-empty-``{}`` contract is
    unchanged by the effective-lane pass.
    """
    _seed_marshal_with_lane_overrides(plan_context.fixture_dir, {'default:lessons-capture': 'off'})
    _patch_lane_resolution(monkeypatch, 'standard')

    cmd_compose(_compose_ns('sp-lane-ownerless'))

    raw = get_manifest_path('sp-lane-ownerless').read_text(encoding='utf-8')
    parsed = _mem.parse_toon(raw)
    assert parsed['phase_6']['step_params'].get('push') is None
