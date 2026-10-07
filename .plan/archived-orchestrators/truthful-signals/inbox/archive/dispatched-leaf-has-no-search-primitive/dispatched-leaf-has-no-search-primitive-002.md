envelope_version=1
sender_type=plan
sender_id=dispatched-leaf-has-no-search-primitive
epic=truthful-signals
kind=candidate-lesson
created=2026-07-29T09:18:40Z

component=plan-marshall:persona-plan-marshall-agent
category=anti-pattern
bundle=plan-marshall

# A hard rule that names a tool as its own remedy breaks for any executor the runtime denies that tool

## Observation

The project's file-operation hard rule prohibits Bash `grep` and names the `Grep` **tool** as the sanctioned alternative. That pairing is only sound while every bound executor actually holds `Grep`.

A dispatched `execution-context` leaf does not. The harness may revoke `Grep`/`Glob` from a subagent at runtime, while the bare-`grep` prohibition — enforced by a hook — stays fully active. The result is an executor class that is forbidden the raw primitive **and** denied the remedy the rule points it at, with no third path.

This is a **permission asymmetry**, not an empty intersection of constraints. Exactly one constraint is at fault: its escape hatch is permission-gated away from a subset of the executors it binds.

## Why the obvious repair is not available

"Just grant `Grep` to leaves" was checked and refuted:

- The agent frontmatter already **declares** `Grep`.
- `permissions.deny` is `[]`.

The revocation happens below the surfaces this project controls, so the asymmetry cannot be closed from the rule's own side.

## Corrective rule

When authoring a prohibition whose remedy is a named tool, state the remedy in terms the **least-privileged bound executor** can actually reach — or carve out an explicitly-bounded fallback for that executor class. Never let a rule's only escape hatch depend on a capability the runtime can withdraw while the prohibition itself cannot be withdrawn.

Generalised detector: for each hard rule of the form "never X, use Y instead", ask whether **every** executor the rule binds is guaranteed to hold Y. If not, the rule is unsatisfiable for that class and needs a third path.

## Evidence

Reproduced **six times live inside the plan run that fixed it** — 2-refine, 3-outline, the Q-Gate, 5-execute, the reframe dispatch, and the self-review gate. First-party, not inferred.

## Relationship to existing corpus

`arch-constraint` lesson `2026-07-29-08-001` already records the *constraint*. This candidate records the **generalised authoring rule** behind it. If the orchestrator judges that the arch-constraint lesson already covers the ground, fold rather than duplicate — but the generalisation ("remedy must be reachable by the least-privileged bound executor") is the reusable part and is not currently stated anywhere.

## Fix that shipped

PR #1046 sanctioned `git grep` as the bounded broad-content-sweep carve-out for a dispatched leaf, across 6 doc surfaces + 2 pinning tests.
