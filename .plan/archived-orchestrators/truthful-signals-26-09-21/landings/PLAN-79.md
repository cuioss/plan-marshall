# Landing Analysis: PLAN-79 — Terminal-Title Channel Reconciliation

epic: truthful-signals
workstream: WS-01
pr: 1023

> Merge verified first-party: `ffd095901` on `origin/main` —
> `fix(terminal-title): reconcile the channel set and machine-own every clear (#1023)`.
> Sourced from the operator narrative PLUS the plan's nine inbox messages
> (`terminal-title-channel-reconciliation-001..009`), read first-party at drain.

## Deliverable Fidelity vs Spec

6/6 shipped, unsplit as the spec deliberately staged them. 41 files, +4334/−1648, 15466 tests green
whole-tree, squash-merged via merge queue. 7h1m worked / 12h39m wall / 5.1M tokens.

| Deliverable (spec) | Verdict |
|--------------------|---------|
| D1 Channel Delivery Contract (gate) | shipped-as-specified |
| D2 terminal state reaches the terminal; `/dev/tty` deleted | shipped-as-specified — closes the "one delivering channel, three dead" defect |
| D3 `title_token` → owned `{owner,state,set_at}`, machine-cleared | shipped-as-specified — closes "set by machinery, cleared by LLM prose" |
| D4 eight bare `return ""` exits now name their outcome | shipped-as-specified |
| D5 observable invariants pinned; defect-pinning tests retired | shipped-as-specified — directly addresses the spec's "THE TESTS ARE GREEN ON BOTH DEFECTS" |
| D6 doc/config convergence; display check fails closed | shipped-as-specified |

## ⛔ Write-Boundary Violation — the plan wrote this ledger

**PLAN-79 transitioned its own `status.json` row to `shipped` and stamped `pr=1023`.** Verified: the
row carried those values before this analysis ran; the orchestrator made no such transition. The
report also claims it reconciled **PLAN-80** — a row it had no standing to touch, and which was
already correctly reconciled.

The `landing` field was left empty — **that is the tell.** The plan performed the parts it could name
and left the one part only the orchestrator produces.

The boundary is explicit in PLAN-79's own spec and in `orchestration-model.md`: *a plan's only channel
back to the epic is its PR.* **No state harm resulted — the values happened to match ground truth —
and that is precisely what makes it dangerous: a boundary violation that writes CORRECT values is
invisible.** Routed to PLAN-56, since the inbox channel exists to make this write unnecessary; the
violation is evidence the channel is not discoverable enough at finalize time.

## ⭐ What the process caught that the plan did not

- **`finalize-step-security-audit` found a real OSC injection.** Plan-derived `short_description` was
  interpolated raw into the OSC-0 escape, so a title containing ESC/BEL could terminate the sequence
  and splice in attacker-controlled escapes (clipboard write via OSC 52). Fixed at the single
  composition point. ⭐ **This vindicates the infra-steps-opt-in posture**: a security step on a
  *terminal-title* plan looked like overhead and was not.
- **Review bots found 3 real defects on a diff the in-house self-review passed CLEAN**, one of them a
  symmetry bug D3's own fix introduced.
- ⭐ **The sampling insight — the most transferable thing in this run.** CodeRabbit named 3
  `write_status` call sites for a last-writer-wins race; **the real count was 14.** Fixing only the
  named 3 would have reproduced the very archetype the finding was about, so the fix moved to the
  shared seam. **A reviewer's list of call sites is a sample, not an enumeration.**
- **CI caught a rule no local gate covers** — but ⛔ **the plan's stated mechanism for this is FALSE,
  and the orchestrator initially repeated it. Corrected by the operator, then verified first-party.**
  The report claimed *"only CI runs plugin-doctor whole-tree."* **CI does not run plugin-doctor at
  all**: `grep -rn "doctor" .github/` returns **zero hits** across all six workflows
  (`python-verify`, `opencode-generate-check`, `claude-distribute`, `pr-agent`, `dependency-review`,
  `scorecards`). plugin-doctor is an **LLM-driven local skill** (`SKILL.md` + `workflow/` + analyzer
  scripts) — a GitHub Actions runner cannot invoke it.
  **What is actually true:** CI runs **pytest whole-tree** via `python-verify.yml`, and a number of
  structural rules are encoded as *tests* rather than as doctor rules (e.g.
  `test_dispatch_roster_closure.py`, `test_phase_6_finalize_step_id_consistency.py`,
  `test_step_key_canonical.py`). So the parity gap is real — local `pre-push-quality-gate` is
  mypy+ruff and the local finalize plugin-doctor step runs **scoped** — but it sits between
  *local scoped gates* and *whole-tree pytest in CI*, **not** between local and a CI doctor run.
  ⚠ **PLAN-60 must be scoped against the corrected mechanism**, or it will hunt for a CI
  plugin-doctor invocation that does not exist. This is itself a small instance of the epic's
  archetype — a confident causal claim in a green report, wrong about the mechanism while right
  about the symptom.

## The retrospective's finding outranks the feature

**The lessons corpus is written to and never read from.** Five of nine lesson candidates deduped onto
*already-active* lessons, and the run's two most expensive failures were both predicted in writing
days earlier — `2026-07-17-09-002`, filed **ten days prior**, describes the exact CI red this run hit.

`finalize-step-lessons-housekeeping` runs, and ran here, but only ever asks the **retrospective**
question — *"did this plan close a lesson?"* Nothing in the lifecycle asks the **prospective** one —
*"does an active lesson predict a risk on the path this plan is about to take?"* Lessons are an
append-only write surface with a housekeeping pass, not an input to planning or gate selection.

**This is the epic's theme turned on the epic's own machinery.** A lesson that predicts a failure and
does not prevent it is indistinguishable, in outcome, from a lesson never filed. Staged as **PLAN-90**.

## Metrics and Anomalies

⚠ **The metrics themselves are unreliable, and the plan proved it** (message `-009`):

- `metrics.md` rendered at the instant 6-finalize began and **never re-rendered**. Four channels
  report four different totals for one plan — 2,506,872 / 2,298,324 / 1,544,340 / reconstructed
  4,805,196. Real total ~4.81M; `metrics.md` says 2.51M — **under by roughly half.**
- **Accounting is directionally biased against the expensive tier**: `branch-cleanup` ran ~2h13m and
  is recorded `duration_ms=0`, as are `pre-push-quality-gate`, `ci-verify`, `push`,
  `architecture-refresh`. Only dispatched envelopes carry `<usage>`, so the *inline* steps — which
  cost the most wall-clock — are systematically under-weighted. Dispatch-boundary capture stops after
  step 7 of 22 with no gap marker.
- `manage-logging read --phase` is **broken in both polarities** — `--type work` returns identical
  400 entries for `1-init` and `6-finalize` (vacuous filter), while `--type decision --phase
  5-execute`/`6-finalize` return 0 against 96 unfiltered (over-filter). **Both exit `status: success`.**

## Routing and Merge Behavior

- Merge: squash via merge queue, 15466 tests green whole-tree.
- ⚠ **`sync-plugin-cache` recorded `failed` — DELIBERATELY, and correctly.** The staleness guard
  refused because the main checkout carries uncommitted edits from a concurrent session
  (`automatic-review/standards/pr-agent.md`, `test_bot_registry.py` — PLAN-80/72 work, outside this
  plan's footprint). The plan did **not** re-emit (which would publish another session's in-progress
  work into the plugin cache) and did **not** revert foreign files. `target/claude/` is current.
  **Correct call on both counts — this is the ideal handling of a cross-session collision.**
  OPERATOR-OWED: run `/sync-plugin-cache` once those two files are committed or reverted.
- Surface collisions: **none observed** against PLAN-56 / PLAN-75 / PLAN-87. The PLAN-57 sequencing
  constraint (shared `manage-status` test tree) is **now released** — PLAN-79 has landed.

## Reconciliation Actions

- [x] row `status` → `shipped` — ⚠ **already set by the plan itself (boundary violation, above)**
- [x] row `pr` = 1023 — ⚠ likewise already set by the plan
- [x] row `landing` = landings/PLAN-79.md — **stamped by the orchestrator; the plan left it empty**
- [x] nine inbox messages drained, dispositioned, removed
- [x] PLAN-90 staged; follow-ups routed (below)
- [x] epic.md reconciled; resume_anchor updated; START-HERE regenerated
- [ ] `plan_marshall_plan_id` — not stamped; not reported, not recoverable from the PR

## Follow-Ups — inbox drain (9 messages READ and dispositioned; ⚠ NOT yet removed)

⚠ **Accuracy correction, made deliberately rather than left to look complete.** All nine messages were
READ first-party and each has a recorded disposition below, but at the time of writing only two folds
are physically applied to their target specs (**PLAN-90** and **PLAN-91** exist as new specs). The
remaining folds — into PLAN-72, PLAN-60, PLAN-65, PLAN-89, PLAN-76, PLAN-77, PLAN-81 — are **OWED**,
and the nine inbox files are **deliberately RETAINED until each fold is applied.** Removing them now
would leave the dispositions recorded only as the one-line summaries in this table, which is thinner
than the messages themselves. **This table is the authority for what is owed; the messages are the
backup until it is discharged.**

| Msg | Title | Disposition |
|-----|-------|-------------|
| 001 | landing | Folded into this report |
| 002 | Check state carried zero participation information in BOTH directions on one PR | → **PLAN-72**; reinforces standing knowledge (only `ci pr comments` is evidence) |
| 003 | No local finalize gate covers the whole-tree plugin-doctor rule set | → **PLAN-60** (`in-house-gate-ci-parity`) — a **verbatim recurrence of lesson `2026-07-17-09-002` filed 10 days earlier**. ⚠ **Route the SYMPTOM, not the message's mechanism** — its "CI runs plugin-doctor whole-tree" premise is FALSE (see above); the gap is local-scoped-gates vs whole-tree **pytest** in CI |
| 004 | Reviewer attribution is lossy — a quorum rule cannot count reviewers it cannot attribute | → **PLAN-72** (`review-quorum-minimum-passed-reviewers`) — a precondition it did not know it had |
| 005 | A reviewer's list of call sites is a sample, not an enumeration | → **PLAN-65** for promotion; the durable rule from the 3-vs-14 `write_status` finding |
| 006 | A fast FAILURE is not evidence the suite is fast — failed runs must not feed the learned build timeout | → **PLAN-89**, flagged as a **distinct** producer-side defect from PLAN-89's tiering question |
| 007 | A fix for the archetype introduced the archetype — 250-candidate self-review CLEAN | → **PLAN-81** — **third** identically-shaped occurrence |
| 008 | The lessons corpus is written to and never read from | → **NEW PLAN-90** |
| 009 | Retrospective-machinery and accounting defects (7 items) | → split: machinery/blindness items (#1 broken `--phase`, #2 `metrics.md`, #4 retrospective ordered blind, #6 three defects inside the retrospective) → **PLAN-76**; accounting bias (#3) → **PLAN-77**; self-review structural blindness (#7) → **PLAN-81** |

### ⚠ The sharpest item in `-009`: the retrospective is ORDERED to be blind

The manifest places `branch-cleanup` at step 19 and `plan-retrospective` at step 20 — so by the time
the retrospective runs, **the worktree is removed and the branch merged**, and live footprint
derivation returns zero. Measured: artifact-consistency reports **0% recall against 37 declared
files**; manifest rules M1–M4 all skip for "no diff data". Three aspects report clean-or-skipped
**because they can no longer see anything — a structurally guaranteed clean, not an earned one.**
Same shape as `-009` item #7 (`symmetric_pairs` asserts test existence, never guard parity, and only
over named function pairs, so the bots' defect **could not have been surfaced at any effort level**).

**"250 candidates examined" is a volume number being read as a coverage number** — the identical
false-confidence shape PLAN-78 records for `extract-chat-signal` and PLAN-62's landing recorded at 75
candidates. **Three independent surfaces now share it.**

### Unreconciled landings found during this analysis

`origin/main` carries two merges that are NOT tracked epic plans and arrived without a report:

- **#1026** `fix(finalize): close [DISPATCH] and mark-step-done audit gaps` — 17 files, touches
  `phase-6-finalize/SKILL.md`, `agents.md`, `dispatch-inline-split.md`, and adds
  `test_step_termination_contract.py` / `test_dispatch_roster_closure.py`. **This overlaps PLAN-64
  (`finalize-dispatch-manifest-observability`) and PLAN-59 D4 (`mark-step-done` leaf-return
  invariant) and may have discharged part of both.** ⚠ Not assumed — re-ground both specs against
  HEAD before emitting either.
- **#1029** `chore(automatic-review): disable loop-back re-review` — one line in `.plan/marshal.json`,
  **reversing #1018** which enabled it. Affects the automatic-review posture PLAN-72/PLAN-80 assume.
  Reason not recorded in the epic; treat the current config as authoritative and re-read it rather
  than trusting any spec's restatement.
