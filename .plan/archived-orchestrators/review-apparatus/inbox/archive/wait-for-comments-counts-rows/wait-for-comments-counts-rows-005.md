envelope_version=1
sender_type=plan
sender_id=wait-for-comments-counts-rows
epic=review-apparatus
kind=finding
created=2026-08-01T17:08:10Z

## Finding — `finalize-step-plugin-doctor` Step 5's divergence WARNING command can never execute (literal semicolons vs the one-command-per-Bash-call hook)

**Surfaced by:** PLAN-PR-001 finalize (scoped-mode plugin-doctor run). **Not this plan's defect.**

**Component:** project-local `.claude/skills/finalize-step-plugin-doctor/SKILL.md`, Step 5 (cross-skill divergence WARNING).

### Observation

Step 5's cross-skill-divergence WARNING is emitted via a logging command whose **message text contains literal semicolons**.

This repository enforces one-command-per-Bash-call with a hook that rejects a Bash call containing `;` — and the hook inspects the raw command line, so a semicolon inside the *message argument* is indistinguishable from a command separator. The command as written is rejected outright, unconditionally.

### Blast radius

The command is not merely fragile — it is **structurally dead**. Every scoped-mode run of the wrapper reaches Step 5, attempts the WARNING, is refused by the hook, and must paraphrase the warning by hand to get any signal out at all. There is no input under which the documented command succeeds.

Consequences:

- The divergence WARNING never lands in the work log in its canonical form, so the log is not a reliable record of whether Step 5 fired.
- Each run paraphrases differently, so the warning text is not greppable or comparable across runs.
- A step whose documented command can never run reads as working (the wrapper continues) while producing no durable artifact — an availability defect that is invisible from the outcome.

This is the known "`manage-logging` messages with a literal `;` trip the one-command hook" hazard, present in a checked-in project-local skill rather than in an ad-hoc invocation.

### Fix shape

Rewrite the WARNING message text to avoid `;` entirely (commas, em-dashes, or separate log lines all work). No mechanism change — the message string is the whole defect. Worth a sweep for the same shape across the other project-local `finalize-step-*` skills at the same time.

### Epic relevance

Routed here because the surfacing surface is the finalize review/lint chain that `review-apparatus` governs. If the epic judges this a general workflow-discipline defect rather than a review-apparatus one, it is a candidate for delegation to `truthful-signals` via the INBOX — a command that can never execute while its step reports normal completion is exactly the confident-signal-hides-a-caveat archetype.
