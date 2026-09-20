envelope_version=1
sender_type=plan
sender_id=a-rule-that-is-green-because-it-examined-nothing
epic=truthful-signals
kind=candidate-lesson
created=2026-08-08T18:40:30Z

component=plan-marshall:plan-retrospective
category=bug
title=Retrospective session capture overwrites the plan's execution session_id
confidence=high
source_plan=a-rule-that-is-green-because-it-examined-nothing

# Retrospective session capture overwrites the plan's execution session_id

## Context

`plan-retrospective` Step 1 calls `platform_runtime session capture --plan-id {plan_id}`, which stamps the **retrospective dispatch's own** session id into `status.metadata.session_id`. On this plan the field held `b933baa1-c60f-4e7c-84f2-59cf1ab19c29` (the execution session) before the call and `54e75a2b-dbee-478f-bfb5-5dc8f5df6b05` (the retrospective subagent's session) after it.

That field is single-valued, and this plan rotated it three times over its life: `d49a3991` at 13:39:31 (first phase-5 entry), `b933baa1` at 15:39:04 (phase-5 loop-back re-entry), `54e75a2b` at 18:19:26 (the retrospective). Each write destroyed the previous value, and no other artifact records the earlier ids.

## Root cause

Two independent problems compound:

1. `session capture` is a blind last-writer-wins stamp with no notion of "the session that executed the plan" versus "the session currently reading the plan".
2. `record-metrics` is ordered at 998, **after** `plan-marshall:plan-retrospective` at 995. So the retrospective overwrites the field and the metrics enrichment then consumes the overwritten value.

The consequence is concrete: `manage-metrics enrich --session-id` walks `~/.claude/projects/{slug}/{session_id}.jsonl` to attribute the four-field `message.usage` view and the derived `billing_weighted_total` per phase. Pointed at the retrospective's own transcript, it attributes the retrospective's context loads to the plan's phases and finds nothing for the phases that actually ran.

## Proposed action

- Make the session record multi-valued: append to a `status.metadata.session_ids[]` list rather than overwriting a scalar, keeping `session_id` as the first/execution session for backward compatibility.
- Have `plan-retrospective` Step 1 read the stored session rather than capture over it, or capture under a distinct key (`retrospective_session_id`).
- Have `enrich` walk every recorded session id and report the per-session attribution, so a plan spanning N sessions is measured over N transcripts instead of one.

## Evidence

- aspect: behavioural-observation — `metadata --get --field session_id` returned `b933baa1` before Step 1 and `54e75a2b` immediately after `session capture`
- aspect: chat_history_analysis — the chat aspect could reach only 1 of the plan's 3 sessions; the three real operator interactions (4 baked-in clarifications, the Q-Gate approval, the execution-profile override) all live in a transcript it cannot open
- aspect: plan_efficiency — `enrich` had not run at retrospective time, so `metrics.toon` carries no `input_tokens` / `cache_read_input_tokens` / `billing_weighted_total` on any phase row
- source: `logs/work.log` 615a2e (`Metadata: session_id=54e75a2b...` at 18:19:26, 72 seconds after the retrospective dispatch)
