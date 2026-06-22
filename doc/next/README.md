# Next Capabilities — Planning Documents

## What this directory is

A focused record of the next capability workstreams for plan-marshall, derived
from a comparison against external AI-development workflows (notably gstack). Each
document describes proposed work, grounded in the mechanisms that exist today.

These are **planning documents, not implementation.** Each workstream below names
the real plan-marshall surface it builds on (router, recipes, finalize steps,
architecture hints) and the concrete files it would touch. Read
[`principles.md`](principles.md) first — it governs every workstream (reuse over
reinvention, findings-pipeline as the universal sink, no new stores, integrate
external tools rather than rebuild them, document hygiene).

The unifying thesis: **plan-marshall already has the deep machinery (deterministic
state, worktree isolation, structured findings, multi-reviewer review, the
architecture-hints store). The next gains come from cheaper paths onto that
machinery and from feeding more signal back into it** — not from new subsystems.

## Workstreams

| # | Workstream | What it adds | Builds on | Document |
|---|------------|--------------|-----------|----------|
| 01 | Routing v2 | A recipe-match routing tier ahead of light/deep, so known-shape requests skip the full pipeline (token + wall-time) | `manage-status planning-lane`, recipe registry, lesson auto-suggest | [01-routing-v2.md](01-routing-v2.md) |
| 02 | Audit recipes | `recipe-code-review` + `recipe-security-audit` as standalone, single-envelope entry points emitting into findings | `ext-point-recipe`, `manage-findings`, `ext-triage-*` | [02-audit-recipes.md](02-audit-recipes.md) |
| 03 | Security audit finalize step | `default:finalize-step-security-audit` — domain-agnostic, loads per-domain security skills by affected-module domain | finalize-step discovery channel, per-domain security skills, `ext-triage-*` | [03-security-finalize-step.md](03-security-finalize-step.md) |
| 04 | Preference learning via hints | Feed recurring user gate-dispositions back as `best_practices`/`insights` in `enriched.json` so future outlines bias toward learned preferences | PR #744 architecture-hints, `manage-findings` resolutions, lessons-capture B3 | [04-preference-learning-hints.md](04-preference-learning-hints.md) |
| 05 | Live verification (integrate) | Wrap an existing browser/acceptance tool behind a thin recipe/finalize step — integrate, do not build a daemon | external tool (e.g. Playwright MCP), `architecture which-module`, `manage-findings` | [05-live-verification-integrate.md](05-live-verification-integrate.md) |

## Sequencing

```text
02 audit-recipes ──┬──► 01 routing-v2 (needs recipe targets to route to)
                   └──► 03 security-finalize-step (shares the audit engine)

04 preference-learning-hints  (independent; highest reuse, smallest scope)
05 live-verification          (independent; research spike first, lowest priority)
```

- **02 is the keystone.** Recipes are the cheap single-envelope path; both 01
  (routes onto them) and 03 (shares the security audit engine) depend on it.
- **01 is the headline** but only pays off once recipes exist to route to.
- **03** ships the security audit as an automatic gate; its on-demand twin is the
  `recipe-security-audit` from 02. One audit engine, two entry points.
- **04 and 05 are independent** and can proceed any time. 04 has the highest
  reuse of existing machinery; 05 is the least-defined and should start as a spike.

## Cross-cutting: the shared audit engine

Workstream 02 (`recipe-security-audit`) and 03 (`finalize-step-security-audit`)
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
  one bounded LLM fallback pass (see [01](01-routing-v2.md)).
- No new preference/learning store — preference signal reuses the existing
  `enriched.json` hints surface (see [04](04-preference-learning-hints.md)).
- No home-grown browser daemon — live verification integrates an existing tool
  (see [05](05-live-verification-integrate.md)).
- No `/careful`-style in-session destructive-command guard — worktree isolation
  and the existing Bash hard-rules already cover this; explicitly dropped.
- No version numbers, changelogs, or dated update sections in any document.
