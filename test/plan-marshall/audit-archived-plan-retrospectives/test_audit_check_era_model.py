#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""The check era model — every emitted check block carries the ``fixed_since``
stamp sourced from the single ``CHECK_ERA`` table, and the stamp is inserted
after ``status`` without disturbing meta blocks.
"""

import importlib.util
import re

from _audit_fixtures import audit, minimal_corpus

from conftest import PROJECT_ROOT

_ERA_FILL_SCRIPT = (
    PROJECT_ROOT / '.claude' / 'skills' / 'finalize-step-era-stamp-fill' / 'scripts'
    / 'era_stamp_fill.py'
)
_AUDIT_SOURCE = (
    PROJECT_ROOT / '.claude' / 'skills' / 'audit-archived-plan-retrospectives' / 'scripts'
    / 'audit.py'
)
_MIRROR_SOURCE = (
    PROJECT_ROOT / 'test' / 'plan-marshall' / 'audit-archived-plan-retrospectives'
    / 'test_audit_check_era_model.py'
)


def _load_era_fill():
    """Load the finalize step's fill executor by path (project-local, not a bundle script)."""
    spec = importlib.util.spec_from_file_location('era_stamp_fill_under_test', _ERA_FILL_SCRIPT)
    assert spec is not None and spec.loader is not None, f'cannot load {_ERA_FILL_SCRIPT}'
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


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
    # This plan changes what the sequence-and-build-minimality check's numbers
    # MEAN, in three ways an archived row cannot disclose about itself: the
    # `build_share` numerator gate (a share is emitted only when the build-duration
    # numerator was measured, where a missing numerator used to default to zero and
    # render as a real zero share), the `_ZERO_GATED` class (a measured zero is now
    # distinguishable from an absent measurement), and the `status_unknown` row
    # column (a build whose outcome could not be read is its own state instead of
    # silently joining the pass or fail bucket). Each turns a former confident zero
    # into an explicit not-measured, so rows computed under the old semantics are
    # no longer datable against #1224 and the boundary moves to this plan's own PR,
    # carried as the PR-PENDING placeholder (bumped from #1224) until
    # project:finalize-step-era-stamp-fill resolves it to the real PR at finalize.
    # This is the co-changing mirror of the audit.py CHECK_ERA constant — the pair
    # changes together and is the designated acceptance for era-fill firing from a
    # composed manifest.
    assert audit.CHECK_ERA["sequence-and-build-minimality"] == "#1342"


def test_pending_sentinel_is_in_the_form_the_finalize_step_resolves():
    """The sentinel must be RESOLVABLE, not merely present (D9).

    ``era_stamp_fill.py`` matches only the double-quoted map-value form of the
    PR-PENDING token, deliberately sparing prose mentions. (This docstring writes
    the token WITHOUT its quotes on purpose: a quoted mention in prose is matched
    like any other, so the fill would rewrite this very sentence into a PR number
    and inflate the lock-step count asserted below.) A sentinel written any other
    way — single-quoted, spaced, or only described in a comment — leaves the
    finalize step reporting ``skipped: true``, which it records as ``done``. The
    step then passes, the phase completes, and the unresolved boundary ships into
    ``main`` claiming a PR that was never assigned: a green that means the exact
    opposite of what it appears to.

    This asserts the fill WOULD fire, against the executor's own matcher rather
    than a second copy of the token, so a change to what "unresolved" means breaks
    here instead of silently at finalize.

    ⛔ **The pair has TWO legitimate states and this test spans both**, because
    ``project:finalize-step-era-stamp-fill`` runs at ``order: 21`` of this repo's
    own finalize — so from that point onward, including in every landed commit on
    ``main``, the sentinel is RESOLVED. A test that asserted only the unresolved
    state would pin a state its own finalize destroys, and would be red on the very
    branch that authored it. Each arm below carries its own falsifiable assertion;
    neither is a bare early return, and the mixed state (a resolved boundary beside
    a surviving sentinel, or the reverse) fails in both.
    """
    era_fill = _load_era_fill()
    token = era_fill.PENDING_TOKEN.strip('"')
    boundary = audit.CHECK_ERA['sequence-and-build-minimality']
    sources = {path.name: path.read_text(encoding='utf-8') for path in (_AUDIT_SOURCE, _MIRROR_SOURCE)}
    carriers = {name: era_fill.PENDING_TOKEN in text for name, text in sources.items()}

    if boundary == token:
        # UNRESOLVED — the fill has not run against this tree yet. Assert it WOULD
        # fire, which is the property that cannot be recovered once it has.
        for name, text in sources.items():
            assert carriers[name], (
                f'{name} carries no map-value sentinel while the boundary is still {token}, so '
                'project:finalize-step-era-stamp-fill will report skipped:true and record done '
                'without resolving anything. A prose-only mention is not a sentinel.'
            )
            filled, count = era_fill.fill_pending_token(text, '#1234')
            assert count >= 1, f'{name}: the matcher found no sentinel to fill.'
            assert era_fill.PENDING_TOKEN not in filled, (
                f'{name}: a sentinel survived the fill, so the resolution is not total.'
            )
            assert '"#1234"' in filled, f'{name}: the fill did not write the resolved PR value.'
        return

    # RESOLVED — the finalize step already ran. "Would it fire" is no longer
    # falsifiable here, so assert what still is: the resolution was TOTAL, and it
    # produced a real PR token rather than some third value.
    assert re.fullmatch(r'#\d+', boundary), (
        f'boundary {boundary!r} is neither the {token} sentinel nor a resolved #NNN token — '
        'the era stamp is in a state no writer produces.'
    )
    assert not any(carriers.values()), (
        f'the boundary resolved to {boundary} but a sentinel survives in {carriers} — the fill '
        'was partial, so the pair no longer moves in lock-step.'
    )


def test_pending_sentinel_count_is_lock_step_across_the_pair():
    """audit.py and its mirror carry the sentinel the same number of times.

    The two files are rewritten together in one pass. If one carries a sentinel the
    other does not, the fill resolves them unevenly and the mirror stops mirroring
    — the drift this pair exists to prevent, arriving through the fix itself.

    Lock-step is the invariant in BOTH states: equal counts before the fill (one
    each) and equal counts after it (zero each). A zero pair is therefore NOT an
    error — but it is only legitimate when the fill is what emptied it, so the zero
    arm is corroborated against the resolved boundary rather than accepted on its
    own. Without that corroboration a pair that simply lost its sentinel — never
    written, or deleted by hand — would read as a clean lock-step pass.
    """
    era_fill = _load_era_fill()
    counts = {
        path.name: path.read_text(encoding='utf-8').count(era_fill.PENDING_TOKEN)
        for path in (_AUDIT_SOURCE, _MIRROR_SOURCE)
    }
    assert len(set(counts.values())) == 1, (
        f'audit.py and its mirror carry different sentinel counts: {counts}. The pair must '
        'move in lock-step.'
    )

    if not any(counts.values()):
        boundary = audit.CHECK_ERA['sequence-and-build-minimality']
        assert re.fullmatch(r'#\d+', boundary), (
            f'both files carry zero sentinels while the boundary is {boundary!r} — the sentinel '
            'left the pair without project:finalize-step-era-stamp-fill resolving it, so the '
            'equal-count pass says nothing about lock-step.'
        )


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
    #
    # The status VALUE is deliberately unconstrained here. `_stamp_era` inserts the
    # stamp after whatever `status:` line the block carries, and a check whose
    # substrate this corpus does not stage reports `unmeasured` rather than
    # `success` — it must still be stamped. Pinning `success` would make this test
    # fail for the honest state and pass only while every check pretends to have
    # measured something, which is the reading the `unmeasured` state exists to
    # end.
    for check in audit.CHECK_NAMES:
        stamped = re.compile(
            rf"^check: {re.escape(check)}\n"
            rf"status: \S+\n"
            rf"fixed_since: {re.escape(audit.CHECK_ERA[check])}$",
            re.MULTILINE,
        )
        assert stamped.search(output), f"{check} missing its fixed_since stamp"
