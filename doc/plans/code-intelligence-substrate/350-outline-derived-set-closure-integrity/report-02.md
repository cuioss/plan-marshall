# Run report — 350-outline-derived-set-closure-integrity (run 02)

**Date (UTC):** 2026-08-18    **Branch:** `claude/derived-set-closure-integrity-3i53aj` (harness-assigned)
**PR:** [#1295](https://github.com/cuioss/plan-marshall/pull/1295)    **Outcome:** completed

> **Verification loop exit:** budget-exhausted, **non-converging** — round 4 found more shipped-surface
> defects than round 3, and an automated reviewer then found one more that all four rounds missed.
> `Outcome` reports the **deliverables**, which are complete; it does not report the loop. Carried in
> the header deliberately, because a stop record a reader has to go looking for is how this distinction
> gets lost — see § "What have we learned", proposal 2, which puts that as a contract change to the
> operator rather than adopting it unilaterally.

This run **continues** run 01, which was halted by operator instruction before the PR cycle. Run 01's
per-deliverable record stays in [`report-01.md`](report-01.md); the state it was halted in is written
up in [`actual-state.md`](actual-state.md). This report covers only what run 02 did.

## How run 01's work was recovered

Run 01 executed on the harness-assigned branch `claude/derived-set-closure-integrity-g7n8x2`, which
that session was bound to. It committed and pushed nine commits and opened no PR. **That branch is
still on `origin`, untouched by this run.**

This session was handed a *different* harness-assigned branch,
`claude/derived-set-closure-integrity-3i53aj`, and the lane contract's rule is that a cloud session
keeps the branch it was assigned — the binding is what makes the run resumable after a VM reclaim.
Continuing on `g7n8x2` would have left every later commit on a branch this session's harness cannot
find. So run 01's nine commits were **rebased onto current `origin/main` and re-pushed as
`3i53aj`**, and the PR is opened from `3i53aj`.

The rebase was required, not cosmetic: `g7n8x2` branched from `eb0124c`, and `main` had since taken
`b199d94` (`chore(cloud-plan-lane): require snapshot-based restore for mutation sweeps`), so the two
had diverged and no fast-forward existed. `b199d94` touches only
`.claude/skills/cloud-plan-lane/SKILL.md`; the rebase was conflict-free, and every commit's tree is
preserved. The commit SHAs therefore differ from the ones `report-01.md` and `actual-state.md`
quote — those documents are corrected to the rebased SHAs rather than left naming commits that are
no longer on the branch under review.

## Verification round budget

Run 01 declared **4 rounds** before its first dispatch and ran three. Run 02 does **not** re-declare a
budget and does not extend it: it executes **round 4**, the final round of the budget run 01 declared,
and the loop ends there. Exhausting the budget is the STOP CONDITION whose autonomous fallback the
contract fixes — everything condition **A** forbids leaving open is fixed regardless of the budget,
and every surviving **B** finding is characterised and disclosed per instance.

## Skills loaded

| Skill | Route | Why |
|---|---|---|
| `cloud-plan-lane` | project-local (`.claude/skills/`) | The run contract; loaded as the first action, before reading the plan. |
| `plan-marshall:ref-code-quality` | bundle path | Always. |
| `pm-plugin-development:plugin-script-architecture` | bundle path | Always. |
| `plan-marshall:persona-implementer` | bundle path | The surface is production code. |
| `pm-dev-python:python-core` | bundle path | The surface is Python production code. |
| `pm-dev-python:pytest-testing` | bundle path | The surface includes Python tests. |

Loaded by **bundle path**, not by plugin notation: the `plan-marshall` plugin is not installed in this
cloud session. No skill was unobtainable by either route.

`pm-plugin-development:plugin-architecture` and `pm-documents:ref-asciidoc` were **not** loaded, for
the reason run 01 recorded: no bundle was structurally added or removed and no `.adoc` file is
touched.

## Deliverables

Run 02 adds no deliverable of its own. D0–D5 were built by run 01 and are recorded in
[`report-01.md`](report-01.md) § Deliverables; run 02's changes to them are only the round-4 fixes
listed under § Findings below.

## Bridge — a write outside this plan's own directory, disclosed

The diff contains one edit under `doc/plans/` outside this plan's directory:
`doc/plans/code-intelligence-substrate/280-outline-plan-scope-derivation-integrity/report-01.md`,
two lines.

It is **a link repair, not a status or bookkeeping write.** Step 3 moved this plan from
`350-outline-derived-set-closure-integrity.md` to `350-outline-derived-set-closure-integrity/plan.md`,
which broke the two links 280's report holds to its arm-A hand-over. Leaving them dangling would have
left 280's report making a false cross-reference — a condition-**A** defect this run's own move
caused. No ledger, no status file, and no other plan directory was touched.

A sweep for the pre-move path — `grep -rn '350-outline-derived-set-closure-integrity\.md'
--include=*.md .`, run at the moment of this claim — returns exactly **one** hit, and it is the
sentence above this one: the pattern quoted in this report's own prose. No live cross-reference to
the pre-move path survives anywhere in the tree, so the repair is complete rather than partial.
⚠ An earlier version of this paragraph claimed the sweep "returns nothing outside `plan.md`'s own
front matter". Both halves were false — the sweep does return a hit, and `plan.md` contains no
occurrence of the string and has no front matter naming it. It was written from expectation rather
than from the command's output, which is the defect this plan is about, committed in the report
that discloses it.

## Build gate

`git diff --name-only origin/main...HEAD -- '*.py'` is **non-empty** — **8 production scripts and 9
test modules**, re-derived by running that exact command at the moment of this claim — so the full
gate applies.

**Per-commit gate.** `./pw quality-gate` ran before **each** of the two `*.py`-touching commits run 02
made — `f11e8b7` (the round-4 fixes) and `8486214` (the reviewer-driven fix) — read from the tools' own
streamed output, since the direct-`./pw` path emits no TOON log. Both runs reported
`Success: no issues found in 414 source files` (mypy production), `All checks passed!` (ruff), and
`>>> quality-gate: SPDX-header check passed`.

**Branch gate — run undisturbed.** Run 01 declined to record its last `SUCCESS` as the gate because a
verification sub-agent's mutation campaign was running on the same tree. Run 02's gate was taken with
nothing else touching the tree: round 4 had reported and exited, its own mutation sweep had restored
from snapshots and `git status --porcelain` was empty, and every fix was committed before the gate
started.

⚠ **This gate measured `117d351`, not the final head.** The reviewer-driven fix `8486214` landed
afterwards, so the local branch gate does **not** cover it. What covers it is (a) its own per-commit
`./pw quality-gate`, (b) the targeted suite run (`test_qgate_closure.py`, 38 passed) plus the mutation
check that the new guard goes red against the raw conversion, and (c) the **CI `verify` run on the
final head**, which is a required context and is what merge-gate condition 1 is read from. Stated
rather than left implicit: re-running the full local gate after every review fix is not what makes the
merge safe here — the required CI context on the exact head SHA is.

| Sub-step | Result, read from the streamed output |
|---|---|
| **quality-gate** | `Success: no issues found in 414 source files`; `All checks passed!`; `>>> quality-gate: SPDX-header check passed` |
| **test-compile** | `Success: no issues found in 770 source files` — the sub-step neither narrower call runs, and the one that failed on run 01 |
| **module-tests** | `20843 passed, 14 skipped in 449.79s (0:07:29)` — `0 failed`, `0 errors` |
| **overall** | `=== verify: SUCCESS ===` |

Read from the output, not the exit code: on run 01 the wrapper exited 0 on a **failing** run, so
`SUCCESS` versus `test-compile failed` is the only signal. `UV_HTTP_TIMEOUT=600` was set on every
`./pw` call; the branch gate exceeds the foreground Bash timeout and was run in the background.

`git status --porcelain` was empty after the gate — the session interpreter is 3.12.3, at or above
the project floor, so this build produced **no `uv.lock` churn** to keep out of a commit.

⛔ **Read the gate for what it is.** The build's own coverage line says SPDX cannot evaluate file
content, plugin-doctor cannot evaluate whether a documented claim is true, `mypy(test)` cannot
evaluate whether a well-typed test asserts anything, and `module-tests` is silent on every input no
test supplies. Round 4 then found fourteen false statements against this green tree — including two
in operator-facing strings that type-check, lint and pass every test while stating something false.

## Findings

Round 4 was dispatched as the final round of run 01's 4-round budget, read-only, with the beyond-diff
sweep, the sweep-and-count rule, the invented-rationale rule, the vacuous-guard rule and the stop
question all put to it explicitly, and with rounds 1–3's own fixes named as a first-class surface. It
returned **fourteen condition-A findings and four condition-B**, recorded per instance below.

⭐ **Eight of the fourteen A findings are in the shipped surface, not in the run's records.** Round 4
was not narrower than round 3 — see § "Stop record".

### A — false statements (fixed; A is not subject to the budget)

| # | Site | What was false | Disposition |
|---|---|---|---|
| A1 | `report-01.md` § D5 | Three false figures in one sentence: **33** tests in `test_qgate_closure.py` (34), "one added to each" of two suites (1 and **2**), total **47** (49). None held even at run 01's own head, and `actual-state.md` already said 49 — the two documents contradicted each other. | **Fixed** in `f11e8b7`; re-derived with `grep -c '^def test_'` against HEAD *and* `origin/main` for the two pre-existing suites. |
| A2 | `report-01.md` § D5 | A promise the document does not keep — "the count is stated per round below" — and round 3's mutant count stated nowhere. | **Fixed.** Round 3's figure (32) and round 4's (19 run, 17 detected, 2 survived) are now stated. |
| A3 | `report-01.md` § D5 | The lead-in "Round 2's **27** cover:" introduces a list of 22 items. | **Fixed** by removing the count from the lead-in: the list enumerates the *behaviours* those mutants reverted, which is not a count of mutants, and it now says so. |
| A4 | `actual-state.md` § 7 vs `report-01.md` § Build gate | The two documents disagree on the branch gate — "ran **four** times" against a three-row table. One is false and a past run's invocation count is not re-derivable from the tree. | **Fixed** by making `report-01.md`'s table the record and removing the restated total, rather than guessing which number was right. |
| A5 | `actual-state.md` § 7 | "The final run's result is recorded in `report-01.md` § Build gate" — that section explicitly declines to record one ("pending a clean re-run"). | **Fixed**; the pointer now names `report-02.md` § Build gate, where run 02 records the gate it actually ran. |
| A6 | `report-02.md` § Bridge | **This run's own defect.** "A sweep … returns nothing outside `plan.md`'s own front matter." Run verbatim it returns one hit, and `plan.md` contains no occurrence of the string and has no front matter naming it. Written from expectation rather than from the command's output. | **Fixed**, and the correction states what the sweep actually returns and that the earlier claim was written without running it. |
| A7 | `report-01.md` § D2 | "emits one finding per declared glob" — a fully enumerated glob emits none, which `test_declared_glob_fully_enumerated_is_closed` pins by asserting `gaps == []`. The owning standard states it correctly; the report was the n−1 site. | **Fixed.** |
| A8 | `report-01.md` § D5 | The exclusion table's lead-in — "every fixture that does **NOT** declare the path its task targets" — excludes its own second row, which does declare exactly that path and deviates because the path is deliberately absent from disk. | **Fixed.** |
| A9 | `_qgate_closure.py::check_declared_set_closure`, projection `detail` | A mechanism clause falsified by execution: "the file exists, so the files_exist check passes". `_check_files_exist` iterates task **step targets**, so a declared path no task targets is never examined and its existence is never consulted — which the module's own top docstring states correctly. Operator-facing string. | **Fixed**; the text now says why `files_exist` cannot see it. |
| A10 | `_qgate_closure.py::check_declared_scope_reconciliation`, `unexpandable_glob` `detail` | An under-enumerated cause list: "absolute, escapes the repository root, the matcher rejected it, or matched only directories". A home-relative pattern (`~/x/*.py`) is none of the four — it is caught by the explicit `~` guard the module comment calls "the load-bearing half". The message told the author four wrong things about the one case the code says matters most. | **Fixed**; the home-relative cause is now first in the list. |
| A11 | `ref-workflow-architecture/standards/call-graph.md:451` | "phase-4-plan **Steps 5+6+7** task creation", 255 lines below the same file's diagram which **this diff edited** to "Steps 5+6". | **Fixed.** Found independently by this run before round 4 reported, and confirmed by round 4. |
| A12 | `extension-api/standards/dispatch-granularity.md` ×2 (lines 70, 154) | The same "Steps 5+6+7" claim, two further sites. Round 4 named one; the sweep-and-count grep found both. | **Fixed** — both. |
| A13 | `plan-marshall/standards/effort-roles.md:47` | "plan-all-tasks; Steps 5+6+7 bundled" — a fourth site of the same claim, named by neither round 4 nor rounds 1–3, found by grepping the claim before fixing any instance of it. | **Fixed.** |
| A14 | `manage-solution-outline/standards/authoring-guide.md:74` | "derive from the union of `affected_files` across all deliverables" — this diff widened that exact rule in `solution-outline-standard.md`, the file this line cites as authoritative, and did not reach the sibling in the same skill. | **Fixed**, carrying the ⛔ that reading `affected_files` alone bands a survey-scope plan `none`. |
| A15 | `plan-retrospective/references/request-result-alignment.md` ×2 (lines 34, 40) | The coverage population and the scope-creep population both still read `Affected files` only, while the identical rule in the same skill's `SKILL.md` § Coverage contract was widened by this diff. An LLM following this doc drops a survey-scope deliverable's whole mutation surface out of the denominator **and then counts those same files as scope creep**. The clause "a bullet with no annotation states no intent and is counted" is also now false for `Files to survey:`, whose heading supplies `read`. | **Fixed** — all three statements, with the heading-default precedence spelled out. |

⚠ **The row numbering here is this report's, not round 4's, and the two counts differ for three
stated reasons.** Round 4 reported fourteen condition-A findings; this table has fifteen rows and one
finding sits outside it:

- Round 4's second finding bundled two defects in one paragraph — an unkept promise and a count that
  does not match its own list. They are **separate instances**, so they are separate rows (A2, A3);
  a finding is recorded per instance, not bundled.
- Round 4 reported the "Steps 5+6+7" claim as two findings (one touched file, one untouched). The
  sweep-and-count grep found **four** sites, recorded here as A11–A13 by file — so one row is a site
  round 4 did not name.
- Round 4's fourteenth finding is the undeclared collateral change, which is a **disclosure** gap
  rather than a false sentence in a file. It is discharged in § "Undeclared collateral, now declared"
  below and is deliberately not a row here.

**Ground truth for A11–A13 was established before correcting anything:**
`phase-4-plan/SKILL.md` § "Dispatched workflows vs inline steps" already read "Steps 5+6" **on
`origin/main`**, and its Step 7 is *Determine Execution Order*. So all four sites were stale before
this branch existed; the branch corrected one of them and left three. A post-fix sweep for
`5+6+7` / `5, 6, 7` / `5 + 6 + 7` across `marketplace/`, `doc/` and `.claude/` returns only unrelated
aspect numbering in a recipe skill.

### Checked and found clean — recorded because a negative result is only useful if it was looked for

- **`phase-5-execute/SKILL.md:576`** says the scope-creep helper "subtracts the union of
  `affected_files`", which looked like a sixteenth stale site. It is not: `scope_creep_check.py::_collect_declared_files` genuinely reads `references.affected_files` **and every `TASK-*.json` step
  target**, so the doc matches the code. The mutation surface reaches the denominator through the task
  targets, and the new referrer/projection closures are what force those targets to cover it — the
  gap is closed upstream by this plan's own D1.
- **The referrer finding's `detail` string** in `_qgate_closure.py` appeared to contain a garbled
  sentence ("Task steps are sourced from the means the declared set is incomplete"). Reading the
  source rather than a regex dump showed the sentence is intact and correct — the extraction dropped a
  double-quoted continuation line. No defect; recorded so the negative is not re-derived later.

### F-R1 — the finding an automated reviewer caught that four verification rounds did not

| Source | Finding | Disposition |
|---|---|---|
| `cuioss-review-bot`, PR #1295 | `_qgate_closure.check_declared_set_closure` built the referrer finding's title and detail with a raw `int(task["number"])`. A task record whose `number` is absent, `None`, or non-numeric raises `KeyError` / `TypeError` / `ValueError` and takes the whole mechanical Q-Gate down. | **Fixed** in `8486214`, guarded, mutation-verified. |

⭐ **This is the same class round 4 was told to hunt, at a site round 4 read and passed.** The module
**already guards this exact field at three other sites** — `_as_int(task.get('number')) or 0` for the
holistic and unmapped accounting (twice) and an `isdigit()` filter for the deliverable index — so the
question that finds it is not *"is this conversion correct?"* but *"what else needs this guard?"*.
Four rounds asked the first question about this line and none asked the second.

⛔ **And the timing is what makes it worth fixing rather than bounding under (b).** Both accesses sit
on the path that **emits** a referrer finding. The check would therefore crash exactly when it has a
closure gap to report and pass whenever it has none — a **fail-open inside the checks written to
prevent fail-open**, which is this plan's entire subject reproduced in its own deliverable.

The guard is a regression test parametrized over `None`, `''` and a non-numeric value, plus a separate
case for an **absent key** (which fails earlier and differently — `KeyError` before any conversion is
attempted, so it does not ride along with the parametrized cases). Assertions are **positive** — one
referrer gap, naming the target, rendering as `TASK-000` — not "did not raise", so a regression that
swallowed the finding could not pass. Mutation-verified: reverting to `int(task['number'])` turns all
four red (4 failed, 34 passed).

**Sweep-and-count on the same claim.** The identical raw pattern appears at six sites in
`_cmd_qgate_mechanical.py`. All six are **pre-existing on `origin/main`** — re-derived by grepping the
diff's added lines, which contain none of them — so this branch did not make them false and they are
recorded as residue rather than widened into this diff. They are a behavioural hardening opportunity,
not a false statement, so condition **A** does not reach them.

### B — behavioural findings

| # | Finding | Disposition |
|---|---|---|
| B1 | `check-artifact-consistency.py::_extract_bullet_entries` — the docstrings added by rounds 1–3, and `artifact-consistency.md:53`, assert "the heading supplies a default, never an override". Inverting `intent or default_intent` left **the entire `plan-retrospective` suite green (949 passed)**. Under the inversion an explicitly marked `(write-replace)` survey bullet is silently downgraded to `read` and drops out of the recall denominator — *raising* recall by shrinking what it is measured against. | **CLOSED, not characterised.** `test_an_explicitly_marked_survey_bullet_reaches_the_recall_denominator` asserts the denominator as exactly 3 and the excluded pool as exactly 1; the inversion reaches 2 and 2 — the opposite verdict on both numbers. Mutation-verified red. |
| B2 | `_plan_parsing.deliverable_write_set` — the docstring added by rounds 1–3 says "a path declared under both fields contributes one write-set member". Deleting the `seen` set left `manage-tasks`, `manage-solution-outline`, `plan-retrospective` and `phase-6-finalize` **all green**. The identical defensive dedupe in `foreign_pr_gate._foreign_paths_by_deliverable` *did* get its own guard. | **CLOSED, not characterised.** Two guards: the exact list (a concatenating regression yields the path twice, which a membership assertion would accept) and the document order the docstring promises. Mutation-verified red. |
| B3 | `manage-lessons/scripts/_lessons_query.py::_derive_components` reads `deliverable['affected_files']` only, so a survey-scope deliverable contributes zero components and zero `unmapped_paths[]`. `manage-lessons consult` surfaces no lesson for the skills it will actually edit, and `manage-lessons/SKILL.md` step 3's promise that "narrowing is visible rather than silent" does not hold for it. | **SURVIVOR — see § Stop record for its (b) bound.** |
| B4 | `test_qgate_closure.py::test_the_finding_names_every_hit_and_states_the_true_total` asserts `len(hits) <= _MAX_HITS_NAMED` as a precondition, where `hits` is the live `manage-tasks/scripts/*.py` set (14 today, cap 20). Adding 7 scripts to that directory turns this into a hard failure of an unrelated change. | **SURVIVOR — see § Stop record for its (b) bound.** |

**Both mutants that survived round 4 were closed rather than characterised**, because both are the
class round 4 was told to hunt: documented behaviour added by an earlier round to explain that round's
own fix, with no guard anywhere. Leaving them open under a (b) bound would have been permitted and
would have been the weaker choice.

### Mutation verification of the two new guards

Run by this run, after committing everything the sweep must not lose, with each file's bytes
snapshotted by the harness itself (`shutil.copy2` to a unique `run02-mutsweep-main` scratch path) and
restored in a `finally` — **never** `git checkout` / `git restore` / `git stash`, which rewrite from
the index and would have discarded uncommitted work:

| Mutant | Result |
|---|---|
| `'intent': intent or default_intent` → `default_intent or intent` | **DETECTED** — 1 failed, 4 passed |
| `if … and path not in seen:` → `if … and path:` | **DETECTED** — 2 failed, 8 passed |

`git status --porcelain` was empty after the sweep, so no mutation survived into the tree.

## Stop record

**Which exit ended the loop: the exhausted round budget (exit ii), at round 4.** Run 01 declared a
4-round budget before its first dispatch; rounds 1–3 ran under run 01 and round 4 under run 02. This
is **not** the verifier's all-clear exit — round 4 was asked the stop question and answered
**"Yes, for A"**: fourteen false statements remained that condition A forbids leaving open.

Every one of those fourteen is **fixed** regardless of the budget, because A is not subject to it.

**Round 4's own answer on condition B**, quoted rather than paraphrased: *"all four may be left open,
each with a (b) bound supplied."* Run 02 closed B1 and B2 anyway. The two it left open:

| Survivor | (b) — the bound, and the promise it stays outside of |
|---|---|
| **B3** — `manage-lessons` does not read the survey pair | Confined to lesson **surfacing**, which is advisory. It cannot change a Q-Gate verdict, a write-set, a recall figure, or the phase-6 landing gate — the four surfaces this plan's deliverables are stated in terms of. The plan's goal is that completeness checks are closure-based and that a closure claim cannot license skipping verification; a lesson that fails to surface changes neither. Closing it means widening `_derive_components` to the write-set, in a skill no deliverable names. |
| **B4** — a live-directory precondition in one test | Deterministic and **loud**: an `assert` carrying its own message, never a silent pass. It cannot produce a false green, only a false red, and only when someone adds seven scripts to one directory. It changes no deliverable's verdict and no other test's meaning. |

Both were re-put to round 4 as part of its stop question and are recorded with its answer, not carried
forward unread.

**Were the late rounds' findings narrower? No — and this is stated as the observation it is, not as a
licence.** Round 4's own words: *"the round-1-through-3 signature held for a fourth consecutive round
— each fix landed at the site the finding named and not at the sites restating the same claim."* Eight
of its fourteen A findings are in the shipped change rather than the run's records, including two
false clauses inside Q-Gate text an operator reads. Round 3 also found more shipped-surface defects
than round 2. The rate did not decay.

**Residue to assume remains.** Read the deliverables as **still carrying defects of the kinds round 4
found** — a claim corrected at n−1 of n sites, a rationale clause asserting a mechanism nobody
executed, and a guard whose fixture cannot distinguish the defect it names. That is not a hypothetical:
it is the measured, four-times-repeated behaviour of this change under audit, and round 4's fixes are
themselves young unreviewed prose that no fifth round has read.

`Outcome` in this report's header reports the **deliverables**, not the loop.

## Reviewer participation

**The expected population is derived from configuration, not transcribed.** It is the `author_login`
of each `marketplace/bundles/plan-marshall/skills/automatic-review/standards/{bot_kind}.md` registry
doc — read at the moment of this claim — cross-named in prose by `.github/workflows/pr-agent.yml`.
That read returns three: `coderabbitai` (coderabbit.md), `cuioss-review-bot` (pr-agent.md),
`sourcery-ai` (sourcery.md). **M = 3.**

Every verdict below is derived from the **stored comment bodies** across all three surfaces
(`get_comments`, `get_reviews`, `get_review_comments`), never from a check-run state or a summary.

| Reviewer (`author_login`) | Verdict | Reopens? | Body evidence / reason |
|---|---|---|---|
| `cuioss-review-bot` | **`reviewed`** | — | Published a "PR Reviewer Guide 🔍" issue comment against head `117d351`, carrying one actionable finding (**Unhandled Exception** on `int(task["number"])`). Fixed in `8486214` and answered on the thread — see § Findings, F-R1. |
| `coderabbitai` | **`rate-limited`** | **yes** | Two bodies. First: *"Review limit reached … **Next review available in: 28 minutes**"*. Then, on an explicit `@coderabbitai review` re-request: *"I will review pull request #1295. ⚠️ Action not completed — Review rate limited."* A countdown, so it clears on its own. |
| `sourcery-ai` | **`rate-limited`** | **no** | *"your pull request is larger than the review limit of 150000 diff characters."* A property of **this diff's size**, not of the clock — the same request never succeeds at this size, so waiting is futile and re-requesting is not productive. |

⭐ **The two `rate-limited` verdicts are not the same fact, and only the `Reopens?` column separates
them.** Both reviewers refused the same PR at the same moment. `coderabbitai`'s refusal is a clock
that clears and was worth re-requesting; `sourcery-ai`'s is a size ceiling that never clears, so
re-requesting it would have been wasted effort. A participation table carrying only the verdict would
have rendered them identically and told a reader nothing about which — if either — was worth chasing.

**No surface was `unreadable`.** All three MCP surfaces returned real bodies on this PR
(`get_reviews` → Sourcery's refusal, `get_comments` → CodeRabbit's and pr-agent's, `get_review_comments`
→ a genuine empty set), so every absence recorded here is a trustworthy absence rather than a failed
read. Merge-gate **condition 2 is therefore established**, not overridden.

### ⚠ A misread by this run, recorded because it nearly produced a false verdict

At roughly 12:03 this run recorded `cuioss-review-bot` as **`silent`** and posted its registry
`trigger_comment` (`/review`) as the recovery check. **That verdict was wrong.** The bot had already
published its Guide comment at 11:58:33 — five minutes earlier.

The cause is exactly the failure the contract warns about, committed by the run enforcing it: the
absence was inferred from a **stale page-1 read plus an empty page-2 read**, and page 1 was never
re-read. A filtered query that could only return what it already had was believed without a positive
control.

Consequences, stated rather than tidied away: one unnecessary `/review` comment, and one redundant
`issue_comment`-triggered workflow run (`32134879260`, conclusion `success`). No incorrect verdict
reached the report, because the bodies were re-read before this table was written. The run also
briefly speculated that the pr-agent workflow's fail-closed gate had a hole; it does not — the gate
was right and the reader was wrong.

**Coverage: 1 of 3 reviewed.** The § Step 8 condition-4 shortfall disclosure fires — see the merge
gate below for its exact wording.

## Cost

Each figure carries its population, because a bare number that merely looks comparable is worse than
none.

- **Tokens:** **not available to the agent in this session.** Stated plainly rather than estimated —
  this cloud session exposes no usage counter to the agent, and a guessed figure would be indistinguishable
  from a measured one in this table.
- **Wall-clock:** run 02's first commit is `d898934` at **11:03:13 UTC** and its last pre-merge commit
  is recorded in this report's final commit; the span across the run's committed work is derived from
  `git log --date=iso-strict` at the moment of this claim. That measures **committed work**, not
  session time: it excludes the state-derivation and rebase that preceded the first commit, and it
  includes long unattended waits on CI and on a reviewer's rate window.
- **Population:** what these figures count is **one interactive Claude Code cloud session** running one
  plan under the standalone lane, as the harness counts it.

⛔ **This is NOT comparable to a plan-marshall `metrics.toon` total.** A `metrics.toon` total counts the
orchestrator-plus-agent dispatch tree under plan-marshall's own per-task billing boundary. A single
interactive cloud session does not share that boundary — this run's sub-agent dispatches (one
verification round) and its own main-loop work fall under no such ledger. The two cannot be made
comparable here, so no parity is implied.

## Merge gate (Step 8)

**Condition 1 — required contexts on the exact head SHA.** Read from GitHub's own computation over the
ruleset (`pull_request_read method: get` → `mergeable_state`), never from a ruleset-config call, which
is unreachable on the cloud MCP path. Required-ness is the ruleset's to define and no individual check
is named as required or ignorable here.

**Condition 2 — every PR comment handled.** One actionable finding was filed (`cuioss-review-bot`,
F-R1); it was fixed in `8486214` and answered on its thread. No surface was `unreadable` — all three
returned real bodies — so this condition is **established**, not overridden.

**Condition 3 — the report finalized and pushed as the last pre-merge commit**, before arming, because
arming locks the branch against further pushes the instant the required checks go green.

**Condition 4 — the review-coverage shortfall disclosure. This is a disclosure, not a gate**, and it
does not hold the merge open. Stated in words:

> **Review coverage: 1 of 3.** `cuioss-review-bot` reviewed and its finding was fixed and answered.
> `coderabbitai` is rate-limited on a per-developer quota — **reopens: yes**, and it was re-requested
> explicitly, which returned *"Action not completed — Review rate limited."* `sourcery-ai` is
> rate-limited on a **diff-size ceiling of 150000 characters** — **reopens: no**, so no wait and no
> re-request would ever have obtained it at this diff's size.

⚠ **This PR merges on 1-of-3 review coverage, and says so.** Blocking on a bot's quota would strand a
landing behind something outside our control, which the contract names as the wrong direction; the
defect it guards against is the *silence*, not the shortfall.

## Contract check (Step 9)

Re-read against what actually happened, confirming both that each step ran and that its artifact
exists.

| Step | Verdict | Artifact |
|---|---|---|
| 1 Skills loaded | **done** | § Skills loaded — six, all by bundle path (the plugin is not installed in this session); none unobtainable. |
| 2 Branch | **done** | `claude/derived-set-closure-integrity-3i53aj` exists **on `origin`** — harness-assigned, kept as assigned. § "How run 01's work was recovered" records the rebase that carried run 01's commits onto it. |
| 3 Plan directory | **done** | `doc/plans/code-intelligence-substrate/350-outline-derived-set-closure-integrity/plan.md` exists and opens with the first-instruction block (checked, present, not repaired). |
| 4 Implement | **done** | Commits carry the `Co-Authored-By` trailer and no "Generated with Claude Code" footer; deliverables addressed by run 01, round-4 and reviewer fixes by run 02. |
| 4 Per-commit gate | **done** | Both `*.py`-touching commits (`f11e8b7`, `8486214`) preceded by a `./pw quality-gate` reporting `ruff` / `mypy` / SPDX clean — § Build gate. |
| 4 Pushed | **done** | Every commit pushed on creation; `git status -sb` reports no `ahead` at the final commit. |
| 5 Build gate | **done** | § Build gate — git-derived Python verdict (8 production scripts, 9 test modules), full `./pw verify` SUCCESS, with the explicit note that it measured `117d351` and that CI's required `verify` covers the final head. |
| 6 Verification sub-agent | **done** | § Findings and § Stop record — four rounds against a budget declared before the first dispatch; **exit (ii), the exhausted budget**, at round 4; round 4's own stop answer quoted; every condition-**A** finding fixed regardless of the budget; two survivors listed individually with their (b) bounds and confirmed re-put to the verifier; late rounds recorded as **not** narrower; residue to assume stated. |
| 7 PR cycle | **done** | PR [#1295](https://github.com/cuioss/plan-marshall/pull/1295). Every comment dispositioned; § Reviewer participation carries a verdict **and** a `Reopens?` value per reviewer, derived from bodies. No `silent` verdict survives — the one provisionally recorded was this run's own misread, corrected and disclosed with its cost. No `unreadable` verdict, so condition 2 is established. |
| 8 Merge gate | **see § Merge gate** | Conditions 1–3 met, condition 4 disclosed in words at 1-of-3. |
| 8 Bridge | **done** | One write under `doc/plans/` outside this plan's directory — a **link repair** caused by Step 3's own `git mv`, not a status or bookkeeping write; no ledger, no status file, no other plan's directory. § Bridge. This report carries the PR number and per-deliverable outcome the orchestrator collects from. |
| 9 This check | **done** | This table. |
| 9 What have we learned | **done** | Two proposals plus one secondary, each with evidence from this run, put to the operator and **not** self-approved; to ship as separate `chore/` PRs on approval. |

**No `/sync-plugin-cache` is owed.** It is a machine-local build step reading the git-ignored
`target/` and writing `~/.claude/`; a cloud run neither performs nor records it as a debt.

**GitHub access path:** the **GitHub MCP server** throughout. There is no `gh` CLI in this session and
Bash cannot reach `api.github.com`.

**Branch form:** **harness-assigned**, kept as assigned.

### Tree claims re-verified at the moment of this claim

Claims about the *diff* are re-derived by the § Findings sweeps; claims about the **filesystem** are
not, and the run's own build gate mutates the tree the report describes. Re-checked here:
`git status --porcelain` is empty; the two mutation sweeps restored every file from their harness
snapshots (never `git checkout`), and the post-sweep status was empty both times; no `uv.lock` churn
was produced, the session interpreter being 3.12.3.

## What have we learned (Step 9)

Two proposals, both carrying evidence this run produced. **Neither is self-approved**; both are put to
the operator, and on approval each ships as a separate `chore/` PR touching only the skill — never in
this plan's diff.

### Proposal 1 — the contract has no procedure for resuming a halted run in a NEW session

**Evidence, from this run.** Run 01 was halted on harness-assigned branch
`claude/derived-set-closure-integrity-g7n8x2` with nine commits pushed and no PR. Run 02 began in a
different cloud session, bound to a *different* harness-assigned branch,
`claude/derived-set-closure-integrity-3i53aj`. § Step 2 covers exactly two arrivals — "a first run
creates the branch" and "a **resumed** run checks the existing branch out" — and the second assumes
the resumed run is bound to the *same* branch name. It is silent on the arrival that actually
happened, and the two rules that do apply point in opposite directions: *keep your assigned branch*
(for resumability) and *the remote is the only durable storage* (so the prior work must be carried
forward, not abandoned).

The run had to derive the procedure itself: rebase the prior branch's commits onto current
`origin/main` — a plain checkout was impossible, because the two had diverged once `main` took a
commit the older branch predates — push to the assigned branch, and leave the old branch untouched on
the remote.

⭐ **And the consequence the contract never warns about: a rebase falsifies every commit SHA the prior
run's report quotes.** `report-01.md` and `actual-state.md` between them named nine commits, none of
which existed on the branch under review afterwards. That is a **condition-A** defect — a report
figure that is false — manufactured by following the contract's own durability rule, and nothing in
§ Step 9's re-verification list would have caught it, because its re-check covers *tree* claims and
*diff* claims, not *history* claims.

**Proposed edit:** a third arrival in § Step 2 ("a run resumed in a new session on a different
assigned branch"), stating the rebase-and-keep-the-assigned-name procedure, and a line in § Step 9's
re-verification paragraph adding **history claims** — commit SHAs quoted in any prior run document —
to the set a run must re-derive when it rebases.

### Proposal 2 — a non-converging loop is not a first-class outcome

**Evidence.** Run 01 raised this and never got to present it; run 02 confirms it with a fourth data
point. Four rounds ran. Round 4 found **more shipped-surface defects than round 3** (eight of fourteen
A findings in the shipped change), and the round-1-through-3 signature — *each fix lands at the site
the finding named and not at the sites restating the same claim* — held for a fourth consecutive
round. Round 3 had already found a regression round 2's fix introduced.

A run that stops on the exhausted budget currently records the same `Outcome` as one that stops on a
verifier's all-clear. The difference lives in a stop record a reader has to go looking for, and
`Outcome: completed` is what a collector reads. The useful signal is not "verification finished" but
**"each round is still finding defects at the same rate, and the rate is not decaying"**.

**Proposed edit:** require the report **header** to carry the loop's exit alongside `Outcome` — e.g.
`Outcome: completed (verification: budget-exhausted, non-converging)` — so a non-converging loop is
visible without reading the stop record. `Outcome` keeps its meaning (a verdict on the deliverables);
the header simply stops hiding which exit produced it.

### Secondary, small

§ Step 6's mutation-sweep instruction tells a run to put scratch under `$TMPDIR` and says nothing
about collisions. Run 01 had two independent sub-agents clobber each other's mutation harness by
choosing the same filename. Run 02 avoided it only by instructing its sub-agent to prefix its scratch
paths and by using a distinct prefix itself — neither of which the contract asks for. **Proposed
edit:** one line — *scratch paths are unique per agent*.

## Residue

Run 01's residue table (`actual-state.md` § 5, R1–R5) carries forward unchanged except where noted.
What run 02 adds or re-derives:

| # | Item | Disposition |
|---|---|---|
| R3 (re-derived) | Sites saying the execution manifest is composed at **`phase-4-plan` Step 8b**; canonical is **Step 7b**. `actual-state.md` estimated "~14"; re-derived at the moment of this claim it is **13** — the grep returns 15, of which `phase-1-init/SKILL.md:907` names phase-1-init's *own* Step 8b and `phase-4-plan/SKILL.md:61` is correct (Step 7b composes, Step 8b is the LLM Q-Gate). | **Still residue, deliberately.** Two were corrected where this diff already touched them. The remaining 13 were false on `origin/main` before this branch existed, this change did not make them false, and **round 4 read R3 and did not raise them** as condition-A findings — the contract makes that the verifier's call, not the author's. Fixing them means editing eight further files no deliverable names, which is itself the undeclared-collateral defect § "Undeclared collateral" exists to prevent. |
| B3 | `manage-lessons` does not read the survey pair (§ Findings). | **Open, bounded.** Next step: widen `_derive_components` to `deliverable_write_set`. |
| B4 | A live-directory precondition in `test_qgate_closure.py` (§ Findings). | **Open, bounded.** Next step: derive the expectation from the directory rather than asserting a cap. |
| New | `doc/plans/code-intelligence-substrate/250-footprint-read-outside-its-window/report-01.md:100` restates the pre-widening coverage rule. | **Deliberately not corrected.** It is another plan's **run report** — a dated record of what that run did, not a live specification. Editing it would falsify the record rather than repair a claim. |

## Undeclared collateral, now declared

Round 4 found that the diff carries a change no deliverable D0–D5 asks for and no run document
disclosed. Declaring it here is the fix.

**The phase-4-plan step renumbering.** Three navigation documents are brought into line with
`phase-4-plan/SKILL.md`'s canonical numbering — `ref-workflow-architecture/standards/call-graph.md`,
`phase-4-plan/references/task-creation-flow.md`, and the hand-edited
`doc/resources/diagrams/call-graph.svg`. The renumbering is `5..7`→`5+6`, `8`→`7`, `8b`→`7b`, `9`→`8`,
`10`→`9`, `11`→`10`, plus deletion of a "Step 7: holistic verification tasks" line describing a step
that does not exist. ⚠ **These documents were stale against `origin/main` before this branch** — the
canonical numbering was already `5/6/7/7a/7b/8/8b/9/10` there. The change is a correction, not a
renumbering of the workflow itself: no step moved.

**Distinguish it from what is NOT collateral in the same files.** The `q-gate-validation` arrow in
`call-graph.md` and `call-graph.svg` changed from *"always / unconditional"* to *"unless B1/B2
suppress it"*. That is **D4's finding**, not collateral: D0 confirmed the surgical-scope bypass
suppresses the dispatched validator, and D4 is the deliverable that says a closure claim must not
carry that authority. A diagram asserting the dispatch is unconditional was false, and correcting it
was doing D4's work.
