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
| D1 | Resolver-configuration menu | **Done** | `marshall-steward/references/menu-derivation-resolvers.md` (new), wired into `menu-configuration.md` Page 4 + routing + TOC + `SKILL.md` reference table. Its data comes from a new `extension_api derivation-resolvers list` verb. |
| D2 | Resolver section in the run-config schema | **Done** | `run_config.py` — `derivation_resolvers` keyed section, `get`/`set`/`list`/`remove` verbs, `read_derivation_resolvers_section()` + `is_derivation_resolver_enabled()`. Follows the `language_servers` pattern in the same store; no new store. |
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

`git diff --name-only origin/main...HEAD -- '*.py'` — **Python changes present** (11 production
scripts + 4 test files), so the full gate applies.

TBD

## Findings

TBD

## Reviewer participation

TBD

## Cost

TBD

## Contract check (Step 9)

TBD

## What have we learned (Step 9)

TBD

## Residue

TBD
