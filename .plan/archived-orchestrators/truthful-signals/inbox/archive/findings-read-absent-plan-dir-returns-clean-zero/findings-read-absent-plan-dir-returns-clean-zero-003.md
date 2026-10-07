envelope_version=1
sender_type=plan
sender_id=findings-read-absent-plan-dir-returns-clean-zero
epic=truthful-signals
kind=candidate-lesson
created=2026-08-30T14:08:28Z

component=plan-marshall:plan-retrospective
category=bug
disposition=new
source_plan=findings-read-absent-plan-dir-returns-clean-zero
source_pr=1369

# A recall-only coverage check scores an under-declared set 100% by construction, and defers the precision half to an aspect that never looks

## Observed in this run's own retrospective

`check-artifact-consistency` reported:

```
affected_files_recall,pass,Recall 100% meets threshold
  declared: 19   found: 19   missing[0]   recall_pct: 100.0
```

The realized footprint of this plan is **44 paths**. Twenty-five of them were never declared.

Recall is `|declared ∩ realized| / |declared|`. An under-declared set therefore scores **100% by
construction** — the smaller the declaration, the easier the pass. The check cannot fail on
under-declaration, which is the only failure mode that matters here.

## The dangling handoff

The precision half is not absent — it is present and deliberately declined:

```
affected_files_exact_match,info,Set mismatch — deferred to manifest aspect (see check-manifest-consistency)
  references_only[25]: ...
  forwarded_to_manifest: true
```

Severity `info`. Forwarded to `check-manifest-consistency`. And `check-manifest-consistency`, run
after the merge, resolved `origin/main..HEAD` to `files_total: 0` and reported **4 of its 5 checks
skipped, 0 findings, summary passed: 1 failed: 0**.

So aspect 1 declines to judge on the explicit promise that aspect 12 will judge, and aspect 12
never examines the forwarded set at all. Two individually-honest reports compose into a confident
clean verdict over a 25-file gap that neither of them looked at. Nothing in either output says the
handoff was not completed.

## A second defect in the same neighbourhood

`check-manifest-consistency` simultaneously emits, in one fragment:

- `diff.diff_available: true`, `diff.oracle_available: true`, `diff.files_total: 0`
- `branch_cleanup_changes,skip,rule M4 skipped — no diff data available (base=unknown or empty diff)`

The fragment asserts a diff is available and, four lines later, that no diff data is available.
A reader of the structured field and a reader of the check message reach opposite conclusions.

## Remedy (for the epic to scope)

1. **Publish precision alongside recall**, each with its own denominator:
   `|declared ∩ realized| / |realized|`. A set comparison that reports one direction cannot report
   set equality, and `affected_files_recall,pass` currently reads as though it did.
2. **A forward must be verifiable.** If aspect 1 forwards a finding to aspect 12, aspect 12 must
   either report on it or report that it could not — the current design has no channel for
   "forwarded and never received", so the gap is structurally invisible.
3. **Distinguish `resolved_empty` from `unavailable`** in the manifest aspect's diff block, so
   `diff_available: true` and "no diff data available" cannot both be true of the same diff.

## Why this belongs to truthful-signals

This is the epic's own archetype occurring inside the machinery built to detect it. The
retrospective reported `PASS, recall 100%` over a declaration covering 43% of what shipped.
