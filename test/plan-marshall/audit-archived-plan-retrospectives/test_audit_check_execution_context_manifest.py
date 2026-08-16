#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""``execution-context-manifest`` step-owner drift — an unknown built-in
phase-6 step is flagged, a canonical roster is clean, an unknown EXTERNAL
step is ignored, and the manifest check surfaces the owner-drift column.
"""

from pathlib import Path

from _audit_fixtures import audit


def _resolve_owner(step: str):
    return audit._resolve_step_owner(step)


def test_resolve_step_owner_classes():
    assert _resolve_owner("default:push") == "orchestrator"
    assert _resolve_owner("push") == "orchestrator"
    assert _resolve_owner("plan-marshall:automatic-review") == "leaf"
    assert _resolve_owner("default:architecture-refresh") == "hybrid"
    assert _resolve_owner("project:finalize-step-plugin-doctor") == "leaf"
    # Unknown BUILT-IN → None (roster drift); unknown EXTERNAL → None (not drift).
    assert _resolve_owner("default:bogus-finalize-step") is None
    assert _resolve_owner("project:some-unknown-step") is None


def _plan_with_phase6(repo_root: Path, steps: list[str]) -> audit.PlanInputs:
    plan_dir = repo_root / ".plan" / "local" / "archived-plans" / "sample-plan"
    plan_dir.mkdir(parents=True, exist_ok=True)
    (plan_dir / "references.json").write_text('{"scope_estimate": "surgical"}', encoding="utf-8")
    (plan_dir / "status.json").write_text(
        '{"metadata": {"change_type": "bug_fix"}}', encoding="utf-8"
    )
    step_lines = "\n".join(f'    - "{s}"' for s in steps)
    manifest = (
        "phase_5:\n  early_terminate: false\n"
        "phase_6:\n"
        f"  steps[{len(steps)}]:\n{step_lines}\n"
    )
    (plan_dir / "execution.toon").write_text(manifest, encoding="utf-8")
    return audit.collect_inputs(plan_dir)


def test_owner_drift_flags_unknown_builtin_phase6_step(tmp_path):
    inputs = _plan_with_phase6(tmp_path, ["default:push", "default:bogus-finalize-step"])
    drift = audit.detect_owner_drift(inputs)
    assert drift is not None
    assert "bogus-finalize-step" in drift


def test_owner_drift_clean_on_canonical_roster(tmp_path):
    inputs = _plan_with_phase6(
        tmp_path, ["default:push", "default:create-pr", "default:archive-plan"]
    )
    assert audit.detect_owner_drift(inputs) is None


def test_owner_drift_ignores_unknown_external_step(tmp_path):
    # An unknown project/skill step is project-defined, never a canonical-roster fault.
    inputs = _plan_with_phase6(tmp_path, ["default:push", "project:some-unknown-step"])
    assert audit.detect_owner_drift(inputs) is None


def test_manifest_check_surfaces_owner_drift_column(tmp_path):
    inputs = _plan_with_phase6(tmp_path, ["default:bogus-finalize-step"])
    row = audit.check_execution_manifest(inputs, tmp_path, {})
    assert row["owner_drift"]
    assert audit._manifest_genuine(row) is True
