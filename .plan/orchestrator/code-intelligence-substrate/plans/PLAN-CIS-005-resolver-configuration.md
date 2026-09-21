# PLAN-CIS-005: Configure Which Resolvers Run, Per Machine

epic: code-intelligence-substrate
workstream: WS-02

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-marshall-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

## Objective

PLAN-02's seam admits N simultaneously-active resolvers, and PLAN-CIS-003/PLAN-CIS-004 supply several. Nothing
yet decides **which resolvers run for which files** in a given checkout. That binding is
**machine-specific**: a resolver may depend on locally-installed tooling, so the same project can
legitimately have different active resolvers on different machines.

Give the binding an operator-facing configuration surface in `marshall-steward` and persist it in the
machine-local run configuration.

## Deliverables

1. A new `marshall-steward` menu for resolver configuration: list discovered resolvers, show which
   are active and for which file patterns, enable/disable, and set precedence.
2. A resolver section in the run-configuration schema, persisted at
   `.plan/local/run-configuration.json`, with the mapping from file pattern / language to resolver.
3. Resolution precedence when several resolvers claim the same file, and a documented default for an
   unconfigured project — which MUST be a working default, not an empty binding.
4. **Retire the dead `.gitignore` negation** at line 29 (`!.claude/run-configuration.json`) and drop
   "and run configuration" from the line-26 comment that introduces it. ⛔ **Surgical: line 29 and
   the comment wording only.** Lines 27-28 (`!.claude/skills/`, `!.claude/commands/`) are LIVE and
   load-bearing — 42 tracked files depend on them — and MUST NOT be touched. This deliverable is
   folded in here by operator decision because this plan is the one that establishes the correct
   store, so it is also the right place to remove the rule that misdirects readers to a
   non-existent one.
5. **Documentation.** `doc/user/configuration.adoc` (**OBSERVED**: the file exists) — the new
   `marshall-steward` resolver menu, what it binds, and where it persists. Extend
   `manage-run-config`'s `standards/run-config-standard.md` with the new keyed section, and state
   explicitly that the store is `.plan/local/run-configuration.json` and is machine-local. ⛔ Ship
   docs **in this plan**.

## Claim Labels

- **OBSERVED**: `.plan/local/run-configuration.json` is the run-configuration store, it **exists**
  (12,756 bytes at time of staging), and it is **machine-local** — `git check-ignore -v` reports it
  ignored by `.gitignore:41` (`.plan/*`, whose only exceptions are `.plan/marshal.json` and
  `.plan/project-architecture/`). **This is the store; there is no ambiguity about which file to
  use.**
- ⚠ **OBSERVED (stale gitignore rule, do not read it as evidence of a file)**: `.gitignore:29`
  carries a negation `!.claude/run-configuration.json` under a comment about allowing run
  configuration to be "shared" — but **that file does not exist and is not tracked** (`ls` reports
  no such file; `git ls-files` returns nothing). It is a leftover rule from an earlier layout, and
  **deliverable 4 retires it.**
  ⛔ **This orchestrator initially read that rule as proof of a live shared file and nearly escalated
  a non-existent conflict between the operator's "machine-specific" requirement and the
  run-configuration store.** The lesson is carried here deliberately: a `.gitignore` entry describes
  a *rule*, never the *existence* of a file.
- **OBSERVED (the boundary of deliverable 4)**: `git ls-files .claude/` returns **42 tracked files**,
  every one under `.claude/skills/` or `.claude/commands/`. ⇒ the negations at `.gitignore:27-28` are
  **live and load-bearing**; only line 29 is dead. Verified by enumeration, not by sampling.
- **HYPOTHESIS**: removing line 29 changes nothing about what git tracks, since the file it names
  does not exist. Confirm/refute by running `git status --porcelain` and a `git check-ignore -v` over
  `.claude/skills/` and `.claude/commands/` **before and after** the edit and diffing the results
  (verify-at-outline). ⚠ A `.gitignore` edit is the kind of change that looks inert and is not — the
  confirm/refute step is cheap and mandatory here.
- **OBSERVED**: `manage-run-config` already persists keyed sections (`commands`, `ci_durations`,
  timeouts, warnings) in `run-configuration.json`, and its store is main-anchored so reads/writes
  resolve against the main checkout regardless of caller cwd. A resolver section follows the existing
  keyed-section pattern.
- **HYPOTHESIS**: `marshall-steward` has a menu structure a new entry can be added to without
  restructuring — confirm/refute at `marketplace/bundles/plan-marshall/skills/marshall-steward/`
  § the verb/menu dispatch (verify-at-outline). **This orchestrator did NOT read the steward's menu
  implementation** — the claim is inferred from the skill's described role as a configuration wizard.
- **HYPOTHESIS**: file-pattern → resolver is the right binding key, rather than language, module, or
  build system. Confirm/refute against PLAN-CIS-003's two resolvers (markdown and Python within the same
  bundle tree) at outline (verify-at-outline). ⚠ Those two split by **file extension inside one
  module**, which is evidence for pattern-keying and against module-keying — but it is a single data
  point.
- **Verify-first clause**: deliverable 3's "working default for an unconfigured project" is the
  operator's binding tier constraint — an unconfigured project must lose nothing. A design where
  resolvers only run once configured would reintroduce the zero-edge defect as a *configuration*
  failure instead of a *derivation* one. Settle the default before scoping.

## Expected Surface

- **HYPOTHESIS**: `marketplace/bundles/plan-marshall/skills/marshall-steward/` — new configuration menu (verify-at-outline)
- **OBSERVED**: `marketplace/bundles/plan-marshall/skills/manage-run-config/scripts/run_config.py` — new keyed section
- **OBSERVED**: `marketplace/bundles/plan-marshall/skills/manage-run-config/standards/run-config-standard.md` — schema documentation
- **HYPOTHESIS**: `marketplace/bundles/plan-marshall/skills/extension-api/` — the seam reads the binding to decide which resolvers activate (verify-at-outline)
- **OBSERVED**: `.gitignore`:26,29 — the dead negation and its introducing comment (deliverable 4). ⛔ Lines 27-28 are out of bounds
- **OBSERVED**: `test/plan-marshall/` — tests

## Dependencies and Sequencing

- **Depends on**: PLAN-02 — there is nothing to configure until the N-resolver seam exists.
- **Best paired with**: PLAN-CIS-003 and PLAN-CIS-004, which supply the resolvers this plan binds. ⚠ Landing
  this before any real resolver exists would ship a menu that configures a single Maven resolver —
  technically correct, practically untestable.
- ✅ **Surface-disjoint from PLAN-CIS-003** (`marshall-steward` + `manage-run-config` vs
  `pm-plugin-development`) and **from PLAN-CIS-004** (vs the `build-*` bundles). May run concurrently with
  either once PLAN-02 lands.
- ⚠ **Touches `manage-run-config`**, which is a widely-consumed core skill — check the sibling epic's
  queue for any plan staged against it before emitting.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/code-intelligence-substrate/plans/PLAN-CIS-005-resolver-configuration.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/local/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-marshall-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
