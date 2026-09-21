envelope_version=1
sender_type=orchestrator
sender_id=api-sheriff-deployment-configurability
epic=truthful-signals
kind=candidate-lesson
created=2026-09-17T06:04:12Z

component=plan-marshall:build-server-client
category=improvement

# A killed build waiter is not a killed build: re-attach to the marshalld job by id, and treat a pre-test timeout as no-verdict rather than red

Routed by the API-Sheriff `deployment-configurability` orchestrator on 2026-09-17 while draining PLAN-26's (`refresh-failure-dispositions`, PR cuioss/API-Sheriff#314, squash `a475cff`) epic inbox. The originating plan filed these as `candidate-lesson` messages to its API-Sheriff epic; their remedy lives in the plan-marshall bundle, so they are relocated here — the routing this epic has used since 2026-09-11. Not re-verified against plan-marshall source by the orchestrator: each is a lead from one plan run. Original message bodies (envelope stripped) are verbatim below.

Origin messages: `refresh-failure-dispositions-004`.

⚠ **Recurrence of `api-sheriff-deployment-configurability-017`** (filed 2026-09-15 from PLAN-24, four harness kills, four re-attaches). This instance adds two facts that one did not carry: re-attachment is by JOB ID against the daemon (not a resubmit), and a `job_status=timeout` arriving BEFORE any test output is a no-verdict outcome that must not be classified as a failing build — job `dbbc60f9` timed out at 300 s against a native IT whose p50 is 1250-1800 s. Fold into the existing item rather than tracking twice.

---

## Original `refresh-failure-dispositions-004`

component=plan-marshall:build-server-client
category=improvement

# A killed build waiter is not a killed build: re-attach to the marshalld job instead of resubmitting a long native IT run

## What happened

The orchestrator ran the native `verify -Pintegration-tests` runs through the marshalld build server as background waits. Two events in this plan:

- **Waiter killed, build unaffected.** For job 2ead93783c7d427e8264814f4ac4cbeb, the harness killed the local wait process on low memory at about 266 s. The daemon-side build kept running. The orchestrator re-attached with a build-server wait on the same job id and got the real verdict: success, exit 0, 1255 s, BffRefreshReuseIT 3/0. Resubmitting would have thrown away about 20 minutes of native build and started a second IT stack.
- **No-verdict timeout.** Job dbbc60f98902441e929d3c4f7a7f44e1 reported `job_status=timeout` at 300 s, before any test ran. It gave no verdict, and the run had to be resubmitted (job abe890bd). Native IT runs in this repository take roughly 1250 to 1800 s.

## Rule

- When a background waiter disappears (harness kill, memory pressure, session hiccup), first query the job by id. Re-attach and wait. Resubmit only if the daemon job itself is failed or unknown.
- A `timeout` that arrives before any test output is "no verdict", not a failure of the change. Never classify it as red; check the budget the job ran under and resubmit with one that fits the native IT p50.
- The daemon job log (`~/.plan-marshall/marshalld/job-logs/{job_id}.log`) is the evidence for the verdict. Record the job id in the work log so a re-attach or a later provenance check can find it.

## Coverage note

The existing auto-memory "Local Gate Timeout Under Foreign Load" covers a gate clipped at about 1190 s under load. It does not cover waiter-process death or re-attaching by job id.

## Evidence

- Plan refresh-failure-dispositions, decision log 2026-09-16T15:07:34Z (waiter killed at about 266 s, re-attached); work log 2026-09-16T15:15:38Z and 15:29:15Z (dbbc60f9 timed out at 300 s before tests, no verdict).
