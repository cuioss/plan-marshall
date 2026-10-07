# Landing Analysis: PLAN-PR-034 — A refusal nobody recognises is filed as a finding

epic: review-apparatus
workstream: WS-01
pr: #1344 (merged, squashed as `dfabe3d8e`)

> Landing record for one shipped plan. Written by the `analyze` verb after verifying
> claims against ground truth. Source: operator paste (mode `paste`), cross-checked
> against the plan's own `landing` message `-015.md` (`landing-check` → `complete: true`,
> 0 missing keys).

## Ground-Truth Corroboration

Every material claim was corroborated first-party BEFORE any ledger write. Nothing below
is taken from the paste on its own authority.

| Claim (paste) | Verdict | Evidence |
|---|---|---|
| Merged as #1344, squashed `dfabe3d8` | **corroborated** | `dfabe3d8e` on `main`, 2026-08-25 06:35:18 UTC |
| 19 files, +2400/−270 | **corroborated** | `git show --stat dfabe3d8e` — exactly 19 files, 2400 insertions, 270 deletions |
| Ships inert: `UNRECOGNISED_REFUSAL_MAX_CHARS is None` | **corroborated** | `_github_pr.py:297` — `UNRECOGNISED_REFUSAL_MAX_CHARS: int \| None = None`; non-firing branch 1 at `:367-369` returns `False` on the absent threshold, and is deliberately ordered first |
| `classify_bot` gated the override behind `bot in refused` — now fixed | **corroborated** | `review_completeness.py:631` — `if bot in refused or bot in (unrecognised_refusal or set()):` |
| Override carried to completeness + barrier consumers | **corroborated** | `review_completeness.py:122-123` (both `check` and `deficit` usage), `branch-cleanup.md:862`, `automatic-review/SKILL.md:683` |
| Re-review matcher's blind spot closed | **corroborated** | `github_re_review.py:332` names the displacement explicitly |
| Cache sync minted `0.1.1543`, so `executor == installPath` gap re-opened | **CONTRADICTED at the consequence** | See § Registry-Pin Gate below |
| 6-finalize billing 277,383 against 3,498,973 tokens | **anomalous — recorded as a watch** | See § Metrics and Anomalies |

### Registry-Pin Gate — the standing trap did NOT re-arm

The operator flagged that this run's sync minted `0.1.1543` and therefore re-opened the
`executor == installPath` gap by one version. The *event* is corroborated — `0.1.1543`
exists in the cache — but the *consequence* is refuted at the current state:

- `MARSHALL_VERSION = 0.1.1544` (`.plan/execute-script.py:80`)
- registry `installPath` = `…/plan-marshall/plan-marshall/0.1.1544` for every bundle, both `user` and `project` scope
- this session's served skill base dir = `…/0.1.1544`

All three agree, so **the gate passes**. A later mint to `0.1.1544` landed *with* the
registry pinned to it. ⚠ This is a POINT SAMPLE taken at analysis time, not a claim that
the per-landing leak is fixed — the standing rule (check the gate at the start of every
session) is unchanged, and the next sync may well re-open it.

## Deliverable Fidelity vs Spec

The spec staged **five** deliverables (D0–D4); the plan shipped **six**. The set is
`shipped-expanded`, not `shipped-as-specified`: two spec deliverables shipped folded
inside the six rather than as their own rows, and three deliverables are genuinely new,
added during execute in response to defects found there.

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| D0 — measure refusal-recognition coverage across registry + corpus | shipped-as-specified | Shipped as delivered #1; the absence was measured over a named population, satisfying the spec's own "an absence asserted over an unnamed population is the archetype this epic exists to remove" |
| D1 — positive-validation (enumerative) arm | shipped-modified | `_github_pr.py:297-380`. Modified in the conservative direction the spec demanded, and further: it ships **inert** behind a `None` threshold |
| D2 — surface `unrecognised_refusal` as its own producer field | shipped-as-specified | `github_pr.py` return literal; `automatic-review/SKILL.md:661` documents the three-state split |
| D3 — state the rule once in `bot-participation-contract.md` | shipped, folded | Not a separate row in the landing's six, but `bot-participation-contract.md` +109/−… and `:349` carries the shipped-value-`None` statement |
| D4 — pin it with a mutation-derived test | shipped, folded | `test_structural_refusal.py` +69; `test_review_completeness.py` +370 |
| — (unplanned) close the re-review matcher's identical blind spot | **added-unplanned** | `github_re_review.py` +162; the spec had this only as an OBSERVED claim, never as a deliverable |
| — (unplanned) deny participation credit for unrecognised-only bots | **added-unplanned** | `review_completeness.py:631` |
| — (unplanned) carry the override to completeness + barrier consumers | **added-unplanned** | `branch-cleanup.md:862`; this is the fix for the finalize-found defect |

### The verify-first clause resolved itself

The spec carried a blocking-shaped clause: *"check whether PLAN-PR-025 D2 has landed
first — if it has not, this plan must not pre-empt its provenance field."* PLAN-PR-025 is
still `staged`, so it had NOT landed, and the plan proceeded anyway. It did not pre-empt:
it extended `github_re_review`'s existing `layer` split (`:325-337`, an OBSERVED claim in
the spec) rather than adding a third copy. ⚠ **Consequence for PLAN-PR-025**: its D2 now
opens a function this landing has already restructured. Recorded in § Follow-Ups.

## Metrics and Anomalies

- **Tokens**: 8,506,434 total / 95,810,061 billing-weighted. Matches the `landing-facts`
  `total_tokens` exactly.
- **Duration**: 24h58m wall, 8h2m worked, 16h55m idle.
- **Phase outlier**: 6-finalize (3,498,973 tokens) **outspent** 5-execute (2,015,206) —
  finalize was 41% of the plan's tokens.

### ⛔ Anomaly: the 6-finalize billing figure is off by two orders of magnitude

Every phase but one bills at 12.6×–28.2× its token count. 6-finalize bills at **0.08×**:

| Phase | Tokens | Billing | Ratio |
|---|---|---|---|
| 1-init | 83,742 | 1,070,775 | 12.8× |
| 2-refine | 155,697 | 2,165,969 | 13.9× |
| 3-outline | 1,904,458 | 23,963,806 | 12.6× |
| 4-plan | 848,358 | 11,525,326 | 13.6× |
| 5-execute | 2,015,206 | 56,806,802 | 28.2× |
| **6-finalize** | **3,498,973** | **277,383** | **0.08×** |
| Total | 8,506,434 | 95,810,061 | — |

The per-phase billing column sums to 95,810,061 — the published total, to the token — so
the total is internally consistent and **inherits** the anomaly rather than contradicting
it. 6-finalize is the re-entered phase, which is precisely the class `truthful-signals`
PLAN-TRUTH-055 made representable and where one defect is known to have escaped to main.

⛔ **Not this epic's surface.** Recorded as a Watch and routed to `truthful-signals`; no
plan is staged here for it.

## Routing and Merge Behavior

- **Review**: 15 Q-Gate findings, all resolved `fixed`, 0 pending. Seven pre-submission
  self-review rounds; `firing_count` recorded **5** against 7 actual firings — rounds 3–5
  never called `mark-step-done`. The plan itself filed that as a candidate-lesson.
- **CI/merge**: 18,134 tests pass; whole-tree quality gate green including a
  marketplace-wide plugin-doctor pass (37 rules, 0 findings). `merge_mechanism=merge_queue`,
  `merge_state=merged`. No rebase conflicts or re-verify signals reported.
- **Finalize steps**: 23 total. The `landing-facts` block listed 21 with an explicit scope
  note — `emit-landing` (order 1000) was writing the message and `archive-plan` (order 1100)
  had not run, so neither asserted its own outcome. 21 + 2 = 23; consistent, and the
  abstention is the honest form.
- ⚠ **The self-review step closed on operator authorisation, not a clean pass.** Round 7's
  two findings were fixed but not themselves re-reviewed. Recorded here rather than left in
  the step records alone.

### ⛔ The finding that justified the whole finalize

`classify_bot` gated the new override behind `bot in refused` while the producer reports
`unrecognised_refusal` and `refused_bots` **disjointly** — so for the only case the
override exists for, it was unreachable, and the bot resolved `absent`: *a reviewer that
declined, reported as one that stayed silent.* That is verbatim the conflation the plan
exists to remove — **the plan reproduced its own target defect**. A test asserted
`STATE_ABSENT` on that exact input, so the suite was green *because* of the defect.
Caught at round 6 of 7.

This is the `test-pins-the-defect` archetype and the third recorded instance in this epic
of a fix re-introducing the defect it was written to remove.

## ⛔⛔ Surface Under-Declaration — the disjointness consequence

The spec declared an Expected Surface of **5 files**. The landing touched **19**. The
14 undeclared files are not incidental: they are the most heavily-contended files in this
epic's corpus.

| Undeclared file actually touched | Staged specs that claim it |
|---|---|
| `automatic-review/SKILL.md` | PR-025, PR-026, PR-029, PR-030 |
| `automatic-review/scripts/review_completeness.py` | PR-025, PR-026, PR-031 |
| `automatic-review/scripts/bot_registry.py` | PR-025, PR-026 |
| `automatic-review/standards/coderabbit.md` | PR-029, PR-031 |
| `automatic-review/standards/sourcery.md` | PR-025 |
| `phase-6-finalize/standards/branch-cleanup.md` | PR-024, PR-025, PR-026, PR-028, PR-033 |
| `workflow-integration-github/SKILL.md` | PR-024, PR-025, PR-029, PR-036 |
| `workflow-integration-github/scripts/github_re_review.py` | PR-025 |
| `test_bot_participation_contract.py` | PR-024, PR-025, PR-030 |
| `test_structural_refusal.py` | PR-025, PR-031 |
| `test_re_review_strategy.py`, `test_refusal_recovery_arming.py`, `test_review_completeness.py`, `test_comments_stage.py` | PR-025 and others |

**Consequence**: ten staged specs (PR-024, -025, -026, -028, -029, -030, -031, -033, -036,
-040) were written against code this landing has moved, and **every one of their
re-grounding verdicts was already stale** before it. This is the known `affected_files`
under-recording archetype — the declared surface is a plan-time estimate that no step
reconciles against the real diff at finalize.

⇒ **A re-grounding pass (`cleanup`) is now a precondition for any emit**, not an
optional tidy-up. Recorded as an Open Defect.

## Reconciliation Actions

- [x] row `status` → `shipped` — `orchestrator queue --transition PLAN-PR-034 --status shipped`
- [x] row `pr` stamped `1344` — `orchestrator queue --set-row PLAN-PR-034 --field pr`
- [x] row `landing` stamped — `orchestrator queue --set-row PLAN-PR-034 --field landing`
- [x] row `plan_marshall_plan_id` stamped — `orchestrator queue --set-row PLAN-PR-034 --field plan_marshall_plan_id`
- [x] inbox message `-015.md` archived as consumed (its claim is fully reconciled here)
- [x] Open Defect opened: surface under-declaration ⇒ re-grounding precondition
- [x] Watch opened: 6-finalize billing anomaly, routed to `truthful-signals`
- [x] Watch opened: the feature ships inert — behaviour verified only by tests
- [x] START-HERE and Ordered Queue blocks regenerated — `orchestrator resume-summary`
- [x] resume_anchor updated

## Follow-Ups

- **PLAN-PR-025 D2 must be re-scoped before emit** — it opens `_is_refusal_notice` for layer
  provenance, a function this landing has already restructured. Its premise is not refuted,
  but it is now written against superseded code. Folded onto PR-025 as a pre-emit amendment
  (this makes **ten** owed, up from nine).
- **The inert feature needs a measured threshold to ever fire.** `UNRECOGNISED_REFUSAL_MAX_CHARS`
  is `None` by deliberate design — D0 measured the population and found no local instance, so
  no bound was derivable. Nothing is staged: deriving the bound needs a corpus that does not
  yet exist. Recorded as a Watch, not a plan.
- **21 inbox messages remain queued** — 14 candidate-lessons from this plan, 1 finding from
  `plugin-doctor-detector-coverage-residue`, 6 from sibling epic `truthful-signals`
  (2 of them `landing` messages needing `landing-check` first). Drained by
  `/plan-orchestrator analyze slug=review-apparatus` with no paste.
- **9 global lessons were filed by the plan** for tooling defects it did not touch,
  including one the plan itself later corrected: `affected_files` is not a faulty read but a
  **missing write path after outline** — which is the same root cause as this landing's
  surface under-declaration above. The two corroborate each other.
