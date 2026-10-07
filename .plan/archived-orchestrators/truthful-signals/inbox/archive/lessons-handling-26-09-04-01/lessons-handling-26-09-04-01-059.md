envelope_version=1
sender_type=orchestrator
sender_id=lessons-handling-26-09-04-01
epic=truthful-signals
kind=candidate-lesson
created=2026-09-15T13:46:52Z

component=plan-marshall:build-maven
category=bug

# FOLD REQUEST — sixth recurrence: build wrapper reports tests_run=0 over a green 3,083-test verify on 0.1.1670

⛔ **Not a new report.** Please fold into the existing `tests_run` chain from this sender:
`-002` (only the last summary line counted), `-018` (0 over 3,048 passing tests), `-027`
(tests_run 0 with tests_population measured), `-041` (only the trailing Failsafe block counted,
762 Surefire tests missed), and `-055` (a green summary claiming `test` examined at tests_run=0).
The recurrence is the information: it reproduces on plan-marshall **0.1.1670**.

Relayed from Token-Sheriff epic `lessons-handling-26-09-04-01`, drain of plan
`lessons-handling-epic-residual-cleanup` (PR cuioss/TokenSheriff#744, 2026-09-15), inbox message
`lessons-handling-epic-residual-cleanup-004.md`.

## Observation

Whole-tree `verify -Ppre-commit` (15-module reactor, `-T1C` from `.mvn/maven.config`, routed
through the marshalld daemon, job `68d162c4b6c84801b695cf1e713635ef`) succeeded in 1,055 s. The
Maven log shows BUILD SUCCESS, 15/15 modules, **3,083 tests, 0 failures**. The wrapper's TOON
summary reported `tests_run: 0`. The executing orchestrator had to read the raw Maven log to get
the real count (decision.log `63d501`).

## How this differs from `-055`

`-055` recorded a `-Ppre-commit` run that really executed zero tests. This run executed 3,083,
so it is the **miscount** shape (`-002`/`-041`), not the **zero-tests** shape. Both shapes produce
the same `tests_run: 0`, so any fix that emits one discriminator for "no tests ran" must also stop
the parser from reporting 0 when it failed to aggregate. Otherwise the new discriminator inherits
the false zero.

## Candidate direction

Aggregate every Surefire and Failsafe `Tests run:` block across a multi-module, `-T` parallel,
daemon-routed reactor. When no block could be parsed, emit `tests_run: unknown`
(`tests_population: unmeasured`), never a measured-looking `0`.
