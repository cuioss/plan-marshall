envelope_version=1
sender_type=plan
sender_id=plan-13-finalize-mechanism-defects
epic=process-compliance
kind=finding
created=2026-09-27T14:21:17Z

# Process-rule issues observed during PLAN-13 init (plan-13-finalize-mechanism-defects)

Observed while running `/plan-marshall task="implement .plan/orchestrator/process-compliance/plans/PLAN-13-finalize-mechanism-defects.md"` in strict process-compliance mode.

## 1. PLAN-13 is invisible to the epic mailbox (spec filename lacks a CODE segment)

`manage-status transition --completed 1-init` reported:

```text
mailbox: probe: not_orchestrated
reason: "request.md source_id is not an orchestrator plan-spec pointer (detection=not_orchestrator_pointer)"
```

The pointer `.plan/orchestrator/process-compliance/plans/PLAN-13-finalize-mechanism-defects.md` is an
orchestrator plan spec that the process-compliance epic emitted, but the detector classifies it as
"no epic". The likely cause is the `PLAN-{CODE}-{NNN}-{slug}.md` naming convention: `PLAN-13-…` has no
UPPERCASE code segment. Consequences:

- every mailbox check-point in this run reports `not_orchestrated` (a *measured fact* per the contract), which is false;
- the finalize `emit-landing` inbox message will be skipped, so the epic will not learn that PLAN-13 landed.

Either the staged spec name is non-conformant (and the epic's emit step should have refused to stage it),
or the detector is too narrow. Both the stager and the detector need a shared, enforced naming contract.

## 2. Step 4 narrative rebind is not executable as documented

phase-1-init Step 4 (file-pointer branch) requires Step 5c-recipe-match and Step 5c-aspect-classify to
receive the INGESTED FILE CONTENT via `--request-text "{request_narrative}"`. But:

- `recipe-match` and `aspect-classify` accept only `--request-text` (no `--request-file` / `--plan-id` input);
- the ingested spec is ~9 KB of multi-line markdown containing backticks and apostrophes. Double-quoting it
  would trigger shell command substitution on the backticks; single-quoting breaks on the apostrophes;
  multi-line Bash arguments collide with the one-command-per-call / no-heredoc hard rules;
- the orchestrator may not `Read` the spec directly (`.plan/` access: scripts only), so the only way to get
  the body in context is `manage-plan-documents request read`, and then it has to be hand-transcribed back
  into a shell argument (a paraphrase risk the file-pointer contract exists to remove).

Workaround used in this run: passed the verbatim title + Objective + Deliverables sections as a single
`$'…'` argument (not the full body), logged as a decision. Fix: give both verbs a `--plan-id` (read the
persisted request.md body) or `--request-file` input, and update Step 4/5c to use it.

## 3. `scope-estimate-heuristic` counts provenance paths as scope

The heuristic counted 10 distinct paths and banded the plan `multi_module`, which fired `S2:scope_estimate`
on the lane router. Three of those paths are pure provenance, not change surface: the spec's own path
(counted twice, as `.plan/orchestrator/.../PLAN-13-….md` and `plans/PLAN-13-….md`), the epic inbox file
cited as evidence, and an absolute path into a *different repository* (`/Users/oliver/git/plan-marshall-mcp/...`).
An ingested orchestrator spec always carries such citations, so every file-pointer plan is inflated.

## 4. `domain-detect` matched on the epic name, not the work

`domain-detect` returned `reason=unambiguous_narrative_match` with the only narrative alias `compliance` —
which comes from the epic slug `process-compliance` in the spec header, not from the work. `python` landed
only in `additional_candidates` and was not included, although the spec names
`platform-runtime/scripts/session_binding.py` and pytest regression tests under `test/plan-marshall/`.
Because the result was non-ambiguous, no prompt fired and the python domain was silently dropped.

## 5. `lanes preview` lane_report omits one full-posture step

`lanes preview` lists 26 `full` phase-6 steps but `lane_report_count: 25`. The missing row is
`plan-marshall:plan-retrospective`: it appears in all three posture step lists (minimal included) yet has no
`lane_report` row, so its declared/effective tier is never shown. An index table must enumerate every member
of the set it indexes.

## 6. session_ids not captured at plan-init

Step 8a found `status.metadata.session_ids` absent (the SessionStart `session capture` hook stored nothing
for this session). Logged the documented WARNING; recording here because it recurs and finalize will need
the late-capture path.
