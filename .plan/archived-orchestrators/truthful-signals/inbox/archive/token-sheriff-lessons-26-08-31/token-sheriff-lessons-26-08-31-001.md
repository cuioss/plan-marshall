envelope_version=1
sender_type=orchestrator
sender_id=token-sheriff-lessons-26-08-31
epic=truthful-signals
kind=candidate-lesson
created=2026-08-31T08:10:31Z

# Transfer: 8 plan-marshall tooling lesson-clusters learned in Token-Sheriff

Filed by the orchestrator of Token-Sheriff epic `lessons-handling-26-08-31-01`, at the operator's
direction. That epic scanned 23 lessons — 16 from Token-Sheriff's `manage-lessons` store plus 7
candidate-lessons that a plan filed to an epic inbox and that were archived on drain without ever
being registered — and aggregated them into 11 queue items.

**Only 2 of the 23 lessons are about Token-Sheriff's own code.** The rest are plan-marshall tooling
lessons that merely happened to be *learned* in that repository. This message hands over the 8
clusters whose **fix lands in this repo**, classified by where the corrective work belongs rather
than by where the failure was observed.

⚠ **This is material, not a queue.** I have deliberately NOT proposed queue items for your epic —
your orchestrator should cluster this against your own corpus, which I cannot see. Several of these
will likely merge with lessons you already hold.

⚠ **Nothing here is registered in any lessons store.** The 7 candidate-lessons were never registered
(registering an unreviewed corrective rule puts unagreed text into a corpus that later passes treat as
settled), and the 16 store lessons live in Token-Sheriff's store, not yours. Treat every claim below
as a **lead to verify against this repository's own source**, not as a settled finding — several were
observed against plan-marshall versions that have since moved.

---

## Manifest

| # | Cluster | Lessons | Component the fix lands in |
|---|---|---:|---|
| 1 | Review-bot detection blind spots | 3 | `automatic-review`, `workflow-integration-github` |
| 2 | Generated-artifact staleness and freshness gates | 3 | finalize gate loop, `architecture-refresh` |
| 3 | Claim-before-verification | 3 | `phase-6-finalize`, `persona-module-tester` |
| 4 | Git and worktree finalize mechanics | 2 | `workflow-integration-git` |
| 5 | Canonical build commands that do not match the module | 2 | `build-maven` |
| 6 | Argparse rejection recurrence | 1 | script surfaces / `recipe-fix-argparse-rejection` |
| 7 | Steward executor version sort | 1 | `marshall-steward` |
| 8 | marshalld baseline interpreter | 1 | `manage-build-server` |

---

## 1. Review-bot detection blind spots — 3 lessons, one failure mode

**The mode: the detector reads a channel the bot did not publish on, concludes `absent`, and the gate
either blocks or waits.** The cost is always an operator wait for work already done.

- A required bot that does not re-post per HEAD makes the review gate **unsatisfiable, not slow**.
- `review_completeness --participated-bots` reads a bare `bot_kind` as absent; only evidence-typed
  pairs register.
- A bot publishing outside the `review_body` channel reads as `absent`. Observed cost: one wasted
  operator wait, with `automatic-review` returning `outcome=loop_back` on iteration 1.

⚠ **Scope correction carried from the source, do not restate the stronger claim.** The run's first
framing was too strong: CodeRabbit *did* post real `review_body` findings on that PR (`d45c82`,
`42cc19`). The defect is that the detector missed *an additional channel*, not that the bot published
nowhere.

**The strongest evidence for this cluster is recursive.** A seventh candidate-lesson was itself
*nearly lost to this exact gap*: `lessons-capture` rejected it as unsubstantiated because it searched
the findings store and reviewer `review_body` records, while CodeRabbit had raised the item only in an
inline review thread (`PRRT_kwDOOA6qMM6c8_VF`), with its own verification run attached. It was
recovered by hand. **A detection gap in the review-reading machinery nearly swallowed the lesson about
the detection gap in the review-reading machinery.**

**Cross-reference, not a transfer:** a Token-Sheriff-retained lesson (`cui-rewrite:disable` is enforced
from the parent pom, but *a bot's repo-only grep reports it as unimplemented*) is a fourth instance of
this same absence-from-the-wrong-source mode. Its fix is a project-config matter and stays there; the
instance is offered here because it widens the mode beyond review channels to **any** evidence source
a bot reads too narrowly.

**Suggested shape of the fix:** enumerate every channel a bot can publish on (review body, inline
review threads, issue comments, check runs) and which the detector currently reads. The gap is the
deliverable. Make the inline-thread case above pass.

## 2. Generated-artifact staleness and freshness gates — 3 lessons

**The mode: a generated artifact goes stale, a gate notices, and the run either loops or ships it.**

- `-Ppre-commit` full-reactor builds need **multiple run-commit-rerun cycles** to reach idempotence;
  the adaptive timeout must account for that.
- The `-Ppre-commit` freshness gate **re-stales itself**. Observed **three times in one run**, so the
  loop is reproducible rather than incidental.
- Generated architecture metadata goes stale silently.

**The converged corrective rule:** a freshness gate is reconciled by regenerating and committing,
**never by `--force`**; and a noticed-but-shipped staleness is a **decision** that must be recorded as
one, not an oversight that passes silently.

⚠ Partial-ownership note: the `-Ppre-commit` profile itself comes from the cui parent pom, not from
plan-marshall. What belongs here is the **gate loop and the reconciliation contract** — the part that
decides what a finalize run does when the gate fires.

## 3. Claim-before-verification — 3 lessons, three components, one mode

**The mode: an assertion made before the evidence that would settle it.** Grouped on failure mode
rather than component, because the components genuinely differ and the mode is identical.

- Finalize steps report **green for absence of verification** — an evidence-free zero-finding audit,
  an unreviewed PR, a baseline-less scope guard.
- A new test asserting existing behaviour **ratifies** it; verify the behaviour is intended before
  locking it in.
- A structural-impossibility claim was **asserted twice before being checked**, and an audit then
  refuted most of it.

The third carries two independent instances from one run: a withdrawn "adversarial oracle" argument,
and a verdict-document residual that scoped a fact about one coordinator method onto a whole layer —
the documented entry point was reachable all along. Its rule: **assert the narrow claim first.**

Given this epic is named *Truthful Signals*, the first item is probably the one to look at hardest: a
step reporting green must name **what it verified**, not merely that it found nothing.

## 4. Git and worktree finalize mechanics — 2 lessons

- Session restart mid-finalize resets the cwd pin; re-locate the worktree before any `--plan-id`
  build/CI call.
- ⚠ **A reproducible producer gap, not an incident.** `prune-local-and-remote-ref` returns
  `branch_delete_failed` and **aborts before pruning the remote-tracking ref**, because
  `worktree-remove` has already deleted the local branch. The documented `status: partial` case covers
  a missing *remote* ref, not this ordering. Result: a stale `origin/feature/*` ref survives cleanup
  **silently, on every merge-queue run**. Cleaned by hand in the observing run after confirming the
  remote branch was genuinely gone.

## 5. Canonical build commands that do not match the module — 2 lessons

- `build-maven` wrapper **silently overrides caller intent**: `--timeout` is a no-op and routing
  defaults to the main checkout. A silent override is the defect — honour the caller or refuse visibly.
- A module's canonical `module-tests` command used `test` where the module's own test-jar dependency
  requires `verify`. (The pom fact is Token-Sheriff's; the canonical-command registration is yours.)

## 6. Argparse rejection recurrence — 1 lesson

**Eight distinct script notations rejected by argparse in a single run** — a recurrence pattern, not a
slip. The lesson's value is that it classifies rather than lists, into five signatures:

1. **Invented flag name** — a plausible synonym guessed for a flag that does not exist
2. **Router-scoped flag in the wrong position** — named in the source as *the canonical recurrence signature*
3. **Missing required flag**
4. **Verb paraphrase**
5. **Semantically malformed value** — exit 1, not 2: the parser accepted the flag and the body rejected the value

⚠ **Check `recipe-fix-argparse-rejection` before doing anything.** That recipe already exists. The open
question is whether it encodes the *signatures* or only the per-incident fix. If it encodes them, this
is already covered and should be retired rather than worked.

## 7. Steward executor version sort — 1 lesson

`generate_executor` sorts plugin-cache versions **lexicographically**, yielding a hybrid executor that
breaks every build. Lexical ordering fails exactly at a digit boundary.

⚠ **A live test case exists in Token-Sheriff right now:** its `marshal.json` is provisioned at
plan-marshall `0.1.1556` against `0.1.1560` installed — precisely that digit-boundary shape. Running
the steward reconciliation there exercises the claim against a real drift rather than a synthetic one.

## 8. marshalld baseline interpreter — 1 lesson

`marshalld` rejects **every** submit with `wrong_interpreter` when the registry carries no
`baseline_interpreter`. A missing registry field produces a per-submit rejection whose message names
the *interpreter* rather than the *missing baseline*, so the diagnosis points away from the cause.
Either refuse at enrolment when the baseline is missing, or make the rejection name the missing field.

---

## Retained in Token-Sheriff, for completeness

Three items were **not** transferred, because their fix lands there:

- **OpenRewrite marker handling** (3 lessons) — `rewrite.yml`, root-pom `activeRecipes`, and the
  `AGENTS.md` marker rule. Its bot-side instance is cross-referenced into §1 above.
- **Tests that under-constrain** (2 lessons) — hand-enumerated matrices omitting supported
  combinations; native-image metadata tests asserting presence rather than exactness.
- **Unicode ellipsis breaks ArchUnit package patterns** (1 lesson) — a documentation character
  producing a test failure far from its cause.

## Provenance

Source epic: `TokenSheriff/.plan/local/orchestrator/lessons-handling-26-08-31-01/` — carries the full
23-lesson disposition table, the clustering rationale, and per-item specs. Readable directly; same
machine. The transferred items are marked `relocated` there with a pointer to this message, so neither
side silently owns the same work.
