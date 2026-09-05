# Aspect: Request-Result Alignment

Did the plan deliver what the user asked for? Purely LLM-driven — no script produces facts.

## Exit-code convention for every script call

Every `python3 .plan/execute-script.py` call in this document — of EVERY notation, **not only `manage-*`** — carries the following exit-code contract unless a step explicitly states otherwise. The scope is widened past `manage-*` because this document invokes `collect-fragments` — a `manage-*`-scoped convention leaves exactly those calls with no rule at all, which is the swallowed-rejection gap.

- **`exit_code == 0` AND `status: success`**: parse the returned TOON and use the value as the step describes.
- **`exit_code == 0` with a `status` other than `success`, or with no parseable `status` at all**: NOT a usable value — STOP exactly as the `exit_code != 0` disposition below requires, with one difference in what the error TOON carries: on this path the diagnostic is on STDOUT, not stderr. Preserve the stdout **error envelope** as emitted — every field it carries, verbatim — into the returned error TOON; it is the only account of the cause that exists. Copy the whole envelope rather than a fixed field list, because the diagnostic fields vary by verb and `error` is sometimes a generic string whose real cause sits in one of the others. A zero exit is not evidence the operation succeeded; a script MAY print `status: error` and still exit 0. Read `status` FIRST, and never read a **success-payload** field off a non-`success` return. A malformed or truncated stdout carrying **no parseable `status` at all** takes this same path: an unreadable read is not evidence of success, so it fails closed onto STOP rather than falling through to the first clause.
- **`exit_code != 0`**: STOP and return an error TOON to the orchestrator carrying the script's stderr verbatim. Non-zero exits include `argparse_rejection` (exit 2) — silent swallowing of `wrong_parameters` rejections is the prohibited anti-pattern; "log and continue" is equally forbidden.

The middle clause is what the `ci` family makes load-bearing: a `ci` verb reports failure as `status: error` at exit 0 **by design**, so a caller must branch on the payload `status` and never on the exit code. That rule is stated authoritatively in `plan-marshall:tools-integration-ci`; it is not restated here.

Step-level exceptions — calls whose non-zero exit is itself the signal — are documented inline in the step that issues them.

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
- Every coverage judgement below compares against the deliverable's **modification-intent** declarations — its declared-file bullets except those whose intent resolves to `read`. The declared-file bullets are those under `Affected files:` **and** those under the survey-scope pair `Files expected to mutate:` / `Files to survey:`, which a survey-scope deliverable declares *instead of* a flat list. `affected_files` is a diff, so a path the deliverable declared it would only read can never appear in it; counting one as an expected modification caps achievable coverage below the 70% bar **by construction**, grading the declaration style rather than the execution. ⛔ Reading `Affected files:` alone drops a survey-scope deliverable's whole mutation surface out of the denominator and then counts those same files as scope creep below.
- **An unannotated bullet takes its heading's default intent, and the heading is not always silent.** `Affected files:` and `Files expected to mutate:` supply no default, so an unannotated bullet under either states no intent and **is counted**. `Files to survey:` supplies `read`, so an unannotated bullet under it is **not** counted — the heading is the declaration. An explicit annotation always wins over the heading's default, so an explicitly marked non-read bullet under `Files to survey:` is counted.
- The three verdicts below are **mutually exclusive and are evaluated in order** — the first that matches wins. Without an explicit order, a completed goal touching one of its five declared files satisfied both `fulfilled` (a non-empty intersection) and `partial` (coverage below 70%), and the verdict depended on which rule the reader happened to apply first.
- A goal is `fulfilled` when task status is `done` AND `affected_files` covers **at least 70%** of its declared modification-intent files. Intersection alone is not sufficient: one file out of five is not a fulfilled goal.
- A goal is `partial` when task status is `done` but that coverage is **< 70%** — including the case where the intersection is empty.
- A goal whose declarations are **entirely** read-intent has no expected modification, so coverage is not applicable: judge it on task status alone and say so — never render it as 0% coverage.
- A goal is `missed` when no task with matching deliverable index reached `done`.
- Scope creep = modified files NOT covered by any deliverable's declared file surface — `Affected files:` plus the `Files to survey:` / `Files expected to mutate:` pair. This one comparison uses the **full** declared list, read-intent entries included: a file the plan declared it would touch at all is not a surprise, whatever intent it named. Small amounts (< 5 files) are acceptable; larger amounts indicate outline drift.

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
