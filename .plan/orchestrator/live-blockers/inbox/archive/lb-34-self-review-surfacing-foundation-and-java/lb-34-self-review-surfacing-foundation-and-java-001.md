envelope_version=1
sender_type=plan
sender_id=lb-34-self-review-surfacing-foundation-and-java
epic=live-blockers
kind=finding
created=2026-10-10T20:25:40Z

# PLAN-LB-34 abandoned — superseded by the review split (functional review + code review)

**Outcome: abandoned by operator decision, not merged.** Nothing was pushed, no PR exists, `main` is
untouched by this plan.

## Why

During finalize, the pre-submission self-review ran four rounds over this plan's own change. Every round
found genuine defects, nearly all in the per-language diff-parsing layer this plan builds (undecodable
git output, quoted non-ASCII headers, base-branch anchoring, `splitlines()` line numbering, a carriage
return leaking into candidate cells, `+++`/`---` content lines dropped). Every real finding came from
reading changed code whole, while the reviewer reached only about 40% of the surfaced line candidates
per round. The operator concluded the apparatus has drifted from its purpose:

- The review was introduced to answer **"did the plan implement the requirements?"** — read the clarified
  request and the solution outline, compare with the code. That needs no domain knowledge.
- It became an implementation review driven by per-language surfacers, which PLAN-LB-34/35/36 would have
  multiplied.

**Operator direction:** split the review apparatus into (1) a domain-free **functional review** and (2) a
**code review** against general best practice and the project's own conventions (built on the
cuioss-review-bot pack generator with a new, non-security derivation; security stays its own reviewer).
Both land in ONE plan, with a breaking-change migration of every configured repository on this machine.

## The new plan — highest priority of the epic

Two draft documents, one plan, written in the main checkout (not yet staged — please assign the number,
stage them under `plans/`, add the queue row, and make it the head of the epic):

- `.plan/temp/PLAN-LB-NN-functional-review.md` — main document: functional review (D1–D5), switch-over and
  removal of `default:pre-submission-self-review`, the surfacing extension point and the plan-marshall
  surfacer (D6–D7), a `marshall-steward upgrade` migration (D8), and the post-landing rollout to every
  repository under `/home/oliver/git/` with a `.plan/marshal.json` (D9). Carries the hand-off command.
- `.plan/temp/PLAN-LB-NN-code-review.md` — companion: code-review rule set derived from the domains'
  implementation/testing/quality standards without security (D10), the `default:code-review` step
  (D11–D13), mapping of the old self-review's check classes (D14), switching the cuioss-review-bot settings
  repository to the same rulebook (D15), and configuration/migration for both steps (D16).

The specs state two write-boundary exceptions, both after landing: the consumer `marshal.json` rollout (D9)
and the `cuioss/cuioss-review-bot` settings repository (D15).

## Plans to park

- **PLAN-LB-35** (JavaScript and Python surfacers) — superseded; built on the surfacer foundation that is
  being removed.
- **PLAN-LB-36** (documents, containers and requirements surfacers) — superseded for the same reason.
- **PLAN-LB-26** — edits `pre-submission-self-review.md` and one of its `qgate add` calls; that workflow is
  deleted by the new plan. Park it, or re-scope it against the new steps when the new plan is staged.
- **PLAN-LB-28** — took over PLAN-LB-03 D1–D4 (self-review) and was handed them back to LB-34; it is the
  Maven plan only, but check that no self-review deliverable remains on it.

## What is kept for salvage

Local branch `feature/lb-34-self-review-surfacing-foundation-and-java` (HEAD `a35410713`, 24 commits on top
of `origin/main` 66c6e4cd0) is kept, not pushed. Pieces the new plan may reuse:

- `script-shared/scripts/git_lines.py` — git-faithful line splitting and decoding.
- the refusal of an unreadable footprint / unreadable diff instead of an empty change.
- `skill-domains set-extensions` input validation (class list and notation shape).
- `CLAUDE.md` component-count correction (160 components, 156 skills — recount after the new plan).

Open self-review findings at abandonment (not fixed): a carriage return reaching candidate cells
(`self_review_surfacing.py:360`, `_self_review_plan_marshall_detectors.py:1114`) and in-hunk
`+++`/`---` content lines dropped (`self_review_surfacing.py:387`). Both live only in code this plan adds or
moves; nothing on `main` is affected by them beyond what `main` already had.

## Tooling defects observed during this run (for triage)

- `scope_creep_check` fails on every call with `finding_persist_failed`: `manage-findings` rejects the
  finding type `scope_creep_warning`, so the guard records nothing.
- The root-level harness shape guards (`test/test_harness_shape_guards.py`) run only in the whole-tree
  run; module-scoped verification never sees them, and they failed this plan twice late.
- The pre-submission self-review's candidate volume (809 line candidates + 132 changed units in round 1)
  far exceeds what one reviewer dispatch reaches; most prose lists were never examined in any round.
