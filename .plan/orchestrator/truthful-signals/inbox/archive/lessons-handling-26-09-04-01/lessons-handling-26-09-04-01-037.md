envelope_version=1
sender_type=orchestrator
sender_id=lessons-handling-26-09-04-01
epic=truthful-signals
kind=candidate-lesson
created=2026-09-09T07:59:30Z

component=plan-marshall:build-maven
category=bug

# A mutating quality profile legitimately dirties the worktree, but every clean-tree assertion reads that dirt as a contract violation or as external interference

⛔ **RELOCATED FROM THE WRONG STORE — this is a MOVE, not a new report.** It was filed as lesson
`2026-09-08-15-001` in **Token-Sheriff's** lessons store, whose repo does not own the `plan-marshall` bundle.
It is written here first and removed there second (integrate-then-remove), so exactly one copy
exists at every point and none exists in two places.

Origin: Token-Sheriff epic `lessons-handling-26-09-04-01`. Original id `2026-09-08-15-001`, created 2026-09-08, lifecycle `active` at the time of the move.
⚠ Nine such lessons accumulated because a plan overrode the `wrong_store` guard rather than
routing the lesson to the repo that owns the bundle — the mechanism is reported separately as
`lessons-handling-26-09-04-01-032`. Body reproduced verbatim below.

---

## Context

Observed in TokenSheriff plan `refresh-2a-coverage-priorities`, 2026-09-08. Confirmed by the operator
as intended project behaviour: *\"the mutating of pre-commit is correct.\"*

TokenSheriff's `-Ppre-commit` profile deliberately binds two **mutating** executions —
`rewrite:run` (OpenRewrite, with `JUnit5BestPractices`, `OrderImports`,
`ShortenFullyQualifiedTypeReferences` and others active) and `license:format` — alongside the
`assert-no-rewrite-changes` `dryRun` assertion that polices them. PR #720 exists specifically to
order the assertions *before* the mutations.

So running the canonical `quality-gate` command **rewrites source files in the working tree**. That
is correct and wanted. Nothing in plan-marshall knows it.

## Impact — a confident, wrong diagnosis, twice

Every clean-tree checkpoint in the lifecycle treats a dirty tree after a build as a defect:

- the post-refine / post-outline `git status --porcelain` contract assertions
  (`workflow/planning.md`, `planning-outline.md`),
- `manage-status transition`'s `worktree_dirty_at_boundary` refusal,
- phase-5's Step 10 commit-ownership invariant,
- the `phase_handshake` `worktree_dirty` invariant.

None of them can distinguish *\"a dispatched agent wrote where it must not\"* from *\"the quality gate
did its job.\"* In this run the orchestrator found the tree dirty twice after gate runs, concluded
the user's IDE was reformatting files, **reverted the changes both times**, and told the user to
change their IntelliJ settings. The reverts then turned the `assert-no-rewrite-changes` gate RED,
because the reverted state is exactly the state the recipe wants changed. The true author was the
project's own gate. The wrong diagnosis was stated to the user with confidence before any check
was run against the build's own output.

The tell that was available and missed: `target/rewrite/rewrite.patch` is byte-identical to the
\"mystery\" diff, and the dryRun log names the file and the recipe chain.

## Directive

Teach the build layer which canonical commands mutate the tree, and teach the assertion layer to
ask.

1. `build-maven` (and its siblings) should report, in the build result TOON, whether the invoked
   command is **tree-mutating** — derivable from the resolved profile's bound goals
   (`rewrite:run`, `license:format`, `spotless:apply`, `formatter:format`, …).
2. Every clean-tree assertion should consult that signal before classifying dirt. Post-mutating-build
   dirt is an expected outcome to be **committed or reported**, never a contract violation and never
   evidence of an external editor.
3. Absent the signal, the diagnostic order must be: check `target/rewrite/rewrite.patch` and the
   build log's own dryRun output **first**; blame an editor only after the build has been ruled out,
   and say which check ruled it out.

Never revert a file to resolve unexplained dirt without first establishing the author. A revert of
mandated formatting is invisible until a later gate run, and it fails the gate for a reason that
points at the wrong file.
