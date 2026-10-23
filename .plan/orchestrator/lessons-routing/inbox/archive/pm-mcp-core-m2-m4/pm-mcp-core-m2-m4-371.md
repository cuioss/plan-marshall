envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-19T18:47:04Z

component=plan-marshall:phase-3-outline
category=anti-pattern

# Removal sweep missed test files that reference the removed constants

Source: Q-Gate 4-plan finding bfe299 (scope_criterion_validator under_coverage, deliverable 3; resolved in run), plan plan-70-plan-instance-alignment.

The success criterion "a header or composition cause with recipe_override, auto_merge_off or question_expired is refused" was checked by a content search for the removed constants. It found `CompositionRuleEvaluatorTest` (4 refs) and `CompositionRulesTest` (1 ref) outside D3's affected files; both were rewritten only by D4/D5, which depend on D3. D3's own module_testing task could not have gone green. The earlier sequencing note (9bd12c) covered only the shipped JSON, because its sweep searched the lowercase wire names and missed the uppercase constants.

## Rule

Before closing the affected-files list of a removal deliverable, run the content search for each removed identifier in every spelling it has (constant, wire name) over main AND test sources, and put every hit into that deliverable - minimal rewrites now, extensions in the later deliverables. A deliverable's module_testing task must be able to go green on its own.
