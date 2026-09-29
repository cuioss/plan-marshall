envelope_version=1
sender_type=plan
sender_id=plan-12-tool-triage
epic=process-compliance
kind=finding
created=2026-09-29T13:44:00Z

# Orchestrator-tier phase-5 build: execution.md and await-long-running.md prescribe opposite mechanisms

## Observed

The first phase-5-execute envelope of plan-12-tool-triage yielded `status: blocked` naming
`verify:module-tests` as orchestrator-tier (`bash_timeout_seconds: 1490`, live resolve).

- `plan-marshall/workflow/execution.md` § "Orchestrator-tier phase-5 verification (await-long-running)"
  step 2: "Resolve and run each `orchestrator`-tier step through the await-long-running seam — the
  detach-and-notify recipe owns the full acquire-slot → background (`run_in_background: true`) →
  wake-on-notification → state-gated clear → release flow."
- `plan-marshall/workflow/await-long-running.md` § "Build consumer — routes through build-server-client":
  "The build consumer does NOT use this detach-and-notify seam ... Do NOT `run_in_background` ... the
  daemon `wait`"; its `consumer` parameter accepts only `ci-wait` | `finalize-barrier`.

Two documents, each authoritative for its step, prescribe opposite actions for the same call. The
orchestrator followed `await-long-running.md` (the newer, more specific contract) and ran the resolved
wrapper in the foreground, relying on the build-execute routing seam to submit to the ready `marshalld`
daemon. The foreground call still hit the 600 s Bash ceiling (resolved `bash_timeout_seconds: 3095`,
`exceeds_bash_ceiling: true`) and the harness moved it to the background anyway — so in practice
neither documented shape is achievable as written for a build longer than the Bash ceiling.

Secondary: the leaf named `module-tests plan-marshall` (1490 s) while `architecture resolve --command
module-tests` returned the whole-tree `module-tests` (3095 s, `module: default`). execution.md step 2 says
"whole-tree", so the orchestrator ran the larger build than the leaf's own verification step needed.

Tertiary (false-green risk): the orchestrator-run build returned `status: error` with one
`test_failure` in `errors[]` (unguarded runtime-derived parametrize in the plan's new test), and
execution.md's table says `error` → route through `verification-feedback` triage. But
`verification-feedback` reads the per-plan findings store, and on this path NOTHING persists the
failure there — the leaf's Step 11 `manage-findings qgate add` persistence only runs for builds the leaf
itself executes. `qgate list --phase 5-execute --resolution pending` returned 0, so the orchestrator
persisted the failure itself (hash 4b7323) before dispatching triage — no documented step says to.
CORRECTION after triage: the build wrapper HAD persisted the same failure twice (021fed, 4b4597) into
the plan-scoped findings store (not the phase-scoped qgate store), and verification-feedback reads both.
So the store was not empty; the orchestrator's check looked at the wrong one of two stores and created a
third duplicate. The defect is therefore two-store opacity: execution.md never says which store the
orchestrator-tier build's failures land in or how to confirm them, and a phase-scoped `qgate list`
reads as "nothing recorded" while the plan store holds the rows.

Quaternary: at execute exit both orchestrator-tier `verify` builds came back green with 0 pending /
0 in_progress tasks. execution.md's orchestrator-tier table says `success` → "re-dispatch phase-5-execute
so the leaf resumes; the freshness gate (Step 12a) now sees the stamp and permits the transition", while
the same document's Pre-dispatch queue peek says an empty queue → the orchestrator "MUST NOT re-dispatch"
and proceeds straight to the transition. Both cannot be followed; the orchestrator applied the MUST, so the
leaf-side Step 12a freshness gate never ran at this boundary.

## Suggested fix

Rewrite execution.md step 2 to route builds through the `build-server-client` submit/wait contract
(explicit `submit` + bounded `wait` re-issue loop, never a single Bash call that can exceed the ceiling),
and state which scope (the leaf's named step vs. whole-tree) the orchestrator runs.
