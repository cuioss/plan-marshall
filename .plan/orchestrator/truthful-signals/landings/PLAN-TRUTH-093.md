# Landing analysis — PLAN-TRUTH-093

**Plan:** `preference-admissibility-prose-vs-auditor-code`
**Spec:** `plans/PLAN-TRUTH-093-preference-admissibility-is-prose-where-the-auditor-has-code.md`
**PR:** #1398 · **Merge commit:** `d94c92858` · **Workstream:** WS-01

## Merge corroboration — first-party, NOT taken from the landing message

⛔ The landing reports `merge_state=unknown` and **again refused to substitute a corroboration it did
not have**, carrying the observation in its `## Residue` instead. Established here independently:

| Source | Result |
|---|---|
| `git log main` | `d94c92858 fix(admissibility): enforce authorship gate in code, not prose (#1398)` is the **tip of main** |
| `ci pr view --pr-number 1398 --project-dir <main>` | `state: merged`, `merge_commit_sha: d94c928580d9ab55a43b525273274ce4b39e0944` |
| `manage-status list` | the plan is **absent** from the live store |
| `.plan/local/archived-plans/` | `2026-09-05-preference-admissibility-prose-vs-auditor-code` present |

⭐ **Second consecutive landing to refuse the fabrication.** Two runs, two days, same discipline — this
is now the epic's observed norm rather than one run's carefulness.

## Deliverable fidelity

**4 of 4 shipped**, and the plan's structure honoured its own gate: deliverable 1 re-derived the three
grounding premises against HEAD **before** deliverables 2–4 moved anything. The auditor's observable
behaviour and its existing filter tests were preserved unchanged, as the spec required — so the
predicate moved home without the move being observable to its callers.

| # | Deliverable | Verdict |
|---|---|---|
| 1 | Re-derive the three grounding premises against HEAD | shipped — the gate |
| 2 | Move the predicate to a shared home; auditor delegates | shipped |
| 3 | Give the emitter an executable gate, retire the prose | shipped — **the plan's whole point** |
| 4 | State the write-time `bot_kind` guard's two halves in one place | shipped |

⭐⭐ **The shipped subject is this epic's thesis in miniature**: a rule enforced structurally at one
surface and *asked for as prose* at another is not one rule with two homes — it is one rule and one
hope. D3 replaced the hope with a call.

## ⛔⛔ Re-firing: 75 firings across 23 steps, headlined `23/23` — THIRD INSTANCE

Derived from the archived `phase_steps["6-finalize"]`. **Ten steps re-fired.**

| Step | firings | prior outcomes |
|---|:-:|---|
| `pre-submission-self-review` | **12** | **7 CONSECUTIVE `failed`**, then 3 `done` |
| `project:finalize-step-plugin-doctor` | 7 | all `done` |
| `finalize-step-simplify` | 7 | all `done` |
| `lessons-housekeeping` / `pre-push-quality-gate` / `push` / `era-stamp-fill` / `ci-verify` | 6 each | all `done` |
| `automatic-review` | 4 | all `done` |
| `lessons-capture` | 2 | `done` |

⭐ **The report disclosed this one** — *"pre-submission-self-review fired 12× with 7 consecutive
failures, six other steps 6–7× each"* — and the record confirms it exactly. ⇒ **The disclosure improved
between `-126` and `-093`**; what has not moved is the `23/23` headline that still sits above it.

**The series is now three:** `-075` 29/22, `-126` 67/23, `-093` **75/23**. ⛔ The trend is upward and the
headline is constant.

## Findings CORROBORATED first-party

### `branch-cleanup`'s missing facts — SECOND instance, and sharper than yesterday's

Yesterday's Open Defect recorded `facts: {}`. This record says something more precise: the entry
carries `['outcome', 'display_detail', 'head_at_completion']` — **no `facts` map at all, yet a
fact-shaped value (`head_at_completion`) written OUTSIDE it.**

⇒ **The step is not fact-blind; it is writing a fact where no typed consumer reads.** That reframes the
fix: not "start recording facts" but "record through `--fact`, and move the one value already being
captured into that channel." The operator's own prescription — *"record `merge_state` via `--fact`"* —
is right, and `head_at_completion` should ride with it.

### The dead `worktree_path` persists — SECOND instance

`use_worktree: True` with a `worktree_path` that does not exist, in the archived record, exactly as in
`-126`. ⇒ **`866bcd`'s persisted-state half is reproducible, not incidental**, and it is what makes
`ci pr view --plan-id` unusable after any landing.

### `uv.lock` — the chain of custody is now CLEAN, and it closes yesterday's open question

The report states the dirty file *"was already modified in the main checkout before finalize touched
it; no plan step wrote it."* ⭐⭐ **That is corroborated by construction**: this epic recorded the same
file dirty on 2026-09-05 from `-126`'s run, before this plan's finalize began. ⇒ **Two runs agree on
custody: `-126` produced it, `-093` inherited and correctly disclaimed it.**

⛔ **It is still uncommitted, and it is still the repair main needs** — `#1417` moved `pyproject.toml`
to ruff `>=0.16.5` without relocking. **The defect is now age, not authorship.**

## ⚠ A count in the report does not reconcile with the inbox

The report closes: *"Four inbox messages reached epic `truthful-signals`: three candidate-lessons from
the retrospective (`-007`/`-008`/`-009`) and the landing (`-010`)."*

**`inbox list` enumerates TEN from that sender — `-001` through `-010`.** The report's own step line
says it: `lessons-capture … 6 inbox message(s) to epic truthful-signals`. 6 + 3 + 1 = 10.

⇒ **The closing count silently dropped the six `lessons-capture` had already filed, while a line
earlier in the same report named them.** ⛔ Not a transport failure — every message arrived and every
one drained. It is a **count-vs-enumeration divergence inside one report**, which is this epic's
archetype turned on the report itself. ⭐ Recorded because a drain that had trusted the closing count
would have left six messages unread with no signal that it had.

## Reconciliation actions

- Queue: `PLAN-TRUTH-093` → `shipped`; `pr` = `1398`; `landing` = `landings/PLAN-TRUTH-093.md`.
- Inbox: 11 messages drained (10 from this sender + 1 from `code-intelligence-substrate`).
  `landing-check`: `complete: false`, `missing_keys: [merge_state]` — **one key, same as `-126`.**
- Capacity: R 2 → 1 of N=3. **Two slots free.**

## Parallelization consequences

No collision observed or predicted with `-089`, which ran beside it throughout. ⚠ `-089` moved from
`location: worktree` to `location: current` during this window — a location change, not a phase change;
recorded so it is not read as contention.

## Open items this landing leaves

| Item | Owner |
|---|---|
| `branch-cleanup` writes a fact outside `facts`; `merge_state` unwired | Open Defect — **UNOWNED**, sharpened |
| `23/23` hides 75 firings — third instance | Open Defect — **UNOWNED**, series updated |
| `uv.lock` repair stranded and ageing | Open Defect — **UNOWNED**, custody now established |
| report's closing message count vs the enumeration | Open Defect — **UNOWNED**, new |
| the eight substantive candidate-lessons | folded / forwarded — see the drain record |

## Metrics

69h41m wall / 8h3m worked / **34h58m idle** · 12,067,640 tokens · 2520 tool uses ·
149,214,666 billing weight.

⛔ **Floors, and the report says so**: token/tool/idle totals are `n=5/6` phases and the billing weight
`n=1/6`. ⚠ **`6-finalize`'s idle cell is empty rather than zero** — the boundary-monotonicity warning
fires because a finalize loop-back re-enters an earlier phase, so the residual is guarded rather than
computed. ⭐ **That is the instrument declining to publish a number it cannot derive**, and it is the
correct behaviour; do not "fix" it by filling the cell.

⇒ **77% of the spend sits in `6-finalize`, and the re-fire table above says why: it is re-firing, not
implementation.** That is `PLAN-TRUTH-107`'s cost case gaining a third measured instance.
