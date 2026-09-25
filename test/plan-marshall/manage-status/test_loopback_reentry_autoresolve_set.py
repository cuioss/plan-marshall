# SPDX-License-Identifier: FSL-1.1-ALv2
#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_status_loopback_reentry_autoresolve_fixtures import (
    Namespace,
    _read_status,
    _seed_plan,
    _stub_metadata,
    _stubbed_invariants,
    cmd_set_phase,
    json,
)

# =============================================================================
# (d-pre) Explicit-None metadata is normalized, never crashed on
# =============================================================================


def test_set_phase_loop_back_with_explicit_none_metadata(plan_context, _stubbed_invariants, _stub_metadata):
    """An explicit JSON null for status['metadata'] must be normalized by the
    backward set-phase (dict.setdefault would return None and the marker
    assignment would raise TypeError)."""
    plan_id = 'loopback-none-metadata-setphase'
    status_path = _seed_plan(plan_context, plan_id)
    status = _read_status(status_path)
    status['metadata'] = None
    status_path.write_text(json.dumps(status), encoding='utf-8')

    result = cmd_set_phase(Namespace(plan_id=plan_id, phase='2-refine'))

    assert result['status'] == 'success'
    marker = _read_status(status_path).get('metadata', {}).get('loop_back_reentry')
    assert marker is not None, (
        'Explicit-None metadata must be normalized to a dict so the backward '
        'set-phase can persist the loop-back marker.'
    )
    assert marker['from_phase'] == '5-execute'
