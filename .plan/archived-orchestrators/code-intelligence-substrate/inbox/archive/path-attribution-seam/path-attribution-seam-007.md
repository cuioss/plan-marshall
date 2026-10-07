envelope_version=1
sender_type=plan
sender_id=path-attribution-seam
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-08-01T18:34:36Z

component=plan-marshall:manage-tasks
category=improvement
bundle=plan-marshall

# The keyword-drift checker cannot see quoted-artifact provenance — and the agent-supplied attribution that accompanied its finding was itself wrong

## What happened

The 4-plan Q-Gate mechanical check `qgate-mechanical-checks` raised `keyword_drift`:

> TASK-011 uses 'pipeline' not present in deliverable outline

Triaged as a **false positive** and resolved `accepted`. The token `pipeline` occurs in TASK-011 only inside the compound `findings-pipeline`, quoted from the **existing** `desc` text of `doc/resources/diagrams/extension-topology.svg` — the very artifact TASK-011 must extend. It is a quotation of the target artifact, not invented scope.

The checker's haystack is the deliverable-outline text. That haystack structurally **cannot** contain a phrase that lives inside an SVG the task edits, so the drift check has no way to see the provenance. The check is not misconfigured; it is blind by construction to one legitimate source of task vocabulary.

## The second, more interesting defect

The finding as filed asserted that the phrase came from the **deliverable-7 body**. It does not — deliverable 7 contains no occurrence of `pipeline` at all. The correct provenance is the SVG's `desc` attribute.

So the finding carried a confident, specific, and **wrong** provenance claim alongside a correct-in-form drift detection. The conclusion (no scope drift) was unchanged, but a triager who had trusted the stated attribution and checked deliverable 7 would have found nothing there and could plausibly have concluded the token was invented — i.e. upheld the false positive on the strength of a bad provenance pointer.

## The rules

**Do X — resolve provenance against the artifact, never against the checker's or the agent's stated attribution.** When triaging a drift finding, grep the *named* source for the token before accepting the attribution. An attribution is a lead, not evidence.

**Do X — when a task legitimately quotes text from an artifact it edits, expect drift checks to fire.** Quoted-target-artifact vocabulary is a known false-positive generator for any check whose haystack is the plan's own prose. Consider extending the checker's haystack to include the text of artifacts the task declares it will modify, or marking quoted spans so the check can exclude them.

**Not Y — do not treat a mechanical checker's finding as carrying a mechanically-derived explanation.** The *detection* here was mechanical (token absent from haystack) but the *attribution* was LLM-supplied narrative attached to it, and only the detection half had a guarantee behind it. Those two halves of a single finding have very different trust levels and should not be read as equally reliable.

## Why it is worth a fix rather than a note

`accepted` false positives cost triage time on every recurrence, and this one is systematic rather than incidental: any task that extends an existing documentation artifact by quoting its current text will trip it. The cheap version is to widen the haystack to include declared target-artifact contents; the cheaper-still version is to have the checker report the token's absence *without* asserting where it came from, so no wrong provenance is introduced into the finding in the first place.
