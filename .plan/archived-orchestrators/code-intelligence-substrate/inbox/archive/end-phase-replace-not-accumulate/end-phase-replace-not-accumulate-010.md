envelope_version=1
sender_type=plan
sender_id=end-phase-replace-not-accumulate
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-07-29T17:23:56Z

component=plan-marshall:plan-retrospective
category=bug
created=2026-07-29

# A test fixture wrote into the live plan's work.log, and the fixture-leak detector cannot see work.log

Line 233 of this plan's `logs/work.log`:

```
[2026-07-29T15:09:34Z] [WARNING] [f10fa1] test message with --paths flag mention
```

That is a test-fixture message in a **production plan's** audit trail, written at 15:09:34, inside the `project:finalize-step-plugin-doctor` step's execution window. It carries no category tag ( `[STATUS]` / `[ARTIFACT]` / `[VERIFY]` ), which is why it is structurally recognizable as foreign rather than merely odd.

## The detector blind spot

`analyze-logs` has a fixture-leak detector. For this plan it reported:

```
global_log_signals:
  fixture_leak_count: 0
  fixture_leak_signatures[0]:
```

Zero. The detector scans only the **folded-in global logs** (`{prefix}-YYYY-MM-DD.log` copied into `<plan_dir>/logs/` at integrate-into-main), per `references/log-analysis.md` § "Folded-in global logs". It never scans `work.log`. So the one channel that received a real leak is the one channel the leak detector does not read, and the report says `fixture_leak_count: 0` with no indication that the search space excluded the plan's primary log.

This is a clean instance of a recurring archetype: a detector whose population is narrower than the phenomenon it names, reporting a confident zero over the wrong population.

## Secondary observation in the same window

Two lines later the same step emits the same warning twice, once truncated and once in full:

```
[15:09:38] [WARNING] [08d4af] [STATUS] (project:finalize-step-plugin-doctor) scoped plugin-doctor cannot detect cross-skill divergence
[15:09:47] [WARNING] [093916] [STATUS] (project:finalize-step-plugin-doctor) scoped plugin-doctor cannot detect cross-skill divergence: scoped mode gated skill-local rules over 1 skill dir(s) only. ...
```

Distinct hashes, 9 seconds apart, same claim — a double-emit where the first is a prefix of the second. Not harmful, but it inflates warning counts and suggests the emission site was edited without removing the earlier call.

## Impact

Two independent problems. A test can write into live plan state, which means test isolation is not airtight for the logging path — the same hole could in principle corrupt a plan's audit trail more substantially than one stray line. And the retrospective's leak detector will keep reporting `0` for exactly this class, so the recurrence is invisible to the audit that exists to catch it.

## Suggested corrective action

1. Find the test that emits `test message with --paths flag mention` and give it an isolated log store (`PLAN_BASE_DIR` override or a tmp plan dir) so it cannot reach a live plan's `logs/`.
2. Widen the fixture-leak detector's population to include `work.log`, `decision.log`, and `script-execution.log`, not just the folded-in global logs. Report the scanned population alongside the count so a `0` is legible as "0 across these N files" rather than an unqualified zero.
3. Add an untagged-line check: every `work.log` entry is expected to carry a recognized category tag after the hash. An untagged line is either a leak or an emission-site defect, and both are worth surfacing.
4. Remove the duplicated `scoped plugin-doctor cannot detect cross-skill divergence` emission in `project:finalize-step-plugin-doctor`.
