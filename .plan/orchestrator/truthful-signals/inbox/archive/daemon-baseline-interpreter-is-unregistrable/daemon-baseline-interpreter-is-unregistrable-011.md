envelope_version=1
sender_type=plan
sender_id=daemon-baseline-interpreter-is-unregistrable
epic=truthful-signals
kind=candidate-lesson
created=2026-08-08T21:22:27Z

component=plan-marshall:phase-6-finalize
category=bug
confidence=high
source_aspects=findings-store,artifact-consistency

# create-pr silently truncates the Intent section mid-sentence and drops the Non-goals paragraph

## Context

`create-pr` distills the plan's intent into a character-budgeted `## Intent` section of the PR description. On this run the distillation overran and was cut:

> `(plan-marshall:phase-6-finalize:create-pr) Intent section truncated to 1493 of 1500 chars — distillation ran long`

The cut landed **mid-sentence**, and what it removed was the **Non-goals** paragraph — the paragraph that tells reviewers which concerns were deliberately scoped out. On this PR that paragraph named three real exclusions: the refusal-visibility question above `build_server.py`, `build_server.py` itself, and the `manage-build-server status` version divergence.

The author noticed and posted a restoring comment (`b75eb2`, "### Non-goals (restored — truncated in the PR description)") explicitly so that reviewers would not file a deliberately scoped-out item as a gap. That manual repair is the only reason the published scope statement was complete — nothing in the pipeline surfaced the truncation to a reader of the PR.

## Root cause

Three compounding properties, none of which is the budget itself:

1. **The truncation is silent at the artifact.** The rendered PR description ends mid-sentence with no marker; a reader cannot tell a cut section from a short one.
2. **The cut is positional, not semantic.** The budget is spent front-to-back, so whatever is authored last is what disappears. Non-goals conventionally comes last, which makes the scope-limiting statement the systematically most likely casualty — the worst possible thing to drop from a document reviewers use to decide what counts as a gap.
3. **The signal is logged at INFO.** `4d7456` is an INFO decision-log line. An event that materially changed the published scope of a PR is recorded at the same level as routine progress, so nothing escalates it.

## Proposed action

- Emit a visible truncation marker into the rendered section itself (e.g. a trailing "… (truncated)" plus a pointer), so the artifact never presents a partial statement as a whole one.
- Make the budget allocation section-aware rather than positional: reserve a floor for Non-goals (and any other scope-limiting block) before spending the remainder on narrative, so an overlong narrative cannot evict the exclusions.
- Raise the truncation log line to WARNING, and — since a distillation overrun is a recurring shape rather than a one-off — record whether the truncation crossed a section boundary, which is the discriminator between a harmless tail trim and a dropped clause.

## Impact scope

Bounded on this plan because a human caught it. The general case is not: a PR whose Non-goals paragraph vanished, with no marker and no warning, invites reviewers to file scoped-out items as gaps — cost paid in reviewer attention and in triage disposing of false findings. It also degrades the PR description as an evidence artifact for later retrospectives, which read it as the plan's published scope.

## Evidence

- decision.log `4d7456`, level INFO — "(plan-marshall:phase-6-finalize:create-pr) Intent section truncated to 1493 of 1500 chars — distillation ran long"
- finding `b75eb2` — the author's restoring `issue_comment` on PR #1122, resolved `taken_into_account`; its own resolution detail notes that fixing the distillation budget "falls outside this plan's settled write boundary and is not undertaken here"
- `review-retrospective.md` — independently characterises `b75eb2` as "a scope-restoration comment … republishing the `Non-goals` paragraph that the PR description's `## Intent` section truncated at its character budget"
