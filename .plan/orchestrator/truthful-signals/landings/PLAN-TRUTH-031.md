# Landing: PLAN-TRUTH-031 — finalize step records are prose, not facts

**PR**: #1076 — merged as `a83d575cc` (**corroborated against `origin/main`**)
**Plan id**: `finalize-step-records-are-prose-not-facts` · **Emitted**: 15 messages (1 landing + 13 candidate-lessons + 1 finding)

## Deliverable fidelity — 4/4, and D1 found a root cause this orchestrator could not

- **D0** — `ext-point-finalize-step.md` gains a `records_facts` frontmatter obligation, derived per-step
  from real consumer questions rather than a uniform template. ⭐ **Set-valued with a stated delta rule**:
  the declaration is the UNION over a step's terminal `mark-step-done` call sites; each site records only
  the honest SUBSET. Guarded in **both directions** — no-orphan-declaration (existential) and
  no-undeclared-record (universal). That is the *control assertion* discipline applied to a schema.
- **D1 — the classifier fixed at its TRUE root cause.**
  `workflow-integration-git/scripts/git-workflow.py::cmd_worktree_rebase_to` returned `action: rebased`
  **unconditionally on `rc == 0`** in the `ahead` state, even when the rebase replayed **zero commits**.
  It now derives `action` from a **pre/post HEAD SHA comparison**, emits `pre_sha` / `post_sha`, and a
  zero-replay rebase reports `action: noop`.
- **D2** — `mark-step-done` gains a repeatable `--fact key=value` surface persisted as a `facts` map,
  with `invalid_fact` rejection (echoing `offending_token`) **before any write**. `sync-baseline`,
  `branch-cleanup` and `sonar-roundtrip` are wired to populate it. `display_detail` keeps its contract and
  now **renders from** the facts rather than solely holding them.
- **D3** — `test_step_records_facts_contract.py`, 9 assertions: **1–7 population-derived** over the
  discovered step population, 8–9 **labelled** targeted anchors. Plus rebase-classifier tests verified to
  fail pre-fix.

⭐ **The spec's verify-first clause did its job.** It warned: *"check whether `baseline-reconcile`'s own
return carries the correct distinction and only the display drops it … read the implementing source
before aiming the fix."* The plan read the source and found the real site was **`git-workflow.py`, not
`baseline-reconcile`** — the fix would have been aimed at the wrong file otherwise. This is the
*a corrective is a hypothesis until the named site is read* rule paying out.

## ⛔ Consequence for this ledger: a corpus figure of ours is now KNOWN-WRONG, not merely unverifiable

This orchestrator measured **39 of 39 archived `sync-baseline` records reading `action=rebased`, never a
noop**, and recorded it as evidence the early rebase always did real work. **D1 identifies exactly why
that reading was contaminated**: every `ahead`-state rebase that replayed zero commits was stamped
`rebased` unconditionally.

⇒ The Watches entry is upgraded from *"unverifiable"* to **"known-wrong in a stated direction"**: the
true noop count was **≥ 2 and is otherwise undeterminable** for pre-#1076 plans, because the field could
not express it. ⚠ **Post-#1076 the field is trustworthy; the archived corpus is not.** Any future
finalize-cadence measurement must treat pre-#1076 `action` values as unusable rather than as data.

## First-party corroboration of three of our own findings

- **`[STEP] Executing` markers are absent for `lessons-capture` and for head-advance re-fires** (msg 010)
  — independently confirms the blocking caveat this orchestrator derived from the archived corpus (33×
  `sync-baseline` vs 1× `sonar-roundtrip` across 39 plans). **Marker absence is confirmed not to mean the
  step did not run.**
- **`generate_executor preflight` reports `fresh` while the skill loader runs three versions stale**
  (finding 001) — first-party confirmation of the **1240-vs-1275 split observed in this session**, and of
  the standing plugin-registry-pin defect. ⛔ **`preflight: fresh` is not evidence the session's skills
  are current.**
- **`record-dispatch-boundary` accepts termination causes `SKILL.md` does not document** (msg 011) — a
  second sighting; already folded onto `PLAN-TRUTH-012`, recurrence recorded rather than re-filed.

## Reconciliation actions

- Queue `running → shipped`; `pr=1076`, `landing`, `plan_marshall_plan_id` stamped.
- **Surface released**: `phase-6-finalize` standards, `workflow-integration-git`, `manage-status`.
  ⚠ **The conditional collision with running `PLAN-TRUTH-010` never materialised in a harmful way** —
  D2 *did* touch `manage-status` (the `--fact` surface), so the branch this orchestrator flagged at emit
  was taken. **TRUTH-010 must re-ground against `mark-step-done`'s new `--fact` surface before it lands.**
- **R drops 2 → 1.** One slot free.
- ⭐ **`PLAN-TRUTH-032` gains first-party support**: msg 013 reports the merge-queue Monitor *"notifies per
  poll, not per state transition"* — a live instance of the waiter/notification design this plan governs.

## ⛔ Owed

Post-merge PR revisit on **#1076**, and still outstanding on **#1075**.
