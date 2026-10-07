# Landing Analysis: PLAN-37 — Credentials-Key Normalization

epic: plan-optimization
workstream: WS-10
pr: #978 (`138747e0d`)

> Landing record for one shipped plan. Written by the `analyze` verb after verifying
> claims against ground truth — a pasted claim is a lead, never a fact.

## Deliverable Fidelity vs Spec

Verified against merge commit `138747e0d` (3 files, +433/-25). **4/4 shipped** (D4 shipped as a
refutation — no rule, by design).

| Deliverable | Verdict | Evidence |
|---|---|---|
| D1 — normalize the `credentials_config` key via existing prefix-stripping | shipped | `_providers_core.py`: **`canonical_credentials_key()` (`:70`) is the single normalizer**; `resolve_credential_path` now calls it (`:345`) instead of carrying its own inline strip — exactly the "reuse the logic, don't write a second normalizer" instruction |
| D2 — pin the prefixed-write / unprefixed-read round trip | shipped | `test_providers_core.py` (+289) |
| D3 — sweep blast radius + migrate existing configs | shipped | lazy + idempotent migration; read accepts **both** directions (`:202-204`, `:234-235`) |
| D4 — confirm plugin-doctor as the rule home | **REFUTED, no rule shipped** | see below |

## ⚠ Two places MY spec was itself imperfect — recorded honestly

The binding-practice point cuts both ways: the orchestrator's *sharpenings* also carry inferred
claims, and two were falsified here.

1. **My Expected Surface named `_config_core.py` as a `credentials_config` writer. It is not.**
   It only lists the string in `CANONICAL_TOP_LEVEL_KEY_ORDER` for key ordering. **This collapsed
   the entire `manage-config` adjacency cluster (PLAN-35/37/38) to zero edits** — the concurrency
   stop I armed never fired because there was nothing to collide with. `marshall-steward` was never
   entered, the domain-detect path never touched, and PLAN-38's #975 came through as a clean
   `no_overlap` rebase. **The adjacency I flagged three times was a phantom** — a false-positive
   collision risk, harmless but wrong.
2. **My "two caller populations" sharpening was itself incomplete — there are three.** I named
   registration-writes-prefixed and consumers-read-unprefixed. `_cred_edit.py:59` is a **third**:
   it passes the operator's raw spelling straight through. **That is precisely why the read had to
   accept BOTH directions rather than only stripping** — my two-population model would have
   justified a one-directional fix that missed the third population. The plan caught it; my
   sharpening did not.

**The lesson for the orchestrator:** a correction is not automatically more reliable than the
claim it corrects. Both my Expected-Surface and my two-population framing were inferred, and both
were falsified at execution — consistent with the widened `verify-before-implement` lesson (even
the orchestrator's *sharpenings* are hypotheses).

## D4 refuted — and the operator flagged a judgment call worth revisiting

D4's hypothesis (plugin-doctor is the rule home) was **refuted with a concrete reason**:
`doctor-marketplace.py` is rooted at `--marketplace-root`; its one project-rooted read
(`marketplace_root.parent.parent`) lands on the project root **only in this meta-project** — in a
consumer repo the marketplace root is the plugin cache, so plugin-doctor cannot see `marshal.json`
there. **`plan-doctor` is recorded in `decision.log` as the correct home.**

The executor then took the task's explicitly-sanctioned "ship no rule at all" branch, reasoning
that D1+D3 make a mismatched key harmless. **⚠ The operator flags this as a judgment call to
revisit: the rule would still catch a key matching NO skill** — a class D1+D3 do not cover
(they reconcile prefix/unprefix, not a genuinely-wrong key). **Recorded as a follow-up** — a
`plan-doctor` rule for orphaned `credentials_config` keys is a small, well-scoped candidate.

## The review-caught defect is the real story

**CodeRabbit found a containment gap the plan introduced.** The new migration's docstring
advertised "best-effort" while its `_save_marshal` persist was **unguarded** — an `OSError` would
have escaped `read_provider_config`'s `(JSONDecodeError, KeyError)` handler and **turned a
resilient read into a hard crash.** Fixed in loop-back TASK-007 with two regression tests.

- **This is the offer-surface / guards-are-highest-risk shape again** — the defect was in the
  plan's *own new* migration code, in exactly the resilient path it was extending.
- **Lessons-capture broadened `2026-07-17-21-001`** from rename-race-safety to *general
  containment* — noting the new migration explicitly cited `_migrate_credentials_home_if_needed`
  as its model and **reproduced its containment gap in a different failure class.** That is a
  sharp generalization: copying a pattern copies its latent gaps.

## Metrics and Anomalies

- Tokens: **2.8M** · Worked: **2h31m** · Wall: **4h12m** · all 6 phases recorded (partial: false)
- Deploy: 1112 files; executor regenerated
- Anomalies: none in execution

## Routing and Merge Behavior

- **Review**: 2 CodeRabbit comments (1 fix, 1 accepted). **Only CodeRabbit again** — consistent
  with the PLAN-38 finding that the review surface is one bot, not the three configured.
- **CI/merge**: all green (plugin-doctor whole-tree 30/30), merged via queue, `main` at `138747e0d`.
- **Surface collisions**: NONE — and the phantom-adjacency finding above explains why the cluster
  I worried about was never real.

## Reconciliation Actions

- [x] status.json `plans[]` updated (`shipped`, pr `978`, landing `landings/PLAN-37.md`)
- [x] epic.md queue row reconciled
- [x] Watch `credentials-key-convention-split` — RETIRED (PLAN-37 #978)
- [x] `manage-config adjacency cluster` — DISSOLVED: `_config_core.py` was never a writer; the
      PLAN-35/37/38 collision risk was a phantom. Correct the note so PLAN-35 is not held for it
- [x] `enabled-bots-vs-operative-drift` watch — reinforced (CodeRabbit-only again on #978)
- [x] resume_anchor updated; START-HERE regenerated

## Follow-Ups

- **⚠ `plan-doctor` rule for orphaned `credentials_config` keys** (operator-flagged D4 revisit):
  D1+D3 reconcile prefix/unprefix spellings but do NOT catch a key that matches **no skill at
  all**. A small `plan-doctor` rule would. Well-scoped candidate — not staged.
- **Copying a pattern copies its gaps** (lesson `2026-07-17-21-001`, broadened) — worth a
  lightweight self-review candidate: any new code citing an existing function "as its model"
  should be checked against that model's *known* gaps, not just its happy path.
- **The orchestrator's own Expected-Surface claims are hypotheses** — this plan falsified two.
  Fold into the binding practice: a spec's Expected Surface and the orchestrator's sharpenings
  are inferred and should be marked verify-at-outline, not asserted.
