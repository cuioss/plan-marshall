# PLAN-92: One Coherent Automated-Review Contract

epic: truthful-signals
workstream: WS-01

> **THE single plan for automated review.** Absorbs and replaces PLAN-71, PLAN-72, PLAN-91 (all
> parked) and PLAN-80's unshipped residue. Written 2026-07-28 as a clean consolidation — earlier
> refuted paths are omitted, not archived; the two that still matter are named as open questions in
> § Unsettled, because a reader who does not know they are open would guess wrong.

## Objective

Automated review has one job: **know whether the code was actually reviewed, and act truthfully when
it was not.** Today it cannot. Bots go silent without blocking, refusals are recognized only to be
discarded, rate limits are never recovered from, dispositions land in the wrong place, and bot-specific
knowledge is scattered across bundles. Make the review contract single-sourced, fail-closed, and
recoverable.

## Verified current state (2026-07-26 → 07-28, all first-party)

**Live config** — `.plan/marshal.json` + `automatic-review/SKILL.md:20-47`:

| Knob | Live | Default |
|---|---|---|
| `enabled_bots` | `coderabbit,sourcery,pr-agent` | `coderabbit,sourcery` |
| `re_review_on_loopback` | `false` | `false` |
| `re_review_on_branch_cleanup` | `true` | `true` |
| `re_review_on_timeout` | `ask` | `ask` |
| `review_rate_window_await` | `false` | `false` |
| buffer / completion-poll / re-review-await / rate-window | defaults | 180 / 600 / 600 / 3600 s |

**CodeRabbit never recovers from its own rate limit — 3 of 3.** Every PR that hit the limit merged
with zero CodeRabbit review; only Sourcery reviewed those:

| PR | Limit notice | Stated ETA | CodeRabbit review |
|---|---|---|---|
| 1014 | yes | 46 min | ⛔ none |
| 1015 | yes | 37 min | ⛔ none |
| 1016 | yes | **3 seconds** | ⛔ none |
| 1013 · 1021 · 1022 · 1023 · 1026 · 1027 | none | — | ✅ reviewed |

The notice (quoted, #1016): marker
`<!-- This is an auto-generated comment: rate limited by coderabbit.ai -->`, heading
`## Review limit reached`, field **`Next review available in: N {seconds|minutes}`**, and the vendor's
own recovery instruction: *"a review can be triggered using the `@coderabbitai review` command as a PR
comment. Alternatively, push new commits to this PR."* **So it does not resume by itself; recovery
requires an action.** The ETA is machine-parseable and currently discarded.

**Five verified defects:**

1. **The refusal is detected only to be deleted.** `"Review limit reached"` sits in `coderabbit.md:30`
   `ignore_patterns`, which `:66` defines as *whole-comment drops*. A rate-limited bot therefore yields
   no findings, no review, and a dropped notice — finalize proceeds as if it had nothing to say.
   **The drop must become a branch.**
2. **The rate-limit discriminator is single-bot.** `_github_pr.py:42` hardcodes
   `_CODERABBIT_BOT_LOGINS`; `:45` `_detect_coderabbit_rate_limited` is called at `:630` and produces
   the `rate_limited` flag. **A rate-limited Sourcery or PR-Agent yields `rate_limited: false`**, so any
   window strategy built on that flag never arms for them. (`:78-79` also documents
   `## Rate limit exceeded`, a phrasing that does not exist.) ⚠ PLAN-80 reported collapsing this island;
   the generic recognizer at `:74-95` did land and is bot-agnostic, but this discriminator survived.
3. **A silent bot does not block.** There is no required/optional distinction — `enabled_bots` is one
   flat list, so a bot that never posts is indistinguishable from one with nothing to say.
4. **Bulk dispositions answer inline comments by reference.** `post_responses` correctly thread-replies
   whenever a finding carries a `thread_id`, and correctly batches thread-less `review_body` findings.
   But on #1023 one batched section disposed of **nine inline comments** in prose attached to their
   parent review — 2 were separately filed and got threads, **7 nitpicks got nothing.** On #1027,
   **42/42 inline comments carry a `PRRT_` thread id and 16 threads are unresolved.** Nitpick is
   policy-SIGNAL (`coderabbit.md:36`, `:83`), so "accepted, not actioned" is a permitted verdict — **it
   still owes a reply in its own thread.** The defect is the channel, not the verdict.
5. **Bot-specific knowledge lives outside `automatic-review`** — 24 files name a bot, including
   operative logic (`_github_pr.py`, `github_re_review.py`, `github_pr.py`) and behaviour-asserting
   prose (`workflow-integration-github/SKILL.md:161`, `tools-integration-ci/standards/pr-review-operations.md`,
   `manage-findings/standards/jsonl-format.md`, `phase-6-finalize/workflow/create-pr.md`,
   `branch-cleanup.md`, `verification-feedback.md`).

## Operator decisions (settled — implement, do not re-litigate)

1. **`required_bots` / `optional_bots` replace `enabled_bots`.** A required bot that does not work
   **stops and asks the operator** (`ask` is the default posture). An optional bot's absence is logged,
   never blocking. **A bot in neither list produces a WARN LOG.**
   ✅ **The shipped default for both lists is EMPTY** — most projects do not have these bots — and the
   lists are **asked at `marshall-steward`**. D3(a) owns the migration of this repo's own three-bot
   value and the never-asked-vs-answered-none distinction the empty default creates.
2. **The registry-wired trigger comment is legitimate** — but only **after** availability returns.
   Never before the ETA has elapsed. Agent-composed variants (e.g. an improvised
   `@coderabbitai full review`, observed on #1027 and absent from every shipped and cached bundle) are
   out of contract: one declared trigger string per bot.
3. **`review_timeout` strategy, in this order:** sleep the parsed ETA → **rebase onto main and push**
   (new commits are the vendor's own recovery path) → **only if main has no changes**, post the registry
   trigger comment. **Push is primary, comment is fallback.**
4. **All bot-specific knowledge belongs in `automatic-review/standards/{bot_kind}.md`** and nowhere else.
5. **Every comment carrying a `thread_id` is owed a reply in that thread**, whatever its disposition.
6. **Classification (settles U2): `required_bots = coderabbit, pr-agent` · `optional_bots = sourcery`.**
   This repo's config is **fully updated to that mapping as part of this plan**, not left to a follow-up.
   ✅ **Required-PR-Agent is safe, and the evidence it needs already exists.** PR-Agent posts a
   `## PR Reviewer Guide 🔍` comment on every review — observed on #1027 carrying
   *"🧪 PR contains tests / 🔒 No security concerns identified / ⚡ No major issues detected"*. That
   comment **is** the participation artifact, and `pr-agent.md:125-127` records that it is
   **deliberately NOT dropped** by `ignore_patterns` precisely because it identifies the review and
   carries every finding.
   ⚠ **What makes it easy to miss is documented at `pr-agent.md:131-134`, and D6 must handle both
   halves:** PR-Agent produces **no inline comments** — exactly one persistent `issue_comment` —
   **and it is UPDATED IN PLACE on re-review rather than reposted.** So *"a pipeline stage that counts
   inline review comments will conclude this bot found nothing"*, and a stage that watches for a **new**
   comment misses the in-place update. This is lesson `2026-07-28-08-003` (comment-count polling misses
   in-place edits) with a named artifact.
   ⇒ **D6 detects PR-Agent by the presence of its Guide comment, and by `updated_at` movement — never
   by check state, never by inline-comment count, never by new-comment arrival.** D6 remains a hard
   precondition of decision 6; the two land together.
7. **An unclassified bot's findings are USED.** All information present is ingested and triaged;
   the operator is **warned about the config**, not deprived of the review. (Settles the D3(a)
   sub-question.)

## ⚠ Unsettled — two questions that must be answered before building on them

⭐ **CONFIRMED 2026-07-28 — the recreate-the-PR leg of D4 WORKS.** PLAN-75's branch produced a natural
experiment across three PRs, verified first-party: **#1025** no review, **#1031** CodeRabbit posted
`Review limit reached` (refused), **#1032** (the recreate) got `Actionable comments posted` — a real
review — and merged. **Closing and re-creating the PR earns a fresh review.** D4's primary path is
de-risked. ⚠ **This does NOT settle U1**, which asks about a force-push to the *same* PR — a different
mechanism. What is confirmed is the new-PR leg.

⛔ **MEASURED — a merged PR with ZERO substantive review, which is defect 1 with a consequence.** On
PLAN-75's #1025 all three bots failed simultaneously: CodeRabbit rate-limited, Sourcery refused the
diff over its 150000-char ceiling, PR-Agent silent. `automatic-review` recorded `0 comment(s) found` /
`outcome: done`, while `finalize-step-review-retrospective` independently recorded *"Review surface
absent: rate-limit, diff-size, silent (3 modes)"*. **The refusal detectors worked correctly — and that
is exactly how the finalize signal became indistinguishable from a clean review.** Zero findings from
three refusals renders identically to zero findings from three clean reviews. Defects 1 and 3 would
each have caught it.

**U1 — ✅ SETTLED 2026-07-28 on #1024. A force-push DOES trigger a review, and the mechanism is now
known.** Observed: *"the pre-merge force-push was a new-commits event, which triggered a real review"*
— CodeRabbit then produced a nitpick and PR-Agent a genuine clean verdict, after both had refused.
**`SKILL.md:161`'s "debounced or skipped on a force-push" caveat is not what governs**; D4's
rebase-and-push primary path is confirmed.

⭐ **THE GOVERNING RULE, and it rewrites the algorithm: CODERABBIT REVIEWS ON EVENTS, NOT TIMERS.**
Three consequences, all first-party from #1024:

1. ⛔ **Sleeping alone accomplishes NOTHING.** Waiting out the window does not cause a review — no event,
   no review. **The sleep is only useful as a precondition for an event**, never as an action in itself.
   D4 must not implement "sleep and re-poll" as a recovery.
2. ⛔ **A premature trigger comment is ACTIVELY HARMFUL, not a no-op.** Manual `@coderabbitai review`
   retries *"each consumed an attempt and reset the window — 58 min → 2 min → 59 min."* So triggering
   while rate-limited **burns an attempt AND pushes the window back out.** This supersedes the earlier
   reading that a premature trigger merely does nothing, and it converts decision 2's "never trigger
   before the ETA" from a discipline into a **hard cost-avoidance rule.**
3. ⇒ **The correct algorithm is: wait out the window, then GENERATE AN EVENT.** A rebase-and-push is the
   event. ⚠ **This also demotes the comment fallback**: when main has no changes there is no event to
   generate, and posting a comment is the only lever — but it must fire **only after the window has
   elapsed**, never during, or it resets the window per (2). D4 must state that ordering explicitly.

⚠ **NEW, and it undercuts a claim this plan currently makes.** On #1024 *"both bots initially refused
(rate limits) while `automatic-review` reported `0 comment(s) found`"* — and **#1021's
refusal-recognition caught NEITHER phrasing.** This plan's § Verified current state credits #1021's
generic recognizer with matching the live notice. **That credit is now contested by a second
observation.** D1 must re-verify which refusal phrasings are actually matched at HEAD, against the real
comment bodies from #1024 and #1032, before building D2 on the assumption that the recognizer works.

⛔ **NEW DEFECT 6 — the pre-merge barrier can loop forever on our own reply.** On #1024,
`github_pr fetch_findings` **stored a comment authored by `cuioss-oliver` despite
`--enabled-bots coderabbit,sourcery,pr-agent`.** Under `pre_merge_comment_barrier: fail_into_loopback`
that is an **infinite loop**: triage posts a reply → the barrier re-fetches the reply as an unhandled
comment → loops back → replies again. The run was only broken out of by manually suppressing the
finding. ⇒ **The author filter is not filtering**, and the failure mode is unbounded rather than merely
noisy. ⚠ **This interacts with decision 7** (an unclassified bot's findings are ingested): ingestion
must not extend to **our own** triage replies. D1 must separate *"a bot we have not classified"* from
*"not a bot at all"* — the first is ingested with a warn, the second must never enter the pipeline.

**U2 — SETTLED 2026-07-28, see decision 6. No longer open.**

## Deliverables

### D1 — GATE: settle U1 and U2; fix the discriminator's blast radius first (mutates nothing)

(a) Settle **U1** and **U2** as above; record both answers as decisions.
(b) Confirm defect 2's scope: enumerate every consumer of the `rate_limited` flag, so the
generalization does not silently change a second behaviour.
(c) Decide the **enforcement** mechanism for decision 4. Prose will not hold — the island survived a
plan written to remove it. A plugin-doctor rule forbidding bot-name literals outside `automatic-review`
is the candidate; **coordinate with PLAN-85's doctor-check remedy rather than shipping two rules.**
(d) Triage the 24-file inventory into: **operative logic** (move behind registry data), **contract
prose** (authority moves to the registry, leave an xref), and **incidental provenance — LEAVE ALONE**
(e.g. `plugin-doctor/_runner.py:206`'s "CodeRabbit PR #811 review fix"; a note naming who found a bug
is not a behaviour contract, and sweeping it inflates the diff and hides the real moves).
⚠ The seven `ext-triage-*/standards/pr-comment-disposition.md` files are a judgement call: per-domain
disposition may be legitimately bot-aware, or each registry's `severity_map` may make those mentions
redundant. **The answer moves the blast radius from 3 files to 10 — do not assume it.**

### D2 — generalize the rate-limit discriminator across all bots

Replace the CodeRabbit-login-keyed detector with registry-driven detection for every registered bot.
Prefer the **HTML marker** (`rate limited by coderabbit.ai`) over prose — handle-free, number-free,
language-independent — with the prose string as fallback. Per-bot, declare **awaitable window vs hard
quota**: a window resets on a published ETA (CodeRabbit, 3 s … 46 min observed) and can be slept on; a
quota (Sourcery's weekly/diff limit) can never be waited out and escalates immediately. Fix the stale
`:78-79` comment.

### D3 — `required_bots` / `optional_bots`: the two-class model, its behaviour, and its standard

**This is the structural centre of the plan** — D6's quorum denominator and D4's escalation target both
resolve through it. Three parts, all required:

**(a) The declaration — SETTLED BY THE OPERATOR 2026-07-28, implement exactly this.**

Replace `enabled_bots` with `required_bots` and `optional_bots`.

- ✅ **A bot in NEITHER list → WARN LOG.** Not an error, not a block. (This overrides the
  orchestrator's earlier fail-closed suggestion of "unknown ⇒ required"; the operator chose warn.)
- ✅ **THE SHIPPED DEFAULT FOR BOTH LISTS IS EMPTY.** Not `coderabbit,sourcery` — **empty.**
  **Rationale (operator): although the bots are sensible, most projects do not have them.** A
  consumer project therefore gets a review pipeline that expects nothing until it says otherwise.
- ✅ **The lists are ASKED AT `marshall-steward`** — the config wizard prompts for them, so a populated
  config is an explicit answer rather than an inherited default.
- ✅ **This repo migrates explicitly, to the settled mapping (decision 6):**
  `required_bots = coderabbit, pr-agent` and `optional_bots = sourcery`, replacing the live
  `enabled_bots: "coderabbit,sourcery,pr-agent"`. **Full update is part of this plan, not a follow-up.**
  ⚠ **An empty default plus an unmigrated marshal.json would silently switch this repo's own review
  gating off** — the exact quiet-degradation this plan exists to prevent. Assert it in a test.

⚠ **NEW REQUIREMENT the empty default creates — distinguish NEVER-ASKED from ANSWERED-NONE.** With
empty as the default, "no bots configured" is ambiguous between *the wizard never ran* and *the operator
deliberately said none*. Those deserve different behaviour: the first should prompt, the second must be
silent forever. **Record the answered state explicitly** (an answered-marker, or the keys present-but-empty
versus absent) so the pipeline neither nags a project that opted out nor stays quiet about one that was
never configured. ⚠ **Without this, "empty" becomes an unfalsifiable state** — indistinguishable from
misconfiguration, which is defect 3's shape one level up.

✅ **SETTLED (decision 7) — an unclassified bot's findings are USED.** All information present is
ingested and triaged exactly as a classified bot's would be; the warn log tells the operator to fix the
**config**, and never costs them the review. ⚠ **The warning is about the CONFIGURATION, not about the
findings' validity** — do not let it degrade into a confidence marker on the findings themselves, and
do not gate ingestion behind acknowledging it. A dropped real finding is strictly the worse failure, and
this epic already carries that instance (defect 1).

**(b) The behaviour, per class.**

| | `required_bots` | `optional_bots` |
|---|---|---|
| Bot posts a review | proceed | proceed |
| Bot absent / silent | **STOP and ASK the operator** (`ask` default) | log, proceed |
| Bot posts a recognized refusal (rate limit, size skip, quota) | enter D4 recovery; escalate via `ask` when D4 is exhausted or the limit is a hard quota | log, proceed |
| Bot still in progress at the poll bound | **not a failure** — distinct state (see (c)) | log, proceed |

⚠ **"Does not work" needs a definition, not a vibe.** Enumerate the failure taxonomy explicitly —
**absent** (no review, no check-run), **in-progress-at-bound**, **refused-awaitable** (window with an
ETA), **refused-hard** (quota; unrecoverable), **participated-but-empty** (posted a review with zero
findings). ⚠ **The last one is NOT a failure** and must not be conflated with absence; conversely
**absent must never be read as "nothing to say"** — that conflation is defect 3.

**(c) ⚠ Distinguish structurally-absent from in-progress.** Lesson `2026-07-21-10-002` records the
completeness guard looping back on a bot with **no check-run at all** instead of telling the two apart.
A bot that publishes no `completion_check_name` is *unobservable*, not *pending* — and a required
unobservable bot must resolve through `ask`, not through an indefinite wait.

**(d) Model the behaviour in `automatic-review/standards/`.** Per the operator directive, the
required/optional semantics, the `ask` posture, and the failure taxonomy above are **authored as a
behaviour standard in `marketplace/bundles/plan-marshall/skills/automatic-review/standards/`** — a
document owning the *contract*, sitting alongside (not inside) the per-bot registry docs
`standards/{bot_kind}.md`, which continue to own per-bot *data*. ⚠ **Keep the two separated:** contract
in the behaviour standard, data in the registry. A per-bot doc that starts restating the contract is how
the divergence in defect 5 began. ⚠ **The `ask` posture must be enforced by machinery, not by prose** —
a documented "stop and ask" that an executor can proceed past is the documentation-layer vacuous guard
this epic tracks at n=6; state the enforcement seam.

⚠ **U2 settles only WHICH bot goes in which list — never whether the mechanism exists.** Build (a)–(d)
regardless of how U2 resolves.

### D4 — the `review_timeout` recovery strategy

⭐ **Reframed by #1024: the recovery is EVENT GENERATION, not waiting.** Sleeping out the window is a
*precondition*, not the action. The sequence is **wait for the window → generate a new-commits event
(rebase + push) → verify a review landed**. A trigger comment is the fallback only when there is no
event to generate (main unchanged), and it must fire **only after the window has elapsed** — posting one
during the window consumes an attempt and **resets the window**.

Per decision 3, with cross-plan coordination and jitter — up to `parallelization_scope` plans may wake
on the same window, and N plans waking together re-collide. ⚠ Prefer an existing primitive
(`manage-locks` already owns cross-plan coordination) over a new one, and note that a shared wait store
must be **main-anchored** to be visible across worktrees. Cap the recursion — a limit that recurs on the
new PR would loop forever; `review_rate_window_timeout_seconds` (3600) is a candidate ceiling. On
rebase conflict, escalate per `ask`; do not auto-resolve.

### D5 — every thread-bearing comment gets its disposition in its own thread

Per decision 5. The batched PR comment renders **only** dispositions for findings with no thread of
their own; a bulk rationale covering thread-bearing comments is **repeated into each thread**, never
summarised into a parent. Reuse the existing `untransmitted[]` / `count_untransmitted` /
`status: partial` channel for anything undeliverable — an undeliverable in-thread reply must be
**visibly** untransmitted, never silently re-routed to the batch. ⚠ D1 must first establish why the 7
nitpicks produced no reply: **(A)** the pre-filter dropped them (whole-comment drops → no finding to
reply with), or **(B)** triage collapsed N findings onto one disposition. **These need different fixes;
settle it by counting stored `pr-comment` findings against #1023/#1027's inline comments.**

### D6 — participation becomes evidence-based

A bot counts as having reviewed only on **positive evidence of a posted review**. ⚠ Neither a green
check nor a stored `pr-comment` finding is sufficient — lesson `2026-07-27-07-001` records both as
false signals, and observed check states have lied in both directions (#1016: Sourcery SKIPPED but
reviewed). Fold the quorum question here: with `required_bots` as the denominator, "quorum met" is
*every required bot posted a review or was explicitly excused by a recognized refusal*. ⚠ **Do not ship
both a numeric threshold and the `ask` posture as competing gates** — `ask` decides what happens when
the quorum is unmet.

**Per-bot evidence, because the three bots publish in three different shapes** — a single detector will
be wrong for at least one of them:

| Bot | Participation evidence | Trap |
|---|---|---|
| **coderabbit** | a posted review body (`Actionable comments posted: N`) and/or inline comments | a `## Review limit reached` notice is a **refusal**, not participation (defect 1) |
| **pr-agent** | the `## PR Reviewer Guide 🔍` `issue_comment` | **no inline comments at all**, and the guide is **updated in place** — counting inline comments or waiting for a *new* comment both conclude "found nothing" (`pr-agent.md:131-134`) |
| **sourcery** | a posted review body | its refusals are hard quotas (diff-size, weekly) — excused, not participating |

⚠ **A post-merge finding appeared on #1027 — but it was OPERATOR-TRIGGERED, so do NOT generalize it.**
The Guide comment (created 07-27T19:47:36Z) was updated in place at 07-28T09:08:56Z carrying a real
**Sequence Number Reuse** defect (verified first-party, staged as **PLAN-93**). ⛔ **The orchestrator
first recorded this as evidence that "a review artifact can change after the merge" and inferred that
D6 needs a post-merge sweep. The operator corrected it: they explicitly started that review to test
Gemini.** The mutation was *induced*, not spontaneous vendor behaviour.
- **What survives:** in-place update is real and documented (`pr-agent.md:131-134`), so a detector must
  watch `updated_at` rather than wait for a new comment. **A merged PR's review state is not immutable
  if something re-triggers a review** — a weak, true claim.
- **What does NOT survive:** any requirement for a routine post-merge re-read. There is **no observed
  case of a bot spontaneously amending a review after merge.** Do not build a sweep for it.
- ⚠ **Attribution is UNRESOLVED and matters for the per-bot evidence table below.** The comment carries
  PR-Agent's Guide format, while the operator triggered the review to test **Gemini** — which #1014
  retired from the registry. **D1 must establish which bot authored that finding before citing it as
  PR-Agent's**, and must ask whether Gemini is being re-introduced (that changes `required_bots` /
  `optional_bots` membership under decision 6).
- ⚠ **Recorded as an orchestrator over-generalization**, n+1 for the correct-verdict-wrong-evidence
  archetype: the *defect* was real and first-party verified, the *inference drawn around it* was not.

⛔ **MEASURED CEILING ON WHAT THE QUORUM CAN PROMISE (#1027).** PR-Agent posted its Guide —
participation — and reported *"no major issues"* on a diff containing **two Major defects CodeRabbit
found**. Under decision 6 it is **required**, and under this deliverable the Guide is valid
participation evidence: **both are satisfied while its review contributed nothing.** ⚠ This does not
refute the classification — a required bot's job is to be present and answerable, and
`participated-but-empty` is a legitimate verdict. **But D6 MUST NOT let a satisfied quorum read as a
reviewed diff.** Say so explicitly in the standard: *quorum proves participation, never quality.*
Building a gate that implies otherwise would rebuild the flagship archetype inside the fix for it.
⭐ Same PR confirms the D2 split with a live instance: Sourcery's zero came from a **hard weekly quota**
exhausted throughout — no sleep could have recovered it, unlike CodeRabbit's window.

⚠ **A zero-findings review IS participation.** *"⚡ No major issues detected"* is a completed review
with nothing to report — the `participated-but-empty` state from D3(b) — and must never be scored as
absence. **Conflating the two is defect 3 in the opposite direction**, and it is the likelier error once
a strict quorum exists.
⚠ **Correction on record:** an earlier orchestrator note characterised PR-Agent as *"SUCCESS but
published nothing."* Its **check state** is indeed uninformative, but the **bot does publish** — the
Guide comment. The claim that its participation is undetectable is **withdrawn**; only the
check-state half stands.

### D7 — tests

(a) A rate-limited **non-CodeRabbit** bot sets `rate_limited: true` — **verified to FAIL pre-fix.**
(b) The ETA parser handles seconds and minutes. (c) A missing **required** bot halts with `ask`; a
missing **optional** bot proceeds with a log. (d) A thread-bearing comment dispositioned
`accepted`/`taken_into_account` produces a thread-reply **and** a resolve, not a batched section —
**verified to FAIL pre-fix** for the bulk case. (e) A `review_body` finding still batches.
(f) An undeliverable in-thread reply lands in `untransmitted[]` with `status: partial`. (g) A green
check with no posted review does **not** count as participation. (h) Per D1(c), a bot-name literal
introduced outside `automatic-review` is flagged. (i) **Both lists default to EMPTY on a fresh project,
and a project with empty lists runs the pipeline without blocking and without prompting once the answer
is recorded.** (j) **A bot in neither list produces a warn log AND its findings are ingested and triaged normally**
(decision 7) — assert both halves, since the ingestion half is the one a "tidy" refactor would drop.
(k) ⚠ **This repo migrates to `required = coderabbit, pr-agent` / `optional = sourcery`** — assert
against the migrated config, since an empty default silently switching this repo's gating off is the
plan's own worst failure mode. (l) **A required PR-Agent that posts no review is caught by
evidence-based participation even when its check is SUCCESS** — the case decision 6 depends on.

**Seven deliverables — over the split guard, and deliberately so:** D2 is a precondition for D4 (the
strategy cannot arm on a single-bot flag), D3 is a precondition for D6 (the quorum denominator), and
D5's fix shape depends on D1's A/B finding. Splitting them would create four plans that each block the
next. ⚠ If D1 finds U1 unsettleable AND the D5 A/B question has two answers, **split D4+D5 out at that
point** and record the decision.

## Claim Labels

Every table and line reference above is **OBSERVED**, read first-party on 2026-07-28 from
`.plan/marshal.json`, `automatic-review/SKILL.md`, `coderabbit.md`, `_github_pr.py`, `github_pr.py`,
and `ci pr comments` / `ci pr reviews` for PRs 1013–1027. The two **HYPOTHESIS** items are U1 and U2,
each with its confirm/refute route stated. **Derived counts** (3-of-3 non-recovery, 42/42 threads, 16
unresolved, 24 files, nine bulk-dispositioned comments) are orchestrator-derived — re-derive at outline.
Verify-first: if D1 finds the `rate_limited` flag already generalized, or every inline comment already
thread-replied, that defect is refuted — re-scope rather than implementing against this spec.

## Expected Surface

- `automatic-review/` — `SKILL.md` config block, `standards/{coderabbit,sourcery,pr-agent}.md`,
  `scripts/bot_registry.py`
- `workflow-integration-github/` — `scripts/_github_pr.py` (`:42`, `:45`, `:74-95`, `:630`),
  `scripts/github_pr.py` (`cmd_post_responses` `:709`, `_build_batched_response_body` `:688`,
  `_THREAD_ID_DETAIL` `:296`, pre-filter path `:391`), `scripts/github_re_review.py`, `SKILL.md`
  (`:139-161`), `scripts/comment-patterns.json`
- `manage-config` — the config model for required/optional, and the **empty shipped default** (⚠ the
  default currently lives at `automatic-review/SKILL.md:22` as `"coderabbit,sourcery"`; check whether a
  `DEFAULT_*` block in `manage-config/scripts/_config_defaults.py` also carries it, so the two do not
  disagree — PLAN-74 records exactly that class of divergence)
- `marshall-steward` — the wizard prompt for `required_bots` / `optional_bots` (`references/wizard-flow.md`
  and its script surface), plus the answered-vs-never-asked marker from D3(a)
- `manage-locks` — cross-plan wait coordination (D4), if D1 picks it
- HYPOTHESIS: `plan-marshall/workflow/triage.md` (only if D1 finds D5-B); `plugin-doctor` (only if D1(c)
  picks the doctor rule); the contract-prose files in defect 5 per D1(d)'s triage
- Tests: `test/plan-marshall/workflow-integration-github/**`,
  `test/plan-marshall/automatic-review/**`

**Disjointness:** `automatic-review` + `workflow-integration-github` + `manage-config` (+ possibly
`manage-locks`, `plugin-doctor`). Disjoint from PLAN-86 (`phase-5-execute`), PLAN-88
(`manage-build-server`), PLAN-89 (`manage-architecture`), PLAN-90 (`manage-lessons` + a phase skill).
⚠ **Overlaps PLAN-85 if D1(c) picks the doctor rule** — coordinate, do not pair.

## Dependencies and Sequencing

- **Absorbs and replaces:** PLAN-71, PLAN-72, PLAN-91 (parked) and PLAN-80's unshipped residue.
- Depends on: none. PLAN-80 (#1021) landed and is a re-grounding input — its generic recognizer stays.
- ⚠ **Re-read the live config at outline.** `#1029` flipped `re_review_on_loopback` to `false`,
  reversing `#1018`; `re_review_on_branch_cleanup` remains `true` and is **ungated on availability** —
  it fires on every branch-cleanup rebase with no check that the bot can accept a review. **That
  ungatedness is the defect, not the trigger.**

## Lessons Carried

Carry at phase-1-init via `manage-lessons convert-to-plan`; retire at finalize. ⚠ Resolve each id
against the live store before staging — phantom ids have been staged from stale notes before.

- `2026-07-27-07-001` — a green CI check and a stored `pr-comment` finding are both false signals of
  participation (D6).
- `2026-07-21-10-002` — completeness guard loops back on a structurally-absent bot instead of
  distinguishing it from in-progress (D3).
- `2026-07-28-08-003` — wait-region completion signals are blind to content-level review state:
  comment-count polling misses in-place edits, and CI-completion folds in a review-bot check (D6).
- `2026-06-21-21-001` — re-review freshness matcher: naive-datetime comparison, fail-open
  None-wildcard, `--paginate` without slurp; all in-house gates passed, only the bots caught it (D2/D4).
- `2026-06-23-19-001` — PRs over ~150 files auto-skip CodeRabbit entirely, leaving local self-review as
  the only net (D3/D6 — a size skip is a *refusal* the required-bot posture must see).

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/truthful-signals/plans/PLAN-92-one-coherent-automated-review-contract.md"
```

## Write-Boundary

Repository source + tests only. NO writes to `.plan/local/orchestrator/` **ledger state**
(`status.json`, `epic.md`, `plans/`, `landings/`); the `inbox/` channel is the sanctioned exception.
See `persona-marshall-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
