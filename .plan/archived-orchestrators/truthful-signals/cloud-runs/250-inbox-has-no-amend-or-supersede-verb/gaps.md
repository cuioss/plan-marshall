# Gaps — 250-inbox-has-no-amend-or-supersede-verb

**Source:** verification.md (same directory)   **Open items:** 12

The code half of the plan is sound: the message-state vocabulary is singular and real, and **all five D5 controls plus the D4 directory-safety guard were independently mutation-proven non-vacuous** during adversarial review (see verification.md § Adversarial review), with 42/224/563 tests re-derived green. What is NOT complete is D4's physical migration (G4) and the consumer half (G3) — which is why the verdict is `partially-implemented` rather than `implemented-with-gaps`. The remaining gaps are stale or incomplete restatements the change left behind, plus one unenforced invariant found by execution (G12).

## G1 — List the four new envelope-state rejection codes in the `inbox validate` surface doc

- **Kind:** incomplete-sweep
- **Severity:** medium
- **Where:** `marketplace/bundles/plan-marshall/skills/plan-orchestrator/SKILL.md:242` — § `inbox validate`; and the guard test `test/plan-marshall/plan-orchestrator/test_inbox_channel_contract.py:926` — `test_inbox_validate_still_lists_every_retained_rejection_code`
- **What is wrong:** The sentence enumerates the codes `inbox validate` returns on envelope rejection and stops at the seven pre-existing ones (`missing_header_field` … `filename_sender_mismatch`), even though `_validate_state_fields` added four more that the verb genuinely returns. Executed against the live handler (re-executed during adversarial review): a message carrying `lifecycle=retired` makes `cmd_inbox_validate` return `error: invalid_lifecycle`, a code that appears nowhere in that section. All four new codes are returned through the same seam — `validate_envelope` calls `_validate_state_fields` at `_orchestrator_inbox.py:484-486` and returns its code directly. The doc-contract test that exists precisely to stop this list going stale asserts an eight-entry tuple (`test_inbox_channel_contract.py:933-943` — the seven base envelope codes plus the resolution-side `invalid_message_name`) and none of the four new ones, so CI does not catch the omission.
- **Why it matters:** A caller reading the canonical invocation doc builds its error handling from that list and will treat `invalid_lifecycle` / `invalid_revision` / `revision_not_monotonic` / `invalid_supersede_state` as unknown failures. It is also the exact defect class this epic is named for — a statement that is not wrong about what it says, but has quietly stopped being complete.
- **Fix:** Extend the enumeration at `SKILL.md:242` to include `invalid_lifecycle`, `invalid_revision`, `revision_not_monotonic`, and `invalid_supersede_state`, keeping the "checked in that order" clause accurate (they run after the seven base checks). Add those four codes to the eight-entry tuple in `test_inbox_validate_still_lists_every_retained_rejection_code` (`test_inbox_channel_contract.py:933`) so the list is pinned.
- **Done when:** The `### inbox validate` section names all eleven envelope-validation codes and the contract test fails if any one is removed (verified by deleting one code from the section and seeing the test go red).
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
- **Severity:** high — re-severitied from `medium` during adversarial review: the routing table at `analyze.md:70-76` is exhaustive over `kind` and has no escape hatch, so this is not a missing nicety but **wrong behaviour on the surface the plan shipped**. A `superseded` message whose `kind` is `landing` is routed to Step 4, which performs a **full ship reconciliation** — writing `landings/PLAN-NN.md` and running `queue --transition ... --status shipped` — for a landing its own envelope records as retired in favour of a successor. That is a false ledger write, not a cosmetic omission.
- **Where:** `marketplace/bundles/plan-marshall/skills/plan-orchestrator/workflow/analyze.md:57-93` — Step 3 (inbox scan) drain loop; the disposition accounting it feeds is at `analyze.md:225`
- **What is wrong:** The drain loop routes every row returned by `inbox list` on `kind` alone and archives it. Re-swept during adversarial review: `grep -n 'lifecycle\|live_count\|closed_senders\|superseded\|stream-end'` over `analyze.md` returns exactly one hit — line 52, the unrelated phrase "closed lifecycle" — so none of the three state fields is read anywhere in the file. Two concrete consequences follow from the code as landed: a `superseded` message is drained and reconciled as ordinary work even though its envelope says it was retired in favour of a successor, and a `stream-end` marker — which carries `kind=finding` by design (`_orchestrator_inbox.py:110-116`) — is routed through the finding branch and absorbed as a substantive observation rather than read as a control record. The plan's D3 done-when ("the drain can tell an empty queue from a finished one") is satisfied at the script surface only.
- **Why it matters:** Every supersession recorded through the new verb is invisible to the only consumer of the queue, so the correction surface changes nothing observable end to end; a retired landing can still be reconciled as a real ship; and using `close-stream` today actively injects a false finding into the epic ledger.
- **Fix:** In `analyze.md` Step 3, add two rules **before** the `kind`-routing table at lines 70-76: skip a row whose `lifecycle` is `superseded` (record it as retired-by-successor, archive it, do not run its branch), and treat a row whose `lifecycle` is `stream-end` as a control record — archive it and note the sender's closure, never route it to the `finding` branch. Because Step 3 item 4's archival path is shared, both new dispositions still archive, so `analyze.md:225`'s closure arithmetic must be extended in the same edit: add the two disposition tokens to the `drained[]` vocabulary and restate the invariant as `messages_archived + messages_invalid + messages_archive_failed == messages_scanned` with the two new tokens counted inside `messages_archived`, or the equation stops closing the moment either rule fires. In Step 6's reporting, key the empty-vs-finished conclusion on `live_count` plus `closed_senders` rather than on `count`.
- **Done when:** A drain over a queue containing one `kind=landing` `lifecycle=superseded` message and one `stream-end` marker writes no `landings/` record, makes no `queue --transition` call, absorbs no finding, reports the sender in the closed set, and still satisfies the `analyze.md:225` count equation.
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
- **Done when:** The Related line enumerates all ten `inbox` sub-verbs registered in `_add_inbox_group` — re-derived during adversarial review from the `actions.add_parser` calls in `orchestrator.py:2546-2721`: `write`, `amend`, `supersede`, `close-stream`, `validate`, `list`, `archive`, `migrate-archive`, `detect`, `landing-check`. Each has its own `### inbox {verb}` section in `SKILL.md` (lines 187, 197, 206, 215, 224, 244, 265, 274, 283, 313), so every name the Related line would add resolves at the target.
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
- **What is wrong:** The bullet states "The ONLY sanctioned in-place mutations are `amend` (body correction) and `supersede`/`close-stream` (envelope state)". `cmd_inbox_close_stream` (`_orchestrator_inbox.py:1607-1664`) mutates nothing — it composes a fresh envelope with `compose_envelope(...)` and claims a new path with `allocate_message_path` (`:1645-1653`), never opening an existing message. It is a pure append, the opposite of what the bullet classifies it as. Two further defects confirmed in the same bullet during adversarial review: (i) the bolded lead reads "with **one** sanctioned in-place edit" while the body names **three** verbs — the same document's own § Message-state vocabulary bullet at `:111` calls `amend` "the one sanctioned in-place edit", so the count and the list disagree; (ii) the sibling canonical statement, `persona-plan-orchestrator/standards/orchestration-model.md:114`, already gets this right — "The only in-place edit it may make is correcting its OWN filed message through `inbox amend` or `inbox supersede`" — so the two canonical documents now contradict each other on which verbs rewrite a file.
- **Why it matters:** The bullet is the canonical statement of how far the append-only invariant has been relaxed. Overstating the relaxation makes the invariant look weaker than it is, and it disagrees with the write-boundary contract that governs the same carve-out.
- **Fix:** Rewrite the bullet at `inbox-envelope.md:117` so the lead and the list agree and both match `orchestration-model.md:114`: the in-place mutations are `amend` (body, plus its `amended`/`revision` stamps) and `supersede` (envelope state); `close-stream` appends a new terminal marker like any other write and belongs outside that list.
- **Done when:** The Invariants bullet names exactly two in-place verbs, its bolded lead states the same count as its body, `close-stream` is classified as an append, and the bullet no longer contradicts `orchestration-model.md:114`.
- **Module/topic:** `plan-orchestrator` — standards/inbox-envelope.md

## G8 — Correct the module docstring's description of the archive write target

- **Kind:** doc-drift
- **Severity:** low
- **Where:** `marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/_orchestrator_inbox.py:30-35` — module docstring, the drain-surface paragraph
- **What is wrong:** Line 33 still says "the only path they ever write is ``inbox/archive/`` joined with either the source message's own bare filename or the bare, sender-constrained ``--as-name`` override". For every well-formed message the write target is `inbox/archive/{sender}/` joined with that name (`cmd_inbox_archive:1285-1296`). The preceding paragraph at `:25-28` states the foldering correctly, so the module docstring contradicts itself five lines apart. The report recorded two sibling docstring fixes (finding 1 and 2) but this third restatement was not swept.
  ⚠ One nuance the fix must preserve, confirmed by reading `cmd_inbox_archive:1276-1298`: a source name that does not match `_MESSAGE_NAME_RE` (no derivable sender — e.g. the literal `archive`) deliberately keeps a **flat** `archive/{dest_name}` destination so its `os.link` `OSError` still surfaces as `invalid_message_name`. So a flat target is not simply wrong everywhere; it is the off-shape error path only.
- **Why it matters:** The module docstring is the first thing a maintainer reads, and it is where the write-boundary-by-construction argument is made; a wrong path there weakens the argument it exists to carry.
- **Fix:** Rewrite the clause at `_orchestrator_inbox.py:33` to read `inbox/archive/{sender}/` joined with the bare source filename or the sender-constrained `--as-name` override, and add the one-clause carve-out for the off-shape source that keeps a flat destination as an error path. Keep the by-construction claim ("never a caller-supplied path") intact — it is true in both branches.
- **Done when:** The module docstring's drain-surface paragraph names `inbox/archive/{sender}/` as the write target, states the off-shape flat fallback explicitly, and no longer disagrees with the foldering statement at `:25-28`.
- **Module/topic:** `plan-orchestrator` — scripts/_orchestrator_inbox.py

## G9 — Make the empty-vs-finished discriminator account for invalid messages

- **Kind:** stale-statement
- **Severity:** low
- **Where:** `marketplace/bundles/plan-marshall/skills/plan-orchestrator/standards/inbox-envelope.md:21` and `SKILL.md:253`; computed at `_orchestrator_inbox.py:1140-1151`
- **What is wrong:** Both docs say `live_count: 0` with an empty `closed_senders` is "an EMPTY queue that may yet receive more". Re-executed independently during adversarial review, against `cmd_inbox_write` then a corrupted `kind` header (`kind=bogus`): `cmd_inbox_list` returned `{'count': 1, 'live_count': 0, 'closed_senders': [], 'invalid_count': 1}` with the row carrying `error: invalid_kind`. The cause is structural, at `_orchestrator_inbox.py:1140-1142`: `live_count` filters on `row['valid'] and row['lifecycle'] == LIFECYCLE_LIVE`, so an invalid row can never raise it. The queue is not empty — it holds a message the drain deliberately leaves un-archived (`analyze.md:78`) — yet the documented discriminator reads it as empty. A stuck invalid message is therefore indistinguishable from an empty queue for a consumer keying on `live_count` alone.
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

## G11 — Complete the `_add_inbox_group` docstring's sub-verb enumeration

- **Kind:** stale-statement
- **Severity:** low
- **Where:** `marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/orchestrator.py:2521-2524` — the `_add_inbox_group` docstring's "Sub-verbs:" line
- **What is wrong:** The docstring enumerates nine sub-verbs — `write`, `amend`, `supersede`, `close-stream`, `validate`, `list`, `archive`, `migrate-archive`, `detect` — while the function registers **ten**. `landing-check` (`orchestrator.py:2719`) is missing. Found by adversarial review while re-deriving the verb count for G5; the enumeration was correct as this plan left it and was made stale by the later `#1215` (`5a5446d3`, terminal machine-readable landing emission), which added the parser without touching the docstring above it. Recorded here rather than dropped because it is the same defect class G5 and G6 name, in the same function, and a single sweep should close all three.
- **Why it matters:** This is the in-code index of the verb group, sitting five lines above the argparse help string G6 already faults. Two stale enumerations and one stale help literal in one function is a surface no reader can trust.
- **Fix:** Add `landing-check` to the "Sub-verbs:" list in the `_add_inbox_group` docstring at `orchestrator.py:2521-2524`, in registration order (after `detect`).
- **Done when:** The docstring's sub-verb list and the `actions.add_parser` calls in the same function name the same ten verbs.
- **Module/topic:** `plan-orchestrator` — scripts/orchestrator.py argument surface (shared sweep with G6)

## G12 — Enforce the `stream-end` terminal marker, or stop stating it as a fact

- **Kind:** unenforced-invariant
- **Severity:** medium
- **Where:** `marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/_orchestrator_inbox.py` — `cmd_inbox_write:890-983` and `cmd_inbox_close_stream:1607-1664`; the asserted meaning lives at `standards/inbox-envelope.md:109` and `:113`, `SKILL.md:253`, and `_orchestrator_inbox.py:104-116`
- **What is wrong:** Every surface states the marker's meaning as a fact about the future — "A terminal control marker: the sender that filed it will send no more" (`inbox-envelope.md:109`), "`closed_senders` lists the senders that have filed a `stream-end` marker, which is what lets the drain tell an EMPTY queue … from a FINISHED one" (`SKILL.md:253`). **Nothing enforces it.** Executed against the live handlers on a `PLAN_BASE_DIR`-isolated store:

  ```text
  close-stream demo-plan        -> success demo-plan-001.md lifecycle=stream-end
    list: count 1, live_count 0, closed_senders ['demo-plan'], invalid_count 0
  write       demo-plan         -> success demo-plan-002.md          # NOT refused
    list: count 2, live_count 1, closed_senders ['demo-plan'], invalid_count 0
  close-stream demo-plan (again)-> success demo-plan-003.md          # NOT refused
    list: count 3, live_count 1, closed_senders ['demo-plan'], invalid_count 0
  ```

  So the listing simultaneously reports the sender as closed and carries a live message that sender filed *after* closing; and one sender can hold an unbounded number of `stream-end` markers, which `closed_senders`' `set` dedup hides entirely. `cmd_inbox_write` never inspects the queue for an existing marker, and `cmd_inbox_close_stream` never checks whether one already exists.
- **Why it matters:** This is precisely the archetype the epic is named for — a field that is not wrong about what it *says*, but whose name asserts something the machinery does not hold. `closed_senders` reads as a derived fact and is in truth an unenforced promise, so a consumer that stops watching a stream on it can miss everything filed afterwards. It is `medium` rather than `high` only because the sole consumer of `closed_senders` today is the test suite — `analyze.md` does not read it at all (G3), so nothing currently acts on the false signal. Closing G3 without closing this one would make it `high`.
- **Fix:** In `_orchestrator_inbox.py`, add one shared predicate — "does this sender already have a valid `lifecycle=stream-end` marker in `inbox/`?" — and consult it at both entry points: `cmd_inbox_write` refuses with a new `stream_closed` error code, and `cmd_inbox_close_stream` returns idempotent success naming the existing marker rather than allocating a second one. Add the code to the error table in `inbox-envelope.md` § Validator error codes' write-side sibling (§ Write-side deliverability, which already carries the `undeliverable_to_running_plan` precedent) and to `SKILL.md` § `inbox write` / § `inbox close-stream`. If enforcement is judged out of scope instead, the alternative fix is to downgrade the prose everywhere it appears — `inbox-envelope.md:109`, `:113`, `SKILL.md:253` — from "will send no more" to "declared its stream ended; not enforced", so the documents stop asserting a guarantee the code does not make. Do one or the other; leaving both as they are is the defect.
- **Done when:** Either (a) a `write` following a `close-stream` for the same sender is refused with a distinct documented error code and a second `close-stream` returns idempotent success, each pinned by a test; or (b) no document states the marker as a guarantee, and a test asserts the queue can hold a post-closure message so the weaker wording stays honest.
- **Module/topic:** `plan-orchestrator` — scripts/_orchestrator_inbox.py + standards/inbox-envelope.md + SKILL.md

## Considered and NOT raised as gaps

- **`revision_not_monotonic` names a co-presence check, not a monotonicity check** (`_orchestrator_inbox.py:509-511`). The validator sees one file's header and cannot observe a revision decreasing over time; true monotonicity is guaranteed only by `cmd_inbox_amend`'s `+1` at `:1500`. Both the code comment and `inbox-envelope.md:137` describe the actual condition accurately, so the surface is self-consistent and the name is the only imprecision — noted, not raised.
- **`_resolve_live_message` is named for a filter it does not apply.** Its docstring (`:1398-1411`) states plainly that it does not filter on `lifecycle` and that the guard is the caller's; this was the sub-agent's finding 3 and it was fixed correctly.
- **`_foldered_archive_dir` accepts the `NO_PLAN` sentinel** because `validate_plan_id` carves it out ahead of its regex. `NO_PLAN` is still a safe directory name (no separator, no traversal), so the guard's purpose holds; only the report's parenthetical describing the predicate as the bare regex is imprecise.

Added during adversarial review, after independent re-derivation:

- **The `NO_PLAN` sentinel is unreachable as a written sender but reachable as an archived one.** `_MESSAGE_NAME_RE` (`_orchestrator_inbox.py:177`) captures the sender as `.+?`, so a file literally named `NO_PLAN-001.md` in the archive yields sender `NO_PLAN`, which `_foldered_archive_dir` then accepts. Confirmed harmless for the same reason the entry above gives — `NO_PLAN` carries no separator and no traversal segment — so it stays a note, not a gap.
- **`orchestrator.py:2675`'s `archive` help string says "Retire one consumed message to inbox/archive/".** Read as naming the archive root rather than the leaf destination, this is not false the way `_orchestrator_inbox.py:33` is (G8), which explicitly joins the bare filename onto it. Not raised; if G8's sweep touches it anyway, that is a bonus, not a requirement.
- **D4's atomicity requirement is satisfied only vacuously.** The four archive-reading functions do land in the single squash commit `51d1c9bc`, so no intermediate checkout exists — but since the physical move never happened (G4), there was never a file relocation for the code change to be atomic *with*. The plan's constraint is met on its letter; whoever closes G4 inherits it in substance and must land the migration's per-sender record in one commit.

## Refuted during adversarial review

**None.** Every one of G1–G10 was re-checked against the tree by an agent that did not write them, and every one held. The re-checks that could have refuted a gap and did not:

- **G1** — could have been refuted if the four new codes were unreachable from `cmd_inbox_validate`. They are reachable: `validate_envelope:484-486` returns `_validate_state_fields`' code directly, and executing the handler against a `lifecycle=retired` message returned `error: invalid_lifecycle`.
- **G3** — could have been refuted if `analyze.md` handled the new state anywhere outside the cited line range. A whole-file sweep for `lifecycle|live_count|closed_senders|superseded|stream-end` returns one hit, line 52's unrelated "closed lifecycle". The gap was strengthened to `high` instead.
- **G4** — could have been refuted if a migration record existed anywhere in the tree. `.plan/` in this checkout holds `local/logs` and `local/marshall-state.toon` and no `local/orchestrator/` at all, so there is no archive to have migrated.
- **G5 / G6 / G11** — could have been refuted if the enumerations were complete. Re-derived from the `actions.add_parser` calls at `orchestrator.py:2546-2721`: ten verbs registered, six named in `inbox-envelope.md:151`, five described in the argparse help at `:2539-2540`, nine in the `_add_inbox_group` docstring at `:2523-2524`.
- **G7** — could have been refuted if `close-stream` rewrote an existing file. It calls `compose_envelope` then `allocate_message_path` (`:1645-1653`) and opens no existing message.
- **G9** — could have been refuted if `live_count` counted invalid rows. Re-executed: one corrupted message yields `count 1, live_count 0, closed_senders [], invalid_count 1`.
- **G10** — could have been refuted if the test file had changed since the merge, making 41/223 correct at the time of writing. `git log` on the file shows only `51d1c9bc`; the file collects 42 tests and the four inbox files collect 224, at the merge commit and today alike.
