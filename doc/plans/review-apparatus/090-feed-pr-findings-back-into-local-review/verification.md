# Verification — 090-feed-pr-findings-back-into-local-review

**Landed as:** PR #1204, squash commit `bb9ab493`
**Verdict:** verified-with-gaps

The plan's four deliverables all landed, and every named symbol, test, doc section and source
anchor the report claims exists in the tree today. Two substantive problems remain: the sole code
deliverable (the noun-set widening) does **not** cover the one count-prose finding the report itself
cites as its corroborating corpus evidence, and one report claim attributes a git fact to the wrong
PR number. Neither is a fabrication of work; both are precision failures in a run that is otherwise
unusually well evidenced.

## Method

Read in full: `plan.md`, `report-01.md`.

Diff read: `git show --stat bb9ab493`, `git show bb9ab493 -- <each of the 7 changed paths>`.

Ground truth is HEAD `61a43e53` on `claude/review-apparatus-analysis-mcf8md`. Every claimed symbol
was re-read at HEAD, not at the landing commit.

Searches run (all reported absences are backed by one of these):

- `Grep _CARDINALITY_NOUNS|_COUNT_PROSE|_NUMBER_WORDS` repo-wide → 4 in-bundle sites + test mirrors.
- `Grep -i "cardinality noun"` repo-wide → the four restatement sites plus one noun-agnostic schema row.
- `Grep "count_prose|count-prose"` repo-wide → 18 files; each non-test, non-plan hit opened and read.
- `Grep "operation.{0,12}field.{0,12}step.{0,12}rule.{0,12}command"` repo-wide → the enumerating sites.
- `Grep test_count_prose_surfaces_check_noun|test_count_prose_does_not_fire_on_nouns_outside_closed_set`
  repo-wide → both tests exist at `test_self_review.py:1558` and `:1585`.
- `grep -c "^def _detect_"` on the registry → 20 detectors at HEAD.
- `git log --oneline -S'max_per_component' -- .../_lessons_query.py` → one commit, `010ea461` (PR #1039).
- `git log --oneline bb9ab493..HEAD -- <the touched ext-self-review and finalize paths>` → one later
  commit, `622f4484` (#1239), which did **not** alter the noun set (`git log -S'commands?|checks?'`
  returns only `bb9ab493`).
- `git log --oneline -S'_collect_skill_contract_sources'` → `94bcddf2` (#1189), confirming the
  file-scope widening the report attributes upstream.

Executed:

- `uv run python -m pytest test/pm-plugin-development/ext-self-review-plan-marshall/test_self_review.py -o addopts="" -q -k count_prose`
  → `5 passed`.
- A standalone regex mutation harness (scratch, not written into the repo) evaluating the pre-fix
  five-noun set, the landed six-noun set and an any-noun over-widening against every fixture string
  in both new tests plus `six list flags` / `nine list flags`.
- A first-party re-derivation of the number-follower distribution over the detector's real domain
  (517 `SKILL.md` + `standards/*.md` files under `marketplace/bundles/*/skills/*`), to check the
  report's "derived, not guessed" claim.

External evidence read through the GitHub MCP read surface: review threads on PR #1170, #1167, #1198.

No repository file was modified other than this file and `gaps.md`. No full build was run.

## Deliverables

| # | *Done when* (plan) | Report claim | Ground truth in the tree | Verdict |
|---|---|---|---|---|
| D0 | Every accepted finding has a yes/no with a named detector per yes; the unanswered set is reported with its size | 43 observed · 30 answered · yes 3 · no 27 · unanswered 13; both plan anchors absent from the window | Counts are internally consistent (30 = 3+27, 43 = 30+13). Two spot-checks match exactly (#1170 all-answered, #1167 four-unanswered incl. the count-prose finding). One anchor's git provenance is misattributed to the wrong PR number. The plan's "re-derive the registry" obligation is unreported | verified-with-gaps |
| D1 | Each security-shaped candidate classified activation-question or detector-gap, both drop paths named, per-run verification stated unavailable | One candidate (path traversal, #1201) → activation question; Path A `lane_dropped`, Path B `security_class_omitted`; per-run lane unavailable | Every anchor re-confirmed at HEAD: `tier: full`, `persona: persona-security-expert`, `order: 9`, `_TIER_RANK`, `_apply_security_class_inactive`, the exact drop-reason string, `_CEREMONY_FINALIZE_DEFAULT = 'auto'`. The #1201 fix exists in the tree with a `/etc/passwd` comment | verified |
| D2 | Each yes has a new detector or a justified widening; the docstring contradiction is fixed | No new detector; `check` added to the noun set; four consumer restatements updated in lock-step | The widening and all four restatements survive at HEAD. The docstring contradiction is genuinely resolved. **But** the widening does not cover the corpus finding the report offers as its corroboration, and a fifth restatement site was missed | partially-implemented |
| D3 | Both cases exist per detector, each proven discriminating by mutation | Positive `nine checks`/`two checks`/`one check`; negative `5 deliverables`/`3 modules`/`5 checkpoints`; mutation-proven in scratch | Both tests exist and pass. I reproduced the mutation result independently: the positive fails on the five-noun set, the negative fails under any-noun. The proof harness is not in the repo | verified |

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

`grep -c "^def _detect_"` on `_self_review_detectors.py` returns **20** at HEAD. The report never
states the re-derived figure. The obligation's purpose (catch a shape that already landed) was met
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

**The widening misses its own corroborating case.** report-01.md:45 offers PR #1167's finding as
the independent corpus corroboration for the widening, diagnosing it as "a `count_prose`-archetype
finding whose noun (`list flags`) sits OUTSIDE the detector's registered noun set". The landed
detector still does not surface it, for **two** reasons, only one of which the report names:

- `flags` is not in the closed six-noun set; and
- even adding `flags?` would not help, because `_COUNT_PROSE` requires the noun to be **immediately
  adjacent** to the number (`\b(?:\d+|{words})\s+(?:{nouns})\b`), and the real prose is
  `the eight list flags` — a modifier intervenes.

Verified by direct regex evaluation: with `operations?|fields?|steps?|rules?|commands?|checks?|flags?`,
`'nine list flags'` → `False`, `'the eight list flags'` → `False`, `'nine flags'` → `True`.

The consequence is live in the tree today. `marketplace/bundles/plan-marshall/skills/automatic-review/SKILL.md:684`
says "the quoting discipline below governs the **eight** list flags only"; `:691` says "all **eight**
list flags declare `nargs='?'`"; `:980` says "All **nine** list flags take an OPTIONAL value"; and
`.../scripts/review_completeness.py:1301` says "the **nine** list flags". The authoritative count is
nine — `grep -n "nargs='?'"` on `review_completeness.py` returns nine hits (`--required-bots`,
`--optional-bots`, `--participated-bots`, `--in-progress-bots`, `--refused-bots`,
`--stale-participation-bots`, `--declined-bots`, `--refused-causes`, `--refusal-size-caps`). So the
finding CodeRabbit raised on #1167 not only went unanswered, it recurred with a larger flag set and
is still stale, in the same document, contradicting its own sibling paragraph — and the detector
this plan widened cannot see it.

**"Derived, not guessed" is overstated.** The plan required (plan.md:112-113):

> ⚠ **Widening must be DERIVED, not guessed.** … **Derive the noun set from the counts that actually
> appear in the corpus, and state whether the resulting set is closed.**

I re-ran the derivation over the detector's real domain (517 contract-source files, the same
population shape the report describes as 510). The report's *characterisation* reproduces: the
number-follower distribution is dominated by `of` (307), `and` (123), `px` (116), `is` (87). That
part is honest and independently confirmed.

But the derivation was used only to justify *not* widening to any noun. The member actually added
came from the plan's own docstring example, and the report says so at report-01.md:76 ("`check` is
added because it is (a) the plan's cited evidence…"). The corpus's own frequent structural
cardinality nouns were never adjudicated in the report: `flags` 21 occurrences, `phase`/`phases` 37,
`states` 27, `columns` 16, `members` 14, against `check`/`checks` at 13. The set is stated closed at
six, which satisfies the second half of the clause; the first half ("derive the noun set from the
counts that actually appear in the corpus") is claimed but not shown, and the un-adjudicated
higher-frequency candidates include the exact noun the report's corroborating finding uses.

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

Discrimination reproduced independently rather than taken on the report's word:

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
cannot match inside `checkpoints`.

Two honest bounds, both already acknowledged by the report:

- The mutation harness (`scratchpad/mutation_proof.py`) is not in the repo, so the proof is not
  reproducible from a clone. The report records this as CodeRabbit F5 and as residue.
- The plan asked for "one **positive** case drawn from the real accepted finding that motivated it"
  (plan.md:118). No accepted finding motivated this widening — the motivating case is the plan's own
  docstring observation, and the corpus corroborator was *unanswered*, not accepted. The positive
  fixture is therefore drawn from the docstring example and a real `phase-1-init/SKILL.md:857`
  instance ("The two checks are ordered: source-origin is primary" — confirmed present at that exact
  line). That is the best available substitute, but the report does not name the substitution.

## Report-claim audit

| # | Claim (report-01.md) | Verdict | Evidence |
|---|---|---|---|
| 1 | Posted answers are readable in this environment; the corpus was built from them, never the internal ledger (:21) | ACCURATE | PR #1170's four threads each carry a posted disposition reply; PR #1167's four carry none. Both surfaces read through the same read path the report names |
| 2 | Counts: 24 PRs, 43 findings, 30 answered, 3 yes, 27 no, 13 unanswered (:25-35) | ACCURATE where checkable | Internally consistent; #1170 and #1167 match exactly. The full 24-PR sweep is not reproducible here |
| 3 | 13 unanswered across #1167 ×4, #1158 ×2, #1198 ×6, #1195 ×1 (:123) | ACCURATE for #1167; PLAUSIBLE for #1198 | #1167 returns exactly four unanswered threads. #1198 returns **three** unanswered inline threads; the remaining three of the claimed six would have to be review-summary or issue-comment findings, which the report says it read but which I did not enumerate |
| 4 | PR #1170 finding #8 is MD040, already covered by markdownlint (:39) | ACCURATE | Thread 4 on #1170 is verbatim an MD040 fenced-code-language finding, dispositioned fixed |
| 5 | PR #1198 finding #23 is a recurring run-report placeholder finding (:41, :43) | ACCURATE | #1198 thread 1 is "Remove the leftover `_pending_` template block" on `doc/plans/truthful-signals/250-.../report-01.md` |
| 6 | The `--max-per-component` anchor's flag and guard shipped together in PR #1153 (:49) | **FALSE** (PR number) | `git log -S` on that file returns one commit, `010ea461` = PR #1039. PR #1153 (`1296ede1`) touches no `manage-lessons` path. The "same PR" structure and the `:232` anchor are correct |
| 7 | PR #1167 finding #3 flagged a stale "six/seven list flags" count whose noun sits outside the set (:45) | ACCURATE, diagnosis INCOMPLETE | The thread body matches. But the binding reason the detector misses it is adjacency, not only the noun set — adding `flags?` still yields no match on `the eight list flags` |
| 8 | The security audit is `tier: full`, `persona-security-expert`, `order: 9` (:58) | ACCURATE | Frontmatter of `finalize-step-security-audit.md` |
| 9 | Both drop paths, with line anchors and the drop-reason string (:60-61) | ACCURATE | Every anchor exact at `bb9ab493`; the reason string matches `_SECURITY_CLASS_DROP_REASON` |
| 10 | `unguarded_boundaries` would not have caught the #1201 traversal (:63) | ACCURATE | The `read_text` sits inside a `try:`; `.exists()` is not a matched boundary |
| 11 | The `SKILL.md`-only file scope was already fixed upstream in PR #1189 (:73) | ACCURATE | `git log -S'_collect_skill_contract_sources'` → `94bcddf2` (#1189); the resolver at `_self_review_detectors.py:276` returns `SKILL.md` plus `standards/*.md` |
| 12 | The docstring claimed `nine checks` while the set lacked `checks` (:75) | ACCURATE | Visible in the landed diff's `-` lines |
| 13 | The widening was derived from a 510-file scan of the detector's domain (:76) | OVERSTATED | The *distribution characterisation* reproduces on 517 files. The added member was not selected from that distribution, and higher-frequency structural candidates (`flags`, `phases`, `states`) are unadjudicated. The scan output is not in the repo |
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
- **Noise bound.** Adding `check` yields 13 additional matches across the 517-file contract-source
  domain (`check` 3, `checks` 10). The list is a review anchor excluded from `counts.total`
  (`ext-point-self-review-surfacing.md:177`), so the added surface cannot inflate the defect count.
- **Non-vacuity.** Neither new test passes both before and after the change: the positive fails
  pre-fix, the negative fails under the named over-widening mutant.

One cosmetic residue: the reflowed docstring at `_self_review_detectors.py:1049-1051` leaves a
one-word line ("the SAME") mid-sentence. Not a defect.

## Completeness review

1. **The corroborating corpus finding remains uncovered** (`_self_review_patterns.py:178` +
   `automatic-review/SKILL.md:684`, `:691`). Detailed under D2. This is the single most consequential
   gap: the plan's only shipped code cannot detect the one real-world instance the report advances
   as its justification, and the stale count that instance named is *still live and self-contradictory*
   in the tree.

2. **Fifth restatement site missed** (`ext-self-review-plan-marshall/SKILL.md:379`). The `## Tests`
   coverage index for this detector does not name either new case.

3. **Registry enumeration not published.** The Claim-labels table's ⛔ re-derivation instruction was
   executed in substance but its result (20 detectors) never appears in the report.

4. **Derivation artifact absent.** `scratchpad/derive_nouns.py` and `scratchpad/mutation_proof.py`
   are both design-time artifacts that did not land, so neither D2's derivation nor D3's mutation
   proof is reproducible from the repository. The report records the second (F5, residue) but not
   the first.

5. **`plan.md` carries its own stale count.** `plan.md:59` opens the Deliverables section with
   "Three." and then enumerates four (D0, D1, D2, D3). The report notices the arithmetic
   (report-01.md:17: "The plan has four deliverables") without flagging the contradiction. In a plan
   whose subject is stale count claims this is worth correcting.

Checked and found complete: production string literals (no argparse `help=` or error template names
the noun set — `Grep -i "cardinality noun"` returns only the four doc sites plus the noun-agnostic
schema row), test fixtures and stubs (the pre-existing `TestDetectCountProse` cases are all
compatible with the widened set — none asserts that a `check` phrase must *not* fire), the N15
schema (noun-agnostic), and the extension-point surfacing standard (noun-agnostic).

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

**Counts by severity:** 0 blockers · 2 major · 4 minor.

Major: the widening does not cover its own corroborating corpus case (and cannot, for an
adjacency reason the report never diagnoses), leaving a live, self-contradictory stale count in
`automatic-review/SKILL.md`; and one report claim attributes a git fact to PR #1153 when the commit
is PR #1039, invalidating the corroborating detail hung on it.

Minor: a fifth consumer restatement (the `## Tests` index) left stale; the mandated registry
re-derivation unreported; the derivation and mutation harnesses absent from the repo so neither D2's
"derived, not guessed" nor D3's mutation proof is reproducible from a clone; and `plan.md`'s own
"Three." deliverables count contradicting its four numbered deliverables.

**Bottom line.** This is a well-evidenced run whose every in-clone anchor survives scrutiny: D1 is
verified anchor-for-anchor, D3's tests exist, pass, and are genuinely discriminating under
independent mutation, and the plan's hardest discipline — routing candidates out rather than
absorbing them because this was the file already open — was followed twice, correctly. The
weakness is concentrated in D2. The plan's back-feed premise produced no code at all from the
accepted-finding corpus; the one code change shipped is the widening the plan itself pre-specified,
selected from the plan's own docstring rather than from the corpus the derivation scanned. That
matters concretely, not just methodologically: the single real count-prose finding the exercise
surfaced uses a noun (`flags`) in a shape (`the eight list flags`) the widened detector still cannot
see, and the drift it named is worse today than when the reviewer raised it — one document now says
"eight list flags" twice and "nine list flags" once, against nine actual flags. The verdict is
verified-with-gaps: nothing claimed is fabricated, but the deliverable that was supposed to close the
loop does not close it.
