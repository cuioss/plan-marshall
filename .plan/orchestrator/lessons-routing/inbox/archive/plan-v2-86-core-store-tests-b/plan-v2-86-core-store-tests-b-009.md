envelope_version=1
sender_type=plan
sender_id=plan-v2-86-core-store-tests-b
epic=lessons-routing
kind=candidate-lesson
created=2026-11-06T11:21:33Z

# build-server wait logs the same 'job_status=running' line dozens of times with one timestamp

- component: plan-marshall:build-server-client
- category: bug
- source plan: plan-v2-86-core-store-tests-b (pm-mcp-core, PR 301)

The plan work log holds long bursts of identical 'build-server wait result ... job_status=running' lines with the same hash and second, for example about 60 copies at one second for the coverage verify job and about 77 for a later test job. The work log of the plan grew to about 6000 entries (~1 MB), which makes it hard to read. A long-poll wait should log one line per real poll, or collapse repeats of the same state.

Evidence: work log of plan-v2-86-core-store-tests-b, entries around 2026-11-06T08:27:38Z (job 0f7ba1e8) and 10:24:58Z (job 01c56528).
