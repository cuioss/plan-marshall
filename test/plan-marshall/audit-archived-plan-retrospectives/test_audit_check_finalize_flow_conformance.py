#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""``finalize-flow-conformance`` — a finalize flow missing ``ci_verify`` is
flagged, a ci-wait timeout and an unresolved state are reported, and a
conformant flow is clean.
"""

from pathlib import Path

from _audit_fixtures import audit


def _plan_finalize(
    repo_root: Path, name: str, phase6: list[str], ci_runs: dict[str, tuple[str, str]]
) -> audit.PlanInputs:
    pd = repo_root / ".plan" / "local" / "archived-plans" / name
    pd.mkdir(parents=True, exist_ok=True)
    (pd / "references.json").write_text('{"scope_estimate": "surgical"}', encoding="utf-8")
    (pd / "status.json").write_text(
        '{"metadata": {"change_type": "bug_fix"}}', encoding="utf-8"
    )
    step_lines = "\n".join(f'    - "{s}"' for s in phase6)
    (pd / "execution.toon").write_text(
        f"phase_5:\n  early_terminate: false\nphase_6:\n  steps[{len(phase6)}]:\n{step_lines}\n",
        encoding="utf-8",
    )
    for run_id, (wo, fs) in ci_runs.items():
        rd = pd / "artifacts" / "ci-runs" / run_id
        rd.mkdir(parents=True)
        (rd / "manifest.toon").write_text(
            f"run_id: {run_id}\nwait_outcome: {wo}\nfinal_status: {fs}\n", encoding="utf-8"
        )
    return audit.collect_inputs(pd)


def test_finalize_flow_missing_ci_verify(tmp_path):
    inputs = _plan_finalize(tmp_path, "pr_no_civ", ["default:create-pr", "default:push"], {})
    row = audit.check_finalize_flow_conformance(inputs)
    assert "missing_ci_verify" in row["flags"]
    assert audit._finalize_flow_genuine(row) is True


def test_finalize_flow_ci_wait_timeout_and_unresolved(tmp_path):
    inputs = _plan_finalize(
        tmp_path,
        "timeout",
        ["default:create-pr", "default:ci-verify", "default:push"],
        {"111": ("deadline_exceeded", "timeout")},
    )
    row = audit.check_finalize_flow_conformance(inputs)
    assert "ci_wait_timeout" in row["flags"]
    assert "ci_unresolved" in row["flags"]


def test_finalize_flow_conformant_is_clean(tmp_path):
    inputs = _plan_finalize(
        tmp_path,
        "clean",
        ["default:create-pr", "default:ci-verify", "default:push"],
        {"111": ("completed", "success")},
    )
    row = audit.check_finalize_flow_conformance(inputs)
    assert row["flags"] == ""
    assert row["has_ci_verify_step"] == "true"
    assert audit._finalize_flow_genuine(row) is False
