# Gaps — 010-lsp-in-execute-lookup-and-write

The plan landed: the `lsp-client` skill exists, all four verbs work against a real language server,
the coverage contract and the worsened-edit guard are both non-vacuous under mutation, and the opt-in
degradation is byte-identical for an unconfigured project. What remains is fifteen concrete defects
found by reading the shipped code and then proving them by execution against a live
`pyright-langserver`: three correctness holes that defeat a deliverable's stated purpose (a
`workspace-symbol` result carries no file path; `document-symbol` returns 1 of 43 symbols and reports
that as a complete answer; the post-edit diagnostics re-run reads the *pre-edit* set and passes a
broken edit), one more that reports an unanswered diagnostics query as a clean file, four
incompletenesses in the write path, one test gap against D2's literal done-condition, and five
documentation / report defects.

`G1`, `G2`, `G5` and `G13` share one owning surface and one fix window: they are all in
`lsp-client/scripts/`, and `G2` + `G13` are two faces of the same `wait_for_diagnostics` return
contract. A later run should take them as one change, not four.

## G1 — Emit the file path on every `workspace-symbol` and `document-symbol` row

- **Kind:** bug
- **Severity:** high
- **Topic:** lsp/resolvers
- **Where:** `marketplace/bundles/plan-marshall/skills/lsp-client/scripts/lsp_client.py:147-162`
  (`_symbol_rows`), reached from `:180-181` (`workspace-symbol` branch)
- **Evidence:** live probe against `pyright-langserver` over a two-file project
  (`alpha.py` defining `class Widget`, `beta.py` importing it), calling the shipped
  `_run_lookup(..., 'workspace-symbol', ..., 'Widget')`:
  `"locations": [{"name": "Widget", "kind": 5, "line": 0, "character": 6}]` — `path keys present: False`.
  The same probe dumped pyright's raw response in the same session: it carries
  `location.uri = "file:///…/alpha.py"`. The path is **supplied by the server and discarded by the
  client** — `_symbol_rows` reads `location` at `:152-154` only to take the `range`. Control taken in
  the same session: `references` rows come back with keys
  `{character, end_character, end_line, line, path}`, because the sibling helper `_location_rows`
  (`:122-144`) emits `path` via `uri_to_path`. Reproduced independently twice.
- **Why it matters:** `workspace-symbol` is the only lookup kind that spans files. Without a file
  path the answer is unusable — a leaf that asks "where is `Widget`?" gets a line number with no file
  and must fall back to `Grep`/`Read`, which is precisely the byte cost D1 exists to remove. D1's
  *Done when* ("a leaf obtains a symbol's **locations**") is not satisfied for this kind.
- **Action:** in `_symbol_rows`, take `uri_to_path(location['uri'])` when a `location` is present and
  add a `path` key to the row; for `document-symbol` (no `location` in a hierarchical response) pass
  the queried file's resolved path into the helper so every row carries `path`. Neither
  `lsp-client/SKILL.md` § Scripts nor the user page's capability table documents a row shape today, so
  this is an addition to both, not a correction: state the `locations[]` row keys once, in
  `lsp-client/SKILL.md` § Scripts, and have the user page's "Locate by coordinate" row say the
  coordinates include the file.
- **Done when:** a `lookup --kind workspace-symbol` payload's `locations[]` rows each carry a `path`
  equal to the defining file, asserted by a real-server test over a two-module sample project in which
  the symbol is defined in a module the call never opens (`workspace-symbol` opens no file at all), and
  asserting `row['path'] == str(that_module.resolve())` rather than merely that a `path` key exists.
- **Effort:** S
- **Risk if fixed:** none to existing consumers — the change is additive to the row shape; the only
  care needed is that `document-symbol` rows keep the same key set as `workspace-symbol` rows.

## G2 — Make the post-edit re-diagnose wait for a publish newer than the edit

- **Kind:** bug
- **Severity:** high
- **Topic:** lsp/resolvers
- **Where:** `marketplace/bundles/plan-marshall/skills/lsp-client/scripts/_lsp_jsonrpc.py:204-223`
  (`wait_for_diagnostics`), consumed by `lsp_client.py:239-247` (`_run_edit`'s `errors_after` loop)
- **Evidence:** the wait breaks as soon as the inbound stream has been quiet for `settle` (2.0 s) and
  the URI has *any* cached entry (`:220`) — including the entry cached during the `errors_before` loop.

  Reproduced **against a live `pyright-langserver`**, not a stand-in. The probe replays `_run_edit`'s
  exact sequence (`open` → `diagnostics` → write the broken content to disk, as
  `apply_workspace_edit` would → `change_to_disk` → `diagnostics` → `edit_verdict`) over a generated
  12,003-line module whose re-analysis pyright cannot finish inside the settle window:

  ```
  diagnostics() #1 returned in 11349 ms -> 0 entries   [uri_in_cache=True  diag_seq=1]
  <broken content written to disk; change_to_disk sent>
  diagnostics() #2 returned in  2017 ms -> 0 entries   [uri_in_cache=True  diag_seq=1]
  errors_before=0  errors_after=0  verdict=success     <-- FAIL-OPEN (stale read)
  TRUTH after extra wait: 1 error(s)
  ```

  `diag_seq` is the transport's own count of `publishDiagnostics` frames received. It is **identical**
  either side of the edit, so no new publish arrived and `wait_for_diagnostics` returned the entry
  cached before the edit, at the 2 s floor. Repeated at 24,003 lines with the same outcome; at 483
  lines the guard verdicts `failed` correctly. The failure is therefore not hypothetical and not
  fake-server-specific — it is the real server being slower than the window, and the guard fails
  **open**, not closed.

  The module docstring already claims the correct behaviour and the code does not implement it
  (`_lsp_jsonrpc.py:14-15`: *"`publishDiagnostics` tracked per URI so a post-edit re-diagnose can wait
  for the **next** push"*).
- **Why it matters:** this is D2's central guard. On any republish slower than 2 s — a large file, a
  cold analysis, a loaded machine — a rename that breaks the parse is compared against its own
  pre-edit diagnostics, `edit_verdict` returns `success`, no rollback happens, and the verb reports
  `status: success, applied: true`. "An edit nobody read is at minimum an edit the parser re-checked"
  silently becomes "an edit nobody read". Nothing in CI would catch a regression here either: mutating
  `wait_for_diagnostics` to `return list(self._diagnostics.get(uri, []))` — deleting the settle
  window, the freshness loop and the timeout outright — leaves the suite at **31 passed, 5 skipped**
  on a runner without pyright.
- **Action:** track a per-URI publish counter (not just the global `_diag_seq`) and give
  `wait_for_diagnostics` an `after_seq` / `min_seq` parameter; have `LspSession.change_to_disk` capture
  the URI's current counter and `LspSession.diagnostics` wait for a counter strictly greater than it.
  On timeout with no newer publish, return an explicit *unknown* rather than the cached set, and make
  `_run_edit` treat unknown as a failure-to-verify (roll back, `reason: diagnostics_unavailable`) —
  never as a pass.
- **Done when:** a **CI-portable** test (fake server subprocess over the real `StdioTransport`, in the
  shape of `test_lsp_transport.py`, so it does not skip without pyright) drives a server whose
  post-`didChange` publish arrives after the settle window, and asserts that `_run_edit` returns
  `status: failed` with the target file byte-identical to its pre-edit content — not `success`. The
  same test must go red when `wait_for_diagnostics` is reverted to the current logic (state that check
  as run, with the observed failure, in the fixing run's report).
- **Effort:** M
- **Risk if fixed:** a server that does not republish after `didChange` (or publishes only on error)
  would newly hit the unknown path and fail edits that previously passed; the timeout and the
  fail-closed choice need to be documented in `lsp-client/SKILL.md` so a leaf reads a
  `diagnostics_unavailable` rejection as "verify by build", not as "the edit was wrong".

## G3 — Surface a `WorkspaceEdit`'s unapplied resource operations in the payload

- **Kind:** incomplete
- **Severity:** medium
- **Topic:** lsp/resolvers
- **Where:** `marketplace/bundles/plan-marshall/skills/lsp-client/scripts/_lsp_workspace_edit.py:97`
  and `:149` (`changes, _notes = normalize_changes(...)`), and `lsp_client.py:207-275` (`_run_edit`,
  which has no notes field)
- **Evidence:** `normalize_changes` builds `notes` for each dropped create/rename/delete file
  operation (`_lsp_workspace_edit.py:71-74`) and the module comment promises they are "surfaced in
  notes rather than silently dropped" (`:36-39`). Both callers bind them to `_notes` and discard them.
  `grep -n "notes"` over `lsp_client.py`, `lsp-client/SKILL.md` and
  `doc/user/lsp-code-intelligence.adoc` returns nothing (control: 8 hits in `_lsp_workspace_edit.py`).
- **Why it matters:** an edit that includes a resource operation is applied *partially* and reported as
  `status: success, applied: true` with a footprint that omits the dropped part. That is exactly the
  under-declared change footprint the plan named as the recurring defect D2 must ship a fix for
  ("the captured file list matches the edit"). A consumer records a footprint that is not the edit.
- **Action:** return the notes from `capture_footprint` / `apply_workspace_edit` (or expose a
  `normalize_changes`-based check), add `notes[]` and an `unapplied_operation_count` to the `edit`
  payload, and make a non-empty resource-operation set **fail the verb** (`reason:
  unsupported_resource_operation`) rather than apply the text-edit remainder.
- **Done when:** `cmd_edit` given a `WorkspaceEdit` containing a `kind: rename` document change
  returns a non-success payload naming the unapplied operation, and no file on disk was modified;
  asserted by a fake-transport test.
- **Effort:** S
- **Risk if fixed:** a server that emits a benign resource op alongside a valid text edit would now be
  rejected instead of partially applied — the safer failure, but it changes the outcome for such
  servers and should be noted in the skill's write-side section.

## G4 — Roll back a partially applied `WorkspaceEdit` when a write fails mid-apply

- **Kind:** bug
- **Severity:** medium
- **Topic:** lsp/resolvers
- **Where:** `marketplace/bundles/plan-marshall/skills/lsp-client/scripts/_lsp_workspace_edit.py:141-158`
  (`apply_workspace_edit`), called unguarded at `lsp_client.py:235`
- **Evidence:** the apply loop reads and writes each file with no `try`/`except`; `_with_session`
  (`lsp_client.py:350-364`) catches only spawn-time `LspError`/`OSError`, and its `finally` closes the
  session without restoring anything. An exception raised on the second of three files therefore
  escapes to `safe_main`, which renders `status: error` and exits 1
  (`tools-file-ops/scripts/file_ops.py:1664-1695`) — with file one already rewritten, `originals`
  discarded, and no footprint in the output.
- **Why it matters:** the write side's whole safety argument is that a failed edit leaves no trace.
  A half-applied multi-file rename is the worst outcome available: the tree is inconsistent, the
  consumer has no footprint to act on, and the error payload does not say which files changed.
- **Action:** wrap the apply loop so a failure restores every file already written (reuse
  `restore_files(originals)`), then re-raise or return a `status: failed` payload carrying
  `reason: apply_failed`, the offending path, and the partial footprint that was rolled back.
- **Done when:** a test making the second file of a three-file edit unwritable (e.g. `chmod 0444` or a
  patched `write_text`) asserts every file is byte-identical to its pre-edit content afterwards and
  the payload names the failure.
- **Effort:** S
- **Risk if fixed:** the restore itself can fail (read-only directory); that second-order failure must
  be reported rather than swallowed, or the payload will again overstate what happened.

## G5 — Recurse into `children` when flattening `documentSymbol` results

- **Kind:** incomplete
- **Severity:** medium
- **Topic:** lsp/resolvers
- **Where:** `marketplace/bundles/plan-marshall/skills/lsp-client/scripts/lsp_client.py:147-162`
  (`_symbol_rows`); the capability is advertised at `_lsp_jsonrpc.py:290`
  (`'documentSymbol': {'hierarchicalDocumentSymbolSupport': True}`)
- **Evidence:** live probe over a file containing `class Widget` with methods `spin` and `stop` plus a
  module-level `top_level`: the shipped payload's names are `['Widget', 'top_level']` — the two methods
  are absent, because pyright returns them nested under `Widget.children` and `_symbol_rows` iterates
  the top level only.
- **Why it matters:** most work in this repository targets a method, not a module-level function.
  A leaf asking for a file's symbols to locate `ClassName.method` gets the class's line and must read
  the file anyway — D1's byte saving evaporates for the common case.
- **Action:** flatten the hierarchy depth-first in `_symbol_rows`, carrying a `container` (parent name)
  or a dotted `name` and a `depth` so the caller can tell a method from a top-level function; keep the
  existing keys so current consumers are unaffected.
- **Done when:** a real-server test over a file with a class asserts that a method's name and line are
  present in `lookup --kind document-symbol` output.
- **Effort:** S
- **Risk if fixed:** payload size grows for large files — worth a documented cap or an explicit
  `--max-symbols`, since the point of the verb is to be cheaper than reading the file.

## G6 — Test a genuinely multi-file rename through the `edit` verb

- **Kind:** test-gap
- **Severity:** medium
- **Topic:** tests
- **Where:** `test/plan-marshall/lsp-client/test_lsp_integration.py:95-106`
  (`test_real_clean_rename_edit`, asserts `file_count == 1`) and
  `test/plan-marshall/lsp-client/test_lsp_client.py:186-215` (both `_run_edit` tests use a
  single-file `WorkspaceEdit`)
- **Evidence:** D2's *Done when* reads "**a multi-file rename** lands through the recorded
  footprint-capturing path, the captured file list matches the edit". The only two-file exercise in the
  suite, `test_apply_and_restore_round_trip` (`test_lsp_workspace_edit.py:107-123`), calls the pure
  helper directly and never touches `_run_edit`, `cmd_edit`, the pre/post diagnostics loops, or the
  footprint that ends up in the payload.
- **Why it matters:** the multi-file path is the one that carries the risk the plan names — a mutation
  nothing read spanning many files. It is also where the per-file loops in `_run_edit` (open each,
  count before; `change_to_disk` each, count after) could be wrong in a way a single-file test cannot
  reveal.
- **Action:** add a real-server test whose sample project defines a symbol in one module and uses it in
  another, rename it through `cmd_edit`, and assert `file_count == 2`, that `files[]` equals the two
  file paths, that both files on disk changed, and that no third file was touched. Add the fake-transport
  mirror for the failure direction (worsened diagnostics over a two-file footprint roll **both** files
  back).
- **Done when:** both tests exist and pass, and the real-server one asserts `file_count == 2` with the
  paths matching the `WorkspaceEdit`.
- **Effort:** S
- **Risk if fixed:** the real-server test is `skipif`-guarded on pyright like its siblings, so CI
  portability is unchanged; expect a few seconds of added runtime.

## G7 — Document the real per-call cost, not the warm-path latencies

- **Kind:** doc-defect
- **Severity:** medium
- **Topic:** documentation-surface
- **Where:** `marketplace/bundles/plan-marshall/skills/lsp-client/SKILL.md:19-24` ("cold start is paid
  once per call, and the natural unit is a per-call batch") and `doc/user/lsp-code-intelligence.adoc`
  (no cost statement at all); the underlying figures are `report-01.md:20-33`
- **Evidence:** re-measured against a live `pyright-langserver` with the workspace scoped to
  `manage-architecture`, exactly as the report's measurement was:

  | Operation | quiet box | loaded box | report |
  |---|---|---|---|
  | cold start (spawn + `initialize`) | 571 ms | 2140 ms | 413 ms |
  | **first** `documentSymbol` after `didOpen` | **4873 ms** | **13384 ms** | 2.7 ms |
  | same call repeated in the session | 4.2 ms | — | 2.7 ms |

  The report's per-call figures are warm-path: its sequence issued `workspace/symbol` and diagnostics
  first, so the analysis wait had already been paid. In addition `workspace_symbol` calls
  `wait_until_idle` with a 1.5 s settle floor (`_lsp_jsonrpc.py:225-243`, invoked at `:349`) and
  `diagnostics` a 2 s settle floor (`:204`) — my `diagnose` re-measurement returned in exactly 2000 ms.
- **Why it matters:** the hosting decision ("cold start ~0.4 s makes per-call boot cheap") and any
  operator's expectation are set from figures that exclude the wait every per-call invocation must pay.
  A one-shot lookup costs seconds, not milliseconds — which is the difference between "cheaper than a
  `Read`" and "not". Sizing this capability against the wrong number is how it gets adopted where it
  loses.
- **Action:** state the cost profile in `lsp-client/SKILL.md` and the user page: cold start, plus a
  first-query analysis wait of seconds on a cold workspace, plus the fixed settle floors for
  `workspace-symbol` and `diagnose`; and recommend batching several lookups into one invocation, which
  is the only way the per-call model amortises. Do not restate the report's table as if it were the
  per-call cost.
- **Done when:** both surfaces name a cold-path figure and the settle floors, and neither presents the
  warm per-call latencies as the cost of a single invocation.
- **Effort:** S
- **Risk if fixed:** an honest cost statement may discourage adoption for single lookups — which is the
  correct outcome, but it should be paired with the batching guidance so the capability is not read as
  useless.

## G8 — Correct the "every payload carries `boundary_note`" claim

- **Kind:** doc-defect
- **Severity:** low
- **Topic:** bundle-docs
- **Where:** `marketplace/bundles/plan-marshall/skills/lsp-client/SKILL.md:92`; the same wording is in
  `report-01.md:58`
- **Evidence:** `boundary_note` is set only in the success payload of `_run_diagnose`
  (`lsp_client.py:301`). A `diagnose` call on an unconfigured or unreachable project returns
  `_degraded(...)` (`:109-119` via `:389-392`), which has no `boundary_note` key. The module docstring
  states the true scope — "carried in every **diagnose** payload" (`:60-62`) — but even that is
  imprecise for the degraded case.
- **Why it matters:** a consumer told that the key is always present may key off it (e.g. "if
  `boundary_note` is missing, this is not a diagnose result") and mis-route a degraded return.
- **Action:** reword to "every payload a running server produced", or add the note to the degraded
  diagnose payload as well (cheaper and makes the docs true as written).
- **Done when:** the SKILL sentence matches the code, and a test asserts whichever invariant was chosen.
- **Effort:** S
- **Risk if fixed:** none.

## G9 — State the re-diagnose's scope limits in the write-side contract

- **Kind:** doc-defect
- **Severity:** low
- **Topic:** bundle-docs
- **Where:** `marketplace/bundles/plan-marshall/skills/lsp-client/SKILL.md:71-86` (§ "The write side")
  and `doc/user/lsp-code-intelligence.adoc:82-90`
- **Evidence:** the verification is scoped to the footprint files (`lsp_client.py:229-246` iterates
  `paths` only) and to severity `Error` (`_lsp_workspace_edit.py:167-169`,
  `DIAGNOSTIC_SEVERITY_ERROR = 1`), with `diagnosticMode: openFilesOnly`
  (`_lsp_jsonrpc.py:57-68`). Neither document says so; both read as "the parser re-checked the change".
- **Why it matters:** a rename can break a file the server did not include in the edit (a string
  reference, a dynamic import, a file outside the analysed set) and the step still passes. A reader who
  believes the check is workspace-wide will skip a build they should have run — the same
  over-reading D3's boundary note exists to prevent, one level down.
- **Action:** add one sentence to both surfaces: the re-diagnose covers exactly the edited files and
  counts only `Error`-severity diagnostics; breakage elsewhere is caught by the build, not here.
- **Done when:** both documents state the scope and the severity limit.
- **Effort:** S
- **Risk if fixed:** none.

## G10 — Add `ready` to the user page's state table

- **Kind:** doc-defect
- **Severity:** low
- **Topic:** documentation-surface
- **Where:** `doc/user/lsp-code-intelligence.adoc:62-78` ("The three states you can always tell apart")
- **Evidence:** the table lists `not_configured` / `unreachable` / `ok`. `preflight` returns a fourth
  state, `ready` (`lsp_client.py:58`, `:341-347`), and it is what the consumer wiring gates on
  (`execute-task/SKILL.md:242`: "`preflight` returns `state: ready`"). `lsp-client/SKILL.md:66-69`
  documents the distinction; the operator page does not.
- **Why it matters:** an operator debugging their configuration from the user page sees a `ready` they
  were told does not exist, and cannot tell whether it is healthy.
- **Action:** add a `ready` row (or a one-line note under the table) saying `preflight` names the
  healthy precondition `ready` while a run verb names its executed outcome `ok`.
- **Done when:** the user page mentions `ready` and matches `lsp-client/SKILL.md`.
- **Effort:** S
- **Risk if fixed:** none.

## G11 — Retract the report's "sync owed" note

- **Kind:** report-defect
- **Severity:** low
- **Topic:** plan-lane-contract
- **Where:** `doc/plans/code-intelligence-substrate/010-lsp-in-execute-lookup-and-write/report-01.md:61`
  and `:127`
- **Evidence:** both lines record a local `/sync-plugin-cache` as owed for the `marketplace/bundles/**`
  edits. `CLAUDE.md` § Standalone Plan Lane now states that Plugin Cache Sync is inert in the lane and
  that a lane plan editing `marketplace/bundles/` "**neither performs a sync nor records one as owed**
  — the merged bundle source is authoritative".
- **Why it matters:** a reader reconciling residue across this epic's reports will chase a debt that
  the contract says does not exist, and may treat other reports' silence on it as an omission.
- **Action:** replace both notes with a one-line statement that the lane does not carry a cache-sync
  debt, citing the CLAUDE.md rule. (Report text is a dated record; annotate rather than rewrite
  history if the epic's convention prefers that.)
- **Done when:** `report-01.md` no longer records an owed sync, or records it as superseded.
- **Effort:** S
- **Risk if fixed:** none.

## G12 — Register `lsp-client` in the bundle manifest's `skills[]`

- **Kind:** omission
- **Severity:** low
- **Topic:** bundle-docs
- **Where:** `marketplace/bundles/plan-marshall/.claude-plugin/plugin.json` (`skills` array)
- **Evidence:** re-derived at audit time — the array lists **76** entries while
  `marketplace/bundles/plan-marshall/skills/` holds **78** directories; the two absent are
  `lsp-client` and `recipe-surgical-fix` (the latter belongs to another plan). No runtime consequence
  today: the Claude target regenerates the manifest with `skills: []` on purpose, because a declared
  array *adds to* the default folder scan and would double-load
  (`marketplace/targets/claude/plugin_json_gen.py:12-19`, `:134-150`).
- **Why it matters:** the committed manifest is the human-readable inventory of the bundle and is
  otherwise complete; a skill missing from it is invisible to anyone auditing the bundle by reading its
  manifest, and the omission is easy to mistake for "this skill was never registered".
- **Action:** add `"./skills/lsp-client"` to the array in sorted position — or, if the array is
  deliberately vestigial because the generator empties it, record that in the file's neighbouring
  documentation so the next auditor does not read the omission as a defect.
- **Done when:** the manifest's `skills[]` and the `skills/` directory listing agree for `lsp-client`,
  or the vestigial status is documented.
- **Effort:** S
- **Risk if fixed:** none — the deployed artifact is regenerated with `skills: []` either way.
