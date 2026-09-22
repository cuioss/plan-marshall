# PLAN-PR-006: A canned no-op comment is indistinguishable from a review

epic: review-apparatus
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-marshall-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

## Provenance — `truthful-signals` PLAN-116 Defect D, split out on its own advice

PLAN-116 was released to this epic on 2026-07-30 and split. Defect D is here as its own plan
**because that spec asked for exactly this**: "a per-bot evidence marker is a **different observable**
from the three D1 already enumerates, and it may warrant its own plan rather than riding here — split
it out if D1's derivation shows it widens the change materially." The split is taken up-front on the
grounds that D asks a different question from A/C/E: those ask *did the bot participate*, D asks
*did the bot actually review*. Sibling slices: PLAN-PR-001 (A), PLAN-PR-002 (B), PLAN-PR-005 (C+E),
PLAN-PR-007 (F).

## ⛔ RE-AIMED 2026-07-30 — the original premise is REFUTED by operator ruling

**This plan was staged as "a canned no-op comment is indistinguishable from a review", treating
PR-Agent's three-line informational Guide as the defect. That framing is WRONG and must not be
implemented.** Operator ruling: **"No findings" IS a result.** A Guide reporting no issues satisfies
the must-always-provide-a-result rule and is **not a defect on its own**. A detector that flags the
canned Guide as non-participation would flag a legitimate outcome.

**The real defect is COMPARATIVE**, and it is the rule that replaces the old objective below.

## Objective

PR-Agent must always provide a result, and a missing result is a bug — but **producing structurally
fewer findings than the other reviewers on the same diff is a bug in itself**, even though each
individual "no findings" result is legitimate. Detect that deficit.

⚠ **The deficit is only assessable against a baseline.** When every other reviewer was rate-limited,
nothing reviewed the diff besides PR-Agent, and the run is evidence **neither way** — it must NOT be
scored as a deficit, and its clean verdict must NOT be read as PR-Agent performing well.

## Live evidence, gathered 2026-07-30 across the five owed post-merge revisits

| PR | CodeRabbit | Sourcery | PR-Agent | Verdict |
|---|---|---|---|---|
| `#1055` | **4 findings** | rate-limited | 0 | ⛔ **DEFICIT 4 : 0** |
| `#1058` | **2 findings**, one 🟠 Major | rate-limited | 0 | ⛔ **DEFICIT 2 : 0** |
| `#1057` | rate-limited | rate-limited | 0 | no baseline — not assessable |
| `#1059` | rate-limited | rate-limited | 0 | no baseline — not assessable |
| `#1061` | reviewed, **0 findings** | rate-limited | 0 | ✅ clean, 0 : 0 with a real baseline |

⭐ **`#1058` is the sharpest instance**: PR-Agent's Guide positively asserts *"No major issues
detected"* on a diff where CodeRabbit posted a finding it classified as **Major**. That is a direct
contradiction of a specific claim on the same input, not a difference of threshold.

⭐ **`#1061` is the necessary counter-example**: PR-Agent's zero agreed with a reviewer that actually
looked. **The detector must not fire there.** Two of five runs are deficits, one is a corroborated
clean, two are unassessable — a detector that scores 4/5 as bad is wrong.

Full per-run analysis in `findings/PR-{1055,1057,1058,1059,1061}.md`.

## Deliverables

1. **D1 — GATE (mutates nothing): settle what counts as a comparable finding, and whether a baseline
   exists.** Per PR, derive each reviewer's finding count and whether it **reviewed at all** (a
   rate-limit refusal is not a zero — it is an absent baseline). ⚠ **Counting is the whole difficulty
   here**: CodeRabbit's four findings on `#1055` arrived across two review bodies ("Actionable comments
   posted: 3" then "1"), and its inline threads carry its own acknowledgement replies. A naive comment
   count would be wrong in both directions. **State the counting rule explicitly.**
2. **D2 — a deficit signal, computed only when a baseline exists.** PR-Agent returning materially fewer
   findings than a reviewer that actually reviewed the same diff is reported. ⛔ **It must NOT fire when
   every other reviewer refused, and must NOT fire on `0 : 0`.**
3. **D3 — the signal names what it is.** A deficit is a **bug report about the reviewer**, not a merge
   verdict and not a participation verdict: PR-Agent *did* provide a result, so participation and the
   merge decision are unaffected. ⛔ **Do not gate the merge on this** — it is an observability signal
   about reviewer quality, and turning it into a gate would block merges on a third party's output.
4. **D4 — tests, each verified to FAIL pre-fix**, using the real corpus: (a) `#1055` (4 : 0) and
   `#1058` (2 : 0) report a deficit; (b) `#1061` (0 : 0, real baseline) does **not**;
   (c) `#1057` / `#1059` (no baseline) are reported as unassessable, **not** as clean and **not** as
   deficits. ⛔ **(b) and (c) are the load-bearing cases** — a detector that fires on them is worse than
   no detector, because it would manufacture reviewer-quality bugs from rate limiting we already
   accept as normal.

## ⭐⭐ D1 OWNS THE COUNTING RULE FOR THE WHOLE EPIC — assigned 2026-08-08

Three staged plans independently need *"how many findings did each reviewer produce on this diff, and
did it review at all"*, and each was about to derive it separately:

| Plan | Why it needs the count |
|---|---|
| **PLAN-PR-006 (this plan), D1** | the deficit signal is a comparison of per-reviewer counts |
| **PLAN-PR-011, D4** | the review-versus-gate delta is "what review caught that the gates did not" |
| **PLAN-PR-021, D2** | the coverage disclosure states an `N of M` and must name its denominator |

⛔ **Three derivations of one quantity is three chances to disagree, and a coverage figure that differs
between two artifacts is exactly the class this epic exists to close.** ⇒ **D1's counting rule is the
epic's single source of truth for reviewer finding counts.** D1 must therefore state it as a *reusable
contract*, not as an internal step: the counting rule, the reviewed-at-all predicate, and the
required-vs-optional denominator, each named and each with its population published.

⚠ **The difficulty is already known and is why this must not be re-derived per plan**: CodeRabbit's four
findings on `#1055` arrived across two review bodies ("Actionable comments posted: 3" then "1"), and its
inline threads carry its own acknowledgement replies. **A naive comment count is wrong in both
directions.** ⭐ **`participated_but_empty` is a real member of the shipped taxonomy** — a reviewer that
looked and found nothing is a *successful* review with a count of zero, and must never collapse into
"did not review".

⛔ **PLAN-PR-011 and PLAN-PR-021 CONSUME this rule; they do not restate it.** If either lands first, it
states the rule and this plan consumes it instead — the ownership is on the *rule*, not on the plan id.
Whichever ships first, **the other two cite it and do not re-derive.**

## ⛔ RE-HOMED 2026-08-08 — the `refused_hard` fall-through, NARROWED by first-party re-verification

Relocated from `epic.md` § Open Defects, where it sat as *"no owning plan, a PLAN-PR-007 D1 question"*.
**PLAN-PR-007 has SHIPPED (`#1118`) without taking it**, so it is re-homed here — this plan owns the
absence-cause partition, and this is a defect in exactly that partition.

⛔⛔ **HALF OF THE RECORDED CLAIM IS NOW REFUTED. Do not carry the original wording forward.** The entry
asserted: *"Only `coderabbit` declares `rate_limit_class` in the registry at all, so every other bot
resolves to `refused_hard` because the field is MISSING."* Orchestrator-verified first-party in merged
main — **all three registry docs now declare it:**

| Bot | `rate_limit_class` | Site |
|---|---|---|
| coderabbit | `awaitable_window` | `coderabbit.md:45` |
| sourcery | `hard_quota` | `sourcery.md:41` |
| pr-agent | `unknown` — with an explicit *"UNVERIFIED — no refusal of any kind observed"* note | `pr-agent.md:121`, `:232` |

⇒ **The "positive claim derived from an ABSENT field" defect is FIXED**: the field is present for every
bot, and pr-agent's `unknown` is an *honest declaration of ignorance*, which is the right shape.

⭐ **What SURVIVES, narrowed to its true form.** `review_completeness.py:237` still computes
`awaitable = bot_registry.rate_limit_class(bot) == 'awaitable_window'` — a **binary** over a
**three-valued** field. So `unknown` collapses into `refused_hard`, and an operator is shown
*"refused_hard (hard quota)"* for a bot whose registry says **we do not know**. ⛔ **The remaining defect
is a declared-unknown rendered as a positive finding** — a strictly smaller and more precise claim than
the original, and still this epic's theme: the gate is right (unknown → unproven → barrier holds, the
safe direction) and the **report** misinforms, steering an operator toward *"waiting is futile, force
it"* when waiting might have worked.

⇒ **D1 folds this in**: the absence-cause partition must treat `unknown` as its own cause, never as
`hard_quota`. ⚠ **Do not stage it separately** — a third state on the same axis this plan already
partitions. Observed live on `API-Sheriff#140` (Sourcery's refusal was a **weekly** limit saying *"try
again later"*, i.e. awaitable in substance). Full original write-up:
[`findings/API-Sheriff-PR-140.md`](findings/API-Sheriff-PR-140.md) § 2.

## ⭐ A THIRD kind of indistinguishable zero (inbox `truthful-signals-006` item 4, 2026-07-30)

This plan already separates a **canned no-op** from a **substantive review**. API-Sheriff PR #132 supplies
a third member of the same family: ⛔ **a rate-limited bot reports `comments_found: 0`, byte-identical to
a clean review.** Two opposite outcomes — *"no issues"* vs *"no review happened"* — one representation.

⭐ **The forwarding epic calls it the most dangerous of its three findings, and the reasoning is worth
keeping**: the sibling defects produced *visible friction* (a blocked gate, an escalating wait) while this
one produces a **clean-looking green**. Had that plan not been separately tracking rate-limit state, the
zero would have read as approval.

⭐⭐ **A generalised rule already exists in the corpus and is directly reusable — do not re-derive it.**
Active lesson **`2026-07-24-13-002`** (`plan-marshall:build-maven`): *"Fail-closed consumer folded a
dispatched producer's ERROR payload into an observed clean verdict (zero findings) — a false green inside
a fail-closed feature, because it did not branch on producer status before folding the payload."*
⇒ **Branch on producer STATUS before folding its payload.** Same defect, different producer.

**Adopt the shared vocabulary verbatim** — it is what stops the participation check and the findings count
disagreeing about whether a review happened:

> **`reviewed-clean` · `reviewed-with-findings` · `did-not-review`**

⚠ **This vocabulary spans PLAN-PR-005 and this plan.** ⛔ **Agree it once and use it in both** — two
plans inventing two vocabularies for one distinction is the duplication failure this epic exists to fix.
⚠ Related but NOT the same: the *which-kind-of-zero* archetype a sibling shipped one instance of in
`#1064` (`inbox_state` discriminating empty / missing / unreadable). **The archetype is theirs; the
subject is ours** — reuse the shape, do not re-open their work.

## ⛔⛔ ABSORBED 2026-08-03 — the deficit is now MEASURED, the refusal is now DETERMINISTIC, and a THIRD artifact carries the same blind spot

### ⭐ The comparative deficit, measured on one diff — and the required reviewer produced zero

`code-intelligence-substrate-007` § 1, first-party to PLAN-CIS-028 / PR **#1080** (merged `e1ae38142`):

| Reviewer | Verdict on the diff | Tasks traceable to it |
|---|---|---:|
| **pr-agent (required)** | "No major issues detected" | **0** |
| CodeRabbit | Two **Major** findings, both dispositioned **FIX-HERE** by the operator | **5** |
| Sourcery | hard-quota throughout — absent | — |

⭐ **The sharp part**: one CodeRabbit Major became TASK-021, a runtime tracked-source guard. **The reviewer
that reported the diff clean was silent on a defect the operator judged worth fixing mid-run — and it is
the reviewer whose green is LOAD-BEARING for the merge gate.**

⇒ **This is a sixth row for the § "Live evidence" table and the strongest yet**, because the baseline is
unambiguous (5 traceable tasks, not merely a finding count) and it is the *required* bot that under-produced.
⚠ **It is n=1 and the filer files it as such.** ⛔ **D4(b)/(c) remain load-bearing** — do not let this row
tempt the detector toward firing on thin baselines.

**Open question handed to us, not answered by the filer**: ⭐ *should the `required` designation follow
measured actionable yield rather than configuration order?* ⚠ **Out of scope for D2** — record it, do not
build it. D3 already forbids this signal from moving a merge verdict, and reassigning `required` would do
exactly that.

### ⭐⭐ The diff-size refusal is the ONLY DETERMINISTIC axis — and therefore the only one a plan can design around

`truthful-signals-014` item 10. Sourcery never reviewed **API-Sheriff PR #141**: it refuses on a
**150,000-char diff limit**. Sourcery is optional, so the quorum passed and the plan proceeded
**correctly** — but ⛔ **nothing in the completeness surface distinguished "reviewed and found nothing"
from "declined to look at all."** That is precisely this plan's third-kind-of-zero, with a new cause.

⭐ **Why this one matters more than its severity suggests**: of the five known false-green axes
(rate-limit, wrong-HEAD, force-push, never-ran, diff-size) **diff-size is the only deterministic one.**
The other four are timing- or state-dependent. ⇒ **A plan whose footprint will exceed the limit knows so
AT OUTLINE**, which makes this the one axis a plan can predict and design around rather than merely detect.

⚠ **Same class already bit us once on a different bot**: an epic carries a standing *"keep the PR under
100 files"* clause written after a plan exceeded **CodeRabbit's** full-review cap; PLAN-11 landed
**56 files / +5,473**. **Two bots, two limits, both discovered the same way — by a plan hitting one.**

⇒ **Proposed and adopted into scope**: surface each bot's **declared size limits** where a plan can consult
them at outline, and report a size-refusal as a **distinct completeness outcome** rather than as silence.
⚠ This extends the shared vocabulary — `did-not-review` is too coarse; the refusal *reason* is the
actionable part.

### ⭐ A THIRD artifact with the same blind spot — `review-retrospective` has no row for a refusal

`truthful-signals-016` § 2 (originating as `fail-closed-signal-integrity-004`, routed here under the
three-way rule). The artifact represents *"produced no comments"* and *"never ran"* **identically: by
having no row.** There is no representation for **"enabled, invoked, and refused."**

**Observed live on PR #1081**: `sourcery` refused with `hard_quota` on **all three** review rounds and
simply **has no row**. ⇒ A reader sees two clean reviewers and concludes the diff was reviewed by two bots.
It was reviewed by two and **refused by a third**, and the artifact cannot say so.

⛔ **This is a fail-open INSIDE the review apparatus itself** — the surface used as evidence that a review
happened. ⭐ **Proposed shape, and it matches this epic's population-derivation discipline**: emit a row per
**enabled** reviewer, not per **responding** reviewer, with an explicit participation state. ⛔ **Deriving
rows from the responding set makes the detector's population a strict subset of its own domain** — the
vacuous-set archetype, in a new place.

⚠ **Scope note**: `finalize-step-review-retrospective` is a *different surface* from the participation
classifier this plan otherwise edits. **Confirm at D1 whether one vocabulary change serves both**; if it
splits the change materially, split the plan — this spec was itself created by exactly that judgement.

### ⭐ The summary card / trigger acknowledgement — a participation artifact, not a review claim

`code-intelligence-substrate-007` § 3. The `(default, pr-comment, accepted)` disposition tuple recurred
twice in one plan from two structurally identical cases: pr-agent's persistent **"PR Reviewer Guide"**
card, and CodeRabbit's **trigger acknowledgement** (*"Review finished. Note: CodeRabbit is an incremental
review system…"*) carrying no code content at all. **Both consumed a triage decision to conclude there was
nothing to decide.**

⭐⭐ **The second case ties this plan to PLAN-PR-013 § mechanism (e)**: that acknowledgement was the **ONLY**
record CodeRabbit produced at #1080's final HEAD. ⇒ **The disposition rule and the participation-evidence
rule are the same lesson from two sides — the artifact that looks like participation is precisely the one
that proves the review did not happen.** ⛔ **Coordinate the discriminator with PLAN-PR-013; do not ship two.**

⚠ **Note the tension with this plan's § RE-AIMED ruling, and resolve it explicitly at D1 rather than
silently**: the operator ruled *"No findings IS a result"* and that a Guide reporting no issues is **not a
defect on its own**. That ruling stands. **What is new is the DISPOSITION treatment** — a contentless card
should not consume a triage decision, and its presence must not be read as review evidence. **Neither
conflicts with the ruling; a detector that starts judging whether prose is "substantive" does.**

### ⛔⛔ ABSORBED 2026-08-03 (second drain) — the absence corpus is a MIXED POPULATION, and D1 measures across it

From `code-intelligence-substrate-009` (PLAN-CIS-030 / PR **#1086**, merged `9b689d65b`): **Sourcery
never reviewed #1086 at all — it hard-refuses above 150,000 diff characters, and that PR was well past
the threshold.**

⛔⛔ **This is the item that most directly threatens D1's validity.** Across **#1077, #1078, #1079, #1084
and #1086** we and the siblings have logged Sourcery as *absent*, *hard-quota*, *stale* or
*unmeasurable*. **Those readings all pointed at rate limiting** — a stochastic, quota-shaped cause.

⇒ **At least one was size, not quota.** The corpus blends **two mechanisms with different remedies**:
quota needs retry/backoff or a plan change; size needs a smaller diff or the reviewer told not to expect
a review. ⛔ **Any per-reviewer participation rate computed across the pooled corpus mis-attributes
both** — and D1 is exactly a per-reviewer measurement.

⇒ ⭐ **D1 gains a prerequisite: partition the absence corpus by CAUSE before computing any rate.** The
diff sizes are recoverable from the merge commits, so this is **cheaply derivable**. ⛔ **Do not report a
Sourcery participation rate until the partition exists** — it would be a confident number over a
population that means two things.

⭐ **The generalisable half, and it strengthens the diff-size item above**: *a reviewer that declines for
a KNOWABLE reason should be recorded as `declined(reason)` **before the review is even requested**, not
discovered as an absence afterwards.* ⇒ **Deterministic refusal is predictable at request time, not
merely detectable after** — which is a different class of mechanism to build against.

⚠ **What the filer explicitly does NOT claim, and neither do we**: the 150,000 threshold is reported by
the plan that hit it — **first-party to that run, second-hand to us. Re-derive before pinning a test to
the number.** And the share of past absences that were size rather than quota is **underived**.
⛔ They also explicitly decline to propose splitting PRs as a workaround; **that remains out of scope here
too** — it is a plan-shape change with its own costs.

### ⭐ A THIRD reviewer state, from PLAN-PR-009's own retrospective — `not-invited`

PLAN-PR-009 volunteered a correction: its claim that *"Sourcery refused on both passes"* was **wrong** —
the review-retrospective found it was **never re-invited** on the second pass. **One refusal record, not
two.**

⇒ ⛔ **`not-invited` is a distinct state from `refused` and from `absent`**, and D1's vocabulary must
carry it. A reviewer that was never asked has not declined and has not gone silent — **and scoring it as
either corrupts the rate in opposite directions.** ⚠ It is also the state most likely to be *ours* rather
than the bot's, which makes it the one with an actionable remedy.

### ⚠ An owed architecture hint, relayed to us and NOT applied

The filer could not apply it — the emitting step is `post_run_review: true`, and an `architecture enrich`
call there would land tracked source on `main` with no push path (the `#990` defect). **Ours to apply or
decline; the orchestrator is not writing it.** ⇒ **Carry it as a deliverable of this plan**, which is
inside a worktree and has a push path:

> **Target**: `architecture enrich insight --module default`
>
> A review bot's persistent summary card and its trigger acknowledgement are participation artifacts, not
> diff-derived claims. Dispose of them as `accepted` without opening a fix task, and never read their
> presence as evidence that the bot reviewed the current HEAD — check for a review object stamped with the
> live `reviewed_commit_sha` instead.

## ⛔⛔ ABSORBED 2026-08-08 (inbox drain) — the refusal pre-filter leaks WITHIN a single bot, and the leak is measurable in the triage ledger

Two inbox messages, one mechanism.

### The mechanical defect — `absent-names-two-states-with-opposite-remedies-003`

Source: pending Q-Gate finding `911e3e`, component `plan-marshall:workflow-integration-github`,
observed at HEAD `a5749b0d2` on PR #1118. **First-party, our own run.**

`fetch_findings` reported `count_skipped_refusal=3` and, **in the same pass**, stored CodeRabbit's
rate-limit refusal notice (`b2f902`) as a pending `pr-comment` finding. Three sibling refusal bodies
from the same bot were filtered; this one was not.

⭐⭐ **Partial coverage WITHIN one bot is what makes this diagnostic rather than ambiguous.** The
refusal predicate is an **enumeration of known refusal shapes**, not a positive test of what a review
body must contain. The same bot emits more than one refusal shape, so the predicate filters the
shapes it has met and passes the ones it has not. This is not "a bot nobody modelled".

Two things go wrong at once when a refusal lands in the ledger as a pending `pr-comment`:

1. The pre-merge barrier's *"0 pending pr-comment findings"* predicate is now gated on a non-finding.
   The run must dispose of a comment that says nothing about the diff — triage work manufactured by
   the tool.
2. Any count of "actionable review comments" for the PR is inflated by one, **corrupting the
   review-retrospective metrics this epic collects** (D3 surface).

### The population signal — `absent-names-two-states-with-opposite-remedies-012`

An owed `architecture enrich --module default` insight hint, recorded here rather than lost:

> When a `pr-comment` finding recurrently resolves as `taken_into_account` rather than being
> actioned, suspect the PRODUCER rather than the triage. The finding store admits every surviving
> comment as a triage item, but several recurring comment classes are not reviewer feedback at all: a
> bot's own refusal or rate-limit notice, a bot's "already reviewed" status reply, and the plan's own
> supplementary PR-body comment. Treat a rising `taken_into_account` share on `pr-comment` as a
> signal to widen the producer's non-feedback pre-filter, not as a triage workload to absorb.

The tuple `(default, pr-comment, taken_into_account)` recurred **3 times in one plan** against a
`preference_min_recurrence` threshold of 2, and **all three were non-feedback classes** (one
plan-authored PR-body supplement, two CodeRabbit status/refusal notices).

⇒ **`taken_into_account` share on `pr-comment` is a cheap, already-collected proxy metric for
pre-filter coverage.** Consider it as the D-level acceptance signal rather than inventing a new one.
⚠ The owed `architecture enrich` call is NOT made by the orchestrator (out of its write boundary) —
the implementing plan owes it.

**Candidate remedy (not applied):** restate the refusal pre-filter **positively** — a stored
`pr-comment` finding must positively look like review feedback, rather than merely not matching a
list of known refusal phrasings. This is the same enumeration-versus-positive-validation defect
CodeRabbit raised against `branch-cleanup.md` on the same PR (`a582b1`), i.e. two independent
instances in one run.

## ⛔⛔ RE-SCOPE REQUIRED 2026-08-09 — PLAN-PR-022 SHIPPED A CONFOUND INTO THIS PLAN'S BASELINE

`PLAN-PR-022` landed as **#1130** on 2026-08-09 and changed the reviewer's *instructions*: domain-scoped
charter packs, `/improve` behind a label, and `AGENTS.md` reaching two repos where it previously did
not resolve at all.

⛔ **Every row in the Live-evidence table above (`#1055`, `#1057`, `#1058`, `#1059`, gathered
2026-07-30) predates that change.** A deficit measured before the instruction fix and a deficit
measured after are **not the same quantity**, and D2's signal cannot pool them.

⇒ **D1 must additionally establish the instruction-generation boundary** — for each PR in the corpus,
which charter the reviewer was running — and D2 must not compute a deficit across it. ⭐ Treat the
boundary as an opportunity rather than only a hazard: the pre/post split is **the cleanest available
measurement of whether #1130 worked**, and it is the same question PLAN-PR-023 D3 asks by re-review.
⚠ **Coordinate with PR-023 D3; do not run two independent measurements of one effect.**

## ⭐⭐ ABSORBED 2026-08-09 — the DISPLAY defect, which is sharper than the deficit defect

Source: `generic-charter-language-specific-defect-008` (PR #1130), first-party.

The `automatic-review` step recorded `outcome: done`, `display_detail: **"0 comment(s) found (unified
triage pending)"**`. ⛔⛔ **That sentence is TEXTUALLY IDENTICAL to what a clean 27-file review
produces** — and it is what a later reader, a PR body, and a status render actually see.

⭐ **This is this plan's title condition, stated exactly**: a canned no-op indistinguishable from a
review — not in the reviewer's output, but in *our own rendering of it*. The only artefact stating the
truth was a `[VERIFY]` WARNING in the work log: *"Zero actionable comments here means NO REVIEWER
PRODUCED CONTENT, not that the diff is clean."* That sentence reaches no step field, no PR body, and
no status render. It was written by the run's own judgement, not produced by any gate.

⇒ **New deliverable: `display_detail` must carry the reviewer-state distribution, not just the comment
count.** `"0 comment(s) found"` and `"0 comment(s) found — 1 empty, 2 refused, 0 proven"` are different
facts and must not share a rendering. ⭐ **The taxonomy already exists** (`STATE_REFUSED_AWAITABLE` /
`STATE_REFUSED_HARD`, split by registry `rate_limit_class`) — it simply does not reach the field a
reader sees. This is a plumbing deliverable, not a design one, and it is the cheapest real improvement
in the whole epic.

⚠ **From `code-intelligence-substrate-010`, a constraint on D1's counting rule:** on PR #1126 pr-agent
participated and raised two focus areas that were **both refuted against live code** — one would have
turned a documented fail-safe into a fail-quiet clean verdict if applied. ⇒ **"participated" and
"produced value" are different predicates, and only the first is measured.** A counting rule that
scores a refuted finding as a finding measures the wrong thing. ⛔ But do NOT swing to scoring
correctness either — that needs a human verdict per finding and is not automatable here; report the
counts and their disposition separately.

## Claim Labels

- ⚠ **Every 2026-08-03 absorbed item is the filer's first-party observation, re-derived by nobody here.**
  The `truthful-signals-014` items came from bundle **0.1.1276**, which predates our tree — **re-ground
  every line reference at outline.**
- OBSERVED (independently corroborated on `#1057`): pr-agent's whole contribution was the three-line
  fixed-shape Guide quoted above, with zero actionable content.
- OBSERVED (same PR, and the reason this matters): CodeRabbit and Sourcery **both refused** (rate
  limit / weekly quota) and said so **only in their comment bodies** — the check states did not show
  it. So the participation signal was simultaneously (a) a canned no-op counted as present and (b)
  two refusals counted as absent-or-silent. ⭐ **Three bots, three wrong classifications, one PR.**
- OBSERVED (`#1061`, a fourth shape): CodeRabbit's **check completed but produced no comment at all**
  — distinct from a refusal comment and from a dropped credit.
- OBSERVED (`#1058`): CodeRabbit **reviewed the first HEAD and refused the second**, so *partial*
  participation read as participation while **the diff that actually merged went unreviewed**.
- ⚠ HYPOTHESIS: the canned-no-op shape is stable enough to detect by shape rather than by content
  judgement — confirm/refute at D1 (verify-at-outline). **If refuted, say so and stop**: a
  content-judgement detector that decides whether prose is "substantive" is a different and much
  larger thing than this plan, and shipping a fragile shape-matcher is worse than shipping nothing.
- HYPOTHESIS (asserted absence): no existing registry field already carries this distinction —
  confirm/refute against `bot_registry.py`'s record fields and `participation_evidence`
  (verify-at-outline). An unverified absence here would duplicate an existing mechanism.
- Verify-first clause: `refusal_patterns` already exists per bot. Establish at D1 whether the canned
  no-op belongs as a *sibling* of that field or as a distinct marker, rather than assuming a new
  field is needed.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/automatic-review/scripts/bot_registry.py`
  — the per-bot record and its `participation_evidence` / `refusal_patterns` fields.
- OBSERVED: `.../automatic-review/standards/pr-agent.md`, `coderabbit.md`, `sourcery.md` — the
  per-bot registry docs whose declared shapes D1 derives against.
- OBSERVED: `.../automatic-review/standards/bot-participation-contract.md` — the evidence taxonomy.
- HYPOTHESIS: `.../workflow-integration-github/scripts/github_pr.py` § `fetch_findings` — if the
  marker must be computed at ingestion (verify-at-outline).
- OBSERVED: the `automatic-review` and `workflow-integration-github` classification tests.

## Dependencies and Sequencing

- Depends on: none, but **sequence AFTER PLAN-PR-007** (Defect F). F adds a taxonomy member; this
  plan adds an orthogonal marker. Landing F first means this plan extends a settled taxonomy instead
  of racing one.
- Overlaps with: ⚠ **PLAN-PR-003** also edits `automatic-review/standards/coderabbit.md` (and
  possibly `sourcery.md`). Sequence, do not pair.
- Overlaps with: ⚠ **PLAN-PR-005** and **PLAN-PR-007** both read
  `bot-participation-contract.md`. Sequence.
- Adjacent to: **PLAN-PR-008** (barrier deadlock). That plan's D2 distinguishes "unproven" from
  "refused" — a THIRD distinction on the same axis. ⛔ **Coordinate, do not duplicate the detector**;
  if the two converge on one mechanism, say so rather than shipping two.

## ⛔⛔ ABSORBED 2026-08-08 — the absence-corpus partition D1 owes now has a NAMED VOCABULARY, and it is already in the contract

Sources: `truthful-signals-020` items 11 + 15; `truthful-signals-021` (a size-ceiling refusal on
#1113); `truthful-signals-022` (that message's own partial RETRACTION); C05 lessons
`2026-07-28-23-001`, `2026-07-28-23-002`, `2026-07-29-19-002` — those three were routed to PLAN-PR-007,
which is LAUNCHED and cannot absorb them, so they are folded here where the taxonomy work lives.

**D1's prerequisite is unchanged and is now sharper: partition the absence corpus BY CAUSE before
computing any per-reviewer rate.** What is new is that the partition does **not** need inventing —
`bot-participation-contract.md` line 59 already defines `refused_hard` as *"a refusal that does not
reopen on a useful timescale (`rate_limit_class: hard_quota`), **or a structural refusal such as a
size/diff ceiling**"*, and carries the disposition too: *"whether the absence is tolerable is a
required-vs-optional question, not a waiting question."* ⭐ **OBSERVED, verified first-party by the
orchestrator at this drain** (that line read directly). ⇒ D1 partitions into the EXISTING taxonomy
members and reports any corpus member that fits none of them; it does not author a parallel vocabulary.

**The four causes the corpus is known to blend**, each with a different remedy and therefore
un-poolable into one rate:

| Cause | Remedy | Waiting helps? |
|---|---|---|
| Rolling rate window | retry / backoff | yes |
| Hard weekly quota | plan change | no |
| Size / diff ceiling (`refused_hard`) | a smaller diff — an AUTHORING decision made long before the PR exists | **no** |
| Not-invited (ours, not the bot's) | invite it | n/a — this one is the actionable one |

⭐ **The size-ceiling member inverts the usual relationship in the worst direction: the larger the
change, the less of it gets reviewed.** Every other cause is bad luck; this one is a structural
incentive pointing the wrong way and is reachable by the author's own scoping decision. **It is
therefore also a REVIEW-COVERAGE dimension of the scope-bloat split guard** — splitting a plan is
currently argued on landing-and-analyzing as one unit, and it also determines whether a reviewer looks
at the diff at all. That consequence survives `truthful-signals-022`'s retraction and is recorded as an
epic Watch; it is NOT a deliverable of this plan.

⚠ **Two corrections that must not be lost, both from `truthful-signals-022` retracting its own
predecessor:**

1. The size ceiling is **NOT a new taxonomy axis** — asserting novelty against an unread taxonomy is
   the same corrective-is-a-hypothesis failure this epic keeps cataloguing. Do not stage a taxonomy
   extension for it.
2. **A Sourcery absence is NOT a coverage gap in this project.** OBSERVED, verified first-party by the
   orchestrator at this drain against `marshal.json`
   (`plan.phase-6-finalize.steps.plan-marshall:automatic-review`): `required_bots = pr-agent`,
   `optional_bots = coderabbit,sourcery`, `bot_lists_provenance = answered`. Per the contract an
   optional bot's silence "never blocks" and "is not a failure". ⛔⛔ **Every "1 of 3" / "2 of 3"
   coverage figure in this epic's ledger — including the six-consecutive-PRs coverage-regime line —
   was computed against the ENUMERATED ROSTER, which is the wrong denominator. Recomputed against
   `required_bots`, those landings met quorum at 1 of 1.** D1 MUST state which denominator each rate
   uses, and MUST NOT reuse the roster-denominated figures already in the ledger.

⚠ The 150,000-diff-character threshold remains SECOND-HAND and is NOT verified as universal or
non-configurable. Re-derive before pinning any test to a number.

- HYPOTHESIS (verify-at-outline): that each historical Sourcery absence in the corpus
  (#1077/#1078/#1079/#1084/#1086/#1107/#1113) is attributable to exactly one cause above. Confirm/refute
  artifact: the stored refusal comment bodies via `ci pr comments --pr-number N`, matched against the
  `refusal_patterns` in each `automatic-review/standards/{bot_kind}.md` registry doc. Diff sizes are
  recoverable from the merge commits — cheap, and still underived.

## ⚠ RECURRENCE 2026-08-09 — a FOURTH consecutive quorum-pass on zero actionable review, and the three refusal reasons are all DIFFERENT

Source: `truthful-signals-027` item 2 (finding `61284d`, reported by PLAN-TRUTH-070 on PR **#1132** —
PR state orchestrator-verified merged at this drain). **Recorded as a recurrence on this plan's existing
counting-rule deliverable (D1), NOT as a new item.**

The filer records #1132 as the third consecutive occurrence; the forwarding orchestrator corroborates
from its own landings and makes it **four consecutive plans**:

| PR | Shape |
|---|---|
| #1122 | quorum *"met (participation only)"*, CodeRabbit rate-limited, two bots `participated_but_empty`, `review-retrospective` returning `verdict unmeasurable` |
| #1123 | `pr-agent` reporting no major issues on a diff where CodeRabbit and Sourcery found real defects |
| #1125 | same shape as #1123 |
| #1132 | merged under explicit operator override — `participation_complete=false`, `unproven_bots=[pr-agent, coderabbit, sourcery]`, `pr-agent=participated_stale`, `coderabbit=refused_awaitable`, `sourcery=refused_hard`, **no reviewer produced an actionable comment on the diff at all** |

⭐⭐ **The load-bearing observation is the LAST ROW's spread, not the count.** Three reviewers reached
non-review by **three different routes** — a stale participation credit, a temporal refusal, and a
structural refusal — **and the quorum outcome was identical to the other three rows.** ⇒ This is the
sharpest available statement of D1's premise: *a predicate that cannot distinguish "reviewed and found
nothing" from "never reviewed" is blind to the reason as well as to the fact.*

⚠ **Note the cross-item consistency, and do not double-count it**: `pr-agent=participated_stale` on
#1132 is the SAME event PLAN-PR-013 absorbed as item 1 of this message. One observation, two plans, two
different questions — PR-013 asks *why the credit decayed*, this plan asks *why the quorum passed
anyway*. ⛔ Neither may cite it as independent corroboration of the other.

⚠ **CLAIM LABEL — this is a pattern claim, not a measurement, and it must not be promoted to one.** The
filer states it explicitly: the #1132 barrier figures are quoted from a landing message, the earlier
three are the forwarding epic's own landings, **no population and no rate — four consecutive
observations.** ⛔ Binding on D1: four-in-a-row is a reason to *derive the population*, never a substitute
for having derived it. This plan's own standing rule — every set-guarding detector must be
population-derived — applies to its own evidence.

⭐ **Sequencing note for D2**: this row set spans the #1130 boundary that the RE-SCOPE section above
flags as a confound (#1122/#1123/#1125 are pre-#1130, #1132 is post). ⇒ **These four are NOT poolable
either**, for exactly the reason stated there. If anything, #1132 landing post-#1130 with zero actionable
output across three reviewers is the more interesting half — it is a datum about whether #1130 worked,
which PR-023 D3 owns. **Coordinate; do not measure it twice.**

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/review-apparatus/plans/PLAN-PR-006-canned-no-op-indistinguishable-from-a-review.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/local/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-marshall-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
