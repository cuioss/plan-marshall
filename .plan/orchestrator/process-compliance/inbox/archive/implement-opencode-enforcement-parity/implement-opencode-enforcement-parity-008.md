envelope_version=1
sender_type=plan
sender_id=implement-opencode-enforcement-parity
epic=process-compliance
kind=finding
created=2026-09-24T16:56:16Z

envelope_version=1
sender_type=plan
sender_id=implement-opencode-enforcement-parity
epic=process-compliance
kind=finding
created=2026-09-24T17:00:00Z

# Finding: on-main executor regeneration via sync-plugin-cache produces a broken executor (ModuleNotFoundError plan_logging on every call)

Epic: process-compliance
Plan: implement-opencode-enforcement-parity
Phase observed: phase-6-finalize, project:finalize-step-sync-plugin-cache Step 3

## Summary

The sync-plugin-cache step's Step 3 on-main executor regeneration (`generate_executor generate` via the executor, no `--marketplace` flag, from the main checkout) wrote a `.plan/execute-script.py` that crashes on EVERY invocation with `ModuleNotFoundError: No module named 'plan_logging'` (raised at module line 183). This was a total lockout: no manage-* verb could run (mark-step-done, logging, metrics, archive — all dead), including the step's own completion record. Recovery required the sanctioned direct-path `generate_executor.py bootstrap --marketplace` outside the executor.

## Facet A — Cache-context generation emits a broken sys.path bootstrap

The failing generation ran with auto-detected plugin-cache context (`/home/oliver/.config/opencode/skills`, 0 marketplace + 160 local scripts pattern observed on dry-run). The emitted executor's module-level `from plan_logging import ...` cannot resolve because the generated sys.path setup does not include a directory carrying that module in cache context. The `--marketplace`-context bootstrap produced a working executor. Generation in cache context is therefore broken-by-default for this repo, yet it is the default path (no flag), and it is the path the sync-plugin-cache doc prescribes (no `--marketplace` flag in its command).

## Facet B — No fail-safe caught it

The generator docstring claims five pre-write guards including py_compile self-check — but a missing-module ImportError is a RUNTIME failure, not a syntax failure, so no guard fires. The broken file was committed atomically onto the live executor path. The only reason finalize survived is the direct-path bootstrap backdoor plus an operator diagnosing it by hand. A regeneration that cannot import its own shared modules should fail closed before replacing the working executor (e.g., smoke-import the emitted file in-process before os.replace).

## Suggested fixes

1. Make sync-plugin-cache pass `--marketplace` (or the repo's pinned equivalent) so on-main regeneration uses marketplace context, matching the development layout the executor must serve.
2. Add a sixth guard: import-smoke-test the substituted executor content (or at least resolve its shared-module imports) before atomic replace; refuse to overwrite a working executor with one that cannot start.
3. Investigate why cache-context generation emits an unresolvable `plan_logging` import while marketplace-context generation does not.

## Evidence

- Failing command: `python3 .plan/execute-script.py plan-marshall:tools-script-executor:generate_executor generate` (cwd=main checkout, no flags) → `scripts_registered: 160` (cache-context shape).
- Every subsequent executor call: `File ".plan/execute-script.py", line 183, in <module> from plan_logging import ... ModuleNotFoundError`.
- Recovery: `python3 marketplace/bundles/plan-marshall/skills/tools-script-executor/scripts/generate_executor.py bootstrap --marketplace` → `status: success, action: generated` → executor works.
- plan_logging.py exists in both repo marketplace and cache; the generated sys.path setup is what fails to expose it.
