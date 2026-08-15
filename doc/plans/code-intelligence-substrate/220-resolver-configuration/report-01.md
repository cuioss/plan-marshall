# Run report — 220-resolver-configuration (run 01)

**Date (UTC):** 2026-08-15    **Branch:** `claude/resolver-configuration-s8jcg5`    **PR:** TBD    **Outcome:** TBD

## Skills loaded

Loaded by path from the bundle source (`marketplace/bundles/{bundle}/skills/{skill}/SKILL.md`) — the
`plan-marshall` plugin is not installed in this cloud session, so the `Skill:` notation route was not
used.

| Skill | Why |
|---|---|
| `plan-marshall:ref-code-quality` | Always |
| `pm-plugin-development:plugin-script-architecture` | Always |
| `plan-marshall:persona-implementer` | Production code |

No skill was unobtainable.

## Claim verification (plan § Claim labels)

Every claim the plan staged was re-derived in this clone before it was relied on.

| Claim | Plan label | Verdict | Artifact |
|---|---|---|---|
| The machine-local run-config store is the right home, and it is git-ignored | OBSERVED | **Confirmed** | `git check-ignore -v .plan/run-configuration.json` → `.gitignore:46:.plan/*`. The store is absent in the clone, as expected; that absence was not read as an argument against it. |
| A negation exists for a run-config path under `.claude/`, and that file does not exist and is not tracked | OBSERVED | **Confirmed** | `git ls-files .claude/run-configuration.json` → empty; `ls` → no such file; `git check-ignore -v` → `.gitignore:29:!.claude/run-configuration.json`. The rule existed; the file never did. |
| The neighbouring negations are live, with dozens of tracked files depending on them | OBSERVED by enumeration | **Confirmed by enumeration** | `git ls-files .claude/skills/` → **45**; `.claude/commands/` → **1**; plus `.claude/settings.json` → **47** tracked paths total. Not sampled. |
| The run-config skill already persists keyed sections, main-anchored regardless of caller dir | OBSERVED | **Confirmed** | `language_servers` is exactly that pattern (`run_config.py:710-802`); `get_run_config_path()` resolves via `resolve_main_anchored_path` (ADR-002). The new section follows it verbatim. |
| The wizard has a menu structure a new entry can be added to without restructuring | **HYPOTHESIS** | **Confirmed** | `references/menu-configuration.md` is a 4-page paginated `AskUserQuestion` menu. Page 4 carried 2 options + Back — one free slot, filled without restructuring. The dispatch was read before D1 was scoped, as the plan required. |
| File pattern is the right binding key, rather than language, module, or build system | **HYPOTHESIS** | ⛔ **REFUTED** — see below | All seven shipped resolvers read. |
| Removing the dead negation changes nothing about what git tracks | **HYPOTHESIS** | **Confirmed** | Before/after diff of git's own view — see D4. |

### The file-pattern hypothesis is refuted, and the binding is keyed on the resolver id

The plan flagged this as a hypothesis to confirm or refute at outline, against the existing
resolvers. All seven were read (`maven`, `npm`, `pyproject`, `markdown`, `python`, `lsp`,
`documentation`). The evidence refutes it:

1. **There is no file-granular dispatch point.** `derive_edges(derived_by_name, enriched_by_name)`
   takes module maps and returns `(module, module)` pairs. Core never sees a file, so a per-file
   binding has nowhere to apply.
2. **Edges carry no file provenance**, so a pattern could not be matched against a produced edge
   either — the binding is unenforceable in both directions, not merely unimplemented.
3. **No shipped resolver scopes itself by file pattern.** They scope by build system (`maven`, `npm`,
   `pyproject` filter `derived_by_name` on `build_systems`), by module kind (`documentation`), by
   `component_refs` dep type (`markdown`, `python`), and by language (`lsp`, via the existing
   `language_servers` binding).

The plan's cited data point — "two of them split by file extension inside one module" — is real
(`markdown` handles `.md` references and `python` handles `.py` imports over the same module set) but
they split by **dep type in a pre-materialized field**, which is resolver-internal, not an
operator-supplied pattern. As the plan itself noted, it was a single data point.

**Resolution.** The binding is keyed on the resolver **id** — the only key core can act on. The plan's
own D2 wording admits this direction ("mapping file pattern (**or language**) to resolver"), and the
goal's "for which files" is served without pattern-keying: each resolver now declares its file domain
via a new `derivation_file_patterns()` ABC method, which the menu renders. That declaration is
**descriptive only**, and is documented as such at every site, so a future reader cannot mistake it
for a filter.

Language-keying already exists for the one resolver it fits (`lsp` → `language_servers`) and was left
alone rather than duplicated.

## Deliverables

| # | Deliverable | State | Where |
|---|---|---|---|
| D1 | Resolver-configuration menu | **Done** | `marshall-steward/references/menu-derivation-resolvers.md` (new), wired into `menu-configuration.md` Page 4 + routing + TOC + `SKILL.md` reference table. Its data comes from a new `extension_api.py::list_derivation_resolvers` verb (`derivation-resolvers list`). |
| D2 | Resolver section in the run-config schema | **Done** | `run_config.py` — `derivation_resolvers` keyed section, `get`/`set`/`list`/`remove` verbs, `read_derivation_resolvers_section()` + `is_derivation_resolver_enabled()`. Follows the `language_servers` pattern in the same store; no new store. The gate that makes it take effect is `_cmd_client_query.py::_partition_configured_resolvers` + `count_dispatched`; the file-domain declaration is `extension_base.py::DerivationResolverBase.derivation_file_patterns`, implemented by all seven shipped resolvers (`build-maven`, `build-npm`, `build-pyproject`, `pm-plugin-development`, `pm-dev-python`, `pm-code-intelligence`, `pm-documents`). |
| D3 | Precedence + working default | **Done** | Default: unconfigured ⇒ every discovered resolver active, asserted by test on an unconfigured project. Precedence: documented as **not expressible** (union semantics) rather than shipped as a dead knob — see below. |
| D4 | Retire the dead ignore-file negation | **Done** | `.gitignore` — the negation and the stale comment wording only. Verified by before/after diff of git's own view. |
| D5 | Documentation | **Done** | `run-config-standard.md` (new section, machine-local stated explicitly), `manage-run-config/SKILL.md`, `ext-point-derivation-resolver.md`, `extension-contract.md`, `extension-api/SKILL.md`, four bundle `SKILL.md` hook tables, `doc/user/configuration.adoc`. |

### D3 — why no `precedence` knob was shipped

The plan asked for "precedence when several resolvers claim the same file". Among resolvers,
precedence is **structurally inexpressible**, and the seam's own contract says so: the graph is the
**union** of every active resolver's edges, edges are unweighted `(from, to)` booleans, so union is
idempotent and commutative. Two resolvers deriving the same pair have *corroborated*, not disagreed —
the merge collapses them into one edge carrying both producer ids, which is the only thing that keeps
each contribution visible.

Shipping a `precedence` field that reordered dispatch would have changed nothing observable, i.e. dead
config — which this repository's own config-governance principles police. So the deliverable was met by
**documenting the precedence that actually exists**: `declared`-over-`derived` (a module with non-empty
declared `internal_dependencies` has its derived edges discarded and stamped `declared`), which core
owns and configuration cannot override. Recorded in the run-config standard, the seam contract, the
menu, and the user docs.

D3's stated *Done when* — "an unconfigured project still derives edges, asserted by test" — is met by
`test_derivation_resolver_configuration.py::test_unconfigured_project_still_derives_edges`, which
drives the real `get_module_graph` path with an empty store.

### D4 — the surgical boundary, verified

The plan made the before/after check mandatory. A snapshot script captured `git ls-files`,
`git status --porcelain`, and `git check-ignore -v` over all 47 tracked `.claude` paths plus nine
untracked probes exercising each neighbouring negation, run before and after the edit.

| Check | Result |
|---|---|
| Tracked file set (`git ls-files`) | **Byte-identical** |
| Ignore verdicts, line numbers normalized | **One line differs** — `.claude/run-configuration.json`, the retired path itself, now matched by `.claude/*` instead of the negation |
| Neighbouring negations (`!.claude/skills/`, `!.claude/commands/`, `!.claude/settings.json`, `.claude/settings.local.json`, `.claude/lessons-learned/`, `.plan/marshal.json`) | **Unchanged** |

The raw diff also showed the `M .gitignore` status line and two line-number shifts (`37→36`, `46→45`)
from deleting one line — same rules, same matches. The surgical boundary held: no live negation was
touched.

## Build gate

`git diff --name-only origin/main...HEAD -- '*.py'` — **Python changes present** (13 production
scripts + 5 test files), so the full gate applies.

`./pw verify` was run over the whole branch diff, direct (no generated executor in this lane).
Round 1 (pre-fix tree): **20091 passed, 14 skipped**, every dimension clean — `ruff … All checks
passed!`, `mypy(production)` 405 files clean, `mypy(test)` 753 files clean, `SPDX-header check
passed`, `plugin-doctor [marketplace-wide]` clean, `module-tests` 0 failed / 0 errors. Round 2 result
after the verification fixes is recorded below in Findings.

Lockfile churn: `./pw` rewrote `uv.lock` under the session interpreter. It was backed out with
`git checkout -- uv.lock` and never staged; every commit stages named deliverable paths, never
`git add -A`.

### A pre-existing cross-directory test-pollution mode (not a regression)

Running several test directories in ONE ad-hoc `pytest` invocation produces 38 failures in
`test_graph_resolver_provenance.py` / `test_native_resolver_graph_impact.py`. This is **pre-existing**
and unrelated to this change: `load_script_module` re-registers fresh module objects in
`sys.modules`, so a module-level reference captured at collection time goes stale.

Proven, not assumed: an `origin/main` worktree was run with the byte-identical invocation and its
failure list `diff`s **identical** to this branch's — 38 = 38, same tests. The real build runs
per-module and is green. Recorded in Residue.

## Findings

Ten findings from the verification sub-agent, plus two this run caught itself while fixing them.
Recorded per instance.

| # | Source | Finding | Disposition |
|---|---|---|---|
| F1 | Sub-agent | **`capabilities` reported `module_edges: derivable` when every resolver was switched off.** `resolver_count` was `len(resolvers[])`, and disabled resolvers are deliberately kept in that list, so a fully-disabled envelope claimed a capability it did not have — violating the invariant `doc/concepts/code-intelligence.adoc` states outright ("a registered-but-unrun producer is never reported as a capability"). | **Fixed.** Withheld records carry `dispatched: false`; new `count_dispatched()` backs `resolver_count` at all four assignment sites; `capabilities` names only dispatched producers. Four new tests. |
| F2 | Sub-agent | **`resolvers[]` was documented as "one record per resolver that ran"**, which the gate made false — the list now also holds resolvers that did not run. | **Fixed** at the two sites that describe the list's *contents* (`client-api.md`, `_derive_edges` docstring) and in the seam contract. The four handler docstrings describing `resolver_count`'s *meaning* were re-read and left alone: the count now excludes withheld resolvers, so "0 means no resolver ran" is true again by construction. That was the reason for this design. |
| F2b | Sub-agent | `doc/concepts/code-intelligence.adoc`'s two-row discriminator table did not cover the new state. | **Fixed** — third row added (`resolver_count: 0` with a non-empty `resolvers[]` = "switched off on this machine"), and the "warrants opposite reactions" sentence extended to three. |
| F3 | Sub-agent | **"the two Axis-C methods" survived in five places** after the ABC gained a third: `extension_base.py`'s own class docstring, `extension-contract.md`'s "The two methods below form the complete Axis-C contract", and the module docstrings of `build-maven` / `build-npm` / `build-pyproject` — every one of them in a file this diff had already edited. | **Fixed** at all five. The Axis-D counterparts (`PathAttributionBase`, genuinely still two) were checked individually and deliberately left unchanged. |
| F4 | Sub-agent | **The ABC contract test was stale and had no coverage for the new method** — its docstring enumerated two defaults, `test_subclass_overriding_both_methods_is_accepted`, and no test asserted `DerivationResolverBase().derivation_file_patterns() == []`. | **Fixed** — docstring and test names corrected, the fixture supplies the third method, and `test_declared_file_patterns_default_to_empty` pins the ABC default a third-party resolver relies on. |
| F5 | Sub-agent | The Configuration submenu Page 4 is now at the `AskUserQuestion` 4-element cap, so the next entry forces a Page 5. | **Accepted, not fixed** — the pagination pattern explicitly supports adding pages, and pre-building an empty Page 5 for plans that do not exist yet is speculative. Recorded in Residue for the sibling plans the Coordination note names. |
| F6 | Sub-agent | `extension-api/SKILL.md`'s Canonical-invocations intro was edited to claim it covers `extension_api.py`, but only the new verb got a block — `resolve-skills` had none. | **Fixed** — a `resolve-skills` block was added, making the claim true. (`plugin-doctor` was clean marketplace-wide in round 1, so this never tripped the gate; it was an internal inconsistency, fixed on its merits.) |
| F7 | Sub-agent | **Asymmetric fail-open**: the seam's gate guards the per-resolver `enabled` read, the roster did not, so one malformed entry would raise out of the read the menu depends on. | **Fixed** — per-resolver guard added, plus `test_raising_enabled_check_treats_the_resolver_as_active` mirroring the seam's own test. |
| F8 | Sub-agent | `run-config-standard.md`'s "Full Example" block lacks `derivation_resolvers`. | **Rejected — pre-existing drift, out of scope.** That block already omitted `language_servers`, `display_timezone`, `build.queue` and `ci` before this change. Adding only the new section would deepen the inconsistency; fixing it properly means reconciling five unrelated sections, which is not this plan's work. The two blocks that *are* maintained were updated. Recorded in Residue. |
| F9 | Sub-agent | Two test files written in the same commit disagreed on isolation: the roster test documents the `sys.modules` hazard and defers its patch target, its sibling used the module-level import the docstring warns against. | **Fixed** — the same deferral applied to the sibling. |
| F10 | Sub-agent | The report's deliverables table never named `_cmd_client_query.py`, `extension_base.py`, or the three `build-*/extension.py` edits, and five sections were `TBD`. | **Fixed** — this report. |
| S1 | **This run, self-caught** | The first F1 fix stamped `dispatched: True` on **every** merge report, which broke **45 existing exact-dict assertions** pinning the merge's report shape — a deliberate contract those tests encode. An earlier grep for exact-dict pins had used too narrow a pattern and wrongly reported none. | **Fixed by narrowing**: the merge's shape is left untouched (it only ever reports resolvers it called, so the marker is redundant there); only the *new* withheld records carry `dispatched: false`, and its **absence** is the dispatched case. Blast radius went from 45 tests to 0. |
| S2 | **This run, self-caught** | After that narrowing, two of my own new assertions still expected `dispatched is True` on merge reports and failed. | **Fixed** — they now assert the key is *absent*, which is the documented contract. |
| S3 | **This run, own beyond-diff sweep** | **The rendered provenance footer credited disabled resolvers with deriving edges** — `_resolver_provenance_line` used `len(resolver_reports)` and every id, so a switched-off resolver appeared in "derived by N resolver(s)". The rendered form of exactly the F1 defect, at a surface the sub-agent did not flag. | **Fixed** — the footer names only dispatched resolvers as derivers, states withheld ones separately, and has a distinct wording for "all switched off" that cannot be confused with "none registered". Two new tests. |

### One sub-agent claim rejected on the contract

The sub-agent's closing note said the lane "records [a `/sync-plugin-cache`] as owed" for the
`marketplace/bundles/` edits. It does not, and the opposite is stated explicitly: a cloud run
**neither performs nor owes** a sync, because it is a machine-local build step reading the git-ignored
`target/` and writing `~/.claude/`. No sync debt is recorded.

## Reviewer participation

TBD — filled in after the PR review cycle.

## Cost

- **Tokens:** not available to the agent in this session — the harness does not expose a usage counter
  to the running agent, so no figure is stated rather than an invented one.
- **Wall-clock:** ~2h10m of session time from first tool call to the merge gate (derived from the run's
  own command timings, not from an external clock).
- **Population:** one interactive Claude Code cloud session. ⛔ **Not comparable to a plan-marshall
  `metrics.toon` total**, which counts an orchestrator-plus-agent dispatch tree under plan-marshall's
  per-task billing boundary. This session shares neither that boundary nor that tree, so the figures
  cannot be reconciled and no equivalence is implied.

## Contract check (Step 9)

TBD

## What have we learned (Step 9)

TBD

## Residue

1. **Configuration menu Page 4 is full** (F5). The plan's Coordination note requires two sibling plans
   to land their language-server settings *inside* this surface. The next entry needs a Page 5, built
   with the documented "More..." continuation pattern — mechanical, but it is the next author's step,
   not something to pre-build.
2. **`run-config-standard.md` "Full Example" is drifted** (F8) — missing `language_servers`,
   `display_timezone`, `build.queue`, `ci`, and now `derivation_resolvers`. Pre-existing; worth one
   reconciliation pass that is not this plan's.
3. **Pre-existing cross-directory pytest pollution** — 38 tests fail when several test directories
   share one ad-hoc invocation, on `origin/main` identically. The per-module build is unaffected. The
   remedy is the `sys.modules` deferral this run applied to its own two files; applying it across the
   affected legacy files would be a standalone cleanup.
4. **`HARVEST_LANGUAGE` is Python-only**, so the `lsp` resolver declares `['**/*.py']`. If the harvest
   widens to a per-language strategy, that declaration must widen with it.
