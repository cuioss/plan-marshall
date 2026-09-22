# Landing Analysis: PLAN-145 — Publish the missing parser seams

epic: test-quality
workstream: WS-03
pr: [#1395](https://github.com/cuioss/plan-marshall/pull/1395) — merged `8d8c17bd19808c12d25546fb7987b5c6103f9f49`

> Landing record for one shipped plan. Lives at `landings/PLAN-145.md`. Written by the
> `analyze` verb after verifying claims against ground truth (actual code, artifacts,
> PR state) — a pasted claim is a lead, never a fact. See
> `persona-plan-orchestrator/standards/orchestration-model.md` for the analysis and
> reconciliation contract.

## Deliverable Fidelity vs Spec

The spec staged **six** deliverables, cut to four at the cleanup split (D4/D5 → PLAN-165). What
shipped is **one**, and it is not one of them: the plan's own D1 sweep refuted the premise the
other deliverables rested on, and the plan pivoted to shipping a guard that re-derives the
refutation on every run.

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| D1 — derive the tree-wide `ParserSeamNotFound` set | shipped-as-specified (as a **refutation**) | 118 entry-point scripts swept; 113 reach a seam; the 5 raising are each a deliberate shape. **Modules owed a seam: 0.** Filed through the inbox at the `3-outline` gate, pre-landing |
| D2 — publish seams in `effort_presets.py` and `manage_terminal_title.py` | **dropped — premise refuted** | Both belong to D1's *no top-level CLI* class, not to `ParserSeamNotFound`. Corroborated independently at HEAD `09f92b5e` before this landing: neither file appears in the merge diff |
| D3 — record shape verdicts for `pytest-testing/**`, `persona-module-tester/**` | folded into the shipped guard | The verdicts are now recorded data inside `test/test_parser_seam_coverage.py` rather than prose |
| — | **added-unplanned** | `test/test_parser_seam_coverage.py` (526 lines, new) — the tree-wide coverage guard. This is the plan's entire product and appears nowhere in the spec |

⛔ **Zero of the five declared Expected-Surface entries were realized, and the whole product
landed outside the declaration.** Merge diff — three files, 607 insertions:

| Realized file | Declared? |
|---|---|
| `test/test_parser_seam_coverage.py` (+526, new) | **no** — undeclared tree-root file, the plan's entire product |
| `test/plan-marshall/script-shared/test_conftest_loader_contract.py` (+83) | **partially** — inside the declared `test/plan-marshall/`, but the declaration scoped that entry to "the directory mirroring each changed skill… **only where a D2 seam requires its own test**", and no D2 seam shipped |
| `test/conftest.py` (+1) | **no** — and explicitly excluded: "this plan does not otherwise edit `test/**`" |

Declared and never touched: `effort_presets.py`, `manage_terminal_title.py`,
`marketplace/bundles/**`, `pytest-testing/**`, `persona-module-tester/**` — the entire
`marketplace/bundles/` half of the declaration.

**This is not ordinary under-declaration. The declaration described a different plan.** The
pivot was correct and is well-evidenced; what is missing is that nothing updated the surface
when the pivot happened. This is the second of the two writers of post-staging scope the
standard names — *the plan itself during execute* — and unlike the Step 5b fold it carries no
same-act obligation at all.

## Metrics and Anomalies

- **Tokens**: 6,171,897 total. Finalize alone recorded 3,532,602, of which **2,346,273 (66%)
  bought no new work** — 18 of 34 step firings were re-firings.
- **Duration**: 493,686 s wall (137 h 08 m), created `2026-08-29`, merged `2026-09-04`.
- **Anomalies**:
  - Three CodeRabbit quota-recovery force-pushes each advanced HEAD, and the verdict-currency
    classifier returned `invalidated` for every settle-band step, because none declares a
    `verdict_inputs` surface. ⚠️ **The remedy is already proven in-tree**:
    `project:finalize-step-era-stamp-fill` is the one step that declares that surface, and it
    resolved `preserved` and skipped at zero cost on every re-entry.
  - `scope_creep_check` compared nothing on both phase-5 firings — `could_not_look` /
    `no_baseline_sha`, because `references.json` carries no `plan_creation_sha`. The check ran
    and produced no finding. Scope was confirmed by direct inspection instead.
  - `build_queue` slot release failed four times from inside the worktree (`git rev-parse
    --git-common-dir` timed out at 10 s). **The builds themselves were green** — the failure is
    in the release after the work, so it never surfaced as a red gate.
  - The merge-queue landing wait has no sanctioned pacing primitive: a bare `sleep` is
    harness-blocked, `until`-loops are forbidden by project rules, and the backgrounded
    fallback was killed twice citing low memory with ~19 GB free.

## Routing and Merge Behavior

- **Review**: quorum satisfied with `coderabbit:participated` and
  `cuioss-review-bot:participated_but_empty`; `sourcery` quota-refused for the whole run.
  **CodeRabbit contributed both substantive findings**, each triaged FIX and fixed on-branch:
  `ad7796` (Major) — the AST collector recorded only definition nodes, so a
  `from helper import build_parser` would publish seam 1 while the guard reported the row exempt;
  `4fa036` (Minor) — roster drift was computed in both directions but only *printed*, so a green
  session tolerated a drifted roster.
  ⚠️ **Two review-machinery defects, both already recorded as this epic's watches, fired again**:
  the required/optional split again failed to track measured yield (the sole required bot raised
  nothing; the optional one raised everything), and Sourcery's refusal was mis-filed as a pending
  `pr-comment` finding rather than recognised by the refusal stack — third recurrence of
  `refusal_pattern_drift`, and this time it corrupted the review-retrospective's own numerator
  (a false 0.0 % fix rate for Sourcery).
  ⚠️ The re-review trigger-B heuristic selected the wrong reviewer on two consecutive rounds and
  never reached the bot actually blocking the quorum; both rounds needed an explicit
  `github_re_review re-review --bot-kind cuioss-review-bot`.
- **CI/merge**: all checks green; merged via **merge queue** as `8d8c17bd`. No rebase conflicts —
  `finalize-step-sync-baseline` reported "already current with origin/main, no commits replayed".

### Surface collision — the concurrent pair, measured

PLAN-145 and PLAN-105 were in flight together (see the 2026-09-04 analyze watch: the pair was
never checked, because a resume-from-`parked` bypasses the disjointness gate). Now that PLAN-145
has landed, the pair can be measured rather than predicted:

- **No merge collision occurred.** PLAN-145 rebased cleanly and merged first; PLAN-105 has not
  pushed. The collision risk transfers to PLAN-105's next rebase onto `8d8c17bd`.
- ⛔ **Had the gate been consulted, it would have returned the right answer for the wrong
  reason.** It would have compared PLAN-145's declared `marketplace/bundles/**` against PLAN-105's
  `marketplace/bundles/` claim and sequenced the pair. The real overlap is in `test/` — which
  PLAN-145 declared it *would not touch*. A gate that is right by accident is not evidence the
  gate works.
- ⛔ **Four staged specs now carry premises against files PLAN-145 just changed**:
  `test/conftest.py` is declared by **PLAN-110** and **PLAN-155**;
  `test/plan-marshall/script-shared/test_conftest_loader_contract.py` is declared by **PLAN-160**
  (by name) and **PLAN-155** (by directory). PLAN-160's is the sharpest: that file is one of its
  three named surface entries and it just gained 83 lines.

## Reconciliation Actions

- [x] row `status` → `shipped` — `orchestrator queue --transition PLAN-145 --status shipped`
- [x] row `pr` stamped `#1395` — stamped at the 2026-09-04 analyze, before the landing
- [x] row `landing` stamped — `orchestrator queue --set-row PLAN-145 --field landing`
- [x] row `plan_marshall_plan_id` already stamped `plan-145-publish-the-missing-parser-seams`
- [x] epic.md queue reconciled from status.json; both generated blocks regenerated
- [x] Open Defect *"PLAN-090's D1 was narrower than what was routed to it"* — **retired by
      refutation**: 0 modules owed a seam, and both named starting points are `no top-level CLI`
- [x] Open Defects *"`github_ops` ↔ `_github_pr` circular import"* and *"`credentials.py` at
      52.6 % coverage"* — **re-routed `→ PLAN-145` to `→ PLAN-165`**; they left PLAN-145 at the
      cleanup split and the arrows were never updated
- [x] Watch added — the declaration-describes-a-different-plan finding above
- [x] Watch updated — the concurrent-pair watch, resolved to "no collision; risk transfers to
      PLAN-105's rebase"
- [x] Open Defect added — four staged specs hold stale premises against the three changed files
- [x] resume_anchor updated
- [x] 15 inbox messages drained and archived

## Follow-Ups

- **14 candidate-lesson messages: all discarded, none promoted.** Every one already exists in the
  global corpus — all 28 lesson ids they reference were verified present. Promoting any would
  have duplicated an entry `lessons-capture` had already written. They are recorded here as a
  cluster rather than as 14 ledger items.
- **The re-firing cost finding is the one worth acting on**, and it is the epic's second
  independent measurement of the same shape (PLAN-170 spent 59 % of its budget in finalize). The
  remedy is proven in-tree and cheap: give settle-band steps a `verdict_inputs` surface. **Out of
  this epic's scope** — it belongs to the measurement-instrumentation cluster already recorded as
  a standing out-of-scope signal. Not staged.
- **`refusal_pattern_drift` remedy** — adding Sourcery's verbatim quota phrasing to
  `refusal_patterns` in `automatic-review/standards/sourcery.md`. Named by the plan as owed to a
  follow-up and outside its footprint. Unowned; out of this epic's scope.
- **6 of the retrospective's 12 lessons are reachable only from the global store** —
  `2026-09-04-14-006`, `2026-09-03-19-005`, `2026-09-03-11-007`, `2026-08-25-09-004`,
  `2026-09-04-12-001`, `2026-09-03-22-002`. `2026-09-03-19-005` is the epic-relevant one: it is
  the recorded form of the re-firing cost story. This is the **second** occurrence of the
  misrouting defect already recorded from PLAN-170; the structural fix — give
  `plan-retrospective` the same `orchestrated` / `epic` inputs `lessons-capture` gets — is
  recorded as a recurrence on that defect, not as a new one.
