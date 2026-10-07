envelope_version=1
sender_type=plan
sender_id=manage-lessons-mixes-local-time-and-utc
epic=truthful-signals
kind=candidate-lesson
created=2026-07-29T16:38:41Z

component=plan-marshall:manage-lessons
category=bug
created=2026-07-29

# A `:0Nd` padding format is a minimum width, not an exact width — document it that way

`manage-lessons/standards/file-format.md` claimed the lesson-id sequence segment is an exact 3-digit number, but `get_next_id()` formats it with Python's `:03d`, which pads to a *minimum* of 3 digits and widens past 999 without truncating. The plan that authored this exact-width claim caught nothing itself — CodeRabbit flagged it post-hoc on the very line the plan wrote, and it was fixed via a loop-back task.

## Solution

When documenting any `:0Nd`-style padding contract, describe it as "at least N digits, zero-padded" rather than "an N-digit number", and cross-check the doc prose against the actual format string in the implementing code before asserting the contract as fact — self-review must verify normative doc claims against the formatting code, not just restate prior prose.

## Impact

Any lesson/finding/id-format doc anywhere in the corpus that asserts a fixed-width numeric segment sourced from a `:0Nd`-style format call is at the same risk. Worth a targeted sweep for "N-digit" / "exact" claims paired with `:0\d+d` format strings.
