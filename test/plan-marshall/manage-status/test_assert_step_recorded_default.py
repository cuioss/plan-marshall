# SPDX-License-Identifier: FSL-1.1-ALv2
#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_status_assert_step_recorded_fixtures import _assert_args, _make_plan, _seed_step, cmd_assert_step_recorded

# =============================================================================
# Canonical step-key round-trip: a bare↔default: / promoted-alias variant
# recorded with one spelling resolves as a canonical MATCH when queried with the
# variant spelling (shared canonicalize_step_key on both write and read).
# =============================================================================


def test_default_prefixed_record_matches_bare_query(plan_context):
    """Record via ``default:push`` then assert via ``push`` → recorded (no mismatch).

    Both the write (mark-step-done) and the read (assert-step-recorded) route the
    step through the shared canonicalizer, so a ``default:``-prefixed record
    reconciles to a canonical MATCH under the bare query.
    """
    plan_id = 'assert-canon-default-to-bare'
    _make_plan(plan_id)
    _seed_step(plan_id, '6-finalize', 'default:push', 'done')

    result = cmd_assert_step_recorded(_assert_args(plan_id, '6-finalize', 'push', require_terminal=True))

    assert result['status'] == 'success'
    assert result['recorded'] is True
    assert result['outcome'] == 'done'
    assert result['step'] == 'push'
