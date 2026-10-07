# Gaps — 080-exploration-split-measured-on-one-phase-and-it-is-the-worst-case

The run itself did the right thing: it halted at its own D0 gate, and that gate's answer was re-derived
independently and again under adversarial review (no `metrics.toon` tracked in git —
`git ls-files "*metrics.toon"` → 0; no `.plan/local/archived-plans/` on disk, and
`find . -name metrics.toon -not -path ./.git/*` → nothing; `.gitignore:46` at the run's base sha
`3a5e2ca` ignores `.plan/*`). Every process claim in `report-01.md` — PR #1178's two-file docs-only diff,
zero inline review threads, both comment ids, the `verify / conclusion` and `Sourcery review` check
conclusions, the `Co-Authored-By` trailer, the sibling-060 directory-name correction — is accurate.

What remains is of two kinds. First, the report's technical justification for the halt is wrong in three
places (`report-01.md:44-48`, `:70-73`, `:208-210`, echoed a fourth time at `:97`): it states that the
instrument D1 needs already exists in `audit.py`. It does not, in three separate respects — no shipped
check reads the three exploration sub-source fields that *define* D1's split (G3); the closest check
pools all phases into one per-plan figure that D1 explicitly forbids (G4); and that same check applies
neither of the two schema reads nor the re-entry guard the plan obliges D1 to inherit, though sound
implementations of all three sit elsewhere in the same file (G7). Second, the consequent work — building
that reporter, then running it over a real corpus — is entirely outstanding, and **the reporter half of
it does not need the corpus and could be built in a cloud clone today** (G3/G4/G7). That last point is
the one that changes what a resuming run should do, and it is the opposite of what the report's residue
says.

⚠ None of this weakens D0. The plan mandates HALT on outcome (b) unconditionally (`plan.md:64-66`), so
the halt is correct regardless of what preparatory work was git-derivable. Only the report's stated
*reason*, and the handoff it produced, are wrong.

## G1 — Correct report-01's claim that the audit checks read D1's counters

- **Kind:** report-defect
- **Severity:** low — the claim is confined to a dated run report and changed no outcome (the HALT was
  plan-mandated either way). It is filed separately from G2 because it is the same false statement in a
  different role: G1 is inert justification prose, G2 is the handoff a later run acts on.
- **Topic:** measurement/metrics
- **Where:** `doc/plans/code-intelligence-substrate/080-exploration-split-measured-on-one-phase-and-it-is-the-worst-case/report-01.md:44-48` (§ "D0 — the gate, in detail"); the same error recurs at `report-01.md:70-73` ("Plan 080 has **no** git-derivable deliverable … *already exist* in `audit.py`") and in the sub-agent finding table at `report-01.md:97`
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
  three sub-source fields as D1's inputs and stating that `report-01.md:44-48`, `:70-73` and `:97`
  misidentified them.
- **Effort:** S (<1h)
- **Risk if fixed:** none — a record correction, no code touched.

## G2 — Correct the residue's "nothing needs building" handoff

- **Kind:** report-defect
- **Severity:** medium — unlike G1 this sentence is a handoff contract that a later run acts on, and
  acting on it produces the wrong plan of work.
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
  sub-source aggregator (G3/G4/G7) is a second, **git-derivable** one that can be built without the corpus
  — including in a cloud clone, which is where this run decided nothing was buildable.
- **Done when:** the resumed plan's report lists both prerequisites separately, states which of the two
  needs the corpus and which does not, and names the aggregator as work rather than as existing.
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
  (`manage-metrics.py:3418-3432`, rendered at `:2336-2362`) and their partition invariant is contractual —
  `marketplace/bundles/plan-marshall/skills/manage-metrics/standards/data-format.md:184` reads, verbatim:
  *"**Partition invariant**: `exploration_index_answerable_bytes + exploration_doc_residency_bytes +
  exploration_unattributed_bytes` equals `exploration_result_bytes` EXACTLY."* But that holds for one
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
  `phases_measured: int`, no per-phase structure. `_corpus_share` (`audit.py:6907-6910`) then divides one
  corpus-wide numerator by one corpus-wide denominator, which is the single band itself. `plan.md:70`
  states ⛔ "**Do not pool phases into one headline** — the whole point is that the phases differ
  sharply", and `plan.md:71-72` requires "the per-phase RANGE for the exploration share, never a single
  band".
- **Why it matters:** the plan's founding observation is that the phases disagree sharply (refine is the
  doc-residency worst case, execute the best case for a substrate). A pooled per-plan share is exactly the
  shape that hid that disagreement, and quoting it as the answer would repeat the error the plan exists to
  correct.
- **Action:** emit per-phase rows (phase × bucket × measure) with a per-phase contributing-plan count, and
  keep the pooled per-plan row only where it is already consumed. Report a range across plans per phase, not
  one corpus-wide band. A working model for the parse already exists in the same file:
  `_parse_billing_phase_fields` (`audit.py:7229-7264`) reads the identical `[phase]`-sectioned shape and
  returns `{phase_name: {field: value}}` presence-only — `_parse_exploration_counters` differs from it
  only by collapsing that outer key.
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
  them. Both spellings have to be searched, because the match sets do not overlap:
  `grep -rln "index-answerable" doc/plans/` matches `080-…/plan.md`,
  `010-lsp-in-execute-lookup-and-write/plan.md` and this audit's own `verification.md` / `gaps.md`;
  `grep -rn "index_answerable\|doc_residency" doc/plans/` additionally matches
  `020-corpus-residency-admission-control/{report-01.md,verification.md,gaps.md}`, which carry only the
  underscore field name. 020 is itself a D0-blocked run (`020-…/report-01.md:3`, outcome blocked), so it
  closes nothing. The epic's framing at
  `doc/plans/code-intelligence-substrate/README.md:5-7` is therefore still the pre-measurement one, and the
  refuted worst-case framing named in `plan.md:38-44` has not been restated anywhere.
- **Why it matters:** the epic is still being scoped on an n=1 observation that its own plan calls the whole
  problem. Until D1 runs on a population, neither the "substrate is aimed at the smaller half" reading nor
  the original premise can be acted on.
- **Action:** resume plan 080 in place from a machine where `.plan/local/archived-plans/` exists, after
  G3/G4/G7 land; run the aggregator, report the per-phase split with per-phase contributing-plan counts, treat
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
- **Where:** `.claude/skills/cloud-plan-lane/SKILL.md` § Report (begins at `:1638`) and
  `doc/plans/cloud-bridge.md` § Path 2 — Sync (`:112-134`)
- **Evidence:** the contract says the report "must state the PR number and the outcome per deliverable —
  including a run that ended **blocked or partial**, and why" (`SKILL.md:1551-1552`, which sits in
  **§ Step 8 — Merge gate**, not in § Report; `cloud-bridge.md:132` says the same), but neither file says
  that a run blocked on a *missing environment prerequisite* still establishes its plan directory and lands
  a report so the determination is durable and the plan resumable. `grep -rn
  "prerequisite\|corpus-bearing"` over both files returns 0 matches, and reading every other `blocked`
  occurrence in them (`SKILL.md:133,209,1098`; `cloud-bridge.md:132`) finds the rule stated in no other
  words either. The 080 run proposed exactly this one-line amendment for an operator decision and
  deliberately did not self-apply it (`report-01.md:183-198`).
- **Why it matters:** two plans in this epic have now hit the same wall (020 and 080), and each had to infer
  the correct behaviour from first principles. A run that inferred differently would leave the flat plan
  file untouched and the determination invisible, so the plan would be re-dispatched into the identical
  wall.
- **Action:** add the one-line note to `cloud-plan-lane` § Report (and/or `cloud-bridge.md` § Path 2 —
  Sync): a run blocked by a missing environment prerequisite still establishes the plan directory and
  lands a report with outcome `blocked`, naming the prerequisite.
- **Done when:** `grep -n "environment prerequisite" .claude/skills/cloud-plan-lane/SKILL.md
  doc/plans/cloud-bridge.md` returns at least one hit stating that rule — **or** a decision to decline it
  is written into `doc/plans/code-intelligence-substrate/080-…/report-02.md` with the operator's reason,
  so a later reader can tell "declined" from "never looked at".
- **Effort:** S (<1h)
- **Risk if fixed:** none of substance; it codifies behaviour two runs already followed.

## G7 — `exploration-share` applies neither schema read nor the re-entry guard D1 inherits

- **Kind:** omission
- **Severity:** medium
- **Topic:** measurement/metrics
- **Where:** `.claude/skills/audit-archived-plan-retrospectives/scripts/audit.py:6862-6888`
  (`_collect_exploration_share_rows`) and `:6789-6833` (`_parse_exploration_counters`)
- **Evidence:** `plan.md:98-104` obliges D1 to carry a three-state partiality read and a three-way
  `measured / unmeasured / unrecognised` cell read; `plan.md:106-109` obliges it to use the published
  value-scope fields and to "check it per contributing phase and exclude or label" any re-entered row.
  Sound implementations of all three exist in the same file and are non-vacuously tested (mutation swept
  in `verification.md` § Test adequacy): `parse_metrics_end_time_presence` (`:1139-1180`), the three-way
  ledger cell read (`:7357-7394`), and the `close_count > 1` re-entry label (`:7515`, feeding
  `unabsorbed_loop_back`). **None is reached from the exploration-share region.**
  `parse_metrics_end_time_presence` is called only at `:1700`, `:4454` and `:7477`;
  `grep -n "value_scope\|close_count"` over `audit.py` returns nothing between `:6747` and `:7128`; and
  `_collect_exploration_share_rows` applies only the absent-is-not-zero exclusion. So a plan whose
  markers are old-schema, and a phase row that was closed more than once (whose counters are therefore
  sums across closes — `data-format.md:128-130`), both enter the exploration shares unlabelled.
- **Why it matters:** these are the two obligations `plan.md` singles out as "both breaking", and the
  first one is named as this project's own archetype — a bare rename defaulting an absent key into a
  clean verdict. D1's figures would inherit exactly that defect from its host, and a re-entered row
  quoted as a rate is arithmetically wrong rather than merely imprecise.
- **Action:** in `_collect_exploration_share_rows`, call `parse_metrics_end_time_presence` on each plan's
  `metrics.toon` and carry `schema` / `forces_floor` / `unreadable_note` onto `_ExplorationShareRow`,
  emitting the note verbatim and labelling any derived figure from a non-`current` record as a floor;
  and read `close_count` per phase (as `_parse_billing_phase_fields` already does) so a `close_count > 1`
  phase is excluded from the per-phase rate or labelled, never silently summed.
- **Done when:** the exploration-share TOON block carries, per plan, the record's schema state and the
  set of re-entered phases; a fixture with the retired `partial` / `unrecorded_phases` keys is reported
  as `old-schema` and its shares labelled as floors rather than admitted clean; and a fixture with a
  `close_count: 2` phase is excluded-or-labelled while a `close_count: 1` phase is not.
- **Effort:** M (a few hours)
- **Risk if fixed:** labelling old-schema records as floors shrinks the clean corpus, which interacts
  with G4's per-phase degeneracy: a per-phase population that is already small can empty entirely once
  floored records are held out. Report the floored count alongside the clean one rather than dropping it.
