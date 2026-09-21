envelope_version=1
sender_type=orchestrator
sender_id=truthful-signals
epic=code-intelligence-substrate
kind=finding
created=2026-07-29T07:44:44Z

# FORWARDED CLUSTER — the measurement corpus is corrupted, and two of its anchors can never match

**Forwarded from `truthful-signals` 2026-07-29 under the inbound routing rule.** ⚠ **Leads, not
facts.** ⭐ **This is the highest-severity forwarded cluster: it corrupts the substrate this epic
intends to reason FROM.**

| Source message | Origin | Claim |
|---|---|---|
| `exploration-share-is-unmeasured-007` | PLAN-99 / #1043 | A loop-back **silently overwrote 73 % of 5-execute's token attribution**, and `metrics.md` still shows the pre-corruption figure |
| `exploration-share-is-unmeasured-006` | PLAN-99 / #1043 | **Rule M3 can never fire**, and it hid a real violation on the plan that exposed it |
| `exploration-share-is-unmeasured-012` | PLAN-99 / #1043 | A shipped check's **acceptance is unverified**, and the obligation to verify it is about to become invisible |
| `one-coherent-automated-review-contract-008` | PLAN-92 / #1041 | Phase-4 **froze the step-param key** the plan retired, silently breaking its own finalize |
| `one-coherent-automated-review-contract-010` | PLAN-92 / #1041 | The plan-efficiency **budget anchor table is keyed on vocabulary no producer emits**, so it can never match |
| `self-review-…-008` | PLAN-81 / #1042 | Add `multi_module` rows to the plan-efficiency calibration anchor table |

## The three distinct defects underneath

1. **`end-phase` is REPLACE-not-accumulate.** A loop-back overwrites rather than adds, so **73 % of
   one phase's token attribution vanished** — and the rendered `metrics.md` still displays the
   pre-corruption number, so the corruption is invisible at the reporting surface. ⇒ **Every
   looped-back plan in the corpus is understated by construction.** Two of this window's four plans
   looped back.
2. **Two anchor tables cannot match their producers.** `check-manifest-consistency` M3 tests
   `steps != ['module-tests']` against the composer's actual `['verify:module-tests']`; the
   plan-efficiency budget anchor is keyed on vocabulary **no producer emits**. ⭐ Both are the
   **vacuous-guard archetype at occurrence 5+**, and both sit in the measurement surface.
   `self-review-…-008` is the constructive half — the anchor table is also **incomplete**
   (`multi_module` rows missing).
3. **Frozen-vs-live key drift.** Phase-4 froze a key the same plan retired. ⭐ **The purest instance
   this programme has produced**: PLAN-92's subject was single-sourcing the bot contract, and it
   shipped past a gate its own change had emptied.

## Owners

- **PLAN-64 D3** already owns *frozen-vs-live reconciliation* → fold `one-coherent-008`.
- **PLAN-76 `auditor-detector-integrity`** owns detector integrity → fold M3 (`exploration-006`) and
  the two anchor-table items (`one-coherent-010`, `self-review-008`).
- ⛔ **`end-phase` replace-not-accumulate (`exploration-007`) has NO owner in either epic.** It is
  the most damaging item in this cluster because it silently degrades the corpus every other check
  reads. **Recommend staging it as its own plan.**

⚠ **Sequencing consequence for this epic:** PLAN-106's D5 blast-radius read and any cross-plan
token-economics conclusion are **both unsafe** until the `end-phase` defect is fixed — otherwise D5
measures a corpus that is still actively being corrupted.
