#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""``sequence-and-build-minimality`` ci_rerun — multiple CI run directories in a
plan fire the ci_rerun flag.
"""

from _audit_fixtures import audit


def test_sequence_ci_rerun_fires_on_multiple_ci_run_dirs(tmp_path):
    # Pin: the ci_rerun signal still counts CI run directories (logic unchanged by
    # the post-#849/#850 re-doc; only the interpretation guidance changed).
    plan_dir = tmp_path / ".plan" / "local" / "archived-plans" / "seq-plan"
    (plan_dir / "artifacts" / "ci-runs" / "run-1").mkdir(parents=True)
    (plan_dir / "artifacts" / "ci-runs" / "run-2").mkdir(parents=True)
    (plan_dir / "references.json").write_text('{"scope_estimate": "surgical"}', encoding="utf-8")
    (plan_dir / "status.json").write_text(
        '{"metadata": {"change_type": "bug_fix"}}', encoding="utf-8"
    )
    inputs = audit.collect_inputs(plan_dir)

    # No builds staged in the ledger — this pins the ci_rerun signal (CI dirs).
    result = audit.cross_sequence_build_minimality([inputs], {})
    row = next(r for r in result["rows"] if r["plan_id"] == "seq-plan")
    assert row["ci_runs"] == 2
    assert any(f.startswith("ci_rerun") for f in row["flags"]), row["flags"]
