envelope_version=1
sender_type=plan
sender_id=absent-names-two-states-with-opposite-remedies
epic=review-apparatus
kind=candidate-lesson
created=2026-08-08T20:41:35Z

# Candidate lesson: `review_completeness` list flags disagree on bot-token form and mis-parse silently

**Source record:** pending Q-Gate finding `b423d3`, phase `6-finalize`, component `plan-marshall:automatic-review`, severity warning. Filed while hand-driving the pre-merge barrier on PR #1118.

## The observation

`review_completeness check` takes several bot-set flags. They do not agree on token form:

- `--participated-bots` requires the **pair** form `bot_kind:evidence_kind`.
- `--stale-participation-bots` requires **bare** kinds.

Feeding the wrong form to either flag is accepted silently. The unparsed token is dropped and the bot resolves to `absent` — its true state is never reported.

## Why it is load-bearing rather than cosmetic

`absent` is a blocking member. So a caller that passes a well-formed-looking-but-wrong token does not get a parse error, an unknown-token warning, or a degraded verdict; it gets a **confident false merge block** attributed to a bot that in fact participated.

Both directions were hit on this run, on this plan's own PR:

- a pair fed to `--stale-participation-bots` reported `absent` instead of `participated_stale`
- bare kinds fed to `--participated-bots` reported `absent` instead of `participated_but_empty`

The asymmetry is invisible at the call site because **the producer emits pairs for both sets**. A caller reading the producer's output and forwarding it verbatim gets the wrong form for one of the two flags by construction.

## Shape of the defect

This is the silent-mis-parse-into-a-blocking-default archetype: an input the parser cannot understand resolves to the value that means "we have no evidence", and "no evidence" is exactly the value that blocks. The failure is therefore both silent AND polarity-selecting — the two properties that this whole plan existed to remove from the participation apparatus, reappearing one layer down in the flag parser rather than in the classifier.

## Candidate remedy (not applied)

Either make the two flags take the same token form, or reject an unparseable token loudly (non-zero exit / explicit error) rather than dropping it into `absent`. A parse that cannot round-trip its input must not resolve to a blocking state by default.

## Why it is routed here

`review_completeness` is the epic's own instrument. A false merge block manufactured by its argument parser is a `review-apparatus` reliability defect, not a general-purpose lesson.
