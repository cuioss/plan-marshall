# PM-MCP carry-over — review-apparatus live corpus

Operator decision (2026-09-26): `plan-marshall-mcp` (PM-MCP, `/Users/oliver/git/plan-marshall-mcp`) replaces
BOTH the process prose AND the Python scripts of plan-marshall. **Nothing Python-bound carries.** What carries
is implementation-independent content — rules, invariants, classification semantics, data, and real-corpus
fixtures. This file extracts that content from the ten staged plans (`PLAN-PR-068` … `-077`), mapped to PM-MCP
requirement ids, as input for PM-MCP's requirements/specification. The ten plans are parked as
PM-MCP-superseded (see `epic.md` § 2026-09-26 and `logs/decision.log`).

## Method and population

- Population: the 10 staged specs, every roster deliverable incl. inline gates/amendments, bodies read in their
  source specs (`PLAN-PR-026/028/029/030/031/035/037/043/045/047/048/049/050/051/052/053`; `PLAN-PR-028` read
  from `.plan/archived-orchestrators/review-apparatus-26-09-21/plans/`).
- Mapping: grep of `plan-marshall-mcp/doc/requirements/*.adoc` + `doc/specification/*.adoc` at its HEAD
  `1db2fcb`. `gap` = no requirement states it; `partial` = a requirement touches it but not the rule; `covered`
  = PM-MCP already states it.
- Extraction was performed by two read-only sub-agents; rows are their derivation, not re-verified line by line.
- Excluded, deliberately: `PLAN-PR-002` (parked on foreign cuioss-organization#235) and `PLAN-PR-039`
  (successor `PLAN-PR-066` shipped) — foreign org CI config, independent of PM-MCP either way.

| Scope | Rows | Carry-over | none | Full/partial gap | Covered in full |
|---|---|---|---|---|---|
| 069 + 070 (WS-01) | 22 | 19 | 3 | 11 (+6 partial-clean maps) | 0 |
| 068, 071–077 (WS-03/04) | 55 | 52 | 3 | 40 | 7 |
| **Total** | **77** | **71** | **6** | **51** | **7** |

## ⛔ Contradictions to settle before PM-MCP freezes

1. **PM-MCP encodes the zero-findings = clean collapse.** Its `finalize.concurrent-wait` matrix routes
   `completed (0 open findings) → merge-gate`. That is exactly the defect this epic exists to remove (070.D2,
   071.D2/D3, 072.D2): a canned guide, an empty required population, and a real clean review are
   indistinguishable at that edge.
2. **Bot roster drift.** PM-MCP `default:automatic-review` names CodeRabbit/Copilot/Gemini/Codex; the live
   registry is `{coderabbit, cuioss-review-bot, sourcery}`.
3. **In-corpus conflict.** "Review skipped: No new commits" is a refusal in `PLAN-PR-043` D2 but explicitly
   NOT a refusal in `PLAN-PR-070` D0 (same structural slot as refusals). Settle before it becomes fixture data.

## Structural gaps (what PM-MCP must add)

- **Bot-registry schema** — refusal patterns, ETA patterns, rate class (hourly vs 7-day `hard_quota`),
  trigger verbs (incremental vs `full review`), trigger surface (which PR events a bot subscribes to),
  declared publish shape, structural caps.
- **Participation record schema** — covered-commit SHA (immutable, from the provider) separate from
  head-at-observation; roster provenance tri-state `never_asked | migrated | answered`; persisted at review time.
- **State vocabularies** — `bot_status` / `MergeGapClass` need `refused` (+ mode `size|weekly_quota|rate`),
  `stale`, `participated_but_empty`, `declined`, `absent`, `unsatisfiable`; empty-required-set is
  `vacuous|unestablished`, never satisfied.
- **FindingRecord** — separate resolve state from `response_transmitted`; transmit outcome
  `sent | not_sent(reason) | sent_unresolved | skipped(no address)`; `reviewed_commit_sha`, `bot_kind`, author.
- **Disposition vocabulary** — "subject accepted, detail corrected"; `rejected` split administrative vs
  refuted premise; bucket/detail contradiction refused at the write seam; documentary remedies recorded as
  commitments re-checked against the landed diff.
- **Measurement discipline** — every ratio names its population (anchored roster baseline, escape set matched
  to denominator, per-round reviewed tree, self-seeded share, split-PR follow).
- **Pre-wait cap gate** — refuse to enter the bot wait region when the diff exceeds a bot's structural cap.
- **Landings** — one per target plan, merge-commit SHA required, total `merge_state` mapping, ad-hoc shape.

## WS-01 — `PLAN-PR-069` refusal recognition / `PLAN-PR-070` participation

| Plan.D | Carry-over (implementation-free) | Kind | PM-MCP |
|---|---|---|---|
| 069.D0 | — re-grounding procedure | none | — |
| 069.D1 | Re-trigger target is selected from the unproven/gating required set, never by comment recency; reads state after the round's own fetch; a required bot that never published must still be selectable. Stale selector once burned the hourly quota. | invariant | **gap** (`finalize.review-escalate` `retry` names no target) |
| 069.D2 | Refusal recognised by derived rule (wrapper `<details><summary>⚠️ Action not completed</summary>`), not a literal list, with controls both directions. Bodies: CodeRabbit "Review rate limited", "Review limit reached", "Already reviewed the last commit…", "Review skipped / No new commits to review…"; Sourcery "you've used your own review budget of 250,000 diff characters for the last 7 days. You can request another review in 4 days and 1 hour", "your pull request is larger than the review limit of", "reached your weekly rate limit of". An unrecognised refusal never falls through to participation credit. | classification + data | **gap**; PM-SEC-1 partial |
| 069.D3 | Rate window = per-attempt interval × attempt ceiling, interval defaulted from the bot's registered rate. CodeRabbit 1 review/hour; operator policy ≥90 min, ≤10 waits. Every wait names its satisfying event and its producer, else fails fast "no satisfying event" (pr-agent listens on opened/reopened/ready_for_review/issue_comment, not `synchronize`). Scope the wait to the named bot. | invariant + data | PM-WF-8/PM-IMPL-4 partial; **gap** |
| 069.D4 | ETA extraction by general number+unit match ("Next included review available in N minutes"); detected-but-unparsed ⇒ `eta_unparsed`, never "no ETA". ETA is a floor to re-check (observed off ~2.4× / ~15×). Never trigger inside a closed window — a trigger extends it (20→48→52 min); close+reopen does not reset; window is org-scoped. Contention surfaces reason/holder/seconds_remaining. Required bot with no re-trigger path detected before awaiting. Cost: #1473 120h41m wall vs 6h20m worked. | invariant + data | PM-DIST-5 partial; **gap** |
| 069.D5 | Rate-limit/budget notices are transport failures classified at ingestion: never actionable, never participation. Windows differ ~3 orders (CodeRabbit ~1h, Sourcery 7d `hard_quota`); window > plan lifetime ⇒ `refused`/`unavailable`, never clean. | classification | PM-WF-13 Pred.2 partial; **gap** (`refused` member, finding exclusion) |
| 069.D6 | Classify a refusal by condition, not text: "Review rate limited" means `rate_limited` (wait) or `no_unreviewed_commit` (use `@coderabbitai full review`, not `review`). `full review` accepted in 10 s on the same HEAD after 4 refusals. | classification + data | **gap** |
| 069.D7 | An escalation class unreachable at default config is made reachable or deleted; unreachability derived over the configuration population. | invariant | PM-TEST-3 / PM-IMPL-5 |
| 069.D8 | Stored refusal carries a mode: Sourcery `size` (150,000 diff chars/PR, never expires, remedy smaller diff) vs `weekly_quota` (250,000/7d, remedy backoff). Fixture: CodeRabbit refused-only 22 PRs (20 rate, 2 size #1407 #1432); Sourcery quota 103, size 34, reviewed 40 of 181. | classification + fixture | **gap** |
| 069.D9 | Rate-limit and currency-blind paths compose: a quota-declined re-trigger leaves a stale credit standing. Fixture TokenSheriff#682 (~10.7h uncovered). | invariant + fixture | PM-WF-13 Pred.2 |
| 070.D0 | Participation marker anchored, never a bare substring (quoted PR text satisfies it); anchor only after sampling the live layout across several PRs with published sample size. CodeRabbit `recent_review_start` absent from live summary on #1477. 74/181 PRs carry a refusal in the summary comment (71 in-place edits, 54 beside real reviews). | classification + fixture | **gap**; PM-SEC-1 partial |
| 070.D1 | — duplicate of 069.D7 | none | — |
| 070.D2 | "Bot commented" admits four false classes: rate-limit meta-comment; prior-round comments re-served; green "Review completed" status placeholder ("No actionable comments were generated") over 0 reviews/0 inline/0 check-runs; thread acknowledgement. Completion comes from a review verdict object; a refusal outranks an edit timestamp. Inverse: a declared clean verdict ("No major issues detected", "No code suggestions found") IS a review. Uncleareable stale ⇒ `unsatisfiable`. Fixtures: 152/156 pr-agent guides canned; 21 PRs no baseline reviewer, 6 merged (#1380 #1406 #1407 #1438, API-Sheriff #288 #300). | classification + fixture | PM-WF-13 partial; **gap** + contradiction 1 |
| 070.D3 | An override of `absent` must cite an artifact proving the review happened (review object, inline comment, check-run); none ⇒ refused. | invariant | PM-WF-13 partial; **gap** |
| 070.D4 | Unregistered bot kind fails loud; override evidence rule covers every unproven-state member. | invariant | PM-EXT-7 + PM-WF-13 |
| 070.D5 | Currency test is unconditional; config chooses only strictness (exact SHA vs after last push). Latest comment predating HEAD ⇒ `unproven`. Covered commit stored separately from head-at-observation. First clean review with no commit permalink can never verify (known case). | invariant + fixture | PM-WF-13 partial; **gap** (covered-sha field) |
| 070.D6 | Classifier outputs at-head vs stale explicitly; "participated", "bot_completion finished" and "CI check green" prove three different things. | classification | PM-WF-9 partial; **gap** |
| 070.D7 | Declared publish shapes reconciled against observed; divergence is a finding. pr-agent declares unconditional Guide `issue_comment` + `inline` under /improve; absent inline ≠ non-participation. | invariant + data | **gap** |
| 070.D8 | Bot classification config read through one shared reader; unregistered token same disposition everywhere, never folded into ratio denominators. | invariant | PM-EXT-7 |
| 070.D9 | A malformed-parameter refusal names token, expected shape, one corrected example. | invariant | PM-WF-6 |
| 070.D10 | — argparse help mechanics | none | — |
| 070.D11 | — CLI doc drift, replaced by schemas | none | — |

## WS-03/04 — `PLAN-PR-068`, `-071` … `-077`

| Plan.D | Carry-over (implementation-free) | Kind | PM-MCP |
|---|---|---|---|
| 068.D0 | Attribute by author before any "unanswered" ratio (own comments corrupt both terms); each finding attributed to a mechanism or marked unattributable; HALT if <9 of 13 attribute. Data: 13 of 43 on #1167×4 #1158×2 #1198×6 #1195×1; corpus 97 of 493 unanswered, 11 unresolved (6 merged); all 7 Sourcery bodies + 3 pr-agent guides unanswered. | fixture + invariant | **gap**; fixture → PM-TEST-2 |
| 068.D1 | Responded marker stamped after successful reply, before resolve; resolve state persisted separately; resolve-only retry never re-sends; failed marker write reported. Named duplicate-delivery window (delivered-but-unstamped). | invariant | PM-WF-4 partial; **gap** |
| 068.D2 | Transmit has three named outcomes: sent / not-sent(reason) / sent-but-unresolved; unanswered set returned explicitly. | classification | **gap** |
| 068.D3 | No reply address ⇒ `skipped`, distinct from untransmitted. | classification | **gap** |
| 068.D4 | Unanswered-set tests derived from the real finding corpus. | fixture | PM-TEST-2 |
| 071.D0 | Reviewer populations derived from registry+config, never a hand bot→login list; required ≠ enabled roster; provenance `never_asked/migrated/answered`. | invariant | PM-EXT-7 partial; **gap** |
| 071.D1 | Per-bot reviewed-at-all classification persisted at review time keyed plan+PR+head_sha; post-merge reader treats absent/unreadable/malformed/stale as `indeterminate` (never clean), naming the case. | invariant | PM-WF-13 partial; **gap** |
| 071.D2 | Empty required population never renders positive: `vacuous` if answered, `unestablished` if never_asked/migrated; single-bot-contentless case tested; clean line names finding types and population behind its zero; defend or change `min_deficit=1`. | classification | **gap** (Pred.2 vacuously met) |
| 071.D3 | Quorum names its yield population; `done` cannot coexist with pending triage; per-bot split published. Fixtures #1425, #1473. | invariant + fixture | **gap** |
| 071.D4 | Operator strings ≤80 ASCII at worst-case expansion; empty roster ≠ reviewed-clean; never_asked renders "question never put"; awaitable refusal names governing config key + value. | invariant | PM-WF-5 partial |
| 071.D5 | Guards derived from behaviour (bucket union = member set, counts sum to roster). | invariant | covered: PM-TEST-3 |
| 071.D6 | A looped-back PR has no single reviewed tree; never synthesise one SHA; delta per round. Fixture #1386. | invariant + fixture | **gap** |
| 071.D7 | Coverage denominator anchored to configured roster baseline; omitted/empty/non-superset ⇒ withheld with cause; proper superset ⇒ `roster_narrowed`. | invariant | **gap** |
| 071.D8 | Rejected/suppressed are not escapes (count published); escape numerator restricted to roster reviewers. | invariant | **gap** |
| 071.D9 | Findings from all providers carry author, kind, bot_kind, reviewed_commit_sha; one implementation per shared predicate; instrument states its scope. | invariant | **gap** |
| 071.D10 | Classifier reads text where stored (quarantined raw body); tests from real stored records. | fixture | PM-SEC-1 / PM-TEST-2 partial |
| 072.D0 | Contradiction incidence published with records scanned and stores reached; zero = "none reachable". | invariant | **gap** |
| 072.D1 | Marker cleared on resolution change only with new reply detail; bare re-disposition of a transmitted finding refused; responded/responded_at is the idempotency key; one skip-reason vocabulary across providers. | invariant | PM-WF-4 partial; **gap** |
| 072.D2 | Per-bot states persisted at review time: participated / participated_but_empty / participated_stale / refused_structural / absent; a zero fetch is exactly one of no-review-covered-head / reviewed-clean / fetch-unreachable. | classification | PM-WF-9 partial; **gap** |
| 072.D3 | Bucket contradicting its detail text detected at the write seam; never coerced from prose. | invariant | PM-WF-6 partial; **gap** |
| 072.D4 | Disposition can say "subject accepted, detail corrected"; accept/reject/soften carry equal evidence obligation. | classification | **gap** |
| 073.D0 | — symbol re-grounding gate | none | — |
| 073.D1 | Landing asserted only on substantiated merge; `merge_state` total mapping merged→landed / open / closed / unknown / n/a, fallback "unclassified, no landing". | classification | PM-WF-15 partial |
| 073.D2 | One landing per target plan (key plan+kind); merge_state validated; `n/a` ≠ `unknown`; merge-commit SHA required; ad-hoc shape declared. | invariant | PM-WF-15 partial; **gap** |
| 073.D3 | Reader failure is an error, not an omission; PR body and retrospective carry the HEAD they describe. | invariant | PM-TOOL-4 partial; **gap** |
| 073.D4 | A posted disposition naming a remedy is re-checked against the landed diff before merge. | invariant | **gap** |
| 074.D0 | Foreign-PR gate clears only a positively classified population; classifies the named branch, not ambient HEAD; blocking set {pushed_no_pr, unpushed}. | invariant | **gap** |
| 074.D1 | Gate enforced at an executable seam; unsupported provider/timeout is a typed failure. | invariant | covered: PM-TOOL-4 / PM-WF-3 |
| 074.D2 | Review-coverage-vs-HEAD checked before the merge barrier; override explicit and recorded. | invariant | covered: PM-WF-13 |
| 074.D3 | — argparse doc drift | none | — |
| 074.D4 | A review bot is not a build check: CI timeout excludes bots and reports the partition; required_bots validated against installed caller workflows; on timeout check "not wired" before "slow". | classification | PM-WF-9 partial; **gap** |
| 074.D5 | Non-empty findings ⇒ `returned_with_findings`; `complete` only for clean. | classification | PM-WF-14 partial; **gap** |
| 074.D6 | Finding persistence is a caller-verified post-condition (N reported ⇒ N persisted). | invariant | covered: PM-WF-14 / PM-WF-5 |
| 074.D7 | One step record per manifest step id. | invariant | covered: PM-WF-13 |
| 074.D8 | Dirty path attributed to its writing step or pre-existing with proof. Data: uv.lock blamed on 5 steps, true cause dependabot #1417. | invariant | PM-IMPL-7 partial; **gap** |
| 074.D9 | Documentary triage remedy recorded as a commitment; an edit removing the claim surfaces it. | invariant | **gap** |
| 074.D8-a | `rejected` split administrative vs refuted; FP metric counts refuted only (one run +4/−3 at once). | classification | **gap** |
| 074.D10-a | Commitment reconcile reads a population incl. self-review, runs after its producers, reports size (order 9 vs producers 11/20/~40 ⇒ always empty). | invariant | PM-WF-13 partial; **gap** (produces-before-reads validation) |
| 074.D5-a | Detectors report measured reach and unreachable population; "closed-set literal beside its defining symbol" is its own class (4 of 5 escapes). | invariant + data | domain-extensions partial |
| 074.D8-b | Review chain reports its self-seeded share; terminating move = replace drifted restatement with a pointer. Data 14/51 (27%) over 19 firings, 5 chains. | data + invariant | **gap** |
| 074.D0-a | Six guard vacuity modes (positional indexing over named members; incomplete affirmative allowlist; self-defeating fix; unanchored pattern; control transcribing a subset of the live constant; non-vacuity firing only on total emptiness). | data (test checklist) | PM-TEST-3 partial |
| 075.D0 | Step record whose head is an ancestor of HEAD with changed inputs reads `stale`, never `done`. | invariant | covered: PM-WF-13 |
| 075.D1 | A channel that produced nothing says so; token totals marked settled vs floor by channel coverage. Data: 16/16 finalize steps no_evidence. | invariant | PM-WF-14 partial; **gap** |
| 075.D2 | — legacy log-pattern channel | none | — |
| 075.D3 | Coverage splits host vs foreign paths or states the exclusion; open decision whether read-only declared paths count. | invariant + decision | PM-IMPL-7 partial; **gap** |
| 076.D0 | Grade on actionable count, not store size; `clean` requires a required reviewer; vacuous split by provenance; roster omitted ≠ empty; participation measured / reviewed-silent / unmeasurable; persisted with populations. | classification | **gap** |
| 076.D1 | Per-reviewer FP metric discloses contradicting records, never a confident zero. | invariant | **gap** |
| 076.D2 | Actionable classification content- and reviewer-aware for issue comments; canned-empty guide stays meta. Data: pr-agent posts only issue_comments; cui-http #162; 152/156 canned. | classification + fixture | **gap** |
| 076.D3 | Split/superseded PR: findings and participation follow to successors. | invariant | **gap** |
| 076.D4 | Per-round share of actionable findings caused by the previous fix; uncomputable ≠ 0. Lead: #1501 2 of 3 rounds. | data + invariant | **gap** |
| 076.D5 | CodeRabbit folds overflow findings into the summary ("Outside diff range comments (N)") at the inline cap; yield must include them. #1539 measured 7, true 9. | data + fixture | **gap** |
| 077.D1 | Footprint split has one producer; consumers read, never re-derive. | invariant | covered: PM-IMPL-7 |
| 077.D2 | Refuse to enter the bot wait region when the diff exceeds a bot's structural cap; name the cap. Sourcery 150,000 chars / 300 files; GitHub 65536-char comment. 69.2% of one finalize's script wall time polled two bots unable to review a 4028-file diff. | data + invariant | **gap** |
| 077.D3 | If test/ and rest each clear the cap, name the test/ split as remedy. n=1: 179,695 = 129,556 test/ + 50,139 rest. | data + fixture | **gap** |
| 077.D4 | Under every cap ⇒ unchanged; the gate adds only a refusal path. | invariant | **gap** |

## Published

Consolidated with a 129-row Part B sweep of the 27 superseded specs into
`plan-marshall-mcp/doc/known-defects/review-apparatus-carry-over.md` (2026-09-26). That file is the
current, fuller version; this one stays as the Part A source.
