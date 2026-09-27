# SPDX-License-Identifier: FSL-1.1-ALv2

from _manage_execution_manifest_compose_execution_tier_fixtures import (
    _clear_arch_resolve_cache,
    _fake_resolver,
    _mem,
    _stamp,
)


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
