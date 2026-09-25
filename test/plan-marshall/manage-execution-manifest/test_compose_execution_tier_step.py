# SPDX-License-Identifier: FSL-1.1-ALv2
#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_execution_manifest_compose_execution_tier_fixtures import (
    _clear_arch_resolve_cache,
    _core,
)


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
