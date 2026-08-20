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
| Narrowing `cleanup.md` Step 9's refusal reason breaks no other consumer (HYPOTHESIS) | `quiescence` sweep over both skills at `origin/main`: **five hits case-insensitively** (`cleanup.md` 107, 108, 111, 115, 170), four under a case-sensitive lowercase sweep — either way **all inside `cleanup.md` itself** | **CONFIRMED** (the verdict rests on the location of the hits, which both spellings agree on) |
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
(i) `cmd_compact`'s per-block `markers_absent` outcomes are passed into `_abstained_sections`, keyed to the owning heading via `GENERATED_BLOCK_OWNING_SECTION`; such a section emits `markers_absent_not_regenerated` and is counted by a new `unreachable_count`, leaving `abstained_count` counting deliberate abstentions only. **Four** report-contract statements updated — `_abstained_sections`' docstring, `cmd_compact`'s docstring, `plan-orchestrator/SKILL.md`, and `orchestration-model.md` § Ledger-Compaction Stage. The plan named three; the fourth was found by sweeping for the vocabulary rather than trusting the list. **Seen RED**: `3 failed, 2 passed, 31 deselected`, the two passes being the purely-narrative and reachable-ledger controls.
(ii) `cleanup.md`'s `## Output` block declares `compaction_regenerated[]`, `compaction_invariants[]` and `compaction_abstained[]`, each required-never-omitted the way `declined[]` is, and the Step 8 instruction names them. **Deviation from the plan, recorded:** the plan proposed `compaction_abstained[A]`, but `applied[A]` already occupies that letter in the same TOON block; `[B]` is used instead, since two independent counts sharing a letter is exactly the ambiguity the declaration exists to remove.
(iii) The tautology in `test_every_hand_authored_section_survives_verbatim` repaired by performing the second `_run()` the comment claimed and asserting byte-identity across THAT pass. **Seen RED with the first disjunct alone against the pre-fix tree: `1 failed, 31 passed`** — re-derived, and it happens to match the figure the gap recorded. The failure diff shows exactly why the disjunct mattered: `text` was read BEFORE the first `_run()`, so it carried the pre-regeneration resume body. The two comments describing operations the test never performed are corrected. **Mutation-tested**: with `_replace_block`'s `unchanged` branch mutated to append a drifting line, the repaired assertion goes RED (`1 failed, 31 deselected`); the file was restored from a byte snapshot, not with a git command, and the restore was verified.
(iv) The branch body shared by `_invariant_queue_spec` and `_corpus_signal` extracted into `_read_queue_spec_reconciliation`, returning a neutral `(state, evidence, population)` triple each caller maps into its own vocabulary. Both public shapes unchanged (the existing suites pass unedited). **Done-when re-derived:** `unreadable_count` / `rows_without_spec_count` / `specs_without_row_count` are now branched on in **exactly one** function — `_read_queue_spec_reconciliation`, named rather than line-cited, since a line number goes stale on the next edit; the three other occurrences are dict-literal *producers* in `cmd_corpus_enumerate`, `cmd_corpus_verdicts` and the sibling-collision reader, not branches.

**D5 — The drain acts on lifecycle** (`024bffb9`).
(i) `analyze.md` Step 3 item 2 now reads `lifecycle` before `kind`: a `superseded` row is recorded `retired_by_successor` and a `stream-end` row `stream_end_noted`, neither running its `kind` branch. Both archive, so both count inside `messages_archived` and the closure equation needs no fourth term — stated explicitly at the equation. The new rules defer to item 3 for an invalid row, because an unvalidated header's `lifecycle` is not a fact the drain may act on. Item numbering was deliberately **not** shifted: inserting a numbered item would have renumbered `4a`/`4b` into `5a`/`5b`, colliding with the existing "Step 5b" references.
Step 6 keys the empty-vs-finished conclusion on `live_count` + `closed_senders` + `invalid_count`.
(ii) `cleanup.md` Step 9 fact 2 rewritten. The refusal stands on a true reason: `closed_senders` is a per-sender closure over an **open** sender population — a plan not yet emitted, or emitted and not yet started, has filed nothing and so appears in neither `closed_senders` nor `live_count` — so a `closed_senders` covering every sender seen so far is consistent with a sender about to appear, which is what quiescence must rule out. The deferred-mechanism block is kept as the surface a successor reuses, and `archive_drain_reason` updated to match. "Drain per closed sender" is recorded below as an operator proposal.
(iii) One shared predicate `find_stream_end_marker` consulted at both entry points: `cmd_inbox_write` refuses with the new `stream_closed` code, `cmd_inbox_close_stream` returns idempotent success naming the existing marker with `already_closed`. Documented in `inbox-envelope.md` § Write-side deliverability beside the `undeliverable_to_running_plan` precedent, and in `SKILL.md` § `inbox write` / § `inbox close-stream`. **Seen RED: `4 failed, 2 passed, 43 deselected`**, the two passes being the open-sender and other-sender controls — confirming the gap's record of both calls succeeding pre-fix.
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

The site set was re-derived from the report rather than taken from the gap: the two the gap names are the `223` figures, and the sweep found **four** count-bearing statements — the two `223`s, the `41`/`549` pair on the same line, and the `16287` module-tests figure treated next.

⚠ **The fourth figure, `16287`, is NOT cleanly re-derivable, and was left standing with its population rather than replaced.** A re-run over the same commit's extracted tree with `uv run python -m pytest test/plan-marshall/ -o addopts="" -n auto` produced **16281 passed, 10 failed, 1 skipped** — 16292 collected against the report line's 16291. The two are **not the same population**: `./pw module-tests` applies the project's own pytest options (coverage, `--durations`) and this command clears them, which is enough to move the collected total. And the *passed* count is **order-dependent under xdist** by that report line's own account — the same flakiness that produced 3 non-passes there produced 10 here. Substituting 16281 would report a number derived from a different command as a correction to this one, which is the manufactured-precision defect this epic exists to close. What was corrected is the figure's **provenance**: both of its sites now name the command and the base (`51d1c9bc`) and say it is a sample of an order-dependent quantity rather than a stable one. Recorded as a **survivor** in § Findings.

**300 report — the stale-restatement figure.** The disposition table's own multiplicities were re-derived: **8 rows citing 13 distinct line locations across 5 files** (two rows carry `×2`, one carries `×4`). The report stated **11** at three sites, contradicted by its own evidence table. Every statement now equals 13, and the table's lead-in states the multiplicity the figure is derived from. This is a fourth site the gap did not name — the `**Disposition — all 11 fixed**` lead-in, corrected with the rest.

## Expected surface — confirm/refute

**HYPOTHESIS CONFIRMED.** `git diff --stat origin/main...HEAD` reaches every file the plan's Expected surface lists and no other. **Two** paths in the diff are not on the list, both lane machinery rather than deliverable surfaces: `doc/plans/truthful-signals/520-…/plan.md` (the Step 3 directory move) and `doc/plans/truthful-signals/520-…/report-01.md` (this report, which the lane requires and the plan's surface list does not enumerate). No fix reached a file beyond the list.

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

**Predicate, from git, not from recollection.** `git diff --name-only origin/main...HEAD -- '*.py'` returns **eight** files — three production (`manage-config.py`, `_orchestrator_inbox.py`, `orchestrator.py`) and five test — so the gate takes its **full** path. `git status --porcelain` was empty before the diff was taken, so no staged, unstaged or untracked file was invisible to it.

**`./pw verify` — CLEAN, read from the tool output rather than the exit code.** All three sub-steps reported clean, and each is confirmed separately because the exit code proves nothing:

| Sub-step | Evidence |
|---|---|
| quality-gate | `mypy … Success: no issues found in 416 source files`; `ruff … All checks passed!`; `>>> quality-gate: SPDX-header check passed`; `issues[0]` with plugin-doctor marketplace-wide |
| test-compile | `mypy … Success: no issues found in 783 source files` (the whole `test/` tree — the sub-step neither `quality-gate` nor `module-tests` performs) |
| module-tests | `21353 passed, 14 skipped in 466.00s (0:07:45)` — **0 failed, 0 errors** |

**A second `./pw quality-gate` was run on the CURRENT tree** after the cold-read fixes landed, because the `verify` above started before those markdown commits and plugin-doctor is the sub-step they could affect. Clean again: `416 source files`, `All checks passed!`, `SPDX-header check passed`, `issues[0]`.

**No lockfile churn.** `git diff --stat origin/main...HEAD -- uv.lock pyproject.toml` is empty, and every commit staged its deliverable paths explicitly — no `git add -A` was used.

**Stale base — § Step 8 condition 2.** Recorded at the merge gate below, with the `git rev-list --count HEAD..origin/main` figure, the shape used, the merge commit tested, and the gate's result on it.

## Findings

One finding per instance, never bundled.

### Round 1 — independent verification sub-agent

The verifier re-derived every red-first claim against pre-fix code in clean worktrees (D2 `1 failed, 2 passed, 232 deselected`; D3 `3 failed, 2 passed, 17 deselected`; D7(i) `1 failed, 53 deselected`; the narrative test `1 failed, 31 passed` — all exact matches), mutation-tested the repaired narrative guard, re-derived all four D1 populations and every D8 figure independently, opened every cross-reference target, and ran the D6(iv) resolve itself.

| # | Source | Finding | Disposition |
|---|---|---|---|
| 1 | verifier | `test_inbox_message_state.py` — comment said the header-only fixture is "rejected as `empty_payload`". Running it returns `missing_header_field`. The test asserted only counts, so nothing caught it. | **fixed** — comment corrected AND the code pinned by a new assertion, so it cannot drift again |
| 2 | verifier | `_orchestrator_inbox.py` `cmd_inbox_list` — the comment sitting **on the `live_count`/`closed_senders` computation** still stated the two-way reading D5(iv) retired. The most authoritative restatement of the rule, and unswept. Two weaker echoes in the test file's module docstring and an older test's comment. | **fixed at all three sites** — the production comment now carries the three-zero table |
| 3 | verifier | `orchestration-model.md` — new prose claimed `--default` "would also take the wrong tier". Verified false at the shipped config: both spellings resolve to `level-3` from `plan.effort`, because D2 just seeded `effort: {}`. An invented rationale, contradicted by this run's own recorded counterfactual. | **fixed** — rewritten to say the tier divergence is what an operator's configuration *makes* possible while the trail divergence is unconditional. **Verified by execution**: with `orchestrator.effort.analyze = level-6`, `--role` → `level-6` (`source: orchestrator.effort.analyze`) and `--default` → `level-3` (`source: plan.effort`) |
| 4 | verifier | Report said "All three report-contract statements updated" above a list of four. | **fixed** — four, and the plan named three |
| 5 | verifier | Report said "**one** path in the diff the list does not name"; there are two (the plan move and this report). | **fixed** |
| 6 | verifier | The three cold reads were performed and drove a real rewrite, but were **absent from the report** — a plan-mandated record. | **fixed** — § Three cold reads added |
| 7 | verifier | The `analyze.md` end-to-end read was performed but the report did not **state that this check was a read**, as § Verification requires. | **fixed** — § The `analyze.md` end-to-end read added |
| 8 | verifier | `emit-landing.md` gives a producer-side reader no hint that an `n/a` in the five sentinel-rejecting keys now makes a landing INCOMPLETE. | **fixed** — a one-sentence pointer added. Not a contract change: § Out of scope excludes changing what a producer must *emit*, and this changes nothing it must emit |
| 9 | verifier | Report's `quiescence` sweep said "four hits"; case-insensitively there are five. | **fixed** — both figures stated with the spelling each came from |
| 10 | verifier | Report said D5(iii) was seen RED with `42 deselected`; the reproduction gives `43`. | **fixed** |
| 11 | verifier | Report cited `orchestrator.py:1868–1875`; the actual branch lines differ. | **fixed** — the function is now named rather than line-cited, since a line number goes stale on the next edit |
| 12 | verifier | `SKILL.md` said the `inbox-envelope.md` table gives "each code's" rejection condition; that table is exhaustive over envelope-validation verdicts only and omits three. | **fixed** — scoped to codes 4–14 |
| 13 | verifier | The two `replaced_body` tests sat inside `TestMarkersAbsent`, under a banner that no longer described them. | **fixed** — moved to their own `TestReplacedBody` class |
| 14 | verifier | `_abstained_sections`' `unreachable_blocks` parameter defaulted to `()`, so omitting it silently restores the pre-fix behaviour — a latent regression vector for the exact defect D4 closes. | **fixed** — default removed; a caller with none passes an empty collection explicitly |
| 15 | verifier | Two PEP8 blank-line regressions, ungated (ruff's E301–E306 are preview-only). | **fixed** at both sites |
| 16 | verifier | A 132-char docstring line among ~80-char neighbours, ungated (E501 disabled). | **fixed** |
| 17 | verifier | `find_stream_end_marker` reads and validates every queued message per write — O(queue), documented nowhere. | **fixed** — a Cost paragraph added stating the bound, why it is accepted, and when to revisit |
| 18 | verifier | Report said "recorded as a survivor in § Findings" while § Findings was `_pending_`. | **fixed** — this section |

### Survivors — left open, each characterised

| # | Finding | Why it may be left open |
|---|---|---|
| S1 | The `16287` module-tests figure in the 250 report is not cleanly re-derivable. | **(b) bounded.** A re-run gives 16281/10-failed under a *different* command (16292 collected vs 16291), and the passed count is order-dependent under xdist by that line's own account. The bound: no figure in that report is now stated without its command and base, so a reader cannot mistake a sample for a stable count. Substituting 16281 would have manufactured precision. Condition A does not reach it — the figure is not false, it is a sample whose provenance was missing, and the provenance is now stated. |

### Rejected — none

No verifier finding was rejected. Findings 1–18 were all fixed; S1 is a survivor rather than a rejection.

### Deferred — none

No behavioural finding was left unfixed and deferred.

## Three cold reads (§ Verification)

The plan requires an independent reader who has **not** seen the plan for each of three passages whose whole value is what a later reader *does* with them, and requires this report to state **which reading they took**. Each reader was given only the passage, inline, and forbidden to open a file or search the repository.

| # | Passage | Intended reading | Reading taken | Verdict |
|---|---|---|---|---|
| 1 | `cleanup.md` § Step 9 after D5(ii) | **refused**, with a narrower stated reason | "**I refuse.** I do not drain or retire that sender's messages… `closed_senders` naming a sender establishes only that *that named sender* will send no more." Ran neither `bash` command. | ✅ intended |
| 2 | `cleanup.md` § Step 8 after D6(ii)–(iii) | marker insertion and annotation move performed **before** the script, and **only** when the marker pair is absent | ❌ **round 1 exposed two real defects** — see below. Rewritten, re-read, and round 2 took the intended reading on all three scenarios. | ✅ intended, after a rewrite |
| 3 | `landing-payload-spec.md` delta table + `analyze.md`'s `complete: true` bullet after D3(ii) | **the required-key subset** | "(b) — only the required-key subset drained… an operator paste could still surface a mechanisable fact the inbox never received." Would not tell the operator "nothing material is outstanding". | ✅ intended |

**Cold read 2 is why this check exists.** Round 1 found two defects no build gate could see:

1. **The numbered list ran opposite to the order it mandated.** Item 1 said "insert the marker pair"; item 2 said "move `Notes` … **before** inserting the markers". A reader executing top-to-bottom does the wrong thing. The reader reached the intended outcome only by overriding the numbering — *"I had to override the list numbering to do so. That is exactly the kind of thing a fast reader gets wrong."*
2. **A step's precondition was the negation of its own gate.** The block was gated on the markers being ABSENT, while step 3 described a ledger that "already has markers" — *"Read literally, step 3 can never fire."*

Fixed by splitting the migration into two explicitly mutually-exclusive rules, each with its own condition and Rule 1's steps in mandated order. **Round 2 on the rewritten passage took the intended reading on all three scenarios** and found a third defect: *"'neither is a per-run step' … was FALSE of Rule 2"* — Rule 1's precondition self-destructs, Rule 2's does not, so Rule 2 must be checked every pass. It also found that both rules moved content into a `### Queue annotations` zone the text presumed to exist, and that "the stage has two halves" now stood above three bolded blocks. All three corrected.

Cold read 3 took the intended reading but flagged one skim hazard — a sentence whose first half read as the claim its second half denied. Reordered so the front half states the narrow claim.

## The `analyze.md` end-to-end read (§ Verification)

**This check was a READ, not an execution**, and the plan requires that to be stated: `analyze.md` is LLM-executed markdown with no entry point, so its closure equation and its new dispositions are settled by reading it end to end. The read was performed after D5(i), over the whole file, and found **three** defects the diff-scoped view could not:

1. **Step 5b's scope sentence became ambiguous.** "each `kind: finding` message Step 5 did not absorb" could be read to include a `stream-end` marker, which carries `kind: finding` by design and which Step 5 never sees — so the marker could route into a disposition after all. Now explicitly excluded.
2. **Item 4's archival enumeration went stale.** "every consuming disposition `drained[]` enumerates (`reconciled`, `observed`, the four Step 5b outcomes)" omitted the two new lifecycle dispositions, which also archive. Now named, with the reason the closure equation needs no fourth term.
3. **Table-order inconsistency** between the Step 6 zero table and the same table in `inbox-envelope.md` / `SKILL.md`. Aligned to EMPTY / FINISHED / BLOCKED everywhere.

The closure equation was then re-checked by reading: `messages_archived + messages_invalid + messages_archive_failed == messages_scanned` holds with `retired_by_successor` and `stream_end_noted` both counted inside `messages_archived`.

## Proposals for the operator (recorded, not work done)

The plan makes two decisions itself so the run needs no mid-run judgement call, and requires the alternative in each case to be recorded here rather than taken. Both are recorded; neither was implemented.

1. **Promote `total_wall_seconds`, the per-step typed facts and the repository end-state to REQUIRED landing keys** (D3(ii)'s alternative). D3 keeps them optional and corrects the *claim* instead. Taking the alternative would change the producer contract in `phase-6-finalize/standards/emit-landing.md`, which this plan does not touch, and would make every landing written before the change retroactively incomplete. The operator's call, on a plan that owns the producer side.
2. **Drain per closed sender** (D5(ii)'s alternative). `inbox list` now reports `closed_senders`, so a drain *could* retire a closed sender's consumed messages without waiting for epic-wide quiescence. D5 keeps the refusal and narrows its reason instead. Whether a per-sender drain is the right successor mechanism — versus the epic-wide signal `cleanup.md`'s deferred-mechanism block still anticipates — is a design question this plan does not settle.

**One operator obligation, for a machine that holds the orchestrator store.** 250/G4 — running the physical `inbox/archive/` per-sender migration and reporting the per-sender counts — is excluded under § Out of scope because its population lives under the git-ignored `.plan/local/orchestrator/{epic}/inbox/archive/`, absent from this clone. `inbox migrate-archive` ships and is idempotent; the fold must be run where `.plan/local/` exists, and its per-sender counts read there.

**One pair a follower must land together.** 302/G5 (the dispatch/inline roster row) and 302/G7 (the `plan.phase-6-finalize.steps.default:emit-landing` registration in `.plan/marshal.json`) are coupled to each other and to neither half of this plan. Landing either without the other turns the roster closure test red in one direction or the other. This plan's D2 deliberately touches only the `orchestrator` block, so it leaves both untouched.

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
