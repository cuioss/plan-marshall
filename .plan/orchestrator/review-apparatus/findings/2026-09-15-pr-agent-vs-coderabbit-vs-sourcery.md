# Corpus analysis: pr-agent vs CodeRabbit vs Sourcery, since 2026-08-30

**Window: `2026-08-30T20:16:39Z` → `2026-09-15T09:50:16Z`** (15.6 days). The lower bound is the stamp from the previous pass ([`2026-08-30-pr-agent-vs-coderabbit-multirepo.md`](2026-08-30-pr-agent-vs-coderabbit-multirepo.md)). The upper bound was taken with `date -u` just before enumeration. This was a read-only pass: nothing was commented, labelled or pushed in any repository.

⭐ **STAMP FOR THE NEXT PASS: use `2026-09-15T09:50:16Z` as the lower bound.**

## Instrument and validation

| Purpose | Tool | Why |
|---|---|---|
| PR enumeration (date and label filters) | `gh pr list --repo cuioss/{r} --search "updated:>=2026-08-30T20:16:39Z" --state all --limit 1000` | `ci pr list --help` offers only `--head`, `--state` and `--limit`. It cannot filter by date or label. |
| Per-PR bodies | GET-only `gh api --paginate --slurp`: `issues/{n}/comments`, `pulls/{n}/comments`, `pulls/{n}/reviews`, `pulls/{n}/commits` | Raw JSON is dumped per PR, so classification can be re-run |
| Trigger checks and pr-agent reviewed SHAs | `gh api actions/workflows/pr-agent.yml/runs?created=…` and `actions/runs?created=…`, both unfiltered by branch | Follows review-practice § 1 |
| Thread resolution state (adjudication) | Sanctioned `ci pr comments --pr-number N` on 21 plan-marshall PRs | Gives `resolved` per inline thread |
| Discovering other repositories | `gh search prs --owner cuioss --updated ">=…"` (765 results, under the 1000 cap) | |

The three repository names were confirmed with `gh repo view`, and all resolve: `cuioss/pr-agent-settings`, `cuioss/cuioss-organization` and the six corpus repositories.

**Validation.**

- **(a) CodeRabbit presence across all three endpoints.** It posted 501 issue_comments, 868 reviews and 1320 review_comments across all dumps. "Reviewed" means at least one review, a root inline comment, or a walkthrough summary. Presence of any artefact is reported separately so the figures compare with the previous pass.
- **(b) pr-agent posts in place.** The 156 guides sit on 156 PRs, and no PR has two guides, which confirms in-place editing. 70 guides carry `Review updated until commit`. Body length splits cleanly: 82 at 242 bytes (canned), 70 at 362–367 bytes (canned plus the commit marker; the length varies with the repository name), and 4 at 1227–2423 bytes (substantive). The canned text is corroborated by length independently of the parser.
  - **New this pass:** `cuioss-review-bot[bot]` also posted **10 inline review comments**, each a commitable `/improve` `**Suggestion:**`. The pipeline must read them as pr-agent output.
- **(c) Hand spot-checks.**
  - plan-marshall#1393: `ci pr comments` and `gh api` agree exactly, 16 = 16 per kind and author.
  - API-Sheriff#255, with `--project-dir`: **`ci` returned 236 against `gh`'s 237.** The missing record is review `5123206655`, the 101st of 109 reviews. `github_ops.REVIEW_THREADS_QUERY` uses `reviews(first: 100)`, `reviewThreads(first: 100)`, `comments(first: 100)` and `comments(first: 10)` per thread, with no pagination and no truncation flag. The output was `status: success`. It is the same data path `fetch_pr_comments_data` feeds into `fetch_findings`.
  - In this instance the dropped body held only metadata; its 4 inline comments survive through `reviewThreads`. Only 1 of 351 dumped PRs exceeds any of the caps.
  - ⇒ The loss is **silent, and latent in this corpus**.
- **(d) Refusals are never scored as silence.**
  - CodeRabbit: rate/limit notices, "Reviews paused" and "Too many files" all count as refusals. 74 refusals sit **inside the summary comment**, and 71 of those arrived as in-place edits.
  - Sourcery: "used your own review budget" is a quota refusal (it expires). "larger than the review limit" and "unable to review… exceeding" are size refusals (they never expire).

**Classifier corrections made mid-analysis, and how they moved the numbers:**

1. **CodeRabbit refusal detection was loose at first.** Free-text matching counted a *conversational* CodeRabbit reply quoting "Review rate limited" (cui-http#179, comment 5481669579) as a refusal. It also counted "Review skipped: No new commits" (5 comments) and "Review failed: The pull request is closed" (1) as refusals. After switching to structural markers, rate refusals went from 179 to 178 comments, and the skipped-other and failed buckets went from 6 to 0. No coverage table below was produced before this correction.
2. **Four-outcome scoring, first draft.** It counted any substantive pr-agent guide as non-deficit. The rule is now a count comparison against the baseline. Clean-corroborated moved from 12 to 8, and deficit from 123 to 127 (4 of which are non-empty deficits).
3. **Adjudication regex, escape bug.** A double backslash disabled `\d`, `\s` and `\b`. It was caught on output and fixed before any figure was used.
4. **Adjudication, "Already fixed on this branch".** This was first classified as a rejection (found while reading plan-marshall#1399). Moving it to accepted changed CodeRabbit accepted from 277 to 278, and pr-agent from 5 accepted / 2 rejected to 6 accepted / 1 rejected.

## Population

| Figure | Value |
|---|---:|
| Repositories | 6 |
| Candidate PRs (updated in window) | 351 |
| Excluded: `skip-bot-review` label | **164** |
| Collected | 187 |
| Excluded: opened before the lower bound (API-Sheriff #234–236, plan-marshall #1368, #1370, #1371) | 6 |
| **Population: PRs opened in window** | **181** |

Per repository: plan-marshall 99, cui-http 29, TokenSheriff 29, API-Sheriff 24. **cui-test-mockwebserver-junit5 and cui-test-juli-logger contribute 0**: all 19 and 17 of their candidates carry the skip label.

**Close-and-reopen duplicates.** 7 groups add 10 extra PRs to the population (same title and diff size). plan-marshall #1411–#1415 are five copies. Distinct diffs: 171.

### Bypass: the `skip-bot-review` count is itself a signal

| Repository | Skip-labelled | App-authored (release-bot, dependabot) | Human-authored | Human-authored, ≥100 changed lines, merged |
|---|---:|---:|---:|---|
| plan-marshall | 24 | 6 | 18 | 7: #1377 (feat, +838/−15), #1401, #1457 (+25284/−34576, ruff), #1463, #1464, **#1491** (+408/−36), #1492 |
| cui-http | 31 | 15 | 16 | 1: #207 (#205 at +4666 was closed) |
| TokenSheriff | 35 | 13 | 22 | 5: #695, #706, #728, #733, #740 |
| API-Sheriff | 38 | 16 | 22 | 4: #242 (180 files), #250, #290, #291 |
| cui-test-mockwebserver-junit5 | 19 | 15 | 4 | 0 |
| cui-test-juli-logger | 17 | 15 | 2 | 0 |
| **Total** | **164** | **80** | **84** | **17** |

- Label timing was checked on 8 plan-marshall PRs: #1377, #1401, #1457, #1463, #1464, #1491, #1492 and #1438 (the last has no label). On all seven labelled PRs the label was **applied 1–3 s after creation**, so the bypass is chosen at open.
- That race still let pr-agent post a canned guide on **11 skip-labelled PRs**, because the event payload predated the label.
- The previous pass excluded 63 but did not split them. **84 human-authored bypasses in 15.6 days** is the figure to watch; 17 of them are merged diffs of at least 100 lines.

### Not included (other cuioss repos with PRs opened in the window, not skip-labelled; counts from dumps)

| Repository | PRs | App-authored | Any bot review | CodeRabbit reviewed (self-declared actionable) | Sourcery reviewed | pr-agent guide |
|---|---:|---:|---:|---:|---:|---:|
| nifi-extensions | 29 | 21 | 8 | 8 (17) | 2 | 0 |
| cuioss-parent-pom | 26 | 26 | 0 | 0 | 0 | 0 |
| cuioss-organization | 9 | 3 | 5 | 4 (4) | 4 | 0 |
| playwright-test-artifacts | 7 | 7 | 0 | 0 | 0 | 0 |
| cui-reference-documentation | 4 | 4 | 0 | 0 | 0 | 0 |
| cui-jsf-components | 3 | 3 | 0 | 0 | 0 | 0 |
| cui-portal-core | 2 | 2 | 0 | 0 | 0 | 0 |
| cui-open-rewrite | 1 | 0 | 1 | 1 (1) | 1 | 0 |
| pr-agent-settings | 1 (#64) | 0 | 1 | 1 (0) | 1 | 0 |
| cui-test-value-objects | 1 | 1 | 0 | 0 | 0 | 0 |

- **nifi-extensions and cuioss-organization carry substantive bot-reviewed PRs** (8 and 5) and are excluded only to keep comparability with the previous pass.
- None of these 83 PRs has a pr-agent guide. Whether each repository has a pr-agent caller was **not checked**, so no coverage-defect claim is made.

**Bot identities, derived from the corpus.** `cuioss-review-bot[bot]` is pr-agent, `coderabbitai[bot]` is CodeRabbit, `sourcery-ai[bot]` is Sourcery. Other bot authors seen, none of them reviewers:

- `cla-assistant[bot]`
- `github-advanced-security[bot]` (CodeQL inline on cui-http#178 and #186)
- `dependabot[bot]`
- `cuioss-release-bot[bot]`

## Coverage

| Repository | PRs | pr-agent guide | CodeRabbit: any artefact | CodeRabbit reviewed | CodeRabbit refused only | CodeRabbit refused on any commit | Sourcery: any artefact | Sourcery reviewed | Sourcery refused only | No reviewer at all |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| plan-marshall | 99 | 96 | 96 | 77 | 19 | 66 | 96 | 22 | 74 | 3 |
| cui-http | 29 | 25 | 26 | 25 | 1 | 19 | 25 | 7 | 18 | 3 |
| TokenSheriff | 29 | 15 | 15 | 14 | 1 | 3 | 15 | 5 | 10 | 14 |
| API-Sheriff | 24 | 20 | 20 | 18 | 1 | 11 | 19 | 6 | 13 | 4 |
| **Total** | **181** | **156** | **157** | **134** | **22** | **99** | **155** | **40** | **115** | **24** |

**No reviewer at all: 24 of 181, and all 24 are Dependabot**, which matches the org skip rule in the reusable workflow's job `if:`. The automated version bumps that made up 25 of the previous pass's 37 are now all skip-labelled.

⭐ **Substantive PRs with no pr-agent result: 1 of 157 non-Dependabot PRs.** It is **cui-http#185** (`fix(security): detect semicolon dot-segment traversal bypass`, +348/−4, merged).

- Opened 14:20:42Z. Across **every** workflow between 14:15 and 14:30 there are zero `pull_request`-event runs; only two unrelated `issue_comment` runs.
- The first `pull_request` runs arrive at 15:03 after a force-push (synchronize), which `pr-agent.yml` does not subscribe to.
- ⇒ **Unassessable, never triggered.** This is a trigger defect, not a bot defect. Its predecessor #183 (same title) did get a canned guide.

**CodeRabbit refusals.**

- Refused-only PRs: 22. Of these, 20 were rate-limited (expires), and **2 hit the size limit, which never expires** (plan-marshall #1407 and #1432, "Too many files").
- "Reviews paused" appeared on 9 PRs.
- On 54 PRs the summary comment currently shows a limit warning **and** the PR carries real reviews.

**Sourcery refusals.**

- Quota ("own review budget", expires) on 103 PRs, size on 34 (never expires).
- Sourcery produced a review on only **40 of 181**. On 115 the only output is a refusal.

## Yield

| Reviewer | Artefact | Volume | Substantive |
|---|---|---:|---:|
| pr-agent | PR Reviewer Guide | 156 (on 156 PRs) | **4** (cui-http#182, plan-marshall #1372, #1376, #1393) |
| pr-agent | Security cell populated | 0 of 156 | 0 |
| pr-agent | `/improve` (plan-marshall only, `auto-improve: true`) | 92 PRs | **10 PRs with 1 commitable suggestion each**; 82 issue comments say "No code suggestions found" |
| CodeRabbit | Inline root comments | 664 (1249 including replies) | n/a |
| CodeRabbit | Reviews | 827 (242 with a body) | **665 actionable, SELF-DECLARED** ("Actionable comments posted: N"); 67 nitpicks, SELF-DECLARED |
| Sourcery | Reviews | 192 (+21 inline) | 11 PRs with "I've found N issues"; 140 refusal artefacts (105 quota, 35 size) |

- **152 of 156 guides (97.4%) are the canned table** carrying both "No major issues detected" and "No security concerns identified".
- Per repo, guides and substantive: plan-marshall 96/3, cui-http 25/1, TokenSheriff 15/0, API-Sheriff 20/0.
- CodeRabbit self-declared actionable per repo: plan-marshall 401 (71 PRs), cui-http 62 (21), TokenSheriff 62 (14), API-Sheriff 140 (17).

**The substantive pr-agent findings, quoted briefly:**

- **cui-http#182, "PR Description Divergence".** The description claims `Redirect.NORMAL` is set, while the code deliberately leaves `Redirect.NEVER`.
- **plan-marshall#1372, "Incorrect Bundle Derivation".** `_derive_synced_bundles` splits on the first hyphen, so `pm-*` / `plan-*` entries are misidentified and pruned.
- **plan-marshall#1376, "Incorrect Output Parser".** `json.loads` runs on TOON stdout, so every live call silently fails closed.
- **plan-marshall#1393, "Duplicate Rules in Permission Fix Ensure".** Multi-rule intents are duplicated by `ensure` and skipped by `add`.
- **`/improve` inline suggestions**, one each on #1372, #1376, #1386 (`parse_toon` may return a list), #1393, #1396 (a bool passes `isinstance(int)`), #1399 (`isdigit` on a whitespace-padded token), #1481/#1482 (the `specs_excluded` miscount), #1486 (a relative `own_dir` against a resolved candidate) and #1497 (the test shells out to the on-disk executor).

## Paired recall

On the **123 PRs** where CodeRabbit self-declared at least one actionable comment **and** pr-agent posted a guide:

> **pr-agent's guide reported a finding on 4 of 123** (plan-marshall 3 of 71, cui-http 1 of 21, TokenSheriff 0 of 14, API-Sheriff 0 of 17).
> Counting `/improve` inline suggestions as well, **9 of 123**.

**Reverse direction: pr-agent findings CodeRabbit did not file.** This was checked by searching identifiers across CodeRabbit's inline, review and issue bodies on the same PR, then reading the matches. There are 10 distinct pr-agent issues (#1481 and #1482 share a diff).

- **CodeRabbit also filed it:** #1372 (CodeRabbit 3893114450, Major) and #1376 (CodeRabbit 3902800586, Major).
- **Partial overlap:** #1399. The same function, but CodeRabbit flagged the `"²"` input class.
- **CodeRabbit did not file it (7):** cui-http#182, plan-marshall #1386, #1393 (CodeRabbit's nearby comments cover dry-run duplicates, a different mechanism), #1396, #1481/#1482, #1486 and #1497.
- Our posted answers on the 6 plan-marshall ones:
  - **accepted/fixed 4:** #1396 (fix commit 1dac71325, PR later closed), #1482, #1486, #1497
  - **rejected 1:** #1386, "premise does not hold"
  - **unanswered 1:** #1393
- **None of the 7 is a security finding**; last pass had cui-http#162.

## Four-outcome scoring (pr-agent, review-practice § 1)

The baseline is CodeRabbit or Sourcery having *reviewed*. The baseline count is the larger of CodeRabbit's self-declared actionable and Sourcery's "found N issues".

| Outcome | plan-marshall | cui-http | TokenSheriff | API-Sheriff | Total |
|---|---:|---:|---:|---:|---:|
| Clean, corroborated | 5 | 3 | 0 | 0 | **8** |
| Deficit (pr-agent guide empty) | 71 | 20 | 14 | 18 | **123** |
| Deficit (pr-agent non-empty but fewer) | 3 | 1 | 0 | 0 | **4** |
| Unassessable, no baseline | 17 | 1 | 1 | 2 | **21** |
| Unassessable, never triggered | 0 | 1 | 0 | 0 | **1** |
| Not scored: Dependabot, excluded by design | 3 | 3 | 14 | 4 | 24 |
| **Total** | 99 | 29 | 29 | 24 | **181** |

- Clean-corroborated: cui-http #183, #193, #194; plan-marshall #1383, #1391, #1418, #1435, #1472.
- **No-baseline PRs that merged (6):** plan-marshall #1380, #1406, #1407 (both reviewers size-refused, never expires), #1438; API-Sheriff #288 and #300. On these the only posted review is the canned pr-agent guide.
  - ⛔ **plan-marshall#1438 merged on 2026-09-07 with no CodeRabbit review** (only a "Review limit reached" summary) and no skip label. That was *after* `.plan/marshal.json` made CodeRabbit required at #1407 (`required_bots: "cuioss-review-bot,coderabbit"`, merged 2026-09-04T16:06:12Z).
  - #1407 itself merged on a never-expiring CodeRabbit size refusal.
- **pr-agent run anomalies (plan-marshall, 922 runs):**
  - The `/review` re-review on **#1479** failed at step "Generate Review Token" and never recovered; the guide shows only the opening commit.
  - **#1480** failed the same way and recovered 13 minutes later.
  - Run 34748813129 (issue_comment, display title of #1477) has been `queued` since 2026-09-13T09:01:19Z.

## Adjudication proxy (plan-marshall, full population, not sampled)

Only answers **we posted on the PR** count: thread replies from `cuioss-oliver` / `OliverWolffGIP`, and `## Triage dispositions` batched comments matched by `In reply to comment_id`. There are 98 batched comments, which reference 98 review and 43 issue-comment node ids.

- Plain CodeRabbit "Actionable comments posted: N" review envelopes (77) are **not findings** and are excluded. 42 of them were answered anyway.
- Dispositions were classified by regex over the first 300 characters. On a seeded random sample of 30 answered units, **27 of 30 matched a hand reading**. The errors were 2 split verdicts read one-directionally and 1 residual "unclear" that was a rejection.

| Bot / unit | Findings | Accepted | Mixed | Deferred | Rejected | Answered as "envelope" | Unclear | **Unanswered** |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| CodeRabbit inline (root) | 400 | 255 | 21 | 11 | 42 | — | 5 | **66** |
| CodeRabbit review body with outside-diff or nitpick content | 58 | 23 | 6 | 2 | 6 | 4 | 2 | **15** |
| pr-agent `/improve` inline | 10 | 6 | — | — | 1 | — | — | **3** |
| pr-agent substantive guide | 3 | — | — | — | — | — | — | **3** |
| Sourcery inline | 15 | 6 | — | 1 | 4 | — | 1 | **3** |
| Sourcery review body ("found N issues") | 7 | — | — | — | — | — | — | **7** |
| **Total** | **493** | **290** | **27** | **14** | **53** | **4** | **8** | **97** |

- **CodeRabbit inline, rejection among dispositioned answers:** 42 of 334 (12.6%), plus 21 mixed. This is our own disposition, not independent adjudication.
- **How the 66 unanswered CodeRabbit inline and the 6 unanswered pr-agent and Sourcery inline split:**
  - 55 CodeRabbit and 3 Sourcery threads are resolved and carry the bot's own "✅ Addressed in …" marker, but have **no posted answer from us**.
  - 3 are resolved with no marker and no reply: CodeRabbit on #1458 (3969226297), and pr-agent on #1372 (3893066633) and #1393 (3927008629).
  - ⛔ **11 are unresolved and unanswered.**
    - Merged PRs: #1433 (3947649192); #1468 (3992367351); **#1484, all four** (4000267866, 4000267870, 4000267874, 4000267877).
    - Closed PRs: #1431 (3945309329); #1440 (3949759158, 3949759166, 3949759189; a review-only scaffolding PR); #1481 (pr-agent 3997885650).
- **Unanswered review bodies:**
  - CodeRabbit: #1376 5076454034; #1393 5104995698, 5106783448; #1405 5112492094; #1427 5133245503; #1431 5126087156, 5126654825; #1433 5130236126; #1452 5143354878; #1456 5151198582; #1483 5191034300, 5191300068; #1487 5193823584, 5194494441; #1497 5207378850.
  - Sourcery: **all 7**. #1439 5131494404; #1441 5132185896; #1454 5146694168; #1469 5184086126; #1485 5191483308; #1496 5206672037 (PR still open); #1497 5207048966.
  - pr-agent guides: **all 3 substantive guides** (#1372 5476142662, #1376 5491880896, #1393 5529527683).
- **Answers outside the sanctioned shape:** 16 of the 97 unanswered units sit on PRs (#1440, #1452, #1456, #1483) that carry a later free-form PR-level note, e.g. an `@coderabbitai review` request stating "Both Major findings… are fixed in `bb376bdd9`". That is not a per-finding answer.

## Epochs

| Candidate boundary | In window? | Behavioural effect on pr-agent |
|---|---|---|
| `cuioss/pr-agent-settings` `.pr_agent.toml` | Last change #15 on 2026-08-24, **before** the window | None in window |
| pr-agent-settings #63, packs published (merged 2026-09-13T22:04:19Z) | Yes | **None**: there is no consumer (next row) |
| pr-agent-settings #64, validate-packs CI | Yes | None (CI only) |
| `reusable-pr-agent-review.yml` v0.22.0 → v0.27.0 (callers bumped 09-02 to 09-11) | Yes | Diff over the range is only the `harden-runner` pin (v2.21.0 → v2.21.1). **At v0.27.0 (`9cffe3a2f`) the file references neither `project.yml` nor `packs/`** (grep verified), so the pack consumer side does not exist. |
| TokenSheriff / API-Sheriff repo-local `.pr_agent.toml` (Java pack, 4390 bytes) | Unchanged since 2026-08-09 | None |
| cui-http | Never had a repo-local file | None |
| ⭐ **plan-marshall #1388, merged 2026-09-03T22:04:35Z** | **Yes** | **Removed the repo-local `.pr_agent.toml`** (57 lines, python+plugin pack) and added `pr-agent.packs` to `.github/project.yml`. Nothing reads that key, so **plan-marshall has run pr-agent on central config only since this instant**. |
| plan-marshall `required_bots` gains coderabbit (#1407, 2026-09-04) | Yes | Gating only; no effect on pr-agent output |

plan-marshall pr-agent yield cut at #1388 (a guide is assigned by the time of its current body, `updated_at`):

| Epoch | Guides | Substantive | Canned | `/improve` PRs (by open time) | `/improve` non-empty |
|---|---:|---:|---:|---:|---:|
| A (< 2026-09-03T22:04:35Z, repo-local pack present) | 16 | **3** | 13 | 18 | 4 |
| B (≥ boundary, central config only) | 80 | **0** | 80 | 74 | 6 |

⚠ **Not attributable to the pack.**

- The previous pass measured plan-marshall *with* the pack at **0 substantive of 29**.
- TokenSheriff and API-Sheriff kept their Java packs throughout and produced 0 of 35 this pass.
- `/improve` did not collapse across the boundary.
- Epoch A has n = 16. The cut is reported because the boundary exists, not as a cause.

## Trigger confound (plan-marshall)

- **Method.** pr-agent's reviewed SHAs are the `head_sha` of successful `pull_request` runs (97 of 98 mapped to a PR by branch and time) plus every `Review updated until commit` marker. CodeRabbit's self-declared actionable counts are keyed by the review's `commit_id`.
- **Scope.** 71 paired PRs carrying 401 self-declared actionable.

| Bucket | Actionable (self-declared) | PRs |
|---|---:|---:|
| On a commit pr-agent reviewed (genuine recall miss) | **265** | 67 |
| On a commit pr-agent is not observed to have reviewed (confound) | 136 | 30 |

- **67 of 71 paired PRs** had CodeRabbit actionables at a commit pr-agent examined.
- **Bias:** in-place editing keeps only the *last* re-review marker, so intermediate `/review` SHAs are lost. The same-commit figure is a **floor**.

## Delta vs the 2026-08-30 pass

| Figure | 2026-08-30 pass | This pass |
|---|---:|---:|
| Window length | ~7.2 days | 15.6 days |
| Candidates / skip-excluded / collected | 160 / 63 / 97 | 351 / 164 / 187 |
| Population | 93 | 181 |
| Repositories contributing PRs | 6 | 4 (both cui-test repos fully skip-labelled) |
| pr-agent guide present | 44 / 93 (47%) | 156 / 181 (86%) |
| CodeRabbit, any artefact | 50 / 93 | 157 / 181 (134 reviewed, 22 refused only) |
| Sourcery, any artefact | 56 / 93 | 155 / 181 (**40 reviewed**, 115 refused only) |
| No reviewer at all | 37 (12 Dependabot + 25 bumps) | 24 (all Dependabot) |
| Substantive PR with no pr-agent result | 0 claimed | 1 (cui-http#185, never triggered) |
| Canned guides | 42 / 44 (95.5%) | 152 / 156 (97.4%) |
| Substantive guides | 2 / 44 | 4 / 156 |
| Security cell populated | 1 / 44 | **0 / 156** |
| `/improve` | 24 PRs, all empty | 92 PRs: 82 empty, **10 with 1 suggestion** |
| CodeRabbit inline | 396 (roots vs. all not stated) | 664 roots / 1249 all (not directly comparable) |
| CodeRabbit reviews / self-declared actionable | 243 / 217 | 827 (242 with body) / 665 |
| Sourcery reviews | 61 (18 size refusals) | 192 (35 size, 105 quota) + 21 inline |
| Paired recall (guide) | 1 / 35 | 4 / 123 (9 / 123 counting `/improve`) |
| pr-agent findings CodeRabbit did not file | 2 (1 security) | 7 distinct (0 security) |
| Human-authored skip-labelled PRs | not split | 84 (17 merged, ≥100 lines) |

## What is supportable, and what is NOT

✅ **Supportable**

1. **The required bot's guide is canned-empty on 97.4% of 156 PRs.** Paired recall is 4 of 123. The gate still cannot tell "reviewed clean" from "reviewed blind", now at twice the n.
2. **`/improve` is no longer uniformly empty.** 10 of 92 PRs carry a suggestion, and on plan-marshall 4 of 6 dispositioned ones were accepted and fixed. They are real findings CodeRabbit did not file. It is a low-volume surface, not a replacement for a reviewer.
3. **The trigger gap does not explain the recall gap.** On 67 of 71 paired plan-marshall PRs, CodeRabbit filed actionables on a commit pr-agent reviewed.
4. **The response path leaks.**
   - 97 of 493 plan-marshall finding units have no posted answer.
   - 11 are unresolved and unanswered, 6 of them on merged PRs.
   - All 7 Sourcery review bodies and all 3 substantive pr-agent guides were never answered.
5. **Sourcery is effectively absent through quota:** it produced a review on only 40 of 181 PRs.
6. **A required-bot merge without that bot's review occurred:** plan-marshall#1438, on CodeRabbit.
7. **`ci pr comments` truncates silently at 100 reviews, threads and comments** (10 per thread), with `status: success` and no truncation field. It was observed once (API-Sheriff#255) without finding-content loss.

⛔ **NOT supportable, and not claimed**

1. **CodeRabbit's 665 is SELF-DECLARED**, not a defect count. The adjudication proxy is *our own* disposition (12.6% rejected among dispositioned inline), not independent ground truth.
2. **No quality claim for TokenSheriff or API-Sheriff** (15 and 20 guides, 0 substantive each), nor for the cui-test repositories (n = 0). They report coverage only.
3. **The epoch A→B drop (3/16 → 0/80) is not attributed to removing the pack.** It is contradicted by the prior pass (0/29 with the pack) and by the Java-pack repos.
4. **"Drop pr-agent" does not follow.** 7 distinct findings CodeRabbit did not file, and 4 of the 5 plan-marshall ones with a posted disposition were accepted and fixed.
5. **The "no reviewer" buckets for the excluded repositories are not coverage defects** (pr-agent caller presence was not checked).

## Consequences for staged work (evidence-tied only)

- **PLAN-PR-026 / 061 (nobody reviewed vs. reviewed clean):**
  - 21 no-baseline PRs, 6 of them merged. Their only posted review is a canned pr-agent guide, which is indistinguishable from "reviewed clean".
  - The 152 of 156 canned rate sizes the collapsed state.
  - cui-http#185 is a never-triggered case, and #1479 is a re-review that failed silently at token generation. Both need to be distinguishable from "clean".
- **PLAN-PR-058 (CodeRabbit clean-review marker gate):**
  - 74 PRs carry a CodeRabbit refusal *inside the summary comment*, 71 of them as in-place edits.
  - 54 of those PRs also have real reviews.
  - "Review skipped: No new commits" (5) and "Review failed: pull request is closed" (1) sit in the same structural slot and are **not** refusals.
  - A conversational reply can quote refusal text (cui-http#179).
  - ⇒ The gate must key on structural markers and on the review record, never on the summary body's current text alone.
- **PLAN-PR-059 / 060 (pipeline loss and response path):**
  - 97 unanswered finding units, including 11 unresolved.
  - Unsanctioned free-form answers cover 16 of them.
  - All Sourcery review bodies went unanswered.
  - `fetch_pr_comments_data` has unpaginated GraphQL `first:` caps with no truncation signal (`github_ops.py:405–447`).
  - pr-agent's `/improve` inline comments are a finding surface and were 3 of 10 unanswered.
- **PLAN-PR-066 (packs consumer):**
  - **Verified absent at the sampled ref.** `reusable-pr-agent-review.yml@9cffe3a2f` (v0.27.0) references neither `project.yml` nor `packs/`.
  - Packs have been published (pr-agent-settings #63) with no reader.
  - plan-marshall removed its repo-local `.pr_agent.toml` at #1388 (2026-09-03T22:04:35Z), so it has run with **no pack at all** since then. The consumer gap is now live in production for plan-marshall, not hypothetical.

## Reproduction

The scripts are persisted beside this document in [`2026-09-15-corpus-scripts/`](2026-09-15-corpus-scripts/). The raw JSON dumps (~58 MB) were NOT persisted — `collect.py` / `collect_other.py` regenerate them, but a re-run reads PR state as of the re-run, not as of this pass. The scripts expect their raw dumps in a working directory; point them at a fresh scratch directory before running.

| Script | What it does |
|---|---|
| `collect.py` | Enumerates with `gh pr list` and dumps `raw/{repo}__{n}.json` (issue comments, review comments, reviews, commits), including skip-labelled PRs |
| `collect_other.py` | Dumps the org-search remainder into `raw_other/` |
| `classify.py` | Produces `classified.json` (structural refusal markers, guide length and focus parsing) |
| `report.py` | Coverage, yield and paired-recall tables |
| `confound.py` | Maps `pm_pragent_runs.json` onto pr-agent SHAs and does the trigger buckets, refined scoring (`scoring.json`) and the epoch cut |
| `adjudicate.py` | Adjudication (`adjudication.json`); `resolved_map.json` holds the `ci pr comments` resolution states (`ci_comments/*.toon`) |
| `final_tables.py` | Writes `appendix.md` |

Epoch evidence:

- `gh api repos/cuioss/cuioss-organization/compare/v0.22.0...v0.27.0`
- `gh api repos/cuioss/plan-marshall/commits/ef974632c` (`.pr_agent.toml` removed)
- `gh api "repos/cuioss/pr-agent-settings/commits?path=.pr_agent.toml"`

## Data appendix

Columns: CR = CodeRabbit, Src = Sourcery. State: M = merged, C = closed unmerged, O = open. "pr-agent outcome" is the § 1 score, with `+improve:N` for inline `/improve` suggestions. "Baseline" for scoring is max(CR self-declared actionable, Sourcery "found N"), so some deficits show CR N = 0 (Sourcery supplied the baseline). "CR N" is CodeRabbit self-declared actionable.

| Repo | PR | Title (short) | Opened | State | pr-agent outcome | CR outcome | Src outcome | pr-agent substantive | CR N |
|---|---|---|---|---|---|---|---|---|---|
| plan-marshall | 1372 | feat(sync-opencode): add project-local skill dep | 2026-08-31 | M | deficit(pra non-empty) +improve:1 | reviewed+ref | reviewed | y | 7 |
| plan-marshall | 1374 | docs: repoint ingested epic citations at durable | 2026-08-31 | M | deficit | reviewed | reviewed | n | 1 |
| plan-marshall | 1375 | lint: bring marketplace/targets inside the ruff | 2026-09-01 | M | deficit | reviewed+ref | REFUSED:quota | n | 1 |
| plan-marshall | 1376 | feat(platform-runtime,plan-retrospective): move | 2026-09-01 | M | deficit(pra non-empty) +improve:1 | reviewed+ref | REFUSED:size | y | 4 |
| plan-marshall | 1378 | feat(plugin-doctor): make AskUserQuestion standa | 2026-09-02 | M | deficit | reviewed+ref | reviewed+ref | n | 2 |
| plan-marshall | 1379 | fix(targets,bundles): register read_directive an | 2026-09-02 | M | deficit | reviewed | reviewed+ref | n | 10 |
| plan-marshall | 1380 | feat(manage-config): over-provision domains on z | 2026-09-02 | M | unassessable-no-baseline | REFUSED:rate | REFUSED:quota | n | 0 |
| plan-marshall | 1382 | feat(persona-plan-marshall-agent): honour user l | 2026-09-02 | M | deficit | reviewed | REFUSED:quota | n | 4 |
| plan-marshall | 1383 | test(plan-marshall): convert namespace tests to | 2026-09-02 | M | clean-corroborated | reviewed | REFUSED:size | n | 0 |
| plan-marshall | 1384 | feat(platform-runtime): report dual-homed hook i | 2026-09-02 | M | deficit | reviewed+ref | reviewed+ref | n | 3 |
| plan-marshall | 1385 | fix(epic-surface-partition): stop treating leads | 2026-09-02 | M | deficit | reviewed+ref | REFUSED:size | n | 2 |
| plan-marshall | 1386 | fix(manage-tasks): repair documented invocations | 2026-09-03 | M | deficit +improve:1 | reviewed | REFUSED:quota,size | n | 5 |
| plan-marshall | 1387 | feat(user-communication): add output-volume rule | 2026-09-03 | M | deficit | reviewed | REFUSED:quota | n | 3 |
| plan-marshall | 1388 | feat(pr-agent): publish review packs to pr-agent | 2026-09-03 | M | deficit | reviewed+ref | REFUSED:size | n | 7 |
| plan-marshall | 1391 | fix(manage-config): stop treating always_on-only | 2026-09-03 | M | clean-corroborated | reviewed | REFUSED:quota | n | 0 |
| plan-marshall | 1392 | feat(automatic-review): flag unknown bot-kind to | 2026-09-03 | M | deficit | reviewed+ref | REFUSED:size | n | 4 |
| plan-marshall | 1393 | feat(platform-runtime): route permission skills | 2026-09-03 | M | deficit(pra non-empty) +improve:1 | reviewed+ref | REFUSED:quota | y | 6 |
| plan-marshall | 1395 | test: publish a tree-wide parser-seam coverage g | 2026-09-03 | M | deficit | reviewed | REFUSED:quota | n | 2 |
| plan-marshall | 1396 | fix(planning-lane): stop reporting confidence in | 2026-09-03 | C | unassessable-no-baseline +improve:1 | REFUSED:rate | REFUSED:size | n | 0 |
| plan-marshall | 1397 | fix(phase-6-finalize): make meta-project-only gu | 2026-09-04 | M | deficit | reviewed+ref | REFUSED:size | n | 15 |
| plan-marshall | 1398 | fix(admissibility): enforce authorship gate in c | 2026-09-04 | M | deficit | reviewed+ref | REFUSED:quota | n | 9 |
| plan-marshall | 1399 | fix(planning-lane): stop reporting confidence in | 2026-09-04 | M | deficit +improve:1 | reviewed+ref | REFUSED:size | n | 25 |
| plan-marshall | 1405 | feat(platform-runtime): runtime-seam-completenes | 2026-09-04 | M | deficit | reviewed+ref | REFUSED:quota | n | 3 |
| plan-marshall | 1406 | feat(skill-domains): seed file_globs from domain | 2026-09-04 | M | unassessable-no-baseline | REFUSED:rate | REFUSED:quota | n | 0 |
| plan-marshall | 1407 | fix(test-quality): close module-budget campaign | 2026-09-04 | M | unassessable-no-baseline | REFUSED:size | REFUSED:size | n | 0 |
| plan-marshall | 1408 | permission-web: route through the registry; decl | 2026-09-04 | M | deficit | reviewed | REFUSED:quota | n | 1 |
| plan-marshall | 1409 | fix(automatic-review): currency-test CodeRabbit' | 2026-09-04 | M | deficit | reviewed | REFUSED:quota | n | 2 |
| plan-marshall | 1410 | feat(automatic-review): diagnose required-review | 2026-09-04 | M | deficit | reviewed+ref | REFUSED:quota | n | 4 |
| plan-marshall | 1411 | chore(cloud-plan-lane): name the empty review, t | 2026-09-04 | C | unassessable-no-baseline | REFUSED:rate | REFUSED:quota | n | 0 |
| plan-marshall | 1412 | chore(cloud-plan-lane): name the empty review, t | 2026-09-04 | C | unassessable-no-baseline | REFUSED:rate | REFUSED:quota | n | 0 |
| plan-marshall | 1413 | chore(cloud-plan-lane): name the empty review, t | 2026-09-04 | C | unassessable-no-baseline | REFUSED:rate | REFUSED:quota | n | 0 |
| plan-marshall | 1414 | chore(cloud-plan-lane): name the empty review, t | 2026-09-04 | C | unassessable-no-baseline | REFUSED:rate | REFUSED:quota | n | 0 |
| plan-marshall | 1415 | chore(cloud-plan-lane): name the empty review, t | 2026-09-04 | C | unassessable-no-baseline | REFUSED:rate | REFUSED:quota | n | 0 |
| plan-marshall | 1416 | chore(cloud-plan-lane): name the empty review, t | 2026-09-04 | M | deficit | reviewed+ref | REFUSED:quota | n | 3 |
| plan-marshall | 1417 | chore(deps-dev): Update ruff requirement from >= | 2026-09-05 | M | n/a dependabot | — | — | — | 0 |
| plan-marshall | 1418 | fix(sync-opencode): resolve one bundle per entry | 2026-09-05 | M | clean-corroborated | reviewed | REFUSED:quota | n | 0 |
| plan-marshall | 1419 | docs(executor): reference the canonical exit-cod | 2026-09-05 | C | unassessable-no-baseline | REFUSED:rate | REFUSED:size | n | 0 |
| plan-marshall | 1420 | docs(repo-scope): record ADR-020 and declare met | 2026-09-05 | M | deficit | reviewed+ref | REFUSED:quota | n | 3 |
| plan-marshall | 1422 | feat(domains): add narrowing re-resolution once | 2026-09-05 | M | deficit | reviewed+ref | REFUSED:quota | n | 13 |
| plan-marshall | 1423 | docs(executor): add the canonical exit-code conv | 2026-09-05 | M | deficit | reviewed+ref | REFUSED:quota | n | 6 |
| plan-marshall | 1424 | feat(plan-orchestrator): add queue --add-row sin | 2026-09-06 | C | deficit | reviewed+ref | REFUSED:quota | n | 3 |
| plan-marshall | 1425 | fix(manage-tasks): stop overloading fresh for th | 2026-09-06 | M | deficit | reviewed+ref | REFUSED:quota | n | 9 |
| plan-marshall | 1426 | test: zero out skipped tests and give run condit | 2026-09-06 | M | deficit | reviewed+ref | REFUSED:quota | n | 6 |
| plan-marshall | 1427 | fix(toon): unify TOON read/write on the canonica | 2026-09-06 | M | deficit | reviewed+ref | REFUSED:quota | n | 10 |
| plan-marshall | 1428 | docs(executor): reference the canonical exit-cod | 2026-09-06 | C | unassessable-no-baseline | REFUSED:rate | REFUSED:size | n | 0 |
| plan-marshall | 1429 | docs(executor): reference the canonical exit-cod | 2026-09-06 | M | deficit | reviewed+ref | REFUSED:size | n | 1 |
| plan-marshall | 1430 | fix(test-suite): restore falsifiability with mut | 2026-09-06 | C | deficit | reviewed+ref | REFUSED:size | n | 15 |
| plan-marshall | 1431 | fix(automatic-review): arm the CodeRabbit rate-w | 2026-09-06 | C | deficit | reviewed | REFUSED:size | n | 5 |
| plan-marshall | 1432 | test(docstrings): re-sweep historical-prose cita | 2026-09-06 | C | unassessable-no-baseline | REFUSED:size | REFUSED:quota | n | 0 |
| plan-marshall | 1433 | fix(automatic-review): arm the CodeRabbit rate-w | 2026-09-06 | M | deficit | reviewed+ref | REFUSED:size | n | 4 |
| plan-marshall | 1434 | feat(plan-orchestrator): add queue --add-row sin | 2026-09-07 | M | deficit | reviewed | REFUSED:quota | n | 4 |
| plan-marshall | 1435 | test(docstrings): re-sweep historical-prose cita | 2026-09-07 | M | clean-corroborated | reviewed+ref | reviewed+ref | n | 0 |
| plan-marshall | 1436 | test(docstrings): re-sweep historical-prose cita | 2026-09-07 | M | deficit | reviewed | REFUSED:quota | n | 2 |
| plan-marshall | 1437 | feat(autonomy-gates): flip loop-back and final-m | 2026-09-07 | M | deficit | reviewed+ref | REFUSED:quota | n | 4 |
| plan-marshall | 1438 | feat(targets): file-level target scoping and the | 2026-09-07 | M | unassessable-no-baseline | REFUSED:rate | REFUSED:quota | n | 0 |
| plan-marshall | 1439 | fix(tools-file-ops): warn on worktree-escape exe | 2026-09-07 | C | deficit | REFUSED:rate | reviewed | n | 0 |
| plan-marshall | 1440 | REVIEW-ONLY (do not merge): post-hoc CodeRabbit | 2026-09-07 | C | deficit | reviewed | REFUSED:quota | n | 3 |
| plan-marshall | 1441 | fix(ref-toon-format): stop the block-scalar dede | 2026-09-07 | M | deficit | reviewed | reviewed | n | 0 |
| plan-marshall | 1442 | fix(test-suite): restore falsifiability with mut | 2026-09-07 | C | unassessable-no-baseline | REFUSED:rate | REFUSED:size | n | 0 |
| plan-marshall | 1443 | fix(test-suite): restore falsifiability with mut | 2026-09-07 | M | deficit | reviewed | REFUSED:size | n | 10 |
| plan-marshall | 1444 | fix(tools-file-ops): warn on worktree-escape exe | 2026-09-07 | M | deficit | reviewed | reviewed | n | 1 |
| plan-marshall | 1446 | fix(test): convert preambles reachable by shippe | 2026-09-07 | M | deficit | reviewed | REFUSED:quota | n | 1 |
| plan-marshall | 1447 | fix(prompt-quality): remediate user-facing promp | 2026-09-08 | M | deficit | reviewed+ref | REFUSED:quota | n | 22 |
| plan-marshall | 1449 | chore(platform-runtime): harness bash-timeout | 2026-09-08 | M | deficit | reviewed | REFUSED:quota | n | 3 |
| plan-marshall | 1452 | fix(permission): close the permission-grammar re | 2026-09-08 | M | deficit | reviewed+ref | REFUSED:quota | n | 1 |
| plan-marshall | 1454 | fix(phase-6-finalize): declare pre-push quality | 2026-09-08 | M | deficit | reviewed | reviewed+ref | n | 2 |
| plan-marshall | 1455 | test: parametrize tabular families in runtime sl | 2026-09-08 | M | deficit | reviewed+ref | REFUSED:size | n | 7 |
| plan-marshall | 1456 | The pm-plugin-development authoring surface is t | 2026-09-09 | M | deficit | reviewed+ref | REFUSED:quota | n | 7 |
| plan-marshall | 1458 | State runtime facts through the runtime; single- | 2026-09-09 | M | deficit | reviewed+ref | REFUSED:size | n | 17 |
| plan-marshall | 1460 | No bundle outside plan-marshall names Claude as | 2026-09-10 | M | deficit | reviewed+ref | reviewed+ref | n | 2 |
| plan-marshall | 1462 | refactor(opencode): move sync-opencode tooling t | 2026-09-10 | M | deficit | reviewed+ref | reviewed | n | 2 |
| plan-marshall | 1466 | fix(orchestrator): validate queue statuses and c | 2026-09-11 | M | deficit | reviewed | REFUSED:quota | n | 1 |
| plan-marshall | 1468 | chore: remove superseded crossing inventory and | 2026-09-11 | M | deficit | reviewed | reviewed | n | 1 |
| plan-marshall | 1469 | fix(build): record in_process ledger entry and p | 2026-09-11 | M | deficit | reviewed | reviewed | n | 6 |
| plan-marshall | 1470 | chore(deps-dev): Update types-pyyaml requirement | 2026-09-12 | M | n/a dependabot | — | — | — | 0 |
| plan-marshall | 1471 | chore(deps-dev): Update ruff requirement from >= | 2026-09-12 | M | n/a dependabot | — | — | — | 0 |
| plan-marshall | 1472 | fix(orchestrator): containment-aware overlap and | 2026-09-12 | M | clean-corroborated | reviewed | REFUSED:quota | n | 0 |
| plan-marshall | 1473 | feat(finalize): gate foreign-path population and | 2026-09-12 | M | deficit | reviewed+ref | REFUSED:quota | n | 5 |
| plan-marshall | 1474 | test(plan-marshall): survey and replace vacuous | 2026-09-12 | C | deficit | reviewed+ref | reviewed+ref | n | 2 |
| plan-marshall | 1475 | fix(permissions): stop modelling Write() as a li | 2026-09-12 | M | deficit | reviewed | REFUSED:quota | n | 4 |
| plan-marshall | 1476 | test(plan-marshall): survey and replace vacuous | 2026-09-12 | M | deficit | reviewed+ref | reviewed+ref | n | 1 |
| plan-marshall | 1477 | fix(automatic-review): gate CodeRabbit clean-rev | 2026-09-12 | M | deficit | reviewed+ref | REFUSED:size | n | 9 |
| plan-marshall | 1478 | feat(orchestrator): reconcile staged declaration | 2026-09-12 | C | unassessable-no-baseline | REFUSED:rate | REFUSED:quota | n | 0 |
| plan-marshall | 1479 | feat(build-queue): centralize max_slots as machi | 2026-09-12 | M | deficit | reviewed+ref | REFUSED:size | n | 15 |
| plan-marshall | 1480 | fix(workflow-integration-github,manage-providers | 2026-09-12 | M | deficit | reviewed | reviewed+ref | n | 2 |
| plan-marshall | 1481 | feat(orchestrator): reconcile staged declaration | 2026-09-12 | C | unassessable-no-baseline +improve:1 | REFUSED:rate | REFUSED:quota | n | 0 |
| plan-marshall | 1482 | feat(orchestrator): reconcile staged declaration | 2026-09-13 | M | deficit +improve:1 | reviewed+ref | reviewed+ref | n | 4 |
| plan-marshall | 1483 | fix(manage-status): close every open phase on ar | 2026-09-13 | M | deficit | reviewed+ref | REFUSED:quota | n | 5 |
| plan-marshall | 1484 | docs(install): add OpenCode install path to READ | 2026-09-13 | M | deficit | reviewed | REFUSED:quota | n | 4 |
| plan-marshall | 1485 | docs(effort): record local model map schema and | 2026-09-13 | C | deficit | REFUSED:rate | reviewed | n | 0 |
| plan-marshall | 1486 | test(quality): sweep three single-instance defec | 2026-09-13 | M | deficit +improve:1 | reviewed | REFUSED:quota | n | 11 |
| plan-marshall | 1487 | fix(orchestrator): enforce queue slug semantics | 2026-09-13 | M | deficit | reviewed+ref | REFUSED:quota | n | 4 |
| plan-marshall | 1488 | fix(phase-6-finalize): correct declared surfaces | 2026-09-14 | M | deficit | reviewed+ref | REFUSED:size | n | 8 |
| plan-marshall | 1489 | fix(manage-architecture): report only what store | 2026-09-14 | M | deficit | reviewed+ref | REFUSED:size | n | 18 |
| plan-marshall | 1490 | docs(effort): record local model map schema and | 2026-09-14 | M | deficit | reviewed+ref | reviewed+ref | n | 1 |
| plan-marshall | 1494 | feat(orchestrator): dispatch write-bound draftin | 2026-09-14 | M | deficit | reviewed | REFUSED:quota | n | 3 |
| plan-marshall | 1496 | feat(config): add interaction_mode preference wi | 2026-09-15 | O | deficit | reviewed+ref | reviewed | n | 4 |
| plan-marshall | 1497 | feat(runtime): add script-driven client.toon at | 2026-09-15 | M | deficit +improve:1 | reviewed+ref | reviewed | n | 7 |
| plan-marshall | 1498 | feat(steward): materialize per-level model pins | 2026-09-15 | O | unassessable-no-baseline | REFUSED:rate | REFUSED:quota | n | 0 |
| cui-http | 176 | chore(deps): bump actions/setup-java from 5.7.0 | 2026-08-31 | M | n/a dependabot | — | — | — | 0 |
| cui-http | 178 | test(security): fix attack database labels and s | 2026-08-31 | M | deficit | reviewed+ref | reviewed | n | 9 |
| cui-http | 179 | fix(client): honor charset, redirect policy, fix | 2026-08-31 | C | unassessable-no-baseline | REFUSED:rate | REFUSED:quota | n | 0 |
| cui-http | 180 | docs(security): correct Javadoc claims to match | 2026-08-31 | M | deficit | reviewed | reviewed+ref | n | 3 |
| cui-http | 181 | fix(client): honor response charset, correct cli | 2026-08-31 | C | deficit | reviewed+ref | REFUSED:quota | n | 3 |
| cui-http | 182 | fix(client): honor response charset, correct cli | 2026-09-01 | M | deficit(pra non-empty) | reviewed+ref | reviewed+ref | y | 2 |
| cui-http | 183 | fix(security): detect semicolon dot-segment trav | 2026-09-01 | C | clean-corroborated | reviewed | REFUSED:quota | n | 0 |
| cui-http | 184 | docs(adr): deduplicate colliding ADR numbers and | 2026-09-01 | M | deficit | reviewed+ref | reviewed | n | 2 |
| cui-http | 185 | fix(security): detect semicolon dot-segment trav | 2026-09-01 | M | never-triggered | reviewed+ref | REFUSED:quota | — | 0 |
| cui-http | 186 | feat(client): validate redirect hops before foll | 2026-09-01 | M | deficit | reviewed+ref | REFUSED:size | n | 5 |
| cui-http | 188 | build(generators): fail the build on a class-fre | 2026-09-02 | M | deficit | reviewed+ref | — | n | 1 |
| cui-http | 189 | test(evidence): restore TLS coverage and fix gua | 2026-09-02 | M | deficit | reviewed+ref | reviewed+ref | n | 1 |
| cui-http | 191 | docs: document redirect API and prune the ADR co | 2026-09-02 | M | deficit | reviewed | reviewed | n | 2 |
| cui-http | 193 | test(redirect): prove FORWARD_TO_ALLOWLISTED for | 2026-09-03 | C | clean-corroborated | reviewed | REFUSED:quota | n | 0 |
| cui-http | 194 | test(redirect): prove FORWARD_TO_ALLOWLISTED for | 2026-09-03 | M | clean-corroborated | reviewed | REFUSED:quota | n | 0 |
| cui-http | 199 | fix(security): re-tier suspicious-path detection | 2026-09-04 | M | deficit | reviewed | REFUSED:quota | n | 1 |
| cui-http | 206 | docs: add full code and documentation quality re | 2026-09-05 | M | deficit | reviewed+ref | REFUSED:quota | n | 11 |
| cui-http | 208 | fix(benchmark): guard deploy, jar packaging, and | 2026-09-05 | M | deficit | reviewed+ref | REFUSED:quota | n | 5 |
| cui-http | 209 | fix(security): decode-aware double-encoding, del | 2026-09-05 | C | deficit | reviewed+ref | REFUSED:quota | n | 2 |
| cui-http | 210 | fix(security): decode-aware double-encoding, del | 2026-09-06 | M | deficit | reviewed+ref | REFUSED:quota | n | 3 |
| cui-http | 211 | chore(deps): bump step-security/harden-runner fr | 2026-09-07 | M | n/a dependabot | — | — | — | 0 |
| cui-http | 214 | fix(forwarded): reconcile family precedence and | 2026-09-07 | M | deficit | reviewed+ref | reviewed | n | 3 |
| cui-http | 216 | fix(security): correct character-set grammars an | 2026-09-07 | C | deficit | reviewed+ref | REFUSED:quota | n | 1 |
| cui-http | 217 | fix(security): correct character-set grammars an | 2026-09-08 | M | deficit | reviewed+ref | REFUSED:quota | n | 1 |
| cui-http | 222 | fix(security): sanitise exception detail and sto | 2026-09-08 | M | deficit | reviewed+ref | REFUSED:quota | n | 1 |
| cui-http | 227 | fix(security): enforce content-type pipeline, re | 2026-09-08 | M | deficit | reviewed+ref | REFUSED:quota | n | 3 |
| cui-http | 229 | fix(security): reconcile configuration surface a | 2026-09-09 | M | deficit | reviewed | REFUSED:quota | n | 2 |
| cui-http | 231 | fix(security): validate cookie name/value and RF | 2026-09-09 | M | deficit | reviewed+ref | REFUSED:quota | n | 1 |
| cui-http | 235 | chore(deps): bump actions/setup-java from 6.0.0 | 2026-09-14 | M | n/a dependabot | — | — | — | 0 |
| TokenSheriff | 681 | feat(coverage): make refresh-class coverage gaps | 2026-08-31 | M | deficit | reviewed | reviewed | n | 4 |
| TokenSheriff | 682 | fix(client): bind refresh-path identity and reco | 2026-08-31 | M | deficit | reviewed+ref | REFUSED:size | n | 10 |
| TokenSheriff | 683 | build(deps-dev): bump browserslist from 4.28.4 t | 2026-09-01 | M | n/a dependabot | — | — | — | 0 |
| TokenSheriff | 684 | build(deps): bump step-security/harden-runner fr | 2026-09-02 | M | n/a dependabot | — | — | — | 0 |
| TokenSheriff | 687 | fix(client): close refresh-path gate gaps and en | 2026-09-02 | M | deficit | reviewed | REFUSED:quota | n | 3 |
| TokenSheriff | 688 | feat(client,validation): adopt cui-http verifyHo | 2026-09-02 | C | unassessable-no-baseline | REFUSED:rate | REFUSED:quota | n | 0 |
| TokenSheriff | 689 | feat(client,validation): adopt cui-http verifyHo | 2026-09-02 | M | deficit | reviewed | REFUSED:quota | n | 2 |
| TokenSheriff | 690 | build(deps): bump fast-uri from 3.1.5 to 3.1.7 i | 2026-09-02 | M | n/a dependabot | — | — | — | 0 |
| TokenSheriff | 691 | build(deps-dev): bump @humanfs/node from 0.16.7 | 2026-09-02 | M | n/a dependabot | — | — | — | 0 |
| TokenSheriff | 692 | build(deps-dev): bump @humanfs/node from 0.16.7 | 2026-09-02 | M | n/a dependabot | — | — | — | 0 |
| TokenSheriff | 694 | feat(validation-quarkus,client-quarkus): expose | 2026-09-03 | M | deficit | reviewed | REFUSED:quota | n | 2 |
| TokenSheriff | 699 | fix(validation,config): stabilize JWKS SAN test, | 2026-09-03 | M | deficit | reviewed | reviewed+ref | n | 1 |
| TokenSheriff | 701 | build(deps-dev): bump jest-environment-jsdom fro | 2026-09-04 | C | n/a dependabot | — | — | — | 0 |
| TokenSheriff | 702 | build(deps-dev): bump babel-jest from 30.5.0 to | 2026-09-04 | C | n/a dependabot | — | — | — | 0 |
| TokenSheriff | 703 | build(deps): bump org.apache.maven.plugins:maven | 2026-09-04 | C | n/a dependabot | — | — | — | 0 |
| TokenSheriff | 704 | build(deps-dev): bump jest from 30.4.2 to 30.5.0 | 2026-09-04 | M | n/a dependabot | — | — | — | 0 |
| TokenSheriff | 705 | build(deps-dev): bump eslint-plugin-jest from 29 | 2026-09-04 | M | n/a dependabot | — | — | — | 0 |
| TokenSheriff | 713 | fix(build): make -Ppre-commit gate fail-loud and | 2026-09-04 | M | deficit | reviewed | REFUSED:quota | n | 2 |
| TokenSheriff | 714 | docs(AGENTS): verify effective POM before trusti | 2026-09-06 | M | deficit | reviewed | reviewed | n | 2 |
| TokenSheriff | 715 | test(validation,client): assert exact identity, | 2026-09-07 | M | deficit | reviewed | REFUSED:quota | n | 3 |
| TokenSheriff | 718 | fix(client): carry refresh token through authori | 2026-09-07 | M | deficit | reviewed | REFUSED:quota | n | 1 |
| TokenSheriff | 720 | fix(build): order pre-commit assertions before t | 2026-09-08 | M | deficit | reviewed | REFUSED:quota | n | 1 |
| TokenSheriff | 725 | feat(client,integration-tests): close 2a refresh | 2026-09-08 | M | deficit | reviewed | REFUSED:size | n | 3 |
| TokenSheriff | 730 | fix(doc,validation): literal ArchUnit dots and r | 2026-09-09 | M | deficit | reviewed | reviewed+ref | n | 1 |
| TokenSheriff | 731 | refactor(client): reclassify mTLS as alpha (DPoP | 2026-09-09 | M | deficit | reviewed+ref | reviewed+ref | n | 27 |
| TokenSheriff | 734 | build(deps-dev): bump eslint-plugin-unicorn from | 2026-09-11 | M | n/a dependabot | — | — | — | 0 |
| TokenSheriff | 735 | build(deps-dev): bump stylelint from 17.14.1 to | 2026-09-11 | M | n/a dependabot | — | — | — | 0 |
| TokenSheriff | 736 | build(deps-dev): bump eslint from 10.9.1 to 10.1 | 2026-09-11 | M | n/a dependabot | — | — | — | 0 |
| TokenSheriff | 742 | build(deps): bump actions/setup-java from 6.0.0 | 2026-09-14 | M | n/a dependabot | — | — | — | 0 |
| API-Sheriff | 241 | test(edge): replace fixed wall-clock awaits with | 2026-09-01 | M | deficit | reviewed+ref | reviewed | n | 0 |
| API-Sheriff | 243 | test(edge): diagnose macOS-local live-Vert.x loo | 2026-09-02 | M | deficit | reviewed | reviewed+ref | n | 5 |
| API-Sheriff | 246 | feat(config): make application and management co | 2026-09-02 | C | deficit | reviewed+ref | REFUSED:size | n | 8 |
| API-Sheriff | 247 | feat(config): make application and management co | 2026-09-02 | C | deficit | reviewed+ref | REFUSED:size | n | 15 |
| API-Sheriff | 248 | feat(config): make application and management co | 2026-09-02 | M | deficit | reviewed | REFUSED:size | n | 9 |
| API-Sheriff | 254 | feat(config): allow a single env var to supply a | 2026-09-03 | M | deficit | reviewed | REFUSED:quota | n | 1 |
| API-Sheriff | 255 | fix(test): loopback-bind test listeners and land | 2026-09-03 | M | deficit | reviewed+ref | reviewed+ref | n | 47 |
| API-Sheriff | 257 | docs(adr): record the pre-boot health probe answ | 2026-09-03 | M | deficit | reviewed | reviewed | n | 2 |
| API-Sheriff | 263 | chore(deps): Bump anthropics/claude-code-action | 2026-09-04 | M | n/a dependabot | — | — | — | 0 |
| API-Sheriff | 267 | feat(config): raise broad trusted-proxy warning | 2026-09-04 | M | deficit | reviewed | REFUSED:quota | n | 2 |
| API-Sheriff | 268 | feat(tls): make upstream hostname verification c | 2026-09-07 | M | deficit | reviewed | REFUSED:size | n | 5 |
| API-Sheriff | 272 | feat(tls): make JWKS back-channel hostname verif | 2026-09-07 | M | deficit | reviewed+ref | REFUSED:quota | n | 4 |
| API-Sheriff | 282 | test(bff): force the near-expiry refresh and cov | 2026-09-09 | M | deficit | reviewed | REFUSED:quota | n | 6 |
| API-Sheriff | 283 | feat(tls): audit resolved TLS and trust source, | 2026-09-09 | M | deficit | reviewed | REFUSED:quota | n | 6 |
| API-Sheriff | 284 | fix(bff-cookie): restore browser-safe posture an | 2026-09-09 | M | deficit | reviewed+ref | REFUSED:quota | n | 9 |
| API-Sheriff | 286 | feat(tls): refuse incoherent TLS combinations on | 2026-09-10 | M | deficit | reviewed+ref | REFUSED:size | n | 11 |
| API-Sheriff | 287 | feat(bff-cookie): settle cookie-mode refresh via | 2026-09-10 | C | deficit | reviewed+ref | REFUSED:size | n | 7 |
| API-Sheriff | 288 | feat(bff-cookie): settle cookie-mode refresh via | 2026-09-10 | M | unassessable-no-baseline | REFUSED:rate | REFUSED:size | n | 0 |
| API-Sheriff | 293 | fix(build-parent): repair main and let the examp | 2026-09-11 | M | deficit | reviewed+ref | reviewed+ref | n | 2 |
| API-Sheriff | 296 | chore(deps): Bump quarkus/ubi9-quarkus-micro-ima | 2026-09-11 | M | n/a dependabot | — | — | — | 0 |
| API-Sheriff | 297 | chore(deps): Bump quarkus/quarkus-distroless-ima | 2026-09-11 | M | n/a dependabot | — | — | — | 0 |
| API-Sheriff | 298 | chore(deps): Bump anthropics/claude-code-action | 2026-09-11 | M | n/a dependabot | — | — | — | 0 |
| API-Sheriff | 299 | chore(release): point the version-bearing conten | 2026-09-11 | M | deficit | reviewed+ref | reviewed+ref | n | 1 |
| API-Sheriff | 300 | chore: update cui-quarkus-parent from 1.7.3 to 1 | 2026-09-11 | M | unassessable-no-baseline | — | — | n | 0 |
