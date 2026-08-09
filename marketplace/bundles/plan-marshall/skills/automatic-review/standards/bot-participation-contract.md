# Bot Participation Contract

The single source of truth for **which review bots must participate**, **what their silence means**,
and **how a non-participation is classified**. The `automatic-review` step body, the producer
(`github_pr fetch_findings`), and the completeness helper (`review_completeness`) all consume this
contract; none of them restate its semantics.

## Required vs optional

Bot participation is classified by two config knobs on the `plan-marshall:automatic-review` step —
`required_bots` and `optional_bots`, each a comma-separated list of `bot_kind` values.

| Classification | Membership | Silence means | Gates the completeness quorum? |
|----------------|-----------|---------------|-------------------------------|
| **Required** | listed in `required_bots` | **A failure.** The bot was expected to review and did not. | **Yes** — a required bot that is still genuinely awaited holds the step open. |
| **Optional** | listed in `optional_bots` | **Not a failure.** The bot is a bonus reviewer; its absence is tolerable. | **No** — an optional bot never blocks mark-done. |
| **Unclassified** | listed in NEITHER | Nothing is expected of it. | **No** — but its comments are **still ingested** and the run records a warning. |

### The warn-but-ingest rule

A bot in neither list is **not** dropped. Its comments flow into the findings store exactly as a
classified bot's do, and the run additionally records a warning naming the unclassified bot. The two
lists carry **classification, not admission**.

This is deliberate. Dropping an unclassified bot's comments would make a configuration omission
silently destroy real review signal — the failure would be invisible precisely when the operator had
not yet thought about that bot. Warning-and-ingesting fails safe: no signal is lost, and the gap in
the configuration is surfaced rather than acted upon.

## The ask posture

`required_bots` and `optional_bots` both default to the **empty string**, and the emptiness is
load-bearing: it keeps a *never-asked* key distinguishable from an *answered-empty* value. Collapsing
the two would make "the operator has not been asked yet" indistinguishable from "the operator
deliberately chose no required bots" — two states that warrant opposite handling.

Three provenance values are recorded:

| Provenance | Meaning |
|------------|---------|
| `never_asked` | The wizard has not yet put the question to the operator. The empty value is a placeholder, not an answer. |
| `migrated` | The value was seeded by the one-shot legacy auto-map from a retired `enabled_bots` list, not by an operator answer. |
| `answered` | The operator was asked and answered — **including an explicit answer of none**. An answered-empty value is a real answer and is never re-asked as though it were absent. |

The wizard records an explicit `answered` provenance even when the operator selects no bots at all.
An empty `required_bots` therefore means the quorum is **vacuously satisfied** — there is nothing to
await — and that is a legitimate configured state, not a misconfiguration to warn about.

## Failure taxonomy

When a bot does not deliver a usable review, the non-participation is classified into exactly one of
seven members. The taxonomy is closed: every non-participation resolves to one of these.

| Member | Condition | Interpretation |
|--------|-----------|----------------|
| `absent` | No comment posted and no completion check-run observed; the review window closed with nothing. | The bot never engaged at all. |
| `not_triggered` | No `pull_request`-event workflow run exists for the PR at all, so nothing could have been published — a PR-wide condition, not a per-bot one. | The reviewers were never asked. The remedy is to trigger the review, not to escalate a reviewer that stayed silent. |
| `in_progress` | The bot's completion check-run is still running when the poll budget expires. | The bot engaged but did not finish in time; left to the pre-merge comment barrier. |
| `refused_awaitable` | The bot posted a refusal whose limit reopens on its own (`rate_limit_class: awaitable_window`). | Worth awaiting — the window resets. |
| `refused_hard` | The bot posted a refusal that does not reopen on a useful timescale (`rate_limit_class: hard_quota`), or a structural refusal such as a size/diff ceiling. | Not worth awaiting; whether the absence is tolerable is a required-vs-optional question, not a waiting question. |
| `participated_but_empty` | The bot posted at least one comment, but every comment was filtered out (noise) so it stored zero findings. | **Accounted-for, not a failure.** The bot did its pass and had nothing actionable to say. |
| `participated_stale` | The bot's comment matched a declared `participation_evidence` publish shape but failed the `participation_requires_update` currency test — the comment was already observed and its `updated_at` has not moved. | The bot reviewed an **earlier** HEAD, so nothing has reviewed the current diff. Blocking, but the remedy is a re-review trigger. |

`participated_but_empty` is the member most often misread. A bot that reviewed and found nothing is a
*successful* review, not a silent one — it must never be treated as an incompleteness, or a clean PR
would hold the step open forever.

### Two members are refinements, not siblings — and their remedies are opposite

Five of the seven members are mutually independent observations. The remaining two exist because
`absent` was doing two other jobs badly, and each carries a remedy that `absent`'s does not:

- **`participated_stale` is the opposite of `absent`.** `absent` means there is no review to refresh,
  so the remedy is to escalate a reviewer that was asked and did not answer. `participated_stale`
  means there **is** a review — it simply predates this HEAD — so the remedy is to **re-trigger** it.
  Collapsing the stale case into `absent` therefore prescribes escalation where a re-review was the
  correct and cheaper answer.
- **`not_triggered` is a refinement of `absent`,** and it is **PR-wide rather than per-bot**: the same
  condition holds for every bot on the PR at once, which is why its input is a single bool rather
  than an observation set keyed by bot. Its remedy is also the opposite of `absent`'s: no reviewer
  was asked, so escalating one names the wrong failure.

The two refinements narrow differently, and only one of them is strictly `absent`-narrowing.
`not_triggered` is evaluated as the **last** branch before the `absent` fall-through, so it can never
override a positive observation about a specific bot — only what would otherwise have been `absent`
is refined. `participated_stale` is narrower in origin but not in effect: it is evaluated after the
refusal branches but **before** `in_progress`, so a bot observed in both sets is classified
`participated_stale` rather than `in_progress`. That precedence is deliberate — a review that exists
but predates this HEAD is a more actionable signal than an in-flight run of unknown outcome, and it
carries the cheaper remedy (re-trigger rather than wait). A **refusal outranks a stale publish**: a
bot with both is classified refused, because the refusal is newer still (it names a reason the bot
will not review now, whereas a stale publish only says the last review predates this HEAD).

### Severity by classification

The taxonomy member describes *what happened*; the required/optional classification decides *whether
it matters*:

- A **required** bot resolving to `absent`, `not_triggered`, `in_progress`, `refused_awaitable`,
  `refused_hard`, or `participated_stale` is a completeness failure — the step is not markable done
  without an explicitly recorded force-done reason.
- An **optional** bot resolving to any member never blocks.
- Any bot resolving to `participated_but_empty` is accounted-for regardless of classification.

A completeness failure is not one undifferentiated state: `participated_stale` and `not_triggered`
block exactly as the other four do, but each names a **different remedy** (re-trigger the review /
trigger the review at all), so a consumer that renders every blocking member as "the bot did not
review" discards the one thing the widened taxonomy exists to carry.

## Evidence taxonomy

Participation is **evidence-typed, not presence-typed.** The mere existence of a comment resolving to
a bot's login proves nothing about whether that bot reviewed *this diff* — it may be a help reply, a
stale comment tied to a prior HEAD, or a marketing footer. A bot counts as a participant only when an
observed comment's `kind` is one of the publish shapes its own registry doc declares in
`participation_evidence`.

### What counts as evidence, per publish shape

| Publish shape | Counts as evidence because | Declared by |
|---------------|---------------------------|-------------|
| `inline` | A per-line comment can only be produced by reading the diff at that line. | CodeRabbit, PR-Agent |
| `review_body` | The bot's review summary is emitted by a completed review pass over the diff. | CodeRabbit, Sourcery |
| `issue_comment` | A PR-level comment a bot declares as a publish shape is a review artifact it emitted against the diff — it counts on its own terms, not because the bot has no other shape. | PR-Agent |

A shape's evidentiary weight is a property of the shape, never of how many shapes the declaring bot
has. A bot may declare several: PR-Agent publishes `issue_comment` unconditionally and `inline` when
`/improve` is enabled for the repository, and each shape counts on the reasoning in its own row. It
follows that the ABSENCE of one declared shape is not evidence of non-participation — only the
presence of a declared shape is evidence, and only of participation.

The vocabulary is **closed to publish shapes**, and that closure is what enforces the diff-derived
rule below: a publish shape is an artifact the bot produced against the diff, so anything without one
has no admissible evidence kind at all.

A bot whose `participation_evidence` is **empty resolves fail-closed** — it can never be *proven* a
participant, and is reported as `absent` rather than silently credited.

### Why a check-run state is not evidence

A check-run reports that a *job ran*, not that a *review was published*. The two come apart in both
directions, so reading check state as participation is wrong regardless of which way it errs:

- **False negative.** PR-Agent posts **no check-run at all** and submits **no review object**.
  Scoring it on check state would mark it absent on every run no matter how well it reviewed.
- **False positive.** A check-run can conclude successfully having posted nothing, or having posted
  only a refusal. A green check is not a published review.

Evidence is therefore taken from observed publish shapes only. Check state remains useful for the
*orthogonal* question of whether a bot's review window is still open (`in_progress` in the failure
taxonomy above) — that is a timing signal, not participation evidence.

#### Normative prohibition — a check conclusion is not evidence and not a handled record

A review bot's **check conclusion** — the terminal `SUCCESS` / `FAILURE` state `github_pr
bot_completion` reports for that bot's registry `completion_check_name` — is subject to two
prohibitions, both normative:

1. **A check conclusion is NOT participation evidence and MUST NOT be substituted for a declared
   `participation_evidence` publish shape.** No caller may synthesise a `{bot_kind}:{evidence_kind}`
   pair from a check conclusion, feed a check-derived pseudo-kind to `review_completeness
   --participated-bots`, or otherwise let a concluded check stand in for an observed publish shape.
   The admissible vocabulary is closed to the publish shapes in the table above, and no check state is
   a member of it. A `SUCCESS` conclusion on a bot that published nothing is `absent`, not
   `participated`.
2. **A check conclusion is NOT a findings-handled record.** A concluded check says nothing about
   whether the bot's comments were fetched, filed, or triaged. It MUST NOT be read as discharging the
   unhandled-comment predicate, and it MUST NOT be recorded as, or substituted for, a
   `pr-comment` finding's resolution.

**`in_progress_bots` is the ONLY legitimate consumer of `bot_completion` output _as participation
input_.** The verb answers the timing question — is this bot's review window still open? — and the
only observation set its return may feed is `--in-progress-bots`, which resolves a required bot to
the `in_progress` taxonomy member. Routing a `bot_completion` return into any *other* participation
observation set (`--participated-bots`, `--refused-bots`) is a contract violation.

This scopes the evidence channel, not the poll loop. `bot_completion` is also a **control-flow**
signal, and consuming it as one is sanctioned: the completion-aware poll documented in
[`../SKILL.md`](../SKILL.md) branches on the return to decide whether to keep polling, settle on the
`review_bot_buffer_seconds` fallback, or stop — none of which is participation input. Only the
budget-exhausted branch reaches `--in-progress-bots`.

### Evidence for a bot that edits one comment in place

A bot that re-reviews by **editing its single persistent comment** rather than posting a new one
declares `participation_requires_update: true`. For such a bot the comment's continued existence
proves only that it reviewed **once, at some earlier HEAD** — after a force-push the unchanged
comment would silently credit it with reviewing code it never saw. Its evidence therefore requires
either **first presence** (the comment is newly observed) or observed **`updated_at` movement**.

A failed movement test is **not the same as no evidence at all**, and the taxonomy keeps the two
apart: the bot published in a declared shape, so the producer reports it in
`stale_participation_bots[]` and it resolves to `participated_stale` — blocking, but with a
re-review trigger as the remedy. Discarding the failed movement test toward `absent` would lose
exactly that distinction and prescribe escalating a reviewer whose review only needed refreshing.

## Participation is not review quality

The quorum proves that every required bot **participated**. It never proves the diff was **reviewed
well**, or reviewed meaningfully at all. This ceiling is measured, not theoretical: on #1027 PR-Agent
published its Guide — valid participation under its record — while reporting "no major issues" on a
diff in which CodeRabbit found two Major defects.

**A satisfied quorum MUST NOT be rendered as a reviewed diff.** Every consumer of the participation
verdict is bound by that: the predicate's own envelope carries `proves: participation_only` so the
claim is machine-readable and cannot be read as a quality statement by accident.

Three obligations follow, and they are **normative**, not advisory. They exist because the PR body
carries a distilled **Intent** section, and an Intent section is precisely the kind of input that can
make a shallow review *look* like a real one.

### Obligation 1 — classify intent-echo as participation, not review

A review whose content only **restates or endorses the stated intent** — "this correctly implements
the described change", "looks consistent with the stated goal" — resolves to
`participated_but_empty`. It is participation: the bot ran and said something. It is **never a
satisfied review obligation**, because echoing the intent demonstrates no engagement with the diff.
Crediting an intent-echo as a review would let a PR pass the gate on the strength of its own
description.

### Obligation 2 — an Intent section must never make a review read cleaner

The participation predicate MUST NOT become **more permissive** on a PR whose body carries an Intent
section. An empty review, or a conformance-only review ("matches the stated intent"), must resolve to
exactly the same state it would resolve to on a PR with no Intent section at all.

This is a **parity requirement, discharged by a parity test**: the predicate's verdict for a given
set of observed review artifacts must be **identical-or-stricter** with the Intent section present
than without it. A prose assurance does not discharge it — the test is what proves the predicate did
not quietly soften.

### Obligation 3 — only diff-derived evidence discharges a review obligation

Evidence must be **diff-derived**. A **body-derived signal — anything a reviewer could have produced
by reading the PR description alone** — cannot discharge a review obligation, no matter how confident
or well-formed it is.

This is enforced structurally rather than asserted in prose: the admissible evidence vocabulary is
closed to the publish shapes in the table above, and the PR body is not a publish shape. A
body-derived signal therefore carries **no admissible evidence kind** and cannot be laundered into
the participation set. Unqualified presence (a bare `bot_kind` with no evidence kind) is rejected for
the same reason.

## Detecting a refusal

A refusal is recognised from each bot's own registry doc (`standards/{bot_kind}.md`), via that doc's
`refusal_patterns[]` field — a dedicated per-bot list of the literal notice shapes that bot publishes
when it declines to review.

`refusal_patterns` is deliberately **separate from `ignore_patterns`**. `ignore_patterns` is a
noise filter listing the routine sections a bot emits on a *successful* review (walkthroughs,
learning notices, summary tables); reusing it for refusal detection would classify ordinary
successful reviews as refusals. The two lists answer different questions and must stay distinct.

A bot whose `refusal_patterns[]` is empty has no observed refusal shape; its non-participation
resolves to one of the non-refusal members — `participated_stale`, `in_progress`, `not_triggered`, or
`absent` — rather than to either refusal member. This is the fail-closed default: a refusal is only
ever claimed on positive evidence.

### A refusal is never noise — it is a branch

Recognising a refusal and then **discarding** it is the same failure as not recognising it. A refusal
that never reaches the quorum layer leaves the bot classified `absent`, which reads as "not heard from
yet" rather than "declined" — so a PR on which every required reviewer refused reports a complete
review with substantively zero review coverage.

The producer therefore treats a recognised refusal as a **three-way branch**, not a drop:

| Aspect | Behaviour | Why |
|--------|-----------|-----|
| Filed as a `pr-comment` finding? | **No.** | A refusal is a signal *about the review*, not feedback about the code. Handing it to triage would ask the operator to dispose of a notice with nothing to fix. |
| Counted as noise? | **No** — it has its own `count_skipped_refusal` counter. | Sharing `count_skipped_noise` is exactly the conflation that hid it. The two counters answer different questions. |
| Surfaced? | **Yes** — the bot is named in `fetch_findings`'s `refused_bots[]` and forwarded to `review_completeness check --refused-bots`. | This is what lets the taxonomy assign `refused_awaitable` / `refused_hard` instead of inferring absence from silence. |
| Counted as participation? | **No** — the refusing comment is excluded from `participated_bots[]`. | A refusal is published in one of the bot's declared publish shapes, so without an explicit exclusion the shape alone would credit it as a proven participant. |

This is also why `refusal_patterns` must never be unioned into the producer's `ignore_patterns` drop
set: doing so collapses the very distinction the two-field split exists to carry.

### The three per-bot marker lists answer three different questions

A bot's registry doc declares three independent marker surfaces. They are easy to confuse because all
three are literal-substring lists read by the same producer, but each drives a different outcome and
none is a superset of another:

| Marker surface | Match semantics | Outcome |
|----------------|-----------------|---------|
| `ignore_patterns` | **Any** entry present in the body. | **Unconditional drop.** The comment is a routine section of a successful review (a walkthrough, a tips block, a `/help` echo) and is never a finding, whatever else the body carries. |
| `refusal_patterns` | **Any** entry present in the body. | **A branch, never a drop.** The comment is the bot declining to review; it is excluded from findings AND from `participated_bots[]`, counted under `count_skipped_refusal`, and surfaced in `refused_bots[]` (see the table above). |
| `contentless_review_markers` + `actionable_content_markers` | **Every** `contentless_review_markers` entry present **and** no `actionable_content_markers` entry present. | **A conditional drop.** The comment is a real review that found nothing, so it is dropped as noise (`count_skipped_noise`) — but only when the body is *fully* clean. A single actionable marker, or one missing required marker, leaves the comment in place and it is filed as a finding in full. |

The pair is a conjunction over `contentless_review_markers` precisely so it cannot be widened by
accident: weakening the list to one representative marker would silently broaden the suppression.
An empty `contentless_review_markers` is the fail-closed default — the layer never fires for a bot
that declares none, which is every bot that has not opted in.

**The drop itself never removes participation evidence.** `participated_bots[]` is derived from the
raw comment list *before* the producer's pre-filter runs, so suppressing a bot's only comment removes
its findings without removing its participation evidence. On a fetch where the bot is credited, it
therefore lands on the `participated_but_empty` member of the failure taxonomy above — *"Accounted-for,
not a failure. The bot did its pass and had nothing actionable to say."* — which is exactly what a
clean review is. Reading *the drop* as `absent` would turn a successful review into a completeness
failure.

That is a claim about the drop in isolation, and it is deliberately **not** an absolute: it does not
say a dropped comment can never resolve to a blocking state. Credit still has to clear the movement
requirement below, and `review_completeness.classify_bot()` assigns `participated_but_empty` only to a
bot present in `proven_participants` — a bot absent from `participated_bots[]` falls through to an
unproven state that blocks the quorum. For a bot declaring `participation_requires_update` (today,
only PR-Agent, the sole bot that opts into the contentless drop) an unchanged clean comment is
credited on the fetch that first observes it and denied on every later fetch, so in the steady state a
dropped clean Guide resolves to **`participated_stale`, not `absent`** — the producer saw the comment
in a declared publish shape and reports the bot in `stale_participation_bots[]`, so what the steady
state records is a review that predates this HEAD rather than a reviewer that never engaged. That is
the intended reading of a stale unchanged comment, not a defect in the drop, and the member it lands
on is the one whose remedy — re-trigger the review — actually fits it.

**Surviving the drop is not the same as being exempt from the movement requirement.** For a bot
declaring `participation_requires_update` the evidence that survives the drop must still show **first
presence or `updated_at` movement** (§ "Evidence for a bot that edits one comment in place"). Keeping
that requirement live across a drop takes an explicit mechanism, because first presence is answered
from what the plan has already **observed** — and the natural record of an observation is the
`pr-comment` finding the comment produced, which a dropped comment by definition does not produce.
The producer therefore records each noise-dropped comment's `(bot_kind, comment_id)` key in a
plan-scoped **observation sidecar** kept beside the findings store, and evaluates first presence
against the **union** of the stored-finding keys and the recorded dropped keys. A dropped comment is
consequently first-present exactly once — on the fetch that first observed it — after which only a
real `updated_at` edit credits the bot again.

The sidecar holds **observation keys, not findings**: they are never returned by a findings query,
never enter the pending-findings gate, and never reach operator triage, so the triage queue stays as
clean as the drop intends. Recording them as findings in any resolution state would put routine
clean-review boilerplate back in front of the operator, which is the defect the drop exists to
remove. Without the record the two halves collide: read from the stored findings alone, the
first-presence arm stays permanently satisfied for every dropped comment, so a bot whose one stale
comment never changed would be credited as a proven participant on every fetch — the exact false
positive `participation_requires_update` exists to close.

## Consumers

| Consumer | What it reads |
|----------|---------------|
| `automatic-review/SKILL.md` | Both lists, to drive the completion-aware poll, the re-review trigger set, and the step-done guard. |
| `github_pr fetch_findings` | Both lists, to classify each ingested comment and emit the unclassified-bot warning; each bot's `participation_evidence` / `participation_requires_update`, to derive the evidence-typed `participated_bots[]` **and the `stale_participation_bots[]` set that carries `participated_stale`**; each bot's `refusal_patterns`, to branch a refusal into `refused_bots[]` rather than drop it; each bot's `contentless_review_markers` / `actionable_content_markers`, to drop a fully clean review comment as noise. |
| `github_pr pull_request_runs` / `ci checks pull-request-runs` | Nothing from this contract — it is the **observation channel for `not_triggered`**, answering the PR-wide question of whether any `pull_request`-event workflow run exists for the PR at all. Its verdict reaches the predicate as the single `--not-triggered` bool. |
| `review_completeness check` | `required_bots` for the quorum; `optional_bots` for reporting only; `participation_evidence` to admit each evidence pair; `rate_limit_class` to split the two refusal states. Consumes `stale_participation_bots[]` via `--stale-participation-bots` to assign `participated_stale`, and the PR-wide `--not-triggered` bool to refine what would otherwise be `absent`. |
| `github_ops pr wait-for-comments` | Each bot's `participation_requires_update`, to select the `updated_at`-movement arm of its completion predicate over the count-growth arm; `participation_evidence` plus `bot_kinds()`, to decide whether the await is answerable at all (`detector_answerable`). |
| `marshall-steward` | Both lists, to ask the wizard question and record the provenance. |

### Recorded exclusions

Four further surfaces mention participation or the movement test and were **swept and deliberately
excluded** from the taxonomy's documented consumer set, so their absence reads as a decision rather
than as a gap: `_github_pr.py` (the private helper the producer calls — it computes the observation
and carries no taxonomy vocabulary of its own), `standards/coderabbit.md` and `standards/sourcery.md`
(neither bot declares `participation_requires_update`, so neither can reach `participated_stale`, and
a registry doc declares per-bot data rather than taxonomy semantics), and
`test_pr_wait_for_comments_predicate.py` (it pins the await predicate's movement arm, which is the
*input* to the currency test rather than the classification it feeds).

See [`../SKILL.md`](../SKILL.md) for the step body that applies this contract and
[`../../manage-config/standards/data-model.md`](../../manage-config/standards/data-model.md) for the
knob storage shape and provenance field.
