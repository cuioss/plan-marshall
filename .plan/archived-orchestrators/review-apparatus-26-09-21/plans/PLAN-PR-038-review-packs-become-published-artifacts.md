# PLAN-PR-038: Review packs become published artifacts, not per-repo copies

epic: review-apparatus
workstream: WS-03

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Source side only. The consuming half is PLAN-PR-039, which MUST NOT land first.

## Objective

Today every consumer repository carries a generated `.pr_agent.toml` holding the *assembled text*
of its review charter, written at generate time by `marketplace/targets/generate.py --target
pr-agent`. The rule text is therefore duplicated into each repository, and changing a rule means a
regeneration fan-out. This plan turns the packs into **published artifacts**: the generator emits
one addressable pack per derived domain, a publish step mirrors them into
`cuioss/pr-agent-settings`, a drift guard asserts the published set equals the derived set, and the
generator stops writing a repo-local `.pr_agent.toml` at all. Nothing consumes the artifacts yet —
that is PLAN-PR-039 — so this plan is additive up to the final deletion and cannot break a live
review on its own.

The design was settled with the operator before staging. The decisions this spec implements, and
which are NOT to be re-litigated during execution: packs are **generated, never hand-written**;
they live in `pr-agent-settings` as published artifacts rather than being fetched from
plan-marshall at review time (which would make 21 repositories' reviews depend on a product repo);
selection and any per-project addition are declared in `.github/project.yml`; and the per-project
addition is **append-only**.

## Deliverables

1. **The generator emits addressable pack artifacts.** One file per derived domain plus the
   cross-cutting spine, each keyed by its domain name, replacing the single assembled blob as the
   emission unit. `compose_packs()` already produces exactly this mapping — the change is what is
   written, not what is derived.
2. **A publish path from plan-marshall to `cuioss/pr-agent-settings`.** Packs land in that
   repository as generated artifacts carrying a do-not-edit header, on merge to `main`, so the lag
   between a skill change and a pack change is minutes rather than a human's attention.
3. **A drift guard: published equals derived.** Extend
   `test/marketplace/targets/pr_agent/test_charter_invariants.py`, whose population already comes
   from `compose_packs()` rather than a literal list.
4. **The generator stops writing a repo-local `.pr_agent.toml`, and plan-marshall's own is
   deleted.** A leftover generated file is inert config that still reads as authoritative once
   PLAN-PR-039 injects by environment — the failure mode this epic keeps finding.
5. **plan-marshall's `.github/project.yml` gains the `pr-agent:` block** — `packs:` plus
   `additional_rules:` — as the reference example every other repository is migrated against.

Five deliverables, deliberately unsplit: they are one artifact contract. Splitting would leave
either packs published with nothing asserting they match the skills, or a guard with nothing to
guard.

## Claim Labels

- OBSERVED: **seven domains derive today** — `docs`, `java`, `javascript`, `oci`, `plugin`,
  `python`, `reqs` — read by executing `discover_domains(Path('marketplace/bundles'))`. Pack sizes
  2712–4395 chars; composed `python,plugin` is 5218 chars; all seven composed is 7778 chars.
  - verdict: corroborated | checked_at: 7845a4b9a383a4d58c9314bfce89970ced67c4f7 | by: review-apparatus/cleanup | rescoped: n/a | evidence: Re-grounded at HEAD 7845a4b9a, method: whole-spec-file intersection against git diff --name-only 26645688b..HEAD (197 paths). Fail-closed by design - the scan is over the WHOLE spec file, not a parsed Expected Surface section, because two section parsers disagreed on this corpus. Basename matching stays DISCARDED as non-discriminating. NO running-row exclusion applied this pass: the queue has no running plan. Intersection: 0 hit(s). EMPTY INTERSECTION - nothing in the window touched this spec, so its premise is unmoved. This is a checked negative, not an unchecked one.
- OBSERVED: domains derive from bundles carrying a `*-security`, `arch-gate-*` or `ext-triage-*`
  skill — read at `marketplace/targets/pr_agent/target.py` § `compose_selection` error text. This
  is why `maven` is **not** derivable, and it is the precondition recorded below.
- OBSERVED: the charter regression guard already exists and asks `compose_packs()` for its
  population rather than iterating a literal — read at
  `test/marketplace/targets/pr_agent/test_charter_invariants.py` § `test_population_size_is_published`,
  `test_an_empty_population_would_fail_rather_than_skip`. Its expectation literals are deliberately
  NOT imported from the thing they guard. **A new domain is therefore guarded the moment it becomes
  derivable**, which is what makes deliverable 3 cheap.
- OBSERVED: plan-marshall carries a generated repo-local `.pr_agent.toml` (6142 bytes) whose header
  reads `GENERATED, do not edit by hand`, landed by #1130 (`f5493b437`) and refined by #1313.
- OBSERVED: `security` is not a selectable domain — it is a 10-topic spine folded into every
  composed pack (`discover_spine_topics`). ⛔ It MUST remain non-selectable: a security pack a
  project can deselect is a regression, and this is the reason `additional_rules` is append-only.
- HYPOTHESIS: `cuioss/pr-agent-settings` is writable by an available token from a plan-marshall
  workflow — confirm/refute against the org App installation's repository scope
  (verify-at-outline). If refuted, the publish step needs a token grant before deliverable 2 can
  ship, and that is a blocking precondition rather than a re-scope.
- Verify-first clause: the emission unit change in deliverable 1 must be settled against
  `render_config` and every one of its callers before scoping — the function currently renders ONE
  composed pack into a TOML literal string, and whether pack artifacts reuse that renderer or need
  a separate one decides the size of this deliverable.

## Expected Surface

- OBSERVED: `marketplace/targets/pr_agent/target.py` — `compose_packs`, `compose_selection`,
  `render_config`, `PACK_SEPARATOR`, `DEFAULT_PACK`, and the emission entry point
- OBSERVED: `marketplace/targets/generate.py` — the `--target pr-agent` / `--packs` surface
- OBSERVED: `test/marketplace/targets/pr_agent/test_charter_invariants.py`
- OBSERVED: `test/marketplace/targets/pr_agent/test_pr_agent_target.py`
- OBSERVED: `.pr_agent.toml` — deleted by deliverable 4
- OBSERVED: `.github/project.yml` — gains the `pr-agent:` block
- HYPOTHESIS: a publish workflow under `.github/workflows/` (verify-at-outline — whether this is a
  new workflow or a step in an existing one is an outline decision)
- HYPOTHESIS: `cuioss/pr-agent-settings` `packs/` — FOREIGN repository (verify-at-outline). The
  foreign-checkout path exists: `marketplace/bundles/plan-marshall/skills/tools-integration-ci/scripts/ci.py` carries `--project-dir` as a top-level ROUTER flag consumed
  before dispatch, not an `add_argument`, so an argparse-table search does not find it.

## Dependencies and Sequencing

- Depends on: none.
- Blocks: **PLAN-PR-039**, which consumes these artifacts. ⛔ 039 MUST NOT land first — its
  fail-loud behaviour would fail every review in every consumer repository until packs exist.
- Overlaps with: no staged spec names `marketplace/targets/` in its Expected Surface. Re-run
  `corpus cross-check` and the live `manage-status list` immediately before emit — 8 of 14 staged
  specs currently collide with a running plan, and that set moves without notice.
- Adjacent to: `marketplace/bundles/**` security / arch-gate / ext-triage skills — the SOURCE the
  packs derive from. This plan changes how packs are emitted and never what they say. A diff that
  alters rule TEXT is out of scope and belongs to whichever skill owns the rule.

### ⛔ Recorded precondition — `maven` is deferred on purpose

The operator asked for a `maven` pack. It is **not derivable today** (see Claim Labels), and the
decision between growing the derivation and carrying an authored pack beside the generated ones was
**deliberately deferred**, with the operator's stated reason: maven is to be modularized anyway, so
the question should be answered after that work rather than before it. This plan therefore ships
exactly the seven derivable domains and **adds no authored-pack mechanism**.

⛔ Do not resolve this during execution. Adding an authored-pack directory "while we are here" would
pre-empt a decision the operator explicitly held open, and would create the two-classes-of-pack
ambiguity — "is this file generated?" — that the do-not-edit header exists to prevent.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/review-apparatus/plans/PLAN-PR-038-review-packs-become-published-artifacts.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests, plus the foreign
`cuioss/pr-agent-settings` artifacts named in the Expected Surface. It creates and edits NO file
under `.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message.
