#!/usr/bin/env python3
"""Audit archived plans across nine retrospective checks.

Walks `.plan/local/archived-plans/{plan_id}/` directories and, per plan, runs a
suite of deterministic checks:

- `execution-context-manifest` — re-runs the 7-row decision matrix from
  `manage-execution-manifest/standards/decision-rules.md` against the plan's
  inputs and compares the derived rule key + manifest shape to what was
  persisted in `execution.toon` / `logs/decision.log`.
- `quality-verification-report` — surfaces findings present, proposed lessons,
  and whether each proposed lesson was already filed (lessons-corpus
  cross-check).
- `metrics` — detects disproportionate token usage, incomplete recordings,
  impossible values (worked > wall, negative idle), and optimization signals.
- `scope-estimate-accuracy` — compares declared `references.json::scope_estimate`
  against the actual affected/modified file count.
- `pr-merge-velocity` — computes PR open-to-merge duration and flags long
  review cycles.
- `task-count-efficiency` — counts `tasks/TASK-*.json` and flags under- or
  over-decomposition relative to the deliverable count.
- `recurring-pattern-detector` (cross-plan) — aggregates finding signatures and
  surfaces any appearing in N≥3 plans as a systemic signal.
- `token-efficiency-trend` (cross-plan) — orders plans chronologically and
  detects a sustained upward trend in tokens-per-phase.

Each check emits one bespoke-TOON block. Intended consumer:
`/audit-archived-plan-retrospectives`.

The script is deterministic by design — per
`extension-api/standards/dispatch-granularity.md` Heuristic 1 every check's core
is a boolean/arithmetic predicate over file-derived inputs, so it lives in a
script rather than a dispatch envelope. The only mutating operation is the
explicitly-confirmed dormation move (`--dormate {plan_id} --confirmed`), which
relocates a reviewed plan to `.plan/temp/dormated-plans/`; without `--confirmed`
the move function is inert.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast

# ---------------------------------------------------------------------------
# Check registry
# ---------------------------------------------------------------------------

CHECK_NAMES = [
    "execution-context-manifest",
    "quality-verification-report",
    "metrics",
    "recurring-pattern-detector",
    "token-efficiency-trend",
    "scope-estimate-accuracy",
    "pr-merge-velocity",
    "task-count-efficiency",
]

# Cross-plan checks aggregate over the full scanned corpus rather than emitting
# one row per plan.
CROSS_PLAN_CHECKS = {"recurring-pattern-detector", "token-efficiency-trend"}

# Canonical phase-5 step names the standard intersects against in Rows 2/3/5.
# Projects that rename these (e.g. `quality_check` instead of `quality-gate`)
# will see Row 5's intersection drop to empty — flagged in the report as a
# `name_drift` signal.
CANON_QUALITY_GATE = {"quality-gate", "module-tests"}
CANON_COVERAGE = "coverage"

# Recurring-pattern systemic threshold (request: 3+ occurrences).
SYSTEMIC_THRESHOLD = 3

# PR review-cycle threshold (hours) above which a plan is flagged slow.
PR_SLOW_REVIEW_HOURS = 24.0

# Disproportionate-token threshold: a phase consuming more than this share of
# the plan's total tokens is flagged.
PHASE_TOKEN_SHARE_THRESHOLD = 0.45

# Scope-estimate file-count bands. Maps a declared scope_estimate to the
# inclusive [low, high] band of expected total touched files. `None` upper
# bound means "unbounded".
SCOPE_FILE_BANDS: dict[str, tuple[int, int | None]] = {
    "surgical": (1, 3),
    "single_module": (1, 15),
    "multi_module": (5, None),
}

# Task-count efficiency: expected tasks-per-deliverable band. Outside this band
# the plan is flagged under- or over-decomposed.
TASKS_PER_DELIVERABLE_LOW = 0.5
TASKS_PER_DELIVERABLE_HIGH = 4.0


# ---------------------------------------------------------------------------
# Shared file readers
# ---------------------------------------------------------------------------


def read_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        return cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))
    except (json.JSONDecodeError, OSError):
        return None


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    out: list[dict[str, Any]] = []
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(obj, dict):
                out.append(obj)
    except OSError:
        return []
    return out


def parse_execution_toon(path: Path) -> tuple[bool, list[str], list[str]] | None:
    """Parse the small fixed-shape execution.toon manifest.

    Returns `(early_terminate, phase_5_steps, phase_6_steps)` or None if the
    file is missing. Hand-rolled because the manifest is tiny and the project's
    `toon_parser` lives behind the executor PYTHONPATH which this skill does
    not load.
    """
    if not path.is_file():
        return None
    lines = path.read_text(encoding="utf-8").splitlines()
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


@dataclass
class PhaseMetrics:
    phase: str
    total_tokens: int = 0
    duration_seconds: float = 0.0
    idle_duration_ms: float = 0.0
    agent_duration_seconds: float = 0.0


def parse_metrics_toon(path: Path) -> list[PhaseMetrics]:
    """Parse the INI-shaped `work/metrics.toon` per-phase block.

    The file uses `[phase-name]` section headers followed by `  key: value`
    lines. Hand-rolled to avoid the executor PYTHONPATH dependency.
    """
    if not path.is_file():
        return []
    phases: list[PhaseMetrics] = []
    current: PhaseMetrics | None = None
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return []
    for raw in text.splitlines():
        stripped = raw.strip()
        if not stripped:
            continue
        if stripped.startswith("[") and stripped.endswith("]"):
            if current is not None:
                phases.append(current)
            current = PhaseMetrics(phase=stripped[1:-1])
            continue
        if current is None or ":" not in stripped:
            continue
        key, _, value = stripped.partition(":")
        key = key.strip()
        value = value.strip()
        if key == "total_tokens":
            current.total_tokens = _to_int(value)
        elif key == "duration_seconds":
            current.duration_seconds = _to_float(value)
        elif key == "idle_duration_ms":
            current.idle_duration_ms = _to_float(value)
        elif key == "agent_duration_seconds":
            current.agent_duration_seconds = _to_float(value)
    if current is not None:
        phases.append(current)
    return phases


def _to_int(value: str) -> int:
    try:
        return int(float(value))
    except ValueError:
        return 0


def _to_float(value: str) -> float:
    try:
        return float(value)
    except ValueError:
        return 0.0


# Match the compose decision-log line shape documented in decision-rules.md.
RULE_FIRED_RE = re.compile(
    r"\(plan-marshall:manage-execution-manifest:compose\) Rule (\S+) fired"
)


def scan_decision_log(path: Path) -> tuple[bool, str | None]:
    """Return `(present_any_compose_line, rule_key_or_None)`.

    `present_any_compose_line` is True if any
    `(plan-marshall:manage-execution-manifest:compose)` line exists — used to
    separate "composer didn't log" from "log file missing".
    """
    if not path.is_file():
        return False, None
    has_compose = False
    rule: str | None = None
    for line in path.read_text(encoding="utf-8").splitlines():
        if "manage-execution-manifest:compose" in line:
            has_compose = True
            m = RULE_FIRED_RE.search(line)
            if m:
                rule = m.group(1)
    return has_compose, rule


def parse_toon_scalar(path: Path, key: str) -> str | None:
    """Read a top-level `key: value` scalar from a flat TOON file."""
    if not path.is_file():
        return None
    prefix = f"{key}:"
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if stripped.startswith(prefix):
                return stripped[len(prefix):].strip().strip('"')
    except OSError:
        return None
    return None


# ---------------------------------------------------------------------------
# Per-plan input collection
# ---------------------------------------------------------------------------


@dataclass
class PlanInputs:
    plan_id: str
    plan_dir: Path
    change_type: str | None = None
    scope_estimate: str | None = None
    recipe_key: str | None = None
    affected_files_count: int = 0
    modified_files_count: int = 0
    phase_5_candidates: list[str] = field(default_factory=list)
    phase_6_candidates: list[str] = field(default_factory=list)
    manifest_present: bool = False
    manifest_early_terminate: bool | None = None
    manifest_phase_5: list[str] = field(default_factory=list)
    manifest_phase_6: list[str] = field(default_factory=list)
    decision_log_rule: str | None = None
    decision_log_present: bool = False


def collect_inputs(plan_dir: Path) -> PlanInputs:
    plan_id = plan_dir.name
    inputs = PlanInputs(plan_id=plan_id, plan_dir=plan_dir)

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

    # Best-effort candidate sets — the manifest's actual phase_6 list is a proxy
    # for `phase_6_candidates` and phase_5 for survivors of any row
    # intersection. Sufficient for Row 3's `lacks module-tests/coverage`
    # predicate against project-renamed names.
    inputs.phase_5_candidates = inputs.manifest_phase_5
    inputs.phase_6_candidates = inputs.manifest_phase_6
    return inputs


# ---------------------------------------------------------------------------
# Check: execution-context-manifest
# ---------------------------------------------------------------------------


def derive_expected_rule(inputs: PlanInputs) -> str:
    """Re-run the 7-row matrix from decision-rules.md against the inputs."""
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
    # Row 3 — docs-shaped
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


def verdict_for(inputs: PlanInputs) -> tuple[str, str]:
    """Return `(verdict, reason)` — `ok`, `drift`, `incomplete`, `unloggable`."""
    if not inputs.manifest_present:
        return "incomplete", "no execution.toon (manifest never composed)"

    expected = derive_expected_rule(inputs)
    actual = inputs.decision_log_rule

    if actual is None and not inputs.decision_log_present:
        return "unloggable", f"expected={expected}, actual=unlogged (decision.log missing compose entry)"
    if actual is None and inputs.decision_log_present:
        return "drift", f"expected={expected}, compose lines present but Rule … fired line missing"
    if actual != expected:
        return "drift", f"expected={expected}, actual={actual}"
    return "ok", f"rule={expected}"


def detect_name_drift(inputs: PlanInputs) -> str | None:
    if not inputs.manifest_phase_5:
        return None
    canon_hits = sum(1 for s in inputs.manifest_phase_5 if s in CANON_QUALITY_GATE)
    if canon_hits == 0 and inputs.manifest_phase_5:
        return (
            f"phase_5 uses renamed candidates {inputs.manifest_phase_5} — "
            f"Row 2/3/5 intersection against {{quality-gate, module-tests}} would be empty"
        )
    return None


def check_execution_manifest(inputs: PlanInputs) -> dict[str, Any]:
    expected = derive_expected_rule(inputs) if inputs.manifest_present else None
    verdict, reason = verdict_for(inputs)
    name_drift = detect_name_drift(inputs)
    return {
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


# ---------------------------------------------------------------------------
# Check: quality-verification-report
# ---------------------------------------------------------------------------

# Extract a JSON code block from the markdown report and a "Proposed Lessons"
# section.
_JSON_BLOCK_RE = re.compile(r"```json\s*(.*?)```", re.DOTALL)


def _lessons_corpus_signatures(repo_root: Path) -> list[str]:
    """Read titles from the lessons-learned corpus for the filed cross-check."""
    corpus = repo_root / ".plan/local/lessons-learned"
    sigs: list[str] = []
    if not corpus.is_dir():
        return sigs
    for md in corpus.glob("*.md"):
        try:
            text = md.read_text(encoding="utf-8")
        except OSError:
            continue
        # First markdown heading or `title:` frontmatter is the signature.
        for line in text.splitlines():
            s = line.strip()
            if s.startswith("# "):
                sigs.append(s[2:].strip().lower())
                break
            if s.lower().startswith("title:"):
                sigs.append(s.split(":", 1)[1].strip().strip('"').lower())
                break
    return sigs


def _signature_filed(signature: str, corpus_sigs: list[str]) -> bool:
    sig = signature.strip().lower()
    if not sig:
        return False
    for existing in corpus_sigs:
        if sig in existing or existing in sig:
            return True
    return False


def check_quality_verification(inputs: PlanInputs, corpus_sigs: list[str]) -> dict[str, Any]:
    report = inputs.plan_dir / "quality-verification-report.md"
    findings_count = 0
    proposed: list[str] = []
    if report.is_file():
        try:
            text = report.read_text(encoding="utf-8")
        except OSError:
            text = ""
        for block in _JSON_BLOCK_RE.findall(text):
            try:
                obj = json.loads(block)
            except json.JSONDecodeError:
                continue
            findings = obj.get("findings")
            if isinstance(findings, list):
                findings_count += len(findings)
            lessons = obj.get("proposed_lessons") or obj.get("lessons")
            if isinstance(lessons, list):
                for item in lessons:
                    if isinstance(item, dict):
                        title = item.get("title") or item.get("signature") or item.get("detail")
                        if isinstance(title, str):
                            proposed.append(title)
                    elif isinstance(item, str):
                        proposed.append(item)

    # Add findings from the artifacts/findings/*.jsonl set.
    findings_dir = inputs.plan_dir / "artifacts" / "findings"
    if findings_dir.is_dir():
        for jsonl in findings_dir.glob("*.jsonl"):
            findings_count += len(read_jsonl(jsonl))

    unfiled = [p for p in proposed if not _signature_filed(p, corpus_sigs)]
    return {
        "plan_id": inputs.plan_id,
        "findings_present": findings_count,
        "proposed_lessons": len(proposed),
        "unfiled_lessons": len(unfiled),
        "unfiled_signatures": unfiled,
    }


# ---------------------------------------------------------------------------
# Check: metrics
# ---------------------------------------------------------------------------


def check_metrics(inputs: PlanInputs) -> dict[str, Any]:
    metrics_path = inputs.plan_dir / "work" / "metrics.toon"
    phases = parse_metrics_toon(metrics_path)
    anomalies: list[str] = []

    if not phases:
        return {
            "plan_id": inputs.plan_id,
            "phases_recorded": 0,
            "disproportionate_token": "",
            "incomplete_recording": "true",
            "impossible_value": "",
            "optimization_signal": "",
            "anomalies": ["no metrics.toon recorded"],
        }

    total_tokens = sum(p.total_tokens for p in phases)

    # (a) Disproportionate phase token usage.
    dispro = ""
    if total_tokens > 0:
        for p in phases:
            share = p.total_tokens / total_tokens
            if share >= PHASE_TOKEN_SHARE_THRESHOLD:
                dispro = f"{p.phase}={share:.0%}"
                anomalies.append(f"{p.phase} consumed {share:.0%} of total tokens")
                break

    # (b) Incomplete recordings: zero-token phase that should carry data.
    incomplete = ""
    zero_phases = [p.phase for p in phases if p.total_tokens == 0]
    if zero_phases:
        incomplete = ",".join(zero_phases)
        anomalies.append(f"zero-token phases: {incomplete}")

    # (c) Impossible values: worked > wall-clock, or negative idle.
    impossible = ""
    for p in phases:
        worked = p.agent_duration_seconds
        wall = p.duration_seconds
        if wall > 0 and worked > wall + 1.0:
            impossible = f"{p.phase}:worked>{wall:.0f}s"
            anomalies.append(f"{p.phase} worked {worked:.0f}s > wall {wall:.0f}s")
            break
        if p.idle_duration_ms < 0:
            impossible = f"{p.phase}:negative_idle"
            anomalies.append(f"{p.phase} negative idle")
            break

    # (d) Optimization signal: a phase whose token-per-second ratio is an
    # outlier (>= 3x the median non-zero phase ratio).
    optimization = ""
    ratios = [
        (p.phase, p.total_tokens / p.duration_seconds)
        for p in phases
        if p.duration_seconds > 0 and p.total_tokens > 0
    ]
    if len(ratios) >= 3:
        sorted_ratios = sorted(r for _, r in ratios)
        median = sorted_ratios[len(sorted_ratios) // 2]
        if median > 0:
            for phase, ratio in ratios:
                if ratio >= 3 * median:
                    optimization = f"{phase}:{ratio:.0f}tok/s"
                    anomalies.append(f"{phase} token/s ratio outlier ({ratio:.0f})")
                    break

    return {
        "plan_id": inputs.plan_id,
        "phases_recorded": len(phases),
        "disproportionate_token": dispro,
        "incomplete_recording": incomplete,
        "impossible_value": impossible,
        "optimization_signal": optimization,
        "anomalies": anomalies,
    }


# ---------------------------------------------------------------------------
# Check: scope-estimate-accuracy
# ---------------------------------------------------------------------------


def check_scope_estimate(inputs: PlanInputs) -> dict[str, Any]:
    declared = inputs.scope_estimate
    # Actual touched-file count: prefer modified_files (post-execution truth),
    # fall back to affected_files (planned).
    actual = inputs.modified_files_count or inputs.affected_files_count
    band = SCOPE_FILE_BANDS.get(declared or "", None)
    mismatch = ""
    if band is not None:
        low, high = band
        if actual < low or (high is not None and actual > high):
            mismatch = f"declared={declared} band=[{low},{high if high is not None else '∞'}] actual={actual}"
    elif declared:
        mismatch = f"declared={declared} (no band mapping) actual={actual}"
    return {
        "plan_id": inputs.plan_id,
        "declared_scope": declared or "",
        "actual_file_count": actual,
        "mismatch": mismatch,
    }


# ---------------------------------------------------------------------------
# Check: pr-merge-velocity
# ---------------------------------------------------------------------------

_ISO_RE = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}")


def _parse_iso_seconds(value: str) -> float | None:
    """Parse an ISO-8601 UTC timestamp into epoch seconds (no tz lib)."""
    m = _ISO_RE.search(value)
    if not m:
        return None
    import calendar
    import time

    try:
        struct = time.strptime(m.group(0), "%Y-%m-%dT%H:%M:%S")
        return float(calendar.timegm(struct))
    except ValueError:
        return None


def check_pr_merge_velocity(inputs: PlanInputs) -> dict[str, Any]:
    ci_runs = inputs.plan_dir / "artifacts" / "ci-runs"
    open_ts: float | None = None
    merge_ts: float | None = None
    pr_number = ""
    if ci_runs.is_dir():
        manifests = sorted(ci_runs.glob("*/manifest.toon"))
        for manifest in manifests:
            num = parse_toon_scalar(manifest, "pr_number")
            if num:
                pr_number = num
            fetched = parse_toon_scalar(manifest, "fetched_at")
            if fetched:
                ts = _parse_iso_seconds(fetched)
                if ts is not None:
                    if open_ts is None or ts < open_ts:
                        open_ts = ts
                    if merge_ts is None or ts > merge_ts:
                        merge_ts = ts
    if not pr_number or open_ts is None or merge_ts is None:
        return {
            "plan_id": inputs.plan_id,
            "pr_number": pr_number or "",
            "elapsed_hours": "",
            "flagged": "",
            "applicable": "false",
        }
    elapsed_hours = (merge_ts - open_ts) / 3600.0
    flagged = "true" if elapsed_hours > PR_SLOW_REVIEW_HOURS else ""
    return {
        "plan_id": inputs.plan_id,
        "pr_number": pr_number,
        "elapsed_hours": f"{elapsed_hours:.1f}",
        "flagged": flagged,
        "applicable": "true",
    }


# ---------------------------------------------------------------------------
# Check: task-count-efficiency
# ---------------------------------------------------------------------------


def _deliverable_count(inputs: PlanInputs) -> int:
    refs = read_json(inputs.plan_dir / "references.json") or {}
    deliverables = refs.get("deliverables")
    if isinstance(deliverables, list):
        return len(deliverables)
    # Fall back to distinct deliverable ids referenced by tasks.
    tasks_dir = inputs.plan_dir / "tasks"
    seen: set[Any] = set()
    if tasks_dir.is_dir():
        for tf in tasks_dir.glob("TASK-*.json"):
            obj = read_json(tf) or {}
            if "deliverable" in obj:
                seen.add(obj["deliverable"])
    return len(seen)


def check_task_count(inputs: PlanInputs) -> dict[str, Any]:
    tasks_dir = inputs.plan_dir / "tasks"
    task_count = len(list(tasks_dir.glob("TASK-*.json"))) if tasks_dir.is_dir() else 0
    deliverables = _deliverable_count(inputs)
    outlier = ""
    if deliverables > 0:
        ratio = task_count / deliverables
        if ratio < TASKS_PER_DELIVERABLE_LOW:
            outlier = f"under_decomposed (ratio={ratio:.2f})"
        elif ratio > TASKS_PER_DELIVERABLE_HIGH:
            outlier = f"over_decomposed (ratio={ratio:.2f})"
    return {
        "plan_id": inputs.plan_id,
        "task_count": task_count,
        "deliverable_count": deliverables,
        "outlier": outlier,
    }


# ---------------------------------------------------------------------------
# Cross-plan: recurring-pattern-detector
# ---------------------------------------------------------------------------


def _finding_signature(obj: dict[str, Any]) -> str | None:
    title = obj.get("title") or obj.get("type")
    if isinstance(title, str) and title.strip():
        # Strip plan-specific suffixes after a colon to group by signature.
        return title.split(":", 1)[0].strip().lower()
    return None


def cross_recurring_pattern(all_inputs: list[PlanInputs]) -> dict[str, Any]:
    sig_to_plans: dict[str, set[str]] = {}
    for inputs in all_inputs:
        findings_dir = inputs.plan_dir / "artifacts" / "findings"
        if not findings_dir.is_dir():
            continue
        seen_in_plan: set[str] = set()
        for jsonl in findings_dir.glob("*.jsonl"):
            for obj in read_jsonl(jsonl):
                sig = _finding_signature(obj)
                if sig:
                    seen_in_plan.add(sig)
        for sig in seen_in_plan:
            sig_to_plans.setdefault(sig, set()).add(inputs.plan_id)

    systemic: list[dict[str, Any]] = [
        {
            "signature": sig,
            "occurrence_count": len(plans),
            "plan_ids": sorted(plans),
        }
        for sig, plans in sig_to_plans.items()
        if len(plans) >= SYSTEMIC_THRESHOLD
    ]
    systemic.sort(key=lambda r: (-int(r["occurrence_count"]), str(r["signature"])))
    return {
        "threshold": SYSTEMIC_THRESHOLD,
        "systemic_count": len(systemic),
        "rows": systemic,
    }


# ---------------------------------------------------------------------------
# Cross-plan: token-efficiency-trend
# ---------------------------------------------------------------------------

_DATE_PREFIX_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})")


def _plan_order_key(inputs: PlanInputs) -> str:
    m = _DATE_PREFIX_RE.match(inputs.plan_id)
    if m:
        return m.group(1) + inputs.plan_id
    status = read_json(inputs.plan_dir / "status.json") or {}
    created = status.get("plan", {}).get("created")
    if isinstance(created, str):
        return created
    return inputs.plan_id


def cross_token_trend(all_inputs: list[PlanInputs]) -> dict[str, Any]:
    series: list[dict[str, Any]] = []
    for inputs in sorted(all_inputs, key=_plan_order_key):
        phases = parse_metrics_toon(inputs.plan_dir / "work" / "metrics.toon")
        if not phases:
            continue
        total = sum(p.total_tokens for p in phases)
        per_phase = total / len(phases) if phases else 0
        series.append(
            {
                "plan_id": inputs.plan_id,
                "phases": len(phases),
                "total_tokens": total,
                "tokens_per_phase": int(per_phase),
            }
        )

    # Regression rule: sustained upward trend — the last third's mean
    # tokens-per-phase exceeds the first third's mean by > 25%.
    regression = ""
    if len(series) >= 3:
        third = max(1, len(series) // 3)
        first_mean = sum(r["tokens_per_phase"] for r in series[:third]) / third
        last_mean = sum(r["tokens_per_phase"] for r in series[-third:]) / third
        if first_mean > 0 and last_mean > first_mean * 1.25:
            regression = (
                f"tokens/phase rose {first_mean:.0f} → {last_mean:.0f} "
                f"(+{(last_mean / first_mean - 1) * 100:.0f}%)"
            )
    return {
        "plans_in_series": len(series),
        "regression": regression,
        "rows": series,
    }


# ---------------------------------------------------------------------------
# Dormation move (the only mutating operation)
# ---------------------------------------------------------------------------


def dormate_plan(repo_root: Path, plan_id: str, confirmed: bool) -> dict[str, Any]:
    """Relocate an archived plan to `.plan/temp/dormated-plans/{plan_id}`.

    Inert unless `confirmed` is True — the interactive confirmation itself is
    owned by the SKILL.md LLM body via AskUserQuestion; this function performs
    only the confirmed move.
    """
    if not confirmed:
        return {
            "status": "refused",
            "plan_id": plan_id,
            "reason": "dormation requires --confirmed; the move function is inert without it",
        }
    src = repo_root / ".plan/local/archived-plans" / plan_id
    if not src.is_dir():
        return {
            "status": "error",
            "plan_id": plan_id,
            "reason": f"source not found: {src}",
        }
    dest_root = repo_root / ".plan/temp/dormated-plans"
    dest_root.mkdir(parents=True, exist_ok=True)
    dest = dest_root / plan_id
    if dest.exists():
        return {
            "status": "error",
            "plan_id": plan_id,
            "reason": f"destination already exists: {dest}",
        }
    shutil.move(str(src), str(dest))
    return {
        "status": "success",
        "plan_id": plan_id,
        "moved_to": str(dest),
    }


# ---------------------------------------------------------------------------
# TOON emission
# ---------------------------------------------------------------------------


def _cell(value: Any) -> str:
    """Render a single TOON table cell, quoting when it contains a comma."""
    if value is None:
        return ""
    s = str(value)
    return f'"{s}"' if "," in s or '"' in s else s


def emit_manifest_block(rows: list[dict[str, Any]]) -> str:
    counts = {"ok": 0, "drift": 0, "incomplete": 0, "unloggable": 0}
    name_drift_count = 0
    for r in rows:
        counts[r["verdict"]] = counts.get(r["verdict"], 0) + 1
        if r["name_drift"]:
            name_drift_count += 1
    out = ["check: execution-context-manifest", "status: success"]
    out.append(f"plans_scanned: {len(rows)}")
    out.append(f"ok_count: {counts['ok']}")
    out.append(f"drift_count: {counts['drift']}")
    out.append(f"incomplete_count: {counts['incomplete']}")
    out.append(f"unloggable_count: {counts['unloggable']}")
    out.append(f"name_drift_count: {name_drift_count}")
    out.append(
        f"rows[{len(rows)}]{{plan_id,verdict,reason,expected_rule,actual_rule,change_type,scope,recipe,affected,modified,name_drift}}:"
    )
    for r in rows:
        out.append(
            "  "
            + ",".join(
                _cell(c)
                for c in [
                    r["plan_id"],
                    r["verdict"],
                    r["reason"],
                    r["expected_rule"] or "",
                    r["actual_rule"] or "",
                    r["change_type"] or "",
                    r["scope"] or "",
                    r["recipe"] or "",
                    r["affected"],
                    r["modified"],
                    r["name_drift"] or "",
                ]
            )
        )
    return "\n".join(out) + "\n"


def emit_table_block(check: str, columns: list[str], rows: list[dict[str, Any]]) -> str:
    out = [f"check: {check}", "status: success", f"plans_scanned: {len(rows)}"]
    out.append(f"rows[{len(rows)}]{{{','.join(columns)}}}:")
    for r in rows:
        out.append("  " + ",".join(_cell(r.get(col, "")) for col in columns))
    return "\n".join(out) + "\n"


def emit_recurring_block(result: dict[str, Any]) -> str:
    rows = result["rows"]
    out = [
        "check: recurring-pattern-detector",
        "status: success",
        f"threshold: {result['threshold']}",
        f"systemic_count: {result['systemic_count']}",
        f"rows[{len(rows)}]{{signature,occurrence_count,plan_ids}}:",
    ]
    for r in rows:
        out.append(
            "  "
            + ",".join(
                _cell(c)
                for c in [r["signature"], r["occurrence_count"], ";".join(r["plan_ids"])]
            )
        )
    return "\n".join(out) + "\n"


def emit_trend_block(result: dict[str, Any]) -> str:
    rows = result["rows"]
    out = [
        "check: token-efficiency-trend",
        "status: success",
        f"plans_in_series: {result['plans_in_series']}",
        f"regression: {_cell(result['regression'])}",
        f"rows[{len(rows)}]{{plan_id,phases,total_tokens,tokens_per_phase}}:",
    ]
    for r in rows:
        out.append(
            "  "
            + ",".join(
                _cell(c)
                for c in [r["plan_id"], r["phases"], r["total_tokens"], r["tokens_per_phase"]]
            )
        )
    return "\n".join(out) + "\n"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def run_checks(all_inputs: list[PlanInputs], selected: list[str], repo_root: Path) -> str:
    corpus_sigs = _lessons_corpus_signatures(repo_root)
    blocks: list[str] = []

    if "execution-context-manifest" in selected:
        rows = [check_execution_manifest(i) for i in all_inputs]
        blocks.append(emit_manifest_block(rows))

    if "quality-verification-report" in selected:
        rows = [check_quality_verification(i, corpus_sigs) for i in all_inputs]
        blocks.append(
            emit_table_block(
                "quality-verification-report",
                ["plan_id", "findings_present", "proposed_lessons", "unfiled_lessons", "unfiled_signatures"],
                [{**r, "unfiled_signatures": ";".join(r["unfiled_signatures"])} for r in rows],
            )
        )

    if "metrics" in selected:
        rows = [check_metrics(i) for i in all_inputs]
        blocks.append(
            emit_table_block(
                "metrics",
                [
                    "plan_id",
                    "phases_recorded",
                    "disproportionate_token",
                    "incomplete_recording",
                    "impossible_value",
                    "optimization_signal",
                ],
                rows,
            )
        )

    if "scope-estimate-accuracy" in selected:
        rows = [check_scope_estimate(i) for i in all_inputs]
        blocks.append(
            emit_table_block(
                "scope-estimate-accuracy",
                ["plan_id", "declared_scope", "actual_file_count", "mismatch"],
                rows,
            )
        )

    if "pr-merge-velocity" in selected:
        rows = [check_pr_merge_velocity(i) for i in all_inputs]
        blocks.append(
            emit_table_block(
                "pr-merge-velocity",
                ["plan_id", "pr_number", "elapsed_hours", "flagged", "applicable"],
                rows,
            )
        )

    if "task-count-efficiency" in selected:
        rows = [check_task_count(i) for i in all_inputs]
        blocks.append(
            emit_table_block(
                "task-count-efficiency",
                ["plan_id", "task_count", "deliverable_count", "outlier"],
                rows,
            )
        )

    if "recurring-pattern-detector" in selected:
        blocks.append(emit_recurring_block(cross_recurring_pattern(all_inputs)))

    if "token-efficiency-trend" in selected:
        blocks.append(emit_trend_block(cross_token_trend(all_inputs)))

    return "\n".join(blocks)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description="Audit archived plans across nine retrospective checks."
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
        help="Also scan `.plan/local/plans/` (active plans) in addition to --plan-dir.",
    )
    parser.add_argument(
        "--check",
        choices=CHECK_NAMES,
        help="Run a single check instead of all. Defaults to every check.",
    )
    parser.add_argument(
        "--dormate",
        metavar="PLAN_ID",
        help="Relocate an archived plan to `.plan/temp/dormated-plans/`. Inert (refused, exit 0) unless --confirmed is also passed.",
    )
    parser.add_argument(
        "--confirmed",
        action="store_true",
        help="Confirm the destructive dormation move (no-op without --dormate).",
    )
    args = parser.parse_args(argv)

    repo_root = Path.cwd()

    if args.dormate:
        result = dormate_plan(repo_root, args.dormate, args.confirmed)
        out = ["operation: dormate", f"status: {result['status']}", f"plan_id: {result['plan_id']}"]
        if "moved_to" in result:
            out.append(f"moved_to: {result['moved_to']}")
        if "reason" in result:
            out.append(f'reason: "{result["reason"]}"')
        sys.stdout.write("\n".join(out) + "\n")
        return 0 if result["status"] in {"success", "refused"} else 1

    roots: list[Path] = [repo_root / args.plan_dir]
    if args.include_active:
        roots.append(repo_root / ".plan/local/plans")

    all_inputs: list[PlanInputs] = []
    for root in roots:
        if not root.is_dir():
            continue
        for plan_dir in sorted(p for p in root.iterdir() if p.is_dir()):
            if args.plan_id and plan_dir.name != args.plan_id:
                continue
            all_inputs.append(collect_inputs(plan_dir))

    selected = [args.check] if args.check else list(CHECK_NAMES)
    sys.stdout.write(run_checks(all_inputs, selected, repo_root))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
