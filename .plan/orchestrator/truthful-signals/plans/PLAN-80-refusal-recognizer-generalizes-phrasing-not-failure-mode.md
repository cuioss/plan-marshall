# PLAN-80: The Bot-Agnostic Refusal Recognizer Generalizes One Bot's PHRASING, Not The Failure Mode

epic: truthful-signals
workstream: WS-01

> Staged 2026-07-27 from an operator-relayed third-party analysis of PR #1014. **The third-party text
> was treated as a lead and every load-bearing claim was re-verified first-party**; one claim was
> sharpened, one reframed, and one finding the analysis missed is recorded below. The originating
> question — *"46 files sounds like severe coupling, is this still in place for the other bots?"* —
> resolved to **no**, and the real defect is elsewhere.

## Objective

`_is_rate_limit_notice` exists so ANY reviewer bot's "I could not review this" notice is dropped as
noise rather than stored as a finding. It was built as a deliberate generalization of the
CodeRabbit-specific detector. **It generalizes CodeRabbit's vocabulary, not the class of refusal** —
so Sourcery's real refusal on #1014 was stored as an actionable finding and had to be hand-triaged.
Make the recognizer key on the *event* (a bot declined to review) rather than on one bot's phrasing.

## ⚠ The coupling premise is REFUTED — record this so it is not re-raised

The relayed claim of *"live machinery across 46 files"* for Gemini was a **raw string-hit count, not
coupling**, and the third-party analysis corrected itself on this point. Verified independently:

- OBSERVED — the bot layer is genuinely data-driven. `bot_registry.py` derives `bot_kinds()`, the
  login→kind map, re-review strategies, trigger comments and the `--bot-kind` argparse choices from
  `standards/{bot_kind}.md`. **Adding or retiring a bot is a data edit**, which is exactly why
  PLAN-70's D1 found retirement was a pure data deletion.
- **⇒ There is no broad per-bot coupling, and no plan should be scoped against one.** The relayed
  per-bot hit-count table (coderabbit 463 hits / sourcery 228 / pr-agent 131) is **not** evidence of
  coupling; those are overwhelmingly docstrings and standards prose. Do not re-derive it as a defect.

**This refutation is itself the epic's theme in miniature**: a large, alarming number that measures
nothing load-bearing. The one real coupling is small and specific — below.

## ⚠ Mechanism — OBSERVED, verified first-party at HEAD

All in `workflow-integration-github/scripts/_github_pr.py`.

### The one genuine per-bot coupling

- OBSERVED — `_CODERABBIT_BOT_LOGINS` (`:55`), `_CODERABBIT_RATE_LIMIT_MARKERS` (`:56`),
  `_is_coderabbit_rate_limit_notice` (`:73`), `_detect_coderabbit_rate_limited` (`:89`), consumed at
  `:661`. This is per-bot logic keyed to one bot **by login literal**, not registry-derived — the only
  such island, and it is the bot with working precision.

### The generic recognizer cannot see a comparative refusal

- OBSERVED — `_is_rate_limit_notice` (`:183-203`) returns
  `has_exceeded and has_shape`.
- OBSERVED — `_RATE_LIMIT_EXCEEDED_MARKERS` (`:146-161`) requires a **notice-voiced past-tense verb**:
  `exceeded|reached|hit`. The comment at `:150-152` states this deliberately excludes `exceeds` /
  `may exceed` as "review voice".
- OBSERVED — Sourcery's actual refusal on #1014 was:
  `"your pull request is larger than the review limit of 150000 diff characters"` — a **one-line
  comparative**, with no past-tense verb and no notice shape.
- **OBSERVED, executed against the live regexes**: all three exceeded-markers return `False`, so
  `has_exceeded = False` and the `and` **short-circuits before the shape check is even reached**.
  *(Sharpening the lead, which described it as failing both conditions — it fails the first, and that
  alone is decisive. The shape gap is real but secondary, and D1 should fix the cause, not the
  symptom.)*
- OBSERVED (consequence, operator-relayed) — the refusal was stored as finding `b1a9be` and required
  manual triage as "not actually a review". **CodeRabbit's equivalent would have been dropped
  automatically.**

### ⛔ The finding the relayed analysis MISSED — a vacuous-authority claim naming the very bot that fails

- OBSERVED — `_is_rate_limit_notice`'s own docstring (`:190-192`) asserts the recognizer is
  generalized *"so a CodeRabbit notice, **a Sourcery weekly-limit note**, and an arbitrary unknown
  bot's notice are all recognized by the same structural signature"*.
- **A real Sourcery refusal was NOT recognized.** The docstring names the exact case it fails.
- OBSERVED — `:147-149` calls the retained CodeRabbit sentence a **"strict superset"** of the
  CodeRabbit-exact detection. That claim is TRUE as written and MISLEADING in effect: it is a superset
  of *CodeRabbit's phrasing*, not of the *refusal class* — which is precisely how a bot-agnostic
  recognizer came to be single-bot-accurate.
- **Sixth instance of the vacuous-authority / defending-documentation family** (after 73, 74, 75, 76,
  78) — and the first where the documentation names the specific counter-example.

## ⭐ OPERATOR-DIRECTED FRAMING (2026-07-27): the marker belongs in the bot's DATA record

The operator asked whether the markers *"shouldn't be part of the description, like in
`automatic-review/standards/sourcery.md`"*. **Verified — yes, and the mechanism already exists and
already runs.**

- OBSERVED — `sourcery.md`'s registry block already declares an **`ignore_patterns`** list, used today
  to drop the Reviewer's-Guide header, the tips/commands summary, the marketing footer, the feedback
  prompt, and `"found 0 issues"`.
- OBSERVED — it is consumed as a **literal whole-comment substring match** at
  `workflow-integration-github/scripts/github_pr.py:253`:
  `any(marker in body for marker in bot_registry.ignore_patterns(bot_kind))`, documented at `:104` as
  the "PER-BOT layer" of the pre-filter.
- **⇒ Adding `"is larger than the review limit"` to `sourcery.md`'s `ignore_patterns` would have
  dropped this comment with ZERO code change.** The defect is not only that the shared regex is
  under-general — it is that **a per-bot fact was encoded in shared bot-agnostic code instead of the
  per-bot data record built for exactly this.**

This reframes the plan: **the data layer is the primary fix**, and the regex layer's real job is
narrower than it claims.

⚠ **The two layers are NOT redundant, and D1 must not collapse them carelessly.** `ignore_patterns`
is per-bot and keyed on `bot_kind`, so it can only fire for a **registered** bot. `_is_rate_limit_notice`
is author-independent and is the only thing that could catch an **unknown or renamed** bot's notice —
which is a real case this repo has hit before. The boundary to draw is *known bot → data record;
unknown bot → structural fallback*, not "delete one".

## ⭐ VERIFIED OBSERVED STRINGS + a NEW finding (orchestrator, 2026-07-27, via `ci pr comments --pr-number 1014`)

**Operator direction: keep Sourcery** — it is an *additional* reviewer, valuable even when it runs
intermittently. CodeRabbit and PR-Agent are the core reviewers. So the task is **not** to stop counting
Sourcery; it is to classify its refusals correctly so an intermittent reviewer's *absence* is never
mistaken for a *finding* or for *participation*.

### The real Sourcery refusal (verbatim, from the PR)

```
kind:   review_body            ← NOT issue_comment
author: sourcery-ai
body:   "Sorry @cuioss-oliver, your pull request is larger than the review limit of 150000 diff characters"
```

⚠ **Two structural facts that constrain D2:**
1. It arrives as a **`review_body`**, not an `issue_comment`. **D1 must confirm the `ignore_patterns`
   pre-filter is applied to `review_body` comments** — if it only filters issue comments, a data-record
   marker will not fire and the fix silently does nothing.
2. The body carries a **user handle** (`Sorry @cuioss-oliver,`) and a **configurable number**
   (`150000`). The stable substring is therefore
   **`your pull request is larger than the review limit of`** — handle-free and number-free. A marker
   including either would break for another user or another quota.

### ⛔ NEW FINDING — the CodeRabbit-SPECIFIC detector does NOT match CodeRabbit's current notice

Same PR carried a genuine CodeRabbit rate-limit notice: `> [!WARNING] > ## Review limit reached >
`@cuioss-oliver`, you've reached your PR review limit, so we couldn't start this review.`

**Executed against the live regexes:**

| Detector | Verdict on the real CodeRabbit notice |
|---|---|
| `_CODERABBIT_RATE_LIMIT_MARKERS` (needs BOTH) | **FAILS** — both markers miss. It requires `## Rate limit exceeded` + `exceeded the limit for the number of`; the current notice says **"Review limit reached"** / **"you've reached your PR review limit"** |
| generic `_is_rate_limit_notice` | **MATCHES** (`has_exceeded` and `has_shape` both true) |

**⇒ The narrative that "one bot has precision the others don't" is REFUTED in both directions.** The
bot-specific detector is **stale against its own bot's current output**, while the generic one catches
CodeRabbit and misses Sourcery. **Neither is a superset of the other** — each covers what the other
misses, which is the strongest possible argument for D1's layer-boundary work.

⚠ **Consequence D1 must chase: `_detect_coderabbit_rate_limited` (`:661`) is the wait-return
discriminator for the review poll loop, and it uses the STALE markers.** If it no longer fires,
finalize waits the full `review_bot_buffer_seconds` on every rate-limited CodeRabbit run instead of
returning early — a latent behaviour defect beyond misclassification. **Confirm/refute at `:661`.**

## Deliverables

### D1 — GATE: draw the layer boundary (mutates nothing)

Settle which layer owns what, and write it down where both are documented:

- **Per-bot, registered bot → the registry data record.** Every bot's known refusal string(s) live in
  its `standards/{bot_kind}.md` `ignore_patterns`. Adding a bot's refusal becomes a data edit, which
  is the property `bot_registry` already gives the rest of the bot layer.
- **Unknown / unregistered bot → the structural fallback**, whose scope should then be stated honestly
  as a *last-resort* recognizer, not as the general solution.
- ⚠ **Resist the tempting narrow fix.** Adding `is larger than` / `exceeds the limit` to the shared
  regex is enumerating one more bot's vocabulary in shared code — **that is what produced today's
  state**, and it would leave the next bot's phrasing to fail the same way. If D1 keeps a structural
  fallback, prefer keying on the *event* (a registered reviewer posted a comment with no actionable
  content — no file/line anchor, no suggestion, no diff reference) over more phrasings.
- Decide whether the `_CODERABBIT_*` island (`:55-109`) collapses into the data layer now — its
  `ignore_patterns` equivalent already exists — while preserving the `_detect_coderabbit_rate_limited`
  wait-return discriminator at `:661`, which is a *different* consumer with different semantics.

### D2 — the refusal markers move into the data records (operator-directed)

**Sourcery stays a configured reviewer.** Tighten its data record so every known failure mode is
classified as a refusal rather than a finding. Ready-to-apply content, grounded in the verified string
above — `ignore_patterns` matching is **literal substring**, so these are handle-free and number-free:

```yaml
ignore_patterns:
  # … existing five entries unchanged …
  - "your pull request is larger than the review limit of"   # diff-size refusal (OBSERVED #1014)
```

⚠ **Only ONE Sourcery failure string is OBSERVED.** The other three modes are known by *outcome*, not
by *text*: #1008 rate-limited, #1012 skipped, #607 weekly quota. **D1/D2 MUST NOT invent marker strings
for those** — inventing vocabulary is the exact defect this plan exists to fix, and a wrong literal in
`ignore_patterns` **silently drops real reviews**, which is strictly worse than the bug being fixed.
Capture each real string as it is next observed, or cover them structurally via D1's fallback. State
in the record which markers are observed and which modes remain uncovered.

**Also in scope — the same audit for every registered bot**, including **refreshing CodeRabbit's
markers**, which the finding above shows are stale against its current notice.

### D3 — the fallback's scope becomes truthful

Whatever D1 leaves in code, **correct the `:190-192` docstring** — it currently names *"a Sourcery
weekly-limit note"* as recognized, which is the exact case that failed. If D1 narrows the fallback to
unknown bots, say so there and at `:147-149`, where "strict superset" invites the reading that caused
this.

### D4 — tests

(a) **Sourcery's exact #1014 string** — `"your pull request is larger than the review limit of 150000
diff characters"` — pinned as the regression case and **verified to FAIL against current code**.
(b) CodeRabbit's notice still dropped (no regression on the working path).
(c) Mirror guard: a genuine review that merely *mentions* a rate limit in prose is still **stored**,
not dropped — precision is load-bearing in both layers.
(d) An **unknown-bot** notice still handled by whatever D1 leaves as the fallback — the case the data
layer structurally cannot cover.
(e) If D1 collapses the CodeRabbit island, `_detect_coderabbit_rate_limited`'s wait-return behaviour
at `:661` is unchanged.

Four deliverables (D1 a gate) — under the split guard. **Deliberately surgical**; the coupling premise
that would have made it large is refuted above.

## Expected Surface

- OBSERVED: `workflow-integration-github/scripts/_github_pr.py` — `:55-109` (CodeRabbit island),
  `:140-161` (`_RATE_LIMIT_PHRASE`, `_RATE_LIMIT_EXCEEDED_MARKERS`), `:163-181`
  (`_RATE_LIMIT_NOTICE_SHAPE_MARKERS`), `:183-203` (`_is_rate_limit_notice`, incl. the docstring
  claim at `:190-192`), consumer at `:661`.
- **OBSERVED (PRIMARY, operator-directed): `automatic-review/standards/{bot_kind}.md` registry blocks
  — the `ignore_patterns` list.** `sourcery.md` is the first target; audit every registered bot.
- OBSERVED: `workflow-integration-github/scripts/github_pr.py` — `:104` (layer documentation),
  `:202`, `:253` (the literal per-bot `ignore_patterns` match). The pre-filter contract lives here.
- OBSERVED: `automatic-review/scripts/bot_registry.py:247-251` / `:289-291` — the `ignore_patterns`
  accessor. **Read-only unless D1 adds a new registry field**; a plain list addition needs no change.
- HYPOTHESIS: `automatic-review/SKILL.md:106,112` — the documented registry-field list; update only
  if D1 adds a field (verify-at-outline).
- OBSERVED: tests under `test/plan-marshall/workflow-integration-github/**` and
  `test/plan-marshall/automatic-review/**` (registry-record tests).

**Disjointness:** confined to `workflow-integration-github`. Disjoint from PLAN-79
(`platform-runtime`/`manage-status`), PLAN-57, PLAN-75, PLAN-62, PLAN-76, PLAN-78.
⚠ **Adjacent to PLAN-72** — different file (`_github_pr.py` vs the `automatic-review` completeness
guard), so file-disjoint, but see sequencing.

## Dependencies and Sequencing

- ⚠ **SEQUENCE BEFORE PLAN-72 — this is a precondition, not merely a neighbour.** PLAN-72's D1 must
  decide whether a size-refused reviewer counts as *absent* or *excused*. **That decision is
  unimplementable while a refusal is indistinguishable from a finding**: you cannot count refusals you
  cannot recognize. Landing PLAN-80 first gives PLAN-72 a reliable refusal signal to build its quorum
  on. Queue position set accordingly (immediately ahead of PLAN-72).
- No other dependency; not gated on #1003.

## Notes

- Same PR (#1014) that produced PLAN-72's third failure mode and the stale-cache refutation. **Three
  distinct defects from one landing**, all theme-matched — worth noting when sizing future landing
  analyses: this one paid for itself several times over.
- **Provenance discipline applied**: the source was third-party chat text relayed by the operator. Per
  `plan-marshall:untrusted-ingestion`, it was treated as a lead — its coupling premise was refuted,
  its central claim confirmed and sharpened by executing the live regexes, and one finding it missed
  was added. **No ledger write took the relayed text at face value.**

## Write-Boundary

Repository source + tests only; NO `.plan/local/orchestrator/` writes. See
`persona-marshall-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
