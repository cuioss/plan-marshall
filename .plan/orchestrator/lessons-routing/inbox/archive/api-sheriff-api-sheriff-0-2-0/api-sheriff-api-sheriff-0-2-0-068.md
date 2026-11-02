envelope_version=1
sender_type=orchestrator
sender_id=api-sheriff-api-sheriff-0-2-0
epic=lessons-routing
kind=finding
created=2026-10-28T20:54:34Z

# Build daemon default job timeout is below a normal `-Pintegration-tests` run

Observed by `plan-v02-11-resource-exhaustion-test-home` while landing PR #534 in the API-Sheriff repository
(epic `api-sheriff-0-2-0`, plan-marshall plugin 0.1.2028, executor 0.1.2021).

- The build daemon's default job timeout is 1800 s. The local `verify -Pintegration-tests -pl integration-tests -am` run
  takes about 1830 s under load, so it only completes when the caller passes an explicit longer timeout.
- The failure is silent in the sense that matters: the run looks like an environment problem, not a missing option. The
  plan treated the local IT run as "environmentally blocked" and relied on CI's integration lane as the gate.
- Under heavy foreign machine load (1-minute load around 30) the whole-tree `test` run also failed twice in an unrelated
  HTTP/2 early-response reset test, which passed in isolation and on a re-run once the load dropped. This is the same
  load sensitivity as the existing project Watch; it is context, not a second finding.

Suggested direction: derive the default job timeout from the module's measured run time, or make the build-maven
`run` result name the daemon timeout when a job is killed by it, so the cause is not mistaken for an environment fault.
