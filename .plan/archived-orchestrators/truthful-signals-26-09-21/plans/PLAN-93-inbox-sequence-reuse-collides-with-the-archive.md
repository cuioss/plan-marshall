# PLAN-93: Inbox Sequence Numbers Restart After A Drain And Collide Irrecoverably With The Archive

epic: truthful-signals
workstream: WS-01

> Post-merge finding on **#1027** (PLAN-56), raised by **PR-Agent** and verified first-party against
> `main` before staging. Small, well-specified, and **unresolvable when it fires** — which is why it is
> its own plan rather than a fold.

## Objective

`next_sequence` allocates a message's `{sender_id}-{NNN}.md` name by scanning `inbox/` only. Once
`cmd_inbox_archive` moves consumed messages to `inbox/archive/`, they are unlinked from `inbox/`, so a
later message from the same `sender_id` restarts at `001` and **collides with the archived copy**. The
collision surfaces at archive time as an `archive_conflict` with **no recovery path**. Make sequence
allocation account for archived messages.

## Mechanism — OBSERVED, verified at HEAD

- `_orchestrator_inbox.py:250-265` — `next_sequence` iterates `inbox_dir.iterdir()` (non-recursive) and
  returns `highest + 1`. Nothing consults the archive.
- `:268-276` — `list_messages`' own docstring confirms the scan is non-recursive and *"nothing under the
  `archive/` subdirectory is ever enumerated"*.
- `cmd_inbox_archive` (`:625-676`) claims the destination with **`os.link`** — which never replaces an
  existing destination — and unlinks the source **only after** the claim succeeds (`:675`).
- ⇒ After a drain, `inbox/` is empty, so `next_sequence` returns `1`. The `O_EXCL` create **succeeds**
  (nothing in `inbox/` to collide with), so the defect is **not** caught at write time. It fires later,
  at archive time: `os.link` raises `FileExistsError` against the archived `-001.md`.

**⭐ What actually happens on collision — and it is NOT data loss.** The `FileExistsError` handler
(`:635-659`) discriminates by **inode identity**: `source.samefile(dest)`. A concurrent-drain winner
shares the inode → idempotent success. A **genuinely distinct** record → `archive_conflict`, *"refusing
to clobber the audit record"*. In the sequence-reuse case the new message is a different inode, so the
guard fires **correctly**. **The archived audit record is protected and the source is never unlinked.**

**⇒ The real consequence is a PERMANENTLY UNDRAINABLE MESSAGE.** The message stays in `inbox/` forever:
it can never be archived, so every subsequent drain re-encounters it, `inbox list` keeps returning it,
and an `analyze` inbox-scan re-consumes the same content on every pass. **The defect breaks drain
idempotence and re-processes a message indefinitely** — it does not destroy anything.

⚠ **Therefore the archive guard is CORRECT and must not be relaxed.** The error is the fail-closed
refusal doing its job; the bug is **upstream, in allocation**. ⛔ **Do not "fix" this by weakening the
`os.link` claim, by allowing a replace, or by treating a distinct-inode collision as idempotent
success** — any of those would trade an unrecoverable-but-loud state for silent audit-record loss,
which is this epic's own anti-pattern.

⚠ **The O_EXCL claim-and-retry that makes allocation safe within `inbox/` is what hides this**: it
guarantees uniqueness against the wrong set — the live directory, not the namespace. A guard that works
correctly while protecting the wrong invariant.

**Live precondition on this epic right now:** the 13 messages drained on 2026-07-28 sit in
`inbox/archive/` as `terminal-title-channel-reconciliation-001..009` and
`manifest-composer-honours-declared-contract-001..004`. Any future message from either `sender_id`
reproduces this immediately.

**Severity — real but bounded; state it honestly.** It requires the *same* `sender_id` to write again
after an archive. Shipped plans do not re-run, so the common case is safe. The reachable cases are: a
plan that finalizes more than once (a loop-back, a retried finalize, or a branch that produces several
PRs — **PLAN-75 ran as three**), and any plan re-staged under an existing slug. Low frequency,
**unrecoverable when hit**.

## Deliverables

### D1 — sequence allocation accounts for the archive

`next_sequence` scans `inbox_dir` **and** `inbox_dir / INBOX_ARCHIVE_SUBDIR`, taking the max across
both. (This is PR-Agent's proposed fix and it is correct as stated.) ⚠ **Do not silently widen the
`O_EXCL` claim to the archive** — the create must stay scoped to `inbox/`; only the *starting number*
changes. Widening the claim would make a live message's write depend on archive state.

### D2 — an undrainable message gets a recovery, and the drain refuses to loop on it

**The `archive_conflict` refusal stays exactly as it is** — it protects the audit record and is the
correct fail-closed behaviour. Two things are owed around it:

(a) **A documented operator recovery.** Today the error names the problem and no remedy. With D1 the
collision becomes unreachable for new messages, but any message *already* stranded in `inbox/` stays
stranded. Give it a way out (a rename-and-retry, or an `--as-name` override on archive) and document it.
(b) ⚠ **The drain must not silently loop.** Establish what `analyze`'s inbox-scan does when a message
fails to archive mid-drain — halt loudly, or skip and continue? **If it skips, the same message is
re-consumed on every future drain and its content re-routed each time**, which is the actual harm here.
The scan must surface a stuck message rather than re-processing it indefinitely. Verify the current
behaviour before choosing (verify-at-outline).

### D3 — tests

(a) Archive a message, then allocate for the same `sender_id`: the new sequence is **greater than the
archived maximum** — **verified to FAIL against pre-fix code**, where it returns `1`.
(b) Archiving that message succeeds rather than raising `archive_conflict`.
(c) A sender with no archived messages is unaffected.
(d) Allocation still works when `archive/` does not exist.
(e) ⚠ **The protective behaviour is PINNED, not just left alone**: a genuinely distinct message whose
name already exists in `archive/` still returns `archive_conflict` and **still leaves the source in
`inbox/`** — assert both, so a later refactor cannot turn the refusal into a clobber.
(f) The concurrent-drain path still resolves as idempotent success via inode identity (`samefile`),
distinct from (e) — the two must not collapse into one branch.

Three deliverables — small by design.

## Claim Labels

All mechanism claims above are **OBSERVED**, read at HEAD after #1027 merged. The severity assessment
is **orchestrator-derived** — re-derive rather than inherit. **HYPOTHESIS:** that no other caller
depends on `next_sequence` returning an inbox-only maximum — confirm by enumerating its callers at
outline (`:316` is the only one found; verify-at-outline).

## Expected Surface

- `marshall-orchestrator/scripts/_orchestrator_inbox.py` — `next_sequence` `:250-265`,
  `allocate_message_path` (`:316` caller), the archive helper, and `INBOX_ARCHIVE_SUBDIR`
- `marshall-orchestrator/SKILL.md` — the `inbox archive` documentation, if D2 changes the error contract
- `test/plan-marshall/marshall-orchestrator/**` — including `test_inbox_drain_contract.py`, the
  contract suite #1027 shipped

**Disjointness:** `marshall-orchestrator` only. Disjoint from PLAN-92 (`automatic-review` /
`workflow-integration-github`), PLAN-86 (`phase-5-execute`), PLAN-88 (`manage-build-server`),
PLAN-90 (`manage-lessons`), PLAN-87 (`script-shared` / `pm-dev-oci`).
⚠ **Overlaps PLAN-49** (renames `marshall-orchestrator` → `plan-orchestrator`) — PLAN-49 stays last and
is drain-gated, so land this well before it.

## Dependencies and Sequencing

- Depends on: none. #1027 has landed; the defect is live on `main`.
- ⚠ **Emit early.** The epic's own inbox is the affected surface, and every orchestrated plan writes to
  it. The longer it runs, the more archived sender_ids accumulate as latent collisions.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/truthful-signals/plans/PLAN-93-inbox-sequence-reuse-collides-with-the-archive.md"
```

## Write-Boundary

Repository source + tests only. NO writes to `.plan/local/orchestrator/` **ledger state**; the
`inbox/` channel is the sanctioned exception. See
`persona-marshall-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
