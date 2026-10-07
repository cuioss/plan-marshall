# API-Sheriff PR #140 — mid-flight, pre-merge, barrier HELD

epic: review-apparatus · analysed 2026-08-01 · **cross-repo** (`cuioss/API-Sheriff`), **PR OPEN — barrier
held at `loop_back`, not a post-merge revisit** · source: operator paste of a leaf's `automatic-review`
return, then verified against ground truth
· evidence: `gh api graphql` PR #140 comments+reviews; `gh api repos/cuioss/API-Sheriff/contents/.plan/marshal.json`;
`review_completeness.py:185-192`; `bot_registry.py:24-27,334-355`; `bot-participation-contract.md:59`

> ⚠ **Not a run of the standing practice.** The PR is open and its findings are untriaged, so § 3 and § 4
> are **OWED, not answered**. Recording them as answered would manufacture a signal.
>
> ⭐ **The paste's own analysis was CORRECT on every load-bearing point.** Verification here confirms it
> rather than correcting it — with one exception in § 2 that the paste could not have seen, and one
> suspicion of MINE that verification REFUTED (§ 5).

## 1. Participation — verified, not taken from the paste

| Bot | State | Evidence (fetched) |
|---|---|---|
| **CodeRabbit** | `refused_awaitable` | `11:54:03Z` — *"Review limit reached … **Next review available in: 49 minutes**"* |
| **PR-Agent** | `participated` | `11:55:19Z` — Reviewer Guide with **`⚡ Recommended focus areas`**, a real finding |
| **Sourcery** | reported `refused_hard` | `11:53:59Z` — *"you have reached your **weekly rate limit** of 500000 diff characters. Please **try again later** or upgrade"* |

**Gating, read from API-Sheriff's own `marshal.json` — the paste's table is CONFIRMED:**

```
required_bots: "coderabbit,pr-agent"
optional_bots: "sourcery"
review_rate_window_await: false
```

⇒ CodeRabbit **is** required here. Quorum is genuinely unmet, and the leaf was right to hold.

⭐ **This is the per-repo gating divergence made concrete.** plan-marshall has
`required_bots: "pr-agent"` / `optional_bots: "coderabbit,sourcery"`. `review-practice.md` § 1's warning —
*"the gating is per-repo — never carry this table's column to another repo"* — is now **enacted and
verified**, not hypothetical. The operator's rationale (CodeRabbit matters more on API-Sheriff, which is
production code) is reflected in config.

## 2. ⛔⛔ NEW VERIFIED DEFECT — `refused_hard` is a FALL-THROUGH being reported as a classification

`review_completeness.py:188-189` is a binary on one string equality:

```python
awaitable = bot_registry.rate_limit_class(bot) == 'awaitable_window'
return STATE_REFUSED_AWAITABLE if awaitable else STATE_REFUSED_HARD
```

And `rate_limit_class()` is documented **fail-closed to `'unknown'`** (`bot_registry.py:334-355`).

⛔ **Only `coderabbit` declares `rate_limit_class` in the registry at all** (`bot_registry.py:27`,
`awaitable_window`). Sourcery declares none. PR-Agent declares none.

⇒ **Every bot except CodeRabbit resolves to `refused_hard` on any refusal, whatever the refusal actually
is** — because the field is missing, not because a hard quota was observed. The operator is then shown
**"refused_hard (hard quota)"**: a positive claim about the bot's quota shape, derived from an absent
field.

**And on this PR the label is also wrong on the merits.** Sourcery's refusal is a *weekly rate limit* that
says "try again later" — an awaitable window, merely a long one. It is not a hard quota and not a
structural ceiling.

⚠ **Severity, stated precisely — this is NOT a false green.** The fall-through direction is *safe*:
unknown → not awaitable → the bot stays in `_UNPROVEN_STATES` → a required bot holds the barrier open. The
gate behaved correctly. The defect is that the **report misinforms** while the gate is right — this
epic's own theme, a confident signal hiding a caveat. Its practical cost is an operator steered toward
"waiting is futile, force it through" when waiting would in fact have worked.

⭐ **Same archetype as `PLAN-PR-007`, one level down.** PR-007 exists because `absent` names two states
with opposite remedies. `refused_hard` names **three**: a declared hard quota, a structural size ceiling,
and *"we never declared anything for this bot"*. The third is not a refusal shape at all.

## 3. Posted answers

**N/A — the PR is open and untriaged.** ⛔ Not scored as a pass.

## 4. Could we have found it ourselves?

**OWED.** PR-Agent's `fe5e13` (the `cookieHeaderConfigurationFor` 4608 cookie budget possibly tightening
the pre-route Cookie limit below a lenient 8192 baseline) is not yet dispositioned, and the back-feed
question keys off the **answer posted on the PR**. Re-run after #140's triage lands.

⭐ Worth carrying forward when it is: the paste reports our **own security-audit** independently flagging
the same residual (the cookie carve-out sets its cap outright with no `max()`). **Two independent
producers converging** is a different and stronger signal than either alone — and it is evidence that the
local security audit, when it runs, finds what the bots find.

## 5. ⚠ A suspicion of MINE, REFUTED — recorded so it is not re-derived

On first reading I suspected `refused_hard` was wrongly merging the *weekly quota* case with the
*never-expiring diff-size ceiling* case. **`bot-participation-contract.md:59` refutes it**: the state is
*defined* as covering both — *"a refusal that does not reopen on a useful timescale (`rate_limit_class:
hard_quota`), **or** a structural refusal such as a size/diff ceiling"*. Collapsing them is deliberate and
defensible **for the gating question** ("should I wait?"), even though it is lossy for the remediation
question ("what would ever fix this?").

⇒ The real defect is § 2's undeclared-field fall-through, which is a different thing entirely. ⛔ Do not
re-raise the merge-of-two-refusal-shapes as a defect; it is by design.

## 6. Corroboration — the check-success-vs-actually-reviewed conflation recurred, live

CodeRabbit's **check-run was SUCCESS** while CodeRabbit **never reviewed the diff**. The epic's standing
rule ("check states lie in both directions; only `ci pr comments` is evidence of participation") held, and
the participation contract caught it exactly as designed.

⭐ **And it caught a human-side instance in the same run**: the assistant's own earlier read — *"CodeRabbit
SUCCESS"* — was the wrong inference, corrected only when the participation layer disagreed. ⚠ **The
archetype is not merely alive in the code; it is alive in how the signal gets read.** That is the
strongest argument yet for `PLAN-PR-014`'s D4 (a check reporting RAN, not HANDLED).

## Feeds

- **PLAN-PR-007** (`absent-names-two-states`) — ⭐⭐ **materially strengthened, and partially compensates
  for the `not_triggered` member it lost on 2026-08-01.** § 2 supplies a NEW, code-verified taxonomy
  defect of the same shape: `refused_hard` conflates two declared refusal shapes with an *undeclared*
  one. ⛔ D1's population question is now "which states are fall-throughs of a missing registry field?",
  which is checkable at `review_completeness.py:188` rather than inferred.
- **PLAN-PR-008** (`review-barrier-deadlocks-on-a-refusing-bot`) — this is a **live deadlock instance in
  the wild**, with `review_rate_window_await: false` confirmed as the reason it cannot self-converge, and
  a leaf correctly declining force-done because it cannot ask. Exactly D3's accepted-coverage-gap
  decision, arriving unprompted.
- **PLAN-PR-014** (`crashed-participation-gate`) — § 6 corroborates D4's shape from a second repo.
- **`bot_registry.py`** — ⛔ **OPEN AND UNOWNED**: `rate_limit_class` is declared for exactly one of the
  registered bots. Whether the fix is "declare it for all" or "make the missing case its own state" is a
  PLAN-PR-007 D1 question, not an independent plan.
- **`review-practice.md` § 1** — the per-repo gating warning is now backed by a verified divergence;
  no rule change needed, the warning already says the right thing.
