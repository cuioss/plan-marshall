# Landing analysis — PLAN-TRUTH-126

**Plan:** `shipped-guards-assume-the-meta-projects-own-layout`
**Spec:** `plans/PLAN-TRUTH-126-shipped-guards-assume-the-meta-projects-own-layout-and-go-vacuously-green-elsewhere.md`
**PR:** #1397 · **Merge commit:** `28b578f1e` · **Workstream:** WS-01

## Merge corroboration — first-party, NOT taken from the landing message

⛔ The landing message reports `merge_state=unknown` and **correctly refused to substitute a
corroboration it did not have.** The merge is established here instead, from two independent reads:

| Source | Result |
|---|---|
| `git log main` | `28b578f1e fix(phase-6-finalize): make meta-project-only guards fail visibly (#1397)` is the **tip of main** |
| `ci pr view --pr-number 1397 --project-dir <main>` | `state: merged`, `merge_commit_sha: 28b578f1ed435973e53c510f0c8225446cc024aa` |
| `manage-status list` | the plan is **absent** from the live store |
| `.plan/local/archived-plans/` | `2026-09-05-shipped-guards-assume-the-meta-projects-own-layout` present |

⭐ **The refusal was right and the epic should not "fix" it by making the producer guess.** A landing
that says `unknown` and a landing that says `merged` on no evidence are not equally wrong — only the
first is recoverable, and it is recoverable exactly the way it was recovered here.

## Deliverable fidelity

**6 of 6 shipped**, and the spec's own ordering constraint was honoured: deliverable 1 (classify the
layout assumptions) gated the rest, so no site was converted before the classification recorded which
were defective and which were legitimate own-source resolution.

| # | Deliverable | Verdict |
|---|---|---|
| 1 | Classify meta-project layout assumptions | shipped — the gate |
| 2 | Report an unresolvable footprint path instead of dropping it | shipped |
| 3 | Dispose of every residual shape-B site the partition names | shipped |
| 4 | Invoke the architecture-resolved executable in the pre-push arms | shipped |
| 5 | Record an un-run dimension in the finalize step's own verdict | shipped |
| 6 | Pin the class with population-derived tests | shipped |

## ⛔⛔ The headline finding is one the operator report did NOT disclose

**67 firings across 23 recorded steps, headlined `23/23`. Nine steps re-fired.** Derived from the
archived `status.json` `metadata.phase_steps["6-finalize"]`, per the standing rule that the archived
record is read on every full-ship drain — the log line and the report are both terminal-state views.

| Step | `firing_count` | prior outcomes |
|---|:-:|---|
| `pre-submission-self-review` | **15** | **12 of 14 `failed`** |
| `pre-push-quality-gate` | 6 | all `done` |
| `project:finalize-step-plugin-doctor` | 6 | all `done` |
| `ci-verify` | 6 | all `done` |
| `automatic-review` | 6 | one **`loop_back`**, rest `done` |
| `project:finalize-step-lessons-housekeeping` | 4 | all `done` |
| `finalize-step-simplify` | 4 | all `done` |
| `push` | 4 | all `done` |
| `lessons-capture` | 2 | `done` |

⭐ **The report was honest where it spoke** — it disclosed the self-review budget exhaustion verbatim
(*"out of budget: 12 rounds, 26 findings fixed, last round NOT clean"*), and the record corroborates it
harder than the headline reads. ⚠ **But `23/23` is a step roster, not a work count**, and the 44
un-headlined re-firings are invisible in it. **This is R63's archetype recurring** — the same shape
recorded at PLAN-TRUTH-075 (29 firings across 22 steps headlined `23/23`, one re-fire disclosed).
⇒ **Second independent instance. The disclosure surface, not the runner, is what has not moved.**

## Findings CORROBORATED first-party

### 1. `ci pr view --plan-id` misclassifies a dead cwd as `auth_failed` — CORROBORATED, and it OUTLIVES the run

The archived record still carries the defect, which is what makes it more than a transient:

```text
metadata.use_worktree   = True
metadata.worktree_path  = .plan/local/worktrees/shipped-guards-assume-the-meta-projects-own-layout
directory exists on disk = False          <- removed by branch-cleanup at order 70
```

⇒ The `--plan-id` arm resolves `cwd` through a path that no longer exists, `gh` cannot start, and the
failure is funnelled into the `auth_failed` arm. **Proof by control reproduced here:** the same call
with `--project-dir <main>` returns `state: merged`. ⛔ **The cost is the renderer's mapping
`auth_failed → [FAILED]`, so every worktree-using plan renders as FAILED after a successful merge.**
Finding `866bcd`, inbox `-007`.

### 2. `branch-cleanup` records NO facts at all — sharper than reported

The report says *"branch-cleanup records no `merge_state` fact"*. The record says more: its
`phase_steps` entry carries **only `outcome` and `display_detail`** — `facts: {}`. It records **no
typed fact whatsoever**, so `merge_state` is not a missing key in a populated map, it is an empty map.

⭐ **And the producer already exists**: `ci pr view` returns `state: merged` plus a
`merge_commit_sha`. The gap is wiring, not observation. ⚠ Note the field-name collision — `ci pr view`
ALSO returns a `merge_state` field, which is GitHub's *mergeability* status and is `unknown` for every
merged PR. **The landing payload's `merge_state` must be fed from `state`, never from that field.**

### 3. `uv.lock` is dirty on main — but it is a REPAIR, not drift

The report frames this as a stray relock. **The corroboration inverts the framing:** `#1417`
(`b90185b4c`, dependabot) changed **`pyproject.toml` only — 1 file, 1 line** — moving the ruff
requirement to `>=0.16.5` **without relocking**. Main therefore landed inconsistent: the constraint
demanded `>=0.16.5` while `uv.lock` pinned `0.16.4`.

⇒ The uncommitted `0.16.4 → 0.16.6` relock (20 insertions / 20 deletions, ruff only) is **the repair
main needs**, stranded. **Two defects remain, and neither is "the lock file is wrong":**
a step declaring `mutates_source: false` mutated source, and it did so past the merge gate with no
push path left. Finding `3d8e95`. ⚠ **The content is correct and should be committed, not reverted.**

### 4. The orchestration verdict was wrong mid-run, and the plan caught it itself

`phase-6-finalize` Step 3 item 4b.a0 requires the dispatcher to resolve orchestration ONCE and forward
it. The verdict `orchestrated: false` / `epic: ""` survived a context compaction and reached
`lessons-capture`, which took Branch A (global corpus) where the contract required Branch B4 (epic
inbox, zero `manage-lessons add`). ⭐ **Corrected in-run**: re-emitted as inbox `-003` / `-004` with
dedup notes naming their global twins, and the globals were **left in place rather than destroyed** —
correct, given the known `manage-lessons remove` destroy-while-reporting-`not_found` defect.

⭐⭐ **The residue is the sharpest part and is inbox `-005`'s:** `emit-landing`'s presence in the
composed manifest was **already persisted independent evidence of orchestration**, and no runtime
consumer cross-reads it. A second, disagreeing signal existed and nothing compared them.

## Reconciliation actions

- Queue: `PLAN-TRUTH-126` → `shipped`; `pr` = `1397`; `landing` = `landings/PLAN-TRUTH-126.md`;
  `plan_marshall_plan_id` = `shipped-guards-assume-the-meta-projects-own-layout`.
- Inbox: 7 messages from this sender dispositioned in the same drain (2 findings, 4 candidate-lessons,
  1 landing). `landing-check` returned `complete: false` with **exactly one** missing key
  (`merge_state`) — **the most complete landing this epic has drained**, and the single gap is the one
  the run deliberately declined to fabricate.
- Capacity: R 3 → 2 of N=3. **One slot frees.**

## Parallelization consequences

No collision was observed between this plan and the two that ran beside it (`-089`, `-093`), and none
was predicted. ⚠ **`-093` regressed `6-finalize` → `5-execute` during this window** — a loop-back, not
a collision; recorded so a later reader does not read the phase movement as contention.

## Open items this landing leaves

| Item | Owner |
|---|---|
| `ci pr view --plan-id` dead-cwd misclassification (`866bcd`) | folded to `PLAN-TRUTH-129` |
| `branch-cleanup` emits no facts; `merge_state` unwired | **UNOWNED** — recorded as an Open Defect |
| `uv.lock` repair stranded, `mutates_source: false` violated (`3d8e95`) | **UNOWNED** — recorded as an Open Defect |
| dispatcher forwarded `orchestrated: false`; manifest evidence never cross-read | folded to `PLAN-TRUTH-110` |
| plugin-doctor `scan_manage_invocation` root-dependent false positives (`cb3735`) | folded to `PLAN-TRUTH-112` |
| `23/23` headline hides 67 firings — 2nd instance | **UNOWNED** — recorded as an Open Defect |

## Metrics

36h5m wall / 10h12m worked / **25h52m idle (72%)** · 11,892,145 tokens · 2710 tool uses ·
144,465,076 billing weight.

⛔ **Every figure above is a FLOOR and the report says so.** `enrich` attributed **2 of 6 phases**
because the plan spans two sessions and `enrich` takes one session id; the token total is `n=5/6` and
the billing weight `n=2/6`. ⭐ **The report publishing its own coverage denominators is the behaviour
this epic asks for** — the figures are unusable as totals and honest as floors, and only the published
`n` makes that distinguishable.

⚠ The 72% idle share is consistent with the stopping-defect measurements already recorded
(`-075` 81%, `-095` 62%) and is `PLAN-TRUTH-107`'s cost case, not this plan's defect.
