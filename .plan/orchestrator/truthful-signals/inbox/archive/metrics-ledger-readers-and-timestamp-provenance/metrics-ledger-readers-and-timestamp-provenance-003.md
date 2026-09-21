envelope_version=1
sender_type=plan
sender_id=metrics-ledger-readers-and-timestamp-provenance
epic=truthful-signals
kind=candidate-lesson
created=2026-08-24T20:00:39Z

component=plan-marshall:plan-retrospective
category=bug
confidence=high
source_plan=metrics-ledger-readers-and-timestamp-provenance
source_pr=1342

# Derive declared files from structured deliverables, not by scraping outline prose

## Context

`check-artifact-consistency` reported:

```
affected_files_recall,pass,Recall 71% meets threshold
  declared: 31   found: 22   recall_pct: 71.0
```

The true declared-write-intent recall is **100%**. The outline declares 22 distinct
`intent: write-replace` paths across its nine deliverables, and all 22 appear in the
merged footprint of PR #1342.

All nine "missing" entries are parser pollution, not files:

- six `**Risk**:` / `**Mitigation**:` prose bullets, lifted verbatim as whole sentences
- the bare symbol name `analyze_shim_marker`
- the sentence `none — this deliverable is read-only; it produces two derived lists…`
- the step notation `project:finalize-step-era-stamp-fill`

So the denominator carried nine non-members, and the check reported a wrong number
that nonetheless cleared its threshold. Nobody looks at a `pass`.

## Root cause

The declared-file set is recovered by scraping bullets out of the outline's markdown
prose. Any bullet in the neighbourhood of the affected-files region is treated as a
path. Meanwhile `manage-solution-outline list-deliverables` already returns
`affected_files` as structured rows carrying `path`, `intent` and `foreign` — the
exact data, already parsed, already distinguishing read from write intent.

This is the repository's own **structured queries first** rule, violated by its own
retrospective tooling against its own structured source.

## Proposed action

Replace the prose scrape with a call to
`manage-solution-outline list-deliverables --plan-id {plan_id}`, take the union of
rows whose `intent` is not `read`, and compute recall over that. As a defence in
depth, reject any candidate "declared file" that fails a path shape test (contains
whitespace, contains `**`, or has no path separator and no file extension).

Additionally: a recall figure whose denominator cannot be validated should not be
graded `pass` on a threshold alone. Publishing the denominator's provenance beside
the ratio is what would have made this visible.

## Evidence

- aspect artifact_consistency: `details.affected_files_recall`, `affected_files_exact_match.outline_only`
- `manage-solution-outline list-deliverables` → 22 distinct write-replace paths
- `git diff --name-only 77db1a0d3 91bbe7470` → 28 paths, containing all 22
