envelope_version=1
sender_type=plan
sender_id=user-language-and-vocabulary
epic=operator-ux
kind=candidate-lesson
created=2026-09-03T06:07:56Z

# Admitting a file to scope is not admitting its mirrored sites: the second copy in an already-scoped file survives

**Proposed component**: `plan-marshall:phase-3-outline`
**Proposed category**: `anti-pattern`
**Evidence class**: Q-Gate findings raised AND resolved in-run (the slipped-then-caught class)
**Signal**: `signal_qgate_pending_count` — 9 of the run's 11 Q-Gate findings are instances of this one class

## The observation

This plan changed one authoritative fact (`DEFAULT_PROJECT` in `manage-config/scripts/_config_defaults.py`, which IS the fail-closed project-field whitelist) and, later, one routing fact (`field_not_found` -> `unknown_field` for `project get`, TASK-007). Every hand-maintained *mirror* of those facts went stale independently.

The outline-phase scope validator caught the mirror problem and was explicitly corrected for it. Finding `681b91` rejected an understated sweep population and forced a verbatim re-sweep, which established the full 16-file `DEFAULT_PROJECT` referrer set and concluded "documentation fallout was found NOT to be zero: 3 of the 6 doc referrers enumerate literally and are now scoped". Three docs were duly admitted to deliverable 2 (`addc9a` api-reference.md, `7f3191` provisioning-fail-closed-audit.md, `9b058b` doc/user/configuration.adoc).

**It still shipped drift — inside the very files that sweep admitted.** Three of the four 6-finalize `contract_drift` findings land in files that were already in scope for this exact reason:

- `api-reference.md` was admitted by `addc9a`, whose resolution named its two edit sites precisely: "the 'Noun: project' set-verb row's literal field-set enumeration" (line 125) and "that section's Fields table" (lines 129-133). A **third** copy of the same closed set sat at line 712 under Common errors. Finding `040b3f` at 6-finalize: "The same document was updated at line 125 ... so api-reference.md now contradicts itself on the same closed set." The plan's own edit made the file self-contradictory.
- Line 712 was then hit a **second** time by an unrelated drift from the same plan (`cf4d3e`: the bullet still attributed `unknown_field` to `project set` only, after TASK-007 gave `project get` the same error).
- `provisioning-fail-closed-audit.md` was admitted by `7f3191`, which named its two stale rows at lines 43 and 70. Finding `a6d9cb` later found the **line-number parentheticals inside those same rows** (row 43 among them) off by one against the live file.

So the sweep found the right FILES. It did not find the right SITES within them, and a file admitted for one occurrence was edited at that occurrence while its siblings survived untouched.

## Why the existing guard did not close it

The detector that caught all three is `pm-plugin-development:ext-self-review-plan-marshall` (the `component` field on every one of those findings), whose deterministic candidate set already includes source-of-truth duplicates and stale count-prose. It works. But it runs at **6-finalize, after the change has landed** — it is a drift detector, and drift needs a delta to exist. The outline-phase `scope_criterion_validator` is the only gate positioned before the edit, and it reasons at file granularity: it answers "does this file mirror the constant?" and stops at the first yes, because that yes is already sufficient to admit the file.

The gap is granularity and phase placement, not detector existence.

## Corrective rule (the actionable part)

Two rules, both already demonstrated as the *fixes* the findings themselves converged on:

1. **When the outline admits a file to scope BECAUSE it mirrors a changed fact, enumerate every site in that file that mirrors it — not the first one found.** File admission and site enumeration are separate obligations. The evidence a scope note records should be a site list, not a file list; `addc9a` recorded two sites and there were three.
2. **Prefer eliminating the mirror over refreshing it.** Both 6-finalize remedies took this shape and said so explicitly: `040b3f` was fixed by "re-point[ing] api-reference.md:712 at the DEFAULT_PROJECT keys instead of adding a sixth name to a second hand-maintained enumeration"; `a6d9cb` by "delet[ing] the line-number parentheticals ... rather than re-deriving them a third time. The rows name their sites by symbol, which is stable across edits". A refreshed mirror is a mirror that will go stale again; a re-pointed or deleted one cannot.

Rule 2 is the stronger of the two, because it is the only one that reduces the mirror population rather than raising the cost of tracking it. This plan re-derived one locator set twice and got it wrong once before deleting it.

## Why this is an epic-level candidate rather than a plan-local note

The mirror population is a property of the corpus, not of this plan: `manage-config`'s field set is enumerated literally in at least four places (SKILL.md:1485, api-reference.md:125, api-reference.md:712, provisioning-fail-closed-audit.md) and two of those were re-pointed at the source of truth *by this plan*. Whether the remaining hand-maintained enumerations across the bundle corpus should be systematically re-pointed is a cross-plan judgement this plan cannot make.

## Cross-references

- Q-Gate findings: `681b91`, `addc9a`, `7f3191` (3-outline); `040b3f`, `cf4d3e`, `a6d9cb` (6-finalize)
- Detector that caught the finalize half: `pm-plugin-development:ext-self-review-plan-marshall`
- Gate that caught the outline half at file granularity: `scope_criterion_validator` (phase-3-outline Step 3c)
- Not covered by `plan-retrospective`'s five candidates or by `finalize-step-review-retrospective`'s Sourcery recurrence.
