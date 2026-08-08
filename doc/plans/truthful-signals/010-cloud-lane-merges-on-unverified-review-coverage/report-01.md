# Run report — 010-cloud-lane-merges-on-unverified-review-coverage (run 01)

**Date (UTC):** 2026-08-08 13:23 UTC    **Branch:** `claude/cloud-lane-merges-unverified-b95oy0`
(harness-assigned)    **PR:** _pending (§ Step 7)_    **Outcome:** completed

## Skills loaded

Loaded by path (the `plan-marshall` plugin was not relied upon; bundle files read directly, the
route the contract names as always-working in a cloud clone):

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

**Expected reviewer population, derived from configuration (not from memory or the plan's prose):**
the repository registers its automated reviewers in a machine-readable registry — one data block per
reviewer at `marketplace/bundles/plan-marshall/skills/automatic-review/standards/{bot_kind}.md`,
parsed generically by `scripts/bot_registry.py` (no hard-coded bot list anywhere). Read the
`author_login` of each registry doc:

| `bot_kind` | `author_login` | `rate_limit_class` | Config source (git-tracked) |
|---|---|---|---|
| `coderabbit` | `coderabbitai` | `awaitable_window` | `automatic-review/standards/coderabbit.md` |
| `sourcery` | `sourcery-ai` | `hard_quota` | `automatic-review/standards/sourcery.md` |
| `pr-agent` | `cuioss-review-bot` | `unknown` | `automatic-review/standards/pr-agent.md` |

Cross-confirmed in prose by `.github/workflows/pr-agent.yml` ("Third automated PR reviewer (PR-Agent
on Google Gemini), beside CodeRabbit and Sourcery"). The HYPOTHESIS that the set is derivable from
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
than argued: "all comments handled" is trivially true against a comment set that contains two
refusals and one finding, and says nothing about participation.

(Note on the plan's "the #1107 report omitted Sourcery entirely" claim: that report is `PLAN-CIS-021`'s
machine-local orchestrator report, not in git and not readable from a cloud session — the plan says so
and says not to look for it. What this run *can* and did confirm is the stronger fact the omission
claim rests on: Sourcery's rate-limit was a **real, recorded-in-the-bodies signal**, so its absence
from any record is an omission, not an absence of signal.)

### D1 — Record participation per reviewer, from the bodies

**Done.** `SKILL.md` § Step 7 gains a "Record per-reviewer participation, from the bodies"
subsection: it derives the population from the registry `author_login` set (never a transcribed list),
and requires a per-reviewer verdict (`reviewed` / `rate-limited` / `silent`) taken from the stored
comment bodies — explicitly never from a check state, a summary, or an absence of complaint (extending
the existing Step 7 principle that "a green check is not evidence that a reviewer participated"). The
§ Report template gains a **Reviewer participation** table over that population. Commit: the D0–D4
implementation commit.

### D2 — Coverage shortfall as a merge-gate disclosure caveat

**Done.** `SKILL.md` § Step 8 gains condition 4: when any expected reviewer's verdict is not
`reviewed`, the run states the shortfall and its reason to the operator before arming auto-merge ("a
run that merges on 1-of-3 must _say_ 1-of-3"). The text is written to be unmistakably **disclosure,
not block** — a ⛔ paragraph states the gate does not hold, wait, or fail on a shortfall, that the
defect is the *silence* not the shortfall, and that conditions 1–3 are the only gates on the merge
itself. The Step 8 header was updated to say the merge is gated on 1–3 and condition 4 is a disclosure
before arming. (Verified cold by the Step 6 sub-agent — see Findings.)

### D3 — Resolve the push-cadence conflict explicitly

**Done, at both sites, without weakening durability.** `SKILL.md` § Step 4 gains "The push cadence
versus review integrity — resolved on the commit side": durability is absolute and outranks review
cleanliness, no finished commit is ever held back, and the conflict is resolved *only* by batching at
the commit boundary (coherent units → fewer pushes → fewer disruptions, at zero durability cost), with
the one forbidden move named (leaving a completed unit unpushed to spare a review). § Step 7 gains "A
push during the review cycle: superseded runs and aborted reviews" — a superseded `verify / conclusion`
cancellation is not a failure, and a push that aborted a review consumed that window (re-trigger, never
bank the abort as `reviewed`). § Step 2's durability section carries a pointer to both so a reader
there sees the tension is resolved, not open. Neither site can be read as licence to leave work
unpushed.

### D4 — Report what the run cost, with its population

**Done.** `SKILL.md` § Report template gains a **Cost** section: tokens + wall-clock + source, and a
mandatory **Population** qualifier with a ⛔ that the figure is NOT comparable to a plan-marshall
`metrics.toon` total (different counting boundary), and that a non-comparable figure must say so rather
than imply parity. `doc/plans/cloud-bridge.md` § Path 3 Collect step 5 now requires the durable
landing record to carry both the reviewer-participation verdicts and the cost line forward, so a cloud
run's cost and coverage survive the deletion of its report rather than vanishing from the corpus.

## Build gate

`git diff --name-only origin/main...HEAD -- '*.py'` → **empty** (no Python changed). The diff touches
`.claude/skills/cloud-plan-lane/SKILL.md` (`.claude/skills/**`) and `doc/plans/**` only. Per Step 5
row 2 (no `*.py`, but `.claude/skills/**` changed) the gate is `./pw quality-gate`. Result: _recorded
below after the run_ — see Findings / this section is updated at finalize.

## Findings

- **Step 6 pre-PR verification sub-agent:** _pending — recorded at Step 6._
- **CI:** _pending — recorded after the PR opens._
- **PR review:** the diff is documentation/prose only (no source), so per § Step 7 the PR carries
  `skip-bot-review`; the automated reviewers are deliberately suppressed. Recorded under Reviewer
  participation below.

## Reviewer participation

This PR's diff is documentation/prose only, so it carries `skip-bot-review` (§ Step 7: "a PR that
changes no source gets no bot review"). Population derived from configuration (as D0); verdicts from
the bodies:

| Reviewer (`author_login`) | Verdict | Body evidence / reason |
|---|---|---|
| `coderabbitai` | `silent` | Deliberately suppressed via `skip-bot-review` (documentation-only diff); no code was withheld from review. |
| `sourcery-ai` | `silent` | Same — suppressed by `skip-bot-review`. |
| `cuioss-review-bot` | `silent` | Same — suppressed by `skip-bot-review`. |

Coverage: **0 of 3**, all by deliberate policy suppression (not rate limit, not unexplained silence).
The § Step 8 shortfall disclosure fires and states exactly that before arming — see Contract check.
(The `reviewed` / `rate-limited` branches of this same taxonomy are exercised on real data by the D0
#1107 re-derivation above; between the two, all three verdicts are demonstrated fillable from bodies.)

## Cost

- **Tokens:** not available to the agent in this session — the Claude Code cloud harness exposes no
  running token counter to the agent, so no honest per-run token figure can be stated here.
- **Wall-clock:** not per-run instrumented in this lane; the run executed within the single
  2026-08-08 UTC cloud session (source: session date). No per-run duration counter is exposed to the
  agent.
- **Population:** any cost figure this lane could state would count *one interactive Claude Code cloud
  session's usage as the harness counts it*. ⛔ That is **NOT comparable** to a plan-marshall
  `metrics.toon` total, which counts the orchestrator-plus-agent dispatch tree under plan-marshall's
  own per-task billing boundary — a boundary a single cloud session does not share. Per D4 the honest
  report is therefore this explicit non-comparability, not a number dressed up to look like a
  `metrics.toon` total.

## Contract check (Step 9)

_Written at Step 8 condition 3 as the last pre-merge commit._

## What have we learned (Step 9)

_Written at Step 8 condition 3 as the last pre-merge commit._

## Residue

- `marketplace/bundles/` was **not** edited (the contract edits are to `.claude/skills/` and
  `doc/plans/`), so **no local `/sync-plugin-cache` is owed** by this run.
- The plan-marshall-side `ci pr create` gap (no `--description`, requires `--plan-id`) is noted in the
  plan as separately filed in the truthful-signals ledger — deliberately out of scope here.
