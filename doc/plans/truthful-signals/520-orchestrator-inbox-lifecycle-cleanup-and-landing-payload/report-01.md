# Run report — 520-orchestrator-inbox-lifecycle-cleanup-and-landing-payload (run 01)

**Date (UTC):** 2026-08-20    **Branch:** `claude/orchestrator-inbox-lifecycle-cleanup-kxrzew`    **PR:** [#1317](https://github.com/cuioss/plan-marshall/pull/1317)    **Outcome:** completed

> **Verification loop exit:** `verifier-clear`

## Skills loaded

Every skill was loaded by **bundle path** (`Read: marketplace/bundles/{bundle}/skills/{skill}/SKILL.md`) — the route that works in a fresh cloud clone. None was unobtainable.

| Skill | Why |
|---|---|
| `plan-marshall:ref-code-quality` | always |
| `pm-plugin-development:plugin-script-architecture` | always |
| `pm-dev-python:python-core` | Python production code (`orchestrator.py`, `_orchestrator_inbox.py`, `manage-config.py`) |
| `pm-dev-python:pytest-testing` | Python tests (five test modules touched) |
| `pm-plugin-development:plugin-architecture` | `SKILL.md` / bundle structure — `plugin.json`, one `SKILL.md` (`plan-orchestrator`), and standards/workflow docs across five skills (a sixth, `manage-config`, contributes only a script) |

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
| The Expected surface is complete (HYPOTHESIS) | `git diff --name-only origin/main...HEAD` — see § Expected surface below | **REFUTED by one file** — `emit-landing.md`, reached by a round-1 verification fix; the plan's own hedge ("a fix may reach one file further") is what came true |

## Deliverables

All eight shipped. One commit per deliverable, in the plan's stated order so the later edit sees the earlier one.

**D1 — Derivation gate** (`58359f9b` established the plan directory; D1 itself mutates nothing). All four populations derived and recorded verbatim above with their file and symbol. No premise failed, so the plan did not halt.

**D2 — The orchestrator block is discoverable where operators read it** (`5078593e`).
(i) `.plan/marshal.json`'s `orchestrator` block seeded with `effort: {}` and `parallelization_scope: 1`, preserving `auto_emit: false` and the file's top-level key order. `sync-defaults` was **not** run, per the plan's ⛔.
(ii) `test_committed_marshal_json_surfaces_every_orchestrator_knob` added, deriving its expectation from `ORCHESTRATOR_KNOWN_KEYS` rather than transcribing it. **Seen RED** against the pre-edit block: `AssertionError: committed orchestrator block surfaces ['auto_emit'], expected every settable knob ['auto_emit', 'effort', 'parallelization_scope']` — `1 failed, 2 passed, 232 deselected`. The two existing committed-file tests were re-run and still pass (they assert top-level key order only and read inside no block).
(iii) `marshal-json-reference.md` § Orchestrator Configuration now states that `init` seeds every knob at its effective default, that each seeded default resolves exactly as the unset key did (with the fall-through per knob), and that a legacy `auto_emit`-only block stays valid and is back-filled by `sync-defaults`. The table row's parenthetical reflects the seeded shape; the `parallelization_scope` paragraph makes the seeded `1` the stated default with the unset case as a legacy note. `auto_emit` gained a real reference section and table row.

*Both sweeps clean.* **PLAN-48 sweep** over `marketplace/`: 4 hits before (`manage-config.py:596`, `effort-roles.md:88`, `marshal-json-reference.md:123` and `:155` — the four the gap names, re-derived and confirmed), **0 after**. **Empty-block sweep** for `empty \`{}\` block is legal` / `empty \`{}\` legal` / `when unset the ask keeps`: 3 hits before (all in `marshal-json-reference.md`), **0 after**. The remaining `empty {}` hits in the tree describe the `effort` sub-block and the config-less finalize steps — both still true, so untouched.

**D3 — A degraded landing fact is missing** (`28e1cbff`).
(i) `LANDING_DEGRADED_SENTINELS` and `LANDING_SENTINEL_REJECTING_KEYS` added; `_is_unsupplied` treats a sentinel as missing for `plan_id`, `deliverables_total`, `deliverables_done`, `total_tokens`, `steps`. `pr` and `merge_state` stay allowed to be `n/a`, and the docstring states that asymmetry. `schema` has no entry — the preceding schema branch already fail-closes.
(ii) `landing-payload-spec.md`'s delta table corrected: `steps` carries per-step outcomes only; the typed facts, the wall-clock and the repository end-state ride optional keys. A note states that MECHANISABLE does not mean required. `analyze.md`'s `complete: true` bullet — **and the two further sentences restating the same overclaim**, at the `complete: false` paragraph's tail and in the `landings_incomplete` field contract — now claim only what the required set covers. The alternative (promoting those rows to required) is recorded below as an operator proposal, not work done.
(iii) The `LANDING_REQUIRED_KEYS` comment rewritten: the constant is the executable authority, and `landing-payload-spec.md` § "Required machine-readable fact keys" and `emit-landing.md` Step 2 restate it for their readers. It defers the prose tie-break to the spec's own sentence rather than restating or overriding it.

*Red-first:* the three rejection cases **seen RED** — `3 failed, 2 passed, 17 deselected` — while the two must-stay-complete cases (`pr`/`merge_state` degraded; a genuine `0` count) were green before and after, which is what shows the rule was not widened into a blanket ban.

**D4 — could-not is distinguishable from chose-not** (`2d7accb9`).
(i) `cmd_compact`'s per-block `markers_absent` outcomes are passed into `_abstained_sections`, keyed to the owning heading via `GENERATED_BLOCK_OWNING_SECTION`; such a section emits `markers_absent_not_regenerated` and is counted by a new `unreachable_count`, leaving `abstained_count` counting deliberate abstentions only. **Four** report-contract statements updated — `_abstained_sections`' docstring, `cmd_compact`'s docstring, `plan-orchestrator/SKILL.md`, and `orchestration-model.md` § Ledger-Compaction Stage. The plan named three; the fourth was found by sweeping for the vocabulary rather than trusting the list. **Seen RED**: `3 failed, 2 passed, 31 deselected`, the two passes being the purely-narrative and reachable-ledger controls.
(ii) `cleanup.md`'s `## Output` block declares `compaction_regenerated[]`, `compaction_invariants[]` and `compaction_abstained[]`, each required-never-omitted the way `declined[]` is, and the Step 8 instruction names them. **Deviation from the plan, recorded:** the plan proposed `compaction_abstained[A]`, but `applied[A]` already occupies that letter in the same TOON block; `[B]` is used instead, since two independent counts sharing a letter is exactly the ambiguity the declaration exists to remove.
(iii) The tautology in `test_every_hand_authored_section_survives_verbatim` repaired by performing the second `_run()` the comment claimed and asserting byte-identity across THAT pass. **Seen RED with the first disjunct alone against the pre-fix tree: `1 failed, 31 passed`** — re-derived, and it happens to match the figure the gap recorded. The failure diff shows exactly why the disjunct mattered: `text` was read BEFORE the first `_run()`, so it carried the pre-regeneration resume body. The two comments describing operations the test never performed are corrected. **Mutation-tested**: with `_replace_block`'s `unchanged` branch mutated to append a drifting line, the repaired assertion goes RED (`1 failed, 31 deselected`); the file was restored from a byte snapshot, not with a git command, and the restore was verified.
(iv) The branch body shared by `_invariant_queue_spec` and `_corpus_signal` extracted into `_read_queue_spec_reconciliation`, returning a neutral `(state, evidence, population)` triple each caller maps into its own vocabulary. Both public shapes unchanged (the existing suites pass unedited). **Done-when re-derived:** `unreadable_count` / `rows_without_spec_count` / `specs_without_row_count` are now branched on in **exactly one** function — `_read_queue_spec_reconciliation`, named rather than line-cited, since a line number goes stale on the next edit; every other occurrence — five sites across three functions (`cmd_corpus_enumerate`, `cmd_corpus_verdicts`, `cmd_corpus_cross_check`) — is a dict-literal *producer*, not a branch.

**D5 — The drain acts on lifecycle** (`3ab7623f`).
(i) `analyze.md` Step 3 item 2 now reads `lifecycle` before `kind`: a `superseded` row is recorded `retired_by_successor` and a `stream-end` row `stream_end_noted`, neither running its `kind` branch. Both archive, so both count inside `messages_archived` and the closure equation needs no fourth term — stated explicitly at the equation. The new rules defer to item 3 for an invalid row, because an unvalidated header's `lifecycle` is not a fact the drain may act on. Item numbering was deliberately **not** shifted: inserting a numbered item would have renumbered `4a`/`4b` into `5a`/`5b`, colliding with the existing "Step 5b" references.
Step 6 keys the empty-vs-finished conclusion on `live_count` + `closed_senders` + `invalid_count`.
(ii) `cleanup.md` Step 9 fact 2 rewritten. The refusal stands on a true reason: `closed_senders` is a per-sender closure over an **open** sender population — a plan not yet emitted, or emitted and not yet started, has filed nothing and so appears in neither `closed_senders` nor `live_count` — so a `closed_senders` covering every sender seen so far is consistent with a sender about to appear, which is what quiescence must rule out. The deferred-mechanism block is kept as the surface a successor reuses, and `archive_drain_reason` updated to match. "Drain per closed sender" is recorded below as an operator proposal.
(iii) One shared predicate `find_stream_end_marker` consulted at both entry points: `cmd_inbox_write` refuses with the new `stream_closed` code, `cmd_inbox_close_stream` returns idempotent success naming the existing marker with `already_closed`. Documented in `inbox-envelope.md` § Write-side deliverability beside the `undeliverable_to_running_plan` precedent, and in `SKILL.md` § `inbox write` / § `inbox close-stream`. **Seen RED: `4 failed, 2 passed, 43 deselected`**, the two passes being the open-sender and other-sender controls — confirming the gap's record of both calls succeeding pre-fix.
(iv) `inbox-envelope.md` § Drain semantics and `SKILL.md` § `inbox list` now tabulate **three** zeros, naming BLOCKED (`live_count: 0` with `invalid_count > 0`) explicitly. A test pins the blocked zero as distinct from the empty one *on the two fields the old two-way reading looked at*, so the two states are asserted against each other rather than each in isolation.

**D6 — the epic tree, the migration, and the dispatch label** (`c924026d`).
(i) `settled.md` declared in the Directory Layout block between `history.md` and `references.json`, commented as mid-life relocated settled narrative with pointers resolving there, and added to the § Carve-outs ledger-document list.
(ii)/(iii) `cleanup.md` § Step 8 carries the migration **before** the script call, as **two mutually-exclusive rules** rather than one — the shape the cold read forced (§ Three cold reads). **Rule 1** applies only when a `## Ordered Queue` is present with **no** `BEGIN GENERATED: ordered-queue` marker: move per-row `Notes` into the annotation zone **first**, then insert the marker pair around the existing table, fabricating no rows. **Rule 2** applies to the opposite case — markers already present with a hand-written line between them — and evacuates that line to the same zone. Only Rule 1 is one-time (its precondition self-destructs); Rule 2 is checked every pass. § Ledger-Compaction Stage states the same obligation next to the never-fabricate rule so the refusal and its remedy read together. `replaced_body` added to `_replace_block`'s return and `cmd_compact`'s `regenerated[]` rows, carrying the pre-write between-marker text for a `regenerated` block and `''` otherwise; **both tests seen RED** (`2 failed, 36 deselected`).
(iv) The canonical-form resolve now carries `--role orchestrator.{surface}`, `--plan-id none`, `--caller` and `--workflow`, with one sentence stating that the resolve seam emits the `[DISPATCH]` line and its paired decision-log record per firing.

**The emitted label was verified, not trusted.** Running the canonical resolve produced, in `.plan/local/logs/work-2026-08-20.log`:

```text
[DISPATCH] (plan-marshall:persona-plan-orchestrator) target=execution-context-level-3 level=level-3 role=orchestrator.analyze workflow=plan-marshall:plan-orchestrator:workflow/analyze.md plan_id=none
```

with the paired decision-log record `(plan-marshall:manage-config) effort resolve-target role=orchestrator.analyze -> target=execution-context-level-3 level=level-3`. The `--default` counterfactual was run on the same site and produced `role=default` on an otherwise identical line — which is precisely why `--default` is not distinguishable between the `analyze` and `decompose` surfaces, and why the explicit `--role` is mandated.

**D7 — every `inbox` enumeration names the registered set** (`b2d56dbb`).
(i) `SKILL.md` § `inbox validate` enumerated **seven** of the fourteen D1(b) codes. It now tables all fourteen in check order with the raising seam, and the "checked in that order" clause is made exact (state checks run after the base sweep). The unreachable `invalid_envelope` fallback is named as the defensive default rather than as a fifteenth outcome. The pinned tuple in `test_inbox_validate_still_lists_every_retained_rejection_code` extended to the full set; **the guard was verified to bite** by deleting `revision_not_monotonic` from the section and seeing `1 failed, 53 deselected` (file restored from a byte snapshot, verified).
(ii) `inbox-envelope.md` § Related extended to the full ten-verb surface. **Every added name was confirmed to have a `### inbox {verb}` target in `SKILL.md` before being written** — all ten resolve.
(iii) The `inbox` subparser's `help=` literal replaced.
(iv) `_add_inbox_group`'s "Sub-verbs:" line made the full ten-verb set in registration order.
(v) `inbox-envelope.md` § Invariants: the bullet's lead said "one sanctioned in-place edit" while its body named three, and it classified `close-stream` as an in-place mutation. Lead and list now agree on **two** (`amend`, `supersede`), `close-stream` is classified as an append — `cmd_inbox_close_stream` composes a fresh envelope and allocates a new path, opening no existing file — and the bullet now cites rather than contradicts `orchestration-model.md` § Ledger Write-Boundary, whose sibling statement already named only those two.
(vi) `_orchestrator_inbox.py`'s drain-surface paragraph rewritten to `inbox/archive/{sender}/`, preserving the flat-destination carve-out for an off-shape source name so its link error still surfaces as `invalid_message_name`. The never-a-caller-supplied-path claim is kept — **checked in both branches** by reading `cmd_inbox_archive`'s destination computation, where the destination is composed from validated parts either way.

⚠ **A plan premise was refuted here and the deviation is recorded rather than followed.** D7(iii) instructs the run to "mirror the already-correct module docstring". Re-derivation showed that docstring was **itself one verb short** — both its brace list and its prose omitted `landing-check`. Mirroring it would have propagated the defect. It was corrected instead, making this a **fourth** `orchestrator.py` site D7 touched rather than the three the plan enumerated.

**D8 — records and registration cosmetics** (`7e269c79`).
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

**250 report.** The duplicated tail of four unfilled `_pending_` sections (`## Cost

Each figure carries its population.

- **Tokens (this session):** **not available to the agent** in this Claude Code cloud session — stated plainly rather than estimated.
- **Verification sub-agent tokens (harness-reported):** round 1 ≈ 281,258 · round 2 ≈ 232,386 · round 3 ≈ 197,259 · round 4 ≈ 157,147 · round 5 ≈ 151,512 · round 6 ≈ 255,043 · cold read 4 ≈ 101,462. Round 7's figure is not included — it was still running when this section was written. **Population:** output tokens for the dispatched verification agents only, as the harness counts them; it excludes the main session, which is the larger share and is unavailable.
- **Wall-clock:** not separately instrumented. The two long build gates are measured: the final `./pw verify` took **535.49 s** (module-tests sub-step), and the historical re-derivation run at `51d1c9bc` took **421.71 s**.
- ⛔ **Not comparable to a plan-marshall `metrics.toon` total.** That figure counts the orchestrator-plus-agent dispatch tree under plan-marshall's own per-task billing boundary, which a single interactive cloud session does not share. No parity is claimed, and the figures above are not offered as a substitute.

## Contract check (Step 9)`, `## What have we learned (Step 9)`, `## Residue`, each already filled earlier in the file) was deleted — 16 lines, verified before deletion to contain only those four headings and `_pending_` bodies. Every `## ` heading now appears exactly once.

Test counts re-derived at **this plan's own landed commit `51d1c9bc`** (the state the report describes — its tree extracted and re-run with `uv run python -m pytest -o addopts=""`). All three were one low:

| Figure | Report said | Re-derived at `51d1c9bc` |
|---|---|---|
| the new file (`test_inbox_message_state.py`) | 41 | **42 passed** |
| the four inbox test files | 223 | **224 passed** |
| `test/plan-marshall/plan-orchestrator/` | 549 | **550 passed** |

The site set was re-derived from the report rather than taken from the gap: the two the gap names are the `223` figures, and the sweep found **four** count-bearing statements — the two `223`s, the `41`/`549` pair on the same line, and the `16287` module-tests figure treated next.

⚠ **The fourth figure, `16287`, is NOT cleanly re-derivable, and was left standing with its population rather than replaced.** A re-run over the same commit's extracted tree with `uv run python -m pytest test/plan-marshall/ -o addopts="" -n auto` produced **16281 passed, 10 failed, 1 skipped** — **16292** collected at that base. ⛔ **No delta against the report line is measurable**: that line states `16287 passed, 1 skipped; 2 failed + 1 error` and **no collected total at all**. Deriving one as `16287 + 1 + 2 + 1` is an inference, not a reading — a pytest *error* can be a setup/teardown error on an item already counted — so it is not stated here as a figure. The two runs sweep the **same test path** (`build.get_test_path('plan-marshall')` returns `test/plan-marshall`, executed and confirmed), so "different population" is not the reason and is not claimed. ⛔ **No cause is assigned for the difference, deliberately.** Three earlier attempts to name one were each refuted: that `./pw module-tests` applies coverage (it does not — `cmd_coverage` is a separate sibling and `addopts` carries no `--cov`); that clearing `addopts` moves the collected total (it does not — at `51d1c9bc`, the base this figure belongs to, `test/plan-marshall` collects **16292** both with `addopts` applied and with `-o addopts=""`); and that ignored `xdist_group` pinning explains the flake (it does not — neither flaking module carries a group marker, and the `--dist=loadgroup` run itself produced 3 non-passes). What can be stated is the **verified difference set**, with no causal claim attached to it: the runs use different xdist scheduler classes (`--dist=loadgroup` → `LoadGroupScheduling`, versus the default `load` → `LoadScheduling`); `./pw` passes `--basetemp` to a prepared session root while the re-run took pytest's default, which `build.py` itself documents as a cleanup-race source; the invocations differ (`uv run pytest` versus `uv run python -m pytest`, which puts the CWD on `sys.path`); and `addopts` is applied versus cleared. Which of those produced the one-item collected delta, or the differing pass counts, is **not established** — and naming one would be the manufactured provenance this correction exists to remove. What the figure carries instead is its command, its base, and the fact that it is a sample of an order-dependent quantity rather than a stable count. Substituting 16281 would report a number produced under a different invocation as a correction to this one, which is the manufactured-precision defect this epic exists to close. What was corrected is the figure's **provenance**: both of its sites now name the command and the base (`51d1c9bc`) and say it is a sample of an order-dependent quantity rather than a stable one. Recorded as a **survivor** in § Findings.

**300 report — the stale-restatement figure.** The disposition table's own multiplicities were re-derived: **8 rows citing 13 distinct line locations across 5 files** (two rows carry `×2`, one carries `×4`). The report stated **11** at three sites, contradicted by its own evidence table. Every statement now equals 13, and the table's lead-in states the multiplicity the figure is derived from. This is a fourth site the gap did not name — the `**Disposition — all 11 fixed**` lead-in, corrected with the rest.

## Expected surface — confirm/refute

**HYPOTHESIS REFUTED BY EXACTLY ONE FILE — which is the shape the plan's own hedge predicted** ("expected to be complete, but a fix may reach one file further"). Re-derived from `git diff --name-only origin/main...HEAD`: the diff reaches every file the Expected surface lists, plus **three** it does not.

| Path | On the list? | What it is |
|---|---|---|
| `doc/plans/truthful-signals/520-…/plan.md` | no | lane machinery — the Step 3 directory move |
| `doc/plans/truthful-signals/520-…/report-01.md` | no | lane machinery — this report, which the lane requires and the surface list does not enumerate |
| `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/emit-landing.md` | **no** | **a real deliverable surface beyond the list** |

⛔ **The third one matters and is disclosed rather than explained away.** `emit-landing.md` is a marketplace bundle file, not lane machinery, and the plan says three times that `phase-6-finalize` is a surface it does not touch. It was reached by round 1's fix for verifier finding 8: the producer doc told an author to write `n/a` for an unreadable fact and gave no hint that D3 now makes `n/a` in five of those keys report the landing INCOMPLETE.

**Why the edit still stands.** § Out of scope excludes changing the producer *contract* — what a conforming producer must EMIT. The edit changes nothing a producer must emit: `n/a` on a failed read remains correct and still never blocks the emission. It adds one sentence telling the author what the consumer will do with it, and a cross-reference. That is a documentation pointer, not a contract change. But it IS a file outside the declared surface, so the hypothesis is recorded **refuted**, not confirmed — the honest verdict is the one the confirm/refute artifact actually produced.

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

**Python-change verdict, from git rather than recollection.** `git diff --name-only origin/main...HEAD -- '*.py'` returns **eight** files — three production (`manage-config.py`, `_orchestrator_inbox.py`, `orchestrator.py`) and five test — so the gate takes its full path. The working tree was verified clean (`git status --porcelain` empty) before the diff was read, so no uncommitted file was invisible to it.

**Per-commit gate.** Every commit touching `*.py` was preceded by `./pw quality-gate`, read for the tool-level clean lines rather than the exit code: `mypy … Success: no issues found`, `ruff … All checks passed!`, `SPDX-header check passed`, and `issues[0]`.

**Full `./pw verify` on the final head** — all three sub-steps, each confirmed separately rather than from the summary line:

| Sub-step | Result |
|---|---|
| quality-gate | `mypy` **Success: no issues found in 416 source files**; `ruff` **All checks passed!**; **SPDX-header check passed**; `issues[0]` |
| test-compile | `mypy test` **Success: no issues found in 783 source files** |
| module-tests | **21353 passed, 14 skipped** in 535.49s |

`=== verify: SUCCESS ===`.

⛔ **`test-compile` is why the narrower calls are not a substitute.** Neither `quality-gate` nor `module-tests` type-checks the test tree, and a test-only type error is exactly what would pass locally and fail CI. It was run.

**Stale-base re-verification (§ Step 8 condition 2).** `git rev-list --count HEAD..origin/main` was **3** mid-run, so the condition applied. `origin/main` was merged **on the branch** (the default shape), and the gate re-run on the merged tree — the figures above ARE that re-run, taken after the merge. The merged content was plans and docs only: `git diff --name-only` over the merge commit, filtered to exclude `doc/plans/`, returns nothing, so the merge added no buildable footprint. The count is re-derived at the merge gate below.

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
| 15 | verifier | A PEP8 blank-line regression in `orchestrator.py`, ungated (ruff's E301–E306 are preview-only). | **fixed** |
| 15b | verifier | The same regression in `_orchestrator_inbox.py`. Recorded as its own row: one finding per instance. | **fixed** |
| 16 | verifier | A 132-char docstring line among ~80-char neighbours, ungated (E501 disabled). | **fixed** |
| 17 | verifier | `find_stream_end_marker`'s per-write cost was documented nowhere. (⚠ The verifier's own statement of that cost — "reads and validates every queued message" — is FALSE, as R2-4 established: the loop skips a non-matching sender's path before opening it. The finding that the cost was undocumented stands; its stated bound did not.) | **fixed twice** — round 1 added a Cost paragraph carrying the verifier's wrong bound; round 2 replaced it with the two bounds the code actually has |
| 18 | verifier | Report said "recorded as a survivor in § Findings" while § Findings was `_pending_`. | **fixed** — this section |

### Round 2 — independent verification sub-agent

Round 2 was pointed at a different and narrower subject than round 1: **what round 1's fixes made false, and what round 1's fixes themselves got wrong** — because by round 2 the highest-risk text in the tree is the prose round 1 wrote to explain its own corrections, which is young, unreviewed, and on nobody's list of consumers to grep for. It found **14**, ten of them condition A. Two are self-inflicted by round 1 in the strongest sense, and two more are prose round 1 wrote to close cold-read findings and never had cold-read.

| # | Finding | Disposition |
|---|---|---|
| R2-1 | § Expected surface said "**two** paths not on the list" and "no fix reached a file beyond the list". Both false: there are **three**, and the third — `emit-landing.md` — is a marketplace bundle file reached by round 1's own finding-8 fix. The "no fix reached a file beyond the list" clause is falsified precisely and only by a round-1 fix. | **fixed** — verdict restated as **REFUTED by one file**, which is the shape the plan's own hedge predicted, with the edit's in-scope justification stated rather than assumed |
| R2-2 | `cleanup.md` Step 8 lead-in **mandated the ordering its own rationale warns against**: it said do the migration first, then gave as the reason a hazard that only arises if you do the relocation second. The document's physical block order is the opposite of the mandate too. Same defect family — list order opposite to mandated order — that cold read 2 caught inside this very step, reintroduced by the fix for it. | **fixed, then corrected twice more** — round 3 replaced the rationale with its inverse, round 4 refuted that, and the shipped text now gives NO rationale: the order is a stated convention and the document explicitly declines to say what another order would do |
| R2-3 | The report's D6 description was the **pre-rewrite conflated version**: it stated the two rules as one, under a condition (markers absent) that makes the evacuation half unreachable, and listed insertion before the `Notes` move. The commit that fixed the sibling restatement did not sweep the report. | **fixed** — restated as two mutually-exclusive rules in mandated order |
| R2-4 | `find_stream_end_marker`'s **Cost paragraph, added by round 1 to close its own finding 17, states a false bound**: the loop skips a non-matching sender's path *before* opening it, so file reads are O(this sender's messages), not O(queue). Round 1 documented the cost it had just complained was undocumented — wrongly. | **fixed, then corrected again** — round 2 stated both bounds separately, but its enumeration bound was itself wrong (`O(n)` where `list_messages` sorts); R3-10 corrected it to `O(n log n)` |
| R2-5 | The **S1 provenance note asserted an invented mechanism, at both its sites**: `./pw module-tests` applies no coverage flag, and clearing `addopts` demonstrably does not move the collected total (**16292 either way at `51d1c9bc`**, the base the figure belongs to). The two runs sweep the same path. The load-bearing half of S1's offered bound was fabricated — the same defect class round 1's finding 3 caught. | **fixed** — rewritten on the verified mechanism (`--dist=loadgroup` vs default `load`, read from `build.py`), with the collected delta carrying no assigned cause |
| R2-6 | `analyze.md` — a **fourth** site still stating the two-way reading, and the worst-placed one: the **bold instruction an executing agent obeys** named `live_count` and `closed_senders` while the table beneath it has three discriminating columns. | **fixed** |
| R2-7 | `cmd_inbox_close_stream`'s docstring — a **fifth** site, in the very file round 1 swept. Round 1's row 2 said "fixed at all three sites"; it was accurate about the three it named and the finding was under-scoped by two. | **fixed** |
| R2-8 | `cleanup.md`'s zone-creation instruction, added by round 1 for the cold read, positions the new zone "immediately after the marker pair's `END`" — but Rule 1 step 1 runs **before** step 2 inserts that marker, so at the moment the instruction is needed there is no `END` to position against. | **fixed** — positioned against the existing table instead |
| R2-9 | Report said "four suites touched"; five test modules changed. | **fixed** |
| R2-10 | Report said "three `SKILL.md` surfaces" — the diff has one `SKILL.md` and touches six skills. Re-derives under no reading. | **fixed** |
| R2-11 | Report said "the three other occurrences"; there are five producer sites across three functions. | **fixed** — the branch claim itself re-verified true |
| R2-12 | § Findings opens "One finding per instance, never bundled" and row 15 then bundled two PEP8 sites into one row. | **fixed** — split into rows 15 and 15b |
| R2-13 | `SKILL.md`'s reworked cross-reference said "codes 4–14 … does not carry rows 1–3", but the target table numbers those same codes **1–11** and does have rows 1–3 holding different codes. Not false (a relative clause disambiguates) but a reader sent for "code 14" finds nothing. | **fixed** — match by code name, with the numbering mismatch stated |
| R2-14 | `orchestration-model.md`'s corrected clause over-claimed: "once `orchestrator.effort` carries anything" — a block carrying only a non-binding `max`, or a `default` equal to `plan.effort`, produces no divergence. | **fixed** |

Round 2 also **confirmed by execution** that round 1's substantive fixes are right: the `emit-landing.md` pointer matches `check_landing_completeness`'s actual behaviour on both an all-`n/a` block and a `pr`/`merge_state`-only-degraded one; the undefaulted `unreachable_blocks` parameter has one call site, always passing it; the three discriminator triples and the three state names agree across all four surfaces (the surrounding prose and header cells differ, and the fourth surface is a code comment rather than a table — so this is agreement on the load-bearing content, not byte-identity); and the D6(iv) dispatch-log lines corroborate the report exactly. It re-derived every population and figure independently, including the full 51-id gap set and the plugin.json 6→4 inversion count.

**One pre-existing defect noted and deliberately NOT fixed** (out of scope, recorded as residue): `emit-landing.md` transcribes `merge_state` as `merged` / `open` / `n/a` while `landing-payload-spec.md` declares five values including `closed` and `unknown`. Unchanged at `origin/main` and unchanged by this branch; flagged only because round 1 edited that file.

### Round 3 — independent verification sub-agent

Round 3 was aimed at round 2's corrections, on the same rule: any clause naming a mechanism must be **executed**, not read. It found **10**, and — more valuably — it named the **generator** behind all three rounds.

| # | Finding | Disposition |
|---|---|---|
| R3-1 | The S1 bound was refuted a **third** time. Round 2's replacement mechanism ("ignored `xdist_group` pinning makes the passed count order-dependent") is false: neither flaking module carries a group marker, and the `--dist=loadgroup` run *itself* produced 3 non-passes — refuted by the very datum it cites. "What actually differs is the xdist distribution" was also over-scoped, omitting `--basetemp` (which `build.py` documents as a spurious-failure source) and `pytest` vs `python -m pytest`. | **fixed by removing the causal claim entirely.** The note now states the **verified difference set** and explicitly assigns **no cause** — see the generator note below |
| R3-2 | `cleanup.md`'s zone-creation instruction — rewritten twice — was wrong in the **other** branch each time. Round 2's version positioned the zone "immediately after the existing table", correct for Rule 1 but, in the Rule 2 branch (markers present), a position **inside the generated region** — the exact loss the same sentence forbids two clauses later. | **fixed** — the position is now given per branch, with the "neither rule applies" case stated |
| R3-3 | `orchestration-model.md`'s effort-divergence enumeration **omitted a binding `max`**. Verified by execution: with `orchestrator.effort = {"max": "level-2"}` and `plan.effort = level-5`, `--role` resolves to `level-2` (clamped) and `--default` to `level-5`. The clamp is post-walk, so "a value that walk would reach" excluded exactly the third divergent case — and the parenthetical's careful "*non-binding* max" shows the distinction was known and its complement dropped. | **fixed** — all three divergent configurations named, with their complements |
| R3-4 | Round-1 finding row 17 still stated, in the present tense, the O(queue) bound R2-4 refuted — and its disposition claimed the added paragraph "stated the bound". Round 2 swept the docstring and added R2-4 but left the row. The same under-scoped-sweep shape round 2 caught in round 1. | **fixed** |
| R3-5 | The § Three cold reads table certified a **pre-split intent** ("only when the marker pair is absent" — the shipped passage has Rule 2, which fires when it is present), and its ✅ was **stale**: the passage changed three more times after the last cold read. | **fixed** — intent restated, staleness disclosed, and **cold read 2 re-run a third time against the shipped text** |
| R3-6 | "the three-zero table is byte-consistent across all four surfaces" — the triples and state names agree, but header cells and prose differ and the fourth surface is a code comment, not a table. Claimed a stronger verification than was performed. | **fixed** |
| R3-7 | "standards/workflow docs across six skills" is five; six is the count of skills touched at all. R2-10's finding was right and its fix reattached the number to the wrong noun. | **fixed** |
| R3-8 | "Findings 1–18" stopped naming every row once R2-12 split out 15b — under a section opening "one finding per instance". | **fixed** |
| R3-9 | "Round 1 / Round 2" meant two different sequences in one document — cold-read passes and verification rounds. | **fixed** — cold-read passes are now "passes" throughout |
| R3-10 | `find_stream_end_marker`'s enumeration bound: `list_messages` sorts, so it is O(n log n), not O(n) — in a paragraph whose own framing is "stated precisely because the two bounds differ". | **fixed** |

### Round 4 — independent verification sub-agent

Round 4 asked one question: **did removing the causal claims break the generator?** The answer is **no**. It found 12, three of them fresh unverified mechanisms authored by round 3's own commit — and one of those is a **regression**, shipped text less true than it was a commit earlier.

| # | Finding | Disposition |
|---|---|---|
| V4-1 | The S1 survivors row was the **third site** of the refuted `loadgroup` mechanism, and endorsed it as "now verified". R2-5 swept two sites and said "both"; round 3 swept the same two. The under-scoped-sweep shape, on the same finding, for the third consecutive round. | **fixed** — the row now matches the notes and asserts no cause |
| V4-2 | ⛔ **A regression.** Round 3's commit message says the Step 8 ordering rationale was *removed*. It was **replaced** — by a false universal ("a queue annotation the migration has just written is live by construction, so neither order can corrupt the other"). Refuted by one admissible ledger: a pre-marker table whose `Notes` cell reads *"Landed in PR #900. Do NOT re-derive."* — Rule 1 moves it into the annotation zone, its subject is closed, and it is exactly the anti-rework artefact the relocation paragraph names. Rule 1's precondition guarantees the liveness filter has never run on that ledger. | **fixed** — the rationale is now genuinely absent. The order stands as a determinism choice, with an explicit ⛔ that **no claim is made in either direction** about the other order |
| V4-3 | "Three configurations diverge … their complements do not" reads as exhaustive and omits the **scalar shorthand** (`orchestrator.effort: "level-6"`), a first-class CLI-writable form that `effort-roles.md` names. The R3-3 defect one iteration later. | **fixed** — restated as a **rule** with illustrative examples and an explicit non-exhaustiveness ⛔. The shorthand case was **run** before being written: `level-6` vs `level-1` |
| V4-4 | Round 3 deleted the hedge on `16291` and kept the number — converting a correctly-flagged inference into a bare assertion, in the commit whose stated purpose was to stop asserting unverified things. The one-item delta the note is organised around may not exist. | **fixed** — the hedge is restored at both sites that STATE the figure (`250:79`, `520:138`; the other occurrences are meta-references to this finding). Round 5 then established the stronger result: no delta is measurable at all, because the report line states no collected total |
| V4-5 | R3-9 claimed cold-read passes were renamed "throughout"; one site kept "round 1 / round 2", and the new parenthetical made it an explicit self-contradiction. | **fixed** |
| V4-6 | § "The generator, named" **mis-attributed both of round 3's cited mechanisms to round 3**. `git log -S` places both at `166fea79` — they are round 2's. The section's headline analytical claim was unsupported by its own evidence. | **fixed** — attribution corrected, and the count restated as four-for-four measured on each round's own commit |
| V4-7 | `17710 either way` is the branch head's population, not the note's base — inside the note that establishes the state-your-base rule, three sentences from "its command, its base". At `51d1c9bc` the figure is 16292. | **fixed** — both figures now carry their base |
| V4-8 | "Three actions in that case, not two" is false on the ledger round 3's *own* adjacent bullet describes (Rule 1 applies, no `Notes` content → no zone, so two actions). Both sentences were written in the same commit. | **fixed** |
| V4-9 | `18 → 14 → 10` counts round 1's table at 18 while § Rejected says "1 through 18, plus 15b" — 19 under the section's own one-finding-per-instance rule. | **fixed** |
| V4-10 | R2-4's disposition still said "both bounds now stated **precisely**" after R3-10 found its enumeration bound wrong. | **fixed** |
| V4-11 | "Two pre-existing defects" above a list of three. Round 1 finding 4's shape, recurring. | **fixed** |
| V4-12 | The Rule 1 zone-placement bullet read unconditionally, so a top-to-bottom reader acts on it before the no-content bullet — the list-order family cold read 2 had already caught twice in this passage. | **fixed** |

### Round 5 — independent verification sub-agent

Round 5 targeted `ec223e2e` and found **15**. Its central result is a sharper diagnosis than round 3's: the recurring class is not "unverified mechanisms" but **prose that narrates its own verification** — clauses of the form *"each run rather than reasoned"*, *"`git log -S` places all three"*, *"both figures now carry their base"*, *"all three sites"*, *"four rounds for four"*. Each is a claim **about having checked something**, and correcting one in the same register produces the next.

| # | Finding | Disposition |
|---|---|---|
| R5-1 | The cold-read pass-3 write-up still asserted, in present tense, the exact universal round 4's own V4-2 row calls a refuted regression — 53 lines apart in one file, so the report asserted and refuted the same sentence. The under-scoped-sweep shape, same finding, **fourth** consecutive round. | **fixed** — neither direction is asserted; both rationales are recorded as withdrawn |
| R5-2 | ⛔ **Shipped text, false by execution.** "the scalar shorthand … **which the walk reads at the `default` rung**" — it does not: a string is handled at its own branch with source `orchestrator.effort`, so unlike `default` it **cannot be clamped by `max`** (which is read only from the object form). Written inside the sentence advertising "each run rather than reasoned". | **fixed** — the shorthand's actual rung and its clamp consequence stated |
| R5-3 | "`git log -S` places all three at `166fea79`" — the O(queue) bound was added at `7d308fab` (round 1), as the report's own R2-4 row and row 17 both say. An attribution asserted *with its method named*, and wrong. | **fixed** |
| R5-4 | "Round 1's was the `--default` tier claim" — `git log -S` places its introduction at `c924026d`, the original run, and its deletion at `7d308fab`. Round 1 **found and removed** it. | **fixed** |
| R5-5 | "**four rounds for four**" — the fourth data point required a fresh mechanism in `ec223e2e`, which nobody had reviewed when the sentence was written. A prediction stated as a measured score, in the section whose thesis is that unmeasured claims are the defect. | **fixed** — the section no longer scores itself |
| R5-6 | "**Across three rounds** the count **fell** (19 → 14 → 10 → 12)" — four counts under "three rounds", and 10 → 12 is a rise. | **fixed** |
| R5-7 | "three of them fresh unverified mechanisms" under-counted: V4-8 and V4-12 are also at `c239c9aa`, and V4-8 is a false completeness claim — the class the same paragraph was defining. | **fixed** |
| R5-8 | "both figures now carry their base" — only the 250 note was fixed; the 520 note still carried a bare `17710`, inside the note establishing the state-your-base rule. Third site of the same figure. | **fixed at all three sites**, and the figure replaced by `16292`, which is the one belonging to that base |
| R5-9 | ⛔ **Shipped text.** The order's sole surviving justification — "fixed so that two orchestrators on the same ledger produce the same result" — is not established: the relocation half is operator-confirmed and defers entirely when no operator is reachable, so two orchestrators can differ regardless of order. | **fixed** — stated as a convention of the document, with no outcome claim |
| R5-10 | ⛔ **Shipped text.** Fixing V4-8 opened a new hole in the same sentence: `(markers absent, Notes present, zone ALREADY present)` was covered by the pre-image's complement and by neither branch of the replacement. | **fixed** — zone creation is described by its own condition rather than by an action count |
| R5-11 | ⛔ **Shipped text.** The non-exhaustiveness ⛔ over-claimed: an out-of-enum value returns `status: error` and no level, and divergence is **per surface**, not per configuration — `{"analyze":"level-6"}` diverges at `analyze` and agrees at `decompose`. | **fixed** — restated per surface, with the error outcome named |
| R5-12 | R2-2's disposition still said "with the correct reason" after the shipped text stopped giving one. | **fixed** |
| R5-13 | "restored at all three sites" — the figure is stated at two; the others are meta-references. | **fixed** |
| R5-14 | The third cold-read pass's ✅ went stale when rounds 4 and 5 rewrote the passage again, and the ⛔ disclosing exactly this hazard for passes 1–2 was not extended. | **fixed** — staleness disclosed; **no fourth pass was run** |
| R5-15 | Six items across three statements say "recorded as residue" while § Residue was `_pending_`. Round 1 finding 18's shape, recurring. | **fixed** — § Residue filled |

**One finding rejected, with reason.** Round 5 also noted that `orchestration-model.md` calls the zone `### Annotations` while `cleanup.md` says `### Queue annotations`, and that four rounds had missed it. It is **not a defect**: `templates/epic.md` carries **both** zones — `### Annotations` under `## START HERE` (line 29) and `### Queue annotations` under `## Ordered Queue` (line 56) — and the standard names both correctly where it enumerates them. The one site using the bare name uses it generically for the pattern. No change made.

### Round 6 — independent verification sub-agent (scope narrowed to shipped text)

The operator extended the budget by five rounds. On round 5's recommendation, round 6 was pointed at `marketplace/**` and `test/**` ONLY — the text consumers execute — and told to leave the run report's narrative alone, under a hard rule that any clause asserting what a function returns must be RUN.

**The narrowing worked.** Round 6 found **9, all 9 in shipped marketplace text and 0 in the run report**, and its six independent spot-checks of report figures all came back correct. By its own count the distinct defect count is nearer four: A1–A3 collapse to one phrase sweep, and A4/A5 are one word and one sentence.

| # | Finding | Disposition |
|---|---|---|
| R6-A1 | ⛔ **Production docstring.** `cmd_inbox_landing_check` still said the check lets the orchestrator establish "that nothing material is outstanding" — verbatim the overclaim D3(ii) exists to delete, surviving in code. | **fixed** |
| R6-A2 | ⛔ **`SKILL.md` § `inbox landing-check`, two false clauses in one paragraph.** (a) "every required key **non-empty** (`complete: true`)" — executed: `total_tokens=n/a` is non-empty and returns `(False, ['total_tokens'])`, so non-empty is no longer sufficient. (b) the same "nothing material is outstanding" overclaim. | **fixed** — both |
| R6-A3 | ⛔ **`analyze.md:106`** — the Step 4 lead-in still carried the overclaim, **twelve lines above its own correction**, in the file the run edited for exactly this. The third cold read was shown the corrected bullet and never saw this lead-in. | **fixed** |
| R6-A4 | `cleanup.md` attributed `compaction_regenerated[]` — **this document's own** report key — to the script, whose payload key is `regenerated`. The same file uses the distinction correctly at two other sites. | **fixed** |
| R6-A5 | `check_landing_completeness`'s docstring LEAD sentence stated a sufficient condition the function does not implement ("with a non-empty value"), corrected only by a bullet fifteen lines below. | **fixed** |
| R6-B1 | The dispatch record is not emitted from the sites that actually resolve: `analyze.md` and `decompose.md` name the resolve command without `--workflow`, and a bare `--role` resolve writes **no log file at all**. | **survivor S2** — see below |
| R6-B2 | A **fourth** zero the three-zero table absorbs into EMPTY: a queue holding only `superseded` messages yields `live_count 0 / closed_senders empty / invalid_count 0` with `count > 0`. | **survivor S3** — see below |
| R6-B3 | `applied[]` has no legal row shape for a relocated `epic.md` section, and a deferred relocation has no field. | **residue** — pre-existing, items 1–2 of § Residue |
| R6-B4 | `emit-landing.md` maps any `inbox write` error to `loop_back`, and a loop-back cannot clear `stream_closed`. **Unreachable** — no shipped step calls `close-stream`. | **residue** — recorded, not fixed |

Round 6 also verified, by execution rather than reading: the whole stream-closure lifecycle through the real CLI; six `orchestrator.effort` configurations against the rewritten `orchestration-model.md` paragraph (**every clause holds**, including the shorthand's rung and the per-surface divergence); `sync-defaults`' non-destructive back-fill, which confirms the plan's ⛔ against running it; the ten-verb set derived from the live CLI; the fourteen-row rejection table's order against source order; and **four mutation tests, all of which bit**. 1747 tests green.

### The fourth cold read of `cleanup.md` § Step 8

Run in parallel with round 6, against the shipped text — the pass § Three cold reads records as owed. It built **seven fixture ledgers and called `cmd_compact` on each** rather than reasoning about the passage. Its verdict on whether it could execute the step correctly, unattended, on an arbitrary ledger: **NO**. Eight defects, five of them reachable states.

| # | Finding | Disposition |
|---|---|---|
| CR4-1 | ⛔ **A CLOSED epic reached Phase B and got hand-edited.** Both judgement blocks write `epic.md` directly and both run BEFORE the script, so `cmd_compact`'s own `refused_closed` protected only the script's write. No other `cleanup` step carries a phase gate, and a closed-but-unarchived epic still has an active store tree. | **fixed** — Step 8 reads the phase FIRST and skips the whole phase; `ledger_compaction` gains `refused_closed` |
| CR4-2 | "Mutually exclusive **by construction**" was false — Rule 1's condition was section-scoped, Rule 2's file-scoped. **Reproduced on a fixture**: the script regenerated the STALE pair, left the real queue duplicated, and reported `unreachable_count: 0` over a genuine blind spot. | **fixed** — both read at the scope `_marker_indices` uses; stated as at-most-one, not as complements, which they are not |
| CR4-3 | `resume-summary` had **no migration rule at all**, though line 90's permanent-refusal diagnosis applies to it verbatim and `GENERATED_BLOCKS` names both. A permanent blind spot the step diagnoses and then does not remedy. | **fixed** — the migration is per block, with a table giving each block's owning section, annotation zone, and wrapped content |
| CR4-4 | Two zone-creation bullets matched the same ledger state (pair present, no hand-written line, no zone); the tie was broken only by reading three paragraphs further. | **fixed** — keyed on the rule that fires, not on marker presence |
| CR4-5 | "its owning section is reported `markers_absent_not_regenerated`" is false when the owning heading is absent — **fixture E: `unreachable_count 0`**, and `orchestrator.py` documents exactly this. | **fixed** — qualified |
| CR4-6 | ⛔ **The migration had NO report field.** A correct migration and an omitted one were indistinguishable: `replaced_body` names what the SCRIPT overwrote, which after a correct migration is empty precisely because the move succeeded. | **fixed** — `compaction_migrated[]` declared, required, never omitted |
| CR4-7 | The order was mandated with its rationale explicitly withheld, at the one point where relocation can carry away the migration's destination. | **fixed** — replaced by the invariant that makes the order genuinely not load-bearing: an annotation zone is a live working surface and is **never** a relocation candidate |
| CR4-8 | "Three blocks follow" stood above five bold-led blocks. | **fixed** |

⭐ **CR4-6 is the epic's own thesis turned on the document that states it.** `cleanup.md` says three times that a silent application is indistinguishable from a lossy one — and left its own direct structural write to `epic.md` unreported.

### Round 7 — final round, frozen tree, scoped to the young corrections

Round 6 recommended stopping but raised one caveat against its own verdict: `cleanup.md` was being rewritten by cold-read fixes **while it verified**. Round 7 ran against a frozen tree (no edit was made between dispatch and result) and targeted only `git diff f2f0013d~1..HEAD -- marketplace/ test/` — the corrections themselves, which five rounds of evidence identify as the highest-risk text.

**It confirmed both predictions rather than refuting them.** 3 findings, all shipped text, all mechanical.

| # | Finding | Disposition |
|---|---|---|
| R7-1 | ⛔ **The D3 overclaim at a FOURTH site** — `test_landing_completeness.py`'s own module docstring, a test file's statement of what the code under test guarantees. Round 6's fix reached three of four. Established by execution: `pr=n/a & merge_state=n/a` → `(True, [])`. | **fixed**; the sweep now returns **zero** across `marketplace/`, `test/` and `.claude/` |
| R7-2 | ⛔ **A FRESH self-contradiction, introduced by `f2f0013d` in the bullet it was editing.** `orchestration-model.md` described Rule 2 as applying to "the opposite case" and then, one clause later, said the two rules are NOT complements — but if Rule 2 were the opposite case they would be. Established by fixture: after one pass the markers are present with no hand-written line and `_replace_block` returns `unchanged`, the state matching neither rule — **the steady state of every ledger after its first compaction**, not an edge case. | **fixed** |
| R7-3 | The same commit added a fourth `compaction_*` key and left "The three `compaction_*` keys" standing two paragraphs above it. | **fixed** |

Round 7 additionally found a **fail-open in the phase gate `f2f0013d` added**: a `manage-status read` that errors, or a payload carrying no `phase`, was read as *not-closed* rather than *unobserved* — in the one gate whose entire purpose is that the writes it protects happen before anything else can refuse them. **Fixed**: it now fails closed and reports `ledger_compaction: indeterminate`.

**All three survivors re-checked by execution; all bounds hold.** S3 proved **tighter** than this report had claimed: a `superseded` row is dispositioned `retired_by_successor` and archived, after which `inbox list` reports `count: 0` — the message is consumed, not silently ignored. The characterisation was pessimistic and is corrected in § Survivors.

### The independent read of round 7's own fixes

Round 7's closing recommendation — because each round's corrections have carried the next round's defects for five consecutive rounds — was that its fixes be read by someone who did not write them before a PR is opened. That read ran against `afd77903` alone.

⭐ **Verdict: no fresh false clause. The first round in eight whose corrections introduced nothing false.** Every added clause was established by running the code or the sweep: eight `check_landing_completeness` fixtures covering the optional-key, degraded-value and empty-value claims; a two-pass `cmd_compact` fixture confirming the "steady state after first compaction" clause; and `cmd_orchestrator_read` driven over three states, which showed the phase-less-but-**successful** payload is genuinely reachable — the fail-open hole was not hypothetical.

It returned **one** finding, and it is an *unsatisfiable* instruction rather than a false one: the new fail-closed clause orders `ledger_compaction: indeterminate` **"with the read's own error"**, while the schema had widened only the scalar enum — leaving nowhere to put the error. **Fixed** by adding `ledger_compaction_reason`, mirroring the `archive_drain` / `archive_drain_reason` pair two lines below and its stated rationale.

It also confirmed the gate's failure direction is the safe one, by fixture rather than by argument: skipping costs a deferred compaction and `cmd_compact` is idempotent, while proceeding runs two direct `epic.md` writes against a possibly-closed tree whose refusal fires only after them. **Deferrable versus unrecoverable.**

One bound it recorded rather than scoring as a defect: "the steady state of every ledger after its first compaction" holds along the conforming path, but a ledger where Rule 1 was owed and skipped reports `markers_absent` on every pass instead. Since Step 8 mandates Rule 1 before the script call, the clause is true as written; the narrower phrasing would be "every compacted block".

### Verification rounds — the record

⛔ **This section is frozen: a table of rounds and counts, and nothing else.** Its two predecessors were
analytical narrations of the loop's own behaviour, rewritten four times, and every rewrite introduced a
defect a later round then had to find — five of round 5's fifteen findings were in two paragraphs of it.
Prose that narrates its own verification is the densest defect source in this document, so this section
no longer contains any.

| Round | Findings | Fixed in |
|---|---|---|
| 1 | 19 (18 rows + 15b) | `7d308fab` |
| 2 | 14 | `166fea79` |
| 3 | 10 | `c239c9aa` |
| 4 | 12 | `ec223e2e` |
| 5 | 15 | `8cc21926` |
| 6 (shipped text only) | 9 | `e6360dd1` |
| cold read 4 | 8 | `f2f0013d` |
| 7 (frozen tree, corrections only) | 3 | `afd77903` |
| read of round 7's fixes | 1 (no fresh false clause) | `d43680a4` |

Cold reads of `cleanup.md` § Step 8: three passes. Pass 1 found two defects, pass 2 found three, pass 3
took the intended reading on all four scenarios put to it and found three further defects.

**What the loop did not do: converge.** The counts do not trend down, and round 5 recorded that its
findings still reach shipped marketplace text rather than narrowing to the run's own record. That is
stated here as the measured outcome; no explanation for it is offered, because none has survived being
checked.

### When the loop stopped, and on what

**Exit: `verifier-clear`.** Not `budget-exhausted`, and the distinction is the whole point of recording it.

- **Budget.** The contract's default is five rounds. Round 5 exhausted it; the operator was reachable, was asked at that boundary with the counts and the survivors, and **granted five more** (rounds 6–10) on identical terms. Rounds 6 and 7 plus two dispatched reads were spent; **three rounds went unused**, which is what makes this a verifier exit rather than a budget one.
- **The round that ended it.** The independent read of `afd77903`, answering the stop question over its own findings and all three survivors.
- **The verifier's own last answer, not the author's:** *"Does this commit introduce any fresh false clause — **no**. Every clause the four edits added is true, and each was established by running the code or the sweep, not by reading a callee and judging it compatible."* Its one finding was an unsatisfiable instruction, fixed in `d43680a4`.
- **The evidence it rests on is stronger than a read.** Eight `check_landing_completeness` fixtures; a two-pass `cmd_compact` fixture establishing the steady-state clause; `cmd_orchestrator_read` driven over three states, showing the phase-less-but-successful payload is genuinely reachable; and a whole-tree sweep for the corrected phrase returning zero. Each could have come back different.
- **Were the late rounds narrower, or merely fewer?** **Narrower, measurably.** Rounds 2–5 found their defects overwhelmingly in the report's own prose about itself; the counts did not fall (19 → 14 → 10 → 12 → 15). Scoping round 6 to shipped text alone changed both: 9 findings, **0 in the report**, and its six independent spot-checks of report figures all correct. Round 7, frozen and scoped to the corrections, found 3. The read found 1, and none false.
- **What residue to assume remains.** The deliverables should be read as still carrying defects of the kind the last rounds found — an enumeration falsified by a later edit, a claim fixed at n−1 of n sites, an instruction ordering a field the schema does not define. Two shipped-text surfaces are the likeliest: `cleanup.md` § Step 8, rewritten six times and the source of a finding in every round that examined it, and any prose written to explain a fix. **The last round found nothing false; that is not the same as there being nothing false.**

⛔ **Stopping is a decision this run made on the verifier's answer, not a state it reached.** Three granted rounds were left unspent. A further round would very likely find something — the honest claim is that the findings have moved from the shipped product to its record and then to near-zero, not that the text is now correct.

### Survivors — left open, each characterised

| # | Finding | Why it may be left open |
|---|---|---|
| S1 | The `16287` module-tests figure in the 250 report is not cleanly re-derivable. | **(b) bounded, with NO cause asserted.** ⚠ This row was itself the **third site** of the refuted `loadgroup` mechanism — R2-5 swept two sites and said "both", round 3 swept the same two, and V4-1 found this one still endorsing the cause as "now verified". Corrected here to match the notes. The bound: neither note states the figure without its command and its base; both list only a **verified difference set** (different xdist scheduler classes, `--basetemp` set versus default, `pytest` versus `python -m pytest`, `addopts` applied versus cleared); and both **decline to say which difference caused what**, including whether the one-item collected delta exists at all, since the report line states no collected total. Condition A does not reach the figure — it is an unreproducible historical observation, not a false statement — and every claim that WAS false around it has been withdrawn rather than replaced. |


**S2 — the dispatch record is not emitted from the two sites that actually resolve** (R6-B1). `orchestration-model.md`'s canonical form now carries `--workflow`, but `analyze.md` and `decompose.md` name the resolve command without it, and a bare `--role` resolve writes no log file at all.

*(b) Bounded.* It reaches **the log and nothing else** — no effort level, no dispatch target, no ledger write and no verdict changes, because `--workflow` gates only the two audit records. The promise it stays outside of: the resolved level and target are byte-identical with and without the flag, which round 6 verified by executing both spellings. D6(iv)'s Done-when is met as the plan scoped it — the plan named `orchestration-model.md` and nothing else — so closing this means editing two verb docs the plan does not list, and 280/G7's symptom persists at those two sites until a plan owning them lands. **Recorded, not fixed.**

**S3 — a fourth zero the three-zero table absorbs into EMPTY** (R6-B2). A queue holding only `lifecycle: superseded` messages yields `live_count 0 / closed_senders empty / invalid_count 0` — the EMPTY triple — while `count > 0`.

*(b) Bounded — and round 7 established the bound is TIGHTER than first stated.* A `superseded` row is dispositioned `retired_by_successor` and archived by `analyze.md` Step 3 item 2, after which `inbox list` reports `count: 0`: the message is **consumed, not ignored**, and Step 6's classification is therefore recorded after the drain, when the queue genuinely is empty. The imprecision is confined to reading the EMPTY row's gloss against the enumeration-time payload. It mislabels **no report line in the conforming flow** and changes no drain behaviour: a superseded row is correctly excluded from `live_count` by design, is correctly not a closed sender, and is correctly valid. Reachability requires a superseded row to outlive its successor in the queue — normally impossible, since `supersede` names a successor that is itself enumerated, and reachable only after an `archive_failed` strands one. The promise it stays outside of: `count` is reported alongside the three discriminators at every one of the four sites, so a reader who checks `count` is never misled. Closing it means a fourth discriminator column across four surfaces plus the code comment, which is a wider edit than the defect warrants. **Recorded, not fixed.**

### Rejected — none

No verifier finding was rejected. Every round-1 row — 1 through 18, plus 15b, which R2-12 split out so the table keeps one finding per instance — was fixed; S1 is a survivor rather than a rejection.

### Deferred — none

No behavioural finding was left unfixed and deferred.

## Three cold reads (§ Verification)

The plan requires an independent reader who has **not** seen the plan for each of three passages whose whole value is what a later reader *does* with them, and requires this report to state **which reading they took**. Each reader was given only the passage, inline, and forbidden to open a file or search the repository.

| # | Passage | Intended reading | Reading taken | Verdict |
|---|---|---|---|---|
| 1 | `cleanup.md` § Step 9 after D5(ii) | **refused**, with a narrower stated reason | "**I refuse.** I do not drain or retire that sender's messages… `closed_senders` naming a sender establishes only that *that named sender* will send no more." Ran neither `bash` command. | ✅ intended |
| 2 | `cleanup.md` § Step 8 after D6(ii)–(iii) | the migration performed **before** the script; marker insertion **only** when the pair is absent, and the between-marker evacuation **only** when it is present | ❌ **the first pass exposed two real defects** — see below. Rewritten, re-read, and the second pass took the intended reading on all three scenarios; a third pass against the shipped text took it on all four. | ✅ intended, after a rewrite |
| 3 | `landing-payload-spec.md` delta table + `analyze.md`'s `complete: true` bullet after D3(ii) | **the required-key subset** | "(b) — only the required-key subset drained… an operator paste could still surface a mechanisable fact the inbox never received." Would not tell the operator "nothing material is outstanding". | ✅ intended |

**Cold read 2 is why this check exists.** Its **first pass** found two defects no build gate could see ("pass" here, never "round" — the verification rounds below are a different sequence):

1. **The numbered list ran opposite to the order it mandated.** Item 1 said "insert the marker pair"; item 2 said "move `Notes` … **before** inserting the markers". A reader executing top-to-bottom does the wrong thing. The reader reached the intended outcome only by overriding the numbering — *"I had to override the list numbering to do so. That is exactly the kind of thing a fast reader gets wrong."*
2. **A step's precondition was the negation of its own gate.** The block was gated on the markers being ABSENT, while step 3 described a ledger that "already has markers" — *"Read literally, step 3 can never fire."*

Fixed by splitting the migration into two explicitly mutually-exclusive rules, each with its own condition and Rule 1's steps in mandated order. **A second pass over the rewritten passage took the intended reading on all three scenarios** and found a third defect: *"'neither is a per-run step' … was FALSE of Rule 2"* — Rule 1's precondition self-destructs, Rule 2's does not, so Rule 2 must be checked every pass. It also found that both rules moved content into a `### Queue annotations` zone the text presumed to exist, and that "the stage has two halves" now stood above three bolded blocks. All three corrected.

⛔ **The ✅ on row 2 certifies a passage that has since changed, and this is disclosed rather than carried silently.** After the second pass, verification rounds 2 and 3 rewrote that same passage three more times — the Step 8 ordering lead-in, the zone-creation position (twice). **Cold read 2 was therefore re-run a third time against the shipped text**; its result is recorded below. The cost of not having done this sooner is concrete: round 3 found that the zone-creation sentence written to close the second pass's finding was wrong in the Rule 2 branch — a passage nobody had cold-read since it was written.

**Third pass, against the shipped text.** It took the intended reading on **all four** scenarios put to it, including the per-branch zone placement that R3-2 had just corrected. ⛔ **That verdict is now stale, and no fourth pass was run.** Rounds 4 and 5 rewrote the same passage again — the ordering lead-in twice, the zone bullet's condition, and the two-versus-three-actions sentence. The shipped text has therefore **not** been cold-read in its current form; that is recorded here rather than left implied by the ✅ above. It found three further defects, all mine:

1. **The ordering rationale was unestablished.** The R2-2 fix had claimed that relocation-after-migration "could sweep content the migration has just placed there into `settled.md`". Round 3 replaced it with the opposite claim — that this could not happen, because such an annotation is live by construction — and round 4 refuted *that* by constructing a `Notes` cell reading "Landed in PR #900. Do NOT re-derive.", whose subject is a shipped plan. ⛔ **So neither direction was ever established, and the report does not assert either.** Both rationales are withdrawn; the shipped text now states the order as a convention of the document and explicitly declines to say what another order would do.
2. **Rule 1 said "its two steps" while three actions are needed** when the zone is absent — zone creation must precede step 1, and it is specified paragraphs earlier, outside the numbered list. The list was not the complete ordered procedure it claimed to be.
3. **Rule 1 forced a speculative empty zone.** Its condition is purely structural, so it fires on a ledger with an empty `Notes` column; zone creation was gated only on "neither rule applies", so that ledger got a zone with nothing to hold — contradicting the passage's own "an empty zone added speculatively is noise" three bullets earlier.

Two further items it raised are **pre-existing and out of scope**, recorded as residue: the deferred-relocation record has no declared destination, and "on a first run" is not an evaluable condition. One was an artifact of the excerpt rather than a defect — `settled.md` *is* introduced in the shipped text, in a parenthetical the excerpt trimmed.

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

## Rebase onto main (operator-directed)

After PR #1314 merged, the operator directed a **rebase** onto `main` rather than the merge this lane defaults to. The hazard was raised before the first bring-in and the operator reaffirmed the rebase, so it was performed — and its consequence, that every replayed commit changes SHA, was handled rather than absorbed.

**What was rebased onto.** `origin/main` at `a34819d9` — PR #1314, the module-budget campaign that split 66 over-budget test modules into 199 test modules plus 64 fixture modules (280 files, +50,276/−42,870). **It touches nothing this branch touches**: `git diff --name-only <merge-base> <#1314 head> -- test/plan-marshall/plan-orchestrator/ test/plan-marshall/manage-config/` returns empty, which is why the rebase of 25 commits produced **zero conflicts**.

**Old→new pairing was established by PATCH CONTENT, not by subject.** `git range-diff 30835539..backup-pre-rebase origin/main..HEAD` paired all **25** commits `1:…=…:1` through `25:…=…:25` — every one an exact `=` match, **zero** dropped, zero altered. Subject-and-order matching would have been a guess; the range-diff is a measurement.

**Only citations proven stale were rewritten.** Each cited SHA was tested with `git merge-base --is-ancestor {sha} HEAD`:

- **3 stayed valid** and were left alone — `51d1c9bc`, `68a21cac`, `6939a0c2` are reachable from `origin/main`, so a rebase does not touch their object ids.
- **17 were proven stale** and rewritten to their paired replacements — **31 citations** across this report. A post-rewrite sweep for all 25 old SHAs across `doc/` returns **zero**.

⛔ **Two commit MESSAGES still cite stale SHAs, and this is disclosed rather than chased.** `afd77903` cites `c843a0f6`; `d43680a4` cites `eb49a7a6`. Both replacements exist (`f2f0013d`, `afd77903`), but a commit message cannot be corrected without another history rewrite, which would invalidate a fresh set of citations in turn. The lane's own rule applies: a stale SHA in an already-written commit message is accepted and disclosed. **The forward-looking rule it implies — do not quote a same-branch SHA in a commit message on a branch that may still be rebased — was violated by this run and is recorded as a lesson, not as a fix.**

**The branch form changed, and that is recorded because it is a deviation.** § Contract check records this run as harness-assigned; the rebase keeps that branch NAME (`claude/orchestrator-inbox-lifecycle-cleanup-kxrzew`), so session resumability is unaffected — what changed is the history under it, which required a force-push with lease.

## Reviewer participation

_pending_

## Cost

_pending_

## Contract check (Step 9)

_pending_

## What have we learned (Step 9)

_pending_

## Residue

Everything left open, with an owner. Five items are **pre-existing defects this run surfaced and deliberately did not fix** — each is outside the plan's scope, and widening the diff to take them would obscure what this plan is accountable for.

| # | Item | Why not fixed here | Where it should go |
|---|---|---|---|
| 1 | `cleanup.md`'s `## Output` block declares no field for a **deferred relocation**, though Step 8 instructs the orchestrator to "record that the judgement was deferred". | Pre-existing; the Output contract is not this plan's surface. Found by the third cold read, which could not execute the instruction. | A plan owning `cleanup.md`'s report contract |
| 2 | `applied[A]{spec,finding_class,source,destination}` cannot carry a relocated `epic.md` **section**, which has neither a `spec` nor a `finding_class` — yet Step 8 says every relocation is named in `applied[]`. | Same surface, same reason. | Same |
| 3 | Neither Rule 1 nor Rule 2 firing has any declared output field, so a migration is unreportable. | Same surface. This plan added the rules' *text*; the report contract they would emit into predates it. | Same |
| 4 | `build.py:376` and `:517` both cite a `real_marshal_json` xdist group as the exemplar. No such group exists anywhere in the tree — the name appears only in those two docstrings. | `build.py` is not on this plan's surface. | A build-tooling plan |
| 5 | `emit-landing.md:169` transcribes `merge_state` as `merged` / `open` / `n/a` while `landing-payload-spec.md` declares five values including `closed` and `unknown`. | Pre-existing and unchanged by this branch; flagged only because round 1 edited that file for an unrelated pointer. | The plan owning the producer contract (302's follower) |

**Operator obligations carried forward** (stated in full under § Proposals): 250/G4's physical archive migration, which needs a machine holding `.plan/local/`; and the 302/G5 + 302/G7 pair, which must land together.

**Residue of this run's own process:**

- **The shipped `cleanup.md` § Step 8 text has not been cold-read in its current form.** Three passes were run; rounds 4 and 5 then rewrote the passage again. A fourth pass is the obvious next check and was not performed.
- **The verification loop did not converge** (19 → 14 → 10 → 12 → 15). Round 5's recommendation, recorded but not acted on here, is to point any further round at the shipped marketplace text alone — `orchestration-model.md` § Dispatch Decision Rule and `cleanup.md` § Step 8 — since that is what consumers execute, and to leave the run report alone.
