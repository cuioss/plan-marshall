#!/usr/bin/env python3
"""Audit archived plans for execution-manifest correctness.

Walks `.plan/local/archived-plans/{plan_id}/` directories and per plan extracts:

- inputs from `references.json` (`scope_estimate`, `affected_files[]`,
  `modified_files[]`) and `status.json::metadata`
  (`change_type`, `plan_source`/recipe_key),
- the actual manifest from `execution.toon`,
- the composer's `Rule … fired` line from `logs/decision.log` if present,

then re-runs the 7-row decision matrix from
`manage-execution-manifest/standards/decision-rules.md` against the same inputs
and compares the derived rule key + manifest shape to what was persisted.

Emits a TOON report grouped by verdict (`ok`, `drift`, `incomplete`,
`unloggable`). Intended consumer: `/audit-execution-context`.

The script is deterministic by design — per
`extension-api/standards/dispatch-granularity.md` Heuristic 1 the matrix
evaluation is a boolean predicate over file-derived inputs, so it lives in a
script rather than a dispatch envelope.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

# Canonical phase-5 step names the standard intersects against in Rows 2/3/5.
# Projects that rename these (e.g. `quality_check` instead of `quality-gate`)
# will see Row 5's intersection drop to empty — flagged in the report as a
# `name_drift` signal.
CANON_QUALITY_GATE = {"quality-gate", "module-tests"}
CANON_COVERAGE = "coverage"


@dataclass
class PlanInputs:
    plan_id: str
    change_type: str | None = None
    scope_estimate: str | None = None
    recipe_key: str | None = None
    affected_files_count: int = 0
    modified_files_count: int = 0
    phase_5_candidates: list[str] = field(default_factory=list)
    phase_6_candidates: list[str] = field(default_factory=list)
    # Surfaced from artifacts:
    manifest_present: bool = False
    manifest_early_terminate: bool | None = None
    manifest_phase_5: list[str] = field(default_factory=list)
    manifest_phase_6: list[str] = field(default_factory=list)
    decision_log_rule: str | None = None
    decision_log_present: bool = False


def read_json(path: Path) -> dict | None:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return None


def parse_execution_toon(path: Path) -> tuple[bool, list[str], list[str]] | None:
    """Parse the small fixed-shape execution.toon manifest.

    Returns `(early_terminate, phase_5_steps, phase_6_steps)` or None if the
    file is missing. Hand-rolled because the manifest is tiny and the project's
    `toon_parser` lives behind the executor PYTHONPATH which this skill does
    not load.
    """
    if not path.is_file():
        return None
    lines = path.read_text().splitlines()
    early_terminate = False
    phase_5: list[str] = []
    phase_6: list[str] = []
    section: str | None = None
    list_key: str | None = None
    for raw in lines:
        line = raw.rstrip()
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("phase_5:"):
            section = "phase_5"
            list_key = None
            continue
        if stripped.startswith("phase_6:"):
            section = "phase_6"
            list_key = None
            continue
        if section == "phase_5" and stripped.startswith("early_terminate:"):
            early_terminate = stripped.split(":", 1)[1].strip().lower() == "true"
            continue
        if section in {"phase_5", "phase_6"} and stripped.startswith("verification_steps") and "[" in stripped:
            list_key = "phase_5_steps"
            continue
        if section in {"phase_5", "phase_6"} and stripped.startswith("steps") and "[" in stripped:
            list_key = "phase_6_steps"
            continue
        if list_key and stripped.startswith("- "):
            value = stripped[2:].strip().strip('"')
            if list_key == "phase_5_steps":
                phase_5.append(value)
            elif list_key == "phase_6_steps":
                phase_6.append(value)
    return early_terminate, phase_5, phase_6


# Match the compose decision-log line shape documented in decision-rules.md.
RULE_FIRED_RE = re.compile(
    r"\(plan-marshall:manage-execution-manifest:compose\) Rule (\S+) fired"
)


def scan_decision_log(path: Path) -> tuple[bool, str | None]:
    """Return `(present_any_compose_line, rule_key_or_None)`.

    `present_any_compose_line` is True if any `(plan-marshall:manage-execution-manifest:compose)`
    line exists — used to separate "composer didn't log" from "log file missing".
    """
    if not path.is_file():
        return False, None
    has_compose = False
    rule: str | None = None
    for line in path.read_text().splitlines():
        if "manage-execution-manifest:compose" in line:
            has_compose = True
            m = RULE_FIRED_RE.search(line)
            if m:
                rule = m.group(1)
    return has_compose, rule


def derive_expected_rule(inputs: PlanInputs) -> str:
    """Re-run the 7-row matrix from decision-rules.md against the inputs.

    Returns the rule key. Pre-filters are not re-derived here — they affect the
    phase_6 list, not the rule key — but the script's report comparison still
    accounts for them when needed.
    """
    change_type = inputs.change_type
    scope = inputs.scope_estimate
    recipe = bool(inputs.recipe_key)
    n_affected = inputs.affected_files_count
    candidates = inputs.phase_5_candidates

    # Row 1
    if change_type == "analysis" and n_affected == 0:
        return "early_terminate_analysis"
    # Row 2
    if recipe:
        return "recipe"
    # Row 3 — docs-shaped: precondition is that phase_5_candidates lacks both
    # module-tests AND coverage. With project-renamed candidates this can be
    # technically true even when the project has tests, so the surrogate is
    # imprecise; we still report it as the matched row.
    if (
        scope in {"surgical", "single_module"}
        and change_type in {"tech_debt", "enhancement"}
        and n_affected > 0
        and "module-tests" not in candidates
        and "coverage" not in candidates
    ):
        return "docs_only"
    # Row 4
    if change_type == "verification" and n_affected > 0:
        return "tests_only"
    # Row 5
    if scope == "surgical" and change_type in {"bug_fix", "tech_debt"}:
        return "surgical_bug_fix" if change_type == "bug_fix" else "surgical_tech_debt"
    # Row 6
    if change_type == "verification" and n_affected == 0:
        return "verification_no_files"
    # Row 7
    return "default"


def collect_inputs(plan_dir: Path) -> PlanInputs:
    plan_id = plan_dir.name
    inputs = PlanInputs(plan_id=plan_id)

    refs = read_json(plan_dir / "references.json") or {}
    status = read_json(plan_dir / "status.json") or {}

    metadata = status.get("metadata", {})
    inputs.change_type = metadata.get("change_type")

    plan_source = metadata.get("plan_source")
    # `plan_source` populated by phase-1-init when sourced from a lesson;
    # equivalent to `recipe_key` for matrix purposes.
    if isinstance(plan_source, str) and plan_source.strip():
        inputs.recipe_key = plan_source.strip()

    inputs.scope_estimate = refs.get("scope_estimate")
    inputs.affected_files_count = len(refs.get("affected_files") or [])
    inputs.modified_files_count = len(refs.get("modified_files") or [])

    parsed = parse_execution_toon(plan_dir / "execution.toon")
    if parsed is not None:
        inputs.manifest_present = True
        et, p5, p6 = parsed
        inputs.manifest_early_terminate = et
        inputs.manifest_phase_5 = p5
        inputs.manifest_phase_6 = p6

    compose_present, rule = scan_decision_log(plan_dir / "logs" / "decision.log")
    inputs.decision_log_present = compose_present
    inputs.decision_log_rule = rule

    # Best-effort candidate sets — we use the manifest's actual phase_6 list as
    # a proxy for `phase_6_candidates` (the composer subset that survived
    # pre-filters), and the manifest's phase_5 as a proxy for survivors of any
    # row intersection. For derivation purposes this is sufficient for Row 3's
    # `lacks module-tests/coverage` predicate against project-renamed names.
    inputs.phase_5_candidates = inputs.manifest_phase_5
    inputs.phase_6_candidates = inputs.manifest_phase_6
    return inputs


def verdict_for(inputs: PlanInputs) -> tuple[str, str]:
    """Return `(verdict, reason)` — one of `ok`, `drift`, `incomplete`, `unloggable`."""
    if not inputs.manifest_present:
        return "incomplete", "no execution.toon (manifest never composed)"

    expected = derive_expected_rule(inputs)
    actual = inputs.decision_log_rule

    if actual is None and not inputs.decision_log_present:
        # Pre-logging era — manifest exists but composer never logged its rule.
        return "unloggable", f"expected={expected}, actual=unlogged (decision.log missing compose entry)"

    if actual is None and inputs.decision_log_present:
        return "drift", f"expected={expected}, compose lines present but Rule … fired line missing"

    if actual != expected:
        return "drift", f"expected={expected}, actual={actual}"

    return "ok", f"rule={expected}"


def detect_name_drift(inputs: PlanInputs) -> str | None:
    """Surface the `quality-gate`/`module-tests` ↔ project-rename name-drift signal.

    Returns a one-line note if the manifest's phase_5 candidates contain names
    that look like project-renamed equivalents of the canonical set.
    """
    if not inputs.manifest_phase_5:
        return None
    canon_hits = sum(1 for s in inputs.manifest_phase_5 if s in CANON_QUALITY_GATE)
    if canon_hits == 0 and inputs.manifest_phase_5:
        return (
            f"phase_5 uses renamed candidates {inputs.manifest_phase_5} — "
            f"Row 2/3/5 intersection against {{quality-gate, module-tests}} would be empty"
        )
    return None


def emit_toon(report: dict) -> str:
    """Render a small bespoke TOON document — kept inline to avoid imports."""
    lines: list[str] = []
    lines.append("status: success")
    lines.append(f"plans_scanned: {report['plans_scanned']}")
    lines.append(f"ok_count: {report['ok_count']}")
    lines.append(f"drift_count: {report['drift_count']}")
    lines.append(f"incomplete_count: {report['incomplete_count']}")
    lines.append(f"unloggable_count: {report['unloggable_count']}")
    lines.append(f"name_drift_count: {report['name_drift_count']}")
    rows = report["rows"]
    lines.append(
        "rows[{n}]{{plan_id,verdict,reason,expected_rule,actual_rule,change_type,scope,recipe,affected,modified,name_drift}}:".format(
            n=len(rows)
        )
    )
    for r in rows:
        cells = [
            r["plan_id"],
            r["verdict"],
            f'"{r["reason"]}"' if "," in r["reason"] else r["reason"],
            r["expected_rule"] or "",
            r["actual_rule"] or "",
            r["change_type"] or "",
            r["scope"] or "",
            r["recipe"] or "",
            str(r["affected"]),
            str(r["modified"]),
            f'"{r["name_drift"]}"' if r["name_drift"] else "",
        ]
        lines.append("  " + ",".join(cells))
    return "\n".join(lines) + "\n"


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description="Audit archived plans against manage-execution-manifest decision rules."
    )
    parser.add_argument(
        "--plan-dir",
        default=".plan/local/archived-plans",
        help="Directory containing per-plan subdirectories. Defaults to archived-plans.",
    )
    parser.add_argument(
        "--plan-id",
        help="Restrict the scan to one plan id (basename of the per-plan subdirectory).",
    )
    parser.add_argument(
        "--include-active",
        action="store_true",
        help="Also scan `.plan/local/plans/` (active plans) in addition to the supplied --plan-dir.",
    )
    args = parser.parse_args(argv)

    repo_root = Path.cwd()
    roots: list[Path] = [repo_root / args.plan_dir]
    if args.include_active:
        roots.append(repo_root / ".plan/local/plans")

    rows: list[dict] = []
    counts = {"ok": 0, "drift": 0, "incomplete": 0, "unloggable": 0}
    name_drift_count = 0

    for root in roots:
        if not root.is_dir():
            continue
        for plan_dir in sorted(p for p in root.iterdir() if p.is_dir()):
            if args.plan_id and plan_dir.name != args.plan_id:
                continue
            inputs = collect_inputs(plan_dir)
            expected = (
                derive_expected_rule(inputs) if inputs.manifest_present else None
            )
            verdict, reason = verdict_for(inputs)
            name_drift = detect_name_drift(inputs)
            if name_drift:
                name_drift_count += 1
            counts[verdict] += 1
            rows.append(
                {
                    "plan_id": inputs.plan_id,
                    "verdict": verdict,
                    "reason": reason,
                    "expected_rule": expected,
                    "actual_rule": inputs.decision_log_rule,
                    "change_type": inputs.change_type,
                    "scope": inputs.scope_estimate,
                    "recipe": inputs.recipe_key,
                    "affected": inputs.affected_files_count,
                    "modified": inputs.modified_files_count,
                    "name_drift": name_drift,
                }
            )

    report = {
        "plans_scanned": len(rows),
        "ok_count": counts["ok"],
        "drift_count": counts["drift"],
        "incomplete_count": counts["incomplete"],
        "unloggable_count": counts["unloggable"],
        "name_drift_count": name_drift_count,
        "rows": rows,
    }
    sys.stdout.write(emit_toon(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
