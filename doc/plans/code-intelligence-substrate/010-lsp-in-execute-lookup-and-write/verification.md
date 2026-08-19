# Verification — 010-lsp-in-execute-lookup-and-write

**Audited:** `plan.md`, `report-01.md` (the only two files in the plan directory)
**Tree state:** `61a43e5` on `claude/code-intelligence-substrate-analysis-kah884`, re-verified at
`f49542c` and again at `c5511dd` on the same branch (the second reading is the adversarial review's).
`git diff 61a43e5..HEAD` over every audited surface — `lsp-client/`, its tests, `manage-run-config`,
`execute-task`, `doc/user/lsp-code-intelligence.adoc`, `plugin.json` — is **empty** at all three
commits, so no citation below moved between the readings. (Other agents commit to this branch
continuously, so the branch head and `git rev-list --count HEAD` move between readings and are not
stated as a fixed figure; the audited surfaces are what was pinned.)
**Overall verdict:** CONFIRMED WITH GAPS

All five deliverables landed as real, reachable code with real tests, and D0's premise was settled
against a genuine language server that is still reachable from this clone. **Five** correctness holes
were found by reading and then proved by execution against a live `pyright-langserver`: the read
side's only cross-file lookup kind returns coordinates with **no file path**; `document-symbol`
returns 1 of 43 symbols on this repository's own `architecture.py` and reports that as a complete
positive answer; the write side's post-edit diagnostics re-run returns the **pre-edit** diagnostic set
on a large real module, so D2's "a worsened diagnostic set fails the step" guard fails open — proved
through the shipped `edit` verb end to end, which reports `status: success, applied: true` and leaves
the broken file in the tree; the same guard compares an **aggregate error count**, so an edit that
merely *moves* breakage from one footprint file to another lands as a pass; and a diagnostics query
the server never answers is reported as `state: ok, error_count: 0` — a clean file.

## Deliverable verdicts

| # | Deliverable (short) | Report claim | Ground truth | Verdict |
|---|---|---|---|---|
| D0 | GATE: warm server reachable from a leaf; hosting decision | CONFIRMED against live `pyright-langserver` 1.1.408; host in-envelope per-call | A live server is reachable and answers (36/36 tests pass here with pyright installed); hosting decision recorded and matches the shipped code. Re-measured latencies reproduce the *warm* figures but not the per-call cost basis the rationale uses | CONFIRMED (with a cost-basis caveat — G7) |
| D1 | Read side + coverage contract | `lookup` verb returns coordinates; `state`+`provider_count` keep the three states separate | Coverage contract shipped and non-vacuous (mutation-proved). But `workspace-symbol` rows carry **no `path`**, and `document-symbol` drops every nested symbol — 1 row returned where the server sent 43, reported as a complete answer | PARTIAL |
| D2 | Write side through the recorded footprint path | footprint from the edit → apply → re-diagnose → worsened fails and rolls back; adversarially verified | Mechanism shipped and the verdict guard is non-vacuous (mutation-proved, incl. the real-server adversarial test). But the re-diagnose reads a stale set on a large real module (fail-open, reproduced **through the shipped verb** against live pyright), the verdict is a bare aggregate error **count** so a swapped *or relocated* error passes, resource-op parts of an edit are silently dropped, a mid-apply failure leaves the tree half-edited, a declined rename returns `status: success`, and **no test exercises a multi-file rename through the verb** | PARTIAL |
| D3 | Diagnostics as a pre-build signal, with the boundary | `diagnose` verb + boundary note in payload, SKILL and user page; cold read passed | Boundary prose present in all three places and in the module docstring; wording is unambiguous ("supplements … not replaces"). D3's *done-condition is about the text* and the text holds; the verb itself reports an unanswered query as a clean file (G13) — a defect the done-condition does not reach | CONFIRMED (done-condition met; see G13 for a verb defect outside it) |
| D4 | Opt-in config, no-op degradation, docs | machine-local `language_servers` + 4 verbs; unconfigured is byte-identical; `not_configured` ≠ `unreachable` | All present and tested; the unconfigured path makes no server contact and no mutation | CONFIRMED |

## Per-deliverable detail

### D0 — GATE: is a warm server reachable from a dispatched leaf at all?

- **Required (plan):** *"a recorded measurement from a live server exists, or the run reports the
  premise refuted"*, plus the hosting decision (envelope / `marshalld` / sidecar) in the same breath.
- **Claimed (report):** cold start 413.4 ms, `documentSymbol` 2.7 ms, `references` 11.9 ms,
  `definition` 2.6 ms, `rename`→multi-file `WorkspaceEdit` 4.9 ms, first diagnostics 736.3 ms, against
  `pyright-langserver` 1.1.408; hosting = in-envelope per-call subprocess; split = proceed unsplit.
- **Found:** the measurement is recorded in `report-01.md:15-45`; the hosting decision is implemented
  exactly as recorded — `lsp_client.py:310-315` (`_session` spawns the configured command per call),
  `_lsp_jsonrpc.py:81-101` (`StdioTransport` = `subprocess.Popen` of the server), teardown at
  `_lsp_jsonrpc.py:245-270`. No daemon, no socket: `grep -n "lsp" marketplace/bundles/plan-marshall/skills/manage-build-server/**` finds nothing, so `marshalld` was not widened.
- **Checks run:** the figures were re-derived against a live server on this machine
  (`/root/.local/bin/pyright-langserver`), workspace scoped to `manage-architecture` as the report was.
  The adversarial pass re-took the whole set independently; both readings are shown, because the
  spread between them is itself the finding:

  | Operation | Audit (quiet box) | Audit (loaded box) | Re-take 1 | **Re-take 2 (adversarial)** | Report |
  |---|---|---|---|---|---|
  | cold start (spawn + `initialize`) | 571.3 ms | 2140.1 ms | 394.3 ms | **352.9 / 357.6 ms** | 413.4 ms |
  | **first** `documentSymbol` after `didOpen` | 4873.3 ms | 13384.0 ms | 970.5 ms | **907.8 ms** | 2.7 ms |
  | `documentSymbol` repeated in same session | 4.2 ms | — | 2.3 ms | **1.9 ms** | 2.7 ms |
  | `documentSymbol` after `workspace/symbol` + diagnostics | — | — | 4.7 ms | **4.3 ms** | 2.7 ms |
  | `definition` | 3.1 ms | 32.3 ms | 1.7 ms | **2.1 ms** | 2.6 ms |
  | `references` | 2.8 ms | 12.3 ms | 2.0 ms | **2.5 ms** | 11.9 ms |
  | first diagnostics (≥2 s floor) | 2000.4 ms | 2001.1 ms | 2000.3 ms | **2302.1 ms** | 736.3 ms |
  | `workspace/symbol` (≥1.5 s `wait_until_idle` floor) | — | — | 2163.0 ms | **2105.1 ms** | 240.6 ms |
  | `rename` → `WorkspaceEdit` | 11.9 ms | 42.4 ms | 2.3 ms | **1.5 ms** | 4.9 ms |

  Two of these are **floor-bounded** rather than load-dependent, and they are the ones the conclusion
  should rest on: `diagnose` cannot return before the `settle` floor (`settle=2.0` at
  `_lsp_jsonrpc.py:204`) and `workspace-symbol` cannot return before `wait_until_idle`'s 1.5 s floor
  (`:225`, invoked at `:349`). ⚠ *Floor-bounded, not constant* — an earlier reading of this row called
  the 2000.3 ms figure deterministic, but the wait restarts on every inbound publish, so the second
  re-take measured 2302.1 ms for the same call. The floor is a lower bound the call cannot beat.
  The analysis wait is not floor-bounded at all: the audit's 4873 ms first-`documentSymbol` figure did
  **not** reproduce — two later re-takes measured 970.5 ms and 907.8 ms on the same workspace. What
  *did* reproduce exactly, in all three readings, is the **ordering effect**: issuing `documentSymbol`
  first in a cold session costs ~1 s, and issuing it after `workspace/symbol` + diagnostics (the
  report's own sequence) costs 4.7 / 4.3 ms. The report's 2.7 ms is therefore a warm figure; the
  magnitude of the cold one is machine-state-dependent and must not be quoted as a constant.

- **Verdict:** CONFIRMED — the premise holds and a live server was genuinely driven. The caveat is the
  *cost basis*: the report's per-call figures are **warm-path** figures (its sequence issued
  `workspace/symbol` and diagnostics before `documentSymbol`, so the analysis wait had already been
  paid). Under the shipped per-call hosting model, a one-shot lookup pays cold start **plus** the
  first-query analysis plus, for two of the four verbs, a fixed multi-second settle floor — order of
  1.4 s for a cold `document-symbol` and ≥2.5 s for a cold `workspace-symbol` on a quiet box, not the
  ~0.42 s the "per-call boot is cheap" rationale uses. See G7.

### D1 — the read side

- **Required (plan):** *"a leaf obtains a symbol's locations without reading the containing files, and
  the three states above are separately representable in the returned payload"* — `definition` /
  `references` / `documentSymbol` / `workspace/symbol`, carrying the substrate's coverage contract.
- **Claimed (report):** `lookup` verb with all four kinds; `state` + `provider_count` keep
  `not_configured` / `unreachable` / `ok`-found-nothing separate; verified by
  `test_three_states_are_distinguishable` plus two real-server tests.
- **Found:** `lsp_client.py:367-377` (`cmd_lookup`), `:170-204` (`_run_lookup`, all four kinds),
  `:416-425` (the argparse `--kind` choices). Coverage contract: `:109-119` (`_degraded`,
  `provider_count: 0`), `:196-204` (`state: ok`, `provider_count: 1`, `location_count`), documented at
  `lsp-client/SKILL.md:49-69`.
- **Checks run:**
  - Mutation M2 — `lsp_client.py:358` changed so the unreachable path returns `STATE_NOT_CONFIGURED`.
    `test_three_states_are_distinguishable` went red (`assert 2 == 3 … {('degraded','not_configured',0),('success','ok',1)}`). The negative control the plan demanded is real.
  - Live probe of the payload shape against pyright over a two-file project
    (`class Widget: def spin/def stop` in `alpha.py`, imported by `beta.py`), driving the **shipped**
    `_run_lookup`. Re-run independently in the adversarial pass, identical result both times:
    - `workspace-symbol` for `Widget` → `locations: [{"name":"Widget","kind":5,"line":0,"character":6}]` — **no `path` key at all** (`path keys present: False`).
    - The same probe dumped pyright's **raw** `workspace/symbol` result: each row carries
      `location.uri = file:///…/alpha.py`. The path is supplied by the server and discarded by the
      client — the information is not missing, it is thrown away.
    - Control in the same session: `references` rows carry
      `{character, end_character, end_line, line, path}`, so the omission is specific to `_symbol_rows`.
    - `document-symbol` over `alpha.py` → `['Widget', 'top_level']`; `Widget.spin` and `Widget.stop`
      are absent.
  - Scale of the `document-symbol` loss, measured on this repository's own
    `manage-architecture/scripts/architecture.py` (576 lines): pyright's hierarchical response carries
    **43** symbols; the shipped verb returns **1** row (`main`) and reports `location_count: 1` — a
    positive, apparently-complete answer that omits 98% of what the server said.
- **Verdict:** PARTIAL. The coverage contract is fully delivered and non-vacuously tested. The literal
  *Done when* ("obtains a symbol's **locations**") is not met for `workspace-symbol`: a name plus a
  line number without a file is not a location, so the one lookup kind that spans files cannot locate
  anything (`_symbol_rows`, `lsp_client.py:147-162`, emits only `name`/`kind`/`line`/`character`, while
  the sibling `_location_rows` at `:122-144` does emit `path`). `document-symbol` is worse than
  incomplete — it is *silently* incomplete: `initialize` advertises
  `hierarchicalDocumentSymbolSupport: true` (`_lsp_jsonrpc.py:290`), `_symbol_rows` never recurses into
  `children`, and nothing in the payload records that anything was dropped, so a 1-of-43 result is
  indistinguishable from a file that genuinely holds one symbol. That is the archetype D1's ⛔ names
  ("a silent empty result is the archetype this epic exists to remove"), one step short of empty. See
  G1 and G5.

### D2 — the write side, applied through the recorded path

- **Required (plan):** *"a multi-file rename lands through the recorded footprint-capturing path, the
  captured file list matches the edit, and a worsened diagnostic set fails the step"* — footprint
  captured **from the edit itself**, never from a later diff; verified **after** application by
  re-running diagnostics.
- **Claimed (report):** `edit` verb: rename → `WorkspaceEdit` → `capture_footprint` → `apply_workspace_edit` → re-diagnose → `edit_verdict` + `restore_files`; adversarially verified by
  `test_edit_worsened_fails_and_rolls_back` and `test_real_adversarial_defect_fails_and_rolls_back`.
- **Found:** `lsp_client.py:207-275` (`_run_edit`), `_lsp_workspace_edit.py:90-98`
  (`capture_footprint`, from `normalize_changes`, i.e. from the edit), `:141-158`
  (`apply_workspace_edit` returning originals), `:161-164` (`restore_files`), `:167-179`
  (`count_error_diagnostics` / `edit_verdict`). The failure payload carries
  `reason: diagnostics_worsened`, `rolled_back: true`, `errors_before` / `errors_after`,
  `new_diagnostics[]` (`lsp_client.py:249-263`).
- **Checks run:**
  - Mutation M1 — `edit_verdict` forced to always return `'success'`. Three tests went red, including
    the real-server adversarial one: `test_edit_worsened_fails_and_rolls_back`,
    `test_real_adversarial_defect_fails_and_rolls_back`, `test_edit_verdict_fails_on_worsened`
    (`3 failed, 33 passed`). The adversarial control is genuine, not positive-only.
  - Live repro of the post-edit read path — **against real `pyright-langserver`**, not a fake server.
    The sequence follows `_run_edit`'s reads (`open` → `diagnostics` → write the broken content to
    disk → `change_to_disk` → `diagnostics` → `edit_verdict`), over a generated ~12,000-line module
    whose analysis pyright cannot finish inside the 2 s settle window:

    ```
    diagnostics() #1 returned in 10658 ms -> 0 entries      [uri_in_cache=True diag_seq=1]
    <broken content written to disk; change_to_disk sent>
    diagnostics() #2 returned in  2004 ms -> 0 entries      [uri_in_cache=True diag_seq=1]
    errors_before=0 errors_after=0 verdict=success
    MECHANISM: diag_seq unchanged since the pre-edit read -> the PRE-EDIT entry was returned
    TRUTH after extra wait (1 new publish frame): 1 error(s)
    ```

    The instrumented `diag_seq` is the proof, not an inference: it is the transport's own count of
    `publishDiagnostics` frames received, and it is **identical** before and after — no new publish
    arrived, so `wait_for_diagnostics` returned the entry cached before the edit, at the 2 s floor.
    ⚠ This probe is *not* a byte-exact replay of `_run_edit` (an earlier reading claimed it "mirrors
    `_run_edit` exactly"): the verb also re-opens the rename target before the pre-edit read — the
    duplicate `didOpen` filed as G14 — so the two flip at different module sizes.
  - **The same failure driven through the shipped verb**, which is the load-bearing evidence and what
    establishes that a broken edit *lands*. Real `StdioTransport`, real pyright, real
    `capture_footprint` / `apply_workspace_edit` / `edit_verdict`; the only interposition is on the
    `textDocument/rename` **response**, replaced by a `WorkspaceEdit` carrying a deliberate defect —
    exactly the control the plan's Verification section mandates for D2. On a 36,002-line module,
    reproduced twice:

    ```
    [wait_for_diagnostics 8049 ms  diag_seq 0 -> 2  entries=0]   <- errors_before
    [wait_for_diagnostics 2006 ms  diag_seq 2 -> 2  entries=0]   <- errors_after (seq unchanged: stale)
    payload: status=success applied=true errors_before=0 errors_after=0 verdict=success
    defect left on disk: True
    ```

    Controls in the same harness: at ~480 lines the identical defect returns `status: failed`,
    `reason: diagnostics_worsened`, `rolled_back: true`, `new_diagnostics: ["undefined_symbol_xyz" is
    not defined]` and the file is restored; at ~12,000 lines the verb-level run still held. The
    threshold is machine- and load-dependent — the guard works exactly until the server is slower than
    the settle window and then fails **open**, not closed.
  - Multi-file coverage: `test_real_clean_rename_edit` asserts `file_count == 1`
    (`test_lsp_integration.py:102`); `test_edit_clean_applies_and_captures_footprint` uses a
    single-file edit (`test_lsp_client.py:186-197`). The only two-file exercise
    (`test_apply_and_restore_round_trip`, `test_lsp_workspace_edit.py:107-123`) bypasses `_run_edit`.
  - Resource operations: `normalize_changes` builds `notes` for a dropped create/rename/delete
    (`_lsp_workspace_edit.py:71-74`), but both callers discard them
    (`:97` and `:149`, `changes, _notes = …`), and
    `grep -n "notes" lsp_client.py SKILL.md doc/user/lsp-code-intelligence.adoc` returns **nothing**
    (control: the same grep finds 8 hits in `_lsp_workspace_edit.py`).
  - Verdict semantics, probed through `_run_edit` with a fake transport:
    - pre-edit `[Error A]`, post-edit `[Error B]` (a *different* error, same count) →
      `status: success, applied: True`, and `bar = 1` is left on disk. An edit that swapped one error
      for another is not a worsened **set** by `edit_verdict`'s bare count comparison.
    - **Cross-file netting, on the multi-file path the deliverable exists for.** Footprint
      `[a.py, b.py]`; pre-edit 1 error in `a.py` and 0 in `b.py`; post-edit 0 in `a.py` and 1 in
      `b.py` → `errors_before=1, errors_after=1`, `status: success, applied: True`, both files left
      rewritten with `b.py` newly broken. `errors_before` / `errors_after` are single integers summed
      across the whole footprint (`lsp_client.py:230-247`), so the guard cannot see breakage that
      merely *moved*. This is the realistic form of the count-vs-set defect and it was not recorded by
      the first reading of this audit.
    - pre-edit `[Error A]`, post-edit `[Error A, Error B]` → the failure payload's `new_diagnostics[]`
      lists **both**, including the pre-existing one. The field name overstates what it holds
      (`lsp_client.py:238-245` appends every post-edit Error and never diffs against the pre-edit set,
      which is only counted, never retained). See G15.
  - A **declined rename** returns `status: success`. When the server sends no `WorkspaceEdit` —
    ordinary when the coordinate is not on a renameable symbol — `_run_edit` returns
    `status: success, applied: False, reason: no_workspace_edit` (`lsp_client.py:217-227`, pinned by
    `test_edit_no_workspace_edit`). The documented consumer wiring routes on `failed` and `degraded`
    only (`execute-task/SKILL.md:244`), so a leaf following it reads a rename that never happened as
    one that landed. G16.
- **Verdict:** PARTIAL. The recorded design rule is genuinely shipped and its central guard is
  non-vacuous. Against the literal *Done when* it falls short in four ways — the worsened-set guard
  fails open when the server is slower than the settle window (G2, reproduced through the shipped verb
  against real pyright), the guard compares an aggregate error **count** rather than per-file sets so
  a swapped *or relocated* error passes (G15), the footprint is not honest for an edit carrying
  resource operations (G3), and the *multi-file* half of the done-condition has no test (G6). A
  mid-apply exception additionally leaves a half-applied edit with no rollback (G4), every `edit` call
  sends a duplicate `didOpen` for the rename target (G14), and a declined rename is reported as a
  success the consumer wiring has no branch for (G16).

### D3 — diagnostics as a pre-build correctness signal

- **Required (plan):** *"the capability is stated together with the boundary, and an independent cold
  reader reports that it read the text as supplements the gate, not replaces it"*.
- **Claimed (report):** `diagnose` verb + `DIAGNOSTICS_BOUNDARY_NOTE` in every payload, boundary prose
  in `lsp-client/SKILL.md` and the user page; the Step-6 sub-agent's cold read returned
  *"supplements the quality gate"*.
- **Found:** `lsp_client.py:60-65` (the note constant), `:301` (carried in the `diagnose` payload),
  `:24-27` (module docstring), `lsp-client/SKILL.md:88-96` ("It does **not** run the project's quality
  gate, tests, linters, or coverage, and a clean `diagnose` is **not** a green build"),
  `doc/user/lsp-code-intelligence.adoc:34-37` (same, as an AsciiDoc NOTE),
  `execute-task/SKILL.md:244` ("supplements, never replaces").
- **Checks run:** read all four surfaces. Every one states the boundary in the same sentence as the
  capability; none phrases the signal as sufficient. I cannot re-run the *original* cold read (it was
  a sub-agent judgement at the time), but the text as it stands admits only the "supplements" reading:
  the negative is explicit, not implied.
- **Verdict:** CONFIRMED against its literal *Done when*, which is a condition on the **text**: the
  capability is stated together with the boundary, and the text as it stands admits only the
  "supplements" reading. Two defects sit outside that condition and are recorded rather than allowed
  to change the verdict:
  - the "every payload" phrasing is false for a `degraded` diagnose return, which carries no
    `boundary_note` (`lsp_client.py:389-392` → `_with_session` → `_degraded`) — G8;
  - the verb itself reports an **unanswered** diagnostics query as a clean file. Driven through the
    shipped `_run_diagnose` over a real `StdioTransport` against a server that answers `initialize`
    and never pushes `publishDiagnostics`, the verb returns after the 15 s timeout with
    `status: success, state: ok, provider_count: 1, error_count: 0` and a `boundary_note` — a payload
    identical in every field to "the server ran and found the file clean". `wait_for_diagnostics`
    returns `list(self._diagnostics.get(uri, []))` on timeout (`_lsp_jsonrpc.py:223`), and no caller
    can tell that from an empty published set — G13.

### D4 — opt-in configuration, no-op degradation, documentation

- **Required (plan):** *"a project with no configuration produces byte-identical behaviour to today,
  and no server configured is distinguishable in the output from a server configured and
  unreachable"*.
- **Claimed (report):** machine-local `language_servers` section with new `language-server`
  get/set/list/remove verbs; `lsp_client` degrades to `read_edit`; distinguishability asserted by
  `test_preflight_not_configured` vs `test_preflight_unreachable`; docs at
  `doc/user/lsp-code-intelligence.adoc`, `run-config-standard.md` § Language-Servers, execute-task
  seams.
- **Found:** `run_config.py:710-801` (the four verb handlers), `:1334-1358` (the `language-server`
  subparser), `run-config-standard.md:208-248` (§ Language-Servers, schema + operations),
  `doc/user/lsp-code-intelligence.adoc:13-16` (*"This is strictly opt-in, and an unconfigured project
  loses nothing"*), `doc/user/README.adoc:22` (indexed), `execute-task/SKILL.md:242,244,286` (three
  consumer seams, all gating on `preflight` → `state: ready` or on a `degraded` return).
  Degradation: `lsp_client.py:350-358` returns `_degraded(...)` before any spawn when
  `resolve_language_server` yields `None` — no subprocess, no mutation.
- **Checks run:** the four config tests plus `test_preflight_not_configured` /
  `test_preflight_unreachable` / `test_edit_degraded_when_not_configured` pass; the last asserts the
  target file is byte-unchanged. `test_run_config_language_server.py` covers set/get/list/remove,
  `enabled: false`, default `language_id`, and a non-JSON `--command`.
- **Verdict:** CONFIRMED. `not_configured` and `unreachable` are separately representable and both are
  asserted. Two low doc defects: the user page's state table (`:62-78`) omits `preflight`'s `ready`
  (G10), and the re-diagnose scope is not stated (G9).

## Correctness review

Defects found by reading the shipped code, each proved by execution where the brief allows:

1. **Stale post-edit diagnostics — D2's guard fails open.** `_lsp_jsonrpc.py:204-223`
   (`wait_for_diagnostics`) breaks out of its wait as soon as the *inbound stream* has been quiet for
   `settle` (2.0 s) **and** the URI has *any* entry — including the entry cached before the edit
   (`:220`). It does not wait for a publish newer than the change, despite the module docstring
   claiming exactly that (`:14-15`: *"`publishDiagnostics` tracked per URI so a post-edit re-diagnose
   can wait for the **next** push"*). `_run_edit` (`lsp_client.py:239-247`) therefore compares
   `errors_after` computed from pre-edit data, `edit_verdict` returns `'success'`, and a broken edit
   lands with `status: success, applied: true`. Reproduced above **against live
   `pyright-langserver`** — both on the read path (~12,000-line module) and, decisively, **through the
   shipped `edit` verb end to end** (36,002-line module, twice), where the payload reads
   `status: success, applied: true` and the defect is left in the tree. The transport's own
   `publishDiagnostics` counter proves no new publish arrived between the two reads.
2. **`workspace-symbol` results are unaddressable.** `lsp_client.py:147-162` (`_symbol_rows`) drops the
   URI entirely, even though pyright returns `SymbolInformation` objects carrying `location.uri` — the
   code reads `location` only to take its `range` (`:152-154`). Confirmed by dumping the raw server
   response alongside the shipped payload in one session: the server sent
   `location.uri = file:///…/alpha.py`; the row that reached the caller had keys
   `{name, kind, line, character}`. Consequence: the payload names a symbol and a line but not a file,
   so the leaf must fall back to `Grep`/`Read` to find it, which is the cost D1 exists to remove.
3. **Nested symbols are silently dropped by `document-symbol`.** `_symbol_rows` iterates the top level
   only; pyright's hierarchical response nests methods under `children`. Measured on this repository's
   `manage-architecture/scripts/architecture.py`: 43 symbols in the server's response, **1** row in the
   payload, `location_count: 1`. A leaf cannot locate `ClassName.method` with this verb, and — worse —
   nothing in the payload distinguishes "this file has one symbol" from "42 were discarded".
4. **A `WorkspaceEdit` carrying resource operations is applied partially and reported as complete.**
   `_lsp_workspace_edit.py:71-74` records the dropped create/rename/delete ops in `notes`, then both
   `capture_footprint` (`:97`) and `apply_workspace_edit` (`:149`) throw the notes away, and no payload
   field carries them. The file-honesty rule the plan required D2 to *ship* ("the captured file list
   matches the edit") is violated exactly when it matters. `test_normalize_reports_resource_operation`
   (`test_lsp_workspace_edit.py:64-68`) asserts the notes exist at the seam that discards them, so the
   guard cannot fire in the shipped path.
5. **A mid-apply failure leaves the tree half-edited.** `apply_workspace_edit`
   (`_lsp_workspace_edit.py:141-158`) writes file-by-file with no `try`/`except`. An error on the
   second of three files propagates out of `_run_edit`; `_with_session` catches only spawn failures
   (`lsp_client.py:356-358`), so `safe_main` turns it into a `status: error` TOON and exit 1
   (`tools-file-ops/scripts/file_ops.py:1664-1700`, the `except Exception` arm at `:1696-1698`) — with
   file one modified, no rollback, and no footprint reported. Reproduced through `_run_edit` over a
   three-file footprint whose middle file carries a malformed `TextEdit`: `KeyError: 'range'` escapes
   and `a.py` is left rewritten while `b.py` / `c.py` are untouched. ⚠ The trigger set is narrower
   than an earlier reading of this item claimed: a **missing path** and an **encoding error** both
   raise in `_run_edit`'s *pre-edit* `session.open()` / `errors_before` loop (`:231-233`), which reads
   every footprint file before any write — verified, with no file modified. The genuine mid-apply
   triggers are a malformed `TextEdit`, a write-side `OSError`, and a file removed between the
   pre-edit read and the apply. G4.
6. **An unanswered diagnostics query is reported as a clean file.** `wait_for_diagnostics` returns
   `list(self._diagnostics.get(uri, []))` when its deadline expires (`_lsp_jsonrpc.py:223`), so "the
   server never told us anything about this file" and "the server told us the file is clean" reach
   `_run_diagnose` and `_run_edit` as the same empty list. `diagnose` then reports
   `state: ok, provider_count: 1, error_count: 0` — the payload the coverage contract reserves for a
   *real* positive answer — and `edit_verdict` scores every such edit `success`. Demonstrated by
   driving the shipped `_run_diagnose` over a real `StdioTransport` against a server that answers
   `initialize` and never pushes diagnostics (the pull-diagnostics server class): returned in 15001 ms
   with `error_count: 0`. G13.
7. **The worsened-set guard is an aggregate count comparison, and `new_diagnostics[]` is misnamed.**
   `edit_verdict` (`_lsp_workspace_edit.py:172-179`) returns `'failed'` only when
   `errors_after > errors_before`, and those two operands are single integers summed **across the
   whole footprint** (`lsp_client.py:230-247`). Two proved consequences: an edit that removes one
   error and introduces a different one in the same file passes and lands (pre `[Error A]` / post
   `[Error B]` → `status: success, applied: True`, `bar = 1` left on disk); and an edit that moves
   breakage between footprint files passes and lands (pre 1 error in `a.py` + 0 in `b.py` / post 0 +
   1 → `errors_before=1, errors_after=1`, `status: success, applied: True`, `b.py` newly broken) —
   the cross-file case strikes exactly on the multi-file rename D2 exists for. Separately, `_run_edit`
   builds `new_diagnostics[]` from *every* post-edit Error without diffing the pre-edit set
   (`lsp_client.py:243-245`), so a pre-existing error is reported as new (proved: pre `[A]` / post
   `[A, B]` → the payload lists both). G15.
8. **Every `edit` call sends a duplicate `didOpen`.** `_run_edit` opens the rename target at
   `lsp_client.py:214`, then re-opens each footprint file — including that same target — at `:232`.
   Counted through an instrumented transport: `didOpen` twice for one URI with no `didClose` between,
   then `didChange`. LSP forbids a second open notification without an intervening close, and
   `LspSession.open` resets `_doc_versions[abs] = 1` each time, so the version sequence a strict
   server sees is 1, 1, 2. pyright tolerates it; a different server need not, and the plan asked for a
   client a second consumer can reuse (`lsp_harvest.py` already does). G14.
9. **A declined rename is reported as a success the consumer wiring cannot route.** When the server
   returns no `WorkspaceEdit`, `_run_edit` returns `status: success, applied: False,
   reason: no_workspace_edit, file_count: 0` (`lsp_client.py:217-227`), pinned by
   `test_edit_no_workspace_edit` (`test_lsp_client.py:217-225`). The documented consumer wiring names
   exactly two returns to route on — *"Treat a `failed` return as a rejected edit … and a `degraded`
   return as 'unavailable' (fall back to `Edit`)"* (`execute-task/SKILL.md:244`) — and
   `lsp-client/SKILL.md` § "The write side" (`:71-86`) does not mention the outcome at all. A leaf
   following the wiring therefore reads a rename that never happened as one that landed and does not
   fall back. The discriminator exists in the payload, so this is a wiring gap, not a missing signal.
   G16.
10. **Bounded, in-spec limitations worth recording** (no gap raised for the mechanism, only for the
    documentation): the re-diagnose covers only the footprint files, and only severity `Error`
    (`_lsp_workspace_edit.py:167-169`); `diagnosticMode` is `openFilesOnly`
    (`_lsp_jsonrpc.py:57-68`), so breakage outside the edited set is invisible. `wait_until_idle`
    (`:225-243`) imposes a ≥1.5 s floor on every `workspace-symbol` call and `wait_for_diagnostics` a
    ≥2 s floor on every `diagnose` — re-measured across readings at 2163.0 / 2105.1 ms and
    2000.3 / 2302.1 ms respectively (a floor, not a constant).

What I read to conclude the rest is sound: all three shipped scripts end to end (`wc -l`:
`lsp_client.py` 456, `_lsp_jsonrpc.py` 378, `_lsp_workspace_edit.py` 179). The transport's reader-thread resilience
(the reviewer's Finding 2) is correctly per-message: `_read_loop` (`_lsp_jsonrpc.py:115-153`) skips a
length-0 or malformed frame and returns only on EOF or `OSError`. `apply_text_edits` (`:119-138`)
applies highest-offset-first against offsets computed once, and the order-independence is asserted
both ways (`test_apply_multiple_edits_bottom_up`). `select_language_server`
(`lsp_client.py:73-96`) rejects a non-list, empty, or non-string command and honours
`enabled: false`. Config resolution reads the shared machine-local store rather than a parallel one
(`:99-101`).

## Test adequacy

Re-derived at audit time: `uv run python -m pytest test/plan-marshall/lsp-client/ -o addopts="" -q` →
**36 passed in 23.27 s**, with `pyright-langserver` present at `/root/.local/bin/pyright-langserver`
so the 5 real-server tests actually ran (they are `skipif`-guarded at
`test_lsp_integration.py:43-44`). Re-derived again independently in the adversarial pass:
**36 passed in 23.74 s** with pyright on `PATH`, and **31 passed, 5 skipped** with pyright hidden —
the latter is the CI shape, and it is the shape the mutation rows below are read against. Re-derived
a third time by the adversarial review: **36 passed in 20.55 s** with pyright, **31 passed, 5 skipped**
with it hidden. Test-function count re-derived by reading all four files: 16 + 5 + 14 + 1 = **36**,
of which the 5 in `test_lsp_integration.py` are the `skipif`-guarded real-server set.

| Deliverable | Covering tests | Adequacy |
|---|---|---|
| D0 | `test_lsp_integration.py` (5 real-pyright tests) | Adequate as standing evidence that a live server is reachable and answers |
| D1 coverage contract | `test_three_states_are_distinguishable` (`test_lsp_client.py:138-157`) | **Non-vacuous** — proved by mutation M2 |
| D1 lookup kinds | `test_lookup_document_symbol_returns_coordinates`, `…_references_returns_locations`, `…_workspace_symbol`, `test_real_document_symbol_and_references`, `test_real_workspace_symbol_after_indexing` | **Weak on payload shape**: the workspace-symbol tests assert `name` and `location_count` only, so the missing `path` passes unnoticed; no test asserts a nested symbol is reachable |
| D2 verdict + rollback | `test_edit_worsened_fails_and_rolls_back`, `test_real_adversarial_defect_fails_and_rolls_back`, `test_edit_verdict_fails_on_worsened` | **Non-vacuous** — proved by mutation M1 (all three go red) |
| D2 footprint | `test_capture_footprint_from_edit`, `test_apply_and_restore_round_trip` | Adequate for the pure helpers; **no test drives a multi-file edit through `_run_edit`/`cmd_edit`**, which is the literal done-condition (G6) |
| D2 resource ops | `test_normalize_reports_resource_operation` | **Vacuous with respect to the shipped path** — it asserts a value that no caller consumes (G3) |
| D2 verdict semantics | `test_edit_verdict_passes_on_equal_or_improved` (`test_lsp_workspace_edit.py:139-142`) | **Locks in the defect**: it asserts `edit_verdict(3, 3) == 'success'` (`:141`), which is exactly the same-count case that lets a swapped or relocated error land (G15). A test can be non-vacuous and still assert the wrong contract |
| D2 declined rename | `test_edit_no_workspace_edit` (`test_lsp_client.py:217-225`) | Adequate as a code test — it asserts `status: success`, `applied: False`, `reason: no_workspace_edit`. **Inadequate as a contract test**: no consumer document names that outcome, so nothing binds the assertion to the wiring a leaf follows (G16) |
| D3 | `test_diagnose_carries_boundary_note` | Adequate for the success path; the degraded path's missing note is unasserted, and no test asserts that a *timed-out* diagnose is distinguishable from a clean one (G13) |
| D4 | `test_preflight_not_configured`, `test_preflight_unreachable`, `test_real_preflight_ready`, `test_edit_degraded_when_not_configured`, `test_run_config_language_server.py` | Adequate — both directions asserted |
| Transport | `test_reader_survives_length_zero_junk_frame` | Adequate and CI-portable (fake server subprocess, no pyright) |
| `wait_for_diagnostics` freshness | *none in CI* | **Missing** — proved by mutation M3 (below). No test asserts staleness or freshness semantics; the settle *duration* is exercised only incidentally, by the one `skipif`-guarded real-server test (G2) |

**Mutation evidence.** Three mutations, each re-run independently in the adversarial pass and a
**third** time by the adversarial review, whose results are the ones tabulated. Snapshots of all three
scripts were taken to `$TMPDIR/…/adv-010-…-mutsweep/` before any edit and restored by byte copy
afterwards; `md5sum` matches the pre-mutation digests (`lsp_client.py` `665eee6b…`, `_lsp_jsonrpc.py`
`0856b4f0…`, `_lsp_workspace_edit.py` `2b815b14…`) and `git status --porcelain` lists no file under
`marketplace/bundles/plan-marshall/skills/lsp-client/`. No `git checkout` / `restore` / `stash` was
used. Baseline before mutation: **36 passed in 20.55 s** with pyright present.

| Mutation | Change | Result |
|---|---|---|
| **M1** | `edit_verdict` forced to always return `'success'` | `3 failed, 33 passed` — `test_edit_worsened_fails_and_rolls_back`, `test_real_adversarial_defect_fails_and_rolls_back`, `test_edit_verdict_fails_on_worsened`. Reproduced verbatim, three times |
| **M2** | the unreachable branch (`lsp_client.py:358`) returns `STATE_NOT_CONFIGURED` | `1 failed, 35 passed` — `test_three_states_are_distinguishable`, failing on `assert 2 == 3` with `{('degraded','not_configured',0),('success','ok',1)}`. Reproduced verbatim, twice |
| **M3** | `wait_for_diagnostics` body replaced by `return list(self._diagnostics.get(uri, []))` — the settle window, the freshness loop and the timeout all deleted | With pyright installed: `1 failed, 35 passed` — only `test_real_adversarial_defect_fails_and_rolls_back`. **With pyright hidden (the CI condition): `31 passed, 5 skipped` — fully green.** Reproduced verbatim, twice. The whole diagnostics-wait mechanism can be deleted and CI does not notice; the fake transport (`test_lsp_client.py:45-46`) pops a queue and never calls it |

## Report accuracy

Most claims in `report-01.md` hold against the tree now. The exceptions:

- **"`diagnose` verb + `DIAGNOSTICS_BOUNDARY_NOTE` in every payload"** (`report-01.md:58`) — false as
  written, and repeated in shipped documentation at `lsp-client/SKILL.md:92` ("every payload carries
  the boundary in `boundary_note`"). Only the *success* diagnose payload carries it
  (`lsp_client.py:301`); a `degraded` return does not (`:109-119`). Correct statement: *every payload
  a running server produced*.
- **The D0 latency table** (`report-01.md:21-29`) is accurate as a set of measurements but is used
  (`:33`, `:40`) as the cost basis for the hosting decision without disclosing that the per-call
  figures are warm-path. Re-measured twice here, the first query in a fresh session costs 970 ms on a
  quiet box (4873 ms in the first audit reading, 13384 ms under load) rather than 2.7 ms; the honest
  per-call cost of a one-shot lookup is cold start **plus** first analysis, and for `diagnose` and
  `workspace-symbol` **plus** a fixed settle floor that no amount of warmth removes.
- **"⚠ Sync owed"** (`report-01.md:61`, `:127`) — stale against the current lane contract. `CLAUDE.md`
  § Standalone Plan Lane now states that a lane plan editing `marketplace/bundles/` *"neither performs
  a sync nor records one as owed"*. Harmless, confined to the report — G11.
- **"`35 passed` in the lsp-client suite"** (`report-01.md:78`) and **"the 4 lsp-client real-pyright
  integration tests"** (`:67`) — both were true of their moment; the current counts are **36** total
  and **5** real-server tests (`test_real_preflight_ready` was the fix commit's addition, and a later
  plan, `02ced6f`, refactored the argument construction). Not defects, recorded so a later reader does
  not treat the older numbers as current.
- **Unverifiable from this clone:** the whole-tree `./pw verify` figures (`18714 passed, 14 skipped`,
  `mypy … 385 files`), the individual commit SHAs (`6a96ab0`, `f5ae40f`, `e4154aa`, `d46769e`,
  `9dc172d`) and the wall-clock figure. The clone is shallow — a `.git/shallow` graft is present, and
  each of those five SHAs still returns `fatal: Not a valid object name` at every reading. (The
  history has been deepened since the first reading, and `git rev-list --count HEAD` keeps moving as
  other agents commit to this branch — 50, then 284, then 299; the plan's own commits are absent at
  all of them, which is the only part of that figure that carries information.) The PR record is
  consistent with them and was re-read independently twice: PR #1140 reports 9 commits, 17 changed
  files, +2335/−3, opened 2026-08-10T15:20:50Z, head ref `claude/lsp-execute-lookup-write-43d0ar`,
  merged 2026-08-10T18:06:34Z by `cuioss-oliver` into `main`.

Verified true: the shipped symbol and file names (`_run_lookup`, `_run_edit`, `capture_footprint`,
`apply_workspace_edit`, `edit_verdict`, `restore_files`, `STATE_READY`, `DIAGNOSTICS_BOUNDARY_NOTE`,
all named test functions), the Finding-1 fix (`cmd_preflight` emits `ready`, `lsp_client.py:341-347`;
documented at `SKILL.md:66-69`; `test_real_preflight_ready`), the Finding-2 fix (per-message reader
resilience plus `test_lsp_transport.py`), the reviewer table (Sourcery's stored review is verbatim the
quoted weekly-rate-limit notice), the branch name (`claude/lsp-execute-lookup-write-43d0ar` is PR
#1140's head ref), and the unsplit decision being recorded before implementation.

## Declared residue — current status

| Residue item (from report) | Still open? | Evidence |
|---|---|---|
| MERGED confirmation for PR #1140 | **Closed** | `pull_request_read get`: `"merged": true`, `"merged_at": "2026-08-10T18:06:34Z"`, `merged_by: cuioss-oliver`, base `main` |
| Local plugin-cache sync owed for `marketplace/bundles/**` | **Moot** | `CLAUDE.md` § Standalone Plan Lane: a lane plan "neither performs a sync nor records one as owed"; the merged bundle source is authoritative and `target/` / `~/.claude/` are machine-local |
| Reviewer coverage 1 of 3 (two bots rate-limited) | **Open but not actionable** | `get_reviews` on #1140 returns a single review — Sourcery's rate-limit notice. No re-review was performed; the PR merged without one, as the contract allows |
| "What have we learned" GAP: the lane contract should sanction arm-and-hand-off | **Closed** | `.claude/skills/cloud-plan-lane/SKILL.md:55`: *"a run cannot reliably block-until-green and re-check inside the session — Step 8's arm-and-hand-off completion exists for exactly this"* |

## Out-of-scope and collateral

Every exclusion was respected.

- **Default-on behaviour** — not built. Absent configuration resolves to `None`
  (`lsp_client.py:81-91`) and every verb returns `degraded` before contacting anything.
- **Batch harvesting of symbol references** — not in this plan's surface. The harvest that exists now
  (`pm-plugin-development/skills/plan-marshall-plugin/scripts/lsp_harvest.py`) belongs to a later
  plan and *reuses* this client (`:138-147`, `:272-277`: `client.StdioTransport`, `client.LspSession`),
  which is what this plan's Notes asked for ("build the client so a second consumer can reuse it").
- **Editor-facing corpus language server** — separate surface
  (`pm-plugin-development/skills/tools-corpus-language-server/`), separate store, and
  `doc/developer/corpus-language-server-protocol.adoc:71-78` records that it deliberately did *not*
  extend the `language_servers` binding.
- **Any claim of a token saving** — none found. The shipped docs claim a mechanism ("coordinates, not
  file bodies"), never a measured share.
- **Widening the build daemon silently** — not done; no LSP reference exists under
  `manage-build-server`, and the hosting decision is recorded.

No collateral change was found: the plan's PR touched 17 files and every surface I located
(`lsp-client/`, its tests, `run_config.py` + its standard + tests, `execute-task/SKILL.md`,
`doc/user/lsp-code-intelligence.adoc`, `doc/user/README.adoc`) is named in the plan's Expected surface
or is the index entry for one that is.

One registration surface the plan did **not** touch is worth recording, because it is where a reader
auditing the bundle by its manifest would look for the new skill: the committed
`marketplace/bundles/plan-marshall/.claude-plugin/plugin.json` declares **76** entries in `skills[]`
while `marketplace/bundles/plan-marshall/skills/` holds **78** directories (counts re-derived
independently at review time). The two absent are `lsp-client` — this plan's skill — and
`recipe-surgical-fix`, which belongs to another plan. There is no runtime consequence: the Claude
target regenerates the manifest with `skills: []` deliberately, because a declared array *adds to* the
default folder scan and would double-load (`marketplace/targets/claude/plugin_json_gen.py:12-19`,
`:134-150`). Recorded as G12.

## Method and coverage

- Read in full: `plan.md`, `report-01.md`, all three shipped scripts, all four test files,
  `lsp-client/SKILL.md`, `doc/user/lsp-code-intelligence.adoc`, the `language_servers` half of
  `run_config.py` and `run-config-standard.md`, and the three `execute-task/SKILL.md` seams.
- Executed: the lsp-client suite at baseline and under each of three mutations with byte-snapshot
  restore (M1/M2/M3, each re-run to a verbatim repeat), with and without pyright on `PATH`; a
  live-server payload-shape probe; a live-server latency re-measurement (four readings across three
  sessions, under different machine load); a fail-open repro on the read path against real pyright;
  a fail-open repro **through the shipped `edit` verb** against real pyright at three module sizes;
  a `_run_diagnose` repro against a purpose-built never-publishing server over the real
  `StdioTransport`; a notification-sequence count through an instrumented transport; and four
  `_run_edit` probes with a fake transport covering the verdict semantics (same-file swap, cross-file
  netting, `new_diagnostics[]` contents, mid-apply failure).
- Queried GitHub read-only for PR #1140's merge state and reviews (twice, independently).
- **Not checked, and why:** the whole-tree `./pw verify` numbers (out of scope per the brief — the run
  is many minutes); the plan's individual commits and their per-commit gates (shallow clone, graft
  present, the five SHAs unreachable); the *original* Step-6 cold reads (a past sub-agent judgement —
  I read the current text instead and state what reading it admits); token/wall-clock cost figures
  (the report itself declines to state tokens).
- **False-negative discipline:** every "grep found nothing" result was paired with a control that finds
  the same pattern where it is known to exist (e.g. `notes` → 0 hits in `lsp_client.py`/SKILL/user page,
  8 hits in `_lsp_workspace_edit.py`).
- **Tree left unchanged.** `git status --porcelain` for
  `marketplace/bundles/plan-marshall/skills/lsp-client/` is empty and all three mutated files match
  their pre-mutation `md5sum` (`665eee6be4d405b18393f368b8db31b7`,
  `0856b4f003199a82e81d915cf3d6989f`, `2b815b14d1b58e106f3609ac02c7db26`). Restoration was by byte
  copy from the snapshot directory; no `git checkout` / `restore` / `stash` was used at any point.
  Other modified paths in the working tree are other agents' `doc/plans/` edits under this same epic;
  I did not touch them.

## Adversarial review

Independent review of this document and `gaps.md`. Attacks run: A1 false positives, A2 false
negatives, A3 vacuous evidence, A4 counts and quotes, A5 actionability, A6 severity/topic,
A7 coverage, A8 internal consistency.

⚠ **Starting condition.** A previous adversarial reviewer was interrupted mid-edit and its partial
corrections were committed, so both documents were re-derived from scratch rather than trusted. The
largest defect found was a direct consequence: `verification.md` cited G13, G14 and G15, and
`gaps.md` referenced G13 in its grouping paragraph and claimed a total of "fifteen", while the file
actually stopped at G12. Three gaps the audit had *proved* existed nowhere in the deliverable a later
fix run would read.

| # | Attack | What was found | Correction applied |
|---|---|---|---|
| 1 | **A8** internal consistency | **G13, G14 and G15 were missing from `gaps.md` entirely** — cited by name in `verification.md` (D2 verdict, D3 verdict, correctness-review items 6–8) and by the grouping paragraph in `gaps.md` itself, but the file ended at G12. The half-applied edit from the interrupted reviewer | Authored all three as full entries, each re-proved by execution first: G13 (unanswered diagnose reads as a clean file — high), G14 (duplicate `didOpen` — medium), G15 (aggregate-count verdict + misnamed `new_diagnostics[]` — high) |
| 2 | **A8** internal consistency | `gaps.md`'s intro said "fifteen concrete defects" but its own breakdown summed to 14 (3+1+4+1+5), and the file listed 12. Grouping paragraph named four gaps sharing a fix window, of six that do | Intro re-derived: **sixteen** defects, breakdown 4+1+4+1+6, plus an explicit severity census (high G1/G2/G13/G15; medium G3/G4/G5/G6/G7/G14/G16; low G8–G12). Grouping paragraph corrected to the six `lsp-client/scripts/` gaps |
| 3 | **A2** false negatives — **the most consequential finding** | The audit's own G2 repro was a *hand-replayed* read sequence, not the shipped verb, and its text claimed the probe "mirrors `_run_edit` exactly" — it does not (the verb re-opens the rename target first, which the audit files separately as G14). Re-running the audit's own construction at 12,002 lines through `_run_edit`, **the guard held**, so the audit's headline claim ("a broken edit lands as success") was not actually established by its evidence | Built a stronger repro: the **shipped `_run_edit`** driven end to end against real pyright, real transport, real footprint/apply/verdict, interposing only on the `textDocument/rename` response to carry a deliberate defect (the control the plan mandates). At 36,002 lines, twice: `status: success, applied: true, errors_after: 0`, defect left on disk, with `diag_seq 2 -> 2` proving the stale read. Controls at ~480 lines (fails and rolls back correctly) and ~12,000 lines (still held). G2 and the D2 detail rewritten to lead with this; the "mirrors exactly" claim retracted in both documents |
| 4 | **A2** false negatives | **Cross-file netting, unrecorded.** `errors_before` / `errors_after` are single integers summed across the *whole footprint* (`lsp_client.py:230-247`), so an edit that moves breakage from one footprint file to another nets zero and lands. Proved: pre 1 error in `a.py` + 0 in `b.py`, post 0 + 1 → `status: success, applied: True`, `b.py` newly broken. This is the *realistic* form of the count-vs-set defect and it strikes exactly on the multi-file rename D2 exists for; the audit had recorded only the contrived same-file swap | Folded into G15 as proved case 2, and into correctness-review item 7 and the D2 detail. It is why G15 is filed **high** rather than medium |
| 5 | **A2** false negatives | **A declined rename returns `status: success`.** When the server sends no `WorkspaceEdit` (ordinary — the coordinate is not on a renameable symbol) the verb returns `status: success, applied: False, reason: no_workspace_edit`, while the documented consumer wiring routes on `failed` and `degraded` only (`execute-task/SKILL.md:244`). A leaf following the wiring reads a rename that never happened as one that landed. Not recorded anywhere in the audit | New gap **G16** (medium, `bundle-docs`), plus correctness-review item 9 and a test-adequacy row noting `test_edit_no_workspace_edit` is adequate as a code test but binds to no consumer contract |
| 6 | **A1** false positives | **G4's evidence named two triggers that cannot fire.** "A path the server named but that no longer exists" and "an encoding error" both raise inside `_run_edit`'s *pre-edit* `session.open()` / `errors_before` loop (`:231-233`), before any write — verified with `b.py` absent: exception fires, **no file modified**. So the cited mechanism did not produce the cited outcome | G4's evidence replaced with a repro that does: a malformed `TextEdit` (no `range`) on the middle file of a three-file footprint → `KeyError: 'range'` escapes with `a.py` rewritten and `b.py`/`c.py` untouched. Trigger set narrowed to the three that genuinely strike mid-apply. Correctness-review item 5 corrected the same way. **The gap itself is real** — only its evidence was wrong |
| 7 | **A5** actionability | G4's *Done when* prescribed `chmod 0444` to make a file unwritable. Verified this **does not work**: the suite runs as `root`, the mode bit is ignored, and the whole three-file edit applied cleanly — a fixing run would have written a test that passes against the unfixed code | *Done when* rewritten with a ⛔ against `chmod`, naming the malformed-`TextEdit` and patched-`write_text` triggers that actually fail |
| 8 | **A4** counts and quotes | G7 claimed the `diagnose` re-measurement "returned in **exactly** 2000 ms" and the D0 table called two floors "deterministic". Re-measured: 2302.1 ms for the same call. The wait restarts on every inbound publish, so the settle value is a **lower bound**, not a constant | Both documents re-worded to "floor-bounded, not constant", with the earlier claim explicitly retracted; D0 table gained a fourth measurement column and a `documentSymbol`-after-warmup row that isolates the ordering effect |
| 9 | **A4** counts and quotes | G8 attributed *"carried in every diagnose payload"* to "the module docstring". It is a `#` code comment above the constant (`lsp_client.py:60-61`); the module docstring says something different | Attribution corrected |
| 10 | **A4** counts and quotes | Header pinned `git rev-list --count HEAD` at **284**; it reads **299** now. Other agents commit to this branch continuously, so the figure is not a property of the audit | Header and Report-accuracy re-worded: the audited *surfaces* are what was pinned (`git diff 61a43e5..HEAD` over all of them is empty at `61a43e5`, `f49542c` and `c5511dd`); the rev count is reported as a moving number whose only informative part is that the plan's five SHAs are absent at all of them |
| 11 | **A4** counts and quotes | Script line counts stated as 457 / 379 / 180; `wc -l` gives 456 / 378 / 179 (trailing-newline convention) | Restated with the measurement basis named |
| 12 | **A1/A4** — clean results, stated so an empty row is distinguishable | Every `path:line` in both documents was opened and checked. **All correct**, including the non-obvious ones: `file_ops.py:1664-1700` / `:1696-1698` (`safe_main`'s `except Exception` arm), `plugin_json_gen.py:12-19` / `:134-150`, `_lsp_jsonrpc.py:220`/`:223`/`:225`/`:290`, `lsp_harvest.py:138-147`/`:272-277`, `cloud-plan-lane/SKILL.md:55`, and every `report-01.md` line reference. Quotes verified verbatim against their source files | None needed |
| 13 | **A4** counts | Re-derived every stated number at check time: **36** tests (16+5+14+1 by reading, 36 passed in 20.55 s by running); **5** real-server tests; **76** manifest entries vs **78** skill directories, the two absent being `lsp-client` and `recipe-surgical-fix`; **43** raw symbols vs **1** shipped row on `architecture.py` (**576** lines); `notes` grep 0/0/0 with control 8. PR #1140: 9 commits, 17 files, +2335/−3, merged 2026-08-10T18:06:34Z; `get_reviews` returns exactly one review, Sourcery's rate-limit notice, verbatim as quoted | All confirmed; none needed correction |
| 14 | **A3** vacuous evidence | Re-ran the audit's whole mutation sweep independently — M1 (`3 failed, 33 passed`, same three tests), M2 (`1 failed, 35 passed`, `assert 2 == 3` with the same triple set), M3 (`1 failed, 35 passed` with pyright; **`31 passed, 5 skipped` — fully green — with pyright hidden**). All three reproduce **verbatim**. The M3 result is real: the entire diagnostics-wait mechanism can be deleted and CI does not notice | Mutation block updated to record the third independent run and the baseline; no claim needed correcting |
| 15 | **A3** vacuous evidence | Independently re-proved every gap the audit claimed to have proved by execution — G1 (row keys `['character','kind','line','name']`, raw server row carries `location.uri`, `references` control carries `path`), G5 (`['Widget','top_level']` vs 4 raw; 1 vs 43 on `architecture.py`), G13 (15064 ms, `state: ok, error_count: 0`, `boundary_note` present), G14 (didOpen ×2, didClose ×0, versions 1/1/2), G15 (all three cases). No claimed reproduction failed to reproduce | Evidence blocks annotated with the independent re-take where the numbers differ |
| 16 | **A6** severity/topic | G15 had no filed severity (it did not exist as an entry). Given two proved cases in which a genuinely worsened diagnostic set lands as `status: success, applied: true` — one of them on the multi-file path — the calibration's "a guard cannot fire" applies | Filed **high**, with the reasoning stated inside the entry so a later reviewer can disagree explicitly. G13 filed **high** (documented coverage contract unimplemented); G14 **medium** (real protocol violation, no observed misbehaviour with the shipped server, but the plan required a reusable client and a second consumer exists); G16 **medium**, topic `bundle-docs` because the fix lands in two SKILL.md files. Every pre-existing severity and topic was re-checked against the calibration and none needed changing |
| 17 | **A7** coverage | `verification.md` covers all five deliverables, out-of-scope compliance, report accuracy, declared residue, collateral and method. No deliverable is silently unmentioned. D3's CONFIRMED verdict correctly rests on its *literal* done-condition (a condition on the text) while recording two verb defects outside it — that separation is right, not a dodge | None needed |
| 18 | **A8** internal consistency | With G13–G16 added, every finding in `verification.md` that warrants action now appears in `gaps.md`, and every `gaps.md` entry traces to a `verification.md` finding. The overall CONFIRMED WITH GAPS verdict follows from its rows (2 PARTIAL, 3 CONFIRMED) | Verified after the additions; the opening summary updated from "four correctness holes" to five |

**Residual doubt:** the thing a further round would most likely find is another instance of the defect
class this round twice caught the audit in — *evidence that does not exercise the shipped path*. G2's
original repro replayed a sequence rather than calling the verb, and G4's cited triggers fired in a
different function than claimed. Both G3 and G5 are currently proved only at the helper/probe level;
neither has been driven through `cmd_edit` / `cmd_lookup` as a subprocess with argparse and TOON
output, so a defect in the CLI seam (argument plumbing, `output_toon` rendering of `locations[]` /
`files[]`) would be invisible to everything here. Second, all latency and fail-open thresholds are
from one machine with one server (`pyright-langserver` 1.1.408); the *mechanisms* are established by
code reading and are server-independent, but every module-size threshold quoted is a local
observation, not a constant. Third, D3's cold-read half is still taken on the run's own sub-agent's
word — it cannot be re-run, and no reading of the current text substitutes for it.

**Verdict on the audit:** SOUND AFTER CORRECTION — every defect it named is real and reproduces, but
three of its gaps were missing from the deliverable entirely, its headline G2 evidence did not
exercise the shipped path, and G4's cited trigger fires in a different function than claimed; with
those fixed, four gaps added or re-proved and two overstated measurements retracted, both documents
now match the tree.
