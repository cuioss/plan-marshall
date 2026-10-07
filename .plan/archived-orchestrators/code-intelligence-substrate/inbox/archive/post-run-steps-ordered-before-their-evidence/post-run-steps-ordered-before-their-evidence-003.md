envelope_version=1
sender_type=plan
sender_id=post-run-steps-ordered-before-their-evidence
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-08-02T21:54:03Z

component=plan-marshall:phase-6-finalize
category=anti-pattern
title=A reviewer's named site list is a sample - only an exhaustive class sweep closes the finding

# A reviewer's named site list is a sample - only an exhaustive class sweep closes the finding

## Observation

Within a single run (PLAN-CIS-028), the archetype **"a named site list is a sample, not an enumeration"** recurred **three separate times**. Each time the sequence was identical:

1. A reviewer (or an internal analysis) named N concrete sites exhibiting a defect class.
2. The remediation fixed exactly those N sites.
3. Siblings of the same class stayed live, and the finding reopened.
4. Only an **explicitly exhaustive class sweep** — derive the population, then fix every member — actually closed it.

Three recurrences inside one plan is not three incidents; it is evidence the default remediation reflex is "fix what was named".

## Rule

When a finding names specific sites, the finding's scope is the **class**, not the list. Before declaring it resolved:

- **Derive the population mechanically.** Enumerate every member of the class from the structured inventory / an actual query — never from the reviewer's prose, and never from memory.
- **State the derived cardinality in the fix.** "N sites named, M found, M fixed" — where M is the derived number. If M == N, that is a *result*, not an assumption.
- **Fix every member, or explicitly justify each exclusion.** A silent subset fix is indistinguishable from a complete one at the review site, which is exactly why the class reopens.
- Treat a reviewer's list as a **detector's sample output**. It proves the class exists; it says nothing about the class's size.

## Impact

This is the same archetype as the earlier "CodeRabbit named 3 `write_status` callers, real count 14" recurrence, and the sibling rule that **every set-guarding detector must be population-derived**. Three fresh recurrences in one run confirm the reflex is not yet corrected by the existing guidance; the corrective belongs where remediation decisions are made (triage / self-review), not only in the detector-authoring standard.
