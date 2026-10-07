envelope_version=1
sender_type=orchestrator
sender_id=api-sheriff-deployment-configurability
epic=truthful-signals
kind=candidate-lesson
created=2026-09-11T13:53:45Z

component=plan-marshall:build-maven
category=bug

# build-maven digests are lossy: last-module tests_run, a `[deprecation]` regex character class that mislabels nearly every line, epilogue lines filed as findings, and targeted -Dtest reds sibling modules

⛔ **RELOCATED FROM THE WRONG STORE — a MOVE, not a new report.** Two lessons filed in **API-Sheriff's**
store (`cuioss/API-Sheriff`, `.plan/local/lessons-learned/`), whose repo does not own the `plan-marshall`
bundle. Written here first and removed there second (integrate-then-remove), during the
`deployment-configurability` epic's lessons intake on 2026-09-11. Bundled because both are defects of
the same component. Original bodies verbatim below the verification block.

Origin ids: `2026-08-29-16-003` (created 2026-08-29), `2026-09-10-22-003` (created 2026-09-10).

## Verification at plan-marshall `origin/main` 356973d80 (read-only pass, 2026-09-11)

| Claim | Verdict | Evidence | Already tracked |
|---|---|---|---|
| (a) `tests_run` is the LAST reactor module's surefire count, not the reactor total (202 vs 1886) | STILL-VALID | `_maven_cmd_parse.py:164` `m = matches[-1]`; shared helper `_build_parse.py:596` rests on the false premise "the final one is the aggregate" — Maven prints no reactor-wide total | PLAN-TRUTH-122 D3 (staged); queued `lessons-handling-26-09-04-01-041`, `-027` |
| (b) background task exit 0 while TOON says `status: error` | BY DESIGN | `tools-script-executor/standards/exit-code-convention.md:45`; `plugin-script-architecture/standards/output-contract.md:81` | n/a — no action |
| (c) `module-tests` budget 330 s vs `verify` 558 s for the same suite, so the subset rung times out | PARTIALLY FIXED | fixed: unmeasured falls back to `orchestrator` (`_cmd_client_build.py:401`), `timeout` is its own status (`_build_result.py:159`). Open: budgets derived per command independently (`:366-376`); 330 = Maven floor 300 (`_maven_execute.py:28`) + 30; nothing enforces subset ≤ superset | PLAN-TRUTH-078 (shipped #1193) diagnosed the inversion; its landing closed 0 of 9 gaps |
| (d) epilogue boilerplate filed as `severity: error` findings; a PASSING `Tests run: 27, Failures: 0` line filed as `test-failure`; genuine failures and compiler errors categorised `deprecation_warning` | STILL-VALID — **root cause NEW** | no epilogue filter, every `[ERROR]`/`[WARNING]` becomes a finding (`_maven_cmd_parse.py:106-130`); any line containing `'tests run:'` → `test_failure` regardless of counts (`_build_jvm_patterns.py:33`); ⛔ `_is_regex_pattern` (`_build_parse.py:490`) treats the literal `'[deprecation]'` (`_build_jvm_patterns.py:54`) as a **regex character class** matching any single letter of d/e/p/r/c/a/t/i/o/n — so nearly every line nothing earlier caught lands in `deprecation_warning` | PLAN-TRUTH-122 §8.4 fold (staged), from consumed `findings-from-cui-http` |
| (e) `-Dtest=X` with `-pl M -am` reds every sibling module with `No tests were executed!`; dropping `-am` tests stale installed artifacts | STILL-VALID, **UNTRACKED** | `_maven_cmd_discover.py:787,810` emits `test -pl X -am`; `failIfNoSpecifiedTests` appears nowhere under `marketplace/bundles`; `build-maven/SKILL.md:39` and `standards/maven-impl.md:53-55` are silent | none found (queued `-033` uses `-Dtest` for a different mechanism) |

**What this message adds beyond existing tracking:** the `[deprecation]` character-class root cause for
the whole miscategorisation; the multi-module variant of (a) beside the surefire/failsafe one already
tracked; the passing-line misfile; and (e) in full. Suggested remedy for (e): when a targeted
`-Dtest` rides a reactor built with `-am`, append `-Dsurefire.failIfNoSpecifiedTests=false` (never the
blunter `-DfailIfNoTests=false`, which also silences the targeted module) and document the pitfall.

Local residue in API-Sheriff (not this store's concern, recorded for completeness): `CLAUDE.md:38-39` and
`AGENTS.md:44` give the targeted-test example without `-am`. Tracked in the API-Sheriff
`deployment-configurability` epic.

---

## Original lesson `2026-08-29-16-003` (verbatim)

id=2026-08-29-16-003
component=maven-build
category=anti-pattern
status=active
created=2026-08-29

# Build-report digests are lossy, each in its own way (tests_run scope, exit-code vs status, timeout-is-not-failure, parser noise) - read the primary artifact

`CLAUDE.md` already states the principle: *"A successful build is not evidence that work
happened."* This lesson collects the concrete instances of it, all in the **reporting layer**
rather than in the build itself — the build was fine; the summary of the build was not.

## Instance 1 — `tests_run` is the last module's number, not the reactor's

The Maven build executor's TOON payload reported `tests_run: 202` for a full-reactor
`verify`. That number is the **last module's surefire summary**, not the reactor total.
`api-sheriff` alone runs **1886** unit tests. A reader treating `tests_run` as "how many
tests this build ran" under-counts by an order of magnitude, and — worse — cannot tell
whether the module they actually care about ran at all, because a module that was skipped
and a module that ran look identical once only the tail is reported.

**Corrective action:** never quote `tests_run` as a reactor-wide test count. When the count
matters (a PR test-plan line, a coverage claim, "did my new tests execute?"), open the
`log_file` from the executor payload and read the per-module surefire summaries. Quote the
number you read there, and name the module it belongs to.

## Instance 2 — a background task exited 0 while the payload said `status: error`

A build dispatched as a background task returned **exit code 0** while the TOON payload it
produced carried `status: error`. The process-level exit code and the structured verdict
disagreed, and the process-level one is the one that is easy to glance at.

**Corrective action:** the executor's `status` field is the verdict; the process exit code
is not. Parse the TOON and branch on `status` / `errors[]` / `warnings[]`. Never conclude
"green" from a task completing, from a command exiting 0, or from the absence of visible
error text in a truncated log tail.

## Instance 3 (2026-08-31) — the resolved timeout budget truncates the suite, and `timeout` is not `failure`

`architecture resolve --command module-tests --module api-sheriff` returns
`bash_timeout_seconds: 330`, while `architecture resolve --command verify --module
api-sheriff` returns **558** — two rungs measuring the **same 1886-test suite** with a 1.7x
divergent budget. The suite needs roughly 540 s wall-clock, so the `module-tests` rung is
cut off mid-run and reports `status: timeout`.

The reporting trap is what `timeout` *means*. A timeout is **not a failing build** — it is
the absence of a verdict. No test result was reported, so it is evidence of neither pass nor
fail. Triaging it as a test failure manufactures findings about code that was never
evaluated, and — the inverse and worse — a caller that re-runs it as though it were flaky
will keep paying for a run that structurally cannot finish inside its own budget.

**Corrective action:** branch on `status: timeout` separately from `status: error`. A
timeout means *re-run with an adequate budget, then read the result* — never "the tests
failed", and never a blind retry at the same budget. When two canonical rungs cover the same
suite, treat a large divergence in `bash_timeout_seconds` as a calibration defect and
recalibrate the smaller one toward the larger.

## Instance 4 (2026-08-31) — the log parser files Maven epilogue boilerplate as error findings

Two failing `verify -pl api-sheriff -am` runs produced **34 findings**, of which only 13
carried any failure content. The other 21 were parser artifacts:

- **19** Maven epilogue boilerplate lines, each filed as its own `severity: error`
  `build-error` finding: the bare section headers `Failures:` and `Errors:`, `See ...
  surefire-reports`, `See dump files ...`, `To see the full stack trace ... -e switch`,
  `Re-run Maven ... -X switch`, `For more information ... articles`, `[Help 1] http://...`,
  `After correcting the problems ...`, and `mvn <args> -rf :api-sheriff`.
- **2** filed from a **passing** test-class summary line — `Tests run: 27, Failures: 0,
  Errors: 0, Skipped: 1 -- in DirectoryAssetSourceTest` — typed as `test-failure`.
- Separately, every genuine surefire failure line was categorised `deprecation_warning`,
  which is simply the wrong category.

A 2-test flake therefore presented as 34 blocking findings — a ~2.6x noise ratio — so the
findings gate reported a scale of breakage that did not exist, and each artifact cost an
individual triage `resolve` call.

**Corrective action:** when triaging build findings, read the `detail` body before believing
the count. Anchor on the surefire failure/error blocks and treat the Maven epilogue as
non-signal. On the producer side: stop parsing after the `[ERROR] Failures:` / `[ERROR]
Errors:` section terminator, require `Failures > 0` or `Errors > 0` before filing a `Tests
run:` summary line, and fix the `deprecation_warning` miscategorisation.

## The shape

Every instance is the same defect: **a summary artifact was read as if it were the
underlying fact.** The build tells the truth; the digest of the build is lossy, and each
digest is lossy in its own specific way — a count that ranges over less than you think
(1), a verdict that disagrees with its own exit code (2), a non-verdict that looks like a
verdict (3), a finding count inflated by non-findings (4).

Before relying on any reported figure — a test count, a coverage percentage, a pass/fail, a
findings count — ask *which artifact produced this number, and what does it actually range
over?* If the answer is not immediately known, go to the primary artifact (the reactor log,
the structured payload, the finding's own `detail` body) and read it.

---

## Original lesson `2026-09-10-22-003` (verbatim)

id=2026-09-10-22-003
component=maven-build
category=anti-pattern
status=active
created=2026-09-10

# A targeted -Dtest run with -pl -am reds sibling modules - pass -Dsurefire.failIfNoSpecifiedTests=false, never drop -am

## Observation

Running one test in a multi-module reactor has two invocations that both look right and are both
wrong, and the failure each produces is misleading in a different way.

**Shape 1 — `verify -pl <module> -am -Dtest=SomeTest`.** `-am` pulls in the module's upstream
dependencies, and `-Dtest` applies to **every** module in the resulting reactor. Surefire then fails
each sibling module that contains no test matching the pattern:

```text
No tests were executed!  (Set -DfailIfNoTests=false to ignore this error.)
```

The red module is not the module under test and has nothing to do with the change. Read
inattentively, this looks like the branch breaking an unrelated module.

**Shape 2 — dropping `-am` to avoid that.** Without `-am` the named module is compiled against
whatever sibling artifacts are already installed in the local repository. On a branch that changed a
sibling module, those artifacts are **stale**, so the build either fails to compile against an API
the branch just changed or — worse — succeeds against the old one and tests the wrong code.

## Directive

1. **Keep `-am` and neutralise the sibling failure**, rather than dropping `-am`:

   ```text
   verify -pl <module> -am -Dtest=SomeTest -Dsurefire.failIfNoSpecifiedTests=false
   ```

   `-am` is what guarantees the siblings are rebuilt from this branch's source. The extra property
   only says "a module with no matching test is not an error", which is exactly the intent.

2. **Never drop `-am` as a workaround for a sibling-module red.** A green obtained that way is a
   green against installed artifacts, not against the branch, and the "success is not evidence that
   work happened" rule applies verbatim.

3. **Read a `No tests were executed!` red by module, not by colour.** If the failing module is not
   the one named by `-pl`, this is the invocation defect, not a branch defect — fix the command,
   don't chase the module.

4. `-DfailIfNoTests=false` (the message's own suggestion) is the older, blunter spelling and disables
   the check globally, including for the module you actually targeted — so a typo in the test name
   passes silently green. `-Dsurefire.failIfNoSpecifiedTests=false` is the one to reach for.
