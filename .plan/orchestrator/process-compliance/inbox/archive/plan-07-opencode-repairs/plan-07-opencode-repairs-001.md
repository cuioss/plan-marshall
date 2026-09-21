envelope_version=1
sender_type=plan
sender_id=plan-07-opencode-repairs
epic=process-compliance
kind=finding
created=2026-09-20T21:23:52Z

# Process-rule issues observed while implementing PLAN-07 opencode-repairs

sender: plan-07-opencode-repairs
epic: process-compliance

## 1. marshal_status stale (advisory, non-blocking)

`generate_executor preflight` returned `executor_action: fresh`,
`marshal_status: stale` (installed 0.1.1716 vs marshal 0.1.1636).
Continued per the preflight branch contract (advisory-only, never auto-mutate
marshal.json). Operator should run `/marshall-steward` to reconcile config
provisioning stamps.

## 2. recipe-match / aspect-classify shell-arg friction

`recipe-match` and `aspect-classify` take `--request-text` via shell args. The
ingested spec body is multiline markdown with headings and fences, which the
tool-usage guidance keeps out of shell arguments. Used a concise
representative token subset for scoring (no match, aspect implementation
fallback) and proceeded. The file-pointer ingestion itself went through the
sanctioned `--body-file` script-mediated read.

## 3. Clean-main assertions lack sibling attribution

Post-init, post-refine, post-outline, and post-plan contract assertions read
`git -C . status --porcelain` as empty-means-clean. With
plan-04-persona-behavior live on the main checkout, the porcelain carried two
sibling-drift entries. Proved own-phase cleanliness by comparing the dirty set
pre/post each dispatch (identical, no new files) and continued, logging the
attribution each time. Never ran `git restore` / `checkout --` / `stash` on a
dirty file. The assertion cannot distinguish sibling drift from own drift under
concurrent main-checkout plans.

## 4. Mailbox probe vs direct detect divergence

`manage-status transition` mailbox probe reported `not_orchestrated`
(`not_orchestrator_pointer`) for source_id
`.plan/local/orchestrator/process-compliance/plans/PLAN-07-opencode-repairs.md`,
while direct `orchestrator inbox detect --source-id` on the same value
returned `orchestrated: true`, epic process-compliance. Transition succeeded
regardless; mailbox check-point recorded as reported.

## 5. Expected Surface omits merge-auth owner

Spec Expected Surface lists only platform-runtime files plus runtime tests,
but Deliverable 3 (unattended consent distinction) necessarily touches
`manage-status/scripts/_cmd_merge_authorization.py` and
`manage-status/SKILL.md`. Proceeded per the deliverable text and the
write-boundary (own repo source and tests only), treating the surface list as
under-declared.

## 6. Tier divergence on verify:module-tests

Execution manifest `phase_5.step_execution_tier` records
`verify:module-tests` as `per_task`, while
`architecture resolve --command module-tests --module plan-marshall` returned
`execution_tier: orchestrator` with `bash_timeout_seconds: 718`. Ran the suite
as orchestrator via the build-server daemon longpoll (green, 22733 tests).

## 7. Stale opencode_runtime docstring fixed in TASK-1

Module docstring claimed metrics capture succeeds with total_tokens; the
implementation honestly declines on every input. Updated the docstring to the
decline-every-input contract and documented that opencode never returns
`hook_not_configured`.

## Verify-first outcome

HYPOTHESIS corroborated at HEAD: seam lives in platform-runtime,
`session_capture` and `metrics_capture` are the no-op entry points, no bare
`runtime` symbol. Finalize-machinery resolver untouched (reference-only
boundary honored). Q-Gate outline findings (3 assessment-coverage) fixed by
filing CERTAIN_INCLUDE assessments; 4-plan Q-Gate clean.
