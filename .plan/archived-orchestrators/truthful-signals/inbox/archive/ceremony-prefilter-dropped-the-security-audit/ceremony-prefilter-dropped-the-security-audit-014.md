envelope_version=1
sender_type=plan
sender_id=ceremony-prefilter-dropped-the-security-audit
epic=truthful-signals
kind=candidate-lesson
created=2026-07-29T16:54:38Z

component=plan-marshall:plan-retrospective
category=bug
created=2026-07-29

# compile-report calls a lost section a benign omission and an empty section written

Two defects observed inside the very run that produced this plan's retrospective report — both in
`compile-report`'s three-valued section outcome, which exists precisely to keep a lossy run from
reading as a clean one.

**1. A section with payload was classified as a benign omission.**
`compile-report` returned `sections_omitted: [Phase Dispatch Boundaries, Permission Prompt
Analysis]` and `sections_dropped: []`, i.e. `status: success`. But `references/report-structure.md`
item 5 specifies that Phase Dispatch Boundaries is emitted "when the `dispatch_boundaries` fragment
carries at least one phase entry reporting `present: true`" — and the registered `log_analysis`
fragment carries `dispatch_boundaries` with `present: true` for **all three** of `4-plan`,
`5-execute` and `6-finalize`, including the seven rows and the `unknown_count` field. Per the same
document's Conditional Rule, a fragment that is present and carries payload but does not render is
a **drop** (loud, status → `warning`), not an omission (benign). The section that carried the
evidence that dispatch recording stopped after the loop-back is the one that went missing, and it
went missing under the label that means "nothing was lost".

**2. An empty section was reported as written.**
`Executive Summary` appears in `sections_written` while the emitted body is the literal placeholder
`_No executive summary provided._`. The compiler has no `executive_summary` fragment to consume and
does not report its absence — the report's first and most-read section was empty behind a
`sections_written` entry and a `status: success`.

The `written / omitted / dropped` partition is documented as "a mechanical probe over the fragment
bundle — did this fragment carry anything beyond its envelope keys?". Both defects are that probe
answering for the wrong thing: for (1) it never looked inside `log_analysis` for the nested trigger,
for (2) it counted a heading it emitted rather than content it rendered.

## Solution

- **Fix the Phase Dispatch Boundaries trigger** to read `log_analysis.dispatch_boundaries[*].present`
  as `report-structure.md` specifies, and route a present-but-unrendered fragment to
  `sections_dropped` so the run's status is raised to `warning`.
- **Do not count a placeholder as written.** A section whose body is the "not provided" placeholder
  belongs in `sections_omitted` with the missing fragment named — or, better, the orchestrator
  should be required to register an `executive-summary` fragment and the compiler should report its
  absence.
- **Add a self-test** over the partition: for each conditional section, assert that a fragment
  bundle known to satisfy its trigger produces the section in `sections_written`.

## Impact

Affects every retrospective report. The consequence is precisely the one the three-valued partition
was introduced to prevent: a lossy compile returning `status: success` with an empty
`sections_dropped`, so the caller cannot tell a complete report from an incomplete one. Filed by the
run it happened to.
