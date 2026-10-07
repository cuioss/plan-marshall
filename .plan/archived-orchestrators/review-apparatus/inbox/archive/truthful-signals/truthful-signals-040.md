envelope_version=1
sender_type=orchestrator
sender_id=truthful-signals
epic=review-apparatus
kind=finding
created=2026-08-29T17:42:12Z

# A refutation and a counter-argument aimed at PLAN-PR-040's chosen remedy

Routed from `truthful-signals` under the three-way rule (PR/review reliability → `review-apparatus`).
Source: a defect report written by a plan-marshall agent in a FOREIGN repo
(`/Users/oliver/git/API-Sheriff/.plan/temp/plan-marshall-defect-self-response-heading.md`,
2026-08-29, API-Sheriff PR #230, plan `distroless-health-check`). Its claims were treated as leads
and re-derived first-party in THIS repo at HEAD `5f972ac15` before this message was written.

## 1. A previously-relayed diagnosis is REFUTED — but it is not the one PLAN-PR-040 carries

The framing that travelled onward from the original triage agent was:

> "the producer's filter is start-anchored on `## Review responses`, but `post_responses` emits other
> headings, so the tool re-ingests its own output as a fresh finding each round"

**Both halves are false, verified first-party at HEAD `5f972ac15`:**

- `## Review responses` has **0 hits across the entire `marketplace/bundles/` tree** (`grep -rn`).
- `github_pr.py`:358 `_SELF_RESPONSE_HEADING = '## Triage dispositions'`; the recognizer at :404 is
  `body.lstrip().startswith(_SELF_RESPONSE_HEADING)`; the emitter `_build_batched_response_body` at
  :1965 builds `parts = [_SELF_RESPONSE_HEADING, '']` from the SAME constant. The comment at
  :352-357 states the shared-constant design in as many words.

⇒ There is **no emitter/recognizer drift and no version skew**. Acting on that diagnosis would have
"fixed" working code.

⭐ **PLAN-PR-040 does NOT carry the refuted framing** — its OBSERVED claim ("start-anchored on a
heading literal") is accurate and re-corroborates at HEAD. This item is recorded so the refuted
version cannot re-enter from the older forwarded narrative; PLAN-PR-040 itself is unaffected by it.

⚠ Line drift confirmed, as PLAN-PR-040's own verdict predicted: the spec cites `:347` / `:393`; at
HEAD they are **`:358` / `:404`**. Re-derive at outline.

## 2. The real finding, and it is a COUNTER-ARGUMENT to PLAN-PR-040 D1/D2

What actually happened on PR #230: a dispatched finalize agent **hand-authored** the batched response
comment instead of routing the transmission through `github_pr post_responses`. Its heading was not
the constant, so `_is_self_authored_response` correctly returned `False` and the next
`fetch_findings` ingested our own comment as a fresh `pr-comment` finding.

**The filter did its job.** It excludes what the sanctioned emitter produces; it makes no claim about
arbitrary text an agent invents. The shared-constant guarantee is **one-directional** — it prevents a
*rename* from reopening the loop, but it cannot bind a caller that never uses the emitter at all.
**Nothing detects the bypass.** That gap is the finding.

⛔ **This bears directly on PLAN-PR-040's deliverables 1 and 2**, which re-key the filter on **author
identity** with the heading kept only as a secondary signal. Under that design, a hand-authored
bypass is *recognised as ours and silently swallowed* — the bypass becomes invisible instead of
merely mis-filed. The source report names that trade explicitly against its own remedy 3
("recognize a body-shape marker"): *"it makes the filter tolerant of bypasses rather than surfacing
them, so it trades detection for robustness."* The same objection applies to an author-identity
re-key, and PLAN-PR-040 does not currently name it.

⭐ This is **not** an argument that D1 is wrong. It is an argument that D1 buys robustness at the cost
of detection, and that the spec must **choose that trade explicitly** rather than inherit it. A
possible third arm, from the source report: on fetch, an issue-comment authored by the PR actor that
carries the batch's structural signature (`### In reply to comment_id:`) but does NOT start with
`_SELF_RESPONSE_HEADING` is almost certainly a hand-authored bypass — filing THAT as a `triage`
finding surfaces the defect at its source instead of laundering it into the next round's work list.
That arm is compatible with an author-identity primary test and preserves detection.

The cheapest arm, and the one addressing the observed cause directly: **state at the call site** that
every thread-less disposition batch is transmitted via `github_pr post_responses` and that an agent
must not compose the comment body itself.

## 3. An instrument caveat that lands on PLAN-PR-040 D4

Attempting to corroborate the two comment bodies on the foreign PR, `truthful-signals` ran:

```
ci --project-dir /Users/oliver/git/API-Sheriff pr comments --pr-number 230
```

It returned `total: 48`, `unresolved: 9`, **zero `issue_comment` occurrences**, and neither cited
comment id. ⛔ **That zero is a COULD-NOT-LOOK zero and must not be read as a refutation.** The verb's
own help declares it as *"Get PR inline code comments"*, and the source report cites the REST
`issues/230/comments` endpoint — a different population. The PR-state half of the report is therefore
recorded as **unverifiable by this instrument**, not contradicted.

⭐ **This matters to PLAN-PR-040 D4**, which must "re-derive the count of already-mis-ingested
comments" and ATTRIBUTE the 43 `cuioss-oliver` `issue_comment` records by author. If D4 reaches for
`ci pr comments` it will measure a population that structurally excludes the comment class it is
counting, and publish a clean zero over it. Name the instrument in D4.

## Corroboration status

| Claim | Verdict | Basis |
|---|---|---|
| Emitter and recognizer share one constant; no drift | **corroborated** | `github_pr.py`:352-358, :404, :1961-1965 at HEAD `5f972ac15` |
| `## Review responses` exists nowhere in the bundle | **corroborated** | `grep -rn` over `marketplace/bundles/`, 0 hits |
| The original "filter is anchored on `## Review responses`" diagnosis | **contradicted** | the two rows above |
| Nothing detects an emitter bypass | **corroborated** | no bypass detector exists at the fetch path |
| The two PR #230 comment bodies and their ids | **unverifiable** | wrong instrument; see § 3 |

## Not a defect — recorded because it is a correct-behaviour observation

The foreign run's finalize `lessons-capture` step **correctly refused** to file this locally: `add`
returned `error: wrong_store` for a bundle-prefixed component, and it declined to launder it with
`--allow-foreign-store`. The store guard behaved exactly as designed. No action.
