# Verification — 100-self-review-surfacing-integrity

**Audited:** `plan.md`, `report-01.md` (the only two files in the plan directory)
**Tree state:** `61a43e5` on `claude/code-intelligence-substrate-analysis-kah884`; the adversarial pass
below re-derived every claim at `9ae90b4` on the same branch, and no cited line moved between the two.
**Overall verdict:** CONFIRMED WITH GAPS

The plan landed as squash commit `94bcddf` — `fix: self-review surfacing integrity — coverage, scope,
termination (D1–D5) (#1189)` — touching 14 files. All five deliverables are present in the tree. D1 and
D2 are fully confirmed, including their negative controls, which this audit re-proved by mutation. D3
and D4 shipped a defensible but narrower mechanism than their literal *Done when* text specifies. D5
shipped as documented prose that the step's own execution path never points at.

## Deliverable verdicts

| # | Deliverable (short) | Report claim | Ground truth | Verdict |
|---|---|---|---|---|
| D1 | Widen the count-prose detector at the resolver | Both detectors resolve one file set through `_collect_skill_contract_sources`; negative control fails pre-fix | `_self_review_detectors.py:1078` iterates the shared resolver; both new tests go red under a mutation restoring the pre-fix behaviour | CONFIRMED |
| D2 | Tie registry membership to check coverage by an invariant | Population-derived test over `in_total` entries, publishes population size, checks 16+17 added, magnitude unchanged | `test_self_review_check_coverage.py`; population re-derived as 17; checks 16/17 at `pre-submission-self-review.md:330,332`; doc mutation drives the test red | CONFIRMED |
| D3 | Every absence claim publishes scope + file count | `scope_statement` emitted unconditionally; rationale rule is workflow guidance (enforcement split declared) | `self_review.py:402` emits it on every success path including a zero-file surface; nothing anywhere *rejects* a scope-less absence claim | PARTIAL |
| D4 | A message aimed at a running plan is reported undeliverable at write time | `--target-plan` refuses a write naming a `running` plan; 4 end-to-end tests | `_orchestrator_inbox.py:936-953`, tests pass — but the guard is opt-in and no *step* doc obliges the one plan-directed stream (`lessons-capture.md:103`) to pass `--target-plan` | PARTIAL |
| D5 | Cap the round loop on convergence, not budget | Doc-only "Round-loop termination" section; converged vs out-of-budget disjoint | `pre-submission-self-review.md:409-427` present and distinct; Step 4 Branch B (`:378-403`, closing at `:407`) never references it and still prescribes correction | PARTIAL |

## Per-deliverable detail

### D1 — widen the detector's file set to match its sibling's

- **Required (plan):** *"both functions resolve the same file set through one path, a test pins their
  agreement, and the planted-count fixture fails before the fix."*
- **Claimed (report):** `_detect_count_prose` now iterates `_collect_skill_contract_sources`; the
  negative control fails against the pre-fix resolver; an agreement test pins the two file sets.
- **Found:**
  - Resolver: `marketplace/bundles/pm-plugin-development/skills/ext-self-review-plan-marshall/scripts/_self_review_detectors.py:276-285` (`_collect_skill_contract_sources`).
  - Consumer: same file `:1078` — `for doc in _collect_skill_contract_sources(skill_dir):`. Docstring
    at `:1049-1058` states the shared-resolver rationale.
  - Negative control: `test/pm-plugin-development/ext-self-review-plan-marshall/test_self_review.py:1646-1666`
    (`test_count_prose_planted_in_standards_doc_is_surfaced`) — the count lives ONLY in
    `standards/rules.md`.
  - Agreement test: same file `:1668-1687`
    (`test_count_prose_file_set_matches_contract_sources_resolver`) — asserts
    `emitted_files == resolver_files`.
  - Pre-fix baseline re-derived independently: `git show 4a1936e:…/_self_review_detectors.py` docstring
    reads *"Detect count-prose in SKILL.md siblings"* and the body does
    `skill_md = skill_dir / 'SKILL.md'` with no `standards/` descent. The plan's premise was true.
- **Checks run:** mutated `:1078` to `for doc in [skill_dir / 'SKILL.md']:` (the pre-fix file set), then
  `uv run python -m pytest …/test_self_review.py -o addopts="" -k count_prose -q` →
  `2 failed, 3 passed` — **both** D1 tests went red, with the agreement failure naming the two missing
  `standards/*.md` paths. File restored from a byte snapshot at
  `/tmp/verify-100-mutsweep/_self_review_detectors.py.orig`; md5 matches and `git status --porcelain`
  is clean for it.
- **Stale consumer of the same value change, not caught by the run.**
  `marketplace/bundles/pm-plugin-development/skills/ext-self-review-plan-marshall/SKILL.md:206` still
  justifies `count_prose`'s exclusion from `total` as *"it anchors a **sibling-SKILL.md** re-check
  rather than flagging an added line"* — the pre-fix file set. Rule 14 at `:256` and the schema
  placeholder at `:178` (`{repo-relative-contract-source-path}`) both state the post-fix file set
  correctly, so the document contradicts itself. A sweep of `marketplace/bundles/` for
  `sibling-SKILL.md|sibling SKILL.md|SKILL.md sibling` returns exactly this one hit. This does not
  touch the *Done when* (the resolver, the agreement test, and the negative control are all satisfied)
  but it is a fourth stale *consumer kind* of the D1 value change, alongside the three the report's
  § "What have we learned" enumerates. See G4.
- **Verdict:** CONFIRMED — every clause of the *Done when* is satisfied and the negative control is
  non-vacuous by direct mutation evidence. One stale doc consumer survives outside the *Done when*
  (G4).

### D2 — tie registry membership to check coverage by an invariant

- **Required (plan):** *"a population-derived test over the registry fails if any counted entry lacks a
  consuming check, and both new checks exist."* Plus the Verification clause: *"D2's population-derived
  test must publish the population size it enumerated."* Plus the arm constraint: ADD the two checks;
  do not drop `in_total`.
- **Claimed (report):** checks 16 (`duplicate_claimable_key`) and 17 (`discard_without_report`) added;
  population-derived test publishing the population size; magnitude unchanged asserted by
  `test_new_checks_do_not_change_total_magnitude`; coverage-gap paragraph closed; "fifteen"→"seventeen"
  reconciled.
- **Found:**
  - Test: `test/pm-plugin-development/ext-self-review-plan-marshall/test_self_review_check_coverage.py`
    — population derived at `:81-83` from `CANDIDATE_LISTS` `in_total`, `assert len(population) > 0` at
    `:109`, size printed at `:110`, coverage assertion at `:117-121`.
  - Checks: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/pre-submission-self-review.md:330`
    (check 16, `duplicate_claimable_keys`) and `:332` (check 17, `discard_without_report`).
  - `keep_markers` consumption made explicit in check 4 at `:296`.
  - Coverage gap closed in the contract:
    `marketplace/bundles/plan-marshall/skills/extension-api/standards/ext-point-self-review-surfacing.md`
    § "Closed coverage gap — every summed key is now examined"; the Consumed-By table gives every one of
    the 22 registry keys a check.
  - Magnitude: `test_self_review_check_coverage.py:166-172`; no `in_total` flag differs between
    `git show 94bcddf:…/_self_review_patterns.py` and HEAD.
- **Checks run:**
  - Re-derived the registry population at HEAD *and* at the landed commit: **22 entries, 17 with
    `in_total: True`** at both. (The report's figure of "23 entries" is wrong — see § Report accuracy.)
  - `uv run python -m pytest …/test_self_review_check_coverage.py -o addopts="" -q -s` → `5 passed`,
    stdout `counted candidate lists (population size): 17`.
  - Mutation: replaced the single occurrence of `` `discard_without_report` entry`` in the workflow doc
    with `DISCARDKEY entry`, re-ran → `2 failed, 3 passed`, the population test failing with
    `counted candidate list(s) with no consuming numbered check … ['discard_without_report']
    (population=17)`. Doc restored from `/tmp/verify-100-mutsweep/pre-submission-self-review.md.orig`;
    md5 matches, `git status` clean for it.
  - Numbered-check block structure re-derived: openers `1.`–`17.` in sequence, contiguous, nothing
    before check 1 in the Step-3 region opening with a digit.
  - Stale count-word sweep across `marketplace/bundles/` for `fifteen|sixteen|seventeen`: the only
    `fifteen` matches are the number-word regex at `_self_review_patterns.py:178` (sic — the regex, not
    a check count) and the number-word map at `_analyze_literal_count.py:195`. No stale check count
    survives. **Scope of this absence claim:** `marketplace/bundles/**` `.md` and `.py` only; `doc/`,
    `.claude/`, `.github/` and `test/` were not swept.
- **Verdict:** CONFIRMED — the invariant is real, population-derived, guarded against an empty
  population, and proven to fire by a real (not synthetic) mutation.

### D3 — every residual/absence claim publishes its searched scope and its file count

- **Required (plan):** *"an absence claim without a scope statement is rejected by the surface, and this
  run's own claims carry theirs."*
- **Claimed (report):** claim shape changed — `surface_scope`/`files_in_scope` pre-existed; added
  `scope_statement` emitted unconditionally; added the workflow rule; **enforcement split** declared —
  the surfacer half is code-enforced, the finding-rationale half is workflow guidance, with no
  rationale-validator, accepted from a CodeRabbit finding.
- **Found:**
  - `marketplace/bundles/pm-plugin-development/skills/ext-self-review-plan-marshall/scripts/self_review.py:106-136`
    (`_format_scope_statement`) and `:402-404` (emitted into the output dict). No early return exists
    between the guards at `:288-330` and the emit at `:394`, so every success path carries it.
  - Workflow rule: `pre-submission-self-review.md:253-259` § "Absence claims state the scope they were
    drawn against", binding both the finding rationale and the clean verdict.
  - Schema surfaces: `ext-point-self-review-surfacing.md:64,79`; `ext-self-review-plan-marshall/SKILL.md:105,202`;
    `pre-submission-self-review.md:146`.
  - Tests: `test_self_review.py:3736` (delta, 1 file), `:3760` (full, 2 files), `:3803-3804` (empty
    surface, 0 files — the "absence carries its scope" case).
  - Report's premise refutation independently re-derived: at `4a1936e`, `self_review.py:330-331` already
    carried `surface_scope` and `files_in_scope`. The plan's asserted absence was indeed false; the
    report labelled this correctly.
- **Checks run:** `git show 4a1936e:…/self_review.py | grep surface_scope|files_in_scope|scope_statement`
  → only the first two present. Full module test run (345 tests across the two affected test dirs) green.
  Exercised `_format_scope_statement` directly for `(delta,1)`, `(delta,0)`, `(full,1)`.
- **Verdict:** PARTIAL —
  1. The literal *Done when* says an absence claim **without** a scope statement is **rejected by the
     surface**. Nothing rejects anything. What shipped is the inverse and weaker construction: the
     surface always *emits* a scope statement, so the *surface* never lacks one — but a downstream
     absence claim that ignores it is not refused by any mechanism. The report declares this split
     openly, and the alternative (an LLM-authored-rationale validator) is genuinely out of keeping with
     how the other seventeen checks are enforced, so this is a defensible substitution rather than a
     failure — but it is a different mechanism than the deliverable specifies, which the plan asked to
     be labelled as such.
  2. The self-binding half ("this run's own claims carry theirs") is honoured in form — the report's
     § "Scope-bearing absence claims" gives scope and count for each — but one of those very claims
     carries a wrong figure (23 vs 22 registry entries), so the section that demonstrates the rule
     violates the accuracy the rule exists to protect.
  3. `_format_scope_statement` produces ungrammatical operator-facing text at exactly the commonest
     delta size (see § Correctness review).

### D4 — a message aimed at a running plan has no reader; make that visible

- **Required (plan):** *"writing a message that names a running plan produces an explicit undeliverable
  report."* Scope guard: do NOT build a mid-run delivery channel.
- **Claimed (report):** optional `--target-plan` on `inbox write`; refusal with
  `undeliverable_to_running_plan` when the epic `status.json` positively reads `running`; the flag never
  reaches the write path; `RUNNING_STATUS` relocated to `_orchestrator_inbox`; 4 end-to-end tests; the
  `--help` write-boundary guard tightened from `--target` to `--target `.
- **Found:**
  - Guard: `marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/_orchestrator_inbox.py:936-953`.
  - Running-set reader: same file `:285-309` (`_running_plan_ids`).
  - Argparse: `marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/orchestrator.py:2558-2570`.
  - Token relocation: `_orchestrator_inbox.py:73` defines `RUNNING_STATUS`; `orchestrator.py:97` imports
    it; `orchestrator.py:140-152` carries only the comment.
  - Docs: `plan-orchestrator/standards/inbox-envelope.md:33-44` (§ Write-side deliverability, four-row
    outcome table); `plan-orchestrator/SKILL.md:192,195`.
  - Tests: `test/plan-marshall/plan-orchestrator/test_inbox_channel_contract.py:299-363` (4 cases) and
    the tightened `--help` guard at `:820-831`.
  - Write-boundary intact: `target_plan` is read at `:936` and used only in the two guard branches; it
    is not passed to `compose_envelope` (`:968`) nor to the path allocator.
- **Checks run:** `uv run python -m pytest …/test_inbox_channel_contract.py -o addopts="" -q -k "TargetPlan or help"`
  → `4 passed`. Whole file plus the ext-self-review dir → `345 passed`.
  Content sweep for `--target-plan` / `target_plan` across `marketplace/bundles/` and `test/`: the flag
  appears **only** in the two orchestrator scripts, the two orchestrator docs, and the test file. Every
  `inbox write` command block in the bundles was re-enumerated with its message **kind**, since the kind
  is what decides whether a target flag is meaningful there:
  `plan-orchestrator/SKILL.md:190-192` (the canonical synopsis — it **does** carry
  `[--target-plan TARGET_PLAN]`, so the generic form advertises the flag),
  `phase-6-finalize/standards/emit-landing.md:204` (`--kind landing`, self-addressed —
  `landing-payload-spec.md:82` makes `plan_id` == `sender_id` a required key),
  `phase-6-finalize/standards/finalize-step-preference-emitter.md:220` (`--kind candidate-lesson`,
  own-run owed hint), `plan-retrospective/SKILL.md:338` (`--kind candidate-lesson`, own-run proposal),
  and `phase-6-finalize/workflow/lessons-capture.md:103` (`--kind {kind}`, resolved by `:82` as
  *"Every candidate lesson and every finding rides as `candidate-lesson`"*). Only the last can carry
  content aimed at a plan other than the sender. No documented invocation writes `--kind finding` at all.
  Nothing else supplies the value either: `orchestrator.py:2570-2582` declares it `required=False,
  default=None` with no fallback, and `cmd_inbox_write` has no programmatic caller outside the argparse
  wiring and the tests.
- **Verdict:** PARTIAL — the mechanism exists, is correct on its own terms, is well tested, stays inside
  the scope guard, and the contract is honest about its restriction (`inbox-envelope.md:35` states
  *"The guard fires only when `--target-plan` is supplied"*). What is missing is an obligation: the one
  documented stream that can carry a message aimed at another plan (`lessons-capture.md:103`) never
  tells its writer to name the target, so the arm-C incident shape still queues silently. "Writing a
  message that names a running plan produces an explicit undeliverable report" is therefore true only of
  callers who already knew the message was aimed at a plan and said so. This is an incomplete
  deliverable, not wrong behaviour. See G1.

### D5 — the doc-claim half self-seeds; cap on convergence, not on budget

- **Required (plan):** *"the termination criterion distinguishes converged from out of budget, and a
  round whose findings are all newly-authored-prose-about-this-plan's-own-edits is reported as
  self-seeding rather than counted as an ordinary non-clean round."* Anti-goal: NOT a round-count
  reduction.
- **Claimed (report):** doc-only change adding a "Round-loop termination" section; self-seeding defined,
  resolution by deletion prescribed, converged vs out-of-budget distinguished; recorded via the existing
  `failed` outcome plus `manage-logging decision --level WARNING`; verified by a cold read.
- **Found:** `marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/pre-submission-self-review.md:409-427`
  — § "Round-loop termination: converged, self-seeding, and out of budget". The two-halves framing at
  `:413-414`; the self-seeding definition with the delta-anchor-is-not-authorship caveat at `:416`
  (CodeRabbit finding 3's fix); deletion-not-correction at `:418`; the recording mechanism at `:420`
  (CodeRabbit finding 4's fix); the converged/out-of-budget contrast at `:422-425`; the explicit
  non-reduction statement at `:427`.
- **Checks run:** read the section cold. The two closes are pinned to disjoint observable states — a
  full-surface clean pass (Step 4 Branch A) versus a recorded warning deviation — so the report's cold-read
  claim holds on my own independent read. Grepped the whole doc and the ext-point for `self-seed` /
  `out of budget`: **every** occurrence is inside `:409-427`. Nothing in Steps 1–4 mentions either.
- **Verdict:** PARTIAL — the prose satisfies the *Done when* literally, but it is unreachable from the
  step's own execution path:
  1. Step 4 Branch B (`:378-403`), the only place a non-clean round is processed, records
     `--outcome failed` and says nothing about classifying the round or emitting the WARNING that
     `:420` requires. There is no forward reference from Step 4 to `:409`. An executor working the
     numbered steps in order never learns the classification exists. See G2.
  2. `:407` — the paragraph that *does* tell the operator what to do with findings — prescribes
     *"amend the diff: rename, tighten regex, **rewrite wording**, delete duplicate section, fix
     contract drift"*, i.e. the correct-and-re-run cycle that `:418` identifies as the re-seeding
     mechanism, with no carve-out. This is a same-document narrowing contradiction of exactly the class
     check 8 detects. See G3.

## Correctness review

I read `_self_review_detectors.py:276-285` and `:1040-1092`, `self_review.py:106-136` and `:270-413`,
`_orchestrator_inbox.py:285-309` and `:895-975`, `orchestrator.py:2555-2571`, and the whole of
`test_self_review_check_coverage.py`. Defects found:

1. **Singular/plural defect in the quotable scope statement** —
   `marketplace/bundles/pm-plugin-development/skills/ext-self-review-plan-marshall/scripts/self_review.py:126-133`.
   The `noun` is computed once from `files_in_scope` and then reused for a *plural* demonstrative later
   in the same sentence. Exercised directly:
   `_format_scope_statement('delta', 1, 'abc123')` returns
   `"searched delta scope: 1 file changed since abc123 — a scoped round, so a clean result covers only
   these file, NOT the full plan surface"`. A one-file delta is the commonest loop-back round, and
   `pre-submission-self-review.md:257` instructs reviewers to **quote** this string, so the defect
   propagates into finding rationales. `files_in_scope == 0` and `>= 2` are fine. The test at
   `test_self_review.py:3736` asserts only `.startswith('searched delta scope: 1 file')`, so it passes
   over the defect. See G5.

2. **Documented fail-open in the deliverability guard** — `_orchestrator_inbox.py:299-309`. A missing,
   unreadable or malformed `status.json`, or one with no `plans[]` array, yields an empty set, so
   `target_plan in _running_plan_ids(root)` is false and the undeliverable write proceeds. This is
   deliberate and documented (`:293-297` in code, `inbox-envelope.md:41` in the contract), and refusing
   on an unverifiable state would be worse. It is nonetheless a branch where the guard cannot fire on a
   real running plan whose ledger happens to be corrupt. Recorded as G9 at low severity because it is
   declared, not hidden.

3. **Latent weakening of the D2 discriminator** — `test_self_review_check_coverage.py:65-78`
   (`_numbered_check_block`). The block is `region[first_numbered_opener:]`, which is exactly the
   numbered checks **only while the numbered checks are the last thing in the Step-3 region**. That
   holds today (verified: openers `1.`–`17.`, region ends at `### Dispatched-envelope output`). A future
   `####` subsection appended after check 17, or a numbered list inserted into the region's preamble,
   silently widens the covered text and the "explanatory prose does not count as a check" narrowing
   quietly stops holding — with no test failing. See G10.

No fail-open branch, off-by-one, unguarded `None`, order dependency, or stale-surface read was found in
the D1 or D2 production paths. `_detect_count_prose`'s `doc.relative_to(project_dir)` at `:1083` cannot
raise, because `_find_skill_dir` (`:263-273`) bounds the walk inside `project_dir`.

## Test adequacy

| Deliverable | Covering tests | Non-vacuity evidence |
|---|---|---|
| D1 | `test_self_review.py:1646` (negative control), `:1668` (agreement) | **Proven by mutation.** Restoring the pre-fix `SKILL.md`-only file set turns both red; 3 sibling `count_prose` tests stay green, so the redness is attributable to the resolver, not the fixture. |
| D2 | `test_self_review_check_coverage.py` (5 cases) | **Proven by mutation** of the real workflow doc (removing check 17's backticked key) → the population test and `test_both_new_checks_exist` both go red. The two synthetic predicate controls (`:123`, `:135`) additionally pin the "prose is not a check" narrowing. |
| D3 | `test_self_review.py:3724`, `:3746`, `:3781` (delta/full/empty scope statements); `:3894` (distinct from `structural_limit`) | Non-vacuous — the empty-surface case asserts a scope statement is present when the candidate lists are all empty, which is the invariant's whole point. But every assertion is `startswith`, so the tail of the sentence — where the grammar defect lives — is untested. |
| D4 | `test_inbox_channel_contract.py:309,326,340,354` | Non-vacuous and symmetric: running→refused **and** the file is not written; landed→queued; untargeted→unaffected; malformed→rejected. Both directions of the bidirectional requirement are covered. |
| D5 | None (doc-only) | A test is not warranted for prose. But nothing pins the Step 4 → termination-section cross-reference either, which is why G2 could ship. |

One weakness in D2's test: the population size is emitted with a bare `print` at
`test_self_review_check_coverage.py:110`, which pytest captures and discards on a passing run. The test
requests the `capsys` fixture at `:103` and never uses it. The plan's Verification section requires the
test to *publish* the population it enumerated; on a green CI run it publishes nothing observable. See G6.

## Report accuracy

Every factual claim in `report-01.md` was checked against the tree. All but one held.

- **FALSE — the registry entry count.** § "Scope-bearing absence claims", first bullet:
  > "Searched scope: the `CANDIDATE_LISTS` registry in `_self_review_patterns.py` (1 file, 23 entries,
  > 17 `in_total`)"

  The registry has **22** entries, not 23 — re-derived at HEAD (module import, `len(CANDIDATE_LISTS)`)
  and at the landed commit `94bcddf` (AST over `git show`), both 22 entries / 17 `in_total`. The `17` is
  correct; the `23` is not; a naive `grep -c 'CandidateList('` returns 23 because the 23rd match is the
  `class CandidateList(NamedTuple):` declaration at `_self_review_patterns.py:502`. The PR body for the
  same claim says *"the `CANDIDATE_LISTS` registry (1 file, 17 `in_total` entries)"* and states no total
  — read directly from PR #1189 via the GitHub API in the adversarial pass — so this error is confined
  to the run report. It is also the one claim in the section whose whole purpose is to demonstrate D3's
  scope-and-count discipline. See G7.
- **True but now line-shifted (not a defect).** "`pre-submission-self-review.md:122` … line 122 now
  includes `scope_statement`" — that enumeration is now at `:146` after later plans inserted content,
  and it does include `scope_statement`. The report's further claim that line 122 was the *sole*
  omission holds: every scope-echo enumeration in the tree (`ext-point:64`, `ext-point:79`,
  `workflow:146`, `workflow:255`, `SKILL.md:105`, `SKILL.md:202`) now names `scope_statement`.
- **True.** "'fifteen'→'seventeen' reconciled across the workflow doc, the ext-point contract, and the
  implementor SKILL.md" — re-derived; no check-count `fifteen` survives in `marketplace/bundles/`.
- **True.** The pre-fix baseline bullets (§ "Claim re-verification — BASELINE, at HEAD `4a1936e`"). I
  re-derived both load-bearing ones from `git show 4a1936e:…`: the detector opened only `SKILL.md`, and
  `surface_scope`/`files_in_scope` already existed. The section is correctly labelled as a pre-fix
  baseline and not as current state.
- **True.** "no `in_total` flag changed" — byte-compared the registry at `94bcddf` against HEAD.
- **True.** "No undeclared collateral change; the `RUNNING_STATUS` move is the declared D4 shared-token
  relocation" — the landed commit touches 14 files, all named in the plan's Expected surface or the
  report; the `orchestrator.py` diff is exactly the import, the comment rewrite, and the `--target-plan`
  argument.
- **UNVERIFIABLE from this clone (not disputed).** The CI figures (`19241 passed, 14 skipped`,
  `mypy 395/717 files`, the 10m59s runtime), the per-commit gate results, the CodeRabbit and
  `cuioss-review-bot` / `sourcery-ai` participation table, and the "93 passed" targeted re-verification.
  These are records of a past CI session; the brief forbids running `./pw verify`. The wall-clock
  estimate *is* now corroborated: PR #1189's API record gives `created_at 2026-08-12T18:21:36Z` and
  `merged_at 2026-08-12T19:36:08Z` — 1h14m, inside the report's "roughly 1–1.5 hours" — along with
  `changed_files: 14`, `additions: 851`, `deletions: 58`, matching the squash stat exactly. The
  individual commit SHAs
  (`53d49f3`, `5ae9848`, `cb577b2`, `89ddcbf`, `0c69f8b`, `2e68683`, `e08f23a`) are all absent from this
  clone, which is the expected consequence of the squash merge the report itself declares — not a
  discrepancy.

## Declared residue — current status

| Residue item (from report) | Still open? | Evidence |
|---|---|---|
| **Landing** — auto-merge armed on PR #1189; squash SHA to be read from the merge event | **CLOSED** | `94bcddf` `fix: self-review surfacing integrity — coverage, scope, termination (D1–D5) (#1189)` is an ancestor of HEAD; all 14 files present in the tree. |
| **`sourcery-ai` review did not run** (weekly rate limit); disclosed as a 2-of-3 coverage shortfall, "no action owed" | **MOOT** | An external quota on a merged PR. Nothing in the tree records or owes anything. |
| **Contract-change proposal** — beyond-diff sweep by *consumer kind*, to ship as a separate `chore/` PR if the operator accepts | **CLOSED** | Accepted and landed as `be70970` `chore(cloud-plan-lane): sweep beyond-diff consumers by kind in Step 6 (#1192)`, touching only `.claude/skills/cloud-plan-lane/SKILL.md` (+10/-1). The instruction is live at `.claude/skills/cloud-plan-lane/SKILL.md:609,616,637,680`, and the evidence it cites is this run's own three-consumer-kind observation. |

## Out-of-scope and collateral

All four exclusions were respected.

- **Semantically-wrong worked examples** — not built. The `worked_example_pairs` detector and check 15
  pre-date this plan (`_self_review_patterns.py` is not in the landed commit's file list) and are
  untouched by it.
- **Reducing self-review rounds** — not done; `pre-submission-self-review.md:427` states the anti-goal
  explicitly and no round cap was introduced.
- **A mid-run delivery channel** — not built. `target_plan` is read at `_orchestrator_inbox.py:936` and
  reaches only the two guard branches; it never reaches `compose_envelope` or the path allocator.
- **Retiring a lesson** — no lessons file appears in the landed commit's 14-file stat.

No collateral change was found. The `structural_limit` field and the workflow doc's §§ at `:261-274`,
which sit adjacent to D3's work and might be mistaken for it, were added later by
`622f448 (#1239)` — confirmed with `git log -S"structural_limit"`.

## Method and coverage

**What I did.** Read `plan.md` and `report-01.md` in full, then located each deliverable's shipped
artefact in the tree by content search and direct read, re-derived every count I state, and drove two
real mutations to prove the negative controls. Ran the two affected test modules in full
(`345 passed in 32s`). Re-derived both pre-fix baselines from `git show 4a1936e:…` rather than trusting
the report's account of them. Inspected the landed squash commit `94bcddf` for undeclared collateral.
Traced each residue item to a landed commit.

**Mutation protocol.** Byte snapshots were taken with `cp` into `/tmp/verify-100-mutsweep/` *before*
each edit and restored with `cp` from that snapshot afterwards — never `git checkout`/`restore`/`stash`.
Post-restore `md5sum` matches the snapshot for both files and `git status --porcelain` lists neither.
(The working tree carries unrelated modifications from concurrent sessions; none are mine.)

**What I could not check.** Everything that lives in the CI record rather than the tree: the
`./pw verify` totals, per-commit quality gates, the reviewer participation table, and the CodeRabbit
finding dispositions as posted. These are marked UNVERIFIABLE above rather than assumed to pass. The
brief forbids the full verify run, and the individual branch commits no longer exist post-squash. The PR
*body* and its timestamps are not in the tree either, but the adversarial pass read them from PR #1189
through the GitHub API rather than leaving them asserted — see § Report accuracy. The D5 "cold read" verification requirement I discharged myself by reading the
termination section without first reading the report's account of it; I reached the same reading the
report claims (the two closes are disjoint and non-collapsible), and the gaps I file against D5 are
about *reachability from Step 4*, not about the distinction itself.

**Absence claims in this document, with their scope.** The claim that no bundle call site passes
`--target-plan` was drawn from a `grep` for `target-plan|target_plan` across `marketplace/bundles/` and
`test/` (all file types, `__pycache__` excluded) cross-checked against an enumeration of every literal
`inbox write` occurrence in `marketplace/bundles/**/*.md` — 5 call sites, none passing the flag. The
claim that no stale check-count `fifteen` survives was drawn from `marketplace/bundles/**` only. The
claim that `self-seeding` appears nowhere outside `:409-427` was drawn from the three files that could
plausibly carry it (the workflow doc, `phase-6-finalize/SKILL.md`, the ext-point contract). Each grep
pattern was confirmed to return hits somewhere it was known to exist before any zero result was
believed.

## Adversarial review

Independent review of this document and `gaps.md`. Attacks run: A1 false positives, A2 false
negatives, A3 vacuous evidence, A4 counts and quotes, A5 actionability, A6 severity/topic,
A7 coverage, A8 internal consistency.

Re-derived at `9ae90b4` on the same branch. Nothing in this document or in `gaps.md` was accepted on
the original auditor's word: every `path:line` was opened, every count recomputed, both claimed
mutations re-run, and the PR record fetched from the GitHub API.

| # | Attack | What was found | Correction applied |
|---|---|---|---|
| A1 | False positives | Every gap's citation was opened at `path:line`. **All ten gaps describe real conditions.** Verified in place: the `sibling-SKILL.md` clause at `ext-self-review-plan-marshall/SKILL.md:206` (G4, sole hit in `marketplace/bundles/`); `noun` reused for the plural demonstrative at `self_review.py:126-133` (G5); the unused `capsys` at `test_self_review_check_coverage.py:103` and the bare `print` at `:110` (G6); the `23`-vs-`22` registry figure at `report-01.md:127` (G7); the unconditional emit at `self_review.py:402` with no rejection path (G8); the empty-set fail-open at `_orchestrator_inbox.py:299-309` (G9); the unpinned block extraction at `:55`/`:65-78` (G10); `:407` vs `:418` in `pre-submission-self-review.md` (G3); Step 4 Branch B carrying no reference to `:409` (G2). No citation had drifted. | None needed for existence; three citations sharpened — G8's site (§ Output Schema `:79`, not "near `:64`" in § Post-Conditions), G10's attribution (the `#:` comment at `:49-51`, not `_numbered_check_block`'s docstring) and its preamble range (`:233-281`, not `:235-280`). |
| A2 | False negatives | The two CONFIRMED verdicts (D1, D2) were re-derived from the shipped code, not from the audit's reasoning, and both hold: `_detect_count_prose:1078` calls the shared `_collect_skill_contract_sources:276-285`, which is also what the rule-6 detector calls at `:440`; the D2 population is genuinely derived from the registry (`:81-83`), guarded `> 0` (`:109`), and asserted per key (`:117-121`). One item the audit missed entirely — the stale `sibling-SKILL.md` rationale at `SKILL.md:206`, filed as G4 in `gaps.md` but traceable to nothing in this document (an A8 defect too). Separately, the **G1 attack the brief singled out**: the call-site enumeration was redone from scratch (`grep` for `inbox write` across the whole repo, then each block opened). Five blocks exist, and the audit's characterisation was materially wrong in two ways — the canonical synopsis at `plan-orchestrator/SKILL.md:190-192` **does** carry `[--target-plan TARGET_PLAN]`, and of the four operational blocks three are self-addressed by message kind (`landing`; two own-run `candidate-lesson`s), so their omission of the flag is correct rather than a defect. Only `lessons-capture.md:103` — `--kind {kind}`, resolved by `:82` as *"Every candidate lesson and every finding rides as `candidate-lesson`"* — can carry plan-directed content. No documented invocation writes `--kind finding` at all, so the audit's preferred remedy targeted a path with zero callers. Confirmed no other mechanism supplies the argument: `orchestrator.py:2570-2582` is `required=False, default=None` with no env/config fallback, and `cmd_inbox_write` has no programmatic caller. | D1's section gains the G4 finding (verdict stays CONFIRMED — it is outside the *Done when*). D4's § Checks run and § Verdict rewritten to enumerate call sites **by kind** and to name `lessons-capture.md:103` as the one site that owes the obligation; the D4 table row follows. G1 rewritten end to end. |
| A3 | Vacuous evidence | Both claimed mutation sweeps were **re-run**, not re-read. D1: `_self_review_detectors.py:1078` → `for doc in [skill_dir / 'SKILL.md']:`, then `pytest …/test_self_review.py -k count_prose` → `2 failed, 3 passed`, the agreement test naming the two missing `standards/*.md` paths. D2: the single `` `discard_without_report` `` occurrence in the workflow doc (`:332`) → `DISCARDKEY`, then `pytest …/test_self_review_check_coverage.py` → `2 failed, 3 passed`. Both reproduce the audit's readings exactly. G6's own claim re-tested: `-s` prints `counted candidate lists (population size): 17`, plain `-q` prints nothing — the publication really is discarded on a green run. G10's structural premise re-derived from the live document: ordinals `[1 … 17]`, contiguous, zero headings inside the extracted block. | None — every "verified" in the document rests on something that came back different under mutation. Snapshot/restore protocol followed (`cp` to a scratch dir, `cp` back, md5 match, `git status --porcelain` clean for both files); no `git checkout`/`restore`/`stash` was used. |
| A4 | Counts and quotes | Registry re-derived **twice by independent methods** — module import at HEAD and AST over `git show 94bcddf:…` — both **22 entries / 17 `in_total`**, confirming G7 and D2. Located the origin of the report's `23`: `grep -c 'CandidateList('` returns 23 because the class declaration at `:502` matches. `_format_scope_statement` exercised directly: `(delta,1)` returns `…covers only these file, NOT the full plan surface` — G5's quote is byte-exact. G2's grep-line list `{409,416,418,420,422,425,427}` for `self-seed\|out of budget` reproduced exactly. `:407` and `:418` quoted verbatim. Landed commit re-stat'd: 14 files, `_self_review_patterns.py` absent from it. The one number stated but not measured was the PR body's wording, quoted in § Report accuracy while § Method declared PR surfaces unreachable. | PR #1189 fetched from the GitHub API: body confirms *"(1 file, 17 `in_total` entries)"* with no total; `changed_files 14 / +851 / -58` and `created_at 18:21:36Z → merged_at 19:36:08Z` (1h14m) corroborate the report's stat and wall-clock. § Report accuracy and § Method corrected so the document no longer both quotes and disclaims the PR. G7's evidence gains the two derivation methods and the `:502` explanation. |
| A5 | Actionability | Nine of ten entries were executable as written. G1 was not: its *Done when* asked for a refusal "issued without any new flag by a caller following the documented invocation at `emit-landing.md:204`" — a `--kind landing` write whose payload names the sender's own plan, which is `running` at finalize time (`TERMINAL_PLAN_STATUSES` at `orchestrator.py:140` shows the row leaves `running` only on a later orchestrator act). Implemented literally, its arm (b) would refuse **every** landing write. Its arm (a) targeted `--kind finding`, which no documented block writes. | G1's Action and *Done when* replaced with a site-specific, checkable obligation at `lessons-capture.md:103` plus `inbox-envelope.md` § Write-side deliverability, and an explicit warning that a payload-side detector must exclude the sender's own plan id. Effort re-estimated M → S. |
| A6 | Severity and topic | G1's **high** does not survive the calibration: the guard fires (four passing tests drive it), the contract states the opt-in restriction verbatim at `inbox-envelope.md:35`, and the canonical invocation advertises the flag — nothing is misreported and no guard is structurally unreachable. That is "an incomplete deliverable" → medium. Topics: G2/G3 own `phase-6-finalize/workflow/pre-submission-self-review.md`, a step's execution contract rather than narrative documentation; G8 owns `extension-api/standards/ext-point-self-review-surfacing.md`, the same class of bundle contract doc as G4. G5–G7, G9, G10 checked and correct. | G1 high → **medium**; the header tally now reads five medium / five low. G2, G3 `documentation-surface` → `dispatch/finalize`; G8 `documentation-surface` → `bundle-docs`. G7 stays `documentation-surface` (it edits the run report, not a bundle). |
| A7 | Coverage | All five deliverables carry a detail section with the *Done when* quoted; all four out-of-scope exclusions are checked; report accuracy and the three-item residue list are covered; test adequacy is tabulated per deliverable. The plan's § Verification clauses are each discharged (negative controls, the population-publication requirement → G6, the D5 cold read, the self-binding D3 check) or explicitly marked unverifiable (`./pw verify`). No deliverable is silently unmentioned. | None. |
| A8 | Internal consistency | Overall verdict follows from the rows (2 CONFIRMED / 3 PARTIAL → CONFIRMED WITH GAPS). Every gap traces to a finding here **except G4**, which appeared nowhere in this document. Two smaller inconsistencies: the D5 table row cited Step 4 Branch B as `:378-407` while the detail cited `:378-403` (the block body ends at `:403`; `:407` is the closing operator sentence); and § Report accuracy quoted the PR body while § Method declared PR surfaces out of reach. | G4's finding added to the D1 section. Table row harmonised to `:378-403, closing at :407`. The PR-body inconsistency resolved by actually fetching the PR (see A4). |

**Residual doubt:** Two things a further round would most likely find. First, the workflow doc carries
three independently-maintained "seventeen"s — the § Step 3 heading, the count of numbered-check openers,
and `len(_counted_lists())` — and only the third is pinned to anything; their agreement today is partly
coincidence, since several numbered checks consume non-`in_total` lists (check 6 → `contract_sources`,
check 11 → `count_prose`) while several `in_total` keys share a check. A drift there is caught only by
`count_prose` + check 11 firing during a future self-review round, which is a soft mechanism. Not filed
as a gap because no contract requires the three numbers to be equal, so there is nothing to assert
against. Second, this pass verified D3's self-binding against the run report and the PR body, and found
one clause in the PR body (*"the flag is a plan id that never reaches the write path"*) that is an
absence claim without a scope statement; it is left unfiled because the plan's rule targets residual and
absence claims about the searched surface, not every sentence of a PR narrative, and the write-boundary
claim was independently verified here.

**Verdict on the audit:** SOUND AFTER CORRECTION — every gap it filed is real and both its mutation
sweeps reproduce, but its headline HIGH mis-severitied an incomplete deliverable as a dead guard, its
call-site enumeration mischaracterised four of five write sites by ignoring message kind, its prescribed
G1 remedy would have refused every landing write, and one gap (G4) traced to nothing in the verification
document.
