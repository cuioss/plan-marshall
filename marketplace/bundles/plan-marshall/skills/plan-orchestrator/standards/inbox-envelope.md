# Inbox Envelope Schema

The message format of the epic's plan-writable OUTBOX. An executing plan appends structured messages to its governing epic through this channel and through nothing else; the orchestrator drains them. The write-boundary contract that sanctions the channel lives in [`persona-plan-orchestrator/standards/orchestration-model.md`](../../persona-plan-orchestrator/standards/orchestration-model.md) § Ledger Write-Boundary — this document owns only the message format and its validation.

## Storage location

```text
.plan/local/orchestrator/{epic}/inbox/{sender_id}-{NNN}.md                    # queued
.plan/local/orchestrator/{epic}/inbox/archive/{sender_id}/{sender_id}-{NNN}.md # retired (per-sender)
```

`inbox/` is created by `orchestrator scaffold` alongside `workstreams/`, `plans/`, `landings/`, and `logs/`. Messages are written ONLY by the `orchestrator inbox write` verb (see [`../SKILL.md`](../SKILL.md) § Canonical invocations), which derives the path from the validated epic slug and `--sender-id` and accepts no caller-supplied output path. There is no argument value that reaches any other path in the epic tree.

`inbox/archive/{sender}/` is the retired-message path a consumed message is moved to — **foldered per sender**. Neither `inbox/archive/` nor its per-sender subdirectories are scaffolded; each is created on first use by `orchestrator inbox archive`, so no existing scaffold constant changes value. The archive folder is keyed on the SOURCE message's sender, so a message and its `--as-name` recovery twin land in the same subdirectory. A sender segment that is unsafe as a DIRECTORY name (a value valid as a filename component but traversing as a directory, e.g. a `..`-shaped sender) is refused rather than folded into a traversing path. A pre-foldering flat archive is folded by `orchestrator inbox migrate-archive`, which reports the count moved per sender; the sequence allocator, the resolver, and the counter all read BOTH the foldered and flat layouts, so a partly-migrated archive never re-opens a retired sequence number.

## Drain semantics

The orchestrator drains the queue; the two drain verbs are mechanical and carry no judgement.

- **`inbox list` is the enumeration seam.** It returns the queued messages in deterministic (sender, sequence) order, each with its header context and its validation verdict. Nothing under `inbox/archive/` is enumerated. The payload also names WHICH KIND OF ZERO a `count: 0` is, because **a zero meaning *could not look* and a zero meaning *looked, found nothing* do not share a representation**: `epic_not_found` (`status: error` — no epic tree at all), `inbox_state: missing` (the epic is there but has no `inbox/` directory, so the enumeration could not look), and `inbox_state: present` with `count: 0` (it looked and found nothing). `inbox_dir` reports the absolute path actually scanned. The `inbox_state` discriminator is captured ONCE, immediately before the enumeration loop, so it reports the same observation the enumeration acted on — under a concurrent drain that removes `inbox/` mid-scan the payload can never pair a non-zero `count` with `inbox_state: missing`. An absent `inbox/` is NOT a fault — the verb stays `status: success` so a drain is never aborted by it, and the discriminator rides the payload rather than the status.
- **`inbox list` surfaces each message's lifecycle, and tells a finished stream from an empty queue.** Every row carries `lifecycle`, `revision`, and `superseded_by`, so a revised message is visibly different from a virgin one and a superseded one is visibly retired. The payload also carries `live_count` (VALID messages still presenting as live — excluding `superseded` and `stream-end`) and `closed_senders` (senders that have filed a `stream-end` marker). Those two are the drain's empty-vs-finished discriminator: `live_count: 0` with an empty `closed_senders` is an EMPTY queue that may yet receive more, while `live_count: 0` with the sender in `closed_senders` is a FINISHED stream.
- **A malformed message is reported, never skipped.** Each row carries either `valid: true` or the validator's distinct error code from the table below, so a broken message stays visible to the drain instead of disappearing from it, and one bad message never aborts the enumeration.
- **An unreadable message is reported the same way.** A message file that cannot even be read — non-UTF-8 bytes, or the file vanishing mid-drain under a concurrent writer — is reported as one row with `valid: false` and the distinct `error: unreadable` code, not confusable with any envelope-validation code below, and enumeration continues to the next message.
- **Archival is the consume marker.** A message leaves the queue only by being archived, so a re-scan of an already-drained message is a no-op and a repeated `inbox archive` of the same message is idempotent success.
- **`inbox validate` resolves the archive — the consume marker's read-side counterpart.** A name absent from `inbox/` is probed against the sender's foldered `inbox/archive/{sender}/` subdirectory (and any un-migrated flat `inbox/archive/` twin) before the verb answers, so a CONSUMED message resolves to `status: success` with `location: archived` (and `archive_path` set) instead of collapsing into the same not-found answer a never-written message gets. `location: queued` is the live-queue branch. `file_not_found` is thereby narrowed to its true meaning: present at NEITHER path. Without the probe the two states are indistinguishable, and the consume marker is only half-observable — writable by the drain, unreadable by anything after it.
- **Archival is a claim, not a check-then-move.** Mirroring sequence allocation below, the destination is claimed atomically — `os.link`, which never replaces an existing file — and the source is unlinked only once that claim succeeds. Two racing drains therefore cannot both clear a presence check: the loser reports `already_archived` derived from the claim's own outcome instead of faulting on a source the winner already moved. Because the claim is a hard link, the loser's answer is decided by **inode identity**, not by source presence — inside the window between the winner's link and its unlink both paths are one file, and the loser's refused claim resolves to `already_archived` even though the source is still there. `archive_conflict` is reserved for the genuinely distinct case: the destination holds a different file, which the drain never clobbers. This is what makes the idempotent-on-repeat guarantee above hold for a resumed drain as well as a sequential one.
- **A mutating verb never resolves an archived epic.** `inbox archive` relocates a file, so it resolves the epic root strictly: an epic whose active tree has already been archived is refused with `epic_not_found` rather than mutating inside the frozen audit record. The read-side verbs (`inbox list`, `inbox validate`) keep the archived read-fallback.
- **The append-only invariant is unbroken.** Archival RELOCATES the file; it never edits or deletes it. The message body at the archived path is byte-identical to the one the sender wrote.
- **A stranded message is recovered with `inbox archive --as-name`.** A message left undrainable by a pre-fix sequence collision — its default destination already holds a distinct archived record, so `archive_conflict` fires forever — is retired under a non-colliding archived name supplied by `--as-name`. The recovery relocates the file exactly as an ordinary archival does, so the append-only invariant still holds and the existing audit record is never clobbered. The override is **sender-constrained** on top of the bare-filename guard: it must match `{sender_id}-*` for the source message's sender, or the call is refused with `as_name_sender_mismatch` (a path-shaped value is still refused with `invalid_message_name`). The constraint keeps the archive's `{sender}-{seq}`-derived provenance intact, so a recovered file can never be attributed to a different sender.

## Write-side deliverability

`orchestrator inbox write` accepts an optional `--target-plan {plan_id}` naming the plan a message is aimed at. The inbox is a **one-way** channel — a plan writes, the orchestrator drains, and the drain is an act BETWEEN plans (§ Invariants) — so it has no delivery path to a plan. A message aimed at a plan that is currently **running** is therefore architecturally undeliverable: that plan will have finished before the orchestrator's next drain and never reads the message. The write verb reports this **at write time** rather than silently queuing a message no reader will consume.

The guard fires only when `--target-plan` is supplied, and refuses only a plan the epic's `status.json` positively reads as `running` (`plans[]` row with `status: running` — the same machine authority `orchestrator`'s own running-plans signal reads):

| Condition | Outcome |
|-----------|---------|
| `--target-plan` names a plan whose `status.json` row is `running` | `status: error, error: undeliverable_to_running_plan` — the message is REFUSED, never queued |
| `--target-plan` is not a path-safe identifier | `status: error, error: invalid_target_plan` |
| `--target-plan` names a non-running plan (landed, parked, or absent), or `status.json` is unreadable / carries no queue | the write PROCEEDS — the message queues as an ordinary epic-addressed message the orchestrator drains |
| `--target-plan` omitted | the write proceeds unchanged (the primary path) |

The guard makes the existing undeliverability **visible**; it deliberately does NOT build a mid-run delivery channel — routing a message into a running plan is a larger design question this channel does not answer. `--target-plan` never reaches the write path: the message file target stays derived from the epic slug and `--sender-id` alone, so the ledger write-boundary carve-out is untouched. Because these are write-side deliverability outcomes, they are distinct from the envelope-VALIDATION verdicts in § Validator error codes, which govern message FORMAT.

## File naming and sequence semantics

| Segment | Rule |
|---------|------|
| `{sender_id}` | The sender's identifier — a plan id for a `plan` sender, an epic slug for an `orchestrator` sender. Kebab-case; validated as a path-safe identifier before use. |
| `{NNN}` | Zero-padded, three-digit-minimum sequence, allocated per sender, starting at `001` and growing past three digits when a sender exceeds 999 messages. |

Sequence allocation is a **claim, not a scan-then-write**: the next free number is proposed by scanning the live queue (`inbox/`), the sender's foldered archive subdirectory (`inbox/archive/{sender_id}/`), AND any un-migrated flat twin directly under `inbox/archive/` — so a sender whose messages have been retired never re-uses a number an archived twin already holds, in EITHER archive layout — but the exclusive create (`O_CREAT | O_EXCL`) is the atomic step, and it stays scoped to `inbox/` alone. A collision advances to the next sequence and retries, so a concurrent or re-entered finalize cannot clobber an existing message. Reading both archive layouts is what keeps this guarantee across the foldering migration: a partly-foldered archive re-opens no retired sequence.

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

The six BASE fields are required. A message missing any one is rejected as `missing_header_field`. The four message-state fields are optional-with-default (see § Message-state vocabulary): a virgin message carries none of them, so it is byte-identical to how it looked before this vocabulary existed and `envelope_version` need not bump.

| Field | Required | Type | Description |
|-------|:--------:|------|-------------|
| `envelope_version` | Yes | integer | Schema version. Currently `1`. Any other value is rejected — never silently accepted. |
| `sender_type` | Yes | enum | `plan` (an executing plan's OUTBOX message) or `orchestrator` (reserved for orchestrator-to-orchestrator messages). |
| `sender_id` | Yes | identifier | The sender's id. MUST match the `{sender_id}` segment of the filename. |
| `epic` | Yes | slug | The epic the message is addressed to. MUST match the tree the message sits in. |
| `kind` | Yes | enum | `landing`, `finding`, or `candidate-lesson` — see the payload contract below. |
| `created` | Yes | ISO-8601 | UTC compose timestamp (`YYYY-MM-DDTHH:MM:SSZ`). **Preserved across an amend** — it names the message's first filing, never the correction instant. |
| `lifecycle` | No | enum | `live` (default; absent ⇒ `live`), `superseded`, or `stream-end`. The single message-state vocabulary. |
| `revision` | No | integer | Amendment counter; `0` (absent) on a virgin message, incremented by each `amend`. Emitted only when non-zero. |
| `amended` | No | ISO-8601 | UTC timestamp of the most recent `amend`. Present iff `revision >= 1`. |
| `superseded_by` | No | filename | Bare filename of the successor. Present iff `lifecycle=superseded`. |

## Payload contract per kind

The payload is free markdown; the kind tells the orchestrator-side pickup how to consume it. Granularity is **one message per emitted item** — that is what the sequence exists to allocate.

| `kind` | Payload contract |
|--------|------------------|
| `landing` | The plan's landing, carrying the run's facts as a machine-readable `landing-facts` block (what shipped, the PR reference, per-step outcomes and typed facts, token totals) plus an optional narrative `## Residue` section for the irreducibly-narrative half. The payload BODY contract — the required fact keys and the report↔inbox delta they close — is owned by [`landing-payload-spec.md`](landing-payload-spec.md); this table owns only the `kind`. Exactly one per orchestrated finalize run, emitted unconditionally by the `emit-landing` terminal step — including when the plan produced no lesson-bearing signals. |
| `finding` | One observation the plan surfaced that the epic should know about but that is not itself a lesson. |
| `candidate-lesson` | One proposed lesson body, in the same `key=value` + markdown-body shape the lessons corpus uses, so the orchestrator-side pickup can lift it into `manage-lessons` with zero transcoding. The plan performs no global-vs-epic classification — only the orchestrator holds the cross-plan context that judgement needs. |

## Message-state vocabulary

A filed message is corrected through the sanctioned surface, never by a direct file edit (which would break the scripts-only access rule) and never by writing a bare successor (which would leave two unrelated live messages in the queue). The correction verbs all record their mutation in the envelope, so a corrected message is never byte-indistinguishable from a virgin one. All THREE message-state concepts ride **one** field, `lifecycle` — derived from the `manage-lessons` `status` model — rather than a second, parallel enum:

| `lifecycle` | Meaning | Verb | Extra fields |
|-------------|---------|------|--------------|
| `live` | The message as filed and current. The default; an absent `lifecycle` reads as `live`. | `inbox write` | `revision` / `amended` when amended |
| `superseded` | Replaced by a named successor; stays on disk and validates green, but stops presenting as live. | `inbox supersede --by` | `superseded_by` |
| `stream-end` | A terminal control marker: the sender that filed it will send no more. | `inbox close-stream` | — |

- **`amend`** replaces a message's body IN PLACE — the one sanctioned in-place edit — while it **preserves `created`**, stamps `amended`, and bumps a monotonic `revision`. The message stays `live`. Amendment rides a COUNTER and a TIMESTAMP, not a second enum, which is what keeps the vocabulary singular. This is the load-bearing half: an in-place body edit that left the envelope unchanged would replace an authorized bypass with an unauthorized one and fix nothing about the signal. Only a `live`, queued, currently-valid message is amendable.
- **`supersede`** flips the retired message to `lifecycle=superseded` and records `superseded_by`. It does NOT rewrite the body into a redirect stub — the append-only-for-content invariant holds, and the envelope itself is the resolvable tombstone. The successor must resolve in `inbox/` or `inbox/archive/`.
- **`stream-end`** is the stream-termination concept expressed as one more value in this same vocabulary. `inbox close-stream` files a fully-valid marker message (it carries the `finding` kind and a body — the closing note) with `lifecycle=stream-end`, so no message-class branch is needed anywhere; the terminal signal rides `lifecycle`, never `kind`. The drain reads the closure from `inbox list`'s `closed_senders` (see § Drain semantics).

## Invariants

- **Append-only, with one sanctioned in-place edit.** A sender creates new message files and never deletes one. The ONLY sanctioned in-place mutations are `amend` (body correction) and `supersede`/`close-stream` (envelope state) — each records its mutation in the envelope, so no in-place edit is ever invisible. A `superseded` message's body is preserved byte-for-byte.
- **One file per message.** A message is never appended to an existing file; each emitted item gets its own sequence.
- **Own-file-only.** A sender writes only files whose `{sender_id}` segment is its own id.
- **One-way.** The plan writes; the orchestrator drains. A plan never reads the ledger to make a decision.

## Validator error codes

The named validation seam is `validate_envelope(text, expected_epic, filename)` in `scripts/_orchestrator_inbox.py`, surfaced as `orchestrator inbox validate` for one message and as the per-row verdict of `orchestrator inbox list` for the whole queue. Checks run in the fixed order below, so a given malformed message always yields the same code.

| Order | `error` | Rejection condition |
|:-----:|---------|---------------------|
| 1 | `missing_header_field` | One or more of the six BASE header fields is absent or empty. |
| 2 | `unknown_envelope_version` | `envelope_version` is not the supported version. |
| 3 | `invalid_sender_type` | `sender_type` is outside the declared enum. |
| 4 | `invalid_kind` | `kind` is outside the declared enum. |
| 5 | `empty_payload` | No payload body follows the header's blank line. |
| 6 | `epic_mismatch` | The `epic` header disagrees with the epic tree the message sits in. Checked only when an expected epic is supplied. |
| 7 | `filename_sender_mismatch` | The filename's `{sender}` segment disagrees with the `sender_id` header. Checked only when a filename is supplied. |
| 8 | `invalid_lifecycle` | `lifecycle` is present but outside the declared enum (`live` / `superseded` / `stream-end`). |
| 9 | `invalid_revision` | `revision` is present but not a non-negative integer. |
| 10 | `revision_not_monotonic` | The amendment invariant is broken: a `revision >= 1` with no `amended` stamp, or an `amended` stamp with no advanced revision. |
| 11 | `invalid_supersede_state` | `superseded_by` is present without `lifecycle=superseded`, or `lifecycle=superseded` without a `superseded_by`. |

The state checks (8–11) run AFTER the base checks (1–7), so the base rejection codes are unchanged and a message carrying none of the state fields (the virgin `live` case) always reaches success. The table is exhaustive over ENVELOPE-VALIDATION verdicts, not over the whole vocabulary either verb reports. In particular, `inbox validate`'s `location` (`queued` / `archived`) is a *resolution* outcome — where the message was found — and is orthogonal to the verdicts above: an `archived` message runs through the identical checks in the identical order.

`unreadable` is a separate, non-numbered code: it is raised by `cmd_inbox_list` itself, before a message's text ever reaches `validate_envelope`, when the message file cannot be read at all (non-UTF-8 bytes, or the file vanishing mid-drain under a concurrent writer). It is deliberately distinct from every code above so a read failure is never confused with an envelope-validation failure.

## Forward compatibility

`envelope_version` is **fail-closed**: a message whose version is not the supported one is rejected with `unknown_envelope_version`, never accepted on a best-effort basis. The `sender_type` discriminator carries the extension point for future sender classes, so a new sender needs no version bump. Nothing beyond those two extension points is added speculatively.

## Related

- [`persona-plan-orchestrator/standards/orchestration-model.md`](../../persona-plan-orchestrator/standards/orchestration-model.md) — § Ledger Write-Boundary, the contract that sanctions this channel
- [`../SKILL.md`](../SKILL.md) § Canonical invocations — the `inbox write` / `inbox validate` / `inbox list` / `inbox archive` / `inbox detect` / `inbox landing-check` argument surfaces
- [`landing-payload-spec.md`](landing-payload-spec.md) — the machine-readable `landing` payload body contract (required fact keys, the report↔inbox delta)
- [`manage-lessons/standards/file-format.md`](../../manage-lessons/standards/file-format.md) — the lesson body shape a `candidate-lesson` payload carries
