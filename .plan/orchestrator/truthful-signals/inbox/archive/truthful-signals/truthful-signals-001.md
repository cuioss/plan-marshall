envelope_version=1
sender_type=orchestrator
sender_id=truthful-signals
epic=truthful-signals
kind=finding
created=2026-07-28T13:27:29Z

# FINDING: exploration cost is unmeasured, and the one check that names it says so in prose

Operator-originated (2026-07-28), from an external-source analysis (Microsoft *FastContext*,
arXiv 2606.14066 — since **withdrawn**, repo and weights deleted; the paper's *method* is the
input here, none of its code or weights). Carries a ready-to-stage plan spec below.

**Proposed queue id: PLAN-98** (next free after PLAN-97 — the orchestrator owns final numbering
and queue position). Spec path on staging:
`plans/PLAN-98-exploration-share-is-unmeasured.md`.

**Theme fit — confident-signal-hides-a-caveat.** `architecture-lookup-ratio` reports a lookup
ratio confidently and then, in prose, tells its reader that the reading that matters ("the lever
was bypassed") is one the script **cannot** distinguish. The caveat is real, honest, and
un-actionable: it hands the adjudicator a manual transcript cross-read. This plan turns that
caveat into a measured number.

---

# PLAN-98: Exploration Cost Is Unmeasured, So The Citations-Only Return Contract Is Unfalsifiable

epic: truthful-signals
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> **Measurement-first by construction:** D1–D3 mutate no return contract. D4 may not land
> a contract change that the D1–D3 baseline cannot score.

## Objective

We assert a structured-navigation lever ("structured queries first", `token-management.adoc` §4)
and we count how often the `architecture` script is called — but we have never measured what
exploration actually *costs*: the share of tool turns and of tokens spent locating code versus
changing it. The one check that reaches for that question,
`checks/architecture-lookup-ratio.md`, states in its own interpretation guide that the script
cannot distinguish "no navigation needed" from "lever bypassed" and defers to a manual
transcript read. Make exploration share a measured per-phase number sourced from the transcript
we already walk, surface it as a retrospective check, and only then define the citations-only
return contract for read-only dispatches — with the baseline as its acceptance test rather than
a plausibility argument.

## Claim Labels

- OBSERVED — `.claude/skills/audit-archived-plan-retrospectives/checks/architecture-lookup-ratio.md`
  § "How the orchestrator interprets the rows": the `build_dominated_lookup` flag is "a **prompt,
  not a verdict**"; reading 2 ("Lever bypassed") requires cross-reading `global-log-analysis` rows
  "or the transcripts". The script's inputs are stated exactly: per plan it reads only
  `logs/script-execution.log` and tallies `architecture {sub}` calls — "No other input is
  consulted." **It counts the lever's use; it never observes the behaviour the lever displaces.**
- OBSERVED — `checks/token-economics.md` measures token *share per phase* and explicitly derives
  every number from `metrics.toon::total_tokens`. Nothing in the check, or in any sibling check,
  attributes tokens to what they were spent *on*. Exploration share is absent from the whole
  check set (22 checks under `checks/`).
- OBSERVED — the attribution seam already exists.
  `platform-runtime/scripts/claude_runtime.py` § `_compute_normalized_tokens` walks the session
  transcript line by line, and already iterates `message.content` items branching on
  `item.get("type") == "tool_result"` and `== "text"`. Classifying tool calls and sizing their
  results is an extension of a loop that is already there — not a new transcript walker.
- OBSERVED — `manage-metrics` § `cmd_enrich` is storage/aggregation only ("manage-metrics never
  parses a transcript itself") and persists whatever per-phase bucket the runtime returns,
  including `input_tokens`, `output_tokens`, `cache_read_input_tokens`,
  `cache_creation_input_tokens`, `billing_weighted_total`, and the `subagent_*` attribution.
  **New per-phase counters need no new plumbing** — they need a new key in the runtime's bucket.
- OBSERVED — a citations-only return contract already exists in this repo and works.
  `phase-3-outline/standards/component-analysis-contract.md` § Output Format mandates a "Single
  TOON summary — no other text output. All analysis detail is persisted to assessments.jsonl",
  and § Critical Rules #1 restates it. **That is the shape D4 generalizes** — it is precedent,
  not invention.
- OBSERVED — that same contract's § Critical Rules #4 forbids ad-hoc discovery: the dispatch
  analyses "only the files provided in the input list". **The dispatch is a scorer, not an
  explorer.** Whoever built the list did the exploring, in their own context.
- OBSERVED — `agents/execution-context-reader.md` § Output returns
  `status` / `display_detail` / `schema` / `candidate`. It is the *untrusted-external* ingestion
  reader (tool surface `WebSearch, WebFetch, Read, Grep`), not a repo-internal explorer, and its
  contract is bounded by `untrusted-ingestion:validate_struct`. **D4 must not widen it** — a
  repo-exploration contract and an untrusted-ingestion contract are different boundaries.
- HYPOTHESIS — **there is no repo-internal exploration dispatch at all**: every read-only dispatch
  either receives its file list from the caller or ingests external content, so repository
  exploration happens inline in the dispatching context and is billed to it. Confirm/refute by
  enumerating the `Task:` dispatch sites in `phase-3-outline/SKILL.md` and
  `phase-3-outline/standards/outline-workflow-detail.md` against their declared return blocks
  (verify-at-outline). **If refuted, D4's target set changes and D1 must re-scope.**
- HYPOTHESIS — transcript entries carry `tool_use` content items bearing the tool name, adjacent
  to the `tool_result` items the walker already handles. Confirm/refute at
  `claude_runtime.py` § `_compute_normalized_tokens` against a live transcript
  (verify-at-outline). **This is the plan's load-bearing assumption**: if the name is not
  recoverable, per-tool attribution is impossible and D1 must fall back to a
  turn-and-payload-size measure without tool identity, or the plan is refuted outright.
- HYPOTHESIS — `checks/token-economics.md` § "Measurement caveat" is **stale prose**: it states
  that `total_tokens` excludes cache fields and that "Recording the full usage view
  (`cache_read` + `cache_creation`) is a known `manage-metrics` improvement", while `cmd_enrich`
  already persists all four fields plus `billing_weighted_total`. Confirm/refute at
  `audit.py` § `cross_token_economics` — does the check *read* the enriched fields?
  (verify-at-outline). **This is itself a theme instance** and, if confirmed, is D3 scope: a
  caveat that outlived its defect still steers every adjudication that reads it.
- HYPOTHESIS — `opencode_runtime.py` § `metrics_normalized_tokens` is unsupported / no-op for
  this data, so the new counters degrade to absent rather than wrong on that target
  (verify-at-outline). The no-op path must stay a *declared* absence, never a zero.
- Verify-first clause: D1 is a **gate**. It settles the two HYPOTHESES marked load-bearing (the
  `tool_use` name, and whether an exploration dispatch exists) against the implementing source
  before any counter is designed. Refutation of either loops back to re-scope — it does not
  proceed on a substituted assumption. **No D4 contract change is authored before D1–D3 produce a
  baseline number**; a return contract justified by argument rather than by measurement is the
  exact failure this plan exists to stop repeating.

## Deliverables

### D1 — GATE: settle the seam, define the classification (mutates no contract)

Confirm the two load-bearing HYPOTHESES above. Then define, and record, the exploration/work
classification: which tool calls count as exploration (repository location — read, glob-match,
text-search, path discovery) versus work (edit, write, build, script call), and how a call whose
result is large but whose intent is work is handled. **Derive the tool set from the population,
never from a hand-written list** — the recurring "a named sample read as an enumeration" archetype
(a reviewer's 3 named call sites against a real population of 14) applies directly here.
D1 also decides the denominator: turn share, payload-byte share, token share, or all three
(the source method reports 56.2% of turns and 46.5% of tokens as *different* numbers — one
denominator will not carry both readings).

### D2 — exploration share is measured per phase

Extend `_compute_normalized_tokens` to emit the D1 counters into each phase bucket, and persist
them through `cmd_enrich` into `metrics.toon` and the `generate` rendering. Runtime-layer parity:
`runtime_base.py` § `metrics_normalized_tokens`, the `opencode_runtime` path, and
`platform-runtime/standards/contract.md` § `metrics normalized-tokens` all move together — a new
bucket key that the contract doc does not declare is the doc-contract-divergence archetype.

### D3 — the share is adjudicable, and the stale caveat is reconciled

A new cross-plan retrospective check (`checks/exploration-share.md` + its `audit.py` computation)
reporting per-plan and corpus exploration share with corpus-relative thresholds and a
degenerate-corpus guard, matching the house style of `token-economics` / `architecture-lookup-ratio`
(**no hard-coded cut-points**). Amend `architecture-lookup-ratio.md` so its "Lever bypassed"
reading names this check as the deterministic cross-read instead of "or the transcripts", and
reconcile the `token-economics` measurement caveat to whatever D1 found true of it. **Register the
new check in the SKILL's check list and `audit.py`'s dispatch roster — population-derived, per
`test/_shared/_dispatch_roster.py`.**

### D4 — the citations-only return contract, scored against the baseline

Author the return-contract standard for read-only dispatches, generalizing the
`component-analysis-contract.md` precedent: the return carries file paths plus line ranges plus a
one-line reason, and detail goes to a sidecar store — never prose into the caller's context. Apply
it where D1's surface enumeration says it pays. Ship a conformance detector over read-only dispatch
return blocks, **population-derived over the dispatch roster, not a curated list**. Acceptance is
the D1–D3 number moving on a measured plan, or an explicit recorded finding that it did not — a
contract that cannot be scored is not landed. Explicitly out of scope: any change to
`execution-context-reader`'s untrusted-ingestion boundary.

### D5 — tests

(a) A transcript fixture with known exploration/work tool calls yields the expected counters —
the assertion that fails against today's walker. (b) The `opencode` path reports the counters as
*absent*, not as zero. (c) The new check's flag stays suppressed on a degenerate corpus (uniform
distribution flags nobody). (d) The D4 conformance detector's population is derived, and a test
pins that a newly-added read-only dispatch is picked up without editing the detector.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/claude_runtime.py`
  — `_compute_normalized_tokens`, `_USAGE_FOUR_FIELDS`
- OBSERVED: `.../platform-runtime/scripts/runtime_base.py` — `metrics_normalized_tokens`
- OBSERVED: `.../platform-runtime/scripts/opencode_runtime.py` — `metrics_normalized_tokens`
- OBSERVED: `.../platform-runtime/standards/contract.md` — § `metrics normalized-tokens`
- OBSERVED: `.../manage-metrics/scripts/manage-metrics.py` — `cmd_enrich`, `generate`
- OBSERVED: `.claude/skills/audit-archived-plan-retrospectives/scripts/audit.py` —
  `cross_token_economics`, `cross_architecture_lookup_ratio`; new sibling + roster row
- OBSERVED: `.claude/skills/audit-archived-plan-retrospectives/checks/architecture-lookup-ratio.md`,
  `checks/token-economics.md`, new `checks/exploration-share.md`, and the SKILL check list
- OBSERVED: `.../phase-3-outline/standards/component-analysis-contract.md` — § Output Format
  (the precedent D4 generalizes; likely gains a pointer, not a rewrite)
- HYPOTHESIS: the read-only dispatch sites D4 applies to — determined by D1's enumeration
  (verify-at-outline)
- HYPOTHESIS: `test/` mirrors for each of the above (verify-at-outline)

**Disjointness:** `platform-runtime` + `manage-metrics` + the project-local auditor.

## Dependencies and Sequencing

- Depends on: none.
- Overlaps with: **PLAN-77** — presumed to touch `platform-runtime` and is the *same archetype*
  (an instrument that is honest about each item while the aggregate question stays unanswerable),
  but a different quantity (script wall-clock vs. exploration tokens) and a different seam
  (hook/session vs. transcript walker). ⚠ **Do not run concurrently with PLAN-77 without
  re-checking the `platform-runtime` surface** — and consider whether PLAN-77's D2 roll-up and
  this plan's D3 check should share a reporting shape rather than diverge.
  **PLAN-76 / PLAN-84** touch the same auditor (`audit.py` + `checks/`) — sequence, do not pair.
- Adjacent to: **PLAN-89** (`runnable-slice-keys-on-the-floor-not-the-measurement`) — measurement
  framing, different subject; stays untouched. **PLAN-64** (finalize dispatch observability) —
  dispatch-level observability, but finalize-scoped and manifest-shaped; stays untouched.

## Notes

- The source method's headline (main-model token use down ~60% by moving repository exploration
  to a separate small model) is **not** the claim this plan adopts. We cannot train an explorer,
  and the paper's own accounting notes the work does not disappear — it moves. What transfers is
  the *measurement* (exploration is a large, separately-attributable share of agent cost) and the
  *return shape* (paths + line ranges, nothing else). Both are testable here without any weights.
- The source repository was deleted by its owner and the paper withdrawn for stated IP-approval
  reasons; community mirrors exist. **No mirrored code or weights are to be vendored or consulted
  for this plan** — the method as described is the whole input.

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and
edits NO file under `.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message
— the orchestrator owns every other ledger write — and reports its outcome through its PR and its
inbox message. See `persona-marshall-orchestrator/standards/orchestration-model.md`
§ Ledger Write-Boundary.
