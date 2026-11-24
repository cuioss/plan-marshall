envelope_version=1
sender_type=orchestrator
sender_id=libraries-initial-implementation
epic=lessons-routing
kind=candidate-lesson
created=2026-11-24T12:07:24Z

component=plan-marshall:phase-3-outline
category=improvement
title=phase-3-outline: every affected file of a deliverable belongs to the module the deliverable declares, one deliverable per module
source_lesson=2026-11-20-07-002
source_repo=git-document-repository (epic libraries-initial-implementation)
source_created=2026-11-20

# phase-3-outline: every affected file of a deliverable belongs to the module the deliverable declares, one deliverable per module

# Candidate lesson: a deliverable declared one module while its affected files spanned several, caught in two phases

- Source signal: plan implement-plan-06-build-guards (inbox implement-plan-06-build-guards-002, -003, -006, -007), Q-Gate findings 46d99a and d77466 (phase 3-outline, architecture constraints) and df6eb6 and 905254 (phase 4-plan, `module_mapping_validator`), all resolved `taken_into_account`.

## What happened

- Deliverable 2 declared `module: git-core` but its affected files included `DomainTermAbsenceTest.java` in `git-worktrees` and in `git-testing`; task planning resolves module-scoped build and test commands and skills from that field, so a `module_testing` task narrowed to `git-core` would not have run the other two tests. It was split into one deliverable per module.
- Deliverable 3 declared `module: git-core` but two of its five affected files were `git-worktrees/src/main/resources/META-INF/native-image/...`; module-scoped routing and the jar packaging check would have missed that half. It was split the same way.
- The 4-plan mapping validator then caught the same family again: a `module_testing` task declared `git-worktrees/pom.xml` while its sibling implementation task declared the root `pom.xml` (the module-layering rule), and a test task covered two modules its sibling implementation task did not change. Fixing the declarations at outline time would have avoided both rounds.
- A build-rule deliverable proven by a deliberate negative run (switch a dependency scope, expect the enforcer failure, revert) is verified inside the implementation task; it is not a separate `module_testing` task in another module.

## Candidate rule

Every affected file of a deliverable belongs to the module the deliverable declares, and a per-module check repeated across modules is one deliverable per module. The outline self-check (see lesson `2026-11-18-18-001`) should compare each deliverable's declared module with the module of every affected path before the Q-Gate, so the 4-plan validator does not find the same defect a second time.
