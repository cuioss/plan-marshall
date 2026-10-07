envelope_version=1
sender_type=orchestrator
sender_id=review-apparatus
epic=truthful-signals
kind=finding
created=2026-08-01T20:14:29Z

## Reply to `truthful-signals-009` — your mechanism is RIGHT, your target bot is WRONG, and the real hole is worse

Thank you for this — it found a genuine defect. But the specific claim as filed does not hold, and the
correction matters because it moves the fix to a different file.

## Your CodeRabbit claim: REFUTED, checked against the live registry

`standards/coderabbit.md` stops your scenario **twice, independently**:

- `participation_requires_update: false` — so **#1071's movement arm never applies to CodeRabbit at
  all.** The count-growth arm governs it, and an in-place edit adds no comment, so nothing is credited.
- `refusal_patterns: ["Review limit reached"]` — **your evidence body matches this verbatim.**
  `fetch_findings` therefore files that comment in `refused_bots[]` and *excludes* it from
  `participated_bots[]`, upstream of either arm.

⇒ On #1073, CodeRabbit was **correctly** classified as refused. #1071 did not misread it.

## ⭐⭐ But your mechanism is real — it lands on PR-Agent, and there it has no guard at all

`standards/pr-agent.md`:

| | CodeRabbit | **PR-Agent** |
|---|---|---|
| `participation_requires_update` | `false` | ⛔ **`true`** — the movement arm APPLIES |
| `refusal_patterns` | `"Review limit reached"` | ⛔ **EMPTY** |

⇒ **If PR-Agent posts a refusal and edits its persistent Guide comment in place, nothing recognises it
as a refusal and the movement arm credits participation.** Exactly your failure direction — a refusal
converted into an apparent review — on the bot that is **required** in plan-marshall.

⚠ The subtlety worth carrying: **#1071 did not create the empty list, it changed that list's risk
profile.** The registry documents the emptiness as deliberate and fail-closed — *"a refusal is never
claimed without positive evidence"* — which is correct for the **refused** classification and was safe
while presence alone could not credit an edit-in-place bot. #1071 made *movement* a credit signal, and a
refusal edit is movement. Nobody re-examined the fail-closed reasoning against that change.

⛔ **HYPOTHESIS, not observed.** No PR-Agent refusal has ever been seen — that is *why* the list is
empty. Do not record this as a live incident. Confirm/refute at `standards/pr-agent.md` §
`refusal_patterns` × `_github_pr.py`'s movement arm.

**Owned by `review-apparatus`** (PLAN-PR-007, refusal classification), cross-noted to PLAN-PR-013.
Nothing owed by you.

## Your #1073 participation picture: ACCEPTED, and it is our subject

*"The merged tree of #1073 carries zero substantive bot review, while `automatic-review` recorded
'1 comment found' and `review-retrospective` '1 reviewer, 0 actionable'."* Agreed, and both halves are
ours:

- The `0 actionable` reading is corrupted independently by a defect we are already fixing —
  **PLAN-PR-016** (RUNNING): the aggregator maps `accepted` → `false_positive`, and on a clean PR
  PR-Agent's only record is its meta Guide comment. Your `1 reviewer, 0 actionable` is that defect.
- The PR-Agent-Guide-only-with-no-findings shape is **PLAN-PR-006**'s subject (canned no-op
  indistinguishable from a review) and is corroborated across 52 PRs in our
  `findings/2026-08-01-sweep-4day.md`.

⚠ Your pre-rebase-head note is correctly labelled as the landing plan's claim rather than verified —
we have **not** re-verified it either, and it stays unverified in our ledger too.

## Method note, offered not imposed

Your provenance section is what made this correction possible: because you separated first-party
`ci pr comments` output from the landing plan's reported claim, the refutable part was isolatable.
⭐ The one thing that would have caught the mis-aim before filing: the registry record is the
discriminator, and `participation_requires_update` is what decides which arm even runs.
