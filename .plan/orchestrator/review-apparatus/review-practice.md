# Review practice: per-run verdicts and the local-review back-feed

epic: review-apparatus

> **SINGLE SOURCE OF TRUTH for this epic's recurring review procedure.** `epic.md` and
> `findings/README.md` POINT here and MUST NOT restate any rule below — two copies of a normative rule
> drift, which is the source-of-truth-duplication archetype this epic exists to fix elsewhere.
> Extracted from `epic.md` on 2026-07-30 for exactly that reason.

**A RECURRING orchestrator obligation, not a one-off.** It runs at every post-merge PR revisit this
epic performs. All rules below are operator-stated (2026-07-30).

## 1. Per-bot verdict rules

| Bot | Gating (plan-marshall) | Rule |
|---|---|---|
| **CodeRabbit** | **optional** | Rate limiting is **known — NOT an issue.** Record and move on |
| **Sourcery** | **optional** | Rate limiting is **known — NOT an issue.** Record and move on |
| **PR-Agent** (`cuioss-review-bot`) | ⛔ **required** | ⛔ **MUST always provide a result. A missing result is a BUG** |

**The gating column is CONFIG, verified not assumed** — `.plan/marshal.json`
`plan-marshall:automatic-review` declares `required_bots: "pr-agent"`,
`optional_bots: "coderabbit,sourcery"`, with `bot_lists_provenance: "answered"` (an answered operator
question, not a seeded default). Operator rationale, 2026-07-30: **for this repo CodeRabbit is optional;
it matters more on API-Sheriff, which is production code.** ⚠ The gating is **per-repo** — never carry
this table's column to another repo without reading that repo's config.

⛔⛔ **"Optional" is a GATING classification, NOT a VALUE classification. Do not confuse them.**
An optional bot's silence never blocks a merge — that is all it means. It says nothing about whether its
findings are worth having. ⭐ **`#1067` is the proof and it points the other way**: the *optional* bot
(CodeRabbit) found **5 genuine defects** on a diff the *required* bot had already answered with none, one
of them the plan reproducing its own target defect. **A future reader must not conclude that an optional
bot's findings matter less** — on the evidence so far they have mattered more.

⇒ Two consequences that follow directly:

- The § 1 **comparative deficit rule is about efficacy, not gating**, so it applies unchanged when the
  baseline comes from an optional bot. A required bot returning nothing where an optional one returns
  five is exactly the deficit the rule names.
- `optional_bots` is **already the sanctioned way to accept an optional bot's silence**
  (`branch-cleanup.md` says so explicitly). So any *deadlock* question — and PLAN-PR-008's accepted-
  coverage-gap decision — is narrowly about a **required** bot, never about CodeRabbit or Sourcery here.

**"No findings" IS a result** — an informational Guide reporting no issues satisfies the
must-provide-a-result rule and is **not a defect on its own**.

⛔ **Separate comparative rule: PR-Agent producing structurally fewer findings than the other reviewers
on the same diff is a bug in itself**, even though each individual "no findings" result is legitimate.

⛔ **The must-provide-a-result rule presumes the bot was ASKED.** A required bot that produced no result
because **no workflow run was ever created** is a *trigger* defect upstream of the reviewer, not a bot
defect — scoring it against the bot misattributes the failure and sends the operator to investigate a
healthy, correctly-configured App. **Check for the run before scoring the silence**: zero
`pull_request`-event runs for the PR across *every* workflow means the event never reached Actions at all.
(First observed on `cuioss/API-Sheriff#133`, 2026-07-30.)

⛔⛔ **NEVER score a bot's silence from a branch-filtered workflow query.** Checking for the run is
required (above), but the obvious query is wrong:
`actions/workflows/{f}.yml/runs?branch={pr_branch}` **cannot see a `/review` run at all** — GitHub
attributes `issue_comment`-triggered runs to `head_branch: main`, never the pull request's branch. And
`/review` is the ONLY re-review path, because the reusable workflow has no `synchronize` trigger by
design. A query that misses the only re-review path will report "never triggered" for a bot that
reviewed. **Query the workflow's runs UNFILTERED over the date, and match on the review comment's own
timestamp.** ⚠ Earned the hard way: `API-Sheriff#133` was scored *never triggered* on exactly this
query, the verdict fed a taxonomy member into `PLAN-PR-007`, and both were refuted on 2026-08-01 — see
[`findings/2026-08-01-sweep-4day.md`](findings/2026-08-01-sweep-4day.md) § 3.

⚠ **The deficit is only assessable against a baseline.** When every other reviewer was rate-limited,
nothing reviewed the diff besides PR-Agent: the run is evidence **neither way**, is scored
*unassessable* rather than clean, and **its verdict must never be read as PR-Agent performing well.**

**The scoring outcomes are four, not three** — a baseline's presence is necessary but not sufficient:

| Outcome | Condition |
|---|---|
| **clean, corroborated** | A real baseline existed and PR-Agent matched it |
| **deficit** | A real baseline existed and PR-Agent returned structurally fewer findings |
| **unassessable — no baseline** | Every other reviewer refused; nothing reviewed the diff but PR-Agent |
| ⭐ **unassessable — never triggered** | A baseline existed, but PR-Agent produced no result because it received no event. The comparison is void, not lost — there is nothing to compare |

⚠ A refusal that **never expires** (a diff-**size** limit) is not the same as a rate/quota limit even
though both read as "refused". Waiting clears one and never clears the other. Record which.

## 2. The back-feed question

For each finding, ask exactly one question:

> **Could we have found it ourselves?**

### The signal is the ANSWER POSTED ON THE PR — not our internal ledger state

The automatic-review workflow is instructed to **always post an answer**: `post_responses` transmits
the triage disposition and its rationale back to the PR as a thread reply (then resolves the thread),
or as one batched PR-level comment for genuinely threadless kinds. **That posted answer is the signal**,
and it says whether we accepted the finding.

⛔ **Do NOT key this off the findings ledger's internal resolutions** (`fixed` / `accepted` /
`taken_into_account` / `rejected` / `suppressed` / `pending`). Those are our own claim about ourselves.
The posted reply is the observable, and the only thing checkable from outside — the same standard that
makes `ci pr comments --pr-number {N}` the sole evidence of participation anywhere in this epic.

### ⭐ A MISSING answer is itself a finding — never a silent exclusion

A finding with no posted answer is a defect in the **response path** and is recorded as one, not
dropped from the corpus. Two known producers: a thread-bearing finding whose thread is missing is
reported **`untransmitted`** (deliberately never batched), and **`skipped`** is specified to fire "only
when there is genuinely nothing to say" — so an unjustified `skipped` is the same defect wearing a
success label. ⚠ **Treating an unanswered finding as noise would hide exactly the failure this epic
exists to catch.**

⚠ **Trap when reading the corpus.** `fetch_findings` deliberately drops any comment whose body *starts
with* the batched-response heading (`count_skipped_self_response`) so our own answers do not re-enter as
findings — but **that same batched comment is the artifact you must read** to check an answer was
posted. Do not mistake the self-response filter for evidence that no answer exists. The match is
start-anchored, so a human comment quoting the heading is still a real finding.

## 3. The three answer shapes

| Answer | Action |
|---|---|
| **Yes** | Add ONE `_detect_*` function over the diff's added lines in `ext-self-review-plan-marshall` |
| **No — semantic** | It needed reading the code and reasoning about intent. The bot's job. Drop it |
| **Yes, but the check was not running** | An **activation** question. ⛔ Do NOT compensate with a detector |
| ⭐ **Yes, and the check RAN but was too narrow** | **WIDEN the existing detector. ⛔ Never add a second one beside it** |

### ⚠ Why the fourth shape exists — added 2026-07-30, on the first real case

The first back-feed case resolved to none of the original three. `#1067`'s `835226` (*"one of those nine"*
against eleven) is covered by `_detect_count_prose`, which **exists and ran** — but scans only `SKILL.md`
files and matches only a closed five-noun set (`operations|fields|steps|rules|commands`). The finding fell
outside both bounds.

Answering that with a *new* detector is how the local review acquires two overlapping copies of one
check — the same duplication failure this epic exists to fix elsewhere. **Widen, and say so.**

⚠ **Widening must be DERIVED, not guessed.** Widening to "any noun" trades a narrow predicate for a noisy
one and violates constraint 2 below. Derive the set from what actually appears; state whether it is closed.

⭐ **And check the detector's own prose while you are there.** `_detect_count_prose`'s comment claims
`nine checks` is matched; `checks` is not in its noun set. **A detector's documentation is not exempt from
the defect it detects** — that one had shipped an unverified count claim about itself.

### ⚠ Why the third shape exists — the security review is conditionally active

The local review also includes the **security audit** (`default:finalize-step-security-audit`), which
is not always on:

- **plan-marshall** — a tier-`full` lane element; lane `auto` **drops** it, so it runs only at lane
  `full`.
- **API-Sheriff** — active in most cases.

⛔ **Do not add a detector to compensate for a check that was simply switched off** — that is how the
local review acquires a second, weaker copy of something it already has.

**Verify against the archived plan; never infer the lane.** The archived plan's execution manifest
carries the answer, and there are **two independent drop paths — check BOTH**:

1. `execution_profile` / `lane_dropped` — the lane tier dropped it (`auto` drops tier-`full`);
2. `security_class_omitted` — the **ceremony pre-filter** dropped it, as `{step, reason}` records.
   Separate from the lane; checking only the lane would miss it and misreport an inactive check as a
   detector gap.

## 4. The two standing constraints

1. **Not about duplicating the reviewer.** A finding that needed reading the code and reasoning about
   intent is the bot's job — answered "no", and dropped.
2. ⭐ **"As soon as you write complex rules, you are wrong."** A structural test, not a judgement call:
   a candidate needing cross-run state, a new config knob, semantic correctness judgement, or a new
   skill **does not fit and must not be built**. Reaching for a complex rule is the signal that the
   candidate does not belong here at all — not a signal to write it carefully.

## 5. Output

**Each run gets a finding document** at `findings/PR-{n}.md`. The per-document section contract lives
in [`findings/README.md`](findings/README.md), which defers to this file for every rule.

**Detector batches**: the first is staged as `PLAN-PR-012`. Later batches accumulate against this file
and stage when worth a plan — **never one plan per detector**.

## 6. ⛔ The per-run finding-document route has LAPSED — reopen it before appending to it

§ 5 requires a finding document at `findings/PR-{n}.md` per run, and that document IS the detector
accumulation list. **Derived 2026-09-18**: every populated one is from the `#1055`–`#1067` era
(`PR-1055.md` three YES rows, `PR-1058.md` one, `PR-1067.md` the WIDEN row that produced § 3's fourth
answer shape, `PR-1059.md` one deliberate NOT-a-candidate). `PLAN-PR-012` shipped 2026-08-13 as `#1204`
and consumed that backlog; **no `findings/PR-{n}.md` exists for any PR above #1067** — zero candidates
appended in roughly 400 PRs. The three later documents in `findings/` are bot-comparison corpus passes
and carry no back-feed column (`back-feed`, `_detect_`, `detector`, "Could we have found" → 0 hits).

⇒ **The epic kept measuring reviewers and stopped back-feeding them.** The obligation is not retired;
it lapsed silently. Reopening it is the precondition for the second detector batch, which already has
three inputs waiting (absorbed 2026-09-18, bodies in `archive/lessons/`):

| Input | The candidate class it asks for |
|---|---|
| `2026-08-27-16-004` | the Class-A predicate — *can this guard fail for the reason it exists?* — ported into the surfacer; 12 of 19 bot findings on one PR were this one archetype, and none of the 20 `_detect_*` functions is that check |
| `2026-08-27-16-006` | a closed-set literal sitting beside the named symbol that defines the same set; four of its five instances are not count-prose, so `PLAN-PR-062` D5's reach measurement does not reach them |
| `2026-09-04-08-011` | a claim falsified only by the ABSENCE of a mechanism — it has no second diff site, so a pair-scoped surfacer is structurally blind to it |

⛔ **`2026-09-04-08-011` needs an ADMISSIBILITY RULING before it is staged**, not an implementation:
§ 4 constraint 2 bars a candidate needing semantic-correctness judgement, and *"name the mechanism that
makes this claim true"* may be exactly that — yet CodeRabbit reached both of its instances through a
path-instruction of that shape, which is evidence the other way. Rule on it here first.

## 7. A review-pipeline detector defect found mid-run is CARRIED FORWARD, never fixed in the landing PR

The epic's most-exercised standing rule, in force but unwritten until 2026-09-18 (lesson
`2026-09-13-09-002`). When a run hits a defect in the review apparatus itself — a missed refusal
pattern, an unmatched ETA, a blind waiter — the finding is folded into the owning spec and the run
continues. Precedent: `landings/PLAN-PR-046.md` § Reconciliation action 3 folded two detector defects
into `PLAN-PR-057` D10 and `PLAN-PR-056` D8; `landings/PLAN-PR-033.md` did the same.

⛔ **The reason is economic, and it is this epic's own argument for fixing the rate window:** a
CodeRabbit round is a contended, hour-long resource, so spending one on a defect in the instrument
**selects which defects get fixed** and prices out precisely the review-apparatus defects this epic
exists to close. Fixing in place also changes the instrument mid-measurement.

## 8. Two verdicts per finding, and the triager owes both

A finding's **diagnosis** and its **proposed resolution** are separately falsifiable (lesson
`2026-09-03-16-001`). Rule on each against the primary source walked to its root — a correct diagnosis
licenses no fix, and a reviewer reading a parent POM while the binding sits in the grandparent, or a
roster label that classifies a STEP while the document places its sub-steps individually, is right
about the symptom and wrong about the site. ⛔ **The same obligation runs onto the triager's own claim**:
a dismissal resting on a recalled rule has been shipped as production text. Three repositories
independently reached the same two-field split (`fix_correct` / `premise_verified`).

Two consequences carried from the absorbed lessons:

- **A coarse classification never licenses a fine-grained conclusion** (`2026-09-15-06-001`, retired as
  a duplicate of the above). Its cost datum is why this section exists: **8 loop-back rounds** spent
  adjudicating a refuted premise, with the identical finding recurring as a second rejected one.
- **Write a guard's test from its PURPOSE, with a matched negative control** (`2026-08-31-08-002`,
  retired as stale — the instance shipped, the rule did not). A guard whose tests were authored from its
  implementation cannot report that its purpose is unmet, and a guard firing about the very subject the
  run is changing is a first-class self-review candidate.

## 9. ⛔ Rewriting a guard's claim to match its narrower reality is a DEFERRAL

From lesson `2026-09-13-20-006`. When the proposed remedy for a finding is *"document the gap"*, ask
who closes it and when. If the honest answer is *"a reviewer, on this same PR"*, close it now — the
narrowed claim hands the close to the next round, and the same gap on `bot_registry.py`'s marker-shape
sweep billed **two** rate-limited review rounds across two axes (`0f4db5` BOT, `d9e200` SHAPE). The
instance feeds `PLAN-PR-058` D0's anchoring decision.

## 10. A remediation acts on the SITE POPULATION a finding's claim spans, not on the reported line

From inbox `truthful-signals-059.md` (drained 2026-09-18), measured on PR #1501: **2 of 3 CodeRabbit
rounds re-found residue of the immediately preceding remediation.** Round 2's miss was one
`architecture search --content` away — the sibling site the previous fix did not sweep; round 3's was a
vacuity inside the guard round 2 had just added to close a vacuity.

⛔ Two rules, both cheap, both skipped on that run:

1. **Enumerate before closing.** A finding's claim usually spans a population; fixing the reported line
   closes the comment, not the claim. Sweep for the population and say what it was.
2. **A guard added in response to a finding carries a control proving it reddens** on the defect it
   closes. Without it the next round finds the guard.

⭐ **The economics are why this sits in the practice rather than in a plan**: an in-house round costs
tokens, an external round costs a rate-limited hour and can burn one of ten unattended waits. A round
spent re-finding our own residue is the most expensive kind of round this epic buys.

## Corrections already applied — do not reintroduce

This procedure was got wrong twice on the day it was written. Both discarded versions are named so they
do not creep back:

1. **Overbuilt.** A three-bucket sort, a separate refusing-bot coverage confound, and a
   precision-versus-yield argument. All discarded — they were compensating logic around a filter that
   already worked.
2. **Keyed off internal ledger state** (`fixed` / `accepted` / …) instead of the posted answer. That
   version would additionally have dropped unanswered findings as noise, which is the exact inversion
   of § 2's missing-answer rule.

## Promotion candidate — not yet

This practice is **project-general, not epic-specific**, so its eventual home is the marketplace rather
than one epic's tree. ⛔ **It is deliberately NOT promoted yet**: it changed three times on its first
day, and promoting a churning contract into a bundle means a plan per correction. **Trigger for
promotion**: the practice survives ~3 consecutive run batches without a rule change — then stage a plan
to move it, since a marketplace edit is repository source and therefore plan work, never an orchestrator
edit.
