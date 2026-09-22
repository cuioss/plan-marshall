# Landing Analysis: PLAN-TRUTH-061 — The Cloud Lane Merges on Unverified Review Coverage

epic: truthful-signals
workstream: WS-01
pr: [#1112](https://github.com/cuioss/plan-marshall/pull/1112) — merged `86c5b7532`

> Landing record for one shipped plan. Executed in the **standalone cloud lane** from
> `doc/plans/truthful-signals/010-cloud-lane-merges-on-unverified-review-coverage/`.
> Every material claim below was re-verified first-party against `origin/main`, the merged diff, and
> the PR state — the run report is a lead, not a fact.
>
> ⛔ **The run's own last read said `merged: false`.** It armed auto-merge, polled several times,
> correctly refused to claim a landing it had not observed, and stopped. The queue landed it
> afterwards. **The run was right to stop and right not to claim** — this record is the collect step
> doing what the contract says it does.

## Deliverable Fidelity vs Spec

Corroborated against `git show --stat 86c5b7532` — 4 files, +411/−3.

| Deliverable (spec) | Verdict | Evidence |
|---|---|---|
| D0 — reviewer population from configuration + prove the gate vacuous | shipped-as-specified | Population derived from `automatic-review/standards/{bot_kind}.md` via `bot_registry.py`, cross-named by `.github/workflows/pr-agent.yml`: `coderabbitai`, `sourcery-ai`, `cuioss-review-bot`. Vacuity shown on merged #1107 from stored bodies (1 of 3). **The stop-condition did not fire** — the population IS derivable, so no hand-maintained list shipped. |
| D1 — per-reviewer participation from bodies | shipped-as-specified | `SKILL.md` Step 7 + report-template participation table. |
| D2 — shortfall as merge-gate disclosure | shipped-as-specified | Step 8 condition 4. ⭐ **The cold-read test passed**: the independent sub-agent read D2 blind and answered **DISCLOSE**, not BLOCK — the plan's own key verification, and the wording survived it. |
| D3 — resolve the push-cadence conflict | shipped-as-specified | Both sites (Step 4 + Step 7, Step 2 pointer). Resolution lives on **commit batching, never on delaying pushes** — durability rule not weakened, as the spec required. |
| D4 — run-cost line with population qualifier | shipped-modified | Template carries the line; `cloud-bridge.md` Collect step 5 carries it forward. ⛔ **The figure itself is unavailable** — see below. |

**One deliverable landed as an honest negative.** D4's cost line reports that **the cloud harness
exposes no token counter to the agent**, so no per-run figure can be stated, and that any figure it
could state would count *one interactive cloud session as the harness counts it* — **not comparable**
to a `metrics.toon` total, which counts the orchestrator-plus-agent dispatch tree under
plan-marshall's own per-task billing boundary. ⭐ **That is the correct outcome, not a shortfall**:
the plan required the line to carry its population or state the incomparability, and it stated the
incomparability rather than emitting a number dressed to look comparable.

⛔ **Consequence for the corpus, and it is worse than the gap I recorded at CIS-021's landing.** I
recorded there that the lane persists no metrics. This run establishes the stronger fact: **a cloud
run cannot self-report cost at all** — the data is not available to the agent. The corpus gap is
therefore **not closable by lane-side reporting**; it needs harness-side instrumentation or nothing.

## Routing and Merge Behavior

**Coverage: 1 of 3 — and the machinery this plan shipped is what reported it.**

| Reviewer | Verdict | Evidence |
|---|---|---|
| `cuioss-review-bot` | `reviewed` | "PR Reviewer Guide 🔍 … No major issues detected" — a real review artifact, zero findings. |
| `coderabbitai` | `silent` | Deliberately suppressed by `skip-bot-review`; posted a skip notice, did not review. |
| `sourcery-ai` | `silent` | Deliberately suppressed by `skip-bot-review`; check skipped, no comment. |

The Step 8 shortfall disclosure **fired and was stated before arming**, and the merge proceeded — a
disclosure, not a block, exactly as D2 specifies. No code was withheld from review (docs-only diff).

⭐⭐ **The run's participation table was first drafted `0 of 3 suppressed` — an assumption — and
reading the bodies corrected it to `1 of 3`.** The mechanism caught its own author's assumption on
its first use. That is the strongest evidence the deliverable works that this landing could have
produced, and it was produced by accident.

- CI: `verify / conclusion` success; `verify / verify` skipped (docs-only path confirmed from git
  evidence, not assumed). Merged via the queue as `86c5b7532`.
- `license/cla` pending throughout (see Follow-Ups).

## Findings the run surfaced

1. **`skip-bot-review` cannot be applied atomically at PR creation on the MCP path the contract
   mandates for cloud runs.** `mcp__github__create_pull_request` has no label parameter; the
   create-draft → label → ready workaround still let PR-Agent review, because **draft creation itself
   fires `pull_request: opened`** and PR-Agent's guard reads the label from that payload. Step 7's
   "apply the label at creation … applying it afterwards is too late" is **literally unachievable**
   on that path. ⭐ A contract instruction that cannot be followed by the runtime it governs.
2. **`./pw` mutates `uv.lock` when the session Python is older than the project requirement**, and
   `git add -A` ships it. The run bootstrapped under Python 3.11 against a `>=3.12` project, rewrote
   134 lines, swept them into the deliverable commit, **caught it at Step 5 and reverted**. The net
   diff is exactly the 4 intended files — verified here independently.
3. **The Step-9 "Bridge" row forbids a change a deliverable legitimately requires.** Its wording
   ("nothing under `doc/plans/` outside this plan's own directory") collides with D4's declared edit
   to the shared `cloud-bridge.md`. Intent is *no status/bookkeeping writes*; the literal text is
   wider than the intent.

All three are **recorded, not shipped** — Step 9 forbids self-approving a contract change, and an
autonomous run has no operator to approve one. ⭐ **That restraint is correct and worth preserving.**

## Reconciliation Actions

- [x] row `status` → `shipped`
- [x] row `pr` stamped — `1112`
- [x] row `landing` stamped — `landings/PLAN-TRUTH-061.md`
- [x] row `plan_marshall_plan_id` — deliberately empty; the cloud lane creates no plan-marshall plan
- [x] epic.md reconciled from status.json
- [x] cloud plan directory collected
- [x] resume_anchor updated

## Follow-Ups

1. **The three contract proposals need an operator decision.** Proposal 1 is the sharpest — the
   contract currently mandates something its own runtime cannot do.
2. **CLA is pending because the cloud run authored commits as `Claude <noreply@anthropic.com>`.** The
   project convention is a `Co-Authored-By:` **trailer**, not authorship. The merge was not blocked
   (`mergeable_state: unstable`, not `blocked`), so this is cosmetic *for now* — but it will keep
   recurring on every cloud run and it makes the CLA signal permanently red.
3. **The cost-corpus gap is now established as harness-side.** Any plan aiming to close it must
   target instrumentation, not the report template. Do not re-file this as a lane-doc fix.
4. **`ci pr create` plan-less gap** — separately recorded as an Open Defect lead; untouched here.


---

## ⛔ CORRECTION 2026-08-08 — the coverage figure in this record used the WRONG DENOMINATOR

This landing reports review coverage against the **enumerated roster** (`coderabbitai`,
`sourcery-ai`, `cuioss-review-bot`). That is not the quorum. Read first-party from
`.plan/marshal.json` (`plan.phase-6-finalize.steps.plan-marshall:automatic-review`):

    required_bots = 'pr-agent'          optional_bots = 'coderabbit,sourcery'
    bot_lists_provenance = 'answered'   # a deliberate operator answer, not an unset default

Per `automatic-review/standards/bot-participation-contract.md`, an **optional** bot's silence "never
blocks" and is "not a failure". ⇒ **`cuioss-review-bot` (pr-agent) reviewing is a satisfied quorum,
1 of 1.** The "N of 3" framing above overstates a shortfall that did not exist. The operator
confirmed the classification on 2026-08-08: *sourcery stays optional for this project.*

⭐ **What the error produced that is worth keeping:** `PLAN-TRUTH-061`'s shipped disclosure derives
its population from the registry **roster** and never reads `required_bots`/`optional_bots` — so the
mechanism computes shortfalls against this same wrong denominator. That defect is real, is routed to
`review-apparatus` (`truthful-signals-022.md`), and was only visible because the arithmetic was wrong
here first.
