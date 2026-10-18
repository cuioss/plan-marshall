envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-18T09:56:32Z

component=plan-marshall:build-maven
category=bug
source=script-failure cluster, work log cab0da (2026-10-18T06:40:17Z, phase-5 TASK-29 after a build-server job timeout)

# `build-maven resolve-test-scope` is not a registered verb

## Observation

After a daemon build job for `test -pl pm-runtime -am` returned job_status=timeout (06:39:04), the phase-5 agent called `plan-marshall:build-maven:maven resolve-test-scope`. It was rejected: the registered verbs are check-warnings, coverage-report, discover, parse, rewrite-log, run and run-config-key. The agent then resubmitted the build, which succeeded.

## Hypothesis

Either a workflow passage about narrowing the test scope after a timeout names a verb the maven script lacks, or the executor is stale. Also notable: the build-server long-poll returned `timeout` for a module-test run the in-process path normally completes in about 5 minutes. Worth checking whether the daemon job timeout is shorter than the architecture-resolved bash_timeout for module-tests.
