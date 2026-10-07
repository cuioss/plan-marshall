envelope_version=1
sender_type=plan
sender_id=git-artifact-scanning-and-destructive-recovery
epic=truthful-signals
kind=candidate-lesson
created=2026-08-31T08:03:18Z

component=plan-marshall:automatic-review
category=bug
created=2026-08-31
bundle=plan-marshall
confidence=high
source_plan=git-artifact-scanning-and-destructive-recovery
related_finding=ec87de

# A per-bot currency exemption silently disables the currency test for the whole ANDed gate

## Context

Observed live on PR 1371, and it would have merged silently.

`review_completeness` returned `participation_complete=true` with `coderabbit=participated` at merge candidate `b9506f81a`. But CodeRabbit's newest review object is dated 2026-08-30T21:07:11Z and covers `399b9f9b..df27ad2` — it never reviewed `b9506f81a`, which was authored 21:35:08Z, 28 minutes later. The credit carried over from the previous HEAD because `coderabbit.md` declares `participation_requires_update: false`, so the currency test that catches exactly this is not applied to it.

The mechanism demonstrably works: `pr-agent`, which does not opt out, was correctly reported `participated_stale` on the same pass and only cleared once it genuinely re-reviewed. One member of the set is exempt, and the gate ANDs over the set.

The barrier only blocked at all because the caller passed `--declined-bots coderabbit`. The default path credits CodeRabbit as participated from the previous HEAD and would have merged with no signal. `proves=participation_only` is the only thing standing between this and a false green, and the pre-merge barrier re-derives participation the same way, so it misses it identically.

**Second, related gap in the same file.** CodeRabbit's refusal here was classified `refusal_class=awaitable_window` with an empty eta, but the cause is its incremental bookkeeping ("does not re-review already reviewed commits"), not a window — two triggers 21 minutes apart returned byte-identical refusals and no review object appeared. An already-reviewed-commit refusal wearing a window label sends a caller into a wait loop that cannot terminate; it needs its own class so the caller escalates instead of waiting. This run spent waits it could never have spent productively.

## Root cause

An exemption declared per member of a set was applied to the member but reasoned about as if it were scoped there. A gate that ANDs a currency predicate over N bots is only as current as its least-current member, and a member exempted from the predicate contributes an unconditional `true`.

## Proposed action

1. Make the participation gate report **which members were currency-tested and which were exempt**, so `participation_complete: true` can never be read without seeing the exemption set. An aggregate whose members were tested under different predicates must publish that split.
2. Add a `refusal_class` value for an already-reviewed-commit refusal, distinct from `awaitable_window`, so a caller escalates rather than waiting.
3. Extend `coderabbit.md`'s `rate_limit_eta_patterns` to include "Next included review available in N minutes", and `sourcery.md`'s `refusal_patterns` to include the budget wording — both were observed live and matched nothing.

## Evidence

- Finding `ec87de`, qgate `6-finalize`, severity warning, resolved `taken_into_account`
- The `barrier-ask-override` merge authorization at HEAD `b9506f81a` records the whole reasoning chain, including that the default path would have merged silently
- aspect: chat_history_analysis — the operator had to state "CodeRabbit is mandatory for this plan. If it is rate-limited wait and try again" mid-finalize, then later ask "so. CodeRabbit reviewed at least once and it is merged, correct?"
- Sibling findings in the same skill family this run: `cbd010` (Branch B anchor omission), `a7d7af` (measured-diff-size argparse rejection). All four share one shape — a documented or declared contract that the live argparse, the live bot wording, or the live currency model does not support. Worth ONE sibling plan, not four.
