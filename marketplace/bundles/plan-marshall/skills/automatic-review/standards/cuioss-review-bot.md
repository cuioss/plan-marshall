# Auto-review triage rule — PR-Agent

PR-Agent-specific triage rule for the plan-marshall `pr-comment` findings pipeline. Companion to
[`coderabbit.md`](coderabbit.md); read that first for the shared pipeline mechanics — this file
only carries what differs for PR-Agent (`cuioss-review-bot[bot]`). The machine-readable registry
block below is the single per-bot data record the `automatic-review` step consumes when
`cuioss-review-bot` is classified in the step's `required_bots` or `optional_bots`. Classification decides whether
PR-Agent's silence is a failure (required) or tolerable (optional); it does NOT decide admission — a
PR-Agent comment is ingested even when the bot appears in neither list, with a warning recorded. See
[`bot-participation-contract.md`](bot-participation-contract.md).

PR-Agent is the third reviewer beside CodeRabbit and Sourcery, deliberately narrowed to a
**security-weighted** charter. It is opt-in per repository (the repo must carry the
`reusable-pr-agent-review.yml` caller workflow). Both `required_bots` and `optional_bots` ship
EMPTY, so `cuioss-review-bot` — like every other bot — is classified per project rather than by a
shipped default.

## Grounding source

Every field and every consumer-stage shape below is stated against **two observed reviews**, and
each is marked CONFIRMED, CORRECTED, or UNVERIFIED against them. Nothing here is written from
assumption about how the bot "probably" behaves.

| | Review A — the finding-bearing shape | Review B — the clean shape |
|---|---|---|
| Repository / PR | `cuioss/API-Sheriff` PR **#103** | `cuioss/plan-marshall` PR **#1078** |
| Comment | `issue_comment` id `IC_kwDOPatrT88AAAABLvbeow` | `issue_comment` id `IC_kwDOQ3xasM8AAAABM2TS9g` |
| Author (as the provider reports it) | `cuioss-review-bot` | `cuioss-review-bot` |
| Posted | `2026-07-26T09:27:15Z` | not recorded on the observation |
| Heading | `## PR Reviewer Guide 🔍` | `## PR Reviewer Guide 🔍` |

**Review B is the only observation of the RAW API body**, captured verbatim from the quarantined
`raw_input.body` of the `pr-comment` finding it produced. Review A was recorded from its GitHub
*rendering*, which is why its assertion literals were written in markdown-bold form and why the
`contentless_review_markers` derived from them matched no real body at all — see the CORRECTED
annotation on that field. Review B verbatim:

```text
## PR Reviewer Guide 🔍  <table> <tr><td>🧪&nbsp;<strong>PR contains tests</strong></td></tr> <tr><td>🔒&nbsp;<strong>No security concerns identified</strong></td></tr> <tr><td>⚡&nbsp;<strong>No major issues detected</strong></td></tr> </table>
```

Sample size is **two reviews**, only one of which carried a finding — see "Signal calibration"
below before generalizing from them.

## Registry data block

The fenced-YAML block below is the machine-readable per-bot record. It is data, not frontmatter.
Consumers read `bot_kind`, `author_login`, `trigger_comment`, `completion_check_name`,
`honors_skip_label`, `participation_evidence`, `participation_requires_update`, `ignore_patterns`,
`review_body_summary_patterns`, `refusal_patterns`, `contentless_review_markers`,
`actionable_content_markers`, `rate_limit_class`, `rate_limit_eta_patterns`, and `severity_map`
from it; the prose sections carry the rationale. This bot declares no
`review_body_summary_patterns`.

```yaml
bot_kind: cuioss-review-bot
author_login: cuioss-review-bot   # CONFIRMED on #103 — the provider reports the author without the
                                  # [bot] suffix, and bot_kind_for_author strips the suffix anyway,
                                  # so this value resolves on both paths. A dedicated App, NOT
                                  # github-actions — see "Why its own identity". Deliberately the
                                  # SAME string as bot_kind above: the kind and the login are one
                                  # name for this reviewer, so login_to_bot_kind() maps it to
                                  # itself — see "Why its own identity" for why that is the point
trigger_comment: "/review"        # CONFIRMED on #103 — human /review at 09:25:47 -> publish 09:27:15
trigger_semantics: requires_explicit_trigger   # the /review command above must be posted
completion_check_name: ""         # CONFIRMED on #103 — absent from `ci pr reviews`, no check-run;
                                  # falls back to the review_bot_buffer_seconds wait
honors_skip_label: true           # UNVERIFIED — #103 carried no skip label, so this was not
                                  # exercised. Kept because it is enforced by the reusable
                                  # workflow's if: guard, NOT by bot config (see "Central config")
# participation_evidence: two publish shapes. The Guide comment is unconditional; inline comments
# are published when `/improve` is enabled and it has something to suggest. An absent inline count
# is therefore NOT evidence of non-participation, while a present one IS evidence of participation.
# The bot still posts NO check-run, so a check-run state remains no evidence for it on either path.
# See "Participation evidence" below.
#
# ⚠ /improve HAS TWO GATING MODES, and reading only the label one misreads participation:
#   - repository-wide — the caller passes `auto-improve: true` to reusable-pr-agent-review.yml.
#     THIS REPOSITORY IS IN THAT MODE as of #1334 (a measured pilot; see that PR for why /review
#     is not the finding surface). No label appears on the pull request, and none is expected.
#   - per pull request — the `pr-agent-improve` label, the org default while `auto-improve` is
#     false. This remains the mode for every consumer repository that has not opted in.
# The reusable workflow ORs the two (`inputs.auto-improve || contains(labels, 'pr-agent-improve')`),
# so an ABSENT label is not evidence that /improve did not run.
#
# ⚠ THIRD SHAPE, CONFIRMED on #1334: when /improve runs and finds nothing it does NOT stay silent —
# it publishes a separate `issue_comment` headed `## PR Code Suggestions ✨` reading "No code
# suggestions found for the PR." So at the PULL REQUEST surface the empty result IS distinguishable
# from a run that never happened. That distinction does NOT extend to the workflow gate: the
# reusable workflow's fail-closed gate keys on the `review` output and is deliberately not extended
# to /improve, which writes the separate `improve` key. Gate-level, the two remain one signal.
#
# ORDERING IS LOAD-BEARING: `inline` is APPENDED after `issue_comment` and must never be placed
# before it. `bot_registry.participation_evidence(bot)` returns the declared order, and
# test_bot_participation_contract.py reads element [0] to synthesize each parametrized bot's
# observed publish shape — prepending would silently re-point that harness at a different shape
# without failing any case.
participation_evidence:
  - issue_comment                 # the single persistent `## PR Reviewer Guide 🔍` comment
  - inline                        # `/improve` code suggestions, published as review comments when
                                  # the `pr-agent-improve` label gates them on
participation_requires_update: true   # a re-review EDITS that same comment in place, so continued
                                  # presence proves only that it reviewed once, at some earlier HEAD.
                                  # Evidence therefore has to clear the currency test, which reads the
                                  # plan-scoped currency ledger and nothing else: the SHA that ledger
                                  # recorded for this comment is the merge candidate, or the ledger
                                  # holds no row for it and the merge candidate resolves, or its
                                  # updated_at no longer matches the value recorded at that credit.
# ignore_patterns: CONFIRMED on #103 — the first two did not fire, and neither
# wrongly dropped the review. The fourth is CONFIRMED on #1334, the /improve pilot's own PR.
ignore_patterns:
  - "## PR Agent Walkthrough"     # /help output — commands reference, never a finding
  - "### Question:"               # /ask answer — a reply to a human, not a review finding
  - "**[Persistent review]"       # contentless "updated to latest commit" notice, authored by the
                                  # reviewer identity so it reaches this pipeline as a candidate
                                  # finding. Suppressed at source by final_update_message = false
                                  # in cuioss/pr-agent-settings; this pattern covers the ones
                                  # already posted and any recurrence if that setting is lost.
  - "No code suggestions found for the PR"   # CONFIRMED on #1334 — /improve's EMPTY result. It is
                                  # published as a SECOND, separate `issue_comment` headed
                                  # `## PR Code Suggestions ✨`, distinct from the Guide, and it
                                  # carries no finding. Without this entry every clean pull request
                                  # under repository-wide auto-improve files one junk finding for
                                  # triage — the same shape the `**[Persistent review]` entry above
                                  # exists to absorb, and newly reachable the moment /improve stops
                                  # being label-gated. Keyed on the inner sentence rather than the
                                  # `## PR Code Suggestions` heading on purpose: that heading is
                                  # ALSO the heading of a suggestion-BEARING result, so ignoring it
                                  # would drop real suggestions published in table form.
# contentless_review_markers: CORRECTED against #1078 — the three literals the Guide carries when
# it found nothing: the heading that identifies the review, plus the 🔒 and 🧪 rows' clean
# assertions, each as BARE INNER TEXT. The bare form is load-bearing, not a style choice: the two
# assertions live inside an HTML <table>, where GitHub renders no markdown, so the raw API body
# carries <strong>No security concerns identified</strong> — never the markdown-bold **…** these
# entries previously declared. The bare inner text is a substring of BOTH renderings, so the entry
# holds whichever form the bot emits. The superseded **-wrapped literals matched no observed body
# at all, which made the whole conjunction dead: two of three required markers could never be
# found, so the predicate returned False on every real clean Guide. EVERY entry is REQUIRED — the
# producer's contentless test is a CONJUNCTION over this whole list, not a disjunction, so a Guide
# missing any one of them is left in place and hand-triaged. The 🧪 clean assertion in particular
# MUST NOT be dropped from the list as an anti-noise optimization: per "Consumer stage" the
# negative 🧪 form is itself an actionable low-severity coverage signal, and keying on the presence
# of the observed positive literal is what makes the drop fail OPEN on every shape that was never
# observed. The ⚡ row's clean literal "No major issues detected" is deliberately NOT a required
# entry — see "Consumer stage" for why it is recorded but not conjoined.
contentless_review_markers:
  - "## PR Reviewer Guide"        # CONFIRMED on #103 and #1078 — the heading that identifies the
                                  # review. It sits OUTSIDE the table, so it is markdown in the
                                  # raw body too and needs no rendering-independent form.
  - "No security concerns identified"   # CONFIRMED on #1078 — the 🔒 row's clean assertion, as
                                  # the inner text of <strong>No security concerns identified</strong>
  - "PR contains tests"           # CONFIRMED on #1078 — the 🧪 row's clean assertion, as the
                                  # inner text of <strong>PR contains tests</strong>
# actionable_content_markers: ANY entry present disqualifies the contentless drop, whatever the
# list above says.
actionable_content_markers:
  - "<details>"                   # CONFIRMED on #103 — the structural carrier of every ⚡
                                  # focus-area finding; one occurrence means the Guide carries
                                  # real content and is filed unchanged. Absent from #1078's clean
                                  # body, which is what makes that body droppable.
refusal_patterns:                 # EMPTY — no refusal of any kind observed on #103 or #1078.
                                  # Fail-closed FOR THIS ARM: no refusal is claimed on the strength of
                                  # a pattern this bot never declared.
                                  # The empty list carries NO conclusion about whether this bot refuses,
                                  # and it does NOT resolve this bot's non-participation to a non-refusal
                                  # outcome. It silences the registry arm and nothing else; the arms that
                                  # do not read this record are unaffected by what this record declares.
                                  # The governing rule for a record in exactly this position is stated
                                  # ONCE, for every bot, in bot-participation-contract.md § "Refusal
                                  # recognition is ENUMERATIVE, and a rewording nobody enumerated is its
                                  # own state". Read it there — including why an empty list is the case
                                  # that rule is sharpest about. It is deliberately NOT restated here:
                                  # a cross-bot rule copied into a per-bot data record is invisible to
                                  # the next bot registered.
rate_limit_class: unknown         # UNVERIFIED — no refusal of any kind observed on #103 or #1078.
                                  # Fail-closed per ADR-009: never assume a refusal is awaitable
                                  # without evidence.
rate_limit_eta_patterns:
# severity_map: an ASSIGNMENT map, NOT a parse map — see the section below.
severity_map:
  security_concern: high          # assigned to a finding taken from the 🔒 row
  focus_area: medium              # assigned to a finding taken from the ⚡ row
  missing_tests: low              # assigned to a finding taken from the 🧪 row
```

### `severity_map` is an assignment map, not a parse map — CORRECTED

The observed review emits **no severity vocabulary at all**: no badge, no level word, no
priority image. Unlike CodeRabbit — whose map keys are strings the bot actually writes and a
consumer parses — this map's keys name **which table row a finding came from**, and the consumer
*assigns* the mapped severity on that basis.

Do not attempt to match these keys against comment text. There is nothing in the body to match.

## Source of truth

- Signal vs. noise + review anatomy: **cuioss-organization** →
  [`docs/automatic-review/pr-agent.md`](https://github.com/cuioss/cuioss-organization/blob/main/docs/automatic-review/pr-agent.md)
- Active config + the setup's recorded learnings:
  [`cuioss/pr-agent-settings`](https://github.com/cuioss/pr-agent-settings) (`.pr_agent.toml`,
  `README.adoc`)
- The workflow that enforces the skip rules:
  [`reusable-pr-agent-review.yml`](https://github.com/cuioss/cuioss-organization/blob/main/.github/workflows/reusable-pr-agent-review.yml)

## Central config

- **File-based and central** — `cuioss/pr-agent-settings/.pr_agent.toml`, merged *beneath* any
  repo-local `.pr_agent.toml`, re-read on every CI invocation.
- **`honors_skip_label: true` is true for a different reason than CodeRabbit's.** PR-Agent's own
  `ignore_pr_labels` / `ignore_pr_authors` settings are read only by `should_process_pr_logic()`,
  which exists in its webhook servers and **not** in `github_action_runner.py` — in GitHub Action
  mode they are dead config. The label skip (and the `dependabot[bot]` /
  `cuioss-release-bot[bot]` author skips) is enforced by the reusable workflow's job-level `if:`
  guard. Do not "fix" this by moving the rules into `.pr_agent.toml`; that silently reviews
  everything.
- **An explicit `/review` comment overrides the skip label** — a human asking on purpose wins.
  This matters here: `/review` is also this bot's `trigger_comment`, so the D2 re-review path
  works on a skip-labelled PR by design.

## Why its own identity

Run with the default `GITHUB_TOKEN` the reviewer would post as `github-actions[bot]`, which is
also the author of every other workflow comment in the repo. Since the producer resolves
`bot_kind` from the author login (`github_re_review.bot_kind_for_author`), that would file
unrelated workflow comments as `pr-comment` findings. The reviewer therefore runs under the
dedicated `cuioss-review-bot` GitHub App. Keep `author_login` in step with that App — this
registry block is the only place the pipeline learns it.

**The `bot_kind` IS that App's login, and the coincidence is deliberate.** Every other registered
bot carries two different strings — `coderabbit` / `coderabbitai`, `sourcery` / `sourcery-ai` — so
`login_to_bot_kind()` is a genuine translation for them. For this reviewer the two are one name, and
the map entry is the identity pair `'cuioss-review-bot': 'cuioss-review-bot'`. That is not a
copy-paste slip to be "fixed": the identity is what makes the configured token in `required_bots`,
the `standards/{bot_kind}.md` filename, and the login a reader sees on the pull request all read as
the same reviewer. A rename of either half must move BOTH, or the coincidence — and the readability
it buys — is lost.

## Pipeline wiring

Wired entirely from the data block above via `automatic-review/scripts/bot_registry.py` — no
PR-Agent-specific code anywhere:

- `_findings_core.BOT_KINDS` derives from `bot_registry.bot_kinds()`, so `cuioss-review-bot` is a
  member because this doc declares `bot_kind: cuioss-review-bot`.
- `github_re_review.py` derives its login→bot_kind map — for this reviewer the identity pair
  `cuioss-review-bot` → `cuioss-review-bot`, since its login and its kind are the same name — and
  its generic re-review strategy (posting `/review`) from the registry.
- `github_pr.py` applies this doc's `ignore_patterns` as the per-bot producer filter, and its
  `contentless_review_markers` / `actionable_content_markers` pair as the content-aware layer
  beneath it.

## Producer stage — what to DROP before it becomes a finding

The `ignore_patterns` above drop the two comment kinds that are not reviews at all: the `/help`
commands reference and `/ask` answers.

**The `## PR Reviewer Guide 🔍` comment is dropped conditionally, on content — never by
`ignore_patterns`.** A bare-heading `ignore_patterns` entry would be wrong: that layer is a
whole-body substring test whose match drops the entire comment, and this bot has no separate
marker comment — the header identifies the review *and* carries every finding, so matching on it
would drop real findings along with the boilerplate.

The conditional rule the producer applies instead: the Guide is dropped **only** when every
`contentless_review_markers` entry is present in the body AND no `actionable_content_markers`
entry is. In every other case it is left untouched and filed as a `pr-comment` finding exactly as
before — a `<details>` focus-area finding, a 🔒 row naming a concrete concern, a 🧪 row that is
not the clean assertion, or a missing heading all leave the comment in place. The predicate can
therefore only ever fail *open*.

**Match the assertions on their BARE INNER TEXT, never on a rendering.** The 🔒 and 🧪 assertions
sit inside an HTML `<table>`, and GitHub renders no markdown inside HTML — so the raw API body the
producer matches against carries `<strong>PR contains tests</strong>`, while the *rendered* comment
a human reads looks like `**PR contains tests**`. A marker written in the rendered form matches
nothing, and because the predicate is a conjunction, a single such marker silently disables the
whole layer: the drop never fires, every clean Guide is filed as a pending finding, and the failure
is invisible because failing OPEN is also the predicate's designed safe direction. The registry
entries therefore carry the inner text alone, which is a substring of both renderings.

**Accepted residual:** on a docs-only PR the Guide carries the 🔒 clean assertion but not the 🧪
one, so the conjunction does not hold and the comment is retained and hand-triaged even though its
content is of little value there. That residue is accepted deliberately, in preference to a looser
predicate that could drop a real coverage signal.

Dropping the Guide here does not make the bot look absent: `participated_bots` is computed from
the raw comment list *before* the pre-filter runs, so a suppressed clean Guide resolves PR-Agent to
`participated_but_empty` **on the fetch that first observes it**. On every later fetch the unchanged
Guide fails the `participation_requires_update` currency test, so the bot is reported in
`stale_participation_bots[]` and resolves to `participated_stale` — a blocking state whose remedy is
the `/review` re-review trigger, **not** `absent`. Either way the drop removes the bot's findings
without removing its participation evidence. See
[`bot-participation-contract.md`](bot-participation-contract.md).

## Rate-limit class — `unknown` (UNVERIFIED)

**No refusal of any kind has been observed for this bot.** #103 produced a normal review, so nothing
in the grounding source exercises a rate-limit, quota, or diff-size decline. `rate_limit_class` is
therefore `unknown` and `rate_limit_eta_patterns` is empty — both recorded as an honest absence of
evidence, not as a claim that this bot never refuses.

`unknown` is the FAIL-CLOSED value (ADR-009): a caller must NOT claim this bot's rate window, await
it, or generate a recovery event for a bot whose refusal shape has never been seen — awaiting a quota
that does not reopen burns the full budget and still times out, and re-triggering a bot that cannot
answer spends a capped recovery attempt for nothing. The recovery sequence therefore escalates
immediately for a refusal of this class **whose cause is a quota** — `escalate_ask{reason:
rate_window_not_awaitable}`; see `../SKILL.md` § "Rate-limit refusal recovery (opt-in)".

⛔ **The class is not the only discriminator, and it is not the one read first.** A refusal whose
observed CAUSE is `size` is routed by **Branch 0** instead, whatever this field declares: it resolves
`refused_structural` and escalates with **`reason: refusal_structural`**, carrying the cap the notice
stated and the measured diff size. Both paths escalate rather than await — so `unknown` buys no wait
on either — but they escalate with **different reasons and different remedies**: a quota refusal's
remedies are wait-or-accept, a size refusal's are split / accept the gap / disable this reviewer for
this PR, and ⛔ never wait. A consumer reading `rate_limit_class` alone offers the wrong set.

Should a refusal ever be observed, record its OBSERVED text in
`refusal_patterns` — **never** in `ignore_patterns`, which is the noise-drop list and would suppress the
refusal instead of branching on it — and reclassify this field against that evidence; do not promote it
to `awaitable_window` on the assumption that it behaves like CodeRabbit's window.

**And when that observed refusal names a ceiling on the DIFF, file it on BOTH lists.**
`refusal_size_patterns` is a subset overlay on `refusal_patterns`, not an alternative to it: an entry
present only in the overlay is dropped by the subset guard and marks the cause of nothing, while an
entry present only in `refusal_patterns` is detected but classified `quota` — which routes the bot
back into the wait-or-accept branch for a ceiling waiting does not move. Add the notice's
cap-extraction regex to `refusal_size_cap_patterns` in the same edit, so the stated ceiling travels
with the refusal instead of being reported `unknown`.

The `ignore_patterns` entry `**[Persistent review]` is NOT a refusal: it is a contentless
"updated to latest commit" notice, which is a different class of non-finding.

## Consumer stage — classify a surviving PR-Agent finding

**`/review` output is one persistent comment; inline comments come only from `/improve`.**
CONFIRMED on #103 — `/review` produces exactly one persistent `issue_comment`, headed
`## PR Reviewer Guide 🔍`, and it is *updated in place* on re-review rather than reposted. Inline
review comments are published by the separate `/improve` command, which is gated on the
`pr-agent-improve` label in the reusable workflow. A pipeline stage that counts only inline review
comments therefore concludes this bot found nothing on any repository where that label is absent —
the Guide, not the inline count, is the shape that is always present.

**Observed body structure** (#103 and #1078): an HTML `<table>` of `<tr><td>` rows. Each cell is an
emoji, a `&nbsp;`, and a `<strong>` assertion; the two are separated by nothing else. Each
focus-area finding is a `<details>` element whose `<summary>` carries a deep-link `<a>`, then a
`<strong>Title</strong>`, then prose — followed by a fenced code excerpt (`java` on #103).

The rows are **assertion statements**, not `label: value` pairs — there is no bare `No` to read as
an empty field. They are emphasized with `<strong>`, NOT with markdown `**` (markdown is not
rendered inside the HTML table), so every match below is on the inner text:

| Row | Assertion inner text | Raw body form |
|---|---|---|
| 🔒 clean | `No security concerns identified` | `🔒&nbsp;<strong>No security concerns identified</strong>` — CONFIRMED on #1078 |
| 🧪 clean | `PR contains tests` | `🧪&nbsp;<strong>PR contains tests</strong>` — CONFIRMED on #1078 |
| ⚡ clean | `No major issues detected` | `⚡&nbsp;<strong>No major issues detected</strong>` — CONFIRMED on #1078 |
| ⚡ with findings | `Recommended focus areas for review` | CONFIRMED on #103 from its rendering; its raw markup was not captured |

The ⚡ clean literal is recorded here but deliberately absent from `contentless_review_markers`:
adding it would make the drop require a clean ⚡ row, and the docs-only shape (which the "Accepted
residual" note above already retains) would be joined by every Guide whose ⚡ row is phrased
differently — a needless narrowing of a predicate the 🔒 and 🧪 rows already anchor.

Extract accordingly:

1. **🔒 row** — the charter field, and an assertion either way. `No security concerns identified`
   is the bot asserting a clean result, not an empty field: it is accounted-for, not a finding. A
   row naming a concrete input or state IS a finding — assign `high` via `severity_concern` in the
   map above.
2. **⚡ row** — the findings themselves, one `<details>` each: a deep-link, a bold title, prose, and
   usually a fenced excerpt. Capped centrally at `num_max_findings`; read its value from the G2
   column of "The two generations" rather than from a number restated here — and note that column
   is itself a cache, to be re-read at `pr-agent-settings` HEAD before it is relied on. Assign
   `medium` absent other signal. `No major issues detected` in this row is a clean assertion, not
   a finding.
3. **🧪 row** — a coverage assertion. `PR contains tests` is clean; the negative form on a
   behavioural change is a cheap, actionable coverage signal (assign `low`).

Match on the row's **emoji plus its assertion inner text**, never on a `label: value` split and
never on a markdown rendering — the observed body has no such split, and its emphasis is HTML.

Fields suppressed centrally and therefore not expected: intro text, tool-usage help, estimated
effort, score, ticket compliance, can-be-split, and the security/effort review labels.

Because the comment is persistent, a re-review **replaces** the body rather than appending. Diff
against the previously triaged body instead of re-triaging identical text.

## Structural constraints and how the pipeline handles them

Two properties of this bot's `/review` output follow from the observed fact that it posts **one
persistent comment of kind `issue_comment`, and submits no GitHub *review* object**
(#103: absent from `ci pr reviews`). Both are handled — neither is an open defect.

1. **The Guide has no resolvable review thread.** Its comment's `kind` is `issue_comment` — one of
   the two genuinely threadless kinds — so GitHub gives it no review thread to reply into or
   resolve. A triaged disposition on the Guide is therefore transmitted by `github_pr
   post_responses` as a **batched PR-level comment** anchored on the source `comment_id`, and
   reported with `transmit_mode: batched_issue_comment` and `resolved_on_provider: false` — `false`
   because no thread exists to resolve, and claiming otherwise would be a false signal.

   **`post_responses` needs no change for the `inline` shape.** The batch admission is justified by
   the *kind*, not by an empty `thread_id`: `post_responses` routes on thread-bearing-ness
   generically. An inline `/improve` comment IS thread-bearing, so it reaches the existing
   thread-reply path on exactly the same rule that sends the Guide down the batched route — and a
   thread-bearing comment that merely lost its `thread_id` is still reported as untransmitted rather
   than batched here.
2. **No review object to await.** Because the bot submits no review, `github_re_review
   await_fresh_review` cannot match one. It matches the bot's **issue-comment** completion signal
   instead, returning `matched_signal: issue_comment` with `head_sha_verified: false` — the comment
   carries no reviewed-commit SHA, so completion is established by authorship plus post-dating the
   trigger. That is weaker evidence than a review match, and the envelope says so rather than
   implying the new HEAD was reviewed.

## Participation evidence — `issue_comment` and `inline`, plus update movement

Getting this bot's evidence wrong is consequential in both directions:

- **`issue_comment` is the unconditional evidence; `inline` is the conditional one.** PR-Agent
  publishes exactly one persistent `## PR Reviewer Guide 🔍` comment on every `/review`, and
  publishes inline code suggestions when `/improve` is enabled for the repository. It posts **no
  check-run** on either path, so **a check-run state is never evidence for this bot** — it produces
  none, and reading one would score it absent on every single run no matter how well it reviewed.
  That is the false-negative direction, and it is why the registry declares the shapes the bot
  actually publishes rather than the ones a generic consumer might look for.

  **An absent inline count is not evidence of non-participation.** The shape is published only
  where the `pr-agent-improve` label gates `/improve` on, so its absence is the normal state on
  most repositories. A PRESENT inline count, however, IS evidence of participation.

  **The new member is a reachable mechanism, not a name.** `workflow-integration-github
  fetch_findings` files an inline PR-Agent comment to the ledger exactly as it does for the other
  two bots; the comment's `kind` is the field that records the outcome, and `post_responses`
  already routes on it (see "Structural constraints" below).
- **Presence alone is not enough — the update must move.** A re-review **edits that same comment in
  place** rather than posting a new one. Its continued existence therefore proves only that PR-Agent
  reviewed *once*, at some earlier HEAD; after a force-push the stale Guide would silently credit
  the bot with reviewing code it never saw. That is the false-positive direction, and
  `participation_requires_update: true` closes it: the credit must clear the currency test, which
  anchors it to the merge candidate through the plan-scoped **currency ledger** — the sole source that
  test reads. The credit holds when the SHA the ledger recorded for this comment IS the merge
  candidate, when the ledger holds no row for it and this fetch observes it at a resolvable merge
  candidate the comment does not demonstrably predate, or when its `updated_at` differs from the value
  recorded at the last credit. An unresolvable merge-candidate SHA withholds it on every arm.

**`participation_requires_update: true` makes PR-Agent today the ONLY bot that can reach
`participated_stale`.** Every registry record declares the field; PR-Agent is the only one that
declares it `true`, so it is the only bot with a currency test that can fail. For a bot declaring
`false` a declared publish shape is either proven participation or nothing at all. That is a
property of the current registry, not of the taxonomy — a second bot adopting
in-place editing inherits the state with no code or contract change, which is exactly why the member
is defined against `participation_requires_update` rather than against this bot's name. And a failed
currency test is emphatically **not** `absent`: PR-Agent published, so the remedy is the `/review`
re-review trigger rather than escalating a reviewer that never engaged.

The evidence proves PR-Agent *participated*, never that its review was good. This bot is the
motivating case for that ceiling: on #1027 it posted its Guide — valid participation under this
record — while reporting "no major issues" on a diff in which CodeRabbit found two Major defects. A
satisfied quorum is not a reviewed diff. See
[`bot-participation-contract.md`](bot-participation-contract.md) § "Evidence taxonomy".

Both handlers above are **generic across the registry**, not PR-Agent special cases: every bot's
`review_body` findings are equally thread-less, and every bot's issue comment is equally valid
evidence that it responded. See
[`workflow-integration-github` SKILL.md](../../workflow-integration-github/SKILL.md) for the
authoritative envelope-field contract; it is not restated here.

## Signal calibration

Every yield figure here is stated together with the **configuration generation** it was measured
under. That pairing is not bookkeeping: this reviewer's output has moved for a reason that is
neither the diff nor the model, so a figure read against the wrong generation describes a reviewer
that no longer exists. The generation boundary is fixed by reading
[`cuioss/pr-agent-settings`](https://github.com/cuioss/pr-agent-settings) at its default-branch
HEAD — the file PR-Agent actually loads — never from a value cached here.

⚠ **The G2 column below IS such a cache, and is recorded as one rather than presented as a mirror.**
`.pr_agent.toml` is re-read at default-branch HEAD on every CI invocation, so nothing pins the
revision these values were transcribed at, and this record cannot refresh itself. What anchors them
is not a commit but the merged pull requests named below — `#5`, `#7`, `#13`, `#14`, `#15` — which do
not move; the column is exactly "the state after `#15`", and any settings change landing after it
ages the column silently, with nothing here to notice. Re-read the file at HEAD before relying on a
G2 cell for anything load-bearing, and treat a disagreement as the column being stale rather than as
the reviewer having drifted.

### The two generations

| | G1 — the suppressed charter | G2 — live at `pr-agent-settings` HEAD |
|---|---|---|
| `extra_instructions` | "do not duplicate [the other reviewers]", "only when you can name the concrete input", "prefer one well-evidenced finding"; six classical AppSec categories | says what to look *for*; contests the empty-list permission directly; severity explicitly not a reporting threshold; anti-fabrication clause retained |
| `num_max_findings` | 3, then 5 | 12 |
| `temperature` | 0.2 — PR-Agent's Gemini-2.5-era default, transmitted on every review | 1.0 |
| `model` | `gemini-3.5-flash` / `gemini-2.5-pro` / `gemini-3.6-flash` | `vertex_ai/gemini-3.7-flash`, with a four-rung fallback ladder |
| `publish_output_no_suggestions` | false — a clean review and a total failure were indistinguishable | true |
| `max_model_tokens` | 32000 (upstream default) | 256000 |
| `max_description_tokens` | 500 (upstream default) | 2000 |
| Charter composition | one generic central charter | central spine plus a generated per-repository domain pack |

G1 is **not live**. The transition is recorded in that repository's own merged history — `#5` (the
charter rewrite), `#7` (temperature), `#13` (the empty-list permission and `num_max_findings` → 12),
`#14` (the checked model-parameter facts) and `#15` (the model leader) — corroborated against those
pull requests rather than against any local note. Every G1 figure below is therefore a historical
record, not a description of the reviewer this pipeline meets today.

### What was measured, and under which generation

All three measurements are **G1**:

- **#103 (`cuioss/API-Sheriff`)** — one focus-area finding, which the maintainer determined to be a
  **false positive** (a plausible-sounding mechanism on a branch that cannot be reached). CodeRabbit
  produced twelve valid findings on the same diff, with zero overlap.
- **The silence run** — across five pull requests and diffs from 5k to 57k tokens, every published
  review was **byte-identical at 242 bytes**: the bare table, zero findings. Its controlled case was
  `/review` on `plan-marshall#1027` (`gemini-3.6-flash`, the full 40748-token diff, no pruning,
  final commit), where CodeRabbit had already reported a TOCTOU race around `shutil.move` and an
  empty-string filename resolving to a directory — both squarely inside the charter, and this
  reviewer reported neither.
- **The 58-pull-request sweep** — findings on 4 of 13 Python and markdown pull requests, and **0 of
  19 Java** ones. A single generic charter is shaped like whichever language its author had in mind,
  which is what G2's per-domain packs answer.

⚠ **One G1 figure is not fully attributable, and is recorded that way rather than rounded off.** The
source states the silence run covered "four models" while naming three ids (`3.5-flash`, `2.5-pro`,
`3.6-flash`). The fourth is unnamed at the source, so the model count is reported here as *three
named of a stated four*, never as four. #1078 raised no finding at all, so it grounds the body SHAPE
recorded above and contributes nothing to any yield figure.

### The reproduction, re-derived against the live generation

**The empty yield does not reproduce as a model effect, and that non-reproduction SUPERSEDES the
model arm rather than being one of its cells.** The silence run varied the model across its cells and
the published review stayed byte-identical at 242 bytes. A result that does not move when the model
changes is not a model result — so the model arm was retired by this finding rather than by
preference.

⚠ **That is one knob, not three.** `model` is the only knob any yield cell varied, so the result
above is evidence about `model` alone. The other two are retired on separate grounds and not on this
one: `reasoning_effort` is unreachable rather than measured-null, and `temperature` is **unmeasured
for yield**. The knob table below states each; nothing here upgrades either into a measured negative.

The cause is located, and its load-bearing clause cannot be configured away. "No major issues
detected" is not a severity filter; it is the text rendered when `key_issues_to_review` returns
empty, and the suppression lives in that field's own description inside the pinned image
(`pr_reviewer_prompts.toml:150`) — a ceiling read as a target, a scope narrower than the charter's, a
confidence gate, and explicit permission to return nothing. Configuration reaches part of that
description and not the rest: `.pr_agent.toml` sets `num_max_findings`, which is interpolated into
it, and `extra_instructions`, which is appended as its own earlier block — so a charter argues
*alongside* the schema rather than replacing it, and no key removes the empty-list permission.

⛔ **A green run is not a reproduction result.** An empty review is exactly what G1 produced, so "the
reviewer ran and reported nothing" distinguishes nothing. The known-answer cases are
`plan-marshall#1027` (the two findings above must appear) and `plan-marshall#1042`, whose oracle is
*shaped* rather than counted: a review returning only the two Major defects has NOT discharged the
severity clause — it has reproduced the exact behaviour that clause was written against, while
looking like a success.

### Knob cells, nulls included

One knob per run. A knob that was not varied is named here as not varied, never left absent.

| Knob | Varied? | Cells | Outcome |
|---|---|---|---|
| `model` (yield) | yes | `gemini-3.5-flash`, `gemini-2.5-pro`, `gemini-3.6-flash` — three named of a stated four | **NULL** — output byte-identical at 242 bytes on every cell |
| `model` (availability) | yes | `gemini-3.5-pro`, `gemini-3.1-pro`, `gemini-2.5-pro` | `404`, `404`, `429`-then-served. An entitlement result; it says nothing about yield |
| `model` (leader promotion) | yes | `gemini-3.7-flash` | Entitlement-checked `HTTP 200`, promoted on published benchmarks — **not** on any yield measurement |
| `temperature` | changed, never A/B-ed for yield | 0.2 → 1.0 | **UNMEASURED for yield.** The change was made on Gemini 3 guidance plus an endpoint probe (`200` at both 1.0 and 0.2; `400` at 3.0 and −1.0), with the charter moving in the same period, so no cell isolates its yield effect |
| `reasoning_effort` | **not varied, and cannot be** | none | **Dead config for Gemini.** `litellm_ai_handler.py` transmits it only for models in `SUPPORT_REASONING_EFFORT_MODELS` (`o3-mini`, `o3-mini-2025-01-31`, `o3`, `o3-2025-04-16`, `o4-mini`, `o4-mini-2025-04-16`) — no Gemini entry. It appears in every run's resolved-config dump, which is what makes it look live |

⛔ The `temperature` row is a **not-measured** null, not a measured-nil one. Reading it as evidence
that temperature does not matter would be reading an absent experiment as a negative result.

⚠ **The `reasoning_effort` row's verdict is anchored to an image revision, and the anchor is named
here rather than left implicit.** `SUPPORT_REASONING_EFFORT_MODELS` is transcribed from
`litellm_ai_handler.py` **inside the reviewer image** — it is not a setting this project's
configuration declares, so unlike every other row above it cannot be re-derived from
`pr-agent-settings`. The image is selected by
`cuioss/cuioss-organization/.github/workflows/reusable-pr-agent-review.yml`, which this repository's
caller pins by commit SHA in `.github/workflows/pr-agent.yml` (`uses: …@f3b0586c…`, v0.23.0). That
pin fixes the *workflow file*, and with it the image REFERENCE that file names; it fixes the image
CONTENT only insofar as that reference is a digest rather than a tag — and **this record has not
verified which form it uses**. The org workflow is not vendored in this checkout, so the form cannot
be established from here at all. **"Dead config for Gemini" is therefore a statement about the image
the list was read from, not a standing property of Gemini**, and two independent moves can make the
row silently false: bumping the `uses:` pin, or — under a tag reference — the org workflow's own
image reference resolving to a different build with the pin unchanged. Nothing in this record or in
CI would report either. Re-read the list whenever that pin moves AND whenever the org workflow's own
image reference changes, before the "unreachable" rejection below is relied on again.

### The chosen arm, and the arms rejected

**Chosen — the charter arm.** Rewrite `extra_instructions` to state what to look for rather than
what to withhold, contest the empty-list permission head-on, add an explicit "severity is not a
reporting threshold" clause, hold the anti-fabrication bar unchanged, and raise `num_max_findings`
to 12 — that value is interpolated into the field description above, so it is read as the expected
shape of an answer rather than as a ceiling. It is the single chosen arm, because the suppressor it
addresses is the one the reproduction actually located.

Rejected, each with the reason:

- **Promote to a Pro model.** Wrong twice over: the 3.x Pro tier is not entitled to this project at
  all (`404` on two rungs), and the published head-to-head puts `3.6-flash` ahead of `3.1 Pro` on
  every coding and agentic benchmark reported. It also treats a prompt problem as a capacity one.
- **Tune thinking depth via `reasoning_effort`.** Unreachable — see the table above. It would take
  an upstream change, not a configuration one.
- **`custom_reasoning_model = true`**, the only temperature suppression reachable from the file.
  Rejected for collateral: it also disables system messages for the model, so it is not a
  temperature-only lever.
- **Add more charter categories.** Capped. Category growth was already tried, the ceiling is roughly
  ten entries and is now enforced by a generator regression test rather than by discipline; past it
  the remedy is a second focused pass, not an eleventh bullet.
- **`pr_reviewer.inline_code_comments`.** It does not exist; setting it would parse, appear in the
  resolved-config dump, and do nothing.
- **`[skills]` prompt inlining.** Rejected on trust-boundary grounds: it is a filesystem scan, so it
  needs a checkout of the pull request head, which would let reviewed content rewrite the reviewer's
  own instructions — the hole `repo_context_from_default_branch` exists to close.
- **A roster change.** Not taken, and this record alters no roster. The evidence is filed for
  PLAN-PR-025B D7 instead: on `plan-marshall#1041` all three reviewers commented on a 48-file pull
  request and two of those comments were refusals, so a comment count read three while the number of
  reviewers that read the diff was one — this one. This reviewer carries no per-account review quota
  and does not decline on diff size, so it is frequently the member still available. That is an
  argument about ensemble availability, not a quality ranking.

### The in-tree counting boundary every figure is dated against

A yield figure is comparable only to one computed under the same **counting** rule, and that rule
moved in this repository independently of the configuration above.

`review_gate_delta.py`'s `_is_actionable` treats a `review_body` finding as actionable unless
`is_status_summary` matches the bot's registry `review_body_summary_patterns` against the comment
BODY; `test_counting_rule_parity.py` pins that predicate across both implementations of the rule.
Before the carve-out existed, a reviewer's `"Actionable comments posted: N"` status summary counted
as one actionable finding.

⛔ **The carve-out is INAPPLICABLE to this bot, not merely non-firing — and saying "it does not fire"
understates the gap.** This record declares no `review_body_summary_patterns`, but that is not what
excludes it: the bot publishes **no `review_body` at all**. `participation_evidence` declares
`issue_comment` and `inline`, and the bot submits no GitHub review object (see "Structural
constraints"), so "every one of its `review_body` comments stays counted" is a claim over an empty
population — true, and about nothing.

⛔ **What the counting rule actually does to this bot is stronger: its `/review` Guide contributes
ZERO.** `_is_actionable` counts `inline` and substantive `review_body`; `issue_comment` is meta. The
Guide is an `issue_comment`, so under the in-tree rule it counts as **nothing at all**, however many
⚡ focus-area rows it carries. Only its `inline` `/improve` comments are countable — the shape that
had never once appeared in this repository before the #1334 pilot. So the in-tree counter's view of
this reviewer is not "counted without a summary carve-out"; it is "not counted on the `/review`
surface at any time".

⚠ **Therefore #103 is a RAW count and is labelled that way.** Its PR-Agent side — one focus-area
finding — was read by hand out of the Guide body; `assess_delta` would score that side **0**, because
the Guide is an `issue_comment`. Its CodeRabbit side is a raw count too, and CodeRabbit *does* declare
`review_body_summary_patterns`, so the two sides are not even drawn from the same countable
population. Read #103 as a manual observation of review CONTENT, never as an `assess_delta` figure,
and never as a ratio: a PR-Agent-versus-CodeRabbit ratio is incomparable in both directions at once —
the carve-out moves the comparator's side by up to one finding per pull request it summarised, while
the whole of this bot's `/review` output is outside the counted population on ours. Any ratio carried
over from that era does not survive; the raw counts do, as raw counts.

The reviewer's **identity** moved too: `bot_kind` is `cuioss-review-bot`, so a corpus keyed on the
retired `pr-agent` token predates that rename. Establish which token a figure was filed under before
comparing it with anything here.

### What survives as a triage rule

Do not read a quality ranking into any figure above, and do not weaken the shared triage rules on
their basis. The G1 figures measure a charter that could not report; they are evidence about a
configuration, not about this reviewer's ceiling. **No G2 yield figure exists yet** — the charter arm
landed with no measured post-change yield, so the honest statement of this reviewer's current signal
quality is that it has not been measured, not that it is good.

⛔ A finding count carries no information about recall, in either direction. On `plan-marshall#1038`
another reviewer posted three findings to this one's none — then withdrew all three itself, so the
silence was the correct answer. On `plan-marshall#1040` the direction reverses: this reviewer posted
first and its finding was the live defect, while the other arrived after the fix and raised one that
was refuted. Compare what was substantiated, never how much was said.

## Trust boundary

PR-Agent emits no "Prompt for AI Agents" block, so there is no machine-payload injection surface
of the CodeRabbit/Sourcery kind. Two PR-Agent-specific reasons to keep the shared
untrusted-external-content rule strictly anyway:

- Its `repo_context_files` feed `CLAUDE.md` / `AGENTS.md` into the model, so its output can echo
  instruction-shaped text back into the review body.
- Its own prompt includes the PR diff, which is attacker-controlled on any contributed change.

Ingest through the untrusted-ingestion boundary; never execute review text verbatim.

## Disposition & nuances (align with `pr-comment-disposition.md`)

- FIX / REPLY-AND-RESOLVE / ESCALATE per the domain `pr-comment-disposition.md`, after the
  `persona-plan-marshall-agent` plan-intent validity check.
- **Security findings get priority** — this bot exists to add a dedicated security lens to the
  three-bot set. A security finding it raises alone (not echoed by CodeRabbit or Sourcery) is the
  highest-value output of the set — subject to "Signal calibration" above, where every yield figure
  is dated to a superseded configuration generation and no post-change figure exists yet.
- **Dedupe across reviewers**, not just within this one: three bots routinely raise the same point.
- **Correct ≠ in-scope** — a security observation about pre-existing code is worth recording, not
  necessarily fixing in the PR that surfaced it.
- **No automatic re-review on push.** A fresh review requires the `/review` trigger comment, which
  is what the D2 re-review path posts. Do not wait for a spontaneous re-review that will never
  arrive.
- **The re-review path re-triggers `/review` ONLY.** `trigger_comment` is `/review` and stays that
  way: a loop-back re-review refreshes the Guide and does NOT re-run `/improve`. That is deliberate
  rather than an oversight — `/improve` is label-gated per pull request, so re-running it on every
  loop-back would spend a second tool invocation (and its token cost) on a repository that never
  opted in. A run that wants fresh inline suggestions asks for them by label, not by loop-back.
