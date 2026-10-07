# Epic audit report — truthful-signals (run 01)

**Date (UTC):** 2026-08-18    **Branch:** `claude/truthful-signals-verification-051sba`    **PR:** [#1298](https://github.com/cuioss/plan-marshall/pull/1298)    **Outcome:** completed

## Scope, and one deviation from the contract's report path

This run executed an operator brief, not a `plan.md`: analyse the epic, verify every landed plan
against ground truth, adversarially review the results, then compile gap-fix plans. There is
therefore no plan directory of its own, and `cloud-plan-lane` § Report's path
`doc/plans/{epic}/{plan-name}/report-NN.md` has no plan name to resolve. This report is placed at the
epic root instead. That is a deviation, recorded here rather than glossed: the contract assumes a run
executes one authored plan, and this one did not.

The Step 8 Bridge rule — write no status or bookkeeping outside the run's own plan directory — was
otherwise honoured. The `verification.md` / `gaps.md` files written into each of the 44 plan
directories are **deliverables of the brief**, not status records, and no ledger, status file, or
other epic was touched.

## Skills loaded

| Skill | Route | Why |
|---|---|---|
| `cloud-plan-lane` | `.claude/skills/cloud-plan-lane/SKILL.md` | The working contract, loaded as the run's first action |
| `author-cloud-plan` | `.claude/skills/author-cloud-plan/SKILL.md` | Phase C — the authoring judgement for the ten new plans |
| `doc/plans/cloud-bridge.md` § Path 1 | path | The plan-naming mechanics the authoring skill points to |

Not loaded, deliberately: `ref-code-quality`, `plugin-script-architecture`, `python-core`,
`pytest-testing`, `plugin-architecture`, `ref-asciidoc`, `persona-implementer`. The deliverables are
Markdown documents under `doc/plans/`; this run changed no production code, no test, no `SKILL.md`
and no `.adoc`. Every skill named above was obtainable by path; none had to be reported unavailable.

## Deliverables

### D1 — epic-level analysis

`doc/plans/truthful-signals/README.md` read first: the epic's theme is a tool, gate or hand-off
reporting a confident clean signal while suppressing the caveat that makes it wrong, plus the
adjacent family in which machinery silently loses information it was handed. That theme is what the
verification was aimed at, and it is what the findings overwhelmingly turned out to be.

Population: **44** plan directories (`030`–`460`; there is no `400`), each holding `plan.md` and
`report-01.md`. Re-derive this count at the moment of any claim about it.

### D2 — per-plan ground-truth verification (44 of 44)

One independent agent per plan. Each read `plan.md` and `report-01.md`, located the landed commit
from the PR number, read the diff that actually landed, then checked every deliverable against HEAD
on four axes — implemented at all, implemented as documented, implemented correctly, implemented
completely — plus report accuracy, out-of-scope compliance, and the residue the report itself
declared.

Verification was not confined to reading. Agents ran single test files through `uv`, executed
functions whose return value a plan asserted something about, reconstructed pre-fix trees with
`git archive` to reproduce published figures, and mutated new guards to confirm they go red against
the defect they name — restoring from byte snapshots taken before mutating, never with a git command.

Written to `{plan}/verification.md` and `{plan}/gaps.md` in each of the 44 directories.

### D3 — adversarial review (44 of 44)

A second, clean agent per plan, told to assume both documents were wrong until the tree said
otherwise. It hunted false positives, rationale asserted but never checked, deliverables passed too
easily, mis-severity, unactionable fixes, and verdicts the rows did not support; re-ran every "swept
the tree, clean" claim with a broader pattern than the original; and re-derived every figure.

It corrected both documents in place and appended an `## Adversarial review` section naming what it
re-checked and what it did not. Refuted gaps are moved to a `## Refuted during adversarial review`
section with the evidence that refuted them, never deleted — a dismissed finding is still evidence.

All 44 `verification.md` files carry that section.

### D4 — ten gap-fix plans, numbered from 500

All 283 surviving gaps grouped by module/skill/topic, authored per `author-cloud-plan`:

| Plan | Scope | Gaps | Deliverables |
|---|---|---|---|
| `500` | plugin-doctor detectors reporting clean over unexamined populations | 29 | 8 |
| `510` | finalize step contract, ordering, re-fire currency | 41 | 8 |
| `520` | orchestrator inbox lifecycle, cleanup, landing payload | 31 | 8 |
| `530` | manage-config seeding, effort presets, steward upgrade flow | 34 | 8 |
| `540` | build gates, test-suite confidence, CI workflow lint | 31 | 8 |
| `550` | metrics, ledger readers, timestamp provenance | 24 | 9 |
| `560` | planning lane, change-type scope, execution manifest | 22 | 8 |
| `570` | git artifact scanning, destructive recovery prose | 17 | 8 |
| `580` | agent-facing documentation surfaces | 30 | 8 |
| `590` | cloud-plan-lane contract and run-report accuracy | 24 | 8 |

Numbering starts at `500` per the operator's instruction and continues sparse-in-tens per
`cloud-bridge.md` § Path 1, leaving room to insert between the audit's plans and the epic's existing
`030`–`460` queue.

**Coverage was checked mechanically, not asserted.** Every gap id was extracted from every `gaps.md`
(excluding refuted entries) and matched against the ten plans: **275 owned by exactly one
deliverable, 8 named under a plan's Out of scope with a reason, 0 owned twice, 0 unaccounted.** The
eight scoped out are `030/G1`, `230/G3`, `230/G4`, `250/G4`, `302/G5`, `302/G7`, `410/G2`, `440/G4` —
each excluded because its substrate is git-ignored `.plan/` state, or it needs a measurement no clone
can take, or it is bidirectionally coupled to a gap that cannot land alone.

Every author re-grounded its full gap set at HEAD before planning a fix. **None was found
already-closed** — every recorded defect still reproduces.

## Findings

### What the verification found

| Verdict | Plans |
|---|---|
| fully-implemented | 2 |
| implemented-with-gaps | 35 |
| partially-implemented | 7 |

**283 open gaps: 42 high, 142 medium, 99 low**, plus 7 refuted and recorded.

The dominant pattern is not missing implementation. The substance of these plans almost always
landed; what did not is the machinery that protects it:

- **Guards that pass against the defect they name.** A test whose expectation is computed by the very
  function whose blind spot it exists to detect; a whitelist keyed on whole files so the write-path
  leak it guards stays green; a population sweep with no non-vacuity floor, green over zero matches.
- **Sweeps stopped at the site the plan pointed at.** A claim corrected at one of four surfaces, with
  the other three left standing — and in several cases the missed surface was in a file the same
  commit had already edited.
- **Premises asserted rather than checked.** Several plans reasoned that a file was "git-ignored and
  absent from the clone" when `.gitignore` re-includes it and it is tracked; one declared a whole
  verification step impossible that turned out to be one command away.
- **Rationale invented to explain a fix.** Docstrings and reports asserting a mechanism — "rejected
  by X", "unreachable because Y" — that the named symbol does not implement.

### What the adversarial pass changed

The second pass was not a formality. It corrected verdicts in both directions: three plans initially
recorded `fully-implemented` were downgraded when a clean-pass row turned out to carry a false
negative, and several gaps were downgraded or refuted outright when their stated mechanism did not
survive execution. It also caught defects in the *fixes being proposed* — one gap's remedy named a
verb that does not exist; another would have shipped a fresh incorrect example because the
discriminator it relied on has two conjuncts, not one.

Only **one** of the initial `fully-implemented` verdicts survived adversarial review intact.

### Findings against this run's own process

- **Shared-working-tree contention.** 20 agents mutation-testing in one checkout raced: an agent
  could snapshot a file another had already mutated and "restore" it to a corrupted state. Caught
  early, and closed by requiring `git diff --quiet -- <path>` before mutating and skipping the file
  when it is already dirty. Two agents also wrote scratch probe files into the repository; both were
  removed, and later dispatches were told to use `$TMPDIR`. **Disposition: fixed.**
- **The report-path deviation** recorded at the top of this document. **Disposition: recorded, not
  fixed** — there is no correct path for a run with no plan.

### Stop record

The loop ended on the **verifier exit**: an independent pre-PR verification sub-agent (§ Step 6) was
dispatched over the finished work and its answer to the stop question is recorded in the Contract
check below. The budget that applied was the default **five** rounds; **one** round ran. No extension
was needed and none was requested, so no operator boundary question arose.

The evidence the stop rests on is stronger than a re-read: coverage was re-derived mechanically from
the files rather than trusted (283 gap ids extracted and matched, yielding the 275/8/0/0 partition),
the 44 × 2 document population was recounted from the filesystem, and the build-gate predicate was
computed from `git diff` rather than recalled.

**Residue to assume remains.** These deliverables should be read as still carrying defects of the
kind the last round found — principally in the ten new plans, which are young, unreviewed prose that
no adversarial pass has yet been run against. The 44 verification pairs have had two passes; the ten
plans have had one author and one verification sub-agent. Their deliverable groupings, and every
count inside them, are the highest-risk text in this diff.

**Survivors:** none. No behavioural finding was left open — this run changed no behaviour.

## Reviewer participation

Expected reviewer population **derived from configuration**, by reading the `author_login` of each
registry doc under `marketplace/bundles/plan-marshall/skills/automatic-review/standards/`. Verdicts
are taken from the stored comment bodies across all three surfaces (`get_comments`, `get_reviews`,
`get_review_comments`), not from a check state:

| Reviewer (`author_login`) | Verdict | Reopens? | Body evidence / reason |
|---|---|---|---|
| `cuioss-review-bot` | `reviewed` | — | Issue comment "PR Reviewer Guide 🔍" against the diff: *No relevant tests · No security concerns identified · No major issues detected*. A review artifact with an explicit nothing-to-report verdict |
| `coderabbitai` | `rate-limited` | yes | Issue comment: *"Review skipped — Auto reviews are limited based on label configuration. Excluded labels (none allowed): `skip-bot-review`"*. It engaged and declined; the notice carries a retry checkbox and names `@coderabbitai review` as the manual trigger, so the refusal clears on demand |
| `sourcery-ai` | `rate-limited` | **no** | Review summary body: *"your pull request is larger than the review limit of 150000 diff characters"*. A property of this diff's size, not of the clock — the diff is an order of magnitude past that ceiling, so the same request never succeeds and waiting is futile |

Coverage: **1 of 3 reviewed.** Inline review threads: zero (`get_review_comments` returned an empty
set, `totalCount: 0`) — a genuine empty read, not an unreadable surface. No comment required action:
two are refusal notices and the third reports no findings.

⚠ **This table corrects an earlier draft of this report**, which recorded all three as "not requested"
on the assumption that `skip-bot-review` suppresses the reviewers outright. It does not. The label
suppresses `coderabbitai` (which says so in its own notice) and the `Sourcery review` check concluded
`skipped`, but `cuioss-review-bot` reviewed anyway and `sourcery-ai` posted a size-ceiling refusal.
The draft was a prediction of reviewer behaviour written before the bodies were read — the precise
defect this epic files against, committed in this report's own participation record. It is corrected
here rather than silently overwritten.

**§ Step 8 condition 4 disclosure fired**, and it said: *review coverage 1 of 3 — `cuioss-review-bot`
reviewed with no findings; `coderabbitai` declined on the `skip-bot-review` label, reopens on demand;
`sourcery-ai` refused on a 150,000-character size ceiling, does not reopen.* The shortfall is
disclosed, not blocked on — condition 4 changes what the run says, never whether it merges.

## Build gate

`git diff --name-only origin/main...HEAD -- '*.py'` → **zero files**. No buildable footprint; the
local build was skipped per § Step 5. The working tree was confirmed clean before the diff was taken,
so the read covers committed work with nothing invisible to it. The merge queue's `merge_group` run
verifies docs-only changes before they land.

## Cost

- **Tokens:** not available to the agent in this session.
- **Wall-clock:** the run's first and last commits are 2026-08-18T14:12:25Z and 2026-08-18T16:05:29Z
  — roughly 1 h 53 min, source: `git log --format=%ad`. This excludes the pre-commit analysis phase.
- **Agents dispatched:** 44 verification + 44 adversarial + 10 authoring + 1 pre-PR verification = 99.
- **Population:** this single Claude Code cloud session's dispatch tree, as the session counts it.
  ⛔ **Not comparable to a plan-marshall `metrics.toon` total**, which counts an
  orchestrator-plus-agent tree under plan-marshall's own per-task billing boundary — a boundary an
  interactive cloud session does not share. The figures are not made comparable here, and no
  comparison should be drawn from them.

## Residue

- **The ten new plans are unexecuted and unreviewed.** They are the deliverable most likely to carry
  defects, for the reason given under Stop record.
- **Eight gaps are scoped out of every plan**, listed under D4 with their reasons. Each needs either
  a local run with `.plan/` state present, or a decision this lane cannot make.
- **Cross-plan file contention.** Several authors flagged that their deliverables share files with
  sibling plans — `510`/`520` on the finalize and landing documents, `530`/`580` on the steward
  surfaces, `540`/`550` on the ledger readers. Executing two of these concurrently will conflict; the
  operator should sequence them rather than fan them out.
- **`590` writes into sibling plan directories**, which the Bridge rule forbids literally. Its author
  pre-authorised the excursion in the plan text and recorded a wording proposal for the contract, but
  a run reading § Step 8 Bridge strictly could stall there. Worth resolving before that plan is
  handed over.

## Pre-PR verification sub-agent (Step 6)

One round ran, over the finished work. Its per-item verdicts: epic coverage PASS (44/44 directories,
all four files each), adversarial-review presence PASS (all 44, smallest section 1,121 words, each
naming file-path and line citations rather than asserting a clean result), gap→plan coverage PASS
(283 ids extracted, 0 uncovered, no genuine double-ownership), plan conformance PASS (all ten
byte-identical to the template's first-instruction block, all sections present, prefixes valid,
deliverable count equal to *Done when:* count), `author-cloud-plan` seven-rule self-check PASS,
documentation standards PASS, no collateral change PASS.

It then spot-checked the three highest-severity gaps it could find by opening each at HEAD:
`302/G1` (`'n/a'` is truthy, so a landing that transmitted nothing reads complete), `380/G1`
(`total = passed + failed + skipped`, so a run where no test body executed clears a `test-failure`
finding), and `320/G1` (an `OSError` comparison returns `scanned=0`, and `partial` is `0 < 0` —
false, so a comparison that read nothing renders clean). **All three reproduce**; none is a false
finding.

**It returned BLOCKED on three numeric claims**, and condition **A** forbids leaving a false statement
open. Each was re-derived independently before being acted on, which changed the disposition of two:

| # | Finding | Disposition |
|---|---|---|
| F1 | Plan `510` claims 41 gaps while its `closes` annotations name 36 | **Refuted.** 36 closed + 5 named under Out of scope = 41, and the source set is twelve directories as stated. The verifier counted `closes` annotations without the Out-of-scope entries. No edit. |
| F2 | Plan `520` claims "31 gap ids from the six source `gaps.md` files" | **Partly upheld, fixed.** 31 is correct (30 closed + 1 excluded); the source set is **seven** directories, not six. Corrected, and the 30/1 split made explicit. |
| F3 | Plan `590` claims "24 ids" from "ten source `gaps.md`" | **Partly upheld, fixed.** 24 is correct (22 closed + 2 excluded); the source set is **twelve** directories. Its separate "ten reports edited" claim is correct and was left alone. |

**F3's fix demonstrated the epic's own defect.** The first pass corrected three sites and left a
fourth — "no dependency on the ten source plans" — standing 130 lines further down. It was caught only
because the fix was followed by a re-sweep for the claim rather than for the sites the finding named.
That is the n−1-of-n failure this epic exists to file, committed inside the audit of it, and it is
recorded here rather than quietly repaired.

**Stop record.** The loop ended on the **verifier exit**, at round 1 of a default budget of five; no
extension was needed and no operator boundary question arose. The verifier's own last answer was that
F1–F3 remained and condition A forbade leaving them; all three were adjudicated and the two genuine
ones fixed, so nothing A governs is left open. Condition **B** is not engaged: this run changed no
behaviour, so there is no behavioural finding to characterise, and there are **no survivors**.

The evidence the stop rests on is stronger than a re-read — coverage re-derived mechanically from the
files (283 ids matched into a 275/8/0/0 partition), the document population recounted from the
filesystem, the build-gate predicate computed from `git diff`, and three gaps re-executed at their
named symbols.

**What the verifier did not check**, in its own words: no build run (documentation-only diff); it did
not verify that all 283 gaps reproduce, only three plus incidental confirmations; it did not re-audit
each `verification.md` against its source `plan.md`/`report-01.md`; its cold-read check was structural
rather than semantic; and it did not check this PR's CI status.

## Contract check (Step 9)

| Step | Verdict | Artifact |
|---|---|---|
| 1 Skills loaded | done | Named under § Skills loaded, with the deliberate omissions and their reason |
| 2 Branch | done | `claude/truthful-signals-verification-051sba` — the **harness-assigned** form, kept as-is per § Step 2; pushed to `origin` before the first edit |
| 3 Plan directory | **n/a** | No `plan.md` was handed to this run; the operator's brief is the plan. Recorded as a deviation at the top of this report rather than narrated as complete |
| 4 Implement | done | 85 commits, each carrying the `Co-Authored-By` trailer, no "Generated with Claude Code" footer |
| 4 Per-commit gate | **n/a** | No commit touched a `*.py`; the gate's trigger surface was never entered |
| 4 Pushed | done | Every commit pushed on creation; `git status -sb` reports no `ahead` |
| 5 Build gate | done | `git diff --name-only origin/main...HEAD -- '*.py'` → zero files; "no buildable footprint, build skipped" |
| 6 Verification sub-agent | done | Recorded in full above: findings, dispositions, the exit taken, the budget, the verifier's own last answer, and the residue to assume remains |
| 7 PR cycle | done | PR [#1298](https://github.com/cuioss/plan-marshall/pull/1298), `skip-bot-review` applied at creation. Participation table records the suppression as suppression, not as coverage |
| 8 Merge gate | done | Condition 1: every required context concluded on head `1c0b9864` — `verify / conclusion` **success**, `verify / gate` **success**, `dependency-review` **success**; `verify / verify` concluded `skipped` by the docs-only footprint gate, exactly as § Step 5 describes. Condition 2: all three comment surfaces read, no comment unaddressed. Condition 3: this report committed as the last pre-merge commit. Condition 4 disclosed under § Reviewer participation |
| 8 Bridge | done | No status or bookkeeping write landed outside this run's own artifacts. The `verification.md` / `gaps.md` pairs are deliverables of the brief; no ledger, no status file, no other epic touched. **One deviation:** this report sits at the epic root, for the reason given at the top |
| 9 This check | done | This table |
| 9 What have we learned | done | Below |

**Re-verified against the working tree, not recalled:** the tree is clean, the diff is 99 files all
under `doc/plans/truthful-signals/`, all additions (the insertion count is deliberately not stated: it
moves with every commit, including the one carrying this sentence), and no `*.py` appears in it. A cloud run neither performs nor
owes a `/sync-plugin-cache`; none is recorded.

## What have we learned (Step 9)

Two contract changes are proposed, both grounded in what this run actually hit. Neither is shipped
here — the lane forbids self-approving a change to the contract that governs the run, so these are
recorded for the operator and would ship as a separate `chore/` PR if accepted.

**1. The report path assumes a run has a plan.** § Report fixes the report at
`doc/plans/{epic}/{plan-name}/report-NN.md`. A run executing an operator brief across a whole epic —
as this one did — has no `{plan-name}`, so the path does not resolve and the run must improvise.
*Evidence:* this run wrote to the epic root and had to disclose the deviation. *Proposed edit:* add a
sentence to § Report stating that a run with no authored plan writes `report-NN.md`, or a named
equivalent, at the epic root, and reports the placement in its Contract check.

**2. Nothing in the contract governs a run that dispatches many agents into one working tree.**
§ Step 6 assumes a single verification sub-agent and tells it to restore mutations from a snapshot.
With agents mutating concurrently, that rule is actively unsafe: an agent can snapshot a file another
has already mutated and "restore" it to the corrupted state, and every red count measured afterwards
is meaningless. *Evidence:* observed early in this run — an agent reported `# MUTATION` markers left
by a sibling, and two agents wrote scratch probe files into the repository. *Proposed edit:* add to
§ Step 6 that where more than one agent may touch the tree, an agent checks `git diff --quiet -- <path>`
before mutating and skips a file that is already dirty, and that scratch belongs in `$TMPDIR`, never
in the repository.

A third candidate was considered and **rejected**: proposing that `skip-bot-review` be narrowed so
plans under `doc/plans/` keep their review. The label's rule is deliberately mechanical, this diff
genuinely matches it, and the argument for reviewing planning prose is an argument about *this* diff
rather than evidence that the rule is wrong. Recording it as a rejected candidate rather than a
proposal.
