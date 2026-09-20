envelope_version=1
sender_type=plan
sender_id=path-attribution-seam
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-08-01T18:32:17Z

component=plan-marshall:manage-references
category=anti-pattern
bundle=plan-marshall

# manage-references has no `list` verb — the read surface is `read` / `get`, and `list` is an invented paraphrase

## What happened

During `6-finalize` on `path-attribution-seam`, a call was issued as:

```bash
python3 .plan/execute-script.py plan-marshall:manage-references:manage-references list --plan-id path-attribution-seam
```

argparse rejected it with `exit_code: 2`:

```text
manage-references.py: error: argument command: invalid choice: 'list'
(choose from 'create', 'read', 'get', 'set', 'add-list', 'set-list', 'get-context', 'compute-footprint')
```

The very next two calls in the log are `manage-references read` and `manage-references get`, both exit 0 — so the intent was a plain read and the correct verb was available the whole time. The cost was one wasted round-trip plus a `script_failure` marker that later tripped the finalize Signal Gate.

## Why it happened

This is recurrence signature #1 (verb-paraphrase) from `persona-plan-marshall-agent/standards/agent-behavior-rules.md` § "Never invent script subcommands". `list` is the verb that *names the goal* ("show me the references"), and it is the canonical read verb on most sibling `manage-*` scripts — `manage-findings list`, `manage-lessons list`, `manage-tasks list`, `orchestrator inbox list`. The cross-script regularity is exactly what makes the wrong guess feel safe.

`manage-references` is the outlier: its store is a single `references.json` per plan, not a collection of records, so its read surface is field-level (`read`, `get`, `get-context`) with no collection verb to list. The absence is a design consequence, not an oversight.

## The rule

**Do X:** Quote the subcommand verbatim from the script's `--help` output or from the owning skill's `## Canonical invocations` section. `manage-references` reads are `read` (whole document / section) and `get` (single field); `get-context` for the assembled context.

**Not Y:** Do not carry a verb across scripts because the sibling `manage-*` scripts share it. Cross-script verb regularity is a convention, not a contract — each script's argparse `choices` is the only authority.

## Detection

The `ARGUMENT_NAMING_*` plugin-doctor rule cluster catches this at edit time when the invented call is written into a skill or workflow document. It does **not** catch an ad-hoc call composed at runtime by the model, which is what happened here — so the runtime guard is the discipline itself: `--help` before a verb you have not used on *that specific script* before.

## Recurrence context

This is the same class as the four canonical argparse-rejection signatures already catalogued. The distinguishing detail worth recording is the *direction* of the error: the invented verb was not hallucinated from prose, it was **generalised from correct usage of sibling scripts**. That is a different and more persistent failure driver than prose-paraphrase, because the model has positive reinforcement for the wrong token.
