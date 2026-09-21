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

# Participation is inferred from proxies rather than read from the bot's own artifacts, so a proven reviewer reads as absent

**Epic:** review-apparatus
**Branch prefix:** fix

## Problem

Two observed false negatives on participation, both from reading a **lossy projection** rather than the
durable ledger:

- **A storage dedup empties the set the barrier is fed.** `fetch_findings` deduped a bot's
  already-stored comment, which emptied `participated_bots` — and `branch-cleanup.md` instructs the
  caller to feed **exactly that set** to the participation predicate ⇒ verdict `absent`. Observed live
  during a finalize where it **would have falsely blocked a legitimate merge**; the run re-derived
  participation from the store and recorded the discrepancy rather than laundering it.
- **Proven participation is not re-credited across FIND calls.** Participation is derived from the
  *current call's* comment scan, so a bot whose review carries no fresh timestamp movement since the
  previous call reads `absent` on the next one. On one PR a bot genuinely reviewed, was filed as a
  finding with its reviewed SHA, and **read `absent` on loop-back iteration 2.** Nothing about its
  participation changed — **the signal moved because the query moved.**

⛔ **A dedup intended for storage hygiene must never be the input to a participation predicate.**

**The generalised mechanism, which is the real title of this plan:**

> ⛔ **Participation is inferred from PROXIES rather than read from the bot's own artifacts.**

| Proxy relied on | Failure it produces |
|---|---|
| comment `created_at` | **false negative** for a bot that edits one comment in place |
| `comments_found: 0` | a rate-limited bot is indistinguishable from a clean review |
| **check-run presence** | a bot that reviews *without* publishing a check is indistinguishable from one that never ran — and the wait loop polls for a signal that can never arrive |
| **inline-comment enumeration** | a finding in the review **body**, where no diff-range anchor exists, is invisible |

⭐ **The last row is measured**: on one PR the comments view returns **8** items where the inline
endpoint returns only **3** — the remaining five are body- or thread-level. **That gap is this defect,
quantified**, and it is the same PR whose Major finding merged unresolved.

## ⛔ The reframing that must not be missed: the contract already says all of this

- `bot-participation-contract.md` already carries a section **"Evidence for a bot that edits one comment
  in place"** and already specifies participation as **first presence OR observed timestamp movement**.
  The append-model assumption is *already rejected* in prose.
- The contract likewise already rejects the check-state proxy — *"a check conclusion reports that the
  bot's INTEGRATION finished, which a refusal also satisfies"* — and specifies per-bot publish shapes.
- ⭐ **But the completeness script computes no timestamp at all.** It consumes a `--participated-bots`
  argument, and the *determination* happens upstream, guided by contract **prose**.

⇒ ⛔ **The in-place-edit rule and the check-state rule are enforced by PROSE, not by CODE.** An agent
reads a doc and decides participation; on these runs it decided wrongly. **Changing a key changes
nothing if no code reads a key.** ⇒ **Aim the fix at making the contract executable**, not at authoring
another rule — otherwise the same false negative recurs against the next bot that edits in place.

## Goal

Participation is read from the bot's own artifacts and from the durable ledger, survives a re-query at a
fixed head SHA, and is decided by code rather than by a reader's interpretation of a standards document.

## Deliverables

Four.

1. **D0 — GATE, mutates nothing: re-establish both defects at HEAD and derive the consumer population.**
   ⚠ **The second defect arrived as a forwarded message that neither originating epic had independently
   re-read — it is a LEAD, not a fact.** Re-establish it against the source before scoping.
   Enumerate every consumer of `participated_bots` (or its successor) and classify each by whether it
   reads **the scan**, **the ledger**, or **a deduped projection**. The two defects are a **sample of
   the shape, not its extent**.
   ⛔⛔ **A live ordering constraint the enumeration must carry.** `participation_evidence(bot)[0]` — the
   **first element of a list** — is consumed as a bot's synthesized publish shape by **seven
   registry-derived consumers**, and a test asserts on it. A recent change had to *append* a new evidence
   kind rather than insert it, because reordering would have silently re-pointed all seven **with no
   test failing.** ⇒ **Classify each consumer by whether it reads the LIST or the FIRST ELEMENT**, and
   make sure the decoupling in D2 covers the **ordering** dependency, not only the dedup one.
   ⛔ **This deliverable HALTS the plan** if the consumer population cannot be derived.
   *Done when:* both defects are re-established or refuted at HEAD, and the consumer population is
   published with each member classified.

2. **D1 — participation is monotonic within a finalize run for a fixed head SHA.** Once a bot's review is
   observed and filed for a given reviewed SHA, later `fetch_findings` calls **for that same head SHA**
   report it as participating regardless of timestamp movement. Derive from **the ledger union with the
   current scan**, not the scan alone — the ledger already carries the bot kind and the reviewed SHA, so
   this needs **no new persisted field**. **Reset only when the head SHA advances.**
   ⭐ **Read participation from the bot's own artifacts** — review comments and review submissions —
   reserve check-run state for bots that genuinely publish one, and record per-bot trigger semantics
   explicitly (`auto_on_push` versus `requires_explicit_trigger`, with the trigger command for the
   latter). ⭐ **For a bot needing an explicit trigger, POST the trigger** rather than waiting for a
   spontaneous pass that cannot come.
   *Done when:* a bot proven on call 1 is still credited on call 2 at an unchanged head SHA, and
   advancing the SHA resets the credit.

3. **D2 — the storage dedup is decoupled from the participation predicate.** The predicate's input is the
   durable record, so a hygiene change to storage cannot silently change a merge verdict.
   **The defect, verified in source:** the cross-iteration dedup is keyed on `(bot_kind, comment_id)`
   **alone — no content or timestamp term.** A bot that edits **one persistent comment in place** never
   changes its id, so an *updated* review is dropped as a duplicate.
   ⭐⭐ **The dedup key is wrong in BOTH directions, for opposite reasons — this is the framing to keep.**
   Our own posted replies get a **new id every turn**, so the dedup *cannot* fire and a start-anchored
   body filter had to be added to stop re-ingesting our own replies. The other bot reuses **one id
   forever**, so the dedup *over*-fires and drops real content. ⇒ **`comment_id` alone is not an identity
   for "have I seen this review" in either direction.** ⛔ **Any fix must state what the identity actually
   is.**
   ⚠ **Precision on "silently": the drop is COUNTED but MISLABELLED, not uncounted.** A
   `skipped_duplicate` counter fires, and a reader of that counter concludes *correct dedup*. ⭐ **Useful
   — it is an existing observable a test can assert against**, so the regression needs no new
   instrumentation.
   *Done when:* the participation predicate's input no longer passes through the storage dedup, and the
   identity used for "seen this review" is stated explicitly.

4. **D3 — tests, each verified to FAIL pre-fix.** (a) A bot whose comment was deduped on storage is
   still credited as participating. (b) A bot proven on FIND call 1 is still credited on call 2 with no
   timestamp movement and an unchanged head SHA. (c) Advancing the head SHA **does** reset the credit.
   (d) The consumer population is derived, non-empty-asserted, and every known member covered.
   ⭐ Add a **population-derived refusal fixture**: assert that each registered bot's known refusal
   wordings classify as refusals. ⛔ Not a hand-list — **the fixture must publish the population size it
   ranged over**; a check that can pass over an empty pattern set is the vacuous-guard archetype again.

## ⛔⛔ A cross-plan collision this plan MUST resolve before porting anything

Prior analysis identified `_has_update_movement`, ~290 lines from the broken dedup **in the same file**,
as *"the correct predicate"* and proposed porting it — on the grounds that two predicates about the same
question live near each other and only one was taught the lesson.

⛔ **Do not port it blind.** A separate plan in this epic has since established, first-party, that
`_has_update_movement` is a **two-arm** predicate whose first arm — *first presence in the plan's
accumulated observation ledger* — is **consumed by the first fetch**, so it **flips a verdict from
proven to unproven at an unchanged HEAD** and **consults no commit SHA at all.**

⇒ **It is more correct than the dedup and still not HEAD-anchored.** Porting it would spread a
non-idempotent predicate to a second site immediately before the other plan replaces it.

⚠ **Resolve this explicitly at D0** and state the resolution in the report. The likely correct answer is
to port the *shape* (a review's identity is not its comment id) while taking the **SHA-anchored**
predicate the currency plan is building, rather than the observation-ledger one. **If that plan has not
landed, say so and record which predicate was adopted and why.**

## Out of scope

- **Authoring another prose rule.** The contract already states the rule; the defect is **enforcement**.
  A deliverable that adds a paragraph reproduces the defect.
- **A retry loop against a vendor's range-consumption behaviour.** A refusal from one bot **permanently
  consumes the commit range it refused** — the incremental bookkeeping marks the range *reviewed* when it
  **declines** it, and the documented recovery is refused with *"does not re-review already reviewed
  commits"*. There is no caller-reachable un-mark. ⇒ **A rate limit is coverage LOST, not coverage
  DEFERRED, and waiting makes it permanent.** ⛔ The deliverable is **honest accounting of lost
  coverage**, never a retry loop.
- **Absorbing the naming defect** that a shipped sibling plan owns. It **survives this plan's remedy**;
  this plan produces or preserves a **credit**. Neither absorbs the other.
- **Re-deriving why an earlier `responded_bots` union was retired.** Read that landing rather than
  rediscovering it.

## Expected surface

- `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_pr.py` —
  `fetch_findings`, its participation derivation, and the cross-iteration dedup.
- `.../workflow-integration-github/scripts/_github_pr.py` — if the derivation is shared. ⚠ Same file as
  another staged plan, different function.
- `.../phase-6-finalize/standards/branch-cleanup.md` — the instruction to feed the deduped set to the
  participation predicate.
- `.../automatic-review/standards/bot-participation-contract.md` — the evidence taxonomy.
- `test/plan-marshall/workflow-integration-github/test_pre_merge_barrier.py` and the `fetch_findings`
  tests.

## Claim labels

| Claim | Label | Confirm/refute artifact |
|---|---|---|
| The dedup emptied `participated_bots` and the barrier returned `absent` while the store showed the bot with reviewed SHA == HEAD | OBSERVED — recorded live during a finalize | Restated here; the decision log is machine-local |
| The cross-iteration dedup is keyed on `(bot_kind, comment_id)` alone, with no content or timestamp term | OBSERVED | The dedup predicate in `fetch_findings` — read it directly |
| A bot's persistent comment moved its timestamp by ~1h52m under **the same comment id** after an explicit trigger | OBSERVED | Restated here. ⚠ **Re-derive the shape against a live PR rather than trusting the figures** |
| The ledger already carries the bot kind and the reviewed SHA | OBSERVED | The finding record schema — so D1 requires no new persisted field |
| The completeness script computes no timestamp; the determination happens upstream, guided by prose | OBSERVED — **with a correction that matters** | ⛔ **Verify by reading the parse and the decision path, NEVER by re-running a grep count.** An earlier form of this claim was stated as *"zero occurrences of `created_at`/`updated_at`"*; a later change added **one** occurrence, and it is a **docstring line**, not logic. **The behavioural claim is unchanged and still holds** — but a re-verifier running the literal count would get a non-zero result and wrongly conclude the premise was refuted. ⭐ **This is the epic's own theme aimed at this plan: a claim stated as a COUNT when what was meant was a claim about BEHAVIOUR.** Where this plan makes its own absence claims, **state the predicate and the scope searched — never ship a bare number** |
| `participation_evidence(bot)[0]` is consumed as a semantic field by seven registry-derived consumers | OBSERVED | The consumers and the test that asserts on the first element |
| The second defect's mechanism as stated | HYPOTHESIS — forwarded, un-re-read by either epic | `fetch_findings`'s participation derivation |
| The two defects share one fix site rather than two | HYPOTHESIS | D0. ⛔ **If they do not, this plan SPLITS rather than growing** |
| An unmatched refusal notice reaches the participation credit in our classifier | HYPOTHESIS — a lead | The refusal-pattern match site and the refused-versus-participated split. ⛔ **Read the MATCHER, not the contract prose** — the contract states the intended rule, and this finding claims the code fails to implement it |
| Inline-comment enumeration under-collects body-level findings | HYPOTHESIS — routed by another epic's judgement, **not classified by the reporting plan itself** | Confirm which enumeration `fetch_findings` actually walks |

⛔ **Re-ground every symbol at HEAD.** The two provider files changed repeatedly on the days these
defects were filed; **line numbers here are navigational only.**

⛔ **Do not go looking for `.plan/`.** The decision logs, inbox messages, and lesson records behind this
plan are git-ignored and **absent from your clone**. Everything needed is restated here.

## Verification

- Full verify; read the payload's `status` / `errors[]`, not the exit code.
- **Every D3 case proven discriminating by mutation.** Case (c) — the SHA advance *does* reset the
  credit — is the one a monotonicity fix most easily breaks, and breaking it converts this plan into the
  false-positive defect another plan in this epic exists to close.
- **Assert against the existing `skipped_duplicate` counter** rather than adding instrumentation.
- **Publish the consumer population and the refusal-pattern population sizes** in the run report.
- ⭐ **Cold read, aimed at the executable contract.** This plan's central claim is that a rule enforced
  by prose is not enforced. Have the pre-PR verification sub-agent read the changed code **cold** and
  answer: *what makes a bot count as having participated, and where is that decided?* If the honest
  answer is still *"a reader applies the standards document"*, the plan has not moved the enforcement
  and should say so rather than claiming the goal.

## Notes

- ⭐ **Record as a PAIR, not as two incidents.** This is the **polarity inverse** of an earlier case
  where a *detected refusal* was reported as a clean review. **Both directions of the participation
  signal have now been observed lying.**
- ⛔ **Why this outranks its size.** On one run the operator took a merge-anyway decision for a genuinely
  rate-limited reviewer, and a **spurious** `absent` for a different bot sat in the same gate
  evaluation. **A false `absent` and a true `absent` were indistinguishable at the moment of the merge
  decision.**
- ⛔ **The archetype, again: the widening that caused the dedup defect was itself a fix.** The in-source
  comment records it — dropping an earlier restriction *"closes the same phantom loop for thread-bearing
  bot comments"*. Closing a phantom-re-surface loop is what pulled thread-less comments into a dedup
  that cannot see an edit. **A fix that reproduced the defect's family — the seventh in this epic.**
- ⛔ **A correction to a sibling plan's derivation seam, worth carrying across.** That plan enumerates
  *"every await-loop caller"*. **Neither the movement predicate nor this dedup is on the await path**, so
  that enumeration would **miss both**. ⇒ The population is **"every site that decides whether a comment
  represents NEW INFORMATION"**, not "detectors reachable from the await". Three members are known: the
  wait completion predicate, the movement predicate, and this dedup.
- **The registered refusal-pattern list is unverifiable prose and drifts silently whenever a vendor
  rewords its notice.** A pattern that no longer matches degrades to a **false credit with no signal** —
  which is why D3's fixture is population-derived rather than a hand-list.
- **Sequencing.** Overlaps other staged plans in this epic on the same provider file (different
  functions) and on `branch-cleanup.md`. ⛔ **Sequence, never pair**, and see the cross-plan collision
  section above before porting any predicate.
