#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""The check era model — every emitted check block carries the ``fixed_since``
stamp sourced from the single ``CHECK_ERA`` table, and the stamp is inserted
after ``status`` without disturbing meta blocks.
"""


from _audit_fixtures import audit, minimal_corpus


def test_check_era_covers_exactly_all_checks():
    # The single CHECK_ERA table must stamp every registered check — no more, no
    # less — so no check inline-duplicates or misses a boundary stamp.
    # Non-vacuity: an empty registry would satisfy every assertion below
    # without examining a single check.
    assert audit.CHECK_NAMES, 'CHECK_NAMES is empty — the sweep would pass vacuously'
    assert set(audit.CHECK_ERA) == set(audit.CHECK_NAMES)


def test_reworked_checks_carry_this_plan_boundary():
    # Plan-13 reworks two checks' mechanics — the classify-before-route lane
    # signals and the Tier-1 recipe floor that re-arms the checkpoint measurement
    # — so their era boundary is plan-13's PR (#875), kept in lock-step with the
    # audit.py mirror. The `metrics` check has since moved OFF #875 to this plan's
    # own PR-PENDING boundary (see test_metrics_check_carries_this_plan_pr_boundary).
    for check in ("track-selection-accuracy", "lane-lever-effectiveness"):
        assert audit.CHECK_ERA[check] == "#875", check


def test_metrics_check_carries_this_plan_pr_boundary():
    # This plan makes per-step token attribution sound — D1 dispatch-boundary
    # reconciliation, D2 inline 6-finalize main-context attribution, and D3 the
    # loop-back boundary-monotonicity idle guard — exactly the per-phase
    # token/duration recording mechanics the `metrics` check verifies. So its era
    # boundary is this plan's own PR, carried as the PR-PENDING placeholder
    # (bumped from #875) until project:finalize-step-era-stamp-fill resolves it to
    # the real PR at finalize. This is the co-changing mirror of the audit.py
    # CHECK_ERA constant — the pair changes together and is the designated
    # acceptance for era-fill firing from a composed manifest.
    assert audit.CHECK_ERA["metrics"] == "#922"


def test_global_log_analysis_carries_this_plan_pr_boundary():
    # The cumulative cost roll-up reworks this check's aggregation and
    # signal-precision mechanics: it adds the `dominant-cost-caller` row kind and
    # ends the `genuine_signal_count == row count` identity, so a reader of an
    # archived row needs to know which side of that boundary it was recorded on.
    # Bumped from #849. Co-changing mirror of the audit.py CHECK_ERA constant.
    assert audit.CHECK_ERA["global-log-analysis"] == "#1260"


def test_merge_window_accounting_carries_this_plan_pr_boundary():
    # Plan-14 reworked the merge-window-accounting mechanics — D1 strips
    # --delete-branch/--strategy from the pr merge-queue enqueue path and D3 fixes the
    # merge-lock stale-holder liveness — both surfaces this check accounts for, so its
    # era boundary is plan-14's PR (#877, bumped from #863).
    assert audit.CHECK_ERA["merge-window-accounting"] == "#877"


def test_finalize_flow_conformance_carries_this_plan_pr_boundary():
    # Plan-17 reworked the finalize-flow-conformance mechanics — D1's pre-merge
    # comment barrier and D2's completion-aware polling rework the finalize
    # merge-completeness surface this check accounts for, so its era boundary is
    # plan-17's PR (#884, bumped from #849).
    assert audit.CHECK_ERA["finalize-flow-conformance"] == "#884"


def test_sequence_build_minimality_carries_this_plan_pr_boundary():
    # This plan RE-BASES the sequence-and-build-minimality check's build-duration
    # derivation off the plan-scoped log onto the structured change-ledger (every
    # build system, every phase), and adds the ledger-derived status ratio, the
    # build-vs-wall-clock share, the suspect-zero rule, and the
    # build-time-exceeds-wall-clock invariant. Those ARE the build-minimality
    # mechanics this check's rows are read against, so its era boundary is this
    # plan's own PR, carried as the PR-PENDING placeholder (bumped from #887) until
    # project:finalize-step-era-stamp-fill resolves it to the real PR at finalize.
    # This is the co-changing mirror of the audit.py CHECK_ERA constant — the pair
    # changes together and is the designated acceptance for era-fill firing from a
    # composed manifest.
    assert audit.CHECK_ERA["sequence-and-build-minimality"] == "#1224"


def test_plan8_reworked_checks_carry_pr_pending_boundary():
    # Plan-8 reworks two checks' mechanics, so their era boundary is plan-8's own PR,
    # carried as the PR-PENDING placeholder until project:finalize-step-era-stamp-fill
    # resolves it to the real PR at finalize (in lock-step with the audit.py mirror —
    # the pair changes together and is the designated acceptance for era-fill firing
    # from a composed manifest):
    #   * token-economics — plan-8's finalize-wait consolidation changes the
    #     finalize_heavy token-economics accounting this check flags (bumped from #887).
    #   * token-efficiency-trend — plan-8's per-dispatch context trim lowers the
    #     tokens-per-phase floor this cross-plan trend check reads (bumped from plan-10).
    for check in ("token-economics", "token-efficiency-trend"):
        assert audit.CHECK_ERA[check] == "#899", check


def test_dispatch_topology_carries_this_plan_pr_boundary():
    # This plan reworks the dispatch-topology check's boundary: D6's compose-time
    # execution_tier structural guard changes how the leaf/dispatch-topology
    # invariant (a leaf cannot reap a backgrounded build) is ENFORCED — from a
    # prose-only rule into a manifest fact — so its era boundary is this plan's own
    # PR, carried as the PR-PENDING placeholder (bumped from plan-10) until
    # project:finalize-step-era-stamp-fill resolves it to the real PR at finalize.
    # This is the co-changing mirror of the audit.py CHECK_ERA constant — the pair
    # changes together and is the designated acceptance for era-fill firing from a
    # composed manifest.
    assert audit.CHECK_ERA["dispatch-topology"] == "#893"


def test_stamp_era_inserts_fixed_since_after_status():
    # Arrange: a synthetic check block for a known check.
    block = "check: metrics\nstatus: success\ngenuine_signal_count: 0\nrows[0]{a}:\n"

    # Act
    stamped = audit._stamp_era(block)

    # Assert: fixed_since rides immediately after the status line, sourced from CHECK_ERA.
    lines = stamped.split("\n")
    assert lines[0] == "check: metrics"
    assert lines[1] == "status: success"
    assert lines[2] == f"fixed_since: {audit.CHECK_ERA['metrics']}"


def test_stamp_era_leaves_meta_blocks_untouched():
    # Meta blocks (report-diff / retire-on-quiet) carry no CHECK_ERA entry and
    # must pass through unchanged.
    meta = "check: report-diff\nstatus: success\nrows[0]{a}:\n"
    assert audit._stamp_era(meta) == meta


def test_execution_context_manifest_era_stamped_to_promotion_boundary():
    # The self-review promotion (default:pre-submission-self-review) bumped the
    # finalize-step-id surface this check re-derives, so its era stamp moves to #872.
    assert audit.CHECK_ERA["execution-context-manifest"] == "#872"
    block = "check: execution-context-manifest\nstatus: success\nrows[0]{a}:\n"
    stamped = audit._stamp_era(block)
    lines = stamped.split("\n")
    assert lines[0] == "check: execution-context-manifest"
    assert lines[1] == "status: success"
    assert lines[2] == "fixed_since: #872"


def test_full_run_stamps_every_check_block(tmp_path):
    # Arrange
    # Non-vacuity: an empty registry would satisfy every assertion below
    # without examining a single check.
    assert audit.CHECK_NAMES, 'CHECK_NAMES is empty — the sweep would pass vacuously'
    inputs = minimal_corpus(tmp_path)

    # Act
    output = audit.run_checks(inputs, list(audit.CHECK_NAMES), tmp_path)

    # Assert: every check block carries its fixed_since stamp right after status.
    for check in audit.CHECK_NAMES:
        expected = f"check: {check}\nstatus: success\nfixed_since: {audit.CHECK_ERA[check]}"
        assert expected in output, f"{check} missing its fixed_since stamp"
