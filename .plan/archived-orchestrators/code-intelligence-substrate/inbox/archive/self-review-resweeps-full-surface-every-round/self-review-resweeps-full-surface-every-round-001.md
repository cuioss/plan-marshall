envelope_version=1
sender_type=plan
sender_id=self-review-resweeps-full-surface-every-round
epic=code-intelligence-substrate
kind=landing
created=2026-08-09T03:20:47Z

## What landed

**PLAN-CIS-031 `self-review-resweeps-full-surface-every-round` — merged as PR #1126, squash-merged via the platform merge queue at `72982d3d4`.**

Realized footprint: 19 paths (17 source/test + 2 architecture artifacts). `references.affected_files` declared 14, so the plan under-declared its own blast radius by 3 real test modules — the head-anchor and reachability regressions D2's own change forced.

All 6 deliverables fulfilled:

| D | What shipped |
|---|---|
| D1 | Per-round self-review cost curve re-derived, population published first |
| D2 | `--since-ref` delta scoping for the self-review round + `missing_head_at_completion` refusal on an unanchored head-dependent verdict |
| D3 | Whole-defect-class sweep obligation before a round closes, with its bound stated at the point of obligation |
| D4 | Per-round detector mix (`counts.by_family`) from the candidate-list registry |
| D5 | Loop-back iteration ceiling enforced at the admission boundary on both knob branches |
| D6 | Landed-footprint scoping + the documentation-only loop-back question settled for the whole-tree gate arms |

## The measured result — the epic's own instrument, measured on itself

**`pre-submission-self-review` ran SIX rounds finding 5, 5, 2, 3, 4, 0 and consumed 1,528,196 tokens on a 19-file diff.**

That is 61% of phase 6-finalize and 31% of the whole plan (4,900,190 dispatched tokens reconstructed; `metrics.md` publishes 2,392,836 with an `(n=4/6)` partiality marker because 6-finalize never closed its row).

The rework chain is the finding, not the cost:

- **Rounds 2, 3, 4 and 5 EACH found defects that the PREVIOUS round's own fix had introduced or left.**
- The recurring class was one thing throughout: *a restated count/range/endpoint/closure claim about a set declared elsewhere*.
- **Hand-correcting it failed three consecutive times.** Round 3 replaced a wrong digit with a wrong number-word. Round 4's rewrite removed an explicit "Two entry shapes" count and reintroduced the same cardinality in prose, carrying the identical undercount. Round 4 also wrote a *review-history* justification into a standards document (violating "No version history" / "Current state only") whose own count — "three consecutive rounds" — was itself wrong; the store shows two.
- **Convergence came only from DELETING the restated claims**, not from correcting them. The durable fix landed as: state no count, range, endpoint, or per-key correspondence about an enumeration that lives elsewhere — cross-reference the section and stop.

Round 5 additionally **refuted a premise round 4's fix rested on**: `_findings_core` dedups on the `(title, content_discriminator)` pair, not on title alone, so the "identical titles collapse the cohort" justification round 4 wrote was false against the live code. The `MUST NOT` it justified was correct; its stated reason was not.

This is a measured rework-chain on the epic's own instrument. It corroborates lesson `2026-08-08-21-003` first-party (the lessons-housekeeping step recorded exactly that at HEAD `57f6c01a9`), and it adds a delta that lesson did not carry: **correction is not a remedy for this class; deletion is.**

## Verdicts, with their populations

**D1 GATE verdict: `confirmed` — and it is a DIRECTION, not a coefficient.**

Population stated before the curve, as the deliverable's own criteria required: `distinct_plans_scanned=5`, `plans_with_at_least_one_round=3`, `plans_with_two_or_more_rounds=2`. The curve therefore rests on **2 plans and 4 rounds**, and **3 of those 4 rounds carry `outcome=error`**, so the token counts include failed-round work and are not clean per-round costs. All 4 rounds fall in one calendar day.

Observed R2:R1 ratios were **0.87** and **1.40** (mean 1.14) — both at or above parity, neither anywhere near the small fraction a delta-scoped round would produce. The mechanism prediction discriminates sharply, so the direction holds at n=2. **Do not quote 1.14 as a calibrated multiplier, and do not report a token saving** — the spec's anti-goal forbids it and the population does not support it.

**D2 delta scoping demonstrably works, and the termination criterion held.**

Round 2 scoped 4 files / 27 candidates against a 17-file / 71-candidate full surface; round 3 scoped 2 files / 22 candidates; round 5 scoped 3 files / 33 candidates. **Round 6's `done` was recorded off the FULL-surface confirmation sweep (76 candidates), never off a clean delta round** — the closure obligation was honoured.

**D5 shipped unexercised.** The ceiling never bound: the run converged at round 6 before any finding could strand at it. It ships correct-by-review, unverified-in-anger.

## Review coverage on PR #1126: effectively zero

1 of 3 bots participated.

- **pr-agent** — participated. Raised 2 focus areas. **Both REFUTED against live code.** The "Scoping Bug" rested on a premise `_resolve_footprint`'s own typed two-state contract contradicts; its suggested guard would have been **vacuous, with an unreachable `else` branch**, and its only reachable effect would have turned a documented fail-safe into a fail-quiet clean verdict — the opposite of the intended hardening. The "Unhandled Exception" area named three exception classes that are already handled and one (`YAMLError`) that cannot occur, because there is no YAML library anywhere in that read path.
- **CodeRabbit** — genuine rate limit. **Never awaited.**
- **Sourcery** — refused on a **DIFF-SIZE cap of 150,000 characters**.

The last two are **different failures needing different remedies**: waiting clears a rate window; it does not clear a size cap. Treating both as one "bot did not participate" class is the gap.

## Residue the epic should track

Six items outlive this plan. Each is filed as a separate `candidate-lesson` message; the two below are the ones with a deliberate decision attached.

1. **Finding `f2928f` (pending, deliberately NOT fixed): `_detect_count_prose` opens only `SKILL.md` while its sibling `_collect_skill_contract_sources` globs `standards/*.md`.** A stale count in a `standards/*.md` doc is invisible to **every** self-review round, delta or full — the closing full-surface pass is not the backstop for that class a reader would assume it to be. Two of this run's own findings were found **only because a reader was pointed at the file by name**. Left unfixed on purpose: changing detector behaviour after the round-6 clean full-surface verdict would have invalidated that verdict and restarted the loop.

2. **`duplicate_claimable_keys` and `discard_without_report` carry `in_total: true` but have NO consuming check.** They inflate `counts.total`, the candidate-count dispatch gate, and the "`{N}` candidates examined" verdict — counted as examined when nothing examines them. **Volume-read-as-coverage, inside the contract that exists to detect it.** Recorded in the doc, not resolved, because the two available remedies move the published count in **opposite** directions (add checks → the count is honest and stays high; drop `in_total` → the count falls and the verdict shrinks). That is an epic-level call, not a plan-level one.

3. **The `[DISPATCH]` audit trail undercounts the plan's most expensive step 6:1.** `pre-submission-self-review` spawned six times and emitted one `[DISPATCH]` line; `finalize-step-plugin-doctor` spawned twice and emitted one. The emission is wired to first entry, not to the loop-back re-fire.

4. **19 pending Q-Gate findings reached merge.** `handshakes.toon` carries rows for `1-init` … `5-execute` and **none for `6-finalize`**, and `_BLOCKING_BOUNDARIES` is exactly `{6-finalize}` — so the gate that counts `qgate` as actionable never evaluated the post-self-review store. The fixes did land; only the records stayed `pending`. The gate is inert on this path, so "pending findings" is not a trustworthy merge signal here.

5. **`check-routing-decisions --diff-file` reports a vacuous SKIP on the invocation its own SKILL.md documents.** The documented plan-relative form (`work/footprint.txt`) resolves to nothing and yields `status: skip, detail: no realized footprint`; the identical file passed absolute turned the same check into `status: fail` on a real `mis_prune:sonar-roundtrip` violation.

6. **`termination_cause` has no member for "returned with findings."** All five finding-bearing self-review rounds are stamped `error` — the same token a crashed dispatch gets. The plan's five most productive dispatches read as failures in the only per-dispatch ledger that exists.

Items 3, 4 and 5 are each **a check reporting a clean or absent signal over work it never examined** — the epic's confident-signal-hides-a-caveat theme, observed three times inside one plan's own instrumentation.

## Housekeeping

- Lessons housekeeping: 0 removed, 1 adapted (`2026-08-08-19-006`), 18 retained over 18, re-fired at HEAD `57f6c01a9` after the stale `1ad5977dc` anchor.
- Deploy target regenerated (1131 entries, version `0.1.1330`); plugin cache synced (10 bundles); on-main executor regenerated.
- 10 argparse rejections across 1,095 script invocations (8 unique), the most frequent being `architecture search --plan-id` (3×) — `architecture` takes `--plan-id` as a top-level router flag, not on the `search` subparser.
- Run was fully unattended: 2 operator-authored turns in 1,039 raw transcript turns, zero pivots, zero permission prompts, zero gate answers.
