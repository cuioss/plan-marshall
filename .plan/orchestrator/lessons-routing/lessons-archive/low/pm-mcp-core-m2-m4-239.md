envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-13T17:39:57Z

# Candidate lesson (Q-Gate finding 63c5ba, 4-plan, taken_into_account): "pattern appears only here" success criterion contradicted by a pre-existing pattern

**Source plan:** plan-21-entity-addressing
**Signal source:** Q-Gate finding 63c5ba (phase 4-plan, severity warning, resolution taken_into_account)
**Suggested component:** plan-marshall:phase-3-outline (success-criterion authoring) / pm-mcp-core project knowledge

## Finding

Deliverable 3's success criterion required that the entry_id, entity and module_id patterns appear in EntityIdGrammar.java and nowhere else below pm-core/src/main, pm-runtime/src/main or pm-providers. A content search found the module_id pattern `[A-Za-z0-9][A-Za-z0-9_.-]{0,56}` already present in `pm-core/src/main/java/de/planmarshall/core/store/ProjectEnrolment.java` inside `BUDGET_KEY` (the @module suffix of a command budget key). The criterion could not hold as worded, and the claim that EntityIdGrammar is the only place of the grammar checks was contradicted.

## Resolution in run

Taken into account: the criterion was read with a documented pre-existing exclusion (ProjectEnrolment.BUDGET_KEY stays untouched; the overlap is recorded in ADR 009). The entry_id and entity patterns remained unique to EntityIdGrammar at that point. Note that the uniqueness of the entry_id grammar was later broken by sibling plan #51 (core.store.EntryId), see the separate candidate on sibling-landing re-checks.

## Why it may be lesson-worthy

"Only here / nowhere else" success criteria were written without a content sweep of the existing tree. An outline that authors a uniqueness criterion should run the content search at outline time (architecture search --content) and name pre-existing occurrences as explicit exclusions up front, instead of leaving the plan-phase Q-Gate to discover them.

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `plan-21-entity-addressing-006.md` from plan plan-21-entity-addressing (PLAN-21, #54; Claude Code)
