# Run report — 010-cloud-lane-merges-on-unverified-review-coverage (run 01)

**Date (UTC):** 2026-08-08    **Branch:** `claude/cloud-lane-merges-unverified-b95oy0`
(harness-assigned)    **PR:** [#1112](https://github.com/cuioss/plan-marshall/pull/1112)
**Outcome:** completed (deliverables); merge armed — see § Merge gate for the CLA caveat

## Skills loaded

Loaded by path (the `plan-marshall` plugin was not relied upon; bundle files read directly, the route
the contract names as always-working in a cloud clone):

- `cloud-plan-lane` (the governing contract) — loaded first, before reading the plan.
- `plan-marshall:ref-code-quality` (always) — `marketplace/bundles/plan-marshall/skills/ref-code-quality/SKILL.md`.
- `pm-plugin-development:plugin-script-architecture` (always) —
  `marketplace/bundles/pm-plugin-development/skills/plugin-script-architecture/SKILL.md`.
- `pm-plugin-development:plugin-architecture` (SKILL.md / bundle structure — the surface is a SKILL.md
  contract).
- `plan-marshall:ref-workflow-architecture` (workflow docs — the surface is the lane workflow doc plus
  `cloud-bridge.md`).

No skill was unobtainable by either route. The surface is prose/markdown only (no production code, no
Python, no security-relevant change), so `persona-implementer`, `python-core`, `pytest-testing`,
`ref-asciidoc`, and `persona-security-expert` were deliberately not loaded.

## Deliverables

### D0 — Establish the reviewer population from configuration; prove the gate vacuous

**Done (evidence deliverable — no contract edit of its own; its result feeds D1/D2 and this report).**

**Expected reviewer population, derived from configuration (not from memory or the plan's prose):** the
repository registers its automated reviewers in a machine-readable registry — one data block per
reviewer at `marketplace/bundles/plan-marshall/skills/automatic-review/standards/{bot_kind}.md`, parsed
generically by `scripts/bot_registry.py` (no hard-coded bot list anywhere). Read the `author_login` of
each registry doc:

| `bot_kind` | `author_login` | `rate_limit_class` | Config source (git-tracked) |
|---|---|---|---|
| `coderabbit` | `coderabbitai` | `awaitable_window` | `automatic-review/standards/coderabbit.md` |
| `sourcery` | `sourcery-ai` | `hard_quota` | `automatic-review/standards/sourcery.md` |
| `pr-agent` | `cuioss-review-bot` | `unknown` | `automatic-review/standards/pr-agent.md` |

Cross-confirmed in prose by `.github/workflows/pr-agent.yml` ("Third automated PR reviewer (PR-Agent on
Google Gemini), beside CodeRabbit and Sourcery"). The HYPOTHESIS that the set is derivable from
configuration rather than a hand-maintained list is **CONFIRMED**: it is a generic, tested registry.
The competing hypothesis — that `.coderabbit.yaml` in *this* repo registers it — is **refuted**: no
such file exists here, and PR #1107's CodeRabbit notice names its config as
`Repository: cuioss/coderabbit/.coderabbit.yaml` (an org repo, not this one). So D0's ⛔ stop-condition
did **not** trigger, and the contract points the run at the registry rather than baking a list.

**Vacuity shown on a real, merged PR (#1107), re-derived from the stored comment bodies** — not a
summary, not a check state (fetched via the GitHub MCP `get_reviews` / `get_review_comments` /
`get_comments` surfaces):

| Reviewer | Verdict (from body) | Body evidence |
|---|---|---|
| `cuioss-review-bot` | `reviewed` | "PR Reviewer Guide 🔍 … **False Negative Bug** … `_identity_deduped` uses overly broad regex patterns" — a substantive finding against the diff. |
| `coderabbitai` | `rate-limited` | "## Review limit reached … we couldn't start this review. **Next review available in: 49 minutes**" — an awaitable-window refusal, not a review. |
| `sourcery-ai` | `rate-limited` | "you have reached your **weekly rate limit of 500000 diff characters**" — a hard-quota refusal, not a review. |

Inline review threads: `totalCount: 0`. Coverage was therefore **1 of 3 reviewed**. #1107 is
`merged: true` (`merged_at 2026-08-07T21:05:34Z`); the one substantive finding was handled (the
operator addressed it in `a3bcd60`), so the lane's "every comment handled" gate was satisfiable —
while two of three expected reviewers never reviewed the diff. That is the vacuity, exhibited rather
than argued.

(Note on the plan's "the #1107 report omitted Sourcery entirely" claim: that report is `PLAN-CIS-021`'s
machine-local orchestrator report, not in git and not readable from a cloud session — the plan says so
and says not to look for it. What this run *can* and did confirm is the stronger fact the omission
claim rests on: Sourcery's rate-limit was a **real, recorded-in-the-bodies signal**, so its absence
from any record is an omission, not an absence of signal.)

### D1 — Record participation per reviewer, from the bodies

**Done.** `SKILL.md` § Step 7 gains a "Record per-reviewer participation, from the bodies" subsection:
it derives the population from the registry `author_login` set (never a transcribed list), and requires
a per-reviewer verdict (`reviewed` / `rate-limited` / `silent`) taken from the stored comment bodies —
explicitly never from a check state, a summary, or an absence of complaint (extending the existing Step
7 principle that "a green check is not evidence that a reviewer participated"). The § Report template
gains a **Reviewer participation** table over that population. Commit `22d63c0`.

### D2 — Coverage shortfall as a merge-gate disclosure caveat

**Done.** `SKILL.md` § Step 8 gains condition 4: when any expected reviewer's verdict is not
`reviewed`, the run states the shortfall and its reason to the operator before arming auto-merge ("a
run that merges on 1-of-3 must _say_ 1-of-3"). The text is written to be unmistakably **disclosure, not
block** — a ⛔ paragraph states the gate does not hold, wait, or fail on a shortfall, that the defect is
the *silence* not the shortfall, and that conditions 1–3 are the only gates on the merge itself. The
Step 8 header was updated to say the merge is gated on 1–3 and condition 4 is a disclosure before
arming. The independent Step 6 sub-agent read the text cold and returned **DISCLOSE** (the plan's
required check; a "BLOCK" verdict would have meant the wording failed). Commit `22d63c0`.

### D3 — Resolve the push-cadence conflict explicitly

**Done, at both sites, without weakening durability.** `SKILL.md` § Step 4 gains "The push cadence
versus review integrity — resolved on the commit side": durability is absolute and outranks review
cleanliness, no finished commit is ever held back, and the conflict is resolved *only* by batching at
the commit boundary (coherent units → fewer pushes → fewer disruptions, at zero durability cost), with
the one forbidden move named (leaving a completed unit unpushed to spare a review). § Step 7 gains "A
push during the review cycle: superseded runs and aborted reviews" — a superseded `verify / conclusion`
cancellation is not a failure, and a push that aborted a review consumed that window (re-trigger, never
bank the abort as `reviewed`). § Step 2's durability section carries a pointer to both. Neither site can
be read as licence to leave work unpushed. Commit `22d63c0`. (This run itself applied the rule: the
D0–D4 work landed as a single coherent commit rather than a flurry, minimising pushes.)

### D4 — Report what the run cost, with its population

**Done.** `SKILL.md` § Report template gains a **Cost** section: tokens + wall-clock + source, and a
mandatory **Population** qualifier with a ⛔ that the figure is NOT comparable to a plan-marshall
`metrics.toon` total (different counting boundary), and that a non-comparable figure must say so rather
than imply parity. `doc/plans/cloud-bridge.md` § Path 3 Collect step 5 now requires the durable landing
record to carry both the reviewer-participation verdicts and the cost line forward, so a cloud run's
cost and coverage survive the deletion of its report. Commit `22d63c0`.

## Build gate

`git diff --name-only origin/main...HEAD -- '*.py'` → **empty** (no Python changed). The net diff
touches `.claude/skills/cloud-plan-lane/SKILL.md` (`.claude/skills/**`) and `doc/plans/**` only. Per
Step 5 row 2 (no `*.py`, but `.claude/skills/**` changed) the local gate is `./pw quality-gate` →
**`status: pass`, `total_issues: 0`** (31 plugin-doctor rules at 0 findings incl. `broken-relative-link`
and `analyze_historical_prose_in_skills`; mypy "no issues found in 381 source files"; ruff "All checks
passed"). On CI, the docs-only path is confirmed from the check runs: `verify / verify` → **skipped**
(footprint gate), `verify / conclusion` → **success** (the required check), `verify / gate` → success,
`dependency-review` → success.

## Findings

Recorded per instance.

- **Step 6 verification sub-agent — CLEAN, no gaps.** It verified D0–D4 and eight checks against
  `plan.md`; all passed. Its D2 cold-read returned **DISCLOSE** (not BLOCK). Its population
  re-derivation matched the three registry docs exactly. Its one stated limit — it has no GitHub access
  and so could not re-fetch #1107's live bodies — is covered independently: this run *did* re-derive
  #1107 from the bodies via the GitHub MCP (§ D0). Disposition: accepted; nothing to fix.
- **CI — green on the required check.** `verify / conclusion` success; no CI failure. Disposition: none
  needed.
- **PR review, `cuioss-review-bot` (pr-agent) — `reviewed`, no findings.** Body:
  "PR Reviewer Guide 🔍 … No relevant tests · No security concerns identified · **No major issues
  detected**" (issue-comment `[#1112 comment 5226329296]`). A clean review artifact against the diff
  with zero actionable findings. Disposition: no action — a no-findings review has nothing to fix and
  nothing "not actionable" to explain; a reply would be noise (frugal-comment rule).
- **PR review, `coderabbitai` — suppressed, did not review.** Body: "## Review skipped — Auto reviews
  are limited based on label configuration … skip-bot-review" (commit status `CodeRabbit: success —
  Review skipped: excluded by label configuration`). Not a review. Disposition: deliberate suppression;
  recorded `silent` (reason: label).
- **PR review, `sourcery-ai` — suppressed, did not review.** `Sourcery review` check → skipped; no
  comment posted. Disposition: deliberate suppression; recorded `silent` (reason: label).
- **`skip-bot-review` could not be applied atomically at creation — `cuioss-review-bot` reviewed
  anyway.** The contract (§ Step 7) says "apply the label at creation … applying it afterwards is too
  late." The cloud/MCP path cannot honour that literally: `mcp__github__create_pull_request` has **no
  label parameter**. The mitigation used — create as draft, apply the label, then mark ready — still let
  PR-Agent review, because *draft creation itself fires the `pull_request: opened` event* (run
  `…753`, started 13:32:54, before the label landed ~13:33:0x), and PR-Agent's job-level `if:` guard
  reads the label from that event payload, which lacked it. The `ready_for_review` run (`…820`) *did*
  skip. Net effect: one stray PR-Agent review on a docs-only PR. CodeRabbit and Sourcery were unaffected
  (they honoured the label). Disposition: **contract gap → proposed in § What have we learned**; no
  in-run fix (the review was harmless — no findings).
- **Stray `uv.lock` churn from the build bootstrap.** The Step 4/5 `./pw quality-gate` bootstrapped
  under **Python 3.11** (the session interpreter; the project requires `>=3.12`) and rewrote `uv.lock`
  (134 lines); `git add -A` swept it into the D0–D4 commit `22d63c0`. Caught at Step 5 (the diff showed
  a fifth file) and reverted to `origin/main` in commit `21a20d9`. The net branch diff no longer
  contains `uv.lock`. Disposition: fixed; **contract-hazard note proposed in § What have we learned**.

## Reviewer participation

Population derived from configuration (as D0); verdicts derived from this PR's stored comment bodies
(§ Step 7), never from a check state. (Note: this table was first drafted `0 of 3 suppressed` on the
assumption that `skip-bot-review` would silence all three; reading the bodies corrected it to `1 of 3`
— which is exactly the D1 principle working as intended.)

| Reviewer (`author_login`) | Verdict | Body evidence / reason |
|---|---|---|
| `cuioss-review-bot` | `reviewed` | "PR Reviewer Guide 🔍 … No major issues detected" — a review artifact against the diff, zero findings. Reviewed despite `skip-bot-review` (draft-open race, see Findings). |
| `coderabbitai` | `silent` | Deliberately suppressed via `skip-bot-review`; posted a "Review skipped — excluded by label" notice and did not review. |
| `sourcery-ai` | `silent` | Deliberately suppressed via `skip-bot-review`; `Sourcery review` check skipped, no comment. |

**Coverage: 1 of 3 reviewed.** The § Step 8 shortfall disclosure **fired** — two expected reviewers
are not `reviewed`. Disclosure stated to the operator: *"Review coverage 1 of 3 — cuioss-review-bot
reviewed (no findings); coderabbitai and sourcery-ai silent, deliberately suppressed via
skip-bot-review because the diff is documentation-only. No code was withheld from review; this is a
disclosure, not a block, and the merge proceeds."* (Both `reviewed` and — via the D0 #1107 exhibit —
`rate-limited` branches of the taxonomy are thereby demonstrated fillable from bodies.)

## Cost

- **Tokens:** not available to the agent in this session — the Claude Code cloud harness exposes no
  running token counter to the agent, so no honest per-run token figure can be stated here.
- **Wall-clock:** not per-run instrumented in this lane; the run executed within the single 2026-08-08
  UTC cloud session (source: session date). No per-run duration counter is exposed to the agent.
- **Population:** any cost figure this lane could state would count *one interactive Claude Code cloud
  session's usage as the harness counts it*. ⛔ That is **NOT comparable** to a plan-marshall
  `metrics.toon` total, which counts the orchestrator-plus-agent dispatch tree under plan-marshall's own
  per-task billing boundary — a boundary a single cloud session does not share. Per D4 the honest report
  is therefore this explicit non-comparability, not a number dressed up to look like a `metrics.toon`
  total.

## Contract check (Step 9)

GitHub access path used: **GitHub MCP server** (`mcp__github__*`). Branch form used: **harness-assigned**
(`claude/cloud-lane-merges-unverified-b95oy0`). The plan did **not** edit `marketplace/bundles/`, so
**no local `/sync-plugin-cache` is owed**.

| Step | Verdict | Evidence |
|---|---|---|
| 1 Skills loaded | done | Named in § Skills loaded. |
| 2 Branch on origin | done | Harness-assigned branch, present on `origin` (pushed at Step 2, kept current per-commit). |
| 3 Plan directory | done | `…/010-…/plan.md` exists and opens with the first-instruction block (present on arrival — no repair needed). |
| 4 Implement | done | Commits `47d584d`, `22d63c0`, `21a20d9` + the final report commit; all carry the `Co-Authored-By: Claude` trailer; D0–D4 addressed. |
| 4 Per-commit gate | done | The one commit touching a gated path (`22d63c0`, `.claude/skills/**`) was preceded by `./pw quality-gate` → `total_issues: 0`. Other commits touch only `doc/plans/**` or `uv.lock` (non-gated). |
| 4 Pushed | done | Every commit pushed; no unpushed commit remains. |
| 5 Build gate | done | No `*.py`; `.claude/skills/**` → `./pw quality-gate` pass; CI docs-only path confirmed. |
| 6 Verification sub-agent | done | Clean; D2 cold-read = DISCLOSE (§ Findings). |
| 7 PR cycle | done | PR #1112; every comment dispositioned (§ Findings). |
| 8 Merge gate | armed | Conditions 1–3 held (required check green; comments handled; report finalized here as the last pre-merge commit); condition 4 disclosure fired (1 of 3). Auto-merge armed; landing read back post-commit and reported to the operator. **CLA caveat below.** |
| 8 Bridge | done (with a wording note) | No run-status/bookkeeping was written outside this plan's directory. The one file changed outside the plan dir — `doc/plans/cloud-bridge.md` — is a **declared deliverable** (D4, in the plan's Expected surface), not bookkeeping. The Step-9 "Bridge" row's literal "nothing … outside this plan's own directory was changed" does not carve this out — flagged in § What have we learned. |
| 9 This check | done | This section. |
| 9 What have we learned | done | Below — three proposals, recorded not shipped. |

**CLA caveat (merge readiness).** The commit author is `Claude <noreply@anthropic.com>`, so
`license/cla` reports `pending — Contributor License Agreement is not signed yet`, and the combined
status is `pending` for that reason alone (every other status/check is green or a benign skip). The
required merge check per `CLAUDE.md` is `verify / conclusion`, which is **green**. Prior cloud-lane PRs
(#1105/#1108/#1109) landed under the same author identity, which indicates `license/cla` is not a hard
merge-queue gate here; but if it is treated as one, the operator must re-check/sign for the queue to
admit. Auto-merge is armed so the queue lands it once its required checks pass. Per the lane's
"a claim is not an outcome" rule, the merge is read back after arming and the true state reported —
not asserted as MERGED from the arm command.

## What have we learned (Step 9)

Three contract observations, each backed by evidence **this run produced**. Per § Step 9 a contract
change is never self-approved and ships as a **separate `chore/` PR** only on operator approval; this
autonomous cloud run has no live operator, so all three are **recorded here for the operator, not
shipped**.

1. **`skip-bot-review` cannot be applied at PR creation through the GitHub MCP, and the draft
   workaround does not fully suppress PR-Agent.** Evidence: `mcp__github__create_pull_request` has no
   label parameter; creating as draft then labelling then marking ready still let `cuioss-review-bot`
   review PR #1112, because draft creation fires `pull_request: opened` before the label lands and
   PR-Agent's guard reads the label from that payload. Step 7 currently says "apply the label at
   creation … applying it afterwards is too late," which is literally unachievable on the MCP path the
   contract itself mandates for cloud runs. **Proposed:** Step 7 should document the MCP reality — the
   create→label→ready sequence, and that a single stray PR-Agent review on the draft-open event is
   expected and harmless on a `skip-bot-review` PR (CodeRabbit and Sourcery still honour the label). A
   fuller fix (open the PR non-draft only after the label exists, or a create-with-label MCP verb) is a
   larger change to name, not silently adopt.

2. **The `./pw` build gate mutates `uv.lock` when the session Python is older than the project
   requirement, and `git add -A` will ship it.** Evidence: the session ran Python 3.11 (project requires
   `>=3.12`); `./pw quality-gate` rewrote `uv.lock` (134 lines), which `git add -A` captured into
   `22d63c0`; caught and reverted in `21a20d9`. **Proposed:** Step 4/5 should warn that a `./pw` run can
   leave lockfile churn and that commits should stage the deliverable paths explicitly (not blanket
   `git add -A`) — or check for and revert stray `uv.lock`/lockfile changes before committing.

3. **The Step-9 "Bridge" check wording forbids a change that a plan deliverable can legitimately
   require.** Evidence: D4's declared surface includes `doc/plans/cloud-bridge.md`, which is *under*
   `doc/plans/` but *outside* this plan's own directory; the Step-9 row asserts "Nothing under
   `doc/plans/` outside this plan's own directory was changed." The row's intent is "write no
   status/bookkeeping outside your plan dir," which this run honoured — but its literal wording collides
   with a deliverable edit to a shared lane doc. **Proposed:** reword the Bridge row to prohibit
   *status/bookkeeping* writes outside the plan directory, explicitly permitting declared-deliverable
   edits to shared lane docs (`cloud-bridge.md`, `README.md`).

## Residue

- **No local `/sync-plugin-cache` owed** — `marketplace/bundles/` was not edited.
- **Merge landing** is read back after arming and reported to the operator; if `license/cla` blocks the
  queue, the PR is armed-and-waiting rather than merged (see the CLA caveat), which is an honest partial,
  not a deliverable failure.
- The plan-marshall-side `ci pr create` gap (no `--description`, requires `--plan-id`) is noted in the
  plan as separately filed in the truthful-signals ledger — deliberately out of scope here.
- Three contract-improvement proposals (above) await operator review; none was shipped in this run.
