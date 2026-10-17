# Review Rubric — the shared grading contract of the two finalize reviews

Two finalize steps review a plan's change before it is pushed, and they ask different questions:

| Step | Question it answers |
|------|---------------------|
| `default:functional-review` | Did the plan deliver every deliverable and every success criterion it was asked for, with evidence — and did it change only what it was asked to change, and say so truthfully? |
| `default:code-review` | Is the change well made, judged against the rulebook of the domains it touches and the project's own conventions? |

This document is the rubric both read. It is the **only** place the blocking line is stated: each step body states what it examines and how it records its outcome, and points here for how a finding is graded, what counts as evidence, where a blocking finding loops back to, and when a round may close. A step body that restates any of those rules is a second copy that can drift from this one; it cites the section instead.

## 1. Severity vocabulary

Every finding either review produces carries exactly one severity:

| Severity | Meaning | Effect on the round |
|----------|---------|---------------------|
| `blocking` | The finding must be resolved before the change is pushed. | The round records `loop_back` to the target § 6 selects. The finding is written to the plan's finding store before the outcome is recorded. |
| `advisory` | The finding is substantiated and reported, but the change may ship with it. | The round may close. The finding is recorded with the round's facts and reaches the reader; it does not loop. |

There is no third severity and no unscored finding. A finding the reviewer cannot place on one side of the line is not yet substantiated — see § 3 and § 5 — and is not reported until it is.

## 2. Functional grading — `default:functional-review`

The functional review grades every outline deliverable with exactly one verdict:

| Verdict | Meaning |
|---------|---------|
| `met` | Every success criterion of the deliverable carries evidence (§ 4). |
| `met_with_residuals` | The deliverable's value is delivered, and the residuals — what is missing or partial — are named on the row. |
| `not_met` | The deliverable's value is not delivered. |
| `superseded` | The deliverable no longer applies, and the row cites the operator decision or the refutation that retired it. A `superseded` row without that citation is not a valid verdict. |

The blocking line for the functional review:

- A `not_met` deliverable is `blocking`.
- A success criterion that is `unevidenced` (§ 4) is `blocking`.
- A **residual** on a `met_with_residuals` row is graded by its consequence: `blocking` when the missing part is part of what the deliverable was asked to deliver, `advisory` when it is not.
- An **unrequested change** — a file the change touches that no deliverable declares or is attributed — is graded by its consequence: `blocking` when it alters behaviour, a contract or a document a reader acts on, `advisory` when it does not.
- A **false or stale self-report** — a task note, a commit message, a decision-log entry or a document line that claims something the change does not do — is graded by its consequence. A false claim a reader would act on is `blocking`; a claim no reader acts on is `advisory`.

## 3. Code-review grading — `default:code-review`

A code finding is **substantiated** only when it carries all three of:

1. **A cited rule** in one of the forms § 5 lists.
2. **A location** as `file:line`.
3. **A failure scenario** — the input or state that triggers the finding, and what goes wrong.

A finding missing any of the three is not a finding; it is rejected, not downgraded.

The blocking line for the code review:

- A substantiated finding whose failure scenario produces **a wrong result, lost data, a fail-open path, or a broken contract** is `blocking`.
- Every other substantiated finding is `advisory`.

The grade follows the failure scenario, never the reviewer's sense of how important the finding is: the charter in § 9 forbids withholding a substantiated finding as minor, and this section is what turns "reported" into "blocking" or "advisory".

## 4. Evidence for a met criterion

A success criterion is `met` only when the row cites at least one piece of evidence in one of these forms:

| Form | Example shape |
|------|---------------|
| A code or document location | `path/to/file.py:42` |
| A test identifier | `test/module/test_file.py::test_name` |
| A recorded verification run | the step id or build run the plan recorded, with its outcome |

A criterion claimed `met` without evidence is `unevidenced`, never `met`. The claim is not taken on trust and not upgraded by agreement with the plan's own notes: the plan's self-report is the thing being checked (§ 9, the intent clause), so it cannot also be the evidence for itself.

## 5. Citation forms for a code finding

A code finding cites its rule in one of these forms:

| Form | What is cited |
|------|---------------|
| Pack rule | A bullet of a domain's `## Review Rules` block (§ 10), named by its skill and the rule text. |
| Spine category | A cross-cutting category of the code-review spine. |
| Project convention | A project convention file and the heading that states the convention. |
| ADR | An architecture decision record, by number. |

A finding that names no rule in any of these forms is uncited and is rejected (§ 3).

## 6. Loop-back target selection

A round with at least one `blocking` finding records `loop_back`. The target is chosen by what the fix needs:

| The fix needs | Target | What happens |
|---------------|--------|--------------|
| New implementation — code, tests or documents that do not yet exist in the change | `5-execute` | The blocking findings become fix tasks, and execute runs them before finalize resumes. |
| Only a correction to the diff in hand — a false note, a stale document line, a one-line amendment | `6-finalize` | Finalize replays inline and the correction is made on the branch in hand. |

When the blocking set holds both kinds, the target is `5-execute`: one implementation gap is enough to need execute, and the corrections ride along as fix tasks.

## 7. Author and verifier

The party that authors a review's verdict is not the party that accepts it.

- The **author** reads the inputs, grades every finding against this rubric, and produces the verdict — the deliverable rows for the functional review, the findings list for the code review.
- The **verifier** is a second dispatch, issued from the inline dispatcher context — never from inside the author's envelope, because a dispatched envelope cannot dispatch further (see [`../../ref-workflow-architecture/standards/agents.md`](../../ref-workflow-architecture/standards/agents.md)). It files no finding and edits no file. It answers exactly two questions:
  1. **Is the grading supported by the cited evidence?** — every verdict, severity and citation checked against the evidence the author named.
  2. **May the round close?** — no `blocking` finding survives, and the verifier accepts the grading.

A round closes only when both answers are yes. The author cannot close its own round.

## 8. Delta rounds, the closing round, and operator overrides

- **A re-fire after a fix is a delta round.** It covers the deliverables and files the fix touched — a deliverable is in the delta when it declares or is attributed a file the fix changed — not the whole change again.
- **A clean delta round is followed by one closing round.** A round with no `blocking` finding is followed by one closing round over every deliverable before the verifier may accept closure. The closing round is what proves the fixes did not break a deliverable outside their own delta.
- **An operator override of the round cap closes only the head the operator judged.** When the operator closes a review past its round cap, the override covers the HEAD that was in front of them and nothing later. Every later fix commit still gets a delta round, and that round is not charged against the round budget. Each override-closed head is recorded as a fact on the step, so a retrospective can name exactly what shipped unreviewed.

## 9. Code-review charter

The code review carries these four clauses verbatim. They are the same clauses the external review bot's spine carries, so the in-run reviewer and the bot work to one charter.

**Substantiation:**

For each finding, name the input or state that triggers it and what goes wrong. Overlap with other reviewers is acceptable — report the issue regardless of whether another tool might also catch it. Do not withhold a substantiated finding because it seems minor or obvious.

**Anti-fabrication:**

An empty list remains the correct answer when the diff genuinely carries nothing substantiable, and you must never invent a finding, pad the list, or report an issue whose mechanism you have not traced in the code shown. But do not return an empty list because nothing reached a bar of severity or importance. There is no such bar.

**Intent as a claim:**

If the pull request description states what the change is intended to do, treat that as a claim to be checked, not as established fact. Report where the implementation diverges from the stated intent, and never treat agreement with it as evidence that the code is correct.

**Severity is not a threshold:**

Severity is not a reporting threshold. Report a finding you can substantiate even when it is narrow, cheap to fix, or confined to test code — the reader decides what to act on, and a finding declined as minor costs one line of triage. Do not weigh whether an issue is important enough to mention.

The charter governs **whether** a finding is reported; § 3 governs **how** a reported finding is graded. Reporting every substantiated finding and blocking only on the § 3 failure classes are two halves of one rule, not a contradiction.

## 10. Harvestable review-rule blocks

The code-review rulebook is harvested from the domain standards skills, by the in-run code review and by the review bot's pack generator alike. A standards skill contributes through two section headings in its `SKILL.md`:

| Heading | Contents |
|---------|----------|
| `## Review Categories` | The domain's review categories — what kinds of defect a reviewer looks for in this domain. |
| `## Review Rules` | The domain's review rules — the concrete rules a finding cites. |

Every block follows four rules:

- **One rule per bullet.** A bullet that carries two rules cannot be cited as one.
- **Mechanism-naming wording.** A rule names the mechanism that goes wrong — what input or state, and what breaks — so a finding citing it can state a failure scenario.
- **Addressed to a reviewer.** A rule states what to look for in the code, not how an author should work.
- **No withholding language.** A rule never tells the reviewer to suppress a finding it could substantiate — no "do not duplicate", no "only when you can name the concrete input". The pack generator drops a harvested rule that carries such a phrase rather than rewriting it, so a rule written that way never reaches a reviewer at all.

## 11. The not-run state

A review that could not read its inputs reports `not_run`, never a clean verdict. An unreadable request, outline, task set, footprint or rulebook means nothing was evaluated, and a `clean` record for an unevaluated change is a green that no check ever produced. The `not_run` state is recorded separately from a clean result, with the reason the inputs could not be read, so a reader can tell "examined and found nothing" from "not examined". This is the same separation ADR-019 makes for every audit: what could not be evaluated is reported apart from what was evaluated and found wanting.
