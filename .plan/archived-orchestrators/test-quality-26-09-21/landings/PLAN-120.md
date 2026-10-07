# Landing Analysis: PLAN-120 — Derive the Partition and the Budget Attribution

epic: test-quality
workstream: WS-06
pr: #1345 (https://github.com/cuioss/plan-marshall/pull/1345)

> Landing record for one shipped plan. Lives at `landings/PLAN-120.md`. Written by the
> `analyze` verb after verifying claims against ground truth (actual code, artifacts,
> PR state) — a pasted claim is a lead, never a fact. See
> `persona-plan-orchestrator/standards/orchestration-model.md` for the analysis and
> reconciliation contract.

**Sources.** The plan filed `inbox/derive-the-partition-and-the-budget-attribution-016.md`
(`kind: landing`, revision 1), which `landing-check` reports **`complete: true`** — every
required fact key present with a real value, no `n/a` and no `unknown`. Its plan directory is
**archived** at `.plan/local/archived-plans/2026-08-25-derive-the-partition-and-the-budget-attribution/`,
carrying the full metrics, decision log, quality-verification report and 20 retrospective
fragments. ⛔ **This record initially said the directory was "deleted" and the report
"unavailable". Both were wrong** — the conclusion came from one negative lookup at
`.plan/local/plans/` without checking `archived-plans/`, which is exactly the
absence-read-as-measurement error this epic keeps cataloguing. Every *derived* figure below
(populations, partition verdicts, overlap set) was independently re-derived by this orchestrator
against HEAD `00b92fca` rather than read from the producer's claim; where the two disagree, the
disagreement is stated and attributed.

⛔ **A note on drain timing.** The 15 candidate-lesson messages were enumerated at 09:08 and the
landing message was filed at 09:09:17 — *after* that enumeration. A drain that had trusted its
first enumeration as the complete work list would have closed reporting "no landing was ever
filed." The queue was re-enumerated after the promotions and the landing was caught. Recorded as
a Watch, not a defect: the append-only inbox is behaving as designed, and the lesson is that a
drain's enumeration is a snapshot, not a closed set.

## Deliverable Fidelity vs Spec

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| **D1** — parse what is declarative, classify what is not; three classes; no hard-coded plan list; halt on undeterminable | shipped-as-specified | `scripts/_epic_spec_parser.py` (469 lines) + `test_epic_spec_parser.py` (378) and `test_epic_spec_parser_notation.py` (199). Re-run at HEAD: `classify --epic test-quality` returns `specs_total: 21`, `class_tally` **declarative 19 / derived 1 / prose 1** — PLAN-140 derived (as the spec predicted), PLAN-100 prose. The corpus is read from `plans_dir`, so a spec added later is picked up with no script edit |
| **D2** — derive the partition and the attribution; report every disagreement; observe the check failing | shipped-as-specified | `scripts/_epic_partition.py` (331) + `test_epic_partition.py` (357). The observed-failing requirement is met by `test_epic_partition_injected_failures.py` (257), which the report enumerates as **5 demonstrations** including a matched clean-corpus control and two masking controls (`injected_root_span`, `injected_container_span`) |
| **D3** — report both derived sets and what the derivation could not see | shipped-as-specified | `scripts/epic-surface-partition.py` (536) renders **all seven sections** — partition, attribution, disagreements, not_derivable, injected_controls, test_count, provenance — each with the command that produced it |
| **Validation against the 267 baseline** | shipped-modified — and correctly so | The spec said *"re-derive it; do not trust it."* The derivation disagreed, and the plan reported the disagreement rather than silencing it. See § Anomalies |
| **Placement** — script under `marketplace/bundles/**`, tests inside a claimed directory | shipped-as-specified | Landed at `marketplace/bundles/pm-plugin-development/skills/tools-epic-surface-partition/`; tests at `test/pm-plugin-development/tools-epic-surface-partition/`, inside PLAN-080's existing recursive `test/pm-plugin-development/**` claim. No spec needed amending, so the spec's inbox-message escape hatch was correctly not used |

**Scope discipline held.** The spec's Out of Scope named *"editing any spec to resolve a
disagreement this check finds"* as "the single most available wrong move in this plan." The
diff touches **no** spec, no existing test module, and no `.plan/` file: 14 files, all of them
the new skill, its tests, its standard, plus the two registration lines.

**The plan added zero over-budget test modules.** Its 7 new test modules are 160/199/257/284/292/357/378
lines — every one under the 400 budget. On a plan whose subject is the budget, that is worth stating.

## Metrics and Anomalies

The plan directory was deleted at finalize, so the metrics below come from the landing message's
`landing-facts` block and the plan's candidate-lesson messages (producer claims, not
orchestrator-verified figures):

- Tokens: **6,520,174** total (`landing-facts`), which the producer explicitly flags as spanning
  more than one population and **not** a dispatched-subagent total. The narrower dispatched figure
  reported by the retrospective is **5,991,048** — 3.7× the 1.6M error anchor for
  `single_module + feature`. `6-finalize` took **3,572,386** (60%), `5-execute` 1,437,812 (24%);
  finalize consumed 2.5× execute.
- Duration: **91,980 wall seconds** (25.5 h) against 243 *worked* minutes and a 120-minute error
  anchor. `6-finalize` never closed an `end_time`, so the worked figure is a **floor**.
- Deliverables **3/3 done**. Finalize closed **26/26**: the landing message's `archive-plan:pending`
  was true at emission (`emit-landing` is ordered before it) and the step subsequently completed.
  Re-firing: `pre-push-quality-gate` ×6, `pre-submission-self-review` ×4,
  `project:finalize-step-plugin-doctor` ×3 (clean each time, 37 rules, 0 findings),
  `automatic-review` 2 iterations / 7 comments / 3 substantive.
- Gates: whole-tree quality gate green at **22,076 tests**; CI green at `598fc22b`;
  `finalize-step-security-audit` 0 findings; `finalize-step-simplify` applied 7 edits.
- ⚠️ `sonar-roundtrip` recorded "Sonar not configured, no scan performed" — a **structurally
  unmeasured** gate, not a clean one, and it will report so on every finalize in this repository
  until Sonar is configured or the step is dropped from the manifest. Repository-level, not this
  epic's; recorded so the clean-looking row is not read as coverage.
- Footprint: **14 files landed against 10 declared**; all 4 extras inside the plan's own new skill
  tree, 3 of them additional test modules. Not scope creep.
- Re-firing dominated finalize: `pre-push-quality-gate` ×6, `pre-submission-self-review` ×4
  (3 findings-bearing), `project:finalize-step-plugin-doctor` ×3, `ci-verify` ×2, `push` ×2.
- Anomaly — **679,275 tokens are booked as `error` that were not waste.** All three rows are
  self-review rounds that found real defects, including a correctness bug in `_raw_mentions_module`
  that demoted `not_derivable` to `unclaimed` — precisely the conflation the tool exists to prevent.
  A reader of `error_total_tokens` would conclude 19% of the phase bought zero detection; the
  opposite is true. Filed as a candidate lesson and promoted.

### Anomaly: the budget baseline disagreed three ways, and all three are explained

The spec's validation target was **267** at `2cd1a19c`. Four figures now exist:

The plan's branch history was walked commit by commit to reconcile every published figure:

| Commit | Role | Count |
|---|---|---|
| `2cd1a19c` | the spec's baseline, when written | 267 |
| `77db1a0d` | the branch's **pre-rebase** base | **270** |
| `91bbe747` (#1342) | the **post-rebase** base — `sync-baseline`'s "1 upstream commit" | **277** |
| `598fc22b` | the plan's own tip | **277** |
| `00b92fca` | merge HEAD, after #1343 and #1344 | **279** |

⛔ **This settles the plan's headline "+4 delta" claim, and not in its favour.** The rebase moved
its own baseline by **+7** before it ever pushed, so the spec's 267 was never the right
comparand. The honest delta at its tip was **277 − 267 = +10**, not +4.

⛔ **The reported 271 reproduces at NO commit in the chain** — not the pre-rebase base (270),
not the post-rebase base or its own tip (both 277), not merge HEAD (279). Its own seven test
modules were under budget at every commit checked, so they do not explain the +1 over 270 either.
The figure was measured mid-run against a tree that no longer existed by the time it was
published, and was never re-derived before the PR description quoted it. **This is the same
disease the epic keeps cataloguing** — a measured number going stale between measurement and
publication — landing this time in the report of the plan built to measure things.

At HEAD, three mutually independent methods agree exactly on **279**: the doctor's own
`rules_run` tally, a `git ls-tree` + `wc -l` sweep, and the landed tool's own `attribution` run
through the executor. The +9 over `77db1a0d` is attributable per instance and **none of it is
PLAN-120's**: 7 modules from `91bbe747` (#1342), 1 from `dfabe3d8` (#1344), 1 from `1169fb5b`
(#1343).

The other three rules moved in the same window: preamble-boilerplate **107 → 110**,
docstring-historical-prose **201 → 205**, subprocess-pythonpath **15 → 15** (unmoved).

### ⛔ Anomaly: the attribution is degenerate, and this is the epic's problem, not the tool's

The tool works. Its answer is unusable:

```
partition:   claimed 2 | unclaimed 0 | multiply_claimed 1057 | not_derivable 0   (of 1059)
attribution: buckets[1] — <multiply-claimed>, 279
```

**Every one of the 279 budget findings lands in a single bucket.** The per-slice attribution
D2 promised — 030:40, 040:57, 050:3, 060:55, 070:62, 080:49 — cannot be reproduced, because
**seven whole-tree `test/` root claims** across five specs swamp every slice claim:

| Plan | Root claim | Is it really an ownership claim? |
|---|---|---|
| PLAN-130 | `test/` | **Yes** — the spec states "this plan crosses the whole partition by construction" |
| PLAN-135 | `test/` | **Yes** — same, stated identically |
| PLAN-105 | `test/` | Probably not — needs adjudication |
| PLAN-120 | `test/` | **No** — parsed from "that script's tests, under `test/`", a *collection constraint*, not a claim |
| PLAN-160 | `test/**` ×3 | **No** — and the triplication is itself a parse artifact |

So the derivation is honest and the corpus is what is broken. The remedy is orchestrator work
(adjudicate and narrow the five root claims), plus one tool-side question: whether an incidental
prose mention of `test/` should resolve to a whole-tree claim at all. Both are recorded below.

## Routing and Merge Behavior

- Review: `review_decision: none`; no blocking bot findings survived to merge. The run reported
  two review-side defects it hit — a Sourcery refusal phrasing matching no registry pattern, and
  bot STATUS bodies filed as pending findings — both filed as candidate lessons and promoted.
- CI/merge: PR **#1345 merged** to `main` from `feature/derive-the-partition-and-the-budget-attribution`
  (verified via the CI abstraction, `state: merged`). Squash through the merge queue.
- **No surface collision.** PLAN-120 ran alone against a held-open slot 2, and nothing rebased
  against it. The decision to hold that slot rather than fill it is retrospectively confirmed:
  the plan did land in `marketplace/bundles/**`.

### The conditional overlap resolved LIVE, as recorded

The epic's queue annotation carried this as a HYPOTHESIS with a named confirm/refute artifact.
**Confirmed.** The script-architecture standard placed the checker under
`marketplace/bundles/{bundle}/skills/{skill}/scripts/`, and the tool's own provenance section
derives `overlap_live: true` with **18** overlapping entries. One prediction was wrong and is
corrected: the overlap covers **PLAN-010 / PLAN-090 / PLAN-105 / PLAN-145 / PLAN-165** —
**PLAN-160 carries no bundle-tree claim at all**. PLAN-010 and PLAN-090 are landed, so the live
constraint among staged plans is PLAN-105 / PLAN-145 / PLAN-165. With PLAN-120 shipped, the
tree is released and the constraint no longer gates emission.

## Reconciliation Actions

- [x] row `status` → `shipped` — `orchestrator queue --transition PLAN-120 --status shipped`
- [x] row `pr` stamped — `#1345`
- [x] row `landing` stamped — `landings/PLAN-120.md`
- [x] row `plan_marshall_plan_id` stamped — `derive-the-partition-and-the-budget-attribution`
- [x] epic.md queue reconciled from status.json
- [x] Open Defect **refuted and retired** — "`test/pm-plugin-development/cloud-plan-lane/` claimed
      by no spec". The derivation reports `unclaimed: 0`; that module is claimed by PLAN-080's
      recursive `test/pm-plugin-development/**` glob, plus PLAN-110/130/135/140. The defect as
      stated was **wrong** and is retired with its refutation recorded
- [x] Open Defect **opened** — the degenerate partition (1057/1059 multiply-claimed; seven root claims)
- [x] Open Defect **opened** — two ADR drafts stranded awaiting an operator decision
- [x] Watch **opened** — a drain's enumeration is a snapshot; the landing arrived after it
- [x] Watch **confirmed a third time** — conformance drift (+9 budget, +3 preamble, +4 prose in one window)
- [x] 16 inbox messages drained and dispositioned (15 promoted, 1 landing reconciled)
- [x] resume_anchor updated
- [x] START-HERE and Ordered Queue blocks regenerated — `orchestrator resume-summary`

## Follow-Ups

- **Adjudicate the five whole-tree root claims** — the single highest-value action this landing
  surfaces. Until they are narrowed, the attribution the epic commissioned returns one bucket and
  no campaign run can be sized from it. Staged as **PLAN-170** (WS-06).
- **PLAN-120's own spec is one of the offenders** — its "under `test/`" line parses as a whole-tree
  claim. Since PLAN-120 is now shipped and its spec is history, this is fixed by narrowing the
  *parser's* reading, not the spec. Folded into PLAN-170.
- **The 279 population supersedes every count in the corpus.** PLAN-135 (107 → 110) and
  PLAN-140 (270 → 279) carry figures now stale by one window; both re-scoped in place.
- ⛔ **Two ADR drafts are stranded and need an operator decision.** `adr-propose` produced them but
  the step mandates operator confirmation and a dispatched leaf cannot fire `AskUserQuestion`, so
  they were neither created nor discarded as "none proposed". This is the one follow-up that
  cannot be resolved inside the epic — it needs the operator.
- 15 framework candidate lessons promoted to the global corpus (`2026-08-25-09-001` … `-015`) —
  none are test-quality subject matter, and none change this epic's scope.

## Residue the Producer Carried as Prose

The landing message names five facts no finalize step recorded as typed data. Three are
**absent measurements wearing the shape of clean ones**, which is this epic's own recurring theme:

- **`scope_creep_check` returned `reason: no_baseline_sha`** — its `residual_count: 0` is an
  ABSENT measurement, not a clean one.
- **Scoped `plugin-doctor` structurally cannot evaluate cross-skill rules** whose finding anchors
  outside `--paths`. Its clean verdict on all 3 firings covers skill-local rules only; whole-tree
  CI was the real check, and it passed.
- **`301 candidates examined` is a volume, not a coverage number** — the self-review pass reaches
  internal consistency between statements present in the diff, not behaviour under absent inputs.
- The plan spans two sessions; `status.metadata.session_ids` records one.
- Two ADR drafts stranded (above).

### The self-review caught what no bot did, and vice versa

The producer reports a correctness defect its own subject matter predicted: `_raw_mentions_module`
anchored every unresolved span on the module **filename**, so a directory-shaped span could never
match, and every module beneath it fell through to `unclaimed` — manufacturing a partition defect
out of the parser's own limits, the exact merge D2 forbids. Fixed with paired positive/negative
controls, falsifiability executed (3 of 5 controls fail with the fix disabled).

Two channels, neither subsuming the other: pre-submission self-review found **7** defects
including that one, which no review bot found; review bots found **3** the in-house gates passed,
**two of which fall inside `ext-self-review-plan-marshall`'s own declared candidate classes** even
though its pass reported "301 candidates examined, no check matched". That gap is a framework
finding, and it is promoted, not held here.
