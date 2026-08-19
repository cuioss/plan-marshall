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

# A refusal is recorded as a refusal, and the contract says so

**Epic:** review-apparatus
**Branch prefix:** fix — bug fix

## Problem

A review bot can decline to review a PR for two structurally different reasons: the **diff is over a
ceiling it declares** (cause `size` — no amount of waiting helps, the diff must shrink), or a
**rate/budget quota is exhausted** (cause `quota` — waiting may help, depending on whether the window
reopens). The repository's recovery machinery is written around that distinction: in
`marketplace/bundles/plan-marshall/skills/automatic-review/SKILL.md` § "Rate-limit refusal recovery",
**Branch 0** fires on `cause: size` and returns `escalate_ask{reason: refusal_structural}` with the
declared `{cap}` and the `{measured_diff_size}` interpolated into its decision log, explicitly so the
operator is never offered a wait on a ceiling waiting cannot move.

**Branch 0 cannot fire from the surfaces the recovery sequence actually reads.** The same section
states that its two inputs "carry the same discriminators … the refusal's `cause` (`size` / `quota`)
… plus the stated `eta` … and the stated `cap`". Neither producer emits either field:

- `_github_pr._detect_rate_limited_bots`
  (`marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/_github_pr.py`)
  appends exactly `{'bot_kind', 'rate_limit_class', 'eta'}` per detected bot — this is what feeds
  `pr wait-for-comments` → `rate_limited_bots[]`.
- `github_re_review._ReReviewStrategy._refusal_record`
  (`.../workflow-integration-github/scripts/github_re_review.py`) returns exactly
  `{'source', 'bot_kind', 'layer', 'eta', 'body'}` — this is what feeds `refusals[]` on the
  `github_re_review re-review` return.

The cause and the cap exist only on a **third** surface, `github_pr fetch_findings` →
`refused_causes[]` / `refused_size_caps[]`, which the same SKILL section says runs *after* the
recovery ("skip this entire subsection and proceed directly to 'Producer: FIND' below").
`tools-integration-ci/standards/pr-review-operations.md` confirms the asymmetry independently:
`refused_structural` is fed by `fetch_findings` alone, while `rate_limited_bots[]` feeds only the
three awaitability members. The one body-bearing record — `refusals[]`'s `body` — is a truncated
excerpt, and no instruction anywhere tells a leaf to re-derive a cause from it.

The consequence is live for a bot in the tree today, not hypothetical. With `review_rate_window_await`
enabled and Sourcery's declared size refusal detected through `rate_limited_bots[]`, Branch 0's guard
has no input, so the refusal falls through to Branch 1 and returns
`escalate_ask{reason: rate_window_not_awaitable}` — whose shared option set opens with
"Wait another {review_rate_window_timeout_seconds}s". **A reviewer that refused because the diff is
too big is offered a wait it can never satisfy**, which is the exact non-option pairing the recovery
machinery was built to abolish. Sourcery declares both a size pattern and `rate_limit_class:
hard_quota`, so no hypothetical registry entry is needed to reach it.

Around that headline sit a cluster of defects of the same kind — a refusal or a decline observed but
recorded as something else, or described in prose that no longer matches the code:

- `_github_pr._extract_rate_limit_eta` still carries the `match.group(1) if match.groups()` shape
  whose twin, `refusal_size_cap`, was fixed 100-odd lines above it in the same file — under the
  identical docstring promise that "a bad registry edit must not break the poll return path". A
  registry pattern with an alternation or an optional group raises `AttributeError` out of the poll.
- `_github_pr._is_refusal_notice` recognises a refusal by registry wording OR by structural shape,
  and when neither fires the comment falls straight through to the participation credit in
  `github_pr.py` — a **reworded** vendor notice is silently credited as review coverage, with nothing
  counting or reporting the event. PR-Agent is the concrete carrier: its `refusal_patterns` list is
  empty, so the registry layer can never fire for it at all.
- The declared refusal wordings are unverifiable prose: the fixture that was supposed to pin them
  (`test/plan-marshall/workflow-integration-github/test_refusal_recovery_arming.py::_refusal_body`)
  ranges over **bots**, exercises each bot's *first* wording only, and falls back to a structural
  notice for a bot declaring none — so a wording that stops matching leaves a green suite.
- `automatic-review/SKILL.md` consumes `matched: true` from a re-review at two sites (trigger B, and
  the `not_triggered` remediation) without reading `head_sha_verified`, although
  `bot-participation-contract.md` states that "a `matched: true` with `head_sha_verified: false` is a
  decline, never a completed re-review". A decline observed there is credited as a review.
- `review_completeness.py`'s own module docstring, its `MalformedBotFlag` docstring and its
  `_split_bots` rejection message all describe a two-form flag split that is false for two of its
  list flags; the `deficit` usage synopsis omits a flag the parser declares; and
  `--stale-participation-bots` silently *drops* a pair whose evidence kind is not registry-admissible,
  turning a `participated_stale` observation into `absent` — two blocking members with **opposite**
  operator remedies.
- The pre-merge barrier interpolates a bare `{cap}` token into the operator-facing decision log and
  into a copy-runnable grant string without ever assigning it, while its sibling `{structural_bots}`
  gets an explicit derivation block a few lines above.
- `bot-participation-contract.md` and the per-bot registry docs still describe a currency predicate
  the code abandoned, a two-source SHA anchor that does not exist, an escalation rule that is now
  conditional, a first-observation heuristic presented as a definition, and an advance-disclosure
  surface as though it emitted a comparable figure when it emits two booleans. One registry doc
  instructs an editor to file an observed refusal in `ignore_patterns` — an unconditional drop —
  which is precisely how a refusing PR reports a clean review.

## Goal

A refusal that a bot publishes is carried, from the moment it is detected to the moment an operator
reads it, as the thing it actually is: with its cause, its declared ceiling, and the remedy that
cause implies. A decline observed at a re-review is accounted as a decline rather than as a completed
review. The declared refusal wordings and the taxonomy the verdicts land in are populations derived
from the tree and asserted, not prose anyone has to keep in step by hand. And every shipped sentence
about how any of that works is one a cold reader takes the intended meaning from.

## Deliverables

Each deliverable is independently verifiable, names the gap ids it discharges so nothing is silently
dropped, and carries an observable *Done when*. **D0 is a gate — it runs first and can halt the
plan.**

The detailed evidence for every gap id below is git-tracked and readable in the clone, under
`doc/plans/review-apparatus/{plan-dir}/gaps.md` and its sibling `verification.md`. This plan restates
what the run needs; those files are the long form, not a prerequisite.

### D0 — Derive the three populations this plan rests on, or HALT

**Gate. No other deliverable starts until this one reports.** Derive each population *from the tree*,
publish its size, and record the derivation expression:

1. **Declared refusal wordings** — the `(bot_kind, pattern)` pairs given by
   `bot_registry.refusal_patterns(b)` for every `b` in `bot_registry.bot_kinds()`
   (`marketplace/bundles/plan-marshall/skills/automatic-review/scripts/bot_registry.py`, reading the
   YAML blocks in `automatic-review/standards/{bot_kind}.md`).
2. **The non-participation taxonomy** — the members `review_completeness.py` declares as
   `STATE_*` constants, minus the complement `STATE_PARTICIPATED`.
3. **The registered bot population and each bot's `rate_limit_class`** — `bot_registry.bot_kinds()`
   and `bot_registry.rate_limit_class(b)`.

⛔ **If any of the three cannot be derived from the tree — the registry will not parse, an accessor
is missing, or a derived population comes back EMPTY — record exactly which, and STOP. Do not
hand-write the missing list.** A hand-maintained population is the defect class this plan is closing;
reproducing it inside the fix would defeat the plan while looking complete.

*Done when:* the run report carries all three populations with their sizes and the expression each
was derived from, **or** a HALT statement naming which derivation failed and why.

### D1 — Emit the refusal cause and cap on both producers, and stop the ETA extractor crashing

*Discharges:* `120` G1 (the headline), `120` G2, `120` G4.

- Add `cause` (via `_github_pr.refusal_cause`) and `cap` (via `_github_pr.refusal_size_cap`) to both
  refusal records. `_detect_rate_limited_bots` already holds the body in hand at the point it builds
  the record; `_refusal_record` takes the body as its first parameter. Neither call needs a new
  provider round-trip.
- Update the three field contracts and the two worked TOON examples to the new record shape:
  `tools-integration-ci/standards/api-contract.md` (§ Provider Field Mapping →
  `pr wait-for-comments`, the `rate_limited_bots[N]{…}` signature and its per-field table),
  `tools-integration-ci/standards/pr-review-operations.md` (the `rate_limited_bots[]` TOON example
  and the paragraph describing it), and `workflow-integration-github/SKILL.md` (the
  `rate_limited_bots[N]{…}` block).
- With both fields emitted, `automatic-review/SKILL.md`'s "Both carry the same discriminators"
  sentence becomes true and stays as written. Do **not** take the alternative disposition (rewriting
  Branch 0 to declare itself unreachable) — it preserves the non-option pairing this plan exists to
  remove.
- Apply `refusal_size_cap`'s already-shipped resolution verbatim to `_extract_rate_limit_eta`: a
  declared group that captured nothing yields **no** figure and moves to the next pattern; the
  no-group convention still keeps `group(0)`. There is no fallback from an empty group to the whole
  match.
- Re-model the arming fixture in
  `test/plan-marshall/workflow-integration-github/test_refusal_recovery_arming.py` on the shipped
  two-axis rule: `_arms` consults the **cause first** (cause `size` → escalate structurally),
  then the class map; rename `TestRecoveryArmingFollowsTheRegistryClass` to name the two-axis rule;
  and correct `test_a_hard_quota_escalates_immediately`'s docstring, which calls `hard_quota` "a
  per-PR ceiling" — the size/quota conflation removed from every other consumer, and the last live
  instance of it.

*Done when:* a size refusal from an `awaitable_window` bot yields a producer record whose
`cause == 'size'`; a test asserts the recovery arms structural escalation (not `claim_and_await`) for
that record; a test asserts a `hard_quota` bot's **size** refusal escalates with
`reason: refusal_structural`, not `rate_window_not_awaitable`; a test with a monkeypatched registry
pattern that compiles and captures nothing proves `_extract_rate_limit_eta` cannot raise; and the
arming fixture would fail if an `awaitable_window` bot's size refusal armed `claim_and_await`.

### D2 — Make a drifted refusal wording observable, and sweep every declared wording

*Discharges:* `110` G3, `110` G4, `110` G5.

- **Emit the drift.** Where a comment resolves to a registered bot, is in a declared
  `participation_evidence` publish shape, and the two recognition layers **disagree** — the structural
  shape matches but no `refusal_patterns` entry does, or the converse — record the divergence as a
  `refusal_pattern_drift[]` entry on the `fetch_findings` return naming the bot and which layer fired
  alone. `_is_rate_limit_notice`'s own docstring already states the intent ("a refusal recognized
  here but absent from the registry is a signal that the bot's `refusal_patterns` need the observed
  phrasing added"); the signal is documented and not emitted. Document the new field in
  `workflow-integration-github/SKILL.md` § `fetch_findings` output.
- **Sweep every wording.** Parametrize the detection sweep in `test_refusal_recovery_arming.py` over
  the **D0 pair population** `(bot_kind, pattern)` rather than over bots, asserting each declared
  wording is detected by the registry layer. Guard the pair population non-empty and publish its
  size. Move the structural-fallback case out of `_refusal_body` into its own explicitly-named test,
  so a bot with no declared wording is *visibly uncovered* instead of appearing covered by a fallback.
- **Record trigger semantics as data.** Add a `trigger_semantics` key to each
  `automatic-review/standards/{bot_kind}.md` YAML block, valued from the closed set
  `auto_on_push` / `requires_explicit_trigger`, plus a `bot_registry.trigger_semantics(bot_kind)`
  accessor that fails closed to `requires_explicit_trigger`. Record the new field's readers in
  `bot-participation-contract.md` § "Consumers". ⛔ **Declare `requires_explicit_trigger` for every
  bot**, because that is exactly what the code does today — `github_re_review` builds and posts the
  trigger comment for every bot uniformly — so the declared value changes no behaviour and asserts
  nothing unobserved. Where a bot may in fact be `auto_on_push`, **record a proposal** in a comment
  beside the key naming the observation that would settle it (a PR where that bot reviewed with no
  trigger comment posted). Do not invent a value from reasoning about vendor behaviour.

*Done when:* `fetch_findings` emits a drift record for a body the structural layer recognises and the
bot's `refusal_patterns` does not, pinned by a test and documented in the SKILL; the declared-wording
sweep parametrizes over the D0 pair population with a vacuity guard that publishes its size, and
removing any single `refusal_patterns` entry from a registry doc makes a *named* case fail; and every
registered bot declares a `trigger_semantics` value in the closed set, asserted by a registry-derived
test.

### D3 — Make `review_completeness`'s flag surface describe and behave like its own parser

*Discharges:* `030` G5, `030` G8, `120` G5.

- **Stop the silent drop.** `--stale-participation-bots` routes through `parse_participation`, whose
  admissibility filter (`if evidence_kind in bot_registry.participation_evidence(bot_kind)`) drops a
  pair whose kind the registry does not admit — so a `participated_stale` observation the producer
  emitted resolves to `absent`. Both members block, so this is not a false pass, but
  `branch-cleanup.md` states their remedies are **opposite** (a `participated_stale` bot did publish,
  so the productive action is a re-review trigger) and the barrier renders those remedies to an
  operator. **Take disposition (a): give the stale flag its own parse that enforces the pair SHAPE but
  does not re-apply the participation admissibility filter.** The producer already established that
  the kind matched a publish shape, so the filter is redundant on the happy path and destructive off
  it. Record the rejected alternative (raise `MalformedBotFlag`) and why: it converts a producer /
  consumer registry skew into a hard stop at the merge gate, where the operator has the least room.
- **Correct the FORM prose.** Restate the split as **four** pair-form flags —
  `--participated-bots`, `--stale-participation-bots`, `--refused-causes`, `--refusal-size-caps`, the
  last two carrying `bot_kind:value` rather than `bot_kind:evidence_kind` — and the bare-form
  remainder, in all three passages: the module docstring, the `MalformedBotFlag` docstring, and the
  `_split_bots` rejection message (which currently tells a caller holding a rejected `bot_kind:cause`
  token that pairs "belong on a pair-form flag (--participated-bots / --stale-participation-bots)",
  the wrong advice, in the message the caller actually sees). Make that message name the pair-form
  set generically rather than two of the four.
- **Fix the `deficit` synopsis — this plan OWNS the edit.** Add `[--refusal-size-caps [<csv>]]` in
  the same position it occupies on the `check` line.
  ⚠ **Shared line with plan `520`.** `520-nobody-reviewed-and-reviewed-clean-are-still-one-signal`
  § D5 carries the same gap from the other side (as `040/G9`) and names this plan as the owner of the
  edit, keeping only its own test extension. If the line already carries the flag when this run
  reaches it, `520` landed first: **make no edit, record it as already discharged, and do not revert
  or reformat it.** Either way the surviving requirement is the *Done when* below.
  `_add_bot_observation_flags` declares it on both subcommands and
  `automatic-review/SKILL.md`'s canonical `deficit` block documents it; only the module's own usage
  line disagrees, which makes the cap-only cause recovery unreachable from documented usage.
- Also state, at the barrier's `review_completeness check` invocation in
  `phase-6-finalize/standards/branch-cleanup.md` and in the two `## Canonical invocations` blocks in
  `automatic-review/SKILL.md`, **which** list flags take `bot_kind:value` pairs and which take bare
  tokens — the pair form is stated today only at the FIND step.

*Done when:* `--stale-participation-bots pr-agent:not-a-declared-kind` with `pr-agent` required
resolves the bot to `participated_stale` and in no case to `absent`, pinned by a test; no passage in
the module names a flag-FORM partition that a sweep of `_add_bot_observation_flags`'s list flags
against their parse functions contradicts, ideally pinned by a test that derives both form-sets from
the parse routing; the two usage synopsis lines differ only by the flags genuinely unique to each
subcommand; and each of the three invocation sites states the pair-form set in its own text.

### D4 — Make the operator-facing refusal surfaces say something an operator can act on

*Discharges:* `120` G3, `120` G7, `120` G11.

- **Give `{cap}` a derivation.** The barrier interpolates a bare `{cap}` into the headless
  decision-log message, the `ask` prompt body, and the pending-findings obligations —
  **re-derive the interpolation count and their sites; do not trust a remembered figure** — while
  binding only `{refusal_size_caps}` (defined as a `{bot_kind}:{cap}` **pair list**) and the scalar
  `{measured_diff_size}` further up. Add a derivation block next to the existing `{structural_bots}`
  derivation, naming the payload field it reads, and **decide the multi-bot rendering explicitly as a
  pair list** — a scalar token is wrong for a per-bot value and has no correct rendering when
  `{structural_bots}` holds two bots. Extend the read instruction so the field the derivation names is
  among the fields read from the `review_completeness check` return. Note the naming trap while you
  are there: the payload is spelled `refused_causes[]` / `refused_size_caps[]` on the
  `fetch_findings` return and `refusal_causes[]` on the `review_completeness check` return; the
  derivation must name which one it reads.
  ⚠ This is **not** the "structurally unbound … would report a fiction" case that standard describes
  for the UNKNOWN path — there the producer never emitted the value; here it did.
- **Cover `refused_structural` in the parity sweep.** The widened-member parity test in
  `test/plan-marshall/workflow-integration-github/test_pre_merge_barrier.py` hand-lists its members
  and omits `refused_structural` — the member whose behaviour at the barrier is the whole point.
  **Derive the parametrisation from the taxonomy's own blocking-member set (D0 population 2) minus
  the members the scenario cannot produce**, so the next member joins automatically; a hand-list is
  the staleness shape this fails on.
- **Point the default-path loop-back prompt at the remedies.** On the default configuration the
  operator sees only "prompt the user to run `/plan-marshall action=finalize` to replay the finalize
  step" (`plan-marshall/workflow/execution.md`, the ELSE branch of the loop-back continuation) — an
  instruction that, for a structural refusal, reaches the identical verdict. The three copy-runnable
  remedies live in the decision log and nothing on this surface points at it. Add a pointer to the
  decision log to the generic prompt, **dispatcher-wide rather than barrier-specific** — that is why
  the earlier run correctly declined to do it inline.

*Done when:* `{cap}` has a stated derivation in `branch-cleanup.md` that names the payload field it
reads and the multi-bot rendering, and a test asserts the derivation block exists rather than only
that the placeholder appears; the parity sweep covers `refused_structural` and adding a blocking
member to the taxonomy either covers it automatically or fails a totality assertion; and the
default-path loop-back prompt names where the remedies are.

### D5 — Account a decline as a decline, and make the call-site population test say what it asserts

*Discharges:* `010` G6, `110` G7, `110` G8, `010` G12.

- **Consume `head_sha_verified`.** `bot-participation-contract.md` states the rule — "a `matched:
  true` with `head_sha_verified: false` is a decline, never a completed re-review, and a consumer
  that reads `matched` alone credits a review that never named the commit it matched" — and
  `automatic-review/SKILL.md` reads `matched` alone at **both** its re-review consumer sites (trigger
  B's `matched: true` arm, and the `not_triggered` remediation's), while its FIND-step
  `review_completeness check` invocation does not interpolate `--declined-bots`. Mirror
  `phase-6-finalize/standards/branch-cleanup-rereview.md`'s treatment at both sites: read
  `head_sha_verified`, route `matched: true` / `head_sha_verified: false` to a decline, accumulate
  `{declined_bots}`, and interpolate `--declined-bots "{declined_bots}"` at the FIND-step invocation.
  Raise the confirmed-site flag count for the participation-guard row in `_CONFIRMED_SITES`
  (`test/plan-marshall/automatic-review/test_bot_participation_contract.py`) in lock-step, and delete
  the header comment recording the omission as intentional.
- **Correct that roster's own docstring**, which states "the pre-merge barrier passes five flags, not
  the participation guard's six" while the tuple immediately below declares the same count for both
  family-A sites. Better than restating a corrected literal: derive the sentence from the tuple, so a
  future count change cannot re-open the drift.
- **Assert each site's class.** `TestCallSitePopulation` derives the site population and asserts each
  member's interpolated flag count and quoting, but never each site's **class** — whether it reads
  the scan, the durable ledger, or a deduped projection. Extend the per-site assertions to record it.
- **Remove the hard-coded taxonomy ordinal** in the same module's guard comment, which calls
  `STATE_PARTICIPATED` "not a ninth member" while the members tuple has grown past that. Replace the
  literal with prose carrying no count, or interpolate it from the tuple's length — a literal ordinal
  rots on every taxonomy growth, which is how it got here.

*Done when:* every `matched: true` arm in `automatic-review/SKILL.md` is paired with a
`head_sha_verified` read, the FIND-step invocation forwards `--declined-bots`, and the flag-count
assertion rises in lock-step; no count literal in `TestCallSitePopulation`'s prose disagrees with
`_CONFIRMED_SITES`; each discovered call site carries an asserted class; and no hard-coded ordinal
for the taxonomy's cardinality remains in the test module.

### D6 — Rewrite the contract and registry prose that no longer describes the code

*Discharges:* `010` G4, `010` G13, `120` G6, `120` G10.

Every site below is prose whose only value is what a later reader does with it, so D6's verification
is a **cold read** (see § Verification), not "the text was changed".

- **The abandoned two-arm predicate and the two-source anchor.** The sites `010 G4` § Where names still describe a
  currency predicate the code replaced, or a two-source SHA anchor that never shipped. Rewrite each to
  the predicate the code actually implements **as read at the time of the run** — not from a
  remembered description, and not from this plan. The sites: `workflow-integration-github/SKILL.md`
  (the canonical `fetch_findings` step body — the single most-read description of the behaviour, and
  the one an executing agent follows); `bot-participation-contract.md` § "Evidence for a bot that
  edits one comment in place" (the "stored finding, or … the noise sidecar" two-source arm; and the
  "edited in place (`updated_at` differs from `created_at`)" arm, which the code does not compute);
  `bot-participation-contract.md` § the "union of the stored-finding SHAs and the recorded sidecar
  SHAs" paragraphs, **including the "observation sidecar" naming inside them** (the README table
  assigns these here; describe the ledger under whatever name the code carries when this run reads
  it); `automatic-review/SKILL.md`'s restatement of the same predicate in a workflow body;
  ⛔ **Ownership of that document's passages is not settled here.** Do not resolve it from this
  deliverable: read the table in [`doc/plans/review-apparatus/README.md`](../README.md) § "The
  shared-document split", which is the **single authority** for who writes which passage. A
  passage the table assigns elsewhere is **reported and left alone** —
  not rewritten here, and not counted a survivor — even when a survivor search returns it.
  `automatic-review/standards/pr-agent.md` at two sites; and `bot_registry.py`'s
  `participation_requires_update` docstring. Sweep for survivors with **two** different searches, not
  one — "first presence / first-present / `updated_at` movement / `updated_at` vs `created_at`" finds
  a different subset than "union of the stored / sidecar". Exclude the `wait-for-comments` completion
  predicate and the `github_re_review` matchers: those are legitimately timestamp-keyed and are not
  the currency test.
- **The pr-agent registry doc's two false statements.** Qualify its unconditional "The recovery
  sequence therefore escalates immediately for this class (`escalate_ask{reason:
  rate_window_not_awaitable}`)" with the cause condition and cross-reference Branch 0 — Branch 1 is
  conditional now, so an `unknown`-class bot refusing on size escalates with `refusal_structural`.
  And change its instruction to "record its OBSERVED text in `ignore_patterns`" to `refusal_patterns`,
  adding the size-overlay note so a future observed size refusal is filed on both lists.
  `ignore_patterns` is an **unconditional drop**: an editor following the current sentence would
  cause the very failure the contract names — a PR whose every required reviewer refused reporting a
  clean, complete review. (This one is pre-existing, inherited by no earlier plan.)
- **The advance-disclosure overstatement.** `bot-participation-contract.md` and
  `phase-6-finalize/workflow/create-pr.md` both say a diff's size is measurable at PR creation "so
  the exclusion is knowable in advance", while the surface returns two **booleans** per reviewer
  (declares a ceiling at all / is the ceiling's value recoverable from a future notice) and no figure
  a diff can be compared against. **Take disposition (a): re-word both sentences to promise what the
  surface delivers** — *which* reviewers carry a ceiling, not whether this diff exceeds one. Record
  the rejected alternative (a declared `declared_cap` registry constant) and why: a declared figure
  goes stale silently when the provider changes its budget, which the shipped design note at
  `_github_pr.refusal_size_cap` deliberately rejected. Both files already carry an honest disclaimer
  several paragraphs away; the residual defect is the unqualified sentence, not the surrounding
  treatment, so keep the edit narrow.
- **Re-wrap the create-pr blockquote** whose taxonomy-count edit left a stranded two-word line and an
  over-long neighbour. Cosmetic, and included because it is the visible trace of an edit made without
  re-reading the surrounding paragraph.

*Done when:* both survivor searches return no hit that describes the currency test, except for
passages the README table assigns elsewhere **or does not name at all** — each of those reported rather than fixed, and each
rewritten site names the single ledger as the sole source; neither pr-agent sentence contradicts
`automatic-review/SKILL.md` § "Rate-limit refusal recovery" or `bot-participation-contract.md`
§ "The three per-bot marker lists"; no shipped document claims the size exclusion is decidable in
advance unless the disclosure emits a comparable figure; no line in the create-pr blockquote is a
stranded fragment; and the cold read in § Verification returns the intended reading.

## Out of scope

Each entry states *why*, because with no operator watching, the written reason is the only thing that
holds the boundary mid-run.

- **The participation-currency mechanics** — the currency ledger and its artifact name, the
  merge-candidate SHA anchor, the first-observation timestamp guard, the empty-SHA non-idempotence,
  the key-only-row migration, the unresolved-head UNKNOWN signal, and the cross-iteration filing dedup
  at `github_pr.py`. **Excluded because plan `500` in this epic owns them**, and two plans editing
  the same predicate concurrently produce a merge conflict in the one function both depend on. This
  plan touches `github_pr.py` only in the refusal-detection block (D2's drift record) and never the
  currency path.
- **Branching the await/trigger path on `trigger_semantics`** (D2 adds the field and the accessor
  only). Excluded because the branch is only correct once each bot's value rests on an observation,
  and a cloud run cannot observe vendor trigger behaviour; declaring the fail-closed value that
  matches today's uniform behaviour is the honest increment, and branching on unverified values would
  make a bot stop being triggered at all.
- **Making the CI provider scripts return non-zero on `status: error`.** Excluded because its blast
  radius is every `ci` call site in the tree, which needs its own plan; the exit-0 hole is filed
  separately as `030` G3 and is not in this plan's gap set.
- **Widening the exit-code convention across the remaining finalize docs** (`030` G6) and the
  missing convention in `branch-cleanup-rereview.md` (`030` G4). Excluded because they are about the
  exit-code convention's reach, not about refusal accounting — a different mechanism with a different
  correctness argument.
- **Amending the landed run reports** (`120` G8, `120` G9, `110` G6, `030` G11, `010` G5, `010` G10).
  Excluded because a `report-NN.md` is a dated record of one execution, not documentation of current
  state; correcting one is report hygiene owned by the epic's collect step, and editing another
  plan's record from this plan would leave two accounts of the same run in git.
- **Adding a derived roster over the participation *sites*** (`010` G9). Excluded because its
  population is the participation-crediting sites, which is plan `500`'s surface; D5 extends the
  existing call-site roster with a class assertion and stops there.
- **Deriving the added regression test's bot list from the registry** (`110` G10) and the
  report-citation corrections (`110` G7's first half). Excluded as a maintenance cost with no
  behavioural consequence — the gap itself records the impact as low — and D5 already takes G7's
  substantive half (the per-site class assertion).

## Expected surface

Production code:

- `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/_github_pr.py` — D1
  (both producer records' new fields; the ETA extractor's empty-group resolution).
- `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_re_review.py`
  — D1 (`_refusal_record`'s new fields).
- `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_pr.py` — D2
  only, and only the refusal-detection block plus the new `refusal_pattern_drift[]` return field.
  ⚠ **Not the currency path** — see § Out of scope.
- `marketplace/bundles/plan-marshall/skills/automatic-review/scripts/bot_registry.py` — D2
  (`trigger_semantics` accessor), D6 (`participation_requires_update` docstring).
- `marketplace/bundles/plan-marshall/skills/automatic-review/scripts/review_completeness.py` — D3
  (the stale-flag parse, the three FORM passages, the `deficit` synopsis).

Contracts and workflow prose:

- `.../automatic-review/SKILL.md` — D1 (the discriminator sentence stays, now true), D3 (canonical
  invocation form notes), D5 (both `matched: true` arms, the FIND-step `--declined-bots`), D6 (the
  restated predicate).
- `.../automatic-review/standards/bot-participation-contract.md` — D2 (§ Consumers), D6 (the currency
  evidence arms, the union/sidecar paragraphs, the advance-disclosure sentence).
- `.../automatic-review/standards/{coderabbit,pr-agent,sourcery}.md` — D2 (`trigger_semantics`), D6
  (pr-agent's two false statements, its predicate restatements).
- `.../workflow-integration-github/SKILL.md` — D1 (`rate_limited_bots[]` shape), D2 (the drift field),
  D6 (the canonical `fetch_findings` step body).
- `.../tools-integration-ci/standards/api-contract.md` and `.../pr-review-operations.md` — D1 (the
  `rate_limited_bots[]` field contract and its worked TOON example).
- `.../phase-6-finalize/standards/branch-cleanup.md` — D3 (the pair-form note), D4 (`{cap}`'s
  derivation and the read instruction).
- `.../phase-6-finalize/workflow/create-pr.md` — D6 (the advance-disclosure sentence, the blockquote
  re-wrap).
- `.../plan-marshall/workflow/execution.md` — D4 (the loop-back continuation prompt).

Tests:

- `test/plan-marshall/workflow-integration-github/test_refusal_recovery_arming.py` — D1, D2.
- `test/plan-marshall/workflow-integration-github/test_pre_merge_barrier.py` — D4.
- `test/plan-marshall/automatic-review/test_bot_participation_contract.py` — D5.
- `test/plan-marshall/automatic-review/test_structural_refusal.py` — D3, D4 (the derivation
  assertions; the existing empty-group cases there are the pattern D1's ETA tests mirror).
- `test/plan-marshall/workflow-integration-github/test_github_pr.py` — D2 (the drift record).

## Claim labels

Every premise below was read at the tree the plan was authored against. **Re-derive every count and
re-read every cited symbol at the moment of the claim** — the clone the run executes in is not
guaranteed to match the tree the author saw.

| Claim | Label | Confirm/refute artifact |
|---|---|---|
| `_detect_rate_limited_bots` appends exactly `{bot_kind, rate_limit_class, eta}` — no `cause`, no `cap` | OBSERVED | `_github_pr.py`, the `detected.append({…})` literal in `_detect_rate_limited_bots` |
| `_refusal_record` returns exactly `{source, bot_kind, layer, eta, body}` | OBSERVED | `github_re_review.py`, `_ReReviewStrategy._refusal_record`'s return literal |
| `automatic-review/SKILL.md` claims both producers carry the `cause` and the `cap`, and Branch 0's guard and `{cap}` both depend on them | OBSERVED | `automatic-review/SKILL.md` § "Rate-limit refusal recovery" — the "Both carry the same discriminators" paragraph and § "Branch 0" |
| `refused_causes[]` / `refused_size_caps[]` exist only on the `fetch_findings` return, which the same section runs *after* the recovery | OBSERVED | `automatic-review/SKILL.md` ("skip this entire subsection and proceed directly to 'Producer: FIND'"); corroborated by `tools-integration-ci/standards/pr-review-operations.md`'s member-to-producer table |
| Sourcery declares both a size pattern and `rate_limit_class: hard_quota`, so the non-option pairing is reachable with no new registry entry | OBSERVED | `automatic-review/standards/sourcery.md` YAML block (`refusal_patterns`, `refusal_size_patterns`, `rate_limit_class`) |
| `_extract_rate_limit_eta` carries the unresolved `group(1) if match.groups()` shape under the same docstring promise its fixed twin carries | OBSERVED | `_github_pr.py`, `_extract_rate_limit_eta` vs `refusal_size_cap`'s resolution comment |
| The `_extract_rate_limit_eta` crash is **latent**: every currently declared ETA pattern carries exactly one *mandatory* group | OBSERVED | `automatic-review/standards/coderabbit.md`'s `rate_limit_eta_patterns` — the only bot declaring any |
| **Absence:** no `refusal_pattern_drift` field or symbol exists anywhere in `marketplace/` or `test/` | OBSERVED | a tree-wide search for `refusal_pattern_drift` (zero hits at authoring) — **re-run it; an unverified absence builds something that may already exist** |
| **Absence:** no `trigger_semantics` / `auto_on_push` / `requires_explicit_trigger` appears in `marketplace/` or `test/` | OBSERVED | a tree-wide search for those three tokens (zero hits at authoring, hits only inside `doc/plans/`) — re-run it |
| **Absence:** `automatic-review/SKILL.md` contains no occurrence of `head_sha_verified` | OBSERVED | a count of `head_sha_verified` in that one file (zero at authoring) — re-run it |
| The declared refusal-wording population is 3 pairs (coderabbit 1, pr-agent 0, sourcery 2) | OBSERVED — **a lead, not a fact** | D0 population 1, re-derived from `bot_registry.refusal_patterns` over `bot_kinds()`. Do not trust this number |
| The non-participation taxonomy has ten members and the test module's guard comment still calls the complement "not a ninth member" | OBSERVED — **a lead** | D0 population 2, and the guard comment in `test_bot_participation_contract.py` |
| `parse_participation`'s admissibility filter drops a non-admissible pair silently, so a `participated_stale` observation resolves to `absent` | OBSERVED | `review_completeness.py`, `parse_participation`'s `if evidence_kind in bot_registry.participation_evidence(...)` and the `--stale-participation-bots` entry's comment |
| `review_completeness.py` has nine list flags of which four are pair-form, contradicting all three FORM passages | OBSERVED — **re-derive both form-sets from the parse routing** | `_add_bot_observation_flags` and the `parse_causes` / `parse_participation` / `_split_bots` routing |
| `{cap}` is interpolated at several barrier sites with no assignment, while `{structural_bots}` has an explicit derivation block | OBSERVED — **re-derive the interpolation sites** | `phase-6-finalize/standards/branch-cleanup.md`, every `{cap}` occurrence vs the `{structural_bots}` derivation fence |
| The barrier parity sweep hand-lists three members and omits `refused_structural` | OBSERVED | `test_pre_merge_barrier.py`'s `parametrize` list for the widened-member parity test |
| The default-path loop-back prompt names only a finalize replay and points at no remedy | OBSERVED | `plan-marshall/workflow/execution.md`, the ELSE branch of the loop-back continuation |
| The sites `010 G4` § Where names still describe the abandoned predicate or the two-source anchor | HYPOTHESIS — the site *set* is re-derived from `010 G4` § Where and from the searches below; no count is carried here | The two survivor searches D6 specifies, run over `marketplace/bundles/plan-marshall/skills/` and `test/`. The count settles only when both searches are re-run |
| Re-modelling `_arms` on the cause axis changes no currently-asserted outcome, because `escalate_immediately` is already right for every registered bot | HYPOTHESIS | Run the re-modelled fixture against the unchanged registry: every existing case must still pass. If one flips, the registry gained a bot this premise did not cover — report it rather than adjusting the assertion |

An asserted **absence** is verified exactly as an asserted presence, and is the higher-risk half
here: this plan builds three things (a drift field, a registry key, an accessor) on the claim that
they do not already exist. Confirm each before building.

## Verification

Beyond the per-deliverable *Done when* conditions:

1. **Build gate.** This plan changes Python, so the lane's conditional build gate fires: run the full
   verify and report its result. Do not report a deliverable done on an unrun suite.
2. **Targeted suites.** Run, and name in the report: `test_refusal_recovery_arming.py`,
   `test_pre_merge_barrier.py`, `test_structural_refusal.py`, `test_bot_participation_contract.py`,
   `test_github_pr.py`. Every one of these has an existing assertion this plan is capable of
   invalidating.
3. **Fail-first.** For D1's headline, D2's drift record and D3's stale-flag parse, show the new test
   **failing against the pre-change code** before the fix. A test that passes both ways proves
   nothing about the defect it names.
4. **Population publication.** The report states each D0 population, its size, and the expression it
   was derived from — re-derived at report time, not carried from D0's first run.
5. ⭐ **Cold read of the contract prose (D6, and D5's SKILL edits).** Have the pre-PR verification
   sub-agent read the changed text **cold — without this plan and without the gaps files** — and
   report, in its own words and **verbatim in the run report**:
   - (a) Reading `bot-participation-contract.md` § "Evidence for a bot that edits one comment in
     place": what is a participation credit anchored to, and **how many sources supply that anchor?**
     The intended reading is *one* — a single currency ledger. ⚠ **Do not ask about, and do not act
     on, the first-observation arm's definition-versus-assumption wording** — that sentence is not
     this plan's, per the README table — so a "wrong" reading there is the other plan's to fix, and a
     mismatch is **reported, never corrected here.**
   - (b) Reading `automatic-review/standards/pr-agent.md`'s `rate_limit_class` section alone: a
     PR-Agent refusal caused by the diff being over a size ceiling escalates with which `reason`?
   - (c) Reading the advance-disclosure paragraphs in `bot-participation-contract.md` and
     `create-pr.md`: can a plan decide, before requesting review, whether **its own diff** exceeds a
     reviewer's ceiling? If yes, the wording failed.
   - (d) Reading `automatic-review/SKILL.md`'s two re-review consumer arms: does `matched: true`
     alone mean the bot reviewed this HEAD?
   - (e) Reading `automatic-review/SKILL.md` § Branch 0 together with the producer field contracts:
     where does the `{cap}` it interpolates come from?

   The intended readings are: (a) the merge candidate's commit, one ledger, a bounded assumption;
   (b) `refusal_structural`; (c) no — only *which* reviewers carry a ceiling; (d) no, it must be
   paired with `head_sha_verified`; (e) the producer's refusal record, which now carries it. **A
   mismatch is a wording failure, not a reader failure** — fix the text and re-read. Record both
   readings if it took two passes.
6. **Survivor sweep by reading.** D6's two searches are re-run at the end and their zero-hit result
   stated; a search that was never re-run after the last edit is not evidence.
7. **Collateral check.** Confirm the diff touches no file outside § Expected surface — in particular
   no change to `github_pr.py`'s currency path, which plan `500` owns.

## Notes

### Sequencing against plan `500`

Plan `500` in this epic is authored in parallel and owns the **participation-currency mechanics**:
the currency ledger and its artifact naming, the merge-candidate SHA anchor and its first-observation
guard, the empty-SHA and key-only-row defects, the unresolved-head UNKNOWN signal, and the
cross-iteration filing dedup. This plan's subject is **refusal and decline accounting**, and it also
carries the stale-prose sweep of `010 G4`; for the shared contract document the README table decides
each passage. Where the two plans touch, this plan cites rather than duplicates:

- **`github_pr.py` is a shared file.** This plan edits only its refusal-detection block and adds one
  return field (D2). It must not touch `_reviewed_at_merge_candidate`, the currency-record readers
  and writers, or the `(bot_kind, comment_id)` dedup. If a conflict arises anyway, **report it and
  leave `500`'s side alone** rather than resolving both — a merge resolution written by the plan that
  does not own the mechanism is how a fix gets silently reverted.
- **`bot-participation-contract.md` is a shared file.** Do not resolve ownership from this plan:
  read the table in [`doc/plans/review-apparatus/README.md`](../README.md) § "The shared-document
  split", which is the **single authority** for who writes which passage. Neither this note nor D6
  assigns a passage; where either names one, it does so to identify a site it edits, never to state
  who owns it — so
  there is one copy to keep true. A passage the table assigns to `500` is **reported and left alone**
  when it still carries a pre-fix claim; the two runs must never write conflicting rewrites of one
  passage. D6 rewrites the *prose* describing the
  currency predicate, but the predicate it must describe is **whatever the code does at the time of
  the run**. Read the code, not this plan and not a landed report; if `500` has already changed the
  predicate, describe the changed one. If `500` has *not* landed, describe the predicate as it stands
  and note in the report that the section may need a follow-up touch once `500` lands.
- **`automatic-review/SKILL.md` is this plan's alone.** `500` excludes it — see its § Out of scope
  and § Expected surface — so a conflict there is not an expected overlap but a signal that `500`
  drifted out of its lane; report it rather than resolving it.

### Provenance, and what not to go looking for

Every defect here was derived by an epic-wide audit of landed `review-apparatus` plans, which wrote
per-plan `gaps.md` and `verification.md` files. Those are **git-tracked** and readable in the clone:

- `doc/plans/review-apparatus/120-review-barrier-deadlocks-on-a-refusing-bot/gaps.md` — G1, G2, G3,
  G4, G5, G6, G7, G10, G11.
- `doc/plans/review-apparatus/010-participation-credited-from-a-superseded-commit/gaps.md` — G4, G6,
  G12, G13.
- `doc/plans/review-apparatus/110-participation-derived-from-a-lossy-view/gaps.md` — G3, G4, G5, G7,
  G8.
- `doc/plans/review-apparatus/030-a-workflow-doc-prescribes-a-flag-no-script-declares/gaps.md` — G5,
  G8.

Read them for the long-form evidence. This plan is written to stand without them, so a missing or
moved `gaps.md` is a reason to proceed from the plan, never to stop.

⛔ **The orchestrator ledger under `.plan/` is git-ignored and does not exist in this clone.** There
is no plan spec, no status file, and no landing record to open. Do not go looking for one, and do not
report a run blocked on its absence.

### Every gap in the input set still reproduced at authoring

Each of the twenty gap ids listed above was re-read against the tree before being written into this
plan, and **none was dropped** — every cited symbol, line, and false sentence was still present. Two
carry a scope note worth keeping:

- `120` G2's crash is **latent**, not live: the deferred report's stated reason ("no registered bot
  declares `rate_limit_eta_patterns`") is false — CodeRabbit declares several — but every declared
  pattern carries exactly one *mandatory* capturing group, so `group(1)` cannot currently be `None`.
  The fix is worth making because the docstring promises safety the code does not deliver, and one
  registry edit with an alternation makes it live. Do not overstate it as a live crash.
- `120` G10's second half (`ignore_patterns` instead of `refusal_patterns`) is **pre-existing** — it
  predates every plan in this epic. It is included because it is the sharpest instance of the same
  mechanism, not because an earlier plan owed it.

### Two dispositions this plan takes so the run does not have to decide

The run has no operator to ask, so both open semantics questions in the input set are decided here
and the rejected alternative is recorded rather than left open:

- **D3, the stale-flag parse:** take the shape-only parse, not the loud rejection. Reason in the
  deliverable.
- **D6, the advance disclosure:** re-word the promise, do not add a declared cap constant. Reason in
  the deliverable.

Where a question genuinely cannot be settled from the tree — which bots are `auto_on_push` — D2
authors a **recorded proposal** beside a fail-closed declared value, never a guess.
