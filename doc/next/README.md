# Next Capabilities — Planning Documents

## What this directory is

A focused record of the next capability workstreams for plan-marshall, derived
from a capability-gap review of the workflow. Each document describes proposed
work, grounded in the mechanisms that exist today. For where these ideas were
informed by prior art, see [`doc/concepts/design-influences.adoc`](../concepts/design-influences.adoc).

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
| 03 | Security audit finalize step | `default:finalize-step-security-audit` — two-layer focused context (`dev-general-security` + per-domain `security` profile skills) | finalize-step discovery, `security` profile, `dev-general-security`, `ext-triage-*` | [03-security-finalize-step.md](03-security-finalize-step.md) |
| 04 | Preference learning via hints | A cross-plan command (modeled on `audit-archived-plan-retrospectives`) detects recurring user gate-dispositions, routes them to `enriched.json` `best_practices`, and implicitly archives | PR #744 architecture-hints, `audit-archived-plan-retrospectives`, `manage-findings` | [04-preference-learning-hints.md](04-preference-learning-hints.md) |
| 05 | Surface encoded-test verification | Make the principle explicit (verify = encoded e2e tests; explore = user's own tools) via a concept note + optional e2e-testing standard — no browser/daemon integration | domain test skills, concept docs | [05-surface-encoded-verification.md](05-surface-encoded-verification.md) |
| 06 | Personas | A structured persona layer: `dev-general-persona` aggregator skill (complete shell — `SKILL.md` + `standards/` reasoning + `personas/` per-persona docs), data-declared and rendered per-target, naming capability bundles for humans; models all three (Security Reviewer, Auditor, Code Reviewer) | `dev-general-*` family, build-target render, the `security`/audit/review bundles | [06-personas.md](06-personas.md) |

## Sequencing

```text
02 audit-recipes ──┬──► 01 routing-v2 (needs recipe targets to route to)
                   └──► 03 security-finalize-step (shares the audit engine)
06 personas ──────────► 03 security-finalize-step (03 consumes the Security Reviewer persona)

04 preference-learning-hints  (independent; reuses the retrospective auditor)
05 surface-encoded-verification (independent; guidance/standard, lowest priority)
```

- **02 is the keystone.** Recipes are the cheap single-envelope path; both 01
  (routes onto them) and 03 (shares the security audit engine) depend on it.
- **01 is the headline** but only pays off once recipes exist to route to.
- **06 precedes 03.** The persona layer lands first so the security audit ships as a
  named "Security Reviewer" persona rather than an unnamed bundle. 06 models all
  three personas (Security Reviewer, Auditor, Code Reviewer); it has no dependency
  on 02, so it can run in parallel with it.
- **03** ships the security audit as an automatic gate; its on-demand twin is the
  `recipe-security-audit` from 02. One audit engine, two entry points. Depends on
  both 02 (engine) and 06 (Security Reviewer persona).
- **04 and 05 are independent** and can proceed any time. 04 reuses the retrospective
  auditor's corpus sweep; 05 is guidance/standard work with no integration.

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
- No live browser verification or exploration surface — see
  [05](05-surface-encoded-verification.md), which only *surfaces* the
  encoded-verification principle and builds no browser/daemon integration.
- No `/careful`-style in-session destructive-command guard — worktree isolation
  and the existing Bash hard-rules already cover this; explicitly dropped.
- No version numbers, changelogs, or dated update sections in any document.
