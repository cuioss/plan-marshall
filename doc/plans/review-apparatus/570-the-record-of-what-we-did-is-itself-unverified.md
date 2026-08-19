> ⛔ **FIRST INSTRUCTION — do not skip, do not delete, do not move below the title.**
>
> Before reading the rest of this plan and before any other action, load the working contract that
> governs this run:
>
> ```text
> Skill: cloud-plan-lane
> ```
>
> It owns the branch/PR/review-comment cycle, the build gate, the pre-PR verification sub-agent, the
> run report, and the closing self-check. **Nothing in this plan overrides it** — where this plan and
> the contract disagree, the contract wins, and the disagreement is reported.
>
> If the skill cannot be loaded, **stop and report the run blocked**. Do not reconstruct the workflow
> from this file: the parts that matter most — the merge gate, the verification dispatch, the report
> — are not in here.
>
> This block is part of the plan, not part of the template. It survives into every copy.

# Every claim in the epic's own run reports resolves against the tree

**Epic:** review-apparatus
**Branch prefix:** chore — maintenance of the epic's records

## Problem

The `review-apparatus` epic exists because a signal can assert more than it establishes: a
participation credit for a commit nobody reviewed, a coverage ratio without its denominator, a
routing table that documents an enforcement boundary nothing enforces. An epic-wide audit of the
landed plans produced a `gaps.md` beside each plan's report. Read across the set, those files
contain the same defect class committed **by the epic's own records**.

A run report is not commentary. It is the artifact the orchestrator's collect step reads an outcome
from, and the only durable account of a run once the branch is merged and deleted. So the failures
below are false signals in exactly the sense the epic names:

- **Symbols that never existed.** Plan 010's report names `_existing_pr_comment_shas` and
  `_recorded_dropped_comment_shas` as the two SHA sources of the currency anchor, and cites a test
  `test_currency_anchor_is_derived_from_both_sha_sources` as the population derivation. None of the
  three exists anywhere in the tree. The shipped reader is a single one, `_recorded_currency_records`,
  and the real test asserts one ledger source. A named test that does not exist is the worst shape of
  this defect: a later reader treats the coverage as present and stops checking.
- **A PR number read off an unrelated PR.** Plan 090's report attributes the `--max-per-component`
  flag and its guard to PR #1153, whose diff contains no `manage-lessons` path at all; the commit
  `git log -S'invalid_cap'` returns is #1039.
- **A residue section asserting the opposite of its own directory.** Plan 110's report closes with
  "None blocking … No follow-up owed" over five live defects in the exact surface the plan declared.
- **Counts stated twice, differently, for the same event.** Plan 020's report gives two green-verify
  totals for one run; plan 130's report gives one total that its own squash-commit message
  contradicts, plus a test tally and a file tally that the commit refutes; plan 120's mutation table
  states a failure count written beside the result rather than from it, and four of its finding rows
  bundle instances under a preamble forbidding exactly that, two of them miscounting their own
  enumeration; plan 100 publishes an absence claim's match count with no searched population, in a
  form that changes every time a document is added to the plan directory.
- **A report that was never finalized.** Plan 060's report still carries `Outcome: _in progress_`, a
  Build-gate section stating "No production source was changed by this plan" against a merge commit
  that changed `gitlab_ops.py` (+11/−1), a Step 8 row pointing at a landing record that appears
  nowhere below it, and reviewer verdicts written as predictions — one of which is wrong, because the
  run read two comment surfaces and the bot in question published its rate-limit notice on a third.
- **Verification obligations the plans mandated and the runs never discharged.** Plans 010 and 050
  each demanded a ⭐ cold read with the answers recorded *verbatim*; neither report carries one.
  Plan 030's report dispositions none of a claim-label row and none of a conditional Verification
  clause. Plan 040's owed architecture insight, plan 020's owed API-Sheriff re-review, plan 100's
  cross-repo proposal, and plan 130's mutation-coverage shortfall all live only inside archived run
  reports, which nothing reads.
- **Contract proposals recorded and never re-anchored.** Plan 050 could not amend the contract that
  governed it, so it recorded two replacement blocks for `cloud-plan-lane/SKILL.md`. Both were
  written against a span that two later landings have since changed — the `unreadable` verdict and
  the `Reopens?` subsection. Applied verbatim now, the proposals would silently delete both.

The mechanism is one habit, visible in the reports themselves: **a sentence written early in a run
was never re-derived against the tree the run finally shipped.** Plan 010's own Finding 4 records
that a late review-fix collapsed the two-source design into one ledger — and §§ D2 and D4 were never
re-read against it. Plan 050's suite figure is a pre-review-fix measurement carried forward. Plan
130's tallies were stated once and restated, never recounted.

## Goal

The epic's records say only what the tree can be made to confirm. Every symbol, test name, PR number,
commit, footprint and figure written in a `review-apparatus` run report resolves against something
that exists; no report asserts an absence of follow-up its own directory contradicts; the one
unfinalized report carries a contract-legal outcome and a footprint matching its merge commit; every
obligation a plan mandated is either discharged with its evidence recorded or carried to a
git-tracked place a later run will actually read; and the contract proposals are re-anchored against
the current contract text and put to the operator as proposals, so applying them cannot revert work
that landed after they were written.

## Deliverables

**One gate (D0) and five deliverables (D1–D5).** The count is stated because this plan's subject is
counts a reader cannot resolve from the page.

Each deliverable names the gap ids it discharges. Those ids index entries in the per-plan `gaps.md`
files, which are git-tracked and readable from any clone — see § Notes, "Where the evidence lives".
Every defect is restated here in full, so the run never needs to open one.

---

### D0 — DERIVE the report corpus and confirm every defect still reproduces (GATE, mutates nothing)

Establish, from the git tree alone, the exact set of files this run will touch and the exact set of
defects it will correct. **Nothing else in this plan may start until D0 has produced its index.**

1. **Enumerate the corpus.** List `doc/plans/review-apparatus/` and record every plan **directory**
   (a directory, not a flat `.md`, is a plan a run has worked). For each, record whether it carries
   `plan.md`, `report-01.md`, `verification.md` and `gaps.md`. Publish the directory count and the
   report-file count as measurements of *this clone*.
2. **Index the in-scope gaps.** This plan discharges gap entries drawn from eleven plan directories.
   **⚠ Re-derive every count in this bullet — do not trust the numbers written here.** As authored,
   the set is: `010` G5, G10 · `020` G18, G19 · `030` G11 · `040` G14, G16 · `050` G4, G12, G16 ·
   `060` G5, G6, G7 · `090` G1, G9 · `100` G8, G9 · `110` G6 · `120` G8, G9 · `130` G14, G15, G18 —
   **23 entries across 11 directories**. Recount both from the list above and state the two figures
   you derived, not these.
3. **Confirm each defect still reproduces**, by opening the cited file and checking the cited claim
   against the tree at the moment of the check. A defect that no longer reproduces — because a later
   landing fixed it, or because the orchestrator's collect step removed the plan directory — is
   **dropped**, and its absence is recorded with the reason. Do not correct a sentence that is
   already true.
4. **HALT conditions.** Stop the run and report it **blocked** if any of these holds:
   - `doc/plans/review-apparatus/` cannot be listed, or carries no plan directory at all;
   - the set of report files cannot be derived from the tree — that is, the run finds itself
     needing a hand-written list of which reports exist in order to proceed.

   ⛔ **Do not fall back to a hand-maintained list of reports.** A hand-maintained inventory of
   records is the defect this plan is correcting; reproducing it inside the fix would be the plan
   defeating itself. Either the corpus is derivable from the tree, or the run stops and says so.
5. **Do not look under `.plan/`.** No orchestrator ledger, no plan spec, no findings store and no
   landing record is present in this clone — `.plan/` is git-ignored. Nothing in this plan needs one.

*Done when:* the run report carries an index naming every plan directory found, every report file the
run will edit, every in-scope gap id with a **reproduces / does not reproduce** verdict and (where it
does not) the reason, and the two re-derived counts from item 2 — or the run is reported blocked
against a named HALT condition.

---

### D1 — Correct the false claims about symbols, PRs and states

Discharges **010 G5**, **090 G1**, **110 G6**.

1. **Plan 010's report, §§ D2 and D4.** § D2 states the reviewed SHA per comment is "the union of
   `_existing_pr_comment_shas` (stored-finding stamps) and `_recorded_dropped_comment_shas` (the
   noise sidecar…)". § D4 bullet 4 cites
   `test_currency_anchor_is_derived_from_both_sha_sources` as the population derivation. **All three
   names resolve to nothing** — in the tree, and in the landed source at the plan's own merge commit.
   The shipped reader is `_recorded_currency_records` (with its writer `_record_currency_records`) in
   `workflow-integration-github/scripts/github_pr.py`, and the real test is
   `test_currency_anchor_is_recorded_in_the_ledger_on_credit` in
   `test/plan-marshall/workflow-integration-github/test_github_pr.py`, which asserts **one** ledger
   source. Rewrite both passages to name the shipped symbols and the single-ledger design, and add
   one sentence under the report's Finding 4 — the finding that already records the late review-fix
   collapsing two sources into one — stating that §§ D2 and D4 were re-derived against the final
   tree. Verify each replacement name by resolving it in the tree **at the moment you write it**.
2. **Plan 090's report, the `--max-per-component` bullet.** It attributes the flag and its
   `invalid_cap` guard to PR **#1153**, and corroborates with "whose review threads are empty
   (Sourcery rate-limited, zero inline threads)". `git log -S'invalid_cap' --` over
   `manage-lessons/scripts/_lessons_query.py` returns exactly one commit, `010ea461` (PR **#1039**);
   #1153 is `1296ede1`, a shims plan whose diff contains no `manage-lessons` path. Correct the PR
   number and commit. Then settle the corroborating clause by a fixed rule, not a judgement:
   **re-verify "review threads are empty" against #1039 if that PR's review surfaces can be read;
   if they cannot, delete the clause** — never carry an unverified corroboration onto a corrected
   citation, and never restate it as read when the read did not happen.
   The conclusion the bullet draws (the fix shipped with the flag, so it carries no posted review
   answer, so it is not in the answered corpus) survives and is not rewritten.
3. **Plan 110's report, § Residue.** It opens "**None blocking.** … No follow-up owed." Its own
   `gaps.md` records five live defects in the plan's declared surface (`github_pr.py`'s
   `fetch_findings`, its participation derivation, and the cross-iteration dedup), two of them
   obligations the report marks satisfied that the tree does not satisfy. Replace the sentence with
   an unambiguous statement that follow-up **is** owed, naming the items by gap id and
   cross-referencing the directory's own `gaps.md` and `verification.md`. Confirm, at the moment of
   the edit, that those items are still open — an item a later landing closed is not listed.

*Done when:* every symbol name, test name, PR number and commit SHA appearing in the three edited
reports resolves against the tree or against `git log` at the moment of the claim; and no residue
section in those three reports asserts an absence of follow-up that its own directory's `gaps.md`
contradicts.

---

### D2 — Re-derive every disputed figure, and label the ones that were real measurements

Discharges **020 G19**, **050 G16**, **090 G9**, **100 G8**, **120 G8**, **120 G9**, **130 G14**,
**130 G15**.

**The rule that governs all eight, decided here so the run never has to choose** (see § Notes, "Two
conventions settled at authoring time"):

- A figure that is simply **wrong about a commit** is *restated* from a re-derivation run now.
- A figure that was a **real measurement at some moment** is not silently overwritten — it is
  *labelled* with the commit or round it measured, so the epic's retrospective corpus stays
  reconcilable.
- **No correction carries a date, a version number, a changelog entry or a "corrected on …" note.**
  Repository documentation standards forbid dated update sections, and a reader who reaches a false
  sentence must not need a second document to learn it is false. The corrected sentence simply states
  what is true.

The eight items:

1. **020 G19 — two green-verify totals for one run.** § Build gate states `15848 passed, 1 skipped`;
   § Contract check step 5 states `15859 passed, 1 skipped`. Both are presented as the run's green
   verify. They are reconcilable — a later fix commit added tests — but § Build gate does not say its
   figure predates the fix. **Label each figure with the commit it measured** — that is the settled
   choice; do not delete either figure. One green-verify figure per commit the report describes, each
   labelled.
2. **050 G16 — the suite figure that measured an earlier tree.** The report's § Build gate says
   "**38 passed** — including all 8 new `comparison`-grade tests", and the PR body says eight tests.
   The audit re-derived: the module held 30 tests before the fix commit and 40 after, ten of them
   `comparison`-grade, and 43 at a later HEAD from unrelated additions. **Do not edit plan 050's
   report** — this gap's own *done when* directs the reconciliation into a successor report. Instead,
   re-derive the three module counts and the added-test count yourself (name the commands and the
   commits), and record the corrected figures **with the reason for the discrepancy** in this run's
   own report, so a retrospective reconciling suite sizes across the epic is not reconciled against
   the stale one.
3. **090 G9 — a plan whose deliverable count a reader cannot resolve.** Plan 090's Deliverables
   section opens with the single word "Three." and then enumerates four numbered deliverables, of
   which D0 is labelled "GATE, mutates nothing", making "three plus a gate" a defensible second
   reading. Rephrase the opening so the count matches the numbered items beneath it without the
   reader having to infer the gate/deliverable distinction. **Do not touch the sentence that follows
   it** — that one counts *detectors*, not deliverables. This is the one edit in this plan that
   touches a `plan.md` rather than a record.
4. **100 G8 — an absence claim with no denominator.** The report's § "Absence-claim scope" describes
   the scope qualitatively ("the entire working tree rooted at the repo") and then gives **match**
   counts only. It also publishes raw tree-wide totals for `Prompt for AI Agents` and
   `enable_prompt_for_ai_agents`, which rise every time a document is added to that plan directory —
   so the published figures were already stale when the audit read them. Restate the claim so that
   (a) it names the search root and the **size of the searched population** alongside the match
   count, and (b) every count it states is **invariant under adding further documents to that plan
   directory** — i.e. expressed as a scoped absence outside the plan directory rather than as a raw
   tree-wide total. Re-derive both the population size and the matches yourself; do not copy a figure
   from the gap entry.
5. **120 G8 — a mutation row counted beside the result rather than from it.** The report's
   "From mutation testing" table, row A ("disable cause-dominance in `_refusal_state`"), states
   **7** failures "all in case (a)". The audit re-ran it and observed **9**, one of them in case (c)
   and unmentioned by the row's composition. Re-derive rather than copy, by this procedure:
   1. Derive plan 120's landing commit from git — the commit that **added**
      `doc/plans/review-apparatus/120-review-barrier-deadlocks-on-a-refusing-bot/report-01.md`.
   2. Check whether `test/plan-marshall/automatic-review/test_structural_refusal.py` and
      `marketplace/bundles/plan-marshall/skills/automatic-review/scripts/review_completeness.py` are
      byte-identical to that commit. **If either has drifted, do not guess:** record in the row that
      the mutation cannot be re-derived against the landed tree, name what drifted, and leave the
      original figure labelled as the landing-time measurement. That is a stated outcome, not a
      failure.
   3. If both are identical: apply the mutation to `_refusal_state` in a working copy, run only
      `test_structural_refusal.py`, record the **names** of every failing test, revert with
      `git checkout --`, and confirm the revert left no Python change in the branch diff.
   4. Restate row A's count **and** its composition from the observed failure list, naming the
      case-(c) test explicitly.
6. **120 G9 — a table that violates its own stated discipline, twice miscounting.** The § Findings
   preamble reads "One row per INSTANCE, never bundled", and four rows immediately below it each
   bundle a range of ids with a prose enumeration in one cell. Two of the four also miscount
   themselves: the `F8–F20` row is 13 ids labelled "Thirteen stale beyond-diff statements" while its
   own cell enumerates fifteen; the `F30–F36` row is 7 ids labelled "Seven further stale statements"
   while its cell enumerates eight. **Amend the preamble** to state the rule the tables actually
   follow — one row per instance, except enumerated same-shape sweeps, which carry their member list
   and a per-member disposition — rather than splitting the ranges. That is the settled choice: it is
   the option the gap sanctions that does not rewrite a landed record wholesale, and splitting
   thirteen ids out of one cell risks losing the dispositions the cell carries. Then
   **re-derive each of the four bundled rows' counts by counting its own enumeration**, not by
   restating its label, and correct the two that disagree.
7. **130 G14 — a test tally and a file tally the commit refutes.** § D3 says "100 tests added across
   six files" and § Build gate says "5 production scripts, 7 test files". Re-derive all four figures
   from the plan's squash commit (`622f4484`): the count of added `def test_` lines under `test/`,
   the number of files under `test/`, and the number of production `.py` paths in
   `git show --name-only --format="" 622f4484`. **Restate the numbers in place — this gap explicitly
   asks for no correction note and no dated entry.** Also check `parametrize` additions before
   concluding, so the tally is not written off as parametrisation.
8. **130 G15 — two `./pw verify` totals for one run.** The report's § Build gate states **19748
   passed**; the squash commit message of `622f4484` states **19752 passed**. Both purport to be the
   final verify. The commit message is the later artifact, so it is the final round. **State which
   round each figure belongs to** — the settled choice, and the one convention 2 in § Notes requires,
   since both are genuine measurements. Re-derive the commit-message figure from `git log` rather
   than copying it from here.

*Done when:* no report in the corpus carries two unlabelled figures for the same event; every figure
this run writes was re-derived by a command the run records; every count corrected in place was
**re-counted after the edit** and matches; and the run's report names, per item, the command and the
substrate each figure was derived from.

---

### D3 — Finalize plan 060's report, and correct what it asserts

Discharges **060 G5**, **060 G6**, **060 G7**. All three are in one file, so they land together.

1. **The outcome.** The header still reads `**Outcome:** _in progress_`. The lane contract in force at
   that run admitted only `completed | partial | blocked`. Derive the outcome mechanically, not by
   judgement: **`completed`** if the PR merged and every deliverable the report's § Deliverables
   section describes carries a state that is not "not done"; **`partial`** if it merged with any
   deliverable unmet; **`blocked`** if it never merged. Confirm the merge state from git — the merge
   commit's presence on `main` — not from the report's own header, which is the artifact in question.
2. **The build-gate footprint.** § Build gate states the Python footprint as "two test files" and
   asserts "No production source was changed by this plan". The plan's merge commit changed **four**
   Python paths — two new test files, plus
   `marketplace/bundles/plan-marshall/skills/workflow-integration-gitlab/scripts/gitlab_ops.py`
   (**+11/−1**, the report's own F3 refusal-parity fix) and
   `test/plan-marshall/workflow-integration-gitlab/test_gitlab_merge_queue.py` (**+4**). Restate the
   section to name all four paths and to state that one production file was changed. Re-derive the
   path list and the line counts from the merge commit yourself; the figures above are leads.
   ⛔ **Do not add the `> **Verification loop exit:**` line or a stale-base re-verification figure.**
   Both post-date that run — they entered the lane contract after its merge commit — so adding them
   would be inventing a record, not completing one. Confirm that ordering from git before deciding.
3. **The dangling landing record.** § Contract check Step 8 ends "Landing recorded to the operator
   (see below)", and nothing below it is a landing record: the following sections are a
   GitHub-access/branch-form note, "What have we learned", and "Residue". Replace the dangling
   pointer with the actual landing record, derived from the PR and its merge commit.
4. **The predicted reviewer verdicts.** The § Reviewer participation section is followed by an italic
   paragraph stating that the report is finalized before the final push and that the reviewers'
   "expected verdicts are unchanged". A prediction presented where an observation belongs is the
   defect this epic is named after. Replace it with what the surfaces actually held at merge. **If a
   surface cannot be read**, replace the prediction with an explicit statement that the post-push
   verdicts were never observed and are therefore **unrecorded** — an honest gap, never a prediction
   re-labelled as an observation, and never a `silent` inferred from a failed read.
5. **The `sourcery-ai` verdict is wrong, and so is the method behind it.** The report records
   `sourcery-ai` as `silent` — "no review artifact and no notice was published" — and discloses
   "`sourcery-ai` skipped/silent" to the operator. On PR #1182 the **reviews** surface carries a
   `sourcery-ai[bot]` review whose entire body is a weekly rate-limit notice. The check-run half of
   the report's claim is accurate (the `Sourcery review` check concluded `skipped`), but the bot was
   **rate-limited and said so**, not silent — and the distinction is the one that matters to an
   operator, because a rate limit reopens and a skip does not. Correct both passages to state the
   observed cause: rate-limited, notice published on the PR-level reviews surface, check run skipped.
   The 1-of-3 coverage figure is unaffected — a refusal is not a review — so do not change it; verify
   that before writing.
   The root cause is a **method gap**, not a transcription slip: the run read the conversation and
   inline-review-thread surfaces, and the PR-level reviews surface is a third. Closing that gap means
   editing the lane contract, which this run may not do — it is carried into **D5** as a proposal.
6. **The refuted falsifiability argument.** § D3's "Cross-provider / cross-verb reach" bullet for
   `refuse_unconfigured`, and the second item of § Residue, both claim that "dropping the 404/403-as-
   refusal handling flips `gitlab:merge-queue`'s off-routing test". It does not: with that block
   removed, `gitlab_ops.py` falls through to `make_error`, `make_error` always sets `status: 'error'`,
   and the off-routing arm asserts only `status == 'error'` — the audit measured **18 passed** under
   that mutant. Correct both passages to state that the arm is **not falsifiable as written**. Do not
   restate the structural argument, and do not attempt the remedy — the fix belongs to the plan that
   takes 060 G3.

*Done when:* plan 060's report carries a contract-legal `Outcome`; no statement in it contradicts
`git show {its merge commit} --name-status`; no forward-looking prediction is presented as an
observation; no passage describes `sourcery-ai` as silent; and neither falsifiability passage asserts
a mutation that would not flip the named test.

---

### D4 — Discharge the owed obligations, or give each one a git-tracked handle

Discharges **010 G10**, **030 G11**, **050 G12**, **020 G18**, **040 G14**, **040 G16**,
**100 G9**, **130 G18**.

Two halves. The first four are obligations this run can discharge outright. The rest are obligations
whose *work* is out of scope here (§ Out of scope) but whose *handle* is not: each currently exists
only inside an archived run report, which is precisely the "recorded so it cannot lapse, in the one
place nothing reads" failure this epic is about.

**Discharged in this run:**

1. **010 G10 — the cold read plan 010 demanded and never performed.** Plan 010's § Verification
   carries a ⭐: have the pre-PR verification sub-agent read the changed text **cold** and report, in
   its own words, (a) which commit a credit is evaluated against, and (b) whether a `declined` bot
   blocks, is disclosed, or is ignored — *"Report the reading verbatim."* Plan 010's report contains
   no cold reading at all (the word does not appear in it). Run the cold read now, against the
   current text of `automatic-review/standards/bot-participation-contract.md` §§ "The currency rule",
   "Evidence for a bot that edits one comment in place", and "Detecting a decline". Record both
   answers **verbatim** in this run's report. If a reading does not match what plan 010's D1 and D3
   intended, record the mismatch as a finding — do not rewrite the contract to suit the reading, and
   do not paraphrase the reader.
2. **050 G12 — the cold read plan 050 called its central check.** Plan 050's § Verification demands a
   cold reader answer three questions — *(1) was the diff reviewed? (2) is this a gap I must act on,
   or an accounted-for absence? (3) how many reviewers were required, and how do I know?* — with the
   answers reported verbatim. Its report carries a paraphrase of Q2 only; Q1 and Q3 have no reported
   answers. Run the cold read against **D5's re-anchored proposal text** (so this item follows D5)
   and against the empty-`required_bots` rendering it describes, asking all three questions plus
   *"was a required review performed?"*. Record four verbatim answers in this run's report. Q3 is the
   one that tests whether the proposal publishes its denominator — the plan's entire subject — so
   report it even, and especially, if the answer is that the text does not say.
3. **030 G11 — two required confirm/refute artefacts with no disposition anywhere.** Plan 030's
   § Claim labels carries the row *"`--in-progress-bots ""` is dropped by the executor so argparse
   sees a flag with no argument, while omitting the flag works — OBSERVED — reproduce it once before
   building on it"*, and its § Verification asks for an "endorsement trap" hint *conditional* on D0's
   work touching the rejection reporting. Its report mentions neither. Record both dispositions in
   plan 030's report:
   - a short **null-result** row stating that the cause class is closed by the pre-existing
     `nargs='?'` / `const=''` relaxation on the list flags in `review_completeness.py`, plus the
     executor's documented empty-argument stripping in
     `tools-script-executor/templates/execute-script.py.template` (the "Strip empty string args"
     branch), cited by file and symbol;
   - a one-line **"not triggered"** for the conditional endorsement-trap hint, with the reason: the
     landing touched no `tools-script-executor` path, so the condition never fired.

   Verify both statements against the tree before writing them; if either no longer holds, record
   what you found instead.
4. **040 G14 — the architecture insight plan 040's Notes said it should record.** The insight: *a
   review bot's persistent summary card and its trigger acknowledgement are participation artifacts,
   not diff-derived claims — dispose of them as accepted without opening a fix task, and never read
   their presence as evidence the bot reviewed the current HEAD; check instead for a review object
   stamped with the live reviewed-commit SHA.* Its mechanical half is already enforced (the currency
   rule, `STATE_DECLINED`, and the `contentless_review_markers` conditional drop) but the *reasoning*
   is written nowhere, and the disposition guidance — accepted, no fix task, no reply — is not
   available to a triage agent. Add a short subsection to
   `automatic-review/standards/bot-participation-contract.md` § "Participation is not review quality"
   stating the insight and **cross-referencing** the currency rule and the
   `contentless_review_markers` drop rather than restating their mechanics. Confirm the absence
   first: search the `automatic-review` and `workflow-integration-github` bundle docs for the insight
   before asserting it is missing, and publish the searched population size with the result.

**Given a handle, not discharged here:**

Each of these gets **one git-tracked location outside an archived run report**, chosen at authoring
time so the run makes no decision. Each entry restates the obligation in full, names what would
settle it, and says who it is for.

5. **040 G16 — the two partitions plan 040's D0 gated on.** Plan 040's D0 required the absence corpus
   to be "partitioned by cause", and D2 required per-PR charter attribution; the landing argued that
   the *mechanism* exists, which is a different proposition from the clause. The **charter** axis is
   nearly free and is derived here: `git log -- marketplace/targets/pr_agent/target.py` returns
   exactly one commit (`f5493b43`, PR #1130, "route review charters by repository domain") — so every
   PR merged before it ran the pre-charter instructions and every PR after ran the domain-scoped
   packs, a two-bucket partition by merge date against one SHA. **Re-derive that `git log` yourself;
   a second commit since authoring changes the partition from two buckets to three.** The **cause**
   axis (recovering each PR's diff size from its merge commit and attributing each observed absence
   to `size` or `quota`) is measurement work this plan does not do. Record both outcomes in
   `bot-participation-contract.md`: the charter partition with its deriving command and its two
   population sizes, and — in as many words — that **no measured cause partition of the historical
   absence corpus exists**, and that the contract's own "do not pool measurements" invariant
   therefore still blocks reporting any per-reviewer participation rate.
6. **020 G18 — the owed API-Sheriff re-review.** Plan 020 carried a check "so it cannot lapse", and
   it now exists only in that plan's archived report. Restate it **in full** in
   `automatic-review/standards/pr-agent.md`, alongside the reviewer pack whose confirm/refute it is,
   as a stated open item: re-review `cuioss/API-Sheriff` **#185** (26 inline items) or **#154** (47)
   with the shipped language-specific reviewer pack installed, and compare against this reviewer's
   recorded zero on the same diffs; **a refutation is a publishable result.** State the owner in as
   many words: it is closed by whichever `review-apparatus` plan next changes the language-specific
   reviewer pack, and until then it is open. Do
   not confuse it with the `cuioss/API-Sheriff` **#103** grounding record already in that file — that
   is a different PR and a different purpose; keep both, and make the distinction explicit.
7. **100 G9 — the cross-repo proposal with no handle.** Plan 100's D2 recorded a verdict on
   `enable_prompt_for_ai_agents` and recommended an action in the external `cuioss/coderabbit`
   repository; a tree-wide search for the flag name returns hits **only inside that plan's own
   directory**. Record the verdict, its evidence, and the recommended external action in
   `automatic-review/standards/coderabbit.md`, so a search for the flag name finds a live handle
   rather than only a closed report, and cite that location from the report's residue entry.
   ⛔ **Do not touch the external repository** — plan 100's read-only-input boundary still binds.
8. **130 G18 — mutation evidence covering a fraction of the added tests.** Plan 130's Verification
   demanded "every D3 test proven discriminating by mutation". Its mutation table covers, by its own
   attribution, **11** tests; the commit added **91** (re-derive both). The remaining tests are
   asserted red-first, which is a weaker claim than mutation-discrimination — the report does not
   overclaim, but the plan's demand is not met. Running that mutation pass is out of scope here
   (§ Out of scope). Record the obligation, with its **re-derived** scope (tests added, tests covered
   by a mutation, the four suites concerned: `test_review_gate_delta.py`,
   `test_review_commitments.py`, `test_gate_coverage.py`, `test_counting_rule_parity.py`), in plan
   130's own report as an explicitly **open** item, so no reader of that directory concludes the
   Verification clause was met.

*Done when:* the two cold reads are recorded verbatim in this run's report with all six answers; plan
030's report carries a stated disposition for every row of its § Claim labels and every conditional
clause of its § Verification; and each of items 4–8 appears in a git-tracked file outside an archived
run report, naming the obligation, what would settle it, and who closes it — verified by searching
for each obligation's distinctive term and finding the new location.

---

### D5 — Re-anchor the `cloud-plan-lane` proposals against the current text, and put them to the operator

Discharges **050 G4**, and the contract half of **060 G6**.

⛔ **This run does not amend `cloud-plan-lane/SKILL.md`.** The contract it would amend is the contract
governing this run, and that contract forbids self-approving a change to itself: a change is
presented to the operator with the evidence, and on approval ships as a **separate PR** on its own
`chore/` branch touching only the skill. This deliverable therefore produces **re-anchored proposal
text recorded in this run's report** — not an edit to the skill.

1. **Why re-anchoring is required.** Plan 050 recorded two replacement blocks, D1a and D1b, for the
   Step 7 reviewer-participation block and the Step 8 shortfall-disclosure condition. Both were
   written against a span the contract no longer has:
   - D1a's opening and closing anchors — "**Record a verdict per reviewer, derived from the stored
     comment bodies**" through "…not merely unmentioned." — still exist, but the span between them
     has grown two later landings: the **`unreadable` verdict** with its ⛔ block and its merge-gate
     paragraph, and the whole **`Reopens?` subsection** with its table. D1a's replacement table has
     four rows (`reviewed` / `reviewed-empty` / `rate-limited` / `silent`) with **no `unreadable`
     row and no `Reopens?` integration**.
   - D1b targets "Step 8 condition 4"; the condition it describes is now **condition 5**, and it
     carries a `Reopens?` clause.
   - Both proposals cite **line numbers that no longer point at their anchors**.

   Applied verbatim, the proposals would delete the unreadable-surface distinction — which exists
   precisely so a tool failure is not recorded as a clean signal — and the reopens-or-not column. A
   proposal whose whole value is being applied without re-derivation is, as written, a regression.
2. **Re-anchor D1a.** Produce replacement text that keeps the `unreadable` verdict row, its ⛔ block
   and its merge-gate paragraph **unchanged**; keeps the `Reopens?` subsection and folds D1a's
   awaitable-versus-hard wording for `rate-limited` **into** it rather than duplicating it; and adds
   the `reviewed-empty` verdict and the required / optional / unclassified classification. Locate the
   span by its **quoted opening and closing sentences**, never by line number, and state in the
   proposal which sentences bound it.
3. **Re-anchor D1b.** Re-point it at Step 8 **condition 5** — verify the ordinal against the current
   text at the moment you write it — and reconcile it with the `Reopens?` clause the condition now
   carries. Keep the "⛔ This is a disclosure requirement, and it is NOT a block" paragraph verbatim:
   the shortfall changes what the run *says*, never whether it merges.
4. **Add the third-surface proposal (060 G6's method half).** The lane's reviewer read enumerates the
   comment surfaces a run must read. Propose adding the **PR-level reviews surface** to that
   enumeration, with the evidence from D3 item 5 — a bot that published only there was recorded as
   `silent`. Confirm from the current contract text whether the surfaces are enumerated at all before
   writing the proposal; if they are not, propose the enumeration and say so.
5. **Add the bridge-check proposal.** This plan's D1–D3 edit **other plans' directories** under
   `doc/plans/`, and the lane's Step 9 bridge row states that "no other plan's directory was touched"
   under a prohibition whose stated subject is *status or bookkeeping* writes. A declared
   record-correction deliverable is neither, but the contract does not say so. Report the
   disagreement as the first-instruction block requires, and propose wording that makes the exception
   explicit for a declared cross-plan record-correction deliverable while leaving the status and
   bookkeeping prohibition intact.
6. **Present, do not apply.** Record all four proposals in this run's report under the contract's
   "What have we learned" heading, each with the evidence from this run and the concrete proposed
   edit, and state in as many words that they await operator approval and that an approved change
   ships as a separate PR. Do not open that PR.

*Done when:* the run's report carries re-anchored D1a and D1b text located by quoted sentence rather
than line number, plus the two additional proposals; each proposal states which existing text it
preserves unchanged; a check against the current contract confirms that applying any of them would
remove neither the `unreadable` verdict nor the `Reopens?` subsection; and `cloud-plan-lane/SKILL.md`
appears in **no** commit of this run's branch.

## Out of scope

Every entry says why, because with no operator watching, this written boundary is the only thing
holding the line mid-run.

- **Rewriting git history — amending, rebasing or force-pushing any merged commit.** The merge
  commits are the substrate every correction in this plan is derived *from*; rewriting them would
  destroy the evidence and invalidate every SHA the corrected reports cite. A false sentence is
  corrected where it is read, not where it was written.
- **Re-opening, re-reviewing or re-titling any merged PR.** A merged PR cannot be changed without
  spending contended bot-review budget on a diff nobody can act on, and the epic's own bridge rule
  already records that a one-word bookkeeping PR is a waste of that budget.
- **Fixing the behavioural defects the same `gaps.md` files describe.** The overwhelming majority of
  those entries are code and contract fixes with their own risk profile and their own tests; several
  are already carried by the sibling plans `500`, `510` and `550` in this epic. Mixing a records diff
  with a behavioural diff means neither audience reviews either properly.
- **Editing `.claude/skills/cloud-plan-lane/SKILL.md`.** The lane forbids a run self-approving a
  change to the contract that governs it, and its Step 9 ships an approved contract change as a
  separate PR on its own branch. D5 produces proposals; nothing more.
- **Running the mutation pass 130 G18 asks for.** Mutating four suites to attribute ~80 tests is
  engineering work with a real test-suite footprint, disproportionate to a records plan and
  impossible to review alongside prose corrections. D4 item 8 records the obligation with its scope
  instead.
- **Deriving the cause partition of 040 G16's absence corpus.** It requires recovering per-PR diff
  sizes from merge commits across a historical corpus — a measurement campaign, not a record
  correction. D4 item 5 records that no measured partition exists and what that blocks, which is the
  branch the gap itself sanctions.
- **Creating GitHub issues as the tracked handle for D4 items 5–8.** An issue is not reachable from
  the clone, so this run's own verification could not confirm it exists, and it would put the
  obligation in a second record outside git — the same "recorded somewhere nothing reads" shape being
  corrected. Git-tracked standards files are used instead.
- **Editing any `gaps.md` or `verification.md`.** They are the audit's findings and the evidence this
  plan is derived from; correcting the report is what discharges a gap, not annotating the file that
  reported it.
- **Collecting or deleting any plan directory (cloud-bridge Path 3).** Collect is the orchestrator's
  local step and depends on `.plan/` state this run cannot see; a run that deleted a plan directory
  would destroy a record the orchestrator has not yet ingested.
- **Plan 050's own report file, and plan 040's, 070's and 080's directories.** 050 G16 directs its
  reconciliation into a successor report rather than into the landed one, and no other in-scope gap
  targets those files. A file not named in § Expected surface is not edited.
- **Plugin cache sync.** `/sync-plugin-cache` reads a git-ignored build tree and writes outside the
  repository; the standalone lane neither performs one nor records one as owed, even though this plan
  edits `marketplace/bundles/`.

## Expected surface

Records under `doc/plans/review-apparatus/` (each `{NNN}-…` abbreviated to its prefix):

- `010-…/report-01.md` — D1 item 1 (§§ D2, D4, Finding 4).
- `020-…/report-01.md` — D2 item 1 (the two verify figures).
- `030-…/report-01.md` — D4 item 3 (the two missing dispositions).
- `060-…/report-01.md` — D3, all six items.
- `090-…/report-01.md` — D1 item 2 (the PR citation).
- `090-…/plan.md` — D2 item 3 (the Deliverables opening; the only `plan.md` edited).
- `100-…/report-01.md` — D2 item 4 (the absence claim) and D4 item 7 (the residue cross-reference).
- `110-…/report-01.md` — D1 item 3 (§ Residue).
- `120-…/report-01.md` — D2 items 5 and 6 (mutation row A; the four bundled finding rows).
- `130-…/report-01.md` — D2 items 7 and 8 (the tallies; the two verify totals) and D4 item 8 (the
  open mutation-coverage obligation).
- `570-the-record-of-what-we-did-is-itself-unverified/report-01.md` — this run's own report: the D0
  index, D2 item 2's reconciliation, D4's verbatim cold reads, and all four D5 proposals.

Bundle standards documents:

- `marketplace/bundles/plan-marshall/skills/automatic-review/standards/bot-participation-contract.md`
  — D4 items 4 and 5.
- `marketplace/bundles/plan-marshall/skills/automatic-review/standards/pr-agent.md` — D4 item 6.
- `marketplace/bundles/plan-marshall/skills/automatic-review/standards/coderabbit.md` — D4 item 7.

Touched transiently and reverted, never committed (D2 item 5):

- `marketplace/bundles/plan-marshall/skills/automatic-review/scripts/review_completeness.py`
- `test/plan-marshall/automatic-review/test_structural_refusal.py`

**No Python change is expected in the final diff.** If `git diff --name-only origin/main...HEAD --
'*.py'` is non-empty at the build gate, the mutation revert failed — investigate before proceeding
rather than letting the gate absorb it.

## Claim labels

| Claim | Label | Confirm/refute artifact |
|---|---|---|
| `_existing_pr_comment_shas`, `_recorded_dropped_comment_shas` and `test_currency_anchor_is_derived_from_both_sha_sources` exist nowhere in the tree — an asserted **absence** | OBSERVED | A repo-wide search for all three returned hits only inside `doc/plans/review-apparatus/010-…/` (report, gaps, verification) and no source or test hit; **re-derive before editing, and publish the searched population** |
| The shipped currency reader is `_recorded_currency_records` with writer `_record_currency_records`, and the real test is `test_currency_anchor_is_recorded_in_the_ledger_on_credit` asserting one ledger source | OBSERVED | `workflow-integration-github/scripts/github_pr.py` and `test/plan-marshall/workflow-integration-github/test_github_pr.py` — resolve each name at the moment you write it |
| The `invalid_cap` guard and `--max-per-component` were introduced by `010ea461` (PR #1039), not PR #1153 | OBSERVED | `git log -S'invalid_cap' -- marketplace/bundles/plan-marshall/skills/manage-lessons/scripts/_lessons_query.py` returns exactly one commit; **re-derive** |
| Plan 110's report § Residue says "None blocking … No follow-up owed" while its `gaps.md` records five live items | OBSERVED | The report's § Residue and the directory's `gaps.md`; **confirm each item is still open before listing it** |
| Plan 060's merge commit changed four Python paths, one of them production (`gitlab_ops.py`, +11/−1) | OBSERVED, figures are leads | `git show {060's merge commit} --numstat`; **re-derive the paths and the line counts** |
| The `Verification loop exit:` line and the stale-base re-verification figure post-date plan 060's run | HYPOTHESIS | `git log -S` over `.claude/skills/cloud-plan-lane/SKILL.md` for each phrase, compared against ancestry of 060's merge commit — settle this before deciding not to add them |
| `sourcery-ai` published a weekly rate-limit notice on PR #1182's **reviews** surface, so `silent` is the wrong verdict | HYPOTHESIS | The PR's reviews surface, read through the GitHub MCP server (§ Notes, "What a clone cannot settle"). If the surface cannot be read, record the read as **unreadable** and do not downgrade it to a confirmation of either verdict |
| Deleting the 404/403-as-refusal block in `gitlab_ops.py` does not flip the `gitlab:merge-queue` off-routing test | OBSERVED | The fallthrough to `make_error`, which always sets `status: 'error'`, against the off-routing arm's assertion on `status` alone; the audit measured 18 passed under that mutant |
| Row A of plan 120's mutation table observes 9 failures, not 7, one of them in case (c) | HYPOTHESIS, count is a lead | The re-run in D2 item 5, against a tree first proven byte-identical to the landing commit; a drifted tree refutes the re-derivation rather than the row |
| Plan 130's commit `622f4484` added 91 tests across 8 test files and changed 6 production `.py` paths | OBSERVED, all four figures are leads | `git show 622f4484 -- 'test/**'` and `git show --name-only --format="" 622f4484`; **re-derive all four** |
| The squash commit message of `622f4484` states a different verify total from plan 130's report | OBSERVED | `git log --format="%B" -1 622f4484`; **re-derive the figure rather than copying it** |
| Plan 010's report contains no cold reading at all — an asserted **absence** | OBSERVED | A case-insensitive search for "cold" over `010-…/report-01.md` returned nothing; **re-derive** |
| Plan 050's report reports only a paraphrase of cold-read Q2, with Q1 and Q3 unanswered | OBSERVED | The report's § Findings verification-sub-agent bullet and § D4 staged-scenario section |
| Plan 030's report mentions neither the `--in-progress-bots ""` claim-label row nor the conditional endorsement-trap hint — an asserted **absence** | OBSERVED | A search for `in-progress-bots` and `endorsement` over `030-…/report-01.md` returned nothing; **re-derive** |
| The empty-argument cause class is closed by `nargs='?'`/`const=''` plus the executor's documented stripping | OBSERVED | `review_completeness.py`'s bot-observation flag registration, and the "Strip empty string args" branch in `tools-script-executor/templates/execute-script.py.template` |
| The 040 G14 insight is recorded nowhere in the `automatic-review` or `workflow-integration-github` bundle docs — an asserted **absence** | OBSERVED | Searches for "summary card" / "trigger acknowledg" over both bundles returned nothing; **re-derive and publish the searched population before writing "this is not recorded anywhere"** |
| The charter axis is a two-bucket partition, because exactly one commit touches `marketplace/targets/pr_agent/target.py` | OBSERVED, count is a lead | `git log -- marketplace/targets/pr_agent/target.py`; **re-derive — a second commit makes it three buckets** |
| `enable_prompt_for_ai_agents` appears nowhere outside plan 100's own directory — an asserted **absence** | OBSERVED | A repo-wide search for the flag name returned hits only under `doc/plans/review-apparatus/100-…/`; **re-derive** |
| D1a's opening and closing anchors still exist in `cloud-plan-lane/SKILL.md`, but the span between them now contains the `unreadable` verdict and the `Reopens?` subsection | OBSERVED | The current § "Record per-reviewer participation, from the bodies" block, read end to end; the line numbers in plan 050's proposals no longer locate it |
| The shortfall disclosure is now Step 8 **condition 5**, not condition 4, and carries a `Reopens?` clause | OBSERVED | The current § Step 8 numbered conditions; **re-verify the ordinal at the moment of writing** |
| The lane's Step 9 bridge row forbids a *status or bookkeeping* write outside the plan's own directory, and this plan's edits are neither | OBSERVED, the reading is the point at issue | The Step 9 contract-check table's Bridge row, read in full — this is the disagreement D5 item 5 reports, not one the run resolves |
| The 23 in-scope gap entries across 11 plan directories are as enumerated in D0 item 2 | HYPOTHESIS, both counts are leads | D0's own re-derivation from the listed gap ids and the directory listing; a collected directory or a fixed defect changes both figures, and D0 records the change |

## Verification

Beyond each deliverable's *Done when*:

**Cold read of the corrected records — the central check.** A corrected report is text whose whole
value is what a later reader concludes from it, so "the edit was applied" cannot settle it. Dispatch
the lane's pre-PR verification sub-agent to read each of the following **cold** — without this plan,
without the `gaps.md` files, and without the diff — and to report *which reading it took*, in its own
words:

1. Given only plan 010's corrected report §§ D2 and D4: *"Which symbols implement the currency
   anchor, and how many SHA sources does it read?"* The required answer names
   `_recorded_currency_records` and **one** source. An answer naming two sources, or naming a symbol
   the reader then cannot find in the tree, means the correction failed.
2. Given only plan 060's corrected report: *"Did this run change production source, and what was its
   outcome?"* The required answer is yes — naming `gitlab_ops.py` — and a contract-legal outcome. An
   answer of "no production source was changed", or "the run is still in progress", means the
   finalization failed.
3. Given only plan 060's corrected § Reviewer participation: *"Did `sourcery-ai` review this PR, and
   is that gap worth re-requesting?"* The required answer distinguishes a **rate limit that reopens**
   from a skip. An answer of "silent" means the correction failed.
4. Given only plan 110's corrected § Residue: *"Is follow-up owed on this plan?"* The required answer
   is yes, with the items nameable. An answer of "no, it is closed" means the correction failed.
5. Given only D5's re-anchored D1a text: *"Which reviewer verdicts can I record, and what do I do
   when I cannot read a reviewer's surface at all?"* The required answer still includes
   **`unreadable`** as a distinct verdict. An answer that omits it means the re-anchoring reverted a
   landed improvement — which is the entire reason D5 exists.

Record every answer **verbatim**. A paraphrase is the failure plan 050's report already committed.

**Re-derivation at the moment of the claim.** A correction is a claim too. Every figure this run
writes — into a corrected report, into a standards file, or into its own report — is re-derived by a
command run *now*, and the run records the command and its substrate beside the figure. **No figure
in this plan may be copied from this plan.** After each count is corrected, **re-count it against the
edited file** and confirm the stated number matches what the file now contains; a corrected count
that was never recounted is the original defect with a new value.

**Symbol and citation resolution sweep.** For every symbol name, test name, file path, PR number and
commit SHA that appears in the *edited* portion of any report, resolve it: symbols and tests against
the tree, PRs and SHAs against `git log`. Report the sweep's population size and its result. An
unresolvable citation is a blocker, not a note.

**Sweep-and-count on the corrections.** A claim is corrected at every site or it is not corrected.
Where a report states the same wrong fact in more than one section — plan 060's `sourcery-ai` verdict
appears in both § Reviewer participation and § Contract check Step 8; its falsifiability claim in
both § D3 and § Residue — sweep the whole file and record the match count before and after.

**Documentation standards on every edit.** Confirm by reading that no correction introduced a date, a
version number, a changelog section, or a "RECENT CHANGES"-style block. **The one exception is this
run's own `report-NN.md`**, which is a dated record of one execution and legitimately carries a date
and an ordinal — do not "correct" it, and do not add a date to any other file. The other reports'
existing date headers are likewise legitimate and are left alone.

**No `.plan/` access.** Confirm the run opened no path under `.plan/` and reported no fact derived
from one.

**Build gate.** This plan is expected to change **no Python**. State the
`git diff --name-only origin/main...HEAD -- '*.py'` verdict explicitly; an empty result is recorded
as the measurement it is, and a non-empty one is investigated before the gate is run (see § Expected
surface).

**Review label.** This PR changes bundle standards documents and one `plan.md` — behavioural prose a
later run executes — so it is reviewed like code. **Do not apply `skip-bot-review`**, notwithstanding
that most of the diff is records.

**No collateral change.** Compare the final diff against § Expected surface and report every file
touched that is not listed, with the reason.

## Notes

**Where the evidence lives.** This plan is derived from an epic-wide audit of the landed
`review-apparatus` plans. The per-gap evidence — file:line citations, the commands run, the probes,
and the suggested groupings — is git-tracked and readable from any clone at
`doc/plans/review-apparatus/{NNN}-…/gaps.md`, with the supporting analysis in the sibling
`verification.md`. Those files are **supporting evidence, not required reading**: every defect,
mechanism and *Done when* this plan depends on is restated above, and the run can execute the plan
without opening one. Open them when a gap's evidence is worth seeing in full — and note that a gap
entry's own figures are leads, exactly as this plan's are.

**Effectively nothing under `.plan/` exists here.** The orchestrator ledger, the plan specs, the
findings store and the landing records are git-ignored and therefore absent from this clone. Do
**not** go looking for one. Two paths under `.plan/` *are* tracked and so do exist
(`.plan/marshal.json` and `.plan/project-architecture/`, per `.gitignore:45-47`) — re-derive that
from `.gitignore` rather than trusting this sentence — but no deliverable here reads either. D0
halts rather than substituting a hand-maintained list for a derivation.

**What a clone cannot settle.** One claim in this plan — that `sourcery-ai` published a rate-limit
notice on PR #1182's PR-level reviews surface — is about a GitHub surface, not about the tree. In a
cloud session the GitHub MCP server is the expected path for it. If that surface cannot be read,
record the read as **unreadable** and say so: `unreadable` and `silent` are opposite claims, and
collapsing the first into the second converts a gap in the run's evidence into a positive statement
about a reviewer. That is the same defect D3 item 5 is correcting.

**Two conventions settled at authoring time**, so the run never faces a decision it has no operator
to resolve:

1. **Corrections are made in place, in the record that carries the false sentence** — not in a
   parallel errata document — with one exception: **050 G16**, whose own *done when* directs the
   reconciliation into a successor report, so plan 050's report is not touched at all. The reason for
   the general rule: a run report is what the orchestrator's collect step reads an outcome from, and
   a reader who reaches a false sentence must not need a second document to learn it is false.
2. **A figure is never silently swapped when it was a genuine measurement** — it is labelled with the
   commit or round it measured. A figure that is simply wrong about a commit is restated. Where a gap
   entry states which of the two it wants (130 G14 asks for a plain restatement with no note; 020 G19
   and 130 G15 ask for labelling), the gap's instruction wins. The gaps disagree with each other on
   this point; the disagreement is resolved here, once, and not reopened mid-run.

**This plan edits other plans' directories, and the contract's bridge check does not obviously permit
it.** The lane's Step 9 bridge row states that no **status or bookkeeping** write may land under
`doc/plans/` outside this plan's own directory, and lists "no other plan's directory was touched"
under that prohibition. A declared record-correction deliverable is neither a status write nor
bookkeeping — but the contract does not say so. Per the first-instruction block, **the contract wins
and the disagreement is reported**: the run proceeds with the corrections as declared deliverables of
this plan, reports the disagreement in its contract check, and carries a wording proposal into D5
item 5. Do not silently ignore the row, and do not abandon the deliverables over it.

**A dated run report is not a defect.** A `report-NN.md` under `doc/plans/` is the one artifact in
this tree that legitimately carries a date and an ordinal, because it records one execution rather
than the current state. The repository's "no timestamps" documentation standard does not reach it. Do
not strip a date from any report while correcting it, and do not treat an existing date header as one
of this plan's targets.

**Line numbers are deliberately absent from this plan.** The `gaps.md` files carry them; this plan
names files, sections and quoted sentences instead, because a line number authored here and read
after an intervening commit points at the wrong statement — which is exactly how plan 050's contract
proposals went stale. Locate every edit site by quoted sentence or by symbol name, and locate D5's
proposal spans the same way.

**Ordering.** D0 gates everything. D1, D2 and D3 are independent of one another and may land in any
order. D4's items 1, 3, 4 and 5–8 are independent; **D4 item 2 (the 050 cold read) depends on D5**,
because it reads D5's re-anchored text. D5 depends on nothing except D3 item 5, whose observation it
carries into a proposal — so settle D3 item 5 before writing that proposal.

**Sibling plans in this epic.** `500`, `510` and `550` take the behavioural defects from the same
audit. This plan takes only the records, and the two sets are disjoint by construction: where a gap
here names a remedy that is code (060 G3's off-routing discrimination, 100 G1's STRIP-rule
correction), this plan states the record truthfully and leaves the remedy to the plan that owns it.
The plans may run concurrently — their expected surfaces do not overlap, with the single exception of
the `automatic-review/standards/` documents, where this plan appends stated open items and the
sibling plans correct prose. If a conflict appears at the merge gate, it is a conflict in a standards
document, not in behaviour.
