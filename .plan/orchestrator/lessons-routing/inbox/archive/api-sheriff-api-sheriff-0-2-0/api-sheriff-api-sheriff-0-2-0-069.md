envelope_version=1
sender_type=orchestrator
sender_id=api-sheriff-api-sheriff-0-2-0
epic=lessons-routing
kind=finding
created=2026-10-29T09:10:04Z

# The review-evidence validator rejects a citation that is not in its exact format, and a hand-written row is only found by running it

Observed by `plan-v02-50-enumeration-detection-substrate` while landing PR #532 in the API-Sheriff repository
(epic `api-sheriff-0-2-0`, plan-marshall plugin 0.1.2021, executor 0.1.2021).

- The rows of the functional-review evidence are checked by a validator that accepts only its documented citation format. A
  row written in a slightly different shape was rejected and had to be redone, in a finalize loop that is already long.
- The format is documented, but the producing step does not state it where the row is written, and nothing checks the row before
  it is committed to the log.

Suggested direction: have the step that writes the evidence rows either emit the citation through a helper that produces the
exact shape, or run the validator on the row before accepting it, so a format drift fails at the writer and not three rounds later.
