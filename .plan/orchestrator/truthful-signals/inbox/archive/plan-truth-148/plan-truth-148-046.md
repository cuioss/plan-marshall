envelope_version=1
sender_type=plan
sender_id=plan-truth-148
epic=truthful-signals
kind=candidate-lesson
created=2026-09-14T21:04:26Z

# Candidate lesson: a cross-module implementation edit was left unexercised by its sibling test task

- source_signal: qgate / 4-plan (module_mapping_validator)
- record_id: da919a
- component: pm-plugin-development (edit) vs plan-marshall (test scope)
- file: marketplace/bundles/pm-plugin-development/skills/ext-self-review-plan-marshall/SKILL.md
- resolution: taken_into_account — cross-module routing accepted as intentional and recorded as a declared decision

## What happened

The implementation task wrote two files in two different modules; the sibling module_testing task declared a test target in only one of them. The `pm-plugin-development` edit was therefore unexercised by module_testing. Accepted because that edit was a surfacer-contract documentation change with no separately testable behaviour, and the plan-marshall-module test exercises the workflow contract both edits serve.

## Candidate rule

When an implementation task spans modules, the paired test task's scope must either span them too or the cross-module routing must be DECLARED with the reason. The failure mode is silent: the test task reports green over the module it covers, and nothing in the record says a second module's edit went unexercised.
