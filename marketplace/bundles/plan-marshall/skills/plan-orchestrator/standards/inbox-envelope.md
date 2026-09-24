# Inbox Envelope Schema

The message format of the epic's inbox channel. An executing plan appends structured messages to its governing epic through this channel and through nothing else; the orchestrator drains the epic queue, and a message aimed at a plan that is currently running is delivered into that plan's own mailbox instead of queued. The write-boundary contract that sanctions the channel lives in [`persona-plan-orchestrator/standards/orchestration-model.md`](../../persona-plan-orchestrator/standards/orchestration-model.md) § Ledger Write-Boundary — this document owns only the message format and its validation.

## Storage location

```text
.plan/orchestrator/{epic}/inbox/{sender_id}-{NNN}.md                          # queued
.plan/orchestrator/{epic}/inbox/to/{plan_id}/{sender_id}-{NNN}.md             # delivered (per addressee)
.plan/orchestrator/{epic}/inbox/to/{plan_id}/consumed/{sender_id}-{NNN}.md    # consumption claim token
.plan/orchestrator/{epic}/inbox/archive/{sender_id}/{sender_id}-{NNN}.md      # retired (per-sender)
```

**Timing is merge-bound, because the address sits on the git-tracked tier.** The epic tree is versioned with the repository, so a message filed from one checkout becomes readable at the same address in another only once the branch carrying it merges. A read therefore sees the messages merged into the checkout it runs in, and a message that has not merged yet is not missing from the address — it has not arrived at it. Nothing about the envelope, the validator, or the sequence allocator changes: the tier decides when a written message becomes visible elsewhere, never what is written.

`inbox/` is created by `orchestrator scaffold` alongside `workstreams/`, `plans/`, `landings/`, and `logs/`. Messages are written ONLY by the `orchestrator inbox write` verb (see [`../SKILL.md`](../SKILL.md) § Canonical invocations), which derives the path from the validated epic slug, `--sender-id`, and — on the delivery route — the validated `--target-plan`, and accepts no caller-supplied output path. There is no argument value that reaches any other path in the epic tree.

`inbox/to/{plan_id}/` is the addressee mailbox a DELIVERED message lands in — one directory per addressed plan, under a **reserved** `to` segment. Like `inbox/archive/` it is not scaffolded and is created on first use, so no existing scaffold constant changes value. Reserving the one segment keeps the addressee namespace closed rather than opening the sibling namespace to every plan id, and keeps the mailbox tree disjoint from both the flat sender-keyed queue and the per-sender archive. The drain's enumeration is non-recursive and admits only FILES matching the message-name grammar, so the mailbox tree is invisible to `inbox list` and no existing tally changes meaning.

`inbox/to/{plan_id}/consumed/` holds the **claim token** a consumption records — one hard link per consumed message, created on first use. It is the atomic device that keeps two readers from both recording a consumption (§ Message-state vocabulary), never the state itself: the consumed message stays at its delivered path carrying `lifecycle=consumed`, which is what keeps a consumed delivery distinguishable from an address nothing was ever delivered to. Like `to/` and `archive/` the segment is not scaffolded, and the mailbox enumeration admits only FILES matching the message-name grammar, so the token directory is invisible to every read.

`inbox/archive/{sender}/` is the retired-message path a consumed QUEUE message is moved to — **foldered per sender**. Neither `inbox/archive/` nor its per-sender subdirectories are scaffolded; each is created on first use by `orchestrator inbox archive`, so no existing scaffold constant changes value. The archive folder is keyed on the SOURCE message's sender, so a message and its `--as-name` recovery twin land in the same subdirectory. A sender segment that is unsafe as a DIRECTORY name (a value valid as a filename component but traversing as a directory, e.g. a `..`-shaped sender) is refused rather than folded into a traversing path. A pre-foldering flat archive is folded by `orchestrator inbox migrate-archive`, which reports the count moved per sender; the sequence allocator, the resolver, and the counter all read BOTH the foldered and flat layouts, so a partly-migrated archive never re-opens a retired sequence number.

## Drain semantics

The orchestrator drains the queue; the two drain verbs are mechanical and carry no judgement.

- **`inbox list` is the enumeration seam.** It returns the queued messages in deterministic (sender, sequence) order, each with its header context and its validation verdict. The scan is non-recursive and admits only files matching the message-name grammar, so nothing under `inbox/archive/` and nothing under `inbox/to/` is enumerated. The payload also names WHICH KIND OF ZERO a `count: 0` is, because **a zero meaning *could not look* and a zero meaning *looked, found nothing* do not share a representation**: `epic_not_found` (`status: error` — no epic tree at all), `inbox_state: missing` (the epic is there but has no `inbox/` directory, so the enumeration could not look), and `inbox_state: present` with `count: 0` (it looked and found nothing). `inbox_dir` reports the absolute path actually scanned. The `inbox_state` discriminator is captured ONCE, immediately before the enumeration loop, so it reports the same observation the enumeration acted on — under a concurrent drain that removes `inbox/` mid-scan the payload can never pair a non-zero `count` with `inbox_state: missing`. An absent `inbox/` is NOT a fault — the verb stays `status: success` so a drain is never aborted by it, and the discriminator rides the payload rather than the status.
- **`inbox list` surfaces each message's lifecycle, and tells a finished stream from an empty queue.** Every row carries `lifecycle`, `revision`, and `superseded_by`, so a revised message is visibly different from a virgin one and a superseded one is visibly retired. The payload also carries `live_count` (VALID messages still presenting as live — excluding `superseded` and `stream-end`) and `closed_senders` (senders that have filed a `stream-end` marker). Together with `invalid_count` those are the drain's zero discriminator, and there are **three** zeros to tell apart, not two:

  | `live_count` | `closed_senders` | `invalid_count` | The state |
  |---|---|---|---|
  | `0` | empty | `0` | **EMPTY** — nothing queued and no sender has declared closure, so a later message is still possible |
  | `0` | non-empty | `0` | **FINISHED** — the named senders filed `stream-end` markers and will send no more |
  | `0` | any | `> 0` | **BLOCKED** — nothing drainable, but messages remain that the drain refuses to consume |

  ⛔ **`live_count: 0` alone is not EMPTY.** `live_count` counts VALID messages presenting as live, so an invalid message is excluded from it exactly as a `superseded` or `stream-end` one is — a queue holding nothing but malformed messages reports `live_count: 0` while carrying work nobody has read. Reading that as an empty queue would claim a completed drain over messages the drain declined. The third zero is BLOCKED, and it is named because the two-way reading silently absorbed it into EMPTY.
- **A malformed message is reported, never skipped.** Each row carries either `valid: true` or the validator's distinct error code from the table below, so a broken message stays visible to the drain instead of disappearing from it, and one bad message never aborts the enumeration.
- **An unreadable message is reported the same way.** A message file that cannot even be read — non-UTF-8 bytes, or the file vanishing mid-drain under a concurrent writer — is reported as one row with `valid: false` and the distinct `error: unreadable` code, not confusable with any envelope-validation code below, and enumeration continues to the next message.
- **Archival is the QUEUE's consume marker.** A message leaves the queue only by being archived, so a re-scan of an already-drained message is a no-op and a repeated `inbox archive` of the same message is idempotent success. The addressee mailbox records consumption differently — in the envelope, with the message left where it was delivered (§ Message-state vocabulary) — because relocating a consumed delivery would make it indistinguishable from a delivery that never happened.
- **`inbox validate` resolves the archive — the consume marker's read-side counterpart.** A name absent from `inbox/` is probed against the sender's foldered `inbox/archive/{sender}/` subdirectory (and any un-migrated flat `inbox/archive/` twin) before the verb answers, so a CONSUMED message resolves to `status: success` with `location: archived` (and `archive_path` set) instead of collapsing into the same not-found answer a never-written message gets. `location: queued` is the live-queue branch. `file_not_found` is thereby narrowed to its true meaning: present at NEITHER path. Without the probe the two states are indistinguishable, and the consume marker is only half-observable — writable by the drain, unreadable by anything after it.
- **Archival is a claim, not a check-then-move.** Mirroring sequence allocation below, the destination is claimed atomically — `os.link`, which never replaces an existing file — and the source is unlinked only once that claim succeeds. Two racing drains therefore cannot both clear a presence check: the loser reports `already_archived` derived from the claim's own outcome instead of faulting on a source the winner already moved. Because the claim is a hard link, the loser's answer is decided by **inode identity**, not by source presence — inside the window between the winner's link and its unlink both paths are one file, and the loser's refused claim resolves to `already_archived` even though the source is still there. `archive_conflict` is reserved for the genuinely distinct case: the destination holds a different file, which the drain never clobbers. This is what makes the idempotent-on-repeat guarantee above hold for a resumed drain as well as a sequential one.
- **A mutating verb never resolves an archived epic.** `inbox archive` relocates a file, so it resolves the epic root strictly: an epic whose active tree has already been archived is refused with `epic_not_found` rather than mutating inside the frozen audit record. The read-side verbs (`inbox list`, `inbox validate`) keep the archived read-fallback.
- **The append-only invariant is unbroken.** Archival RELOCATES the file; it never edits or deletes it. The message body at the archived path is byte-identical to the one the sender wrote.
- **A stranded message is recovered with `inbox archive --as-name`.** A message left undrainable by a pre-fix sequence collision — its default destination already holds a distinct archived record, so `archive_conflict` fires forever — is retired under a non-colliding archived name supplied by `--as-name`. The recovery relocates the file exactly as an ordinary archival does, so the append-only invariant still holds and the existing audit record is never clobbered. The override is **sender-constrained** on top of the bare-filename guard: it must match `{sender_id}-*` for the source message's sender, or the call is refused with `as_name_sender_mismatch` (a path-shaped value is still refused with `invalid_message_name`). The constraint keeps the archive's `{sender}-{seq}`-derived provenance intact, so a recovered file can never be attributed to a different sender.

## Write-side deliverability

`orchestrator inbox write` accepts an optional `--target-plan {plan_id}` naming the plan a message is aimed at. The epic QUEUE is drained BETWEEN plans (§ Invariants), so a message left in it for a plan that is currently **running** would never be read — that plan finishes before the next drain reaches it. Rather than refuse such a message, the write verb **delivers** it: the message is written to the addressee mailbox composed from the channel's `(epic_slug, plan_id)` address, `inbox/to/{plan_id}/`, which is the same address the plan-side read resolves.

The routing decision fires only when `--target-plan` is supplied, and delivers only to a plan whose queue row positively reads as `running`. The row is read through the ledger layout module's assembled view — the same machine authority `orchestrator`'s own running-plans signal reads — and it matches the target when either its `id` or its launched `plan_marshall_plan_id` equals `--target-plan`. Every write names which of the two locations it used in a `destination` field over the closed `queue` / `mailbox` vocabulary, so delivery and queueing are separately assertable without pattern-matching the returned `path`, and names why in a `routing_reason` field whose value set is the `ROUTING_REASONS` tuple in `scripts/_orchestrator_inbox.py` — that tuple, not this table, is authoritative:

| Condition | Outcome |
|-----------|---------|
| `--target-plan` names a plan whose queue row is `running` | `destination: mailbox` — the message is DELIVERED to `inbox/to/{plan_id}/` |
| `--target-plan` is not a path-safe identifier | `status: error, error: invalid_target_plan` |
| `--target-plan` names a non-running plan (landed, parked, or any other non-`running` status), or a plan with no row in the queue — including an absent `queue/` directory | `destination: queue` — the message queues as an ordinary epic-addressed message the orchestrator drains |
| The target's row file, the header, the anchor, or the `queue/` directory could not be read, or the header is absent | `destination: queue` |
| The ledger is still in the monolithic layout (`legacy_layout`) | `destination: queue` — the legacy `plans[]` is refused, never read, so it is never read as naming a running plan |
| `--target-plan` omitted | `destination: queue` — the primary path, unchanged |

⛔ **An unreadable ledger queues; it never delivers.** The running-plan set is derived from a POSITIVE read of the assembled view. An unreadable header or row file, an absent `queue/` directory or absent row, and a `legacy_layout` ledger each leave the target unconfirmed as running, so the message takes the queue branch. A `legacy_layout` ledger is never delivered to, even when its `plans[]` names the target as `running`. Delivery is never inferred from an absence.

**Stream closure is the second write-side refusal, and it is about the SENDER rather than the target.** A sender that has filed a valid `lifecycle=stream-end` marker declared its own stream ended, and `inbox close-stream`'s whole meaning is that the sender will send no more. Writing after that would contradict a signal the drain has already reported through `closed_senders`, so it is refused at write time:

| Condition | Outcome |
|-----------|---------|
| The sender has a valid `lifecycle=stream-end` marker queued in `inbox/` | `status: error, error: stream_closed` — the message is REFUSED and no file is allocated. The error names the existing marker. |
| The sender has no such marker, or has only a marker that fails validation | the write PROCEEDS — an invalid marker is not a closure the drain would honour either, so it is not one here |
| A DIFFERENT sender has closed its stream | the write PROCEEDS — closure is per sender, never epic-wide |

The check runs BEFORE the `--target-plan` routing decision, because whether this sender may write at all does not depend on where the message was aimed — a closed sender is refused whether its message would have queued or been delivered. The scan covers `inbox/` only, never `inbox/archive/`: once the drain consumes and archives the marker, the queue no longer carries the closure and the sender may write again. That bound is deliberate — the queue is the live state — and a sender that must stay closed across a drain is a larger design question this guard does not settle.

Delivery does not widen the ledger write-boundary carve-out. `--target-plan` never becomes a path: it is a validated identifier that SELECTS between the epic queue and one addressee mailbox, both composed inside the same `inbox/` directory from the validated epic slug, so no argument value reaches any other path in the epic tree. Because these are write-side routing outcomes, they are distinct from the envelope-VALIDATION verdicts in § Validator error codes, which govern message FORMAT.

## File naming and sequence semantics

| Segment | Rule |
|---------|------|
| `{sender_id}` | The sender's identifier — a plan id for a `plan` sender, an epic slug for an `orchestrator` sender. Kebab-case; validated as a path-safe identifier before use. |
| `{NNN}` | Zero-padded, three-digit-minimum sequence, allocated per sender within the directory the message is written to, starting at `001` and growing past three digits when a sender exceeds 999 messages. |

Sequence allocation is a **claim, not a scan-then-write**: the next free number is proposed by scanning the directory the message is written to, together with that directory's flat and per-sender `archive/` layouts — so a sender whose messages have been retired never re-uses a number an archived twin already holds, in EITHER archive layout — but the exclusive create (`O_CREAT | O_EXCL`) is the atomic step, and it stays scoped to that same directory. A collision advances to the next sequence and retries, so a concurrent or re-entered finalize cannot clobber an existing message. Reading both archive layouts is what keeps this guarantee across the foldering migration: a partly-foldered archive re-opens no retired sequence.

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

The six BASE fields are required. A message missing any one is rejected as `missing_header_field`. The five message-state fields are optional-with-default (see § Message-state vocabulary): a virgin message carries none of them, so it is byte-identical to how it looked before this vocabulary existed and `envelope_version` need not bump.

| Field | Required | Type | Description |
|-------|:--------:|------|-------------|
| `envelope_version` | Yes | integer | Schema version. Currently `1`. Any other value is rejected — never silently accepted. |
| `sender_type` | Yes | enum | `plan` (an executing plan's OUTBOX message) or `orchestrator` (reserved for orchestrator-to-orchestrator messages). |
| `sender_id` | Yes | identifier | The sender's id. MUST match the `{sender_id}` segment of the filename. |
| `epic` | Yes | slug | The epic the message is addressed to. MUST match the tree the message sits in. |
| `kind` | Yes | enum | `landing`, `finding`, or `candidate-lesson` — see the payload contract below. |
| `created` | Yes | ISO-8601 | UTC compose timestamp (`YYYY-MM-DDTHH:MM:SSZ`). **Preserved across an amend** — it names the message's first filing, never the correction instant. |
| `lifecycle` | No | enum | `live` (default; absent ⇒ `live`), `superseded`, `stream-end`, or `consumed`. The single message-state vocabulary. |
| `revision` | No | integer | Amendment counter; `0` (absent) on a virgin message, incremented by each `amend`. Emitted only when non-zero. |
| `amended` | No | ISO-8601 | UTC timestamp of the most recent `amend`. Present iff `revision >= 1`. |
| `superseded_by` | No | filename | Bare filename of the successor. Present iff `lifecycle=superseded`. |
| `consumed_at` | No | ISO-8601 | UTC timestamp of the consumption. Absent (the default) on every message no reader has taken. Present iff `lifecycle=consumed`. |

## Payload contract per kind

The payload is free markdown; the kind tells the orchestrator-side pickup how to consume it. Granularity is **one message per emitted item** — that is what the sequence exists to allocate.

| `kind` | Payload contract |
|--------|------------------|
| `landing` | The plan's landing, carrying the run's facts as a machine-readable `landing-facts` block (what shipped, the PR reference, per-step outcomes and typed facts, token totals) plus an optional narrative `## Residue` section for the irreducibly-narrative half. The payload BODY contract — the required fact keys and the report↔inbox delta they close — is owned by [`landing-payload-spec.md`](landing-payload-spec.md); this table owns only the `kind`. Exactly one per orchestrated finalize run, emitted unconditionally by the `emit-landing` terminal step — including when the plan produced no lesson-bearing signals. |
| `finding` | One observation the plan surfaced that the epic should know about but that is not itself a lesson. |
| `candidate-lesson` | One proposed lesson body, in the same `key=value` + markdown-body shape the lessons corpus uses, so the orchestrator-side pickup can lift it into `manage-lessons` with zero transcoding. The plan performs no global-vs-epic classification — only the orchestrator holds the cross-plan context that judgement needs. |

## Message-state vocabulary

A filed message is corrected through the sanctioned surface, never by a direct file edit (which would break the scripts-only access rule) and never by writing a bare successor (which would leave two unrelated live messages in the queue). The correction verbs all record their mutation in the envelope, so a corrected message is never byte-indistinguishable from a virgin one. EVERY message-state concept rides **one** field, `lifecycle` — derived from the `manage-lessons` `status` model — rather than a second, parallel enum:

| `lifecycle` | Meaning | Recorded by | Extra fields |
|-------------|---------|-------------|--------------|
| `live` | The message as filed and current. The default; an absent `lifecycle` reads as `live`. | `inbox write` | `revision` / `amended` when amended |
| `superseded` | Replaced by a named successor; stays on disk and validates green, but stops presenting as live. | `inbox supersede --by` | `superseded_by` |
| `stream-end` | A terminal control marker: the sender that filed it will send no more. | `inbox close-stream` | — |
| `consumed` | A reader has TAKEN this delivered message. It stays at its delivered path and stops presenting as live. | `consume_message()` in `scripts/_orchestrator_inbox.py` | `consumed_at` |

- **`amend`** replaces a message's body IN PLACE — a sanctioned in-place edit, enumerated alongside its sibling verb in § Invariants below — while it **preserves `created`**, stamps `amended`, and bumps a monotonic `revision`. The message stays `live`. Amendment rides a COUNTER and a TIMESTAMP, not a second enum, which is what keeps the vocabulary singular. This is the load-bearing half: an in-place body edit that left the envelope unchanged would replace an authorized bypass with an unauthorized one and fix nothing about the signal. Only a `live`, queued, currently-valid message is amendable.
- **`supersede`** flips the retired message to `lifecycle=superseded` and records `superseded_by`. It does NOT rewrite the body into a redirect stub — the append-only-for-content invariant holds, and the envelope itself is the resolvable tombstone. The successor must resolve in `inbox/` or `inbox/archive/`.
- **`stream-end`** is the stream-termination concept expressed as one more value in this same vocabulary. `inbox close-stream` files a fully-valid marker message (it carries the `finding` kind and a body — the closing note) with `lifecycle=stream-end`, so no message-class branch is needed anywhere; the terminal signal rides `lifecycle`, never `kind`. The drain reads the closure from `inbox list`'s `closed_senders` (see § Drain semantics).
- **`consumed`** records that a reader took a DELIVERED message. It flips `lifecycle` and stamps `consumed_at`, and the two move together — either one without the other is rejected as `invalid_consume_state`, so the marker is never half-written. The marked message **stays at its delivered path**: relocating it would leave the mailbox looking like one nothing was ever delivered to, which is precisely the collapse the marker exists to remove.

### Consumption is a claim, not a read-then-mark

Two readers must not both record a consumption of one message. The claim is the same primitive archival uses: `os.link` creates `inbox/to/{plan_id}/consumed/{name}` and never replaces an existing file, so the create IS the claim and every answer is derived from the claim's own outcome rather than from a presence check a racing caller could also clear. The winner then stamps the marker **through the claimed inode** (a truncating write, never an atomic replace), so the message and its claim token stay ONE file and **inode identity** remains the discriminator for every later caller: a refused claim over the same inode is this message's own consumption record, while a refused claim over a DISTINCT inode is a different file's record and is refused with `consume_conflict` rather than clobbered. A claim that is won but cannot be stamped is RELEASED, so a message that was never marked can never report as already consumed.

⛔ **The release half of that guarantee needs a loser half, because inode identity says WHOSE record the token is and not whether that record is FINISHED.** A loser that observes the token between the winner's `os.link` and its stamp sees exactly what a completed consumption looks like by presence alone — and if the winner then fails, it unlinks, and the loser has already reported a consumption that never happened. So a caller that loses the claim decides from the MARKER rather than from the token, waiting out the winner's stamp over a bounded number of re-reads:

| What the loser observed | Outcome |
|-------------------------|---------|
| A COMPLETE marker — `lifecycle=consumed` **and** `consumed_at`, the pair `invalid_consume_state` treats as inseparable | `status: success` with `already_consumed: true`, carrying the ORIGINAL `consumed_at` |
| The claim withdrawn with no complete marker ever seen | `status: error, error: consume_claim_released` — positively, no consumption happened; the message is still unconsumed and the consume may be retried |
| The claim still held, marker still incomplete when the wait ends | `status: error, error: consume_marker_incomplete` — nothing was established, which is neither a release nor a consumption |

Reading only the `consumed_at` half is what made the half-written marker indistinguishable from the finished one, which is why the completeness test is the same inseparable pair the validator already enforces.

### The three delivery states

A mailbox read publishes `delivery_state` beside `mailbox_state`, and the two answer different questions: `mailbox_state` says what the ENUMERATION could see, `delivery_state` says what happened at the address. Three substantive states, plus the discriminator that keeps an unmeasured read out of them:

| `delivery_state` | The state |
|------------------|-----------|
| `consumed` | Mail was delivered here and every readable message carries the marker. |
| `delivered_unconsumed` | Mail is here and at least one message is demonstrably unmarked — a reader still has something to take. |
| `never_delivered` | Nothing has ever been delivered to this address. The mailbox directory is created by the delivery that first writes into it, and consumption marks in place rather than removing, so an absent mailbox is a positive fact about delivery. |
| `unmeasured` | The address could not be inspected (no epic tree, or an unlistable mailbox), or an unreadable message leaves the verdict undecidable. Never a claim about delivery. |

⛔ **`never_delivered` is the state a two-state design loses.** A plan that never received a message and a plan that received one and consumed it must not read alike. Each message row carries its own stated `consumption` (`consumed` / `unconsumed` / `unknown` — the last for a message that could not be READ, so its consumption was never determined), and `consumed_count` / `unconsumed_count` publish the populations the address-level verdict was derived from.

## Invariants

- **Append-only, with three sanctioned in-place edits.** A sender creates new message files and never deletes one. Exactly three surfaces mutate a filed message in place — `amend` (body correction, stamping `amended` plus a monotonic `revision`), `supersede` (envelope state, stamping `lifecycle=superseded` plus a successor pointer), and the consumption claim (envelope state, stamping `lifecycle=consumed` plus `consumed_at`, and confined to the addressee mailbox) — and each records its mutation in the envelope, so no in-place edit is ever invisible. A `superseded` message's body is preserved byte-for-byte, and so is a `consumed` one's: consumption records state in the envelope and never touches the payload. **`close-stream` is an APPEND, not an in-place edit**: it composes a fresh envelope and allocates a new sequenced path, opening no existing file — the same classification [`orchestration-model.md` § Ledger Write-Boundary](../../persona-plan-orchestrator/standards/orchestration-model.md) states.
- **One file per message.** A message is never appended to an existing file; each emitted item gets its own sequence.
- **Own-file-only.** A sender writes only files whose `{sender_id}` segment is its own id.
- **One-way per location, and the ledger is never read by a plan.** The epic QUEUE is one-way: a plan writes to it, the orchestrator drains it, and a plan never reads it. The addressee MAILBOX carries the other direction: a message aimed at a running plan is delivered into `inbox/to/{plan_id}/`, and the addressed plan reads ONLY its own mailbox. What stays absolute across both is the load-bearing half — **a plan never reads the ledger to make a decision**: `status.json`, `queue/`, `resume_anchor.md`, `queue-view.md`, `epic.md`, `workstreams/`, `plans/`, and `landings/` remain orchestrator-only, and a mailbox read is a read of messages addressed to that plan, never of the epic's own state.

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
| 8 | `invalid_lifecycle` | `lifecycle` is present but outside the declared enum (`live` / `superseded` / `stream-end` / `consumed`). |
| 9 | `invalid_revision` | `revision` is present but not a non-negative integer. |
| 10 | `revision_not_monotonic` | The amendment invariant is broken: a `revision >= 1` with no `amended` stamp, or an `amended` stamp with no advanced revision. |
| 11 | `invalid_supersede_state` | `superseded_by` is present without `lifecycle=superseded`, or `lifecycle=superseded` without a `superseded_by`. |
| 12 | `invalid_consume_state` | `consumed_at` is present without `lifecycle=consumed`, or `lifecycle=consumed` without a `consumed_at`. |

The state checks (8–12) run AFTER the base checks (1–7), so the base rejection codes are unchanged and a message carrying none of the state fields (the virgin `live` case) always reaches success. The table is exhaustive over ENVELOPE-VALIDATION verdicts, not over the whole vocabulary either verb reports. In particular, `inbox validate`'s `location` (`queued` / `archived`) is a *resolution* outcome — where the message was found — and is orthogonal to the verdicts above: an `archived` message runs through the identical checks in the identical order.

`unreadable` is a separate, non-numbered code: it is raised by `cmd_inbox_list` itself, before a message's text ever reaches `validate_envelope`, when the message file cannot be read at all (non-UTF-8 bytes, or the file vanishing mid-drain under a concurrent writer). It is deliberately distinct from every code above so a read failure is never confused with an envelope-validation failure.

## Forward compatibility

`envelope_version` is **fail-closed**: a message whose version is not the supported one is rejected with `unknown_envelope_version`, never accepted on a best-effort basis. The `sender_type` discriminator carries the extension point for future sender classes, so a new sender needs no version bump. Nothing beyond those two extension points is added speculatively.

## Related

- [`persona-plan-orchestrator/standards/orchestration-model.md`](../../persona-plan-orchestrator/standards/orchestration-model.md) — § Ledger Write-Boundary, the contract that sanctions this channel
- [`../SKILL.md`](../SKILL.md) § Canonical invocations — the `inbox write` / `inbox amend` / `inbox supersede` / `inbox close-stream` / `inbox validate` / `inbox list` / `inbox read` / `inbox archive` / `inbox migrate-archive` / `inbox detect` / `inbox landing-check` argument surfaces, one `### inbox {verb}` section each
- [`landing-payload-spec.md`](landing-payload-spec.md) — the machine-readable `landing` payload body contract (required fact keys, the report↔inbox delta)
- [`manage-lessons/standards/file-format.md`](../../manage-lessons/standards/file-format.md) — the lesson body shape a `candidate-lesson` payload carries
