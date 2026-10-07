envelope_version=1
sender_type=plan
sender_id=lane-router-reads-the-wrong-body
epic=truthful-signals
kind=candidate-lesson
created=2026-07-29T10:56:26Z

component=pm-plugin-development:ext-self-review-plan-marshall
category=bug
proposed_title=A clean self-review over 40 candidates missed the plan's own doc-contract divergence

# A clean self-review over 40 candidates missed the plan's own doc-contract divergence

## Status

**Observed during `lane-router-reads-the-wrong-body`, NOT fixed.** The missed defect is **live on merged main** (`83a0466d2`) as a MAJOR CodeRabbit finding.

## What happened

`pre-submission-self-review` ran at 08:59-09:08Z, spent **291,624 tokens across 59 tool uses and two dispatches**, and returned:

```text
self-review clean: 40 candidates examined, no check matched
```

The candidate-count gate had fired DISPATCH (`total_candidates=40`, above the 5 threshold), so this was the full cognitive-phase review, not a fast path.

Two and a half hours later CodeRabbit reviewed the same diff and found, at **`marketplace/bundles/plan-marshall/skills/phase-1-init/SKILL.md:824-831`** — a file **this plan itself edited**:

> The doc claims an unset `change_type` deep-biases via DQ1/S3. It cannot. `s3_deep = change_type in _DEEP_CHANGE_TYPES and not narrow_and_concrete`, so `None` can never satisfy the membership test and never fires S3. `S2` explicitly ORs `scope_estimate is None`; `S3` does not.

## Why this one matters more than a normal miss

Three compounding facts:

1. **It is the exact defect class the plan was built to fix.** The plan's subject is a router whose describe-side documentation diverges from what the code actually does. The plan then *authored a new instance of that divergence in the router's own contract doc* and shipped it.
2. **It is in the deliverable's declared affected-files set.** This is not an adjacent file the review had no reason to open. `phase-1-init/SKILL.md` was named in `references.affected_files`, and the Q-Gate at 06:40:56Z had specifically flagged D2 for *under-covering* the describe-side surface at `phase-1-init/SKILL.md:822` — the review had been pointed at these exact lines by the plan's own quality gate.
3. **`40 candidates examined` is a VOLUME, not a coverage number.** The report reads as thoroughness. It measures how many deterministic candidate sites the surfacer emitted, not whether the semantic claim in each edited doc paragraph was checked against the code it describes.

## The structural gap

`ext-self-review-plan-marshall` surfaces deterministic candidate classes (regexes, help strings, count-prose, producer-consumer pairs, description-vs-body frontmatter, ...). A **normative prose claim about control flow in a SKILL.md that the same commit also changed the code for** is not among them — so it was never a candidate, and "no check matched" is literally true while being materially wrong.

The failure is not that a check misfired. It is that **the clean verdict was reported at a confidence the candidate set could not support**, with no statement of what the 40 candidates did and did not cover.

## Proposed action

1. **Add a candidate class**: for every `.md` hunk in the diff that asserts a conditional/control-flow claim (`if X then Y`, `an unset Z causes W`, `A biases toward B`) *and* whose commit also touches a source file in the same skill, surface the paired (prose claim, code predicate) for explicit verification. This plan's diff would have produced exactly one such pair and it is the defect.
2. **Make the clean verdict scope-qualified.** `self-review clean: 40 candidates examined, no check matched` must become `clean over {enumerated classes}; NOT covered: {classes}`. A verdict that does not name its own blind spots is the confident-signal-hides-a-caveat shape this epic exists to eliminate.
3. **Feed Q-Gate findings into the self-review candidate set.** The 06:40:56Z Q-Gate finding named `phase-1-init/SKILL.md:822` as an under-covered describe-side surface. That finding was resolved `taken_into_account` at outline time and then never re-entered the review pipeline. A prior gate's flagged location is the highest-prior candidate available and it is currently discarded.

## Evidence

- `status.json` `phase_steps[6-finalize][pre-submission-self-review]`: `self-review clean: 40 candidates examined, no check matched`
- `logs/decision.log` 08:59:06Z — `Candidate-count gate DISPATCH - total_candidates=40 (>5 threshold, cov_scope=inherit)`
- `logs/decision.log` 06:40:56Z — Q-Gate D2 fail: `describe-side surface phase-1-init/SKILL.md line 822 is in no Affected files`
- `execution.toon` — 291,624 tokens / 59 tool uses spent on the step
- CodeRabbit review of `07778c3b`, posted 2026-07-29T10:32:41Z, severity Major
