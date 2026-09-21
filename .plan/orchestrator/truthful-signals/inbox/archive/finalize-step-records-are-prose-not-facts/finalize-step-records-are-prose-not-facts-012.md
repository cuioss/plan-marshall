envelope_version=1
sender_type=plan
sender_id=finalize-step-records-are-prose-not-facts
epic=truthful-signals
kind=candidate-lesson
created=2026-08-02T12:18:36Z

component=plan-marshall:plan-retrospective
category=bug
confidence=high
source_plan=finalize-step-records-are-prose-not-facts
source_pr=1076
source_aspects=script_failure_analysis

# report-structure.md names aspect keys in snake_case; collect-fragments requires kebab-case

## Context

`plan-retrospective/references/report-structure.md` § "Section List" names each section's trigger fragment by aspect key, in snake_case:

> 3. Artifact Consistency — renders the `artifact_consistency` aspect fragment ...
> 4. Log Analysis — renders the `log_analysis` aspect fragment ...
> 6. Invariant Outcomes — renders the `invariant_summary` aspect fragment ...
> 10. Script Failure Analysis — ... renders the `script_failure_analysis` aspect fragment

`collect-fragments add` rejects all four. Its registry is kebab-case:

```
Valid aspect keys: ['artifact-consistency', 'chat-history-analysis', 'direct-gh-glab-usage',
 'dispatch_boundaries', 'execution-context-dispatch-audit', 'invariant-summary',
 'lessons-proposal', 'llm-to-script-opportunities', 'log-analysis', 'logging-gap-analysis',
 'manifest-decisions', 'permission-prompt-analysis', 'plan-efficiency',
 'request-result-alignment', 'routing-decisions', 'script-failure-analysis', 'wrapper-tangle']
```

This run issued four `add` calls using the reference doc's exact spellings and got four `Unregistered aspect key` errors. Note the registry is not internally consistent either — `dispatch_boundaries` is the one snake_case entry in an otherwise kebab-case list.

The same doc/registry split runs through the per-aspect reference files: each one's TOON Fragment Shape opens with a snake_case `aspect:` value (`aspect: plan_efficiency`, `aspect: request_result_alignment`, `aspect: logging_gap_analysis`, `aspect: llm_to_script_opportunities`, `aspect: lessons_proposal`) while its own Persistence section then registers under the kebab-case key.

## Root cause

Two naming conventions for the same identifier with no single source of truth: the fragment's internal `aspect:` field and the registration key drifted apart, and the section-list doc followed the internal field. The registry guard (added to stop compile-report silently dropping a section) is what makes the drift visible instead of costly — it converts what would have been a lost report section into a hard error.

## Proposed action

1. Pick kebab-case (it is already the registry's and the Persistence sections' convention) and rewrite `report-structure.md`'s section list to use it.
2. Normalise `dispatch_boundaries` to `dispatch-boundaries` so the registry has one convention.
3. Normalise the `aspect:` field inside each reference's TOON Fragment Shape to match the registration key, so a fragment's self-identification and its registration key are the same string.
4. Add a test asserting that every aspect key named in `report-structure.md` is accepted by `collect-fragments add`.

## Evidence

- Four `collect-fragments add` rejections this run: `artifact_consistency`, `log_analysis`, `invariant_summary`, `script_failure_analysis`
- `references/report-structure.md` § "Section List" items 3, 4, 6, 10 — the snake_case spellings
- The `valid_aspects[17]` list returned by the rejection — kebab-case except `dispatch_boundaries`
