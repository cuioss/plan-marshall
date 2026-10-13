---
lane:
  class: adversarial
  cost_size: L
name: default:functional-review
description: Functional review before push — checks that the plan delivered every outline deliverable and success criterion with evidence, changed only what it was asked to change, and reported its own work truthfully; a blocking finding loops back to execute or finalize
order: 6
mutates_source: false
head_dependent: true
default_on: true
presets: []
records_facts:
  - acceptance
  - may_close
  - work_performed
  - round_kind
  - deliverables_reviewed
  - criteria_checked
  - files_read
  - deliverables_met
  - deliverables_met_with_residuals
  - deliverables_not_met
  - deliverables_superseded
  - criteria_unevidenced
  - unrequested_changes
  - false_self_reports
  - blocking_count
  - advisory_count
  - override_closed_heads
requires_prompt_fields:
  - attribution
  - verdict_file
implements:
  - plan-marshall:extension-api/standards/ext-point-execution-context-workflow
  - plan-marshall:extension-api/standards/ext-point-finalize-step
---

# Functional Review

The `functional-review` finalize step answers one question about the plan's change before it is pushed: **did the plan deliver what it was asked to deliver?** It grades every outline deliverable and every success criterion against evidence, audits the change for files no deliverable asked for, and checks the plan's own reports of its work — task notes, commit messages, decision-log entries, document lines — against what the change actually does.

How a finding is graded, what counts as evidence, where a blocking finding loops back to, what the verifier answers, and when a round may close are stated once, in [`../standards/review-rubric.md`](../standards/review-rubric.md). This document states what the step examines, in what order, and how it records the outcome; for grading, loop-back targets, the verifier questions and the delta-then-closing-round rule it cites the rubric section rather than restating it.

The procedure is the same for every language and build system: the step reads the plan's own record of what it was asked to do and compares it with the change, so no step here branches on the kind of file a plan changed.

## Exit-code convention for every script call

The exit-code contract for every `python3 .plan/execute-script.py` call in this document — of EVERY notation, not only `manage-*` — is stated once in [`tools-script-executor/standards/exit-code-convention.md`](../../tools-script-executor/standards/exit-code-convention.md); it is not restated here.

## Shell-safe free text in command templates

Several command templates below interpolate free text into a shell argument — a finding's or an advisory's title and ref, a verifier's reason, a rendered verdict line. The review writes that text, not this document, and it routinely carries backticks, `$` and quotes. This section is the one statement of the rule for both review steps: it governs the command templates of this document and of [`code-review.md`](code-review.md), which cites it rather than restating it. Every `manage-logging` `--message`, every `manage-findings` `--title` and `--detail`, and every `manage-status mark-step-done` `--display-detail` in either document is therefore written as ONE single-quoted shell argument, and the text is substituted into it by these rules:

1. **Single-quote the argument**: `--message '… {title}'`. Between single quotes the shell expands nothing — no backtick command, no `$(…)`, no `$VAR` — so the text reaches the verb byte for byte.
2. **Escape each embedded single quote as `'\''`** before substituting the value: close the quoted run, add an escaped quote, reopen the run. A title `don't` is substituted as `don'\''t`.
3. **Never put interpolated text in double quotes.** Inside double quotes the shell still runs a backtick or `$(…)` substitution and expands `$VAR`, and an embedded double quote ends the argument early, so a rendered command can run a substitution or break before the decision-log line or the finding is recorded.

None of the verbs these templates call — `manage-logging decision`, `manage-findings qgate add` and `qgate resolve-by-rule`, `manage-status mark-step-done` — takes the text from a file (each verb's `--help` lists the text only as an argument), so the single-quoted argument is the one safe form, and every template in both documents uses it. Each template that interpolates text names this section.

## Activation

This document carries no activation logic. The manifest composer decides whether the step runs (see [`../../manage-execution-manifest/standards/decision-rules.md`](../../manage-execution-manifest/standards/decision-rules.md)): the `commit_push_disabled` pre-filter drops it when the run will not push, the `scope_gated_finalize` pre-filter drops it on a surgical scope unless the step carries a declared lane, and the `functional_review` ceremony gate — this step's own `lane` — forces it out (`off`) or in (`minimal`) independently of every other review. When the dispatcher reaches the step, the step runs to one of the terminal branches of Step 6.

## Who does what

The step is **orchestrator-owned**: the phase-6-finalize dispatcher runs it in its own inline context, never as a dispatched leaf, because the step issues dispatches of its own and a dispatched leaf cannot (see [`../../ref-workflow-architecture/standards/agents.md`](../../ref-workflow-architecture/standards/agents.md)).

| Role | What it does | Where it runs |
|------|--------------|---------------|
| **Dispatcher context** | Resolves the round's scope (Step 1), chooses where the author runs (Step 2), validates the verdict (Step 4), dispatches the verifier (Step 5) and records the outcome (Step 6). | The inline phase-6-finalize context. |
| **Author** | Reads the plan's inputs and writes the verdict file (Step 3). | A dispatched envelope, or the inline context when the Step 2 gate keeps it inline. |
| **Verifier** | Answers the two questions of [`review-rubric.md`](../standards/review-rubric.md) § 7 about the author's verdict. Files no finding and edits no file. | Always a separate dispatch, issued from the inline context — on both author arrangements. |

**The author records nothing.** Its brief ends when the verdict file is written and its return names the file. The step outcome is recorded by the inline dispatcher context in Step 6, AFTER the verifier of Step 5 has answered — the party that wrote the verdict never records the round, and no outcome exists before the verifier has spoken.

When the author runs inline, the dispatcher context is itself the author, so the verifier MUST still be the Step 5 dispatch: running it inline would put author and verifier in one party.

## HEAD-dependency

The step declares `head_dependent: true`. Its verdict is a reading of the plan's diff, so a later commit produces a diff this step never examined. Capture `git -C {worktree_path} rev-parse HEAD` immediately before EVERY terminal `mark-step-done` call of Step 6 and forward it as `--head-at-completion {sha}`. The only branch that may omit it is Branch C, and only when the `rev-parse` itself fails.

The recorded SHA is also what the next firing's delta round is measured from: `review_support attribution --delta-step functional-review` reads this step's own record to decide between a full and a delta round.

**Verdict-input surface — deliberately undeclared.** The step declares no `verdict_inputs`. Its inputs are the plan's request, outline, task records and decision log — none of them in the tree difference — plus every file the change touches, which is derived at run time from the plan's own footprint. That is the discovered-input shape [`../standards/verdict-currency.md`](../standards/verdict-currency.md) § "The classification" names as having no sound static subset, so the step keeps the unconditional re-fire on every HEAD advance.

## Inputs of the dispatched author

| Prompt-body field | Required | Description |
|-------------------|:--------:|-------------|
| `plan_id` | Yes | Plan identifier. |
| `WORKTREE` | Yes | Working-directory path of the plan's worktree. |
| `attribution` | Yes | The TOON the dispatcher's Step 1 `review_support attribution` call returned, forwarded verbatim: the round kind, the deliverables in scope with their attribution source, the per-deliverable file set, the base ref and the unrequested-change candidates. The author does NOT re-run attribution. |
| `verdict_file` | Yes | Absolute path of the verdict file the author writes (Step 1 resolves it). On a delta round the file still holds the previous round's verdict, which the author reads before overwriting it. |

Skills the caller forwards in `skills[]`: `plan-marshall:persona-plan-marshall-agent`.

## Step 1: Resolve the round's scope (inline)

Resolve which deliverables this round covers:

```bash
python3 .plan/execute-script.py plan-marshall:phase-6-finalize:review_support attribution \
  --plan-id {plan_id} --delta-step functional-review
```

Branch on the returned TOON:

- **`status: error`** — the outline, the change ledger or the step record could not be read. Nothing can be evaluated: go to **Step 6 Branch C** with the returned `error` as the reason.
- **`unrequested_candidates` absent** (`footprint_source: unresolved`) — the realized footprint could not be derived, so the unrequested-change audit cannot run. Go to **Step 6 Branch C** with reason `footprint_unresolved`. An absent candidate list is never read as an empty one.
- **`status: success`** — capture the whole TOON as `{attribution_toon}`, and `round_kind`, `deliverable_count` and `base_ref` from it.

Resolve the two file paths the round uses:

```bash
python3 .plan/execute-script.py plan-marshall:manage-files:manage-files mkdir \
  --plan-id {plan_id} --dir work
```

```bash
python3 .plan/execute-script.py plan-marshall:manage-files:manage-files exists \
  --plan-id {plan_id} --file work/functional-review-verdict.json
```

```bash
python3 .plan/execute-script.py plan-marshall:manage-files:manage-files exists \
  --plan-id {plan_id} --file work/functional-review-verifier.json
```

Capture each returned `path` as `{verdict_file}` and `{verifier_file}`, and the first call's `exists` as `{verdict_exists}`. These two files are the only `.plan/` files this step reads or writes directly; every other plan input is read through a `manage-*` verb.

**A delta round needs the previous verdict.** On `round_kind: delta` the author carries forward the rows of the deliverables outside the delta, so it needs the previous round's verdict file. When `{verdict_exists}` is `false` on a delta round, re-run the attribution call above WITHOUT `--delta-step` and use that full-round TOON instead.

**Record an operator-closed head before anything else.** Read this step's previous record:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status read \
  --plan-id {plan_id}
```

Locate `metadata.phase_steps.6-finalize.functional-review`. When its `facts.may_close` is `operator_override`, the operator closed the review past its round cap at that record's `head_at_completion` (see [`review-rubric.md`](../standards/review-rubric.md) § 8). Add that head to the plan's list of override-closed heads — the call is idempotent, so a head already on the list is not added twice:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status metadata \
  --plan-id {plan_id} --set --append --field functional_review_override_heads \
  --value {head_at_completion}
```

Then read the list back and capture it comma-joined as `{override_heads}` (empty when the field is absent):

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status metadata \
  --plan-id {plan_id} --get --field functional_review_override_heads
```

The list lives in the plan's status metadata rather than only on the step record because `manage-status loop-back close` writes a fresh record at each override, so a head recorded only there would be lost at the next one.

## Step 2: Choose where the author runs (inline)

The author runs inline when the round covers at most 3 deliverables (`deliverable_count <= 3`) and in a dispatched envelope otherwise. The gate is a cost optimization only: both arrangements write the same verdict file in the same schema, and Steps 4-6 do not know which one produced it. Log the decision, quoting the text per [§ Shell-safe free text](#shell-safe-free-text-in-command-templates):

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id {plan_id} --level INFO \
  --message '(plan-marshall:phase-6-finalize:functional-review) Author {INLINE|DISPATCH} — round_kind={round_kind}, deliverables in scope={deliverable_count}'
```

**Inline**: run Step 3 in the dispatcher context, then continue with Step 4.

**Dispatch**: resolve the target through the role resolver. The `--workflow` value is this step's registry entry — the `default:functional-review` row of the [`../SKILL.md`](../SKILL.md) § "Built-in Step Dispatch Table", whose document is `workflow/functional-review.md` — written as its notation. Quote it from there; never compose a notation by hand:

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  effort resolve-target --phase phase-6-finalize \
  --workflow plan-marshall:phase-6-finalize/workflow/functional-review.md \
  --plan-id {plan_id} --caller plan-marshall:phase-6-finalize
```

The resolve carries the dispatch context, so it emits the `[DISPATCH]` work-log line and its paired decision-log record itself (see [`dispatch-logging.md`](../../ref-workflow-architecture/standards/dispatch-logging.md) § Emission contract). Do NOT hand-write a `[DISPATCH]` line. Extract `target` and dispatch:

```text
Task: plan-marshall:{target}
  prompt: |
    name: functional-review-author
    plan_id: {plan_id}
    skills: [plan-marshall:persona-plan-marshall-agent]
    workflow: plan-marshall:phase-6-finalize/workflow/functional-review.md
    attribution: |
      {attribution_toon}
    verdict_file: {verdict_file}
    WORKTREE: {worktree_path}
```

**A dispatched author executes Step 3 ONLY.** Loaded with `attribution` and `verdict_file` in its prompt body, this document's Step 3 is the whole of its task: it does not run Steps 1, 2, 4, 5 or 6, issues no dispatch, records no step outcome, and files no finding. It returns the § "Author return" TOON once the verdict file is written.

On an author return of `status: error`, or no parseable return, go to **Step 6 Branch C** with reason `author_failed`.

## Step 3: Author the verdict

The author reads the inputs, grades every deliverable in scope, runs the two audits, and writes the verdict file.

### 3a. Read the inputs

Read the plan's record of what it was asked to do and what it reports having done. Every input comes through a `manage-*` verb or git:

```bash
python3 .plan/execute-script.py plan-marshall:manage-plan-documents:manage-plan-documents \
  request read --plan-id {plan_id} --section clarified_request
```

```bash
python3 .plan/execute-script.py plan-marshall:manage-solution-outline:manage-solution-outline \
  read --plan-id {plan_id}
```

The outline carries, per deliverable, its success criteria, its affected files and its change notes, and it carries the plan's out-of-scope statements — a change the outline puts out of scope is an unrequested change even when a deliverable's file set reaches it.

The task records carry each task's description, steps, verification commands and the outcome each one recorded. List every task of a deliverable in scope, then read each one:

```bash
python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks list \
  --plan-id {plan_id} --deliverable {number} --status all
```

```bash
python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks read \
  --plan-id {plan_id} --task-number {task_number}
```

The recorded verification runs — the evidence form a criterion may cite — are the execution log of the plan's manifest:

```bash
python3 .plan/execute-script.py plan-marshall:manage-execution-manifest:manage-execution-manifest \
  read --plan-id {plan_id}
```

The realized footprint — every file the change touches:

```bash
python3 .plan/execute-script.py plan-marshall:manage-references:manage-references compute-footprint \
  --plan-id {plan_id} --worktree-path {worktree_path}
```

The decision log and the commit messages are where the plan reports its own work:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  read --plan-id {plan_id} --type decision
```

```bash
git -C {worktree_path} log {base_ref}..HEAD
```

The change itself, per file in a deliverable's file set (the `files` rows of `{attribution_toon}`):

```bash
git -C {worktree_path} diff {base_ref}...HEAD -- {path}
```

Read the change as whole files and whole functions, not as hunks: open every changed file with the `Read` tool and read the function or section around each hunk in full. A criterion is judged against what the file now says, not against what the diff added.

### 3b. Grade every deliverable in scope

For each deliverable in the `deliverables` rows of `{attribution_toon}`, write one verdict row:

- Grade the deliverable `met`, `met_with_residuals`, `not_met` or `superseded` by [`review-rubric.md`](../standards/review-rubric.md) § 2.
- Write one criterion entry per success criterion, in the outline's order. A criterion is `met` only with evidence in a form [`review-rubric.md`](../standards/review-rubric.md) § 4 lists. The plan's own report that it met a criterion is the thing being checked, so it is never the evidence.
- On `met_with_residuals`, name every residual and say whether it is part of what the deliverable was asked to deliver (`consequential`).
- On `superseded`, cite the operator decision or the refutation in `superseded_by`.
- Give every blocking item a `fix_kind` — `implementation` when the fix needs work the change does not contain yet, `correction` when it is an amendment to the diff in hand ([`review-rubric.md`](../standards/review-rubric.md) § 6).

**On a delta round**, grade only the deliverables in scope and copy every other deliverable's row verbatim from the previous verdict in `{verdict_file}`. A row is carried forward only because no file it declares or is attributed changed since the round that wrote it.

### 3c. Audit for unrequested changes

Every path in `unrequested_candidates` is a file the change touches that no deliverable declares or is attributed. Write exactly one `unrequested_changes` entry per candidate: read its diff, say why it changed in `reason`, and grade it by consequence (`consequential`) as [`review-rubric.md`](../standards/review-rubric.md) § 2 states. On a delta round the candidates are narrowed to the changed paths; copy every previous entry for a path outside them.

### 3d. Audit the plan's self-reports

Collect the claims the plan makes about its own work — the task closing notes and step outcomes, the commit messages, the decision-log entries, and every changed document line that states what the code does. Write one `self_reports` entry per claim checked: its `source`, the `claim`, whether it `holds` against the change, and — for a claim that does not hold — whether a reader would act on it (`reader_acts_on`). A claim that holds is listed and graded nothing. A claim stale against a later commit is a claim that does not hold.

### 3e. Write the verdict file

Write the verdict with the `Write` tool to `{verdict_file}`, as JSON in the § "Verdict schema" below, listing in `files_read` every file this round read. Then return the § "Author return".

## Verdict schema

The verdict file is the schema `review_support validate --kind functional` checks — the schema documented in `scripts/review_support.py`, restated here because the author writes it:

```json
{
  "deliverables": [
    {
      "number": 1,
      "verdict": "met | met_with_residuals | not_met | superseded",
      "criteria": [
        {
          "criterion": "the success-criterion text",
          "status": "met | unevidenced | not_met",
          "evidence": ["path/to/file.py:42", "test/module/test_file.py::test_name"],
          "fix_kind": "implementation | correction"
        }
      ],
      "residuals": [
        {"description": "what is missing", "consequential": true, "fix_kind": "implementation | correction"}
      ],
      "superseded_by": "the operator decision or refutation",
      "fix_kind": "implementation | correction"
    }
  ],
  "unrequested_changes": [
    {"path": "path/to/file", "consequential": false, "reason": "why it changed", "fix_kind": "implementation | correction"}
  ],
  "self_reports": [
    {"source": "TASK-3 closing note", "claim": "the claim", "holds": false, "reader_acts_on": true, "fix_kind": "implementation | correction"}
  ],
  "files_read": ["path/to/file.py"]
}
```

`deliverables` carries exactly one row per outline deliverable. `residuals` belongs on a `met_with_residuals` row and `superseded_by` on a `superseded` row. `fix_kind` is required on every item that grades `blocking`; a `not_met` deliverable and an `unevidenced` criterion default to `implementation` when it is omitted.

## Author return

```toon
status: success | error
verdict_file: {verdict_file}
message: "<what went wrong — present only on error>"
```

## Step 4: Validate the verdict (inline)

```bash
python3 .plan/execute-script.py plan-marshall:phase-6-finalize:review_support validate \
  --plan-id {plan_id} --kind functional --verdict-file {verdict_file}
```

Branch on the returned TOON:

- **`status: error`** — the verdict file or the outline could not be read. Go to **Step 6 Branch C** with the returned `error` as the reason.
- **`valid: false`** — the verdict breaks the schema. Repair it ONCE, in the inline context: read the returned `errors[]`, re-read through the Step 3a verbs whatever input an error concerns, correct the verdict file with the `Write` tool so it answers each error, and validate again. The repair is author work, so the verifier of Step 5 is still a separate dispatch. A verdict still invalid after that one repair goes to **Step 6 Branch C** with reason `verdict_invalid` and the first error.
- **`valid: true`** — capture `findings`, `facts` and `loop_back_target`. Every `rewrites[]` entry is a criterion the author called `met` without evidence; log it, because the grading changed under the author (quoted per [§ Shell-safe free text](#shell-safe-free-text-in-command-templates)):

  ```bash
  python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
    decision --plan-id {plan_id} --level INFO \
    --message '(plan-marshall:phase-6-finalize:functional-review) Criterion D{deliverable}.C{criterion} claimed met without evidence — graded unevidenced'
  ```

**A clean delta round is followed by the closing round.** When `round_kind` is `delta` and `facts.blocking_count` is `0`, the round does not close on its own evidence — [`review-rubric.md`](../standards/review-rubric.md) § 8. Run the closing round in this same firing: repeat Step 1's attribution call WITHOUT `--delta-step`, then Steps 2, 3 and 4 over every deliverable, and continue to Step 5 with the closing round's result. A delta round WITH a blocking finding needs no closing round; it continues to Step 5 as it is.

## Step 5: Verifier (dispatch from the inline context)

The verifier fires on every round that reached this point, on both author arrangements. Resolve the target exactly as Step 2 does — the resolve emits this firing's own `[DISPATCH]` record:

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  effort resolve-target --phase phase-6-finalize \
  --workflow plan-marshall:phase-6-finalize/workflow/functional-review.md \
  --plan-id {plan_id} --caller plan-marshall:phase-6-finalize
```

The verifier carries `instructions`, not `workflow`: its task is the adjudication written below, and it reads only the verdict file and the evidence that file cites.

```text
Task: plan-marshall:{target}
  prompt: |
    name: functional-review-verifier
    plan_id: {plan_id}
    skills: []
    instructions: |
      You are the VERIFIER for one round of the functional review. You did not
      author the verdict and must not re-author it: file no finding, edit no file,
      and grade no deliverable the author did not grade.

      The author's verdict is the JSON file {verdict_file}. Read it with the Read
      tool. The validator graded it as follows:

        round_kind: {round_kind}
        blocking: {blocking_count}
        advisory: {advisory_count}
        findings: {findings_rendered}

      Decide TWO questions, in this order.

      (1) IS THE GRADING SUPPORTED BY THE CITED EVIDENCE?
      For each criterion graded met, open the evidence it cites and check that the
      evidence shows the criterion holds. For each deliverable, unrequested change
      and self-report, check that its verdict follows from what the change says.
      Answer false when any grading is not supported, and name it in reason.

      (2) MAY THE ROUND CLOSE?
      Answer true only when no blocking finding remains, the round_kind is full,
      and your answer to (1) is true. Answer false otherwise and name which of the
      three decided it.

      Return exactly this TOON and nothing else:

        status: success
        grading_supported: true | false
        may_close: true | false
        reason: "<one line, <=200 chars, naming what you checked and what decided it>"
    WORKTREE: {worktree_path}
```

`{findings_rendered}` is one line per `findings` entry of the Step 4 return, carrying its `ref`, `kind`, `severity`, `fix_kind` and `title`.

On a parseable return, write the two answers and the reason with the `Write` tool to `{verifier_file}` as JSON:

```json
{"grading_supported": true, "may_close": true, "reason": "the verifier's reason"}
```

On a failed dispatch or an unparseable return, write nothing to `{verifier_file}` and continue — the validator then reads the verifier as absent, which closes nothing. Then validate again with the verifier's answer:

```bash
python3 .plan/execute-script.py plan-marshall:phase-6-finalize:review_support validate \
  --plan-id {plan_id} --kind functional --verdict-file {verdict_file} --verifier-file {verifier_file}
```

On a dispatch that wrote nothing, omit `--verifier-file`. Capture `verifier` (`accepted` / `declined` / `absent` / `malformed`), `may_close`, `loop_back_target`, `findings` and `facts` from this return — they are the round's final answer. `accepted` follows the verifier's first answer: it confirmed the grading. On a round with a blocking finding its `may_close: false` is the answer question (2) requires, so the round still reads `accepted`; `declined` means the verifier rejected the grading, or refused closure on a round without a blocking finding. Log the verifier's answer on the decision log before Step 6 branches — `{reason}` is the verifier's own free text, quoted per [§ Shell-safe free text](#shell-safe-free-text-in-command-templates):

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id {plan_id} --level INFO \
  --message '(plan-marshall:phase-6-finalize:functional-review) Verifier {verifier}; may_close={may_close} — {reason}'
```

## Step 6: Record the outcome (inline)

Every branch resolves the worktree HEAD immediately before its `mark-step-done` call:

```bash
git -C {worktree_path} rev-parse HEAD
```

Capture the full SHA as `{sha}`.

Every branch with a non-empty `{override_heads}` forwards `--fact override_closed_heads={override_heads}`, so a retrospective can name every head that shipped past the round cap without a review. A branch with an empty list omits the fact.

| Validator `may_close` | Final round | Branch |
|-----------------------|-------------|--------|
| `true` | full | A — the round closes |
| `false` | any | B — the round loops back |

`may_close: true` already requires a valid verdict with no blocking finding and an accepted verifier, and Step 4 never lets a clean delta round reach this point, so the final round of a closing firing is always a full one.

### Branch A — the round closes

Resolve the findings earlier rounds of this review filed, which this round's verdict no longer holds as blocking — first the blocking findings, then the state findings, each `--detail` quoted per [§ Shell-safe free text](#shell-safe-free-text-in-command-templates):

```bash
python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings qgate resolve-by-rule \
  --plan-id {plan_id} --phase 6-finalize --rule functional-review \
  --resolution taken_into_account \
  --detail 'functional review closed at {sha}: the verifier accepted a verdict with no blocking finding'
```

```bash
python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings qgate resolve-by-rule \
  --plan-id {plan_id} --phase 6-finalize --rule functional-review-state \
  --resolution taken_into_account \
  --detail 'functional review closed at {sha}: the verifier accepted the verdict and answered may_close=true'
```

On a non-`success` return from either call, do NOT record `done`: surface the returned error and halt.

Advisory findings are not filed — a pending finding blocks the merge — and reach the reader through the step's facts and the decision log, one line each — `{title}` is the review's free text, quoted per [§ Shell-safe free text](#shell-safe-free-text-in-command-templates):

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id {plan_id} --level INFO \
  --message '(plan-marshall:phase-6-finalize:functional-review) Advisory {kind} at {ref} — {title}'
```

On a non-`success` return from any advisory line — a `status: error` TOON or a non-zero exit — do NOT record `done`: surface the returned error and halt. The decision log is the only place an advisory reaches the reader, so a close recorded over a line that was not written would drop the advisory without trace.

Then record the close, with `--display-detail` quoted per [§ Shell-safe free text](#shell-safe-free-text-in-command-templates):

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize --step default:functional-review --outcome done \
  --display-detail 'functional review clean: {deliverables_reviewed} deliverables, {advisory_count} advisory' \
  --fact acceptance={verifier} --fact may_close=true --fact work_performed=true \
  --fact round_kind={round_kind} \
  --fact deliverables_reviewed={deliverables_reviewed} --fact criteria_checked={criteria_checked} \
  --fact files_read={files_read} --fact deliverables_met={deliverables_met} \
  --fact deliverables_met_with_residuals={deliverables_met_with_residuals} \
  --fact deliverables_not_met={deliverables_not_met} --fact deliverables_superseded={deliverables_superseded} \
  --fact criteria_unevidenced={criteria_unevidenced} --fact unrequested_changes={unrequested_changes} \
  --fact false_self_reports={false_self_reports} \
  --fact blocking_count={blocking_count} --fact advisory_count={advisory_count} \
  --fact override_closed_heads={override_heads} \
  --head-at-completion {sha}
```

Every `{…}` count is the value of the same-named key in the Step 5 validator `facts`. The `--fact override_closed_heads` line is conditional: include it only when `{override_heads}` is non-empty, and drop it otherwise.

### Branch B — the round loops back

The round does not close. File the blocking findings before the outcome is recorded.

**On a full round**, first resolve the blocking findings earlier rounds filed — this round re-examined every deliverable, so its blocking set is the whole of what still blocks, and a finding it still holds is re-filed below as pending (`--detail` quoted per [§ Shell-safe free text](#shell-safe-free-text-in-command-templates)):

```bash
python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings qgate resolve-by-rule \
  --plan-id {plan_id} --phase 6-finalize --rule functional-review \
  --resolution taken_into_account \
  --detail 'superseded by the functional review round at {sha}'
```

A delta round resolves nothing: it examined only part of the change, so a finding outside its scope still stands.

File every `findings` entry whose `severity` is `blocking`, one call each — `{ref}` and `{title}` are the review's free text, so `--title` and `--detail` are quoted per [§ Shell-safe free text](#shell-safe-free-text-in-command-templates):

```bash
python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings qgate add \
  --plan-id {plan_id} --phase 6-finalize --source qgate --type bug \
  --title '{kind} at {ref}' --detail '{title} [fix_kind {fix_kind}]' \
  --rule functional-review --component plan-marshall:phase-6-finalize --severity error
```

Advisory findings are not filed — a pending finding blocks the merge — and reach the reader through the step's facts and the decision log, one line each, quoted per [§ Shell-safe free text](#shell-safe-free-text-in-command-templates):

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id {plan_id} --level INFO \
  --message '(plan-marshall:phase-6-finalize:functional-review) Advisory {kind} at {ref} — {title}'
```

On a non-`success` return from any advisory line — a `status: error` TOON or a non-zero exit — do NOT record the loop-back: surface the returned error and halt. The decision log is the only place an advisory reaches the reader, so a loop-back recorded over a line that was not written would drop the advisory without trace.

**When the verifier did not accept**, also file one state finding naming which situation it was — `verdict_refused` (`verifier: declined`), `verifier_unavailable` (`verifier: absent` or `malformed`). The fixed rule key is what lets the closing round, or an operator close, resolve it. `{reason}` is the verifier's free text, quoted per [§ Shell-safe free text](#shell-safe-free-text-in-command-templates):

```bash
python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings qgate add \
  --plan-id {plan_id} --phase 6-finalize --source qgate --type bug \
  --title '{state} at functional-review' --detail '{reason}' \
  --rule functional-review-state --component plan-marshall:phase-6-finalize --severity warning
```

On a non-`success` return from any `qgate add`, do NOT record the loop-back: surface the returned error and halt — a loop-back whose findings are not in the store points the next round at nothing.

**Select the target.** The target is the validator's `loop_back_target` when it is `5-execute` or `6-finalize`. A round with no blocking finding that loops back only because the verifier did not accept has `loop_back_target: none`; its target is `6-finalize` — the next round is a re-review of the diff in hand.

**On target `5-execute`**, every blocking finding with `fix_kind: implementation` becomes one fix task. Allocate each through the two-step add:

```bash
python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks prepare-add \
  --plan-id {plan_id}
```

Write the fix task's definition to the returned path with the `Write` tool, in the task-definition format `manage-tasks` documents for `prepare-add`: a title naming the finding's `ref`, a description carrying its `title` and the deliverable it belongs to, and that deliverable's number. Then commit it:

```bash
python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks commit-add \
  --plan-id {plan_id}
```

The correction findings ride along with the fix tasks ([`review-rubric.md`](../standards/review-rubric.md) § 6). Then move the plan back to execute BEFORE the outcome is recorded:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status set-phase \
  --plan-id {plan_id} --phase 5-execute
```

On target `6-finalize`, make no `set-phase` call — the dispatcher replays this step inline.

Record the loop-back. `{acceptance}` is the validator's `verifier` value, and `--display-detail` is quoted per [§ Shell-safe free text](#shell-safe-free-text-in-command-templates):

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize --step default:functional-review --outcome loop_back \
  --loop-back-target {target} \
  --display-detail '{verdict}' \
  --fact acceptance={acceptance} --fact may_close=false --fact work_performed=true \
  --fact round_kind={round_kind} \
  --fact deliverables_reviewed={deliverables_reviewed} --fact criteria_checked={criteria_checked} \
  --fact files_read={files_read} --fact deliverables_met={deliverables_met} \
  --fact deliverables_met_with_residuals={deliverables_met_with_residuals} \
  --fact deliverables_not_met={deliverables_not_met} --fact deliverables_superseded={deliverables_superseded} \
  --fact criteria_unevidenced={criteria_unevidenced} --fact unrequested_changes={unrequested_changes} \
  --fact false_self_reports={false_self_reports} \
  --fact blocking_count={blocking_count} --fact advisory_count={advisory_count} \
  --fact override_closed_heads={override_heads} \
  --head-at-completion {sha}
```

The `--fact override_closed_heads` line is conditional here as well: include it only when `{override_heads}` is non-empty.

`{verdict}` is `functional review found {blocking_count} blocking over {deliverables_reviewed} deliverables, {advisory_count} advisory` when the round has a blocking finding, and `functional review not closed: verifier {verifier}` when it has none.

A loop-back is a productive non-completion, not a failure: the round examined the change and handed back work for the next round. It is never recorded `failed`.

### Branch C — the review could not run

Reached when an input could not be read, the author failed, or the verdict stayed invalid after its one repair. Nothing was evaluated, so the step records the **not-run** state of [`review-rubric.md`](../standards/review-rubric.md) § 11 — never a clean verdict — with `work_performed=false`.

The outcome is `loop_back` to `6-finalize`, and the choice is load-bearing. A `done` would close a review that never ran. A `failed` leaf record does not stop the dispatcher's step loop, so `push` would run next and ship the change unreviewed. `loop_back` is the outcome that stops the loop advancing past this step and re-fires it on the next entry, bounded by this step's round budget — so an input that stays unreadable halts the run for the operator rather than letting the push through.

File the not-run state first, so the store carries it and an operator close resolves it with the other state findings. `{reason}` may be a script's error text, so `--detail` here and `--display-detail` below are quoted per [§ Shell-safe free text](#shell-safe-free-text-in-command-templates):

```bash
python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings qgate add \
  --plan-id {plan_id} --phase 6-finalize --source qgate --type bug \
  --title 'not_run at functional-review' --detail '{reason}' \
  --rule functional-review-state --component plan-marshall:phase-6-finalize --severity warning
```

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize --step default:functional-review --outcome loop_back \
  --loop-back-target 6-finalize \
  --display-detail 'functional review not run: {reason}' \
  --fact work_performed=false \
  --head-at-completion {sha}
```

When `rev-parse` itself failed, omit `--head-at-completion` rather than forwarding an unresolved value, and append `; HEAD unresolvable` to the detail.

## Operator override and the rounds that follow it

When this step's round budget is spent, the operator either grants another round or closes the review with `manage-status loop-back close --step functional-review`, which records `may_close=operator_override` at the head the operator judged and resolves this step's `functional-review-state` findings. The override closes ONLY that head ([`review-rubric.md`](../standards/review-rubric.md) § 8):

- A later fix commit advances HEAD past the override-closed record, so the dispatcher's HEAD-dependency check re-fires this step, and `attribution` scopes the firing as a delta round over the files the commit touched. The re-fire comes from the HEAD advance, not from a loop-back admission, so it spends no round from this step's budget.
- Step 1 adds every override-closed head to `functional_review_override_heads`, and every later record carries the list as `override_closed_heads`.

## Round-loop termination

The step's record holds exactly one of four things, and they are different records:

- **Closed** — Branch A: a full round with no blocking finding that the verifier accepted (`may_close=true`).
- **Looped back** — Branch B: the round found work for the next round, or the verifier did not accept (`may_close=false`, `work_performed=true`).
- **Not run** — Branch C: nothing was evaluated (`work_performed=false`, outcome `loop_back`), so the run cannot advance to the push until the review runs.
- **Closed by the operator** — `manage-status loop-back close`, recorded with `may_close=operator_override`. This is not a closed review and is never reported as one.
