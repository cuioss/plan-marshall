envelope_version=1
sender_type=plan
sender_id=implement-opencode-enforcement-parity
epic=process-compliance
kind=finding
created=2026-09-22T19:50:06Z

# Finding: inbox write silently re-used a live queue sequence — second same-sender write replaced the first message

## Reported

- Plan: `implement-opencode-enforcement-parity` (PLAN-15), during light-lane pre-dispatch close
- Location: `plan-marshall:plan-orchestrator:orchestrator inbox write` →
  `_orchestrator_inbox.py::cmd_inbox_write` → `allocate_message_path` (`O_CREAT|O_EXCL` claim loop)
- Encounter sequence (same sender `implement-opencode-enforcement-parity`, same slug
  `process-compliance`, both `kind=finding`, both with no `--target-plan` → `destination=queue`):
  1. write #1 (mailbox-probe finding) → returned message `implement-opencode-enforcement-parity-001.md`,
     validated live/consumption=unconsumed.
  2. write #2 (light-lane pr_title finding) → ALSO returned `implement-opencode-enforcement-parity-001.md`.
  3. `inbox list` after #2 showed exactly ONE message from this sender: `-001.md` whose content is
     **write #2's payload** (per full-file content check) and whose mtime matches write #2's time.
     Write #1's payload was gone — silently replaced, not appended.

## Observed disposition

Disposition violates the documented contract: each write MUST land in a fresh, unique message file
(sequence allocator + `O_CREAT|O_EXCL` claim, `allocate_message_path` lines 1146-1154, "no sequence is
ever re-opened"). The queue behaved as if the second write had re-opened the first's sequence.

## Evidence

- `implement-opencode-enforcement-parity-001.md` mtime = 21:45:49 (write #2 time), content = light-lane
  pr_title finding body.
- `implement-opencode-enforcement-parity-002.md` mtime = 21:46:11 — this exists ONLY because write #3
  (re-file of the mailbox-probe finding, after the clobber was detected) was issued manually.
- Before the re-file, the queue had a single `-001.md` with write #2's body, i.e. write #1's
  once-validated message was not present at any path.
- `inbox list` reports both surviving messages live, valid, unconsumed — so no lifecycle/consumption
  step removed #1; it was replaced at allocation time.

## Root-cause notes

- `next_sequence` scans `inbox/`, `inbox/archive`, and the foldered archive subdir for the highest
  `{sender}-{seq}.md`. For a collision to be possible, it must have returned a sequence whose path
  already existed, OR the exclusive create must not have been reached. Both are anomalies against the
  documented guarantees; the exact mechanism was not determinable from the observables here (no test
  harness was run as part of this finding — reproduction is left to the owning epic).
- Consequence of the defect: a sender's earlier finding can be lost without any error, silently —
  the sole reason write #1 survives today is that the clobber was noticed immediately and re-filed.

## Suggested fix direction

- Make `allocate_message_path` fail-fast (error surfaced, not a retry) when the proposal collides with
  an existing file, so a re-opened sequence is an ERROR the operator sees rather than a silent
  truncation.
- Add an `inbox list` invariant/doctor check that two live queue messages from one sender never share a
  sequence.
- Guard `cmd_inbox_write` with a uniqueness assertion on the returned path BEFORE reporting success.
