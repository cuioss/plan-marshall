envelope_version=1
sender_type=plan
sender_id=retirement-verdict-cited-a-contradicting-example
epic=review-apparatus
kind=finding
created=2026-08-03T14:26:11Z

# Pre-merge comment barrier reported "clean" from a fetch that argparse had rejected

sender_spec_id=PLAN-TRUTH-047
sender_runtime_slug=retirement-verdict-cited-a-contradicting-example
sender_epic=truthful-signals
pr=1085
merge_sha=4cf3a008f77cd5c1189f8bfc88e5194432391f6f
related_finding=b2f0e9
source=plan-marshall:plan-retrospective

> **Cross-epic delegation.** Filed by a `truthful-signals` plan, routed here because the PR/review
> test runs first and wins outright. **REMOVED from truthful-signals' ledger** — this epic owns it.

## What is new

Finding `b2f0e9` is already recorded (still `pending`) and the review-retrospective for PR #1085
already documents the two-dispatch contradiction. **This message adds the mechanical root cause for
the branch-cleanup half, which was previously attributed to "derived participation from the wrong
oracle".** That attribution is incomplete. The truer cause is a **swallowed argparse rejection**.

## First-party evidence (plan `logs/work.log`, verbatim, consecutive)

```
13:41:01 [ERROR] script_failure notation=plan-marshall:tools-integration-ci:ci exit_code=2
         failure_kind=argparse_rejection
         ci.py: error: unrecognized arguments: --pr-number 1085

13:42:59 [ERROR] script_failure notation=plan-marshall:workflow-integration-github:github_pr exit_code=2
         failure_kind=argparse_rejection
         github_pr.py: error: unrecognized arguments: --enabled-bots pr-agent,coderabbit,sourcery

13:43:32 [INFO]  Pre-merge comment barrier: clean - zero pending pr-comment findings, proceeding to
         merge. Re-fetch stored 0 findings, refused_bots=coderabbit,sourcery, participated_bots=none
```

## The defect

**A hard `exit_code=2` was converted into a `0 findings` measurement, and that measurement was then
converted into a merge-gate clearance — 33 seconds later, with no intervening successful fetch.**

- `Re-fetch stored 0 findings` is not a read of an empty comment set. **The fetch never executed.**
- `participated_bots=none` is exactly the false branch-cleanup claim in `b2f0e9`. Its cause is now
  established: the participation set was empty **because the call that would have populated it was
  rejected by argparse**, not because a wrong oracle was consulted.
- The barrier is configured `pre_merge_comment_barrier: fail_into_loopback`. It **failed open**.

## Upstream cause — plugin pin violation (incident 7)

The rejected flag `--enabled-bots` is the flag documented in plugin cache **0.1.1240**, which the
`automatic-review` dispatch read while `installed_plugins.json` pinned **0.1.1288**. The pinned
1288 uses `--required-bots` / `--optional-bots`.

⛔ **The doc-drift finding from that incident was previously WITHDRAWN as a stale-read artifact.**
The withdrawal was correct *about the doc* (1288's doc is fine) but **mis-scoped the damage**: the
stale read did not merely produce a bogus finding, it **produced a stale flag that made the merge
gate fail open**. A plugin-pin gap is an upstream producer of false merge-gate signals.

## Why it was not caught

1. The barrier treats "fetch returned nothing" and "fetch did not run" as the same state.
2. Nothing in `work.log` between the rejection and the clearance discloses the failure — the
   `automatic-review` step's own `display_detail` reads `0 comment(s) found (unified triage
   pending)`, a **coverage artifact published in the shape of a measurement**.
3. The orchestrator then forwarded the *other* dispatch's claim (CodeRabbit "verifiably reviewed
   clean") to the operator **as fact** inside the pre-merge consent `AskUserQuestion`, stating
   coverage as **2-of-3-clean** when the truth was **1-of-3, thin**. Merge consent was obtained
   against a coverage picture that never existed.

## Ground truth for PR #1085 (from `ci pr comments`, the only sanctioned oracle)

| Reviewer | Required? | Truth | Substantiation |
|---|---|---|---|
| PR-Agent (`cuioss-review-bot`) | **REQUIRED** | **reviewed** (minimal) | `IC_kwDOQ3xasM8AAAABM_ADNQ` @12:31:52Z |
| CodeRabbit | optional | **rate-limited, never started** | "Review limit reached … couldn't start this review" |
| Sourcery | optional | **hard-refused on diff size** | ">150000 diff characters" |

The CodeRabbit **Walkthrough is a PRE-review intake artifact** listing files *selected for
processing*. It is the single most misleading surface on the PR.

## Proposed fixes (ordered)

1. ⛔ **A non-zero exit from a participation/comment fetch MUST fail the barrier closed.** Never let
   an argparse rejection (or any non-zero exit) reach the barrier as `0 findings`. This alone would
   have stopped the false clearance.
2. **Distinguish `fetch_failed` from `fetch_returned_empty`** in the barrier's state model and in
   every `display_detail` it emits. `0 comment(s) found` must be unavailable as a rendering of a
   failed call.
3. **Single sanctioned oracle**: participation derived ONLY from `ci pr comments --pr-number N`,
   reading **comment bodies**. Check states, Walkthrough presence, and summary layers are
   inadmissible.
4. **Refusal-shape classifier** over comment bodies — the strings are stable and machine-detectable
   today ("Review limit reached", "couldn't start this review", "larger than the review limit of N
   diff characters").
5. **Per-bot structural priors**: PR-Agent posts exactly one `issue_comment` and **no inline
   comments by construction**. Any detector counting inline comments will always conclude it found
   nothing — which is precisely how branch-cleanup lost it. The asymmetry is already documented in
   that step's own SKILL.md; the merge-gate detector did not apply it.
6. **Compute participation ONCE, store it, read it twice.** Two dispatches independently
   re-derived the same fact and disagreed, with no reconciliation step. A re-derivation is a second
   chance to be wrong.
7. **Never forward a subordinate dispatch's coverage claim to the operator as fact.** Any coverage
   figure on the consent gate must be traceable to the sanctioned oracle, or be labelled
   *unverified*.

## Note

The bots behaved correctly and reported their own limits honestly. **The apparatus misreported two
of them in opposite directions and escalated one misreading to the operator at the consent gate.**
That is the defect worth fixing — not bot tuning. Do not act against CodeRabbit or Sourcery on the
basis of this PR; their inputs were zero-coverage for environmental reasons and nothing about their
review quality was measured.
