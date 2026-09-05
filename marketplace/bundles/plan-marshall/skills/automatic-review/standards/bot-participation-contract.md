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
eleven members. The taxonomy is closed: every non-participation resolves to one of these.

This count is stated here on purpose, and it is the ONE place in prose that states it. It is not a
hand-maintained restatement: `test_bot_participation_contract.py` reads this sentence back, converts
the cardinal word to an integer, and asserts it equals the member count derived from
`review_completeness`'s own `STATE_` constants — so a member added to the classifier without
updating this word fails the suite. A count with that mechanical link to its source is a checked
fact; a count written anywhere else is an unguarded duplicate, which is why no other document
restates it.

| Member | Condition | Interpretation |
|--------|-----------|----------------|
| `absent` | No comment posted and no completion check-run observed; the review window closed with nothing. | The bot never engaged at all. |
| `not_triggered` | No `pull_request`-event workflow run exists for the PR at all, so nothing could have been published — a PR-wide condition, not a per-bot one. | The reviewers were never asked. The remedy is to trigger the review, not to escalate a reviewer that stayed silent. |
| `unregistered_kind` | The configured token matches **no member of the live registry kind set** (`bot_registry.bot_kinds()`). Decided from the configuration, not from an observation, and evaluated only after every observation branch has declined. | **No reviewer answers to this name**, and none ever could — participation is keyed by a `bot_kind` derived from the author login, so a token outside that codomain can never enter `participated_bots`. The remedy is to **fix the name**, never to chase the reviewer. The payload names the live kind set the token was checked against, which is also the set the corrected token must come from. |
| `in_progress` | The bot's completion check-run is still running when the poll budget expires. | The bot engaged but did not finish in time; left to the pre-merge comment barrier. |
| `refused_awaitable` | The bot posted a refusal whose limit reopens on its own (`rate_limit_class: awaitable_window`). | Worth awaiting — the window resets. |
| `refused_hard` | The bot posted a refusal that does not reopen on a useful timescale (`rate_limit_class: hard_quota`) and whose cause is a rate/budget **quota** — an account- or plan-level allowance. | Not worth awaiting; whether the absence is tolerable is a required-vs-optional question, not a waiting question. |
| `refused_unknown` | The bot posted a refusal about whose awaitability nothing is known. Reached two ways: the registry declares its class `unknown` (its refusal shape has never been observed), or **no arm of the recognition stack could read the notice at all** — which resolves here whatever class the bot declares. | A declared *we-do-not-know*, NEVER a positive hard quota. Rendering it as `refused_hard` steers an operator toward "waiting is futile, force it" for a refusal that might have been awaitable. Its own member so the ignorance reaches the reader as ignorance. |
| `refused_structural` | The bot posted a refusal whose **cause is a ceiling on the diff itself** — the PR is over a per-PR size budget (an observed `cause: size`). Decided by the cause axis, whatever the bot's `rate_limit_class` declares. | **The only member whose refusal is not temporal.** The other three say *not now*; this one says *not this diff*, and the same request never succeeds while the diff is this size. Remedies: **split**, **accept the gap**, or **disable this reviewer for this PR** — ⛔ **never await.** The finding carries the **cap** the notice stated, so the gap is auditable against the measured diff size. |
| `participated_but_empty` | The bot posted at least one comment, but every comment was filtered out (noise) so it stored zero findings. | **Accounted-for, not a failure.** The bot did its pass and had nothing actionable to say. |
| `participated_stale` | The bot's comment matched a declared `participation_evidence` publish shape but failed the `participation_requires_update` currency test — the currency ledger anchors the comment to a commit that is **not** the merge candidate, and its `updated_at` is unchanged from the value recorded at that credit. | The bot reviewed an **earlier** commit, so nothing has reviewed the current diff. Blocking, but the remedy is a re-review trigger. |
| `declined` | The bot was asked to review the merge candidate (a re-review was triggered) and answered without producing a review of it — an **incremental-review decline**: it responded with a comment carrying no reviewed-commit SHA (`head_sha_verified: false`) rather than a review of this HEAD. | The bot engaged but **declined** to review this commit. Blocking, but re-triggering is futile — the productive action is to accept the decline (move the bot to `optional`, or record a merge-authorization), not to trigger again. |

`participated_but_empty` is the member most often misread. A bot that reviewed and found nothing is a
*successful* review, not a silent one — it must never be treated as an incompleteness, or a clean PR
would hold the step open forever.

### Some members are refinements, not siblings — and their remedies are opposite

Most members are mutually independent observations. The rest exist because another member was doing
a second job badly, and each carries a remedy that member's does not. Three of them refine `absent`;
the fourth refines the refusal branch.

- **`participated_stale` is the opposite of `absent`.** `absent` means there is no review to refresh,
  so the remedy is to escalate a reviewer that was asked and did not answer. `participated_stale`
  means there **is** a review — it simply predates this HEAD — so the remedy is to **re-trigger** it.
  Collapsing the stale case into `absent` therefore prescribes escalation where a re-review was the
  correct and cheaper answer.
- **`not_triggered` is a refinement of `absent`,** and it is **PR-wide rather than per-bot**: the same
  condition holds for every bot on the PR at once, which is why its input is a single bool rather
  than an observation set keyed by bot. Its remedy is also the opposite of `absent`'s: no reviewer
  was asked, so escalating one names the wrong failure.
- **`unregistered_kind` refines `absent` at the CONFIGURATION boundary rather than the observation
  boundary,** and it is the only member decided without an observation at all. `absent` says a
  reviewer we know was asked and did not answer, so its remedy is to chase the reviewer.
  `unregistered_kind` says the configured **name matches no reviewer we know**, so there was never a
  reviewer to chase and the remedy is to **fix the name** — a disjoint remedy, and one an operator
  cannot even guess at from `absent`. Collapsing the two is what makes a barrier report a true
  statement about the observed set beside a false steer about its cause: the review exists and is
  plainly visible (the warn-but-ingest rule above still files it), while the quorum reports it
  missing, so the cost lands as **diagnosis** rather than detection.

  Its position in the classifier is load-bearing in both directions. It is evaluated **after** every
  observation branch, because a membership test is a fact about the name and must never displace
  something the run actually observed — an unregistered token observed participating reports that.
  It is evaluated **before** `not_triggered` and `absent`, because when nothing was observed it says
  strictly more than either.

  ⛔ **Not a silent drop.** An unknown token stays in the roster and stays blocking — it is in the
  unproven set exactly as `absent` is, so the barrier still fails closed. Dropping it instead would
  replace a confusing block with a **silent pass**, satisfying the quorum through a reviewer nobody
  configured, which is strictly worse than the defect it would be fixing.
- **`refused_structural` refines the REFUSAL branch, and its remedy set is disjoint from the other
  three's.** The three temporal refusal members all describe a limit that moves — the same request
  succeeds once it does — so their remedy set is *wait, or accept the gap*. A diff-size ceiling does
  not move: the same PR is over the limit a minute later and an hour later alike. Its remedy set is
  *split, accept the gap, or disable this reviewer for this PR*, and ⛔ **`await` is not a member of
  it.** Collapsing the structural case into a temporal member therefore does not merely mislabel it —
  it **offers a non-option**, handing the operator a wait for a ceiling that waiting does not move.

  This is why the cause is a **member** rather than a label attached to one. A label leaves every
  consumer routing on the member, so the wrong remedy is still the one offered; only a distinct
  member changes what the consumer does.

The `absent` refinements narrow differently, and only two of the three are strictly
`absent`-narrowing. `unregistered_kind` and `not_triggered` are evaluated as the **last two** branches
before the `absent` fall-through, in that order, so neither can override a positive observation about
a specific bot — only what would otherwise have been `absent` is refined. Their order between
themselves is deliberate: `unregistered_kind` is per-bot and decisive about the NAME, while
`not_triggered` is PR-wide and decisive only about the RUN, so a token that answers to no reviewer is
reported as such rather than being absorbed into a PR-wide "nothing ran" that would send the operator
to trigger a review no configured name could ever credit. `participated_stale` is narrower in origin
but not in effect: it is evaluated after the
refusal branches but **before** `in_progress`, so a bot observed in both sets is classified
`participated_stale` rather than `in_progress`. That precedence is deliberate — a review that exists
but predates this HEAD is a more actionable signal than an in-flight run of unknown outcome, and it
carries the cheaper remedy (re-trigger rather than wait). A **refusal outranks a stale publish**: a
bot with both is classified refused, because the refusal is newer still (it names a reason the bot
will not review now, whereas a stale publish only says the last review predates this HEAD).

### Severity by classification

The taxonomy member describes *what happened*; the required/optional classification decides *whether
it matters*:

- A **required** bot resolving to `absent`, `not_triggered`, `unregistered_kind`, `in_progress`,
  `refused_awaitable`, `refused_hard`, `refused_unknown`, `refused_structural`, `participated_stale`,
  or `declined` is a completeness failure — the step is not markable done without an explicitly
  recorded force-done reason.
- An **optional** bot resolving to any member never blocks.
- Any bot resolving to `participated_but_empty` is accounted-for regardless of classification.

A completeness failure is not one undifferentiated state: several blocking members name a **different
remedy** than the others — `participated_stale` (re-trigger the stale review), `not_triggered`
(trigger the review at all), `declined` (accept the decline, because re-triggering a bot that will
not review this commit is futile), and `refused_structural` (split the diff, accept the gap, or
disable this reviewer for this PR — **never** wait) — so a consumer that renders every blocking member
as "the bot did not review" discards the one thing the widened taxonomy exists to carry.

⛔ **`refused_structural` is the member on which offering the wrong remedy is worst**, because the
wrong remedy there is not merely unhelpful but *unavailable*: waiting is an action the operator can
take that is guaranteed not to work. A prompt that lists it has spent the operator's attention on a
non-option and left the real remedies unnamed. Any consumer that renders a remedy set for a refusal
MUST take it from the member, and MUST NOT offer `await` on this one.

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
| `issue_comment` | A PR-level comment a bot declares as a publish shape is a review artifact it emitted against the diff — it counts on its own terms, not because the bot has no other shape. | CodeRabbit, PR-Agent |

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

### The currency rule — an in-place re-reviewer's credit is evaluated against the commit being merged

**A currency-tested participation credit is valid only against the merge candidate: such a review
counts iff the commit it reviewed is the merge candidate's HEAD, and that verdict is a pure comparison
that consumes no observation state, so it is identical however many times it is evaluated while the
merge candidate remains resolvable.**

That qualification is the honest reach of the claim, not a hedge. The merge-candidate SHA is read per
fetch from a fallible provider call, so a resolved-then-unresolved sequence moves the verdict from a
credit to the undecidable outcome without any observation state having been consumed. Idempotence
holds over repeated evaluation, never over a changed ability to read the head — and stating the reach
that narrowly is what keeps this contract from asserting of the verdict what its own producer does
not.

**The rule's reach is exactly the bots whose registry record declares
`participation_requires_update: true`** — the in-place re-reviewers. That is the set the producer
gates the currency test on, and it is narrower than *every* site that credits participation. A bot
declaring `participation_requires_update: false` is credited on the presence of a comment in one of
its declared `participation_evidence` publish shapes, and **no commit is compared** — see § "The
currency-blind path for append-per-review bots" below, which records that reach difference as an
accepted, bounded gap rather than leaving it to be inferred from the rule's silence. The reach is a
registry-derived property, never a fixed list of bot names: a bot that newly declares
`participation_requires_update: true` is currency-tested from that declaration onward, with no change
here.

The rule exists because the artifact that merges is **one commit**, while the barrier was asking a
per-PR question — *"did the bot participate on this PR?"* — that a loop-back, rebase, or force-push
leaves answered `yes` for a tree no reviewer ever saw. Anchoring the credit to the merge candidate's
SHA closes that false positive; making the credit a pure SHA comparison rather than a consumed
observation closes a second defect, the **observer effect** — a credit derived by *looking* changed
its answer on the second look, so the same unedited comment at the same HEAD flipped from
`participated` to `participated_stale` between one fetch and the next.

#### A wait's completion arm is timestamp-anchored, and that is correct

`github_ops pr wait-for-comments` ends its poll on a movement arm that fires when a bot declaring
`participation_requires_update` has edited its persistent comment since the wait started — a
**timestamp** anchor, where this rule anchors a credit on a **commit SHA**. The recorded answer is
that the timestamp anchor is **correct for that arm**, and the divergence from this rule is not a
defect: a wait asks *"did anything move since I started?"*, which is a different question from *"did
this review the merge candidate?"*. A poll is a scheduling decision — when to stop waiting and fetch
— and movement since the wait began is the observable that answers it. Anchoring the poll on the
merge-candidate SHA instead would end the wait on a comment that never moved, and would run an
in-place re-reviewer to the full timeout, because such a bot's comment count never grows.

The arm therefore grants no participation credit: it decides when to stop polling, and the credit is
granted only by the currency test the producer applies afterwards. A movement match proves a
re-review **arrived**; whether that review is current is decided against the commit, by this rule.
That is a recorded classification rather than a gap, and no follow-up is filed against the wait
predicate.

#### The currency-blind path for append-per-review bots — an accepted, bounded gap

A bot declaring `participation_requires_update: false` **re-reviews by posting a new comment**, so its
credit is granted the moment a comment of its in a declared publish shape is observed. No commit is
compared, and the currency ledger holds no row for it. **The consequence, stated plainly: a comment
such a bot posted against a commit that is no longer the merge candidate still credits it.** After a
loop-back, rebase, or force-push, an append-per-review bot can therefore be counted toward the quorum
on a review of a tree that is no longer the one being merged — the same false positive the currency
rule closes for in-place re-reviewers, still open on this path. Two states are unreachable for such a
bot in consequence: it never resolves `participated_stale`, and it never appears in
`undecidable_participation_bots[]`.

**Why the gap is accepted rather than closed here.** Closing it means anchoring every bot's credit,
which is a different mechanism from the one the currency test implements: the ledger records
`(reviewed_commit_sha, updated_at)` per credited comment precisely because an in-place re-reviewer's
comment identity does not change between reviews, and the ledger is what supplies the missing "which
commit did this one comment read?". An append-per-review bot's comments do not need that ledger to be
told apart — but neither do they carry a reviewed SHA, so anchoring them requires deciding what a new
comment's presence proves about the commit it was posted against, which is a **new** contract
question rather than a wider application of this one. Widening the reach without settling it would
replace an over-credit with an equally unfounded verdict in the other direction.

**What bounds it.** The gap is bounded to bots declaring `participation_requires_update: false`, and
this contract's other gates are unaffected by it: the `not_triggered` PR-wide observable, the refusal
members, the pre-merge comment barrier, and the `declined` detection via `head_sha_verified` all still
apply to such a bot. It is also self-limiting in the common case — an append-per-review bot that is
re-triggered on the advanced HEAD posts a NEW comment, so the next fetch credits it on evidence that
does post-date the merge candidate.

**When it is revisited.** Either of two observations reopens it: a required bot declaring
`participation_requires_update: false` observed satisfying the quorum on a merge candidate it
demonstrably did not review, or a decision to anchor every bot declaring `participation_evidence` —
which is the alternative disposition, deliberately **not** taken here. That alternative changes the
barrier verdict for every consumer project whose `required_bots` includes an append-per-review bot, so
it is a contract change with its own blast radius, not an implementation detail of this rule.

### Evidence for a bot that edits one comment in place

A bot that re-reviews by **editing its single persistent comment** rather than posting a new one
declares `participation_requires_update: true`. For such a bot the comment's continued existence
proves only that it reviewed **once, at some commit** — after a loop-back or force-push the unchanged
comment would silently credit it with reviewing code it never saw. Applying the currency rule, its
evidence requires the comment to prove a review of the **merge candidate**:

- the **currency ledger** — the SOLE source this test reads — anchors the comment to the
  merge-candidate SHA. That ledger records, per `(bot_kind, comment_id)`, the merge-candidate SHA and
  the `updated_at` at the fetch that LAST credited that comment, and it records them whether or not the
  comment produced a finding — so a comment the pre-filter drops is anchored exactly as one that was
  filed, and no second set of SHAs is consulted or unioned in; **or**
- it was **edited in place since it was last credited** — `updated_at` differs from the **recorded**
  `updated_at` the currency ledger holds for that credit, never from `created_at` — a fresh review at
  the current tree. Comparing against the recorded value is what stops the arm from becoming a
  permanent "was ever edited" flag: an edit at commit N credits N, and not N+1 unless a further edit
  lands. An absent `updated_at` reads as no movement, which is the fail-closed direction; **or**
- this fetch is the **first observation** of the comment — a **bounded assumption**, never a verified
  fact. A fetched comment carries no reviewed SHA, so nothing in it says which commit the bot actually
  read, and the ledger's silence says only that this plan has not seen the comment before — which is
  not the same as the bot not having published it earlier. The assumption errs toward **crediting**: a
  comment that in truth reviewed an **earlier** commit is credited at the merge candidate. One guard
  bounds it on this arm specifically: when the merge-candidate commit's own timestamp can be read, a
  comment whose timestamps predate that commit is refused, because it demonstrably existed before the
  code did. The guard does not turn the assumption into a verification — a comment posted after the
  commit is still credited without proof that it read it.

**An unreadable merge candidate withholds the credit on EVERY arm, not on one of them.** With no
readable head SHA there is no commit for any arm to anchor against: a recorded SHA has nothing to
equal, an edit proves a fresh review of *something* without saying of what, and a first observation
cannot be tied to the tree being merged. All of them therefore fail closed, and the bot is reported as
`undecidable_participation` rather than as stale, since a re-review trigger cannot fix a failed read.
The uniformity is itself load-bearing: failing closed on every arm is what keeps the verdict stable
across a failed read, because a later fetch that likewise cannot resolve the head reaches the same
blocking answer instead of flipping.

A comment recorded against an **earlier** commit, unedited, fails the test. Because the test is an SHA
comparison rather than a first-seen tally, re-running the fetch at the same HEAD — for as long as that
HEAD stays resolvable — returns the same answer, so the credit no longer depends on how many times the
plan has looked. Losing the ability to read the head is the one thing that moves the answer, and it
moves it to the undecidable outcome rather than to a credit. No participation path reads the
observation ledger (`observed_keys`) as a currency signal.

A failed currency test is **not the same as no evidence at all**, and the taxonomy keeps the two
apart: the bot published in a declared shape, so the producer reports it in
`stale_participation_bots[]` and it resolves to `participated_stale` — blocking, but with a
re-review trigger as the remedy. Discarding the failed currency test toward `absent` would lose
exactly that distinction and prescribe escalating a reviewer whose review only needed refreshing.

### Detecting a decline — the bot answered without reviewing this commit

`participated_stale` catches *a review anchored to a commit that is not the merge candidate*; it
cannot catch *no review at all, answered as engagement*. Those are disjoint. When a re-review is triggered for the merge
candidate and the bot answers with a comment that carries **no reviewed-commit SHA**
(`head_sha_verified: false` from the re-review await), the bot **declined** to review this commit — an
**incremental-review decline**. A refusal at first pass leaves no reviewed-SHA to compare, so there is
nothing stale to detect; the currency rule has nothing to work with, and the decline must be recorded
in its own right.

Such a bot resolves to the **`declined`** taxonomy member — blocking, and excluded from the quorum
exactly as `participated_stale` is, but with a **distinct remedy**: re-triggering an incremental-review
bot that already declined produces another decline, not a review, so the productive action is to
accept the decline (move the bot to `optional`, or record an operator merge-authorization) rather than
to trigger again. `declined` is distinct from the four refusal members, which name an explicit
rate-limit / quota / size **refusal notice**; the decline is the quieter shape — the bot answered, but
its answer named no commit.

The deciding bit — whether the re-review produced a review of the new HEAD (`head_sha_verified: true`)
or only a comment (`head_sha_verified: false`) — is **computed and must be consumed**: a `matched:
true` with `head_sha_verified: false` is a decline, never a completed re-review, and a consumer that
reads `matched` alone credits a review that never named the commit it matched.

#### The reviewed-commit reference is recognised wherever it sits, and compared for EQUALITY

`head_sha_verified` is decided by whether a review's reviewed-commit evidence **references** the
awaited HEAD — not by whether that evidence *is* the bare SHA. The same reviewed-commit value arrives
in more than one shape: a bare hex token, or the SHA carried inside a `…/commit/{sha}` permalink. Both
name the same commit, so both MUST verify.

⛔ **This predicate fails toward BLOCKING, which is the opposite direction from the rest of this
contract's refusal handling, and is why the recognition must be wide.** A reference the matcher does
not recognise falls through to the weaker comment discriminator and publishes `head_sha_verified:
false` — a `declined` verdict the bot never made, on the one member whose documented remedy is to
ACCEPT the decline rather than re-trigger. The false verdict therefore stops a merge AND steers the
operator away from the retry that would have exposed it, so a narrower recogniser is not merely less
useful here, it is strictly worse.

**Widen WHERE the SHA may sit, never WHICH commit counts.** Every token recovered from the evidence is
compared for **equality** against the awaited HEAD; an abbreviation or leading run never matches.
Widening the comparison instead of the location would credit a review of some other commit as a review
of this one, and would leave a negative control unable to tell *found the awaited commit* from
*matched something SHA-shaped*.

Worked example — awaited HEAD `a1b2c3d4e5f60718293a4b5c6d7e8f9012345678`:

| Reviewed-commit evidence | `head_sha_verified` | Why |
|---|---|---|
| `a1b2c3d4e5f60718293a4b5c6d7e8f9012345678` | `true` | The bare token equals the awaited HEAD. |
| `https://github.com/{owner}/{repo}/commit/a1b2c3d4e5f60718293a4b5c6d7e8f9012345678` | `true` | The permalink CARRIES the awaited HEAD — the location differs, the commit does not. |
| `https://github.com/{owner}/{repo}/commit/0f1e2d3c4b5a69788796a5b4c3d2e1f098765432` | `false` | The same shape naming a genuinely different commit: the negative control the widening must still fail. |
| `https://github.com/{owner}/{repo}/commit/a1b2c3d4e5f6` | `false` | An abbreviation of the awaited HEAD — equality, never prefix. |

A widening asserted only by its positive case cannot show it did not simply match everything, so the
two permalink rows differ only in which commit they name, and the abbreviation row pins the equality
boundary the location widening must not cross.

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

A bot whose `refusal_patterns[]` is empty has no observed refusal shape, so no refusal is claimed on
the strength of a pattern it never declared. That is the fail-closed default for **this arm** — but it
is not the whole of that bot's recognition, because recognition is enumerative.

### Refusal recognition is ENUMERATIVE, and a rewording nobody enumerated is its own state

Recognition works by enumerating shapes that have been **observed**, so its reach is bounded by what
has been written down. Two consequences follow, and both are properties of the mechanism rather than
gaps in any one bot's record:

- **A bot whose `refusal_patterns[]` is empty rests entirely on the arms that do not read its
  registry record.** Nothing about that is hypothetical: PR-Agent declares an empty list today, and it
  is one of the bots this repository's merge barrier treats as *required* — so a reviewer whose
  silence actually blocks a merge has no registry counterexample on file.
- **A refusal REWORDED past every enumerated shape is recognised as an
  `unrecognised_refusal`** — not filed as review feedback, and not credited as participation. It
  resolves to the `refused_unknown` member, because an arm that could not read the notice supports no
  claim about it; asserting a reset window nobody observed would be worse than admitting ignorance.
  This arm is **fail-safe and inert until a threshold is measured**: it fires only under a derived
  `UNRECOGNISED_REFUSAL_MAX_CHARS`, and at the shipped value of `None` it never fires at all, so the
  behaviour described here is what the arm does once armed rather than what the stack does today.
  Read that as the arm's shipped state, not as a caveat on the rule: with no threshold the recognition
  stack behaves exactly as it did before this arm existed.

**The rule applies at BOTH recognition sites**, and stating it for one only is how the second came to
carry the gap unnoticed: the filing pre-filter (`github_pr fetch_findings`) and the re-review matcher
(`github_re_review`) each run the same stack and each report the same state. A rule documented for the
producer alone would leave the matcher silently exempt — which is exactly where the worse failure
lived, since an unrecognised refusal reaching the matcher was admitted as a genuine review carrying
`head_sha_verified: true`.

The remedy the state carries is a **mechanism, not a description**: each record names the registry
file and the field to add the observed phrasing to, and carries the withheld excerpt to add. Filing it
moves that phrasing into the registry arm, where the next fetch reads it as an ordinary recognised
refusal.

⛔ **Do not restate here how many reviewers are registered, how many declare an empty list, or how
many arms the stack has.** Every one of those figures moves whenever a bot or an arm is added, and a
restated count is a duplicated fact with no mechanical link to its source. The rule is written so that
the next reviewer registered inherits it with no edit here and no number to correct.

### A refusal resolves by `rate_limit_class` BY DEFAULT, displaced by two overrides

A recognised refusal resolves to exactly one of **four** members. The refusing bot's registry
`rate_limit_class` — a three-valued field (`awaitable_window` / `hard_quota` / `unknown`), not a
boolean — supplies the **default** member. Two **per-refusal observations** displace that default, and
both are consulted before it:

| Observation | Member | Meaning |
|-------------|--------|---------|
| **override (first) —** `cause: size` (any `rate_limit_class`) | `refused_structural` | A ceiling on the diff itself. The same request never succeeds at this size, so **no wait is productive** — the remedies are split / accept / disable-for-this-PR. |
| **override (second) —** no arm of the recognition stack could READ the refusal (any `rate_limit_class`) | `refused_unknown` | Nothing was READ, so nothing is known — least of all whether the window reopens. Deferring to the declared class here would assert a reset time nobody observed. |
| *default —* `awaitable_window` | `refused_awaitable` | The limit reopens on its own; awaiting the reset is productive. |
| *default —* `hard_quota` | `refused_hard` | A budget that does not reopen on a useful timescale; awaiting it only burns budget. |
| *default —* `unknown` | `refused_unknown` | The registry declares ignorance — the refusal shape has never been observed, so whether waiting helps is not known. |

**The two overrides CAN both hold, and the `size` cause is consulted first.** They would be
contradictory only if they described the SAME refusal — a `size` cause is READ from the notice's own
text, which is what the unrecognised override denies. But both are per-**bot** aggregates over that
bot's refusals: the producer emits one `unrecognised_refusal[]` record per COMMENT, and the consumer
receives a bot-kind list. A bot that published one refusal an arm read as a size ceiling and another no
arm could read therefore satisfies both, from two different notices, with neither observation wrong.

The positively-read cause wins, because an absence must not erase a ceiling the run actually
extracted — taking the unrecognised override first would discard that figure and leave the operator
deciding without the one remedy already in hand (split the PR under the stated cap). The ordering is
safe in the awaitability direction, which is what makes it the conservative choice and not merely the
more informative one: both members it can yield are non-awaitable, so neither order can offer a wait on
a bot carrying an unreadable notice. The orders differ only in whether the operator is told WHY.

**Why both overrides outrank the class.** `rate_limit_class` is declared once per **bot**, while each
override is observed per **refusal**. One bot can refuse for both causes at a single class — Sourcery's
per-PR size ceiling and its weekly quota are both `hard_quota` — so the per-bot field cannot separate
them even in principle, and the more specific observation is the one that must win. The same reasoning
carries the second override: a bot's declared class describes the refusals whose shape has been
observed, and says nothing whatever about one that reached no arm at all.

Reading the class first would keep both cases invisible in exactly the situation that matters most,
and by the same mechanism: a bot declaring `awaitable_window` would resolve `refused_awaitable` —
whose whole meaning is *worth awaiting* — for a size ceiling that waiting cannot move, and equally for
a notice no arm could parse.

`review_completeness._refusal_state()` is the one place this mapping lives. The class arm is total and
injective: no class value collapses into another, and any value that is neither of the first two —
including a malformed or absent one — resolves fail-closed to `refused_unknown`. The mapping was once a
binary `== 'awaitable_window'` test, which folded `unknown` into `refused_hard` and so rendered a
declared *we-do-not-know* as a positive *hard quota* finding. That is the defect `refused_unknown`
closes: a declared ignorance is not a hard quota, and an operator shown `refused_hard` is steered
toward "waiting is futile, force it" for a refusal that might have reopened on its own.

### Two axes: awaitability and CAUSE — and the cause is state-determining for `size`

`rate_limit_class` is the **awaitability** axis (can the caller usefully wait?). It is distinct from the
refusal's **cause**, which the same bot can carry more than one of: Sourcery declares TWO `hard_quota`
refusals with different causes — a per-PR **diff-size ceiling** (`"your pull request is larger than the
review limit of"`) and an account-level **weekly quota** (`"reached your weekly rate limit of"`). Both
are `hard_quota` on the awaitability axis, yet their remedies differ — a size refusal needs a smaller
diff, a quota refusal needs backoff — so a participation *rate* pooled across the two mis-attributes
both.

The cause axis is wired as a per-refusal overlay. Its `size` value **decides the member**; every other
value is advisory and leaves the awaitability split untouched:

- **Registry:** each bot declares `refusal_size_patterns` — the subset of its `refusal_patterns` whose
  cause is a diff-size ceiling. Every other refusal is a rate/budget quota. Sourcery declares its size
  ceiling there; its weekly-quota notice is deliberately absent, so it classifies `quota`. A bot
  declaring a non-empty `refusal_size_patterns` is a bot with a structural ceiling, which is what makes
  the exclusion disclosable **in advance** (below).
- **Derivation:** `_github_pr.refusal_cause(body, bot_kind)` returns `size` iff a `refusal_size_patterns`
  entry matches, else `quota`. It assumes a body already recognised as a refusal, so it names the cause
  rather than re-detecting it.
- **Cap extraction:** each bot may also declare `refusal_size_cap_patterns` — extraction regexes that
  read the **ceiling the notice itself states**. `_github_pr.refusal_size_cap(body, bot_kind)` returns
  that figure, or `''` when the bot declares no pattern or the notice states none. The exact mirror of
  `rate_limit_eta_patterns`, one axis over: an awaitable refusal states *when* it reopens, a structural
  one states *how big* the diff was allowed to be. The figure is **read, never declared** — a declared
  constant goes stale silently when the provider changes its budget, whereas the notice's own figure is
  first-party evidence captured at the moment of refusal, which is what makes a recorded gap auditable
  against the diff that was actually refused. An absent cap is reported as `unknown`, never defaulted.
- **Producer:** `github_pr fetch_findings` emits `refused_causes[]` — one `{bot_kind, cause}` per
  refusing bot (`size` sticky: a bot that posted both records `size`) — and `refused_size_caps[]`, one
  `{bot_kind, cap}` per bot whose size notice stated a ceiling.
- **Classifier:** `review_completeness check --refused-causes --refusal-size-caps` resolves a `size`
  cause to `refused_structural` and reports `refusal_causes[]` as `{bot_kind, cause, cap}`. The cause
  flag is shared by `check` and `deficit`, so the two commands can never name different members for one
  refusal.

The invariant this enforces: **do not report a participation rate over a corpus pooled across causes** —
a size refusal and a quota refusal have different remedies, so a rate that mixes them mis-attributes
both. The partition is a computed signal, not merely a documented possibility.

#### Advance disclosure — a size ceiling is knowable before the review is requested

Every other verdict in this contract is computed from an **observed** refusal, so the gap is only ever
discovered after a reviewer has already declined — at the merge gate, where the remaining options are
expensive. A size ceiling is different in kind: it is a declared property of the **reviewer** rather
than an outcome of the run, so *that a reviewer carries one* is answerable before any review is
requested.

⛔ **What is disclosed is the reviewer's ceiling, never this diff's verdict.** The surface reads the
registry and no PR, and it emits no figure a diff could be compared against — so it cannot tell a plan
whether its own diff exceeds a reviewer's limit, and no consumer may render it as though it had. A plan
learns WHICH reviewers carry a ceiling and, separately, whether that ceiling's value is recoverable at
all; it does not learn that it is over one. The figure itself exists only in a refusal notice the
reviewer has already published.

The disclosure is still worth having because a ceiling recurs **by size rather than by chance**: it is
fixed, so a reviewer carrying one refuses over-size plans predictably and forever, and knowing at
outline time which reviewers those are turns an unexplained merge-gate non-participation into an
anticipated one. `review_completeness size-caps` is the surface a plan consults for this. It takes no
plan and reads no PR — the answer is registry data — and reports per registered reviewer:

- `structural_cap` — whether it declares a size-caused refusal at all, **derived** from
  `refusal_size_patterns` so the disclosure can never disagree with the classification above.
- `cap_extractable` — whether the cap's *value* is also recoverable from its notice. Reported
  separately and honestly, because the two are independent: a reviewer can have a ceiling nobody has
  taught the registry to read, and collapsing them would let "declares a ceiling" be misread as "the
  ceiling's value is recoverable".

**Rejected alternative — declare each reviewer's cap as a registry constant (`declared_cap`).** It
would let this surface emit a comparable figure and so answer the *is my diff over it?* question the
disclosure deliberately does not. It is rejected for the reason `refusal_size_cap_patterns` already
encodes at `_github_pr.refusal_size_cap`: a declared figure is an assertion that goes stale
**silently** the moment the provider changes its budget, and nothing in the pipeline would notice it
had. The notice's own figure is first-party evidence captured at the moment of refusal, which is what
makes a recorded gap auditable rather than asserted — so the disclosure stays honestly narrower rather
than confidently wrong.

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
| Surfaced? | **Yes** — the bot is named in `fetch_findings`'s `refused_bots[]` and forwarded to `review_completeness check --refused-bots`, with its cause and stated cap alongside. A refusal no arm could READ is surfaced in `unrecognised_refusal[]` instead and forwarded via `--unrecognised-refusal-bots`. | This is what lets the taxonomy assign a refusal member — by the bot's declared class, displaced by whichever override the observation carries — instead of inferring absence from silence. |
| Counted as participation? | **No** — the refusing comment is excluded from `participated_bots[]`. | A refusal is published in one of the bot's declared publish shapes, so without an explicit exclusion the shape alone would credit it as a proven participant. |

This is also why `refusal_patterns` must never be unioned into the producer's `ignore_patterns` drop
set: doing so collapses the very distinction the two-field split exists to carry.

### The three per-bot marker lists answer three different questions

A bot's registry doc declares three independent marker surfaces that each drive a **comment-level**
outcome (drop or branch). They are easy to confuse because all three are literal-substring lists read
by the same producer, but each drives a different outcome and none is a superset of another. (The
`refusal_size_patterns` overlay from § "Two axes" is deliberately NOT one of these three: it drives no
comment-level outcome — it labels a refusal's CAUSE, which selects the `refused_structural`
member rather than dropping or keeping a comment — and it is by design a subset of
`refusal_patterns`, so the no-superset property here is scoped to these three comment-level surfaces.)

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
say a dropped comment can never resolve to a blocking state. Credit still has to clear the currency
rule below, and `review_completeness.classify_bot()` assigns `participated_but_empty` only to a
bot present in `proven_participants` — a bot absent from `participated_bots[]` falls through to an
unproven state that blocks the quorum. The reading that follows turns on a CONDITION, not on a named
roster: it applies to a bot that declares `participation_requires_update` **and** opts into the
contentless drop by declaring `contentless_review_markers` — PR-Agent is one such bot, and any
registry doc can add another. For such a bot an unchanged clean comment is credited while the merge
candidate is the commit it was reviewed against, and denied once HEAD advances past that commit, so
once a loop-back or force-push moves HEAD a dropped clean Guide resolves
to **`participated_stale`, not `absent`** — the producer saw the comment in a declared publish shape
and reports the bot in `stale_participation_bots[]`, so what it records is a review that predates the
merge candidate rather than a reviewer that never engaged. That is the intended reading of a stale
comment, not a defect in the drop, and the member it lands on is the one whose remedy — re-trigger the
review — actually fits it.

**Surviving the drop is not the same as being exempt from the currency rule.** For a bot
declaring `participation_requires_update` the evidence that survives the drop must still prove a review
of the **merge candidate** (§ "The currency rule"). Keeping that rule live across a drop takes an
explicit mechanism, because a dropped comment by definition files no `pr-comment` finding, so nothing
in the findings store says which commit it was read against. The producer therefore keeps the anchor
in ONE place for every credited comment alike — the plan-scoped **currency ledger**, which records
each comment's `(bot_kind, comment_id)` key together with the merge-candidate SHA and the `updated_at`
at the fetch that last credited it. The currency rule is evaluated against that ledger and against
nothing else: a dropped comment and a filed one are anchored by the same record, so there is no second
set of SHAs to union in and no shape of comment the rule reaches only indirectly. A dropped comment's
recorded SHA is the commit it was credited against; a later HEAD reads as stale, and an `updated_at`
that differs from the recorded one credits the bot again.

The ledger holds **observation records, not findings**: they are never returned by a findings query,
never enter the pending-findings gate, and never reach operator triage, so the triage queue stays as
clean as the drop intends. Recording them as findings in any resolution state would put routine
clean-review boilerplate back in front of the operator, which is the defect the drop exists to
remove. Without the record the currency rule has no SHA for a dropped comment to compare, so a bot
whose one stale comment never changed could not be told apart from one reviewing the merge candidate —
the exact false positive `participation_requires_update` exists to close.

## The counting rule

The epic's single source of truth for **how a reviewer's output is counted**, so every consumer counts
the same way and no rate is computed over an invisible denominator. Three named quantities, each with
its population published:

- **The finding count**, per reviewer per PR, is the number of filed `pr-comment` findings attributed
  to that reviewer's `bot_kind`. It is the FILED count — *after* the producer's pre-filter has dropped
  noise, refusals, self-responses, and cross-iteration duplicates — never a raw comment count and never
  a count of review-body summaries. A naive comment count is wrong in **both** directions: one
  reviewer's findings can arrive across several review bodies (a `"Actionable comments posted: 3"` then
  a `"1"`), which over-counts if the summaries are counted and under-counts if only the last is; and a
  reviewer's inline threads carry its own acknowledgement replies, which are not findings. Counting
  filed findings sidesteps both, because the producer already collapsed those shapes.

- **The reviewed-at-all predicate** — a reviewer reviewed the diff iff its taxonomy state is
  `participated` or `participated_but_empty`: a proven publish shape against the merge candidate. Every
  other state — the four refusals, `absent`, `not_triggered`, `in_progress`, `participated_stale`,
  `declined` — is a non-review, so it can be neither a deficit baseline nor a meaningful finding count.
  `participated_but_empty` (reviewed, found nothing) counts as a review with a count of zero; it is
  **never** collapsed into "did not review".

- **The required-vs-optional denominator** — the populations every rate is computed over, published so a
  denominator is never invisible: the **required set** (`required_bots` — gates the completeness
  quorum), the **optional set** (`optional_bots` — reported, never gates), and the **enabled roster**
  (required ∪ optional — the review-retrospective's row domain, so a reviewer that produced nothing
  still has a row). A rate reported without its population is the defect this rule exists to remove.

## The comparative deficit signal

A required reviewer that produces materially fewer findings than a reviewer that **actually reviewed
the same diff** is a reviewer-quality bug, and is reported as one. "No findings" from a single reviewer
is a legitimate result and never a defect on its own; the defect is comparative — a deficit *against a
baseline*.

This signal is **observability, never a gate**:

- It is **not a merge verdict.** The reviewer *did* provide a result, so participation and the merge
  decision are unaffected. `review_completeness deficit` carries `gates_merge: false` and `proves:
  reviewer_quality_only` in as many words. Turning it into a gate would block a merge on a third party's
  output.
- It is **not a participation verdict.** A required reviewer with a deficit still satisfies the quorum
  (it participated); a deficit is a statement about *yield*, computed only over reviewers that reviewed.

It fires **only against a real baseline** and is otherwise silent:

- **deficit** — a baseline exists (some non-required reviewer reviewed the same diff) and a required
  reviewer that reviewed produced materially fewer findings than the baseline's best.
- **clean** — a baseline exists and no required reviewer under-produced; `0 : 0` against a baseline that
  reviewed and found nothing lands here, never in `deficit`.
- **unassessable** — NO non-required reviewer reviewed the diff, so there is no baseline and the run is
  evidence neither way. When every other reviewer refused, nothing reviewed the diff besides the
  required bot; the signal must not manufacture a reviewer-quality bug out of rate limiting the pipeline
  already accepts as normal.

**Do not pool measurements across the instruction-generation boundary.** A change to a reviewer's
instructions (a domain-scoped charter, an agent-instructions file newly resolving in a repository)
changes the quantity being measured, so a deficit measured before such a change and one measured after
are not the same number. Which charter a PR's reviewer was running is part of the population a deficit
is reported over.

## The review-versus-gate delta

*"What did review catch that the in-house gates did not"* is the only direct read on gate/review parity
available, and it arrives free on every PR. `review_gate_delta assess` is the measurement; this section
is its contract. It is a signal about **the gates' reach** — never about a reviewer, and never a merge
verdict (`proves: gate_escape_only`, `gates_merge: false`).

**A finding review files against a tree the gates already passed is a gate escape** — something the
gates ran over and did not report — so no per-finding gate attribution is needed. The in-house gates
run before review: `pre-push-quality-gate` at `order: 5` and `pre-submission-self-review` at `order: 7`,
against `automatic-review` at `order: 30`. That is what makes the signal free rather than a bespoke
study.

⚠ **"The gates passed" is not the same claim as "the gates saw this tree", and the gap is real on an
ordinary forward pass.** Two `mutates_source: true` steps run BETWEEN the gates and review —
`finalize-step-simplify` (`order: 8`) and `finalize-step-security-audit` (`order: 9`) — and the
dispatcher's re-entry check only re-fires a step the loop REACHES. A forward pass runs
5 → 7 → 8 → 9 → 11 → 20 → 30 monotonically and never returns to order 5, so lines those two steps
introduce reach the reviewer having never been gated. Counting a finding on such a line as a gate
escape attributes to the gates a miss they were never given the chance to make.

The escape claim therefore rests on three inputs, each failing closed: the gate **verdict** (a red gate
escaped nothing; an absent signal is unsubstantiated), the **gate-certified tree** (`head_at_completion`
from the gate step's record), and the **reviewed tree** (`reviewed_commit_sha` from the findings). The
two trees must be shown EQUAL, not assumed — a missing SHA is not evidence of sameness, and a mismatch
is positive evidence of the gap above. The unblocking condition is for the gate to re-fire after the
mutating steps; that is a change to the finalize step ordering, not to this measurement.

### Two properties, both structural rather than advisory

**1. Refusal-PRs are excluded BY CONSTRUCTION.** The bots refuse frequently, so an absence of review
findings is very often an absence of *review*, not of defects. ⛔ **A parity metric that does not
exclude refusal-PRs will report improving parity as coverage collapses** — this epic's named failure
mode, and the reason a metric that can produce it must not ship.

The guard is that `structural_share` is emitted **only at full coverage** (every roster member in the
reviewed-at-all set). A collapse can then only ever move the metric from *a number* to *no number*,
never to a better number. **Partial** coverage is withheld for the same reason and it is the dangerous
case: a collapse silently re-weights the partition. If the reviewer that finds the gate-addressable
defects goes quiet, every surviving escape is structural and a naive share reports 100% — *"the gates
are perfectly configured"* — when the only thing that changed is who spoke.

**2. Partition BEFORE computing any rate.** The escape set is **mixed**, and conflating its halves is
how a fixable configuration hole gets recorded as irreducible residual:

| Partition | Meaning | What it is evidence of |
|---|---|---|
| `gate_addressable` | An in-house gate COULD have caught it — a lint family absent from the `select` list, an un-enabled check | A gate **configuration** finding. Actionable on our side |
| `gate_structural` | No in-house gate CLASS reaches it however configured — documentation-prose semantics, report-claim consistency, behaviour under inputs no test supplies | The genuine residual the parity question is about |
| `unpartitioned` | No admissible label supplied | Nothing. It **withholds** the share |

An escape carrying no admissible label is never defaulted into a bucket — defaulting would let a typo
move the number — so an unlabelled escape withholds the share exactly as partial coverage does.

### A withheld share is not a withheld observation

The escapes a partial or unlabelled round surfaced are real, and are still reported with their
per-partition counts and their populations. Only the **ratio** — the thing a shrinking denominator
corrupts — is withheld. Every figure publishes `reviewer_coverage`, `enabled_bots`, `reviewed_bots`,
`gate_head_sha`, `reviewed_head_sha`, and a `provenance` string naming how the escape set was
derived, because a rate reported without its population is the defect § "The counting rule" exists to
remove. The two SHAs are echoed for the same reason the reviewer sets are: a reader can then see
WHICH trees were compared rather than trusting that they were.

⛔ **The provenance names a SELECTION EFFECT, and a consumer must carry it.** On the current finalize
step ordering the tree check excludes most real PRs, so a column of `excluded` accumulates. That
column reads, over time, exactly like *"the gates caught everything"* — the misreading this whole
section exists to prevent. It means the opposite: those PRs were never measurable. A consumer
reporting this signal states that the measurable population is only those PRs where neither post-gate
`mutates_source` step committed, and that it is a biased population rather than a sample.

### What this measures and what it does not

It measures the **gates**. A high `gate_addressable` share is a to-do list for the gate configuration;
a high `gate_structural` share says the gates are configured about as well as their analysis classes
allow and the residual is genuinely review-only. ⚠ It is **not** an argument that self-review or the
gates should be trusted less: the two mechanisms have different and complementary reach, and the same
run that produced this measurement's motivating evidence had self-review catch four instances of a
stale-set defect the bots did not. Neither a volume nor a share is a coverage number.

Whether the gate-green / review-finding pairing is a **recurring** signal rather than a single
instance is a hypothesis this instrument exists to test, not one it assumes. Until enough measured PRs
accumulate, the verb ships as a measurement with **no parity claim attached**.

## Consumers

| Consumer | What it reads |
|----------|---------------|
| `automatic-review/SKILL.md` | Both lists, to drive the completion-aware poll, the re-review trigger set, and the step-done guard. |
| `github_pr fetch_findings` | Both lists, to classify each ingested comment and emit the unclassified-bot warning; each bot's `participation_evidence` / `participation_requires_update`, to derive the evidence-typed `participated_bots[]` **and the `stale_participation_bots[]` set that carries `participated_stale`**; each bot's `refusal_patterns`, to branch a refusal into `refused_bots[]` rather than drop it, and its `refusal_size_patterns`, to attribute each refusal's CAUSE into `refused_causes[]` (size vs quota), and its `refusal_size_cap_patterns`, to read the stated ceiling into `refused_size_caps[]`; the enumerative arm, to report a refusal no earlier arm could read into `unrecognised_refusal[]` — withholding the finding, denying the participation credit, and carrying the registry file and field that close the gap; each bot's `contentless_review_markers` / `actionable_content_markers`, to drop a fully clean review comment as noise. |
| `github_pr fetch_findings` → `merge_candidate_sha_resolved` | Nothing from this contract — it is the producer's report of whether the merge-candidate SHA could be READ at all. `fetch_pr_head_sha` returns `''` on any failure path, so a `false` is *"the head is unresolvable"*, never a verdict about a bot that an operator can act on. **Producer-side disclosure: no taxonomy member routes on it.** |
| `github_pr fetch_findings` → `undecidable_participation_bots[]` | Each bot's `participation_evidence` / `participation_requires_update`, to name the bots whose comment matched a declared publish shape on a fetch where the merge candidate was unreadable. Reported in **neither** `participated_bots[]` (nothing anchors the credit) **nor** `stale_participation_bots[]` (stale's remedy is a re-review trigger, which cannot fix a failed read). ⚠ **Producer-side disclosure with no classifier member yet** — the failure taxonomy above has no member for this state, so no consumer reaches it. Widening the taxonomy is a separate plan, and this field is the prerequisite it needs; the gap is stated here rather than left to surface as an unreachable branch. |
| `github_pr fetch_findings` → `refusal_pattern_drift[]` | Each bot's `refusal_patterns` and `participation_evidence`, read through the `_github_pr.refusal_layers` provenance seam at the FILING pre-filter only (never the participation loop), to emit one `{bot_kind, layer}` record per bot whose notice the STRUCTURAL arm read **while that bot's own declared `refusal_patterns` did NOT** — `layer` naming the arm that read it, and therefore always `structural_fallback`: the notice was caught by shape while the registry record missed it, so that record has drifted from the bot's current wording. ⛔ **The predicate is DIRECTIONAL, not "exactly one arm fired".** The mirror case — the registry arm matching while the structural arm does not — is the DESIGNED state for a whole class of refusals and is never emitted: a diff-size ceiling is a comparison rather than an "exceeded / reached / hit" statement, so it is invisible to the structural arm BY CONSTRUCTION (see § "Two axes"), and recording its registry-only match would report the architecture working as designed as decay. **Diagnostic only: it changes no verdict, denies no credit, and no taxonomy member routes on it** — the refusal itself was still recognised and classified normally. Deduped on `(bot_kind, layer)`, because drift is a property of the declared wording rather than of each comment carrying it. |
| `bot_registry.trigger_semantics` (accessor) | Each bot's `trigger_semantics`, from the closed set `auto_on_push` / `requires_explicit_trigger`, whitespace-stripped and validated against `TRIGGER_SEMANTICS_VALUES`, failing closed to `requires_explicit_trigger`. Closed in that direction because the errors are asymmetric: wrongly assuming a bot auto-reviews makes the pipeline WAIT for a review nobody requested, surfacing only as an unexplained timeout at the merge gate, whereas wrongly posting a trigger costs one redundant comment. ⚠ **Registry-side disclosure with no routing consumer yet** — every registered bot declares `requires_explicit_trigger`, which is exactly what the pipeline does today (it posts each bot's `trigger_comment` unconditionally), so no caller branches on the field and no behaviour changes. Its value is that the assumption the code already embodies is now DECLARED and checkable per bot: a reviewer that reviews on push becomes a one-line data edit instead of a silent mis-wait. |
| `github_pr pull_request_runs` / `ci checks pull-request-runs` | Nothing from this contract — it is the **observation channel for `not_triggered`**, answering the PR-wide question of whether any `pull_request`-event workflow run exists for the PR at all. Its verdict reaches the predicate as the single `--not-triggered` bool. |
| `review_completeness check` | `required_bots` for the quorum; `optional_bots` for reporting only; `participation_evidence` to admit each evidence pair; `rate_limit_class` for the DEFAULT refusal member (`refused_awaitable` / `refused_hard` / `refused_unknown`), displaced by two per-refusal overlays: `--refused-causes` (from `refused_causes[]`) resolves a `size` cause to `refused_structural`, and `--unrecognised-refusal-bots` (from `unrecognised_refusal[]`) resolves a refusal no arm could read to `refused_unknown`. Consumes `stale_participation_bots[]` via `--stale-participation-bots` to assign `participated_stale`, the bots that answered a re-review without reviewing the merge candidate via `--declined-bots` to assign `declined`, the PR-wide `--not-triggered` bool to refine what would otherwise be `absent`, and `--refusal-size-caps` (from `refused_size_caps[]`) to carry each structural refusal's stated ceiling. Reports `refusal_causes[]` as `{bot_kind, cause, cap}`. Emits `review_state_summary` (the reviewer-state distribution) so `display_detail` can tell reviewed-clean from nobody-reviewed. |
| `review_completeness size-caps` | Each bot's `refusal_size_patterns` and `refusal_size_cap_patterns`, to disclose IN ADVANCE which reviewers carry a structural diff-size ceiling and whether its value is recoverable. Reads no PR — the answer is registry data, so a plan can consult it before requesting a review. |
| `review_completeness deficit` | The same observation flags as `check`, to classify each bot and derive its reviewed-at-all predicate and filed finding count, then report the comparative deficit signal — a reviewer-quality observation that gates no merge (§ "The comparative deficit signal"). |
| `review_gate_delta assess` | The enabled roster (`required_bots ∪ optional_bots`) via `--enabled-bots` as the coverage denominator, and the reviewed-at-all set via `--reviewed-bots` as its numerator — both supplied by the caller from this rule's definitions rather than re-derived. Its escape count applies this rule's **filed-and-actionable** definition, review-body-summary carve-out included, matching `review_retrospective`'s classification; the two implement the same rule independently because they live in different bundles, so a change to the rule must land in both. Reports what review caught that the in-house gates did not — a signal about the GATES that gates no merge (§ "The review-versus-gate delta"). |
| `finalize-step-review-retrospective` (`review_retrospective`) | The enabled roster (`author_login` values) via `--enabled-reviewers`, to emit a row per ENABLED reviewer rather than per responding one, each carrying `participation: measured` / `unmeasurable` (§ "The counting rule" — the row-domain population); and the reviewed-at-all set (`participated` / `participated_but_empty` `author_login` values) via `--reviewed-reviewers`, to grade whether the review-quality comparison could be performed at all (`comparison: measured` / `clean` / `vacuous` / `indeterminate`) rather than reporting a benign no-op on a run where no reviewer produced content. |
| `github_ops pr wait-for-comments` | Each bot's `participation_requires_update`, to select the `updated_at`-movement arm of its completion predicate over the count-growth arm; `participation_evidence` plus `bot_kinds()`, to decide whether the await is answerable at all (`detector_answerable`). |
| `marshall-steward` | Both lists, to ask the wizard question and record the provenance. |

### Recorded exclusions

Four further surfaces mention participation or the movement test and were **swept and deliberately
excluded** from the taxonomy's documented consumer set, so their absence reads as a decision rather
than as a gap: `_github_pr.py` (the private helper the producer calls — it computes the observation
and carries no taxonomy vocabulary of its own), `standards/coderabbit.md` and `standards/sourcery.md`
(a registry doc declares per-bot data rather than taxonomy semantics; `sourcery.md` additionally
declares no `participation_requires_update`, so that bot cannot reach `participated_stale`), and
`test_pr_wait_for_comments_predicate.py` (it pins the await predicate's movement arm, which is the
*input* to the currency test rather than the classification it feeds).

See [`../SKILL.md`](../SKILL.md) for the step body that applies this contract and
[`../../manage-config/standards/data-model.md`](../../manage-config/standards/data-model.md) for the
knob storage shape and provenance field.
