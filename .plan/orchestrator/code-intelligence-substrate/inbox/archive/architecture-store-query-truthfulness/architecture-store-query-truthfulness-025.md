envelope_version=1
sender_type=plan
sender_id=architecture-store-query-truthfulness
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-09-15T07:52:59Z

component=pm-plugin-development:plugin-doctor
category=bug

# Two plugin-doctor rules over one stale probe produce two findings and one cause

Source: Q-Gate finding b9a0bb (5-execute, resolution=rejected — same root cause as 181b07).

manage-invocation-invalid reported the identical merge_lock queue-list invocation as
using an unregistered subcommand. It is the SECOND rule restating the FIRST rule's
verdict, and both inherited the same stale evidence: a --help walk over a deployed copy
predating commit 991bce8df.

## Solution

Filed separately from 181b07 on purpose. Two rules sharing one probe multiply a single
false positive into a finding COUNT, and the count is what a gate reads: this pair
turned one stale cache entry into "quality-gate red with 2 plugin-doctor findings" and
blocked the task gate on a doubled phantom. When rules share a fact source, the finding
should name the shared probe so a reviewer can refute both at once instead of triaging
them as independent evidence.

Note the second-order trap in this one's own body: it proposed, as an alternative
remedy, deleting SKILL.md's queue-list section and test_merge_queue_list.py "if the verb
was intentionally dropped". Acting on that would have deleted a live verb and its tests
because a stale help cache said the verb did not exist.

## Impact

A false finding that also carried a destructive suggested remedy.
