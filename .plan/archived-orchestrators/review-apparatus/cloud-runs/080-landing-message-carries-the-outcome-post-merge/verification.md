# Verification — 080-landing-message-carries-the-outcome-post-merge

**Landed as:** PR #1196, squash commit `6b923309` (refutation)
**Verdict:** verified-with-gaps

The refutation's **trigger** is sound and independently re-derived: the landing emission genuinely moved
post-merge before the run, so the plan's foundational OBSERVED claim was false at the HEAD the run read.
The refutation's **closure decision** is not sound in full: three of the six deliverables were declared
moot on arguments that do not survive inspection, and one defect the plan named — a `kind: landing`
message emitted, and phrased as a landing, for a plan that did **not** merge — is live in the current
tree.

## Method

1. Read `plan.md` and `report-01.md` in full; extracted every deliverable, *Done when* clause,
   ⛔/⭐/⚠ obligation, out-of-scope item, claim-label row and Verification demand.
2. Read the landed diff (`git show --stat 6b923309`) — two files, both under `doc/plans/**`, 120 added
   lines, no source change.
3. Re-derived the refutation from the tree at **both** `6b923309` (the squash commit this plan landed as,
   and the HEAD the run read) and the current review branch HEAD. Every report citation was opened at
   `6b923309` and its quoted text compared character-for-character; every finding below that names a
   defect was re-checked at the current HEAD as well.
4. Traced the emission chain end to end: step `order:` frontmatter → the sort choke-point
   (`_sort_steps_by_frontmatter_order`) → the finalize dispatch loop's per-step outcome handling →
   `branch-cleanup`'s six terminal branches → the landing producer → the inbox write boundary.
5. Read the implementing Python (`pr_intent_section.py`, `_orchestrator_inbox.py`,
   `_manifest_validation.py`) for fail-open branches, non-idempotence and unreachable predicates.
6. Enumerated the finalize-step population by `order:` frontmatter across
   `phase-6-finalize/{workflow,standards}/*.md` **and** `.claude/skills/*/SKILL.md`, to check D0's
   published population independently.
7. Read PR #1196's issue comments and reviews through the GitHub API to check the report's reviewer
   table.
8. Searched `test/` for tests pinning the single-landing, halted-finalize and SHA-bearing claims.

Searches whose *absence* results are relied on below are named at each finding.

## Refutation audit

### The refutation's argument, restated

1. The plan's foundational OBSERVED claim is *"`lessons-capture` precedes `branch-cleanup`"*. At HEAD
   `lessons-capture` is `order: 991` and `branch-cleanup` is `order: 70`; higher order runs later, so the
   emission is already post-merge.
2. The plan's own verify-first gate says a moved emission REFUTES the plan and it must be closed.
3. Every other enumerated defect is already resolved: the batch self-description is gone; the singular
   landing is a documented invariant; `review-retrospective.md` is HEAD-stamped and derived from the
   append-only `pr-comment` store; `create-pr` keeps Non-goals and truncates visibly.
4. D2's missing outcome fields are not a live defect because (a) the root cause is cured by the ordering
   and (b) the plan's own out-of-scope forbade the enrichment.
5. The never-merges case is already correct because a finalize that halts pre-merge never reaches
   `order: 991`, so it emits no landing rather than a false one.

### Independent re-derivation from the tree

**Point 1 — CONFIRMED, and stronger than the report states.** At `6b923309`,
`phase-6-finalize/workflow/lessons-capture.md` frontmatter carries `order: 991` and
`phase-6-finalize/standards/branch-cleanup.md` carries `order: 70`. Ascending order *is* runtime order:
`manage-execution-manifest/scripts/_manifest_validation.py:384-417` sorts steps ascending
(`sortable.sort(key=lambda pair: pair[0])` at `:409`), and `phase-6-finalize/SKILL.md:217` at `6b923309`
(`:220` at HEAD) defines the band — *"**POST-RUN REVIEW (post-merge, `order > 70`)** — every step
declaring `post_run_review: true` runs after the merge gate"*. `lessons-capture` declares
`post_run_review: true`.

**Point 2 — CONFIRMED, with the movement itself located.** The plan's gate is conditioned on *"if a
landing **has since moved** the emission"*. It did: `git log -p` on `lessons-capture.md` shows exactly one
change to the field, `-order: 60` / `+order: 991`, in commit `e1ae3814`, *"fix(phase-6-finalize): reorder
post-run-review steps after the merge gate (#1080)"*. So the plan's claim was true when authored and was
inverted by intervening work — the gate's literal trigger, not merely a mis-stated premise. (The report
attributes the move to sibling plans 040/050 and cites `source-edit-pushability.md` from #1175; the actual
reorder is #1080, a different change. See § Report-claim audit.)

**Point 3 — CONFIRMED in three parts of four.**

- *Batch self-description gone.* `grep -n -i "batch\|two lesson"` over `lessons-capture.md` at
  `6b923309` returns no match (exit 1). CONFIRMED.
- *Singular-landing invariant documented.* `lessons-capture.md:82` at `6b923309` opens verbatim
  *"Exactly **one `kind: landing` message per orchestrated finalize run**, emitted unconditionally"* (the
  line continues *"— including at zero signals"*);
  `plan-orchestrator/standards/inbox-envelope.md:92` carries the matching payload-contract row;
  `finalize-step-preference-emitter.md:219-221` reads *"This branch emits NO `kind: landing` message."*
  All three quotes are exact. But see § Correctness review — the invariant is **per finalize run**, and
  the defect the plan reported was **three landings for one plan**.
- *`review-retrospective.md`.* `head_dependent: true` at `SKILL.md:16`; `--head-at-completion {sha}` on
  the completion record, the zero-findings skip-clean record and both non-fatal error paths;
  `unmeasurable` / `indeterminate` grading present. All CONFIRMED. But the stamp lands on the
  **step record**, not on the **artifact** — see § Correctness review.
- *`create-pr`.* `create-pr.md:148-149` at `6b923309` is *"3. **Explicit non-goals** — what this change
  deliberately does NOT do…"*; `create-pr.md:180-182` is the `truncated: true` branch, *"cut at a word
  boundary, with the truncation marker rendered INSIDE the budget so the loss is visible"*. The script
  `phase-6-finalize/scripts/pr_intent_section.py:159-187` implements exactly that and provably cannot
  overrun the budget. CONFIRMED.

**Point 4 — REFUTED. The out-of-scope clause says the opposite of what the report reads into it.** The
plan's text is:

> ⇒ **D2 must not add any field that reads as authoritative**, and the enriched message should carry its
> claims **labelled as the plan's own report**.

That contemplates an enriched message and constrains its *labelling*; it does not forbid the enrichment.
The report renders it as *"The plan's own OUT-OF-SCOPE **forbade the enrichment** that would matter
here"* — an inversion. The project itself settled the question shortly afterwards: PR #1215 added
`phase-6-finalize/standards/emit-landing.md` and
`plan-orchestrator/standards/landing-payload-spec.md`, a machine-readable landing carrying `pr`,
`merge_state`, `deliverables_total/done`, `total_tokens` and per-step outcomes, with
`emit-landing.md:158` stating *"the STEP's own recorded claim, never a corroboration"* — precisely the
labelled-as-own-report shape the plan asked for. D2 was a live, actionable deliverable, not a
constraint-barred one.

**Point 5 — REFUTED. This is the load-bearing error.** The premise *"a finalize that halts pre-merge never
reaches order 991"* assumes a non-merging `branch-cleanup` stops the pipeline. It does not.
`branch-cleanup.md` § "Mark Step Complete" has **six** terminal branches and **every one records
`--outcome done`** (lines 1720, 1751, 1760, 1769, 1782, 1796 at HEAD; the same six at `6b923309`).
Only **two** of the six substantiate a landed merge — Branch A and Branch E, the two that record
`merge_mechanism`. **Four do not merge**, and three of those four are the load-bearing ones:

- **Branch C — declined by user** — *"Nothing was rebased, merged, or cleaned up"*, `work_performed=false`.
- **Branch D — no PR found** — *"exits before the rebase and before any merge"*, `work_performed=false`.
- **Branch F — enqueued, merge not yet landed** — *"It records **no `merge_mechanism`**, because no merge
  landed"*, and yet `--outcome done`.

The fourth, **Branch B — local-only mode**, also records `done` with no merge, but it is the lane in which
*"PR creation and merging are handled outside this workflow"* (`branch-cleanup.md:1594`), so `pr` and
`merge_state` are `n/a` **by design** and the payload spec accommodates that value. Branch B is therefore
not a false *fact*; it is still a false *sentence* under the producer's one worked headline, which renders
`shipped as n/a (n/a)` — that half is C2's finding, not this one.

`branch-cleanup` is an **inline** step (`standards/dispatch-inline-split.md:45`), so the post-dispatch
completion guard that halts on a missing record (`SKILL.md:1136`) does not apply to it. Nothing in
`SKILL.md` halts the FOR loop on a `done` outcome: the only per-outcome branching is the **resumable
re-entry check** at the head of each iteration, whose general rule is *"IF outcome == "done": SKIP this
step (continue to next iteration)"* (`SKILL.md:720`) — a skip of one step, never a stop of the loop — and
`SKILL.md:37` closes the set: *"Never skip a step in the manifest list based on PR state, CI state, or
earlier step outcomes. The ONLY valid skip condition is the resumable re-entry check."* The two other
outcome paths documented for the loop both continue as well (`SKILL.md:1057` and `SKILL.md:592`, the
timeout paths, mark `failed` and *"continue to the next step"*); the one outcome that does divert the
pipeline is `loop_back` (`SKILL.md:696`, `:722`, and the item-7b continuation hook), which is precisely
the outcome `branch-cleanup.md:1068` says the structurally-blocked path must use **and which none of
Branches C / D / F uses**. The loop therefore proceeds into the post-run band and reaches the landing
producer, which emits **unconditionally**
(`emit-landing.md:48`: *"the emission is unconditional when the step runs"*; at `6b923309`,
`lessons-capture.md:238`: *"always ≥ 1 — the `kind: landing` message is unconditional"*).

**The document states the mechanism itself.** The inference above need not be assembled from separate
sites: `branch-cleanup.md:1068` warns a future author away from settling a structurally-blocked path with
Branch C precisely because *"It also lets the FOR loop continue through to `archive-plan` — archiving the
plan with the PR unmerged, the worktree unremoved, and the branch undeleted."* That is the merge gate's
own account of what a terminal `done` on a non-merging path does, and `emit-landing` (`order: 1000`) sits
between `branch-cleanup` (70) and `archive-plan` (1100). `archive-plan` carries a refuse-to-archive gate
for foreign deliverables (`archive-plan.md:38`) and none for the host PR's merge state.

### Does the refutation hold?

**Its trigger holds.** The gate fired for the right reason and the report was the correct deliverable for
that trigger.

**Its closure does not hold in full.** The plan's ⛔ observation 1 — *"the message ASSERTS a landing in its
prose while the PR is open… The fix must change the message's **claim**"* — survives. In the current tree
the only worked example of the landing body is
`emit-landing.md:175`:

> 1. **An optional one-line narrative headline** under a `## What landed` heading — e.g.
>    `{plan_id} shipped as {pr} ({merge_state}).`

A `## What landed` heading and the verb *shipped*, with the contradicting fact parenthesised beside them —
which is exactly the shape the plan called out as insufficient. Reached on a Branch C / D / F run, it is a
landing-asserting message for a plan that did not land.

## Deliverables

| # | *Done when* (plan) | Report claim | Ground truth in the tree | Verdict |
|---|---|---|---|---|
| D0 | "the population is derived and published, or the stop condition fires and the split is proposed" | Population = exactly the three named floor members; zero additional; stop condition does not fire | Independently re-derived over `phase-6-finalize/{workflow,standards}/*.md` + `.claude/skills/*/SKILL.md` by `order:` frontmatter. No fourth PR/review/merge-state artifact found that is not regenerated. `project:finalize-step-era-stamp-fill` (order 21) writes a PR number into tracked source but declares `head_dependent: true`, so it re-arms on loop-back and is correctly excluded. Population = 3 stands. Two defects in the publication rather than the derivation: the table omits five of the six project-local steps its method says it enumerated (it is labelled "relevant subset"); and D0's third criterion — *"is **not** regenerated after a loop-back"* — is mis-answered for the PR body, whose "staleable?" cell reads *"**was** — now visible truncation + kept Non-goals"*, an answer to the content question, not to the regeneration one. It is in fact still not regenerated (C11). | **Satisfied on the population; the per-member staleness record is wrong for one of three** |
| D1 | "the choice is made with both failure modes stated, and the never-merges case has a **defined message**" | "Already post-merge… **Never-merges is already correct:** a finalize that halts pre-merge never reaches order 991, so it emits **no** landing" | Emission site: correct. Never-merges: **false**. `branch-cleanup` Branches C/D/F record `--outcome done` without merging, the loop continues, and the landing is emitted anyway. No message is defined anywhere for a plan that never merges: `grep -n -i "never merges\|halt\|blocked\|abandoned"` over `landing-payload-spec.md` returns nothing, and the orchestrator's terminal-row gap marker (`orchestrator.py:674-677`, over `TERMINAL_PLAN_STATUSES = ('shipped', 'landed')` at `:140`) fires only for `shipped`/`landed` rows. | **Not satisfied** |
| D2 | "no landing message contains a 'What landed' assertion that can be true only if the merge happened, unless the merge happened" | Root cause cured by ordering; content mandate barred by out-of-scope | The out-of-scope reading is an inversion (see § Refutation audit point 4). The *Done when* clause itself is **unmet at HEAD**: `emit-landing.md:175` is a `## What landed` / *shipped* headline with no conditioning on `merge_state`, reachable on a non-merged run. The fact half was delivered by PR #1215 (`landing-payload-spec.md`), but without a commit SHA — `LANDING_REQUIRED_KEYS` (`_orchestrator_inbox.py:811-820`) is `schema, plan_id, pr, merge_state, deliverables_total, deliverables_done, total_tokens, steps`; `grep -n -i "sha"` over `emit-landing.md` and `landing-payload-spec.md` finds no commit-SHA field. | **Not satisfied** |
| D3 | "one landing per landing, **proven by a test over the multi-emission shape**" | "Already the documented invariant" | The documented invariant is scoped *per orchestrated finalize run*; the reported defect was three landings for **one plan** across successive outcomes. `cmd_inbox_write` (`_orchestrator_inbox.py:890-982`) has no per-sender landing-uniqueness guard — a second `--kind landing` from the same `sender_id` allocates a new sequence and returns `status: success` (reproduced by execution). `cmd_inbox_supersede` exists (added by PR #1198) but is a manual verb; `grep -n "supersede"` over `emit-landing.md` finds no call. No test over the multi-emission shape exists (`grep -rln "emit_landing\|emit-landing" test/` → 5 files, none asserting single-landing-per-plan; `test_inbox_message_state.py` covers the supersede verb mechanics only). | **Not satisfied** |
| D4 | "**every D0 member** either carries a HEAD stamp or regenerates, with the choice justified per member" | "Already done" for `review-retrospective.md` | The clause quantifies over all three D0 members; the report assesses one. **`review-retrospective.md`** — the step *record* carries `--head-at-completion` (`SKILL.md:427-445`); the **artifact** does not: the Step 4 composition instruction (`.claude/skills/finalize-step-review-retrospective/SKILL.md:388-425`) enumerates what the artifact must contain — metrics table, `## Review-versus-Gate Delta`, `## Qualitative Quality Assessment`, `## Comparative Verdict` — and never a HEAD stamp, while `SKILL.md:94` claims *"the stamp is what ties it to that tree for anyone reading the retrospective later"*. The `## Review-versus-Gate Delta` section does carry `gate_head_sha` / `reviewed_head_sha` (`:342`, `:344`, `:402`), so the reviewer half is anchored, but only inside that one optional section. **PR body** — neither arm holds: `create-pr` frontmatter declares `order: 20` and `mutates_source: false` with **no** `head_dependent`, so an already-`done` record is SKIPPED by the general re-entry rule (`phase-6-finalize/SKILL.md:720`) and the body is never recomposed after a loop-back; its own re-entry branch reuses the PR without rewriting the body (`create-pr.md:71`, *"Skip creation; reuse the returned `pr_number`"*); and no other finalize step calls `pr edit` over it (`grep -rn "pr edit"` over `phase-6-finalize/` and `.claude/skills/` returns only `architecture-refresh.md`'s re-enrichment note). See C11. **Landing message** — no HEAD or SHA anchor at all (C10, and the SHA gap). The staleness the plan *observed* is cured by ordering for two of the three members (990 and 1000 are post-merge, after the last point HEAD can advance), so the class defect is gone there; the literal *Done when* is met by none of the three. | **Partially satisfied** |
| D5 | four tests, each proven failing pre-fix | N/A — no implementation | No test exists for (a) a landing carrying the SHA, (b) the halted-finalize case, (c) the sibling-count assertion, or (d) a consumer detecting a stale artifact by HEAD. Searched `test/` for `emit-landing`, `emit_landing`, `landing`. | **Not satisfied** |

## Report-claim audit

| Report claim | Status |
|---|---|
| `lessons-capture` `order: 991`, `branch-cleanup` `order: 70` | **CONFIRMED** at `6b923309`, frontmatter read directly |
| `SKILL.md:149` ordering authority; `SKILL.md:214-217` post-run band; `SKILL.md:219` ascending validator | **CONFIRMED exactly** at `6b923309`: `:149` is *"Each step declares an `order: <int>` value in its authoritative source"*; the four band bullets occupy `:214-217` with POST-RUN REVIEW at `:217`; `:219` is the **Ordering authority** paragraph naming the ascending-order validator |
| `lessons-capture.md:82` "Exactly one `kind: landing` message per orchestrated finalize run, emitted unconditionally" | **CONFIRMED** verbatim |
| `inbox-envelope.md:92` landing payload row | **CONFIRMED** verbatim |
| `finalize-step-preference-emitter.md:219-221` emits no second landing | **CONFIRMED** verbatim |
| Grep for `batch` / `same batch` / `two lesson` in `lessons-capture.md` → no matches | **CONFIRMED** (re-run, exit 1) |
| `review-retrospective`: `head_dependent: true`, `--head-at-completion` on every terminal record, append-only `pr-comment` derivation, `unmeasurable`/`indeterminate` grading | **CONFIRMED**, with the artifact-vs-step-record distinction the report does not draw |
| `create-pr.md:148-149` Non-goals first-class; `create-pr.md:180-182` visible word-boundary truncation inside budget | **CONFIRMED** verbatim, and confirmed in the implementing script |
| Consumer check: `cleanup.md:111` never derives quiescence from a merge landing | **CONFIRMED** verbatim — line 111 is *"⛔ Quiescence is **never** derived from a timer, and **never** from a merge landing."* |
| D0 population = 3, no additional member | **CONFIRMED** by independent enumeration |
| Build gate: no Python changes, build skipped | **CONFIRMED** — the diff is two files under `doc/plans/**` |
| Reviewer table (`cuioss-review-bot` clean, `coderabbitai` skipped on `skip-bot-review`, `sourcery-ai` rate-limited) | **CONFIRMED** against the live PR #1196 comment and review bodies. Two of the three quotes are verbatim: `cuioss-review-bot`'s *"PR Reviewer Guide 🔍 … No relevant tests / No security concerns identified / No major issues detected"* and `sourcery-ai`'s *"you have reached your weekly rate limit of 500000 diff characters"*. The `coderabbitai` line is a faithful **paraphrase**, not a quotation — the posted body reads *"Review skipped — Auto reviews are limited based on label configuration"* with *"Excluded labels (none allowed) (1): skip-bot-review"*, where the report renders it as *"Review skipped — only excluded labels are configured (`skip-bot-review`)"*. Substance identical; the report presents it in quotation form |
| "Never-merges is already correct… emits **no** landing rather than a false one" | **REFUTED** — see § Refutation audit point 5 |
| "The plan's own OUT-OF-SCOPE forbade the enrichment that would matter here" | **REFUTED** — the clause constrains labelling, not existence |
| "D3 — Already the documented invariant" | **MISLEADING** — the invariant is per-run; the observed defect was per-plan |
| Git-provenance row substantiating "a landing has since moved the emission" with #1175 / #1165 / #1170 | **IMPRECISE** — those PRs are real and did the `review-retrospective` work, but the emission move is `e1ae3814` (#1080), which the report never names |
| "An independent verification sub-agent… returned REFUTATION CONFIRMED on all six checks" | **UNVERIFIABLE** — no persisted sub-agent artifact exists in the repository; the claim rests on the report alone, and its Q1/Q2 conclusions are contradicted by the findings above |

## Correctness review

**C1 — A landing is emitted for a plan that did not merge (CONFIRMED).** Covered in § Refutation audit
point 5. Three `branch-cleanup` branches record `--outcome done` while explicitly not merging; the
dispatch loop continues; `emit-landing` (`order: 1000`) emits unconditionally. `emit-landing.md` contains
no merge-state gate — `grep -n -E "supersede|inbox write|existing|idempot|second landing|already"` over it
returns exactly three lines: the `inbox write` call (`:204`), the error-handling row (`:236`), and one
incidental *"already-resolved verdict"* phrase (`:68`). Its **only** skip is the Step 0 non-orchestrated
guard (`:100-121`), which is about a compose-gate escape, not about merge state.

**C2 — The landing's only worked headline asserts a landing unconditionally (CONFIRMED).**
`emit-landing.md:175` pairs a `## What landed` heading with *shipped* and parenthesises `{merge_state}`.
The plan's ⛔ says appending a correct field beside a false sentence leaves the false sentence there. The
template is labelled *optional* and *e.g.*, which softens it to guidance rather than a mandate — but it is
the only guidance the producer gives.

**C3 — `merge_state` derivation is under-specified (PLAUSIBLE).** `emit-landing.md:158-161` says derive
`pr` and `merge_state` *"from the `create-pr` and `branch-cleanup` step records… (their `facts` /
`outcome` / `display_detail`); when no PR exists, both are `n/a`"*. The only stated *rule* is the no-PR
case. Branch F records `outcome: done`, `work_performed=true` and **no** `merge_mechanism`; an agent
reading `outcome: done` without the absence rule can render `merge_state=merged`. The discriminator exists
in the facts — `merge_mechanism` is recorded iff *"the merge actually **landed** and was corroborated"*
(`branch-cleanup.md:1702`). Stated precisely, and weaker than a flat absence: `merge_mechanism` **is**
named at the consuming site, but only as one example in the list of typed facts to transcribe
(`emit-landing.md:137`), never in item 4's derivation rule — so the producer names the discriminator
without ever saying it is the discriminator. The spec's own vocabulary for the key
(`landing-payload-spec.md:84`) is likewise stated and unenforced (C10).

**C4 — No landing-uniqueness guard at the write boundary (CONFIRMED by execution).** `cmd_inbox_write`
(`_orchestrator_inbox.py:890-982`) validates slug, sender id, sender type, kind, epic existence,
deliverability-to-a-running-plan and payload non-emptiness. It never asks whether this sender already
filed a `kind: landing`. `allocate_message_path` simply takes the next sequence. A second landing is
therefore accepted silently and — the envelope being append-only — both survive to the drain, with no
`superseded_by` link unless a caller invokes `inbox supersede` by hand. Probed directly: two successive
`--kind landing` writes from `sender_id=plan-080` both returned `status: success`, allocating
`plan-080-001.md` and `plan-080-002.md`.

**C5 — `pr_intent_section.py` reports a reader failure as a substantive absence (CONFIRMED).**
`_run_outline_read` degrades an `OSError` (`:115-116`), a non-zero exit (`:117-118`) and an unparseable
envelope (`:121-122`) all to `{}`; `has_outline_intent` treats a non-`success` status as "no content"
(`:135-136`, `continue`) and returns `False` (`:139`); `cmd_render` then emits `omitted: True` with
`reason: 'no outline intent: solution_outline.md absent, or its summary and overview sections are both
absent or empty'` (`:203-204`, inside the omission branch at `:194-211`). That reason asserts a fact the
script did not establish, and the PR body loses its whole Intent section — including Non-goals — with
nothing in the rendered body indicating a section was ever intended. This is the same archetype the plan's
D0 named for the PR body, on a path the report did not examine.

**The conflation is restated at the consuming site, so it is a contract and not a slip.**
`create-pr.md:169-172` instructs the agent that `omitted: true` means *"the plan has no outline intent (no
`solution_outline.md`, or its `summary` and `overview` sections are both absent or empty)… This is a
normal outcome for outline-less plans, not a failure."* The decision-log line the branch writes
(`create-pr.md:174-178`) interpolates the script's `{reason}`, so a reader failure is logged **as** the
absence claim — the loss is recorded, but recorded wrongly.

Test coverage is partial in a way worth stating precisely: the absent-outline fixture
(`test_pr_intent_section.py:67-68`) returns `status: error / error: not_found` through a stub whose
`_Completed` stand-in always carries `returncode=0` and parseable output (`:54-59`, `:89-93`), so the
non-success-status degradation **is** exercised — it is the `OSError`, non-zero-exit and
unparseable-envelope paths, the three that mean something other than "no outline", that no test in the
file reaches.

**C6 — The truncation marker does not name what was lost (CONFIRMED, minor).** The three composed Intent
items are ordered problem → approach → non-goals, and truncation cuts from the end, so Non-goals is
structurally the first casualty. The marker
(`pr_intent_section.py:81-84`) reads *"Intent truncated — {shown} of {total} characters shown"* — it makes
the loss visible but not identifiable, so a reviewer still cannot tell that the scope statement is what
went missing. The plan's detectability argument is addressed at the "a human can see something was cut"
level and not at the "the reviewer knows the Non-goals are absent" level.

**C7 — `failed_outcome_strategy` is cited but defined nowhere (CONFIRMED, minor).**
`phase-6-finalize/SKILL.md:533` reads *"the dispatcher honours `failed_outcome_strategy`"*. A repo-wide
search (`grep -rn "failed_outcome_strategy"` over the whole tree excluding `.git`) returns that one line.
The mechanism the sentence relies on to bound a failed step's blast radius does not exist, which is
directly relevant to what happens after a non-merging `branch-cleanup`.

**C8 — `default:emit-landing` is unclassified in the dispatched/inline roster (CONFIRMED, minor).**
`standards/dispatch-inline-split.md` declares itself *"the single source of truth"* and carries a closure
invariant — *"Every step in the authoritative registry carries **exactly one** classification… never both
and never neither"* — pinned by `test/plan-marshall/phase-6-finalize/test_dispatch_roster_closure.py`.
`grep -n "emit-landing"` over that document returns nothing, while `SKILL.md:178` registers the step and
calls it inline, `SKILL.md:772` names it among *"the inline consumers"*, and `SKILL.md:848` names it as
the owner of the run's one landing. (`grep -n "emit-landing"` over `SKILL.md` returns `:178`, `:766`,
`:770`, `:772`, `:796`, `:848` — six lines, none of them in a roster.) The guarding
test reads `.plan/marshal.json`, which is **tracked** (one of the two exceptions at
`.gitignore:45-47`) but **stale**: the committed snapshot predates the step, so the test passes
without covering it (run locally: exit 0).

**C9 — Branch F names a recovery its own `done` record suppresses (CONFIRMED).** `branch-cleanup.md:1801`
closes Branch F with *"Re-entering finalize once the queue merge lands takes the `state == merged` path,
which performs the deferred local cleanup"*, while `:1796` records `--outcome done`. The dispatcher's
general re-entry rule for every step outside the head-dependent and `push` special cases is *"IF outcome
== "done": SKIP this step (continue to next iteration)"* (`SKILL.md:720`), and the prohibition that closes
the set is *"Never skip a step in the manifest list based on PR state, CI state, or earlier step outcomes.
The ONLY valid skip condition is the resumable re-entry check (skip if already marked `done` from a
previous invocation)"* (`SKILL.md:37`). The single escape from that skip is a `head_dependent: true` declaration
(`SKILL.md:549`), and `branch-cleanup`'s frontmatter declares `order: 70` and `mutates_source: false`
only — `grep -n "head_dependent"` over the document returns `:125` and `:689`, both prose about
*`automatic-review`'s* declaration. The document already knows this: `:1068` states that *"an
already-`done` `branch-cleanup` is SKIPPED by the resumable re-entry check, so the very remedies the
message names … would point at a pass that never runs."* Two sentences in one document contradict each
other, and the reachable one is false.

**C10 — the drain-completeness check passes a fact-free landing (CONFIRMED by execution).**
`check_landing_completeness` (`_orchestrator_inbox.py:859-887`) computes
`missing = [key for key in LANDING_REQUIRED_KEYS if not facts.get(key)]` — presence and non-emptiness
only. The producer's Error Handling table instructs the opposite of an empty value on failure:
*"A fact read … returns an error | Write that field as `n/a` in the fenced block (key still present) and
continue"* (`emit-landing.md:235`). `'n/a'` is truthy, so a degraded field passes. Probed directly: a
`landing-facts` block whose every required value is `n/a` returns `(True, [])`, and so does one carrying
`merge_state=totally-merged-trust-me`. The vocabulary the spec fixes for that key
(`landing-payload-spec.md:84`, *"(`merged` / `open` / `n/a`)"*) is unenforced and unrestated by the
producer. This matters because of what the check is *for*: it *"lets the orchestrator turn 'the queue is
empty' into 'nothing material is outstanding' — the two coincide only when every drained landing was
complete"* (`plan-orchestrator/SKILL.md:322`). The test named for the shared-source invariant does not
test it — `test_landing_completeness.py:137-141` asserts three membership facts about
`LANDING_REQUIRED_KEYS` and never reads the producer.

**C11 — The PR body, a D0 member, neither carries an as-of anchor nor is recomposed after a loop-back
(CONFIRMED).** The report and the earlier pass both closed the PR-body member on the Non-goals /
visible-truncation question alone, which is the *content* half of D0's concern. The *staleness* half —
D4's *Done when*, which quantifies over every D0 member — is unmet for it. `create-pr` is `order: 20`,
composed from `{changed_files}` resolved by `git diff --name-only origin/{base_branch}...HEAD` at that
point (`create-pr.md:100-108`), and its body is written once (`:120-134`, `:136-165`). It declares
`mutates_source: false` and **no** `head_dependent:` (frontmatter `:1-16`), so the general re-entry rule
SKIPs an already-`done` record (`phase-6-finalize/SKILL.md:720`); even were it re-fired, its own
existing-PR branch *"Skip[s] creation; reuse[s] the returned `pr_number`"* (`create-pr.md:71`) and
recomposes nothing. No other finalize step rewrites the body: `grep -rn "pr edit"` over
`phase-6-finalize/` and `.claude/skills/` returns only `architecture-refresh.md:277`, `:305`, `:550` — the
re-enrichment note, a different section. The loop-back fix commits the wait region absorbs
(`SKILL.md:219`, the *"bounded re-settle mutation-fixpoint"*) therefore land on a PR whose body describes
the pre-loop-back diff, and nothing in the rendered body states the HEAD it was composed against. The harm
is the one D0 named: a reviewer's completeness judgement is made against a scope statement that no longer
matches the diff, and the mismatch is undetectable from the body.

## Completeness review

By consumer kind, over the current tree:

- **Prose (skill bodies).** The landing producer, the merge gate, and the orchestrator drain are mutually
  consistent on the *happy* path. The non-merging path is unrepresented in all three.
- **Docs (standards).** `landing-payload-spec.md` derives the report↔inbox delta and classifies it, but
  its required-fact set omits the commit SHA the plan's D2 and D5(a) both name. `inbox-envelope.md`'s
  landing row is **not** stale against the spec: at HEAD `inbox-envelope.md:97` describes the payload as
  *"a machine-readable `landing-facts` block"* and defers explicitly — *"The payload BODY contract … is
  owned by `landing-payload-spec.md`; this table owns only the `kind`"*. The narrative-payload wording is
  the pre-#1215 text at `6b923309` (`:92`) and was replaced, not left behind.
- **Schema placeholders.** `LANDING_REQUIRED_KEYS` (`_orchestrator_inbox.py:811-820`) is the single source
  of truth for completeness and is shared by producer, validator and drain. No SHA slot. A `merge_state`
  vocabulary **is** fixed — `landing-payload-spec.md:84` gives *"(`merged` / `open` / `n/a`)"* — but
  nothing enforces it: `check_landing_completeness` tests presence and non-emptiness only, so any string
  passes (see C10).
- **Worked examples.** The one landing-body example (`emit-landing.md:169-186`) shows only the merged
  case. There is no worked example for a non-merged, deferred, or declined run.
- **Test fixtures / stubs (`*.py`).** `test_landing_completeness.py` covers prose-vs-facts completeness,
  fail-closed schema, and the shared-constant invariant. It does not cover merge-state truthfulness,
  single-landing-per-plan, or the halted-finalize case.
- **Prose-bearing string literals in production code.** `pr_intent_section.py:203-205` carries the
  absence-asserting `reason` string discussed in C5, and `create-pr.md:169-172` restates that same claim
  as an instruction, so the literal is a contract rather than a stray string; `_TRUNCATION_MARKER`
  (`:81-84`) carries the loss-quantifying but section-blind marker of C6. Swept the landing path for the
  same shape and found none: `compose_envelope` (`_orchestrator_inbox.py:362-397`) emits only header
  key/value pairs and the caller's payload, and `check_landing_completeness` returns key names, not prose.
  The landing's one prose assertion lives in the producer *document* (`emit-landing.md:175`), not in code —
  which is why C2's remedy is a doc change.
- **Stale doc restatements.** Two found. `create-pr.md:169-172` restates `pr_intent_section.py`'s
  reader-failure conflation as normal behaviour (C5). `branch-cleanup.md:1801` restates a re-entry recovery
  that `:1068` in the same document says the `done` record suppresses (C9). Checked and **not** stale:
  `inbox-envelope.md:97` (it defers the payload body to `landing-payload-spec.md` rather than restating
  the pre-`emit-landing` narrative contract), and `lessons-capture.md:35`, `:84`, `:239`, `:247`, all of
  which name `emit-landing` as the landing owner and disclaim their own emission.

## Out-of-scope compliance

| Out-of-scope item | Status |
|---|---|
| Making the channel TRUSTED / adding fields that read as authoritative | **Complied with.** The run added no field at all. The later `emit-landing` work labels its claims as the step's own (`emit-landing.md:158`), which is what the clause asked for. The report's *reading* of the clause was wrong (§ Refutation audit point 4), but no breach occurred. |
| Re-running review comparison on every loop-back by default | **Complied with.** No regeneration default was introduced. |
| Making the `landing` payload shape contractual unless D2 forces it | **Complied with by this run** (nothing touched). Made contractual subsequently by PR #1215, which is the "unless D2 forces it" arm, exercised by a different plan. |
| Disturbing `branch-cleanup`'s position in the step order | **Complied with.** `branch-cleanup` is `order: 70` at `6b923309` and at HEAD; unchanged by this run. |

The diff itself is two files under `doc/plans/review-apparatus/080-…/` and touches no source, so no
out-of-scope breach is structurally possible from this commit.

## Residue status

The report records one residue item:

> **D2 content enrichment** (landing message carrying an explicit, non-authoritative outcome summary)…
> The epic may open a fresh, correctly-scoped plan for it if still wanted.

**Status: largely closed, by a different epic.** PR #1215 (plan 302, `truthful-signals`, commit
`5a5446d3`) added `standards/emit-landing.md` (`order: 1000`), `landing-payload-spec.md`, the
`landing-facts` fenced block and `check_landing_completeness`. The landing now carries `pr`,
`merge_state`, deliverable counts, token totals and the per-step outcome set, labelled as the plan's own
claim.

**Residual within the residue:** no commit SHA (D2 and D5(a) both require it); no cost-against-anchor
comparison (only a raw `total_tokens`); no explicit "what was deliberately left unchanged" field; and the
message's *claim* is still landing-shaped regardless of `merge_state`.

The report's *"Nothing else open"* does not hold: the never-merges behaviour (D1), the per-plan
single-landing guarantee (D3), and the four D5 tests were all closed as moot rather than recorded as
residue.

## Summary

The verify-first gate fired for a real reason, and the run was right to report a refutation rather than
re-implement a plan whose central premise had been inverted by PR #1080. The report is unusually accurate
at the level of individual citations — every file:line quotation checked reproduces verbatim, and the
reviewer-participation table matches the live PR exactly.

Where it fails is in the step from *"the ordering defect is fixed"* to *"therefore nothing here is a live
defect."* Three of its six moot-ness arguments do not survive: the never-merges case is not handled (three
`branch-cleanup` branches record `done` without merging and the pipeline runs on to emit a landing
anyway), the out-of-scope clause was read as forbidding the D2 enrichment the project implemented one day
later, and the single-landing invariant it cites is scoped per finalize run while the defect reported was
per plan. The plan's own ⛔ — *"the fix must change the message's **claim**, not only append an outcome"* —
remains unimplemented: `emit-landing.md:175`'s worked headline is a `## What landed` / *shipped* sentence
with the contradicting `merge_state` in parentheses beside it.

Eleven follow-up items are recorded in `gaps.md`: one blocker, five major, five minor.

## Adversarial review

A second, independent pass re-derived every load-bearing claim above against the tree rather than
accepting it, and completed the sections the first pass left open. What follows is the audit of this
document by that pass; it is stated precisely enough to re-run.

### What was re-derived, and how

- **The blocker, from first principles.** Read all six `--outcome done` call sites in
  `branch-cleanup.md` § "Mark Step Complete" (`grep -n -- "--outcome done"` → `:168`, `:1692`, `:1696`,
  `:1703`, and the six code blocks at `:1720`, `:1751`, `:1760`, `:1769`, `:1782`, `:1796`), read each
  branch body, then read the dispatch loop's per-outcome branching (`phase-6-finalize/SKILL.md:686-723`)
  and the prohibition at `:37`. Separately checked that `loop_back` — the one outcome that *does* divert
  the pipeline — is not what any of Branches C / D / F records.
- **The step order**, by extracting `order:` / `name:` / `post_run_review:` frontmatter from every file
  under `phase-6-finalize/{standards,workflow}/` and every `.claude/skills/*/SKILL.md`, and sorting.
  `branch-cleanup` 70, `emit-landing` 1000, `archive-plan` 1100 confirmed; the six project-local steps
  enumerated independently of the report.
- **The emission move**, by `git log --oneline --all -S'order: 991'` on `lessons-capture.md` and reading
  the resulting diff hunk (`-order: 60` / `+order: 991`).
- **Three executable probes.** `check_landing_completeness` over an all-`n/a` `landing-facts` block and
  over `merge_state=totally-merged-trust-me` (both `(True, [])`); two successive `cmd_inbox_write` calls
  with `--kind landing` from one `sender_id` (both `status: success`, sequences 001 and 002);
  `test_dispatch_roster_closure.py` (21 passed) against a `.plan/marshal.json` holding 25 steps, none of
  them `emit-landing`. Modules were loaded through `test/conftest.py`'s `load_script_module`, which is
  what supplies the `file_ops` import path a direct `importlib` load lacks.
- **Every `path:line` citation in this document and in `gaps.md`** was opened at the commit it names.
- **The reviewer table**, re-read against PR #1196's live issue comments and reviews.

### Verdict on each load-bearing finding

**UPHELD — the blocker survives.** A `kind: landing` message is emitted for a run whose merge did not
land. Every link re-derived independently: the six terminal branches all record `done`; nothing in the
FOR loop halts on `done`; `emit-landing` sits at `order: 1000`, between the merge gate and
`archive-plan`, and emits unconditionally with no merge-state gate. The document's own admission at
`branch-cleanup.md:1068` states the mechanism.

**UPHELD** — refutation-audit points 1, 2, 3 and 4; correctness items C1, C2, C4, C5, C6, C7, C8, C9,
C10; the D0 population of three; the deliverable verdicts for D1, D2, D3, D5; every "CONFIRMED" row of
the report-claim audit, including the `coderabbitai` paraphrase note, which reproduces exactly (the
posted body reads *"Auto reviews are limited based on label configuration"* with *"Excluded labels (none
allowed) (1): skip-bot-review"*).

**OVERSTATED, and corrected in place:**

1. *"Three of them are non-merging."* Four of the six branches do not merge. Branch B (local-only) is the
   fourth; it is excluded from the blocker because that lane has no PR by design and the payload spec
   accommodates `n/a`, but its headline still renders `shipped as n/a (n/a)`, which is C2's finding. The
   count and the reasoning for the exclusion are now both stated.
2. *C3: the `merge_mechanism` discriminator "is never named at the consuming site."* It **is** named, at
   `emit-landing.md:137`, among the typed facts to transcribe. What is missing is narrower and still real:
   it is never named in item 4's derivation rule as the thing that decides `merge_state`.
3. *C1: the gate-absence grep "returns only the write call itself and the error-handling row."* It returns
   three lines, not two; the third (`:68`) is incidental. Corrected so the search reproduces.
4. *The dispatch loop's behaviour on a non-`done` step is "continue to the next step" per `SKILL.md:1057`,
   `:592`.* Those two lines are the **timeout** paths, and support only the `failed` case. The claim the
   argument actually needs — that nothing halts on `done` — now rests on `SKILL.md:720` and `:37`, which
   state it directly.
5. *C8: `SKILL.md:772` and `SKILL.md:883` name `emit-landing` among the inline consumers.* Line 883 names
   `default:finalize-step-preference-emitter`, not `emit-landing`. The second supporting citation is
   `:848`. The finding itself — that the step is absent from the roster document that claims closure over
   every registered step — is unaffected and reproduces.

**REFUTED, and corrected:** the closing sentence *"Seven follow-up items are recorded in `gaps.md`."*
`gaps.md` carried ten entries, and now carries eleven.

**Could not verify:** the report's claim that an independent verification sub-agent returned REFUTATION
CONFIRMED on six checks. No sub-agent artifact is persisted anywhere in the repository; the row stays
UNVERIFIABLE. This is the only claim in the report that cannot be settled from the tree, and it is not
the same as refuted — the sub-agent may well have run and concluded exactly that. Its Q1/Q2 conclusions
are nonetheless contradicted by C1 and C4.

### What this pass added

- **C11**, a defect neither the run nor the first pass found: the PR body, the third D0 member, neither
  carries an as-of anchor nor is recomposed after a loop-back. `create-pr` declares no `head_dependent`,
  so an already-`done` record is skipped; its existing-PR branch reuses the PR without rewriting the body;
  and no other finalize step calls `pr edit` over it. Found by taking D4's *Done when* literally — it
  quantifies over **every** D0 member, and both the run and the first pass assessed only one.
- **A corrected D0 verdict.** The population of three is right, but the report's per-member staleness cell
  for the PR body answers the content question in the regeneration column.
- **A corrected D4 verdict**, now assessed against all three members rather than one.
- **A stale-doc sweep** with its negative results named: `create-pr.md:169-172` and
  `branch-cleanup.md:1801` are stale restatements; `inbox-envelope.md:97` and the four `lessons-capture.md`
  landing references are current and were checked.
- **A prose-literal sweep of the landing path**, which found none — `compose_envelope` and
  `check_landing_completeness` carry no fact-asserting strings, and the landing's one false sentence lives
  in the producer document, not in code.
- **G8** in `gaps.md` for C11, plus corrected line citations, a corrected entry count, and a contiguous
  renumbering by severity.

### The verdict does not change

`verified-with-gaps` stands. The refutation's trigger was correct and the report was the right
deliverable for it; its closure argument fails on three of six deliverables and now on a fourth member of
a fifth. Nothing found in this pass argues for closing the plan as satisfied, and nothing found argues
that the run should have implemented D0–D5 as scoped — the premise really had been inverted before the
run started.
