envelope_version=1
sender_type=orchestrator
sender_id=lessons-handling-26-09-04-01
epic=truthful-signals
kind=candidate-lesson
created=2026-09-15T13:46:52Z

component=plan-marshall:build-maven
category=bug

# Maven build-output parser files the failure-trailer boilerplate as blocking deprecation_warning errors

Relayed from Token-Sheriff epic `lessons-handling-26-09-04-01`, drain of plan
`lessons-handling-epic-residual-cleanup` (PR cuioss/TokenSheriff#744, 2026-09-15), inbox message
`lessons-handling-epic-residual-cleanup-005.md`. The orchestrator confirmed the cited log entry
exists in the archived plan before relaying.

## Observation

After a failing `verify -Pcoverage` run (a JaCoCo `check` on `benchmarking-common`), the build
parser filed Maven's standard failure-trailer advice lines as pending build-error findings, with
category `deprecation_warning` and severity `error`:

- `Re-run Maven using the -X switch to enable full debug logging.`
- `[Help 1] http://cwiki.apache.org/confluence/display/MAVEN/…`
- `mvn <args> -rf :<module>`

There were six of these, plus three genuine coverage findings that duplicated Q-Gate findings
already filed for the same JaCoCo check. `pending_findings_blocking_count` reached 9, and each had
to be suppressed or accepted by hand (decision.log `3dcaec`: "786a61/37086c/c23894/81b0d3/7b88a0/636e6d
suppressed (Maven trailer boilerplate mis-filed by the build parser as deprecation_warning errors)").

## Why it matters

Advice text is not a diagnostic. Filing it as a blocking error inflates the triage load with
guaranteed false positives. Classifying an unrecognized `[ERROR]` line as `deprecation_warning`
also puts a wrong category on it, and triage routing uses that category.

## Candidate direction

- Exclude Maven's `[ERROR]` failure-trailer block from finding extraction.
- Do not default an unrecognized `[ERROR]` line to `deprecation_warning`. Use an explicit
  `unclassified` category, or do not file it.
- Deduplicate build-error findings against Q-Gate findings already filed for the same check. See
  relay `-062` for the fan-out: one JaCoCo check produced five findings.
