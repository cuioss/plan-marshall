#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Audit archived plans across twenty-two retrospective checks.

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
- `track-selection-accuracy` — reconstructs each plan's counterfactual "correct"
  planning lane from its realized signals (via the imported `evaluate_signals_pure`
  + S5 `_request_is_concrete` from the live planning-lane router — no threshold
  duplicated) and compares it against the lane/track the plan actually ran
  (`status.json::metadata.planning_lane`, `references.json::track`), emitting an
  OVER-TRACKED / UNDER-TRACKED / correct verdict per plan.
- `pr-merge-velocity` — computes PR open-to-merge duration and flags long
  review cycles.
- `task-count-efficiency` — counts `tasks/TASK-*.json` and flags under- or
  over-decomposition relative to the deliverable count.
- `recurring-pattern-detector` (cross-plan) — aggregates finding signatures and
  surfaces any appearing in N≥3 plans as a systemic signal.
- `token-efficiency-trend` (cross-plan) — orders plans chronologically and
  detects a sustained upward trend in tokens-per-phase.
- `global-log-analysis` (cross-plan) — parses the global `.plan/local/logs/`
  corpus (script-execution / work / decision logs), buckets by level, aggregates
  per notation+subcommand, and flags error/warning lines, slow calls,
  high-frequency callers, impossible/hang durations, and test-fixture leaks —
  each correlated to the archived-plan execution window it falls inside.
- `token-economics` (cross-plan) — joins each plan's per-phase `metrics.toon`
  tokens to `references.json` (scope_estimate, footprint) and
  `status.json::metadata` (change_type), computes per-plan token shares and
  efficiency ratios, derives corpus-relative anti-pattern thresholds (median /
  percentile over the live corpus, never hard-coded), and flags the
  token-economics anti-patterns catalogued in the canonical token-economics lesson
  (fixed-overhead floor, planning≫execute, phase-heavy outline/refine/finalize,
  big-spend-tiny-footprint, long sessions, and execute-metrics blindness).
- `quality-chain` (cross-plan) — classifies every `artifacts/findings/*.jsonl`
  finding by the QUALITY MECHANISM that caught it (build / self-review /
  auto-review / human-review) and the RESOLUTION it received (direct_fix /
  loop_back / rerun_flake / accepted / suppressed / pending / lesson), builds a
  per-plan mechanism×resolution matrix plus corpus totals, flags the chain
  anti-patterns (`build_pending_pile`, `auto_review_only`,
  `review_body_duplicate`, `no_qgate6`), and shift-left-tiers each
  `auto_review_only` finding against the
  `ext-self-review-plan-marshall` deterministic surfacer remit (Tier 1-4) so a
  finding the PR bot caught is graded by how completely the pre-submission
  structural review could have caught it first.
- `sequence-and-build-minimality` (cross-plan) — reconstructs each plan's
  call sequence from `logs/script-execution.log`, buckets the calls into phases
  by the `logs/work.log` `[DISPATCH] role=phase-N` timeline, classifies every
  `pyproject_build run` by duration (minimal `< build_minimal_seconds` / scoped /
  heavy `> build_heavy_seconds`), mines `work.log` for the actual build verb and
  scope (verify / module-tests scoped-vs-all / quality-gate / coverage /
  compile), and flags the redundancy / non-minimality anti-patterns
  (`build_churn`, `non_minimal_build`, `docs_only_build`, `ci_rerun`,
  `phase_reentry`, `arch_over_resolution`, `consecutive_dup`) catalogued in the
  build-minimality lessons. Carries three structural caveats (finalize-fold
  conflation, the verify-count-vs-heavy-duration upper-bound/floor pairing, and
  consecutive-dup over-counting) documented in the check sub-document.
- `input-integrity` (per-plan, corpus data_confidence summary) — the
  no-false-healthy FOUNDATION. Reports each plan's input presence/health
  (execution.toon / metrics.toon / references.json / tasks/ / artifacts/findings/
  / logs/script-execution.log) and flags `metrics_blind` (any zero-token phase
  that should carry data, especially 5-execute), `incomplete_lifecycle` (no
  5-execute or 6-finalize recorded), and `missing_dispatch_markers` (no
  `role=phase-N` lines in work.log). Emits a corpus `data_confidence` summary
  (fully-recorded / partial / blind counts) with the D1 severity column. The
  cross-check obligation: EVERY other check MUST consume this verdict and annotate
  rows derived from a `metrics_blind` plan as "floor, not truth" — a check may not
  claim "all healthy" over blind-input plans.
- `task-graph-redundancy` (per-plan) — reconstructs each plan's task graph from
  `tasks/TASK-*.json` as adjacency over step targets and flags five redundancy
  signals: `multi_task_file` (a file edited by ≥2 tasks — the primary
  duplicate-task signal, computed from a `file_owners` adjacency map rather than a
  pairwise count), `dup_substep` (the same `(target, intent)` baked into >1 task),
  `in_task_build` (a HEAVY build/verify command — `module-tests` / `quality-gate`
  / `coverage` or full-suite `verify` — baked into a task's
  `verification.commands` that phase-5/6 already runs, inferred from the verb
  alone with no `execution.toon` join), `verif_task_fanout` (>1
  module_testing/verification task), and `deliverable_fanout` (a deliverable whose
  task count exceeds the per-run corpus outlier threshold `max(3, median*2)`,
  recomputed fresh from the loaded corpus each run). A per-plan row carries
  `severity: genuine` whenever any of the five signals is populated.
- `preference-pattern-detector` (cross-plan) — aggregates recurring user
  gate-dispositions across the corpus. Walks each plan's
  `artifacts/findings/*.jsonl`, derives a `(module, finding-class, disposition)`
  tuple for every finding carrying a user-gate disposition
  (`suppressed`/`accepted`/`taken_into_account`), counts distinct plans per tuple,
  threshold-gates at `THRESHOLDS["preference_disposition_occurrences"]`, and emits
  candidate-preference rows. The script OWNS only the threshold-gated surfacing;
  the generalization (tuple → best-practice/insight string) and routing (to
  `architecture enrich`) are LLM-orchestration steps documented once in
  `phase-6-finalize/standards/disposition-to-hint-routing.md` and consumed by
  SKILL.md Step 4c.
- `dispatch-topology` (per-plan) — verifies the roadmap's leaf/dispatch-topology
  invariant (subagents are LEAVES — only the orchestrator dispatches further
  subagents). Scans each plan's `logs/work.log` `[DISPATCH] (caller) target=…`
  lines and flags any whose `(bundle:skill)` caller is not an allowed dispatcher
  (`plan-marshall:plan-marshall` or a `plan-marshall:phase-N-…` context) — a leaf
  that spawned a subagent.
- `finalize-flow-conformance` (per-plan) — verifies the post-#849/#850 finalize
  mechanics (deterministic `ci_verify` gate, adaptive ci-wait ratchet) from the
  `phase_6.steps` roster + `artifacts/ci-runs/*/manifest.toon`: flags
  `missing_ci_verify` (a PR created with no ci-verify gate), `ci_wait_timeout`
  (`wait_outcome: deadline_exceeded`), and `ci_unresolved` (latest `final_status`
  not green).
- `merge-window-accounting` (cross-plan) — accounts for the #849 widened
  merge-mutex + FIFO admission-queue window by bucketing the global
  `[LOCK] (merge:*)` lifecycle lines by `lock_id` (= plan_id); reports per-plan
  acquire/release/blocked/reclaim counts + max FIFO `waiting_count` and flags
  `merge_contention` when a plan waited behind the queue front.
- `lane-lever-effectiveness` (cross-plan) — the CHECKPOINT MEASUREMENT ARM of the
  token-optimization roadmap. Measures whether the cost-reducing lane levers
  (recipe auto-routing, the light planning lane, the minimal execution posture,
  the #854 surgical-fix micro-lane) are engaged, and scores each plan's summed
  `total_tokens` against its scope class's armed checkpoint target (surgical
  ≤1.2M / single_module ≤1.5M / multi_module ≤2.5M): emits a per-plan
  `within`/`over`/`unclassed`/`no_metrics` checkpoint verdict, the corpus lever-
  engagement counts, and an `estimated_avoided_tokens` scope-gated subtraction.
  `checkpoint_over` is the genuine overspend signal.
- `cross-check-synthesis` (cross-plan, runs LAST) — the facet-completeness
  critic. It consumes the OTHER checks' retained structured results (not their
  emitted strings) and reports the cross-check couplings that single-check rows
  alone miss: (a) a token-trend `regression=empty` that is untrustworthy because
  input-integrity reports blind execute phases; (b) sequence
  `non_minimal_build`/`build_churn` corroborated by a plan's build WALL-CLOCK
  (`total_build_seconds` upper half) — build redundancy wastes wall-clock, not
  tokens; (c) quality-chain
  `no_qgate6`/`auto_review_only` correlating with sequence `ci_rerun` and
  token-economics `finalize_heavy`; (d) recurring-pattern argparse signatures
  correlating with global-log ERROR/argparse-rejection counts and
  quality-verification unfiled signatures (collapsed to ONE candidate); (e)
  scope-estimate under-estimation correlating with task-count and token-per-file;
  (f) task-graph-redundancy `in_task_build` correlating with sequence
  `build_churn`/`phase_reentry` (one wasted heavy run seen statically and at
  runtime); (g) dispatch-topology leaf-dispatch violations correlating with
  sequence `phase_reentry`; (h) finalize-flow-conformance
  `missing_ci_verify`/`ci_unresolved` correlating with sequence `ci_rerun`; (i)
  merge-window-accounting `merge_contention` correlating with sequence `ci_rerun`
  or token-economics `finalize_heavy`; and (j) lane-lever-effectiveness
  `checkpoint_over` correlating with token-economics `big_spend_tiny_footprint`
  (surgical-overpay: a checkpoint overspend on a plan the cheap lane existed to
  keep small). Each coupling carries its qualifying caveat and the D1 severity
  column. The block operationalizes the SKILL.md Step-4b completeness critic.

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
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
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
    "track-selection-accuracy",
    "pr-merge-velocity",
    "task-count-efficiency",
    "global-log-analysis",
    "token-economics",
    "quality-chain",
    "sequence-and-build-minimality",
    "input-integrity",
    "task-graph-redundancy",
    "architecture-lookup-ratio",
    "preference-pattern-detector",
    # Roadmap-mechanics checks (plan-11): verify the roadmap's own mechanics
    # directly rather than inferring generic symptoms.
    "dispatch-topology",
    "finalize-flow-conformance",
    "merge-window-accounting",
    "lane-lever-effectiveness",
    # cross-check-synthesis is the facet-completeness critic; it consumes the
    # other checks' computed results, so it MUST be last in this list (run_checks
    # dispatches in CHECK_NAMES order and synthesis reads the retained results).
    "cross-check-synthesis",
]

# Cross-plan checks aggregate over the full scanned corpus rather than emitting
# one row per plan. `input-integrity` is deliberately NOT here: it is per-plan
# (one health row per plan) even though it ALSO emits a corpus data_confidence
# summary header alongside the per-plan rows.
CROSS_PLAN_CHECKS = {
    "recurring-pattern-detector",
    "token-efficiency-trend",
    "global-log-analysis",
    "token-economics",
    "quality-chain",
    "sequence-and-build-minimality",
    "architecture-lookup-ratio",
    "preference-pattern-detector",
    # merge-window-accounting scans the corpus-wide global `[LOCK]` lifecycle logs
    # once and buckets by plan_id, so it is cross-plan (like global-log-analysis).
    # dispatch-topology and finalize-flow-conformance are per-plan (one row per
    # plan) and are deliberately NOT here.
    "merge-window-accounting",
    # lane-lever-effectiveness aggregates the whole corpus into per-checkpoint-class
    # spend verdicts + corpus-wide lever-engagement counts, so it is cross-plan.
    "lane-lever-effectiveness",
    # cross-check-synthesis is cross-plan: it joins the other checks' corpus-level
    # results into coupling verdicts rather than emitting one row per plan.
    "cross-check-synthesis",
}

# ---------------------------------------------------------------------------
# Check era model (fixed_since boundary stamps)
# ---------------------------------------------------------------------------
#
# `CHECK_ERA` is the SINGLE source of truth for each check's `fixed_since`
# stamp — the roadmap-era boundary as of which the check's computation is known
# accurate. The stamp is surfaced deterministically on every emitted block header
# (see `_stamp_era`); no check inline-duplicates its own boundary. When a future
# roadmap plan changes a check's semantics, bump that check's entry here (never
# in a per-check emit function) — the one-line lifecycle convention documented in
# SKILL.md § "Check era model".
#
# Stamp vocabulary is the roadmap-plan boundaries this refresh audits against:
# `#812` (execution-profile lane/partiality markers), `#842`/`#845`/`#849`/`#850`
# (plan-1..plan-3 execution-loop / routing / finalize-flow / dist), `#852`
# (find-triage D6 step-ownership), `#862` (inline phase-1-init dispatch /
# routing-order fix), `#863` (merge-queue enablement via marshall-steward), `#872`
# (self-review promoted to a default finalize step), `#875` (plan-13's boundary —
# `metrics`, `track-selection-accuracy`, and `lane-lever-effectiveness`),
# `#PLAN15-PR` (plan-15's boundary — the `architecture-lookup-ratio` check plan-15
# bumps; resolved to the real `#NNN` at that plan's finalize), `PR-PENDING` (this
# plan's own boundary — a finalize-resolved placeholder for the check this plan
# reworks: `merge-window-accounting`, whose accounting this plan's D1 merge-queue
# enqueue-path rework and D3 merge-lock stale-holder liveness fix alter; corrected
# to the concrete #{n} after create-pr), and `plan-10` (the roadmap head this plan
# re-confirms the general checks accurate against). Every key MUST be a member of
# `CHECK_NAMES`.
CHECK_ERA: dict[str, str] = {
    # Roadmap-affected checks carry the specific boundary whose mechanics they
    # verify (kept in step with the plan-11 semantic updates).
    # Bumped to #872: the finalize-step-id surface this check re-derives now carries
    # default:pre-submission-self-review (self-review promoted to a default step).
    "execution-context-manifest": "#872",
    # #875 — this plan (plan-13) reworks these two checks' mechanics, so their era
    # boundary IS this plan's own PR. `metrics` verifies inline phase-1-init
    # main-context token recording (the n=6/6 total_tokens surfacing);
    # `track-selection-accuracy` verifies the classify-before-route lane signals
    # (change_type + scope_estimate pre-classified before the router runs).
    "metrics": "#875",
    "track-selection-accuracy": "#875",
    "global-log-analysis": "#849",
    "sequence-and-build-minimality": "#849",
    "input-integrity": "#812",
    # General checks unaffected by the roadmap: re-confirmed accurate against the
    # roadmap head (plan-10) by this refresh.
    "quality-verification-report": "plan-10",
    "recurring-pattern-detector": "plan-10",
    "token-efficiency-trend": "plan-10",
    "scope-estimate-accuracy": "plan-10",
    "pr-merge-velocity": "plan-10",
    "task-count-efficiency": "plan-10",
    "token-economics": "plan-10",
    "quality-chain": "plan-10",
    "task-graph-redundancy": "plan-10",
    "preference-pattern-detector": "plan-10",
    # architecture-lookup-ratio — #PLAN15-PR (this plan's boundary): this plan
    # reworks the information-vs-build lookup-ratio mechanics, so its era boundary
    # IS this plan's own PR. The `#PLAN15-PR` placeholder is resolved to the real
    # `#NNN` by the finalize era-stamp resolution.
    "architecture-lookup-ratio": "#PLAN15-PR",
    # Roadmap-mechanics checks (plan-11) carry the boundary whose mechanics they
    # verify: dispatch-topology confirms the plan-10 leaf/dispatch invariant;
    # finalize-flow-conformance verifies #849's deterministic ci_verify / adaptive
    # ci-wait mechanics.
    "dispatch-topology": "plan-10",
    "finalize-flow-conformance": "#849",
    # PR-PENDING — this plan (plan-14) reworks the merge-window-accounting
    # mechanics, so its era boundary IS this plan's own PR (bumped from #863):
    # D1 strips --delete-branch/--strategy from the pr merge-queue enqueue path and
    # D3 fixes the merge-lock stale-holder liveness (the live-worktree guard) —
    # both surfaces this check accounts for (the `[LOCK] (merge:*)` lifecycle
    # bucketing + the widened merge-mutex admission window). The concrete #{n} is a
    # documented finalize-time correction that reads the real PR number from
    # status.json after create-pr and rewrites the constant AND its test_audit.py
    # mirror in lock-step. PR-PENDING is a provably-invalid PR token that fails
    # loudly if the correction is ever forgotten — never guess this plan's PR
    # number at phase-5.
    "merge-window-accounting": "PR-PENDING",
    # lane-lever-effectiveness — #875 (this plan's boundary): the Tier-1
    # recipe-match floor fix + the classify-before-route change this plan ships
    # alter which plans engage the light planning lane and the minimal execution
    # posture, so the checkpoint measurement arm (per-scope-class token spend vs
    # armed targets) re-arms at this plan's PR.
    "lane-lever-effectiveness": "#875",
    "cross-check-synthesis": "plan-10",
}

# The roles the phase-5 verification steps must resolve to for a manifest to be
# considered well-composed. A phase-5 step ID is resolved to its matrix `role:`
# in-code (e.g. `default:verify:quality-gate` → `quality-gate`,
# `default:verify:module-tests` → `module-tests`) and intersected against this
# set, mirroring the composer's Role-Field Intersection
# (`manage-execution-manifest/standards/decision-rules.md` § "Role-Field
# Intersection"). Genuine `name_drift` is an unresolvable role or a non-empty
# phase_5 that resolves to zero of these roles — NOT a renamed name.
QUALITY_GATE_ROLES = {"quality-gate", "module-tests"}

# Canonical-verify step prefix. A phase-5 step ID of the shape
# `default:verify:{canonical}` (or its bare `verify:{canonical}` form) is the
# single parameterized canonical-verify step — the matrix role is derived from
# the trailing `{canonical}` segment via `_CANONICAL_TO_ROLE` rather than from a
# per-canonical role-file (the `phase-5-execute/standards/{name}.md` role-files
# were deleted). See `phase-5-execute/standards/canonical_verify.md`.
_CANONICAL_VERIFY_PREFIX = "verify:"

# Canonical command segment → matrix `role:` value. This mirrors the composer's
# `_CANONICAL_TO_ROLE` table in
# `manage-execution-manifest/scripts/manage-execution-manifest.py`, itself the
# composer's copy of the canonical→role mapping documented in
# `phase-5-execute/standards/canonical_verify.md`. Both `verify` and
# `module-tests` map to the `module-tests` role; whole-tree gates map to their
# own roles. Resolution is purely in-code — the deleted standards docs are never
# read.
_CANONICAL_TO_ROLE: dict[str, str] = {
    "quality-gate": "quality-gate",
    "verify": "module-tests",
    "module-tests": "module-tests",
    "coverage": "coverage",
    "integration-tests": "integration",
    "e2e": "e2e",
}

# Legacy bare default-step name → matrix `role:` value. The three default-step
# bare names (`quality_check` / `build_verify` / `coverage_check`) predate the
# parameterized `default:verify:{canonical}` form; their backing role-files have
# been deleted, so their role is resolved in-code here. Mirrors the composer's
# `_LEGACY_BARE_NAME_ROLE` table.
_LEGACY_BARE_NAME_ROLE: dict[str, str] = {
    "quality_check": "quality-gate",
    "build_verify": "module-tests",
    "coverage_check": "coverage",
}

# ---------------------------------------------------------------------------
# Phase-6 finalize step-ownership model (#852 D6)
# ---------------------------------------------------------------------------
#
# #852's D6 step-ownership canonicalization split every phase-6 finalize step
# into two ownership classes: ORCHESTRATOR-OWNED (inline) steps run synchronously
# in the main context (pure scripts or trivial orchestration that earn no
# envelope — push, ci-verify, record-metrics, archive-plan, …) and
# LEAF-DISPATCHABLE steps are dispatched under `Task: execution-context-{level}`
# because they carry an LLM core (create-pr, automatic-review, sonar-roundtrip,
# the review/simplify/security-audit sweeps, …). The classification is the single
# source of truth in `phase-6-finalize/SKILL.md` § "Dispatched workflows vs
# inline steps"; there is NO persisted per-step `owner` field on the manifest
# (`execution.toon` records only the bare `phase_6.steps` ID list), so this check
# DERIVES each step's ownership from that canonical roster rather than reading a
# persisted counterpart. The derivation mirrors `detect_name_drift`'s in-code
# role resolution over phase_5 — a built-in step ID the roster no longer
# recognizes is `owner_drift` (the persisted manifest references a renamed or
# removed finalize step), exactly as an unresolvable phase_5 role is `name_drift`.
#
# The maps below are keyed by the BARE step name (the `default:` prefix stripped);
# `project:` / `bundle:skill` external steps are classified via the known
# meta-project map and otherwise resolve to `None` WITHOUT flagging drift (an
# unknown external step is project-defined, not a canonical-roster fault).
_ORCHESTRATOR_OWNED_STEPS = frozenset(
    {
        "finalize-step-sync-baseline",
        "push",
        "ci-verify",
        "branch-cleanup",
        "pre-push-quality-gate",
        "record-metrics",
        "archive-plan",
        "finalize-step-print-phase-breakdown",
    }
)
_LEAF_DISPATCHED_STEPS = frozenset(
    {
        "pre-submission-self-review",
        "create-pr",
        "lessons-capture",
        "adr-propose",
        "automatic-review",
        "sonar-roundtrip",
        "finalize-step-simplify",
        "finalize-step-security-audit",
    }
)
# `architecture-refresh` is the one hybrid step: Tier-0 discover/diff runs inline
# and Tier-1 re-enrichment fans out per affected module — it owns both classes.
_HYBRID_OWNED_STEPS = frozenset({"architecture-refresh"})

# Known meta-project external steps and their ownership. Unknown external steps
# (absent from this map) resolve to `None` and are NOT flagged as drift.
_EXTERNAL_STEP_OWNER: dict[str, str] = {
    "project:finalize-step-deploy-target": "orchestrator",
    "project:finalize-step-sync-plugin-cache": "orchestrator",
    "project:finalize-step-plugin-doctor": "leaf",
    # Promoted built-in-equivalent bundle finalize step: its dispatched form is a
    # leaf. A composed manifest normalizes it to the bare ``automatic-review`` id
    # (classified via `_LEAF_DISPATCHED_STEPS` above); the bundle-prefixed id is
    # classified here for manifests / rosters that carry the un-normalized form.
    "plan-marshall:automatic-review": "leaf",
}


def _resolve_step_owner(step_id: str) -> str | None:
    """Resolve a phase-6 finalize step ID to its ownership class.

    Returns `orchestrator` (inline), `leaf` (dispatched), `hybrid`
    (architecture-refresh), or `None` for an unrecognized step. Built-in
    (`default:`-prefixed or bare) step IDs resolve via the canonical
    orchestrator/leaf/hybrid sets; `project:` / `bundle:skill` external steps
    resolve via `_EXTERNAL_STEP_OWNER`. `None` distinguishes an unrecognized
    BUILT-IN step (a genuine roster drift, per `detect_owner_drift`) from an
    unrecognized EXTERNAL step (project-defined, never drift).
    """
    bare = step_id.strip()
    if ":" in bare and not bare.startswith("default:"):
        # External (`project:` / `bundle:skill`) — classified only via the known map.
        return _EXTERNAL_STEP_OWNER.get(bare)
    bare = _bare_step(bare)
    if bare in _ORCHESTRATOR_OWNED_STEPS:
        return "orchestrator"
    if bare in _LEAF_DISPATCHED_STEPS:
        return "leaf"
    if bare in _HYBRID_OWNED_STEPS:
        return "hybrid"
    return None


# ---------------------------------------------------------------------------
# Centralized threshold table
# ---------------------------------------------------------------------------
#
# Every audit magic number lives here — the single source of truth consumed by
# every check. No check re-declares a constant inline; a check needing a tunable
# reads it from `THRESHOLDS[...]`. Keeping them in one documented table makes the
# audit's sensitivity auditable in isolation and lets a future check reuse a band
# without re-deriving it.
#
# Where a corpus distribution exists a check SHOULD prefer a percentile/median
# helper (see `percentile`/`median` below) over a hard-coded constant; the
# entries here are the fixed thresholds that have no meaningful corpus-relative
# form (boundary counts, share fractions, duration ceilings).
THRESHOLDS: dict[str, Any] = {
    # Recurring-pattern systemic threshold (request: 3+ occurrences).
    "systemic_occurrences": 3,
    # Preference-pattern-detector threshold: a (module, finding-class,
    # disposition) recurrence must appear in at least this many distinct plans to
    # surface as a candidate preference (mirrors the systemic-occurrences band).
    "preference_disposition_occurrences": 3,
    # PR review-cycle threshold (hours) above which a plan is flagged slow.
    "pr_slow_review_hours": 24.0,
    # Disproportionate-token threshold: a phase consuming more than this share
    # of the plan's total tokens is flagged.
    "phase_token_share": 0.45,
    # Optimization-signal outlier multiple: a phase whose token/second ratio is
    # at least this multiple of the median non-zero ratio is flagged.
    "token_rate_outlier_multiple": 3.0,
    # Token-efficiency-trend regression: the last third's mean tokens-per-phase
    # must exceed the first third's by more than this fraction to flag.
    "token_trend_regression_fraction": 0.25,
    # Build-duration classification ceilings (seconds): `minimal < scoped` and
    # `scoped < heavy`. Used by sequence-and-build-minimality.
    "build_minimal_seconds": 120.0,
    "build_heavy_seconds": 400.0,
    # Build-clustering window (minutes): repeated builds within this span are a
    # build-churn signal.
    "build_clustering_minutes": 10.0,
    # Long-session message-count ceiling: a session above this is flagged long.
    "long_session_messages": 200,
    # Global-log slow-call ceiling (seconds): a script call at/over this is slow.
    "slow_call_seconds": 30.0,
    # Global-log high-frequency caller ceiling: a notation+subcommand called at
    # least this many times across the corpus is flagged high-frequency.
    "high_frequency_calls": 50,
    # Scope-estimate file-count bands. Maps a declared scope_estimate to the
    # inclusive [low, high] band of expected total touched files. `None` upper
    # bound means "unbounded".
    "scope_file_bands": {
        "surgical": (1, 3),
        "single_module": (1, 15),
        "multi_module": (5, None),
    },
    # Task-count efficiency: expected tasks-per-deliverable band. Outside this
    # band the plan is flagged under- or over-decomposed.
    "tasks_per_deliverable_low": 0.5,
    "tasks_per_deliverable_high": 4.0,
    # Retire-on-quiet proposal threshold: a check that surfaces zero genuine
    # signals across at least this many consecutive recorded runs (the current
    # run plus its immediate predecessors) surfaces a removal PROPOSAL in the
    # `retire-on-quiet` block. Proposal only — the script never removes a check.
    "retire_on_quiet_runs": 3,
    # Armed per-scope-class total-token checkpoint targets (the roadmap's
    # optimization checkpoint, `.plan/plan-optimization/HANDOVER.md`). A plan's
    # scope_estimate maps to its checkpoint class; the plan's summed metrics.toon
    # total_tokens is measured against the class target. Consumed by
    # lane-lever-effectiveness (the checkpoint measurement arm). A scope_estimate
    # outside this map is `unclassed` (no verdict).
    "checkpoint_token_targets": {
        "surgical": 1_200_000,
        "single_module": 1_500_000,
        "multi_module": 2_500_000,
    },
}

# Back-compatible module-level aliases. These name the same values the
# `THRESHOLDS` table owns; they exist so existing call-sites and the test module
# (which references `SYSTEMIC_THRESHOLD` by name) resolve without a rename. New
# code reads `THRESHOLDS[...]` directly.
SYSTEMIC_THRESHOLD: int = THRESHOLDS["systemic_occurrences"]
PR_SLOW_REVIEW_HOURS: float = THRESHOLDS["pr_slow_review_hours"]
PHASE_TOKEN_SHARE_THRESHOLD: float = THRESHOLDS["phase_token_share"]
SCOPE_FILE_BANDS: dict[str, tuple[int, int | None]] = THRESHOLDS["scope_file_bands"]
TASKS_PER_DELIVERABLE_LOW: float = THRESHOLDS["tasks_per_deliverable_low"]
TASKS_PER_DELIVERABLE_HIGH: float = THRESHOLDS["tasks_per_deliverable_high"]


def median(values: list[float]) -> float:
    """Return the median of a non-empty list, or 0.0 when empty.

    Corpus-relative threshold helper: checks that have a live distribution
    SHOULD prefer this (or `percentile`) over a hard-coded `THRESHOLDS` constant.
    """
    if not values:
        return 0.0
    ordered = sorted(values)
    mid = len(ordered) // 2
    if len(ordered) % 2 == 1:
        return ordered[mid]
    return (ordered[mid - 1] + ordered[mid]) / 2.0


def percentile(values: list[float], pct: float) -> float:
    """Return the `pct` percentile (0-100) via nearest-rank, 0.0 when empty.

    Corpus-relative threshold helper (see `median`). Deterministic nearest-rank
    so the audit is reproducible run-to-run on a frozen corpus.
    """
    if not values:
        return 0.0
    ordered = sorted(values)
    pct = max(0.0, min(100.0, pct))
    rank = max(1, round(pct / 100.0 * len(ordered)))
    return ordered[rank - 1]


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
    # Token total attributable to the plan-retrospective dispatch within the
    # phase window (recorded by manage-metrics as a `retrospective_tokens`
    # sub-field on `[6-finalize]`). Default 0 when absent — archived plans
    # predating the attribution change have the spend irrecoverably co-mingled,
    # so the metrics checks exclude nothing for them (best-effort degrade).
    retrospective_tokens: int = 0

    @property
    def effective_tokens(self) -> int:
        """Token total with plan-retrospective spend excluded (never negative)."""
        return max(0, self.total_tokens - self.retrospective_tokens)


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
        elif key == "retrospective_tokens":
            current.retrospective_tokens = _to_int(value)
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


def parse_metrics_partiality(metrics_path: Path) -> tuple[bool, set[str]]:
    """Read #812's recorded-partiality markers from `metrics.toon`.

    Returns `(partial, unrecorded_phases)` from the top-level `partial` /
    `unrecorded_phases` scalars manage-metrics stamps: a canonical phase lacking a
    recorded boundary (`end_time`) is listed in `unrecorded_phases`, and `partial`
    is true whenever that set is non-empty. A phase the recorder KNOWS is
    unrecorded is recorded-partial BY DESIGN — not an accidental zero-token
    blindness — so the metrics and input-integrity checks consume this signal
    rather than inferring blindness from zero-token phases alone. Absent markers
    (a plan predating #812) degrade to `(False, set())`, preserving the old
    zero-token inference for those plans.
    """
    partial_raw = parse_toon_scalar(metrics_path, "partial")
    partial = str(partial_raw or "").strip().lower() == "true"
    unrecorded_raw = parse_toon_scalar(metrics_path, "unrecorded_phases")
    unrecorded = {seg.strip() for seg in (unrecorded_raw or "").split(",") if seg.strip()}
    return partial, unrecorded


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
    # track-selection-accuracy inputs: the ACTUAL planning track the plan ran.
    # `planning_lane` (light|deep) is the lane the router resolved at phase-1-init
    # (`status.json::metadata.planning_lane`); `track` (simple|complex) is the
    # coarser track recorded in `references.json::track`. Both are None when the
    # plan predates the field or never recorded it.
    planning_lane: str | None = None
    track: str | None = None
    # lane-lever-effectiveness input: the execution-profile POSTURE the plan ran
    # under (`status.json::metadata.execution_profile`, one of minimal|auto|full).
    # None when the plan predates the #811 execution-profile field.
    execution_profile: str | None = None


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

    # track-selection-accuracy: the ACTUAL planning track the plan ran. The lane
    # lives in status.json::metadata.planning_lane; the coarser track in
    # references.json::track.
    planning_lane = metadata.get("planning_lane")
    if isinstance(planning_lane, str) and planning_lane.strip():
        inputs.planning_lane = planning_lane.strip()
    track = refs.get("track")
    if isinstance(track, str) and track.strip():
        inputs.track = track.strip()

    # lane-lever-effectiveness: the execution-profile posture the plan ran under.
    execution_profile = metadata.get("execution_profile")
    if isinstance(execution_profile, str) and execution_profile.strip():
        inputs.execution_profile = execution_profile.strip()

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

    # Row 3 resolves candidate step IDs to their matrix roles (mirroring the
    # composer's Role-Field Intersection) rather than testing literal-string
    # membership: a well-composed phase_5 carries parameterized IDs such as
    # `default:verify:module-tests`, not the bare role string `module-tests`.
    role_cache: dict[str, str | None] = {}
    candidate_roles = {
        _resolve_step_role(inputs.plan_dir, step_id, role_cache)
        for step_id in candidates
    }

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
        and "module-tests" not in candidate_roles
        and "coverage" not in candidate_roles
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


def _strip_step_namespace(step_id: str) -> str:
    """Strip only the optional `default:` prefix from a phase-5 step ID.

    `default:quality_check` → `quality_check`; `quality_check` → `quality_check`;
    `default:verify:quality-gate` → `verify:quality-gate` (the canonical-verify
    form is preserved so the trailing `{canonical}` segment is recoverable). This
    mirrors the composer's `_strip_default_prefix` — it MUST NOT split on the
    last colon, which would collapse a parameterized step to its bare canonical
    and break role derivation.
    """
    bare = step_id.strip()
    prefix = "default:"
    return bare[len(prefix):] if bare.startswith(prefix) else bare


def _resolve_step_role(
    _repo_root: Path, step_id: str, cache: dict[str, str | None]
) -> str | None:
    """Resolve a phase-5 step ID to its matrix `role:` value, purely in-code.

    Resolution mirrors the composer's `_role_of` — no standards `.md` file is
    read (the `phase-5-execute/standards/{name}.md` role-files were deleted):

    - Canonical-verify steps (`default:verify:{canonical}` or the bare
      `verify:{canonical}` form) derive the role from the trailing `{canonical}`
      segment via the `_CANONICAL_TO_ROLE` table.
    - Legacy bare default-step names (`quality_check` / `build_verify` /
      `coverage_check`) resolve via the `_LEGACY_BARE_NAME_ROLE` table.

    Returns `None` for external steps (`project:` / `bundle:skill`),
    canonical-verify steps whose `{canonical}` is unrecognized, and any other
    bare name absent from `_LEGACY_BARE_NAME_ROLE` — preserving the "missing
    data → step is never role-selected" convention. The `_repo_root` parameter
    is retained for call-site stability (role resolution no longer touches the
    filesystem). Results (including unresolved `None`) are memoized in `cache`.
    """
    if step_id in cache:
        return cache[step_id]

    bare = _strip_step_namespace(step_id)

    # Canonical-verify steps: `default:verify:{canonical}` (bare:
    # `verify:{canonical}`). Role is derived from the trailing canonical segment.
    if bare.startswith(_CANONICAL_VERIFY_PREFIX):
        canonical = bare[len(_CANONICAL_VERIFY_PREFIX):]
        role = _CANONICAL_TO_ROLE.get(canonical)
        cache[step_id] = role
        return role

    # External steps (`project:foo` / `bundle:skill`) have no role.
    if ":" in step_id and not step_id.startswith("default:"):
        cache[step_id] = None
        return None

    # Legacy bare default-step names resolve via the in-code table. An
    # unrecognized bare name resolves to `None` (never role-selected).
    role = _LEGACY_BARE_NAME_ROLE.get(bare)
    cache[step_id] = role
    return role


def detect_name_drift(inputs: PlanInputs, repo_root: Path, role_cache: dict[str, str | None]) -> str | None:
    """Genuine name_drift detection via in-code role resolution.

    Resolves each phase-5 step ID to its matrix `role:` (via the
    `_CANONICAL_TO_ROLE` / `_LEGACY_BARE_NAME_ROLE` tables, mirroring the
    composer's `_role_of`) and intersects the resolved roles against
    {quality-gate, module-tests}. Genuine drift is exactly: (a) a step ID whose
    role cannot be resolved, or (b) a non-empty phase_5 list that resolves to
    zero quality-gate/module-tests roles. A well-composed phase_5 such as
    `['default:verify:quality-gate', 'default:verify:module-tests']` resolves to
    {quality-gate, module-tests} and is NOT flagged.
    """
    if not inputs.manifest_phase_5:
        return None
    unresolved: list[str] = []
    resolved_roles: set[str] = set()
    for step_id in inputs.manifest_phase_5:
        role = _resolve_step_role(repo_root, step_id, role_cache)
        if role is None:
            unresolved.append(_strip_step_namespace(step_id))
        else:
            resolved_roles.add(role)
    if unresolved:
        return (
            f"phase_5 step ID(s) {unresolved} resolve to no matrix `role:` "
            f"(unknown canonical or unknown legacy step) — unresolvable role"
        )
    if not (resolved_roles & QUALITY_GATE_ROLES):
        return (
            f"phase_5 {inputs.manifest_phase_5} resolves to roles {sorted(resolved_roles)} "
            f"— zero intersection with {{quality-gate, module-tests}}"
        )
    return None


def detect_owner_drift(inputs: PlanInputs) -> str | None:
    """Step-ownership drift over the manifest's phase_6 finalize step roster (#852 D6).

    Derives each phase_6 step's ownership class (orchestrator-owned inline vs
    leaf-dispatchable) via `_resolve_step_owner` — there is no persisted `owner`
    field on the manifest, so the class is DERIVED from the canonical finalize
    roster (`phase-6-finalize/SKILL.md` § "Dispatched workflows vs inline steps").
    This extends the manifest check's previously role-only re-derivation to cover
    step-ownership. Genuine `owner_drift` is exactly a BUILT-IN (`default:`-prefixed
    or bare) phase_6 step ID whose ownership cannot be resolved — the persisted
    manifest references a finalize step the current roster renamed or removed.
    External (`project:` / `bundle:skill`) steps are project-defined and never
    flagged. Returns a describing string on drift, else None.
    """
    if not inputs.manifest_phase_6:
        return None
    unrecognized: list[str] = []
    for step_id in inputs.manifest_phase_6:
        bare = step_id.strip()
        is_builtin = not (":" in bare and not bare.startswith("default:"))
        if is_builtin and _resolve_step_owner(step_id) is None:
            unrecognized.append(_bare_step(bare))
    if unrecognized:
        return (
            f"phase_6 built-in step(s) {unrecognized} resolve to no ownership class "
            f"(orchestrator/leaf/hybrid) — roster drift from the canonical finalize steps"
        )
    return None


def check_execution_manifest(
    inputs: PlanInputs, repo_root: Path, role_cache: dict[str, str | None]
) -> dict[str, Any]:
    expected = derive_expected_rule(inputs) if inputs.manifest_present else None
    verdict, reason = verdict_for(inputs)
    name_drift = detect_name_drift(inputs, repo_root, role_cache)
    owner_drift = detect_owner_drift(inputs)
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
        "owner_drift": owner_drift,
    }


# ---------------------------------------------------------------------------
# Check: quality-verification-report
# ---------------------------------------------------------------------------

# Extract a JSON code block from the markdown report and a "Proposed Lessons"
# section.
_JSON_BLOCK_RE = re.compile(r"```json\s*(.*?)```", re.DOTALL)


def _lesson_title(md: Path) -> str | None:
    """Return the first markdown heading or `title:` frontmatter (lowercased)."""
    try:
        text = md.read_text(encoding="utf-8")
    except OSError:
        return None
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("# "):
            return s[2:].strip().lower()
        if s.lower().startswith("title:"):
            return s.split(":", 1)[1].strip().strip('"').lower()
    return None


def _lessons_corpus_signatures(repo_root: Path) -> list[str]:
    """Read titles from the lessons-learned corpus for the filed cross-check."""
    corpus = repo_root / ".plan/local/lessons-learned"
    if not corpus.is_dir():
        return []
    sigs: list[str] = []
    for md in sorted(corpus.glob("*.md")):
        title = _lesson_title(md)
        if title:
            sigs.append(title)
    return sigs


def _lessons_corpus_titles(repo_root: Path) -> list[str]:
    """Read the corpus as `lesson_id\\ttitle` entries for `_dedup_pretag`.

    The lesson id is the corpus filename stem (the `lesson-<id>` basename without
    its `.md` suffix), so the dedup pre-tag can name the covering lesson. Pairs
    with the bare-title
    `_lessons_corpus_signatures` used by the quality-verification filed
    cross-check, which does not need the id.
    """
    corpus = repo_root / ".plan/local/lessons-learned"
    if not corpus.is_dir():
        return []
    entries: list[str] = []
    for md in sorted(corpus.glob("*.md")):
        title = _lesson_title(md)
        if title:
            entries.append(f"{md.stem}\t{title}")
    return entries


def _signature_filed(signature: str, corpus_sigs: list[str]) -> bool:
    sig = signature.strip().lower()
    if not sig:
        return False
    for entry in corpus_sigs:
        # Tolerate both bare-title entries and `lesson_id\ttitle` entries.
        existing = entry.split("\t", 1)[-1] if "\t" in entry else entry
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
    # #812 recorded-partiality markers: a phase the recorder KNOWS is unrecorded
    # is recorded-partial by design, not an accidental zero-token anomaly.
    _partial, unrecorded_phases = parse_metrics_partiality(metrics_path)
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

    # Token-spend checks exclude plan-retrospective spend (deliberate analysis):
    # the share, optimization-ratio, and cross-plan series compute on effective
    # (retrospective-excluded) tokens. Plans predating the `retrospective_tokens`
    # attribution carry 0, so the exclusion is a no-op for them.
    effective_total = sum(p.effective_tokens for p in phases)

    # (a) Disproportionate phase token usage — computed on effective tokens so a
    # retrospective neither trips the threshold nor inflates another phase's share.
    dispro = ""
    if effective_total > 0:
        for p in phases:
            share = p.effective_tokens / effective_total
            if share >= PHASE_TOKEN_SHARE_THRESHOLD:
                dispro = f"{p.phase}={share:.0%}"
                anomalies.append(f"{p.phase} consumed {share:.0%} of total tokens")
                break

    # (b) Incomplete recordings: zero-token phase that should carry data — but a
    # phase listed in #812's `unrecorded_phases` is recorded-partial BY DESIGN,
    # so it is surfaced as informational partiality, NOT an incomplete-recording
    # anomaly. Only an UNEXPLAINED zero-token phase (not in the marker set) fills
    # the `incomplete_recording` column.
    incomplete = ""
    zero_phases = [p.phase for p in phases if p.total_tokens == 0]
    unexplained_zero = [p for p in zero_phases if p not in unrecorded_phases]
    recorded_partial_zero = [p for p in zero_phases if p in unrecorded_phases]
    if unexplained_zero:
        incomplete = ",".join(unexplained_zero)
        anomalies.append(f"zero-token phases: {incomplete}")
    if recorded_partial_zero:
        anomalies.append(
            f"recorded-partial phases (unrecorded_phases marker): "
            f"{','.join(recorded_partial_zero)}"
        )

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
    # outlier (>= 3x the median non-zero phase ratio). Computed on effective
    # (retrospective-excluded) tokens; a phase whose entire spend is
    # retrospective (effective_tokens == 0) is excluded from the ratio set and
    # the median.
    optimization = ""
    ratios = [
        (p.phase, p.effective_tokens / p.duration_seconds)
        for p in phases
        if p.duration_seconds > 0 and p.effective_tokens > 0
    ]
    if len(ratios) >= 3:
        sorted_ratios = sorted(r for _, r in ratios)
        median_ratio = sorted_ratios[len(sorted_ratios) // 2]
        outlier_multiple = THRESHOLDS["token_rate_outlier_multiple"]
        if median_ratio > 0:
            for phase, ratio in ratios:
                if ratio >= outlier_multiple * median_ratio:
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
# Check: track-selection-accuracy
# ---------------------------------------------------------------------------
#
# Reconstructs the counterfactual "correct" planning lane for each archived plan
# from its realized signals and compares it against the lane/track the plan
# actually ran. The counterfactual reuses the LIVE routing logic via the
# imported `evaluate_signals_pure` + `_request_is_concrete` from the planning-lane
# router — no routing threshold is duplicated here. A plan that ran deep/complex
# where the signals score light is OVER-TRACKED; one that ran light/simple where
# the signals score deep is UNDER-TRACKED.

# Lane (light|deep) → track (simple|complex). The router's coarse-grained track:
# a deep lane corresponds to the complex track, a light lane to the simple track.
_LANE_TO_TRACK = {"light": "simple", "deep": "complex"}


def _load_routing_logic(repo_root: Path) -> Any:
    """Import the live planning-lane router's pure scorer + S5 helper.

    The routing logic is the single source of truth — the audit replays it rather
    than re-deriving any threshold. `_cmd_planning_lane.py` imports several sibling
    modules at module level (across the manage-status / tools-file-ops /
    manage-solution-outline / manage-logging skills), so this helper adds every
    marketplace `skills/*/scripts/` directory to ``sys.path`` (mirroring the test
    conftest's path setup) before importing, then returns the module. Returns
    ``None`` when the marketplace tree cannot be located or the router module
    raises any exception at import time (ImportError, SyntaxError,
    AttributeError, …) — the check then degrades to a `no_routing_logic`
    verdict rather than aborting the audit.
    """
    marketplace_root = repo_root / "marketplace" / "bundles"
    if not marketplace_root.is_dir():
        return None
    for bundle_dir in sorted(marketplace_root.iterdir()):
        skills_dir = bundle_dir / "skills"
        if not skills_dir.is_dir():
            continue
        for skill_dir in sorted(skills_dir.iterdir()):
            scripts_dir = skill_dir / "scripts"
            if scripts_dir.is_dir():
                path_str = str(scripts_dir)
                if path_str not in sys.path:
                    sys.path.insert(0, path_str)
    try:
        import _cmd_planning_lane  # noqa: PLC0415
    except Exception:  # noqa: BLE001 — any import-time failure degrades to no_routing_logic
        return None
    return _cmd_planning_lane


def _read_marshal_compatibility(repo_root: Path) -> str | None:
    """Read `plan.phase-2-refine.compatibility` from the project marshal.json.

    Project-level (same for every plan in a corpus scan). Returns None when the
    file or the key is absent.
    """
    config = read_json(repo_root / ".plan" / "marshal.json")
    if not isinstance(config, dict):
        return None
    plan_block = config.get("plan")
    if not isinstance(plan_block, dict):
        return None
    refine = plan_block.get("phase-2-refine")
    if not isinstance(refine, dict):
        return None
    value = refine.get("compatibility")
    return value if isinstance(value, str) else None


def _routing_const(routing: Any, name: str) -> frozenset[str] | None:
    """Read a frozenset constant off the imported router module, or None.

    Used by the #854 era-awareness attribution to reference the router's OWN
    carve-out constants (`_NARROW_SCOPE_ESTIMATES`, `_DEEP_CHANGE_TYPES`) rather
    than duplicating the thresholds. Returns None when the attribute is absent (a
    router revision that renamed the constant) so the caller degrades to a plain,
    non-era-annotated verdict rather than raising.
    """
    value = getattr(routing, name, None)
    return value if isinstance(value, frozenset) else None


def check_track_selection_accuracy(
    inputs: PlanInputs, routing: Any, compatibility: str | None
) -> dict[str, Any]:
    """Per-plan actual-vs-counterfactual planning-track verdict.

    `routing` is the imported planning-lane module (or None when unavailable);
    `compatibility` is the project-level marshal.json value, read once by the
    caller. The counterfactual lane is `evaluate_signals_pure(realized signals)`;
    `request_concrete` is re-derived from the plan's `request.md` via the imported
    `_request_is_concrete`. When `request.md` is absent the check short-circuits to
    `not_recorded` (reason `missing_request_md`) rather than feeding a fabricated
    vague-request signal; an unreadable-but-present file is treated as unknown (no
    S5 deep-bias). Verdict: OVER-TRACKED (ran deep/complex, counterfactual light),
    UNDER-TRACKED (ran light/simple, counterfactual deep), correct, not_recorded,
    or no_routing_logic.
    """
    actual_lane = inputs.planning_lane or ""
    # Actual track: prefer the explicit references.json::track, else derive from
    # the recorded lane.
    actual_track = inputs.track or _LANE_TO_TRACK.get(actual_lane, "")

    if routing is None:
        return {
            "plan_id": inputs.plan_id,
            "actual_lane": actual_lane,
            "actual_track": actual_track,
            "counterfactual_lane": "",
            "verdict": "no_routing_logic",
            "era": "",
        }
    if not actual_lane and not actual_track:
        # The plan never recorded a planning lane/track — nothing to compare.
        return {
            "plan_id": inputs.plan_id,
            "actual_lane": "",
            "actual_track": "",
            "counterfactual_lane": "",
            "verdict": "not_recorded",
            "era": "",
        }

    # Re-derive S5 request concreteness from the archived request.md body.
    # An absent request.md is insufficient data, NOT a vague request: feeding
    # request_concrete=False here would fabricate the S5 deep-bias signal and can
    # manufacture a false UNDER-TRACKED verdict for plans that simply never had a
    # request.md. Short-circuit to not_recorded with a distinguishing reason so the
    # operator reads the row as informational rather than a real routing miss.
    request_md = inputs.plan_dir / "request.md"
    if not request_md.is_file():
        return {
            "plan_id": inputs.plan_id,
            "actual_lane": actual_lane,
            "actual_track": actual_track,
            "counterfactual_lane": "",
            "verdict": "not_recorded",
            "reason": "missing_request_md",
            "era": "",
        }
    try:
        body = request_md.read_text(encoding="utf-8")
    except OSError:
        # The file exists but is unreadable — treat S5 as unknown, not vague.
        # request_concrete=True suppresses the S5 deep-bias so an I/O error does not
        # masquerade as a vague request and manufacture a false UNDER-TRACKED verdict.
        request_concrete = True
    else:
        request_concrete = bool(routing._request_is_concrete(body))

    counterfactual = routing.evaluate_signals_pure(
        scope_estimate=inputs.scope_estimate,
        change_type=inputs.change_type,
        compatibility=compatibility,
        plan_source=inputs.recipe_key,
        request_concrete=request_concrete,
    )
    counterfactual_lane = counterfactual["lane"]

    # Compare on the lane axis (the router's native verdict). Map the actual track
    # back to a lane when the lane itself was not recorded.
    effective_actual_lane = actual_lane or {
        v: k for k, v in _LANE_TO_TRACK.items()
    }.get(actual_track, "")

    verdict = "correct"
    if effective_actual_lane == "deep" and counterfactual_lane == "light":
        verdict = "OVER-TRACKED"
    elif effective_actual_lane == "light" and counterfactual_lane == "deep":
        verdict = "UNDER-TRACKED"

    # Era-awareness around the #854 light-lane carve-out. The imported
    # `evaluate_signals_pure` is the LIVE post-#854 router, whose narrow-and-concrete
    # carve-out relaxes a bounded surgical/single_module + concrete request to LIGHT
    # even when its change_type is generative or its compatibility is breaking (the
    # S3/S4 co-firing the carve-out suppresses). A plan that ran DEEP under the
    # pre-#854 router — where that same co-firing forced deep — is scored
    # OVER-TRACKED here only BECAUSE of the carve-out. That over-tracking is
    # era-relative: the plan's deep run was consistent with the router in force when
    # it ran, so the row is annotated (not silently counted as an absolute routing
    # miss). Attribution is derived from the router's OWN constants (imported, never
    # duplicated) so no threshold is copied.
    era = CHECK_ERA.get("track-selection-accuracy", "")
    carve_out_attributed = False
    if verdict == "OVER-TRACKED":
        narrow = _routing_const(routing, "_NARROW_SCOPE_ESTIMATES")
        deep_change = _routing_const(routing, "_DEEP_CHANGE_TYPES")
        in_narrow = narrow is not None and inputs.scope_estimate in narrow
        would_force_deep = (
            deep_change is not None and inputs.change_type in deep_change
        ) or compatibility == "breaking"
        carve_out_attributed = bool(in_narrow and request_concrete and would_force_deep)

    return {
        "plan_id": inputs.plan_id,
        "actual_lane": actual_lane,
        "actual_track": actual_track,
        "counterfactual_lane": counterfactual_lane,
        "verdict": verdict,
        "era": f"{era}:carve_out" if carve_out_attributed else era,
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
# Cross-plan: preference-pattern-detector
# ---------------------------------------------------------------------------
#
# Aggregates recurring user gate-dispositions across the archived-plan corpus and
# surfaces `(module, finding-class, disposition)` tuples that appear in N or more
# distinct plans as candidate preferences. The disposition is the finding's
# `resolution` field narrowed to the three user-gate dispositions
# (`suppressed` / `accepted` / `taken_into_account`); the finding-class is the
# same prefix-collapsed signature the recurring detector uses; the module is the
# finding's `module` attribution (falling back to `component`, then `default`).
#
# This check OWNS only the threshold-gated surfacing of the tuples. The
# generalization (tuple → best-practice / insight string) and routing (to
# `architecture enrich`) are LLM-orchestration steps documented ONCE in
# `phase-6-finalize/standards/disposition-to-hint-routing.md` and consumed by
# SKILL.md Step 4c — the script never generalizes or routes.

# The three user-gate dispositions a preference recurrence is built from. Other
# `resolution` values (`fixed`, `pending`, etc.) are not preferences and are
# excluded from the aggregation.
_PREFERENCE_DISPOSITIONS = {"suppressed", "accepted", "taken_into_account"}


def _preference_disposition(obj: dict[str, Any]) -> str | None:
    """Return the finding's user-gate disposition, or None when it is not one.

    Reads the `resolution` field directly and keeps only the three user-gate
    dispositions. A `promoted` finding (lesson-promoted) is never a preference.
    """
    if obj.get("promoted"):
        return None
    res = str(obj.get("resolution") or "").strip().lower()
    return res if res in _PREFERENCE_DISPOSITIONS else None


def _preference_module(obj: dict[str, Any]) -> str:
    """Return the finding's module attribution for preference aggregation.

    Prefers the explicit `module` field, falls back to `component`, then to the
    cross-cutting `default` bucket. Cross-cutting patterns (no concrete module)
    route via `--module default` per the shared routing contract.
    """
    for key in ("module", "component"):
        value = obj.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return "default"


def cross_preference_pattern(all_inputs: list[PlanInputs]) -> dict[str, Any]:
    """Aggregate `(module, finding-class, disposition)` recurrences corpus-wide.

    Reuses the `read_jsonl` corpus walk over each plan's
    `artifacts/findings/*.jsonl`. For each finding carrying a user-gate
    disposition, derives a `(module, finding-class, disposition)` tuple, counts
    the distinct plans each tuple appears in (a tuple appearing in multiple
    findings within one plan contributes a single occurrence for that plan), and
    threshold-gates at `THRESHOLDS["preference_disposition_occurrences"]`.
    """
    threshold = THRESHOLDS["preference_disposition_occurrences"]
    tuple_to_plans: dict[tuple[str, str, str], set[str]] = defaultdict(set)
    for inputs in all_inputs:
        findings_dir = inputs.plan_dir / "artifacts" / "findings"
        if not findings_dir.is_dir():
            continue
        seen_in_plan: set[tuple[str, str, str]] = set()
        for jsonl in findings_dir.glob("*.jsonl"):
            for obj in read_jsonl(jsonl):
                disposition = _preference_disposition(obj)
                if disposition is None:
                    continue
                finding_class = _finding_signature(obj)
                if not finding_class:
                    continue
                module = _preference_module(obj)
                seen_in_plan.add((module, finding_class, disposition))
        for key in seen_in_plan:
            tuple_to_plans[key].add(inputs.plan_id)

    candidates: list[dict[str, Any]] = [
        {
            "module": module,
            "finding_class": finding_class,
            "disposition": disposition,
            "occurrence_count": len(plans),
            "plan_ids": sorted(plans),
        }
        for (module, finding_class, disposition), plans in tuple_to_plans.items()
        if len(plans) >= threshold
    ]
    candidates.sort(
        key=lambda r: (
            -int(r["occurrence_count"]),
            str(r["module"]),
            str(r["finding_class"]),
            str(r["disposition"]),
        )
    )
    return {
        "threshold": threshold,
        "candidate_count": len(candidates),
        "rows": candidates,
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
        # Exclude plan-retrospective spend: sum effective (retrospective-excluded)
        # tokens for `total`, and count only phases that carry implementation
        # spend in the divisor (a phase whose entire spend is retrospective is
        # excluded). Plans predating the attribution carry 0, so the exclusion is
        # a no-op for them.
        total = sum(p.effective_tokens for p in phases)
        impl_phases = sum(1 for p in phases if p.effective_tokens > 0)
        per_phase = total / impl_phases if impl_phases else 0
        series.append(
            {
                "plan_id": inputs.plan_id,
                "phases": impl_phases,
                "total_tokens": total,
                "tokens_per_phase": int(per_phase),
            }
        )

    # Regression rule: sustained upward trend — the last third's mean
    # tokens-per-phase exceeds the first third's mean by more than the
    # centralized regression fraction.
    regression = ""
    if len(series) >= 3:
        third = max(1, len(series) // 3)
        first_mean = sum(r["tokens_per_phase"] for r in series[:third]) / third
        last_mean = sum(r["tokens_per_phase"] for r in series[-third:]) / third
        regression_factor = 1.0 + THRESHOLDS["token_trend_regression_fraction"]
        if first_mean > 0 and last_mean > first_mean * regression_factor:
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
# Cross-plan: global-log-analysis
# ---------------------------------------------------------------------------
#
# Parses the global `.plan/local/logs/` corpus — `script-execution-*.log`,
# `work-*.log`, and `decision-*.log` — and surfaces operational signals the
# per-plan checks cannot see because they read only a single plan's artifacts:
# error/warning lines, slow script calls, high-frequency callers, impossible or
# hang-shaped durations, and test-fixture leaks (synthetic bundle/plan ids that
# escaped a test run into the shared corpus). Every flagged line is correlated to
# the archived-plan execution window(s) it falls inside (per-phase start/end times
# from each plan's `work/metrics.toon`) so a signal can be attributed to the plan
# that produced it, or marked ad-hoc when it falls outside every window.
#
# Thresholds (`slow_call_seconds`, `high_frequency_calls`) come from the
# centralized `THRESHOLDS` table; no magic number is re-declared here.

# `[2026-05-31T22:00:01Z] [INFO] [3befe7] <rest>` — shared line grammar across
# script-execution / work / decision logs. The trailing `Z` and the bracketed
# hash are mandatory; `<rest>` is the notation+message body.
_LOG_LINE_RE = re.compile(
    r"^\[(?P<ts>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})Z\]\s+"
    r"\[(?P<level>[A-Z]+)\]\s+\[(?P<hash>[0-9a-f]+)\]\s+(?P<rest>.*)$"
)

# Trailing `(0.22s)` script-call duration, anchored to end-of-line. The capture
# is a strict decimal float (`\d+(?:\.\d+)?`) so a malformed multi-dot token such
# as `1.2.3` can never reach the `float()` at the call site below.
_LOG_DUR_RE = re.compile(r"\((\d+(?:\.\d+)?)s\)\s*$")

# Script-execution head: `bundle:skill:script subcommand ... (0.22s)`. The
# notation is the three-segment colon form; the first whitespace-delimited token
# after it is the subcommand (the aggregation key drops the trailing args).
_LOG_SCRIPT_HEAD_RE = re.compile(
    r"^(?P<notation>[a-z0-9-]+:[a-z0-9_-]+:[a-z0-9_-]+)"
    r"\s+(?P<sub>\S+)?"
)

# Lines whose body signals a failure even when the LEVEL cell is INFO (a script
# can exit non-zero while the logging wrapper stamps INFO). Mirrors the prototype
# FAIL_MARKERS set.
#
# The bare `Error` / `failed` markers use a slug-boundary guard `(?<![\w-])…(?![\w-])`
# rather than a plain `\b`: a hyphen is a word boundary, so `\bError\b` matched the
# word "error" embedded in a branch/plan slug (e.g. `workflow-doc-error-branches`),
# producing failure false-positives on ordinary INFO branch-intent lines. Requiring
# the marker NOT to be flanked by a word char OR a hyphen keeps real status text
# ("Build failed", "Error:") while excluding slug-embedded occurrences. The specific
# markers (invalid choice / Traceback / exit_code / argparse_rejection / status:error)
# are already unambiguous and need no guard.
_LOG_FAIL_MARKERS_RE = re.compile(
    r"invalid choice|unrecognized arguments|the following arguments are required"
    r"|Traceback|exit[_ ]?code\s*[=:]?\s*[12]|argparse_rejection"
    r"|(?<![\w-])Error(?![\w-])|(?<![\w-])failed(?![\w-])"
    r"|status:\s*error",
    re.IGNORECASE,
)

# LEVELS that are *more severe* than INFO. Only these (or a failure-marker body)
# flag a line as an error. DEBUG is diagnostic output *below* INFO and is NOT an
# error: flagging every non-INFO level swept thousands of DEBUG lines into the
# error count (the recording-noise the audit-tool precision fix removed). A line
# at one of these levels — or any line whose body carries a failure marker — is a
# genuine signal; everything else is not.
_ELEVATED_LOG_LEVELS = frozenset({"WARNING", "WARN", "ERROR", "CRITICAL", "FATAL"})

# Read-only QUERY subcommands that legitimately exit non-zero on "not found" — the
# executor stamps the call line at ERROR even though "absent" is a normal answer.
# ONLY a completed script call whose subcommand is in this set is treated as a benign
# probe and excluded from error-flagging. A NON-query command (e.g. `run`, `verify`,
# `compile`) at an elevated level with no failure marker is a genuine failure and
# stays flagged — narrowing the exclusion to this allowlist prevents silently dropping
# real failures from non-probe commands. The set is deliberately conservative: a
# query verb omitted here merely re-earns a benign error-flag (noise), whereas a
# non-query verb wrongly included would hide a real failure.
_LOG_BENIGN_PROBE_SUBCOMMANDS = frozenset(
    {"exists", "read", "get", "list", "find", "search", "resolve"}
)

# Impossible / hang-shaped duration ceiling (seconds) for a DETERMINISTIC
# per-plan-op call. A single such script call recorded at/over this is not a real
# wall-clock cost — it is a clock-skew artifact or a hung-then-killed call.
# Distinct from the `slow_call_seconds` *slow* band: slow is "worth
# investigating", impossible is "the recording itself is suspect".
#
# Call-class awareness (#849): the flat 600 s ceiling applies ONLY to
# deterministic per-plan-op calls. Build and ci-wait class calls legitimately
# run far longer — #849's adaptive ci-wait ratchet grows the ci-wait budget as
# observed durations rise — so bounding them at 600 s falsely flagged every
# ratcheted ci-wait as "impossible". Those calls are instead bounded by the
# ratcheted ci-wait ceiling read inline from `run-configuration.json` (see
# `_ratcheted_ci_wait_ceiling`), so a long-but-legitimate ci-wait lands in the
# *slow* band, not the *impossible* one.
_IMPOSSIBLE_DURATION_SECONDS = 600.0

# Build / ci-wait / sonar-CE / merge-wait call classifier over the global-log
# call key (`{notation} {subcommand}`). A call matching this pattern is bounded
# by the ratcheted ci-wait ceiling rather than the flat deterministic ceiling.
# Everything else is a deterministic per-plan-op call and keeps the 600 s bound.
_BUILD_CI_WAIT_KEY_RE = re.compile(
    r"build-(?:pyproject|maven|gradle|npm)|pyproject_build|:maven\b|:gradle\b|:npm\b"
    r"|tools-integration-ci|:ci\b|ci[_-]verify|pr_checks"
    r"|workflow-integration-sonar|sonar"
    r"|merge[_-]lock|:wait\b|\bwait\b",
    re.IGNORECASE,
)


def _is_build_or_ci_wait_call(key: str) -> bool:
    """True when the call key is a build / ci-wait / sonar-CE / merge-wait call.

    These call classes legitimately run long (the ratcheted ci-wait budget), so
    they are bounded by `_ratcheted_ci_wait_ceiling`, not the flat deterministic
    `_IMPOSSIBLE_DURATION_SECONDS`.
    """
    return bool(_BUILD_CI_WAIT_KEY_RE.search(key))


def _ratcheted_ci_wait_ceiling(repo_root: Path) -> float:
    """Inline-read the ratcheted ci-wait impossible-duration ceiling.

    #849's adaptive ci-wait ratchet persists a per-command timeout under
    `commands.{key}.timeout_seconds` in `run-configuration.json` that grows as
    observed ci-wait durations rise; `build.queue.upper_limit_seconds` is the
    companion ratcheted build-queue ceiling. A build / ci-wait call running near
    either ratcheted value is legitimate, not an impossible-duration artifact, so
    the global-log check bounds those calls by the MAX of the persisted ceilings
    (never below the flat `_IMPOSSIBLE_DURATION_SECONDS` floor). Inline read (no
    manage-* dispatch) per the skill's inline-reader rule; degrades to the flat
    ceiling when the config or the ratcheted values are absent.
    """
    try:
        config = read_json(repo_root / ".plan" / "run-configuration.json")
    except (OSError, ValueError):
        return _IMPOSSIBLE_DURATION_SECONDS
    if not isinstance(config, dict):
        return _IMPOSSIBLE_DURATION_SECONDS
    ceilings: list[float] = [_IMPOSSIBLE_DURATION_SECONDS]
    commands = config.get("commands")
    if isinstance(commands, dict):
        for key, entry in commands.items():
            if not (isinstance(entry, dict) and _is_build_or_ci_wait_call(str(key))):
                continue
            secs = entry.get("timeout_seconds")
            if isinstance(secs, (int, float)) and secs > 0:
                ceilings.append(float(secs))
    build = config.get("build")
    if isinstance(build, dict):
        queue = build.get("queue")
        if isinstance(queue, dict):
            secs = queue.get("upper_limit_seconds")
            if isinstance(secs, (int, float)) and secs > 0:
                ceilings.append(float(secs))
    return max(ceilings)

# Test-fixture leak signatures: synthetic bundle / plan ids that exist only
# inside the test suite's tmp fixtures and must NEVER appear in the shared global
# log corpus. Their presence means a test run wrote to the real
# `.plan/local/logs/` instead of an isolated `PLAN_BASE_DIR`. Matched
# case-insensitively against each line body.
_FIXTURE_LEAK_RE = re.compile(
    r"\bfake-[a-z0-9-]*bundle\b|\bidem-bundle\b|\braising-bundle\b|\borphan-md-[a-z0-9-]+\b",
    re.IGNORECASE,
)


def _parse_log_ts(value: str) -> datetime | None:
    """Parse the `YYYY-MM-DDTHH:MM:SS` log timestamp (sans trailing Z)."""
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%S")
    except ValueError:
        return None


def plan_execution_windows(roots: list[Path]) -> dict[str, tuple[datetime, datetime]]:
    """Map `plan_id -> (earliest start, latest end)` from per-phase metrics.

    Reads every plan's `work/metrics.toon` and collects the per-phase
    `start_time` / `end_time` lines, returning the enclosing window
    `(min start, max end)` per plan. Plans whose metrics carry no parseable
    window are omitted. Used to attribute a flagged log line to the plan whose
    execution window contains it.
    """
    windows: dict[str, tuple[datetime, datetime]] = {}
    for root in roots:
        if not root.is_dir():
            continue
        for plan_dir in sorted(p for p in root.iterdir() if p.is_dir()):
            metrics = plan_dir / "work" / "metrics.toon"
            if not metrics.is_file():
                continue
            try:
                text = metrics.read_text(encoding="utf-8")
            except OSError:
                continue
            starts: list[datetime] = []
            ends: list[datetime] = []
            for raw in text.splitlines():
                stripped = raw.strip()
                if stripped.startswith("start_time:"):
                    ts = _parse_log_ts(stripped.split(":", 1)[1].strip().rstrip("Z"))
                    if ts is not None:
                        starts.append(ts)
                elif stripped.startswith("end_time:"):
                    ts = _parse_log_ts(stripped.split(":", 1)[1].strip().rstrip("Z"))
                    if ts is not None:
                        ends.append(ts)
            if starts and ends:
                windows[plan_dir.name] = (min(starts), max(ends))
    return windows


def _attribute_to_plans(
    ts: datetime | None, windows: dict[str, tuple[datetime, datetime]]
) -> list[str]:
    """Return the plan ids whose execution window contains `ts` (sorted)."""
    if ts is None:
        return []
    return sorted(pid for pid, (s, e) in windows.items() if s <= ts <= e)


def cross_global_log_analysis(repo_root: Path) -> dict[str, Any]:
    """Parse the global log corpus and surface operational signals.

    Reads `script-execution-*.log`, `work-*.log`, and `decision-*.log` under
    `.plan/local/logs/`, buckets lines by LEVEL, aggregates script calls per
    `notation subcommand`, and flags: elevated-level (>= WARNING) / failure-marker
    lines — excluding benign non-zero-exit probe calls — slow calls
    (`>= slow_call_seconds`), impossible/hang durations
    (`>= _IMPOSSIBLE_DURATION_SECONDS`), high-frequency callers
    (`>= high_frequency_calls`), and test-fixture leaks. Each flagged line is
    correlated to the archived-plan execution window(s) it falls within.

    Returns a result dict consumed by `emit_global_log_block`. Best-effort: a
    missing logs directory yields an empty (all-zero) result rather than raising.
    """
    logs_dir = (repo_root / ".plan/local/logs").resolve()
    slow_ceiling = float(THRESHOLDS["slow_call_seconds"])
    high_freq_ceiling = int(THRESHOLDS["high_frequency_calls"])
    # Call-class-aware impossible-duration ceilings: deterministic per-plan-op
    # calls keep the flat 600 s bound; build / ci-wait class calls are bounded by
    # the ratcheted ci-wait ceiling so a legitimately-long ci-wait is not flagged.
    ci_wait_ceiling = _ratcheted_ci_wait_ceiling(repo_root)

    # Correlate against both archived and active plan windows.
    windows = plan_execution_windows(
        [repo_root / ".plan/local/archived-plans", repo_root / ".plan/local/plans"]
    )

    level_counts: dict[str, int] = defaultdict(int)
    call_counts: dict[str, int] = defaultdict(int)
    call_seconds: dict[str, float] = defaultdict(float)
    error_lines: list[dict[str, Any]] = []
    slow_calls: list[dict[str, Any]] = []
    impossible_calls: list[dict[str, Any]] = []
    fixture_leaks: list[dict[str, Any]] = []
    total_lines = 0
    total_seconds = 0.0

    if logs_dir.is_dir():
        patterns = ("script-execution-*.log", "work-*.log", "decision-*.log")
        log_files: list[Path] = []
        for pat in patterns:
            log_files.extend(logs_dir.glob(pat))
        for log in sorted(log_files):
            try:
                content = log.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            for raw in content.splitlines():
                m = _LOG_LINE_RE.match(raw)
                if not m:
                    continue
                total_lines += 1
                level = m.group("level")
                rest = m.group("rest")
                ts_text = m.group("ts")
                ts = _parse_log_ts(ts_text)
                level_counts[level] += 1

                head = _LOG_SCRIPT_HEAD_RE.match(rest)
                is_script_call = False
                script_sub = ""
                if head:
                    sub = head.group("sub") or ""
                    key = f"{head.group('notation')} {sub}".strip()
                    call_counts[key] += 1
                    dur_m = _LOG_DUR_RE.search(rest)
                    if dur_m:
                        is_script_call = True
                        script_sub = sub
                        seconds = float(dur_m.group(1))
                        call_seconds[key] += seconds
                        total_seconds += seconds
                        # Deterministic per-plan-op calls keep the flat 600 s
                        # ceiling; build / ci-wait class calls are bounded by the
                        # ratcheted ci-wait ceiling (#849), so a legitimately-long
                        # ratcheted ci-wait lands in the slow band, not impossible.
                        impossible_ceiling = (
                            ci_wait_ceiling
                            if _is_build_or_ci_wait_call(key)
                            else _IMPOSSIBLE_DURATION_SECONDS
                        )
                        if seconds >= impossible_ceiling:
                            impossible_calls.append(
                                {
                                    "ts": ts_text,
                                    "seconds": seconds,
                                    "key": key,
                                    "plans": _attribute_to_plans(ts, windows),
                                }
                            )
                        elif seconds >= slow_ceiling:
                            slow_calls.append(
                                {
                                    "ts": ts_text,
                                    "seconds": seconds,
                                    "key": key,
                                    "plans": _attribute_to_plans(ts, windows),
                                }
                            )

                has_marker = bool(_LOG_FAIL_MARKERS_RE.search(rest))
                # A completed script call is a benign non-zero-exit probe ONLY when its
                # subcommand is a known read-only QUERY (`exists`/`read`/`get`/`list`/
                # `find`/`search`/`resolve`) answering "not found" — not a real failure. A
                # non-query command (e.g. `run`) at an elevated level with no failure
                # marker is NOT benign and stays flagged. Flag genuine failures: any
                # failure-marker body (at any level), OR an elevated-level line that is
                # not a known-query benign probe.
                benign_probe = (
                    is_script_call
                    and script_sub in _LOG_BENIGN_PROBE_SUBCOMMANDS
                    and not has_marker
                )
                if has_marker or (level in _ELEVATED_LOG_LEVELS and not benign_probe):
                    error_lines.append(
                        {
                            "ts": ts_text,
                            "level": level,
                            "detail": rest[:160],
                            "plans": _attribute_to_plans(ts, windows),
                        }
                    )

                if _FIXTURE_LEAK_RE.search(rest):
                    leak_m = _FIXTURE_LEAK_RE.search(rest)
                    fixture_leaks.append(
                        {
                            "ts": ts_text,
                            "signature": leak_m.group(0) if leak_m else "",
                            "detail": rest[:160],
                            "plans": _attribute_to_plans(ts, windows),
                        }
                    )

    frequent: list[tuple[str, int]] = sorted(
        ((key, count) for key, count in call_counts.items() if count >= high_freq_ceiling),
        key=lambda kc: (-kc[1], kc[0]),
    )
    high_frequency: list[dict[str, Any]] = [
        {
            "key": key,
            "count": count,
            "total_seconds": round(call_seconds.get(key, 0.0), 1),
        }
        for key, count in frequent
    ]

    slow_calls.sort(key=lambda r: -float(r["seconds"]))
    impossible_calls.sort(key=lambda r: -float(r["seconds"]))

    return {
        "logs_present": logs_dir.is_dir(),
        "plan_windows_derived": len(windows),
        "total_log_lines": total_lines,
        "total_script_seconds": round(total_seconds, 1),
        "level_counts": dict(level_counts),
        "error_count": len(error_lines),
        "error_lines": error_lines,
        "slow_call_count": len(slow_calls),
        "slow_calls": slow_calls,
        "impossible_count": len(impossible_calls),
        "impossible_calls": impossible_calls,
        "high_frequency_count": len(high_frequency),
        "high_frequency": high_frequency,
        "fixture_leak_count": len(fixture_leaks),
        "fixture_leaks": fixture_leaks,
        "slow_ceiling": slow_ceiling,
        "high_frequency_ceiling": high_freq_ceiling,
    }


# ---------------------------------------------------------------------------
# Cross-plan: token-economics
# ---------------------------------------------------------------------------
#
# Operationalizes the one-off deep-dive captured in the canonical token-economics
# lesson as a repeatable check. Joins each plan's per-phase `metrics.toon` token spend to its
# `references.json` footprint (scope_estimate, affected/modified file count) and
# `status.json::metadata` change_type, then computes per-plan token shares and
# efficiency ratios and a corpus-relative anti-pattern flag set.
#
# DYNAMIC THRESHOLDS — the defining property of this check. Every anti-pattern
# threshold is derived from the LIVE corpus on each run via the `median` /
# `percentile` helpers, NOT read from the `THRESHOLDS` table and NOT hard-coded.
# The lesson's literal numbers (~450K floor, 2× planning, 30% outline share, 600
# messages) are the SHAPE of each anti-pattern, but the cut-points float with the
# corpus so the check stays honest as the corpus evolves (a future corpus with a
# lower floor flags relative to that lower floor). The only fixed inputs are the
# phase name list and the structural `exec_metrics_blind` predicate (execute
# total == 0), which is a recording fact, not a tunable.

# Canonical phase ordering in `work/metrics.toon` section headers. The three
# planning phases and the lone execution phase are named so the planning≫execute
# and phase-heavy ratios read off the right sections.
_TE_PHASES = ["1-init", "2-refine", "3-outline", "4-plan", "5-execute", "6-finalize"]
_TE_PLANNING_PHASES = ["2-refine", "3-outline", "4-plan"]
_TE_EXECUTE_PHASE = "5-execute"


def _parse_session_message_count(path: Path) -> int:
    """Read the top-level `session_message_count` scalar from `metrics.toon`.

    The count is a file-level scalar above the first `[phase]` section, so
    `parse_metrics_toon` (which only captures phase sections) does not see it.
    Returns 0 when the file or the field is absent.
    """
    value = parse_toon_scalar(path, "session_message_count")
    return _to_int(value) if value is not None else 0


@dataclass
class _TokenEconomicsRow:
    plan_id: str
    change_type: str
    scope_estimate: str
    files: int
    tasks: int
    session_message_count: int
    total_tokens: int
    phase_tokens: dict[str, int]
    exec_metrics_blind: bool

    @property
    def tokens_per_file(self) -> int:
        return self.total_tokens // self.files if self.files else 0

    @property
    def tokens_per_task(self) -> int:
        return self.total_tokens // self.tasks if self.tasks else 0

    @property
    def planning_tokens(self) -> int:
        return sum(self.phase_tokens.get(p, 0) for p in _TE_PLANNING_PHASES)

    @property
    def execute_tokens(self) -> int:
        return self.phase_tokens.get(_TE_EXECUTE_PHASE, 0)

    def phase_share(self, phase: str) -> float:
        """Fraction of plan total spent in `phase` (0.0 when total is 0)."""
        return self.phase_tokens.get(phase, 0) / self.total_tokens if self.total_tokens else 0.0


def _collect_token_economics_rows(all_inputs: list[PlanInputs]) -> list[_TokenEconomicsRow]:
    """Build the per-plan token-economics row for every plan carrying metrics.

    Plans without a parseable `metrics.toon` (no phases) are excluded — they
    contribute no token signal and would skew the corpus distributions with a
    zero total.
    """
    rows: list[_TokenEconomicsRow] = []
    for inputs in all_inputs:
        metrics_path = inputs.plan_dir / "work" / "metrics.toon"
        phases = parse_metrics_toon(metrics_path)
        if not phases:
            continue
        phase_tokens = {p.phase: p.total_tokens for p in phases}
        total = sum(phase_tokens.values())
        tasks_dir = inputs.plan_dir / "tasks"
        task_count = len(list(tasks_dir.glob("TASK-*.json"))) if tasks_dir.is_dir() else 0
        files = inputs.modified_files_count or inputs.affected_files_count
        rows.append(
            _TokenEconomicsRow(
                plan_id=inputs.plan_id,
                change_type=inputs.change_type or "",
                scope_estimate=inputs.scope_estimate or "",
                files=files,
                tasks=task_count,
                session_message_count=_parse_session_message_count(metrics_path),
                total_tokens=total,
                phase_tokens=phase_tokens,
                exec_metrics_blind=phase_tokens.get(_TE_EXECUTE_PHASE, 0) == 0,
            )
        )
    return rows


def _derive_token_economics_thresholds(rows: list[_TokenEconomicsRow]) -> dict[str, float]:
    """Derive every anti-pattern cut-point from the LIVE corpus distribution.

    Returns a dict of corpus-relative thresholds — NONE are hard-coded. Each is a
    `median` / `percentile` over the current corpus, so the same run that flags a
    plan also annotates the cut-point it was measured against. An empty corpus
    yields all-zero thresholds (no plan can then be flagged).

    Cut-point rationale (each mirrors an anti-pattern in the canonical token-economics lesson):
    - `floor_band` — 10th-percentile of plan totals: the non-amortizing overhead
      floor the cheapest plans sit on (anti-pattern A).
    - `median_total` — median plan total: the "big spend" reference for
      big-spend-tiny-footprint (anti-pattern, the tokens/file inversion).
    - `small_footprint` — 25th-percentile of file counts: "tiny footprint".
    - `median_planning_exec_ratio` — median of per-plan planning/execute ratios
      (execute-blind plans excluded): a plan worse than this is planning-heavy
      relative to the corpus, not against a hard-coded 2× (anti-pattern B).
    - `outline_share_p75` / `refine_share_p75` / `finalize_share_p75` —
      75th-percentile of each phase's share distribution: "heavy" is corpus-
      relative, replacing the lesson's literal 30%/25%/35% (anti-pattern C and the
      outline/refine variants).
    - `long_session_p75` — 75th-percentile of session message counts: a long
      session is relative to the corpus, not a fixed 600 (anti-pattern D).
    """
    if not rows:
        return {
            "floor_band": 0.0,
            "median_total": 0.0,
            "small_footprint": 0.0,
            "median_planning_exec_ratio": 0.0,
            "outline_share_p75": 0.0,
            "refine_share_p75": 0.0,
            "finalize_share_p75": 0.0,
            "long_session_p75": 0.0,
            "corpus_outline_share": 0.0,
            "corpus_refine_share": 0.0,
            "corpus_finalize_share": 0.0,
            "corpus_execute_share": 0.0,
            "floor_has_spread": 0.0,
            "big_spend_has_spread": 0.0,
        }

    totals = [float(r.total_tokens) for r in rows]
    file_counts = [float(r.files) for r in rows if r.files > 0]
    message_counts = [float(r.session_message_count) for r in rows if r.session_message_count > 0]
    planning_exec_ratios = [
        r.planning_tokens / r.execute_tokens
        for r in rows
        if not r.exec_metrics_blind and r.execute_tokens > 0
    ]
    outline_shares = [r.phase_share("3-outline") for r in rows]
    refine_shares = [r.phase_share("2-refine") for r in rows]
    finalize_shares = [r.phase_share("6-finalize") for r in rows]

    # Corpus-wide per-phase distribution: each phase's tokens as a fraction of the
    # whole corpus total (the lesson's "X% of corpus tokens reach phase Y" line).
    grand_total = sum(r.total_tokens for r in rows)
    corpus_phase = {
        p: (sum(r.phase_tokens.get(p, 0) for r in rows) / grand_total if grand_total else 0.0)
        for p in _TE_PHASES
    }

    # Spread guards for the corpus-relative OUTLIER flags. Both `fixed_overhead_floor`
    # and `big_spend_tiny_footprint` are outlier detectors that carry signal only
    # when the plan-total distribution has a genuine tail on the relevant side. In a
    # degenerate corpus of near-identical plans the percentile band collapses
    # (p10 == median == max), so `total <= p10` and `total >= median` both trivially
    # catch EVERY plan — the "fire on everything" failure the check's dynamic-
    # threshold rationale explicitly exists to avoid. Each side gets its own guard:
    #   floor_has_spread     — the cheap decile (p10) sits strictly BELOW the median,
    #                          i.e. there is a genuine low tail distinct from the
    #                          middle. (Uniform corpus → p10 == median → no floor.)
    #   big_spend_has_spread — some plan outspends the median (max > median), i.e.
    #                          there is a genuine HIGH tail. (Uniform corpus →
    #                          max == median → no "big spend" outlier.)
    median_total = median(totals)
    floor_has_spread = percentile(totals, 10) < median_total
    big_spend_has_spread = bool(totals) and max(totals) > median_total

    return {
        "floor_band": percentile(totals, 10),
        "median_total": median_total,
        "small_footprint": percentile(file_counts, 25) if file_counts else 0.0,
        "median_planning_exec_ratio": median(planning_exec_ratios) if planning_exec_ratios else 0.0,
        "outline_share_p75": percentile(outline_shares, 75),
        "refine_share_p75": percentile(refine_shares, 75),
        "finalize_share_p75": percentile(finalize_shares, 75),
        "long_session_p75": percentile(message_counts, 75) if message_counts else 0.0,
        "corpus_outline_share": corpus_phase["3-outline"],
        "corpus_refine_share": corpus_phase["2-refine"],
        "corpus_finalize_share": corpus_phase["6-finalize"],
        "corpus_execute_share": corpus_phase["5-execute"],
        "floor_has_spread": 1.0 if floor_has_spread else 0.0,
        "big_spend_has_spread": 1.0 if big_spend_has_spread else 0.0,
    }


def _token_economics_flags(row: _TokenEconomicsRow, thr: dict[str, float]) -> list[str]:
    """Compute the corpus-relative anti-pattern flags for one plan.

    Every comparison is against a `thr[...]` cut-point that
    `_derive_token_economics_thresholds` measured from the live corpus on this
    run — no literal magic number appears here. Each flag annotates the value and
    the floating cut-point it was measured against so the read-out is
    self-describing. The `exec_metrics_blind` floors annotation (mandated by the
    check sub-document) marks that the plan's flags are computed on under-counted
    data because its execute phase recorded zero tokens.
    """
    flags: list[str] = []

    # exec_metrics_blind — structural recording fact (execute total == 0). Listed
    # first so the reader knows every downstream number is a floor for this plan.
    if row.exec_metrics_blind:
        flags.append("exec_metrics_blind(5-execute=0;floors:tokens_per_*,planning_gt_exec)")

    # fixed_overhead_floor — a plan sitting on the corpus floor band (cheapest
    # decile) AND with a tiny footprint is paying the non-amortizing 6-phase tax.
    # Gated on `floor_has_spread`: in a degenerate (near-uniform) corpus the floor
    # band collapses onto the median and every plan would trivially trip this — an
    # outlier flag must require a corpus with an actual cheap tail (p10 < median).
    if (
        thr["floor_has_spread"] > 0
        and thr["floor_band"] > 0
        and row.total_tokens <= thr["floor_band"]
        and thr["small_footprint"] > 0
        and row.files <= thr["small_footprint"]
    ):
        flags.append(
            f"fixed_overhead_floor({row.total_tokens:,}tok<=p10={thr['floor_band']:,.0f}"
            f";{row.files}f<=p25={thr['small_footprint']:.0f})"
        )

    # planning_gt_exec — planning trio outspends execution by more than the corpus
    # median planning/execute ratio. Only meaningful when execute is measured.
    if (
        not row.exec_metrics_blind
        and row.execute_tokens > 0
        and thr["median_planning_exec_ratio"] > 0
    ):
        ratio = row.planning_tokens / row.execute_tokens
        if ratio > thr["median_planning_exec_ratio"]:
            flags.append(
                f"planning_gt_exec({ratio:.1f}x>median={thr['median_planning_exec_ratio']:.1f}x)"
            )

    # outline_heavy / refine_heavy / finalize_heavy — phase share at/above the
    # corpus 75th-percentile for that phase (corpus-relative, not a fixed %).
    for phase, key, label in (
        ("3-outline", "outline_share_p75", "outline_heavy"),
        ("2-refine", "refine_share_p75", "refine_heavy"),
        ("6-finalize", "finalize_share_p75", "finalize_heavy"),
    ):
        share = row.phase_share(phase)
        cut = thr[key]
        if cut > 0 and share >= cut:
            flags.append(f"{label}({share:.0%}>=p75={cut:.0%})")

    # big_spend_tiny_footprint — total at/above corpus median while footprint is in
    # the corpus bottom quartile: the tokens/file inversion the lesson names.
    # Gated on `big_spend_has_spread`: when no plan outspends the corpus median (a
    # uniform corpus, max == median) there is no "big spend" outlier — the
    # `>= median` test would otherwise catch every plan, the exact "fire on
    # everything" degeneracy.
    if (
        thr["big_spend_has_spread"] > 0
        and thr["median_total"] > 0
        and row.total_tokens >= thr["median_total"]
        and thr["small_footprint"] > 0
        and row.files > 0
        and row.files <= thr["small_footprint"]
    ):
        flags.append(
            f"big_spend_tiny_footprint({row.total_tokens:,}tok>=median={thr['median_total']:,.0f}"
            f";{row.files}f<=p25={thr['small_footprint']:.0f})"
        )

    # long_session — message count at/above the corpus 75th-percentile.
    if thr["long_session_p75"] > 0 and row.session_message_count >= thr["long_session_p75"]:
        flags.append(
            f"long_session({row.session_message_count}msgs>=p75={thr['long_session_p75']:.0f})"
        )

    return flags


def cross_token_economics(all_inputs: list[PlanInputs]) -> dict[str, Any]:
    """Compute per-plan token economics + corpus aggregates with dynamic flags.

    Returns a result dict consumed by `emit_token_economics_block`. The per-plan
    rows carry shares, efficiency ratios, and the corpus-relative anti-pattern
    flag list; the corpus aggregates carry per-change_type and per-scope_estimate
    means plus the corpus per-phase distribution and the derived (floating)
    thresholds. Best-effort: an empty corpus yields all-zero aggregates and no
    flagged rows rather than raising.
    """
    rows = _collect_token_economics_rows(all_inputs)
    thresholds = _derive_token_economics_thresholds(rows)

    plan_rows: list[dict[str, Any]] = []
    for r in sorted(rows, key=lambda x: -x.total_tokens):
        flags = _token_economics_flags(r, thresholds)
        plan_rows.append(
            {
                "plan_id": r.plan_id,
                "change_type": r.change_type,
                "scope": r.scope_estimate,
                "files": r.files,
                "tasks": r.tasks,
                "msgs": r.session_message_count,
                "total_tokens": r.total_tokens,
                "tokens_per_file": r.tokens_per_file,
                "tokens_per_task": r.tokens_per_task,
                "exec_blind": r.exec_metrics_blind,
                "flags": flags,
            }
        )

    # Aggregates by change_type and scope_estimate: count, summed/avg tokens, avg
    # files, and corpus-amortized tokens/file (the lesson's by-dimension table).
    def _aggregate(dimension: str) -> list[dict[str, Any]]:
        buckets: dict[str, dict[str, Any]] = {}
        for r in rows:
            key = getattr(r, dimension) or "(unset)"
            b = buckets.setdefault(key, {"n": 0, "total": 0, "files": 0})
            b["n"] += 1
            b["total"] += r.total_tokens
            b["files"] += r.files
        out: list[dict[str, Any]] = []
        for key, b in buckets.items():
            n = b["n"]
            out.append(
                {
                    "value": key,
                    "n": n,
                    "avg_tokens": b["total"] // n if n else 0,
                    "avg_files": round(b["files"] / n, 1) if n else 0.0,
                    "tokens_per_file": b["total"] // b["files"] if b["files"] else 0,
                }
            )
        out.sort(key=lambda x: -int(x["avg_tokens"]))
        return out

    return {
        "plans_in_corpus": len(rows),
        "rows": plan_rows,
        "by_change_type": _aggregate("change_type"),
        "by_scope": _aggregate("scope_estimate"),
        "thresholds": thresholds,
    }


# ---------------------------------------------------------------------------
# Cross-plan: quality-chain
# ---------------------------------------------------------------------------
#
# Classifies every `artifacts/findings/*.jsonl` finding across the corpus along
# two orthogonal axes and studies the SHIFT-LEFT overlap: what the PR auto-review
# bot caught that the cheaper, earlier quality mechanisms (build, self-review) did
# not. Operationalizes the prototype `.plan/temp/quality_chain.py` deep-dive as a
# repeatable check on the same `read_jsonl` reader the `quality-verification`
# check uses.
#
# MECHANISM — which quality gate surfaced the finding:
#   build         — a build/test/compile failure (`test-failure.jsonl`,
#                   `build-error.jsonl`).
#   self-review   — a Q-Gate / assessment / qgate-sourced finding the plan caught
#                   itself before opening the PR (`qgate-*.jsonl`,
#                   `assessments.jsonl`, `source == "qgate"`).
#   auto-review   — a PR-bot comment (`pr-comment.jsonl` whose detail names the
#                   bot, e.g. `gemini`). The shift-left subject: an issue the bot
#                   caught that build+self-review missed.
#   human-review  — a human PR comment / `source == "user_review"` finding.
#   other         — anything that does not classify above.
#
# RESOLUTION — what disposition the finding received, derived from `resolution`
# + `resolution_detail` regex (mirrors the prototype's `resolution_bucket`):
#   direct_fix    — fixed in place (resolution `fixed`, no rerun marker) or
#                   `taken_into_account` without a loop-back marker.
#   loop_back     — `taken_into_account` whose detail names a follow-up TASK /
#                   deliverable (the fix was deferred into a later step).
#   rerun_flake   — `fixed` whose detail names a transient / re-run / flake cause.
#   accepted      — `accepted` (acknowledged, not actioned).
#   suppressed    — `suppressed`.
#   pending       — `pending` / `none` / empty (unresolved at archive time).
#   lesson        — `promoted` is truthy (the finding became a lesson).
#
# SHIFT-LEFT TIERING — for every `auto_review_only` finding (an auto-review
# finding the plan did NOT also catch via build/self-review), grade how
# completely the `ext-self-review-plan-marshall` deterministic surfacer COULD have
# surfaced it pre-submission, so the read-out separates "the structural review
# would have caught this" from "only a cognitive PR review could". Tiers map to
# the surfacer's published candidate categories (regexes, user-facing strings,
# markdown sections, symmetric pairs, flag-guard pairs, contract sources,
# schema-bearing files):
#   Tier 1 (deterministic-surfaceable) — the finding body names a surfacer
#           candidate category by keyword (regex / wording / duplication / symmetric
#           pair / flag guard / contract / schema). The pre-submission structural
#           review's bounded surface scan would have flagged the exact line.
#   Tier 2 (structural-but-cognitive)  — a structural defect class the surfacer
#           anchors but does not auto-flag (naming, docstring/JavaDoc, dead code,
#           import ordering) — the surface scan narrows it, the LLM pass confirms.
#   Tier 3 (semantic) — a correctness / logic / behavioral finding no deterministic
#           surface can reach; only build or a cognitive review catches it.
#   Tier 4 (unclassified) — body too sparse to tier.
# The lower the tier, the stronger the shift-left signal: a Tier-1 auto_review_only
# finding is one the project paid a full PR round-trip for that a pre-submission
# `self_review surface` pass would have caught for free.

# Findings whose filename marks a build/test mechanism.
_QC_BUILD_FILES = {"test-failure.jsonl", "build-error.jsonl"}

# resolution_detail signatures (mirror the prototype's RERUN / LOOPBACK_DETAIL).
_QC_RERUN_RE = re.compile(
    r"re-run|precondition race|stale pre-clamp|transient|flake", re.IGNORECASE
)
_QC_LOOPBACK_RE = re.compile(
    r"TASK-|to be created by|Added .* step|addressed by|deliverable", re.IGNORECASE
)

# Bot-author signature inside a pr-comment detail body — an auto-review (vs a
# human PR comment).
_QC_BOT_RE = re.compile(r"gemini|copilot|bot|automated", re.IGNORECASE)

# Canonical axis orderings — the matrix columns/rows read off these so every
# plan's matrix and the corpus totals share one stable shape.
_QC_MECHANISMS = ["build", "self-review", "auto-review", "human-review", "other"]
_QC_RESOLUTIONS = [
    "direct_fix",
    "loop_back",
    "rerun_flake",
    "accepted",
    "suppressed",
    "rejected",
    "pending",
    "lesson",
]

# Shift-left Tier 1 — body keywords that map 1:1 onto a deterministic surfacer
# candidate category (regexes, user-facing strings, markdown sections, symmetric
# pairs, flag-guard pairs, contract sources, schema-bearing files).
_QC_TIER1_RE = re.compile(
    r"\bregex\b|\bpattern\b|over-?fit|user-facing|wording|disambiguat"
    r"|duplicat|\bdupe\b|symmetric|sibling pair|flag[- ]?guard|--[a-z]"
    r"|contract|schema|toon block|json block|markdown section",
    re.IGNORECASE,
)
# Shift-left Tier 2 — structural defect classes the surfacer anchors but does not
# itself auto-flag (the LLM pass confirms against the narrowed surface).
#
# `comment` is intentionally NOT a bare alternation here: a defect ABOUT a code
# comment must carry a defect qualifier (`stale|outdated|dead|TODO` comment, or a
# `typo` that the separate alternation already covers). The bare word "comment"
# is review-process noise — "see comment", "left a comment", "as per comment" are
# pointers into a PR thread, not structural defects, and must fall through to the
# Tier-4 (too-sparse-to-tier) bucket rather than masquerade as a Tier-2 finding.
_QC_TIER2_RE = re.compile(
    r"\bnaming\b|\brename\b|docstring|javadoc|\bdoc\b|dead code|unused"
    r"|import order|\bI001\b|unreachable|typo"
    r"|(?:stale|outdated|dead|todo)\s+comment",
    re.IGNORECASE,
)
# Shift-left Tier 3 — semantic / behavioral classes no deterministic surface can
# reach.
_QC_TIER3_RE = re.compile(
    r"\blogic\b|\bbug\b|incorrect|wrong|race|edge case|null|off-by|behavi"
    r"|regression|crash|exception|boundary|semantic",
    re.IGNORECASE,
)


def _qc_mechanism(fname: str, obj: dict[str, Any]) -> str:
    """Classify which quality MECHANISM surfaced a finding (prototype port)."""
    if fname in _QC_BUILD_FILES:
        return "build"
    if fname == "pr-comment.jsonl":
        detail = str(obj.get("detail") or "")
        return "auto-review" if _QC_BOT_RE.search(detail) else "human-review"
    if fname == "assessments.jsonl" or fname.startswith("qgate-"):
        return "self-review"
    source = obj.get("source")
    if source == "user_review":
        return "human-review"
    if source == "qgate":
        return "self-review"
    return "other"


def _qc_resolution(obj: dict[str, Any]) -> str:
    """Classify a finding's RESOLUTION bucket (prototype port).

    `promoted` short-circuits to `lesson`; otherwise the `resolution` field is
    refined by a `resolution_detail` regex (rerun/flake vs direct, loop-back vs
    direct).
    """
    if obj.get("promoted"):
        return "lesson"
    res = str(obj.get("resolution") or "none").lower()
    detail = str(obj.get("resolution_detail") or "")
    if res == "fixed":
        return "rerun_flake" if _QC_RERUN_RE.search(detail) else "direct_fix"
    if res == "taken_into_account":
        return "loop_back" if _QC_LOOPBACK_RE.search(detail) else "direct_fix"
    if res in {"accepted", "suppressed", "rejected"}:
        return res
    # Everything else — pending/none/empty AND any unrecognized resolution —
    # buckets to `pending` rather than returning an unbucketed value. Returning
    # an unknown resolution directly KeyError-crashed the matrix when the
    # ext-point-verify `rejected` disposition was introduced (#788); coercing an
    # unknown disposition to the genuine-severity `pending` bucket surfaces it as
    # unresolved instead of crashing, until it earns its own explicit bucket.
    return "pending"


def _qc_shift_left_tier(obj: dict[str, Any]) -> int:
    """Grade how deterministically the surfacer could have caught a finding.

    Returns 1 (deterministic-surfaceable) … 4 (unclassified). Lower is a stronger
    shift-left signal — a Tier-1 finding is one a pre-submission
    `self_review surface` pass would have flagged on a bounded surface, so paying
    a full PR round-trip for it is avoidable rework.
    """
    body = " ".join(
        str(obj.get(k) or "")
        for k in ("title", "detail", "resolution_detail")
    )
    if _QC_TIER1_RE.search(body):
        return 1
    if _QC_TIER2_RE.search(body):
        return 2
    if _QC_TIER3_RE.search(body):
        return 3
    return 4


@dataclass
class _QualityChainPlan:
    plan_id: str
    # matrix[mechanism][resolution] = count
    matrix: dict[str, dict[str, int]]
    mech_total: dict[str, int]
    findings: list[dict[str, Any]]


def _collect_quality_chain(all_inputs: list[PlanInputs]) -> list[_QualityChainPlan]:
    """Build a per-plan mechanism×resolution matrix + per-finding record list.

    Reuses `read_jsonl` over each plan's `artifacts/findings/*.jsonl` (the same
    reader `check_quality_verification` uses). Plans with no findings directory
    are omitted. Each surfaced finding record carries its plan, mechanism,
    resolution, the source jsonl filename, a truncated title, and — for
    auto-review findings only — its shift-left tier.
    """
    plans: list[_QualityChainPlan] = []
    for inputs in all_inputs:
        findings_dir = inputs.plan_dir / "artifacts" / "findings"
        if not findings_dir.is_dir():
            continue
        matrix: dict[str, dict[str, int]] = {
            m: dict.fromkeys(_QC_RESOLUTIONS, 0) for m in _QC_MECHANISMS
        }
        mech_total: dict[str, int] = dict.fromkeys(_QC_MECHANISMS, 0)
        records: list[dict[str, Any]] = []
        for jsonl in sorted(findings_dir.glob("*.jsonl")):
            for obj in read_jsonl(jsonl):
                mech = _qc_mechanism(jsonl.name, obj)
                res = _qc_resolution(obj)
                matrix[mech][res] += 1
                mech_total[mech] += 1
                tier = _qc_shift_left_tier(obj) if mech == "auto-review" else 0
                records.append(
                    {
                        "plan_id": inputs.plan_id,
                        "mechanism": mech,
                        "resolution": res,
                        "source_file": jsonl.name,
                        "title": str(obj.get("title") or obj.get("type") or "")[:80],
                        "shift_left_tier": tier,
                    }
                )
        if mech_total["build"] + sum(mech_total[m] for m in _QC_MECHANISMS) == 0:
            # No findings at all in this plan's directory — still record the plan
            # so the matrix shows a clean (all-zero) chain rather than dropping it.
            pass
        plans.append(
            _QualityChainPlan(
                plan_id=inputs.plan_id,
                matrix=matrix,
                mech_total=mech_total,
                findings=records,
            )
        )
    return plans


def _quality_chain_flags(plan: _QualityChainPlan) -> list[str]:
    """Compute the chain anti-pattern flags for one plan.

    - `build_pending_pile` — a pile of build findings left `pending` at archive
      time (a build-failure backlog the plan never cleared).
    - `auto_review_only` — the plan carries auto-review findings but recorded ZERO
      build and ZERO self-review findings: the PR bot was the only quality gate
      that fired, so everything shifted right to the most expensive stage.
    - `review_body_duplicate` — the same finding title appears under BOTH
      self-review and auto-review (the bot re-reported what the plan already
      caught — duplicated review effort).
    - `no_qgate6` — the plan recorded findings but ZERO self-review findings: it
      reached the PR with no Q-Gate / assessment self-review surface at all.
    """
    flags: list[str] = []
    m = plan.matrix

    build_pending = m["build"]["pending"]
    if build_pending >= 2:
        flags.append(f"build_pending_pile({build_pending})")

    auto_total = plan.mech_total["auto-review"]
    build_total = plan.mech_total["build"]
    self_total = plan.mech_total["self-review"]
    if auto_total > 0 and build_total == 0 and self_total == 0:
        flags.append(f"auto_review_only({auto_total})")

    # Duplicate finding titles spanning self-review and auto-review.
    self_titles = {
        f["title"].lower()
        for f in plan.findings
        if f["mechanism"] == "self-review" and f["title"]
    }
    auto_titles = {
        f["title"].lower()
        for f in plan.findings
        if f["mechanism"] == "auto-review" and f["title"]
    }
    dupes = self_titles & auto_titles
    if dupes:
        flags.append(f"review_body_duplicate({len(dupes)})")

    total_findings = sum(plan.mech_total.values())
    if total_findings > 0 and self_total == 0:
        flags.append("no_qgate6")

    return flags


def cross_quality_chain(all_inputs: list[PlanInputs]) -> dict[str, Any]:
    """Classify the corpus findings by mechanism×resolution + shift-left study.

    Returns a result dict consumed by `emit_quality_chain_block`. Carries the
    per-plan matrix rows (with chain anti-pattern flags), the corpus-total
    mechanism×resolution matrix, the consolidated per-finding row list (each with
    its D1-stamped severity decided by the emitter), and the shift-left tier
    histogram over `auto_review_only` findings. Best-effort: an empty corpus
    yields all-zero aggregates and no rows rather than raising.
    """
    plans = _collect_quality_chain(all_inputs)

    corpus: dict[str, dict[str, int]] = {
        mech: dict.fromkeys(_QC_RESOLUTIONS, 0) for mech in _QC_MECHANISMS
    }
    plan_rows: list[dict[str, Any]] = []
    all_findings: list[dict[str, Any]] = []
    tier_histogram = {1: 0, 2: 0, 3: 0, 4: 0}

    for plan in sorted(plans, key=lambda p: p.plan_id):
        for mech in _QC_MECHANISMS:
            for res in _QC_RESOLUTIONS:
                corpus[mech][res] += plan.matrix[mech][res]
        flags = _quality_chain_flags(plan)
        plan_rows.append(
            {
                "plan_id": plan.plan_id,
                "build": plan.mech_total["build"],
                "self_review": plan.mech_total["self-review"],
                "auto_review": plan.mech_total["auto-review"],
                "human_review": plan.mech_total["human-review"],
                "other": plan.mech_total["other"],
                "total": sum(plan.mech_total.values()),
                "flags": flags,
            }
        )
        all_findings.extend(plan.findings)
        for f in plan.findings:
            if f["mechanism"] == "auto-review" and f["shift_left_tier"] in tier_histogram:
                tier_histogram[f["shift_left_tier"]] += 1

    return {
        "plans_in_corpus": len(plans),
        "rows": plan_rows,
        "corpus_matrix": corpus,
        "findings": all_findings,
        "tier_histogram": tier_histogram,
        "mechanisms": _QC_MECHANISMS,
        "resolutions": _QC_RESOLUTIONS,
    }


# ---------------------------------------------------------------------------
# Cross-plan: sequence-and-build-minimality
# ---------------------------------------------------------------------------
#
# Reconstructs each plan's call sequence from its plan-scoped
# `logs/script-execution.log` (ordered, unambiguous), buckets every call into a
# phase by the `logs/work.log` `[DISPATCH] role=phase-N` timeline, and studies
# BUILD MINIMALITY: the user's thesis that a build after a deliverable should be
# FOCUSED (compile + test-compile + test-run for the CHANGED module only) and
# should only run on buildable stuff. Operationalizes the prototype deep-dives
# `.plan/temp/sequence_analysis.py` + `.plan/temp/build_minimality.py` as a
# single repeatable cross-plan check on the same readers the other checks use.
#
# DURATION CLASSIFICATION (thresholds from the centralized THRESHOLDS table — no
# magic number re-declared here):
#   minimal  < build_minimal_seconds   — compile / small scoped run.
#   scoped   build_minimal..build_heavy — single-module tests.
#   heavy    > build_heavy_seconds      — whole-tree verify / all-modules — NOT
#                                          minimal.
#
# BUILD-VERB MINING — the work.log records the actual verb+scope a build ran with
# (`verify`, `module-tests {module}`, `quality-gate`, `coverage`, `compile`). A
# `module-tests` whose argument is a KNOWN module is scoped; otherwise it is an
# all-modules run. This is the qualitative companion to the duration band: the
# duration says "how long", the verb says "what scope".
#
# REDUNDANCY / ANTI-PATTERN FLAGS (per plan):
#   build_churn          — repeated builds clustered within build_clustering_minutes
#                          (a re-run loop rather than one focused build per change).
#   non_minimal_build    — at least one heavy (> build_heavy_seconds) build ran —
#                          a whole-tree verify where a scoped module run sufficed.
#   docs_only_build      — the plan touched no `.py` file (or change_type ==
#                          documentation) yet ran a build — buildable-stuff
#                          violation (the docs-only-build axis).
#   ci_rerun             — more than one CI run directory under artifacts/ci-runs/
#                          (the PR round-trip ran CI more than once). Post-#849/#850
#                          finalize-flow caveat: a SECOND CI pass is now often the
#                          EXPECTED shape, not wasteful churn — the early
#                          baseline-rebase finalize step (`finalize-step-sync-baseline`,
#                          #786) rebases the branch onto origin/main at finalize start
#                          and a post-force-push re-review (#742) legitimately re-runs
#                          CI, and #849's deterministic `ci_verify` + adaptive ci-wait
#                          ratchet make that re-verification cheap and intentional. The
#                          flag therefore counts CI passes; the sub-doc interprets ≥2 as
#                          a rebase/re-review round-trip vs a genuine red→green churn
#                          loop (correlate with quality-chain `loop_back` volume).
#   phase_reentry        — a phase-N role was dispatched more than once. Post-#849/#850
#                          caveat: a 5-execute / 6-finalize re-entry is the EXPECTED
#                          shape of the finalize triage loop-back (the
#                          `loop_back_without_asking` inline-replay cycle), not
#                          necessarily redundant phase work — a loop-back that fixed a
#                          real finding is correct-by-design. The sub-doc reads a
#                          6-finalize/5-execute re-entry against the plan's loop_back
#                          resolutions before calling it redundant.
#   arch_over_resolution — architecture calls outnumber build calls by a wide
#                          margin while builds exist (resolution overhead dwarfing
#                          the work it resolves).
#   consecutive_dup      — back-to-back identical (notation, subcommand) calls — a
#                          mechanical double-call. NOTE: over-counts same-verb /
#                          different-args calls (see caveat 3 in the sub-doc).

# Phase-dispatch role marker in work.log: `[DISPATCH] ... role=phase-N...`.
_SBM_DISPATCH_RE = re.compile(r"\[DISPATCH\].*?role=(?P<role>phase-[0-9][a-z-]*)")

# A single script-execution.log call line: timestamp, level, hash, then the
# three-segment notation, the subcommand, and an optional trailing `(N.NNs)`
# duration. Mirrors the prototype SCRIPT regex.
_SBM_CALL_RE = re.compile(
    r"^\[(?P<ts>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})Z\]\s+\[[A-Z]+\]\s+\[[0-9a-f]+\]\s+"
    r"(?P<notation>[a-z0-9-]+:[a-z0-9_-]+:[a-z0-9_-]+)\s+(?P<sub>[^\s(]*)\s*"
    r"(?:\(([0-9.]+)s\))?"
)

# Build-verb mention inside a work.log line: the verb plus an optional
# whitespace-delimited scope argument (a module name when scoped).
_SBM_VERB_RE = re.compile(
    r"\b(module-tests|quality-gate|verify|coverage|compile)\b(?:\s+([a-z][a-z0-9-]+))?"
)

# A pyproject_build run call (the only build notation in this Python project).
def _sbm_is_build(notation: str, sub: str) -> bool:
    return notation.endswith("build-pyproject:pyproject_build") and sub == "run"


# An architecture call (any verb) — the resolution-overhead denominator.
def _sbm_is_arch(notation: str) -> bool:
    return notation.endswith("manage-architecture:architecture")


# The canonical buildable modules in this repo. A `module-tests {arg}` whose arg
# is in this set is a scoped run; otherwise it is an all-modules run.
_SBM_KNOWN_MODULES = {
    "plan-marshall",
    "pm-dev-java",
    "pm-dev-java-cui",
    "pm-dev-frontend",
    "pm-dev-frontend-cui",
    "pm-dev-oci",
    "pm-dev-python",
    "pm-documents",
    "pm-plugin-development",
    "pm-requirements",
}


def _sbm_classify_build(duration: float) -> str:
    """Classify a build by wall-clock duration against the THRESHOLDS bands.

    `unknown` when the duration was not recorded (0.0). Otherwise `minimal`
    (< build_minimal_seconds), `scoped` (build_minimal..build_heavy), or `heavy`
    (> build_heavy_seconds — NOT minimal).
    """
    if duration <= 0:
        return "unknown"
    if duration < float(THRESHOLDS["build_minimal_seconds"]):
        return "minimal"
    if duration < float(THRESHOLDS["build_heavy_seconds"]):
        return "scoped"
    return "heavy"


def _sbm_parse_ts(value: str) -> datetime | None:
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%S")
    except ValueError:
        return None


def _sbm_normalize_role(role: str) -> str:
    """`phase-5-execute` → `5-execute` (drop the leading `phase-` segment)."""
    return role.replace("phase-", "", 1)


def _sequence_build_minimality_plan(inputs: PlanInputs) -> dict[str, Any]:
    """Reconstruct one plan's call sequence + build-minimality signals.

    Reads the plan-scoped `logs/script-execution.log` (ordered call timeline) and
    `logs/work.log` (phase-dispatch markers + build-verb mentions), joins the
    `references.json` / `status.json::metadata` footprint already on `inputs`, and
    counts CI run directories under `artifacts/ci-runs/`. Returns the per-plan row
    dict consumed by the emitter. Best-effort: a plan with no logs degrades to an
    all-zero row rather than raising.
    """
    plan_dir = inputs.plan_dir
    sel = plan_dir / "logs" / "script-execution.log"
    wl = plan_dir / "logs" / "work.log"

    # (1) Ordered call timeline from script-execution.log.
    calls: list[tuple[datetime, str, str, float]] = []
    if sel.is_file():
        try:
            sel_text = sel.read_text(encoding="utf-8", errors="replace")
        except OSError:
            sel_text = ""
        for line in sel_text.splitlines():
            m = _SBM_CALL_RE.match(line)
            if not m:
                continue
            ts = _sbm_parse_ts(m.group("ts"))
            if ts is None:
                continue
            dur = float(m.group(4)) if m.group(4) else 0.0
            calls.append((ts, m.group("notation"), m.group("sub"), dur))

    # (2) Phase-dispatch timeline + per-role dispatch counts from work.log.
    phase_marks: list[tuple[datetime, str]] = []
    role_dispatch: dict[str, int] = defaultdict(int)
    verb_counts = {
        "scoped_mt": 0,
        "all_mt": 0,
        "quality_gate": 0,
        "verify": 0,
        "coverage": 0,
        "compile": 0,
    }
    if wl.is_file():
        try:
            wl_text = wl.read_text(encoding="utf-8", errors="replace")
        except OSError:
            wl_text = ""
        for line in wl_text.splitlines():
            tm = re.match(r"^\[(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})Z\]", line)
            if tm:
                dm = _SBM_DISPATCH_RE.search(line)
                if dm:
                    ts = _sbm_parse_ts(tm.group(1))
                    if ts is not None:
                        phase_marks.append((ts, dm.group("role")))
                        role_dispatch[dm.group("role")] += 1
        # Build-verb mining over the whole work.log text.
        for vm in _SBM_VERB_RE.finditer(wl_text):
            verb, arg = vm.group(1), vm.group(2)
            if verb == "module-tests":
                if arg in _SBM_KNOWN_MODULES:
                    verb_counts["scoped_mt"] += 1
                else:
                    verb_counts["all_mt"] += 1
            elif verb == "quality-gate":
                verb_counts["quality_gate"] += 1
            elif verb == "verify":
                verb_counts["verify"] += 1
            elif verb == "coverage":
                verb_counts["coverage"] += 1
            elif verb == "compile":
                verb_counts["compile"] += 1

    phase_marks.sort()

    def phase_of(when: datetime) -> str:
        cur = "1-init"
        for mdt, role in phase_marks:
            if when >= mdt:
                cur = _sbm_normalize_role(role)
            else:
                break
        return cur

    # (3) Per-phase call buckets + per-phase build counts/durations.
    per_phase: dict[str, dict[str, float]] = defaultdict(
        lambda: {"calls": 0.0, "builds": 0.0, "build_seconds": 0.0, "arch": 0.0}
    )
    builds: list[tuple[datetime, float]] = []
    arch_calls = 0
    for ts, notation, sub, dur in calls:
        phase = phase_of(ts)
        bucket = per_phase[phase]
        bucket["calls"] += 1
        if _sbm_is_build(notation, sub):
            bucket["builds"] += 1
            bucket["build_seconds"] += dur
            builds.append((ts, dur))
        if _sbm_is_arch(notation):
            bucket["arch"] += 1
            arch_calls += 1

    # (4) Build classification by duration band.
    klass = {"minimal": 0, "scoped": 0, "heavy": 0, "unknown": 0}
    for _, dur in builds:
        klass[_sbm_classify_build(dur)] += 1
    max_build_seconds = max((d for _, d in builds), default=0.0)
    total_build_seconds = sum(d for _, d in builds)

    # (5) Redundancy primitives.
    # consecutive_dup — back-to-back identical (notation, sub). Over-counts
    # same-verb/different-args calls (sub-doc caveat 3).
    consecutive_dup = 0
    prev_key: tuple[str, str] | None = None
    for _, notation, sub, _ in calls:
        key = (notation, sub)
        if key == prev_key:
            consecutive_dup += 1
        prev_key = key

    # build_churn — builds whose start falls within build_clustering_minutes of the
    # previous build's start (a re-run cluster rather than one focused build).
    cluster_window_seconds = float(THRESHOLDS["build_clustering_minutes"]) * 60.0
    churn = 0
    for i in range(1, len(builds)):
        if (builds[i][0] - builds[i - 1][0]).total_seconds() < cluster_window_seconds:
            churn += 1

    # CI run directories.
    ci_runs = 0
    ci_dir = plan_dir / "artifacts" / "ci-runs"
    if ci_dir.is_dir():
        ci_runs = sum(1 for d in ci_dir.iterdir() if d.is_dir())

    # phase_reentry — any phase role dispatched more than once.
    phase_reentry_roles = sorted(
        _sbm_normalize_role(role) for role, n in role_dispatch.items() if n > 1
    )

    span_seconds = (calls[-1][0] - calls[0][0]).total_seconds() if len(calls) > 1 else 0.0

    # Footprint: docs-only when no `.py` file was touched (or change_type is
    # documentation). Reuses the inputs already collected; falls back to reading
    # references for the actual file list (collect_inputs only kept counts).
    refs = read_json(plan_dir / "references.json") or {}
    affected = refs.get("modified_files") or refs.get("affected_files") or []
    py_files = [f for f in affected if isinstance(f, str) and f.endswith(".py")]
    docs_only = inputs.change_type == "documentation" or (bool(affected) and not py_files)
    n_builds = len(builds)

    # (6) Flags.
    flags: list[str] = []
    if churn > 0:
        flags.append(f"build_churn({churn}<{int(THRESHOLDS['build_clustering_minutes'])}m)")
    if klass["heavy"] > 0:
        flags.append(
            f"non_minimal_build({klass['heavy']}heavy>{int(THRESHOLDS['build_heavy_seconds'])}s)"
        )
    if docs_only and n_builds > 0:
        flags.append(f"docs_only_build({n_builds}builds;no_py)")
    if ci_runs > 1:
        flags.append(f"ci_rerun({ci_runs})")
    if phase_reentry_roles:
        flags.append(f"phase_reentry({';'.join(phase_reentry_roles)})")
    # arch_over_resolution — architecture calls dwarf build calls (>= 5x) while
    # builds exist: resolution overhead outweighing the work it resolves.
    if n_builds > 0 and arch_calls >= 5 * n_builds:
        flags.append(f"arch_over_resolution(arch={arch_calls};builds={n_builds})")
    if consecutive_dup > 0:
        flags.append(f"consecutive_dup({consecutive_dup})")

    # Phase graph string: `phase:calls(builds=B,arch=A)` per phase in canonical order.
    phase_order = [
        "1-init", "2-refine", "3-outline", "4-plan", "5-execute", "6-finalize",
    ]
    ordered_phases = sorted(
        per_phase.keys(),
        key=lambda p: phase_order.index(p) if p in phase_order else 99,
    )
    graph_parts: list[str] = []
    for phase in ordered_phases:
        b = per_phase[phase]
        extra = []
        if b["builds"]:
            extra.append(f"b={int(b['builds'])}")
        if b["arch"]:
            extra.append(f"a={int(b['arch'])}")
        suffix = f"({'/'.join(extra)})" if extra else ""
        graph_parts.append(f"{phase}:{int(b['calls'])}{suffix}")
    phase_graph = " ".join(graph_parts)

    verb_str = (
        f"smt={verb_counts['scoped_mt']};amt={verb_counts['all_mt']};"
        f"qg={verb_counts['quality_gate']};vf={verb_counts['verify']};"
        f"cov={verb_counts['coverage']};cmp={verb_counts['compile']}"
    )

    return {
        "plan_id": inputs.plan_id,
        "change_type": inputs.change_type or "",
        "calls": len(calls),
        "span_seconds": int(span_seconds),
        "builds": n_builds,
        "build_minimal": klass["minimal"],
        "build_scoped": klass["scoped"],
        "build_heavy": klass["heavy"],
        "max_build_seconds": int(max_build_seconds),
        "total_build_seconds": int(total_build_seconds),
        "build_churn": churn,
        "arch_calls": arch_calls,
        "ci_runs": ci_runs,
        "consecutive_dup": consecutive_dup,
        "docs_only": docs_only,
        "phase_reentry": ";".join(phase_reentry_roles),
        "verbs": verb_str,
        "phase_graph": phase_graph,
        "flags": flags,
    }


def cross_sequence_build_minimality(all_inputs: list[PlanInputs]) -> dict[str, Any]:
    """Reconstruct the per-plan call sequence + build-minimality signal set.

    Returns a result dict consumed by `emit_sequence_build_minimality_block`. Each
    per-plan row carries the call/build/verb counts, the per-phase graph, and the
    redundancy/anti-pattern flag list; the corpus aggregates carry the duration-band
    totals, the build-verb totals, and the corpus build-second total. Best-effort:
    an empty corpus yields all-zero aggregates and no rows rather than raising.
    """
    rows = [_sequence_build_minimality_plan(i) for i in all_inputs]
    rows.sort(key=lambda r: -int(r["total_build_seconds"]))

    corpus = {
        "minimal": sum(int(r["build_minimal"]) for r in rows),
        "scoped": sum(int(r["build_scoped"]) for r in rows),
        "heavy": sum(int(r["build_heavy"]) for r in rows),
        "builds": sum(int(r["builds"]) for r in rows),
        "build_seconds": sum(int(r["total_build_seconds"]) for r in rows),
        "build_churn": sum(int(r["build_churn"]) for r in rows),
        "ci_runs": sum(int(r["ci_runs"]) for r in rows),
        "consecutive_dup": sum(int(r["consecutive_dup"]) for r in rows),
        "docs_only_build_plans": sum(
            1 for r in rows if r["docs_only"] and int(r["builds"]) > 0
        ),
    }
    return {
        "plans_in_corpus": len(rows),
        "rows": rows,
        "corpus": corpus,
        "build_minimal_seconds": float(THRESHOLDS["build_minimal_seconds"]),
        "build_heavy_seconds": float(THRESHOLDS["build_heavy_seconds"]),
        "build_clustering_minutes": float(THRESHOLDS["build_clustering_minutes"]),
    }


# ---------------------------------------------------------------------------
# Check: input-integrity (per-plan health + corpus data_confidence summary)
# ---------------------------------------------------------------------------
#
# The no-false-healthy FOUNDATION for the whole audit. Every other check reads a
# subset of a plan's structured inputs and reports signals derived from them; if
# those inputs are absent or under-recorded, a "no findings" verdict from a peer
# check is a FALSE HEALTHY — the check saw nothing because there was nothing to
# see, not because the plan was clean. This check makes that distinction explicit
# and deterministic: it reports, per plan, which canonical inputs are present and
# healthy, and flags the three input-health defects that silently floor every
# downstream check.
#
# PER-PLAN HEALTH COLUMNS — presence booleans for the canonical input set:
#   has_execution   — `execution.toon` (the composed manifest).
#   has_metrics     — `work/metrics.toon` (per-phase token/duration recording).
#   has_references  — `references.json` (scope/footprint/deliverables).
#   has_tasks       — a non-empty `tasks/` dir with at least one `TASK-*.json`.
#   has_findings    — a non-empty `artifacts/findings/` dir with at least one
#                     `*.jsonl` finding file.
#   has_script_log  — a non-empty plan-scoped `logs/script-execution.log`.
#
# THREE FLAGS (the defects that floor downstream checks):
#   metrics_blind          — any phase that SHOULD carry token data recorded zero
#                            tokens. The 5-execute phase is the load-bearing case:
#                            a zero-token execute means every token-economics and
#                            token-trend number for the plan is under-counted, so
#                            the plan's downstream rows are a FLOOR, not the truth.
#                            Other zero-token phases are also surfaced, but a
#                            zero-token 5-execute escalates the data_confidence
#                            bucket to `blind`.
#   incomplete_lifecycle   — the plan never recorded a 5-execute OR a 6-finalize
#                            phase (no such section in metrics.toon). The plan did
#                            not run to completion through the recorded lifecycle,
#                            so completeness-dependent checks (pr-merge-velocity,
#                            quality-chain resolution) read a truncated history.
#   missing_dispatch_markers — the plan's `logs/work.log` carries no
#                            `[DISPATCH] role=phase-N` lines, so the
#                            sequence-and-build-minimality phase attribution cannot
#                            bucket calls into phases (it folds everything into
#                            1-init — the finalize-fold conflation caveat).
#
# CORPUS data_confidence SUMMARY — a three-bucket tally over the scanned plans:
#   fully-recorded — no flag fired: every canonical input present, no blind phase,
#                    a complete lifecycle, and dispatch markers present.
#   partial        — at least one input absent or a non-execute zero-token phase /
#                    incomplete lifecycle / missing dispatch markers, but the
#                    5-execute phase DID record tokens (not blind).
#   blind          — the 5-execute phase recorded zero tokens (metrics_blind on the
#                    load-bearing phase). Every downstream number for these plans is
#                    a FLOOR — the audit may NOT claim "all healthy" over them.

# The phases whose zero-token recording is a `metrics_blind` defect rather than an
# expected absence. 1-init can legitimately be tiny; the execution and finalize
# phases always carry real work, so a zero-token recording there is a recording
# defect. 5-execute is the load-bearing case that escalates to `blind`.
_II_DATA_BEARING_PHASES = ["4-plan", "5-execute", "6-finalize"]
_II_EXECUTE_PHASE = "5-execute"
_II_FINALIZE_PHASE = "6-finalize"

# work.log dispatch-marker shape — reused from sequence-and-build-minimality's
# `_SBM_DISPATCH_RE` intent: a `[DISPATCH] ... role=phase-N` line.
_II_DISPATCH_RE = re.compile(r"\[DISPATCH\].*?role=phase-[0-9]")


def _ii_has_nonempty_dir(directory: Path, glob: str) -> bool:
    """True when `directory` exists and contains at least one `glob` match."""
    return directory.is_dir() and any(directory.glob(glob))


def _ii_has_nonempty_file(path: Path) -> bool:
    """True when `path` is a file with non-whitespace content."""
    if not path.is_file():
        return False
    try:
        return bool(path.read_text(encoding="utf-8").strip())
    except OSError:
        return False


def check_input_integrity(inputs: PlanInputs) -> dict[str, Any]:
    """Report one plan's input presence/health + the three input-health flags.

    Per-plan deterministic predicate over the plan's canonical inputs. Returns the
    health columns, the three flags (`metrics_blind`, `incomplete_lifecycle`,
    `missing_dispatch_markers`), and a `data_confidence` bucket
    (`fully-recorded` / `partial` / `blind`) the corpus summary tallies. The bucket
    is `blind` exactly when the 5-execute phase recorded zero tokens — the
    load-bearing case that floors every downstream token number for the plan.
    """
    plan_dir = inputs.plan_dir

    # Presence/health of the canonical input set.
    has_execution = (plan_dir / "execution.toon").is_file()
    metrics_path = plan_dir / "work" / "metrics.toon"
    has_metrics = metrics_path.is_file()
    has_references = (plan_dir / "references.json").is_file()
    has_tasks = _ii_has_nonempty_dir(plan_dir / "tasks", "TASK-*.json")
    has_findings = _ii_has_nonempty_dir(
        plan_dir / "artifacts" / "findings", "*.jsonl"
    )
    has_script_log = _ii_has_nonempty_file(
        plan_dir / "logs" / "script-execution.log"
    )

    # Per-phase token recording.
    phases = parse_metrics_toon(metrics_path)
    phase_tokens = {p.phase: p.total_tokens for p in phases}
    recorded_phases = set(phase_tokens)
    # #812 recorded-partiality markers: a phase the recorder KNOWS is unrecorded
    # is recorded-partial by design, NOT an accidental zero-token blindness. The
    # check consumes this signal instead of inferring blindness from zero tokens
    # alone — a marker-explained zero-token phase is `partial`, not `blind`.
    _partial, unrecorded_phases = parse_metrics_partiality(metrics_path)

    # metrics_blind — any data-bearing phase recorded zero tokens that the #812
    # markers do NOT explain. A zero-token phase listed in `unrecorded_phases` is
    # recorded-partial by design and is excluded from the blind set.
    blind_phases = [
        ph
        for ph in _II_DATA_BEARING_PHASES
        if ph in recorded_phases
        and phase_tokens.get(ph, 0) == 0
        and ph not in unrecorded_phases
    ]
    # execute_blind is a GENUINE (accidental) blind: 5-execute recorded zero
    # tokens with no recorded-partiality marker to explain it. A marker-explained
    # zero-token execute is recorded-partial (bucket `partial`), not `blind`.
    execute_recorded_partial = _II_EXECUTE_PHASE in unrecorded_phases
    execute_blind = (
        phase_tokens.get(_II_EXECUTE_PHASE, None) == 0 and not execute_recorded_partial
    )
    metrics_blind = ";".join(blind_phases)

    # incomplete_lifecycle — no 5-execute OR no 6-finalize section recorded.
    missing_lifecycle_phases = [
        ph
        for ph in (_II_EXECUTE_PHASE, _II_FINALIZE_PHASE)
        if ph not in recorded_phases
    ]
    incomplete_lifecycle = ";".join(missing_lifecycle_phases)

    # missing_dispatch_markers — no `[DISPATCH] role=phase-N` line in work.log.
    work_log = plan_dir / "logs" / "work.log"
    has_dispatch_markers = False
    if work_log.is_file():
        try:
            wl_text = work_log.read_text(encoding="utf-8", errors="replace")
        except OSError:
            wl_text = ""
        has_dispatch_markers = bool(_II_DISPATCH_RE.search(wl_text))
    missing_dispatch_markers = "" if has_dispatch_markers else "true"

    # data_confidence bucket: blind > partial > fully-recorded.
    any_input_missing = not all(
        [has_execution, has_metrics, has_references, has_tasks, has_script_log]
    )
    any_defect = bool(
        metrics_blind or incomplete_lifecycle or missing_dispatch_markers
    )
    if execute_blind:
        data_confidence = "blind"
    elif any_input_missing or any_defect or execute_recorded_partial:
        # A #812-marker-explained zero-token execute is recorded-partial: it is
        # the `partial` bucket, never the false-healthy `fully-recorded`.
        data_confidence = "partial"
    else:
        data_confidence = "fully-recorded"

    return {
        "plan_id": inputs.plan_id,
        "has_execution": str(has_execution).lower(),
        "has_metrics": str(has_metrics).lower(),
        "has_references": str(has_references).lower(),
        "has_tasks": str(has_tasks).lower(),
        "has_findings": str(has_findings).lower(),
        "has_script_log": str(has_script_log).lower(),
        "metrics_blind": metrics_blind,
        "incomplete_lifecycle": incomplete_lifecycle,
        "missing_dispatch_markers": missing_dispatch_markers,
        "data_confidence": data_confidence,
    }


def _input_integrity_genuine(row: dict[str, Any]) -> bool:
    """Genuine-signal predicate for one input-integrity row.

    Genuine (actionable): the plan has a real input-health defect — a
    `metrics_blind` phase, an `incomplete_lifecycle`, or `missing_dispatch_markers`.
    A genuine row means downstream checks read floored/truncated inputs for the
    plan. Informational: a `fully-recorded` plan, or a plan whose only gap is an
    absent OPTIONAL artifact (e.g. no findings file) with no flag fired.
    """
    return bool(
        row["metrics_blind"]
        or row["incomplete_lifecycle"]
        or row["missing_dispatch_markers"]
    )


def emit_input_integrity_block(rows: list[dict[str, Any]]) -> str:
    """Emit the per-plan input-integrity block + corpus data_confidence summary.

    Each per-plan row carries the input presence/health columns, the three flags,
    the `data_confidence` bucket, and the uniform D1 `severity` column (genuine
    when any flag fired). The block leads with the corpus `data_confidence`
    tally (`fully-recorded` / `partial` / `blind` counts) so the read-out's
    foundation is visible at a glance: a non-zero `blind` count is the structural
    block against any "all healthy" corpus claim.
    """
    confidence_counts = {"fully-recorded": 0, "partial": 0, "blind": 0}
    for r in rows:
        bucket = r["data_confidence"]
        confidence_counts[bucket] = confidence_counts.get(bucket, 0) + 1
    blind_plan_ids = sorted(
        r["plan_id"] for r in rows if r["data_confidence"] == "blind"
    )

    rows, genuine_signal_count = _severity_summary(rows, _input_integrity_genuine)

    out = [
        "check: input-integrity",
        "status: success",
        f"plans_scanned: {len(rows)}",
        # Corpus data_confidence summary — the no-false-healthy foundation. A
        # non-zero blind count means downstream "all healthy" claims are barred.
        f"data_confidence_fully_recorded: {confidence_counts['fully-recorded']}",
        f"data_confidence_partial: {confidence_counts['partial']}",
        f"data_confidence_blind: {confidence_counts['blind']}",
        f"blind_plan_ids: {_cell(';'.join(blind_plan_ids))}",
        f"genuine_signal_count: {genuine_signal_count}",
        (
            f"rows[{len(rows)}]{{plan_id,has_execution,has_metrics,has_references,"
            "has_tasks,has_findings,has_script_log,metrics_blind,"
            "incomplete_lifecycle,missing_dispatch_markers,data_confidence,"
            "severity}:"
        ),
    ]
    for r in rows:
        out.append(
            "  "
            + ",".join(
                _cell(c)
                for c in [
                    r["plan_id"],
                    r["has_execution"],
                    r["has_metrics"],
                    r["has_references"],
                    r["has_tasks"],
                    r["has_findings"],
                    r["has_script_log"],
                    r["metrics_blind"],
                    r["incomplete_lifecycle"],
                    r["missing_dispatch_markers"],
                    r["data_confidence"],
                    r["severity"],
                ]
            )
        )
    return "\n".join(out) + "\n"


# ---------------------------------------------------------------------------
# Check: task-graph-redundancy
# ---------------------------------------------------------------------------
#
# Per-plan adjacency check over `tasks/TASK-*.json`. A plan's task graph is
# reconstructed as adjacency over step targets (a `file_owners: target → owning
# task numbers` map) and verification-command verbs, surfacing five redundancy
# signals. The duplicate-task signal is the `multi_task_file` adjacency map (a
# file edited by ≥2 tasks), not a pairwise count. Heavy in-task builds are
# inferred from the verification command verbs alone — no `execution.toon` join.
# The deliverable→task fan-out outlier threshold is the per-run corpus median,
# computed in `run_checks` across the loaded corpus (not per-row, not persisted).

# `TASK-NNN.json` filename grammar — the three-digit zero-padded task id.
_TASK_FILE_RE = re.compile(r"^TASK-(\d{3})\.json$")

# Heavy build/verify verbs: a per-task verification carrying one of these runs a
# full suite that phase-5 execute / phase-6 finalize already run — duplicated
# compute. Distinct from a scoped/light single-file or `--plan-id`-scoped check.
HEAVY_BUILD_TOKENS = ("module-tests", "quality-gate", "coverage")

# Build-runner notation tokens. A verification command is only a heavy build when
# it both invokes a build runner AND carries a HEAVY_BUILD_TOKENS verb (or the
# full-suite `verify` verb) — a bare `manage-*` call is never a heavy build.
BUILD_RUNNERS = ("pyproject_build", "build-maven", "build-gradle", "build-npm")


def _load_plan_tasks(plan_dir: Path) -> list[dict[str, Any]]:
    """Read every well-formed `tasks/TASK-NNN.json` under a plan dir."""
    tasks_dir = plan_dir / "tasks"
    if not tasks_dir.is_dir():
        return []
    tasks: list[dict[str, Any]] = []
    for tf in sorted(tasks_dir.glob("TASK-*.json")):
        if not _TASK_FILE_RE.match(tf.name):
            continue
        obj = read_json(tf)
        if obj is not None:
            tasks.append(obj)
    return tasks


def _task_targets(task: dict[str, Any]) -> set[str]:
    """Return the set of non-empty step targets a task edits."""
    return {
        s["target"]
        for s in task.get("steps", []) or []
        if isinstance(s, dict) and s.get("target")
    }


def is_heavy_build_cmd(cmd: str) -> bool:
    """True when a verification command runs a HEAVY build/verify suite.

    Verb-only inference (Decision 3): the command must invoke a build runner AND
    carry a `HEAVY_BUILD_TOKENS` verb or the full-suite `verify` verb. A scoped /
    light check (single file, `--plan-id`-scoped) does not match.
    """
    if not any(runner in cmd for runner in BUILD_RUNNERS):
        return False
    if any(token in cmd for token in HEAVY_BUILD_TOKENS):
        return True
    # `... run --command-args "verify ..."` is the full-suite verify verb.
    return bool(re.search(r'command-args\s+"?\s*verify\b', cmd)) or '"verify' in cmd


def check_task_graph_redundancy(inputs: PlanInputs) -> dict[str, Any]:
    """Reconstruct one plan's task graph and flag five redundancy signals.

    Adjacency over step targets and verification verbs (Decision 2): a
    `file_owners` map yields `multi_task_file` directly (a file edited by ≥2
    tasks — the primary duplicate-task signal, REPLACING a pairwise count); a
    `(target, intent)` map yields `dup_substep`; heavy in-task builds are inferred
    from the verification verbs via `is_heavy_build_cmd`; `verif_task_fanout`
    counts module_testing/verification tasks; and `deliv_counts` /
    `max_tasks_per_deliverable` are returned for the per-run `deliverable_fanout`
    threshold finalized in `run_checks`. The `deliverable_fanout` cell is stamped
    there (it needs the corpus median); this function leaves it absent.
    """
    tasks = _load_plan_tasks(inputs.plan_dir)

    # (a) multi_task_file — adjacency map target → owning task numbers.
    file_owners: dict[str, set[int]] = {}
    for t in tasks:
        number = int(t.get("number", 0) or 0)
        for target in _task_targets(t):
            file_owners.setdefault(target, set()).add(number)
    multi_task_files = sorted(
        tgt for tgt, owners in file_owners.items() if len(owners) > 1
    )

    # (b) dup_substep — the same (target, intent) baked into >1 task.
    substep_owners: dict[tuple[str, str], set[int]] = {}
    for t in tasks:
        number = int(t.get("number", 0) or 0)
        for s in t.get("steps", []) or []:
            if not isinstance(s, dict) or not s.get("target"):
                continue
            key = (s["target"], str(s.get("intent", "")))
            substep_owners.setdefault(key, set()).add(number)
    dup_substeps = sorted(
        f"{tgt} [{intent}]"
        for (tgt, intent), owners in substep_owners.items()
        if len(owners) > 1
    )

    # (c) in_task_build — a heavy build/verify command in a task's verification.
    in_task_builds: list[str] = []
    for t in tasks:
        number = int(t.get("number", 0) or 0)
        commands = (t.get("verification") or {}).get("commands", []) or []
        for cmd in commands:
            if isinstance(cmd, str) and is_heavy_build_cmd(cmd):
                m = re.search(r'command-args\s+"?([^"]+)', cmd)
                verb = m.group(1).strip() if m else "build"
                in_task_builds.append(f"T{number}:{verb}")

    # (d) verif_task_fanout — >1 module_testing/verification task.
    verif_tasks = sorted(
        int(t.get("number", 0) or 0)
        for t in tasks
        if t.get("profile") in ("module_testing", "verification")
    )

    # (e) deliverable fan-out raw counts — the per-run threshold is applied in
    # run_checks where the corpus median is known.
    deliv_counts: dict[int, int] = {}
    for t in tasks:
        d = int(t.get("deliverable", 0) or 0)
        if d > 0:
            deliv_counts[d] = deliv_counts.get(d, 0) + 1

    return {
        "plan_id": inputs.plan_id,
        "tasks": len(tasks),
        "multi_task_file": ";".join(multi_task_files),
        "dup_substep": ";".join(dup_substeps),
        "in_task_build": ";".join(in_task_builds),
        "verif_task_fanout": ";".join(str(n) for n in verif_tasks)
        if len(verif_tasks) > 1
        else "",
        # Stamped in run_checks once the per-run median threshold is known.
        "deliverable_fanout": "",
        "deliv_counts": deliv_counts,
        "max_tasks_per_deliverable": max(deliv_counts.values(), default=0),
    }


def _finalize_deliverable_fanout(rows: list[dict[str, Any]]) -> int:
    """Stamp `deliverable_fanout` on each row from the per-run corpus median.

    The outlier threshold is `max(3, median*2)` over the per-deliverable task
    counts across the loaded corpus (Decision 4), recomputed fresh each run. A
    row whose `max_tasks_per_deliverable` reaches the threshold gets a non-empty
    `deliverable_fanout` cell naming the offending count. Returns the threshold.
    """
    all_counts = [
        float(c) for r in rows for c in r["deliv_counts"].values()
    ]
    median_tpd = median(all_counts)
    threshold = max(3.0, median_tpd * 2.0)
    for r in rows:
        max_tpd = r["max_tasks_per_deliverable"]
        r["deliverable_fanout"] = (
            f"max={max_tpd}>=thr={threshold:.0f}" if max_tpd >= threshold else ""
        )
    return int(threshold)


def _task_graph_redundancy_genuine(row: dict[str, Any]) -> bool:
    """Genuine when any of the five redundancy signals is populated (Decision 5).

    All five sub-checks emit `genuine`; there is no informational-only sub-check.
    An empty row (clean plan: distinct targets, no heavy in-task build, balanced
    fan-out) is `informational`.
    """
    return bool(
        row["multi_task_file"]
        or row["dup_substep"]
        or row["in_task_build"]
        or row["verif_task_fanout"]
        or row["deliverable_fanout"]
    )


def emit_task_graph_redundancy_block(
    rows: list[dict[str, Any]], threshold: int
) -> str:
    """Emit the per-plan task-graph-redundancy block + corpus totals.

    Each per-plan row carries the five signal cells plus the uniform D1
    `severity` column (`genuine` when any signal populated). The block leads with
    the corpus totals (plans flagged per signal and the per-run deliverable-fanout
    `threshold`) so the systemic redundancy footprint is visible at a glance.
    """
    rows, genuine_signal_count = _severity_summary(
        rows, _task_graph_redundancy_genuine
    )
    out = [
        "check: task-graph-redundancy",
        "status: success",
        f"plans_scanned: {len(rows)}",
        f"multi_task_file_plans: {sum(1 for r in rows if r['multi_task_file'])}",
        f"dup_substep_plans: {sum(1 for r in rows if r['dup_substep'])}",
        f"in_task_build_plans: {sum(1 for r in rows if r['in_task_build'])}",
        f"verif_task_fanout_plans: {sum(1 for r in rows if r['verif_task_fanout'])}",
        f"deliverable_fanout_plans: {sum(1 for r in rows if r['deliverable_fanout'])}",
        f"deliverable_fanout_threshold: {threshold}",
        f"genuine_signal_count: {genuine_signal_count}",
        (
            f"rows[{len(rows)}]{{plan_id,tasks,multi_task_file,dup_substep,"
            "in_task_build,verif_task_fanout,deliverable_fanout,severity}:"
        ),
    ]
    for r in rows:
        out.append(
            "  "
            + ",".join(
                _cell(c)
                for c in [
                    r["plan_id"],
                    r["tasks"],
                    r["multi_task_file"],
                    r["dup_substep"],
                    r["in_task_build"],
                    r["verif_task_fanout"],
                    r["deliverable_fanout"],
                    r["severity"],
                ]
            )
        )
    return "\n".join(out) + "\n"


# ---------------------------------------------------------------------------
# Dormation move (the only mutating operation)
# ---------------------------------------------------------------------------

# Canonical plan-ID grammar: lowercase alphanumerics and hyphens only, starting
# and ending on an alphanumeric (the kebab/date shape used project-wide). This is
# a self-contained inline validator — the skill runs via direct `python3
# .../audit.py` with NO executor PYTHONPATH, so it cannot import
# `tools-input-validation`'s `validate_plan_id`. By construction the grammar
# rejects any `..`, absolute-path prefix (`/`), or embedded path separator
# (`/` or `\`), which are the path-traversal vectors this guard closes.
_PLAN_ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def _validate_plan_id(plan_id: str) -> str | None:
    """Return a refusal reason when `plan_id` violates the canonical grammar.

    Returns `None` when the value is a well-formed plan ID. A non-`None` return
    is the fail-fast front line of the belt-and-braces path-traversal defense:
    it fires before any move destination is
    constructed, complementing the resolved-path containment guards below.
    """
    if not plan_id or not _PLAN_ID_RE.match(plan_id):
        return (
            f"invalid plan_id {plan_id!r}: must match the canonical kebab/date "
            f"grammar (lowercase alphanumerics and hyphens, no '..', no path "
            f"separators, no absolute prefix)"
        )
    return None


def dormate_plans(
    repo_root: Path, plan_ids: list[str], confirmed: bool
) -> dict[str, Any]:
    """Relocate one or more archived plans to `.plan/temp/dormated-plans/{plan_id}`.

    Mirrors `dormate_global_logs` posture exactly: inert unless `confirmed` is True
    (the interactive confirmation is owned by the SKILL.md LLM body via
    AskUserQuestion; this function performs only the confirmed move). The supplied
    `plan_ids` are deduplicated silently (order-preserving) and each is validated
    against the canonical grammar via `_validate_plan_id` before any destination is
    constructed. Source and destination resolutions are bracketed by
    `is_relative_to` containment guards. An all-or-nothing refuse-on-clash pre-check
    (invalid grammar, missing source, or an already-existing destination) refuses
    the WHOLE operation (`status` `refused`/`error`) before relocating any plan, so
    a mid-batch clash never leaves a partially-moved batch on disk.
    """
    if not confirmed:
        return {
            "status": "refused",
            "reason": "dormation requires --confirmed; the move function is inert without it",
            "moved": [],
        }

    # Dedup silently, preserving first-seen order.
    deduped: list[str] = []
    seen: set[str] = set()
    for plan_id in plan_ids:
        if plan_id not in seen:
            seen.add(plan_id)
            deduped.append(plan_id)

    src_parent = (repo_root / ".plan/local/archived-plans").resolve()
    dest_parent = (repo_root / ".plan/temp/dormated-plans").resolve()

    # All-or-nothing pre-check: validate grammar, resolve + contain source and
    # destination, and refuse-on-exists across EVERY plan before moving anything.
    resolved: list[tuple[str, Path, Path]] = []
    for plan_id in deduped:
        grammar_error = _validate_plan_id(plan_id)
        if grammar_error is not None:
            return {
                "status": "refused",
                "plan_id": plan_id,
                "reason": grammar_error,
                "moved": [],
            }
        src = (src_parent / plan_id).resolve()
        if not src.is_relative_to(src_parent) or not src.is_dir():
            return {
                "status": "error",
                "plan_id": plan_id,
                "reason": f"source not found or invalid: {src}",
                "moved": [],
            }
        dest = (dest_parent / plan_id).resolve()
        if not dest.is_relative_to(dest_parent):
            return {
                "status": "error",
                "plan_id": plan_id,
                "reason": f"invalid destination: {dest}",
                "moved": [],
            }
        if dest.exists():
            return {
                "status": "error",
                "plan_id": plan_id,
                "reason": f"destination already exists: {dest}",
                "moved": [],
            }
        resolved.append((plan_id, src, dest))

    dest_parent.mkdir(parents=True, exist_ok=True)
    moved: list[str] = []
    for plan_id, src, dest in resolved:
        shutil.move(str(src), str(dest))
        moved.append(plan_id)
    return {
        "status": "success",
        "moved": sorted(moved),
        "moved_to": str(dest_parent) if moved else "",
    }


def dormate_all_plans(repo_root: Path, confirmed: bool) -> dict[str, Any]:
    """Dormate every archived plan under `.plan/local/archived-plans/`.

    Enumerates the per-plan subdirectories of `.plan/local/archived-plans/` and
    delegates to `dormate_plans` with the full set, inheriting its inert-unless-
    confirmed posture, per-plan grammar validation, containment guards, and
    all-or-nothing refuse-on-clash pre-check. An absent archive directory yields
    an empty (no-op) success.
    """
    if not confirmed:
        return {
            "status": "refused",
            "reason": "dormation requires --confirmed; the move function is inert without it",
            "moved": [],
        }
    src_parent = (repo_root / ".plan/local/archived-plans").resolve()
    if not src_parent.is_dir():
        return {
            "status": "success",
            "moved": [],
            "moved_to": "",
        }
    try:
        plan_ids = sorted(p.name for p in src_parent.iterdir() if p.is_dir())
    except OSError as e:
        return {
            "status": "error",
            "reason": f"failed to read archive directory: {e}",
            "moved": [],
        }
    return dormate_plans(repo_root, plan_ids, confirmed)


# Global log filename grammar: any `{prefix}-YYYY-MM-DD.log`, where the trailing
# `YYYY-MM-DD` is the dated rotation segment (e.g. `script-execution-2026-05-31.log`,
# `work-2026-05-31.log`, `decision-2026-05-31.log`). The capture group isolates the
# date so the move can compare it against today and skip the still-active log. The
# grammar itself excludes any path separator (`[a-z0-9-]+` prefix, `/` never matches),
# complementing the resolved-path containment guards below.
_GLOBAL_LOG_RE = re.compile(r"^[a-z0-9-]+-(?P<date>\d{4}-\d{2}-\d{2})\.log$")


def dormate_global_logs(repo_root: Path, confirmed: bool) -> dict[str, Any]:
    """Relocate COMPLETE past-date global logs to `dormated-plans/global-logs/`.

    Mirrors `dormate_plan` posture exactly: inert unless `confirmed` is True (the
    interactive confirmation is owned by the SKILL.md LLM body via AskUserQuestion;
    this function performs only the confirmed move). Scans `.plan/local/logs/` for
    `{prefix}-YYYY-MM-DD.log` files whose date is strictly before today and moves
    each into `.plan/temp/dormated-plans/global-logs/`. Today's still-active log is
    NEVER moved. On a destination-name clash the whole operation refuses
    (`status: error`) rather than overwriting. `is_relative_to` containment guards
    bracket both the source and destination resolutions.
    """
    if not confirmed:
        return {
            "status": "refused",
            "reason": "dormation requires --confirmed; the move function is inert without it",
            "moved": [],
        }
    logs_dir = (repo_root / ".plan/local/logs").resolve()
    if not logs_dir.is_dir():
        return {
            "status": "success",
            "moved": [],
            "moved_to": "",
        }
    today = datetime.now().date()
    # Collect the past-date complete logs first so a mid-move clash refuses before
    # relocating any file (refuse-on-exists is all-or-nothing per the dormate_plan
    # posture, not a partial best-effort).
    candidates: list[Path] = []
    for child in sorted(logs_dir.iterdir()):
        if not child.is_file():
            continue
        resolved = child.resolve()
        if not resolved.is_relative_to(logs_dir):
            continue
        m = _GLOBAL_LOG_RE.match(child.name)
        if m is None:
            continue
        try:
            log_date = datetime.strptime(m.group("date"), "%Y-%m-%d").date()
        except ValueError:
            continue
        if log_date >= today:
            # Today's (or any future-dated) log is still active — never move it.
            continue
        candidates.append(resolved)

    dest_parent = (repo_root / ".plan/temp/dormated-plans/global-logs").resolve()
    if not dest_parent.is_relative_to((repo_root / ".plan/temp/dormated-plans").resolve()):
        return {
            "status": "error",
            "reason": f"invalid destination parent: {dest_parent}",
            "moved": [],
        }
    # Refuse-on-exists pre-check across all candidates before moving anything.
    for src in candidates:
        dest = (dest_parent / src.name).resolve()
        if not dest.is_relative_to(dest_parent):
            return {
                "status": "error",
                "reason": f"invalid destination: {dest}",
                "moved": [],
            }
        if dest.exists():
            return {
                "status": "error",
                "reason": f"destination already exists: {dest}",
                "moved": [],
            }
    dest_parent.mkdir(parents=True, exist_ok=True)
    moved: list[str] = []
    for src in candidates:
        dest = (dest_parent / src.name).resolve()
        shutil.move(str(src), str(dest))
        moved.append(src.name)
    return {
        "status": "success",
        "moved": sorted(moved),
        "moved_to": str(dest_parent) if moved else "",
    }


# ---------------------------------------------------------------------------
# Persisted report sink (the only non-read-only side effect besides dormation)
# ---------------------------------------------------------------------------

# Report files live here and ONLY here. The write is path-guarded to this
# directory so a run can never escape it; longitudinal diffs read the most
# recent prior report from the same directory.
AUDIT_REPORTS_REL = ".plan/local/audit-reports"

# `{run-timestamp}.toon` filename grammar: UTC `YYYYMMDDTHHMMSSZ`. The reader
# orders by this stem so "latest prior" is deterministic.
_REPORT_STEM_RE = re.compile(r"^\d{8}T\d{6}Z$")


def _run_timestamp() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")


def write_persisted_report(
    repo_root: Path, blocks: list[str], summary_metrics: dict[str, Any]
) -> Path | None:
    """Persist this run's emitted blocks + summary metrics under audit-reports/.

    Writes `.plan/local/audit-reports/{run-timestamp}.toon` and returns its path,
    or `None` when the resolved destination would escape `audit-reports/` (the
    write is refused rather than performed outside the guarded directory). The
    report carries a `summary_metrics` header (read back by
    `load_latest_prior_report`) followed by the run's full block text.
    """
    reports_dir = (repo_root / AUDIT_REPORTS_REL).resolve()
    dest = (reports_dir / f"{_run_timestamp()}.toon").resolve()
    if not dest.is_relative_to(reports_dir):
        return None
    reports_dir.mkdir(parents=True, exist_ok=True)
    lines = ["report: audit", "summary_metrics:"]
    for key in sorted(summary_metrics):
        lines.append(f"  {key}: {_cell(summary_metrics[key])}")
    body = "\n".join(lines) + "\n\n" + "\n".join(blocks) + "\n"
    dest.write_text(body, encoding="utf-8")
    return dest


def _parse_report_summary_metrics(path: Path) -> dict[str, Any]:
    """Read the `summary_metrics:` header block from a persisted report."""
    metrics: dict[str, Any] = {}
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return metrics
    in_block = False
    for raw in text.splitlines():
        if raw.strip() == "summary_metrics:":
            in_block = True
            continue
        if in_block:
            if not raw.startswith("  ") or ":" not in raw:
                break
            key, _, value = raw.strip().partition(":")
            metrics[key.strip()] = _coerce_metric(value.strip().strip('"'))
    return metrics


def _coerce_metric(value: str) -> Any:
    if value in {"True", "False"}:
        return value == "True"
    try:
        return int(value)
    except ValueError:
        return value


def load_latest_prior_report(repo_root: Path) -> dict[str, Any] | None:
    """Return the most recent prior report's summary metrics, or None.

    "Prior" is the report with the lexicographically-greatest timestamp stem;
    when this run has not yet written its own file the latest is the previous
    run. Returns `None` when no valid report file exists.
    """
    reports_dir = (repo_root / AUDIT_REPORTS_REL).resolve()
    if not reports_dir.is_dir():
        return None
    candidates = sorted(
        (p for p in reports_dir.glob("*.toon") if _REPORT_STEM_RE.match(p.stem)),
        key=lambda p: p.stem,
    )
    if not candidates:
        return None
    return _parse_report_summary_metrics(candidates[-1])


def diff_summary_metrics(
    prior: dict[str, Any], current: dict[str, Any]
) -> list[tuple[str, Any, Any]]:
    """Return `(key, prior_value, current_value)` for every changed metric.

    A key absent from one side is reported with an empty string on that side. The
    result is sorted by key so the diff block is deterministic.
    """
    changes: list[tuple[str, Any, Any]] = []
    for key in sorted(set(prior) | set(current)):
        before = prior.get(key, "")
        after = current.get(key, "")
        if before != after:
            changes.append((key, before, after))
    return changes


def _report_diff_block(repo_root: Path, current: dict[str, Any]) -> str | None:
    """Build the `report-diff` summary block against the latest prior report."""
    prior = load_latest_prior_report(repo_root)
    if prior is None:
        return None
    changes = diff_summary_metrics(prior, current)
    out = [
        "check: report-diff",
        "status: success",
        f"changed_count: {len(changes)}",
        f"rows[{len(changes)}]{{metric,prior,current}}:",
    ]
    for key, before, after in changes:
        out.append("  " + ",".join(_cell(c) for c in [key, before, after]))
    return "\n".join(out) + "\n"


# ---------------------------------------------------------------------------
# Era model: fixed_since stamping + retire-on-quiet proposal
# ---------------------------------------------------------------------------
#
# Two script-computed era signals ride on top of the emitted blocks:
#  - `fixed_since` — `_stamp_era` inserts each check's `CHECK_ERA` boundary stamp
#    into its block header, so every emitted check block carries its era.
#  - retire-on-quiet — a check whose `genuine_signal_count` has been zero across
#    `THRESHOLDS["retire_on_quiet_runs"]` consecutive recorded runs surfaces a
#    removal PROPOSAL in the `retire-on-quiet` block. Proposal only — nothing is
#    removed. The per-run genuine substrate is persisted as `genuine__{check}`
#    summary-metric keys so the streak can be read back across runs.

# Uniform per-check genuine-count substrate: the key each run persists into the
# report's `summary_metrics` header so a later run can read the quiet streak.
_GENUINE_METRIC_PREFIX = "genuine__"

_CHECK_HEADER_RE = re.compile(r"^check:\s*(\S+)\s*$", re.MULTILINE)
_GENUINE_COUNT_RE = re.compile(r"^genuine_signal_count:\s*(\d+)\s*$", re.MULTILINE)


def _stamp_era(block: str) -> str:
    """Insert the block's `fixed_since` boundary stamp into its header.

    Reads the block's leading `check: {name}` line and, when the name is a known
    check with a `CHECK_ERA` entry, inserts a `fixed_since: {stamp}` line
    immediately after the `status:` line. Non-check meta blocks (`report-diff`,
    `retire-on-quiet`) carry no era entry and pass through unchanged.
    """
    header = _CHECK_HEADER_RE.search(block)
    if header is None:
        return block
    stamp = CHECK_ERA.get(header.group(1))
    if stamp is None:
        return block
    lines = block.split("\n")
    for i, line in enumerate(lines):
        if line.startswith("status:"):
            lines.insert(i + 1, f"fixed_since: {stamp}")
            break
    return "\n".join(lines)


def _extract_per_check_genuine(blocks: list[str]) -> dict[str, int]:
    """Map each emitted check block to its `genuine_signal_count`.

    Parses the block text (every `emit_*` block carries both a `check:` header
    and a `genuine_signal_count:` line) so the substrate is uniform across all
    checks without threading the count through each emitter. Meta blocks
    (`report-diff`) whose header is not a known check name are skipped.
    """
    out: dict[str, int] = {}
    for block in blocks:
        header = _CHECK_HEADER_RE.search(block)
        if header is None or header.group(1) not in CHECK_NAMES:
            continue
        count = _GENUINE_COUNT_RE.search(block)
        if count is not None:
            out[header.group(1)] = int(count.group(1))
    return out


def _prior_genuine_runs(repo_root: Path, limit: int) -> list[dict[str, int]]:
    """Return up to `limit` prior runs' per-check genuine counts, newest first.

    Reads the `genuine__{check}` keys from each recent persisted report's
    `summary_metrics` header. The current run's report has not been written yet
    when this is called (the sink runs at the end of `run_checks`), so every
    returned run is a genuine predecessor. A report predating the era model
    carries no `genuine__` keys and yields an empty run dict — which breaks any
    quiet streak (an unknown run is not a confirmed-quiet run).
    """
    reports_dir = (repo_root / AUDIT_REPORTS_REL).resolve()
    if limit <= 0 or not reports_dir.is_dir():
        return []
    try:
        toon_files = list(reports_dir.glob("*.toon"))
    except OSError:
        return []
    candidates = sorted(
        (p for p in toon_files if _REPORT_STEM_RE.match(p.stem)),
        key=lambda p: p.stem,
        reverse=True,
    )[:limit]
    runs: list[dict[str, int]] = []
    for path in candidates:
        metrics = _parse_report_summary_metrics(path)
        run = {
            key[len(_GENUINE_METRIC_PREFIX):]: value
            for key, value in metrics.items()
            if key.startswith(_GENUINE_METRIC_PREFIX) and isinstance(value, int)
        }
        runs.append(run)
    return runs


def _retire_on_quiet_proposals(
    repo_root: Path, current_genuine: dict[str, int]
) -> tuple[list[dict[str, Any]], int]:
    """Compute retire-on-quiet proposals and the recorded-run count.

    A check's quiet streak is the number of consecutive most-recent recorded runs
    — the current run first, then each prior report — whose genuine count is
    exactly zero. A non-zero count OR a run that never recorded the check breaks
    the streak. A check quiet for at least `THRESHOLDS["retire_on_quiet_runs"]`
    runs surfaces a removal proposal. Returns `(proposals, runs_recorded)` where
    `runs_recorded` is 1 (this run) plus the number of prior reports read.
    """
    threshold = int(THRESHOLDS["retire_on_quiet_runs"])
    prior_runs = _prior_genuine_runs(repo_root, threshold)
    runs = [current_genuine, *prior_runs]
    proposals: list[dict[str, Any]] = []
    for check in CHECK_NAMES:
        streak = 0
        for run in runs:
            if run.get(check) == 0:
                streak += 1
            else:
                break
        if streak >= threshold:
            proposals.append(
                {
                    "check": check,
                    "quiet_run_count": streak,
                    "fixed_since": CHECK_ERA.get(check, ""),
                    "proposal": (
                        f"retire (quiet for {streak} recorded runs "
                        f">= {threshold}) — proposal only, no removal"
                    ),
                }
            )
    return proposals, len(runs)


def emit_retire_on_quiet_block(
    proposals: list[dict[str, Any]], runs_recorded: int
) -> str:
    """Emit the `retire-on-quiet` proposal block.

    Meta block (no `fixed_since` stamp of its own) leading with the tunable
    threshold and the recorded-run count so the reader knows how much history
    backs the proposals — the mechanism only fires once at least
    `retire_on_quiet_runs` runs have been recorded. Each row names the check, its
    quiet-run streak, its `CHECK_ERA` stamp, and the proposal text. The block is
    always emitted on a full sweep (empty rows show the mechanism ran); it never
    removes a check.
    """
    threshold = int(THRESHOLDS["retire_on_quiet_runs"])
    out = [
        "check: retire-on-quiet",
        "status: success",
        f"quiet_run_threshold: {threshold}",
        f"runs_recorded: {runs_recorded}",
        f"proposal_count: {len(proposals)}",
        f"rows[{len(proposals)}]{{check,quiet_run_count,fixed_since,proposal}}:",
    ]
    for p in proposals:
        out.append(
            "  "
            + ",".join(
                _cell(c)
                for c in [
                    p["check"],
                    p["quiet_run_count"],
                    p["fixed_since"],
                    p["proposal"],
                ]
            )
        )
    return "\n".join(out) + "\n"


# ---------------------------------------------------------------------------
# TOON emission
# ---------------------------------------------------------------------------


def _cell(value: Any) -> str:
    """Render a single TOON table cell, quoting when it contains a comma."""
    if value is None:
        return ""
    s = str(value)
    return f'"{s}"' if "," in s or '"' in s else s


def _severity_summary(
    rows: list[dict[str, Any]], genuine_predicate: Callable[[dict[str, Any]], bool]
) -> tuple[list[dict[str, Any]], int]:
    """Stamp a uniform `severity` cell on every row and count genuine signals.

    Returns `(rows_with_severity, genuine_signal_count)`. Each row gains a
    `severity` key of `genuine` (the `genuine_predicate` fired — an actionable
    signal) or `informational` (a present-but-not-actionable row: missing
    artifacts, healthy verdicts). The count is the number of `genuine` rows.

    Generalizes the `severity` pattern previously unique to `emit_manifest_block`
    so every `emit_*_block` carries the same per-row column and `genuine_signal_count`
    summary line.
    """
    genuine_count = 0
    for row in rows:
        if genuine_predicate(row):
            row["severity"] = "genuine"
            genuine_count += 1
        else:
            row["severity"] = "informational"
    return rows, genuine_count


def _dedup_pretag(signature: str, corpus_sigs: list[str]) -> str:
    """Pre-tag a finding signature against the lessons-learned corpus.

    Returns `novel` when no filed lesson covers the signature, or
    `covered_by:{lesson_id}` when one does. This is a Gate-1 PRE-filter only —
    the authoritative dedup adjudication remains in the LLM body. Reuses the
    same substring containment match as `_signature_filed` so the script's
    pre-tag and the body's adjudication agree on what "covered" means.

    `corpus_sigs` carries the lesson signatures; when it is produced by
    `_lessons_corpus_titles` the lesson id is parsed from the corpus filename so
    the returned tag names the covering lesson.
    """
    sig = signature.strip().lower()
    if not sig:
        return "novel"
    for entry in corpus_sigs:
        lesson_id, _, title = entry.partition("\t")
        existing = (title or lesson_id).strip().lower()
        if not existing:
            continue
        if sig in existing or existing in sig:
            return f"covered_by:{lesson_id}" if lesson_id else "covered"
    return "novel"


def _manifest_genuine(row: dict[str, Any]) -> bool:
    """Genuine-signal predicate for an execution-context-manifest row.

    Genuine (actionable): a `drift` verdict, a populated `name_drift` (which,
    post role-resolution, is only ever an unresolvable role or a zero-intersection
    phase_5), or a populated `owner_drift` (a phase_6 built-in step the canonical
    finalize roster no longer recognizes — #852 D6 step-ownership). Informational:
    `incomplete` / `unloggable` verdicts (missing artifacts, not a composition
    fault) and `ok` rows.
    """
    return bool(
        row["verdict"] == "drift" or row["name_drift"] or row.get("owner_drift")
    )


def emit_manifest_block(rows: list[dict[str, Any]]) -> str:
    counts = {"ok": 0, "drift": 0, "incomplete": 0, "unloggable": 0}
    name_drift_count = 0
    owner_drift_count = 0
    for r in rows:
        counts[r["verdict"]] = counts.get(r["verdict"], 0) + 1
        if r["name_drift"]:
            name_drift_count += 1
        if r.get("owner_drift"):
            owner_drift_count += 1
    rows, genuine_signal_count = _severity_summary(rows, _manifest_genuine)
    out = ["check: execution-context-manifest", "status: success"]
    out.append(f"plans_scanned: {len(rows)}")
    out.append(f"ok_count: {counts['ok']}")
    out.append(f"drift_count: {counts['drift']}")
    out.append(f"incomplete_count: {counts['incomplete']}")
    out.append(f"unloggable_count: {counts['unloggable']}")
    out.append(f"name_drift_count: {name_drift_count}")
    out.append(f"owner_drift_count: {owner_drift_count}")
    out.append(f"genuine_signal_count: {genuine_signal_count}")
    out.append(
        f"rows[{len(rows)}]{{plan_id,verdict,severity,reason,expected_rule,actual_rule,change_type,scope,recipe,affected,modified,name_drift,owner_drift}}:"
    )
    for r in rows:
        out.append(
            "  "
            + ",".join(
                _cell(c)
                for c in [
                    r["plan_id"],
                    r["verdict"],
                    r["severity"],
                    r["reason"],
                    r["expected_rule"] or "",
                    r["actual_rule"] or "",
                    r["change_type"] or "",
                    r["scope"] or "",
                    r["recipe"] or "",
                    r["affected"],
                    r["modified"],
                    r["name_drift"] or "",
                    r.get("owner_drift") or "",
                ]
            )
        )
    return "\n".join(out) + "\n"


def emit_table_block(
    check: str,
    columns: list[str],
    rows: list[dict[str, Any]],
    genuine_predicate: Callable[[dict[str, Any]], bool],
) -> str:
    """Emit a tabular check block carrying the uniform `severity` column.

    `severity` is appended as the final column on every row and a
    `genuine_signal_count` summary line precedes the rows. `genuine_predicate`
    decides which rows are actionable signals vs informational.
    """
    rows, genuine_signal_count = _severity_summary(rows, genuine_predicate)
    severity_columns = [*columns, "severity"]
    out = [f"check: {check}", "status: success", f"plans_scanned: {len(rows)}"]
    out.append(f"genuine_signal_count: {genuine_signal_count}")
    out.append(f"rows[{len(rows)}]{{{','.join(severity_columns)}}}:")
    for r in rows:
        out.append("  " + ",".join(_cell(r.get(col, "")) for col in severity_columns))
    return "\n".join(out) + "\n"


def emit_recurring_block(result: dict[str, Any]) -> str:
    # Every systemic recurring pattern is by definition a genuine signal (it
    # cleared the N-occurrence threshold); the dedup pre-tag tells the body
    # whether it is already filed.
    rows, genuine_signal_count = _severity_summary(result["rows"], lambda _r: True)
    out = [
        "check: recurring-pattern-detector",
        "status: success",
        f"threshold: {result['threshold']}",
        f"systemic_count: {result['systemic_count']}",
        f"genuine_signal_count: {genuine_signal_count}",
        f"rows[{len(rows)}]{{signature,occurrence_count,plan_ids,candidate,severity}}:",
    ]
    for r in rows:
        out.append(
            "  "
            + ",".join(
                _cell(c)
                for c in [
                    r["signature"],
                    r["occurrence_count"],
                    ";".join(r["plan_ids"]),
                    r.get("candidate", "novel"),
                    r["severity"],
                ]
            )
        )
    return "\n".join(out) + "\n"


def emit_preference_pattern_block(result: dict[str, Any]) -> str:
    # Every surfaced preference cleared the occurrence threshold, so each row is a
    # genuine signal — a candidate preference the orchestrator routes per the
    # shared disposition-to-hint contract.
    rows, genuine_signal_count = _severity_summary(result["rows"], lambda _r: True)
    out = [
        "check: preference-pattern-detector",
        "status: success",
        f"threshold: {result['threshold']}",
        f"candidate_count: {result['candidate_count']}",
        f"genuine_signal_count: {genuine_signal_count}",
        f"rows[{len(rows)}]{{module,finding_class,disposition,occurrence_count,plan_ids,severity}}:",
    ]
    for r in rows:
        out.append(
            "  "
            + ",".join(
                _cell(c)
                for c in [
                    r["module"],
                    r["finding_class"],
                    r["disposition"],
                    r["occurrence_count"],
                    ";".join(r["plan_ids"]),
                    r["severity"],
                ]
            )
        )
    return "\n".join(out) + "\n"


def emit_trend_block(result: dict[str, Any]) -> str:
    # A trend row is a genuine signal only when a sustained regression fired for
    # the series; per-plan rows are the supporting series, not standalone signals.
    has_regression = bool(result["regression"])
    rows, genuine_signal_count = _severity_summary(
        result["rows"], lambda _r: has_regression
    )
    out = [
        "check: token-efficiency-trend",
        "status: success",
        f"plans_in_series: {result['plans_in_series']}",
        f"regression: {_cell(result['regression'])}",
        f"genuine_signal_count: {genuine_signal_count}",
        f"rows[{len(rows)}]{{plan_id,phases,total_tokens,tokens_per_phase,severity}}:",
    ]
    for r in rows:
        out.append(
            "  "
            + ",".join(
                _cell(c)
                for c in [
                    r["plan_id"],
                    r["phases"],
                    r["total_tokens"],
                    r["tokens_per_phase"],
                    r["severity"],
                ]
            )
        )
    return "\n".join(out) + "\n"


def emit_global_log_block(result: dict[str, Any]) -> str:
    """Emit the cross-plan global-log-analysis block.

    Every flagged line — error/non-INFO, slow call, impossible duration,
    high-frequency caller, or fixture leak — is a genuine signal, so it is
    stamped `severity: genuine` via the shared `_severity_summary` helper (D1
    infra). The block carries summary counts (level bucket totals, corpus size)
    followed by one `rows[N]{kind,detail,attributed_plans,severity}` table over
    the consolidated signals. Informational context (level_counts,
    total_log_lines) rides the summary lines, not the table, so the
    `genuine_signal_count` reflects only actionable rows.
    """
    signals: list[dict[str, Any]] = []

    for r in result["error_lines"]:
        signals.append(
            {
                "kind": f"error:{r['level']}",
                "detail": r["detail"],
                "attributed_plans": ";".join(r["plans"]) or "ad-hoc",
            }
        )
    for r in result["impossible_calls"]:
        signals.append(
            {
                "kind": "impossible-duration",
                "detail": f"{r['seconds']:.1f}s {r['key']}",
                "attributed_plans": ";".join(r["plans"]) or "ad-hoc",
            }
        )
    for r in result["slow_calls"]:
        signals.append(
            {
                "kind": "slow-call",
                "detail": f"{r['seconds']:.1f}s {r['key']}",
                "attributed_plans": ";".join(r["plans"]) or "ad-hoc",
            }
        )
    for r in result["high_frequency"]:
        signals.append(
            {
                "kind": "high-frequency-caller",
                "detail": f"{r['count']}x {r['total_seconds']:.1f}s {r['key']}",
                "attributed_plans": "",
            }
        )
    for r in result["fixture_leaks"]:
        signals.append(
            {
                "kind": "fixture-leak",
                "detail": f"{r['signature']} :: {r['detail']}",
                "attributed_plans": ";".join(r["plans"]) or "ad-hoc",
            }
        )

    # Every surfaced row is a genuine, actionable signal by construction.
    rows, genuine_signal_count = _severity_summary(signals, lambda _r: True)

    level_summary = ";".join(
        f"{lvl}={cnt}" for lvl, cnt in sorted(result["level_counts"].items())
    )
    out = [
        "check: global-log-analysis",
        "status: success",
        f"logs_present: {str(result['logs_present']).lower()}",
        f"plan_windows_derived: {result['plan_windows_derived']}",
        f"total_log_lines: {result['total_log_lines']}",
        f"total_script_seconds: {result['total_script_seconds']}",
        f"level_counts: {_cell(level_summary)}",
        f"error_count: {result['error_count']}",
        f"slow_call_count: {result['slow_call_count']}",
        f"impossible_count: {result['impossible_count']}",
        f"high_frequency_count: {result['high_frequency_count']}",
        f"fixture_leak_count: {result['fixture_leak_count']}",
        f"slow_ceiling_seconds: {result['slow_ceiling']}",
        f"high_frequency_ceiling: {result['high_frequency_ceiling']}",
        f"genuine_signal_count: {genuine_signal_count}",
        f"rows[{len(rows)}]{{kind,detail,attributed_plans,severity}}:",
    ]
    for r in rows:
        out.append(
            "  "
            + ",".join(
                _cell(c)
                for c in [
                    r["kind"],
                    r["detail"],
                    r["attributed_plans"],
                    r["severity"],
                ]
            )
        )
    return "\n".join(out) + "\n"


def emit_token_economics_block(result: dict[str, Any]) -> str:
    """Emit the cross-plan token-economics block with the D1 severity column.

    Per-plan rows carry shares, efficiency ratios, and the corpus-relative flag
    list. A row is `genuine` (actionable) when it carries at least one
    anti-pattern flag, `informational` otherwise — stamped via the shared
    `_severity_summary` helper (D1 infra). The block leads with the derived
    (floating) thresholds and the corpus per-phase distribution so the read-out
    is self-describing: every flag's cut-point is visible alongside the rows it
    flagged. The by-change_type and by-scope aggregate tables follow as
    informational context for the tokens/file inversion.
    """
    thr = result["thresholds"]

    plan_rows = result["rows"]
    for r in plan_rows:
        r["flags_str"] = ";".join(r["flags"])
    plan_rows, genuine_signal_count = _severity_summary(
        plan_rows, lambda r: bool(r["flags"])
    )

    out = [
        "check: token-economics",
        "status: success",
        # total_tokens = input+output ONLY (manage-metrics excludes cache_read /
        # cache_creation; the excluded share scales with per-turn context size — large
        # for a monolithic session, modest for an isolated envelope). Every figure below
        # is a GENERATION-VOLUME proxy, not a total-traffic measure — see
        # checks/token-economics.md "Measurement caveat".
        "measurement_caveat: total_tokens=input+output; excludes cache_read/cache_creation (context-size-dependent under-count) — generation-volume proxy, not total traffic",
        f"plans_in_corpus: {result['plans_in_corpus']}",
        # Derived (floating) thresholds — every one measured from THIS run's
        # corpus, never hard-coded. Echoed so the flagged rows are self-describing.
        f"floor_band_p10_tokens: {thr['floor_band']:.0f}",
        f"median_total_tokens: {thr['median_total']:.0f}",
        f"small_footprint_p25_files: {thr['small_footprint']:.1f}",
        f"median_planning_exec_ratio: {thr['median_planning_exec_ratio']:.2f}",
        f"outline_share_p75: {thr['outline_share_p75']:.3f}",
        f"refine_share_p75: {thr['refine_share_p75']:.3f}",
        f"finalize_share_p75: {thr['finalize_share_p75']:.3f}",
        f"long_session_p75_msgs: {thr['long_session_p75']:.0f}",
        # Corpus per-phase distribution (share of the whole corpus token spend).
        f"corpus_refine_share: {thr['corpus_refine_share']:.3f}",
        f"corpus_outline_share: {thr['corpus_outline_share']:.3f}",
        f"corpus_execute_share: {thr['corpus_execute_share']:.3f}",
        f"corpus_finalize_share: {thr['corpus_finalize_share']:.3f}",
        f"genuine_signal_count: {genuine_signal_count}",
        f"rows[{len(plan_rows)}]{{plan_id,change_type,scope,files,tasks,msgs,total_tokens,tokens_per_file,tokens_per_task,exec_blind,flags,severity}}:",
    ]
    for r in plan_rows:
        out.append(
            "  "
            + ",".join(
                _cell(c)
                for c in [
                    r["plan_id"],
                    r["change_type"],
                    r["scope"],
                    r["files"],
                    r["tasks"],
                    r["msgs"],
                    r["total_tokens"],
                    r["tokens_per_file"],
                    r["tokens_per_task"],
                    str(r["exec_blind"]).lower(),
                    r["flags_str"],
                    r["severity"],
                ]
            )
        )

    by_ct = result["by_change_type"]
    out.append(f"by_change_type[{len(by_ct)}]{{value,n,avg_tokens,avg_files,tokens_per_file}}:")
    for r in by_ct:
        out.append(
            "  "
            + ",".join(
                _cell(c)
                for c in [r["value"], r["n"], r["avg_tokens"], r["avg_files"], r["tokens_per_file"]]
            )
        )

    by_scope = result["by_scope"]
    out.append(f"by_scope[{len(by_scope)}]{{value,n,avg_tokens,avg_files,tokens_per_file}}:")
    for r in by_scope:
        out.append(
            "  "
            + ",".join(
                _cell(c)
                for c in [r["value"], r["n"], r["avg_tokens"], r["avg_files"], r["tokens_per_file"]]
            )
        )

    return "\n".join(out) + "\n"


def _qc_finding_genuine(row: dict[str, Any]) -> bool:
    """Genuine-signal predicate for one quality-chain per-finding row.

    Genuine (actionable): an `auto-review` finding (shift-left subject — caught
    only at the most expensive stage), OR a build/self/auto finding still
    `pending` at archive time (unresolved chain debt). Informational: a finding
    cleanly resolved by an earlier mechanism (`direct_fix` / `lesson`) or a
    human-review row, which is the expected disposition rather than a signal.
    """
    if row["mechanism"] == "auto-review":
        return True
    if row["resolution"] == "pending":
        return True
    return False


def emit_quality_chain_block(result: dict[str, Any]) -> str:
    """Emit the cross-plan quality-chain block with the D1 severity column.

    Three table tiers in one block:

    1. `corpus_matrix` — the mechanism×resolution totals over the whole corpus,
       one row per mechanism with a cell per resolution bucket. Informational
       context (the chain's overall shape), echoed above the per-plan and
       per-finding tables.
    2. `plans` — one row per plan carrying the per-mechanism totals and the chain
       anti-pattern flag list; a row is `genuine` when it carries ≥1 flag.
    3. `findings` — the per-finding rows the task mandates, each stamped with the
       D1 `severity` column (genuine when an auto-review/shift-left finding or a
       pending finding) and, for auto-review findings, its shift-left tier.

    The `shift_left_tiers` summary line carries the Tier 1-4 histogram over
    `auto_review_only` findings so the read-out shows, at a glance, how much of
    the right-shifted review effort a pre-submission structural surface scan could
    have reclaimed.
    """
    mechanisms = result["mechanisms"]
    resolutions = result["resolutions"]
    corpus = result["corpus_matrix"]

    # Per-plan rows carry the flag list; severity = genuine when ≥1 flag.
    plan_rows = result["rows"]
    for r in plan_rows:
        r["flags_str"] = ";".join(r["flags"])
    plan_rows, plan_genuine_count = _severity_summary(plan_rows, lambda r: bool(r["flags"]))

    # Per-finding rows carry the D1 severity column.
    finding_rows, finding_genuine_count = _severity_summary(
        result["findings"], _qc_finding_genuine
    )

    th = result["tier_histogram"]
    tier_summary = ";".join(f"tier{t}={th.get(t, 0)}" for t in (1, 2, 3, 4))

    out = [
        "check: quality-chain",
        "status: success",
        f"plans_in_corpus: {result['plans_in_corpus']}",
        f"plan_genuine_signal_count: {plan_genuine_count}",
        f"finding_genuine_signal_count: {finding_genuine_count}",
        f"shift_left_tiers: {_cell(tier_summary)}",
    ]

    # 1. Corpus mechanism×resolution matrix.
    out.append(f"corpus_matrix[{len(mechanisms)}]{{mechanism,{','.join(resolutions)},total}}:")
    for mech in mechanisms:
        cells = [corpus[mech][res] for res in resolutions]
        total = sum(cells)
        out.append("  " + ",".join(_cell(c) for c in [mech, *cells, total]))

    # 2. Per-plan mechanism totals + flags.
    out.append(
        f"plans[{len(plan_rows)}]{{plan_id,build,self_review,auto_review,human_review,other,total,flags,severity}}:"
    )
    for r in plan_rows:
        out.append(
            "  "
            + ",".join(
                _cell(c)
                for c in [
                    r["plan_id"],
                    r["build"],
                    r["self_review"],
                    r["auto_review"],
                    r["human_review"],
                    r["other"],
                    r["total"],
                    r["flags_str"],
                    r["severity"],
                ]
            )
        )

    # 3. Per-finding rows with the D1 severity column.
    out.append(
        f"findings[{len(finding_rows)}]{{plan_id,mechanism,resolution,source_file,shift_left_tier,title,severity}}:"
    )
    for r in finding_rows:
        out.append(
            "  "
            + ",".join(
                _cell(c)
                for c in [
                    r["plan_id"],
                    r["mechanism"],
                    r["resolution"],
                    r["source_file"],
                    r["shift_left_tier"] or "",
                    r["title"],
                    r["severity"],
                ]
            )
        )

    return "\n".join(out) + "\n"


def _sbm_genuine(row: dict[str, Any]) -> bool:
    """Genuine-signal predicate for one sequence-and-build-minimality row.

    Genuine (actionable): the row carries at least one redundancy / non-minimality
    flag (`build_churn`, `non_minimal_build`, `docs_only_build`, `ci_rerun`,
    `phase_reentry`, `arch_over_resolution`, `consecutive_dup`). Informational: a
    plan that built minimally with no redundancy primitive — the expected shape,
    not a signal.
    """
    return bool(row["flags"])


def emit_sequence_build_minimality_block(result: dict[str, Any]) -> str:
    """Emit the cross-plan sequence-and-build-minimality block with D1 severity.

    Per-plan rows carry the call/build/verb counts, the per-phase graph, and the
    redundancy/anti-pattern flag list. A row is `genuine` (actionable) when it
    carries ≥1 flag, `informational` otherwise — stamped via the shared
    `_severity_summary` helper (D1 infra). The block leads with the duration-band
    thresholds and the corpus build-class / build-verb totals so each flagged row
    is self-describing, then emits one `rows[N]{...}` table over the per-plan
    signals.

    THREE STRUCTURAL CAVEATS (documented verbatim in
    `checks/sequence-and-build-minimality.md`) govern how the rows are read:
    finalize-fold conflation when no `role=phase-6-finalize` marker exists; the
    `verify` work.log word-count being an UPPER BOUND while a heavy (> heavy-band)
    duration is the FLOOR; and `consecutive_dup` over-counting same-verb /
    different-args calls. The emitter surfaces the raw numbers — the caveats live
    in the sub-doc the orchestrator reads alongside this block.
    """
    rows = result["rows"]
    for r in rows:
        r["flags_str"] = ";".join(r["flags"])
    rows, genuine_signal_count = _severity_summary(rows, _sbm_genuine)

    corpus = result["corpus"]
    out = [
        "check: sequence-and-build-minimality",
        "status: success",
        f"plans_in_corpus: {result['plans_in_corpus']}",
        # Duration-band thresholds (from the centralized THRESHOLDS table) so each
        # build-class count is self-describing.
        f"build_minimal_seconds: {result['build_minimal_seconds']:.0f}",
        f"build_heavy_seconds: {result['build_heavy_seconds']:.0f}",
        f"build_clustering_minutes: {result['build_clustering_minutes']:.0f}",
        # Corpus build-class + redundancy totals.
        f"corpus_builds: {corpus['builds']}",
        f"corpus_build_minimal: {corpus['minimal']}",
        f"corpus_build_scoped: {corpus['scoped']}",
        f"corpus_build_heavy: {corpus['heavy']}",
        f"corpus_build_seconds: {corpus['build_seconds']}",
        f"corpus_build_churn: {corpus['build_churn']}",
        f"corpus_ci_runs: {corpus['ci_runs']}",
        f"corpus_consecutive_dup: {corpus['consecutive_dup']}",
        f"corpus_docs_only_build_plans: {corpus['docs_only_build_plans']}",
        f"genuine_signal_count: {genuine_signal_count}",
        f"rows[{len(rows)}]{{plan_id,change_type,calls,span_seconds,builds,build_minimal,build_scoped,build_heavy,max_build_seconds,build_churn,arch_calls,ci_runs,consecutive_dup,phase_reentry,verbs,phase_graph,flags,severity}}:",
    ]
    for r in rows:
        out.append(
            "  "
            + ",".join(
                _cell(c)
                for c in [
                    r["plan_id"],
                    r["change_type"],
                    r["calls"],
                    r["span_seconds"],
                    r["builds"],
                    r["build_minimal"],
                    r["build_scoped"],
                    r["build_heavy"],
                    r["max_build_seconds"],
                    r["build_churn"],
                    r["arch_calls"],
                    r["ci_runs"],
                    r["consecutive_dup"],
                    r["phase_reentry"],
                    r["verbs"],
                    r["phase_graph"],
                    r["flags_str"],
                    r["severity"],
                ]
            )
        )
    return "\n".join(out) + "\n"


# ---------------------------------------------------------------------------
# Cross-plan: architecture-lookup-ratio (information-lookup vs build-lookup)
# ---------------------------------------------------------------------------
#
# manage-architecture subcommands split by INTENT. INFORMATION-LOOKUP (orientation /
# navigation) queries answer "where is X / which module owns this path / what files /
# project shape" — the structured-query alternative to Glob/Grep/raw-bash exploration
# (token-management.adoc §4). BUILD-LOOKUP resolves the canonical build command + the
# verification step set (build-management.adoc). DISCOVERY (discover / enrich / crawl-*)
# is one-time architecture CONSTRUCTION, not a per-plan lookup, so it is counted
# separately and EXCLUDED from the ratio.
_ALR_INFO_SUBS = frozenset(
    {
        "find",
        "which-module",
        "files",
        "module",
        "modules",
        "info",
        "overview",
        "topology",
        "graph",
        "commands",
    }
)
_ALR_BUILD_SUBS = frozenset({"resolve", "derive-verification"})


def _architecture_lookup_ratio_plan(inputs: PlanInputs) -> dict[str, Any]:
    """Count one plan's manage-architecture calls split by intent.

    Reads the plan-scoped `logs/script-execution.log` and tallies every
    `manage-architecture:architecture {sub}` call into INFORMATION-LOOKUP
    (orientation / navigation), BUILD-LOOKUP (canonical-command resolution), or
    DISCOVERY (one-time construction). Returns the per-plan row dict consumed by
    `emit_architecture_lookup_ratio_block`. Best-effort: a plan with no log degrades
    to an all-zero row rather than raising.
    """
    sel = inputs.plan_dir / "logs" / "script-execution.log"
    info = build = 0
    # Discovery (one-time construction) is broken out per verb so the otherwise-
    # lumped count is legible. NOTE: discover/enrich/crawl are mostly SETUP-TIME /
    # ad-hoc calls (marshall-steward, manual) that run OUTSIDE plan execution, so a
    # plan's per-plan discovery breakdown is usually all-zero — the corpus-wide
    # setup volume lives in global-log-analysis (high-frequency-caller). See the
    # sub-doc.
    disc = {"discover": 0, "enrich": 0, "crawl": 0, "other": 0}
    if sel.is_file():
        try:
            text = sel.read_text(encoding="utf-8", errors="replace")
        except OSError:
            text = ""
        for line in text.splitlines():
            m = _SBM_CALL_RE.match(line)
            if not m or not _sbm_is_arch(m.group("notation")):
                continue
            sub = m.group("sub")
            if sub in _ALR_INFO_SUBS:
                info += 1
            elif sub in _ALR_BUILD_SUBS:
                build += 1
            elif sub.startswith("discover"):
                disc["discover"] += 1
            elif sub.startswith("enrich"):
                disc["enrich"] += 1
            elif "crawl" in sub:
                disc["crawl"] += 1
            else:
                disc["other"] += 1
    discovery = disc["discover"] + disc["enrich"] + disc["crawl"] + disc["other"]
    # ratio = information lookups per build lookup; None when no build lookup ran
    # (a plan with zero build lookups has no defined ratio and cannot be flagged).
    ratio = (info / build) if build else None
    return {
        "plan_id": inputs.plan_id,
        "change_type": inputs.change_type or "",
        "info_lookups": info,
        "build_lookups": build,
        "discovery_calls": discovery,
        "discovery": disc,
        "total_arch": info + build + discovery,
        "ratio": ratio,
    }


def _alr_genuine(row: dict[str, Any]) -> bool:
    """A row is genuine when it carries the build_dominated_lookup flag."""
    return bool(row.get("flags"))


def cross_architecture_lookup_ratio(all_inputs: list[PlanInputs]) -> dict[str, Any]:
    """Per-plan information-lookup vs build-lookup ratio + corpus aggregates.

    For each plan counts manage-architecture INFORMATION-LOOKUP vs BUILD-LOOKUP calls
    (see `_architecture_lookup_ratio_plan`), then flags `build_dominated_lookup` on
    plans that ran a non-trivial number of build lookups yet sit in the bottom
    quartile of the corpus info/build ratio — a candidate for "navigation bypassed the
    structured-query lever". Corpus-relative: the build-volume floor (`median`) and the
    ratio cut (`p25`) are derived from the LIVE corpus, never hard-coded; a
    degenerate-corpus guard suppresses the flag when the ratio has no real low tail.

    A low ratio is NOT inherently a defect — a recipe / surgical / issue-fix plan
    legitimately pre-knows its targets and needs no navigation. The flag is a prompt
    (see `checks/architecture-lookup-ratio.md`), not a verdict. Best-effort: an empty
    corpus yields all-zero aggregates and no rows.
    """
    rows = [_architecture_lookup_ratio_plan(i) for i in all_inputs]

    total_info = sum(r["info_lookups"] for r in rows)
    total_build = sum(r["build_lookups"] for r in rows)
    total_discovery = sum(r["discovery_calls"] for r in rows)
    corpus_discovery = {
        k: sum(r["discovery"][k] for r in rows)
        for k in ("discover", "enrich", "crawl", "other")
    }

    # Corpus thresholds over the plans that actually ran a build lookup — a plan with
    # zero build lookups has no ratio and cannot be build-dominated.
    build_rows = [r for r in rows if r["build_lookups"] > 0]
    ratios = [r["ratio"] for r in build_rows]
    builds = [float(r["build_lookups"]) for r in build_rows]
    median_build = median(builds)
    ratio_p25 = percentile(ratios, 25.0) if ratios else 0.0
    median_ratio = median(ratios) if ratios else 0.0
    # Degenerate-corpus guard: only flag when the ratio distribution has a real low
    # tail (p25 strictly below the median). A uniform corpus flags nobody.
    has_spread = ratio_p25 < median_ratio

    for r in rows:
        flags: list[str] = []
        if (
            has_spread
            and r["build_lookups"] >= median_build
            and r["ratio"] is not None
            and r["ratio"] <= ratio_p25
        ):
            flags.append(
                f"build_dominated_lookup(info/build={r['ratio']:.2f}<=p25={ratio_p25:.2f};"
                f"build={r['build_lookups']}>=median={median_build:.0f})"
            )
        r["flags"] = flags

    corpus_ratio = (total_info / total_build) if total_build else None
    return {
        "plans_in_corpus": len(rows),
        "corpus_info_lookups": total_info,
        "corpus_build_lookups": total_build,
        "corpus_discovery_calls": total_discovery,
        "corpus_discovery": corpus_discovery,
        "corpus_info_build_ratio": corpus_ratio,
        "median_build_lookups": median_build,
        "ratio_p25": ratio_p25,
        "median_ratio": median_ratio,
        "rows": rows,
    }


def emit_architecture_lookup_ratio_block(result: dict[str, Any]) -> str:
    """Emit the cross-plan architecture-lookup-ratio block with the D1 severity column.

    Per-plan rows carry the information-lookup vs build-lookup counts and the
    info/build ratio; a row is `genuine` when it carries `build_dominated_lookup`,
    `informational` otherwise — stamped via the shared `_severity_summary` helper. The
    block leads with corpus totals and the corpus-derived thresholds so each flagged
    row is self-describing. A LOW ratio is NOT inherently a defect — see
    `checks/architecture-lookup-ratio.md`: a recipe / surgical / issue-fix plan
    legitimately pre-knows its targets and needs no navigation. The flag is a prompt to
    check whether navigation bypassed the structured-query lever (Read / raw-bash
    instead of `architecture find`/`which-module`), not a verdict.
    """
    rows = result["rows"]
    for r in rows:
        r["flags_str"] = ";".join(r["flags"])
        r["ratio_str"] = f"{r['ratio']:.2f}" if r["ratio"] is not None else "n/a"
        d = r["discovery"]
        r["discovery_breakdown"] = (
            f"discover={d['discover']};enrich={d['enrich']};"
            f"crawl={d['crawl']};other={d['other']}"
        )
    rows, genuine_signal_count = _severity_summary(rows, _alr_genuine)

    cr = result["corpus_info_build_ratio"]
    cd = result["corpus_discovery"]
    out = [
        "check: architecture-lookup-ratio",
        "status: success",
        # INFORMATION-LOOKUP = orientation/navigation verbs (find/which-module/files/
        # module/info/overview/...); BUILD-LOOKUP = resolve/derive-verification.
        # DISCOVERY (discover/enrich/crawl) is one-time setup — reported (now broken out
        # per verb), excluded from the ratio. Per-plan discovery is usually all-zero:
        # these are setup-time/ad-hoc calls outside plan execution, so the corpus-wide
        # discovery volume lives in global-log-analysis, not here. A low ratio may mean
        # "no navigation needed" — see the sub-doc.
        f"plans_in_corpus: {result['plans_in_corpus']}",
        f"corpus_info_lookups: {result['corpus_info_lookups']}",
        f"corpus_build_lookups: {result['corpus_build_lookups']}",
        f"corpus_discovery_calls: {result['corpus_discovery_calls']}",
        f"corpus_discovery: discover={cd['discover']};enrich={cd['enrich']};"
        f"crawl={cd['crawl']};other={cd['other']}",
        (
            f"corpus_info_build_ratio: {cr:.3f}"
            if cr is not None
            else "corpus_info_build_ratio: n/a"
        ),
        f"median_build_lookups: {result['median_build_lookups']:.0f}",
        f"ratio_p25: {result['ratio_p25']:.3f}",
        f"median_ratio: {result['median_ratio']:.3f}",
        f"genuine_signal_count: {genuine_signal_count}",
        f"rows[{len(rows)}]{{plan_id,change_type,info_lookups,build_lookups,"
        f"discovery_calls,discovery_breakdown,total_arch,ratio,flags,severity}}:",
    ]
    for r in rows:
        out.append(
            "  "
            + ",".join(
                _cell(c)
                for c in [
                    r["plan_id"],
                    r["change_type"],
                    r["info_lookups"],
                    r["build_lookups"],
                    r["discovery_calls"],
                    r["discovery_breakdown"],
                    r["total_arch"],
                    r["ratio_str"],
                    r["flags_str"],
                    r["severity"],
                ]
            )
        )
    return "\n".join(out) + "\n"


# ---------------------------------------------------------------------------
# Cross-plan: cross-check-synthesis (facet-completeness critic, runs LAST)
# ---------------------------------------------------------------------------
#
# The facet-completeness critic that operationalizes the SKILL.md Step-4b
# completeness gate. Every other check reports signals over ONE facet of the
# corpus; a real systemic problem usually shows up as a CHATTER of related
# single-check signals across facets — a token-trend regression that looks empty,
# a heavy build, a finalize-heavy token share, a CI re-run, an argparse-rejection
# spike. This check joins the OTHER checks' RETAINED structured results (the
# `rows`/`result` dicts they computed, NOT their emitted TOON strings) and reports
# the cross-check COUPLINGS those single rows individually miss.
#
# Because it reads the other checks' results, it MUST run last (it is the final
# entry in CHECK_NAMES). When invoked alone via `--check cross-check-synthesis`,
# run_checks computes the upstream results it depends on without emitting their
# blocks, so the synthesis can still fire.
#
# Each coupling carries a QUALIFYING CAVEAT — the condition under which the
# coupling is a genuine signal versus a coincidence — so the orchestrator reads a
# fired coupling with the same skepticism the underlying checks' caveats demand
# (e.g. an empty token-trend regression is only untrustworthy when input-integrity
# reports blind execute phases; it is not itself a finding).
#
# THE SIX COUPLINGS:
#   (a) trend_empty_untrustworthy   — token-efficiency-trend regression is EMPTY
#       while input-integrity reports >=1 blind execute. Caveat: an empty
#       regression over blind-execute plans is "floor, not truth" — the trend
#       saw no rise because the execute tokens were never recorded, not because
#       spend is flat.
#   (b) churn_explains_walltime     — a plan flagged sequence non_minimal_build /
#       build_churn whose build wall-clock (total_build_seconds) sits in the corpus
#       upper half (>= median). Caveat: build redundancy explains WALL-CLOCK waste,
#       NOT token cost — a build's token cost is ~fixed (it runs as a subprocess and
#       returns a bounded result TOON), so the token over-spend belongs to message /
#       reasoning volume (long_session), not builds. The earlier token-cost framing
#       was a mis-attribution.
#   (c) qgate_gap_chain             — a plan flagged quality-chain no_qgate6 /
#       auto_review_only that ALSO carries sequence ci_rerun OR token-economics
#       finalize_heavy. Caveat: a missing self-review surface co-occurring with a
#       CI re-run / heavy finalize is the shift-right tax — the PR round-trip paid
#       for what an earlier gate could have caught.
#   (d) argparse_signature_cluster  — recurring-pattern argparse-shaped signatures
#       correlate with global-log ERROR / argparse_rejection counts AND
#       quality-verification unfiled signatures. COLLAPSED to ONE candidate (the
#       three facets are three views of the same source-keyed drift, per the
#       SKILL.md source-keyed argparse-rejection rule). Caveat: file ONE
#       source-keyed lesson, not one per facet.
#   (e) scope_underestimate_cost    — a plan flagged scope-estimate-accuracy
#       under-estimation that ALSO sits in the high tokens-per-file / high
#       task-count tail. Caveat: an under-estimated scope predicts the over-spend;
#       the coupling names the predicted-vs-actual gap, not a fresh finding.
#   (f) redundant_build_churn       — a plan whose task graph bakes a HEAVY build
#       into a task's verification (task-graph-redundancy in_task_build) AND whose
#       runtime sequence was flagged build_churn / phase_reentry. Caveat: the
#       static in_task_build redundancy and the observed runtime churn corroborate
#       one wasted heavy run — confirm they co-occur before filing.

# argparse-rejection signatures the recurring-pattern detector surfaces — the
# wording the global-log FAIL markers and the per-plan script-failure analysis
# share for an invented-subcommand / missing-flag / invented-flag drift.
_SYN_ARGPARSE_SIG_RE = re.compile(
    r"argparse|invalid choice|unrecognized argument|required.*argument|exit[_ ]?code",
    re.IGNORECASE,
)


def _syn_flagged_plans(result: Any, flag_predicate: Callable[[str], bool]) -> set[str]:
    """Return the plan ids whose `flags` list has any flag matching the predicate.

    `result` is a cross-plan check result dict carrying a `rows` list of
    `{plan_id, flags:[...]}` row dicts (token-economics, quality-chain,
    sequence-and-build-minimality all share this shape). Best-effort: a missing /
    malformed result yields an empty set.
    """
    out: set[str] = set()
    if not isinstance(result, dict):
        return out
    for row in result.get("rows", []) or []:
        pid = row.get("plan_id")
        flags = row.get("flags") or []
        if pid and any(flag_predicate(str(f)) for f in flags):
            out.add(str(pid))
    return out


def _syn_in_task_build_plans(tgr_rows: Any) -> set[str]:
    """Return plan ids whose task-graph-redundancy row carries an in_task_build."""
    out: set[str] = set()
    if not isinstance(tgr_rows, list):
        return out
    for row in tgr_rows:
        if isinstance(row, dict) and row.get("in_task_build"):
            out.add(str(row.get("plan_id")))
    return out


def _syn_build_walltime_outlier_plans(sequence: Any) -> set[str]:
    """Return plan ids whose build wall-clock sits in the corpus upper half.

    Reads each sequence row's `total_build_seconds` and returns the plans at or
    above the median of the plans that ran at least one build. Zero-build plans are
    excluded — they cannot waste build wall-time — and the median is taken over the
    non-zero population so a corpus dominated by build-free plans does not collapse
    the threshold to zero. This is the WALL-CLOCK correlate the `churn_explains_walltime`
    coupling joins against: build redundancy wastes wall-clock, not tokens (a build's
    token cost is ~fixed regardless of duration). Best-effort: a missing / malformed
    result yields an empty set.
    """
    if not isinstance(sequence, dict):
        return set()
    pairs: list[tuple[str, int]] = []
    for row in sequence.get("rows", []) or []:
        pid = row.get("plan_id")
        secs = row.get("total_build_seconds")
        if pid and isinstance(secs, (int, float)) and secs > 0:
            pairs.append((str(pid), int(secs)))
    if not pairs:
        return set()
    threshold = median([float(s) for _, s in pairs])
    return {pid for pid, s in pairs if s >= threshold}


# ---------------------------------------------------------------------------
# Check: dispatch-topology (per-plan) — D3
# ---------------------------------------------------------------------------
#
# Directly verifies the roadmap's leaf/dispatch-topology invariant: subagents are
# LEAVES — only the main-context orchestrator dispatches further subagents (a leaf
# returns a signal, it never issues a `Task:`/`execution-context` dispatch). The
# invariant is the canonical contract in
# `ref-workflow-architecture/standards/agents.md`.
#
# Deterministic signal: each `[DISPATCH] (caller) target=... role=...` line in a
# plan's `logs/work.log` names the DISPATCHER via its `(bundle:skill)` caller
# prefix. Only the orchestrator (`plan-marshall:plan-marshall`) and the phase
# workflows the orchestrator uses as caller-phase context
# (`plan-marshall:phase-N-...`) may legitimately emit a `target=` dispatch. A
# `target=` dispatch whose caller is ANY other skill is a topology violation — a
# leaf (execute-task, automatic-review, sonar-roundtrip, a verify/finalize leaf,
# a retrospective aspect, …) spawned a subagent. The allowlist is used rather than
# a leaf denylist so a newly-added leaf is caught by default.

# A `[DISPATCH]` line carrying a `target=` field, capturing the `(bundle:skill)`
# caller prefix. The `target=` presence distinguishes a real subagent dispatch
# from a bare `[DISPATCH] role=phase-N` phase-entry marker (which carries no
# target and is not itself a spawn record).
_DISPATCH_TARGET_RE = re.compile(
    r"\[DISPATCH\]\s*\((?P<caller>[a-z0-9-]+:[a-z0-9_-]+)\)[^\n]*\btarget="
)
# Allowed dispatchers: the orchestrator and the phase workflows it drives. Any
# other caller emitting a `target=` dispatch is a leaf-topology violation.
_DISPATCH_ALLOWED_CALLER_RE = re.compile(
    r"^plan-marshall:(plan-marshall|phase-[1-6]-)"
)


def check_dispatch_topology(inputs: PlanInputs) -> dict[str, Any]:
    """Per-plan leaf/dispatch-topology conformance from `logs/work.log`.

    Scans every `[DISPATCH] ... target=...` line and classifies its `(bundle:skill)`
    caller against the allowed-dispatcher allowlist. Returns the total dispatch
    count, the leaf-violation count, and a `;`-joined list of the offending caller
    skills (the violation detail). A plan with no work.log, or with only bare
    phase-entry `[DISPATCH] role=...` markers (no `target=`), reports zero of both.
    """
    work_log = inputs.plan_dir / "logs" / "work.log"
    dispatch_count = 0
    violators: list[str] = []
    if work_log.is_file():
        try:
            text = work_log.read_text(encoding="utf-8", errors="replace")
        except OSError:
            text = ""
        for m in _DISPATCH_TARGET_RE.finditer(text):
            dispatch_count += 1
            caller = m.group("caller")
            if not _DISPATCH_ALLOWED_CALLER_RE.match(caller):
                violators.append(caller)
    leaf_dispatch = len(violators)
    return {
        "plan_id": inputs.plan_id,
        "dispatch_count": dispatch_count,
        "leaf_dispatch": leaf_dispatch,
        "violators": ";".join(sorted(set(violators))),
    }


def _dispatch_topology_genuine(row: dict[str, Any]) -> bool:
    """Genuine (actionable): any leaf-dispatch topology violation."""
    return int(row.get("leaf_dispatch") or 0) > 0


# ---------------------------------------------------------------------------
# Check: finalize-flow-conformance (per-plan) — D4
# ---------------------------------------------------------------------------
#
# Directly verifies the post-#849/#850 finalize mechanics: the deterministic
# `ci_verify` gate, the adaptive ci-wait ratchet, and the widened merge mutex.
# The finalize roster (`execution.toon` `phase_6.steps`) plus the persisted CI
# artifacts (`artifacts/ci-runs/{run_id}/manifest.toon`, carrying `wait_outcome`
# and `final_status` per #849's ci_verify) are the deterministic inputs.
#
# Conformance flags:
#   missing_ci_verify — the roster created a PR (`create-pr` step) but carries no
#                       `ci-verify` step: the #849 deterministic CI gate is absent
#                       (a pre-#849 finalize shape).
#   ci_wait_timeout   — a persisted ci-run recorded `wait_outcome: deadline_exceeded`
#                       — the adaptive ci-wait ratchet hit its budget ceiling.
#   ci_unresolved     — the LATEST persisted ci-run's `final_status` is not
#                       `success` (failure / timeout / none): finalize did not reach
#                       a green CI on the recorded runs.


def _bare_step(step_id: str) -> str:
    """Strip the optional `default:` prefix from a phase-6 step ID (bare name)."""
    s = step_id.strip()
    return s[len("default:"):] if s.startswith("default:") else s


def check_finalize_flow_conformance(inputs: PlanInputs) -> dict[str, Any]:
    """Per-plan post-#849/#850 finalize-flow conformance."""
    bare6 = {_bare_step(s) for s in inputs.manifest_phase_6} if inputs.manifest_phase_6 else set()
    has_pr_step = "create-pr" in bare6
    has_ci_verify_step = "ci-verify" in bare6

    ci_dir = inputs.plan_dir / "artifacts" / "ci-runs"
    try:
        run_dirs = sorted(d for d in ci_dir.iterdir() if d.is_dir())
    except OSError:
        run_dirs = []
    ci_run_count = len(run_dirs)
    latest_final_status = ""
    wait_timeout = False
    for d in run_dirs:
        manifest = d / "manifest.toon"
        wo = parse_toon_scalar(manifest, "wait_outcome")
        if (wo or "").strip() == "deadline_exceeded":
            wait_timeout = True
        fs = parse_toon_scalar(manifest, "final_status")
        if fs is not None:
            latest_final_status = fs.strip()

    flags: list[str] = []
    if has_pr_step and not has_ci_verify_step:
        flags.append("missing_ci_verify")
    if wait_timeout:
        flags.append("ci_wait_timeout")
    if ci_run_count > 0 and latest_final_status not in {"success", ""}:
        flags.append(f"ci_unresolved({latest_final_status})")

    return {
        "plan_id": inputs.plan_id,
        "has_pr_step": str(has_pr_step).lower(),
        "has_ci_verify_step": str(has_ci_verify_step).lower(),
        "ci_run_count": ci_run_count,
        "final_status": latest_final_status,
        "flags": ";".join(flags),
    }


def _finalize_flow_genuine(row: dict[str, Any]) -> bool:
    """Genuine (actionable): any finalize-flow conformance flag fired."""
    return bool(row.get("flags"))


# ---------------------------------------------------------------------------
# Check: merge-window-accounting (cross-plan) — D5
# ---------------------------------------------------------------------------
#
# Accounts for the #849 widened merge-mutex + FIFO admission-queue window (fair
# merge ordering / the parallelism enabler). The deterministic signal is the
# best-effort `[LOCK] (merge:{event}) {lock_id}` lifecycle lines the merge-lock
# primitive appends to the main-anchored global logs (`.plan/local/logs/`), each
# carrying a following indented `waiting_count:` field (the FIFO queue depth). The
# `{lock_id}` is the plan_id, so the corpus lines bucket per plan. Events:
# `acquired` / `released` / `blocked` (a non-front plan waiting behind the FIFO
# front) / `reclaimed`.
#
# Per-plan accounting: the acquire/release/blocked/reclaim counts and the max
# observed `waiting_count`. `merge_contention` fires when the plan was ever
# `blocked` (it waited in the admission queue) OR the max waiting_count exceeds 1
# (other plans were queued behind it) — the merge window this plan actually paid.

_LOCK_MERGE_RE = re.compile(
    r"\[LOCK\]\s*\(merge:(?P<event>[a-z_-]+)\)\s+(?P<lock_id>[A-Za-z0-9._-]+)"
)
_LOCK_WAITING_RE = re.compile(r"^\s*waiting_count:\s*(?P<n>\d+)")


def cross_merge_window_accounting(
    all_inputs: list[PlanInputs], repo_root: Path
) -> dict[str, Any]:
    """Cross-plan merge-mutex admission-queue accounting from the global logs.

    Scans the `[LOCK] (merge:*)` lifecycle lines across `.plan/local/logs/` and
    buckets them by `lock_id` (= plan_id). Emits one row per plan in the scanned
    corpus that recorded any merge-lock event, plus corpus totals. Best-effort: an
    absent logs dir yields no rows.
    """
    corpus_plan_ids = {i.plan_id for i in all_inputs}
    # per plan_id → {event_counts, max_waiting}
    acc: dict[str, dict[str, Any]] = {}
    logs_dir = (repo_root / ".plan" / "local" / "logs").resolve()
    try:
        log_files = sorted(logs_dir.glob("*.log"))
    except OSError:
        log_files = []
    for log_file in log_files:
        try:
            lines = log_file.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        for idx, raw in enumerate(lines):
            m = _LOCK_MERGE_RE.search(raw)
            if not m:
                continue
            lock_id = m.group("lock_id")
            event = m.group("event")
            entry = acc.setdefault(
                lock_id,
                {"acquired": 0, "released": 0, "blocked": 0, "reclaimed": 0, "max_waiting": 0},
            )
            entry[event] = entry.get(event, 0) + 1
            # waiting_count rides on the immediately-following indented lines.
            for look in lines[idx + 1 : idx + 6]:
                wm = _LOCK_WAITING_RE.match(look)
                if wm:
                    entry["max_waiting"] = max(entry["max_waiting"], int(wm.group("n")))
                    break
                if look and not look[:1].isspace():
                    break

    rows: list[dict[str, Any]] = []
    for lock_id in sorted(acc):
        # Attribute only to plans in the scanned corpus (a lock_id for a plan not
        # in this scan is carried in the corpus totals but not emitted as a row).
        e = acc[lock_id]
        blocked = int(e.get("blocked", 0))
        max_waiting = int(e.get("max_waiting", 0))
        contention = blocked > 0 or max_waiting > 1
        rows.append(
            {
                "plan_id": lock_id,
                "in_corpus": str(lock_id in corpus_plan_ids).lower(),
                "acquired": int(e.get("acquired", 0)),
                "released": int(e.get("released", 0)),
                "blocked": blocked,
                "reclaimed": int(e.get("reclaimed", 0)),
                "max_waiting": max_waiting,
                "flags": "merge_contention" if contention else "",
            }
        )

    corpus = {
        "plans_with_merge_events": len(rows),
        "contended_plans": sum(1 for r in rows if r["flags"]),
        "total_blocked": sum(int(r["blocked"]) for r in rows),
        "max_waiting_observed": max((int(r["max_waiting"]) for r in rows), default=0),
    }
    return {"rows": rows, "corpus": corpus}


def _merge_window_genuine(row: dict[str, Any]) -> bool:
    """Genuine (actionable): the plan hit merge contention (waited in the queue)."""
    return bool(row.get("flags"))


def emit_merge_window_accounting_block(result: dict[str, Any]) -> str:
    """Emit the merge-window-accounting block with the D1 severity column."""
    rows = result["rows"]
    corpus = result["corpus"]
    rows, genuine_signal_count = _severity_summary(rows, _merge_window_genuine)
    out = [
        "check: merge-window-accounting",
        "status: success",
        f"plans_with_merge_events: {corpus['plans_with_merge_events']}",
        f"contended_plans: {corpus['contended_plans']}",
        f"total_blocked: {corpus['total_blocked']}",
        f"max_waiting_observed: {corpus['max_waiting_observed']}",
        f"genuine_signal_count: {genuine_signal_count}",
        f"rows[{len(rows)}]{{plan_id,in_corpus,acquired,released,blocked,reclaimed,max_waiting,flags,severity}}:",
    ]
    for r in rows:
        out.append(
            "  "
            + ",".join(
                _cell(c)
                for c in [
                    r["plan_id"],
                    r["in_corpus"],
                    r["acquired"],
                    r["released"],
                    r["blocked"],
                    r["reclaimed"],
                    r["max_waiting"],
                    r["flags"],
                    r["severity"],
                ]
            )
        )
    return "\n".join(out) + "\n"


# ---------------------------------------------------------------------------
# Check: lane-lever-effectiveness (cross-plan) — D6
# ---------------------------------------------------------------------------
#
# The CHECKPOINT MEASUREMENT ARM of the token-optimization roadmap
# (`.plan/plan-optimization/HANDOVER.md`). Measures whether the cost-reducing
# lane levers the roadmap shipped — recipe auto-routing (#811 lane-selection),
# the light planning lane, the minimal execution posture, and the #854
# surgical-fix micro-lane — are actually being ENGAGED, and whether per-scope-class
# spend stays inside the armed checkpoint targets.
#
# Deterministic inputs (all per-plan, no global logs):
#   scope_estimate         → checkpoint class + armed target (THRESHOLDS)
#   metrics.toon           → summed total_tokens (the measured spend)
#   recipe_key/plan_source → recipe auto-route HIT (a plan seeded from a recipe/lesson)
#   planning_lane          → light-lane fire (lane == "light")
#   execution_profile      → chosen posture; minimal is the cost-reducing lever
#
# Per-plan verdict: the plan's summed total_tokens vs its scope class's armed
# checkpoint target — `within` / `over` / `unclassed` (scope outside the armed
# set) / `no_metrics` (no recorded tokens). `checkpoint_over` is the genuine
# (actionable) overspend signal. `posture_not_taken` (a surgical-scope plan the
# micro-lane recommends `minimal` for, that ran a non-minimal posture) and
# `lever_engaged` are informational lever-adoption columns.
#
# `avoided_tokens` is a scope-gated subtraction estimate: for a plan where a
# cost-reducing lever WAS engaged AND that came in under its class target, the
# headroom kept under target (`target - total_tokens`) — an UPPER-BOUND estimate
# of the tokens the engaged lever helped avoid. Zero when no lever engaged or the
# plan overspent. Summed corpus-wide into `estimated_avoided_tokens`.


def _plan_total_tokens(inputs: PlanInputs) -> int:
    """Summed `total_tokens` across a plan's recorded metrics phases (0 if none)."""
    phases = parse_metrics_toon(inputs.plan_dir / "work" / "metrics.toon")
    return sum(p.total_tokens for p in phases)


def _lane_lever_row(inputs: PlanInputs, targets: dict[str, int]) -> dict[str, Any]:
    """Compute one plan's lane-lever-effectiveness row (pure over its inputs)."""
    scope = inputs.scope_estimate or ""
    checkpoint_class = scope if scope in targets else "unclassed"
    target = int(targets.get(scope, 0))
    total = _plan_total_tokens(inputs)

    recipe_routed = bool(inputs.recipe_key)
    lane = inputs.planning_lane or ""
    light_lane = lane == "light"
    posture = inputs.execution_profile or ""
    posture_minimal = posture == "minimal"
    # The #854 surgical-fix micro-lane recommends the minimal posture for a
    # surgical-scope plan; a surgical plan that ran a non-minimal posture did not
    # take the recommended lever.
    recommended_minimal = scope == "surgical"
    posture_not_taken = recommended_minimal and not posture_minimal
    lever_engaged = recipe_routed or light_lane or posture_minimal

    if total == 0:
        verdict = "no_metrics"
    elif checkpoint_class == "unclassed":
        verdict = "unclassed"
    elif total <= target:
        verdict = "within"
    else:
        verdict = "over"
    checkpoint_over = verdict == "over"

    avoided_tokens = (
        max(0, target - total) if lever_engaged and verdict == "within" else 0
    )

    return {
        "plan_id": inputs.plan_id,
        "scope": scope,
        "checkpoint_class": checkpoint_class,
        "target": target,
        "total_tokens": total,
        "verdict": verdict,
        "recipe_routed": str(recipe_routed).lower(),
        "lane": lane,
        "posture": posture,
        "posture_not_taken": str(posture_not_taken).lower(),
        "lever_engaged": str(lever_engaged).lower(),
        "avoided_tokens": avoided_tokens,
        "flags": "checkpoint_over" if checkpoint_over else "",
    }


def _lane_lever_genuine(row: dict[str, Any]) -> bool:
    """Genuine (actionable): the plan overspent its armed checkpoint target."""
    return bool(row.get("flags"))


def cross_lane_lever_effectiveness(all_inputs: list[PlanInputs]) -> dict[str, Any]:
    """Cross-plan lane-lever effectiveness + per-class checkpoint verdicts.

    Emits one row per scanned plan (sorted by plan_id) carrying its checkpoint
    verdict and lever-adoption columns, plus corpus aggregates: the lever-
    engagement counts (recipe auto-routes, light-lane fires, minimal-posture
    choices), the per-checkpoint-class over-target tallies, and the corpus-wide
    `estimated_avoided_tokens`. Best-effort: an empty corpus yields no rows and
    zeroed aggregates.
    """
    targets = cast(dict[str, int], THRESHOLDS["checkpoint_token_targets"])
    rows = [_lane_lever_row(i, targets) for i in sorted(all_inputs, key=lambda x: x.plan_id)]

    def _class_over(cls: str) -> tuple[int, int]:
        members = [r for r in rows if r["checkpoint_class"] == cls]
        return sum(1 for r in members if r["verdict"] == "over"), len(members)

    by_class = {
        cls: {"over": _class_over(cls)[0], "n": _class_over(cls)[1], "target": int(targets[cls])}
        for cls in targets
    }
    corpus = {
        "plans_measured": sum(1 for r in rows if int(r["total_tokens"]) > 0),
        "recipe_routed_count": sum(1 for r in rows if r["recipe_routed"] == "true"),
        "light_lane_fires": sum(1 for r in rows if r["lane"] == "light"),
        "minimal_posture_chosen": sum(1 for r in rows if r["posture"] == "minimal"),
        "posture_not_taken_count": sum(1 for r in rows if r["posture_not_taken"] == "true"),
        "checkpoint_over_count": sum(1 for r in rows if r["verdict"] == "over"),
        "estimated_avoided_tokens": sum(int(r["avoided_tokens"]) for r in rows),
        "by_class": by_class,
    }
    return {"rows": rows, "corpus": corpus}


def emit_lane_lever_effectiveness_block(result: dict[str, Any]) -> str:
    """Emit the lane-lever-effectiveness block with the D1 severity column."""
    rows = result["rows"]
    corpus = result["corpus"]
    rows, genuine_signal_count = _severity_summary(rows, _lane_lever_genuine)
    by_class = corpus["by_class"]
    out = [
        "check: lane-lever-effectiveness",
        "status: success",
        f"plans_measured: {corpus['plans_measured']}",
        f"recipe_routed: {corpus['recipe_routed_count']}",
        f"light_lane_fires: {corpus['light_lane_fires']}",
        f"minimal_posture_chosen: {corpus['minimal_posture_chosen']}",
        f"posture_not_taken: {corpus['posture_not_taken_count']}",
        f"checkpoint_over: {corpus['checkpoint_over_count']}",
        f"estimated_avoided_tokens: {corpus['estimated_avoided_tokens']}",
    ]
    for cls in ("surgical", "single_module", "multi_module"):
        c = by_class[cls]
        out.append(f"{cls}_over: {c['over']}/{c['n']} (target {c['target']})")
    out.append(f"genuine_signal_count: {genuine_signal_count}")
    out.append(
        f"rows[{len(rows)}]{{plan_id,scope,checkpoint_class,target,total_tokens,verdict,"
        f"recipe_routed,lane,posture,posture_not_taken,lever_engaged,avoided_tokens,flags,severity}}:"
    )
    for r in rows:
        out.append(
            "  "
            + ",".join(
                _cell(c)
                for c in [
                    r["plan_id"],
                    r["scope"],
                    r["checkpoint_class"],
                    r["target"],
                    r["total_tokens"],
                    r["verdict"],
                    r["recipe_routed"],
                    r["lane"],
                    r["posture"],
                    r["posture_not_taken"],
                    r["lever_engaged"],
                    r["avoided_tokens"],
                    r["flags"],
                    r["severity"],
                ]
            )
        )
    return "\n".join(out) + "\n"


def cross_check_synthesis(all_results: dict[str, Any]) -> dict[str, Any]:
    """Compute the cross-check couplings from the retained check results.

    `all_results` maps a check name to the structured result that check computed
    (the per-plan row list for per-plan checks, the cross-plan result dict for
    cross-plan checks). Reads them — never the emitted strings — and returns a
    result dict consumed by `emit_cross_check_synthesis_block`: one coupling row
    per coupling with `fired` / `caveat` / `detail`, plus the count of fired
    couplings. Best-effort: a missing upstream result degrades that coupling to
    `fired: false` rather than raising.
    """
    trend = all_results.get("token-efficiency-trend")
    integrity = all_results.get("input-integrity")
    sequence = all_results.get("sequence-and-build-minimality")
    economics = all_results.get("token-economics")
    quality_chain = all_results.get("quality-chain")
    recurring = all_results.get("recurring-pattern-detector")
    global_log = all_results.get("global-log-analysis")
    quality_verification = all_results.get("quality-verification-report")
    scope = all_results.get("scope-estimate-accuracy")
    task_count = all_results.get("task-count-efficiency")
    task_graph = all_results.get("task-graph-redundancy")
    dispatch_topology = all_results.get("dispatch-topology")
    finalize_flow = all_results.get("finalize-flow-conformance")
    merge_window = all_results.get("merge-window-accounting")
    lane_lever = all_results.get("lane-lever-effectiveness")

    rows: list[dict[str, Any]] = []

    # (a) trend_empty_untrustworthy.
    trend_regression = (
        trend.get("regression") if isinstance(trend, dict) else None
    ) or ""
    blind_plan_ids = sorted(
        str(r.get("plan_id"))
        for r in (integrity or [])
        if isinstance(r, dict) and r.get("data_confidence") == "blind"
    )
    a_fired = bool(not trend_regression and blind_plan_ids)
    rows.append(
        {
            "coupling": "trend_empty_untrustworthy",
            "fired": a_fired,
            "detail": (
                f"token-trend regression=empty over {len(blind_plan_ids)} "
                f"blind-execute plan(s): {';'.join(blind_plan_ids)}"
                if a_fired
                else (
                    f"regression={trend_regression!r}; blind_execute_plans={len(blind_plan_ids)}"
                )
            ),
            "caveat": (
                "empty regression over blind-execute plans is floor-not-truth: "
                "the trend saw no rise because execute tokens were never recorded"
            ),
        }
    )

    # (b) churn_explains_walltime.
    #
    # This coupling correlates build churn against build WALL-CLOCK
    # (`total_build_seconds`), NOT against the token metric. Builds are cheap in tokens
    # BY DESIGN — `doc/concepts/build-management.adoc`: a build costs ~100 tokens (the
    # TOON envelope), the LLM suspends on the synchronous call (zero tokens during the
    # wait), and the build log never enters context. So build redundancy is a
    # WALL-CLOCK cost (the developer pays it in latency), not a token cost — that is the
    # axis to correlate against. (Separately, the recorded `total_tokens` = input+output
    # excludes cache_read/cache_creation, a context-size-dependent under-count of total
    # traffic — but that is a per-turn property orthogonal to builds; see the
    # token-economics measurement caveat.) The visible token over-spend on these plans
    # is generation volume (`long_session`) + execution-context fragmentation, not builds.
    churn_plans = _syn_flagged_plans(
        sequence,
        lambda f: f.startswith("non_minimal_build") or f.startswith("build_churn"),
    )
    walltime_outlier_plans = _syn_build_walltime_outlier_plans(sequence)
    b_plans = sorted(churn_plans & walltime_outlier_plans)
    b_fired = bool(b_plans)
    rows.append(
        {
            "coupling": "churn_explains_walltime",
            "fired": b_fired,
            "detail": (
                f"{len(b_plans)} plan(s) with non_minimal_build/build_churn AND build "
                f"wall-clock in the corpus upper half (>= median total_build_seconds): "
                f"{';'.join(b_plans)}"
                if b_fired
                else f"churn_plans={len(churn_plans)};walltime_outlier_plans={len(walltime_outlier_plans)}"
            ),
            "caveat": (
                "build redundancy is a WALL-CLOCK cost, not a token cost: builds are cheap "
                "in tokens by design (~100-token TOON; the LLM suspends on the synchronous "
                "call — doc/concepts/build-management.adoc), so churn is correlated against "
                "wall-clock. The visible token over-spend on these plans is generation "
                "volume (long_session) + execution-context fragmentation, not builds"
            ),
        }
    )

    # (c) qgate_gap_chain.
    qgate_gap_plans = _syn_flagged_plans(
        quality_chain,
        lambda f: f.startswith("no_qgate6") or f.startswith("auto_review_only"),
    )
    ci_rerun_plans = _syn_flagged_plans(sequence, lambda f: f.startswith("ci_rerun"))
    finalize_heavy_plans = _syn_flagged_plans(
        economics, lambda f: f.startswith("finalize_heavy")
    )
    c_plans = sorted(qgate_gap_plans & (ci_rerun_plans | finalize_heavy_plans))
    c_fired = bool(c_plans)
    rows.append(
        {
            "coupling": "qgate_gap_chain",
            "fired": c_fired,
            "detail": (
                f"{len(c_plans)} plan(s) with no_qgate6/auto_review_only AND "
                f"ci_rerun OR finalize_heavy: {';'.join(c_plans)}"
                if c_fired
                else f"qgate_gap_plans={len(qgate_gap_plans)};ci_rerun_plans={len(ci_rerun_plans)};finalize_heavy_plans={len(finalize_heavy_plans)}"
            ),
            "caveat": (
                "missing self-review surface co-occurring with a CI re-run / heavy "
                "finalize is the shift-right tax — the PR round-trip paid for what "
                "an earlier gate could have caught"
            ),
        }
    )

    # (d) argparse_signature_cluster — collapsed to ONE candidate.
    argparse_signatures = sorted(
        str(r.get("signature"))
        for r in (recurring.get("rows", []) if isinstance(recurring, dict) else [])
        if isinstance(r, dict) and _SYN_ARGPARSE_SIG_RE.search(str(r.get("signature") or ""))
    )
    global_error_count = (
        int(global_log.get("error_count", 0)) if isinstance(global_log, dict) else 0
    )
    qv_unfiled_total = 0
    for r in quality_verification or []:
        if isinstance(r, dict):
            qv_unfiled_total += int(r.get("unfiled_lessons") or 0)
    d_fired = bool(argparse_signatures and global_error_count > 0 and qv_unfiled_total > 0)
    rows.append(
        {
            "coupling": "argparse_signature_cluster",
            "fired": d_fired,
            "detail": (
                f"argparse signatures={';'.join(argparse_signatures)} correlate with "
                f"global-log errors={global_error_count} and unfiled "
                f"quality-verification signatures={qv_unfiled_total} — collapse to ONE "
                f"source-keyed candidate"
                if d_fired
                else f"argparse_signatures={len(argparse_signatures)};global_errors={global_error_count};qv_unfiled={qv_unfiled_total}"
            ),
            "caveat": (
                "the three facets are three views of ONE source-keyed argparse "
                "drift — file ONE source-keyed lesson, not one per facet"
            ),
        }
    )

    # (e) scope_underestimate_cost.
    scope_under_plans = {
        str(r.get("plan_id"))
        for r in (scope or [])
        if isinstance(r, dict) and r.get("mismatch")
    }
    # High tokens-per-file tail: plans at/above the corpus median tokens_per_file.
    tpf_values = [
        int(r.get("tokens_per_file") or 0)
        for r in (economics.get("rows", []) if isinstance(economics, dict) else [])
        if isinstance(r, dict)
    ]
    tpf_median = median([float(v) for v in tpf_values]) if tpf_values else 0.0
    high_tpf_plans = {
        str(r.get("plan_id"))
        for r in (economics.get("rows", []) if isinstance(economics, dict) else [])
        if isinstance(r, dict)
        and tpf_median > 0
        and int(r.get("tokens_per_file") or 0) >= tpf_median
    }
    outlier_task_plans = {
        str(r.get("plan_id"))
        for r in (task_count or [])
        if isinstance(r, dict) and r.get("outlier")
    }
    e_plans = sorted(scope_under_plans & (high_tpf_plans | outlier_task_plans))
    e_fired = bool(e_plans)
    rows.append(
        {
            "coupling": "scope_underestimate_cost",
            "fired": e_fired,
            "detail": (
                f"{len(e_plans)} plan(s) with a scope mismatch AND high tokens/file "
                f"(>=median={tpf_median:.0f}) OR a task-count outlier: {';'.join(e_plans)}"
                if e_fired
                else f"scope_mismatch_plans={len(scope_under_plans)};high_tpf_plans={len(high_tpf_plans)};outlier_task_plans={len(outlier_task_plans)}"
            ),
            "caveat": (
                "an under-estimated scope predicts the over-spend — the coupling "
                "names the predicted-vs-actual gap, not a fresh finding"
            ),
        }
    )

    # (f) redundant_build_churn — a plan whose task graph bakes a HEAVY build
    # into a task's verification (`in_task_build`) AND whose runtime sequence was
    # flagged `build_churn` / `phase_reentry`. The static redundancy (a build the
    # task list duplicated) and the observed runtime churn are two views of the
    # same wasted compute.
    in_task_build_plans = _syn_in_task_build_plans(task_graph)
    churn_reentry_plans = _syn_flagged_plans(
        sequence,
        lambda f: f.startswith("build_churn") or f.startswith("phase_reentry"),
    )
    f_plans = sorted(in_task_build_plans & churn_reentry_plans)
    f_fired = bool(f_plans)
    rows.append(
        {
            "coupling": "redundant_build_churn",
            "fired": f_fired,
            "detail": (
                f"{len(f_plans)} plan(s) with an in_task_build AND "
                f"build_churn/phase_reentry: {';'.join(f_plans)}"
                if f_fired
                else f"in_task_build_plans={len(in_task_build_plans)};"
                f"churn_reentry_plans={len(churn_reentry_plans)}"
            ),
            "caveat": (
                "a heavy build baked into a task's verification is a STATIC "
                "redundancy; confirm it co-occurs with the observed build_churn "
                "runtime signal before filing — the two corroborate one waste"
            ),
        }
    )

    # (g) dispatch_topology_reentry — a plan whose work.log recorded a LEAF-emitted
    # subagent dispatch (a topology-invariant violation) AND whose runtime sequence
    # was flagged `phase_reentry`. A leaf that spawns a subagent surfaces the extra
    # dispatch as an unexpected phase re-entry; the static topology violation and the
    # observed re-entry corroborate one anomalous dispatch.
    topo_violation_plans = {
        str(r.get("plan_id"))
        for r in (dispatch_topology or [])
        if isinstance(r, dict) and int(r.get("leaf_dispatch") or 0) > 0
    }
    reentry_plans = _syn_flagged_plans(sequence, lambda f: f.startswith("phase_reentry"))
    g_plans = sorted(topo_violation_plans & reentry_plans)
    g_fired = bool(g_plans)
    rows.append(
        {
            "coupling": "dispatch_topology_reentry",
            "fired": g_fired,
            "detail": (
                f"{len(g_plans)} plan(s) with a leaf-emitted dispatch AND "
                f"phase_reentry: {';'.join(g_plans)}"
                if g_fired
                else f"topo_violation_plans={len(topo_violation_plans)};reentry_plans={len(reentry_plans)}"
            ),
            "caveat": (
                "a leaf-emitted subagent dispatch VIOLATES the leaf/dispatch-topology "
                "invariant (subagents are leaves); a co-occurring phase_reentry "
                "corroborates the extra dispatch as observed rework"
            ),
        }
    )

    # (h) finalize_gate_gap_ci_rerun — a plan whose finalize flow was non-conformant
    # (missing the #849 deterministic ci_verify gate, or its recorded CI never
    # resolved green) AND whose runtime sequence re-ran CI. The missing/failed
    # deterministic gate and the observed CI re-run are two views of the shift-right
    # tax the post-#849 flow exists to remove.
    finalize_gap_plans = {
        str(r.get("plan_id"))
        for r in (finalize_flow or [])
        if isinstance(r, dict)
        and ("missing_ci_verify" in str(r.get("flags") or "") or "ci_unresolved" in str(r.get("flags") or ""))
    }
    h_ci_rerun_plans = _syn_flagged_plans(sequence, lambda f: f.startswith("ci_rerun"))
    h_plans = sorted(finalize_gap_plans & h_ci_rerun_plans)
    h_fired = bool(h_plans)
    rows.append(
        {
            "coupling": "finalize_gate_gap_ci_rerun",
            "fired": h_fired,
            "detail": (
                f"{len(h_plans)} plan(s) with missing_ci_verify/ci_unresolved AND "
                f"ci_rerun: {';'.join(h_plans)}"
                if h_fired
                else f"finalize_gap_plans={len(finalize_gap_plans)};ci_rerun_plans={len(h_ci_rerun_plans)}"
            ),
            "caveat": (
                "a non-conformant finalize flow (absent #849 ci_verify gate or an "
                "unresolved CI) co-occurring with a CI re-run is the deterministic-gate "
                "gap the post-#849 flow removes — confirm both before filing"
            ),
        }
    )

    # (i) merge_window_ci_rerun — a plan that WAITED in the #849 merge admission
    # queue (merge_contention) AND re-ran CI OR paid a heavy finalize. A plan queued
    # behind the merge mutex whose HEAD advanced (rebase/re-review) legitimately
    # re-runs CI; the coupling accounts for the merge-window cost the widened mutex
    # trades for fairness/parallelism.
    contended_plans = {
        str(r.get("plan_id"))
        for r in (merge_window.get("rows", []) if isinstance(merge_window, dict) else [])
        if isinstance(r, dict) and r.get("flags")
    }
    i_ci_rerun_plans = _syn_flagged_plans(sequence, lambda f: f.startswith("ci_rerun"))
    i_finalize_heavy_plans = _syn_flagged_plans(
        economics, lambda f: f.startswith("finalize_heavy")
    )
    i_plans = sorted(contended_plans & (i_ci_rerun_plans | i_finalize_heavy_plans))
    i_fired = bool(i_plans)
    rows.append(
        {
            "coupling": "merge_window_ci_rerun",
            "fired": i_fired,
            "detail": (
                f"{len(i_plans)} plan(s) with merge_contention AND ci_rerun OR "
                f"finalize_heavy: {';'.join(i_plans)}"
                if i_fired
                else f"contended_plans={len(contended_plans)};ci_rerun_plans={len(i_ci_rerun_plans)};finalize_heavy_plans={len(i_finalize_heavy_plans)}"
            ),
            "caveat": (
                "merge-queue contention co-occurring with a CI re-run / heavy finalize "
                "is the merge-window cost the #849 widened mutex trades for fair "
                "ordering — it is accounting, not necessarily waste"
            ),
        }
    )

    # (j) surgical_overpay — a plan that MISSED the lane lever (spent over its
    # armed checkpoint target — a genuine lane-lever-effectiveness signal) AND was
    # independently flagged `big_spend_tiny_footprint` by token-economics. The
    # checkpoint overspend and the tokens/file inversion are two views of the same
    # over-spend on a plan the cheap lane existed to keep small.
    lane_lever_miss_plans = {
        str(r.get("plan_id"))
        for r in (lane_lever.get("rows", []) if isinstance(lane_lever, dict) else [])
        if isinstance(r, dict) and "checkpoint_over" in str(r.get("flags") or "")
    }
    big_spend_plans = _syn_flagged_plans(
        economics, lambda f: f.startswith("big_spend_tiny_footprint")
    )
    j_plans = sorted(lane_lever_miss_plans & big_spend_plans)
    j_fired = bool(j_plans)
    rows.append(
        {
            "coupling": "surgical_overpay",
            "fired": j_fired,
            "detail": (
                f"{len(j_plans)} plan(s) over the armed checkpoint target AND "
                f"big_spend_tiny_footprint: {';'.join(j_plans)}"
                if j_fired
                else f"lane_lever_miss_plans={len(lane_lever_miss_plans)};big_spend_plans={len(big_spend_plans)}"
            ),
            "caveat": (
                "a checkpoint overspend co-occurring with big_spend_tiny_footprint "
                "is a lane-lever MISS — the cheap lane (recipe/light/minimal) existed "
                "to keep this plan small; confirm both facets before filing"
            ),
        }
    )

    fired_count = sum(1 for r in rows if r["fired"])
    return {
        "couplings_evaluated": len(rows),
        "couplings_fired": fired_count,
        "rows": rows,
    }


def _syn_genuine(row: dict[str, Any]) -> bool:
    """Genuine-signal predicate for one cross-check-synthesis coupling row.

    Genuine (actionable): the coupling FIRED — a cross-facet correlation surfaced
    that a single check's rows individually miss. Informational: a coupling that
    did not fire (its facets did not co-occur), carried for completeness so the
    read-out shows every coupling was evaluated.
    """
    return bool(row["fired"])


def emit_cross_check_synthesis_block(result: dict[str, Any]) -> str:
    """Emit the cross-check-synthesis block with the D1 severity column.

    One row per coupling, each carrying the `fired` boolean, the cross-facet
    `detail`, the qualifying `caveat`, and the uniform D1 `severity` column
    (`genuine` when the coupling fired) stamped via the shared `_severity_summary`
    helper. The block leads with `couplings_evaluated` / `couplings_fired` so the
    read-out shows the critic ran every coupling, then emits one
    `rows[N]{coupling,fired,caveat,detail,severity}` table. This block
    operationalizes the SKILL.md Step-4b completeness critic: a fired coupling is
    a cross-check signal the per-check adjudication must resolve before dormation.
    """
    rows = result["rows"]
    for r in rows:
        r["fired_str"] = str(r["fired"]).lower()
    rows, genuine_signal_count = _severity_summary(rows, _syn_genuine)
    out = [
        "check: cross-check-synthesis",
        "status: success",
        f"couplings_evaluated: {result['couplings_evaluated']}",
        f"couplings_fired: {result['couplings_fired']}",
        f"genuine_signal_count: {genuine_signal_count}",
        f"rows[{len(rows)}]{{coupling,fired,caveat,detail,severity}}:",
    ]
    for r in rows:
        out.append(
            "  "
            + ",".join(
                _cell(c)
                for c in [
                    r["coupling"],
                    r["fired_str"],
                    r["caveat"],
                    r["detail"],
                    r["severity"],
                ]
            )
        )
    return "\n".join(out) + "\n"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def run_checks(all_inputs: list[PlanInputs], selected: list[str], repo_root: Path) -> str:
    corpus_sigs = _lessons_corpus_signatures(repo_root)
    corpus_titles = _lessons_corpus_titles(repo_root)
    blocks: list[str] = []
    summary_metrics: dict[str, Any] = {}

    # cross-check-synthesis consumes the OTHER checks' RETAINED structured results.
    # When it is selected we must COMPUTE every upstream check's result even if the
    # upstream itself was not selected (e.g. `--check cross-check-synthesis`), so
    # the synthesis can read them. `all_results` is that retention store: each
    # upstream stores its structured result here at computation time; the upstream
    # block is EMITTED only when the upstream is itself selected. This keeps every
    # existing check's emitted output and summary_metrics byte-for-byte identical
    # when synthesis is not selected (`synth_needed` is False, so the `or` guard
    # collapses to the original `in selected` condition).
    synth_needed = "cross-check-synthesis" in selected
    all_results: dict[str, Any] = {}

    if "execution-context-manifest" in selected:
        role_cache: dict[str, str | None] = {}
        rows = [check_execution_manifest(i, repo_root, role_cache) for i in all_inputs]
        block = emit_manifest_block(rows)
        summary_metrics["execution-context-manifest_genuine"] = sum(
            1 for r in rows if _manifest_genuine(r)
        )
        blocks.append(block)

    if "quality-verification-report" in selected or synth_needed:
        rows = [check_quality_verification(i, corpus_sigs) for i in all_inputs]
        all_results["quality-verification-report"] = rows
        if "quality-verification-report" in selected:
            emit_rows = [
                {
                    **r,
                    "unfiled_signatures": ";".join(r["unfiled_signatures"]),
                    "candidate": _dedup_pretag(
                        r["unfiled_signatures"][0] if r["unfiled_signatures"] else "",
                        corpus_titles,
                    ),
                }
                for r in rows
            ]
            blocks.append(
                emit_table_block(
                    "quality-verification-report",
                    ["plan_id", "findings_present", "proposed_lessons", "unfiled_lessons", "unfiled_signatures", "candidate"],
                    emit_rows,
                    lambda r: bool(r["unfiled_lessons"]),
                )
            )
            summary_metrics["quality-verification-report_unfiled"] = sum(
                int(r["unfiled_lessons"]) for r in rows
            )

    if "metrics" in selected or synth_needed:
        rows = [check_metrics(i) for i in all_inputs]
        all_results["metrics"] = rows
        if "metrics" in selected:
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
                    lambda r: bool(
                        r["disproportionate_token"]
                        or r["incomplete_recording"]
                        or r["impossible_value"]
                    ),
                )
            )

    if "scope-estimate-accuracy" in selected or synth_needed:
        rows = [check_scope_estimate(i) for i in all_inputs]
        all_results["scope-estimate-accuracy"] = rows
        if "scope-estimate-accuracy" in selected:
            blocks.append(
                emit_table_block(
                    "scope-estimate-accuracy",
                    ["plan_id", "declared_scope", "actual_file_count", "mismatch"],
                    rows,
                    lambda r: bool(r["mismatch"]),
                )
            )

    if "track-selection-accuracy" in selected:
        routing = _load_routing_logic(repo_root)
        compatibility = _read_marshal_compatibility(repo_root)
        rows = [
            check_track_selection_accuracy(i, routing, compatibility)
            for i in all_inputs
        ]
        blocks.append(
            emit_table_block(
                "track-selection-accuracy",
                ["plan_id", "actual_lane", "actual_track", "counterfactual_lane", "verdict", "era"],
                rows,
                lambda r: r["verdict"] in {"OVER-TRACKED", "UNDER-TRACKED"},
            )
        )
        summary_metrics["track-selection-accuracy_mistracked"] = sum(
            1 for r in rows if r["verdict"] in {"OVER-TRACKED", "UNDER-TRACKED"}
        )

    if "pr-merge-velocity" in selected:
        rows = [check_pr_merge_velocity(i) for i in all_inputs]
        blocks.append(
            emit_table_block(
                "pr-merge-velocity",
                ["plan_id", "pr_number", "elapsed_hours", "flagged", "applicable"],
                rows,
                lambda r: bool(r["flagged"]),
            )
        )

    if "task-count-efficiency" in selected or synth_needed:
        rows = [check_task_count(i) for i in all_inputs]
        all_results["task-count-efficiency"] = rows
        if "task-count-efficiency" in selected:
            blocks.append(
                emit_table_block(
                    "task-count-efficiency",
                    ["plan_id", "task_count", "deliverable_count", "outlier"],
                    rows,
                    lambda r: bool(r["outlier"]),
                )
            )

    if "recurring-pattern-detector" in selected or synth_needed:
        result = cross_recurring_pattern(all_inputs)
        for r in result["rows"]:
            r["candidate"] = _dedup_pretag(r["signature"], corpus_titles)
        all_results["recurring-pattern-detector"] = result
        if "recurring-pattern-detector" in selected:
            blocks.append(emit_recurring_block(result))
            summary_metrics["recurring-pattern-detector_systemic"] = result["systemic_count"]

    if "token-efficiency-trend" in selected or synth_needed:
        result = cross_token_trend(all_inputs)
        all_results["token-efficiency-trend"] = result
        if "token-efficiency-trend" in selected:
            blocks.append(emit_trend_block(result))
            summary_metrics["token-efficiency-trend_regression"] = bool(result["regression"])

    if "global-log-analysis" in selected or synth_needed:
        log_result = cross_global_log_analysis(repo_root)
        all_results["global-log-analysis"] = log_result
        if "global-log-analysis" in selected:
            blocks.append(emit_global_log_block(log_result))
            summary_metrics["global-log-analysis_errors"] = log_result["error_count"]
            summary_metrics["global-log-analysis_fixture_leaks"] = log_result[
                "fixture_leak_count"
            ]

    if "token-economics" in selected or synth_needed:
        te_result = cross_token_economics(all_inputs)
        all_results["token-economics"] = te_result
        if "token-economics" in selected:
            blocks.append(emit_token_economics_block(te_result))
            summary_metrics["token-economics_flagged"] = sum(
                1 for r in te_result["rows"] if r["flags"]
            )

    if "quality-chain" in selected or synth_needed:
        qc_result = cross_quality_chain(all_inputs)
        all_results["quality-chain"] = qc_result
        if "quality-chain" in selected:
            blocks.append(emit_quality_chain_block(qc_result))
            summary_metrics["quality-chain_plans_flagged"] = sum(
                1 for r in qc_result["rows"] if r["flags"]
            )
            summary_metrics["quality-chain_auto_review_only"] = sum(
                1 for r in qc_result["rows"] if any(f.startswith("auto_review_only") for f in r["flags"])
            )
            th = qc_result["tier_histogram"]
            summary_metrics["quality-chain_shift_left_tier1"] = th.get(1, 0)

    if "sequence-and-build-minimality" in selected or synth_needed:
        sbm_result = cross_sequence_build_minimality(all_inputs)
        all_results["sequence-and-build-minimality"] = sbm_result
        if "sequence-and-build-minimality" in selected:
            blocks.append(emit_sequence_build_minimality_block(sbm_result))
            summary_metrics["sequence-and-build-minimality_flagged"] = sum(
                1 for r in sbm_result["rows"] if r["flags"]
            )
            summary_metrics["sequence-and-build-minimality_heavy_builds"] = sbm_result[
                "corpus"
            ]["heavy"]
            summary_metrics["sequence-and-build-minimality_docs_only_build_plans"] = (
                sbm_result["corpus"]["docs_only_build_plans"]
            )

    if "input-integrity" in selected or synth_needed:
        ii_rows = [check_input_integrity(i) for i in all_inputs]
        all_results["input-integrity"] = ii_rows
        if "input-integrity" in selected:
            blocks.append(emit_input_integrity_block(ii_rows))
            summary_metrics["input-integrity_blind"] = sum(
                1 for r in ii_rows if r["data_confidence"] == "blind"
            )
            summary_metrics["input-integrity_partial"] = sum(
                1 for r in ii_rows if r["data_confidence"] == "partial"
            )
            summary_metrics["input-integrity_genuine"] = sum(
                1 for r in ii_rows if _input_integrity_genuine(r)
            )

    if "task-graph-redundancy" in selected or synth_needed:
        tgr_rows = [check_task_graph_redundancy(i) for i in all_inputs]
        # The per-run deliverable-fanout threshold needs the whole corpus, so it
        # is finalized here (not per-row) before retention/emit.
        tgr_threshold = _finalize_deliverable_fanout(tgr_rows)
        all_results["task-graph-redundancy"] = tgr_rows
        if "task-graph-redundancy" in selected:
            blocks.append(emit_task_graph_redundancy_block(tgr_rows, tgr_threshold))
            summary_metrics["task-graph-redundancy_genuine"] = sum(
                1 for r in tgr_rows if _task_graph_redundancy_genuine(r)
            )

    # architecture-lookup-ratio is a standalone cross-plan check (not consumed by
    # synthesis), so it is gated only on explicit selection.
    if "architecture-lookup-ratio" in selected:
        alr_result = cross_architecture_lookup_ratio(all_inputs)
        all_results["architecture-lookup-ratio"] = alr_result
        blocks.append(emit_architecture_lookup_ratio_block(alr_result))
        summary_metrics["architecture-lookup-ratio_flagged"] = sum(
            1 for r in alr_result["rows"] if r["flags"]
        )
        summary_metrics["architecture-lookup-ratio_corpus_info"] = alr_result[
            "corpus_info_lookups"
        ]
        summary_metrics["architecture-lookup-ratio_corpus_build"] = alr_result[
            "corpus_build_lookups"
        ]

    if "preference-pattern-detector" in selected or synth_needed:
        pref_result = cross_preference_pattern(all_inputs)
        all_results["preference-pattern-detector"] = pref_result
        if "preference-pattern-detector" in selected:
            blocks.append(emit_preference_pattern_block(pref_result))
            summary_metrics["preference-pattern-detector_candidates"] = pref_result[
                "candidate_count"
            ]

    if "dispatch-topology" in selected or synth_needed:
        dt_rows = [check_dispatch_topology(i) for i in all_inputs]
        all_results["dispatch-topology"] = dt_rows
        if "dispatch-topology" in selected:
            blocks.append(
                emit_table_block(
                    "dispatch-topology",
                    ["plan_id", "dispatch_count", "leaf_dispatch", "violators"],
                    dt_rows,
                    _dispatch_topology_genuine,
                )
            )
            summary_metrics["dispatch-topology_violations"] = sum(
                int(r["leaf_dispatch"]) for r in dt_rows
            )

    if "finalize-flow-conformance" in selected or synth_needed:
        ffc_rows = [check_finalize_flow_conformance(i) for i in all_inputs]
        all_results["finalize-flow-conformance"] = ffc_rows
        if "finalize-flow-conformance" in selected:
            blocks.append(
                emit_table_block(
                    "finalize-flow-conformance",
                    [
                        "plan_id",
                        "has_pr_step",
                        "has_ci_verify_step",
                        "ci_run_count",
                        "final_status",
                        "flags",
                    ],
                    ffc_rows,
                    _finalize_flow_genuine,
                )
            )
            summary_metrics["finalize-flow-conformance_flagged"] = sum(
                1 for r in ffc_rows if _finalize_flow_genuine(r)
            )

    if "merge-window-accounting" in selected or synth_needed:
        mwa_result = cross_merge_window_accounting(all_inputs, repo_root)
        all_results["merge-window-accounting"] = mwa_result
        if "merge-window-accounting" in selected:
            blocks.append(emit_merge_window_accounting_block(mwa_result))
            summary_metrics["merge-window-accounting_contended"] = mwa_result["corpus"][
                "contended_plans"
            ]

    if "lane-lever-effectiveness" in selected or synth_needed:
        lle_result = cross_lane_lever_effectiveness(all_inputs)
        all_results["lane-lever-effectiveness"] = lle_result
        if "lane-lever-effectiveness" in selected:
            blocks.append(emit_lane_lever_effectiveness_block(lle_result))
            summary_metrics["lane-lever-effectiveness_checkpoint_over"] = lle_result[
                "corpus"
            ]["checkpoint_over_count"]

    # cross-check-synthesis MUST run LAST — it reads every upstream result the
    # blocks above retained into `all_results`.
    if synth_needed:
        syn_result = cross_check_synthesis(all_results)
        blocks.append(emit_cross_check_synthesis_block(syn_result))
        summary_metrics["cross-check-synthesis_fired"] = syn_result["couplings_fired"]

    summary_metrics["plans_scanned"] = len(all_inputs)

    # Era model: persist the uniform per-check genuine substrate, stamp each
    # emitted block with its `fixed_since` boundary, and (on a full sweep) surface
    # the retire-on-quiet proposals over the recorded-run history.
    per_check_genuine = _extract_per_check_genuine(blocks)
    for check_name, genuine_count in per_check_genuine.items():
        summary_metrics[f"{_GENUINE_METRIC_PREFIX}{check_name}"] = genuine_count
    blocks = [_stamp_era(block) for block in blocks]
    if set(selected) == set(CHECK_NAMES):
        proposals, runs_recorded = _retire_on_quiet_proposals(repo_root, per_check_genuine)
        blocks.append(emit_retire_on_quiet_block(proposals, runs_recorded))

    diff_block = _report_diff_block(repo_root, summary_metrics)
    if diff_block:
        blocks.append(diff_block)
    write_persisted_report(repo_root, blocks, summary_metrics)

    return "\n".join(blocks)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description="Audit archived plans across twenty-two retrospective checks."
    )
    parser.add_argument(
        "--plan-dir",
        default=".plan/local/archived-plans",
        help="Directory containing per-plan subdirectories. Defaults to .plan/local/archived-plans.",
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
        nargs="+",
        metavar="PLAN_ID",
        help="Relocate one or more archived plans to `.plan/temp/dormated-plans/`. Duplicate ids are deduplicated silently; the whole batch is moved all-or-nothing. Inert (refused, exit 0) unless --confirmed is also passed.",
    )
    parser.add_argument(
        "--dormate-all",
        action="store_true",
        help="Relocate EVERY archived plan under `.plan/local/archived-plans/` to `.plan/temp/dormated-plans/`. Same all-or-nothing posture as --dormate. Inert (refused, exit 0) unless --confirmed is also passed.",
    )
    parser.add_argument(
        "--dormate-global-logs",
        action="store_true",
        help="Relocate COMPLETE past-date global logs (`{prefix}-YYYY-MM-DD.log`) from `.plan/local/logs/` to `.plan/temp/dormated-plans/global-logs/`. Today's still-active log is never moved. Inert (refused, exit 0) unless --confirmed is also passed.",
    )
    parser.add_argument(
        "--confirmed",
        action="store_true",
        help="Confirm the destructive dormation move (no-op without --dormate / --dormate-all / --dormate-global-logs).",
    )
    args = parser.parse_args(argv)

    repo_root = Path.cwd()

    if args.dormate or args.dormate_all:
        if args.dormate_all:
            result = dormate_all_plans(repo_root, args.confirmed)
            operation = "dormate-all"
        else:
            result = dormate_plans(repo_root, args.dormate, args.confirmed)
            operation = "dormate"
        moved = result.get("moved", [])
        out = [f"operation: {operation}", f"status: {result['status']}"]
        if "plan_id" in result:
            out.append(f"plan_id: {result['plan_id']}")
        if result.get("moved_to"):
            out.append(f"moved_to: {result['moved_to']}")
        if "reason" in result:
            out.append(f'reason: "{result["reason"]}"')
        out.append(f"moved[{len(moved)}]{{plan_id}}:")
        for name in moved:
            out.append(f"  {name}")
        sys.stdout.write("\n".join(out) + "\n")
        return 0 if result["status"] in {"success", "refused"} else 1

    if args.dormate_global_logs:
        result = dormate_global_logs(repo_root, args.confirmed)
        moved = result.get("moved", [])
        out = ["operation: dormate-global-logs", f"status: {result['status']}"]
        if result.get("moved_to"):
            out.append(f"moved_to: {result['moved_to']}")
        if "reason" in result:
            out.append(f'reason: "{result["reason"]}"')
        out.append(f"moved[{len(moved)}]{{date_file}}:")
        for name in moved:
            out.append(f"  {name}")
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
