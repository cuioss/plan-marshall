# PLAN-PR-005: Participation is derived from a lossy view, so a proven reviewer reads as absent

epic: review-apparatus
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-marshall-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

## Provenance — `truthful-signals` PLAN-116 Defects C and E

PLAN-116 was released to this epic on 2026-07-30 and split. This plan carries **Defects C and E
together**, because they are one root cause seen twice: participation is computed from a **derived,
lossy view** instead of from the durable store. Sibling slices: PLAN-PR-001 (A), PLAN-PR-002 (B),
PLAN-PR-006 (D), PLAN-PR-007 (F).

## Objective

Two observed false negatives on participation, both from reading a lossy projection rather than the
ledger:

- **Defect C — dedup empties the set the barrier is fed.** `fetch_findings` deduped pr-agent's
  already-stored comment, which emptied `participated_bots`; `branch-cleanup.md` instructs the caller
  to feed **exactly that set** to the participation predicate → verdict `pr-agent: absent`. Observed
  LIVE during PLAN-114's finalize, where it **would have falsely blocked a legitimate merge**. The
  plan re-derived participation from the store (`pr-agent:issue_comment`, reviewed sha == HEAD) →
  `complete`, and recorded the discrepancy in its decision log rather than laundering it.
- **Defect E — proven participation is not re-credited across FIND calls.** Participation is derived
  from the **current call's comment scan**, so a bot whose review carries no fresh `updated_at`
  movement since the previous call reads `absent` on the next one. On PR #1056 pr-agent genuinely
  reviewed at 15:07 and its Guide was filed as finding `7e3f74` (`bot_kind: pr-agent`,
  `reviewed_commit_sha: 69f2270…`); on **loop-back iteration 2 the same bot read `absent`**. Nothing
  about its participation changed — **the signal moved because the query moved.**

Make participation derive from the durable ledger union with the current scan, so a proven
participation for a given head SHA survives a re-query.

⛔ **A dedup intended for storage hygiene must never be the input to a participation predicate.**

## ⛔ ABSORBED 2026-08-09 — a load-bearing ordering constraint, and two more lossy channels

### 1. `participation_evidence(bot)[0]` is read as a bot's synthesized publish shape by SEVEN modules

Source: `generic-charter-language-specific-defect-010`, first-party (Q-Gate `dc3ba1`, 3-outline).

PLAN-PR-022 widened pr-agent's `participation_evidence` with `inline`, and had to append it **after**
`issue_comment` — because `test_bot_participation_contract.py:638` reads `participation_evidence(bot)[0]`
and **seven registry-derived consumers** would otherwise have been silently re-pointed **with no test
failing**.

⛔⛔ **This is a live constraint on D1's consumer enumeration, and it is exactly this plan's subject:**
the first element of a list is being consumed as a semantic field. Any plan that reorders it changes
behaviour invisibly. ⇒ D1 must classify each consumer by whether it reads the **list** or the
**first element**, and D3's decoupling must cover the ordering dependency, not only the dedup one.
⚠ PLAN-PR-006 must respect the same constraint — noted in both specs.

### 2. Two bots' real content never reached the findings store, and three mechanisms hid it

Source: `truthful-signals-025` item 3. ⛔ **Second-hand, NOT re-derived — a lead.**

⭐⭐ **The part that inverts a decision this epic has already faced twice: Sourcery looked worthless in
the metrics table and in fact produced the run's ONLY non-overlapping findings** — one of them a
hard-coded `parents[3]` root depth, the `#894` archetype. ⇒ **A per-reviewer metrics table that scores
a bot on findings that reached the store scores a bot at zero when the TRANSPORT failed, and that zero
then feeds a retirement argument.** The measurement and the retirement decision are coupled through a
lossy channel — which is this plan's title condition, one layer further out than Defects C and E.

### 3. The barrier reads a store it can see, over a provider state it cannot

Source: `code-intelligence-substrate-011`, first-party on #1127. **14 of 60 GitHub comment threads
remained unresolved while our own store showed 0 pending.** That is thread-resolution state rather than
undispositioned work — ⛔ **but a barrier reading only our own store cannot tell the difference**, and
it recorded `participation_complete: true` alongside its own caveat about exactly this.

⇒ Same shape as the two above: **the predicate is satisfied by the projection it reads, over a reality
it does not.** Add provider thread-state to D1's consumer classification.

## Deliverables

1. **D1 — GATE (mutates nothing): re-establish both defects at HEAD and derive the consumer
   population.** ⚠ **Defect E arrived as a FORWARDED message and neither originating epic had
   independently re-read the source** — it is a LEAD, not a fact. Enumerate every consumer of
   `participated_bots` (or its successor) and classify each by whether it reads the scan, the ledger,
   or a deduped projection. C and E are a SAMPLE of the shape, not its extent.
2. **D2 — participation is monotonic within a finalize run for a fixed head SHA.** Once a bot's review
   is observed and filed for a given `reviewed_commit_sha`, later `fetch_findings` calls for that same
   head SHA report it as participating regardless of `updated_at` movement. Derive from **the ledger
   union with the current scan**, not the scan alone; the ledger already carries `bot_kind` and
   `reviewed_commit_sha`. **Reset only when the head SHA advances.** (This direction came from the
   sibling epic as a suggestion, explicitly ours to accept or reject at D1 — accepting it is a
   decision this plan makes on evidence, not an inherited instruction.)
3. **D3 — the storage dedup is decoupled from the participation predicate.** The predicate's input is
   the durable record, so a hygiene change to storage cannot silently change a merge verdict.
4. **D4 — tests, each verified to FAIL pre-fix.** (a) A bot whose comment was deduped on storage is
   still credited as participating. (b) A bot proven on FIND call 1 is still credited on call 2 with
   no `updated_at` movement and an unchanged head SHA. (c) Advancing the head SHA DOES reset the
   credit. (d) The consumer population is derived, non-empty, and contains every known member.

## ⭐⭐ THE ROOT CAUSE IS NAMED — three defects, one cause (inbox `truthful-signals-006`/`-007`, 2026-07-30)

Two API-Sheriff landings (PR #132 / PLAN-30 and PR #133 / PLAN-15) converge on a single statement that
generalises this plan's title from *"a lossy view"* to its actual mechanism:

⛔ **Participation is inferred from PROXIES rather than read from the bot's own artifacts.**

| Proxy relied on | Failure it produces |
|---|---|
| comment `created_at` | **false negative** for a bot that edits one comment in place |
| `comments_found: 0` | a **rate-limited** bot is indistinguishable from a **clean review** |
| **check-run presence** | a bot that reviews *without* publishing a check is indistinguishable from one that never ran — and the wait loop polls for a signal that can never arrive |

**Corrective (adopt as the shape of D1/D2)**: read participation from the bot's own artifacts — review
comments and review submissions — reserve check-run state for bots that genuinely publish one, and record
per-bot trigger semantics explicitly (`auto_on_push` vs `requires_explicit_trigger`, with the trigger
command for the latter). ⭐ **For a bot needing an explicit trigger, POST the trigger** rather than
waiting for a spontaneous pass that cannot come.

## ⛔ AND THE CONTRACT ALREADY SAYS THIS. The defect is enforcement, not authorship.

⭐ **This reframes the plan and must not be missed** — verified first-party by the forwarding epic, and
the code half re-verified here:

- `automatic-review/standards/bot-participation-contract.md:115` already carries a section
  **"Evidence for a bot that edits one comment in place"**, and `:121` already specifies participation as
  **first presence OR observed `updated_at` movement**. The append-model assumption is *already rejected*.
- The contract likewise already rejects the check-state proxy — *"a check conclusion reports that the
  bot's INTEGRATION finished, which a refusal also satisfies"* — and specifies per-bot publish shapes.
- ⭐ **But `automatic-review/scripts/review_completeness.py` has NO TIMESTAMP LOGIC.** It consumes
  `--participated-bots`, and the *determination* happens upstream, guided by contract **PROSE**.

  ⚠ **PRECISION CORRECTION, 2026-08-08 — the original wording of this bullet has gone stale and would
  now read as REFUTED by the very check it names.** It said *"contains ZERO occurrences of `created_at`
  or `updated_at` (`grep -c` returns 0)"*. **That grep now returns 1**: `#1118` added a single
  occurrence at `:221`, and it is a **docstring line** (*"`updated_at` has not moved, so the review it
  proves predates this HEAD"*), not logic. ⇒ **The substantive claim is UNCHANGED and still holds — no
  timestamp is computed here — but a re-verifier running the literal grep would get a non-zero count and
  wrongly conclude the premise was refuted.**

  ⭐ **This is the epic's own theme aimed at this spec: a claim stated as a COUNT over a file, when what
  was meant was a claim about BEHAVIOUR.** The count was true when written and is a hostage to any later
  edit; the behavioural claim survives. **Verify by reading the parse and the decision path, never by
  re-running the count.** Where this plan makes its own residual/absence claims, state the predicate and
  the scope searched — do not ship a bare number.

⇒ ⛔ **The in-place-edit rule and the check-state rule are enforced by PROSE, not by CODE.** An agent
reads a doc and decides participation; on these runs it decided wrongly. **Changing a key changes nothing
if no code reads a key.** Aim the fix at making the contract **executable**, not at authoring another
rule — otherwise the same false negative recurs against the next bot that edits in place.
⚠ Same shape as the inbox `append-only` invariant a sibling epic already records as *"enforced by PROSE
ONLY, and was breached once."*

⚠ **Not re-derived here** (the forwarding epic's first-party account of their own runs): the rate-limit
window escalation, the `force-done` count, commit `9865794`, the check-run inference site, and the claim
that PR-Agent had genuinely reviewed the current HEAD. **Re-derive before scoping.**

## ⭐⭐ A THIRD site, INSIDE this plan's own function — and the fix is 290 lines above it (`#1068`, 2026-07-30)

Orchestrator-verified first-party against `#1068` and the source. ⛔ **This is a PORT, not an invention:
the same file already contains the correct predicate.**

**The defect** — `cmd_fetch_findings` (`github_pr.py:514`), "Pre-filter 5: cross-iteration dedup":

```python
if (bot_kind or '', comment_id) in existing_comment_keys:
    skipped_duplicate += 1
    continue
```

⛔ **Keyed on `(bot_kind, comment_id)` ALONE — no content or timestamp term.** pr-agent edits **one
persistent Guide comment in place**, so its id never changes: an updated review is dropped as a
duplicate.

**The correct predicate, in the SAME FILE at `:486`** — `_has_update_movement`, whose docstring already
states the rule and the fail-closed direction:

```python
if (bot_kind, comment_id) not in existing_keys:
    return True
updated_at = str(comment.get('updated_at') or '')
created_at = str(comment.get('created_at') or '')
return bool(updated_at) and updated_at != created_at
```

⇒ **Two predicates about the same question live ~290 lines apart; one was taught the lesson and the
other was not.** Identical shape to PLAN-PR-001 (whose model sits one file over) — ⭐ **that makes this
the THIRD instance of one root cause, and the second where the fix already exists nearby.**

**Live evidence, `#1068`** (`issues/1068/comments`): `cuioss-review-bot[bot]` comment `id 5132764006`,
`created_at` **15:19:30Z**, `updated_at` **17:11:25Z** — moved by ~1h52m, body opening
`## PR Reviewer Guide 🔍 #### (Review updated until commit …)`. The operator's `/review` at 17:09:55Z
produced that update ~90 s later, **under the same comment id**.

- ⚠ **Precision on "silently": it is COUNTED but MISLABELLED, not uncounted.** `skipped_duplicate += 1`
  fires, and a reader of that counter concludes *correct dedup*. ⭐ **This is useful** — the counter is an
  existing observable that a test can assert against, so D3's regression does not need new instrumentation.
- ⛔ **The archetype, again: the widening that caused it was itself a fix.** The in-source comment records
  it — *"Dropping the earlier `not thread_id` restriction closes the same phantom loop for thread-bearing
  bot comments"*. Closing a phantom-re-surface loop is what pulled thread-less comments (pr-agent's Guide
  is exactly that) into a dedup that cannot see an edit. **A fix that reproduced the defect's family —
  n≥7 in this epic.**
- ⭐⭐ **The dedup key is wrong in BOTH directions, for opposite reasons — this is the framing to keep.**
  Our own `post_responses` replies post with a **NEW id every turn**, so the dedup *cannot* fire and a
  start-anchored body filter had to be added (`:286-294`) to stop re-ingesting our own replies. pr-agent
  reuses **ONE id forever**, so the dedup *over*-fires and drops real content. ⇒ **`comment_id` alone is
  not an identity for "have I seen this review" in either direction.** Any fix must state what the
  identity actually is.
- ⛔ **CORRECTION to PLAN-PR-001's derivation seam — carry this across.** That plan's D4 enumerates
  *"every `poll_until` caller"*. **Neither `_has_update_movement` nor this dedup is on the await path**,
  so that enumeration would MISS both. ⇒ The population is **"every site that decides whether a comment
  represents NEW INFORMATION"**, not "detectors reachable from the await". Three members known:
  `cmd_pr_wait_for_comments`'s completion predicate (broken), `_has_update_movement` (correct — the
  model), and this dedup (broken).

## ⭐ A FOURTH proxy: inline comments are not the review population (`#1065`, inbox `truthful-signals-008` item 3)

Actionable findings appear in the **review BODY**, where no diff-range anchor exists to attach them —
so an ingestion that walks inline comments alone silently under-collects.

⇒ **Add to the proxy table above**: *"inline-comment enumeration"* → **a body-only finding is invisible**.
Same root cause as the other three: the population is taken from a convenient projection rather than from
the bot's own artifacts.

⚠ **Provenance is honest and worth preserving**: the originating plan's landing note flagged this as
*"may belong to the sibling `review-apparatus` epic"* and stated plainly that **the plan performed no
classification** — so the routing here is the forwarding epic's judgement, not the plan's claim. ⛔ Not
re-derived by this epic; treat the mechanics as a lead and confirm at D1 which enumeration
`fetch_findings` actually walks.

⭐ **Corroborating evidence already in hand**: on `#1066` the `ci pr comments` view returns **8** items
where the `pulls/1066/comments` inline endpoint returns only **3** — the remaining 5 are body/thread-level.
**That gap is this defect, measured**, and it is the same PR whose Major finding merged unresolved.

## Claim Labels

- OBSERVED (recorded live during PLAN-114's finalize): the dedup emptied `participated_bots` and the
  barrier returned `pr-agent: absent` while the store showed `pr-agent:issue_comment` with
  reviewed sha == HEAD.
- OBSERVED (PR #1056): pr-agent reviewed at 15:07, filed as finding `7e3f74`, and read `absent` on
  loop-back iteration 2.
- OBSERVED: the ledger already carries `bot_kind` and `reviewed_commit_sha` — these are the fields
  the monotonic derivation needs, so D2 requires no new persisted field.
- ⭐ OBSERVED (record as a PAIR, not two incidents): this is the **polarity inverse of `#1026`**, where
  a *detected refusal* was reported as a clean review. **Both directions of the participation signal
  have now been observed lying.**
- ⛔ OBSERVED (why this outranks its size): on the #1056 run the operator took a merge-anyway decision
  for a genuinely rate-limited CodeRabbit, and pr-agent's **spurious `absent` sat in the same gate
  evaluation**. A false `absent` and a true `absent` were **indistinguishable at the moment of the
  merge decision.**
- HYPOTHESIS (message-supplied, un-re-read by either epic): Defect E's mechanism as stated —
  confirm/refute at D1 against `github_pr.py` § `fetch_findings` participation derivation
  (verify-at-outline).
- HYPOTHESIS: C and E share one fix site rather than two — confirm/refute at D1 (verify-at-outline).
  If they do not, this plan splits rather than growing.
- Verify-first clause: re-ground every symbol at HEAD. `_github_pr.py` and `github_pr.py` changed
  repeatedly on the day these defects were filed; line numbers are navigational only.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_pr.py`
  — `fetch_findings` and its participation derivation (the `participation_requires_update` handling).
- HYPOTHESIS: `.../workflow-integration-github/scripts/_github_pr.py` — if the derivation is shared
  (verify-at-outline). ⚠ Same file as PLAN-PR-001, different function.
- OBSERVED: `.../phase-6-finalize/standards/branch-cleanup.md` — the instruction to feed the deduped
  set to the participation predicate.
- OBSERVED: `.../automatic-review/standards/bot-participation-contract.md` — the evidence taxonomy.
- OBSERVED: `test/plan-marshall/workflow-integration-github/test_pre_merge_barrier.py` and the
  `fetch_findings` tests.

## Dependencies and Sequencing

- Depends on: none.
- Overlaps with: ⚠ **PLAN-PR-001** — same file (`_github_pr.py`), different function. Sequence, do not
  pair, until both surfaces are re-verified at outline.
- Overlaps with: ⚠ **PLAN-PR-007** (Defect F) also reads
  `bot-participation-contract.md`. F is a *naming* defect that **survives this plan's remedy**; this
  plan produces or preserves a CREDIT. Do not let either absorb the other.
- Overlaps with: ⚠ **PLAN-PR-008** (barrier deadlock) edits `branch-cleanup.md`. Sequence.
- Adjacent to: the retired `responded_bots` work in `truthful-signals` PLAN-92 (shipped, #1041) —
  read its landing first rather than re-deriving why that union was retired.

## ⛔⛔ ABSORBED 2026-08-08 — an unmatched refusal notice is ingested as an ordinary review AND CREDITS THE BOT

Sources: `truthful-signals-020` items 22 + 23; `lessons-handling-26-08-08-01-001` (cluster C05)
lesson `2026-07-28-19-002`. ⛔ **LEADS, NOT FACTS** — first-party to their reporters, re-derived by
nobody here.

**Item 23 — the credit path.** A CodeRabbit OSS rate-limit refusal whose wording matches no registered
`refusal_pattern` is not classified as a refusal at all: it falls through to the ordinary
review-comment path and **the bot is credited as a participant**. The refusal was *published*, it was
*read*, and it *still produced a participation credit* — which is this plan's exact defect shape
arriving from the classification side rather than the view side.

⇒ **The registered pattern list is unverifiable prose and drifts silently whenever a vendor rewords
its notice.** A pattern that no longer matches degrades to a false credit with no signal. The suggested
durable guard, adopted here: **a fixture asserting that each registered bot's known refusal wordings
classify as refusals** — a population-derived check over the registry, not a hand-list. Per the epic's
standing rule, that fixture MUST publish the population size it ranged over; a check that can pass
over an empty pattern set is the vacuous-guard archetype again.

**Item 22 — why the credit is expensive here specifically.** A CodeRabbit refusal **permanently
consumes the commit range it refused**: the incremental bookkeeping marks the range *reviewed* when it
DECLINES it, and the documented recovery (wait, re-trigger) is refused with "does not re-review already
reviewed commits". There is no caller-reachable un-mark. ⇒ **a rate limit is coverage LOST, not
coverage DEFERRED, and waiting makes it permanent.** Worst observed shape: the refused range contained
the fixes for that same bot's own earlier findings. This pairs with item 23 as one incident at two
layers — the run both lost the coverage and recorded it as obtained.

**Lesson `2026-07-28-19-002` (C05)** states the same rule this plan already holds and is folded here as
corroboration, not new scope: participation must be derived from review CONTENT; a bot review can
arrive AFTER the merge, so the bot's own status prose and the finalize-time comment snapshot are both
non-oracles.

- HYPOTHESIS (verify-at-outline): that an unmatched refusal reaches the participation credit in OUR
  classifier. Confirm/refute artifact: the `refusal_patterns` match site in `fetch_findings` and the
  `refused_bots[]` / `participated_bots[]` split — `bot-participation-contract.md` § "Counted as
  participation? **No**" states the intended contract, so the question is whether the *match* holds,
  not whether the *rule* exists. ⛔ Read the matcher, not the contract prose: the contract is what this
  finding claims the code fails to implement.
- HYPOTHESIS (verify-at-outline, item 22): that CodeRabbit's range-consumption behaviour reproduces
  against our repo. If it does, note that it is a VENDOR behaviour with no caller-side remedy — the
  deliverable is honest accounting of lost coverage, never a retry loop.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/review-apparatus/plans/PLAN-PR-005-participation-derived-from-a-lossy-view.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/local/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-marshall-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
