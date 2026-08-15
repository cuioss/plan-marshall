# Run report — 200-lsp-derivation-resolver (run 01)

**Date (UTC):** 2026-08-15    **Branch:** `claude/lsp-derivation-resolver-rtaki2`    **PR:** [#1243](https://github.com/cuioss/plan-marshall/pull/1243)    **Outcome:** completed

## Skills loaded

| Skill | Route |
|---|---|
| `cloud-plan-lane` | `.claude/skills/cloud-plan-lane/SKILL.md` — loaded as the first action |
| `pm-plugin-development:plugin-script-architecture` | Bundle path (always-load) |
| `plan-marshall:extension-api` § `ext-point-derivation-resolver` | Bundle path — the contract implemented |

`plan-marshall:ref-code-quality` was **not** loaded as a separate read: its
substance reached this run through `plugin-script-architecture` and the
repository's own quality gate (ruff / mypy / plugin-doctor), which enforce the
same standards mechanically. Recorded here rather than claimed as loaded.

Skills deliberately not loaded, because the run's surface did not reach them:
`persona-security-expert` (no security-relevant surface), `pm-documents:ref-asciidoc`
(one `.adoc` edit, following the file's established conventions).

## Deliverables

| # | Deliverable | Outcome | Commit |
|---|---|---|---|
| D0 | GATE — headless batch harvest | **Confirmed by execution** | (pre-implementation probe) |
| D1 | LSP-backed derivation resolver | Done | `ebfae80` |
| D2 | File-to-module lift | Done | `ebfae80` |
| D3 | Lifecycle + honest failure modes | Done | `ebfae80`, fixed in `96cda52` |
| D4 | Configuration | Done | `ebfae80` |
| D5 | Documentation | Done | `cd69b9a` |

### D0 — the gate, settled against a running server

`pyright-langserver` 1.1.408 is present in this environment. A minimal stdio LSP
client was driven end-to-end **before any implementation was scoped**, as the
plan requires:

| Workspace | Files | Requests | Harvest | ms/req | Intra-repo refs |
|---|---|---|---|---|---|
| `manage-architecture/scripts` | 10 | 402 | 2.29 s | 5.7 | 22 |
| repository root | 200 | 3 864 | 14.12 s | 3.7 | 229 |

Server boot: 0.34–0.46 s. Extrapolated to the repository's 1 248 tracked `*.py`
files: **≈ 90 s**, paid once per crawl. **The premise is confirmed, not refuted**,
so D1–D4 proceeded.

One finding from the gate is load-bearing and is now pinned by a test: anchoring
the definition request on an `ImportFrom` statement's own `col_offset` puts it on
the `from` keyword, which the server resolves to nothing. The first probe
returned **0** intra-repo references for exactly that reason. Using `ast.alias`
positions (exact on Python 3.10+) took the same workspace from 0 to 22. A silent
zero here is indistinguishable from a workspace with no references — which is the
failure this plan exists to eliminate, reproduced accidentally in its own gate.

### D1 — the resolver, and the lifecycle the seam forced

The plan's framing ("runs once at derivation time … reads stay cheap and
persistent") is satisfiable on the shipped seam, but **not** by booting a server
inside the resolver. Two facts from the clone decide it:

- `derive_edges` is contractually **pure** — no subprocess, no filesystem access.
- Resolvers are dispatched at graph-**query** time (`_cmd_client_query.py:909`),
  once per `graph` / `path` / `neighbors` / `impact` call.

A server booted in `derive_edges` would therefore pay its whole index cost on
every one of those calls. The in-seam route already exists and is documented at
the site that uses it: `build_component_refs` states that its engine "reads files
from disk, so it has to run here — at discovery time — and never inside a
derivation resolver". So the harvest is a discovery-time engine
(`pm-plugin-development:…:lsp_harvest`) whose references persist into
`derived.json`, and the resolver is a pure join over them — the same shape the
shipped `python` import join uses.

**No extension point was added, and the seam was not widened.** The plan's
stop-and-record condition was therefore not triggered.

**The transport is reused, not reimplemented — after a first cut that got this
wrong.** This repository already ships `plan-marshall:lsp-client`: a JSON-RPC
`StdioTransport`, an `LspSession` exposing `definition` / `references` / `rename`,
and `resolve_language_server()` over the shared binding. The first cut
hand-rolled all of it, putting a second, silently divergent LSP client in one
repository. The harvest now drives the shipped session. The engine's only
remaining LSP-specific code is the part genuinely absent upstream: which source
positions to ask about (`import_positions`).

**Why a new bundle.** A bundle registers at most one resolver, and `pm-dev-python`
already owns `python`. Hosting the LSP join there would stamp its edges `python`
and make parser-resolved edges indistinguishable from AST-import edges —
forfeiting exactly the provenance the goal requires ("stamped with their
producer"). The seam's own standard states the consequence: two derivations that
must stay distinguishable have to live in two bundles. Hence
`pm-code-intelligence`, resolver id `lsp`, an 11th production bundle.

### D2 — the lift

`lift_to_modules()` maps file-granular references to module pairs. An endpoint the
attribution seam cannot attribute yields **a note and no edge**; so does an
attributed name outside the discovered module set, and so does a self-edge.

Verified by the **drop** case, per the plan: `test_unattributable_endpoint_produces_note_and_no_edge`
and its source-endpoint twin fail against any implementation that guesses an
owner. The happy-path test alone would not.

### D3 — honest failure

Four lifecycle failure modes, each with its own negative control and a distinct
stated reason: `server-absent`, `server-failed-to-start`, `server-timeout`,
`workspace-unsupported`. Two further tests assert the properties directly —
`test_every_failure_mode_states_a_distinct_reason` (four modes ⇒ four distinct
reasons) and `test_no_failure_mode_reports_a_zero_edge_success`.

The status record rides every module as `lsp_harvest`, so the resolver reports
`harvest-did-not-run: {reason}`. Without it a dead server and an edge-free
workspace would both reach the caller as `status: ok, edge_count: 0`.

### D4 — configuration

**The first cut violated this deliverable's ⛔ and was corrected.** It shipped
three `pm_code_intelligence.lsp.*` keys in `.plan/marshal.json` — a *second* place
to name the same pyright binary for the same language, alongside the
machine-local `language_servers` binding that already existed. That binding's own
standard says plainly it "is the shared configuration surface the
resolver-configuration work extends — not a parallel store". The keys and this
bundle's `config_defaults` are gone.

**The shared binding is now the only switch.** A language harvests exactly when it
has an enabled `language_servers` entry, read through `lsp-client`'s own
`resolve_language_server()`. Off-by-default comes for free: the store is
machine-local and git-ignored, so a fresh clone has no binding and boots no
server — which also preserves Tier 0's subprocess-free property by default.

The resolver-configuration plan the deliverable names has **not** landed as a new
surface; the existing `language_servers` section is the shared surface it would
extend, so the minimum was defined there rather than by inventing one.

### D5 — documentation

**The first cut asserted the opposite of the truth and was corrected.** It stated
that live symbol pass-through was "deliberately absent rather than merely
unimplemented" and that "nothing at this tier is queryable". Both are false:
`plan-marshall:lsp-client` ships `lookup --kind
references|definition|document-symbol|workspace-symbol` plus verified rename, and
is user-documented at `doc/user/lsp-code-intelligence.adoc`. D5's ⚠ asks for
precision about what is and is not built; the first cut failed it outright, on
the one deliverable whose entire purpose is that precision.

What the corrected pages say: Tier 2 is `PARTLY BUILT` — symbol references are
reachable **live** (lsp-client) *and* harvested **in batch** (this resolver), no
persisted symbol store exists, and call graphs and type relations are not built.
Tier 0's `SUBPROCESS-FREE` becomes `BY DEFAULT`, because an enabled harvest trades
that property away.

The lifecycle section no longer argues that pass-through is unbuilt; it explains
why the batch harvest and the live client stay **separate lifecycles** while
sharing transport and configuration by reuse.

## Build gate

`git diff --name-only origin/main...HEAD -- '*.py'` → **non-empty** (8 files), so
the full `./pw verify` was required and run.

Final run — all three sub-steps clean, read from the output rather than the exit code:

- **quality-gate**: `mypy` Success (400 source files), `ruff` All checks passed, `SPDX-header check passed`, plugin-doctor `issues[0]`
- **test-compile**: `mypy` Success (736 source files)
- **module-tests**: **19 708 passed, 14 skipped, 0 failed**

## Findings

Recorded per instance.

| # | Source | Finding | Disposition |
|---|---|---|---|
| 1 | Own testing (D0 probe) | Definition requests anchored on `ImportFrom.col_offset` land on the `from` keyword and resolve to nothing — a silent zero reading exactly like an empty workspace | **Fixed** — `ast.alias` positions; pinned by `test_import_positions_anchor_on_the_imported_name` |
| 2 | `./pw verify` (test-compile) | `test/pm-code-intelligence/__init__.py` made a hyphenated directory look like a Python package; `mypy` rejected it | **Fixed** — removed, matching the sibling convention (no bundle-level `__init__.py`) |
| 3 | `./pw verify` (module-tests) | **Real engine bug**: the candidate-file skip list matched against each file's *absolute* path, so a component of the workspace root's own location vetoed every file. A project under a directory named `target` / `venv` / `node_modules` would harvest nothing and report `workspace-unsupported` — a stated-but-**wrong** reason | **Fixed** — matching is now relative to the workspace root; two regression tests pin both halves |
| 4 | `./pw verify` (module-tests) | Resolver roster and bundle-count expectations in three test files did not include the new bundle/resolver | **Fixed** — rosters updated; one count assertion re-expressed as `len(_PRODUCTION_BUNDLES)` so it cannot drift again |
| 5 | Own review | `CLAUDE.md` component counts were already stale before this change (145 skills recorded, 152 actual) | **Fixed** — corrected to the verified 11 / 157 / 153 / 2 / 2 |
| 6 | Own review | A dead server can surface as `BrokenPipeError` on write or `JSONDecodeError` on read, neither of which was caught — an unhandled exception would have failed the whole crawl rather than degrading to a stated no-harvest | **Fixed** — both folded into the server-gone path; pinned by `test_garbage_emitting_server_does_not_escape_as_an_exception` |
| 7 | Verification sub-agent (blocking) | **D5 stated the opposite of the truth**: the concepts page claimed live symbol pass-through was "deliberately absent" and that "nothing at this tier is queryable", while `plan-marshall:lsp-client` ships exactly that lookup surface and a verified rename | **Fixed** — tier ladder, concepts page, bundle README and SKILL.md rewritten to state what is actually built |
| 8 | Verification sub-agent (blocking) | **D4's ⛔ violated**: `pm_code_intelligence.lsp.*` in `.plan/marshal.json` was a second surface naming the same server for the same language, duplicating the machine-local `language_servers` binding whose own standard calls itself the surface this work should extend | **Fixed** — keys and `config_defaults` removed; the shared binding is the only switch |
| 9 | Verification sub-agent (blocking) | **The resolver produced a silent zero outside this repository.** `lsp_harvest` is materialized only by `pm-plugin-development`'s discovery, so in any consumer project no module carries the record and `derive_edges` returned `([], [])` — a confident zero meaning "no harvest happened here" | **Fixed** — a missing record now yields a stated `harvest-did-not-run` note; a test asserts it, replacing one that had asserted the defective behaviour as correct |
| 10 | Verification sub-agent (blocking) | An entire LSP transport was reimplemented alongside the shipped `lsp-client` | **Fixed** — the harvest drives the shipped `StdioTransport` / `LspSession` |
| 11 | Verification sub-agent (blocking) | Bundle-count restatements stale in 8 tracked files — `README.md`, `AGENTS.md`, `doc/concepts/README.adoc`, `doc/concepts/extension-architecture.adoc`, `doc/developer/repository-layout.adoc` (×2), `extension-contract.md`, `ext-point-domain-bundle.md`, plus the topology SVG — **including the enumerating tables**, not only the counts | **Fixed** — counts and tables updated |
| 12 | Verification sub-agent (blocking) | `module-discovery.md` enumerates `dep_type` as exactly five kinds; `lsp` is a sixth | **Fixed** |
| 13 | Verification sub-agent (should-fix) | `AXIS_A_RESOLVER_IDS` in `test_graph_family_bundle_project.py` omitted `lsp`; used as a filter, so the omission was invisible to CI — the "test fixture that still passes" kind | **Fixed**, with the file's docstring ("three Axis-A ones") |
| 14 | Verification sub-agent (should-fix) | `pm-plugin-development`'s SKILL.md documented `discover_modules()` without mentioning that it now boots a language server | **Fixed** |
| 15 | Verification sub-agent (should-fix) | URI paths were not percent-decoded, so a workspace path containing a space would miscount every reference as out-of-workspace — a stated-but-wrong reason, the same class as finding 3 | **Fixed** — `unquote` + `urlparse` |
| 16 | Verification sub-agent (should-fix) | D3's fourth mode fires before the server launches (no sources found), so it tests "workspace has no sources", not "server rejects this workspace" | **Accepted, scope narrowed rather than renamed** — the reason string now reads `workspace-unsupported: no {language} sources found under the project root`, which states exactly what was detected. A true server-side rejection is not reachable without a server that emits one; recorded in Residue |

### Second verification pass (after the fixes)

The sub-agent was re-dispatched, as the contract requires. It confirmed findings
7–9 and 11–15 resolved by reading the source and executing the tests, and found
that the reuse refactor had introduced regressions of its own:

| # | Source | Finding | Disposition |
|---|---|---|---|
| 17 | Sub-agent round 2 (blocking) | Three prose sites still described the retired `.plan/marshal.json` keys — including this bundle's own **prohibition list**, which named the very surface D4's ⛔ forbids | **Fixed** — all three rewritten to the shared binding |
| 18 | Sub-agent round 2 | **Regression from the refactor**: a dead server stalled 60 s instead of failing fast (the shared transport returns on EOF without waking its waiters), and the reason then interpolated the *whole-harvest* budget (`300s`) rather than the handshake budget actually waited on | **Fixed** — the handshake budget is bound once and reported; the factor is now an explicit, documented constant, halving the stall |
| 19 | Sub-agent round 2 | `request_timeout_s` was documented as a per-request budget but bounds only `initialize` after the refactor — the shared session exposes no per-call timeout | **Fixed as documentation**, not as behaviour: the docstrings now state what is actually enforced. Claiming a bound that does not exist is the defect; silently adding one to another bundle's session is not this plan's call |
| 20 | Sub-agent round 2 | **A vacuous test.** `test_end_to_end_materialization_...` used a `sys.path.insert` trick pyright does not follow, so `refs` was empty and its assertion loop ran **zero** iterations — green while proving nothing, and it was the only real-server test of the materialization shape | **Fixed** — a package layout pyright resolves, plus non-empty assertions and an exact-shape check so it cannot pass empty again |
| 21 | Sub-agent round 2 | An unimportable `lsp-client` was reported as "not configured", telling an operator to configure a server when the client module was missing — and it made the real reason unreachable | **Fixed** — the two causes are now distinguished |
| 22 | Sub-agent round 2 | Enabling `language_servers` for a language now also switches on a per-crawl whole-workspace harvest, and no page a user reads said so | **Fixed** — the run-config standard gains a two-consumers table naming the cost asymmetry |
| 23 | Sub-agent round 2 | The URI percent-decoding fix (finding 15) had **no test** | **Fixed** — two tests pin decoding and non-`file:` rejection |
| 24 | Sub-agent round 2 | Truncation inside the *last* file exited the loop normally, returning a partial harvest with no partiality note | **Fixed** — truncation is tracked and reported wherever it occurs |
| 25 | Sub-agent round 2 | Duplicate, mutually contradictory `## Configuration` sections in the bundle SKILL.md | **Fixed** |
| 26 | Sub-agent round 2 | Topology diagram's derivation-resolver card read `1 impl · build-maven`; there are five | **Fixed** (pre-existing staleness, adjacent to this diff) |
| 27 | Sub-agent round 2 | `doc/concepts/README.adoc` still called Tier 0 "subprocess-free" unqualified after the page it summarises had been qualified | **Fixed** |
| 28 | Sub-agent round 2 (nit) | `_path_from_uri` re-implements `_lsp_workspace_edit.uri_to_path()` | **Rejected** — that helper is a private module of another bundle. Importing a `_`-prefixed module across a bundle boundary is worse coupling than six lines of stdlib, and the public `lsp_client` surface does not re-export it |
| 29 | Sub-agent round 2 (nit) | `domain-residency-audit.md` says "all 10 bundles" | **Deferred** — an audit recipe's own historical record, not a claim about the current tree |

Finding 20 deserves emphasis: a test asserting over an empty collection passes
unconditionally. It survived the first review, the build gate, and CI, and was
caught only because the second pass **executed** the arrangement and printed what
it produced rather than reading the assertions. The lane's warning about fixtures
that "still pass" applies to vacuous loops as much as to stale constants.

Finding 3 is worth its own note: it was invisible to the isolated test run and
surfaced only under the full suite, because pytest's `tmp_path` lives under this
project's `target/`. The check that caught it was
`test_every_failure_mode_states_a_distinct_reason` — it saw two distinct reasons
where it required four. A weaker assertion ("each mode fails") would have passed
while all three subprocess modes silently collapsed onto one wrong reason.

### Correctness spot-check

The plan calls for sampling derived edges and verifying them by hand, and for
reporting the sample size and how it was chosen.

**Population:** all **6** references the shipped engine derived over the
`build-maven/scripts` workspace (6 files, 1.42 s). This is the *whole* population
for that workspace, not a sample of it — chosen because it is small enough to
verify exhaustively and its imports are unambiguous.

**Result: 6/6 correct**, verified against the source import statements. Notably
`_maven_cmd_discover.py -> _maven_execute.py` comes from a **function-local
deferred import** at line 555 — a reference a top-of-file scan would miss, which
is the kind of edge this tier exists to add.

⚠ **This is one bundle's script directory, not the repository.** It is a small
and favourable subset: flat, single-directory, unambiguous imports. It supports
"the derived edges are correct here"; it does **not** establish a repository-wide
precision figure, and no such figure is claimed. The plan's own warning applies —
a confidently-labelled wrong edge is worse than no edge, and this run has not
measured precision at scale.

## Reviewer participation

_pending — filled after the PR review cycle._

## Cost

- **Tokens:** not available to the agent in this session.
- **Wall-clock:** not separately instrumented. The dominant measurable components
  were four full `./pw verify` runs at ≈ 5–6 min each and the D0 probes at
  ≈ 20 s total.
- **Population:** whatever these figures cover is a single interactive Claude Code
  cloud session. ⛔ **Not comparable to a plan-marshall `metrics.toon` total**,
  which counts an orchestrator-plus-agent dispatch tree under plan-marshall's own
  per-task billing boundary. No parity is implied and none should be inferred.

## Contract check (Step 9)

| Step | Verdict | Artifact |
|---|---|---|
| 1 Skills loaded | **Done, with a caveat** | Named above. `ref-code-quality` was not separately read — recorded rather than claimed |
| 2 Branch | **Done** | Harness-assigned `claude/lsp-derivation-resolver-rtaki2` kept as-is and pushed to `origin` **before any edit**, as the invariant requires. The run created no branch, so the closed prefix set did not apply |
| 3 Plan directory | **Done, out of order** | `doc/plans/code-intelligence-substrate/200-lsp-derivation-resolver/plan.md` exists, numeric prefix preserved, first-instruction block present and verified. ⚠ **Performed after implementation had begun, not before** — the contract puts it at Step 3. No harm resulted (the branch was correct throughout and the move was a pure `git mv`), but it is reported as out-of-order rather than narrated as compliant |
| 4 Implement | **Done** | Seven commits, each carrying the trailer, no "Generated with Claude Code" footer |
| 4 Per-commit gate | **Done** | Every commit touching `*.py` was preceded by a clean `./pw quality-gate` — ruff "All checks passed!", mypy "Success: no issues found", "SPDX-header check passed", plugin-doctor `issues[0]` |
| 4 Pushed | **Done** | Pushed after every commit; `git status -sb` reports no `ahead` |
| 5 Build gate | **Done** | Python-change verdict non-empty (8 files) ⇒ full `./pw verify`, run to green over all three sub-steps |
| 6 Verification sub-agent | **Done, twice** | First pass found 5 blocking defects; fixed and **re-dispatched** per the contract; second pass confirmed them resolved and found 8 regressions, all dispositioned above |
| 7 PR cycle | **Done** | PR #1243. `skip-bot-review` deliberately **not** applied — the diff touches `*.py` and `marketplace/bundles/**`, and a skill is code |
| 8 Merge gate | See § Reviewer participation | Conditions 1–3 checked before arming |
| 8 Bridge | **Clean** | No status or bookkeeping write landed under `doc/plans/` outside this plan's own directory. `.plan/` was not written at all |
| 9 This check | **Done** | This table |
| 9 What have we learned | **Done** | A contract change is proposed below and presented to the operator, not self-approved |

**GitHub access path:** the GitHub MCP server (no `gh` CLI in this session).
**Branch form:** harness-assigned.
**Plugin cache sync:** not owed — a cloud run neither performs nor records one.

## What have we learned (Step 9)

**Proposed change: the lane needs a prior-art check before implementation, and it
has none.**

*Evidence from this run.* This repository already ships `plan-marshall:lsp-client`
— a JSON-RPC transport, an `LspSession` with `definition` / `references` /
`rename`, and `resolve_language_server()` over a shared machine-local binding. It
landed under a sibling plan in the same epic. This run nevertheless:

1. hand-rolled a second LSP transport;
2. added a second configuration surface naming the same binary for the same
   language, violating an explicit ⛔ in the plan; and
3. wrote documentation asserting that the capability `lsp-client` provides was
   "deliberately absent rather than merely unimplemented" — which would have
   shipped as repository doctrine, in the very deliverable whose ⚠ is *state
   precisely what is and is not built*.

All three trace to one omission: **nothing in the contract asks a run to check
whether the capability already exists before building it.** Step 1 loads skills by
*surface*; Step 5 gates the build; Step 6 sweeps beyond the diff for stale
*claims* about values the change touched. None of them prompts "does this already
exist here?" Step 6 did eventually catch it — but only after the wrong thing was
built, documented, committed, and pushed four times.

The cost of catching it earlier is one search. The cost of not catching it was a
full refactor plus a documentation correction.

*Proposed edit.* Add to § Step 1, after the skill-loading table:

> **Before implementing a capability, check whether this repository already
> provides it.** Search the tree for the capability by name and by mechanism (for
> a protocol or format, its wire/tool name; for a config surface, the setting it
> would carry). Record what you found in the report — including "nothing", which
> is a different fact from not having looked. A plan that names a capability as
> absent is asserting a claim, and an asserted **absence** is verified exactly as
> an asserted presence.

The last sentence deliberately reuses the wording the plan template already
applies to claim labels, because this run's plan *did* carry that instruction —
"An asserted **absence** … is verified exactly as an asserted presence" — and it
was applied to the resolver roster but never to the capability itself. Lifting it
into the contract makes it bind on every run rather than on a plan that remembers
to say it.

**Status: presented to the operator, not self-approved.** Per § Step 9 this ships
as its own `chore/` PR touching only the skill, never folded into this plan's PR.

## Residue

- **D3's fourth mode is narrower than the plan names it.** The plan says "does not
  support the workspace" — a server-side verdict. What is implemented and tested is
  "the workspace has no sources for this language", detected before launch. The
  reason string states exactly that, so nothing is misreported, but a genuine
  server-side rejection has no negative control.
- **The `lsp` and live-lookup paths share a binding but not a health check.** If a
  configured server is broken, the harvest reports it per crawl and `lsp-client`
  reports it per call, independently. Neither tells the other.
- **`.plan/project-architecture/` is TRACKED, and this run left it stale — on
  purpose.** `_project.json`'s description still says "ten production bundles", and
  there is no `pm-code-intelligence/enriched.json` while every sibling bundle has
  one. This run did **not** edit it, because the lane contract states the lane
  "never touches `.plan/`" — a boundary it seemed wrong to cross unilaterally.
  ⚠ **That contract statement rests on a false premise**: it reasons from `.plan/`
  being git-ignored, and this subtree is not. Either the contract should carve out
  the tracked portion, or this overlay should be regenerated on a machine that can
  run the crawl. Flagged rather than silently fixed or silently skipped.
- **Sibling resolvers are not asserted against the new `lsp` dep type.** Their
  "everything else is ignored" tests derive their populations from the
  marketplace-inventory `DependencyType` enum, which has no `lsp` member. The
  behaviour is correct (each resolver's kind set excludes it) but unasserted.

- **Repository-wide precision is unmeasured.** The spot-check covers one small
  workspace. A larger hand-verified sample, or a cross-check of `lsp` edges
  against `python` edges (where the union should show heavy corroboration), would
  turn "correct here" into a real precision estimate.
- **Enabling a language now enables two things at once.** The `language_servers`
  binding switches on both `lsp-client`'s per-lookup path and this harvest's
  per-crawl one, and there is no separate switch for the harvest alone. That is a
  deliberate one-binding-per-language choice, and it is now disclosed in the
  run-config standard — but a project wanting leaf lookup without the per-crawl
  cost has no option today beyond leaving the language unconfigured.
- **One language only.** Python via pyright, as scoped. The engine takes
  `server_cmd` / `language` / `suffix` parameters, so a second language is
  configuration plus a position-enumeration strategy — `import_positions` is
  Python-specific and would need a per-language counterpart.
- **The harvest is off by default and therefore unexercised in CI.** The
  end-to-end tests run against a real server when one is installed, but the
  integration path through discovery runs disabled. Enabling it in CI would cost
  ≈ 90 s per crawl.
