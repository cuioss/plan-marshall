> ⛔ **FIRST INSTRUCTION — do not skip, do not delete, do not move below the title.**
>
> Before reading the rest of this plan and before any other action, load the working contract that
> governs this run:
>
> ```text
> Skill: cloud-plan-lane
> ```
>
> It owns the branch/PR/review-comment cycle, the build gate, the pre-PR verification sub-agent, the
> run report, and the closing self-check. **Nothing in this plan overrides it** — where this plan and
> the contract disagree, the contract wins, and the disagreement is reported.
>
> If the skill cannot be loaded, **stop and report the run blocked**. Do not reconstruct the workflow
> from this file: the parts that matter most — the merge gate, the verification dispatch, the report
> — are not in here.
>
> This block is part of the plan, not part of the template. It survives into every copy.

# The cloud lane contract assumes local-runtime affordances the cloud session does not have

**Epic:** truthful-signals
**Branch prefix:** fix

⚠⚠ **THIS PLAN EDITS THE CONTRACT THAT GOVERNS THIS RUN.** The lane's own rule is that a run **never
self-approves a change to the contract that governs it.** The scope of *this* edit is operator-authored
(the deliverables below), so the run **implements** them — but it must still execute its OWN branch /
build / merge cycle against the contract **as it currently stands**, and any *further* change the run
discovers is **recorded as a proposal** (§ "What have we learned"), never adopted mid-run. ⛔ The
contract wins over this plan, and any disagreement is reported. ⭐ **The run is its own fixture:** it
will itself hit the affordances this plan describes (an MCP-only GitHub path, self-wake tools that may
be gated, a `*.py`-only build gate), so it should report which it actually observed.

## Problem

The lane contract was written against the **local** execution model — a shell with `gh`, a run that can
block-until-green and re-check, a reachable ruleset API, a build gate that mirrors a local plugin-doctor
sweep, a plugin cache to sync, no operator mid-run. But the lane's *reason for existing* is that it runs
in a **cloud** session, and four cloud runs on a single day each independently rediscovered that the
cloud model differs — spending run budget re-deriving the same environment facts, in one case nearly
reading its own inability to self-confirm a merge as a **failure**, and reporting a machine-local
"debt" that a cloud run cannot and need not carry. The contract is silent or subtly wrong at each point
of difference, and it states none of the facts **once** where a future run could reuse them.

The four run reports are the evidence, all git-tracked in this clone:

- `doc/plans/code-intelligence-substrate/010-lsp-in-execute-lookup-and-write/report-01.md`
- `doc/plans/review-apparatus/010-participation-credited-from-a-superseded-commit/report-01.md`
- `doc/plans/truthful-signals/030-merge-gate-cannot-tell-a-required-check-from-a-decorative-one/report-01.md`
- `doc/plans/truthful-signals/040-inert-thinking-directives-in-dispatched-docs/report-01.md`

Six points of divergence survive into the **current** contract (the rest were already fixed — see
§ Notes, "Already landed"). ⭐ **Findings 5 and 6 carry a direct operator ruling** and are therefore
`OBSERVED`, not proposals.

### Finding 1 — Step 8 assumes a synchronous drive the cloud session cannot perform (operator-confirmed)

Step 8 is written as *verify all checks green → merge → confirm `state: MERGED`*, which assumes the run
can **wait** for CI and re-check across the review cycle. In a Claude Code cloud session the self-wake
mechanisms that wait depends on — `send_later`, `subscribe_pr_activity` — were **approval-gated** (both
returned "requires approval"), and Bash cannot poll GitHub (no `gh`, no API auth). The LSP run therefore
could not autonomously block-until-green and confirm the terminal `MERGED` state **within the session**;
it armed auto-merge (the queue enforces the green gate structurally) and disclosed that the landing is
confirmed by the orchestrator at collect. ⭐ **The operator confirmed this is a gap**: arming auto-merge
and handing the `MERGED` confirmation to collect is a **legitimate completion, not a partial run**,
whenever the self-wake tools are unavailable — and the contract does not currently say so, so a future
run in the same environment reads its own inability to self-confirm as a failure.
*(Source: `code-intelligence-substrate/010` report § "What have we learned".)*

### Finding 2 — the contract is written autonomous-only, but interactive runs have a reachable operator

The lane is authored for a headless run with **no operator**. But the `040` run executed in an
interactive main session with the operator reachable, hit a plan STOP CONDITION offering a re-scope, and
**escalated via `AskUserQuestion`** — where a headless run of the *same plan* would have taken the plan's
autonomous fallback. ⇒ **The identical plan yields different outcomes depending on operator
reachability**, and the contract is silent on whether the main session may escalate versus always taking
the fallback. *(Source: `truthful-signals/040` report § "What have we learned".)*

### Finding 3 — the contract is spelled in `gh`, but the cloud path is MCP with no `gh` CLI

Every actionable command in Steps 7–8 is written as `gh` (`gh pr create`, `gh pr merge --squash --auto`,
`gh pr checks`, `gh pr view --json …`, `gh api …/pulls/{N}/comments`). The cloud session has **no `gh`
CLI**; the GitHub MCP server is the only path. § GitHub access says "when running on MCP, use the
equivalent call" but **provides no mapping** — so every cloud run re-derives the translation by hand, and
one run (`030` D3) could not test a `gh`-specific merge behaviour at all because the documented form does
not exist in its environment. *(Source: `truthful-signals/030` report § "What have we learned" #3.)*

### Finding 4 — "read required-ness from the ruleset" reads as an API call that 403s here; and a blocked PR's *disclosed* blocker can name the wrong check

Step 8 condition 1 (reworded by the already-landed plan `030`) says required-ness is "the ruleset's to
define … read it from the ruleset." On the cloud MCP path the **branch-protection / ruleset-config API is
not reachable** — direct `api.github.com` returned `403` ("GitHub access is not enabled for this
session"), and the MCP server exposes no ruleset tool — so a run that reads "read it from the ruleset" as
*call a ruleset API* hits a wall. The run that works reads required-ness from **`mergeStateStatus`**
(GitHub applying the ruleset for you), which condition 1 already names but does not flag as *the* method
because the config API is unreachable. Separately, the `review-apparatus/010` run misread a
`mergeable_state: blocked` PR by promoting a **salient but non-required** pending status (`license/cla`)
to "the blocker" in an operator disclosure, when the real blocker was the still-running **required**
check — the correct derivation is (required contexts ∩ non-green contexts), never the loudest pending
one. *(Sources: `truthful-signals/030` report § "What have we learned" #2; `review-apparatus/010` report
§ "Why the CLA was falsely read as a merge blocker".)*

### Finding 5 — the build gate triggers on docs the local build never builds (operator-ruled: `*.py` only)

Step 4's per-commit gate and Step 5's build-gate table both trigger `./pw quality-gate` on
`.claude/skills/**` and `marketplace/bundles/**` changes, on the rationale that a markdown-only change
"can and does fail the build … it is how this contract's own first PR went red." The `040` run flagged
this as CI-inaccurate — `python-verify.yml` opts into `skip-on-docs-only: true`, and the `030` run
**observed live** that a skills-only PR skipped `verify / verify`. ⭐ **The operator has ruled: for this
project, the local build gate triggers on `*.py` only.** The docs-only change is still not
un-verified — `python-verify.yml`'s own comment states *"A merge_group run … still verify"*, so the
**merge queue's `merge_group` run is the CI net** that builds a docs-only change before it lands; the
run's local gate need not duplicate it. So the skills/bundles trigger rows, and the "first PR went red"
rationale, are wrong in the same understating direction the epic files against.
*(Sources: `truthful-signals/040` report § "Build-gate error"; `030` report § "Build gate"; operator ruling.)*

### Finding 6 — the contract frames a plugin-cache sync as a debt a cloud run owes (operator-ruled: machine-local only)

The § "Scope and precedence" carve-out row (mirrored in `CLAUDE.md`) tells a cloud run editing
`marketplace/bundles/**` to *"record in the report that the plan's bundle edits are unsynced, so whoever
picks the work up locally knows a sync is owed,"* and the report template asks whether the plan
*"owes a local `/sync-plugin-cache`."* The four runs then recorded it **inconsistently** — two reported
"sync owed: yes", `040` argued "neither necessary nor possible … not a debt this cloud run creates."
⭐ **The operator has ruled: `/sync-plugin-cache` is a machine-local build concern; a cloud build never
performs or owes it.** The merged bundle source is authoritative; whether a local developer refreshes
their own cache is their concern, not a debt the cloud run tracks. The "a sync is owed" framing is the
source of the inconsistency. *(Source: `truthful-signals/040` report § Contract check / Residue; operator ruling.)*

## Goal

The cloud-plan-lane contract states the cloud session's actual affordances **once**, in a place a future
run reuses instead of rediscovering; a run that can only arm-and-hand-off its merge is told that is a
completed run; an interactive run knows when it may escalate and a headless one still completes
autonomously; every `gh`-form command carries its MCP equivalent; the merge gate reads required-ness
from the reachable surface and never names a decorative check as a blocker; the build gate triggers on
`*.py` only, with the merge queue named as the net for docs-only; and a cloud run neither performs nor
reports a phantom plugin-cache-sync debt.

## Deliverables

Each is **text whose whole value is what a later RUN does with it**, so each carries a cold read in
§ Verification — "present and well-formed" cannot verify a contract paragraph that reads the wrong way.

1. **D0 — GATE: derive and publish the cloud session's affordance set from the evidence, calibrated to
   THIS run's environment.** Mutates nothing. From the four named reports, enumerate the affordance facts
   the deliverables rest on — GitHub access is MCP-only / no `gh`; `send_later` and `subscribe_pr_activity`
   may be approval-gated; the ruleset-config API is unreachable (`403`) so required-ness comes from
   `mergeStateStatus`; arming MCP auto-merge queues immediately once required checks are green; the CI
   build skips docs-only on the PR trigger but the `merge_group` run still verifies; `/sync-plugin-cache`
   is machine-local — and, for each, record whether **this run's own environment** confirms it (is `gh`
   present here? are the self-wake tools gated here? does the config API `403` here? does the run's own
   build gate fire on its diff?).
   *Done when:* the affordance set is published with a per-fact source (which report / which config file /
   this run's probe), each fact marked *confirmed here* / *reported-only*.
   ⛔ **This decides the WORDING PRECISION of D1 — state "is gated" only where this run confirmed it, and
   "may be gated (reported)" otherwise — it does NOT decide whether the deliverables proceed.** ⭐ **The
   contract is silent or wrong on these facts either way, so the deliverables proceed;** only the
   certainty of each phrasing moves. Halt-and-record only if the corpus is internally inconsistent in a
   way that makes a fact unsafe to state at all.

2. **D1 — a single "Cloud session affordances" section, stating the facts once, with a `gh`↔MCP command
   mapping (Findings 3, 4, 5, 6).** Add a consolidated block the run reads early: the affordance facts
   from D0, and a mapping giving every `gh` command the skill uses its MCP-server equivalent (`pr create`
   [+ label], `pr merge --squash --auto`, `pr checks`, `pr view --json mergeStateStatus,mergeable,state,mergedAt`,
   `api …/pulls/{N}/comments` — the inline-review-thread surface). Cross-reference it from § GitHub
   access, Steps 7–8, and Step 5 rather than restating.
   *Done when:* a reader handed any single `gh`-form line in the skill can name the exact MCP call to make
   from the mapping, and the affordance facts appear in exactly one place (no restatement that can drift).
   ⛔ **Do not name an individual *check* here** — the affordances are about the *access path, tools,
   build trigger, and sync model*, not the repo's check set, which stays the ruleset's to define (§ D3).

3. **D2 — Step 8: sanction arm-and-hand-off as a completed run (Finding 1).** State that when the
   self-wake tools are unavailable, **arming auto-merge and handing the terminal `MERGED` confirmation to
   the orchestrator collect step** (which reads it from the PR merge event) is a **completed** run, not
   `partial` or `blocked`; and reconcile Step 9's contract-check row 8, which currently reads as "confirm
   `MERGED` within the session."
   *Done when:* a cold reader given "auto-merge armed, required checks green, `MERGED` not yet observable
   because self-wake is gated" classifies the run as **completed**, not failed — and the row-8 artifact
   language no longer demands in-session `MERGED`.
   ⛔ **This must NOT weaken the confirm-the-merge-actually-happened rule for runs that CAN self-confirm.**
   The claim-is-not-an-outcome rule stands; this adds a *second legitimate terminal state* for the
   self-wake-gated environment, it does not license asserting a merge that was never read back.

4. **D3 — Step 8 condition 1: the reachable-surface increment on the already-landed required/decorative
   rewording (Finding 4).** Building on plan `030`'s landed condition-1 text (⛔ re-ground against its
   *current* wording before editing — do not rewrite it), add: (a) the ruleset-config API is not reachable
   on the cloud MCP path, so required-ness is read from `mergeStateStatus` (GitHub applying the ruleset),
   never from a config-API call; and (b) when `mergeStateStatus` is `BLOCKED`, the blocker is derived from
   (required contexts ∩ non-green contexts), and a visible-but-non-required pending status is **never**
   named as "the blocker" in an operator disclosure.
   *Done when:* two cold reads pass — (i) a reader given the condition does **not** attempt a ruleset-config
   API call but reads `mergeStateStatus`; (ii) a reader given a `BLOCKED` PR whose only non-green check is
   a **non-required** pending status names the blocker as the unsatisfied **required** context (pending or
   absent), not the salient non-required one.
   ⛔ **The cloud increment only.** The required-vs-decorative *distinction* is already landed; do not
   redo it, and do not name any individual check.

5. **D4 — the interactive-vs-headless escalation duality (Finding 2).** In § "Rules that outrank
   convenience" (or a dedicated adjacent note), state that when the executing session has a **reachable
   operator** — an interactive main session, not a dispatched leaf — and a plan offers a re-scope or names
   a STOP CONDITION with an autonomous fallback, the run **MAY** escalate the decision via
   `AskUserQuestion`; a **headless** run, or a dispatched leaf, takes the plan's stated autonomous
   fallback.
   *Done when:* a cold reader given two scenarios — an interactive main session with a reachable operator,
   and a headless run — selects **escalate-via-AskUserQuestion** for the first and **autonomous-fallback**
   for the second.
   ⛔ **Escalation is `MAY`, never `MUST`.** A mandatory escalation would author a deliverable that
   *requires* a decision a headless run cannot make (the no-operator rule). The headless autonomous path
   must remain a complete, unblocked outcome.

6. **D5 — correct the build-system affordance assumptions (Findings 5 and 6; both operator-ruled).** Two
   parts, same "the contract mis-states the local build system" root:
   - **(a) Build gate → `*.py` only, at BOTH sites.** Narrow Step 4's per-commit gate and Step 5's table
     to trigger the build on `*.py` changes only; drop the `.claude/skills/**` / `marketplace/bundles/**`
     trigger rows; remove the CI-inaccurate "Why the second row exists" rationale and the "first PR went
     red on a missing `mode:` field" claim. Name the merge queue's `merge_group` run as the CI net that
     still verifies a docs-only change before it lands. ⭐ **Carry forward plan `400`'s still-valid fix:**
     add `errors[]` alongside `status` (and, for `verify`, `total_issues`) to the field list the gate
     reads, at both sites — the repository-wide rule names all three, and a `*.py`-only predicate does not
     change which fields make the log conclusive.
     *Done when:* Step 5's table has two rows (`*.py` → `./pw verify`; else → skip), no rationale claims a
     markdown-only change fails the local build, and both gate sites read `status` **and** `errors[]`.
   - **(b) `/sync-plugin-cache` is machine-local; a cloud run neither performs nor owes it.** Reword the
     skill's § "Scope and precedence" carve-out row and the report template's Contract-check line so a
     cloud run stops reporting a "sync owed" debt — the merged bundle source is authoritative; a local
     cache refresh is a local-developer concern, not a debt this cloud run tracks. ⛔ **Skill only** — the
     `CLAUDE.md` § "Standalone Plan Lane" summary carries the same stale framing, but it lives in the root
     instructions that also govern *local* work, not the cloud lane's contract; aligning it is left to the
     operator and is out of scope here (§ Out of scope).
     *Done when:* the skill's carve-out row and the report template no longer frame a cloud run as *owing*
     a sync, and a cold reader given a bundle-editing cloud run reports **no sync debt**, not "sync owed: yes".
   ⛔ **(a) supersedes the premise of staged plan `400`** (§ Out of scope / § Notes) — do not also apply
   plan 400's three-outcome report vocabulary, which a two-outcome gate makes unnecessary.

**Six deliverables (a GATE plus five), one component (the `cloud-plan-lane` skill — the cloud lane's
contract, and nothing that governs local plan execution), one theme.** ⛔ **Resist widening into a
general lane audit** — six findings were routed here from four run reports and two operator rulings, not
an open-ended review.

## Out of scope

- ⛔⛔ **Local plan execution and the general build / plugin-cache machinery — this is a CLOUD-ONLY
  change.** Every finding here governs the standalone **cloud** lane: the `*.py`-only build gate, the
  arm-and-hand-off merge, the escalation duality, the no-sync rule. Local plans run the plan-marshall
  lifecycle instead (`.plan/execute-script.py`, `architecture resolve`, and the **general** `CLAUDE.md`
  Build-Commands and Plugin-Cache-Sync sections) — a **different, machine-local runtime this plan does
  not touch.** ⛔ **Every edit lands in `.claude/skills/cloud-plan-lane/SKILL.md` and nowhere else** — not
  the plan-marshall build machinery, and not the `CLAUDE.md` § "Standalone Plan Lane" summary (a root-
  instruction mirror the operator aligns separately if wanted). The skill *is* the cloud lane's contract;
  it is the whole surface.
- ⛔ **The merge gate's required-vs-decorative check distinction itself.** ✅ Already **landed** by plan
  `030` (PR #1137). D3 adds only the cloud *increment* on top; it does not redo the distinction.
- **Cloud-run commit authorship (`Claude <noreply@anthropic.com>`) leaving author-email checks
  (`license/cla`) permanently pending.** Excluded because it has **no lane-contract lever**: the commit
  identity is set by the harness, not the contract, and the contract deliberately **names no individual
  check** — writing `license/cla` into the skill is the very defect condition 1 forbids. It is an
  authorship-identity / infra decision for the operator; recorded in § "What have we learned", not fixed
  here.
- ⛔ **`doc/plans/**` — individual lane plans.** This plan changes the lane's **contract**, never a plan
  executed under it.
- **Staged plan `400-cloud-lane-build-gate-reads-one-field-short` — do not run it alongside this.** ⚠ **The
  operator's `*.py`-only ruling dissolves plan 400's premise.** Plan 400 asserts "Step 5 defines three
  trigger surfaces *deliberately*" and builds its Finding 2 (a three-outcome report vocabulary) and D3 (a
  drift check between the three-row and one-row tables) on that middle row. A two-outcome (`*.py` / not)
  gate removes the middle row, so **plan 400's Finding 2 evaporates** (the report template's existing
  "no Python changes, build skipped" already expresses the two outcomes), and its only independent
  survivor — the `errors[]` field (its Finding 1 / D1) — is **carried into D5(a) here**. ⇒ **Recommend
  retiring plan 400.** If the operator keeps it instead, the two hard-conflict on the same lines and must
  serialize with 400 re-grounded onto the `*.py`-only model first.

## Expected surface

- `.claude/skills/cloud-plan-lane/SKILL.md` — **located by quoted phrase, not by line** (the file is
  edited often; line numbers are the least durable part of any claim):
  - a **new** consolidated "Cloud session affordances" section (D1) with the `gh`↔MCP mapping;
  - § "GitHub access" — cross-reference to the new section (D1);
  - § "Scope and precedence" — the Plugin Cache Sync carve-out row (D5b);
  - Step 4 — the per-commit gate predicate + field list (D5a);
  - Step 5 — the build-gate table, the "Why the second row exists" rationale, and the field list (D5a);
  - Step 8 — the merge-completion prose (D2) and condition 1 (D3);
  - Step 9 — contract-check **row 8** (D2 reconciliation);
  - § "Rules that outrank convenience" — the escalation duality (D4);
  - the **Report** template — the Cost/Contract-check lines for sync-debt (D5b) and the build-gate
    section wording (D5a).

  ⛔ **This one file is the entire write surface.** No `CLAUDE.md` edit, no plan-marshall build machinery,
  nothing under `marketplace/bundles/**` — the cloud lane's contract lives wholly in this skill (§ Out of scope).
- **Read-only evidence corpus** (the grounding for D0, git-reachable in the clone): the four `report-01.md`
  files named in § Problem.
- **Read-only** — `.github/workflows/python-verify.yml` (the `skip-on-docs-only` opt-in and the
  "`merge_group` … still verify" comment that grounds D5a's net).

⚠ **No `/sync-plugin-cache` is owed by this plan — and after D5b, that is the contract's plain statement,
not a caveat.** It edits only `.claude/skills/cloud-plan-lane/SKILL.md` (project-local, loaded from the
clone) — no `marketplace/bundles/**` source, no `~/.claude/` cache. ⭐ **This plan is its own first
instance of the D5b rule:** its run reports **no sync debt.**

## Claim labels

Every scoping premise is labelled; a `HYPOTHESIS` carries the git-reachable artifact that settles it, and
is re-verified **by content** at the moment of the claim (line numbers drift).

| Claim | Label | Confirm/refute artifact |
|---|---|---|
| Each of the four runs independently rediscovered the cloud environment's constraints | OBSERVED | the four `report-01.md` files, read for this plan — **git-tracked, first-party in the clone** |
| `send_later` / `subscribe_pr_activity` were approval-gated, so the LSP run could not self-confirm `MERGED` | OBSERVED | `code-intelligence-substrate/010` report § "What have we learned" — ⭐ **operator-confirmed there.** Re-probe in THIS run (D0) |
| The ruleset-config API returns `403` on the cloud MCP path | OBSERVED | `truthful-signals/030` report D0 — the `403` body is quoted. ⛔ **Do not route around a `403`** (agent-proxy rule) — read `mergeStateStatus` |
| The skill is written in `gh`-form; the cloud path is MCP with no `gh` CLI | OBSERVED | reports `030` D3 and `code-intelligence-substrate/010`; the skill's § "GitHub access" text |
| Step 8 does not sanction arm-and-hand-off; the contract is silent on operator escalation | HYPOTHESIS | the current `SKILL.md` — **by quoted phrase, re-verified by content.** ⚠ An asserted *absence* — the higher-risk half |
| Plan `030` already landed the required-vs-decorative rewording of condition 1 | OBSERVED | `030` report (D1 in `f834942`, PR #1137 merged) **and** the current `SKILL.md` condition 1 — ⛔ **re-ground before D3 edits** |
| The local build gate can be `*.py`-only because the `merge_group` run still verifies docs-only | OBSERVED | `.github/workflows/python-verify.yml` — the `skip-on-docs-only` opt-in and the "*A merge_group run … still verify*" comment; `030` report's live "docs-only path — verify/verify skipped" observation |
| For this project the build gate triggers on `*.py` only | OBSERVED | **operator ruling** — the authoritative resolution of `040`'s build-gate finding |
| `/sync-plugin-cache` is machine-local; a cloud run neither performs nor owes it | OBSERVED | **operator ruling** — settles the `030`-vs-`040`-vs-plan-400 disagreement |
| The `*.py`-only ruling dissolves plan `400`'s Finding 2 and leaves only its `errors[]` fix | HYPOTHESIS | `doc/plans/truthful-signals/400-…md` — read its D2/D3 premise against a two-outcome gate before acting |

An asserted **absence** is verified exactly as an asserted presence, and is the higher-risk half. Every
count and set above is a **lead** — re-derive it at the moment of the claim.

## Verification

- ⛔ **D1–D5 are each text-that-drives-a-reader, so each gets an independent COLD READ** (the Step 6
  verification sub-agent is the vehicle; aim it at *interpretation*, not just "implemented as specified"):
  - **D1 mapping** — hand the reader one `gh`-form line and the new mapping, ask for the MCP call. Correct
    answer names the exact MCP tool. **And** confirm the affordance facts appear in exactly one place.
  - **D2** — scenario: auto-merge armed, required checks green, `MERGED` not yet observable. Ask: completed,
    or failed/partial? **Correct answer: completed.**
  - **D3(i)** — hand the reader condition 1, ask how to read required-ness. Correct: reads `mergeStateStatus`,
    no ruleset-config API call. **D3(ii)** — a `BLOCKED` PR whose only non-green check is non-required. Ask
    the blocker. **Correct: the unsatisfied REQUIRED context**, never the salient non-required one.
  - **D4** — two scenarios (interactive main with reachable operator; headless). **Correct: escalate-via-
    `AskUserQuestion`; autonomous-fallback.**
  - **D5(a)** — hand the reader a docs-only diff and ask which build the gate runs. **Correct: none — record
    "no buildable footprint, build skipped"** (and the merge queue is the net), *not* a local quality gate.
    Then a synthetic build result with a green `status`, zero `total_issues`, and a **non-empty `errors[]`**
    — ask whether the gate passed. **Correct: NO** (the `errors[]` field is read).
  - **D5(b)** — hand the reader a bundle-editing cloud run, ask what its report says about a plugin-cache
    sync. **Correct: no sync debt** — a machine-local concern, not owed by the cloud run.
- ⛔ **D0's affordance set is re-derived from the four reports at the moment of the claim, and names a
  source per fact** — a set stated without per-fact provenance is an assertion, not a derivation.
- ⚠ **This run is its own live fixture.** It uses the MCP GitHub path, likely finds the self-wake tools
  gated, edits the very Step 8 that governs its own merge, and — because it changes only `.claude/skills/`
  (no `*.py`) — its own build gate takes the **skip** path and its own report carries **no sync debt**,
  a live instance of D5. Report all of this first-hand.

## Notes

- ⭐ **Already landed — do NOT re-open** (verified against the current `SKILL.md`): the queue-lock
  "one-way door" recovery (`030`), the required-vs-decorative condition-1 rewording (`030` D1), the
  `never git add -A` lockfile-churn rule (`030` D4), and the Bridge-row / "record nothing outside your
  plan directory" wording (`030` D5). A run that re-proposes any of these has not re-grounded against the
  file.
- ⛔ **Plan `400` is superseded by D5(a), not merely adjacent** (§ Out of scope). The operator's
  `*.py`-only ruling removed the middle trigger row plan 400 assumed permanent, so its report-vocabulary
  finding no longer exists and its `errors[]` fix is carried here. **Recommend retiring plan 400**;
  if kept, it must re-ground onto the two-outcome model and this plan serializes behind it.
- ⭐ **Dogfooding is deliberate:** a run editing the *merge* gate then exercises the merge gate on its own
  PR; a run editing the *arm-and-hand-off* sanction is (in the self-wake-gated cloud environment) the
  exact case D2 describes; and a run editing the *sync* and *build-trigger* rules is itself a
  `.claude/skills/`-only change that exercises both. Report the coincidences as evidence.
- **D4 preserves the no-operator model** by authoring escalation as `MAY` with the autonomous fallback
  intact — the plan adds a *permitted* interactive path without making any deliverable *require* a mid-run
  decision.
- ⛔ **Do not go looking for the orchestrator spec, the routed inbox message, or any landing record.** They
  live under `.plan/`, git-ignored and absent from this clone. Everything this plan needs is in this file
  and the four git-tracked reports it names.
