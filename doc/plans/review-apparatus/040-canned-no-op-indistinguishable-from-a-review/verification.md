# Verification — 040-canned-no-op-indistinguishable-from-a-review

**Landed as:** PR #1165, squash commit `fd292004`
**Verdict:** verified-with-gaps

The plan's central mechanism landed and is real: the three-valued `rate_limit_class` no longer collapses,
a state distribution reaches `display_detail`, a deficit signal exists with the right verdict vocabulary
for the baseline axis, and the contract document states the counting rule with its populations. Its D4
tests are discriminating rather than decorative — a naive count-only detector, constructed and run as a
mutant, fails five of the nine deficit tests including both load-bearing negative cases. Three material
gaps remain. **The plan's own title condition is still live on its second surface:** the retrospective's
`comparison` grade separates *reviewed-clean* from *nobody-reviewed* only when it is handed the
reviewed-at-all set, and its own SKILL.md states that no persisted handoff of that classification reaches
the step, instructing the step to pass the flag bare — so every zero-findings run, reviewed or not, grades
`indeterminate` and renders one string. The deficit signal is never invoked by any workflow. And its
rendered envelope suppresses the very populations the plan required it to publish — printing
`verdict: clean` with no row at all for a required reviewer that did not review, and printing no
population line whatsoever on `unassessable`.

## Method

Read in full: `plan.md`, `report-01.md`.

Read the landed diff: `git show --stat fd292004`, then per-path `git show fd292004 -- <path>` for
`review_completeness.py`, `review_retrospective.py`, `bot-participation-contract.md`,
`automatic-review/SKILL.md`, `finalize-step-review-retrospective/SKILL.md`, `create-pr.md`,
`pr-review-operations.md`, `github_pr.py`, `_github_pr.py`, and the four test files — the seventeen paths
the squash touched.

Ground truth is the working tree at `61a43e53`, the newest commit touching anything outside
`doc/plans/`; `git log --oneline 61a43e53..HEAD --name-only` filtered against `doc/plans/` returns no
source path, so later commits move no code this document cites. Later landings over the same code were
separated with `git log --oneline fd292004..HEAD -- <paths>`, which names three follow-ups touching
`review_completeness.py` (`6ba4dace` #1167, `064560ab` #1168, `9e9e9880` #1241) and one touching the
retrospective (`b286928c` #1170); each was confirmed to exist with `git log --oneline -1 <sha>`.

Read the current files whole where relevant: `review_completeness.py` (1558 lines; constants block,
`_refusal_state`, `classify_bot`, `compose_review_state_summary`, `assess_deficit`, `check_completeness`,
`check_deficit`, `_emit_toon`, `_emit_deficit_toon`, the argparse surface), `review_retrospective.py`
(`_grade_comparison`, `aggregate`, `main`), `bot-participation-contract.md` §§ "Failure taxonomy",
"Participation is not review quality", "A refusal resolves by CAUSE first", "Two axes", "The counting
rule", "The comparative deficit signal", "Consumers", and `automatic-review/SKILL.md` §§ participation
guard, "Mark Step Complete", "Output", "Canonical invocations".

Searches run (repository root as the search path unless stated; `__pycache__` hits discounted
throughout):

- `grep -rln "deficit" marketplace/ .claude/ doc/` (excluding `doc/plans`) — four source files, none of
  which is a workflow step. `grep -rn "check_deficit\|assess_deficit\|cmd_deficit\|review_completeness
  deficit" --include=*.py --include=*.md marketplace/ test/ .claude/` — the only non-test callers are
  inside `review_completeness.py` itself; the test-tree hits are a docstring cross-reference
  (`test_review_commitments.py:398`) and two guards in `test_structural_refusal.py` — a cause-agreement
  test (`:385`) and a documentation guard that pins `--refusal-size-caps` into `automatic-review/SKILL.md`'s
  `deficit` invocation block (`:799`).
- `grep -rniE "(five|six|seven|eight|nine|ten|eleven)[ -]member" --include=*.md --include=*.py
  marketplace/ test/ .claude/ doc/developer/`, widened with `"one of ten|of the ten|ten non-participation"`
  because two sites state the count in forms the first pattern misses — **seven** taxonomy-count
  statements, all reading "ten", all correct (the remaining hits are unrelated metrics-bucket and
  HEAD-dependence prose).
- `grep -rn "refused_awaitable" … | grep -v "refused_unknown"` — fifteen hits, every one a single-member
  mention in context; no surviving two-way refusal enumeration.
- `grep -rn "comment(s) found" --include=*.md --include=*.py marketplace/ test/ .claude/` — nine hits, all
  in the changed sites or their tests; no stale restatement elsewhere. `grep -rn "unified triage pending"`
  over the same tree returns the same five `automatic-review/SKILL.md` template sites and nothing else.
- `grep -rn "_STATE_SUMMARY_BUCKETS" test/ marketplace/ .claude/` — three hits, all inside
  `review_completeness.py`; no test references the constant.
- `grep -rn "required_reviewed" test/` — no test asserts the field.
- `grep -rn "min_deficit\|min-deficit" bot-participation-contract.md automatic-review/SKILL.md` — the
  contract never mentions the threshold; only `SKILL.md:1011` restates the default.
- `grep -rn "summary card\|already reviewed\|trigger acknowledg\|Review finished" --include=*.md` over
  `automatic-review/` and `workflow-integration-github/` — no output; widened to
  `"participation artifact\|persistent summary\|not diff-derived\|acknowledgement"` it returns two
  unrelated hits.
- `grep -n "required_bots\|optional_bots" .plan/marshal.json` — this repository configures
  `required_bots: pr-agent`, `optional_bots: coderabbit,sourcery` at `:117-118`. That file is
  git-ignored, so this one figure is machine-local rather than re-derivable from a fresh clone.
- `grep -rn "\-\-display-detail" --include=*.md marketplace/ .claude/ | grep "—"` — the em-dash
  `display_detail` template is not unique to this plan; `architecture-refresh.md` prescribes em-dash
  strings at `:124`, `:196`, `:412` and again in its error table at `:467-471`.
- `grep -rn "bot_states" --include=*.md --include=*.py marketplace/ .claude/` — every hit is an
  in-memory read of `review_completeness check`'s immediate TOON or a docstring about it. Nothing writes
  the classification anywhere a later step can read, which is the substantiating search behind C7.

Pre-fix comparison: `git show fd292004^:<path>` for `review_completeness.py` (lines 309-311) and
`review_retrospective.py` (line 201), confirming both "before" claims literally.

Tests run (read-only):

```
UV_HTTP_TIMEOUT=600 uv run python -m pytest \
  test/plan-marshall/automatic-review/test_review_completeness.py \
  test/plan-marshall/finalize-step-review-retrospective/test_review_retrospective.py \
  -o addopts="" -q
→ 184 passed
```

Behavioural probes executed against the library functions with the marketplace `scripts` dirs on
`sys.path` (no repository file modified):

```python
rc.assess_deficit(
    [{'bot_kind': 'pr-agent', 'reviewed': False, 'finding_count': 0},
     {'bot_kind': 'coderabbit', 'reviewed': True, 'finding_count': 4}],
    required_bots=['pr-agent'])
→ {'verdict': 'clean', 'baseline_max': 4, 'baseline_reviewers': ['coderabbit'],
   'required_reviewed': [], 'deficit_reviewers': [], ...}

rc.compose_review_state_summary(
    [{'bot_kind': 'a', 'state': 'refused_teapot'},
     {'bot_kind': 'b', 'state': rc.STATE_REFUSED_HARD}])
→ '1 refused'          # a two-bot roster tallying to one
```

and `rc._emit_deficit_toon` over the `clean`, `unassessable`, and `0 : 0` payloads.

Discrimination probe (mutation): `review_completeness.py` was snapshotted to a scratch directory, its
`assess_deficit` verdict block replaced by the naive count-only detector the plan warns about (`deficit`
iff a required reviewer's `finding_count` is 0, baseline ignored), `pytest -k TestDeficitSignal` run
against the mutant, and the file restored from the snapshot in a `finally` (`git status --porcelain`
clean afterwards for every source path). Result: **5 failed, 4 passed** — the mutant is caught by
`test_row_e_clean_zero_to_zero_with_a_real_baseline`,
`test_rows_c_and_d_unassessable_when_every_baseline_refused`,
`test_required_count_alone_cannot_distinguish_the_rows`, `test_min_deficit_threshold_is_honoured`, and
`test_deficit_cli_declares_non_gating`.

String measurement (arithmetic only, `python3 -c`): `len('0 comment(s) found — 1 empty, 1 refused, 1
refused-structural (unified triage pending)') == 86`, `isascii() is False`; the worst three-bucket
expansion `'0 comment(s) found — 1 refused-structural, 1 not-triggered, 1 in-progress (unified triage
pending)'` measures 98; and the unbounded nine-bucket expansion — reachable on a nine-reviewer roster,
one per bucket — measures 161, so no relabelling alone can bring the template inside the bound. The
review-retrospective surface's own three grade strings measure 73 (`clean`, at its shortest placeholder
expansion), 50 (`vacuous`) and **109** (`indeterminate`, a fixed literal with no placeholder), all three
`isascii() is False`.

## Deliverables

| # | *Done when* (plan) | Report claim | Ground truth in the tree | Verdict |
|---|---|---|---|---|
| D0 | "the contract is written with each population published, and the absence corpus is partitioned by cause" | Contract written in `bot-participation-contract.md`; partition documented as derivable from `refusal_patterns`; HALT does not trigger | § "The counting rule" exists with all three populations named (`bot-participation-contract.md:508-534`). No corpus was partitioned — derivability was documented instead | met-in-substance, weakened |
| D1 | "one vocabulary is defined in one place, and every consumer named in D2/D3 uses it" | `STATE_REFUSED_UNKNOWN` + `_refusal_state()`; nine-member taxonomy in the contract; cause member split out | `STATE_REFUSED_UNKNOWN` at `review_completeness.py:204`; `_refusal_state` at `:425-466` is total and injective; the contract is the single definition site; eight downstream restatements corrected | met |
| D2 | "the signal fires on the two deficit rows, stays silent on the clean row, and reports the two baseline-less rows as unassessable" | `assess_deficit()` + a `deficit` subcommand, `gates_merge: false` | `assess_deficit` at `:614-705`, `check_deficit` at `:928-1009`, `cmd_deficit` at `:1268`, subcommand registered at `:1540`. All four verdict behaviours tested and passing — the clause as written is discharged. **But** no workflow invokes it, and its rendering suppresses the required-reviewer population | clause met; deliverable's purpose unmet |
| D3 | "no surface renders 'nobody reviewed' and 'reviewed clean' as the same string, proven by a test per surface" | Both surfaces done | Surface 1 met and tested (`test_nobody_reviewed_and_reviewed_clean_render_differently`). Surface 2's discriminator (`comparison`, from #1170) works in the library and is tested there, but its input never reaches the step: `finalize-step-review-retrospective/SKILL.md:151-155` records that no persisted reviewed-at-all handoff exists and instructs the step to pass `--reviewed-reviewers` bare, so every zero-findings run grades `indeterminate` and renders one string. The per-row `participation` field renders both facts `unmeasurable` too | surface 1 met; surface 2 unmet in the shipped workflow |
| D4 | "all five behave as specified, each proven to fail before the change" | Two flipped tests observed `2 failed`; new-symbol tests AttributeError pre-fix | All five behaviours are tested and pass, and are discriminating: a naive count-only mutant fails five of the nine deficit tests, cases (b) and (c) among them | met |

### D0 — the counting rule, stated as a reusable contract

`marketplace/bundles/plan-marshall/skills/automatic-review/standards/bot-participation-contract.md:508`
opens § "The counting rule" with "Three named quantities, each with its population published", and the
three bullets deliver exactly what the plan asked: the **finding count** ("the number of filed
`pr-comment` findings attributed to that reviewer's `bot_kind` … never a raw comment count", `:514-521`,
explicitly naming the both-directions failure the plan's ⚠ describes), the **reviewed-at-all predicate**
("a reviewer reviewed the diff iff its taxonomy state is `participated` or `participated_but_empty`",
`:523-528`), and the **required-vs-optional denominator** ("the **required set** … the **optional set** …
and the **enabled roster** (required ∪ optional)", `:530-534`). The rule is genuinely consumed rather than
decorative: `_REVIEWED_STATES` at `review_completeness.py:279` is the predicate, and `check_deficit`
derives each reviewer's filed count from the store at `:984`.

The partition obligation was met differently from how the plan framed it. At the landing, the contract
said (`git show fd292004:…/bot-participation-contract.md:344-351`) "The cause partition is therefore
**derivable from the tree**" and that the cause member is "deliberately **not wired** here". The plan asked
to "partition the absence corpus by CAUSE", noting "Diff sizes are recoverable from merge commits, so this
is cheaply derivable". No corpus was partitioned and no diff size was recovered from any merge commit; what
landed is a statement that the registry data supports the partition. That is a legitimate scoping call
under the plan's own split threshold — and the invariant the partition exists to protect ("do not report a
participation rate over a corpus pooled across causes") is stated at `:402-404` and no rate was reported —
but the literal *Done when* clause was not discharged. The wiring landed later in #1167 (`6ba4dace`), and
today the contract's § "Two axes" (`:365-405`) describes a fully computed partition.

The same shape applies to D2's charter clause. The plan requires that "D0 must establish, per PR in the
corpus, which charter the reviewer was running". The contract states the invariant at `:563-567` ("Which
charter a PR's reviewer was running is part of the population a deficit is reported over"), but a search
for `charter` across `marketplace/`, `.claude/`, and `test/` finds no per-PR attribution anywhere — the
rule exists, the measurement does not. The boundary itself is cheap to date: the charter packs are
generated by `marketplace/targets/pr_agent/target.py`, and `git log -- marketplace/targets/pr_agent/target.py`
returns exactly one commit, `f5493b43` (#1130, "route review charters by repository domain"), so every PR
merged before it ran the pre-charter instructions and every PR after ran the domain-scoped packs. The
attribution is a git query, not an unrecoverable fact.

### D1 — the reviewer-state vocabulary

The pre-fix defect is confirmed literally. `git show fd292004^:…/review_completeness.py` lines 310-311:

```python
awaitable = bot_registry.rate_limit_class(bot) == 'awaitable_window'
return STATE_REFUSED_AWAITABLE if awaitable else STATE_REFUSED_HARD
```

a binary test over a three-valued field, exactly as the plan's OBSERVED claim states.

Today `_refusal_state` (`review_completeness.py:425-466`) is total and injective over the class axis, with
`unknown`/anything-else failing closed to `STATE_REFUSED_UNKNOWN` (`:466`), and
`bot_registry.rate_limit_class` itself fails closed to `'unknown'` for an absent or malformed field
(`bot_registry.py:513-514`), so the new member is reachable for an unregistered bot as well as for
pr-agent. `STATE_REFUSED_UNKNOWN` is in `_UNPROVEN_STATES` (`:258`), so the new member still blocks — the
right call, since a refusal is a refusal.

All three registry documents declare the field, with the values the report states:
`coderabbit.md:56` `rate_limit_class: awaitable_window`, `sourcery.md:49` `hard_quota`,
`pr-agent.md:134` `unknown`. The plan's instruction not to carry forward the older "only one declares it"
wording was honoured.

The drift risk the new member created was chased down. A whole-tree sweep for member-count prose returns
**seven** statements, all reading "ten" and all correct: `bot-participation-contract.md:52`
("classified into exactly one of ten members") and `:73` ("Seven of the ten members"),
`review_completeness.py:189` ("Ten members"), `automated-review-lifecycle.md:56` ("exactly one of ten"),
`create-pr.md:201` ("closed ten-member"), `automatic-review/SKILL.md:24` ("the ten-member failure
taxonomy"), and `pr-review-operations.md:248` ("That taxonomy has **ten** non-participation members").
The derived cardinality agrees: `_NON_PARTICIPATION_MEMBERS` in
`test/plan-marshall/automatic-review/test_bot_participation_contract.py:114-125` is a ten-tuple. A sweep
for `refused_awaitable`/`refused_hard` without `refused_unknown` finds no surviving two-way enumeration.
The count is partly machine-guarded: that file's `:501`,
`test_the_contracts_closure_count_agrees_with_the_derived_member_count`, applies
`_CLOSURE_COUNT = re.compile(r'classified into exactly one of (?P<count>\w+) members')` (`:174`) to the
contract's own § "Failure taxonomy" and compares the word to the tuple's length. That guard's reach is one
sentence in one document — the test says so itself at `:528-529` ("a count restated anywhere else is
outside its reach") — so the other **six** restatements are unguarded prose. A sibling guard at `:525`
does sweep the whole tree, but for `N blocking members` claims, a different and strictly smaller quantity.

### D2 — the deficit signal

The verdict vocabulary and the baseline logic are right on the axis the plan specified.
`assess_deficit` (`review_completeness.py:614-705`) computes `baseline` as the non-required reviewers with
`reviewed` true (`:670-673`), returns `DEFICIT_UNASSESSABLE` when that list is empty (`:681-682`), and
otherwise reports a deficit only when `baseline_max - count >= min_deficit` (`:686-691`), so `0 : 0`
against a real baseline lands in `clean`. The non-gating declaration is machine-readable and rendered
verbatim: `'proves': 'reviewer_quality_only'` and `'gates_merge': False` (`:699-700`), printed by
`_emit_deficit_toon` (`:1137-1138`). The finding count is the filed `pr-comment` count read from the store
(`check_deficit:984`), matching the counting rule.

Two gaps sit against this deliverable.

**Nothing invokes it.** `grep -rn "deficit" marketplace/ .claude/ doc/ -l` (excluding `doc/plans` and
`__pycache__`) returns `tools-script-executor/SKILL.md` (an unrelated use of the word),
`automatic-review/SKILL.md`, `bot-participation-contract.md`, and `review_completeness.py`. In
`automatic-review/SKILL.md` the only occurrences are the § "Canonical invocations" block at `:999-1028` — a
declaration of the argparse surface, not a workflow step, though its prose already speaks as though a step
ran it ("so the step forwards the sets it already gathered", "the step MUST NOT gate the merge on it",
`:1010`, `:1021`). No step in `automatic-review/SKILL.md`, `phase-6-finalize/`, or
`finalize-step-review-retrospective/` runs `review_completeness deficit`. The plan's D2 opens "A required
reviewer returning materially fewer findings … **is reported**"; in the tree as it stands, nothing reports
it, because nothing calls it.

**Its rendering suppresses the populations the plan required it to publish.** Executed, not inferred. For a
baseline reviewer with four findings and a required reviewer that refused, `assess_deficit` returns
`verdict: clean`, and `_emit_deficit_toon` then omits `required_reviewed` entirely because it is empty
(`:1145-1149`, `if required_reviewed:`):

```
status: success
verdict: clean
proves: reviewer_quality_only
gates_merge: false
baseline_max: 4
baseline_reviewers[1]:
  - coderabbit
```

The `unassessable` case is worse: `baseline_reviewers` is empty there too and its guard (`:1140-1144`,
`if baseline:`) drops it as well, so the whole block is five lines with **no population at all**:

```
status: success
verdict: unassessable
proves: reviewer_quality_only
gates_merge: false
baseline_max: 0
```

The plan's Verification section is explicit — "**Publish each population size** the rule computes over, in
the artifact itself. A rate whose denominator is invisible is the defect this plan is about" — and the
emitter publishes a population only when it is non-empty, which is precisely when its absence is the
finding. The `check_deficit` CLI path partially rescues the first case by appending `reviewers[]`
(`:1008`, printed at `:1155-1160`), which does carry `pr-agent,false,0,refused_hard`.

The `clean` verdict itself is defensible on its own terms — a deficit is a statement about *yield* among
reviewers that reviewed, and a required reviewer that did not review is caught by the participation guard
`check` runs from the same observation sets — but the vocabulary has an `unassessable` member for a missing
*baseline* and none for a missing *required* review, and the rendering gives the reader nothing to
distinguish the two situations by. `grep -rn "required_reviewed" test/` returns nothing, so no test pins
this case in either direction.

### D3 — the reviewer-state distribution reaches the field

**Surface 1 — met.** `compose_review_state_summary` (`review_completeness.py:586-611`) tallies
`_STATE_SUMMARY_BUCKETS` (`:294-310`), the field is on the envelope (`:915`), and it is emitted when
non-empty (`_emit_toon:1022-1024`). `automatic-review/SKILL.md:795-806` prescribes interpolating it into
Branch A's `--display-detail`. The discriminating test exists and passes:
`test_review_completeness.py:1880-1895`, `test_nobody_reviewed_and_reviewed_clean_render_differently`,
asserting `nobody == '3 refused'`, `reviewed_clean == '3 empty'`, and `nobody != reviewed_clean`. The test
covers the composer rather than the rendered `display_detail`, because the composition itself is prose in
`SKILL.md` rather than code.

**Surface 2 — met in the library, unreachable in the shipped workflow.** `review_retrospective.py:331`
is the whole per-row classifier:

```python
participation = 'measured' if raw_total > 0 else 'unmeasurable'
```

A reviewer that reviewed and found nothing files no records, so `raw_total == 0` and its row renders
`unmeasurable` — the identical value a reviewer that never ran renders. The landing's own test says so in
as many words (`test_review_retrospective.py:697`,
`test_enabled_reviewer_with_no_findings_gets_an_unmeasurable_row`):

> "produced nothing", "never ran", and "enabled-invoked-refused" all leave no record; without a row they
> render identically. The row names the reviewer and marks it unmeasurable — never scored — rather than
> omitting it.

At the landing that was the whole of surface 2. #1170 (`b286928c`, confirmed by
`git log -S'_grade_comparison'`) added `_grade_comparison` (`review_retrospective.py:108-153`) and the
`comparison` field, which on a zero-findings run separates `clean` (an enabled reviewer is substantiated
as having reviewed) from `indeterminate` (none is), and
`finalize-step-review-retrospective/SKILL.md:190-192` maps the grade to distinct `--display-detail`
values. The proving test exists and is explicitly a discrimination proof —
`test_review_retrospective.py:835`, `test_comparison_clean_vs_indeterminate_discriminate_on_identical_zero_store`,
which holds the roster and the empty store fixed, asserts every row is `unmeasurable` in both runs, and
then asserts `reviewed_clean['comparison'] != nobody_reviewed['comparison']`.

**But the discriminating input never reaches the step, and the skill says so in as many words.** That
test supplies `reviewed_reviewers=['cuioss-review-bot']` directly to `aggregate()`. The workflow cannot.
`finalize-step-review-retrospective/SKILL.md:151-155` states: "⚠ **No persisted handoff of that
classification currently reaches this step.** `review_completeness check` emits `bot_states` in its
immediate TOON during the automatic-review step and the merge-gate barrier, but nothing persists it in a
form this step can read at `order: 990` (after the merge gate). So **pass `--reviewed-reviewers` bare**
here, and the zero-findings grade **fails closed to `indeterminate`**" — repeated at `:225-230` for the
ordinary Step 2 call. A whole-tree sweep for `bot_states` (§ Method) finds no writer: every hit reads the
classifier's immediate TOON in-process. So on every zero-findings run the enabled roster is non-empty,
`reviewed_reviewers` is empty, `_grade_comparison` returns `COMPARISON_INDETERMINATE` at
`review_retrospective.py:153`, and the step renders the one `indeterminate` string — whether a reviewer
reviewed and found nothing or nobody reviewed at all. That is the plan's D3 *Done when* ("no **surface**
renders 'nobody reviewed' and 'reviewed clean' as the same string") undischarged on the second surface,
not a refinement of one that discriminates. The `clean` branch is fail-closed rather than wrong — an
unsubstantiated review is correctly never credited — but the consequence is that the two facts share a
rendering, which is exactly the defect this plan is named after.

The per-row field is the smaller half of the same root cause: `:331` ignores `reviewed_reviewers` even
though that set is a parameter of the same `aggregate()` call (`:217`), so even once the handoff exists a
reader scanning the per-reviewer table alone — rather than the grade above it — still cannot tell a
reviewer that reviewed and found nothing from one that never ran.

### D4 — tests, each verified to fail pre-fix

Every behaviour the plan enumerates has a test, and all 184 tests in the two files pass.

- (a) two deficit rows: `test_row_a_deficit_four_to_zero`, `test_row_b_deficit_two_to_zero`.
- (b) `0 : 0` with a real baseline stays clean: `test_row_e_clean_zero_to_zero_with_a_real_baseline`,
  asserting `DEFICIT_CLEAN` and `deficit_reviewers == []`.
- (c) baseline-less rows: `test_rows_c_and_d_unassessable_when_every_baseline_refused`, asserting
  `DEFICIT_UNASSESSABLE`, `!= DEFICIT_CLEAN`, and `baseline_reviewers == []`.
- The named blind-spot test exists: `test_required_count_alone_cannot_distinguish_the_rows`, holding
  `required_count == 0` fixed and varying only the baseline across all three verdicts.
- The 150,000 figure is pinned to no threshold, constant, or detection pattern; `sourcery.md:43` keeps the
  detection pattern number-free ("your pull request is larger than the review limit of") and reads the
  figure through `refusal_size_cap_patterns` (`:47-48`) instead, exactly as the plan's ⛔ demanded. A
  whole-tree `grep -rn "150000\|150,000"` returns it only inside test fixtures that author their own
  notice body and assert the extractor reads back what that body states
  (`test_github_pr.py:2599`, `:2671`, `:2845`), plus two illustrative comments
  (`sourcery.md:48`, `_github_pr.py:301`) — never as a production figure the code depends on.

The report's own *stated* proof for the new tests — "New/changed functions did not exist pre-fix, so their
tests AttributeError against pre-fix code" — is true of any new symbol and carries no discriminating
information. The plan's Verification section asked for something stronger: "confirm that a naive detector
*does* fire on them today, so the test is discriminating rather than decorative". That check was not
performed by the run; it has now been performed here, and it passes. With `assess_deficit`'s verdict block
replaced by the naive count-only rule (deficit iff a required reviewer filed zero findings, baseline
ignored), `pytest -k TestDeficitSignal` reports **5 failed, 4 passed**, and the failures include both
load-bearing negative cases: the mutant renders row E as `deficit` where the test demands `clean`, and rows
C/D as `deficit` where the test demands `unassessable`. The tests are discriminating; only the report's
account of *why* they are was weak.

## Report-claim audit

**Claim re-derivation table**

| Report claim | Verdict | Evidence |
|---|---|---|
| `display_detail` rendered nobody-reviewed identically to reviewed-clean | ACCURATE | `git show fd292004^:…/automatic-review/SKILL.md` Branch A composed the count-only string; the plan's own quotation matches |
| "…with the default-empty `required_bots`, `participation_complete` is vacuously true, so Branch A fires" | OVERSTATED | This repository configures `required_bots: pr-agent` and `optional_bots: coderabbit,sourcery` (`.plan/marshal.json:117-118`), so the vacuous-quorum path is not how the observed run reached Branch A. The *defect* claim is right; this particular mechanism for it is not the one in force here |
| The refusal taxonomy exists but never reaches `display_detail` | ACCURATE | Pre-fix envelope carried `bot_states` but no summary field; `review_state_summary` is new at `:915` |
| `review_completeness.py:310`: `awaitable = rate_limit_class(bot) == 'awaitable_window'` | ACCURATE | Verified verbatim at that exact line in `fd292004^`; the binary return is the line below it |
| All three registry docs declare `rate_limit_class`; coderabbit=`awaitable_window`, sourcery=`hard_quota`, pr-agent=`unknown` | ACCURATE | `coderabbit.md:56`, `sourcery.md:49`, `pr-agent.md:134` |
| The refusal pre-filter enumerates known shapes rather than positively validating | ACCURATE (and still true) | `_github_pr.py:155-187`, `_is_refusal_notice`: registry `refusal_patterns` OR the structural `_is_rate_limit_notice` (`:185-187`); no positive test of what review feedback must contain |
| "see 'Out of this plan (split)'" (the cross-reference attached to that row) | FALSE | No section by that name exists in `report-01.md`. Its eleven sections are: Skills loaded, Claim re-derivation, Scoping decision, Deliverables, Build gate, Findings, Reviewer participation, Cost, Contract check, What have we learned, Residue. § "Scoping decision" discusses only the cause member, not the pre-filter |
| `review_retrospective.aggregate()` built `reviewers[]` purely from finding records | ACCURATE | `git show fd292004^:…/review_retrospective.py:201`, `for author in sorted(per_reviewer)` |
| The 150,000 threshold is not re-derivable; Sourcery's size pattern is number-free | ACCURATE | `sourcery.md:43` is number-free; the figure is read via `refusal_size_cap_patterns` at `:47-48` |
| The partition is derivable because Sourcery declares a size notice and a quota notice as distinct `refusal_patterns` | ACCURATE | `sourcery.md:42-44` declares exactly those two entries; `refusal_size_patterns` at `:45-46` carries only the size one |

**Deliverable and process claims**

| Report claim | Verdict | Evidence |
|---|---|---|
| Commits `058d761`, `11df4da`, `3ab4e76`, `9f37480`, `607fa10`, `1bb595e`, head `7ecd755` | UNVERIFIABLE | `git cat-file -t` reports "Not a valid object name" for all seven — expected after a squash merge with the branch deleted. Not evidence against the report, but the per-commit attribution cannot be checked |
| `STATE_REFUSED_UNKNOWN` + `_refusal_state()` added, one-to-one over three classes, added to `_UNPROVEN_STATES` | ACCURATE | `:204`, `:425-466`, `:258` |
| `assess_deficit()` + a `deficit` subcommand carrying `gates_merge: false` / `proves: reviewer_quality_only` | ACCURATE | `:614`, `:1268`, `:1540`, `:699-700` |
| "Fires only against a real baseline; `unassessable` when every other reviewer refused; never on `0 : 0`" | ACCURATE | `:681-691`, plus the four passing tests and the mutation probe |
| `compose_review_state_summary()` + `review_state_summary` field; Branch A interpolates it | ACCURATE | `:586`, `:915`, `automatic-review/SKILL.md:797`, `:805` |
| Surface 2 "emits a row per **enabled** reviewer (roster ∪ observed), each carrying `participation: measured \| unmeasurable`, closing the vacuous-set (no-row) defect" | ACCURATE | The row emission is at `review_retrospective.py:317`, and the no-row collapse is what the claim names as closed. It does not claim the per-row field separates reviewed-clean from never-ran, and it does not: `:331` renders both `unmeasurable`, as the accompanying test asserts |
| Surface 2 closes D3's *Done when* (the report's "D3 … (both surfaces)" heading) | OVERSTATED | The no-row collapse is closed. The *string* collapse D3 names is not: at the landing surface 2 had no discriminating rendering at all, and the `comparison` grade that supplies one (#1170) is fed by an input `finalize-step-review-retrospective/SKILL.md:151-155` records as unavailable to the step (§ D3) |
| "eight documentation-drift instances … all were **fixed** (commit `607fa10`), then confirmed clean by full-tree greps" | ACCURATE | All eight named sites carry the corrected text today, at drifted line numbers: `review_completeness.py:189` ("Ten members"), `automated-review-lifecycle.md:56` ("exactly one of ten"), `pr-review-operations.md:248` ("**ten** non-participation members") and `:258` (three-way refused row), `workflow-integration-github/SKILL.md:137`, `github_pr.py:812` and `:1034-1035`, `_github_pr.py:178`, `test_github_pr.py:1009`. My independent whole-tree sweeps for stale member counts and two-way refusal enumerations return clean |
| "`test_required_count_alone_cannot_distinguish_the_rows` pins that `required_count == 0` is identical across all five rows" | ACCURATE | The test exists at `:1999`, passes, and varies only the baseline |
| "New/changed functions did not exist pre-fix, so their tests AttributeError against pre-fix code" (as the D4 fail-pre-fix proof) | ACCURATE BUT NON-DISCRIMINATING | True of any new symbol, so it is not the pre-fix evidence the plan's Verification section demanded. The tests themselves are nonetheless discriminating — the naive-detector mutant fails five of nine (§ D4) |
| "`./pw verify` … 18979 passed, 14 skipped" | UNVERIFIABLE | Not re-run (the instructions forbid a full build). The two touched test files pass: 184 passed |
| Reviewer-participation table for PR #1165 (`cuioss-review-bot` reviewed, `coderabbitai` and `sourcery-ai` rate-limited) | UNVERIFIABLE | A property of the PR's comment surface, not of the tree |
| § Residue "Landing delegated" | CLOSED | Landed as `fd292004` |
| § Residue "Split-out: the wired quota-vs-diff-size cause member" | CLOSED | `6ba4dace` (#1167) wired the cause axis; the tree now carries `CAUSE_SIZE` (`:271`), `STATE_REFUSED_STRUCTURAL` (`:225`), `parse_causes` (`:382`), `recover_causes_from_caps` (`:469`), and a `size-caps` subcommand (`:1542`) |
| § Residue "Contract-change proposal pending: manual `pull_request_read` polling as the in-session fallback" | CLOSED | `d8039616` (#1166); `cloud-plan-lane/SKILL.md:1528` now carries § "Manual read-polling is the in-session alternative to arm-and-hand-off" |
| § Residue "CodeRabbit's window reopens in ~5 min. Not awaited." | MOOT | A statement about the run, not a tree obligation |

The one FALSE claim is the dangling `see "Out of this plan (split)"` cross-reference, and its consequence is
substantive rather than cosmetic: the pre-filter remedy it pointed at never reached § Residue, so nothing
carries it forward (see Completeness review).

## Correctness review

**C1 — the deficit envelope publishes a population only when it is non-empty, and has no verdict for a
missing required review.** `review_completeness.py:691`,
`verdict = DEFICIT_DEFICIT if deficit_reviewers else DEFICIT_CLEAN`. `deficit_reviewers` is built only over
`required_reviewed` (`:675-678`, filtered on `r.get('reviewed')`; the loop is `:684-690`), so a required
reviewer that refused, was absent, or was never triggered contributes nothing and the else-branch fires.
The verdict vocabulary (`:283-285`) has an `unassessable` member for a missing *baseline* but none for a
missing *required* review. Rendering compounds it: `_emit_deficit_toon` guards both population lines on
non-emptiness (`:1140-1144`, `:1145-1149`), so the `clean`-with-no-required-review block shows no required
row at all and the `unassessable` block shows no population whatsoever — against the plan's Verification
demand to publish each population in the artifact itself. Confirmed by execution for all three payload
shapes. The suppression is deliberate rather than accidental: the module docstring's deficit TOON shape
annotates both population lines "emitted only when non-empty" (`:175-176`), so the fix has to change the
documented shape as well as the emitter. The contract's wording — "**clean** — a baseline exists and no required reviewer under-produced"
(`bot-participation-contract.md:556-557`) — is technically true and reads as an all-clear. **CONFIRMED.**

**C2 — the prescribed `display_detail` exceeds the repository's 80-character bound, and uses a non-ASCII
glyph.** `phase-6-finalize/standards/output-template.md:340` and `:343` state the rules: "**Max 80
characters** (…the renderer does not truncate)" and "**Plain ASCII** — no unicode glyphs";
`external-step-contract.md:55` repeats "Plain ASCII — no unicode glyphs"; `branch-cleanup.md:1707` states
the length must be checked "against its placeholders' **worst-case expansion**, never its literal form".
The composition this plan introduced uses an em dash (U+2014) at `automatic-review/SKILL.md:797`, `:800`,
`:805`, `:850`, and its expansion over this repository's own three-bot roster measures 86 characters:
`0 comment(s) found — 1 empty, 1 refused, 1 refused-structural (unified triage pending)` — a wholly
ordinary outcome (pr-agent reviews clean, coderabbit rate-limits, sourcery size-refuses). The worst
three-bucket expansion, over the three longest bucket labels
(`refused-structural`, `not-triggered`, `in-progress`), measures 98 — and the template has no bounded
worst case at all, because `compose_review_state_summary` emits one segment per non-zero bucket
(`:606-610`): a roster with one reviewer in each of the nine buckets renders 161 characters.
`branch-cleanup.md:1707` requires the length be checked "against its placeholders' **worst-case
expansion**", so shortening bucket labels cannot discharge it — the rendering itself has to be bounded.
`automatic-review/SKILL.md:856`
restates the ≤80/ASCII rule in the very section whose template breaks it. **CONFIRMED** (measured with
`len()` and `isascii()`).

Two qualifications bound this. The ASCII half is not a defect this plan invented: `architecture-refresh.md`
prescribes em-dash `display_detail` strings at `:124`, `:196`, and `:412` while restating the plain-ASCII
rule at `:460`, so the house pattern already diverges from the house rule. The length half *is* specific to
this composition — those other templates are all comfortably under the bound — and the rule is genuinely
enforced elsewhere: `test/plan-marshall/phase-6-finalize/test_pre_submission_self_review_verdict.py:219`,
`test_every_verdict_fits_the_display_detail_budget`, parses another step's SKILL.md verdict literals,
widens every placeholder to its plausible maximum, and asserts `len <= 80`, `isascii()`, and no trailing
period. That is both the precedent and the ready-made shape of the fix.

**C3 — the empty-roster fallback reproduces the defect verbatim.** `compose_review_state_summary` returns
`''` for an empty `bot_states` (`:602-611`; the rationale is in the docstring at `:597-600`), and
`automatic-review/SKILL.md:798` then falls back to `"{N} comment(s) found (unified triage pending)"` —
character-for-character the string the plan's Problem section quotes as the defect.
`automatic-review/SKILL.md:648` states that `required_bots` and `optional_bots` "both default EMPTY", so in
an unconfigured project the fix is inert and the collapsed string returns. The docstring argues the empty
string is the honest value for a roster that was never configured, which is a fair argument about the
*summary*; it does not extend to the *display string*, which still reads to a cold reader as "a review
happened and found nothing". **CONFIRMED.**

**C4 — no guard ties the display buckets to the taxonomy.** `_STATE_SUMMARY_BUCKETS` (`:294-310`) is an
explicit enumeration, and `compose_review_state_summary` sums only the states named in it (`:607-610`); a
state with no bucket is counted into `counts` (`:602-605`) and then silently dropped. Confirmed by
execution: a two-bot roster carrying one unbucketed state renders `'1 refused'`, tallying to one for a
population of two. `grep -rn "_STATE_SUMMARY_BUCKETS" test/ marketplace/ .claude/` finds no test
referencing the constant, so nothing fails when a member is added without a bucket — the tally would simply
stop summing to the roster size, under-reporting exactly the way this plan exists to prevent. The union is
correct today (11 bucketed states, 11 taxonomy members, verified by set comparison), but the taxonomy
gained `refused_structural` in #1167 and the bucket list was updated by hand — the hazard is live and was
survived by attention, not by a guard. **CONFIRMED.**

**C5 — an illustrative example describes a state its own branch cannot normally reach.**
`automatic-review/SKILL.md:800` says, verbatim, "So a run where three required reviewers all refused
renders `"0 comment(s) found — 3 refused (unified triage pending)"`". But every refusal member is in
`_UNPROVEN_STATES` (`:252-264`), `participation_complete = not required_unproven`
(`review_completeness.py:865`), and Branch A is "entered only after the participation guard above returns
`participation_complete: true`, or a force-done WARNING was recorded" (`SKILL.md:789`). Three refusing
*required* reviewers therefore route to Branch C (loop-back), not Branch A. The scenario is reachable only
through the force-done hatch; the ordinary case for this string is refusing *optional* reviewers.
**CONFIRMED.**

**C6 — `min_deficit` defaults to 1, so a one-finding gap is reported as a deficit.** `:617`, and the
docstring at `:640-643` calls that "a required reviewer that reviewed yet produced strictly fewer findings
than a baseline". The plan's D2 says "**materially** fewer findings", and the contract repeats "materially"
at `:538` and `:555` without ever naming the threshold — a search for `min_deficit` across the contract
returns nothing, so the only restatement of the default is `automatic-review/SKILL.md:1011`. A 1-vs-2 split
between two reviewers on the same diff is ordinary variance, not a reviewer-quality bug.
`test_min_deficit_threshold_is_honoured` pins the threshold as configurable, so the mechanism is there;
only the default and the gap between "materially" and "strictly fewer" are arguable. **CONFIRMED** as a
design choice worth revisiting, not as a defect.

**C7 — surface 2's discriminator has no input in the shipped workflow.** Established in § D3 above and
recorded here because it is the sharpest correctness finding in the review: the `comparison` grade can
reach `clean` only when the caller supplies `reviewed_reviewers`, and the step's own SKILL.md
(`:151-155`, again at `:225-230`) records that no persisted reviewed-at-all handoff reaches it and
instructs it to pass the flag bare. The whole-tree `bot_states` sweep confirms no writer exists. Both
zero-findings cases therefore render the `indeterminate` string. Fail-closed and honest, but the two facts
share a rendering — D3's *Done when*, unmet on the second surface. **CONFIRMED.**

**C8 — the review-retrospective's own `display_detail` strings break the ≤80/ASCII contract, and one
breaks it unconditionally.** `finalize-step-review-retrospective/SKILL.md:190-192` prescribes three grade
strings; measured with `len()` and `isascii()` they are 73 / 50 / **109** characters and all three carry
an em dash. The `indeterminate` string — `indeterminate — 0 findings and no reviewer produced content;
review-quality comparison could not be performed` — has no placeholder, so its 109 characters are not a
worst case but the only case, and it is the string this deliverable's second surface emits on exactly the
run the plan is about. The governing contract is the one the same skill cites at `:447-448` as its reason
for keeping the Step 3b delta verdict *out* of `display_detail`:
`phase-6-finalize/standards/external-step-contract.md` § "Required termination", whose constraint list
gives "≤80 characters" (`:52`) and "Plain ASCII — no unicode glyphs" (`:55`). The skill therefore invokes
the ceiling as binding in one section and overruns it by 29 characters in another. **CONFIRMED.**

**C9 — `review_completeness.py`'s own `Usage:` line omits the flag its documentation guard calls
load-bearing.** The module docstring gives two invocation lines: `check` at `:115` carries
`[--refusal-size-caps [<csv>]]`; `deficit` at `:116` does not, though `_add_bot_observation_flags`
(`:1298`) registers the flag on both subparsers (`:1434`) and `automatic-review/SKILL.md:1010-1018` marks
it ⛔ "the load-bearing one: a cap arriving WITHOUT its cause drives the fail-closed cause recovery, so a
caller that passes it to `check` but not `deficit` reproduces exactly the disagreement the pair exists to
prevent". A caller following the module's own Usage line does precisely that. The SKILL.md invocation
block is machine-guarded against this omission —
`test/plan-marshall/automatic-review/test_structural_refusal.py:799`,
`test_the_deficit_invocation_block_documents_the_cap_flag`, whose docstring notes that "plugin-doctor
cannot catch it, because it validates documented invocations against the parser, not the parser against
the docs" — but the guard reads `SKILL.md` only, and the module docstring is the second documented
invocation surface. **CONFIRMED.**

No fail-open exception path, off-by-one, non-idempotence, or unguarded `None` was found in the changed
code. `check_deficit`'s store read is fail-closed (`:960-967`, an `OSError`/`ValueError` returns the
`load_failure` error branch rather than an empty-and-clean result), matching the plan's Notes rule "Branch
on producer STATUS before folding its payload". `recover_causes_from_caps` (`:469-503`, from the later
#1167) uses `setdefault` so an observed cause is never overridden, and is applied identically by `check`
and `deficit` (`:980`), which is the right shape. The argparse `help=` prose on both scripts
(`review_completeness.py:1298-1554`, `review_retrospective.py:426-465`) describes the current behaviour and
claims nothing the code does not do — notably `--enabled-reviewers` says only that the no-row collapse is
closed, and `--reviewed-reviewers` correctly attributes the clean-vs-indeterminate separation to the
`comparison` grade rather than to the per-row field.

## Completeness review

**Consumers swept, and found clean.** Every restatement of the taxonomy member count, of the refusal
split, and of the `display_detail` template was checked across `marketplace/`, `test/`, `.claude/`, and
`doc/developer/` — prose, docstrings, comments, and test docstrings alike. Six member-count statements, all
"ten"; no two-way refusal enumeration survives; nine occurrences of `comment(s) found` and five of `unified
triage pending`, all in the changed sites or their tests. The eight drift sites the report names all carry
corrected text. This part of the work is genuinely complete and better than most.

**Missing: the deficit signal has no caller.** Established by `grep -rn "deficit" marketplace/ .claude/
doc/ -l` and `grep -rn "check_deficit\|assess_deficit\|cmd_deficit" --include=*.py`.
`bot-participation-contract.md:662` lists `review_completeness deficit` in the § "Consumers" table — which
describes what the command reads, not who runs it. No finalize step, no workflow document, no retrospective
step invokes it.

**Missing: the populations are published conditionally.** `_emit_deficit_toon` prints
`baseline_reviewers` and `required_reviewed` only when non-empty (C1), so the two cases where an empty
population is the finding are the two cases where it is invisible.

**Missing: no test for the required-did-not-review case.** `grep -rn "required_reviewed" test/` returns
nothing. Of the nine tests in `TestDeficitSignal`, none constructs a required reviewer with
`reviewed: False` alongside a *reviewing* baseline;
`test_rows_c_and_d_unassessable_when_every_baseline_refused` sets `reviewed=False` on the required
reviewer but also on both baselines, so the `not baseline` branch short-circuits at
`review_completeness.py:681` before the gap can be observed.

**Missing: the reviewed-at-all handoff surface 2 needs** (C7 above). The classification exists, the
consumer flag exists, the grading logic exists and is tested — and nothing writes the classification where
the consumer can read it, so the flag is documented as always-bare and the grade is pinned to
`indeterminate` on every zero-findings run.

**Missing: no test for the row-level half of surface 2.** The surface has a discrimination test at the
aggregate grade (`test_review_retrospective.py:835`), and that test supplies `reviewed_reviewers`
directly. No test asserts that a reviewed-clean *row* differs from a never-ran *row* — because it does not;
the existing tests assert the opposite deliberately. Nor does any test pin the *step's* rendering, which is
where the collapse survives.

**Missing: no bucket-coverage guard** (C4 above).

**Missing: the member-count guard reaches one sentence.**
`test_bot_participation_contract.py:501` checks the contract's own closure sentence, and a separate sweep
(`:525`) checks every "N blocking members" claim across the marketplace docs — but no check reads the
**six** other *taxonomy*-count restatements. Those six are exactly the class of site the run's own
sub-agent had to correct by hand when the taxonomy went from eight members to nine. The same shape now
exists one level down for this plan's own additions: the three-member deficit verdict vocabulary is
restated at five sites — `review_completeness.py:171` (the docstring's TOON shape), `:283-285` (the
constants), `:646-647` (`assess_deficit`'s Returns), `bot-participation-contract.md:554-559`, and
`automatic-review/SKILL.md:1021-1024` — with no guard reading any of them, so adding the verdict C1 calls
for would repeat the eight-to-nine drift by hand.

**Missing: a guard over the module docstring's invocation lines** (C9 above). The equivalent guard for the
SKILL.md block exists and names its own reach; nothing extends it to the `Usage:` lines in the script.

**Missing: the deferred pre-filter remedy left no trace.** The plan's Notes carry "Candidate remedy for the
pre-filter, not yet applied: restate it **positively** — a stored `pr-comment` finding must positively look
like review feedback", and the plan's § Expected surface names `github_pr.py`'s `fetch_findings` refusal
pre-filter. The report deferred it with a cross-reference to a section that does not exist and did not add
it to § Residue. `_github_pr.py:155-187` still enumerates (registry patterns, else the structural
recognizer), so the defect is live and unrecorded.

**Missing: the owed architecture insight was not recorded.** The plan's Notes state an insight this plan
"should record": *a review bot's persistent summary card and its trigger acknowledgement are participation
artifacts, not diff-derived claims — dispose of them as accepted without opening a fix task, and never read
their presence as evidence the bot reviewed the current HEAD*. The nearest existing prose is
`bot-participation-contract.md:307`, § "Obligation 3 — only diff-derived evidence discharges a review
obligation", which covers *body-derived* signals and not bot-produced participation artifacts; the searches
above find nothing naming a summary card or a trigger acknowledgement. The mechanical half of the insight
pre-exists — the currency rule (`bot-participation-contract.md:207`) and the decline detector (`:249`) both
key on the reviewed-commit SHA, and the `contentless_review_markers` conditional drop (`:459`) keeps a
clean card from consuming a triage decision — but the disposition guidance itself was never written down,
and the report does not claim it was.

**Missing: no corpus was measured, for either axis the plan named.** Neither the absence corpus's
cause partition (D0) nor the per-PR charter attribution (D2's instruction-boundary clause) exists as data
anywhere in the tree; both landed as invariants instead. The contract's own rule forbids reporting a
participation rate until the first exists, so the gap is self-limiting rather than dangerous — and the
second is a one-commit git query away (§ D0).

## Out-of-scope compliance

Clean on all five exclusions.

- **Judging whether a reviewer's prose is "substantive".** Nothing added scores prose.
  `compose_review_state_summary` counts states; `assess_deficit` counts filed findings.
- **Reassigning which reviewer is `required` based on measured yield.** No code path writes
  `required_bots`, and `assess_deficit` returns `gates_merge: False` (`:700`) with no consumer able to move
  a verdict — there is no consumer at all.
- **Scoring finding correctness.** `positives_count` / `false_positives_count` in the retrospective are
  pre-existing fields, untouched by `fd292004` except for the row-population change.
- **Splitting large PRs to stay under a reviewer's size limit.** Not attempted; the split-out cause member
  was deferred and later landed as classification, not as PR-splitting.
- **Re-opening the which-kind-of-zero discriminator shipped elsewhere.** The landing reuses the shape
  (published populations, named zeros) rather than rebuilding it; the idiom's existing homes
  (`manage-lessons`, `plan-orchestrator`, `plan-retrospective`) are untouched.

The landing also stayed inside the plan's § Expected surface, with one addition the plan implicitly
sanctions: `phase-6-finalize/workflow/create-pr.md` was touched for a member-count restatement, which is
drift-following rather than scope creep.

## Residue status

| Report residue item | Status | Closed by |
|---|---|---|
| Landing delegated to the merge queue; squash SHA not yet known | CLOSED | `fd292004` |
| Split-out: the *wired* quota-vs-diff-size refusal cause member | CLOSED | `6ba4dace` (#1167), with follow-ups `064560ab` (#1168) and `9e9e9880` (#1241). The tree carries `CAUSE_SIZE`, `STATE_REFUSED_STRUCTURAL`, `parse_causes`, `recover_causes_from_caps`, and the `size-caps` subcommand |
| Contract-change proposal: manual `pull_request_read` polling as the in-session fallback | CLOSED | `d8039616` (#1166); `cloud-plan-lane/SKILL.md:1528` |
| CodeRabbit's window reopens in ~5 min; not awaited | MOOT | A statement about the run |

**Residue the report should have recorded and did not:** the positive-restatement remedy for the refusal
pre-filter (still open, `_github_pr.py:155-187`), and the owed architecture insight about participation
artifacts (still unrecorded). Both are carried into `gaps.md`.

## Summary

Counts by severity: **0 blockers, 3 major, 13 minor** (16 gaps, listed in `gaps.md`).

The plan's hard mechanism landed and is correct where it landed: the three-valued `rate_limit_class` no
longer folds `unknown` into a positive hard-quota finding, the counting rule is written once with all three
populations published and is genuinely consumed by the code, and the eight documentation-drift instances
the new taxonomy member created were chased down and are still correct in the tree — a whole-tree sweep for
stale member counts and two-way refusal enumerations comes back clean. Every behaviour the plan's D4
enumerates has a test, and those tests discriminate: the naive count-only detector the plan warns about
fails five of the nine, both load-bearing negative cases among them.

What did not land is the *reaching a reader* half of the plan, which is the half the plan's title is about,
and it failed in three separate places.

On the second D3 surface the collapse is still live. The `comparison` grade added by #1170 does separate
*reviewed-clean* from *never-ran*, and an explicit discrimination test proves it — but the test hands
`aggregate()` the reviewed-at-all set directly, and the step cannot. Its own SKILL.md records that nothing
persists that classification anywhere a step at `order: 990` can read it, and instructs the step to pass
`--reviewed-reviewers` bare; a whole-tree sweep for a writer of `bot_states` confirms there is none. So
every zero-findings run grades `indeterminate` and emits one string, whichever fact produced it. The
per-row `participation` field renders both `unmeasurable` for the same reason.

The deficit signal has no caller anywhere in the tree, so nothing reports it; and when it is called, its
rendering publishes a population only when that population is non-empty — printing `verdict: clean` with no
row at all for a required reviewer that did not review, and printing no population line whatsoever on
`unassessable`. That is the plan's own "publish each population" requirement inverted at exactly the two
inputs where the empty population is the finding, and the module docstring documents the suppression
(`:175-176`, "emitted only when non-empty") rather than treating it as an oversight.

Both surfaces also overrun the repository's `display_detail` contract. The Branch A template exceeds
80 characters at an ordinary three-bucket expansion (86) and has no bounded worst case at all (161 over
the full bucket vocabulary); the retrospective's `indeterminate` string is a fixed 109-character literal.
Both carry a non-ASCII em dash — which, on the Branch A side, matches a pre-existing house pattern rather
than originating here.

## Adversarial review

This document and `gaps.md` were re-derived independently against the working tree rather than read for
plausibility, and then re-derived a second time by a further reviewer that checked the first rather than
trusting it. The method, precisely enough to re-run:

- **Every `path:line` citation in both documents resolves to the text quoted beside it**, machine-checked
  by reading each cited line and asserting the quoted fragment appears in it — 76 citations across
  `review_completeness.py`, `review_retrospective.py`, `bot_registry.py`, `_github_pr.py`, the contract,
  the three SKILL.md files, the three registry docs, the `phase-6-finalize` standards, and five test
  files. Drift of one to four lines was
  the common failure and every instance is now pinned to the current tree; two citations were not drift but
  error, and neither survives: the contract's `clean` definition sits at `:556-557`, and the contract
  carries no restatement of `min_deficit` at all (`grep -rn "min_deficit\|min-deficit"` over it returns
  nothing), so no document claims one. Quotation fidelity was checked in the same pass — a quoted sentence
  must match the source character for character, emphasis markers included.
- **Every count in both documents was re-derived.** 184 passing tests, nine tests in `TestDeficitSignal`,
  nine occurrences of `comment(s) found`, five of `unified triage pending`, fifteen `refused_awaitable`
  mentions, eight corrected drift sites, four `deficit`-mentioning source files, eleven display buckets over
  eleven taxonomy members, three registry `rate_limit_class` declarations — all upheld by re-running the
  searches. Two required a wider net than the obvious one. The taxonomy-count sweep needs a second pattern
  to reach **seven** statements: a `(word)[ -]member` regex alone misses `pr-review-operations.md:248`
  ("That taxonomy has **ten** non-participation members"), a site the report-claim audit below cites, so
  the guard's reach is one statement of seven and the unguarded remainder is **six**. And the 98-character
  `display_detail` figure is a three-*bucket* worst case, not the template's worst case: the rendering is
  unbounded, reaching 161 over the full nine-bucket vocabulary, which is what makes relabelling an
  insufficient remedy.
- **Executable claims were executed, twice and independently.** `assess_deficit` and `_emit_deficit_toon`
  over the `clean`, `unassessable`, and `0 : 0` payloads; `compose_review_state_summary` with an unbucketed
  state and with an empty roster; `_refusal_state` over all three declared classes plus a malformed and an
  empty one; the bucket union against the member set; `min_deficit` at its default against a 1-vs-2 split.
  Every result reproduced. The `unassessable` rendering carrying **no** population line at all is the
  sharpest instance of the emitter defect and is folded into the deficit gap rather than split out.
- **The claim about test quality was settled by mutation, and the mutant was reproduced exactly.**
  `review_completeness.py` was snapshotted byte-for-byte to a scratch directory, `assess_deficit`'s verdict
  block replaced by the naive count-only detector, the deficit tests re-run, and the file restored from the
  snapshot in a `finally` (never via `git checkout`/`restore`/`stash`; `git status --porcelain` confirmed
  clean afterwards). The result is **5 failed, 4 passed** with the identical failure list, so the earlier
  figure stands; a stricter naive mutant that also flattens the reported gap fails 7 of 9.

Dispositions, as they now stand.

**Upheld against the tree:** C1 in full (executed), C2 as qualified, C3, C4, C5, C6, the no-caller finding,
the missing required-reviewer test, the unrecorded pre-filter remedy, the unrecorded architecture insight,
the dangling report cross-reference, the never-measured corpus partition and charter attribution, the
mutation result, and every entry in the report-claim audit.

**Corrected upward — the sharpest finding here.** The surface-2 collapse is a live major defect, not a
row-level refinement. `_grade_comparison` and its discrimination test establish only that the *library*
discriminates; the step's own SKILL.md (`:151-156`, `:225-230`) records that the discriminating input
reaches no consumer and instructs the step to pass the flag bare, and a whole-tree sweep finds no writer of
`bot_states`. The plan's title collapse therefore survives on the plan's second surface — C7, and the first
gap.

**Corrected downward.** The 150,000 figure is pinned to no production constant, threshold, or detection
pattern — the accurate claim — but it does appear in test fixtures that author their own notice body and
assert round-trip extraction, so "not pinned anywhere" overstated it.

**Refuted:** nothing. Two earlier candidate findings are correctly recorded as refuted rather than as gaps —
that the D4 tests rest on vacuous evidence (the mutation probe disproves it for the tests, while the
report's *stated* proof remains correctly described as non-discriminating), and that no test proves surface
2's discriminator works (`test_review_retrospective.py:835` proves it for the library, which is the narrower
claim that test makes).

**Unverifiable, and not counted against the report:** the seven pre-squash commit SHAs — `git cat-file -t`
reports "Not a valid object name" for each, expected after a squash merge with the branch deleted, while
the seven landing and follow-up SHAs all resolve — the `./pw verify` totals, and PR #1165's comment
surface.

`gaps.md` holds **three major and thirteen minor** entries, numbered contiguously G1–G16 and ordered by
severity, and every count stated in either document matches the tree as it stands.
