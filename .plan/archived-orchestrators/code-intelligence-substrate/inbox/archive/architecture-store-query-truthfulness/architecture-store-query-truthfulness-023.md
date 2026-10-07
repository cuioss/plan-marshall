envelope_version=1
sender_type=plan
sender_id=architecture-store-query-truthfulness
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-09-15T07:52:55Z

component=plan-marshall:phase-3-outline
category=anti-pattern

# A search hit list is a CANDIDATE set — reading it is what turns it into a declared surface

Source: Q-Gate finding 1ef42b (5-execute, resolution=rejected — confirmed no-op).

The outline's D2 evidence recorded "D2 consumer sweep - 6 distinct files reference
content_search" and treated all six as consumers of the capabilities status vocabulary,
adding three to the Expected Surface on that basis. Read at HEAD, only FOUR are. The
other two are bare-identifier collisions:

- q-gate-validation.md — content_search is section 2.12's own query-type enum member.
- test_claude_pretooluse_hook.py — the only occurrence is a snake_case TEST FUNCTION
  NAME, test_r2_reason_names_the_sanctioned_content_search_replacement. The file carries
  no available/unavailable literal.

## Solution

A bare snake_case identifier over-matches into unrelated enums AND into test function
names. The hit list is a candidate set that must be READ before any member becomes a
declared surface; promoting it unread inflates the footprint and manufactures edits that
should never happen.

## Impact

Two of six declared consumers were phantoms; both were correctly left unedited, but only
after execute-time verification.
