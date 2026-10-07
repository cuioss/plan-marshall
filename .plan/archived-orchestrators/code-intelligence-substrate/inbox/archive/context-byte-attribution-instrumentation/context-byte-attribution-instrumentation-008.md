envelope_version=1
sender_type=plan
sender_id=context-byte-attribution-instrumentation
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-08-03T16:50:30Z

component=plan-marshall:persona-plan-marshall-agent
category=anti-pattern
bundle=plan-marshall

# Eleven argparse rejections in one plan, across nine distinct scripts, two matching signatures the rule already names verbatim

`signal_script_failure_clusters_count` was 11 for this plan. `work/fragment-script-failure-analysis.toon` resolves that to 12 total / 11 unique failures, of which **9 are `argparse_rejection` (exit 2) spread over 8 distinct script notations**. The remaining 2 are genuine script-internal errors.

The rejections, by subtype:

| Notation | Subcommand | Subtype | Rejected on |
|---|---|---|---|
| `manage-findings` | `qgate` | invented_flag | `--resolution-detail` |
| `manage-findings` | `qgate add` | argparse_other | missing required set |
| `manage-solution-outline` | `get-deliverable` | missing_required_flag | `--deliverable-number` |
| `manage-files` | `read` | invented_flag | `--tail 20` |
| `phase-6-finalize:ci_verify` | `run` | missing_required_flag | `--worktree-path` |
| `tools-integration-ci:ci` | `pr` | invented_flag | verb-scoped `--plan-id` |
| `workflow-integration-github:github_pr` | `bot_completion` | missing_required_flag | `--bot-kind` |
| `workflow-integration-git:git-workflow` | `switch-and-pull` | missing_required_flag | `--base` |
| `workflow-integration-git:git-workflow` | `prune-local-and-remote-ref` | invented_flag | `--branch` |

## Why this is not just another recurrence tally

Two of these — `--tail` on `manage-files`, and a **verb-scoped `--plan-id` on `ci pr`** — are named *verbatim* as recurrence signatures in `persona-plan-marshall-agent/standards/agent-behavior-rules.md` § "Never invent script subcommands — recurrence signatures". The rule is loaded into every single dispatch in the pipeline, as the first and most foundational skill. It is not obscure, not optional, and not buried: it carries its own worked examples of these exact two flags.

**The guard is stated, loaded, and still violated nine times in one plan.** That is the finding. A hard rule that every envelope loads and that still produces 9 violations per run is not functioning as a guard — it is functioning as documentation. Restating it more loudly is the intervention that has already been tried.

## First-hand recurrence, observed while writing this lesson

This is not a reconstruction from logs. The `lessons-capture` step that authored this message reproduced the defect **twice within its own execution**, minutes after reading the rule:

1. `manage-findings qgate list --plan-id ...` — omitted the required `--phase`. Exit 2. (Logged at `2026-08-03T16:45:33Z`, i.e. *after* the retrospective's fragment was written, so it is not even counted in the 11.)
2. `manage-files list --plan-id ... --path artifacts` — the flag is `--dir`, not `--path`. Exit 2, twice in one parallel batch.

So the true rate for this plan is at least 11 argparse rejections, not 9, and the step whose job is to *record* the pattern instantiated it while doing so. The recurrence is not a property of careless dispatches; it is a property of the interface.

## Solution

The corrective action is **not** "read the rule harder". Three structural directions, in rough order of leverage:

1. **Make the executor answer the question the caller is actually asking.** Every one of these 9 failures is a caller that knew the notation and the verb but guessed one flag. `execute-script.py` already holds the `SCRIPTS` mapping; a rejection could return the accepted flag set for that exact subcommand as structured TOON rather than an argparse usage dump, turning a dead exit-2 into a self-correcting round trip.
2. **Close the naming drift at the source.** `--path` vs `--dir`, `--tail` vs no-such-thing, verb-scoped vs top-level `--plan-id`: the guesses are all *plausible* because sibling scripts really do use the guessed name. The `ARGUMENT_NAMING_*` plugin-doctor cluster is the right home for enforcing one name per concept across the whole script surface; this plan's evidence is a population-derived argument for widening it.
3. **Treat exit-2 clusters as a first-class quality signal, not narrative residue.** 9 rejections cost real tokens and real wall-clock in every plan. `fragment-script-failure-analysis.toon` already computes the cluster; nothing currently gates on it.

## Impact

Cross-cutting, every plan, every phase. This is a **token-cost** finding as much as a correctness one, which places it inside `code-intelligence-substrate`'s priority-1 remit: each rejection is a wasted round trip whose cost is the full re-sent context, not the ~40 tokens of the failed command. Nine of them per plan is a measurable, recurring, entirely avoidable context tax — and it is exactly the class of spend this epic's instrumentation now makes visible.

**Note for the orchestrator-side pickup:** `plan-retrospective` surfaced this at medium confidence and deliberately withheld it from the inbox at its confidence bar (`work/fragment-lessons-proposal.toon`, `medium_confidence_reported_not_recorded[1]`). It is routed here because the script-failure cluster IS this step's declared signal population, and because the in-step reproduction above is fresh evidence the retrospective could not have had. It is not a duplicate of messages 001-006.
