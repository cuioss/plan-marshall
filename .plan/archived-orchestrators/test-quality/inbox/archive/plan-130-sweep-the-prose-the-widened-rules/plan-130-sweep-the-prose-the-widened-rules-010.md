envelope_version=1
sender_type=plan
sender_id=plan-130-sweep-the-prose-the-widened-rules
epic=test-quality
kind=candidate-lesson
created=2026-09-07T15:22:31Z

# Three argparse rejections in one finalize phase, all from workflow prose read as if it were the argparse surface

**Signal**: `script_failure` markers in the `6-finalize` work log. Three distinct notations, each `exit_code=2`, `failure_kind=argparse_rejection`.

## The three records

| Time (UTC) | Notation | Rejection detail |
|---|---|---|
| `2026-09-07T06:13:08Z` | `plan-marshall:workflow-integration-github:github_pr` | required flag missing on `bot_completion`: `['bot-kind']` |
| `2026-09-07T15:08:36Z` | `plan-marshall:manage-references:manage-references` | unregistered verb; accepted set `['add-list', 'capture-footprint', 'compute-footprint', 'create', 'get', 'get-context', 'read', 'reconcile-scope', 'set', 'set-list', 'sync-affected-files']` |
| `2026-09-07T15:11:09Z` | `plan-marshall:manage-solution-outline:manage-solution-outline` | unregistered verb; use `list-deliverables` — registered `['exists', 'get-deliverable', 'get-field', 'get-module-context', 'list-deliverables', 'read', 'resolve-path', 'update', 'validate', 'write']` |

## What they have in common

All three fired inside **dispatched post-run-review leaves** (`automatic-review`, `plan-retrospective`) — steps whose workflow docs describe the reads they need **narratively** ("read the plan's references", "list the deliverables") rather than quoting the canonical invocation. Two of the three are the verb-paraphrase signature; one is a missing required flag. None is a novel failure mode: all three are already-named recurrence signatures in `persona-plan-marshall-agent` § "Never invent script subcommands".

The interesting fact is therefore **not** that the signature exists — it is that the guidance forbidding it was loaded in every one of these envelopes and the rejections still happened three times in a single phase.

## The transferable rule

Prohibition text does not survive contact with a narrative workflow step. A leaf reads "read the plan's references" and synthesises a verb, because the step gave it a goal and no command. The countermeasure that actually binds is **structural, at the authoring site**, not behavioural at the calling site:

- A workflow step that needs a script read should **quote the canonical invocation inline**, or xref the script's `Canonical invocations` block by name. A step that states only the intent has delegated verb selection to the model.
- Where a step legitimately cannot quote a fixed command, it should say so and instruct a `--help` walk first — making the extra call an expected step rather than a recovered failure.

## Cheap recovery is why this stays invisible

Every rejection above printed the accepted set in its own detail text, so recovery was one call away and no step failed. That is precisely why the class persists: it is self-healing at the cost of one wasted call each time, so it never surfaces as a defect and never gets fixed at the authoring site. Worth checking whether these three steps' docs can be made to quote their invocations.
