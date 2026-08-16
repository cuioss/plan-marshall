#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Check registration and full-sweep wiring — every newly registered check is
era-stamped, and a full sweep emits its block and its synthesis couplings.
"""

from _audit_fixtures import audit, minimal_corpus


def test_new_checks_registered_and_era_stamped():
    for c in ("dispatch-topology", "finalize-flow-conformance", "merge-window-accounting"):
        assert c in audit.CHECK_NAMES
        assert c in audit.CHECK_ERA
    assert "merge-window-accounting" in audit.CROSS_PLAN_CHECKS
    assert "dispatch-topology" not in audit.CROSS_PLAN_CHECKS
    assert audit.CHECK_NAMES[-1] == "cross-check-synthesis"


def test_full_sweep_emits_new_blocks_and_couplings(tmp_path):
    inputs = minimal_corpus(tmp_path)
    output = audit.run_checks(inputs, list(audit.CHECK_NAMES), tmp_path)
    for c in (
        "dispatch-topology",
        "finalize-flow-conformance",
        "merge-window-accounting",
        "lane-lever-effectiveness",
    ):
        assert f"check: {c}\nstatus: success\nfixed_since: {audit.CHECK_ERA[c]}" in output
    for coupling in (
        "dispatch_topology_reentry",
        "finalize_gate_gap_ci_rerun",
        "merge_window_ci_rerun",
        "surgical_overpay",
    ):
        assert coupling in output
    # cross-check-synthesis remains the last check block, ahead of the meta blocks.
    assert output.index("check: lane-lever-effectiveness") < output.index(
        "check: cross-check-synthesis"
    )
