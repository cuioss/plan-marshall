envelope_version=1
sender_type=orchestrator
sender_id=api-sheriff-kidicap-gateway-requirements
epic=lessons-routing
kind=finding
created=2026-11-24T12:06:31Z

> Routed from API-Sheriff epic `kidicap-gateway-requirements` (repository cuioss/API-Sheriff) by its orchestrator on 2026-11-24, at the operator's direction ("move all plan-marshall related stuff" to this inbox). Facts below come from that epic's ledger unless a line says it was re-read in this run; plugin version in use there: 0.1.2184.

# finding: the CI abstraction cannot read push runs on `main`, so post-merge verification needs a raw `gh` call

Observation (API-Sheriff ledger, re-observed 2026-11-24): `ci checks status --head main` answers "no pull requests found", and a push to `main` has no PR, so the Maven Build and Integration Tests runs of a merge commit cannot be read through `plan-marshall:tools-integration-ci:ci`. `ci checks logs --run-id` works only when a run id is already known. `ci pr queue-state` reports `merge_group_run` as `found: indeterminate` when the run list reaches its bound of 50 runs with none for the PR ("older runs were not read"). Consequence: six merge commits' main-branch runs stayed unobserved in the ledger for up to 2 months until the operator ran a hand-written `gh run list --branch main --commit ...` script.

Capability gap: a read-only verb listing the runs of a branch or commit (workflow, event, status, conclusion, run id), plus a way to read a deploy-snapshot job's conclusion. The orchestrator's rule against calling `gh` directly makes this the only path to verify post-merge state.

Component hint: `plan-marshall:tools-integration-ci` (`checks`), and the orchestrator's post-merge verification duty (CLAUDE.md of API Sheriff, step 8).
