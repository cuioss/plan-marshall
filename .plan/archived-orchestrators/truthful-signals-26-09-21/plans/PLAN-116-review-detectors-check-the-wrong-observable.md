# PLAN-116: Two review detectors check the wrong observable — and one is now on every loop-back

epic: truthful-signals
workstream: WS-01

> Staged 2026-07-29 from inbox `truthful-signals-006`, which consolidates the raw evidence in
> `post-merge-review-…-008` (detector blindness) and `-009` (the guard).
> ⛔ **Defect A is LIVE on every loop-back as of #1054 + #1052.**

## Objective

Both defects are **shape problems, not duration problems** — neither is fixed by a longer timeout,
and **both present as timeouts**. One detector **counts rows when it should watch a row**; the other
**asserts a precondition its own configuration denies**. Bring each onto the observable that actually
answers the question it asks.

## ⛔ Defect A — `wait-for-comments` counts rows, and pr-agent edits one in place

`_github_pr.py:710`:

```python
def is_complete_fn(data: dict) -> bool:
    return int(data.get('unresolved', 0)) > baseline
```

A pure count comparison against a snapshot baseline. **`pr-agent` re-reviews by editing its one
persistent Guide comment in place**, so the unresolved count **never grows** and the await can only
ever time out. Observed: a **~23-minute await that completed nothing** while pr-agent had in fact
reviewed (guide `updated_at` 09:10:26Z).

### It is now LIVE and load-bearing — this is the part that changes the priority

Two changes landed **after** the raw evidence was filed, and compose badly:

- **#1054** (`25b0c91c9`) — a loop-back now posts each REQUIRED bot's trigger comment and **awaits the
  result**.
- **#1052** (`ef80c1c8d`) — `required_bots` narrowed to **`pr-agent` alone**.

⇒ **Every loop-back from now on**: posts `/review` to pr-agent → awaits via `wait-for-comments` → the
count never grows → burns the full `re_review_await_timeout_seconds` (**600 s**) → hits
`re_review_on_timeout: ask` → **escalates to the operator**.

**Ten minutes and an operator prompt on every loop-back, even when pr-agent reviewed correctly.**

⚠ It does **not** deadlock — the `ask` fallback holds — but **the detector is now blind to precisely
the one bot it is the sole waiter for.**

### ⭐ The fix already exists one file over — this is a port, not an invention

- `github_re_review.py:247-250` matches on the **later of `updated_at` / `created_at`**, written for
  exactly this shape.
- The registry **already declares the answer**: `participation_requires_update: true` in
  `automatic-review/standards/pr-agent.md`.
- ✅ **Orchestrator-verified**: `bot_registry.py:320` exposes a `participation_requires_update`
  accessor, and `automatic-review/SKILL.md` documents the semantics — *"for a bot declaring
  `participation_requires_update`, only on first presence or observed `updated_at` movement."*

⇒ **This is two detectors where one was taught the lesson and the other was not.** The fix is to bring
`wait-for-comments` onto the **same registry-driven semantics**, ⛔ **not to invent new logic** and
⛔ **not to lengthen the timeout.**

## Defect B — the empty-review guard asserts an unreachable precondition

The org workflow's fail-closed gate fails the job on a precondition its own configuration denies.
⚠ **Partly overtaken by events**: #1048 was **reverted** by #1053, so the specific synchronize-trigger
framing is moot. **The underlying observation — a guard asserting a precondition its configuration
cannot satisfy — is retained** and must be re-established at HEAD before scoping.

## Deliverables

1. **D1 — GATE (mutates nothing): re-establish both defects at HEAD, and DERIVE the detector
   population.** ⛔ A and B are the two that surfaced — **treat them as a SAMPLE.** Find every
   completion/participation detector and classify each by the observable it checks (row count,
   row content, check state, timestamp movement). ⚠ **B must be re-verified post-#1053** — do not
   scope against the reverted framing.
2. **D2 — port `wait-for-comments` onto the registry-driven semantics** already used by
   `github_re_review.py`, honouring `participation_requires_update` per bot. **Mirror the existing
   implementation; do not fork a second convention.**
3. **D3 — a detector that cannot answer says so.** An await that ends because its observable can
   never change must report **that**, not a timeout. ⭐ **A timeout claims "we waited long enough";
   this detector never could have succeeded** — and the two demand opposite operator responses.
4. **D4 — tests, each verified to FAIL pre-fix.** (a) An in-place Guide `updated_at` bump completes
   the await. (b) A bot without `participation_requires_update` still completes on a new row.
   (c) The unanswerable case reports its own inapplicability rather than a timeout. (d) The detector
   population is **derived**, non-empty, and contains **all four** known members (A, B, C, D).

## ⛔ Defect C — the pre-merge barrier is fed a DEDUPED set and reports the required bot absent

**FOLDED IN 2026-07-29** from inbox `orchestrated-plan-detection-fails-silently-008.md` — observed
LIVE during PLAN-114's finalize, where it **would have falsely blocked a legitimate merge**.

`fetch_findings` deduped pr-agent's already-stored comment, which emptied `participated_bots`.
`branch-cleanup.md` instructs the caller to feed **exactly that set** to the participation predicate
→ verdict `pr-agent: absent`. The plan re-derived participation from the store
(`pr-agent:issue_comment`, reviewed sha == HEAD) → `complete`, and **recorded the discrepancy in the
decision log rather than laundering it**.

⭐ **This is the same wrong-observable shape as Defect A, in the opposite direction.** A checks a
count that cannot grow (false *negative* on participation); C checks a set that dedup empties (false
*negative* on participation) — both because the detector reads a **derived, lossy view** instead of
the durable store. ⛔ **A dedup intended for storage hygiene must never be the input to a
participation predicate.**

## Defect D — a canned no-op comment is indistinguishable from a review

**FOLDED IN 2026-07-29** from inbox `ceremony-prefilter-dropped-the-security-audit-005.md`, and
**independently corroborated by this session's #1057 evidence**: pr-agent's entire contribution was
`PR contains tests / No security concerns / No major issues detected` — a fixed-shape informational
Guide with zero actionable content. It satisfies "a comment from the bot exists" while carrying no
evidence the diff was examined.

⚠ On the same PR, **CodeRabbit and Sourcery both refused** (rate limit / weekly quota) and said so
**only in their comment bodies** — the check states did not show it. So the participation signal was
simultaneously (a) a canned no-op counted as present and (b) two refusals counted as absent-or-silent.

⛔ **Scope note:** D asks the detector to distinguish *participation* from *substantive review*. Keep
D1's derivation honest about this — a per-bot evidence marker is a **different observable** from the
three D1 already enumerates, and it may warrant its own plan rather than riding here. **Split it out
if D1's derivation shows it widens the change materially.**

## ⛔ Defect E — a PROVEN reviewer is reported `absent` on the next FIND call

**FOLDED IN 2026-07-29** from `code-intelligence-substrate-003.md` (forwarded by the sibling under the
routing rule; origin: the `inventory-blind-spot` plan, PR #1056). ⚠ **A forwarded message is a LEAD** —
neither epic has independently re-read `_github_pr.py`. **Re-establish at D1.**

`github_pr fetch_findings` does not re-credit a bot's already-proven participation across FIND calls.
Participation is derived from the **current call's comment scan**, so a bot whose review carries no
fresh `updated_at` movement since the previous call reads as `absent` on the next one.

On PR #1056: pr-agent **genuinely reviewed at 15:07** — its Guide comment filed to the ledger as
finding `7e3f74` (`bot_kind: pr-agent`, `reviewed_commit_sha: 69f2270…`). On **loop-back iteration 2**
the same bot read as **`absent`**. Nothing about its participation changed — **the signal moved
because the query moved.**

⭐ **This is the polarity INVERSE of #1026**, where a *detected refusal* was reported as a clean
review. **Both directions of the participation signal have now been observed lying** — record them as
a pair, not as two incidents.

⛔ **Compounding, and the reason this outranks its size:** on that same run the operator took a
merge-anyway decision for a genuinely rate-limited CodeRabbit, and pr-agent's **spurious `absent` sat
in the same gate evaluation**. A false `absent` and a true `absent` were **indistinguishable at the
moment of the merge decision**. That is PLAN-119's deadlock and this defect meeting in one gate.

**Suggested direction (the sibling's, ours to accept or reject at D1):** participation should be
**monotonic within a finalize run** — once a bot's review is observed and filed for a given
`reviewed_commit_sha`, later `fetch_findings` calls for that same head SHA report it as participating
regardless of `updated_at` movement. The ledger already carries `bot_kind` + `reviewed_commit_sha`, so
derive participation from **the ledger union with the current scan**, not the scan alone. Reset only
when the head SHA advances.

⚠ **A fourth shape, observed on #1061 (PLAN-110):** coderabbit's **check completed but produced no
comment at all** — distinct from a refusal comment (A/D) and from a dropped credit (E). And on #1058
(PLAN-109) coderabbit **reviewed the first HEAD and refused the second**, so *partial* participation
read as participation while the diff that actually merged went unreviewed. **D1's derivation must
cover all of these; the named defects are a SAMPLE.**

## ⛔ Defect F — `absent` names two states with opposite remedies, and reports the alarming one

**FOLDED IN 2026-07-29** from inbox `truthful-signals-007.md`. ⭐ **The gate was right. The word was
wrong.** This is a **reporting-fidelity** defect, not a crediting defect — which makes it distinct
from C and E, and it **survives both of their remedies**: C and E aim to produce or preserve a
*credit*; F concerns how a correctly-refused *stale* review is **named**.

**Observed on #1059 with full evidence:** workflow run `30466587421` conclusion **success**; the org
fail-closed step *"Verify the reviewer actually produced a review"* **passed**;
`cuioss-review-bot[bot]` published its Guide at **15:36:44Z** against HEAD `acbdcecf3`; the final
merged HEAD was `cf634762` at **16:51:40Z**. pr-agent ran, reviewed and published — **75 minutes
before the rebase that produced the merge candidate.** Its registry sets
`participation_requires_update: true`, `updated_at` never moved, so participation was **correctly not
credited** — and then reported as `absent`.

**The contract contradicts itself in one table** (`automatic-review/standards/bot-participation-contract.md`):

- `:56` defines `absent` as *"No comment posted and no completion check-run observed … **the bot never
  engaged at all**"*
- `:98` routes an unprovable participant to that **same** member
- `:81` names *"a stale comment tied to a prior HEAD"* as a thing presence does not prove

One member carries two states whose conditions are **mutually exclusive** — one requires no comment,
the other is only reachable when a comment exists. The taxonomy declares itself closed; it is not.
**`stale` is a real, common state with no member of its own**, so it lands on the member whose remedy
is maximally wrong: *never ran* → investigate the App install, credentials, org config (an
infrastructure incident); *ran, then the diff moved* → the reviewer is healthy, the defect is step
ordering, the fix is a re-trigger.

⛔ **It recurs on the COMMON path, not an edge case.** After #1053 pr-agent subscribes to
`opened`/`reopened`/`ready_for_review` only — **a rebase is invisible to it** — and
`finalize-step-sync-baseline` rebases and force-pushes as part of **every** finalize, *after* the
PR-open review. **The plan flow's own step ordering guarantees that any PR needing a rebase ends with
a stale Guide and a false `absent`.** ⭐ This likely explains much of this epic's review-coverage
pain, including PLAN-112's six barrier rounds.

**Remedy (from the message, adopted):** add a sixth member — `stale` / `participated_stale` — for an
admissible publish shape that fails the `participation_requires_update` / HEAD-currency test. It
**gates exactly as `absent` does today**, so **no merge verdict changes**. The distinguishing evidence
is already in hand at classification time (the comment was observed, its `kind` matched a declared
`participation_evidence` shape, only the currency test failed) and is **discarded on the way to
`absent`**.

⛔ **Do NOT fix this by crediting stale participation and do NOT soften the gate.** Widening what
counts as participation would trade a misleading label for an unsound gate — *the exact failure mode
this epic is named after*. ⚠ Note the message's own sharp point: `absent` defends itself as "the
fail-closed default", but **fail-closed does not apply to naming** — the closed outcome is right
either way, and there is no safety gained by describing a healthy reviewer as one that never engaged.

⚠ **Cross-link to PLAN-119:** a false `absent` and a true `absent` are indistinguishable at the
barrier, so F is an input to the deadlock, not merely a cosmetic report defect.

## Claim Labels

- OBSERVED (orchestrator-verified at HEAD): `participation_requires_update` exists in
  `bot_registry.py` and its semantics are documented in `automatic-review/SKILL.md`.
- OBSERVED (orchestrator-verified): #1054 `25b0c91c9` and #1052 `ef80c1c8d` are both merged, so the
  composition producing the live cost is real.
- OBSERVED (message-supplied, with line refs): `_github_pr.py:710` count comparison;
  `github_re_review.py:247-250` timestamp match; the ~23-minute empty await.
  ⚠ **Verify by SYMBOL — those files changed repeatedly today.**
- HYPOTHESIS: A and B are the only affected detectors — confirm/refute at D1 (verify-at-outline).

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-integration-github/**` (`_github_pr.py`)
- OBSERVED: `automatic-review/scripts/bot_registry.py`, `automatic-review/standards/pr-agent.md`
- HYPOTHESIS: `github_re_review.py` (read-only reference, unless D2 shares the helper)
- HYPOTHESIS: the org workflow guard for Defect B (verify-at-outline)

## Dependencies and Sequencing

- Depends on: none.
- Overlaps with: ⛔ **PLAN-115** (`tools-integration-ci` pr verbs, **LAUNCHED**) is adjacent — both
  reach PR comment plumbing. **Re-check disjointness before emitting; do not pair without it.**
  ⚠ **PLAN-112** (launched) touches finalize gating.
- Adjacent to: the retired `responded_bots` work in PLAN-92 (shipped) — read its landing first.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/truthful-signals/plans/PLAN-116-review-detectors-check-the-wrong-observable.md"
```

## Write-Boundary

Repository source + tests only; NO `.plan/local/orchestrator/` writes other than this plan's own
`inbox/{sender}-{seq}` message. See orchestration-model.md § Ledger Write-Boundary.
