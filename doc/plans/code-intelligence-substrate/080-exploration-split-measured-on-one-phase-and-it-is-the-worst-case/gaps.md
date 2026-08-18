# Gaps — 080-exploration-split-measured-on-one-phase-and-it-is-the-worst-case

The run itself did the right thing: it halted at its own D0 gate, and I re-derived that gate's answer
independently (no `metrics.toon` tracked in git — `git ls-files "*metrics.toon"` → 0; no
`.plan/local/archived-plans/` on disk — `ls .plan/local` → `logs` only; `.gitignore:46` at the run's base sha
`3a5e2ca` ignores `.plan/*`). Every process claim in `report-01.md` — PR #1178's two-file docs-only diff,
zero inline review threads, both comment ids and bodies, the `Co-Authored-By` trailer, the sibling-060
directory-name correction — is accurate. What remains is of two kinds. First, the report's technical
justification for the halt is wrong in two places: it states that the instrument D1 needs already exists in
`audit.py`, when in fact no shipped check reads the three exploration sub-source fields that *define* D1's
split, and the closest check pools all phases into one per-plan figure that D1 explicitly forbids. Second,
the consequent work — building that reporter, then running it over a real corpus — is entirely outstanding,
and the reporter half of it does **not** need the corpus and could be built in a cloud clone today.

## G1 — Correct report-01's claim that the audit checks read D1's counters

- **Kind:** report-defect
- **Severity:** medium
- **Topic:** measurement/metrics
- **Where:** `doc/plans/code-intelligence-substrate/080-exploration-split-measured-on-one-phase-and-it-is-the-worst-case/report-01.md:44-48` (§ "D0 — the gate, in detail"); the same error is repeated in the sub-agent finding table at `report-01.md:97`
- **Evidence:** the report says the `exploration-share` / `billing-composition` checks read
  "`{exploration,work,execute,orchestration,unclassified}_result_bytes` / `_tool_calls` counters — the exact
  per-phase exploration counters D1 collects." D1's split is defined in `plan.md:29-31` as
  index-answerable / doc-residency / unattributed, which is a different field family:
  `marketplace/bundles/plan-marshall/skills/manage-metrics/scripts/manage-metrics.py:3411-3420`
  (`_EXPLORATION_SUBSOURCES = ('index_answerable', 'doc_residency', 'unattributed')` →
  `exploration_{sub}_bytes`), documented as *"Deliberately SEPARATE from `_EXPLORATION_COUNTER_FIELDS` …
  they partition ONE bucket's bytes, they are not a sixth bucket"* (`manage-metrics.py:3413-3417`).
  `grep -rn "index_answerable\|doc_residency" .claude/skills/audit-archived-plan-retrospectives/` → **0**
  matches (control: 33 matches under `marketplace/` and `test/`).
- **Why it matters:** the sentence is the load-bearing premise of the halt's "080 is measurement-only,
  nothing is git-derivable here" argument, and it made the run's own verification sub-agent corroborate the
  error instead of catching it (`report-01.md:97`). A reader of this report concludes the epic's central
  split is already reportable when it is not.
- **Action:** state the correction in `report-02.md` when plan 080 is resumed (do not rewrite the dated
  record): name `exploration_{index_answerable,doc_residency,unattributed}_bytes` as D1's actual inputs,
  name their writer (`manage-metrics enrich` / `cmd_generate`), and state that no audit check reads them.
- **Done when:** `report-02.md` (or the resumed plan's report) contains an explicit correction naming the
  three sub-source fields as D1's inputs and stating that `report-01.md:44-48` misidentified them.
- **Effort:** S (<1h)
- **Risk if fixed:** none — a record correction, no code touched.

## G2 — Correct the residue's "nothing needs building" handoff

- **Kind:** report-defect
- **Severity:** medium
- **Topic:** measurement/metrics
- **Where:** `doc/plans/code-intelligence-substrate/080-exploration-split-measured-on-one-phase-and-it-is-the-worst-case/report-01.md:208-210` (§ Residue, first bullet)
- **Evidence:** "The instrument to run already exists (`exploration-share` + `billing-composition` checks in
  `audit.py`); **nothing needs building** — only the corpus needs to be present." Against the tree:
  `.claude/skills/audit-archived-plan-retrospectives/scripts/audit.py:6778-6786` builds its counter set from
  the five coarse buckets only, `:6789-6793` sums them across phases, and
  `.claude/skills/audit-archived-plan-retrospectives/checks/exploration-share.md:16-18` states *"the script
  reads the ten per-phase exploration counters … and sums them across the plan's phases. No other input is
  consulted."*
- **Why it matters:** the residue is the handoff contract to a corpus-bearing session. A local run that
  trusts it will arrive expecting to invoke an existing report, find none, and either improvise a
  hand-rolled aggregation (the exact discipline failure this plan exists to prevent) or stall.
- **Action:** in `report-02.md`, restate the residue as: the corpus is one prerequisite, and the per-phase
  population aggregator (G3/G4) is a second, git-derivable one that can be built without the corpus.
- **Done when:** the resumed plan's report lists both prerequisites separately, and the plan's scope names
  the aggregator as work rather than as existing.
- **Effort:** S (<1h)
- **Risk if fixed:** none — a record correction.

## G3 — Teach the retrospective auditor to read the exploration sub-source fields

- **Kind:** omission
- **Severity:** medium
- **Topic:** measurement/metrics
- **Where:** `.claude/skills/audit-archived-plan-retrospectives/scripts/audit.py:6778-6786`
  (`_ES_BUCKETS`, `_ES_COUNTER_FIELDS`) and `:7176` (`_BC_BYTE_FIELDS`); check doc
  `.claude/skills/audit-archived-plan-retrospectives/checks/exploration-share.md:14-24`
- **Evidence:** no occurrence of `exploration_index_answerable_bytes`, `exploration_doc_residency_bytes` or
  `exploration_unattributed_bytes` anywhere under `.claude/skills/audit-archived-plan-retrospectives/`
  (grep → 0, control 33 elsewhere). The fields exist and are persisted per phase
  (`manage-metrics.py:3418-3435`, rendered at `:2320-2360`) and their partition invariant is contractual
  (`marketplace/bundles/plan-marshall/skills/manage-metrics/standards/data-format.md:184`:
  `index_answerable + doc_residency + unattributed == exploration_result_bytes` EXACTLY), but only for one
  plan at a time in that plan's own metrics report — nothing aggregates them across plans.
- **Why it matters:** the epic's whole value case turns on the index-answerable share, and it is currently
  measurable only by opening one plan's report at a time. D1 asks for it over a population; with no reader,
  D1 is unimplementable even when the corpus is present.
- **Action:** extend the `exploration-share` check (or add a sibling check) to read the three sub-source
  fields with the same absent-is-not-zero discipline the coarse counters already use
  (`_parse_exploration_counters`'s presence-only accumulation, `audit.py:6789-6833`), assert the partition
  invariant per phase, and report the split alongside the existing shares. Cover it with fixtures in
  `test/plan-marshall/audit-archived-plan-retrospectives/` including a record with the fields absent (must
  be excluded, never admitted at zero) and a record with a measured zero (must stay in).
- **Done when:** `audit.py` reads all three sub-source fields; a synthetic-fixture test asserts that an
  absent sub-source field excludes the plan while a measured `0` is retained; the check's sub-document
  documents the new inputs.
- **Effort:** M (a few hours)
- **Risk if fixed:** the corpus-exclusion predicate widens — a plan measured for the coarse buckets but
  archived before the sub-sources existed must not silently drop out of the existing exploration-share
  corpus. Keep the two exclusion populations separate.

## G4 — Report the exploration split per phase, not pooled per plan

- **Kind:** incomplete
- **Severity:** medium
- **Topic:** measurement/metrics
- **Where:** `.claude/skills/audit-archived-plan-retrospectives/scripts/audit.py:6789-6833`
  (`_parse_exploration_counters`) and `:6836-6859` (`_ExplorationShareRow`)
- **Evidence:** the parser's own docstring — "Returns `(totals, phases_measured)` where `totals` maps each
  counter field to **its sum across the plan's phase sections**" — and the row dataclass carries only
  `phases_measured: int`, no per-phase structure. `plan.md:70` states ⛔ "**Do not pool phases into one
  headline** — the whole point is that the phases differ sharply", and `plan.md:72-73` requires a per-phase
  RANGE rather than a single band.
- **Why it matters:** the plan's founding observation is that the phases disagree sharply (refine is the
  doc-residency worst case, execute the best case for a substrate). A pooled per-plan share is exactly the
  shape that hid that disagreement, and quoting it as the answer would repeat the error the plan exists to
  correct.
- **Action:** emit per-phase rows (phase × bucket × measure) with a per-phase contributing-plan count, and
  keep the pooled per-plan row only where it is already consumed. Report a range across plans per phase, not
  one corpus-wide band.
- **Done when:** the check's TOON block carries one row per canonical phase with its own contributing-plan
  count, and a test asserts that a two-plan corpus whose phases differ produces distinct per-phase shares
  rather than one pooled figure.
- **Effort:** M (a few hours)
- **Risk if fixed:** the derived cut-points (`_derive_exploration_share_thresholds`, `audit.py:6891-6910`)
  are computed over per-plan shares with a degenerate-corpus spread guard; a per-phase population is smaller
  and degenerates sooner, so the guard must be re-applied per phase or the thresholds will fire on
  everything.

## G5 — Perform D1–D4 from a corpus-bearing session

- **Kind:** incomplete
- **Severity:** medium
- **Topic:** measurement/metrics
- **Where:** `doc/plans/code-intelligence-substrate/080-exploration-split-measured-on-one-phase-and-it-is-the-worst-case/` — contains `plan.md` and `report-01.md` only; no `report-02.md`
- **Evidence:** `report-01.md:36-40` records D1–D4 as "Not attempted; gated by D0". No sibling plan closed
  them: `grep -rln "index-answerable" doc/plans/` matches only `080-…/plan.md`,
  `010-lsp-in-execute-lookup-and-write/plan.md`, and `020-corpus-residency-admission-control/report-01.md`
  — and 020 is itself a D0-blocked run (`020-…/report-01.md:3`, outcome blocked). The epic's framing at
  `doc/plans/code-intelligence-substrate/README.md:5-7` is therefore still the pre-measurement one, and the
  refuted worst-case framing named in `plan.md:38-44` has not been restated anywhere.
- **Why it matters:** the epic is still being scoped on an n=1 observation that its own plan calls the whole
  problem. Until D1 runs on a population, neither the "substrate is aimed at the smaller half" reading nor
  the original premise can be acted on.
- **Action:** resume plan 080 in place from a machine where `.plan/local/archived-plans/` exists, after
  G3/G4 land; run the aggregator, report the per-phase split with per-phase contributing-plan counts, treat
  the addressable share as a lower bound until the byte remainder is classified (D2), state the value case
  in whichever direction the evidence points (D3), and give every figure its population, phase and sampling
  point (D4).
- **Done when:** `report-02.md` exists in this directory carrying a per-phase split with per-phase
  population sizes, an explicit lower-bound label wherever the byte remainder is unclassified, an explicit
  statement that the cached-read remainder is a different population owned by a sibling plan, and a
  value-case statement reconciled with the epic README.
- **Effort:** L (a day+)
- **Risk if fixed:** an unwelcome answer may require re-scoping the epic — which `plan.md:86` names as the
  point, not a risk to avoid.

## G6 — Say what a run blocked on a missing environment prerequisite must produce

- **Kind:** doc-defect
- **Severity:** low
- **Topic:** plan-lane-contract
- **Where:** `.claude/skills/cloud-plan-lane/SKILL.md:1546-1558` (§ Report) and `doc/plans/cloud-bridge.md`
- **Evidence:** the contract says the report "must state the PR number and the outcome per deliverable —
  including a run that ended **blocked or partial**, and why" (`SKILL.md:1552-1554`), but neither file says
  that a run blocked on a *missing environment prerequisite* still establishes its plan directory and lands
  a report so the determination is durable and the plan resumable. `grep -rn
  "prerequisite\|corpus-bearing"` over both files returns no such note. The 080 run proposed exactly this
  one-line amendment for an operator decision and deliberately did not self-apply it
  (`report-01.md:183-198`).
- **Why it matters:** two plans in this epic have now hit the same wall (020 and 080), and each had to infer
  the correct behaviour from first principles. A run that inferred differently would leave the flat plan
  file untouched and the determination invisible, so the plan would be re-dispatched into the identical
  wall.
- **Action:** add the one-line note to `cloud-plan-lane` § Report (and/or `cloud-bridge.md` § Path-2): a run
  blocked by a missing environment prerequisite still establishes the plan directory and lands a report with
  outcome `blocked`, naming the prerequisite.
- **Done when:** either file states that rule in one place, or an operator decision to decline it is
  recorded.
- **Effort:** S (<1h)
- **Risk if fixed:** none of substance; it codifies behaviour two runs already followed.
