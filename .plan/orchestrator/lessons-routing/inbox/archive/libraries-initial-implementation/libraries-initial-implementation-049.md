envelope_version=1
sender_type=orchestrator
sender_id=libraries-initial-implementation
epic=lessons-routing
kind=candidate-lesson
created=2026-11-24T12:07:31Z

component=plan-marshall:plan-marshall
category=improvement
title=ask the owner gates that refine names before dispatching outline, not after a full outline pass
source_lesson=2026-11-22-13-004
source_repo=git-document-repository (epic libraries-initial-implementation)
source_created=2026-11-22

# ask the owner gates that refine names before dispatching outline, not after a full outline pass

# Candidate lesson: ask the owner gates that refine names before outline runs, not after a full outline pass

- Source signal: plan-retrospective of plan-09-store-release-index-listeners (inbox plan-09-store-release-index-listeners-021; chat-history and plan-efficiency aspects).

## What happened

Refine named two owner gates (the GDR-NFR-1 measuring tool and the step-refusal outcome) and wrote them into the Clarified Request, because the refine leaf cannot ask the operator. The orchestrator did not ask them. Outline then ran in full, batched four owner questions in `outline_prompt`, and had to run a second time with the answers. The operator picked the non-recommended option (JOL), so the second outline run added two affected files and rewrote Dependencies and Risks. 3-outline cost 433,468 tokens and 12m12s over the two passes.

## Root cause

Owner gates surfaced by refine have no orchestrator hand-off between refine and outline: they wait for outline, which asks them only after a full pass built on assumed answers.

## Candidate rule

When the refine return names owner gates, the orchestrator asks them (one `AskUserQuestion` batch) before dispatching outline and passes the answers into the outline dispatch; outline keeps its own `outline_prompt` for questions it discovers itself. Owning component: `plan-marshall:plan-marshall` (the refine-to-outline hand-off).
