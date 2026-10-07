# Corpus analysis — pr-agent vs CodeRabbit, six repositories

**Window: 2026-08-23 → 2026-08-30T20:16:39Z.** The lower bound is the previous corpus pass
([`2026-08-23-pr-agent-vs-coderabbit-corpus.md`](2026-08-23-pr-agent-vs-coderabbit-corpus.md)).
Read-only; no repository was changed.

⭐ **STAMP FOR THE NEXT PASS — use `2026-08-30T20:16:39Z` as the lower bound.**

## What this pass answers that the last one could not

The 2026-08-23 corpus measured **one repository** from the local `pr-comment.jsonl` substrate, and
carried a stated blind spot: nothing after PR #1134, because a `doc/plans/` lane run never writes
`.plan/`. It also measured a **dead configuration** — its last pr-agent PR was #1129, the
domain-routed charter landed at #1130, and `/improve` at #1334.

This pass measures the **live** configuration across **six repositories** from PR state itself, so
the charter and `/improve` are both inside the population for the first time.

## Instrument, and how it was validated

| Purpose | Tool |
|---|---|
| PR enumeration (date + label filters) | `gh pr list` — the `ci pr list` abstraction has no date, label, or limit filter and cannot express the query |
| Per-PR comment/review bodies | `gh api` (JSON) |

⛔ **The instrument was validated before use, because a prior session reported a foreign-repo
`ci pr comments` call returning `total: 48` with ZERO `issue_comment` rows — and pr-agent is
`issue_comment`-ONLY, so an instrument that dropped that class would score pr-agent zero *by
construction* in every foreign repo.**

**That anomaly is REFUTED.** Re-run on the same PR (cuioss/API-Sheriff#230), the sanctioned
abstraction returned `inline 39 / issue_comment 6 / review_body 3` — total 48, the *same* total —
and `gh api .../issues/230/comments` independently returned exactly **6**. The two instruments
agree. The earlier zero was the observer's **counting**, not a population exclusion. ⇒ The
foreign-targeting path is sound, and the open question folded onto PLAN-PR-040 D4 on 2026-08-29 is
**closed**.

⚠ **One classifier defect was found and corrected mid-analysis, and it moved the numbers.** The
first pass detected CodeRabbit presence only via `review_comments` and `reviews`, missing that
CodeRabbit **also posts `issue_comments`**. That understated its coverage (38 → 50 PRs) and
overstated the no-reviewer bucket (46 → 37). Every coverage figure below is post-correction. The
*yield* figures were never affected, as they read review bodies and inline comments only.

## Population

| Figure | Value |
|---|---:|
| Repositories | 6 |
| Candidate PRs (updated in window) | 160 |
| Excluded: `skip-bot-review` label | 63 |
| Collected | 97 |
| Excluded: opened before the lower bound | 4 |
| **Population — PRs opened in window** | **93** |

Restricting to PRs *opened* in the window is deliberate: a PR opened earlier carries reviews from
the previous era, which would contaminate a comparison of the current configuration.

## Coverage — who showed up

| Repository | PRs | pr-agent | CodeRabbit | Sourcery |
|---|---:|---:|---:|---:|
| plan-marshall | 31 | 29 | 29 | 30 |
| cui-http | 25 | 13 | 18 | 19 |
| TokenSheriff | 11 | 1 | 1 | 2 |
| API-Sheriff | 13 | 1 | 1 | 2 |
| cui-test-mockwebserver-junit5 | 7 | 0 | 1 | 2 |
| cui-test-juli-logger | 6 | 0 | 0 | 1 |
| **Total** | **93** | **44** | **50** | **56** |

**37 PRs drew no reviewer at all.** That is NOT a coverage defect: 12 are Dependabot automerge, and
all 25 others are automated `chore: update cui-java-parent` / `cuioss-organization workflows` version
bumps. ⭐ **No substantive PR in this corpus went unreviewed** — an earlier draft of this analysis
claimed two (cui-http #154, #157), and that claim was **my classifier bug, not a finding**.

## Yield — the headline

| Reviewer | Artefact | Volume | Substantive |
|---|---|---:|---:|
| **pr-agent** | `PR Reviewer Guide` | 44 | **2** |
| **pr-agent** | `/improve` suggestions | 24 | **0** |
| **CodeRabbit** | inline comments | 396 | — |
| **CodeRabbit** | reviews (self-declared actionable) | 243 | **217** |
| **Sourcery** | reviews | 61 | 18 were size refusals |

⛔⛔ **42 of pr-agent's 44 review guides are the identical ~200-byte canned table** carrying both
*"No major issues detected"* and *"No security concerns identified"*.

⭐ **That classification is corroborated on an axis independent of the parser.** Body length
partitions the 44 guides cleanly: 42 at ~200 bytes, one at 1001, one at 1798. The near-zero yield is
therefore a property of the output, not an artefact of how it was counted.

⛔ **`/improve` is now n=24, and every one is "No code suggestions found".** The pilot's prior
record was n=2, both empty — "not a verdict, but no longer an anecdote". At **24/24** it is a verdict.

### Paired recall — the measurement that matters

On the **35** PRs where CodeRabbit filed at least one actionable comment *and* pr-agent also posted
a guide:

> **pr-agent reported a finding on 1 of 35.**

## ⭐ The finding that stops this being "pr-agent is broken"

**Both substantive pr-agent findings are genuinely good, and one is a security defect CodeRabbit did
not file:**

- **API-Sheriff #230** — `.mvn/maven.config` defines both `-T1` and `-T1C`; the later flag wins,
  re-enabling parallel module builds and the test flakiness the project's own
  `build-gate-discipline.adoc` documents. A real, correctly-reasoned config defect.
- **cui-http #162** — a **fail-open** in the RFC 7239 `Forwarded` parser: a directive with
  whitespace before `=` bypasses malformed-directive detection and is treated as a valid extension
  instead of marking the header `UNRESOLVABLE`, so conflicting-source reconciliation does not fail
  closed. Filed under **Security concerns** — the one guide in 44 that populated that cell.

⇒ **The defect is VOLUME, not correctness.** pr-agent is not emitting noise that must be triaged
away; it is emitting almost nothing, and what it does emit is worth reading. Any remedy framed as
"improve pr-agent's precision" is aimed at the wrong axis.

## What is supportable, and what is not

✅ **Supportable.**

1. **A required reviewer whose output is canned-empty on 95% of PRs is a gate that cannot fail.**
   This is a claim about **coverage and roster**, not model quality — the same framing the epic's
   standing Watch already carries, now at a far larger n.
2. **`/improve` adds nothing at present**: 24 consecutive empty suggestion lists.
3. **The charter era is now measured.** The 2026-08-23 corpus's "measures a dead config" caveat is
   **discharged** — this population is entirely post-#1130 and post-#1334.

⛔ **NOT supportable, and deliberately not claimed.**

1. **CodeRabbit's 217 is SELF-DECLARED** (`Actionable comments posted: N` from its own review
   bodies), not adjudicated. The prior corpus measured CodeRabbit precision at **12.1% rejected**, so
   217 actionable is emphatically not 217 real defects. **The robust comparison is the
   zero-versus-nonzero shape and the 1-of-35 paired recall, never a 100:1 ratio.**
2. **pr-agent's 2 and CodeRabbit's 217 are different measures** — a parsed focus-area count versus a
   bot's own tally. They are not two readings of one instrument.
3. **This does not say "drop pr-agent".** It found a security bug CodeRabbit missed on cui-http #162.
   The standing #1335 counter-instance (Sourcery alone found `bug_risk`) is unretired.
4. **Coverage outside plan-marshall and cui-http is too thin to compare.** TokenSheriff and
   API-Sheriff contribute 1 reviewed PR each; the two `cui-test-*` repos contribute 0 and 1. Those
   rows report coverage, and support **no** quality claim in either direction.

## Consequences for staged work

- **PLAN-PR-025B (D7 — promote CodeRabbit to required)**: premise **strengthened**. Its evidence was
  three PRs; it is now 35 paired PRs across two repos with real volume. ⛔ D7's own instruction to
  *promote, never drop* is reinforced, not weakened, by the cui-http #162 finding.
- **PLAN-PR-026 (nobody-reviewed vs reviewed-clean are one signal)**: this is the population that
  sizes it. A canned-empty guide and no guide at all are indistinguishable to the gate, on 42 of 44.
- **PLAN-PR-040 D4**: the instrument question is **closed** — `ci pr comments` returns
  `issue_comment` on foreign repos; the prior zero was a counting error.
- ⛔ **Charter exhortation stays retired.** Nothing here reopens it: the output is not *wrong*, so
  more instruction text has no defect to correct. The lever remains roster and coverage.

## Reproduction

Population, per-repo tallies, and both corrections above are reproducible from the enumeration
(`gh pr list --search "updated:>=2026-08-23"`, `skip-bot-review` excluded, then `createdAt >=` the
bound) and the three per-PR endpoints (`issues/{n}/comments`, `pulls/{n}/comments`,
`pulls/{n}/reviews`). Bot identities were **derived from the corpus**, not assumed:
`cuioss-review-bot[bot]` = pr-agent, `coderabbitai[bot]` = CodeRabbit, `sourcery-ai[bot]` = Sourcery.
