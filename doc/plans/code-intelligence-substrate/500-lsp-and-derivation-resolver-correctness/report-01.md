# Run report — 500-lsp-and-derivation-resolver-correctness (run 01)

**Date (UTC):** 2026-08-20    **Branch:** `claude/lsp-derivation-resolver-correctness-7ncdpz`    **PR:** _pending_    **Outcome:** completed

> **Verification loop exit:** _pending_

## Skills loaded

Loaded by reading the bundle source path, not the plugin notation — the `plan-marshall` plugin is not
installed in this cloud session.

| Skill | Why |
|---|---|
| `plan-marshall:ref-code-quality` | always |
| `pm-plugin-development:plugin-script-architecture` | always |
| `plan-marshall:persona-implementer` | production code |
| `pm-dev-python:python-core` | Python production code |
| `pm-dev-python:pytest-testing` | Python tests |

No skill was unobtainable by both routes.

`pm-plugin-development:plugin-architecture` and `pm-documents:ref-asciidoc` were **not** loaded: the
run changed no bundle structure or frontmatter, and its two `.adoc` edits are prose insertions into
existing sections whose surrounding conventions were followed from the file itself. Recorded here
rather than left as a silent omission.

## Preconditions

⛔ The plan requires the `pyright-langserver` availability check before D1, D2 or D3, with the answer
recorded here.

**Present** — `/root/.local/bin/pyright-langserver`. The real-server branch therefore applies: the
real-server assertions run and their results are reported below. The CI-portable mirror was built
**anyway**, as the plan requires in either branch, and its adequacy is measured under
§ Build gate → CI portability.

## Deliverables

| # | Deliverable | Commit | Verification state |
|---|---|---|---|
| D1 | lsp-client diagnostics answer contract, per-file worsened-set verdict | `7f36c76` | Done. 4 CI-portable red/green pairs; all four "Done when" clauses met |
| D2 | Lookup rows carry their file; the write path is all-or-nothing | `7f36c76` | Done. (a)–(e) met; (a)/(b) in both real-server and fake-transport form; one assertion per verb through the CLI seam |
| D3 | The `lsp` harvest resolves real imports, refuses vendored targets, names its failure | `3331bfa` | Done. Gating baseline taken; G1 proceeded; all five "Done when" clauses met |
| D4 | Python/npm discoverers stop reporting a missing capability as a measured absence | `8f468a4`, `a230637` | Done. (a)–(g) met, including (g) unchanged |
| D5 | Corpus server survives a bad frame, resolves the right site, never presents an unconfirmed one as exact | `9d375df` | Done. (a)–(e) met |
| D6 | One store, one meaning of `configured`; four standing questions recorded | `573580c` | Done. G9 fixed both sides; G10/G25/G12 and the three handed-up proposals recorded, none acted on |

Plan directory established in `cdf8062`.

### D1 — the diagnostics answer contract

`wait_for_diagnostics` counted publishes globally and returned the cached list for a URI as soon as
the inbound stream went quiet, so the post-edit re-diagnose could settle for the server's verdict
about the **pre-edit** content. It now counts publishes **per URI**; `change_to_disk` returns the
count observed before the change; the post-edit wait requires one strictly greater.

A URI the server never published for returned `[]` — byte-identical in every payload field to a file
the server examined and called clean. It now returns `None`, an explicit unknown. `diagnose` renders
that as `state: unknown` / `answered: false` / `reason: diagnostics_unanswered` and carries **no**
`error_count`, `warning_count` or `diagnostics[]` at all, since a zero there is the false clean signal
the verb exists not to emit. `edit` treats it as failure-to-verify (`reason:
diagnostics_unavailable`) with a rollback.

`edit_verdict` summed error counts across the whole footprint. It is now a **per-file diff of the
error diagnostic sets** and fails when any file gained one; `new_diagnostics[]` carries the added set
rather than the whole post-edit set.

⚠ **One scoping decision the plan left implicit, recorded because it is a judgement call.** The plan
says to key retained diagnostics by `(path, severity, code, message, line)` and to "fail when `added`
is non-empty for **any** file". Read literally that would gate on *all* severities, whereas the
shipped gate counts **errors only** (`DIAGNOSTIC_SEVERITY_ERROR`, and its docstring calls it "the only
severity a worsened-set gate counts"). This run kept the gate's severity scope at **errors**, and
changed only count→set. Reasoning: `severity` is in the key because it identifies a diagnostic, not
because the gate counts every severity; and widening to warnings would make any rename that introduces
an unused-import warning fail and roll back — an undeclared behaviour change with real blast radius,
well beyond the three defects (G2/G13/G15) the deliverable names. Every G15 case the plan cites is
caught with errors-only: the same-file swap, the cross-file move, and the `new_diagnostics[]`
over-report. Stated here so a reviewer can overrule it rather than discover it.

`errors_before` / `errors_after` are retained in the payload as the plan requires.

`test_edit_verdict_passes_on_equal_or_improved` pinned exactly the count-based defect and was replaced
with the set-based pair, as the plan directs.

### D2 — lookup rows and the write path

`_symbol_rows` discarded `location.uri`. Every row now carries `path`, `container` and `depth`, with
`document-symbol` taking the queried file's resolved path so both kinds emit one key set, and the walk
descends into `children` so a class's methods appear.

`normalize_changes`' resource-operation notes were computed and discarded by both callers. A
create/rename/delete-file operation now **fails the verb whole**
(`reason: unsupported_resource_operation`, with `notes[]` and `unapplied_operation_count`) rather than
applying the text-edit remainder.

The apply loop had no exception boundary. `apply_workspace_edit` now restores every file already
written and raises `WorkspaceApplyError` naming the offending path, which `_run_edit` reports as
`apply_failed`; a rollback that itself fails is reported in `restore_error` rather than swallowed.

`LspSession.open` is idempotent, so a document reached twice gets one `didOpen` and monotonic
`didChange` versions.

⛔ The plan's two trigger prohibitions were honoured: the mid-apply test uses a **malformed
`TextEdit`** (no `range`), not `chmod` — the suite runs as `root`, where the mode bit is inert — and
the test is not written around a missing path or a non-UTF-8 file, both of which raise in the pre-edit
loop before any write.

### D3 — the harvest

⛔ **Gating baseline, taken first, on this clone.** `build_lsp_component_refs` inputs: `pyright-langserver`
present and enabled through the shared binding; the real discovered module set from
`plugin_discover.discover_plugin_modules` (11 modules, **none root-scoped** — every `paths.module` is
`marketplace/bundles/{name}`, which independently confirms the plan's Notes on why `200/G13`'s
wrong-edge half is unreachable).

| Metric | Baseline (before) | After G1 + G13 |
|---|---|---|
| `files_scanned` | 2214 | 1398 |
| References | 4899 | 3189 |
| **Cross-bundle references** | **0** | **72** |
| **Module edges** | **0** | **10** |
| References targeting `.venv/**` | 3302 | 0 |
| `unattributable-endpoint` suppressed | 4348 | 1879 |
| `out-of-workspace` | 26945 | 12965 |
| `vendor-tree` | n/a (no such note) | 422 |
| `unresolved-symbol` | 6094 | 293 |
| Wall-clock | 169.2 s | 83.4 s |

The baseline showed zero cross-bundle edges, so the premise held and the **G1 half proceeded** rather
than halting.

**G1 — the search path.** The harvest now derives the module search path from the tree and sends it as
`python.analysis.extraPaths`. ⚠ **This generalises the plan's phrasing, deliberately.** The plan says
"every bundle skill `scripts/` directory", which is a description of *this* repository; hard-coding
`marketplace/bundles/*/skills/*/scripts` into a capability that ships to consumer projects would be a
generalization leak. The implemented rule is structural: **a directory holding Python files but no
`__init__.py` is not a package, so an import of one of its files can only resolve with that directory
on the search path** — which is exactly the set a launcher synthesizes, computed from the tree. On
this repository it yields 177 directories, covering every `scripts/` directory the plan names.

Assembling paths into settings is the client's concern, so `lsp-client` gained
`analysis_config_with_extra_paths` and an injectable `analysis_config` on `StdioTransport` (the
`workspace/configuration` reply) and `LspSession` (the handshake). Both are passed, because a server
may read either channel and the two must not disagree. ⚠ This is a **cross-bundle edit**, which the
plan's D3 authorises for this purpose (it names the `workspace/configuration` reply as the first
option, and that reply lives in `lsp-client`); the plan's "do not reach across" ⚠ is scoped to the
`LspError` typed discriminator, which this run did **not** reach across for — see P3.

⚠ **Spot-check of the resulting edge set, as the plan requires.** A wider search path can resolve a
name to another bundle's same-named module. Measured: exactly **one** module basename is ambiguous
across the 177 search paths — `extension`, in 15 directories — and **nothing imports it bare**
(`grep` for `^\s*(from extension import|import extension)\b` over `*.py`: no matches). The risk is
therefore latent, not reachable. It is nonetheless guarded: where two search paths supply one module
name, no ordering makes the attribution correct, so the reference is dropped and reported under a new
`ambiguous-module-name` note. All 10 derived edges are `pm-* → plan-marshall`, and every sampled
cross-bundle reference is a real import of a shared plan-marshall module — including the exact probe
the plan cites as previously UNRESOLVED, `from extension_base import DerivationResolverBase,
ExtensionBase`, confirmed present at `pm-code-intelligence/.../extension.py:22` and
`pm-dev-python/.../extension.py:19`.

**G13 — vendored targets.** One module-level `VENDORED_TREE_DIRS` constant now applies to both the
files queried and the targets resolved to, with a `vendor-tree` note counted apart from
`out-of-workspace`. ⛔ Fixed **with** G1, not after it, for the sequencing reason the plan gives.
⛔ Not fixed by narrowing the root-scoped fallback — the fallback is unchanged and a test pins that it
*would* still claim a `.venv` target, so a later narrowing cannot silently retire the harvest-side
exclusion that actually prevents it. **New finding:** the baseline showed `.pyprojectx/` reached as
both source and target; the source-side skip list had never named it. Added to the constant, which is
why `files_scanned` fell from 2214 to 1398.

**G2 — refusal vs timeout.** Split, with a fifth `server-rejected:` prefix. Reproduced against the
pre-change tree exactly as the plan describes: a server answering `initialize` with a JSON-RPC error
in ~24 ms was reported `server-timeout: … did not respond within 10s (initialize failed: …)`.
⚠ The discriminator is message text, which is fragile; the fallback direction is chosen so an
unrecognised message from a *completed* handshake stays a timeout. The typed-field fix is recorded as
P3 rather than reached across for.

**G3 + G6 — the docstrings.** Both corrected to describe the caller-supplied prefix table the code
invokes, and to name the two obligations the substitute does not carry.

⛔ **`200/G12`'s prefix assertion, and which branch was taken.** Re-derived: the existing
`test_every_failure_mode_states_a_distinct_reason` collected **whole interpolated strings** and
asserted `len(reasons) == 4` — it did **not** already assert a prefix set. Per the plan's authored
branch, the conversion was made **in this run**: it now collects `reason.split(':', 1)[0]` and asserts
**set equality** against the five expected prefixes. Set equality rather than a length, so a mode
reporting under the *wrong* prefix is caught as well as one reporting under a duplicate. **The sibling
plan `550-test-suite-anti-vacuity` should reconcile rather than duplicate this.**

⚠ **Out of scope, and stated as the plan requires:** this run does **not** make the harvest
reproducible across interpreters. There is still no `pythonPath` / `workspace/configuration` pinning,
so the reference count and three of the notes still move with which Python the server resolves
against. D3 fixes the `.venv` **symptom**, not the reproducibility.

### D4 — the discoverers

`_parse_pyproject_metadata` read one table of one file. It now falls back to `[tool.poetry]` and then
to `setup.cfg`, **strictly** — neither fires while `[project]` supplies a name, because `metadata` and
`dependencies` are read beyond edge derivation. ⛔ `setup.py` is not attempted and that limit is
stated in the user page.

PEP 508 parsing is now a named function taking the environment marker first and then splitting on the
**bare `@`**. ⛔ The plan's correction was honoured: a `' @ '` split would have passed the spaced form
and left `sample-core@file:///./core` — the spelling `pip freeze` emits — broken. Seven legal
spellings are parametrised, and `marker-and-specifier` passes on **both** sides, which is the control
proving the parametrisation is not uniformly red.

The bare `except Exception` is narrowed to the three exceptions a descriptor problem raises and logs a
WARNING naming the file; anything else propagates, pinned by its own test.

npm: the **disclosure route**, as the plan directs — the extraction is unchanged, and the user page,
`build-npm/SKILL.md` and the function docstring now state that `peerDependencies` and
`optionalDependencies` produce no edge. The extraction route is recorded as P2 with its four
lock-step sites enumerated.

(g) re-derived from the test rather than from the plan's figure: the PEP 621 fixture's exact edge-set
assertion is `test_full_edge_set_is_exactly_the_declared_internal_dependencies`, asserting five edges.
It passes **unchanged**.

### D5 — the corpus server

Exception boundaries at the handler and around the serve loop body, plus an entry path that keeps
`serve` out of `@safe_main`, whose TOON-on-stdout contract is fatal for a protocol channel. Every
contained exception is reported on stderr.

`on_references` omits unverified sites. ⛔ Option **(a)**, the contract-conforming direction, as the
plan directs; option (b) is recorded as P5. Both constraints the plan attaches are met: `query` is
unfiltered and still emits every site with its `verified` flag, and the omission is **visible** — the
withheld count travels on each returned `Location` as `omittedUnverifiedCount` **and** as a
`window/logMessage` notification, which is the only channel left when every site was withheld and the
list is empty. Server-to-client notification support was added to `LspServer` for that second channel.

`resolve_reference_site` ranks rather than takes-first: full notation over tail-only, and a tie at the
same rank is reported against the owner as unverified. Some previously-`verified` sites become
unverified; that is the honest direction and it lowers the headline count.

`initialize` adopts the client's declared root (`rootUri` → `rootPath` → `workspaceFolders[0]`) when
`--project-path` was not passed. ⚠ An explicit `--project-path` still wins, pinned by its own test.
`--project-path` now defaults to `None` rather than `'.'` so "not given" is distinguishable from
"given as the cwd"; every reader spells the fallback `args.project_path or '.'`, so the effective
default is unchanged.

⛔ G3: the **disclosure half**, not the rebuild. The staleness bound is stated in `SKILL.md`, the user
page and the module docstring, with a test quantified over all three surfaces. Invalidate-and-debounce
is recorded as P4.

### D6

G9 fixed on **both** sides to the dict definition. The guard compares the two answers directly rather
than asserting a value on one side: the defect was the *disagreement*, and the shipped code was
self-consistent on each side, so a one-sided assertion would have passed against it. A separate test
pins that `enabled` still fails **open** on a malformed entry, so tightening `configured` cannot
quietly tighten it too. The two roster tests asserting `configured` on well-formed entries
(`test_unconfigured_resolvers_are_enabled_but_not_configured`,
`test_explicitly_enabled_resolver_is_marked_configured`) still pass.

G10, G25, G12 and the three handed-up proposals are recorded in
[`proposals.md`](proposals.md). **Nothing there was acted on.** Key re-derivations:

- **G10** — `resolve-dependencies validate --scope marketplace`: **61 unresolved of 5083 dependencies
  over 308 components**. Classified structurally: **26 non-notations (43 %)** and **35 well-formed
  notations whose target does not exist (57 %)**. The ~97 %-false-positive premise the diagnostics
  deferral rests on has **inverted**. Recorded as a proposal with the argument on both sides; the
  deferral is **not** declared upheld and diagnostics were **not** implemented.
- **G25** — the asserted absence re-derived with the search terms and results tabulated in
  `proposals.md`. No bundle manifest declares `lspServers`; no component invokes `preflight` or
  `query`; every hit outside the skill's own directory is registration, catalogue or documentation.
- **G12** — the 020 report's coordination note **appended to, not rewritten** (it is a dated record of
  one execution), naming `tools-corpus-language-server` first with its component-granular limit and
  posing the open question three-way.

## Build gate

`git diff --name-only origin/main...HEAD -- '*.py'` → **24 files**. Python changed, so the full
`./pw verify` ran. Working tree confirmed clean (`git status --porcelain` empty) before the diff was
taken, so the gate saw all the work.

**Result: passed.** All three sub-steps ran: quality-gate (`ruff … All checks passed!`,
`mypy … Success: no issues found in 416 source files`, `SPDX-header check passed`), test-compile, and
module-tests.

⛔ **This figure moves with every commit, so it is stamped with the commit it was measured at rather
than carried forward.** An earlier revision of this section reported `21414 passed, 14 skipped` from
`a230637` and left it standing across three later commits that changed **production** Python — the
stale-figure defect this report warns about elsewhere, committed here.

| Measured at | Result |
|---|---|
| `a230637` | 21414 passed, 14 skipped, 583.66 s |
| `f5bc086` (independently re-run by the round-3 verifier) | 21419 passed, 14 skipped, 507.80 s |
| **`be54037`, the REBASED tree — the figure that governs** | **21419 passed, 14 skipped, 412.44 s, `verify: SUCCESS`** |

The figure that governs is the last, because it is the only one measured on the tree that actually
lands. All three sub-steps ran on it: quality-gate (`ruff … All checks passed!`, `mypy … Success: no
issues found in 416 source files`, `SPDX-header check passed`), test-compile, and module-tests.

⚠ **The first `./pw verify` FAILED**, and the failure is worth recording because it is exactly the
class the contract warns about: `test-compile` — the only sub-step that type-checks the test tree, and
the one neither `quality-gate` nor `module-tests` runs — rejected two unused `type: ignore` comments
that were green under both narrower calls. Fixed in `a230637`; the figures above are the re-run.

### Stale-base re-verification (merge-gate condition 2)

`git rev-list --count HEAD..origin/main` at the gate: **0** — the base is current, because the branch
was **rebased** onto it rather than left behind it (§ Residue records why a rebase rather than a
merge, and what the rebase obliged).

⚠ **A zero here is a measurement, not the absence of one.** It reads zero *because* the run brought
the base in: before the rebase the gap was **4** commits, one of them PR #1314's 309-file test
restructure. What condition 2 requires is that the gate has been run on a tree containing the moved
base, and it was:

| | |
|---|---|
| Shape used | **Rebased onto `origin/main` (`a34819d`)** — the branch head *is* the tested tree, so the PR's own CI verifies exactly what lands |
| Tested commit | `be54037` |
| Predicate | 24 `*.py` files changed, so the **full** `./pw verify` — not the docs-only skip |
| Result | **`verify: SUCCESS`** — 21419 passed, 14 skipped, 412.44 s |

**This run also settles the one risk the #1314 coordination check could not reach.** A file-overlap
check cannot see an order-dependent `load_script_module` registration collision — the failure mode
#1314's own body records as having cost a sibling plan 173 failures. Only a green whole-tree run
**with #1314's 202 split modules and 66 new fixture modules actually in the tree** settles that, and
this is that run.

### CI portability — measured, not assumed

The plan requires this as a check in its own right: a guard only a locally-installed binary can
falsify does not protect CI.

| Run | Result |
|---|---|
| Affected suites, **pyright hidden from `PATH`**, current code | **662 passed, 10 skipped** |
| The five new/changed guard modules, **pyright hidden**, against **reverted** (`origin/main`) code | **53 failed, 10 passed, 1 skipped** |

Only the explicitly `skipif`-guarded real-server tests skip. Every new guard runs, and 53 of them are
falsifiable without a language server — against the plan's observation that the shipped suite stayed
green with the entire diagnostics-wait mechanism deleted.

`PATH` was built by symlinking `/root/.local/bin` minus `pyright*` into a scratch directory, so `uv`
and the toolchain stayed reachable while `shutil.which('pyright-langserver')` returned `None`.

### Mutation sweep — every guard shown to fail against the defect it names

Ten mutants, one per fixed defect, each run with **pyright hidden**. Files were snapshotted by the
harness itself and written back in a `finally` — never a git command, which would have rewritten the
tree from the index. `git status --porcelain` was empty before the sweep and empty after it.

| Mutant | Verdict |
|---|---|
| D1 stale read: ignore `after_seq`, never answer unknown | RED (3 failed) |
| D1 set verdict: never fail on a worsened set | RED (4 failed) |
| D2 symbol rows: drop the path again | RED (2 failed) |
| D3 vendored targets: admit them again | RED (4 failed) |
| D3 search path: send no `extraPaths` | RED (2 failed) |
| D4 PEP 508: drop the marker and direct-reference splits | RED (6 failed) |
| D5 exception boundary: let a handler defect escape | RED (1 failed) |
| D5 unverified sites: emit them as exact `Location`s | RED (1 failed) |
| D5 ranking: take the first candidate again | RED (3 failed) |
| D6 `configured`: back to key presence | RED (2 failed) |

**10 of 10 killed. No survivors.**

## Red-then-green, per fixed defect

Every new guard was run against the pre-change tree in a detached `origin/main` worktree before being
declared green. Where a guard would have failed on a *signature* rather than on behaviour, the
pre-change copy was adapted (old constructor call, pre-change defaults, `getattr` fallbacks for
absent names) so the observed failure is the **defect**, not the API change.

| Group | Pre-change result | Representative observed failure |
|---|---|---|
| D1 (6 checks) | 6 failed | stale read → `status: success` with the defect on disk; silence → `state: ok`; swap → `success` with `errors_before == errors_after == 1`; `new_diagnostics` `['A','B']` instead of `['B']` |
| D2 (8 checks) | 8 failed | `cmd_edit` through the CLI rendered `status: success` on a resource-op edit; `KeyError: 'path'` on symbol rows; versions `[1, 2, 1, 2]` |
| D3 (13 checks) | 11 failed, 2 controls green | `server-timeout: … did not respond within 10s (initialize failed: …)` after ~24 ms; `.venv was admitted as a target`; `[('alpha','rootmod')]` wrong edge; the real cross-bundle import did not resolve |
| D4 (25 checks) | 19 failed, 6 controls green | Poetry and setuptools monorepos derived **no edges at all**; three of four PEP 508 spellings lost the edge |
| D5 (12 checks) | 10 failed, 2 controls green | rc=1 with stdout ending `…"textDocumentSync": 1}}}status: error`; `the decoy won: {('aaa-notes.md', True)}` |
| D6 (4 checks) | 2 failed, 2 controls green | roster `configured: True` where the store verb said `False` |

The "controls green" counts are tests that must pass on **both** sides — invariants the change must
not move — and are named as such rather than presented as coverage.

## Collateral check

⛔ **An earlier revision of this section said "44 files, every one inside the plan's Expected
surface". Both halves were wrong** — the count was stale, and files outside the surface were already
present when it was written. Verification item 5 requires every such file **accounted for**, not
absent. Re-derived at the moment of this claim:

`git diff --name-only origin/main...HEAD` → **50 files** (re-derived at `ec3a919`; `report-01.md` is
already in that set, so committing this section does not move it). **Seven fall outside** the plan's
Expected surface, each for a stated reason:

| File | Why it was touched |
|---|---|
| `doc/user/lsp-code-intelligence.adoc` | D1 made its state table and its count-based write-side rule **false**. |
| `marketplace/bundles/plan-marshall/skills/build-pyproject/SKILL.md` | D4 made four of its Axis-C statements **false**. |
| `marketplace/bundles/plan-marshall/skills/execute-task/SKILL.md` | D1 made its instruction to the consuming leaf **false** — it told a leaf to read every `failed` return as a rejected edit. |
| `marketplace/bundles/plan-marshall/skills/manage-run-config/SKILL.md` | D6/G9 made its `configured` comment incomplete. |
| `.../manage-run-config/standards/run-config-standard.md` | D6/G9 made its definition of `configured` **false**. |
| `test/plan-marshall/extension-api/test_derivation_resolver_roster.py` | D6/G9's *Done when* requires a test **on each side** of the store; this is one side. |
| `test/plan-marshall/manage-run-config/test_run_config_derivation_resolver.py` | The other side. |

The first five are the plan's own carve-in: § Out of scope states this plan changes *"the
documentation that is **inseparable from a behaviour change it lands**"*, and a statement this run's
change renders false is exactly that. The last two are named by a *Done when* clause. Nothing else
lies outside; the plan's own directory carries `plan.md`, `proposals.md` and this report, as the
Expected surface anticipates.

## Gap coverage

Per gap id, as § Verification item 6 requires. Severities are the ones the plan's own table carries.

| Deliverable | Source plan | Gap ids | Disposition |
|---|---|---|---|
| D1 | `010-lsp-in-execute-lookup-and-write` | G2, G13, G15 (high ×3) | **discharged** |
| D2 | `010-…` | G1 (high) | **discharged** |
| D2 | `010-…` | G3, G4, G5, G14 (medium ×4) | **discharged** |
| D3 | `200-lsp-derivation-resolver` | G1, G2 (high ×2) | **discharged** |
| D3 | `200-…` | G3, G6, G13 (medium ×3) | **discharged** |
| D4 | `210-native-coordinate-resolvers` | G1, G10 (high ×2) | **discharged** |
| D4 | `210-…` | G2, G3, G11 (medium ×3) | **discharged** |
| D4 | `210-…` | G4 (medium) | **discharged by disclosure**; extraction recorded as P2 |
| D5 | `240-skill-lsp-server` | G1, G28 (high ×2) | **discharged**; G28's option (b) recorded as P5 |
| D5 | `240-…` | G2, G4 (medium ×2) | **discharged** |
| D5 | `240-…` | G3 (medium) | **discharged by disclosure**; rebuild recorded as P4 |
| D6 | `240-…` | G10 (medium) | **recorded as a proposal** (P6) — not decided, per the plan |
| D6 | `240-…` | G25 (medium) | **recorded as a decision record** (D1 in `proposals.md`) |
| D6 | `220-resolver-configuration` | G9 (low) | **discharged** |
| D6 | `020-corpus-residency-admission-control` | G12 (low) | **discharged** |

Twenty-eight gaps, none silently absent. Totals re-derived against the table: high 3+1+2+2+2 = 10;
medium 4+3+4+3+2 = 16; low 2 — twenty-eight, matching the plan's lead-in.

⚠ **A citation the plan anticipated:** the plan notes that a landed cloud plan's directory is deleted
at collect, so a cited `gaps.md` may be absent. All six cited directories were **present** on this
clone, so no citation was unreachable and the plan's restated content was corroborated where checked.

## Findings

Two independent sub-agents were dispatched per round: a **plan verifier** (reads the plan and the
diff, runs the claims) and a **cold reader** (Verification item 4 — reads the four reader-facing texts
with **no access to the plan**, and reports which reading it took).

### Round 1 — cold read

All four required readings came back **correct**: `diagnostics_unavailable` read as *"verify by
build"* (B), the attribution docstrings read as *a caller-supplied prefix table* (B), the staleness
bound read as *"answers may be stale"* (A), and every item of `proposals.md` read as *proposal
recorded* (with `D1` correctly read as a decision record). No wording failure by the plan's own
criterion — but the reader named four places where it nearly took the wrong one, and one sentence
that is false as written. All five fixed in `ef3e165`.

| # | Finding | Disposition |
|---|---|---|
| C1 | `proposals.md`'s preamble said everything is "recorded, not decided" and "needs an operator's approval first" — **false** of the decision record it introduces: leaving a surface unwired needs nobody's approval | **fixed** — the preamble now separates the two entry kinds by who must act next |
| C2 | The user page's "every site is re-read before it is reported" sits several sections above the staleness bound with nothing reconciling them; the reader was pushed toward the freshness reading before the later section corrected it | **fixed** — the cache clause and an xref to the existing `[[staleness]]` anchor |
| C3 | The lsp-client write-side rule described fail-and-rollback only for `diagnostics_worsened`, so `status: failed` momentarily reads as "you broke something" | **fixed** — a forward pointer in the rule |
| C4 | `derive_edges`' "the lift does not go through the Axis-D seam" is a claim about **upstream** code in a method that performs no lift, sending a reader hunting for a callable that is not there | **fixed** — names the harvest as the lift's location |
| C5 | P6's heading stated a conclusion ("has inverted") where it reports a measurement; P5 read as if the landed option had settled the question | **fixed** — both now state the measurement and leave the decision open |

### Round 2 — plan verifier

Twenty findings. The verifier ran the claims rather than reading them, which is what produced most of
these. All fixed in `6bbd765`.

| # | Finding | Disposition |
|---|---|---|
| F1 | **A real deliverable gap.** D3 *Done when* (c)'s second clause requires `lift_to_modules` with a root-scoped module and a `.venv` target to produce **no edge**. It produced `[('alpha','rootmod')]` with no note — the exclusion lived only in `harvest_workspace` | **fixed** — `lift_to_modules` now refuses a vendored endpoint itself, under the same constant, with a `vendor-tree` suppression. The root-scoped fallback is still untouched, per the plan's ⛔ |
| F2 | A guard named `..._is_never_attributed_to_a_root_scoped_module` asserted that it **is** — a false statement standing in test output | **fixed** — split into the attributor's pinned behaviour and the lift's actual refusal |
| F3 | "the live seam claims only `.claude` and `.plan`" — **false** at three sites. Executed: five claims from three attributors. The *conclusion* (`None` for marketplace paths) holds; the premise did not | **fixed** at all three, and independently re-derived by this run |
| F4 | D4 falsified four statements in `build-pyproject/SKILL.md` and the dependency user page | **fixed** — and a **fifth** the verifier missed: the user page's ecosystem **table**, the same claim in a different consumer kind |
| F5 | D1 falsified `doc/user/lsp-code-intelligence.adoc` — "the three states" and "if the error count went **up**, the step fails" | **fixed** — an `unknown` row and set-based write-side bullets |
| F6 | D6/G9 falsified the run-config standard's "`configured` reports whether an **entry exists**" | **fixed** at the standard and the SKILL.md comment |
| F7 | D5/G4 falsified the corpus skill's load-bearing `--project-path` paragraph, and the new adoption behaviour was documented nowhere operator-facing | **fixed** — both |
| F8 | "pays the build once at `initialize`" is **false** — the index is a lazy property and the handshake builds nothing; two adjacent statements in one document disagreed | **fixed** at three sites; independently re-derived (`index` is a `property`; `_on_initialize` does not touch it) |
| F9 | `proposals.md` P2 said the npm join "reads the first segment and must not start treating a new scope as an edge" — it reads the **name** and *deliberately ignores* the scope, which makes the coupling **tighter** than stated. Wrong file path too | **fixed** — and the stronger reason stated |
| F10 | P6's reproduction command does not run by direct path (`ModuleNotFoundError: marketplace_bundles`) | **fixed** — the executor form recorded, with why |
| F11 | D5 *Done when* (b) says "driving a running `serve`"; the test called `on_references` in process, so the omitted count and the `window/logMessage` were never observed on the wire | **fixed** — a subprocess test |
| F12 | D2's ⚠ CLI-seam obligation half-met for `lookup`: the `path` assertion ran against a direct helper call because the fake answered `workspace/symbol` with `null` | **fixed** — the fake returns a real `SymbolInformation` and the assertion lands on rendered TOON |
| F13 | The nine-way vendored sweep asserted only an empty reference list — which a fake server that never spawned satisfies nine times | **fixed** — asserts `outcome.ran` |
| F14 | `test_the_query_verb_...` called the index, not `cmd_query`, and its final assertion could not fail | **fixed** — drives `cmd_query` |
| F15 | `test_the_skip_set_is_one_constant_used_for_sources_and_targets` asserted only membership, never the coupling its name claims | **fixed** — renamed, plus a new test that **moves** the constant and watches all three consumers follow |
| F16 | No run report existed, so the report-bound *Done when* clauses were unverifiable | **not a gap** — the report was untracked at the time and is committed in `6bbd765`. Round 3 verifies its content |
| F17 | The run **measured** a shipped figure false and left it shipped: the ~380-of-~5300 / ~97 %-false-positive premise, against this run's 61-of-5083 / 43 % | **fixed** at four sites. ⚠ These surfaces belong to sibling plan `560`, which should **reconcile rather than duplicate**; leaving a knowingly-false figure shipped was the worse option |
| F18 | The new user-page sentence "a `pyproject.toml` that does not parse publishes nothing" is false when a `setup.cfg` is present | **fixed** |
| F19 | `bare_import_roots`' "no `__init__.py` is not a package" — under PEP 420 it is a namespace-package **portion** | **fixed** — the real reason is that a portion is importable only under its dotted path |
| F20 | `proposals.md`'s "a decision record is a decision the run *did* take" can read as the run having decided | **fixed** — reworded to "left exactly as it found it" |

### Round 2b — the run's own sweep of its round-2 prose

Fixed in `b2b6988`, found by this run rather than by a verifier, applying the rule that the previous
round's own prose is the highest-risk surface:

| # | Finding | Disposition |
|---|---|---|
| S1 | `corpus_lsp.py`'s `--project-path` **argparse help** still said only "(default: cwd)" — the behaviour G4 replaced. A prose-bearing string literal in production code: a docs sweep never opens the file and a code sweep never reads the sentence | **fixed** |
| S2 | `proposals.md` said `merge_path_claims` "returns five claims" — run, it returns a `(claims, roster)` pair whose claim list holds five | **fixed** |

### Round 3 — cold read

All four required readings came back **correct** a second time, on the corrected texts. The reader
also confirmed five of this run's mechanism claims by executing them — the Axis-D claim set (5 claims
/ 3 attributors, `None` for a marketplace path), the npm two-of-four extraction, the single untyped
`LspError` raised for both causes, D6/G10's 308 / 5083 / 5022 / 61 and its 26 / 4 / 31 split, and
G25's asserted absence — each reproduced exactly.

Seven findings, all fixed in `c944289`. **Four of the seven are defects the previous round's own
fixes introduced**, which is the pattern the contract predicts: by round N the highest-risk text is
what round N−1 wrote.

| # | Finding | Disposition |
|---|---|---|
| R1 | **A silent-empty case nothing documented, created by this deliverable.** The strict fallback is all-or-nothing per file: a `[project]` table supplying a name suppresses `[tool.poetry]` **whole**, including its dependency lists. Run: the hybrid layout returns `metadata {'name': 'hybrid-dist'}` with `dependencies []` — a valid edge **target** contributing no outbound edges, with nothing saying why | **fixed by disclosure + a test.** All-or-nothing stays: a per-field merge would let one form silently override the other, and the plan's own ⚠ requires the fallback be strict. Now a stated limit in the user page, pinned by `test_a_pep621_name_suppresses_the_poetry_table_whole_including_its_dependencies` |
| R2 | `proposals.md` P6 described **in the present tense** a documentation state the same run had corrected, sending a reader to `SKILL.md` for a 97 % claim that is no longer there | **fixed** — past tense, plus an explicit "those surfaces have since been corrected; what remains open is the gate" |
| R3 | The corpus user page said the index is built "when the first **request** arrives" — but `initialize` **is** a request and is always first, so read literally it says the handshake pays the build, which `SKILL.md` explicitly denies | **fixed** — "when the first **lookup** arrives — not during the handshake, which builds nothing" |
| R4 | "Two scopes are read from **each** descriptor form" is false for `setup.cfg` (runtime only), and the sentence contradicted itself three clauses later; the ecosystem **table** carried the same unqualified promise | **fixed** at both — "up to two scopes, depending on which form supplied the name" |
| R5 | `lsp-code-intelligence.adoc`'s section is titled "the states you can always tell apart" and omits `preflight`'s `ready`, so a reader who calls `preflight` gets a state the exhaustive-sounding table lacks | **fixed** — a NOTE naming `ready` and when to expect it |
| R6 | The same page names `diagnostics_unavailable` but never `diagnostics_worsened` — the one reason code that **does** mean the edit was wrong was the one it could not look up | **fixed** |
| R7 | An empty find-references result has **five** causes the editor cannot distinguish: an off server advertises nothing, `completeness_note` rides in a field no editor renders, and the withheld count arrives as a `window/logMessage` many clients hide by default | **fixed** — a new `[[empty-references]]` section tabulating all five and the two commands that separate them |

⚠ **R7 is worth naming as more than a doc gap.** This epic exists to make an empty answer legible, and
the *editor* surface — the one an operator actually looks at — could not distinguish five kinds of
empty. The withholding D5 introduced (G28) made that strictly worse by adding a sixth. The fix is
documentation because the LSP protocol offers no richer channel; the underlying limit is real and is
now stated rather than implied.

### Round 3 — plan verifier

The verifier re-checked all twelve round-2 fixes site by site, re-derived every figure this run
publishes by **executing** it, and ran the full `./pw verify` itself. **Ten findings, every one a
false statement (condition A); one additionally resets condition B.** All fixed in `ec3a919` and this
commit.

Confirmed independently: the Axis-D claim set (5 claims / 3 attributors, `None` for a marketplace
path); the 308 / 5083 / 5022 / **61** validator figures and their 26 / 31 / 4 split; the lazy `index`
property and that `_on_initialize` never touches it; `derive_name_edges` taking
`dependency.split(':', 1)[0]`; **177** search paths; exactly one ambiguous basename (`extension`, 15
directories) with no bare import of it; **72** cross-bundle references and **10** module edges, all
`pm-* → plan-marshall`; the PEP 621 fixture's 5-edge assertion unchanged. It found **no vacuous
guard**.

| # | Finding | Disposition |
|---|---|---|
| V1 | `build-pyproject/SKILL.md` still said a module whose `pyproject.toml` does not parse publishes no name — the **same claim** round 2 fixed on the user page, landed at one of two sites. Executed: such a module publishes `broken-but-cfg` via the `setup.cfg` fallback | **fixed** |
| V2 | The PEP 420 paragraph round 2 wrote is **wrong**: a namespace portion's modules *are* importable as `{dir}.{module}` from the parent, and the paragraph contradicted itself two clauses later. Re-run here — dotted import succeeds, bare import does not | **fixed**; `__init__.py` is a *convention* discriminator, not a semantic one, and it now says so |
| V3 | `lift_to_modules`' docstring still said vendored exclusion happens "before a target ever reaches this function" — round 2 added exactly that exclusion **inside** it, so the contract list told a reader the opposite of what the code does | **fixed** |
| V4 | This report's Collateral check claimed "44 files, every one inside the Expected surface". **Both halves false** — stale count, and outside files were already present | **fixed** — re-derived, all seven outside files accounted for |
| V5 | This report's Build gate carried figures measured at `a230637`, unchanged across three later commits that touched production Python | **fixed** — stamped per commit, with the merged-tree run named as governing |
| V6 | **`execute-task/SKILL.md`** — the skill that drives the leaf — still said "treat a `failed` return as a rejected edit (investigate the reported diagnostics)". After D1 that is wrong for three of four reasons, and it is the misreading D1 exists to prevent, at its **only consuming site** | **fixed** — the four reasons split, each with what to do |
| V7 | The corpus `SKILL.md` still asserted the gate is "hard-gated on the validator-precision work" and that diagnostics would ship "before that precision work lands" — asserting work has not landed that G10 re-derived as inverted. The least-corrected of the four sites | **fixed** |
| V8 | `[[unverified]]` was stacked above `[[staleness]]` on one section title, so the new five-causes table's xref resolved to the **wrong section** | **fixed** — anchor moved to the section it names |
| V9 | The user page still said the withheld count means "an empty result is never mistaken for 'no references'" — contradicted fifteen lines later by the section this run added | **fixed** |
| V10 | `lsp-client/SKILL.md` said "`preflight` reports the same **three** situations" over a table that gained a fourth row in this branch — the identical count round 2 fixed on the user page, sibling missed | **fixed** |

⚠ **V6 is the finding worth carrying forward.** Every other surface this run corrected is read by a
human; V6 is read by a **task leaf**, and it instructed that leaf to do the one thing D1's fail-closed
direction exists to stop — treat "nobody checked" as "your edit was wrong". It lies outside the plan's
Expected surface, which is why no diff-scoped check could have found it and only a consumer-directed
sweep did.

**Observations left open, with their bounds** (the verifier's O1–O5, none blocking):

| # | Observation | Why it is left |
|---|---|---|
| O1 | `lsp-client/SKILL.md` tells a leaf to run `./pw verify` — this repo's wrapper, in a skill that ships to consumer projects of any ecosystem | **Pre-existing**: two sites and the module docstring predate this branch; propagated once. Owned by `560-documentation-surface-truthfulness` |
| O2 | `_report_omitted`'s notification names the bare script rather than the executor form | Incomplete, not false |
| O3 | `lsp_client.py`'s module docstring enumerates two outcomes; `unknown` is a third, unnamed **there** (it is named in `SKILL.md`, the user page and the code) | Incomplete, not false |
| O4 | The ambiguity guard drops a reference whenever the **target basename** is ambiguous, even for a dotted or relative import to a uniquely-located file | **Bounded:** 0 hits on this repository, always counted under `ambiguous-module-name`, and it is the conservative direction the plan's ⚠ mandates. Cannot change this deliverable's verdict |
| O5 | The D3 "after" figures drift at HEAD (`files_scanned` 1400 vs 1398, references 3194 vs 3189, wall-clock 86.2 s vs 83.4 s) | Explained: ~2 test files added after the measurement commit. The report frames these as measurements taken at a point, which is what they are |

## Reviewer participation

_Pending._

## Cost

- **Tokens:** not available to the agent in this session.
- **Wall-clock:** **26 h 58 m** between the first and last commit on this branch. Source:
  `git log --format=%aI origin/main..HEAD`, first vs last — **author** dates, deliberately: the
  rebase reset every *committer* date to the rebase instant, so `%cI` would report a span of one
  minute. ⚠ This is elapsed span, **not** time worked: the run was idle across a long gap while
  waiting for PR #1314 to land, and no attempt is made here to net that out.
- **Population:** this single Claude Code cloud session's usage. ⛔ **Not comparable** to a
  plan-marshall `metrics.toon` total, which counts the orchestrator-plus-agent dispatch tree under
  plan-marshall's own per-task billing boundary — a boundary an interactive cloud session does not
  share. The figures are not made comparable and no parity is implied.

## Contract check (Step 9)

_Pending._

## What have we learned (Step 9)

_Pending._

## Residue

### Coordination with PR #1314 (the test module-budget campaign)

The operator flagged [#1314](https://github.com/cuioss/plan-marshall/pull/1314) — run 1 of the
`test-quality/100-module-budget-campaign`, which splits 66 over-budget test modules into 199 test
modules plus 64 `_{domain}_fixtures.py` modules across **281 files**.

**Checked before assuming: there is no collision — verified twice, and the second time is the one
that counts.** The first check read all 281 filenames from the open PR's file list. #1314 then grew
to **309 files** before merging, so the check was re-run against the **landed** commit (`a34819d`)
rather than trusted from the draft:

| Measured on the landed merge | Count |
|---|---|
| Files in #1314 | 309 |
| …under `marketplace/**` or `doc/user/**` | **0** |
| …in this branch's seven test directories | **0** |
| **Intersection with this branch's 50 changed files** | **empty** |

The draft-time breakdown, which the landed form did not change:

| #1314 touches | Overlap with this branch |
|---|---|
| `test/plan-marshall/{plan-retrospective, manage-status, manage-metrics, manage-tasks, manage-lessons, manage-locks, manage-findings, manage-adr, manage-change-ledger, audit-archived-plan-retrospectives}` | **none** |
| `doc/plans/test-quality/**`, four top-level `test/plan-marshall/*.py` | **none** |
| `marketplace/**` | **0 files** |
| `doc/user/**` | **0 files** |
| The seven test directories this branch changes | **0 files** |

⚠ **The interaction to watch is semantic, not textual.** #1314's own body records that
`conftest.load_script_module` registers under the script stem, and that collapsing distinct
registrations onto a shared one cost a sibling plan **173 order-dependent failures**. This branch
uses `load_script_module` (`test_pyproject_descriptor_forms.py`) and reads `sys.modules` through the
roster tests' `_live()` helper, so a registration change anywhere in the suite could surface here as
an order-dependent failure rather than as a merge conflict. #1314 states that no registration name
changed (117 `load_script_module` + 23 `spec_from_file_location` names, none lost, gained or
renamed), so the hazard is stated as controlled — but the whole-tree run on the merged tree is what
actually settles it, and that run is merge-gate condition 2's, below.

**Disposition:** #1314 is fetched into this branch before the merge gate, and the full `./pw verify`
is re-run on the merged tree — which condition 2 requires whenever the base has moved, so this adds
no step that was not already owed. Recorded under § Build gate → stale-base re-verification with the
merge commit that was tested.

**Brought in by a REBASE.** The run first proposed a merge, on the ground that this report quotes
commit SHAs a rebase would invalidate. The operator reaffirmed the rebase; that is their decision,
and the citations were re-derived rather than the instruction reinterpreted.

⛔ **A rebase changes the SHA of every commit it replays, so every document quoting one is stale by
construction.** What was done, in order:

1. A safety ref (`pre-rebase-backup`) was set at the pre-rebase head before anything was rewritten.
2. `git rebase origin/main` — all **16** commits replayed, **no conflicts**.
3. Old and new were paired by **patch content**, not by subject:
   `git range-diff pre-rebase-backup...origin/main origin/main...HEAD` reported every one of the 16 as
   `=` (identical patch), with **none dropped, squashed or changed**. Subject-and-order matching was
   not used — subjects repeat, and a dropped commit would be silently remapped onto its neighbour.
4. Each replayed SHA was proved reachable (`git merge-base --is-ancestor {sha} HEAD`) **before** being
   written down.
5. **20 citations** were rewritten across this report, and every remaining 7-hex token in it was
   re-checked to resolve to a commit on this branch. A grep for all sixteen retired SHAs across
   `doc/` returns nothing.

The other rebase hazard the contract names does **not** apply here: no commit *message* on this
branch quotes a same-branch SHA, so nothing unfixable was left stale. The `020` report's appended
correction cites no SHA either.

### Left open

_Pending the verification loop's exit._
