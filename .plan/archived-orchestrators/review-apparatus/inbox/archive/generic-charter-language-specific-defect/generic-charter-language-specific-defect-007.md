envelope_version=1
sender_type=plan
sender_id=generic-charter-language-specific-defect
epic=review-apparatus
kind=candidate-lesson
created=2026-08-09T17:05:32Z

# A rejection banner that advertises the flag it just rejected sends the fix to the wrong place

component: plan-marshall:execution-context
category: bug
confidence: high
source_signal: signal_script_failure_clusters_count

## Context

This run's finalize phase argparse-rejected **three distinct script notations**, all inside dispatched `execution-context-level-5` envelopes, all with `exit_code=2 failure_kind=argparse_rejection`:

| Time | Notation | Rejection |
|------|----------|-----------|
| 13:23:45Z | `plan-marshall:manage-architecture:architecture` | `unrecognized arguments: --plan-id generic-charter-language-specific-defect` |
| 16:01:46Z | `plan-marshall:manage-status:manage-status` | `merge-authorization: error: argument merge_authorization_verb: invalid choice: 'generic-charter-language-specific-defect' (choose from 'grant', 'check')` |
| 16:02:48Z | `plan-marshall:tools-integration-ci:ci` | `unrecognized arguments: --plan-id generic-charter-language-specific-defect` |

Each fired inside a step that then completed and reported `outcome: done` — `architecture-refresh` reported "11 modules rediscovered, no descriptor drift"; `branch-cleanup` reported "PR 1130 merged via queue, main pulled, branch + worktree removed". Nothing in either step's `display_detail` records that a call was rejected and retried.

## Root cause

The three failures are not one signature. They are three, and they are only visible as three because the notations differ:

1. **`architecture` — declared, but positionally wrong.** `--plan-id` IS a real flag: `architecture.py --help` shows `[--plan-id PLAN_ID]` on the top-level parser, mutually exclusive with `--project-dir`. The call placed it AFTER the subcommand, where the subparser does not accept it. **The rejection banner printed the flag in its own usage line while rejecting it** — `usage: architecture.py [-h] [--project-dir PROJECT_DIR] [--plan-id PLAN_ID] {discover,init,...}` immediately above `error: unrecognized arguments: --plan-id ...`. A fixer reading that output sees the flag advertised as valid and concludes the flag is right, so the natural next move is to re-issue it, or to reach for a different flag name, rather than to move the flag left of the verb. The banner actively points away from the defect.

2. **`ci` — not declared at all.** `ci.py`'s usage is `ci.py [-h] {pr,checks,issue,branch,repo}` — no `--plan-id` on any parser. The foreign-checkout route this repo documents for `ci.py` is `--project-dir`, a top-level router flag consumed before dispatch. So here `--plan-id` is not misplaced, it does not exist.

3. **`manage-status merge-authorization` — a value where a verb belongs.** The plan id was passed as the first positional of `merge-authorization`, whose positional is the verb (`grant` / `check`).

What makes them one cluster is the caller's premise, not the parsers. The `execution-context` prompt-body contract states that `plan_id` is required and that **"every script call inside this envelope forwards `--plan-id {plan_id}`."** Read as written, that is a universal quantifier over script calls. It is false in three different ways at once: some scripts take the flag only top-level, some do not take it at all, and some take the plan id as a value under a verb that must come first. The envelope prescribes a flag whose acceptance is per-script and per-position, and the leaf obeys.

## Why the existing guards did not catch it

- `ARGUMENT_NAMING_*` (plugin-doctor, unconditionally active under `quality-gate`) governs **authored** invocations in markdown. These were composed at runtime by a leaf executing a prose contract, so no authored string was ever wrong.
- The `persona-plan-marshall-agent` hard rule *"Never invent script subcommands"* names the verb-scoped `--plan-id` / `--project-dir` signature explicitly, with worked examples. It is documented, loaded into every envelope, and it did not prevent the recurrence — for `architecture` and `ci` this is at least the second and third recorded instance of the same signature.

## Proposed action

1. **Fix the envelope's universal claim at the source.** `execution-context.md`'s "every script call inside this envelope forwards `--plan-id {plan_id}`" should state the rule that is actually true: forward `--plan-id` only where the target script declares it, and only in the position it declares it (top-level vs verb-scoped). A prose universal that is false for a known subset of the script surface is the defect, not the leaf that obeyed it.
2. **Make the rejection banner point at the defect.** When argparse rejects a flag that IS declared on an ancestor parser, the usage line reproducing that flag is worse than silence. Emit a distinguishing hint — the `execute-script` wrapper already classifies `failure_kind=argparse_rejection` and holds both the rejected token and the parser's declared set, so it can say *"`--plan-id` is declared on the top-level parser; place it before the subcommand"* rather than re-printing a banner that reads as an endorsement.
3. **Surface a rejection that a step recovers from.** All three steps reported `outcome: done` with no trace of the rejection in their `display_detail`. A retried-after-rejection call is exactly the degraded-input case a later reader needs; today it survives only as an `[ERROR]` line nothing consumes.

## Relation to the epic

Direct reinforcement of **PLAN-PR-017** (*a workflow doc prescribes a flag no script declares*), and the third notation recorded against it. It adds a sub-signature PR-017's current framing does not cover: the flag is **declared** and still rejected, purely on position, with the banner vouching for it. PR-017's D0 population should therefore include *flag-position* validity, not only flag *existence* and value shape.

## Evidence

- `logs/work.log` 2026-08-09T13:23:45Z, 16:01:46Z, 16:02:48Z — the three `script_failure` records, verbatim above
- `architecture.py --help` — `--plan-id PLAN_ID` declared top-level, mutually exclusive with `--project-dir`
- `ci.py` usage — `{pr,checks,issue,branch,repo}`; no `--plan-id` on any parser
- `execution-context` prompt-body contract, `plan_id` row — "every script call inside this envelope forwards `--plan-id {plan_id}`"
- `status.metadata.phase_steps.6-finalize` — `architecture-refresh` and `branch-cleanup` both `outcome: done`, neither mentioning a rejection
