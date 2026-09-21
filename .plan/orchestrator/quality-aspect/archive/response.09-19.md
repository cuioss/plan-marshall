# Response to summary.09-19.md — cross-machine reconciliation

Produced by the `truthful-signals` orchestrator (this checkout) in response to
`.plan/orchestrator/truthful-signals/archive/transfer/summary.09-19.md`
(18 topic clusters, PLAN-01–PLAN-18 minus PLAN-16, plus 2 "Owned elsewhere"
clusters — ~170 individual bullets).

## Method and confidence (read before acting on this)

This is a **cluster-level** reconciliation against this checkout's live ledger
(truthful-signals' own 221-row queue, all 6 active sibling epics, and the one
archived sibling `test-suite-quality`), not an exhaustive bullet-by-bullet
audit — doing that for ~170 bullets against ~400+ tracked plan rows was out of
scope for one pass. Per this project's own Verify-First discipline, every
verdict below is tagged:

- **OBSERVED** — confirmed against a merged commit/PR, an exact title match,
  or a documented skill/verb that implements exactly the described mechanism.
- **HYPOTHESIS** — thematic/title similarity only; plausible but unverified.
  Treat as a lead, not a settled fact — spot-check before skipping.

⛔ Silence on a bullet is **not** a checked "not covered" — it means the title
scan found no candidate, which is weaker than a verified negative.

## A. Clusters already landed or actively owned here — do not duplicate

| Cluster | Verdict | Local evidence |
|---|---|---|
| **PLAN-01 / PLAN-11** — transcript-less target policy, session-id on transcript-less dispatch | OBSERVED, shipped | PR #1530 `fix(finalize): degrade session identity on transcript-less targets` — exact match to both bullets |
| **PLAN-11** — commit-existence validation for completion anchors | OBSERVED, shipped | PR #1525 `Make finalize anchors unfabricable and the mutex reclaimable` |
| **PLAN-02** — merge-mutex reclamation past hold budget | OBSERVED, shipped | same PR #1525 |
| **PLAN-02** — change-ledger row per build | OBSERVED, shipped | PLAN-TRUTH-026 (#1075), PLAN-TRUTH-027 "build-ledger-is-the-build-time-oracle" (#1224) |
| **PLAN-02** — pollution guard for concurrent merge.lock writes | HYPOTHESIS, likely covered | `manage-locks` (TOCTOU-safe read-modify-write + plan-liveness core) already unifies this exact class of coordination primitive |
| **PLAN-02** — branch-cleanup removing worktree metadata with the worktree | tracked, not yet landed | PLAN-TRUTH-164 "worktree-remove-leaves-use-worktree-and-worktree-path-stale" — **staged here (parked)**, not shipped. Don't duplicate; check its spec before starting equivalent work elsewhere. |
| **PLAN-03** — billing-cost measurement before bounding re-fire | tracked, not yet landed | PLAN-TRUTH-160 "the-billing-cost-column-undercounts-output..." — **staged here** |
| **PLAN-03** — unmeasured channels rendered unmeasured / population-published signal-gate counts (PLAN-04) | OBSERVED, governing principle | This is ADR-019 ("an audit separates what it could not evaluate from what it evaluated and found wanting"), the load-bearing rule across this whole epic's corpus (`unevaluated`/`indeterminate` vocabulary used pervasively, e.g. PLAN-TRUTH-082, -117, -153) |
| **PLAN-04** — verdict_inputs surface for step currency; finalize-step-contract ordering | OBSERVED, shipped (multi-part) | PLAN-TRUTH-084 (#1309), PLAN-TRUTH-095 (#1339), PLAN-TRUTH-148 (#1488) |
| **PLAN-04** — symmetric-pair comparison within one edit | OBSERVED | `pm-plugin-development:ext-self-review-plan-marshall` names "symmetric-pair functions, flag-guard pairs" as a detector class verbatim |
| **PLAN-04** — absent-verdict admission closed in phase-5 | OBSERVED, is this machinery | This is the Re-Grounding Verdict Field admission table itself (`persona-plan-orchestrator/standards/orchestration-model.md` § Re-Grounding Verdict Field / `corpus verdicts`) |
| **PLAN-04** — context-load flags at every call site / forwarding at record-dispatch-boundary | OBSERVED, shipped | PLAN-CIS-030 (#1086), PLAN-CIS-042 (#1154) — **owned by sibling `code-intelligence-substrate`** |
| **PLAN-05, PLAN-06 (review-yield-a/b, in full)** | **belongs to sibling `review-apparatus`** | 78-plan active epic dedicated to exactly this domain. Rate-window/quota-wait: PLAN-PR-025B (#1433, "arm the refusal recovery that has never run"). Participation credit shape: PLAN-PR-046 (#1477), PLAN-PR-042 (#1410). Refusal recognition + rate window: PLAN-PR-069 (staged). Do not open new work here — route any *new* finding to `review-apparatus`'s inbox, not this epic's. |
| **PLAN-07 footprint-surface (whole cluster)** | OBSERVED, is this machinery | `manage-references`'s realized-footprint capture, upstream-base diff, and three-way symmetric-difference reconciliation is this exact surface. The "shared containment rule for twin comparisons" and "classified unevaluated state" are literally the `corpus declaration-currency` containment rule and ADR-019 vocabulary documented in `plan-orchestrator/SKILL.md` |
| **PLAN-08 baseline-reconcile (git-prose / merge-tree parsing, drift recovery)** | OBSERVED, shipped | PLAN-TRUTH-054 "baseline-reconcile-anchors-on-a-stale-phase-1-sha-and-one-verdict-auto-merges" (#1206) — same cluster name, already landed |
| **PLAN-08 / PLAN-17** — dedup on canonical component spelling, lesson retirement fail-open | OBSERVED, shipped | PLAN-TRUTH-044 "the-lesson-retirement-path-fails-open-in-three-independent-places" (#1113) |
| **PLAN-08** — orchestration context forwarded from source id | OBSERVED, is this machinery | `orchestrator inbox detect` verb classifies a plan's `source_id` exactly this way |
| **PLAN-09 outline-sweep (whole cluster)** | OBSERVED, shipped | PLAN-CIS-047 "outline-derived-set-closure-integrity" (near-exact name match), PLAN-CIS-015 "outline-plan-scope-derivation-integrity", PLAN-TRUTH-089 "planning-lane-change-type-scope-and-execution-manifest" (#1399), PLAN-TRUTH-036 (#1188) |
| **PLAN-10 plan-execute-mechanics (most of it)** | OBSERVED, shipped/staged | Freshness: PLAN-TRUTH-128 (#1425, shipped) + PLAN-TRUTH-158 (staged, parked). Scope-creep guard: PLAN-TRUTH-138→superseded into PLAN-TRUTH-145 (staged). Frozen-manifest staleness: PLAN-CIS-038 (#1236, shipped), PLAN-TRUTH-132→PLAN-TRUTH-145. "OUTCOME before voluntary checkpoint yield": PLAN-CIS-061 "voluntary-checkpoint-is-a-stall" (staged, parked) — same term "voluntary checkpoint" |
| **PLAN-12 worktree-paths (most of it)** | OBSERVED, shipped/staged | PLAN-TRUTH-114 "the-move-back-guard-resolves-through-the-tree-it-protects" (#1361). Argparse/notation rejection classification: PLAN-TRUTH-101 (#1386), PLAN-CIS-032 (#1127), PR #1507 `fix(plan-marshall): make argparse rejections name their own fix`; PLAN-TRUTH-162 remains **staged here** for the residual "canonical hint not uniform" gap |
| **PLAN-13 self-review-detectors (whole cluster)** | **belongs to sibling `code-intelligence-substrate` WS-05** | Detector/auditor integrity is that workstream's charter: PLAN-CIS-016 "auditor-detector-integrity" (shipped), PLAN-CIS-021 "self-review-cannot-see-a-duplicate-claimable-key" (shipped, matches "duplicate-claimable keys" verbatim), PLAN-CIS-043/044/045 (all shipped) |
| **PLAN-14 chat-signal-halt** | OBSERVED, shipped/staged | PLAN-CIS-013 "chat-signal-provenance-filter-under-inclusive" (#1271, shipped). Wait-state narration: PLAN-TRUTH-169 "a-timeout-verdict-describes-the-wait-not-the-work-and-time-budgets-are-undeclared" — **staged here** |
| **PLAN-15 config-guards** | HYPOTHESIS, likely covered | Non-object-root / malformed-document rejection is the same defensive pattern documented for `status.json` in `orchestrator.py queue --add-row` (`invalid_status_document`, `invalid_plans`); `manage-config` follows the same convention |
| **PLAN-17 finalize-self-review (whole cluster, high confidence)** | OBSERVED, shipped (multi-part) | This is the epic's core workstream. Infra-noise CI-timeout classification: PLAN-TRUTH-078 "a-timeout-is-not-a-red-test-and-a-kill-is-not-a-timeout" (#1193). Metrics re-close on loop-back: PLAN-TRUTH-055 (#1129). Finalize-step-contract / self-review-decides-its-own-close: PLAN-TRUTH-148 (#1488). Self-review whole-passage re-review: PLAN-CIS-031 "self-review-resweeps-full-surface-every-round" (#1126). Archive-plan completion receipt: `manage-status`'s documented delete-plan lesson carry-back (vetoes deletion when a carried lesson did not land) |
| **PLAN-18 cost-mergequeue** | OBSERVED, shipped (split across two epics) | Re-fire after already-green: PLAN-TRUTH-030 (#1194, here). Merge-queue enqueue proving PR membership: PLAN-PR-009 "merge-queue-enqueue-does-not-take" (#1087, **sibling `review-apparatus`**) |

## B. Should stay owned by the originating machine

| Cluster | Why no local match | Additional info offered |
|---|---|---|
| **PLAN-01** — analyze-logs build_count reconciliation; batched fragment registration; fragment paths against a single plan root | No candidate found in either the local title corpus or recent commits | None beyond: per-task `changed_files` persistence (same cluster) has a *routed but not yet promoted* thread here — `PLAN-LH2-19 manage-tasks-surface-gap`, staged in the `lessons-handling-26-08-26-01` epic's queue and drained into `truthful-signals`'s inbox per that epic's own resume anchor. If your machine's version of this is more advanced, it should win; otherwise flag the overlap risk to us before either side starts. |
| **PLAN-02** — coverage-report exit-1-with-empty-stderr diagnosis; down-daemon failover for concurrent suites; generator interpreter resolution; named rejected flag in capture-footprint failures | No exact local match | Live, *unresolved* local pain point in the same subsystem worth cross-checking before you build: `PLAN-PR-044` (review-apparatus, finalize-blocked at the push barrier) is currently gated on `freshness: build_scope_narrow`, with `module-tests` confirmed NOT the fix — only full `verify` covers compile+lint+test. If your "accepted evidence named in build_scope_narrow refusal" bullet solves this, it's high-value to land wherever it's further along. |
| **PLAN-03** — delete-to-one-home re-search verification; convergent resolutions applied as stated; mirrored-site admission with scope | No local match | — |
| **PLAN-04** — fallback tool for unsweepable lint roots | No local match | — |
| **PLAN-08** — documented-set contract test for termination-cause block | No local match | — |
| **PLAN-10** — absolute-path tasks-file staging; overlap-aware self-absorb at first phase-5 entry; deliverable-scoped chain-tail predicate | No local match | — |
| **PLAN-11** — site-grained exclusions; B7 orchestrator-tier-handoff carve-out; triage route to rejected; live-config bounds vs documented defaults | Weak/no title match | `triage route to rejected` and `ext-triage-*` infrastructure exist here generically; if your version adds a *new* disposition value, check it doesn't collide with the closed triage vocabulary before landing. |
| **PLAN-11** — bot STATUS bodies kept out of the pending barrier | Belongs to review-apparatus domain but no exact local plan title match | Route to `review-apparatus`'s inbox rather than us — it owns the pending-barrier machinery (PLAN-PR-* WS-04) |
| **PLAN-15** — mode lists derived from authoritative tuple | Weak match only | — |
| **PLAN-17** — fallback/stacked-child rebase before refusal re-read; emitting-notation bucketing in lessons-capture gate; Simplify reconciling outline-prose decisions | No strong local match | — |
| **PLAN-18** — auto-fix churn in realized-footprint accounting; derivation comments verified against code | Partial infra exists (see below), no shipped plan closes it | The quality-gate auto-fix-in-place convention is already documented project policy (CLAUDE.md: "Quality-gate auto-fixes in place — never `git restore` a dirty file to undo it"), but nothing here yet folds that churn into the realized-footprint *accounting*. If you have working code for this it's a genuine gap here too. |

## C. "Owned elsewhere" section of your summary — epistemic correction needed

Your summary names two epics we do not have active here, under **"Owned
elsewhere."** Important asymmetry for your orchestrator to know:

### `test-quality` / PLAN-180 test-fidelity-rules

We have **no active epic by this name.** We have an epic `test-suite-quality`
that is **CLOSED** (10 plans, all shipped, archived at
`.plan/archived-orchestrators/test-suite-quality/`) — our own standing
instruction is **do not reopen it.** Your machine's `test-quality` epic having
reached `PLAN-180` means its corpus has grown far beyond ours under the same
name-root; treat the two as **unrelated epics that happen to share a
name-prefix**, not the same ledger continuing elsewhere.

That said, one bullet is **OBSERVED as already landing here**, just not under
any orchestrator epic — as ad-hoc PR work: "behavior-cluster splits" matches
the `slice-040` test-refactor commit series merged this week (`refactor(test):
slice-040 {automatic-review, phase-6-finalize, manage-ci-artifacts,
tools-integration-ci, workflow-integration-{git,github,gitlab,sonar}} behaviour
clusters (#1514,#1515,#1517–1522,#1526)`). If your `PLAN-180` deliverable
covers the same ground, check for duplication.

"pytest basetemp out of agent scratch" is a known, *unticketed* local pain
point (a prior session found 75,917 temp files / 783 MB of `pytest-basetemp`
residue inflating a verify run from 1560s to 4120s) — no local plan owns the
fix; your version is welcome to lead.

The rest of this cluster (CLI-accepted hoisted argv, live module object in
`TestFindSkillsRoot`, seam-pinned test mirrors, yield-honest fixture
docstrings, single registration for split modules) has no local match at all
— keep it on your side.

### `process-compliance` PLAN-08 process-contracts

**No epic by this name exists here, active or archived** — confirmed by a
directory search of both the live and archived orchestrator stores. Several
individual bullets do map onto shipped/existing local infrastructure, offered
as context rather than as duplication risk:

- "findings persisted to the finding store" — OBSERVED, PLAN-TRUTH-086
  "unchecked-finding-persist-loses-the-finding" shipped (#1038); `manage-findings`
  is the unified JSONL store this describes.
- "plan-local manifest snapshots" — `manage-execution-manifest` already exists
  as the owning skill.
- "re-review timeouts within leaf budgets" — likely belongs with
  `review-apparatus`'s PLAN-PR-069 (staged, "refusal-recognition-and-the-rate-window").
- "outline counts re-derived" — duplicate of the PLAN-09 outline-sweep bullet,
  already covered by PLAN-CIS-047 / PLAN-TRUTH-089 above.

Since no epic here owns this cluster as a whole, recommend your machine either
keeps orchestrating it standalone, or — if you want it merged into our
ledger — send it through the normal inbox/transfer channel naming a specific
sibling epic rather than a bundle called "process-compliance," which has no
counterpart on this side.

## What this document is not

This is a one-time cross-check, not a live sync channel. It was produced by
reading this checkout's ledger state as of 2026-09-19; it does not account for
anything that has landed on either machine since. Re-run the comparison before
relying on a "not found" verdict above to still hold.
