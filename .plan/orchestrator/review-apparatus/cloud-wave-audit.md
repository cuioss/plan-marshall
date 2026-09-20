# Cloud-wave audit — ingestion of `doc/plans/review-apparatus/` (2026-08-23)

The record of one ingestion: thirteen epic plan specs were exported to `doc/plans/review-apparatus/`
around 2026-08-09, executed as Claude Code cloud sessions between 08-10 and 08-15, audited on 08-20
(PR #1308), and ingested back into this ledger on 08-23.

**This document is the cross-cutting synthesis.** Per-plan detail lives in `landings/PLAN-PR-NNN.md`;
the raw corpus (each run's `plan.md`, `report-01.md`, `verification.md`, `gaps.md`) lives under
`cloud-runs/`. Nothing here restates those — this is only what no single plan's record can hold.

## 1. What landed

All thirteen ran and all thirteen merged. **Zero were abandoned.**

| Cloud | Ledger id | PR | Verification verdict |
|---|---|---|---|
| 010 | PLAN-PR-013 | #1141 (+#1142) | verified-with-gaps |
| 020 | PLAN-PR-023 | #1151 | verified-with-gaps |
| 030 | PLAN-PR-017 | #1157 | verified-with-gaps |
| 040 | PLAN-PR-006 | #1165 | verified-with-gaps |
| 050 | PLAN-PR-021 | #1170 | verified-with-gaps |
| 060 | PLAN-PR-020 | #1182 | **partially-implemented** |
| 070 | PLAN-PR-019 | #1187 | verified-with-gaps |
| 080 | PLAN-PR-010 | #1196 | verified-with-gaps (**refutation**, docs-only) |
| 090 | PLAN-PR-012 | #1204 | verified-with-gaps |
| 100 | PLAN-PR-003 | #1212 | verified-with-gaps |
| 110 | PLAN-PR-005 | #1219 | verified-with-gaps (**premise refuted**) |
| 130 | PLAN-PR-011 | #1239 | **partially-implemented** |
| 120 | PLAN-PR-008 | #1241 | verified-with-gaps |

**Not one verdict was `verified`.** Every run left gaps, and two left enough that the auditor refused
the weaker word. That is the headline finding about the *wave*, distinct from any finding about a plan.

## 2. The gap population

**171 gaps** across thirteen `gaps.md` files. Coverage against the eight staged gap-fix plans, judged
by substance (does a deliverable, executed as written, satisfy the gap's *Done when*):

| | Count |
|---|---|
| full | 154 |
| partial | 17 |
| none | 3 |

The three `none` rows — `010 G5`, `010 G14`, `110 G6` — plus the report-correction halves of
`110 G7`, `120 G2` and `130 G4` form **one cluster with one cause**: every plan touching a seam
excludes landed-run-report corrections by design, and PLAN-PR-031 (the records plan) routes only some
of them. Six record-integrity items, one of them *a named test that does not exist*, were owned by
nobody until this ingestion routed them.

### ⛔ A correction to this orchestrator's own first pass

An initial citation grep over `NNN GM` reported that only 46 of 171 gaps were cited by the 5NN series.
**That figure was wrong and is retracted.** The plans use four incompatible notations —
`070-G1` (550), `` `010` G4 `` (510), `090/G2` (560), `090 G1` (570) — so a single-form grep
manufactures false orphans. Verified by three independent analysts, each of whom refuted the premise
handed to them. **Any coverage grep over this corpus must match all four forms.**

## 3. What the wave taught — standing rules

Rules earned by measurement in this wave, not restatements of gaps.

1. **A test that drives the library is not a test of the pipeline.** Plans 040 and 050 both shipped
   green with explicit discrimination tests, and both surfaces still collapse in production, because
   each test hands the pure function an input the workflow cannot supply. *Every* Done-when on a
   rendering surface must exercise the **step's path**.
2. **Before crediting a discrimination fix, sweep for the producer of its discriminating input.**
   `_grade_comparison` has four grades; `clean` requires `--reviewed-reviewers`; **no writer of that
   set exists anywhere in the tree.** It is a three-valued function in production.
3. **A capability with no caller is not a deliverable.** `assess_deficit` is correct, tested and
   mutation-verified — and invoked by nothing. A § Consumers row says what a command *reads*, not who
   runs it.
4. **"The mechanism exists" is not "the measurement exists".** Two HALT-gated clauses in plan 040 were
   discharged by a proposition adjacent to the one they stated.
5. **A refuted premise is not a clean surface.** Plan 110 wrote "no follow-up owed" over three live
   defects in the files it had itself declared, one of them its own defect statement verbatim.
6. **A refutation's trigger and its closure are separately assessable.** Plan 080's gate fired for a
   real reason and four of six deliverables were then closed as moot, one on a straight *inversion* of
   the plan's own out-of-scope text. **A verify-first gate licenses closing the PLAN, not closing every
   DEFECT it named.**
7. **A "population-complete" derivation that filters through a hand-listed vocabulary is complete only
   over the vocabulary.** `_merge_shaped_roster.MERGE_SHAPED_VERBS` is a frozenset; injecting
   `('pr','queue-merge')` leaves both population guards green. Plan 030 reproduced the same shape with
   a three-element document literal, which cost it two real members.
8. **An argued mutation is not a measured one.** Two structural falsifiability arguments in plan 060
   were measured and both were wrong.
9. **A published null result is dated evidence, not a durable fact.** Plan 030's
   "`--enabled-bots` absent from the whole tree" was true at its merge and is false today.
10. **A run report can contradict the diff it shipped with.** Read `git show {squash} --name-status`
    before believing any footprint claim.
11. **A late review-fix invalidates the prose that same landing wrote.** Three of plan 010's stale
    contract passages were authored by #1141 and superseded by its own review-fix commit.
12. **A proposal-only deliverable decays.** Plan 050's contract proposals were correct at merge and are
    a **regression** if applied today; two later landings grew inside the exact span they replace.
13. **A cloud-lane run can never close a `cloud-plan-lane` gap** — the contract forbids a run governed
    by it from amending it. **Ingestion into the local lane dissolves this**; see §5.
14. **Never trust a count written beside a table.** Plan 120's report took four consecutive fixes of
    that defect and still landed with two miscounted bundles.

## 4. Live defects in merged `main` — carried as Open Defects

Each is claimed by a staged plan; the plan is named. None is closed.

| # | Defect | Sev | Owner |
|---|---|---|---|
| 1 | A currency-subject bot's **second** evidence comment bypasses the currency test and credits an advanced HEAD; the subtraction then clears the stale set too. Reproduced end-to-end against the shipped producer, twice, independently. | blocker | PLAN-PR-024 D1 |
| 2 | `structural_share: 100.0` at `reviewer_coverage: 1/1` the moment the caller-supplied roster shrinks — the named inversion the plan said must not ship. | blocker | PLAN-PR-030 D1 |
| 3 | A landing message is emitted for a run whose merge did not land. `emit-landing` is unconditional; five terminal `branch-cleanup` branches record `done` without merging. | blocker | PLAN-PR-028 D1 |
| 4 | `execution-context.md:23` tells every dispatched leaf that `--plan-id` after a `ci` verb is an argparse rejection. **Ten** subcommands declare it themselves, all `required=True`. | blocker | PLAN-PR-027 D1 |
| 5 | The foreign-PR gate clears on a payload with no `foreign` classification, clears `unpushed`, and passes no `--branch`. A stale remote-tracking ref makes a pushed branch read `unpushed` — and clear. | major | PLAN-PR-028 D4 |
| 6 | A delivered thread reply whose resolve mutation fails is re-sent next round **and** counted `untransmitted`. | major | PLAN-PR-029 D2 |
| 7 | `_is_obvious_noise` reads the CodeRabbit AI-agent block; four of twelve `ignore.low` regexes are unanchored substrings, so a phrase inside the block silently destroys the whole finding. | major | PLAN-PR-029 D1 |
| 8 | The recovery Branch 0 branches on a `cause` neither producer emits, so a Sourcery size refusal is offered a wait. | major | PLAN-PR-025 D1 |
| 9 | `--stale-participation-bots` silently drops a non-admissible pair → `absent` instead of `participated_stale`. | major | PLAN-PR-025 D3 |
| 10 | GitLab `pr merge-queue` issues the merge-train POST **before** any callee-side state read; the shared GitLab preflight fails **open** on an unresolvable project scope while its docstring claims the opposite. | major | PLAN-PR-027 D3 |

## 5. ⭐⭐ The ingestion itself changes what is possible

Three gaps (`050 G4`, `050 G5`, the mechanism half of `060 G6`) were unclosable in the cloud lane for
a structural reason: **`cloud-plan-lane/SKILL.md` is the contract governing a lane run, and a run may
not amend the contract that governs it.** Every plan that met one of these recorded a *proposal* and
stopped. The consequence was permanent: 27 commits have touched that file since plan 050 merged and
none applied its proposal, which is now a regression if applied verbatim.

`050 G4`'s own Task states the escape: *"Then apply — the proposal-only prohibition binds a run
governed by that contract, not a run outside the lane."*

**A `/plan-marshall` plan is not a lane run.** Staged as **PLAN-PR-032**, which re-anchors and then
*applies*. This is the single highest-value consequence of moving the corpus into the local ledger.

## 6. Re-grounding of the eight staged gap-fix plans

None had ever been verified. Re-grounded against `e8324d241` (2026-08-23):

| Plan | Verdict | Deliverables | Must be corrected before emit |
|---|---|---|---|
| PLAN-PR-024 (500) | confirmed | 6 (at guard) | 4 defects; cites a `SKILL.md` section that does not exist; split 2-way recommended |
| PLAN-PR-025 (510) | confirmed | **7 (over guard)** | 7 defects; **README check 3 FAILS**; mis-names an invocation site; D6's Done-when is unfalsifiable as written; split 3-way recommended |
| PLAN-PR-026 (520) | *see §7* | | |
| PLAN-PR-027 (530) | *see §7* | | |
| PLAN-PR-028 (540) | **partially-confirmed** | 7 | **DO NOT EMIT AS WRITTEN.** D0 void; D1's `branch-cleanup.md` edit void; D2 half-landed by #1317 *one day after authoring*; `merge_state` vocabulary wrong (3 values vs the live 5); every count wrong (6→8 sites, 3→5 non-merging, 25→26 steps). Re-author, then split 540a/540b |
| PLAN-PR-029 (550) | confirmed | 6 (at guard) | 5 defects; one Expected-surface path **does not exist** (`test_findings_store.py`); D4's Done-when quotes the landed report inexactly and returns a false green |
| PLAN-PR-030 (560) | **partially-confirmed** | 6 + gate | 4 defects: D4/G12 **names the wrong file** (the dispatched-envelope schema is in `pre-submission-self-review.md`; the file it names already carries the field); D4/G13's real surface is **~25 files, four declared**; D6 edits another plan's directory with no disagreement report. **Split 3-way** (delta / gate-verdicts / count-prose) |
| PLAN-PR-031 (570) | **partially-confirmed** | 5 + gate / **36 sub-items** | 7 defects, see below. **README check 1 FAILS** (zero occurrences of `per the README table`, and no mention of the README at all); § Notes under-enumerates its own epic siblings |

**No miscitation was found in PLAN-PR-031's gap citations** — all 23 in-scope gap ids exist and every
subject is described correctly. *The plan about false citations contains no false citation.*

**But four of its claims about the tree are falsified**, which is the same defect in the other
direction and must be corrected before it runs:

1. **D4 item 5 is falsified.** It asserts exactly one commit touches `marketplace/targets/pr_agent/target.py`
   and derives a two-bucket charter partition. There are **two** (`f5493b43` #1130 and `66b686bf` #1313),
   so the partition has three buckets. *A stale count about to be landed in a contract, by the plan
   whose subject is stale counts.*
2. **D5 item 3 quotes a string that is not in the contract.** It instructs keeping
   "⛔ This is a disclosure requirement, and it is NOT a block" verbatim; that text does not exist. The
   current wording is deliberately **weaker** (condition 6 carves CodeRabbit out), so forcing the quote
   would re-introduce a flat claim the contract has qualified.
3. **D5 item 4's premise is already satisfied.** The lane already enumerates three surfaces
   (`cloud-plan-lane/SKILL.md:1291`, table `:1296-1300` naming *Review summary bodies*) and carries a
   worked example of exactly the 060 failure. The real residual is *why 060's run missed a surface the
   contract already mandates* — a different question.
4. **D3 item 6 mis-describes one of its two targets.** 060's § Residue asserts the **opposite** of what
   the plan says, so the *Done when* is vacuously satisfiable and the instruction would rewrite a
   correct passage. D1 item 3's "five live defects" is likewise wrong — three code bugs, four with the
   missing test.

## 7. Surface overlap — larger than the README states

The exported README's contention section covers `bot-participation-contract.md` and the 500/510 pair
only. Verified additions:

- **`github_pr.py` + `test_github_pr.py` are claimed by THREE plans** — PLAN-PR-024, -025, -029. Code
  plus its pinning tests: a harder collision than the documentation contention the README does flag.
- **`workflow-integration-github/SKILL.md` § `github_pr fetch_findings`** is a third shared contract
  surface with **no split at all** — PLAN-PR-024 D3/D4 and PLAN-PR-025 D2/D6 both write it.
- **A fourth editor of the § Consumers table the README does not name**: PLAN-PR-026 D2's three-valued
  `participation` change invalidates the `finalize-step-review-retrospective` row.
- `phase-6-finalize/SKILL.md`, `ci_base.py`, `_github_pr.py` — shared by PLAN-PR-027 and -028.
- `finalize-step-review-retrospective/SKILL.md` — shared by PLAN-PR-026, -028, -030.
- `branch-cleanup.md` — shared by PLAN-PR-024, -026, -028.
- `coderabbit.md` — shared by PLAN-PR-029 and -031.
- `gitlab_pr.py` — shared by PLAN-PR-029 and -030.

**⛔ Ownership collision to settle before either is emitted:** `030 G7` is claimed by **both**
PLAN-PR-025 D3 and PLAN-PR-027 D5, for the same three invocation sites.

## 8. Plans created by this ingestion

Gaps no staged plan closes, staged as new specs. See each spec for its evidence.

| Id | Subject | From |
|---|---|---|
| PLAN-PR-032 | Apply the `cloud-plan-lane` contract amendments — outside the lane | `050 G4`, `050 G5`, `060 G6` mechanism half |
| PLAN-PR-033 | The foreign-PR gate's blocking population, and Branch F's unreachable recovery | `020 G4`, `080 G5` — both need an operator decision |
| PLAN-PR-034 | A refusal nobody recognises is filed as an ordinary finding | `040 G13` |
| PLAN-PR-035 | The response path drops answers, and nothing measures it | plan 090 residue: 13 of 43 observed PR findings received no posted answer |
| PLAN-PR-036 | The exit-code convention stops at the skill boundary | `030 G6` residual — three docs in this epic's own review path carry no convention |

## 9. Amendments owed to staged specs before emit

Not new plans — corrections to specs already staged. **Each is a pre-emit obligation.**

1. **PLAN-PR-029 D2** — add `070 G1`'s third requirement: persist resolve state separately
   (`resolve_pending` or equivalent) and add a resolve-only retry branch. As written, 550 enacts the
   half `070 G1` explicitly warns against and its Done-when certifies the result.
2. **PLAN-PR-026 D4** — its worked example is character-for-substance the string `040 G10` forbids;
   restore the `bot_lists_provenance` clause.
3. **PLAN-PR-026 D3** — fold in `040 G15`: change the `min_deficit` default *or* defend it in the
   contract with a pinning test. A run-report proposal is neither.
4. **PLAN-PR-025 D5** — add `010 G14`'s wiring test and `010 G10`'s second cold-read question.
5. **PLAN-PR-025 D6** — add `010 G4`'s three test-prose passages; narrow the Done-when carve-out to
   contract-document passages only.
6. **PLAN-PR-024 D2** — tighten the Done-when to `010 G8`'s wording.
7. **PLAN-PR-031 D2** — add `120 G2` and `130 G4`'s report halves as further items.
8. **PLAN-PR-027 D2 / D4** — widen `030 G3`'s test clause beyond `create-pr.md`; add `060 G8`'s two
   missing record fields.
9. **PLAN-PR-028** — re-author wholesale (§6).

## 10. Epic-level open items, deliberately not plans

- **`020 G6`** — that an executing agent can ignore correct prose is the house convention for all eight
  `phase-6-finalize` scripts, not a defect of one gate. An epic-wide architectural question.
- **`130 G18`** — a mutation sweep over four test suites (~80 tests). Real work, nobody scheduled;
  folded into PLAN-PR-031's split rather than staged separately.
