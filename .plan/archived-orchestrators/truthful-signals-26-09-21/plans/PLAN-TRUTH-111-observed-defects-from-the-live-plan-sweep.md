# PLAN-TRUTH-111: Observed defects from the live-plan sweep

epic: truthful-signals
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no brief.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and hand-off contract.

## Provenance

Staged 2026-08-24 on operator direction (*"of course the concrete bugs are to be planned for fixing as
well"*), from the first orchestrator sweep of live plans' findings stores plus the PR #1340 transcript.

⛔ **These are the members with NO existing owner.** Members that folded elsewhere are named under
§ Not in scope so this plan does not re-derive them.

⚠ **Every finding here was FILED BY A PLAN, first-party, in its own run.** This spec did not discover
them; it gives them an owner because the channel that would have delivered them does not exist
(`PLAN-TRUTH-110`) and the read path returned a clean zero (`PLAN-TRUTH-109`).

## Objective

Fix the concrete defects that live plans filed first-party and that have no other owner. Each is a
member in § Deliverables, and each is named there. This is a bundle of unowned members, not one
mechanism, so outline should evaluate splitting along member boundaries. *(Section added at the
2026-09-11 `cleanup` as a pointer.)*

## Deliverables

Six deliverables. D0 is a gate. ⚠ **Deliberately a grab-bag of one subsystem's observed defects, not a
theme** — outline should split it if D0's re-grounding shows the members diverge.

**D0 — GATE: re-ground every member at HEAD before fixing any.** All were observed inside a running
plan's envelope, some against a **seated cache that may lag repo source** — `D-095-c` records a
near-miss where exactly that produced a confident false finding, refuted only because repo source was
checked. ⛔ **Re-verify each against repo source, not against a seated skill body.** A member that no
longer reproduces is dropped with a positive account (the commit or symbol that closed it), never
silently.

**D1 — `ci pr view` returns no PR body, so read-modify-append on a body is unreachable.** Verified
first-party: it returns 12 fields and no `body`, with no flag to request one, while `pr edit`
**replaces** from a scratch file. ⇒ A caller attempting to append silently overwrites.
⛔ **Do NOT frame this as a documented-invocation defect.** `architecture-refresh.md:276` already
**retired** that sequence, for a different reason (no PR exists when that step runs). ⭐ **The reason it
matters is forward, not backward:** that doc's owed remedy is a **re-homing to a surface after
`create-pr`, where a PR does exist — and that surface hits this exact wall.** The gap blocks the fix
the retirement promises.

**D2 — `pr_intent_section`'s 1500-character budget clips mid-sentence.** Filed by the run as
*"pr_intent_section 1500-char budget clipped the whole non-goals paragraph"*; the cut landed at
`**Explicit`, so the explicit non-goals paragraph never reached the PR body — ⛔ *"precisely the
paragraph that stops a reviewer filing a scoped-out concern as a gap, and the bots were about to read
it."* ⚠ A budget is legitimate; **clipping mid-token is not.** Truncate at a boundary and say so, or
drop the section whole with a marker. ⭐ Keep the run's mitigation as documented practice: post the
missing content as an **additive top-level comment** rather than rewriting the body blind.

**D3 — `assert-step-recorded --require-terminal` passes on a STALE record from a prior firing.** ⛔ The
verb exists to catch a step that returned without recording; **accepting a prior firing's record
defeats it exactly on the re-fire path**, which is where finalize spends most of its steps. ⚠ Adjacent
to `-097` F5 (`prior_firings[]` carries outcomes without SHAs) — **the missing anchor is plausibly the
same root cause**; D0 must check before fixing them separately.

**D4 — `scope_creep_check` publishes a vacuous clean zero when it has no baseline sha.** The epic's
canonical archetype, in a check whose whole purpose is to detect drift. ⇒ Publish the baseline and a
three-way status; an absent baseline is `indeterminate`, never clean. ⭐ **`manage-lessons`' resolved /
missing / unresolved vocabulary is the shipped model** — reuse it rather than inventing a fourth.

**D5 — the `Bash` tool swallows non-zero exit codes, so bare `git diff --quiet` proofs are vacuous.**
Filed at **`error`** severity, and it is **self-invalidating**: the plan that filed it says *"every bare
`git diff --quiet` byte-clean proof in this plan is vacuous."* ⛔ **Scope carefully at D0.** The harness
behaviour is not ours to change; **what is ours is every call site that treats a bare exit code as a
proof.** ⇒ Sweep for them and make each read an explicit status, exactly as the build-wrapper rule
already requires (*the wrapper exits 0 on failure; read the TOON `status`*). ⚠ **This may be the
largest member; if D0's sweep is wide, split it out.**

## Not in scope — folded elsewhere, do not re-derive

- `review_commitments reconciliation is structurally vacuous at order 8` and `review_commitments
  reconcile saw 0 commitments on a run with 8 resolved self-review findings` → **`PLAN-TRUTH-104`**
  (independent confirmation, and the second is sharper than `-104`'s own framing).
- `affected_files diverges from the live footprint and nearly downgraded a live gate` →
  **`PLAN-TRUTH-098`** Arm 2.
- The 9 unresolved `pr-comment` findings on PR #1340 → that plan's own review cycle; **not ours.**
- `OPERATOR DECISION OWED: the zero-skip gate is inert — arm it or delete it` → ⛔ **an operator
  decision, surfaced separately. Not a deliverable here.**

## Expected Surface

Provisional — D0 will move it.

- `marketplace/bundles/plan-marshall/skills/tools-integration-ci/**`
- `marketplace/bundles/plan-marshall/skills/phase-6-finalize/**`
- `marketplace/bundles/plan-marshall/skills/manage-status/**` *(`assert-step-recorded`)*
- `marketplace/bundles/plan-marshall/skills/plan-retrospective/**` *(`scope_creep_check`)*
- `test/plan-marshall/**`

## Dependencies and Sequencing

⛔ **Re-derive with `corpus cross-check` at emit time.**

- ⚠ **`PLAN-TRUTH-097`** — D3 is adjacent to its F5. Serialize if D0 confirms shared root cause.
- ⚠ **`PLAN-TRUTH-106`** — D2 touches PR-body rendering; `-106` restructures the report/landing
  surfaces. Confirm no overlap at emit.
- **Depends on:** nothing hard.

## Claim Labels

- OBSERVED: `ci pr view --pr-number 1340` returns 12 fields and no `body`; `architecture-refresh.md:276` says the append sequence was *previously* prescribed and is retired — both read first-party 2026-08-24.
  - verdict: corroborated | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: github_ops.py view_pr_data requests 11 gh --json fields and returns no body key; architecture-refresh.md:276 confirms the retirement text verbatim
- OBSERVED: the five remaining members are findings filed by live plans, read from `.plan/local/worktrees/*/…/artifacts/findings/*.jsonl` in the 2026-08-24 sweep, with their titles quoted verbatim above.
  - verdict: unverifiable | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: .plan/local/worktrees/ now holds 5 unrelated worktrees; none of the 2026-08-24 sweep source plans or worktrees remain
- HYPOTHESIS: each still reproduces at HEAD — confirm/refute at D0 against **repo source, not a seated skill body** (verify-at-outline). ⛔ `D-095-c` records a near-miss where a seated body produced a confident false finding.
  - verdict: unverifiable | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: D0 re-grounding gate has not run; no plan directory implementing this spec exists yet
- HYPOTHESIS: D3 and `-097` F5 share a root cause (a missing per-firing anchor) — confirm/refute at D0 (verify-at-outline).
  - verdict: unverifiable | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: Shared-root-cause hypothesis explicitly deferred to D0; not run
- HYPOTHESIS: D5's call-site population is small — confirm/refute at D0 (verify-at-outline). **If wide, split it out rather than absorbing it.**
  - verdict: unverifiable | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: D5 call-site population size explicitly deferred to D0; not run
- Verify-first clause: a member that no longer reproduces is dropped with a **positive account** of what closed it — an absent symbol is equally explained by a fix, a rename and a file move.
  - verdict: unverifiable | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: Forward verify-first clause; not yet executed

## Folded from the PLAN-TRUTH-096 drain (2026-08-24)

Two verified observed defects, each self-contained and small.

**(1) The chat-history aspect analysed one of two recorded sessions (inbox `-002`).**
`plan-retrospective` takes a single optional `--session-id` and dispatches the chat-history aspect
against that one transcript. This plan's `status.metadata.session_ids` records **two**, and the
dispatcher supplied only the second:

| Session | raw turns | operator turns | gate decisions |
|---|---:|---:|---:|
| `fbc49fc3…` (supplied) | 340 | 1 | 0 |
| `e0c9a71c…` (not supplied) | 1691 | 10 | 15 |

The single operator turn in the supplied session **is the slash-command invocation itself**. Every
gate decision, every correction, and every unblocking prod lives in the session the dispatcher did
not pass. ⛔ Had the retrospective analysed only what it was given, it would have reported a confident
*"essentially no operator interaction"* for a plan whose narrative includes two overridden routers,
three scope widenings, a force-removed worktree, and six bare `continue` prods. ⇒ The aspect must
iterate `session_ids`, and a partial read must be labelled as one.

**(2) `signal_qgate_pending_count` carries pending-plus-resolved (inbox `-009`).**
⭐ **The forwarded value is CORRECT and the gate is CORRECT — do not re-derive this as an arithmetic
bug.** Verified first-party against the archived findings store:

| Phase | total | rejected | counted |
|---|---:|---:|---:|
| 2-refine | 1 | 0 | 1 |
| 3-outline | 6 | 1 | 5 |
| 5-execute | 2 | 0 | 2 |
| 6-finalize | 12 | 1 | 11 |
| **Total** | **21** | **2** | **19** |

0 pending + 19 resolved-in-run = **19**, reproducing the forwarded `signal_qgate_pending_count: 19`
exactly. The defect is that a field **named** `..._pending_count` carries pending-plus-four-
resolutions, and the name is the only thing a consumer sees.

⛔ **The harm is measured, not hypothetical.** The `lessons-capture` body that received the value read
the field by its name, computed pending-only (0 across all five phases), and reported 19 as *above
its own arithmetic ceiling* — i.e. impossible. It then found a coincidence that fit perfectly
(`context_load_attribution.total_rows: 19`, nineteen dispatch-boundary rows) and hypothesised the
gate was querying the dispatch ledger. **Two 19s in one run, one a genuine coincidence, and a name
that licensed the wrong reading.** ⇒ Rename the field to what it carries; a comment is not a fix.

## Folded from the PLAN-TRUTH-088 drain (2026-08-24)

**(1) A stale served skill body is indistinguishable from a live contract (inbox `-001`).**
⛔⛔ **This is R84(3) reproduced, and this time it produced a real artifact rather than a near-miss.**
The retrospective loaded `plan-marshall:manage-metrics` from plugin cache **`0.1.1240`**, whose
served `SKILL.md` documents the `record-dispatch-boundary --termination-cause` enum as **six**
values. The live argparse `choices` accepts **twelve**, and the repository's own `SKILL.md` documents
twelve with a contract test that discovers every occurrence.

⭐ **First-party confirmation of the mechanism, taken this session:** the cache holds
`{1240, 1526, 1527, 1538, 1539, 1541, 1542}` and the **unmarked** set is `{1240, 1538, 1542}` — so
`0.1.1240` is unmarked and therefore live to the loader. That is not incidental: it is why this
session's own harness surfaced the **pre-#1162** `marshall-orchestrator` skill names, and why
`lessons-capture` emitted the duplicate landing `-015` from a body that structurally cannot carry a
`landing-facts` block. **One unmarked stale directory, three distinct observable failures in one
day.**

⛔ **The defect is NOT that the cache is stale** — that is the host pin problem, operator-owned. The
defect is that **a served body carries no assertion of its own currency**, so a reader cannot tell a
retired contract from a live one, and a confident finding derived from it is indistinguishable from a
correct one. ⚠ **OWNERSHIP GAP: `restart-check` names `PLAN-TRUTH-059` as the owner of
`registry_parity`, and `-059` has SHIPPED (#1213) — so the surface has no live owner.** Recorded here
rather than staged, but it needs one.

**(2) `exit_code: 2` failure detail prefers stdout over stderr (inbox `-009`).** Small and concrete:
an argparse rejection writes its message to stderr, so a failure detail built from stdout discards
the only part that says what was wrong. ⭐ Same shape as the retired
`argparse-rejection-log-discards-the-only-recoverable-part` item (`PLAN-TRUTH-039`, superseded) —
check that spec's disposition before implementing, so this does not re-open a settled decision.

## Folded from the PLAN-TRUTH-094 drain (2026-08-25) — inbox `-001`, three unowned members

Three group-A findings from PR #1343's run. All three are this epic's purest archetype: **a payload
whose vocabulary cannot express the condition it is reporting**. Each was measured by the plan, not
inferred. They take the spec to **nine** deliverables — within the raised 12-deliverable guard
(operator, 2026-08-08), so no split is triggered; D0's re-grounding gate covers them unchanged.

**D6 — `branch-sync-state` reports `ahead` for a DIVERGED branch.** *(`8d655d`)* After the
sync-baseline rebase, `git merge-base --is-ancestor <remote> HEAD` exits 1, so a plain push is
rejected non-fast-forward. The verb's state set is
`ahead | synced | remote_absent_landed | remote_absent_unverified` — **there is no `diverged` member**,
so a rebased branch is structurally forced into `ahead`. ⛔ The push barrier consumes this state to
CHOOSE AN ACTION, so it picks the wrong one. ⭐ The ancestry data is already in hand at the point of
comparison — this is a missing enum member, not a missing measurement.

**D7 — `ci checks wait` buckets a PENDING check into `failing_checks[]`.** *(`ed23b9`)* On
`deadline_exceeded` it emitted CodeRabbit with `conclusion: PENDING` into an array the api-contract
defines as *"the subset of `checks[]` whose `result` is `failure`"*, with empty `log_file` / `run_id`
because there is no failed job. ⛔ The finalize contract routes `failing_checks[]` to triage, so **a
slow review bot opens a build-failure investigation with nothing to investigate.** Same shape as D6: a
third condition (still running) forced into a two-valued vocabulary.

**D8 — `deploy-target` / `sync-plugin-cache` published a cache one merge STALE, both reporting
success.** *(`0c4569`; also candidate-lessons `-005` and `-006`)* `branch-cleanup` merges via the
platform merge queue, so the merge lands only on `origin/main` and nothing in phase 6 pulls. Local main
sat one commit behind and the generator emitted from a tree missing the plan's own merged changes
(**1176 entries / 0.1.1543** vs **1177 / 0.1.1544** after pulling).

⛔⛔ **The staleness guard cannot catch this BY CONSTRUCTION** — it fingerprints the WORKING TREE and
compares against a sentinel written from that same working tree, so both agree with each other while
both disagree with the merged remote. **It proves emit-vs-sync consistency and never emit-vs-merge
currency.** That is a vacuous guard in the strict sense: its two inputs cannot disagree.

⚠ **This is a SECOND, INDEPENDENT cache-currency mechanism, and it must not be merged with the known
one.** The long-tracked registry-pin gap is *"`/sync-plugin-cache` mints a new cache version and never
re-pins the registry"* — a pin left behind. This one is *"the emit itself ran against a stale tree"* —
a wrong source. Different causes, different fixes; a remedy for either leaves the other live.
⭐ Corroborated at this drain: the pin gate is currently CLEAN (`executor_version` `0.1.1544` ==
`installed_version` `0.1.1544`), which is consistent with this instance having been corrected in-run
and is NOT evidence the mechanism is closed.

## ⭐ FOLDED 2026-08-31 — inbox drain (11 message(s))

- **`disjointness-gate-reads-declared-surface-wrong-003.md`** — The realized-footprint derivation cannot represent a declared delete on a renamed path
- **`disjointness-gate-reads-declared-surface-wrong-004.md`** — reconcile-ledgers' union_rows is not invariant under its own --window-seconds
- **`disjointness-gate-reads-declared-surface-wrong-008.md`** — The Phase Dispatch Boundaries section can never emit, and its absence is classified benign
- **`findings-read-absent-plan-dir-returns-clean-zero-005.md`** — A build whose resolved timeout budget is smaller than its own learned duration can only ever time out
- **`findings-read-absent-plan-dir-returns-clean-zero-006.md`** — create-pr's stamped pr_number survives a close-and-reopen, so the structured fact names a closed PR while the plan lands on another
- **`findings-read-absent-plan-dir-returns-clean-zero-007.md`** — Two disjoint phase populations rendered under an identical (n=k/6) marker print Worked above Wall
- **`findings-read-absent-plan-dir-returns-clean-zero-008.md`** — affected_files is re-derived only on an admitted loop-back, so a mid-execute scope expansion silently under-scopes every affected_files-derived finalize gate
- **`findings-read-absent-plan-dir-returns-clean-zero-010.md`** — The PR-body Intent section is appended by the renderer but positioned third by the template, and its character budget clipped the one non-goal a reviewer most needed
- **`git-artifact-scanning-and-destructive-recovery-002.md`** — A skipped enrichment step must fail closed, not let a matcher run against an empty field
- **`git-artifact-scanning-and-destructive-recovery-007.md`** — Emit the failing verb's live --help on any argparse exit-2 from the executor
- **`git-artifact-scanning-and-destructive-recovery-008.md`** — Make per-deliverable declared-vs-realized coverage a read, not a hand count

⛔ Each is the sending plan's own first-party observation, relayed verbatim by title. **Treat every one as a LEAD** — the drain did not re-derive them, and several were observed against tree states that have since moved. Re-ground at outline.

## ⭐⭐ FOLDED 2026-08-31 — two INBOUND cross-epic messages, drained

### `review-apparatus-022.md` — seven not-ours items from PLAN-PR-025A (#1368), a declared TRANSFER

The sender states plainly: *"they are removed from our ledger and tracked nowhere on our side"* — so
these are ours or they are nobody's. ⛔ **Every item is the sending plan's first-party observation,
RELAYED — review-apparatus did not re-derive them, and neither did this drain.** Leads, not findings.

- **1. `re_entered_phases` reports empty on a plan with three recorded loop-backs.** Believed to be
  the live defect that escaped to main from `PLAN-TRUTH-055` (#1129). ⭐ **The value is the
  RECURRENCE**: a plan with three loop-backs is a stronger reproduction than the original.
- **2. `affected_files` under-records the realized footprint; recorded deviations stay unparseable
  prose.** Recurrence of the 19-vs-37 under-recording. ⚠ Every `affected_files`-derived finalize step
  under-scopes when scope moves during execute.
- **3. ⛔⛔ MERGE-FIFO DEADLOCK WITH A DIAGNOSTIC THAT NAMES NOBODY.** `merge.lock` was FREE while
  `merge_lock acquire` returned `blocked` with `waiting_count: 2` and **`blocking_plan_id: null`**.
  The FIFO head was held by `detector-and-auditor-integrity` with no session polling it; clearing that
  entry released it. ⭐⭐ **This is the mechanism behind `PLAN-TRUTH-090`'s reported blocker** — see
  `landings/PLAN-TRUTH-090.md`, where this orchestrator's own `merge_lock check` probe read `free` and
  wrongly characterised the plan's conclusion as an error. **`check` and `acquire` disagree, and only
  `acquire` sees the FIFO.** A vacuous-diagnostic instance: the field that exists to name the blocker
  is null in the one state where it is needed.
- **4. `merge_commit_sha` would have recorded ANOTHER PLAN'S COMMIT.** switch-and-pull pulled 0 commits
  because `main` had already advanced to a sibling's landing. Caught in-run. ⛔ **An ordering hazard
  that appears only under concurrent landings, and it fails silently — the stamped sha is well-formed
  and wrong.** Directly relevant now that this epic runs at N=3.
- **5.** Project allow-list grants 3 of 6 `project:` finalize-step skills — operational friction.
- **6.** A `manage-lessons housekeeping-classify` verb proposed so the retain partition is *computed*.
- **7.** One invocation rejected seven times in a single run — contract-discovery cost.
- **8.** The executor resolved a pre-#1370 `analyze-logs.py`, so the retrospective **graded itself with
  a retired check** — the stale-cache-as-evidence archetype, explicitly not kept by the sender.

### `token-sheriff-lessons-26-08-31-001.md` — 8 tooling clusters learned in Token-Sheriff

⚠ The sender is explicit that this is **material, not a queue**, that **nothing is registered in any
lessons store**, and that several observations predate current tree states. Clusters 2-8 land in this
repo: generated-artifact staleness gates · claim-before-verification · git/worktree finalize mechanics
· canonical build commands not matching the module · argparse-rejection recurrence · steward executor
version sort · marshalld baseline interpreter. **Cluster 1 (review-bot detection) is review-apparatus's
and was routed there, not kept.**

⛔ **Clusters 2-8 are recorded here as UNOWNED material, not as deliverables of this plan.** Staging
them is a separate decision the operator has not been asked for; folding them in silently would
manufacture scope. See the epic Open Defect.

## ⛔⛔ FOLDED 2026-08-31 (PLAN-TRUTH-090 deferred re-entry) — one new defect, and item 4 reaches n=2

### `4cb145` — worktree-remove does not reconcile the metadata it invalidates

After a **successful** `worktree-remove`, `get-worktree-path` still reports
`worktree_state: materialized` at the **deleted** path. Filed by the `-090` re-entry as a bug,
non-blocking, and explicitly left unfixed because a truthful-signals sibling owns those directories.

Two consequences were observed LIVE, and the first is the one to fix:

- ⛔⛔ **`ci --plan-id … pr view` returns `error_cause: auth_failed` — a FALSE cause.** `gh auth status`
  shows two logged-in accounts, and the identical call with `--project-dir` succeeds. **A
  stale-metadata failure is reported as an authentication failure**, sending a reader to fix
  credentials that were never broken. This is the epic's theme exactly: a confident, specific,
  wrong cause is worse than an unclassified error.
- `phase_handshake verify` refuses with `worktree_unresolved`.

⭐ It also **REFUTES a documented claim**: `branch-cleanup.md` line 80 says `--plan-id` *"keeps
working post-removal"*. That sentence relies on a `use_worktree=false` fallback **which removal never
sets**. The doc and the code disagree, and the doc is wrong.

⚠ **Cross-epic:** `review-apparatus` lists the `ci pr view` `auth_failed` misclassification among the
items it KEPT from PLAN-PR-025A. **This is its root cause** — the two ledgers hold the same symptom
from opposite ends, and neither can see the other's half. Tell them rather than fixing it twice.

### ⭐⭐⭐ `merge_commit_sha` stamping ANOTHER PLAN'S COMMIT is now n=2, TWO EPICS, TWO PLANS

The `review-apparatus-022` item 4 folded here earlier the same day reported this from PLAN-PR-025A's
landing. The `-090` re-entry hit it **independently** hours later: `branch-cleanup` prescribes
`rev-parse HEAD`, which assumes the SYNCHRONOUS path where HEAD is the landing commit; on a **deferred**
re-entry `main` had advanced to `7845a4b9a` (sibling PR #1370). The run recorded `8bc4a68f6` instead,
corroborated against `ci pr view`'s own `merge_commit_sha`.

⛔ **It fails SILENTLY — the stamped sha is well-formed and wrong**, and it seeds the footprint
fallback with another plan's diff. ⛔ **It appears only under concurrent or deferred landings**, which
is the regime this epic now runs in at N=3. ⇒ **Two independent reproductions across two epics is no
longer a lead; size it as a defect with a known trigger.**

### Deviation: a two-step verb whose first failure skips its independent second step

`prune-local-and-remote-ref` returned `branch_delete_failed` because `worktree-remove` had already
deleted the local branch — and therefore **never reached the remote half**, leaving a stale
`refs/remotes/origin/feature/…` behind. The two halves are independent; the first failing should not
skip the second.

---

## Superseded By

⛔ **This spec is SUPERSEDED by `PLAN-TRUTH-155-agent-facing-documentation-surfaces-and-the-live-plan-defect-sweep.md` (PLAN-TRUTH-155)**, recorded 2026-09-12 under the operator directive to group plans by shared target at a ceiling of 12 deliverables. It is retained in full as the audit record of why it was retired and as the authority its successor's `## Claim Labels` section POINTS at — the successor deliberately does not restate these claims, so **this document is where they are re-derived from**. Do not implement from this spec; implement from its successor.
