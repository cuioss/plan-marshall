# PLAN-70: Retire the Gemini Bot Registry, and Ground `pr-agent.md` in Observed PR-Agent Behaviour

epic: truthful-signals
workstream: WS-01

> Staged from an operator directive (2026-07-26): "Gemini is to be replaced with pr-agent. Remove the
> gemini details as well … verify all references are gone. Later (while implementing the plan)
> analyze the pr-agent reviews, analyze and adapt `standards/pr-agent.md` to the findings /
> observations." Grounded at HEAD by the orchestrator.

## Objective

Gemini was sunset 2026-07-17 and dropped from the shipped default bot list, but its registry doc and
~40 files of references remain — a retired reviewer still carried as live machinery. Remove it, and
replace the *placeholder* quality of `standards/pr-agent.md` with a standard grounded in what
PR-Agent actually posts.

Two halves with different epistemics, deliberately kept in one plan because they are the same
substitution: **D1–D3 are a deterministic removal sweep; D4 is an evidence-gathering pass that
cannot run until PR-Agent has produced real reviews.** See the gate.

## ⚠ Grounding — OBSERVED, verified at HEAD (2026-07-26)

- OBSERVED — `automatic-review/SKILL.md:23`: Gemini "is registered (`standards/gemini.md`) but is NOT
  in the shipped default following its 2026-07-17 sunset — add `gemini` here to re-enable it". So it
  is already non-operative by default; this plan removes the machinery, not a behaviour.
- OBSERVED — `standards/gemini.md` exists and is the registry doc the bot-list contract points at.
- OBSERVED — **42 files** carry the string `gemini` across `marketplace/`, `.github/`, `doc/`, and
  `test/`. Density varies sharply and the sweep MUST classify rather than blind-replace:
  `test/plan-marshall/automatic-review/test_bot_registry.py` (10 hits — real registry coverage),
  `_github_pr.py` / `github_re_review.py` (1 hit each — likely an author-login or example),
  `.github/workflows/pr-agent.yml` (**0 hits** — the filename matched the earlier search, not the
  content). Seven `ext-triage-*/standards/pr-comment-disposition.md` files across six bundles carry
  per-bot disposition guidance.
- OBSERVED — `standards/pr-agent.md` is already registered and, like Gemini, deliberately NOT in the
  shipped default: it "is opt-in per repository (the repo must carry the
  `reusable-pr-agent-review.yml` caller workflow)".
- OBSERVED (2026-07-26) — **this repo has already opted in**: `.plan/marshal.json`'s
  `plan-marshall:automatic-review` block carries `enabled_bots: "coderabbit,sourcery,pr-agent"`.
  Gemini is correctly absent, confirming the sunset is real at the config layer. **But `pr-agent`
  being listed does NOT prove it is operative** — this project's recorded archetype is exactly
  "enabled-bots-vs-operative drift" (a bot in the list that never actually runs), and the PR-Agent
  rollout was blocked on operator-side setup. **D4's gate must check for posted reviews, NOT for
  list membership** — reading `enabled_bots` and concluding PR-Agent is live would be that archetype
  committed inside the very plan meant to ground the standard in evidence.

## Deliverables

### D1 — GATE: classify every reference, and settle the retired-bot contract (mutates nothing)

Enumerate all 42 files and classify each hit: (a) operative machinery (registry doc, bot-list
defaults, author-login constants, re-review strategy wiring); (b) documentation/prose; (c) test
fixture or example data where `gemini` is an arbitrary bot name and removing it would weaken generic
coverage rather than delete dead code; (d) false positive (filename-only matches). **Class (c) is the
trap** — a registry test that exercises "an unregistered bot" is not Gemini-specific machinery, and
blanking it reduces coverage.

Settle one contract question: **what happens if a retired bot posts a comment anyway?** Standing
guidance in this project is that a pruned bot can still post a valid finding, which must not be
ignored. Decide whether removing the registry doc leaves such a comment (i) unclassifiable and
silently dropped — unacceptable, the exact archetype this epic targets — or (ii) routed to a generic
unknown-bot path that still files a finding. If no such path exists, D2 must add one or the removal
is a fail-open change.

### D2 — remove the Gemini registry and its operative references

Delete `standards/gemini.md` and every class-(a) reference: bot-list documentation, author-login
constants, re-review wiring, and the `SKILL.md:23` description's Gemini clause. Preserve the D1
verdict on unknown-bot handling.

### D3 — sweep documentation and tests; verify zero residue

Update class-(b) prose and the seven `pr-comment-disposition.md` files. Re-point class-(c) fixtures at
a neutral placeholder bot name rather than deleting the coverage. **Acceptance: a repo-wide
case-insensitive search for `gemini` returns only intentional historical records** (ADRs, archived
plans, landing records — which are audit history and MUST NOT be rewritten). Name the surviving set
explicitly in the PR body so "all references are gone" is a checked claim, not an assertion.

### D4 — ⛔ EVIDENCE-GATED: ground `pr-agent.md` in observed reviews

**Do not author this from assumption.** Collect actual PR-Agent review output — its comment shapes,
author login, severity vocabulary, completion signal, noise patterns — and adapt
`standards/pr-agent.md`'s registry fields (`author_login`, `trigger_comment`,
`completion_check_name`, `honors_skip_label`, `ignore_patterns`, `severity_map`) plus its triage
guidance to what was observed. Every adapted field cites the PR and comment it was derived from.

**Gate:** this deliverable requires PR-Agent to have actually reviewed something. Per the project
record, the PR-Agent rollout was blocked on operator action (the `cuioss-review-bot` App and org
secrets). **At outline, verify PR-Agent has posted reviews on at least one real PR.** If it has not:
D4 is NOT satisfiable — split it out and ship D1–D3 alone rather than writing a speculative standard.
A registry doc authored from assumption is precisely the defect class this epic exists to remove.

### D5 — tests

Bot-registry coverage no longer references Gemini but still covers the registered-bot and
unregistered-bot paths (per the D1 class-(c) verdict); the D1 unknown-bot contract is asserted — a
comment from an unregistered bot is not silently dropped.

## Expected surface

- OBSERVED: `automatic-review/standards/gemini.md` (delete), `automatic-review/SKILL.md:23` (bot-list
  description)
- OBSERVED: `automatic-review/standards/pr-agent.md` (D4)
- OBSERVED: `workflow-integration-github/` — `_github_pr.py`, `github_pr.py`, `github_re_review.py`,
  `SKILL.md`
- OBSERVED: seven `ext-triage-*/standards/pr-comment-disposition.md` across `pm-dev-python`,
  `pm-requirements`, `pm-dev-oci`, `pm-documents`, `pm-dev-frontend`, `pm-plugin-development`,
  `pm-dev-java`
- OBSERVED: `phase-6-finalize/workflow/create-pr.md`, `standards/branch-cleanup.md`,
  `manage-findings/standards/jsonl-format.md`, `marshall-steward/references/landing-cycle.md` +
  `wizard-flow.md`, `extension-api/standards/ext-point-lane-element.md`,
  `automatic-review/standards/coderabbit.md` + `sourcery.md`,
  `plugin-doctor/scripts/_analyze_markdown.py`
- OBSERVED: ~14 test modules under `test/` (classify per D1 before touching)

**Disjointness:** `automatic-review` + `workflow-integration-github` + the `ext-triage-*` disposition
docs. Disjoint from PLAN-66 (`manage-locks`), PLAN-53 (`marshall-orchestrator`), PLAN-51
(`plan-retrospective`), PLAN-57 (`manage-status`), PLAN-69 (`script-shared` /
`tools-script-executor`), PLAN-67 (`manage-config` / `marshall-steward` — ⚠ light adjacency: both
touch `marshall-steward` references, different files; re-check if concurrent).
⚠ **OVERLAPS PLAN-71** — both touch `automatic-review/SKILL.md`. Sequence, do not parallelize.

## Notes

- Scope-bloat check: 5 deliverables, under the guard. D4 is the split candidate if its gate fails —
  and splitting on a failed gate is the correct outcome, not a scope miss.
- The removal is docs+wiring, not behaviour: Gemini is already out of the shipped default, so D1–D3
  should produce no runtime change. If the plan discovers a behaviour change, that is a finding —
  it means Gemini was more live than the sunset claimed.

## Write-Boundary

Repository source + tests only; NO `.plan/local/orchestrator/` writes. See
`persona-marshall-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
