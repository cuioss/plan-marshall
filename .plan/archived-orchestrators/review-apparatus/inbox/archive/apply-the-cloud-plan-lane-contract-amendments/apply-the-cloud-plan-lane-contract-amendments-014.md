envelope_version=1
sender_type=plan
sender_id=apply-the-cloud-plan-lane-contract-amendments
epic=review-apparatus
kind=candidate-lesson
created=2026-09-05T06:30:13Z

component=pm-plugin-development:ext-self-review-plan-marshall
category=improvement
created=2026-09-05

# Two of three cells in one table row were de-duplicated; the third was left enumerating and five self-review rounds passed over it

## Observation

This PR's whole purpose in that region was de-duplication: replacing inline value enumerations
with cross-references to the Step 7 subsection that defines them. In the report template's
reviewer-participation table row it did exactly that for the **Class** column and the **Verdict**
column — and left the **`Reopens?`** column still enumerating `yes` / `no` / `unknown`, which
Step 7 (lines 1434-1438) defines. CodeRabbit caught it (finding `ebea56`,
`.claude/skills/cloud-plan-lane/SKILL.md:2242`, Minor, remediated in-run by TASK-008):

> Line 2242 repeats `yes`, `no`, and `unknown`, while Lines 1434-1438 define those values.
> Replace the inline list with a cross-reference so the report template cannot drift from Step 7.

In the run's own triage note: *"the same defect class this PR already fixes twice in that very
table row … an incomplete execution of this PR's own de-duplication work, not a new request."*

## The part that makes this worth an epic message

`default:pre-submission-self-review` ran **five rounds** over this file — dispatched at 15:07,
15:18, 15:20, 15:29, 15:32, 15:42, 15:44, and again at 18:21 and 00:29 — producing three
`outcome=failed` rounds, five `self-review-finding-fix-*` sub-dispatches, and a closing verdict of:

```text
16:01:16  Complete - round 5 full-surface clean, 6 candidates, 0 findings
```

A "full-surface clean" verdict, on the exact file, immediately upstream of a reviewer finding a
value-set duplication in a cell whose two siblings the same PR had just fixed. The self-review
surfaced 6 candidates and this was not among them.

## The detector this suggests

`ext-self-review-plan-marshall` already surfaces "source-of-truth duplicates" and
"same-document normative directives" as deterministic candidate classes. This instance sits in a
blind spot between them, and it has an unusually crisp mechanical signature:

> **Sibling-cell asymmetry.** Within a single markdown table row (or a single fenced-template
> stanza), N cells of a related group carry a cross-reference to a definition elsewhere in the
> document and M cells enumerate literal values instead. Any row where `N >= 1` and `M >= 1` is a
> candidate — the row itself is the evidence that the author considered the values non-local, and
> the enumerating cell is the one that did not get the treatment.

This is derivable without judgement: it needs only the row's cell contents and a test for
"contains a cross-reference" versus "contains a literal value list". It does not require knowing
which values are authoritative. And it is precisely the shape a *partial* de-duplication pass
leaves behind — which is the common case, because a de-duplication pass that misses everything is
noticed, while one that misses one of three is not.

## Overlap disclosure

`plan-retrospective` already routed a message about **the 9-vs-5 self-review defect undercount**.
That message is about the *count* — how many self-review defects the step reported against how
many existed. This one is not a count claim: it names one concrete, mechanically detectable shape
the current candidate set does not cover, and proposes the predicate for it. The two are
complementary — the undercount says the step under-reports, this says one specific reason why —
and neither restates the other.

## Ancillary note recorded for completeness

The remediation deliberately added **no lockstep guard test** for the surviving duplication,
because an operator decision on this plan explicitly superseded guarding the duplication in
favour of removing it. Two items stay in that cell by design (blank-for-a-completed-review, and
the label-suppression clause) because they are report-template semantics rather than value
definitions and are defined nowhere else. A future detector must not flag those.
