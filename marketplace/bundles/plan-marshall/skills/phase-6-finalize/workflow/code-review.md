---
lane:
  class: adversarial
  cost_size: L
name: default:code-review
description: Code review before push — judges whether the changed code is well made against the review rules of the domains it touches, the code-review spine and the project's own conventions; every finding cites a rule, a location and a failure scenario, and a blocking finding loops back to execute or finalize
order: 7
mutates_source: false
head_dependent: true
default_on: true
presets: []
records_facts:
  - acceptance
  - may_close
  - work_performed
  - round_kind
  - domains_reviewed
  - files_read
  - blocking_count
  - advisory_count
  - rules_cited
  - override_closed_heads
requires_prompt_fields:
  - scope
  - rule_sources
  - findings_file
implements:
  - plan-marshall:extension-api/standards/ext-point-execution-context-workflow
  - plan-marshall:extension-api/standards/ext-point-finalize-step
---

# Code Review

The `code-review` finalize step answers one question about the plan's change before it is pushed: **is the change well made?** It reads every changed file whole and judges it against the review rules of the domains the change touches, the cross-cutting code-review spine, and the project's own conventions. Every finding names the rule it breaks, the place it breaks it, and the input or state under which it goes wrong.

How a finding is graded, which citation forms a finding may use, where a blocking finding loops back to, what the verifier answers, and when a round may close are stated once, in [`../standards/review-rubric.md`](../standards/review-rubric.md). This document states what the step reads, in what order, and how it records the outcome; for grading, citation forms, loop-back targets, the verifier questions and the delta-then-closing-round rule it cites the rubric section rather than restating it.

The procedure is the same for every language and build system. What differs between two changes in two languages is the rulebook the step loads — derived from the domains each change touches — never the steps it follows.

**Not to be confused with** `plan-marshall:recipe-code-review`, a recipe that reviews a whole codebase outside any plan and is not a finalize step, nor with `plan-marshall:persona-code-reviewer`, the work identity this step's author loads. Finalize-step discovery reads only `ext-point-finalize-step` implementors, so the step id `default:code-review` collides with neither.

## Exit-code convention for every script call

The exit-code contract for every `python3 .plan/execute-script.py` call in this document — of EVERY notation, not only `manage-*` — is stated once in [`tools-script-executor/standards/exit-code-convention.md`](../../tools-script-executor/standards/exit-code-convention.md); it is not restated here.

## Shell-safe free text in command templates

Several command templates below interpolate free text into a shell argument — a finding's title and ref, a verifier's reason, a rendered verdict line. The review writes that text, not this document, and it routinely carries backticks, `$` and quotes. Every `manage-logging` `--message`, every `manage-findings` `--title` and `--detail`, and every `manage-status mark-step-done` `--display-detail` in this document is therefore written as ONE single-quoted shell argument, and the text is substituted into it by these rules:

1. **Single-quote the argument**: `--message '… {title}'`. Between single quotes the shell expands nothing — no backtick command, no `$(…)`, no `$VAR` — so the text reaches the verb byte for byte.
2. **Escape each embedded single quote as `'\''`** before substituting the value: close the quoted run, add an escaped quote, reopen the run. A title `don't` is substituted as `don'\''t`.
3. **Never put interpolated text in double quotes.** Inside double quotes the shell still runs a backtick or `$(…)` substitution and expands `$VAR`, and an embedded double quote ends the argument early, so a rendered command can run a substitution or break before the decision-log line or the finding is recorded.

None of the verbs these templates call — `manage-logging decision`, `manage-findings qgate add` and `qgate resolve-by-rule`, `manage-status mark-step-done` — takes the text from a file (each verb's `--help` lists the text only as an argument), so the single-quoted argument is the one safe form, and every template below uses it. Each template that interpolates text names this section.

## Activation

This document carries no activation logic. The manifest composer decides whether the step runs (see [`../../manage-execution-manifest/standards/decision-rules.md`](../../manage-execution-manifest/standards/decision-rules.md)): the `commit_push_disabled` pre-filter drops it when the run will not push, the `scope_gated_finalize` pre-filter drops it on a surgical scope unless the step carries a declared lane, and the `code_review` ceremony gate — this step's own `lane` — forces it out (`off`) or in (`minimal`) independently of every other review. When the dispatcher reaches the step, the step runs to one of the terminal branches of Step 6.

## Who does what

The step is **orchestrator-owned**: the phase-6-finalize dispatcher runs it in its own inline context, never as a dispatched leaf, because the step issues dispatches of its own and a dispatched leaf cannot (see [`../../ref-workflow-architecture/standards/agents.md`](../../ref-workflow-architecture/standards/agents.md)).

| Role | What it does | Where it runs |
|------|--------------|---------------|
| **Dispatcher context** | Resolves the round's scope and rulebook (Step 1), chooses where the author runs (Step 2), validates the findings (Step 4), dispatches the verifier (Step 5) and records the outcome (Step 6). | The inline phase-6-finalize context. |
| **Author** | Loads the rulebook, reads the change and the project's conventions, and writes the findings file (Step 3). Works under the `plan-marshall:persona-code-reviewer` identity. | A dispatched envelope, or the inline context when the Step 2 gate keeps it inline. |
| **Verifier** | Answers the two questions of [`review-rubric.md`](../standards/review-rubric.md) § 7 about the author's findings. Files no finding and edits no file. | Always a separate dispatch, issued from the inline context — on both author arrangements. |

**The author records nothing.** Its brief ends when the findings file is written and its return names the file. The step outcome is recorded by the inline dispatcher context in Step 6, AFTER the verifier of Step 5 has answered — the party that wrote the findings never records the round, and no outcome exists before the verifier has spoken.

When the author runs inline, the dispatcher context is itself the author, so the verifier MUST still be the Step 5 dispatch: running it inline would put author and verifier in one party.

## HEAD-dependency

The step declares `head_dependent: true`. Its findings are a reading of the plan's diff, so a later commit produces a diff this step never examined. Capture `git -C {worktree_path} rev-parse HEAD` immediately before EVERY terminal `mark-step-done` call of Step 6 and forward it as `--head-at-completion {sha}`. The only branch that may omit it is Branch C, and only when the `rev-parse` itself fails.

The recorded SHA is also what the next firing's delta round is measured from: `review_support attribution --delta-step code-review` reads this step's own record to decide between a full and a delta round.

**Verdict-input surface — deliberately undeclared.** The step declares no `verdict_inputs`. Its inputs are every file the change touches — derived at run time from the plan's own footprint — plus the rulebook of the domains that footprint touches and the project's convention files. That is the discovered-input shape [`../standards/verdict-currency.md`](../standards/verdict-currency.md) § "The classification" names as having no sound static subset, so the step keeps the unconditional re-fire on every HEAD advance.

## Inputs of the dispatched author

| Prompt-body field | Required | Description |
|-------------------|:--------:|-------------|
| `plan_id` | Yes | Plan identifier. |
| `WORKTREE` | Yes | Working-directory path of the plan's worktree. |
| `scope` | Yes | The round's scope the dispatcher's Step 1 composed, forwarded verbatim: `round_kind`, `base_ref` and the `files` this round reviews. The author does NOT re-derive it. |
| `rule_sources` | Yes | The rulebook the dispatcher's Step 1 resolved, forwarded verbatim: the reviewed `domains` and the `skills` whose `## Review Rules` the author loads. The author does NOT re-resolve it. |
| `findings_file` | Yes | Absolute path of the findings file the author writes (Step 1 resolves it). On a delta round the file still holds the previous round's findings, which the author reads before overwriting it. |

Skills the caller forwards in `skills[]`: `plan-marshall:persona-plan-marshall-agent`, `plan-marshall:persona-code-reviewer`.

## Step 1: Resolve the round's scope and rulebook (inline)

### 1a. The files this round reviews

Resolve the round kind and the per-deliverable file sets:

```bash
python3 .plan/execute-script.py plan-marshall:phase-6-finalize:review_support attribution \
  --plan-id {plan_id} --delta-step code-review
```

Branch on the returned TOON:

- **`status: error`** — the outline, the change ledger or the step record could not be read. Nothing can be reviewed: go to **Step 6 Branch C** with the returned `error` as the reason.
- **`unrequested_candidates` absent** (`footprint_source: unresolved`) — the realized footprint could not be derived, so the change cannot be read whole. Go to **Step 6 Branch C** with reason `footprint_unresolved`. An absent candidate list is never read as an empty one.
- **`status: success`** — capture `round_kind`, `base_ref`, the `files` rows and `unrequested_candidates`.

Resolve the realized footprint — every file the change touches:

```bash
python3 .plan/execute-script.py plan-marshall:manage-references:manage-references compute-footprint \
  --plan-id {plan_id} --worktree-path {worktree_path}
```

On a non-`success` return go to **Step 6 Branch C** with reason `footprint_unresolved`. The files this round reviews are:

- **On `round_kind: full`** — every path of the realized footprint. Nothing pre-selects candidate lines or files: the change is read whole.
- **On `round_kind: delta`** — the realized-footprint paths that appear in a `files` row of a deliverable in scope or in `unrequested_candidates`, which `attribution` has already narrowed to the deliverables and files the fix touched ([`review-rubric.md`](../standards/review-rubric.md) § 8).

Compose `{scope_toon}` from these values and capture `{file_count}` as the number of files:

```toon
round_kind: {round_kind}
base_ref: {base_ref}
files[{file_count}]:
  - {path}
```

### 1b. The rulebook this round applies

Resolve the domains the change touches — the plan's declared domains united with every configured domain whose file patterns match the footprint:

```bash
python3 .plan/execute-script.py plan-marshall:phase-6-finalize:review_support domains \
  --plan-id {plan_id}
```

On `status: error` go to **Step 6 Branch C** with reason `rulebook_unresolved` — a review without its rulebook evaluates nothing ([`review-rubric.md`](../standards/review-rubric.md) § 11). That includes `error: footprint_unresolved`: the verb never answers with the declared domains alone when the footprint could not be derived, because that rulebook would omit every footprint-matched domain. Otherwise capture every `domain` value.

For each domain, read the standards skills the project configures for it:

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  get-skills-by-profile --domain {domain}
```

The domain's rule sources are the skill notations its `implementation`, `module_testing` and `quality` profiles name, in that order, each listed once. The domain's `core` skills are among them: `get-skills-by-profile` merges them into every profile it returns, so this step reads the same four profiles the cuioss-review-bot pack generator harvests (`core`, `implementation`, `module_testing`, `quality`). Two kinds of skill are excluded by construction, because the security review owns them and no security rule belongs in a code review:

- every skill whose name ends in `-security`;
- `plan-marshall:persona-security-expert`.

The `security` profile is not read at all. A domain whose lookup returns a non-`success` status goes to **Step 6 Branch C** with reason `rulebook_unresolved`. These are the same `## Review Rules` blocks the cuioss-review-bot pack generator harvests, so the in-run reviewer and the external bot read one rulebook ([`review-rubric.md`](../standards/review-rubric.md) § 10).

Compose `{rule_sources_toon}`: the reviewed domains, and every rule-source notation across them, each listed once, with `plan-marshall:ref-code-quality` — the code-review spine — always present:

```toon
domains[{domain_count}]:
  - {domain}
skills[{skill_count}]:
  - plan-marshall:ref-code-quality
  - {notation}
```

### 1c. The two files the round writes

```bash
python3 .plan/execute-script.py plan-marshall:manage-files:manage-files mkdir \
  --plan-id {plan_id} --dir work
```

```bash
python3 .plan/execute-script.py plan-marshall:manage-files:manage-files exists \
  --plan-id {plan_id} --file work/code-review-findings.json
```

```bash
python3 .plan/execute-script.py plan-marshall:manage-files:manage-files exists \
  --plan-id {plan_id} --file work/code-review-verifier.json
```

Capture each returned `path` as `{findings_file}` and `{verifier_file}`, and the first call's `exists` as `{findings_exist}`. These two files are the only `.plan/` files this step reads or writes directly; every other plan input is read through a `manage-*` verb.

**A delta round needs the previous findings.** On `round_kind: delta` the author carries forward the findings located outside the delta, so it needs the previous round's findings file. When `{findings_exist}` is `false` on a delta round, re-run the attribution call above WITHOUT `--delta-step` and compose the scope of a full round instead.

### 1d. Record an operator-closed head before anything else

Read this step's previous record:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status read \
  --plan-id {plan_id}
```

Locate `metadata.phase_steps.6-finalize.code-review`. When its `facts.may_close` is `operator_override`, the operator closed the review past its round cap at that record's `head_at_completion` (see [`review-rubric.md`](../standards/review-rubric.md) § 8). Add that head to the plan's list of override-closed heads — the call is idempotent, so a head already on the list is not added twice:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status metadata \
  --plan-id {plan_id} --set --append --field code_review_override_heads \
  --value {head_at_completion}
```

Then read the list back and capture it comma-joined as `{override_heads}` (empty when the field is absent):

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status metadata \
  --plan-id {plan_id} --get --field code_review_override_heads
```

The list lives in the plan's status metadata rather than only on the step record because `manage-status loop-back close` writes a fresh record at each override, so a head recorded only there would be lost at the next one.

## Step 2: Choose where the author runs (inline)

The author runs inline when the round reviews at most 5 files (`file_count <= 5`) and in a dispatched envelope otherwise. The gate is a cost optimization only: both arrangements write the same findings file in the same schema, and Steps 4-6 do not know which one produced it. Log the decision, quoting the text per [§ Shell-safe free text](#shell-safe-free-text-in-command-templates):

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id {plan_id} --level INFO \
  --message '(plan-marshall:phase-6-finalize:code-review) Author {INLINE|DISPATCH} — round_kind={round_kind}, files in scope={file_count}'
```

**Inline**: load the author's work identity, run Step 3 in the dispatcher context, then continue with Step 4:

```text
Skill: plan-marshall:persona-code-reviewer
```

**Dispatch**: resolve the target through the role resolver. The `--workflow` value is this step's registry entry — the `default:code-review` row of the [`../SKILL.md`](../SKILL.md) § "Built-in Step Dispatch Table", whose document is `workflow/code-review.md` — written as its notation. Quote it from there; never compose a notation by hand:

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  effort resolve-target --phase phase-6-finalize \
  --workflow plan-marshall:phase-6-finalize/workflow/code-review.md \
  --plan-id {plan_id} --caller plan-marshall:phase-6-finalize
```

The resolve carries the dispatch context, so it emits the `[DISPATCH]` work-log line and its paired decision-log record itself (see [`dispatch-logging.md`](../../ref-workflow-architecture/standards/dispatch-logging.md) § Emission contract). Do NOT hand-write a `[DISPATCH]` line. Extract `target` and dispatch:

```text
Task: plan-marshall:{target}
  prompt: |
    name: code-review-author
    plan_id: {plan_id}
    skills: [plan-marshall:persona-plan-marshall-agent, plan-marshall:persona-code-reviewer]
    workflow: plan-marshall:phase-6-finalize/workflow/code-review.md
    scope: |
      {scope_toon}
    rule_sources: |
      {rule_sources_toon}
    findings_file: {findings_file}
    WORKTREE: {worktree_path}
```

**A dispatched author executes Step 3 ONLY.** Loaded with `scope`, `rule_sources` and `findings_file` in its prompt body, this document's Step 3 is the whole of its task: it does not run Steps 1, 2, 4, 5 or 6, issues no dispatch, records no step outcome, and files no finding. It returns the § "Author return" TOON once the findings file is written.

On an author return of `status: error`, or no parseable return, go to **Step 6 Branch C** with reason `author_failed`.

## Step 3: Author the findings

The author loads the rulebook, reads the project's conventions and the change, judges the change, and writes the findings file.

### 3a. Load the rulebook

The rulebook is read from the standards skills installed for this project — the `skills` of `{rule_sources_toon}` — never from a copy held here. Load each skill in-context:

```text
Skill: {notation}
```

- From `plan-marshall:ref-code-quality`, the code-review spine: its `## Review Categories` (the cross-cutting categories) and its `## Review Rules` (the cross-cutting rules).
- From every other skill: its `## Review Rules`. A skill without the section contributes no rule.

The charter that governs which findings are reported is [`review-rubric.md`](../standards/review-rubric.md) § 9; read it with the rest of the rubric before judging anything.

A rule source that cannot be loaded leaves the rulebook incomplete, so the author returns `status: error` naming it rather than reviewing against part of the rulebook.

### 3b. Read the project's conventions

The project's own conventions are rules a finding may cite in the "project convention" form:

- **Convention files** — `CLAUDE.md` and `AGENTS.md` at the worktree root, read with the `Read` tool. A file that does not exist contributes nothing.
- **Decision records** — the ADRs that govern the touched code. Resolve the module owning each reviewed file, then scan the decision records affecting each distinct module and each touched skill directory:

  ```bash
  python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture \
    which-module --path {path}
  ```

  ```bash
  python3 .plan/execute-script.py plan-marshall:manage-adr:manage-adr scan --affects {module}
  ```

  Read each matched ADR whose summary bears on the change:

  ```bash
  python3 .plan/execute-script.py plan-marshall:manage-adr:manage-adr read --number {number}
  ```

- **Architecture hints** — the recorded responsibility, purpose and key packages of each touched module:

  ```bash
  python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture \
    module --module {module} --full
  ```

### 3c. Read the change whole

For every file in the `files` of `{scope_toon}`:

```bash
git -C {worktree_path} diff {base_ref}...HEAD -- {path}
```

Then open the file with the `Read` tool and read every changed function or section in full, together with what it calls and what calls it where that bears on a finding. A finding is judged against what the file now does, not against what the diff added. A file the change deletes is read through its diff alone.

### 3d. Judge the change

Report every finding the charter requires and no other. Each finding carries all three parts [`review-rubric.md`](../standards/review-rubric.md) § 3 requires — a rule cited in a § 5 form, a `file:line` location, and a failure scenario naming the input or state and what goes wrong — plus:

- `failure_class` — `wrong_result`, `lost_data`, `fail_open` or `broken_contract` when the failure scenario produces one of them, `none` otherwise. The class decides the grade ([`review-rubric.md`](../standards/review-rubric.md) § 3); the author never states a severity of its own.
- `fix_kind` — `implementation` when the fix needs work the change does not contain yet, `correction` when it is an amendment to the diff in hand ([`review-rubric.md`](../standards/review-rubric.md) § 6). Required on every finding whose `failure_class` is not `none`.
- `title` — one line naming the defect.

A suspicion that cannot name a rule, a location and a failure scenario is not a finding and is not reported.

**On a delta round**, judge only the files in scope and copy every previous finding whose location lies outside them verbatim from `{findings_file}`. A finding is carried forward only because no file it is located in changed since the round that wrote it.

### 3e. Write the findings file

Write the findings with the `Write` tool to `{findings_file}`, as JSON in the § "Findings schema" below, listing in `domains_reviewed` every domain of `{rule_sources_toon}` and in `files_read` every file this round read. Then return the § "Author return".

## Findings schema

The findings file is the schema `review_support validate --kind code` checks — the schema documented in `scripts/review_support.py`, restated here because the author writes it:

```json
{
  "findings": [
    {
      "rule": {"form": "pack_rule | spine_category | convention | adr", "ref": "the cited rule"},
      "location": "path/to/file.py:42",
      "failure_scenario": "the input or state that triggers it, and what goes wrong",
      "failure_class": "wrong_result | lost_data | fail_open | broken_contract | none",
      "fix_kind": "implementation | correction",
      "title": "one line naming the defect"
    }
  ],
  "domains_reviewed": ["the-domain-key"],
  "files_read": ["path/to/file.py"]
}
```

`rule.ref` names what the § 5 form cites: the skill and the rule text for a `pack_rule`, the category for a `spine_category`, the convention file and its heading for a `convention`, the ADR number for an `adr`. `location` is `path:line` or `path:start-end`. An empty `findings` list is a valid answer when the change carries nothing substantiable.

## Author return

```toon
status: success | error
findings_file: {findings_file}
message: "<what went wrong — present only on error>"
```

## Step 4: Validate the findings (inline)

```bash
python3 .plan/execute-script.py plan-marshall:phase-6-finalize:review_support validate \
  --plan-id {plan_id} --kind code --verdict-file {findings_file}
```

Branch on the returned TOON:

- **`status: error`** — the findings file could not be read. Go to **Step 6 Branch C** with the returned `error` as the reason.
- **`valid: false`** — the findings break the schema, or `rejected_findings` names a finding without a cited rule, a location or a failure scenario. Repair it ONCE, in the inline context: for each `errors[]` entry and each rejected finding, re-read the cited rule and the change, then either supply the missing part from what the change shows or remove the finding when it cannot be substantiated — a rejected finding is never kept without its missing part ([`review-rubric.md`](../standards/review-rubric.md) § 3). Correct the findings file with the `Write` tool and validate again. The repair is author work, so the verifier of Step 5 is still a separate dispatch. Findings still invalid after that one repair go to **Step 6 Branch C** with reason `findings_invalid` and the first error.
- **`valid: true`** — capture `findings`, `facts` and `loop_back_target`.

**A clean delta round is followed by the closing round.** When `round_kind` is `delta` and `facts.blocking_count` is `0`, the round does not close on its own evidence — [`review-rubric.md`](../standards/review-rubric.md) § 8. Run the closing round in this same firing: repeat Step 1a's attribution call WITHOUT `--delta-step` and compose the scope of a full round, then Steps 2, 3 and 4 over every file of the change, and continue to Step 5 with the closing round's result. A delta round WITH a blocking finding needs no closing round; it continues to Step 5 as it is.

## Step 5: Verifier (dispatch from the inline context)

The verifier fires on every round that reached this point, on both author arrangements. Resolve the target exactly as Step 2 does — the resolve emits this firing's own `[DISPATCH]` record:

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  effort resolve-target --phase phase-6-finalize \
  --workflow plan-marshall:phase-6-finalize/workflow/code-review.md \
  --plan-id {plan_id} --caller plan-marshall:phase-6-finalize
```

The verifier carries `instructions`, not `workflow`: its task is the adjudication written below, and it reads only the findings file, the rules it cites and the code locations it names.

```text
Task: plan-marshall:{target}
  prompt: |
    name: code-review-verifier
    plan_id: {plan_id}
    skills: []
    instructions: |
      You are the VERIFIER for one round of the code review. You did not author
      the findings and must not re-author them: file no finding, edit no file,
      and add no finding the author did not report.

      The author's findings are the JSON file {findings_file}. Read it with the
      Read tool. The validator graded them as follows:

        round_kind: {round_kind}
        blocking: {blocking_count}
        advisory: {advisory_count}
        findings: {findings_rendered}

      Decide TWO questions, in this order.

      (1) IS THE GRADING SUPPORTED BY THE CITED EVIDENCE?
      For each finding, open the code at its location and the rule it cites.
      Check that the rule says what the finding claims, that the code at the
      location does what the failure scenario describes, and that the
      failure_class follows from that scenario. Answer false when any finding
      is not supported, and name it in reason.

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

`{findings_rendered}` is one line per `findings` entry of the Step 4 return, carrying its `ref`, `severity`, `fix_kind` and `title`.

On a parseable return, write the two answers and the reason with the `Write` tool to `{verifier_file}` as JSON:

```json
{"grading_supported": true, "may_close": true, "reason": "the verifier's reason"}
```

On a failed dispatch or an unparseable return, write nothing to `{verifier_file}` and continue — the validator then reads the verifier as absent, which closes nothing. Then validate again with the verifier's answer:

```bash
python3 .plan/execute-script.py plan-marshall:phase-6-finalize:review_support validate \
  --plan-id {plan_id} --kind code --verdict-file {findings_file} --verifier-file {verifier_file}
```

On a dispatch that wrote nothing, omit `--verifier-file`. Capture `verifier` (`accepted` / `declined` / `absent` / `malformed`), `may_close`, `loop_back_target`, `findings` and `facts` from this return — they are the round's final answer. `accepted` follows the verifier's first answer: it confirmed the grading. On a round with a blocking finding its `may_close: false` is the answer question (2) requires, so the round still reads `accepted`; `declined` means the verifier rejected the grading, or refused closure on a round without a blocking finding. Log the verifier's answer on the decision log before Step 6 branches — `{reason}` is the verifier's own free text, quoted per [§ Shell-safe free text](#shell-safe-free-text-in-command-templates):

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id {plan_id} --level INFO \
  --message '(plan-marshall:phase-6-finalize:code-review) Verifier {verifier}; may_close={may_close} — {reason}'
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

`may_close: true` already requires valid findings with no blocking finding and an accepted verifier, and Step 4 never lets a clean delta round reach this point, so the final round of a closing firing is always a full one.

### Branch A — the round closes

Resolve the findings earlier rounds of this review filed, which this round no longer holds as blocking — first the blocking findings, then the state findings, each `--detail` quoted per [§ Shell-safe free text](#shell-safe-free-text-in-command-templates):

```bash
python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings qgate resolve-by-rule \
  --plan-id {plan_id} --phase 6-finalize --rule code-review \
  --resolution taken_into_account \
  --detail 'code review closed at {sha}: the verifier accepted findings with no blocking finding'
```

```bash
python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings qgate resolve-by-rule \
  --plan-id {plan_id} --phase 6-finalize --rule code-review-state \
  --resolution taken_into_account \
  --detail 'code review closed at {sha}: the verifier accepted the findings and answered may_close=true'
```

On a non-`success` return from either call, do NOT record `done`: surface the returned error and halt.

Advisory findings are not filed — a pending finding blocks the merge — and reach the reader through the step's facts and the decision log, one line each — `{title}` is the review's free text, quoted per [§ Shell-safe free text](#shell-safe-free-text-in-command-templates):

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id {plan_id} --level INFO \
  --message '(plan-marshall:phase-6-finalize:code-review) Advisory at {ref} — {title}'
```

Then record the close, with `--display-detail` quoted per [§ Shell-safe free text](#shell-safe-free-text-in-command-templates):

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize --step default:code-review --outcome done \
  --display-detail 'code review clean: {files_read} files, {advisory_count} advisory' \
  --fact acceptance={verifier} --fact may_close=true --fact work_performed=true \
  --fact round_kind={round_kind} \
  --fact domains_reviewed={domains_reviewed} --fact files_read={files_read} \
  --fact blocking_count={blocking_count} --fact advisory_count={advisory_count} \
  --fact rules_cited={rules_cited} \
  --fact override_closed_heads={override_heads} \
  --head-at-completion {sha}
```

Every `{…}` count is the value of the same-named key in the Step 5 validator `facts`. The `--fact override_closed_heads` line is conditional: include it only when `{override_heads}` is non-empty, and drop it otherwise.

### Branch B — the round loops back

The round does not close. File the blocking findings before the outcome is recorded.

**On a full round**, first resolve the blocking findings earlier rounds filed — this round re-examined every file, so its blocking set is the whole of what still blocks, and a finding it still holds is re-filed below as pending (`--detail` quoted per [§ Shell-safe free text](#shell-safe-free-text-in-command-templates)):

```bash
python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings qgate resolve-by-rule \
  --plan-id {plan_id} --phase 6-finalize --rule code-review \
  --resolution taken_into_account \
  --detail 'superseded by the code review round at {sha}'
```

A delta round resolves nothing: it examined only part of the change, so a finding outside its scope still stands.

File every `findings` entry whose `severity` is `blocking`, one call each — `{ref}` and `{title}` are the review's free text, so `--title` and `--detail` are quoted per [§ Shell-safe free text](#shell-safe-free-text-in-command-templates):

```bash
python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings qgate add \
  --plan-id {plan_id} --phase 6-finalize --source qgate --type bug \
  --title 'code finding at {ref}' --detail '{title} [fix_kind {fix_kind}]' \
  --rule code-review --component plan-marshall:phase-6-finalize --severity error
```

Advisory findings are not filed — a pending finding blocks the merge — and reach the reader through the step's facts and the decision log, one line each, quoted per [§ Shell-safe free text](#shell-safe-free-text-in-command-templates):

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --plan-id {plan_id} --level INFO \
  --message '(plan-marshall:phase-6-finalize:code-review) Advisory at {ref} — {title}'
```

**When the verifier did not accept**, also file one state finding naming which situation it was — `verdict_refused` (`verifier: declined`), `verifier_unavailable` (`verifier: absent` or `malformed`). The fixed rule key is what lets the closing round, or an operator close, resolve it. `{reason}` is the verifier's free text, quoted per [§ Shell-safe free text](#shell-safe-free-text-in-command-templates):

```bash
python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings qgate add \
  --plan-id {plan_id} --phase 6-finalize --source qgate --type bug \
  --title '{state} at code-review' --detail '{reason}' \
  --rule code-review-state --component plan-marshall:phase-6-finalize --severity warning
```

On a non-`success` return from any `qgate add`, do NOT record the loop-back: surface the returned error and halt — a loop-back whose findings are not in the store points the next round at nothing.

**Select the target.** The target is the validator's `loop_back_target` when it is `5-execute` or `6-finalize`. A round with no blocking finding that loops back only because the verifier did not accept has `loop_back_target: none`; its target is `6-finalize` — the next round is a re-review of the diff in hand.

**On target `5-execute`**, every blocking finding with `fix_kind: implementation` becomes one fix task. Allocate each through the two-step add:

```bash
python3 .plan/execute-script.py plan-marshall:manage-tasks:manage-tasks prepare-add \
  --plan-id {plan_id}
```

Write the fix task's definition to the returned path with the `Write` tool, in the task-definition format `manage-tasks` documents for `prepare-add`: a title naming the finding's `ref`, a description carrying its `title`, and the number of the deliverable whose file set holds the finding's location (the `files` rows of Step 1a). Then commit it:

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
  --plan-id {plan_id} --phase 6-finalize --step default:code-review --outcome loop_back \
  --loop-back-target {target} \
  --display-detail '{verdict}' \
  --fact acceptance={acceptance} --fact may_close=false --fact work_performed=true \
  --fact round_kind={round_kind} \
  --fact domains_reviewed={domains_reviewed} --fact files_read={files_read} \
  --fact blocking_count={blocking_count} --fact advisory_count={advisory_count} \
  --fact rules_cited={rules_cited} \
  --fact override_closed_heads={override_heads} \
  --head-at-completion {sha}
```

The `--fact override_closed_heads` line is conditional here as well: include it only when `{override_heads}` is non-empty.

`{verdict}` is `code review found {blocking_count} blocking over {files_read} files, {advisory_count} advisory` when the round has a blocking finding, and `code review not closed: verifier {verifier}` when it has none.

A loop-back is a productive non-completion, not a failure: the round examined the change and handed back work for the next round. It is never recorded `failed`.

### Branch C — the review could not run

Reached when the footprint or the rulebook could not be resolved, the author failed, or the findings stayed invalid after their one repair. Nothing was evaluated, so the step records the **not-run** state of [`review-rubric.md`](../standards/review-rubric.md) § 11 — never a clean verdict — with `work_performed=false`.

The outcome is `loop_back` to `6-finalize`, and the choice is load-bearing. A `done` would close a review that never ran. A `failed` leaf record does not stop the dispatcher's step loop, so `push` would run next and ship the change unreviewed. `loop_back` is the outcome that stops the loop advancing past this step and re-fires it on the next entry, bounded by this step's round budget — so an input that stays unreadable halts the run for the operator rather than letting the push through.

File the not-run state first, so the store carries it and an operator close resolves it with the other state findings. `{reason}` may be a script's error text, so `--detail` here and `--display-detail` below are quoted per [§ Shell-safe free text](#shell-safe-free-text-in-command-templates):

```bash
python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings qgate add \
  --plan-id {plan_id} --phase 6-finalize --source qgate --type bug \
  --title 'not_run at code-review' --detail '{reason}' \
  --rule code-review-state --component plan-marshall:phase-6-finalize --severity warning
```

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize --step default:code-review --outcome loop_back \
  --loop-back-target 6-finalize \
  --display-detail 'code review not run: {reason}' \
  --fact work_performed=false \
  --head-at-completion {sha}
```

When `rev-parse` itself failed, omit `--head-at-completion` rather than forwarding an unresolved value, and append `; HEAD unresolvable` to the detail.

## Operator override and the rounds that follow it

When this step's round budget is spent, the operator either grants another round or closes the review with `manage-status loop-back close --step code-review`, which records `may_close=operator_override` at the head the operator judged and resolves this step's `code-review-state` findings. The override closes ONLY that head ([`review-rubric.md`](../standards/review-rubric.md) § 8):

- A later fix commit advances HEAD past the override-closed record, so the dispatcher's HEAD-dependency check re-fires this step, and `attribution` scopes the firing as a delta round over the files the commit touched. The re-fire comes from the HEAD advance, not from a loop-back admission, so it spends no round from this step's budget.
- Step 1d adds every override-closed head to `code_review_override_heads`, and every later record carries the list as `override_closed_heads`.

## Round-loop termination

The step's record holds exactly one of four things, and they are different records:

- **Closed** — Branch A: a full round with no blocking finding that the verifier accepted (`may_close=true`).
- **Looped back** — Branch B: the round found work for the next round, or the verifier did not accept (`may_close=false`, `work_performed=true`).
- **Not run** — Branch C: nothing was evaluated (`work_performed=false`, outcome `loop_back`), so the run cannot advance to the push until the review runs.
- **Closed by the operator** — `manage-status loop-back close`, recorded with `may_close=operator_override`. This is not a closed review and is never reported as one.
