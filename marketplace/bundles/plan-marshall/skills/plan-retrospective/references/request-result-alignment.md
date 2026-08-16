# Aspect: Request-Result Alignment

Did the plan deliver what the user asked for? Purely LLM-driven — no script produces facts.

## Inputs

- `request.md` — original user request, plus refine-phase clarifications.
- `solution_outline.md` — goals and deliverables captured in outline phase.
- `metrics.md` — final totals (when present).
- `references.json` — `affected_files` list.
- `work.log` — phase transitions and decisions.

## TOON Fragment Shape

```toon
aspect: request_result_alignment
status: success
plan_id: {plan_id}
goals[*]{text,status,evidence}:
  "Add opt-in retrospective skill",fulfilled,"SKILL.md + 12 refs + 5 scripts present"
  "Add rate-limit middleware",partial,"handler.py done; config wiring pending"
gaps[*]{goal,reason}:
  "Add rate-limit middleware","deliverable 4 not executed in this run"
scope_creep[*]{detail}:
  ...
findings[*]{severity,message}:
  info,"All declared deliverables completed"
  warning,"One goal partially fulfilled — follow-up plan recommended"
```

## LLM Interpretation Rules

- Extract goals from the `Summary` and `Deliverables` sections of `solution_outline.md`. Each deliverable heading is a top-level goal.
- Every coverage judgement below compares against the deliverable's **modification-intent** declarations — its `Affected files` bullets except those annotated `(read)`. `affected_files` is a diff, so a path the deliverable declared it would only read can never appear in it; counting one as an expected modification caps achievable coverage below the 70% bar **by construction**, grading the declaration style rather than the execution. A bullet with no annotation states no intent and is counted.
- A goal is `fulfilled` when `affected_files` intersects its declared modification-intent list AND task status is `done`.
- A goal is `partial` when task is `done` but `affected_files` coverage is < 70% of its declared modification-intent files.
- A goal whose declarations are **entirely** read-intent has no expected modification, so coverage is not applicable: judge it on task status alone and say so — never render it as 0% coverage.
- A goal is `missed` when no task with matching deliverable index reached `done`.
- Scope creep = modified files NOT covered by any deliverable's declared Affected files. This one comparison uses the **full** declared list, read-intent entries included: a file the plan declared it would touch at all is not a surprise, whatever intent it named. Small amounts (< 5 files) are acceptable; larger amounts indicate outline drift.

## Finding Shape

```toon
aspect: request_result_alignment
severity: info|warning|error
message: "{one-line}"
goal: "{goal text, truncated to 80 chars}"
```

## Out of Scope

- Quantitative efficiency — that is plan-efficiency.
- Chat-level narrative — that is chat-history-analysis.

## Persistence

After synthesizing the TOON fragment per the shape documented above, the orchestrator writes the fragment to `work/fragment-request-result-alignment.toon` via the `Write` tool and registers it with the bundle:

```bash
python3 .plan/execute-script.py plan-marshall:plan-retrospective:collect-fragments add \
  --plan-id {plan_id} --aspect request-result-alignment --fragment-file work/fragment-request-result-alignment.toon
```

`compile-report run --fragments-file` consumes the assembled bundle in Step 4 of SKILL.md. The bundle file is auto-deleted on successful report write; on failure it is retained for debugging.
