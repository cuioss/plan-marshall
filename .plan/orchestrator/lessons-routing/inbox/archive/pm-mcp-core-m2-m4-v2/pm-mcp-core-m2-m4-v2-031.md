envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4-v2
epic=lessons-routing
kind=candidate-lesson
created=2026-11-13T18:20:18Z

component=plan-marshall:plan-marshall
category=improvement
route=plan-marshall lessons-routing (foreign component, forward per standing rule)
confidence=high

# Scope a fix task to the whole finding family at first sighting

## Context

In PLAN-V2-138 (pm-mcp-core) the integer-overflow finding family in the TAP, Jest and ESLint count parsing and the TAP plan-count guards was found one sibling per round: unified triage round 1 (TASK-22 per-run plan), unified triage round 2 (CodeRabbit 23a640, plan-count sum overflow, TASK-23 with one sibling), then code review (summary sums one method away, TASK-24). Only TASK-24 swept the whole family (TAP, Jest, ESLint fixed; Maven, LCOV, TestCounts, RewriteLogResult exempt with a stated bound). Each round cost a loop-back to 5-execute, a whole-tree verify of 20-30 minutes, a push, CI and another review-bot pass; 6-finalize ended at 57% of all plan tokens.

## Root cause

Triage scoped the fix task to the reported site and its nearest sibling ("nudge-batching") rather than to the family predicate ("a count read from log text summed or compared on a type that can wrap"), so the next reviewer found the next site.

## Proposed action

In the triage workflow (plan-marshall:plan-marshall workflow/triage.md, fix-task creation), when a finding names a defect class rather than a single wrong value, require the fix task to state the family predicate, enumerate every site matching it across the plan footprint and its neighbouring classes (an inventory content search), and record each site as fixed or exempt with its bound. A reviewer then checks the enumeration instead of rediscovering one site per round.

## Evidence

- aspect: chat_history_analysis - loop-backs TASK-22, TASK-23 (23a640 plus one sibling), TASK-24 (family sweep)
- aspect: plan_efficiency - max_phase_token_share 0.57 (6-finalize), 1.09M tokens per deliverable
- aspect: llm_to_script_opportunities - overflow-family inventory would have collapsed four rounds into one
