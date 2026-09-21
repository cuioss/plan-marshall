envelope_version=1
sender_type=orchestrator
sender_id=lessons-handling-26-09-04-01
epic=truthful-signals
kind=candidate-lesson
created=2026-09-08T05:58:26Z

component=plan-marshall:build-maven
category=bug

⛔ **FOLD REQUEST — recurrence of `lessons-handling-26-09-04-01-006.md`** (the build wrapper's `tests_run` reporting only the last summary line), already filed here. This is an independent re-observation at much larger scale: `tests_run=0` with `tests_population=measured` over **3,048 passing tests**, reproduced on three separate builds. Please fold rather than open a second item.

Relayed from Token-Sheriff PLAN-07 (`test-signal-and-assertion-integrity`, PR #715 / `8f3b8aee`), finding `6c8413`.

# Candidate lesson: a measured zero must be measured — build wrapper reported tests_run=0 over 3048 passing tests

Source finding: `6c8413` (bug, severity warning) in plan `test-signal-and-assertion-integrity`.
Component: `plan-marshall:build-maven`.

## Cross-repo routing note

This component is owned by the plan-marshall repo, whose lessons store is a different
repository. `manage-lessons` refused the local file with `error=wrong_store`, and that
refusal is CORRECT. Do not re-file it from this project with `--allow-foreign-store`;
carry it to the plan-marshall repo instead.

## Observation

Invocation: `plan-marshall:build-maven:maven run --command-args 'verify -Ppre-commit'`,
routed through marshalld (`mechanism=daemon_longpoll`, job `2666b5ac19ac432eac8df85dddd56037`).

Wrapper reported: `status=success`, `exit_code=0`, `duration_seconds=1459`, `tests_run=0`,
`tests_population=measured`, `analyses_examined='compile, lint, test'`, and the human line
"green build: analyses examined: compile, lint, test; 0 test(s) executed".

Ground truth from the underlying maven log: BUILD SUCCESS across all 15 reactor modules in
24:12 min, 3048 tests / 0 failures / 0 errors / 0 skipped, summed over the 11 per-module
`Tests run:` summary lines. Reproduced on three separate whole-tree builds in this run.

## Proposed rule

`tests_population` is the load-bearing field, not `tests_run`. `measured` ASSERTS the count
was taken, so a consumer is entitled to read the zero as a real zero and go hunting an
un-gated condition that does not exist. A parser that finds no per-module `Tests run:`
lines must report `tests_population=unknown` — a declared unknown is honest, a measured
zero over an unread population is a fabricated measurement. Generally: a summariser that
cannot establish a count must say so rather than emit its initialiser.

## Suggested fix

Parse and sum the per-module `Tests run: N, Failures: F, Errors: E, Skipped: S` reactor
summary lines; fall back to `tests_population=unknown` when the parse matches nothing.

## Negative control any fix must pass

Run a build with tests skipped and require `tests_population=unknown` (not a measured
zero), and a normal build and require the summed count to match the reactor log.
