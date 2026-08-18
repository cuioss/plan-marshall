# Gaps — 250-inbox-has-no-amend-or-supersede-verb

**Source:** verification.md (same directory)   **Open items:** 10

The core of the plan is sound: all six deliverables are implemented, both mutation checks (the D5(e) sequence-reuse control and the D1 envelope-stamp control) turned the plan's own tests RED against the naive implementation, and 42/224/563 tests pass. Every gap below is either an incomplete sweep of statements the change made stale, or the consumer-side half that was shipped as declared residue.

## G1 — List the four new envelope-state rejection codes in the `inbox validate` surface doc

- **Kind:** incomplete-sweep
- **Severity:** medium
- **Where:** `marketplace/bundles/plan-marshall/skills/plan-orchestrator/SKILL.md:242` — § `inbox validate`; and the guard test `test/plan-marshall/plan-orchestrator/test_inbox_channel_contract.py:926` — `test_inbox_validate_still_lists_every_retained_rejection_code`
- **What is wrong:** The sentence enumerates the codes `inbox validate` returns on envelope rejection and stops at the seven pre-existing ones (`missing_header_field` … `filename_sender_mismatch`), even though `_validate_state_fields` added four more that the verb genuinely returns. Executed against the live handler: a message carrying `lifecycle=retired` makes `cmd_inbox_validate` return `error: invalid_lifecycle`, a code that appears nowhere in that section. The doc-contract test that exists precisely to stop this list going stale asserts only the seven old codes, so CI does not catch the omission.
- **Why it matters:** A caller reading the canonical invocation doc builds its error handling from that list and will treat `invalid_lifecycle` / `invalid_revision` / `revision_not_monotonic` / `invalid_supersede_state` as unknown failures. It is also the exact defect class this epic is named for — a statement that is not wrong about what it says, but has quietly stopped being complete.
- **Fix:** Extend the enumeration at `SKILL.md:242` to include `invalid_lifecycle`, `invalid_revision`, `revision_not_monotonic`, and `invalid_supersede_state`, keeping the "checked in that order" clause accurate (they run after the seven base checks). Add those four codes to the tuple in `test_inbox_validate_still_lists_every_retained_rejection_code` so the list is pinned.
- **Done when:** The `### inbox validate` section names all eleven envelope-validation codes and the contract test fails if any one is removed.
- **Module/topic:** `plan-orchestrator` — SKILL.md canonical invocations + inbox doc-contract tests

## G2 — Reconcile `cleanup.md` Step 9's "no quiescence signal exists" with the landed `stream-end` signal

- **Kind:** stale-statement
- **Severity:** medium
- **Where:** `marketplace/bundles/plan-marshall/skills/plan-orchestrator/workflow/cleanup.md:105-115` — Step 9 (Phase C), fact 2
- **What is wrong:** The step states as a plain fact, not a hypothetical: "**No quiescence signal exists today**, and none will arrive until a successor spec supplies one", and refuses to drain the inbox on that basis every run. Since PR #1198, `inbox close-stream` files a `lifecycle=stream-end` marker and `inbox list` returns `closed_senders` — a sender-declared "this stream will send no more", which is the emission-quiescence concept the step is waiting for. `cleanup.md` was last touched by #1183 and has not been reconciled. Whether `closed_senders` fully satisfies the precondition is a judgement the doc must now make explicitly; what it cannot keep doing is asserting the signal does not exist.
- **Why it matters:** An asserted absence that the tree contradicts is the highest-risk statement class this epic tracks. Either the archive drain is being refused on a premise that no longer holds, or the premise needs narrowing — and a reader today cannot tell which.
- **Fix:** Rewrite fact 2 of Step 9 to name `inbox list`'s `closed_senders` / `live_count` explicitly, and state one of two things: (a) the drain may now proceed for a sender present in `closed_senders`, wiring it into the deferred-mechanism block already written at `cleanup.md:115-125`; or (b) precisely why a per-sender stream closure does not amount to epic-wide emission quiescence, so the refusal survives with a true reason. Do not leave the absolute claim standing.
- **Done when:** Step 9 no longer asserts that no quiescence signal exists, and either drains on `closed_senders` or names the specific shortfall of that signal.
- **Module/topic:** `plan-orchestrator` — workflow/cleanup.md

## G3 — Teach the `analyze` drain to consume `lifecycle`, `live_count`, and `closed_senders`

- **Kind:** omission
- **Severity:** medium
- **Where:** `marketplace/bundles/plan-marshall/skills/plan-orchestrator/workflow/analyze.md:57-93` — Step 3 (inbox scan) drain loop
- **What is wrong:** The drain loop routes every row returned by `inbox list` on `kind` alone and archives it. The strings `lifecycle`, `live_count`, and `closed_senders` do not appear in the file. Two concrete consequences follow from the code as landed: a `superseded` message is drained and reconciled as ordinary work even though its envelope says it was retired in favour of a successor, and a `stream-end` marker — which carries `kind=finding` by design (`_orchestrator_inbox.py:110-116`) — is routed through the finding branch and absorbed as a substantive observation rather than read as a control record. The plan's D3 done-when ("the drain can tell an empty queue from a finished one") is satisfied at the script surface only.
- **Why it matters:** Every supersession recorded through the new verb is invisible to the only consumer of the queue, so the correction surface changes nothing observable end to end; and using `close-stream` today actively injects a false finding into the epic ledger.
- **Fix:** In `analyze.md` Step 3, add two rules before the kind-routing branch: skip a row whose `lifecycle` is `superseded` (record it as retired-by-successor, archive it, do not run its branch), and treat a row whose `lifecycle` is `stream-end` as a control record — archive it and note the sender's closure, never route it to the `finding` branch. In Step 6's `drained[]` reporting, key the empty-vs-finished conclusion on `live_count` plus `closed_senders` rather than on `count`.
- **Done when:** A drain over a queue containing one superseded message and one stream-end marker produces neither a reconciled landing nor an absorbed finding for either, and reports the sender as closed.
- **Module/topic:** `plan-orchestrator` — workflow/analyze.md (the consumer-side follow-up the report declared as residue)

## G4 — Run the physical archive migration and report the per-sender counts

- **Kind:** omission
- **Severity:** medium
- **Where:** the repository's `.plan/local/orchestrator/{epic}/inbox/archive/` trees — `cmd_inbox_migrate_archive` in `marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/_orchestrator_inbox.py:1667`
- **What is wrong:** D4's *Done when* has three clauses — "the archive is foldered, the existing files are migrated, and the count moved per sender is reported". Only the first is met. The run had no `.plan/` tree (cloud clone), and this checkout has `/home/user/plan-marshall/.plan` with no `local/orchestrator/` under it, so the real archives named in the plan (~652 files across three epics) have never been folded and no per-sender count has ever been reported. The migration verb ships and is tested; it has never been executed against a real archive.
- **Why it matters:** Until it runs, every archive stays flat and the dual-layout reads are the only thing holding sequence allocation correct. That mitigation is real but it is a compatibility shim, and the plan's own rule — a silent relocation is indistinguishable from a lossy one — cannot be checked for a migration that has not happened.
- **Fix:** On a machine that holds `.plan/local/orchestrator/`, run `orchestrator inbox migrate-archive --slug {epic}` for every epic (including archived-epic trees where reachable), record `moved_by_sender` / `moved_total` / `skipped[]` per epic, and reconcile the totals against the pre-migration file count for each sender before and after.
- **Done when:** Every epic's `inbox/archive/` holds only per-sender subdirectories, and the per-sender moved counts are recorded somewhere durable with a before/after reconciliation.
- **Module/topic:** `plan-orchestrator` — operational migration of the orchestrator store

## G5 — Complete the verb enumeration in `inbox-envelope.md` § Related

- **Kind:** incomplete-sweep
- **Severity:** medium
- **Where:** `marketplace/bundles/plan-marshall/skills/plan-orchestrator/standards/inbox-envelope.md:151`
- **What is wrong:** The Related pointer reads "the `inbox write` / `inbox validate` / `inbox list` / `inbox archive` / `inbox detect` / `inbox landing-check` argument surfaces". Verified against the pre-commit file (`git show 51d1c9bc^:…`, line 128): this was the complete five-verb list before the plan, and the plan added four verbs without touching it (a later plan appended `landing-check`). `amend`, `supersede`, `close-stream`, and `migrate-archive` are missing, while the same document devotes a whole § Message-state vocabulary to three of them.
- **Why it matters:** The schema document is where a reader goes to learn the channel; its own index of the argument surfaces omits the verbs the document spends a section describing, so a reader can conclude no such invocation is documented.
- **Fix:** Extend the line at `inbox-envelope.md:151` to name `inbox amend`, `inbox supersede`, `inbox close-stream`, and `inbox migrate-archive` alongside the existing six.
- **Done when:** The Related line enumerates all ten `inbox` sub-verbs registered in `_add_inbox_group`.
- **Module/topic:** `plan-orchestrator` — standards/inbox-envelope.md

## G6 — Update the `inbox` argparse group help string in production code

- **Kind:** stale-statement
- **Severity:** medium
- **Where:** `marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/orchestrator.py:2536-2541` — the `help=` literal on the `inbox` subparser
- **What is wrong:** The help text still reads "Epic inbox OUTBOX and drain: append, validate, list, or archive a message, or detect a plan's orchestration context." That is the pre-plan five-verb description; the commit updated the module docstring (`orchestrator.py:57-69`) and the `_add_inbox_group` docstring but not this user-facing string literal. Ten sub-verbs are registered. The plan's own claim-label table names `inbox --help` as the confirm/refute artifact for the verb-group surface, which makes this line part of the artifact the plan was measured against.
- **Why it matters:** It is the one-line summary an operator sees in `orchestrator --help`, and it describes a surface that no longer exists — the correction verbs the whole plan added are invisible there.
- **Fix:** Replace the literal with a summary that covers correction (`amend`/`supersede`), stream termination (`close-stream`), and archive foldering (`migrate-archive`) alongside append/validate/list/archive/detect — mirroring the already-correct wording at `orchestrator.py:57-69`.
- **Done when:** `orchestrator inbox --help`'s group description names the correction and stream-termination verbs.
- **Module/topic:** `plan-orchestrator` — scripts/orchestrator.py argument surface

## G7 — Stop listing `close-stream` as an in-place mutation

- **Kind:** doc-drift
- **Severity:** low
- **Where:** `marketplace/bundles/plan-marshall/skills/plan-orchestrator/standards/inbox-envelope.md:117` — § Invariants, "Append-only, with one sanctioned in-place edit"
- **What is wrong:** The bullet states "The ONLY sanctioned in-place mutations are `amend` (body correction) and `supersede`/`close-stream` (envelope state)". `cmd_inbox_close_stream` (`_orchestrator_inbox.py:1607-1664`) mutates nothing — it composes a new envelope and calls `allocate_message_path`, creating a brand-new message file. It is a pure append, the opposite of what the bullet classifies it as.
- **Why it matters:** The bullet is the canonical statement of how far the append-only invariant has been relaxed. Overstating the relaxation makes the invariant look weaker than it is and misleads anyone reasoning about which verbs can rewrite an existing file.
- **Fix:** Move `close-stream` out of the in-place list: state that the only in-place mutations are `amend` (body) and `supersede` (envelope state), and that `close-stream` appends a new terminal marker like any other write.
- **Done when:** The Invariants bullet classifies `close-stream` as an append, not an in-place mutation.
- **Module/topic:** `plan-orchestrator` — standards/inbox-envelope.md

## G8 — Correct the module docstring's description of the archive write target

- **Kind:** doc-drift
- **Severity:** low
- **Where:** `marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/_orchestrator_inbox.py:30-35` — module docstring, the drain-surface paragraph
- **What is wrong:** It still says "the only path they ever write is ``inbox/archive/`` joined with either the source message's own bare filename or the bare, sender-constrained ``--as-name`` override". Post-foldering the write target is `inbox/archive/{sender}/` joined with that name (`cmd_inbox_archive:1285-1298`). The same paragraph's foldering statement two lines earlier (`:25-28`) is correct, so the module docstring contradicts itself. The report recorded two sibling docstring fixes (finding 1 and 2) but this third restatement was not swept.
- **Why it matters:** The module docstring is the first thing a maintainer reads, and it is where the write-boundary-by-construction argument is made; a wrong path there weakens the argument it exists to carry.
- **Fix:** Change the phrase to `inbox/archive/{sender}/` joined with the bare source filename or the sender-constrained `--as-name` override, keeping the by-construction claim intact.
- **Done when:** No sentence in the module docstring describes a flat `inbox/archive/{name}` write target.
- **Module/topic:** `plan-orchestrator` — scripts/_orchestrator_inbox.py

## G9 — Make the empty-vs-finished discriminator account for invalid messages

- **Kind:** stale-statement
- **Severity:** low
- **Where:** `marketplace/bundles/plan-marshall/skills/plan-orchestrator/standards/inbox-envelope.md:21` and `SKILL.md:253`; computed at `_orchestrator_inbox.py:1140-1151`
- **What is wrong:** Both docs say `live_count: 0` with an empty `closed_senders` is "an EMPTY queue that may yet receive more". Executed against the live handler with one message whose `kind` header was corrupted: `count 1, invalid_count 1, live_count 0, closed_senders []`. The queue is not empty — it holds a message the drain deliberately leaves un-archived (`analyze.md:78`) — yet the documented discriminator reads it as empty. A stuck invalid message is therefore indistinguishable from an empty queue for a consumer keying on `live_count` alone.
- **Why it matters:** The whole point of `live_count`/`closed_senders` is to make two kinds of zero distinguishable; a third kind of zero (looked, found only undrainable messages) collapses into one of them.
- **Fix:** Amend both sentences to state that `live_count: 0` with an empty `closed_senders` means empty **only when `invalid_count` is also 0**, and name the third case explicitly (`live_count: 0`, `invalid_count > 0` — a queue blocked on messages the drain refuses to consume). Add a test asserting the three-way discrimination.
- **Done when:** Both docs state the `invalid_count` condition and a test pins the blocked-queue case as distinct from empty.
- **Module/topic:** `plan-orchestrator` — standards/inbox-envelope.md + SKILL.md + inbox listing tests

## G10 — Finish `report-01.md`: remove the duplicate `_pending_` sections and correct the test counts

- **Kind:** stale-statement
- **Severity:** low
- **Where:** `doc/plans/truthful-signals/250-inbox-has-no-amend-or-supersede-verb/report-01.md:71` and `:149-163`
- **What is wrong:** Two things. (a) The report ends with a second, unfilled copy of four sections — `## Cost`, `## Contract check (Step 9)`, `## What have we learned (Step 9)`, `## Residue` — each containing only `_pending_`, after all four were filled at lines 113–147; leftover template scaffolding that makes the run's record read as abandoned. (b) Line 71 states "All 41 tests in the new file pass" and "all 223 inbox tests"; the test file is unchanged since the merge and carries **42** test functions (all passing), and the four inbox files total **224** — re-derived today with `pytest -o addopts="" -q`.
- **Why it matters:** The run report is the artifact the orchestrator collects; a duplicated `_pending_` tail invites a reader to conclude the run never finished, and a stated count that the tree contradicts is exactly the signal-integrity defect this epic exists to remove.
- **Fix:** Delete lines 149–163 (the duplicated `_pending_` block) and correct the two counts at line 71 to 42 and 224.
- **Done when:** `report-01.md` carries each Step-9 section exactly once, filled, and its stated test counts match a re-run.
- **Module/topic:** `doc/plans/truthful-signals/250-…` — run report hygiene

## Considered and NOT raised as gaps

- **`revision_not_monotonic` names a co-presence check, not a monotonicity check** (`_orchestrator_inbox.py:509-511`). The validator sees one file's header and cannot observe a revision decreasing over time; true monotonicity is guaranteed only by `cmd_inbox_amend`'s `+1` at `:1500`. Both the code comment and `inbox-envelope.md:137` describe the actual condition accurately, so the surface is self-consistent and the name is the only imprecision — noted, not raised.
- **`_resolve_live_message` is named for a filter it does not apply.** Its docstring (`:1398-1411`) states plainly that it does not filter on `lifecycle` and that the guard is the caller's; this was the sub-agent's finding 3 and it was fixed correctly.
- **`_foldered_archive_dir` accepts the `NO_PLAN` sentinel** because `validate_plan_id` carves it out ahead of its regex. `NO_PLAN` is still a safe directory name (no separator, no traversal), so the guard's purpose holds; only the report's parenthetical describing the predicate as the bare regex is imprecise.
