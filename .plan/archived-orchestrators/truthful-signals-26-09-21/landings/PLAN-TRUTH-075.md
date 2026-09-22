# Landing Analysis: PLAN-TRUTH-075 — cloud-lane build gate reads one field short

epic: truthful-signals
workstream: WS-01
pr: #1336 — merged as `77c9dc70a`

Drained from the epic inbox (10 messages, `-001`…`-010`) on 2026-08-24. This is a **full ship** — a
tracked plan of this epic — so it carries a queue transition and this record, unlike the #1330 / #1332 /
#1337 observations.

## Ground-Truth Corroboration

| Claim | Verdict | Evidence |
|---|---|---|
| Merged as `77c9dc70a` via the merge queue, squash | corroborated | `git log origin/main` — `77c9dc70a chore(cloud-plan-lane): guard the build-gate report against trigger-table drift (#1336)`; `ci pr view --pr-number 1336` → `state: merged` |
| 3 files | corroborated | `git show --stat` — 3 files, **745+/2−** |
| The guard is 10 tests | corroborated | `test/pm-plugin-development/cloud-plan-lane/test_build_gate_lockstep.py`, **740 lines added** |
| Plan finished, worktree removed | corroborated | absent from `manage-status list` (7 live → 6) |
| **The landed commit has ONE parent** | **corroborated** | `git log --format="%h %p" 77c9dc70a` → `77c9dc70a 2cd1a19c8`. ⭐ This is first-party proof for candidate-lesson `-004`: the footprint resolver's merge-commit tier can **never** fire in this repository, not "rarely" |
| Row reconciled by the orchestrator | ✅ yes | the row was still `running` with empty result fields when this drain began — nothing pre-stamped it |

## Deliverable Fidelity vs Spec

**Four staged, one implemented, three closed on re-verification with evidence.** That is the headline,
and it is a success of the mechanism rather than a scoping failure.

| Deliverable | Verdict |
|---|---|
| D0 — is the wrapper's green-with-errors a live false-green? | **closed by CODE READ.** `_build_shared.py::cmd_run_common` + `_build_result.py`: `errors[]` is populated at exactly one call site, reached only after `error_result()` has unconditionally set `status: error`. ⇒ a defence-in-depth gap, **not** a live false-green. The spec named this its discriminator gate; it is answered |
| D1 — both gate sites must require an empty `errors[]` | **already satisfied** at both cited sites. Line numbers had moved; content requirement present. Read with D0: correct **and currently unreachable** |
| D2 — merge-queue / stale-base report vocabulary | **already shipped** by `2cbcb1f30` / PR #1299 |
| D3 — the build-gate lockstep guard | **shipped** — the report template now quotes Step 5's normative phrase `"no buildable footprint, build skipped"`; Step 5's trigger table was not edited |

### ⭐⭐ The diagnosis the plan corrected about itself: queue latency, not stale ingest

`solution_outline.md` and BOTH phase summaries state the chronology **backwards**, claiming #1299
predates the plan's staging. Finding `74f30d` corrects it with `git show -s --date=short`: the plan was
staged **2026-08-09**, #1299 landed **2026-08-18** (nine days AFTER staging), execution was
**2026-08-23**. The spec was accurate the day it was written.

⛔ **The two diagnoses have OPPOSITE remedies and must not be conflated.** *Stale ingest* argues for
better sourcing at staging time — and would have been wrong here, since nothing about staging could
have caught it. *Queue latency* argues for **re-verification at execution start**, which is what
actually happened and is why three deliverables closed without touching a file two other plans also
claim.

⚠ **The correction never reached the artifact it corrects** — see Open Defect `D-075-f`.

### ⭐ The defect cascade: a guard against n−1-of-n reproduced n−1-of-n four times inside itself

| Round | Found by | Defect | Fix |
|---|---|---|---|
| 1 | self-review r1 | glob pinned at 2 of 4 sites; docstring said "twice" | `9b0558334` |
| 2 | self-review r2 | population check was non-emptiness → a 2→1 shrink passes silently | `e5cadb886` |
| 3 | `finalize-step-simplify` (outside its remit) | skip row bound POSITIONALLY while the docstring claimed semantic | `cd5135b57` |
| 4 | sourcery on the PR | the REPORT surface still bound positionally — same defect, other surface | `f41d4cdaf` |
| 5 | sourcery on the PR | the cardinality floor cannot detect a marker SWAP | accepted, rationale recorded |

⭐ **Round 4 is the sharpest, and the lesson is in the failed first attempt**: the first fix
(block-wide uniqueness) was **wrong**, and the tests caught it — the block legitimately quotes a second
phrase in its stale-base paragraph, so uniqueness fails on a *correct* document. The landed fix scopes
the binding to the verdict sentence's paragraph. Guard grew 4 → 10 tests; every fix carries a matched
negative control, two of them red against a first-match binding.

⛔ **This is the vacuous-guard archetype (n≥6) recurring INSIDE the fix for it, for at least the second
recorded time** (PLAN-TRUTH-055 did the same). The epic's standing rule — *a fix for a vacuous guard is
itself a prime site for one* — now has two independent confirmations and should be treated as expected
behaviour, not as a surprise.

## Cost — recorded without being explained away

**3.04M tokens dispatched · 71.4M billing-weighted · 13h2m wall · 2h30m worked · 10h32m idle**, for a
3-file landing. `6-finalize` alone was **45.3M billing (63%)** across 342 tool uses; 80% of wall time
was idle. The plan-retrospective judged this **past the `error` anchor (1.6M) for
`single_module+feature`** and called the verdict robust because the total is a floor.

⚠ The plan explicitly declined to settle whether the spend was worth it, calling that "a judgement for
the orchestrator, not for this plan to settle in its own favour." **That restraint is correct and is
recorded as good practice.** The orchestrator's judgement: the spend bought five rounds of defect-finding
on a 3-file diff plus **five reproduced infrastructure defects** (`-008`) that no cheaper pass would
have surfaced — but that is a defence of *this* run's yield, not of the cadence. The finalize
concentration is forwarded to `code-intelligence-substrate`, which owns cost accounting.

⛔ **Do NOT read this as support for collapsing the finalize band.** R22 stands: the amplification, not
the band size, is the cost driver, and `-097` DB lands before any band change is priced.

## Residue drained from the sibling messages

Ten messages, every one dispositioned. Nothing in this landing is left in the inbox.

| Message | Kind | Disposition |
|---|---|---|
| `-001` billing unreadable by the retrospective | candidate-lesson | **folded** → `-097` DD (R18 already owned it); its option (c) is a genuine addition |
| `-002` re-fire emits `Completed` without `Executing` | candidate-lesson | **folded** → `-097` F4 (new) |
| `-003` `channel_completeness` grades itself on an inflated denominator | candidate-lesson | **folded** → `-097` F3 (new) |
| `-004` footprint resolver has no squash-surviving tier | candidate-lesson | **folded** → `-098` Arm 1, with the single-parent proof |
| `-005` build oracle reports 0 builds against 52 logged calls | candidate-lesson | **folded** → `-088` DA (RUNNING); its hypothesis is **already refuted** by R5 |
| `-006` dispatch-boundary coverage + unfed context columns | candidate-lesson | **folded** → `-097` F2 (second independent measurement) |
| `-007` re-ground a staged spec at execution start | candidate-lesson | **standing rule** + Open Defect `D-075-f` |
| `-008` five reproduced infrastructure defects | finding | **split**: 1→`-087` DA · 2,3→new `-105` · 4→forwarded · 5→`-097` DE |
| `-009` the three no-code closures, with evidence | finding | **observed** — it is this record's evidence base |
| `-010` the landing itself | landing | **this record** |

⛔ **`-010` carried NO `landing-facts` block** — `landing-check` returned `complete: false` with all
**eight** required keys missing, including `schema`. This is the pre-fix prose-only shape. Every figure
in this record was therefore read out of prose or re-derived first-party, not drained. Recorded as
`D-075-g`.

## Sequencing consequence for a staged sibling

**`PLAN-TRUTH-092`** (`cloud-plan-lane-contract-and-run-report-accuracy`, staged) declares
`.claude/skills/cloud-plan-lane/SKILL.md` in its Expected Surface — a different defect (merge gate, not
build gate). It must be re-grounded against this landing: the file moved, and **the new guard will fail
if `-092` edits the Step 5 trigger table or the report `## Build gate` block without keeping them in
lockstep.** ⭐ That is the guard working as intended, not an obstacle — but `-092`'s author must know
before starting. Folded into `-092`'s spec.
