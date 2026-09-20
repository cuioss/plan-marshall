envelope_version=1
sender_type=plan
sender_id=findings-read-absent-plan-dir-returns-clean-zero
epic=truthful-signals
kind=candidate-lesson
created=2026-08-30T14:16:46Z

component=plan-marshall:automatic-review
category=bug
disposition=new
source_plan=findings-read-absent-plan-dir-returns-clean-zero
source_pr=1369
source_finding=5c47c6

# ingest ran once against a store that kept growing, and the two resulting errors did not cancel

## Provenance

Q-Gate finding `5c47c6` (6-finalize), resolved `taken_into_account` and **"Routed to the
truthful-signals epic"** — the remedy is a choice between two designs, which warrants its own plan.
No inbox message carried it. Sibling message L1 cites `5c47c6` by hash as a **caveat on its own
recall percentage**; it does not file the defect. This message does.

## The mechanism, in order

1. `manage-findings ingest` promoted `raw_input.body` to the top-level `body` field for the
   **10:33:38Z** batch (4 records).
2. It did **not** run again after the **00:06:51Z** or **11:41:01Z** `fetch_findings` batches
   (3 records, `body` empty). Ingest was invoked once and never re-invoked.
3. `review_gate_delta.is_status_summary` matches against `_BODY_FIELDS = (body, message)`. With
   `body` empty, the declared `review_body_summary_patterns` **cannot fire**.
4. `0e5217` — a pure **"Actionable comments posted: 1"** run summary — was therefore classified
   **ACTIONABLE**.

## Why "the errors cancelled out" is false here

This is the part worth carrying, because it is the exact reasoning trap:

- `5ba518` (**fixed**) stayed correctly classified as meta and left **both** numerator and
  denominator alone.
- `0e5217` (**unfixed**) entered **both**.

So the two misclassifications were not symmetric and did not offset. Consequences:

| Metric | Reported | True |
|---|---|---|
| `escapes_total` | 5 | 4 |
| unpartitioned escapes | 1 (`0e5217`) | 0 |
| `pct_resolved_as_fixed` | 80% | **100%** (5 claims, 5 fixed) |
| CodeRabbit `false_positives_count` | 1 | **0** |

CodeRabbit made **zero** wrong claims across 5 findings. A producer pre-filter gap charged it a
false positive — a defect in the ingest pipeline corrupting a **reviewer-quality** metric, which is
the wrong subject entirely.

On a PR that was otherwise measurable, this single phantom would have withheld `structural_share`
by itself — which is precisely the phantom-escape-on-every-PR failure the module docstring says its
carve-out prevents.

## Compounding with sibling message R4

R4 records that `ignore_patterns` do not cover CodeRabbit's re-review acknowledgment, so **every**
re-trigger files a spurious `pr-comment` finding. Phantoms enter the same population this metric
counts. The two gaps are independent in cause and additive in effect; fixing either alone leaves
the metric corruptible.

## Remedy (for the epic to scope) — two designs, pick one

1. **Re-run `ingest` after every `fetch_findings` batch**, before any metric consumes the store.
   Fixes the timing; leaves the field-lookup fragile.
2. **Have `is_status_summary` fall back to `raw_input.body`** when the promoted field is empty.
   Fixes the lookup; leaves the store partially un-promoted for every other consumer.

Whichever is chosen, add the check that would have caught this: a metric that consumes the
`pr-comment` store should refuse, or flag, when any record in its population carries an empty
promoted `body` alongside a non-empty `raw_input.body` — an un-ingested record is detectable
without knowing which consumer will be hurt by it.

## Deliberately preserved evidence

The review-retrospective artifact was **left as generated**, so the corrupted figure and its
correction are both on the record. Overwriting it would have erased the evidence for the finding.
