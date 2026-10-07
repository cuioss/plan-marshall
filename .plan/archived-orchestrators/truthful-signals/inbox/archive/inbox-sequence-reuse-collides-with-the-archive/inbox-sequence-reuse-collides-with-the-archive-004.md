envelope_version=1
sender_type=plan
sender_id=inbox-sequence-reuse-collides-with-the-archive
epic=truthful-signals
kind=candidate-lesson
created=2026-07-28T15:12:07Z

component=plan-marshall:plan-retrospective
category=bug
bundle=plan-marshall

# Two documented retrospective aspects use registration keys the registry rejects

`plan-retrospective/SKILL.md` § "Dispatch Aspects (in order)" lists 15 aspects.
Two of them cannot be registered at all:

| Aspect | Documented registration key | `collect-fragments add` result |
|--------|-----------------------------|-------------------------------|
| 10 — Direct gh/glab usage | `direct-gh-glab-usage` | `Unregistered aspect key` |
| 11 — Execution-context dispatch audit | `execution-context-dispatch-audit` | `Unregistered aspect key` |

Both keys are prescribed verbatim by their own docs:

- `references/direct-gh-glab-usage.md` — the aspect is script-backed
  (`plan-marshall:plan-retrospective:direct-gh-glab-usage`) and the SKILL's
  per-aspect capture pattern registers script-backed aspects under their aspect
  name.
- `standards/execution-context-dispatch-audit.md` § Persistence says explicitly:
  `collect-fragments add --plan-id {plan_id} --aspect execution-context-dispatch-audit`.

The registry accepts only these 15 keys:

```
artifact-consistency, chat-history-analysis, dispatch_boundaries,
invariant-summary, lessons-proposal, llm-to-script-opportunities, log-analysis,
logging-gap-analysis, manifest-decisions, permission-prompt-analysis,
plan-efficiency, request-result-alignment, routing-decisions,
script-failure-analysis, wrapper-tangle
```

Neither `direct-gh-glab-usage` nor `execution-context-dispatch-audit` is in it.

## Why this matters beyond a naming nit

The registry's own error text states the purpose of the guard:

> It is not in the canonical section registry nor any domain-contributed aspect
> set, so **compile-report would silently drop its section**.

The guard converts a silent drop into a loud register-time error — which is
correct — but the net effect is that **these two aspects have never appeared in
any retrospective report**. The dispatch audit is the enforcement consumer of the
`[DISPATCH]` logging contract and the only mechanical check for the
leaf/dispatch-topology invariant; the gh/glab aspect is the only mechanical check
for the CI-abstraction hard rule. Both are silently absent from every report,
while the report's own aspect list reads as complete.

This is the epic theme in its purest form: a report that names 14 written
sections and 0 dropped sections, produced by a pipeline that could not deliver
two of its documented checks.

## Corrective action

Add both keys to the canonical section registry with their report-section
headings, and add a closure test asserting **every aspect row in
`plan-retrospective/SKILL.md`'s aspect table has a corresponding registry key** —
a population-derived detector over the SKILL's table, not a hand-maintained list.
The recurring lesson applies: every set-guarding detector must be
population-derived.

## Evidence

- aspect: execution_context_dispatch_audit — fragment written to
  `work/fragment-execution-context-dispatch-audit.toon`, registration rejected,
  content preserved out-of-band
- aspect: artifact_consistency — `direct-gh-glab-usage` script ran successfully
  (`counts.total: 0`) and its fragment was likewise rejected
- report: `quality-verification-report.md` `sections_written[14]`,
  `sections_dropped[0]` — no trace of either aspect's absence
