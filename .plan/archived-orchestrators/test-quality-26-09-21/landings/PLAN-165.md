# Landing Analysis: PLAN-165 — Close the two orphan production defects

epic: test-quality
workstream: WS-03
pr: [#1480](https://github.com/cuioss/plan-marshall/pull/1480) — merged, squash `c89beb88b4291755f8eddd00253c71092df22c04`

> Landing record for one shipped plan. Written by `analyze` after verifying claims
> against ground truth. Drained from inbox message
> `implement-plan-165-close-orphan-defects-016.md` (`landing-check`: `complete: true`,
> `missing_keys: []`), corroborated against the real PR state and the real diff.

## Deliverable Fidelity vs Spec

Realized footprint is **4 files, 254 insertions, 24 deletions** — read from
`git show --stat c89beb88b`, not from the narrative.

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| **D1** — adjudicate the `github_ops` import arrangement, then act on the verdict | shipped-as-specified, **closed by decision** | `github_ops.py` comment-only change (34 added / 6 removed, all comment). No import statement moved, added, or removed — verified in the diff. The governing block above the three `# noqa: E402` bottom imports now records both halves the spec demanded: the load-order rationale AND the monkeypatch-interception contract. The spec's ⛔ "do not fix `_github_pr` alone" was honoured vacuously — nothing was fixed, because the pattern was accepted. |
| **D2** — raise `credentials.py` coverage from a measured baseline | shipped-as-specified (figures **not re-derived here**) | New `test/plan-marshall/manage-providers/test_credentials_cli.py` (175 lines) driving the CLI routing chain through the existing `build_parser()`/`main()` seam. The spec's ⚠️ "measure it first rather than adopting the lead" was honoured: the run reports a **measured** 52.56% baseline, which corroborates the spec's `unverifiable`-stamped 52.6% claim. |
| **D3** — give `test_configure.py`'s hardcoded auth type one definition | shipped-as-specified, **verified in the tree** | `CLI_AUTH_TYPES = ('none', 'token', 'basic')` at `credentials.py:39`, consumed by both parsers (`:72`, `:87`) and imported by the test at `test_configure.py:22-24`. The literal `'none', 'token', 'basic'` occurs **0 times** in the test — the spec's ⛔ "verify the constant is actually consumed" is satisfied in both directions. |
| **D4** — report the measured deltas | shipped-modified | Delivered, with one figure **withdrawn before merge** — see Anomalies. |

**Nothing dropped, nothing added unplanned.** The 4-file footprint is exactly the
production-plus-test pair each deliverable named; the spec's declared surface of 7 entries
over-declared by 3 (the `_github_ci.py` / `_github_issue.py` / `_github_pr.py` siblings were
read for the adjudication and correctly not modified).

## Metrics and Anomalies

- **Tokens**: 4,969,190 total. `6-finalize` alone was 3.24M — **53%**, more than execute,
  outline and plan combined. The token figure is a **floor**, not a total: the phase was
  never closed, so it folds 14 dispatch-boundary rows as `(boundary floor)`.
- **Duration**: 3h23m worked, **16h15m wall**.
- **Budget**: crossed **both** error thresholds for `multi_module + tech_debt`
  (2.5M tokens / 180 min). This is the epic's first recorded double-threshold breach.
- **Anomaly — a false claim was caught and corrected before merge.** The PR body asserted
  the strict serial reverse-order pass had run and passed. It had not: the run was killed
  twice by host memory pressure with no verdict in either direction. Body and landing both
  now read **UNMEASURED**. The reverse-order evidence that does exist is the canonical
  parallel form (21,006 tests green).
- **Anomaly — 24 step firings across steps that nominally fire once.** Six steps carry
  `firing_count` 2–3 over two loop-back rounds; the three costliest re-fired steps all
  recorded the **same** `head_at_completion` (`56d5d442`), i.e. repeated work against an
  identical tree.
- **Unverifiable from here**: the coverage figures (52.56% → ≥84%) and the test-count delta
  (20,994 → 21,007). Re-deriving either requires a build, which is outside the orchestrator
  boundary. Recorded as **reported, not re-derived** — not as corroborated.

## Routing and Merge Behavior

- **Review**: `automatic-review` re-ran at head `56d5d44` and filed 2 findings. Both review
  escapes were classified **gate-addressable** — a rule exists for them and it did not fire.
  CodeRabbit surfaced a `ROUTES` mirror-list source-of-truth duplicate on a branch where
  `pre-submission-self-review` had just recorded "no check matched".
- **The pre-merge barrier blocked on a stale required reviewer.** `cuioss-review-bot` had
  reviewed `d55f2f90` but not the three commits that landed during review, and its registry
  declares no auto-review-on-push. A bare loop-back would have **skipped** the review step on
  the re-entry check and re-entered the barrier with an identical verdict. Cleared by the
  explicit re-review trigger the registry names (first attempt timed out at 559s).
- **`automatic-review` returned `escalate_ask{reason=re_review_timeout, outcome=declined}`
  on a HEAD the bot had in fact reviewed.** Both bots publish re-reviews by editing a
  persistent comment in place, and that path reports `head_sha_verified: false`
  unconditionally. Resolved on evidence (a direct `fetch_findings` at the merge candidate)
  rather than by taking the `declined` verdict or recording "proceeded unreviewed".
- **CI/merge**: all 11 checks green. `merge_mechanism=merge_queue`, `merge_state=merged` —
  but see the defect below: the queue path did **not** work unaided.

## Reconciliation Actions

- [x] row `status` → `shipped` — `queue --transition PLAN-165 --status shipped`
- [x] row `pr` stamped `#1480`
- [x] row `landing` stamped `landings/PLAN-165.md`
- [x] row `plan_marshall_plan_id` stamped `implement-plan-165-close-orphan-defects`
- [x] epic.md reconciled from status.json; both generated blocks regenerated
- [x] 16 inbox messages drained (15 candidate-lessons + this landing), each with a recorded disposition
- [x] Open Defects opened: merge-queue enqueue unfalsifiable; budget double-breach; stale-reviewer/loop-back interaction
- [x] Open Defect **closed**: `check-manifest-consistency false fail` — now explained and corpus-tracked
- [x] `resume_anchor` updated

## Follow-Ups

- **Folded into PLAN-160 as R5** — the vacuous-parametrize class (candidate-lesson -013).
  Expected Surface updated in the same act: `claimed_count` 20 → 21 (`pyproject.toml`),
  verified from `corpus surfaces`. ⚠️ PLAN-160 now carries **5 deliverables** — one below the
  scope-bloat split threshold. Re-evaluate for a split before emitting.
  Note this plan **already applied** that lesson to its own file: `test_configure.py:31-32`
  carries the binding-site non-vacuity assert. R5 is the sweep for the rest of the tree.
- **11 candidate-lessons promoted** to the global corpus (`2026-09-13-12-001` … `-011`).
- **3 folded onto existing corpus lessons** rather than filed as duplicates: the build-oracle
  zero-rows recurrence (`2026-08-25-09-009`, which this run's `mechanism=daemon_longpoll`
  evidence **confirms**), the session-id capture escalation (`2026-09-04-14-006` — capture at
  finalize entry is still too late), and the `check-manifest-consistency` recurrence plus its
  new resolver-parity half (`2026-09-04-17-006`).
- **The epic's lesson-stream leak is CLOSED.** Three consecutive prior landings sent their
  lessons to the global corpus without passing through this inbox. This run filed all 15
  here, and the orchestrator routed each one deliberately.
