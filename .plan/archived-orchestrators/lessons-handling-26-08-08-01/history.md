# History: Lessons Handling 26-08-08

slug: `lessons-handling-26-08-08-01` · closed 2026-08-27 · phase `closed`

Frozen record of the FIRST lessons-drain epic. `epic.md` and the rest of the tree remain on
disk untouched — close freezes, never deletes.

## Vision as pursued

Drain the active lessons-learned corpus into the three live sibling epics, so accumulated
lessons become owned work rather than a growing backlog. Pursued as chartered and completed:
203 lessons scanned, every one carrying an auditable disposition, 23 routable clusters
delivered to sibling inboxes, and the active corpus emptied.

The epic was a **router**, not an implementer. It staged no plan specs and launched no plans;
its queue rows were routing decisions. `next` was never usable here and never used.

## Outcome

| | Count |
|---|--:|
| lessons scanned | 203 |
| clusters formed | 24 (23 routable + 1 self-owned retirement) |
| inbox messages delivered | 24 — truthful-signals 16, code-intelligence-substrate 5, review-apparatus 3 |
| lessons retired from the corpus | 203 |
| queue rows | 24, all `retired` |

**Every one of the 24 rows was drained and dispositioned by its destination.** The per-row
outcome is stamped in `status.json`'s `plan_marshall_plan_id` and rendered in `epic.md`'s
START-HERE block.

### How the destinations disposed of them

| Disposition | Rows | Detail |
|---|--:|---|
| Folded, **spec edit made** | 3 | PLAN-LH-11 → `PLAN-TRUTH-059`; PLAN-LH-19 → `PLAN-TRUTH-012`; PLAN-LH-12 → `PLAN-CIS-015` (split made mandatory at the orchestrator tier) |
| Folded into a named sibling spec | 8 | LH-01→TRUTH-067, LH-03→CIS-017, LH-04→TRUTH-045+065, LH-05→PR-005+013, LH-06→PR-011, LH-07→CIS-002, LH-08→CIS-022+3, LH-09→CIS-020, LH-18→PR-018 |
| Accepted as a **lead**, spec edit NOT made | 6 | LH-02, LH-10, LH-15, LH-20, LH-22, and LH-17 (which arrived post-launch and could not be scoped in) |
| **UNOWNED — new spec wanted, none staged** | 6 | LH-13, LH-14, LH-16, LH-21, LH-24 |
| **DISCARDED** | 1 | LH-23, consumer-repo Java/CUI — out of epic scope; belongs in the consumer repos |

⚠ **The row counts above sum to 24 only because LH-17 is counted once, under "lead".** It is
listed in that row's detail because its disposition is a lead that could not be applied, not a
separate class.

## Carried-forward leads

These left the epic unresolved and are **not** discharged by this close:

- ⛔ **The `manage-lessons` header-less-lesson defect (PLAN-LH-24 / msg -016) is STILL
  UNFIXED**, and it got worse. This epic recorded that a lesson with no `key=value` header is
  listable, unmatchable and un-retirable. The 2026-08-26 drain then measured the
  membership-disagreement population at **n=5** (this epic saw n=1), and observed a
  **strictly worse** behaviour: `remove` DESTROYED `2026-08-25-05-001` while returning
  `not_found`, writing no tombstone. Owned by `lessons-handling-26-08-26-01`'s PLAN-LH2-18.
- ⛔ **Six clusters were accepted as leads with no spec edit** (LH-02, LH-10, LH-15, LH-17,
  LH-20, LH-22). The receiving epics hold them in their decision logs; no spec carries them.
  A lead recorded and not scoped is indistinguishable from one forgotten unless someone
  re-reads those logs.
- ⛔ **Five clusters are UNOWNED with a new spec explicitly wanted and never staged** (LH-13,
  LH-14, LH-16, LH-21, plus LH-24). `truthful-signals` recorded "NEW SPEC WANTED" for each and
  staged none.
- ⚠ **LH-23 was discarded, not routed.** The catch-all arm of the three-way rule sent it to
  `truthful-signals`, which correctly judged it out of scope. The open question travels with
  it: whether the practice belongs in `pm-dev-java-cui:cui-http-testing`'s standards or in the
  consumer repo's own CI. **Nobody owns it.**
- ⚠ **The 8 `already-covered` verdicts were never verified** against their covering clause's
  own worked example — the evidence standard `remove --coverage-verdict completely_covered`
  requires. They were retired as `superseded` with the covering clause named and the
  verification recorded as owed. That debt is unpaid.

## Unresolved defect recorded at close

- ⚠ **Audit asymmetry: 202 tombstones for 203 removals.** Lesson `2026-08-07-21-001` could not
  be retired by any sanctioned verb and was removed from the filesystem by operator direction,
  bypassing the tombstone writer. Its record lives in `archive/`, `dispositions.md` § C22, and
  `truthful-signals` msg -016 instead. Recorded deliberately so it is not later found as a
  mystery.

## Watches carried forward

- **`manage-change-ledger` `kind=build` rows were contested** between C02 (→ `truthful-signals`)
  and C03 (→ `code-intelligence-substrate`). Both destinations may plan against that surface.
- **`finalize-step-simplify` scope boundary contested** between C10 (→ `truthful-signals`) and
  C05 (→ `review-apparatus`). They may be one surface.
- **Three documented expected-false-positives in one Q-Gate family.** A gate whose
  expected-failure list keeps growing is being trained to be ignored. Re-check if a fourth
  appears.

## Closing rationale

Closed 2026-08-27 at operator direction, after a reconciliation that established — from the
**siblings' own decision logs**, not from this epic's ledger — what became of all 24 messages.
Before that reconciliation every row still read `staged` with an empty
`plan_marshall_plan_id`, because the epic's final action ("stamp each PLAN-LH-NN row with the
accepting plan id") was never performed when the drain finished.

⭐ **The lesson this epic teaches about itself:** archival of a message at its destination is
the *consume* marker, not a *verdict*. All 24 messages were archived within days of the drain,
which reads like completion and is not. The fold-or-decline outcome existed only in three
sibling decision logs for 19 days, invisible from this ledger, and would have been frozen as
"unknown" had the close been taken at face value.

## Relationship to the successor epic

`lessons-handling-26-08-26-01` is the SECOND drain, not a continuation — the mode contract
opens a fresh dated epic per invocation and never reopens a prior one. It scanned 87 lessons
that accumulated in the 18 days after this epic emptied the corpus (~4.8/day).

⚠ **Two of its 19 cluster slugs are byte-identical to this epic's** —
`doc-contract-divergence` (here PLAN-LH-19, there PLAN-LH2-06) and
`review-bot-participation-and-reliability` (here PLAN-LH-05, there PLAN-LH2-10) — with
near-matches on self-review, plugin-cache, git-worktree, cost-measurement and manage-script
surfaces. The same siblings therefore hold overlapping cluster subjects filed 18 days apart,
and **neither ledger can see the other's messages**. The destinations must reconcile the pairs;
this epic's rows record the first routing, which is why the tree is retained rather than
deleted.
