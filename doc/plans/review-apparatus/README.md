# review-apparatus

Plans staged for standalone execution from the `review-apparatus` epic.

**Theme:** the reliability of automated PR review — reviewer participation, comment retrieval,
triage, and the signals that report whether a review actually happened.

Execution contract: `Skill: cloud-plan-lane` (see [`../README.md`](../README.md)).

## Audit of the landed plans

Every plan in this epic that has run carries two further documents alongside its `plan.md` and its
run report:

| File | What it holds |
|---|---|
| `verification.md` | Ground truth: each deliverable's *Done when* checked against the tree, an audit of every load-bearing claim the run report makes, and the correctness, completeness and out-of-scope reviews. Each carries an `## Adversarial review` section recording a second, independent re-derivation. |
| `gaps.md` | What the verification found still open, written as executable tasks — severity, the sites, the evidence, the fix, and an observable *done when*. |

The audit's own findings are staged as the **`5NN-` plan series** in this directory. Those plans
carry the gaps forward grouped by the mechanism they belong to rather than by the plan that
surfaced them, so one seam is repaired once:

| Plan | Seam |
|---|---|
| `500` | Participation credit, anchored to the commit being merged |
| `510` | Refusal and decline accounting, and the contract that describes it |
| `520` | The deficit signal and the comparison grade — telling "nobody reviewed" from "reviewed clean" |
| `530` | CI dispatch enforcement, the exit-code convention, and the envelope contract |
| `540` | What finalize asserts when a plan ends — the landing message and the foreign-PR gate |
| `550` | The review-comment round trip — the noise pre-filter, the reply marker, the agent block |
| `560` | The instruments that measure our own gates |
| `570` | The epic's records, which carry the defect the epic is named after |

`500` and `510` contend on one seam and MUST NOT run concurrently. `560` does **not** add a
§ "Consumers" row: it **rewrites the existing `review_gate_delta assess` row** — its D3 replaces that
row's "two independent implementations" claim — in the same table `500` D3 and `510` D2 each add a
new row to. An existing-row edit against two row insertions is a textual merge risk in one table
rather than an ownership question, but do not run `560` alongside either without checking that table.

### The shared-document split

`500` and `510` both edit
`marketplace/bundles/plan-marshall/skills/automatic-review/standards/bot-participation-contract.md`,
and so — in smaller, disjoint ways — do `520`, `560` and `570`. The table below names the passages
`500`, `510`, `560` and `570` write; `520`'s are not enumerated here, so check its own § Expected
surface rather than assuming the table is the whole set of editors. **For the passages below, this
table is the single authority for who writes what.** Each plan references it and restates
none of it — a split described in two documents is a split that goes stale in one of them, which is
exactly how this boundary was stated wrongly four times in succession.

| Passage | Gap id | Written by |
|---|---|---|
| The currency-rule scope sentence | `010 G2` | `500` |
| The "by definition an observation at the merge candidate" claim in § "Evidence for a bot that edits one comment in place" | `010 G3` | `500` |
| The § "Consumers" rows for fields `500` adds | — | `500` |
| The new bounded-gap section | — | `500` |
| The recorded answer on whether a timestamp-anchored completion arm is correct for a wait (D0) | — | `500` |
| The "stored finding, or … the noise sidecar" two-source arm | `010 G4` | `510` |
| The "edited in place (`updated_at` differs from `created_at`)" arm | `010 G4` | `510` |
| The "union of the stored-finding SHAs and the recorded sidecar SHAs" paragraphs, **including the "observation sidecar" naming inside them** | `010 G4` | `510` |
| The advance-disclosure sentence | `120 G6` | `510` |
| The § "Consumers" row for fields `510` adds | — | `510` |
| The § "The review-versus-gate delta" withholding guarantee, restated against the roster baseline | `130 G1` | `560` |
| The resolution axis (`rejected` / `suppressed`) added to § "The counting rule" | `130 G2` | `560` |
| The reviewer population the escape set is filtered to, in § "The review-versus-gate delta" | `130 G6` | `560` |
| The selection-effect sentence naming the measurable population, in § "The review-versus-gate delta" | `130 G4` | `560` |
| The **existing** § "Consumers" row for `review_gate_delta assess` — its "two independent implementations" claim, rewritten in place rather than added | `130 G7` | `560` |
| The instrument's declared scope (meta-project-instrumented only), in § "The review-versus-gate delta" | `130 G10` | `560` |
| The summary-card / trigger-acknowledgement insight, as a new subsection of § "Participation is not review quality" | `040 G14` | `570` |
| The charter-partition record — its deriving command, its two population sizes, and the statement that no measured cause partition of the historical absence corpus exists | `040 G16` | `570` |

**The one overlap, resolved here rather than in either plan.** `010 G4` § Where names
`bot-participation-contract.md:491-498` and `010 G11` § Where names `:493-500` — the same paragraphs.
The **paragraphs are `510`'s** (`G4` deletes the union claim that is their subject); `500` renames the
*code* artifact those paragraphs describe (`G11`) and does **not** edit them. Whichever plan runs
second finds the other half done: `510` describes the ledger under whatever name the code then
carries, and `500` reports the prose dependency instead of editing it.

Line numbers here are **leads** — re-derive each passage by its quoted text, not by its line.

A passage this table does not name is settled by neither plan: **report it, do not choose.**

**Three checks keep this from drifting, and each can fail.** Run them against `500` and `510` before
either is handed to a session. Check 1 is the one that matters: an earlier version tested only
whether a named passage *appeared* in the table, which is why it caught one of three known defects —
presence was never the question, **agreement with the `Written by` column** is.

1. **Every contract passage a plan names, it names in the role this table gives it.** For each
   passage row, find **every** occurrence of it in each plan — not the first; a first-occurrence test
   is satisfied by a legitimate deferral and never reaches the offending mention below it, which is a
   guard that cannot fire. The plan in `Written by` may name it freely. **Every occurrence in any
   other plan MUST carry the literal phrase `per the README table`** — that token, not a paraphrase,
   so the check is a grep rather than a judgement. A plan listing a passage in its § Expected surface,
   or under a *Done when* it must satisfy, is claiming to write it, so an unmarked mention there is a
   failure. Test the assignee, not the mention.
2. **Every contract passage a plan writes has a row here.** A passage a deliverable writes and this
   table does not name is owned by nobody — the defect that took four rounds to find. Read the
   deliverable bodies for this, not the Notes.
3. **Neither plan assigns ownership.** Grep both for `owns` / `owned by` / `belongs to` in a sentence
   that also names a contract passage. The only permitted hit is a pointer *to this table* naming no
   passage. Any other hit is a second copy of the split, and a second copy is what goes stale.

Checks 1 and 2 are read against the **deliverable bodies and § Expected surface**, because that is
where every instance of this defect has actually lived. Phrases in the table are paraphrases; match
on the passage, not on the wording.

⛔ **The greps are aids; check 2 is the authority, and it is done by reading.** Do not infer from a
clean grep that the split is sound. One defect shape this boundary actually produced — a *Done when*
whose clause **covers** a deferred passage without **naming** it — escapes all three checks as
specified, because there is no passage token to match and no ownership verb to find. It was caught by
reading, and only by reading.

No per-defect table of what-each-check-catches appears here on purpose. An earlier revision carried
one; a later verification refuted a row of it by re-running the checks against a scratch revert. A
claim about a heuristic's coverage is exactly as prone to going stale as the split it guards, and a
false coverage claim is worse than none — it licenses trusting a grep that did not look.

The same rule is why **neither plan counts the passages or sites of this shared document**: every
falsehood this boundary produced was a stale numeral. That set is re-derived from `010 gaps.md`
§ Where at the moment of the claim, and written down neither here nor there. The rule is scoped to
this document — a count elsewhere in a plan is fine where it names its members in the same breath,
so a reader can check it without leaving the sentence.
