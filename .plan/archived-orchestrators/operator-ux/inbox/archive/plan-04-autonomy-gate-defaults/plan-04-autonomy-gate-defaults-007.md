envelope_version=1
sender_type=plan
sender_id=plan-04-autonomy-gate-defaults
epic=operator-ux
kind=candidate-lesson
created=2026-09-07T12:44:45Z

# A multi-site sweep left siblings behind five times, including on lines the same plan had already edited

component: plan-marshall:execute-task
category: anti-pattern
confidence: high
source_signal: qgate findings (6-finalize 25c162 / 7beb81 / 866ade), pr-comment findings 56451a / e79008
dedupe_note: NOT the ext-self-review .adoc blind spot already filed as candidate 002. Every instance below is `.md`, inside the surfacer's declared format. The surfacer looked and the sites were not there to find, because the sweep that should have edited them had already declared itself complete.

## The defect

When this plan restated one fact at many sites, the sweep that was supposed to close the class stopped short, and the residue was found only by a later reviewer. Five independent instances in one run:

- `wizard-flow.md:521`, `wizard-flow.md:497`, `menu-configuration.md:231` — three sibling sites still carrying the single-tier framing of loop-back routing after commit `361ec93` swept the two-tier routing into five other sites. All three findings record the same sentence: *"This plan touched this exact sentence, then commit 361ec93 swept the routing into five sibling sites and did not return here."*
- `data-model.md:832` + two siblings (CodeRabbit 56451a) — the same class, caught externally. The plan then found a fourth site the reviewer had not cited (`phase-6-finalize/SKILL.md:110`).
- `execution.md:627` (CodeRabbit e79008) — the response records it plainly: *"execution.md:627 was simply missed."*

## Why the existing rules did not catch it

The corpus already forbids the *claim* half (`agent-behavior-rules.md` — never assert closure over an enumeration). It says nothing about the *coverage* half after an edit has begun. These five sites carried no closure claim to check; they were simply not revisited.

The aggravating factor is specific and repeatable: **a line the plan had already edited read as current.** All three `wizard-flow` / `menu-configuration` sites had been correctly edited earlier in the same plan for the default-value half, and that prior edit is exactly why the later routing sweep skipped them. An already-touched line is evidence that *one* fact at that site is current, never that every fact is.

## Corrective

1. A sweep that closes a class is not done when the edits are done — it is done when the **identifying query is re-run against the post-edit tree and returns only sites that are correct**. Re-run the sweep, do not reason about it from the edit list.
2. When a plan edits a site for reason A and a later commit sweeps reason B, the reason-A site is **in** the reason-B population. Exclude it only by reading it, never by remembering that it was touched.
3. Record the arithmetic, not the assertion (see the sibling candidate on closure claims): the shape that worked in this run was `23 returned = 18 declared + 5 excluded`.

## Boundary against the sibling candidate

This candidate is the **coverage** half: sites the sweep never reached. The sibling candidate is the **claim** half: artifacts that asserted a completeness they did not have. They co-occurred in this run but have different remedies — re-run the query here, record the arithmetic there.
