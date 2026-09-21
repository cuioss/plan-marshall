# Landing Analysis: PLAN-TRUTH-011 — Provider & Shared-Logging Path/Boundary Containment

epic: truthful-signals
workstream: WS-01
pr: #1123 — https://github.com/cuioss/plan-marshall/pull/1123

> Reconciled at the PLAN-TRUTH-049 analysis, not from an operator paste. The landing was
> discovered by corroborating `origin/main` while verifying #1125, and the narrative was
> read from the plan's own inbox landing message (`provider-logging-path-containment-009.md`).
> Every material claim was checked against the real diff before being recorded.

## Ground-Truth Corroboration Performed

| Claim | Verdict | Evidence |
|---|---|---|
| PR #1123 merged | corroborated | `ci pr view --pr-number 1123` → `state: merged`, head `feature/provider-logging-path-containment` |
| Landed as `38f45faeb` | corroborated | `git log origin/main` — `38f45faeb fix(manage-logging): contain client plan_id at shared log path boundary (#1123)` |
| Worktree removed | corroborated | `manage-status list` — plan absent from live plans |
| **~700 lines of unspecified scope landed under this PR** | **corroborated exactly** | `git show --stat 38f45faeb` — `_analyze_literal_count.py` **+412** and `test_analyze_literal_count.py` **+289** = **701 lines**, plus `rule-catalog.md`, `rule-provenance.md`, `execute-script.py.template` |

## Deliverable Fidelity vs Spec

| Deliverable | Verdict | Evidence |
|---|---|---|
| Guard the shared log-path choke point | **shipped-modified, and the modification corrected the request's framing** | `plan_logging.py` (+41) — `get_log_path` now runs the caller-supplied `plan_id` through `is_valid_plan_id` **before resolving any path**. The guard sits at the resolver, not at the two originally-reported call sites, because all seven entry points route through it. ⭐ Outline-time root-cause work found the gap was **not "two unvalidated call sites" but an asymmetry inside one function** — per-caller validation covered four of seven entry points, with `log_script_execution` worst (it extracts `plan_id` from raw argv before argparse runs) while the sibling `orchestrator` branch was already contained by `_reject_unsafe_entry_id` |
| Promote four landed containment lessons into one durable rule | shipped-as-specified | `persona-security-expert/standards/input-validation-trust-boundaries.md` (+19) |
| Narrow the Q-Gate worktree linter's WL-C check | shipped-as-specified | `plan-marshall/workflow/q-gate-validation.md` (+20), `test_q_gate_validation_worktree_linter.py` (+329) |
| — | **added-unplanned** | `_analyze_literal_count.py` (+412) + its test (+289): a **new plugin-doctor capability with no plan spec behind it**, entered via a finalize-time loop-back |

Two ADRs landed: **ADR-016** (containment of a caller-supplied identifier belongs at the shared
resolver, not at each entry point) and **ADR-017** (a validator derives its contract from the target's
own declaration and fails closed when it cannot).

## Metrics and Anomalies

- Q-Gate pending findings at finalize: **0**. Script-failure clusters: **0**.
- Automated review: 2 reviewers compared, 14 actionable comments; 9 remediated in-run, 6 accepted
  without change (bot summaries, "already reviewed" chatter, one declined Sourcery spelling nit —
  `modelled` is the established spelling across 9 files).
- Pre-submission self-review: 5 findings across 3 passes; simplify 5 edits / 2 findings; security-audit
  1 regression / 2 findings.
- **One loop-back from `6-finalize` to `5-execute`** (2026-08-08T21:08:09Z) — and that loop-back is
  where the 701 unplanned lines entered.

## Routing and Merge Behavior

- Merged to main via the merge queue as `38f45faeb`; branch and worktree removed.
- No rebase conflicts or re-verify signals recorded. No collision with the two plans running alongside
  it (`-049` on the plugin-cache surface, `-055` on `manage-metrics`) — the disjointness call held.

## Reconciliation Actions

- [x] row `status` → `shipped`
- [x] row `pr` stamped — `1123`
- [x] row `landing` stamped — `landings/PLAN-TRUTH-011.md`
- [x] row `plan_marshall_plan_id` stamped — `provider-logging-path-containment`
- [x] epic.md queue reconciled from status.json
- [x] Open Defects opened for residue 1–3 below
- [x] START-HERE block regenerated

---

## Amendment — operator landing narrative received after this record was written (2026-08-09)

This record was originally written from the plan's own inbox landing message, discovered by
corroborating `origin/main`. The operator's fuller narrative arrived afterwards. **It corrects one
finding of mine and adds four the inbox message did not carry.** Nothing below duplicates the record
above; where the two disagree, the correction is stated as a correction.

### ⛔ CORRECTION TO MY OWN FINDING — the plugin-doctor analyzer was an OPERATOR-APPROVED scope deviation

Above, and in the Open Defect I opened from it, I recorded the 701 unplanned lines as scope admitted
through a finalize-time loop-back and framed it as a governance question about unsanctioned additions.
**That framing was wrong in its load-bearing half: the operator approved the deviation.** It was a
sanctioned scope extension, not a loop-back slipping work past the spec.

**What survives the correction, and it is the part that matters:** the approved work still appears in
**no deliverable's `affected_files`**. ⇒ *approval is not recording.* An operator can widen scope
legitimately and every `affected_files`-derived finalize step still under-scopes, because the widening
was never written back into the manifest. **That is a strictly better finding than the one I filed** —
it survives the "but it was authorised" objection that would have killed the original.

⭐ Recorded against myself: I inferred *unsanctioned* from *undeclared*. **A missing declaration is
evidence about the record, not about the authorisation.** Same class as C2 (an explanation that fits an
observation is not the explanation that produced it).

### ⛔ NEW — the plan introduced a regression in its own fix, and the review apparatus caught it twice

The new `get_log_path` raise was evaluated **in an argument position outside the executor's
fire-and-forget handler**. A malformed `--audit-plan-id` would therefore have **crashed the executor
after a build ran, replacing its exit code with 1 and dropping the ledger row.** Caught by the
security-audit step, then **widened to `OSError` after CodeRabbit found the guard still too narrow**.

⭐⭐ **This is the containment archetype turning on its author**: a plan whose entire subject is
"contain a caller-supplied value at the choke point" introduced an *uncontained raise* at a different
choke point. And it needed **two** independent catches — the first fix was still too narrow. The
vacuous-guard-reintroduced-by-its-own-fix archetype now has a sibling: **guard-introduced-by-a-guard-plan
is itself unguarded.**

### ⛔ NEW — `adr-propose` declares no `mutates_source`, so the dispatcher strands its own ADRs

ADR-016 and ADR-017 had to be **recorded and committed by hand**: `adr-propose` declares
`mutates_source: false`, so the dispatcher would have written them into a worktree that was about to be
deleted. The plan filed this as a finding. ⇒ **a step that produces a durable artifact while declaring
it mutates nothing loses the artifact**, and loses it silently at worktree-removal time — the loss is
invisible because the step reports success. This is the same declaration-versus-behaviour shape as the
lessons-housekeeping defect above, in a second step.

### ⛔ NEW — the metrics disagree with themselves, on PLAN-TRUTH-055's exact surface

`metrics.md` totals **5.6M tokens**; the retrospective found the **dispatch ledger sums differently**,
and flagged **`5-execute` carrying three inconsistent totals**. The retrospective also found **three
defects in its own machinery**. ⇒ **this is a live, independent reproduction of PLAN-TRUTH-055's
subject** (`the-metrics-record-cannot-represent-a-re-entered-phase`), which is RUNNING right now. It is
not new work — it is corroboration that arrived while the owning plan is in flight, and it raises that
plan's population.

### ⚠ CHECKED AND NOT CORROBORATED — the `uv.lock` staleness claim, as worded

The narrative reports: *"main's lock appears stale against the landed ruff bump — worth a separate
PR."* **Checked first-party against `origin/main`:**

- the ruff bump `d5dcf900c` (#1097) changed **`pyproject.toml` only**;
- `uv.lock` was last updated by `4fde77e6f` (#1113), which is **after** it;
- the lock's ruff entry reads specifier `>=0.16.1` and **resolves `0.16.2`** — consistent with the bump
  on both the specifier and the resolution.

⇒ **The lock is NOT stale against the ruff bump.** The underlying observation — that `uv.lock`
regenerates on every build and was reverted each time — is plausible and is **recorded as an unverified
lead**: ordinary re-resolution drift against newer releases is a different thing from staleness against
#1097, and it would need a separate PR for a different reason. ⭐ Reverting it on a logging PR was the
right call either way; only the stated justification does not hold.

### Recorded, no action taken here

- **The push freshness gate was force-overridden once**, recorded honestly in `decision.log`. Not
  source drift: all four gates were green on that exact source tree and the digest mismatch was the
  reverted lock. ✅ Accepted as recorded — the honest log entry is what makes it acceptable.
- **A plugin-cache version split was live during the run**: one subagent read its workflow from
  `0.1.1240` while the installed version was `0.1.1304`. **Two versions in one run, 64 apart.** Folded
  into the pin/orphan Open Defect — and note it is the *same* `0.1.1240` that has been the unmarked
  stale dir in prior incidents.
- **`pr-agent`, the one required bot, reported "no major issues" on a diff where CodeRabbit and
  Sourcery found real defects.** ⇒ **the required-bot quorum was satisfied by the bot that found
  nothing**, twice in two consecutive plans (#1122 the same shape). **PR/review subject ⇒ routes to
  `review-apparatus`, not here.**

## Follow-Ups — the residue the plan itself flagged

1. **⛔ A finalize-time loop-back added a new CAPABILITY, not a fix to the declared one.**
   `_analyze_literal_count.py` is a genuinely new plugin-doctor analyzer that entered through the
   loop-back and appears in **no deliverable's `affected_files`**. The `execute-script.py.template`
   edit is well-motivated (it contains the newly-raisable `invalid_plan_id` at the executor ledger call
   site); the analyzer is not. **The epic owes a decision: should a finalize-time loop-back that adds a
   new capability be admitted at all, or forced back through a spec?** → recorded as an Open Defect; it
   is a governance question the ledger cannot resolve alone, so it is surfaced rather than decided.
   ⭐ This is also the second independent instance of `affected_files` under-recording (the first cost
   PLAN-CIS-001 a 19-vs-37 gap) — **it folds into PLAN-TRUTH-057**, which owns the declared side.
2. **⛔ The plan did not perform its own declared lesson retirement, and the green line says otherwise.**
   Six source lessons were owed. `finalize-step-lessons-housekeeping` reported *"0 removed, 0 promoted,
   0 adapted, 1 retained — 6 carried lessons pre-retired concurrently"*. The obligation was satisfied by
   a **concurrent run**, so the green housekeeping line is **not evidence this plan did the retiring**.
   ⭐ This is the epic's own theme, filed against the epic's own machinery: a confident signal hiding a
   caveat. → folded into the epic's Open Defects.
3. **An unconfirmed hypothesis was carried and never resolved, and now has no owner.** The
   "logging-escape probes written into the permanent work log" observation (PR #1034) was carried
   explicitly as a non-deliverable for outline-time re-verification. Nothing in the landed diff
   addresses it. → recorded as a Watch.
4. **`build_queue.py` FIFO-ordering defect remains out of scope**, extracted to PLAN-66 as declared —
   pointer preserved so the epic does not lose it.
