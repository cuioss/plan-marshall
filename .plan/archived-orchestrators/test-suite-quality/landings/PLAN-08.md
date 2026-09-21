# Landing Analysis: PLAN-08 — Finalize Dispatch & Audit Integrity

epic: test-suite-quality
workstream: WS-03
pr: #1026 (`f14cb2d079558100f7ce49e5b31ed1670be74da8`, squash-merged via merge queue, 2026-07-27 20:34:21 UTC)

> Landing record for one shipped plan. Lives at `landings/PLAN-08.md`. Written by the
> `analyze` verb after verifying claims against ground truth (actual code, artifacts,
> PR state) — a pasted claim is a lead, never a fact. See
> `persona-marshall-orchestrator/standards/orchestration-model.md` for the analysis and
> reconciliation contract.

## Deliverable Fidelity vs Spec

Every verdict below was checked against the **merged tree and the diff**, never the PR prose —
the standing instruction this epic adopted after #1012's PR body asserted the inverse of what
shipped. The diff is 17 files / +1158 −110 (the operator's "16 files" excludes the generated
`.plan/project-architecture/default/enriched.json`).

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| **D1** — close the `[DISPATCH]`-emission gap | shipped-modified (narrowed, correctly) | Both named stragglers fixed and the prose-only `wait-region-unified-triage` site normalized to a concrete bash block (`phase-6-finalize/SKILL.md:1207+`). Emit fused to spawn at all three sites with identical "ONE indivisible pair" language (`:589`, `:895+`, `:1210+`). The dispatched/inline branch was rewritten to look the step up in `dispatch-inline-split.md`'s roster instead of naming an example — closing the infer-from-example hole. Population-derived detector present as new `test/_shared/_dispatch_roster.py` (68 lines) + `test_dispatch_roster_closure.py` (+283), so the guard reads today's roster rather than a hardcoded list — the `2026-07-26-22-005` vacuous-guard archetype avoided by construction |
| **D2** — promoted-step leaf-cannot-dispatch topology | shipped-as-specified, **and wider than staged** | The already-fixed verdict is recorded as a verification finding rather than converted into manufactured work. All residues closed: `automatic-review/SKILL.md:9` now reads `allowed-tools: Read, Bash, Skill` (both `Task` and `AskUserQuestion` gone). The dead path `phase-6-finalize/workflow/automated-review.md` returns **zero** citations across `marketplace/bundles/` and `doc/` — and the plan found **four** citations where my spec named two, via a marketplace-wide sweep my outline had not asked for |
| **D3** — record-before-return invariant | shipped-as-specified | Invariant bound over **every** dispatched leaf at `agents.md:146`, with two reach-points: built-in (`default:`) steps via the new `phase-6-finalize/SKILL.md:129` paragraph, external steps via `external-step-contract.md` § Required termination. Both partitions bound, neither restating the other. The canonical-form inversion refine reported was correctly **not** acted on — no step doc was rewritten toward the fully-qualified form |
| **D4** — whole-tree quality-gate arm (operator-folded) | shipped-as-specified | Unconditional whole-tree arm added to `pre-push-quality-gate.md` naming all three whole-tree-only dimensions explicitly (marketplace-wide plugin-doctor pass, `.claude/` ruff coverage, `marketplace/targets` SPDX coverage). Kept in lock-step across the frontmatter `description`, the opening contract, the three-guard order sentence, **both** Mark-Step-Complete branches, and **both** `display_detail` strings. Carries an honest-degradation branch that emits a WARNING naming all three un-gated dimensions rather than skipping silently |
| **Dogfooding fix 1** (unplanned) | added-unplanned, correct | D3's own regression test parsed the roster then discarded it — both assertions were global regardless of roster contents, staying green over a real hole (the nine `default:`-prefixed dispatched steps had **no** reach-point to the `agents.md` invariant). Fixed by adding the built-in reach-point and partitioning the roster with a per-partition requirement. The vacuous-guard archetype found **inside the fix for a vacuous guard** — the second instance of that recursion in this repo (after #1013's `_split_bundle_version`) |
| **Dogfooding fix 2** (unplanned) | added-unplanned, correct | `resolve_test_scope` filtered the footprint through `build_map` globs before deriving owning modules; those globs match only Python files, so this plan's own doc-heavy two-bundle footprint resolved to one module and would have scoped the module-tests gate **away from** the bundle whose tests assert on the changed `rule-catalog.md`. Fixed so module ownership is independent of the glob filter (`_test_scope_divergence.py` +41, `test_test_scope_divergence.py` +66) |

**Lesson dispositions VERIFIED against the live store** — the control that is now 4-for-4 in WS-03
at catching false retirements. All four bound lessons return `not_found`, i.e. genuinely retired:
`2026-06-24-10-001` (D1), `2026-07-13-00-001` (D2), `2026-07-13-12-003` (D3), `2026-07-24-13-001` (D4).
The phantom `2026-07-22-20-006` likewise `not_found`, confirming the strike.

`2026-07-24-13-001`'s retirement was **conditional** on D4 closing its residual dimension
completely, and the condition is satisfied: the whole-tree arm is unconditional, not
trigger-gated, and names all three dimensions the bundle-scoped sweep structurally cannot reach.
This is the correct discharge of a lesson the epic had twice declined to retire.

## Metrics and Anomalies

- **Tokens: 3.5 M** — the most expensive plan in this epic by a wide margin (PLAN-04 was 1.90 M for
  a 1-file diff; PLAN-08 is ~1.8× that for 17 files). An error-column outcome for a 6-deliverable
  bug-fix, as the retrospective judged and the operator accepted.
- **Duration: 3 h 37 m worked / 15 h 43 m wall** — a 4.3× wall-to-work ratio.
- **Anomalies** (all operator-reported, causally distinct):
  - A 192 K-token dispatch written off by a `mark-step-done` omission — i.e. **the defect D3 exists
    to close consumed 5.5 % of the plan's own budget while the plan was closing it.**
  - ~47 min lost to an orphaned pytest tree.
  - System load 82–100 from concurrent sessions.
  - Session skill registry pinned at **0.1.1194** while the executor ran **0.1.1222** for the whole
    run — so a plan editing `phase-6-finalize/SKILL.md` was reading a stale copy of it. Worked
    around per-document; the surviving risk is that a stale-read edit could have been composed
    against superseded text. The merged content checks out on every point verified above, so no
    harm is evidenced, but the exposure was real. This is [the plugin-registry-pin / orphan-GC
    inversion] recurring, and a restart clears it.

## Routing and Merge Behavior

- **Review — the narrative's "all three bots reviewed and found nothing" is CONTRADICTED on two
  counts.** Verified via `ci pr reviews` and `ci pr comments` (the only evidence of participation):
  - **Sourcery did not review at all.** It posted a refusal: *"you have reached your weekly rate
    limit of 500000 diff characters."* The machinery handled this correctly — `automatic-review`
    carries a `rate_limited` discriminator and `review_rate_window_await` defaults to `false`,
    which specifies "treat as an ordinary settle and proceed." So **proceeding was by design; the
    defect is in the reporting**, which rendered a detected refusal as a clean review. Do **not**
    read this as a refusal-detector gap — #1021's detector is not implicated.
  - **CodeRabbit did find something, and it is STILL OPEN in main.** Its review posted 1 actionable
    + 3 nitpick comments at 20:35:19 UTC — **58 seconds AFTER the merge commit** (20:34:21 UTC),
    following the operator's manual `/review` at 20:30:17. The actionable finding is real and
    confirmed live: `agents.md:162` now enumerates **four** corollaries, while `:131` and `:174`
    still say *"the other **two** leaf-cannot-do-it cases"*. That is a stale-count drift inside the
    file the plan edited, of the exact archetype the plan exists to close, and it received no
    disposition because it arrived post-merge.
  - **PR-Agent did participate and did publish** (`cuioss-review-bot`, Reviewer Guide, "no security
    concerns / no major issues"), and was triaged with a reasoned accept. Consistent with the
    `publish_output_no_suggestions=true` change — clean reviews are now visible rather than silent.
- **CI/merge**: green; squash-merged via the merge queue. No rebase conflicts, no surface collision
  with any other plan (nothing else was in flight — the epic held at `N = 1`).
- **Merge-queue diagnosis retracted by the plan itself**: finding `fe7069` claimed the enqueue
  silently failed; the PR was queued the whole time. The inference came from `mergeStateStatus`,
  which does not carry queue membership. Retracted and kept as a suppressed record — the right
  disposition. Separately the plan used `gh pr merge --auto` as a diagnostic, which is an **action,
  not a read**; it was a no-op here but it is outside the read-only-probe boundary.

## Reconciliation Actions

- [x] row `status` → `shipped` — `orchestrator queue --transition PLAN-08 --status shipped`
- [x] row `pr` stamped `#1026` — `orchestrator queue --set-row PLAN-08 --field pr`
- [x] row `landing` stamped — `orchestrator queue --set-row PLAN-08 --field landing`
- [x] row `plan_marshall_plan_id` stamped `finalize-dispatch-audit-integrity`
- [x] epic.md Ordered Queue row reconciled from status.json
- [x] Watch **"finalize dispatch-audit inoperative"** RETIRED — D1 closed it; the epic's zero-emission
      observation across three consecutive plans is answered by 10 emitted lines on this finalize
- [x] Watch **"Residual open dimension of `2026-07-24-13-001`"** RETIRED — D4 closed it
- [x] Watch **"Automated review yield is near-zero on this epic's shape"** REVISED, not retired —
      the yield was NOT zero this time; it was misread as zero
- [x] 6 new watches opened (below)
- [x] resume_anchor updated
- [x] START-HERE block regenerated

## Follow-Ups

**Opened as watches, none folded into PLAN-10** (PLAN-10's surface is `plan-retrospective` +
`phase-5-execute`; every item below is finalize/review machinery, so folding them would breach the
disjointness that makes PLAN-10 emittable):

1. **`agents.md` stale corollary count — the only item with a known, live, one-line defect.**
   `:131` and `:174` say "two" where the enumeration is now four. CodeRabbit flagged it; it merged
   unfixed. Fix count-free per the bot's own suggestion.
2. **A post-merge re-review produces findings nobody triages.** The manual `/review` → bot-answers-
   after-merge sequence is structural, not a one-off: `re_review_on_loopback` is `false` (#1029)
   precisely because plain `/review` is a full review, so manual `/review` is the only re-review
   path — and nothing makes the merge wait for it. Either the request must gate the merge or its
   findings must route somewhere post-merge.
3. **A detected bot refusal is reported as a clean review.** `review_rate_window_await=false` is a
   legitimate proceed-on-degradation choice, but the finalize summary must say "Sourcery refused
   (rate limit), not reviewed" rather than folding it into "reviewed, found nothing." Textbook
   confident-signal-hides-a-caveat.
4. **`[STEP] Completed step:` fires for 2 of 17 steps** — the retrospective's own finding, and the
   sharpest of these: it is the **sibling contract in the same file this plan fixed**, left
   untouched. D3 closed `mark-step-done`'s record-before-return while its `[STEP]`-emission twin
   stayed broken next to it.
5. **`[DISPATCH]` audit log now over-counts by one** — the plan's level correction created a second
   `[DISPATCH]`-tagged line, so the log reads 12 dispatches where 11 occurred. Self-reported. The
   irony is load-bearing: the audit log this plan exists to make trustworthy ships with an
   off-by-one, and the mechanism is D2's own archetype — a correction written *beside* a wrong
   record instead of *to* it.
6. **`references.json` is never reconciled after phase 4** — 12 affected files against a merged diff
   of 16/17, and finding `6a2bb2` traces a real mis-classification to that staleness.

Also recorded, unowned (finalize/orchestration machinery, out of this epic's charter): baseline-
reconcile under-reporting overlap; the RESPOND→FIND self-ingestion loop; `worktree-remove`'s 60 s cap
misreporting a timeout as a dirty tree; `adr-propose` present in the manifest despite `lane: off`.

**Epic-level conclusion.** Four defects came from dogfooding, one from a bot, none from Sonar. The
control that works on this epic's shape is **running the machinery against itself** plus orchestrator
corroboration — not automated review. But the corollary is sharper than the standing watch had it:
the bots' yield here was *not* zero, and the plan's summary said it was. Both the refusal and the
post-merge finding were legible in the PR the whole time.
