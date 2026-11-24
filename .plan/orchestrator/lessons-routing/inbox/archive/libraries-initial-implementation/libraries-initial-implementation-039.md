envelope_version=1
sender_type=orchestrator
sender_id=libraries-initial-implementation
epic=lessons-routing
kind=candidate-lesson
created=2026-11-24T12:07:26Z

component=plan-marshall:manage-architecture
category=bug
title=manage-architecture: which-module returns no module for resource-only paths under META-INF/native-image
source_lesson=2026-11-20-07-004
source_repo=git-document-repository (epic libraries-initial-implementation)
source_created=2026-11-20

# manage-architecture: which-module returns no module for resource-only paths under META-INF/native-image

# Candidate lesson: `architecture which-module` returns no module for resource-only paths under `META-INF/native-image`

- Source signal: plan implement-plan-06-build-guards (inbox implement-plan-06-build-guards-008), Q-Gate finding 5c711d (phase 4-plan, `module_mapping_validator`, deliverable 3), component `plan-marshall:manage-architecture`.

## What happened

`architecture which-module` returned `module: null` for all four `src/main/resources/META-INF/native-image/...` paths of the plan (two per module). The module-mapping validation therefore could not attribute a resource-only change to its module, which weakens the check exactly where a deliverable writes no Java. The same finding also noted that a module-testing task covered only the `git-core` metadata while the sibling implementation task wrote the `git-worktrees` files too, so those files had no test in their module.

## Candidate rule

Resolve a path under a module's `src/main/resources` (and `src/test/resources`) to that module through the module root, not through the Java source roots. A resource-only deliverable should be mapped and validated like any other; where a module cannot be resolved the validator should report `unresolved` rather than pass the pair. The project-level corollary: every shipped resource file has a test in its own module.
