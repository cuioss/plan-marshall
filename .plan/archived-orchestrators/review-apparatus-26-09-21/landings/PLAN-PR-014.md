# Landing — PLAN-PR-014 `crashed-participation-gate-records-a-pass`

epic: review-apparatus · analysed 2026-08-01 · **PR #1070 MERGED** `40bfba08c` at `2026-08-01T19:18:00Z`
(verified via `gh api`) · 2/2 deliverables, 22/22 finalize steps · 16 inbox messages, all drained

## What landed

- **Seven list flags relaxed to `nargs='?'` / `const=''`** across TWO parsers — `review_completeness.py
  check` (×5) and `github_pr.py fetch_findings` (×2). ⭐ Larger than the spec's 5-flags-one-parser scope.
- All four documented call sites quoted.
- **An UNKNOWN verdict branch** in `automatic-review/SKILL.md` and `branch-cleanup.md`: a non-zero exit
  OR a return missing the field is UNKNOWN, never a pass, **with the force-done hatch explicitly
  withdrawn from it**.
- **A normative prohibition** in `bot-participation-contract.md`: a check conclusion is neither
  participation evidence nor a findings-handled record.
- Tests whose flag populations derive from the live argparse surfaces, with vacuity guards.

## ⭐⭐ The mechanism correction — the spec was wrong, and the plan says so

The crash was **never** the unquoted placeholder. `.plan/execute-script.py:989` strips every empty-string
argument before argparse runs, so `--flag ""` and a bare `--flag` are indistinguishable downstream.
**Quoting could never have fixed it; `nargs='?'` was doing all the work, for a reason the docs stated
incorrectly.** The plan had already shipped four callouts repeating the wrong story and corrected them
in `5d10ad536`.

⚠ **Orchestrator record, kept honest**: the mechanism finding (from API-Sheriff #138, verified at the
executor) was correct and the operator relayed it. The *alarm* built on it — "PR-014's remedy is
refuted, relay urgently" — was **wrong**, because the plan had already shipped `nargs='?'` before the
alarm was raised. Filed at the time as an orchestrator failure mode; recorded here so the useful half
and the wrong half are not remembered as one thing.

## ⛔ The landing message preceded the merge by 13 minutes

The `kind=landing` inbox message was created **19:05:08Z** and says *"merging now"*; the merge completed
**19:18:00Z**. `lessons-capture` is order 60, `branch-cleanup` order 70 — so the landing message is
**written before the merge and structurally cannot carry the outcome**.

⭐ **This is `PLAN-PR-010`'s target defect, observed live on one of our own plans** — stronger evidence
than anything in that spec, and the reason PLAN-PR-014 was NOT marked shipped when the message arrived.

## ⭐ Counter-example — the merge did NOT outrun the review

The merge went through on a known-partial review at operator direction, and the post-merge sweep came
back **clean**: CodeRabbit had posted `✅ Confirmed as addressed` on both its findings.

⚠ Recorded deliberately. The standing post-merge-revisit obligation describes a risk that materialises
*often*, not always; logging only the failures would quietly convert it into a certainty. Two things
stay distinct: **the disposition was the operator's, the clearance was evidence.** Neither licenses the
other, and this run must not be cited as precedent for merging on a partial review.

## Inbox — 16 messages, all valid, all drained

| Retained (review-domain) | Routed to |
|---|---|
| `classify_bot` participation-precedence launders a live refusal into a pass | **PLAN-PR-013** |
| `github_re_review` counts a refusal ACK as a match | **PLAN-PR-013 / PR-007** |
| Trigger-B self-contradiction can make the REQUIRED bot structurally untriggerable | **PLAN-PR-008** |
| A comment carrying the documented ignore-pattern marker survived the noise pre-filter | **PLAN-PR-016** |

12 delegated to `truthful-signals` (msg `review-apparatus-010`) — the executor-strip lesson, the
UNMEASURED empty-flag population, a second semicolon-in-`manage-logging` sighting, and the whole
8-message retrospective batch, every one of which self-suggested that epic.

## Feeds

- **PLAN-PR-013** — gains TWO confirmed mechanisms (participation-precedence laundering; refusal-ACK
  counted as a match). ⛔ The spec forbids consolidation for the wrong-commit class; honour that.
- **PLAN-PR-016** (running) — msg `-007` is the SAME producer pre-filter it already owns, one bot over.
  ⚠ Whether it is in scope is the plan's call at outline, not a directive from here.
- **PLAN-PR-008** — Trigger-B self-contradiction is a barrier-reachability defect in its surface.
- **PLAN-PR-010** — the 13-minute gap above is its confirming instance.
- **PLAN-PR-015** — unblocked by this landing (the `branch-cleanup.md` collision is gone).
