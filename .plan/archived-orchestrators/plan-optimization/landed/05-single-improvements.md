# 05 — Single Improvements (independent of the lane feature)

**Status: LANDED REFERENCE — do not execute from this doc.** Its live content has been extracted into
self-contained plan documents under [`../plans/`](../plans/): §1+§3 → `plan-1-execution-loop.md`,
§2+§5 → `plan-3-finalize-flow.md`, §4 → `plan-4-find-triage.md` (the consolidated triage is its
home); **§6 SHIPPED (PR #812)**. This document remains the original analysis/spec context. Small,
**separately-shippable** improvements surfaced by the token
analysis ([`03-synthesis-optimal-path.md`](../03-synthesis-optimal-path.md)) and the lane design
([`04-execution-profile-lane-selection-outline.md`](04-execution-profile-lane-selection-outline.md)).
Each stands alone — no dependency on `04` or on each other — so each can be its own small plan and ship
ahead of the larger execution-profile feature.

## 1. Deterministic q-gate re-validation + `q_gate_validation` knob

**Problem.** A q-gate *re-run* is a subagent **re-dispatch** (reloads persona + skill docs + outline
state) — and re-dispatches are a dominant cost (the synthesis measured ~320k of one plan in outline
re-dispatches). Worse, re-runs fire even when nothing changed (the synthesis flagged integrate-sonar:
"q-gate ×2, 0 findings, ~0.35M").

**Change.**
- The **first q-gate pass always runs** (adversarial validator). A **re-run fires only when the
  validated outline/plan changed since the last pass** — gated on the artifact's content hash, never an
  unconditional repeat.
- Re-validation is done **cheaply**: in the *same* agent turn that fixed the finding (no re-dispatch),
  and/or via the deterministic part of the scope-criterion check — not a fresh dispatch.
- Operator control via a per-q-gate-step param **`q_gate_validation`** (nested in `marshal.json`, so the
  outline and plan q-gates tune independently):
  - `off` — do not run at all (no first pass, no re-validation);
  - `once` — first pass only; accept fixes without re-validation (downstream adversarial steps catch a bad fix);
  - `until_clean` — re-validate after each change until a pass is clean. **Default.**
- Confidence is **not** a gate (the doc-validation run — 99% confidence + a real q-gate finding — shows
  confidence and outline-correctness are different axes).

**Surface.** `phase-3-outline` + `phase-4-plan` q-gate steps; the content-hash of the validated
artifact; `manage-config` declares `q_gate_validation`; the in-turn / deterministic re-validation path.

**Evidence.** synthesis §"Structural cost drivers" + lesson `2026-06-30-08-001` (outline re-dispatch
inflation; integrate-sonar's "q-gate ×2, 0 findings").

**Independence.** Needs only the existing q-gate. The lane feature (`04`) later *composes* this — posture
sets the knob's default (`minimal` → `once`) — but `04` is additive; without it the knob simply defaults
to `until_clean`.

**`off | once | until_clean` is a general validator-iteration policy** — the same shape fits the other
looping validators (`automated-review` re-review, `self-review` iterations); a shared `*_validation`
param could generalize it later.

## 2. `ci-verify` → deterministic CI-status check

**Problem.** The finalize `ci-verify` step is a dispatched **agent** (~50–100k tokens/plan) whose only
job is to assert "checks green" — a fact the precondition resolver already establishes via the
`requires: [ci-complete]` precondition. Spending agent tokens to re-assert it is near-zero marginal
value.

**Change.** Replace the dispatched `ci-verify` agent with a **deterministic script check** that reads CI
status through the CI abstraction (`tools-integration-ci`) and asserts green — no LLM dispatch. On a
non-green/edge state it surfaces the failure for handling exactly as today.

**Surface.** `phase-6-finalize` `ci-verify` step; `plan-marshall:tools-integration-ci`.

**Evidence.** synthesis recommendation 2 (~50–100k/plan to re-assert CI green the precondition resolver
already established).

**Independence.** Pure replacement of one finalize step's implementation; no lane dependency. (In `04`,
`ci-verify` is a `core` lane-element regardless of how it's implemented, so the two don't interact.)

## 3. Execute-envelope-loop fix (`task_complete_returned_verbatim`)

**Problem.** phase-4-plan's bin-packer puts tasks into **one** envelope (`envelope_count: 1`) so a single
phase-5-execute dispatch loads context once and loops all tasks. Instead the execute leaf returns the
bare `task_complete` **after the first task on every dispatch**, so the orchestrator **re-dispatches per
task** — a correctly-batched 7-task envelope became ~9 dispatches (+2 for loop-back). Each re-dispatch
reloads persona + `execute-task` + domain skills + re-reads task state; on integrate-sonar this alone
likely accounts for the bulk of the ~1.63M execute spend. The single most *fixable* miss in the analysis.

**Change (decide in the plan).**
- **(a)** the execute leaf runs its **envelope loop** — iterates all same-`envelope_id` tasks in one
  dispatch before returning `task_complete`; or
- **(b)** the orchestrator **force-batches** the remaining same-`envelope_id` tasks instead of
  re-dispatching when it sees a bare `task_complete` mid-envelope.

**Surface.** phase-5-execute envelope-group executor; the execution-context return contract
(`task_complete` handling at the dispatch boundary); `manage-execution-manifest` `envelope_count`.

**Evidence.** lesson `2026-06-30-08-001` (recurrence item 1 — "the single most *fixable* miss").

**Independence.** Pure reliability fix to the execute dispatch loop; no dependency on `04`/`06`. (Its
per-dispatch token impact becomes measurable once `06`'s dispatch-cost instrumentation lands, but the fix
ships without it.) It is an execution-context dispatch concern that sits here, with the other discrete
ship-now fixes, rather than in `06`'s optimization restructurings.

## 4. Self-consistent finder — no contradictory auto-apply

**Problem.** The `finalize-step-security-audit` agent applied a `PLUGIN_CACHE_PATH` hardening that
**contradicted its own accepted sibling finding** (`PLAN_MARSHALL_CREDENTIALS_DIR`, which it had left
as-is) — same sink class, opposite disposition. The inconsistent edit broke 2 test-isolation tests, was
caught by the orchestrator's pre-push re-verify, and reverted — costing the audit dispatch (~140k), a
wasted ~11-min `verify`, and a second `verify` after the revert.

**Change.** Before any finder **applies** a fix, gate it on a **disposition self-consistency check**:
collect every finding's disposition in the run; if the edit about to be applied for finding B
contradicts an `accepted`/left-as-is disposition for a sibling finding A of the **same sink class /
pattern**, **withhold the auto-apply** and surface it for human/triage instead. The principle is
"never auto-apply an edit your own run declined elsewhere."

- **Pre-`06`:** the check lives in the finder's apply path (`finalize-step-security-audit`, and any other
  finder that both judges and applies).
- **Post-`06`:** dispositions are decided in the consolidated triage (`06` §1), so the consistency gate
  moves there — one place sees all dispositions, which is the natural home; it then also covers
  cross-producer contradictions, not just within one finder.

**Surface.** `finalize-step-security-audit` apply path; the disposition records in `manage-findings`; the
apply gate (a deterministic same-class-opposite-disposition predicate, LLM only for the ambiguous "same
class?" call). Generalizes to any auto-applying finder.

**Evidence.** synthesis recurrence item 3 (the `PLUGIN_CACHE_PATH` revert).

**Independence.** Standalone gate on the apply path; no dependency on `04`/`06`, though it composes with
`06` §1 (when triage consolidates, the gate moves to the single triage step). Adds no config knob — it
is a correctness gate, not a tunable.

## 5. Hold `main` steady across the CI wait (anti-staleness merge)

**Problem.** Between "CI goes green on commit X" and "merge X", `main` advances — parallel sessions land
PRs during the ~11-min CI wait — so the up-to-date branch-protection requirement bounces the merge; each
retry is rebase + force-push + a **full ~11-min CI cycle**. integrate-sonar paid this **twice**. The
early-baseline-rebase step does **not** close it: that handles staleness at plan *start*; the vulnerable
window is the CI wait *itself*.

**Change — two routes, pick per provider:**
- **(a) Platform merge queue** (e.g. GitHub merge queue) — submit to the queue and let the platform
  serialize merges and re-test against the latest `main` automatically, with no plan-side rebase or
  re-wait. **Handles all sources** of `main` movement (including non-plan-marshall commits). Preferred
  where the provider supports it.
- **(b) Extend the plan-marshall merge mutex across the CI wait** (platform-agnostic fallback). The merge
  mutex + FIFO admission queue already exists (`manage-locks`); today it serializes the *merge moment*.
  Acquire it **before** the pre-merge CI wait and hold it through wait + merge, so no sibling
  plan-marshall session lands on `main` during your wait → no sibling-induced staleness. Caveat: this
  **serializes plan-marshall merges** (one holds the mutex ~11 min) — a throughput cost — and does **not**
  cover external commits (only the platform queue does). So (b) is the fallback; (a) is the real fix.

**Surface.** phase-6-finalize merge / CI-wait flow; `tools-integration-ci` (platform merge-queue
integration for (a)); `manage-locks` (the merge-mutex hold window for (b)); `branch-cleanup` step.

**Evidence.** synthesis recurrence item 4 (2 staleness CI cycles on integrate-sonar).

**Independence.** Standalone; composes with the early-baseline-rebase step (plan-*start* staleness) — this
closes the *CI-wait-window* staleness. Likely adds a config knob (`use_merge_queue` / mutex-hold mode) →
`marshal.json` + `doc/user/configuration.adoc`.

## 6. Reliable per-phase metrics recording (no silently-dropped phases)

**Problem.** Across the corpus **7 of 58 plans recorded only 5/6 (or 4/6) phases** — a phase's tokens
(usually `6-finalize`) were **silently dropped**, so the plan total is a **floor, not a measurement**
(the audit's `input-integrity` check flags these `partial`). `metrics.md` carries a soft `(n=5/6)`
marker, but the *structured* total has no partial flag — so downstream consumers (plan-retrospective,
the audit, and `04`'s cost-preview calibration, `06`'s measurement) can treat an under-count as truth.

**Root cause (confirm in the plan).** Per-phase token attribution is swept from dispatch-boundary
records at the end; when a boundary record is missing — finalize interrupted, a loop-back, or
`record-metrics` running before the last finalize tokens accrue — that phase drops out of the sum with
no error, only the soft `(n=X/6)` marker.

**Change.**
- **Snapshot per phase at the transition** — record each phase's token total when the phase completes
  (its `status.json` phase → `done`), not only via an end-of-plan sweep; a completed phase keeps its
  tokens even if a later phase is interrupted.
- **Make partiality first-class** — when any phase is unrecorded, stamp the structured metrics with
  `partial: true` + `unrecorded_phases: [...]`; consumers MUST treat a partial total as a floor (the
  `input-integrity` rule, enforced at the *source* now, not only in the audit).
- **Reconcile, don't silently sum** — `record-metrics` reconciles all six phases and flags any gap,
  rather than summing whatever boundary records happen to be present.

**Surface.** `manage-metrics` (per-phase collection + the `partial` / `unrecorded_phases` flags); the
phase-boundary token attribution (the dispatch-boundary / work-log sweep); the `record-metrics` finalize
step; `metrics.md` / `metrics.toon` output. Distinct from `06` §3 (per-*dispatch* attribution) — this
fixes per-*phase* recording reliability.

**Evidence.** The audit's `input-integrity` check: 7 partial plans — `reactivate-architecture-refresh-step`,
`ci-pr-safe-merge`, `dead-extension-points-audit-fix`, `dynamic-finalize-step-discovery`,
`phase-6-finalize-strict-sync-ordering`, `security-audit-finalize-step`, `terminal-title-build-busy` —
each with a phase's tokens unrecorded.

**Independence.** Standalone data-quality fix; no dependency on `04`/`06`. It **improves the inputs**
every other token analysis relies on (04's cost-preview calibration, 06's measurement, the audit
itself), so it is a sensible *early* ship. Adds no config knob — it is a correctness fix.

## `marshal.json` + documentation (required for each improvement)

- **`marshal.json`** — each improvement that adds a config knob seeds its default into the plan-marshall
  `marshal.json` keyed-map: #1 → `q_gate_validation` (default `until_clean`) on the `phase-3-outline` /
  `phase-4-plan` q-gate steps; #5 → `use_merge_queue` / mutex-hold mode on the merge flow. (#2 ci-verify,
  #3 envelope-loop, #4 self-consistency gate add no knob.)
- **Defaults that live in `04`, not here** (cross-reference for consistency): the q-gate's *lane tier*
  (`adversarial` / `auto`) and `ci-verify`'s *lane class* (`core` / `minimal`) are set in `04`'s
  per-element default table — these improvements only change *how* those steps run, not *when* the lane
  includes them.
- **`doc/user/configuration.adoc`** — every new/changed knob MUST be documented (#1 `q_gate_validation`,
  #5 `use_merge_queue`).
- **Concept / standards docs — add or adapt** per improvement:
  - #1 → the `phase-3-outline` / `phase-4-plan` q-gate steps;
  - #2 → `phase-6-finalize` `ci-verify` + `tools-integration-ci`;
  - #3 → phase-5-execute envelope executor + the `execution-context` `task_complete` return contract;
  - #4 → `finalize-step-security-audit` apply path + `manage-findings` disposition records;
  - #5 → the `phase-6-finalize` merge flow + `manage-locks` / `tools-integration-ci`;
  - #6 → `manage-metrics` (per-phase collection + the `partial` / `unrecorded_phases` flags) + the
    `record-metrics` finalize step + the `metrics.md` / `metrics.toon` schema (no config knob).
