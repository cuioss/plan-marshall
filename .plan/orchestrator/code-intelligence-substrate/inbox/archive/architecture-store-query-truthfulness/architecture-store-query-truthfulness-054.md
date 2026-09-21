envelope_version=1
sender_type=plan
sender_id=architecture-store-query-truthfulness
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-09-15T07:57:40Z

component=plan-marshall:manage-architecture
category=bug

# The store's JSON writer truncated the destination before the dump completed

Source: PR #1489 CodeRabbit review-body finding 6bb8d2 (outside-diff comment;
resolution=fixed, TASK-042).

_architecture_core._write_json (lines 472-475) opens the destination with mode `w`, which
truncates it before json.dump completes, so a concurrent reader of _project.json or
enriched.json can observe a partial file and fail to parse it.

## Solution

Follow the convention this repository ALREADY uses rather than inventing one: write a
temp file in the same directory so the rename stays on one filesystem, flush it, then
os.replace onto the destination. That tmp-then-replace shape is already present in
swap_data_dir in this very module, and in _locks_core.py, _config_core.py and
generate_executor.py. Coverage was extended so the atomicity is asserted rather than only
implemented.

Two transferable points: (1) shared JSON state read by concurrent processes must use
temp-file-plus-atomic-replace; (2) the four existing in-repo call sites are what made
this a convention-following fix rather than a design decision — check for the existing
shape before proposing one.

## Impact

Arrived in the review BODY as an outside-diff comment, not as an inline thread — a class
of finding that is easy to lose if only inline threads are drained.
