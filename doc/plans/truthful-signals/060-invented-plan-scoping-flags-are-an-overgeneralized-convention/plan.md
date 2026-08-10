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

# Invented `--plan-id` flags are an over-generalised convention that prose cannot fix

**Epic:** truthful-signals
**Branch prefix:** fix

## Problem

Callers keep invoking scripts with a `--plan-id` flag the target verb does not declare, and argparse
rejects them with a bare exit 2. In one plan's run this accounted for **2 of 4 script-failure
clusters** — inside a workflow whose agents all load the rule prohibiting exactly that, unconditionally.

The valuable part is the diagnosis, not the count. **The caller is not guessing wildly — it is
over-generalising a real and near-universal convention.** Nearly every `manage-*` verb *is*
plan-scoped and *does* take `--plan-id`, so the flag reads as ambient boilerplate rather than a
per-verb declaration. `ci checks status`, by contrast, is repo/PR-scoped.

**Therefore prose cannot fix this.** "Don't invent flags" asks the reader to suppress a *correct*
pattern-match on the basis of a carve-out invisible from the call site. A rule that every agent has
loaded and that still fires repeatedly is not doing the work it claims to do — which makes this a
**vacuous guard in the documentation layer**, the same family as the code-layer instances this epic
tracks.

Three further instances sharpen the shape:

- **A second sub-shape — a closed enum with no member expressing the caller's intent.** In another
  repository, a `manage-findings qgate add` call failed at exit 2 where the invocation surface was
  otherwise sound. `--type` is `required=True, choices=FINDING_TYPES`, and `FINDING_TYPES` appears to
  have **no `escalation` member** — yet the lost finding was an *escalation*. If that holds, "don't
  invent flags" is not merely unpersuasive, it is **unfollowable**: the caller's intent has no
  admissible encoding, so the remedy is a surface question, not a discipline question.
- **A verb's own help text advertising a flag the verb does not accept.** `ci pr view --help`
  documents `--head` as "an alternative to `--pr-number`", but `pr view` does not appear to declare
  `--pr-number` — so invoking it fails at the top-level parser. A caller misled by accurate-looking
  help is not making a guess, and no amount of caller discipline fixes it.
- **A misattributed diagnostic.** `check_auth_cli` reports "Not authenticated" for *every* non-zero
  exit, including a missing binary. Observed live where the real cause was a `gh` **PATH** problem in
  a dispatched leaf — leaves appear to receive a truncated PATH. The diagnostic is confident and the
  caveat (we do not actually know why the call failed) is suppressed, which sends the operator to the
  wrong fix. This is this epic's archetype living inside an error message.

## Goal

The invented-flag failure is structurally impossible or self-correcting rather than merely
prohibited: a caller that gets it wrong is told what the right invocation is, and a document that
advertises a flag its verb does not declare is caught before a caller trusts it.

## Deliverables

1. **D1 — GATE: measure the real shape, then choose a structural remedy over a stronger rule.**
   Mutates nothing.
   - **(a) Quantify.** Mine the script-failure corpus for `argparse_rejection` exit-2 events and
     classify each: invented `--plan-id` on a non-plan-scoped verb; other invented flags; **closed-enum
     values with no member matching caller intent**; genuine typos. **Include help-text-vs-declared-flag
     divergence in the corpus**, not only rejected invocations. ⛔ **Do not scope from n=2.** The known
     instances span two repositories and are still too few to scope from.
   - **(b) Determine the carve-out.** Enumerate the **non**-plan-scoped verbs across the `manage-*` and
     `ci` surface. If that set is small and stable, the convention is near-total and the remedy differs
     from the case where it is large and arbitrary.
   - **(c) Choose the remedy, with an explicit bias AWAY from another prose rule.** Candidates,
     cheapest first: an **actionable argparse error** naming the correct invocation for that verb
     (turning a dead exit-2 into a self-correcting one); **accepting-and-ignoring** `--plan-id` where
     harmless; making the plan-scoping property **visible at the call site**; a plugin-doctor check
     flagging docs that advertise an undeclared flag.
     ⚠ **Adding emphasis to the existing prose rule is an explicitly REJECTED option** unless D1 argues
     why this instance differs — it has already failed at n≥3.
   *Done when:* the classified corpus, the carve-out set, and the chosen remedy with its rationale are
   all recorded in the report.
   ⛔ **STOP CONDITION.** If the corpus cannot be mined — the failure records are unavailable or too
   sparse to classify — **halt and report that**. Do **not** proceed to D2 on the strength of the
   handful of instances described above; scoping a structural change from anecdote is what this
   deliverable exists to prevent.
2. **D2 — Implement the D1 remedy.** Scoped to whatever D1 selects.
   *Done when:* the remedy is implemented and D1's recorded rationale matches what shipped.
   ⛔ **Hard constraint: no verb's real argument surface may be widened merely to absorb the mistake**
   — unless D1 explicitly decides accept-and-ignore *is* the remedy and records the trade. Silently
   accepting a meaningless flag trades a loud failure for a quiet one, which is this epic's own
   anti-pattern.
3. **D3 — Tests.**
   - (a) The exact failing invocation shape (`ci checks status --plan-id …`) produces D1's chosen
     behaviour — first **verified to produce a bare exit-2 against current code**, so the test pins the
     fix rather than the defect.
   - (b) A correct invocation is unaffected.
   - (c) If D1 adds a doctor check: a doc advertising a non-existent flag is flagged, and a correct doc
     is **not**.
   *Done when:* all three hold, with the negative cases present.

Three deliverables, deliberately small. The value is in D1's diagnosis, not in volume.

## Out of scope

- **Why the rejection was survivable.** In one instance the executor hit the exit-2, **continued past
  it**, and silently lost the finding. That fail-open behaviour is a separate defect owned by another
  plan in this epic. This plan owns why the call was *rejected*; that one owns why the rejection did
  not stop anything. Folding them together would produce a plan spanning two unrelated mechanisms.
- **Remediation of existing argparse rejections.** A `recipe-fix-argparse-rejection` recipe already
  exists for that. This plan is **prevention** — confirm there is no overlap rather than duplicating
  it.
- **The dispatched-leaf PATH truncation itself, beyond recording it.** If D1 confirms leaves get a
  truncated PATH, that is a real defect in its own right and worth its own plan; fixing the
  *diagnostic* without fixing the *environment* still leaves dispatched CI calls failing, so the
  report must say so — but a run with no operator should not silently expand into an environment fix
  it was not scoped for.

## Expected surface

- `marketplace/bundles/plan-marshall/skills/tools-integration-ci/**` — the `ci` argparse surface,
  including the `checks status` verb and `pr view`'s `--head` / `--pr-number` handling.
- `marketplace/bundles/plan-marshall/skills/manage-change-ledger/**` — a second rejection site of the
  same class.
- `marketplace/bundles/plan-marshall/skills/manage-findings/**` and the `FINDING_TYPES` constant — only
  if D1 confirms the closed-enum sub-shape.
- A shared argparse / error-emission helper, **if one exists** — the natural home for an actionable
  rejection message. ⛔ Confirm a shared seam exists before assuming it.
- `marketplace/bundles/pm-plugin-development/**` — only if D1 picks the doc-check remedy.
- `test/**` — tests.

## Claim labels

⚠⚠ **This plan is derived from a spec that carried NO claim-label section.** Labels were deliberately
**not** retrofitted at authoring time: assigning `OBSERVED` to a claim the author did not personally
verify manufactures provenance, and a wrong label reads as a checked one — which is worse than a
missing one.

⇒ **Treat EVERY claim below as `HYPOTHESIS` until this run verifies it**, including every count,
every file path, and every asserted absence. ⭐ **Asserted absences are the higher-risk half**: an
unverified "X does not exist, build it" produces duplicate work against a surface that already
exists, and nothing downstream trips over it. **Labelling is this run's job, before any deliverable
is sized.**

| Claim | Label | Confirm/refute artifact |
|---|---|---|
| `ci checks status` is repo/PR-scoped and does not declare `--plan-id` | HYPOTHESIS | the `ci` argparse surface under `tools-integration-ci` — read the verb's declared arguments |
| Invented `--plan-id` accounted for 2 of 4 script-failure clusters in one run | HYPOTHESIS | D1(a)'s corpus mining. ⛔ A count from a single run is a **lead**; re-derive |
| Nearly every `manage-*` verb is plan-scoped and takes `--plan-id` | HYPOTHESIS | D1(b)'s enumeration — this is the premise the whole diagnosis rests on |
| `FINDING_TYPES` has no `escalation` member | HYPOTHESIS | the `FINDING_TYPES` constant under `tools-file-ops` — an asserted **absence**, verified as a presence |
| `ci pr view --help` advertises `--pr-number` while the verb does not declare it | HYPOTHESIS | run `--help` and read the declared arguments; ⛔ this was recorded as **unsettled** — it may have been an invocation error by the observer |
| `check_auth_cli` reports "Not authenticated" for every non-zero exit including a missing binary | HYPOTHESIS | that function's source |
| Dispatched leaves receive a truncated PATH, making `gh` unreachable | HYPOTHESIS | reproduce inside a dispatched leaf; this is the claimed **mechanism** behind the misattributed diagnostic |
| `recipe-fix-argparse-rejection` exists and is remediation rather than prevention | HYPOTHESIS | that recipe's own text — ⛔ read it before building anything adjacent, or this plan ships a duplicate |
| No shared argparse error-emission seam exists | HYPOTHESIS | ⛔ asserted **absence** — search before building one |

An asserted **absence** is verified exactly as an asserted presence, and is the higher-risk half.
Every count above is a **lead** — re-derive it at the moment of the claim.

## Verification

- ⛔ **If D1 picks the actionable-error remedy, the error message is text-whose-value-is-what-a-reader-
  does** — so it gets a **cold read**. Show the Step 6 verification sub-agent only the new error
  output from a failing invocation, with no other context, and have it state what it would run next.
  The correct answer is the working invocation. If it cannot tell, the message failed however
  complete it looks.
- (b)'s carve-out enumeration must **publish the population it scanned**, not just the non-plan-scoped
  verbs it found. A list of exceptions with no denominator is not a carve-out, it is a sample.
- D3(c)'s negative case (a correct doc is not flagged) is as load-bearing as the positive one — a
  doctor check that fires on correct docs is a regression.
- Python and test changes are expected, so the build gate takes its full path.

## Notes

- **The remedies are complements, not alternatives.** An actionable error catches the caller; a doctor
  check catches the document that misled them. D1(c) should be free to pick both.
- Theme fit: a *documentation-layer* vacuous guard. The rule exists, is loaded, is correct, and does
  not fire in the reader's head at the moment it is needed — which is indistinguishable, in outcome,
  from a predicate that cannot fire.
- ⛔ **Do not go looking for the orchestrator spec, the inbox message, the other repository's plan
  archive, or any landing record.** They live under `.plan/` or outside this repository, and are
  absent from this clone. Everything needed is in this file; where evidence is genuinely unreachable,
  the honest move is to say so in the report, not to reconstruct it.
