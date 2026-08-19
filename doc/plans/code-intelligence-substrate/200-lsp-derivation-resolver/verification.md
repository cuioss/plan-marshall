# Verification — 200-lsp-derivation-resolver

**Audited:** `plan.md`, `report-01.md`
**Tree state:** first pass at `7a3f11d`; adversarially re-verified at `a90adeb`, both on `claude/code-intelligence-substrate-analysis-kah884`. `git diff --name-only 7a3f11d..a90adeb -- '*.py'` is empty, so every code measurement below is comparable across the two.
**Overall verdict:** PARTIALLY REFUTED

The machinery landed and is honest about its own failure modes. What it does not do is the thing the
plan's Goal names: on the one repository where the harvest is materialized, the shipped resolver
derives **zero** module edges. D2's stated mechanism (the path-attribution seam) was not used and the
substitution is undisclosed. D3's fourth failure mode is not merely narrow — a genuine server-side
rejection is actively misreported as a timeout.

## Deliverable verdicts

| # | Deliverable (short) | Report claim | Ground truth | Verdict |
|---|---|---|---|---|
| D0 | GATE: headless batch harvest within budget | "Confirmed by execution"; 200 files / 14.12 s / 229 intra-repo refs | Re-derived live: 200 files / **15.0–17.1 s** / **249** intra-repo refs; 1387 candidate `*.py` under root; measured full crawl **56–84 s** (not the linear extrapolation — index cost is paid once) | CONFIRMED |
| D1 | LSP-backed derivation resolver on the shipped seam | "Done"; "the resolver runs through the existing seam and its edges appear in the store" | Seam registration real (`discover_derivation_resolvers()` returns `lsp` among 7); `lsp_harvest` status reaches all 11 bundle modules through `discover_project_modules`. **But a full-tree harvest with an enabled binding yields 0 module edges** — reproduced four times across two interpreter environments | PARTIAL |
| D2 | File-to-module lift through the path-attribution seam | "Verified by the drop case" | Drop case genuinely verified (mutation-proven). **The lift does not use the Axis-D seam** — it uses a bundle-local `make_prefix_attributor`; three shipped documents say otherwise | PARTIAL |
| D3 | Lifecycle + honest failure, one negative control per mode | "Four lifecycle failure modes, each with its own negative control and a distinct stated reason" | Four controls exist and pass; distinctness is mutation-resistant. **A server that answers `initialize` with a JSON-RPC error — including "workspace not supported" — is reported `server-timeout: … did not respond within 10s`** | PARTIAL |
| D4 | Configuration inside the shared surface, no parallel mechanism | "The shared binding is now the only switch" | Confirmed: no `config_defaults` override, zero `pm_code_intelligence.*` keys anywhere in the tree, `resolve_binding()` reads `lsp_client.resolve_language_server()` | CONFIRMED |
| D5 | Documentation: resolver, tier ladder, lifecycle rationale | "Tier 2 is `PARTLY BUILT`… Tier 0's `SUBPROCESS-FREE` becomes `BY DEFAULT`" | Confirmed verbatim in `doc/concepts/code-intelligence.adoc:19-31,42-51,80-121`. Three residual false/stale statements found (seam claim ×2, `dep_type` enumeration ×1) | PARTIAL |

## Per-deliverable detail

### D0 — GATE: can a server be driven headlessly to completion in batch?

- **Required (plan):** "a batch harvest has been driven end-to-end and its timing recorded, **or** the premise is refuted."
- **Claimed (report):** `pyright-langserver` 1.1.408 present; 10 files / 402 requests / 2.29 s and 200 files / 3 864 requests / 14.12 s; boot 0.34–0.46 s; ≈ 90 s extrapolated over 1 248 tracked `*.py`.
- **Found:** `pyright-langserver` at `/root/.local/bin/pyright-langserver`. Re-derived with the *shipped* engine (`harvest_workspace`, `file_budget=200`) against the repository root:
  ```
  candidate *.py under root (after skip list): 1387   (== `git ls-files '*.py' | wc -l`)
  elapsed=17.08s ran=True files_scanned=200 intra-repo refs=249   (first pass)
  elapsed=15.01s ran=True files_scanned=200 intra-repo refs=249   (independent re-run)
  ```
  and over `build-maven/scripts` (the report's spot-check workspace): `ran=True files_scanned=6 refs=6` in 1.7–3.2 s, the same six pairs both times.
- **Checks run:** four live harvests through the shipped code path (two bounded probes, two whole-tree); all completed, none timed out.
- **Verdict:** **CONFIRMED.** The premise holds and the recorded order of magnitude is reproducible; the file count is 249 on both passes, and only wall-clock moves.
- ⚠ **Correction to this document's own first pass.** It reported a linear extrapolation — "1387 candidate files ⇒ ≈ 118 s full crawl" — while its *own* D1 probe had already measured the whole-tree harvest at 60.4 s. The extrapolation is wrong in kind, not merely in value: `initialize` builds the index once, so per-file cost falls as the budget grows. Measured whole-tree harvests here: **56.0 s / 70.9 s / 83.8 s** across three runs. The honest statement is that a full crawl costs roughly a minute to a minute and a half on this tree, and that the 200-file probe over-predicts it by about 1.5–2×.
- ⚠ **Timing on this gate is machine-load-dependent and the reference counts are interpreter-dependent** (see D1). Neither figure should be quoted without its environment.

### D1 — an LSP-backed derivation resolver

- **Required (plan):** "the resolver runs through the existing seam **and its edges appear in the store**"; "⛔ No new extension point".
- **Claimed (report):** Done; "No extension point was added, and the seam was not widened"; the transport is reused, not reimplemented.
- **Found:**
  - Registration: `marketplace/bundles/pm-code-intelligence/skills/plan-marshall-plugin/extension.py:48` — `class Extension(ExtensionBase, DerivationResolverBase)`, `derivation_resolver_id()` at `:87-89`. Discovery confirmed live: `discover_derivation_resolvers()` returns `['documentation', 'lsp', 'markdown', 'maven', 'npm', 'pyproject', 'python']`.
  - Seam untouched: `git show c86de8b --stat` lists no `extension_base.py`; the only `ext-point-derivation-resolver.md` change is 5 lines in § Current implementations.
  - Transport reuse: `lsp_harvest.py:272,290,307,315` drive `client.StdioTransport` / `client.LspSession` from `plan-marshall:lsp-client`; the module's only LSP-specific code is `import_positions` (`:155-191`).
  - Status propagation: `plugin_discover.attach_lsp_references` (`:585-616`) stamps every module; the field survives `discover_project_modules` — verified live, `lsp_harvest=True` on all 11 bundle modules.
  - **Edges in the store — refuted in practice.** Driving the shipped `build_lsp_component_refs` over the repository root with a real enabled binding and the real discovered module set:
    ```
    elapsed=56.0s ran=True files=1387 refcount=1920
    modules with lsp refs: 0
    notes:
      - out-of-workspace: 12740 reference(s) resolved outside the project root and own no module
      - unresolved-symbol: 5321 position(s) the server could not resolve to a definition
      - unattributable-endpoint: 1372 suppressed [...]
      - self-edge: 548 suppressed [plan-marshall -> plan-marshall; ...]
    ```
    **Every figure above was independently re-derived and every one holds — but only in one interpreter environment, and this document must say which.** Re-run with the project's own `.venv/bin` first on `PATH` (so pyright resolves against `.venv`), the six figures reproduce exactly. Re-run without it, twice, deterministically:
    ```
    ran=True files_scanned=1387 refcount=1501   modules with lsp refs: 0
      - out-of-workspace: 12764   - unresolved-symbol: 5731
      - unattributable-endpoint: 953   - self-edge: 548
    ```
    The whole difference is **419 references whose target is a file under `.venv/lib/python3.12/site-packages/`** (1920 − 419 = 1501; 1372 − 419 = 953, exactly). Those are third-party library files that happen to sit inside the project root, so `_within` admits them (`:396-397`) even though `.venv` is skipped as a *source* (`:210`). See Correctness review item 6.
    **Invariant across both environments:** `files_scanned` = 1387, `self-edge` = 548, **module edges = 0**. The zero-edge headline does not depend on the environment; the diagnostic counts do.
    Root cause confirmed by direct probe (reproduced verbatim): the marketplace's cross-bundle imports are *bare* imports resolved by the generated executor's `sys.path`, which pyright at the workspace root cannot follow. Asking the shipped positions of `marketplace/bundles/pm-dev-python/skills/plan-marshall-plugin/extension.py:19`:
    ```
    'from extension_base import DerivationResolverBase, ExtensionBase' @col 27 -> UNRESOLVED
    'from extension_base import DerivationResolverBase, ExtensionBase' @col 51 -> UNRESOLVED
    'from extension_base import DerivationResolverBase, ExtensionBase' @col  5 -> UNRESOLVED
    ```
  - ⚠ **Correction to this document's own first pass.** It stated: "Every reference pyright *can* resolve is intra-directory, hence intra-bundle, hence a self-edge (548 of them)." That is false, and it was the stated root cause for the headline gap. Measured over the 1 920 resolved references: **1 172 are not intra-directory**; 878 of the 1 501 repository references target `test/`, which is outside `marketplace/bundles/` entirely; and 7 of the 548 self-edges are cross-*directory* within one bundle, not intra-directory. What is actually true, and is what the conclusion rests on:
    - **cross-bundle references that resolve: 0** (both environments) — so no `marketplace/bundles/**` pair can ever produce an edge;
    - every reference with *both* ends inside `marketplace/bundles/**` is intra-bundle (541 intra-directory + 7 cross-directory), hence a self-edge;
    - every suppressed `unattributable-endpoint` is unattributable at its **source** end (953 of 953 without the venv; 1 372 of 1 372 with it) — never only at its target — because the attribution table holds only the eleven `marketplace/bundles/{name}` prefixes, so any source under `test/`, `.claude/`, `marketplace/targets/`, `.venv/` or the repository root is unowned by construction.
    Zero edges is therefore structural, not incidental — the conclusion survives, but the reason stated in the first pass did not.
- **Verdict:** **PARTIAL.** Mechanism, seam discipline and transport reuse are all as claimed. The literal *Done when* clause "its edges appear in the store" is unmet on the only project where the harvest is materialized, and the plan's Goal ("the module graph carries edges derived from actual symbol references") is unmet with it.

### D2 — the file-to-module lift

- **Required (plan):** "The lift goes through the path-attribution seam"; "⛔ A reference whose endpoint cannot be attributed produces NO edge and a note — never a guessed module"; *Done when:* "an unattributable endpoint produces a note and no edge, asserted by test." Plan Notes add: "⛔ **The attribution seam is a hard gate for D2**."
- **Claimed (report):** "`lift_to_modules()` maps file-granular references to module pairs. An endpoint the attribution seam cannot attribute yields **a note and no edge**… Verified by the **drop** case."
- **Found:**
  - Drop rule: `lsp_harvest.py:445-460`. Tests `test_unattributable_endpoint_produces_note_and_no_edge` (`test_lsp_harvest.py:64`) and its source twin (`:84`).
  - **The seam is not used.** `build_lsp_component_refs` builds its own attributor: `lsp_harvest.py:552` — `attribute = make_prefix_attributor(module_paths)` (`:566-594`). `lsp_harvest.py` imports nothing from `_path_attribution_merge`; `merge_path_claims` / `lookup_claim` appear nowhere in the bundle.
  - The substitution is not merely stylistic — it is load-bearing. The Axis-D seam claims nothing under `marketplace/bundles/**`. Live:
    ```
    {'prefix': '.claude', 'module': 'pm-plugin-development', ...}
    {'prefix': '.plan',   'module': 'plan-marshall', ...}
    marketplace/bundles/pm-dev-java/skills/x/scripts/y.py -> None
    ```
    Had the lift gone through the seam as specified, *every* endpoint would be unattributable. The deviation is what makes the lift able to attribute anything at all — and it is undisclosed in the report.
  - Three shipped documents assert the seam is used: `doc/concepts/code-intelligence.adoc:113`, `marketplace/bundles/plan-marshall/skills/extension-api/standards/ext-point-derivation-resolver.md:231`, and the code's own docstrings (`lsp_harvest.py:420-422`, `extension.py:115`).
- **Checks run (mutation, re-run independently):** replaced the drop branch with a leading-directory guess plus `known.add(...)`, then ran the **whole** file:
  ```
  FAILED test_unattributable_endpoint_produces_note_and_no_edge
  FAILED test_unattributable_source_endpoint_produces_note_and_no_edge
  FAILED test_suppression_notes_are_aggregated_with_a_count
  3 failed, 31 passed
  ```
  The three named failures are exactly those the first pass reported; its "3 failed, 6 passed" tail was a `-k`-scoped subset and is restated here against the full 34-test population so the reading is reproducible. File restored from byte snapshot (`/tmp/adv-200-lsp-derivation-resolver-mutsweep/`); `git status --porcelain` clean for it.
- **Verdict:** **PARTIAL.** The refuses-to-guess behaviour is real and non-vacuously tested. The stated mechanism — the plan's own hard gate — was replaced by a bundle-local prefix table, and three shipped documents state the opposite.

### D3 — server lifecycle and its honest failure modes

- **Required (plan):** "A server that is absent, fails to start, times out, or does not support the workspace must produce 'resolver ran: no' with a stated reason"; *Done when:* "each failure mode produces a distinct stated reason, verified with a negative control per mode"; "⛔ none may yield a zero-edge success."
- **Claimed (report):** four modes, four controls, plus `test_every_failure_mode_states_a_distinct_reason` and `test_no_failure_mode_reports_a_zero_edge_success`.
- **Found:** reason constants at `lsp_harvest.py:99-106`; controls at `test_lsp_harvest.py:285` (absent), `:312` (bad-shebang spawn failure → real `OSError`), `:352` (unresponsive), `:371` (no sources). Distinctness assertion at `:421-448`, anti-zero-success at `:451-471`. All pass.
  - **Defect:** the `except client.LspError` arm (`lsp_harvest.py:327-338`) formats `REASON_SERVER_TIMEOUT` for *every* protocol failure, including a server that answered promptly with a JSON-RPC error. Probe against a stub server that replies to `initialize` with `{'code': -32603, 'message': 'workspace not supported by this server'}`:
    ```
    SERVER-ERROR-RESPONSE  elapsed=5.03s ran=False
      reason="server-timeout: …python3 did not respond within 10s
              (initialize failed: {'code': -32603, 'message': 'workspace not supported by this server'})"
    ```
    The server *did* respond. This is D3's fourth mode — a genuine server-side workspace rejection — arriving under the *third* mode's reason string. `REASON_WORKSPACE_UNSUPPORTED` (`:106`) can only ever fire from the pre-launch no-sources check at `:267-269`.
  - Same arm, second case: a server that starts and dies is reported after the full handshake budget (`SERVER-CRASHES-ON-BOOT elapsed=10.00s … 'server-timeout: … did not respond within 10s (timed out waiting for response to initialize)'`). Here the wording is literally true; the test at `:328` documents the collapse in its own docstring.
- **Checks run (mutation, re-run independently):** reverted `_candidate_files`' relative-path fix (`:213` → `path.parts`), whole file:
  ```
  FAILED test_workspace_under_a_skip_named_directory_is_still_harvested
  1 failed, 33 passed
  ```
  Restored from snapshot; clean. (The first pass's "1 failed, 1 passed" was again a scoped subset.)
- **Checks run (mutation, new — the distinctness assertion itself):** rewrote `REASON_SERVER_ABSENT` to carry the `server-failed-to-start:` prefix, collapsing two of the four modes onto one stated reason. `test_every_failure_mode_states_a_distinct_reason` **stayed green**; only the per-mode control `test_absent_server_reports_ran_false_with_a_stated_reason` went red. See Test adequacy — the distinctness assertion does not pin the property it names.
- **Both probes re-run independently and reproduced verbatim**, including the reason strings and the ≈5 s / 10.0 s elapsed readings. (The 5 s on the rejecting stub is the `shutdown` request in `transport.close()` timing out, not the rejection itself; the rejection is returned in milliseconds.)
- **Verdict:** **PARTIAL.** No mode yields a zero-edge success — the archetype the plan targets is genuinely eliminated. But "each failure mode produces a distinct stated reason" fails for the fourth mode as the plan words it, and the reason produced is affirmatively wrong rather than merely coarse — the same "stated-but-wrong reason" class the run itself flagged twice (findings 3 and 15). The test that would have caught a collapse cannot (see Test adequacy).

### D4 — configuration

- **Required (plan):** supply language-server settings *within* the shared resolver-configuration surface; "⛔ MUST NOT ship a parallel config mechanism"; if the owning plan has not landed, record the coupling and define the minimum.
- **Claimed (report):** first cut shipped three `pm_code_intelligence.lsp.*` keys and was corrected; the shared `language_servers` binding is now the only switch; off-by-default falls out of the store being git-ignored.
- **Found:**
  - `grep -rn "pm_code_intelligence"` over the whole tree returns exactly one hit — a test module name (`test_lsp_derivation_resolver.py:27`). No config keys survive.
  - No `config_defaults` override: `extension.py:76-81` is a comment stating the omission; `test_bundle_ships_no_configuration_mechanism_of_its_own` (`test_lsp_derivation_resolver.py:222-235`) asserts `extension_type.config_defaults is ExtensionBase.config_defaults`.
  - Single switch: `resolve_binding()` (`lsp_harvest.py:485-508`) calls `client.resolve_language_server(language)`; `attach_lsp_references` (`plugin_discover.py:612`) passes its result straight through.
  - Coupling recorded: `run-config-standard.md:218-227` § "Two consumers, one switch", including the ⚠ that configuring a language also switches on a whole-workspace per-crawl harvest.
  - Off-by-default verified live: `discover_plugin_modules` on this clone reports `"ran": false, "reason": "not-configured: no enabled language_servers binding for python in the run-configuration store"`.
- **Verdict:** **CONFIRMED.**

### D5 — documentation

- **Required (plan):** the resolver on the concepts page, the tier-ladder correction, the lifecycle rationale; "⚠ State precisely what is and is not built."
- **Claimed (report):** Tier 2 `PARTLY BUILT`, Tier 0 `SUBPROCESS-FREE BY DEFAULT`, lifecycle section explains why the batch harvest and live client stay separate.
- **Found:** all three present and precise — `code-intelligence.adoc:19-31` (ladder), `:40-51` (both routes named, "Call graphs and type relations are not built by either", the no-persisted-symbol-store caveat), `:80-121` (§ The language server as a derivation resolver, § Why this is separate from the live lookup client, § What the protocol does not offer, § The lift, § Honest failure). `doc/concepts/README.adoc:29` carries the qualified Tier 0 wording. The topology SVG's derivation-resolver card reads `7 impls · Active`. `pm-plugin-development`'s SKILL.md `:89` discloses that `discover_modules()` boots a language server.
- **Residual defects:**
  - `module-discovery.md:348` still enumerates `dep_type` as "one of `script` / `skill` / `import` / `path` / `implements`" — five kinds. Finding 12 fixed only the other site (`:161`, which does list `lsp`).
  - `code-intelligence.adoc:113` and `ext-point-derivation-resolver.md:231` both state the lift goes "through the path-attribution seam". It does not (see D2).
  - `doc/concepts/extension-architecture.adoc:16` — "every bundle declares its domain identity and organises its skills by profile" — is false for `pm-code-intelligence`, which returns `[]` from `get_skill_domains()` by design. The same file's line 14 alt text was updated to "eleven".
- **Verdict:** **PARTIAL.** The deliverable's substance landed; three enumerating/mechanism statements are wrong.

## Correctness review

Read in full: `lsp_harvest.py` (595 lines), `pm-code-intelligence/.../extension.py` (203 lines), `plugin_discover.attach_lsp_references`, and the consuming `_lsp_jsonrpc.StdioTransport` / `LspSession`.

1. **`lsp_harvest.py:327-338` — a responding server is reported as a non-responding one.** Every `LspError` (timeout, EOF-on-dead-server, *and* a JSON-RPC error reply) is formatted with `REASON_SERVER_TIMEOUT`. Failing input: any server that rejects `initialize`. Consequence: the operator is told the binary "did not respond within 10s" when it responded in milliseconds with a reason; D3's fourth mode is unreachable for real server-side rejections. Evidence: probe output under D3.
2. **`lsp_harvest.py:566-594` — `make_prefix_attributor` resolves an equal-prefix tie by iteration order.** Two modules whose `paths.module` normalize to the same prefix land at the same sort key; `sorted(..., key=len, reverse=True)` is stable, so the winner is whichever the `module_paths` dict yielded first. The Axis-D seam this function stands in for explicitly forbids exactly that ("MUST NOT resolve the disagreement by iteration order", `ext-point-path-attribution.md` § The ambiguous-ownership obligation) and emits no claim instead. Not reachable in the marketplace today (bundle directories are unique), so the consequence is latent.
3. **`lsp_harvest.py:381-393` vs `:396-397` — the definition target is not `resolve()`d while the root is.** `root = Path(project_root).resolve()` (`:255`) but `_path_from_uri` returns the server's path verbatim (`:393`). A workspace reached through a symlink makes `_within` false for in-workspace targets, silently inflating the `out-of-workspace` count. Not observed on this tree.
4. **`extension.py:151-154` — two guards that cannot fire from the shipped producer.** `unresolved-target` requires `resolved: false` and `unknown-endpoint` requires a target outside `derived_by_name`; `build_lsp_component_refs:556-559` only ever emits `resolved: True` targets drawn from `module_paths`. Both are defensible defensive guards against a future producer and are unit-tested with synthetic input; recorded for completeness, not as a defect.
5. **`plugin_discover.py:616` shares one `status` dict object across every module.** Benign today (the map is serialized, never mutated per module), but an in-place edit on one module's record would silently rewrite all of them.
6. **`lsp_harvest.py:396-397` — vendor and virtualenv trees are skipped as reference *sources* but admitted as reference *targets*.** `_candidate_files` (`:210`) excludes `.git`, `node_modules`, `target`, `.venv`, `venv`, `__pycache__`, `.plan` from the files it queries; `_within` applies no such filter to what a definition resolves *to*. Measured consequence on this tree: with the project `.venv` on `PATH`, **419 of the 1 920 harvested references (22%) and 419 of the 1 372 `unattributable-endpoint` suppressions (31%) are files under `.venv/lib/python3.12/site-packages/`** — third-party libraries, not repository code. The reported suppression volume therefore depends on which interpreter pyright happened to pick up, which is why this document had to state its environment in D0/D1.
   **The latent half is worse than the reported half.** `make_prefix_attributor`'s fallback (`:588-591`) gives a root-scoped module (`paths.module` of `.` or `''`) whatever nothing else claims. `_pyproject_cmd_discover.py:159` emits exactly that value (`is_root = relative_path == '.'`), so in a Python project with a root module *plus* at least one sub-module, every third-party import under a project-local `.venv` becomes a real edge into the root module — **with no note at all**. Demonstrated:
   ```
   module_paths = {'alpha': 'alpha', 'rootmod': '.'}
   attribute('.venv/lib/python3.12/site-packages/pytest/__init__.py') -> 'rootmod'
   lift_to_modules([('alpha/x.py', '.venv/.../pytest/__init__.py'), ...]) -> EDGES [('alpha','rootmod')]  NOTES []
   ```
   That is the confidently-labelled wrong edge D2's ⛔ exists to prevent, produced silently and at volume. It is **not reachable today** — the harvest is materialized only by `pm-plugin-development`'s marketplace discovery, whose module paths are all `marketplace/bundles/{name}` with no root-scoped module — which is why it is filed at medium rather than high. Filed as G13.

No fail-open branch, off-by-one, or unguarded `None` was found in the edge path. `import_positions` correctly handles `node.level` (`:190`), star imports (`:182-183`), and unparseable sources (`:172-175`); the three shipped positions and their column offsets (27 / 51 / 5 for `from extension_base import DerivationResolverBase, ExtensionBase`) were re-derived by hand and match.

## Test adequacy

| Deliverable | Covering tests | Non-vacuity evidence |
|---|---|---|
| D0 | `test_end_to_end_harvest_against_a_real_server`, `test_end_to_end_materialization_produces_lsp_component_refs` (`test_lsp_harvest.py:575,599`) | Both **ran** here (pyright present; 50 passed, 0 skipped). The materialization test carries the post-finding-20 non-empty guards (`assert refs, …`, exact-shape equality at `:630`) |
| D1 | `test_discovery_attaches_a_harvest_status_to_every_module` (`:533`); resolver units in `test_lsp_derivation_resolver.py` | Integration test asserts the anti-vacuity invariant rather than an environment state; independently corroborated by my live `discover_project_modules` run |
| D2 | `:64`, `:84`, `:98`, `:111`, `:124`, `:137`, `:156`, `:170`, `:180` | **Mutation-proven** — a guessing lift turns 3 of them red |
| D3 | `:285`, `:312`, `:328`, `:352`, `:371`, `:385`, `:407`, `:421`, `:451`, `:474` | **Partly mutation-proven.** Reverting the relative-path skip fix turns `test_workspace_under_a_skip_named_directory_is_still_harvested` red — but that pins the skip list, not D3's *Done when*. The distinctness assertion at `:421` is **vacuous with respect to the property it names** (below); the four per-mode `startswith` controls are what actually pin it |
| D4 | `test_bundle_ships_no_configuration_mechanism_of_its_own` (`test_lsp_derivation_resolver.py:222`), `test_unconfigured_language_reports_itself_and_runs_nothing` (`test_lsp_harvest.py:501`) | Identity assertion against `ExtensionBase.config_defaults` cannot pass against an override |
| resolver zero-guard | `test_project_with_no_harvest_record_anywhere_says_so` (`test_lsp_derivation_resolver.py:176`) | **Mutation-proven** — disabling the `if derived_by_name and not saw_status` branch (`extension.py:160`) turns it red |

**Gaps in coverage:**

- **`test_every_failure_mode_states_a_distinct_reason` (`:421-448`) does not test distinctness of the failure *modes*.** It builds a `set` of four fully-interpolated reason strings and asserts `len(reasons) == 4`. Those four strings already differ by the interpolated binary name (`definitely-not-a-real-language-server-xyz`, the unlaunchable stub path, `sys.executable`), so two modes can share a reason *prefix* and the set still has four members. **Mutation-proven:** rewriting `REASON_SERVER_ABSENT` to `'server-failed-to-start: {binary} could not be launched'` — collapsing the absent and failed-to-start modes onto one stated reason — leaves this test **green**; only `test_absent_server_reports_ran_false_with_a_stated_reason` (which asserts `startswith('server-absent:')`) goes red. The named property is pinned by the four per-mode controls, not by the test that claims it. Filed as G12.
- **No test pins the truncation/partiality note** that finding 24 claims fixed. `grep -rn "truncat\|harvest-budget" test/` returns no hit in either plan test file; `harvest_workspace`'s `truncated` flag (`:294,313,349-353`) and the `out-of-workspace` / `unresolved-symbol` / `unreadable` notes (`:299,355-357`) are all unasserted. **Mutation-proven:** replacing `truncated = True` at `:313` with `pass` leaves all **50 tests green**.
- **No test exercises the real tree's edge outcome.** The only real-server materialization test uses a synthetic two-package workspace pyright resolves. Nothing would have gone red when the repository's own harvest produced zero edges.
- **No negative control for a server-side `initialize` rejection** (the D3 residue item), which is why defect 1 above shipped.

All 50 tests in the two files pass on this tree (first pass 51.34 s; re-run here 47.88 s / 48.69 s). Restoration after every mutation was byte-exact — first pass from `/tmp/verify-200-mutsweep/`, this pass from `/tmp/adv-200-lsp-derivation-resolver-mutsweep/`, both written back by hand with `cp` and md5-verified; no `git checkout` / `restore` / `stash` was used, and `git status --porcelain` shows no modification to `lsp_harvest.py` or `extension.py` afterwards.

## Report accuracy

Claims verified true against the tree now: the resolver id and bundle rationale; "no extension point was added and the seam was not widened" (no `extension_base.py` in the commit); the transport reuse; finding 2 (`test/pm-code-intelligence/` carries no bundle-level `__init__.py`, matching `test/pm-dev-python/`); finding 3 (`:213` matches relative); finding 4 and 13 (`EXPECTED_RESOLVER_IDS` and `AXIS_A_RESOLVER_IDS` in `test_graph_family_bundle_project.py:62,83` both carry `lsp`; `_PRODUCTION_BUNDLES` in `test_extension_discovery.py:511-523` carries `pm-code-intelligence` at `:513`; `EXPECTED_MANIFEST_COUNT = 11` in `test/marketplace/test_plugin_license.py:20` — a different file from the one the first pass implied); finding 8 and 17 (no `pm_code_intelligence` key survives); finding 14; finding 15 (`_path_from_uri:381-393`); finding 22 (`run-config-standard.md:218-227`); finding 23 (`test_definition_uri_is_percent_decoded`, `test_non_file_uris_are_ignored`); finding 25 (one `## Configuration` section); finding 26 (`7 impls · Active`); finding 27.

Claims that are false, stale, or overstated:

- **"Finding 12 … `module-discovery.md` enumerates `dep_type` as exactly five kinds; `lsp` is a sixth — **Fixed**".** Only one of the two enumerations was fixed. `module-discovery.md:348` still reads "`dep_type` (one of `script` / `skill` / `import` / `path` / `implements`)".
- **§ Correctness spot-check: "Population: all **6** references the shipped engine derived… **Result: 6/6 correct**".** Reproducible exactly — I re-ran it and got the same 6 pairs including `_maven_cmd_discover.py -> _maven_execute.py`, whose deferred import is at `_maven_cmd_discover.py:555`. But the plan asked for a sample of **derived edges**, and what was sampled is **file references** over a synthetic single-directory workspace root. No derived *module edge* was verified, because on the real module set there are none. The section's framing ("sampling derived edges") overstates what was checked.
- **§ Residue: "a cross-check of `lsp` edges against `python` edges (where the union should show heavy corroboration)"** presupposes that `lsp` edges exist. Measured: zero.
- **Finding 24's "Fixed — truncation is tracked and reported wherever it occurs"** is true of the code and untrue of the test suite; no regression test pins it (see Test adequacy).
- **Finding 5 / `CLAUDE.md` counts** were accurate at merge — re-derived independently from the eleven `plugin.json` manifests at `c86de8b`: 11 bundles, 153 skills, 2 agents, 2 commands, 157 total. They have since drifted (now **154 / 158**) through a later plan's added skill. Recorded as drift, not as this run's defect. (Counting `skills/*/SKILL.md` on disk instead gives 156, i.e. two skills exist that no manifest registers — outside this plan's scope, noted so the two populations are not confused.)
- **Build-gate counts (19 708 / 19 986 passed)** were not re-run — out of scope per the audit brief. **UNVERIFIABLE.**
- **Reviewer-participation section** — the PR-thread and bot-comment claims are not reachable from this clone. **UNVERIFIABLE.**

## Declared residue — current status

| Residue item (from report) | Still open? | Evidence |
|---|---|---|
| D3's fourth mode is narrower than the plan names it | **Open, and worse than stated** | `REASON_WORKSPACE_UNSUPPORTED` fires only from the pre-launch no-sources check (`lsp_harvest.py:267-269`); a real server-side rejection is misreported as `server-timeout` (probe under D3) |
| `lsp` and live-lookup share a binding but not a health check | **Open** | `lsp_harvest` does its own `shutil.which` (`:264`); `lsp_client` has `cmd_preflight`; neither consults the other |
| `.plan/project-architecture/` is TRACKED and left stale | **Open** | `git ls-files --error-unmatch .plan/project-architecture/_project.json` → tracked. `_project.json:2` still says "ten production bundles"; `ls .plan/project-architecture/` shows no `pm-code-intelligence/` while all ten siblings have one |
| Sibling resolvers not asserted against the new `lsp` dep type | **Open** | `_dep_detection.py:25-32` — `DependencyType` still has exactly five members, no `lsp` |
| Repository-wide precision unmeasured | **Open, and superseded** | Not "unmeasured" — measured here at **zero edges** in both interpreter environments, so precision is undefined rather than unknown |
| Enabling a language enables two things at once | **Open, disclosed** | `run-config-standard.md:218-227` carries the two-consumers table and the ⚠ |
| One language only | **Open by design** | `HARVEST_LANGUAGE = 'python'` (`lsp_harvest.py:86`); `import_positions` is Python-specific |
| Harvest off by default, unexercised in CI | **Open** | Live check on this clone: `"ran": false, "reason": "not-configured: …"` |

## Out-of-scope and collateral

No out-of-scope work found. The run did **not** edit the query layer (`git show c86de8b --stat` touches no `_cmd_client_query.py`), did not build live symbol pass-through, did not ship a parallel configuration mechanism, and did not widen the seam. Multi-language coverage was not attempted. Collateral edits (counts, rosters, topology SVG, `installation.adoc`) are all declared in the report's findings table and each is confirmed present.

## Method and coverage

**Checked by reading:** `plan.md`, `report-01.md`, the epic README; `lsp_harvest.py`, `pm-code-intelligence` `extension.py` / `README.md` / `SKILL.md` / `plugin.json`, `plugin_discover.attach_lsp_references`, `_lsp_jsonrpc.py` (`StdioTransport`, `LspSession`), `lsp_client.py` head; both test files in full; `code-intelligence.adoc`, `ext-point-derivation-resolver.md`, `ext-point-path-attribution.md`, `module-discovery.md`, `run-config-standard.md`, `extension-architecture.adoc`, `extension-contract.md`, `ext-point-domain-bundle.md`, `README.md`, `installation.adoc`, the topology SVG.

**Checked by execution:**
- `pytest` on both plan test files — 50 passed, 0 skipped (real-server tests exercised). Run three times across the two passes.
- **Five mutations.** Three prove a named guard non-vacuous (D2 drop rule, `_candidate_files` relative match, resolver `saw_status` branch) — all three re-run in the second pass with identical red sets. Two prove the *opposite*: deleting `truncated = True` (`:313`) leaves 50 green, and collapsing `REASON_SERVER_ABSENT` onto the `server-failed-to-start:` prefix leaves the distinctness test green. Byte snapshots taken to `/tmp/verify-200-mutsweep/` and `/tmp/adv-200-lsp-derivation-resolver-mutsweep/` and written back by hand; no `git checkout`/`restore`/`stash` used; `git status --porcelain` clean for both files afterwards.
- **Nine live probes** through the shipped engine: the D0 200-file budget (×2), the report's `build-maven/scripts` spot-check population (×2), a stub server rejecting `initialize`, a server that dies on boot, a direct cross-bundle `textDocument/definition` probe, and a full-tree `build_lsp_component_refs` with a real binding (×3, in two interpreter environments).
- Three pipeline probes: `discover_derivation_resolvers()` roster, `discover_project_modules()` field survival, and `merge_path_claims()` / `lookup_claim()` over the live Axis-D attributor set.
- Component counts re-derived from `plugin.json` manifests at both `HEAD` and `c86de8b`; candidate-file count cross-checked against `git ls-files '*.py'`.
- A synthetic `make_prefix_attributor` / `lift_to_modules` case demonstrating the root-scoped-module wrong-edge path (Correctness review item 6).

**Not checked / UNVERIFIABLE:**
- The report's `./pw verify` totals (19 708 / 19 986 passed) — the brief excludes running the full suite.
- Everything in § Reviewer participation and § Merge-conflict resolution — PR-side facts not reachable from this clone.
- Whether the zero-edge outcome also holds for a *consumer* project. The harvest is materialized only by `pm-plugin-development`'s marketplace discovery, so no consumer project reaches the code path at all today; the resolver correctly reports `harvest-did-not-run` there (`extension.py:160-170`, mutation-proven).
- The D0 boot-time figures (0.34–0.46 s) were not separately isolated from total harvest time.
