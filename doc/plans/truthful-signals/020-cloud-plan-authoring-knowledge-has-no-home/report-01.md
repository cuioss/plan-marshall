# Run report — 020-cloud-plan-authoring-knowledge-has-no-home (run 01)

**Date (UTC):** 2026-08-08    **Branch:** `claude/cloud-plan-authoring-knowledge-cd2azw`
(harness-assigned)    **PR:** [#1117](https://github.com/cuioss/plan-marshall/pull/1117)
**Outcome:** completed

## Skills loaded

Loaded by path (the `plan-marshall` plugin was not relied upon; bundle files were read directly, the
route the contract names as always-working in a cloud clone):

- `cloud-plan-lane` (the governing contract) — loaded first, before reading the plan.
- `plan-marshall:ref-code-quality` (always) —
  `marketplace/bundles/plan-marshall/skills/ref-code-quality/SKILL.md`.
- `pm-plugin-development:plugin-script-architecture` (always) —
  `marketplace/bundles/pm-plugin-development/skills/plugin-script-architecture/SKILL.md`.
- `pm-plugin-development:plugin-architecture` (SKILL.md / bundle structure — the surface is a new
  `SKILL.md`; its `references/frontmatter-standards.md` was read to settle the `mode`/`allowed-tools`
  question).

The surface is prose/markdown only (a new skill plus two doc pointers — no production code, no Python,
no `.adoc`, no security-relevant change), so `persona-implementer`, `python-core`, `pytest-testing`,
`ref-asciidoc`, and `persona-security-expert` were deliberately not loaded. No skill was unobtainable
by either route.

## Deliverables

### D0 — GATE: establish the knowledge is unhoused; bound the skill against duplication

**Done.** The new skill's § Boundary carries two verbatim lists (the D0 done-when).

**OWNED-ELSEWHERE** enumerates what each of the four candidate files already owns, each entry naming
its owning file: naming / prefix rules, derive-from-spec order, carry-across set, do-not-delete-spec,
and reach-`origin/main` → `doc/plans/cloud-bridge.md` § Path 1; the plan shape, the first-instruction
block, the claim-label mechanics, and the out-of-scope section's generic reason →
`doc/plans/_template/plan.md`; the whole execution contract, the run-side count re-derivation rule, and
the run-side self-approval prohibition → `.claude/skills/cloud-plan-lane/SKILL.md`; the tree layout and
the status-is-the-filesystem model → `doc/plans/README.md` and `cloud-bridge.md` § Status vocabulary.

**REMAINDER** is the seven authoring-judgement rules the skill owns. **The subtraction is not thin:**
four of the seven (self-sufficiency, no-operator deliverable design, stop-condition deliverables,
cold-read verification) are owned by no other file; the remaining three (evidence-in-the-clone,
counts-as-leads, out-of-scope-names-why) point to their template/lane owner and add only a
cloud-specific increment. **The ⛔ STOP condition did not fire** — this is not a pointer-shaped skill.

**Re-derived count (claim-label check).** The plan's scoping premise — an asserted absence — was
re-derived, not trusted: `.claude/skills/` held **14 skills** before this run (`audit-archived-plan-
retrospectives`, `cloud-plan-lane`, `sync-plugin-cache`, and eleven `finalize-step-*` / `recipe-*`
skills), and **none covered cloud-plan authoring** (`cloud-plan-lane` is execution; `recipe-plan-review`
reviews a landed plan). The asserted absence holds; the count now reads 15 including the new skill.

### D1 — `.claude/skills/author-cloud-plan/SKILL.md`, user-invocable, carrying the judgement

**Done.** Commit `b2221ef`. Frontmatter matches the sibling project-local skills — `name`,
`description`, `user-invocable: true`, `mode: workflow`, `allowed-tools` (the tool list of the closest
sibling, `cloud-plan-lane`). Seven rules, each carrying its grounding (the *why*, drawn from the two
cloud plans run so far), not merely the rule:

1. **Self-sufficiency** — restate what the run needs; `.plan/` is invisible; name a machine-local path
   only to say "do not look". Grounding: plan `010`'s Notes restated its machine-local landing record
   by hand.
2. **No operator** — no deliverable may need a mid-run decision; record a proposal, never decide; never
   self-approve a contract change. Grounding: plan `010`'s run recorded three proposals rather than
   shipping them.
3. **Stop-condition deliverables** — make a derivable premise the gating deliverable and HALT rather
   than fall back to hand-maintenance. Grounding: plan `010`'s D0 stop-condition.
4. **Cold-read verification** — verify text-that-drives-a-reader by an independent cold read reporting
   which reading it took. Grounding: plan `010`'s D2 cold read returned DISCLOSE.
5. **Evidence lives in the clone** — the cloud increment on the template's claim-label mechanics: the
   artifact must be git-reachable, and an asserted absence is the highest-risk claim in a cloud plan.
6. **A count is a lead** — the authoring counterpart to the lane's run-side re-derivation rule.
7. **Out-of-scope names why** — the cloud increment on the template's out-of-scope section: with no
   operator watching, the written boundary is the only drift-stopper.

### D2 — Wire it in at the two points where an author actually stands

**Done.** Commit `b2221ef`. `doc/plans/cloud-bridge.md` § Path 1 gains a pointer paragraph before the
numbered steps; `doc/plans/README.md` § "The rules" gains a paragraph distinguishing the run contract
(`cloud-plan-lane`) from the authoring skill (`author-cloud-plan`). **Pointers only** — each names the
topics the skill covers to describe it, and neither copies a rule's substance. The anti-duplication
property (no OWNED-ELSEWHERE entry restated inside the skill) was confirmed by the pre-PR sub-agent's
cold read (§ Findings).

### D3 — Apply the skill's own criterion to its own footprint

**Done.** Per-rule table: each of the seven rules read against plan `010` (from history at
`86c5b7532`) and **this** plan (`020`), reporting which plan each rule *catches* — i.e. contains the
situation the rule governs (whether the plan handled it well, or the rule would flag a gap):

| # | Rule | Catches in `010` | Catches in `020` |
|---|---|---|---|
| 1 | Self-sufficiency | ✔ Notes restate the machine-local landing record: "NOT visible from a cloud session … do not go looking for it" | ✔ Notes: "Do not go looking for the orchestrator spec or the landing records … Everything needed is in this file" |
| 2 | No operator | ✔ D2 authored as disclosure-not-decision; run recorded 3 proposals rather than deciding | ✔ Out-of-scope excludes the operator decision ("three open contract proposals are a separate operator decision … not touched here"); no deliverable needs a decision |
| 3 | Stop-condition deliverables | ✔ D0: "if the population cannot be derived from configuration, say so and **stop**" | ✔ D0 GATE: "⛔ STOP CONDITION — this deliverable may end the plan … if the remainder is thin, report that and stop" |
| 4 | Cold-read verification | ✔ D2 Verification: sub-agent reads the merge-gate text cold, must say DISCLOSE not BLOCK | ✔ **Flags a real gap** — `020`'s primary deliverable (the skill) is a text-that-drives-a-reader, yet its Verification specified D3 (criterion coverage) and no cold read of the skill's own rules. Mitigated this run by instructing the Step 6 sub-agent to cold-read the skill |
| 5 | Evidence lives in the clone / absence is higher-risk | ✔ "lane persists no metrics" is an OBSERVED asserted absence with a git-visible artifact (enumerated template sections) | ✔ "`.claude/skills/` holds 14 skills and none covers cloud-plan authoring \| OBSERVED (asserted absence) \| directory listing … re-derive it" |
| 6 | A count is a lead | ✔ "Every count this plan states is re-derived at the moment of the claim … `1 of 3`, the population, the section enumeration are all leads" | ✔ "enumerated … — **re-derive it, do not trust this count**" |
| 7 | Out-of-scope names why | ✔ Each of four out-of-scope bullets carries its reason (e.g. blocking on bot participation → "a rate limit is not a defect and must not strand a landing") | ✔ Each of three out-of-scope bullets carries its reason (e.g. not merging into `cloud-plan-lane` → "would make every cloud run load guidance it can never use") |

**Every rule catches a real situation in both plans** — so none is unnecessary or wrongly worded, and
no rule was dropped or reworded. The strongest result is rule 4 catching a genuine gap in the very
plan that authored it (the self-referential blind spot D3 exists to surface): `020` should have
specified a cold read of its own skill deliverable, and did not; the run supplied it via the Step 6
sub-agent.

## Build gate

`git diff --name-only origin/main...HEAD` → `.claude/skills/author-cloud-plan/SKILL.md`,
`doc/plans/README.md`, `doc/plans/cloud-bridge.md`, and the moved `…/020-…/plan.md`. **No `*.py`.** Per
Step 5 row 2 (no `*.py`, but `.claude/skills/**` changed) the gate is `./pw quality-gate` →
**`status: pass`, `total_issues: 0`** across 31 plugin-doctor rules (incl. `analyze_historical_prose_in_skills`,
`broken-relative-link`, `analyze_skill_mode`, `analyze_lane_frontmatter`, `analyze_allowed_tools_drift`,
all 0); mypy "no issues found in 381 source files"; ruff "All checks passed". On CI, the docs-and-skill
path is confirmed from the check runs: `verify / verify` → **skipped** (footprint gate),
`verify / conclusion` → **success** (the required check), `verify / gate` → success,
`dependency-review` → success.

**Lockfile hazard handled (recurrence of plan `010`'s finding #2).** The session Python is 3.11.15;
the project requires `>=3.12`. `./pw quality-gate` bootstrapped and rewrote `uv.lock` (a `M uv.lock` in
the tree). It was reverted (`git checkout HEAD -- uv.lock`) and the deliverable paths were staged
**explicitly** rather than via `git add -A`, so `uv.lock` never entered a commit. The net branch diff
contains no `uv.lock`.

## Findings

Recorded per instance.

- **Step 6 verification sub-agent — CLEAN, no gaps.** It verified D0 (both lists present, verbatim;
  remainder substantial; STOP does not fire), D1 (frontmatter matches the sibling; all seven rules
  grounded), D2 (both pointers; no rule copied), the KEY anti-duplication check (no OWNED-ELSEWHERE
  entry restated), a cold read of the skill's boundary framing (unambiguous; it took the intended
  reading), and out-of-scope (`cloud-plan-lane` untouched; nothing beyond the expected surface).
  Disposition: accepted; nothing to fix.
- **Step 6 sub-agent — one non-blocking observation (accepted).** It flagged rule 7's cloud increment
  as the closest of the three overlap rules to the template's generic out-of-scope reason, judging it a
  pointer-with-increment (acceptable) because it attributes the section and generic reason to the
  template and adds a mechanism the template does not carry (no-operator → sole drift-stopper), but
  noting it is the entry a future edit is most likely to let slip into duplication. Disposition:
  accepted as-worded — the increment (no-operator) is genuinely absent from `_template/plan.md`; the
  skill already attributes ownership. Recorded here as a standing caution, no change made.
- **CI — green on the required check.** `verify / conclusion` → success; no CI failure. Disposition:
  none needed.
- **Lockfile churn from the build bootstrap** — see § Build gate. Disposition: fixed in-run (reverted;
  explicit staging); it is a recurrence of a hazard plan `010` already proposed a contract note for,
  which remains an operator-pending proposal (§ What have we learned).
- **PR review, `cuioss-review-bot` — `reviewed`, no findings.** Body: "PR Reviewer Guide 🔍 — No
  relevant tests · No security concerns identified · **No major issues detected**"
  (`#1117 issuecomment-5227053797`). A clean review artifact against the diff with zero actionable
  findings. Disposition: no action — nothing to fix, nothing "not actionable" to explain; a reply would
  be noise (frugal-comment rule).
- **PR review, `sourcery-ai` — `reviewed`, no findings.** Body: "Hey - I've reviewed your changes and
  they look great!" (`#1117 pullrequestreview-4889210569`, over commit `b2221ef`). A review artifact
  against the diff, zero findings. Disposition: no action (as above).
- **PR review, `coderabbitai` — did not review (suppressed by label).** Body: "Review skipped — Auto
  reviews are limited based on label configuration … Excluded labels: `skip-bot-review`"
  (`#1117 issuecomment-5227051586`). A skip notice, not a review. Disposition: recorded `silent`
  (reason: label); nothing to handle.
- **`skip-bot-review` did not suppress two of three bots — recurrence of plan `010`'s MCP-label race.**
  The label was applied via the create-draft → label → mark-ready sequence (the GitHub MCP
  `create_pull_request` has no label parameter, plan `010` finding #1). Only `coderabbitai` honored it;
  `sourcery-ai` and `cuioss-review-bot` had already started on the draft/open event before the label
  was read, and both posted a (harmless, no-findings) review. Disposition: **strengthens plan `010`'s
  still-open proposal** (a create-with-label path or documenting the race), not a new proposal; the two
  stray reviews were harmless on a no-source PR.

## Reviewer participation

Population derived from configuration (the `author_login` of each
`marketplace/bundles/plan-marshall/skills/automatic-review/standards/{bot_kind}.md` registry doc,
cross-named by `.github/workflows/pr-agent.yml`), never transcribed: `coderabbitai` (coderabbit.md),
`sourcery-ai` (sourcery.md), `cuioss-review-bot` (pr-agent.md).

Verdicts derived from this PR's stored comment bodies (§ Step 7), never from a check state:

| Reviewer (`author_login`) | Verdict | Body evidence / reason |
|---|---|---|
| `cuioss-review-bot` | `reviewed` | "PR Reviewer Guide 🔍 … **No major issues detected**" — a review artifact against the diff, zero findings. Reviewed despite `skip-bot-review` (draft/open race). |
| `sourcery-ai` | `reviewed` | "Hey - I've reviewed your changes and they look great!" — a review over the diff, zero findings. Reviewed despite `skip-bot-review` (draft/open race). |
| `coderabbitai` | `silent` | "Review skipped — Auto reviews are limited based on label configuration … Excluded labels: `skip-bot-review`" — honored the label, posted a skip notice, did not review. |

**Coverage: 2 of 3 reviewed.** The § Step 8 shortfall disclosure **fired** — one expected reviewer
(`coderabbitai`) is not `reviewed`. Disclosure stated to the operator: *"Review coverage 2 of 3 —
`sourcery-ai` and `cuioss-review-bot` reviewed (both no findings); `coderabbitai` silent, deliberately
suppressed via `skip-bot-review` because the diff is a prose skill plus doc pointers with no source. No
code was withheld from review; this is a disclosure, not a block, and the merge proceeds."* Both the
`reviewed` and `silent` branches of the taxonomy are demonstrated fillable from the bodies.

## Cost

- **Tokens:** not available to the agent in this session — the Claude Code cloud harness exposes no
  running token counter to the agent, so no honest per-run token figure can be stated here.
- **Wall-clock:** not per-run instrumented in this lane; the run executed within the single 2026-08-08
  UTC cloud session (source: session date). No per-run duration counter is exposed to the agent.
- **Population:** any figure this lane could state would count *one interactive Claude Code cloud
  session's usage as the harness counts it*. ⛔ That is **NOT comparable** to a plan-marshall
  `metrics.toon` total, which counts the orchestrator-plus-agent dispatch tree under plan-marshall's
  own per-task billing boundary — a boundary a single cloud session does not share. The honest report
  is therefore this explicit non-comparability, not a number dressed to look like a `metrics.toon`
  total.

## Contract check (Step 9)

GitHub access path used: **GitHub MCP server** (`mcp__github__*`). Branch form used:
**harness-assigned** (`claude/cloud-plan-authoring-knowledge-cd2azw`) — kept as-is per the contract.
The plan **did not** edit `marketplace/bundles/`, so **no local `/sync-plugin-cache` is owed** (it
added a project-local `.claude/skills/` skill, which is not part of the marketplace-bundle sync).

| Step | Verdict | Evidence |
|---|---|---|
| 1 Skills loaded | done | § Skills loaded. |
| 2 Branch on origin | done | Harness-assigned branch, pushed to `origin` as the first action (it was absent from the remote), kept current per-commit. |
| 3 Plan directory | done | `…/020-…/plan.md` exists and opens with the first-instruction block (present on arrival — no repair needed). |
| 4 Implement | done | Commits `c419f67` (plan move), `b2221ef` (D1+D2), + the report commit; all carry the `Co-Authored-By: Claude` trailer; D0–D3 addressed. |
| 4 Per-commit gate | done | The one commit touching a gated path (`b2221ef`, `.claude/skills/**`) was preceded by `./pw quality-gate` → `total_issues: 0`. The plan-move commit (`c419f67`) is a pure `git mv` (non-gated). |
| 4 Pushed | done | Every commit pushed; no unpushed commit remains at merge. |
| 5 Build gate | done | No `*.py`; `.claude/skills/**` → `./pw quality-gate` pass; CI docs-and-skill path confirmed. |
| 6 Verification sub-agent | done | Clean; one non-blocking observation accepted (§ Findings). |
| 7 PR cycle | done | PR #1117; every comment dispositioned (§ Findings, § Reviewer participation). |
| 8 Merge gate | armed | Conditions 1–3 held: required check `verify / conclusion` green; every comment handled (all no-findings reviews / a skip notice); report finalized here as the last pre-merge commit. Condition-4 disclosure fired (2 of 3). Auto-merge armed; landing read back post-commit and reported to the operator. **CLA caveat below.** |
| 8 Bridge | done | Nothing under `doc/plans/` outside this plan's own directory was changed except the two declared-deliverable doc pointers (`cloud-bridge.md`, `README.md`, in the plan's Expected surface) — not bookkeeping. The report carries the PR number and per-deliverable outcome. |
| 9 This check | done | This section. |
| 9 What have we learned | done | Below. |

**CLA caveat (merge readiness).** The commit author is `Claude <noreply@anthropic.com>`, so
`license/cla` reports `not_signed` / pending, and the PR's combined status is `pending` for that reason
alone (every merge-relevant check is green: `verify / conclusion` success, `verify / gate` success,
`dependency-review` success). The required merge check per `CLAUDE.md` is `verify / conclusion`, which
is **green**. Prior cloud-lane PRs (including #1112) landed under the same author identity, which
indicates `license/cla` is not a hard merge-queue gate here; if it is treated as one, the operator must
re-check/sign for the queue to admit. Auto-merge is armed so the queue lands the PR once its required
checks pass. Per the lane's "a claim is not an outcome" rule, the merge is read back after arming and
the true state reported to the operator — not asserted as MERGED from the arm command.

## What have we learned (Step 9)

Two observations, each backed by evidence **this run produced**. A contract change is never
self-approved and ships as a separate `chore/` PR only on operator approval; this autonomous cloud run
has no live operator, so both are **recorded for the operator, not shipped**.

1. **The `uv.lock` bootstrap hazard recurred, exactly as plan `010` predicted.** Evidence: session
   Python 3.11.15 < project `>=3.12`; `./pw quality-gate` rewrote `uv.lock`; caught and reverted; the
   deliverable paths were staged explicitly to keep it out of the commit. Plan `010` already proposed
   that Step 4/5 warn about lockfile churn and stage deliverable paths explicitly rather than
   `git add -A`. **This run is a second instance of that same hazard** — it strengthens `010`'s
   still-open proposal rather than adding a new one. The proposal remains operator-pending.
2. **The lane's own contract worked as written for a new-skill (non-`cloud-plan-lane`) surface.** No
   step was ambiguous or unachievable for this plan; the Step 5 row-2 docs-and-skill gate, the Step 6
   sub-agent, and the merge gate all applied cleanly to a `.claude/skills/**`-only change. **No new
   contract change is proposed from this run** — the one hazard it hit is already filed (above).

## Residue

- **No local `/sync-plugin-cache` owed** — `marketplace/bundles/` was not edited.
- The `uv.lock` bootstrap hazard (§ What have we learned #1) is a recurrence of plan `010`'s open
  proposal; it awaits the same operator decision.
- **The `author-cloud-plan` skill is now the home for cloud-plan authoring judgement.** A future author
  adding a rule should run D3's criterion (does it catch a real plan?) before adding it, and should
  cold-read any text-that-drives-a-reader deliverable — including the skill itself.
