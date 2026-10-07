envelope_version=1
sender_type=plan
sender_id=finalize-step-records-are-prose-not-facts
epic=truthful-signals
kind=candidate-lesson
created=2026-08-02T11:38:21Z

component=plan-marshall:phase-6-finalize
category=anti-pattern
bundle=plan-marshall
source_plan=finalize-step-records-are-prose-not-facts
source_pr=1076
source_finding=842926

# A doc-scanning detector that splits on a token match collects PROSE as a call site

## Observation

The plan added a population-derived contract test,
`test/plan-marshall/phase-6-finalize/test_step_records_facts_contract.py::test_work_performed_is_recorded_on_every_done_call_site`,
which walks each finalize-step markdown doc, splits it into "call sites", and asserts every
`--outcome done` call site carries `--fact work_performed`.

It failed on `default:sonar-roundtrip`. The flagged text was **not a `mark-step-done` invocation at all** —
it was the narrative paragraph at `sonar-roundtrip.md:140` documenting the `head_dependent` frontmatter
obligation, whose prose reads *"Every `--outcome done` branch below MUST capture the worktree HEAD SHA"*.

Root cause: `_call_site_blocks` admitted **any line carrying the `mark-step-done` token** whose block also
matched `--outcome`. A sentence that merely NAMES both tokens was therefore collected as a done call site
with no `--fact work_performed` — a false positive. The helper's own docstring already claimed prose was
excluded, so the docstring documented an exclusion the code did not implement.

## Why this matters beyond the one test

This is the **false-positive twin of the vacuous-guard archetype**. The recurring lesson so far has been
"a predicate that never fires". This is the inverse: a predicate that fires on text that is not a member of
the population it claims to scan. Both share one cause — the detector's unit of analysis was never pinned to
a structural boundary, only to a token.

A markdown-scanning detector is especially exposed because the documents it scans are *about* the very
invocations it is looking for. Every well-written skill doc discusses `mark-step-done` and `--outcome done`
in prose. The population a doc-scanning detector wants (real invocations) and the population it accidentally
gets (invocations plus every sentence describing one) are guaranteed to differ, in every doc, forever.

## Rule

1. A doc-scanning detector MUST anchor its unit of analysis to a **structural boundary**, not a token match.
   For invocation detection that boundary is the fenced code block: an occurrence outside a fence is prose
   by construction and is never a call site.
2. Every such detector MUST carry a **mutation guard** proving the boundary holds — a fixture containing a
   prose-only mention of the target token, asserted to yield zero call sites. Without that guard the
   boundary is a claim, not a property.
3. When a helper's docstring asserts an exclusion, the exclusion needs a test. This defect was reachable
   precisely because the docstring's claim ("prose is excluded") was believed instead of pinned.

## Resolution in-plan

TASK-008 tightened the call-site boundary to real invocations only, corrected the misleading helper
docstring, and added the prose-only-rejection mutation guard.
