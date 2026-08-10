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

# The self-review surface over-reports its own coverage three ways

**Epic:** code-intelligence-substrate
**Branch prefix:** fix

## Problem

Pre-submission self-review recently gained delta-scoped rounds — each round examines what changed
rather than re-sweeping the whole surface. That was the right change. Three defects in the
**surfacing** layer make the resulting verdict claim more coverage than it has, and the first two are
made **worse** by the scoping change rather than left unaffected by it.

**A — the detector reads a narrower file set than its own sibling.** The stale-count detector opens
**only** the skill's `SKILL.md`. Its sibling in the *same file* — the one that collects a skill's
contract sources — returns *"`SKILL.md` plus every `standards/*.md` inside the skill directory"*.
⇒ **A stale count living in a `standards/*.md` doc is surfaced by no candidate list, delta round or
full.** The closing full-surface pass is not the backstop a reader assumes: *"full surface"* means
the full **file** surface, not the full **detector** surface.
⭐ Both functions resolve one conceptual input — *the docs carrying this skill's contract* — through
two file sets, with no shared resolver and no test pinning their agreement.

**B — two registry entries are counted as examined by nothing.** Two detector entries carry an
"include in total" flag, so they are summed into the candidate total, into the dispatch gate that
keys off that total, and into the terminal verdict *"self-review clean: N candidates examined, no
check matched"* — while the workflow's check list stops short of them. ⇒ **Volume-read-as-coverage
inside the contract that exists to detect volume-read-as-coverage.**

**C — a scoped round still reports whole-surface claims.** A sibling epic handed over a hard
requirement: every residual or absence claim must publish **what scope was searched** and **how many
files were scanned**, with the reasoning that this *"converts the scoping change from a risk into a
safe one"*. ⛔ Neither token was ever implemented. The requirement arrived **after the plan that made
the scoping change had already started**, and was drained a day after it merged — so the delta
scoping shipped without it.

Their first-party evidence for why it matters: a self-review round asserted a literal appeared in
*"ZERO test and source files"* while three live survivors sat in merged main, because the sweep was
scoped to one directory tree while the **claim** said *"test and source"*. ⇒ ⛔⛔ **This is exactly
how scope restrictions fail — not by missing the delta, but by making a claim wider than the scope
searched.**

## Goal

A self-review verdict's coverage claim is true: every counted candidate class has a check that
examines it, the detector's file set matches its sibling's by construction rather than by
coincidence, and every absence claim states the scope it was derived from.

## Deliverables

1. **D1 — widen the detector's file set to match its sibling's.**
   ⭐ **Fix the asymmetry at the resolver, not by editing one call site** — one conceptual input
   should have one resolver.
   ⛔ **Add a negative-control fixture**: a stale count planted in a `standards/*.md` doc MUST be
   surfaced. A positive-only fixture passes against the current broken resolver and proves nothing.
   *Done when:* both functions resolve the same file set through one path, a test pins their
   agreement, and the planted-count fixture fails before the fix.
2. **D2 — tie registry membership to check coverage by an invariant.**
   A registry entry counted in the total MUST have a consuming check, enforced by a
   **population-derived** contract test over the registry — ⛔ never a hand-copied list.
   ✅ **Direction already decided: ADD THE TWO CONSUMING CHECKS.** The two uncovered entries each
   gain a check, so the total, the dispatch gate and the verdict **stay at their current magnitude
   and become honest**.
   ⛔ **Do not re-derive this as an open question, and do not ship the alternative.** Dropping the
   entries from the total is recorded as the arm **not** taken: it would shrink the number without
   examining anything more, which is the *improve-the-metric-by-examining-less* shape this project
   rejects on principle rather than on balance. Adding the checks is the arm that increases what is
   examined.
   ⚠ **Own this consequence rather than discovering it**: with real checks behind them the headline
   count now corresponds to real examination, so **the dispatch-gate threshold behaviour should be
   unchanged by construction** — verify that rather than assuming it.
   *Done when:* a population-derived test over the registry fails if any counted entry lacks a
   consuming check, and both new checks exist.
3. **D3 — every residual/absence claim publishes its searched scope and its file count.**
   ⭐ **Adopt the positive shape a sibling demonstrated**: one finding *searched the CLAIM rather
   than the STRING* — enumerating the doc-quoted literals and matching each against the live source
   symbol — and closed its class exhaustively. **That is the shape a scoped round's final
   confirmation pass should use.**
   ⛔ **This deliverable binds this plan against itself**: it authors a claim-scoping rule, so its own
   residual claims — in the PR body, in its own self-review rounds, in its run report — must publish
   scope and file count **from the first round**. A rule applied to a sibling's work and not to one's
   own is not yet a rule.
   *Done when:* an absence claim without a scope statement is rejected by the surface, and this run's
   own claims carry theirs.
4. **D4 — a message aimed at a running plan has no reader; make that visible.**
   The requirement in arm C arrived mid-run and was unreadable by the plan it targeted. The drain is
   an act between plans, so **a message aimed at a running plan is architecturally undeliverable and
   nothing says so.**
   ⚠ **Scope carefully.** The minimum honest form is that a message naming a currently-running plan
   is **reported as undeliverable at write time**, not silently queued.
   ⛔ **Do not build a mid-run delivery channel** — that is a much larger design question and is not
   this plan's to answer. ✅ The sibling epic that raised the original requirement has independently
   agreed with scoping it out; this is settled, not open.
   *Done when:* writing a message that names a running plan produces an explicit undeliverable
   report.
5. **D5 — the doc-claim half of self-review SELF-SEEDS; cap on convergence, not on budget.**
   ⭐⭐ **Second sighting of a mechanism, which makes it a pattern rather than an anecdote.** On a
   later run the self-review ran six rounds for roughly a million tokens — the majority of that
   phase's spend — and **closed on a recorded warning deviation rather than a clean pass**: the
   *behavioural* half converged (later rounds found real shipped-code defects, the last found none)
   while the *doc-claim* half did not, **because each correction authored new prose for the next
   round to audit.**
   ⛔ **Same shape as the standing lesson that correction breeds the next instance of the class and
   only deletion converges** — now observed at the level of the round loop rather than the individual
   claim.
   *Done when:* the termination criterion distinguishes *converged* from *out of budget*, and a round
   whose findings are all newly-authored-prose-about-this-plan's-own-edits is reported as
   **self-seeding** rather than counted as an ordinary non-clean round.
   ⛔ **NOT a round-count reduction** — that anti-goal is inherited unchanged.
   ⚠ Coordinate with D3: publishing the searched scope is what makes a self-seeded round
   *identifiable* in the first place.

Five deliverables — at the split guard's edge. ⚠ **Evaluate the split before implementing**; the
natural cut is (D1+D2: what the detector sees) and (D3+D4+D5: what a round CLAIMS about what it saw).

## Out of scope

- **The semantically-wrong-worked-example class** — a normative example that is structurally
  well-formed and semantically wrong. ⛔ **Deliberately excluded**, on the explicit warning of the
  epic that handed this over: it is **not the same shape**, it is invisible to any sweep-scope
  discipline, and silently absorbing it reproduces the exact defect this plan is fixing.
- **Reducing the number of self-review rounds.** Excluded because the loop is not wasteful, it was
  unscoped — and rounds late in a loop have caught structurally unreachable guards on an otherwise
  green suite. The target is the scope of a round, never the willingness to run one.
- **A mid-run message delivery channel.** Excluded under D4 with the originating epic's agreement: a
  plan that changes course mid-run on an orchestrator message is harder to reason about than one
  that does not.
- **Retiring any lesson from the corpus.** Excluded because corpus retirement is gated behind another
  epic's plan — **retire nothing.**

## Expected surface

- `marketplace/bundles/pm-plugin-development/skills/ext-self-review-plan-marshall/scripts/_self_review_detectors.py`
  — D1. **OBSERVED.**
- `.../ext-self-review-plan-marshall/scripts/_self_review_patterns.py` — the registry, D2.
  **OBSERVED.**
- `.../ext-self-review-plan-marshall/scripts/self_review.py` — D3. **OBSERVED.**
- `marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/pre-submission-self-review.md`
  — the check list and the verdict shape, D2/D3. **OBSERVED.**
- `marketplace/bundles/plan-marshall/skills/extension-api/standards/ext-point-self-review-surfacing.md`
  — the contract. **OBSERVED.**
- The orchestrator inbox write verb — D4. **HYPOTHESIS**, verify at outline.
- `test/pm-plugin-development/` — tests. **OBSERVED.**

## Claim labels

| Claim | Label | Confirm/refute artifact |
|---|---|---|
| The stale-count detector opens only `SKILL.md` while its sibling globs the standards directory | **OBSERVED at HEAD** | Both functions live in `_self_review_detectors.py`. ⛔ **Re-read them — line numbers move, and the asymmetry is the premise D1 rests on.** |
| Neither the scope token nor the file-count token appears anywhere in the self-review script or its workflow doc | **OBSERVED — an asserted ABSENCE, re-verify it** | Search both files in the clone. **An asserted absence carries the higher verification burden**: if either token now exists, D3 changes shape. |
| Two registry entries are counted in the total with no consuming check | **OBSERVED** | The registry plus the workflow's check list — both in the clone. Confirm the count of entries **and** the number of checks; do not trust either figure as stated here. |
| A verdict reported a specific candidate count of which two were examined by nothing | **OBSERVED, but the artifact is NOT reachable from this clone** | It lives in a machine-local run record. ⛔ **Do not go looking for it.** The claim is settled instead by the registry-versus-check-list comparison above, which is entirely in the clone. |
| A round asserted a literal appeared in zero files while three survivors were live in merged main | **OBSERVED (second-hand, from the epic that handed this over)** | ⛔ **Re-derive before pinning a test to it.** Their own caveat discipline applies to material they hand us. |
| The self-seeding round mechanism | **OBSERVED twice, second-hand for the sizing** | The *pattern* is what D5 acts on; the token figures are leads. Re-derive any figure quoted. |
| A message aimed at a running plan is undeliverable | **OBSERVED, and structural** | The drain is an orchestrator act between plans — confirm from the inbox verb's own contract in the clone. |

## Verification

- **D1 and D2 are verified by negative controls, not by green runs.** Plant a stale count in a
  standards doc; remove a check from a counted registry entry. Both must fail. A suite that only
  demonstrates the happy path passes against both defects as they stand today.
- **D2's population-derived test must publish the population size** it enumerated. A set-guarding
  detector that can return zero from an empty population and still report success is the archetype
  this whole plan is about.
- **D3 is verified against this plan's own output.** Read this run's PR body and self-review rounds:
  if any absence claim in them lacks a scope statement, D3 has failed regardless of what the code
  does.
- **D5 carries a cold read**: whether the termination criterion reads as *converged* versus *out of
  budget* is exactly the distinction a later reader must not collapse. Dispatch the pre-PR
  verification sub-agent to read it cold and report which reading it took.
- Full `./pw verify` per the lane contract's build gate.

## Notes

- **Sequencing.** No dependency; the surface this repairs has already shipped. ⚠ **Re-verify D2
  against the landing of the plan that shipped one of these two detectors** — it may already carry
  part of it.
- ⛔ **Never pair with the executor-generator fixtures plan** — both change what "population-derived
  fixture" means in this repository. Land one, then read it.
- ⚠ **D4 touches the orchestrator inbox surface**; re-verify nothing else is editing it concurrently.
