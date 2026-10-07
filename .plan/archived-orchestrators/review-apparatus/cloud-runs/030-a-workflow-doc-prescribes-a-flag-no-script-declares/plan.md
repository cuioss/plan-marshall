> ⛔ **FIRST INSTRUCTION — do not skip, do not delete, do not move below the title.**
>
> Before reading the rest of this plan and before any other action, load the working contract that
> governs this run:
>
> ```text
> Skill: cloud-plan-lane
> ```
>
> It owns the branch/PR/review-comment cycle, the build gate, the pre-PR verification sub-agent, the
> run report, and the closing self-check. **Nothing in this plan overrides it** — where this plan and
> the contract disagree, the contract wins, and the disagreement is reported.
>
> If the skill cannot be loaded, **stop and report the run blocked**. Do not reconstruct the workflow
> from this file: the parts that matter most — the merge gate, the verification dispatch, the report
> — are not in here.
>
> This block is part of the plan, not part of the template. It survives into every copy.

# A prescribed invocation is executable state, and a rejected one is swallowed inside the step that judges whether a PR was reviewed

**Epic:** review-apparatus
**Branch prefix:** fix

## Problem

A workflow doc prescribes CLI flags that the scripts it invokes do not declare. A dispatched leaf that
obeys the standing "no improvisation" rule and quotes the doc verbatim is therefore **guaranteed to
fail**:

```
github_pr.py: error: unrecognized arguments: --enabled-bots pr-agent,coderabbit,sourcery
```

⭐⭐ **Obedience is the failure mode.** The standing mitigation for CLI errors is *quote the doc, never
invent a verb* — and that mitigation is inverted here, because the doc is the thing that is wrong.

⛔ **But the doc drift is the instance, not the defect.** Ninety seconds after that rejection, the same
dispatch reported `[STATUS] Complete`, `outcome=done`,
`display_detail: "1 comment(s) found (unified triage pending)"`. **The non-zero exit was swallowed**,
inside the step whose entire job is to establish which bots participated — and the rejected flag was
the one scoping *which bots the fetch considers*.

The sharpest single observation, three consecutive lines of one work log:

```
13:41:01 [ERROR] script_failure notation=…:ci exit_code=2 failure_kind=argparse_rejection
                 ci.py: error: unrecognized arguments: --pr-number 1085
13:42:59 [ERROR] script_failure notation=…:github_pr exit_code=2 failure_kind=argparse_rejection
                 github_pr.py: error: unrecognized arguments: --enabled-bots …
13:43:32 [INFO]  Pre-merge comment barrier: clean - zero pending pr-comment findings, proceeding to
                 merge. Re-fetch stored 0 findings, … participated_bots=none
```

⛔⛔ `participated_bots=none` and *"clean … proceeding to merge"* are **33 seconds apart in the same
log.** The barrier reported clean from a fetch argparse had rejected, and the zero it read as *"no
pending findings"* was the zero of **a command that never ran**. Note also that the two rejections have
**opposite causes** — one caller was wrong, the other caller was right and the surface was missing —
which is the argument for fixing the swallow rather than the flags, in the sharpest available form.

**There are four distinct cause classes, and a docs-only fix closes only one of them:**

| Class | Example | Where the fault lives |
|---|---|---|
| Flag does not exist | `--enabled-bots` | the doc prescribes it |
| Flag exists but **position** is wrong | `--plan-id` after the verb instead of before it | the envelope contract prescribes it universally |
| Value **shape** accepted and misparsed | bare bot names where `bot_kind:evidence_kind` pairs are required | no value-shape validation |
| Empty value dropped by the harness | `--in-progress-bots ""` — the executor drops the empty value, argparse sees a flag with no argument | the harness, not the caller or the doc |

⭐⭐ **The third class is the worst, and it is the inverse of a swallow.** Argparse said **yes**.
Nothing was rejected, so there was nothing to swallow — the surface accepted a malformed value and
manufactured a **confident, fully-populated fiction**: an all-absent verdict over a population it never
evaluated. And the two flags **disagree with each other** (`--participated-bots` wants pairs,
`--stale-participation-bots` wants bare kinds) while **the producer emits pairs for both**, so a caller
forwarding the producer's output gets the wrong form for one of them **by construction**.

⭐ **The second class has a named root, and it is a contract, not a doc.** The `execution-context`
prompt-body contract states that *"every script call inside this envelope forwards `--plan-id
{plan_id}`."* Read as written that is a **universal quantifier over script calls, and it is false in
three ways at once**: some scripts take the flag only top-level, some do not take it at all, and some
take the plan id as a value under a verb that must come first.

## Goal

A script invocation that fails — by rejection, by misposition, or by a value the surface accepts and
misreads — fails the step that made it, visibly, instead of being absorbed into a green result. The
prescribed invocations in the review-and-merge path parse against the parsers they name, and the
envelope contract no longer states a universal that is false for a known subset of the script surface.

## Deliverables

Four. ⛔ Split rather than adding a fifth.

1. **D0 — PRIMARY, and a gating derivation: enforce the exit-code convention inside dispatched
   review-and-merge step bodies.** A non-zero exit from any script call must fail the step.
   ⛔ **Derive the population.** It is *every script invocation reachable in the finalize
   merge-and-review path* — not the sites named in this plan, and not one step body. Observed instances
   already span **three notations** and reach `ci.py` and the pre-merge barrier, which are outside
   `automatic-review` entirely.
   ⛔ **This deliverable HALTS the plan if the population cannot be derived** from the tree. Do not
   hand-maintain a list of call sites: a curated list is exactly the artifact this plan exists to
   retire — this epic has twice been bitten by *a list of call sites is a sample, not an enumeration*.
   ⛔ **D0's framing must not narrow to "surface the swallowed rejection".** That closes three classes
   and leaves the accepted-but-misparsed class untouched, because there is no rejection to surface.
   The population is *caller-supplied values the surface accepts and misinterprets* **alongside** the
   ones it rejects silently.
   *Done when:* the population is derived and stated with its derivation method, and a rejected call in
   any member site fails its step, proven by a test that passes today and fails after.

2. **D1 — a malformed value is REJECTED, not silently reinterpreted.** A bare bot name passed where a
   `bot_kind:evidence_kind` pair is required must be rejected as malformed. ⛔ **It must never resolve
   to `absent`**, which is a *blocking* member — that makes the defect silent **and**
   polarity-selecting, manufacturing a confident false merge block attributed to a bot that in fact
   participated.
   Include **flag-set internal consistency**, not only per-flag shape: either the two flags take the
   same token form, or an unparseable token is rejected loudly. *A parse that cannot round-trip its
   input must not resolve to a blocking state by default.*
   *Done when:* both directions are tested — a pair fed to the bare-form flag, and a bare kind fed to
   the pair-form flag — and each is a visible caller error rather than an `absent` verdict.

3. **D2 — reconcile the prescribed invocations to the live surfaces, semantically.** Diff every
   prescribed invocation in the review-and-merge surface against its script's live argparse, and fix
   the divergences.
   ⚠ **Not a rename.** The two vocabularies model different things: `enabled` is one undifferentiated
   set, while `required`/`optional` is a **gating classification**. A mechanical rename produces a doc
   that parses and still misinstructs. Same for the return fields (`complete` / `unfetched_bots` versus
   `participation_complete` / `unproven_bots` / `bot_states`).
   Include the envelope contract itself: the universal `--plan-id` claim must be replaced by something
   true per-script and per-position. **That contract is the primary fix site for the position class —
   not any `## Canonical invocations` block.**
   *Done when:* every prescribed invocation in the derived population parses against its own parser.

4. **D3 — a population-derived test that fails when a documented invocation does not parse.**
   ⛔ The population is derived from the docs **at run time**, and **non-emptiness is asserted first** —
   this epic has been bitten by set-guards that pass having examined nothing. Copy the derivation
   pattern from `test/_shared/_dispatch_roster.py`.
   *Done when:* the test exists, its population size is published in its own output, and it fails
   against a deliberately reintroduced divergence.

## Out of scope

- **The executor's `detail=` truncation.** The wrapper truncates from the tail while argparse prints
  its actionable `error:` line last, so all four occurrences of one rejection cut off at `error: a` —
  the diagnostic elision is why this went undiagnosed for two days. ⛔ **Do not absorb it.** It is
  staged as a separate plan in another epic; their fix does not fix ours and ours does not fix theirs.
  ⭐ Worth knowing while working: *if you cannot see why a dispatched rejection happened, suspect the
  truncation before suspecting the caller.*
- **Building a second consumer for degraded-input signals.** Another staged plan in this epic owns
  turning a recorded-but-unread signal into a gate input. If D0 needs one, **coordinate through the run
  report rather than building a parallel consumer** — two consumers for one distinction is the
  duplication this epic exists to fix.
- **Adding prose that restates the exit-code convention.** `phase-6-finalize`'s convention *already*
  forbids this — *"silent swallowing of `wrong_parameters` rejections is the prohibited anti-pattern;
  'log and continue' is equally forbidden"* — and it did not prevent any of the observed instances. The
  fix is **enforcement**; a plan that only adds prose reproduces the defect.
- **Any change to a repository other than this one.**

## Expected surface

⚠ Every entry is a **floor, not the extent** — D0's derivation sets the real population.

- `marketplace/bundles/plan-marshall/skills/automatic-review/scripts/review_completeness.py` — the
  `--participated-bots` / `--in-progress-bots` / `--stale-participation-bots` parse and the exit path.
- `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_pr.py` — the
  `fetch_findings` call surface.
- `marketplace/bundles/plan-marshall/skills/tools-integration-ci/scripts/ci.py` and `ci_base.py` — the
  swallowed-rejection site at the router/provider boundary.
- `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/branch-cleanup.md` — the
  pre-merge barrier, the fourth observed site.
- `marketplace/bundles/plan-marshall/skills/automatic-review/SKILL.md` and
  `workflow-integration-github/SKILL.md` — the invocation blocks and the surviving `enabled_bots`
  frontmatter key.
- The `execution-context` prompt-body contract — the false `--plan-id` universal.
- ⚠ **Four of these were modified by a recent merged PR.** **Re-ground every line reference against
  merged `main`**; treat any number in this plan as stale until re-read.

## Claim labels

| Claim | Label | Confirm/refute artifact |
|---|---|---|
| A prescribed `--enabled-bots` is rejected by the live parser | OBSERVED | `github_pr.py`'s argparse table for `fetch_findings` versus the invocation block in `automatic-review/SKILL.md` |
| The rejection is swallowed and the step reports `done` | OBSERVED | The step body's handling of a non-zero script exit — read the call site, not the convention doc |
| A bare bot name where a pair is required yields an all-absent verdict rather than an error | OBSERVED | The `--participated-bots` parse site and its `bot_kind:evidence_kind` split — read the parse, not the help string |
| The two flags require **different** token forms while the producer emits pairs for both | OBSERVED | The two argparse declarations plus the producer's emission site |
| `--in-progress-bots ""` is dropped by the executor so argparse sees a flag with no argument, while omitting the flag works | OBSERVED | The executor's argument marshalling — reproduce it once before building on it |
| The population extends beyond the sites named here, across the whole finalize merge-and-review path | HYPOTHESIS | D0's derivation **is** this test. ⭐ A null result is a valid, publishable outcome — report it rather than padding the list |
| A prior shipped remedy wired an UNKNOWN-verdict branch to `review_completeness` but **not** to its siblings in the same step body | HYPOTHESIS | Read the UNKNOWN-verdict wiring at `review_completeness` and check whether the same guard covers the other calls in that body. ⛔ **The discriminating question, and it changes the plan's size**: if the guard is present *and still did not catch a rejection at that very site*, this plan is a **repair of a shipped fix**, not an extension of it. ⚠ **Do not assume the smaller reading because it is smaller** — this epic's recorded failure mode is preferring the attractive hypothesis |
| Some *consumer* silently tolerates the old field names (reads `complete`, gets `None`) | HYPOTHESIS | Enumerate the readers of the renamed return fields. A doc fix would not repair this — check before closing |

⚠ **Every count here is a lead**: three notations, five instances, four cause classes, four rejections
in one run. All are observations from past runs. **Re-derive anything you assert.**

⛔ **Do not go looking for `.plan/`.** The work logs, inbox messages, and landing records behind these
observations are git-ignored and **absent from your clone**. Everything needed is restated above.

## Verification

- Run the repository's full verify and read the payload's `status` / `errors[]` — the wrapper exits 0
  even on failure, which is the same class of defect this plan is about.
- **Every test proven to fail pre-fix by mutation.** For D0 in particular: reintroduce a rejected
  invocation and confirm the step now fails where it previously reported `done`.
- **D3's population size is published in the test output**, so a future reader can tell a passing test
  from an empty one.
- ⭐ **Cold read, and aim it at the envelope contract.** D2 rewrites the `--plan-id` universal. Have the
  pre-PR verification sub-agent read the new contract text **cold** and answer: *for a script that
  accepts `--plan-id` only before its verb, what does this text tell me to do?* If the cold reading
  still produces a post-verb invocation, the wording failed. Report the reading verbatim.
- ⚠ **Check for the endorsement trap while fixing.** When argparse rejects a flag that *is* declared on
  an ancestor parser, the usage banner advertises the flag immediately above the error — so a fixer
  reads the flag as endorsed and reaches for a different name instead of moving it left of the verb.
  If D0's work touches the rejection reporting, emit a distinguishing hint (*"declared on the top-level
  parser; place it before the subcommand"*). The wrapper already classifies
  `failure_kind=argparse_rejection` and holds both the rejected token and the parser's declared set.

## Notes

- **Sequencing — this plan shares files with several others in the epic. Sequence, never pair.**
  `branch-cleanup.md` is shared with two other staged plans; `github_pr.py` with three;
  `review_completeness.py` with one. ⚠ It also **crosses the CI verb surface** with another staged plan
  that derives a population over the same surface — **if the two derivations turn out to be the same
  population viewed differently, say so rather than shipping two.**
- **Severity is set by what was gating, not by the exit code.** In one affected run a review bot set a
  SUCCESS commit status **one second after posting "we couldn't start this review"**, and the quorum
  check that should have caught exactly that was inert. Two independent layers of one gate failed
  silently in a single plan, and a green merge signal stood on nothing.
- **The blast radius argument, stated precisely.** In the first observed instance the outcome was still
  correct: the barrier blocked the merge and forced another iteration. But it got there by
  **re-deriving participation independently**. ⛔ A defence that holds only because a downstream check
  re-does the work is not a defence — it is a redundancy that someone will optimise away, or that will
  fail the first time the downstream check is skipped.
- **A documented recurrence signature still recurred inside a dispatch.** The post-verb `--plan-id`
  form is already named in the agent persona's *"never invent script subcommands"* guidance, and the
  structural guard governs *authored* invocations in skill bodies — **not invocations an agent composes
  at runtime.** That gap is precisely what D0 must close.
- **A defect recorded under a plausible-but-wrong cause is worse than an unrecorded one**, because it
  looks owned. One half of this corpus had been attributed to *"derived participation from the wrong
  oracle"*; the truer cause is the swallowed rejection.
