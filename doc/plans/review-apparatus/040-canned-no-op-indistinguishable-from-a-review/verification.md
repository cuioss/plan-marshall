# Verification — 040-canned-no-op-indistinguishable-from-a-review

**Landed as:** PR #1165, squash commit `fd292004`
**Verdict:** verified-with-gaps

The plan's central mechanism landed and is real: the three-valued `rate_limit_class` no longer collapses,
a state distribution reaches `display_detail`, a deficit signal exists with the right verdict vocabulary
for the baseline axis, and the contract document states the counting rule with its populations. Four
material gaps remain: the deficit signal is never invoked by any workflow; it renders `clean` for a run in
which no required reviewer reviewed at all; the second D3 surface still renders *reviewed-clean* and
*never-ran* as the same string (the landing's own test asserts this); and the prescribed `display_detail`
composition violates the repository's own `display_detail` contract on two counts.

## Method

Read in full: `plan.md`, `report-01.md`.

Read the landed diff: `git show --stat fd292004`, then per-path `git show fd292004 -- <path>` for
`review_completeness.py`, `review_retrospective.py`, `bot-participation-contract.md`,
`automatic-review/SKILL.md`, `finalize-step-review-retrospective/SKILL.md`, `create-pr.md`,
`pr-review-operations.md`, `github_pr.py`, `_github_pr.py`, and the four test files.

Established the current tree as ground truth at `HEAD = 61a43e53`, and separated later landings with
`git log --oneline fd292004..HEAD -- <paths>`, which names three follow-ups touching the same code
(`6ba4dace` #1167, `064560ab` #1168, `9e9e9880` #1241) and two more touching the retrospective
(`b286928c` #1170, and later test-slice work).

Read the current files whole where relevant: `review_completeness.py` (1558 lines; constants block,
`_refusal_state`, `classify_bot`, `compose_review_state_summary`, `assess_deficit`, `check_completeness`,
`check_deficit`, `_emit_toon`, `_emit_deficit_toon`), `review_retrospective.py` (`_grade_comparison`,
`aggregate`, `main`), `bot-participation-contract.md` §§ "The counting rule", "The comparative deficit
signal", "A refusal resolves by CAUSE first", "Two axes", and `automatic-review/SKILL.md` §§ participation
guard, "Mark Step Complete", "Output", "Canonical invocations".

Searches run (all with the repository root as the search path unless stated):

- `grep -rn "deficit" marketplace/ .claude/ doc/ -l` (excluding `doc/plans`) — four files, none of which
  is a workflow step. `grep -rn "check_deficit\|assess_deficit\|cmd_deficit" --include=*.py marketplace/
  test/ .claude/` — the only non-test callers are inside `review_completeness.py` itself.
- `grep -rn -i "eight[ -]member\|seven member\|one of eight\|one of seven\|nine[ -]member\|one of
  nine\|ten member\|one of ten" --include=*.md --include=*.py marketplace/ test/ .claude/ doc/` — four
  hits, all reading "ten", all correct.
- `grep -rn "refused_awaitable" ... | grep -v "refused_unknown"` and `grep -rn "refused_hard" ... | grep
  -v "refused_unknown"` — no surviving two-way refusal enumeration.
- `grep -rn "comment(s) found" --include=*.md --include=*.py marketplace/ test/ .claude/` — nine hits, all
  in the changed sites or their tests; no stale restatement elsewhere.
- `grep -rn "_STATE_SUMMARY_BUCKETS" test/ marketplace/` — no test references it.
- `grep -n "required_reviewed" test/plan-marshall/automatic-review/*.py` — no test asserts the field.
- `grep -rn "summary card\|already reviewed\|trigger acknowledg\|Review finished" --include=*.md
  marketplace/bundles/plan-marshall/skills/automatic-review/
  marketplace/bundles/plan-marshall/skills/workflow-integration-github/` — no output.
- `grep -rn "required_bots\|optional_bots" .plan/marshal.json ...` — this repository configures
  `required_bots: pr-agent`, `optional_bots: coderabbit,sourcery`.

Pre-fix comparison: `git show fd292004^:<path>` for `review_completeness.py` (line 310) and
`review_retrospective.py` (line 201), confirming the two "before" claims literally.

Tests run (read-only, no repository file modified):

```
UV_HTTP_TIMEOUT=600 uv run python -m pytest \
  test/plan-marshall/automatic-review/test_review_completeness.py \
  test/plan-marshall/finalize-step-review-retrospective/test_review_retrospective.py \
  -o addopts="" -q
→ 184 passed
```

One behavioural probe executed against the library function with the marketplace `scripts` dirs on
`sys.path` (no file written):

```python
rc.assess_deficit(
    [{'bot_kind': 'pr-agent', 'reviewed': False, 'finding_count': 0},
     {'bot_kind': 'coderabbit', 'reviewed': True, 'finding_count': 4}],
    required_bots=['pr-agent'])
→ {'verdict': 'clean', 'baseline_max': 4, 'baseline_reviewers': ['coderabbit'],
   'required_reviewed': [], 'deficit_reviewers': [], ...}
```

and the rendered TOON for that payload, via `rc._emit_deficit_toon`.

String measurement (arithmetic only, `python3 -c`): `len('0 comment(s) found — 1 empty, 1 refused, 1
refused-structural (unified triage pending)') == 86`, `isascii() is False`.

## Deliverables

| # | *Done when* (plan) | Report claim | Ground truth in the tree | Verdict |
|---|---|---|---|---|
| D0 | "the contract is written with each population published, and the absence corpus is partitioned by cause" | Contract written in `bot-participation-contract.md`; partition documented as derivable from `refusal_patterns`; HALT does not trigger | § "The counting rule" exists with all three populations named (`bot-participation-contract.md:508-533`). No corpus was partitioned — derivability was documented instead | met-in-substance, weakened |
| D1 | "one vocabulary is defined in one place, and every consumer named in D2/D3 uses it" | `STATE_REFUSED_UNKNOWN` + `_refusal_state()`; nine-member taxonomy in the contract; cause member split out | `STATE_REFUSED_UNKNOWN` at `review_completeness.py:204`; `_refusal_state` at `:425-467` is total and injective; the contract is the single definition site; eight downstream restatements corrected | met |
| D2 | "the signal fires on the two deficit rows, stays silent on the clean row, and reports the two baseline-less rows as unassessable" | `assess_deficit()` + a `deficit` subcommand, `gates_merge: false` | `assess_deficit` at `:614-706`, `check_deficit` at `:928-1010`, `cmd_deficit` at `:1268`, subcommand registered at `:1540`. All four verdict behaviours tested and passing. **But** no workflow invokes it, and it returns `clean` when no required reviewer reviewed | partially met |
| D3 | "no surface renders 'nobody reviewed' and 'reviewed clean' as the same string, proven by a test per surface" | Both surfaces done | Surface 1 met and tested (`test_nobody_reviewed_and_reviewed_clean_render_differently`). Surface 2 **not** met: both render `participation: unmeasurable` | partially met |
| D4 | "all five behave as specified, each proven to fail before the change" | Two flipped tests observed `2 failed`; new-symbol tests AttributeError pre-fix | All five behaviours are tested and pass. The "fail pre-fix" proof for the new tests is a missing-symbol `AttributeError`, which is vacuous; the plan's stronger demand ("confirm a naive detector *does* fire on (b) and (c)") was substituted, not performed | met, weakly evidenced |

### D0 — the counting rule, stated as a reusable contract

`marketplace/bundles/plan-marshall/skills/automatic-review/standards/bot-participation-contract.md:508`
opens § "The counting rule" with "Three named quantities, each with its population published", and the
three bullets deliver exactly what the plan asked: the **finding count** ("the number of filed
`pr-comment` findings attributed to that reviewer's `bot_kind` … never a raw comment count", `:513-521`,
explicitly naming the both-directions failure the plan's ⚠ describes), the **reviewed-at-all predicate**
("a reviewer reviewed the diff iff its taxonomy state is `participated` or `participated_but_empty`",
`:522-528`), and the **required-vs-optional denominator** ("the **required set** … the **optional set** …
and the **enabled roster** (required ∪ optional)", `:529-533`). The rule is genuinely consumed rather than
decorative: `_REVIEWED_STATES` at `review_completeness.py:279` is the predicate, and `check_deficit` reads
filed findings at `:983`.

The partition obligation was met differently from how the plan framed it. At the landing, the contract
said (`git show fd292004:…/bot-participation-contract.md:344-351`) "The cause partition is therefore
**derivable from the tree**" and that the cause member is "deliberately **not wired** here". The plan asked
to "partition the absence corpus by CAUSE", noting "Diff sizes are recoverable from merge commits, so this
is cheaply derivable". No corpus was partitioned and no diff size was recovered from any merge commit; what
landed is a statement that the registry data supports the partition. That is a legitimate scoping call
under the plan's own split threshold — and the invariant the partition exists to protect ("do not report a
participation rate over a corpus pooled across causes") is stated and no rate was reported — but the
literal *Done when* clause was not discharged. The wiring landed later in #1167 (`6ba4dace`), and today the
contract's § "Two axes" (`:365-407`) describes a fully computed partition.

### D1 — the reviewer-state vocabulary

The pre-fix defect is confirmed literally. `git show fd292004^:…/review_completeness.py` line 310:

```python
awaitable = bot_registry.rate_limit_class(bot) == 'awaitable_window'
return STATE_REFUSED_AWAITABLE if awaitable else STATE_REFUSED_HARD
```

a binary test over a three-valued field, exactly as the plan's OBSERVED claim states.

Today `_refusal_state` (`review_completeness.py:425-467`) is total and injective over the class axis, with
`unknown`/anything-else failing closed to `STATE_REFUSED_UNKNOWN` (`:465-467`), and
`bot_registry.rate_limit_class` itself fails closed to `'unknown'` for an absent or malformed field
(`bot_registry.py:513-514`), so the new member is reachable for an unregistered bot as well as for
pr-agent. `STATE_REFUSED_UNKNOWN` is in `_UNPROVEN_STATES` (`:258`), so the new member still blocks — the
right call, since a refusal is a refusal.

All three registry documents declare the field, with the values the report states:
`coderabbit.md:56` `rate_limit_class: awaitable_window`, `sourcery.md:49` `hard_quota`,
`pr-agent.md:134` `unknown`. The plan's instruction not to carry forward the older "only one declares it"
wording was honoured.

The drift risk the new member created was chased down. A whole-tree sweep for member-count prose returns
only four hits, all reading "ten" and all correct: `bot-participation-contract.md:52`,
`bot-participation-contract.md:73`, `review_completeness.py:189`, `automated-review-lifecycle.md:56`;
`create-pr.md:201` likewise reads "closed ten-member". A sweep for `refused_awaitable`/`refused_hard`
without `refused_unknown` finds no surviving two-way enumeration. The count is also machine-guarded:
`test/plan-marshall/automatic-review/test_bot_participation_contract.py` reads the contract's own prose
count back as an integer and compares it to a member tuple whose length is load-bearing (the diff at
`fd292004` extends both).

### D2 — the deficit signal

The verdict vocabulary and the baseline logic are right on the axis the plan specified.
`assess_deficit` (`review_completeness.py:614-706`) computes `baseline` as the non-required reviewers with
`reviewed` true (`:672-675`), returns `DEFICIT_UNASSESSABLE` when that list is empty (`:682-683`), and
otherwise reports a deficit only when `baseline_max - count >= min_deficit` (`:686-691`), so `0 : 0`
against a real baseline lands in `clean`. The non-gating declaration is machine-readable and rendered
verbatim: `'proves': 'reviewer_quality_only'` and `'gates_merge': False` (`:701-702`), printed by
`_emit_deficit_toon` (`:1137-1138`). The finding count is the filed `pr-comment` count read from the store
(`check_deficit:983`), matching the counting rule.

Two gaps sit against this deliverable.

**Nothing invokes it.** `grep -rn "deficit" marketplace/ .claude/ doc/ -l` (excluding `doc/plans`) returns
`tools-script-executor/SKILL.md` (an unrelated use of the word), `automatic-review/SKILL.md`,
`bot-participation-contract.md`, and `review_completeness.py`. In `automatic-review/SKILL.md` the only
occurrences are the § "Canonical invocations" block at `:999-1028` — a declaration of the argparse surface,
not a workflow step. No step in `automatic-review/SKILL.md`, `phase-6-finalize/`, or
`finalize-step-review-retrospective/` runs `review_completeness deficit`. The plan's D2 opens "A required
reviewer returning materially fewer findings … **is reported**"; in the tree as it stands, nothing reports
it, because nothing calls it.

**It renders `clean` when no required reviewer reviewed.** Executed, not inferred — the probe above returns
`verdict: clean` for a baseline reviewer with four findings and a required reviewer that refused, and
`_emit_deficit_toon` then omits `required_reviewed` entirely because it is empty (`:1145-1149`, `if
required_reviewed:`). The rendered block is:

```
verdict: clean
proves: reviewer_quality_only
gates_merge: false
baseline_max: 4
baseline_reviewers[1]:
  - coderabbit
```

A reader is told "clean" and shown no row at all for the required reviewer. That is the plan's own
vacuous-set archetype — "Deriving rows from the responding set makes the detector's population a strict
subset of its own domain" — landing inside the signal the plan built to close it. The `check_deficit` CLI
path partially rescues this by appending `reviewers[]` (`:1006-1008`, printed at `:1155-1160`), which does
carry `pr-agent,false,0,refused_hard`; but the `verdict` field itself — the one a consumer reads — says
`clean`. `grep -n "required_reviewed" test/plan-marshall/automatic-review/*.py` returns nothing, so no test
pins this case in either direction.

### D3 — the reviewer-state distribution reaches the field

**Surface 1 — met.** `compose_review_state_summary` (`review_completeness.py:586-611`) tallies
`_STATE_SUMMARY_BUCKETS` (`:294-311`), the field is on the envelope (`:918`), and it is emitted when
non-empty (`_emit_toon:1022-1024`). `automatic-review/SKILL.md:795-806` prescribes interpolating it into
Branch A's `--display-detail`. The discriminating test exists and passes:
`test_review_completeness.py:1881-1895`, `test_nobody_reviewed_and_reviewed_clean_render_differently`,
asserting `nobody == '3 refused'`, `reviewed_clean == '3 empty'`, and `nobody != reviewed_clean`.

**Surface 2 — not met.** `review_retrospective.py:331` is the whole per-row classifier:

```python
participation = 'measured' if raw_total > 0 else 'unmeasurable'
```

A reviewer that reviewed and found nothing files no records, so `raw_total == 0` and it renders
`unmeasurable` — the identical string a reviewer that never ran renders. The landing's own test says so in
as many words (`test_review_retrospective.py`, `test_enabled_reviewer_with_no_findings_gets_an_unmeasurable_row`):

> "produced nothing", "never ran", and "enabled-invoked-refused" all leave no record; without a row they
> render identically. The row names the reviewer and marks it unmeasurable — never scored — rather than
> omitting it.

Naming a reviewer instead of omitting it is a genuine improvement over the no-row defect, and the
`unmeasurable` label is honest about what the store can substantiate. But the plan's *Done when* is "no
surface renders 'nobody reviewed' and 'reviewed clean' as the same string, proven by a test per surface",
and on this surface they are the same string, with no test proving otherwise. There is no test in
`test_review_retrospective.py` that asserts a reviewed-clean row differs from a never-ran row — the search
`grep -rn "compose_review_state_summary" test/` locates the surface-1 proof, and the surface-2 test file
contains only the roster-population tests quoted above.

A later plan (#1170, `b286928c`, confirmed by `git log -S'_grade_comparison'`) added `_grade_comparison`
(`review_retrospective.py:107-155`), which takes a `reviewed_reviewers` set and grades the whole run
`clean` versus `indeterminate` — closing the collapse at the **aggregate** level. The per-row
`participation` field was not revisited and still ignores `reviewed_reviewers`, even though that set is now
a parameter of the same `aggregate()` call (`:214-217`).

### D4 — tests, each verified to fail pre-fix

Every behaviour the plan enumerates has a test, and all 184 tests in the two files pass.

- (a) two deficit rows: `test_row_a_deficit_four_to_zero`, `test_row_b_deficit_two_to_zero`.
- (b) `0 : 0` with a real baseline stays clean: `test_row_e_clean_zero_to_zero_with_a_real_baseline`,
  asserting `DEFICIT_CLEAN` and `deficit_reviewers == []`.
- (c) baseline-less rows: `test_rows_c_and_d_unassessable_when_every_baseline_refused`, asserting
  `DEFICIT_UNASSESSABLE`, `!= DEFICIT_CLEAN`, and `baseline_reviewers == []`.
- The named blind-spot test exists: `test_required_count_alone_cannot_distinguish_the_rows`, holding
  `required_count == 0` fixed and varying only the baseline across all three verdicts.
- The 150,000 figure is not pinned anywhere; `sourcery.md:43` keeps the detection pattern number-free
  ("your pull request is larger than the review limit of") and reads the figure through
  `refusal_size_cap_patterns` instead, exactly as the plan's ⛔ demanded.

The "proven to fail pre-fix" evidence is uneven. The two flipped collapse-tests are a real pre/post pair —
the pre-fix classifier at `fd292004^:310` genuinely returned `refused_hard` for pr-agent, so
`test_refusal_of_unknown_class_is_its_own_state_not_hard` must have failed. For the deficit tests, the
report's stated proof is that "New/changed functions did not exist pre-fix, so their tests AttributeError
against pre-fix code" — which is true of any new function and carries no discriminating information. The
plan's Verification section asked for something stronger and specific: "confirm that a naive detector *does*
fire on them today, so the test is discriminating rather than decorative". No such naive detector was
constructed; `test_required_count_alone_cannot_distinguish_the_rows` was substituted for it. The
substitution is reasonable and the report is transparent about what it did, but the plan's clause was not
discharged as written.

## Report-claim audit

**Claim re-derivation table**

| Report claim | Verdict | Evidence |
|---|---|---|
| `display_detail` rendered nobody-reviewed identically to reviewed-clean | ACCURATE | `git show fd292004^:…/automatic-review/SKILL.md` Branch A composed the count-only string; the plan's own quotation matches |
| "…with the default-empty `required_bots`, `participation_complete` is vacuously true, so Branch A fires" | OVERSTATED | This repository configures `required_bots: pr-agent` and `optional_bots: coderabbit,sourcery` (`.plan/marshal.json:117-118`), so the vacuous-quorum path is not how the observed run reached Branch A. The *defect* claim is right; this particular mechanism for it is not the one in force here |
| The refusal taxonomy exists but never reaches `display_detail` | ACCURATE | Pre-fix envelope carried `bot_states` but no summary field; `review_state_summary` is new at `:918` |
| `review_completeness.py:310`: `awaitable = rate_limit_class(bot) == 'awaitable_window'` | ACCURATE | Verified verbatim at that exact line in `fd292004^` |
| All three registry docs declare `rate_limit_class`; coderabbit=`awaitable_window`, sourcery=`hard_quota`, pr-agent=`unknown` | ACCURATE | `coderabbit.md:56`, `sourcery.md:49`, `pr-agent.md:134` |
| The refusal pre-filter enumerates known shapes rather than positively validating | ACCURATE (and still true) | `_github_pr.py:155-187`, `_is_refusal_notice`: registry `refusal_patterns` OR the structural `_is_rate_limit_notice`; no positive test of what review feedback must contain |
| "see 'Out of this plan (split)'" (the cross-reference attached to that row) | FALSE | No section by that name exists in `report-01.md`. Its sections are: Skills loaded, Claim re-derivation, Scoping decision, Deliverables, Build gate, Findings, Reviewer participation, Cost, Contract check, What have we learned, Residue. § "Scoping decision" discusses only the cause member, not the pre-filter |
| `review_retrospective.aggregate()` built `reviewers[]` purely from finding records | ACCURATE | `git show fd292004^:…/review_retrospective.py:201`, `for author in sorted(per_reviewer)` |
| The 150,000 threshold is not re-derivable; Sourcery's size pattern is number-free | ACCURATE | `sourcery.md:43` is number-free; the figure is read via `refusal_size_cap_patterns` at `:47` |
| The partition is derivable because Sourcery declares a size notice and a quota notice as distinct `refusal_patterns` | ACCURATE | `sourcery.md:42-44` declares exactly those two entries; `refusal_size_patterns:46` carries only the size one |

**Deliverable and process claims**

| Report claim | Verdict | Evidence |
|---|---|---|
| Commits `058d761`, `11df4da`, `3ab4e76`, `9f37480`, `607fa10`, `1bb595e`, head `7ecd755` | UNVERIFIABLE | `git cat-file -t` reports "Not a valid object name" for all seven — expected after a squash merge with the branch deleted. Not evidence against the report, but the per-commit attribution cannot be checked |
| `STATE_REFUSED_UNKNOWN` + `_refusal_state()` added, one-to-one over three classes, added to `_UNPROVEN_STATES` | ACCURATE | `:204`, `:425-467`, `:258` |
| `assess_deficit()` + a `deficit` subcommand carrying `gates_merge: false` / `proves: reviewer_quality_only` | ACCURATE | `:614`, `:1268`, `:1540`, `:701-702` |
| "Fires only against a real baseline; `unassessable` when every other reviewer refused; never on `0 : 0`" | ACCURATE | `:682-691`, plus the four passing tests |
| `compose_review_state_summary()` + `review_state_summary` field; Branch A interpolates it | ACCURATE | `:586`, `:918`, `automatic-review/SKILL.md:797`, `:805` |
| Surface 2 "emits a row per **enabled** reviewer (roster ∪ observed), each carrying `participation: measured \| unmeasurable`, closing the vacuous-set (no-row) defect" | OVERSTATED | The row emission is accurate (`review_retrospective.py:317`). "Closing the vacuous-set defect" is only half true: the no-row collapse is closed, the same-string collapse is not — the three named facts all render `unmeasurable` (`:331`), which the accompanying test asserts |
| "eight documentation-drift instances … all were **fixed** (commit `607fa10`), then confirmed clean by full-tree greps" | ACCURATE | All eight named sites carry the corrected text today, at drifted line numbers: `review_completeness.py:189` ("Ten members"), `automated-review-lifecycle.md:56` ("exactly one of ten"), `pr-review-operations.md:248` ("**ten** non-participation members") and `:258` (three-way refused row), `workflow-integration-github/SKILL.md:137`, `github_pr.py:812` and `:1035`, `_github_pr.py:178`, `test_github_pr.py:1009`. My independent whole-tree sweeps for stale member counts and two-way refusal enumerations return clean |
| "`test_required_count_alone_cannot_distinguish_the_rows` pins that `required_count == 0` is identical across all five rows" | ACCURATE | The test exists and passes; it varies only the baseline |
| "New/changed functions did not exist pre-fix, so their tests AttributeError against pre-fix code" (as the D4 fail-pre-fix proof) | ACCURATE BUT VACUOUS | True of any new symbol; it is not the discriminating pre-fix failure the plan's Verification section demanded for cases (b) and (c) |
| "`./pw verify` … 18979 passed, 14 skipped" | UNVERIFIABLE | Not re-run (the instructions forbid a full build). The two touched test files pass: 184 passed |
| Reviewer-participation table for PR #1165 (`cuioss-review-bot` reviewed, `coderabbitai` and `sourcery-ai` rate-limited) | UNVERIFIABLE | A property of the PR's comment surface, not of the tree |
| § Residue "Landing delegated" | CLOSED | Landed as `fd292004` |
| § Residue "Split-out: the wired quota-vs-diff-size cause member" | CLOSED | `6ba4dace` (#1167) wired the cause axis; the tree now carries `CAUSE_SIZE` (`:271`), `STATE_REFUSED_STRUCTURAL` (`:225`), `parse_causes`, `recover_causes_from_caps`, and a `size-caps` subcommand |
| § Residue "Contract-change proposal pending: manual `pull_request_read` polling as the in-session fallback" | CLOSED | `d8039616` (#1166); `cloud-plan-lane/SKILL.md:1528` now carries § "Manual read-polling is the in-session alternative to arm-and-hand-off" |
| § Residue "CodeRabbit's window reopens in ~5 min. Not awaited." | MOOT | A statement about the run, not a tree obligation |

The one FALSE claim is the dangling `see "Out of this plan (split)"` cross-reference, and its consequence is
substantive rather than cosmetic: the pre-filter remedy it pointed at never reached § Residue, so nothing
carries it forward (see Completeness review).

## Correctness review

**C1 — `assess_deficit` reports `clean` when no required reviewer reviewed.** `review_completeness.py:691`,
`verdict = DEFICIT_DEFICIT if deficit_reviewers else DEFICIT_CLEAN`. `deficit_reviewers` is built only over
`required_reviewed` (`:678-681`, filtered on `r.get('reviewed')`), so a required reviewer that refused,
was absent, or was never triggered contributes nothing and the else-branch fires. The verdict vocabulary
has an `unassessable` member for a missing *baseline* but none for a missing *required* review, so the
input space is not covered. Confirmed by execution (probe above) and by the rendered TOON, which drops the
empty `required_reviewed` line entirely (`:1145-1149`). The contract's own wording — "**clean** — a
baseline exists AND no required reviewer under-produced" (`bot-participation-contract.md:551-553`) — is
technically true and reads as an all-clear. **CONFIRMED.**

**C2 — the prescribed `display_detail` violates the repository's `display_detail` contract on two counts.**
`phase-6-finalize/standards/output-template.md:341-343` states the rules: "**Max 80 characters** (…the
renderer does not truncate)" and "**Plain ASCII** — no unicode glyphs"; `external-step-contract.md:55`
repeats "Plain ASCII — no unicode glyphs"; `branch-cleanup.md:1707` states the length must be checked
"against its placeholders' **worst-case expansion**, never its literal form". The composition this plan
introduced uses an em dash (U+2014) at `automatic-review/SKILL.md:797`, `:800`, `:805`, `:850`, and its
expansion over this repository's own three-bot roster measures 86 characters:
`0 comment(s) found — 1 empty, 1 refused, 1 refused-structural (unified triage pending)` — a wholly
ordinary outcome (pr-agent reviews clean, coderabbit rate-limits, sourcery size-refuses). A three-bucket
distribution including `refused-structural` and `not-triggered` reaches 98. `automatic-review/SKILL.md:856`
restates the ≤80/ASCII rule in the very section whose template breaks it. **CONFIRMED** (measured with
`len()` and `isascii()`).

**C3 — the empty-roster fallback reproduces the defect verbatim.** `compose_review_state_summary` returns
`''` for an empty `bot_states` (`:610-611`), and `automatic-review/SKILL.md:798` then falls back to
`"{N} comment(s) found (unified triage pending)"` — character-for-character the string the plan's Problem
section quotes as the defect. `automatic-review/SKILL.md:648` states that `required_bots` and
`optional_bots` "both default EMPTY", so in an unconfigured project the fix is inert and the collapsed
string returns. The docstring argues the empty string is the honest value for a roster that was never
configured, which is a fair argument about the *summary*; it does not extend to the *display string*,
which still reads to a cold reader as "a review happened and found nothing". **CONFIRMED.**

**C4 — no guard ties the display buckets to the taxonomy.** `_STATE_SUMMARY_BUCKETS` (`:294-311`) is an
explicit enumeration, and `compose_review_state_summary` sums only the states named in it (`:607-610`); a
state with no bucket is counted into `counts` and then silently dropped. `grep -rn "_STATE_SUMMARY_BUCKETS"
test/ marketplace/` finds no test referencing it, so nothing fails when a member is added without a
bucket — the tally would simply stop summing to the roster size, under-reporting exactly the way this
plan exists to prevent. This is the same drift class the plan *did* guard for the taxonomy prose
(`test_bot_participation_contract.py` reads the prose count back as an integer). The taxonomy has since
gained `refused_structural` and the bucket list was updated by hand in #1167 — the hazard is live and was
survived by attention, not by a guard. **CONFIRMED** (absence established by the named grep).

**C5 — an illustrative example describes a state its own branch cannot normally reach.**
`automatic-review/SKILL.md:800` says "So a run where three **required** reviewers all refused renders
`"0 comment(s) found — 3 refused (unified triage pending)"`". But every refusal member is in
`_UNPROVEN_STATES` (`:252-268`), `participation_complete = not required_unproven`
(`review_completeness.py:864`), and Branch A is "entered only after the participation guard above returns
`participation_complete: true`, or a force-done WARNING was recorded" (`SKILL.md:788`). Three refusing
*required* reviewers therefore route to Branch C (loop-back), not Branch A. The scenario is reachable only
through the force-done hatch; the ordinary case for this string is refusing *optional* reviewers.
**CONFIRMED.**

**C6 — `min_deficit` defaults to 1, so a one-finding gap is reported as a deficit.** `:616`, and the
docstring at `:641-644` calls that "a required reviewer that reviewed yet produced strictly fewer findings
than a baseline". The plan's D2 says "**materially** fewer findings". A 1-vs-2 split between two reviewers
on the same diff is ordinary variance, not a reviewer-quality bug. `test_min_deficit_threshold_is_honoured`
pins the threshold as configurable, so the mechanism is there; only the default is arguable. **CONFIRMED**
as a design choice worth revisiting, not as a defect.

No fail-open exception path, off-by-one, non-idempotence, or unguarded `None` was found in the changed
code. `check_deficit`'s store read is fail-closed (`:960-967`, an `OSError`/`ValueError` returns the
`load_failure` error branch rather than an empty-and-clean result), matching the plan's Notes rule "Branch
on producer STATUS before folding its payload". `recover_causes_from_caps` (`:469-503`, from the later
#1167) uses `setdefault` so an observed cause is never overridden, and is applied identically by `check`
and `deficit` (`:978`), which is the right shape.

## Completeness review

**Consumers swept, and found clean.** Every restatement of the taxonomy member count, of the refusal
split, and of the `display_detail` template was checked across `marketplace/`, `test/`, `.claude/`, and
`doc/developer/` — prose, docstrings, comments, and test docstrings alike. Four member-count statements,
all "ten"; no two-way refusal enumeration survives; nine occurrences of `comment(s) found`, all in the
changed sites or their tests. The eight drift sites the report names all carry corrected text. The bundle's
argparse `help=` strings were checked (`review_completeness.py:1298-1560`,
`review_retrospective.py:427-450`) and describe the current behaviour. This part of the work is genuinely
complete and better than most.

**Missing: the deficit signal has no caller.** Established by `grep -rn "deficit" marketplace/ .claude/
doc/ -l` and `grep -rn "check_deficit\|assess_deficit\|cmd_deficit" --include=*.py`. `bot-participation-contract.md:662`
lists `review_completeness deficit` in the § "Consumers" table — which describes what the command reads,
not who runs it. No finalize step, no workflow document, no retrospective step invokes it.

**Missing: no test for the required-did-not-review case.** `grep -n "required_reviewed"
test/plan-marshall/automatic-review/*.py` returns nothing. Of the nine deficit tests, none constructs a
required reviewer with `reviewed: False` alongside a *reviewing* baseline;
`test_rows_c_and_d_unassessable_when_every_baseline_refused` sets `reviewed=False` on the required
reviewer but also on both baselines, so the `not baseline` branch short-circuits before the gap can be
observed.

**Missing: no test proving surface 2 distinguishes the two facts.** The whole D3 *Done when* clause names
"a test per surface". Surface 1 has one; surface 2's tests
(`test_enabled_reviewer_with_no_findings_gets_an_unmeasurable_row` and siblings) assert the opposite.

**Missing: no bucket-coverage guard** (C4 above).

**Missing: the deferred pre-filter remedy left no trace.** The plan's Notes carry "Candidate remedy for the
pre-filter, not yet applied: restate it **positively** — a stored `pr-comment` finding must positively look
like review feedback", and the plan's § Expected surface names `github_pr.py`'s `fetch_findings` refusal
pre-filter. The report deferred it with a cross-reference to a section that does not exist and did not add
it to § Residue. `_github_pr.py:155-187` still enumerates (registry patterns, else the structural
recognizer), so the defect is live and unrecorded.

**Missing: the owed architecture insight was not recorded.** The plan's Notes state an insight this plan
"should record": *a review bot's persistent summary card and its trigger acknowledgement are participation
artifacts, not diff-derived claims — dispose of them as accepted without opening a fix task, and never read
their presence as evidence the bot reviewed the current HEAD*. `grep -rn "summary card\|already
reviewed\|trigger acknowledg\|Review finished" --include=*.md` over `automatic-review/` and
`workflow-integration-github/` returns nothing. The mechanical half of the insight pre-exists — the
currency rule (`bot-participation-contract.md:207`) and `STATE_DECLINED` (`:249`) both key on the
reviewed-commit SHA, and the `contentless_review_markers` conditional drop (`:459`) keeps a clean card from
consuming a triage decision — but the insight itself was never written down, and the report does not claim
it was.

## Out-of-scope compliance

Clean on all five exclusions.

- **Judging whether a reviewer's prose is "substantive".** Nothing added scores prose.
  `compose_review_state_summary` counts states; `assess_deficit` counts filed findings.
- **Reassigning which reviewer is `required` based on measured yield.** No code path writes
  `required_bots`, and `assess_deficit` returns `gates_merge: False` (`:702`) with no consumer able to move
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

Counts by severity: **0 blockers, 4 major, 8 minor** (12 gaps, listed in `gaps.md`).

The plan's hard mechanism landed and is correct where it landed: the three-valued `rate_limit_class` no
longer folds `unknown` into a positive hard-quota finding, the counting rule is written once with all three
populations published and is genuinely consumed by the code, and the eight documentation-drift instances
the new taxonomy member created were chased down and are still correct in the tree — a whole-tree sweep for
stale member counts and two-way refusal enumerations comes back clean. Every behaviour the plan's D4
enumerates has a passing test. What did not land is the *reaching a reader* half of the plan, which is the
half the plan's title is about. The deficit signal has no caller anywhere in the tree, so nothing reports it;
when it is called, it renders `verdict: clean` for a run in which no required reviewer reviewed at all,
omitting the empty `required_reviewed` line entirely — a false-green of exactly the shape the plan was
written to remove, re-entered inside the plan's own new signal. On the second D3 surface, *reviewed-clean*
and *never-ran* still render as the identical string `participation: unmeasurable`, and the landing's own
test asserts that they do; the aggregate-level half of that was closed later by #1170, the row-level half
was not. And the display string the plan prescribes breaks the repository's own `display_detail` contract on
both of its rules — a non-ASCII em dash, and 86 characters against an 80-character bound, on this
repository's own three-reviewer roster.
