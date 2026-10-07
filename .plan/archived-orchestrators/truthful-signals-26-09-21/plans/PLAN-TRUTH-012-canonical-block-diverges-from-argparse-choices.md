# PLAN-TRUTH-012: A canonical-invocations block that documents 6 of the 11 values its argparse accepts

> Renamed from **PLAN-107** on 2026-07-30 (see `plan-id-rename-map.md`). ⛔ The DOC half of the
> "11 accepted / 6 documented" item belongs to `code-intelligence-substrate`'s **PLAN-CIS-009**
> (ex-PLAN-13) — do not re-file it here.

epic: truthful-signals
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Staged 2026-07-28 from the PLAN-94 landing (#1040), inbox message 010.

## Objective

⛔ **RE-SCOPED 2026-08-08 — the original motivating instance is REFUTED and this plan no longer
fixes it.** The plan's subject is now the CLASS and its structural guard, not the `manage-metrics`
enum. Read `## ⛔ D1 IS REFUTED` below before scoping anything.

A documented `{a|b|c}` enum in a `## Canonical invocations` block is **not commentary**: the
plugin-doctor `manage-invocation-invalid` analyzer reads that block as **source of truth**, so a
block that diverges from the live argparse `choices` is an **incorrect oracle**, not merely stale
docs. This plan derives the real population of divergent blocks (D2), ships a population-derived
plugin-doctor rule that fails `quality-gate` on divergence (D3), and proves it with controls in both
directions (D4). It also carries the broader **doc-contract-divergence** class — a document
asserting something about a site outside itself with nothing checking the assertion — via cluster
C19 (18 corpus instances) and five first-party instances from PR #1115, folded in below.

**The refuted part, retained only as the record**: the original claim was that `manage-metrics`
SKILL.md listed six of eleven `DISPATCH_TERMINATION_CAUSES` values in two places. Re-verified at
HEAD on 2026-08-08 — the script defines **11** values and **all 11 appear in SKILL.md** (each ≥3
times). **D1 must not be implemented.** ⭐ The refutation strengthens the plan rather than weakening
it: the one instance anybody had actually looked at was fine, which is precisely why the population
sweep (D2) and the mechanical guard (D3) are the deliverables that matter — a class cannot be
retired from the sample that motivated it.

## The divergence — OBSERVED

`record-dispatch-boundary --termination-cause` is documented in the `### record-dispatch-boundary`
operations section **and** the `## Canonical invocations` block. Both list:

```text
{voluntary_checkpoint|task_complete_returned_verbatim|budget_yield|
 harness_cancellation|error|clean_exit_queue_empty}
```

The live argparse accepts **eleven** — the six above plus `step_complete`, `blocked_user_review`,
`blocked_session_restart`, `task_batch_complete`, `agent_returned`.

⛔ **Not theoretical drift: `step_complete` was used SEVEN times in PR #1040's run** — it is the
termination cause on every one of that plan's seven `6-finalize` dispatch-boundary rows.

⚠ **The prose actively reinforces the wrong contract**: *"Required — missing or unrecognised values
are rejected as script errors (there is no implicit fallback)."* A reader takes that as an exhaustive
enum. **An agent following the documented contract and meeting `step_complete` in a live artifact
would classify it as an invented subcommand value under the project's own "Never invent script
subcommands" rule — and would be wrong.**

## ⛔ D1 IS REFUTED — RE-SCOPE BEFORE EMITTING (orchestrator corroboration, 2026-08-07)

**The "six of eleven" divergence no longer exists.** Verified by symbol at `origin/main`
`47ace1585`, by this orchestrator, reading the implementing source directly:

- `manage-metrics/scripts/manage-metrics.py` § `DISPATCH_TERMINATION_CAUSES` — **11 values**.
- `manage-metrics/SKILL.md` — **both** doc sites (the operations section and the `## Canonical
  invocations` block) list **11 values**, not six.

So **D1 is a no-op** and the Objective's OBSERVED claim above is stale prose. It was closed by a
prior commit, not by any plan in this queue.

⛔ **This premise was labelled `OBSERVED` here and `HYPOTHESIS` in its twin.** The same claim was
split across two epics — this spec's own header assigns the doc half to
`code-intelligence-substrate`'s PLAN-CIS-009 — and only the CIS-009 copy carried the label plus a
named confirm/refute artifact. That label is why the CIS-009 run caught the refutation on contact
and did not rewrite a correct file to match a dead premise. **A claim copied into a second plan does
not inherit the first plan's verification**, and an inherited `OBSERVED` is the more dangerous half.

**What is NOT refuted:** D2 onward — deriving the population and adding the structural guard that
retires the *class*. The CIS-009 run's sweep supports that half: a large `choices=` population, and
**two live drifts of this exact class**, both missing `arch-constraint`:

- `manage-findings/SKILL.md` — 12 documented vs `FINDING_TYPES` 14
- `manage-lessons/SKILL.md` — 3 documented vs `LESSON_CATEGORIES` 4

⚠ Those two are **the CIS-009 run's finding, spot-verified by that run, not by this orchestrator** —
leads to confirm at the named symbols, not established facts. The exact swept population is owed
with them; the figure reported was approximate and cannot support a completeness claim.

**Re-scope required before this spec is emitted**: drop D1, re-derive the population, and take the
class-retirement half as the plan. Per
[`orchestrate.md`](../../../../marketplace/bundles/plan-marshall/skills/marshall-orchestrator/workflow/orchestrate.md)
§ Step 4, a refuted clause that has not been re-scoped fails the Prep-ready test, so this row is
**not emittable as written**.

## Deliverables

⛔ D1 below is retained only as the record of what was refuted — see the section above. Do not
implement it.

1. **D1 — fix the instance.** Add the five missing values to **both** the operations section and the
   canonical block, each with a one-line meaning. The existing entries model this well —
   `clean_exit_queue_empty` carries its `loop-exit-guard` precondition inline.
2. **D2 — GATE (mutates nothing): derive the population.** ⛔ **`manage-metrics` is the site one run
   happened to find — it is a SAMPLE, not an enumeration.** Compare every documented `{a|b|c}` enum in
   every `manage-*` canonical block against its live argparse `choices` and report the divergent set.
   Report the divergent count **separately** from the number of blocks examined.
3. **D3 — the structural guard.** A plugin-doctor rule failing `quality-gate` when a documented enum
   in a canonical block diverges from the live argparse `choices`. The comparison is mechanical and
   the data is already introspectable — **the same class of deterministic check the
   `ARGUMENT_NAMING_*` cluster already performs for flag names.** ⚠ The rule must be
   **population-derived** from the script inventory, not a hardcoded list of scripts to check.
4. **D4 — tests, each verified to FAIL pre-fix.** (a) The guard flags a block with a deliberately
   truncated enum. (b) The guard passes on a correct block. (c) The guard's population is non-empty
   and contains `manage-metrics` — **the positive-population assertion**, without which a glob that
   matches nothing looks identical to one that matches everything correct.

## Claim Labels

- OBSERVED: the six documented values in both locations; the eleven argparse values; the seven
  `step_complete` uses in PR #1040.
- OBSERVED: the plugin-doctor `manage-invocation-invalid` analyzer reads the canonical block as
  source-of-truth (stated in `marshall-orchestrator/SKILL.md` § Canonical invocations and mirrored
  across bundles).
- HYPOTHESIS: other `manage-*` blocks carry the same divergence — confirm/refute at D2's sweep
  (verify-at-outline). **If D2 finds `manage-metrics` is the only instance, D3 is still in scope** —
  the guard's value is preventing recurrence, not the count it finds today.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-metrics/SKILL.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-metrics/scripts/manage-metrics.py` (read-only, the argparse oracle)
- HYPOTHESIS: `marketplace/bundles/pm-plugin-development/skills/plugin-doctor/**` — the new analyzer
  (verify-at-outline)
- HYPOTHESIS: additional `manage-*` SKILL.md files D2 surfaces (verify-at-outline)

## Dependencies and Sequencing

- Depends on: none
- Overlaps with: ⚠ **PLAN-TRUTH-002 and PLAN-TRUTH-003 both add plugin-doctor detectors**, and PLAN-TRUTH-004's D1(c) may
  pick a doctor rule. ⛔ **Sequence with whichever of those is in flight — same analyzer surface.**
  PLAN-TRUTH-009 (`surface-every-knob-in-marshal-json`) is the same *documentation-completeness* class but a
  **different bundle** (`manage-config`), so it is a parallel slot: **disjoint — do not merge.**
- Adjacent to: PLAN-64 touches `manage-metrics`' *callers*, not its SKILL.md. ⚠ Re-check before pairing.

## Context — the density observation

Filed alongside a report-only observation from the same run: **seven argparse rejections across six
distinct components** (`manage-status phase-handshake`, `manage-findings --resolution-detail`,
`manage-execution-manifest compose`, `git-workflow commit`, `ci --plan-id`, `manage-files --subdir`,
`git-workflow switch-and-pull` missing `--base`). No single component is the culprit so it is not
filed separately — **but an incomplete canonical block is one of the mechanisms that produces that
density**, and D3's guard would reduce it.

The index-completeness rule already recorded in `agent-behavior-rules.md` — *"a newly-authored
index/summary table must enumerate every member of the set it indexes"* — already states the
obligation. This is a live violation of it **in a canonical block, the highest-stakes place for it to
occur.**

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/truthful-signals/plans/PLAN-TRUTH-012-canonical-block-diverges-from-argparse-choices.md"
```

## ⛔ RETRACTED 2026-07-30 — the `--enabled-bots` fold was MISATTRIBUTED. Do not scope a deliverable at it.

**This section is retained as a correction, not as work.** The orchestrator folded the `#1064`
`review_completeness --enabled-bots` argparse rejection in here as a canonical-block-vs-argparse
divergence. `review-apparatus` refuted it (`review-apparatus-006`) and the refutation was
**independently re-verified here**:

- OBSERVED — `grep -rn "enabled-bots\|enabled_bots" marketplace/bundles/` returns **no `--enabled-bots`
  CLI flag anywhere**. Every hit is the **retired `enabled_bots` CONFIG KNOB** in migration prose
  (`manage-config/standards/data-model.md`, `marshall-steward/SKILL.md`, `upgrade.py:239`
  `_LEGACY_BOT_LIST_KEY`). **No canonical block advertises the flag**, so there is nothing here for a
  canonical-block-vs-argparse rule to catch.
- ⇒ The two subagents did **not** hit a doc/script contract defect in the source. They **read a stale
  plugin cache** and invoked a retired flag against the current script.

⛔ **A deliverable in THIS plan aimed at that incident would find nothing to fix.** Re-aimed to
**PLAN-TRUTH-008**, which already owns the doc-vs-script version-skew axis — that is the archetype, and
its fix is cache-version resolution, not a doc edit.

⚠ **Guard against the inverse error too.** The stale-cache archetype invalidates an *artifact*; it must
never *acquit a defect*. Here it acquits nothing real: the flag's absence from source was verified
directly, not inferred from the cache explanation. The retraction rests on the grep, not on the story.

⚠ **A second, DISTINCT rejection exists in the same script and is NOT ours** — `--participated-bots`
supplied with no value (the zero-participation case) exits 2 because the documented invocation
interpolates it unquoted. `review-apparatus` staged it as their `PLAN-PR-014`. ⛔ **Both rejections log as
`failure_kind=argparse_rejection`, so they are indistinguishable in the record** — any attribution of an
incident to one rather than the other from a log signature alone is a HYPOTHESIS. This plan's population
derivation must not treat that signature as identifying.

## ~~FOLDED 2026-07-30 — a live instance from #1064~~ (superseded by the retraction above)

Reported by the operator at the #1064 landing and folded here because it is precisely this plan's
subject: **a canonical invocation block naming flags the script's argparse does not accept.**

- OBSERVED — the pre-merge review barrier's evidence script `review_completeness` was invoked with the
  documented **`--enabled-bots`** form and **exited 2 (argparse rejection)**. The live surface is
  **`--required-bots` / `--optional-bots`**; re-running with those succeeded.
- OBSERVED — the rejection landed **~60 s before the gate flipped green**.
- ⭐ **TWO SUBAGENTS HIT THIS INDEPENDENTLY.** That converts it from an incident into a population
  signal, and it is the strongest available argument for the detector this plan builds: a human or agent
  following the doc verbatim fails, and the failure mode is an exit code rather than a readable message.

⚠ **Scope discipline — do NOT inflate this into a false-green claim.** The operator confirms the green
verdict is **real** (the re-run with the correct surface genuinely passed). This is a **doc/script
divergence**, not a laundered gate. The adjacent finding — that a retried step leaves no attempt
identity, so the barrier's record cannot show the first rejection — is a **separate** Open Defect in
`epic.md` and belongs to `phase-6-finalize`, not here. Two findings, one incident: resolve them as a set
but do not merge them.

⇒ **Detector consequence:** `review_completeness` must be in this plan's population. Its owning skill's
canonical block is the divergent source-of-truth, which is exactly what the plugin-doctor
`manage-invocation-invalid` rule reads — so this instance should be a test case, not just a fix.

## ⭐ FOLDED 2026-07-30 — two instances that ARE this plan's archetype (unlike the retracted one)

1. **`plan-less-pr-...-006`** (PLAN-115, #1065): *"Widening an argument surface leaves the narrow form
   pinned in every doc that documented it."* ⭐ **This is the general statement of this plan's defect** and
   it names the mechanism: the divergence is not authored, it is **left behind** when a surface widens —
   so the population is *"every doc that documented the old form"*, which a per-skill sweep will miss.
   ⇒ D2's population derivation should key on **surface-change events**, not on a static doc scan.
2. **`ci pr view --help` self-contradicts** — orchestrator-observed 2026-07-30: the help text documents
   `--head` as *"an alternative to `--pr-number`"*, but **`--pr-number` is absent from the usage line and
   the parser rejects it** (`error: unrecognized arguments: --pr-number 1065`). A canonical surface whose
   **own help advertises a flag it refuses**.
   ⛔ **Its consequence is worse than a failed CLI call, and was found independently by a sibling epic**
   (`code-intelligence-substrate-010` §2): a monitor was armed with `pr view --pr-number`, **could never
   match**, and reported an ordinary `[Monitor timed out]` while the awaited state had already occurred —
   costing six manual `retry` turns. ⇒ **A doc/argparse divergence on a surface something POLLS is not a
   usability bug; it is a structurally blind watcher.** Rank this instance above a plain doc mismatch.

⚠ **Contrast with the retraction above:** the `--enabled-bots` item was misattributed here because no
canonical block advertised it. **These two do** — `ci pr view`'s own `--help` is the advertising surface,
and #1065's widened arguments left real docs pinned to the narrow form. The distinction to carry into D1:
**this plan's population is "a surface that ADVERTISES a form it does not accept", not "an invocation that
failed".**

## ⭐ FOLDED 2026-08-02 — SECOND SIGHTING of the producerless-contract-row shape, plus a new sibling plan

**From `review-apparatus-012` item 12** (PR #1077 finalize), delegated to us:

> A **declared-but-never-emitted `display_detail`** is a producerless contract row. Declaring and
> emitting are two edits in two places; **nothing fails when the second is skipped** — the renderer
> degrades to `<missing display_detail>` and forces a `[FAILED]` headline, **so the step reports broken
> for a reason unrelated to whether it worked.**

⇒ Second sighting of the `dispatch_boundaries` producerless-row shape already recorded on this plan.
⛔ **Recurrence, not a new item.** ⭐ The new detail worth carrying: the failure mode is **not silence
but a MISLEADING failure** — a missing producer manufactures a false negative about the step's actual
work.

## ⚠ ADJACENCY 2026-08-02 — `PLAN-TRUTH-040` is the same archetype at the dispatch layer

`PLAN-TRUTH-040` (staged) covers a step that **declares** `candidates` as a required prompt-body field
while the generic finalize dispatch template **has no slot to carry it** — declaring and satisfying as
two unlinked edits, exactly this plan's shape.

⛔ **Decide at outline whether 012 ABSORBS 040 or they stay separate.** Argument for absorbing: one
enforcement mechanism ("a declaration without a producer is a build error") could close both. Argument
against: 012's surface is `manage-metrics` SKILL.md + `plugin-doctor`, 040's is `phase-6-finalize` — a
merged plan spans two bundles. ⭐ **#1076's `records_facts` frontmatter with its no-orphan-declaration /
no-undeclared-recordboth-direction guards is the reference implementation for either choice.**

## ⭐ FOLDED 2026-08-03 — the consumer-sweep archetype recurred TWICE inside one plan

From `PLAN-TRUTH-010` (`-007`), both first-party in one run:

1. **The outline declared 1 consumer of a changed signature; there were 2.** The declared count was
   *an artefact of how far the author looked, presented as the size of the set.*
2. **A roster's population was a strict subset of its own predicate's domain** — the detector guarded a
   set smaller than the set it claimed to guard, so members outside the roster were unguarded **and the
   guard still reported clean.**

⇒ **Two more instances of the standing archetype**: *a list of call sites produced by looking is a
SAMPLE, not an enumeration.* ⭐ **They were caught only because a later pass re-derived the population
instead of trusting the earlier count** — a single-pass plan would have shipped a missed live consumer
with a confident *"1 consumer updated"* attached.

**Carried here because this plan's enforcement mechanism is the natural home**: a declared count and a
derived count are the same declaration-without-a-producer shape as `display_detail`.

⛔ **This directly sizes the epic follow-up named by that landing** — enforce a single authoritative
`_TEST_ROOTS` (thread the root set through `resolve_test_scope`). **That work touches exactly this
signature**, so it must be sized against the consumer-sweep hazard, **never against a hand-counted
consumer list**. That run hit the hazard **twice on that very signature**.

⭐ **The standing remedies, restated so they are not re-derived**: never state a consumer count produced
by looking — derive it from the population via a structured architecture query and **state the query**,
so the claim is reproducible; every set-guarding detector is **population-derived** (copy
`test/_shared/_dispatch_roster.py`); and **when a fix WIDENS the population, re-check the detector's
anchor** — a population-derived detector built against the old, narrower domain is silently wrong
against the new one.

## ⭐ FOLDED 2026-08-03 — a guard scoped to ONE document enforcing a directive that spans FIVE (`-005`)

`manage-metrics/SKILL.md` carried an operative directive — *a value added to
`DISPATCH_TERMINATION_CAUSES` must be added to all three sites in the same change* — **citing
`test_manage_metrics.py` as the enforcement.** Two facts made the citation false:

1. **The real mirror set is FIVE, not three.** Two further live enumerations exist outside `SKILL.md`:
   the `termination_cause` enum restated in `standards/data-format.md` (**inside the section that
   declares itself the single source of truth**), and the hand-listed values in the
   `record-dispatch-boundary` argparse `description=` string. ⚠ Its `choices=` **is** derived from the
   tuple and is therefore **not** a mirror — the distinction matters for the population.
2. **The guard is narrower than the directive.** `_parse_termination_cause_sites` reads `_SKILL_MD`
   **only**, as its own docstring states.

⇒ All five happened to agree, so there was **no live drift** — **the defect is forward-looking and fully
determined**: the next enum addition follows the three-site directive, leaves two mirrors stale, **and
the contract test still passes green.**

### ⛔ How it was dispositioned, and why that is only half a fix

**Documentation-only.** `SKILL.md:410` now says the test reads *"this document only, so those three sites
are the whole GUARDED population — not the whole population … nothing fails if you miss one."*

⭐ **That is the right first move and it is on-theme** — a guard that cannot see a population should say
so rather than let its green read as coverage. ⛔ **But honesty is not enforcement.** The two mirrors
remain unguarded and **the residue is live in merged `main`**; the note's own closing clause concedes the
guard cannot even *bound* the population it fails to cover.

> ⭐⭐ **Scope the guard to the directive, or scope the directive to the guard — never state a directive
> the guard cannot see.**

⇒ **This plan owns the enforcement half.** ⚠ The declared/derived distinction (`choices=` derived vs
`description=` hand-listed) is exactly this plan's shape and should be its worked example.

## FOLDED IN 2026-08-08 — cluster C19 plus five fresh doc-contract-divergence instances

⛔ **Read the spec's existing block first: this plan's D1 premise is REFUTED and annotated. The
fold below attaches to its SURVIVING class-retirement half, not to the refuted D1.**

**Cluster C19** (`lessons-handling-26-08-08-01-011`, **18 corpus instances**, doc-contract
divergence) is routed here as its home — including its sub-group B, *"two documents disagree and
nothing cross-checks them"*, which is the class this plan's surviving half exists to retire.
⚠ The 18 instances are the router's count over the lessons corpus and were **not re-derived
here**; treat as a floor and a sample, not an enumeration.

**Five fresh first-party instances from PR #1115** (each a distinct shape, dispositioned per
instance rather than as a bundle):

- `-010` — a central standard claimed **N sibling skills bind an obligation when only 1 did**.
  ⭐ The sharpest of the five: it is a *count* in normative prose, and a count in a premise is a
  sample. This is the same defect the plan is named for, one level up — the doc asserting the
  state of its own consumers.
- `-011` — an **ADR cited as "already accepted" while its recorded Status is `Proposed`**. A
  citation that upgrades a document's status by asserting it.
- `-012` — a skill body gained an **authoring-time `MUST` while its activation description still
  scoped it to running/interactive use** ⇒ the obligation is unreachable for the audience it
  binds. Description-vs-body divergence.
- `-017` — a standard **described a suppression behaviour without naming where the suppression is
  enforced**, so no reader can verify it and no test can pin it.
- `-018` — a **thin-pointer skill violated its own no-duplication prohibition three lines after
  stating it.**

⭐ **What the five have in common is the deliverable**: in every case the document asserts
something about a *site outside itself* — a sibling's binding, an ADR's status, an enforcement
location, its own duplication — and nothing checks the assertion. **A cross-document claim needs
a named, checkable referent, exactly as a `HYPOTHESIS` does.** That is the retirement rule this
plan should ship, and it generalises past argparse.

## ⭐⭐ FOLDED IN 2026-08-09 — the 2026-07-04 review's doc-contract cluster, RE-VERIFIED AT HEAD

`doc/review-26-07-04.md` is being retired. Its doc-vs-reality findings are **exactly this plan's
class**: a document asserting something about a site outside itself, with nothing checking the
assertion. **Every item below was re-checked at HEAD; the fixed ones are listed so nobody re-files them.**

### Still valid — README vs `plugin.json` (machine-checkable, and the checker is D3's job)

| Finding | Re-verified at HEAD |
|---|---|
| **[D1]** `pm-dev-frontend` README says **6 skills**, `plugin.json` registers **8** | ⛔ still wrong — and the two missing are `arch-gate-js` + **`javascript-security`**, a security skill left undocumented |
| **[D2]** `pm-dev-python` README says **4**, registers **6** | ⛔ still wrong — missing `arch-gate-python` + **`python-security`** |
| **[D3]** `pm-plugin-development` README enumerates 13, registers **16** | ⛔ still wrong — missing `ext-self-review-plan-marshall`, **`plugin-security`**, `recipe-fix-argparse-rejection` |
| **[D4]** `pm-dev-oci` README says **3**, registers **4** | ⛔ still wrong — omits `plan-marshall-plugin` |
| **[D5]** *"not registered in plugin.json"* is false | ⛔ still present in **2 of 3** READMEs (`pm-dev-frontend`, `pm-dev-python`); `pm-plugin-development` no longer says it |
| **[D6]** `pm-dev-java-cui` README's `skills:` example names `pm-dev-java-cui:cui-logging-enforce` | ⛔ still present — **no such skill exists** (it is `recipe-cui-logging-enforce`); copying the example fails to load |

⭐⭐ **THREE OF THESE HIDE A SECURITY SKILL.** That is the elevation: a README undercount is cosmetic
until the omitted skill is the one a reader would go looking for. ⭐ **And every one is mechanically
checkable** — README count vs `plugin.json` count is a comparison a rule can make, which is precisely
D3's population-derived guard extended one surface outward.

### Still valid — cross-skill and governance references

- **[S2]** `recipe-cui-logging-enforce`'s Fix Sequence references bare
  `standards/logging-maintenance-reference.md` / `standards/logging-standards.md` — ✅ **re-verified:
  2 unqualified refs, and the skill has NO `standards/` dir of its own.** They belong to
  `pm-dev-java-cui:cui-logging`, which the same file qualifies correctly elsewhere.
- **[S3]** `ext-outline-workflow/standards/` still holds all four superseded per-type
  `change-{bug_fix,enhancement,feature,tech_debt}.md` beside the consolidated `change-types.md` —
  ✅ **re-verified: 5 files present**, the four referenced nowhere. *Where a copy exists, delete the copy.*
- **[S4]** `tools-script-executor/standards/script-organisation.md` and
  `manage-plan-documents/standards/adding-document-types.md` — ✅ both still exist and are referenced
  by no SKILL.md. Wire in or remove.
- **[C-G1]** `AGENTS.md` instructs a `Co-Authored-By: opencode/{model}` trailer that contradicts the
  repo convention — ✅ **re-verified present at HEAD.**
- **[C-G2]** `AGENTS.md` and `CLAUDE.md` list **different** forbidden Bash constructs for the same
  one-command rule (`|` in one, `&`/newlines in the other). Two authoritative sources, one rule.

### ✅ FIXED SINCE THE REVIEW — recorded so they are not re-filed

- **[S1]** `phase-6-finalize` SKILL.md mapping four steps to `standards/…` paths that live under
  `workflow/` — **now clean: 0 occurrences at HEAD.**
- **[C-G3]** CLAUDE.md's *"structurally unmergeable"* branch-prefix rationale — **the phrase is gone**;
  the current text correctly describes the `pull_request` base-branch trigger.

## Write-Boundary

Repository source + tests only; NO `.plan/local/orchestrator/` writes other than this plan's own
`inbox/{sender}-{seq}` message. See orchestration-model.md § Ledger Write-Boundary.
