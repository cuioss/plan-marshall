# SPDX-License-Identifier: FSL-1.1-ALv2

from _manage_status_assert_step_recorded_fixtures import (
    _assert_args,
    _make_plan,
    cmd_assert_step_recorded,
    read_status,
    write_status,
)

# =============================================================================
# Near-miss orphan key -> step_record_mismatched_key
# =============================================================================


def test_canonical_key_present_is_recorded_terminal(plan_context):
    """(1) When the queried (canonical) key carries a terminal record, the verb
    reports recorded/terminal even if other orphan keys also exist — the
    near-miss scan never fires when the canonical record is present."""
    plan_id = 'assert-mismatch-canonical'
    _make_plan(plan_id)
    status = read_status(plan_id)
    status.setdefault('metadata', {})['phase_steps'] = {
        '6-finalize': {
            'plan-marshall:plan-retrospective': {'outcome': 'done', 'display_detail': None},
            'plan-retrospective': {'outcome': 'done', 'display_detail': None},
        }
    }
    write_status(plan_id, status)

    result = cmd_assert_step_recorded(
        _assert_args(plan_id, '6-finalize', 'plan-marshall:plan-retrospective', require_terminal=True)
    )

    assert result['status'] == 'success'
    assert result['recorded'] is True
    assert result['outcome'] == 'done'


# =============================================================================
# Legacy-vs-canonical duplicate: the fresher canonical write must win over a
# stale legacy (``default:``-prefixed) key inserted earlier in the dict.
# =============================================================================


def test_canonical_exact_match_wins_over_stale_legacy_prefixed_key(plan_context):
    """When both a stale legacy ``default:push`` key and a fresh canonical ``push``
    key are present (legacy inserted first, per dict insertion order), the read
    side must prefer the exact canonical match and report the FRESH outcome, not
    the stale legacy one the ordered scan would hit first.

    A scan that breaks on the first canonical match lets the earlier-inserted
    ``default:push`` entry (a pre-migration write) shadow the newer ``push``
    write, so the read reports a stale outcome as the current one.
    """
    plan_id = 'assert-legacy-shadow'
    _make_plan(plan_id)
    status = read_status(plan_id)
    # Insertion order: stale legacy key first, fresh canonical key second.
    status.setdefault('metadata', {})['phase_steps'] = {
        '6-finalize': {
            'default:push': {'outcome': 'failed', 'display_detail': 'stale legacy'},
            'push': {'outcome': 'done', 'display_detail': 'fresh canonical'},
        }
    }
    write_status(plan_id, status)

    result = cmd_assert_step_recorded(_assert_args(plan_id, '6-finalize', 'push', require_terminal=True))

    assert result['status'] == 'success'
    assert result['recorded'] is True
    assert result['outcome'] == 'done'
