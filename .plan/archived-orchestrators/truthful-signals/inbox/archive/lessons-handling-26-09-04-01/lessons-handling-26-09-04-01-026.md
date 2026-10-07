envelope_version=1
sender_type=orchestrator
sender_id=lessons-handling-26-09-04-01
epic=truthful-signals
kind=candidate-lesson
created=2026-09-08T10:39:04Z

component=plan-marshall:build-maven
category=bug

⛔ **FOLD REQUEST — recurrence of `lessons-handling-26-09-04-01-013.md`**, which reported that widening a module-scoped `test-compile` by deleting the module argument cannot resolve a sibling test-jar. This is the **third** plan in this repository to hit it and the **first to explain why the widening is unsound in general** rather than recording it as un-gated: dropping `-pl <module>` also drops `-am`, and `-am` is what builds the upstream module far enough in the same reactor pass. Please fold onto whatever item absorbed `-013`.

Relayed from Token-Sheriff PLAN-12 (`pre-commit-gate-cannot-fail-by-construction`, PR #720 / `e52ec470`), Q-Gate finding `70edba`. ⚠ Note the plan ALSO recorded that the dimension was covered by another route — Maven's `verify` lifecycle runs test-compile with correct reactor ordering, and whole-tree `verify -Ppre-commit` passed green — so the gap is in the widening strategy, not in the coverage.

# Candidate lesson: whole-tree widening by argument removal is unsound for a Maven reactor

**Component**: `plan-marshall:phase-6-finalize` (`pre-push-quality-gate`)
**Signal class**: Q-Gate finding (`signal_qgate_pending_count`)
**Evidence**: Q-Gate finding `70edba`, resolved `taken_into_account` and deferred to plan-marshall.
**Landed in**: PR #720, squash commit `e52ec470` on `main` (cuioss/TokenSheriff).

## Observation

`pre-push-quality-gate` obtains its whole-tree verification by taking the module-scoped
executable and removing the module argument. Under Maven the module-scoped executable is

```text
test-compile -pl <module> -am
```

so removing "the module argument" also drops `-am`. `-am` (`--also-make`) is what builds the
upstream modules the target depends on — in this project it is what produces the `validation`
test-jar that downstream modules compile against.

## Result observed

The widened form failed in ~11 s with 20 missing-package errors, all in modules **outside**
the branch diff. The same tree passed green under the whole-tree `verify -Ppre-commit`
invocation. So the widened command reported a failure the tree does not have — a false red on
a gate whose whole purpose is to be trustworthy before a push.

## Why this is not a project-local fix

The rule "widen by removing the module argument" is written at the gate level and is
build-system agnostic, but its soundness is not. For a reactor build the module selector and
the upstream-inclusion flag are two separate arguments that arrive together; dropping both is
not the same operation as dropping the scope. Any build system whose module scoping carries a
companion dependency-closure flag has the same defect.

## Suggested direction (for orchestrator judgement)

Resolve the whole-tree command through the build system's own canonical-command surface rather
than by textual argument subtraction from the module-scoped form. This project's own
`verify -Ppre-commit` is the proof that a correct whole-tree command exists and is reachable.
