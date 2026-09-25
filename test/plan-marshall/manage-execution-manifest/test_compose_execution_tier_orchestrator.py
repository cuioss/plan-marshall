# SPDX-License-Identifier: FSL-1.1-ALv2
#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_execution_manifest_compose_execution_tier_fixtures import (
    _clear_arch_resolve_cache,
    _fake_resolver,
    _mem,
    _stamp,
)


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
