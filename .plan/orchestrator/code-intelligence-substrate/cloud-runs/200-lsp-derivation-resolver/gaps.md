# Gaps — 200-lsp-derivation-resolver

The `lsp` resolver is registered, honest about its failure modes, and correctly refuses to guess an
owner — all mutation-proven. What it does not do is produce edges: driven over this repository with a
real enabled binding, the shipped engine harvests **1 501 repository file references** (1 920 when
pyright also resolves into the project's own `.venv`) and derives **zero** module edges, because
**not one cross-bundle reference resolves** — the marketplace's cross-bundle imports are bare imports
resolved by the generated executor's `sys.path`, which pyright at the workspace root cannot follow.
The zero-edge result reproduced on four whole-tree runs across two interpreter environments.
Alongside that, D2's stated mechanism (the Axis-D path-attribution seam) was silently replaced by a
bundle-local prefix table while three shipped documents still claim the seam is used, D3's fourth
failure mode is actively misreported as a timeout, the test that is supposed to catch such a collapse
cannot, and two claims in the run report's findings table are not true of the tree. Thirteen gaps
follow.

## G1 — Make the harvest resolve cross-bundle imports so the resolver derives non-zero edges

- **Kind:** bug
- **Severity:** high
- **Topic:** lsp/resolvers
- **Where:** `marketplace/bundles/pm-plugin-development/skills/plan-marshall-plugin/scripts/lsp_harvest.py:221-365` (`harvest_workspace`, server initialization); the resolver consuming it at `marketplace/bundles/pm-code-intelligence/skills/plan-marshall-plugin/extension.py:106`
- **Evidence:** `build_lsp_component_refs` over the repository root with `binding={'command': ['pyright-langserver','--stdio']}` and the real discovered module set, run three times in two interpreter environments:
  - with the project `.venv/bin` first on `PATH`: `ran=True files=1387 refcount=1920` / `modules with lsp refs: 0` / `unattributable-endpoint: 1372` / `self-edge: 548` / `unresolved-symbol: 5321` / `out-of-workspace: 12740`, in 56.0 s;
  - without it, twice, byte-identical results: `refcount=1501` / `modules with lsp refs: 0` / `unattributable-endpoint: 953` / `self-edge: 548` / `unresolved-symbol: 5731` / `out-of-workspace: 12764`, in 70.9 s and 83.8 s.
  The 419-reference difference is entirely references targeting `.venv/lib/python3.12/site-packages/**` (see G13). **`files_scanned=1387`, `self-edge=548` and `module edges = 0` are invariant across both.**
  Cross-bundle resolution measured directly: of the 1 920 resolved references, **0 have both endpoints in different bundles**. Direct probe of the cross-bundle import in `pm-dev-python/skills/plan-marshall-plugin/extension.py:19`:
  `'from extension_base import DerivationResolverBase, ExtensionBase' @col 5 -> UNRESOLVED` (all three positions: cols 27, 51, 5).
- **Why it matters:** the plan's Goal is "the module graph carries edges derived from actual symbol references for at least one language", and D1's *Done when* is "its edges appear in the store". On the only project where the harvest is materialized, the edge set is empty and always will be: no cross-bundle reference resolves, and every reference with both ends inside `marketplace/bundles/**` is intra-bundle (541 intra-directory + 7 cross-directory = the 548 self-edges). Enabling the binding today buys ≈ 60–85 s of crawl cost per run for nothing.
- **Action:** give the server the module search path the executor synthesizes. Either pass `python.analysis.extraPaths` (the set of every bundle skill `scripts/` directory) through the `workspace/configuration` reply the harvest can supply, or generate a transient `pyrightconfig.json` for the harvest root, or narrow the harvest's workspace root to a per-bundle subtree with that bundle's own path set. Whichever is chosen, keep the drop-and-note rule intact.
- **Done when:** a full-tree `build_lsp_component_refs` with an enabled binding returns at least one module in `refs` whose `target_bundle` differs from its own name, and a real-server test asserts a named cross-bundle edge (e.g. `pm-dev-python -> plan-marshall`) rather than a synthetic fixture edge.
- **Effort:** M
- **Risk if fixed:** a wider resolution surface means more resolved references, so `unattributable-endpoint` volume and harvest wall-clock both rise; the ≈ 60–85 s full-tree cost could grow. Wrongly-scoped `extraPaths` could resolve a name to the wrong bundle's copy of a same-named module and produce a confidently wrong edge — the exact outcome D2 exists to prevent, so pair this with a spot-check of the resulting edge set. Fix G13 first or alongside: a wider search path resolves *more* third-party imports, so the vendor-tree inflation grows with this change.

## G2 — Report a JSON-RPC error reply as its own failure mode, not as a timeout

- **Kind:** bug
- **Severity:** high
- **Topic:** lsp/resolvers
- **Where:** `marketplace/bundles/pm-plugin-development/skills/plan-marshall-plugin/scripts/lsp_harvest.py:327-338` (the `except client.LspError` arm) and the constant at `:105`
- **Evidence:** stub server replying to `initialize` with `{'code': -32603, 'message': 'workspace not supported by this server'}` produces
  `ran=False reason="server-timeout: …python3 did not respond within 10s (initialize failed: {'code': -32603, 'message': 'workspace not supported by this server'})"` after 5.03 s — the server responded immediately.
- **Why it matters:** D3 requires that "each failure mode produces a distinct stated reason". A server-side workspace rejection — D3's own fourth mode — is delivered under the third mode's reason string, telling the operator the binary is unresponsive when it explicitly refused. This is the "stated-but-wrong reason … worse than a silent one because it looks considered" class the run itself flagged twice (findings 3 and 15) and then shipped a third instance of.
- **Action:** split the `LspError` arm and give the refusal a **new `server-rejected:` reason**. A JSON-RPC error response (the transport raises `LspError(f'{method} failed: …')` from `_lsp_jsonrpc.py:197`) is a server refusal, not a timeout; reserve `REASON_SERVER_TIMEOUT` for the wait-expiry path (`_lsp_jsonrpc.py:193`). ⚠ Do **not** reuse `REASON_WORKSPACE_UNSUPPORTED` here, even though its wording fits: that constant already belongs to the pre-launch no-sources check at `:267-269`, so reusing it would make two distinct causes share one prefix — the same collapse this gap exists to end — and it would leave the failure-mode count at four, contradicting the *Done when* below. A fifth prefix is the outcome this entry selects.
- **Done when:** a negative control driving a stub server that answers `initialize` with a JSON-RPC error yields a reason whose **prefix** (the text before the first `:`) is `server-rejected` and differs from all four existing prefixes, and `test_every_failure_mode_states_a_distinct_reason` asserts five distinct *prefixes* — `{'server-absent', 'server-failed-to-start', 'server-timeout', 'workspace-unsupported', 'server-rejected'}`. ⚠ Asserting five distinct whole strings is not enough — see G12: the current four-string assertion stays green when two modes are collapsed onto one prefix, because the strings still differ by interpolated binary name. Fix G12 first or this *Done when* is satisfiable by a test that cannot fail.
- **Effort:** S
- **Risk if fixed:** the two `LspError` shapes are distinguished only by message text unless the transport is taught to carry a discriminator; a text match is brittle. Prefer adding a typed field to `LspError` in `lsp-client` — but that is another bundle's surface, so coordinate rather than reach across.

## G3 — Route the lift through the Axis-D path-attribution seam, or state plainly that it does not

- **Kind:** incomplete
- **Severity:** medium
- **Topic:** lsp/resolvers
- **Where:** `marketplace/bundles/pm-plugin-development/skills/plan-marshall-plugin/scripts/lsp_harvest.py:552` (`attribute = make_prefix_attributor(module_paths)`) and `:566-594`
- **Evidence:** `lsp_harvest.py` imports nothing from `_path_attribution_merge`; `merge_path_claims` / `lookup_claim` appear nowhere in either bundle. The seam itself claims nothing under the marketplace: live `merge_path_claims(discover_path_attributors(), …)` returns only `{'prefix': '.claude', …}` and `{'prefix': '.plan', …}`, and `lookup_claim('marketplace/bundles/pm-dev-java/skills/x/scripts/y.py', claims)` → `None`.
- **Why it matters:** D2 states "The lift goes through the path-attribution seam" and the plan's Notes make it a ⛔ hard gate — "without a trustworthy path-to-module answer the lift guesses". The lift uses a self-built longest-prefix table instead. That substitution is *necessary* (the seam would attribute nothing, so routing through it would guarantee zero edges) — which makes it a genuine finding about the seam's coverage, not a shortcut. It was neither disclosed in the run report nor recorded as residue.
- **Also:** the substitute does not satisfy the seam's own **ambiguous-ownership obligation**. `make_prefix_attributor` sorts by `len(prefix)` with a stable sort, so two modules whose `paths.module` normalize to equal-length prefixes are separated by whichever the `module_paths` dict yielded first — resolution by iteration order, which `ext-point-path-attribution.md` § The ambiguous-ownership obligation explicitly forbids ("MUST NOT resolve the disagreement by iteration order"), requiring no claim instead. Not reachable in the marketplace today (bundle directory names are unique), so this is a property of the substitute rather than a live defect — but it is part of what "state plainly that it does not use the seam" has to say.
- **Action:** decide and record. Either have `pm-plugin-development` publish `(marketplace/bundles/{bundle}, {bundle})` claims through `claim_paths()` so the seam can answer and the lift can call `lookup_claim`, or keep `make_prefix_attributor` and state in the engine, the concepts page and the resolver standard that the lift uses a discovery-derived prefix table rather than the Axis-D seam, with the reason and with the two obligations it does not carry (ambiguous ownership, and the vendor-tree exclusion of G13).
- **Done when:** either `lsp_harvest.py` calls `lookup_claim` over merged Axis-D claims and the drop tests still pass, or all three sites named in G4/G5/G6 describe the mechanism actually used and name the ambiguous-ownership divergence.
- **Effort:** M
- **Risk if fixed:** publishing marketplace-bundle prefixes as Axis-D claims changes what `which-module` and the change-footprint classifiers answer for every `marketplace/bundles/**` path — a much wider blast radius than this resolver. Verify against the `which-module` test suite before landing.

## G4 — Correct the concepts page's claim that the lift uses the path-attribution seam

- **Kind:** doc-defect
- **Severity:** medium
- **Topic:** documentation-surface
- **Where:** `doc/concepts/code-intelligence.adoc:113`
- **Evidence:** "The lift between them goes through the path-attribution seam, and its important behaviour is the case where it produces nothing".
- **Why it matters:** this is the page D5 exists to make precise, and it names a mechanism the shipped code does not use. A reader auditing the substrate would look for Axis-D claims behind the `lsp` edges and find none.
- **Action:** replace with the mechanism actually used (a longest-prefix table over the discovered module directories), or make the claim true via G3.
- **Done when:** the sentence names the mechanism `lsp_harvest.py:552` actually invokes.
- **Effort:** S
- **Risk if fixed:** none.

## G5 — Correct the resolver standard's claim that the lift uses the path-attribution seam

- **Kind:** doc-defect
- **Severity:** medium
- **Topic:** bundle-docs
- **Where:** `marketplace/bundles/plan-marshall/skills/extension-api/standards/ext-point-derivation-resolver.md:231`
- **Evidence:** "…lifts its file-granular references to module granularity through the path-attribution seam; an endpoint no module owns yields no edge and a note rather than a guessed module."
- **Why it matters:** the extension-point standard is the contract document an implementor reads. Stating that a shipped implementor consumes Axis-D when it does not misleads the next resolver author into believing the seam covers marketplace paths.
- **Action:** as G4 — describe the discovery-derived prefix table, or make the claim true via G3. The second half of the sentence (drop-and-note) is accurate and should stay.
- **Done when:** the roster row describes the attribution mechanism the code uses.
- **Effort:** S
- **Risk if fixed:** none.

## G6 — Correct the engine and resolver docstrings that name the path-attribution seam

- **Kind:** doc-defect
- **Severity:** medium
- **Topic:** lsp/resolvers
- **Where:** `marketplace/bundles/pm-plugin-development/skills/plan-marshall-plugin/scripts/lsp_harvest.py:416-418` and `marketplace/bundles/pm-code-intelligence/skills/plan-marshall-plugin/extension.py:113-115`
- **Evidence:** `lsp_harvest.py` — "The lift goes through the path-attribution seam — the ``attribute`` callable is that seam's ``path -> owning module`` answer". `extension.py` — "its references were lifted to module granularity through the path-attribution seam".
- **Why it matters:** the docstring asserts that the injected callable *is* the seam's answer; the only caller injects `make_prefix_attributor`. A maintainer reading either docstring would look for the wrong integration point.
- **Action:** describe the callable as a path-to-module lookup the caller supplies, and name what `build_lsp_component_refs` actually supplies.
- **Done when:** neither docstring claims Axis-D, or G3 makes both true.
- **Effort:** S
- **Risk if fixed:** none.

## G7 — Add the missing `lsp` kind to `module-discovery.md`'s second `dep_type` enumeration

- **Kind:** doc-defect
- **Severity:** medium
- **Topic:** bundle-docs
- **Where:** `marketplace/bundles/plan-marshall/skills/extension-api/standards/module-discovery.md:348`
- **Evidence:** "every element must carry all three of `target_bundle`, `dep_type` (one of `script` / `skill` / `import` / `path` / `implements`), and `resolved`" — five kinds. The same file's line 161 was corrected and does list `lsp`.
- **Why it matters:** report finding 12 records this as **Fixed**; it is half-fixed. The remaining line is in the normative "must carry" clause, so an implementor following it would treat an `lsp` entry as contract-violating.
- **Action:** add `lsp` to the parenthetical at `:348`, or replace the inline list with a cross-reference to `:161`.
- **Done when:** `grep -n "script. / .skill. / .import. / .path. / .implements" module-discovery.md` returns no line lacking `lsp`.
- **Effort:** S
- **Risk if fixed:** none.

## G8 — Pin the truncation/partiality note with a regression test

- **Kind:** test-gap
- **Severity:** medium
- **Topic:** tests
- **Where:** `marketplace/bundles/pm-plugin-development/skills/plan-marshall-plugin/scripts/lsp_harvest.py:294,313,349-353`; test file `test/pm-plugin-development/plan-marshall-plugin/test_lsp_harvest.py`
- **Evidence (mutation, not grep):** replacing `truncated = True` at `:313` with `pass` leaves **all 50 tests in both plan test files green**. That is the direct proof; the grep this entry previously cited was inaccurate — `out-of-workspace` does appear once in `test_lsp_harvest.py:198`, in a *docstring*, with no assertion behind it. `grep -rn "truncat\|harvest-budget" test/` is genuinely empty for both plan test files. Report finding 24 records the inner-loop truncation flag as **Fixed**, and finding 24's whole point is that truncation inside the last file previously exited the loop normally and reported a partial harvest as complete.
- **Why it matters:** the fix is exactly the kind that silently regresses — deleting `truncated = True` at `:313` restores the original defect and no test notices. A partial harvest reported as complete is a confident wrong answer at edge-set scale.
- **Action:** add a test driving `harvest_workspace` with a `timeout_s` small enough to expire mid-file (a slow stub server plus a multi-import source file) and assert a note starting `harvest-budget:`; add a second asserting `out-of-workspace:` fires when a definition resolves outside the root.
- **Done when:** deleting `truncated = True` at `:313` makes at least one test fail.
- **Effort:** M
- **Risk if fixed:** a timing-dependent test can flake; drive the deadline deterministically (monkeypatch `time.monotonic`) rather than by sleeping.

## G9 — Add a negative control and roster entry for the `lsp` dep type in the sibling resolvers' tests

- **Kind:** test-gap
- **Severity:** low
- **Topic:** tests
- **Where:** `marketplace/bundles/pm-plugin-development/skills/tools-marketplace-inventory/scripts/_dep_detection.py:25-32` (`DependencyType`) and the sibling resolvers' "everything else is ignored" tests
- **Evidence:** `DependencyType` still enumerates exactly five members (`SCRIPT_NOTATION`, `SKILL_REFERENCE`, `PYTHON_IMPORT`, `RELATIVE_PATH`, `IMPLEMENTS`); no `lsp`. The sibling resolvers derive their ignore-populations from that enum, so none of them is asserted to ignore an `lsp` reference.
- **Why it matters:** this is the run's own declared residue and it is the "test fixture that still passes" shape — the behaviour is correct today but unasserted, so a future resolver that widened its kind set would silently claim `lsp` edges and forfeit provenance.
- **Action:** update the **authoritative** definition first, then let the tests derive from it. Add an `lsp` member to `DependencyType` — it is a real `dep_type` in the `component_refs` contract, so the enum is incomplete — and leave each sibling resolver's ignore-population derived from that enum, as `test/pm-plugin-development/plan-marshall-plugin/test_markdown_derivation_resolver.py:55` already does (`ALL_DEP_TYPES = frozenset(member.value for member in DependencyType)`). Do **not** hard-code `'lsp'` into each sibling test: that creates a second list mirroring a set defined elsewhere, the drift-prone shape this repository treats as a defect in its own right, and it is what let the two populations diverge here. Where a sibling test still restates the kind set literally, convert it to the derived form in the same change.
- **Done when:** `DependencyType` declares `lsp`; every sibling resolver's ignore-population is derived from `DependencyType` rather than restated, so a future member reaches all of them without further edits; and at least one test per sibling resolver asserts that a `dep_type: 'lsp'` reference yields no edge and no note from that resolver. An independently hard-coded `'lsp'` in a test does **not** satisfy this criterion.
- **Effort:** S
- **Risk if fixed:** adding an enum member may widen the detection engine's own behaviour if any code iterates `DependencyType` to decide what to scan — check call sites before adding.

## G10 — Refresh the tracked `.plan/project-architecture/` overlay for the new bundle

- **Kind:** omission
- **Severity:** medium
- **Topic:** architecture-core
- **Where:** `.plan/project-architecture/_project.json:2`; missing `.plan/project-architecture/pm-code-intelligence/enriched.json`
- **Evidence:** `git ls-files --error-unmatch .plan/project-architecture/_project.json` → tracked. Its description still reads "It ships **ten** production bundles…". `ls .plan/project-architecture/` lists ten bundle directories plus `default`; every sibling bundle has an `enriched.json` and `pm-code-intelligence` has no directory at all.
- **Why it matters:** this subtree is in git, so the staleness ships to every clone. A consumer reading `_project.json` is told the marketplace has ten bundles when it has eleven, and the eleventh has no curated overlay while all its siblings do. The run declared this as residue and deliberately left it, reasoning from the lane contract's "never touches `.plan/`" — a statement the run itself showed rests on the false premise that all of `.plan/` is git-ignored.
- **Action:** regenerate the overlay on a machine that can run the crawl (or hand-add the `pm-code-intelligence/enriched.json` matching its siblings' shape) and correct the `_project.json` description. Separately, carve the tracked portion out of the lane contract's `.plan/` prohibition so the next run is not blocked by the same false premise.
- **Done when:** `_project.json` names eleven bundles and `.plan/project-architecture/pm-code-intelligence/enriched.json` exists.
- **Effort:** S
- **Risk if fixed:** a full regeneration rewrites every module's overlay and could clobber hand-curated `enriched.json` content; prefer a targeted addition plus the one-line description fix.

## G11 — Correct the "every bundle declares its domain identity" claim

- **Kind:** doc-defect
- **Severity:** medium — raised from low. The calibration puts "a false claim in shipped documentation" at medium and reserves low for a cosmetic inconsistency; this is a false universal statement about the one required extension hook, on the concepts page, and it is the same class as G4/G5/G6, which are all medium.
- **Topic:** documentation-surface
- **Where:** `doc/concepts/extension-architecture.adoc:16`
- **Evidence:** "The required hook is `get_skill_domains()` — every bundle declares its domain identity and organises its skills by profile". `pm-code-intelligence` returns `[]` (`extension.py:51-60`) and ships no skills organised by profile; `ext-point-domain-bundle.md:116-121` and `extension-contract.md:67` both correctly record it as the no-domain case.
- **Why it matters:** the same file's line 14 was updated to "eleven production bundles" by this run, so the sentence now over-claims about a bundle the run itself added. Two adjacent standards already state the correct rule, so the concepts page is the outlier.
- **Action:** qualify — e.g. "every bundle implements `get_skill_domains()`; a bundle contributing an edge set rather than skills returns none".
- **Done when:** the sentence admits the no-domain case, matching `ext-point-domain-bundle.md:116-121`.
- **Effort:** S
- **Risk if fixed:** none.

## G12 — Make the failure-mode distinctness test able to fail

- **Kind:** test-gap
- **Severity:** medium
- **Topic:** tests
- **Where:** `test/pm-plugin-development/plan-marshall-plugin/test_lsp_harvest.py:421-448` (`test_every_failure_mode_states_a_distinct_reason`)
- **Evidence:** the test builds `reasons = {…four fully-interpolated reason strings…}` and asserts `len(reasons) == 4`. The four strings already differ by the interpolated `{binary}` — `definitely-not-a-real-language-server-xyz`, the unlaunchable stub's path, and `sys.executable` — so two modes can share a reason *prefix* and the set still has four members. Proven by mutation: rewriting `REASON_SERVER_ABSENT` (`lsp_harvest.py:103`) to `'server-failed-to-start: {binary} could not be launched'`, so the absent and failed-to-start modes report the same stated reason, leaves this test **green**; the only red is `test_absent_server_reports_ran_false_with_a_stated_reason` (`:285`), which asserts `startswith('server-absent:')`.
- **Why it matters:** D3's *Done when* is literally "each failure mode produces a distinct stated reason", and this is the test named for it — in the run report (finding 3's note: "it saw two distinct reasons where it required four") and in the audit. The property is in fact pinned only by the four separate per-mode `startswith` controls, which nothing ties to the count of modes: adding a fifth mode without a fifth control would leave the collapse undetected. This is the same shape as report finding 20 — a test that reads as a strong invariant and asserts a weaker one that cannot fail for the stated reason.
- **Action:** assert on the reason *prefix* rather than the whole string — e.g. collect `reason.split(':', 1)[0]` for each mode and assert the set equals the expected prefix set (`{'server-absent', 'server-failed-to-start', 'server-timeout', 'workspace-unsupported'}`), so both a collapse and an unexpected extra prefix fail.
- **Done when:** rewriting `REASON_SERVER_ABSENT` to carry the `server-failed-to-start:` prefix makes `test_every_failure_mode_states_a_distinct_reason` fail.
- **Effort:** S
- **Risk if fixed:** asserting an exact prefix set couples the test to the reason vocabulary, so G2's new fifth mode must be added to it in the same change — which is the intended coupling, not a cost.

## G13 — Exclude vendor and virtualenv trees from the harvest's reference *targets*

- **Kind:** bug
- **Severity:** medium — the reachable half misreports a diagnostic count rather than an edge; the wrong-edge half is not reachable through the only shipped producer. Raise to high if the harvest is ever materialized for a project whose module set includes a root-scoped module.
- **Topic:** lsp/resolvers
- **Where:** `marketplace/bundles/pm-plugin-development/skills/plan-marshall-plugin/scripts/lsp_harvest.py:396-397` (`_within`), against the skip set at `:210` (`_candidate_files`); the root-scoped fallback at `:588-591` (`make_prefix_attributor`)
- **Evidence:** `_candidate_files` excludes `.git`, `node_modules`, `target`, `.venv`, `venv`, `__pycache__`, `.plan` from the files it *queries*; `_within` applies no filter at all to what a definition resolves *to*. Measured on this repository with the project `.venv/bin` first on `PATH`, so pyright resolves third-party imports against it: **419 of 1 920 harvested references (22%) target `.venv/lib/python3.12/site-packages/**`, and all 419 land in the `unattributable-endpoint` note — 31% of its 1 372 total.** Re-run without the venv on `PATH`: 1 501 references, 953 suppressions, 0 references targeting `.venv`. Same tree, same code, two figures.
  The latent half, demonstrated directly:
  ```text
  module_paths = {'alpha': 'alpha', 'rootmod': '.'}
  make_prefix_attributor(module_paths)('.venv/lib/python3.12/site-packages/pytest/__init__.py') -> 'rootmod'
  lift_to_modules([('alpha/x.py', '.venv/.../pytest/__init__.py')], attribute, module_paths)
    -> EDGES [('alpha', 'rootmod')]   NOTES []
  ```
  `paths.module == '.'` is a real discovered value, not a hypothetical: `marketplace/bundles/plan-marshall/skills/build-pyproject/scripts/_pyproject_cmd_discover.py:159` reads `is_root = relative_path == '.'`.
- **Why it matters:** two things. (1) The `unattributable-endpoint` count is presented to an operator as "references no module owns" and is a third noise on this tree — and which third depends on which interpreter pyright picked up, so the number is not a property of the repository. (2) In a Python project with a root-scoped module *plus* a sub-module and a project-local `.venv`, every third-party import becomes a real edge into the root module, emitted **with no note**, because the root-scoped fallback claims whatever nothing else claims. That is the confidently-labelled wrong edge D2's ⛔ exists to prevent, produced silently and at volume — the plan's own stated worst outcome.
- **Action:** apply the same exclusion to targets that `_candidate_files` applies to sources. Factor the skip set out of `_candidate_files` into a module-level constant and have `_within` (or the call site at `:322-325`) reject any target whose path relative to the root intersects it, counting those separately from `out-of-workspace` (e.g. a `vendor-tree` note) so the two causes stay distinguishable. Do **not** fix this by narrowing the root-scoped fallback alone — the inflated count is the reachable defect and is independent of it.
- **Done when:** a test drives `harvest_workspace` over a workspace containing a `.venv/lib/pythonX/site-packages/pkg/__init__.py` that a source file imports, and asserts the resulting `references` contain no pair whose target is under `.venv/`; and a second test asserts that `lift_to_modules` with `module_paths = {'alpha': 'alpha', 'rootmod': '.'}` and a `.venv` target produces no edge.
- **Effort:** S
- **Risk if fixed:** the harvested reference count drops (here by 419), so any figure recorded from a previous run stops matching — expected, and the point. Excluding `target/` as a target could also drop legitimate references in a project that builds generated sources into it; if that matters, make the target-side skip set narrower than the source-side one rather than sharing it verbatim.
