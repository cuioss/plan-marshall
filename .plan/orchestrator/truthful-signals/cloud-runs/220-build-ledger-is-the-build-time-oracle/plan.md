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

# Make the build ledger the build-time oracle

**Epic:** truthful-signals
**Branch prefix:** feature

## Problem

Build time is audited today by **regex-parsing a log**. The retrospective audit's
`sequence-and-build-minimality` check derives durations from `(N.NNs)` fragments in
`logs/script-execution.log`, and its documented classification population is `build-pyproject` calls
only.

⚠ **So this is a RE-BASING, not a greenfield addition.** The value is replacing a lossy derivation with
the structured ledger, **not adding a second derivation beside it**.

Two blindnesses come with the current approach, and both must be **named and closed rather than
silently inherited**:

- The derivation sees only one build system, so **Maven, Gradle and npm builds are invisible**.
- Builds run in the early phases **never reach the plan-scoped log at all**, so they are invisible
  regardless of tool.

⇒ **Today's build totals are undercounts of unknown size.**

⛔ **And a third problem makes the new oracle suspect before it is even consumed.** On one observed run
a `module-tests` build was **killed at 411 s by the wrapper's internal ceiling while the resolved
envelope promised 441 s**, and the routed status reported **`duration_seconds = 0`** against 411
seconds of real work. Two distinct defects sit there — *the published ceiling and the enforced ceiling
disagree*, and **a zero duration for a 411-second run makes the ledger's own duration field actively
false rather than merely absent.** ⭐ **A zero is indistinguishable from a cache hit or a no-op** —
the same conflation this epic recorded when a 2–5 second type-check green turned out to be a stale
cache. ⇒ **Any build-time total over archived plans under-counts by every killed run, by an unknown
amount.**

## Goal

Build time is derived from the structured ledger rather than from a log, covers every build system and
every phase, reports the aggregate on the plan's own reporting surface, and carries invariants that
make an impossible or fabricated duration visible instead of averaged in.

## Deliverables

1. **D0 — GATE: establish what already exists, and the wall-clock denominator.** Mutates nothing.
   Read the existing minimality check and enumerate **exactly which build facts it derives, from which
   source, over which population**. Then establish the wall-clock denominator the ratio needs.
   *Done when:* the existing facet inventory and the denominator are both recorded.
   ⛔ **Do not add a check that duplicates a facet already computed — fold instead.**
   ⚠ **Settle whether the metrics record is present often enough to be a reliable denominator.** The
   existing metrics check has an **absent-file branch**, so a ratio built on it inherits that hole.
   ⛔ **Treat `duration_seconds = 0` as a SUSPECT value requiring corroboration, never as data.**
2. **D1 — Re-base build-duration classification onto the ledger.**
   *Done when:* durations come from the ledger's structured field for **every** build system and every
   phase, and the report **quantifies the delta** against the old log-derived totals.
   ⛔ **Name both blindnesses explicitly in the report.** "We now see more" without a number is a claim;
   the delta is the evidence.
3. **D2 — The two new ledger-derived facets.**
   - **(a) Build time vs overall wall-clock** — the share of a plan's elapsed time spent inside builds.
   - **(b) Passing vs failing build ratio**, derived from the ledger status field across its four values
     (`success` / `error` / `timeout` / `killed`).
   ⛔ **`killed` is NOT `error`.** A whole-tree kill is an infrastructure event; collapsing it into
   "failed" would report a harness problem as a code problem.
   ⭐ **Add the invariant the existing metrics check's impossible-values family already models: build
   time cannot exceed plan wall-clock.** A violation is a **recording defect** — and it is precisely the
   check that would catch a duration plumbed through wrongly.
   *Done when:* both facets compute, `killed` is counted separately, and the invariant fires on a
   violating fixture.
4. **D3 — Report total build time on the plan's own reporting surface**, not only in the cross-plan
   audit.
   *Done when:* the aggregate appears on the surface D0 named.
   ⚠ **D0 names the exact surface — do not assume it is the retrospective report.** The request said
   "final report", which may name a different artifact. **This is the deliverable most likely to be
   aimed at the wrong file.**
5. **D4 — Tests, each verified to FAIL pre-fix, plus documentation reconciliation.**
   - (a) A ledger with a known mix of all four statuses produces the expected ratio, **with `killed`
     counted separately**.
   - (b) A build-time-exceeds-wall-clock fixture is flagged.
   - (c) **A non-pyproject build appears in the totals** — the test that proves the first blindness is
     closed.
   - (d) D0's population derivation is **asserted non-empty**.
   Reconcile the affected check documents **and the skill's stated check count**, which is written as a
   number in the skill description.
   *Done when:* all four pass, each seen red first, and no stale count remains.

Five deliverables, under the split presumption.

## Out of scope

- **Fixing the wrapper's internal ceiling disagreement.** The published number and the enforced number
  differing is a real defect, but it belongs to the build-wrapper surface, not to the audit consumer.
  **Record it; do not fix it here.** This plan's obligation is to stop *trusting* the resulting
  duration.
- **Producing the ledger fields.** A separate plan in this epic mutates the **producers** — the build
  scripts, the executor template, the wrappers, the ledger writer. This plan mutates **consumers**. The
  split is deliberate and keeps the two surface-disjoint.
- **Widening into general run measurement.** ⚠ By this epic's routing rule, measurement of our own runs
  belongs to a sibling epic and this would ordinarily be forwarded. **It was assigned here explicitly**,
  as part of one work chain — recorded so a later reader does not "correct" the routing. ⇒ **Notify that
  epic when this lands**: the audit corpus is what they read.

## Expected surface

- `.claude/skills/audit-archived-plan-retrospectives/checks/sequence-and-build-minimality.md` — the
  existing derivation to re-base.
- `.claude/skills/audit-archived-plan-retrospectives/checks/metrics.md` — the wall-clock source and the
  impossible-values precedent.
- `.claude/skills/audit-archived-plan-retrospectives/SKILL.md` — the stated check count.
- `.claude/skills/audit-archived-plan-retrospectives/scripts/**` — the implementing analyzers named in
  the check document, **located by symbol**.
- `marketplace/bundles/plan-marshall/skills/plan-retrospective/**` — for D3, **only if D0 names it**.
- Tests under the project-local skill's test home.

## Claim labels

| Claim | Label | Confirm/refute artifact |
|---|---|---|
| The audit skill has ~23 check documents and **none** references the change ledger | OBSERVED | the `checks/` directory and a search for the ledger's names. ⛔ An asserted **absence** — re-verify, since a sibling plan may have added one |
| `sequence-and-build-minimality` already performs build-duration classification from the script-execution log, scoped to one build system | OBSERVED | that check document — **by section**, and it is the fact that reframes this from "add" to "re-base" |
| The metrics check documents wall-clock and worked durations and already carries an impossible-values rule | OBSERVED | that check document — the precedent D2's invariant follows |
| The metrics check has an absent-file branch | OBSERVED | that document. ⛔ **The hole D0 must size** — a ratio built on a sometimes-absent denominator inherits it |
| The metrics record's wall-clock field is the right denominator, and is summable to a plan total | HYPOTHESIS | the producer that writes it — **D0 owns this** |
| The "final report" surface is the retrospective report rather than a distinct finalize artifact | HYPOTHESIS | **D0.** ⚠ An operator's naming of one artifact may under-scope or mis-aim the work |
| The existing shipping-predicate exclusion should apply identically to the new facets | HYPOTHESIS | **D0.** ⛔ Inheriting it silently would be as wrong as dropping it silently |
| A run was killed at 411 s against a promised 441 s envelope and reported `duration_seconds = 0` | HYPOTHESIS | ⛔ **REPORTED by another epic; not reproducible from this clone.** Treat as the reason for D0's suspect-zero rule, not as data |
| The ledger carries a structured duration field for every build system | HYPOTHESIS | ⛔ **the producer plan's landed output.** **This plan is meaningless until that field exists** — see the stop condition |

An asserted **absence** is verified exactly as an asserted presence, and is the higher-risk half.
Every count above is a **lead** — re-derive it at the moment of the claim.

## Verification

- ⛔ **STOP CONDITION, checked before anything else: does the ledger actually carry a structured
  duration for every build system?** If the producer work has not landed, or re-scoped away from
  plumbing duration, **halt and report that** — D1 and D2(a) both assume the field exists. Building a
  consumer for a field that is not there produces a check that silently measures nothing.
- ⛔ **D4(c) is the test that proves the blindness is closed.** Without a non-pyproject build in the
  fixture, the re-base is unverified and the totals may still be single-tool.
- ⛔ **`killed` must be visibly separate in the output**, not merely counted separately in the code. A
  reader looking at the ratio should be able to tell an infrastructure kill from a red build.
- **The suspect-zero rule must be demonstrated**: feed a zero duration alongside a real one and show the
  zero is flagged rather than averaged in. A zero silently included is worse than an absent value,
  because it drags an average toward a number nobody measured.
- Python, documentation, and test changes are expected, so the build gate takes its full path.

## Notes

- ⛔ **Hard dependency:** this plan consumes another plan's landed output — the structured duration
  field and a mandatory plan identifier on ledger rows. **Do not run it before that lands.** ✅ The two
  are **surface-disjoint** (producers versus consumers), so they never collide; the dependency is on the
  *output*, not on the files.
- ⚠ If D3 renders a duration alongside a timestamp, check for overlap with the display-timezone plan in
  this epic.
- ⛔ **Do not go looking for the orchestrator spec, the forwarded message, or any landing record.** They
  live under `.plan/`, which is git-ignored and absent from this clone. Everything needed is in this
  file.
