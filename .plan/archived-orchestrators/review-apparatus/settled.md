# Settled narrative — relocated from `epic.md`

Dated records relocated by the cloud-wave ingestion on 2026-08-23. **Nothing here was deleted** —
each section is reproduced verbatim, and `epic.md` carries a pointer at the origin.

> ⭐ **2026-09-13 relocation (operator-confirmed)**: six further resume-anchor blocks were moved here
> VERBATIM — see § "Relocated resume-anchor blocks (2026-09-13 cleanup, operator-confirmed)" at the end
> of this file. Their subjects are closed by the `PLAN-PR-033` (#1473) and `PLAN-PR-046` (#1477)
> landings and by the 2026-09-12 corpus redistribution. ⛔ The three STANDING blocks were deliberately
> NOT relocated and remain inline in the resume anchor.

These are RECORDS of decisions already taken, not live state. Live state is `status.json` and
`epic.md`; the landed cloud wave is `cloud-wave-audit.md` and `cloud-runs/`.

---
## ⛔⛔ #1071 opened a latent false-positive on PR-Agent — CODE-VERIFIED 2026-08-01

A `truthful-signals` reply claimed #1071's timestamp arm misreads a refusal as a re-review, citing
CodeRabbit on their #1073 (comment edited in place 88 min later, body still *"Review limit reached"*).

**Checked against the live registry — the claim does NOT hold for CodeRabbit.** Two independent guards
stop it (`standards/coderabbit.md`): `participation_requires_update: false`, so #1071's movement arm
**never applies to it** (the count-growth arm does, and an in-place edit adds no comment); and
`refusal_patterns: ["Review limit reached"]` **matches their evidence verbatim**, so `fetch_findings`
files it in `refused_bots[]` and excludes it from `participated_bots[]`.

⭐⭐ **But the MECHANISM is real, and it lands on the other bot.** `standards/pr-agent.md`:

| | CodeRabbit | **PR-Agent** |
|---|---|---|
| `participation_requires_update` | `false` | ⛔ **`true`** — movement arm APPLIES |
| `refusal_patterns` | `"Review limit reached"` | ⛔ **EMPTY** |

⇒ **If PR-Agent ever posts a refusal and edits its persistent Guide comment in place, nothing
recognises it as a refusal and the movement arm credits participation.** A refusal becomes a review.

⚠ **#1071 CHANGED the risk profile of that empty list rather than creating the emptiness.** The registry
documents `refusal_patterns: EMPTY` as deliberate and fail-closed — *"a refusal is never claimed without
positive evidence"* — which is sound for the **refused** classification. It was safe while presence
alone could not credit an edit-in-place bot. **#1071 made movement a credit signal, and a refusal edit
is movement.** The fail-closed reasoning was never re-examined against that change.

⛔ **HYPOTHESIS, not observed**: no PR-Agent refusal has ever been seen (that is *why* the list is
empty). The confirm/refute artifact is `standards/pr-agent.md` § `refusal_patterns` crossed with
`_github_pr.py`'s movement arm. **Do not record it as a live incident.**
⇒ Owned by **PLAN-PR-007** (it owns refusal classification and PR-Agent's `absent` semantics), with a
cross-note to **PLAN-PR-013**. Reply sent to `truthful-signals`.

## Retained from the PR #1070 drain — assigned, not unowned

⛔ **These four are NOT Open Defects — each has an owning staged plan.** Recorded here only because the
owning specs were written before this evidence existed and must be re-read against it at outline.

- ⭐⭐ **`classify_bot` checks participation BEFORE refusal, and the participation evidence is NOT
  HEAD-scoped** → a bot that reviewed an earlier commit and then REFUSED the current one is credited
  `participated`. **The live refusal is laundered away by stale evidence from a prior commit.**
  ⇒ **PLAN-PR-013** (`participation-credited-from-a-superseded-commit`) — this is its exact mechanism,
  now confirmed in code rather than inferred from #1063. ⛔ The spec assigns this wrong-commit class to
  PR-013 and **forbids consolidation**; PR-014 correctly declined to fix it in passing.
- ⭐ **`github_re_review` returned `matched: true` AND `refusal_detected: true` in ONE envelope** on
  PR #1070 — the "match" was CodeRabbit's ACK text *"does not re-review already reviewed commits"*.
  **A refusal ACK counted as a review**, and the caller then reported a fresh review that does not
  exist. ⇒ **PLAN-PR-013**, with the taxonomy half touching **PLAN-PR-007**.
- **Trigger-B contradicts itself** — its prose and numbered steps disagree, and the disagreement can
  make the REQUIRED bot **structurally untriggerable**. ⇒ **PLAN-PR-008** (barrier reachability).
- **A bot comment carrying the DOCUMENTED ignore-pattern marker still survived the noise pre-filter**
  into the findings ledger (PR #1070, CodeRabbit's auto-generated ACK). ⇒ **PLAN-PR-016** (RUNNING) —
  the same producer pre-filter it already owns, one bot over. ⚠ Whether it is in scope is **that plan's
  call at outline**, not a directive from here; PR-016's own verify-first clause takes precedence.

## ⛔⛔ RETIRED FRAMING — 'the merge-queue enqueue does not take' is REFUTED. Do not propagate it.

**PLAN-PR-009 / #1087 refuted its own title, and both hypotheses the spec carried.** No enqueue was ever
issued; `use_merge_queue: true` was correctly plumbed and present in the payload; the queue was never the
failing component (the same run recovered via `ci pr merge-queue` and #1082 landed normally).

**The established cause is an OFF-ROUTING DISPATCH** to `ci pr merge` — a verb `branch-cleanup`'s routing
names on neither branch, and the only merge-shaped verb with no preflight, no readiness poll and no
post-merge check.

⛔ **Anyone searching this epic for "merge queue enqueue" reaches a plan whose finding is "the merge queue
was never reached."** The id cannot be changed — it is the branch, the plan directory, the PR title stem,
the inbox `sender_id`, and the landed PR — so **the framing is retired here instead.** Do not cite the
enqueue framing into sibling specs.

### ⭐⭐ STANDING PRACTICE CHANGE, accepted from `merge-queue-enqueue-does-not-take-007` — this is a criticism of MY spec authoring and it is correct

> **Name plan specs after the OBSERVATION, not the hypothesised cause.**

The plan id is **load-bearing, not a label**: branch name, plan directory, PR title stem, inbox
`sender_id`, and the phrase every later reader uses to recall the work. ⛔ **When it encodes a hypothesis,
a refuted hypothesis cannot be corrected without renaming a launched plan — which is prohibited, and
rightly so.** The result is a permanent inversion, and anyone reasoning from the title alone will
re-derive the refuted hypothesis.

The observable fact here was **"`ci pr merge` reported merged on a PR that closed unmerged" (#1081)** —
phrasing that survives *any* diagnostic outcome, because it states what was seen rather than what was
guessed.

⚠ **Preserve what the spec did WELL**: it carried its hypotheses **explicitly and enumerated**, which is
exactly what let the D1 gate refute them cleanly and settle a third cause. ⇒ **Hypotheses belong in the
spec body as inputs to a diagnostic gate, never in the title and never as conclusions. Move only the
naming.**

⛔ **Audit the staged queue against this before emitting**: several titles name mechanisms rather than
observations. Do NOT rename anything launched or shipped.

## PLAN-PR-007 landed (#1118) + a live cross-epic duplicate — 2026-08-08, after the queue audit

Full landing record: [`landings/PLAN-PR-007.md`](landings/PLAN-PR-007.md). Shipped 5/5 deliverables,
21/21 finalize steps, 7h27m. The taxonomy is seven closed members.

### ⭐⭐ The landing's own verdict on itself is the best datum the epic has

**The pre-merge barrier blocked `#1118` once — on that plan's OWN new `participated_stale` member,
firing against its own PR.** Choosing the loop-back over an available override is what produced
CodeRabbit's review: **8 actionable comments including a Major where the plan violated its own
fail-closed thesis at a call site it had just added.** ⇒ **An override was defensible and would have
shipped a Major.** Folded into `PLAN-PR-008` D3 as its first value-side datum — the escalation's framing
changes from *"pay latency for findings that can never block"* to *"at the one observed opportunity,
taking the exit would have shipped a Major"*. ⚠ n=1: it constrains the DESIGN (expensive, recorded,
distinguishable), not the answer.

⛔⛔ **And the SAME PR passed an unreviewed range in the other direction.** Its last two commits were
never bot-reviewed — CodeRabbit refuses already-reviewed ranges, Sourcery was over its size limit,
pr-agent returned contentless guides — and **the barrier passed them on `participated_but_empty`:
participation, not coverage.** The 14 fixes after CodeRabbit's one real review rest on CI and
self-review alone. ⭐ **The epic's thesis reproduced by the very plan that widened the taxonomy to state
it: naming a state made the gap NAMEABLE, not VISIBLE.** Second first-party instance of CodeRabbit's
range-consumption (already folded into PR-005); the barrier half belongs to PR-006 + PR-013.

### ⛔⛔ CROSS-EPIC DUPLICATE FOUND LIVE — PLAN-PR-018 RETIRED

`manage-status list` showed `self-review-resweeps-full-surface-every-round` at `2-refine`; its
`request.md` `source_id` names **`code-intelligence-substrate` PLAN-CIS-031** — the same subject as our
staged **PLAN-PR-018**, launched today at 20:33. **They are in flight; we were staged.** ⇒ Our row is
**retired**, and everything PR-018 had absorbed (the C18 nine-lesson corpus, the scope-of-sweep ≠
scope-of-claim trap, the `#1087` cost-and-yield datum, the fresh `#1118` yield curve) was handed to them
as `review-apparatus-006`.

⚠ **The routing rule is the real finding.** Their spec routes it out of here ("no
PR/review-participation surface"); our row arrived routed the opposite way ("pre-submission self-review
IS review apparatus"). ⭐ **The three-way test does not cleanly assign *self*-review** — both readings
are defensible, neither epic erred procedurally, and the duplicate survived in two ledgers until an
unrelated status listing exposed it. **A ledger cannot detect a duplicate that lives in another
ledger**; only a live plan-list read did. Recorded as a Watch.

### Two flagged items were re-attributed away from this epic

- ⛔ **`enriched.json` dirty on main is NOT this run's doing.** Both files were **already modified at
  this orchestrator session's start**, before PR-007's finalize ran (first-party from this session's own
  opening git snapshot), and the sibling recorded the same four hints earlier today.
  **`truthful-signals` PLAN-TRUTH-064 already owns making the guard see them.** Finding `763636` is a
  duplicate of an owned item — **do not file a follow-up plan, do not revert.** ⭐ The report's guard
  reasoning still stands and is worth keeping: `post_run_source_guard`'s predicate excludes `.plan/`,
  and these are tracked files inside it.
- ⛔ **The token-figure understatement is `truthful-signals` PLAN-TRUTH-066's subject** (*"the
  retrospective reads a record that is not yet written"* — `record-metrics` is ordered after
  `plan-retrospective`). 6.9M dispatched / 9.9M inline / 65.1M billing-weighted are **three populations
  that must never be summed.** Not ours; already staged there.

## Queue audit — 2026-08-08 (full reconciliation of all outstanding specs)

Every staged and launched spec was read and its material claims checked against merged main. **Nine
corrections were applied to the specs themselves**; they are recorded here so a resuming session sees
what moved without re-reading twenty files.

### ⭐⭐ The finding that matters most — `#1118` shipped a member that reads as closing a trap it left open

PLAN-PR-007 landed as **`#1118`** (`fddc4ec8b`). It widened the participation taxonomy to seven closed
members, and a required bot resolving to `participated_stale` now **blocks**. That looks like
PLAN-PR-013's D3 ("a review of a superseded commit does not satisfy a required-bot gate").

⛔⛔ **It is not.** Verified by symbol at `github_pr.py` § `_has_update_movement` (`:645-677`):

```
return bool(updated_at) and updated_at != created_at
```

**The currency test keys on COMMENT MUTATION — no commit SHA is consulted anywhere.** A bot that
reviewed commit N and later edits its comment for any reason reads as *current* for N+1; a review first
observed after a head advance is credited the same way. ⭐ **`reviewed_commit_sha` is already stored in
the findings store and simply is not what the barrier consults.**

⭐⭐ **PLAN-PR-007's own spec predicted this exact trap** — it warned that "a detector keyed on diff
CONTENT rather than on HEAD IDENTITY would miss [the content-identical rebase]". What shipped is keyed
on **neither**; comment mutation is weaker than both. ⇒ **The epic's sharpest instance of its own theme:
a plan named the right trap, shipped a member that reads as closing it, and left it open one layer
down.** PLAN-PR-013 is re-scoped accordingly — its D3 is now *re-key the currency test onto HEAD
identity*, not *add a comparison*.

### Corrections applied to specs

| Spec | Correction |
|---|---|
| **PR-013** | Re-scoped against `#1118` (above). Blocking half shipped; anchor half is the live subject. |
| **PR-011** | **D2 presumptively SHIPPED** — `#1118` added `_github_checks.py` (+120) with the workflow-run presence probe D2 proposed, plus `not_triggered`/`in_progress` as distinct members. Marked re-verify-or-drop. |
| **PR-008** | ✅ **UNBLOCKED** — its PR-007 dependency is discharged. But `#1118` edited `branch-cleanup.md` (+64) and `test_pre_merge_barrier.py` (+145): re-ground every line reference. D1's population now derives from the shipped seven-member taxonomy, not from a hand-list. |
| **PR-010** | ⛔ **The delegation was NEVER ACCEPTED — this plan is OURS.** Their `PLAN-100` still reads `transferred` (to us) and no `PLAN-TRUTH-*` row owns the subject. The row said "do NOT start" for six days while the sibling paid a manual tax. |
| **PR-003** | Sourcery population HYPOTHESIS **REFUTED** — no strip-list in `sourcery.md` or `pr-agent.md`; the contradiction is `coderabbit.md`-only. Population is one, not per-document. |
| **PR-019** | Asserted absence **CORROBORATED first-party**: `cmd_post_responses` (`:1333`) selects on `resolution` + `pr_number` with **no transmitted marker**. D1's absence question is settled; its consumer derivation is not. |
| **PR-005** | Its `grep -c` **= 0** claim now returns **1** (a docstring added by `#1118`). Substance holds; the wording was a count standing in for a behaviour claim. |
| **PR-017** | Its "no shared-file debt … does NOT touch `branch-cleanup.md`" claim was **self-contradicting** — its own absorbed section puts the fourth site at the barrier. Corrected; four of its five surfaces were modified by `#1118`. |
| **PR-018** | "Overlaps with no staged plan on file surface" was **wrong** — PR-012 targets the same skill (`ext-self-review-plan-marshall`). Sequenced, PR-018 preferred first. |

### Structural defects found across the corpus

- ⛔⛔ **FOUR specs were staged with NO `## Expected Surface` section** — PR-017, PR-018, PR-019, PR-020.
  That section is the **disjointness admission input** the `next` verb consumes, so **none of the four
  was admissible and the shortfall would have read as "no candidate qualified"**, never as "the spec is
  malformed". All four now carry one. ⭐ **A missing input and a failed test are indistinguishable at
  the admission gate** — the epic's own theme, in its own staging process.
- ⛔ **PR-017 and PR-020 were also missing their `## Hand-Off Command`** (PR-017 additionally its
  Write-Boundary). Added.
- ⚠ **Three specs declared a workstream the ledger contradicted** — PR-008, PR-009, PR-010 said `WS-01`
  while `status.json` said `WS-04`. The ledger was right (barrier / merge / landing-channel are WS-04);
  the specs are corrected.

### Distribution improvement applied

⛔ **Three plans were each about to derive per-reviewer finding counts independently** — PR-006 D1
(deficit comparison), PR-011 D4 (review-versus-gate delta), PR-021 D2 (the `N of M` denominator).
**Three derivations of one quantity is three chances to disagree, and a coverage figure that differs
between two artifacts is precisely this epic's subject.** ⇒ **PR-006's D1 now owns the counting rule for
the epic**; PR-011 and PR-021 consume it and are forbidden from restating it. Ownership attaches to the
*rule*, not the plan id — whichever lands first states it.

## Inbox drain — 2026-08-08 (13 messages, queue emptied)

⭐ **Clean drain: 13 scanned / 13 consumed / 0 invalid / 0 archive failures.** `inbox list` now returns
`count: 0` with `inbox_state: present` — the *looked-and-found-nothing* zero, not the *could-not-look*
one. 12 messages came from the PLAN-PR-007 run (1 landing + 11 candidate-lesson); the 13th arrived
mid-drain from `truthful-signals`.

| Message | Kind | Disposition |
|---|---|---|
| `…-001` | landing | **reconciled** — duplicate of a settled reconciliation; PR-007's row was already complete |
| `…-002` | candidate-lesson | **folded** → PR-017 (closes its open HYPOTHESIS) |
| `…-003` | candidate-lesson | **folded** → PR-006 |
| `…-004` | candidate-lesson | **folded** → PR-008 |
| `…-005` | candidate-lesson | **promoted** → `2026-08-08-21-001` |
| `…-006` | candidate-lesson | **folded** → PR-011 |
| `…-007` | candidate-lesson | **promoted** → `2026-08-08-21-002` |
| `…-008` | candidate-lesson | **promoted** → `2026-08-08-21-003` |
| `…-009` | candidate-lesson | **folded** → PR-017; signal-gate half **delegated** to `truthful-signals` |
| `…-010` | candidate-lesson | **promoted** → `2026-08-08-21-004` |
| `…-011` | candidate-lesson | **promoted** → `2026-08-08-21-005` |
| `…-012` | candidate-lesson | **folded** → PR-006 |
| `truthful-signals-024` | finding | **folded** → PR-021 (primary) + PR-008 |

### The three things this drain changed that a reader must not re-derive

1. ⭐⭐ **PR-017's fourth-cause-class HYPOTHESIS is CLOSED and widened.** It was a second-hand
   `truthful-signals-020` lead explicitly "re-derived by nobody here". Q-Gate `b423d3` confirms it
   first-party on #1118 — and the real defect is worse than the hypothesis: **the two flags disagree
   with each other** (`--participated-bots` wants `bot:evidence` pairs, `--stale-participation-bots`
   wants bare kinds) while **the producer emits pairs for both sets**. A caller forwarding producer
   output verbatim gets the wrong form *by construction*. ⇒ D0's population is now flag-set **internal
   consistency**, not per-flag value-shape validation alone.

2. ⛔⛔ **PR-021's defect has an opposite polarity, and fixing only the staged one makes the other
   worse.** PR-021 was staged for a **false alarm** (shortfall disclosed against the roster rather than
   the required set). `truthful-signals-024` shows the **false-clean** direction on the same mechanism:
   on #1122 the quorum was met by a bot that filed nothing, while the bot that produces the actionable
   findings was rate-limited and never saw the diff. If the disclosure counts `participated_but_empty`
   as participation, it reports **full coverage on a PR where nothing was reviewed**. Swapping the
   denominator alone removes the incidental noise that was the only thing drawing attention to a thin
   review. **Both polarities, one pass.**

3. ⭐⭐ **PR-011 now has a controlled experiment instead of an impression.** Same diff, same day:
   self-review produced 6 findings, CodeRabbit's first review produced 8, and the two sets are
   **essentially disjoint**. Self-review found inconsistencies *between statements in the diff*; it did
   not find *behaviours under inputs the diff does not contain*. The consequence the plan must carry is
   sharper than "self-review is weaker": a run that treats self-review as a proxy for review quality
   **merges on that proxy exactly when a bot is unavailable** — which is precisely what happened later
   in this same run.

### One question answered, so it is never re-asked

`truthful-signals-024` asked whether `rate_limited` fell outside the #1118 taxonomy. ✅ **It is inside
it**: `STATE_REFUSED_AWAITABLE` (`review_completeness.py:132`) and `STATE_REFUSED_HARD` (`:133`), split
by the refusing bot's registry `rate_limit_class` (`:237`). A rate-limited bot does **not** collapse
into "did not participate". ⛔ The message's per-bot states remain a **lead, not a measurement** — the
sender did not run `ci pr comments --pr-number 1122`.

### Dedup discipline applied once, deliberately

`…-007` arrived headlined as *five hard-coded set-guarding populations*. That archetype is **already**
lesson `2026-08-08-20-001`, and all six sites were already fixed. The promotion therefore extracts only
the genuinely new rule — **a count comparison whose two sides share a pivot proves nothing** — and
cross-references `20-001` rather than restating the population rule a sixth time.

## Corpus review + drain — 2026-08-09 (full reconciliation of all outstanding plans)

A ground-truth pass over every staged spec, plus a 17-message drain. **Three deliverables were found
already SHIPPED and dropped, one plan's premise was REFUTED, and one plan's evidence base was found to
carry a confound introduced by the plan that shipped this week.**

### What ground truth changed

| Plan | Verdict | Evidence read first-party in merged main |
|---|---|---|
| **PR-008 D2** | ✅ **SHIPPED — dropped** | `review_completeness.py:237` splits `awaitable_window` / `hard_quota` via registry `rate_limit_class` |
| **PR-008 D3** | ✅ **SHIPPED AND EXERCISED — dropped** | `_cmd_merge_authorization.py` (HEAD-bound, `gap_class`, fail-closed at `:157`); used on #1130 as `barrier-ask-override` |
| **PR-011 D2** | ✅ **SHIPPED — dropped** | `_github_checks.py` `_classify_check_buckets` `:121`, `_is_pull_request_event_run` `:155`, `_has_pull_request_event_run` `:178`, `_pull_request_event_runs_for_pr` `:244` |
| **PR-008 D1 (size cap)** | ⛔ **ABSENT — confirmed applicable** | `review_completeness.py` (587 lines) contains no `diff_size` / `size_cap` / `150000` / `too_large` token |
| **PR-003** | ⛔ **LIVE — confirmed applicable** | `coderabbit.md:138-140` says strip the AI-agent block as noise; `:142-149` calls the same block "high-value structure … extract file/line/summary as fields" |
| **PR-012** | ⛔ **LIVE — confirmed applicable** | `_detect_count_prose` `:1040` docstring scopes it to `SKILL.md` in the skill dir, over five cardinality nouns |
| **PR-002** | ⛔ **LIVE — stays parked** | the empty-`REVIEW_OUTPUT` guard is unchanged at `reusable-pr-agent-review.yml:327` post-#237 |

### ⛔⛔ PLAN-PR-008's premise is REFUTED

Its Objective states *"There is no sanctioned way to record 'this bot is degraded, proceed with a
documented gap.'"* **There is** — explicit, recorded, HEAD-bound, gap-class-bound, and exercised on
#1130. With D2 and D3 gone, what survives is one thing: **the taxonomy has no STRUCTURAL-refusal
member.** A rate limit is *temporal* (the same request succeeds later); a diff-size cap is *structural*
(it never does), so the existing wait/accept option pair **offers a non-option on the size branch**.
⚠ The slug no longer describes the work and the plan is now small — a fold into PR-021 is an open
emit-time question, recorded so it is not re-derived.

### ⛔ PLAN-PR-006's baseline carries a confound this week's landing introduced

Every row of its live-evidence table (`#1055`, `#1057`, `#1058`, `#1059`) was gathered **2026-07-30**,
before **#1130** changed the reviewer's instructions. A deficit measured before the instruction fix and
one measured after are not the same quantity. ⭐ The pre/post boundary is also the cleanest available
measurement of whether #1130 worked — which is the same question **PR-023 D3** asks by re-review, so
the two must be coordinated rather than run as independent measurements of one effect.

### Distribution — is the split across plans right?

**Yes, with one exception.** Five plans orbit the barrier (PR-005, PR-006, PR-008, PR-013, PR-021) and
that looked like over-fragmentation until each was read against its seam:

| Plan | Distinct seam |
|---|---|
| PR-013 | **currency** — is the credit anchored to the merge candidate's SHA |
| PR-005 | **derivation** — is the credit read from the ledger or a lossy projection |
| PR-021 | **disclosure** — what the coverage statement says, and against which denominator |
| PR-006 | **quality** — did a participating reviewer produce anything |
| PR-008 | **refusal taxonomy** — can the state even be represented |

These are genuinely different, and the specs already cross-reference rather than duplicate (PR-021 D2
explicitly consumes PR-006 D1's counting rule instead of re-deriving it). **The exception is PR-008**,
which after losing D2 and D3 is a single-deliverable plan sitting on PR-021's surface.

⭐⭐ **The one thing no plan owned, now assigned:** *`participation_complete` is a LIVENESS predicate
being consumed as a COVERAGE predicate.* Four PRs of evidence (#1118, #1122, #1127, #1130) and it was
scattered across four specs as a symptom. **PR-021 now owns the statement**; the others consume it.

### The drain, in one line each

17 scanned / 17 archived / 0 invalid / 0 failures. **6 folded** (PR-005, PR-006, PR-008, PR-013,
PR-017, PR-021, PR-023, PR-010 — some messages fed two specs), **1 promoted** (as an *update* to lesson
`2026-08-08-21-003`, not a duplicate), **3 reconciled** (the three competing landings — only the
18:38:03Z one was acted on), **4 discarded and delegated out** (3 to `truthful-signals` as
`review-apparatus-021`, 1 to `code-intelligence-substrate` as `review-apparatus-007`).

⭐⭐ **The sharpest item drained**: `automatic-review` rendered `display_detail: "0 comment(s) found
(unified triage pending)"` on a run where **no reviewer produced content** — textually identical to
what a clean 27-file review produces. That is PR-006's title condition located in *our own rendering*
rather than in the reviewer's output, and it is the cheapest real fix in the epic: the taxonomy already
exists, it simply never reaches the field a reader sees.

## Inbox drain — 2026-08-09 (second drain, 1 message / 2 items, both folded)

`truthful-signals-027.md` (`kind: finding`, transferred to us under the three-way routing rule after
arriving in their inbox as `candidate-lesson` from PLAN-TRUTH-070 / PR #1132, both items carrying
`likely_epic=review-apparatus` in their own envelopes). ⭐ Their `lessons-capture` step flagged the
misrouting as a **lead rather than deciding it** — the transfer needed an orchestrator. Contract working.
**Disposition: `folded`. Removed from their ledger, nothing owed back.**

### ⭐⭐ Item 1 → PLAN-PR-013 — and the drain UPGRADED it from a lead to a verified mechanism

The report: bot participation flipped `true` → `false` across two fetches of PR #1132 at the **unchanged
HEAD `cbb184c9d`**, ~24 min apart, with no push and a `noop` rebase.

⭐ **This drain read the implementing source first-party rather than propagating the filer's hypothesis,
and the mechanism is now OBSERVED**: `github_pr.py` § `_has_update_movement` (`:644-677`) is a **two-arm**
predicate — *first presence in the plan's accumulated `observed_keys` ledger* **OR** *comment
`updated_at` movement*. The first fetch **consumes** the first-presence credit (persisted at `:898`; the
code comment at `:892-897` states the design intent outright), so a second fetch of the same unedited
comment at the same HEAD **must** flip to `participated_stale`. Deterministic, not intermittent.

⛔⛔ **All three candidate mechanisms the filer named are CONTRADICTED** (no wall clock is read; no
PR-level `updatedAt` is read; no paging effect), and so is the forwarding orchestrator's ⭐⭐ inference
that the `updatedAt`-vs-SHA candidate was *"the predicted one"* — their direction was right, their
mechanism wrong. ✅ They labelled it unverified and offered it as a starting point; the label is what made
re-derivation the obvious move.

⭐⭐ **The new consequence, which no plan held: the merge verdict depends on HOW MANY TIMES YOU LOOK.**
Fetch once → merge on `true`; fetch twice → block on `false`, same evidence. **An observer effect in a
merge gate.** ⇒ PR-013 D1 now owes an **idempotence-under-re-evaluation** report per site, not only a
which-SHA report. ⭐ It also **corrects PR-013's own OBSERVED claim**, which quoted only the second arm of
that function and presented it as the whole body.

### ⚠ Item 2 → PLAN-PR-006 — recurrence, folded, NOT a new item

A fourth consecutive quorum-pass on zero actionable review (#1122, #1123, #1125, #1132). ⭐ The sharp
edge is the spread, not the count: on #1132 three reviewers reached non-review by **three different
routes** (`participated_stale` / `refused_awaitable` / `refused_hard`) and the quorum outcome was
identical to the other three. ⚠ Explicitly a **pattern claim, not a measurement** — no population, no
rate — and it straddles the #1130 confound boundary, so the four rows are not poolable.

⚠ **Cross-item double-count guard recorded in both specs**: `pr-agent=participated_stale` on #1132 is ONE
observation feeding both items. PR-013 asks why the credit decayed, PR-006 asks why the quorum passed
anyway; neither may cite it as independent corroboration of the other.

## Relocated resume-anchor blocks (2026-09-04 cleanup, operator-confirmed)

Thirty-one settled `resume_anchor` blocks, moved **verbatim** from `status.json` during the Phase B
relocation judgement. Nothing was dropped, summarised, or reworded. Each keeps its original `=== … ===`
header so the anchor's pointer resolves by name. Standing rules and do-not-re-derive notes were NOT
relocated — they remain inline in the anchor.

### 2026-09-03 FIFTH DATA-POINT (API-Sheriff, operator-relayed). ABSORBED as an Open Defect. TWO NEW DERIVATIONS.
⭐⭐⭐ (A) THE THREE-REPO SWEEP IS A REVERT, AND THE VALUE TO RESTORE IS PROVEN BY EACH REPO'S OWN HISTORY. All THREE sweep diffs read EXACTLY `coderabbit,pr-agent` BEFORE the change - TokenSheriff 05818bc4 (#693), API-Sheriff 1c7308c (#249), cui-http c7862d0 (#192). ⇒ The owed action is a ONE-LINE REVERT per repo. ⛔ This RETIRES the reporting run's framing ("changing project config is your call"): nobody has to decide what the required set should be, because each repo already had it.
⭐⭐ (B) THE BLOCK IS DETERMINISTIC AND PERMANENT, NOT "it would have blocked this merge" - derived from OUR code, not from the run's report. review_completeness.py:1040 builds `classified` from the configured token strings VERBATIM with NO registry check; :1048 matches evidence on `bot_kind`; `proven` is keyed on `bot_kind`; and `absent` is the documented FAIL-CLOSED default for no-evidence (:711). ⇒ A non-kind token can never be proven by any amount of real reviewing, so EVERY future merge in that repo blocks. ⛔ And retrying cannot fix it - re-fetch, re-classify, re-emit absent: NON-CONVERGENCE ARCHETYPE, THIRD INSTANCE (after PLAN-PR-043 D1 and the foreign CodeRabbit data-point). Same signature, third distinct cause.
⭐ FALSE-absent CORROBORATED, not assumed: API-Sheriff PR #254 (merged, = repo HEAD 6ba8879) carries 7 coderabbitai / 1 cuioss-review-bot / 2 sourcery-ai comments. pr-agent DID review; the config could not see it.
⛔ 3 OF 3 TRACKED FILES STILL WRONG ON MAIN, re-derived this pass: TokenSheriff .plan/marshal.json:107, API-Sheriff :115, cui-http :103 - all `coderabbit,cuioss-review-bot`, ALL THREE WORKING TREES CLEAN. The plan-local fixes reached NO main and RE-FIRE on the next plan in each repo. ⚠ Denominator still UNKNOWN: ~21 org repos, 9 local checkouts - three is a FLOOR, never a total.
DISPOSITION: absorbed, NO spec written and NONE amended. PLAN-PR-044 already owns every ours-side limb (D0 name-the-mechanism, D1 validate-token-against-bot_kinds, D2 say-it-at-configuration-time, D3 discriminating-message). D0 is now FULLY SETTLED - mechanism (1), the login in the kind slot, other two rejected - and D1's target is the `classified` loop named above. ⛔ Spec NOT amended: its row is `running`.
⛔⛔ THE OPERATOR RELAY TO PLAN-PR-044 IS NOW MORE URGENT, and still the ONLY channel (`inbox write --target-plan` refuses a running plan by construction). Without it D0 re-derives from scratch what is settled here, and D1 is authored without knowing the exact loop it must fix.

### 2026-09-03 STATUS PASS at HEAD 902c23c52. ⛔⛔ THE PREVIOUS ANCHOR'S CENTRAL CLAIM IS REFUTED — READ THIS BEFORE THE CLEANUP BLOCK BELOW.
⛔⛔ PLAN-PR-038 IS RUNNING, NOT STAGED. The cleanup block below says "PLAN-PR-038 was EMITTED but never started - it is still `staged` and absent from manage-status list. The second slot is genuinely open." EVERY LIMB OF THAT IS FALSE AT THIS HEAD. Acting on it would have DOUBLE-LAUNCHED a live plan.
⭐⭐ DERIVED FIRST-PARTY, THREE INDEPENDENT CORROBORATIONS, none of them the ledger: (1) `manage-status list` — plan `review-packs-become-published-artifacts`, current_phase 6-finalize, in_progress, location worktree; (2) that worktree's `request.md` carries `source_id: .plan/local/orchestrator/review-apparatus/plans/PLAN-PR-038-review-packs-become-published-artifacts.md`, created 2026-09-02T15:54:14Z — so the identity is the SPEC POINTER, not a slug-name coincidence; (3) `ci pr list` — PR 1388 OPEN on `feature/review-packs-become-published-artifacts`.
LEDGER RECONCILED IN THIS PASS: PLAN-PR-038 staged -> running, plan_marshall_plan_id and pr 1388 stamped. ⚠ Recorded on DISK+CI evidence, NOT operator-confirmed — the emit≠running invariant's usual second half is absent here, and the row says so deliberately.
⛔⛔ R = 2 of N = 2. THE EPIC IS AT CAPACITY AND NO SLOT IS OPEN. `next` must emit NOTHING until PLAN-PR-038 or PLAN-PR-044 lands. Do not re-derive an open slot from the block below.
⭐ PLAN-PR-044 ALSO MOVED: 4-plan -> 6-finalize (worktree `misconfigured-reviewer-name-reads-missing-review`, branch `feature/misconfigured-reviewer-name-reads-missing-review` at 7fe7af247). NO PR YET — it is absent from the open-PR list, so 6-finalize here is PRE-create-pr. Its row stays `running` with pr empty, which is correct.
⭐⭐ THE GENERAL LESSON, AND IT IS THE EPIC'S OWN THESIS TURNED INWARD: the ledger asserted `staged` for a plan that had been running for a day, and a cleanup pass that scored 5-of-6 signals READY never caught it — because every signal it read was ledger-internal. A restart-check that never reads `manage-status list` cannot see a launched plan the ledger forgot. ⛔ ALWAYS cross-read the LIVE PLAN STORE against the queue before trusting any "slot is open" claim.
⚠ Both derivable epic.md blocks were verified byte-identical to `resume-summary` BEFORE this reconciliation and regenerated AFTER it. A decision-log entry `probe` (hash ba9c73) is a stray test write from this pass — ignore it, it carries no content.
⭐⭐ NEXT ACTION: nothing to emit. (a) Land PLAN-PR-038 (#1388) and PLAN-PR-044; (b) re-ground the five declined specs (PR-030, PR-038, PR-032, PR-028, PR-025B) — still the highest-value no-slot work; (c) the operator relay to PLAN-PR-044 named below is STILL OWED and still has no channel.

### 2026-09-03 CLEANUP DONE at HEAD 19453cb1b. RESTART VERDICT: NOT_READY - and that is TRUE STATE, not a defect.
restart-check: 5 of 6 signals scored. READY: phase, corpus_reconciliation, inbox (0 queued / 205 archived), worktree (clean at 19453cb1b). NOT_READY: running_plans - PLAN-PR-044 is genuinely running. registry_parity is not_available and EXCLUDED from the floor (PLAN-TRUTH-059's surface). ⛔ The verdict is not_ready because a plan IS running; the LEDGER is fully consistent and a restart is safe from the ledger's side.
⚠ R = 1 of N = 2. PLAN-PR-038 was EMITTED but never started - it is still `staged` in the queue and absent from manage-status list. The second slot is genuinely open.

PHASE A: corpus enumerate 48/48 BOTH directions, 0 rows_without_spec, 0 specs_without_row, 0 unreadable. Tally: 25 shipped / 18 staged / 3 retired / 1 parked / 1 running.
⭐⭐ METHOD CHANGED THIS PASS AND THE OLD ONE IS RETIRED - reuse the NEW one: intersect each spec's DECLARED Expected Surface (via `corpus surfaces`, the single shared reader) against `git diff --name-only {base}..HEAD`. ⛔ The former WHOLE-SPEC-FILE method is NON-DISCRIMINATING and must not be revived: it scores hits on prose mentions of CLAUDE.md and .plan/marshal.json, giving SEVEN spurious movers where the declared-surface method gives FOUR real ones. It was only ever chosen because two section parsers disagreed; corpus surfaces now reads 48/48 with 0 unreadable, so that reason is gone.
A1: 13 of 18 staged re-grounded - 12 corroborated, 1 unverifiable. PLAN-PR-039 is `unverifiable` BY CONSTRUCTION, not by omission: its surface is foreign-repo-only, so a plan-marshall diff can never reach that population. An unreachable population is NOT a refutation.
⛔ FIVE SPECS DECLINED, declared surface MOVED and NOT re-audited this pass - PR-030 (3/22 paths), PR-038, PR-032, PR-028, PR-025B. Left DELIBERATELY UNSTAMPED so the field stays ABSENT (which ADMITS) rather than carrying a verdict nobody checked. ⭐ Re-grounding these is the highest-value no-slot work available right now.
A2 nothing retired (no positive account). A3 no ambiguity across 48. A4 source_origin_match_count 0. A5 redistribution DECLINED, unchanged.
PHASE B: compacted, epic_changed FALSE, both blocks unchanged (idempotent), 3/3 invariants ok, 8 sections abstained ALL preserved_verbatim, unreachable_count 0, 8 relocation pointers all resolve, NEITHER migration rule fired.
⚠ SETTLED-NARRATIVE RELOCATION DEFERRED AGAIN - not confirmed this pass. Deferring is the safe branch. epic.md has GROWN substantially this session and is a strong relocation candidate whenever an operator will confirm.
PHASE C: archive_drain REFUSED - the PERMANENT documented default. ⛔ Never derive quiescence from a timer or a merge landing.

⭐⭐ NEXT ACTION ON RESTART: (a) confirm PLAN-PR-044's progress; (b) the second slot is OPEN - re-emit PLAN-PR-038 (it never started); (c) re-ground the five declined specs. ⛔ Before any emit, re-derive the live-plan collision set - and remember that axis is currently UNINFORMATIVE (live plans declare no footprint).

### 2026-09-03 FOURTH DATA-POINT (#693): IT IS A COORDINATED THREE-REPO SWEEP, NOT ONE PROJECT'S MISTAKE.
⭐⭐⭐ DERIVED, NOT ASSERTED - swept all 9 local checkouts under ~/git for required_bots:
  DEFECTIVE (3): TokenSheriff 05818bc4 (#693) · API-Sheriff 1c7308c (#249) · cui-http c7862d0 (#192) - all reading "coderabbit,cuioss-review-bot"
  CORRECT (1): plan-marshall, "pr-agent"
  NO KEY (5): cui-jsf-test-basic, cui-llm-rules, cui-open-rewrite, cuioss-parent-pom, nifi-extensions
⭐⭐⭐ ALL THREE DEFECTIVE COMMITS SHARE THE IDENTICAL SUBJECT: "chore(config): rename the pr-agent reviewer token to cuioss-review-bot". Three repos, three separate REVIEWED PRs, one wrong change, all landed. DELIBERATE AND COORDINATED - someone concluded the token should be the author login and rolled it out. It is not a typo and it WILL NOT STOP ON ITS OWN.
⛔⛔ THE ONE REPO THAT GOT IT RIGHT IS THE ONE THAT DEFINES THE REGISTRY. The sweep landed precisely where nobody could see `bot_kind: pr-agent` and `author_login: cuioss-review-bot` side by side. ⇒ The strongest possible argument for PLAN-PR-044 D2: the naming is confusing enough that a maintainer inverted it ON PURPOSE and three reviews agreed.
⛔ THE FIVE KEY-LESS REPOS ARE NOT A CLEAN BUCKET. An absent required_bots defaults EMPTY, and an empty required set makes the quorum VACUOUSLY SATISFIED - no required bot, so nothing can fail. A different posture, not a healthy one. Never count them as unaffected.
⚠ POPULATION IS A SAMPLE, STATE IT THAT WAY: 9 LOCAL CHECKOUTS, 4 configure the key, 3 of those 4 are wrong. The org fan-out is ~21 repos, so the true denominator is UNKNOWN and the three PR numbers prove only that the sweep visited AT LEAST three. ⛔ Never restate "3 of 4" without "of the locally-checked-out repos that configure it".

TWO OWED ACTIONS, AND ONLY ONE IS OURS:
  1. plan-marshall validates the token against the live registry = PLAN-PR-044, RUNNING. ⭐ This evidence does NOT change its deliverables - D1/D2/D3 were already right; only D0's scope grew, and D0's answer is now known.
  2. REVERT THE THREE REPOS. ⛔ NOT plan-marshall's write boundary and NOBODY OWNS IT. Tracked as debt here so it is not assumed someone noticed.
⛔ PLAN-PR-044 STILL CANNOT BE TOLD - running-row exclusion plus no orchestrator-to-running-plan channel. Operator relay is the only path and is now MORE urgent, because D0 would otherwise investigate one project while the reality is a fleet sweep.

### 2026-09-03 THIRD DATA-POINT (cui-http). 3 items, all corroborated first-party, 1 framing CORRECTED.
⛔⛔ (1) THE marshal.json DEFECT IS CUI-HTTP'S, NOT OURS - correct the report's "live defect on main". cui-http/.plan/marshal.json:103 reads required_bots "coderabbit,cuioss-review-bot"; PLAN-MARSHALL'S OWN reads required_bots "pr-agent" at :117 and is CORRECT. Introduced by cui-http commit c7862d0 (#192) "chore(config): rename the pr-agent reviewer token to cuioss-review-bot".
⭐⭐ THIS ANSWERS PLAN-PR-044's D0: mechanism (1) - the LOGIN was put in the kind slot. The stale-resolved-registry and unmapped-login arms are REJECTED. D0 no longer needs to investigate; it needs to RECORD.
⭐⭐⭐ AND IT IS WORSE THAN A TYPO, in the way that most strengthens the plan: the commit subject states the intent outright - a DELIBERATE rename - and it LANDED THROUGH A REVIEWED PR. Nothing in the config, the schema, or the review said required_bots takes a bot_kind. ⇒ PR-044 D2 (validate at configuration time) is the ONLY layer that could have caught it, because the human layer already looked and approved.
⛔⛔ THE RUNNING PLAN CANNOT BE TOLD, and this is a real gap not a formality: PLAN-PR-044 is `running`, the running-row exclusion forbids amending its spec, and `inbox write --target-plan` REFUSES a running plan by construction (undeliverable_to_running_plan). THE OPERATOR IS THE ONLY RELAY CHANNEL. If the relay does not happen, D0 will re-derive from scratch what was already known - the epic.md entry is the evidence it was known.
⚠ cui-http's TRACKED file is still wrong (only that plan's local snapshot was fixed) so it RE-FIRES on the next plan there. ⛔ Not our write boundary - an owed operator action, not a deliverable.

(2) CodeRabbit registry gap = ALREADY STAGED as PLAN-PR-046 (yesterday). Corroboration folded; expected surface unchanged (adds no file surface). ⚠ COUNT IT HONESTLY: one CHECKED instance (#194, re-derived here) plus one REPORTED (#193, NOT read) - not two checked. Consequence now named on the spec: the absent caused a LOOP-BACK and required the FORCE-DONE escape hatch.

⛔⛔ (3) NEW, AND IT FAILS TOWARD MERGING: a Sourcery HARD REFUSAL WAS CREDITED AS PARTICIPATION. Live text on #194 - "you've USED your own review budget of 250,000 diff characters for the last 7 days" - matches NEITHER registry pattern ("your pull request is larger than the review limit of", "reached your weekly rate limit of"): the wording is USED, the recognizer keys on reached/exceeded/hit. Full chain read at HEAD 30cd8aaf8: registry arm misses, structural arm keys on rate-limit phrasing, ENUMERATIVE ARM IS INERT (_github_pr.py:338, UNRECOGNISED_REFUSAL_MAX_CHARS = None), and the comment IS a review_body - a declared publish shape - so it falls through to the CREDIT path. Three arms miss, the fourth is disabled.
⭐ sourcery.md:50 declares rate_limit_class hard_quota, so a RECOGNISED refusal would have escalated immediately - correct for a 4-day weekly budget. The registry is right; only the RECOGNITION failed.
FOLDED onto PLAN-PR-043 D2 (into the EXISTING deliverable - no sixth added, the split-guard warning stands). Expected surface UPDATED in the same act: claimed_count 10 -> 11 (+sourcery.md), verified from corpus surfaces.
⭐⭐ PLAN-PR-043 NOW CARRIES BOTH DIRECTIONS AT ONCE: D5's false `declined` fails toward BLOCKING, D2's new limb fails toward MERGING. ⛔ A recognition change that cures one can loosen the other - controls are required in BOTH directions, not one.

### 2026-09-03 SECOND DATA-POINT (cui-http#194) CONFIRMED YESTERDAY'S HYPOTHESIS. STAGED AS PLAN-PR-046.
⭐⭐ ROOT CAUSE ESTABLISHED FIRST-PARTY, and ONE mechanism explains BOTH data-points. Re-derived via the CI abstraction against cuioss/cui-http: PR #194 carries THREE comments - sourcery-ai review_body (a size refusal, 250000 diff chars), coderabbitai issue_comment, cuioss-review-bot issue_comment - and CodeRabbit's ONLY comment is an issue_comment carrying `<!-- recent_review_start -->  No actionable comments were generated in the recent review. 🎉`.
⇒ coderabbit declares participation_evidence [review_body, inline] (coderabbit.md:41-43). ISSUE_COMMENT IS NOT A CREDITED SHAPE. A CodeRabbit clean review therefore earns NO participation credit BY CONSTRUCTION and resolves `absent`. ⭐ The epic's own thesis reproduced by OUR OWN REGISTRY: reviewed-clean and nobody-reviewed collapse into one signal, and here WE cause it.
⛔ THE EARLIER RUN'S NOISE-PRE-FILTER DIAGNOSIS STAYS REFUTED - recorded on the spec so it cannot be re-adopted. The string IS in ignore_patterns (coderabbit.md:47), but the noise drop is at github_pr.py:1551 INSIDE the finding-persistence loop (:1446) while participation is credited in a separate loop (:1313) that reads no noise predicate.

⛔⛔ THE FALSE WAIT IS AGENT-LEVEL, NOT PRODUCER-LEVEL. coderabbit's refusal_patterns are EXACTLY "Review limit reached" and "Review rate limited" - NEITHER matches the clean text - so no script arm classified it as a refusal. The plan inferred a quota window from an unexplained `absent` plus an awaitable_window rate class (coderabbit.md:58). The inference was wrong AND plausible; fix the producer's claim, not the waiter.
⛔⛔ D0 MUST NOT SIMPLY ADD issue_comment TO participation_evidence. CodeRabbit's WALKTHROUGH/SUMMARY comment is ALSO an issue_comment and is posted BEFORE any review completes, so a bare shape widening trades a false negative for a MERGE-WARD false positive. Credit on the STRUCTURAL MARKER (`<!-- recent_review_start -->`) - the same derive-the-set rule PLAN-PR-043 D2 already requires. A matched negative control (the walkthrough alone credits nothing) is mandatory.
⚠ UNCHECKED LIMB, recorded so it is not read as clean: whether OTHER bots publish a clean verdict in an uncredited shape. Sourcery carries the same participation_requires_update posture and was NOT checked. D0 derives it per bot.

⛔ NOT FOLDED ONTO PLAN-PR-026 despite sharing its exact title-subject: PR-026 already carries SEVEN deliverables (D0-D6), OVER the split guard. Recorded so the omission reads as a decision, not an oversight.
⭐ Corpus health after staging: 48 specs, blocking_count 0, unreadable_claim_section_count 0; PR-046 declarative, 9 claimed / 0 unresolved.
⭐ Queue (staged): 042, 046, 043, 045, 025B, ... with PLAN-PR-044 RUNNING.

### 2026-09-03 FOREIGN DATA-POINT (operator-relayed, explicitly NO LANDING). Absorbed, no spec amended.
⭐ THE OBSERVATION IS THIS EPIC'S THESIS IN ONE RUN: a CodeRabbit run that reviewed the EXACT merge tree - coverage stamp naming 4f8b0733a as both sourceCommitId AND coveredCommitId, kind reviewed, all 48 changed files, Merge Risk Minimal, both pre-merge checks passing - scored `absent`. Reviewed-clean and nobody-reviewed resolved to ONE SIGNAL. That is PLAN-PR-026's title, observed live.

⛔⛔ THE RUN'S OWN DIAGNOSIS IS REFUTED AT HEAD 30cd8aaf8 - DO NOT RE-ADOPT IT. It blamed the noise pre-filter consuming "No actionable comments were generated" (count_skipped_noise: 3). Limb 1 holds: that string IS in coderabbit.md:47 ignore_patterns. Limb 2 does NOT: the noise drop sits at github_pr.py:1551 INSIDE the FINDING-PERSISTENCE loop (:1446), while participation is credited in a SEPARATE loop (:1313) that consults NO noise predicate. The predicate's own docstring scopes it - "before each surviving comment is persisted as a pr-comment finding". ⇒ At this HEAD a noise-filtered clean review STILL CREDITS PARTICIPATION.
⭐ THE LIVE ALTERNATIVE (HYPOTHESIS, not established): coderabbit declares participation_evidence [review_body, inline] (coderabbit.md:41-43) and issue_comment is NOT a credited shape for it. A clean review published as an issue_comment is denied by the EVIDENCE-SHAPE GATE, not by the filter.
⛔ THE DISCRIMINATING CHECK, one read: the `kind` of the comment carrying the coverage stamp. review_body => something else is wrong and the entry is incomplete. issue_comment => the gate is the cause and the remedy is a REGISTRY question, not a filter question.
⚠ THIRD POSSIBILITY, do not skip it: the observing system may be on an OLDER CACHED VERSION. The registry-pin leak makes that the ORDINARY case - establish the observed system's version before treating any of this as a defect in current main.

⭐⭐ NON-CONVERGENCE ARCHETYPE, SECOND INSTANCE. Re-firing re-fetches the same comment, re-filters it identically, re-emits absent - all 5 iterations spent on an unchanging input. SAME SIGNATURE as PLAN-PR-043 D1 (trigger B cannot select the bot that gates), DIFFERENT CAUSE. The archetype: a retry loop whose input cannot change by retrying. ⛔ An iteration budget spent on a fixed input must be reported as NON-CONVERGENCE, never as exhaustion - worth its own detector.

✅ A CONTROL THAT WORKED, recorded because the defect sections are otherwise all failures. The override was minted through the DESIGNED mechanism: barrier flipped to `ask` mode (whose "Merge anyway" branch is the documented barrier-ask-override mint site), granted HEAD-BOUND against 4f8b0733a with evidence. ⭐ The gap-class binding was observed working LIVE - barrier-ask-override admissible for review-barrier-gap while pre-merge-consent read INADMISSIBLE for that same class, refusing to let a routine merge confirmation authorize past a participation gap the operator never saw. That is the matched POSITIVE control for PLAN-PR-015's merge-authorization work. ⛔ Do not let the density of defects here imply the barrier is broadly unsound; this limb is confirmed.

### 2026-09-02 OPERATOR PASTE (TokenSheriff run, RELAYED not drained). 3 items, 3 dispositions.
⛔⛔ THE RUN SAID "Both are in the epic inbox" AND THIS EPIC'S INBOX WAS EMPTY - inbox list: count 0, live_count 0, invalid_count 0, inbox_state present. The operator confirmed the messages are in TOKENSHERIFF'S inbox. ⇒ Consumer-repo review findings have NO PATH into this ledger and arrive only when a human relays them. ⛔ NEVER read "the inbox is empty" as saying anything about consumer repos.
  ⚠ MECHANISM IS A LEAD, NOT CORROBORATED: likely the CWD-keyed main-anchored store resolution (same family as the manage-lessons cross-repo hazard), so `inbox write --slug review-apparatus` from inside TokenSheriff creates a review-apparatus tree THERE. Reading TokenSheriff's store was DECLINED by the operator, correctly, so nothing first-party settles it. ⛔ Do NOT transfer this to a sibling epic until someone re-derives it from the resolver.
  ⭐ It explains something already in the record: truthful-signals-042.md came from the SAME TokenSheriff plan (refresh-identity-and-scope-defences, PR #682) and reached us ONLY via a hand forward.

1. FALSE `declined` FROM AN IN-PLACE RE-REVIEW -> FOLDED onto PLAN-PR-043 as D5. Expected surface updated in the SAME act; claimed_count 7 -> 10, verified from corpus surfaces (+bot-participation-contract.md, +pr-agent.md, +github_re_review.py). PR-043 now has FIVE deliverables - inside the split guard but approaching it, do NOT absorb a sixth.
   MECHANISM RE-CORROBORATED FIRST-PARTY at HEAD 30cd8aaf8: pr-agent declares participation_evidence [issue_comment, inline] over ONE persistent comment and participation_requires_update true because "a re-review EDITS that same comment in place" (pr-agent.md:96-100). The edited comment names no commit => head_sha_verified false => matched:true + head_sha_verified:false IS the `declined` member (contract:65, :349), whose documented remedy is "accept the decline (move the bot to optional, or record an operator merge-authorization)" (:354-358).
   ⭐⭐ THE REQUIRED BOT'S ORDINARY RE-REVIEW BEHAVIOUR RESOLVES TO THE ONE VERDICT THAT STEERS THE OPERATOR INTO MERGING UNREVIEWED.
   ⛔⛔ THIS IS NOT THE 5ec6d3 PERMALINK DEFECT AND #1368's FIX CANNOT COVER IT. contract:368-379 names this failure but attributes it to a NARROW RECOGNISER, remedy "widen WHERE the SHA may sit". There is NO SHA in the evidence to recognise. An ABSENT reference and an UNRECOGNISED one are different facts with different fixes; the contract states only the second.

2. CODERABBIT FABRICATED A FINDING - a `the the` typo present in NO revision - WITH A COMMITTABLE SUGGESTION ATTACHED. Recorded as an Open Defect, NOT STAGED (n=1, relayed).
   ⛔ The committable suggestion is what makes it different in kind: a wrong finding costs a triage decision; a one-click suggestion for a nonexistent defect invites APPLYING a change nobody found necessary.
   ⛔ Do NOT generalise to "CodeRabbit hallucinates" - the standing record is that it carries most of the actionable yield. ONE fabrication moves no rate.
   ⭐ ESCALATION CONDITION NAMED so it does not drift: a SECOND fabrication, or ANY observation of a fabricated suggestion being applied, promotes it to a spec. (The currency-blind gap was held under exactly this discipline and its trigger DID eventually fire.)
   ⭐ CHECK WHEN STAGED: confirm a committable suggestion cannot enter any auto-apply path before calling this only a reviewer-quality problem.

3. The Maven `central` reserved-id / grandparent-POM item is NOT this epic's - it is TokenSheriff domain, and its methodology limb (a spec asserting "no repository exists anywhere in the chain" after checking three POMs and missing the grandparent) is the derive-completeness-never-assert-it archetype. Recorded here only so its NON-routing is deliberate rather than an omission.

### 2026-09-02 OPERATOR: "Started both". CORROBORATED FOR ONE, NOT BOTH. R = 1 of N = 2.
✅ PLAN-PR-044 -> `running`, plan_marshall_plan_id stamped `misconfigured-reviewer-name-reads-missing-review`. Corroborated on disk BEFORE recording: manage-status list shows it at 3-outline, in_progress, location current, and the plan directory exists under .plan/local/plans/. That is why the row is `running` and not merely `launched`.
⛔⛔ PLAN-PR-038 IS NOT STAMPED AND MUST NOT BE. Nothing observes it: it is ABSENT from manage-status list (5 plans, none matching) and there is NO directory for it under .plan/local/plans/. Recording `launched` or `running` would assert a state no instrument reports - the exact failure this epic exists to remove. The operator's report is trusted as a report; it is not evidence the launch took.
⚠ CONSEQUENCE: R = 1 of N = 2, so a slot may still be GENUINELY OPEN. Do not read the emitted pair as two running plans.
⛔ THREE CAUSES ARE OPEN AND WERE NOT GUESSED BETWEEN: (1) phase-1-init has not yet written status - a race, re-check settles it; (2) the launch did not take; (3) it was started somewhere this list does not see. ⛔ manage-status list has NO scope flag (only --filter by phase), so "not in the list" is not the same as "not anywhere" - a checkout this session cannot see would look identical. Re-check before concluding.

⭐ NEXT ACTION: re-check `manage-status list` for PLAN-PR-038. If present -> stamp running + plan_marshall_plan_id. If still absent -> the launch did not take; re-emit its command.
⛔ RUNNING-ROW EXCLUSION NOW BINDS ON PLAN-PR-044: do NOT re-scope it, do NOT re-ground it, do NOT amend its spec while it runs.
⭐ PLAN-PR-042 still takes the first slot that frees - and if PLAN-PR-038 turns out NOT to have started, that slot is open NOW. ⛔ But 042 cannot fill it while PR-038 is unresolved: if 038 IS running unseen, 042 would collide with it in cuioss/pr-agent-settings. Settle 038's state FIRST.

### 2026-09-02 EMITTED THE PAIR: PLAN-PR-044 + PLAN-PR-038. N = 2, R = 0 at emit, 2 of 2 slots filled, shortfall EMPTY.
auto_emit is false, so BOTH `launched` transitions stay OPERATOR-CONFIRMED and nothing is running. ⛔ EMIT != RUNNING, and that holds for both commands.
Prep-ready from the parser: corpus verdicts blocking_count 0 over 47 specs, 47/47 claim sections parsed, unreadable_claim_section_count 0.
⚠ EVERY VERDICT IS STALE (stamped 7845a4b9a, HEAD 30cd8aaf8) and PLAN-PR-044 / PLAN-PR-045 carry NO verdict at all (field absent, which ADMITS). Staleness is REPORTED, never promoted.

⛔⛔ PLAN-PR-042 DEFERRED TO THE FIRST SLOT THAT FREES - operator-decided 2026-09-02, do not re-litigate. It is the pr-agent SUBSTANCE and it is deferred for a REASON, not by neglect:
  - collides with PR-044 on review_completeness.py + test/plan-marshall/automatic-review/ (CHECKED, n=2);
  - and would collide with PR-038 IN THE FOREIGN REPO - 038 publishes pack artifacts into cuioss/pr-agent-settings while 042 D1 runs a one-variable-at-a-time A/B in that same repo, so 038 would mutate the configuration 042 must hold constant.
  ⭐⭐ THE DURABLE RULE EARNED HERE: plan-marshall file disjointness says NOTHING about a foreign repo. Before pairing any two plans that both reach into pr-agent-settings (or any other foreign target), check the FOREIGN surface by hand - the gate cannot and will report silence.
  ⭐ A silver lining to record so the deferral is not read as pure loss: 038 lands the packs 042 will eventually A/B against, so running 042 afterwards is a better experiment than running it now.

⭐ NEXT ACTION: await operator-confirmed launch of one or both emitted plans, then record `launched` per plan (once each). When a slot frees, EMIT PLAN-PR-042.
⛔ BEFORE THAT EMIT: re-derive the live-plan collision set AND check the pr-agent-settings foreign surface against whatever else is then in flight.

### 2026-09-02 OPERATOR RAISED parallelization_scope 1 -> 2. ADJACENCY WATCH REOPENED. PAIRING NOT YET EMITTED.
⛔⛔ THE 2026-08-25 "N = 1 STANDS / DO NOT DO PAIRING ANALYSIS" DECISION IS SUPERSEDED. Every downstream note below that says "a full slot is steady state" or "intra-epic parallel-run review is RETIRED" was written under N = 1 and no longer binds. Read them as history, not as instruction.
Chosen pair: PLAN-PR-044 || PLAN-PR-038. Disjointness is CHECKED, not silent: PR-038's ONLY overlap rows are PLAN-PR-004 (retired, .pr_agent.toml) and PLAN-PR-022 (shipped ancestor, .pr_agent.toml + marketplace/targets/generate.py). ZERO overlap with any staged spec. Both sides declarative, admits_disjointness_check true.
⭐ ADJACENCY WATCH REOPENED per its own retirement clause (the clause discharging itself, not a reversal). ⛔ RECORDED AT REOPEN so nobody miscounts later: PR-044 || PR-038 is cross-MODULE disjoint (automatic-review + manage-config + marshall-steward vs marketplace/targets/ + .github/ + .pr_agent.toml), which is a WEAKER question than the original intra-directory one. A clean result is n=1 on a NEW question, NOT n=3 on the old. The original still has no negative control.
⛔ CONFOUND RECORDED AT PAIRING TIME: the cross-epic axis was BLIND (all 3 live plans declare no affected_files). A clean result is consistent with "no collision" AND with "a collision the instrument could not see". Do NOT resolve the watch on it.

⛔⛔ PLAN-PR-042 IS NOT IN EITHER SLOT, AND IT IS THE pr-agent SUBSTANCE. It collides with PR-044 on review_completeness.py + test/plan-marshall/automatic-review/ (checked, n=2), so it cannot pair with the head.
⛔⛔ AND 042 || 038 IS THE WORSE PAIR DESPITE BEING FILE-DISJOINT IN THIS REPO - a trap the gate structurally cannot see. PR-038 PUBLISHES pack artifacts INTO cuioss/pr-agent-settings; PR-042 D1 runs a one-variable-at-a-time A/B IN THAT SAME REPO. 038 would change the configuration 042 is trying to hold constant. ⭐ THE RULE: plan-marshall file disjointness says NOTHING about a foreign repo, and both plans reach into one. Check the foreign surface by hand before ever pairing two plans that touch pr-agent-settings.

⚠ THE "REMAINING pr-agent LEVERS" REGISTER IS UNSTAGED AND LIVES ONLY IN THIS ANCHOR'S PROSE - it was never promoted to a spec. Contents: handle_push_trigger + push_commands in a toml plus `synchronize` in the caller's types: (the fail-closed-gate half is CORRECTED/already excluded); and an /improve ORACLE at GATE level in the org workflow (PLAN-PR-026 scopes the same work locally). Operator asked where the pr-agent improvements are; this register is the part with no spec.

### 2026-09-02 INBOX DRAINED (analyze, no paste). 1 scanned = 1 archived + 0 invalid + 0 archive_failed.
Post-drain: live_count 0, closed_senders EMPTY, invalid_count 0, inbox_state present => the EMPTY state, NOT finished. `truthful-signals` has declared NO closure, so more messages are expected.
`truthful-signals-042.md` (kind finding, lifecycle live, forwarded from refresh-identity-and-scope-defences-002.md) -> STAGED as PLAN-PR-045 at queue position 4, behind PR-043. Surface declarative, 8 claimed / 0 unresolved.

⭐⭐ THE ACCEPTED CURRENCY-BLIND GAP'S OWN REOPENING TRIGGER HAS FIRED. bot-participation-contract.md's § "The currency-blind path for append-per-review bots" names two observations that reopen it; the first has now occurred with evidence.
⭐ NOTHING WAS TAKEN AT FACE VALUE - all five local claims re-corroborated first-party at HEAD 30cd8aaf8, AND the foreign observation the sender itself filed as an UNCORROBORATED LEAD was re-derived against cuioss/TokenSheriff#682 via the CI abstraction (--project-dir) plus `git -C`. It came back STRONGER than filed: CodeRabbit reviewed head 99c36992 at 20:26:12Z (review body names the range 379afb77...99c36992 verbatim), the head advanced to 82e6597d at 20:50:49Z (author AND committer date identical), and CodeRabbit's NEXT review body is 2026-09-01T07:30:21Z => a ~10.7-HOUR window with no review of the merge candidate. Its range 99c36992...cf8acb8 did eventually cover 82e6597d (verified ancestor) - the next morning.
⭐⭐ FIRST-PARTY LIMB THE MESSAGE DID NOT NAME: SOURCERY ALSO DECLARES participation_requires_update: false (sourcery.md:36). The affected population is TWO registered bots, not one. Read from the other side, pr-agent.md:428 says pr-agent is "today the ONLY bot that can reach participated_stale".
⚠ TWO LIMBS DID NOT SETTLE, and both are recorded as such on the spec: (1) the 20:51:18Z "Review limit reached" decline is ABSENT from the PR's current comment set, read two days post-merge - ⛔ NOT a refutation, such notices are transient and get removed; do NOT build a Done-when on it. (2) The three findings' reviewed_commit_sha stamps were NOT checked - that store belongs to the foreign plan. An unchecked limb, not a clean one.

⛔⛔ ONLY HALF OF PLAN-PR-024'S EXCLUSION IS DISCHARGED. It cited (i) nobody has observed the real publishing behaviour - NOW DISCHARGED - and (ii) the change needs sign-off across every consumer project whose required_bots names an append-per-review bot - STILL OPEN, and it is an OPERATOR decision, not a technical one. PLAN-PR-045 D1 is therefore a DECISION with rejected arms recorded; arms (a) unconditional currency test and (b) invalidate-on-force-push are BOTH gated on that sign-off, arm (c) disclosure-only is not.
⛔ DO NOT FOLD PR-045 INTO PR-043. PR-043 owns refusal recognition and the trigger-B selector; PR-045 owns a CONTRACT-DISPOSITION decision with a consumer-wide blast radius. Burying a decision inside a refusal plan hides it.
⭐ THE COMPOSE IS THE PART NEITHER PATH PREDICTS ALONE: the contract's "self-limiting" mitigation assumes the re-trigger is SERVED. Declined for quota, no new comment arrives and the stale credit stands. Rate-limit path (PR-043/PR-025B) x currency-blind path (PR-045) = false green.
⚠ THREE GREEN-LOOKING SIGNALS, ONE REVIEW: review_completeness `participated`, bot_completion `completed: true`, and a green CodeRabbit CI check are all satisfiable while the review is stale. Only the first is even about a review, and it does not say OF WHAT.

### 2026-09-02 OPERATOR PASTE: 2 FINDINGS FROM A USING PROJECT. PLAN-PR-044 STAGED AT QUEUE POSITION 2. R = 0 of N = 1, SLOT OPEN.
⭐⭐ NEW SPEC PLAN-PR-044 (WS-01) 'a misconfigured reviewer name reads as a missing review' - staged DIRECTLY BEHIND PLAN-PR-042, ahead of PLAN-PR-043. Surface declarative, 9 claimed entries, 0 unresolved, admits_disjointness_check true.
  STRUCTURAL CLAIM CORROBORATED FIRST-PARTY: nothing validates a required_bots/optional_bots token against bot_registry.bot_kinds(). Derivation named and re-runnable: two enumerations over marketplace/bundles + .claude + test (28 `bot_kinds()` call sites, 20 other `bot_kinds` references), and no hit validates the config lists. Participation is keyed by a bot_kind DERIVED from the author login, so a token outside that codomain can NEVER enter participated_bots and falls to `absent` - the state reserved for "this bot did not review". Eleven STATE_* constants, none meaning "the configured name matches no reviewer".
  ⛔⛔ THE REPORTED INCIDENT'S PROXIMATE CAUSE IS *NOT* ESTABLISHED, and this repo's own registry CONTRADICTS the naive reading: pr-agent.md maps `cuioss-review-bot` -> `pr-agent`, so the operator's stated pair should NOT mismatch here. D0 of the spec settles which of three mechanisms fired (login-as-token / stale resolved registry / unmapped login). Do NOT author the fix against a guess.
  ⭐ THE REMEDY SHAPE ALREADY EXISTS: `not_triggered` already refines `absent`. Follow it; do not add a parallel mechanism beside the eleven-state vocabulary. marshall-steward ALREADY builds its bot questions from bot_kinds(), so the wizard path cannot produce the mismatch - the asymmetry with a hand-edited marshal.json IS the entry point.
  ⛔⛔ OPERATOR-DECIDED 2026-09-02: PLAN-PR-044 IS PROMOTED TO QUEUE HEAD, displacing PLAN-PR-042 to position 2. This SUPERSEDES the 2026-08-30 operator-set head. Do not re-litigate and do not restore 042 to the head on the strength of that older note.

⭐ OBSERVATION 2 ABSORBED into the coverage Watch - no new work, no ship semantics. A HEAD-BOUND merge authorization over a one-statement delta, in a USING project: both required bots reviewed the substantive diff but NOT the final delta; sourcery (OPTIONAL) approved that delta; the queue re-tested against main. The machinery behaved AS DESIGNED - merge_authorization is HEAD-bound AND gap-class-bound ({head, gap_class, granted_over}), so the accepted gap is recorded structurally rather than only in prose.
⛔⛔ DO NOT ADD IT TO THE n=5 COVERAGE INVARIANT POPULATION - that invariant was derived over plan-marshall PRs and this is a using project. It is a partial COUNTER-instance (the required bots DID review) and a CONFIRMING one (the delta that actually merged was covered only by an optional bot) at the same time. Mixing the populations would let a foreign instance move a local invariant.

⛔⛔ THE LIVE-PLAN COLLISION SET WAS RE-DERIVED AND THE ANSWER IS A VACUOUS ZERO - do NOT read it as clear. corpus cross-check: epics_scanned 9, plans_scanned 3, 639 file overlaps = 492 corpus_spec + 147 sibling_epic_spec + ZERO live_plan; source_origin_match_count 0 (still NO true duplicates). BUT all three live plans sit at 1-init and declare NO affected_files (two field_not_found, one file_not_found), so the arm compared each spec against an EMPTY path set three times. SILENCE, not a checked negative.
  => Filed as an Open Defect and DELEGATED to truthful-signals as review-apparatus-023.md (a TRANSFER - removed from our work, retained here only as the derivation record). The asymmetry is the defect: cross-check publishes spec_surface_states[] for OUR specs and no candidate-side equivalent.
  ⚠ CONSEQUENCE FOR THE NEXT EMIT: the live-plan axis is currently UNINFORMATIVE. Any emit rests on the intra-corpus axis, the sibling-epic axis and N=1 - never on a checked live-plan negative.

⭐⭐ NEXT ACTION: EMIT - PLAN-PR-042 unless the operator promotes PLAN-PR-044. A slot is free (R = 0 of N = 1).
⛔ STILL QUEUED AND UNDRAINED: inbox truthful-signals-042.md (kind finding, lifecycle live, valid, created 2026-09-02T14:23:13Z). It was NOT drained this pass - this pass handled an operator PASTE, not the inbox. Drain it with `/plan-orchestrator analyze slug=review-apparatus` (no paste).

### 2026-08-31 CLEANUP DONE at HEAD 7845a4b9a. RESTART VERDICT: READY. Queue IDLE, R = 0 of N = 1.
restart-check: 5 of 6 signals scored, ALL ready (phase, running_plans, corpus_reconciliation, inbox, worktree). registry_parity is not_available and EXCLUDED from the floor - it is PLAN-TRUTH-059's surface, so an unowned check cannot veto a verdict this component can reach.
✅ ALL 16 STAGED SPECS RE-GROUNDED at HEAD 7845a4b9a (was 26645688b). All 16 stamped at claim-index 0; ZERO section-scope fallbacks. blocking_count 0, unreadable_claim_section_count 0. Do not re-ground again before the next landing.
⭐ METHOD (reuse): whole-spec-file intersection against `git diff --name-only 26645688b..HEAD` (197 paths), fail-closed. Basename matching stays DISCARDED as non-discriminating.
⭐ NEXT-PASS PRIORITY (derived intersection sizes): PR-030 12, PR-029 11, PR-026 8, PR-031/PR-028 7, PR-043/PR-035 5, PR-040 4, PR-042/025B/036/033/037 2, and THREE CHECKED NEGATIVES at 0 - PR-032, PR-038, PR-039.

⛔⛔ PLAN-PR-039 IS A NAMED EXEMPTION, NOT AN UNFIXED DEFECT - do not "correct" it. corpus surfaces reports indeterminate_count 2 and it did NOT move, which is CORRECT and accounted for BY NAME: PR-039's surface is FOREIGN-REPO-ONLY by design, so claimed_count 0 is the right reading, and inventing a plan-marshall path to move the metric would DESTROY WS-02's disjoint-by-construction property. The other indeterminate is PR-041, which is SHIPPED/terminal. The exemption and its consequence are now recorded IN the spec.
⛔ THE CONSEQUENCE, stated so nobody re-reads it as a check: the disjointness gate reads SILENCE for PR-039, not a checked negative. Its disjointness rests on the foreign-only property it DECLARES, never on the gate having compared anything. The two coincide for this plan; they are not the same fact.

CLEANUP DISPOSITIONS: A2 nothing retired (no staged spec could be given a POSITIVE account of what closed it - absence alone never settles applicability). A3 no ambiguity across all 45. A4 source_origin_match_count 0 over 9 sibling epics + 2 live plans => NO true duplicates; the 642 file overlaps are corpus-internal contention already tracked in Sequencing. A5 redistribution DECLINED (unchanged: splits belong at emit; PR-028's mandatory 540a/540b split still stands).
PHASE B: compacted, epic_changed FALSE, both blocks unchanged (idempotent), 3/3 invariants ok, 8 sections abstained ALL preserved_verbatim, unreachable_count 0, 8 relocation pointers all resolve. Marker migration: NEITHER rule fired.
⚠ SETTLED-NARRATIVE RELOCATION DEFERRED - operator confirmation was not sought this pass. Deferring is the safe branch; a wrong relocation is not. epic.md is ~1570 lines and IS a relocation candidate whenever an operator is willing to confirm.
PHASE C: archive_drain REFUSED - the PERMANENT documented default. No epic-wide quiescence signal exists; closed_senders is per-sender only and the sender population is open. ⛔ Never derive quiescence from a timer or from a merge landing - both are prohibited derivations.

⭐⭐ NEXT ACTION: EMIT PLAN-PR-042 (operator-set highest priority, queue head). A slot is free and the corpus is uniformly current.
⛔ BEFORE THAT EMIT: re-derive the live-plan collision set - plans_scanned is now 2, down from 4, so the 2026-08-29 reading is expired.

### 2026-08-31 PLAN-PR-025A LANDED (#1368) + 13-MESSAGE INBOX DRAINED. R = 0 of N = 1 -> A SLOT IS OPEN.
Merge corroborated FIRST-PARTY (ci pr view state=merged + git log on main), not taken from the paste: 31d42db871eb1ed6095868b42af85e8162ef4a8e. Row shipped, pr/landing stamped, landings/PLAN-PR-025A.md written.
Drain closure: 13 scanned = 13 archived + 0 invalid + 0 archive_failed. Post-drain live_count 0, closed_senders EMPTY, invalid_count 0 => the EMPTY state, NOT finished.

⭐⭐ NEXT ACTION: EMIT. A slot is open and the queue head is unchanged - PLAN-PR-042 (the required reviewer returns an empty list) is STILL the operator-set highest priority. PLAN-PR-025B is now UNBLOCKED (its dependency was 025A's D1, which shipped) and sits behind 043.
⛔ Re-derive the live-plan collision set before emitting; the 2026-08-29 result is EXPIRED - 025A, 1366 and 1369 have all landed since.

⛔⛔ TWO CORRECTIONS TO THE RUN'S OWN DIAGNOSIS - do not re-adopt the run's version:
1. `merge_state=unknown` is NOT a branch-cleanup producer failure. landing-check returned complete:false with merge_state the SOLE missing key, and the run blamed branch-cleanup for recording none of its four records_facts. But a SUCCESSFUL `ci pr view` on merged PR #1368 ALSO returns merge_state: unknown - GitHub stops reporting a mergeable state once merged. ⇒ A post-merge landing STRUCTURALLY CANNOT satisfy the completeness contract. That is a CONTRACT defect, FOLDED onto PLAN-PR-028 (whose title is literally 'a landing message that cannot outrun its merge'). ⛔ Fix it WITHOUT collapsing n/a and unknown - the merged case is a THIRD thing: observed, and the question no longer applies.
2. The false `auth_failed` is REAL and now ROOT-CAUSED: `ci_base.check_auth_cli` maps ANY non-zero `gh auth status` exit to auth_failed and discards BOTH streams (`returncode, _, _`). `gh auth status` validates over the network, so a transient failure is indistinguishable from unauthenticated - the probe collapses could-not-verify into not-authenticated. Blast radius is the whole summary: auth_failed is an UNANSWERED arm, so precedence rule 1 forced [FAILED] on a fully successful merged run. FOLDED onto PLAN-PR-036. ⭐ The CONSUMER IS CORRECT - fix the producer's claim, never the fail-closed barrier.
   ⚠ NOT reproducible at this HEAD (re-runs give success / no_pr_found / worktree_resolution_failed, all correctly discriminated). Structural misclassification CONFIRMED from code; the day's trigger is HYPOTHESIS pending the matched control.

⭐ NEW SPEC PLAN-PR-043 (staged behind 042): 'the re-trigger selector cannot reach the bot that gates'. Trigger B picks ONE bot by COMMENT RECENCY, but the gating bot is by definition the one that has not commented recently - so the bot whose remedy is a re-trigger is the one bot trigger B structurally cannot select, and the loop never converges. Plus: three refusal-recognition arms each missed the SAME CodeRabbit notice for a DIFFERENT structural reason, and TWO further unregistered bodies remain. ⛔ Widening the literal is the WRONG fix - recognise the wrapper shape or derive the set.

DRAIN DISPOSITIONS: -012 reconciled · -001/-009 staged as PLAN-PR-043 · -008/-010 PROMOTED to lessons 2026-08-31-08-001/-002 · -011 + -010's self-review class FOLDED onto PLAN-PR-030 · -013 FOLDED onto PLAN-PR-036 · -002/-003/-004/-005/-006/-007 DELEGATED to truthful-signals as review-apparatus-022.md (ONE consolidated message; a TRANSFER - they are removed from our ledger).
⭐ PLAN-PR-030 gained TWO self-review blind spots: a guard's own diagnostic fired a live false positive in the run introducing it and TEN self-review rounds missed it (CodeRabbit caught it); and diff-derived candidates cannot see a doc line the change made stale without touching, costing EIGHT convergence rounds.
⚠ Cost: 36h26m wall / 9.88M tokens / 221.87M billing, of which 6-finalize alone is 147.7M (67%) with 24h35m idle.

### 2026-08-30 TWO DEFECTS FILED. PLAN-PR-042 IS NOW THE EPIC'S HIGHEST-PRIORITY SPEC (operator-set).
⭐⭐⭐ PLAN-PR-042 'the required reviewer returns an empty list on a correct, full review' - STAGED AT THE HEAD OF THE QUEUE, ahead of PLAN-PR-025B. EMIT IT FIRST once a slot frees. R = 1 of N = 1 today (PLAN-PR-025A running), so nothing is emittable yet.
  ⛔ It is an INVESTIGATION, not a fix - the cause is UNKNOWN and the deliverable is evidence + a decision. D0 reproduce, D1 one-variable-at-a-time A/B, D2 decide with rejected arms recorded, D3 make a canned-empty required review a THIRD observable state.
  ⛔⛔ FIVE HYPOTHESES ARE ALREADY REFUTED FIRST-PARTY - DO NOT RE-INVESTIGATE THEM (all from run 33333426580, plan-marshall PR #1370):
     1. Model ladder fell through -> REFUTED: `Generating prediction with vertex_ai/gemini-3.7-flash`, the LEADING model, no fallback.
     2. Diff was clipped -> REFUTED: `Tokens: 203455, total tokens under limit: 256000, returning full diff`.
     3. Charter absent/not applied -> REFUTED: full domain-routed pack present, including 'Severity is not a reporting threshold' and 'There is no such bar'.
     4. Not triggered -> REFUTED: it ran and published; coverage 44 of 93 PRs.
     5. Yield degrades with diff size -> REFUTED: hit rate 0%/0%/11%/6%/0% across ascending size buckets; the two hits are 2200 lines/39 files and 754/13, and the larger sits ABOVE the empty median of 1942.
  => On a correct model, with the FULL diff, under a maximally permissive charter, pr-agent returned an empty list. Remaining live hypothesis = the model/prompt-schema itself. ⛔ n=1 run log, labelled HYPOTHESIS on the spec - D0/D1 exist to settle it, do NOT report it as established.
  ⛔ NEVER 'drop pr-agent' - one of its two findings is a SECURITY defect CodeRabbit did not file (cui-http #162, fail-open in the RFC 7239 Forwarded parser). D2 arm (c) coordinates with PLAN-PR-025B D7 (promote CodeRabbit).
  ⚠ D1/D2 are mostly FOREIGN-REPO work in cuioss/pr-agent-settings, fanning out to ~21 repos. Corroborate a landing against the FOREIGN PR.

⭐ PLAN-PR-037 ABSORBED THE SECOND DEFECT as a new D4 (fold, not emit - PR-037 still collides with a live plan on _findings_core.py): `_is_actionable` buckets issue_comment -> meta UNCONDITIONALLY while review_body gets a registry-driven per-reviewer test, so pr-agent's actionable_count is STRUCTURALLY 0.
  ⛔⛔ CONSEQUENCE BEYOND WRONG COUNTS: EVERY pre-2026-08-30 `actionable_count: 0` FOR pr-agent IS UNINFORMATIVE - zero by construction, not by measurement. Do NOT cite one as evidence that pr-agent produced nothing. The 2026-08-30 corpus pass, read at source, is the first measurement that could say.
  ⭐ The fix shape already exists: review_body's `_is_status_summary` is the registry-driven seam to extend. A canned-empty guide MUST still score 0 - matched negative control required, or an under-count is merely replaced by an over-count.

✅ WATCH CLOSED: the 3.7-flash entitlement PROXY (opened 2026-08-24). The closing evidence it demanded - the model line in a real review run log - has been read first-party. The WIF service account IS served the leading model. ⛔ This closure is the OPPOSITE of reassuring: it removes the ladder as an explanation for the empty reviews.

⭐ CORPUS PASS STAMPED: findings/2026-08-30-pr-agent-vs-coderabbit-multirepo.md. NEXT-PASS LOWER BOUND = 2026-08-30T20:16:39Z.

### 2026-08-29 PLAN-PR-025A IS RUNNING. R = 1 of N = 1 -> THE EPIC IS AT CAPACITY. EMIT NOTHING.
plan_marshall_plan_id: a-refusal-is-recorded-as-a-refusal-the-record. Operator-confirmed AND corroborated on disk before recording (manage-status list: current_phase 4-plan, in_progress) - which is why the row is `running` and not merely `launched`.
⛔ A FULL SLOT IS STEADY STATE, NEVER A SHORTFALL TO FIX. Do not emit, do not pair, do not run disjointness analysis. N = 1 is operator-confirmed and STANDS.
⛔⛔ RUNNING-ROW EXCLUSION NOW BINDS ON PLAN-PR-025A: do NOT re-scope it, do NOT re-ground it, do NOT amend its spec while it runs. Re-scoping a spec mid-execution changes the brief under a running plan.
⚠ 025A runs in location `current` (the MAIN CHECKOUT), while the three live sibling-epic plans run in worktrees. Phase-1's placement decision, recorded because it changes WHERE a cross-epic collision would land - not acted on.

⭐ NEXT ACTION WHEN IT LANDS: `/plan-orchestrator analyze slug=review-apparatus` (its inbox message, or a paste). THEN, and only then:
  1. PLAN-PR-025B becomes emittable - it has waited on 025A's D1 (the recovery branches on `cause` before `rate_limit_class`).
  2. Re-derive the live-plan collision set BEFORE that emit; the 2026-08-29 result expires as soon as any live plan lands.
  3. Re-ground 025A's successors against the new HEAD - a landing moves the tree under every remaining spec.

⭐ USEFUL WORK THAT NEEDS NO SLOT while 025A runs (do NOT touch 025A itself):
  - Re-ground the specs whose verdicts are stale, EXCLUDING PLAN-PR-025A. Every pre-2026-08-29 verdict predates HEAD a1cae6102.
  - PLAN-PR-028 still needs its mandatory 540a/540b split AND is blocked by a live-plan collision (manage-solution-outline.py, _orchestrator_inbox.py) - the split is safe to do now, the emit is not.
  - The branch-cleanup merge-queue precondition defect is still an unstaged one-sentence Open Defect.

### 2026-08-29 SPLIT DONE + PLAN-PR-025A EMITTED. R = 0 of N = 1, so the emitted plan fills the only slot.
⛔⛔ PLAN-PR-025 IS RETIRED AND SUPERSEDED - the mandatory split is DONE, do NOT redo it and do NOT emit PLAN-PR-025.
  PLAN-PR-025A (D0-D6, the record)  <- EMITTED, awaiting operator-confirmed launch
  PLAN-PR-025B (D7-D9, the recovery) <- STAGED, BLOCKED until 025A LANDS (depends on 025A's D1: the recovery branches on `cause` before `rate_limit_class`)
  Bodies copied BYTE-FOR-BYTE by anchored line-range extraction; partition verified over 10 load-bearing clauses, each in exactly one half. PLAN-PR-025 kept on disk as the audit record - AMEND THE SUCCESSORS, never it.
  Queue spliced IN PLACE so 025A inherits 025's first-staged position. 41 -> 43 rows. corpus enumerate 43/43, 0 both directions. blocking_count 0, unreadable_claim_section_count 0.
⭐ DECIDED, NOT ESCALATED: 025A keeps all seven of D0-D6 as ONE plan. The (a) D0+D1+D2 / (b) D3+D4 / (c) D5+D6 subdivision is retained as an INTERNAL ordering obligation, because D1-D5 all consume D0's three derived populations - three plans would either re-derive them three times (the exact hand-maintained-population defect this plan closes) or couple sub-plans to another plan's run report. Rationale is recorded on the spec, per the scope-bloat guard.
⛔ 025A's OWN carried obligations, still live: D3 MUST carry PR-027 D5's form statement forward (PR-027 shipped as #1356, so it IS in the tree - re-read those two blocks before editing); D2 is written against code PR-034 (#1344) restructured and must be re-scoped at outline; D5 owns the 5ec6d3 live false-decline defect and must fix the PRODUCER side (a SHA inside a commit URL), noting it fails TOWARD BLOCKING so a tightening-only fix makes it worse.
⛔ EMIT != RUNNING. auto_emit is false (default), so 025A's `launched` transition stays OPERATOR-CONFIRMED, and `running` is operator-observed in both cases. Nothing has been launched.

### 2026-08-29 INBOX DRAINED (analyze, no paste). 2 scanned = 2 archived + 0 invalid + 0 archive_failed.
Post-drain inbox: live_count 0, closed_senders EMPTY, invalid_count 0, inbox_state present => the EMPTY state, NOT finished. `truthful-signals` has declared NO closure, so more messages are expected.
Both messages were kind=finding, lifecycle=live, from `truthful-signals`. NEITHER was taken at face value - every material claim was re-derived first-party at HEAD a1cae6102 before any ledger write.

1. `truthful-signals-039.md` -> OBSERVED (absorbed into the existing coverage Watch; no new work).
   Sender explicitly labelled its figures OBSERVED-BUT-NOT-RE-DERIVED and asked for corroboration. Done, and ALL of it held: on #1361 pr-agent (cuioss-review-bot) posted 2 issue_comments BOTH EMPTY, CodeRabbit posted 20 rows carrying the entire actionable yield, and Sourcery posted 1 review_body refusal quoting "larger than the review limit of 150,000 diff characters" VERBATIM.
   => Coverage invariant n=4 -> n=5. PR size derived first-party: 2857 changed lines / 18 files (git show --shortstat 5f972ac15) - the cap bites FAR below what line count suggests.
   MECHANISM (does not decay with n): pr-agent is issue_comment-only so it can NEVER HEAD-bind through a check; Sourcery's refusal is HONEST but leaves that arm unreviewed while the barrier still resolves clean.
   NOT ESTABLISHED either way: whether Sourcery would have found anything under the cap - no counterfactual exists in either run.

2. `truthful-signals-040.md` -> FOLDED onto PLAN-PR-040 (D1, D2, D4, Claim Labels, Expected Surface). No new spec.
   CORROBORATED: emitter (:1965) and recognizer (:404) share ONE constant, so there is NO drift; the older "## Review responses" framing is REFUTED by a clean-coverage derived zero (0 hits, 5268 files scanned, 0 unreadable, not truncated); NOTHING detects an emitter bypass.
   THE REAL FINDING is a COUNTER-ARGUMENT to PR-040 D1/D2: the observed incident was a hand-authored BYPASS of `post_responses`, so the filter did its job. An author-identity re-key would make such a bypass INVISIBLE rather than mis-filed - D1 must CHOOSE that trade explicitly. A detection-preserving third arm and a call-site statement are both folded onto the spec.
   FIRST-PARTY LIMB the message did NOT name: the recognizer docstring (:390-394) makes the start anchor a LOAD-BEARING false-positive boundary, and cuioss-oliver is BOTH the emitter identity and a real reviewer (8 inline + 2 issue_comment on #1361), so a naive identity test swallows the operator's own review comments.
   THE MESSAGE'S OWN SECTION-3 CAVEAT IS CONTRADICTED: `ci pr comments` does NOT structurally exclude issue_comment - run first-party it returns inline, review_body AND issue_comment. D4 MAY use it. The unexplained foreign-repo zero is recorded as a FOREIGN-TARGETING question instead. Surviving D4 obligation: name the instrument, publish coverage as a derived figure.
   THREE stale line citations CORRECTED on the spec: :393->:404, :347->:358, and _github_pr.py:982->:1121/:1182/:1211 (the third was NOT named by the message and is the load-bearing one for D1).
   Two claim verdicts RE-STAMPED by review-apparatus/analyze at HEAD a1cae610273dfb29c1a8031974a48774649ef7a2, superseding cleanup verdicts that recorded themselves as "NOT re-verified this pass".

CROSS-EPIC COLLISION SET, DERIVED 2026-08-29 via `corpus cross-check` (9 sibling epics, 4 live plans, 302 candidates) - EXPIRES AS SOON AS A LIVE PLAN LANDS, re-derive before the next emit:
  THREE live plans are in the repo right now from SIBLING ledgers: `detector-and-auditor-integrity` (5-execute), `disjointness-gate-reads-declared-surface-wrong` (6-finalize), `findings-read-absent-plan-dir-returns-clean-zero` (6-finalize). N=1 is EPIC-LOCAL, so this is the live collision question - constraint C, not the retired intra-epic pairing.
  BLOCKED by a live plan (5): PR-028 (manage-solution-outline.py + _orchestrator_inbox.py), PR-029 (3 manage-findings files), PR-030 (2 ext-self-review files), PR-035 (_findings_core.py), PR-037 (_findings_core.py + its test).
  CLEAR of every live plan (9): PR-025, PR-026, PR-031, PR-032, PR-033, PR-036, PR-038, PR-039, PR-040.
  source_origin_match_count 0 => still NO true duplicates; the 527 file overlaps are corpus-internal contention already tracked in Sequencing.

NEXT ACTION UNCHANGED: EMIT - but the slot's rightful occupant is BLOCKED ON ITS OWN MANDATORY SPLIT, not on a collision. R = 0 of N = 1. Queue order still puts PLAN-PR-025 first (mandatory 025a/025b split, the 5ec6d3 live-defect fold, the PR-027 D5 preservation obligation).

### 2026-08-27 CLEANUP DONE. Queue IDLE - R = 0 of N = 1, nothing running. restart-check READY. blocking_count 0. HEAD 26645688b.
✅ ALL 14 STAGED SPECS RE-GROUNDED at HEAD 26645688b (up from 6 of 15 last pass) - the corpus is UNIFORMLY CURRENT for the first time. Do not re-ground again before the next landing.
⭐ NEXT-PASS PRIORITY (derived intersection sizes): PR-030 13, PR-025 12, PR-031/PR-026 11, PR-029/PR-028 9, PR-040 4, PR-036/PR-033 3, PR-035 2, PR-039/PR-037/PR-032 1, PR-038 0.
⭐ METHOD (reuse): whole-spec-file intersection against git diff --name-only {spec's own base}..HEAD, fail-closed (two section parsers disagreed on this corpus). Basename matching stays DISCARDED as non-discriminating. Two base shas: f6d058b4b (486 paths) and 1169fb5bf (248).

⚠ FLAGGED FOR OUTLINE, NOT RESOLVED: PLAN-PR-036 is the likeliest spec to be PARTLY DISCHARGED already - #1356 deliberately reworked the exit-code convention across all three SKILL.md surfaces it targets, which is its exact subject. Give it a POSITIVE ACCOUNT before scoping; do not assume the gap survives, and do not mark it fixed without one.
⭐ #1356 FIXED verification-feedback.md's pr-state defect (line 108 now carries the error_cause: no_pr_found discriminator) ⇒ one of PLAN-PR-030's four swept instances is DISCHARGED.
⭐ PLAN-PR-029's premise VERIFIED HOLDING: resolve_pending / resolve-only return ZERO in github_pr.py at HEAD, so D2's amended third requirement is still unlanded.

A4: source_origin_match_count 0 over 9 sibling epics + 2 live plans ⇒ NO true duplicates. The 532 file overlaps are contention already tracked in Sequencing, and at N=1 they are ORDERING, not pairing. A5 redistribution DECLINED - both mandatory splits (PR-025 025a/025b, PR-028 540a/540b) belong at emit.

⭐ NEXT ACTION: EMIT. Queue order puts PLAN-PR-025 first - it carries the mandatory 025a/025b split, the 5ec6d3 live-defect fold, and the PR-027 D5 preservation obligation.

⭐ BOTH 2026-08-25 AMENDMENTS TO PR-027 WERE EXERCISED ON THEIR FIRST RUN AND HELD (D2's widened test clause, D4's three-field routing_note). The 030 G7 settlement held too - no collision materialised.

⛔⛔ LIVE UNFIXED DEFECT, FOLDED ONTO PLAN-PR-025 D5: finding 5ec6d3 - github_re_review's head_sha_verified misses a SHA embedded in a COMMIT URL, manufacturing a false decline that would BLOCK A MERGE on a bot that did review. Overridden in 1356 on the branch's own precondition; live in main. ⚠ It fails TOWARD BLOCKING, opposite in direction to the rest of PR-025's defects - a tightening-only fix makes it WORSE.

⛔⛔ A VACUOUS GREEN INSIDE OUR OWN INSTRUMENT, FOLDED ONTO PLAN-PR-030: three self-review rounds each found one member of a class and published cohort_size 1 - a property of the SURFACER'S CANDIDATE LIST reported as a property of the tree. A directed sweep then found FOUR, including verification-feedback.md collapsing every ci pr view non-success into 'no PR exists' and returning a clean 'nothing to triage'. ⭐ And 12 of 19 bot findings were ONE archetype the in-run self-review had already passed - the blind spot is systematic, not accidental.

⛔ REVIEWER COVERAGE IS NOW n=5 (1340, 1349, 1356, 1359, 1361), folded onto PLAN-PR-026. #1361 added 2026-08-29 and FULLY RE-DERIVED FIRST-PARTY (pr-agent 2 empty issue_comments, CodeRabbit 20 rows carrying the whole yield, Sourcery 1 review_body refusing at the 150000-diff-character cap on a 2857-line/18-file PR). INVARIANT: the REQUIRED bot (pr-agent) contributed nothing in all four; an OPTIONAL bot carried whatever review happened. ⛔ Read it precisely - 1349's measurable population was ZERO so it supports no quality claim either way; 1356 and 1359 DO carry measurable reviews and the optional bot produced everything. The supportable statement is about COVERAGE AND ROSTER, not model quality: a required set of one whose member is reliably empty is a gate that cannot fail.

⛔ NEW OPEN DEFECT: branch-cleanup's merge-queue path documents SKIPPING the rebase, but the queue cannot accept a conflicting PR - the conflict-resolving rebase is a precondition the routing section does not name. Not staged (one sentence; PR-033 and PR-028 540b both touch that doc).
⚠ PIN GATE OPEN A THIRD CONSECUTIVE LANDING: executor 0.1.1561 vs registry installPath 0.1.1556. Steady-state leak confirmed. OPERATOR-ONLY repair.
⭐ THE 1349 LANDING-FACTS REGRESSION DID NOT RECUR (1356 complete true) ⇒ INTERMITTENT, not a removed feature. Narrows PR-028 D2's producer-side assertion. Recorded there.

✅ SUPERSEDED 2026-08-29 - PLAN-PR-027 LANDED as #1356 and is reconciled (row shipped, landings/PLAN-PR-027.md). Kept for its amendment record only: ⚠ ITS AMENDMENTS ARE UNTESTED - D2's test clause (widened from create-pr.md alone to all three widened docs) and D4's routing_note (three fields, not one) were amended 2026-08-25 and this is their FIRST execution. ⚠ 6 deliverables, at the guard, carries a recorded (a) D1+D2+D5 / (b) split for outline to honour.
⭐ NO-SLOT WORK: finish re-grounding the NINE stale specs (priority by intersection size: 027/028=10, 026=9, 029/031=8, 030=7, 036=3, 033/035=2, 032=1). ⛔ Do NOT re-ground PR-027 while it runs - running-row exclusion.

⛔ TWO LIVE DEFECTS FROM THE 1349 LANDING:
1. emit-landing emitted NO landing-facts block - complete false, ALL 8 keys missing, grep -c returns 0. A REGRESSION: PLAN-PR-034's landing one day earlier was complete true from the same step. Folded onto PLAN-PR-028 D2 with a PRODUCER-SIDE assertion requirement (nothing at the emit site notices).
2. PIN GAP RE-OPENED AT SIX VERSIONS - executor 0.1.1550 vs registry installPath 0.1.1544, after this run's sync minted v0.1.1550. OPERATOR-ONLY repair. NOT asserted as the cause of defect 1.

⛔⛔ NEW WATCH - TWO CONSECUTIVE PRs WHERE THE EXTERNAL REVIEWER SET CONTRIBUTED NOTHING while the barrier reported a completed round: 1349 first-party (0 comments, 1 empty, 2 refused; in-house self-review found FIVE real defects including a live lexicographic timestamp bug ranking -05:00 before Z) and 1340 forwarded (coderabbit credited on STALE evidence, sourcery reviewed nothing across six HEADs). ⭐ RE-FRAME: the failure mode is REFUSAL AND STALENESS, not reviewer quality - the lever is COVERAGE, not roster composition. Sizes PR-026 D3 and PR-025 D7. ⛔ n=2, NOT 'the bots are useless'.

✅ SUPERSEDED 2026-08-29 - PLAN-PR-024 LANDED as #1349 and is reconciled (row shipped, landings/PLAN-PR-024.md). The re-grounding cleanup it gated RAN on 2026-08-27.
⭐ USEFUL WORK THAT NEEDS NO SLOT, while it runs: finish re-grounding the NINE stale specs in the priority order below. All four proposed cleanup items are DONE.
⛔ Do NOT re-ground PLAN-PR-024 itself while it runs: the running-row exclusion forbids re-scoping a spec under a running plan.

STATE: 41 rows - 24 SHIPPED, 14 STAGED, 0 LAUNCHED, 0 RUNNING, 1 PARKED (PR-002), 2 RETIRED. (CORRECTED 2026-08-29 from resume-summary count divergences: the narrated 22/15/1-running predated the PR-024 and PR-027 landings, both of which ARE reconciled in status.json.) corpus verdicts blocking_count: 0 - THE CORPUS HAS NO BLOCKING VERDICT for the first time (PLAN-PR-028 re-authored 2026-08-25). Inbox: count 0, live_count 0, closed_senders EMPTY, invalid_count 0 ⇒ the EMPTY state, NOT finished.

### ✅ CLEANUP RUN 2026-08-25 - do not redo
ALL NINE PRE-EMIT AMENDMENTS ARE NOW DISCHARGED (6 at the PR-024 emit, 1/2/3/4/5/7/8 at cleanup). The cloud-wave-audit section 9 register is EMPTY except item 9 (PR-028's re-author). Highest-value: PR-029 D2's Done-when CERTIFIED the permanently-unresolved thread and was corrected; PR-025 D6's carve-out second limb was wide enough to swallow its own sweep; PR-026 D4 carried the exact string 040 G10 forbids.
✅ 030 G7 SETTLED, collision WITHDRAWN - PR-027 D5 owns it; PR-025 D3's Discharges line never named it. Recorded on both specs and epic.md. Survives as a PRESERVATION obligation on PR-025 D3 (whichever lands second carries the other's edit forward).
⚠ RE-GROUNDING IS PARTIAL AND THAT IS DELIBERATE: 6 of 15 staged specs re-grounded at HEAD 1169fb5bf (PR-025 + PR-040 first-party; PR-037/038/039 by empty intersection; PR-028 re-checked, still blocking). NINE STILL STALE: PR-026, -027, -029, -030, -031, -032, -033, -035, -036. Staleness is REPORTED, never promoted - none blocks. NEXT-PASS PRIORITY = derived intersection size: 027/028=10, 026=9, 029/031=8, 030=7, 036=3, 033/035=2, 032=1.
✅ PLAN-PR-028 RE-AUTHORED 2026-08-25 - DO-NOT-EMIT LIFTED, verdict rescoped yes, blocking_count 0. THREE landings had arrived since authoring not two (F1/F2/F3 split, 1317, and 1338 which is squarely D2's subject). STRUCK: D0 entirely (540b inherits NO gate) - D1's branch-cleanup edit - D2's degraded_keys list (1338 met the requirement by folding degraded values into missing_keys via _is_unsupplied; the BEHAVIOUR holds, only granularity differs) - D2's shared-source test. CORRECTED: D1's table re-keyed on merge_state ALONE (5 rows, replacing a 3-fact composite predating the F1/F2/F3 split) - vocabulary 3 to FIVE values, never collapse n-a with unknown - counts stated as FACTS (8 sites, 5 non-merging, 26 steps verified live) not as a HALT armed on the stale numbers. ABSORBED: the ad-hoc NO_PLAN landing defect, with a MATCHED NEGATIVE CONTROL required so the fix cannot be a blanket allow-list widening. ⛔ SPLIT IS MANDATORY: emit 540a (D4+D5+D6 020 items, ready, surface untouched) BEFORE 540b (D1+D2+D3+D6 080 items). NEVER emit PR-028 whole.
⭐ METHOD (reuse it): whole-spec-file intersection against git diff --name-only f6d058b4b..HEAD (286 paths), fail-closed because two section parsers disagreed on this corpus. Basename matching was computed and DISCARDED as non-discriminating - a floor of ~66 hits on nearly every spec from common names like SKILL.md.
⛔ STRUCTURAL FINDING: this corpus writes claim labels as TABLE ROWS, but the re-grounding verdict grammar attaches only as a nested child of a BULLET claim. So each spec carries exactly ONE verdict-bearing claim acting as a spec-level carrier, and PER-CLAIM verdicts are not expressible for table-form claims.

### WHAT SESSION 2 DID - do not redo
1. PLAN-PR-034 landing RECONCILED (paste mode). Row shipped, three result fields stamped, landings/PLAN-PR-034.md written. landing-check complete: true.
2. INBOX DRAINED - 22 consumed = 21 drained (14 PROMOTED to lessons 2026-08-25-09-004..09-017, 3 FOLDED, 3 OBSERVED, 1 DISCARDED) + 1 RECONCILED. Closure holds: 22 archived, 0 invalid, 0 archive_failed.
3. PLAN-PR-024 EMITTED with pre-emit amendment 6 APPLIED FIRST, and it was LOAD-BEARING: D2's ledger-reader bullet prescribed DROPPING a key-only row from the map, which 010 G8 names in as many words as the NON-FIX (an absent key takes the first-observation arm and credits the bot at any resolvable advanced HEAD). Replaced with G8's two sanctioned remedies. Done-when (c) retired from 'same verdict as an empty ledger' - which CERTIFIED the non-fix - to G8's wording asserting participated_stale.
4. THREE STANDING CLAIMS CORRECTED, verified first-party:
   - THE REGISTRY PIN GATE PASSES. MARSHALL_VERSION, registry installPath and the served skill base ALL read 0.1.1544. A sync minted 1543, but a 1544 mint followed WITH the registry pinned. POINT SAMPLE - keep checking each session.
   - PR-027/PR-030 do NOT collide with build-gates-test-suite. Its ACTUAL 6-finalize diff touches 7 files, none in this corpus. REFUTED at the diff.
   - PR-024 does NOT collide with plugin-doctor - shipped as 1343.
5. CLOUD-LANE RESIDUE: class 1 (build-gate ./pw verify) ALREADY FIXED by the prior normalisation - verified, NOT re-applied. Class 2 was LIVE, now APPLIED: PLAN-PR-027:577 vehicle rewritten to execution-context-{level} via the manifest.

### ⛔ OPEN DEFECTS AND WATCHES (detail in epic.md)
- OPEN DEFECT: PR-034 declared 5 files and touched 19. TEN staged specs claim the 14 undeclared ones. Root cause = a MISSING WRITE PATH after outline. ⇒ RE-GROUND before emitting anything after PR-024.
- OPEN DEFECT: an ad-hoc NO_PLAN landing can NEVER satisfy landing-check - n/a is legal only at pr and merge_state. STRUCTURAL. This epic shipped one itself (PLAN-PR-041). PLAN-PR-028 owns the contract but is unemittable as written.
- WATCH: the post-1130 pr-agent population is NO LONGER ZERO - n=4 (PRs 1336, 1337, 1338, 1343), EVERY pr-agent observation empty, coderabbit found the merge blocker twice. /improve n=2, both empty. ⇒ PROMOTE CODERABBIT (PR-025 D7), DO NOT DROP ANYONE - the 1335 counter-instance stands.
- WATCH: the split guard's review-coverage dimension is MEASURED - 179695 vs a 150000 cap, test/ 129556, non-test 50139 ⇒ a source/test split gets BOTH halves reviewed rather than neither.
- WATCH: a truncated CI fan-out SELF-HEALS on the next push - re-push before calling it a workflow defect.
- WATCH: PR-034 ships INERT (UNRECOGNISED_REFUSAL_MAX_CHARS is None) - WS-01's defect is closed in code and tests, not in observed runtime behaviour.
- WATCH: 6-finalize billing is 0.08x its tokens vs 12.6x-28.2x elsewhere, and the column SUMS TO THE PUBLISHED TOTAL so the total inherits it. Routed to truthful-signals.
- WATCH: the 3.7-flash entitlement proof is a PROXY - the HTTP 200 came from operator USER credentials, the workflow authenticates as a WIF service account. Closing evidence is the model gemini-3.7-flash line in a real review run log. Failure mode is bounded (ladder falls through to 3.6-flash).
- WATCH: the repo that CONFIGURES the third reviewer is the one repo it cannot review - cuioss/pr-agent-settings has no .github tree, so no workflow invokes pr-agent there. Structural, not a defect. Deliberately NOT staged.

### ⭐⭐ THE pr-agent CORPUS MEASUREMENT - and its expiry date
findings/2026-08-23-pr-agent-vs-coderabbit-corpus.md. 223 stores / 1353 records / 224 PRs after excluding 1689 pytest-scratch stores (local/worktrees/**, temp/pytest-basetemp/** - synthetic authors alice/bob/octocat). An unfiltered walk reports 2368/273, about 3/4 fixture data.
⛔⛔ THE CORPUS MEASURES A CONFIGURATION THAT NO LONGER EXISTS. pr-agent's last measured PR is 1129; the domain-routed charter landed at 1130 (f5493b437, this epic's shipped PLAN-PR-022) and /improve at 1334. ⚠ SUPERSEDED IN PART 2026-08-25: the post-1130 population is no longer zero - see the Watch above, n=4.
⛔ 'Do not spend another round on charter text' is QUALIFIED: it holds for EXHORTATION (pr-agent-settings 5 and 13 → silence 76.5% → 73.3%). It does NOT cover CONCRETE DOMAIN RULES, a different species with prior evidence FOR it (path_instructions: 4 valid findings of 5 on 1042). 1130 is UNTESTED, not refuted.
⭐ What still stands: paired recall - pr-agent said no major issues on 22 of 33 paired PRs, CodeRabbit had a repaired finding on 20 of those, and 47 of the 68 sat on the EXACT commit pr-agent reviewed (15 Major / 26 Minor / 6 Trivial / 0 Critical). Precision 6.1% vs 12.1% rejected. SIZES PLAN-PR-026. RE-CONFIRMS PR-031's blind spot.

### ✅ PR 1334 LANDED (f6d058b4b) - the /improve pilot
auto-improve: true, repo-scoped, operator-chosen (NOT org-wide). It ANNOUNCES an empty result (PR Code Suggestions / No code suggestions found), and 1334 added the matching ignore_patterns entry.
⛔ TWO TRAPS: the org command gate is startsWith (a /review after prose is silently ignored); pr-agent's re-review EDITS ITS COMMENT IN PLACE, so wait-for-comments gives new_count: 0 - read movement_matched_bots.
⭐ CodeRabbit = 1 review/hour - merge as-is once it has reviewed, do not add commits.
⛔ Observed live: merge_state clean + green CI while NOTHING had reviewed the merge candidate. Compare ci pr reviews / comment shas against git rev-parse HEAD before every merge.

### REMAINING pr-agent LEVERS
⛔⛔ CORRECTED - the synchronize lever does NOT need fail-closed-gate work. That was true at 1048/1053 and is now FALSE. Verified first-party in the org workflow: the gate's if: is an explicit allow-list - (pull_request AND auto-review AND action IN [opened, reopened, ready_for_review, review_requested]) OR (issue_comment AND startsWith(body, /review)) - so synchronize is ALREADY excluded. What remains: handle_push_trigger + push_commands in a toml, plus synchronize in the caller's types:. ⚠ Cost: a re-review is a FULL review, not a delta.
- An /improve ORACLE in the org workflow - the gate keys on the review output and is not extended to /improve, so GATE-level the two zeros are still one signal. Same work PLAN-PR-026 scopes locally.
- ⛔ NOT reachable by configuration at all: CodeRabbit EXECUTES verification scripts (ast-grep, rg, fd, python probes) against the tree before asserting. PR-Agent has no such facility, and repo_context_files supplies CONTEXT not INSTRUCTIONS. Full independence needs in-house gates (PLAN-PR-030).

### PLAN-PR-040 - our own comment is ingested as a review finding
⭐ MECHANISM CORROBORATED FIRST-PARTY before staging: github_pr.py:393 is body.lstrip().startswith(_SELF_RESPONSE_HEADING) with the literal '## Triage dispositions' at :347, so ANY comment we author opening with anything else is ingested as a review finding. An author-identity comparison already exists at _github_pr.py:982 (viewer_login) ⇒ the fix is a RE-KEY, not new plumbing. The docstring at :17 already concedes the filter cannot be complete - DOCUMENTED, NOT CORRECTED.
⛔ This corrupts PLAN-PR-035's 13 of 43 at BOTH ends - recorded on PR-035's spec: its D0 must ATTRIBUTE by author before reporting any ratio.
⛔ PR-040 is the SIXTH claimant of the github_pr.py family (PR-024, -025, -029, -034, -035) - derived from corpus cross-check, never counted by hand.

CLEANUP DISPOSITIONS (2026-08-23): A2 nothing already-fixed. A3 no ambiguity. A4 source_origin_match_count: 0 ⇒ NO true duplicates; file overlaps are contention already tracked in Sequencing; nothing superseded. A5 redistribution DECLINED (splits belong at emit; PR-028 must be re-authored). Archive drain REFUSED (permanent default - no epic-wide quiescence signal; closed_senders is per-sender only).

### 2026-09-02 EMITTED: PLAN-PR-044 (auto_emit false, so `launched` awaits operator confirmation).
R = 0 of N = 1 at emit; 1 of 1 slot filled, shortfall empty. Prep-ready from the parser: corpus verdicts blocking_count 0 over 46 specs, 46/46 claim sections parsed, unreadable_claim_section_count 0. Surface declarative, admits_disjointness_check true, 9 claimed / 0 unresolved.
⚠ EVERY VERDICT IN THE CORPUS IS STALE - stamped at 7845a4b9a, HEAD is now 30cd8aaf8. REPORTED, NEVER PROMOTED: staleness carries no admission consequence. PLAN-PR-044 itself carries NO verdict (field absent), which ADMITS - settling its verify-first clauses is the launched plan's own job.
⛔ THE DISJOINTNESS VERDICT RESTS ON TWO AXES, NOT THREE. Intra-corpus overlap is ORDERING at N=1 (operator-confirmed 2026-08-25, parallel-run review retired) and sibling-epic specs are not running. The LIVE-PLAN axis is UNINFORMATIVE this pass - see the vacuous-zero entry above. Do not record this emit as having cleared a live-plan check.
⛔ EMIT != RUNNING. Nothing is launched. Record `launched` only on operator-confirmed launch, and `running` only when the plan is observed started.

## Relocated resume-anchor blocks (2026-09-15 cleanup, operator-confirmed)

One dated block, moved VERBATIM out of the `resume_anchor` on 2026-09-15. Its subject is closed: the
two landings it reports are reconciled, `PLAN-PR-065` has since shipped (#1491), and its Phase-A
figures describe a 67-row corpus the 2026-09-15 pass re-derived at 68. ⛔ Nothing summarised or
dropped; the still-live items it carried (the plugin pin, the fail-closed marker gate, the `retired`
vocabulary gap, the standing owed list) are carried forward in the current anchor.

### 2026-09-13 CLEANUP DONE at HEAD 77cb2e251. Anchor RELOCATED (operator-confirmed). R = 1 of N = 2.

NEXT ACTION ON RESTART: (a) OPERATOR FIRST — repair the plugin pin, then FULL RESTART (see the pin block below); (b) PLAN-PR-061 is EMITTED and awaiting an operator-confirmed launch — record `launched` only when started; (c) PLAN-PR-065 is RUNNING (live plan pr-065-settings-repo-accumulates-never-lands, 5-execute) — await its PR, then `analyze` the landing.
⭐ THE SLOT MATH: N = 2, R = 1 (PLAN-PR-065 launched). PLAN-PR-061 fills the second slot and was emitted; it is the ONLY staged spec with ZERO live_plan collision rows over the 4 live plans (architecture-store-query-truthfulness, plan-truth-148, plan-truth-157, pr-065). Every other candidate is blocked by a live overlap; PLAN-PR-039 stays surface-indeterminate (prose, ADR-019 — silence is not a checked negative).
⛔⛔ THE PLUGIN PIN IS OPEN AGAIN — the predicted post-sync window, NOT the stale 2026-09-08 note. Gate `executor == installPath` FAILS: executor 0.1.1660, registry pins 0.1.1655 (18 entries / 10 keys). Both dirs currently unmarked, so nothing is inverted YET — the foreign GC will re-anchor markers on installPath and mark 1660. REPAIR ORDER IS MARKERS-FIRST, THEN REGISTRY (operator-only), then a FULL RESTART: nothing less re-seats skill bodies, and the executor was regenerated this session so the agent registry is session-pinned. `/marshall-steward` is advisory only (marshal.json provisioned 0.1.1636 vs installed 0.1.1660) and is never auto-mutated.
⛔ TWO LANDINGS RECONCILED THIS SESSION, and BOTH under-declared their footprint: PLAN-PR-033 #1473 (38af136ed, 2/2) landed 28 files against 14 declared — and the undeclared half SHIPPED PLAN-PR-056 D6 (head_sha_verified over the comment body), discharging a staged deliverable with NO ledger row moving. PLAN-PR-046 #1477 (77cb2e251, 5/5) modified 10 undeclared files. ⇒ THIRD consecutive landing with realized > declared. `reconcile-scope` detects it and NOTHING IN FINALIZE CALLS IT — unowned.
⛔⛔ THE SHIPPED MARKER GATE IS UNEXERCISED AND FAILS CLOSED — highest-risk open item. `recent_review_start` is ABSENT from CodeRabbit live summary comments, and `_is_participation_evidence` gates content with a BARE `in` test over the whole body (any occurrence anywhere satisfies it — quoted PR text included). A verdict comment that does not match resolves a clean review `absent`, which BLOCKS A MERGE. CodeRabbit raised it twice (b131a3, c847ec), both `taken_into_account`, never disputed. ⛔ The decline was CORRECT — do not anchor against an unsampled layout. SAMPLE FIRST: assigned to PLAN-PR-058 D0, which must publish the sampled population and its size before any anchoring decision.
⛔ THE QUEUE CANNOT EXPRESS `retired` — VALID_STATUS_VOCABULARY is {staged, launched, running, parked, shipped, landed} and `--transition` refuses `retired`, while 4 rows already carry it from the pre-single-row bulk writer. The 18 specs superseded by the 2026-09-12 redistribution are therefore recorded `parked`, which is SAFE (next walks staged only) but NOT TRUE. Real status lives in each spec header, the epic.md redistribution table, and decision.log. Filed to truthful-signals as review-apparatus-036.md.
⭐⭐ CORPUS SHAPE AFTER THE 2026-09-12 REDISTRIBUTION (operator-directed, split guard raised ~6 -> 12): 9 composed plans PLAN-PR-056..064 absorb 18 sources whole, pointer-composition — NO deliverable body was retyped, every source retained as authoritative text with a SUPERSEDED header. PLAN-PR-039 deliberately standalone (foreign-repo-only surface). PLAN-PR-065 staged 2026-09-13 for cuioss/pr-agent-settings (backlog + protection + docs + the publisher fix).
PHASE A 2026-09-13: `corpus enumerate` 67/67 BOTH directions, 0 rows_without_spec, 0 specs_without_row, 0 unreadable. Tally 33 shipped / 19 parked / 10 staged / 4 retired / 1 launched = 67. A1 BY DERIVATION: 1542 paths moved since 17906028b — a HUGE window — but only 6 were deleted or renamed (sync-opencode, CROSSING-INVENTORY.md, install-claude.adoc, terminal-title-architecture.md, a run-config test) and ZERO staged specs cite any of them. ⭐ The discriminator is the RETIRED-path set, not the moved count. A2 nothing retired (no positive account). A3 nothing to apply: blocking_count 0, unreadable_claim_section_count 0, the 3 prose specs are named and deliberate. A4 duplication — no action; the corpus was regrouped 2026-09-12. A5 redistribution DECLINED this pass: it was applied in full on 2026-09-12 and re-cutting a corpus twice in two days would churn a brief no reader has yet used.
⛔ ONE VERDICT STAMPED THIS SESSION, FIRST-PARTY: PLAN-PR-056 claim 3 = `contradicted` / `rescoped: yes` @ 38af136ed — github_re_review.py calls `_verifies_head_sha` over the comment BODY, so D6 premise is DEAD and D6 is re-scoped IN PLACE to the audit half. ⛔ The other staged specs were NOT claim-by-claim re-audited; their field stays ABSENT (which ADMITS) rather than carrying a verdict nobody checked.
PHASE B: settled-narrative relocation APPLIED (operator-confirmed) — six dated anchor blocks moved VERBATIM to settled.md § "Relocated resume-anchor blocks (2026-09-13 cleanup, operator-confirmed)". NOTHING DROPPED. The three STANDING blocks below are kept INLINE deliberately. ⛔ DO NOT RE-RELOCATE them.
PHASE C `archive_drain: refused` — the PERMANENT documented default. No EPIC-WIDE quiescence signal exists; closed_senders is per-sender only and the sender population is open. ⛔ Never derive quiescence from a timer or a merge landing.
⚠ INBOX IS AN ACTIVE CHANNEL, NOT A QUIET ONE: 17 messages drained across this session in three separate arrivals, including three foreign senders (truthful-signals, plan-truth-139). An empty queue is the EMPTY zero, never `finished` — no sender has filed a stream-end.
⛔ STILL OWED: TokenSheriff permanently merge-blocked (required_bots names the retired pr-agent kind); two ADR proposals await confirmation (79a483); the deploy-target/R4 divergence is DECIDED (skill adopts the executor invocation) and filed to truthful-signals as review-apparatus-039.md, needing the ./pw population DERIVED rather than the single site fixed.

## Relocated resume-anchor blocks (2026-09-13 cleanup, operator-confirmed)

Six dated blocks, moved VERBATIM out of `status.json`'s `resume_anchor` on 2026-09-13 under the
[Ledger-Compaction Stage](../../../../marketplace/bundles/plan-marshall/skills/persona-plan-orchestrator/standards/orchestration-model.md)
relocation rule. ⛔ **Nothing was summarised, reworded, or dropped.** Each block's subject is closed:
the 2026-09-08 block by the `PLAN-PR-033` (#1473) and `PLAN-PR-046` (#1477) landings, the five
2026-09-04 blocks by those landings plus the 2026-09-12 corpus redistribution. The three STANDING
do-not-re-derive blocks were NOT relocated and remain inline in the anchor.

### 2026-09-08 BOTH SLOTS FULL. R = 2 of N = 2. PLAN-PR-046 + PLAN-PR-033 LAUNCHED (operator-confirmed started).

NEXT ACTION ON RESTART: NOTHING IS EMITTABLE — no slot is free until one of the two lands. Await their PRs, then `analyze` each landing, which frees the slot that `next` then re-derives. ⛔ Do NOT run `next` expecting an emit; it will correctly report a zero-slot shortfall.
⭐ THE PAIR WAS RE-DERIVED AT HEAD 17906028b, not carried over: a queue-order walk of the 21 staged rows independently reselected 046 then 033 against a corpus that had since gained PR-054/PR-055 and retired PR-028. corpus surfaces 54 declarative / 3 prose over 57; corpus cross-check 9 epics, 1 live plan, 406 paths compared, 1415 overlap rows, source_origin_match_count 0, NO row pairing 046 with 033 either way and ZERO live_plan rows touching any staged spec; corpus verdicts blocking_count 0 over 344 claims / 57 specs, all 57 claim sections parsed.
⛔ RECORDED AS `launched`, NOT `running`, DELIBERATELY: orchestrate.md Step 4 counts R from `launched` ALONE, so promoting a started row to `running` would silently drop it out of the concurrency count and free an occupied slot. The operator's "started both" is recorded in decision.log instead. ⚠ That divergence is an UNOWNED DEFECT — the queue vocabulary carries `running` (cleanup's running-row exclusion and restart-check's running_plans signal both read it) while the only concurrency consumer reads `launched`; the two cannot both be right. Operator's call whether to stage it.
⛔ PR-033 IS AHEAD OF PR-054 BY DECISION, not by accident — PR-033's operator decisions bound what PR-054 (the foreign-PR-gate half of the retired PR-028) may implement, and the two collide on `foreign_pr_gate.py`. The older "PR-033 behind PR-028 D4/D5" ordering note is SUPERSEDED by that split.
⭐ THE REGISTRY-PIN ⛔⛔ BLOCK BELOW IS OBSOLETE — VERIFIED 2026-09-08: executor, installPath, cache dist-manifest and target dist-manifest ALL resolve 0.1.1624. Parity holds; no repair and no restart are owed. (Decision dd5f0c.)
⚠ Cleanup HEAD 9ba245149 is NOT an ancestor of HEAD — the merge queue rebased it into 17906028b (same subject, #1448). The corpus reconciliation is content-current; only the shas moved. PR-043 claim 4 (checked_at b64db6671) and PR-033 claim 0 (checked_at 19453cb) are STALE — reported, never promoted.
⛔ STILL OWED, unchanged: settled-narrative relocation DEFERRED pending operator confirmation (epic.md ~242 KB); once PR-032 landed, PLAN-PR-031 D5 items 1-3 and PLAN-PR-026 D6's lane item must be dropped BEFORE either is emitted; TokenSheriff permanently merge-blocked; two ADR proposals await confirmation (79a483).
⛔⛔ THE `ready` VERDICT DOES NOT COVER THE REGISTRY PIN. `restart-check` scored **5 of 6** signals; the sixth, `registry_parity`, returns `not_available` and is EXCLUDED from the floor — it is owned by `PLAN-TRUTH-059`. **The pin is 0.1.1592 against a cache/target at 0.1.1619.** A `ready` verdict here is a statement about the epic, not about the runtime. ⛔ Repair before relying on in-process `Skill:` dispatches: `.plan/temp/repair-plugin-pin.py --target 0.1.1619` (a VERSION, never a bundle name) then a **FULL RESTART** — nothing less re-seats skill bodies.
PHASE A: `corpus enumerate` **57/57 BOTH directions**, 0 rows_without_spec, 0 specs_without_row. Tally DERIVED from `status_tally`: 31 shipped / 21 staged / 0 running / 1 parked / 4 retired = 57.
A1 BY DERIVATION (the same method as the 2026-09-04 pass): **1005 paths moved** since `cc5ea40a1`. **19 of 20 staged specs had declared surface move; ZERO did not**; PR-039 is indeterminate by design (foreign-repo-only surface). ⭐⭐ **THE DECISIVE CORPUS-WIDE CHECK CAME BACK CLEAN**: only **2** paths were deleted or renamed in the whole window (both `marshall-steward` references) and **no staged spec cites either** — unlike 2026-09-04, where the `pr-agent.md` rename invalidated 11 specs. **A wide window is not the same as a dangerous one, and the discriminator is the retired-path set, not the moved-path count.**
⭐ ONE VERDICT STAMPED, FIRST-PARTY: `PR-043 claim 4 = corroborated @ b64db6671`. `github_re_review.py` sets `head_sha_verified` from `matched_signal == 'review'` in ONE hard-coded assignment, and `_references_head_sha` has exactly ONE call site inside the review branch ⇒ `head_sha_verified: true` is **UNREACHABLE** on the `issue_comment` path. ⛔⛔ **The relayed line number (571) AND this ledger's own prior note (394) BOTH failed to resolve at HEAD while the mechanism held — CITE THE SYMBOL, NEVER THE LINE.** ⚠ That verdict is now **stale by one commit** (HEAD moved to `9ba245149` mid-pass): reported, never promoted.
⛔ THE OTHER 18 MOVED SPECS WERE **NOT** CLAIM-BY-CLAIM RE-AUDITED, so their field stays **ABSENT (which ADMITS)** rather than carrying a verdict nobody checked. Same honest posture as every prior pass — a wide window licenses a derivation, not a claim of coverage.
A2 nothing retired (no positive account of a fix). A3 nothing to apply (`blocking_count` 0, `unreadable_claim_section_count` 0, the 3 prose specs are named and deliberate). A4 `source_origin_match_count: 0`; `file_overlap_match_count: 1317` is ORDERING material, not duplication.
⭐⭐⭐ A5 **APPLIED** — the long-standing `PLAN-PR-028` MANDATORY SPLIT was finally performed, source and destination enumerated: **`PLAN-PR-054`** (`540a`, the foreign-PR gate — D4 + D5 + D6's `020` items) and **`PLAN-PR-055`** (`540b`, the landing/PR-body half — D1 + D2 + D3 + D6's `080` items). PR-028's row is **retired** and its header carries a SUPERSEDED block. ⛔ **The file is NOT deleted and is NOT dead**: it remains the **authoritative text of every deliverable body**, and both halves POINT at it rather than retyping — retyping would be exactly the reconstruction drift this epic forbids at every other hand-off. ⛔ **`540a` BEFORE `540b`**, and `PLAN-PR-054` COLLIDES with the already-emitted `PLAN-PR-033` on `foreign_pr_gate.py` — prefer landing PR-033 first, since its operator decisions bound what 054 may implement.
⛔ A DEFECT IN MY OWN EARLIER FOLDS, FOUND AND FIXED THIS PASS: three deliverable blocks (`D5a`, `D6`, `D7`) had been appended to `PLAN-PR-043` using a `## Expected Surface` anchor, but that spec orders **Claim Labels BEFORE Expected Surface** — so ~15 KB of deliverable prose was sitting INSIDE `## Claim Labels`, and the claim parser stopped at the first non-bullet block, reporting 4 claims where 5 existed. Relocated into `## Deliverables`; the parser now reads all 5 and the verdict stamp succeeded. ⭐ **`corpus set-verdict`'s `claim_index_out_of_range` refusal is what surfaced it** — the fail-loud path did its job. ⛔ **Anchor a fold on the section it belongs to, never on the section that happens to follow it.** PR-050/-051/-052 were checked and are correctly placed.
PHASE B COMPACTED: both blocks regenerated (`resume-summary` 188→190, `ordered-queue` 26→28), **all 3 invariants `ok`** (`queue_spec_bidirectional` over 57/57, `no_terminal_in_live_queue` over 26 live rows, `relocated_pointer_reachable` over 10 pointers), `abstained_count: 8` all `preserved_verbatim`, **`unreachable_count: 0`**. `compaction_migrated[]` EMPTY — neither marker rule fired, which is the steady state once a ledger has been migrated.
⛔ SETTLED-NARRATIVE RELOCATION **DEFERRED, NOT SKIPPED**. The contract forbids applying that judgement silently and requires operator confirmation; a deferred relocation is safe and a wrong one is not. `epic.md` has grown 190 KB → ~240 KB since the 2026-09-04 relocation. **Offer it explicitly next session.**
PHASE C `archive_drain: refused` — the PERMANENT documented default, not a skip. No EPIC-WIDE emission-quiescence signal exists; `closed_senders` is per-sender only and the sender population is open, so a plan not yet emitted appears in neither `closed_senders` nor `live_count`. ⛔ Quiescence is NEVER derived from a timer or a merge landing.
PHASE D `restart_verdict: ready`, `sampled_at 2026-09-08T06:30:40Z`. Signals: phase=orchestrating ✅ · running_plans none over 57 rows ✅ · corpus_reconciliation 57/57 ✅ · inbox 0 queued / 289 archived ✅ · worktree CLEAN at `9ba245149` ✅ · registry_parity `not_available` (excluded).
CORPUS AT REST: `corpus verdicts` blocking_count 0 over 57/57 parsed, 0 unreadable claim sections. `corpus surfaces` 54 declarative / 3 prose, indeterminate_count 3.

### 2026-09-04 CLEANUP DONE at HEAD cc5ea40a1. Ledger RELOCATED (operator-confirmed). PLAN-PR-047 + PLAN-PR-048 staged.

⭐⭐ LEDGER RELOCATION HAPPENED THIS PASS — the 4-pass deferral is CLEARED. Operator confirmed; 28 settled anchor blocks moved VERBATIM to `settled.md` § "Relocated resume-anchor blocks (2026-09-04 cleanup, operator-confirmed)", each under its own `### {original header}`. Anchor 97,995 B -> ~22,000 B; epic.md 266,133 -> 189,934 B; START HERE 102,654 -> 26,446 B. ⛔ NOTHING DROPPED. 3 STANDING blocks kept INLINE deliberately (N=2 operator-confirmed; PLAN-PR-038/039 architecture SETTLED; STANDING (carried)). ⛔ DO NOT RE-RELOCATE those three.
PHASE A: corpus enumerate 50/50 BOTH directions, 0 rows_without_spec, 0 specs_without_row, 0 unreadable. Tally 27 shipped / 20 staged / 3 retired / 1 parked / 0 RUNNING.
⭐⭐ A1 METHOD, unchanged and still the right one: intersect each spec's DECLARED Expected Surface (via `corpus surfaces`, the single shared reader) against `git diff --name-only 19453cb1b..cc5ea40a1` (111 paths). 15 of 18 then-staged specs had declared surface move — a HUGE window, because #1388 and #1392 both landed on `automatic-review`.
⭐⭐⭐ THE DECISIVE CORPUS-WIDE CHECK THIS PASS: #1392 RETIRED `standards/pr-agent.md` (renamed `cuioss-review-bot.md`) and retired `bot_kind: pr-agent`. Swept ALL 50 specs — 11 cite the retired path, of which 3 are STAGED (PR-029, PR-031, PR-042) and were CORRECTED IN PLACE, membership-verified from `corpus surfaces` (not by cardinality). ⛔ The 8 shipped/retired citations were DECLINED — a shipped spec's surface has no consumer. ⚠ A spec declaring a path that no longer exists is a surface the disjointness gate CANNOT MATCH.
A1 verdicts stamped on PR-029 and PR-031 (claim 0, `corroborated`, checked_at cc5ea40a1, by review-apparatus/cleanup). ⛔ NOT stamped elsewhere: the other 13 moved specs were NOT claim-by-claim re-audited, so their field stays ABSENT (which ADMITS) rather than carrying a verdict nobody checked. Same honest posture as prior passes.
A2 nothing retired (no positive account). A3: 3 prose-surface specs (PR-004 retired, PR-041 shipped, PR-039 STAGED and deliberately indeterminate — foreign-repo-only surface, unpickable by construction, NAMED not inferred). A4 `source_origin_match_count: 0`; `file_overlap_match_count: 973` is ORDERING material, not duplication. A5 redistribution DECLINED, unchanged.
PHASE B: neither migration rule fired (both marker pairs present, no hand-written content between them) — steady state. `### Annotations` zone for resume-summary is absent and correctly NOT created (nothing to move). compact regenerated both blocks then idempotent; 3/3 invariants ok; 9 relocation pointers all resolve; 8 sections abstained ALL `preserved_verbatim`; unreachable_count 0.
PHASE C: archive_drain REFUSED — the PERMANENT documented default. ⛔ Never derive quiescence from a timer or a merge landing.
⚠ TWO INBOX MESSAGES ARRIVED MID-CLEANUP and were drained inline (truthful-signals is an ACTIVE sender — it has now sent THREE times in one day; never assume quiet).
⛔⛔ THE MOST IMPORTANT THING THIS PASS: `truthful-signals-045.md` §2.1 CONTRADICTED A FOLD I MADE EARLIER THE SAME DAY, and PLAN-PR-025B D10 IS CORRECTED IN PLACE. D10 read as though close-and-reopen BUYS BACK review capacity. IT DOES NOT — PR-level workarounds (close/reopen, new PR, force-push, new SHA) NONE touch an ACCOUNT-SCOPED quota. The two reports reconcile and the reconciliation IS the rule: the observed reopen worked because THE WINDOW HAD ALREADY ELAPSED (10+ hours), not because a fresh PR reset anything. CORRECTED POSTURE: while a bot is actively refusing for quota reasons DO NOT re-trigger; re-trigger EXACTLY ONCE, AFTER the window elapsed. A re-trigger inside the window RESETS it (50->59 min observed) and spends quota; the bot's ETA is an ESTIMATE not a contract (~2.4x then ~15x error). ⛔⛔⛔ That rule was written then VIOLATED ~6 HOURS LATER IN THE SAME EPIC — ~27 spam comments on a public PR, which exhausted the SEPARATE CHAT-MESSAGE quota and removed the recovery path. ⇒ D10 must ship as a GUARD, not guidance.
⭐ STAGED: PLAN-PR-047 (WS-03, D0-D4, 10 declared paths) and PLAN-PR-048 (WS-01, D0-D4, 11 declared paths). ⭐ PR-048 D4 is the SIBLING of shipped PLAN-PR-044 D1, NOT a duplicate: #1392 validated a token against the REGISTRY, D4 validates it against INSTALLED CALLER WORKFLOWS — a valid bot_kind can still be unwired here, and that failure presents as a TIMEOUT, the wrong diagnosis.
⭐ FOLDS with the same-act surface obligation discharged: 2.8 -> PLAN-PR-040 (filter must key on "a comment THIS WORKFLOW wrote", not author/reply; adds NO file surface — stated, not omitted); 2.4 -> PLAN-PR-045 (participated_stale does NOT TERMINATE — non-convergence archetype FIFTH instance; surface +2, membership-verified). 2.9 filed as a WATCH, not a spec.
PHASE D: restart_verdict was `not_ready` ONLY on the queued inbox message; that message is now drained. RE-RUN restart-check to get the post-drain verdict.
⭐⭐ NEXT ACTION: (a) BOTH SLOTS OPEN, R = 0 of N = 2 — but SEVEN specs gained surface today (025B, 029, 031, 040, 042, 043, 045, 046 + new 047/048), so RE-DERIVE the disjoint pair; the earlier PLAN-PR-042 + PLAN-PR-032 verdict is STALE. (b) The three unowned defects from the PLAN-PR-044/038 landings are STILL unstaged. (c) OPERATOR: `repair-plugin-pin.py --target 0.1.1592` + full restart; `/marshall-steward`; the two ADR proposals (79a483); TokenSheriff still merge-blocked.

### 2026-09-04 SECOND DRAIN — 1/1. Queue EMPTY again (NOT finished). PLAN-PR-047 STAGED.

`truthful-signals-044.md` arrived 08:29:22Z AFTER the first drain closed. scanned 1 / archived 1 / invalid 0. Disposition **staged** (kind=finding, ESCALATED not absorbed). Post-drain live_count 0, closed_senders EMPTY, invalid_count 0 ⇒ the EMPTY zero. ⛔ Still NOT "finished" — truthful-signals has filed no stream-end and has now sent twice in one day.
⭐ NEW SPEC PLAN-PR-047 (WS-03, D0–D4) "the counting stage reasons from inputs that were never persisted". Declared surface 10 entries, declarative, admits true, 0 unresolved (parser-verified). Corpus now 49/49 BOTH directions, 0 rows_without_spec, 0 specs_without_row, blocking_count 0.
⛔ NOT folded onto PLAN-PR-030 (already SEVEN items, over the split guard) nor PLAN-PR-043 (taken to six by THIS session's own earlier fold). Both omissions recorded as decisions.
⛔⛔ ONE SENDER CLAIM REFUTED BEFORE STAGING — and this is the reusable part. The sender claimed "the PR-Agent registry doc states this bot posts no inline comments at all". At 31d42db87 — THE REGISTRY VERSION THE SOURCE RUN ITSELF READ, predating PR #1386's merge (71279cc02, 2026-09-03T17:53:36Z) — the doc ALREADY declared BOTH shapes (issue_comment unconditional + inline under /improve) and said outright that a present inline count IS evidence of participation. ⇒ The observed record is what the registry PREDICTS, and the sender's consequence is BACKWARDS. ⭐⭐ THE METHOD THAT CAUGHT IT: check a registry claim against the version the OBSERVING RUN READ, not against current HEAD — the third-possibility rule already in this ledger, applied and paying off.
⭐ The INVERTED form survives as D4: the Guide issue_comment is declared UNCONDITIONAL yet ZERO issue_comment records were observed. Real mismatch, opposite direction.
⭐ Three claims verified FIRST-PARTY at cc5ea40a1 before staging: sourcery.md:20-22 (no review_body_summary_patterns; empty default keeps every review_body COUNTED), sourcery.md:51 (rate_limit_class hard_quota), github_re_review.py:394 ('head_sha_verified': matched_signal == 'review') — the last corroborating BOTH 9f7923 and our own e8bde7.
⛔⛔ THE SELECTION EFFECT, carry it regardless of any fix: finalize-step-simplify (order 8) and finalize-step-security-audit (order 9) mutate source AFTER the gates (5, 7) with no re-gate ⇒ THE ONLY MEASURABLE PRs ARE THOSE WHERE NEITHER STEP COMMITTED — the PRs that needed no fixing. A BIASED POPULATION, not a random sample. ⛔ A run of `excluded` rows means those PRs were NEVER MEASURABLE; it does NOT mean the gates were clean.
⭐⭐ NEXT ACTION: (a) inbox empty — but truthful-signals is an ACTIVE sender, re-check before assuming quiet; (b) both slots still open, and the disjoint pair needs RE-DERIVING (five specs gained surface this session: 031, 043, 025B, 046, plus new 047); (c) three unowned defects still unstaged; (d) operator: repair-plugin-pin --target 0.1.1592, /marshall-steward, ADR proposals (79a483), TokenSheriff merge-blocked.

### 2026-09-04 INBOX DRAINED — 20/20, THE OWED DRAIN IS DONE. Queue at the EMPTY zero (NOT finished).

✅ messages_scanned 20, archived 20, invalid 0, archive_failed 0 — closure equation holds. Post-drain live_count 0, closed_senders EMPTY, invalid_count 0 ⇒ the **EMPTY** state. ⛔ NOT "finished": neither sender filed a stream-end marker, so more messages ARE expected. Do not read this zero as closure.
⭐ 15 PROMOTED to the global lessons corpus as 2026-09-04-08-001 … -015 (bodies set and verified; the `add` verb returns the id as `id:`, NOT `lesson_id:` — a first attempt parsed the wrong key and allocated 15 empty lessons before the bodies were written, so re-check the key if you automate this again).
⭐ 3 FOLDED with the same-act surface obligation discharged on every one: rpp-015 -> PLAN-PR-031 D6 (a posted disposition is a promise nothing re-checks against what landed; +3 entries, claimed_count 8 parser-verified); rpp-009 -> PLAN-PR-043 D6 limb A (the rate window is a RETRY POLICY — per-attempt interval + attempt ceiling — not a flat timeout; +3, claimed_count 14); truthful-signals-043 split THREE ways as its sender intended — item 1 -> PLAN-PR-025B D10 (close-and-reopen on the SAME branch/HEAD is the recovery that worked: a time-based refusal and an event-based loop-back DO NOT MEET), item 2 -> PLAN-PR-046 D3 (+2, claimed_count 11), item 3 -> PLAN-PR-043 D6 limb B (pr-agent does NOT trigger on `synchronize`, so push-then-wait has no satisfying event; `pull_request_runs` `not_triggered` is the fail-fast).
⭐⭐ truthful-signals-043 item 2 IS e8bde7 REACHED FROM THE OTHER SIDE — an in-place republish read as `declined`, seen in TokenSheriff and CORROBORATED FIRST-PARTY on our own #1388. Two independent observations of one mechanism. ⛔ The foreign PR ids are LEADS, not corroborated in this checkout.
⭐ 2 DISCARDED, NEITHER DROPPED SILENTLY: mrn-003 = dedup (already Open Defect (b), recurrence recorded on the existing entry); rpp-016 = REFUTED — it claimed findings die with the plan directory, and the store is intact with all 8 hash ids resolving on the first read. Its PROPOSAL (a carry-out route) names a real gap; its PREMISE is false.
⛔ TWO STALE-SURFACE CORRECTIONS made in the same pass: PLAN-PR-031 and PLAN-PR-043 both declared `standards/pr-agent.md`, RETIRED by #1392 — corrected to `standards/cuioss-review-bot.md`. ⚠ A spec declaring a path that no longer exists is a surface the disjointness gate cannot match; the rename may have left OTHER specs stale — not swept this pass.
⚠ PLAN-PR-025B's surface is STILL unverifiable from the parser — it collapses onto plan_id PLAN-PR-025 under the known 025-family defect. Its +4 fold entries were written but `corpus surfaces` cannot attribute them. PRE-EXISTING, not introduced by the drain.
⭐⭐ NEXT ACTION: (a) the drain is DONE — do not re-queue it; (b) both slots still OPEN, PLAN-PR-042 + PLAN-PR-032 remain the derived-disjoint pair (re-verify, since four specs just gained surface); (c) stage the three unowned defects; (d) operator: repair-plugin-pin --target 0.1.1592, /marshall-steward, the two ADR proposals (79a483), TokenSheriff still merge-blocked.

### 2026-09-04 PLAN-PR-038 RE-PASTE. The ship was ALREADY reconciled last pass from inbox msg 017 — this block is the NEW material only.

⭐⭐⭐ THE EIGHT "UNREACHABLE" FINDINGS WERE RECOVERED. THE PREMISE IS REFUTED: the store did NOT die with the plan directory. `.plan/local/archived-plans/2026-09-03-review-packs-become-published-artifacts/artifacts/findings/` is INTACT (13 jsonl files) and ALL 8 hash ids resolved on the FIRST read, every one `resolution: pending`, `promoted: false`. ⛔ THE MISSING THING WAS A ROUTE, NOT THE DATA — THE CARRY-OUT IS A READ. Never again conclude that archival destroys findings.
⭐⭐ TRANSFER, NOT OFFER — six non-review findings filed into `truthful-signals` through the sanctioned `inbox write` channel (`sender_type: orchestrator`): 18f362 -> review-apparatus-025.md, 1d5140 -> -026, 1f0c43 -> -027, 5a5761 -> -028, c8e4a9 -> -029, d4501c -> -030. Each is now enumerable in THAT epic's queue and no longer depends on this ledger being read. e8bde7 STAYS here (PR/review, already recorded). 79a483 is an OPERATOR action.
⭐⭐ THREE OF THE SIX INDEPENDENTLY REPRODUCE ARCHETYPES ALREADY ON RECORD, which raises their weight: c8e4a9 (ERROR severity) confirms lesson 2026-09-02-21-002 THAT HOUSEKEEPING HAD JUST RETAINED AS NOT COVERED, with live pids — a killed pytest master left TEN xdist workers running; 5a5761 is a SECOND independent observation of `affected_files` under-recording; d4501c is the VACUOUS-GUARD archetype verbatim (`verdict: clear` over `commitments_considered: 0`).
⛔ 79a483 IS WHY `adr-propose` IS `skipped`, NOT `done` — Step 5 needs an AskUserQuestion per proposal and a dispatched leaf cannot reach the operator. TWO proposals await operator confirmation (published-artifact-set orthogonality; fan-out CLI parameter is a request not a contract). Decision-log entry abe291.
⛔⛔ NEW DEFECT — 100% COVERAGE OVER A SET THAT EXCLUDES THE WORK. All 5 deliverables reported 100% of their DECLARED paths while 12 of 23 landed files sit OUTSIDE every declared surface (the build-server `--timeout` work landed under a deliverable scoped to `marketplace/targets/pr_agent`). Recall over the DECLARED set is STRUCTURALLY INCAPABLE OF FALLING. Instrument-reports-perfect archetype = the literal subject of staged PLAN-PR-030, and it COMPOUNDS 5a5761 (same union that cannot learn unpredicted paths).
⚠ COST: 4.06M tokens vs a 2.5M anchor (1.63x), 86.2M billing-weighted; 6-finalize alone 48%; ONE ERRORED DISPATCH RETURNED NOTHING FOR 344K. ⛔ An `error` is not "produced nothing" — it is produced-and-discarded, and it bills.
⚠ CodeRabbit was the ONLY measurable reviewer (8 actionable / 8 fixed / 0 rejected). The gate-delta is EXCLUDED, NOT CLEAN — the loop-back left two reviewed trees so no single `reviewed_commit_sha` exists. Do not read the exclusion as a passing comparison.
⚠ TWO RUN SELF-CORRECTIONS, recorded so neither reads as settled: the merge mutex was NOT held through the landing (lapsed; another plan holds it; the queue serialized the merge regardless), and `branch-cleanup` was first marked done WITHOUT its typed facts, which `emit-landing` reads directly.
⛔⛔ PLUGIN PIN — CORROBORATED AND WORSE THAN THE PASTE SAID: `installPath` pins 0.1.1585 but the cache now holds up to **0.1.1592**, not 1591 (two further versions landed with #1392/#1393). REPAIR IS OPERATOR-ONLY: `python3 .plan/temp/repair-plugin-pin.py --target 0.1.1592`; only a FULL RESTART re-seats skill bodies. ⚠ Build-daemon reconcile owed x1 (deferred, build in flight).
⚠ Inbox here: 18 live messages remain (all candidate-lesson except the truthful-signals finding); msg 017 was archived last pass. The drain is still owed.

### 2026-09-04 DISJOINTNESS RE-DERIVED at cc5ea40a1 — the block below said "re-derive first"; THIS IS THE ANSWER, do not redo it.

⭐ BOTH SLOTS FILLABLE: PLAN-PR-042 + PLAN-PR-032. Derived, not judged. corpus surfaces: both `declarative` (tally 45 declarative / 3 prose / 0 derived / 0 absent / 0 unreadable over 48; indeterminate_count 3). corpus cross-check (epics 9, live plans 4, specs 48, comparable 45, indeterminate 3, compared_path_count 294, file_overlap_match_count 890, source_origin_match_count 0): NO overlap row pairs 042 with 032 either way, and NEITHER appears in any live_plan row. corpus verdicts: blocking_count 0 over 290 claims / 48 specs, unreadable_claim_section_count 0.
⭐⭐ CORRECTION TO A STANDING NOTE BELOW: THE LIVE-PLAN AXIS IS NO LONGER UNINFORMATIVE. cross-check returned 10 live_plan rows this pass (vs planning-lane-change-type-scope-execution-manifest, shipped-guards-assume-the-meta-projects-own-layout, preference-admissibility-prose-vs-auditor-code). Live plans DO declare footprint now — stop recording that axis as vacuous.
⛔ NO SECOND CANDIDATE FROM THE REVIEW-SIGNAL CLUSTER: PLAN-PR-042 collides intra-corpus on 29 rows (043, 045, 046, 026, 031, 037, 044, 034, 025, 025A, 017, 016, 014). 032 qualifies only because its surface is the cloud-plan-lane contract, not automatic-review.
⛔ PLAN-PR-039 IS NOT EMITTABLE — surface `prose`, indeterminate: no comparable path declared, so its clean reading is SILENCE, not a checked negative (ADR-019).
⛔ auto_emit = false, so NOTHING was recorded `launched`. EMIT != RUNNING.
⚠ THE FORK, SURFACED AND NOT DECIDED: the three NEW unowned defects (TokenSheriff permanently merge-blocked by our own rename; D5's false-green foreign propagation; head_sha_verified unreachable for pr-agent) plus the 20-message drain are arguably higher-value than either staged candidate. Operator's call.

### 2026-09-04 TWO LANDINGS RECONCILED. R = 0 of N = 2 — BOTH SLOTS OPEN. Everything below this block is HISTORY.

✅ PLAN-PR-044 SHIPPED #1392 (merged cc5ea40a1, 6/6 deliverables, 7.93M tokens / 64.2M billing) — landings/PLAN-PR-044.md.
✅ PLAN-PR-038 SHIPPED #1388 (merged ef974632c, 5/5, 4.06M tokens) — landings/PLAN-PR-038.md. ⛔ THIS ONE WAS NOT IN THE OPERATOR'S PASTE; found by cross-reading `git log` + `manage-status list` and corroborated at the PR. ⭐⭐ SECOND TIME IN TWO SESSIONS the live plan store held a truth the ledger did not — ALWAYS cross-read it.
Both landing-check `complete: true`, both messages archived. Queue: 27 shipped / 16 staged / 3 retired / 1 parked / 0 running.

⛔⛔ THREE NEW DEFECTS, ALL UNOWNED BY ANY STAGED SPEC — these are the highest-value new work:
1. THE RENAME BROKE TokenSheriff. #1392 retired `bot_kind: pr-agent` (pr-agent.md -> cuioss-review-bot.md); the kind set is now {coderabbit, cuioss-review-bot, sourcery}. TokenSheriff #699 "correct required_bots" set `coderabbit,pr-agent` at 2026-09-04T00:13:27Z — 1h41m AFTER #1392 merged at 2026-09-03T22:32:44Z. It is now PERMANENTLY MERGE-BLOCKED by the very mechanism PR-044 fixed. ⭐ The shipped `unregistered_kind` state is what makes it diagnosable — the instrument works, the fleet is out of step. ⛔ DURABLE GENERALISATION: renaming a bot_kind invalidates every consumer config fleet-wide and NO PROPAGATION MECHANISM EXISTS.
2. D5's FOREIGN PROPAGATION DID NOT HAPPEN, and its corroboration was FALSE-GREEN. The landing cited #249/#192/#693 as merged — those are the ORIGINAL DEFECTIVE SWEEP PRs from 2026-09-02, not this plan's deliverables. Re-derived per repo: EXACTLY ONE checkout changed (plan-marshall -> `cuioss-review-bot`). API-Sheriff and cui-http hold the post-rename-correct value BY ACCIDENT OF THE SWEEP; TokenSheriff is wrong. ⛔ This is the recorded "corroborate a foreign landing against the FOREIGN PR" failure in its exact form — and defect 6 below (the foreign gate that can never pass) is WHY it went unexamined.
3. `head_sha_verified` IS UNREACHABLE FOR pr-agent (finding e8bde7). PLAN-PR-038 cleared its barrier by AUTHORIZATION, not participation — `participation_complete: false`, unproven [pr-agent, sourcery], HEAD-bound barrier-ask-override at 0a6fa35f7. `head_sha_verified` derives from the signal TYPE, and pr-agent re-reviews by EDITING AN ISSUE_COMMENT IN PLACE, so it can NEVER verify. ⇒ A plan with pr-agent required cannot clear `participated_stale` by the contract's OWN prescribed remedy. ⚠ All three reviewers failed differently on that PR: pr-agent (detector), sourcery (size refusal, cap 150000 vs 2963 lines), coderabbit (budget, 0 remain).

⛔ FOUR SELF-REPORTED PLAN-PR-044 DEFECTS, ALL CORROBORATED: (a) the shipped fix does NOT close its own defect — `unregistered_kind` fires only for UNREGISTERED tokens, and `coderabbit` is a registered kind sitting in `optional_bots`, so a well-named required reviewer in the wrong list still buys participation_complete:true with zero diff-readers (lesson 2026-09-03-23-003); (b) THE DURABLE CONFIG FIX IS OWED — tracked .plan/marshal.json still reads optional_bots "coderabbit,sourcery", so /marshall-steward is owed or every future plan inherits it; (c) six lessons MIS-ROUTED to the global store because plan-retrospective (995) runs BEFORE lessons-capture (991) while the verdict resolves inside the latter — PRODUCER AFTER CONSUMER; (d) the pre-archive foreign gate can NEVER pass (8fe5be) — it classifies the checked-out branch and a merged PR's head is never main.

⚠⚠ THE INBOX IS NOT DRAINED: 20 live messages remain (19 candidate-lesson, 1 truthful-signals finding), 0 invalid, 0 closed senders. Only the TWO LANDINGS were consumed this pass. A `/plan-orchestrator analyze slug=review-apparatus` drain is OWED and is the largest single piece of pending ledger work.
⭐⭐ NEXT ACTION: (a) drain the 20-message inbox; (b) stage specs for the three unowned defects above; (c) `/marshall-steward` for the owed config fix; (d) BOTH SLOTS ARE OPEN — `next` can emit two, but re-derive disjointness first.

## Relocated 2026-09-23 (cleanup, operator-confirmed) — eight Open-Defects/Watches sections whose subject is closed

Selected on the "closed subject, not merely old" test: each carries its own closed/resolved marker in
its heading and no still-open item embedded as its primary subject. Several sections in the same range
were deliberately NOT relocated because they carry an embedded live item (`RESOLVED 2026-08-24` — a
"STILL OPEN" scoping defect; the `PLAN-PR-046` and `PLAN-PR-033` LANDING sections — each carries a live
open-defect tail); those stay in `epic.md` for a future pass to judge on their own terms.

### ⭐ CLOSED-BY-MEASUREMENT 2026-09-05 — the union-with-spec surface reading has a measured cost

While PLAN-PR-042 ran, `corpus cross-check`'s `live_plan` rows named exactly
`bot-participation-contract.md` and `cuioss-review-bot.md` — **precisely the two production files it
actually touched** (`git show --stat` on `497261525`: those two plus one test file). This
orchestrator treated that as a partial reading and cleared candidates against the **union** of the
live rows and the spec's five declared entries.

**The cost is now measurable.** The union reading correctly serialized `PLAN-PR-025B` (which declares
`test/plan-marshall/automatic-review/`, where the plan did write), but also serialized **`PLAN-PR-026`,
`-030`, `-031`, `-047` and `-048`** behind `review_completeness.py` and `review_retrospective.py` —
**two files this plan never wrote.** Five plans sequenced behind two files that never moved.

⛔ **The rule still stands and is NOT relaxed**: a running plan's live surface can be genuinely partial
because it grows as the plan works, so clearing against the live arm alone remains unsafe. What is
recorded here is that the conservative reading has a **throughput** cost, not a safety one — it lost
five pairings; it admitted no collision. ⭐ **Correctness in the safe direction is still a cost, and
naming it is how the next reader knows the trade was made deliberately.**

### ✅ CORRECTED-AND-CLOSED 2026-09-05 — `2-refine` drift was REAL but did NOT survive the archive

`phases[]` records `2-refine` as `in_progress` while the plan sat at `6-finalize`, and `progress`
reports `completed_phases: 4` where **five** are genuinely complete. The **light planning lane
collapses refine+outline+derive into one envelope and never closes `2-refine`.**

⛔⛔ **THIS ORCHESTRATOR'S CONCLUSION WAS WRONG AND IS RETRACTED HERE.** Inbox message
`apply-the-cloud-plan-lane-contract-amendments-016.md` (a self-correction filed by the same plan)
establishes that the drift **did NOT survive the archive**: the archived record at
`.plan/local/archived-plans/2026-09-05-apply-the-cloud-plan-lane-contract-amendments/status.json`
does not carry it. The first half of the claim was accurate **when written** — the drift was read off
the live `status.json` during `emit-landing` and corroborated by `manage-status progress` returning
`completed_phases: 4` at `6-finalize`. The *conclusion* — that it would ship into the archive — is the
part that was wrong. ⭐ **A defect that self-resolves at archive is not an open defect**, and leaving
this standing would have sent a future plan hunting a condition that no longer exists.

⭐ **The run deliberately did NOT repair it, and that was still the right call** — a hand-write to
`status.json` that close to `archive-plan` risks more than the inaccuracy does, and the accurate
record is that the machinery skipped the phase, not that it completed. Recorded here so the next
reader does not treat a light-lane plan's `completed_phases` as a count.

⛔ Also on the same record: `phase_steps["6-finalize"]` carries BOTH `plan-marshall:plan-retrospective`
(written by the step) and a bare `plan-retrospective` (written by the orchestrator), both `done` with
different `display_detail`. It inflates any count over `phase_steps` and defeats a naive
`len(phase_steps) == len(manifest.steps)` handshake. **Staged as PLAN-PR-050 D4.**

### ✅ 2026-09-04 SECOND DRAIN — 1/1 consumed, staged as PLAN-PR-047; ⛔ ONE SENDER CLAIM REFUTED BEFORE STAGING

`truthful-signals-044.md` arrived at 08:29:22Z, **after** the first drain closed. `messages_scanned: 1`,
`archived: 1`, `invalid: 0`. Disposition **staged** — a `kind: finding` escalated, not absorbed.

**Staged as `PLAN-PR-047` (WS-03, D0–D4)** — *the counting stage reasons from inputs that were never
persisted, and each gap changes a published number*. Declared surface **10 entries, `declarative`,
`admits_disjointness_check: true`, 0 unresolved** (parser-verified). Corpus now **49/49** both directions,
0 `rows_without_spec`, 0 `specs_without_row`, `blocking_count: 0`.

⛔ **NOT folded onto `PLAN-PR-030`** despite the shared measurement subject — PR-030 already carries seven
items (one gate + six deliverables), over the split guard. Nor onto `PLAN-PR-043`, which **this session's
own earlier fold** took to six. Recorded so both omissions read as decisions.

⛔⛔ **One of the sender's four claims was REFUTED before staging, and the spec carries the refutation so
it cannot be re-adopted.** The claim: *"the PR-Agent registry doc states this bot posts no inline comments
at all"*, making an observed `kind=inline` record a contradiction. **At `31d42db87` — the registry version
the source run actually read, predating PR #1386's merge (`71279cc02`, 2026-09-03 17:53:36Z) — the doc
declared BOTH publish shapes**: `issue_comment` unconditional plus `inline` under `/improve`, with the
explicit note *"An absent inline count is therefore NOT evidence of non-participation, while a present one
IS evidence of participation."* ⇒ The observed record is what the registry **predicts and endorses**, and
the sender's drawn consequence (*a counting stage would have concluded this bot found nothing*) is
backwards.

⭐ **The inverted form survives and is what D4 carries**: the Guide `issue_comment` is declared
**unconditional**, yet **zero** `issue_comment` records were observed for `cuioss-review-bot`. An
unconditional shape that did not appear is a genuine mismatch — in the opposite direction.

⭐ **Three claims verified first-party at HEAD `cc5ea40a1` before staging**: `sourcery.md:20-22` (no
`review_body_summary_patterns`; the empty default keeps every `review_body` **COUNTED**), `sourcery.md:51`
(`rate_limit_class: hard_quota`), and `github_re_review.py:394`
(`'head_sha_verified': matched_signal == 'review'`) — the last corroborating both `9f7923` and this epic's
own `e8bde7`.

⛔⛔ **The compounding selection effect is why this is a MEASUREMENT defect, not a coverage gap.**
`finalize-step-simplify` (order 8) and `finalize-step-security-audit` (order 9) mutate source **after** the
gates (5, 7), and a forward pass never re-gates their edits ⇒ **the only measurable PRs are those where
neither step committed anything** — systematically the PRs that needed no fixing. A biased population, not
a random sample. ⛔ **A run of `excluded` rows means those PRs were never measurable. It does NOT mean the
gates were clean.**

### ✅ 2026-09-04 INBOX DRAINED — 20 of 20 consumed, 0 invalid, queue at the EMPTY zero

`messages_scanned: 20`, `messages_archived: 20`, `messages_invalid: 0`, `messages_archive_failed: 0` —
the closure equation holds. Post-drain `live_count: 0`, `closed_senders` **empty**, `invalid_count: 0`
⇒ the **EMPTY** state, ⛔ **NOT finished**: neither sender declared closure, so more messages are expected.

| Disposition | N | What |
|---|:-:|---|
| **promoted** | 15 | lifted to the global lessons corpus as `2026-09-04-08-001` … `-015` |
| **folded** | 3 | into `PLAN-PR-031`, `PLAN-PR-043`, `PLAN-PR-025B` + `PLAN-PR-046` |
| **discarded** | 2 | one dedup, one **refuted** — neither dropped silently |

**The 15 promotions** span `phase-6-finalize` (4), `plan-retrospective` (2), `phase-5-execute` (2),
`ext-self-review-plan-marshall` (2), and one each of `manage-solution-outline`, `manage-change-ledger`,
`persona-module-tester`, `script-shared`, `automatic-review`. ⭐ Two are worth naming: `-005` *reject a
fix-task whose files fall outside its deliverable declared surface* is the **direct remedy for the 12-of-23
scope drift** recorded above, and `-013` *completeness asserted again inside the fix for three
asserted-completeness defects* is the recurring archetype re-firing inside its own repair.

**The 3 folds, and the same-act surface obligation discharged on all of them:**

| Message | → | Surface |
|---|---|---|
| `rpp-015` | `PLAN-PR-031` **D6** — a posted disposition is a promise nothing re-checks against what landed | +3 entries; `claimed_count` **8**, parser-verified |
| `rpp-009` | `PLAN-PR-043` **D6 limb A** — the rate window is a retry policy, not a flat timeout | +3 entries; `claimed_count` **14** |
| `truthful-signals-043` | split 3 ways as its sender intended — item 1 → `PLAN-PR-025B` **D10**, item 2 → `PLAN-PR-046` **D3**, item 3 → `PLAN-PR-043` **D6 limb B** | PR-025B +4, PR-046 +2 (`claimed_count` **11**), PR-043 covered above |

⭐⭐ **`truthful-signals-043` item 2 is `e8bde7` reached from the other side** — an in-place republish read as
`declined` — observed in TokenSheriff and **corroborated first-party** on our own PR #1388. Two independent
observations of one mechanism. ⛔ The foreign PR ids are **LEADS**, not corroborated in this checkout.

⛔ **Two stale-surface corrections made in the same pass**: `PLAN-PR-031` and `PLAN-PR-043` both declared
`standards/pr-agent.md`, **retired by #1392** — corrected to `standards/cuioss-review-bot.md`. A spec
declaring a path that no longer exists is a surface the disjointness gate cannot match.

⚠ **`PLAN-PR-025B`'s surface remains unverifiable from the parser** — it still collapses onto `plan_id`
`PLAN-PR-025` under the known 025-family defect recorded above. The fold's +4 entries were written, but
`corpus surfaces` cannot attribute them. **Pre-existing, not introduced here.**

⛔ **`rpp-016` was DISCARDED AS REFUTED, and the distinction matters**: it reported findings *"die with the
plan directory — there is no carry-out route"*. The store is intact and all 8 hash ids resolved on the first
read. Its *proposal* (a carry-out route) names a real gap; its *premise* (the data is lost) is false, and
recording it as a live signal would have preserved the false half.

### ⭐⭐ RESOLVED 2026-09-04 — THE EIGHT “UNREACHABLE” FINDINGS WERE RECOVERED; THE DATA SURVIVES ARCHIVAL

PLAN-PR-038's landing reported eight findings *"pending in a store that just died with the plan
directory"* with *"no route out of the archive"*. ⛔ **The premise was wrong in the way that matters: the
store did not die.** `.plan/local/archived-plans/2026-09-03-review-packs-become-published-artifacts/artifacts/findings/`
is intact and readable — 13 JSONL files — and **all 8 hash ids resolved on the first read**, every one at
`resolution: pending`, `promoted: false`.

⭐ **The missing thing was a ROUTE, not the data.** Recording that distinction matters: a future run that
believes findings are destroyed by archival will stop looking. They are not. The carry-out is a read.

| Hash | Type / sev | Component | Subject | Routed |
|---|---|---|---|---|
| `e8bde7` | bug / warn | `workflow-integration-github` | `head_sha_verified` can never be true for pr-agent ⇒ the `participated_stale` remedy is unreachable | **stays here** (PR/review) |
| `18f362` | triage / warn | `tools-integration-ci` | CI payload cannot establish WHICH commit was verified — `head_sha` and `elapsed_sec` contradict | → `truthful-signals` `review-apparatus-025.md` |
| `1d5140` | bug / warn | `phase-6-finalize` | `ci_verify` reports `persisted=false` / `persist_skipped_reason=head_sha` while it DID persist | → `-026.md` |
| `1f0c43` | improvement / warn | `manage-architecture` | script startup ~18s cold makes subprocess budgets marginal under `-n auto` | → `-027.md` |
| `5a5761` | improvement / warn | `manage-references` | `affected_files` under-records loop-back work ⇒ every derived finalize step under-scopes | → `-028.md` |
| `c8e4a9` | **bug / ERROR** | `manage-build-server` | a `timeout` verdict kills the daemon job but **orphans the whole pytest tree** | → `-029.md` |
| `d4501c` | improvement / warn | `phase-6-finalize` | `review_commitments reconcile` returns `verdict=clear` over `commitments_considered: 0` | → `-030.md` |
| `79a483` | insight / info | `phase-6-finalize` | **two ADR proposals awaiting operator confirmation** | **operator action** |

Routing follows the three-way rule — PR/review here, everything else not-ours to `truthful-signals`. Six
were filed through the sanctioned `inbox write` channel as `sender_type: orchestrator`, so this is a
**transfer, not an offer**: each is enumerable in that epic's own queue and no longer depends on this
ledger being read.

⭐⭐ **Three of the six independently reproduce archetypes already on record**, which raises their weight:
`c8e4a9` confirms lesson `2026-09-02-21-002` **that housekeeping had just retained as NOT covered**, with
live pids (a killed pytest master left ten xdist workers running); `5a5761` is a **second independent
observation** of the `affected_files` under-recording defect; `d4501c` is the **vacuous-guard archetype**
verbatim — a `clear` verdict over an empty population, the exact thing the standing rule
*"every set-guarding detector must publish its population size"* exists to forbid.

⛔ **`79a483` is why `adr-propose` is `skipped`, not `done`** — Step 5 needs an `AskUserQuestion` per
proposal and a dispatched leaf cannot reach the operator. Two proposals await confirmation: (1) *a published
artifact set is orthogonal — cross-cutting text is emitted exactly once*; (2) *a fan-out CLI parameter is a
request, not a contract*. Decisive decision-log entry `abe291`.

### ✅ 2026-09-03 — a CONTROL that worked, recorded because this section is otherwise all failures

From the same data-point. The operator minted the override through the designed mechanism: flipped
the barrier to `ask` mode (whose *"Merge anyway"* branch is the documented `barrier-ask-override` mint
site) and granted it **HEAD-bound** against `4f8b0733a` with the evidence recorded.

⭐ **The gap-class binding was observed doing its job live**: `barrier-ask-override` read admissible
for `review-barrier-gap`, while `pre-merge-consent` read **inadmissible** for that same class —
refusing to let a routine merge confirmation authorize past a participation gap the operator never
saw. That is the fail-closed guard behaving exactly as specified, and it is the matched positive
control for the merge-authorization work PLAN-PR-015 landed. Do not let this section's density of
defects imply the barrier is broadly unsound; this limb is confirmed working.

### ✅ WATCH CLOSED 2026-09-15 (operator decision) — ex “we are wholly Tier 1, and this epic's defect list IS the Tier 1 trade billed back to us”

⛔⛔ **PREMISE REFUTED BY THE OPERATOR — do not re-open on the original framing.** The apparatus is already
hybrid: **Tier 1** = CodeRabbit + Sourcery, **Tier 2** = pr-agent (`cuioss-review-bot`, org CI, our model
ladder and charter), plus the in-house finalize self-review. "Adopt Tier 2" was never an open decision.

⭐ **The only residual question was merge-gate composition, and it is DECIDED: CodeRabbit stays a REQUIRED
reviewer until pr-agent achieves similar review quality — which the operator states is not yet the case.**
No fallback, no bypass policy, no gate change; the unattended CodeRabbit recovery protocol stays in force
unchanged. Config agrees (verified 2026-09-15): `.plan/marshal.json` `required_bots:
"cuioss-review-bot,coderabbit"`, `optional_bots: "sourcery"`. **Reopen condition**: pr-agent review quality
comparable to CodeRabbit's, **measured by the existing comparison protocol** —
[`review-practice.md`](review-practice.md) § 1 (the comparative deficit rule and its four scoring outcomes,
run at every post-merge PR revisit). ⛔ An earlier draft of this note claimed no such instrument existed —
REFUTED by the operator; that protocol is it. Decision logged in `decision.log`.

The original watch text is kept below for its evidence (the four vendor-runtime defects remain real and
remain owned by their specs):

From `next-level-001` (sibling orchestrator, relaying *Spec-Driven Production Grade Development in the
Age of Vibe Coding*, Boonstra, May 2026). ⚠ **An outside document: the tier model is asserted, not
measured, and the one supporting anecdote carries no figure.** The reason it is filed here anyway is
that its diagnosis is checkable against **our own record**, and it holds.

The model splits continuous automated review by **who owns the runtime and who writes the criteria** —
**Tier 1** managed SaaS (*"you get the vendor's review opinions, not yours"*), **Tier 2** hybrid (a
review skill committed to the repo, run by our CI via a coding-agent CLI in non-interactive mode, on a
model we choose), **Tier 3** custom deployed agent with durable memory.

⛔ **The argument that earns the watch**: every one of these is a property of NOT owning the runtime,
and all four are already in this ledger — CodeRabbit's one-review-per-hour window that **resets on
every trigger**; a refusal arriving as an **in-place comment edit** invisible to `movement_matched_bots`;
a run **reporting a review that never ran** (`count_stored: 0` read as reviewed-and-clean); and a
vendor-side `bot_kind` rename that invalidated consumer config fleet-wide with no propagation
mechanism, leaving TokenSheriff permanently merge-blocked. ⇒ **None is fixable inside Tier 1**, and the
standing rule that a CodeRabbit review is mandatory makes that dependency load-bearing on the merge path.

⚠ **What it does NOT argue, kept because it is the honest half**: not leaving Tier 1 — the managed
reviewers find real findings, and a self-owned reviewer grading its own repository has an independence
problem a vendor does not. The credible reading is **Tier 2 ALONGSIDE Tier 1**, covering house-specific
criteria and removing the single points of failure from the merge gate.

⛔ **Filed as a Watch, not staged.** It is a scoping question the message deliberately does not settle,
and it would be the largest architectural decision this epic has taken. **Surfaced to the operator
2026-09-14; awaiting a decision.** Note the standing-rule collision if it is ever taken: the
unattended-recovery protocol (≥90-min sleeps, max 10 waits, close-and-reopen) exists to survive a
constraint Tier 2 does not have.

### ✅ LANDING 2026-09-14 — `PLAN-PR-065` shipped #1491, 10/10, and the FOREIGN half landed as `pr-agent-settings` #64

Full record: [`landings/PLAN-PR-065.md`](landings/PLAN-PR-065.md). Landing `complete: true`; `#1491`
corroborated first-party (`ci pr view` → `merged`).

⭐⭐ **The plan repaired its own instrument BEFORE using it** — D1 made `ci pr list` derive a complete
population instead of a page (the exact defect this orchestrator hit at staging, when the verb returned
30 rows against an operator-reported 46), and only then did D2 derive the population and D3 close
against it. The gate that decided what to close was fixed before it decided anything.

⛔ **The review coverage of #1491 is a recorded BYPASS, not a clean review.** Bot review was explicitly
skipped by operator decision (empty rosters, `skip-bot-review`). `0 comments found` here means **nobody
looked** — which is precisely the conflation `PLAN-PR-061` exists to end, and the ledger must never
later read it as evidence of quality. ⚠ The retrospective's own `indeterminate` over a "roster of 3"
was a **false alarm**: it reads rosters from `marshal.json` rather than the plan's step-params
override. Transferred.

⛔⛔ **Declared vs realized diverged in BOTH directions for the first time**: 19 declared against a
13-path realized footprint, not nested — 5 realized-but-undeclared (including `branch-cleanup.md`, a
fix task appended during execute) and **4 declared-but-never-realized** (the GitLab half of the
`--limit` contract, declared in scope and never touched). ⇒ Fourth consecutive landing with the drift,
and over-declaration is the more dangerous half for this epic's gate: a spec that declares what it will
not touch makes the disjointness check sequence siblings behind files nothing ever claims.

⭐⭐ **Promoted as lesson `2026-09-14-19-001`** — the run's best finding: D1 fixed a producer while
`branch-cleanup.md`'s Safety Check, **the consumer gating a branch DELETION**, still read a bare count
with no `--limit`. A page read as a population, in the exact code path the deliverable existed to
correct. The scope-criterion validator caught it; **nothing in the outline's own success criterion
would have.**

⭐ **`PLAN-PR-039`'s precondition is DISCHARGED** — `packs/` exists on that repository's `main` for the
first time. ⛔ It stays unemittable for a *different* reason, and its `prose` surface was deliberately
NOT corrected: the exemption is named, and inventing a plan-marshall path to move the metric would
destroy the foreign-only property that makes WS-02 disjoint by construction. Emitting it is an operator
decision to accept a candidate the gate cannot check.

**Drain 22/22 archived** — `-017` promoted; `-001`…`-016`, `-018`…`-020` transferred to
`truthful-signals` as `review-apparatus-041.md` (an invocation-discipline cluster of **ten rejections in
one run**, three of them the same mistake repeated after the correct form had been displayed — plus
`-014`, which is NOT discipline but a real tooling defect: the generated executor rejected a flag the
dispatched script declares, and two regenerations did not clear it); `next-level-001` is the Watch above.

