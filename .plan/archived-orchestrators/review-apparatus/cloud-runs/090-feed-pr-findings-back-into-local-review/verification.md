# Verification — 090-feed-pr-findings-back-into-local-review

**Landed as:** PR #1204, squash commit `bb9ab493`
**Verdict:** verified-with-gaps

The plan's four deliverables all landed, and every named symbol, test, doc section and source
anchor the report claims exists in the tree today. One substantive problem remains: a report claim
attributes a git fact to the wrong PR number, which invalidates the corroborating detail hung on it.
A second, weaker problem is a reach limitation the report does not diagnose — the sole code
deliverable (the noun-set widening) cannot match the one count-prose finding the report advances as
its corroborating corpus evidence, because that prose puts a modifier between the number and the
noun. Neither is a fabrication of work; both are precision failures in a run that is otherwise
unusually well evidenced.

## Method

Read in full: `plan.md`, `report-01.md`.

Diff read: `git show --stat bb9ab493`, `git show bb9ab493 -- <each of the 7 changed paths>`.

Ground truth is the working tree of `claude/review-apparatus-analysis-mcf8md`. Every claimed symbol
was re-read at that state, not at the landing commit `bb9ab493` — so a reading below is evidence about
the current tree, not about the landing commit, and the two are distinguished wherever they differ.
The source tree is **not** frozen since the landing: `git diff --name-only bb9ab493 HEAD` lists
`doc/plans/**` plus the landing's own seven paths, which one later commit — `622f4484` (#1239) —
re-touched across the ext-self-review and finalize surfaces. That commit left the noun set and every
symbol read here undisturbed (`git log -S'commands?|checks?'` on the pattern module returns `bb9ab493`
alone — the `git log --oneline bb9ab493..HEAD` search below, and § Residue), so the "at HEAD"
readings below are stable — but stable by verification, not by absence of change.

Searches run (all reported absences are backed by one of these):

- `grep -rn "_CARDINALITY_NOUNS|_COUNT_PROSE|_NUMBER_WORDS"` over `*.py`/`*.md` → the four
  ext-self-review sites, plus three *independent* `_NUMBER_WORDS` tables that are not mirrors of this
  one: `plugin-doctor/scripts/_analyze_literal_count.py:179` (a `persona-security-expert`-scoped
  count contract) and two test-side tables in `test_bot_participation_contract.py:185` /
  `test_cleanup_contract.py:143`. None of the three consumes the cardinality-noun set.
- `grep -rni "cardinality noun"` over `*.py`/`*.md` (excluding `doc/plans/`) → eight hits: three of
  the four enumerating restatement sites (`ext-self-review-plan-marshall/SKILL.md:256`,
  `_self_review_detectors.py:1048`, `pre-submission-self-review.md:316` — the fourth, the
  `_CARDINALITY_NOUNS` constant itself, carries no such phrase and is reached by the constant sweep
  above), the `## Tests` coverage row at `SKILL.md:379`, one noun-agnostic schema row
  (`ext-point-self-review-surfacing.md:215`), two non-enumerating comment lines in
  `_self_review_patterns.py:163,169`, and one test comment (`test_self_review.py:1559`).
- `grep -rl "count_prose\|count-prose"` repo-wide → 20 tracked files (21 hits including
  `.pytest_cache`); each non-test, non-plan hit opened and read.
- `grep -rniE "operations?, *fields?, *steps?, *rules?"` repo-wide → the enumerating sites.
- `grep -n` for `test_count_prose_surfaces_check_noun` /
  `test_count_prose_does_not_fire_on_nouns_outside_closed_set`
  → both tests exist at `test_self_review.py:1558` and `:1585`.
- `grep -c "^def _detect_"` on the registry → 20 detectors, matching the 20 names `self_review.py`
  imports at `:45-64`; the emitted surface is 22 candidate lists (`len(CANDIDATE_LISTS)`), because
  two detectors return a pair.
- `git log --oneline -S'max_per_component' -- .../_lessons_query.py` → one commit, `010ea461` (PR #1039).
- `git log --oneline bb9ab493..HEAD -- <the touched ext-self-review and finalize paths>` → one later
  commit, `622f4484` (#1239), which did **not** alter the noun set (`git log -S'commands?|checks?'`
  returns only `bb9ab493`).
- `git log --oneline -S'_collect_skill_contract_sources'` on `_self_review_detectors.py` → two
  commits, `99a9a913` (the module decomposition) and `94bcddf2` (#1189); reading the latter's diff
  shows it is the one that moved `_detect_count_prose` off `skill_dir / 'SKILL.md'` and onto the
  shared resolver, confirming the file-scope widening the report attributes upstream.
- `git log --oneline -S"eight list flags" -- automatic-review/SKILL.md` → `064560ab` (#1168) and
  `9e9e9880` (#1241); `git log -S"nine list flags"` → `9e9e9880` alone.

Executed:

- `uv run python -m pytest test/pm-plugin-development/ext-self-review-plan-marshall/test_self_review.py -o addopts="" -q -k count_prose`
  → `5 passed` — 5 of `TestDetectCountProse`'s 8 cases; the other three do not carry `count_prose`
  in their names.
- A mutation probe that monkey-patches `_self_review_detectors._COUNT_PROSE` in process (no file was
  edited) and re-runs the two new tests' fixtures through the real `_detect_count_prose`, against the
  pre-fix five-noun set, the landed six-noun set, and an any-noun over-widening.
- A regex probe evaluating those three variants plus a `flags?`-extended set against
  `the eight list flags` / `nine list flags` / `nine flags`.
- A first-party re-derivation of the number-follower distribution, counted **per line** because the
  detector matches per line — a whole-file scan lets `\s+` cross a newline and inflates every figure
  (`checks` alone gains 8 spurious hits from TOON blocks such as `elapsed_sec: 210` followed by
  `checks[3]{...}`) — over the detector's real domain
  (517 `SKILL.md` + `standards/*.md` files under `marketplace/bundles/*/skills/*` at HEAD; **510** at
  the landing commit, which is the figure the report states), to check the report's "derived, not
  guessed" claim.
- A reach measurement over that same 517-file domain: lines the landed regex matches, versus lines a
  one-intervening-word allowance would add.
- `len(CANDIDATE_LISTS)` and the nine `nargs='?'` declarations in `review_completeness.py`, both
  computed rather than read off prose.

External evidence read through the GitHub MCP read surface: review threads on PR #1170, #1167, #1198.

No repository file was modified other than this file and `gaps.md`. No full build was run.

## Deliverables

| # | *Done when* (plan) | Report claim | Ground truth in the tree | Verdict |
|---|---|---|---|---|
| D0 | Every accepted finding has a yes/no with a named detector per yes; the unanswered set is reported with its size | 43 observed · 30 answered · yes 3 · no 27 · unanswered 13; both plan anchors absent from the window | Counts are internally consistent (30 = 3+27, 43 = 30+13). Two spot-checks match exactly (#1170 all-answered, #1167 four-unanswered incl. the count-prose finding). One anchor's git provenance is misattributed to the wrong PR number. The plan's "re-derive the registry" obligation is unreported | verified-with-gaps |
| D1 | Each security-shaped candidate classified activation-question or detector-gap, both drop paths named, per-run verification stated unavailable | One candidate (path traversal, #1201) → activation question; Path A `lane_dropped`, Path B `security_class_omitted`; per-run lane unavailable | Every anchor re-confirmed at HEAD: `tier: full`, `persona: persona-security-expert`, `order: 9`, `_TIER_RANK`, `_apply_security_class_inactive`, the exact drop-reason string, `_CEREMONY_FINALIZE_DEFAULT = 'auto'`. The #1201 fix exists in the tree with a `/etc/passwd` comment | verified |
| D2 | Each yes has a new detector or a justified widening; the docstring contradiction is fixed | No new detector; `check` added to the noun set; four consumer restatements updated in lock-step | The widening and all four restatements survive at HEAD, and the docstring contradiction is genuinely resolved. **But** the clause's first half is met by none of the three yeses (already-covered, routed out, routed out) — the report restates it at `report-01.md:81`; the widening does not reach the corpus finding offered as its corroboration (an adjacency limit the report never diagnoses); five higher-frequency derivation candidates were never adjudicated; and a fifth restatement site was missed | verified-with-gaps |
| D3 | Both cases exist per detector, each proven discriminating by mutation | Positive `nine checks`/`two checks`/`one check`; negative `5 deliverables`/`3 modules`/`5 checkpoints`; mutation-proven in scratch | Both tests exist and pass. The mutation result reproduces independently, at the regex level and through the real detector: the positive fails on the five-noun set, the negative fails under any-noun. The proof harness is not in the repo, and the positive is not "drawn from the real accepted finding" the clause names — an unreported substitution | verified-with-gaps |

### D0 — the answered-finding corpus

**What holds.** The published counts satisfy the plan's Verification demand ("publish the corpus
size, the yes count, the no count, and the unanswered count") and are arithmetically consistent.
The gate's environmental precondition — posted answers readable — is corroborated: PR #1170's four
inline threads each carry a `cuioss-oliver` disposition reply and a CodeRabbit acknowledgement, and
all four are `is_resolved: true`. That PR is correctly absent from the report's unanswered list.

The unanswered claim for PR #1167 is exact. The PR carries four inline threads, every one
`is_resolved: false` with `total_count: 1` — a bot comment and no reply. That is precisely the
report's "#1167 (×4)" (report-01.md:123).

The third of those threads is the count-prose corroborator the report cites at report-01.md:45. Its
body reads:

> **Update the list-flag cardinality text.** This change adds `--refused-causes`. The nearby text
> still refers to "six" list sets and "seven" list flags. The `check` command now declares eight
> list flags.

That is the finding the report describes, verbatim in substance. CONFIRMED.

**What does not hold.** report-01.md:49 states:

> Confirmed from git: the flag AND its `if args.max_per_component < 0: … invalid_cap` guard were
> introduced together in the **same** squash-merged PR #1153 (`_lessons_query.py:232`), whose review
> threads are empty (Sourcery rate-limited, zero inline threads).

The file anchor is right — `marketplace/bundles/plan-marshall/skills/manage-lessons/scripts/_lessons_query.py:232`
is `if args.max_per_component < 0:` at HEAD, with `'error': 'invalid_cap'` at :236. The
"same PR" structure is right — `git log -S'max_per_component'` and `git log -S'invalid_cap'` on that
file each return exactly one commit, `010ea461`. But that commit is **PR #1039**
(`feat(manage-lessons): surface active lessons prospectively (#1039)`), not #1153. PR #1153 is
`1296ede1 feat(shims): give migration/back-compat shims an owner, floor, and removal trigger`, whose
`--name-only` stat contains no `manage-lessons` path at all. The load-bearing conclusion (the fix
shipped with the flag, so no posted answer accepted it as a review finding) survives; the corroborating
detail attached to it ("whose review threads are empty") was read off the wrong PR and is therefore
unsupported. CONFIRMED FALSE as to the PR number.

**Unreported obligation.** The Claim-labels table required re-derivation of the registry:

> The detector registry is the unit of change and holds roughly eighteen `_detect_*` functions |
> OBSERVED — ⚠ **the count is a lead** | Enumerate the registry at HEAD. ⛔ **Re-derive**

`grep -c "^def _detect_"` on `_self_review_detectors.py` returns **20** at HEAD, matching the 20
names `self_review.py:45-64` imports; the emitted surface is **22** candidate lists
(`len(CANDIDATE_LISTS)` computed = 22), because two detectors return a pair. The report never
states either re-derived figure. The obligation's purpose (catch a shape that already landed) was met
in substance — the report checks `unguarded_boundaries`, `source_of_truth` and `scan_derived_keys`
against specific candidates — but the enumeration itself is absent. CONFIRMED omission, minor.

### D1 — activation question, not detector gap

Every anchor re-verified at HEAD:

- `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/finalize-step-security-audit.md:1-14`
  — frontmatter carries `lane:\n  class: adversarial\n  tier: full`, `persona: persona-security-expert`,
  `order: 9`. All three match the report.
- `.../manage-execution-manifest/scripts/_manifest_lanes.py:23` — `_TIER_RANK = {'minimal': 0, 'standard': 1, 'full': 2}`;
  `:203` — `keep = _TIER_RANK[effective] <= _TIER_RANK.get(posture, _TIER_RANK['full'])`. The report
  quotes the predicate accurately.
- `.../manage-execution-manifest.py` at `bb9ab493` — `'execution_profile': execution_profile,` on
  line 2293 and `'lane_dropped': lane_dropped,` on 2294; `'security_class_omitted'` on 2286. The
  report's line anchors were exact at its own commit (they now sit at 2555/2556/2547).
- `.../_manifest_rules.py:343-396` — `_apply_security_class_inactive` occupies exactly that span at
  the landing commit, and `_SECURITY_CLASS_DROP_REASON = 'no declared affected files and empty live footprint'`
  at `:340` is the string the report quotes.
- `.../_manifest_rules.py:620` — `_CEREMONY_FINALIZE_DEFAULT = 'auto'`, supporting the report's
  framing note that reconciles the plan's "the `auto` lane drops it" against the posture axis.

The candidate itself is real: `marketplace/bundles/pm-documents/skills/plan-marshall-plugin/scripts/doc_references.py:253`
`_resolve_one` carries the fail-closed `except ValueError` with an in-code comment naming
`xref:../../../../etc/passwd#x[]`, and `git log` shows the file was introduced by
`28cce1bf feat(pm-documents): documentation domain owns its corpus (#1201)` — the PR the report names.

The report's supporting argument that `unguarded_boundaries` would not have caught it also checks
out: the `read_text` call in that function sits inside a `try:`, and `.exists()` is not in the
detector's matched boundary set. D1 is fully verified.

### D2 — the widening

**Landed and current.** All four restatement sites carry `check`/`checks` at HEAD:

1. `.../ext-self-review-plan-marshall/scripts/_self_review_patterns.py:178` —
   `_CARDINALITY_NOUNS = 'operations?|fields?|steps?|rules?|commands?|checks?'`
2. `.../scripts/_self_review_detectors.py:1048-1049` — the `_detect_count_prose` docstring now names
   `` ``check`` `` in the closed set.
3. `.../ext-self-review-plan-marshall/SKILL.md:256` — Detection Rule 14 names `check` in the closed set.
4. `marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/pre-submission-self-review.md:316`
   — Check 11 reads "operations, fields, steps, rules, commands, or checks".

The one later commit touching these files, `622f4484` (#1239), did not disturb the noun set
(`git log -S'commands?|checks?'` on the pattern module returns `bb9ab493` alone).

**The docstring contradiction is genuinely fixed.** The pre-fix comment claimed `nine checks` was
matched while `checks` was absent from the set; the fix makes the claim true rather than deleting
it, which is the resolution the plan's D2 asked for. Verified by mutation: with the pre-fix set,
`nine checks` → no match; with the landed set → match.

**The widening does not reach its own corroborating case.** report-01.md:45 offers PR #1167's
finding as the independent corpus corroboration for the widening, diagnosing it as "a
`count_prose`-archetype finding whose noun (`list flags`) sits OUTSIDE the detector's registered noun
set". The landed detector does not surface that prose, for **two** reasons, only one of which the
report names:

- `flags` is not in the closed six-noun set; and
- even adding `flags?` would not help, because `_COUNT_PROSE`
  (`_self_review_patterns.py:183-185`) requires the noun to be **immediately adjacent** to the
  number (`\b(?:\d+|{words})\s+(?:{nouns})\b`), and the real prose is `the eight list flags` — a
  modifier intervenes.

Verified by direct regex evaluation: with `operations?|fields?|steps?|rules?|commands?|checks?|flags?`,
`'nine list flags'` → `False`, `'the eight list flags'` → `False`, `'nine flags'` → `True`.

The adjacency limit is not incidental to this one phrase. Over the detector's 517-file contract-source
domain the landed regex matches **189** lines; allowing at most one intervening word token would add
**113** more (`two keyed-map step`, `one scalar field`, `2 active-plan check`, …). So the reach gap is
broad — and so is the noise a naive fix would admit, which is why the remedy is a derivation, not a
loosening (see G2 in `gaps.md`).

**The prose the #1167 finding named is NOT still stale — that reading is refuted.** The finding was
acted on, in the immediately following PR: `064560ab` *"fix(review-apparatus): address CodeRabbit
review comments from #1167 (#1168)"* raised the FIND-step figures from six/seven to seven/eight and
the parser-surface figure from seven to eight. `9e9e9880` (#1241) then raised the FIND-step figures to
**eight** and the parser-surface figure to **nine**, in one commit. The two live figures name two
different populations and are each correct:

- `automatic-review/SKILL.md:684`, `:686`, `:691` say **eight**, and are scoped to the
  `review_completeness check` invocation printed immediately above them at `:675-682`, which passes
  exactly eight list flags.
- `:980` and `review_completeness.py:1301` say **nine**, and are scoped to the parser's whole flag
  surface. Nine is authoritative: `grep -n "nargs='?'"` on `review_completeness.py` returns nine hits
  — `--required-bots`, `--optional-bots`, `--participated-bots`, `--in-progress-bots`,
  `--refused-bots`, `--stale-participation-bots`, `--declined-bots`, `--refused-causes`,
  `--refusal-size-caps`.

The ninth flag, `--declined-bots`, is supplied only from the phase-6 re-review path
(`phase-6-finalize/standards/branch-cleanup.md:833`), which is why the earlier FIND-step call omits
it. The residual defect is therefore a clarity one, not a staleness one: nothing in the document
states that the eight-flag and nine-flag figures are scoped to different call sites, so a reader —
or the count-prose check this plan exists to feed — cannot tell scoped-correct from stale.

Two facts about the #1167 thread survive unchanged: it received **no posted answer** (four threads,
all `is_resolved: false`, `total_count: 1`, re-read through the GitHub review-comment surface), and
the widened detector cannot see the shape it reported. "Unanswered" and "unfixed" are different
claims, and only the first holds here.

**"Derived, not guessed" is overstated.** The plan required (plan.md:111-113):

> ⚠ **Widening must be DERIVED, not guessed.** … **Derive the noun set from the counts that actually
> appear in the corpus, and state whether the resulting set is closed.**

I re-ran the derivation over the detector's real domain — 517 contract-source files at HEAD. The
report's figure of **510** is exact at its own commit (`git ls-tree -r bb9ab493` yields 510 such
files); the corpus has grown by seven since, so the two numbers agree rather than conflict. The
report's *characterisation* reproduces: the number-follower distribution is dominated by `of` (303),
`and` (123), `px` (116), `is` (87). That part is honest and independently confirmed.

But the derivation was used only to justify *not* widening to any noun. The member actually added
came from the plan's own docstring example, and the report says so at report-01.md:76 ("`check` is
added because it is (a) the plan's cited evidence…"). Re-derived over the 517-file domain (singular
+ plural, case-insensitive, counting every match on a line but never across a newline, so the count
matches what the line-scoped detector can see), the structural nouns outside the closed set rank:
`deliverable`/`deliverables` **67**, `module`/`modules` **44**, `state`/`states` **25**,
`phase`/`phases` **24**, `flag`/`flags` **20**, `column`/`columns` **16**, `member`/`members` **13**
— against `check`/`checks` at **5**, the lowest of the set.

Two of those were in fact adjudicated, and the critique must say so: `deliverables` and `modules` —
the top two — are exactly the negative test's fixtures (`test_self_review.py:1597`), pinned as
must-not-fire, which is an adjudication recorded in executable form even though the report never
notes they are the corpus's most frequent candidates. The remaining five (`state`, `phase`, `flag`,
`column`, `member`) are un-adjudicated, and one of them is the exact noun the report's corroborating
finding uses. The set is stated closed at six, which satisfies the second half of the clause; the
first half ("derive the noun set from the counts that actually appear in the corpus") is claimed but
not shown.

**A fifth restatement site was missed.** report-01.md:77 claims consumer sites were updated "across
**four** restatement kinds", and report-01.md:114 claims "a repo-wide sweep for the five-noun
enumeration confirmed no other consumer site remained stale". Both statements are true as written —
that sweep looked for the noun enumeration. It did not look for the test-coverage index.
`marketplace/bundles/pm-plugin-development/skills/ext-self-review-plan-marshall/SKILL.md:379` is the
`## Tests` section's per-detector coverage row for this detector:

> - Stale count-prose detection: a modified sibling file plus a SKILL.md whose prose carries
> `twelve fields` / `5 rules` surfaces those count-prose lines (positive); a count planted in a
> sibling `standards/*.md` doc is surfaced too … a digit NOT adjacent to a cardinality noun surfaces
> nothing; a modified file outside any skill directory surfaces nothing; the same skill dir reached
> via two modified siblings deduplicates per `(file, line)`

It enumerates the pre-existing cases exhaustively and names neither of the two cases this plan
added. Its sibling rows (for example the flag-guard-pair row at `:369`) do enumerate every case, so
the omission is a drift, not a style difference. The repo's own rule at
`marketplace/bundles/plan-marshall/skills/persona-plan-marshall-agent/standards/agent-behavior-rules.md:270`
governs this exactly: "When you add a member to the indexed set, add its index row in the SAME
change."

### D3 — the two tests

Both exist and pass. `test/pm-plugin-development/ext-self-review-plan-marshall/test_self_review.py:1558`
(`test_count_prose_surfaces_check_noun`) and `:1585`
(`test_count_prose_does_not_fire_on_nouns_outside_closed_set`); the class runs `5 passed` under
`-k count_prose`.

Discrimination reproduced independently rather than taken on the report's word — twice: once at the
regex level, and once by monkey-patching `_COUNT_PROSE` in process and re-running both tests'
fixtures through the real `_detect_count_prose`. Against the pre-fix five-noun set the positive test
fails and the negative passes; against the landed six-noun set both pass; against an any-noun mutant
the positive passes and the negative fails. Per-fixture:

| Fixture | pre-fix five-noun | landed six-noun | any-noun mutant |
|---|---|---|---|
| `nine checks` | no | yes | yes |
| `two checks` | no | yes | yes |
| `one check` | no | yes | yes |
| `5 deliverables` | no | no | yes |
| `3 modules` | no | no | yes |
| `5 checkpoints` | no | no | yes |

So the positive case genuinely fails pre-fix (not vacuous), and the negative case genuinely fails
under the over-widening the stop rule forbids. `5 checkpoints` does pin the trailing `\b`: `checks?`
cannot match inside `checkpoints`. The negative asserts `out == []`
(`test_self_review.py:1602`), not merely the absence of a substring, so it cannot pass vacuously.

Two bounds on the proof, one acknowledged by the report and one not:

- The mutation harness (`scratchpad/mutation_proof.py`) is not in the repo, so the proof is not
  reproducible from a clone. The report records this as CodeRabbit F5 and as residue.
- The plan asked for "one **positive** case drawn from the real accepted finding that motivated it"
  (plan.md:117-118). No accepted finding motivated this widening — the motivating case is the plan's
  own docstring observation, and the corpus corroborator was *unanswered*, not accepted. The positive
  fixture is therefore drawn from the docstring example and a real `phase-1-init/SKILL.md:857`
  instance ("The two checks are ordered: source-origin is primary, file-overlap secondary." —
  confirmed verbatim at that exact line). That is the best available substitute, and the report does
  **not** name the substitution — it writes the clause as satisfied instead (report-01.md:95). That
  omission, together with D2's restated clause at report-01.md:81, is recorded as G8.

## Report-claim audit

| # | Claim (report-01.md) | Verdict | Evidence |
|---|---|---|---|
| 1 | Posted answers are readable in this environment; the corpus was built from them, never the internal ledger (:21) | ACCURATE | PR #1170's four threads each carry a posted disposition reply; PR #1167's four carry none. Both surfaces read through the same read path the report names |
| 2 | Counts: 24 PRs, 43 findings, 30 answered, 3 yes, 27 no, 13 unanswered (:25-35) | ACCURATE where checkable | Internally consistent; #1170 and #1167 match exactly. The full 24-PR sweep is not reproducible here |
| 3 | 13 unanswered across #1167 ×4, #1158 ×2, #1198 ×6, #1195 ×1 (:123) | ACCURATE for #1167; PLAUSIBLE for #1198 | #1167 returns exactly four unanswered threads. #1198 returns **three** unanswered inline threads; the remaining three of the claimed six would have to be review-summary or issue-comment findings, which the report says it read but which I did not enumerate |
| 4 | PR #1170 finding #8 is MD040, already covered by markdownlint (:39) | ACCURATE | Thread 4 on #1170 is verbatim an MD040 fenced-code-language finding, dispositioned fixed |
| 5 | PR #1198 finding #23 is a recurring run-report placeholder finding (:41, :43) | ACCURATE | #1198 thread 1 is "Remove the leftover `_pending_` template block" on `doc/plans/truthful-signals/250-.../report-01.md` |
| 6 | The `--max-per-component` anchor's flag and guard shipped together in PR #1153 (:49) | **FALSE** (PR number) | `git log -S` on that file returns one commit, `010ea461` = PR #1039. PR #1153 (`1296ede1`) touches no `manage-lessons` path. The "same PR" structure and the `:232` anchor are correct |
| 7 | PR #1167 finding #3 flagged a "six/seven list flags" count whose noun sits outside the set (:45) | ACCURATE, diagnosis INCOMPLETE | The thread body matches verbatim in substance, and the thread is genuinely unanswered. But the binding reason the detector misses it is adjacency, not only the noun set — adding `flags?` still yields no match on `the eight list flags`. The finding was also *fixed* in the next PR (`064560ab`, #1168), which the report does not note; unanswered ≠ unfixed |
| 8 | The security audit is `tier: full`, `persona-security-expert`, `order: 9` (:58) | ACCURATE | Frontmatter of `finalize-step-security-audit.md` |
| 9 | Both drop paths, with line anchors and the drop-reason string (:60-61) | ACCURATE | Every anchor exact at `bb9ab493`; the reason string matches `_SECURITY_CLASS_DROP_REASON` |
| 10 | `unguarded_boundaries` would not have caught the #1201 traversal (:63) | ACCURATE | The `read_text` sits inside a `try:`; `.exists()` is not a matched boundary |
| 11 | The `SKILL.md`-only file scope was already fixed upstream in PR #1189 (:73) | ACCURATE | `git log -S'_collect_skill_contract_sources'` → `94bcddf2` (#1189); the resolver at `_self_review_detectors.py:276` returns `SKILL.md` plus `standards/*.md` |
| 12 | The docstring claimed `nine checks` while the set lacked `checks` (:75) | ACCURATE | Visible in the landed diff's `-` lines |
| 13 | The widening was derived from a 510-file scan of the detector's domain (:76) | POPULATION ACCURATE, INFERENCE OVERSTATED | 510 is exact at the landing commit (`git ls-tree -r bb9ab493`); the domain is 517 at HEAD. The *distribution characterisation* reproduces. But the added member was not selected from that distribution: five higher-frequency structural candidates (`state`/`states` 25, `phase`/`phases` 24, `flag`/`flags` 20, `column`/`columns` 16, `member`/`members` 13) are unadjudicated against `check`/`checks` at 5, while the two that top the distribution (`deliverable` 67, `module` 44) are adjudicated only implicitly, as the negative test's fixtures. The scan output is not in the repo |
| 14 | Consumer sites updated in lock-step across four restatement kinds (:77) | ACCURATE but INCOMPLETE | All four carry `check` at HEAD. A fifth restatement — the `## Tests` coverage index at `SKILL.md:379` — was not updated |
| 15 | A repo-wide sweep confirmed no other consumer site remained stale (:114) | ACCURATE as scoped | The five-noun enumeration sweep is complete; my independent sweep finds the same four sites. The sweep did not cover test-coverage index rows |
| 16 | The count_prose N15 schema is noun-agnostic and unaffected (:111) | ACCURATE | `extension-api/standards/ext-point-self-review-surfacing.md:152` — `count_prose[N15]{file,line,text}`, and `:215` describes it noun-agnostically |
| 17 | Both new tests exist and are in the passing set (:101) | ACCURATE | Both present; `5 passed` under `-k count_prose` |
| 18 | The positive fails pre-fix; the negative fails under any-noun over-widening (:92-93) | ACCURATE | Reproduced independently — see the D3 table |
| 19 | The routed-out run-report placeholder scan belongs to the cloud-plan-lane, which does not run ext-self-review (:43, :118) | ACCURATE | `.claude/skills/cloud-plan-lane/SKILL.md` references self-review only as its own sub-agent gate (`:590`); it never invokes the ext-self-review script |
| 20 | The disposition record requires neither rationale nor source; `--detail` optional on `resolve`, `required=True` on `add`; no source field exists (:127) | ACCURATE | `_findings_core.py:455` validates only `resolution not in RESOLUTIONS`; `manage-findings.py:299` `add … required=True` vs `:363` `resolve … --detail` optional; the only `--source` is the qgate provenance enum at `:390` |
| 21 | `cmd_post_responses` skips a `rejected` finding with no `resolution_detail` as `no_resolution_detail` (:127) | OVERSTATED (harmless) | `github_pr.py:1611-1613` applies the skip to **every** respondable finding, not only `rejected`. The asymmetry the report argues for is if anything stronger than stated |
| 22 | F3 fixed in commit `380e02d` (:137) | UNVERIFIABLE | `git cat-file -t 380e02d` → "Not a valid object name". Expected for a squash-merged branch; the *content* of the fix (`one check` in the positive fixture) is present at `test_self_review.py:1580-1583` |
| 23 | `./pw verify pm-plugin-development` = SUCCESS, `2234 passed` (:101) | UNVERIFIABLE | Not re-run (out of scope for this pass). The targeted subset passes |
| 24 | D0 corpus counts and D1 manifest anchors are analysis from evidence outside the clone (:112) | ACCURATE and commendable | The report bounds its own verifiability honestly; every in-clone anchor it names checks out |

## Correctness review

**No bugs were found in the landed code.** The change is a one-token addition to a regex alternation
plus documentation. Specific things checked and cleared:

- **Word-boundary integrity.** `(?:{_CARDINALITY_NOUNS})\b` places `\b` outside the alternation, so
  `checks?` cannot match inside `checkpoint`, `checklist`, or `checked`. Verified against
  `5 checkpoints` → no match.
- **Singular/plural.** `checks?` matches both `one check` and `nine checks`; `(?i)` covers casing.
  Both branches are pinned by the positive test.
- **No fail-open path.** The detector's surrounding logic (`_detect_count_prose`,
  `_self_review_detectors.py:1064-1092`) is unchanged; its `except OSError: continue` on the doc
  read predates this plan.
- **Noise bound.** Adding `check` yields **5** additional matches across the 517-file contract-source
  domain (`check` 3, `checks` 2) — re-derived, and smaller than any other candidate considered. Of
  those five, two are genuine stale-able cardinality claims (`phase-1-init/SKILL.md:857`
  "The two checks are ordered: source-origin is primary, file-overlap secondary.",
  `phase-4-plan/SKILL.md:825`), one is a non-cardinal *"at least one check"* phrasing
  (`phase-6-finalize/SKILL.md:498`), and two are incidental `Step N check` / `check N` phrasings
  (`marshall-steward/SKILL.md:672`, `ext-self-review-plan-marshall/SKILL.md:232`). The list is a
  review anchor excluded from `counts.total`
  (`ext-point-self-review-surfacing.md:177`), so the added surface cannot inflate the defect count.
- **Non-vacuity.** Neither new test passes both before and after the change: the positive fails
  pre-fix, the negative fails under the named over-widening mutant.

One cosmetic residue: the reflowed docstring at `_self_review_detectors.py:1049-1051` leaves a
one-word line ("the SAME") mid-sentence. Not a defect.

## Completeness review

1. **The corroborating corpus finding remains out of the detector's reach**
   (`_self_review_patterns.py:183-185`). Detailed under D2: the plan's only shipped code cannot
   surface the one real-world instance the report advances as its justification, and the report's
   diagnosis names only half the reason. The reach limit is general — a one-word allowance would add
   113 lines to the 189 the predicate matches over the contract-source domain.

2. **Five of the derivation's own candidates were never adjudicated.** `state`/`states` 25,
   `phase`/`phases` 24, `flag`/`flags` 20, `column`/`columns` 16, `member`/`members` 13, all more
   frequent than the added `check`/`checks` at 5, and none named in the report. The two *most*
   frequent — `deliverable`/`deliverables` 67 and `module`/`modules` 44 — are adjudicated, as the
   negative test's must-not-fire fixtures, though the report does not note that they head the
   distribution.

3. **Fifth restatement site missed** (`ext-self-review-plan-marshall/SKILL.md:379`). The `## Tests`
   coverage index for this detector does not name either new case.

4. **Registry enumeration not published.** The Claim-labels table's ⛔ re-derivation instruction was
   executed in substance but its result (20 `_detect_*` functions, 22 emitted candidate lists) never
   appears in the report.

5. **Derivation artifact absent.** `scratchpad/derive_nouns.py` and `scratchpad/mutation_proof.py`
   are both design-time artifacts that did not land, so neither D2's derivation nor D3's mutation
   proof is reproducible from the repository. The report records the second (F5, residue) but not
   the first.

6. **`automatic-review/SKILL.md` never states its eight-versus-nine scope split.** `:684`, `:686`
   and `:691` count the eight list flags the FIND-step invocation at `:675-682` passes; `:980` and
   `review_completeness.py:1301` count the parser's nine. Both are correct (see D2), but nothing says
   so, so the document reads as self-contradictory to anyone — or any detector — re-counting it.

7. **Two live stale count claims sit in the automatic-review test contract, outside the detector's
   file scope.** `test/plan-marshall/automatic-review/test_bot_participation_contract.py:983` reads
   "the pre-merge barrier passes five flags, not the participation guard's six", while
   `_CONFIRMED_SITES` (`:817-846`) declares **6** for both family-A sites, the module comment at
   `:807-809` says six, and the block at `branch-cleanup.md:829-836` interpolates six `--*-bots`
   flags — so both the figure and the "genuinely differ" rationale are false. `:850` reads "a sixth
   flag reaches the quoting scan automatically" while `_ALL_LIST_FLAGS`, derived live from the parser
   by `derive_bot_flags`, holds **seven**. The suite passes (78 passed) because neither claim is
   asserted. Neither is visible to `_detect_count_prose`: its domain is `SKILL.md` plus
   `standards/*.md` only (`_collect_skill_contract_sources`, `_self_review_detectors.py:276`), so
   every `.py` docstring and comment in the tree is outside its **file scope** — a third reach axis,
   alongside the noun set and the adjacency limit, that the run never names.

8. **Two *Done when* clauses were restated rather than met.** D2's "each yes has either a new
   detector or a justified widening" (plan.md:114-115) is satisfied by none of the three yeses;
   report-01.md:81 substitutes a narrower clause. D3's "one positive case drawn from the real
   accepted finding that motivated it" (plan.md:117-118) is not met either, and report-01.md:95
   writes it as satisfied. Both dispositions are correct under the plan's own Out-of-scope rules —
   the defect is the silent rewording, not the routing.

Checked and found NOT to be defects, recorded because a later reader will otherwise re-derive them:

- **The documentation is not wrong about reach.** The pattern comment
  (`_self_review_patterns.py:162`, `:179`), Detection Rule 14 (`SKILL.md:256`) and the plan's
  mandated cold read (`report-01.md:110`) all state the *immediately adjacent* requirement
  correctly, and the cold read's own answer ("does not match `version 3`, `5 deliverables`,
  `3 modules`, `5 checkpoints`") matches the regex exactly. The adjacency limit is a design limit to
  be re-decided, not the docstring defect reproduced by its own fix — the plan's cold-read check
  passes.
- **`_detect_count_prose`'s `except OSError: continue`** (`_self_review_detectors.py:1081-1082`) is
  a silent-skip fail-open: an unreadable contract source is dropped with no counter and no note. It
  predates this plan, is unchanged by the landing, and cannot flip a verdict because `count_prose` is
  excluded from `counts.total`. Out of scope, recorded so it is not re-found as new.
- **The symmetric-pair count claims are correct.** `SKILL.md:232` and the `## Tests` row at `:367`
  both say six pairings; `_PAIR_TOKENS` (`_self_review_patterns.py:47-54`) holds six.
- **Production string literals.** No argparse `help=`, `description=`, error template or log template
  restates the noun set. `self_review.py:565` derives its help prose from the registry
  (`f'Emit {len(CANDIDATE_LISTS)} candidate lists '`), so it cannot go stale; `:556` is a
  noun-agnostic `description=`. `grep -rni "cardinality noun"` over `*.py`/`*.md` (excluding
  `doc/plans/`) returns eight hits — doc sites, the `## Tests` coverage row, two non-enumerating
  comments, one noun-agnostic schema row and one test comment — and no string literal among them.
- **`ext-self-review-plan-marshall/SKILL.md:60`'s "twenty-two candidate lists" is correct.**
  `len(CANDIDATE_LISTS)` computes to 22.
- **The hand-maintained sibling-list mirror is complete.**
  `test_self_review_reachability_regression.py:114-136` enumerates 21 sibling lists plus the one
  under test = 22, and its comment states the hand-maintenance is deliberate (deriving it would make
  the assertion vacuous).
- **`plugin-doctor` was not duplicated.** It carries its own `_NUMBER_WORDS` and count-claim regex
  (`_analyze_literal_count.py:179,208`), but scoped to the `persona-security-expert` standards
  population only — no overlap with the cardinality-noun set, and the plan correctly left it alone.
- **Test fixtures and stubs.** The pre-existing `TestDetectCountProse` cases are all compatible with
  the widened set — none asserts that a `check` phrase must *not* fire.
- **The N15 schema and the extension-point surfacing standard** are noun-agnostic
  (`ext-point-self-review-surfacing.md:152`, `:215`).
- **`plan.md:59`'s "Three."** reads against four numbered items, but D0 is labelled "GATE, mutates
  nothing", so "three deliverables plus a gate" is a defensible reading of the same text. It is an
  ambiguity, not a demonstrable stale count; recorded as the lowest-severity gap rather than as a
  contradiction.

## Out-of-scope compliance

Compliant. The plan's Out-of-scope list names `plugin-doctor`, the simplify step, re-implementing
the reviewer, and the structural stop rule (cross-run state, a new configuration knob, semantic
judgement, a new bundle/skill/standard/extension point). The landing:

- touched no `plugin-doctor` file and no simplify surface (`git show --name-only bb9ab493` lists
  seven paths, none under either);
- added no configuration knob, no new skill, standard or extension point;
- correctly **routed out** the two candidates that would have breached the stop rule (the run-report
  placeholder scan, whose artifact the extension does not run over; and the authoritative-set →
  doc-prose-list mirror drift, which needs a pairing annotation), recording each rather than
  absorbing it — which is the discipline the plan asked for.

One note, not a violation: the landing edited
`marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/pre-submission-self-review.md`,
which lies outside the plan's "Expected surface" list. That edit is the lock-step consumer update
the plan's own D2 logic requires, and the plan lists an expected surface, not a permitted one.

## Residue status

| Residue item (report-01.md:197-200) | Status | Evidence |
|---|---|---|
| **Run-report placeholder scan** → route to a cloud-plan-lane report-completeness gate | **OPEN**, and the underlying defect is live | `.claude/skills/cloud-plan-lane/SKILL.md` has no placeholder/`TBD` scan; merge condition 4 (`:1428`) is the pre-existing prose obligation "the report is finalized and pushed". `grep -rn "^_pending_$" doc/plans/` returns 10 hits across **4** landed run reports |
| **Authoritative-set → doc-list mirror drift** | **OPEN** | The registry holds 20 `_detect_*` functions at HEAD; none spans a code set to a prose list. `_detect_source_of_truth` and `_detect_scan_derived_keys` are the adjacent ones the report already names as too narrow |
| **Disposition-flow evidence asymmetry** (a rejection must cite the artifact that settles it) | **OPEN** | `manage-findings.py:363` still declares `--detail` optional on `resolve`; the only `--source` in the skill is the qgate provenance enum at `:390`. No citation field exists on a disposition |
| **Unanswered-finding rate** (13 of 43) | **OPEN as a signal** | Corroborated on the two PRs I spot-checked: #1167's four threads and #1198's three inline threads all remain `is_resolved: false` with no reply |

No later plan in the tree closes any of these. `git log --oneline bb9ab493..HEAD` on the relevant
paths shows only `622f4484` (#1239), which touched the ext-self-review surface without addressing
any residue item.

## Summary

**Counts by severity:** 0 blockers · 1 major · 7 minor · 1 cosmetic. These map one-to-one onto
`gaps.md` G1–G9.

Major: one report claim attributes a git fact to PR #1153 when the commit is PR #1039, invalidating
the corroborating detail hung on it and sending a later auditor to an unrelated PR.

Minor, in `gaps.md` order: the widening does not reach its own corroborating corpus case, for an
adjacency reason the report never diagnoses (G2); the derivation is absent from the repo and five of
its higher-frequency candidates were never adjudicated (G3); a fifth consumer restatement, the
`## Tests` index, left stale (G4); the mandated registry re-derivation unreported (G5);
`automatic-review/SKILL.md` never states the scope split that makes its eight- and nine-figures both
correct (G6); two live stale count claims in `test_bot_participation_contract.py`, outside the
detector's file scope (G7); and two *Done when* clauses restated rather than met (G8). Cosmetic:
`plan.md:59`'s "Three." against four numbered items, defensible under the D0-is-a-gate reading but
never reconciled (G9).

**Bottom line.** This is a well-evidenced run whose every in-clone anchor survives scrutiny: D1 is
verified anchor-for-anchor, D3's tests exist, pass, and are genuinely discriminating under
independent mutation of the real detector, and the plan's hardest discipline — routing candidates out
rather than absorbing them because this was the file already open — was followed twice, correctly.
The weakness is concentrated in D2, and it is a weakness of *justification*, not of code. D2's
second clause is met — the widening landed, the docstring contradiction is genuinely resolved, and
all four restatements are current — but its first clause ("each yes has either a new detector or a
justified widening") is met by none of the three yeses, and the report restates the clause rather
than reporting the deviation. The plan's back-feed premise produced no code at all from the
accepted-finding corpus; the one code change shipped is the widening the plan itself pre-specified,
selected from the plan's own docstring rather than from the corpus the derivation scanned — and the
single real count-prose finding the exercise surfaced uses a noun (`flags`) in a shape
(`the eight list flags`) the widened detector cannot see, because a modifier separates the number
from the noun. The verdict remains verified-with-gaps: nothing claimed is fabricated, one factual
attribution is wrong, and the deliverable that was supposed to close the loop closes it only in the
narrow form the plan pre-specified.

## Adversarial review

This document and `gaps.md` have been re-derived twice, each time by an independent reader working
from the clone with no prior context and reproducing every load-bearing finding against the tree
rather than accepting it from the page. Every `path:line` citation in both documents has been
opened; every count in both has been recomputed. The two documents agree: `gaps.md` carries one
entry per finding this document establishes, at the same severity and with the same figures, and
nothing this document refutes remains actionable there.

**Method, precisely enough to re-run.** Ground truth is the working tree of
`claude/review-apparatus-analysis-mcf8md`; the landing commit is `bb9ab493`. Anchors were read with
`awk`/`grep -n` at the paths and lines cited, and at `bb9ab493` via `git show <sha>:<path>` where the
citation was stated against that commit. Provenance claims were re-run as
`git log --oneline -S'<token>' -- <path>`, and each named PR number was confirmed against the
commit's own subject line. Counts were computed, never read off prose: `grep -c "^def _detect_"` for
the registry; `len(CANDIDATE_LISTS)` imported and evaluated; `grep -n "nargs='?'"` on
`review_completeness.py` with the flag name recovered by walking back to the enclosing
`add_argument`; the contract-source corpus enumerated as `marketplace/bundles/*/skills/*/SKILL.md` ∪
`marketplace/bundles/*/skills/*/standards/*.md`, at HEAD and via `git ls-tree -r bb9ab493`; the
flag family derived live by `derive_bot_flags`, run under `pytest` so the shared helper's `conftest`
import resolves. **The follower distribution is counted per line, never over whole file text** —
`_COUNT_PROSE` is applied to one line at a time, so a whole-text scan lets `\s+` cross a newline and
manufactures matches the detector can never make. Regex behaviour was settled by execution: a probe
evaluating the pre-fix five-noun set, the landed six-noun set, a `flags?`-extended set and an
any-noun mutant against the fixture strings and the real prose; and a second probe monkey-patching
`_self_review_detectors._COUNT_PROSE` in process (no file edited, so no snapshot/restore was needed)
and running both new tests' fixtures — and the real `the eight list flags` sentence — through the
real `_detect_count_prose`. `pytest -k count_prose` was run (`5 passed`), as was the whole of
`test_bot_participation_contract.py` (`78 passed`). PR threads on #1167, #1170 and #1198 were re-read
through the GitHub review-comment surface. `git status --porcelain` was checked before and after and
is clean of this review's doing outside these two files.

**Upheld, reproduced exactly.** The PR #1153 → #1039 misattribution. Every D1 anchor (`tier: full`,
`persona-security-expert`, `order: 9`, `_TIER_RANK` at `_manifest_lanes.py:23` and the keep predicate
at `:203`, `_apply_security_class_inactive` spanning `343-396` at the landing commit, the drop-reason
string at `:340`, `_CEREMONY_FINALIZE_DEFAULT` at `:620`, the manifest emission lines at
2286/2293/2294 at `bb9ab493` and 2547/2555/2556 at HEAD, and `_resolve_one` at
`doc_references.py:253` with its `/etc/passwd` comment at `:281`). The four noun-set restatements and
the missed fifth (`SKILL.md:379`, which names six of `TestDetectCountProse`'s eight cases). The
20-detector registry and the 22 candidate lists. The nine `nargs='?'` flags and their names. The
517-file domain at HEAD and 510 at `bb9ab493`. The `#1167` ×4 and `#1198` ×3 unanswered thread
counts, and #1170's four resolved threads each carrying a disposition reply. The seven-path landing
diff. The 10 `_pending_` hits across four run reports. Every `manage-findings` / `github_pr.py`
disposition anchor, including that the `no_resolution_detail` skip at `github_pr.py:1611-1613`
applies to every respondable finding rather than only to `rejected`. The adjacency reach measurement
(189 matched lines; +113 under a one-word allowance). The corrected follower distribution — `of` 303,
`state`/`states` 25, `phase`/`phases` 24, `flag`/`flags` 20, `column`/`columns` 16, `member`/`members`
13, `check`/`checks` 5. The noise bound of 5 added matched lines. And D3's discrimination, upheld
through the real detector rather than only the regex.

**Overstated, and corrected here.** "The derivation's own candidates were never adjudicated" —
`deliverable`/`deliverables` (67) and `module`/`modules` (44) head the distribution and *are*
adjudicated, as the negative test's must-not-fire fixtures; the un-adjudicated set is the five
ranking below them. "D2's *Done when* is met" — its second clause is, its first is not, and the same
holds for D3's "drawn from the real accepted finding" clause; both were recorded as bounds rather
than as the gap they are (now G8). Of the five lines `check` newly matches, two are genuine
stale-able cardinality claims and one is a non-cardinal "at least one check" phrasing, not three
genuine. Three method statements were narrower than the searches they describe: the
`_collect_skill_contract_sources` history returns two commits on that file, not one; the
`cardinality noun` sweep returns eight hits whose breakdown omitted the `## Tests` row; and
`-k count_prose` selects five of the class's eight cases rather than the class.

**Refuted.** Two `path:line` citations did not resolve to the text they were hung on: the FIND-step
invocation is at `automatic-review/SKILL.md:675-682`, not `:672-679` (cited twice), and the plan's
"derived, not guessed" clause is at `plan.md:111-113`, not `:112-114`. The earlier reading that the
count CodeRabbit flagged on PR #1167 is *still stale* stays refuted, and the diffs confirm it:
`064560ab` (#1168) raised the FIND-step figures from six/seven to seven and the parser-surface figure
from seven to eight; `9e9e9880` (#1241) then raised the FIND-step figures to eight and the
parser-surface figure to nine in one commit, because they count two different populations — the eight
flags the `:675-682` invocation passes and the nine the parser declares, the ninth (`--declined-bots`)
being supplied only from `branch-cleanup.md:833`. The frequency figures previously written as
37/27/21/16/14/13 and `of` 307 are not arbitrary: they reproduce exactly under a whole-file scan, and
fail only because that scan lets the number and the noun sit on different lines — which the
line-scoped detector cannot do.

**Not verifiable from the clone, and left labelled as such:** the full 24-PR corpus sweep, the
`./pw verify pm-plugin-development` result, and the `380e02d` commit hash (a pre-squash branch
object, confirmed absent by `git cat-file -t`).

**Added by this pass.** Two live stale count claims in
`test/plan-marshall/automatic-review/test_bot_participation_contract.py` (`:983`'s "five flags"
against `_CONFIRMED_SITES`' six, and `:850`'s "a sixth flag" against a seven-member derived family),
and with them the detector's third reach axis — file scope, which excludes every `.py` docstring and
comment (G7). The D2/D3 clause restatements as a gap in their own right (G8). The re-derived
adjudication story that puts `deliverable` and `module` at the head of the distribution and inside
the negative test. The in-tree precedent for G3's remedy
(`test_bot_participation_contract.py:501-523`, which reads a prose closure count out of a contract
doc and asserts it against the derived member set). The cold read cleared: the pattern comment,
Detection Rule 14 and `report-01.md:110` all state the adjacency requirement correctly, so the plan's
cold-read check passes and the adjacency limit is a design decision to revisit, not a docstring
defect reproduced by its own fix. The pre-existing silent-skip fail-open at
`_self_review_detectors.py:1081-1082`, cleared as unable to flip a verdict. And the symmetric-pair
count claims (`SKILL.md:232`, `:367` against `_PAIR_TOKENS`), cleared as correct.
