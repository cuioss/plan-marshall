envelope_version=1
sender_type=plan
sender_id=plan-12-tool-triage
epic=process-compliance
kind=finding
created=2026-09-29T13:43:56Z

# Two routed whole-tree pytest runs on one worktree destroy each other's basetemp

**Observed (plan-12-tool-triage, finalize pre-push-quality-gate, HEAD f18f01df3):** the orchestrator queued the gate's whole-tree `module-tests` arm and, right behind it, a whole-tree `verify` (the extra build the push freshness gate needs — see the staged prepush-gate-cannot-satisfy-push-freshness finding). Both were routed to marshalld (`serialization=daemon-scheduled`) yet ran overlapping: `module-tests` returned `status: error` with 10 `FileNotFoundError`s, every one inside `.plan/temp/pytest-basetemp/<run>/popen-gwN` (collection errors from `tmp_path_factory.mktemp`, one `read_text` on a tmp file), while `verify` over the identical tree came back green (28188 tests). A re-run of `module-tests` alone was then required.

**Why it matters:** the failure is indistinguishable at the TOON level from a genuine test red (`status: error`, `category: test_failure` / `test_collection_error`), so a strict reading of pre-push-quality-gate Branch B would record `failed` and halt the phase over an infrastructure collision, and verification-feedback triage would be dispatched against non-defects. The orchestrator's own error was queueing two whole-tree pytest runs at once; nothing prevents or detects it.

**Suggested fix:** either make the daemon actually serialize two runs against the same worktree (the `daemon-scheduled` label implied it would), or give each run a private basetemp root; and have the build wrapper classify a basetemp-vanished `FileNotFoundError` cluster as `indeterminate` rather than `error`.
