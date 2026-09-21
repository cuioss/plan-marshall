# PLAN-08: Finalize Dispatch-Audit Integrity

epic: test-suite-quality
workstream: WS-03

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> See `persona-marshall-orchestrator/standards/orchestration-model.md` for the hand-off contract.

## Objective

Repair the finalize dispatch-audit chain so a dispatched finalize step actually emits its `[DISPATCH]`
audit line, and so a finalize step that was promoted to a `bundle:skill` (and thereby classified
DISPATCHED) can still fire the nested dispatch/audit its own workflow requires. Today the audit is
inoperative for the phase it guards: this epic observed **zero `[DISPATCH]` lines across finalize's
dispatched steps in three consecutive plans** (PLAN-02, PLAN-03, PLAN-05), which makes the
dispatch-audit's inverse-coverage check unable to detect an inline-where-dispatch-was-required
violation.

## Verified-open / to-verify inputs

| Lesson | Claim | Status |
|--------|-------|--------|
| `2026-06-24-10-001` | Dispatched finalize step (plugin-doctor) reached terminal `done` with **no `[DISPATCH]` emission** — ran inline where dispatch was required | **recurrence-confirmed open** (observed PLAN-02/03/05) |
| ~~`2026-07-22-20-006`~~ | ~~`pre-submission-self-review` DISPATCH-formula unfirable from the leaf~~ | **STRUCK 2026-07-27 — THIS LESSON ID DOES NOT EXIST.** `manage-lessons get` returns `not_found`. The orchestrator carried the ID from a stale memory note and serialized it into this spec without resolving it against the store. There is nothing to verify and nothing to retire. Refine correctly caught it |
| `2026-07-13-00-001` | `automatic-review` promoted to a `bundle:skill` step is classified DISPATCHED, becoming a leaf that **cannot fire its own nested verification-feedback Task dispatch** | verify at outline |
| `2026-07-13-12-003` | `automatic-review` marks `mark-step-done` with the **fully-qualified step name instead of the manifest's bare key**, stranding the canonical record at `loop_back` | verify at outline |
| `2026-07-24-13-001` (residual dimension) | The pre-push gate runs only **bundle-scoped** `quality-gate {bundle}` (mypy + ruff + SPDX), never a whole-tree `quality-gate`, so the **marketplace-wide plugin-doctor static-analysis pass is un-gated locally** | **OBSERVED open** — verified in the live lessons store 2026-07-26; the lesson's own body records this dimension as still open after PLAN-07 closed its `test-compile` dimension |

D1–D3 are one family: a finalize step whose *dispatch topology* is wrong — either it does not emit the
audit that proves it dispatched, or being itself a dispatched leaf it cannot fire the nested dispatch
its workflow depends on. The bare-key strand (`2026-07-13-12-003`) is the record-keying corollary and
was noted as NOT cleanly closed by PLAN-20's canonicalize work — confirm its current state first.

**D4 is a deliberate, operator-authorized addition from a different family** (gate scope, not dispatch
topology), folded here on 2026-07-26 because it lands in the same `phase-6-finalize` gate machinery
PLAN-07's D4 just edited and shipping it separately would mean a second plan through the same file.
The orchestrator flagged that this overrides the original spec's off-limits clause; the operator
decided to fold. The off-limits clause below has been **narrowed accordingly** rather than left
self-contradictory — it still bars a general finalize sweep.

## Deliverables

1. **RE-SCOPED 2026-07-27 (refine finding, orchestrator-corroborated): the loop-level fix HAS landed —
   fix the two named stragglers and add a population-derived detector.** Reading `2026-06-24-10-001`
   in full confirms its 7th recurrence (observed on PR #1012): the six-times-confirmed whole-phase
   absence is **broken** — 7 of 9 dispatched finalize steps emitted correctly shaped `[DISPATCH]`
   lines. The lesson explicitly instructs: *"The loop-level pairing advice from the third-through-sixth
   recurrences has evidently been acted on; do not re-apply it wholesale."* **The original broad
   root-cause framing is therefore contraindicated by the lesson itself** — do not re-derive it.
   - **The two stragglers**: `project:finalize-step-plugin-doctor` (Complete 19:27:28, no `[DISPATCH]`)
     and `project:finalize-step-review-retrospective` (Complete 20:47:33, no `[DISPATCH]`). Both left
     `[STATUS] (plan-marshall:execution-context.{step}) Complete` surrogates, so both are provably the
     **benign instrumentation-omission mode** — the dispatch happened, the line was skipped. Route them
     through the same emit seam the other seven use.
   - **The detector must be POPULATION-DERIVED, not a hardcoded step list.** Enumerate the DISPATCHED
     roster from `phase-6-finalize/standards/dispatch-inline-split.md` and assert each entry emits. A
     test hardcoding today's nine steps passes vacuously the moment a tenth is added — precisely the
     guard-population-defined-by-the-absent-artifact archetype of lesson `2026-07-26-22-005`, and the
     vacuous-guard family this epic keeps surfacing.
   - **HYPOTHESIS (verify first — it may collapse two fixes into one).** `phase-6-finalize/SKILL.md`
     carries **three** `[DISPATCH]` emit sites of **inconsistent form**: `:584` and `:855` give a
     concrete copy-pasteable `manage-logging work --message "[DISPATCH] …"` bash block, while `:1160`
     (the wait-region unified triage hook) is **prose only** — *"Emit the standardized `[DISPATCH]`
     work-log line (see …)"* — sitting between concrete command blocks for its own steps (1) and (3).
     If omission correlates with instruction **form** rather than the `project:` prefix, it explains
     the anomaly the lesson flags (project-prefixed `finalize-step-lessons-housekeeping` DID emit, so
     *"the family hypothesis does NOT hold cleanly"*) and predicts a **third** omitter,
     `wait-region-unified-triage` — which the lesson's 4th recurrence does list among steps with no
     `[DISPATCH]` line. **Confirming artifact**: trace which of the three emit sites each straggler's
     dispatch branch routes through. If confirmed, normalize all three sites to the concrete command
     form and the two stragglers plus the triage hook close together. If refuted, fall back to the
     per-step-doc fix the lesson prescribes. **Label: HYPOTHESIS — the orchestrator did NOT trace the
     routing.**
2. **RE-SCOPED 2026-07-27 (refine finding, orchestrator-corroborated): the topology defect is ALREADY
   FIXED — close it as verified, and land only the three named residues.** Refine read the current
   code and the orchestrator independently confirmed all four targets `2026-07-13-00-001` names:
   `automatic-review` is **FIND-only** with zero nested `Task:` (`SKILL.md:52,75`), triage having moved
   to the dispatcher-owned unified wait-region dispatch (`dispatch-inline-split.md:19-20,31`) — that is
   the lesson's own **corrective direction 2, implemented**; `pre-submission-self-review` splits
   correctly (`workflow/pre-submission-self-review.md:33`, `Task:` issued from dispatcher context at
   `:170`); `sonar-roundtrip` is likewise FIND-only (recurrence 2's directive); and
   `finalize-step-simplify` carries no nested `Task:` (recurrence 3). **No topology work remains — do
   not hunt for another instance.** What DOES remain are three residues the lesson's own corrective
   action names and which no one closed:
   - `automatic-review/SKILL.md:9` still declares `allowed-tools: Read, Bash, Task, AskUserQuestion,
     Skill`. The lesson says verbatim: *"remove `Task` from `automatic-review/SKILL.md` frontmatter
     `allowed-tools:` if the body no longer dispatches."* It no longer dispatches. `AskUserQuestion` is
     likewise declared while `SKILL.md:241` states the leaf does not fire it — assess both, remove what
     the body genuinely cannot use.
   - `ref-workflow-architecture/standards/agents.md:135` still cites the pre-promotion path
     `phase-6-finalize/workflow/automated-review.md` (renamed to `automatic-review/SKILL.md` at
     promotion) — the lesson names this fix explicitly.
   - `pm-plugin-development/skills/plugin-doctor/references/rule-catalog.md:350` cites the same dead
     path.

   Record the verification finding (topology confirmed correct at four sites, with the evidence) as
   part of the deliverable — a verified-already-fixed result is a real outcome here, not a no-op.
   **Retirement gate:** `2026-07-13-00-001` retires only if all three residues land; if any is left,
   TRIM the lesson to it rather than retiring, exactly as #1012 did with `2026-07-24-13-001`.
3. **RE-SCOPED 2026-07-27 to the OMITTED-CALL half only** (`2026-07-13-12-003`). Its 7th recurrence
   partitions the class, and the wrong-key half is **absorbed**.
   - **Mechanism — note the direction, it is actionable.** The canonical form is the **BARE** key.
     `manage-execution-manifest/SKILL.md:258` documents `PROMOTED_BUILTIN_STEP_IDS` mapping
     `plan-marshall:automatic-review` → `automatic-review`, so the fully-qualified promoted alias
     normalizes **down** to bare; `compose` fails loud with `non_canonical_step` on any non-canonical
     emitted id (`SKILL.md:178`); one shared resolver (`script-shared/scripts/_step_key_canonical.py`)
     backs `mark-step-done`, `assert-step-recorded`, and every manifest boundary. **Do NOT rewrite any
     step doc toward the fully-qualified form — that is away from canonical.** (Refine reported this
     inverted, as "the manifest now carries the fully-qualified key"; the conclusion held but the
     direction did not.)
   - **What survives — the omitted-call variant** (lesson's 2026-07-21 `platform-agnostic-waiting-standard`
     recurrence): a dispatched leaf does its work, returns `status: success`, and never calls
     `mark-step-done` at all. Key normalization cannot fix a write that never happens, and this half
     costs strictly more than the wrong-key half — a full **re-dispatch** of the step's envelope
     rather than a reconcile.
   - **Fix as a structural invariant**, per the lesson's own durable corrective: (a) workflow bodies
     land the terminal `mark-step-done` **before** composing their return TOON, never as a final prose
     step a leaf can skip while still returning `success`; (b) the dispatcher treats a `status: success`
     return that fails `assert-step-recorded` with `step_record_missing` as a **contract violation
     attributable to the leaf**, not a condition to silently reconcile past. Regression test: a leaf
     cannot return `success` without its record landing.
   - **Pair with D1, do not duplicate it.** D1 and D3 are two halves of ONE completion handshake on
     opposite sides — D1 dispatcher-side (`[DISPATCH]` before spawn), D3 leaf-side (`mark-step-done`
     before return). Both fail identically: a terminal outcome with no paired record. Expect a shared
     seam and one detector shape.
   - **⚠ Trim housekeeping.** The lesson's 7th recurrence carries a now-**STALE** parenthetical:
     *"(It does NOT cover `bundle:skill` — that prefix is preserved verbatim by design, so the
     `automatic-review` variant remains live.)"* `PROMOTED_BUILTIN_STEP_IDS` closes exactly that gap.
     Do NOT carry that sentence forward as live residue when trimming or retiring.
4. **Close the residual dimension of `2026-07-24-13-001`: make the whole-tree `quality-gate`
   dimension reachable from the pre-push gate.** The gate currently loops `quality-gate {bundle}` per
   touched bundle, which resolves to mypy + ruff + SPDX only; the **plugin-doctor static-analysis pass
   attaches to the whole-tree `quality-gate` (no module argument)**, so bundle scoping silently drops
   the dimension. Unlike the `test-compile` case PLAN-07 fixed, a whole-tree run of the *existing*
   local toolchain WOULD have caught it — this is a scope-narrowing variant, not a missing tool.
   Add the whole-tree pass to `pre-push-quality-gate.md` alongside PLAN-07's three-guard chain
   (quality-gate → test-compile → module-tests), keeping the frontmatter `description`, both
   Mark-Step-Complete branches, and both `display_detail` strings in lock-step — PLAN-07 updated all
   five sites together and that is the pattern to match. **Weigh the cost explicitly**: a whole-tree
   `quality-gate` on every push is not free, so if outline finds it too expensive to run
   unconditionally, apply the escalate-only-on-trigger discipline the module-tests gate already uses
   rather than dropping the deliverable. Note the specific exposure: a finalize step that MUTATES
   source (e.g. `finalize-step-lessons-housekeeping` promoting a rule into a `standards/` doc) edits
   *after* the plan's footprint was scoped, so bundle scoping structurally cannot cover it — that is
   exactly how #1008 lost a round-trip to `no-historical-prose-in-skills`.

## Lessons consumed — retire from the global store on landing

Retire each **only after confirming the plan actually resolves it**; a folded lesson that outline finds
already-fixed or out-of-scope is recorded, not blindly retired.

| Lesson | Resolved by |
|--------|-------------|
| `2026-06-24-10-001` | D1 |
| ~~`2026-07-22-20-006`~~ | **STRUCK — does not exist in the store; nothing to retire** |
| `2026-07-13-00-001` | D2 — retire only if all three residues land, else TRIM to what remains |
| `2026-07-13-12-003` | D3 |
| `2026-07-24-13-001` | D4 — **retire only if D4 closes the whole-tree `quality-gate` dimension.** PLAN-07 already closed this lesson's `test-compile` dimension and correctly left it active on this residue; if D4 lands the whole-tree pass and outline confirms no further dimension survives, the lesson retires in full. If D4 is descoped to an escalate-only form that still leaves a dimension un-gated, **trim the lesson to that residue instead of retiring it** |

## Expected Surface

- `phase-6-finalize` — the dispatch-audit seam / step-execution machinery and the `pre-push`-adjacent
  dispatch classification (D1–D3).
- `phase-6-finalize/standards/pre-push-quality-gate.md` — the gate document itself (D4). **This file
  was edited by PLAN-07 (#1012, `ae0d8d79b`), which added the `test-compile` guard; rebase D4 on that
  shipped three-guard shape rather than the pre-#1012 two-guard text.** The original "distinct from
  PLAN-07's file" note is superseded by the D4 fold — the two plans now DO share this file, but
  sequentially (PLAN-07 shipped first), so there is no concurrency hazard.
- `automatic-review` — the promoted-step dispatch + `mark-step-done` keying.
- Possibly `manage-execution-manifest` / the step-classification code if the DISPATCHED classification
  is decided there — verify at outline.
- Regression tests for each fix (an audit that can be inoperative silently needs a test that fails when
  it is). For D4 specifically: a test that fails if the gate's dimension set narrows again.
- **OFF-LIMITS** (narrowed 2026-07-26 for the D4 fold): unrelated finalize lessons — doc-prose,
  rebase-recovery, sync-baseline, and the general finalize-cost/machinery items. This plan covers the
  dispatch-topology family (D1–D3) **plus the single named gate-scope dimension of `2026-07-24-13-001`
  (D4)**, and nothing else. It is still NOT a general finalize sweep. Also off-limits: re-touching
  PLAN-07's `test-compile` guard, and `build.py` (it resolves to the `unknown` file-type bucket and
  blocks at plan time — lesson `2026-07-26-20-001`).

## Dependencies and Sequencing

- Independent of PLAN-09 → parallelizable.
- Shares the `phase-6-finalize` bundle with PLAN-07 (07: `pre-push-quality-gate`; 08: dispatch
  machinery) — expected file-disjoint; confirm at outline, else sequence.

## Hand-Off Command

```text
/plan-marshall Repair the phase-6-finalize dispatch-audit chain so dispatched finalize steps emit their [DISPATCH] audit and promoted-to-dispatched steps can still fire the nested dispatch their workflow requires — verifying each lesson is still open before acting. Context: this epic observed ZERO [DISPATCH] lines across finalize's dispatched steps in three consecutive plans, so the dispatch-audit's inverse-coverage check cannot detect an inline-where-dispatch-was-required violation. Deliver: (1) make the [DISPATCH] emission a structural obligation — root-cause why plugin-doctor and other dispatched steps reach terminal done with no [DISPATCH] emission (lesson 2026-06-24-10-001) and fix it at the dispatch seam so reaching done inline is itself detectable, not via a prose reminder; (2) resolve the promoted-step leaf-cannot-dispatch class — automatic-review promoted to a bundle:skill step is classified DISPATCHED and becomes a leaf that cannot fire its own nested verification-feedback Task dispatch (lesson 2026-07-13-00-001), and pre-submission-self-review's DISPATCH-formula is unfirable from the leaf that evaluates it (lesson 2026-07-22-20-006) — fix the topology so the nested work is reachable; and (3) fix the bare-key record-keying strand where automatic-review marks mark-step-done with the fully-qualified step name instead of the manifest's bare key, stranding the canonical record at loop_back (lesson 2026-07-13-12-003) — but confirm against the post-canonicalize seam first, it may be partially closed. And (4) close the residual dimension of lesson 2026-07-24-13-001 by making the whole-tree quality-gate dimension reachable from the pre-push gate: the gate currently loops quality-gate {bundle} per touched bundle, which resolves to mypy + ruff + SPDX only, while the marketplace-wide plugin-doctor static-analysis pass attaches to the WHOLE-TREE quality-gate invocation (no module argument), so bundle scoping silently drops that dimension — unlike the test-compile gap, a whole-tree run of the existing local toolchain WOULD have caught it, making this a scope-narrowing variant rather than a missing tool. Add the whole-tree pass to marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/pre-push-quality-gate.md alongside the three-guard chain (quality-gate then test-compile then module-tests) that PR #1012 just shipped — REBASE on that shipped three-guard text, not the older two-guard version — and keep the frontmatter description, both Mark Step Complete branches and both display_detail strings in lock-step, which is the five-site pattern #1012 used. Weigh the cost explicitly: a whole-tree quality-gate on every push is not free, so if it is too expensive to run unconditionally, apply the escalate-only-on-trigger discipline the module-tests divergence gate already uses rather than dropping the deliverable. The specific exposure to close: a finalize step that MUTATES source (such as finalize-step-lessons-housekeeping promoting a rule into a standards/ doc) edits after the plan footprint was scoped, so bundle scoping structurally cannot cover it — that is exactly how PR #1008 lost a push-to-CI round-trip to the no-historical-prose-in-skills rule. Add a regression test for each fix, since an audit that can be silently inoperative needs a test that fails when it is; for deliverable 4 specifically, a test that fails if the gate's dimension set narrows again. Scope to the dispatch-topology family PLUS the single named gate-scope dimension above — do NOT sweep unrelated finalize lessons (doc-prose, rebase-recovery, sync-baseline), do NOT re-touch the test-compile guard #1012 added, and do NOT declare build.py in any deliverable (it matches no _CLASSIFY_PATTERNS entry in build-pyproject's classify_paths so it resolves to the unknown file-type bucket and blocks at plan time — lesson 2026-07-26-20-001). This plan RESOLVES lessons 2026-06-24-10-001, 2026-07-22-20-006, 2026-07-13-00-001, 2026-07-13-12-003 and 2026-07-24-13-001 — verify each is still open, then RETIRE the resolved ones from the lessons-learned store in finalize lessons-housekeeping since the fix consumes them; record (do not retire) any that outline finds already-fixed or out of scope. For 2026-07-24-13-001 specifically: PR #1012 already closed its test-compile dimension and correctly left the lesson ACTIVE on the whole-tree residue, so retire it only if deliverable 4 closes that residue completely and outline confirms no further dimension survives — otherwise TRIM it to whatever remains rather than retiring it. Resolve all build commands through the architecture-resolved executor and read the TOON status and errors after each build call.
```

## Status Trail

- plan_marshall_plan_id: {set at launch}
- pr: {set when the PR opens}
- landing: {set when the landing analysis is recorded at landings/PLAN-08.md}
