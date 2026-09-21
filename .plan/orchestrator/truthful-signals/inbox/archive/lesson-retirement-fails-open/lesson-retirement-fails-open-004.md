envelope_version=1
sender_type=plan
sender_id=lesson-retirement-fails-open
epic=truthful-signals
kind=candidate-lesson
created=2026-08-08T18:02:59Z

component=pm-plugin-development:ext-self-review-plan-marshall
category=improvement
bundle=pm-plugin-development

# Re-run self-review detectors over the FIX diff, not only the original diff

## Context

Plan `lesson-retirement-fails-open` ran `pre-submission-self-review` four times.
The finding counts were 3, then 4, then 1, then clean. The second round is the
interesting one: two of its four findings were direct residue of the FIRST round's
own fixes.

- `cb6b52` — `manage-lessons/SKILL.md` frontmatter still advertised
  `restore-from-plan` as three-state after finding `5e7268`'s fix added the fourth
  value. The fix updated the body table, the scripts-table row, the argparse help,
  `planning.md` and `plan-retrospective`, and missed the frontmatter that
  summarises the same contract.
- `50d38c` — the `manage-status` Scripts-table `delete-plan` row still enumerated
  3 of what findings `a06593` and `5e7268` had just made a 5-value vocabulary. The
  finding's own text records the cause: "findings a06593 and 5e7268 both updated
  the detail table but neither updated this row".

The pattern continued past self-review into PR review. CodeRabbit's `c51665`
reported a `destination.exists()` / `shutil.move()` TOCTOU pair. The fix claimed
the destination with `os.open(O_CREAT|O_EXCL)`. pr-agent then found, in round 2,
that the claim fd is closed before `shutil.copyfile` reopens the destination by
path — reintroducing the window inside the fix for the window. It also found that
the fix hardened one member of a structurally identical pair and left its twin
untouched.

Six of the eight self-review findings and both pr-agent findings are instances of
the plan's own thesis, and the ones that cost the most rounds were introduced by
fixes rather than by the original implementation.

## Root cause

Each self-review round scans the diff as it stands, but nothing gives the fix diff
a first-class second pass with the same detector set that produced the finding
being fixed. A fix that touches five doc surfaces and misses a sixth is exactly
what the `contract_drift` and `description_body_drift` detectors exist to catch,
and they only see it a whole round later — if the round budget allows.

## Proposed action

After the fix-findings envelope returns, re-run the detector set that produced each
fixed finding over the fix diff specifically, before the next full round. At
minimum re-run the enumeration- and vocabulary-shaped detectors
(`contract_drift`, `description_body_drift`, `same_document_contradiction`,
duplicate-claimable-key) against every file the fix touched, since a vocabulary
change fans out across doc surfaces by construction.

## Impact

Repair rounds, not first-pass work, dominated this plan's cost: 8 of the 12
counted phase-6 dispatches were self-review or PR-review repair, and phase 6 alone
exceeded the whole-plan token error anchor. Catching round-1 fix residue inside
round 1 would have removed a full round.

## Evidence

- artifact: `artifacts/findings/qgate-6-finalize.jsonl` — 8 findings over 4 rounds (3, 4, 1, clean); `cb6b52` and `50d38c` both name the round-1 fixes as their cause
- artifact: `review-retrospective.md` — "pr-agent observed that the claim fd is os.closed before shutil.copyfile reopens the destination by path"; "the classic asymmetric-fix defect — hardening one member of a producer-consumer pair and leaving its twin"
- aspect: chat_history_analysis — 2 loop-backs of a maximum 3, both 6-finalize to 5-execute
