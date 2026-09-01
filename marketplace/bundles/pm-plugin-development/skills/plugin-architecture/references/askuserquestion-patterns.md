# AskUserQuestion Authoring Obligations

Five obligations every `AskUserQuestion` prompt in this marketplace must meet. Each one is stated as a rule a prompt can be tested against — not as advice — and each carries an **enforced by** marker naming what actually checks it.

Three obligations (1, 2, 5) are mechanically checked by the `askuserquestion-prompt-quality` rule in [`plugin-doctor`](../../plugin-doctor/references/rule-catalog.md). Two (3, 4) are author judgement only. Read [What this document does not enforce](#what-this-document-does-not-enforce) before treating a clean doctor run as a verdict.

The reader answering the prompt knows their own problem. They do not know this system. Every obligation below follows from that one asymmetry.

## Obligation 1 — Every option states its consequence

An option's description says **what happens when it is chosen**, not what the option is called. An option carrying a label and no description, or a description that only restates the label, fails.

**Enforced by**: `askuserquestion-prompt-quality`, check B.

```text
# BAD — the description restates the label; the reader learns nothing
Options:
1. Squash — Squash merge
2. Rebase — Rebase merge
```

```text
# GOOD — each description names the outcome
Options:
1. Squash — The branch lands on main as one commit; the individual commit messages are discarded.
2. Rebase — Each commit lands on main separately; the branch history is preserved.
```

## Obligation 2 — No option is describable only in system-internal mechanics

An option a reader can evaluate only by reasoning about skill loading, dispatch envelopes, frontmatter, phases, or a tool API is not a choice they can make. Describe the option by its effect on **their** work.

**Enforced by**: `askuserquestion-prompt-quality`, check A.

```text
# BAD — answering requires knowing what "loading a standard set" does
Options:
4. pick this only if you want the plan to avoid loading the Java/CUI standard sets
```

```text
# GOOD — the same option, described by what the reader gets
Options:
3. Neither — Your code is reviewed against language-neutral standards only; no Java- or Python-specific findings are raised.
```

## Obligation 3 — The recommended option is marked and ordered first

When one option is the right answer in the common case, say so and put it first. A prompt with a hidden default makes the reader re-derive a judgement the author already made.

**Enforced by**: author judgement (not mechanically checked).

```text
# BAD — the author's recommendation exists but is buried and unmarked
Options:
1. Abort — Stop and discard the run.
2. Retry once — Re-run the failing step a single time.
3. Retry with a longer timeout — Re-run with the timeout raised to 10 minutes.
```

```text
# GOOD — recommendation first and marked
Options:
1. Retry with a longer timeout (recommended) — Re-runs with the timeout raised to 10 minutes; this clears the usual cause.
2. Retry once — Re-runs the step unchanged; use this when you expect the failure was transient.
3. Abort — Stops the run and discards the partial result.
```

## Obligation 4 — The question names what the system already knows and why it still needs the user

State the finding that produced the question, then the gap the reader has to close. A bare question makes the reader guess what was already established.

**Enforced by**: author judgement (not mechanically checked).

```text
# BAD — no context; the reader cannot tell what is being decided or why
Question: "What type of plan for this task?"
```

```text
# GOOD — what is known, then what is missing
Question: "Your request changes both the build configuration and the test tree, so this reads as either a fix or a refactor. Which is it?"
```

## Obligation 5 — The preamble carries no workflow step number, tool-API type, or internal noun

The preamble is the reader's first sentence. A step number, a tool-API type name, or an internal noun in it tells the reader they are watching a machine's log rather than being asked a question.

**Enforced by**: `askuserquestion-prompt-quality`, check A.

```text
# BAD — a step number and a tool-API type name in the reader's first sentence
Question: "Domain detection returned ambiguous (no narrative match). Per Step 7 this requires an operator multiSelect"
```

```text
# GOOD — the same situation, in the reader's terms
Question: "Your files match no single language clearly, so the review standards cannot be picked automatically. Which should this plan apply?"
```

## Worked example: the api-sheriff prompt

This is the prompt that motivated the obligations. It fails 5 (a step number and a tool-API type in the preamble) and 2 (option 4 is answerable only by reasoning about which standard sets get loaded). Options 1–3 are elided — they are not part of the recorded example.

```text
# BAD — as it shipped
Question: "Domain detection returned ambiguous (no narrative match). Per Step 7 this requires an operator multiSelect"
Options:
1. (elided)
2. (elided)
3. (elided)
4. pick this only if you want the plan to avoid loading the Java/CUI standard sets
```

```text
# GOOD — conformant rewrite
Question: "Your files match no single language clearly, so the review standards cannot be picked automatically. Which should this plan apply?"
Options:
1. Java (recommended) — Reviews your code against the Java standards: naming, null-safety, and test conventions.
2. Python — Reviews your code against the Python standards: typing, packaging, and pytest conventions.
3. Neither — Reviews your code against language-neutral standards only; no language-specific findings are raised.
```

The rewrite is the same decision: the reader still picks the standards. It carries no step number, no tool-API type, and no option that requires knowing what the system does internally. The `askuserquestion-prompt-quality` test suite pins this pair — the shipped form must produce findings, the rewrite must produce none.

## What this document does not enforce

Obligations **3** (recommended option marked and ordered first) and **4** (the question names what the system already knows) are author judgement. The `askuserquestion-prompt-quality` rule does not evaluate them, and deliberately does not try: both require deciding whether a recommendation is *correct* and whether context is *sufficient*, which no token check can answer.

A clean `plugin-doctor` run therefore means "no obligation-1, -2, or -5 violation was found in the invocation blocks examined". It does **not** certify a conformant prompt. Obligations 3 and 4 remain the author's and the reviewer's to check by reading.

## Tool mechanics you cannot infer

Three facts about the tool that no amount of care will let an author guess. Everything else about a prompt is governed by the obligations above.

| Fact | Consequence for the author |
|------|----------------------------|
| An option list holds 2–4 options | A one-option prompt is invalid — use plain text for pure free-text input |
| `header` is capped at 12 characters | Longer headers are truncated; write the header as a short noun, not a sentence |
| A free-text option is added automatically, labelled `Type something.` | The label is fixed and not customisable — if free text is meant for a specific purpose, the question text has to say so |
