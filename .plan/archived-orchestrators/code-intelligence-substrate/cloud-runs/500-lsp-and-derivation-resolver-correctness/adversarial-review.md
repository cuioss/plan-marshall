# Adversarial review of the 500-lsp-and-derivation-resolver-correctness audit

Target audit: `500-verification.md` + `500-gaps.md` (post-run audit of PR #1321, plan
`500-lsp-and-derivation-resolver-correctness`). Repo HEAD `31211a99b`.

## Headline finding

The audit's own top-line verdict — **"zero high-severity gaps... none of it capable of producing a
false-clean success"** — is refuted by the very source document (`report-01.md`) the audit read and
cites as its evidence.

`report-01.md` § Left open, survivor **S1** (CRLF line-ending rewrite):

> "so a rollback reports `rolled_back: true` over a file whose bytes differ from the pre-edit bytes"
> ... Bound: "Line endings only, never content — **the one open finding that can produce a
> clean-looking difference**, which is why it is named first."

And explicitly, in round 11's own summary (`report-01.md:1057-1059`):

> "**None of these can produce a false clean success — the class this plan exists to eliminate —
> except `S1`, which is bounded to line endings.**"

The report **names its own exception** to the false-clean-immunity claim. The audit's
`500-verification.md` (§ Non-convergence, last bullet) says:

> "Twelve behavioural survivors (S1–S12, B2, B3) remain open by design, each with a stated bound. I
> independently confirmed S1 ... is still present in the shipped code ... **None of the twelve can
> produce a false-clean success per the report's own analysis, which I did not find reason to
> dispute.**"

This is a direct, checkable contradiction. The auditor confirmed S1's presence in code but did not
connect it to the report's own explicit "except S1" sentence three lines away in the same document, and
then wrote a blanket claim ("none... false-clean success") that the source it cites literally negates for
the one survivor it named by name. This single sentence is the reason the epic's zero-high-severity base
rate held here too: **the run's own report discloses a live false-clean survivor, and the audit's summary
erased the disclosure while quoting the same survivor as confirmed-present.**

## Severity recalibration #1 — `500-gaps.md` G1 (CRLF false-clean): low -> HIGH

`500-gaps.md`'s own G1 entry independently reaches the same fact — its Evidence line quotes the
verbatim report language and its Consequence line says "this is the one residue item that can look
clean while the bytes on disk changed" — yet rates the gap **low** severity. This is an internal
inconsistency inside the audit's own two files: `gaps.md` documents the exact mechanism that
`verification.md`'s summary says does not exist, and even `gaps.md` itself undersells its own evidence
by rating "the one residue item that can look clean" as low.

Per the review brief's own calibration rule — a false claim (here, in the tool's live return payload,
`rolled_back: true`, not merely in documentation) sits above a cosmetic inconsistency — and per the
plan's own stated Goal ("the write path fails closed... never a pass" / "a code path that cannot answer
returns the shape of an answer"), a rollback that reports `rolled_back: true` while the restored bytes
provably differ from the pre-edit file is exactly the defect class the entire six-deliverable plan
exists to eliminate, still present and reachable (any CRLF-authored file — certain on Windows-originated
input, a realistic corpus for a cross-platform tool) at HEAD. **Recalibrated: HIGH.**

## Missed finding — S8 (`normalize_changes` silently drops a malformed `documentChanges` entry, verb
reports `success`): not in `gaps.md` at all

The report's own § Left open lists S8: *"`normalize_changes` silently drops a malformed
`documentChanges` entry, and the whole-refusal gate fires only on non-empty `notes[]`, so the remainder
is applied and reported `success`."* Neither `500-verification.md` nor `500-gaps.md` mentions S8 by
name or by mechanism anywhere.

I independently verified the mechanism by reading
`marketplace/bundles/plan-marshall/skills/lsp-client/scripts/_lsp_workspace_edit.py:126-140`
(`normalize_changes`):

```python
for change in document_changes:
    if not isinstance(change, dict):
        continue                                    # <- silently dropped, no note
    kind = change.get('kind')
    if kind in _RESOURCE_OP_KINDS:
        notes.append(f'unapplied resource operation: {kind}')
        continue
    text_document = change.get('textDocument')
    edits = change.get('edits')
    if isinstance(text_document, dict) and isinstance(edits, list):
        path = uri_to_path(text_document.get('uri', ''))
        result.setdefault(path, []).extend(edits)
    # else: falls through -- also silently dropped, no note, no result entry
```

A `documentChanges` entry that is not a dict, or is a dict but neither a recognised resource-operation
kind nor a well-formed `{textDocument, edits}` pair, is dropped with **no note appended**. The
whole-refusal gate G3's fix added (`notes[]` non-empty -> fail the verb) only fires on resource-op
kinds, so this class of malformed entry never trips it. The caller proceeds to apply every
*recognised* edit in the `WorkspaceEdit` and reports `status: success` with a footprint that silently
omits the dropped entry — this is structurally the *same* defect class G3 was written to close (an edit
containing an unrepresented part is applied partially and reported `status: success`), reached through
a different malformed-input door.

This differs materially from S2/S9, which the report correctly notes "cannot produce a false clean"
because they *raise* and escape to `safe_main` as a bare error. S8 does not raise — it silently
continues and can report a real `status: success`. The round-11 summary's blanket "except S1" is
therefore incomplete on the report's own terms; S8 is a second exception the report itself half-names
(by listing the mechanism) without applying its own false-clean test to it, and the audit never engaged
with S8 at all. **Rate: MEDIUM** (consistent with the plan's own original G3 rating for the same
mechanism — resource-op notes were medium, not high — and it requires a malformed `WorkspaceEdit` shape,
the same caveat the report attaches to S2/S9).

## G6 (npm blast radius) — measured, and the audit's own escalation trigger is now met: medium -> HIGH

`500-gaps.md` G6 correctly identifies the npm-side risk and explicitly defers its severity pending
measurement: *"If the blast radius matches the Python case (whole-tree loss), this should be re-triaged
to high severity."* I performed that measurement by reading the code (the same code-reading method the
audit itself used throughout, since executing a build/test cycle is outside this review's write
boundary):

`marketplace/bundles/plan-marshall/skills/build-npm/scripts/_npm_cmd_discover.py`:

- `_load_package_json` (`:391-404`) returns whatever `json.loads` parses, without checking it is a
  `dict`. A top-level JSON array or string parses successfully and is returned as **truthy**, so
  `root_data is None` (line 63) and `if ws_data:` (line 80) both pass it through unchanged.
- `_resolve_workspaces` (`:143`) immediately calls `root_data.get('workspaces', [])`. If `root_data` is
  a `list` or `str`, this raises `AttributeError: '...' object has no attribute 'get'` — **uncaught**,
  at the very top of `discover_npm_modules`, before any per-module logic runs.
- Independently, inside the workspace-member loop (`:76-83`), a member's `package.json` that is a
  top-level array/string passes the same truthy check (`if ws_data:`) and is handed to `_build_module`,
  whose very first data access, `pkg_data.get('name', base.name)` (`:233`), raises the same
  `AttributeError` — **uncaught**, inside the `for ws_dir in workspace_dirs:` loop with no
  per-iteration `try`/`except`.

Both paths propagate all the way out of `discover_npm_modules` uncaught. This is exactly the shape of
the Python-side defect round 10 fixed and treated as its worst finding ("no malformed input, no
filesystem failure, no server: ordinary text in a metadata field, and the capability answered
nothing at all... every module in the tree, not just the malformed one"): **one workspace member's
malformed `package.json` (or the root's) aborts discovery of every npm module in the project**,
including ones that parse perfectly. G6's own stated escalation criterion is met.
**Recalibrated: HIGH.**

(The `workspaces: ["/etc/*"]` / `["../*"]` half of G6 is a separate, still-unmeasured concern — glob
escaping the project root — and is not resolved by this reading; it remains open at whatever severity
a further measurement assigns, orthogonal to the whole-tree-abort finding above.)

## D5 round-8 frame fix — independently CONFIRMED (the audit is right here)

Verified independently, not taking the audit's word:

- At commit `9d375dfed` (the squashed D5 landing commit, an ancestor of current HEAD), `read_message`
  in `_corpus_lsp_protocol.py` has **no** `FrameError` class and returns `None` uniformly for every
  malformed frame shape (bad length, missing header, short body, bad JSON, bad UTF-8) — identical to
  end-of-stream. This matches the audit's/report's claim that the title clause was false at that
  commit.
- At HEAD, `_corpus_lsp_protocol.py:36-115` has `FrameError(detail, recoverable)`, `read_message`
  raising it per malformed shape with the recoverable/unrecoverable split the report describes, and
  `serve()` (`:218-256`) wraps `read_message` in `try/except FrameError`, logging via
  `_log_frame_error` and either continuing (recoverable) or ending (unrecoverable) — never silently.
- `git log --oneline -- test/.../test_corpus_lsp_honesty.py` shows the fix commit
  `e06141409` ("fix: a deliverable's own title clause was false, and two more code defects") between
  `9d375dfed` and the final squash `2c40e7027` — consistent with the report's claim that round 8's fix
  was folded into the landed squash.
- Read the actual test bodies (`test_a_recoverable_bad_frame_is_skipped_and_the_session_continues`,
  `test_an_unrecoverable_bad_frame_ends_the_session_AUDIBLY`, both parametrised over the seven frame
  shapes): they assert (a) the request *after* the bad frame is answered (recoverable) or specifically
  is **not** answered (unrecoverable), (b) exactly one `malformed frame` stderr line, driven through a
  real `subprocess.run` over `serve`. Against the pre-round-8 code confirmed above (`read_message`
  returns `None` for every shape, indistinguishable from EOF), request id `9` after the bad frame would
  never be answered and stderr would carry no `malformed frame` line — the test would fail for exactly
  the reason claimed, not incidentally. **d5_frame_fix_verdict: CONFIRMED.**

## Round 11 `setup.cfg` fix — independently CONFIRMED (the audit is right here too)

Read `_pyproject_cmd_discover.py:462-520` (`_read_setup_cfg`) directly. Confirmed: `ConfigParser()` is
constructed with default (i.e. `BasicInterpolation`-on) behaviour; every `parser.get()` call is inside
the `try` block (not just `parser.read()`); metadata is accumulated into a **local** `read_metadata`
dict and committed to the real `metadata` dict only after the whole descriptor is read successfully
(the "all-or-nothing" property the report claims); the docstring explicitly states the "interpolation
stays ON" reasoning matching setuptools' own behaviour. This matches `report-01.md`'s round-11 (V2/V3)
account exactly, at the file:line level. **Confirmed by code reading**, which is the same standing the
report itself gives this check (no execution-based re-verification exists for this function past round
11, a gap both the report and the audit correctly flag as open).

## CI portability figures — not independently reproduced by this review either

Per the write boundary and time budget, this review did not attempt to hide `pyright-langserver` from
`PATH` and re-run the affected suites, matching the audit's own disclosed scope limit. This is not a
defect in the audit — it disclosed the limit plainly — but it means the `662 passed / 10 skipped` and
`53 failed / 10 passed / 1 skipped` figures remain **unverified by three independent passes now**
(round 5's own four attempts, this audit, and this adversarial review), not merely one. The coverage
hole compounds rather than closes.

## Coverage holes in the audit

- Of the twelve disclosed survivors (S1–S12, B2, B3), the audit states it independently confirmed only
  **S1 and B2** by code read. It did not check S2–S12 or B3 individually against the code — it accepted
  the report's bounds for ten of twelve on the report's word alone, then asserted a blanket property
  ("none... false-clean") across all twelve that the report itself contradicts for the one item (S1) the
  audit did check.
- G6's blast radius was named as unmeasured and left that way — this review measured it (see above) and
  it changes the verdict.
- The CI-portability figures were named as unverified and left that way (consistent, not a defect, but
  the coverage hole is real and now three-deep).
- Round 11's own `setup.cfg` fix was (correctly) verified only by code reading, not execution, and the
  audit says so; this review did the same and reached the same conclusion — an honest, matching
  limitation, not a gap in the audit specifically.
- The `72` cross-bundle references / `10` module edges / `61`-of-`5083` validator figures were correctly
  flagged as unreproducible in a sandbox without `pyright-langserver`/a live validator run; not
  re-attempted here either, for the same reason. No defect found in how the audit handled these.

## Fabricated findings

None found. Every deliverable-level mechanism claim in `500-verification.md` that this review checked
independently (D5's frame fix, D4/round-11's `setup.cfg` fix, D6's `configured` unification via direct
line read) held up exactly as stated, at the file:line level. The audit's factual reporting of what is
in the tree is accurate everywhere sampled; its failure is in the **completeness and internal
consistency of its severity/verdict layer**, not in fabricating evidence.

## Wrong counts or quotes

None found that rise to "wrong." The plan.md-vs-report.md numeric drift on G10's validator figures
(`61 of 5 081`, `25/36`, `41%/59%` in `plan.md` vs `61 unresolved of 5083`, `26/35`, `43%/57%` in
`report-01.md`) is explicitly expected — the plan's own text labels every such figure "a lead, not a
fact" to be re-derived at run time, and the audit correctly quotes the report's re-derived figures, not
the plan's stale ones.

## Unactionable entries

None of `500-gaps.md`'s six entries (G1–G6) lack an observable Done-when; all six are reasonably
actionable as written. The gap is severity, not actionability.
