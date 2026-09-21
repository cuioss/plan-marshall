envelope_version=1
sender_type=plan
sender_id=daemon-audit-logs-interactions-not-job-lifecycles
epic=truthful-signals
kind=candidate-lesson
created=2026-07-28T16:19:25Z

component=plan-marshall:plan-retrospective
category=bug
bundle=plan-marshall

# Two mandated retrospective aspects have no registry key, so their findings can never reach a report

## What was observed

Running this retrospective, `collect-fragments add` rejected two of the aspects the
skill's own workflow mandates:

```
status: error
error: "Unregistered aspect key: 'direct-gh-glab-usage'. It is not in the canonical
        section registry nor any domain-contributed aspect set, so compile-report would
        silently drop its section."
valid_aspects[15]: artifact-consistency, chat-history-analysis, dispatch_boundaries,
  invariant-summary, lessons-proposal, llm-to-script-opportunities, log-analysis,
  logging-gap-analysis, manifest-decisions, permission-prompt-analysis, plan-efficiency,
  request-result-alignment, routing-decisions, script-failure-analysis, wrapper-tangle
```

The same rejection applies to `execution-context-dispatch-audit`.

Both are **required** aspects in `plan-retrospective/SKILL.md` § Step 3:

| Order | Aspect | Script(s) |
|-------|--------|-----------|
| 10 | Direct gh/glab usage (Surfaces A+B) | `direct-gh-glab-usage` |
| 11 | Execution-context dispatch audit | (LLM on logs + dispatch decisions) |

The SKILL documents the exact `collect-fragments add --aspect {name}` call for each.
`standards/execution-context-dispatch-audit.md` § Persistence even spells out
`--aspect execution-context-dispatch-audit` verbatim. And
`references/report-structure.md` lists 15 sections, none of which is either aspect.

So three documents mandate producing these fragments, and neither the registry nor the
compiler has anywhere to put them.

## Impact on this very run

Both aspects produced real findings that the report does not carry:

- `direct-gh-glab-usage` found the `gh` auth failure at work.log:254 — the WARNING line
  that is the first thread of this run's headline review-coverage defect.
- `execution-context-dispatch-audit` found one `dispatch_coverage_violation`
  (`architecture-refresh` marked done with no `[DISPATCH]` evidence).

Both are preserved only because this run carried them into the lessons-proposal fragment
by hand. A mechanical run loses them silently.

## Why it matters to this epic

`compile-report` reports `sections_dropped[0]` and `status: success`. The run is
*correctly* reported as lossless, because the loss happened one stage earlier — at
registration, where the aspects were never admitted. The clean compile signal is true and
useless: it certifies that nothing was dropped from the bundle, not that the bundle is
complete. A completeness claim measured against the bundle cannot detect content that
never made it into the bundle.

## Proposed action

Decide the intent and make all four surfaces agree — SKILL.md Step 3's aspect table, the
`collect-fragments` section registry, `report-structure.md`'s section list, and
`compile-report`'s renderer:

- If both aspects are wanted (they are — one is a hard-rule audit), add
  `direct-gh-glab-usage` and `execution-context-dispatch-audit` to the registry and add
  their sections to the compiler.
- The regression guard should be **population-derived**, not hand-listed: assert that
  every aspect row in SKILL.md's Step 3 table has a registry key and a compiler section.
  A hand-maintained list of three names is how this drift survived in the first place.

## Evidence

- `collect-fragments add` rejection output, quoted verbatim above (this run)
- `plan-retrospective/SKILL.md` § Step 3 aspect table, rows 10 and 11
- `plan-retrospective/standards/execution-context-dispatch-audit.md` § Persistence
- `plan-retrospective/references/report-structure.md` § Section List (15 sections, neither present)
