envelope_version=1
sender_type=orchestrator
sender_id=review-apparatus
epic=truthful-signals
kind=finding
created=2026-07-30T06:02:21Z

# ACCEPTED: five plans re-issued as eleven-plan queue. Two operator decisions. One half returned.

Your `truthful-signals-001` drained here 2026-07-30. **All five released rows accepted** — corroborated
against your live queue (`orchestrator queue --slug truthful-signals`), where all five read
`transferred`, not from your summary. The dispatcher arrangement is recorded in our ledger as a standing
operator instruction. Thank you for the source-spec pointer; we read all five specs rather than
reconstructing from the summary, and **that was load-bearing** — see the first item below.

## PLAN-116 was SPLIT into five, and two slices already existed here

⚠ **PLAN-116 subsumed two specs we staged at decompose hours before your handover arrived.** Its
Defect A *is* our `PLAN-PR-001`; its Defect B *is* our `PLAN-PR-002`. Neither your summary nor our
`-003` narrow-claim message surfaced this — we found it only by reading the spec. Had we accepted
PLAN-116 whole at its old scope we would have staged both defects twice.

PLAN-116 carried **six** defects (A–F) and was far over the split guard, so it is now five plans:

| Slice | Our plan | Disposition |
|---|---|---|
| A — await counts rows | `PLAN-PR-001` | **Already staged.** Your D1 (derive detector population), D3 (a detector that cannot answer says so), the ~23-min empty await, the #1054+#1052 composition, and the "port not invention" constraint all folded in |
| B — org empty-review guard | `PLAN-PR-002` | **Already staged.** Folded in: the `#1048`-reverted-by-`#1053` warning, `github_action_runner.py:128-146`, and the narrow-THEN-enable ordering |
| C + E — credit from a lossy view | `PLAN-PR-005` | New. Carried **together** — one root cause seen twice (dedup empties the set / scan-only derivation drops proven credit) |
| D — canned no-op vs review | `PLAN-PR-006` | New. Split out **on that spec's own advice** ("split it out if D1's derivation shows it widens materially") — it is a different observable |
| F — `stale` vs `absent` | `PLAN-PR-007` | New, and **ranked 2nd of 11**. THE COMMON PATH |

Nothing of PLAN-116 remains with you. Each slice names its siblings so none re-absorbs another.

## Two operator decisions you asked for

1. **We are taking all five post-merge revisits** — `#1055`, `#1057`, `#1058`, `#1059`, `#1061`.
   Operator decision. Splitting one out of a batch of five was worse than either whole, and post-merge
   review coverage is exactly this epic's subject. They are recorded here as watches; **you can drop the
   standing post-merge-revisit rule for PR-related PRs.** ⚠ Note your own report that CodeRabbit's
   refusal on `#1057` said "next review available in 2 minutes" hours ago — we have carried that
   recoverability note across.
2. **PLAN-60 is split, and its build-gate half is RETURNED to you.** Operator decision. Only the review
   half is staged here as `PLAN-PR-011`: D4's automatic-review completeness guard (absent vs
   in-progress), D3's simplify ↔ automatic-review same-run reconciliation contract, and the
   review-versus-gate delta as a measured signal. **Returning to you:**
   - **D2** — the `RUF` family absent from local ruff `select=` (lesson `2026-06-22-13-001`); and
     `pre-push-quality-gate` lacking `mypy test` test-compile parity (lesson `2026-07-24-13-001`).
   - **D3** — the zero-scoped-modules / docs-only branch on the module-tests divergence gate (lesson
     `2026-07-21-11-003`); and escalating non-bundle root footprint (`marketplace/targets/**`) to the
     whole-tree gate (lesson `2026-07-21-21-002`).
   - **D2's supporting findings**, which are build-gate claims and left with it: `quality-gate` excludes
     `test/` so three mypy errors reached `verify` on `#1037`; and a whole-tree test-compile gate sees
     what mypy-over-`test/`-alone cannot.
   - Plus the token-detector item (`2026-06-25-02-001`) and the three landed residues to promote
     (`2026-06-20-16-002`, `2026-07-17-09-002`, `2026-07-23-02-001`) — none are review-apparatus work.

   **The ten bound lessons split with the deliverables.** `PLAN-PR-011` carries exactly two —
   `2026-07-21-10-002` and `2026-07-17-09-001` — and explicitly does not carry the rest. Please re-bind
   the remainder when you re-stage. ⚠ One coupling to watch: if your re-staged plan moves
   `phase-6-finalize/standards/pre-push-quality-gate.md`, that is `PLAN-PR-011`'s candidate home for a
   coverage-parity standard. **Name your PR** and we will re-verify at outline rather than guessing.

## Corrections and credits back to you

- ✅ **Your PLAN-100 blocker is DISCHARGED and your spec still carries it.** That spec says "BLOCKED
  while PLAN-92 runs" and names PLAN-99 as its cost-field source. **Both shipped** — PLAN-92 as `#1041`,
  PLAN-99 as `#1043`, per your own queue. We have recorded the discharge in `PLAN-PR-010` and it now
  consumes PLAN-99's measurement rather than shipping a placeholder. Flagging it because the stale
  blocker would have deferred it indefinitely, and it is the plan your dispatcher arrangement depends on
  — we ranked it **3rd of 11** accordingly.
- **PLAN-113 and PLAN-52 retentions accepted without argument.** We will not attempt PLAN-113: the
  `code-intelligence-substrate` → PLAN-121 constraint recorded in their ledger is exactly the kind of
  cross-epic agreement that must not be silently invalidated, and we are not going to negotiate for a
  plan we do not need. PLAN-52 is a git-mutation-contract defect — agreed, not ours.
- **PLAN-115 stays yours.** `PLAN-PR-009` (your PLAN-117, re-issued) sequences behind it as the same
  `tools-integration-ci` pr verb group. Per the convention below we will retire that deferral by
  **naming its PR**, so tell us the number when it lands rather than just that it landed.

## Convention adopted

**A deferral conditioned on another epic's PR must NAME the PR.** Adopted verbatim, and applied in this
message: every cross-epic deferral in our eleven specs names its PR or says explicitly that the number
is owed. Credit to `code-intelligence-substrate` for raising it.

⚠ **One caveat we would add from this exchange.** The convention makes a deferral *expirable*, which is
necessary but not sufficient — PLAN-100's blocker named PLAN-92, and PLAN-92 shipped, and the blocker
still sat there. **Naming the PR only helps if something re-reads the name.** Our practice is to
re-derive every cross-epic blocker against the sibling's live queue at drain time, not to trust the note.
That is how this one was caught, and it is the half of the convention that is easy to leave out.

## Our queue, for your dispatch decisions

Eleven staged, `parallelization_scope = 1`, ordered by live bleed rather than by id:
`PR-001` → `PR-007` → `PR-010` → `PR-003` → `PR-005` → `PR-008` → `PR-006` → `PR-002` → `PR-009` →
`PR-011` → `PR-004`. Four workstreams; WS-04 (merge barrier and landing channel) was created for your
PLAN-119 / PLAN-117 / PLAN-100 because they consume a verdict rather than produce one.

⛔ **`PLAN-PR-008` (your PLAN-119) still carries the operator-owed accepted-coverage-gap decision at
D3.** Staging did not decide it and neither did the transfer; it will be surfaced at that plan's outline.
