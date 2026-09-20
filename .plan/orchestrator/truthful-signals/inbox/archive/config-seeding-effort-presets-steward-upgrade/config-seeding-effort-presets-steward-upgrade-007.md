envelope_version=1
sender_type=plan
sender_id=config-seeding-effort-presets-steward-upgrade
epic=truthful-signals
kind=candidate-lesson
created=2026-08-26T14:42:34Z

component=plan-marshall:tools-script-executor
category=bug
source_plan=config-seeding-effort-presets-steward-upgrade
confidence=high

# The argparse-rejection hint names the wrong verb's flags and suggests a write verb for a read verb

## Context

The executor wraps argparse rejections in a helpful hint naming the accepted verbs or flags. That hint exists specifically to stop invented-subcommand and invented-flag drift — the recurrence signature `persona-plan-marshall-agent` § "Never invent script subcommands" is written against, and the one `script-failure-analysis` counted **33 times** in this plan alone. Two live instances observed during this retrospective show the hint itself producing the drift it exists to prevent.

**Instance 1 — the hint names a different verb's flags.**

```
python3 .plan/execute-script.py plan-marshall:manage-change-ledger:manage-change-ledger query --plan-id X --kind build
→ error: unknown_flag
  rejected: --plan-id
  accepted: changed-paths, commit-sha, deliverable-id, exit-code, fingerprint, job-id,
            job-status, kind, log-file, notation, output-bytes, plan-id, status,
            worktree-root, worktree-sha
```

The hint lists `plan-id` as accepted. Passing it again was rejected by argparse itself: `unrecognized arguments: --plan-id`. `query --help` shows the verb's real surface is exactly **two** flags — `--kind` and `--exit-code`. The fifteen listed are the `append` verb's fields. A caller following the hint is directed at thirteen flags that do not exist on the verb it just failed on.

**Instance 2 — the hint proposes a destructive verb as the fix for a read.**

```
python3 .plan/execute-script.py plan-marshall:manage-references:manage-references get-list --plan-id X --field affected_files
→ Use `plan-marshall:manage-references:manage-references set-list` — registered: [...]
```

`get-list` is a read that does not exist; the correct verb is `get`. The hint suggested **`set-list`** — a write. A caller trusting the suggestion would have overwritten the list it was trying to read. The same shape appeared in the plan's own logs at 16:35:45Z, where a `manage-references` rejection produced the identical `set-list` suggestion.

## Root cause

The suggestion is chosen by string proximity to the rejected token rather than by verb semantics or by the rejected verb's own parser. `get-list` is lexically nearest `set-list`; the `append` field set is presumably the script's declared field roster rather than the failing subparser's `_actions`.

## Proposed action

1. Derive the "accepted flags" list from the **rejected subparser's own** `_actions`, not from a script-level field roster. `--help` on that verb already produces the correct answer, so the data is present.
2. Constrain read-verb suggestions to read verbs. Never propose a mutating verb as the correction for a non-mutating one; a wrong suggestion that only fails is cheap, a wrong suggestion that succeeds destructively is not.
3. Add a regression that asserts, for every script and verb, that the hint's flag set equals that verb's parser flag set.

## Evidence

- Live reproduction during this retrospective: `manage-change-ledger query --plan-id` rejected with a 15-flag hint; `manage-change-ledger query --help` shows 2 flags.
- Live reproduction: `manage-references get-list` → suggested `set-list`; the correct verb is `get`.
- `logs/work.log` 2026-08-25T16:35:45Z — the same `set-list` suggestion produced during the run itself.
- aspect: `script_failure_analysis` — 33 total argparse rejections, 11 unique, across 7 components; `manage-solution-outline get-deliverable` alone accounts for 15.
