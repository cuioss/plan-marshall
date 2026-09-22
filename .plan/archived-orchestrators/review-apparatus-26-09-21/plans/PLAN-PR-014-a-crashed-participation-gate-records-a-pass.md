# PLAN-PR-014: A crashed participation gate records a pass, and the zero-participation case is what crashes it

epic: review-apparatus
workstream: WS-04

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-marshall-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

## Provenance — inbox `code-intelligence-substrate-003.md`, drained 2026-07-30

Forwarded from the PLAN-11 landing on PR **#1063** and removed from that epic's ledger. Staged rather
than folded: the sender offered `PLAN-PR-005/006/007` as candidate homes, but all three concern how
participation is **classified**, while this defect is that the classifier **never ran** and the pipeline
recorded a pass anyway. ⛔ **This is ranked FIRST in the epic queue.** It is a live false-GREEN with a
reproduction confirmed at the call site, and a false-green that admits unreviewed code to a merge
outranks PLAN-PR-001's wasted 600 s per loop-back.

## Objective

`review_completeness check` — the one component that models participation properly — exits 2 on the
zero-participation input, and an `exit_code=2` is indistinguishable to the calling step from never
having run. The step records `outcome: done`. Every surviving signal reads green.

⭐ **The gate crashes precisely in the scenario it exists to detect.**

## Deliverables

1. **D1 — quote the interpolations at EVERY call site.** ⛔ **Root-caused, OBSERVED, no investigation
   owed** — see Claim Labels. The documented invocation interpolates list flags **unquoted**
   (`--participated-bots {participated_bots}`), so an empty resolution leaves the flag with no argument
   and argparse rejects with `expected one argument`. ⚠ **DERIVE the site population before fixing** —
   two files are confirmed and **five flags per site share the shape** (`--required-bots`,
   `--optional-bots`, `--participated-bots`, `--in-progress-bots`, `--refused-bots`). A fix that quotes
   the one flag named in the incident report leaves the other four live. This project's most-repeated
   defect is the one-site fix against an N-site defect.
2. **D2 — a non-zero exit from `review_completeness` MUST block `mark-step-done` for
   `automatic-review`.** ⭐ **A crashed gate is an UNKNOWN verdict, never a pass.** This is the
   deliverable that holds even if D1 misses a site: D1 removes the known crash, D2 makes any *future*
   crash loud. ⛔ Ship both — D1 alone leaves the class open, D2 alone leaves a reproducible crash.
3. **D3 — the zero-participation input must be accepted, not rejected.** That input is not malformed;
   **it IS the finding.** ⚠ Note the surface already half-agrees with itself: `--required-bots`'s own
   help text states *"An empty list is a valid configured state (quorum vacuously satisfied)"* — so the
   contract already declares empty admissible while the invocation shape cannot express it. Settle
   whether the fix belongs in the caller (quoting), the parser (`nargs='?'` / a default), or both, and
   state the choice.
4. ⭐⭐ **D4 — a check conclusion MUST NOT be substituted for a participation record, NOR for a
   findings-handled record.** The second half was added 2026-07-30 on verified `#1066` evidence and is
   the sharper of the two, because there the check aggregate was **factually correct and still
   misleading**:

   - **VERIFIED** (`ci pr comments --pr-number 1066`, orchestrator-run — the forwarding epics recorded
     that *nobody* had run it): CodeRabbit posted **8 comments incl. a Major**, its 3 inline review
     comments timestamped **11:58:43Z**. The PR merged at **12:06:46Z**, **8 minutes later**, with all 8
     **unresolved**.
   - ⇒ The `11/11 checks pass incl. CodeRabbit` aggregate was **right** — CodeRabbit's check was
     genuinely `SUCCESS` because it genuinely reviewed. ⛔ **The error was in what "success" was taken to
     mean.** A check reports that the bot **RAN**; it says nothing about whether its **OUTPUT was
     handled**. The aggregate conflated the two and a Major finding merged unaddressed.
   - ⭐ **This also settles a question the forwarding epic left open**: the earlier `SUCCESS` flip was NOT
     an auto-resolve, and the recorded discount (*"CodeRabbit check pending = rate-limit refusal, not a
     signal"*) was **correct when written and then legitimately superseded by a real review**. ⚠ So the
     generalisable half they proposed — *"a discount must be a machine fact the aggregate consumes, not
     a note beside it"* — is **right in principle but aimed slightly wrong here**: on `#1066` the
     re-crediting was *correct*. Build D4 for the check-vs-handled conflation, not for a discount that
     needed to survive.

   **The original obligation, unchanged:** A bot's check
   conclusion is `SUCCESS` whether it reviewed, refused on quota, or declined as redundant: **there is
   no conclusion value meaning "did not review"**, so the fallback signal is *structurally incapable of
   dissent*. Admissible evidence is an evidence-typed `bot_kind:evidence_kind` pair only. `ci pr
   comments` presence is **necessary but not sufficient** (a comment *from* a bot is not a review *by*
   it); a check conclusion is not even necessary.
5. **D5 — tests, each verified to FAIL pre-fix.** (a) The zero-participation invocation completes and
   returns `participation_complete: false` rather than exiting 2. (b) A non-zero `review_completeness`
   exit blocks `mark-step-done`. (c) ⭐ A regression pinning the `#1063` shape: gate exits non-zero →
   step does NOT record `done`. (d) The call-site population D1 derives is **derived**, non-empty, and
   every member asserted — copy `test/_shared/_dispatch_roster.py`.

## Claim Labels

- ⭐ **OBSERVED — reproduced live by the orchestrator against the executor, not read from the message.**
  `review_completeness check --plan-id … --required-bots pr-agent --participated-bots` →
  `error: argument --participated-bots: expected one argument`, argparse exit 2. The zero-participation
  case is a **confirmed** crash, not a hypothesis.
- ⭐ **OBSERVED — the call site is the cause, and there are at least two.**
  `phase-6-finalize/standards/branch-cleanup.md:631` and `automatic-review/SKILL.md:612` both document
  `--participated-bots {participated_bots}` with an **unquoted** placeholder. Empty resolution ⇒ flag
  with no argument ⇒ exit 2. ⚠ **Re-ground by heading, not line number** — hot surface.
- OBSERVED: the live `check` surface is `--plan-id`, `--required-bots`, `--optional-bots`,
  `--participated-bots`, `--in-progress-bots`, `--refused-bots`, `--triage-ran`. **No `--enabled-bots`
  exists** on this script, nor anywhere in `github_pr.py`.
- ⛔ **OBSERVED — TWO distinct argparse rejections exist and they are INDISTINGUISHABLE in the log.**
  Both exit 2 and both surface as `failure_kind=argparse_rejection`:
  1. `--participated-bots` with no value → `expected one argument` (the zero-participation case, D1/D3);
  2. `--enabled-bots …` → `unrecognized arguments` (a **retired** flag still documented in stale plugin
     cache `0.1.1232`'s copy of `review_completeness.py`).
  ⇒ **HYPOTHESIS: #1063's logged rejection was mechanism 1.** The sender asserts it, but the signature
  cannot discriminate — it may have been mechanism 2. **Confirm/refute artifact**: the argv actually
  recorded for that invocation in `#1063`'s script/work log under `.plan/local/plans/`. ⚠ The
  orchestrator could not read it (outside its carve-out). **Do not scope D1/D3 as if the attribution
  were settled** — but note D2 and D4 are correct under *either* mechanism, which is why they are the
  load-bearing pair.
- OBSERVED (reported by the sender as orchestrator-verified on their side, consistent with our own
  #1063 read): checks were **10/10 SUCCESS** including `Sourcery review — SUCCESS/pass`, with
  `mergeable`, `merge_state: clean`, while Sourcery had hard-quota-refused both rounds and produced no
  review artifact. **A green check set here was not weak evidence of review — it was NO evidence, and it
  was indistinguishable from strong evidence.**
- HYPOTHESIS (the sender's, unverified by us): CodeRabbit "explicitly declined to re-review an
  already-reviewed commit" and pr-agent was never re-triggered. ⚠ Our own #1063 read found CodeRabbit's
  walkthrough `updated_at` DID move to 07:43:06Z after the final commit, so *declined* may be too strong.
  **Confirm/refute artifact**: the CodeRabbit reply body at 07:43:01Z on #1063. Settle it before citing
  a decline.
- OBSERVED (operator deviation, recorded for completeness, not a defect): the trigger-A re-review gate
  was deliberately not re-fired on that loop-back (logged WARNING) because it would have re-asked a
  just-answered question. Defensible — but it left the loop-back commit with **no** re-review path,
  neither automatic nor gated.

## ⛔ Prohibited remedies

- **Do NOT fix this by making `review_completeness` exit 0 on error.** That converts a loud crash into a
  silent pass — the same false-green in a new location.
- **Do NOT fix it by having the caller skip the gate when the participation list is empty.** Empty
  participation is the case the gate exists for; skipping it is the defect, restated as a feature.
- ⚠ **Do NOT widen `optional_bots` to make the quorum pass.** `optional_bots` is the sanctioned way to
  accept a *configured* bot's silence, not a lever for making a crashed gate green.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/branch-cleanup.md`
  (the `review_completeness check` invocation block).
- OBSERVED: `marketplace/bundles/plan-marshall/skills/automatic-review/SKILL.md` (the second
  invocation, and the `mark-step-done` path D2 must gate).
- OBSERVED: `marketplace/bundles/plan-marshall/skills/automatic-review/scripts/review_completeness.py`
  (the argparse surface, for D3).
- HYPOTHESIS: the `mark-step-done` implementation for `automatic-review` (verify-at-outline) — D2's
  actual enforcement point, which may be in the skill doc rather than a script.
- OBSERVED: the `automatic-review` / pre-merge-barrier tests.

## Dependencies and Sequencing

- Depends on: none. ⭐ **Deliberately NOT sequenced behind PLAN-PR-007 or PLAN-PR-008**, unlike the rest
  of the participation cluster: D1–D3 are a call-site and argparse fix that touches no taxonomy, so
  coupling it to PR-007's taxonomy or to PR-008's **operator-owed** D3 would delay a confirmed live
  false-green behind an unanswered question. **Ship it first.**
- ⛔ **Overlaps `branch-cleanup.md` with PLAN-PR-008, PLAN-PR-009 and PLAN-PR-013. Sequence, never
  pair** — four plans now share that file.
- ⚠ **Feeds PLAN-PR-008's D1.** "The checker crashed" is a barrier terminal state its population
  derivation must enumerate, and it is **not** a bot-refusal state. Landing this first means PR-008's D1
  derives against a barrier that can no longer crash silently.
- ⚠ **Complements PLAN-PR-013.** Both are false-greens on the same merge gate, with different
  mechanisms: PR-013 credits a review of the wrong commit; this one records a pass when the gate never
  ran. ⛔ Do not consolidate — the fixes share no code.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/review-apparatus/plans/PLAN-PR-014-a-crashed-participation-gate-records-a-pass.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/local/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-marshall-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
