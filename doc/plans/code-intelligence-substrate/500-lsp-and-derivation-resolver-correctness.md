> ⛔ **FIRST INSTRUCTION — do not skip, do not delete, do not move below the title.**
>
> Before reading the rest of this plan and before any other action, load the working contract that
> governs this run:
>
> ```text
> Skill: cloud-plan-lane
> ```
>
> It owns the branch/PR/review-comment cycle, the build gate, the pre-PR verification sub-agent, the
> run report, and the closing self-check. **Nothing in this plan overrides it** — where this plan and
> the contract disagree, the contract wins, and the disagreement is reported.
>
> If the skill cannot be loaded, **stop and report the run blocked**. Do not reconstruct the workflow
> from this file: the parts that matter most — the merge gate, the verification dispatch, the report
> — are not in here.
>
> This block is part of the plan, not part of the template. It survives into every copy.

# The LSP surfaces and the derivation resolvers answer honestly

**Epic:** code-intelligence-substrate
**Branch prefix:** fix

## Problem

Three shipped surfaces in this repository answer code-intelligence questions, and each of them
currently returns a confident answer it cannot stand behind.

**The LSP client** (`marketplace/bundles/plan-marshall/skills/lsp-client/scripts/`) is the read/write
seam a task leaf uses instead of `Grep` and `Edit`. Its post-edit verification can return the
**pre-edit** diagnostic set, so an edit that breaks the parse is compared against its own earlier
state and reported `status: success, applied: true` with the broken file left on disk. Its verdict
sums error **counts** across the whole footprint, so an edit that moves breakage from one file to
another nets zero and lands. A file the server never answered for is byte-identical, in every payload
field, to a file the server examined and called clean. And its `workspace-symbol` rows — the only
lookup kind that spans files — carry a line number with **no file path**, which is precisely the
`Grep`/`Read` fallback the capability exists to remove.

**The skill-corpus language server**
(`marketplace/bundles/pm-plugin-development/skills/tools-corpus-language-server/scripts/`) is
resident, and residency is its entire justification — yet one malformed request kills it, because
JSON-RPC dispatch has no exception boundary and the process then writes TOON error text onto the
frame stream a client is still parsing. Its `textDocument/references` projection discards the
`verified` flag the index computed, so reference sites the index itself could **not** confirm reach
an editor as ordinary LSP `Location`s — while two shipped pages promise, in near-identical words,
that such a site is "never presented as an exact location".

**The derivation resolvers** are supposed to give the module graph edges derived from real code. The
`lsp` resolver derives **zero** module edges on this repository, and structurally so: the
marketplace's cross-bundle imports are bare imports resolved at runtime by the generated executor's
`sys.path`, which a language server rooted at the repository root cannot follow, so not one
cross-bundle reference resolves. The native Python discoverer reads exactly one table (`[project]`)
of exactly one file (`pyproject.toml`), so a Poetry-managed project and a setuptools `setup.cfg`
project each derive nothing — and a malformed descriptor is swallowed by a bare `except Exception`.
In every one of those cases the seam reports `status: ok, edge_count: 0`, which the shipped
documentation defines as *"a real, positive result"* — a measured absence, when the truth is a
missing capability.

The mechanism is the same in all three: **a code path that cannot answer returns the shape of an
answer.** Each site was found by an audit of the landed plans and then re-checked by an independent
adversarial pass; the per-gap detail is cited below, and the essentials are restated here so this
plan stands alone.

## Goal

Every one of these surfaces either answers or says it could not. The write path fails closed when the
parser's verdict is unavailable or newer breakage appeared anywhere in the footprint; lookup rows
carry the file they refer to; the resident corpus server survives a bad frame and never presents an
unconfirmed site as exact; the Python and npm discoverers read the descriptors they already claim to
have found, and a descriptor they cannot parse is reported rather than absorbed; the `lsp` harvest
either resolves cross-bundle imports or states why it cannot, and never silently attributes a
vendored file to a repository module. Where the right answer is a design or contract decision, this
plan records a proposal for the operator and takes none.

## Deliverables

Each deliverable is independently verifiable. ⛔ **Every count, threshold and file list in this plan
is a lead, not a fact** — re-derive it in the clone at the moment you rely on it. The tree has moved
since these gaps were filed, and several of the audit's own numbers were environment-dependent.

### Preconditions every deliverable inherits

Three of the five surfaces are verified against a **real language server**. A fresh clone may not
have one.

⛔ **Before starting D1, D2 or D3, derive whether `pyright-langserver` is on `PATH`, and record the
answer in the run report.** Both branches are authored here, so no decision is required:

- **Present** — real-server assertions run, and their results are reported.
- **Absent** — every *Done when* below that names a real server is satisfied instead by its
  **CI-portable mirror**: a fake server subprocess driven over the real `StdioTransport`, in the
  shape of the existing `test/plan-marshall/lsp-client/test_lsp_transport.py`. The real-server
  assertion is then recorded as NOT RUN with the reason, and the deliverable is **not** claimed on a
  `skipif`-guarded test that silently skipped. A `skipif` test that skips is not evidence.

The CI-portable mirror is required **in either branch**, because the shipped suite is green today
with the entire diagnostics-wait mechanism deleted: mutating `wait_for_diagnostics` to
`return list(self._diagnostics.get(uri, []))` left the suite at 31 passed / 5 skipped on a runner
without pyright (re-run independently by the adversarial review; re-derive the figures, the shape is
what matters). A guard that only a locally-installed binary can falsify is not a guard.

---

1. **D1 — The lsp-client's diagnostics answer contract, and a per-file worsened-set verdict**
   *Covers* `010-lsp-in-execute-lookup-and-write/gaps.md#G2`, `#G13`, `#G15` (all high). The gap
   file is corroboration; everything needed is restated here.

   Three defects share one return contract in
   `marketplace/bundles/plan-marshall/skills/lsp-client/scripts/_lsp_jsonrpc.py`
   (`wait_for_diagnostics`, near `:204-223`) and one verdict in
   `.../scripts/_lsp_workspace_edit.py` (`edit_verdict`, near `:172-179`), consumed by
   `lsp_client.py::_run_edit`:

   - **Stale read (G2).** The wait breaks as soon as the inbound stream has been quiet for the settle
     window and the URI has *any* cached entry — including the entry cached during the pre-edit read.
     The adversarial review drove the **shipped** `_run_edit` end to end against real pyright with a
     deliberate defect interposed on the `textDocument/rename` response: `status: success`,
     `applied: true`, `errors_after: 0`, defect left on disk, with the transport's publish counter
     unchanged either side of the edit. The module's own docstring already claims the correct
     behaviour ("wait for the **next** push") and the code does not implement it. ⛔ The module size
     at which this flips (~36 000 lines in that run, holding at ~12 000) is a **machine- and
     load-dependent observation, not a constant** — do not build a test on a line count; build it on
     a fake server whose post-`didChange` publish is deliberately later than the settle window.
   - **Silence read as clean (G13).** On timeout, or against a server that answers `initialize` and
     never pushes `publishDiagnostics` (the pull-diagnostics class), the same function returns an
     empty list — identical in every payload field to a file the server examined and found clean.
     Driven through the shipped `_run_diagnose`, the verb returned `state: ok`, `error_count: 0`,
     `provider_count: 1`, `boundary_note` present.
   - **Count, not set (G15).** `errors_before` / `errors_after` are single integers accumulated
     across the **whole footprint**, so: a same-file swap (`[Error A]` → `[Error B]`) passes; an
     error **moving** from `a.py` to `b.py` passes with both files left rewritten; and the failure
     payload's `new_diagnostics[]` lists pre-existing errors as new, because it is built from the
     post-edit set with no diff. Both shipped surfaces head the rule "a worsened diagnostic **set**
     fails the step".

   *Change:* give `wait_for_diagnostics` a per-URI publish counter and an `after_seq` / `min_seq`
   parameter; have `change_to_disk` capture the counter and the post-edit wait require one strictly
   greater. On expiry with no newer publish — and on a URI never published for at all — return an
   explicit **unknown**, never the cached list. `_run_diagnose` renders unknown as `state: unknown`
   with `answered: false` and `reason: diagnostics_unanswered`; `_run_edit` treats unknown as
   failure-to-verify — roll back, `status: failed`, `reason: diagnostics_unavailable`, never a pass.
   Retain the pre-edit diagnostics **per file**, keyed by `(path, severity, code, message, line)`;
   compute `added` / `removed` per file; fail when `added` is non-empty for **any** file; populate
   `new_diagnostics[]` from `added` only. Keep `errors_before` / `errors_after` in the payload —
   consumers may already read them.

   *Done when:* four CI-portable tests (fake server subprocess over the real `StdioTransport`) pass
   and each fails against the pre-change code — state that red/green pair in the run report:
   (a) a server whose post-`didChange` publish arrives **after** the settle window makes `_run_edit`
   return `status: failed` with the target byte-identical to its pre-edit content;
   (b) a server that answers `initialize` and never publishes makes `diagnose` differ in at least one
   field from the payload the same verb returns against a server that publishes an **empty**
   diagnostic list, and makes `_run_edit` return `status: failed` with the file unchanged;
   (c) pre `[A]` → post `[B]` in one file returns `failed` and rolls back, and an error moving from
   `a.py` to `b.py` over a two-file footprint returns `failed` with **both** files rolled back;
   (d) with pre `[A]` → post `[A, B]`, `new_diagnostics[]` contains `B` and **not** `A`.
   ⛔ `test_edit_verdict_passes_on_equal_or_improved` currently asserts `edit_verdict(3, 3) ==
   'success'` — it pins exactly this defect and **must change with the contract**; re-derive its
   location before editing.
   ⚠ The fail-closed direction is a behaviour change for a server that legitimately publishes nothing
   for a clean file. State it in `lsp-client/SKILL.md` § "The write side" so a leaf reads
   `diagnostics_unanswered` / `diagnostics_unavailable` as **"verify by build"**, not as "the edit was
   wrong". That sentence is a text-that-drives-a-reader deliverable — see Verification.

2. **D2 — Lookup rows carry their file, and the write path is all-or-nothing**
   *Covers* `010-lsp-in-execute-lookup-and-write/gaps.md#G1` (high), `#G5`, `#G3`, `#G4`, `#G14`
   (medium). One owning surface: `lsp-client/scripts/lsp_client.py` and
   `lsp-client/scripts/_lsp_workspace_edit.py`. The source `gaps.md` recommends these be taken as one
   change window together with D1's; they are split here only so each half is reviewable.

   - **G1 — no path on symbol rows.** `_symbol_rows` (near `lsp_client.py:147-162`) reads the
     server's `location` only to take its `range` and discards `location.uri`. Shipped
     `workspace-symbol` rows are `['character', 'kind', 'line', 'name']`; the sibling `_location_rows`
     already emits `path` via `uri_to_path`, which is the control proving the helper exists.
     *Change:* take `uri_to_path(location['uri'])` when a `location` is present; for
     `document-symbol` (hierarchical, no `location`) pass the queried file's resolved path in, so
     both kinds emit the **same key set**.
   - **G5 — hierarchy not flattened.** The client advertises
     `hierarchicalDocumentSymbolSupport: True` and then iterates only the top level, so a class's
     methods are absent. Observed: a file with `class Widget { spin, stop }` plus `top_level` yielded
     `['Widget', 'top_level']`. *Change:* flatten depth-first, carrying a `container` (parent name) or
     dotted name plus a `depth`, keeping existing keys.
   - **G3 — dropped resource operations are invisible.** `normalize_changes` builds `notes` for each
     dropped create/rename/delete operation and both callers bind them to `_notes` and discard them,
     so an edit containing a resource operation is applied **partially** and reported
     `status: success` with a footprint that omits the dropped part. *Change:* surface `notes[]` and
     an `unapplied_operation_count` in the `edit` payload, and make a non-empty resource-operation
     set **fail the verb** (`reason: unsupported_resource_operation`) rather than apply the text-edit
     remainder.
   - **G4 — no rollback mid-apply.** The apply loop has no `try`/`except`; an exception on the second
     of three files escapes to `safe_main`, leaving file one rewritten, `originals` discarded and no
     footprint in the output. Reproduced with a malformed `TextEdit` (no `range`) on the middle file:
     `a.py` MODIFIED, `b.py`/`c.py` untouched. *Change:* wrap the loop so a failure restores every
     file already written (`restore_files(originals)`), then return `status: failed`,
     `reason: apply_failed`, the offending path, and the rolled-back footprint. A failure of the
     restore itself must be reported, not swallowed.
     ⛔ **Do not trigger the test with `chmod 0444`.** The adversarial review measured this: the suite
     runs as `root`, the mode bit is ignored, and the whole three-file edit applied cleanly — a test
     written that way passes against the unfixed code. Use a malformed `TextEdit` or a patched
     `Path.write_text` that raises on the second call.
     ⚠ Two triggers an earlier reading named do **not** strike mid-apply — a missing path and a
     non-UTF-8 file both raise in the pre-edit open/`errors_before` loop, before any write. Do not
     write the test around them.
   - **G14 — duplicate `didOpen`.** `_run_edit` opens the rename target and then the `errors_before`
     loop re-opens every footprint file including that target; `LspSession.open` resets the document
     version each time, so a strict server observes versions 1, 1, 2 with no `didClose` between.
     Observed: didOpen ×2, didClose ×0. *Change:* track opened URIs on `LspSession` and make `open()`
     a no-op for an already-open document (or add `ensure_open()` used at both sites); do not reset
     the version for an already-open document.

   *Done when:* (a) a `lookup --kind workspace-symbol` payload's `locations[]` rows each carry
   `path` equal to `str(defining_module.resolve())` — asserted over a two-module sample where the
   symbol is defined in a module the call never opens — and `document-symbol` rows carry the same key
   set; (b) a `document-symbol` lookup over a file containing a class returns a **method's** name and
   line; (c) `cmd_edit` given a `WorkspaceEdit` containing a `kind: rename` document change returns a
   non-success payload naming the unapplied operation with **no file on disk modified**; (d) a
   three-file edit failing on the second file leaves all three byte-identical to their pre-edit
   content and names the failing path in the payload; (e) a multi-file `edit` sends exactly **one**
   `textDocument/didOpen` per distinct URI with monotonically increasing `didChange` versions.
   (a) and (b) get the real-server form when a server is available **and** a fake-transport mirror in
   either branch; (c), (d), (e) are fake-transport and must run unconditionally.
   ⚠ The adversarial review's residual doubt applies directly here: G3 and G5 were proved only at the
   helper/probe level, never through `cmd_edit` / `cmd_lookup` as a subprocess with argparse and TOON
   rendering. Drive at least one assertion per verb through the CLI seam, so a defect in argument
   plumbing or `output_toon` rendering of `locations[]` / `files[]` cannot hide.

3. **D3 — The `lsp` harvest resolves real imports, refuses vendored targets, names its real failure,
   and describes its own attribution truthfully**
   *Covers* `200-lsp-derivation-resolver/gaps.md#G1`, `#G2` (high), `#G13`, `#G3`, `#G6` (medium).
   Owning surface:
   `marketplace/bundles/pm-plugin-development/skills/plan-marshall-plugin/scripts/lsp_harvest.py`
   and the resolver at
   `marketplace/bundles/pm-code-intelligence/skills/plan-marshall-plugin/extension.py`.

   ⛔ **Gating derivation — do this first and let it halt the deliverable.** Re-derive the baseline
   on the clone: run `build_lsp_component_refs` over the repository root with an enabled binding and
   the real discovered module set, and record `files_scanned`, the reference count, the module-edge
   count, and the count of references whose two endpoints lie in **different bundles**. The audit
   observed zero module edges and zero cross-bundle references across four whole-tree runs in two
   interpreter environments. **If the baseline already shows a non-zero cross-bundle edge set, stop
   this deliverable's G1 half, record the finding and the numbers, and proceed to the other four
   halves** — the premise has changed and the fix would be aimed at a defect that no longer exists.
   ⛔ If no language server is on `PATH`, the baseline cannot be taken: record that, skip the G1 half
   with the reason, and still land the G13 / G2 / G3 / G6 halves, all of which are provable against a
   stub server or by reading. Do **not** substitute a hand-written expected edge list for the
   measurement.

   - **G1 — cross-bundle imports do not resolve.** The marketplace's cross-bundle imports are bare
     imports satisfied at runtime by the generated executor's `sys.path`; a server rooted at the
     repository root cannot follow them. A direct probe of
     `from extension_base import DerivationResolverBase, ExtensionBase` returned UNRESOLVED at every
     column tried. *Change:* give the server the module search path the executor synthesizes — pass
     `python.analysis.extraPaths` (every bundle skill `scripts/` directory) through a
     `workspace/configuration` reply, or generate a transient `pyrightconfig.json` for the harvest
     root, or narrow the harvest root to a per-bundle subtree carrying that bundle's own path set.
     Whichever is used, the drop-and-note rule stays intact.
     ⚠ Wrongly-scoped `extraPaths` can resolve a name to another bundle's same-named module and
     produce a **confidently wrong edge** — the exact outcome the resolver's ⛔ exists to prevent. The
     resulting edge set must be spot-checked and the spot-check reported.
   - **G13 — vendored trees are excluded as sources but admitted as targets.** `_candidate_files`
     skips `.git`, `node_modules`, `target`, `.venv`, `venv`, `__pycache__`, `.plan` for the files it
     **queries**; `_within` applies no filter at all to what a definition resolves **to**. Two
     consequences: the `unattributable-endpoint` count presented to an operator is inflated by
     third-party targets and moves with which interpreter the server resolved against (the audit
     measured 419 of 1 920 references targeting `.venv/**` with the project venv on `PATH`, and zero
     without it — same tree, same code, two figures; re-derive, do not quote); and
     `make_prefix_attributor`'s root-scoped fallback attributes such a target to any module whose
     `paths.module` is `.` — a value the Python discoverer really emits — producing a silent wrong
     edge **with no note**. *Change:* factor the skip set into a module-level constant and apply it to
     targets as well, counting those separately from `out-of-workspace` (e.g. a `vendor-tree` note) so
     the two causes stay distinguishable. ⛔ Do not fix this by narrowing the root-scoped fallback
     alone — the inflated count is the reachable defect and is independent of it. Fix this **with or
     before** G1: a wider search path resolves more third-party imports, so the inflation grows with
     G1.
     ⚠ This gap is **medium** — in its source entry, in its adversarial review, and here. Its entry
     names a trigger to raise it ("*…if the harvest is ever materialized for a project whose module
     set includes a root-scoped module*") and **this plan does not meet it**: D3 makes the harvest
     resolve imports but changes nothing about the module set, whose only producer emits
     `marketplace/bundles/{name}`, never `.`. See § Notes. Work it before or with G1 for the
     sequencing reason above, not because it is severe.
   - **G2 — a refusal reported as a timeout.** A JSON-RPC error reply to `initialize` (a server
     refusing the workspace) is caught by the `except client.LspError` arm and reported as
     `server-timeout: … did not respond within 10s (initialize failed: …)` — observed after 5.03 s,
     from a server that answered immediately. *Change:* split the arm; a JSON-RPC error response is a
     refusal, not a timeout. Give it `REASON_WORKSPACE_UNSUPPORTED` when it arrives from `initialize`,
     or a new `server-rejected:` prefix, and reserve the timeout reason for wait-expiry.
     ⚠ The two `LspError` shapes are distinguished only by message text unless the transport carries a
     discriminator. A typed field on `LspError` is the better fix but lives in **another bundle**
     (`lsp-client`) — do not reach across; if a typed discriminator is wanted, record it as a proposal
     (see D6) and implement the text-based split here with the fragility stated in the code comment.
   - **G3 + G6 — the lift does not use the seam the docstrings name.** `lsp_harvest.py` imports
     nothing from `_path_attribution_merge`; the lift uses `make_prefix_attributor(module_paths)`, a
     self-built longest-prefix table. That substitution is **necessary**, not a shortcut: live
     `merge_path_claims(discover_path_attributors(), …)` claims only `.claude` and `.plan`, and
     `lookup_claim('marketplace/bundles/…/scripts/y.py', claims)` returns `None` — routing through the
     seam would guarantee zero edges. Two docstrings assert the opposite (`lsp_harvest.py` near
     `:416-418`: *"the ``attribute`` callable is that seam's ``path -> owning module`` answer"*; the
     resolver's `extension.py` near `:113-115`: *"lifted to module granularity through the
     path-attribution seam"*). *Change (no decision required):* correct **both docstrings** to describe
     what the code does — a caller-supplied path-to-module lookup, supplied by
     `build_lsp_component_refs` as a discovery-derived longest-prefix table — and state the two
     obligations the substitute does **not** carry: the seam's ambiguous-ownership obligation (the
     prefix table's stable sort resolves an equal-length tie by iteration order, which
     `ext-point-path-attribution.md` explicitly forbids; not reachable today because bundle directory
     names are unique) and the vendor-tree exclusion G13 adds.
     ⛔ **Do not** publish `(marketplace/bundles/{bundle}, {bundle})` claims through `claim_paths()` in
     this run. That changes what `which-module` and the change-footprint classifiers answer for every
     `marketplace/bundles/**` path — a far wider blast radius than this resolver, and an operator
     decision. **Record it as a proposal** under D6 instead, with the blast radius and the
     `which-module` test suite named as the thing that must be verified first.

   *Done when:* (a) the baseline above is recorded in the run report with all four numbers, or its
   impossibility is recorded with the reason; (b) with G1 landed and a server available, a full-tree
   `build_lsp_component_refs` returns at least one reference whose two endpoints lie in **different
   bundles**, and a test asserts a **named** cross-bundle edge (e.g. `pm-dev-python → plan-marshall`)
   rather than a synthetic fixture edge — and if no server is available, the `extraPaths` plumbing is
   instead pinned by a stub-server test asserting the settings the harvest sends; (c) a test drives
   `harvest_workspace` over a workspace containing `.venv/lib/pythonX/site-packages/pkg/__init__.py`
   that a source file imports and asserts **no** resulting reference targets `.venv/`, and a second
   asserts `lift_to_modules` with `module_paths = {'alpha': 'alpha', 'rootmod': '.'}` and a `.venv`
   target produces **no edge**; (d) a stub server answering `initialize` with a JSON-RPC error yields
   a reason whose **prefix** (text before the first `:`) differs from all four existing prefixes;
   (e) neither docstring claims the Axis-D seam, and both name the mechanism the code invokes.

   ⛔ **(d) has a known trap, and the fix for it lives in a sibling plan.** The existing
   `test_every_failure_mode_states_a_distinct_reason` collects **whole interpolated strings** and
   asserts `len(reasons) == 4`; the strings already differ by interpolated binary name, so two modes
   can collapse onto one prefix and the test stays green — proved by mutation. Satisfying (d) against
   that test is satisfying a test that cannot fail. **Both branches are authored, so no decision is
   needed:** re-derive whether the test already asserts a **prefix set**. If it does (the sibling
   plan `550-test-suite-anti-vacuity` owns that change), **extend the expected prefix set with the new
   fifth prefix** and change nothing else. If it does not, convert it in this run — collect
   `reason.split(':', 1)[0]` per mode and assert set equality against the expected prefixes — and
   note in the run report that the conversion was made here, so the sibling plan reconciles rather
   than duplicates.

4. **D4 — The Python and npm discoverers stop reporting a missing capability as a measured absence**
   *Covers* `210-native-coordinate-resolvers/gaps.md#G1`, `#G10` (high), `#G11`, `#G2`, `#G3`, `#G4`
   (medium). Five of the six live in one function,
   `marketplace/bundles/plan-marshall/skills/build-pyproject/scripts/_pyproject_cmd_discover.py::_parse_pyproject_metadata`,
   which reads exactly one table of exactly one file; the sixth is its npm sibling
   `build-npm/scripts/_npm_cmd_discover.py::_extract_dependencies`.

   Every one of them ends at the same output: `{'id': 'pyproject', 'status': 'ok', 'edge_count': 0}`,
   which `client-api.md` defines as *"N resolvers ran and found nothing. The empty answer is a real,
   positive result"* and the user page renders as *"your modules genuinely declare no dependencies on
   each other"*. That is a misreport, not a documentation defect.

   - **G1 — Poetry.** The parser reads PEP 621 `[project]` and nothing else, so a project declaring
     `[tool.poetry] name` and `[tool.poetry.dependencies]` emits no name and no dependencies. Driven
     over a synthetic three-module Poetry monorepo: all three modules `metadata={} deps=[]`,
     `edges: ([], [])`. *Change:* fall back to `[tool.poetry]` when `[project]` is absent or carries
     no `name` — read `name` / `version` / `description`, and `tool.poetry.dependencies` (skipping the
     `python` key) plus `tool.poetry.group.dev.dependencies` into the `name:scope` list with the same
     `runtime` / `dev` scopes. A Poetry dependency **value** may be a string or a table; only the key
     is needed. ⚠ Make it a **strict** fallback that never fires when `[project]` is present —
     `metadata` and `dependencies` are read by consumers beyond edge derivation.
     ⚠ No claim is made here about how large the un-migrated Poetry population is; the audit measured
     none and neither should this run.
   - **G10 — setuptools.** `_find_descriptor_file` accepts `pyproject.toml`, `setup.cfg` **and**
     `setup.py`, so a setuptools module is admitted, stamped `build_systems: ['python']` and given a
     real `paths.descriptor` — pointing at a file `_parse_pyproject_metadata` never opens. The module
     enters the join's scope and contributes nothing, which is worse than being filtered out. Observed
     over a synthetic setuptools monorepo: `descriptor= lib_app/setup.cfg`, `metadata={} deps=[]`,
     `edges: ([], [])`. *Change:* fall back to `setup.cfg` — `[metadata] name`/`version`/`description`
     and each newline-separated `[options] install_requires` entry at scope `runtime`, through the same
     specifier strip. `configparser` is stdlib; no dependency is added.
     ⛔ `setup.py` is executable Python and is **not** statically parseable in general — do not attempt
     it. A `setup.py`-only module keeps today's behaviour, and that limit must be **stated** in
     `doc/user/dependency-intelligence.adoc` § Python specifics rather than left silent.
   - **G2 — PEP 508 direct reference.** The specifier-strip chain contains no `@`, so
     `m-core @ file:///./core` survives whole and the join reads `m-core @ file`. Observed: the edge
     vanishes, while the same modules with `m-core>=1.0` yield the edge — so the spelling alone
     destroys it. *Change:* split on the **bare** `@` before the specifier chain.
     ⛔ **The source gap's original prescription was wrong and the adversarial review corrected it:**
     PEP 508 does **not** require whitespace around the `@` (`urlspec = AT wsp* URI_reference`), and
     the reference implementation parses `m-core@file:…`, `m-core@ file:…` and `m-core @ file:…` all
     to `name='m-core'`. A `' @ '` split leaves the whitespace-free spelling — the one `pip freeze`
     emits — broken while passing a test written only for the spaced form. Splitting on the bare `@`
     is safe: `@` is not legal in a PEP 508 name, and an npm-style `@scope/` never appears in a Python
     requirement.
   - **G3 — PEP 508 environment marker.** The chain contains no `;`, so
     `m-core; python_version >= "3.11"` truncates at the first `>` to `m-core; python_version`. Worse
     than G2: the mangled key survives PEP 503 normalisation as a plausible-looking string, so nothing
     downstream can spot it. *Change:* split on `;` **first**, before the specifier chain. Same
     one-line fix window as G2, separate assertions.
   - **G11 — an unreadable descriptor is swallowed.** A bare `except Exception` returns the empty
     metadata/dependency pair, so a malformed descriptor is indistinguishable from one declaring
     nothing — and it kills the **dependent's** declared edge, since the target published no name.
     Observed over a two-module project with one unbalanced bracket. The npm side is not symmetric:
     its loader returns `None` and drops the module, a more visible outcome. *Change:* keep returning
     the empty pair (dropping the module is a larger behaviour change) but log a WARNING through the
     module's existing `log_entry` seam naming the file and the exception, and narrow the catch to
     `tomllib.TOMLDecodeError`, `OSError`, `UnicodeDecodeError` so an unexpected exception is not
     absorbed too.
   - **G4 — npm reads two of four dependency kinds.** `_extract_dependencies` iterates `dependencies`
     and `devDependencies` only, so `peerDependencies` — the idiomatic way a plugin package declares
     its dependency on a workspace's core package — and `optionalDependencies` produce no edge. The
     Python side **discloses** its analogous limit in the user page; the npm section carries no
     equivalent sentence, so the two ecosystems are documented asymmetrically for the same class of
     gap. ⛔ **No decision is required and none may be taken:** the extraction route widens what every
     npm module publishes and must be updated in lock-step across four scope-vocabulary sites, which
     is a scope call. **Take the disclosure route in this run** — add one paragraph to
     `doc/user/dependency-intelligence.adoc` § npm specifics and to `build-npm/SKILL.md` § Axis-C
     naming the two unread kinds and their consequence, matching the shape of the Python paragraph —
     and record the extraction route as a proposal under D6 with the four sites enumerated.

   *Done when:* (a) a new `poetry-monorepo` fixture whose modules declare names and inter-module
   dependencies **only** under `[tool.poetry]` yields a non-empty edge set through
   `BuildExtension.derive_edges`; (b) a new `setuptools-monorepo` fixture declaring them **only** in
   `setup.cfg` does the same; (c) both `sample-core @ file:///./sample_core` **and**
   `sample-core@file:///./sample_core` yield the same edge as `sample-core>=1.0.0`, each pinned by its
   own test; (d) `sample-core; python_version >= "3.11"` yields the same edge as `sample-core`;
   (e) discovering a module whose `pyproject.toml` is syntactically invalid emits a WARNING naming
   that file, and an exception outside the narrowed set propagates rather than being swallowed;
   (f) § Python specifics states that a `setup.py`-only module publishes no name, and § npm specifics
   states that `peerDependencies` and `optionalDependencies` produce no edge; (g) **the existing PEP
   621 fixture's exact edge-count assertion still passes unchanged** — re-derive that count from the
   test rather than trusting the figure recorded in the source gap.
   ⚠ Fixtures go under `test/plan-marshall/build-pyproject/fixtures/`, shaped like the existing
   `multi-module-python` one; re-derive its shape rather than reconstructing it from this text.

5. **D5 — The corpus language server survives a bad frame, resolves the right site, and never
   presents an unconfirmed one as exact**
   *Covers* `240-skill-lsp-server/gaps.md#G1`, `#G28` (high), `#G2`, `#G4`, `#G3` (medium). Owning
   surface: `marketplace/bundles/pm-plugin-development/skills/tools-corpus-language-server/scripts/`
   (`corpus_lsp.py`, `_corpus_lsp_protocol.py`, `_corpus_index.py`).

   - **G1 — one bad request kills the resident server and corrupts the stream.**
     `LspServer.handle` calls the handler with no `try`, and `serve` wraps nothing; `cmd_serve` runs
     under `@safe_main`, whose contract is TOON-on-stdout — correct for a verb, fatal for a stdio
     protocol channel. Reproduced end to end: `initialize`, then `textDocument/definition` on
     `file:///tmp/a%00b.md`, then a second `initialize` → process exits **1**, the third request is
     never answered, and stdout ends `…"textDocumentSync": 1}}}status: error\nerror: internal_error\n…`.
     The trigger is `Path.read_text` raising `ValueError` where the `except` catches only `OSError`
     and `UnicodeDecodeError` — but **any** handler exception has this shape. *Change:* wrap the
     handler call in `try/except Exception` and return a JSON-RPC error (`code -32603`) for a request,
     or swallow-and-log for a notification; wrap the `serve` loop body so one bad frame cannot end the
     session; give `serve` an entry path that does **not** go through `@safe_main`, or make the
     wrapper write to stderr for `serve`. Pair the boundary with a stderr log line so a swallowed
     exception cannot hide a real defect.
   - **G28 — the protocol layer discards `verified`.** `on_references` maps every reference through
     `_lsp_location(path, line)`, which emits only `uri` and `range`; the `verified` flag the index
     computed is dropped, and LSP has no weaker form than `Location`. The audit measured 162 of 5 020
     sites (3.2 %) unverified — **re-derive both numbers** — each reported against the owner's own
     file at the cited line. Demonstrated live through a running `serve`: an unverified inbound edge
     emitted `manage-architecture/SKILL.md` line 515, whose text never mentions the target. Two
     shipped pages promise the opposite in near-identical words: *"never presented as exact"*.
     ⛔ **The source gap says "pick one" of two options; this plan picks the one that needs no
     operator, and records the other.** Implement **option (a)**: omit `verified: false` sites from
     the `textDocument/references` response, which makes the shipped code satisfy the two documents
     already on `main` — the contract-conforming direction, and therefore not a contract change the
     run would be self-approving. Two constraints make it safe: the `query` verb **must keep**
     emitting every site with its `verified` flag (it already does, and it is the surface's only
     reachable consumer), and the references response must carry a count of the omitted sites (or the
     existing completeness note) so the omission is **visible** rather than a silent empty result —
     the defect class this epic exists to remove. Option (b) — keep emitting them and reword both
     pages to scope the promise to the `query` payload — is recorded as a proposal under D6 with its
     measured recall cost, because weakening a shipped guarantee is an operator's call.
   - **G2 — first candidate wins.** `CorpusIndex.resolve_reference_site` returns the first candidate
     file whose line at the cited number contains any expected token — owner-file first, then
     `sorted(rglob)` order, with no tie-break and no ambiguity signal. Reproduced on a synthetic
     corpus: a decoy prose line at line 5 of one file wins over the true citation at line 5 of
     another, `verified=True`. The audit's corpus scan found a minority of verified sites with more
     than one matching candidate and a larger minority winning on a **tail segment** alone rather than
     the full notation — re-derive both shares; they are the audit's own single-process measurement.
     *Change:* rank rather than take-first — prefer a line carrying the **full notation** over one
     carrying only the tail; on a tie, either report the owner file with `verified: false` or add an
     `ambiguous: true` field and document it. Some currently-`verified` sites will become unverified;
     that is the honest direction and it lowers the headline count.
   - **G4 — `initialize.rootUri` ignored.** The `initialize` handler ignores its `params` entirely;
     the project root comes only from `--project-path`, defaulting to the client's cwd — and the
     documented editor config an operator is told to write is the one most likely to omit the flag,
     whose failure is silent and looks exactly like a deliberate opt-out. *Change:* when the CLI
     project path resolved to nothing, resolve from `params['rootUri']`, falling back to `rootPath`
     then `workspaceFolders[0].uri`, and rebuild config/corpus resolution before returning
     capabilities. ⚠ Keep an explicit `--project-path` winning over `rootUri` so the documented block's
     behaviour is unchanged.
   - **G3 — nothing is invalidated on change.** The index is built once and never cleared; the line
     and candidate caches only grow; `did_open` / `did_change` / `did_close` touch only the document
     map. In a long-lived session every answer after the first edit is computed against a stale
     snapshot, and a newly created sub-document is invisible for the process's lifetime — while
     `SKILL.md` states that *"every reference site is re-read before it is reported"*.
     ⛔ **Take the disclosure half in this run, not the rebuild.** A rebuild costs a full index build
     (the audit's ~2.5 s figure was later shown to be measurement contention and re-measured lower —
     ⛔ **treat every timing in this plan as a lead to re-measure, never as an established fact**), and
     a debounce policy is a design decision with no operator to approve it. State the staleness bound
     explicitly in `SKILL.md`, the user page and the module docstring, beside the residency claim they
     sit next to, and record the invalidate-and-debounce design as a proposal under D6.

   *Done when:* (a) a subprocess test drives `initialize` → a request that raises inside the handler
   (the null-byte URI is the proved trigger; re-derive it) → a second `initialize`, and asserts the
   bad request gets a JSON-RPC error object, the following request is answered normally, the process
   exits 0, and **stdout contains only `Content-Length`-framed messages**; (b) driving a running
   `serve` over a corpus containing a known-unverified edge returns **no** `Location` for that edge,
   and the response carries the omitted-site count, with a test pinning both; (c) the synthetic decoy
   corpus resolves to the true citation file (or reports the site unverified/ambiguous), pinned by a
   test; (d) a subprocess test spawns `serve` with cwd **outside** the project and **no**
   `--project-path`, sends `initialize` with `rootUri` pointing at an enabled project, and receives
   the three providers; (e) `SKILL.md`, the user page and the module docstring each carry the
   staleness bound, and a test asserts the phrase is present in the skill contract.
   ⚠ The adversarial review's residual doubt names this exact area as the highest-yield next find:
   the **protocol projection** is thinner than the index beneath it and correspondingly under-tested,
   and `notation_at_position`'s URI-normalisation assumption (the document map is keyed by the
   client's raw URI string while `_lsp_location` emits a resolved one) is untested. Drive the new
   tests through a **running server**, not the index directly.

6. **D6 — One store, one meaning of `configured`; and four standing questions recorded, not decided**
   *Covers* `220-resolver-configuration/gaps.md#G9` (low), `240-skill-lsp-server/gaps.md#G10`,
   `#G25` (medium), `020-corpus-residency-admission-control/gaps.md#G12` (low), plus the three
   proposals D3, D4 and D5 hand to this deliverable.

   - **G9 — two readers of one store disagree.** The resolver roster computes
     `'configured': resolver_id in section` (`extension-api/scripts/extension_api.py`, near `:167`)
     while the store verb computes `configured = isinstance(entry, dict)`
     (`manage-run-config/scripts/run_config.py`, near `:871-877`). For a malformed entry such as
     `{"markdown": "yes"}` the roster reports `configured: true` and
     `derivation-resolver get --resolver markdown` reports `configured: false`; both report
     `enabled: true` (fail-open). The menu document instructs the agent to render `configured` as the
     distinction between "left at the default" and "deliberately set", so an operator is told two
     different things about one store. *Change:* adopt the **dict** definition in both readers (an
     entry counts as configured only when it is a dict) and pin it with a test on each side.
     *Done when:* a non-dict entry yields the same `configured` value from
     `extension_api.list_derivation_resolvers()` and `run_config.cmd_derivation_resolver_get`, pinned
     by a test in each file, and the two roster tests that assert `configured` on well-formed entries
     still pass — re-derive which tests those are.
   - **G10 — the D3 diagnostics deferral rests on an inverted premise.** The corpus server withholds
     editor diagnostics, hard-gated on validator-precision work — and that work **has landed**. The
     audit re-derived the unresolved set at **61 of 5 081 dependencies over 308 components**, against
     the ~380 of ~5 300 with "~97 % false positives" the gate reasoning was built on, and classified
     the 61 as **25 non-notations (41 %)** and **36 well-formed notations whose target does not exist
     (59 %)**. So the false-positive share has not merely drifted, it has **inverted**, and the
     majority of what remains is the class diagnostics exist to surface. ⛔ **Every figure in this
     paragraph is a lead: re-derive the unresolved set and its classification from the live validator
     before writing anything down.** *Change:* record the re-derived count and classification, and a
     **proposal** on whether to implement D3 (advertise `diagnosticProvider` and stream the
     validator's set) — with the argument on both sides and the criterion that would settle it. ⛔ Do
     **not** implement diagnostics in this run and do not declare the deferral upheld: advertising
     diagnostics binds the surface to the validator's precision, which is a scope and risk decision.
     *Done when:* a document in this plan's directory states the freshly re-derived unresolved count,
     its classification, and the proposal — and the run report names the command the numbers came
     from.
   - **G25 — the surface has no consumer.** An asserted **absence**, and therefore the highest-risk
     claim here: a tree-wide search finds `lspServers` in **no** bundle manifest, and no workflow,
     persona, phase skill or command invokes `preflight` or `query`. ⛔ **Re-derive that absence
     before acting on it** — search `marketplace/bundles/**` for `lspServers`, for `corpus_lsp`, and
     for the skill's own notation, and record what was searched and what was found. This epic has
     already built and removed one zero-adoption surface, so the condition that failure mode exists to
     prevent is reduced here, not met. ⛔ Wiring a consumer is a design decision with a real cost — any
     consumer paying a one-shot index build per call reintroduces exactly the cost the plan ruled out,
     so it must batch or run resident. **Record the decision, do not take it:** state the deliberate
     zero-consumer state, the candidate consumers (a plugin-doctor or outline step calling
     `query --kind references` instead of a Grep sweep), the batching constraint, and the review
     trigger that would reopen it. *Done when:* the re-derived absence and the decision record both
     exist in this plan's directory.
   - **G12 — a coordination note points at the wrong surface.** The residency plan's residue tells an
     eventual deliverable to coordinate with the `lsp-client` and to re-verify whether that or
     `manage-architecture` is the better home — a **code-facing** client — while a **corpus-facing**
     resident server has since shipped with the index, the resident cost model and the opt-in switch
     already solved. That server does **not** satisfy the deliverable: its index is
     component-granular, with no heading or anchor concept — `definition` returns the component's file
     at line 0 by explicit design, and `hover` returns description plus frontmatter. The note also
     predates the removal of the LSP query facade, so the "right home" question has more candidates
     than the two it names. *Change:* rewrite the coordination note to name
     `pm-plugin-development:tools-corpus-language-server` first, state what it does and does not
     answer, and frame the open question as **three-way** (extend that server with a section-granular
     request, extend `manage-architecture`'s content surface, or extend a `--section` verb) rather
     than two-way. ⚠ This edits a landed plan's report, which is a **dated record of one execution**:
     annotate or append the correction, do not rewrite history. *Done when:* the residue names
     `tools-corpus-language-server` with its granularity limit and poses the three-way question.
   - **The three handed-up proposals**, each recorded with its blast radius and the artifact that
     would settle it, and none implemented: (i) publishing marketplace-bundle prefixes as Axis-D
     path-attribution claims, which changes `which-module` and the change-footprint classifiers for
     every `marketplace/bundles/**` path (from D3); (ii) extending npm discovery to `peerDependencies`
     and `optionalDependencies`, which widens what every npm module publishes and requires four
     scope-vocabulary sites updated in lock-step (from D4); (iii) index invalidation with a debounce
     on `didChange` / `didSave`, and option (b) of the unverified-site question — keeping the sites in
     the references response and rewording the two pages instead (from D5).

   *Done when (deliverable-level):* one proposal document exists in this plan's directory carrying all
   items above; each names what would be changed, the blast radius, and the observation that would
   settle it; and **no proposal is acted on in this run**. The run report links it and states plainly
   that these were recorded, not decided.

## Out of scope

Each entry names its reason, because the executing run has no operator to ask and the written
boundary is the only thing standing between it and mid-run drift.

- **The test-vacuity gaps of these same source plans** — `200/G8`, `200/G12`, `200/G9`, `210/G5`,
  `210/G7`, `210/G6`, `240/G5`–`#G9`, `010/G6`, `220/G6`, `220/G7`. *Reason:* they are the scope of
  the sibling plan `550-test-suite-anti-vacuity`, and fixing them here would collide on the same test
  files. The single exception is the `200/G12` **prefix assertion**, which D3 must touch because its
  own *Done when* is otherwise satisfiable by a test that cannot fail — D3 authors both branches and
  reports which it took.
- **The documentation-surface gaps of these same source plans** — `200/G4`, `200/G5`, `200/G7`,
  `200/G11`, `210/G8`, `240/G11`–`#G24`, `240/G27`, `010/G7`–`#G10`, `010/G12`, `010/G16`,
  `220/G3`–`#G5`, `220/G8`, and the `020` report corrections. *Reason:* they are the scope of
  `560-documentation-surface-truthfulness`. This plan changes only the documentation that is
  **inseparable from a behaviour change it lands** — the fail-closed wording D1 adds, the
  `setup.py`/npm-kinds disclosures D4 adds, the staleness bound D5 adds, and the two docstrings D3
  corrects — because shipping the behaviour without them leaves a surface asserting the opposite of
  what it now does.
- **Making the `lsp` harvest reproducible across interpreters.** The harvest's reference count, three
  of its four notes and its wall-clock all move with which Python the server resolves against, and
  there is no `pythonPath` / `workspace/configuration` pinning. *Reason:* it is a residual doubt
  raised by the adversarial review, not a filed gap; D3 fixes the `.venv` **symptom** and must say in
  its report that it does not make the harvest reproducible.
- **Regenerating the tracked `.plan/project-architecture/` overlay** (`200/G10`). *Reason:* not in
  this plan's gap set, and the standalone lane never touches `.plan/`.
- **Removing or renaming the `errors_before` / `errors_after` payload fields.** *Reason:* consumers
  may already read them; D1 keeps them for continuity and adds the set-based fields alongside.
- **Adding a `manage-config` path for the `code_intelligence` section** (`240/G26`) and the
  `DependencyType` enum widening (`200/G9`). *Reason:* neither is in this plan's gap set, and both
  widen a surface beyond the defects here.
- **Implementing editor diagnostics on the corpus server, wiring it a consumer, publishing Axis-D
  claims for marketplace paths, widening npm discovery, and index invalidation.** *Reason:* each is a
  design or contract decision with a blast radius beyond this plan, and a cloud run has no operator to
  approve one. D6 records each as a proposal — that is the deliverable, and taking any of these
  decisions instead would be the failure it exists to prevent.

## Expected surface

Re-derive this list against the clone before relying on it; line numbers in this plan are leads.

- `marketplace/bundles/plan-marshall/skills/lsp-client/scripts/_lsp_jsonrpc.py` — the diagnostics
  return contract (D1).
- `marketplace/bundles/plan-marshall/skills/lsp-client/scripts/_lsp_workspace_edit.py` — per-file
  verdict, resource-operation surfacing, apply-loop rollback (D1, D2).
- `marketplace/bundles/plan-marshall/skills/lsp-client/scripts/lsp_client.py` — symbol rows, the
  edit/diagnose payloads, `ensure_open` (D1, D2).
- `marketplace/bundles/plan-marshall/skills/lsp-client/SKILL.md` — the fail-closed wording D1 requires.
- `marketplace/bundles/pm-plugin-development/skills/plan-marshall-plugin/scripts/lsp_harvest.py` —
  search path, target exclusion, failure-mode split, attribution docstring (D3).
- `marketplace/bundles/pm-code-intelligence/skills/plan-marshall-plugin/extension.py` — the resolver
  docstring (D3).
- `marketplace/bundles/plan-marshall/skills/build-pyproject/scripts/_pyproject_cmd_discover.py` —
  Poetry, `setup.cfg`, PEP 508 splits, narrowed catch (D4).
- `marketplace/bundles/plan-marshall/skills/build-npm/scripts/_npm_cmd_discover.py` and
  `build-npm/SKILL.md` — the npm disclosure (D4).
- `doc/user/dependency-intelligence.adoc` — the `setup.py` and npm-kind limits (D4).
- `marketplace/bundles/pm-plugin-development/skills/tools-corpus-language-server/scripts/`
  (`corpus_lsp.py`, `_corpus_lsp_protocol.py`, `_corpus_index.py`) and its `SKILL.md` +
  `doc/user/corpus-language-server.adoc` — D5.
- `marketplace/bundles/plan-marshall/skills/extension-api/scripts/extension_api.py` and
  `marketplace/bundles/plan-marshall/skills/manage-run-config/scripts/run_config.py` — the
  `configured` definition (D6).
- `doc/plans/code-intelligence-substrate/020-corpus-residency-admission-control/report-01.md` — the
  coordination-note correction (D6), appended as a correction, not a rewrite.
- `test/plan-marshall/lsp-client/`, `test/plan-marshall/build-pyproject/`,
  `test/plan-marshall/build-npm/`, `test/pm-plugin-development/plan-marshall-plugin/`,
  `test/pm-plugin-development/tools-corpus-language-server/` — the tests and fixtures.
- This plan's own directory — the proposal document and the D3 decision record (D6).

⛔ `.plan/` is git-ignored and **invisible from this run's clone**. Nothing in this plan requires
reading it; do not go looking for the orchestrator ledger, the plan specs or any landing record.

## Claim labels

Every premise below is a claim about the tree. `OBSERVED` means both the audit and its independent
adversarial re-review reproduced it **by execution**; `HYPOTHESIS` means it rests on reading, on a
single unreplicated run, or on a timing figure. Each `HYPOTHESIS` names an artifact reachable from a
fresh clone.

| Claim | Label | Confirm/refute artifact |
|---|---|---|
| The post-edit re-diagnose can return the pre-edit set, so a defective edit reports `success` with the defect on disk | OBSERVED | Drive `_run_edit` against a fake server whose post-`didChange` publish arrives after the settle window (`_lsp_jsonrpc.py::wait_for_diagnostics`) |
| The line count at which the stale read flips is machine- and load-dependent, not a constant | HYPOTHESIS (timing) | Two runs at different module sizes on the run's own machine; the test must not depend on a size |
| A server that answers `initialize` and never publishes yields a payload identical in every field to "clean" | OBSERVED | Stub server over the real `StdioTransport`; compare against a server publishing an empty diagnostic array |
| `errors_before`/`errors_after` are summed across the footprint, so a swapped or moved error passes | OBSERVED | Fake-transport `_run_edit` over a two-file footprint, pre 1+0 / post 0+1 |
| `workspace-symbol` rows carry no `path` while the server supplies `location.uri` | OBSERVED | Row keys from `_symbol_rows` vs the raw server response, with `references` rows as the control |
| `documentSymbol` results are not flattened, so methods are absent | OBSERVED | Lookup over a file with a class; compare shipped names against the raw response |
| `_run_edit` sends a second `didOpen` with no `didClose`, resetting the version | OBSERVED | Instrumented transport over a one-file `edit`; count `didOpen` / `didClose` |
| The apply loop leaves earlier files rewritten when a later one fails | OBSERVED | Three-file footprint with a malformed `TextEdit` on the middle file — ⛔ not `chmod`, which is inert as `root` |
| `normalize_changes`' resource-operation notes are computed and discarded by both callers | HYPOTHESIS (read) | A fake-transport test through `cmd_edit` with a `kind: rename` document change |
| The `lsp` harvest derives zero module edges on this repository because no cross-bundle reference resolves | OBSERVED | The gating baseline in D3 — a full-tree `build_lsp_component_refs` with an enabled binding |
| Harvest reference counts, note volumes and wall-clock move with which interpreter the server resolves against | OBSERVED (and therefore every such number is a lead) | Two full-tree runs, with and without the project venv first on `PATH` |
| A JSON-RPC error reply to `initialize` is reported under the timeout reason | OBSERVED | Stub server answering `initialize` with a JSON-RPC error; read the emitted reason prefix |
| The lift uses a self-built prefix table, not the Axis-D seam, and the seam would claim nothing for marketplace paths | OBSERVED | `lookup_claim('marketplace/bundles/…/scripts/y.py', merge_path_claims(discover_path_attributors(), …))` returns `None` |
| A Poetry-only and a `setup.cfg`-only project each derive nothing while the seam reports `status: ok, edge_count: 0` | OBSERVED | The two synthetic monorepo fixtures D4 adds |
| Both PEP 508 spellings (`@` direct reference, `;` marker) destroy the edge, and the bare-`@` split is the correct fix | OBSERVED | Same modules with a plain specifier as the control; the reference `Requirement` parser as the legality check |
| A malformed `pyproject.toml` is swallowed and kills the dependent's edge with no signal | OBSERVED | Two-module project with one unbalanced bracket |
| npm discovery reads only `dependencies` and `devDependencies` | HYPOTHESIS (read) | A fixture package declaring a sibling only under `peerDependencies`, asserted to yield no edge |
| One malformed request kills `serve` and writes TOON onto the frame stream | OBSERVED | The three-request subprocess probe in D5's *Done when* |
| `on_references` discards `verified`, so unconfirmed sites reach a client as exact `Location`s | OBSERVED | A running `serve` over a corpus with a known-unverified edge |
| `resolve_reference_site` takes the first matching candidate with no tie-break | OBSERVED | The synthetic decoy corpus |
| The shares of ambiguous and tail-only-matching verified sites | HYPOTHESIS (single measurement) | Re-run the corpus scan using the resolver's own candidate order and token test |
| The `initialize` handler ignores `params`, so `rootUri` is unused | HYPOTHESIS (read) | The subprocess test in D5's *Done when* (cwd outside the project, no `--project-path`) |
| Nothing invalidates the index or its caches on document change | HYPOTHESIS (read) | A `didChange` → re-query test; or the absence of any reset, re-derived by reading the three sync handlers |
| The validator's unresolved set is now ~61 of ~5 081, split ~25 non-notations / ~36 absent targets — inverting the ~97 %-false-positive premise | HYPOTHESIS (single re-derivation, and it drifts) | A fresh `resolve-dependencies validate --scope marketplace` run, classified |
| **Asserted absence:** no bundle manifest declares `lspServers` and no component invokes a `corpus_lsp` verb | HYPOTHESIS (asserted absence — the highest-risk claim here) | A recorded search of `marketplace/bundles/**` for `lspServers`, `corpus_lsp` and the skill's notation, with the search terms in the run report |
| The roster and the store verb compute `configured` differently, disagreeing on a non-dict entry | HYPOTHESIS (read) | A test with `{"markdown": "yes"}` asserting the two readers agree |
| The corpus server's index is component-granular, so it does not satisfy the residency plan's section-granular deliverable | OBSERVED | `_corpus_index.py`'s own statement that no intra-file position is recorded, plus a `definition` answer at line 0 |

⛔ **Timing figures are never established facts in this plan.** Every duration quoted in the source
gaps was taken in a tree where sibling agents were running full suites; one such figure was later
shown to be contention and re-measured materially lower. Any deliverable that needs a duration
re-measures it and reports the measurement conditions.

## Verification

Beyond each deliverable's *Done when*:

1. **Build gate.** This plan changes Python, so the full `./pw verify` runs, and its result — passed,
   failed, counts — is reported as measured, not as expected.
2. **CI portability is itself a check.** Re-run the whole suite with any language server hidden from
   `PATH` and confirm the new guards still fail against reverted code. A guard that only a
   locally-installed binary can falsify does not protect CI. Report the before/after counts.
3. **Red-then-green for every guard.** For each new test that pins a fixed defect, run it against the
   pre-change code and record the observed failure in the run report. The audits found three separate
   tests in these surfaces that read as strong invariants and could not fail; a new test asserted only
   green is not evidence.
4. **Cold read of the text that drives a reader.** Dispatch the pre-PR verification sub-agent to read
   **cold**, with no access to this plan, and report which reading it took:
   - the fail-closed sentence D1 adds to `lsp-client/SKILL.md` — does it read as **"verify by build"**
     or as **"the edit was wrong"**? Only the first is correct.
   - the D3 attribution docstrings — do they name the **Axis-D seam** or a **caller-supplied prefix
     table**? Only the second is correct.
   - the D5 staleness bound — does it read as **"answers may be stale after an edit"** or as
     **"answers are always re-read"**? Only the first is correct.
   - D6's proposal document — does it read as a **decision taken** or a **proposal recorded**? Only
     the second is correct.
   Any wrong reading is a wording failure, however complete the text looks; fix the wording and
   re-read.
5. **Collateral check.** Diff the branch against the expected surface above and account for every file
   outside it.
6. **Coverage statement.** The run report states, per gap id in § Gap coverage, whether it was
   discharged, recorded as a proposal, or halted with a reason. A gap silently absent from that
   statement is a defect in the run.

## Notes

**Sequencing against the sibling 5xx plans.** All eight 5xx plans fix gaps from the same audit, so
overlap is by file, not by subject.

- **`550-test-suite-anti-vacuity`** owns `200/G12` — the failure-mode distinctness test D3 must also
  touch. They collide on one test function. No ordering is required because D3 authors both branches
  (extend an existing prefix-set assertion, or convert the whole-string one) and reports which it
  took; whichever plan lands second reconciles, and the reconciliation is a one-line set membership.
  If both are in flight, prefer landing `550` first — then D3 only extends a set.
- **`560-documentation-surface-truthfulness`** owns the prose statements about the attribution seam
  (`200/G4`, `200/G5`), the corpus server's D3 figures (`240/G11`–`#G16`), and the lsp-client cost and
  state-table corrections (`010/G7`–`#G10`). This plan changes only documentation inseparable from a
  behaviour it lands. **If `560` lands first**, D3's docstrings and D6's recorded classification must
  not contradict what it wrote — read those files before writing. **If this plan lands first**, `560`
  should quote D6's re-derived numbers rather than re-deriving them a third time.
- No other 5xx plan is expected to touch these files. Re-derive that before assuming it: the bucket
  names are `510-architecture-store-query-truthfulness`, `520-measurement-and-cost-integrity`,
  `530-detector-and-auditor-integrity`, `540-finalize-dispatch-and-blocking-boundary-observability`,
  `570-cloud-plan-lane-contract-proposals`.

**Where a gap entry and its adversarial review disagree, the adversarial review wins.** It was the
later, evidence-bearing pass. Four places where that changes what this run does are already folded in
above and are listed here so they are not re-litigated: the PEP 508 `@` split must be on the **bare**
`@`, not `' @ '`; the mid-apply rollback test must **not** use `chmod`; and `240/G10`'s lean is
**presume the deferral needs reversing**, not upholding — while still recording rather than deciding.

⛔ **`200/G13` is MEDIUM. Do not raise it, and do not order D3 by pretending it is high.** Its entry
and its adversarial review both rate it medium, and they agree on why: the wrong-edge half "*is **not
reachable today*** — the harvest is materialized only by a discovery whose module paths are all
`marketplace/bundles/{name}` with no root-scoped module". The entry names a trigger for escalation —
"*Raise to high if the harvest is ever materialized for a project whose module set includes a
root-scoped module*" — and **D3 does not meet it.** That trigger is a conjunction, and D3 satisfies
only the first half: it makes the harvest resolve imports, and changes nothing about the module set.
Re-derived: `build_lsp_component_refs` has exactly one non-test caller, `plugin_discover.py`, whose
`module_paths` come from `build_bundle_module` and are always `marketplace/bundles/{name}` or the
bare bundle name — never `.`. That fact alone settles it; D3 could not put a root-scoped module into
`module_paths` whatever else it did.

An earlier draft of this plan raised G13 to high and justified it on that trigger. The justification
was false, and it quoted the refuting fact one sentence earlier. It is withdrawn; **the reason to
work G13 early is sequencing, not severity** — the vendored-target inflation grows with G1's wider
search path, so G13 lands before or with G1. Severity plays no part in that ordering.

**The source gap files are corroboration, not required reading.** Every citation of the form
`{plan}/gaps.md#G7` points at a git-tracked file under
`doc/plans/code-intelligence-substrate/{plan}/`, and each is quoted from and restated above so this
plan is self-sufficient. ⚠ A landed cloud plan's directory is **deleted at collect**, so a cited file
may be absent by the time this runs. That is expected and is not a blocker: proceed from the restated
content, and note the absence in the run report.

**No deliverable requires a decision this run cannot make.** Every point where the source gaps say
"pick one" or "decide and record" is authored either as the contract-conforming branch (D5's option
(a), D4's disclosure route, D3's docstring correction) or as a recorded proposal in D6. If the run
finds itself weighing two designs, that is a defect in this plan — record the choice as a proposal and
say so, rather than taking it.

## Gap coverage

Twenty-eight gaps across six source plans: **10 high, 16 medium, 2 low**. Every one is discharged by
a deliverable below; none is placed out of scope. Every severity here is the one its own entry
carries — this plan re-rates nothing. Re-derive all three figures from the `Severity` field of the
cited entries rather than trusting this line.

| Deliverable | Source plan | Gap ids | Severity |
|---|---|---|---|
| D1 | `010-lsp-in-execute-lookup-and-write` | G2, G13, G15 | high ×3 |
| D2 | `010-lsp-in-execute-lookup-and-write` | G1 | high |
| D2 | `010-lsp-in-execute-lookup-and-write` | G3, G4, G5, G14 | medium ×4 |
| D3 | `200-lsp-derivation-resolver` | G1, G2 | high ×2 |
| D3 | `200-lsp-derivation-resolver` | G3, G6, G13 | medium ×3 |
| D4 | `210-native-coordinate-resolvers` | G1, G10 | high ×2 |
| D4 | `210-native-coordinate-resolvers` | G2, G3, G4, G11 | medium ×4 |
| D5 | `240-skill-lsp-server` | G1, G28 | high ×2 |
| D5 | `240-skill-lsp-server` | G2, G3, G4 | medium ×3 |
| D6 | `240-skill-lsp-server` | G10, G25 | medium ×2 |
| D6 | `220-resolver-configuration` | G9 | low |
| D6 | `020-corpus-residency-admission-control` | G12 | low |

Totals: high 3+1+2+2+2 = 10; medium 4+3+4+3+2 = 16; low 2 — twenty-eight, matching the lead-in above
and the entries themselves. ⛔ Re-derive these totals against the table rather than trusting the
arithmetic here; an earlier revision left this line carrying the addends of a withdrawn severity
raise, contradicting its own table twenty lines up.
