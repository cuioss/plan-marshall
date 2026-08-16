#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""``exploration-share`` registration and the synthesis couplings it feeds — the
check registers ahead of synthesis, a full sweep emits its block, and the
surgical-overpay coupling fires only when both facets are present.
"""

from _audit_fixtures import audit, minimal_corpus


def test_exploration_share_carries_this_plan_pr_boundary():
    # The ten per-phase exploration counters this check reads are emitted for the
    # first time by the same plan that introduces the check, so every plan archived
    # before that boundary carries no counters at all and is EXCLUDED from the
    # corpus rather than read as zero-exploration. Its era boundary is therefore
    # that plan's own PR, carried as the PR-PENDING placeholder until
    # project:finalize-step-era-stamp-fill resolves it to the real PR at finalize.
    # This is the co-changing mirror of the audit.py CHECK_ERA constant — the pair
    # is rewritten in lock-step by that step.
    assert audit.CHECK_ERA["exploration-share"] == "#1043"


def test_exploration_share_registered_and_ordered_before_synthesis():
    # Registered in every table, and inserted BEFORE the facet-completeness critic
    # so the "synthesis runs last" invariant survives the addition.
    assert "exploration-share" in audit.CHECK_NAMES
    assert "exploration-share" in audit.CROSS_PLAN_CHECKS
    assert "exploration-share" in audit.CHECK_ERA
    assert audit.CHECK_NAMES[-1] == "cross-check-synthesis"
    assert audit.CHECK_NAMES.index("exploration-share") < audit.CHECK_NAMES.index(
        "cross-check-synthesis"
    )


def test_full_sweep_emits_exploration_share_block(tmp_path):
    # The full sweep emits the block, era-stamped, ahead of cross-check-synthesis.
    inputs = minimal_corpus(tmp_path)

    output = audit.run_checks(inputs, list(audit.CHECK_NAMES), tmp_path)

    assert (
        "check: exploration-share\nstatus: success\n"
        f"fixed_since: {audit.CHECK_ERA['exploration-share']}" in output
    )
    assert output.index("check: exploration-share") < output.index(
        "check: cross-check-synthesis"
    )


def test_lane_lever_registered_and_era_stamped():
    assert "lane-lever-effectiveness" in audit.CHECK_NAMES
    assert "lane-lever-effectiveness" in audit.CROSS_PLAN_CHECKS
    # Era bumped to this plan's own PR boundary (#875).
    assert audit.CHECK_ERA["lane-lever-effectiveness"] == "#875"
    # cross-check-synthesis stays last after the new registration.
    assert audit.CHECK_NAMES[-1] == "cross-check-synthesis"


def test_surgical_overpay_coupling_fires_on_miss_and_big_spend():
    # coupling (j): a lane-lever miss (checkpoint_over) AND token-economics
    # big_spend_tiny_footprint over the same plan.
    all_results = {
        "lane-lever-effectiveness": {
            "rows": [{"plan_id": "p-over", "flags": "checkpoint_over"}]
        },
        "token-economics": {
            "rows": [{"plan_id": "p-over", "flags": ["big_spend_tiny_footprint(2Mtok)"]}]
        },
    }
    result = audit.cross_check_synthesis(all_results)
    by = {r["coupling"]: r for r in result["rows"]}
    assert by["surgical_overpay"]["fired"] is True
    assert "p-over" in by["surgical_overpay"]["detail"]
    assert result["couplings_evaluated"] == 10


def test_surgical_overpay_coupling_unfired_when_facets_disjoint():
    # The lane-lever miss and the big-spend footprint on DIFFERENT plans do not
    # couple — the coupling requires the SAME plan on both facets.
    all_results = {
        "lane-lever-effectiveness": {
            "rows": [{"plan_id": "p-over", "flags": "checkpoint_over"}]
        },
        "token-economics": {
            "rows": [{"plan_id": "other", "flags": ["big_spend_tiny_footprint(2Mtok)"]}]
        },
    }
    result = audit.cross_check_synthesis(all_results)
    by = {r["coupling"]: r for r in result["rows"]}
    assert by["surgical_overpay"]["fired"] is False


def test_synthesis_evaluates_ten_couplings_on_empty_results():
    # Best-effort degradation: every coupling (now ten) still evaluated, none fired.
    result = audit.cross_check_synthesis({})
    assert result["couplings_evaluated"] == 10
    assert result["couplings_fired"] == 0
    by = {r["coupling"]: r for r in result["rows"]}
    assert "surgical_overpay" in by
