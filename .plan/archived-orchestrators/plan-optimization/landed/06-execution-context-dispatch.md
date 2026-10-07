# 06 — Execution-Context: per-dispatch cost optimization

**Status: LANDED REFERENCE — do not execute from this doc.** Its live content has been extracted into
self-contained plan documents under [`../plans/`](../plans/): §1 → `plan-4-find-triage.md`
(verify-first — the provider/generator surfaces were decomposed by PRs #834/#837 after this doc was
written); §2's doc-trim candidates → `plan-8-context-trim.md`; §2's planning-phase COALESCING is
**RETIRED** (superseded by `plan-5-inline-init.md` + lane pruning + the plan-1 invariant — rationale
in `../HANDOVER.md` §"Retired directions"; §2a below is the analysis that led there); **§3 SHIPPED
(PR #812)**. The execution-context *cost* findings from the token analysis
([`03-synthesis-optimal-path.md`](../03-synthesis-optimal-path.md)) plus the open follow-up from the
execution-context refactor (#364). Independent of `04` (lane selection) and `05` (single improvements) —
this plan addresses the **structural per-dispatch floor** that `04`'s worked examples (§9) attribute the
correctly-deep plans' residual cost to, and which no lane/recipe/effort knob touches. The related
*reliability* bug — the execute-envelope-loop defeat — is a discrete ship-now fix and lives in
[`05`](05-single-improvements.md) §3, not here.

Background: the execution-context refactor (#364) replaced per-role agents with the generic
`execution-context-{level}` dispatcher. Two cost optimizations and one measurement gap remain.

## 1. OPTIMIZATION — consolidate the finalize find/triage flow (file-to-ledger → one triage)

**Observation.** Several finalize steps repeat the same shape — *find, then triage* — each in its own
dispatch that reloads triage + domain context: `sonar-roundtrip`, `automated-review` (PR comments),
`self-review`, `security-audit`, plus build/lint/test findings. Each pays the per-dispatch floor (§2) to
triage its own findings in isolation.

**Idea.** Split **find** from **triage**: every find-source files its findings to the shared ledger
(`manage-findings`, the unified JSONL store that already exists) and **defers judgment**; then **one**
triage dispatch loads the full ledger + the relevant `ext-triage-{domain}` skills (grouped **by domain**,
not by producer) and triages everything in one context. The find-source contract below makes the find
stage mostly deterministic script.

**Find-source contract (two classes).** Each find-source implements a common contract —
*`fetch`/`surface` → file findings to the `manage-findings` ledger (domain-tagged; untrusted free-text
under the `raw_input.*` namespace); no triage* — but they split by **how the findings arise**:

- **Fetchers — pure script, zero LLM, on the *provider contract*.** Review/issue retrieval belongs on
  the **existing provider contract** (`tools-integration-ci` for the GitHub/GitLab SCM/CI providers,
  `workflow-integration-sonar` for sonar) — not a new abstraction. Formalize two script verbs on it:
  **`fetch_findings → ledger`** (files findings with untrusted free-text under `raw_input.*`,
  domain-tagged, no triage) and
  **`post_responses(triaged) → provider`** (pushes dispositions back — PR replies, sonar resolutions —
  *after* the consolidated triage). **Triage leaves the provider**: today `workflow-integration-github`
  bundles fetch + triage + respond; the split keeps the two deterministic I/O verbs on the provider and
  pulls judgment out to the consolidated step. The find loop iterates configured providers'
  `fetch_findings`: *wait for `ci-complete`, then loop every provider, filing findings (`raw_input.*`)* —
  one script step, no per-provider dispatch. (`build` / `lint` / `test` findings are **not** provider-fetched —
  they self-file to the ledger during the build run — so they join the same consolidated triage but have
  no respond side.)
- **Generators — LLM, but find-only.** The findings must be *reasoned into existence*: `security-audit`
  (analyses the code) and `self-review`'s cognitive pass (beyond its deterministic surfacer, which is
  itself a script that files candidates). These still need an LLM dispatch to *produce* findings, but
  they too **file to the ledger and defer triage** — they no longer triage in their own context.

So the whole finalize finding flow becomes: **1 script** (the provider fetch loop) + **the few generator
find-dispatches** (find-only) + **1 script** (ingestion: `raw_input.*` → cleaned top-level fields) + **1 LLM pass**
(validity-for-candidates + triage over the ledger, by domain) + **1 script** (the provider respond loop
— post dispositions back) — replacing today's N find-and-triage dispatches. The fetch/respond sections
carry zero LLM cost; the only LLM work is the irreducible generators and the single consolidated
validity/triage pass.

**Why it works / reuses existing infra.** The substrate already exists — `manage-findings` is the
unified ledger every producer already files to, and triage already flows through `ext-triage-{domain}`
(the CLAUDE.md hard rule). This is an **orchestration change, not new infrastructure**: separate find
from triage and **fan-in** the triage. The win is N producer-triage contexts → (cheap finds) + 1
triage; and because triage knowledge is **per-domain**, multiple producers in the same domain (sonar +
PR + security on a Java change all → `ext-triage-java`) collapse to one load instead of three.

**Caveats to settle in the plan.**
- **Self-contained records via a `raw_input.*` quarantine namespace** (resolves the re-fetch risk *and*
  keeps the untrusted boundary — the `untrusted-ingestion` contract applied to the ledger). Every
  untrusted free-text field a producer captures goes under a **`raw_input.{field}`** node
  (`raw_input.description`, `raw_input.message`, `raw_input.body`, …), each under a **configurable
  per-field size cap** (`finding_raw_input_max_bytes`, default **64 KiB / 65536 B**); trusted provider
  metadata (rule / severity / location) stays top-level. A single deterministic **ingestion step** runs
  the `untrusted-ingestion` `validate_struct` boundary over **every `raw_input.*` field** in one batched
  pass, validates/cleans each, and **promotes the cleaned value to its proper top-level field name**
  (`raw_input.description` → `description`). The containment invariant is then **structural**: a field
  under `raw_input.*` is by-definition un-ingested, and a top-level field is clean by construction (it
  only arrives there via ingestion). **Triage reads top-level fields only, never `raw_input.*`** (a
  plugin-doctor guard enforces it). This also **closes a real gap** — including for sonar/PR, which today
  reach triage *without* passing the ingestion boundary (the contract names PR/comment/sonar bodies as
  in-scope surfaces, but the current finalize triage consumes them directly); the provider's typed
  structure only makes the `execution-context-reader`'s semantic *extraction* skippable (the record is
  already structured), never the deterministic *validation*. Result: the find stage stays dead-cheap
  (producers just dump `raw_input.*`, no per-producer validation dispatch), the ingestion is one pass,
  and triage is self-contained + trusted. The per-field cap bounds ledger bloat, ingestion cost, and
  prompt-injection blast radius; the triage prompt still treats the promoted free-text fields as
  delimited untrusted data. The **64 KiB default is corpus-grounded**: across 399 PR-comment findings the
  largest free-text field runs p50 ≈ 2 KB, p99 ≈ 21 KB, max ≈ 68 KB (all other finding classes p99 ≤
  ~3.5 KB), so 64 KiB covers p99 ~3× and clips only the single ~68 KB outlier (truncate with a
  `[truncated]` marker). Operators can raise it.
- **Validity stage** — the `ext-point-verify` validity stage (before triage) folds into the
  find→ledger step (validate on file), so triage sees only valid findings.
- **Loop-back** — `automated-review`'s fix→re-review loop runs *after* the consolidated triage decides
  dispositions; the consolidation changes *where* triage happens, not the loop-back itself.
- **Mixed domains** — the single triage context loads every `ext-triage-{domain}` the ledger needs;
  still one context vs. one-per-producer, but the saving shrinks as domain-count rises (it never
  inverts — domains ≤ producers).

**Surface.** phase-6-finalize orchestration (split find / triage / respond); the **provider contract**
(`tools-integration-ci`, `workflow-integration-github`/`-gitlab`, `workflow-integration-sonar`) gains
the `fetch_findings → ledger` + `post_responses(triaged) → provider` verbs, with triage removed from it;
`manage-findings` ledger schema gains the `raw_input.*` quarantine namespace (per-field, size-capped,
untrusted); a deterministic ingestion step (`untrusted-ingestion` `validate_struct`, batched) validates
each `raw_input.{field}` and promotes the cleaned value to its top-level field name; the
triage-reads-top-level-only (never `raw_input.*`) invariant (plugin-doctor guard);
`ext-triage-{domain}` (triage, exists); the generator steps (`security-audit`, `self-review`)
restructured to file-then-defer-triage; `build`/`lint`/`test` self-file (no respond); `ext-point-verify`
validity on file.

**Independence.** Reuses existing ledger + triage extension points; no dependency on `04`/`05`. Composes
with `05` §3's envelope-loop fix (both reduce dispatch count) and §2 (both reduce per-dispatch context).
The **validate-on-fetch
hardening** (routing PR/sonar free-text through `validate_struct` before triage) is a **security fix in
its own right** — it closes a current prompt-injection surface and could land ahead of the full
consolidation.

## 2. OPTIMIZATION — per-dispatch fixed context cost

**Problem.** Every execution-context dispatch re-reads large SKILL/workflow docs into context each turn
— the per-phase `cache_read` figures (12.7M in refine, 28M in outline, 228M+ in execute/finalize) are
the plan-marshall skill/workflow docs being re-read on every turn of every dispatched agent. This
per-dispatch floor is the root of the ~1.0M-token plan floor (no plan landed under it) and a major
driver of the 36.8% finalize share. **No lane/recipe/effort knob addresses it** — `04` right-sizes
*which* dispatches run; this is the cost *of each dispatch*.

**Direction (refine in the plan).** Lean the per-dispatch context:
- load only the workflow doc a dispatch needs, not the full SKILL bodies;
- trim the largest workflow docs (`phase-6-finalize/SKILL.md` ~1000 lines, `branch-cleanup.md` ~880,
  `execution.md` ~625) and push detail behind progressive-disclosure standards;
- review what `persona-plan-marshall-agent` and the dispatcher load by default on every dispatch;
- **coalesce the pre-worktree planning phases into one context.** init → refine → outline → plan
  run on the *same tree* (worktree materialization is deferred to phase-5 Step 2.5; every phase-2-4
  dispatch carries `WORKTREE: .`), so no boundary forces the per-phase split — the real boundaries are
  **planning (1–4) | execute (5) | finalize (6)**. Running the surviving planning phases in one context
  loads the shared context once and carries the request/refine/outline understanding forward (a
  continuity win, not just cost). This is the same principle as `05` §3's envelope-loop fix (do more
  per context), applied to planning. See §2a below — **two of the three planning routes already ship
  this**; the open gap is the deep lane, and the design constraints in §2a are binding.

**Surface.** the `execution-context` dispatcher (what it loads per dispatch); the large SKILL/workflow
docs; `persona-plan-marshall-agent` default loading.

### 2a. Planning-phase coalescing — current state on main + binding design constraints (verified 2026-07-05)

**What already ships** (`plan-marshall/workflow/planning.md`, `Action: init`):

| Route | Dispatch topology for phases 1–4 | Status |
|-------|----------------------------------|--------|
| **Recipe-routed shortcut** (`auto_route_recipe=true` + init persisted `recipe_key`) | init dispatch, then refine/outline run **inline in the orchestrator's own context** — zero further planning dispatches; execution-context is reserved for phase-5 only (planning.md "Inline early-phase path", ~lines 95–127) | shipped |
| **Light lane** (`planning_lane=light`) | init dispatch, then **ONE collapsed envelope** loading `phase-3-outline/workflow/light-lane.md` (refine-no-loop + Simple-outline + deliverable-derivation folded), with the DQ3 escalation ratchet evaluated in-context; on `escalate_to_deep` the orchestrator re-dispatches the deep pipeline (planning.md ~lines 281–319) | shipped |
| **Deep lane** | init + refine + outline + plan as **four separate execution-context dispatches**, plus conditional sibling q-gate dispatches | **the open gap — this is what P7 coalesces** |

The corpus makes the gap matter: **all 58 corpus plans ran `lane=deep`** (see
[`01-token-master-table.md`](../01-token-master-table.md)), so the shipped shortcuts almost never fire —
the deep lane is where the per-phase dispatch floor is actually paid. P7 is therefore an *extension of
two shipped patterns to the deep lane*, not a green-field mechanism — do not rebuild what light-lane.md
and the inline early-phase path already prove.

**Binding design constraints the coalescing must resolve** (all verified against the current tree):

1. **Operator-prompt escalation (the dialogue-fix collision).** The phases-1–4 window contains the
   pipeline's interactive surface: the init posture/recipe prompts (orchestrator-owned once the
   dialogue-fix plan lands), phase-2-refine's Step 11 confidence-loop clarification (FU-A/P5), and
   outline user-feedback rounds. A dispatched leaf cannot fire `AskUserQuestion`, and the harness
   cannot resume a returned agent — so every escalation from a coalesced leaf costs a **full
   re-dispatch of the whole coalesced context**, which can erase the amortization win on interactive
   plans. Two coherent shapes: **(a) run the surviving planning phases inline in the orchestrator**
   (the recipe-shortcut path already does exactly this; prompts are natively reachable; zero dispatch
   floor — at the cost of main-context growth and per-phase model/effort pinning), or **(b) one
   coalesced leaf + a checkpoint/continuation contract** (leaf returns a prompt-required signal with a
   step checkpoint; orchestrator asks; re-dispatch resumes from the checkpoint with answers baked in).
   Decide (a) vs (b) — or (a) for light-interaction plans and (b) as fallback — in the P7 outline;
   FU-A/P5's refine-loop redesign should anticipate whichever shape is chosen.
2. **Q-gate independence.** The outline/plan q-gates stay **independent sibling dispatches** (the
   adversarial check must not be the producer judging itself) — already the shipped topology: the
   orchestrator dispatches q-gate-validation as a sibling top-level Task because `Task` is unavailable
   inside an execution-context leaf.
3. **Contract-assertion checkpoints.** The orchestrator today runs post-init and post-refine
   main-checkout cleanliness / return-shape assertions **between** dispatches (the rogue-implementation
   guards, `feedback_phase2_refine_never_implements` class). Coalescing removes those intermediate
   observation points; the design must either move the assertions into the coalesced unit's internal
   step boundaries (self-assert + fail-fast return) or accept later detection — decide explicitly,
   don't lose the guards silently.
4. **Per-phase metrics attribution.** Phase boundaries are recorded by the orchestrator at dispatch
   boundaries (fused `phase-boundary` calls from each dispatch's `<usage>`). One coalesced dispatch
   yields one usage blob spanning 2-refine→4-plan — exactly the light-lane precedent, which already
   smears phases 2–4 into one measurement. Reconcile with `manage-metrics`' six-phase model (the
   `partial`/`unrecorded_phases` semantics #812 just hardened): either the leaf self-reports per-phase
   splits, or the coalesced unit is declared a first-class recording granularity. Don't regress the
   measurement that P1/P4/P7 savings are quantified with.
5. **Lane-awareness.** Coalesce whichever phases survive `04`'s lane pruning, not a fixed 1–4 (already
   stated above; the light-lane escalation ratchet shows the pattern for mid-unit lane changes).

**Relationship to the operator-stated invariant (now HANDOVER §2, "Target dispatch topology"):** the floor every plan designs to is
**one execution-context per core phase** (adversarial validators as the only sibling dispatches;
mid-phase operator input batched into at most one answer-laden re-dispatch) — `05` §3 restores it for
5-execute and `05` §1 for 3-outline. The coalescing here is the *stronger* form (phases 2–4 sharing
ONE context), built on top of that floor, not a substitute for it.

**Leverage, honestly stated:** planning is 35.9% of corpus tokens, but coalescing saves only the
per-dispatch *fixed context reload* (~3 planning dispatches eliminated, plus continuity), not the phase
work — and outline's cost is dominated by re-dispatch *iteration* (q-gate/user-feedback rounds), which
`05` §1 attacks, not this. Still lower-leverage than `05` §3 and §1 — run P7 last, measured.

## 3. ENABLER — dispatch-cost measurement (Group-2, open from #364)

**Problem.** The execution-context refactor's remaining open follow-up is **Group-2 dispatch-cost
measurement** — there is no per-*dispatch* token attribution today (metrics capture per-*phase*
`cache_read`, not per-dispatch). Without it, §1/§2 can't be quantified and `05` §3's envelope-loop fix
can't be validated.

**Change.** Instrument the dispatch boundary to attribute per-dispatch context tokens, so before/after
deltas for `05` §3 (dispatch count), §1 (triage contexts collapsed), and §2 (per-dispatch size) are
measurable. The `execution_log` already records per-step `total_tokens`/`tool_uses`/`duration_ms`;
extend it (or a sibling) with the per-dispatch context-load attribution.

**Independence.** Pure instrumentation; enables `05` §3 + §1/§2 but ships independently.

## Relationship to the other plans

- The execute-envelope-loop fix is an execution-context dispatch concern but a discrete ship-now
  reliability fix — it lives in [`05`](05-single-improvements.md) §3 with the other single improvements,
  not here.
- `04` §9's correctly-deep examples (#8–9) attribute their residual ~3% / structural floor to
  "envelope-loop defeat, per-dispatch context" — `05` §3 closes the first, **this plan closes the
  rest**; `04` only decides which dispatches to run, not their per-dispatch cost.
- `05` §4 (self-consistent finder) and §5 (anti-staleness merge) stay in `05` — they are finalize-flow
  concerns, not execution-context.

## `marshal.json`, concepts & documentation (required)

- **`marshal.json`** — seed every config knob this plan adds: `finding_raw_input_max_bytes` (§1, default
  64 KiB / 65536), and any other knob an improvement introduces (e.g. a per-dispatch context-budget or
  doc-loading mode).
- **`doc/user/configuration.adoc`** — every new/changed config knob MUST be documented here
  (`finding_raw_input_max_bytes` + any other).
- **Concept / standards docs — add or adapt** for the structural changes (not just the knobs):
  - `manage-findings` ledger-schema doc — the `raw_input.*` quarantine namespace, the per-field size cap,
    and the deterministic ingestion step that promotes cleaned fields to top-level (§1);
  - `untrusted-ingestion` contract — its application to the ledger (`raw_input.{field}` →
    `validate_struct` → promoted top-level field; the triage-reads-top-level-only invariant) (§1);
  - `phase-6-finalize` SKILL — the split find / one-triage flow (§1);
  - the `execution-context` dispatcher + `persona-plan-marshall-agent` — per-dispatch loading changes
    (§2); the `task_complete` envelope-loop contract is `05` §3;
  - `ref-workflow-architecture` — the dispatch / finalize-flow diagrams it describes.
