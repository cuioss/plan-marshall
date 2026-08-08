# Operator-Prompt Authoring

Every operator prompt (`AskUserQuestion`) is a **two-sided contract**. One side is the option the operator reads — its `label` and `description`. The other side is the branch the workflow dispatches when that option is chosen. This standard governs the correspondence between the two sides, and it applies to every option string an orchestrator assembles from a prompt-required envelope (`refine_prompt`, `escalate_ask`, `outline_prompt`) as well as to every prompt a main-context workflow fires directly.

## The option-text-names-the-branch rule

Each option's `label`/`description` MUST semantically name what the branch that option dispatches actually does — verified **per option**, not per prompt:

- A "Close" option MUST close. If choosing it defers, re-queues, or leaves the item open, the option text lies.
- A "Proceed" option MUST NOT defer. If choosing it parks the work for a later pass, it is a "Defer" option wearing a "Proceed" label.
- A "Stash foreign files and re-verify" option MUST stash and re-verify — not merely record a note.

The test is behavioural, not lexical: read the branch the option selects, then confirm the option text names that behaviour. An option whose wording "reads right" but selects a branch that does something else is a defect, even when every option is individually plausible.

## Re-check both sides on either change

The two sides drift independently. Changing one without re-verifying the other reopens the gap:

- When you edit an **option string**, re-read the branch it dispatches and confirm the new wording still names that branch's behaviour.
- When you edit a **branch** (what happens when an option is chosen), re-read every option that selects it and confirm the option text still names the new behaviour.

Both directions are mandatory. A prompt is only correct when every option, in its current wording, names the current behaviour of the branch it dispatches.

## Structural gates do not catch this — verify at authoring time

The in-house structural gates (the plugin-doctor rule set, the reachability analyzer, the marketplace lint pass) do NOT detect wording-vs-behaviour drift. They can confirm a prompt is *reachable* and *well-formed*, but they cannot judge whether an option's label semantically matches the branch it selects — that is a meaning-level correspondence no regex or AST check decides. Authors therefore verify the correspondence **at authoring time**, per option, as an explicit step of writing or editing any prompt. There is no downstream gate that will catch a mismatch for you.

## Prompts governed by this standard are assembled in envelopes

Under the leaf/dispatch-topology invariant, a dispatched leaf cannot reach the operator: it returns a prompt-required envelope and the main-context orchestrator fires the prompt. The option strings this standard governs are therefore assembled in the batched envelopes the orchestrator fires — `refine_prompt` (below-threshold confidence-loop clarification, owned by `plan-marshall/workflow/planning.md`), `escalate_ask` (scope-deviation / `smart_and_ask` gates, owned by `plan-marshall/workflow/execution.md`), and `outline_prompt` (open design questions, owned by `plan-marshall/workflow/planning-outline.md`). Whether the option string is authored in the leaf that computes the envelope or in the orchestrator that renders it, the option-text-names-the-branch rule binds it. See [`agents.md`](agents.md) § "Leaf cannot fire AskUserQuestion — return a prompt-required envelope" for the envelope contract and the precedent table.

This rule codifies the residue of the operator-prompt option-to-branch correspondence lesson: an option is only trustworthy when its text names the branch it dispatches, and that correspondence is re-verified whenever either side changes.
