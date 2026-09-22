# PLAN-TRUTH-059: `sync-plugin-cache` updates the cache and the executor and **never the registry** — so the pin points at a GC-scheduled directory

epic: truthful-signals
workstream: WS-01

⛔⛔ **The `#896` failure mode is currently ARMED on this machine.**

## Objective

The registry-pin / orphan-GC inversion has recurred **~daily for a week (9 recorded incidents)** and has
been treated as an operational nuisance. **The mechanism is now named, and it makes the recurrence
inevitable rather than unlucky.**

> ⭐⭐ **`sync-plugin-cache` updates the CACHE and the EXECUTOR, and never the REGISTRY.**

⇒ Every cache sync moves the cache forward and leaves `installed_plugins.json` behind. **This is not
drift; it is a producer that writes two of three stores.**

## OBSERVED — the current state is the dangerous one

Verified by this orchestrator at ~07:10Z: pin `0.1.1288`, sole unmarked dir of 41 ⇒ `unmarked == [pinned]`
held, **repaired**.

⛔ **`code-intelligence-substrate` re-checked after #1084's cache sync:**

- The sole **unmarked** version is now **`0.1.1291`** — matching the **executor**.
- **`installed_plugins.json` still pins `0.1.1288`**, which is now **orphan-marked and GC-scheduled.**

⇒ ⛔⛔ **The pin points at a directory scheduled for deletion.** That is precisely the `#896`
failure mode — *the 7-day GC deleting a cache version a stale executor is pinned to* — which produced
`ModuleNotFoundError: plan_logging` on the nifi upgrade. ⭐ **The remedy `#896` shipped was an executor
bootstrap self-heal; this plan is about not arming the trap in the first place.**

⚠ **My own 07:10Z snapshot is therefore already stale** — recorded so nobody reads it as a resolution.
*A pin state is a snapshot, never a status.*

## ⛔ Why a pre-launch check is necessary and demonstrably NOT sufficient

Incidents **7, 8 and 9 all fired INSIDE one plan run** (#1085) — `automatic-review`,
`plan-retrospective`, and `lessons-capture`, the last **self-observed at load, from inside its own
dispatch**, announcing a persona from a version **49 behind** its own envelope, **with no loader
indication.**

⇒ **The failure is not in the pin at launch; it is in what the session's loaded registry serves when
asked, hours later.**

⭐⭐ **And it is not merely a doc-read nuisance** — established on #1085: a stale `0.1.1240` read produced
the `--enabled-bots` flag, a `0.1.1288` script rejected it with **exit 2**, and the pre-merge barrier
turned that into **"clean, 0 findings" in 33 seconds**. ⇒ **A pin gap manufactures FALSE GREEN AT THE
MERGE BOUNDARY.**

## ⛔ Scope — the fix is not ours; the DETECTION is

`installed_plugins.json` is **the plugin manager's file.** ⛔ **Do not write it, and do not propose
writing it** — a third-party store with a second writer is `PLAN-TRUTH-049` with the plugin system as
the other producer.

⇒ **What is ours**: (a) noticing, (b) refusing to proceed silently, (c) telling the operator what to run.
⭐ **Neither epic has filed this**, which is why a known-daily defect has no owner.

## Deliverables

1. **D0 — GATE: derive the three stores and who writes each.** cache dirs / `installed_plugins.json` /
   the generated executor. ⛔ **Confirm the named mechanism by SYMBOL** — that `sync-plugin-cache` writes
   cache + executor and not the registry. ⚠ **It is currently a stated conclusion from two observers,
   not a code read.** *A corrective is a hypothesis until the named site is read.*
2. **D1 — a detector with the RIGHT oracle.** ⛔ **Counting executor path-versions does NOT detect it** —
   every recorded incident had a **clean executor and a stale loader**. ⭐ **The assertion is
   `unmarked_dirs == [pinned_version]`**, read from `installed_plugins.json`. ⚠ **Both failure states
   must be caught**: the pin orphan-marked while a newer dir is unmarked (today), **and zero unmarked
   dirs** (observed 08-02 — `[]` is a failure state too, not a pass).
3. **D2 — a mid-run assertion, because pre-launch is provably insufficient.** A dispatched envelope must
   be able to establish that a loaded skill body came from the pinned version. ⭐ **The loader announces
   its base directory** — that string is the available evidence. ⛔ **Fail closed and say which version
   it got**, rather than proceeding with a body from 49 versions back.
4. **D3 — the operator-facing remedy is stated, not implied.** The detector reports **what to run**
   (`/reload-plugins`, repair the pin). ⚠ **A session restart does NOT fix it — reconfirmed repeatedly.**
   ⭐ The working in-run remedy is **`Read` the pinned `SKILL.md` directly**; state that too.
5. **D4 — tests, each verified to FAIL pre-fix.** (a) The live inversion (pin `0.1.1288` orphan-marked,
   `0.1.1291` unmarked) is detected. (b) The all-marked state (`unmarked == []`) is detected. (c) A
   healthy state passes. (d) A dispatched load from a non-pinned version is reported.

⚠ Five deliverables. ⛔ **Do NOT widen into fixing the registry** — see § Scope.

## Claim Labels

- **OBSERVED (this orchestrator, first-party, 08-03 ~07:10Z)**: pin `0.1.1288`, sole unmarked of 41.
  ⚠ **Now stale — superseded by the sibling's later read.**
- **REPORTED (sibling, first-party to them, after #1084)**: `0.1.1291` unmarked / `0.1.1288` pinned and
  orphan-marked. ⛔ **Re-verify at D0 — it is the whole premise, and it is cheap.**
- **REPORTED / stated conclusion, NOT a code read**: that `sync-plugin-cache` never writes the registry.
  ⭐ **It explains the daily cadence and is the plan's organising claim** — ⛔ which is exactly why D0
  must confirm it by symbol rather than adopt it.
- **OBSERVED (ours, #1085)**: incidents 7/8/9 in one run; the 49-version gap self-observed inside a
  dispatch; the `--enabled-bots` → exit 2 → "clean" chain.
- ⛔ **NOT ESTABLISHED**: whether the GC has ever actually deleted a pinned dir here. ⚠ **The trap being
  armed is not the trap having fired** — do not report it as damage taken.

## Expected Surface

- **HYPOTHESIS**: `.claude/skills/sync-plugin-cache/` — the sync script (meta-project-only surface)
- **HYPOTHESIS**: `tools-script-executor/scripts/generate_executor.py` — the pin/selector logic
- **HYPOTHESIS**: `plugin-doctor` — the natural home for D1's detector
- **OBSERVED (read-only)**: `~/.claude/plugins/installed_plugins.json`, the cache tree

## Dependencies and Sequencing

- ⚠ **Adjacent to `PLAN-TRUTH-049`** (two producers write `.orphaned_at` in two encodings) — **same
  tree, different defect.** ⛔ **Do not fold**: 049 is the marker's ENCODING, this is the registry's
  STALENESS. ⭐ But **049's D-1 aged-marker test and this plan's D1 read the same directories** — run
  them together if both are in flight.
- ⚠ Adjacent to `PLAN-TRUTH-008` (executor preflight stamps rather than resolves). **Cite; evaluate
  absorption at outline.**
- ⭐ **Cross-epic**: `code-intelligence-substrate` named the mechanism and has not filed it. **Tell them
  this plan exists so neither of us writes the detector twice.**

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/truthful-signals/plans/PLAN-TRUTH-059-sync-plugin-cache-updates-the-cache-and-executor-and-never-the-registry.md"
```

## ⭐ FOLDED IN 2026-08-08 — ownership CONFIRMED cross-epic, and the D0 premise is now VERIFIED

From `code-intelligence-substrate-023` § 2 and `review-apparatus-018` § 4, plus a first-party
symbol check run at the drain.

- ✅ **CIS checked their 28-plan queue and confirmed nobody owns the pin detector.** They have
  written a **do-not-duplicate** into their own ledger naming `PLAN-TRUTH-059` as owner. ⇒ No
  cross-epic coordination is owed; **this plan is the only detector.**
- ⭐ CIS singled out the half they would have missed: **`unmarked == []` being a FAILURE state
  rather than a pass.** Keep it explicit in the oracle — an empty set reads as *"nothing stale"*
  to anyone writing the obvious check.
- ✅ **D0's premise is CORROBORATED, not merely repeated.** Both siblings assert
  *"`sync-plugin-cache` updates the cache and the executor and never the registry"*, and CIS
  flagged their own version as **refutable and second-hand — a stated conclusion from two
  observers, not a code read**. ⛔ Two ledgers asserting one unverified claim is still ONE
  SOURCE. It has now been checked first-party at this drain, by two independent methods: a
  direct grep of `.claude/skills/sync-plugin-cache/` and an inventory-wide content search for
  `installed_plugins`. **Result: no code anywhere in the tree writes the registry** — the only
  matches are three prose mentions in `plugin-script-architecture/references/notation-spec.md`.
  ⚠ This is an **absence** claim and is bounded by the search's coverage: the content sweep is
  inventory-scoped. D0 should still confirm by symbol at the sync entry point rather than
  inheriting this note.
- ⛔⛔ **THE TRAP IS ARMED RIGHT NOW, AND THE STATE IS WORSE THAN THIS SPEC RECORDS.** Re-surveyed
  first-party at the #1115 landing: **`unmarked == ['0.1.1240', '0.1.1304']` — TWO unmarked dirs**
  against pin `0.1.1304`. The spec above describes a pin-not-in-the-keep-set shape; the live shape
  is a **stale unmarked dir sitting beside a correct pin**, which is the configuration that seated
  a session 48 versions backward. The executor separately pins **`0.1.1325`**, orphan-marked in
  epoch-ms and absent from the registry. ⇒ **The oracle must reject `[stale, pin]` as well as
  `[]` and `[wrong]`** — three failure shapes, not one.
- ⛔⛔ **THE ORACLE AS STATED IS INSUFFICIENT — `unmarked == [pin]` CAN PASS OVER A LIVE SPLIT.**
  This is the sharpest correction available to this spec and it comes from an incident where the
  check *passed*: pin, markers and the loader all agreed on `0.1.1304` while the **executor** sat at
  a different, orphan-marked version. A two-way agreement certified a three-way disagreement.
  ⇒ **THE ORACLE IS: `executor_version == registry_pin == the sole unmarked dir` — THREE consumers,
  ONE number.** Any pairwise formulation is a vacuous guard in this plan's own sense: green because
  it did not examine the third consumer. D1 must assert all three, and its negative control must be
  a tree where two agree and the third does not.
- ⚠ **AND THE ARMING PATH IS ROUTINE, NOT EXCEPTIONAL**: the `generate_executor preflight` that runs
  on ordinary `/plan-marshall` invocations re-anchors the executor at a freshly-generated directory,
  which a later sweep can orphan-mark. ⇒ **Any plan can arm this, not only one that syncs the cache**
  — which is why a pre-launch check is insufficient and the assertion has to sit where the executor
  is resolved.
- ⭐ **The re-arming agent is now named**: PR #1115's own `sync-plugin-cache` finalize step
  regenerated the executor to `0.1.1325`. **The finalize that reports the condition is the
  finalize that creates it** — which is why a pre-launch check is provably insufficient.
- **Cluster C11** (`lessons-handling-26-08-08-01-005`, 6 corpus instances, plugin-cache and
  executor regeneration staleness) is routed here as its home. ⚠ Corpus instances not re-derived.

## ⛔⛔ THE ORACLE IS A WELL-FORMEDNESS CHECK, NOT A FRESHNESS CHECK — accepted from CIS `-024`, 2026-08-08

**This refutes the oracle's SUFFICIENCY, not the plan.** ✅ **The ask is ANSWERED YES: the second
conjunct is adopted as a deliverable.**

CIS measured, first-party on this machine: `installed_plugins.json` pins `0.1.1304`, `0.1.1304` is the
**only** unmarked dir ⇒ **`unmarked == [pin]` HOLDS and the oracle reports CLEAN** — while of **360**
`.md` files under `marketplace/bundles/plan-marshall/skills/`, the pinned dir matches source on **352**
and **diverges on 8**, and all 8 match the *orphan-marked* `0.1.1325`:

`manage-status/SKILL.md` · `plan-retrospective/SKILL.md` · `marshall-steward/SKILL.md` ·
`manage-lessons/SKILL.md` · `manage-lessons/standards/cwd-keyed-store-resolution-audit.md` (exists
ONLY in 1325) · `manage-locks/standards/cwd-keyed-store-resolution-audit.md` ·
`manage-architecture/standards/arch-gate-fitness-functions.md` · `plan-marshall/workflow/planning.md`

⇒ **The dir that matches source is scheduled for deletion; the dir that is pinned and loaded is not the
newest source state.**

⭐⭐ **Why every cheap ordering misses it — the transferable part.** A later-written cache dir was built
from an OLDER source state, so version ordinal says `1325 > 1304` (newer), directory mtime says `1304 >
1325` (newer), **the two heuristics contradict each other**, and only content-vs-source is right.
⛔ **Do not swap one heuristic for the other** — today either alone yields a confident wrong answer, in
opposite directions.

⇒ **`unmarked == [pin]` establishes that the registry and the keep-set agree WITH EACH OTHER. It says
nothing about whether either agrees with the REPOSITORY.** That is an internally-consistent pair of
records, mutually confirming and jointly wrong — the exact shape both epics keep filing against other
people's detectors, now found in our own.

**D-new (adopted): `pin_content == source_content`**, sampled over the bundle's `.md` set and reported
as **"N of M files match; K diverge"**, never as a boolean. *"352 of 360 match"* is actionable;
*"stale"* is not, and *"clean"* would have been wrong here. It degrades honestly — a partial scan says
so — which is this epic's population rule applied to the detector itself.

**The failure states are now FOUR, and the oracle must reject all of them:**

| # | Shape | Caught by |
|---|-------|-----------|
| 1 | `unmarked == []` | keep-set conjunct |
| 2 | pin orphan-marked while a newer dir is unmarked | keep-set conjunct |
| 3 | `unmarked == [stale, pin]` — a stale unmarked dir beside a correct pin (measured here 2026-08-08) | keep-set conjunct |
| 4 | **`unmarked == [pin]` AND the pin is stale against source** | **content conjunct (new)** |

⚠ **AND THE UNMARKED SET IS NOT STATIONARY.** This epic measured `unmarked == ['0.1.1240','0.1.1304']`
and CIS measured `unmarked == ['0.1.1304']` **the same day**. Both readings are honest; the markers are
being rewritten between them — which `PLAN-TRUTH-049`'s re-grounded D-1 independently found. ⇒ **Any
oracle that samples the unmarked set once is sampling a moving value**, so D1 must state its sampling
instant and treat a single reading as a snapshot, never a status.

⚠ **Second-hand**: the 8-file delta is first-party to CIS and **NOT re-derived here**. One machine, one
instant, non-monotonic version ordinals. **Re-derive at D0 before pinning a test to the 8 filenames** —
use them as the shape of the defect, not as the expected set.

✅ **Ownership unchanged**: CIS is still not staging a rival detector; their do-not-duplicate stands.

## ⭐⭐ MERGED 2026-08-08 — this plan ABSORBS -008 + -039

**Component:** `tools-script-executor (executor & registry truthfulness)` · **Deliverables after merge: 12** (raised cap is 12).

Three plans, one component, one property: **the executor/cache layer reports a freshness and a
success it has not established.** Exactly 12 deliverables — at the raised cap, not over it.

- **`-059`** — `sync-plugin-cache` updates the cache and executor and **never the registry**; the oracle
  now needs FOUR conjuncts, including CIS's `pin_content == source_content`.
- **`-008`** — `generate_executor preflight` decides freshness by **version stamp**, never by content.
  ✅ **CONFIRMED at HEAD: `MARSHALL_VERSION` comparisons, ZERO `sha256`.** ⭐⭐ **This is the same defect
  as `-059`'s new fourth conjunct, reached from the other side** — CIS measured a pinned dir diverging
  from source on 8 of 360 files while every stamp-based check passed. **A stamp is not a hash.** Neither
  plan could have stated that alone; together it is one deliverable, not two.
- **`-039`** — every `argparse_rejection` embeds the usage banner and truncates the recoverable part.
  ⭐ Measured at **463 signatures across 48 of 58 plans — the corpus's largest waste class** — while its
  own recurrence detector scores **0**. It belongs here because the rejections are *executor-dispatched
  script* failures and the fix is in the executor's logging path.

⛔ **Internal order is load-bearing**: the content-hash conjunct (`-008` + `-059` D-new) must land before
any "normalise the corpus" step, or the normalisation is validated by the stamp check it replaces.

⛔ **The absorbed spec(s) are `superseded` and retained as the record — do not implement or emit them.**
⚠ **Re-count deliverables at outline.** The figure above is the sum of the pre-merge counts; overlapping deliverables should COLLAPSE rather than concatenate, and a merged plan that still reads as two plans stapled together has not been merged.

## ⭐ FOLDED IN 2026-08-09 — three `generate_executor` defects from the 2026-07-04 review, RE-VERIFIED AT HEAD

`doc/review-26-07-04.md` is being retired; these three survive re-verification and belong to this
plan's component (`tools-script-executor`). **All three were checked against HEAD at fold time — they
are not inherited claims.**

- **[R1] The generation fallback is unreachable on its most common failure — *High*.**
  `cmd_generate` wraps `discover_scripts()` in `try/except Exception` to fall back to
  `discover_scripts_fallback()`, but `discover_scripts` signals *"inventory not found"* via
  `sys.exit(2)` — a `SystemExit`, which is a `BaseException`, **not** an `Exception`. The handler is
  bypassed and **the glob fallback never runs for exactly the failure it exists to cover.**
  ✅ **Re-verified at HEAD: `cmd_generate` still does not catch `SystemExit`.** The sibling `cmd_drift`
  does. ⭐ This is a vacuous fallback — an error path that cannot be reached — which is this epic's
  archetype in the executor itself.
- **[R8] Executor validation interpolates a filesystem path into `python3 -c` source — *Low*.**
  `verify_executor` / `get_executor_mappings` f-string the real executor path into
  `spec_from_file_location('executor', '{path}')` and run it with `python3 -c`. A checkout path
  containing a quote or backslash breaks the generated program. ✅ **Re-verified: 2 interpolation
  sites at HEAD.** Fix: pass the path via `sys.argv`/env, never into the source string.
- **[R9] `discover_scripts_fallback` drops any script whose name contains `test` — *Low*.**
  The glob fallback skips on the **bare substring** `'test' in name.lower()`, which also matches
  legitimate entrypoints (`latest.py`, `contest.py`). ✅ **Re-verified at HEAD.** Fix: match
  `test_` / `_test` precisely. ⭐ A discovery gap that exists **only** in the fallback path — so it is
  invisible until R1 is fixed and the fallback actually runs. **R1 and R9 must land together**, or
  fixing R1 activates a path that silently drops scripts.

⚠ **Line numbers from the review are 5 weeks stale — verify by symbol.** The review says so itself.

## ⛔⛔ "THE REGISTRY PIN" IS NOT ONE VALUE — TWO FIELDS, AND THEY DISAGREE (2026-08-09, first-party)

**This corrects the oracle as specified everywhere above, including my own three-way and four-conjunct
formulations.** Measured at the pre-restart check on 2026-08-09, after an operator repair:

| Consumer | Value |
|---|---|
| sole unmarked cache dir | **`0.1.1327`** |
| `.plan/execute-script.py` `MARSHALL_VERSION` | **`0.1.1327`** |
| registry `installPath` (14/14 plan-marshall entries) | **`0.1.1327`** |
| registry **`version`** (14/14 plan-marshall entries) | ⛔ **`0.1.1326`** — and 1326 IS orphan-marked |

⇒ **`installPath` and `version` disagree in every plan-marshall entry.** The registry is internally
inconsistent with *itself*.

⭐⭐ **THE CONTROL IS WHAT MAKES THIS A FINDING RATHER THAN A FORMAT QUIRK.** The one third-party
plugin in the same file (`frontend-design@claude-code-plugins`) has `installPath` and `version` **in
agreement** (`1.1.0` / `1.1.0`). **14 of 15 entries disagree; the 1 that isn't ours agrees.** So the
two fields are normally equal, and the divergence is real drift produced by our repair path — not a
schema in which they are permitted to differ.

⛔ **CONSEQUENCE FOR D1 — THE ORACLE MUST NAME ITS FIELD.** An oracle reading `version` reports a
**false alarm** here; one reading `installPath` reports **clean**. Both are "the registry pin". A
detector that says *"pin"* without naming the field is unfalsifiable — it will be right or wrong
depending on an unstated choice, which is this epic's archetype exactly.

- **`installPath` is the load-bearing field** (it is the path actually resolved), and it agrees with
  the unmarked dir and the executor ⇒ **the load path was healthy at this reading.**
- **D1 must assert on `installPath`** for the load-safety question, **and separately assert
  `installPath == version`** as its own conjunct, because a registry disagreeing with itself is a
  distinct defect from a registry disagreeing with the cache.

⚠ **I got this wrong first.** My earlier readings extracted "the pin" with a regex over the whole JSON,
which returned **both** fields and made a healthy load path read as `ORACLE: FAIL`. **A field name is
part of a claim; "the pin" is not a value.** Recorded against myself — same class as reading a
disjointness off a title instead of a file list.

⇒ **The failure set is now FIVE**: `unmarked == []` · `[stale, pin]` · pin orphan-marked while a newer
dir is unmarked · `unmarked == [pin]` with pin stale **against source** · and **`installPath != version`
within the registry itself**.

---

## ⛔⛔ FOLDED AT THE PLAN-TRUTH-049 LANDING (2026-08-09) — THE MARKER SET IS DRIVEN BY A THIRD PARTY, AND IT RE-ANCHORS ON THE REGISTRY

**OBSERVED — first-party, double-sampled seconds apart (both samples agreed, so this is not the
read-during-write artefact that manufactured the incident-13 false alarm).** Whole population,
14 version dirs enumerated, not sampled:

| consumer | value |
|---|---|
| registry `installPath` | `0.1.1327` (14/14 plan-marshall entries) |
| registry `version` | `0.1.1326` — **orphan-marked** (the disagreement recorded above, still live) |
| executor `MARSHALL_VERSION` | `0.1.1331` |
| **sole unmarked dir** | **`0.1.1327`** |

**⭐⭐ THE NEW MECHANISM, AND IT IS THE ONE THAT EXPLAINS WHY THIS RECURS DAILY.** Marker contents and
mtimes place the transition to the second:

- `0.1.1331` was marked at **08-09 09:39:03.967** with **`1786261143967` — raw epoch-ms, the FOREIGN
  encoding.**
- `0.1.1327`'s directory mtime changed at **08-09 09:39:03.901** — **its marker was DELETED**, 66 ms
  earlier.

⇒ **The foreign producer (Claude Code's plugin GC) does not merely add markers. It RE-ANCHORS the whole
set on the registry `installPath`, un-marking that dir and marking every other.**

**⛔ CONSEQUENCE FOR D1, AND IT IS SHARPER THAN THE FIELD-NAMING ONE ABOVE.** The "sole unmarked dir"
is not an independent third consumer at all — **it is a lagging function of the registry.** So the
oracle's three-way assertion `executor == pin == sole unmarked dir` is not three independent
measurements; it is **two** (executor, registry) plus a derived value that the foreign GC periodically
forces into agreement with the registry. An oracle that treats the unmarked set as independent
corroboration of the registry is **counting one witness twice**.

- **D1 must state that the unmarked set is REGISTRY-DERIVED, not independent** — and must therefore
  gate on `executor == installPath` as the load-safety conjunct, with the unmarked set used only to
  detect the *window* between a sync and the foreign GC's next re-anchor.
- **D1 must also survive a moving population.** The re-anchor is asynchronous and unannounced: it fired
  at 09:39 today, three and a half hours after a finalize report read the opposite state. **Any single
  sample is stale on arrival.** The double-sample rule is necessary but not sufficient — the oracle
  must report the sample instant alongside the verdict, or it publishes a status where it measured a
  snapshot.

**⇒ The live split right now is executor-vs-everything:** `.plan/execute-script.py` pins `0.1.1331`,
which the foreign GC orphan-marked in the encoding its own 7-day GC parses. Scripts work today; the
fuse is ~7 days. **Repair remains operator-only.**

⚠ **A fourth consumer this spec's survey does not cover:** the *session's own seating*. PLAN-TRUTH-049's
session ran seated on orphan-marked `0.1.1304` while this session is seated on `0.1.1327`. Seating is
fixed at session start, so **a survey run in one session says nothing about another session's seating**
— and neither is visible in the registry, the executor, or the marker set. D1 must either measure it or
state explicitly that it does not.

---

## ⛔⛔⛔ INCIDENT 15, 2026-08-09 — `unmarked == []` REPRODUCED, AND THE PRODUCING ACTION IS NAMED: `marshall-steward upgrade`

**OBSERVED, double-sampled 5 s apart, both samples identical.** Immediately after the operator ran
`/marshall-steward upgrade`:

| consumer | value |
|---|---|
| registry `installPath` | `0.1.1327` — **unmoved by the upgrade** |
| registry `version` | `0.1.1326` — unmoved |
| executor `MARSHALL_VERSION` | `0.1.1331` — unmoved |
| **unmarked dirs** | **`[]` — ALL TEN ARE ORPHAN-MARKED** |

⇒ **Nothing is protected.** The pin, the registry `version`, and the executor's dir are all
GC-scheduled. This is the empty-set state CIS singled out as *"the one an obvious check would miss —
an empty set reads as 'nothing stale' to anyone writing the obvious check."* **Second confirmed
occurrence, and this time the producing action is identified inside the same hour.**

**⭐⭐ THE SATURATION MECHANISM, NOW STATED PRECISELY — D1 MUST ENCODE THIS.** Our marker pass
(`_mark_superseded_version_dirs`) **only ADDS markers; it never CLEARS them**, and it spares exactly
one dir: the current one. The foreign GC had already marked `0.1.1331` at `09:39:03` (epoch-ms). The
upgrade's pass then marked everything except `1331` — which was already marked. **Union = the whole
set.** ⇒ **Saturation is reachable in ONE step whenever the foreign GC has pre-marked the dir our pass
would have spared.** The docstring's *"structurally impossible"* anti-saturation guarantee is refuted a
second time, and the refutation is now constructive rather than observational.

**⭐ THE MARKER-RESET CONFOUND ALSO REPRODUCED, WITH A TIMESTAMP.** `0.1.1240` — the ancient dir that
keeps reappearing — was re-marked at `2026-08-09T10:45:30Z`, **the newest marker in the tree**. Its age
was reset to zero. ⇒ **an age-based oracle over these markers measures time-since-last-sweep, not
time-since-orphaning**, and a dir can be re-marked indefinitely without ever aging out. This is the
`0.1.1240` behaviour recorded twice before, now with the reset instant captured.

⛔ **AND THE UPGRADE WENT GREEN.** `/marshall-steward upgrade` completed over an unrepaired split and
left the registry pin exactly where it was — the standing note that *"all 4 stages go green over an
unrepaired split"* is confirmed again, with the additional finding that the upgrade **actively worsened
the marker state** (it marked the pin) rather than merely failing to improve it.

⇒ **D1's oracle must reject a SIXTH shape and must state a DIRECTION**: it is not enough to detect
`[]`; the detector must distinguish *"the sweep saturated"* from *"nothing has been marked yet"*, and
those are the same observation to any check that only counts unmarked dirs. **Publish the population
size and the newest marker's age alongside the verdict.**

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. ⛔ **It writes NOTHING
under `~/.claude/plugins/`** — the registry is the plugin manager's file (§ Scope). It creates and edits
NO file under `.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message.


---

## ⭐ FOLDED FROM THE 2026-08-09 INBOX DRAIN — 3 messages

**`code-intelligence-substrate-025` (finding).** ⛔⛔ **The oracle failed in BOTH directions within one
hour on one machine.** `-024` gave the false PASS (`unmarked == [pin]` held while the pinned dir was
**8 files stale** vs source). Hours later CIS produced the **false FAIL**: a read returned
`unmarked == [1240, 1326, 1327]` when 1240 and 1327 **were** marked — their markers landed *seconds
after* the sample. ⇒ **A marker survey is a READ-DURING-WRITE.** They told the operator not to launch a
plan, citing a 144-file backward-seat trap **that did not exist**. ⭐ The false fail is the more
dangerous direction because **it triggers action**.

⇒ **TWO oracle additions, not one:**
1. `pin_content == source_content`, reported as *"N of M files match"* — **never a boolean** (from `-024`).
2. **Sample stability**: read at least twice, seconds apart, and require agreement.

⛔⛔ **`indeterminate` MUST be its own outcome, distinct from both `pass` and `fail`.** Collapsing it
reproduces the shared archetype from the opposite side: *could not look* rendered as *looked and found
nothing* — or, worse here, as *looked and found something*.

⛔ **A repair is not a resolution.** The trigger was the routine `generate_executor preflight` on a
`/plan-marshall` invocation — so a repair holds only until the next regeneration, and regeneration
happens in the ordinary course of the slash command. ⇒ **Any detector that runs only at launch is stale
by finalize.** Second independent argument for the mid-run assertion.

⚠ CIS's own caveat, kept: § 1–3 is first-party to them, one machine, one evening, and the `23:04:56`
marker timing is a **single observation**. Re-derive before pinning a test to it.

**`two-producers-...-002` (candidate-lesson).** *The pin-trap detector surveys three consumers and
misses the running session's own seat.* ⭐ **Independent corroboration of the fourth-consumer gap this
orchestrator recorded at the #1125 landing** — and it arrived from the plan, not from us. The session's
seat is fixed at session start and appears in neither the registry, the executor, nor the marker set.
**D1 must either measure it or state explicitly that it does not.**

**`daemon-...-010` (candidate-lesson).** *Every health signal reported the pinned plugin-cache version
while every dispatched leaf ran a superseded one.* ⇒ **The health surface and the execution surface
disagree, and only the health surface is reported.** This is the same one-witness-counted-twice defect
from the consumer side: a green health line is not evidence about what any leaf actually loaded.


---

## ⭐⭐ 2026-08-09, POST-#1132 — A NEW SHAPE, AND IT IS THE LEAST DANGEROUS ARMED ONE YET. THE REPORT'S NUMBERS WERE ALREADY STALE.

Measured first-party, double-sampled 5 s apart, both samples identical, whole population (14 dirs):

| consumer | value |
|---|---|
| registry `installPath` | `0.1.1331` |
| registry `version` | **`0.1.1331` — ⭐ NOW AGREES** |
| executor `MARSHALL_VERSION` | `0.1.1336` |
| **unmarked dirs** | **`[0.1.1331, 0.1.1336]` — the pin AND the executor's, both unmarked** |

**The #1132 report said *"the cache now holds 0.1.1335"*.** Measured: `1335` exists **and is marked**;
the newest dir is `1336` and the executor is at `1336`. ⚠ **A version number in a finalize report is
stale by the time it is read** — third instance this week of exactly that, and the reason every reading
here carries its sample instant.

**Three things changed, and they pull in opposite directions:**

1. ✅ **The `installPath` != `version` drift is REPAIRED.** It stood at 14-of-15 disagreeing; both fields
   now read `0.1.1331`. ⇒ **The field-naming conjunct is satisfied for the first time since it was
   added.** D1 must still *name* its field — a conjunct that happens to hold is not a conjunct that is
   checked — but the live divergence is gone.
2. ⛔ **`executor == installPath` FAILS: `1336 != 1331`.** Skill bodies resolve from `1331` while every
   script runs from `1336` — **five versions apart, spanning #1131, #1132 and #1133.** The trap is armed,
   exactly as the report says.
3. ⭐⭐ **But NEITHER load-bearing dir is orphan-marked.** Both `1331` and `1336` are unmarked, so
   **nothing is on the 7-day GC fuse.** ⇒ This is a **divergence without GC exposure** — materially less
   dangerous than incident 15's `unmarked == []`, where the pin and the executor were both scheduled for
   deletion.

⛔ **THIS IS A DISTINCT CLASSIFICATION AND D1 MUST BE ABLE TO EMIT IT.** The oracle's existing shapes
range over *which* dirs are unmarked; this state needs a **second axis**: *is either load-bearing dir
GC-exposed?* Reporting `1336 != 1331` as a bare `fail` would rank it alongside incident 15, and the two
call for different operator urgency — one is "repair when convenient", the other is "repair before the
fuse burns". ⇒ **Report the divergence AND the exposure, separately.**

⚠ **AND THE TWO-UNMARKED-DIRS CASE IS ITSELF UNRESOLVED.** The standing note is *"the loader follows the
unmarked dir"* — **singular**. With `[1331, 1336]` both unmarked, which does it follow? The `[stale,
pin]` shape is already a recorded failure; this is its mirror, `[pin, newer]`, and **the loader's
behaviour under it is not established.** ⛔ **D1 must not assume it resolves to the pin.** Settle it
against the loader's selection code before relying on either answer.


---

## ⭐ FOLDED FROM THE 2026-08-09 (EVENING) DRAIN — the absorbed-TRUTH-039 argparse surface, with a live instance

**`hook-005` (candidate-lesson).** *`architecture --plan-id` is a **top-level router flag** and is
**rejected when placed after the verb**.*

⭐⭐ **This is the mirror image of a correction already in the operator's standing notes**, and it
completes the pair. The recorded lesson was: *`ci.py` DOES have `--project-dir` — a top-level router
flag consumed before dispatch, not an `add_argument` declaration, which is why an argparse-table grep
reports it absent.* ⇒ **There, the router flag was invisible to a grep and wrongly reported ABSENT.
Here, the router flag is invisible to the VERB and wrongly REJECTED at the call site.**

> **One design — a flag consumed by the router before dispatch — produces a false negative when you
> search for it and a false rejection when you use it.**

⇒ Folds into the absorbed `PLAN-TRUTH-039` argparse-rejection surface this spec now carries.
⛔ **The remedy is not to document the ordering** — it is that a rejection must say *"this flag exists
but belongs before the verb"* rather than *"unrecognised argument"*, which is what sends a caller
looking for a flag that is right there.
