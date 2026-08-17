# Run report — test-quality epic re-scoping (run authoring-02)

**Date (UTC):** 2026-08-17    **Branch:** `claude/test-quality-plan-analysis-pzfrly` (harness-assigned, kept as-is)    **PR:** _pending_    **Outcome:** _in progress_

This run executes no plan. Its subject is the **epic itself**: read every landed run report under
`doc/plans/test-quality/`, establish what the executed half actually did and what it repeatedly could
not do, and change the remaining plans and the epic brief accordingly. It follows the precedent of
`report-authoring-01.md`, which reported the epic's original authoring the same way.

The operator asked three questions and this report answers all three, each with the evidence it was
answered from: **do the remaining plans need adapting**, **do we need additional plans**, and — added
mid-run — **are all tests running, and did the suite get slower**.

## Skills loaded

| Skill | Route |
|---|---|
| `cloud-plan-lane` | `Skill:` notation (project-local `.claude/skills/`) — first action of the run |
| `author-cloud-plan` | `Skill:` notation (project-local) — the authoring judgement this run's deliverable is governed by |
| `plan-marshall:ref-code-quality` | bundle path — always-load |
| `pm-plugin-development:plugin-script-architecture` | bundle path — always-load |

The conditional skills were **not** loaded, and the reason is stated rather than glossed: this run's
whole surface is Markdown under `doc/plans/`. It writes no Python, no `SKILL.md`, no `.adoc`, and
touches nothing under `marketplace/bundles/`, so none of `pm-dev-python:pytest-testing`,
`pm-dev-python:python-core`, `pm-plugin-development:plugin-architecture` or `pm-documents:ref-asciidoc`
governs anything it may edit. No skill was unobtainable by both routes.

## Deliverables

This run's deliverables were derived from the analysis rather than handed to it, so they are stated
here with what each was derived from.

| # | Deliverable | Commit | State |
|---|---|---|---|
| D1 | Analyse all ten landed reports across plans `010`–`060` | — | Done — § "What the reports say" |
| D2 | Three new plans for work no plan owned: `090`, `100`, `110` | `d1fdb3e` | Done |
| D3 | Re-scope the two unstarted plans `070` and `080` | `0acc98e` | Done |
| D4 | Reconcile the epic brief `README.md` with what four runs measured | `8389fb9` | Done |
| D5 | Record, in each landed report, where its open findings went | `053501b` | Done — on the operator's explicit instruction |
| D6 | This report | this file | Done |

### The tension D5 carries, declared rather than hidden

The lane's Step 8 bridge rule says a run records **nothing outside its own plan directory** — no
ledger, no status file, no other plan's directory — while permitting a *declared-deliverable* edit to
a shared lane doc. D5 appends a dated disposition section to six landed reports in six other plan
directories. That is squarely inside the shape the rule restricts.

It is done because the operator instructed it directly: *"in case you handle some of the reports
findings: document that in the reports as well."* It is declared as a deliverable rather than
performed as bookkeeping, each appended section is marked with its date and its author-run, and
nothing above it is revised — the appends record what happened next, they do not rewrite a historical
record. The epic README additionally carries a residue index so the same information exists in one
place a run can read without opening six reports. **Reported as a deliberate deviation, not as
compliance.**

## What the reports say

Ten reports were read in full: `010` run 01, `020` run 01, `030` runs 01–02, `040` run 01, `050`
runs 01–02, `060` runs 01–03 — plus the epic's own `report-authoring-01.md`, which is not one of the
ten.

### Answer 1 — yes, the remaining plans need adapting, and the evidence is unanimous

**Every line floor in the epic is unreachable, and four runs said so independently.**

| Plan | Floor | Achieved | What its own report concluded |
|---|---:|---:|---|
| `030` | 30% | 2.56% | *"the plan's premise for this floor is refuted by measurement"* — and recommended re-deriving for `040`–`080` |
| `040` | 25% | 0.581% | *"on this slice a 25% line reduction is not achievable from prose"* |
| `050` | 20% | 0.52% | the shortfall is *"entirely unfinished scope, not a quality compromise"* |
| `060` | 25% | 0.72% | *"The 25% figure appears to have been set from the corpus-wide profile rather than this slice's"* |

Re-derived here for all six slices, the arithmetic is sharper than any single run could see: **three of
the six floors exceed that slice's entire comment-and-docstring volume**, so deleting every comment
and every docstring would still fall short — and **B3** forbids deleting the rationale at all. `080`'s
25% floor is ~15,100 lines against ~13,400 of total prose. The floors are retired epic-wide; a run now
reports its line delta as an observation.

**The module-budget split never happens.** `010` landed `test-module-line-budget` over **315**
violations. Re-derived today, after four reduction plans: **313**. The other two rules those plans
touched moved hard — preamble boilerplate 370 → 179, historical prose 254 → 81 — so this is not four
runs achieving nothing. It is one deliverable, sequenced last by all four for the same sound reason
(fixture work changes which modules are over budget), never reached by any of them, because a cloud
run completes **two to three** code deliverables and a fifth deliverable does not happen.

**The same partition defect was found four times and fixed zero times.**
`test/pm-code-intelligence/` was added mid-epic, belonged to no plan, and halted `030`, `040`, `050`
and `060` in turn. Each escalated; each was told to proceed. `060`'s own report named the reason the
cycle repeated: its claim was *"a decision about **this run**, not a durable partition fix."* The
README's exclusion list was also short by two entries the whole time.

**And a recorded finding had nowhere to go.** Every reduction plan is correctly forbidden from editing
`marketplace/bundles/**` and `test/conftest.py`, and correctly records what it finds there instead.
Nothing owned the records. `060` measured 27 `parse_ns` conversions blocked on production modules that
publish no parser seam and wrote that a published `build_parser()` would unblock all fifteen of one
group — and no plan could publish one. (That report's G3 row quotes "14"; its G8 row
records the subtotal corrected to 15 in `f4bf557`.)

### Answer 2 — yes, three additional plans, each from something the reports could not act on

| Plan | What it owns | Derived from |
|---|---|---|
| `090` harness and rule gaps | The production and harness surface every reduction plan excludes: parser seams, the loader that cannot address a skill-root `extension.py`, the `sys.modules` registration with no guard, the citation matchers that miss two live spellings, and the severity ladder — reported rather than flipped, since verification found the one eligible flip already landed | `020` #15, `030` run-02 F7, `050` run-02 residue, `060` run-02 G3/G4 and run-03 H4/H6, `010` D6 proposal 2 |
| `100` module-budget campaign | All 313 over-budget modules, one slice per run, measured against the budget and never against a line target | The 315 → 313 measurement, and four reports each recording their split deliverable unstarted |
| `110` every test runs, no slowdown | The two run conditions nobody measured — the skipped count and the suite's wall-clock — plus the instruments and the bounded exception list they need | The operator's added question, and the constant `14 skipped` in every landed build-gate section |

### Answer 3 — all tests are not running, and no, the suite did not get slower

**Skipped tests.** Every landed build-gate section ends `… passed, 14 skipped`, from `010`'s first run
through `030`'s second. The passed count climbs; the skipped count never moves, which is the tell that
nothing looked at it. Statically derived here: roughly **60 skip sites** across ~14 distinct stated
reasons, concentrated in `test/sync-plugin-cache/` (~32, gated on `git` and `rsync`) and
`test/pm-plugin-development/` (~12). Most conditions are false in any environment that can run this
build, which is worse rather than better: a guard that never fires buys nothing, and on the one machine
where it does fire it turns a broken environment into a green build. Plan `110` owns closing them, with
a bounded exception list for the genuinely-variable platform cases and a guard that fails when a skip
appears outside it.

**Duration — measured, and the answer is no.** The operator asked whether the changes made the suite
slower and directed that the *last PRs* be analysed rather than a local run performed. The only
instrument comparable across those PRs is GitHub Actions' own timing for the `Run verification` step of
the `verify / verify` job on `main` — the same job, the same runner class, the same command:

| Commit on `main` | Position | `Run verification` |
|---|---|---:|
| `7de3084` | pre-epic (2026-08-14) | **781 s** |
| `24271bc` | two commits before `020` landed — the nearest pre-epic full build | **786 s** |
| `7cadb98` | after every test-quality PR had landed | **788 s** |
| `d1c3153` | later still, after three non-epic PRs | 812 s |

**The epic's entire executed half cost about two seconds**, while the collected count rose roughly
20,066 → 20,330 (+1.3%). There is no regression to investigate or fix. Two caveats, both stated
because the figures are otherwise easy to over-read: the *whole-workflow* duration is a far noisier
instrument (same-day `main` runs range about 9–27 minutes), so the step is what to compare; and the
+26 s at `d1c3153` follows three later non-epic PRs, so it is not the epic's.

What is missing is the instrument, and the risk is ahead rather than behind. `test/conftest.py`'s
`parse_ns` docstring states its own cost — it *"re-executes the script module on every call"* — and
plans `070` and `080` carry roughly **502** and **222** hand-built namespaces against **1** and **0**
`parse_ns` calls, so the epic's largest **B6** conversion has not happened yet; plan `100` will add
several hundred modules, each re-running its own import preamble at collection. Plan `110` builds the
guard before those three run.

## Build gate

`git diff --name-only origin/main...HEAD -- '*.py'` → **empty**. No buildable footprint; the local
build is skipped per the lane's `*.py`-only gate, and the merge queue's `merge_group` run is the net
for a docs-only change. `git status --porcelain` was empty at Step 2 and is re-asserted before each
diff, so the gate's verdict is taken over committed work only.

## Findings

_Recorded per instance as the run proceeds; the verification section below carries the round record._

## Reviewer participation

_Written at the merge gate, from the stored comment bodies across all three surfaces._

## Cost

- **Tokens:** not available to the agent in this session.
- **Wall-clock:** recorded at the merge gate.
- **Population:** one Claude Code cloud session. ⛔ Not comparable to a plan-marshall `metrics.toon`
  total, which counts an orchestrator-plus-agent dispatch tree under a different billing boundary.

## Contract check (Step 9)

_Written at the merge gate, as the last pre-merge commit._

## What have we learned (Step 9)

_Written at the merge gate._

## Residue

_Written at the merge gate._
