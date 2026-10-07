# Decisions archive — `review-apparatus`

epic: review-apparatus

> ⛔ **RELOCATED, NEVER DELETED.** This file holds the chronological decision narrative and the
> resolved/retired entries that were moved out of `epic.md` on 2026-07-30 so the live ledger states
> only what a fresh session must ACT on. **Nothing here was rewritten** — the blocks below are verbatim
> slices of the prior `epic.md`.
>
> **Where the authority now lives:**
>
> | Content | Home |
> |---|---|
> | Machine state (queue, statuses, anchor) | `status.json` — the sole authority |
> | Rules for review runs | `review-practice.md` — the single source of truth |
> | Per-plan evidence, prohibitions, claim labels | each `plans/PLAN-PR-NNN-*.md` (specs are self-sufficient by contract) |
> | Per-run findings | `findings/` |
> | Full audit trail | `logs/decision.log` and `inbox/archive/` — ⛔ **append-only, never pruned** |
>
> ⚠ **A retired entry is not a refuted one.** Items here were retired because they were resolved,
> superseded, or absorbed into a spec — not because they were wrong. Read the reason on each.

---

## Chronological decisions (2026-07-29 → 2026-07-30)

- 2026-07-29 — **Epic created by operator instruction, overriding an orchestrator recommendation
  not to.** The recommendation was that `truthful-signals` already owns this work (PLAN-115 launched,
  PLAN-116 and PLAN-119 staged) and a second epic would duplicate an owner. The operator's grounds
  for overriding: (a) the surfaces DO separate once the already-running plan is left alone, and
  (b) durability — this work had been carried in chat context, which is materially less durable than
  an orchestrator ledger and had already lost the thread once in a single day. Grounds (b) is the
  decisive one and is not addressed by the recommendation.
- 2026-07-29 — **SUPERSEDED (same day, by the rule below): id band PLAN-400..PLAN-499.** Recorded and
  then replaced before any plan was staged under it, so no artifact carries a 4xx id. Kept visible
  rather than deleted so a reader who saw the band in an early inbox message can find its retraction.
- 2026-07-29 — **Plan id scheme: `PLAN-PR-NNN`, sequence starting at `001`, applying to EVERY plan in
  this epic — created or transferred.** Operator instruction. Spec files are
  `plans/PLAN-PR-NNN-{descriptive-slug}.md`.

  This is strictly better than a numeric band: it makes collision with the other two epics impossible
  by construction rather than by a reserved range that has to be remembered and honoured, and it ends
  the inherited-carve-out problem outright — a transferred item is re-issued here at the next `PR`
  sequence number instead of dragging a foreign id into this ledger.

  Both halves verified live against the executor, not read from a doc:

  - `orchestrator queue --transition PLAN-PR-001` reaches `plan_not_found` rather than a format
    rejection, so the queue verb accepts the form despite its `PLAN-NN` metavar;
  - `orchestrator inbox detect --source-id .plan/local/orchestrator/review-apparatus/plans/PLAN-PR-001-example.md`
    returns `orchestrated: true`, `detection: orchestrated`.

  ⚠ **The `PR` token must be UPPERCASE.** The detect grammar accepts `PLAN-{SLUG}-{DIGITS}` where
  `{SLUG}` is 2–8 uppercase alphanumerics; a lowercase `plan-pr-001-…` falls outside the grammar and
  would classify as `unrecognised_id`, silently detaching the plan from this epic. Digits are mandatory
  and zero-padded to three.

  ⚠ **The cached skill does not document this form.** The `marshall-orchestrator` SKILL.md loaded from
  plugin cache `0.1.1240` describes only `PLAN-NN-*` for `inbox detect`; the source bundle documents all
  three forms and the four-token `detection` vocabulary. The form works — that is why it was verified
  against the executor rather than trusted from either doc.
- 2026-07-29 — **`parallelization_scope` = 1 (strictly sequential).** This epic's plans concentrate on
  a narrow, mutually overlapping surface (`bot_registry.py`, `review_completeness.py`, `_github_pr.py`,
  the pre-merge barrier). N>1 would force holds more often than it would gain throughput. Revisit if
  org-repo config work (disjoint by construction from every plan-marshall file) becomes a steady second
  stream.
- 2026-07-29 — **PLAN-115 stays with `truthful-signals`.** Operator instruction: a launched plan is not
  moved. Consequence to respect at decompose: PLAN-115 owns `tools-integration-ci` plan-less-PR work,
  so anything staged here that touches that seam is sequenced behind its landing, not paired with it.
- 2026-07-29 — **Cross-epic moves go through the inbox, never by direct edit.** Adopting PLAN-116 and
  PLAN-119 requires mutating `truthful-signals`' `status.json`, which is outside this epic's
  direct-file-write carve-out. The request is filed as an inbox message to that epic and applied by its
  orchestrator; rows are staged here only once released. Until then they remain THEIRS and must not be
  double-staged. Under the `PLAN-PR-NNN` rule a released item is **re-issued at the next `PR` sequence
  number**, not carried across at its old id — nothing is renamed, because a staged item has no plan
  artifact to rename, only a spec to write here.
- 2026-07-29 — **Reference knowledge for the two central config repos captured at init** in
  `reference-config-repos.md` + `references.json`, so no plan re-derives it. Both configs are
  self-documenting: every setting carries its rationale and the evidence that produced it. ⚠ The
  `coderabbit` checkout was found on an unmerged, FALSIFIED branch (PR #4) rather than main — live config
  is `origin/main` at `46cd5f7`. Confirm the branch before reading either config as live.
- 2026-07-29 — **Workstreams cut on OWNERSHIP LAYER, not on defect type.** WS-01 await-and-participation
  detection (plan-marshall consumer side), WS-02 org-workflow-gates (`cuioss-organization`), WS-03
  review-signal-efficacy (the two config repos plus the ingestion standards consuming their output).
  The layer shape is deliberate: the three repos sit on **different release cadences**, and that
  difference is the real constraint. WS-02 alone fans out to ~21 consumer repos through an org
  release tag, while both config repos take effect on the next review with no release step. A cut
  by defect type would have put a same-day change and a 21-repo release in one workstream.
- 2026-07-29 — **Queue ordered by LIVE BLEED, not by id or workstream:** PR-001 → PR-003 → PR-002 →
  PR-004. PR-001 burns the full 600 s await plus an operator escalation on *every* loop-back right
  now. PR-003 is second because if its contradiction resolves to EXTRACT, CodeRabbit finding
  extraction has been silently degraded on every review since `a97b64f`. PR-002 has no current
  bleed — it blocks a *future* `handle_push_trigger` enablement. PR-004 is measurement only.
  ⚠ **`status.json` `plans[]` ARRAY order is the queue order** — id numbering carries no ordering
  authority. The array was reordered to match this decision after the generated START-HERE block was
  read back and showed `next` would otherwise have emitted PR-002 second.
- 2026-07-29 — **Split guard: no splits owed.** All four specs carry 3–4 deliverables, under the ~6
  presumptive threshold. PLAN-PR-001's narrowness is a separate deliberate choice: it claims ONE
  function (`cmd_pr_wait_for_comments`) rather than the `_github_pr.py` detector surface generally,
  so it need not be serialized against `truthful-signals` PLAN-116, which declares that file as its
  core. Boundary declared to that epic as `review-apparatus-003`; **non-blocking** — PR-001 proceeds
  unless they reply that PLAN-116 already rewrites that predicate.
- 2026-07-29 — **Re-derived at decompose, from live state rather than from the anchor's prose.**
  Handovers `review-apparatus-001` / `-002` are STILL QUEUED in `truthful-signals`' inbox and its
  queue shows PLAN-116 and PLAN-119 both `staged` — so they remain THEIRS and were **not**
  double-staged here. PLAN-115 is `launched`, not landed; consequence respected by staging nothing
  that touches `tools-integration-ci`, so **no plan in this epic sequences behind it**.

- 2026-07-30 — ⭐ **This epic is now the OWNER of the automated-PR-review apparatus; `truthful-signals`
  becomes a DISPATCHER for the theme.** Standing operator instruction relayed in `truthful-signals-001`:
  *"All findings AND landings of PR-related work land in `review-apparatus` from now on."* Five plans
  released (three more than requested). Consequence: this epic must be able to absorb a landing, which is
  why `PLAN-PR-010` (the landing message carries no outcome) is ranked 3rd — until it lands, the sibling
  attaches every forwarded outcome by hand.
- 2026-07-30 — **PLAN-116 SPLIT into five, and two slices already existed here.** ⚠ Its Defect A *was*
  `PLAN-PR-001` and its Defect B *was* `PLAN-PR-002`, both staged hours earlier at decompose. **Neither
  the handover summary nor our own narrow-claim message surfaced this — it was found only by reading the
  source spec.** Accepting PLAN-116 at its stated scope would have staged both defects twice. The
  standing lesson: a handover summary is a lead; the released SPEC is the artifact.
- 2026-07-30 — **Taking all five post-merge revisits** (`#1055`, `#1057`, `#1058`, `#1059`, `#1061`).
  Operator decision. Splitting one PR out of a batch of five was worse than either whole, and post-merge
  review coverage is this epic's subject. `truthful-signals` drops its standing rule for PR-related PRs.
- 2026-07-30 — **PLAN-60 split; build-gate half RETURNED to `truthful-signals`.** Operator decision. Only
  the review half is staged (`PLAN-PR-011`: completeness-guard absent-vs-in-progress, the
  simplify ↔ automatic-review same-run contract, and the review-versus-gate delta as a measurement).
  ⛔ The returned half — ruff `select=`, `mypy test` parity, gate footprint scoping — must NOT be
  re-absorbed here. **The ten bound lessons split with the deliverables**; `PLAN-PR-011` carries exactly
  two (`2026-07-21-10-002`, `2026-07-17-09-001`).
- 2026-07-30 — **WS-04 created** (merge barrier and landing channel). The three re-issued finalize-side
  plans CONSUME a review verdict rather than produce one, which is WS-01's charter. Cutting them into
  WS-01 would have made that charter meaningless.
- 2026-07-30 — **Convention adopted: a deferral conditioned on another epic's PR must NAME the PR.**
  Raised by `code-intelligence-substrate`, extended to us by `truthful-signals`. ⚠ **With one caveat we
  added back:** naming the PR makes a deferral expirable but only helps if something re-reads the name —
  PLAN-100's blocker named PLAN-92, PLAN-92 shipped as `#1041`, and the blocker still sat there. Our
  practice is to re-derive every cross-epic blocker against the sibling's LIVE queue at drain time, never
  from the note.
- 2026-07-30 — **The cached orchestration standard misled us on the read boundary, and the source
  settled it.** Cache `0.1.1240` says other epics' trees are out of bounds for Read; the source bundle
  (post-`#1040`, `orchestrator-read-boundary-self-contradiction`) states **reads are unrestricted in
  location** and the write carve-out governs writes only. Reading the five released specs was therefore
  sanctioned — and necessary, per the PLAN-116 finding above. ⚠ **A workflow doc read from cache can be
  silently behind its source**; this is the second time that gap has had a live consequence.

- 2026-07-30 — **Review practice EXTRACTED to `review-practice.md`; `epic.md` and `findings/README.md`
  are now pointers.** The trigger was **duplication, not size**: the per-bot verdict rules had already
  been written into two files, which is the source-of-truth-duplication archetype `PLAN-PR-003` exists
  to fix elsewhere — worth fixing in our own tree first. Kept in the epic tree rather than promoted to
  the marketplace, because a bundle edit is repository source and therefore plan work, never an
  orchestrator edit. ⚠ **Promotion candidate recorded WITH a trigger**: the practice is project-general
  rather than epic-specific, but it changed three times on its first day, and promoting a churning
  contract costs a plan per correction — promote once it survives ~3 consecutive run batches unchanged.

- 2026-07-30 — **Inbox drained 4/4 (not 3 — a message arrived mid-drain).** The anchor and an
  enumeration taken minutes earlier both said 3; re-enumerating at the top of the drain returned **4**
  (`code-intelligence-substrate-002.md`, 08:08:51Z). ⭐ **This is the second time in two days that
  re-deriving `inbox list` instead of trusting a count changed the work** — the sibling epic recorded the
  same catch for out-of-order arrival. ⛔ Standing rule reaffirmed: **the drain's own enumeration is the
  work list; a count carried in prose is never authority.**

  Dispositions: `code-intelligence-substrate-001` **folded** (five-mode sample → PR-007's D1 population,
  with mode 5 explicitly excluded and mode 3 flagged as the likeliest new member);
  `code-intelligence-substrate-002` **staged** as `PLAN-PR-013`; `truthful-signals-002` **folded** (id
  rename map + the PR-011 ↔ TRUTH-019 deep collision); `truthful-signals-003` **folded** (the
  `poll_until` population question → PR-001's D4).
- 2026-07-30 — ⭐ **`PLAN-PR-013` staged: the FALSE-POSITIVE polarity, and the only plan in this epic
  that deliberately moves a merge verdict.** Every participation plan queued before it concerns a real
  review failing to be credited (worst case: a needless loop-back). PR-013 is the inverse — credit
  granted for a review of a superseded commit, worst case **an unreviewed tree merging**. Staged rather
  than folded into PR-007 precisely because PR-007's load-bearing safety property is that *no verdict
  moves*; absorbing PR-013 there would have set the two plans' safety properties against each other.
- 2026-07-30 — **Two claims in the `#1063` handover were CORRECTED against live evidence, and both
  corrections narrow the fix.** (a) "The final shipped commit was reviewed by nobody" is **false** —
  CodeRabbit *was* re-triggered by hand at 07:42:52Z and did see `2475cd17`; the true claim is
  *the REQUIRED bot never saw it*. Scoping to "nobody" would have aimed the fix at the wrong gap.
  (b) "PR #1063 is still OPEN, catchable now" was **true when written (08:08:51Z) and expired 32 minutes
  later** — it merged at 08:40:48Z. ⭐ The lesson outlives the window: **an inbox message carrying a
  closing window needs the window re-derived at drain time**, the same rule this epic already adopted for
  cross-epic blockers. The substance survived both corrections — the defect is real and now confirmed on
  merged evidence.
- 2026-07-30 — **Sibling ids renamed; provenance deliberately NOT rewritten.** `PLAN-113` →
  `PLAN-TRUTH-001`, `PLAN-52` → `PLAN-TRUTH-006`, the returned PLAN-60 build half → `PLAN-TRUTH-019`;
  `PLAN-115` keeps its id because it is launched. Only **forward-looking pointers** were updated. ⛔
  Provenance prose, `logs/`, and `inbox/archive/` still carry the old ids and MUST stay that way — those
  were the ids at transfer time, the sibling records the five numeric ids as *permanently spent with
  their rows kept*, and rewriting them would falsify the audit trail.

- 2026-07-30 — **Second drain the same day: 2 more messages, and `PLAN-PR-014` staged at the QUEUE HEAD.**
  ⛔ **Ranked ahead of PLAN-PR-001 deliberately.** PR-001 wastes 600 s per loop-back; PR-014 is a
  **false-GREEN that admits unreviewed code to a merge**, and unlike most items here its reproduction is
  *confirmed* and its fix is mechanically small. A confirmed false-green outranks a confirmed cost.
  ⚠ It is also deliberately NOT sequenced behind PR-007 or PR-008 — coupling it to PR-007's taxonomy or
  to PR-008's **operator-owed** D3 would delay a live false-green behind an unanswered question.
- 2026-07-30 — ⭐ **The `review_completeness` crash is ROOT-CAUSED at the call site, by reproduction
  rather than by inference.** `--participated-bots` supplied with no value exits 2
  (`expected one argument`), and the documented invocation interpolates it **unquoted** at
  `branch-cleanup.md:631` and `automatic-review/SKILL.md:612`. An empty participation set — the
  zero-participation case — therefore strips the flag's argument and crashes the gate, **and the calling
  step recorded `outcome: done` anyway.** ⭐ Five flags per site share the shape, so the fix is a derived
  population, not a one-line quote.
- 2026-07-30 — ⛔ **TWO distinct argparse rejections exist on that script and they are INDISTINGUISHABLE
  in the log** — both exit 2, both surface as `failure_kind=argparse_rejection`: the empty-value case
  above, and a **retired** `--enabled-bots` flag. ⇒ **The `#1063` attribution to the empty-value case is
  a HYPOTHESIS, not a fact**, recorded as such in PR-014. It is settleable only from the argv recorded in
  that plan's own log, which the orchestrator cannot read. ⚠ **A failure_kind is not a failure cause** —
  two mechanisms sharing one log signature is the same confident-signal-hides-a-caveat shape this epic is
  named after, found this time in our own diagnostic evidence.
- 2026-07-30 — ⛔ **`truthful-signals`' `--enabled-bots` diagnosis CONTRADICTED and returned as
  `review-apparatus-006`.** They folded it into their `PLAN-TRUTH-012` (canonical-block-vs-argparse
  divergence) on the grounds that the defect is the doc/script contract. **There is no such divergence in
  the source**: `--enabled-bots` appears **nowhere** in `marketplace/bundles/` for `review_completeness`,
  nor in `github_pr.py` at all. It survives only in plugin cache `0.1.1232`'s copy of the script. Their
  two subagents read a **stale cache** and invoked a retired flag — the stale-cache-as-evidence archetype,
  which has a different fix. A PLAN-TRUTH-012 deliverable aimed at it would find nothing to fix.
- 2026-07-30 — **Cache↔executor split MEASURED, and it is worse than the watch said.** The executor
  embeds **exactly one** version (`0.1.1271`), so there is no pin/orphan inversion. But skills load from
  `0.1.1240` and **32 versions coexist** in the cache root. ⇒ **What we READ is 31 versions behind what we
  RUN.** Standing rule adopted: **verify a flag surface against the executor (`--help`), never against a
  doc — cached or not.** This is the third live consequence of that gap in two days.

- 2026-07-30 — ⭐ **`#1067` analysed (`findings/PR-1067.md`): the richest single run so far, and it
  reinforced three staged plans without staging a fourth.** Reported by the operator as enqueued; it had
  **already merged** (14:41:54Z) — the second expired window today, and the second time re-deriving at
  analysis time changed what was true. Absorbed, not escalated: every apparatus finding folded into an
  existing plan, and the five *code* defects belong to the plan's own epic and were **not** claimed here.
- 2026-07-30 — ⭐ **A rate-limit window reopening recovered 5 real defects BY LUCK.** CodeRabbit's window
  reopened while the plan sat blocked on the merge mutex; the review it then gave found five genuine
  defects, one of them the plan reproducing its own target defect. ⛔ **Nothing in the apparatus waits for
  a reopening window** — had the mutex not blocked, #1067 would have merged with all five and every signal
  green. ⚠ **This does NOT reopen the retired rate-limit watch**: the operator's ruling that rate limiting
  is expected and is not a bot malfunction stands. What it establishes is that a rate-limit refusal is a
  **deferred review carrying real content**, which is the strongest evidence yet for PLAN-PR-008's
  `refused_awaitable` split naming a state where *waiting demonstrably recovers findings*.
- 2026-07-30 — ⛔ **Third sighting of the PLAN-PR-013 shape, and the sharpest: the merged tree was the
  REMEDIATION CODE, and nobody reviewed it.** Three loop-back commits fixed CodeRabbit's five findings at
  14:03–14:04; no review of any kind exists after 13:48:28Z; merged 14:41:54Z. ⭐ Remediation code is the
  highest-risk diff on a PR — written under loop-back pressure, addressing defects a reviewer just found —
  and it is *systematically* the least-reviewed, because it arrives after every bot has taken its turn.
- 2026-07-30 — **A fourth back-feed answer shape added to `review-practice.md`: "the check RAN but was too
  narrow → WIDEN it, never add a second."** Forced by the first real case (`835226`): `_detect_count_prose`
  exists and ran, but scans only `SKILL.md` and matches a closed five-noun set. Answering that with a new
  detector would give the local review two overlapping copies of one check — the duplication failure this
  epic fixes elsewhere. ⭐ **Found in passing: that detector's own comment claims `nine checks` is matched
  while `checks` is absent from its noun set** — the count-prose detector had shipped an unverified count
  claim about itself.
- 2026-07-30 — ⚠ **`#1067`'s 5 : 0 deficit is CONFOUNDED and is not scored as a clean 5 : 0.** PR-Agent
  reviewed at 11:20:37Z; the branch was rebased at ~13:10 (proven by the committer-date reset); CodeRabbit
  reviewed the post-rebase tree. **The two bots did not review the same artifact.** Recorded as a deficit
  with the confound named — comparing reviews across a rebase is exactly the error PLAN-PR-007 exists to
  make visible, and this epic must not commit it in its own scoring.

- 2026-07-30 — ⛔⛔ **SELF-CORRECTION, same day: the orchestrator asserted an absence without checking, and
  the epic's own archetype was committed in the epic's own ledger.** The `#1067` analysis recorded
  *"nothing in the apparatus waits for a reopening window."* **False.** `truthful-signals-005` named the
  knob and a `grep` settled it in one call.
  **What is actually shipped**: `automatic-review`'s opt-in `review_rate_window_await`
  (+ `review_rate_window_timeout_seconds`, default 3600, matched to CodeRabbit's ~hourly reset) — it
  claims the bot's rate window via `merge_lock rate-window claim`, paces a bounded wait on that claim's
  expiry, then **GENERATES** the trigger event (rebase-and-push; `trigger_comment` only as fallback), and
  it **already** splits `awaitable_window` / `hard_quota` / `unknown` with three distinct
  `escalate_ask` reasons.
  ⇒ **PLAN-PR-008's D2 is presumptively ALREADY SHIPPED** and is marked re-scope-or-drop-at-outline;
  implementing it as written would rebuild a shipped mechanism. D3 and D4 stand.
  ⭐ **The real finding is an ACTIVATION question**: `.plan/marshal.json:113` sets
  `"review_rate_window_await": false` (also the default), so the `#1067` recovery was luck **because the
  recovery is switched off**. Per `review-practice.md` § 3, ⛔ do not compensate for a switched-off check.
  ⚠ **PLAN-PR-008's own Claim Labels already carried "⛔ Do not assume `ask` is absent"** — the identical
  trap one mechanism over. **A warning written in the ledger did not read itself**, which is the same
  lesson `truthful-signals` recorded about their own id-freedom claim two days earlier.
- 2026-07-30 — ⭐ **The activation question has a SECOND instance, so it is a pattern, not a one-off.**
  `#1066` (PLAN-202, merged `d04ac98ed`) landed with **one-bot coverage**: only pr-agent reviewed,
  CodeRabbit refused on an **awaitable** window, Sourcery on a hard quota — and the awaitable refusal was
  never waited out, because the knob is off. **A recoverable coverage gap, left unrecovered by
  configuration.** ⇒ This is now an operator decision worth surfacing on its own: arm
  `review_rate_window_await`, or accept that awaitable refusals are never recovered. ⛔ It is NOT a
  build-something question.
- 2026-07-30 — **`PLAN-PR-010` re-scoped by its fourth confirmation.** `#1065`'s landing message asserts
  *"PR: #1065"* under a **"What landed"** heading while the PR is open. ⭐ The message does not merely
  *omit* an outcome — it **asserts a false one in prose**, so appending a correct `outcome:` field beside
  it leaves the false sentence live. **The fix must change the claim, not only add a field.**

- 2026-07-30 — ⭐ **Bot gating recorded as CONFIG, and it narrows two plans.** Operator rationale: *for
  this repo CodeRabbit is optional; it matters more on API-Sheriff, which is production code.* Verified
  rather than inferred — `.plan/marshal.json` `plan-marshall:automatic-review` declares
  `required_bots: "pr-agent"`, `optional_bots: "coderabbit,sourcery"`, `bot_lists_provenance: "answered"`
  (an answered operator question, not a seeded default).
  **Consequences**: PLAN-PR-008's D1 must **not** enumerate optional-bot refusal as a deadlock state —
  `optional_bots` is already the sanctioned acceptance of an optional bot's silence, so the deadlock is
  narrowly about **pr-agent**; and the arming trade in *this* repo buys an optional bot's review, which is
  a materially weaker case for arming than the raw `#1067` story suggests.
  ⛔⛔ **But "optional" is a GATING classification, NOT a VALUE one, and the two must never be collapsed.**
  On `#1067` the *optional* bot found **5 genuine defects** on a diff the *required* bot answered with
  none. ⭐ **On the evidence so far the optional bots' findings have mattered MORE, not less** — a future
  reader who downgrades them because of this row has misread it. Recorded in `review-practice.md` § 1,
  which now carries the gating column and the per-repo warning.

- 2026-07-30 — ⭐⭐ **ARCHETYPE NAMED: "true when written, false when read."** Four instances surfaced in
  a single day, on four different surfaces, and naming it is what stops the fifth being analysed from
  scratch:
  1. A landing message asserting *"PR: #1065"* under **"What landed"** while the PR is open (PLAN-PR-010,
     now at **four** confirmations).
  2. Inbox `code-intelligence-substrate-002` — *"#1063 is still OPEN, catchable now"*, true at 08:08:51Z,
     **expired 32 minutes later** at merge.
  3. The operator's own *"#1067 enqueued, watching for it to land"* — already merged when analysed.
  4. ⭐ **NEW: `review-retrospective.md` on `#1067` asserting CodeRabbit "never reviewed this diff"** —
     generated 11:46, true then; CodeRabbit reviewed at **13:35:43Z** with 5 findings; never regenerated
     after the loop-back. Caught by the plan's own retrospective at finalize step 20/25.

  **The common shape**: a persisted artifact snapshots a still-moving fact and is never re-derived, while
  reading as current. ⛔ **The remedy is NOT "add an outcome field"** — a correct field beside a false
  sentence leaves the false sentence. Either regenerate, or stamp an explicit as-of.
  ⚠ **The general defence, and it is already this epic's standing rule**: re-derive at read time. It is
  why the inbox drain re-enumerates and why PR state is re-checked at analysis time — both changed the
  answer today.
- 2026-07-30 — ⛔ **The review-retrospective instance is the one that would have corrupted THIS epic's own
  corpus.** `finalize-step-review-retrospective` exists to compare the PR's reviewers — and it shipped a
  false claim about a reviewer. ⭐ **The harm is an inverted verdict, not a stale sentence**: a consumer
  trusting it reads CodeRabbit as absent ⇒ *no baseline* ⇒ scores `#1067` **"unassessable"**, when the
  truth is a **5 : 0 deficit against a real baseline** — opposite conclusions about the required bot's
  efficacy. ⭐ **`findings/PR-1067.md` survived only because it was scored from the API, never from the
  artifact**, which is exactly the standing rule that provider state is the sole evidence of
  participation. That rule now has a second justification: it protects us from our own tooling, not just
  from the bots.
  **Folded into PLAN-PR-010 as D0 (derive the population) + D3b (regenerate or stamp an as-of), NOT
  staged as a 15th plan** — two instances of one shape is a population to derive, and this epic's own
  standing rule is that a reported instance is a SAMPLE. ⚠ PR-010 is now at six deliverables, at the
  split-guard threshold, proceeding unsplit with the rationale recorded in the spec.

- 2026-07-30 — **Third drain: 3 messages, ONE new plan (`PLAN-PR-015`), five folds, one unowned defect.**
  ⭐ **`PLAN-PR-015` is the most severe finding the epic has taken.** A barrier override granted at 12:37
  against an explicitly **docs-only** delta ("2 ADR files, 542 insertions, no buildable source")
  authorized the 14:41:54Z merge of a HEAD containing **five production fix commits, 3 Major**, that did
  not exist when the operator ruled. ⛔ **They were caught by an ADR-number collision forcing a rebase —
  not by any gate.** Two defects: the authorization was HEAD-scoped in the operator's *reasoning* but not
  in its *persisted form*; and the barrier's second evaluation **recorded the residual gap and merged
  anyway**. ⭐ The 14:30 log entry is exemplary and is the only reason this is reconstructible — **the
  defect is that a correctly-recorded caveat gated nothing, and in the log it reads like a gate that
  passed.** Staged over a real temptation to fold into PR-013: both enforce *approval is HEAD-scoped*, but
  one governs a bot's credit and the other a human's authorization, and PR-013 is already at the split
  guard. ⛔ If either D1 shows they resolve to one predicate, consolidate.
- 2026-07-30 — ⛔ **CORRECTION RETURNED to `code-intelligence-substrate`: their § 3 committed the error
  their § 3 reports.** They claimed Sourcery's `#1063` refusal was also a size cap. **It was not** —
  verified at `pulls/1063/reviews`: *"you have reached your **weekly rate limit of 500000 diff
  characters**"*, a **quota**. `#1067` and `API-Sheriff#133` are *"larger than the **review limit of
  150000 diff characters**"*, a **size cap**. ⭐ **They generalised one PR's cause onto another without
  re-reading its body — collapsing two distinct causes into one, which is exactly the `hard_quota`
  catch-all defect they were reporting.** Their core finding is unaffected and **strengthened**: both
  causes demonstrably occur, same bot, same repo, ~8 hours apart. ⇒ PR-008's D1 must classify on the axis
  that matters — **can retrying this same input ever succeed?** — and must not assume Sourcery only ever
  size-refuses.
- 2026-07-30 — ⚠ **Two forwarded timestamps CORRECTED against the API**: the merge at **14:41:54Z** (not
  15:02:32) and CodeRabbit's review at **13:35:43Z** (not 13:40:11). Unexplained — possibly a differing
  clock in the plan's own decision log. ⛔ **Neither affects any finding**; the override still spans the
  rebase either way. Recorded so a future reader uses the API times and does not "fix" our record to match
  the message.
- 2026-07-30 — ⭐⭐ **ROOT CAUSE NAMED for the participation cluster, and it reframes PLAN-PR-005 from
  "a lossy view" to its mechanism: participation is inferred from PROXIES rather than read from the bot's
  own artifacts.** Three defects, one cause — comment `created_at` (false negative for in-place editors),
  `comments_found: 0` (rate-limited indistinguishable from clean), and check-run presence (reviewing
  without a check indistinguishable from not running).
  ⛔ **And the contract ALREADY says all of this.** `bot-participation-contract.md:115/:121` already
  specifies participation as first-presence OR `updated_at` movement, and already rejects the check-state
  proxy — while **`review_completeness.py` contains ZERO occurrences of `created_at`/`updated_at`**
  (orchestrator-verified, `grep -c` = 0). ⇒ **The rules are enforced by PROSE, not by CODE.** Aim the fix
  at making the contract executable; **changing a key changes nothing if no code reads a key.**
- 2026-07-30 — **A shared vocabulary adopted across PLAN-PR-005 and PLAN-PR-006**: `reviewed-clean` /
  `reviewed-with-findings` / `did-not-review`. ⛔ **Agree it once, use it in both** — two plans inventing
  two vocabularies for one distinction is the duplication failure this epic exists to fix. Reuses the
  corpus rule `2026-07-24-13-002`: **branch on producer STATUS before folding its payload.**

---

## Resolved / superseded defect entries

> Every entry below now has an owning staged spec, which carries its prohibitions verbatim
> (verified before relocation). Kept for provenance only.

✅ **The inherited-candidates section is RETIRED (2026-07-30).** `truthful-signals` applied the handover
and the operator widened it: **five** plans were released, not two, and all five now have owning specs
here (see Ordered Queue). Nothing in this epic is waiting on another epic's release any more.

- `PLAN-116` (participation shapes, incl. stale-vs-absent) → **split into five**: PR-001 (A), PR-002 (B),
  PR-005 (C+E), PR-006 (D), PR-007 (F).
- `PLAN-119` (barrier deadlock, with its operator-owed D3) → `PLAN-PR-008`.
- `PLAN-117` (merge-queue enqueue) → `PLAN-PR-009`.
- `PLAN-100` (landing message post-merge) → `PLAN-PR-010`.
- `PLAN-60` (gate ↔ CI parity) → **split**; review half is `PLAN-PR-011`, build-gate half returned.

Retained by `truthful-signals`, and NOT ours — ⛔ **all three ids MOVED on 2026-07-30; use the right-hand
column when re-deriving against their live queue** (inbox `truthful-signals-002.md` / `-003.md`):

| Was | Now | Note |
|---|---|---|
| `PLAN-113` | **`PLAN-TRUTH-001`** | Retained deliberately — `code-intelligence-substrate` recorded the PLAN-113 → PLAN-121 sequencing as a hard constraint. Do not attempt to take it |
| `PLAN-52` | **`PLAN-TRUTH-006`** | A git-mutation-contract defect, not a review defect |
| the returned PLAN-60 build half | **`PLAN-TRUTH-019`** (`build-gate-coverage-parity`) | ⛔ Must NOT be re-absorbed here |
| `PLAN-115` | **`PLAN-115`** — unchanged | Launched, so not renamed. `PLAN-PR-009`'s deferral may keep naming it; they will send its PR number when it opens |

⚠ **Provenance prose elsewhere in this tree still says `PLAN-116` / `PLAN-119` / `PLAN-117` / `PLAN-100` /
`PLAN-60`, and that is CORRECT** — those were the ids at transfer time, and the sibling records the five
numeric ids as **permanently spent** with their rows kept rather than deleted, precisely so the audit
trail survives. ⛔ Do not rewrite provenance, `logs/`, or `inbox/archive/` to the new ids: that would
falsify what happened. Only forward-looking pointers carry the new id.

Originated here — **all four now have an owning staged plan** (see Ordered Queue):

- **`wait-for-comments` counts rows instead of watching one row.** → `PLAN-PR-001`.
  `_github_pr.py:710` compares an
  unresolved COUNT against a baseline; pr-agent re-reviews by editing its one persistent Guide comment
  in place, so the count never grows and the await can only time out. The fix already exists one file
  over (`github_re_review.py:247-250` matches on the later of `updated_at`/`created_at`) and the registry
  already declares the answer (`participation_requires_update: true`). LIVE and load-bearing since #1054
  + #1052 composed: every loop-back now burns the full 600s and escalates to the operator even when
  pr-agent reviewed correctly. **Now confirmed at the config layer**: `pr-agent-settings` sets
  `persistent_comment = true` AND `final_update_message = false`, so pr-agent edits one comment in place
  and posts nothing new on re-review — by design and correctly so. There is no new row to count. ⛔ The
  fix belongs in the detector; do not "fix" it by re-enabling `final_update_message`, which was turned off
  precisely because plan-marshall filed that content-free update comment as a finding needing triage.
- **Org empty-review guard asserts a precondition its own config denies.** → `PLAN-PR-002`.
  `cuioss-organization`
  `reusable-pr-agent-review.yml` fails the job on empty `REVIEW_OUTPUT`; the runner legitimately produces
  nothing on unchanged-SHA, merge-commit and bot-commit pushes. Must be narrowed BEFORE
  `handle_push_trigger` is enabled, not after. ~21-repo consumer release fan-out. ⛔ Do NOT "fix" by
  downgrading empty-review to a warning — the runner exits 0 when every model call fails, and this guard
  is the only thing separating "reviewed, found nothing" from "never reviewed"; that ambiguity already
  cost a real misread on #1024.
- **PR-Agent security charter unverified in EFFECT.** → `PLAN-PR-004`. Confirmed landed at init: `pr-agent-settings`
  `main` is at `765e23f` (#13), and the live `.pr_agent.toml` carries both halves — `num_max_findings`
  raised 5 → **12**, and closing paragraphs that contest the empty-list permission and deny that severity
  is a reporting threshold. What is unverified is whether the model's behaviour changed. Oracle: a
  `/review` on plan-marshall#1042 (where CodeRabbit found six substantiated findings across the same
  diff, which is what justified raising the cap). **Pass is SHAPED, not counted** — if only Major-severity
  findings return, the severity clause did not take; a finding count proves nothing on its own. Note the
  residual suppressor is unreachable from config (`pr_reviewer_prompts.toml:150`), so a null result here
  means the charter cannot win that argument from `extra_instructions` — not that the charter is wrong.

- **Our own ingestion contract asserts both readings of the AI-agent block.** → `PLAN-PR-003`.
  Found AT decompose by direct read, not from a paste. `automatic-review/standards/coderabbit.md`
  carries a "Strip from the body before reasoning (noise, not findings)" list that names "the
  AI-agent prompt block", and then — four lines later — a trust-boundary section calling the same
  block "high-value structure (the cleanest per-finding payload)" and instructing the reader to
  "extract file/line/summary as fields". A reader does one or the other depending on which
  paragraph they reach first, and nothing announces the divergence. **This is why the `coderabbit`
  #3 premise could not be settled** — #3 turned the block OFF on the grounds that nothing consumes
  it, while the config comment it replaced said to keep it because plan-marshall ingests it; our own
  standard asserts BOTH, so neither side was checkable. Note `automatic-review/SKILL.md`'s
  never-execute rule does NOT break the tie: extracting-as-data and discarding are both
  non-execution. Archetype: doc-contract-divergence + the recurring vacuous-authority shape.
  ⚠ If the resolution is EXTRACT, finding extraction has been degraded on every CodeRabbit review
  since `a97b64f` and nothing announced it — the findings simply got thinner.

- ⛔ **`github_pr post_responses` is NOT idempotent — VERIFIED, and it has no owning plan yet.** From
  inbox `truthful-signals-007` item 6 (API-Sheriff PR #133). It selects findings by `terminal` alone with
  **no prior-transmission term**, so a second RESPOND pass re-sends replies already answered — observed
  cost **9 duplicated thread replies**, recurring on any further pass.
  ⭐ **Orchestrator-verified, and the forwarding epic did NOT verify it** (they said so): the sibling
  `workflow-integration-sonar/scripts/sonar.py` **already gets this right** — it imports
  `mark_finding_responded` (`:718`), skips on `finding.get('responded')` with reason `already responded`
  (`:748-749`), and sets the marker (`:764`). `workflow-integration-github/scripts/github_pr.py` has
  **none of these**: its `responded` occurrences are a *local output accumulator* of the same name, never
  a persisted marker. ⚠ **A naive `grep responded` finds hits in both files and suggests parity — the
  discriminator is `mark_finding_responded` / `finding.get('responded')`.**
  **Corrective**: add a per-finding `responded` marker mirroring Sonar; make the predicate
  `terminal AND NOT responded`, never `terminal` alone; and **set the marker in the same unit of work
  that sends the reply**, so a partially-completed pass does not re-send its already-sent prefix on retry.
  ⚠ **Left unstaged deliberately** — small, fully diagnosed, with a working model to copy, and the queue
  is at 15. ⛔ **If it IS staged, name the POPULATION**: the generalised rule is *"treat every
  external-transmit verb as re-entrant by default and audit each one's selection predicate for a
  prior-transmission term"*, and that sweep crosses both providers. The forwarding epic explicitly is not
  claiming that audit.

---

### Watches (as they stood at relocation)

- ✅ **The five owed post-merge revisits are ANALYSED (2026-07-30)** — one finding document each under
  `findings/PR-{1055,1057,1058,1059,1061}.md`. Taken as one batch from `truthful-signals` by operator
  decision; that epic has dropped its standing rule for PR-related PRs. Summary:

  | PR | CodeRabbit | Sourcery | PR-Agent | Verdict |
  |---|---|---|---|---|
  | `#1055` | 4 findings | rate-limited | 0 | ⛔ **DEFICIT 4 : 0** |
  | `#1058` | 2 findings, one Major | rate-limited | 0 | ⛔ **DEFICIT 2 : 0** |
  | `#1057` | rate-limited | rate-limited | 0 | no baseline — not assessable |
  | `#1059` | rate-limited | rate-limited | 0 | no baseline — not assessable |
  | `#1061` | reviewed, 0 findings | rate-limited | 0 | ✅ clean, corroborated |

  PR-Agent provided a result on all five — **zero must-provide violations**. Posted answers complete on
  all five: no `untransmitted`, no unjustified `skipped`.

  **Still open from this batch:**
  - ⭐ **`#1057` recovery is actionable and unclaimed.** CodeRabbit's refusal named the re-trigger and
    said "next review available in **2 minutes**" on 2026-07-29T15:14:56Z. No re-trigger was issued, so
    the merged diff has been reviewed by exactly one bot, which returned nothing.
  - **The recovery question common to all five is unanswered**: does an explicit re-review trigger still
    recover a review on a MERGED PR?
  - ⚠ **A prior note about `#1058` is not what the evidence shows.** It was recorded as "CodeRabbit
    reviewed the first HEAD and refused the second"; the fetched comments show CodeRabbit reviewing and
    posting 2 findings, with the later `@coderabbitai review` returning "Review finished". Re-verify
    before citing the partial-participation shape from this PR.
- ⭐ **OPEN — does a `pull_request`-triggered workflow run get created while a PR is
  `mergeable_state: dirty`?** Raised 2026-07-30 from `cuioss/API-Sheriff#133`
  (`findings/API-Sheriff-PR-133.md`). OBSERVED: that PR has **zero `pull_request`-event runs for any
  workflow** — pr-agent and dependency-review alike — while carrying `mergeable: false` / `dirty`; its
  only run is a `push`-event `Maven Build`. HYPOTHESIS (leading, **not settled** — one PR, correlation
  only): GitHub cannot materialize `refs/pull/{n}/merge` for a conflicted PR and so creates no run.
  ⚠ **Competing mechanism still live**: the v0.17.0 reusable-workflow guard (`15376a19`) — the only
  `pull_request` pr-agent run that day concluded **`skipped`** on a different branch, and `skipped` is a
  *created run*, a materially different state from *no run created*. ⛔ Do not merge the two states.
  **Re-check**: resolve #133's conflicts, then trigger via `reopened` / `ready_for_review` / an
  `issue_comment` — a plain push does not re-fire `opened`, so a push-only retest proves nothing.
  ⭐ **Why this matters beyond one PR**: if confirmed, every required-bot participation gate is
  **structurally unsatisfiable on a conflicted PR**, and the barrier's `fail_into_loopback` remedy cannot
  fix it — the loop-back does not resolve conflicts. That makes it an input to PLAN-PR-008's
  not-passable-by-action classification, and the reason PLAN-PR-007 gained a `not_triggered` member.
  Not yet owned by a staged plan; owned as a watch until the mechanism is settled.
- ⭐ **Plugin cache is stale against the executor — now MEASURED, and it has caused three live
  consequences in two days.** Skills load from cache `0.1.1240`; the executor embeds **exactly one**
  version, `0.1.1271` (so there is **no** pin/orphan inversion — that hypothesis is refuted here); and
  **32 versions coexist** under the cache root (`0.1.1194` … `0.1.1271`). ⇒ **What we READ is 31 versions
  behind what we RUN.**
  The three consequences, all first-party: (1) the cached SKILL.md's `inbox detect` section omits the two
  slug-prefixed id forms and the four-token `detection` vocabulary — caught only by testing against the
  executor; (2) the cached orchestration standard's read-boundary claim contradicted its source; (3) ⭐
  **a sibling epic's two subagents invoked the retired `--enabled-bots` flag from cache `0.1.1232` and
  mis-diagnosed the result as a source doc/script divergence** (corrected to them as
  `review-apparatus-006`).
  ⛔ **Standing rule adopted: verify a flag or command surface against the executor (`--help`), never
  against a doc — cached or not.** Re-check: `/sync-plugin-cache`, then confirm the loaded skill matches
  `marketplace/bundles/`. ⚠ Not blocking this epic, but it is no longer a cosmetic staleness note — it is
  an active source of wrong diagnoses, and the tool-layer fix is owed.
- ✅ **RETIRED as a watch — PROMOTED to a defect, now owned by `PLAN-PR-003`.** The watch asked
  whether plan-marshall's `automatic-review` ingestion consumes the AI-agent block or strips it.
  Answered at decompose: **our own standard says BOTH**, in one file, four lines apart. That is a
  defect in the contract rather than an open question about behaviour, so it moved to Open Defects
  above. The verification the watch called for is now that plan's deliverable 2 (does the enacting
  code match the resolved instruction), and its deliverable 3 closes the `coderabbit` #3 premise on
  the resulting evidence. The watch's warning still stands and is carried into the spec: **do not
  read a reduced finding count as improved signal.**
- ✅ **RETIRED 2026-07-30 — "Sourcery hard-refuses repeatedly" is NOT a defect.** Operator ruling:
  Sourcery rate limiting is **known and not an issue**, as is CodeRabbit's. The prior entry said it
  would "graduate to a defect" if it refused on three more landings — **that escalation is cancelled**;
  it refused on all five owed revisits and that is the expected state, not evidence. Sourcery stays as
  an additional reviewer. ⚠ Do not re-open this as a defect on refusal-count evidence.
  ⛔ **What is NOT retired**: the barrier *deadlocking* on a refusing bot (`PLAN-PR-008`). The refusal
  is expected; the barrier having no exit from it is still a defect. Do not collapse the two.

## Retired from Open Defects — 2026-08-08 queue audit

### `refused_hard` fall-through (half refuted, remainder re-homed to PLAN-PR-006)

- ⛔⛔ **`refused_hard` is a FALL-THROUGH reported as a classification — VERIFIED 2026-08-01, no owning
  plan yet.** `review_completeness.py:188-189` is a binary on one string equality
  (`rate_limit_class(bot) == 'awaitable_window'`), and `rate_limit_class()` is fail-closed to
  `'unknown'`. ⭐ **Only `coderabbit` declares `rate_limit_class` in the registry at all**
  (`bot_registry.py:27`) — so **every other bot resolves to `refused_hard` on any refusal**, because the
  field is missing, not because a hard quota was seen. The operator is then shown *"refused_hard (hard
  quota)"*, a positive claim derived from an absent field. Observed live on `API-Sheriff#140`, where
  Sourcery's refusal is in fact a **weekly** limit saying *"try again later"*.
  ⚠ **NOT a false green** — the fall-through direction is safe (unknown → unproven → barrier holds). The
  gate is right and the *report* misinforms, which is this epic's own theme. Practical cost: it steers an
  operator toward "waiting is futile, force it" when waiting would have worked.
  ⛔ **Do NOT stage this as its own plan** — it is a `PLAN-PR-007` D1 question ("which taxonomy members
  are fall-throughs of a missing registry field?"), checkable at `review_completeness.py:188`. Whether the
  fix is *declare `rate_limit_class` for every bot* or *give the undeclared case its own state* belongs to
  that plan. Full write-up: [`findings/API-Sheriff-PR-140.md`](findings/API-Sheriff-PR-140.md) § 2.

### `post_responses` non-idempotency (owned by PLAN-PR-019; diagnosis relocated into that spec)

- ⛔ **`github_pr post_responses` is NOT idempotent — VERIFIED, no owning plan.**
  ⭐ **THIRD sighting, now with a ROOT CAUSE** (inbox `-002`): the documented rationale in
  `verification-feedback.md` Step 8 ("already-responded findings are terminal and no longer pending")
  is **inverted**. `_RESPONDABLE_RESOLUTIONS` *is* the terminal set — terminal is the **selection**
  criterion, not an exclusion criterion, so a finding becoming terminal is what makes it eligible and
  it stays eligible forever. ⚠ PR #1071 did not get bitten only because the store held exactly ONE
  finding: **n=1 masked it; that is not evidence of safety.** Prior sightings: 9 duplicated replies
  (plan-marshall), 11 threads (API-Sheriff #138). ⛔ Three observations are not a rate — do not derive one. It selects findings by
  `terminal` alone with **no prior-transmission term**, so a second RESPOND pass re-sends replies already
  answered (observed: **9 duplicated thread replies**, recurring on any further pass).
  ⭐ **The sibling already gets this right**: `workflow-integration-sonar/scripts/sonar.py` imports
  `mark_finding_responded` (`:718`), skips on `finding.get('responded')` (`:748-749`), and sets the
  marker (`:764`). `workflow-integration-github/scripts/github_pr.py` has **none of these** — its
  `responded` occurrences are a *local output accumulator* of the same name.
  ⚠ **A naive `grep responded` finds hits in both files and suggests parity — the discriminator is
  `mark_finding_responded` / `finding.get('responded')`.**
  **Corrective**: add a per-finding `responded` marker mirroring Sonar; predicate becomes
  `terminal AND NOT responded`; **set the marker in the same unit of work that sends the reply**.
  ⚠ Left unstaged deliberately — small, fully diagnosed, model to copy, queue at 15. ⛔ **If staged,
  name the POPULATION**: every external-transmit verb needs auditing for a prior-transmission term, and
  that sweep crosses both providers.
