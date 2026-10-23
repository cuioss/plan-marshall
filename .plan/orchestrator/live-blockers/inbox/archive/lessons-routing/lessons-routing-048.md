envelope_version=1
sender_type=orchestrator
sender_id=lessons-routing
epic=live-blockers
kind=finding
created=2026-10-23T08:22:58Z

# The declared footprint omits what the plan will touch

Severity: high. Bundle: **plan-marshall** (`phase-3-outline`, `phase-4-plan` Q-Gate, `manage-solution-outline`). Filed under RULING 2026-10-09 (a).

This is the class the orchestration standard measures as the dominant residual: about two thirds of the files a landing touched were never declared.

## Sources

- corpus `2026-10-10-20-006`
- inbox `pm-mcp-core-m2-m4-296`, `-297`, `-339`, `-369`, `-370`, `-371`, `-372`

## Consolidated statement

The outline treats a change as an edit of the named file, and the Q-Gate confirms the declared list instead of testing it against the tree. Six distinct misses recur:

1. **A deletion carries no referrer sweep.** D11 deleted `doc/plans/job-runner.adoc`; `slots-usage-and-budgets.adoc:15` links to it and `core/analysis/package-info.java` points at a removed section. Both were found only by the 4-plan `scope_criterion_validator` after an operator question.
2. **A rename or split misses the documents that restate the name.** D2 renamed/split call states; a content search then hit state-catalogue 07/04 and workflow-dsl 02/03, none of them in any deliverable. Carrying them into tasks later surfaced as a 20-file scope-creep warning.
3. **A removal misses consumers in every spelling.** D3 removed `PruneReason.RECIPE_OVERRIDE` / `AUTO_MERGE_OFF` while shipped `composition-rules.json` kept naming `recipe_override` / `auto_merge_off`, and two test classes still referenced the constants (both scheduled for later deliverables that depend on D3) — D3's own module-testing task could not have gone green.
4. **A counted or read population is not declared.** D11's criterion counted eight package files but listed seven; it read two plan documents that deliverables 6 and 7 create and declared neither.
5. **The developer guide of a changed package is omitted.** D8 changed `CompiledInvariants.check`'s signature, and `pm-workflow/doc/developer/workflow-unit.adoc`, which describes that call, was in no deliverable, although the project requires the developer doc of every changed package.
6. **A cross-module deliverable is declared against one module.** D9 declared `module: pm-workflow` while two of its five files live in `pm-core` and its own verification ran `test -pl pm-core -am`; task planning derives the build target from the module field. Separately, a `write-replace` target that does not exist was declared (`test/plan-marshall/.../test_finalize_step_plugin_doctor.py`) and a mapping row was added instead of correcting the path.

## What is asked

- On a delete or rename, run a content search for the file name and the section anchor (or the old symbol and its wire spelling) and put every referrer in the same deliverable, or state why it is excluded.
- On a removal, search main **and** test sources for every spelling of each removed identifier; a deliverable's module-testing task must be able to go green on its own.
- Declare every file a success criterion counts or reads, including files created by earlier deliverables.
- Declare `{module}/doc/developer/{package}.adoc` for every package whose code a deliverable changes.
- Derive a deliverable's `module` from the owning module of every affected file and split per module where they disagree; when `which-module` returns null because the file lives outside the repository, declare it an operator/mixed step with module `none`.
- Verify every `write-replace` path exists before the outline declares it, and have the module-mapping validator check existence before offering "add a mapping row" as a resolution.

## Evidence

As recorded by the senders. Not re-verified against HEAD in this run.
