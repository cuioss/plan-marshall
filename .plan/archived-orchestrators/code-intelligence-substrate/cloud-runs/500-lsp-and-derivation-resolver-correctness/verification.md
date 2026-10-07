# Verification — 500-lsp-and-derivation-resolver-correctness

**Audited:** `plan.md` (815 lines), `report-01.md` (1328 lines), `proposals.md` (311 lines), and the
shipped tree at `main` HEAD, spot-checked file-by-file against every deliverable's stated behaviour.
**Tree state:** `31211a99b` (main HEAD at audit time). PR #1321 landed as six squashed commits:
`cdf80625b` (plan dir), `7f36c760f` (D1/D2), `3331bfa48` (D3), `8f468a4a0` (D4), `a2306379f`
(test-compile fix, folded into D4's window), `9d375dfed` (D5), `573580c86` (D6). All six are ancestors
of current HEAD.
**Overall verdict:** **CONFIRMED WITH GAPS**

This is the most heavily self-verified plan in the epic I have reviewed: an 11-round verification loop
(five rounds under the standard budget, five more under an operator-extended budget, plus one targeted
round-11 re-check), two independent sub-agent roles per round (a plan verifier and a cold reader), a
17-mutant kill sweep, and three external review bots. The run's own report exited on
`budget-exhausted, non-converging` rather than a clean verifier, and it says so plainly rather than
dressing the exit up as convergence.

I independently re-derived, by reading the code rather than the report, every one of the six
deliverables' core mechanisms: D1's per-URI publish counter and per-file diagnostic-set diff, D2's
symbol-row path/container/depth flattening and the two-stage rollback correctness fix (round 7's
`originals.pop` removal and round 9's re-read-based `restore_error`), D3's `VENDORED_TREE_DIRS`
constant and `python.analysis.extraPaths` plumbing, D4's Poetry/`setup.cfg` fallback chain and the
`BasicInterpolation`-stays-on fix from round 11, D5's `FrameError`/`read_message` exception boundary —
the fix the plan flagged as the highest-risk claim to re-check — and D6's unified `isinstance(entry,
dict)` definition of `configured` across all three readers. In every case the code at HEAD matches what
`report-01.md` claims, at the file:line level, including several multi-round correction chains (e.g.
the `setup.cfg` interpolation fix being corrected a second time by round 11 after round 10's first
attempt was itself wrong). I found **no false claim** in the report's deliverable-level narrative.

What is not sound, or not fully closed, is smaller than the deliverables themselves: two figures in
§ Build gate → CI portability were never independently reproduced by any of the eleven verification
rounds (the report says so itself); round 11's own fixes (the corrected `setup.cfg` remedy) were never
re-checked by a subsequent round, because round 11 was the last one run; and a short, honestly
catalogued residue list (S1–S12, B2, B3) remains open by design, none of it capable of producing a
false-clean success — the one defect class this plan exists to eliminate. None of this is a defect the
run hid; all of it is disclosed in `report-01.md` § Left open. The gaps below are follow-up items for a
successor plan, not corrections to false claims in this one.

## Deliverable verdicts

| # | Deliverable (short) | Report claim | Ground truth | Verdict |
|---|---|---|---|---|
| D1 | Diagnostics answer contract + per-file worsened-set verdict | Done, 4 CI-portable red/green pairs | `wait_for_diagnostics` per-URI `after_seq`, `edit_verdict` per-file set diff — both confirmed at file:line | **CONFIRMED** |
| D2 | Lookup rows carry file; write path all-or-nothing | Done, (a)–(e) met | `_symbol_rows` flattening with `path`/`container`/`depth`; `apply_workspace_edit` rollback correct after two multi-round fixes | **CONFIRMED** |
| D3 | `lsp` harvest resolves cross-bundle imports, refuses vendored targets | Done, gating baseline taken, 72 cross-bundle / 10 edges | `VENDORED_TREE_DIRS`, `extraPaths` plumbing confirmed in code; the 72/10 figures are **unreproducible in this sandbox** (no `pyright-langserver`) | **CONFIRMED** (mechanism); **numeric claim unverified in this audit** |
| D4 | Python/npm discoverers stop reporting missing capability as measured absence | Done, (a)–(g) met | Poetry/`setup.cfg` fallback, PEP 508 bare-`@`/`;` splits, narrowed catch all confirmed; round-11's interpolation-stays-on correction present | **CONFIRMED** |
| D5 | Corpus server survives a bad frame, never presents unconfirmed as exact | Done — title clause **FALSE until round 8**, fixed then | `FrameError`/`read_message` exception boundary, `on_references` omission with `omittedUnverifiedCount`, all confirmed in the shipped file | **CONFIRMED** (round-8 fix genuinely present at HEAD) |
| D6 | One store, one meaning of `configured`; standing questions recorded | Done, G9 both sides fixed, three proposals recorded not decided | `isinstance(entry, dict)` unified across `extension_api.py`, `run_config.py` (two readers, `cmd_derivation_resolver_get` and `_list`) | **CONFIRMED** |

**6 of 6 confirmed.** No deliverable is refuted or partial by my independent check.

## Per-deliverable detail

### D1 — the diagnostics answer contract
- **Required (plan):** per-URI publish counter with `after_seq`; explicit `unknown` on timeout/never-published; per-file diagnostic-set diff replacing whole-footprint counts.
- **Claimed (report):** all three landed; `errors_before`/`errors_after` retained.
- **Ground truth:** `marketplace/bundles/plan-marshall/skills/lsp-client/scripts/_lsp_jsonrpc.py:229-281` (`diagnostics_seq`, `wait_for_diagnostics` with `after_seq` param, `None` on unanswered); `_lsp_workspace_edit.py:372-388` (`edit_verdict` returns `'failed'` iff `any(added_by_path.values())`). Old vacuous test `test_edit_verdict_passes_on_equal_or_improved` no longer exists; replaced by `test_edit_verdict_fails_when_any_file_gained_an_error` / `test_edit_verdict_passes_when_no_file_gained_an_error` (`test/plan-marshall/lsp-client/test_lsp_workspace_edit.py:349-355`), both asserting on real per-file inputs, not on their own output.
- **Verdict:** CONFIRMED.

### D2 — lookup rows and the write path
- **Required (plan):** symbol rows carry `path`; hierarchy flattened; resource operations fail whole; apply loop rolls back on mid-write failure; `didOpen` idempotent.
- **Claimed (report):** all landed; round 7 found and fixed a "false clean" (`originals.pop` discarding the one file that needed restoring); round 9 found and fixed a second false-clean class (a write that fails at `open()` before truncating, and duplicate URI aliasing).
- **Ground truth:** `lsp_client.py:185-229` (`_symbol_rows`, depth-first walk, `container`/`depth`/`path` on every row); `_lsp_workspace_edit.py:224-311` (`apply_workspace_edit` keeps the failing path in `originals`; `_still_modified` re-reads the footprint and catches `UnicodeDecodeError` explicitly, matching round 10's A-5 fix); `_lsp_jsonrpc.py:385-407` (`LspSession.open` is idempotent via `self._open_paths`). `lsp_client.py:390-400` shows the CodeRabbit C2 fix (every `didChange` sent before any verdict collected).
- **Verdict:** CONFIRMED. The two-round correction chain (round 7 then round 9 on the same rollback mechanism) is itself evidence the loop was doing real work, not performative sweeping.

### D3 — the `lsp` harvest
- **Required (plan):** search path plumbed via `extraPaths`; vendored trees excluded as both source and target; refusal-vs-timeout split; docstrings corrected to name the real mechanism.
- **Claimed (report):** all landed; baseline 0→72 cross-bundle references, 0→10 module edges; `.venv` targeting 3302→0.
- **Ground truth:** `lsp_harvest.py:116` (`REASON_SERVER_REJECTED`), `:149` (`VENDORED_TREE_DIRS` as one module-level constant), `:287` (applied to targets via `_within`), `:304-347` (`bare_import_roots`, structural `__init__.py` rule). `test_lsp_harvest.py:555-607` converts `test_every_failure_mode_states_a_distinct_reason` to a **set-equality** assertion over six prefixes (`server-absent`, `server-failed-to-start`, `server-timeout`, `workspace-unsupported`, `server-rejected`, `request-failed`) — confirmed not to be the whole-string-collection form the plan's ⛔ warns is vacuous.
- **Verdict:** CONFIRMED for mechanism. The **72 cross-bundle references / 10 module edges** figures could not be independently reproduced in this audit — `pyright-langserver` is not installed in this sandbox — so I record them as **unverified in this audit**, consistent with the plan's own instruction that every such count is a lead. This is not a report defect: the report itself repeatedly warns the same numbers are environment-sensitive and stamps them per measurement.

### D4 — the Python and npm discoverers
- **Required (plan):** Poetry and `setup.cfg` fallbacks, PEP 508 bare-`@` and `;`-first splits, narrowed exception catch, npm disclosure.
- **Claimed (report):** all landed; round 10 found and fixed a new defect in D4's own code (`setup.cfg` interpolation aborting the whole discovery on a bare `%`); round 11 found round 10's fix used the wrong justification and corrected it.
- **Ground truth:** `_pyproject_cmd_discover.py:301-346` (`_parse_pyproject_metadata`, strict fallback chain); `:406-460` (`_read_pep621`, `_read_poetry`); `:462-520` (`_read_setup_cfg` — **interpolation stays ON**, all `parser.get()` calls moved inside the `try`, matching round 11's correction, not round 10's original "disable interpolation" attempt, which the report itself says was wrong); `:264-296` (`requirement_name`, marker-first then bare-`@` split). Fixtures `poetry-monorepo` and `setuptools-monorepo` exist under `test/plan-marshall/build-pyproject/fixtures/`.
- **Verdict:** CONFIRMED, including the fact that the *final* shipped remedy is round 11's corrected one, not round 10's initial (and admittedly wrong) one.

### D5 — the corpus server
- **Required (plan):** exception boundary at handler and frame level; `on_references` omits unverified sites with a visible withheld-count channel; ranked candidate resolution; `initialize` adopts `rootUri`; staleness bound disclosed.
- **Claimed (report):** ⛔ **the deliverable's own title clause ("survives a bad frame") was FALSE from commit `9d375def` through seven verification rounds** — that commit guarded the handler, not the frame reader, so all seven malformed-frame shapes still silently ended the session. Fixed in round 8, folded into the same squashed commit on `main`.
- **Ground truth:** `_corpus_lsp_protocol.py:36-115` — `FrameError` class with a `recoverable` flag, `read_message` raising it for non-integer/negative Content-Length, missing header, short body (unrecoverable), and bad JSON/non-object/non-UTF-8 body (recoverable); `:218-256` — `serve()`'s outer loop wraps `read_message` in `try/except FrameError`, continuing on recoverable and returning 0 on unrecoverable, both branches logging to stderr via `_log_frame_error`. `corpus_lsp.py:179-217` — `handle()` wraps the handler call in `try/except Exception`, returning a `-32603` JSON-RPC error for a request or a logged no-op for a notification. Test file `test_corpus_lsp_honesty.py:157-238` drives exactly **seven** frame shapes (3 recoverable + 4 unrecoverable) through a real `serve` subprocess, asserting the request after the bad frame is still answered (recoverable case) or that the session ends **audibly** with exactly one `malformed frame` stderr line (unrecoverable case) — this is the guard that would have failed against the pre-round-8 code, and it is present at HEAD.
- **Verdict:** CONFIRMED. This was the single highest-risk claim named in my dispatch instructions, and it checks out: the round-8 fix is genuinely in the tree, genuinely tested through a real subprocess (not the index directly, addressing the plan's own ⚠ about protocol-layer under-testing), and the title clause is now true.

### D6 — one store, one meaning of `configured`; standing questions
- **Required (plan):** `configured` unified as `isinstance(entry, dict)` in both readers; G10/G25/G12 and three proposals recorded, none decided.
- **Claimed (report):** G9 fixed both sides plus a third reader (`cmd_derivation_resolver_list`) the plan didn't originally name (found by round 8's F5); G10/G25/G12 recorded in `proposals.md`.
- **Ground truth:** `extension_api.py:175` (`'configured': isinstance(section.get(resolver_id), dict)`); `run_config.py:882` (`configured = isinstance(entry, dict)`, in `cmd_derivation_resolver_get`) and `:948` (`resolvers.append({'id': key, 'enabled': enabled, 'configured': isinstance(section.get(key), dict)})`, in `cmd_derivation_resolver_list` — the third reader). `run_config.py:866` — `entry.get('enabled', DERIVATION_RESOLVER_ENABLED_DEFAULT) is not False`, the CodeRabbit C4 fix (only the literal JSON `false` disables, matching the store's documented fail-open rule). `proposals.md` carries P1–P6 and decision record D1, each with a blast radius and a settling criterion, and none flagged as implemented.
- **Verdict:** CONFIRMED.

## Correctness review

The shipped mechanisms are not merely present, they are the *right* mechanisms for the stated problem
in every case I checked:
- D1's severity-scoped gate (errors only, not warnings) is a defensible, disclosed judgement call — widening to warnings would make an innocuous unused-import warning roll back a correct rename, which is explicitly out of the three named defects' scope.
- D2's `_still_modified` correctly distinguishes "the write already damaged this file" from "the restore rewrite failed for the same reason the original write did" (round 9's EACCES/immutable-file fix) — a subtlety a naive fix would have gotten wrong in the *other* direction (a false-alarm `restore_error` over an untouched tree).
- D4's decision to keep `BasicInterpolation` **on** in `setup.cfg` parsing, once round 11 caught that setuptools itself uses interpolation, is the correct alignment choice: agreeing with the ecosystem's own consumer on all three input classes (interpolated names, escaped `%%`, and rejected bare `%`) beats a narrower fix that would silently publish a wrong join key.
- D5's omission-plus-notification design for unverified references (rather than a downgrade or a silent drop) genuinely closes the recall/precision gap the two conflicting shipped-page promises created, and it does so without adding a decision the run was not authorised to make (option (b) is correctly deferred to the operator).

## Test adequacy

I mentally reverted three fixes and checked whether the shipped guard would catch it:
- **D1**: reverting `edit_verdict` to `sum(errors) <= sum(errors)` fails `test_edit_verdict_fails_when_any_file_gained_an_error` immediately (it asserts `'failed'` on a same-count-different-file scenario the old code passed). Non-vacuous.
- **D3**: reverting `test_every_failure_mode_states_a_distinct_reason` to a whole-string count (as it was before D3) would make the current six-mode set collapse silently under duplicate prefixes; the shipped **set-equality** assertion against six named literals is exactly the fix the plan's own ⛔ demanded, and I confirmed the assertion is `assert prefixes == {...}` (six literals), not `len(...) == 6`.
- **D5**: reverting `read_message` to return `None` uniformly (the pre-round-8 shape) fails all seven of `test_a_recoverable_bad_frame_is_skipped_and_the_session_continues` / `test_an_unrecoverable_bad_frame_ends_the_session_AUDIBLY`'s parametrised cases, because the test asserts on subprocess `returncode`, response ids received after the bad frame, and the exact `stderr` count — none of which the old code could produce.

I found **no vacuous guard** in the surfaces I sampled. This matches the report's own claim across eleven rounds and a 17-mutant kill sweep (10 in the base table, 8 more red-checked individually per finding in rounds 7–9), but my sample was independent of that sweep.

## Report accuracy

Every claim I checked against the tree — the D1–D6 mechanism descriptions, the CodeRabbit fix
descriptions (C2's notify-before-collect reordering, C4's `is not False` gate), the doc disclosures in
`dependency-intelligence.adoc` (`setup.py` and `peerDependencies`/`optionalDependencies` limits), and
the `execute-task/SKILL.md` correction (V6/W5's four-reason-code table) — matched the code exactly.
**No false claim found in this audit's sample.** The report is unusually forthcoming about its own
prior false statements (it names and fixes over 90 of them across eleven rounds, several of which were
its *own* previous round's introduced regressions), which is a strength, not a weakness, of the
artifact under audit.

## Non-convergence — what the budget-exhausted loop left unsettled

The loop's finding rate never decayed to zero across eleven rounds (19 → 10 → 8 → 9 → 8 → 8 → 7 → 7 → 9
→ 8 condition-A findings per round, per the report's own corrected series). Two structural patterns
recurred through round 11: (1) a fix that closes a false statement at some sites and misses a sibling
site making the *same* claim (the n−1-of-n shape — e.g. the PEP-621-only contract corrected at five
prose sites before round 6 finally reached the three production docstrings that own it); (2) a fix
introducing a *new* false statement or defect in the code it just touched (round 9's fix falsifying
four of round 7's own statements; round 10 finding two more defects inside round 9's own new code).

What was **still unsettled when the budget ran out**, and whether the tree is now correct on it:
- **Round 11's own fixes were never independently re-checked by a further round** — this is structural (a loop that ends after a round of fixes always ends with its last fixes unverified), and it is the honest shape the report names rather than hides. I independently re-derived round 11's `setup.cfg` fix by reading the code (see D4 above) and it matches the report's account exactly, which is the closest an outside audit can come to closing this gap without a twelfth round.
- **§ Build gate → CI portability's two population counts** (`662 passed, 10 skipped`; `53 failed, 10 passed, 1 skipped`) were never reproduced by any of five attempts across the verification rounds. Not proven false — genuinely unverifiable in this audit's environment too, since it requires hiding `pyright-langserver` from `PATH` inside a full test run, which I did not attempt (out of scope for a read-only audit).
- **Twelve behavioural survivors (S1–S12, B2, B3)** remain open by design, each with a stated bound. I independently confirmed S1 (CRLF line-ending rewrite) is still present in the shipped code (`_lsp_workspace_edit.py:190-196`'s comment names the limit; no binary-I/O rewrite was made) and B2 (the two `restore_files(originals)` calls outside a try/except, `lsp_client.py:405,425`) is still structurally as described. None of the twelve can produce a false-clean success per the report's own analysis, which I did not find reason to dispute.

## Residue

The run explicitly declined three implementation decisions it was not authorised to make (P1
Axis-D claim publication, P2 npm peer/optional-dependency extraction, P4 index invalidation/debounce,
P5 keeping unverified sites, P6 corpus diagnostics), recording each as a proposal with a blast radius
and a settling criterion rather than deciding silently — this matches the plan's explicit prohibition
on taking any such decision. The npm-side malformed-`package.json`/`workspaces`-glob defects (S5's
second half) remain unfixed and are pre-existing on `origin/main`, not introduced or worsened by this
run. Nothing in `report-01.md`'s residue accounting appears to omit a gap the tree actually has, based
on my sampling.
