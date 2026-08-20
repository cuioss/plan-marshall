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
| D1 | lsp-client diagnostics answer contract, per-file worsened-set verdict | `ea8fadf` | Done. 4 CI-portable red/green pairs; all four "Done when" clauses met |
| D2 | Lookup rows carry their file; the write path is all-or-nothing | `ea8fadf` | Done. (a)–(e) met; (a)/(b) in both real-server and fake-transport form; one assertion per verb through the CLI seam |
| D3 | The `lsp` harvest resolves real imports, refuses vendored targets, names its failure | `1d2731d` | Done. Gating baseline taken; G1 proceeded; all five "Done when" clauses met |
| D4 | Python/npm discoverers stop reporting a missing capability as a measured absence | `253bf44`, `94cd8ba` | Done. (a)–(g) met, including (g) unchanged |
| D5 | Corpus server survives a bad frame, resolves the right site, never presents an unconfirmed one as exact | `87e888e` | Done. (a)–(e) met |
| D6 | One store, one meaning of `configured`; four standing questions recorded | `accf6ed` | Done. G9 fixed both sides; G10/G25/G12 and the three handed-up proposals recorded, none acted on |

Plan directory established in `bc72501`.

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

**Result: passed.** `21414 passed, 14 skipped` in 583.66 s, exit 0. All three sub-steps ran:
quality-gate (`ruff … All checks passed!`, `mypy … Success: no issues found in 416 source files`,
`SPDX-header check passed`), test-compile, and module-tests.

⚠ **The first `./pw verify` FAILED**, and the failure is worth recording because it is exactly the
class the contract warns about: `test-compile` — the only sub-step that type-checks the test tree, and
the one neither `quality-gate` nor `module-tests` runs — rejected two unused `type: ignore` comments
that were green under both narrower calls. Fixed in `94cd8ba`; the figures above are the re-run.

**Stale-base re-verification (§ Step 8 condition 2):** recorded at the merge gate below.

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

`git diff --name-only origin/main...HEAD` → 44 files. **Every one falls inside the plan's Expected
surface.** No file outside it was touched. The plan's own directory carries `plan.md`,
`proposals.md` and this report, as the Expected surface anticipates.

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

_Pending — the verification sub-agents' findings and dispositions are recorded here._

## Reviewer participation

_Pending._

## Cost

- **Tokens:** not available to the agent in this session.
- **Wall-clock:** _re-derived at finalize; source: `git log --format=%cI` on this branch's first and
  last commits._
- **Population:** this single Claude Code cloud session's usage. ⛔ **Not comparable** to a
  plan-marshall `metrics.toon` total, which counts the orchestrator-plus-agent dispatch tree under
  plan-marshall's own per-task billing boundary — a boundary an interactive cloud session does not
  share. The figures are not made comparable and no parity is implied.

## Contract check (Step 9)

_Pending._

## What have we learned (Step 9)

_Pending._

## Residue

_Pending._
