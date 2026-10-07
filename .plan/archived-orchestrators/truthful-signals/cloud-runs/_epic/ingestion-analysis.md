# Cloud-run ingestion analysis — truthful-signals

Ingestion of `doc/plans/truthful-signals/` into this ledger. Per-group analysis digests from the
ingestion sub-agents, plus the cross-cutting rulings the ingestion itself forced.

Population: 47 executed plans (44 original `030`–`460`, no `400`; 3 derived `500`/`510`/`520`),
8 un-run plans (`530`–`600`), 2 epic docs. All 47 landings confirmed present in `main` by merge
commit, not by PR state.

---

## ⛔ RULING 1 — a run report is a dated record; do NOT retro-edit it

**32 of the 283 gaps (11.3%) name a `doc/plans/truthful-signals/**/report-01.md` as their `Where`.**
Ingestion moves every one of those reports out of version control into this git-ignored archive, so
a deliverable that "corrects" one edits a file no consumer reads.

This was reached independently twice: by the ingestion's own path analysis, and by gap `380/G5`,
which states it as a rule — *"Do not retro-edit `report-01.md` — a run report is a dated record of
one execution, not documentation of current state; this gap entry is the correction of record"* —
and retargets its own fix to the tree. `CLAUDE.md` § Standalone Plan Lane supports it: a run report
takes the dated-record exemption from the "Current state only" documentation standard.

⛔ **But four gaps in two other plans prescribe the opposite** — `430/G4`, `430/G9`, `260/G4`,
`260/G5` all say to edit `report-01.md` directly. Under Ruling 1 they are unactionable as written.

**RULING: the correction of record lives in the gap entry and in this ledger, never in the archived
report.** Every report-scoped gap is closed-as-recorded at ingestion. Where the same false claim is
ALSO restated on a live surface, only that live restatement is actionable — and it must be
re-derived, not inherited from the gap's `Where` line.

Affected staged plans, which cite archived reports in their Expected surface and need re-scoping
before emission: `530`, `550`, `570`, `580`, and above all `590` (11 of its 17 surface paths are run
reports).

## Gap coverage — verified mechanically at ingestion

All **283** gap ids are owned by a fix plan: 0 uncovered, 0 genuine ghost citations.
(`070/G6` reads as a ghost only because plan `530` names it as *not carried* — `070`'s `gaps.md`
skips `G5`→`G7`, its `G6` having been moved to the Refuted section.)

- 179 owned only by an un-run plan (`530`–`600`)
- 97 owned only by an executed plan (`500`/`510`/`520`)
- 7 owned by both
- 35 cited by more than one fix plan — cross-references and out-of-scope declarations, NOT double
  ownership; consistent with the audit's `closes`-based 275/8/0/0 partition.

---

## Group G6 — planning lane / dispatch / manifest / test suite

Plans 240, 260, 280, 340, 350, 380, 430. All seven landed and none was reverted; every superseding
commit extended the work.

| Plan | PR | Verdict | Deliverables | Gaps (H/M/L) |
|---|---|---|---|---|
| 240 deep-lane-bought-by-one-signal | 1188 | implemented-with-gaps | 4/4 | 5 (1/2/2) |
| 260 generic-dispatch-template | 1197 | implemented-with-gaps | 4/4 | 7 (2/1/4) |
| 280 dispatch-audit-empty-primary-surface | 1200 | implemented-with-gaps | 4/4 (rollout 6 of 22 sites) | 7 (2/3/2) |
| 340 derive-verification-build-class | 1222 | implemented-with-gaps (fragile) | 5/5 (D1+D2 reversed) | 4 (0/3/1) |
| 350 change-type-one-word-two-scopes | 1221 | implemented-with-gaps | 5/5 | 4 (1/2/1) |
| 380 test-suite-false-confidence | 1229 | **partially-implemented** (corrected) | 6/7 — **D6 did not land** | 8 (1/3/4) |
| 430 timeout-is-not-a-red-test | 1193 | implemented-with-gaps | 4/4 | 9 (0/4/5) |

**Carry-forward, one per plan:**

- **240** — S7 is suppressed whenever the scope band is `single_module`, but that band is also what
  `classify_scope_pure` assigns when it found **no path at all**: a false positive was closed by
  shipping a false negative into the same seam, and the plan's own designated control (D3(d))
  structurally cannot reach the branch.
- **260** — D2 added a *third* declaration surface and linked two of three; the input-table
  `Required: Yes` row that the ext-point doc itself names as the declaration surface is read by
  nothing, so the original defect still reproduces verbatim for **24 of 26** steps.
- **280** — the seam is correct and per-firing, but only **6 of 22** dispatch sites use it, and the
  same commit that left 11 hand-written `[DISPATCH]` blocks rewrote the standard to call that shape
  forbidden — with `planning.md:275` still instructing it *and citing the forbidding section as its
  authority*.
- **340** — D1/D2 were reversed by operator decision at the D0 gate; the emitter was never touched.
  ⛔ The only authorisation is the report's own assertion of an `AskUserQuestion` exchange, with **no
  tree artifact**. A reviewer declining to take that word reads the plan as `partially-implemented`.
- **350** — the reconciliation validates the *supplied* `change_type` against the canonical enum but
  never the *settled* one it reads back, so a plan carrying a documented-but-non-canonical value
  (e.g. `feature_breaking`) can no longer compose at all — a hard block that did not exist before.
- **380** — D2, the deliverable the plan called "the one that matters most", gates finding-clearance
  on a count that includes skips, so the exact mechanism it was written to stop survives inside the
  fix.
- **430** — D0's consumer population was corrected 8→11 during the run and 11→12 in verification.
  The plan named "every consuming gate is identified" as its highest-risk claim and it was wrong at
  every pass, each time caught by adversarial review rather than by the derivation.

**⛔ `380/G1` CONFIRMED STILL OPEN at HEAD**, verified directly during ingestion:
`_build_shared.py:751` is `tests_run = test_summary.total if test_summary is not None else 0`;
the gate it feeds is `:467` `if tests_run > 0:`; `_build_parse.py:622` computes
`total = passed + failed + skipped`. `G7`'s second site is live too (`_build_shared.py:185`).
⇒ **a green build whose only outcome is skips reports a non-zero executed-test count and clears a
pending `test-failure` finding.** Nothing bounds it, because `G8`'s zero-skip gate
(`PLAN_MARSHALL_STRICT_NO_SKIP`) is set nowhere and can never fire.

**Recurring archetypes measured across the group:**

- **Vacuous guard — 6 of 7 plans.** 240/G2, 260/G1, 280/G1 (mutation survives all 1151 manage-config
  tests), 350/G2, 380/G1+G8, 430/G3. Only 340 is free of it, and there adversarial review refuted
  the verification's own claim that both D4 controls guard.
- **Under-derived population — 5 of 7.** 240 (n=1 generalised to the whole orchestrated population),
  260, 280 (missed the entire orchestrator lane), 380, 430. 380's report states the lesson:
  *"an expected-surface list is a lead, not a population."*

**⛔ Serialization constraints — these pairs share files and must NOT run concurrently:**

| Surface | Plans |
|---|---|
| `_build_shared.py` + `_build_format.py` | **380** and **430** — 380/G1, 380/G7, 430/G2, 430/G3 must be fixed as ONE change; separate PRs guarantee a conflict |
| `manage-execution-manifest.py` | **340** (`:2296-2306`) and **350** (`:1848-1875`) — highest collision risk; both landed the same day and both carried serialize-against-the-sibling notes |
| `_cmd_planning_lane.py` | **240** (G1/G2/G5) and **350** (D0 at `:785`, `:104`) |
| `phase-6-finalize/SKILL.md` dispatch blocks | **260** (G2) and **280** (G4) |
| `plan-retrospective/scripts/` | **280** (M3, closed by #1288) and **430** (G7/G8 in `analyze-logs.py`) |

**⚠ One stale residue to not re-file:** the bare-vs-canonical token mismatch appears in three plans
under three framings (280 D0 deferred, 350 Out-of-scope, closed independently by `eb0124c9`/#1288).
**350's residue still says the sibling item is "still open" — it is not.** Anyone reading 350's
residue will re-file a closed item.

---

## ⛔ RULING 2 — every `gaps.md` is a SNAPSHOT, not live state

Every `gaps.md` was written by the audit at PR **#1298 (2026-08-18)**. Three remediation plans landed
**after** it — **#1320** (plan 500), **#1309** (plan 510), **#1317** (plan 520) — and they closed gaps
that no `gaps.md` records as closed.

Measured at HEAD by the ingestion agents, per group:

| Group | Gaps | Already CLOSED at HEAD | Closed by |
|---|---|---|---|
| G7 (060 080 140 310 370 450) | 41 | **10** | 060 G2/G3/G5/G6/G7 ← #1320; 310 G1/G3/G4/G5/G8 ← #1309 |
| G2 (030 160 230 330 390 440) | 34 | **8** | 160/G2, 160/G9, 230/G2, 330/G1, 440/G1, 440/G2, 440/G3, 440/G6 — five of them ← #1309 |
| G5 (150 220 290 410 420 460) | 29 | **3** | 410/G1, 410/G4 ← #1309; 460/G5 |

⛔ **A consumer that schedules work from a `gaps.md` without re-grounding will re-open closed items** —
five plugin-doctor gaps, five baseline-reconcile gaps, and five finalize gaps at minimum.
**#1309 alone is the single largest gap-closer in the corpus.**

⇒ **RULING: re-ground every gap at HEAD before emitting the plan that owns it.** The staged specs
carry this as a standing precondition.

## ⛔ RULING 3 — #1309 reproduced the epic's own n−1 archetype inside a gap fix

`refine-workflow-detail.md` line **288** was rewritten to close `310/G3`, while line **289** — `310/G2`,
the adjacent row of the *same table* — was left standing. Two gaps, consecutive lines, one fixed.
**Fourth recorded instance of this shape in this epic.**

---

## Group G2 — finalize / CI / merge gates

| Plan | PR | Verdict | Deliverables | Gaps (H/M/L) |
|---|---|---|---|---|
| 030 merge-gate-required-vs-decorative | 1137 | partially-implemented | 4/6 — D0 partial, **D3 dropped** | 4 (0/2/2) |
| 160 build-gate-coverage-parity | 1174 | implemented-with-gaps | 6/6 (D2/D3 no-change-with-evidence) | 10 (1/6/3) |
| 230 finalize-retriggers-ci | 1194 | partially-implemented | **1/6 — only D1 landed** | 4 (1/3/0) |
| 330 post-run-guard-exempts-plan-files | 1217 | implemented-with-gaps | 6/6 (D2 at 1 of 2 sites) | 5 (2/3/0) |
| 390 ci-and-supply-chain-hardening | 1230 | implemented-with-gaps | 9/9 (**D5 reverted by #1246**) | 5 (0/3/2) |
| 440 merge-currency-treadmill | 1235 | partially-implemented | 4/5 — **D4 unmeasurable** | 6 (1/3/2) |

**Carries:**
- **030** — required-ness on the cloud path is readable only from `mergeStateStatus` (the ruleset-config
  API returns `403`), so any instruction to "derive the required set" is unexecutable there.
- **160** — ⚠ **G6 is a defect introduced by PR #1239, a LATER plan**, filed under 160 only because it
  shares the output surface. Do not attribute it to #1174 when triaging.
- **230** — the plan's central premise was **refuted by its own investigation**; its gate was unopenable
  from a cloud clone. Five of six deliverables are honest non-delivery, not failure.
- **330** — the plan's own defect survived inside its fix: `G5` is an ordinary `git rm` of a tracked
  `.plan/` descriptor reported `clean: True` by **both** fixed guards, reachable with no exotic filename.
- **390** — ⛔ **D5 broke the required check every merge gate depends on within 24 h** and was reverted
  in substance by #1246 (`24271bca`) after a shared concurrency group let a `pull_request` run cancel a
  push run's `gate` job, planting a red `verify / conclusion` and returning `405 Repository rule
  violations`. Nothing yet guards the restored invariant (`G1`).
- **440** — delta-scoping bounds the cost of each re-run and does nothing to the *number* of re-runs;
  the lever reaches **1 of 11** head-dependent steps and D4 produced no measurement.

**⛔ The cloud lane's missing `.plan/` is the dominant cause of non-delivery** — three plans had a GATE
deliverable that could not be opened from a fresh clone (230/D0 archived CI manifests, 440/D4 a real
finalize to measure, 030/D0 the `403` ruleset API). `230/G3` and `440/G4` are the same unmet-measurement
gap under two ids.

**Collisions:** `.claude/skills/cloud-plan-lane/SKILL.md` (all four 030 gaps + 440 + 390 — highest
single-file contention) · `phase-6-finalize/SKILL.md` (230, 330, 440) · `pre-push-quality-gate.md`
(**160 and 440 — live two-plan collision**) · `branch-cleanup.md` (440, 230) · `test_workflow_lint.py`
(390 G2+G4+G5 = one change) · `build.py`+`_gate_coverage.py` (160 G1/G5/G6/G8/G10 = one change).

---

## Group G7 — git / artifacts / cloud lane / generator

| Plan | PR | Verdict | Deliverables | Gaps (H/M/L) |
|---|---|---|---|---|
| 060 invented-plan-scoping-flags | 1150 | partially-implemented | **1/3** — D2/D3 sanctioned non-execution | 7 (1/5/1) |
| 080 key-order-canonicalization | 1156 | implemented-with-gaps | 10/10 (D3 = re-derived refutation) | 9 (1/6/2) |
| 140 detect-artifacts-live-audit-trail | 1171 | implemented-with-gaps | 5/5 | 5 (2/2/1) |
| 310 baseline-reconcile-stale-sha | 1206 | implemented-with-gaps | **6/6 all landed** | 8 (1/5/2) |
| 370 multi-target-generator-edge-paths | 1228 | implemented-with-gaps | 7/8 — D6 dropped under authorisation | 7 (0/3/4) |
| 450 cloud-lane-assumes-local-affordances | 1147 | implemented-with-gaps | 6/6 | 5 (1/3/1) |

**⭐ Resolution of the two mandated report-staleness cases — both are HEADER-ONLY, failing in opposite
directions. Trust the body and the landed diff over the header.**

- **060 landed exactly what its report describes.** `git show --name-status -M c586d2cbe` returns
  **two paths and nothing else** — no `*.py`, no `test/**`, no `marketplace/bundles/**`. The
  STOP-CONDITION halt was real and D2/D3 genuinely did not execute. `PR: _pending_` is the single false
  statement; `Outcome: completed` is a *qualified* completion disclosed in the same sentence.
- **310 landed FAR MORE than its header admits.** `PR: _pending_ / Outcome: _in progress_` are unfilled
  template placeholders on a run that delivered **all six** deliverables across 11 non-plan files,
  including two production scripts and two test modules. Nothing was left undone.

**Carries:**
- **060** — the plan implemented nothing by design; its real yield is that **5 of its 7 gaps were later
  closed by plan 500**, leaving two report-document fixes.
- **080** — ⛔ **`G9` (high) is open at HEAD**: `_claude_runtime_impl.py:90-100` builds
  `marshal_data = {...}` and calls `_write_json` with **no read and no existence check**, destroying the
  whole `marshal.json` — the maximal lost update on the very file D4 was written to protect.
- **140** — the fix protects a *nested* worktree but not the scan root, and the finalize path a phase-5+
  run actually uses puts the plan's own worktree **at** the scan root, so the headline invariant does
  not hold in the configuration it was written for.
- **310** — everything promised landed and is mutation-pinned, but the report still says "in progress".
- **370** — the **same PR** created the mirror of both its own gaps in the sibling emitter (G3, G7), and
  its reverse sweep could not see them because it **ran before the change**.
- **450** — the plan that exists to make the cloud lane state its affordances truthfully shipped a
  report that **denies having done the very things it did** (five cells say "no PR opened"; PR #1147
  merged as `a3eb36bb8`). The epic's archetype committed inside the fix for it.

**Collisions:** `git-workflow.py` (140 ~`:530-760` / 310 ~`:1150-1290`, disjoint regions) ·
`workflow-integration-git/SKILL.md` (**140 + 310, real collision**) · `upgrade-flow.md` (080 G3+G5+G7 =
one change) · `_config_core.py::order_config_keys` docstring (080 G2 + G6).

---

## Group G5 — metrics / ledger readers / timestamps

| Plan | PR | Verdict | Deliverables | Gaps (H/M/L) |
|---|---|---|---|---|
| 150 configurable-display-timezone | 1172 | implemented-with-gaps | 5/5 | 5 (2/2/1) |
| 220 build-ledger-is-the-build-time-oracle | 1224 | implemented-with-gaps | 5/5 | 7 (1/5/1) |
| 290 main-sha / config-hash | 1205 | implemented-with-gaps | 3/3 | 5 (1/2/2) |
| 410 pipeline-talks-to-itself | 1231 | implemented-with-gaps | 4/4 | 4 (0/3/1) |
| 420 writer-destroyed-the-distinction | 1255 | implemented-with-gaps | 4/5 + D1 N/A by design | 3 (0/1/2) |
| 460 audit-ledger-undatable-zero | 1278 | **fully-implemented** | 4/4 clean | 5 (0/3/2) |

**⭐ The 460 reconciliation — `fully-implemented` with 5 gaps measures two different things.** The
verdict is scoped to deliverables D0–D3 (every row a clean pass, mutation-proved). `gaps.md` is scoped
to *open items on surfaces the plan touched or created*, a strictly larger set. The five decompose as:
two are side-effects of **correctly-refused out-of-scope edits**; one is **pre-existing** and outside
the gate; one was made false by a **sibling plan** (420); one is a **verification artifact**.
⇒ **A plan can be fully-implemented and still leave open items; the gap count is not a quality signal.**
The inverse holds too — 220 has all-`yes` Implemented cells and 7 gaps, and is `implemented-with-gaps`
only because *Done-when* conditions were unmet.

**Carries:**
- **150** — the knob reaches 2 RENDER sites and its write-path guard is **file-granular**, so converting
  any of the 9 persisted `now_utc_iso()` writes in `manage-metrics.py` passes the guard green; D5(c),
  the named invariant test, cannot observe that defect class at all.
- **220** — replaced a log-derived undercount but **never produced the delta number that was its own
  stated evidence**, and the facet it added (`build_share`) reintroduces the fabricated-zero defect for
  every plan archived before the ledger existed.
- **290** — ⛔ the shipped fix is correct but **the diagnosis is false and now lives in a production
  docstring** (`_invariants.py:1514-1518`): the executor strips `--audit-plan-id`, so the "signal never
  fired" story would send a reader to "fix" 28 documented, working call sites.
- **410** — D1's fail-closed filter is structural only in the auditor; the emitter that actually minted
  the false preference is an **LLM prose contract**, so the invariant is a tested fact for one surface
  and an instruction for the other.
- **420** — an information-honesty fix, not an information-recovery one; a genuinely all-measured-zero
  row carries no fingerprint and is `indeterminate` **by design**.
- **460** — ⛔ the gate is semantically correct but **arithmetically inert**: all four consumers route
  the value through `.get(field, 0)`, `> 0`, `> row_value` or `max(...)`, in each of which absent and
  measured-`0` are indistinguishable. It corrects the readers' contract, **not any emitted number**.

**⛔ ONE GAP UNDER TWO IDS — `420/G1` and `460/G4` are the SAME defect** (two
`…reads_three_ways_in_the_retrospective_reader` test names + a comment). Both open, both with stale line
refs — the module was decomposed and the sites are now
`test_record_model_representability_unmeasured.py:55/:139/:144`. **Fixing one closes the other; tracking
them separately double-counts.**

**Collisions:** `audit.py` is the **hottest file in the corpus** — 220 G1/G3/G7, 410 G3, 460 G3, in three
different check regions; it also **lives outside the architecture crawl inventory**, so a content sweep
will not find drift in it · `data-format.md` § Per-Dispatch Context-Load Attribution (420 G2+G3, 460
G1+G2 — must settle together) · `analyze-logs.py` (220 G2, 420 G2, 460 G1/G2/G3).

**⛔ The epic's namesake defect recurs inside its own fixes — 6 instances in this group, 3 introduced or
left behind by the very plan removing the class** (220/G1, 220/G6, 410/G3).
**5 of 6 plans have at least one FALSE statement in their own run report**, and two of those shipped into
a production docstring (290/G1) or the landed commit body (290/G4), where they outlive the plan directory.

---

## Group G1 — plugin-doctor / documentation surfaces

| Plan | PR | Verdict | Deliverables | Gaps (H/M/L) |
|---|---|---|---|---|
| 040 inert-thinking-directives | 1138 | implemented-with-gaps | 3/3 | 6 (1/2/3) |
| 100 canonical-block-diverges | 1158 | implemented-with-gaps | 6/6 | 10 (2/8/0) |
| 130 skills-carry-incident-history | 1163 | implemented-with-gaps | 6/6 | 6 (1/3/2) |
| 170 graduate-deployment-diagram | 1296 | implemented-with-gaps | 5/5 | 5 (0/2/3) |
| 190 split-user-configuration-doc | 1179 | implemented-with-gaps | 6/6 | 8 (3/3/2) |
| 270 java-skills-anti-pattern | 1195 | implemented-with-gaps | 6/6 | 7 (1/3/3) |

**Carries:**
- **040** — the plan's named population source was the **wrong mechanism** (`_dispatch_roster.py` is a
  finalize step parser, not the execution-context roster); the reusable pattern it established — derive
  the population from each doc's own ext-point `implements:` frontmatter — is **still not written down
  anywhere durable** (G5), and the same mis-pointer cost was paid twice (040 and 050).
- **100** — ⛔ both named leads were recorded **refuted** on evidence about the canonical block, while
  the claim-label named the *whole* `SKILL.md` — the leads are **live** at the sites actually named
  (G1, G2). *A false refutation inside a plan about false oracles.*
- **130** — the rule that is the plan's only anti-regression guarantee sees a **strict subset** of the
  narration forms D1 was briefed to sweep (fires on 2 of 8 realistic forms) — a rule scoped narrower
  than the directive it enforces, the plan's own stated anti-pattern.
- **170** — the report's disposition/residue cells are a **self-falsifying surface**: round 4 measured
  that the report manufactured 3–5 new false statements *per round*, fixed the class by citing commits
  instead of quoting mutable text, and two falsified rows still survive at HEAD (G4, G5).
- **190** — D1's **Covered** bucket certified **five keys that do not exist**. The asymmetry is the
  danger: `get --field self_review` errors, but `set --field self_review --value banana` returns
  `success` and persists a key nothing reads.
- **270** — the rule landed only in `java-null-safety`, an **optional** skill, while `java-core` — a
  **default** skill whose description advertises "null-safety" — teaches records and carries no pointer.
  The original failure path (`record Foo(Optional<String> bar)`) is still the default-configuration path.

**⛔ The group's dominant pattern: the GATE deliverable's own ABSENCE claim is what fails.** Four of six
produced a false or under-scoped absence — 100/D1 (refuted two live leads), 130/D1 (`as of 20YY`
declared zero-in-tree; `permission-architecture.md:55` was in the population), 190/D1 (ran the diff in
one direction only → three of the group's five `high` gaps), 270/D0 (swept where the trigger was
expected, not where one could live). Only 040/D2 (which halted and re-derived) and 170/D3 survived
re-derivation. ⇒ **An absence claim is only as good as the population it was swept over, and the sweep
must run where the thing COULD be, not where it was expected.** 190's strongest form: *resolving a key
by name is not the same as executing the verb* — name-resolution let five dead config keys through.

**Collisions:** `plugin-doctor/**` is the hot spot — 040, 100, 130 each added an analyzer and each edited
the same six registration files (`_runner.py`, `_rule_registry.py`, `doctor-marketplace.py`,
`rule-catalog.md`, `rule-provenance.md`, `_fixtures.py`+`test_runner.py`). Any two in parallel conflict.
`manage-config/**` (100/G3 + 190/G4+G5, both edit `data-model.md`). **Genuinely disjoint and
parallelisable: 170 (`ref-svg-diagrams`), 270 (`pm-dev-java`), 190's `doc/user/*.adoc` half.**

**⛔ Three plans hold three DIFFERENT policies on whether a run report is amendable** — 040 and 170 file
stale report figures as gaps; **100 explicitly refuses**: *"a run report is a dated record that is not
amended."* And #1309/#1320 **did in fact amend 040's report twice**. See RULING 1: 100's stated
principle is the one this ledger adopts; the epic did not operate by it.

---

## Group G4 — config / steward / version selection / daemon

| Plan | PR | Verdict | Deliverables | Gaps (H/M/L) |
|---|---|---|---|---|
| 050 migration-shims-have-no-expiry | 1153 | implemented-with-gaps | 4/4 | 7 (1/3/3) |
| 070 marshalld-self-reload | 1152 | implemented-with-gaps | 6/6 | 6 (1/4/1) |
| 090 surface-every-knob-in-marshal-json | 1155 | implemented-with-gaps | 5/5 | 3 (1/1/1) — **all 3 closed** |
| 200 respread-effort-preset-ladder | 1181 | implemented-with-gaps | 5/5 | 8 (0/4/4) |
| 210 named-recovery-discards-config | 1186 | implemented-with-gaps | 4/4 | 5 (3/1/1) |
| 320 sync-plugin-cache-never-registry | 1213 | implemented-with-gaps | 8/8 | 10 (2/5/3) — **all 10 closed** |
| 360 collapse-version-selection | 1223 | **partially-implemented** (corrected) | 6/7 — **D1 did not land** | 6 (1/3/2) |

**Carries:**
- **050** — the inventory's boundary was never established: two independent sweeps each found a
  *different* unmarked category-B shim, and the guard's measured recall is **4 of 25** known shim shapes.
  "0 findings on the real tree" is evidence about the **indicator set**, not about the tree.
- **070** — ⛔ the contract's whole safety premise ("idleness is read from the daemon's own scheduler
  count, never inferred") is **false for exactly the population the reconcile targets**: a daemon pinned
  below the counts extension answers the handshake without them, `run_status` writes `0`, and `decide`
  returns `upgrade/idle_and_stale` — **draining a live build**.
- **090** — the run skipped the one surface Rule 4 calls "the most-forgotten", the **tracked**
  `.plan/marshal.json`, on a premise false on both halves (`.gitignore:46` re-includes it; it is in
  `git ls-files`). A plan about discoverability left its own dogfooding config hiding both knobs.
- **200** — ⛔ `balanced` is the only preset with slots **below** its own default, and every prose
  surface was written in the "name the lifts" style that silently loses that remainder — so the string
  the wizard prints verbatim **promises Opus-medium finalize where Sonnet-high runs**.
- **210** — the D2 collapse is real but its guard is **vacuous**: `_references_authority(text)` is
  `'planning.md' in low and 'named recovery' in low`, both true by construction for any region carrying
  the standard cross-reference bullet. A reworded destructive block passes 3 of 3 tests green.
- **320** — ⭐ **`320/G1` is CLOSED at HEAD** (see RULING 2). The declared residue is still open: the
  detector is a library + adapters, **not wired into any live gate or plugin-doctor rule** — `grep -rl
  pin_trap` over `marketplace/` and `.claude/` returns nothing, and the leading `_` keeps it out of
  executor discovery, so **it is still uninvocable**.
- **360** — ⛔ **the plan's root lever never shipped.** D1's headline action ("stop baking absolute
  version paths into the executor; resolve at runtime") was not performed — absolute version-pinned
  paths are still baked. What landed is marker-removal from a resolver that was **already** runtime.
  D1's own *Done when* passes, and passed pre-fix too.

**⛔ Double-routed gaps that will collide:** `210/G1` is claimed by **560 and 570** (a single test file,
`test_phase_2_refine_manage_config_readonly.py`) · `360/G5` by **530 and 540** · `200/G1` and `200/G8`
by **530 and 580**. Whichever runs second finds the gap closed or re-edits the same lines.

**⛔ One gap under two ids:** `320/G6` and `360/G3` are the **same defect in the same function**
(`loader_selected_version`'s dead marker logic), filed from opposite directions. #1320 closed both with
one change and its coverage table lists them as separate met rows. `320/G5` is a third face of it.

**Collisions:** `generate_executor.py` — **320 (D5) and 360 (D4) landed 3h45m apart and 360's rewrite
invalidated 320's docstrings within hours; the clearest concurrency hazard in the corpus** ·
`_plugin_pin_trap.py` (320 + 360) · `effort_presets.py` (200 + 050) · `_config_defaults.py` (090 + 200 +
050) · `marshall-steward/` (070, 200, 360).

**⚠ Verification base commits are unreliable as checkpoints.** 320's `2402b02b`, 360's `5cea6604`,
050's `9afba956`, 210's `f816f85c` are **absent from this clone** (squashed/rebased away). Only
`ac06e4fc` resolves. **Landing commits all resolve and are the anchor of record.**

---

## Group G3 — orchestrator / inbox / landing

⛔ **39 of this group's 48 filed gaps are ALREADY CLOSED at HEAD** (110: 0/7 · 120: 4/4 · 180: 7/7 ·
250: 11/12 · 300: 9/9 · 302: 8/9). **9 remain open, concentrated almost entirely in plan 110.**

⚠ **Arithmetic correction made at ingestion.** The analysis agent's headline read "29 closed / 19
open"; its own per-plan breakdown and its own open-item list both sum to **39 closed / 9 open**
(0+4+7+11+9+8 = 39; open = 110's seven + `250/G4` + `302/G6` = 9). The detail is evidence-backed and
the headline was not, so the detail governs. Recorded rather than silently fixed — a summary figure
disagreeing with the rows it summarises is this epic's own archetype, committed in its ingestion.

| Plan | PR | Verdict | Deliverables | Gaps | Closed | Open |
|---|---|---|---|---|---|---|
| 110 landed-residue-promotion-sweep | 1169 | implemented-with-gaps | 4/4 | 7 | **0** | **7** |
| 120 rename-marshall→plan-orchestrator | 1162 | **fully-implemented** | 7/7 | 4 | 4 | 0 |
| 180 orchestrator-cleanup-verb | 1183 | implemented-with-gaps | 5/5 | 7 | 7 | 0 |
| 250 inbox-amend-supersede | 1198 | **partially-implemented** (corrected) | 5/6 — **D4 partly** | 12 | 11 | **1** |
| 300 operator-report-evidence-surface | 1211 | implemented-with-gaps (corrected) | 4/4 | 9 | 9 | 0 |
| 302 terminal-report-machine-readable | 1215 | implemented-with-gaps | 6/6 | 9 | 8 | **1** |

**⭐ 300 vs 302 — the exact relationship.** 302 is **not an independent follow-on**: it is a **mid-run
operator-directed SPLIT of 300 itself**, recorded in `300/report-01.md` § "Plan split". The operator
reversed an earlier "no split" decision mid-run and cut the seam between *the space* and *the emission*.
**300 kept D0–D3** (banded allocation contract, reserved terminal band 1000–1099, `archive-plan`
1000→1100, the `order: 9` collision, the collision check). **300's former D4–D8 became 302's D1–D5**
(`default:emit-landing` at order **1000**, occupying 300's reserved slot; the orchestrator-only compose
gate; the report↔inbox delta spec; the `landing-facts` payload; the drain-completeness check).
302 strictly serializes after 300 — its **D0 gate is "confirm 300's slot exists"**, and it passed.

**No gap is double-counted across 300 and 302** — verified by reading both files against each other. The
one item spanning the seam, **300/G3** (`reads:` applied nowhere), is filed **once, in 300 only**, at
`low`; its Module/topic field literally reads "the 300/302 seam". A reader auditing 302 alone would not
see it.

**Carries:**
- **110** — D0's gate correctly fired "not derivable", but the promotion landed in a `mode: knowledge`
  extension-author skill (`extension-api`) that **no agent-facing surface points at** — `grep -rn
  build-systems-common` over `persona-plan-marshall-agent/` and `plan-marshall/workflow/` returns
  **0 hits**. The audience that needs it still cannot reach it.
- **120** — provably a **pure token rename**: 242 removed / 242 added, 0 unmatched either way after
  applying only the four rename substitutions, independently re-derived. Nothing behavioural hides in a
  67-file diff.
- **180** — the verb's core is structurally sound under mutation (14 of 32 tests redden), but the plan
  **shipped its own headline defect one level up**: `abstained[]` told an operator a surface it *could
  not reach* had been *deliberately preserved* — the default output on every epic predating the landing.
- **250** — ⛔ **the archive migration has NEVER RUN.** Verdict is `partially-implemented` for exactly
  that reason and it is still true.
- **300** — ⭐ D3's collision check was **seen to fire on the live `order: 9` collision**, and resolving
  it revealed the collision was masking a real bug: `architecture-refresh` was snapshotting the tree
  *before* `security-audit`'s hardening edits — the exact inverse of its documented purpose.
- **302** — the drain-completeness check shipped **accepting the producer's own `n/a` as a present
  fact**, so a run whose fact reads all failed reported `complete: true`. Fixed — but nothing
  reconciles *shipped plans* against *landings seen*.

**⛔ THE TWO GAPS STILL OPEN IN THIS GROUP:**
1. **`250/G4` — the per-sender inbox archive migration has never run. EMPIRICALLY CONFIRMED on this
   machine**: `inbox/archive/` holds files directly (e.g. `audit-report-path-ignores-plan-dir-001.md`
   … `-011.md`, `content-search-seam-001.md`) across four epic trees. Plan 520 **explicitly excluded**
   it — *"a cloud run can neither perform the migration nor verify it … recorded as an operator
   obligation for a machine that holds the orchestrator store."* ⇒ **This is an OPERATOR ACTION on this
   machine, and `orchestrator inbox migrate-archive --slug SLUG` is the sanctioned verb.**
   ⚠ D4's atomicity requirement is satisfied only **vacuously** — there was never a file relocation for
   the code change to be atomic *with*. Whoever closes G4 inherits the constraint in substance.
2. **`302/G6` — `terminal_emission_dropped` is documented in no `.md` anywhere.** `grep -rln` over
   `marketplace/` and `.claude/` returns exactly one file, `manage-execution-manifest.py`. The field
   D2's entire observability claim rests on has no documentation.

**⚠ `302/G7` closed BY LUCK, not by design.** `.plan/marshal.json:170` gained `"default:emit-landing"`
in **`e0764ab14` (#1326)** — the commit immediately before HEAD — *after* plan 520 declared it out of
scope on the grounds that it must land **together** with 302/G5's roster row or the bidirectional
closure test reddens. G5 landed in #1317 and G7 in #1326: **split across separate PRs despite the gap
saying they must land together.** Both halves are now in the tree, so the test is satisfiable.

**⛔ The rename (120) is the group's upstream dependency and was SEQUENCED WRONG.** 120's plan insisted a
pure-rename plan must be sequenced **last** on its surface. It was not — **four of six plans (180, 250,
300, 302) named the pre-rename path in their Expected surface and had to re-ground at run time.** Cost:
five separate ad-hoc re-groundings instead of one.

**Collisions:** `orchestrator.py` (180, 250, 302) · `_orchestrator_inbox.py` (250, 302) ·
`workflow/cleanup.md` (**180 Step 8 + 250 Step 9 — same file, adjacent steps, direct collision**) ·
`workflow/analyze.md` (**250/G3's fix rewrites the very count invariant 302's drain feeds**) ·
`inbox-envelope.md` (250, 302) · `orchestration-model.md` (180, 250) · `ext-point-finalize-step.md`
(300/G4, 302/G4). **`extension-api/standards/build-systems-common.md` (110) is the ONE non-overlapping
surface in the group** — which is exactly why 110 was in neither remediation plan's scope.

**"Swept, clean" over an incomplete population — SIX OF SIX plans filed one**, and in 110, 250, 300 and
302 **the verifier's own sweep was then also incomplete**, each adversarial pass finding more with a
broader pattern. 300's residual doubt states it plainly: *"the pattern searched for `61`; the same class
almost certainly exists for other superseded values."*

**⚠ Verdict-calibration rule the corpus uses but never wrote down:** *implemented **partly*** →
`partially-implemented`; *implemented but **incomplete*** → `implemented-with-gaps`. It turns on a
single word in one cell of one table. 250 was corrected on it; 302's D4 (`Implemented? yes /
Complete? no`) was upheld under it.

**⚠ Reviewer coverage degraded on EVERY PR in the group** — 110 = 2 of 3; 120, 180, 250, 300, 302 = **1
of 3 each**, always `cuioss-review-bot` alone with both others rate-limited. ⭐ **110, the one PR that
did get CodeRabbit, received three valid findings including one Major** — and #1317's own commit message
records that *"the single most valuable finding came from CodeRabbit, not from any of [eleven
self-directed verification passes]."* Direct evidence of the rate-limit shortfall's cost.

---

## ⛔⛔ MASTER GAP LEDGER — re-derived at HEAD during ingestion

The audit reported **283 open gaps**. That figure was true at PR #1298 (2026-08-18). Three remediation
plans have landed since. Re-derived at HEAD from the seven groups' evidence-backed per-plan closure
lists:

| Group | Gaps | Closed at HEAD | **Open** |
|---|---:|---:|---:|
| G1 plugin-doctor / docs (040 100 130 170 190 270) | 42 | 13 | **29** |
| G2 finalize / CI (030 160 230 330 390 440) | 34 | 8 | **26** |
| G3 orchestrator / inbox (110 120 180 250 300 302) | 48 | 39 | **9** |
| G4 config / version (050 070 090 200 210 320 360) | 45 | 17 | **28** |
| G5 metrics / ledger (150 220 290 410 420 460) | 29 | 3 | **26** |
| G6 planning / tests (240 260 280 340 350 380 430) | 44 | **0** | **44** |
| G7 git / cloud lane (060 080 140 310 370 450) | 41 | 10 | **31** |
| **TOTAL** | **283** | **90** | **193** |

⇒ **193 open gaps, not 283.** Every count in every `gaps.md` overstates by its plan's closure column.

**Closures by remediation plan:** #1320 (plan 500) and #1309 (plan 510) did the bulk; #1317 (plan 520)
cleared almost the whole orchestrator group; `302/G7` closed incidentally in #1326.

**⛔ 23 of the 44 executed plans have had NO remediation pass at all** — `030 070 080 110 140 150 170
200 210 220 240 260 270 280 290 340 350 370 380 390 420 430 450`. **Group G6 (44 gaps) is untouched in
full**, and plan **110** is the orchestrator group's single blind spot (7 open, in neither remediation
plan's scope, on the one surface nothing else touches).

**Highest-value open items, from the carries:**

1. **`380/G1` + `380/G7` + `430/G2` + `430/G3`** — a green build whose only outcome is skips reports a
   non-zero executed-test count and **clears a pending `test-failure` finding**; the zero-skip gate that
   would bound it is armed nowhere. Must be fixed as **ONE change** (shared `_build_shared.py`).
2. **`080/G9`** — `ClaudeRuntime.project_initial_setup` unconditionally overwrites `marshal.json` with
   no read and no existence check: **the maximal lost update on the very file the plan protected.**
3. **`070/G1`** — a daemon pinned below the counts extension answers the handshake without them,
   `run_status` writes `0`, and reconcile **drains a live build**.
4. **`360/D1`** — the root lever never shipped; absolute version-pinned paths are still baked into the
   executor. *(This is the same surface as the standing registry/executor-pin incident family.)*
5. **`250/G4`** — the per-sender inbox archive migration has never run. **Actionable on this machine.**
6. **`290/G1`** — a **false diagnosis living in a production docstring** that would send a reader to
   "fix" 28 working call sites.
7. **`210/G2`/`G3`, `160/G1`, `130/G5`, `040/G6`** — guards that pass against the defect they name.

---

## Derived plans 500 / 510 / 520 — post-verification performed AT INGESTION

These three shipped with **no `verification.md` and no `gaps.md`**. The audit authored them but never
verified them, because they were executed after the audit closed. Post-run verification was performed
during this ingestion, to the same method as the other 44 (deliverables checked against HEAD on four
axes, upstream `closes` annotations re-checked per gap, mutations snapshotted to `$TMPDIR` and restored
by byte-copy with md5 verified). Full records: `landings/PLAN-TRUTH-083.md`, `-084.md`, `-085.md`.

| Cloud | Ledger id | PR | Verdict | Deliverables | New gaps |
|---|---|---|---|---|---|
| 500 | PLAN-TRUTH-083 | #1320 | implemented-with-gaps | 8/8 | 8 (1H/4M/3L) |
| 510 | PLAN-TRUTH-084 | #1309 | *(see landing record)* | | |
| 520 | PLAN-TRUTH-085 | #1317 | implemented-with-gaps | 8/8 | 8 (0H/4M/4L) |

**⛔ `500/G1` (high) — the defect class was closed in three rules and LEFT LIVE IN A FOURTH.**
`analyze_argument_naming` returns `[]` and the gate reports `findings: 0` whenever
`.plan/execute-script.py` is absent — **which is every cloud clone** — silently disabling the whole
`ARGUMENT_NAMING_*` cluster **including the rule plan 500 itself added**. The no-op is undisclosed: the
gate renders *clean* rather than *could not look*. That surface is inside the plan's own Expected
surface, and the plan twice demanded the coverage gap be "recorded, not asserted clean". It was not.

**⭐ 520's upstream closure is genuinely good: 30 claimed → 29 CLOSED, 1 PARTIAL, 0 NOT-CLOSED.**
`302/G1` — the highest-severity gap in the orchestrator group — is closed and was **verified by
execution, not reading**: dropping `steps` from `LANDING_SENTINEL_REJECTING_KEYS` turns the pinning
test RED. `250/G7` is the single partial: `close-stream` is reclassified as an append everywhere, but
`inbox-envelope.md` states two different in-place-edit counts **12 lines apart**. Carried as `520/G6`.

**⛔ BOTH derived plans had their diff silently widened by the review cycle AFTER their figures were
derived.** In 520, CodeRabbit added `decompose.md` and `effort-roles.md` after the last verification
round — so **every count in that report taken before the review cycle is one low**, and three separate
"inconsistencies" are the same unswept fix at three sites. In 500, § Collateral claims derivation from
`git diff` yet omits two files including a **production** change to `resolve_project_dir.py`, from the
same cause — *the 4th recurrence of the exact defect that report's own Proposal 2 names.*

⇒ **STANDING RULE: a derived figure must be re-derived AFTER the review cycle closes, not before.**
The review cycle is a diff-widening event, and every report in this corpus that derived its counts
before it is wrong by exactly the review's own footprint.

**⭐ The counter-signal from 500 is worth as much as its defect.** Every census/population/count figure
in that report re-derives **EXACTLY** (152/81/71/69, the 43/18/2/7/1 cause split, 18 across seven
notations, 6 brace-less sites, 25 anchors / 4 detectable, 33 and 414, 46/21, 29 rows, 6 subsections,
5 signatures) while its narrative sections went stale in five places. ⇒ **Mechanically-derived figures
survived a run in which hand-written prose did not.** That is the strongest evidence in the corpus for
deriving rather than asserting, and it points the same way as RULING 1.

**⚠ Neither verification ran a full `./pw verify`, and neither queried the GitHub API.** 500: 691 tests
across 15 named files plus the 1885-test plugin-doctor directory. 520: 399 tests across 5 changed
modules plus the 586-test `plan-orchestrator` suite. Both confirmed review-comment substance **by
execution** instead of by thread state. Squash merges mean no per-commit claim in any of the three
reports is checkable.

---

## Plan 510 — post-verification result, and the FINAL live gap arithmetic

**510 = PLAN-TRUTH-084, PR #1309, `7566efd95` — implemented-with-gaps, 8/8 deliverables, 9 new gaps
(2 high). Upstream: 36 claimed → 33 CLOSED, 3 PARTIAL, 0 NOT-CLOSED.** Full record:
`landings/PLAN-TRUTH-084.md`.

**⛔ `510/G1` (high) — the plan's central mechanism fires on an UNDOCUMENTED MAGIC STRING.** The
input-table conformance scope that `ext-point-finalize-step.md` itself calls *"where the contract is
actually held"* fires only on tables whose first header cell is the literal `Prompt-body field`, a
convention stated in no normative document. A matched positive/negative control differing only in that
header flips the suite RED → 19-passed-green. **Same shape as the gap it was written to close.**

**⛔ `510/G2` (high) — `190/G6` IS CLOSED ON ITS DOCUMENTATION HALF ONLY.**
`phase-6-finalize set --field self_review` **still succeeds and persists a dead key**. D4's own preamble
diagnoses this as *"a shipped false signal on the highest-risk gate the page describes"* and then fixes
only the documentation half, **with no residue entry**.

### ⚠ FOUR of the 90 closures are PARTIAL — each residue is carried, none is lost

| Upstream gap | Closed as to | Still open as | Carried in |
|---|---|---|---|
| `190/G6` | the documentation | the `set --field` code path | `510/G2` (high) |
| `260/G1` | one header string | "any finalize-step doc" (its own *Done-when*) | `510/G1` (high) |
| `280/G2` | most `resolve-target` sites | `planning.md:233` — a site 510's Out-of-scope excludes **by name** | `510` residue |
| `160/G2` | four "derived" labels | a fifth, surviving as a source comment | `510/G8` (low) |
| `250/G7` | the reclassification | two in-place-edit counts 12 lines apart | `520/G6` (low) |

⇒ **A "closed" gap is not automatically a settled one.** Re-ground at HEAD before scheduling; the
`gaps.md` snapshot and the closure column are both leads, not facts.

### FINAL live gap arithmetic

| Population | Count |
|---|---:|
| Original corpus (44 plans, audit at #1298) | 283 |
| — closed at HEAD by #1320 / #1309 / #1317 / #1326 | **90** |
| = original still open | **193** |
| + new gaps filed by the derived plans (500: 8 · 510: 9 · 520: 8) | **25** |
| **= LIVE OPEN GAPS** | **218** |

**Of the 25 new gaps, 3 are high**: `500/G1` (detector no-ops without `.plan/`, reports clean),
`510/G1` (guard bound to an undocumented header string), `510/G2` (dead config key still persists).

**⭐ The single most transferable rule this ingestion produced.** Both 500 and 520 had their diff
silently widened by the review cycle **after** their figures were derived, and 510's own § Reviewer
participation used a floating `origin/main` endpoint **three sections after § Build gate corrects
exactly that defect**. ⇒ **A derived figure must be re-derived AFTER the review cycle closes.** The
review is a diff-widening event, and every report in this corpus that derived counts before it is
wrong by the review's own footprint.

---

## Ownership, and the four plans staged to close the gap

Re-derived over the whole live set after ingestion: **218 open gaps, 38 with NO owning plan** — 13
original-corpus residue plus all 25 the derived plans filed. The 8 pre-existing staged plans were
authored on 2026-08-18 and **structurally cannot** cover gaps filed by runs on 08-20/21.

Four plans were staged to close it:

| Plan | Scope | Closes |
|---|---|---|
| `PLAN-TRUTH-094` | plugin-doctor detector coverage residue | `500/G1–G3, G5–G8` |
| `PLAN-TRUTH-095` | finalize-step contract guard residue | `510/G1–G4, G6–G9` |
| `PLAN-TRUTH-096` | orchestrator inbox + landing residue | `520/G1–G8`, `250/G4` (sibling epics) |
| `PLAN-TRUTH-097` | dispatch contract + the two unopened measurement gates | `260/G1,G2,G3,G6,G7`, `280/G2,G4,G7`, `160/G4`, `230/G1,G4`, `440/G4` |

**Result: 216 of 218 owned.** The two remaining — `500/G4` and `510/G5` — are both **run-report
corrections**, so RULING 1 disposes of them as closed-as-recorded. That is a disposition, not a
coverage hole.

⛔ **`PLAN-TRUTH-097` MUST RUN LOCALLY.** Its D7 opens the two gates no cloud clone could open —
`230/D0`'s archived CI-manifest corpus and `440/D4`'s before/after re-fire measurement on a real
finalize. Both need `.plan/` state. This is the epic's standing lesson about the cloud lane, converted
into a scheduling constraint.

## ⚠ The cross-check's collision verdict is an UNDERCOUNT — do not schedule on it

`corpus cross-check` reports **one** staged-vs-staged collision (`095` ↔ `097`, on
`ext-point-finalize-step.md` and `_gate_coverage.py`). **That figure is not trustworthy.** The check
matches **exact normalized paths**, and the eight pre-existing staged specs carry **34 abbreviated or
bare** surface entries (`.../manage-config/SKILL.md`, bare `cache_retention.py`, `_build_parse.py`)
which cannot match a full path. The four plans staged at ingestion use full paths only (0 abbreviated),
so the check sees them correctly and the older ones barely at all.

⇒ **The authority for sequencing is the per-group collision map derived by the ingestion agents, not
the script.** Known real collisions the script cannot see:

| Surface | Staged plans |
|---|---|
| `_build_shared.py` + `_build_format.py` | **087** — and `380/G1`+`G7`+`430/G2`+`G3` must be ONE change |
| steward surfaces (`effort-menu.md`, `wizard-flow.md`, `menu-configuration.md`) | **086** ↔ **091** |
| ledger readers (`analyze-logs.py`, `data-format.md`) | **088** ↔ **092**, and `audit.py` is the hottest file in the corpus |
| `test_phase_2_refine_manage_config_readonly.py` | **089** ↔ **090** — `210/G1` is double-routed, a single test file claimed by two plans |
| `manage-config/standards/data-model.md` | **086** ↔ **091** |
| `ext-point-finalize-step.md`, `_gate_coverage.py` | **095** ↔ **097** *(the one the script did see)* |

**Genuinely disjoint and safe to run in parallel:** `093` (preference admissibility), `094`
(plugin-doctor), `096` (orchestrator inbox), and `075` (cloud-lane build gate).

⇒ **A follow-up worth staging:** normalise every staged spec's `## Expected Surface` to full
repo-relative paths, so `corpus cross-check` can actually see the corpus it is asked to check. A
disjointness gate that cannot resolve 34 of its inputs is a gate reporting clean over a population it
never examined — this epic's own archetype, sitting in the orchestrator's own tooling.
