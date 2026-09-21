# plan-optimization — CLOSED 2026-07-22 (close-freeze record)

> Frozen close record, prepended at close. Close freezes, never deletes — the full tree
> (`status.json`, `landings/`, `logs/`, `plans/`, and the archived roadmap below) remains the audit
> record. Landings are the authority; this is the summary.

**Outcome: 21 landings, 0 parked, 0 dropped.** WS-01…WS-10 all drained. The terminal WS-10 wave
closed this session with **PLAN-23** (#986 — marker-detector; first close of the vacuous-guards
archetype) and **PLAN-35** (#985 — build-decision made the sole build/no-build authority, retiring
four disagreeing oracles). Full per-plan record in `landings/PLAN-NN.md`; decision trail in
`logs/decision.log`.

**Legacy of the epic:** the binding **verify-before-implement** practice was born here (lesson
`2026-07-21-22-001`, filed against the orchestrator itself; promoted into `orchestration-model.md` by
PLAN-40 #981) and the **confident-signal-hides-a-caveat** flagship archetype was first characterized
here (build wrappers exit 0 on failure → exit-0 necessary-not-sufficient; PLAN-24 #963 / PLAN-32
#972).

**Carried-forward leads — NOT dropped, live in the successor `truthful-signals`:** the entire watch
set, candidate list, recurring-archetype registry, and unresolved defects were migrated to
`truthful-signals/status.json` before close. Late-surfacing leads: baseline-reconcile persists a
merge commit contrary to its no-mutation contract (lesson `2026-07-22-21-001`) → `truthful-signals`
PLAN-52; diff-scoped-sweep (`2026-07-18-05-002`); lessons-pipeline records-but-closes-nothing.

**Closing rationale:** wave complete (21/21), nothing parked, successor epic live and carrying every
open lead. Closed + self-archived to `archived-orchestrators/plan-optimization/` per #937.

---

# HISTORY — Token-Optimization Roadmap (archived full record)

**TWO ARCHIVED SNAPSHOTS.** Snapshot 1 (2026-07-12, directly below) is the complete pre-cleanup
HANDOVER, frozen when the live doc was restructured — "§7.x"/"§8 row" references resolve against
it. **Snapshot 2 (2026-07-13, appended at the very END of this file under "SNAPSHOT 2")** is the
pre-second-compaction HANDOVER, frozen after the 2026-07-12/13 burst landed (items A–D, 16, 17,
plan-7) — the detailed shipped rows for #877–#887 and the struck defect/watch rows resolve there.
**Live status, the queue, and open defects live in [`HANDOVER.md`](HANDOVER.md)** — do not
execute anything from this file. Not maintained going forward.

**Lifecycle (plan docs are handled like lesson sources):** `plans/` holds only not-yet-started
work. When a plan is created from a doc, the doc **moves into the plan's own directory** (via
`manage-files add`, then removed from `plans/`) so it travels with the plan and is **archived with
it** by the phase-6 archive step — there is no separate landed copy of plan docs. **After the plan
is archived, as the last step**, this file and `00-README.md` are updated to point at the archived
location: add the §3 Shipped row (PR number + `.plan/local/archived-plans/<date>-<plan_id>/`) and
remove the §5 queue row. Each plan doc carries the exact steps in its "Lifecycle" footer.
[`landed/`](landed/) holds ONLY the pre-roadmap design specs (04/05/06) — plan docs never go there.

Directory map: [`plans/`](plans/) = the executable queue · [`landed/`](landed/) = shipped design
specs (reference only) · `01`–`03` + `2026-06-30-08-001.md` = the token analysis this all rests on ·
[`00-README.md`](00-README.md) = index.

## 1. The effort in one paragraph

A token-usage audit of the plan-marshall corpus (lesson `2026-06-30-08-001`, 58 plans) found ~73% of
every plan's tokens are framework overhead around the edit, a hard ~1.0M-token per-plan floor, and
that the *edit* is the smallest cost bucket (planning 35.9% · execute 27.4% · finalize 36.8%). The
dominant *fixable* drains are dispatch-multiplication bugs (the execute envelope-loop defeat, q-gate
re-dispatches) and finalize's N find-and-triage dispatches — not sizing knobs. The lane feature
(shipped #811) right-sizes *which* steps run; the queue below fixes *how many contexts* the rest
costs.

## 2. Target dispatch topology (operator decision, 2026-07-05)

The design every queued plan aligns to:

- **1-init runs INLINE in the main context** (**SHIPPED #862**, plan-5) — no dispatch. Init is cheap
  script-orchestration, and six of the eight operator prompts live there; inline, they fire natively.
- **2-refine, 3-outline, 4-plan stay dispatched — exactly ONE execution-context each** (the plan-1
  invariant). Re-dispatching a core phase is a defect. Mid-phase operator input is BATCHED: the leaf
  returns all questions at once, the orchestrator asks, at most one answer-laden re-dispatch.
- **Adversarial validators (q-gates, automated-review, self-review, security-audit) are the only
  sanctioned sibling dispatches** — separation is by design.
- **Lane pruning composes on top** (shipped #811): light-lane collapsed envelope, recipe-routed
  inline path, `auto`-posture refine/plan pruning — so a high-confidence plan runs ~4 planning-side
  contexts and a routed/light one fewer still.
- **Finalize is consolidated** (plans 3–4): script ci-verify, one find loop → one ingestion → ONE
  triage pass → one respond loop.

### Success criteria (set 2026-07-07 — measure, don't narrate)

Honest baseline: pre-roadmap corpus median **1.91M** tokens/plan (surgical 1.39M, bug_fix 1.71M,
floor 1.03M). Roadmap-era runs #840/#842/#845/#846/#847/#849 (3.8/4.4/3.5/2.9/2.3/4.1M) are all
above the median; **#851 (2026-07-07) is the first AT it — 1.9M**, with two asterisks: both review
bots failed (no substantive bot review → no loop-back cost) and `plan-retrospective` was
scope-gated out (`single_module` subtraction — a shipped lane lever firing for real, ~200k
avoided). #850 followed at 3.9M — an 8-deliverable multi_module feature (deep lane correctly
chosen there), which would miss the future ≤2.5M multi_module checkpoint target. **#853
(2026-07-08) is the sharpest datapoint**: a textbook pre-diagnosed surgical fix (root cause
verified LIVE in the request itself, 3-file footprint) still cost 2.5M — deep/`auto` at 98% again,
planning 984k (40%), finalize 1.19M (48%); that is the plan-9 class at 2× its ≤1.2M target.
**plan-4 itself landed at 4.6M (#852)** — the most expensive roadmap run yet (10 deliverables; see
the scope-bloat outcome below). plan-9 followed at 3.66M (#854 — deep/`auto` correctly: a
6-deliverable feature, not the surgical class it creates), **plan-10 at 4.5M (#855)** — if counted
against the armed checkpoint it is a multi_module MISS at 1.8× (4.5M vs ≤2.5M), with the honest
mitigation that the overspend was two legitimate review loop-back cycles catching 5 real defects
(2 self-review, 3 bot incl. a fixture-green/prod-dead regex) — quality spend, not idle waste; note
both post-checkpoint runs so far are roadmap infrastructure plans, so the **clean checkpoint
datapoints are still outstanding** — the §5 row-4.9 pilot (surgical ≤1.2M) is the first one, and
plan-11's `lane-lever-effectiveness` check now measures this systematically (18/24 corpus plans
over target). **First ORDINARY post-checkpoint datapoint: #856** (2026-07-09, terminal-title
freeze + executor sticky-binding, 5-deliverable bug fix) at **3.8M — checkpoint MISS #1 of 3**
(over even the multi_module ≤2.5M target at ~1.5×; ≥2.5× if scored single_module). Two honest
qualifiers: the request was diagnosis-first ("analyze why"), so the micro-lane fit gate correctly
did NOT apply (root cause unknown at request time), and 3 of its ~11-min CI cycles were queue
traffic (#855/#858 merging concurrently). Still: deep-lane spend on a bug fix is exactly the
pattern the levers exist to cut — 2 of the 3 checkpoint datapoints remain, and the row-4.9 pilot
should be one of them. plan-11 landed at **4.50M (#857)** — roadmap infrastructure, not a
checkpoint row, but its phase split is a first-of-kind anomaly: **execute 48.3%** (corpus median
27.4%) with a lean 22.6% planning side — the `module: null` whole-tree-build fallback on a
project-local skill made phase 5 the cost center (root cause + plan-7 D1 fold in §7.12). **THE
PILOT landed (#860, 2026-07-09): 1.93M vs the ≤1.2M surgical target — checkpoint MISS #2 of 3
(1.6×)** — but a split verdict: `minimal` posture FIRED for the first time ever (operator-chosen at
the #840 dialogue; subtractions real, incl. the bot-enforcement guard correctly re-adding
automated-review), while the **light lane missed AGAIN and is now root-caused as a wiring-order
defect**: the lane router ran at init with `change_type`/`scope_estimate` UNSET and fail-safed to
deep; `recipe-match` executed 46 minutes later — the Tier-1 auto-route can never win that race
(full record §7.13; fix folded into plan-5 as a first-class requirement). **#861 (2.88M,
single_module 1.9×, §7.15) completed the triad — checkpoint DECIDED: FAILED 0/3, all three
pre-#862; see the checkpoint bullet below for the verdict + the CONFIRMED re-arm.** **plan-5 landed at
4.57M (#862)** — roadmap infrastructure, ties plan-4 as most expensive; finalize-dominant anatomy
(finalize 2.44M = 53%: two review loop-back cycles over three automated-review passes + the
doc-sweep re-validations; planning 28%, execute 18%). It shipped inline-init AND the routing-order
fix — **the light-lane wiring defect is now closed in code; plan-12's log was VOID as the proof
(its init predated #862 — parallel pair), so the FIRST live acceptance test is the next plan that
inits post-#862.** **plan-12 landed at 5.48M (#863) — NEW COST RECORD, finalize 68% (worst share
ever): 6 self-review iterations + 2 review loop-backs on a provider-symmetric mirror surface**
(§7.16; infrastructure, not a checkpoint row; steward merge-queue enable is the pending operator
action). **BREAKTHROUGH on #866 (2026-07-10, the era-stamp micro plan): re-armed checkpoint
datapoint #1 lands AT the ≤1.2M surgical target (~1.11M recorded, n=5/6)** — the first ordinary
run at target ever, with `minimal` firing (2nd time), the `surgical_bug_fix` compose rule
producing a 16-step manifest, AND the #862 routing-order fix PROVEN live (recipe-match before the
lane router). The light lane itself still hasn't fired — two residual micro-sized blockers in §8
(recipe confidence floor + no-recipe unset-signal fail-safe). (Side plan #864, 5.46M
multi_module feature, is EXCLUDED from the re-armed count — its init predated #862; §7.19.)
**Re-armed datapoint #2: #869 at 3.09M — MISS ~1.24×** (multi_module after its base_branch
scope-add; floor + S2-on-unset still pre-fix, §7.20). **Datapoint #3: #871 at 3.26M — MISS ~2.2×
(single_module ≤1.5M) → RE-ARMED CHECKPOINT DECIDED: 1/3 AT TARGET.** The decisive pattern across
the triad: **#866 ran `minimal` → 1.11M; #869/#871 ran posture `auto` (full 20-step finalizes,
1.10M/1.68M) → 3.1M/3.3M — posture engagement alone is worth ~2M/plan.** All three also ran
pre-fix-#2 (floor rejected every pre-diagnosed request; light lane STILL 0-fired) — the residual
blockers were known and their fix was in flight during the entire window, so this verdict again
condemns engagement, not design. **Operator decision pending: re-arm a THIRD time after micro-fix
#2 lands (floor + classify-before-route — the last blockers), or accept the standing conclusion
(the levers work when engaged; make `minimal`/light engagement the default for the
surgical/single-module class) and stop measuring.** Realized savings before #851 ≈ 0; what's landed is measurement,
reliability, correctness, and (with #849) the first structural cost removals (0-dispatch
ci-verify, staleness-cycle elimination). #849 also partially realized the scope-bloat fear: the
optimization plan itself cost 4.1M (outline 914k on the mutex design, finalize 1.98M on a
14-comment review loop-back). The cost case now rests on the landed #849+#852 machinery + plan-9.
Therefore:

- **Checkpoint DECIDED (2026-07-10): FAILED 0/3.** Armed post-#852; targets: surgical ≤1.2M ·
  single_module ≤1.5M · multi_module ≤2.5M. The three ordinary datapoints: **#856** 3.8M
  (multi_module, 1.5×) · **#860 pilot** 1.93M (surgical, 1.6×) · **#861** 2.88M (single_module,
  1.9×). Decisive mitigating fact: **all three ran while the light lane was structurally
  unreachable** (the pre-#862 wiring-order defect — the pilot's autopsy found it, #862 fixed it),
  and only #860 even got the `minimal` posture. So the verdict condemns the levers AS-WIRED, not
  the design. **RE-ARM CONFIRMED (operator, 2026-07-10): measure the next 3 ordinary plans
  post-#862** — same targets, now with routing-order fixed + inline init + minimal proven able to
  fire. plan-12 runs first regardless (infrastructure, auxiliary datapoint + the routing
  acceptance test); the re-armed clock starts at the next ordinary request.
- **The micro-lane is now QUEUED unconditionally as plan-9** (operator decision 2026-07-07, slot
  4.5): the fast path for the surgical class where tok/LOC is worst. It turned out to be a
  composition/calibration plan, not new infrastructure — recipe auto-route already triggers the
  inline early-phase path, and recipes already seed lane/posture. If the plan-4 checkpoint fails,
  plan-9's priority RISES (pull it before anything else); it is no longer merely plan-B.
- **Unused-lever watch:** the light lane has NEVER fired (0/58 corpus + all recent runs) and the
  `minimal` posture has never been chosen even on perfect candidates (#846). Shipped mechanisms
  with zero realized savings are calibration/behavior gaps, not wins — plan-9 D1/D3 fix exactly
  this; the now-rendering routing-decisions aspect (#845) supplies the counterfactual data. First
  counter-signal on #851: the scope-gated finalize subtraction dropped `plan-retrospective` for a
  `single_module` change — the step-composition half of the machinery does fire; the lane/posture
  half still never has (trade-off: a scope-gated retrospective also means no routing-decisions
  counterfactual for that run). **Calibration SHIPPED #854** (light-lane carve-out +
  `recipe-surgical-fix` + honest minimal recommendation). **Pilot outcome (#860): the posture half
  now WORKS** (`minimal` fired, first time ever) — **the lane half is structurally dead as wired**:
  the lane router decides at init before classification/recipe-match run, so it fail-safes deep on
  unset signals every time; no calibration can fix an ordering defect. **Fix SHIPPED #862** (plan-5
  D6: recipe evaluation before the planning-lane router) — awaiting first live proof (plan-12's
  init predated #862, VOID as a test): on the next initing plan expect `recipe-match` BEFORE the
  `planning-lane` routing line, and no `S2` firing on unset signals.
- **Scope-bloat guard:** plans keep absorbing folded lessons (correct, but compounding). If a
  plan's outline exceeds ~6 deliverables, SPLIT rather than land a 4M+ monster — the payback math
  dies if the optimization plans themselves each cost 4M. **Outcome on plan-4: VIOLATED silently**
  — 10 deliverables, 4.6M, and NO split weighing recorded anywhere in the decision log. The guard
  is roadmap prose, not machinery; for the remaining plans the operator must enforce it personally
  at the outline review gate.

### Retired directions

**"Coalesce phases 1–4 (or 2–4) into one execution-context leaf" is RETIRED** (2026-07-05). A
returned `Task` leaf cannot be resumed, so every mid-unit operator prompt would force a full
re-dispatch of the coalesced context; making that safe requires checkpoint/resume machinery, in-leaf
contract assertions, per-phase metrics splitting, and level flattening — all to save only ~1–2
context loads (~50–100k/plan) beyond what inline-init + lane pruning + the one-context-per-phase
invariant already capture. Analysis: `landed/06-execution-context-dispatch.md` §2a. Do not resurrect
without new evidence.

## 3. Shipped

| What | PR | Archived plan | Notes |
|------|----|---------------|----|
| Lane feature (04 design) | **#811** | `.plan/local/archived-plans/2026-06-30-execution-profile-lane-selection/` | posture/lane contract + six-size cost scale + lanes preview. Two landing defects, both now fixed: posture dialogue inert (fixed #840), routing-decisions aspect non-rendering (fixed #845, plan-2). |
| Reliable metrics + dispatch-cost measurement (05 §6 + 06 §3) | **#812** | `.plan/local/archived-plans/2026-07-01-implement-reliable-per-phase-metrics/` | per-phase snapshot, first-class `partial`/`unrecorded_phases`, per-dispatch context-load attribution. **Measurement is LIVE** — quantify plan-1/4/8 with it. |
| Posture-dialogue fix (dialogue-fix plan) | **#840** | `.plan/local/archived-plans/2026-07-06-fix-execution-profile-posture-dialogue/` | **ALL SIX** phase-1-init prompt sites migrated to orchestrator-owned escalation envelopes (scope-expanded beyond the outline's two); reachability guard (analyze-only) + six-key cost table restored on live config + drift test + doc corrections. **Bootstrap self-signal CONFIRMED** on its own run (`execution_profile=auto` resolved, security-audit dropped, no XS/XXL ValueError). Cost flagged high: ~3.8M for a bug_fix ([BUDGET] finding). |
| Execution-loop invariant (plan-1) | **#842** | `.plan/local/archived-plans/2026-07-06-execution-loop-reliability/` | one-context-per-phase invariant: D1 phase-5 dispatch-wiring fix (`workflow:` execute-task→phase-5-execute envelope; **removed lesson `2026-06-29-17-001`**, its exact root cause), D2/D3 `q_gate_validation` knob (`off\|once\|until_clean`, default `until_clean`) + whole-outline content-hash re-run gate, D4 `outline_prompt` batched-question envelope. CodeRabbit/Gemini caught a real Q-Gate `until_clean` unchanged-and-pending exit-gate gap → fixed via loop-back TASK-8. **Pre-fix baseline captured live** (7 `task_complete_returned_verbatim` on its own phase-5 — the executor only regenerates at finalize); **after-measurement (D5) OWED on the first post-merge multi-task plan.** ~4.4M tokens (multi_module enhancement + a full review loop-back cycle). |
| Routing-decisions render + `q_gate_validation` default (plan-2) | **#845** | `.plan/local/archived-plans/2026-07-07-plan-2-routing-render/` | routing-decisions aspect now renders (SECTION_SPEC row + `should_emit` carve-out) + D2 registered⇒rendered pytest guard + generic domain-aspect fallback in `compile-report` (closes the `wrapper-tangle` silent-drop) + `q_gate_validation` default flipped `until_clean`→`once` (machinery + 8 docs/tests + live `marshal.json` override removal). **Self-review caught D1 incomplete** (adding the SECTION_SPEC row is necessary-not-sufficient — `should_emit` gates on fragment SHAPE; the D2 guard had a blind spot too) → fixed in-flight + contract-doc alignment. **D5 after-measurement DELIVERED** (this plan's own retrospective): **0 `task_complete_returned_verbatim` vs 7 pre-fix** — the execution-loop fix HELD; the 3 phase-5 `voluntary_checkpoint` yields are legitimate orchestrator-owns-long-builds yields. ~3.5M tokens (heavy finalize: self-review ×3 + retrospective; local plugin-doctor gate skipped as a Python-3.14 argparse-introspection env false-positive — CI's real gates all green). |
| Finalize-flow hardening: script ci-verify + widen merge mutex (plan-3) | **#849** | `.plan/local/archived-plans/2026-07-07-finalize-flow-hardening/` | D1 deterministic `ci_verify.py` (**proven live green, 0 dispatch/0 tokens** on its own finalize) + D2 dispatched→inline rewire (deleted `workflow/ci-verify.md`) + D3 adaptive `ci:wait` ratchet (records elapsed-at-deadline **upward** so the ceiling self-corrects) + D4 widened merge mutex (full staleness window, release at operator-waits, bounded hold) + D5 optional `use_merge_queue` complement through `tools-integration-ci` + D6 config/doc sweep. **Self-review caught+fixed a real `ci_verify.py` OSError fail-open** boundary; PR review (gemini+coderabbit) → **6 fix tasks** incl. a `classify_check` deadline-ordering fail-open bug (loop-back TASK-11–16, one full re-validation cycle). Retired lessons `2026-07-07-00-002` + `2026-06-20-18-001` (verified covered in merged code). New lesson `2026-07-07-17-001` (ci-verify fail-open classifier row ordering). ~4.1M tokens (6-finalize 39% — the review loop-back). |
| Find/triage consolidation: ledger→one-triage flow + raw_input quarantine + self-consistency gate (plan-4) | **#852** | `.plan/local/archived-plans/2026-07-08-plan-4-find-triage/` | 10 deliverables: D1 ledger core (`raw_input.{field}` quarantine + content-discriminator hash_id dedup + resolution_detail relational integrity), D2 batched `validate_struct` ingestion (triage reads top-level only), D3 two-verb provider contract (`fetch_findings`/`post_responses`, fail-loud unconfigured, tz/wildcard/pagination + CWE-178 denylist hardening), D4 consolidated find→ingest→one-triage→one-respond + disposition self-consistency gate, D5 generators find-only + self-review title correction, D6 step-ownership manifest + mark-step-done key canonicalization, D7 two plugin-doctor guards (triage-reads-top-level-only + verify-step canonicals), D8 `finding_raw_input_max_bytes` knob + dead-config sweep, D9 doc sweep, D10 lifecycle. **Self-review caught+fixed a sonar regex symmetric-pair gap; disposition self-consistency gate correctly rejected a same-run simplify revert; CodeRabbit review converged 15→2→0 over 3 loop-back rounds** (caught real byte-cap clamp bypass + sonar post_responses idempotency defects). Also folded in the uncommitted main marshal.json config sync. Retired 5 folded lessons (`2026-07-07-00-001`, `2026-06-30-21-001`, `2026-06-21-00-002`, `2026-06-25-08-001`, `2026-06-22-14-001`). ~4.6M tokens (heavy finalize: 3-round review loop-back + external-rebase reconciliation). |
| Audit-check refresh: era sentinels + roadmap-mechanics checks (plan-11) | **#857** | `.plan/local/archived-plans/2026-07-09-plan-11-audit-check-refresh/` (historical after the corpus-cut — see §3 note) | 7 deliverables in the project-local `audit-archived-plan-retrospectives` skill: D1 era model (central `CHECK_ERA` `fixed_since` table stamped on every emitted block + `retire_on_quiet_runs=3` removal-*proposal*), D2 six roadmap-affected checks re-computed against post-#849/#852/#812/#854 mechanics (call-class-aware impossible-duration, `partial`/`unrecorded_phases` markers, step-ownership `owner_drift`, era-aware track carve-out), D3 `dispatch-topology` (leaf/dispatch invariant), D4 `finalize-flow-conformance` (post-#849 ci_verify mechanics), D5 `merge-window-accounting` (#849 widened-mutex FIFO admission window), D6 `lane-lever-effectiveness` (the **armed-checkpoint measurement arm** — per-scope-class token spend vs surgical ≤1.2M / single_module ≤1.5M / multi_module ≤2.5M + recipe/light/minimal lever-engagement counts + the `surgical_overpay` cross-check coupling), D7 corpus-cut run + confirmed dormation + this bookkeeping. All four new checks CROSS-validated against the real 24-plan corpus (18 of 24 over their armed checkpoint; light-lane 0-fired, minimal-posture 0-chosen — the unused-lever gap now MEASURED). Two audit test files stay green (new-location + legacy). **Corpus-cut is this plan's closing step** (operator-confirmed dormation is orchestrator-owned). |
| Finalize-contract follow-ups: structural triage loop-back contract + post-rebase re-resolution + rate-window await (plan-10) | **#855** | `.plan/local/archived-plans/2026-07-09-plan-10-finalize-contracts/` | 5 deliverables (§4 operator opted IN): D1 `triage.md` Step 3c FIX not-done/STOP directive, D2 `triage-fix-not-done-contract` plugin-doctor analyzer (build-failing, whole-tree gate green) + test, D3 `advances_main_via_rebase` frontmatter fact on both rebase steps + post-rebase step-doc re-resolution contract in `phase-6-finalize/SKILL.md`, D4 `rate_limited` discriminator on `ci pr wait-for-comments` + test, D5 rate-window await knobs (`review_rate_window_await`/`_timeout_seconds`) + `escalate_ask{rate_window_timeout}` reusing the item-7a continuation hook. **Operator chose the mechanical option on all 3 outline design decisions** (analyzer + script discriminator + escalate-ask). **Self-review caught+fixed 2 regex-overfit defects in its OWN new code; the review bots then caught 3 more** — incl. a real production bug where D4's `^`/`re.MULTILINE` heading anchor was fixture-green but DEAD in production (`fetch_pr_comments_data` flattens newlines → the anchor could only match at offset 0) → loop-back TASK-10/11/12 (rate-limit anchor unanchored + `any()`→`all()`, prohibition-regex narrowed off bare `not`, typo). The D4 `rate_limited` discriminator fired LIVE on this plan's own automated-review (CodeRabbit was rate-limited). Retired folded lessons `2026-07-07-21-002` + `2026-07-07-21-001` (verified covered vs merged tree). New lesson `2026-07-09-14-001` (test fixtures must mirror the PRODUCTION data shape, else a boundary-anchored regex is green-in-tests/dead-in-prod). ~4.5M tokens (two legitimate finalize loop-back cycles catching 5 real defects; plan-retrospective judged it a clean well-run deep feature). |
| Inline phase-1-init + routing-order fix (plan-5) | **#862** | `.plan/local/archived-plans/2026-07-10-plan-5-inline-init/` | 6 deliverables: D1 `planning.md` Action:init executes phase-1-init INLINE in the orchestrator (six operator prompts fire natively via `AskUserQuestion`, six signal-consumption blocks deleted) at all THREE dispatch sites (Action:init + Action:lessons convert + `recipe.md` Step 2), D2 `phase-1-init/SKILL.md` restructured to inline-callable form (`implements:` marker removed → reachability rule no longer flags it structurally) + 3 live-found init defects folded (Step 8a underscore typo, Step 3a/5c pre-`status.json` ordering), D3 `manage-metrics` inline-phase recording (timestamps-only close is `recorded`, not `partial`) + regression test, D4 rogue-leaf assertions retired, D5 dead `phase-1-init` effort role removed clean-break (KNOWN_ROLES + 3 presets + `_config_defaults` + `effort-roles.md`/`effort-variants.md` + `efforts.adoc` + marshal.json), D6 complete dispatch-mechanics doc sweep (agents/call-graph/phases + planning/SKILL.md + rule-catalog cross-bundle + 3 adoc + call-graph.svg). **Routing-order fix**: recipe evaluation runs inline BEFORE the planning-lane router (the §7.13 light-lane wiring defect). Reachability analyzer keyed solely on `implements:` marker (scope-gap fix, incl. tests). **Two Q-Gate rounds caught 6 real outline/task defects** (wrong `manage-metrics.py` path, missing sweep files); **two review loop-backs** — CodeRabbit/Gemini drove TASK-9..13 (unused `path` param, stale `research` sub-key ×2, prose "all six" overstatement + `source.type` schema drift, call-graph 6→5-group heading, xref-by-name redirect). Self-review + lessons-housekeeping RETAINED lesson `2026-07-06-10-001` (residue is an uncodified general authoring rule; post-merge promotion would orphan an uncommitted main change). **Era-stamp `CHECK_ERA` (lane-lever-effectiveness + track-selection-accuracy) is an OPEN follow-up** (source change → separate PR; the plan merged without it). ~4.6M tokens (2 review loop-back cycles). |
| Micro-lane fast path for surgical fixes (plan-9) | **#854** | `.plan/local/archived-plans/2026-07-09-micro-lane/` | 6 deliverables: D1 light-lane router calibration (narrow+concrete carve-out in `evaluate_signals_pure`), D2 `recipe-surgical-fix` (`lane_seed {planning:light, profile:minimal}`, automated-review force-kept), D3 minimal-posture recommendation at init Step 8d, D4 recipe registered across the full doc-contract surface (`recipes.adoc` + `provides_recipes()` + `ext-point-recipe.md` table + `configuration.adoc`). **D5/D6 folded live**: executor-gen PYTHONPATH multi-version-shadowing fix (`collect_script_dirs` newest-version-per-bundle selection + `generate_executor` bootstrap `sys.path` guard) + pollution-aware preflight wired into the `task=` init entry path — both discovered when this plan's OWN init crashed on the stale plugin-cache shadow (`ImportError` ×29). Self-review caught+fixed 2 doc contract-drift defects; 10 review-bot comments triaged (3 inline-fixed). Filed lesson `2026-07-09-04-001` (`architecture which-module` matches `paths.sources` not `paths.tests`). Folded lesson `2026-06-29-16-001` RETAINED (D4 followed but did not codify a guard). ~3.66M tokens (deep-lane/`auto` — correctly, a 6-deliverable feature, NOT the surgical class it creates). **Pilot (`get-deliverable` verb) NOT shipped here — deferred to a separate micro-lane measurement plan** (the real efficiency proof). |
| Architecture data/doc mechanical sweep + inline-token unit fix (plan-15) | **#876** | `.plan/local/archived-plans/2026-07-12-plan-15-architecture-data-sweep/` | 6 deliverables (4 full, 2 partial): D1 architecture-refresh.md flag-order fix + narrative-test sweep (retired `2026-07-07-20-001`); D2 `skills_by_profile` refresh + warn-on-read staleness guard (retired `2026-07-07-16-001`; a Gemini review caught a real malformed-non-dict guard gap → fixed in-run, 1 loop-back); D5 `resolve_bundle_path` newest-version selection in BOTH resolvers + tests (retired `2026-07-11-15-002`); **D6 inline `total_tokens` drops `cache_read` — CONFIRMED on its own metrics (1-init row 79K comparable vs the ~11M cache-read-inflated form; the §8 unit row is struck, future plans print comparable totals natively)**. PARTIAL: D3 notation-drift (2 genuine callers fixed; metric can't reach 0 — counts plugin-doctor's own detector/catalog literals → small follow-up); D4 era stamp **MERGED UNRESOLVED (`#PLAN15-PR` literal on main, audit.py:297 — recurrence #2 of `2026-07-11-09-001`; surgical fill command prepared, doubles as the recalibrated floor's first must-match test)**. New lesson `2026-07-12-15-001` (docs-only deliverables changing a pinned call-shape break narrative-contract module-tests). **FIRST END-TO-END LIGHT-LANE RUN (n=1/1 routed+stayed light)** — but cost 2.35M grand / 2.27M phases-2–6 vs ≤1.2M: overshoot = `auto`-posture finalize ceremony (20 steps) + the loop-back's second CI wait, NOT a mis-route. Leaf-backgrounded builds recurred ×2 (build-slot contention with concurrent plan-14; orchestrator took over; [OUTCOME] coverage 3/10 → plan-7 D2 evidence). `--delete-branch` queue rejection = recurrence #5. Also OWED: lessons-housekeeping's post-merge SKILL.md promotion was REVERTED (post-merge finalize source-edits can't push under branch protection — systemic, same class as the era-stamp gap). |
| Light-lane unblock (floor + classify-before-route) + inline-init metrics (plan-13) | **#875** | `.plan/local/archived-plans/2026-07-11-plan-13-init-routing-metrics/` | 4 deliverables: D1 Tier-1 recipe floor recalibrated to the pre-diagnosed-change SHAPE signal (surgical-fix only; real #860/#866/#869/#871 request-string fixtures + #856 diagnosis-first must-not-match); D2 classify `change_type`+`scope_estimate` BEFORE the planning-lane router — new pure `scope_estimate_from_request_pure` (file-count via `_PATH_RE`, ZERO discovery) + phase-1-init Step 8a.5, killing S2-on-unset; D3 inline-init main-context tokens surfaced into `total_tokens` — **n=6/6 TOKENS confirmed** (`enrich four_field_phases_attributed: 6`; 1-init records tokens for real, no longer wall-only) + planning.md Metrics-block doc-accuracy note; D4 `CHECK_ERA` (lane-lever-effectiveness + track-selection-accuracy + metrics) stamped `#875` as a DELIVERABLE, finalize-resolved from `PR-PENDING` placeholder (lesson `2026-07-11-09-001`). **One review loop-back**: CodeRabbit nitpick (duplicated `_PATH_RE` distinct-path extraction) → TASK-9 `_distinct_paths` dedup; a D1 test (`test_is_surgical_fix_recipe_matches_identity_variants`) also caught a real narrow-prefix bug at the orchestrator-tier verify (fixed in-run — a gate HIT, honoring `2026-07-09-14-001`). Merged via the merge queue (its first real stress test — clean; `--delete-branch` flag rejected by GH merge-queue, retried without → note for plan-14). **Residual n=5/6 on Worked/Tool-Uses columns is the inherent inline-phase limit (no `<usage>` for worked-seconds), NOT the D3 token bug.** **COST CORRECTED at the #875 landing analysis (§7.26): the printed 14.1M is NOT ledger-comparable — D3's four-field sum includes `cache_read` (init row 11.16M = 11.09M cache reads); the comparable cost is ~2.95M (phases 2–6: 220k/577k/367k/446k/1,344k) — mid-pack for a 4-deliverable roadmap plan, cheaper than plan-5/plan-12.** Unit fix → plan-15 D6. This plan itself ran deep/`auto` (correct — a 4-deliverable feature); the light-lane ≤1.2M acceptance is plans 14/15 (scored on the comparable basis until plan-15 D6 lands). Retired nothing (both routing blockers were HANDOVER-§8-owned, no corpus lessons filed). |
| Merge-queue enablement as a marshall-steward provisioning capability (plan-12) | **#863** | `.plan/local/archived-plans/2026-07-10-enable-merge-queue/` | 5 deliverables (probe-driven, BOTH providers): D1 `merge_group:` CI trigger on `python-verify.yml` + structural test, D2 `ci repo merge-queue probe/enable` 3-level verbs behind the `ci` abstraction with the shared `MERGE_QUEUE_*` eligibility vocabulary + real GitLab merge-train enqueue replacing the fail-loud stub, D3 idempotent marshall-steward provisioning step (probe→ask→configure-or-refuse, provider-neutral — the D2 probe decides), D4 probe-backed `use_merge_queue` set-time validation + actionable `branch-cleanup` finalize error, D5 `configuration.adoc` both-provider fixture-vs-live posture. **Self-review needed 6 iterations** to converge on doc drift across the symmetric github/gitlab CI-provider surface (dead `--confirm` flag at 5 sites, undocumented validation, stale Page-4 count, unscoped `merge_group` regex, leaf-command-reference/SKILL-frontmatter/configuration.adoc gaps). **Two automated-review loop-backs**: CodeRabbit rate-limited round 1, full review round 2 caught a **Major** API-error-vs-`ineligible` misclassification bug in BOTH providers (fix gives `MERGE_QUEUE_UNSUPPORTED` a real producer) + 4 minor. simplify deduped the github_ops probe/enable helper. GitLab path fixture-verified, no live consumer (lesson `2026-07-09-14-001`). Merged via the NORMAL path — `use_merge_queue` stays `false`; the actual steward merge-queue provisioning on this repo is a separate operator action. Retrospective merged a recurrence into `2026-06-29-16-001` (a symmetric provider-implementation pair is a mirror surface; quantified the 43%-of-finalize doc-drift cost). ~5.5M tokens (2 review loop-backs + 6 self-review iterations). **Era-stamp `CHECK_ERA` OWED (still open): merge-window-accounting's own boundary + plan-5's owed #862 stamps — the lifecycle-footer form is structurally dead (source change → needs a separate small PR); the plan merged without it.** |

> **Corpus-cut note (plan-11, 2026-07-09).** Once plan-11's confirmed dormation runs, the
> `.plan/local/archived-plans/…` **path columns above become historical** — the dormated plans move to
> the purgeable `.plan/temp/dormated-plans/`, so the **PR number + git history are the durable
> reference**, not the archive path. The analysis docs (`01`–`03`) already snapshot the old corpus.
> The cut sweeps only plans archived BEFORE plan-11's start date (per-plan `--dormate ID … --confirmed`
> + `--dormate-global-logs`); any plan that archives while plan-11 runs (e.g. plan-10 landing in
> parallel) already carries the new mechanics' signals and is a first member of the clean post-roadmap
> corpus.

## 4. Live status (verified 2026-07-10)

- **plan-5 (inline-init + routing-order fix) SHIPPED** — PR #862, merge `32d283bb`, archived
  `.plan/local/archived-plans/2026-07-10-plan-5-inline-init/`. 6/6 deliverables: init runs inline at
  all 3 entry sites (prompts fire natively; rogue-leaf assertions retired), dead `phase-1-init`
  effort role removed clean-break, inline-phase metrics locked in + regression test, complete
  dispatch-mechanics doc sweep, reachability rule structurally clean — **and the routing-order fix
  (recipe eval BEFORE the planning-lane router), closing the §7.13 light-lane wiring defect in
  code**. Two Q-Gate rounds caught 6 real outline/task defects pre-code; two review loop-back
  cycles (CodeRabbit+Gemini, TASK-9…13) converged on the third automated-review pass. First fully
  UNATTENDED landing (all three `*_without_asking` knobs true; CI green on all 3 pushed HEADs).
  4.57M / 5h3m worked — finalize-dominant (53%). **Open follow-ups**: era stamp OWED (now plan-12
  D5 — the lifecycle-footer form proved structurally dead: source changes can't happen post-merge);
  lesson `2026-07-06-10-001` consciously RETAINED (promote-then-retire in a future related plan).
  **Acceptance test: plan-12's log was VOID (its init predated #862 — parallel pair); the first
  plan initing post-#862 is the live proof.** plan-12 has since SHIPPED (#863, §7.16) — pending
  operator action: `/marshall-steward` → Configuration → Merge Queue, then the next finalize is
  the queue's acceptance test.
- **plan-10 (finalize-contract follow-ups) SHIPPED** — PR #855, squash `f878af85`, archived
  `.plan/local/archived-plans/2026-07-09-plan-10-finalize-contracts/`. The three post-plan-4 finalize
  contract gaps are closed: the triage FIX create-task/not-done/STOP contract is now BOTH documented
  (D1 `triage.md`) and mechanically enforced (D2 build-failing `triage-fix-not-done-contract`
  analyzer, whole-tree gate green); post-rebase step-doc re-resolution is structural (D3
  `advances_main_via_rebase` fact + dispatcher contract); and the CodeRabbit rate-limit gap has a
  `rate_limited` discriminator (D4, which fired LIVE on this plan's own automated-review) plus an
  opt-in rate-window await with escalation (D5). §4 was operator-opted-IN at init, and the operator
  chose the mechanical option on all 3 outline design decisions. **The finalize loop-back machinery
  earned its keep twice:** self-review caught 2 regex-overfit defects in this plan's own new code,
  and the review bots then caught a real production bug (D4's `^`/MULTILINE anchor was fixture-green
  but dead in production because `fetch_pr_comments_data` flattens newlines) → 3 fix tasks over one
  full re-validation cycle. Retired the two folded lessons `2026-07-07-21-002` + `2026-07-07-21-001`
  (verified covered vs the merged tree); new lesson `2026-07-09-14-001` (fixtures must mirror
  production data shape). ~4.5M tokens (two legitimate loop-back cycles catching 5 real defects) —
  above the multi_module ≤2.5M checkpoint, but the overspend is defect-catching, not idle waste.
  **plan-11 corpus-cut + plan-5 are next.**
- **plan-11 (audit-check refresh) SHIPPED — PR #857** — the `audit-archived-plan-retrospectives` skill is
  refreshed: era model (`CHECK_ERA` `fixed_since` + retire-on-quiet proposals), six roadmap-affected
  checks recomputed against current mechanics, and four NEW roadmap-mechanics checks
  (`dispatch-topology`, `finalize-flow-conformance`, `merge-window-accounting`,
  `lane-lever-effectiveness`). The full sweep runs clean over the real 24-plan corpus — all 22 checks
  emit, cross-check-synthesis runs LAST with 10 couplings (the new `surgical_overpay` joins
  lane-lever `checkpoint_over` to token-economics `big_spend_tiny_footprint`). **The checkpoint
  measurement arm now has DATA:** 18 of 24 corpus plans are OVER their armed targets (surgical 2/2,
  single_module 5/5, multi_module 11/16); the light lane has still NEVER fired (0/24) and the minimal
  posture was NEVER chosen — the unused-lever gap is now measured, not asserted. Closing step: the
  corpus-cut (confirmed dormation of pre-cut plans + past-date global logs) is orchestrator-owned.
  **plan-10 SHIPPED (§3/§4); plan-5 is next in the queue.**
- **plan-9 (micro-lane) SHIPPED** — PR #854, squash `4f7ea855`, archived (§3). The surgical-fix
  fast path EXISTS: light-lane carve-out in `evaluate_signals_pure`, `recipe-surgical-fix`
  (lane_seed `{planning:light, profile:minimal}`, automated-review force-kept, Tier-1 auto-route
  at ≥0.6 keyword confidence, fit gate: single module + ≤~2 files + root-cause-and-exact-change
  present), honest minimal recommendation at init Step 8d, full doc-contract registration. D5/D6
  folded LIVE after this plan's own refine crashed on plugin-cache multi-version PYTHONPATH
  shadowing (`0.1-BETA` sorted first → ImportError; fixed `collect_script_dirs` newest-version
  selection + bootstrap `sys.path` guard + init-path pollution preflight). **The levers are
  calibrated but UNPROVEN — the pilot (§5 row 4.9) is the acceptance measurement.** ~3.66M.
  **plan-10 SHIPPED (§3/§4); plan-5 is next.**
- **plan-4 (find/triage consolidation) SHIPPED** — PR #852, squash `dabab228`, archived
  `.plan/local/archived-plans/2026-07-08-plan-4-find-triage/`. 10 deliverables: ledger raw_input
  quarantine + content-discriminator hash_id + batched `validate_struct` ingestion (triage reads
  top-level only), two-verb provider contract (`fetch_findings`/`post_responses`, fail-loud
  unconfigured, matcher + CWE-178 denylist hardening), consolidated find→ingest→one-triage→one-respond
  + disposition self-consistency gate, step-ownership manifest + mark-step-done canonicalization, two
  new plugin-doctor guards, `finding_raw_input_max_bytes` knob. **Disposition self-consistency gate
  proved itself live** (rejected a same-run simplify edit that would have reverted a test fix);
  **CodeRabbit review converged 15→2→0 over 3 loop-back rounds** (caught a real byte-cap clamp bypass +
  sonar `post_responses` idempotency defect). Also folded the uncommitted main marshal.json config sync
  (restoring the Sonar credential extras from §7.8b). Retired 5 folded lessons. ~4.6M tokens (heavy
  finalize: 3-round review loop-back + a mid-finalize external-rebase reconciliation). **plan-9 is next.**
- **plan-3 (finalize-flow hardening) SHIPPED** — PR #849, archived (§3). D1 deterministic ci-verify
  proven live (green pass-through, **0 dispatch/0 tokens** on its own finalize); D3 adaptive `ci:wait`
  ratchet; D4 widened merge mutex (the parallelism enabler — parallel finalize is now safe, so the §5
  bounded pairs may begin); D5 optional `use_merge_queue`. Self-review + PR review caught real
  ci_verify fail-open bugs (OSError boundary + `classify_check` deadline ordering) → 6 fix tasks in a
  loop-back cycle. Retired lessons `2026-07-07-00-002` + `2026-06-20-18-001`. **plan-4 is next.**
  Landing-audit addenda (2026-07-07): all four D4 hard requirements verified in the merged flow doc
  (release-at-operator-waits + FIFO re-enqueue on resume; `merge_hold_budget_seconds=3600` with
  escalation; `_fifo_front` invariant unchanged; release on EVERY abort path) and the mutex
  acquire/release fired live on its own branch-cleanup. The 6 non-retired folded lessons were
  CORRECTLY retained (per-lesson rationale in the decision log — see §7.5 outcome). Cost warts for
  the queue: `finalize-step-simplify` ran twice for 295k and produced 0 edits; self-review errored
  once and re-ran (335k total); outline hit a new high 914k (mutex design + operator dialogues + a
  Q-Gate re-entry loop closing 3 findings — verify the `once` default was respected on the next
  run). Deep-lane/`auto` at 100% confidence again (plan-9 datapoint). New lesson
  `2026-07-07-17-001` (classifier rows specific-before-catch-all, fail-closed on undetermined) —
  standing guard, corpus-owned; pointer added to plan-7's classifier rework.
- **plan-2 (routing-decisions render + q_gate_validation default) SHIPPED** — PR #845, archived (§3).
  routing-decisions aspect now renders (proven live by plan-2's own retrospective — the section
  appeared in the compiled report for the first time); `q_gate_validation` default flipped
  `until_clean`→`once`.
- **plan-1's D5 after-measurement DELIVERED by plan-2** (the first post-merge multi-task plan): plan-2's
  own phase-5 recorded **0 `task_complete_returned_verbatim`** (vs the 7-boundary pre-fix baseline) —
  3 `voluntary_checkpoint` + 1 `clean_exit_queue_empty`, `unknown_count=0`, `polling_pairs_count=0`.
  The one-context-per-phase / envelope-loop fix HELD. The measurement debt is closed.
- **plan-1 (execution-loop) SHIPPED** — PR #842, archived (§3). The one-context-per-phase invariant
  is encoded; the phase-5 dispatch-wiring defeat (lesson `2026-06-29-17-001`) is fixed and the lesson
  removed. `q_gate_validation` knob + content-hash re-run gate + `outline_prompt` batching landed. A
  review loop-back (TASK-8) fixed a real Q-Gate exit-gate gap the reviewers caught.
- **The dialogue-fix plan SHIPPED** — PR #840, squash `0ba32b2a`, archived (§3). All six init
  prompt sites are now reachable via escalation envelopes; the marshal.json cost-table crasher is
  fixed (D3); the reachability guard is live analyze-only, with **phase-2-refine Step 11 and the
  execute-task gates as the only remaining surfaced exposures** (→ plan-6).
- **The parallel review/remediation effort continues landing on main** (#813–#839, incl. #832
  targets-engine and #839 platform-runtime decomposition after the last check). Surfaces it moved:
  `github_ops.py` + `self_review.py` decomposed (#837/#834 → plan-4 is verify-first for real),
  plugin-doctor registry (#831 → rebase-sensitive for plan-2), `agents/execution-context.md`
  (#825 → plan-6 D3 re-verify), extension-point catalogue (#814). The "no two same-surface plans in
  parallel" constraint applies *against that effort's open PRs too*. #840 itself paid **two
  HEAD-advance CI cycles** (~15 min each) to this — fresh plan-3 evidence.
- **Recurring wart observed on #840's finalize** (logged, non-blocking): several dispatched finalize
  agents omitted their own mark-step-done bookkeeping and the orchestrator completed it — check
  lesson coverage before plan-3/plan-4 rework that surface.

## 5. The ordered queue — one document, one command

Each doc is self-contained. **Concurrency schedule (decided 2026-07-07):**

1. **plan-3 SOLO** — it is the parallelism enabler (the widened mutex makes parallel finalize safe)
   AND it modifies the finalize machinery every sibling's own finalize runs through; never run
   anything beside it.
2. **plan-4 ∥ plan-9** — disjoint surfaces (findings/providers/finalize orchestration vs
   recipes/init routing); shared: `configuration.adoc` (different sections) and — since plan-4
   gained the step-ownership contract (2026-07-07) — `manage-execution-manifest` (plan-4 adds an
   ownership field to step declarations; plan-9 touches lane composition). Both additive, expected
   rebase-clean; whichever finalizes second re-validates through the widened mutex anyway.
3. **plan-5 ∥ plan-7** — plan-5 requires plan-9 landed (same init surface); plan-7 is disjoint.
4. **plan-6** — sequential after plan-7 (both edit `execute-task/SKILL.md`) and after plan-4
   (both append to the plugin-doctor `_rule_registry.py`).
5. **plan-8 SOLO, last** — it trims the docs plans 3/4 rewrite.

Hard cap: **2 concurrent plans**, and parallel pairs only AFTER plan-3 lands. **Override
2026-07-10 (operator): the 4-plan MICRO-FIX burst (safe-merge preflight ∥ light-lane blockers ∥
inline-init metrics ∥ compose order) runs 4-wide** — micro-sized, pairwise disjoint EXCEPT
#2∥#3 sharing `planning.md`/phase-1-init sections (expected rebase-clean; #855's post-rebase
re-resolution covers the second finisher); the now-required merge queue serializes the 4 landings
at the platform (its first stress test — expect zero manual rebase cycles; report otherwise).
The 2-cap stays the norm for ordinary/deep plans. Parallelism buys
wall-time; TOTAL tokens are ~the same either way. The real trade-offs: (a) the burn RATE doubles,
so a rolling rate cap (5h/weekly window) can be exhausted mid-flight and throttle both runs where
serial would have spread the spend across refreshes; (b) the second finisher pays one extra
re-validation cycle on the rebased tree that a serial successor wouldn't; (c) serial preserves the
option to fold plan-A's landing lessons into plan-B before B spends — every landing this week has
amended the queue. **Operator decision (2026-07-07): run the queue SERIALLY** — the reshaping
argument (c) decides it; the pairings above stay sanctioned as an option if wall-time ever becomes
the binding constraint. Serial order: plan-4 (SHIPPED #852) → plan-9 (SHIPPED #854) → plan-10 (next) → plan-5 → plan-7 →
plan-6 → plan-8, with plan-11 (audit-check refresh, slot 4.95) inserted after plan-10 — disjoint
surface, so it may also run beside any of them if wall-time matters. **Fallout rule:** once a plan
is RUNNING, its spec doc is frozen — late fallout goes to a follow-up doc (plan-10 is the live
example), never into the running plan's doc. **Era-stamp rule (new, 2026-07-09; registry
LIVE post-plan-11):** every remaining roadmap plan that fixes a failure mode adds, as part of its
landing, its `fixed_since` era stamp to the audit skill's `CHECK_ERA` registry
(`.claude/skills/audit-archived-plan-retrospectives/scripts/audit.py` — the single central table
plan-11 introduced, keyed by check name; the invariant `set(CHECK_ERA) == set(CHECK_NAMES)` is
test-enforced) so the audit distinguishes pre-fix rows from regressions. **AMENDED 2026-07-10
(plan-5 proved the footer form structurally dead — a post-archive footer step cannot change
source on merged main):** the stamp must be a DELIVERABLE inside the plan (implemented+committed
with the change set), NOT a lifecycle-footer item. plan-12 D5 is the pattern; plan-5's owed #862
stamp rides there too. Fold the stamp in as a deliverable at outline time for plan-6/7/8.

| # | Command | Theme |
|---|---------|-------|
| 4.5 | `plan-9-micro-lane` | SHIPPED — PR #854, archived `.plan/local/archived-plans/2026-07-09-micro-lane/` (see §3) |
| 4.9 | ~~**THE PILOT**~~ **DONE — PR #860** (archived `.plan/local/archived-plans/2026-07-09-fix-missing-get-deliverable-subcommand/`): **1.93M vs ≤1.2M = checkpoint MISS #2**, split verdict — `minimal` posture fired (FIRST lever engagement ever), light lane missed with the root cause now KNOWN (lane router decides before classification/recipe-match; fix → plan-5). Lesson `2026-07-06-17-001` retired (verb shipped). Full record §7.13 |
| 4.8 | ~~`plan-10-finalize-contracts`~~ **SHIPPED** — PR #855, archived `.plan/local/archived-plans/2026-07-09-plan-10-finalize-contracts/` (see §3/§4). Triage FIX not-done/STOP contract (directive + build-failing analyzer), post-rebase step-doc re-resolution, `rate_limited` discriminator + opt-in rate-window await (§4 operator opted in). Retired `2026-07-07-21-002` + `2026-07-07-21-001` |
| 4.95 | ~~`plan-11-audit-check-refresh`~~ **SHIPPED** — PR #857, archived `.plan/local/archived-plans/2026-07-09-plan-11-audit-check-refresh/` (see §3/§4) — audit skill refreshed: era sentinels + retire-on-quiet + 4 new roadmap-mechanics checks (dispatch-topology, finalize-flow-conformance, merge-window-accounting, lane-lever-effectiveness — the checkpoint measurement arm). Corpus-cut (confirmed dormation) is its orchestrator-owned closing step |
| 4.97 | ~~`plan-12-enable-merge-queue`~~ **SHIPPED** — PR #863, archived `.plan/local/archived-plans/2026-07-10-enable-merge-queue/` (see §3/§4) — merge-queue enablement as a marshall-steward provisioning capability, probe-driven on BOTH providers: `merge_group:` CI trigger + `ci repo merge-queue probe/enable` verbs (both providers) + real GitLab merge-train enqueue replacing the fail-loud stub + idempotent provider-neutral steward provisioning step + probe-backed `use_merge_queue` set-time validation + actionable finalize error + both-provider fixture-vs-live docs. 6 self-review iterations (symmetric github/gitlab doc drift) + 2 automated-review loop-backs (CodeRabbit Major API-error-vs-`ineligible` misclassification catch on both providers). Merged NORMAL path (`use_merge_queue` stays false; steward provisioning is a separate operator action). ~5.5M. **DIVERGENCE (corrected 2026-07-10 landing analysis, §7.16c): the traveled plan doc DID carry `### D5 — era stamps as a DELIVERABLE` — the OUTLINE silently dropped it (spec 6 deliverables → outline 5) and the finalize report misattributed the loss to the footer form.** The **era-stamp `CHECK_ERA` is OWED for #862 + #863 → the era-stamp micro plan (§8)**; the outline-drop class is a watch item. |
| 5 | ~~`plan-5-inline-init`~~ **SHIPPED** — PR #862, archived `.plan/local/archived-plans/2026-07-10-plan-5-inline-init/` (see §3/§4). Inline phase-1-init in main context (6 native prompts) + removed dead `phase-1-init` effort role + inline-phase metrics recording + complete dispatch-mechanics doc sweep + **routing-order fix** (recipe eval before the planning-lane router — the light-lane wiring defect from §7.13). 2 review loop-back cycles (5 CodeRabbit/Gemini fix tasks: unused param, stale `research` sub-key, prose overstatement, call-graph heading, xref redirect). ~4.6M |
| 13 | ~~`plan-13-init-routing-metrics`~~ **SHIPPED** — PR #875, archived `.plan/local/archived-plans/2026-07-11-plan-13-init-routing-metrics/` (see §3). Tier-1 floor → pre-diagnosed-change SHAPE + classify-before-route (killing S2-on-unset) + inline-init metrics **n=6/6 tokens confirmed — but in the WRONG UNIT: the four-field sum includes `cache_read`, so the printed 14.1M total is init-dominated; comparable cost ~2.95M (§7.26; unit fix → plan-15 D6)**. Light-lane acceptance now rides plans 14/15 (the next pre-diagnosed request), scored on the comparable basis; the two §8 light-lane blockers are struck below |
| **14** | `/plan-marshall task="implement .plan/plan-optimization/plans/plan-14-ci-merge-hygiene.md"` | merge-queue/CI plumbing: `--delete-branch` strip + strategy-flag drop (lesson `23-001`, 4 recurrences — retire) + 600s-vs-880s wait-budget wiring (ratchet/p50 verify-first) + holder-liveness (recovering ≠ dead) + **D5 (added 2026-07-11, §7.25): un-dead the `pre-submission-self-review` compose pre-filter** (empty-footprint-at-phase-4 polarity; 2/2 post-promotion drops). AFTER 13 (light-lane acceptance candidate); may pair with 15 |
| 15 | ~~`plan-15-architecture-data-sweep`~~ **SHIPPED** — PR #876, archived `.plan/local/archived-plans/2026-07-12-plan-15-architecture-data-sweep/` (spec doc moved there post-hoc — the run skipped the lifecycle move; see §3). **FIRST END-TO-END LIGHT-LANE RUN** (n=1/1); cost 2.27M comparable vs ≤1.2M = ceremony+loop-back overshoot, not a mis-route. D6 unit fix CONFIRMED (future totals comparable natively). OWED: D4 era stamp `#PLAN15-PR` unresolved on main (surgical command prepared) + D3 drift-metric self-count + housekeeping post-merge promotion revert |
| 7 | `/plan-marshall task="implement .plan/plan-optimization/plans/plan-7-execute-task-tests.md"` | per-task sibling-test coverage + the D2 REMAINDER post-#868 (leaf prohibition, commit-obligation, freshness ledger incl. detached path) + project-local module mapping |
| 6 | `/plan-marshall task="implement .plan/plan-optimization/plans/plan-6-prompt-reachability.md"` | refine/execute-task prompt batching + tool frontmatter + guard→gating + D5 promote-then-retire `10-001`. After plan-7 (shared `execute-task/SKILL.md`) |
| 8 | `/plan-marshall task="implement .plan/plan-optimization/plans/plan-8-context-trim.md"` | per-dispatch doc-trim (direction — scope in outline, quantify first; reconciles `2026-06-30-08-001` at roadmap completion). SOLO, LAST |

## 6. Dialogue-fix outcome notes (shipped #840 — what changed vs. the plan docs)

- **Scope expansion (operator-approved): ALL SIX init prompt sites migrated**, not just the two
  confirmed-live ones — the phase-1 half of the old FU-A is **already closed**. Consequences wired
  into the queue: plan-5's D1 now replaces six signal sites (not two) with direct prompts; plan-6 no
  longer depends on plan-5 and covers only refine Step 11 + execute-task + FU-B + the guard flip.
- The reachability guard (D2) is live analyze-only; remaining surfaced exposures are exactly
  plan-6's D1/D2 scope.
- The transitional signal wiring (leaf returns `*_prompt` envelopes → planning.md consumes) is the
  surface plan-5 later deletes by inlining init — it is *expected* churn, by design.

## 7. Non-plan actions

1. **Capture #812's rate-limit-deferred lessons** (quota reset 2026-07-05; #840's lessons-capture
   ran, but verify the #812-specific ones landed). The high-value one — *execute-task agents run
   only compile/quality-gate, never the module's suite* — is the lesson behind plan-7. File via
   `manage-lessons`.
2. **Lesson `2026-06-30-21-001`** (manage-findings pr-comment `resolution_detail` mis-pairing): do
   NOT file a separate plan — folded into plan-4 verify-first.
3. **Push-freshness re-stale `--force` friction** — lesson coverage RESOLVED (2026-07-07): it IS
   the `16-002`/`24-09-002` family (recurred #812, #842, #846, and on #849's own finalize, each
   time a justified `--force` override). No new lesson needed; re-homed into **plan-7 D2** (the
   build-freshness ledger contract).
4. **Finalize mark-step-done omissions** (observed #840): dispatched finalize agents skipped their
   own step bookkeeping; orchestrator back-filled. Lesson `2026-06-21-00-002` covers the key-
   canonicalization half — was folded into plan-3, but **#849 descoped it** (doc-example rename
   only; lesson still active, see §7.5 outcome). Recurred on #847: the `plan-retrospective` step
   (built primarily as a user-invocable command) didn't self-record its finalize-step marker; the
   orchestrator back-filled again — same wart family, watch during plan-3's finalize rework.
5. **Lesson-corpus triage done 2026-07-07** — every active lesson was mapped against the remaining
   plan surfaces. Folded (see each plan's "Lessons folded in" section): plan-3 ×7(+1 conditional) —
   **outcome at landing (#849): 2 retired** (`00-002`, `20-18-001` — verified covered in merged
   code), **6 correctly retained**: three are standing guards that stay corpus-owned (`24-14-001`,
   `28-13-001`, `21-11-002` — honored in the D4 design, not codified artifacts), and three were
   consciously DESCOPED and remain OPEN surfaces — the freshness-gate re-stale family
   (`16-002`/`24-09-002`; outline verdict: "this plan touches neither the freshness gate nor the
   finalize build ordering") and `2026-06-21-00-002` (mark-step-done key canonicalization — NOT
   shipped; the manage-status change was a doc-example rename only). All three were **re-homed
   2026-07-07**: the freshness-gate family (`16-002`/`24-09-002`) → **plan-7 D2** (build-freshness
   ledger contract — it recurred again on #849's own finalize), and `21-00-002` → **plan-4**'s new
   step-ownership contract (together with the leaf-can't-dispatch orchestrator-workflow friction
   #849 surfaced: project-local finalize steps that sub-dispatch cannot run in a leaf — no lesson
   existed for that; it's now encoded in plan-4 directly). plan-4 ×4
   (beyond the two already in verify-first), plan-5 ×1, plan-7 ×5, plan-8 reconciles
   `2026-06-30-08-001` at roadmap completion. **Already retired**: `2026-06-29-01-001` (the original
   envelope-loop filing — covered by landed #842, confirmed by #845's 0-verbatim measurement;
   tombstoned 2026-07-07). **Verify-then-retire candidate** (likely covered by landed #842, needs a
   behavior check before removing): `2026-06-21-19-001` (Q-Gate burns an iteration re-dispatching
   for informational findings — the content-hash re-run gate should now prevent this).
   `2026-06-24-18-001` (per-deliverable commits not firing) was on this list but is **confirmed NOT
   fully covered** — a parallel run on 2026-07-07 hit a second live path (phase-5 leaf backgrounded
   an ~11-min build twice → orchestrator took over verification → the leaf's commit step never ran,
   commit recovered at finalize); re-folded into **plan-7 D2** (deterministic long-build ownership +
   commit-fires-regardless-of-owner) together with the `feedback_orchestrator_owns_long_builds`
   class. Note plan-7's D1 (per-task module suites) would AMPLIFY this mode if D2 didn't land with
   it. The ANSI/FORCE_COLOR
   plugin-doctor false-positive issue is **FIXED — PR #846** (parallel session, 2026-07-07;
   executor front-door pins NO_COLOR/PYTHON_COLORS/CLICOLOR/CLICOLOR_FORCE/PY_COLORS + pops
   FORCE_COLOR for every subprocess; plugin-doctor `_run_help` color-suppressed + ANSI-stripped +
   cache bump; proven live 865→0 findings — the local plugin-doctor gate is trustworthy again).
   Its run added fresh plan-3 recurrence evidence: ci-wait 600s deadline-exceeded **3× in one run**
   (`2026-07-07-00-002`) and another sync-baseline freshness re-stale (`2026-06-20-16-002`) — both
   already folded into plan-3. **Follow-on PR #847 landed 2026-07-07** (the formerly-parked sibling
   `fix-build-wrapper-log-parser-contract`, parallel session; archived
   `2026-07-07-fix-build-wrapper-log-parser-contract`): the four build-wrapper parsers themselves
   hardened — shared `read_log_text` ANSI-strip choke point, order-independent pytest-summary
   parsing (the review loop caught the shipped whole-log count-scan as a REAL correctness gap),
   result-assembly safety-net + regression coverage. **2.3M tokens — the cheapest roadmap-era run
   yet**, finalize still 40% (927k; two review loop-backs, each a full ~15–18-min CI re-validation
   needing two 600s ci-wait windows — more 00-002/plan-3 evidence). New lesson
   `2026-07-07-10-001` (summary-line anchoring + cross-parser audit) folded into plan-7;
   `2026-07-06-17-001` (`get-deliverable` verb) hit its **3rd recurrence** → designated the plan-9
   pilot. It also ran deep-lane/`auto` at 99.5% confidence on a bounded bug fix — another
   unused-lever datapoint for plan-9 D1/D3. Lessons with no roadmap-surface fit stay in the corpus,
   owned by the normal lessons pipeline.

6. **Side plan #851 landed 2026-07-07** (`fix-terminal-title-defects`, archived
   `2026-07-07-fix-terminal-title-defects`): executor active-plan binding rework
   (bind-on-entry / protect-active / stale-reclaim) + worktree-aware title-state reader + arch doc;
   5 files / +435. **1.9M — first at-median run** (asterisks in §2). Fallout: (a) new lesson
   `2026-07-07-20-001` — `architecture-refresh.md` orders top-level `--project-dir` AFTER the
   subcommand, so every verbatim call exit-2s on first attempt; exact 5-call-site rewrite known →
   **micro-path candidate #2** (no queued plan owns that doc); (b) `2026-07-06-17-001`
   (`get-deliverable`) hit its **4th recurrence** (#842, #846, #847, #851) — pilot pressure rising;
   serial order puts plan-9 right after plan-4, so keep it as the pilot unless a 5th recurrence
   lands first; (c) **bot-review coverage gap pattern**: CodeRabbit rate-limited + Gemini errored →
   merged with NO substantive bot review (local gates carried it: self-review 38/0, plugin-doctor
   0, CI 10/10, Sonar 0). With Gemini sunsetting 2026-07-17, a CodeRabbit rate-limit window will
   mean ZERO bot review — operator call whether automated-review should optionally await the
   rate-window reset (~54 min); would slot into plan-4's automated-review surface if wanted.
   Deep-lane/`auto` at 99.5% confidence again on a bounded 2-defect fix (plan-9 datapoint).
7. **Side plan #850 landed 2026-07-07** (`introduce-deterministic-dist-branch-versioning`, archived
   `2026-07-07-introduce-deterministic-dist-branch-versioning`, squash `4b1056d2`): deterministic
   `0.1.N` marketplace versioning + per-target `dist-manifest.json` fingerprints +
   executor/marshal.json provisioning stamps + `generate_executor preflight` wired into
   `/plan-marshall` re-entry and marshall-steward; version `0.1.1068` live. 3.9M / 8 deliverables
   (finalize 1.76M = 45%; review loop 16 comments → 15 fixed incl. 12 robustness — review earned
   its cost again). **THE D4 MUTEX PROOF ARRIVED**: first finalize overlapping sibling landings
   (#849 and #851 both rebased in mid-run) under the widened mutex — lock held 19 min across
   rebase→force-push→CI-wait→merge, ZERO bounces/retries, first-attempt force-push-with-lease,
   `upstream_commit_count=0` at merge, clean re-review of the rebased HEAD; the two mid-finalize
   rebases happened cleanly at sync points (the designed residual for long finalizes). Lessons
   fallout: `2026-07-07-21-002` (triage subagent implemented+tested its fix task inline, marked it
   done, returned loop_back → no-op loop-back with changes stranded uncommitted; orchestrator
   hand-committed) and `2026-07-07-21-001` (session-start-loaded finalize docs go stale when a
   mid-finalize rebase pulls in a flow refactor → `workflow_not_found` on #849's deleted ci-verify
   workflow doc; orchestrator adapted by re-reading the worktree) → **both re-homed to plan-10**
   (plan-4 was ALREADY RUNNING when this fallout landed; plan-10 verify-first diffs against
   plan-4's landed state and implements only the uncovered remainder);
   `2026-07-07-16-001` (architecture inventory stale/missing `skills_by_profile` for
   `default`/`documentation` modules — pure data refresh, exact fix known) → **micro-path
   candidate #3**, no owning plan.
8. **Side plan #853 landed 2026-07-08** (`fix-executor-preflight-staleness-signaling`, archived
   `2026-07-08-fix-executor-preflight-staleness-signaling`, squash `1b759de8`): #850 follow-up —
   `sync.py` now copies `dist-manifest.json` into the plugin-cache root + a contract-lock test;
   acceptance PASSED end-to-end (preflight reports 0.1.1069/fresh, was `unknown`). **2.5M for a
   textbook pre-diagnosed 3-file fix** → the strongest plan-9 datapoint yet (§2). Second observed
   scope-gated subtraction: `security-audit` dropped (tier above posture cutoff) — the
   step-composition lever fires consistently now. New lesson `2026-07-08-09-001`
   (unlink-before-copy TOCTOU/stale-symlink in the cache-root copy; ONLY the PR bot caught it —
   the "slipped past every in-house gate" family with `2026-06-22-13-001` [folded into plan-7] and
   `2026-06-30-15-001`; corpus-owned). Operator items (a) dirty marshal.json and (b) Sonar
   extras — **both RESOLVED by #852**: plan-4's finalize committed the sync-defaults/provisioning
   refresh (adding `provisioned_version`/`config_seed_fingerprint` + the phase-* knob block) and
   the `credentials_config` Sonar extras rode through intact in the same landed file. The
   standalone chore-PR prompt prepared for this is MOOT — do not run it (2026-07-08 verify-first
   re-check confirmed: no gap, no PR).
   **Watch DOWNGRADED — observed upsert-safe (2026-07-08):** re-verified byte-for-byte that
   `credentials_config::plan-marshall:workflow-integration-sonar` (`{organization: cuioss,
   project_key: cuioss_plan-marshall}`) is **present and identical at every committed
   marshal.json-touching commit from #806 [seed, `6345f09d`] → #840 → #842 → #845 → #852
   [`dabab228`] → HEAD** — never absent on committed main, and byte-identical across the #852
   boundary (`dabab228^ == dabab228`). The earlier "loss" was only ever an uncommitted working-tree
   artifact (#850's session), discarded — no clobber ever landed. #852 IS the marshal.json-writing
   provisioning/stamping event the watch targeted, and it **preserved** the non-default
   `credentials_config` key → the write path is upserting, not clobbering. No lesson, no tool-layer
   fix warranted. Residual watch (weak): if a future provisioning/stamping write is ever observed
   *dropping* a non-default key on committed main, re-arm (adjacent to `2026-06-29-23-001`).
9. **plan-9 landing addenda (2026-07-09, #854)**: (a) the operator-observed phase-5 leaf
   build-backgrounding recurrence left **NO decision-log trace** — the orchestrator preempted and
   owned every build synchronously, so the workaround renders the pattern invisible to log mining;
   log-based counts UNDERCOUNT this mode and the operator report is the record → recorded as
   plan-7 D2 evidence. (b) New lesson `2026-07-09-04-001` (`architecture which-module` matches
   `paths.sources` only, never `paths.tests`) → **folded into plan-7 D1** (the touched-module
   test-suite resolution depends on exactly that mapping). (c) Folded lesson `2026-06-29-16-001`
   RETAINED with correct rationale (D4 followed the registration checklist but codified NO guard —
   fold-to-retire intent not satisfied; stays corpus-owned until a guard ships). (d) The pilot was
   correctly NOT shipped inside plan-9 (the path must exist before something can run through it) —
   now queued as §5 row 4.9 with the exact request phrasing; `2026-07-06-17-001` stays active
   until the pilot lands the verb.

10. **plan-10 landing addenda (2026-07-09, #855)**: (a) **Era-stamp follow-up** — plan-10's spec
    doc was frozen before the §5 era-stamp rule existed, so its lifecycle footer carried no stamp
    item. At the plan-11 landing analysis, verify `CHECK_ERA` (audit skill) carries plan-10's
    boundary — `fixed_since=2026-07-09` (#855, `f878af85`) for the mechanics its checks sentinel:
    the triage FIX not-done contract (21-002 signature — `finalize-flow-conformance`'s not-done
    sentinel), post-rebase step-doc re-resolution (21-001 signature), and the `rate_limited`
    discriminator. If plan-11's parallel session didn't stamp it, stamp it then (post-#855
    occurrences of those signatures are regressions, not expected-era rows). (b) Folded-lesson
    retirement CLEAN: exactly the two folded lessons (21-002, 21-001) retired, both verified
    covered vs the merged tree; nothing over- or under-retired. (c) New lesson `2026-07-09-14-001`
    (fixtures must mirror production data shape) is corpus-owned (persona-module-tester) — a
    guidance pointer added to plan-7 (its D1/classifier rework writes exactly this kind of
    parser-fixture test). (d) Positive live proof: D4's `rate_limited` discriminator fired on this
    plan's own automated-review — shipped-and-exercised in the same run.

11. **Side plan #856 landed 2026-07-09** (terminal-title freeze + executor sticky plan-binding —
    follow-on to #851 on the same surface): D1 pure `session_binding.py` + `session
    bind/resolve-plan/doctor` verbs, D2 bind+repaint fired on the manage-status phase-write seam
    (the unified seam for both defects), D3 sticky binding REMOVED from the executor template
    (revises #851's bind-on-entry design — read-only `--plan-id` inspection no longer binds; proven
    live when the diagnostic session itself got stuck-bound to plan-10), D4 merge_lock title tokens
    consolidated onto the shared seam, D5 docs. Review gates earned their keep again: 2 under-scoped
    doc/test-contract gaps (a NEW recurrence of `2026-06-29-16-001` — the doc-contract-drift lesson,
    still guard-less after plan-9 retained it; recurrence count rising) + 3 real robustness bugs in
    the new module caught by automated-review. **Merge-window: the external-PR gap is REAL
    (operator-confirmed 2026-07-09).** The mutex is acquired only by plan-marshall finalize flows —
    any merge outside that machinery (ad-hoc/manual `gh` merges, the parallel remediation effort,
    dependabot, plans finalizing without the mutex path) advances main mid-window and CANNOT be
    serialized by the lock (it doesn't know the lock exists). Under the up-to-date-required ruleset
    that forces repeated rebase+CI cycles regardless of mutex discipline — #856 paid 3. The
    structural remedy already EXISTS, shipped optional as **#849 D5 `use_merge_queue`**: GitHub's
    merge queue serializes ALL PRs including external ones. Operator call: if mixed
    external-traffic weeks stay common, enable it. For the next audit sweep, plan-11's
    `merge-window-accounting` check should attribute bounces to sibling-mutex traffic vs
    external-merge traffic — only the former reflects on mutex correctness. 3.8M / clean
    retrospective / all 6 phases recorded → **checkpoint MISS #1** (see §2).

12. **plan-11 landing analysis (2026-07-09, #857, squash `9353f71f`)**: (a) **§7.10 era-stamp
    verification DONE** — `CHECK_ERA` is LIVE on main, covers all 22 checks (the
    `set(CHECK_ERA) == set(CHECK_NAMES)` invariant), and plan-10 is represented: general checks +
    `dispatch-topology` are stamped at the `plan-10` head-boundary. One nuance, accepted:
    `finalize-flow-conformance` is stamped `#849` (its ci_verify mechanics), so plan-10's #855
    not-done-contract boundary is not DISTINCTLY stamped — practically moot post-corpus-cut (every
    post-cut plan is post-#855); if a not-done row from the #849–#855 window is ever flagged as a
    regression, correct that stamp via a chore PR then. (b) **Cost anatomy root-caused LIVE**
    (operator irritation justified): `architecture which-module --path
    .claude/skills/audit-archived-plan-retrospectives/scripts/audit.py` → **`module: null`** — the
    project-local skill maps to NO module, so the per-deliverable build-freshness gate had nothing
    to scope to and fell back to WHOLE-TREE verify on every commit, each run synchronously by the
    orchestrator (leaves can't background long builds). The plan's actual test surface was two
    audit test files — the correct scope was seconds, not ~10-min tree builds × N commits. Folded
    into **plan-7 D1** (together with lesson `2026-07-09-04-001` this completes the
    touched-path→test-scope resolution gap: mapped modules mis-resolve test paths; project-local
    surfaces don't resolve at all). (c) **Metrics (from the archived plan, all 6 phases recorded):
    4.50M total** — 4h27m worked / 9h1m wall / 4h37m idle; phase split planning-side 1.02M
    (22.6%, LEAN vs the 35.9% corpus median) · **execute 2.17M = 48.3% (corpus median 27.4% — hard
    anomaly)** · finalize 1.31M (29.1%). The anomaly is the (b) root cause made visible: phase 5
    ran 509 tool uses / 2h33m worked with 302.9M cache-read (the transcript re-fed on every
    synchronous orchestrator build). This plan's overspend was NOT planning bloat — it was pure
    per-commit whole-tree build overhead, the cleanest plan-7 D1 evidence yet.

13. **THE PILOT landed 2026-07-09 — PR #860** (`fix-missing-get-deliverable-subcommand`, merge
    `d09d05d`, archived; all 6 phases recorded): `get-deliverable` verb as a thin alias over the
    pre-existing `read --deliverable-number` (refine's key finding: the capability EXISTED — the
    4-recurrence lesson was a *discoverability* gap, not a missing feature) + shared
    `_lookup_deliverable` helper + tests + SKILL.md row; Sourcery loop-back added the
    `document_not_found` guard/parity test. Lesson `2026-07-06-17-001` RETIRED (shipped). **Metrics:
    1.93M / 1h25m worked / 3h14m wall** — planning-side 813k (42%!), execute 257k (13%), finalize
    859k (45%, of which the automated-review rounds 412k). **Checkpoint MISS #2** (≤1.2M target,
    1.6×) — though −23% vs #853's comparable pre-diagnosed class and tied-cheapest full-pipeline
    run. **Routing autopsy (decision log):** (i) lane router fired at init 15:44:53 with
    `change_type=None, scope_estimate=None` — predicate `S2:scope_estimate` fired on the UNSET
    signal → deep fail-safe; (ii) `recipe-match`/`resolve-recipe` ran 16:30:56, **46 min later** —
    the Tier-1 auto-route structurally cannot precede the lane decision on the `task=` path →
    **fix folded into plan-5** (routing-order requirement, first-class); (iii) `change_type`
    classified `feature` (verb addition) — fix-keyword matching can't hit it; recipe fit gate must
    key on the pre-diagnosed-change shape (also plan-5's fold); (iv) `minimal` FIRED via the #840
    posture dialogue (operator-chosen; projected=auto) — dropped simplify/security-audit/sonar, and
    the **bot-enforcement guard correctly re-added automated-review** (ci_provider=github — bots
    review every push regardless). Live defects logged by the run: (a) phase-5 sub-agent
    backgrounded+orphaned a build — orchestrator-owns-long-builds recurrence → plan-7 D2 evidence
    (now 4 observations, still no decision-log trace from the takeover itself); (b)
    `architecture-refresh.md` `--project-dir`-after-subcommand — lesson `2026-07-07-20-001`
    recurrence #2, micro-path candidate #2 pressure rising; (c) **NEW: manifest compose-order
    defect, verified in the composed manifest** — `finalize-step-preference-emitter`
    (frontmatter `order: 80`) listed AFTER `archive-plan`; running as-listed would fail (archive
    moves the plan dir); the run reordered manually + logged [WARNING] → **micro-path candidate
    #4** (compose must honor step `order:` vs the archive barrier), see §8. (d) Executor preflight
    advisory: marshal provisioning stamps stale (0.1.1072 vs installed 0.1.1075) — non-blocking;
    reconcile via `/marshall-steward` on the next steward run (plan-12's D3 touches the same
    surface).

14. **plan-5 landing analysis (2026-07-10, #862, merge `32d283bb`; §4 has the deliverable
    summary)**: (a) **Metrics: 4.57M / 5h3m worked / 7h28m wall** — ties plan-4 as most expensive;
    anatomy is finalize-dominant (planning 1.29M/28%, execute 832k/18%, **finalize 2.44M/53%** —
    two loop-back cycles over three automated-review passes + doc-sweep re-validations). Roadmap
    infrastructure, not a checkpoint row. Q-Gate earned its keep: 2 rounds caught 6 real
    outline/task defects pre-code. First fully UNATTENDED landing (all three `*_without_asking`
    true). (b) **Era-stamp process defect found and fixed**: the §5 rule's lifecycle-footer form is
    structurally dead (post-archive steps can't change source on merged main) — plan-5's stamp is
    OWED; rule AMENDED (stamp = deliverable), plan-12 D5 carries both its own and plan-5's #862
    stamp. (c) Folded lesson `2026-07-06-10-001` consciously RETAINED by lessons-housekeeping
    (residue = still-uncodified general authoring rule; promote-then-retire in a future related
    plan — correct disposition, not a bookkeeping defect). (d) The routing-order fix is code-closed
    but UNPROVEN — plan-12's run is the live acceptance test (decision log: recipe-match before
    the lane routing line; no `S2` on unset signals). (e) plan-5's own run was the last of its
    kind by design: dispatched init, deep lane, 187k init phase — the post-#862 init should show
    materially lower init cost and native prompts; compare on plan-12.

15. **Side plan #861 landed 2026-07-09/10** (`fix-architecture-init-enrichment-wipe`, merge
    `454c4516`, archived): `architecture init --force` unconditionally blanked every module's
    `enriched.json` (`api_init(force=True)` in `_cmd_manage.py`) — curated enrichment destroyed;
    the marshall-steward "Regenerate Architecture" flow ran that init --force AFTER a preserving
    discover --force (redundant AND destructive, while its prose promised preservation). Fix at
    the tool layer (per the standing feedback rule): blank-all moved behind explicit
    `--reset`; plain `--force` preserves + seeds missing — silent wipes impossible by
    construction; regression + CLI e2e + no-op tests; full doc/call-site sweep; live-validated on
    its own finalize (discover --force → byte-identical descriptor). Also restored
    nifi-extensions' 14 wiped files (admitted side-track; consumer repos now protected too).
    Review notes: self-review caught 2 real defects in its own diff; **Gemini's
    "error-on-reset-alone" suggestion correctly DECLINED** (contrary to deliberate no-op design —
    good triage judgment). **Metrics: 2.88M / 2h26m worked** — finalize 1.61M (56%,
    review loop-back + 2 CI cycles under landing traffic), planning-side 960k (33%), execute 309k
    (11%). Ordinary single_module bug fix → **checkpoint MISS #3 (1.9×) — the checkpoint is
    DECIDED: FAILED 0/3** (see §2 — re-arm post-#862 CONFIRMED by the operator 2026-07-10). Ran pre-#862
    (dispatched init, deep lane — structurally forced, last-generation evidence).

16. **plan-12 landing analysis (2026-07-10, #863, squash `a5672048`; §3/§5 have the deliverable
    summary)**: (a) **Metrics: 5.48M / 4h3m worked — NEW COST RECORD; finalize 3.71M = 68% (worst
    share ever recorded)** — 6 self-review iterations on symmetric two-provider doc drift + 2
    automated-review loop-backs; planning 1.28M (23%), execute 488k (9%); scope-guard corollary: a
    provider-symmetric feature is a MIRROR SURFACE and counts double at review time (recurrence
    merged into `2026-06-29-16-001` by the retrospective). The 8h33m execute wall was 7h48m idle
    (overnight), not work. (b) **Routing acceptance test VOID, not failed**: init ran 07-09
    19:32:47 — BEFORE #862 merged (~03:00 on 07-10); the parallel pair structurally could not test
    its partner's fix (my scheduling note assigned the test to the wrong plan). Same pre-fix
    signature (deep via `S2` on unset signals, no prior recipe-match) — pre-fix evidence, not a
    regression. **The acceptance test moves to the next plan initing post-#862.** (c) **Era-stamp
    slip #3 — root cause corrected vs the landing report**: the traveled plan doc HAS `### D5 —
    era stamps as a DELIVERABLE` (verified in the archive), so the finalize report's "it was
    scoped as a Lifecycle-footer item" is wrong — the OUTLINE silently dropped a spec deliverable
    (spec 6 → outline 5) and no gate compares source-doc deliverables against outline coverage
    (Q-Gate validates the outline internally only). Stamps for BOTH #862 and #863 now ride the
    era-stamp micro plan (§8); watch the outline-drop class for recurrence before filing a lesson.
    (d) **Init compare (plan-5 §7.14e follow-through): inconclusive** — 116k vs plan-5's 187k, but
    this init predates #862 (dispatched-era); the true inline-init datapoint is also the next
    plan. (e) **Pending operator action: `/marshall-steward` → Configuration → Merge Queue** —
    probe→confirm→enable; the first post-enable finalize is the queue's live acceptance test
    (expect external-traffic bounces → ~0 in merge-window accounting).

17. **Era-stamp micro plan landed 2026-07-10 — PR #866** (`fix-check-era-stamps`, merge
    `16099535`; retires the #862/#863 era-stamp debt). **THE ROUTING-ORDER FIX IS PROVEN LIVE**:
    decision log shows `recipe-match` at 11:37:23 — BEFORE the planning-lane routing at 11:43:05
    (the #862 acceptance test PASSES on ordering). Two residual gaps, both now the light lane's
    LAST blockers: (a) **Tier-1 confidence floor rejected a textbook candidate** ("no recipe above
    the confidence floor" on a root-cause-known/exact-change/single-file request) — pure
    calibration; (b) when no recipe matches, the router STILL fires `S2` on UNSET signals → deep
    fail-safe (the classify-before-route half of plan-5's requirement did not ship). Light lane
    lifetime firings: still ZERO. **Checkpoint (re-armed) datapoint #1: ~1.11M recorded — AT the
    ≤1.2M surgical target** (asterisk: n=5/6, init unrecorded — true total ≈1.2–1.3M), the first
    ordinary run at target EVER, despite absorbing ~30 min of merge recovery; `minimal` fired
    (2nd time), the compose `surgical_bug_fix` rule produced a 16-step manifest (plugin-doctor /
    self-review / simplify / security-audit / sonar dropped; bot-enforcement guard re-added
    automated-review, which ran, 308k). Operational defects: (i) **`pr safe-merge` reported
    success but CLOSED #866 unmerged** — merge queue now REQUIRED on main (steward provisioning
    #865) while `use_merge_queue=false`; recovery = restore branch + reopen + `pr merge-queue`
    (~30 min). TWO defects here: safe-merge must preflight queue-required state (probe verb
    exists!) and must treat closed-unmerged as FAILURE; and the steward enable evidently flipped
    the PLATFORM without flipping the KNOB — plan-12 D3 specified both atomically → re-run
    `/marshall-steward` (probe should report the drift and set the knob), and the safe-merge
    preflight is a tool-layer micro fix. (ii) **Inline-init metrics UNRECORDED** (init row: wall
    only, no tokens/worked — first live inline init; plan-5 D3 shipped a regression test yet the
    live path under-records). (iii) Compose-order defect RECURRENCE #2 (preference-emitter after
    archive-plan in the composed manifest — micro-path candidate #4 pressure rising). (iv)
    phase-5 leaf backgrounded its build and returned WITHOUT committing — plan-7 D2 recurrence
    (commit-not-firing path, `18-001`; orchestrator committed at finalize + re-built for
    freshness). (v) A stale-looking `automatic-review` merge-lock holder was cleared manually —
    **CORRECTED in §7.19a: the holder was a LIVE sibling plan mid-merge-recovery, not a phantom**;
    the watch item is now holder-liveness detection (a recovering plan must not be judged dead),
    softened by the platform queue owning merge serialization.

18. **Steward chore #867 landed 2026-07-10 17:14Z** (provisioning stamp 0.1.1080→0.1.1082, main
    `55060fb5`): **the merge queue's first CLEAN-PATH proof** — PR enqueued and merged through the
    platform queue with all checks green, no closed-unmerged repeat (the `--squash --auto`
    strategy flag was ignored with a warning: the queue owns the merge method — expected; the
    enqueue verb could drop the flag to silence it, cosmetic). Queue status: LIVE and working;
    #1's safe-merge preflight fix remains wanted for the general/consumer case, but this repo's
    trigger condition (knob drift) is gone. Two small leftovers: (a) executor regenerated to
    0.1.1082 mid-session → restart Claude Code before new plan dispatches from that session; (b)
    **2 caller-side notation-drift warnings** (`manage_solution_outline` / `manage_status`
    underscore forms) — small caller-sweep, **micro-path candidate #5**, no owning plan.

19. **Side plan #864 landed 2026-07-10** (`automatic-review` modularization, squash `48bfc58a`,
    archived `2026-07-10-automatic-review`): bot-review pipeline made config-driven/data-not-code —
    new top-level **`automatic-review` skill (STEP-ID RENAMED from `automated-review`** — use the
    new name in all future queue docs/commands), per-bot standards with embedded data blocks +
    generic `bot_registry.py` loader, **Sourcery first-class bot_kind**, `enabled_bots` knob
    (timely: Gemini sunsets 2026-07-17 — the transition is now config), producer dedup on
    `(bot_kind, comment_id)`. Review gates caught real issues: plugin-doctor+self-review found 2
    rename scope-gaps (the 16-001 doc-contract class, correctly folded not re-filed); CodeRabbit
    caught 4 incl. this plan's OWN D3 wiring gap + a latent `_parse_block` bug. **Metrics: 5.46M /
    5h36m worked** (outline 762k design-heavy, execute 2.06M/38%, finalize 1.90M/35%).
    **EXCLUDED from the re-armed checkpoint: init 07-09 19:37, pre-#862** (pre-fix routing
    signature; also a 5-deliverable modularization where deep is the correct lane). **Two record
    corrections:** (a) the §7.17(v) "phantom" `automatic-review` merge-lock holder was NOT phantom
    — it was THIS plan, live, mid-merge-recovery; #866's holder-matched release cleared a LIVE
    sibling's lock (harmless only because the platform queue now owns merge serialization —
    holder-liveness heuristics must not equate "recovering" with "dead"; watch item re-scoped).
    (b) safe-merge closed-unmerged is now a **2nd live occurrence** (#864 hit it first: `merged:
    true` misreport + `--delete-branch` closed the PR; branch restored at `98e9dc09`, reopened,
    queue-merged on attempt 2 behind #866) — recurrence evidence for the running micro-fix #1;
    the union-resolved marshal.json conflict also committed `use_merge_queue: true` (fix-forward
    now on main via this plan + steward).

20. **Micro-fix #1 landed 2026-07-10 — PR #869** (`fix-pr-safe-merge-queue-required`, main
    `2e427f9c`): safe-merge now runs a base-branch-scoped merge-queue preflight (dual-remedy
    refusal), fails CLOSED on probe error, and re-verifies `merged` state (closed-without-merge →
    explicit failure); + D3 scope-add: first-class `base_branch` param on `/plan-marshall`
    (operator_param > project_default > git_fallback). **Refine DISPROVED my #865 premise**
    (verify-first paid off): `e161fed6` flipped `use_merge_queue` in the SAME commit as the
    platform rule — the steward enable WAS atomic; likelier #866 cause: the plan worktree carried
    a pre-#865 marshal.json snapshot → NEW watch class: **worktree config-staleness** (config
    changes on main don't reach in-flight worktrees until rebase). **Metrics: 3.09M / 2h8m
    (n=5/6, init unrecorded AGAIN — fix #3 in flight)** — outline 663k, finalize 1.10M; posture
    `auto` (only security-audit dropped). **Re-armed checkpoint datapoint #2: MISS at ~1.24×**
    (multi_module ≤2.5M — the D3 scope-add moved it out of the surgical class; routing: floor
    rejected the pre-diagnosed request again + S2-on-unset → deep, both pre-fix-#2, expected).
    **New lesson `2026-07-10-23-001` (live catch on its own merge):** `pr merge-queue` forwards
    `--delete-branch`, which GitHub REJECTS when the queue is enabled (branch-cleanup.md's
    documented call carries it too); recovered by re-enqueueing without the flag; three-point
    directive filed (strip in handler + fix doc + fixture-accurate test) → **micro-path candidate
    #6** (pair with #867's cosmetic `--squash --auto` warning — same flag-forwarding family).
    **Zero bot reviews on this PR** (Sourcery rate-limited, CodeRabbit/Gemini silent) — the
    §7.6(c) risk pattern live again; with `enabled_bots` (#864) + the plan-10 D5 rate-window
    await knob (default off), bot-coverage posture is an operator config decision now. Compose-
    order defect **recurrence #3, behavior WORSENED**: preference-emitter SKIPPED outright this
    time (not manually reordered) — fix #4 in flight. Executor regenerated twice → restart before
    next dispatch from that session.

21. **Micro-fix #4 landed 2026-07-10/11 — PR #871** (`fix-manifest-composer-archive-order`, main
    `b3169143`): compose-order defect closed (§8 row struck — the REAL root cause was
    marshal.json insertion-order emission + sync-defaults back-fill, not a missing frontmatter
    read; terminal stable sort as the last cmd_compose choke-point; the bug reproduced 3× during
    its own fix run — lanes preview, phase-4 manifest, own finalize). Self-review caught 2 real
    doc-contract gaps over 2 iterations (undocumented sort transform; transform miscounted 3→4).
    **Metrics: 3.26M / 2h20m (n=5/6 — init unrecorded, recurrence; fix #3 in flight)** — finalize
    1.68M (52%, full 20-step posture-`auto` manifest), execute 771k incl. the orchestrator verify
    sweep + 5 test contract updates. **Re-armed checkpoint datapoint #3: MISS ~2.2×
    (single_module) → checkpoint DECIDED 1/3; the minimal-vs-auto ~2M/plan lever quantification
    and the third-arming decision are in §2.** `--delete-branch` queue rejection recurrence #2 on
    its own merge (candidate #6 pressure HIGH). Sourcery rate-limited again (notice-only);
    CodeRabbit re-ran green on the rebased HEAD — not bot-unreviewed this time. Executor at
    0.1.1088; restart before next dispatch from that session. Burst remaining in flight: #2
    (light-lane blockers — the one that changes everything) + #3 (inline-init metrics).

22. **Side plan #868 landed 2026-07-11** (detach-and-notify for long builds/CI waits, main
    `432b4474`): the orchestrator-babysits-long-builds cost class is structurally addressed —
    `await-long-running` detach seam (persona + workflow + `canonical_verify`), `run_config.py`
    ci-duration record/p50 rolling window, `cmd_ci_wait` detach (p50-seeded sleep + `gh run
    watch`/`glab ci status --wait`). **Dogfooded live on its own run** (~700–930s builds + CI
    waits detached past the 600s ceiling, main free; fire-and-forget queue merge with a Monitor
    wake). **Roadmap consequences:** (a) **plan-7 D2 RE-SCOPED** (doc updated): the
    orchestrator-tier half is DONE; remaining = leaf-backgrounding prohibition + commit-fires-
    regardless obligation (`24-18-001` path 2) + freshness-ledger stamping INCLUDING the new
    detached path; (b) the `feedback_orchestrator_owns_long_builds` memory updated (synchronous
    babysitting superseded by detach-notify); (c) interplay with #849's `ci:wait` ratchet: the
    p50 window now seeds waits — plan-7/audit should treat p50-seeding as the current mechanic.
    New lesson `2026-07-10-23-002` (post-rebase stale WORKTREE EXECUTOR can't resolve a skill the
    rebase pulled in → regenerate) — second member of the **worktree-staleness watch class**
    (§7.20's marshal.json snapshot is the first). The #855 post-rebase re-resolution contract
    proved itself again (automated-review.md removed upstream by #864, handled). Refine caught a
    real `holder_is_dead` correctness bug in the deferred global-mutex idea (correctly deferred).
    **Metrics: 2.4M / 2h14m worked — an ordinary multi_module feature UNDER the 2.5M target**
    (post-decision context datapoint, not counted; the 6h13m idle is the very CI-wait cost this
    feature removes going forward).

23. **Self-review promotion landed 2026-07-11 — PR #872** (`promote-self-review-default-finalize`,
    main `ffe1e935`): the always-finds-bugs step is now the built-in
    `default:pre-submission-self-review` for EVERY consumer — `default_on: true`, configurable
    contract on the workflow-body frontmatter, deterministic surfacer resolved via the new
    `ext-point-self-review-surfacing` extension point with a **zero-generator fallback**
    (consumer-safe: LLM review still runs without a domain surfacer), meta-project `project:`
    wrapper deleted + marshal migrated + full doc sweep. **The era-stamp-as-deliverable pattern
    WORKED** (D6 shipped, outline did not drop it) — with a new wrinkle: phase-5 stamped a GUESSED
    PR number (#868), corrected at finalize when the real #872 existed → new lesson
    `2026-07-11-09-001` (era-stamp values that reference the plan's own PR must be resolved at
    finalize, not execute). **The promoted step dogfooded itself** (caught 2 real doc-drift
    defects in its own plan; CodeRabbit caught 4 more of the same class). Routing: floor rejection
    + deep via S2 (pre-fix, expected — and `auto` is CORRECT for this 6-deliverable class).
    **Metrics: 2.9M / 3h20m (n=5/6, init unrecorded — fix #3 still UNSTARTED)** — post-decision
    context: a multi_module promotion at ~1.16× the old target. `--delete-branch` queue rejection
    = the recurrence #3 already logged. **NEW medium watch: the 600s ci-wait budget repeatedly
    timed out against the ~880s verify job** (re-waits) — #849 D3's ratchet should have learned
    880s and #868's p50 seeding should now cover it; if the next landing still shows 600s
    re-waits, the ratchet/p50 is not wired to this wait path → defect. **Burst accounting
    corrected: micro-fixes #2 (light-lane blockers — THE decisive one) and #3 (inline-init
    metrics) were NEVER STARTED** — the parallel trio was #872/#868/#864. #2, #3, #6 are the
    pending command set.

24. **CONSOLIDATION RECONCILIATION (operator-requested, 2026-07-11).** Of the four prepared
    micro-fix commands, only #1 (#869) and #4 (#871) ran; the era-stamp (#866) and self-review
    promotion (#872) commands also ran. Everything still open was aggregated into THREE new plan
    docs + one fold, so the whole remainder is six single plans: **plan-13**
    (light-lane floor + classify-before-route + inline-init metrics — absorbs unstarted micro-fixes
    #2+#3; run FIRST; its acceptance replaces any third checkpoint arming), **plan-14**
    (merge-queue flag family/lesson `23-001` + ci-wait budget wiring + holder-liveness; after 13,
    pairs with 15), **plan-15** (micro-path candidates #2/#3/#5: architecture-refresh flag order/
    `20-001` + `skills_by_profile` refresh/`16-001` + notation-drift; after 13, pairs with 14),
    then the roadmap remainder **plan-7** (re-scoped post-#868) → **plan-6** (gained D5:
    promote-then-retire `10-001`) → **plan-8** (SOLO last). Deliberately left as WATCHES, not
    plans: worktree staleness (2 members, lessons filed — plan-worthy only on next recurrence),
    outline-drops-spec-deliverable (1 occurrence), zero-bot-review posture (a CONFIG decision:
    `review_rate_window_await` + `enabled_bots`, decide before Gemini sunsets 2026-07-17).

25. **Side plan #874 landed 2026-07-11 (`steward-sync-defaults-executor-stale-noop`, main
    `4fcbe9f40`, archived `2026-07-11-steward-sync-defaults-executor-stale-noop`)**:
    marshall-steward's menu-mode remediation pass ran sync-defaults through a version-stale
    executor → silent no-op with `marshal_status: stale` persisting. Fix (doc-only, SKILL.md): a
    `generate_executor preflight` step inserted BEFORE sync-defaults + a detect/warn conditional
    when config stays stale after a clean-looking sync. Refine adversarially REJECTED the
    request's Option 2 on an invalid premise (`bootstrap_plugin.resolve_bundle_path` is NOT
    version-aware — first `iterdir()` hit, not newest; only `collect_script_dirs` got the fix) →
    lesson `2026-07-11-15-002`, folded as **plan-15 D5**. Notably the refine leaf resolved that
    three-option choice WITHOUT `AskUserQuestion` ("no AskUserQuestion tool available in this
    dispatch") — live plan-6 D1 evidence, noted in its doc. CodeRabbit caught a real correctness
    gap in the plan's own detect/warn logic (inferring clean from `marshal_status: fresh` alone,
    ambiguous with a failed sync) → loop-back TASK-002 requiring both calls' `status: success`
    first; lesson `2026-07-11-15-001`. **Cost: 1.52M / 3h50m (n=5/6)** — post-decision context:
    the cheapest `auto`-posture run ever recorded, 1.27× the surgical ≤1.2M target — the
    `surgical_bug_fix` compose rule + surgical Q-gate bypasses + scope-gated subtractions did the
    work even without `minimal`. Routing rows (init 11:26Z, PRE-#875 merge): floor rejection +
    S2-on-unset — the FINAL pre-fix-era datapoints, not regressions; plans 14/15 remain the
    post-fix acceptance. **NEW STRUCTURAL DEFECT found at this landing analysis: the
    #872-promoted `pre-submission-self-review` default step is dead at compose** — the
    `_apply_pre_submission_self_review_inactive` pre-filter drops it on empty footprint, but
    compose runs once at phase-4 BEFORE the worktree exists (footprint always empty there); the
    docstring's promised later re-compose never happens on the normal path. 2/2 post-promotion
    plans (#874 AND #875) logged the omission — the step has fired ZERO times since promotion →
    folded as **plan-14 D5** (mirror `_apply_canonical_verify_inactive`'s
    empty-footprint-is-a-no-op polarity). Also: the freshness-gate re-stale family recurred
    (doc-only simplify commits → rebuild + fresh CI wait per loop-back; plan-7 D2 evidence
    updated), and the merge went through the platform queue cleanly per the report.

26. **plan-13 landed 2026-07-11 — PR #875** (`plan-13-init-routing-metrics`, main `36bb2e667`,
    archived `2026-07-11-plan-13-init-routing-metrics/`; its run session did the §3/§5/§8/README
    reconciliation, this item is the independent landing ANALYSIS). All 4 deliverables verified
    against the archive; own-init routing rows (10:42Z) show floor-reject + S2-on-unset —
    pre-its-own-fix, as expected, and deep/`auto` was CORRECT for a 4-deliverable feature. D4 era
    stamps finalize-resolved from `PR-PENDING` (the `2026-07-11-09-001` pattern working). One
    loop-back (CodeRabbit `_PATH_RE` dedup → TASK-9) + one verify-gate HIT (narrow-prefix bug in
    `_recipe_skill_dir_candidates` caught by a D1 test at the orchestrator-tier verify).
    `--delete-branch` queue rejection = recurrence #4 (plan-14 D1). **The material finding is in
    its own metrics: D3 landed n=6/6 but in the WRONG UNIT.** The `four_field_total` sum includes
    `cache_read_input_tokens`, so the 1-init row records 11,155,473 (= 145 in + 25,967 out +
    11,093,578 cache_read + 35,783 cache_creation — verified against `manage-metrics.py` ~1511
    and the archived metrics.md), two orders of magnitude above every dispatched row's
    envelope-based total. **The printed 14.1M grand total is therefore NOT ledger-comparable; the
    comparable cost is ~2.95M (phases 2–6)** — mid-pack for a 4-deliv roadmap plan (cheaper than
    plan-5's 4.6M / plan-12's 5.5M), with a lean 446k execute and a 1.34M finalize (1 loop-back +
    2 CI waits + the ~24-min queue verify). §3/§5 rows corrected. Consequences wired: **plan-15
    D6** owns the unit fix (drop cache_read / match the dispatched `<usage>` definition), and the
    plans-14/15 ≤1.2M acceptance is scored on the comparable basis (phases 2–6 + init
    in/out/creation) until it lands — both plan docs carry the scoring note. Lessons-capture
    filed 0 and housekeeping retained 58 — correct: both blockers were §8-owned, and the unit
    defect was found post-archive by this analysis.

27. **plan-15 landed 2026-07-12 — PR #876** (`plan-15-architecture-data-sweep`, main `3efc74e88`,
    archived `2026-07-12-plan-15-architecture-data-sweep/`; spec doc moved into the archive
    post-hoc — the run skipped the lifecycle move step, and it also skipped the post-archive
    HANDOVER/README updates, both done at this landing analysis). **THE FIRST END-TO-END
    LIGHT-LANE RUN**: routed light at init (this morning's 3/3 evidence), STAYED light (no
    explosion escalation), one collapsed refine+outline+derive envelope. **The lane verdict is
    a clean PASS (n=1/1); the COST verdict is a MISS: 2.35M grand / 2.27M phases-2–6 vs the
    ≤1.2M surgical target (~1.9×)** — anatomy: `auto`-posture 20-step finalize ceremony + one
    review loop-back (Gemini caught a REAL malformed-non-dict guard gap in D2's staleness check →
    fixed in-run, second CI wait). Consistent with the standing conclusion: the lane works, the
    remaining ~1M is POSTURE engagement (operator chose `auto` at the ask; `minimal` was
    projected). D6's unit fix CONFIRMED live (init row 79K comparable — grand totals are
    ledger-comparable natively from here on). 3 folded lessons retired on schedule; 1 new
    (`2026-07-12-15-001`, meta corpus: docs-only deliverables changing a pinned call-shape break
    narrative-contract module-tests). **Three owed follow-ups**: D4 era stamp merged unresolved
    (§8 row; surgical fill command prepared — ALSO the recalibrated floor's first must-match
    test), D3 drift-metric self-count (§8 row), housekeeping post-merge promotion reverted (§8,
    folded into the step-key-hygiene command). Leaf-backgrounded builds recurred ×2 under
    build-slot contention with concurrent plan-14 ([OUTCOME] coverage 3/10) — plan-7 D2 evidence,
    noted in its doc.

## 8. Open-defects reference

- ~~Posture dialogue inert~~ → **FIXED #840** (all six init sites; verified on its own run); made
  fully native (no signal hop) by plan-5.
- ~~`marshal.json` four-key cost table~~ → **FIXED #840** (D3, incl. drift test).
- ~~Routing-decisions aspect non-rendering~~ → **FIXED #845** (plan-2; renders live, D2 registered⇒rendered guard + domain-aspect fallback).
- Refine Step 11 / execute-task unreachable prompts + execution-context tool-frontmatter gap →
  plan-6.
- Execute-task sibling-test gap → plan-7 (+ §7.1 lesson).
- ~~pr-comment `resolution_detail` mis-pairing (`30-21-001`)~~ → **FIXED #852** (plan-4 D1
  relational integrity + content-discriminator hash_id; lesson retired).
- ~~Merge staleness / CI-wait window~~ → **FIXED #849** (plan-3: D4 widened mutex + D3 adaptive
  ci-wait ratchet) — **proof observed on #850**: first mutex-era finalize overlapping two sibling
  landings — 19-min hold, zero merge bounces, first-attempt force-push, `upstream=0` at merge.
- Freshness-gate re-stale family (`16-002`/`24-09-002`) → **plan-7 D2** (re-homed after plan-3
  descoped it; recurred on #849's own finalize; recurred again on #874 — doc-only simplify commits
  re-staled the gate, one rebuild + fresh CI wait per loop-back, §7.25).
- ~~Mark-step-done canonicalization (`21-00-002`) + leaf-can't-dispatch orchestrator-workflow
  steps~~ → **FIXED #852** (plan-4 D6: per-step `owner` declaration in the manifest schema +
  `default:`-prefix canonicalization at the mark-step-done boundary; lesson retired).
- ~~Triage create-task-NOT-done contract (`21-002`) + post-rebase step re-resolution (`21-001`)~~ →
  **FIXED #855** (plan-10: D1 directive + D2 build-failing analyzer for the triage contract; D3
  `advances_main_via_rebase` fact + post-rebase step-doc re-resolution contract; both lessons retired
  at landing).
- ~~Lane router decides before classification/recipe-match on the `task=` init path~~ → **FIXED
  #862 and PROVEN LIVE on #866** (recipe-match precedes the lane routing, §7.17). ~~Two residual
  light-lane blockers: (a) Tier-1 recipe confidence floor rejects textbook surgical candidates;
  (b) no-recipe path routes on UNSET signals (`S2` deep fail-safe).~~ → **FIXED #875 (plan-13):**
  D1 recalibrated the Tier-1 floor to key on the pre-diagnosed-change SHAPE (surgical-fix only),
  D2 added a pure `scope_estimate_from_request_pure` heuristic + a phase-1-init Step 8a.5 that
  classifies `change_type`/`scope_estimate` BEFORE the lane route (killing S2-on-unset). **PROVEN
  LIVE 2026-07-12 — THE LIGHT LANE FIRED, first lifetime firings ever, on ALL THREE post-#875
  inits (plan-14 08:53Z, plan-15 08:54Z, steward-step-ordering 11:26Z):** scope-estimate-heuristic
  classified pre-route, route line shows `fired=none` + `planning_lane=light` +
  `execution_profile=minimal` projected 3/3, and each dispatched the collapsed light-lane envelope
  (refine+outline+derive in ONE dispatch). Plan-14 + steward then escalated light→deep at
  `trigger=explosion` (one-way ratchet, ALSO first-ever firings — correct, multi-deliverable
  features); **plan-15 stayed light through compose — candidate first end-to-end light-lane run.**
  Floor rejection 3/3 is CORRECT (none are pre-diagnosed surgical); the floor's must-match half
  still awaits a real surgical request. Operator chose posture `auto` at the ask each time
  (plan-14 deliberately, so its D5 self-review runs on its own diff). Cost scoring at the
  landings, on the comparable basis (see the inline-token unit row).
- ~~Era stamps OWED for #862 AND #863~~ → **DONE #866** (CHECK_ERA bumped + comments + test
  assertion; watch item closed).
- ~~`pr safe-merge` closes-without-merging under queue-required~~ → **FIXED #869** (base-branch-
  scoped queue preflight, fail-closed probe, merged-state re-verify; 2 live occurrences #864+#866).
  The "#865 non-atomic steward enable" sub-claim was DISPROVEN in refine (`e161fed6` was atomic);
  replacement watch class: **worktree staleness** — two members: (a) config (in-flight worktrees
  carry pre-landing marshal.json snapshots until rebase, §7.20); (b) executor (post-rebase worktree
  executor can't resolve skills the rebase pulled in → regenerate; lesson `2026-07-10-23-002`,
  §7.22).
- **Merge-queue flag-forwarding family** (lesson `2026-07-10-23-001`): `pr merge-queue` forwards
  `--delete-branch` (GitHub REJECTS it queue-enabled; branch-cleanup.md documents the bad call) +
  #867's ignored `--squash --auto` warning — strip/silence both in the handler + doc + fixture-
  accurate tests → **plan-14 D1** (absorbed micro-path candidate #6). **Recurrences #2 (#871), #3
  (#872, 2026-07-11), #4 (#875), #5 (#876)** — confirmed that EVERY queue merge hits the
  rejection and pays a retry until plan-14 D1 lands.
- **`pre-submission-self-review` dead at compose (NEW, found at the #874 landing analysis,
  §7.25)**: the #872-promoted default step has fired ZERO times since promotion — 2/2
  post-promotion plans (#874 AND #875) logged `pre-submission-self-review omitted — empty
  footprint`. The `_apply_pre_submission_self_review_inactive` pre-filter drops on empty
  footprint, but compose runs once at phase-4 BEFORE the worktree is materialised (footprint
  always empty), and the docstring's promised later re-compose never happens on the normal path.
  Inverted polarity vs the adjacent `_apply_canonical_verify_inactive` (which correctly no-ops on
  compose-time emptiness). Fail-open: a promoted quality gate silently absent — same class as the
  light-lane unreachability → **plan-14 D5**. **CONFIRMED + REFINED on nifi-extensions #432
  (2026-07-12): 3 more empty-footprint drops at early composes, but a LATE re-compose (worktree
  live, footprint non-empty) KEPT the step and it RAN (71k tokens, caught nothing that round but
  executed) — the step fires iff a re-compose happens post-materialization, proving D5's
  fix direction.**
- **#864 step-rename shipped WITHOUT a config-key migration + the composer emits unresolvable
  step keys that HARD-BLOCK finalize (NEW, 2026-07-12, three consumer datapoints):** every
  consumer marshal.json still carried the retired `default:automated-review` key. nifi-extensions
  #432: the composer emitted the unloadable step → **finalize hard-blocked** → in-run workaround
  (their lesson `2026-07-12-15-001`); TokenSheriff #560: benign variant (duplicate step, ~0 cost);
  cui-jsf: pre-empted. Consumer configs fixed to the canonical `plan-marshall:automatic-review`
  (nifi in-run; TokenSheriff PR #561 — correcting the initially-advised WRONG `default:` prefix,
  which has no standards doc and would itself have hard-blocked; cui-jsf PR #140). **Upstream fix
  needed (prepared command; thematic homes plan-14/steward are RUNNING+frozen):** (a)
  sync-defaults/steward reconcile migrates renamed step keys via a rename table (retired-key →
  canonical), (b) compose validates every emitted step RESOLVES at compose time — fail loud with
  an actionable message naming the bad key, never emit an unresolvable step for finalize to choke
  on.
- ~~**`resolve_bundle_path` not version-aware** (lesson `2026-07-11-15-002`, filed by #874's
  refine)~~ → **FIXED #876 (plan-15 D5): newest-version selection in BOTH resolvers + tests;
  lesson retired at landing.**
- **Era-stamp placeholder MERGED UNRESOLVED — recurrence #2 of `2026-07-11-09-001`** (#876:
  `"architecture-lookup-ratio": "#PLAN15-PR"` literal on main, `audit.py:297` + 2 comment refs;
  #872 had the same slip caught at finalize, #876's finalize had NO wired fill step and prose
  didn't save it). Immediate fix = the prepared surgical command (§7.27 — doubles as the
  recalibrated floor's FIRST must-match live test). Systemic fix owed: the own-PR placeholder
  fill must be a WIRED manifest step running pre-push at finalize, not a prose instruction —
  same class as **lessons-housekeeping's post-merge SKILL.md promotion being REVERTED on #876**
  (post-merge finalize steps cannot edit source under branch protection; they must run pre-push
  or emit a follow-up PR). Both folded into the step-key-hygiene prepared command as an extra
  deliverable.
- **Notation-drift metric counts its own detector literals** (#876 D3 residue): the 2 residual
  drift counts are plugin-doctor catalog/detector literals, not genuine callers — the metric
  can never reach 0 as wired. Small pre-diagnosed follow-up: exclude the detector's own files
  from the drift scan + pin drift=0 on a clean tree.
- **Zero-bot-review windows recur** (#851, #869): Sourcery rate-limited + CodeRabbit/Gemini silent
  → merged bot-unreviewed. Mitigations exist but are config: plan-10 D5 `review_rate_window_await`
  (default off) + #864 `enabled_bots`. Operator posture decision, esp. after Gemini sunsets
  2026-07-17.
- **600s ci-wait budget vs long jobs — CONSUMER recurrence** (TokenSheriff
  `client-code-review-fixes`, 2026-07-12): `ci --plan-id` wait 602.97s = budget timeout + 417s
  re-wait — the #872 signature outside the meta-project → already **plan-14 D2** (RUNNING; doc
  frozen, this line is the recurrence record).
- **WATCH (1 occurrence): post-remediation re-verify leg falls off the CI abstraction**
  (TokenSheriff `client-code-review-fixes`, 2026-07-12): after sonar-roundtrip's remediation push,
  ZERO executor `ci` calls — the session used a raw background Bash wait (1h39m,
  "Wait for sonar-build") + raw `gh` log pulls, hand-grepping past harden-runner noise, while the
  script-owned path (`ci:wait` detach + `failing_checks` log enrichment via `filter_log`/build
  parsers, storage `work/ci-bodies/`) sat unused (ci-bodies empty). Round 1 of the same finalize
  used the verbs correctly and ci-verify classified the failure precisely (S3077) — so the
  machinery works and the docs lose the agent only on the LOOP-BACK leg (sonar-roundtrip →
  re-verify). Fix direction if it recurs: the sonar-roundtrip / re-verify workflow docs must
  explicitly route the re-wait through `ci:wait` and point at `failing_checks`/`ci-bodies` for
  failure diagnosis — never raw `gh run view --log`. Candidate fold: plan-6 (doc/prompt
  reachability family) or a micro follow-up to plan-14.
- ~~**Inline-init metrics unrecorded** (first live inline init, #866: wall-only row, n=5/6) —
  plan-5 D3 regression despite its test.~~ → **FIXED #875 (plan-13 D3):** `cmd_enrich` now surfaces
  the main-context four-field attribution into `total_tokens` for inline phases (explicit-wins), and
  the fixture-green/live-dead `test_phase_boundary_inline.py` was flipped to the production enrich
  path. **n=6/6 TOKENS confirmed on plan-13's own metrics** (`enrich four_field_phases_attributed:
  6`; 1-init recorded 11.1M tokens vs the old `-`). Residual `n=5/6` on the Worked/Tool-Uses columns
  is the inherent inline-phase limit (no `<usage>` envelope for worked-seconds), not the token bug.
- ~~**Inline-phase `total_tokens` in the WRONG UNIT** (found at the #875 landing analysis, §7.26:
  the four-field sum included `cache_read`, init row 11.16M, grand totals init-dominated)~~ →
  **FIXED #876 (plan-15 D6) and CONFIRMED on its own metrics: 1-init row 79K comparable.**
  Future plans print ledger-comparable totals natively — the manual comparable-basis scoring rule
  is retired (plan-14, which initied pre-fix, is the last plan whose printed total needs a manual
  check at landing).
- ~~Manifest compose order vs archive barrier~~ → **FIXED #871** (terminal stable
  `_sort_steps_by_frontmatter_order` choke-point in cmd_compose; archive-plan barrier by
  construction; real root cause was marshal.json INSERTION order + sync-defaults back-fill; the
  bug reproduced 3× during its own fix run; 5 pre-existing tests had baked the buggy ordering and
  were contract-updated).
- Outline can silently DROP a spec deliverable (spec 6 → outline 5, unflagged; #863 §7.16c) — no
  gate compares source-doc deliverables vs outline coverage. First observation; candidate Q-Gate
  check on recurrence.
- Manifest compose order ignores finalize-step frontmatter `order:` relative to the archive barrier
  (`preference-emitter` order:80 composed AFTER `archive-plan`, #860) → micro-path candidate #4, no
  owning plan.
- Project-local surfaces (`.claude/skills/**`) resolve to `module: null` → whole-tree build
  fallback per commit (plan-11 paid ~1M; §7.12) → **plan-7 D1**.

## 9. Standing operating constraints

- **Retire-what-you-replace, completely.** Every plan that removes or restructures a dispatch/step
  MUST (a) sweep for the now-dead config surface — the knob/effort-role in `_config_defaults.py`,
  the `marshal.json` seed, and `doc/user/configuration.adoc` — and (b) sweep ALL concept docs
  describing the old behavior (grep the old wording/payload keys tree-wide; enumerate, don't
  sample). Clean-slate, no deprecation shims. This is the known under-scoping failure mode; plans
  3, 4, and 5 carry explicit removal-sweep deliverables — treat them as the pattern.
- **Folded lessons MUST leave the corpus when their plan lands.** Each plan doc carries a "Lessons
  folded in — retire on landing" section; the landing run's lessons-housekeeping retires every
  folded lesson the plan actually covered (`manage-lessons remove --force` with a
  coverage-citing reason). A folded lesson still active after its plan landed is a bookkeeping
  defect — check at each landing analysis.
- **plan-3 LANDED (#849): bounded pairs per the §5 concurrency schedule are now sanctioned** (max 2
  concurrent, disjoint surfaces only) — the widened mutex serializes finalize windows via FIFO; the
  first live parallel finalize pair is D4's proof run. Same-surface plans stay strictly sequential
  regardless — including against the parallel remediation effort's open PRs (§4).
- **Measurement is live** (#812): capture per-dispatch before/after on plans 1, 4, 8 — that's why 5-A
  shipped first.
- **Every plan touches shipped surfaces** → normal branch→PR→CI→review→squash-merge flow; expect the
  finalize cost floor until plans 1/3/4 reduce it.

---

# SNAPSHOT 2 (2026-07-13) — content removed at the second HANDOVER compaction

Everything below was cut from HANDOVER.md on 2026-07-13 after the burst landed (items A–D, 16,
17, plan-7 all shipped and analyzed). Detailed shipped rows, resolved queue rows, struck defect
rows, and closed watches — verbatim as they last stood.

## Snapshot-2 §3: detailed shipped rows (#877–#887)

| Plan | PR | Full row |
|------|----|-----------|
| pr-strategy knob | #879 | `project.pr_strategy` compact\|distinct + 150-file ceiling; **first-class `manage-config project pr-decision --changed-files N` verb (ride\|split)** = the single consult point for create-pr + the new ad-hoc full-PR-flow hard rule (authored fresh) + the steward landing cycle. Bots caught 2 real bugs (unsupported-flag doc example; verb read config without re-validation → lesson `2026-07-12-18-001`). 3.13M n=6/6 (init 48.2K comparable) |
| steward sort + landing cycle | #878 | `manage-config steps-sort` (frontmatter-order, reuses #871 choke-point) + **plan-less `ci pr create --body-file` + `ci repo label ensure` (both providers — the plan-bound-PR-creation gap is CLOSED)** + base-branch-conditional landing cycle w/ skip-bot-review label + merge-queue-aware merge. 3.9M n=6/6 (init 66.6K — D6 comparable unit confirmed on a 2nd plan). Light→deep escalation correct (11-file). **Landing cycle PROVEN LIVE 2026-07-12: the operator's steward pass landed its reconcile via PR #880 through the queue (stamps → 0.1.1096) — no direct-to-main mutation** |
| drift-metric redirect (item B) | #882 | **Refine INVALIDATED the request premise** (preflight never computes drift; source already measured 0; the proposed exclude-own-files fix would have been a coverage-narrowing no-op) → redirected to one additive regression test pinning `notation_drift == 0` against clean marketplace SOURCE (+ loop-back pytest.skip guard from PR review — re-review ran clean). Deep/auto escalation CORRECT (S1+S5 fired, request premise not concrete) — the adversarial-refine value case: 1.90M spent, a wrong fix prevented. **True residual-2 cause (corrected mid-finalize): ~25 stale old plugin-cache VERSION DIRS (0.1.1068–0.1.1092, 0.1-BETA); resync writes newest, never prunes; drift auto-detect scans a stale old version → default-context drift=2 PERSISTS across resyncs** → prepared item D. New lesson `2026-07-13-00-001`: automatic-review classified dispatched-leaf but its body documents a nested verification-feedback dispatch it cannot perform (2 burst occurrences: #883 blocked-return, #882 orchestrator-owned). 3h44m |
| holder_is_dead sink (item C) | #883 | `holder_is_dead()` guarded via `is_valid_plan_id()` before path construction (inverse polarity to sibling — corrupt lock stays reclaimable) + traversal-corpus test; lesson `2026-07-12-19-001` RETIRED with citing reason. **FIRST at-target run on `auto`: 1.17M incl. CodeRabbit + sonar** (light lane via signal_set; minimal projected, operator upgraded to auto for security-critical — decision-logged with rationale). Recipe no-match on a pre-diagnosed request = 2nd wrongful rejection (watch fired → §5). Leaf/dispatch invariant fired VISIBLY (automatic-review leaf returned `status: blocked` for the nested verification-feedback dispatch; orchestrator resumed — the sanctioned yield contract works when wired). Lesson-residue promotion BLOCKED post-merge on protected main = recurrence #2 of the source-edit gap (plan-16 D3). 3h50m wall, 4× ~15-min CI waits |
| era-fill surgical (item A) | #881 | BOTH audit.py placeholders resolved on main (`#876`/`#877`, comment blocks rewritten — recurrences #2+#3 cleared); **the surgical at-target measurement: 1.69M MISS 1.41× vs ≤1.2M — finalize 1.17M (69%): ci-verify 17m + merge-queue 23m under the 5-wide burst**; light+minimal via `signal_set` (recipe no-match on a pre-diagnosed request = plan-13 D1 residual, benign); leaf-backgrounded build recurrence #8 (phase-5 executor leaf backgrounded module-tests, orchestrator takeover); lesson `2026-07-11-09-001` correctly RETAINED (decision-logged: mechanism fix = plan-16 D3). 2h0m wall |
| plan-14 ci-merge-hygiene | #877 | D1 `--delete-branch`/`--strategy` stripped from `pr merge-queue` (handler + argparse + 3 docs) — **verified live: #877 self-merged via queue with no rejection** + D2 opt-in `--adaptive` ci:wait on all 3 raw wait sites + D3 merge-lock live-worktree guard (`stale_holder_live_worktree` blocked signal) + D5 self-review empty-footprint polarity flip + D4 era stamp `PR-PENDING`. Bot caught a real path-traversal in D3's own new code (gemini → TASK-11 guard). Light→deep escalated (5 deliv/7 modules). Rebased over plan-15/#876 audit.py CHECK_ERA conflict. 3.9M n=6/6 (init 98.4K). Lesson `2026-07-10-23-001` retired; new `2026-07-12-19-001` (holder_is_dead sibling sink) |
| plan-17 review-completeness | #884 | **D1 pre-merge comment-completeness barrier DOGFOODED LIVE — caught 2 late CodeRabbit comments on its OWN PR's rebased HEAD before merge, triaged (1 declined false-positive, 1 accepted meta), then merged via queue** + D2 per-bot completion-aware polling (`bot_registry` `completion_check_name` + `github_pr bot_completion` verb) + D3 step-done integrity guard (`review_completeness.py`) + D4 knobs/`configuration.adoc` + D5 fixture tests + D6 era-stamp #849→#884 **resolved live pre-merge (first plan to CLOSE the era-placeholder recurrence — no wired step yet, hand-resolved)**. Self-hosted automatic-review caught 5 real fixes → loop-back (TASK-11–15: unguarded query_findings, stale adoc step-id, verb-count drift, RUF005, mutex-release doc). Light→deep escalated (cross_cutting, 6 deliv). Sibling #881 audit.py CHECK_ERA conflict resolved on rebase. **phase-5 executor did NOT commit per-deliverable (finalize found dirty worktree — recurrence of `2026-06-24-18-001`).** New lesson `2026-07-13-00-001` (automatic-review dispatched-leaf-can't-dispatch topology). 3.3M n=6/6 (worked 2h46m; wall 10h34m — CI + merge-queue idle) |
| plan-7 execute-task-tests | #887 | **RE-SCOPED HARD post-#868** (verify-first found per-deliverable module-tests + tier-agnostic `kind=build` stamp + owner-independent commit already shipped). D1 which-module `paths.tests`∪`.claude/skills` containment fix (retired lesson `2026-07-09-04-001`; closes project-local `module:null` whole-tree fallback) + D2 leaf-no-background invariant in `agents.md`/`execute-task` + regression test locking #868's tier-agnostic stamp + D4 era stamp `sequence-and-build-minimality`/`token-economics` (era-stamp-fill ran INLINE off-manifest at its order-21 slot — resolved PR-PENDING→#887 pre-merge, **first live proof of the #885 mechanism**). Gemini caught a genuine root-module prefix-length bug in D1's own code → TASK-7 loop-back fix (module-tests GREEN, re-reviewed clean). **9th leaf-backgrounding recurrence DURING ITS OWN FINALIZE despite D2's just-landed invariant (phase-5 fix-task leaf backgrounded module-tests + returned before committing; orchestrator took over) → the doc-only invariant is necessary-not-sufficient, STRUCTURAL GUARD STILL OWED → new lesson `2026-07-13-12-002`** + `2026-07-13-12-003` (automatic-review mark-step-done key drift: qualified vs bare manifest key stranded the record at loop_back). Detached orchestrator builds killed 3× under build-slot contention with sibling item-D. Merged via platform merge queue (squash). 2.8M (worked 2h24m; wall 5h15m — CI + 4-wide merge-queue wait) |
| cache-scanner orphan fix (item D) | #886 | `find_bundles()` groups by bundle, skips `.orphaned_at` dirs, selects newest via `_version_sort_key` (mirrors plan-15 D5 pattern; NO pruning — CC's 7-day GC owns deletion) + consumer-chain regression test; **acceptance met: drift=0 with stale orphaned dirs present**. Gemini caught a real misgrouping edge case (`^\d+\.\d+`-named non-versioned bundle silently discarded → parent-guard + test). **Leaf-backgrounding recurred ×3 THIS RUN despite explicit "run synchronously" in every dispatch prompt — prompt-level instruction proven insufficient (suggests harness auto-backgrounding); large share of the 2.1M was re-running lost builds** → plan-6 D6 evidence. 2.1M / 1h43m (surgical MISS 1.75×, takeover-driven) |
| plan-16 step-key-hygiene | #885 | D1 compose-time step-resolution fail-loud gate (`_check_step_resolvable` + `bundle:skill` discovery branch, wired into `cmd_compose`) + D2 idempotent `RETIRED_STEP_KEY_RENAMES` table in sync-defaults (`automated-review`→`plan-marshall:automatic-review`, knob-preserving, pre-deep-merge) + D3a wired `project:finalize-step-era-stamp-fill` step (registered for future plans) + D3b `source-edit-pushability.md` pre-merge contract + D3c version-aware-bundle-path re-apply + D5 `configuration.adoc` step-key-forms + rename-table. **D7 audit.py CHECK_ERA DROPPED — upstream #881 already resolved the same placeholders (operator-confirmed at sync-baseline semantic re-verify).** **TWO upstream conflicts resolved LIVE mid-finalize** (audit.py/#881 → D7 drop; configuration.adoc/#884 → resolve-both, kept #884 params + D5 rename fix). Self-review caught 3 real issues (era-fill unguarded write + finally cleanup, output-schema doc drift, retired-key doc drift); PR bots 8 comments → 6 fixed via loop-back (TASK-13–16). Merged via platform merge queue (squash). ~4M n=6/6 (12h37m wall — 2 upstream rebases + PR-review loop-back + 3× full CI waits). **Lesson `2026-07-11-09-001` RETAINED** (era-fill mechanism shipped but unproven end-to-end since D7/D6 self-stamp dropped). Stale-worktree-executor recurrence (bot_completion + merge_lock notations absent from phase-5-frozen executor; both degraded gracefully) |

## Snapshot-2 §5: struck defect rows (resolved, verbatim)

- ~~Era-stamp placeholders merged unresolved~~ → SYMPTOMS SHIPPED #881; MECHANISM SHIPPED plan-16
  D3a (#885) as `project:finalize-step-era-stamp-fill`. Mechanism did NOT self-apply on plan-16
  (D6/D7 self-stamp dropped + manifest-bootstrap gap, merged into `2026-06-21-01-001`) → lesson
  `2026-07-11-09-001` retained until a composed-manifest firing (→ HANDOVER §6 watch).
- ~~Post-merge finalize steps cannot edit source~~ → SHIPPED plan-16 D3b/D3c (#885):
  `source-edit-pushability.md` pre-merge contract + re-applied version-aware-bundle-path
  promotion; era-stamp-fill is the reference implementation.
- ~~Composer emits unresolvable step keys → finalize hard-block~~ → SHIPPED plan-16 D1/D2 (#885):
  compose-time fail-loud (`error: unresolvable_step`) + idempotent `RETIRED_STEP_KEY_RENAMES`
  sync-defaults migration (`automated-review`→`plan-marshall:automatic-review`).
- ~~`pre-submission-self-review` dead at compose~~ → SHIPPED plan-14 D5 (#877), acceptance PASSED
  on #884 (present + ran + caught 1 drift finding).
- ~~Merge-queue `--delete-branch` flag family~~ → SHIPPED plan-14 D1 (#877), verified live
  self-merge; lesson `2026-07-10-23-001` retired.
- ~~600s ci-wait budget vs long jobs~~ → SHIPPED plan-14 D2 (#877): opt-in `--adaptive` on all 3
  raw wait sites; ratchet converges after one full-duration wait (542s→~880s observed).
- ~~Merge-lock holder liveness~~ → SHIPPED plan-14 D3 (#877): `holder_has_live_worktree` guard;
  sibling `holder_is_dead` sink hardened by #883 (lesson `2026-07-12-19-001` retired).
- ~~Project-local `module: null` → whole-tree build fallback~~ → SHIPPED plan-7 D1 (#887):
  which-module `paths.sources`∪`paths.tests` containment + `.claude/skills/**` mapping; retired
  lesson `2026-07-09-04-001`; Gemini caught the root-module tie-break bug → TASK-7.
- ~~Drift metric counts its own detector literals~~ → SHIPPED #882 (premise WRONG — source
  drift=0, regression-test-pinned); true residual = stale cache version dirs → item D/#886
  (acceptance met, drift=0 with orphaned dirs present).
- ~~Bot comments posted after the fetch window merged unhandled~~ → SHIPPED plan-17 (#884):
  fail-closed pre-merge barrier + per-bot completion polling + step-done integrity; DOGFOODED
  LIVE on its own PR (2 late comments caught pre-merge).

## Snapshot-2 §6: closed watches

- plan-14 D5 acceptance → PASSED on plan-17/#884 (self-review present + ran + 1 real finding).
- Recipe Tier-1 no-match watch → fired ×2 (#881+#883), promoted to §5 open defect.
- Run-session bookkeeping drift → 1 skip (#876) / full compliance (#884, #885); kept as watch.

## Snapshot-2 §4: resolved queue rows

A era-fill → #881 · B drift-metric → #882 · C holder_is_dead → #883 · D cache-scanner → #886 ·
16 step-key-hygiene → #885 · 17 review-completeness → #884 · 7 execute-task-tests → #887.
Full landing analyses: §3 rows above + topic memory files.

# SNAPSHOT 3 (2026-07-15) — ROADMAP COMPLETE — content removed at the finale HANDOVER cleanup

**THE CORE TOKEN-OPTIMIZATION ROADMAP IS CLOSED.** The finale — **plan-8 `context-trim` (PR #899,
07-15, 12/12)** — attacked the last three cost drivers (A per-dispatch context floor; B finalize-wait →
one concurrent barrier + detach + D6 before/after measure; C raw-log spelunking → per-signature pytest
traceback + `build parse --failures-detail`), stamped CHECK_ERA, and closed the ledger (D8). All
data-driven cost-driver plans have graduated. What remains after the finale is bounded fixes + one new
capability (see HANDOVER §START-HERE / §4), NOT cost-driver plans. Full detail: archived plan dirs
under `.plan/local/archived-plans/` + topic memories.

## Snapshot-3 §3: shipped rows #888–#899 (verbatim one-liners; full rows = topic memories)

| Plan | PR | One-liner |
|------|----|-----------|
| manifest `_REPO_ROOT` compose-blocker | #888 | (side, cache-resolver class) — see `project_manifest_repo_root_cache_bug_pr888` |
| cache `Path(__file__)` resolver sweep | #889 | (side, cache-resolver class) |
| steward upgrade-verb (item E) | #891 | `upgrade` verb: content-drift CLI + stage/gate emitter + menu/direct exposure; deep/`auto`, 2.8M (6-finalize 46%) |
| domain-multivalue (item F) | #892 | multi-domain init (always_on/file_globs/multiSelect); dogfooded; surfaced+fixed #888/#889 inline (3-PR marathon, 9h52m/3.1M) |
| plan-6 prompt-reachability | #893 | in-leaf prompts→batched envelopes (D1/D2) + execution-context frontmatter (D3) + operator-prompt standard (D5) + **D6 compose-time `execution_tier` guard verified live** + D7 era-fill acceptance PASSED; D4 gating-flip dropped. 4.2M/7h44m |
| cache-resolver hardening (plan H) | #894 | FIX A (find_bundles 3-tier orphaned fallback) + FIX C (generate_executor newest-version) + D3; closes cache-resolver A+B+C; Gemini caught `Path.home()` RuntimeError. 2.5M/4h36m (leanest) |
| lane-unification (plan L) | #895 | kills ci_provider-keyed bot-enforcement guard; finalize selection unified on `lane` knob; automatic-review/sonar = `lane: ask`; ALL steps materialized; drop-when-no-provider. 4.5M/7h47m |
| lane-materialization | #896 | sync-defaults `_materialize_finalize_lanes` (present→effective; new→`off`) + class:core/derived-state IMMUNE to weakening `off` + executor-bootstrap self-heal vs GC-pruned pinned version. 4.7M/8h29m |
| merge-queue bypass-actors | #897 | org-agnostic `bypass_actors` + config-first `merge_queue.bypass_app_id` + self-heal; CodeRabbit caught 2 real bugs; #2 org-wide default 2753519 deferred→steward. 3.2M/2h10m worked |
| steward pass | #898 | landed 4-item steward reconcile (steps-sort + materialized lanes + provisioning stamps); unblocked plan-8 restart |
| **plan-8 context-trim (FINALE)** | **#899** | **12/12 + 2 unplanned (test-compile tree-wide latent break ~234 errs / lesson 12-001; ci-barrier plugin-doctor allowlist). Clusters A/B/C + CHECK_ERA + ledger close. Reviews COMPLEMENTARY: Gemini caught a bug CodeRabbit missed → CodeRabbit caught 13 more (14 fixed / 2 loop-backs). D6 before/after headline UNVERIFIED at archive — pull for verdict. 5.3M/5h28m worked (4-plan 11h idle = operator parking)** |

## Snapshot-3 §5/§6: defects & watches resolved this stretch (verbatim)

- ~~Leaf-backgrounded builds (dominant cost driver, 13 obs)~~ → RESOLVED plan-6 D6/#893 (compose-time
  `execution_tier=orchestrator` guard, verified live). **Residual OPEN (moved to HANDOVER §5): initial-envelope
  call-site gap RECURRED #897.**
- ~~Cache-resolver bug class (A/B/C)~~ → RESOLVED plan H/#894 + #888/#889.
- ~~GC-sweep verification (dated 07-14/15)~~ → PASSED 07-14 (GC deletes stale dirs; 428MB→99M; no prune leg).
- ~~Refine/execute-task unreachable prompts + execution-context tool-frontmatter~~ → RESOLVED plan-6/#893.
- ~~bot-enforcement guard force-adds automatic-review for bots-less repos~~ → RESOLVED plan L/#895.
- ~~Build result carries no structured test-failure detail (raw-log spelunking)~~ → SHIPPED plan-8/#899
  Cluster C (`build parse --failures-detail` verb verified live).
- ~~Finalize wait-loops (sole remaining cost driver, 6 datapoints)~~ → ADDRESSED plan-8/#899 Cluster B.
  **Residual watch (HANDOVER §6): confirm the D6 before/after delta is a real reduction on next landings.**
- ~~nifi `/marshall-steward upgrade` fail (error text owed)~~ → RESOLVED: root cause = executor-bootstrap
  ModuleNotFoundError from GC-pruned pinned version (#896 D4 hardened it); the generate-time format-mismatch
  leg became the executor-version-transition plan (HANDOVER §4, pending).
