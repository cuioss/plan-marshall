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

# The cloud-plan-lane contract carries rules with no receipts, and its run reports carry false claims

**Epic:** truthful-signals
**Branch prefix:** `chore` — every change is prose in a governing skill or in a landed run report; no
buildable source is touched. (A cloud session keeps its pre-assigned `claude/*` branch; the prefix
governs only a branch this run cuts itself — see the contract § Step 2.)

## Problem

Twenty-four defects, filed across twelve already-landed plans in this epic, resolve into two mechanisms
in one place.

**The first is in the contract itself.** `.claude/skills/cloud-plan-lane/SKILL.md` ships rules whose
inputs it declares unobtainable, facts it never probed stated as flat fact, and obligations with no
artifact that proves they were met. § Step 8 condition 1 instructs the run to derive which context
blocks from `(required contexts ∩ non-green contexts)` (`SKILL.md:1342-1349`) while the same
condition, forty lines above, states that the ruleset-config API is unreachable on the cloud MCP path
(`:1303-1305`) — so the left operand cannot be enumerated and the paragraph has no terminus a cloud
run can reach. § Cloud session affordances states three facts as confirmed (`:54` no `gh`; `:56`
ruleset API not reachable; `:57` arming queues at once) that the run which wrote them recorded as
*reported-only, not probed*, and its `:56` row still says to read required-ness from
`mergeStateStatus` while `:1315-1321` establishes the MCP payload has no such key and the field is
`mergeable_state`. And condition 1's non-required-context **disclosure** obligation (`:1338-1340`)
has no report artifact anywhere: the Step-9 contract-check row `| 8 Merge gate |` (`:1504`) demands
none, and the § Report template (`:1563-1693`) has no merge-gate section — while the sibling
disclosure it was modelled on, condition 4's review-coverage shortfall, *does* carry one at `:1663`.
(Every `SKILL.md` line number in this plan is HEAD-anchored at authoring time and is a **lead**: that
file moves, so locate by the quoted text, never by the number.)

**The second is in the run reports the contract produces**, and it is the same mechanism one layer
out. Fifteen of the twenty-four defects are false statements standing in landed `report-01.md` files:
counts that do not re-derive, unresolved template placeholders read as "the run recorded nothing",
sections written early and never reconciled with what the run later did, and absence claims the same
file contradicts. The contract already carries the rule that would have caught five of them — "**A
count derived by looking is a sample.** State how it was derived, and re-derive it at the moment of
the claim" (`SKILL.md:1701-1702`) — and it was violated in four separate plans. The rule is not the
missing part. The **receipt** is: Step 9's self-check has a row for every step's artifact and none for
whether the report's own claims survive a re-read, so a run finishes its contract check green with a
report that contradicts itself. That is exactly the shape of the merge-gate defect above, which is
why both belong in one plan.

The sharpest instance is plan 450's own report. Its D0 product *is* an observation table — the plan
made the run its own live fixture — and three of its cells assert the run observed nothing where it
observed the affordance directly: `:34` "no PR opened", `:36` "no arming this run", `:185` "not
exercised for GitHub operations this run (no PR)", in a file that opens PR #1147 at `:3`, reads its
comment surfaces at `:120` and arms auto-merge at `:162`. The mechanism is visible in the commit
list: the D0 table landed while the run was still partial, and the later commits updated the header
and the contract-check rows without revisiting D0.

## Goal

The lane contract states no rule whose inputs it declares unobtainable, states no affordance fact
above the evidence grade the corpus actually has, and demands an artifact for every obligation it
imposes — including a new one for the truthfulness of the report itself, so the class of false claim
this plan sweeps out of ten landed reports cannot be re-introduced by the next run without the
Step-9 check reporting it as not done. The ten reports, which are still uncollected and are the
evidence corpus later plans in this epic mine, say what their runs actually did.

## ⛔ Declared Bridge excursion — read before Step 4

This plan's D1, D5 and D6 **edit run reports inside ten other plans' directories** under
`doc/plans/truthful-signals/`. The contract's Step-9 row `| 8 Bridge |` (`SKILL.md:1505`) states
flatly that "no other plan's directory was touched", while permitting "a **declared-deliverable**
edit to a shared lane doc". This plan and the contract therefore disagree, and the first-instruction
block requires the run to **report the disagreement** rather than resolve it silently. The resolution
is decided here, in advance, so the run needs no mid-run decision:

1. **Make the edits.** They are declared deliverables of this plan, named file by file below. What
   the Bridge row protects is the *substance* — no status write, no ledger, no bookkeeping row in
   another plan's directory — and none of that is done here. Prior art: plan 450's run made the same
   excursion (its `report-01.md:181` records it as an operator-directed, declared exception).
2. **Touch nothing else** under `doc/plans/` — no file outside the ten `report-01.md` files named in
   § Expected surface and this plan's own directory. Any other write there is scope drift.
3. **Report row 8 Bridge as a declared excursion**, naming the ten directories and stating that no
   status or bookkeeping write was made.
4. **Record a proposal, do not ship it** (D4, item d): that the Bridge row's wording be widened to
   cover a declared-deliverable edit to a sibling plan's *report* the same way it already covers a
   shared lane doc. This is a change to the very rule that would license this plan's own excursion —
   the sharpest self-approval case there is — so it goes to § What have we learned as a proposal for
   the operator, never into this PR.

**On the contract edits themselves (D2, D3, D4, D7).** These are *declared deliverables of a plan the
operator handed over*, not a run deciding from its own experience that the contract should change.
The prohibition at `SKILL.md:1544` ("Never self-approve a change to the contract that governs you")
governs the second case and does not bar the first — plans 030 (PR #1137) and 450 (PR #1147) both
landed deliverables in this same file. Any **further** contract gap this run notices, beyond the
deliverables below, is recorded as a proposal in § What have we learned and is **not** shipped in
this PR.

## Deliverables

D0 gates every other deliverable. D1 carries the plan's only `high` gap and lands first after the
gate. D2–D4 and D7 are the contract half — prose in a governing skill; D1, D5 and D6 are the record
half — corrections inside landed run reports.

Where a gap's *Fix* offered the run a choice between two remedies, **this plan has already chosen**;
the choice is stated in the deliverable. The run makes no such decision.

0. **D0 — GATE: re-derive the defect population and its class map** *(gates D1–D7; closes no gap on
   its own)*

   The evidence base for every deliverable below is the git-tracked gap documents at
   `doc/plans/truthful-signals/{source-plan}/gaps.md`, one `## G{n}` entry per defect, with the
   sibling `verification.md` § Adversarial review carrying what was upheld, refuted or re-severitied.
   Nothing in this plan requires a file outside the clone.

   a. **Reproduce each of the 22 in-scope gaps at HEAD.** For each id named in D1–D7, open the file
      and line its **Where** clause names and record `reproduces` / `already-closed` / `moved`. Line
      numbers in a gap document are **leads, not addresses** — the contract file is long and has been
      edited since; locate by the quoted text, not by the number. A gap that no longer reproduces is
      recorded in the report as *already closed by `{sha}`* and **dropped**, never re-fixed.
   b. **Classify each of the 15 report-accuracy defects into exactly one class:**
      **C1** unresolved template placeholder (`_pending_`, `(Recorded at close.)`, a duplicated
      template heading); **C2** a section never reconciled with what the run later did; **C3** a
      stated count that does not re-derive; **C4** an absence or negative claim ("not probed", "none",
      "no build", `silent`) that the same file or the tree contradicts.
   c. **Name, per class, the receipt a Step-9 check could demand** — a check the run can perform on
      its own report with no input the lane lacks. This is D4(c)'s input.
   d. **Decide, per correction in D5 and D6, what substrate settles it**: the clone alone, a live
      GitHub read over the MCP surface, or neither. A correction whose substrate is unavailable at
      the moment of the edit is written as **the claim withdrawn with its substrate named** — never
      as a value transcribed from the gap document, which is a second-hand reading of a surface this
      run did not read.

   ⛔ **STOP CONDITIONS.** (i) If the `gaps.md` files named in § Expected surface are not present in
   the clone, the plan has no evidence base: **stop and report the run blocked**, naming what was
   missing. (ii) If step (c) leaves any class with no receipt a run can perform on its own report,
   **do not invent one and do not ship a prose rule in its place** — drop that class from D4(c),
   record it in the report as an unguarded class with the reason, and continue. Do **not** substitute
   a hand-maintained checklist of known-bad phrasings for a derivable check; that is the defect class
   this epic exists to remove, reproduced inside its own fix.

   *Done when:* the report carries one row per in-scope gap id with its reproduction verdict, one
   class label per report defect, a receipt (or an explicit "no receipt available, dropped") per
   class, and a substrate decision per D5/D6 correction — and any gap recorded `already-closed` names
   the sha that closed it.

1. **D1 — Plan 450's report says what its run actually did** *(closes 450/G1 `high`, 450/G2, 450/G5)*

   All three sites are in
   `doc/plans/truthful-signals/450-cloud-lane-assumes-local-runtime-affordances/report-01.md`.
   Each correction states the run's **final** state; where a cell was accurate when written and only
   its stated reason is false, correct the reason and keep the verdict — the three cells are not
   wrong in the same way.

   a. **§ D0 table, "Self-wake / polling"** — the verdict *not probed* is correct (nothing in the
      report shows `send_later` or `subscribe_pr_activity` being invoked); the reason "no PR opened"
      is false. Replace the reason with what the run did instead (drove the cycle by direct read).
   b. **§ D0 table, "Auto-merge arming"** — the run armed auto-merge (`report-01.md:162`). Mark it
      **confirmed here**, and record what the arm call returned and whether the arm was observable
      afterwards.
   c. **§ Contract check, "GitHub access path"** — replace "not exercised … (no PR)" with the
      surfaces the run actually used (`create_pull_request`; `pull_request_read` for the comment
      surfaces; `enable_pr_auto_merge`), re-derived from the report's own body, not assumed.
   d. **§ Reviewer participation, the `sourcery-ai` row** — verdict `silent` → `rate-limited`, with
      the review-summary body as its evidence, and a note that the *check-run* concluding `skipped`
      is not evidence of silence: the finding lived on the review-summary surface (`get_reviews`),
      which the contract at run time did not name. Add one line to § Merge gate condition 2 recording
      that the condition was established over two of the three comment surfaces, the third read only
      retrospectively. The body text is quoted verbatim in
      `450-…/gaps.md` § G2; per D0(d), if the live `get_reviews` read on the PR is unavailable, quote
      it **as recorded in that gap document and say so** rather than presenting it as a fresh read.
   e. **§ Deliverables preamble, the commit list** — name every commit the run made on the branch
      with a one-phrase role each, re-derived at the moment of the edit (the live PR's commit list,
      or `git log` over the plan directory — state which). The current sentence names three and
      asserts a trailer property over that smaller set; `fbf1438`, the commit carrying the Bridge
      excursion the report elsewhere declares, is absent from it.

   *Done when:* no statement in `450-…/report-01.md` asserting an absence — no PR, no arming, no
   GitHub operation, a `silent` reviewer — is contradicted by another statement in the same file;
   every § D0 "this run" cell reflects the run's final state rather than its state when the row was
   written; and the commit sentence's stated scope matches the set it names, with the derivation
   named.

2. **D2 — § Cloud session affordances carries its evidence grade and points at one authority**
   *(closes 450/G3, 450/G4; closes the affordance-row half of 030/G3)*

   All edits in `.claude/skills/cloud-plan-lane/SKILL.md` § Cloud session affordances — the
   affordance table and the `gh` ↔ MCP mapping table beneath it.

   a. **Grade the three unhedged rows.** GitHub access, Ruleset-config API and Auto-merge arming are
      stated as flat fact; the D0 table of the run that wrote them marks their backing facts
      *reported-only / not probed* (GitHub access is the partial case — the MCP server's *presence*
      was confirmed, the absence of `gh` was reported only). Reword each to carry its grade, matching
      the form the Self-wake row already uses ("may be **approval-gated**"), and leave the
      operational instruction that follows each fact unchanged. § GitHub access already says "Never
      assume a tool is present — check"; after this the same page no longer half-contradicts it.
   b. **Correct the stale cell.** The Ruleset-config row says to read required-ness from
      `mergeStateStatus`; the MCP `get` payload has no such key (§ Step 8's field note, and the
      mapping row that already names both spellings). Name both spellings on the row.
   c. **State the index/detail relationship at the head of the table**: each row is a **pointer**
      whose authoritative wording is the linked `§`, so a future edit to a fact is made in the step
      and only summarized here. This satisfies the intent of "the affordance facts appear in exactly
      one place" — one *authoritative* place — without deleting the index the section exists to be.
      Apply the same rule to the three comment-surface mapping rows, leaving the three-surface table
      in § Step 7 authoritative. ⛔ **Preserve the operational imperatives** while removing the
      restated prose: a reader of the mapping table must still learn that `get_comments` is not
      sufficient alone and that the review-summary surface **MUST be read before the merge gate**.
   d. **Name the required context on the Ruleset-config row** (030/G3): on this repository it is
      `verify / conclusion` — cited to § Step 2 and `CLAUDE.md` § Branch Naming, which both already
      state it — marked **operator-maintained, re-read whenever the `main` ruleset changes**, and a
      run never derives or extends it for itself. ⛔ This goes on the affordance row, **not** into
      condition 1, whose own text must continue to name no individual check.

   *Done when:* every row in § Cloud session affordances either states a fact confirmed by a named
   artifact in this repository or is phrased as an observation the reader is told to re-check; no
   affordance row names a field, tool or trigger that its linked section contradicts; the table states
   which side is authoritative when they differ; the mapping rows no longer restate the § Step 7
   table's prose while still carrying its two imperatives; and the Ruleset-config row names the
   required context with its provenance and its operator-maintained marker. Verified by cold read
   (§ Verification).

3. **D3 — Merge gate condition 1 terminates somewhere a cloud run can reach** *(closes 030/G2;
   closes the condition-1 half of 030/G3)*

   In `.claude/skills/cloud-plan-lane/SKILL.md` § Step 8 condition 1, the `BLOCKED` paragraph.

   Add the unobtainable-operand case the paragraph omits: on an access path where the required set is
   not enumerable — the cloud MCP path, per § Cloud session affordances — the run **names no blocker
   at all** and instead discloses the facts it can establish, in this shape: "`mergeable_state:
   BLOCKED`; the required set is not enumerable on this access path; the non-green contexts on head
   `{sha}` are X, Y." Point at the affordance row D2(d) amends as the approximation the disclosure may
   cite. Keep the existing prohibition on promoting a salient non-required status to "the blocker".

   ⛔ Do **not** close this by writing a list of this repository's required checks into condition 1.
   The condition must still name no individual check, and a hand-maintained required-check list in the
   contract is what the source plan's own STOP condition forbade. The remedy is an explicit
   "cannot determine" branch, not a hardcoded set.

   *Done when:* § Step 8 condition 1 contains no instruction whose inputs the same section declares
   unobtainable — every path through the `BLOCKED` paragraph terminates in a disclosure a cloud run
   can actually produce — and the condition still names no individual check. Verified by cold read
   (§ Verification).

4. **D4 — Every obligation the contract imposes gets an artifact that proves it was met**
   *(closes 030/G4, 220/G5)*

   All in `.claude/skills/cloud-plan-lane/SKILL.md`. One mechanism, four items: a rule shipped
   without a receipt is a self-check that passes while proving nothing.

   a. **The condition-1 disclosure gets its receipt** (030/G4). Extend the Step-9 contract-check row
      `| 8 Merge gate |` so it demands, where any non-required context was pending, failed or absent
      at arm time, that the report states which contexts they were and that the condition-1 disclosure
      was made — or states that every context on the head was green. Add a `## Merge gate` section to
      the § Report required-content template, between `## Reviewer participation` and `## Cost`,
      requiring: the merge-state read and the head SHA it was read at; conditions 1–3 with their
      evidence; and the condition-1 non-required-context disclosure verbatim (or "every context
      green").
   b. **The `CHECK_ERA` obligation is stated, with its receipt** (220/G5). Neither `CHECK_ERA` nor
      `era_stamp_fill` occurs anywhere in the contract today. Add to § Step 4 (or § Step 8, whichever
      the surrounding text makes the better home — the run picks the location, not whether to add it):
      a change that alters an `audit-archived-plan-retrospectives` check's semantics obliges a
      `CHECK_ERA` bump to the `PR-PENDING` sentinel while working, resolved after create-PR by running
      `.claude/skills/finalize-step-era-stamp-fill/scripts/era_stamp_fill.py` with the real PR number,
      committed and pushed **before the merge gate** — because the finalize step that normally does
      this does not fire in this lane, and a literal `PR-PENDING` landing on `main` poisons the era
      model every archived-plan audit reads its rows against. Verify the script path, its flag
      spelling and the lock-step test mirror by reading the script at the moment of the edit; the gap
      document's spelling is a lead. Add a contract-check row so the obligation has an artifact.
   c. **The report's own truthfulness gets a receipt** — the recurrence control for classes C1–C4
      derived in D0(b–c), and the reason the D5/D6 sweep is worth its cost. Add to § Step 9 a
      report-consistency check, sited beside the existing "Re-verify every report claim about the
      working tree" paragraph, which that paragraph is the precedent for. Restricted to the classes
      D0(c) produced a run-performable receipt for; the shape to aim at:
      - **every count in the report is re-derived at finalize** and states the command or artifact it
        was derived from — the contract's existing "a count derived by looking is a sample" rule
        (§ Rules that outrank convenience) gets the artifact it currently lacks;
      - **no absence or negative claim survives unchecked** against the run's own later sections — a
        cell written before the PR existed is re-read against the run's final state;
      - **no template placeholder and no duplicated template heading survives** into the committed
        report;
      - the **`PR:`** header field is filled, or states why it cannot be.
      Add the matching contract-check row so a report failing any of these is reported as **not
      done** at Step 9 rather than done.
   d. **Record the Bridge-row proposal** (§ Declared Bridge excursion, item 4) in § What have we
      learned. **Proposal only — not shipped in this PR.**

   *Done when:* the `| 8 Merge gate |` row names an artifact for the condition-1 disclosure and the
   § Report template has a section that artifact lands in; the contract names `CHECK_ERA` and
   `era_stamp_fill.py` with a contract-check row attached; § Step 9 carries a report-consistency check
   whose every clause is one D0(c) produced a receipt for, with a contract-check row; the report
   records the Bridge proposal as a proposal; and a run that armed with a pending non-required context
   and did not disclose it, or committed a report containing an unresolved placeholder, is reported as
   **not done** at Step 9 rather than done. Verified by cold read (§ Verification).

5. **D5 — Seven corrections across six landed reports, reconciled with what their runs did**
   *(closes 220/G4, 110/G4, 110/G5, 060/G4, 160/G7, 370/G4, 260/G4 — classes C1 and C2; 110 takes two
   of the seven, which is why the file count is one lower than the correction count)*

   One edit per instance, in the file each gap names. Findings are recorded per instance, not bundled.

   a. **220** § Deliverables, the D1 bullet — the bullet says the blindnesses were "quantified" and
      then lists three emitted field names, which is the mechanism, not the number. **Chosen remedy:**
      state plainly that the delta could not be measured in this environment, name the audit command
      that would measure it, and drop the word "quantified" for the field list. The alternative — run
      the audit — is not available: it needs `.plan/work/change-ledger.jsonl` and a populated
      `.plan/local/archived-plans/`, and `.plan/` is git-ignored and absent from this clone.
   b. **110** § Build gate — it asserts "no local build was run", while § Run continuation in the same
      file records `./pw quality-gate` with `total_issues: 0`. Append one sentence: the pre-PR gate
      correctly skipped the build on the docs-only footprint, and a local build was subsequently run
      during the run continuation.
   c. **110** § Contract check rows 2 and 7 — they record a branch and PR the run superseded; the
      report's own header at `:3` already names the branch and PR that landed. Update both rows to
      the landed values, marking row 2 as an operator-directed re-issue away from the harness-assigned
      branch, and keep the re-issue reason already given in § Run continuation. The contract-check
      table is a *conformance* record, so a stale row there reads as a compliance fact that is false.
   d. **060** header line — `**PR:** _pending_` → the PR number, re-derived at the moment of the edit
      from the plan directory's git history (`git log --oneline -- {plandir}`).
   e. **160** — delete the second, `_pending_` `## Cost` heading and its body; the filled `## Cost`
      section earlier in the same file stands.
   f. **370** — delete the four trailing `(Recorded at close.)` placeholder sections (`## Cost`,
      `## Contract check (Step 9)`, `## What have we learned (Step 9)`, `## Residue`); filled versions
      of all four already appear earlier in the file.
   g. **260** § D0, the direction-2 paragraph — "none" holds only under the narrowed scope "fields
      inside a step doc's own `prompt:` block". State the scope actually swept, and record the
      dispatcher's runtime-input class (`iteration`, `producer`, whitelisted `session_id`) as the
      direction-2 population it did not cover.

   *Done when:* each of the seven corrections satisfies its gap's own *Done when*; and, checked once
   per touched file across the six, no
   `_pending_` or `(Recorded at close.)` placeholder remains, no template heading occurs twice, and no
   § Build gate or § Contract check statement is contradicted by another section of the same file.

6. **D6 — Five stated counts re-derived, not transcribed** *(closes 040/G4, 260/G5, 430/G4, 430/G9,
   440/G5 — class C3)*

   ⛔ **Every figure below is a lead. Re-derive it at the moment of the edit and state the derivation
   beside it** — the numbers in the gap documents were derived against a tree that has since moved,
   and transcribing one would commit, inside the fix, the exact defect being fixed. Where a figure
   is about the state at a landed commit rather than at HEAD, derive it at that commit and say so.

   a. **040** § D3 — the "boundary harness (10 positive / 10 negative)" figure is not re-derivable
      from any committed artifact, and the committed negative parametrization has a different count.
      **Chosen remedy:** state the committed counts, re-derived from the test file, and mark the
      ad-hoc harness explicitly as an uncommitted run-time artifact. Do not simply delete the figure.
   b. **260** § D3 — the stated test count for `test_step_prompt_fields_contract.py`. The same figure
      appears a **second** time in § Findings ("ran the N tests green"); fix **both** sites.
   c. **430** § D3 — the case count for `test_non_finish_discrimination.py`, derived at the commit the
      report documents, with the collection command named.
   d. **430** — the case count for `test_pre_commit_verify_freshness.py`, stated at **two** sites
      (§ D1 gate row #7 and § D3); fix both, and derive it from the *landed diff's added test
      functions*, which is the population the report is claiming — not from the file's total at HEAD.
   e. **440** § D0 — "the three EARLIEST head-dependent steps (`order` 4, 6, 7)". Re-derive the
      head-dependent order set from step frontmatter and correct the enumeration. The follow-on
      "consistent with that ordering" inference rests on the same premise: either drop it or restate
      it as an unverified observation, since the cited counts are not monotone in `order`. The claim
      appears a **second** time in the report's claim-labels table; fix both sites.

   *Done when:* each corrected figure equals what its named derivation returns when re-run, the
   derivation is stated in the report beside the figure, and for the three two-site cases both sites
   agree.

7. **D7 — The authoring skill names the population-derivation mechanism** *(closes 040/G5)*

   In `.claude/skills/author-cloud-plan/SKILL.md` — which today contains no occurrence of
   `population-derived`, `_dispatch_roster` or `implements:`. Add a short paragraph stating that a
   plan calling for a population-derived detector must name the derivation mechanism; that the
   mechanism for dispatched-doc populations is the ext-point `implements:` frontmatter (or the
   extension-discovery helper where the surface matches); and that `test/_shared/_dispatch_roster.py`
   is a Markdown-section parser for finalize step rosters and **not** a population source. Cite the
   reference implementation named in the gap, after confirming the symbol still exists at HEAD.

   The cost of not having this is measured: two plans in this epic (040 and 050) named
   `_dispatch_roster.py` as the pattern, and 050's own run then rediscovered the mis-pointer from
   scratch — the cost was paid twice, and the mis-pointer still stands at
   `doc/plans/truthful-signals/050-migration-shims-have-no-expiry/plan.md`. Correcting that plan's
   text is **not** in scope (see § Out of scope).

   ⛔ Respect the skill's own § Boundary: it carries only judgement with no home elsewhere and points
   at owning documents rather than restating them. Write this as authoring judgement plus a pointer,
   not as a copy of the detector's implementation notes.

   *Done when:* `.claude/skills/author-cloud-plan/SKILL.md` names the frontmatter-derivation mechanism
   for population-derived detectors and explicitly rules out `_dispatch_roster.py`, and the reference
   implementation it cites resolves at HEAD. Verified by cold read (§ Verification).

## Out of scope

- **030/G1 — settle the documented merge-queue arming command.** Its *Done when* requires a recorded
  observation of `gh pr merge {N} --squash --auto` against a live PR. § Cloud session affordances
  records that a cloud session has no `gh` CLI and cannot reach `api.github.com`; both branches of the
  gap's fix depend on that observation, so a lane run could only guess at it. The gap's own source
  says as much — `030-…/verification.md` § "Residual doubt" states it "cannot be resolved from this
  session" and names an operator with a `gh` CLI as the actor. Excluded, not dropped: it stays open in
  its gaps document. *(Note: the assignment list for this plan carried it as `medium`; the source
  `gaps.md` and its § Adversarial review re-severitied it to `low` after the production-code evidence
  originally cited was refuted by execution. The lower severity is the one this plan trusts.)*
- **230/G3 — open plan 230's D0 measurement gate.** Its substrate is the archived CI-manifest corpus
  under git-ignored `.plan/`, which is absent from a cloud clone by construction and, per the gap
  itself, absent from a normal developer checkout too. No committed artifact can be produced from this
  environment, so a deliverable here could only restate the blockage the gap already records.
- **Every other gap in the twelve source `gaps.md` files** (re-derive the directory set; it is not
  the same set as the ten reports this plan edits)**.** Only the 24 ids named above are assigned to
  this plan; the rest belong to sibling plans in this epic. Editing one here would duplicate another
  plan's work and collide with it on the same files.
- **The code and skill defects the source plans' other gaps name** — `_gate_coverage.py`, `audit.py`,
  `_analyze_argument_naming.py`, `equality_check.py`, `verdict_currency.py` and the rest. This plan
  changes prose in a governing skill and in landed run reports; touching production Python would put
  two audiences in one diff and pull the build gate over a change none of these deliverables needs.
- **Anything in a touched `report-01.md` beyond the statements the gap documents show to be false.**
  A run report is a dated record of one execution, exempt from the "no timestamps" and "current state
  only" standards (`CLAUDE.md` § Standalone Plan Lane). This plan corrects falsehoods; it does not
  restyle, re-date, re-scope or re-narrate a record. Anything that was true when written and is merely
  *dated* stays exactly as it is.
- **The mis-pointer in `050-…/plan.md`.** It is a queued plan's own text; rewriting another plan's
  brief mid-queue changes what a future run is asked to do without that run or its author knowing. D7
  closes the durable half by putting the correct mechanism in the authoring skill.
- **Correcting `SKILL.md:150` / `CLAUDE.md:21`** — the two places that already name the required
  context. 030/G3 offers that only as the alternative to recording the set; D2(d) takes the recording
  branch, so no correction there is owed.

## Expected surface

- `.claude/skills/cloud-plan-lane/SKILL.md` — D2 (§ Cloud session affordances + the `gh` ↔ MCP mapping
  table), D3 (§ Step 8 condition 1), D4 (§ Step 4 or § Step 8, § Step 9, § Report).
- `.claude/skills/author-cloud-plan/SKILL.md` — D7.
- `doc/plans/truthful-signals/450-cloud-lane-assumes-local-runtime-affordances/report-01.md` — D1.
- `doc/plans/truthful-signals/220-build-ledger-is-the-build-time-oracle/report-01.md` — D5(a).
- `doc/plans/truthful-signals/110-landed-residue-promotion-sweep/report-01.md` — D5(b), D5(c).
- `doc/plans/truthful-signals/060-invented-plan-scoping-flags-are-an-overgeneralized-convention/report-01.md`
  — D5(d).
- `doc/plans/truthful-signals/160-build-gate-coverage-parity/report-01.md` — D5(e).
- `doc/plans/truthful-signals/370-multi-target-generator-edge-paths/report-01.md` — D5(f).
- `doc/plans/truthful-signals/260-the-generic-dispatch-template-cannot-carry-a-step-specific-mandatory-field/report-01.md`
  — D5(g), D6(b).
- `doc/plans/truthful-signals/040-inert-thinking-directives-in-dispatched-docs/report-01.md` — D6(a).
- `doc/plans/truthful-signals/430-a-timeout-is-not-a-red-test-and-a-kill-is-not-a-timeout/report-01.md`
  — D6(c), D6(d).
- `doc/plans/truthful-signals/440-the-merge-currency-treadmill/report-01.md` — D6(e).
- `doc/plans/truthful-signals/590-cloud-plan-lane-contract-and-run-report-accuracy/` — this plan's own
  directory: `plan.md` and `report-NN.md`.

**Read-only** (the evidence base, never edited by this plan): the twelve
`doc/plans/truthful-signals/{source-plan}/gaps.md` and `verification.md` files. Re-derive that set
from the ids in § Deliverables — it is wider than the ten reports § Expected surface lists as edited,
because two source plans (030 and 230) contribute a gap without owning a report this plan corrects.

**No `*.py` file is expected in the diff.** If one appears, that is scope drift and is reported as
such (§ Verification).

## Claim labels

| Claim | Label | Confirm/refute artifact |
|---|---|---|
| 450/G1 (`high`) reproduces at HEAD | OBSERVED | `450-…/report-01.md` — `:34` "not probed (no PR opened…)", `:36` "not probed (no arming this run)", `:185` "not exercised … (no PR)", against `:3`/`:162` in the same file |
| Condition 1 instructs a derivation the same section declares unobtainable (030/G2) | OBSERVED | `.claude/skills/cloud-plan-lane/SKILL.md` § Step 8 condition 1 — the `BLOCKED` paragraph, against the ruleset-API sentence ~40 lines above and the § Cloud session affordances "Ruleset-config API" row |
| The § Report template has no merge-gate section and the `\| 8 Merge gate \|` row demands no disclosure artifact (030/G4) | OBSERVED | `SKILL.md` § Report required-content block (sections: Skills loaded, Deliverables, Build gate, Findings, Reviewer participation, Cost, Contract check, What have we learned, Residue) and the Step-9 contract-check table |
| The contract names neither `CHECK_ERA` nor `era_stamp_fill` (220/G5) — an asserted **absence** | OBSERVED | A content search of `.claude/skills/cloud-plan-lane/SKILL.md` for `CHECK_ERA\|era_stamp_fill` returns nothing. ⛔ Re-derive before writing D4(b): an absence is the higher-risk claim, and a run that skips this check may add text that already exists |
| The authoring skill names no population-derivation mechanism (040/G5) — an asserted **absence** | OBSERVED | A content search of `.claude/skills/author-cloud-plan/SKILL.md` for `population-derived\|_dispatch_roster\|implements:` returns nothing. Re-derive before writing D7 |
| Three affordance rows state as fact what the writing run marked reported-only (450/G3) | OBSERVED | `SKILL.md` § Cloud session affordances rows "GitHub access", "Ruleset-config API", "Auto-merge arming", against the D0 table in `450-…/report-01.md:33-36` |
| The "Ruleset-config API" row names a merge-state field its own § Step 8 note says does not exist (450/G4) | OBSERVED | That row's "Read required-ness from `mergeStateStatus`", against § Step 8 condition 1's MCP field note (`mergeable_state`, lowercase, no `mergeStateStatus` key) |
| The twelve report-accuracy defects assigned to D5 and D6 reproduce at HEAD | OBSERVED | Located by content search in each named `report-01.md`: `_pending_` in 060; two `## Cost` headings in 160; four `(Recorded at close.)` sections in 370; "no local build was run" vs the § Run continuation build in 110; the superseded branch/PR in 110's contract-check rows 2 and 7; "quantified" in 220's D1 bullet; "Direction 2 … none" and the test count in 260; the two case counts in 430; "three EARLIEST" in 440 (**two** sites); the boundary-harness figure in 040 |
| The corrected **value** of each count in D6 | HYPOTHESIS | Each is re-derived at the moment of the edit by the derivation D6 names (test collection at the documented commit; step frontmatter for the order set). The figures in the gap documents are leads and are **not** to be transcribed |
| The `sourcery-ai` review body and the full commit set of plan 450's PR (D1(d), D1(e)) | HYPOTHESIS | The live PR surfaces (`get_reviews`, the commit list). Both are quoted in the git-tracked `450-…/gaps.md` § G2 / § G5; per D0(d), if the live read is unavailable the correction cites the gap document as its substrate and says so |
| Plan 060's PR number (D5(d)) | OBSERVED | `git log --oneline -- doc/plans/truthful-signals/060-…/` names the landing commit and its PR number; re-derive at the moment of the edit |
| The D1 delta figure of plan 220 is not derivable in this environment (D5(a)) | OBSERVED | `.gitignore` excludes `.plan/*`, and `CLAUDE.md` § Standalone Plan Lane states a cloud clone carries none of it — so `.plan/work/change-ledger.jsonl` and `.plan/local/archived-plans/` cannot exist here. ⛔ Machine-local: **do not go looking for them** |
| Expected surface: two skill files, ten sibling reports, this plan's directory, no `*.py` | HYPOTHESIS | The run's own `git diff --name-only origin/main...HEAD`, checked at Step 9 against the § Expected surface list |
| No gap in this set is `vacuous-test` or `vacuous-guard` | OBSERVED | The **Kind** line of each of the 24 entries across the twelve source `gaps.md` files — re-derive both figures at the moment of the check: every one is `stale-statement`, `doc-drift`, `omission` or `incomplete-sweep`. No deliverable here therefore carries a red-first obligation; if the gate at D0(a) finds otherwise for any id, that id's deliverable acquires one and the report says so |

## Verification

**Cold reads — the deliverables whose whole value is what a later reader does with the text.** D2, D3,
D4 and D7 are contract prose; "implemented as specified" cannot verify them, because the text can be
present, well-formed and still read the wrong way. Dispatch the § Step 6 verification sub-agent to
take each **cold** — given only the changed section, not this plan — and to **report which reading it
took**. A wrong reading means the wording failed, however complete it looks.

| Text | Question put cold | Reading that passes |
|---|---|---|
| D2, § Cloud session affordances | Does a cloud session have the `gh` CLI? Which field carries merge state on the MCP path? When this table and a step section disagree, which wins? Must the review-summary surface be read before the merge gate? | Observed absent in every session so far — check rather than assume; `mergeable_state`; the linked section; **yes** |
| D3, condition 1 | `mergeable_state` is `BLOCKED` and you cannot enumerate the required set. Write the operator disclosure. | Names **no** blocker; states the merge state, that the required set is not enumerable on this path, and the non-green contexts on the head. Fails if it names a blocker, invents a required set, or falls back to the loudest pending status |
| D4(a), the merge-gate receipt | You armed auto-merge with one non-required context pending and your report says nothing about it. Is Step 9 row 8 done? | **Not done** |
| D4(c), the report receipt | Your report states "44 cases" from a note you took mid-run. What must happen before the report is committed? | Re-derive it and state the derivation beside it — not "leave it, it was right when written" |
| D4(b), `CHECK_ERA` | You changed an audit check's semantics in this lane. What do you owe, and when? | Bump to the sentinel while working; resolve it with the named script after create-PR; commit and push **before** the merge gate |
| D7, the authoring note | You are authoring a plan that calls for a population-derived detector. Where does the population come from, and may you copy `test/_shared/_dispatch_roster.py`? | The ext-point `implements:` frontmatter; **no** — that module is a Markdown-section parser, not a population source |

**Per-file report checks** (D1, D5, D6), run once per touched `report-01.md` after its edits:

- no `_pending_` and no `(Recorded at close.)` placeholder remains;
- no template heading (`## Cost`, `## Contract check`, `## What have we learned`, `## Residue`)
  occurs more than once;
- no statement asserting an absence — no PR, no arming, no build, no GitHub operation, "none", a
  `silent` reviewer — is contradicted by another statement in the same file;
- every count carries the derivation it was re-derived from, and for the three two-site figures in
  D6(b), D6(d) and D6(e) both sites agree.

**Scope checks at Step 9:**

- `git diff --name-only origin/main...HEAD` matches § Expected surface. Any `*.py` file, any file
  under `doc/plans/` outside the ten named reports and this plan's own directory, or any bundle file
  under `marketplace/` is **scope drift** and is reported as such, not narrated as an extra.
- The build gate's git-derived verdict is expected to be "no Python changes, build skipped". If it is
  not, the diff has drifted and that is the finding.
- Row `| 8 Bridge |` is reported as a **declared excursion** naming the ten sibling directories, with
  an explicit statement that no status or bookkeeping write was made (§ Declared Bridge excursion).
- The Bridge-row amendment (D4(d)) appears in § What have we learned as a **proposal**, and does not
  appear in the diff.

**Coverage check:** the report lists all 24 assigned gap ids with, for each, the deliverable that
closed it, "already closed by `{sha}`", or the out-of-scope reason — so a reader can see that none was
silently dropped.

## Notes

**Why the report corrections are in scope at all — the judgement call, stated rather than assumed.**
Fifteen of these twenty-four gaps are false statements inside run reports that have already landed,
and `CLAUDE.md` § Standalone Plan Lane grants a run report an explicit exemption as "a dated record of
one execution rather than documentation of the current state". The tempting reading is that a record
should be left alone and only the forward-looking contract fixed. This plan rejects that reading, for
four reasons, and readers should be able to check the argument rather than take it:

1. **The exemption is about currency, not accuracy.** It exempts a report from the "No timestamps" and
   "Current state only" standards — from the obligation to be *kept current*. Nothing in it licenses a
   statement that was false about the run at the moment it was written. "This run did not open a PR",
   in a file that opens one, is not a dated fact; it is a wrong one.
2. **These reports have not been collected yet, and collection copies them forward and then deletes
   them.** `doc/plans/cloud-bridge.md` § Path 3 has the orchestrator read the report's findings
   (step 3), carry its per-deliverable outcome, its **reviewer-participation verdicts** and its cost
   line into a durable landing record (step 5), and then **delete the report** (step 6). Every false
   claim still standing is therefore scheduled to be copied into the record that outlives it, with its
   only corrigible source removed immediately afterwards. Step 5 already carries a ⛔ against
   downgrading an `unreadable` verdict to `silent` for precisely this reason — and 450/G2 is a
   `silent` verdict that should read `rate-limited`, the same conversion hazard one verdict over.
3. **They are a live evidence corpus.** `450-…/gaps.md` records that plan 450 was itself compiled from
   four sibling run reports. A false "not probed" does not merely sit there — it suppresses evidence a
   later plan in this epic mines, in the epic named for truthful signals.
4. **The corrections are cheap and checkable.** Each is one sentence with a substrate in the clone or
   in git, and D0(d) forces the run to say which.

**And the durable half is what makes the sweep worth doing.** A sweep with no recurrence control is a
sweep you do again: the contract *already* carries the rule that would have caught five of these
("a count derived by looking is a sample… re-derive it at the moment of the claim"), and four separate
plans violated it anyway. The missing part is not another rule but a **receipt** — which is the same
diagnosis 030/G4 makes about the merge-gate disclosure ("condition 1's disclosure got the rule and not
the receipt"), one layer out. D4 is that receipt, and it is the deliverable this plan would keep if it
could keep only one. The instance sweep (D5, D6) is worth its cost *because* D4 stops the class
recurring; without D4 it would be maintenance, and this plan would have been authored around D1–D4
alone.

**What the corrections do not do.** They do not rewrite the history of any run. Where a cell was
accurate when written and only its reason is false, D1(a) corrects the reason and keeps the verdict.
Where a section was written before the run finished, D5(b) and D5(c) name what the run later did
rather than silently overwriting what it first said. The record grows; it is not replaced.

**`.plan/` is machine-local and invisible here.** The orchestrator ledger, the plan specs, the
archived-plan corpus and the change ledger live under `.plan/`, which `.gitignore` excludes and a
cloud clone does not carry. Two deliverables touch this: D5(a) records that plan 220's delta figure is
**not derivable in this environment** rather than trying to derive it, and 230/G3 is out of scope for
the same reason. **Do not go looking for any `.plan/` path named in this plan or in any gap document.**

**No gap in this set is a vacuous-test or vacuous-guard.** All twenty-four are `stale-statement`,
`doc-drift`, `omission` or `incomplete-sweep`, so no deliverable here carries a seen-RED-first
obligation. This is stated because it is unusual for this epic, and because a reader who assumes
otherwise will look for a test obligation that is deliberately absent. If D0(a) finds a **Kind** line
that contradicts this, that deliverable acquires the red-first obligation and the report says so.

**Sequencing and concurrency.** D2, D3 and D4 all edit `.claude/skills/cloud-plan-lane/SKILL.md`, and
D2(d) and D3 touch adjacent text (the affordance row and the condition-1 pointer into it) — 030/G3 is
closed only when **both** land, which is why it is named in both deliverables. This plan therefore
cannot run concurrently with any other plan editing that file. It has no dependency on the twelve source
plans, all of which have landed.

**Prior art.** Plans 030 (PR #1137) and 450 (PR #1147) in this epic landed deliverables in the same
contract file; plan
450's run made the same sibling-report excursion this plan declares in advance, and recorded it as an
operator-directed exception. The gap documents this plan works from are git-tracked at
`doc/plans/truthful-signals/{source-plan}/gaps.md`, each with a `verification.md` beside it whose
§ Adversarial review records what was upheld, refuted or re-severitied — that section outranks the gap
body where they disagree.
