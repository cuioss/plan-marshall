envelope_version=1
sender_type=plan
sender_id=lb-32-head-dependent-step-refire
epic=live-blockers
kind=candidate-lesson
created=2026-10-10T03:28:01Z

component=plan-marshall:automatic-review
category=bug
source_plan=lb-32-head-dependent-step-refire
confidence=high

# Make the automatic-review display_detail template fit 80 ASCII characters

## Context

The automatic-review step fired 5 times on plan `lb-32-head-dependent-step-refire`. Every firing reported the same deviation: the documented `display_detail` template, `N comment(s) found — X reviewed, Y empty, Z refused-structural (unified triage pending)`, is 87 characters and contains an em dash, which breaks the 80-character ASCII rule for that field. Each agent handled it by hand and not the same way: two firings stored the documented 87-character form (which `mark-step-done` accepted) and returned a shortened one, so the stored record and the returned value disagreed; three stored a shortened form ("triage pending", ASCII hyphen) that departs from the document.

The lessons-housekeeping step has the same shape of defect: its two Step 2 exit templates contain an em dash while the same document states the field is ASCII-only, and each firing flattened the returned value by hand.

## Root cause

The step documents carry templates that violate the field's own constraint, and `mark-step-done` does not enforce the constraint, so the violation is absorbed by each agent differently instead of failing once at the source.

## Proposed action

- Shorten the automatic-review template to fit 80 ASCII characters and replace the em dash in both step documents.
- Have `mark-step-done` either flatten to ASCII and reject over-length values, or reject both, so a template that cannot fit fails the first time it is used.
- Add a doc-contract test that renders each documented `display_detail` template at its longest plausible values and asserts the limit.

## Evidence

- aspect: chat_history_analysis — first automatic-review return: "That is 87 characters and contains an em dash, so it breaks the 80-character ASCII rule; `mark-step-done` accepted it anyway"; every later return lists the shortening under its deviations; the final status record stores the shortened form `1 comment(s) found - 1 reviewed, 1 empty, 1 refused-structural (triage pending)`
- aspect: llm_to_script_opportunities — "shorten automatic-review display_detail to 80 ASCII chars by hand", 5 repetitions
- self-review advisories in three rounds named the housekeeping em dash as an out-of-scope observation
