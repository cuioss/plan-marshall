# SPDX-License-Identifier: FSL-1.1-ALv2
#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_status_loopback_reentry_autoresolve_fixtures import Namespace, _lifecycle


def test_loop_back_auto_override_with_explicit_none_metadata():
    """_loop_back_auto_override must not raise AttributeError when
    status['metadata'] is explicitly None — it returns the verify result
    unchanged (no marker means no auto-override)."""
    verify_result = {'status': 'drift', 'drift_count': 1, 'diffs': []}

    result = _lifecycle._loop_back_auto_override(
        Namespace(plan_id='loopback-none-metadata-override', completed='5-execute'),
        {'metadata': None},
        verify_result,
    )

    assert result is verify_result, (
        'None metadata carries no marker — the blocking verify result must be returned unchanged, not crashed on.'
    )
