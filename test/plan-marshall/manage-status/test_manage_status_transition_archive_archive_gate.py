# SPDX-License-Identifier: FSL-1.1-ALv2
#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_status_manage_status_transition_archive_fixtures import (
    Namespace,
    _seed_early_archive_plan,
    _seed_two_in_progress_plan,
    _stub_finding_queries,
    cmd_archive,
    json,
)

# =============================================================================
# The findings gate reads the OPEN-PHASE SET, not `current_phase`.
#
# A backward `set-phase` from `6-finalize` to `5-execute` leaves BOTH phases
# `in_progress` while moving `current_phase` to `5-execute`. A gate testing
# `status['current_phase'] == '6-finalize'` therefore does not fire in exactly the
# state a loop-back produces, so a no-reason archive could close both phases and
# archive the plan with actionable findings still pending. That reachability is a
# consequence of the close-every-open-phase change above, which is what makes it this
# plan's to fix rather than pre-existing debt.
#
# The three cells below vary one axis each around the same seed, so each answers a
# question the others cannot: does the gate fire when finalize is open but NOT
# current (the defect), does `--reason` still exempt it (the intent discriminator),
# and does it stay silent when the open phase is NOT finalize (the over-broad-gate
# control).
# =============================================================================


def test_archive_gate_fires_when_finalize_is_open_but_not_current(plan_context, monkeypatch):
    """NEGATIVE control: two phases open, `current_phase` is 5-execute ⇒ still refused.

    The precondition assertions are what make this fail against the retired
    `current_phase` equality: the plan really is NOT in `6-finalize` by that measure,
    and finalize really IS still open.
    """
    _stub_finding_queries(monkeypatch, {'sonar-issue': 2})
    plan_id = 'finalize-open-but-not-current'
    _seed_two_in_progress_plan(plan_id)

    live_status = json.loads((plan_context.plan_dir_for(plan_id) / 'status.json').read_text(encoding='utf-8'))
    assert live_status['current_phase'] == '5-execute', (
        f'Seed precondition: a current_phase equality test must NOT match here, or this '
        f'cell passes against the retired gate. Got {live_status["current_phase"]!r}.'
    )
    open_before = [p['name'] for p in live_status['phases'] if p['status'] == 'in_progress']
    assert open_before == ['5-execute', '6-finalize'], (
        f'Seed precondition: 6-finalize must really still be open. Got {open_before!r}.'
    )

    result = cmd_archive(Namespace(plan_id=plan_id, dry_run=False, reason=None))

    assert result['status'] == 'error', result
    assert result['error'] == 'blocking_findings_present', result
    assert result['blocking_count'] == 2, result
    assert plan_context.plan_dir_for(plan_id).exists(), 'The refused archive must move nothing.'
    assert 'archived_to' not in result, result



def test_archive_gate_stays_silent_when_the_open_phase_is_not_finalize(plan_context, monkeypatch):
    """Matched control: an open phase that is NOT 6-finalize must not arm the gate.

    Without this cell, the widened predicate is equally consistent with one that fires
    on ANY open phase — which would block every mid-lifecycle abandonment behind
    findings the plan never reached finalize to triage.
    """
    _stub_finding_queries(monkeypatch, {'sonar-issue': 2})
    plan_id = 'finalize-not-open-early-abandon'
    _seed_early_archive_plan(plan_id)

    live_status = json.loads((plan_context.plan_dir_for(plan_id) / 'status.json').read_text(encoding='utf-8'))
    open_before = [p['name'] for p in live_status['phases'] if p['status'] == 'in_progress']
    assert open_before == ['2-refine'], (
        f'Seed precondition: exactly one open phase, and it is not 6-finalize. Got {open_before!r}.'
    )

    result = cmd_archive(Namespace(plan_id=plan_id, dry_run=False, reason=None))

    assert result['status'] == 'success', (
        f'The gate is about finalize being open, not about any phase being open: {result!r}.'
    )
    assert 'archived_to' in result, result
