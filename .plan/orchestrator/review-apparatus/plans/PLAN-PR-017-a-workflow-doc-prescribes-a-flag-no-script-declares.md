# PLAN-PR-017 — A workflow doc prescribes a flag no script declares

epic: review-apparatus · workstream: WS-03 · staged 2026-08-02 · **priority: emit-next candidate**

## Why this is now a plan and not a residue item

It was filed as residue of PLAN-PR-016 (`correct-review-scores-as-maximally-wrong-006`, explicitly
marked NOT fixed by #1078). It has since **hard-failed a plan in another epic**:

> `github_pr.py: error: unrecognized arguments: --enabled-bots pr-agent,coderabbit,sourcery`
> — PLAN-CIS-027's `automatic-review` leaf, PR #1079, following `automatic-review/SKILL.md` verbatim

⇒ Three independent sightings, escalating in severity: latent drift (PR-016 residue) → an orchestrator
hitting the same archetype on `ci pr view --pr-number` → **a live argparse rejection inside a dispatched
finalize step in a sibling epic.**

## ⭐⭐ The archetype — this is why it outranks an ordinary stale doc

**A leaf that obeys the "no improvisation" hard rule and quotes the doc verbatim is GUARANTEED to fail.**
The standing mitigation for CLI errors is *"quote the doc, never invent a verb"* — and that mitigation
is inverted here, because **the doc is the thing that is wrong**. Obedience is the failure mode.

⛔ Do not scope this as "update the docs". Scope it as: *a prescribed invocation in a workflow doc is
executable state, and nothing currently verifies it against the parser it invokes.*

## The divergence

| Site | Doc prescribes | Live argparse |
|---|---|---|
| `github_pr fetch_findings` | `--enabled-bots` | `--required-bots` / `--optional-bots` |
| `review_completeness check` | `--enabled-bots`, `--settled-bots` | `--required-bots`, `--optional-bots`, `--participated-bots`, `--in-progress-bots`, `--refused-bots` |
| `automatic-review` returns | `complete`, `unfetched_bots` | `participation_complete`, `unproven_bots`, `bot_states` |
| `ci pr view` help text | names `--pr-number` | `--head` only; `--pr-number` is exit 2 |

⚠ Not cosmetic: **the two vocabularies model different things.** `enabled` is one undifferentiated set;
`required`/`optional` is a gating classification. A mechanical rename would produce a doc that parses and
still misinstructs.

## Two second-order consequences (from `plan-cis-027-...-001`, carry into outline)

1. The doc's D3 instructions tell the caller to compute a `{settled_bots}` union. The live
   `review_completeness` **deliberately** rejects a bare `bot_kind` with no `evidence_kind`, so that
   unqualified presence cannot be mistaken for proof of review. ⛔ A caller following the doc **fails
   closed for the wrong reason**, and the failure reads as a *participation gap* rather than a *caller
   bug* — a false coverage signal produced by a doc error.
2. `enabled_bots` survives as a `configurable:` frontmatter key while live step-params carry
   `required_bots` / `optional_bots` / `bot_lists_provenance`.

## Affected sites (a starting list, NOT an enumeration — derive the population)

- `automatic-review/SKILL.md` — § "Producer: FIND", § "Step-done completeness guard (D3)",
  `## Canonical invocations`, the `enabled_bots` frontmatter key
- `workflow-integration-github/SKILL.md` — `## Canonical invocations`, `github_pr fetch_findings`
- `tools-integration-ci/scripts/ci.py` — the `pr view --head` help string naming `--pr-number`

⛔ **Derive the population; do not fix the list.** The listed sites came from three *incidental*
encounters, so they are a sample. **Two CLI-vs-doc divergences in the review/merge path found by
accident implies more found on purpose.**

## ⛔⛔ ABSORBED 2026-08-02 — the general fault: a swallowed non-zero exit, INSIDE the participation step

From `code-intelligence-substrate-006` (origin PLAN-CIS-027, PR #1079, third `automatic-review`
iteration at HEAD `aa74db65`):

```
script_failure notation=plan-marshall:workflow-integration-github:github_pr exit_code=2
  failure_kind=argparse_rejection
  detail=github_pr.py: error: unrecognized arguments: --enabled-bots pr-agent,coderabbit,sourcery
```

**Ninety seconds later the dispatch reported `[STATUS] Complete`, `outcome=done`,
`display_detail: "1 comment(s) found (unified triage pending)"`.**

⭐⭐ **This reframes the plan.** The doc drift (above) is ONE INSTANCE of what this fault makes
invisible. **Scope the swallowed exit as primary and the flag as its instance**, not the reverse.

- `--enabled-bots` scopes **which bots the fetch considers** — so a rejected bot-scoping flag means the
  fetch ran with different scoping than intended, ⛔ **inside the step whose entire job is to establish
  which bots participated.**
- The same run's barrier reported `unproven_bots=pr-agent(absent), coderabbit(refused_awaitable),
  sourcery(refused_hard)` — **all three were in the rejected flag's value.**
- ⚠ **The flag was also redundant**: the roster was already available via `step_params`
  (`required_bots: pr-agent` / `optional_bots: coderabbit,sourcery`,
  `bot_lists_provenance: answered`). The step had the roster through a supported channel and passed it
  through an unsupported one as well.

⭐ **Blast radius, stated precisely — the outcome was still correct.** The barrier blocked the merge,
forced loop-back iteration 3, and cleared only once participation was genuinely established. But it got
there by **re-deriving participation independently**. ⛔ **A defence that holds only because a downstream
check re-does the work is not a defence** — it is a redundancy that will be removed by someone
optimising, or that will fail the first time the downstream check is skipped.

⛔⛔ **This is a GAP IN PLAN-PR-014's SHIPPED REMEDY.** #1070 fixed the argparse surfaces and added an
UNKNOWN-verdict branch (*a non-zero exit OR a missing field is UNKNOWN, never a pass*) — but wired it to
`review_completeness`, **not to `github_pr fetch_findings` inside the same step body**. The identical
false-green shape survived one file over. ⇒ Derive **every** script call inside the step body, not the
ones a prior plan happened to name. This epic has now been bitten twice by *a reviewer's/plan's list of
call sites is a SAMPLE, not an enumeration*.

⚠ `phase-6-finalize`'s exit-code convention **already forbids this** — *"silent swallowing of
`wrong_parameters` rejections is the prohibited anti-pattern; 'log and continue' is equally
forbidden"* — but the convention is **not enforced inside this step body**. So the fix is enforcement,
not a new rule; a plan that only adds prose reproduces the defect.

⭐ Standing-rule cross-reference: *"a green finalize is never proof the bots saw the diff."* **This is a
mechanism by which that stays true even when every visible signal is green** — the step that establishes
participation can fail internally and still report `done`.

## ⛔⛔ ABSORBED 2026-08-03 — a SECOND script, a THIRD rejection cause, the SAME swallow. Deliverable 0 is now settled beyond argument.

`truthful-signals-014` item 6, from a consuming project's round-7 bundle findings at bundle **0.1.1276**.

**`review_completeness check` was argparse-rejected (`exit_code=2`) FOUR TIMES** at the same call-site hash
`6a8227`, across four separate entries into `automatic-review`. **Final recorded state: `outcome: done`,
`head_at_completion: 21ff759`.**

⭐ **Root cause is a THIRD mechanism, and it is at the harness layer, not the caller's grammar**:
`--in-progress-bots ""` makes **the executor drop the empty value**, so argparse sees a flag with no
argument. **Omitting the flag entirely works.** ⇒ A caller can construct a *correct* argv and still be
rejected, because an empty-string value does not survive the executor.

⇒ **The swallowed-exit fault now has three independent causes across two scripts:**

| Script | Rejection cause | Where the fault lives |
|---|---|---|
| `github_pr fetch_findings` | `unrecognized arguments: --enabled-bots` | doc prescribes a flag that does not exist |
| `review_completeness check` | `--enabled-bots` / `--settled-bots` drift | doc prescribes a flag that does not exist |
| **`review_completeness check`** | ⭐ **`--in-progress-bots ""` — empty value dropped by the EXECUTOR** | **harness, not caller or doc** |

⛔⛔ **This settles deliverable 0 and kills the docs-only outline outright.** A doc reconciliation
(deliverables 1–2) **cannot** fix the third row — the argv is correct and still rejected. **Only enforcing
the exit-code convention in the step body catches all three.** ⇒ Deliverable 0 is not merely primary; the
other deliverables are **provably insufficient without it.**

⭐ **And it is FOUR rejections in one run recording `done`** — not one. The gate was **structurally absent
for that plan's entire finalize run**: an invocation argparse rejects *before the body runs*, so it can
enforce nothing. `outcome: done` is unearned four times over.

### ⛔ The discriminating question D1 MUST answer FIRST — it changes the plan's size

**PLAN-PR-014 (#1070) wired its UNKNOWN-verdict branch to `review_completeness` — the very script rejected
here.** So either:

- **(A)** bundle 0.1.1276 **predates** #1070 ⇒ this is historical at that site, and the plan is what the
  ABSORBED section above already says: extend PR-014's wiring to the unwired siblings; **or**
- **(B)** the bundle **postdates** #1070 ⇒ ⛔⛔ **PLAN-PR-014's remedy does not work even where it WAS
  wired**, which is a far larger claim than "it wasn't wired everywhere" and makes this plan a *repair* of
  a shipped fix rather than an extension of it.

⛔ **Date the bundle against #1070's merge before scoping anything.** ⚠ **Do not assume (A) because it is
the smaller plan.** This epic's recorded failure mode is preferring the attractive hypothesis.

### ⭐ Severity is set by what was gating, not by the exit code

In the same run **CodeRabbit set a SUCCESS commit status one second after posting "we couldn't start this
review."** The quorum check is the mechanism that should have caught exactly that — **and it was inert.**
⇒ **Two independent layers of the same gate failed silently in one plan.** A green merge signal stood on
nothing.

### ⚠ Why it went undiagnosed for two days — NOT ours, already owned

The executor **truncates `detail=` from the tail** (`detail[:_DISPATCH_FAILURE_DETAIL_LIMIT]`, verified
first-party in the sibling's tree) and argparse prints its actionable `error:` line **last**. **All four
occurrences cut off at `error: a`.** ⇒ **The diagnostic elision hid the caller bug.** Staged as
`truthful-signals` **PLAN-TRUTH-039**. ⛔ **Do not absorb it** — their fix does not fix ours, and ours does
not fix theirs; it stops the *next* one hiding. ⭐ Worth knowing at outline: **if you cannot see why a
dispatched rejection happened, suspect the truncation before suspecting the caller.**

## ⛔⛔ ABSORBED 2026-08-03 (second drain) — the same swallow, now at the PRE-MERGE BARRIER, with the log lines consecutive

From `retirement-verdict-cited-a-contradicting-example-001` (`truthful-signals` PLAN-TRUTH-047 / PR
**#1085**, merge `4cf3a008f`), routed here under the three-way rule. **First-party `logs/work.log`,
verbatim and consecutive:**

```
13:41:01 [ERROR] script_failure notation=plan-marshall:tools-integration-ci:ci exit_code=2
         failure_kind=argparse_rejection
         ci.py: error: unrecognized arguments: --pr-number 1085

13:42:59 [ERROR] script_failure notation=plan-marshall:workflow-integration-github:github_pr exit_code=2
         failure_kind=argparse_rejection
         github_pr.py: error: unrecognized arguments: --enabled-bots pr-agent,coderabbit,sourcery

13:43:32 [INFO]  Pre-merge comment barrier: clean - zero pending pr-comment findings, proceeding to
         merge. Re-fetch stored 0 findings, refused_bots=coderabbit,sourcery, participated_bots=none
```

⛔⛔ **`participated_bots=none` and "clean … proceeding to merge" are 33 seconds apart in the same log.**
The barrier reported clean **from a fetch argparse had rejected**, and the zero it read as *"no pending
findings"* was the zero of *a command that never ran.*

⭐ **This message's stated contribution is a CORRECTION of an existing attribution**, and that is the
useful part: finding `b2f0e9` had attributed the branch-cleanup half to *"derived participation from the
wrong oracle."* ⛔ **That attribution is incomplete — the truer cause is a swallowed argparse rejection.**
⇒ A defect already recorded under a plausible-but-wrong cause is **worse than an unrecorded one**, because
it looks owned.

⇒ **This is the FOURTH distinct site** for deliverable 0, and the first at the **pre-merge barrier** rather
than inside `automatic-review`. ⛔ **It also widens the population beyond the `automatic-review` step body
that the ABSORBED section above scoped** — `ci.py` and the barrier are outside it. **Derive across the
whole finalize merge-and-review path, not one step body.**

⚠ **Note the `--pr-number 1085` rejection is now HISTORICAL**: PLAN-PR-009 / #1087 shipped `--pr-number`
on `ci pr view`. ⭐ **The caller was right and the surface was missing** — the inverse of the
`--enabled-bots` case on the very next line, **in the same run.** ⇒ **Two opposite causes, one swallow,
33 seconds apart** — which is the argument for fixing the swallow rather than the flags, in the sharpest
form this epic has.

## ⛔⛔ ABSORBED 2026-08-08 — a FOURTH cause class: the flag is DECLARED and ACCEPTED, and the VALUE SHAPE is wrong

Source: `truthful-signals-020` item 28 (api-sheriff-roadmap round 8, routed under the three-way rule).
⛔ **LEAD, NOT FACT** — first-party in the reporter's repo, re-derived by nobody here. Re-ground the
line references at outline against our own `automatic-review` source.

`--participated-bots` takes evidence-typed `bot:evidence` pairs. Passing **bare bot names** does not
raise, does not reject, and does not warn — the fail-closed completeness gate simply reports **every
required bot absent** and would have blocked a merge. It was caught only because the operator checked
the claim against the PR by hand.

⭐ **Why this belongs here and widens the deliverable rather than duplicating it.** The three absorbed
cases above are all *rejection swallowed* — argparse said no and nobody listened. This one is the
**inverse and it is worse**: argparse said **yes**. Nothing was swallowed because nothing was
rejected. The surface accepted a malformed value and manufactured a **confident, fully-populated
fiction** — a complete-looking absence verdict over a population it never actually evaluated.

⇒ **D0's framing must not narrow to "surface the swallowed rejection".** A rejection-surfacing fix
closes three of the four cases and leaves this one untouched, because there is no rejection to
surface. The population to derive is *caller-supplied values that the surface accepts and
misinterprets*, alongside the values it rejects silently. **An accepted-but-misparsed argument is
indistinguishable from a correct one at every layer downstream** — which is exactly the epic's
confident-signal-hides-a-caveat theme arriving at the argument boundary rather than at the review
boundary.

⚠ This is the vacuous-guard class inverted once more: not a gate that passes having examined nothing,
but a gate that **fails** having examined nothing, with full confidence. Both directions are reachable
from the same missing value-shape validation.

- HYPOTHESIS (verify-at-outline): that `--participated-bots` in OUR tree has the same bare-name
  behaviour. Confirm/refute artifact: the `--participated-bots` parsing site in
  `automatic-review`'s completeness-check script and its `bot:evidence` split — read the parse, not
  the help string.

### ⭐⭐ RECURRENCE, SAME DAY — and it PROMOTES the hypothesis above to OBSERVED, in our own tree

Source: `truthful-signals-023` Finding 2, on **plan-marshall PR #1115** (PLAN-TRUTH-042), corroborated
first-party at that plan's landing analysis. **This is no longer a foreign-repo lead.**

The first `review_completeness` check on #1115 passed **bare bot names** where
`bot_kind:evidence_kind` pairs are required. All three bots read as absent and the check returned a
FAILING verdict. Ground truth via `ci pr comments`: coderabbitai 25 comments (20 inline, 2 review
bodies, 3 issue comments), cuioss-review-bot 1, sourcery-ai 1 review body — **all three genuinely
participated.** The run noticed, re-ran with the correct shape, and got `participation_complete: true`.

⇒ **Two instances, opposite directions, from the SAME missing value-shape validation:**

| Instance | Direction | Consequence |
|---|---|---|
| `truthful-signals-020` item 28 (foreign repo) | fail-closed **false negative** | would have blocked a merge; caught only by a hand check against the PR |
| `truthful-signals-023` Finding 2 (**#1115, ours**) | fail-closed **false negative** | *did* return a failing verdict on a mergeable PR; caught only because the run re-ran it |

⚠ **The fail-closed direction is the safer one and must not be read as the defect being mild.** Both
instances were caught by a human or a lucky retry, not by the mechanism. Nothing in the check
distinguishes *"this bot did not participate"* from *"you asked me the wrong way"* — and that missing
distinction is symmetric: the same silent reinterpretation that manufactures a false absence can
manufacture a false presence given a different malformed shape.

⇒ **D0's remedy is now determined, not merely suggested: a bare name MUST be REJECTED AS MALFORMED,
never silently interpreted as an unmatched pair.** Rejection is the whole fix — it converts an
invisible wrong answer into a visible caller error, which is the same move the swallowed-rejection
cases need from the other side.

- **OBSERVED** (first-party, #1115 landing analysis): the bare-name shape produces an all-absent
  verdict in THIS repo's `review_completeness` check. The hypothesis above is settled affirmatively;
  outline still reads the parse site to locate the fix, not to establish the behaviour.

## ✅ CONFIRMED 2026-08-08 (inbox drain) — the FOURTH cause class is now FIRST-PARTY, and it is BIDIRECTIONAL

Source: inbox `absent-names-two-states-with-opposite-remedies-002` (pending Q-Gate finding `b423d3`,
phase `6-finalize`, component `plan-marshall:automatic-review`, severity warning), filed while
hand-driving the pre-merge barrier on **PR #1118 — our own tree, our own run**.

⭐⭐ **This CLOSES the open HYPOTHESIS in the section above.** That absorbed item came from
`truthful-signals-020` as a second-hand lead in the reporter's repo, explicitly "re-derived by nobody
here". It is now confirmed in OUR tree, so the deliverable no longer rests on a foreign observation.

⛔ **And it is worse than the hypothesis stated — the two flags disagree with each other:**

| Flag | Required token form |
|---|---|
| `--participated-bots` | the **pair** form `bot_kind:evidence_kind` |
| `--stale-participation-bots` | **bare** kinds |

Both directions were hit on this one PR:

- a pair fed to `--stale-participation-bots` reported `absent` instead of `participated_stale`
- bare kinds fed to `--participated-bots` reported `absent` instead of `participated_but_empty`

⭐⭐ **The asymmetry is invisible at the call site because THE PRODUCER EMITS PAIRS FOR BOTH SETS.** A
caller that reads the producer's output and forwards it verbatim gets the wrong form for one of the
two flags **by construction** — this is not a caller mistake that better discipline would prevent.

⇒ **D0's population must include flag-set INTERNAL CONSISTENCY**, not only per-flag value-shape
validation. A fix that validates each flag's shape independently still lets a caller forward the
producer's output into the flag that wants the other form.

⚠ The unparsed token resolves to `absent`, which is a **blocking** member — so the defect is both
silent AND polarity-selecting, manufacturing a **confident false merge block** attributed to a bot
that in fact participated. That is the same silent-mis-parse-into-a-blocking-default archetype the
#1118 plan existed to remove from the classifier, reappearing one layer down in the flag parser.

**Candidate remedy (not applied):** either make the two flags take the same token form, or reject an
unparseable token loudly rather than dropping it into `absent`. *A parse that cannot round-trip its
input must not resolve to a blocking state by default.*

## ⛔⛔ ABSORBED 2026-08-08 (inbox drain) — a FIFTH instance, a THIRD script, and it fired INSIDE `automatic-review` itself

Source: inbox `absent-names-two-states-with-opposite-remedies-009`, `[ERROR] … script_failure`
work-log line `2026-08-08T19:32:15Z` (hash `429c71`). **First-party, PR #1118, our own tree.**

```
notation=plan-marshall:manage-architecture:architecture
exit_code=2
failure_kind=argparse_rejection
architecture.py: error: unrecognized arguments: --plan-id absent-names-two-states-with-opposite-remedies
```

It fired **17 seconds after** `[SKILL] (plan-marshall:execution-context.automatic-review) Loaded …` —
i.e. as one of the first actions inside the epic's own automated-review dispatch. **The dispatch then
ran for another 19 minutes and completed.**

⭐⭐ **Two properties that make this the sharpest instance in this spec, not merely another tally
mark:**

1. ⛔ **It happened inside `automatic-review`.** The step that adjudicates whether a PR was reviewed
   lost a structured architecture query, silently, and proceeded. Whatever the query was for, the
   dispatch's later reasoning ran **without it**, and *nothing downstream recorded a degraded input*.
   This is the same false-green shape as the absorbed cases above, now on a **third** notation
   (`manage-architecture:architecture`), which further confirms the population is
   *every script call inside the step body* rather than any curated list.
2. ⛔⛔ **A DOCUMENTED recurrence signature still recurred inside a level-5 dispatch.** The cause is the
   verb-scoped `--plan-id` form already named in `persona-plan-marshall-agent` § "Never invent script
   subcommands": `architecture.py` accepts `--plan-id` as a **top-level router flag, before the
   subcommand**, and passing it after the verb is rejected. **The prose guard exists and did not
   prevent it.** The structural guard (`ARGUMENT_NAMING_*` under `quality-gate`) governs *authored*
   invocations in skill bodies, **not invocations an agent composes at runtime** — which is precisely
   the gap D0 must close.

⚠ **Two further same-class rejections in the same run**, emitted by the finalize envelope itself at
20:38:16Z and 20:38:45Z (both `manage-findings`, both argparse rejections): a `qgate list` missing the
required `--phase`, and an **invented `--fields` flag**. The `--fields` one is a fresh instance of the
"never invent a flag" class. ⇒ **Three notations, five instances, one run.**

⚠ A second work-log failure at 19:02:51Z (`build-pyproject:pyproject_build`, `module-tests`) is
ordinary and self-resolving — recorded for completeness, **not** proposed as an instance.

## ⛔⛔ ABSORBED 2026-08-09 — THE ROOT IS AN ENVELOPE CONTRACT, NOT A DOC. D0 RE-SCOPES.

Source: inbox `generic-charter-language-specific-defect-007`, first-party on the #1130 run. **Three
more argparse rejections, all inside dispatched `execution-context-level-5` envelopes, all
`exit_code=2 failure_kind=argparse_rejection`:**

| Time | Notation | Rejection |
|---|---|---|
| 13:23:45Z | `manage-architecture:architecture` | `unrecognized arguments: --plan-id …` |
| 16:01:46Z | `manage-status:manage-status` | `merge-authorization: invalid choice: '…' (choose from 'grant','check')` |
| 16:02:48Z | `tools-integration-ci:ci` | `unrecognized arguments: --plan-id …` |

⭐⭐ **THE ROOT CAUSE IS NOT THE DOCS, AND THIS RE-FRAMES D0.** The `execution-context` prompt-body
contract states that `plan_id` is required and that **"every script call inside this envelope forwards
`--plan-id {plan_id}`."** Read as written that is a **universal quantifier over script calls, and it is
false in three different ways at once**:

- some scripts take the flag **only top-level** (`architecture` — declared, but rejected after the verb)
- some **do not take it at all** (`ci` — `--project-dir` is the foreign-checkout route)
- some take the plan id **as a value under a verb that must come first** (`manage-status
  merge-authorization`)

⇒ **The envelope prescribes a flag whose acceptance is per-script and per-position, and the leaf
obeys.** ⛔ **A prose universal that is false for a known subset of the script surface is the defect,
not the leaf that obeyed it.** D0's population must therefore include **flag POSITION validity**, not
only flag existence and value shape — and the primary fix site is
`execution-context.md`'s prompt-body contract, not any `## Canonical invocations` block.

### ⭐ A sub-signature that actively sends the fix to the wrong place

For `architecture`, **the rejection banner advertises the flag in its own usage line while rejecting
it**: `usage: architecture.py [-h] [--project-dir …] [--plan-id PLAN_ID] {discover,init,…}` printed
immediately above `error: unrecognized arguments: --plan-id …`. A fixer reading that output sees the
flag endorsed as valid and concludes the flag is right — so the natural next move is to re-issue it or
reach for a different flag name, **rather than to move the flag left of the verb.** ⇒ Add: when
argparse rejects a flag that IS declared on an ancestor parser, emit a distinguishing hint (*"declared
on the top-level parser; place it before the subcommand"*) rather than re-printing a banner that reads
as an endorsement. The `execute-script` wrapper already classifies `failure_kind=argparse_rejection`
and holds both the rejected token and the parser's declared set.

### ⚠ And all three steps reported `done`

`architecture-refresh` reported *"11 modules rediscovered, no descriptor drift"*; `branch-cleanup`
reported *"PR 1130 merged via queue…"*. **Neither `display_detail` records that a call was rejected and
retried.** A retried-after-rejection call is exactly the degraded-input case a later reader needs, and
today it survives only as an `[ERROR]` line nothing consumes. ⇒ This is the same
recorded-but-unread-signal shape as PLAN-PR-023 D2; **coordinate the two, do not build two consumers.**

⚠ **`truthful-signals-025` item 2 folds in here too**: a malformed `--participated-bots` value is
silently rejected and `review_completeness` **still exits 0**, manufacturing a participation gap
indistinguishable from a real one. Second-hand to us — treat as a lead — but it is the same
accepted-but-misparsed class D0 already owns.

## Deliverable sketch (≤4 — split if it grows)

0. ⛔ **PRIMARY — enforce the exit-code convention inside dispatched review step bodies.** A non-zero
   exit from any script call must fail the step. Population = every script invocation in the
   `automatic-review` step body, **derived**, not the two sites named here. Fix the `fetch_findings`
   call site to the canonical surface and read the roster from `step-params get`.

1. **Derive** every `## Canonical invocations` block / prescribed invocation in the review-and-merge
   surface and diff each against its script's live argparse. Output the population before fixing.
2. **Reconcile** docs to the live surfaces — semantically, preserving the required/optional distinction,
   not by rename.
3. **A derived, population-based test** that fails when a documented invocation does not parse.
   ⛔ Population derived from the docs at run time; non-emptiness asserted FIRST (this epic has been
   bitten by vacuous set-guards; copy `test/_shared/_dispatch_roster.py`).

## Claim labels

- **OBSERVED** — the #1079 argparse rejection; the PR-016 residue table; `ci pr view --pr-number` exit 2
  (all three reproduced or first-party).
- **HYPOTHESIS** — that the population extends beyond the listed sites. Confirm/refute: deliverable 1's
  derivation is exactly this test, and a null result is a valid, publishable outcome.
- ⚠ **UNKNOWN** — whether any *consumer* silently tolerates the old field names (e.g. reads `complete`
  and gets `None`). A doc fix would not repair that; check before closing.

## Expected Surface

⛔ **Added 2026-08-08 — this spec was staged WITHOUT one, so the `next` verb's disjointness admission
test had nothing to read.** Every entry is labelled; re-verify against HEAD at outline.

- **OBSERVED**: `marketplace/bundles/plan-marshall/skills/automatic-review/scripts/review_completeness.py`
  — the `--participated-bots` / `--in-progress-bots` parse and the exit-code path. ⚠ **Modified by
  `#1118`** (+131 lines).
- **OBSERVED**: `marketplace/bundles/plan-marshall/skills/tools-integration-ci/scripts/ci.py` +
  `ci_base.py` — the swallowed-rejection site at the router/provider boundary. ⚠ `ci_base.py` **modified
  by `#1118`** (+16 lines).
- **OBSERVED**: `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_pr.py`
  — the second script of the two-script, three-cause corpus. ⚠ **Modified by `#1118`** (+90 lines).
- **OBSERVED**: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/branch-cleanup.md`
  — the pre-merge barrier, the FOURTH site. ⚠ **Modified by `#1118`** (+64 lines).
- **OBSERVED**: `automatic-review/SKILL.md` + `workflow-integration-github/SKILL.md` invocation blocks.
- **HYPOTHESIS** (verify-at-outline): the population extends beyond these named sites across the whole
  finalize merge-and-review path. D0/D1 derives it; the list above is the FLOOR, not the extent.

## Sequencing

⛔⛔ **CORRECTED 2026-08-08 — the previous claim ("no shared-file debt … does NOT touch
`branch-cleanup.md`") was FALSE and self-contradicting.** This spec's own § *ABSORBED 2026-08-03 (second
drain)* places the fourth site **at the pre-merge barrier**, which IS `branch-cleanup.md`; and the
widened population explicitly reaches `ci.py` and the barrier, "outside the `automatic-review` step
body". A spec cannot claim surface-disjointness from a file its own scope section adds.

- ⛔ **Shares `branch-cleanup.md` with PLAN-PR-008 and PLAN-PR-013. Sequence, never pair.**
- ⛔ **Shares `github_pr.py` with PLAN-PR-005, PLAN-PR-013 and PLAN-PR-019. Sequence, never pair.**
- ⛔ **Shares `review_completeness.py` with PLAN-PR-011's D2.** Coordinate.
- ⚠ **Crosses the CI verb surface with PLAN-PR-020.** Both derive a population over it; **if the two
  derivations turn out to be the same population viewed differently, SAY SO rather than shipping two.**
- ⛔⛔ **RE-GROUND EVERY LINE REFERENCE**: four of this spec's five OBSERVED surfaces were modified by
  `#1118` (PLAN-PR-007, merged). The `--pr-number` rejection is already HISTORICAL (`#1087` shipped it).
  Read merged main, never this spec's numbers.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/review-apparatus/plans/PLAN-PR-017-a-workflow-doc-prescribes-a-flag-no-script-declares.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/local/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-marshall-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
