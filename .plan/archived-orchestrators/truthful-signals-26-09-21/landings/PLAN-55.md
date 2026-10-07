# Landing Analysis: PLAN-55 — Orchestration inbox channel (producer half)

epic: truthful-signals
workstream: WS-01
pr: #1016 (merged; main at `f8465bf`)

> Landing record. **This is the first plan whose landing was partly delivered through the channel it
> shipped** — three inbox messages were read first-party from
> `.plan/local/orchestrator/truthful-signals/inbox/` before this record was written.

## Deliverable Fidelity vs Spec

5/5 shipped; 21/21 finalize steps; 12748 tests green; metrics `partial: false`, all six phases.

| Surface | Verdict |
|---|---|
| `orchestrator inbox` verb group — `write` / `validate` / `detect` | shipped-as-specified. `write` allocates the per-sender sequence with an **atomic `O_CREAT\|O_EXCL` claim**, derives the path from the validated epic slug + `--sender-id`, and **accepts no caller-supplied output path** — the containment property is structural, not checked |
| `standards/inbox-envelope.md` | shipped — `key=value` header + markdown payload, six required fields, **fail-closed `envelope_version`**, `landing`/`finding`/`candidate-lesson` enum, four invariants (append-only, one-file-per-message, own-file-only, one-way) |
| `lessons-capture.md` Branch B4 | shipped |

**It dogfooded itself, on live traffic.** PLAN-55 is itself an orchestrated plan; at `lessons-capture`
the shipped capability detected its own orchestration context via `inbox detect`, took B4, and wrote
**3 messages with zero global-lessons-store writes**. D2/D4 are verified against production behaviour,
not only tests. Verified first-party: 1 `landing` + 2 `candidate-lesson`, correct envelopes, correct
per-sender sequence (`-001/-002/-003`).

## ✅ The judgement call: the 3 inbox files STAY

**Decision: keep them.** Reasoning, since the plan's own `request.md` did forbid ledger writes:

- The write-boundary clause exists to stop an implementing plan mutating **ledger state** —
  `status.json`, `epic.md`, `plans/`, `landings/` — where a plan-authored edit would corrupt the
  orchestrator's authority. **`inbox/` is categorically different: it is the plan-writable surface
  this very plan was commissioned to create.** Forbidding writes to it would make the feature
  unreachable by its only producer.
- The containment invariants make plan writes safe by construction: own-file-only, append-only,
  one-way, no caller-supplied path. A plan cannot reach ledger state through this channel.
- Nothing entered the PR (`.plan/*` is gitignored), so there is no repository consequence either way.

⚠ **Follow-up owed on MY side, not the plan's: the write-boundary wording is now stale.** Every staged
spec in this epic carries *"creates and edits NO file under `.plan/local/orchestrator/`"*. That is now
wrong for orchestrated plans. **The clause must be narrowed to ledger state with `inbox/` named as the
sanctioned exception** — otherwise every future plan either violates its boundary or suppresses the
feature. Recorded as an epic-level action.

**The self-review was right to flag it and right to defer to the operator** — a plan that discovers its
own spec forbids the thing it just shipped should surface the contradiction, not resolve it silently.

## ⛔ Reviewer coverage — check states are now proven unreliable in BOTH directions

| Bot | Check | Reality |
|---|---|---|
| CodeRabbit | SUCCESS | ran, posted 1 comment — noise-filtered |
| **Sourcery** | **SKIPPED** | **ran anyway and posted a comment** |
| PR-Agent | SUCCESS | ran, **published nothing** |

**A SKIPPED check reviewed; a green check did not.** This is materially worse than the one-directional
problem PLAN-72 was staged on, and it has a retrospective consequence:

⚠ **My own "Sourcery failed 4 consecutive PRs" count is partly derived from CHECK STATES and is
therefore UNSAFE.** #1012's Sourcery was recorded as "SKIPPED" — on this evidence a skipped check does
not mean it did not review. **The count is downgraded from 4 confirmed to 2 confirmed (#1014
size-refusal and #607 weekly quota, both evidenced by an actual posted refusal) plus 2 unverified.**
Do not re-assert 4 without per-PR comment evidence. The operator's decision to keep Sourcery is
further supported: it may be participating more than the check states suggested.

**Cascade worth noting:** both real comments were noise-filtered to zero stored findings, so the
trigger-A re-review of the rebased HEAD hit its documented skip (no bot finding on record to
re-trigger) — **the merged commit carries no fresh bot review.** The finalize correctly logged the
caveat instead of letting a clean run imply review depth.

⚠ **Check whether the noise-filtering was correct** — PLAN-80 exists because a Sourcery refusal was
*mis*classified. Here two comments were filtered *as* noise. If either was a real finding, the filter
failed in the opposite direction. **Named as a verification item for PLAN-80's D1**, which already
owns the classifier.

## PR-Agent — precision on the discharge question

The finalize narrative says the behavioural proof is *"still not discharged — a fourth observation of
green workflow ≠ published comment."* **Both statements are true of different claims and should not be
merged:**

- *"PR-Agent can publish a valid finding on ordinary traffic"* — **discharged** on #1013, where it
  published a finding sharper than CodeRabbit's on the same defect. That artifact exists and does not
  un-happen.
- *"A green PR-Agent check means it reviewed"* — **false**, now on four observations including this
  one. Never gate on the check.

The honest summary: **PR-Agent works when it works, and its check state carries no information.**

## Follow-Ups

### ⛔ 1. PLAN-56 (the drain) is now URGENT — a live regression is running

The producer shipped without a consumer. Per this landing: *"orchestrated-plan lessons are now
deferred, not captured — a green finalize truthfully says 'routed to the epic' where it used to say
'filed'."* **Every orchestrated plan from now on writes lessons into an inbox nothing reads.** The
statement is truthful, which is exactly why it is dangerous: nothing looks broken while lesson capture
is silently accumulating unread. **PLAN-56 promoted.** Also: `kind: finding` has a schema and no
producer.

### 2. Candidate lessons drained from the inbox — one staged, one recorded

- **`-002` → staged as PLAN-85.** Argparse rejections recur as invented plan-scoping flags; 2 of 4
  script-failure clusters in one run. **The mechanism is the valuable part**: nearly every `manage-*`
  verb IS plan-scoped and DOES take `--plan-id`, so the flag reads as ambient boilerplate. The caller
  is **over-generalising a real, near-universal convention** — and prose cannot counter a correct
  generalisation with one carve-out. A rule every agent loads that still fires twice per plan is not
  doing its job.
- **`-003` → recorded, NOT staged.** Frontmatter description drifted from the body in the same commit
  that extended the body; `ext-self-review-plan-marshall` **caught it before push**. The detector is
  correctly specified and fired. Slipped-then-caught with a working guard is a watch, not a plan —
  though it is a useful counterweight to PLAN-81, which was staged because that same self-review
  **missed** a defect. Same machinery, one hit and one miss; PLAN-81's D1 should read both.

### 3. Upstream closure confirmed

The rebase pulled in #1013, the tool-layer fix for the executor version-split defect hand-repaired
earlier this session, with `test_executor_version_split_regression.py`. **Still owed:**
`/sync-plugin-cache` does not advance the `installed_plugins.json` pin, and preflight still checks the
version stamp rather than actual path anchoring.

### 4. Process note worth keeping

The plan **re-ran the full quality gate (~5 min) rather than using the documented reconciliation-record
path** after its self-review fix advanced HEAD. It paid off: `pre-commit-verify-freshness` returned
fresh against a **genuine build stamp at the real HEAD**, not a reconciliation note. Given PLAN-82 is
staged precisely because that gate accepts evidence it cannot substantiate, this was the right call.
