envelope_version=1
sender_type=plan
sender_id=domain-post-plan-narrow
epic=operator-ux
kind=candidate-lesson
created=2026-09-06T07:28:03Z

# Candidate lesson: two guards authored in the SAME commit diverged in guard strength (`.strip()` vs bare truthiness)

**Source**: plan `domain-post-plan-narrow` (PLAN-03, epic `operator-ux`), PR #1422
**Signal source**: orchestrator self-observation during the remedy for the run's dominant class
**Suggested component**: `pm-plugin-development:ext-self-review-plan-marshall`
**Suggested category**: `anti-pattern`
**Dedup read**: RECURRENCE-OR-NEW — the orchestrator should decide. Nearest actives below.

## Observation

While remedying the run's dominant failure class, the orchestrator wrote a pair of sibling guards in one commit. One tested the value with `.strip()`; the other stopped at bare truthiness. A whitespace-only value therefore passes the second guard and fails the first — the two siblings disagree about what "supplied" means, in code authored together, by one author, in one edit.

This is distinct from the "missed the Nth site" shape the run also produced (`7f14d3`, the fourth site of a three-site fix). There, a site was never touched. Here, **both sites were touched in the same edit and still diverged** — so no "did I find every site?" sweep would have caught it. The check that catches this one is "do the sites I just wrote agree?", not "did I find them all?".

## Nearest active lessons (for the merge-vs-new decision)

- `2026-09-04-17-014` — *Self-review found the same defect twice in the same regex and twice across sibling instruments, one round apart each*. Closest match; that lesson is about the same defect recurring across siblings a round apart, this one about siblings diverging within one edit.
- `2026-09-03-06-006` — *Admitting a file to scope is not admitting its mirrored sites*. Adjacent, but about scope admission rather than same-edit divergence.
- `2026-09-02-14-001` — *Verify a delete-to-one-home fix by re-searching the literal, not by enumeration*. Adjacent verification technique.

A `## Recurrence` note on `2026-09-04-17-014` is likely preferable to a near-identical new lesson, provided the note preserves the same-edit distinction — that is the part none of the three currently carries.

## Candidate corrective

When a change writes a symmetric pair (two guards, two mirrors, two lanes), compare the two written forms against each other before the round closes, not merely each against the requirement. The symmetric-pair detector already exists in `ext-self-review-plan-marshall`; the gap is that it did not fire on a strength difference between two guards, only on structural divergence.
