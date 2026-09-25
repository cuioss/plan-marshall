# SPDX-License-Identifier: FSL-1.1-ALv2
#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_config_build_map_seed_fixtures import (
    _FAKE_AGGREGATED,
    _FAKE_AGGREGATED_WITH_ADDED,
    _FAKE_AGGREGATED_WITH_REMOVED,
    Namespace,
    _cmd_build_map_mod,
    _config_core_mod,
    _seed_with,
)


def test_drift_in_sync_when_persisted_equals_derived(plan_context, monkeypatch):
    """drift returns in_sync: true when the persisted map equals the derivation.

    Seed with a deterministic aggregation, then run drift against the SAME
    aggregation — the derived and persisted glob sets are identical, so the
    diff is empty and in_sync is True with no drift entries.
    """
    # Arrange — seed with the fake map, leaving aggregate_build_map patched to
    # return that same map so the derived side matches the persisted side.
    _seed_with(monkeypatch, _FAKE_AGGREGATED)

    # Act — drift against the identical derivation.
    result = _cmd_build_map_mod.cmd_build_map_drift(Namespace(verb='drift'))

    # Assert — in sync, no drift.
    assert result['status'] == 'success'
    assert result['in_sync'] is True
    assert result['drift'] == {}



def test_drift_surfaces_added_globs(plan_context, monkeypatch):
    """drift surfaces added_globs for a glob in the derivation but absent from persisted.

    Seed with the baseline map, then point the derivation at a richer aggregation
    that gained `scripts/extra.py`. The drift must report that glob under
    added_globs (a route the project gained since the map was last seeded) and
    nothing under removed_globs.
    """
    # Arrange — persist the baseline map.
    _seed_with(monkeypatch, _FAKE_AGGREGATED)

    # Re-point the derivation at the richer aggregation (one extra production glob).
    monkeypatch.setattr(_config_core_mod, 'aggregate_build_map', lambda: _FAKE_AGGREGATED_WITH_ADDED)

    # Act
    result = _cmd_build_map_mod.cmd_build_map_drift(Namespace(verb='drift'))

    # Assert — the new glob is reported as added, nothing removed.
    assert result['status'] == 'success'
    assert result['in_sync'] is False
    assert result['drift']['python']['added_globs'] == ['scripts/extra.py']
    assert result['drift']['python']['removed_globs'] == []



def test_drift_surfaces_removed_globs(plan_context, monkeypatch):
    """drift surfaces removed_globs for a glob in persisted but absent from derivation.

    The reverse of the added case: seed with the baseline map (which carries the
    test route), then point the derivation at a thinner aggregation that dropped
    the test route. The drift must report the dropped glob under removed_globs and
    nothing under added_globs.
    """
    # Arrange — persist the baseline map (carries scripts/*.py and test/**/*.py).
    _seed_with(monkeypatch, _FAKE_AGGREGATED)

    # Re-point the derivation at the thinner aggregation (test route dropped).
    monkeypatch.setattr(_config_core_mod, 'aggregate_build_map', lambda: _FAKE_AGGREGATED_WITH_REMOVED)

    # Act
    result = _cmd_build_map_mod.cmd_build_map_drift(Namespace(verb='drift'))

    # Assert — the dropped glob is reported as removed, nothing added.
    assert result['status'] == 'success'
    assert result['in_sync'] is False
    assert result['drift']['python']['removed_globs'] == ['test/**/*.py']
    assert result['drift']['python']['added_globs'] == []



def test_drift_is_read_only_marshal_json_byte_identical(plan_context, monkeypatch):
    """drift never mutates marshal.json — the file is byte-identical after the call.

    Seed, snapshot the persisted marshal.json bytes, then run drift against a
    DIVERGENT derivation (so drift is non-empty). The on-disk bytes must be
    unchanged: drift is a pure read-only diff that never calls save_config.
    """
    # Arrange — persist the baseline map, then capture the exact on-disk bytes.
    _seed_with(monkeypatch, _FAKE_AGGREGATED)
    marshal_path = plan_context.fixture_dir / 'marshal.json'
    before = marshal_path.read_bytes()

    # Re-point the derivation at a divergent aggregation so drift is non-empty
    # (proving the byte-identity holds even when there IS drift to report).
    monkeypatch.setattr(_config_core_mod, 'aggregate_build_map', lambda: _FAKE_AGGREGATED_WITH_ADDED)

    # Act
    result = _cmd_build_map_mod.cmd_build_map_drift(Namespace(verb='drift'))

    # Assert — drift reported a diff, yet the file bytes are unchanged.
    assert result['status'] == 'success'
    assert result['in_sync'] is False
    after = marshal_path.read_bytes()
    assert after == before, 'drift mutated marshal.json — it must be read-only'
