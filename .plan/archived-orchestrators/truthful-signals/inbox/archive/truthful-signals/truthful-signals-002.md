envelope_version=1
sender_type=orchestrator
sender_id=truthful-signals
epic=truthful-signals
kind=finding
created=2026-07-28T13:45:26Z

# FINDING: exploration cost is unmeasured, and the one check that reaches for it defers to a manual read

Operator-originated (2026-07-28). Carries a ready-to-stage plan spec below.
**Supersedes `truthful-signals-001.md`** (archived unread — same subject, over-long framing).

**Proposed queue id: PLAN-98** (next free after PLAN-97; the orchestrator owns final numbering
and position). Spec path on staging: `plans/PLAN-98-exploration-share-is-unmeasured.md`.

**Theme fit — confident-signal-hides-a-caveat.** `architecture-lookup-ratio` reports a lookup
ratio confidently, then tells its reader in prose that the reading that matters — "the lever was
bypassed" — is one the script cannot distinguish, and hands off to a manual transcript read.

---

# PLAN-98: Exploration Share Is Unmeasured, So The Citations-Only Return Shape Cannot Be Scored

epic: truthful-signals
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> **Measurement-first:** D1–D3 change no return contract. D4 may not land a contract change
> the D1–D3 baseline cannot score.

## Objective

We assert a structured-navigation lever ("structured queries first") and we count how often the
`architecture` script is called — but we never measure what exploration costs: the share of tool
turns and tokens spent locating code versus changing it. We also already have the return shape
that would reduce it (`component-analysis-contract.md`: paths and counts out, detail to a sidecar
store) applied at exactly one dispatch. Measure the share first, then generalize the shape where
the measurement says it pays.

## Claim Labels

- OBSERVED — `checks/architecture-lookup-ratio.md` § "How the orchestrator interprets the rows":
  `build_dominated_lookup` is "a **prompt, not a verdict**"; the "Lever bypassed" reading requires
  cross-reading `global-log-analysis` rows "or the transcripts". Its inputs are stated exactly —
  per plan it reads only `logs/script-execution.log` and tallies `architecture {sub}` calls, "No
  other input is consulted." **It counts the lever's use, never the behaviour the lever displaces.**
- OBSERVED — no check attributes tokens to what they were spent *on*. `checks/token-economics.md`
  derives every number from `metrics.toon::total_tokens` (share per phase). Exploration share is
  absent from all 22 checks under `checks/`.
- OBSERVED — the seam exists. `platform-runtime/scripts/claude_runtime.py`
  § `_compute_normalized_tokens` already walks the transcript and already iterates
  `message.content` items branching on `type == "tool_result"` and `== "text"`.
- OBSERVED — `manage-metrics` § `cmd_enrich` is storage/aggregation only ("manage-metrics never
  parses a transcript itself") and persists whatever bucket the runtime returns. New per-phase
  counters need a new bucket key, not new plumbing.
- OBSERVED — the citations-only return shape already exists and works:
  `phase-3-outline/standards/component-analysis-contract.md` § Output Format mandates a "Single
  TOON summary — no other text output. All analysis detail is persisted to assessments.jsonl."
  **D4 generalizes this; it invents nothing.**
- OBSERVED — that same contract's § Critical Rules #4 forbids ad-hoc discovery — the dispatch
  analyses "only the files provided in the input list". **It is a scorer, not an explorer:**
  whoever built the list explored, in their own context.
- HYPOTHESIS — **no repo-internal exploration dispatch exists at all**; every read-only dispatch
  either receives its file list from the caller or ingests external content, so exploration
  happens inline and is billed to the dispatching context. Confirm/refute by enumerating the
  `Task:` dispatch sites in `phase-3-outline/SKILL.md` and
  `standards/outline-workflow-detail.md` against their declared return blocks
  (verify-at-outline). If refuted, D4's target set changes.
- HYPOTHESIS — transcript entries carry `tool_use` content items bearing the tool name, adjacent
  to the `tool_result` items already handled. Confirm/refute at `claude_runtime.py`
  § `_compute_normalized_tokens` against a live transcript (verify-at-outline). **Load-bearing:**
  if the name is not recoverable, per-tool attribution is impossible and D1 falls back to a
  turn-and-payload-size measure, or the plan is refuted.
- HYPOTHESIS — `checks/token-economics.md` § "Measurement caveat" is stale prose: it calls
  recording the full usage view "a known `manage-metrics` improvement" while `cmd_enrich` already
  persists all four usage fields plus `billing_weighted_total`. Confirm/refute at `audit.py`
  § `cross_token_economics` — does the check *read* them? (verify-at-outline). If confirmed this
  is D3 scope and a theme instance: a caveat that outlived its defect still steers every
  adjudication that reads it.
- HYPOTHESIS — `opencode_runtime.py` § `metrics_normalized_tokens` is unsupported for this data,
  so the counters degrade to a *declared absence*, never a zero (verify-at-outline).
- Verify-first clause: D1 is a gate. It settles the two load-bearing hypotheses against the
  implementing source before any counter is designed; refutation loops back to re-scope rather
  than proceeding on a substituted assumption. No D4 contract change is authored before D1–D3
  produce a baseline.

## Deliverables

### D1 — GATE: settle the seam, define the classification (mutates nothing)

Confirm the two load-bearing hypotheses. Define and record the exploration/work classification —
which tool calls count as locating code versus changing it, and how a work call with a large
result is handled. **Derive the tool set from the population, never a hand-written list** (the
recurring "named sample read as an enumeration" archetype). Pick the denominator: turn share,
payload-byte share, token share, or more than one — they are different numbers and one will not
carry both readings.

### D2 — exploration share is measured per phase

Emit the D1 counters from `_compute_normalized_tokens` into each phase bucket; persist through
`cmd_enrich` into `metrics.toon` and the `generate` rendering. `runtime_base.py`, the `opencode`
path, and `platform-runtime/standards/contract.md` § `metrics normalized-tokens` move in
lock-step — an undeclared bucket key is the doc-contract-divergence archetype.

### D3 — the share is adjudicable, and the stale caveat is reconciled

A new cross-plan check (`checks/exploration-share.md` + its `audit.py` computation) with
corpus-relative thresholds and a degenerate-corpus guard, in the house style of `token-economics`
— **no hard-coded cut-points**. Amend `architecture-lookup-ratio.md` so "Lever bypassed" names
this check instead of "or the transcripts", and reconcile the `token-economics` caveat to what D1
found. Register the check in the SKILL list and `audit.py`'s dispatch roster, population-derived
per `test/_shared/_dispatch_roster.py`.

### D4 — generalize the citations-only return shape, scored against the baseline

Lift the `component-analysis-contract.md` shape into a standard for read-only dispatches — paths
plus line ranges plus a one-line reason returned, detail to a sidecar store, no prose into the
caller's context — and apply it where D1's enumeration says it pays. Ship a conformance detector
over read-only dispatch return blocks, population-derived over the dispatch roster. Acceptance is
the D1–D3 number moving on a measured plan, or a recorded finding that it did not. Out of scope:
`execution-context-reader`'s untrusted-ingestion boundary, which is a different boundary.

### D5 — tests

(a) A transcript fixture with known exploration/work calls yields the expected counters — the
assertion that fails today. (b) The `opencode` path reports the counters absent, not zero.
(c) The new check's flag stays suppressed on a degenerate corpus. (d) A newly-added read-only
dispatch is picked up by the D4 detector without editing it.

## Expected Surface

- OBSERVED: `.../platform-runtime/scripts/claude_runtime.py` — `_compute_normalized_tokens`,
  `_USAGE_FOUR_FIELDS`
- OBSERVED: `.../platform-runtime/scripts/runtime_base.py` — `metrics_normalized_tokens`
- OBSERVED: `.../platform-runtime/scripts/opencode_runtime.py` — `metrics_normalized_tokens`
- OBSERVED: `.../platform-runtime/standards/contract.md` — § `metrics normalized-tokens`
- OBSERVED: `.../manage-metrics/scripts/manage-metrics.py` — `cmd_enrich`, `generate`
- OBSERVED: `.claude/skills/audit-archived-plan-retrospectives/scripts/audit.py` —
  `cross_token_economics`, `cross_architecture_lookup_ratio`, new sibling + roster row
- OBSERVED: `.../checks/architecture-lookup-ratio.md`, `checks/token-economics.md`, new
  `checks/exploration-share.md`, and the SKILL check list
- OBSERVED: `.../phase-3-outline/standards/component-analysis-contract.md` — § Output Format
  (the precedent D4 lifts; likely gains a pointer, not a rewrite)
- HYPOTHESIS: the read-only dispatch sites D4 applies to — set by D1's enumeration
  (verify-at-outline)
- HYPOTHESIS: `test/` mirrors for each of the above (verify-at-outline)

**Disjointness:** `platform-runtime` + `manage-metrics` + the project-local auditor.

## Dependencies and Sequencing

- Depends on: none.
- Overlaps with: **PLAN-77** — same archetype (an instrument honest per item while the aggregate
  question stays unanswerable), different quantity and seam, but presumed to touch
  `platform-runtime`. ⚠ Do not run concurrently without re-checking that surface; consider whether
  PLAN-77's D2 roll-up and this plan's D3 check should share a reporting shape.
  **PLAN-76 / PLAN-84** touch the same `audit.py` + `checks/` surface — sequence, do not pair.
- Adjacent to: **PLAN-89** (measurement framing, different subject) and **PLAN-64** (dispatch
  observability, finalize-scoped and manifest-shaped) — both stay untouched.

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and
edits NO file under `.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message
— the orchestrator owns every other ledger write — and reports its outcome through its PR and its
inbox message. See `persona-marshall-orchestrator/standards/orchestration-model.md`
§ Ledger Write-Boundary.
