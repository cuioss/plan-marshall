# SPDX-License-Identifier: FSL-1.1-ALv2

from _manage_status_mark_step_done_completion_head_and_keys_fixtures import (
    _args,
    _make_plan,
    cmd_mark_step_done,
    read_status,
)

# =============================================================================
# Step-key canonicalization
#
# The canonicalizer's own unit coverage (default strip, project/bundle preserve,
# idempotence) lives in test_step_key_canonical.py — the shared resolver's home.
# These cases assert the mark-step-done BOUNDARY behaviour: a prefixed --step is
# recorded under the canonical key computed by the shared resolver.
# =============================================================================


def test_mark_step_default_prefixed_records_under_bare_key(plan_context):
    """A ``default:``-prefixed --step is recorded under the bare manifest key.

    Recording under the caller's ``default:``-prefixed spelling must not orphan
    the record from the bare-keyed dispatcher reader, which would leave the step
    done on disk and invisible to the reader that checks whether it is done. The
    canonicalized key MUST be the bare name.
    """
    plan_id = 'mark-step-canon-prefixed'
    _make_plan(plan_id)
    result = cmd_mark_step_done(_args(plan_id, '6-finalize', 'default:push', 'done', display_detail='test detail'))

    assert result['status'] == 'success'
    # The returned step echoes the canonical bare key, not the prefixed input.
    assert result['step'] == 'push'

    persisted = read_status(plan_id)
    phase_steps = persisted['metadata']['phase_steps']['6-finalize']
    assert phase_steps == {'push': {'outcome': 'done', 'display_detail': 'test detail'}}
    assert 'default:push' not in phase_steps
