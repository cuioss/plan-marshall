envelope_version=1
sender_type=plan
sender_id=the-ledger-has-no-safe-single-row-append
epic=truthful-signals
kind=candidate-lesson
created=2026-09-07T08:07:24Z

component=plan-marshall:persona-plan-marshall-agent
category=anti-pattern
confidence=medium

# Check a doc-contract claim against the on-disk file, not the loaded skill body

## Context

While auditing this plan, two documents appeared to disagree about a closed enumeration. The `manage-metrics` SKILL.md body loaded into the session enumerated twelve dispatch termination causes at all three of its enumeration sites. `plan-retrospective/references/logging-gap-analysis.md`, read fresh from disk, enumerated thirteen - the same twelve plus `baseline_drift`.

That reads as a textbook doc-contract divergence, and `manage-metrics` SKILL.md even names the structural-equality test that is supposed to prevent it. Reporting it would have been a well-formed, confidently-worded, entirely fabricated finding.

Both files on disk are byte-identical copies of one another and both contain `baseline_drift` four times. The loaded skill body was stale relative to HEAD - skill bodies are seated at session start, and this session began three days before the enumeration reached its current form.

## Root cause

A loaded skill body and the repository file it came from are two different artifacts with two different currencies. Nothing at the point of use marks which one is being read, so an enumeration read out of context looks exactly as authoritative as one read off disk.

## Proposed action

Before reporting any doc-contract divergence, enumeration drift, or count-prose staleness, re-read the claim from the on-disk file. Loaded skill content is adequate for guidance and inadequate as evidence about the current state of the repository. The cost of the check is one read; the cost of skipping it is a fabricated finding that survives review because it is internally coherent.

## Evidence

- Loaded `manage-metrics` SKILL.md body: twelve causes at the bullet list, the command block and the canonical-invocations block; zero occurrences of `baseline_drift`.
- On disk, both `marketplace/bundles/plan-marshall/skills/manage-metrics/SKILL.md` and `target/claude/plan-marshall/skills/manage-metrics/SKILL.md`: 51,795 bytes each, byte-identical, `baseline_drift` present four times.
- `logging-gap-analysis.md`, read from disk during the same run: thirteen causes including `baseline_drift`.
