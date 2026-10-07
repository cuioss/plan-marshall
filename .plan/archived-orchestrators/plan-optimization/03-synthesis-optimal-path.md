# Token-Usage Synthesis — Optimal Path Through plan-marshall

Scope: all **8 archived + 49 dormated** plan-marshall plans + the **TokenSheriff source plan**
(`2026-06-29-doc-validation-capability-split`, PR cuioss/TokenSheriff#524) that seeded lesson
`2026-06-30-08-001`. Token figures are `input+output` generation volume (the audit script's
`total_tokens`); they exclude `cache_read`/`cache_creation`, which are 10-100x larger and the
dominant *billed* cost — every per-phase number below is therefore a **lower bound** on real
traffic. Companion data: [`01-token-master-table.md`](01-token-master-table.md),
[`02-token-aggregates.md`](02-token-aggregates.md).

## Data-confidence floor (read first)

Seven plans have **partial metrics** (≥1 phase's tokens unrecorded → the Total is a floor, not a
measurement): `reactivate-architecture-refresh-step` (archived), and `ci-pr-safe-merge`,
`dead-extension-points-audit-fix`, `dynamic-finalize-step-discovery`,
`phase-6-finalize-strict-sync-ordering`, `security-audit-finalize-step`, `terminal-title-build-busy`
(dormated). Their token totals **under-count** the missing phase (usually 6-finalize, which is the
single most expensive phase). The `input-integrity` check reports **0 blind plans** in either corpus,
so no plan is fully un-measurable — but no "all efficient" claim is made over the seven floored
plans. All ratio statistics below are computed over the **51 fully-recorded plans with known LOC**.

## The headline: the editing work is the *smallest* of the three macro-buckets

Per-phase corpus token share (where every generation token actually goes):

| Macro-bucket | Share | Detail |
|--------------|-------|--------|
| **Planning** (init+refine+outline+plan) | **35.9%** | init 2.9% · refine 5.9% · outline 16.3% · plan 10.8% |
| **Execute** (the actual edits) | **27.4%** | the only phase that mutates the deliverable |
| **Finalize** (review/ceremony/retrospective) | **36.8%** | the largest single bucket |

**Almost three-quarters of every plan's token spend is framework overhead around the edit, not the
edit.** This is the structural fact the two lesson data points already pointed at, now confirmed
across 51 plans: finalize ≥ planning > execute. The deep lane is sized for large multi-module code
changes; the per-dispatch floor it imposes does not shrink when the change is small.

## The fixed-overhead floor is real and large

- **No plan in the corpus landed for under ~1.0M tokens.** Cheapest fully-recorded plan:
  `fix-escalate-ask-guard-ordering` — **20 LOC, 1,034,469 tokens** (51,723 tok/LOC).
- Six plans of **≤50 LOC each cost ≥1.0M tokens**; the extreme is `fix-automated-review-merge-anyway`
  at **11 LOC / 1,041,870 tokens = 94,715 tok/LOC**.
- Corpus **tokens-per-LOC: median 3,504, range 418 → 94,715 (a 226x spread)** — and the spread tracks
  LOC almost perfectly inversely. A change is "expensive per line" precisely when it is *small*,
  because it pays the same ~1.0M framework floor over fewer lines. See the LOC-bucket table in
  `02-token-aggregates.md`: ≤50 LOC plans run ~50,000 tok/LOC; >2000 LOC plans run ~500 tok/LOC.

**Implication:** lane right-sizing helps the misrouted-trivial case, but the deep lane *itself* needs
a lower per-dispatch floor — the dominant cost on a correctly-deep plan is re-loading large
SKILL/workflow docs into each subagent turn (the lesson's `cache_read` 12M–280M-per-phase evidence),
not the work.

## Q: Was the refine necessary?

**Corpus fact: all 58 plans reached ≥95% confidence (median 98.5%, min 95.0) — and refine ran on
every one,** consuming a median 5.3% (max 20.6%) of plan tokens. The stored confidence is the
*post*-refine value, so this alone doesn't prove the *input* was already high — but combined with the
per-run evidence in lesson `2026-06-30-08-001` it is a strong signal:

- **doc-validation (TS-src):** confidence came back **99% on iteration 1** — the input was a complete
  spec. Refine (102,606 tok) was **near-pure confirmation**; its one catch (stale seed paths) folds
  trivially into an outline premise check. **Clearest skip.**
- **integrate-sonar (arch):** refine **earned its keep** — its clarifications widened Bug B's scope
  (fix all 3 keyed-map functions, not 1) and chose the tool-layer credentials fix. Single round,
  genuine value.

**Verdict:** refine is **conditionally valuable, not universally**. It pays when the input is
genuinely ambiguous (sonar); it is overhead when the input is a complete, high-confidence spec
(doc-validation). A plan-start confidence/spec-completeness probe should let refine **early-exit at
one round** (or skip to an outline premise-check) when the input is already ≥ threshold. Because
every plan in this corpus already cleared 95%, the refine loop is doing confirm-work far more often
than clarify-work.

## Q: Which steps did not add value? Were all steps necessary?

Synthesizing the two per-step value audits in lesson `2026-06-30-08-001` with the corpus signals
(`token-economics` anti-pattern flags, `sequence-and-build-minimality`, `task-count-efficiency`):

| Step | Value verdict | Evidence |
|------|---------------|----------|
| 1-init | **Keep — necessary, cheap.** | 2.9% corpus share; ~55–75k flat. |
| 2-refine | **Conditional — skip/early-exit on high-confidence complete specs.** | See above; 5.9% share but confirm-work on ≥95%-confidence inputs. |
| 3-outline (incl. q-gate scope validator) | **Keep the validator — highest-value check in the pipeline.** | Caught the Javadoc-link scope gap (doc-val) — the one check that changed the outcome. But `outline_heavy` flagged on 18+ plans (16.3% corpus share, the biggest planning phase); cost is inflated by re-dispatch iteration, not the core validation. |
| 4-plan (task decomposition) | **Net-negative on linear plans.** | `task-count-efficiency` shows **0 over-decomposition outliers** (counts are fine) — the problem is *defect introduction*: it minted the wrong verify command (doc-val, lesson `…00-002`) and modelled a config-wiring deliverable as verification-only (sonar) → `triage_required` recovery. Collapse to a single linear task list for linear changes. |
| 5-execute | **Necessary work, heavily inflated.** | 27.4% share. Inflated by the **envelope-batching defeat** (see below), not by the edits. |
| 6 / create-pr | **Keep — necessary.** | The merged PR is the goal. |
| 6 / ci-verify-as-agent | **Near-zero value — make deterministic.** | ~101k tokens to assert "checks green" that the precondition resolver already established. Should be a script check, not a dispatched agent. |
| 6 / automated-review | **Keep — highest-value finalize step.** | Found 3 stale Javadoc anchors (doc-val) and a **real secret-key leak** (sonar → lesson `2026-06-29-23-001`). |
| 6 / sonar-roundtrip | **Skip-conditional on no-code-logic change.** | ~113k for a guaranteed-empty result on a doc/Javadoc change. |
| 6 / self-review ×3 | **Adversarial — keeps value, but iterates serially.** | Found 2 real doc-drift gaps (sonar). |
| 6 / security-audit | **Finder good; auto-apply caused rework.** | Applied a `PLUGIN_CACHE_PATH` hardening inconsistent with its own accepted sibling finding → broke 2 tests → revert + a wasted ~11-min `verify` (sonar run). |
| 6 / plan-retrospective (12–13 aspects) | **Traceability value; heaviest single finalize agent (~153k).** | — |
| 6 / lessons-housekeeping | **Near-zero on narrow plans — short-circuit.** | sonar run: classified 49 lessons, retained all, subsumed none. Should short-circuit when the plan footprint touches no lesson's component. |
| 6 / deploy-target, sync-plugin-cache, record-metrics, archive | **Keep — necessary, cheap (meta-project derived state).** | — |

**The generalizable rule (corpus-confirmed):** the steps that add value are the **adversarial /
validation** ones — outline scope-validator, automated-review, self-review, security-audit-as-finder;
they *find* things. The steps that add little are the **transform / confirm** ones applied to inputs
that don't need them — refine on a complete spec, task-decomposition of a linear change,
ci-verify/sonar/lessons-housekeeping where the output is structurally guaranteed empty. **Right-size
by skipping transform/confirm steps when their input is already high-confidence or their output is
structurally empty; always keep the adversarial validators.**

## Structural cost drivers no lane/recipe/effort knob touches

These dominate on *correctly*-deep plans and are the real optimization frontier:

1. **Execute envelope-batching defeat (highest-leverage, fixable).** phase-4-plan bin-packs tasks
   into one envelope so phase-5 loads context once and loops. Instead the execute leaf returns the
   bare `task_complete` after the *first* task on every dispatch (`task_complete_returned_verbatim`
   drift), so the orchestrator **re-dispatches per task** — sonar's 7-task single envelope became ~9
   dispatches, each reloading persona + execute-task + domain skills. This alone plausibly accounts
   for the bulk of the inflated execute spend. `sequence-and-build-minimality` corroborates with
   `phase_reentry(5-execute)` on **every** archived plan.
2. **Per-dispatch fixed context cost.** Each subagent re-reads 600–1000-line workflow docs
   (`phase-6-finalize/SKILL.md` ~1000 lines, `branch-cleanup.md` ~880, `execution.md` ~625). This is
   the ~1.0M floor's root and the reason finalize is 36.8% of tokens for the meta-project (plugin-doctor
   + deploy-target + sync-cache + 3 retrospective-class steps on top of the standard set).
3. **Build / wall-time waste (`sequence-and-build-minimality`).** 10 heavy builds (>400s) across the 8
   archived plans, `arch_over_resolution` (arch-gate did **46 architecture lookups for 2 builds**),
   and pervasive `phase_reentry`. Wall-time is further dominated by **idle** — CI waits and overnight
   gaps (the lesson's 1h41m idle of 4h wall; corpus wall outliers of 75–77h are overnight idle, not
   work). Wall-time is a poor efficiency proxy; tokens and tokens/LOC are the real ones.
4. **Avoidable rework** — security-audit self-inconsistent auto-apply (sonar), and **merge-staleness
   rebases** (main advances during the CI-wait window → up-to-date branch-protection bounces the merge
   → extra full ~11-min CI cycles). The early-baseline-rebase step does not close this; the vulnerable
   window is the CI wait, not plan start.
5. **Token-efficiency is regressing.** `token-efficiency-trend` over the 8 latest (archived) plans:
   tokens/phase rose **306,492 → 415,806 (+36%)**. The floor is drifting up, not down.

## The optimal path (produces the identical merged outcomes for a fraction of the tokens)

For a **bounded/localized/mechanical** change (rename/move, find-replace, single-file edit, no
cross-module behavioral delta — the doc-validation archetype):

> `init (minimal)` → **skip refine** (one premise check given ≥95% confidence) → `outline` **with
> complete inbound+outbound+all-link-class enumeration up front** (eliminates the re-dispatch rounds)
> → **collapse 4-plan** to a single linear task list (no envelope bin-packing; no wrong-verify-command
> defect) → `execute` **in ONE envelope** → finalize with a **scripted CI-green check** instead of a
> ci-verify agent, **keep automated-review**, **skip sonar** for no-code-logic, then merge.

For a **correctly-deep** change (the integrate-sonar archetype — the floor is structural, not a
routing mistake):

> `init` → `refine` (1 round, early-exit) → `outline + q-gate` (keep validators) → `plan` **giving
> every deliverable a real implementation task** (no verification-only deliverable → no
> `triage_required` recovery) → **`execute` in ONE envelope** (fix the leaf loop / force-batch
> same-`envelope_id` tasks → ~9 dispatches collapse to ~2) → finalize keeping the adversarial finders
> (self-review, security-audit-as-*finder*, automated-review) but with **security-audit checking
> self-consistency before applying**, **lessons-housekeeping short-circuited** when the footprint
> touches no lesson component, and a **merge-queue that holds main steady across the CI wait**.

Both paths **retain every step that found a real defect** and remove the transform/confirm steps and
the reliability bugs. Order-of-magnitude: the mechanical path lands the same PR for **well under a
third** of the tokens; the deep path **plausibly halves** the spend.

## Priority-ordered recommendations

1. **Fix the execute envelope loop** (`task_complete_returned_verbatim`) — single highest-leverage
   change; collapses ~9 dispatches to ~2 on multi-task plans. *(Reliability bug, not a sizing knob.)*
2. **Make ci-verify a deterministic script**, not a dispatched agent (~100k/plan saved).
3. **Skip-conditional sonar-roundtrip and short-circuit lessons-housekeeping** when the footprint has
   no code-logic delta / touches no lesson component (~110k + ~100k/plan on narrow plans).
4. **Refine early-exit / spec-completeness probe** at init — collapse refine to a premise check when
   confidence ≥ threshold.
5. **Lower the per-dispatch context floor** — leaner workflow-doc loading per subagent (attacks the
   ~1.0M floor and the 36.8% finalize share directly).
6. **Self-consistent audits + a merge-queue** to kill the two rework classes (security-audit revert,
   staleness rebases).
7. **Collapse 4-plan for linear changes** to a single task list (removes the recurring task-gen
   defect; no over-decomposition exists, so nothing is lost).
