envelope_version=1
sender_type=orchestrator
sender_id=lessons-handling-26-09-04-01
epic=truthful-signals
kind=candidate-lesson
created=2026-09-04T07:45:52Z

# Finding: the build wrapper's `tests_run` reports only the LAST summary line, so a full `verify` looks like it ran 7 tests

> **Relayed from Token-Sheriff.** Source epic `lessons-handling-26-09-04-01`, original lesson `2026-09-03-18-001`. Body reproduced verbatim below the provenance line.

**Proposed component**: `plan-marshall:build-maven` (build wrapper result parsing)
**Category**: `bug` — a reported count that is not the count it names

⛔ **Why this belongs in the truthful-signals collection**: the wrapper does not fail or warn — it reports a number that a reader has every reason to read as the suite total, and on a multi-module `verify` that number is whichever summary happened to print last. A caller comparing `tests_run` across two runs to detect a lost test would be comparing noise.

---

# The build wrapper's `tests_run` reports only the last summary line

## What was observed

Two runs against the same unchanged worktree, both green:

| Command | Reported `tests_run` | Wall time |
|---|---|---|
| `test -pl token-sheriff-client` | 724 | 93s |
| `verify -pl token-sheriff-client` | **7** | 26s |

The obvious reading — that `verify` runs a hundredfold-smaller slice than `test`
— is wrong. Reading the underlying Maven log shows both phases ran the same
suite:

```
line 228: [INFO] Tests run: 724, Failures: 0, Errors: 0, Skipped: 0   <- surefire total
line 293: [INFO] Tests run: 7,   Failures: 0, Errors: 0, Skipped: 0   <- failsafe total
```

The wrapper's parser takes the **last** `Tests run:` summary in the log. On a
`test` invocation that is surefire's total; on a `verify` invocation failsafe
runs afterwards, so its much smaller integration-test total overwrites it.

## Why it matters

`tests_run` is the field an agent or a human uses to answer "did the gate
actually exercise anything?". Under-reporting it by two orders of magnitude
inverts that signal: the more complete gate (`verify`, which adds lint and
integration tests) reports the *smaller* number, so `verify` looks like the
weaker check when it is the stronger one. An agent applying the ordinary
heuristic "a suspiciously small test count means the tests did not run" will
chase a non-existent regression, or — worse — will accept a genuinely empty
surefire run on some other module because it has learned to discount small
counts on `verify`.

Note the accompanying `tests_population: measured`. That field asserts the
count is a real measurement rather than an unknown, which is exactly what makes
the wrong number credible.

## How to check it

Do not trust `tests_run` alone to decide whether a phase executed a suite.
Read the Maven log the wrapper points at via `log_file` and look at **every**
`Tests run:` total line, not the last one. A `verify` run has at least two.

## Correct fix (upstream)

The parser should sum the per-plugin totals it finds, or report them
separately (`surefire_tests_run` / `failsafe_tests_run`), rather than letting
the last match win. This lives in the plan-marshall `build-maven` wrapper, not
in this repository — filed here because the store for this checkout does not
own that bundle.
