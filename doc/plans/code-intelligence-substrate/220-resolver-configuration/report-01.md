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

`git diff --name-only origin/main...HEAD -- '*.py'` — **Python changes present**: 14 production
scripts and 6 test files at the time of writing (re-derived from the command, not carried forward from
an earlier round — the figure moved every round as fixes landed). The full gate therefore applies.

`./pw verify` was run over the whole branch diff, direct (no generated executor in this lane), once
per verification round. Every dimension clean each time — `ruff … All checks passed!`,
`mypy(production)` 405 files, `mypy(test)` 753 files, `SPDX-header check passed`,
`plugin-doctor [marketplace-wide]`, `module-tests` 0 failed / 0 errors:

| Round | Tree | Result |
|---|---|---|
| 1 | pre-fix | **20091 passed, 14 skipped** |
| 2 | after the round-1 fixes | **20098 passed, 14 skipped** |
| 3 | after the round-2 fixes | recorded at the merge gate |

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

**Three verification rounds.** Round 1 found ten findings; round 2 found that round 1's own fix was
wrong on the wire, plus ten more; round 3 found nine, six of them in this report. Each round was
dispatched because the previous one found a defect — a verification pass that found something has not
finished. Recorded per instance, per round.

| # | Source | Finding | Disposition |
|---|---|---|---|
| F1 | R1 sub-agent | **`capabilities` reported `module_edges: derivable` when every resolver was switched off.** `resolver_count` was `len(resolvers[])`, and disabled resolvers are deliberately kept in that list, so a fully-disabled envelope claimed a capability it did not have — violating the invariant `doc/concepts/code-intelligence.adoc` states outright ("a registered-but-unrun producer is never reported as a capability"). | **Fixed**, though the *representation* took two attempts — see R2-1. A withheld record is marked, `count_dispatched()` backs `resolver_count` at all four assignment sites, and `capabilities` names only dispatched producers. The marker is the `status` value `not_dispatched`, per R2-1. |
| F2 | R1 sub-agent | **`resolvers[]` was documented as "one record per resolver that ran"**, which the gate made false — the list now also holds resolvers that did not run. | **Fixed, but round 1's fix was incomplete** — see R2-2 below, which found three further statements this disposition had claimed covered. The four handler docstrings describing `resolver_count`'s *meaning* were re-read and correctly left alone: the count excludes withheld resolvers, so "0 means no resolver ran" is true by construction. That was the reason for this design. |
| F2b | R1 sub-agent | `doc/concepts/code-intelligence.adoc`'s two-row discriminator table did not cover the new state. | **Fixed** — third row added (`resolver_count: 0` with a non-empty `resolvers[]` = "switched off on this machine"), and the "warrants opposite reactions" sentence extended to three. |
| F3 | R1 sub-agent | **"the two Axis-C methods" survived in five places** after the ABC gained a third: `extension_base.py`'s own class docstring, `extension-contract.md`'s "The two methods below form the complete Axis-C contract", and the module docstrings of `build-maven` / `build-npm` / `build-pyproject` — every one of them in a file this diff had already edited. | **Fixed** at all five. The Axis-D counterparts (`PathAttributionBase`, genuinely still two) were checked individually and deliberately left unchanged. |
| F4 | R1 sub-agent | **The ABC contract test was stale and had no coverage for the new method** — its docstring enumerated two defaults, `test_subclass_overriding_both_methods_is_accepted`, and no test asserted `DerivationResolverBase().derivation_file_patterns() == []`. | **Fixed** — docstring and test names corrected, the fixture supplies the third method, and `test_declared_file_patterns_default_to_empty` pins the ABC default a third-party resolver relies on. |
| F5 | R1 sub-agent | The Configuration submenu Page 4 is now at the `AskUserQuestion` 4-element cap, so the next entry forces a Page 5. | **Accepted, not fixed** — the pagination pattern explicitly supports adding pages, and pre-building an empty Page 5 for plans that do not exist yet is speculative. Recorded in Residue for the sibling plans the Coordination note names. |
| F6 | R1 sub-agent | `extension-api/SKILL.md`'s Canonical-invocations intro was edited to claim it covers `extension_api.py`, but only the new verb got a block — `resolve-skills` had none. | **Fixed** — a `resolve-skills` block was added, making the claim true. (`plugin-doctor` was clean marketplace-wide in round 1, so this never tripped the gate; it was an internal inconsistency, fixed on its merits.) |
| F7 | R1 sub-agent | **Asymmetric fail-open**: the seam's gate guards the per-resolver `enabled` read, the roster did not, so one malformed entry would raise out of the read the menu depends on. | **Fixed** — per-resolver guard added, plus `test_raising_enabled_check_treats_the_resolver_as_active` mirroring the seam's own test. Round 2 found a **third** reader with the same gap (`cmd_derivation_resolver_list`) and round 3 found that third guard shipped untested; both closed — see R2-7 and R3-7. |
| F8 | R1 sub-agent | `run-config-standard.md`'s "Full Example" block lacks `derivation_resolvers`. | **Rejected — pre-existing drift, out of scope.** That block already omitted `language_servers`, `display_timezone`, `build.queue` and `ci` before this change. Adding only the new section would deepen the inconsistency; fixing it properly means reconciling five unrelated sections, which is not this plan's work. The two blocks that *are* maintained were updated. Recorded in Residue. |
| F9 | R1 sub-agent | Two test files written in the same commit disagreed on isolation: the roster test documents the `sys.modules` hazard and defers its patch target, its sibling used the module-level import the docstring warns against. | **Fixed** — the same deferral applied to the sibling. |
| F10 | R1 sub-agent | The report's deliverables table never named `_cmd_client_query.py`, `extension_base.py`, or the three `build-*/extension.py` edits, and five sections were `TBD`. | **Fixed** — this report. |
| S1 | R1, self-caught | The first F1 fix stamped `dispatched: True` on **every** merge report, which broke **45 existing exact-dict assertions** pinning the merge's report shape — a deliberate contract those tests encode. An earlier grep for exact-dict pins had used too narrow a pattern and wrongly reported none. | **Fixed by narrowing** the marker to the withheld records only; blast radius 45 tests → 0. That narrowing is what R2-1 then found to be wrong on the wire. |
| S2 | R1, self-caught | After that narrowing, two of my own new assertions still expected `dispatched is True` on merge reports and failed. | **Fixed** — and superseded by R2-1: they now assert `status`. |
| S3 | R1, own beyond-diff sweep | **The rendered provenance footer credited disabled resolvers with deriving edges** — `_resolver_provenance_line` used `len(resolver_reports)` and every id, so a switched-off resolver appeared in "derived by N resolver(s)". The rendered form of exactly the F1 defect, at a surface the sub-agent did not flag. | **Fixed** — the footer names only dispatched resolvers as derivers, states withheld ones separately, and has a distinct wording for "all switched off" that cannot be confused with "none registered". Two new tests. |

### Round 2 — the wire defect, and what round 1's sweep missed

| # | Finding | Disposition |
|---|---|---|
| R2-1 | ⛔ **The round-1 representation does not survive serialization.** Withheld records were marked with a `dispatched: false` **key**, but resolver reports go out as a **uniform TOON array** whose header is the union of the records' keys. A key present on only some records renders as an empty cell on the others — so a resolver that DID run printed as `dispatched: ""` beside a sibling reading `false`, which reads as *not dispatched*: the exact inversion the marker exists to prevent. The column position floated too, since the header follows first-occurrence order over an id-sorted list. Verified by driving the real serializer. | **Fixed by redesign** — the state now rides on `status`, which every report already carries: `ok` \| `error` \| `not_dispatched`. Every record keeps an identical key set, so the wire is four columns wide whatever the configuration is, and the four documented TOON schema blocks are correct as written. No consumer branches on `status` (re-verified independently in round 3). Two tests pin it against the real serializer. |
| R2-2 | **`architecture-persistence.md:606` carried verbatim the retired sentence** the F2 row claimed to have fixed, plus `resolver_count` = `len(resolvers)` at `:607` and a two-state table at `:609`. The file is normative: `client-api.md:130` routes readers to it for the graph verb's shape. | **Fixed** (all three). |
| R2-3 | **`client-api.md:99` asserted `len(resolvers)` one row below the row the F2 fix had just rewritten** to say the opposite — same table, adjacent rows. | **Fixed.** |
| R2-4 | `client-api.md:101` "Every registered resolver runs and gets a row … `resolver_count` **therefore** counts the resolvers that ran" — the "therefore" no longer follows. | **Fixed.** |
| R2-5 | The four TOON schema blocks described the row set as "one row per REGISTERED resolver". | **Fixed** — and left 4-column, which R2-1's redesign makes correct. |
| R2-6 | **`doc/user/dependency-intelligence.adoc` told the reader the opposite**: ":77 a zero row … means that resolver ran", plus a two-state empty-answer table and no pointer to the new configuration section. | **Fixed** — three edits, including an xref to `configuration.adoc#derivation-resolvers`. |
| R2-7 | **Three of the four "a disabled resolver is still reported" paragraphs were not updated** (menu, run-config standard, user configuration) — an operator following the menu would disable everything and meet `resolver_count: 0` / `not_derivable` with nothing telling them that is expected. | **Fixed** at all three. |
| R2-8 | `ext-point-derivation-resolver.md:139` "names the resolvers that ran", and its two-row anti-vacuity table. | **Fixed.** |
| R2-9 | **`test_graph_queries.py::_assert_provenance_self_consistent` asserted the retired invariant** (`resolver_count == len(resolvers)`) and stated it in its docstring, passing only because the sandboxed store never disables anything. | **Fixed** — asserts the dispatched count, and the docstring explains why the two differ. |
| R2-10 | `cmd_derivation_resolver_list` lacked the per-resolver guard its sibling got, and re-read the store once per resolver, contradicting the rationale in `read_derivation_resolvers_section`'s own docstring. | **Fixed** — one snapshot, per-entry guard. |
| R2-S1 | **Self-caught while fixing**: the `sys.modules` deferral from F9 raised `KeyError` when the test file was run alone and nothing had imported the module yet. | **Fixed** — `importlib.import_module`, which returns the live object or imports it. |

### Round 3 — what round 2's fixes made false

| # | Finding | Disposition |
|---|---|---|
| R3-1 | **`_derivation_merge.py:126` — the seam's own return contract still documented the deleted `dispatched` marker**, including "its absence IS the dispatched case", which R2-1 made actively wrong. Added by round 1, missed by round 2. | **Fixed.** |
| R3-2 | **`doc/concepts/code-intelligence.adoc:160` still said `dispatched: false`** — the only one of five sibling anti-vacuity tables round 2 did not convert, and the document the F1 row cites as the authority for the whole invariant. | **Fixed.** |
| R3-3 | **`_partition_configured_resolvers`' docstring said a disabled resolver returns `status: ok`** while the function body 45 lines below writes `not_dispatched`. Round 2 edited the inline comment, not the docstring above it. | **Fixed.** |
| R3-4 | **`test_graph_family_bundle_project.py:348` asserted `resolver_count == len(discovered_ids)`** against the real tree and the real machine-local store — green only because a fresh clone and CI have no store. A developer who disables one resolver through the new menu turns it red. Round 2 had rewritten the *sibling* test's docstring to disclaim exactly this equivalence and left the assertion encoding it. | **Fixed** — the roster assertion stays; the count is checked against the dispatched population. Test renamed, since it names the discovered set. |
| R3-5 | **ADR-014, the abstract source of every table that was updated, was not** — ":77 `resolver_count` is the roster's *cardinality*", the canonical two-row table, and "one report per producer … whether it **succeeded**". | **Fixed** — amended rather than left false. An ADR is a decision record, but a governing record stating a now-false invariant misleads harder than an amended one, and this repository does amend ADRs. The amendment also records *why* the state is a status value rather than a key, so the next implementor inherits R2-1's reasoning instead of rediscovering it. |
| R3-6 | **`client-api.md:105` — the fifth and last two-state table.** Round 2 updated the prose above it and the schema comments below it, but not the table an agent scans. | **Fixed.** |
| R3-7 | The guard R2-10 added shipped **without a test**, unlike the two siblings it claims parity with. | **Fixed** — test added. |
| R3-8 | A dead `sys.modules['_cmd_client_query']` line in my own test, twenty lines below the docstring round 2 rewrote to warn against exactly that lookup. | **Fixed** — removed. |
| R3-9 | `extension_api.main`'s `getattr(args, 'func', cmd_resolve_skills)` fallback would silently route a future verb into the wrong handler. | **Fixed** — every subparser sets its own handler and dispatch is explicit. |
| R3-R | **Six inaccuracies in this report**, including three rows describing the design R2-1 deleted, a dangling "see R2-B1/B2/B3 below" pointing at rows that were never written, "two self-caught" where the table showed three, and a file count matching no commit on the branch. | **Fixed** — this section. The lesson is recorded in § What have we learned. |

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
