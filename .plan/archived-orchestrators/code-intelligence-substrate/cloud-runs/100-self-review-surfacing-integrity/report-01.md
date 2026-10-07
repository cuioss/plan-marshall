# Run report — 100-self-review-surfacing-integrity (run 01)

**Date (UTC):** 2026-08-12    **Branch:** claude/self-review-surfacing-integrity-jcwvqa (harness-assigned)    **PR:** [#1189](https://github.com/cuioss/plan-marshall/pull/1189)    **Outcome:** completed (auto-merge armed — landing delegated to the merge queue)

## Skills loaded

- `cloud-plan-lane` (working contract — loaded first)
- `plan-marshall:ref-code-quality` (always) — read via bundle path
- `pm-plugin-development:plugin-script-architecture` (always) — read via bundle path
- `pm-dev-python:python-core` (Python production code) — read via bundle path
- `pm-dev-python:pytest-testing` (Python tests) — read via bundle path

Standards from these skills are loaded on-demand as the work requires.

## Deliverables

- **D1 — widen the count-prose detector at the resolver (commit `53d49f3`).** `_detect_count_prose`
  now iterates `_collect_skill_contract_sources` (SKILL.md + `standards/*.md`) instead of opening only
  `SKILL.md`, so both detectors resolve the one conceptual input through one resolver. **Verified:** a
  negative-control test plants a count in a `standards/*.md` doc and asserts it is surfaced — it FAILS
  against the pre-fix resolver (confirmed by stashing the detector change and re-running: both new
  tests failed) and passes after; an agreement test pins the detector's scanned file set to the shared
  resolver's output. Docs (SKILL.md rule 14, ext-point `count_prose` row) updated.
- **D2 — population-derived registry↔check coverage + two new checks (commit `5ae9848`).** Added
  cognitive checks 16 (`duplicate_claimable_key`) and 17 (`discard_without_report`) to the workflow
  doc — the two `in_total` registry entries the ext-point recorded as having "No consuming check".
  `keep_markers`'s consumption by check 4 is now explicit in the doc too. **Verified:** a
  population-derived test enumerates the `in_total` registry entries, publishes the population size
  (guarding against a vacuous pass over an empty population), and fails if any counted entry lacks a
  backtick-quoted reference in the Step-3 checks region; a synthetic negative control proves the
  predicate fails when a check is missing. **Dispatch-gate magnitude unchanged by construction:** no
  `in_total` flag changed, asserted by `test_new_checks_do_not_change_total_magnitude`. Coverage-gap
  paragraph in the ext-point marked closed; "fifteen"→"seventeen" reconciled across the workflow doc,
  the ext-point contract, and the implementor SKILL.md.
- **D3 — publish and require the searched-scope statement (commit `cb577b2`).** ⚠ **Claim shape
  changed** (as the plan anticipated): the scope token (`surface_scope`) and file-count token
  (`files_in_scope`) already existed. Added `scope_statement` (derived from them) emitted
  UNCONDITIONALLY by the surfacer — pinned present on full, delta, and empty (zero-file) surfaces, so
  the surface never presents an absence without the scope it was drawn against. Added the workflow rule
  "Absence claims state the scope they were drawn against": a finding rationale asserting an absence
  MUST quote the round's `scope_statement` and never phrase the claim wider than `files_in_scope`.
  Docs updated. **Enforcement split (two parts):** the surfacer half IS code-enforced and tested —
  `scope_statement` is emitted unconditionally, so the surface can never present an absence without its
  scope; the finding-*rationale* rule is workflow guidance, in the same class as all seventeen cognitive
  checks (findings are authored by the LLM cognitive review, not produced by a script, so there is no
  `findings[]` array for a Python validator to inspect). This split was raised by CodeRabbit and accepted
  — no rationale-validator was added, as that would be a new enforcement mechanism inconsistent with how
  every other check in this workflow is enforced. **This run's own absence claims carry their scope** —
  see § "Scope-bearing absence claims" below.
- **D4 — undeliverable-to-running-plan report at write time (commit `89ddcbf`).** Added optional
  `--target-plan` to `inbox write`; when it names a plan the epic `status.json` positively reads as
  `running`, the write is refused (`undeliverable_to_running_plan`) rather than silently queued. Not a
  mid-run delivery channel — the flag is a plan id, never reaches the write path. `RUNNING_STATUS`
  moved to `_orchestrator_inbox` and imported back into `orchestrator.py` (single source, avoiding the
  source-of-truth drift this surface exists to catch). **Verified:** 4 end-to-end tests (running →
  refused + not queued; non-running → queued; untargeted → unaffected; malformed id → rejected). The
  `--help` write-boundary test's `--target` substring guard tightened to `--target ` (its own `--file `
  convention) so it still forbids a bare output-target arg while admitting the identifier flag. Docs:
  inbox-envelope.md § Write-side deliverability + orchestrator SKILL.md canonical invocation.
- **D5 — cap the round loop on convergence, not budget (commit `0c69f8b`).** Doc-only change to the
  self-review workflow: added a "Round-loop termination" section defining a SELF-SEEDING round (all
  findings are doc-claim findings inside the delta scope — the prose this plan's own prior rounds
  authored, identified via D3's published scope), reporting it as such rather than as an ordinary
  non-clean round; prescribing resolution by DELETION not correction; and distinguishing a CONVERGED
  close (full-surface clean pass) from an OUT-OF-BUDGET close (warning deviation, doc-claim half
  non-converged). NOT a round-count reduction. Verification is a cold read (Step 6 sub-agent).

## Build gate

`git diff --name-only origin/main...HEAD -- '*.py'` verdict: **Python changed** (both bundles —
`_self_review_detectors.py`, `self_review.py`, `_orchestrator_inbox.py`, `orchestrator.py`, plus three
test files), so the full `./pw verify` gate ran.

**Result: SUCCESS.** `19241 passed, 14 skipped` (0 failed / 0 errors, in 10m59s); `=== verify: SUCCESS
===`. Coverage line: mypy(production) 395 files, ruff over `marketplace/bundles`/`test`/`.claude`, SPDX
headers, **plugin-doctor marketplace-wide** (so the workflow-doc / ext-point / SKILL.md / inbox-envelope
changes passed structural lint and `test_real_marketplace_quality_gate_has_zero_findings`), mypy(test)
717 files, and whole-tree module-tests. The 14 skips are environment guards (the strict-no-skip gate is
off by default). Per-commit quality gates were also clean throughout (mypy/ruff/SPDX).

## Findings

### Claim re-verification — BASELINE (pre-fix, at HEAD `4a1936e`)

⚠ **This section records the PRE-FIX BASELINE the deliverables then fixed — it is not a statement of
current state.** Each bullet re-verifies a plan claim against the clone at HEAD `4a1936e` (the branch
point, before any commit on this branch). "opens only", "currently always queues", "lacks the criterion"
describe the code AS IT WAS, and every one of these was subsequently fixed (see § Deliverables for the
fixing commits). Do not read these as unshipped defects.

- **D1 asymmetry — CONFIRMED.** `_detect_count_prose` (`_self_review_detectors.py:1040`) opens only
  `skill_dir / 'SKILL.md'`, while its sibling `_collect_skill_contract_sources` (`:276`) returns
  "SKILL.md plus every standards/*.md". A stale count in a `standards/*.md` doc is surfaced by no
  candidate list. Fix at the resolver: `_detect_count_prose` will iterate
  `_collect_skill_contract_sources`.
- **D2 two uncovered counted entries — CONFIRMED and authoritatively recorded.**
  `ext-point-self-review-surfacing.md:219-222` explicitly records `duplicate_claimable_keys` and
  `discard_without_report` as the two `in_total: true` keys with "No consuming check", with a
  "Recorded coverage gap" paragraph. `keep_markers` (also `in_total: true`) IS covered (Check 4,
  per the contract's Consumed-By table). So exactly two entries need checks. Direction per plan: ADD
  the two checks (16, 17); do not drop `in_total`.
- **D3 asserted-absence REFUTED — D3 changes shape (as the plan anticipated).** The scope token
  (`surface_scope`) and file-count token (`files_in_scope`) DO now exist — emitted unconditionally
  by the surfacer (`self_review.py:330-331`), documented in the workflow doc (`:122`), the SKILL.md,
  and the ext-point schema. So the surfacer already publishes scope + count. The residual gap: the
  operator-facing VERDICT (`display_detail` clean strings) and the workflow's absence claims do not
  carry them, and no invariant pins that a clean claim must. D3 becomes: pin the always-emitted
  invariant, carry scope into the workflow's clean-verdict contract, and require every absence claim
  (this run's own included) to state its scope + file count.
- **D4 — CONFIRMED structural.** The inbox (`_orchestrator_inbox.py`, `inbox-envelope.md`) is the
  epic's plan→epic OUTBOX, drained by the orchestrator between plans; "the plan never reads the
  ledger to make a decision." There is no plan-as-recipient channel, so a message intended for a
  running plan is architecturally undeliverable. `cmd_inbox_write` currently always queues. Minimal
  honest form (D4): make the write verb report undeliverable at write time when a message targets a
  currently-running plan, without building a delivery channel.
- **D5 — CONFIRMED pattern.** The self-review step re-fires per round on HEAD-advance (loop-back);
  the loop closes only on a full-surface clean pass. There is no criterion distinguishing *converged*
  from *out of budget*, and no self-seeding classification. D5 adds both to the workflow doc,
  coordinating with D3 (published scope makes a self-seeded round identifiable).

### Scope-bearing absence claims (D3 self-binding)

D3 binds this plan against itself: its own residual/absence claims must publish the scope searched and
the file count, from the first round. This run's absence claims, each with its scope:

- **"Exactly two `in_total` registry entries lacked a consuming check."** Searched scope: the
  `CANDIDATE_LISTS` registry in `_self_review_patterns.py` (1 file, 23 entries, 17 `in_total`)
  cross-referenced against the "Consumed By" table in `ext-point-self-review-surfacing.md` (1 file) and
  the Step-3 checks region of `pre-submission-self-review.md` (1 file). Result: `duplicate_claimable_keys`
  and `discard_without_report` — the two the ext-point itself already recorded — and no others
  (`keep_markers` is consumed by check 4).
- **"The scope token and file-count token already exist"** (D3 premise refutation). Searched scope:
  `self_review.py` and `pre-submission-self-review.md` (2 files). Result: `surface_scope` +
  `files_in_scope` present in both (self_review.py:330-331; workflow doc line 122), plus the SKILL.md
  and ext-point schema — the plan's asserted absence is refuted.
- **"No `fifteen` check-count reference remains outside the three reconciled docs."** Searched scope:
  `architecture`-equivalent content sweep via `Grep` for `fifteen` across `marketplace/bundles`
  (crawled tree). Result: after reconciliation, the only remaining `fifteen` matches are two unrelated
  literals — the number-word regex in `_self_review_patterns.py:167` and a number-word map in
  `_analyze_literal_count.py:195` — neither a check-count. Coverage note: this `Grep` sweep covers the
  `marketplace/bundles` tree only; `doc/`, `.claude/`, and `.github/` were not swept, so the claim is
  scoped to `marketplace/bundles`.

### Verification sub-agent (Step 6)

An independent `general-purpose` sub-agent verified each deliverable against `plan.md`'s literal
"Done when" text, confirmed the negative controls are real, swept beyond the diff, and did the D5 cold
read. Verdicts: **D1 PASS, D2 PASS, D3 PASS (code), D4 PASS, D5 PASS.** Details:

- **D2 population published:** the agent independently enumerated all 17 `in_total` keys and confirmed
  each is referenced in the Step-3 checks region — population = 17, magnitude unchanged by construction.
- **D3 asserted-absence refuted, coherently:** the agent confirmed `surface_scope`/`files_in_scope`
  pre-existed and only `scope_statement` is new, and that it is emitted unconditionally including on an
  empty surface.
- **D4 no delivery channel:** the agent read the full write path and confirmed `--target-plan` reaches
  ONLY the guard — never `compose_envelope` or `allocate_message_path` — so the write-boundary is intact.
- **D5 cold read — distinction HOLDS:** the agent read the termination criterion cold and reported that
  "converged" and "out of budget" are pinned to disjoint, machine-checkable close states (a full-surface
  clean pass vs. a warning-deviation close), so a later reader could NOT collapse them. This is the
  reading the plan's Verification section required.

**Findings and dispositions (per instance):**

1. **[FIXED] Stale echo-field enumeration** — `pre-submission-self-review.md:122` (an untouched line)
   listed the surfacer's scope-echo fields (`surface_scope`, `since_ref`, `files_in_scope`) but omitted
   `scope_statement`, which D3 added and the same doc's new absence-claim section depends on — an
   incomplete-enumeration defect of exactly the beyond-diff shape D3 targets. **Fixed in commit `2e68683`:**
   line 122 now includes `scope_statement`. Self-verified by grepping every `files_in_scope` occurrence
   across the bundles — all scope-echo enumerations (SKILL.md schema + note, ext-point Post-Conditions +
   schema, the two new subsections) now include `scope_statement`; line 122 was the sole omission. A
   full sub-agent re-dispatch was not run for this mechanical one-field prose completion the agent had
   already isolated as the sole omission; instead a targeted re-verification ran the marketplace-wide
   plugin-doctor zero-findings test + the verdict test (93 passed), confirming the doc-linted file stays
   clean.
2. **[NOTED — closed by the PR body] "This run's own claims carry their scope" (D3 second half)** — the
   agent flagged that this clause is verifiable only against the PR body, which is outside the diff. It
   is closed by: (a) the § "Scope-bearing absence claims" section above, and (b) the PR body, which
   states the searched scope + file count for each of its absence claims (§ Step 7).

No undeclared collateral change; the `RUNNING_STATUS` move is the declared D4 shared-token relocation.

### CI / PR review

**CI:** `verify / conclusion` and `verify / verify` both concluded **success** on head `2e68683`
(`verify / gate`, `review / review`, `dependency-review`, `generate-check` all green; `Sourcery review`
and `auto-merge` checks skipped). The CodeRabbit-fix commit `e08f23a` and this final report commit each
re-trigger `verify`; the merge gate reads the actual required-context state on the final head before
arming.

**PR review — CodeRabbit posted 6 actionable findings, all dispositioned (fixes in `e08f23a`):**

| # | Finding | Disposition |
|---|---|---|
| 1 | D1 left SKILL.md-only wording in check 11 + the `count_prose` schema placeholder | **FIXED** — both now name the contract sources (`SKILL.md` + `standards/*.md`) |
| 2 | D2 coverage test matched a key anywhere in the Step-3 region | **FIXED** — narrowed to the numbered-check block + a new negative control (counted key in non-check prose → flagged) |
| 3 | D5 delta scope proves changed-since, not authorship | **FIXED** — caveat added: confirm the flagged prose is this plan's own prior-round correction, not an absorbed base merge |
| 4 | D5 self-seeding / out-of-budget not wired into Step 4 | **FIXED** — recorded via the existing `failed` outcome + `manage-logging decision --level WARNING`; no new `mark-step-done` outcome |
| 5 | D3 has no executable finding-rationale validator | **ACCEPTED AS GUIDANCE** — surfacer half enforced+tested; the rationale rule is workflow guidance like all 17 cognitive checks. CodeRabbit accepted and recorded the boundary as a learning |
| 6 | Report auditability + baseline labeling | **FIXED (this report commit)** — baseline section relabelled, `commit below` given its SHA (`2e68683`), Step 7/8/9 filled |

CodeRabbit re-verified the fixes on the current head and confirmed D1/D2/D3/D4/D5 addressed; its only
open item was the report finalization (this commit). Its fuller incremental re-review of `e08f23a` then
hit the weekly rate limit (~42 min). All three comment surfaces (issue comments, review summaries,
inline threads) were read.

## Reviewer participation

Expected reviewer population derived from the `author_login` of each
`marketplace/bundles/plan-marshall/skills/automatic-review/standards/{bot_kind}.md` registry doc
(`coderabbit.md`, `pr-agent.md`, `sourcery.md`; cross-named by `.github/workflows/pr-agent.yml`):

| Reviewer (`author_login`) | Verdict | Body evidence / reason |
|---|---|---|
| `cuioss-review-bot` | `reviewed` | Posted its "PR Reviewer Guide" over the diff — *"PR contains tests, No security concerns identified, No major issues detected"* (issue-comment surface). |
| `coderabbitai` | `reviewed` | Published a full review with 6 actionable findings (review-summary + inline-thread surfaces), then re-verified the fixes on the current head and confirmed D1–D5 addressed. (Its incremental re-review of the fix commit is rate-limited ~42 min, but its substantive review is complete and its findings dispositioned.) |
| `sourcery-ai` | `rate-limited` | Published only a quota notice in place of a review — *"reached your weekly rate limit of 500000 diff characters"* (review-summary surface). Did not review this diff. |

**Coverage: 2 of 3.** Shortfall disclosure (§ Step 8 condition 4): `sourcery-ai` is rate-limited on a
weekly quota and did not review; the merge proceeds on the 2 reviewers that did (`cuioss-review-bot` +
`coderabbitai`). This is disclosed here and in the operator hand-off — a routine external quota, not a
gate.

## Cost

- **Tokens:** not available to the agent in this session — the Claude Code cloud harness does not
  surface a token counter to the running agent.
- **Wall-clock:** from the initial branch push through auto-merge arming, roughly 1–1.5 hours (source:
  PR/commit timestamps — PR #1189 created 18:21Z, arming ~19:1xZ), dominated by full `./pw verify` CI
  passes (~11 min each) and two automated-review cycles.
- **Population:** this single Claude Code cloud session's usage as the harness counts it. ⛔ NOT
  comparable to a plan-marshall `metrics.toon` total — that counts the orchestrator-plus-agent dispatch
  tree under plan-marshall's per-task billing boundary, which a single interactive cloud session does
  not share. No comparable figure is available, so none is presented.

## Contract check (Step 9)

Re-read the `cloud-plan-lane` skill; per-step verdict:

| Step | Verdict |
|---|---|
| 1 Skills loaded | ✅ Named in § Skills loaded (read via bundle paths). |
| 2 Branch | ✅ Kept the harness-assigned `claude/self-review-surfacing-integrity-jcwvqa`; published to `origin` before any work. |
| 3 Plan directory | ✅ `…/100-self-review-surfacing-integrity/plan.md` exists and opens with the first-instruction block (present, unmodified). |
| 4 Implement | ✅ Deliverables addressed in coherent commits; every commit carries the `Co-Authored-By: Claude` trailer. |
| 4 Per-commit gate | ✅ Every commit touching `*.py` was preceded by a clean `./pw quality-gate` (ruff `All checks passed!`, mypy `Success`, SPDX passed). |
| 4 Pushed | ✅ `git push` after every commit; no unpushed commit remained. |
| 5 Build gate | ✅ Python changed → full `./pw verify` ran → SUCCESS (19241 passed, 0 failed). |
| 6 Verification sub-agent | ✅ Dispatched; D1–D5 PASS + D5 cold read; its one finding fixed (`2e68683`). |
| 7 PR cycle | ✅ PR #1189; all three comment surfaces read; every CodeRabbit finding dispositioned (fixed, or accepted-as-guidance with reason). |
| 8 Merge gate | Conditions 1–3 met (required contexts green, comments handled, report finalized as the last pre-merge commit); coverage shortfall (2-of-3) disclosed; auto-merge armed SQUASH as the final action after this commit's verify concludes. Landing delegated to the merge queue — a cloud session cannot block-until-landed (§ Step 8 arm-and-hand-off). |
| 8 Bridge | ✅ No status/bookkeeping write landed under `doc/plans/` outside this plan's own directory. |
| 9 This check | ✅ (this section). |
| 9 What have we learned | See below. |

GitHub access path: the **GitHub MCP server** (cloud path). Branch form: **harness-assigned** `claude/*`.
No `/sync-plugin-cache` owed (a cloud run never performs or owes it).

## What have we learned (Step 9)

The `cloud-plan-lane` contract held end-to-end. One evidence-backed observation is worth proposing to
the operator; everything else is recorded as "no change".

**Proposed contract refinement (operator decision):** for the SAME value change (D1's
SKILL.md → contract-source widening), the Step 6 pre-PR verification sub-agent's beyond-diff sweep and
the automated PR reviewer (CodeRabbit) each caught DIFFERENT stale-prose sites, and neither caught all.
The sub-agent found the echo-field enumeration at `pre-submission-self-review.md:122`; CodeRabbit found
check 11's wording and the `count_prose` schema placeholder — sites the sub-agent's phrase-oriented sweep
missed. **Evidence from THIS run:** a single value change had ≥3 stale-prose consumers of DIFFERENT KINDS
(an echo enumeration, a check description, a schema placeholder), and no single reviewer found them all.
The candidate refinement to `cloud-plan-lane` § Step 6 is to have the beyond-diff-sweep instruction
enumerate a change's consumers **by kind** — prose restatement, schema placeholder, worked example,
cross-doc reference — rather than sweeping for a single phrasing, so a value change's restatements are
found by construction rather than by luck. Presented as a proposal; if the operator accepts, it ships as
a **separate `chore/` PR** touching only the skill, never folded into this plan's PR.

Everything else: **no change proposed** — the branch/PR/review/merge cycle, the conditional build gate,
the report contract, and the merge-gate disclosure rule all worked as written on this run.

## Residue

- **Landing:** auto-merge armed on PR #1189 (SQUASH); the merge queue lands it. The squash SHA and the
  `state: MERGED` confirmation are read from the PR merge event by the orchestrator's collect step — a
  cloud session cannot block-until-landed (§ Step 8 arm-and-hand-off), so the landing is delegated, not
  a partial outcome.
- **`sourcery-ai` review:** did not run (weekly rate limit); disclosed as the 2-of-3 coverage shortfall.
  No action owed — a routine external quota.
- **Contract-change proposal:** the § "What have we learned" beyond-diff-sweep-by-consumer-kind proposal
  awaits an operator decision; if accepted it ships as a separate `chore/` PR, not from this branch.
