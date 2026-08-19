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

# The lane's contract gaps become a decidable register, and the landed run-record's false claims become a re-derived correction set

**Epic:** code-intelligence-substrate (ledger-backed)
**Branch prefix:** chore — maintenance and documentation; this plan changes no production code and no test

## Problem

An audit of this epic's landed cloud plans found thirty-two defects that all belong to one surface:
the standalone plan lane itself. They split two ways.

**One — the contract has holes that every future run will fall into.** Its Step 1 skill-loading table
maps surfaces to skills and has **no row for an SVG diagram**, so a run that edits
`doc/resources/diagrams/*.svg` never learns that `pm-documents:ref-svg-diagrams` imposes a mandatory
rasterise-and-read-back gate; one run did exactly that, followed the table faithfully, and shipped an
unrasterised diagram. Neither the contract nor `doc/plans/cloud-bridge.md` says what a run **blocked on
a missing environment prerequisite** must produce, so two plans in this epic hit the same wall and each
inferred from first principles that it should still establish its directory and land a report — a run
that inferred otherwise would leave the flat plan file untouched and the determination invisible, and
the plan would be re-dispatched into the identical wall. A two-part proposal about the **post-PR push
cost** (a one-line report edit consumed a bot's review window) was presented by a run, never taken and
never declined, and the contract has been renumbered since, so it can no longer be applied verbatim.

**Two — the landed record says things that are not true, always by the same mechanism.** A figure is
measured mid-run and restated at finalization without being re-derived, so build-gate footprints
understate the surface the gate covered, per-file test counts are stale by the time they merge, a
PR description states a total the landed tree contradicts, and a merge-gate row names a head that was
not the merged head. A commit is cited by its branch SHA, the PR squash-merges, the branch is deleted,
and every citation in the report becomes unresolvable in a fresh clone. And in the sharpest case, a
resumed run's recovery step lost two of eleven commits while its report asserted that nine were pushed
and **every commit's tree is preserved** — the loss was documentation-only, so no code or test was lost,
but the destruction is asserted not to have happened, and the two destroyed commits were themselves
corrections to earlier false claims.

*Mechanism.* The contract already requires re-derivation, but only for three claim classes: **diff**
claims are re-derived by the § Step 6 sweeps, and **tree** and **history** claims by § Step 9. The
figures above are none of those three — they are *measurements*, and nothing re-derives them at the
moment of the claim. Likewise, § Step 9 requires re-deriving history claims *after a rebase* but never
requires proving that the commit **population** survived one, which is exactly what the eleven-to-nine
loss slipped through.

## Goal

The operator holds one register that states, per contract gap, what happened, the exact edit proposed
against the contract's current text, and the decision being asked for — and the epic holds one
re-derived correction set naming every false claim in its landed run records, with the command and the
ref each correction was measured at. Neither the governing contract nor any other plan's directory is
modified by the run that produces them.

> ⛔ **THE ONE RULE THIS PLAN EXISTS TO RESPECT — read it before Step 4.**
>
> **This run must not edit `.claude/skills/cloud-plan-lane/SKILL.md`, and must not edit `CLAUDE.md`
> § Standalone Plan Lane, `doc/plans/README.md`, `doc/plans/cloud-bridge.md`, or
> `doc/plans/_template/plan.md`.** Not to "helpfully apply" a proposal, not to fix a line the plan
> itself calls wrong, not even for a one-line addition the evidence obviously supports.
>
> The reason is the contract's own rule at § Step 9 → "What have we learned": *"Never self-approve a
> change to the contract that governs you."* A run that amends its own governing text has approved
> that amendment with nobody's authority but its own, and it has done so at the exact moment it is
> least able to see the consequences. The contract's remedy is fixed: **present it to the operator with
> the evidence, and on approval ship it as a separate `chore/` PR touching only the skill.** This plan
> is authored to produce the first half. The second half is not this run's to perform.
>
> The line, stated so it needs no judgement:
>
> | Surface | This run |
> |---|---|
> | `.claude/skills/cloud-plan-lane/SKILL.md` | **Never edits it.** It is the contract that governs this run. |
> | `CLAUDE.md` § Standalone Plan Lane, `doc/plans/README.md`, `doc/plans/cloud-bridge.md`, `doc/plans/_template/plan.md` | **Never edits them in this plan.** § Step 9's bridge row does permit a *declared-deliverable* edit to a shared lane doc — so the permitted side of this line is real — but every candidate in this plan's gap set is a **behavioural amendment** (it changes what a future run does), and a behavioural amendment to a lane doc is a contract change wherever it is written. **This plan declares no such deliverable, and the permitted side is therefore empty here.** |
> | Another plan's directory under `doc/plans/{epic}/` | **Never edits it.** See D2's preamble and P7 — the corrections are recorded in this plan's own directory instead. |
> | `marketplace/bundles/**`, any `*.py` | **Never edits them.** Out of scope, with reasons below. |
> | This plan's own directory | The only place this run writes. |
>
> The decision test, for anything not in the table: **would a future run behave differently after this
> edit?** If yes, it is a behavioural amendment and it goes into `proposals.md`. If the answer is
> unclear, it goes into `proposals.md` — the tie-break is fixed so that no mid-run judgement is
> required.

## Deliverables

Each deliverable is independently verifiable. Every number below is a **lead**: the tree has moved
since this plan was authored, and a count copied forward is exactly the defect this plan is about.
Re-derive each at the moment you state it, and record the command and the ref you took it at.

1. **D0 — Anchor derivation and target census (gating; this one can halt the plan)** — before any
   other work, derive two things and write both into the run report.
   (a) **The contract's current anchors.** Read `.claude/skills/cloud-plan-lane/SKILL.md` and record,
   for each section a proposal touches, its **current** heading and line range: § Step 1's
   "Conditionally, by what the plan touches" table, § Step 5 (build gate), § Step 7 (PR cycle),
   § Step 8 (merge gate, and the numbering of its conditions), § Step 9 (the contract-check table, the
   three-claim-class block, and "What have we learned"), and § Report. The anchors this plan quotes
   were true when it was authored and the file has been renumbered before — one open proposal is
   unapplicable *because* of a renumbering — so a proposal written against stale anchors is worthless.
   ⛔ **If the skill file cannot be read, HALT**: report the run blocked, naming the file. Do not write
   proposals against a contract you could not open, and do not reconstruct its numbering from this plan.
   (b) **The target census.** For each source plan named in § Gap coverage, record one of three states:
   `present` (the directory exists and the quoted defective text is still there), `already corrected`
   (the directory exists and the text has changed), or `collected` (the directory is gone — a landed
   cloud plan's directory is deleted at collect in a ledger-backed epic, which this one is). A
   `collected` or `already corrected` target is not a failure; it is a recorded disposition.
   *Done when:* the report carries a table of the six re-derived contract anchors, and a census row for
   every source plan in § Gap coverage with one of the three states and the check that produced it.

2. **D1 — `proposals.md`: the operator's decision register** — a new file
   `doc/plans/{epic}/{this-plan}/proposals.md` carrying **seven** proposals, each written so the
   operator can decide without opening anything else. Per proposal: **what happened** (the run and the
   observable consequence — never a speculative improvement), **the exact proposed edit** quoted against
   the anchors D0 re-derived, **the risk the wording must handle**, and **the decision being asked**
   with its options. The file opens with a ⛔ stating that it proposes and does not apply, and that an
   accepted proposal ships as a separate `chore/` PR touching only the skill.
   - **P1 — an SVG-diagram row in the § Step 1 conditional table.** A run edited
     `doc/resources/diagrams/context-isolation.svg`, followed the table, and never saw
     `pm-documents:ref-svg-diagrams` and its mandatory rasterise-and-read-back gate. Proposed row:
     `| SVG diagram (doc/resources/diagrams/*.svg) | pm-documents:ref-svg-diagrams |`. **The wording must
     carry a no-rasteriser branch** — report the coverage gap in the run report, never skip silently —
     because that plan's adversarial review established that no rasteriser was reachable in its runtime
     (`rsvg-convert`, `inkscape`, `convert`, `chromium` absent; `cairosvg` not importable), so the bare
     row would create an obligation a run cannot discharge. Decision: adopt with the branch / adopt
     without it / decline.
   - **P2 — what a run blocked on a missing environment prerequisite must produce.** Two plans in this
     epic (`020`, `080`) blocked on a corpus living under the git-ignored `.plan/` tree, and each
     inferred the same behaviour unaided. The nearest existing rule — that the report states the PR
     number and the per-deliverable outcome *including a run that ended blocked or partial, and why* —
     sits in § Step 8 (merge gate), which a blocked run never reaches. Proposed: one line in § Report
     (and/or `cloud-bridge.md` § Path 2 — Sync) stating that such a run still performs Step 3, still
     lands a report with `Outcome: blocked`, and names the prerequisite; optionally relocating the
     blocked-or-partial sentence into § Report where a blocked run will read it. Decision: adopt /
     decline — **and if declined, the reason is recorded**, so a later reader can tell "declined" from
     "never looked at", which is the state this proposal has been in.
   - **P3 — post-PR push batching, and the § Step 8 conditions sequencing note.** A run consumed
     CodeRabbit's review window with a one-line report edit that moved the head mid-review. The
     underlying *fact* has since landed in the contract; neither proposed edit did, and the proposal is
     neither shipped nor closed. Proposed: (i) a § Step 7 rule to batch known-pending post-PR edits into
     one push; (ii) a note that the report-push condition and the green-on-head condition are sequenced
     rather than simultaneous — **stated against the condition numbering D0 re-derived**, because the
     original proposal's "condition 3" has since been renumbered. Risk the wording must handle: a
     batching rule must not read as licence to withhold a commit — durability outranks it; the original
     proposal's own phrasing ("the lever is ordering, never withholding a commit") handles it. Decision:
     adopt both / adopt (i) only / decline.
   - **P4 — a fourth re-derivation class, and a durable citation form.** § Step 9 states that there are
     three claim classes and that only the diff class is covered for free; the figures that keep going
     stale are in none of them. Proposed (a): add a **measurement** class — build-gate footprint and
     result, test counts, diff sizes, PR-description totals, and check-run verdicts together with the
     head they ran on — re-derived at the final head at the moment the report is written, each stating
     the ref it was taken at; with the matching line in the § Report template's `## Build gate`.
     Proposed (b): a report cites `PR #NNNN` plus the merge commit on `main`, **or** a SHA together with
     the ref it lives on, and never a bare branch SHA — because a squash merge deletes the branch and
     every citation rots at once. Evidence is the correction set D2–D4 produces; state the instance
     count as a lead re-derived from § Gap coverage, never as a trusted number. Decision: adopt both /
     adopt (b) only / decline.
   - **P5 — prove the commit population survived a rebase or a resume.** A run's recovery step carried
     nine of eleven commits onto the branch that became the PR, and its report stated that nine were
     pushed and every commit's tree was preserved. The mechanism (a dropping rebase, or a fetch taken
     before the prior run's last push) is not recoverable from the tree; the **effect** is established.
     Both lost commits were documentation-only, so no production code and no test was lost — the damage
     is confined to the record, and the record is what a later reader relies on instead of re-deriving.
     § Step 9 already requires re-deriving history *claims* after a rebase but never requires proving
     the *population* survived one. Proposed: record `git rev-list --count {base}..{source-ref}` before
     and after, and enumerate any difference commit-by-commit before proceeding. Decision: adopt as a
     gate / adopt as a report-only disclosure / decline.
   - **P6 — how a landed run report is corrected.** Three separate gap entries reach for three different
     answers ("replace the paragraph", "prefer an inline correction note over a silent rewrite", "a
     marked addendum rather than an edit to a dated run record"), so the convention is genuinely
     unsettled. `CLAUDE.md` § Standalone Plan Lane grants a run report an explicit exemption from the
     "No timestamps" and "Current state only" standards *because it is a dated record of one execution
     rather than documentation of current state* — which argues that a record is corrected **additively**
     and never rewritten. Proposed rule: leave the original sentence in place, append an inline marker,
     and add an entry to a `## Corrections` section at the end of the document giving the quoted
     original, the re-derived value, the command, and the ref; a structural remnant carrying no claim (a
     duplicated template stub) is deleted outright with one line recording the deletion; a document that
     is **not** a dated record (`plan.md`, `gaps.md`, `rationale.md`) is edited in place under the normal
     documentation standards. Decision: adopt / adopt a different convention / decline.
   - **P7 — may a run correct another plan's landed directory at all?** § Step 9's contract-check row
     "8 Bridge" requires that no **status or bookkeeping** write land under `doc/plans/` outside the
     run's own directory — "no ledger, no status file, no other plan's directory was touched" — while
     permitting "a **declared-deliverable** edit to a shared lane doc". A *corrective* edit to another
     plan's landed report is neither of those, so the clause neither clearly permits nor clearly forbids
     it. **This plan resolved the ambiguity conservatively** — every correction is recorded in this
     plan's own directory and none is applied in place — which is why D2–D4 produce a document rather
     than edits. Proposed: state in that row whether a corrective, non-status edit to another plan's
     landed record is permitted when declared as a deliverable, and under what convention (P6).
     Decision: permit / forbid / permit only via a follow-up `chore/` PR authored from a correction
     document. ⛔ Note for the operator, and the reason this proposal is worth answering: on "permit",
     the follow-up is mechanical — `record-corrections.md` is already the patch set.
   *Done when:* `proposals.md` exists with all seven proposals, each carrying what happened, the exact
   edit against a D0-re-derived anchor, and an explicit decision with options; and the cold read in
   § Verification returns **DECIDE**, not APPLY.

3. **D2 — `record-corrections.md`, part one: citations that no longer resolve** — a new file
   `doc/plans/{epic}/{this-plan}/record-corrections.md`, opening with a ⛔ stating that it **records**
   corrections and does not apply them (P7), and organised by source plan. Every entry carries: the
   file and location, the **quoted original claim**, the **re-derived truth**, the **command or API call**
   used, and the **ref it was measured at**. Part one covers claims that name a commit or a head that a
   fresh clone cannot resolve or that was not the head in question.
   - `070-…/report-01.md` — the CI head: the report evidences checks on an earlier commit than the one
     the merge gate acted on, and lists a `review / review` check that did not run on it. Re-derive the
     PR's head and its check runs from the GitHub surface, and record both the head and the check list.
   - `130-…/report-01.md` — the contract-check commit count, plus the squash SHA the report never names,
     so a later reader can resolve the run at all (its branch SHAs no longer exist).
   - `140-…/report-01.md` — the deliverable table's Commit column and the findings table cite branch
     SHAs that resolve to nothing; the durable object is the squash-merge commit.
   - `260-…/report-01.md` — the merge-gate row names the predecessor of the merged head. Record the
     merged head, or record why a report cannot name its own finalization commit.
   - `330-…/report-01.md` — the contract-check "8 Merge gate" row names a head one commit before the
     merged head, against which the gating check actually ran.
   ⛔ Re-derive every SHA through `PR #NNNN` → merge commit (`git log --oneline --grep "(#NNNN)"
   origin/main`, or the GitHub surface), never by trusting a SHA quoted in this plan or in the report.
   *Done when:* every entry in part one states a re-derived value with its command and ref, and every
   SHA the entry itself quotes either resolves with `git cat-file -t` in a fresh clone of `main` or is
   written together with the ref it lives on.

4. **D3 — `record-corrections.md`, part two: figures that were true when measured and false when landed**
   — the same file, same entry shape. This is one mechanism at seven sites, and naming it as one is the
   point: each figure was correct at the moment it was taken and was invalidated by the run's own later
   commits, which is why P4 proposes re-derivation at the moment of the claim rather than better
   arithmetic.
   - `140-…/report-01.md` — the build-gate footprint understates the `*.py` files the gate covered, and
     the report's own findings table contradicts it.
   - `190-…/report-01.md` — three: the build-gate `*.py` enumeration (a new production module is absent
     from it), the D5 per-file test counts (pre-fix counts presented as the landed ones; annotate as
     `pre → landed` rather than replacing one wrong number with another), and the residue entry's
     diff-size figure justifying a reviewer's size refusal.
   - `210-…/report-01.md` — the build-gate `*.py` file count, recorded before the last two fix passes
     added more. ⚠ The audit's account of *which* files arrived late is inferred from the report's pass
     ordering, not observed — the branch was deleted at squash-merge — so record the corrected count and
     say the arrival order is not recoverable.
   - `260-…/report-01.md` — the final build gate is recorded against a commit that a later Python-changing
     commit supersedes; either name the later commit and the figures from the gate that ran there, or
     state plainly that the last recorded gate predates the final Python commit.
   - `350-…/report-01.md` § D5 — five per-file test counts and their total. ⚠ **The adversarial review
     overturned the audit here and wins:** the figures were **not miscounted** — every one was exact at
     the run's own tip and was invalidated by tests the same run added afterwards. Correct them by
     naming the modules with each count **and the ref it was measured at**, or drop the total; do not
     record this as an arithmetic error.
   - `350-…/report-02.md` § F-R1 — the "six sites" sweep count for a raw task-number conversion. ⚠ The
     adversarial review found the audit's own replacement count under-enumerated as well; the corrected
     figure separates direct conversions from raw reads handed to a `:03d` format. **Re-run the sweep
     yourself and state the pattern** — do not copy either number from this plan.
   - `135-…/report-01.md` — a quoted bot rate-limit figure that does not match its comment. The comment's
     `updated_at` is later than its `created_at`, so the bot may have rewritten the body after the report
     was drafted. Re-read the comment; if it cannot be read, record **UNVERIFIABLE with the reason**,
     never a value.
   *Done when:* every entry in part two states the re-derived figure with the command and the ref, and
   no entry states a bare number without both.

5. **D4 — `record-corrections.md`, part three: false claims, lost content, and dispositions never
   recorded** — the same file, same entry shape, covering claims that were wrong on the merits and
   obligations that were discharged but never written down. Grouped by owning document.
   - **Plan `350`'s record-integrity set (the sharpest case).** `report-02.md` § "How run 01's work was
     recovered" states that nine commits were pushed and every commit's tree is preserved; the source
     branch carries eleven above the same base, and two never reached the branch under review. Record
     the re-derived counts, name the two commits, and state that the mechanism is not recoverable —
     ⚠ the adversarial review **withdrew the audit's rebase-dropped-them claim**: the timestamps admit a
     fetch taken before the prior run's last push just as well, and only the *effect* is established.
     ⛔ Bound to carry with it: both lost commits are documentation-only, so **no production code and no
     test was lost**. The two commits' content is what `report-01.md` is missing — a corrected
     deliverable-commit enumeration naming five commits including a round-3 population-regression fix
     (the line the run had already fixed once, having been wrong twice), and a recorded final build gate
     where the document now carries an unfulfilled promise to record one. `actual-state.md` § 7 then
     asserts that the run recorded **no** final gate, which is a statement about the run's conduct
     produced by the recovery step. Recover the two commits' text from the surviving source branch and
     quote it into the correction entries. Also record the re-anchoring of every unresolvable SHA quoted
     across the three documents, and the deviation the plan's § Verification never learned about: a
     clause requiring each fixture to carry the pre-fix text verbatim was deliberately not satisfied as
     written, because nothing shipped is a content detector — all three closures are set computations —
     and the substituted mutation campaign is strictly stronger. That disposition lives only in the run
     report, so a later reader of `plan.md` sees an unqualified requirement.
     ⛔ **If the source branch no longer exists**, the two commits' text is unrecoverable: record that
     outcome explicitly, naming what was lost and why, rather than reconstructing it.
   - **Claims that were wrong on the merits.** `010-…/report-01.md` records a `/sync-plugin-cache` as
     owed at two lines; `CLAUDE.md` § Standalone Plan Lane now states that the sync is inert in this
     lane and that a lane plan editing `marketplace/bundles/` "neither performs a sync nor records one
     as owed". `130-…/report-01.md` calls a path "per-call (uncached)" where half of it is memoised for
     the process lifetime (the shipped skill's own phrasing, "never cached across dispatches", is the
     accurate one), and records a blanket "all five deliverables verified as implemented-as-specified"
     that two deliverables do not support. `135-…/report-01.md` asserts every commit carries the
     `Co-Authored-By` trailer where the plan-authoring commit, made before the run began, does not —
     correct it by stating the population the claim covers. `140-…/report-01.md`'s D4 row claims a
     negative-control pair at two levels; this run supplied one level, the other shipped earlier.
     `160-…/report-01.md` records a per-profile empty as producing "zero signal" where an allocation-time
     WARNING and a Q-Gate finding already existed (the confirmed defect was distinguishability, not
     reporting), and rejects a finding as "nonsensical input" where an ordinary enrichment path produces
     the state.
   - **Dispositions never recorded.** `280-…/report-01.md` § Deliverables carries no heading for two of
     its deliverables; they went to a successor plan, which is correct — not saying so is the silent
     half. `330-…/report-01.md` never dispositions its plan's ⛔⛔ sequencing warning, a correctness
     condition on everything the plan shipped; substantively it appears covered by a sibling plan that
     has landed, so record the disposition **with its evidence**, and if the evidence no longer holds,
     record that instead.
   - **Two structural items.** `160-…/report-01.md` ends with four duplicated template headings whose
     bodies read `_pending_`, so a reader scanning to the end finds the run's cost, contract check and
     residue claiming to be unfinished — this is a remnant carrying no claim, so the correction entry
     records a **deletion**, not an additive note. And `240-…/proposal-protocol-surface.md` cites a
     sibling plan's `rationale.md` by relative link; that file is removed when its plan is collected, so
     the link is a scheduled breakage. ⚠ The audit's framing that the citing plan "is queued, not yet
     run" is **false and withdrawn** — it landed. Record the fix as **inlining the two-sentence argument
     at the citation site**, so it depends on nothing else; promoting that argument to an ADR is another
     plan's work and this correction must not wait on it.
   *Done when:* every entry in part three names its document and location, quotes the original claim,
   states the corrected claim with the check that established it, and — for the two `350` entries that
   depend on the source branch — states either the recovered text or an explicit unrecoverable outcome.

## Out of scope

- **Editing `.claude/skills/cloud-plan-lane/SKILL.md`.** Its own § Step 9 forbids a run from
  self-approving a change to the contract that governs it, and fixes the remedy: present the evidence to
  the operator, and on approval ship a separate `chore/` PR touching only the skill. D1 produces the
  first half; performing the second half inside this run is the exact prohibited act.
- **Editing `CLAUDE.md` § Standalone Plan Lane, `doc/plans/README.md`, `doc/plans/cloud-bridge.md`, or
  `doc/plans/_template/plan.md`.** A behavioural amendment is a contract change wherever it is written,
  and every lane-doc candidate in this gap set is behavioural — it changes what a future run does. The
  contract does permit a *declared-deliverable* edit to a shared lane doc, so this boundary is a choice
  about this plan's gap set rather than a blanket prohibition; the choice is stated in § Goal's table so
  a run cannot mistake one for the other.
- **Applying any correction in place, in another plan's directory.** § Step 9's bridge row requires that
  no write land under `doc/plans/` outside this run's own directory and names "no other plan's directory
  was touched"; whether a *corrective* edit is inside or outside that prohibition is genuinely unclear,
  and a run has no operator to ask. The conservative reading is the only one that cannot be wrong, and
  P7 asks the operator to settle it. Nothing is lost by waiting: the correction document is the patch
  set a follow-up PR would apply.
- **Adding the set-detector/content-detector sentence to
  `marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/q-gate-validation.md`** (the second
  half of one `350` gap). That is a shipped bundle standard, not a lane artifact; this plan is
  deliberately confined to `doc/plans/**` so its diff-containment gate can be mechanical. The
  in-scope half — recording the deviation where the plan itself is read — is delivered in D4, and the
  bundle half is **routed as a finding in the run report** so it is handed on rather than dropped.
- **Promoting a plan's `rationale.md` argument into an ADR or a concepts page.** It belongs to the
  documentation-surface work, not here; D4's inlining fix is chosen precisely so this plan depends on
  neither its existence nor its timing.
- **Fixing the underlying code defects that the mis-stated report claims describe** (the unguarded
  numeric conversions, the glob-shaped write-set, the silent non-dict profile skip, and their kin).
  Those are separate gaps in other plans of this series with their own tests and risk profiles; a
  record correction and a code fix have different review audiences and must not share a diff.
- **Re-running any build or test suite to produce a figure.** Every correction here is derivable from
  git and the GitHub API. Timing and throughput figures measured in a shared tree are unreliable, and
  no gap in this set rests on one — so re-running a suite would add a new unreliable number rather than
  settle an old one.
- **Correcting reports in plan directories outside § Gap coverage's fourteen source plans.** Coverage is
  defined by the gap set; sibling plans in this series own the rest, and an unbounded sweep would
  collide with them.

## Expected surface

Everything this run writes is inside its own plan directory. That is not incidental — it is what makes
the § Verification containment gate mechanical.

- `doc/plans/code-intelligence-substrate/{this-plan}/plan.md` — moved here from the flat file by Step 3.
- `doc/plans/code-intelligence-substrate/{this-plan}/proposals.md` — new; D1.
- `doc/plans/code-intelligence-substrate/{this-plan}/record-corrections.md` — new; D2–D4.
- `doc/plans/code-intelligence-substrate/{this-plan}/report-NN.md` — the run report, per the contract.

**Read but never written** (the census in D0 and the re-derivations in D2–D4 read them):
`.claude/skills/cloud-plan-lane/SKILL.md`, `doc/plans/cloud-bridge.md`, `CLAUDE.md`, and the fourteen
source plan directories named in § Gap coverage — each of which may already be gone.

**Not touched, expected to appear nowhere in the diff:** `.claude/skills/**`, `marketplace/bundles/**`,
`doc/plans/README.md`, `doc/plans/_template/**`, any other plan's directory, and any `*.py`.

## Claim labels

| Claim | Label | Confirm/refute artifact |
|---|---|---|
| The lane's § Step 1 conditional table maps surfaces to skills in seven rows and has **no** row for an SVG diagram | OBSERVED | `.claude/skills/cloud-plan-lane/SKILL.md`, the table under "Conditionally, by what the plan touches" — read directly; the row count and line range are **leads**, re-derive in D0 |
| Neither the lane skill nor `doc/plans/cloud-bridge.md` contains the string `prerequisite` — an asserted **absence**, and therefore the highest-risk claim here | OBSERVED | `grep -n "prerequisite" .claude/skills/cloud-plan-lane/SKILL.md doc/plans/cloud-bridge.md` returned no hits when this plan was authored; **re-run it and report the result either way** — a hit refutes P2's premise and P2 is then withdrawn rather than argued |
| § Step 9 names exactly three claim classes (diff, tree, history) and states that only the diff class is covered for free — so measurement figures belong to none of them | OBSERVED | § Step 9, the block ending "So three claim classes, and only one is covered for free" |
| § Step 9's contract-check row "8 Bridge" forbids a status/bookkeeping write outside the run's own directory and permits a declared-deliverable edit to a shared lane doc | OBSERVED | § Step 9's contract-check table, row "8 Bridge" — the text this plan's § Goal table and P7 both rest on |
| § Step 9 forbids self-approving a change to the governing contract and fixes the remedy (present to operator; ship on approval as a separate `chore/` PR touching only the skill) | OBSERVED | § Step 9 → "What have we learned" |
| This epic is ledger-backed, so a landed cloud plan's directory is **deleted** at collect | OBSERVED | `doc/plans/cloud-bridge.md` § Status vocabulary and § Path 3 step 6; `doc/plans/_template/plan.md` names the ledger-backed epics |
| A branch SHA quoted in a landed report becomes unresolvable in a fresh clone once the PR squash-merges and the branch is deleted | OBSERVED | the audits re-ran `git cat-file -t` over the quoted SHAs in three source plans and every one reported missing; the **per-plan counts are leads**, re-derive them |
| Each of the fourteen source plan directories still exists with the documents this plan names | HYPOTHESIS | a listing of `doc/plans/code-intelligence-substrate/`; **D0 settles it per target** and a `collected` state is a recorded outcome, not a failure |
| Each quoted defective sentence is still present at its quoted location | HYPOTHESIS | a literal string search per target in D0, recording `present` / `already corrected` / `collected`; ⛔ never edit by pattern-guess when the quoted text is absent |
| The source branch carrying plan `350`'s two lost commits still exists on `origin` | HYPOTHESIS | `git ls-remote origin 'refs/heads/claude/derived-set-closure-integrity-*'`, then `git cat-file -t` on the two commits; if absent, D4 records the content as unrecoverable |
| The bot comment quoted in plan `135`'s report currently reads a different figure than the report quotes | HYPOTHESIS — a single unreplicated read of a body whose `updated_at` postdates its `created_at`, i.e. a body observed to change | re-read the comment via the GitHub surface; if it cannot be read, record UNVERIFIABLE with the reason, never a value |
| No gap in this plan's set rests on a duration or a throughput measurement | OBSERVED | the thirty-two gap entries in § Gap coverage; this is why the plan re-derives from git and the GitHub API only and re-runs no suite |
| Plan `350`'s per-file test figures were exact when taken and were invalidated by the same run's later commits — they were **not** miscounted | OBSERVED (adversarial review, which supersedes the audit's account) | that plan's `verification.md` § Adversarial review, the A4-counts row; re-derivable at the source branch |

An asserted **absence** is verified exactly as an asserted presence, and is the higher-risk half. The
second row above is this plan's one asserted absence, and P2 stands or falls with it.

## Verification

Beyond each deliverable's *done when*:

- **Diff containment (mechanical, and the single most important check).** Re-derive
  `git diff --name-only origin/main...HEAD`. **Every path must be under this plan's own directory.**
  Specifically: zero paths under `.claude/skills/`, zero under `marketplace/bundles/`, zero under any
  other plan's directory, no `CLAUDE.md`, no `doc/plans/README.md`, no `doc/plans/cloud-bridge.md`, no
  `doc/plans/_template/`, and no `*.py`. A path outside the plan directory is a violation of this plan's
  central rule: **revert that file, record it as a finding in the run report, and say what led to it** —
  do not argue it was harmless.
- **Build gate.** Re-derive `git diff --name-only origin/main...HEAD -- '*.py'`; it is expected empty and
  the build is then skipped. Record the verdict rather than asserting the expectation — this plan's whole
  subject is figures asserted instead of re-derived.
- **Cold read A — does the register propose or apply?** Dispatch a sub-agent that has **not** read this
  plan, give it `proposals.md` **alone**, and ask two questions: *(1) For each proposal, is the reader
  being asked to APPLY the change or to DECIDE whether it should be applied? (2) If a proposal is
  accepted, who applies it, and in what change?* Required answers: **DECIDE**, and **the operator, via a
  separate `chore/` PR touching only the skill**. Any APPLY reading is a wording failure however complete
  the document looks — fix the wording and re-run the cold read. Record the reading the sub-agent
  actually returned, not a paraphrase.
- **Cold read B — does the correction set read as an instruction to edit?** Give a fresh sub-agent
  `record-corrections.md` alone and ask: *does this document instruct me to edit the reports it names?*
  Required answer: **no** — it records corrections; applying them is a separate, operator-approved change.
- **Citation resolvability.** Extract every hex commit token from `proposals.md` and
  `record-corrections.md` and check each with `git cat-file -t` in a clone of `main`. Every token must
  resolve, **or** be written together with the ref it lives on. This is the rule P4(b) proposes, applied
  to this plan's own output first.
- **Re-derivation discipline.** Every number in both new documents states the command and the ref it was
  taken at. A number carrying neither is a defect **whether or not it is correct** — that is the property
  under test.
- **Gap coverage.** Every gap id in § Gap coverage appears in one of the two documents with an explicit
  disposition: `corrected`, `already corrected upstream`, `target collected`, or `unverifiable` with the
  reason. A gap with no disposition is reported as **not done**; a silently dropped gap is the failure
  this section exists to prevent.
- **Report and hand-off.** The run report names the two deliverable documents and reproduces the seven
  proposal titles with their one-line asks, so the orchestrator's collect step — which reads the
  report's findings and writes the landing record before deleting the directory — carries the register
  forward. ⚠ Distinguish the two kinds of proposal in the report: § Step 9's "what have we learned" asks
  what **this run's own execution** revealed about the contract, and is answered on its own terms
  (including "none, because …"); `proposals.md` is an audit-derived deliverable and is pointed at, not
  substituted for that answer.

## Notes

**Why this plan records rather than fixes, in one sentence you can hold onto mid-run:** the contract
forbids a run from approving a change to the contract that governs it, and the bridge rule makes it
unclear whether a run may write into another plan's directory at all — so the two things this plan could
"just do" are precisely the two things it must instead hand to the operator, and it hands them over in a
form that makes acting on them mechanical.

**The audit and its adversarial review.** Every gap here was produced by a ground-truth audit and then
adversarially re-reviewed. **Where the two disagree, the review wins** — it was the later, evidence-bearing
pass. Three places where that changes what this run does are called out in the deliverables: the `350`
test figures were true-then-invalidated rather than miscounted; the `350` sweep count was under-enumerated
by the audit's own correction and must be re-run rather than copied; and the commit-loss mechanism was
asserted by the audit and **withdrawn** by the review — only the effect is established, and both lost
commits were documentation-only.

**Counts.** Every number in this plan is a lead. The instance counts in P4, the per-plan SHA counts, the
site counts in D3 — all were true when this plan was authored and none is to be restated without
re-derivation. This is the plan's own subject, and a run that copies a number forward has reproduced the
defect inside the fix.

**Sequencing against sibling plans.** Other plans in this `5xx` series correct stale figures in landed
run reports too, and at least one of them names a report this plan also covers. Because this plan applies
**no** in-place edits, it shares no file with them and can run at any time — the containment gate in
§ Verification is what guarantees that. Two consequences to record rather than act on: if a sibling plan
*has* applied an in-place correction, D0's census will find the text `already corrected`, which is a
normal disposition; and P7 asks the operator to settle, for all of them at once, whether such in-place
edits were permitted in the first place.

**`.plan/` is invisible here — do not go looking.** The orchestrator ledger, the plan specs, the landing
records and the generated executor all live under the git-ignored `.plan/` tree, which this clone does not
have. Nothing in this plan requires them. For the same reason `/sync-plugin-cache` is inert in this lane
and **this run neither performs a sync nor records one as owed** — which is itself one of the corrections
D4 records against an earlier report.

**The gap files are corroboration, not required reading.** Each source plan's `gaps.md` and
`verification.md` carry the full entry behind every item here, and this plan restates each defect's
essential content — the document, the false claim, and the observable fix — so it stands alone. Those
directories are deleted at collect, so treat a missing one as expected and record it, never as a blocker.

## Gap coverage

Thirty-two gaps, fourteen source plans. Cite as `{source-plan}/gaps.md#{gap-id}`; the gap files are
git-tracked on `main` until their plan is collected.

| Deliverable | Source plan | Gaps discharged |
|---|---|---|
| **D1** (P1) | `090-envelope-length-and-the-isolation-currency` | G5 *(medium)* |
| **D1** (P2) | `080-exploration-split-measured-on-one-phase-and-it-is-the-worst-case` | G6 |
| **D1** (P3) | `190-frozen-manifest-diverges-from-live-config` | G14 |
| **D1** (P4–P7) | — | no gap of its own; P4–P7 are the mechanisms behind D2–D4, and their evidence is the correction set |
| **D2** | `070-dispatch-spend-on-dispatches-that-produced-nothing` | G10 |
| **D2** | `130-lsp-shaped-query-api` | G8 *(the commit-count and squash-SHA claim; the other two claims are in D4)* |
| **D2** | `140-project-local-artifact-provider` | G4 |
| **D2** | `260-chat-signal-provenance-filter-under-inclusive` | G5 |
| **D2** | `330-retrospective-report-sections-structurally-dead` | G15 |
| **D3** | `135-remove-lsp-query-facade` | G13 |
| **D3** | `140-project-local-artifact-provider` | G5 |
| **D3** | `190-frozen-manifest-diverges-from-live-config` | G9, G10, G11 |
| **D3** | `210-native-coordinate-resolvers` | G9 |
| **D3** | `260-chat-signal-provenance-filter-under-inclusive` | G4 |
| **D3** | `350-outline-derived-set-closure-integrity` | G5, G6 |
| **D4** | `350-outline-derived-set-closure-integrity` | G1 *(medium)*, G2 *(medium)*, G3 *(medium)*, G4, G18 *(the `plan.md` half; the bundle-standard half is out of scope and routed)*, G19 |
| **D4** | `010-lsp-in-execute-lookup-and-write` | G11 |
| **D4** | `130-lsp-shaped-query-api` | G8 *(the "uncached" claim and the blanket verification claim)* |
| **D4** | `135-remove-lsp-query-facade` | G10, G12 |
| **D4** | `140-project-local-artifact-provider` | G6 |
| **D4** | `160-empty-skill-resolution-indistinguishable-from-minimal` | G10, G11, G12 |
| **D4** | `280-outline-plan-scope-derivation-integrity` | G9 |
| **D4** | `330-retrospective-report-sections-structurally-dead` | G16 |

**Severity roll-up (a lead — re-derive from the rows above):** four medium (`090`/G5, `350`/G1, `350`/G2,
`350`/G3) and twenty-eight low; no high-severity gap is in this set, so none is placed out of scope.
`130`/G8 spans D2 and D4 because it is three claims of two different kinds in one entry, and `350`/G18
spans D4 and § Out of scope because it is one gap with a `doc/plans/` half and a `marketplace/bundles/`
half; both splits are stated so a later reader can check coverage without recounting.
