envelope_version=1
sender_type=plan
sender_id=required-reviewer-returns-empty-list
epic=review-apparatus
kind=candidate-lesson
created=2026-09-05T16:44:17Z

component=plan-marshall:manage-solution-outline
category=bug
created=2026-09-05
bundle=plan-marshall

# Prose under "Files to survey:" parses into path fragments and is persisted as read intent

## Context

Q-Gate `99cab6` at `3-outline`. Deliverable 1 declared four `Files to survey:` bullets as
free prose — repository names, foreign-repo descriptions, a PR reference — rather than
repo-relative paths. The structured reader
(`manage-solution-outline read --deliverable-number 1`) did not reject them and did not
report them as unparseable. It returned **three** `survey_scope` rows whose paths were:

```text
"scoped, outside the repository tree)"
"only)"
"only)"
```

These are fragments split at the parenthetical commas. None is a path. None is even
distinct — two are the identical string `only)`.

## Root cause

The parser splits the bullet text on commas and treats every resulting fragment as a path,
with no validation that a `survey_scope` entry looks like a path at all. Prose containing
commas therefore silently becomes structured data.

Two consequences, and the second is the reason this is a bug rather than cosmetic:

1. **Cardinality is not even preserved.** Four authored bullets became three rows. A
   consumer counting declared survey targets gets a number that matches nothing the author
   wrote — and has no signal that anything was lost.
2. **The garbage is persisted as declared intent.** Step 7 `sync-affected-files` derives
   `read_intent_files` from these same structured per-deliverable declarations, so
   `scoped, outside the repository tree)` and `only)` were written into `references.json`
   as the plan's declared read-intent footprint. The finding's remediation confirms this
   was not hypothetical — the recorded rows had to be explicitly corrected:

   > The persisted `read_intent_files` rows were corrected: `sync-affected-files` added the
   > two real paths, then `set-list` replaced the field with exactly those two, dropping the
   > malformed `only)` and `scoped, outside the repository tree)` fragments.

`mutation_scope` parsed correctly and `affected_files` was unaffected, so the write-set
declaration was never at risk. The defect is scoped to the survey / read-intent half —
which is precisely the half with no downstream consumer strict enough to notice.

## Why it stayed invisible

A malformed path in a *mutation* set fails loudly the moment something tries to write it.
A malformed path in a *read-intent* set is never opened, never diffed, and never compared
against the realized footprint (a read-intent path is expected absent from a diff by
definition). Nothing in the pipeline is positioned to notice that the string is not a path.

This connects to sibling candidate 001 from this plan (`check-outline-vs-shipped` not
consulting declared intent): both are cases where the read-intent half of the footprint
carries data that no consumer validates. They are distinct defects in distinct components
and should not be merged, but they are evidence of the same soft spot.

## Proposed action

1. Validate `survey_scope` / `mutation_scope` entries as path-shaped at parse time, and
   report a non-path entry as a structured parse diagnostic rather than emitting it as a
   row. An entry the reader cannot resolve must be visible as unresolved — never returned
   as a confident row containing a sentence fragment.
2. Preserve and report cardinality: if N bullets were authored and M rows resolved, M != N
   is itself reportable. The current behaviour cannot express "I read four things and
   produced three".
3. Consider refusing to persist a `read_intent_files` entry that is not path-shaped, so a
   parse defect cannot reach `references.json` even if step 1 is bypassed.
4. The authoring-side remedy applied here is worth documenting as the pattern: out-of-tree
   evidence (foreign repositories, orchestrator records, PR references) moved verbatim
   into a narrative block below the structured heading, leaving the structured heading
   carrying only back-ticked repo-relative paths. Verified after the fix: `survey_scope`
   yields exactly 2 rows, both real paths, cardinality matching the author.

## Evidence

- Q-Gate `3-outline` `99cab6` — triage, severity warning, `taken_into_account`, file `.../automatic-review/standards/cuioss-review-bot.md`
- `99cab6` detail — the three malformed rows quoted verbatim above
- `99cab6` resolution — the `references.json` `read_intent_files` correction via `sync-affected-files` + `set-list`
- `99cab6` resolution — peer audit: deliverables 2 and 3 declare flat `Affected files` and both re-parse cleanly, so no peer carried the same defect
