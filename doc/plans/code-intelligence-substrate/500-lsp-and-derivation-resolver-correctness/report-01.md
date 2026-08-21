# Run report — 500-lsp-and-derivation-resolver-correctness (run 01)

**Date (UTC):** 2026-08-20    **Branch:** `claude/lsp-derivation-resolver-correctness-7ncdpz`    **PR:** none — not requested by the operator, and § Contract check records step 7 as **not done**    **Outcome:** completed (the deliverables; see § How the loop stopped for the loop)

> **Verification loop exit:** budget-exhausted, non-converging

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
| D5 | Corpus server survives a bad frame, resolves the right site, never presents an unconfirmed one as exact | `9d375df`, and the frame half completed in round 8 | Done. (a)–(e) met — but ⛔ **the title clause was FALSE until round 8**: `9d375df` guarded the *handler*, not the *frame*, and every malformed frame still ended the session silently. See § Findings round 8 / F4 |
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

⛔ **Both columns are ONE paired measurement, on the pre-rebase tree** — base `3083553`, the left
column with this branch's D3 change absent and the right column with it applied. They are comparable
to each other and to nothing else. An earlier revision of this section carried them with no such
stamp, and the rebase onto `a34819d` (PR #1314, +204 test modules) then made the right-hand column
read as current when it was not — round 4's W7.

**Re-measured at HEAD, after the rebase.** Run twice, byte-identical on every figure but wall-clock:

| Metric | After G1 + G13 (pre-rebase) | At HEAD (post-rebase, ×2) |
|---|---|---|
| `files_scanned` | 1398 | **1602** |
| References | 3189 | **3549** |
| **Cross-bundle references** | 72 | **72** |
| **Module edges** | 10 | **10** |
| References targeting `.venv/**` | 0 | **0** |
| `unattributable-endpoint` suppressed | 1879 | **2239** |
| `out-of-workspace` | 12965 | **13839** |
| `vendor-tree` | 422 | **0** |
| `unresolved-symbol` | 293 | **751** |
| Wall-clock | 83.4 s | **64.8 s / 63.4 s** |

The three figures D3's claims actually rest on — **72** cross-bundle references, **10** module edges
(all still `pm-* → plan-marshall`), and **0** references targeting `.venv/**` — are unchanged. The
file-count-driven figures moved with #1314's 204 added test modules, as expected.

⛔ **Measurement conditions for the right-hand column, since two of its cells are NOT reproducible
across sessions.** Both runs above: this clone at HEAD, `pyright-langserver` from
`/root/.local/bin`, a 600 s budget, one process at a time. Round 6's verifier re-ran the same
harvest on the same clone and reproduced **`files_scanned` 1602, references 3549, cross-bundle 72,
module edges 10, `.venv` targets 0** exactly — but measured `vendor-tree` **465** and
`unresolved-symbol` **293** where these runs measured **0** and **751**.

⚠ **The two cells trade off against each other, and the cause is interpreter state, not the code
under test.** 465 + 293 = 758 ≈ 0 + 751: a position either resolves *into* a vendored tree (counted
`vendor-tree`, suppressed) or fails to resolve at all (counted `unresolved-symbol`), and which one a
given position lands in depends on what the language server has indexed at that moment. That is the
interpreter-dependence this plan's D3 § *Out of scope* names and declines to fix. ⛔ **Read those two
cells as a pair whose sum is stable, never as independent figures**, and do not compare either across
runs.

It does not touch this deliverable's verdict. The vendored trees are present on this clone (`.venv`
923 `.py` files, `.pyprojectx` 817); the `.venv`-targeting count is **0** in every run by every
observer; and both the exclusion and its suppression note are pinned by tests that do not depend on
this repository's contents or on a live server.

The baseline showed zero cross-bundle edges, so the premise held and the **G1 half proceeded** rather
than halting.

**G1 — the search path.** The harvest now derives the module search path from the tree and sends it as
`python.analysis.extraPaths`. ⚠ **This generalises the plan's phrasing, deliberately.** The plan says
"every bundle skill `scripts/` directory", which is a description of *this* repository; hard-coding
`marketplace/bundles/*/skills/*/scripts` into a capability that ships to consumer projects would be a
generalization leak. The implemented rule is structural: **a directory holding Python files but no
`__init__.py` is not a package, so an import of one of its files can only resolve with that directory
on the search path** — which is exactly the set a launcher synthesizes, computed from the tree. On
this repository it yields 177 directories. ⚠ **That is 69 of the 70 bundle-skill `scripts/`
directories holding `.py` files, not all 70** — an earlier revision of this sentence said "every
`scripts/` directory the plan names", which is false.
`marketplace/bundles/plan-marshall/skills/platform-runtime/scripts` is excluded because it carries an
`__init__.py`, so by the structural rule above it *is* a package and needs no search-path entry. **Three** real bare imports nonetheless target it — `from claude_runtime import …` in
`tools-permission-doctor/scripts/permission_common.py:26` **and** `permission_doctor.py:27`, and
`from platform_runtime import _make_runtime` in `script-shared/scripts/marketplace_paths.py:214`. **Bounded:** all three importers are inside the
`plan-marshall` bundle, so neither a cross-bundle reference nor a module edge can be affected — the
**72** / **10** result is provably unchanged, and that was confirmed by measurement, not argued.

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

`git diff --name-only origin/main...HEAD -- '*.py'` → **24 files** (re-derived at `b364322`). Python
changed, so the full `./pw verify` ran. Working tree confirmed clean (`git status --porcelain` empty) before the diff was
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
| `be54037`, the REBASED tree | 21419 passed, 14 skipped, 412.44 s, `verify: SUCCESS` |
| `b364322`, round 4's fixes | 21419 passed, 14 skipped, 385.38 s, `verify: SUCCESS` |
| `b0d746c`, round 5's fixes | 21419 passed, 14 skipped, 404.89 s, `verify: SUCCESS` |
| `d893d51`, round 6's fixes | 21420 passed, 14 skipped, 490.34 s, `verify: SUCCESS` |
| `def48c4`, round 7's fix | 21422 passed, 14 skipped, 400.14 s, `verify: SUCCESS` |
| `e061414`, round 8's fixes | 21433 passed, 14 skipped, 406.69 s, `verify: SUCCESS` |
| `f93849e`, round 9's fixes | 21437 passed, 14 skipped, 416.91 s, `verify: SUCCESS` |
| **`91629f3`, round 10's fixes — the figure that governs** | **21439 passed, 14 skipped, 416.59 s, `verify: SUCCESS`** |

The figure that governs is the last, because it is the only one measured on the tree that actually
lands. Rounds 4 through 10 each touch production Python — docstrings at first, then real behaviour changes
from round 7 on (`apply_workspace_edit`'s rollback, `read_message`'s frame contract, the harvest's
failure-mode split, the resolver listing's `configured` flag, round 9's three write-path fixes, and
round 10's `setup.cfg` interpolation fix) — so the gate was re-run on each rather than carried
forward, which is the stale-figure defect this section already records once. The
count rises with each round that closes a finding by adding a guard rather than by bounding it:
21419 → 21420 is round 6's single B4 guard, 21420 → 21422 is round 7's pair pinning the partial-write
rollback (B5), 21422 → 21433 is round 8's eleven — eight driving the seven bad-frame shapes and a
clean-EOF control through the real `serve` subprocess, one for the harvest's `request-failed:` mode,
one for the third `configured` reader, and one for the recoverable-frame stream alignment — 21433 → 21437 is round 9's four (the clean-tree `restore_error` case, the URI-alias normalisation,
and the two line-length clamp guards), and 21437 → 21439 is round 10's pair pinning the `setup.cfg`
interpolation abort. Each delta is exactly the guards named and nothing else.
⛔ **Every commit after the governing one is report-only**, and that is established rather than
asserted: `git diff --name-only {governing}..HEAD -- '*.py'` returns nothing. All three sub-steps ran
on the governing commit: quality-gate (`ruff … All checks passed!`, `mypy … Success: no issues found
in 416 source files`, `SPDX-header check passed`), test-compile (`mypy … 939 source files`), and
module-tests.

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

Ten mutants, each run with **pyright hidden**. Files were snapshotted by the harness itself and
written back in a `finally` — never a git command, which would have rewritten the tree from the
index. `git status --porcelain` was empty before the sweep and empty after it.

⛔ **These ten cover the defects fixed up to `9d375df`, not the branch's full set** — an earlier
revision of this line said "one per fixed defect", which stopped being true the moment a later round
fixed anything. Rounds 7, 8 and 9 fixed eight more (the rollback `pop`, D5's frame contract, the
harvest's budget attribution, the third `configured` reader, the spurious `restore_error`, the
line-length clamp, the URI alias, and B4's absent assertions). **Each of those was red-checked
individually at the time it was fixed** — by reinstating the defect and observing its own guards go
red, recorded per finding in § Findings rounds 7–9 — rather than by extending this table. The two
methods are equivalent in what they establish; the table is simply not the record for those eight.

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

Every guard added by the **deliverable commits** was run against the pre-change tree in a detached
`origin/main` worktree before being declared green. Where a guard would have failed on a *signature*
rather than on behaviour, the pre-change copy was adapted (old constructor call, pre-change defaults,
`getattr` fallbacks for absent names) so the observed failure is the **defect**, not the API change.

⛔ **The guards added by rounds 7–9 were red-checked differently, and the distinction is recorded
rather than blurred under "every".** Those defects did not exist on `origin/main` — they were in the
branch's own code — so a pre-change worktree could not exhibit them. Each was instead red-checked by
**reinstating the defect in place** and observing its own guards fail: the rollback `pop`, `serve`'s
silent end-of-stream, the harvest's `else` arm, the `configured` key-presence test, the
`restore_error` inference, the file-length clamp, and the unresolved URI. Every one is reported with
its red result in § Findings rounds 7–9.

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

`git diff --name-only origin/main...HEAD` → **62 files**, 28 of them `*.py` (re-derived at `91629f3`,
the round-10 fix commit; `report-01.md` is already in that set, so committing this section does not
move it). **Sixteen fall outside** the plan's Expected surface, each for a stated reason — the first
seven from the deliverables, five added by round 4's sweep, and four by round 6's. ⛔ Round 8 added
**three** files and **no** new outside-surface entry: its three code fixes all landed inside the
surface the plan named (`_lsp_jsonrpc.py`, `_corpus_lsp_protocol.py`, `run_config.py` and their test
directories), which is what a round finding defects in the *implementation* rather than in prose
about it looks like on this table:

| File | Why it was touched |
|---|---|
| `doc/user/lsp-code-intelligence.adoc` | D1 made its state table and its count-based write-side rule **false**. |
| `marketplace/bundles/plan-marshall/skills/build-pyproject/SKILL.md` | D4 made four of its Axis-C statements **false**. |
| `marketplace/bundles/plan-marshall/skills/execute-task/SKILL.md` | D1 made its instruction to the consuming leaf **false** — it told a leaf to read every `failed` return as a rejected edit. |
| `marketplace/bundles/plan-marshall/skills/manage-run-config/SKILL.md` | D6/G9 made its `configured` comment incomplete. |
| `.../manage-run-config/standards/run-config-standard.md` | D6/G9 made its definition of `configured` **false**. |
| `test/plan-marshall/extension-api/test_derivation_resolver_roster.py` | D6/G9's *Done when* requires a test **on each side** of the store; this is one side. |
| `test/plan-marshall/manage-run-config/test_run_config_derivation_resolver.py` | The other side. |
| `doc/concepts/code-intelligence.adoc` | Round 4 / sweep: it restated the retired ~97 % false-positive premise as "dominated by", which D5's re-measurement **inverted**. |
| `doc/developer/corpus-language-server-protocol.adoc` | Round 4 / W1: the same retired premise, at the surface a *developer* reads. |
| `.../extension-api/standards/module-discovery.md` | Round 4 / W6: D4 made its Python dependency-string contract (PEP 621 only) **false**. |
| `.../manage-architecture/standards/architecture-persistence.md` | Round 4 / sweep: the same claim as W6, third consumer kind. |
| `.../marshall-steward/references/menu-derivation-resolvers.md` | Round 4 / W2: D6 made its definition of `configured` **false**, at the agent-facing menu that renders the field. |
| `.../build-pyproject/scripts/extension.py` | Round 6 / F1: D4 made **three** of its production docstrings false — including `_distribution_name`'s and `derive_edges`', the method D4's own *Done when* clauses drive. The resolver that owns the behaviour, never opened until round 6. |
| `.../extension-api/standards/ext-point-derivation-resolver.md` | Round 6 / F2: the same claim, in the table the document calls the one place the shipped roster is enumerated. |
| `.../script-shared/scripts/extension/_name_edge_join.py` | Round 6 / F3: the same claim, in the docstring of the module that *performs* the join. |
| `doc/concepts/extension-architecture.adoc` | Round 6 / F3: the same claim, as two labels on the Axis-C description. |

All of them except the two tests are the plan's own carve-in: § Out of scope states this plan changes
*"the documentation that is **inseparable from a behaviour change it lands**"*, and a statement this
run's change renders false is exactly that. The two tests are named by a *Done when* clause. Nothing
else lies outside; the plan's own directory carries `plan.md`, `proposals.md` and this report, as the
Expected surface anticipates.

⚠ **Five of the sixteen were reached only by round 4**, and they split two ways — a distinction an
earlier revision of this paragraph got wrong by claiming all five "were already false before this
branch touched anything adjacent". **Two** were: the `~97 %` premise sites, false since the
re-measurement that predates this branch. **Three** were made false *by this run* — D4 taught the
discoverer Poetry and `setup.cfg`, which falsified the PEP-621-only contract in `module-discovery.md`
and `architecture-persistence.md`, and D6 tightened `configured`, which falsified the resolver menu's
definition. Either way they are the n−1-of-n shape the contract's sweep-and-count rule names, and
they are why the outside-surface count grew in a round that fixed no code.

⛔ **Four more were reached only by round 6, and they are the same claim as one of round 4's** — the
Python dependency-string contract, which D4 falsified and which the run had by then corrected at five
*prose* sites while never opening the code that owns it. That the surface kept growing across three
separate rounds for **one** claim is the strongest evidence this report carries about how the run
fails, and it is what § What have we learned proposes a contract change for.

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
| O1 | `lsp-client/SKILL.md` tells a leaf to run `./pw verify` — this repo's wrapper, in a skill that ships to consumer projects of any ecosystem | **Pre-existing at FOUR sites**, all predating this branch: `SKILL.md:41`, `SKILL.md:157`, `lsp_client.py:27` (the module docstring), and `DIAGNOSTICS_BOUNDARY_NOTE` at `lsp_client.py:77` — the last being a prose literal shipped in **every** `diagnose` payload, so it reaches an operator through machine output rather than through a document. An earlier revision of this row named three of the four. This branch propagated it once and that copy is fixed (W9); the four are owned by `560-documentation-surface-truthfulness` |
| O2 | `_report_omitted`'s notification names the bare script rather than the executor form | Incomplete, not false |
| O3 | `lsp_client.py`'s module docstring enumerates two outcomes; `unknown` is a third, unnamed **there** (it is named in `SKILL.md`, the user page and the code) | Incomplete, not false |
| O4 | The ambiguity guard drops a reference whenever the **target basename** is ambiguous, even for a dotted or relative import to a uniquely-located file | **Bounded:** 0 hits on this repository, always counted under `ambiguous-module-name`, and it is the conservative direction the plan's ⚠ mandates. Cannot change this deliverable's verdict |
| O5 | The D3 "after" figures drift at HEAD (`files_scanned` 1400 vs 1398, references 3194 vs 3189, wall-clock 86.2 s vs 83.4 s) | **Overtaken by the rebase, and both the figures and the explanation given here went false with it** — the drift is not "~2 test files" but PR #1314's 204 added test modules. Round 4 caught it (W7/W8); § D3 now carries the stamped pre-rebase pair plus a re-measurement at HEAD |

### Round 4 — plan verifier

The verifier re-checked all ten round-3 fixes site by site, re-resolved every one of the 15 SHA
citations the rebase forced this report to re-derive, and re-ran the `pm-plugin-development` suite
(**2621 passed / 0 skipped**). Confirmed: all ten V-fixes landed; no retired SHA survives anywhere in
the report; **no vacuous guard**; all six deliverables complete with every ⛔ and ⚠ in the plan
honoured.

**Nine findings — eight of them false statements (condition A), and four of those the *same claim this
run had already fixed at a sibling site*.** That n−1-of-n shape is now the run's dominant defect
class: rounds 2, 3 and 4 each produced it, and each time the missed site was reached by a *different*
kind of consumer than the ones fixed. All nine closed in this commit.

| # | Finding | Disposition |
|---|---|---|
| W1 | `doc/developer/corpus-language-server-protocol.adoc:92` — a **fifth** site of the retired ~97 % false-positive premise. The run fixed four, then V7 fixed a fifth; this is the sixth surface and the one a *developer* reads | **fixed** — the decision (withheld) is kept, the retired figure is marked retired, and the open question is xref'd to the skill rather than restated |
| W2 | `menu-derivation-resolvers.md:51` still defined `configured` as "whether an explicit entry exists" — the pre-D6 definition, at the **agent-facing menu** that `extension_api.py`'s own new comment names by hand as the reason the definition was tightened | **fixed** — an explicit **mapping** entry, with the malformed-entry case stated |
| W3 | `doc/user/corpus-language-server.adoc:211` — "`query` separates the other four" is contradicted by its own table two rows later: cause 3 is "Not separately signalled" | **fixed** — three of four, with the fourth named and its bound stated |
| W4 | `doc/user/lsp-code-intelligence.adoc`'s NOTE said `preflight` "reports the same situations" over a table that gained an `unknown` row in this branch. V10 fixed the `lsp-client/SKILL.md` sibling of exactly this sentence and left the user page | **fixed** — the note now names the configuration states it does report and says `preflight` never returns `unknown` |
| W5 | Inside **V6's own new sentence** in `execute-task/SKILL.md`: "nothing on disk changed in either case" is false for `apply_failed` when the rollback itself fails — the very case D2 added `restore_error` for | **fixed**, and the same omission fixed at its three siblings (`lsp-client/SKILL.md`, `lsp_client.py`'s docstring, the user page), which the verifier did not name |
| W6 | `extension-api/standards/module-discovery.md:300` still described the Python dependency string as PEP-621-only after D4 taught the discoverer Poetry and `setup.cfg` | **fixed**, and the same claim fixed at `manage-architecture/standards/architecture-persistence.md:167` — a site the verifier did not name, and the *third* consumer kind of this one sentence |
| W7 | § D3's baseline table went stale in the rebase (`files_scanned`, references, `out-of-workspace`, `vendor-tree`, wall-clock), and carried no stamp saying which tree it was measured on | **fixed** — the pair is stamped as one measurement on the pre-rebase tree, and re-measured at HEAD |
| W8 | § Findings O5's numbers **and** its explanation both went false in the rebase: the cause is #1314's 204 added test modules, not "~2 test files" | **fixed** — the row records that it was overtaken, rather than being quietly restated |
| W9 | The new fail-closed paragraph in `lsp-client/SKILL.md` added a **`./pw verify`** instruction — this repository's wrapper — to a skill that ships to consumer projects of any ecosystem. The verifier offered a bound and recommended the fix instead | **fixed** — "the project's architecture-resolved `verify` command". ⚠ The **four** pre-existing sites (round 3's O1, whose own count round 5 corrected — see there) are **untouched**: they predate this branch and are owned by `560-documentation-surface-truthfulness`. This branch no longer *adds* to them |

⚠ **What round 4 says about this run.** Four of its eight condition-A findings (W1, W2, W4, W6) are
sibling sites of claims this run had already corrected, and two more (W5 inside V6's sentence, W8
inside the round-3 record) are defects introduced by the *previous round's own fixes*. The lesson is
recorded in § What have we learned rather than repaired by one more sweep: a fix to a false statement
is not complete until the claim — not the file — has been swept.

### Round 5 — plan verifier (the budget's last round)

The verifier re-checked all ten round-4 fixes, swept each corrected claim to every site, re-derived
the report's figures **by executing** them, and ran a mutation pass for vacuity. **Twelve findings:
nine false statements (condition A, all fixed here) and three behavioural survivors (condition B,
each left open with a bound).**

Reproduced independently, by execution: `./pw verify` at HEAD (**21419 passed, 14 skipped**,
`verify: SUCCESS`); **every cell** of § D3's "At HEAD" column, including the `vendor-tree` 0 and
`unresolved-symbol` 751 this run could not explain; **177** search paths and the single ambiguous
basename; the validator's 308 / 5083 / **61** and its 26 / 31 / 4 split; the `pm-plugin-development`
suite at **2621 passed / 0 skipped**; all 17 SHA tokens resolving to ancestors of HEAD; the collateral
55 / 24 / twelve-outside. It found **no vacuous guard** other than B1's uncovered branch.

| # | Finding | Disposition |
|---|---|---|
| A1 | `lsp_client.py:275`, `_edit_failure`'s docstring — "nothing is left modified on disk". The **fifth** site of the claim W5 retired at four, and the first in production code | **fixed** — the helper now states that it decides nothing about the tree, and names the state each of the five reason/phase combinations leaves it in |
| A2 | `_lsp_workspace_edit.py:17` — "so no caller can observe a half-applied edit". Sixth site, same claim | **fixed** — a caller observes one in exactly the `restore_error` case, and the docstring says so |
| A3 | `lsp-client/SKILL.md` and the user page both said `edit` "rolls back" on `diagnostics_unavailable`. **Measured**: the `phase: before` branch returns `rolled_back: false` because *nothing was ever written* — and for a pull-diagnostics server that is the **mainline** return, not a corner. W5's own new instruction ("`rolled_back: false` … the tree is then left partly edited") therefore made a leaf read this payload exactly backwards | **fixed** at all three consuming sites — the two `phase` routes are now tabulated, `unverified_path` is documented, and the `rolled_back: false` rule is scoped to "**together with `restore_error`**, never alone" |
| A4 | § Residue — "this branch's 50 changed files". It is 55; `b11e5cc` re-derived that count for § Collateral check and did not sweep this sibling. The intersection is still **empty** (re-derived) | **fixed** |
| A5 | § Residue ×2 — "seven test directories". Six changed; `test/plan-marshall/build-npm` is in the Expected surface but no file there changed | **fixed** |
| A6 | § Cost — "26 h 58 m", measured two commits earlier | **fixed** — stamped, and stated as a lower bound the report's own commits extend |
| A7 | § Collateral check — "every one of them was already false before this branch", **introduced by `b11e5cc` itself**. True of two of the five; the other three were falsified by D4 and D6 | **fixed** — the five are split by which made them false |
| A8 | § Findings O1 / W9 — the pre-existing `./pw verify` sites enumerated as three. There is a fourth: `DIAGNOSTICS_BOUNDARY_NOTE`, a prose literal shipped in **every** `diagnose` payload, which reaches an operator through machine output rather than a document | **fixed** at both rows; the handoff to `560` now names four |
| A9 | § D3 — "covering **every** `scripts/` directory the plan names". 69 of 70; `platform-runtime/scripts` is excluded by the structural rule because it carries `__init__.py` | **fixed** — with B3's bound stated inline |

⛔ **The contract's five-round budget was spent here, and the boundary question was PUT TO THE
OPERATOR rather than decided by the run.** They were told that the loop was not converging — round 5
produced *nine* condition-A findings against round 4's eight, and both of round 4's structural
patterns recurred — and they **extended the budget to ten rounds, to run until it converges**. The
loop therefore continues past round 5; everything condition A forbids leaving open is fixed in this
commit regardless, and condition B's three survivors are carried into the next round for re-checking
rather than closed here.

⚠ **Both of round 4's structural patterns recurred in round 5, which is the finding about the run
rather than about the code.** A1/A2/A3 are the n−1-of-n shape *again*: W5 swept four sites of the
"nothing changed on disk" claim and left two production docstrings and one reason-code sibling.
A4–A7 are all in this report's own prose — three figures `b11e5cc` re-derived for one section without
sweeping the others, and one claim `b11e5cc` newly introduced. The run has now produced both patterns
in five consecutive rounds; § What have we learned proposes the contract change that follows from it.

### Round 6 — plan verifier (first round of the extended budget)

The verifier swept all eight claims the previous two commits corrected, re-derived the report's
figures by executing them, and ran four mutations. **Eight condition-A findings and one new
condition-B finding (B4).** All nine closed here — B4 by a test rather than a disclosure.

Reproduced independently, by execution: `./pw verify` at HEAD (**21419 passed / 14 skipped**,
`verify: SUCCESS`, mypy over 416 production + 939 test files); the validator's 308 / 5083 / **61**
and its 26 / 31 / 4 split; the harvest twice (**72** cross-bundle, **10** edges, **0** `.venv`
targets, 1602 / 3549); **177** search paths and the single ambiguous basename; **70** bundle-skill
`scripts/` directories, exactly one carrying `__init__.py`; the Poetry and setuptools fixtures
through the **real** `BuildExtension.derive_edges`; the 55-file / 24-`*.py` / six-test-directory
diff; all 20 SHA tokens resolving to ancestors of HEAD; G25's asserted absence.

| # | Finding | Disposition |
|---|---|---|
| F1 | ⭐ **The PEP-621-only contract survived in the owning resolver's own production docstrings** — `build-pyproject/scripts/extension.py` at three places: the module docstring ("what a Python distribution DOES publish is its PEP 621 `[project] name`"), `_distribution_name` ("a directory that declares no `[project] name` publishes no distribution"), and `derive_edges` ("each module publishes a `[project] name`"). Measured false through the real path: the Poetry fixture publishes `poetry-core-lib` from `[tool.poetry]`, the setuptools fixture `setuptools-core-lib` from `setup.cfg [metadata]`, and `derive_edges` — the exact method D4's *Done when* (a) and (b) drive — yields three edges for each | **fixed** at all three. The docstrings now describe the field (`metadata.name`) rather than the descriptor, which is what the resolver actually reads |
| F2 | The same claim in `ext-point-derivation-resolver.md:227` — the table the document itself calls the one place the shipped roster is enumerated | **fixed** |
| F3 | The same claim in `_name_edge_join.py`, the docstring of the module that *performs* the join, plus two labels in `doc/concepts/{code-intelligence,extension-architecture}.adoc` | **fixed** at all four |
| F4 | § Left open called B1 "the one vacuity gap in the branch". **False when written** — `b0d746c` had created a second (B4) in the same commit that closed round 5 | **fixed**; the sentence is now a re-derived measurement rather than a property claim |
| F5 | § Findings O1's cite `SKILL.md:142` now points at the sentence **W9 installed**; the real fourth `./pw verify` site is `:157`. The *count* of four was right | **fixed** — all four re-derived and confirmed byte-identical on `origin/main` |
| F6 | § Left open's B2 cited `lsp_client.py:373`/`:391`; `b0d746c`'s 15 added lines moved them to `:383`/`:403` | **fixed** |
| F7 | § D3's "At HEAD" table published two cells with no measurement stamp, and the verifier's own re-run **did not reproduce them** (`vendor-tree` 465 vs 0, `unresolved-symbol` 293 vs 751) — while every load-bearing cell reproduced exactly | **fixed** — conditions stamped, and the ⚠ the run had left open is now answered: 465 + 293 ≈ 0 + 751, so the two cells trade off according to what the server has indexed. They are recorded as a pair whose **sum** is stable and are not to be compared across runs |
| F8 | § Build gate carried a sentence twice, in two variants, introduced by `9552d75` | **fixed** |
| B4 | New: `phase` and `unverified_path` were asserted by **no** test while four documents described them — all four added by `b0d746c` | **closed by a test**, not bounded — see § Left open |

⛔ **Round 6's own verdict on convergence: not narrower, and it said so.** Four findings (F5–F8) are
genuinely narrower than anything round 5 produced — two line-number drifts caused mechanically by one
commit, one missing stamp, one editing artefact. **F1–F3 are not.** They are a claim family the run
had corrected at **five prose sites and never once in code**, and the residue sat in the production
docstrings of the very resolver whose `derive_edges` D4's *Done when* clauses drive. The verifier's
own words: *"a widening search radius, not a converging one — the loop is finding fewer things
because each round's sweep is aimed at the previous round's claim, and a new claim family surfaces
each time it widens."*

⚠ **The sweep now has a rule that would have caught F1–F3, and it is the lesson of this round:** a
claim about *what the code does* is not swept until the **code that does it** has been read. Rounds
2–5 swept prose from prose. Round 6 is the first to reach a production docstring in a file the branch
never opened.

### Round 7 — plan verifier (the method changed, and it found the run's only false-clean)

Round 6 diagnosed *why* the loop was widening: each round's sweep had been aimed at the previous
round's **claim**. So round 7 was dispatched with a different method — start from the **behaviour**
each deliverable changed, execute it, and work outward to every statement about it, in whatever file
that statement lives. ⭐ **The method change is what found A2/B5**, and nothing else would have: five
consecutive rounds had swept the *statements* about rollback across eight sites without ever running
the path they describe.

**Nine findings — eight condition-A and one behavioural. All nine closed here, B5 by a fix and a
guard rather than a bound.**

| # | Finding | Disposition |
|---|---|---|
| A2 / B5 | ⛔ **A mid-write failure left a damaged file on disk and reported a clean rollback.** `apply_workspace_edit`'s handler ran `originals.pop(path, None)` — dropping the failing file's pre-edit content from the restore set *exactly and only* when a write had already truncated it. Every other failure shape never records an original, so the `pop` fired **only** in the case where it did harm. Reproduced: a three-file edit whose middle write truncates then raises ENOSPC left `b.py` **empty**, with `restore_error: None` and a payload saying `rolled_back: true`. That is a **false clean** — the single defect class this entire plan exists to remove — inside the code D2 shipped, and it falsified eight statements across three production docstrings, two skill contracts and the user page | **fixed** — the failing path stays in `originals`, so the file the write damaged is the one that gets restored. Two guards pin it: a transient failure now restores all three files, and a persistent one reports `restore_error` instead of claiming success. Red-checked — reinstating the `pop` fails both, and the eight statements are true again without editing any of them |
| A1 | `_edit_failure`'s docstring, inside round 5's own A1 fix: "every caller passes its own `rolled_back`, and the **three** failure reasons". Executed: `unsupported_resource_operation` passes **no** `rolled_back` and the key is absent from its payload, and the same sentence then enumerates **four** reasons | **fixed** — the four are listed, each with the state it leaves and what it passes |
| A3 | `corpus-language-server-protocol.adoc:92` — "before that precision work **lands**", the exact phrase round 3's V7 judged false and removed from the corpus `SKILL.md`. Round 4's W1 edited this very line and left it | **fixed** |
| A4 | `doc/concepts/code-intelligence.adoc:61` — "a Python distribution publishes a single PEP 621 `[project] name`". **Seventh** site of that family; the branch edited this file twice (`:286`, `:308`) and left `:61` | **fixed** |
| A5 | `test_pyproject_derivation_resolver.py` — the test module of the resolver D4 changed, false at four places: the join described as PEP-621-only, "dependency extraction is pure `pyproject.toml` parsing" (it is `configparser` for `setup.cfg`), and twice that `toolbox` "declares no `[project] name`" where the true premise is that it names itself in **no** descriptor | **fixed** at all four, and in the fixture comment that states the same premise |
| A6 | § Residue — "this branch's **55** changed files", the **third** recurrence of one unstamped count (50 → 55 → 59). Round 5's A4 fixed it and named the cause; `bb41ae2` re-derived it for § Collateral check and again did not sweep this sibling | **fixed** — and stamped with the commit, so the next drift is visible rather than silent. The intersection itself re-verified **empty** |
| A7 | § Left open's B1 mutation figure, "58 passed", stale by the very growth B2's row already records | **fixed** — restated so the *greenness* is the finding and the count is stamped, since it rises whenever the directory gains a guard |
| A8 | § D3 and § Left open both said **two** bare imports target `platform-runtime/scripts`. There are **three** — `permission_doctor.py:27` was unnamed. The bound is unaffected | **fixed** at both |

⚠ **What round 7 changes about this run's story.** Every previous round found statements. This one
found a **defect**, and it found it by executing the code the statements describe. The eight false
statements A2 produced needed no editing once the code was fixed — they had been describing the
*intended* behaviour all along, and the code was the thing that disagreed. ⛔ That inverts the
sweep's assumption: rounds 2–6 all asked "which statement is stale?", and the answer here was "none
of them — the code is". A run that only ever sweeps prose against prose cannot reach that answer.

### Round 8 — plan verifier (the method applied to the deliverables round 7 did not reach)

Round 7's method — execute the behaviour, then sweep outward — was applied to D1, D3, D4, D5 and D6.
**Nine findings across five deliverables, two of them defects in the CODE rather than in a statement
about it. All nine closed here; three closed by changing behaviour, not prose.**

The verifier ran 17 mutations (17 killed, 0 survivors), a static AST scan of every added test
function (**78** at `0acfa7e`, the commit round 8 read; the branch carries more now, and the figure is
stamped because it moves with every guard a later round adds), and re-derived every load-bearing
figure by execution: `files_scanned` **1602**, references **3549**, cross-bundle **72**, module edges
**10**, `.venv` targets **0**, **177** search paths, one ambiguous basename, **70** bundle-skill
`scripts/` dirs with exactly one carrying `__init__.py`, the validator's 308 / 5083 / **61**, all SHA
tokens ancestors of HEAD, and the gate at **21422 passed / 14 skipped**.

| # | Finding | Disposition |
|---|---|---|
| F4 | ⭐ ⛔ **D5's own title clause — "survives a bad frame" — was false, and had been since `9d375df`.** That commit guarded the *handler*; `read_message` sits **outside** the guard and returns `None` for every malformed shape, which the loop reads as "the client is gone". Measured across seven frame shapes — bad JSON, short body, negative length, non-integer length, JSON array, invalid UTF-8, no `Content-Length` — **all seven ended the session, and every one wrote nothing to stderr.** The plan's paired requirement (a stderr line so a swallowed failure cannot hide) was unmet on this path. The contrast is inside this branch: the *client* transport it shipped is explicitly per-message resilient | **fixed in the code.** `read_message` now raises `FrameError` and keeps `None` for end-of-stream alone. A frame whose declared body was read whole leaves the stream aligned, so it is logged and **skipped**; one whose length was unusable ends the session — but on stderr, never silently. **Eight** guards drive all seven shapes plus a clean-EOF control through the real `serve` subprocess (the round's other three cover the harvest's new mode, the third `configured` reader, and frame alignment at the unit level); all seven go red against the old behaviour |
| F3 | **A post-handshake failure reported the *handshake's* budget.** One `else` covered both branches, so a per-file request that failed after 35 s was reported as "did not respond within 1s" — the exact defect the `server-rejected` split was added to remove, one layer further in, in an operator-facing string. Four docstrings around it were false too: `timeout_s` "bounds the definition requests in aggregate" (it is tested *between* calls, so it cannot interrupt one in flight, and exceeding it reports `ran=True` with a `harvest-budget:` note, never a timeout) | **fixed in the code** — a distinct `request-failed:` mode that quotes **no** budget, because none was set for it, and reports elapsed harvest time instead. A guard drives a server that completes the handshake and then answers nothing; the failure-mode set assertion gained the sixth prefix. Red-checked |
| F5 | **A third reader of the `configured` store, using the pre-D6 definition.** D6 unified two readers; `cmd_derivation_resolver_list` iterates on key presence and called its result "the configured resolver entries" — in a docstring, an argparse **epilog**, a standards table and a SKILL body | **fixed in the code**, and the fix is deliberately not "make `list` hide malformed entries": omitting one would hide an operator's own typo from the verb that exists to show them the store. Each row now carries its own `configured` flag under the shared dict test, so the listing stays complete **and** the three readers agree. A guard asserts both halves against `{"markdown": "yes"}` |
| F6 | `dependency-intelligence.adoc`'s "*The fallback is all-or-nothing per file*" over-states the rule. Executed: when an earlier form supplies dependencies but **no name**, the later form is consulted and its dependencies are **appended** | **fixed** — the gate is the *name*, and the union case is stated with its bound (reachable only from an invalid PEP 621 descriptor; a union, never an override, so no declaration is lost) |
| F7 | Three D1 statements this branch itself wrote: `wait_for_diagnostics` waits "for `settle` seconds of quiet on the **inbound stream**" (measured: a server pushing `$/progress` every 20 ms did **not** extend the wait — quiet is measured on diagnostics alone); the module docstring's "notifications — **buffered**" (measured: 200 `$/progress` notifications retained nowhere); and `WorkspaceApplyError`'s "raised once every file … has been restored" | **fixed** at all three, each now stating what the code does and why |
| F1 | § Left open's **B1 row false in every clause**, and round 6's F4 disposition ("fixed") false about it | **fixed** — see the B1 row, which now records how it closed |
| F2 | § Left open's B2 line citations stale for the **third** time | **fixed**, with the recurrence itself recorded |

⛔ **Two more places where the CODE was wrong, not the statement.** Round 7 found the first (the
rollback discarding the file it damaged). Round 8 found F4 and F3. In all three the surrounding prose
described the *intended* behaviour correctly and the implementation did not — which is why five
rounds of sweeping prose against prose could not reach any of them, and why the method change is the
single most valuable thing this verification loop produced.

⚠ **F4 is the most serious finding of the run by deliverable impact:** a deliverable marked *Done,
(a)–(e) met* across seven verification rounds did not have the property its own title claims. Nothing
caught it because every round read the *handler* boundary — where G1's evidence was — and no round
had ever fed the server a malformed frame.

### Round 9 — plan verifier (the seams the previous rounds' own fixes opened)

Round 9 drove the behaviour round 8's fixes created, and executed families no round had ever run.
**Fifteen findings — seven condition-A and eight condition-B, three of the latter defects in the
code.** All seven condition-A findings are fixed here; four condition-B findings are **closed** by a
fix and a guard rather than bounded, and the remainder carry bounds.

⭐ **The round's most important finding is that round 7's own fix falsified four statements the loop
had just declared true.** This is the first fix-induced regression in nine rounds, and it is the
strongest evidence yet for the contract change § What have we learned proposes.

| # | Finding | Disposition |
|---|---|---|
| A2 / B | ⛔ ⭐ **A write that fails BEFORE truncating reported a partly-edited tree over a clean one.** Round 7 correctly stopped discarding the failing path from `originals` — but a write that fails at `open()` (EACCES, EPERM, EROFS, an immutable file) never truncates, so "restoring" that path is a rewrite of untouched content that fails for the same reason, setting `restore_error` over a tree nothing modified. Reproduced with a real immutable file, **not a monkeypatch**: `restore_error: PermissionError`, `TREE CLEAN: True`. Four contracts assert the converse — and `lsp-client/SKILL.md` named **"a read-only path"** as its example, the exact input that refutes it | **fixed in the code.** `restore_error` is now derived by **re-reading the footprint**: it is set only when some file's content actually differs from what was captured, and an unreadable file counts as modified (fail-closed). The false alarm is the mirror of a false clean and misleads a leaf as much. The four statements are true again — and the SKILL example is corrected, since a read-only path now reports **no** `restore_error`. Guard added, red-checked |
| B4 | ⛔ **Two URI spellings for one file produced a genuine false clean.** `path_to_uri` resolves, `uri_to_path` did not, so `/t/a.py` and `/t/./a.py` became two entries for one document; the second captured its "original" from disk *after* the first had written it, and the rollback restored a state the file had never been in while reporting `rolled_back: true`. The same defect class round 7 closed, reached by a different input | **fixed in the code** — `uri_to_path` resolves, so aliases normalise to one key and one footprint row. Guard added, red-checked. Aliasing is a server defect; a false clean is the one outcome this write path may not produce whatever the server does |
| B1 | ⛔ **`_position_to_offset` clamped an over-long `character` to the FILE length, not the line length**, in violation of an explicit LSP 3.17 rule. The standard end-of-line idiom `[line, 0]-[line, 2147483647]` therefore replaced everything from that line to EOF: a one-line rename silently truncated the file. **Pre-existing on `origin/main`**, covered by no test | **fixed in the code** — the clamp stops at the line's content, excluding the terminator (clamping one character further would join two lines, a subtler wrong answer). Two guards, red-checked. The diagnostics gate caught most such wreckage because it gained errors; a tail of comments or data added no *new* error diagnostic and was accepted |
| A1 | The comment justifying the fallback's **direction** in `lsp_harvest.py` described the conjunction `e061414` had just replaced — i.e. it described defect F3 itself. The fix commit edited six lines below it and did not sweep it | **fixed** — the marker is consulted for the handshake only, and the comment now states the bound that follows |
| B2 | The unrecoverable arm's "ends the session" half was pinned by **no** test: deleting its `return 0` left the directory 100/100 green, because a desynchronised reader fails to answer the next request whether it stopped or not | **closed by a guard, not bounded** — asserted on the stderr line **count**, the one thing that distinguishes ending from stumbling on. Three of the four arms now kill the mutant; the short-body arm consumes the rest of the stream and is inherently unobservable, which is recorded rather than papered over |
| A3 | § Findings round 8 said "**eleven** guards … through the real `serve` subprocess". Eight do; the other three cover the harvest, the `configured` reader and unit-level alignment — **the report contradicted its own commit message** | **fixed** |
| A4 | § Mutation sweep's "ten mutants, **one per fixed defect**" went false the moment a later round fixed anything; the branch has fourteen | **fixed** — the table is scoped to the defects it covers, and rounds 7–9's eight are recorded as red-checked in place, per finding |
| A5 | § Red-then-green's "**every** new guard was run … in a detached `origin/main` worktree" is false for thirteen guards — their defects were in the *branch's* code, so no pre-change worktree could exhibit them | **fixed** — the two red-check methods are now distinguished rather than blurred under "every" |
| A6 | A test docstring generalised "unrecoverable means the bytes were not eaten" across all four arms; false for the short-body arm, which consumed the stream | **fixed** |
| A7 | "78 added test functions", unstamped | **fixed** — stamped as **78 at `0acfa7e`**, the commit round 8 read. ⛔ The fix's own first draft said "92 at HEAD", which was the count at `e061414` and 96 two commits later: a moving figure restated inside the correction of a moving figure. No live count is quoted here now — the figure is measured per commit and stamped, or not given |

**Left open with bounds** (the verifier's B3, B5–B8): a frame truncated *inside* its header block ends
the session silently (EOF was genuinely reached, so the session must end either way; only the operator
distinction is lost, and `read_message`'s own comment documents it); `normalize_changes` silently drops
malformed `documentChanges` entries (requires a malformed server edit); a `null` URI raises out of
`capture_footprint` to `safe_main` (identical in shape and cost to survivor B2 — an error, never a
success); a `request-failed:` discards accumulated notes (`ran=False`, so no caller reads them); and an
unparseable or BOM-prefixed file is a silent scanned-but-empty file (affects recall only, never
attribution, and the `unresolved-symbol` count already discloses the shortfall).

### Round 10 — plan verifier (the last of the extended budget)

Round 10 executed the seven behaviour families round 9 named as never swept by any round, and
re-drove the seams round 9's own fixes created. **Ten findings — nine condition-A and one condition-B
that no bound could cover. All ten fixed here.**

Three of the seven families came back **genuinely clean** (corpus cache invalidation, the module
lift, `hover`/`stats`); one clean by measurement with an over-stated word; three yielded — and the
last of those produced the round's worst finding, on **legal input**, in this branch's own new code.

| # | Finding | Disposition |
|---|---|---|
| B-1 | ⛔ ⭐ **A percent sign in a `setup.cfg` value aborted the entire Python module discovery.** `_read_setup_cfg` built a default `ConfigParser`, whose `BasicInterpolation` raises from `get()` — **not** from `read()` — and the `get` calls sat *outside* the guard. `description = 100% pure python`, or a percent-encoded direct-reference URL, therefore escaped `discover_python_modules` and took **every** module with it, including the ones whose descriptors parsed perfectly. No malformed input, no filesystem failure, no server: ordinary text in a metadata field, and the capability answered nothing at all. **New in this branch** — `_read_setup_cfg` is D4's own code, and this is precisely the failure mode D4's narrowed `_load_toml` catch was written to remove, re-committed one function below it | **fixed** — interpolation disabled (these values are metadata, never templates) and every read moved inside the guard. Two guards, over a **multi-module** tree because the defect's signature is that the innocent siblings vanish too; red-checked |
| A-1 | § Left open's B2 line citations, stale for the **fourth** time — invalidated by round 9's own fix commit | **fixed by removing them.** The two call sites are now named by *what they are*, which no commit can invalidate. Four recurrences of one defect is enough evidence that the remedy is to stop citing lines, not to re-derive them again |
| A-2 | The row fixing an unstamped moving figure introduced a second one in the same sentence ("92 at HEAD", which was the count at `e061414` and 96 two commits later) | **fixed** — no live count is quoted; the figure is stamped per commit or not given |
| A-3 | "**both** importers are inside the `plan-marshall` bundle", twice, each within two sentences of correctly saying there are **three**. Residue of round 7's A8, which fixed the count and left the dependent quantifier | **fixed** at both |
| A-4 | § Left open said "**B2 and B3 are the only genuine survivors**" while rounds 9 and 10 had left ten more open with bounds *elsewhere in this report* — so the section a reader consults for what remains carried almost none of it | **fixed** — all twelve open survivors are now listed there, with their bounds and their reproductions |
| A-5 | `_still_modified`'s docstring promised that an unreadable file counts as modified; a non-UTF-8 file **raises** instead, because `UnicodeDecodeError` is not an `OSError`. Round 9's own text | **fixed in the code** — the exception is caught, so a file truncated mid-multi-byte-character no longer replaces `WorkspaceApplyError` and cost the caller `failed_path` and `restore_error` |
| A-6 | `uri_to_path`'s docstring promised a fallback when "the filesystem refuses the walk"; a **symlink loop** raises `RuntimeError`, which `except OSError` does not catch. Round 9's own text | **fixed in the code** |
| A-7 | "`setup.cfg` gives runtime only … **because it has no `dev` equivalent**" — it has one, `[options.extras_require]`. A true limitation with a false reason | **fixed** — the limit now says the analogue exists and is not read yet |
| A-8 | The clamp comment's "the LINE LENGTH excludes the terminator" is false for CRLF, where it excludes only the `\n`. Round 9's own text | **fixed** — with the reason it does not arise through `apply_workspace_edit`, and that this is a *disclosed limit* rather than a mitigation |
| A-9 | `expected_tokens`' "the target's **discriminating** final segment" — measured: **18** tails are shared, `extension` by four components and `plan-marshall-plugin` by eleven | **fixed** at both sites, with the measurement, and with why the full-notation match therefore outranks a tail-only one |

⛔ **Four of round 10's nine condition-A findings are statements round 9 itself wrote** (A-5, A-6, A-8
in the files its fix edited; A-1 and A-2 in the report commit that accompanied it). Round 9 called its
own discovery of this "the first fix-induced regression in nine rounds". Round 10 makes it **two
consecutive rounds**, which is what turns it from an incident into the finding § What have we learned
is built on.

### Independent re-check of round 9's fixes, and what carries NO independent verification

⭐ **Round 9's verifier re-ran its own harnesses against `91629f3` after the fixes landed** — not a
re-read, the same executed reproductions — and closed five findings on its own evidence:

| id | At `a2bff58` | At `91629f3` |
|---|---|---|
| A2 | immutable file → `restore_error: PermissionError` over a **clean tree** | `restore_error: None`, tree clean |
| B4 | two URI spellings → two footprint rows, rollback left `THREE\n` with `rolled_back: true` | one key, `edit_count: 2`, **`ROLLBACK CORRECT: True`** |
| B1 | `[0,0]–[0,2147483647]` replaced the whole file with `'X'` | `'X\nbeta\ngamma\n'` |
| B2 | mutation M1 left the directory **100 passed** | M1 **killed** |
| A1 | the comment described the conjunction already replaced | states the handshake-only bound |

It also confirmed **no regression from the A2 fix**: reinstating round 7's defect is still killed by
its own guard, and the two suites carrying the new guards report **126 passed**.

⛔ **What no verifier has independently checked**, stated plainly rather than left to inference:

- **Round 10's own ten fixes.** Round 10 *found* them; the run fixed them and red-checked each by
  reinstating the defect, but no verification round has run against `91629f3`. The `setup.cfg`
  percent-sign fix (`B-1`) is the one that matters most here — it is a **behaviour** change to
  production code, and its evidence is the run's own two guards and its own red-check.
- **Which four report claims `f93849e` corrected.** Round 9's re-check names this as unre-derived.
- **Round 9's bounded B-items** (`S2`, `S4`–`S12` in § Left open) were not re-verified after the
  fixes; their bounds rest on round 9's and round 10's original reproductions.

⚠ **This is a consequence of stopping on a spent budget, and it is the honest shape of that
stop** — a loop that ends after a round of fixes always ends with its last fixes unverified. Round
10's own recommendation was to fix and stop rather than open another round; the alternative is not
"verified everything" but "one more round of fixes, itself unverified".

### How the loop stopped

**Exit: `budget-exhausted, non-converging`.** Both tokens are load-bearing and neither is a
formality.

**The budget.** The lane contract's budget is five rounds. Round 5 spent it, and — the operator being
reachable — the boundary question was **put to them** rather than decided by the run. They were told
the loop was not converging and **extended it to ten rounds, to run until it converged.** It did not.
Round 10 is the tenth and no further extension was sought, so the loop ends on a spent budget, not on
a clean verifier.

**The verifier's own last answer**, asked directly and recorded rather than paraphrased: *"Does
anything you found remain that condition A or B forbids leaving open?"* — **Yes**, nine condition-A
statements and one condition-B finding (`B-1`) that no bound could cover. **All ten are fixed in
`91629f3`.** Everything condition A forbids leaving open is closed; `B-1` was fixed rather than
bounded because the cost of leaving it was the *entire* discovery result, silently.

**Were the late rounds' findings narrower, or merely fewer?** ⛔ **Neither — and this is the finding
the exit qualifier records.** Per round, condition-A findings ran 20, 10, 9, 9, 8, 8, 9, 9: flat, not
decaying. Round 10's own summary is quoted rather than softened: *"the loop has not converged and it
will not converge by running more rounds, because the finding rate is not decaying."*

**What each round's findings were made of is the real story**, and it changes twice:

| Rounds | Method | What they found |
|---|---|---|
| 1–6 | Read the statements, compare them to each other | Stale prose only. **Zero** code defects |
| 7–8 | **Execute the behaviour**, then sweep outward | Three code defects, incl. a deliverable whose own title clause was false for seven rounds |
| 9–10 | Execute the seams the previous fixes opened | Four more code defects — **and two consecutive rounds in which the previous round's fix had falsified statements in the files it edited** |

⭐ **Six of the seven code defects this run fixed were found after round 6, by executing rather than
reading.** Five rounds of prose-versus-prose sweeping found none of them. That is the single most
transferable thing this run produced, and § What have we learned proposes the contract change that
follows from it.

**Residue a reader should assume remains.** Stated as the verifier stated it, not softened: the write
path is correct for content but **not for line endings**, and its own clean-tree check cannot see a
line-ending-only change (`S1`). Both discoverers crash rather than degrade on descriptors that are
syntactically valid but structurally wrong (`S5`). The diagnostics gate assumes a spec-conforming
server and leaves an edit on disk if it does not get one (`S2`, `S9`). Poetry's legacy and non-`dev`
groups produce no edges, undisclosed (`S4`). **None of these can produce a false clean success — the
class this plan exists to eliminate — except `S1`, which is bounded to line endings.** All twelve are
in § Left open with their bounds and their reproductions.

**What a further round would have to execute**, recorded so a successor plan need not re-derive it:
the families round 10 left unswept after finding four of seven productive — chiefly the npm workspace
resolution paths, `diagnostic_key` under duplicate-with-different-severity, and the corpus index's
behaviour when the corpus changes size mid-session. ⚠ The verifier's own recommendation, adopted
here, is that this is **not** worth another open-ended round: the correct closing move was to fix
`B-1`, fix the condition-A statements, and stop and disclose.

## Reviewer participation

**Not done — no PR exists.** The run has not reached Step 7: it is still inside Step 6's verification
loop, whose budget the operator extended from five rounds to ten. No reviewer has been invited, so
there is no population to report a verdict for, and this section is filled after the PR is created,
not before. Reporting it as *not done* rather than as *not applicable* is deliberate — the step is
owed, it has simply not been reached.

## Cost

- **Tokens:** not available to the agent in this session.
- **Wall-clock:** **≥ 32 h 10 m** — `cdf8062` (2026-08-20T08:49:01Z) to `91629f3`
  (2026-08-21T16:58:51Z), across **33** commits. Source: `git log --format=%aI origin/main..HEAD`, first vs last —
  **author** dates, deliberately: the rebase reset every *committer* date to the rebase instant, so
  `%cI` would report a span of one minute. ⛔ **Stamped and a lower bound by construction**: every
  commit after the one named extends it, including the commit carrying this sentence. An earlier
  revision published `26 h 58 m` unstamped and it was stale two commits later — the same
  moves-with-every-commit defect § Build gate stamps against, committed a second time in a different
  section; a later revision published `≥ 27 h 53 m`, stamped, which this supersedes at the last
  commit. ⚠ This is elapsed span, **not** time worked: the run was idle across a long gap while
  waiting for PR #1314 to land, and no attempt is made here to net that out.
- **Population:** this single Claude Code cloud session's usage. ⛔ **Not comparable** to a
  plan-marshall `metrics.toon` total, which counts the orchestrator-plus-agent dispatch tree under
  plan-marshall's own per-task billing boundary — a boundary an interactive cloud session does not
  share. The figures are not made comparable and no parity is implied.

## Contract check (Step 9)

Per step, with the artifact that proves it. Steps not reached are reported **not done** rather than
narrated as complete.

| Step | Verdict |
|---|---|
| 1 Skills loaded | **Done** — named in § Skills loaded, loaded by bundle source path because the plugin is not installed in a cloud session |
| 2 Branch | **Done** — `claude/lsp-derivation-resolver-correctness-7ncdpz`, the **harness-assigned** form, kept as the contract requires and recorded as such; present on `origin` |
| 3 Plan directory | **Done** — `doc/plans/code-intelligence-substrate/500-lsp-and-derivation-resolver-correctness/` with `plan.md`, `proposals.md` and this report |
| 4 Implement | **Done** — six deliverables, 33 commits, every one carrying the trailer |
| 4 Per-commit gate | **Done** — every commit touching `*.py` was preceded by a clean `./pw quality-gate` (`ruff … All checks passed!`, `mypy … Success`, `SPDX-header check passed`) |
| 4 Pushed | **Done** — `git status -sb` reports no `ahead`; the branch was pushed after every commit, not once at PR time |
| 5 Build gate | **Done** — § Build gate carries the git-derived `*.py` verdict and one stamped row per commit that changed production Python, the last governing |
| 6 Verification sub-agent | **Done** — ten rounds, every finding and disposition recorded per round; exit `budget-exhausted, non-converging`; the budget (five, extended by the operator to ten) and the extension are recorded with what the operator was told; the verifier's own last answer is quoted; each survivor is listed individually in § Left open with its bound; whether the late rounds were narrower is answered explicitly (no) |
| 7 PR cycle | ⛔ **NOT DONE.** No PR exists. The operator has not asked for one, and the lane's PR step is theirs to trigger. § Reviewer participation records this as *not done* rather than *not applicable* — the step is owed, it has simply not been reached |
| 8 Merge gate | ⛔ **NOT DONE**, and cannot be: it presupposes a PR. Condition 2 (the stale-base re-verification) **was** discharged early, on its own terms — `main` moved under the branch, the branch was rebased onto `a34819d` at the operator's instruction, and the full `./pw verify` was re-run on the merged tree and has been re-run on every subsequent commit that touched Python |
| 8 Bridge | **Done** — no status or bookkeeping write landed under `doc/plans/` outside this plan's own directory. The one edit to another plan's directory (`020-corpus-residency-admission-control/report-01.md`) is a **declared deliverable** of D6, appended as a correction |
| 9 This check | **Done** — this table |
| 9 What have we learned | **Done** — below, with a proposal the operator must accept or decline |

## What have we learned (Step 9)

Two proposals, each named by what happened in **this** run rather than by what might generally be
better. Both are for the operator to accept or decline; neither is applied here.

### Proposal 1 — the verification loop must execute, not only read

**The evidence.** Rounds 1–6 swept statements against statements across six rounds and found **zero**
code defects. Rounds 7–10 executed the behaviour first and found **seven**, including: a rollback
that discarded the one file it needed to restore; a deliverable whose own title clause (*"survives a
bad frame"*) had been false since the commit that claimed it, through seven verification rounds; two
false cleans; a file-truncating clamp; and a percent sign in a `setup.cfg` value that erased every
module in the tree. Not one of these was reachable by reading, because in every case **the prose was
right and the code was wrong** — the sweep's implicit question, *"which statement is stale?"*, has no
correct answer when the answer is *"none of them"*.

**The proposed change** to `cloud-plan-lane` § Step 6's sub-agent instruction: alongside the existing
beyond-diff sweep, require the verifier to **start from each deliverable's behaviour, execute it, and
compare what it does to every statement about it** — and to treat "the statements agree with each
other" as no evidence at all. The instruction should name the shape that kept working here: *for each
claim family, ask which file **owns** the behaviour, run it, and read that file's docstrings.*

⚠ **The cost is real and should be stated with the benefit.** Executing rounds took roughly twice as
long per round as reading rounds. Rounds 7–10 cost about 25 minutes of verifier wall-clock each; they
also found every defect that mattered.

### Proposal 2 — a fix commit must re-derive the measurements in the sections it moves

**The evidence.** Round 9 found that round 7's fix had falsified four statements. Round 10 found that
round 9's fix had falsified four more — two docstrings and a comment it wrote itself, plus two
figures in the report commit that accompanied it. That is **two consecutive rounds in which the
previous round's own repair introduced the next round's findings**. The single most-repeated defect
in this entire report is narrower still: one survivor row's line citations drifted **four times**
(`:373`/`:391` → `:383`/`:403` → `:390`/`:410` → `:393`/`:413`), each time because a commit added
lines above them and nobody re-derived the row.

**The proposed change**: a commit that changes behaviour must, in the same commit, re-derive every
figure, count and citation in the sections whose lines it moved — **including rows recorded as open
survivors**, which are the ones a run is least likely to revisit because they are filed as settled. A
survivor row is a measurement with an expiry date.

⭐ **And the cheaper half, which this run adopted at round 10 and would recommend as the default:**
where a citation would be a line number, name the thing instead. `:390`/`:410` became *"the two
`restore_files(originals)` calls in `_run_edit`"*, which no commit can invalidate. Four recurrences
of one defect is enough evidence that re-deriving line numbers is the wrong remedy and not citing
them is the right one.

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
| …in this branch's six changed test directories | **0** |
| **Intersection with this branch's changed files** (**59** at `d893d51`) | **empty** |

The draft-time breakdown, which the landed form did not change:

| #1314 touches | Overlap with this branch |
|---|---|
| `test/plan-marshall/{plan-retrospective, manage-status, manage-metrics, manage-tasks, manage-lessons, manage-locks, manage-findings, manage-adr, manage-change-ledger, audit-archived-plan-retrospectives}` | **none** |
| `doc/plans/test-quality/**`, four top-level `test/plan-marshall/*.py` | **none** |
| `marketplace/**` | **0 files** |
| `doc/user/**` | **0 files** |
| The six test directories this branch changes | **0 files** |

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

⚠ **This list is PROVISIONAL while the loop runs.** The operator extended the budget past round 5, so
each survivor below is re-put to the verifier in each further round rather than settled here.

⛔ **These are condition-B entries. Most of the *numbered* ones are CLOSED rather than bounded** — B1
by round 7's fix (unnoticed at the time), B4 by a guard, B5 by a fix, and round 8's F4 by a real
change to the frame reader. They are kept here because the reasoning that closed each one is the
record of why a bound was refused.

⛔ **Twelve findings are genuinely open, and ALL of them are listed here.** An earlier revision said
"B2 and B3 are the only genuine survivors" while rounds 9 and 10 had left ten more open with bounds
elsewhere in this report — so the section a reader consults for *what remains* did not carry most of
what remained. That is round 10's A-4, and it is the last instance of this report's most persistent
defect: a claim that was true when written and was not re-derived when the thing it counts moved.
Nothing condition A governs is in this list: every false statement the rounds so far found is fixed.
Round 3's O2–O4 stand as recorded there; round 5 added B1–B3, round 6 added B4, round 7 added B5.

| # | Survivor | Bound, with its evidence |
|---|---|---|
| B1 | **CLOSED — and the row that said otherwise was false in every clause.** B1 recorded that the restore-failure branch was pinned by no test, that mutating `except OSError as restore_exc: restore_error = restore_exc` to `except OSError: pass` left the whole `lsp-client` directory green, and that no fixture in this tree could provoke a real restore failure without patching the filesystem layer. Round 7's own fix commit refuted all three as a side effect — `test_a_rollback_that_cannot_restore_the_damaged_file_says_so` patches `Path.write_text` and asserts `restore_error is not None` — and **nobody re-derived the survivor row**. Re-run at HEAD: the mutation now yields **1 failed, 60 passed**. ⛔ Round 6's F4 also recorded this row's "the one vacuity gap in the branch" sentence as *fixed*; `git show bb41ae2` shows it as unchanged context, so that disposition was false too | **No bound is owed — there is nothing left open.** The behaviour is correct, pinned, and red-checked. The record is kept because *how it closed* is the finding: a survivor row is a measurement with an expiry date, and this one expired unnoticed across two commits |
| B2 | **Two rollback call sites sit outside the exception boundary** — the two `restore_files(originals)` calls in `_run_edit` — the `diagnostics_unavailable` phase-`after` return and the `diagnostics_worsened` return. An `OSError` there escapes `_run_edit` to `safe_main`, so the verb returns a bare `status: error` with the edit still on disk and no `restore_error` | It **cannot produce a false clean**: the return is an error, never a success or a `rolled_back: true`. It requires a write failure *during* rollback. And G4's actual scope — the apply loop — **is** guarded, so the deliverable's clause is met; this is the adjacent case the clause does not name. ⚠ Round 6 sharpened it: when this was recorded the FIRST of the two sites was on a branch **no test executed at all** — an unconditional `raise` at its head left 58/58 green. That is no longer true; the guard added for B4 drives exactly that branch, so the site is now exercised even though its `OSError` path still is not. ⛔ **The line numbers this row used to carry drifted FOUR times** — `:373`/`:391` → `:383`/`:403` → `:390`/`:410` → `:393`/`:413` — each time because a commit added lines above them, and each time this row was not re-derived with it. They are now gone: the two call sites are named by **what they are**, which no commit can invalidate. That recurrence, and this remedy, are what § What have we learned proposes a contract change for |
| B4 | **`phase` and `unverified_path` were asserted by no test** — deleting both kwargs from both production returns left **58 passed / 0 failed**, while **four** documentation sites describe them, all four added by `b0d746c`. The commit that closed round 5 opened a gap of its own, in the one field a task leaf's reading of the payload turns on | **CLOSED by a test rather than bounded.** Two guards now pin both routes through `diagnostics_unavailable`: `phase: before` with `rolled_back: false` and **no** `restore_error`, and `phase: after` with `rolled_back: true` and the file restored. Red-checked — stripping the two kwargs fails both guards, and the real code passes them. Closing it cost less than the disclosure would have |
| B5 | **A mid-write failure left the damaged file modified while the payload reported a clean rollback** — `originals.pop(path, None)` discarded the failing file's pre-edit content in the one case where a write had already truncated it. Found by round 7, by *executing* the path rather than reading the eight statements about it | **CLOSED by a fix, not bounded.** The failing path stays in the restore set. Two guards pin both outcomes — a transient failure restores every file, a persistent one reports `restore_error` rather than claiming success — and both go red against the reinstated `pop`. ⛔ This was the run's only **false clean**, and condition B never applied to it: a defect that reports success over a damaged tree cannot be left open under any bound |
| B3 | **One search-path directory is missed.** `platform-runtime/scripts` carries an `__init__.py`, so the structural rule treats it as a package and omits it, yet **three** real bare imports target it (re-derived; an earlier revision said two and named two of the three) | **Provably cannot affect this deliverable's result**: all three importers are inside the `plan-marshall` bundle, so no cross-bundle reference and no module edge can change. Confirmed by measurement, not by argument — the **72** / **10** figures are identical with and without it. Recorded at § D3 alongside the sentence it falsified (A9) |

**Open survivors from rounds 9 and 10**, each with an executed reproduction rather than an argument:

| # | Survivor | Bound |
|---|---|---|
| S1 | **A CRLF file has every line ending rewritten to LF by any edit.** Measured: a 3-character edit turned `b'aaa\r\nbbb\r\nccc\r\n'` into `b'aaa\nBBB\nccc\n'`. Invisible to the diagnostics gate **and to `_still_modified`**, so a rollback reports `rolled_back: true` over a file whose bytes differ from the pre-edit bytes | Line endings only, never content — the one open finding that can produce a *clean-looking* difference, which is why it is named first. **Pre-existing on `origin/main`**; `read_text`/`write_text` translate newlines on both sides. Rare on a Linux Python repo, certain on a Windows-authored or mixed-EOL file. Fixing it means moving the whole write path to binary I/O with explicit newline handling, which is a larger change than this plan's D2 scope |
| S2 | **A malformed post-edit diagnostic raises after the write**: a non-dict entry, a non-dict `range`, or `range.start: null` escapes `_run_edit` **after** the edit is on disk, so it stays there with no rollback and a bare `status: error` | Same shape and cost as B2 below. Requires a spec-violating server — LSP makes `range` required and non-null. **Not a false clean**: the return is an error, never a success |
| S3 | A **truncated-mid-multi-byte-character** write whose restore *also* fails makes `_still_modified` raise, replacing `WorkspaceApplyError` and costing the caller `failed_path` and `restore_error` | **Closed at HEAD** by catching `UnicodeDecodeError` (round 10's A-5). Listed because the reproduction is the evidence for that catch |
| S4 | `[tool.poetry.dev-dependencies]` (the pre-1.2 spelling) and every non-`dev` Poetry group produce no edge, **undisclosed** — while the analogous npm gap was closed *by disclosure* in the same deliverable. `[options.extras_require]` in `setup.cfg` is the third instance | Dev-scope edges only; runtime edges are unaffected. Now disclosed for `setup.cfg` (A-7); the Poetry groups remain a documentation gap, not a wrong answer |
| S5 | Pre-existing discoverer crashes on **valid-but-wrongly-shaped** descriptors: a `package.json` whose top level is an array or string; `[project]` as a scalar; `dependencies = "core"` yielding one bogus edge per character; `workspaces: ["/etc/*"]`; `workspaces: ["../*"]` globbing outside the project root | All pre-existing on `origin/main`; all require a malformed descriptor. Distinct from round 10's B-1, which this plan **did** fix because that one triggers on *legal* input and is this branch's own code |
| S6 | Rollback is **last-writer-wins**: an external edit landing between capture and restore is silently discarded, and `_still_modified` reports clean | Inherent to any rollback that captures content up front. Window = the diagnostics wait |
| S7 | A frame truncated **inside** its header block ends the session silently (no `malformed frame` line), where the same truncation one byte later is audible | EOF was genuinely reached, so the session must end either way; only the operator-facing distinction is lost. `read_message`'s own comment documents the case |
| S8 | `normalize_changes` silently drops a malformed `documentChanges` entry, and the whole-refusal gate fires only on non-empty `notes[]`, so the remainder is applied and reported `success` | Requires a malformed server edit; the honesty note covers only `create`/`rename`/`delete` |
| S9 | A `null` `textDocument.uri` raises out of `capture_footprint`, before `_run_edit`'s `try` | Identical in shape and cost to B2 — an error, never a success and never a `rolled_back: true` |
| S10 | A `request-failed:` discards every note the harvest accumulated | `ran=False`, so no caller reads the outcome as a result |
| S11 | An **unparseable or BOM-prefixed** file is a silent scanned-but-empty file, while an unreadable one gets a note | Affects recall only, never attribution. Documented in `import_positions`; the `unresolved-symbol` count already discloses the shortfall |
| S12 | A **dangling symlink** reports the resolved target in `failed_path` rather than the path the server named | Cosmetic; the failure is still reported and still fails closed |

Round 3's observations O1 and O5 are **not** in this list: O1 was overtaken by round 5's A8 (the site
count was wrong) and remains a handoff to `560-documentation-surface-truthfulness` rather than a
survivor of this plan; O5 was overtaken by the rebase and is recorded as such at its own row.

⚠ **Three checks the verifier could not re-derive, disclosed rather than silently carried.** § Build
gate's CI-portability row 1 (`662 passed, 10 skipped`) does not name its population, and none of the
four populations round 5 tried reproduced it — *unverifiable*, not proven false; row 2 and § Red-then-
green's pre-change counts need a detached worktree with hand-adapted pre-change test copies, which
round 5 did not reconstruct; and six of the ten mutants in § Mutation sweep were not independently
re-run (four were). The cold reads of rounds 1 and 3 are unrepeatable by construction — a verifier
that has read the plan is no longer a plan-blind reader.
