envelope_version=1
sender_type=plan
sender_id=plan-203-inbox-consumed-vs-missing
epic=truthful-signals
kind=landing
created=2026-07-30T09:32:40Z

## What landed

**PLAN-203 — the inbox and the resume anchor cannot distinguish consumed from missing.**
PR **#1064** (`feature/plan-203-inbox-consumed-vs-missing`), CI green, 2 reviewers compared
(coderabbit + pr-agent), 1 actionable review comment remediated in-run.

Surface: `plan-marshall:marshall-orchestrator` — `scripts/_orchestrator_inbox.py`,
`scripts/orchestrator.py`, `SKILL.md` § Canonical invocations, `standards/inbox-envelope.md`,
`workflow/resume.md`, and the three `test/plan-marshall/marshall-orchestrator/` suites.

### Deliverables as shipped

- **D1 — `inbox validate` resolves the archive.** On a miss in `inbox/`, the resolver now checks
  `inbox/archive/` and returns a distinct `location: archived` with the archive path.
  `file_not_found` retains its narrow meaning: present at NEITHER path. Consumed and missing are
  now different answers.
- **D2 — `inbox list` states which kind of zero it means.** The payload reports the resolved
  `inbox_dir` and an `inbox_state` discriminator, so `inbox_missing` / `epic_not_found` is
  distinguishable from a genuinely empty queue.
- **D3 — `resume-summary` derives the inbox counts.** Queued/archived counts are rendered from the
  inbox at read time, separately from the operator's narrative anchor, so a stale sentence can no
  longer outrank a live count.
- **D4 — GATE (mutates nothing).** The enumeration ran and **REFUTED** the request's own
  hypothesis. See the candidate-lesson messages that accompany this landing.
- **D5 — tests, each verified red pre-fix.** Distributed into D1/D2/D3; each behaviour was observed
  failing before its fix.

### Residue the epic should track

1. ⛔ **D4 refuted the "inbox count is the only drifted hand-written count" hypothesis.** Population
   swept across 7 files: **13 assertion classes are DERIVABLE, 8 are genuinely NARRATIVE.** At least
   **three DERIVABLE surfaces beyond the inbox remain unprotected**, and one of them — the `epic.md`
   Ordered Queue table — is **strictly larger** than the count this plan fixed. All are STAGED, not
   fixed, and each rides as its own `candidate-lesson` message.
2. ⭐ **The epic's theme reproduced itself inside this plan's own fix.** CodeRabbit caught
   `inbox_state` being observed AFTER the enumeration it describes — a payload that can report
   `count: 3` alongside `inbox_state: missing`, i.e. "could not look" asserted about a scan that
   did look. Fixed in-run; recorded as a candidate lesson because the archetype, not the line, is
   the finding.
3. A Q-Gate `keyword_drift` false positive and a decision-log fragmentation artifact are also
   carried as candidate-lesson messages.

### Claim labels

- OBSERVED (first-party): every deliverable outcome above, PR number, CI state, reviewer counts,
  and the D4 enumeration split (13 derivable / 8 narrative across 7 files).
- OBSERVED (review bot, verified and remediated): the `inbox_state` observation-point defect.
