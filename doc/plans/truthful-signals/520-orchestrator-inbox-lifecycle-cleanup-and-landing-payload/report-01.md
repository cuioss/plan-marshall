# Run report — 520-orchestrator-inbox-lifecycle-cleanup-and-landing-payload (run 01)

**Date (UTC):** 2026-08-20    **Branch:** `claude/orchestrator-inbox-lifecycle-cleanup-kxrzew`    **PR:** _pending_    **Outcome:** _pending_

> **Verification loop exit:** _pending_

## Skills loaded

Every skill was loaded by **bundle path** (`Read: marketplace/bundles/{bundle}/skills/{skill}/SKILL.md`) — the route that works in a fresh cloud clone. None was unobtainable.

| Skill | Why |
|---|---|
| `plan-marshall:ref-code-quality` | always |
| `pm-plugin-development:plugin-script-architecture` | always |
| `pm-dev-python:python-core` | Python production code (`orchestrator.py`, `_orchestrator_inbox.py`, `manage-config.py`) |
| `pm-dev-python:pytest-testing` | Python tests (four suites touched) |
| `pm-plugin-development:plugin-architecture` | `SKILL.md` / bundle structure (`plugin.json`, three `SKILL.md` surfaces) |

`plan-marshall:ref-workflow-architecture` was **not** loaded: the workflow-doc edits here are content corrections inside existing `analyze.md` / `cleanup.md` steps, adding no dispatch topology and no new skill composition. `persona-implementer`, `persona-security-expert` and `pm-documents:ref-asciidoc` were not loaded — no `.adoc` was touched and the change is not security-relevant.

## D1 — Derivation gate (the four populations, derived before any edit)

All of (a)–(c) derived successfully from code, so the plan did **not** halt. (d) returned a tracked path, so D2's configuration half shipped.

**(a) The `inbox` sub-verb set** — from the `actions.add_parser(...)` calls inside `_add_inbox_group`, `marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/orchestrator.py`. **Ten verbs, in registration order:**

`write`, `amend`, `supersede`, `close-stream`, `validate`, `list`, `archive`, `migrate-archive`, `detect`, `landing-check`

**(b) The rejection codes reachable from `cmd_inbox_validate`** — by reading `cmd_inbox_validate`, `validate_envelope` and `_validate_state_fields` in `_orchestrator_inbox.py`. **Fourteen, in check order:**

`invalid_slug`, `invalid_message_name`, `file_not_found` (the verb's own, before and at resolution); `missing_header_field`, `unknown_envelope_version`, `invalid_sender_type`, `invalid_kind`, `empty_payload`, `epic_mismatch`, `filename_sender_mismatch` (`validate_envelope`'s base sweep); `invalid_lifecycle`, `invalid_revision`, `revision_not_monotonic`, `invalid_supersede_state` (`_validate_state_fields`).

A fifteenth literal, `invalid_envelope`, exists as `cmd_inbox_validate`'s defensive fallback for a rejection reporting no code. It is **unreachable** while `validate_envelope` returns a literal on every rejection branch — read and confirmed, not assumed — and is documented as the defensive default rather than counted in the set.

**(c) The orchestrator config key set** — `ORCHESTRATOR_KNOWN_KEYS`, `marketplace/bundles/plan-marshall/skills/manage-config/scripts/_config_defaults.py:277`. **Three keys:** `auto_emit`, `effort`, `parallelization_scope`.

**(d) `.plan/marshal.json` tracked in this clone** — `git ls-files .plan/marshal.json` returned `.plan/marshal.json`. **Tracked.**

## Claim labels — every asserted absence re-verified at HEAD

The plan carries three asserted-absence claims and flags them as the higher-risk half. Each was re-run before the edit that depends on it.

| Claim | Re-derived result | Verdict |
|---|---|---|
| 090/G1 — the tracked `orchestrator` block carries only `auto_emit` while `ORCHESTRATOR_KNOWN_KEYS` names three | `.plan/marshal.json` → `{"auto_emit": false}`; constant → three keys | **reproduces** |
| 302/G1 — the completeness check rejects only empty values | `missing = [key for key in LANDING_REQUIRED_KEYS if not facts.get(key)]` | **reproduces** |
| 180/G6 — every abstained section is emitted `preserved_verbatim`, unconditionally | `_abstained_sections` appended a fixed `'treatment': 'preserved_verbatim'` | **reproduces** |
| 250/G3 — `analyze.md` reads none of `lifecycle` / `live_count` / `closed_senders` / `superseded` / `stream-end` | whole-file sweep: **one** hit, the unrelated prose "closed lifecycle" at line 52 | **reproduces** (absence confirmed) |
| 250/G12 — no `stream_closed` enforcement at either entry point | sweep of `_orchestrator_inbox.py` for `stream_closed`: **zero hits**; `cmd_inbox_write` and `cmd_inbox_close_stream` read in full | **reproduces** (absence confirmed) |
| 280/G7 — the orchestrator lane emits no dispatch record on either surface | `DISPATCH` sweep over `persona-plan-orchestrator/` and `plan-orchestrator/`: **zero hits** | **reproduces** (absence confirmed) |
| Narrowing `cleanup.md` Step 9's refusal reason breaks no other consumer (HYPOTHESIS) | `quiescence` sweep over both skills: **four hits, all inside `cleanup.md` itself** | **CONFIRMED** |
| The Expected surface is complete (HYPOTHESIS) | `git diff --stat origin/main...HEAD` — see § Expected surface below | **CONFIRMED** |

## Deliverables

All eight shipped. One commit per deliverable, in the plan's stated order so the later edit sees the earlier one.

**D1 — Derivation gate** (`94984c81` established the plan directory; D1 itself mutates nothing). All four populations derived and recorded verbatim above with their file and symbol. No premise failed, so the plan did not halt.

**D2 — The orchestrator block is discoverable where operators read it** (`04c81b31`).
(i) `.plan/marshal.json`'s `orchestrator` block seeded with `effort: {}` and `parallelization_scope: 1`, preserving `auto_emit: false` and the file's top-level key order. `sync-defaults` was **not** run, per the plan's ⛔.
(ii) `test_committed_marshal_json_surfaces_every_orchestrator_knob` added, deriving its expectation from `ORCHESTRATOR_KNOWN_KEYS` rather than transcribing it. **Seen RED** against the pre-edit block: `AssertionError: committed orchestrator block surfaces ['auto_emit'], expected every settable knob ['auto_emit', 'effort', 'parallelization_scope']` — `1 failed, 2 passed, 232 deselected`. The two existing committed-file tests were re-run and still pass (they assert top-level key order only and read inside no block).
(iii) `marshal-json-reference.md` § Orchestrator Configuration now states that `init` seeds every knob at its effective default, that each seeded default resolves exactly as the unset key did (with the fall-through per knob), and that a legacy `auto_emit`-only block stays valid and is back-filled by `sync-defaults`. The table row's parenthetical reflects the seeded shape; the `parallelization_scope` paragraph makes the seeded `1` the stated default with the unset case as a legacy note. `auto_emit` gained a real reference section and table row.

*Both sweeps clean.* **PLAN-48 sweep** over `marketplace/`: 4 hits before (`manage-config.py:596`, `effort-roles.md:88`, `marshal-json-reference.md:123` and `:155` — the four the gap names, re-derived and confirmed), **0 after**. **Empty-block sweep** for `empty \`{}\` block is legal` / `empty \`{}\` legal` / `when unset the ask keeps`: 3 hits before (all in `marshal-json-reference.md`), **0 after**. The remaining `empty {}` hits in the tree describe the `effort` sub-block and the config-less finalize steps — both still true, so untouched.

**D3 — A degraded landing fact is missing** (`24e1d24a`).
(i) `LANDING_DEGRADED_SENTINELS` and `LANDING_SENTINEL_REJECTING_KEYS` added; `_is_unsupplied` treats a sentinel as missing for `plan_id`, `deliverables_total`, `deliverables_done`, `total_tokens`, `steps`. `pr` and `merge_state` stay allowed to be `n/a`, and the docstring states that asymmetry. `schema` has no entry — the preceding schema branch already fail-closes.
(ii) `landing-payload-spec.md`'s delta table corrected: `steps` carries per-step outcomes only; the typed facts, the wall-clock and the repository end-state ride optional keys. A note states that MECHANISABLE does not mean required. `analyze.md`'s `complete: true` bullet — **and the two further sentences restating the same overclaim**, at the `complete: false` paragraph's tail and in the `landings_incomplete` field contract — now claim only what the required set covers. The alternative (promoting those rows to required) is recorded below as an operator proposal, not work done.
(iii) The `LANDING_REQUIRED_KEYS` comment rewritten: the constant is the executable authority, and `landing-payload-spec.md` § "Required machine-readable fact keys" and `emit-landing.md` Step 2 restate it for their readers. It defers the prose tie-break to the spec's own sentence rather than restating or overriding it.

*Red-first:* the three rejection cases **seen RED** — `3 failed, 2 passed, 17 deselected` — while the two must-stay-complete cases (`pr`/`merge_state` degraded; a genuine `0` count) were green before and after, which is what shows the rule was not widened into a blanket ban.

**D4 — could-not is distinguishable from chose-not** (`b8f2286e`).
(i) `cmd_compact`'s per-block `markers_absent` outcomes are passed into `_abstained_sections`, keyed to the owning heading via `GENERATED_BLOCK_OWNING_SECTION`; such a section emits `markers_absent_not_regenerated` and is counted by a new `unreachable_count`, leaving `abstained_count` counting deliberate abstentions only. All three report-contract statements updated — the function docstring, `cmd_compact`'s docstring, `plan-orchestrator/SKILL.md`, and `orchestration-model.md` § Ledger-Compaction Stage. **Seen RED**: `3 failed, 2 passed, 31 deselected`, the two passes being the purely-narrative and reachable-ledger controls.
(ii) `cleanup.md`'s `## Output` block declares `compaction_regenerated[]`, `compaction_invariants[]` and `compaction_abstained[]`, each required-never-omitted the way `declined[]` is, and the Step 8 instruction names them. **Deviation from the plan, recorded:** the plan proposed `compaction_abstained[A]`, but `applied[A]` already occupies that letter in the same TOON block; `[B]` is used instead, since two independent counts sharing a letter is exactly the ambiguity the declaration exists to remove.
(iii) The tautology in `test_every_hand_authored_section_survives_verbatim` repaired by performing the second `_run()` the comment claimed and asserting byte-identity across THAT pass. **Seen RED with the first disjunct alone against the pre-fix tree: `1 failed, 31 passed`** — re-derived, and it happens to match the figure the gap recorded. The failure diff shows exactly why the disjunct mattered: `text` was read BEFORE the first `_run()`, so it carried the pre-regeneration resume body. The two comments describing operations the test never performed are corrected. **Mutation-tested**: with `_replace_block`'s `unchanged` branch mutated to append a drifting line, the repaired assertion goes RED (`1 failed, 31 deselected`); the file was restored from a byte snapshot, not with a git command, and the restore was verified.
(iv) The branch body shared by `_invariant_queue_spec` and `_corpus_signal` extracted into `_read_queue_spec_reconciliation`, returning a neutral `(state, evidence, population)` triple each caller maps into its own vocabulary. Both public shapes unchanged (the existing suites pass unedited). **Done-when re-derived:** `unreadable_count` / `rows_without_spec_count` / `specs_without_row_count` are now branched on in **exactly one** function (`orchestrator.py:1868–1875`); the three other occurrences are dict-literal *producers* in `cmd_corpus_enumerate`, `cmd_corpus_verdicts` and the sibling-collision reader, not branches.

**D5 — The drain acts on lifecycle** (`024bffb9`).
(i) `analyze.md` Step 3 item 2 now reads `lifecycle` before `kind`: a `superseded` row is recorded `retired_by_successor` and a `stream-end` row `stream_end_noted`, neither running its `kind` branch. Both archive, so both count inside `messages_archived` and the closure equation needs no fourth term — stated explicitly at the equation. The new rules defer to item 3 for an invalid row, because an unvalidated header's `lifecycle` is not a fact the drain may act on. Item numbering was deliberately **not** shifted: inserting a numbered item would have renumbered `4a`/`4b` into `5a`/`5b`, colliding with the existing "Step 5b" references.
Step 6 keys the empty-vs-finished conclusion on `live_count` + `closed_senders` + `invalid_count`.
(ii) `cleanup.md` Step 9 fact 2 rewritten. The refusal stands on a true reason: `closed_senders` is a per-sender closure over an **open** sender population — a plan not yet emitted, or emitted and not yet started, has filed nothing and so appears in neither `closed_senders` nor `live_count` — so a `closed_senders` covering every sender seen so far is consistent with a sender about to appear, which is what quiescence must rule out. The deferred-mechanism block is kept as the surface a successor reuses, and `archive_drain_reason` updated to match. "Drain per closed sender" is recorded below as an operator proposal.
(iii) One shared predicate `find_stream_end_marker` consulted at both entry points: `cmd_inbox_write` refuses with the new `stream_closed` code, `cmd_inbox_close_stream` returns idempotent success naming the existing marker with `already_closed`. Documented in `inbox-envelope.md` § Write-side deliverability beside the `undeliverable_to_running_plan` precedent, and in `SKILL.md` § `inbox write` / § `inbox close-stream`. **Seen RED: `4 failed, 2 passed, 42 deselected`**, the two passes being the open-sender and other-sender controls — confirming the gap's record of both calls succeeding pre-fix.
(iv) `inbox-envelope.md` § Drain semantics and `SKILL.md` § `inbox list` now tabulate **three** zeros, naming BLOCKED (`live_count: 0` with `invalid_count > 0`) explicitly. A test pins the blocked zero as distinct from the empty one *on the two fields the old two-way reading looked at*, so the two states are asserted against each other rather than each in isolation.

**D6 — the epic tree, the migration, and the dispatch label** (`c94b87a9`).
(i) `settled.md` declared in the Directory Layout block between `history.md` and `references.json`, commented as mid-life relocated settled narrative with pointers resolving there, and added to the § Carve-outs ledger-document list.
(ii)/(iii) `cleanup.md` § Step 8 carries a one-time marker migration **before** the script call, conditioned on a `## Ordered Queue` present with no `BEGIN GENERATED: ordered-queue` marker: insert the pair around the existing table, move per-row `Notes` and any hand-written between-marker line into the annotation zone, fabricate no rows. § Ledger-Compaction Stage states the same obligation next to the never-fabricate rule so the refusal and its remedy read together. `replaced_body` added to `_replace_block`'s return and `cmd_compact`'s `regenerated[]` rows, carrying the pre-write between-marker text for a `regenerated` block and `''` otherwise; **both tests seen RED** (`2 failed, 36 deselected`).
(iv) The canonical-form resolve now carries `--role orchestrator.{surface}`, `--plan-id none`, `--caller` and `--workflow`, with one sentence stating that the resolve seam emits the `[DISPATCH]` line and its paired decision-log record per firing.

**The emitted label was verified, not trusted.** Running the canonical resolve produced, in `.plan/local/logs/work-2026-08-20.log`:

```text
[DISPATCH] (plan-marshall:persona-plan-orchestrator) target=execution-context-level-3 level=level-3 role=orchestrator.analyze workflow=plan-marshall:plan-orchestrator:workflow/analyze.md plan_id=none
```

with the paired decision-log record `(plan-marshall:manage-config) effort resolve-target role=orchestrator.analyze -> target=execution-context-level-3 level=level-3`. The `--default` counterfactual was run on the same site and produced `role=default` on an otherwise identical line — which is precisely why `--default` is not distinguishable between the `analyze` and `decompose` surfaces, and why the explicit `--role` is mandated.

**D7 — every `inbox` enumeration names the registered set** (`c7e0e1c9`).
(i) `SKILL.md` § `inbox validate` enumerated **seven** of the fourteen D1(b) codes. It now tables all fourteen in check order with the raising seam, and the "checked in that order" clause is made exact (state checks run after the base sweep). The unreachable `invalid_envelope` fallback is named as the defensive default rather than as a fifteenth outcome. The pinned tuple in `test_inbox_validate_still_lists_every_retained_rejection_code` extended to the full set; **the guard was verified to bite** by deleting `revision_not_monotonic` from the section and seeing `1 failed, 53 deselected` (file restored from a byte snapshot, verified).
(ii) `inbox-envelope.md` § Related extended to the full ten-verb surface. **Every added name was confirmed to have a `### inbox {verb}` target in `SKILL.md` before being written** — all ten resolve.
(iii) The `inbox` subparser's `help=` literal replaced.
(iv) `_add_inbox_group`'s "Sub-verbs:" line made the full ten-verb set in registration order.
(v) `inbox-envelope.md` § Invariants: the bullet's lead said "one sanctioned in-place edit" while its body named three, and it classified `close-stream` as an in-place mutation. Lead and list now agree on **two** (`amend`, `supersede`), `close-stream` is classified as an append — `cmd_inbox_close_stream` composes a fresh envelope and allocates a new path, opening no existing file — and the bullet now cites rather than contradicts `orchestration-model.md` § Ledger Write-Boundary, whose sibling statement already named only those two.
(vi) `_orchestrator_inbox.py`'s drain-surface paragraph rewritten to `inbox/archive/{sender}/`, preserving the flat-destination carve-out for an off-shape source name so its link error still surfaces as `invalid_message_name`. The never-a-caller-supplied-path claim is kept — **checked in both branches** by reading `cmd_inbox_archive`'s destination computation, where the destination is composed from validated parts either way.

⚠ **A plan premise was refuted here and the deviation is recorded rather than followed.** D7(iii) instructs the run to "mirror the already-correct module docstring". Re-derivation showed that docstring was **itself one verb short** — both its brace list and its prose omitted `landing-check`. Mirroring it would have propagated the defect. It was corrected instead, making this a **fourth** `orchestrator.py` site D7 touched rather than the three the plan enumerated.

**D8 — records and registration cosmetics** (`d9c8b7e9`).
(i) `plugin.json`: `persona-plan-orchestrator` moved after `persona-plan-marshall-agent`, `plan-orchestrator` after `plan-marshall-plugin`, leaving `marshall-steward` directly after `manage-terminal-title`. **Out-of-order adjacent pairs re-derived before and after: 6 → 4**, and the four survivors are exactly the pre-existing inversions § Out of scope leaves alone (`ref-code-quality > persona-auditor`, `persona-security-expert > execute-task`, `manage-ci-artifacts > manage-change-ledger`, `platform-runtime > plan-doctor`). The diff is 2 insertions / 2 deletions — only the two named entries moved.
(ii)–(iv) recorded in § Report-figure re-derivations below.

## Report-figure re-derivations (D8 ii–iv)

Each figure is stated with the base or population it was derived at.

**120 report — the token census.** `68a21cac` was unreachable in this shallow clone; a single `git fetch --unshallow` made it reachable, and it is confirmed as the first parent of the rename commit `6939a0c2`. Its tree was extracted to a scratch checkout and swept with the same tool:

- **Re-derived at `68a21cac`: 264 matching lines across 73 files**, of which **0 lines across 0 files** were under `.plan/`.
- ⛔ **The original figure (265 / 74) does not reproduce there and is not recoverable.** It was derived from a working tree that no longer exists and for which the run recorded no commit. The +1 line / +1 file delta is recorded **as a delta with no cause assigned** — attributing it would manufacture the provenance this correction exists to remove. The figure was **not** re-attributed to `68a21cac`.
- The **union-count bullet** carried the same unreproducible 74 and was corrected with it — a second site the gap did not name.
- **Population bullet corrected.** It claimed ripgrep's `.gitignore` handling excluded `.plan/` as a whole. It does not: `.gitignore` ignores `.plan/*` and re-includes `!.plan/marshal.json` and `project-architecture/`, so **13 tracked files** at that base were *inside* the swept population. They returned zero hits, which is why their inclusion was invisible in the result.
- **D6 rationale corrected** to name the git-ignored part precisely (`.plan/local/**`, the generated executor) and to state that the two tracked paths were searched and returned nothing — an empty result, not an exclusion.

**250 report.** The duplicated tail of four unfilled `_pending_` sections (`## Cost`, `## Contract check (Step 9)`, `## What have we learned (Step 9)`, `## Residue`, each already filled earlier in the file) was deleted — 16 lines, verified before deletion to contain only those four headings and `_pending_` bodies. Every `## ` heading now appears exactly once.

Test counts re-derived at **this plan's own landed commit `51d1c9bc`** (the state the report describes — its tree extracted and re-run with `uv run python -m pytest -o addopts=""`). All three were one low:

| Figure | Report said | Re-derived at `51d1c9bc` |
|---|---|---|
| the new file (`test_inbox_message_state.py`) | 41 | **42 passed** |
| the four inbox test files | 223 | **224 passed** |
| `test/plan-marshall/plan-orchestrator/` | 549 | **550 passed** |

The site set was re-derived from the report rather than taken from the gap: the two the gap names are the `223` figures, and the sweep found **four** count-bearing statements — the two `223`s, the `41`/`549` pair on the same line, and the `16287` module-tests figure treated below.

**300 report — the stale-restatement figure.** The disposition table's own multiplicities were re-derived: **8 rows citing 13 distinct line locations across 5 files** (two rows carry `×2`, one carries `×4`). The report stated **11** at three sites, contradicted by its own evidence table. Every statement now equals 13, and the table's lead-in states the multiplicity the figure is derived from. This is a fourth site the gap did not name — the `**Disposition — all 11 fixed**` lead-in, corrected with the rest.

## Expected surface — confirm/refute

**HYPOTHESIS CONFIRMED.** `git diff --stat origin/main...HEAD` reaches every file the plan's Expected surface lists and no other. The one path in the diff that the list does not name is `doc/plans/truthful-signals/520-…/plan.md` — the lane's own Step 3 directory move, which is lane machinery rather than a deliverable surface. No fix reached a file beyond the list.

## Coverage check by id

The id set was re-derived from the seven source `gaps.md` files rather than from this plan's grouping. Those files carry **51** gap ids in total; this plan cites **35**, of which **31 are its own accountability** — matching the plan's stated figure — and the other four are next-door references.

| Deliverable | Gap ids closed |
|---|---|
| D2 | 090/G1, 090/G2, 090/G3 |
| D3 | 302/G1, 302/G2, 302/G9 |
| D4 | 180/G6, 180/G4, 180/G1, 180/G8 |
| D5 | 250/G3, 250/G2, 250/G12, 250/G9 |
| D6 | 180/G3, 180/G7, 180/G2, 280/G7 |
| D7 | 250/G1, 250/G5, 250/G6, 250/G11, 250/G7, 250/G8 |
| D8 | 120/G1, 120/G2, 120/G3, 120/G4, 250/G10, 300/G5 |
| **Excluded** — § Out of scope | 250/G4 (the physical archive migration; population is under the git-ignored `.plan/local/`, absent from this clone) |

30 closed + 1 excluded = **31**. The four further cited ids — 302/G3, 302/G4, 302/G5, 302/G7 — are named by the plan as work belonging to other plans, not as gaps assigned here.

## Build gate

_pending_

## Findings

_pending_

## Reviewer participation

_pending_

## Cost

_pending_

## Contract check (Step 9)

_pending_

## What have we learned (Step 9)

_pending_

## Residue

_pending_
