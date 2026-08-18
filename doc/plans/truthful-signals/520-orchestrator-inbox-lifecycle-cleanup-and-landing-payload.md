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

# Orchestrator inbox lifecycle, cleanup and landing payload tell the truth about what they saw

**Epic:** truthful-signals
**Branch prefix:** `fix` — the substance is four defective signals plus the stale statements around them.

## Problem

Four orchestrator surfaces report a confident value that the machinery underneath does not support,
and each was found by an independent adversarial re-check recorded in a git-tracked `gaps.md` under
`doc/plans/truthful-signals/`.

**The landing drain accepts a documented degraded value as a fact.** `check_landing_completeness`
(`marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/_orchestrator_inbox.py`) computes
`missing = [key for key in LANDING_REQUIRED_KEYS if not facts.get(key)]`. The producer
(`phase-6-finalize/standards/emit-landing.md`) explicitly sanctions writing `n/a` for any field it
could not read, and `n/a` is truthy, so a landing whose token total, step list and deliverable counts
all failed to read reports `complete: true`. `plan-orchestrator/workflow/analyze.md` converts
`complete: true` into "the landing transmitted its whole mechanisable delta … a subsequent operator
paste yields nothing new from that plan".

**The compaction report calls an unreachable section a preserved one.** `_abstained_sections` in
`plan-orchestrator/scripts/orchestrator.py` classifies a `##` section as abstained-from unless it
*contains* a `BEGIN GENERATED` marker, and emits `treatment: preserved_verbatim` for every such
section. A derivable surface whose markers are absent — the case `_replace_block` reports as
`markers_absent` — therefore lands in `abstained[]` claiming it was preserved by choice. The
function's own docstring asserts the opposite property ("what lets a reader tell 'nothing needed
touching' from 'the stage could not see it'"). On every `epic.md` scaffolded before the
`ordered-queue` marker pair shipped, this is the default output, not an edge case.

**The inbox drain never reads the state fields the inbox now carries.** `inbox list` returns
`lifecycle`, `live_count` and `closed_senders`, and `close-stream` files a `stream-end` marker; the
only consumer, `plan-orchestrator/workflow/analyze.md`, routes every row on `kind` alone through a
table with no escape hatch. A `superseded` message whose `kind` is `landing` is routed to a full ship
reconciliation — a `landings/` write and a `queue --transition … --status shipped` — for a landing its
own envelope records as retired. A `stream-end` marker carries `kind=finding` by design and is
absorbed as a substantive observation. In the same area, nothing enforces the marker's stated meaning:
a sender can write after closing, and can close twice, and `closed_senders`' set dedup hides it.

**The repository's own committed configuration hides the knobs the epic surfaced.** `.plan/marshal.json`
is git-tracked (`.gitignore` ignores `.plan/*` then re-includes `!.plan/marshal.json`), it is present
in every clone, and its `orchestrator` block still reads `{"auto_emit": false}` while
`_config_defaults.ORCHESTRATOR_KNOWN_KEYS` names three keys. The plan that surfaced the knobs skipped
this file on the false premise that it is git-ignored and absent from a cloud clone.

Around those four sit a set of enumerations, docstrings and run-report figures that stopped being
complete or never reproduced — each named by id below.

## Goal

Every one of the four signals reports what the machinery can actually support: a landing whose facts
are degraded is incomplete, a section the compaction stage could not reach is distinguishable from one
it chose to leave alone, the drain acts on the lifecycle state it is handed and the `stream-end`
marker means what the documents say it means, and this repository's own configuration surfaces the
orchestrator knobs an operator is told to discover there. The enumerations and records around them
state a set the tree agrees with, or state their own population.

## Deliverables

Deliverables run in order, and the four `high` gaps land in D2–D5 so a run that stops early has
shipped them. **Every count in this plan is a lead, never a fact — re-derive it at the moment of the
change and write the re-derived value, not the one written here.**

1. **D1 — Derivation gate** *(closes no gap; gates D2, D5 and D7)* — derive four populations from the
   tree and record each derived value in the run report before any edit:
   (a) the `inbox` sub-verb set, from the `actions.add_parser(...)` calls inside `_add_inbox_group`
   in `marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/orchestrator.py`;
   (b) the envelope-validation rejection codes reachable from `cmd_inbox_validate`, by reading
   `validate_envelope` and `_validate_state_fields` in
   `marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/_orchestrator_inbox.py`;
   (c) the orchestrator config key set, from `ORCHESTRATOR_KNOWN_KEYS` in
   `marketplace/bundles/plan-marshall/skills/manage-config/scripts/_config_defaults.py`;
   (d) whether `.plan/marshal.json` is tracked in this clone, via `git ls-files .plan/marshal.json`.
   **If (a), (b) or (c) cannot be derived from code — the symbol is gone, renamed, or the registration
   is no longer enumerable — HALT the plan and report which premise failed.** Do not substitute a
   hand-written list for a derivation that failed; a hand-maintained enumeration is the defect D7
   exists to remove. If (d) returns nothing, D2's configuration half is dropped with that reason
   recorded and D2's documentation half still ships.
   *Done when:* the run report carries the four derived values verbatim, each with the file and symbol
   it came from, and either all of (a)–(c) succeeded or the run halted naming the failed premise.

2. **D2 — The orchestrator block is discoverable where operators actually read it**
   *(closes 090/G1, 090/G2, 090/G3)* — three parts.
   (i) Add the keys D1(c) derived and the committed file lacks to the `orchestrator` block of the
   tracked `.plan/marshal.json`, preserving the existing `auto_emit` value and the file's top-level
   key order. ⛔ Do **not** run `manage-config sync-defaults` instead: it re-stamps
   `system.provisioned_version` and `system.config_seed_fingerprint` and back-fills
   `plan.phase-6-finalize.steps.default:emit-landing`, three further committed-file changes that belong
   to other plans (see Out of scope).
   (ii) Add a regression guard to `test/plan-marshall/manage-config/test_config_defaults.py` — e.g.
   `test_committed_marshal_json_surfaces_every_orchestrator_knob` — asserting
   `set(committed['orchestrator']) == set(ORCHESTRATOR_KNOWN_KEYS)`, using the existing
   `_COMMITTED_MARSHAL_PATH`. The two existing committed-file tests assert top-level key order only and
   read inside no block, so adding inner keys must not disturb them; confirm that by running them.
   (iii) Correct the documentation: in
   `marketplace/bundles/plan-marshall/skills/extension-api/standards/marshal-json-reference.md`
   § "Orchestrator Configuration", state that `init` seeds every knob at its effective default, that
   each seeded default resolves exactly as the unset key did, and that a legacy `auto_emit`-only block
   stays valid and is back-filled by `sync-defaults`; rewrite the table row so its parenthetical
   reflects the seeded shape rather than "empty `{}` legal", and make the seeded value the stated
   default in the `parallelization_scope` paragraph with the unset case as the legacy note. Retire the
   "Reserved extension slot (PLAN-48)" framing at every site that presents the shipped `auto_emit` as
   future or reserved — re-derive that site set with a `PLAN-48` sweep over `marketplace/` rather than
   trusting the four sites the gap names.
   *Done when:* the guard test passes against the edited file **and has been seen RED** against the
   pre-edit `{"auto_emit": false}` block; and a `PLAN-48` sweep over `marketplace/` returns no hit that
   describes `auto_emit` as reserved or future, and no sweep hit presents the seeded orchestrator block
   as empty or the seeded `parallelization_scope` as absent.

3. **D3 — A degraded landing fact is missing, and the spec claims only what the check enforces**
   *(closes 302/G1, 302/G2, 302/G9)* — three parts, all in the landing-payload contract.
   (i) In `_orchestrator_inbox.py`, add a sentinel set (`{'n/a'}`, case-insensitive, after strip) and
   treat a required key whose value is a sentinel as MISSING for every key that can never legitimately
   be unknown — `plan_id`, `deliverables_total`, `deliverables_done`, `total_tokens`, `steps`. `schema`
   needs no entry: the preceding `facts.get('schema') != LANDING_FACTS_SCHEMA` branch already
   fail-closes on any other value. Keep `pr` and `merge_state` allowed to be `n/a` — "no PR exists" is
   a real state the payload spec names — and state that asymmetry in the docstring.
   (ii) Reconcile `landing-payload-spec.md` with what the check enforces. **The choice is made here, so
   the run makes no judgement call:** keep `total_wall_seconds`, the per-step typed facts and the
   repository end-state OPTIONAL, and correct the *delta table* instead — its "Routed as" cells must
   say that `steps` carries per-step outcomes only and that the typed facts and the wall-clock ride
   optional keys — then amend the `complete: true` bullet in
   `plan-orchestrator/workflow/analyze.md` so it claims only what the required set covers. The
   alternative (promoting those rows to required) would change the producer contract in
   `phase-6-finalize`, which this plan does not touch; record it in the run report as a **proposal for
   the operator**, not as work done.
   (iii) Rewrite the `#:` comment above `LANDING_REQUIRED_KEYS` so it states what is true — the
   constant is the executable authority, and `landing-payload-spec.md` § "Required machine-readable
   fact keys" and `emit-landing.md` Step 2 restate the same set for their readers — naming both sites,
   and not contradicting `landing-payload-spec.md`'s own tie-break sentence about which document wins.
   *Done when:* `check_landing_completeness` on a landing whose `total_tokens` / `steps` /
   `deliverables_*` are `n/a` returns `complete: False` naming exactly those keys, while a landing with
   `pr=n/a` / `merge_state=n/a` and every other key real still returns `complete: True` — both pinned by
   cases added to `test/plan-marshall/plan-orchestrator/test_landing_completeness.py`, and the first
   case **seen RED before the sentinel change lands**; and every row `landing-payload-spec.md`'s delta
   table classifies MECHANISABLE is either in `LANDING_REQUIRED_KEYS` or recorded in that table as
   optional, with no sentence in either file claiming `complete: true` means more than the required set
   covers.

4. **D4 — The compaction report distinguishes could-not from chose-not, and its own tests mean
   something** *(closes 180/G6, 180/G4, 180/G1, 180/G8)* — four parts in the compact stage.
   (i) In `orchestrator.py`, pass the per-block outcomes `cmd_compact` already computes into
   `_abstained_sections` (or the set of block names whose outcome was `markers_absent`, keyed to the
   owning heading) and emit a distinct treatment — e.g. `markers_absent_not_regenerated` — for a
   section carrying a derivable surface the stage could not reach, excluding it from `abstained_count`
   or adding a separate `unreachable_count`. Update the function docstring and the report-contract
   statements in `plan-orchestrator/SKILL.md` and
   `persona-plan-orchestrator/standards/orchestration-model.md` § Ledger-Compaction Stage so all three
   describe the emitted vocabulary.
   (ii) Add the three compaction keys to `plan-orchestrator/workflow/cleanup.md`'s `## Output` TOON
   block with the shapes the script emits —
   `compaction_regenerated[R]{surface,outcome,lines_before,lines_after}`,
   `compaction_invariants[I]{invariant,verdict,evidence,population}`,
   `compaction_abstained[A]{section,treatment}` — state each as required-never-omitted the way
   `declined[]` already is, and make the Step 8 instruction name those keys.
   (iii) Repair the tautology in
   `test/plan-marshall/plan-orchestrator/test_orchestrator_compact.py`
   `TestNarrativeSurvivesVerbatim::test_every_hand_authored_section_survives_verbatim`: its closing
   `assert after == text or after == _epic_text(plan_context)` re-reads bytes nothing wrote between the
   two reads, so the second disjunct is true by construction. Either perform the second `_run()` the
   comment claims and assert byte-identity across it, or delete the disjunctive assertion and fix the
   two comments that describe operations the test never performs.
   (iv) Extract the branch body shared by `_invariant_queue_spec` and `_corpus_signal` into one helper
   returning a neutral `(state, evidence, population)` triple, with each caller mapping it into its own
   vocabulary; keep both public shapes unchanged so the existing suites pass unedited.
   *Done when:* a `compact` run over an `epic.md` whose `## Ordered Queue` carries no marker pair emits
   an `abstained[]` row whose `treatment` is not `preserved_verbatim`, pinned by a case in
   `TestMarkersAbsent` **that was seen RED against the current code before the fix landed**; the
   repaired narrative test contains no assertion whose truth is independent of the code under test and
   **was seen RED when its first disjunct alone is asserted against the pre-fix tree** (the gap records
   `1 failed, 31 passed` — re-derive, do not trust the figure); `cleanup.md`'s `## Output` block
   declares a key for each of the three; and exactly one function in `orchestrator.py` branches on
   `unreadable_count` / `rows_without_spec_count` / `specs_without_row_count`.

5. **D5 — The drain acts on lifecycle, and `stream-end` means what the documents say**
   *(closes 250/G3, 250/G2, 250/G12, 250/G9)* — four parts.
   (i) In `plan-orchestrator/workflow/analyze.md` Step 3, add two rules **before** the `kind`-routing
   table: a row whose `lifecycle` is `superseded` is recorded as retired-by-successor, archived, and
   its `kind` branch is not run; a row whose `lifecycle` is `stream-end` is treated as a control
   record — archived and noted as the sender's closure, never routed to the `finding` branch. Both new
   dispositions still archive, so extend the `drained[]` disposition vocabulary with the two tokens and
   restate the closure invariant in the same edit so
   `messages_archived + messages_invalid + messages_archive_failed == messages_scanned` still holds
   with both counted inside `messages_archived`. In Step 6, key the empty-vs-finished conclusion on
   `live_count` plus `closed_senders` rather than on `count`.
   (ii) Rewrite fact 2 of `cleanup.md` Step 9. It asserts "**No quiescence signal exists today**, and
   none will arrive until a successor spec supplies one" — an absolute the tree now contradicts.
   **The choice is made here:** the refusal stands, but on a true reason. Name `inbox list`'s
   `closed_senders` / `live_count` explicitly, state precisely why a per-sender stream closure is not
   epic-wide emission quiescence, and keep the deferred-mechanism block as the surface a successor
   reuses. Record "drain per closed sender" in the run report as a **proposal for the operator**, not as
   work done.
   (iii) Enforce the marker in `_orchestrator_inbox.py`: add one shared predicate — does this sender
   already have a valid `lifecycle=stream-end` marker in `inbox/`? — and consult it at both entry
   points, so `cmd_inbox_write` refuses with a new documented `stream_closed` error code and
   `cmd_inbox_close_stream` returns idempotent success naming the existing marker instead of allocating
   a second one. Document the new code in `standards/inbox-envelope.md` § Write-side deliverability
   (alongside the `undeliverable_to_running_plan` precedent) and in `SKILL.md` § `inbox write` /
   § `inbox close-stream`. Enforcement is chosen over downgrading the prose because (i) lands the first
   real consumer of `closed_senders` in the same change.
   (iv) Amend `standards/inbox-envelope.md` and `SKILL.md` so `live_count: 0` with an empty
   `closed_senders` means EMPTY only when `invalid_count` is also `0`, and name the third zero
   explicitly (`live_count: 0` with `invalid_count > 0` — a queue blocked on messages the drain refuses
   to consume).
   *Done when:* a drain walked over a queue holding one `kind=landing` `lifecycle=superseded` message
   and one `stream-end` marker writes no `landings/` record, makes no `queue --transition` call,
   absorbs no finding, reports the sender as closed, and still satisfies the closure equation — checked
   by reading `analyze.md` end to end, since the workflow is LLM-executed markdown with no entry point;
   a `write` following a `close-stream` for the same sender is refused with the new code and a second
   `close-stream` returns idempotent success, both pinned by tests in
   `test/plan-marshall/plan-orchestrator/` **each seen RED against the pre-fix handlers** (the gap
   records the pre-fix behaviour as both calls succeeding); a test pins the blocked-queue zero as
   distinct from the empty zero; and `cleanup.md` Step 9 no longer asserts that no quiescence signal
   exists.

6. **D6 — What the epic tree holds, how a pre-marker `epic.md` gets migrated, and what the lane's
   dispatch emits** *(closes 180/G3, 180/G7, 180/G2, 280/G7)* — four parts, all in
   `persona-plan-orchestrator/standards/orchestration-model.md` and
   `plan-orchestrator/workflow/cleanup.md`.
   (i) Declare `settled.md` where the standard says what an epic tree contains: add it to the
   tree-layout code block between `history.md` and `references.json`, commented as relocated settled
   narrative written mid-life by the compact stage with pointers in `epic.md` resolving there, and add
   it to the ledger-document parenthetical in § Carve-outs. The standard already mandates the file
   elsewhere and `cleanup.md` already links to that carve-out list.
   (ii) Add a one-time migration step to `cleanup.md` § Step 8, **before** the script call: when
   `epic.md` carries a `## Ordered Queue` section and no `BEGIN GENERATED: ordered-queue` marker, the
   orchestrator inserts the marker pair around the existing table and moves any per-row `Notes` content
   into the `### Queue annotations` zone, writing through the direct-file-write carve-out rather than
   through the script. State the same one-time obligation in § Ledger-Compaction Stage next to the
   never-fabricate rule, so the refusal and its remedy are read together.
   (iii) In the same Step 8 migration, instruct the orchestrator to move any hand-written line found
   *between* the markers into the adjacent annotation zone before the first compaction, and add a
   `replaced_body` (or `discarded[]`) field to `cmd_compact`'s payload carrying the pre-write
   between-marker text for every block whose outcome is `regenerated`, with a test asserting the field
   is populated when a block changes — so a first pass over an already-annotated ledger names the
   content it overwrote, not merely a line-count delta.
   (iv) In the standard's "**Canonical form.** One dispatch shape, used verbatim" block, extend the
   resolve to carry `--workflow {the workflow/instructions doc the leaf loads}`, `--plan-id none` and
   `--caller plan-marshall:persona-plan-orchestrator`, and add one sentence stating that the resolve
   seam emits the `[DISPATCH]` line and its paired decision-log record to the dated global log, per
   firing. Pass an explicit `--role orchestrator.{surface}` on the `analyze` / `decompose` sites: a
   `--default` resolve carries no payload role and renders the literal `default`, which is not
   distinguishable in the trail. Verify the emitted label before landing rather than trusting this
   sentence.
   *Done when:* `settled.md` appears in both the tree-layout block and the § Carve-outs list;
   `cleanup.md` § Step 8 carries a marker-insertion step conditioned on the absent marker pair and
   § Ledger-Compaction Stage names the one-time migration; a `compact` run over an `epic.md` whose
   generated block holds a hand-written line names that line's content in the emitted report, pinned by
   a test; and the canonical-form block carries `--workflow` and `--plan-id none`, with the run report
   recording the label a resolve driven from `analyze.md` actually produced.

7. **D7 — Every `inbox` enumeration names the set the code registers**
   *(closes 250/G1, 250/G5, 250/G6, 250/G11, 250/G7, 250/G8)* — six stale or incomplete restatements
   of two populations D1 derived. Use D1(a) for the sub-verb set and D1(b) for the rejection codes;
   write the derived values, never the counts this plan repeats.
   (i) `plan-orchestrator/SKILL.md` § `inbox validate` — extend the rejection-code enumeration to the
   full D1(b) set, keeping the "checked in that order" clause accurate (the state-field checks run
   after the base envelope checks), and add the new codes to the pinned tuple in
   `test/plan-marshall/plan-orchestrator/test_inbox_channel_contract.py`
   `test_inbox_validate_still_lists_every_retained_rejection_code`.
   (ii) `standards/inbox-envelope.md` § Related — extend the argument-surface line to the full D1(a)
   verb set; each name resolves to its own `### inbox {verb}` section in `SKILL.md`, so confirm every
   added name has a target before writing it.
   (iii) `orchestrator.py` — replace the `inbox` subparser's `help=` literal, which still describes the
   pre-correction five-verb surface, with a summary covering correction, stream termination and archive
   foldering alongside append/validate/list/archive/detect; mirror the already-correct module docstring.
   (iv) `orchestrator.py` `_add_inbox_group` docstring — make its "Sub-verbs:" line the full D1(a) set
   in registration order.
   (v) `standards/inbox-envelope.md` § Invariants — the "Append-only, with one sanctioned in-place
   edit" bullet's bolded lead states one verb while its body names three, and it classifies
   `close-stream` as an in-place mutation although `cmd_inbox_close_stream` composes a fresh envelope
   and allocates a new path, opening no existing file. Rewrite it so the lead and the list agree, so
   `close-stream` is classified as an append, and so it stops contradicting the sibling statement in
   `orchestration-model.md` § Ledger Write-Boundary.
   (vi) `_orchestrator_inbox.py` module docstring — the drain-surface paragraph still names
   `inbox/archive/` joined with a bare filename as the only write target, five lines after the
   preceding paragraph states the per-sender foldering. Rewrite it to `inbox/archive/{sender}/`, and
   preserve the one carve-out: a source name matching no message-name pattern deliberately keeps a flat
   destination so its link error still surfaces as `invalid_message_name`. Keep the
   never-a-caller-supplied-path claim intact — it is true in both branches.
   *Done when:* the contract test fails when any one rejection code is deleted from the `SKILL.md`
   section (verified by deleting one and seeing it go RED); the § Related line and the
   `_add_inbox_group` docstring each name exactly the D1(a) set; the argparse help names the correction
   and stream-termination verbs; the Invariants bullet names exactly two in-place verbs with a lead
   stating the same count; and the module docstring names the foldered target and its flat error path.

8. **D8 — Records and registration cosmetics** *(closes 120/G1, 120/G2, 120/G3, 120/G4, 250/G10,
   300/G5)* — grouped because none is behavioural and each is a stale figure or a position.
   (i) `marketplace/bundles/plan-marshall/.claude-plugin/plugin.json` — move the two renamed skill
   entries back to their alphabetical positions (`persona-plan-orchestrator` after
   `persona-plan-marshall-agent`; `plan-orchestrator` after `plan-marshall-plugin`, leaving
   `marshall-steward` directly after `manage-terminal-title`). Change no other entry: re-derive the
   out-of-order adjacent pairs before and after and confirm only those two moved.
   (ii) `doc/plans/truthful-signals/120-…/report-01.md` — the D0 figure, the D0 derivation-population
   bullet, and the D6 rationale. Re-derive the token census at the merge parent `68a21cac`; write the
   re-derived figure *with the base it was derived at*, and record separately that the run's own
   working-tree figure does not reproduce and is unrecoverable. ⛔ Do **not** re-attribute the original
   figure to `68a21cac` — the run derived it from a working tree, and manufacturing provenance is the
   defect this epic exists to close. Correct the population bullet so it no longer claims `.plan/` as a
   whole was excluded (ripgrep honours `.gitignore`'s negations, so the tracked `.plan/` paths were
   *in* the swept population), and correct the D6 rationale so it names which `.plan/` paths are
   tracked and states that they were searched. **If `68a21cac` is unreachable in this clone** (a shallow
   clone), run `git fetch --unshallow` once; if it is still unreachable, drop this sub-item, leave the
   figure untouched, and record in the run report that it was not re-derivable here. Every other
   sub-item of D8 proceeds regardless.
   (iii) `doc/plans/truthful-signals/250-…/report-01.md` — delete the duplicated tail of `_pending_`
   sections (`## Cost`, `## Contract check (Step 9)`, `## What have we learned (Step 9)`, `## Residue`
   appear a second time, unfilled, after all four were filled earlier in the file) and correct the two
   stated test counts to the values a re-run produces. ⚠ D5 and D7 change these suites, so re-derive the
   counts **at the merge-base state the report describes**, not from your own working tree, and say
   which state the corrected figure was taken at.
   (iv) `doc/plans/truthful-signals/300-…/report-01.md` — the stale-restatement figure appears at more
   than one site; re-derive the disposition table's own multiplicities and make every statement of the
   figure equal that sum, or restate each as "{sites} sites / {statements} statements".
   *Done when:* the `plugin.json` adjacent-pair check shows the two named entries in order and no other
   entry moved; each corrected report figure is stated together with the population or base it was
   derived at; and no corrected figure in any of the three reports is contradicted by that report's own
   evidence table.

## Out of scope

- **250/G4 — running the physical archive migration and reporting per-sender counts.** Its population
  is `.plan/local/orchestrator/{epic}/inbox/archive/`, which lives under the git-ignored part of
  `.plan/` and is **absent from this clone**. A cloud run can neither perform the migration nor verify
  it, and authoring it here would produce a deliverable that cannot be settled. The run report records
  it as an operator obligation for a machine that holds the orchestrator store.
- **`plan.phase-6-finalize.steps.default:emit-landing` in `.plan/marshal.json`.** D2 touches only the
  `orchestrator` block. The finalize-step registration is owed by a different plan (302/G7, in
  `doc/plans/truthful-signals/302-…/gaps.md`), it must land together with that plan's
  dispatch/inline roster row or the roster closure test turns red in one direction or the other, and
  running `sync-defaults` to get it would drag in two unrelated re-stamps.
- **Wiring typed producers for `pr` and `merge_state`, and `emit-landing`'s `records_facts`
  declaration** (302/G3, 302/G4). Both change `phase-6-finalize` step contracts, which this plan does
  not touch; D3 deliberately corrects the *claim* rather than widening the required set, so the
  producer side stays untouched and reviewable on its own.
- **Promoting `total_wall_seconds` and the per-step typed facts to required keys.** Named in D3 as the
  alternative and recorded as a proposal, not taken: it changes what a conforming producer must emit,
  which would make every landing written before the change incomplete.
- **The four pre-existing `plugin.json` ordering inversions** that predate the rename. D8(i) restores
  only the two positions the rename disturbed; fixing the others is an unrelated tidy-up whose diff
  would obscure the two entries this plan is accountable for.
- **The plugin cache and `.plan/execute-script.py`.** Both are machine-local build artifacts absent
  from a fresh clone; per `CLAUDE.md` § Standalone Plan Lane a cloud run neither syncs the cache nor
  records the sync as owed.

## Expected surface

**HYPOTHESIS** — this list is derived from the `Where` lines of the gap entries this plan closes and
is expected to be complete, but a fix may reach one file further. Confirm/refute artifact: the run's
own `git diff --stat` against the merge base, compared with this list in the run report.

- `.plan/marshal.json` — D2(i); **git-tracked** (`.gitignore` ignores `.plan/*` then re-includes
  `!.plan/marshal.json`), so it is in the clone and is edited like any other tracked file. D1(d) checks
  this before D2 relies on it.
- `marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/_orchestrator_inbox.py` — D3(i),
  D3(iii), D5(iii), D7(vi).
- `marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/orchestrator.py` — D4(i), D4(iv),
  D6(iii), D7(iii), D7(iv).
- `marketplace/bundles/plan-marshall/skills/plan-orchestrator/workflow/analyze.md` — D3(ii), D5(i).
- `marketplace/bundles/plan-marshall/skills/plan-orchestrator/workflow/cleanup.md` — D4(ii), D5(ii),
  D6(ii), D6(iii).
- `marketplace/bundles/plan-marshall/skills/plan-orchestrator/SKILL.md` — D4(i), D5(iii), D5(iv),
  D7(i).
- `marketplace/bundles/plan-marshall/skills/plan-orchestrator/standards/inbox-envelope.md` — D5(iii),
  D5(iv), D7(ii), D7(v).
- `marketplace/bundles/plan-marshall/skills/plan-orchestrator/standards/landing-payload-spec.md` —
  D3(ii).
- `marketplace/bundles/plan-marshall/skills/persona-plan-orchestrator/standards/orchestration-model.md`
  — D4(i), D6(i), D6(ii), D6(iv).
- `marketplace/bundles/plan-marshall/skills/extension-api/standards/marshal-json-reference.md` —
  D2(iii).
- `marketplace/bundles/plan-marshall/skills/plan-marshall/standards/effort-roles.md` and
  `marketplace/bundles/plan-marshall/skills/manage-config/scripts/manage-config.py` — D2(iii), the
  PLAN-48 sweep sites.
- `marketplace/bundles/plan-marshall/.claude-plugin/plugin.json` — D8(i).
- `test/plan-marshall/manage-config/test_config_defaults.py` — D2(ii).
- `test/plan-marshall/plan-orchestrator/test_landing_completeness.py` — D3.
- `test/plan-marshall/plan-orchestrator/test_orchestrator_compact.py` — D4, D6(iii).
- `test/plan-marshall/plan-orchestrator/test_inbox_channel_contract.py` and its sibling inbox suites —
  D5, D7(i).
- `doc/plans/truthful-signals/{120,250,300}-…/report-01.md` — D8(ii)–(iv).

## Claim labels

| Claim | Label | Confirm/refute artifact |
|---|---|---|
| 090/G1 reproduces at HEAD: the tracked `.plan/marshal.json` `orchestrator` block carries only `auto_emit`, while `ORCHESTRATOR_KNOWN_KEYS` names three keys | OBSERVED | `.plan/marshal.json` → `orchestrator`; `manage-config/scripts/_config_defaults.py` → `ORCHESTRATOR_KNOWN_KEYS` |
| 302/G1 reproduces at HEAD: the completeness check rejects only empty values | OBSERVED | `_orchestrator_inbox.py` → `check_landing_completeness`, the `missing = [key … if not facts.get(key)]` line |
| 180/G6 reproduces at HEAD: every abstained section is emitted as `preserved_verbatim`, unconditionally | OBSERVED | `orchestrator.py` → `_abstained_sections`, the `abstained.append({… 'treatment': 'preserved_verbatim'})` line |
| 250/G3 reproduces at HEAD: `analyze.md` reads none of `lifecycle` / `live_count` / `closed_senders` / `superseded` / `stream-end` | OBSERVED (asserted absence — re-verify) | a whole-file sweep of `plan-orchestrator/workflow/analyze.md` for those tokens; at authoring it returned one unrelated hit ("closed lifecycle"). Re-derive: an absence is the higher-risk claim |
| 250/G12 reproduces at HEAD: no `stream_closed` enforcement exists at either entry point | OBSERVED (asserted absence — re-verify) | a sweep of `_orchestrator_inbox.py` for `stream_closed`, plus reading `cmd_inbox_write` and `cmd_inbox_close_stream` |
| 280/G7 reproduces at HEAD: the orchestrator lane emits no dispatch record on either surface | OBSERVED (asserted absence — re-verify) | a `DISPATCH` sweep over `persona-plan-orchestrator/` and `plan-orchestrator/`; at authoring it returned zero hits |
| Closing 250/G3 raises 250/G12 from `medium` to `high`, because it lands the first real consumer of `closed_senders` | HYPOTHESIS | `doc/plans/truthful-signals/250-inbox-has-no-amend-or-supersede-verb/gaps.md` § G12 "Why it matters", which states the coupling |
| Narrowing `cleanup.md` Step 9's refusal reason (D5(ii)) breaks no other consumer, because no other document depends on the absolute "no quiescence signal exists" claim | HYPOTHESIS | a sweep for "quiescence" across `marketplace/bundles/plan-marshall/skills/plan-orchestrator/` and `persona-plan-orchestrator/` before the edit |
| The population 180/G7 affects (live `epic.md` files predating the `ordered-queue` markers) cannot be counted from this clone | OBSERVED | the affected files live under the git-ignored `.plan/local/orchestrator/`; the *contract* gap is fully observable in `templates/epic.md` and `orchestration-model.md` and is what D6 fixes |
| The expected surface above is complete | HYPOTHESIS | the run's `git diff --stat`, compared against the list |

An asserted **absence** is verified exactly as an asserted presence and is the higher-risk half:
three of the claims above are absences, and each names the sweep that settles it. Re-run every one —
this plan was authored against a tree that may have moved.

## Verification

Beyond each deliverable's *Done when*:

- **Build gate.** D2–D8 change `*.py` under `marketplace/bundles/` and `test/`, so the lane's Python
  build gate applies; run it and read the result rather than the exit code.
- **Red-first, explicitly.** Four guards must be **seen RED before their fix lands**, and the run
  report records the failing output for each: D2's committed-config guard against the pre-edit block;
  D3's all-`n/a` completeness case; D4's `TestMarkersAbsent` treatment case; D4's repaired narrative
  assertion with only its first disjunct; D5's post-closure `write` refusal and double-`close-stream`
  idempotence; and D7(i)'s rejection-code contract test with one code deleted from the section. A guard
  never seen red is not evidence, and 180/G1 is on this plan precisely because a green assertion was
  carrying no weight.
- **Three cold reads.** Each of the following is text whose whole value is what a later reader *does*
  with it, so "implemented as specified" cannot settle it. Dispatch an independent reader who has not
  seen this plan, give them only the edited passage, and have them **report which reading they took**:
  1. `cleanup.md` § Step 9 after D5(ii) — does the reader conclude the drain is refused, or permitted
     for a closed sender? The intended reading is **refused, with a narrower stated reason**.
  2. `cleanup.md` § Step 8 after D6(ii)–(iii) — does the reader perform the marker insertion and the
     annotation move *before* calling the script, and only when the marker pair is absent?
  3. `landing-payload-spec.md`'s delta table plus `analyze.md`'s `complete: true` bullet after D3(ii) —
     does the reader conclude `complete: true` means the whole mechanisable delta drained, or only the
     required-key subset? The intended reading is **the required-key subset**.
  A wrong reading means the wording failed however complete the diff looks; fix the wording and read
  again.
- **Coverage check by id.** The run report lists all 31 gap ids (30 closed by a deliverable, one excluded under
  § Out of scope) from the seven source `gaps.md` files
  this plan draws on, each against the deliverable that closed it or the Out-of-scope entry that
  excluded it. Re-derive the id set from `doc/plans/truthful-signals/{090,120,180,250,280,300,302}-…/gaps.md`
  rather than trusting this plan's grouping — those files are git-tracked and readable in the clone.
- **Re-derive every count.** No figure in this plan is trustworthy: not the verb count, not the
  rejection-code count, not the orchestrator key count, not any report figure. Each written value in
  the run report names the command or file it was derived from, at the moment of the change.
- **Read `analyze.md` end to end after D5(i).** It is LLM-executed markdown with no entry point, so its
  closure equation and its new dispositions are settled by reading, not by executing. State in the
  report that this check was a read.

## Notes

- **Where the gaps came from.** Every deliverable cites gap ids of the form `{plan}/{Gn}`, resolvable in
  `doc/plans/truthful-signals/{plan}/gaps.md` — all git-tracked and readable from the clone. Each
  entry's sibling `verification.md` carries an `## Adversarial review` section recording which gaps were
  upheld, refuted or re-severitied; where a gap body and that section disagree, the section wins. No
  gap assigned to this plan was dropped as already-closed: all 31 were re-checked against HEAD during
  authoring and all 31 still reproduce.
- **`.plan/` in this lane.** The git-ignored parts — `.plan/local/**` (the orchestrator ledger, plan
  specs, landing records, epic trees) and the generated `.plan/execute-script.py` — are **absent from
  this clone. Do not go looking for them, and do not try to run the executor.** Two paths under `.plan/`
  *are* tracked and present: `.plan/marshal.json` and `.plan/project-architecture/`. D2 edits the first
  with ordinary file tools; D1(d) confirms it is tracked before D2 relies on it. The lane contract's
  note that a lane run "never touches `.plan/`" describes the typical run — it is not a prohibition on
  editing a tracked file that happens to live at that path. If the run reads it as one, it records the
  disagreement per the first-instruction block rather than silently skipping D2.
- **Two decisions are already made, so the run makes neither.** D3(ii) keeps the optional keys optional
  and corrects the claim; D5(ii) keeps the archive-drain refusal and corrects its reason. In both cases
  the alternative is recorded in the run report as a proposal for the operator. No deliverable in this
  plan requires a mid-run judgement call.
- **Sequencing within the plan.** D5 and D7 both edit `orchestrator.py`, `_orchestrator_inbox.py`,
  `SKILL.md` and `inbox-envelope.md`; D4 and D6 both edit `orchestrator.py`, `cleanup.md` and
  `orchestration-model.md`. Land them in the stated order so the later edit sees the earlier one, and
  keep the marker-migration text (D6(ii)) and the `replaced_body` field (D6(iii)) in one commit — they
  are the two halves of one migration story.
- **Two commits that must not be split apart.** D2(i) and D2(ii) land together: the guard test asserts
  against the committed file, so a commit carrying one without the other is red. Likewise D5(iii)'s new
  error code and its documentation.
- **What this plan deliberately leaves next door.** 302/G5 (the dispatch/inline roster row) and 302/G7
  (the finalize-step registry entry) are coupled to each other and to neither of this plan's halves;
  the run report should name them as the pair a follower must land together.
