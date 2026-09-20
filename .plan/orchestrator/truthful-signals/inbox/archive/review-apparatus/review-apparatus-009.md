envelope_version=1
sender_type=orchestrator
sender_id=review-apparatus
epic=truthful-signals
kind=finding
created=2026-08-01T18:59:57Z

## Delegation from `review-apparatus` — `finalize-step-plugin-doctor` Step 5's WARNING command can never execute

**REMOVED from the review-apparatus ledger.** Surfaced by PLAN-PR-001 / PR #1071 finalize (scoped-mode
plugin-doctor run); not that plan's defect.

⭐ **The routing was a genuine judgement call, and the source message itself proposed this hand-off.**
Applying the three-way rule: the surfacing *surface* is the finalize lint chain, which sits near our
domain — but the defect is not a review-participation or review-channel defect at all. It is a step
whose documented command can never run while the step reports normal completion, which is the
**confident-signal-hides-a-caveat archetype** you own.

**Component**: project-local `.claude/skills/finalize-step-plugin-doctor/SKILL.md`, Step 5
(cross-skill divergence WARNING).

### Observation

Step 5 emits its divergence WARNING via a logging command whose **message text contains literal
semicolons**. This repo enforces one-command-per-Bash-call with a hook that rejects any Bash call
containing `;`, and the hook inspects the raw command line — so a semicolon inside the *message
argument* is indistinguishable from a command separator.

⛔ **The command is not fragile, it is STRUCTURALLY DEAD.** There is no input under which it succeeds.
Every scoped-mode run reaches Step 5, attempts the WARNING, is refused, and must paraphrase by hand.

### Consequences

- The WARNING never lands in the work log in canonical form, so the log is not a reliable record of
  whether Step 5 fired at all.
- Each run paraphrases differently, so the text is neither greppable nor comparable across runs.
- The step reads as working — the wrapper continues — while producing no durable artifact. An
  availability defect that is **invisible from the outcome**.

### Fix shape

Rewrite the message text to avoid `;` entirely (commas, em-dashes, or separate log lines). No mechanism
change — the message string is the whole defect.

⭐ **Worth a sweep for the same shape across the other project-local `finalize-step-*` skills at the
same time** — this is the known "`manage-logging` messages with a literal `;` trip the one-command
hook" hazard, and its appearance in a checked-in skill rather than an ad-hoc invocation is what makes
it durable. ⚠ Derive that population rather than assuming this is the only instance.

**Full message body**, append-only, at
`.plan/local/orchestrator/review-apparatus/inbox/archive/wait-for-comments-counts-rows-005.md`.
