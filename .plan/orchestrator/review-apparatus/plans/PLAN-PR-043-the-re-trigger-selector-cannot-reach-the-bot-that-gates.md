# PLAN-PR-043: The re-trigger selector cannot reach the bot that gates

> ⛔⛔ **SUPERSEDED 2026-09-12 by `PLAN-PR-056` — do NOT emit this spec.** Its queue row is retired
> under the operator's decision to raise the split guard to 12 deliverables and group staged work by
> shared target surface; D1, D2, D3, D4, D5, D5a, D6 and D7 are carried there as D1–D8. ⛔ **This file
> is NOT dead and is NOT deleted**: it remains the AUTHORITATIVE TEXT of every deliverable body —
> including the D5a fold, the three rate-window limbs and the 2026-09-11 inbox folds — and
> `PLAN-PR-056` points here rather than retyping it.

epic: review-apparatus
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Drained 2026-08-31 from inbox `-001` (finding) and `-009` (candidate-lesson), both observed
> live on PR #1368 during PLAN-PR-025A's finalize. Corroborated against the shipped source
> before staging.

## Objective

The participation guard's declared remedy for a `participated_stale` required bot is **a
re-review trigger**. Trigger B is the mechanism that fires one. But trigger B selects its bot
by **comment recency**, and the gating bot is by definition the one that has *not* commented
recently — so **the bot that gates is the one bot trigger B structurally cannot select.** The
loop does not converge: each finalize re-entry re-runs the identical pass and re-reports the
same `unproven_bots`.

Alongside it, the refusal-recognition stack keeps under-registering vendor refusal shapes, so a
refusal is filed as an actionable finding — or worse, credited as participation for a HEAD the
bot explicitly declined.

## Deliverables

### D1 — Select the trigger-B bot from the gating set, not from comment recency

The observable that says *"re-trigger me"* and the mechanism that re-triggers are wired to
different selectors. Candidate remedies, from the finding, all **unvalidated** — pick one and
record why the others were rejected:

1. select from the **unproven/gating** set rather than by recency (most direct);
2. allow trigger B to trigger **more than one** bot when more than one is unproven;
3. re-read the store **after** the round's own FIND so the selector sees current state.

⛔ **The selector is ALSO stale by construction** — it picks from findings filed *before* the
round's FIND. On PR #1368 it therefore could not see that CodeRabbit had already auto-reviewed
the new head, posted a redundant trigger, and **burned that bot's hourly quota** (`0 remain`).
Remedy 3 addresses this limb specifically; a fix taking only remedy 1 must state what it leaves.

*Done when:* on a PR whose required bot is `participated_stale` and whose newest bot comment is
from a different bot, trigger B selects the **required** bot; pinned by a test whose pre-fix form
fails.

### D2 — Close the refusal-recognition gap the three arms each missed differently

On PR #1368 a CodeRabbit refusal was filed as an actionable finding (`12ce1a`). Every arm
declined it for its **own** structural reason — this is the finding, and a fix that patches one
arm leaves the others:

| Arm | Why it missed |
|---|---|
| Registry | holds `Review limit reached`; the notice says `Review rate limited` |
| Structural | needs a limit-exceeded verb the notice lacks |
| Enumerative | inert (no measured threshold) **and** vetoed by the `<details>` code-anchor marker |

⚠ **The in-run remediation (TASK-016) registered ONE literal.** Finding `-001` reports **two
further unregistered bodies** under the same `<details><summary>⚠️ Action not completed</summary>`
wrapper — *"Already reviewed the last commit…"* and *"Review skipped / No new commits to
review…"*. ⛔ **Widening the literal is the WRONG fix and the finding says so** — recognise the
**wrapper shape**, or derive the set, rather than chasing vendor strings one at a time.

⛔⛔ **A FOURTH MISS, ON A DIFFERENT BOT, FAILING IN THE OPPOSITE DIRECTION — folded 2026-09-03,
corroborated first-party on `cuioss/cui-http#194`.** Sourcery's live refusal reads:

> *"Sorry @…, you've **used** your own review budget of 250,000 diff characters for the last 7 days.
> You can request another review in 4 days and 1 hour…"*

Its registry declares only two patterns (`sourcery.md`): `"your pull request is larger than the review
limit of"` and `"reached your weekly rate limit of"`. **Neither matches** — the live wording is
*used*, the recognizer keys on *reached/exceeded/hit*. The full chain, every link read at HEAD
`30cd8aaf8`:

| Arm | Outcome |
|---|---|
| registry `refusal_patterns` | ✗ no match — wording differs |
| structural rate-limit arm | ✗ keys on rate-limit phrasing |
| enumerative arm | ✗ **INERT** — `_github_pr.py:338` `UNRECOGNISED_REFUSAL_MAX_CHARS: int \| None = None` |
| `participation_evidence` | ✓ it is a `review_body`, a declared shape ⇒ **CREDITED AS PARTICIPATION** |

⛔ **A hard refusal was counted as a review.** Three arms miss and the fourth is disabled, so the
comment falls through to the credit path. ⭐ And `sourcery.md:50` declares `rate_limit_class:
hard_quota`, so a *recognised* refusal would have escalated immediately — correct, since a 4-day
weekly budget is not awaitable. The registry is right; only the recognition failed.

⭐⭐ **NOTE THE DIRECTIONS, because this spec now carries both.** D5's false `declined` fails toward
BLOCKING; this one fails toward MERGING. They live in the same subsystem simultaneously, so a fix
that tightens recognition to cure one can loosen the other. ⛔ Any change here needs a control in
BOTH directions, not one.

*Done when:* all observed bodies — CodeRabbit's three and Sourcery's budget refusal — are recognised
as refusals by a **derived** rule rather than a literal list; a body that is NOT a refusal is still
filed (matched negative control); and the enumerative arm's inertness is either resolved or recorded
as a deliberate non-fix with its reason. ⛔ Do not rely on the enumerative arm as the safety net while
its threshold is `None` — it cannot fire.

### D3 — Stop the enumerative arm being vetoed by the code-anchor marker

The `<details>` veto is what let a refusal reach participation credit. Establish whether the
veto is correct for this class, and either carve out the refusal wrapper or record why not.

*Done when:* a refusal wrapped in `<details>` is not credited as participation, pinned by a test.

### D4 — One conflation, THREE consumers: a refusal is treated as review evidence at three call sites

⛔⛔ **FOLDED IN 2026-08-31** from `truthful-signals-041` (transferred under the three-way rule;
originally `disjointness-gate-reads-declared-surface-wrong-009`). ⚠ **RELAYED, not re-derived by
this orchestrator** — the sending plan's own first-party observation. Corroborate before acting.

The sender named three sites, and the reason this is **one** fix rather than three patches is that
they share a single mechanism:

| Site | What it does with a refusal |
|---|---|
| `fffb89` | counts it as a **completion signal** |
| `942346` | stores it as a **triageable finding** |
| `071a67` | lets its `reviewed_commit_sha` **suppress the very re-review that would cure it** |

⭐ Site `071a67` is the vicious one: the refusal both fails to count as review AND blocks the retry.
It composes directly with D1 — a stale required bot that cannot be re-triggered, whose refusal then
suppresses the re-review, cannot converge by any path.

**Companion defect:** `reviewed_commit_sha` is stamped from the **landing HEAD**, not from the tree
the reviewer actually read — so a bot's verdict is bound to a commit it never saw. ⛔ This is the
same class as the epic's shipped `head_sha_verified` work; check whether that fix reaches this
stamp before scoping new code.

**Two further `automatic-review` registry gaps** (`…-011`): the rate-limit ETA pattern misses the
live phrasing, and a second gap in the same file. ⇒ Fold into D2's derived-rule requirement rather
than adding literals.

*Done when:* all three sites read a refusal as a refusal, pinned per site; `reviewed_commit_sha`
names the tree the reviewer read; and the registry gaps are closed by D2's derived rule with a
matched negative control.

### D5 — A false `declined` from an in-place re-review, whose remedy is to merge unreviewed

⛔⛔ **FOLDED IN 2026-09-02** from an operator paste reporting a `cuioss/TokenSheriff` run. ⚠ The run's
own messages went to **TokenSheriff's** epic inbox and never reached this ledger — the observation is
relayed, not drained. **The mechanism below was re-corroborated first-party at HEAD `30cd8aaf8`; the
observed incident was not.**

pr-agent declares `participation_evidence: [issue_comment, inline]` over **one persistent comment**,
and `participation_requires_update: true` because *"a re-review EDITS that same comment in place"*
(`pr-agent.md:96-100`). When it re-reviews, the edited comment carries no reviewed-commit reference
for the new HEAD, so `head_sha_verified` resolves `false` — and a `matched: true` with
`head_sha_verified: false` **is** the `declined` member (`bot-participation-contract.md:65`, `:349`).

⛔ **`declined` is the one member whose documented remedy is to stop requiring the review**: *"accept
the decline (move the bot to `optional`, or record an operator merge-authorization) rather than
trigger again"* (`:354-358`). ⇒ **The required bot's ordinary re-review behaviour resolves to the one
verdict that steers the operator into merging unreviewed.** It fails toward less safety by the route
the contract itself calls *"strictly worse"*.

⭐⭐ **THIS IS NOT THE `5ec6d3` PERMALINK DEFECT, AND THE SHIPPED FIX CANNOT COVER IT.**
`bot-participation-contract.md:368-379` names this failure and attributes it to a **narrow
recogniser** — the remedy being *"widen WHERE the SHA may sit"* (PLAN-PR-025A, #1368). That widening
cannot reach this case: **there is no SHA anywhere in the evidence to recognise.** An absent
reference and an unrecognised one are different facts with different fixes, and the contract
currently states only the second.

*Done when:* an in-place re-review that names no commit is distinguishable from one whose reference
the matcher failed to read, and the first does NOT resolve `declined`; the contract passage at
`:368-379` names both causes rather than only the recogniser; and a **matched negative control**
holds — a genuine decline still resolves `declined`, or a false negative merely replaces a false
positive.

Five deliverables — still inside the split guard, but D5 arrived by fold and pushes this spec toward
it. ⛔ Re-check the guard before emitting; do not absorb a sixth.

### D5a — `head_sha_verified` is UNREACHABLE for the required bot, and the cause is now LOCATED

⭐⭐⭐ **Folded from `truthful-signals-051.md` item 1 on 2026-09-07** (their `-005`, from PLAN-TRUTH-099 /
PR #1434). This CONVERTS D5's standing `HYPOTHESIS` about `github_re_review.py` into an **OBSERVED**
located cause, and it is the root of a defect this epic has recorded as *"still unfixed"* **three
separate times**.

`cuioss-review-bot` publishes the commit it reviewed **in the BODY** of its Reviewer Guide comment
(*"Review updated until commit `<sha>`"*). It populates **no structured reviewed-commit field**, because
its participation arrives as an `issue_comment` rather than a review object.

⛔ **`github_re_review.py` calls `_references_head_sha` EXACTLY ONCE — line 571, inside the REVIEW
branch, against `review['commit_sha']`. The `issue_comment` branch (lines 363, 617) never calls it.**

⇒ ⛔⛔ **A re-review by that bot can NEVER reach `head_sha_verified: true`, so it disposes as
`declined` on every cycle.** The correct outcome — *it did review this head* — is **UNREACHABLE**, not
merely unproven. Every `barrier-ask-override` this epic has granted on that bot rests on this.

⭐⭐ **And the symptom is DOCUMENTED rather than hidden**, which makes it sharper:
`workflow-integration-github/SKILL.md:39` records the resulting state as *"`matched_signal:
issue_comment` with `head_sha_verified: false`"*. **A described defect reads as an accepted design to
every later reader** — the documentation is what let it survive three sightings.

*Done when:* `_references_head_sha` is applied to the matched comment **body** on the `issue_comment`
path, **and the returned record keeps the field-vs-prose distinction visible** so a caller can tell a
structured verification from a body-derived one. ⛔ Collapsing the two would trade an unreachable
`true` for an unauditable one.

⭐ **SECOND-REPO SIGHTING, folded 2026-09-11 from `truthful-signals-054.md` item 1(b)** (relayed from
API-Sheriff `deployment-configurability`, their `-002`). Same arm, same symptom — an `issue_comment`
re-review reads as `declined`. Mechanism re-read first-party at HEAD `356973d80`: the hard-coded
`'head_sha_verified': matched_signal == 'review'` assignment in `github_re_review.py` is unchanged.
Three active global lessons name this same arm (`2026-09-05-11-002`, `2026-09-04-19-001`,
`2026-09-06-20-001`) — one defect, not three.

⛔⛔ **A REMEDY DIRECTION IS REFUTED — do not adopt it.** The originating lesson proposed collapsing the
fix onto "the existing resolver", on the premise that `fetch_findings` already extracts
`reviewed_commit_sha` from this comment. **It does not.** At `356973d80`, `github_pr.py`'s FIND path
stamps `reviewed_commit_sha = _github.fetch_pr_head_sha(pr_number)` — the **PR head at fetch time**,
not a SHA parsed from any comment body. ⇒ **There is no correct extractor to reuse**; the body parse
this deliverable's *Done when* names (`_references_head_sha` over the matched comment body) is new work.
The fetch-time stamp is `PLAN-PR-053`'s subject and D4's companion defect here — cite it, never reuse it.

### D6 — The rate window is a RETRY POLICY, not a flat timeout, and the wait must name its satisfying event

⭐ **Folded from two independent sources on 2026-09-04**: `review-packs-become-published-artifacts-009.md`
(this repo) and `truthful-signals-043.md` item 3 (relayed from TokenSheriff, a LEAD not corroborated here).

**Limb A — the surface cannot express the policy.** The operator's stated unattended-run policy was *"wait
at least 90 minutes and try again, up to 10 waits"*. The manifest can only carry
`review_rate_window_await: false` with `review_rate_window_timeout_seconds: 3600`. A 90-minute interval with
a 10-attempt ceiling exceeds a single 3600s budget by an order of magnitude, so the pair **cannot represent
it at all**. ⛔ Because the surface could not express it, the operator supplied it in prose — it applied to
one run, was never recorded in the manifest, and is unavailable to the next plan meeting the same window.
CodeRabbit's limit is one review per hour, so **any wait shorter than that interval cannot succeed**, and a
single 3600s budget affords at most one attempt at the boundary.

**Limb B — a wait must be able to name the event that would satisfy it.** pr-agent's workflow triggers on
`pull_request: [opened, reopened, ready_for_review]` and `issue_comment` — **not `synchronize`**, which is
what a push to an open PR emits. A push therefore produces no pr-agent run at all, so a push-then-wait
loop-back **has no possible satisfying event** and burns iterations by construction. ⭐ The observable
already exists: `workflow-integration-github` → `pull_request_runs` exposes the PR-wide `not_triggered`
state, and a bot reported `not_triggered` after a push is a **fail-fast, not a wait**.

*Done when:* the rate window is modelled as a per-attempt interval plus an attempt ceiling, with the interval
**defaulted from the bot registry's known rate limit** rather than requiring the operator to know it; and a
wait-for-condition loop names both the event that would satisfy it and the producer that emits it, failing
fast with a *no satisfying event* verdict when either is unnameable. ⭐ **Record the trigger surface per bot**
— the event set each configured bot responds to is stable, cheap to record once, and is the fact that decides
whether push-then-wait is coherent for that bot at all.

⛔ This is the NON-CONVERGENCE archetype again (fourth instance): a retry loop whose input cannot change by
retrying. Limb A cannot converge because the interval is too short; limb B because no event will ever arrive.


**Limb C — the knob is scoped on the wrong axis, so it cannot await the only substantive reviewer.**
⭐ **Folded from inbox `apply-the-cloud-plan-lane-contract-amendments-004.md` on 2026-09-05**, observed
live on PR #1416. The operator explicitly chose to wait for CodeRabbit rather than merge on
participation-only coverage, and set `review_rate_window_await: true` for the plan. **It had no effect.**
The rate-window recovery is scoped to `required_bots` by an explicit rule, and the plan's configuration is
`required_bots=cuioss-review-bot`, `optional_bots=coderabbit,sourcery` — so the knob **could not fire for
the bot the operator was waiting on**, and coderabbit's refusal settled rather than escalated.

⛔ **The scoping is inverted against what the bots actually do on this repository.** `cuioss-review-bot` —
the required one, the one the knob CAN await — publishes a canned intent-echo Guide body carrying no
diff-derived observation; the corpus records it returning canned-empty on **42 of 44** reviews, and it did
so again here, reporting *"no major issues detected"* on the same head where CodeRabbit filed two Major
findings. `coderabbit` — the optional one the knob **cannot** await — produced **all 3** actionable
findings this plan received.

The recovery knob is scoped on the required/optional axis, which encodes **merge-gate authority**, while
the thing being waited for is **substantive review output**. Those two properties are independent, and on
this repository they point at different bots.

*Done when:* the rate-window recovery is scoped to the bot the operator names rather than to a class — or
the required/optional split reflects which bots actually produce diff-derived findings. ⛔ What must NOT
remain is a wait knob whose only reachable target is a bot that never finds anything. The `escalate_ask`
path this run took is the workaround, and it costs an operator prompt every time.

⚠ **This is a fourth non-convergence limb of a different kind**: limbs A and B cannot converge because the
retry input cannot change; limb C cannot converge because the retry was **never armed for the bot in
question at all**. A run reading only `review_rate_window_await: true` would conclude the wait was armed.

### D7 — The rate window's own instruments are deaf, and one of them reads a foreign PR's counter

⭐ **Folded 2026-09-05 from three independent sources**: `truthful-signals-049.md` (relayed from
PLAN-TRUTH-093 / PR #1398), `preference-admissibility-prose-vs-auditor-code-001.md` (finding `1b5171`,
same run), and `truthful-signals-048.md` item 2 (relayed from TokenSheriff PLAN-01 / PR #713).

**Limb A — none of the three registered ETA patterns can match the phrasing CodeRabbit actually uses.**

⭐⭐ **THREE further independent reports arrived 2026-09-07, and together they change the remedy.**
`one-format-several-implementations-that-disagree-001`, `test-suite-anti-vacuity-001` item 2, and
`truthful-signals-051` item `-004` all report the same gap. The second of those localises it exactly:
`unrecognised_refusal[]` and `refusal_pattern_drift[]` were **both empty**, so a declared
`refusal_patterns` arm DID match the notice — **the failure is specifically in
`rate_limit_eta_patterns`, not in refusal detection.**

⛔ **FOUR distinct phrasings have now gone unparsed on a single PR**: `"36 minutes"`, `"2 minutes"`,
`"57 minutes"`, and `"Next included review available in 50 minutes."`

⛔⛔ **A FIFTH, AND IT IS THE SAME SENTENCE — folded 2026-09-13 from `plan-pr-046`'s inbox `-001`
item 2 (finding `fe6347`, live on #1477).** CodeRabbit stated *"Next included review available in 48
minutes"* and `refusal_eta` came back **empty on BOTH** the `pr wait-for-comments` and the
`github_re_review` returns, across **every one of seven refusals**; the duration had to be read out of
the body by hand each time. ⭐ **This is the decisive argument against adding a literal**: the
already-recorded fourth phrasing differs from this one only in its NUMBER, so a pattern set that missed
both is not missing entries — it is the wrong shape. Derive the duration from a general number+unit
match, as this limb already requires. ⚠ Same run: **a trigger RESETS the window rather than shortening
it** (stated ETA moved outward 20 → 48 → 52 minutes across three triggers), which is the
already-recorded rule re-confirmed first-party — and it is why the ETA must be parsed rather than
guessed: `expired: true` on our own claim says the CLAIM ran out, never that the bot is ready.

⇒ **Pattern enumeration is the wrong shape.** Derive the duration from a general number+unit match
rather than adding a fifth literal. An unparsed ETA means the awaitable-window branch cannot size its
own wait and the operator gets no bound.

⛔⛔ **DO NOT inherit the free-OSS-vs-Team explanation.** One reporting run attributed this to a plan
tier, then checked its own persisted envelopes and **retracted**: *"all three, on both PRs, record
`Plan: Team` with the same `0 remain` footer."* The remedy worked and the mechanism was unfounded, and
the run said so. A plan-tier cause for this gap is **refuted**, not open.

⭐⭐ **A TRIGGER RE-ARMS THE WINDOW — this is the expensive one.** `truthful-signals-051` item `-003`
reports **six `@coderabbitai` triggers over ~12 hours and five 90-minute waits that produced NO
review**, because every trigger re-armed the window; **closing and recreating the PR obtained a full
review in under 15 minutes.**

⇒ **This SHARPENS, and does not contradict, the refutation this epic recorded on 2026-09-06.** Close +
reopen does not RESET the window (two ETAs across a close and a fresh open resolve to the same absolute
instant). What this adds is that **triggering actively EXTENDS it** — so the harm was never the absence
of a close, it was the repeated trigger. ⛔ **Read the limit notice BEFORE triggering.** The two
findings are compatible and both are load-bearing; neither may be dropped in favour of the other.

⚠ Two further items from the same cluster ride here: **post the registry-declared trigger token, never
one chosen per bot** (`-001`), and **an acknowledgement is not a review — require a review object**
(`-002`).

⭐⭐⭐ **THE MECHANISM, folded 2026-09-08 from `one-format-…-003` — this is WHY the gap stayed silent
across five reports, and it generalises past this bot.** A paired detect-then-extract design has TWO
lists, and only one of them is guarded:

| List | Decides | Drift detector |
|---|---|---|
| `refusal_patterns` | **whether** a notice is a refusal | ✅ `refusal_pattern_drift[]` + `unrecognised_refusal[]`, the latter **state-determining**, not advisory |
| `rate_limit_eta_patterns` | **what value** to pull out of a recognised notice | ⛔ **nothing** |

⇒ A notice that IS recognised as a refusal but whose ETA cannot be extracted produces **no signal
anywhere**: detection succeeded, so no drift is reported, and extraction failed silently to `""`.
⛔ **Guard the EXTRACTION list, not only the DETECTION list.** *Done when:* an unextractable value from
a successfully-detected notice raises its own drift signal, and that signal is state-determining in the
same way `unrecognised_refusal` is.

⛔⛔ **THE MEASURED COST, folded from `truthful-signals-052` and `one-format-…-002`: ~5 HOURS of wall
clock against a 21-MINUTE window.** Rounds 5, 6 and 7 were each ~1h45m apart under a 90-minute
standing wait floor, and **all three refused**. Round 7's notice stated its own reset —
*"Next included review available in 21 minutes"* — and a retry timed to that **succeeded immediately**.
`refusal_eta` read `""` throughout.

⇒ ⭐ **A PUBLISHED ETA BEATS A CONFIGURED WAIT FLOOR.** The floor is a guess made without the number
the bot is already publishing. *Done when:* a parsed ETA overrides the configured floor, and a run that
waits longer than a published reset records why.

⛔⛔ **THE WINDOW'S PRICE, MEASURED ON A LANDING RUN — folded 2026-09-13 from `PLAN-PR-033`'s inbox
`-005` (candidate-lesson), corroborated by that run's own landing facts.** #1473 spent **three
90-minute CodeRabbit quota waits inside finalize**, and its recorded shape is 120h41m wall against
6h20m worked. ⇒ **The window did not merely delay that run — it PRICED IN-RUN REMEDIATION OUT OF
REACH**: two review-pipeline defects observed live on that PR (`852b0f`, `658eec`) were resolved
`accepted` as carry-forward *because* fixing either would advance HEAD and restart the mandatory
re-review cycle. ⭐ **That is this limb's cost argument in its sharpest form**: the wait policy is not
only a throughput cost, it is a **selection effect on which defects get fixed at all** — the apparatus
that reviews us decides, by its quota, which of its own defects we are able to repair. ⚠ Carry it as
evidence for the retry-policy shape, NOT as licence to skip a re-review.

⭐ **SECOND-REPO RECURRENCE, folded 2026-09-11 from `truthful-signals-054.md` item 4** (relayed,
Token-Sheriff `lessons-handling-…-050`). Four short Fair-Usage windows in one run, each notice naming its
own ETA (57 s, 6 min, 5 min, 3 min); the blanket ≥90-minute floor turned ~15 minutes of stated waiting
into up to six hours. The sender's proposed discrimination — **Fair-Usage backoff** (wait the stated ETA
plus margin) vs **real quota exhaustion** (the long wait is right only there) — is this limb's rule with
a name on each arm, not a new rule. ⚠ **Keep the counter-evidence beside it**: `PLAN-PR-025B` D10 recorded
a stated ETA off by ~2.4× and then ~15×, so "wait the ETA" must stay a FLOOR the run re-checks against
the notice, never a contract — and the "never trigger inside a closed window" rule above still binds on
every arm. ⛔ The ≥90-minute floor is an **operator standing order** for unattended runs; what an ETA may
override is the operator's call, and this deliverable makes the override *expressible*, it does not grant
it. Adds no file surface.

⛔⛔ **AND THE TRIGGER RESETS THE WINDOW — measured, from `test-suite-anti-vacuity-002` across
PRs #1430 / #1442 / #1443.** Every trigger fired while the window was still closed **restarted** it
rather than being ignored:

| Trigger | Time | New window advertised |
|---|---|---|
| force-push | 13:43:40Z | 50 minutes |
| close-and-reopen | 14:45:25Z | 52 minutes |
| force-push | 16:05:03Z | 40 minutes |

⭐ The 16:05:03Z refusal was an **in-place EDIT of an existing comment, re-stamped at the exact second
of the push** — which is `PLAN-PR-052` D3/D3a's mutable-refusal surface producing the evidence for this
one. **The recovery succeeded only on the sequence: wait for FULL expiry → then trigger.**

⇒ This is the operational rule the three prior reports were circling: ⛔ **never trigger inside a closed
window.** It is compatible with the 2026-09-06 refutation (close+reopen does not RESET a window) —
close+reopen is simply one of the trigger forms that EXTENDS it.

⚠ **A tension left OPEN rather than resolved**: the notices here say *"You've used all free OSS reviews
for now"*, while `truthful-signals-051` recorded a sender retracting a plan-tier explanation after
finding `Plan: Team` in its own persisted envelopes. **Both readings are first-party and they concern
different runs.** ⛔ Do not collapse them — D0 should establish which tier each observed notice came
from before any tier-dependent behaviour is written.

⛔⛔ **CROSS-PLAN CONTENTION IS A REFUSAL CAUSE, AND IT IS INVISIBLE ON THE RECORD — folded 2026-09-15
from `truthful-signals-058`** (relayed from `plan-truth-148`, PR #1488). A CodeRabbit re-review at head
`c5ed864ce` was refused by the re-trigger guard with `reason=window_open`,
**`holder=architecture-store-query-truthfulness`**, `seconds_remaining=2444` — **another plan held the
rate window.**

⭐ **The guard behaved correctly** and did NOT re-issue, since re-issuing inside an open window only
resets it (this limb's own rule, working). ⛔ **The defect is the visibility**: the refusal cause,
the holder, and the remaining seconds exist ONLY in the work log, so the step record shows a reviewer
that produced nothing with no reason attached — and a reader cannot tell a bot that refused from a bot
nobody asked. *Done when (added):* a refusal caused by cross-plan window contention surfaces its
`reason`, `holder` and `seconds_remaining` on the STEP RECORD, not only in the log. ⚠ This is the
multi-plan face of the window cost `PLAN-PR-056` D8 already carries: with several epics running, one
plan's review budget is spent by another plan's, and nothing in either plan's record says so.

⛔ ORIGINAL LIMB-A TEXT FOLLOWS.

`automatic-review/standards/coderabbit.md:64-67` declares three `rate_limit_eta_patterns`. **Measured
cost in one run: roughly THREE HOURS waiting on a rate window that had already reopened.** ⛔ The doc
compounds it by blaming the bot for a phrasing the registry simply does not match. *Done when:* the
pattern set is derived from observed refusal bodies rather than asserted, publishes the population it
was derived from, and a body matching **no** pattern is reported as `eta_unparsed` — never as
"no ETA offered".

**Limb B — `merge_lock rate-window check` accepts `--pr-number` and then ignores it.**
`merge_lock.py`'s `_run_rate_window_check` (~line 1491) echoes `record['attempts']` unconditionally,
while the **claim** path (~line 607) scopes it correctly:

```python
attempts_before = record['attempts'] if record is not None and record['pr_number'] == pr_number else 0
```

⇒ `check` publishes an `attempts` / `attempts_remaining` pair that is only meaningful for whichever
`pr_number` the record happens to hold, **and the caller reads it as its own.** Observed live twice in
one run. *Done when:* `check` scopes to its `--pr-number` exactly as `claim` does, or refuses the flag
outright — ⛔ a declared parameter that is silently ignored is the vacuous-filter archetype.

**Limb C — a required bot with no re-trigger path cannot be waited out at any duration.** A required
bot that neither auto-reviews on push nor runs under `re_review_on_loopback: true` has **no re-trigger
path at all**, so a wait-and-retry loop reproduces the identical outcome forever, each iteration
spending a full await budget because **the retry re-asks a question that was never re-sent.** The
relaying epic's transferable rule, kept verbatim because it generalises past this bot:

> When a gate returns the same result on every retry, the productive question is not *"how long should
> I wait"* but: **what event is supposed to change this result, and does that event actually fire on
> my retry path?** If no event fires, waiting longer is not a weaker version of the fix — **it is not
> a fix at any duration.**

*Done when:* `automatic-review` detects the structural dead end **before** entering the await loop and
surfaces the configuration change that would fix it (*"enable `re_review_on_loopback` for {bot}, or
make it optional"*).

⭐⭐ **TWO MORE SIGHTINGS, folded 2026-09-11 from `truthful-signals-054.md` items 1(d) and 2** (relayed
from API-Sheriff `-002` and Token-Sheriff `lessons-handling-…-047`). The barrier refused correctly —
`cuioss-review-bot` had reviewed only the pre-fix HEAD — but under `re_review_on_loopback: false` the
loop-back it steers the agent toward **cannot clear it by construction**; one explicit
`github_re_review` cleared it in **69 seconds**. ⇒ The cost of the dead end is not the wait, it is the
repeated loop-back an agent runs while trusting the barrier's remedy. Re-read first-party at
`356973d80`: `automatic-review/SKILL.md` skips the whole loop-back re-review section when the knob is
`false`, and justifies the default as safe *because the pre-merge barrier re-derives participation* —
the barrier is a correct NET, but it names no remedy that works at that default. `branch-cleanup.md`'s
barrier prose already warns *"if neither holds, the loop-back re-enters this barrier with the same
verdict"*; the refusal payload itself does not. *Done when (added):* the barrier's refusal names the
remedy **available under the live configuration** — the explicit re-review trigger, or the knob, or
`optional_bots` — and never a loop-back that configuration makes inert. Surface: `branch-cleanup.md`
added below (HYPOTHESIS — the barrier's refusal rendering).

⛔ Limbs A–C are the **fifth, sixth and seventh** non-convergence instances on this deliverable's
theme, and limb C is D6 limb B's rule stated in its general form.


## Claim Labels

- OBSERVED: trigger B selects exactly one bot, chosen from the newest bot-authored finding, so a
  `participated_stale` required bot whose peer comments more recently can never be selected.
  Confirm/refute at the trigger-B selection site in `automatic-review` (verify-at-outline —
  ⛔ **re-read it; PLAN-PR-025A moved this surface**).
  - verdict: corroborated | checked_at: 19453cb | by: review-apparatus/cleanup | rescoped: n/a | evidence: Re-grounded at HEAD 19453cb (was 7845a4b9a). METHOD CHANGED THIS PASS: intersection of the spec's DECLARED Expected Surface (via corpus surfaces, the single shared reader) against git diff --name-only 7845a4b9a..HEAD (204 paths). The former whole-spec-file method is RETIRED as non-discriminating - it scored hits on prose mentions of CLAUDE.md and .plan/marshal.json. ZERO declared paths moved in this window, so no premise of this spec was disturbed. NOT a line-by-line re-audit: this establishes the surface is UNDISTURBED, not that the premise was re-read.
- OBSERVED: on PR #1368 the CodeRabbit notice `Review rate limited` was filed as actionable
  finding `12ce1a` and remediated in-run by TASK-016. Confirm/refute at PR #1368's comment
  history and the plan's findings store.
- OBSERVED: two further unregistered bodies exist under the same wrapper. Confirm/refute by
  re-reading PR #1368's CodeRabbit comments — ⛔ **an unverified absence here builds a rule
  against a set that may already have grown.**
- HYPOTHESIS: the `<details>` code-anchor veto is what admitted the refusal to participation
  credit — confirm/refute at the enumerative arm's veto condition (verify-at-outline).

- OBSERVED (D5a, re-grounded first-party 2026-09-08 at HEAD `b64db6671`): `head_sha_verified` is
  hard-coded to `matched_signal == 'review'` in `github_re_review.py`, and `_references_head_sha` is
  called from exactly one site, inside the review branch against `review['commit_sha']`. The
  `issue_comment` path therefore cannot produce `head_sha_verified: true` for any bot. ⛔ **Cite the
  SYMBOL, not the line** — the relayed report and this ledger's own prior note both carried line
  numbers (`571`, `394`) that no longer resolve; the mechanism held, the coordinates did not.
  - verdict: corroborated | checked_at: b64db66713d037b456d3c0c0956c68839208b173 | by: review-apparatus/cleanup | rescoped: n/a | evidence: Re-grounded FIRST-PARTY at HEAD b64db6671, not relayed: github_re_review.py sets head_sha_verified from matched_signal == 'review' in ONE hard-coded assignment, and _references_head_sha has exactly ONE call site, inside the review branch against review['commit_sha']. The issue_comment discriminator returns 'issue_comment', so head_sha_verified: true is UNREACHABLE on that path for any bot; the module's own docstring records the symptom verbatim. The relayed line number (571) and this ledger's prior note (394) BOTH failed to resolve at HEAD - the mechanism held, the coordinates did not.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/automatic-review/SKILL.md` — trigger B
- OBSERVED: `marketplace/bundles/plan-marshall/skills/automatic-review/standards/coderabbit.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/_github_pr.py`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_pr.py`
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/automatic-review/scripts/review_completeness.py`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/automatic-review/standards/bot-participation-contract.md` — D5: the `declined` member and the `:368-379` cause statement
- OBSERVED: `marketplace/bundles/plan-marshall/skills/automatic-review/standards/cuioss-review-bot.md` — D5: the in-place-edit evidence declaration
- OBSERVED: `marketplace/bundles/plan-marshall/skills/automatic-review/standards/sourcery.md` — D2: the budget-refusal wording gap
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_re_review.py` — D5: where `head_sha_verified` is computed (verify-at-outline)
- OBSERVED: `test/plan-marshall/automatic-review/`, `test/plan-marshall/workflow-integration-github/`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-locks/scripts/merge_lock.py` — D7 limb B: `_run_rate_window_check` accepts `--pr-number` and ignores it (~:1491), against the correctly-scoped claim path (~:607)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-locks/SKILL.md` — D7 limb B: the `rate-window check` contract
- OBSERVED: `test/plan-marshall/manage-locks/` — D7 limb B
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/manage-config/standards/data-model.md` — D6 limb A: the rate-window knobs become a per-attempt interval plus an attempt ceiling.
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/automatic-review/scripts/bot_registry.py` — D6 limb A: the per-bot default interval, and limb B's per-bot TRIGGER SURFACE record.
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/workflow-integration-github/SKILL.md` — D6 limb B: `pull_request_runs` / the PR-wide `not_triggered` fail-fast observable.
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/branch-cleanup.md` — D7 limb C: the pre-merge barrier's refusal names the remedy available under the live `re_review_on_loopback` configuration (verify-at-outline — confirm whether the refusal text is rendered here or in `review_completeness.py`).

## Dependencies and Sequencing

- ⛔ **Overlaps the `github_pr` family** — never concurrent with PLAN-PR-025B, PLAN-PR-029,
  PLAN-PR-035, PLAN-PR-040.
- ⚠ Re-derive the live-plan collision set before launch.
- ⭐ **Its surface was just moved by PLAN-PR-025A (#1368)** — re-ground every line reference at
  outline; this spec was authored the day that landed.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/review-apparatus/plans/PLAN-PR-043-the-re-trigger-selector-cannot-reach-the-bot-that-gates.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and
edits NO file under `.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message.
