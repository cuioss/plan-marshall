# Next Capabilities — Planning Documents

## What this directory is

A focused record of the next capability workstreams for plan-marshall, derived
from a capability-gap review of the workflow. Each document describes proposed
work, grounded in the mechanisms that exist today. For where these ideas were
informed by prior art, see [`doc/concepts/design-influences.adoc`](../concepts/design-influences.adoc).

These are **planning documents, not implementation.** Each workstream below names
the real plan-marshall surface it builds on (personas, recipes, finalize steps,
architecture hints) and the concrete files it would touch. Read
[`principles.md`](principles.md) first — it governs every workstream (reuse over
reinvention, findings-pipeline as the universal sink, no new stores, encoded
verification over live-run surfaces, document hygiene).

The unifying thesis: **plan-marshall already has the deep machinery (deterministic
state, worktree isolation, structured findings, multi-reviewer review, the
architecture-hints store). The next gains come from cheaper paths onto that
machinery and from feeding more signal back into it** — not from new subsystems.

**The numbering reflects the recommended implementation order.**

## Workstreams

| # | Workstream | What it adds | Builds on | Document |
|---|------------|--------------|-----------|----------|
| 03 | Audit recipes | `recipe-code-review` + `recipe-security-audit` as standalone, single-envelope entry points emitting into findings | `ext-point-recipe`, `manage-findings`, `ext-triage-*` | [03-audit-recipes.md](03-audit-recipes.md) |
| 04 | Routing v2 | A recipe-match routing tier ahead of light/deep, so known-shape requests skip the full pipeline (token + wall-time) | `manage-status planning-lane`, recipe registry, lesson auto-suggest | [04-routing-v2.md](04-routing-v2.md) |
| 05 | Security audit finalize step | `default:finalize-step-security-audit` — two-layer focused context (`persona-security-expert` + per-domain `security` profile skills) | finalize-step discovery, `security` profile, the landed `persona-security-expert`, `ext-triage-*` | [05-security-finalize-step.md](05-security-finalize-step.md) |
| 06 | Surface encoded-test verification | Make the principle explicit (verify = encoded e2e tests; explore = user's own tools) via a concept note + optional e2e-testing standard — no browser/daemon integration | domain test skills, concept docs | [06-surface-encoded-verification.md](06-surface-encoded-verification.md) |

## Sequencing

The numbering is the recommended order; the dependency arrows below show why. The
persona / ref / profile identity model has **landed** (the `persona-*` and `ref-*`
skills, the `manage-personas` resolver, and the `profiles:` binding now exist), so
the workstreams that depended on it build directly on that surface:

```text
03 audit-recipes ──┬──► 04 routing-v2     (needs recipe targets to route to)
                   └──► 05 security-finalize-step (shares the audit engine)
05 security-finalize-step                 (uses persona-security-expert — now available)
06 surface-encoded-verification           (independent; lowest priority)
```

- **03 audit-recipes is the keystone.** Recipes are the cheap single-envelope path;
  04 routes onto them and 05 shares the security audit engine with them.
- **04 routing** depends on 03 (recipe targets to route to).
- **05 security** depends on the landed persona model (`persona-security-expert` +
  the `security` profile) and 03 (the shared audit engine). It ships as the named
  Security Expert persona.
- **06 verification** is independent guidance, lowest priority.

## Cross-cutting: the shared audit engine

Workstream 03 (`recipe-security-audit`) and 05 (`finalize-step-security-audit`)
MUST share one audit implementation with two entry points — on-demand recipe vs
automatic finalize step. Author the per-domain skill-selection + audit-run logic
once; both surfaces call it.

## Lifecycle of this directory

This directory is self-consuming:

- **Each workstream document is removed when its plan lands.** Completing a plan
  includes deleting its `NN-*.md` here (and pruning the row from this README's
  workstream table) as part of that plan's own finalize.
- **The `doc/next/` directory is removed entirely after the final plan lands.**
  The last plan to complete also deletes `README.md` and `principles.md` and the
  now-empty directory.
- **Every plan updates the canonical docs it affects.** Each workstream document
  carries a "Documentation to update" section naming the `doc/user/*` and
  `doc/concepts/*` files that plan must revise. Those updates are deliverables of
  the concrete plan, not of this planning directory. Where a needed concept doc
  does not yet exist, the plan creates it.

## What we are NOT doing

- No always-on LLM request classifier — routing stays heuristic-first with at most
  one bounded LLM fallback pass (see [04](04-routing-v2.md)).
- No new preference/learning store — preference signal reuses the existing
  `enriched.json` hints surface.
- No live browser verification or exploration surface — see
  [06](06-surface-encoded-verification.md), which only *surfaces* the
  encoded-verification principle and builds no browser/daemon integration.
- No `/careful`-style in-session destructive-command guard — worktree isolation
  and the existing Bash hard-rules already cover this; explicitly dropped.
- No role-play persona prose — personas are structured, data-declared skills
  (see [`doc/concepts/personas.adoc`](../concepts/personas.adoc)), not "You are a
  seasoned…" preambles.
- No version numbers, changelogs, or dated update sections in any document.
