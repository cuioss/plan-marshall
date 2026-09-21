envelope_version=1
sender_type=plan
sender_id=identifier-vocabulary-decision
epic=orchestrator-refactor
kind=candidate-lesson
created=2026-09-20T08:31:47Z

component=plan-marshall:tools-integration-ci
category=anti-pattern
bundle=plan-marshall

# A documented argparse recurrence signature recurred anyway — the router-scoped --plan-id placed AFTER the ci verb

Source signal: script-failure cluster 1 of 3 on plan `identifier-vocabulary-decision`
(epic `orchestrator-refactor`). Work-log marker, `2026-09-20T07:08:35Z`:

```text
[ERROR] (plan-marshall:execute-script:2) script_failure
notation=plan-marshall:tools-integration-ci:ci exit_code=2
failure_kind=argparse_rejection
detail=ci.py: error: unrecognized arguments: --plan-id identifier-vocabulary-decision
```

The call placed `--plan-id` after the subcommand verb. On the `ci` surface `--plan-id`
is a **router** flag consumed ahead of the first verb token, so a post-verb placement
is rejected even though the flag exists and the value was correct.

## Why this one matters more than an ordinary typo

⛔ This exact failure is **already a documented recurrence signature**. It is named in
`persona-plan-marshall-agent/standards/agent-behavior-rules.md` § "Never invent script
subcommands — recurrence signatures" as the router-scoped-`--plan-id`-after-the-verb
case, and it is restated in the `execution-context` dispatcher's own prompt-body
contract table, which spells out the three positional cases for `--plan-id` on the `ci`
router specifically. The guard was written, is loaded into the agent that made the
call, and the call was made wrong anyway.

That is the finding: **a prose guard against a positional-argument mistake did not
prevent the mistake**, in an envelope that had the guard resident. Recording it as
"remember the rule harder" would be the vacuous-guard archetype this corpus already
carries n≥6 instances of.

## What actually worked

⭐ The failure envelope carried its own remediation and it is a good one:

```text
note: --plan-id is a top-level flag and belongs BEFORE the subcommand (verb), not
after it. The flag exists — it is only in the wrong position. Move it ahead of the
verb, e.g. `... plan-marshall:tools-integration-ci:ci --plan-id X pr view`.
```

Directional, names the fix, and distinguishes "flag does not exist" from "flag is
misplaced" — which is the distinction that makes the recovery one call instead of a
help-spelunk. The structural lever, if one is wanted, is on that side: make the
rejection self-correcting (or make the router accept both positions) rather than adding
another sentence of prose to a guard that already exists and already did not bind.

## For the epic

`orchestrator-refactor` is the epic that just landed ADR-023 on identifier-parameter
vocabulary. This is a **positional** rather than a *naming* defect, so it is adjacent to
but not covered by that ADR. Worth deciding whether the argument-vocabulary work should
grow a positional-contract arm, or whether this belongs to whichever epic owns the
`ARGUMENT_NAMING_*` plugin-doctor rule cluster.
