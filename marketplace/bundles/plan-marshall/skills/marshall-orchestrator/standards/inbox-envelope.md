# Inbox Envelope Schema

The message format of the epic's plan-writable OUTBOX. An executing plan appends structured messages to its governing epic through this channel and through nothing else; the orchestrator drains them. The write-boundary contract that sanctions the channel lives in [`persona-marshall-orchestrator/standards/orchestration-model.md`](../../persona-marshall-orchestrator/standards/orchestration-model.md) § Ledger Write-Boundary — this document owns only the message format and its validation.

## Storage location

```text
.plan/local/orchestrator/{epic}/inbox/{sender_id}-{NNN}.md          # queued
.plan/local/orchestrator/{epic}/inbox/archive/{sender_id}-{NNN}.md  # retired
```

`inbox/` is created by `orchestrator scaffold` alongside `workstreams/`, `plans/`, `landings/`, and `logs/`. Messages are written ONLY by the `orchestrator inbox write` verb (see [`../SKILL.md`](../SKILL.md) § Canonical invocations), which derives the path from the validated epic slug and `--sender-id` and accepts no caller-supplied output path. There is no argument value that reaches any other path in the epic tree.

`inbox/archive/` is the retired-message path a consumed message is moved to. It is NOT scaffolded — it is created on first use by `orchestrator inbox archive`, so no existing scaffold constant changes value.

## Drain semantics

The orchestrator drains the queue; the two drain verbs are mechanical and carry no judgement.

- **`inbox list` is the enumeration seam.** It returns the queued messages in deterministic (sender, sequence) order, each with its header context and its validation verdict. Nothing under `inbox/archive/` is enumerated. The payload also names WHICH KIND OF ZERO a `count: 0` is, because **a zero meaning *could not look* and a zero meaning *looked, found nothing* do not share a representation**: `epic_not_found` (`status: error` — no epic tree at all), `inbox_state: missing` (the epic is there but has no `inbox/` directory, so the enumeration could not look), and `inbox_state: present` with `count: 0` (it looked and found nothing). `inbox_dir` reports the absolute path actually scanned. The `inbox_state` discriminator is captured ONCE, immediately before the enumeration loop, so it reports the same observation the enumeration acted on — under a concurrent drain that removes `inbox/` mid-scan the payload can never pair a non-zero `count` with `inbox_state: missing`. An absent `inbox/` is NOT a fault — the verb stays `status: success` so a drain is never aborted by it, and the discriminator rides the payload rather than the status.
- **A malformed message is reported, never skipped.** Each row carries either `valid: true` or the validator's distinct error code from the table below, so a broken message stays visible to the drain instead of disappearing from it, and one bad message never aborts the enumeration.
- **An unreadable message is reported the same way.** A message file that cannot even be read — non-UTF-8 bytes, or the file vanishing mid-drain under a concurrent writer — is reported as one row with `valid: false` and the distinct `error: unreadable` code, not confusable with any envelope-validation code below, and enumeration continues to the next message.
- **Archival is the consume marker.** A message leaves the queue only by being archived, so a re-scan of an already-drained message is a no-op and a repeated `inbox archive` of the same message is idempotent success.
- **`inbox validate` resolves the archive — the consume marker's read-side counterpart.** A name absent from `inbox/` is probed against `inbox/archive/` before the verb answers, so a CONSUMED message resolves to `status: success` with `location: archived` (and `archive_path` set) instead of collapsing into the same not-found answer a never-written message gets. `location: queued` is the live-queue branch. `file_not_found` is thereby narrowed to its true meaning: present at NEITHER path. Without the probe the two states are indistinguishable, and the consume marker is only half-observable — writable by the drain, unreadable by anything after it.
- **Archival is a claim, not a check-then-move.** Mirroring sequence allocation below, the destination is claimed atomically — `os.link`, which never replaces an existing file — and the source is unlinked only once that claim succeeds. Two racing drains therefore cannot both clear a presence check: the loser reports `already_archived` derived from the claim's own outcome instead of faulting on a source the winner already moved. Because the claim is a hard link, the loser's answer is decided by **inode identity**, not by source presence — inside the window between the winner's link and its unlink both paths are one file, and the loser's refused claim resolves to `already_archived` even though the source is still there. `archive_conflict` is reserved for the genuinely distinct case: the destination holds a different file, which the drain never clobbers. This is what makes the idempotent-on-repeat guarantee above hold for a resumed drain as well as a sequential one.
- **A mutating verb never resolves an archived epic.** `inbox archive` relocates a file, so it resolves the epic root strictly: an epic whose active tree has already been archived is refused with `epic_not_found` rather than mutating inside the frozen audit record. The read-side verbs (`inbox list`, `inbox validate`) keep the archived read-fallback.
- **The append-only invariant is unbroken.** Archival RELOCATES the file; it never edits or deletes it. The message body at the archived path is byte-identical to the one the sender wrote.
- **A stranded message is recovered with `inbox archive --as-name`.** A message left undrainable by a pre-fix sequence collision — its default destination already holds a distinct archived record, so `archive_conflict` fires forever — is retired under a non-colliding archived name supplied by `--as-name`. The recovery relocates the file exactly as an ordinary archival does, so the append-only invariant still holds and the existing audit record is never clobbered. The override is **sender-constrained** on top of the bare-filename guard: it must match `{sender_id}-*` for the source message's sender, or the call is refused with `as_name_sender_mismatch` (a path-shaped value is still refused with `invalid_message_name`). The constraint keeps the archive's `{sender}-{seq}`-derived provenance intact, so a recovered file can never be attributed to a different sender.

## File naming and sequence semantics

| Segment | Rule |
|---------|------|
| `{sender_id}` | The sender's identifier — a plan id for a `plan` sender, an epic slug for an `orchestrator` sender. Kebab-case; validated as a path-safe identifier before use. |
| `{NNN}` | Zero-padded, three-digit-minimum sequence, allocated per sender, starting at `001` and growing past three digits when a sender exceeds 999 messages. |

Sequence allocation is a **claim, not a scan-then-write**: the next free number is proposed by scanning BOTH the live queue (`inbox/`) and the archive (`inbox/archive/`) — so a sender whose messages have been retired never re-uses a number its archived twin already holds — but the exclusive create (`O_CREAT | O_EXCL`) is the atomic step, and it stays scoped to `inbox/` alone. A collision advances to the next sequence and retries, so a concurrent or re-entered finalize cannot clobber an existing message.

## Message shape

A `key=value` metadata header (the repo's existing `file_ops.parse_markdown_metadata` format), exactly one blank line, then the markdown payload body:

```text
envelope_version=1
sender_type=plan
sender_id=orchestration-inbox-channel
epic=truthful-signals
kind=landing
created=2026-07-26T21:04:11Z

## What landed

...markdown payload...
```

The blank line is the header terminator. A message with no blank line has no payload and is rejected as `empty_payload`.

## Header fields

Every field is required. A message missing any one is rejected as `missing_header_field`.

| Field | Required | Type | Description |
|-------|:--------:|------|-------------|
| `envelope_version` | Yes | integer | Schema version. Currently `1`. Any other value is rejected — never silently accepted. |
| `sender_type` | Yes | enum | `plan` (an executing plan's OUTBOX message) or `orchestrator` (reserved for orchestrator-to-orchestrator messages). |
| `sender_id` | Yes | identifier | The sender's id. MUST match the `{sender_id}` segment of the filename. |
| `epic` | Yes | slug | The epic the message is addressed to. MUST match the tree the message sits in. |
| `kind` | Yes | enum | `landing`, `finding`, or `candidate-lesson` — see the payload contract below. |
| `created` | Yes | ISO-8601 | UTC compose timestamp (`YYYY-MM-DDTHH:MM:SSZ`). |

## Payload contract per kind

The payload is free markdown; the kind tells the orchestrator-side pickup how to consume it. Granularity is **one message per emitted item** — that is what the sequence exists to allocate.

| `kind` | Payload contract |
|--------|------------------|
| `landing` | The plan's landing narrative: what shipped, the PR reference, and any residue the epic should track. Exactly one per orchestrated finalize run, emitted unconditionally — including when the plan produced no lesson-bearing signals. |
| `finding` | One observation the plan surfaced that the epic should know about but that is not itself a lesson. |
| `candidate-lesson` | One proposed lesson body, in the same `key=value` + markdown-body shape the lessons corpus uses, so the orchestrator-side pickup can lift it into `manage-lessons` with zero transcoding. The plan performs no global-vs-epic classification — only the orchestrator holds the cross-plan context that judgement needs. |

## Invariants

- **Append-only.** A sender creates new message files and never edits or deletes an existing one, including its own.
- **One file per message.** A message is never appended to an existing file; each emitted item gets its own sequence.
- **Own-file-only.** A sender writes only files whose `{sender_id}` segment is its own id.
- **One-way.** The plan writes; the orchestrator drains. A plan never reads the ledger to make a decision.

## Validator error codes

The named validation seam is `validate_envelope(text, expected_epic, filename)` in `scripts/_orchestrator_inbox.py`, surfaced as `orchestrator inbox validate` for one message and as the per-row verdict of `orchestrator inbox list` for the whole queue. Checks run in the fixed order below, so a given malformed message always yields the same code.

| Order | `error` | Rejection condition |
|:-----:|---------|---------------------|
| 1 | `missing_header_field` | One or more header fields is absent or empty. |
| 2 | `unknown_envelope_version` | `envelope_version` is not the supported version. |
| 3 | `invalid_sender_type` | `sender_type` is outside the declared enum. |
| 4 | `invalid_kind` | `kind` is outside the declared enum. |
| 5 | `empty_payload` | No payload body follows the header's blank line. |
| 6 | `epic_mismatch` | The `epic` header disagrees with the epic tree the message sits in. Checked only when an expected epic is supplied. |
| 7 | `filename_sender_mismatch` | The filename's `{sender}` segment disagrees with the `sender_id` header. Checked only when a filename is supplied. |

The table is exhaustive over ENVELOPE-VALIDATION verdicts, not over the whole vocabulary either verb reports. In particular, `inbox validate`'s `location` (`queued` / `archived`) is a *resolution* outcome — where the message was found — and is orthogonal to the verdicts above: an `archived` message runs through the identical checks in the identical order.

`unreadable` is a separate, non-numbered code: it is raised by `cmd_inbox_list` itself, before a message's text ever reaches `validate_envelope`, when the message file cannot be read at all (non-UTF-8 bytes, or the file vanishing mid-drain under a concurrent writer). It is deliberately distinct from every code above so a read failure is never confused with an envelope-validation failure.

## Forward compatibility

`envelope_version` is **fail-closed**: a message whose version is not the supported one is rejected with `unknown_envelope_version`, never accepted on a best-effort basis. The `sender_type` discriminator carries the extension point for future sender classes, so a new sender needs no version bump. Nothing beyond those two extension points is added speculatively.

## Related

- [`persona-marshall-orchestrator/standards/orchestration-model.md`](../../persona-marshall-orchestrator/standards/orchestration-model.md) — § Ledger Write-Boundary, the contract that sanctions this channel
- [`../SKILL.md`](../SKILL.md) § Canonical invocations — the `inbox write` / `inbox validate` / `inbox list` / `inbox archive` / `inbox detect` argument surfaces
- [`manage-lessons/standards/file-format.md`](../../manage-lessons/standards/file-format.md) — the lesson body shape a `candidate-lesson` payload carries
