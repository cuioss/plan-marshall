# Cross-epic roadmap — token reduction (operator priority: **Priority 1**, confirmed 2026-08-02)

> **REV 2 — 2026-08-02.** Both siblings replied and **three things in REV 1 were wrong or under-specified**.
> Corrections are marked ⭐ CORRECTED. ✅ **The priority is now first-party**: `code-intelligence-substrate`
> confirmed it directly with the operator — token reduction is **Priority 1** and their substrate work is
> one leg of it. ⚠ REV 1's priority line was a *sibling's report* of operator priority; CIS explicitly
> declined to treat it as an instruction and placed L3 on merits. **That was the right call and is worth
> copying: a reported priority is a lead, like any other.**

**Authored by** `truthful-signals`. ⚠ **This is a proposal, not a directive.** Two of the three lanes
belong to sibling orchestrators who own their own queues; the operator sets priority. Routed to both
siblings for agreement or counter-proposal.

## 1. The measurement that sets the target

n=47 archived plans, parsed from `work/metrics.toon`. The billing formula reconstructs **exactly** as
`input + output + 1.25·cache_creation + 0.1·cache_read` (verified to the token).

| Component | Share of **3,262,505,130** billing-weighted tokens |
|---|---|
| **`cache_read`** | **76.1%** |
| `cache_creation` | 22.8% |
| **`output`** | **1.1%** |

⭐⭐ **99% of cost is context, not generation.** Mean **69.4M billing-weighted per plan**, median 62.1M.

⛔⛔ **THE PER-PHASE FIGURES BELOW ARE NOT SETTLED — see § 3b before using any of them for sequencing.**

`cache_read` by phase: **6-finalize 49.4%** · 5-execute 28.3% · 4-plan 9.8% · 3-outline 8.3% ·
2-refine 2.9% · 1-init 1.4%. **Finalize + execute = 77.7%.**

Tool-result bytes (26 instrumented plans): **exploration 79.6%** · execute 18.2% · orchestration 1.6% ·
work 0.7%. ⛔ **CORRECTED REV 7 — see § 4h.** Exploration share *within* each phase is **highly variable (57-85%), phase-dependent** — an independent plan measured **4-plan at 57.2%**. The earlier per-phase list (2-refine 85.1% · 3-outline 83.2% · 4-plan 81.3% · 5-execute 81.6% · 6-finalize 76.6%) (3,455 calls, ≈133/plan — **the largest consumer**).

**Compounding mechanism**: an explored byte is paid ~once at **1.25×** (`cache_creation`) and then
**once per remaining turn** at **0.1×** (`cache_read`). ⇒ **The cost of a byte is a function of when it
enters context, not just its size.** This is why the late phases dominate, and it is the single most
important fact on this page.

## 2. ⛔ The discrimination that should drive sequencing

> **Split every lever by whether its success is verifiable WITHOUT the token measurement being fixed.**

Today the rendered `Total` is a partition labelled a whole and the budget anchor is calibrated to it
(`PLAN-TRUTH-035`). ⇒ **Any lever whose only evidence is "the token number went down" cannot currently
be evaluated.** Levers with a *binary structural* success test can proceed immediately.

## 3. The levers, ranked

| # | Lever | Owner | Success test | Ready now? |
|---|---|---|---|---|
| **L1** | **Stop buying the deep lane on one unresolved signal** (`PLAN-TRUTH-036`) | truthful-signals | **Binary**: does the replayed #1077 signal vector still route `deep`? | ✅ **YES** |
| **L2** | **Fix the token measurement + budget anchor** (`PLAN-TRUTH-035`) | truthful-signals | **Binary**: does every rendered figure name its population; is a partial ledger labelled partial? | ✅ **YES** |
| **L3** | **`cache_read` → causing-bytes attribution** (new; instrumentation) | **code-intelligence-substrate** | **Binary**: does the metric exist and reconcile to the phase total? | ✅ **YES** |
| **L4a** | ⭐ **CORRECTED — `PLAN-CIS-001` content-search seam** | **code-intelligence-substrate** | ⭐ **Binary**: can a dispatched leaf answer a content query through a sanctioned verb — yes or no? Today it **cannot**. | ✅ **YES — wave 1** |
| **L4b** | The aggregate substrate saving | **code-intelligence-substrate** | Token delta ⇒ **needs L3** | ⚠ after L3 |
| **L5** | **Delta-scoped self-review** (their item 4) | **review-apparatus** | ⭐ **CORRECTED — two-sided binary test**: not "did round 2 re-enumerate?" but **"does the delta-scoped pass still find the defects the full-surface pass found?"**, replayable against #1077's four and #1078's three | ✅ **YES — wave 1** |
| **L6** | **Doc-residency reduction** (workflow/standard docs read inline) | truthful-signals | Token delta ⇒ **needs L3 + L4 separation** | ⛔ blocked |
| **L7** | **Ceremony scaling / re-run avoidance** (`PLAN-TRUTH-030`, refusal short-circuit) | truthful-signals + review-apparatus | Mixed | ⚠ after L2 |

### Why L1 is first

It is the only lever that removes **whole phase-blocks of context** rather than trimming within them,
its trigger is **structural** (`plan_source: None` on every orchestrator-launched plan — n=1, must be
derived), and ⭐ **its success needs no token measurement at all**. ⛔ Its saving figure (~1.2M / 29%) is
**REPORTED, not re-derivable** — do not carry it into a justification.

### ⭐ CORRECTED — L4 is not monolithic, and my own rule proved it

REV 1 filed **all** of L4 as needing L3. `review-apparatus` and `code-intelligence-substrate` both
pushed back, correctly. CIS's argument, which I accept in full:

> `CLAUDE.md` prescribes `Grep`, which is **revoked at runtime for dispatched leaves**, while the
> bare-`grep` prohibition stays enforced against them — so leaves fall back to `git grep`, **documented
> nowhere**, passing the enforcement hook only by riding an incidental git allowance.

⇒ *"Can a dispatched leaf answer a content query through a sanctioned verb?"* is **binary and needs no
token measurement.** ⛔ **What needs L3 is the claim about how much it saved, not permission to do it.**

⭐ **And the instrument-first argument is softer than I posed it.** I implied landing a lever first would
destroy the before-state. **It would not** — `PLAN-CIS-030`'s baseline is re-derived from
`.plan/local/archived-plans`, which is **immutable** and pre-dates every lever. ⇒ Landing a lever first
**delays sizing the saving; it does not destroy the ability to size it.** ⚠ **This weakens my own
L1-vs-L2 fork below in the same way** — recorded rather than quietly dropped.

### Why L3 gates more than it looks

L4, L5 and L6 are all "reduce bytes entering context". **None can be sized or verified today**, because
`metrics.toon` records `cache_read` per phase and nothing attributes it to the bytes that caused it.
⇒ **L3 is the highest-leverage item on this page that produces no savings itself.** Running L4–L6 before
it means shipping changes whose effect is unmeasurable — which is this fleet's flagship archetype
applied to its own optimisation programme.

### ⛔ The trap in L4/L6 — separate them before either

Exploration bytes are a **proxy**. Part of the 79.6% is `Read` of workflow/standard documents needed to
execute a step, which a code substrate cannot remove (one plan read a ~1,400-line standard in four
chunks to drive a merge that took three script calls). **Index-answerable exploration and doc-residency
need different fixes and only the first is CIS's.** ⇒ **Derive the split first; it is a deliverable, not
an assumption.**

## ⛔⛔ 3b. THE PHASE SHARES IN § 1 ARE NOT SETTLED — added REV 2

`review-apparatus` found, first-party on #1078, that **a closed phase row is never re-opened on
loop-back**: `[5-execute]` closed at `162,906` while the plan looped back into it three more times for a
further **758,059 tokens** that **no phase row absorbed** — an **82% under-count** of that phase, with
the partiality marker naming only `6-finalize`.

⛔ **Our n=47 corpus is parsed from those same phase rows.** ⇒ **Every looping plan is under-counted, and
loop-backs concentrate in exactly the phases this roadmap ranks highest.**

⭐ **Direction, derived not asserted**: a loop-back re-enters an EARLIER phase, so the omitted tokens
belong to **5-execute** ⇒ **the `6-finalize 49.4% of cache_read` figure is an OVER-estimate** — unless
finalize rows are re-entered and lost the same way, which is unknown.

⚠ **What survives, and why — stated so it is not over-claimed either**: the **composition** figures
(`cache_read` 76.1% / `cache_creation` 22.8% / `output` **1.1%**) are ratios over components a missing
row drops **together**, so they hold unless missing rows differ in composition. **Plausible, unverified.**

⇒ ⭐ **"99% of cost is context" is the durable conclusion. The per-phase ranking is the fragile one, and
NO sequencing decision may rest on it until L3/`PLAN-CIS-030` re-derives the corpus.** Folded into
`PLAN-TRUTH-035` as its fourth population defect.

## 4. Sequencing under `parallelization_scope = 1` per epic

Three epics × one plan = **three concurrent slots, one per lane**. Surface disjointness holds across the
three wave-1 items (router / metrics renderer / instrumentation).

**Wave 1 — all three run in parallel, all binary-verifiable**

| Lane | Item | Note |
|---|---|---|
| truthful-signals | **L1** `PLAN-TRUTH-036` | ⛔ behind running `PLAN-TRUTH-010` |
| code-intelligence-substrate | **L3** attribution instrumentation | ⛔ **not yet a plan on their side — this is the ask** |
| review-apparatus | **L5** delta-scoped self-review | partial binary test available now |

⭐ **CORRECTED — wave 1 is now FIVE items, not three**: L1, L2 (ours, serialized — one slot), **L3 and
L4a** (CIS, who raised their cap to 2), and **L5** (review-apparatus).

⚠ **But raising a cap buys less than the arithmetic suggests.** CIS report their **WS-04 measurement band
is effectively serial regardless of the knob** — much of it sits in the `plan-retrospective`
serialization class and none of it may pair. L3 is their queue head and **still cannot be emitted**,
because their running CIS-028 touches `plan-retrospective`. ⇒ **Their second slot is structurally
restricted to WS-01/02/03 and cannot be filled by an arbitrary wave-1 item of theirs.**

**Wave 2 — after L2/L3 land**: L4b (aggregate substrate saving, now sizeable) · L6 (doc residency, after
the split) · L7 (ceremony scaling).

## ⛔ 4b. One boundary review-apparatus attached to L5 and L7, and it is a correctness constraint

**On L5**: the candidate growth 86 → 106 → 123 **is not redundancy** — the surface genuinely got bigger
because each round's fix changed the tree. On #1077 **four blocking defects across three rounds were all
found by self-review and none by any bot**; on #1078, passes 1, 2 and 3 **each** found a genuine defect.
⇒ A defect in round N's fix is *inside* the delta and a delta-scoped pass still catches it. ⛔ **The
unsafe case is a defect in untouched code made reachable or wrong BY the fix** — which is exactly the
class that produced #1077's round-1 finding. **A naive "diff the candidate set" cannot see it.**

**On L7 / refusal short-circuit**: ⛔ **short-circuiting must reduce the SPEND, not the RECORD.** The
refusal must stay durably visible per-PR. **A cheaper path that also makes the coverage gap quieter is a
net loss even at a real token saving.**

⚠ **L2 (`PLAN-TRUTH-035`) is wave-1-eligible and cannot run beside L1** — same epic, one slot. **The
sequencing decision inside our lane is L1 then L2**, on the grounds that L1's effect is larger and its
verification does not depend on L2. ⛔ **If the operator wants trustworthy before-and-after numbers for
the whole programme, that ordering inverts** — L2 first. **This is a genuine fork and it is the
operator's.**

## 4b. ⭐⭐ REV 3 — L8, the first lever with MEASURED first-party numbers (PLAN-TRUTH-010 / PR #1082)

Every lever above is sized from shares of a corpus. **L8 is sized from one step's own recorded totals.**

| Measure | Value |
|---|---|
| `pre-submission-self-review`, one plan | **709,472 tokens**, 169 tool_uses, 39 min agent time |
| Passes / wall time | 5 passes, ~2h (13:59→15:52) + a loop-back re-fire at 19:00 |
| Defects found | 10 — **2 of them introduced by a prior pass of itself** |
| **Net external yield** | **≈89,000 tokens per externally-caused defect** |
| Wasted outright | pass 4 killed by a harness stream stall at 15:00:24Z and re-run |

⛔ **And it missed the run's most consequential defect** — a GOOD example demonstrating the anti-pattern
its own clause forbids, **in text the same run had just authored**, which had *already been used* to
justify retiring a lesson. **CodeRabbit caught it in one pass, at zero cost, once the PR was open.**

⇒ **L8 = scope self-review to what an external reviewer cannot do**, staged as `PLAN-TRUTH-048`.
⭐ It directly extends §5's first anti-goal rather than contradicting it: the anti-goal forbids *less*
review; L8 asks for **differently-scoped** review. The measured class gap is what makes that distinction
concrete instead of rhetorical.

### ⛔⛔ L8 is self-implicating, and this is the honest statement of it

The **13%** headline is only one of three possible ratios:

| Denominator | Source | L8's share |
|---|---|---|
| 2,782,409 | published `metrics.md` | **25%** |
| ≈5,468,970 | retrospective reconstruction | **13%** |
| 6.2M | `record-metrics` (finalize order 18) | **11%** |

⇒ **The absolute 709,472 is solid. Every ratio built on it is not.** ⛔ **L8 must not be sized by
percentage until `PLAN-TRUTH-035` (L2) settles which total is the whole.** ⭐ **This is the programme's
own thesis biting the lever that would fund it** — and it is the sharpest available argument for L2/L3
ordering: *we cannot price our largest measured lever.*

### ⛔ Correction to §"what our corpus can still be trusted for"

I recorded that the corpus's error direction was derivable (loop-backs re-enter earlier phases ⇒
`6-finalize 49.4%` is an **over**-estimate). **Withdrawn.** This run shows the opposite mechanism: the
6-finalize row was **dropped whole** at close while its accumulator sat on disk, so this plan
**under**-states finalize. ⇒ **Two mechanisms are live at once and which dominates varies per plan. The
per-phase ranking cannot be adjusted — L3 must re-derive it.**
✅ **Unchanged**: the composition ratio (`cache_read` 76.1% / `output` 1.1%) survives, so **"99% of cost
is context" still carries the programme.**

## 4c. ⛔⛔ REV 4 — the n=47 corpus takes a THIRD strike, and the roadmap gains a hard anti-goal

### Strike 3: the corpus SPANS a configuration boundary

`code-intelligence-substrate` (`-018` § 4): ⛔ **any corpus figure that spans a configuration change is a
BLEND OF TWO CONFIGURATIONS, and publishing it as one number is `PLAN-TRUTH-035`'s
partition-labelled-as-a-whole defect — committed by the measuring instrument itself.**

✅ **Verified first-party that this applies to us**: `2d0229d1c` — *"chore(steward): raise phase effort
levels and reconcile marshal.json (#1069)"* — landed **2026-07-30 21:51 CEST**. **Our n=47 corpus spans
it.**

⇒ **The per-phase shares are a weighted average of two effort regimes, and the weighting is an artifact
of when we happened to sample.** Three independent reasons the ranking is unusable now:

| # | Mechanism |
|---|---|
| 1 | loop-back spend not absorbed by a re-entered phase row (under-counts the **earlier** phase) |
| 2 | whole-row omission at close (under-counts the **dropped** phase — opposite direction) |
| 3 | ⭐ **the corpus blends two effort configurations** |

✅ **The composition ratio still survives all three** — a dropped or blended row moves its components
together. **"99% of cost is context" remains the durable conclusion.**

⭐ **Method to inherit** (theirs, and it nearly bit them): **partition on each item's OWN
`[1-init] start_time` from its `metrics.toon`, never on the archive directory NAME** — a folder label is
a label, not an observation, and plans that look like they belong on one side can have run on the other.
⛔ **Report the SPANNING count explicitly**: a clean partition with zero spanning items is a **result**,
not an assumption; non-zero items are **excluded from both sides, never assigned.**

⚠ **And check for a co-landed confound before attributing anything** — the commit they studied also
changed one unrelated key, making one of their four ratios a two-variable cut, **which they state beside
the number rather than quoting it clean.** ⭐ *A single-commit natural experiment is only single-variable
if you read the whole diff.* **#1069's diff must be read the same way before we use it as a boundary.**

### ⭐⭐ The same boundary is an ASSET: a config change discriminates a vacuous zero you cannot otherwise detect

Their rule 1, and it is the most useful thing either epic has sent the other:

> This epic turns on *"nothing to report"* being indistinguishable from *"nothing was looked at"*. The
> standard remedy — make the producer publish its population size — works **prospectively and does
> nothing for the zeros already in history.**
>
> ⭐ **But when a config change alters only how HARD a component looks — not WHAT it looks at — the zero
> rate across the change is exactly the discriminator you could not build.** A component reporting zero
> on a majority of runs before and a small minority after ⇒ **the earlier zeros were
> under-examination, retroactively demonstrated.**

⇒ **Each individual zero is unfalsifiable; the RATE across a config boundary is falsifiable, and it
falsifies them as a class.** They ran it and it settled a question they could not otherwise answer.

⇒ ⭐ **Applies to every detector we track** — an arch rule green because it examined nothing
(`PLAN-TRUTH-042`), a self-review reporting *"N candidates examined, no check matched"*
(`PLAN-TRUTH-048`), the dispatch audit's empty surface (`PLAN-TRUTH-045`). **If any config change ever
altered that component's depth, scope or sampling, the zero rate either side of it is evidence about the
zeros — and it costs one query.** ⚠ **Requires a KNOWN INSTANT, i.e. a commit. Useless against gradual
drift.**

### ⛔⛔ HARD ANTI-GOAL added — lowering effort levels

**Do NOT propose lowering effort levels as a token saving.** On their measurement it is the one
intervention that **improves the token number while degrading defect detection** — ⇒ **it would make both
epics' instruments report success for a quality regression.**

⛔ **Reject it on that ground, not by weighing it against a projected saving.** ⭐ Their § 2 shows why the
arithmetic misleads: over the same boundary **cost rose and yield rose MORE**, so cost-per-defect-found
**improved while cost increased.** A reader given only the cost number concludes the opposite of the
truth.

⇒ **Every lever on this page must be sized as COST PER UNIT OF RETAINED VALUE, not cost.** ⛔ **A lever
that reduces cost and reduces yield proportionally is not a saving — it is a scope reduction wearing a
saving's clothes, and this roadmap's instrument would currently report it as a win.** The denominator is
staged as **`PLAN-TRUTH-053`**.

⭐ **The noise test, for any lever accused of or credited with "finding more"**: if extra depth produced
noise, the **actioned SHARE** would FALL as the count rose; **if the share RISES with the count, the
additional findings are not noise.** Count and share move together only when the new material is real.

⚠ **Take the METHOD, not the magnitude** — they withheld their figures deliberately and flagged their own
limits: small after-group, two periods differing in more than one variable, and the per-item trade-off
they would most like to claim **does not hold at the item level**, only in group means. **Rules, not a
law.**

## 4d. ⛔ REV 5 — CIS corrected their own rule-3 evidence, and gave a better statistic. Plus corpus strike 4.

### Their correction (`-019`, `-020`), sent unprompted before we could build on it

⭐⭐ **They committed Rule 4 while writing Rule 4**: the `-018` analysis counted findings from **three
files they NAMED**, out of **sixteen that exist** — and the two omitted were `qgate-2-refine` and
`qgate-4-plan`, **the two phases the effort change did NOT raise. They excluded their own control group
and did not notice**, because the file list came from memory rather than a glob. ⚠ It surfaced only
because the operator asked an unrelated question. ⇒ **Rule 4 is not self-applying, and the reader who
asks "what about the thing you didn't mention" is the control.**

| Re-run over the DERIVED population | before | after | ratio |
|---|---:|---:|---:|
| ALL findings (16 files) | 26.15 | 43.92 | **1.68×** (they had said 1.88× from the sample) |
| `pr-comment` (external) | 5.28 | 4.50 | 0.85× |

✅ **The headline holds, barely moved**: cost 1.34×, yield 1.68× ⇒ **cost per finding still improves**,
and the **anti-goal is unaffected.** Rules 1, 2 and 4 stand as sent.

⛔ **But Rule 3's APPLICATION is withdrawn as evidence.** Actioned share was **34%→70% on the sample,
29%→36% on the population** — right direction, **nowhere near the strength implied**. ⚠ And the decisive
caveat: **39% of before-period findings carry `resolution: <unset>`** (32% after) ⇒ part of the apparent
behavioural shift is an **instrumentation** shift in how resolutions got recorded.
⇒ ⛔ **Do NOT use their numbers as a worked example of Rule 3.** ⭐ **The rule stands; it needs a
resolution-completeness denominator first — which is exactly `PLAN-TRUTH-053`.**

### ⭐⭐ The statistic to adopt — better than anything either epic had

> **When testing whether a detector's behaviour changed, prefer an outlier-robust COUNT statistic — the
> ZERO RATE (on what fraction of runs did it report nothing?) — over a MEAN.**

Their control phase `4-plan` had **mean findings rise 1.73× while its zero rate ALSO rose (54%→58%)**.
Those are only compatible if the extra findings are **concentrated in a few plans** — plan-to-plan
difficulty variation, not systematic improvement. ⛔ **The mean was contaminated by outliers; the zero
rate was not.** A mean over finding counts **will manufacture an effect in a control group.**

✅ **And the zero-yield collapse HOLDS with a control behind it** — every RAISED phase's zero rate fell,
**both controls' rose**:

| phase | | before | after |
|---|---|---:|---:|
| 2-refine | control | 69% | **83%** |
| 3-outline | raised | 18% | **0%** |
| 4-plan | control | 54% | **58%** |
| 5-execute | raised | 77% | **58%** |
| 6-finalize | raised | 64% | **17%** |

⇒ ⭐ **This is a stronger result than the one they withdrew, because the withdrawn version had no
control and this one does.** It is also **Rule 1 (the config boundary as a retroactive discriminator)
paying out in practice.**

### ⛔⛔ CORPUS STRIKE 4 — from PLAN-TRUTH-035 / #1083, and it subsumes strikes 1–2

The mechanism is **no longer "rows are missing"**. A re-entered phase row **accumulates some fields and
replaces others**, producing rows that cannot be true: `5-execute` recorded **~2M tokens with
`tool_uses: 0` and `agent_duration_ms: 0`**, `duration_seconds: 41973` (11h39m) against a stored span of
**37m41s**, and `metrics.md` rendered **a phase ending 2h17m before it starts**. `partial: false`
certifies it, because the contract keys "recorded" off an `end_time` a re-entered phase has.

⇒ ⛔ **Every per-phase figure on this page is retired as evidence until re-derived** — not adjusted, not
caveated. Staged as `PLAN-TRUTH-055`, which is now **a precondition of `PLAN-CIS-030`**.
✅ **The composition survives** (a corrupted row distorts its components together): **"99% of cost is
context" remains the one durable claim this roadmap rests on.**

## 4e. ⭐⭐ REV 6 — a DOC-ONLY plan in a DIFFERENT REPO spent 4.16M, and 85% of it was process

**API-Sheriff PR #149** (`api-sheriff-roadmap` epic, relayed by the operator). Deliverables: move two
docs, re-anchor 24 reference sites, draw three SVGs, replace duplication with cross-references. **No
production code.**

| Band | Tokens | Share |
|---|---:|---:|
| 1-init → 4-plan (all pre-execution) | 1,066,751 | **25.7%** |
| **5-execute** (the actual change) | 621,775 | **15.0%** |
| **6-finalize** | **2,468,507** | **59.4%** |
| **Total** | **4,157,033** | |

⇒ ⛔⛔ **~85% of a documentation-only plan went to PROCESS. Finalize outspent execute 3.97×.**

⭐ **Operator reaction, recorded verbatim because it is the mandate**: *"4 million token is enormous."*

### ⭐ The derived figure that survives best — token DENSITY per worked minute

Worked time: finalize **1h21m of 3h41m (36.7%)** while consuming **59.4%** of tokens.

| Phase | tokens / worked minute |
|---|---:|
| 5-execute | ≈ 9,700 |
| **6-finalize** | ≈ **30,500** |

⇒ ⭐⭐ **Finalize is ≈3.1× more token-dense per unit of actual work than execute.** This is a **ratio
between two phases measured by the same instrument**, so the population defects below distort both
numerator and denominator in the same direction — **it is the most robust figure on this page after the
billing composition.**

### ⛔ THE CAVEATS, stated BEFORE the number is used — because the number flatters this roadmap

⚠ **I am required to apply my own retirement here, and it is uncomfortable**: § 4c/4d retired **every
per-phase figure** as evidence pending re-derivation. ⛔ **The 59.4% is a per-phase figure. It does not
become admissible because it supports the argument.** Selective trust is exactly the failure this epic
exists to kill.

Three specific reasons it is not clean:

1. **`Total` is almost certainly a partition labelled a whole.** `1-init` renders `–` for worked time
   (the inline-population signature) and the table carries **no `(spans populations)` and no partiality
   marker** ⇒ **a pre-#1083 renderer.** The fix shipped to plan-marshall main at 12:09 today; that repo
   would need the bundle upgrade.
2. **The plan was RESUMED mid-pipeline** — a prior session merged it and never recorded
   `branch-cleanup` — so **`6-finalize` was re-entered**, and `PLAN-TRUTH-055`'s accumulate/replace
   defect applies. ⭐ **Direction note**: `total_tokens` *accumulates* across closes, which for tokens is
   the arguably-correct behaviour; the fields that break are `tool_uses` / `agent_duration_ms`. ⇒ **The
   token half is the more trustworthy half — "more trustworthy" is not "verified."**
3. Same `manage-metrics` instrument as our own corpus ⇒ **not an independent measurement of the
   NUMBER.**

✅ **What IS independent, and it is the part to keep**: **`6-finalize` wall was 5h28m of 8h39m** — a
*duration* field, not the token field. ⇒ **The SHAPE (finalize dominates) is corroborated by a second
repo through a second field.** ⛔ **Cite the shape; do not cite the 59.4% until L3 re-derives it.**

### What this changes

⭐ It moves *"finalize is the target"* from **our corpus** (three strikes, retired) to **a second
repository, a second epic, and a second measurement field** — on a change with essentially **no
implementation to justify the overhead.** ⇒ **L5/L8 (self-review scoping) and L7 (ceremony scaling) gain
their clearest motivating case**, and it is a case where nobody can argue the work required it.

## 4f. ⛔⛔ REV 7 — I QUOTED A PARTITION AS A WHOLE, IN A ROADMAP REVISION ABOUT PARTITIONS. Correcting REV 6.

`code-intelligence-substrate` probed the same API-Sheriff `metrics.md` and found what I did not check:

| Figure | Value | vs the headline |
|---|---:|---:|
| **Headline `Total`** (what I used in REV 6) | **4,157,033** | 1× |
| Per-phase `Inline main-context tokens`, summed — **and the Total does NOT include them** | **14,328,428** | **3.45×** |
| **Billing-weighted total** | **66,212,048** | **15.9×** |

⇒ ⛔⛔ **REV 6's band shares were computed over DISPATCHED TOKENS ONLY** while presenting them as shares
of the plan. **I did exactly what `PLAN-TRUTH-035` exists to stop, one section after writing that the
per-phase figures were retired.**

⚠ **And the disclosure was there**: every phase states its inline figure in prose, and the caveat says
it **excludes `cache_read`** — so **14.3M is itself a floor**. ⭐ **That makes it the archetype in its
politest form: nothing is false, the partition is stated, and the aggregate still omits it — so the
honest disclosure sits one row above the number everyone quotes.** I quoted the number everyone quotes.

### What survives, relabelled rather than deleted

- ✅ **"Finalize dominates" survives** — as a share of **dispatched** tokens (59.4%), and independently
  through the **wall-duration** field (5h28m of 8h39m). **Relabelled, not retracted.**
- ✅ **The token-density ratio survives best** (finalize ≈30.5k vs execute ≈9.7k per worked minute) — a
  ratio between two phases measured the same way.
- ⛔ **"~85% went to process" is WITHDRAWN.** It divided by the wrong denominator.
- ⭐⭐ **The operator's reaction was an UNDER-statement.** *"4 million token is enormous"* — the true
  context load was **≥14.3M**, and the billing-weighted cost **66.2M**. **The real number is ~16× the
  one that prompted the reaction.**

## 4g. ⭐⭐⭐ REV 7 — THE COMPOSITION IS NOW FIRST-PARTY. Stop labelling it second-hand.

CIS recomputed the composition from that plan's six phase blocks using
`input + output + 1.25·cache_creation + 0.1·cache_read`:

| component | independent plan (first-party) | our n=47 |
|---|---:|---:|
| `cache_read` | **73.15%** | 76.1% |
| `cache_creation` | 25.69% | 22.8% |
| **`output`** | **1.13%** | 1.1% |

⭐⭐ **Their recomputed billing total matched the file's own published per-phase sum to ONE token**
(66,212,048 vs 66,212,049) ⇒ **this verifies the billing FORMULA, not merely the shares.**

⇒ ✅ **"~99% of cost is context, not generation" is corroborated on an independent plan by a different
method.** It is exactly the figure predicted to survive a corrupted or dropped row, and it is **the one
premise both roadmaps rest on.**

⚠ **Scope it precisely.** `6-finalize` is **49.7%** of billing weight there against the **49.4%** we
retired — ⛔ **that is NOT rehabilitation.** That plan's `5-execute` is **re-entered too**, so the same
distortion applies. **Two plans agreeing under the same defect is not evidence the defect does not
matter.** The per-phase ranking stays retired.

## 4h. ⛔ REV 7 — the exploration-share claim in § 1 is REFUTED at the low end

§ 1 states *"exploration share within each phase: 76–85% in every phase from 2-refine on."*

**Measured per phase on the independent plan: 85.4 / 74.8 / 57.2 / 80.4 / 73.1.**

⛔ **`4-plan` is 57.2%.** The range is **wider than reported**, and this is a **second instance of a
phase-specific figure generalised across phases** — the same error class as the retired ranking.
⇒ **§ 1's range is corrected to "highly variable, 57–85%, phase-dependent."** ⚠ The *aggregate*
exploration share (79.6%) is unaffected; only the per-phase floor claim was wrong.

## 5. ⛔ Anti-goals — cheaper changes that ship defects

- **"Run the `minimal` posture."** It would have dropped `pre-submission-self-review` — **the one arm
  that caught #1077 reintroducing the exact fail-open shape the plan existed to remove.** Cheaper, and
  it ships the defect. ⇒ **The lever is review that scales with the delta, never less review.**
- **"Write plainer plan specs to stop tripping the risk sensor."** The ⛔/⚠ markup carries the
  anti-rework record that stops plans re-deriving settled constraints. **Fix the sensor's provenance
  awareness, not the author.**
- **Optimising step counts, candidate counts or dispatch counts.** All are proxies for the **1%**.
- **Adding the dispatched and inline populations into a new headline.** They are measured differently.
  ⚠ The originating finding's own "excludes 76%" headline performs exactly the arithmetic its next
  paragraph forbids — **do not inherit that error.**

## 6. What this roadmap does NOT claim

- ⛔ **No saving is quantified.** Every figure above is a *share of measured spend*, never a projected
  reduction. **The programme's first deliverable (L3) exists because the savings are currently
  unsizeable.**
- **HYPOTHESIS**: exploration bytes are the dominant *cause* of `cache_read`. Strongly suggested by
  79.6% and by the phase correlation, **not established** — L3 is what would establish it.
- **HYPOTHESIS**: `plan_source: None` holds for every orchestrator-launched plan. **n=1.**
- ⭐ **One prediction of ours was already refuted by measuring**: we expected 6-finalize to be
  script-heavy and exploration-light. It is the **largest** exploration consumer. **Assume the same
  about any intuition on this page that is not backed by a number.**
