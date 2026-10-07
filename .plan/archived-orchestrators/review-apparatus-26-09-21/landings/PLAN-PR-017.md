# Landing: PLAN-PR-017 — A workflow doc prescribes a flag no script declares

epic: review-apparatus · workstream: WS-03 · shipped 2026-08-11
cloud run: `cloud-runs/030-a-workflow-doc-prescribes-a-flag-no-script-declares/`
PR #1157 (`3c7a1cc80`)

> Landing analysis over the cloud-wave corpus. `report-01.md` is the run's claim; `verification.md`
> is ground truth. Where they disagree, verification wins.

**Verification verdict: `verified-with-gaps`.**

## What landed

All four deliverables landed and every symbol, test class, heading and doc edit the report names still
exists in the tree. The D1 malformed-flag rejection work is clean, well-tested, and correctly separated
from the evidence-admissibility filter. **The verification found no claim that was false at landing** —
three are overstated and one has since gone stale.

**Deliverables: 4 — 3 done, 1 partial (D0).**

## ⛔⛔ The plan shipped the very defect it exists to remove — and it is LIVE at HEAD

`030 G1`, severity **blocker**. The rewritten `execution-context.md` `--plan-id` cell replaced one
false universal with a **new** false claim: it tells every dispatched leaf that placing `--plan-id`
after a `ci` verb is an argparse rejection. Walking the live parser gives **ten** subcommands that
declare `--plan-id` themselves, **all `required=True`** — `pr create|edit|reply|thread-reply|
prepare-body|prepare-comment` and `issue create|comment|prepare-body|prepare-comment`.

Re-verified first-party at HEAD: `execution-context.md:23` still carries the sentence verbatim.
(Ten, not six — the verification corrected itself mid-document and the corrected figure is right.)

Claimed by **PLAN-PR-027** (ex-`530`) D1.

## D0's anti-curation mandate: met in form, not in substance

The widening *obligation* is derived per doc, but the doc *set* is a three-element literal, and that
literal cost the plan two real population members: `branch-cleanup-rereview.md` (loaded from inside the
barrier, carries **no** exit-code convention at all) and `create-pr.md` (a live swallow).

## Report claims the verification found overstated or stale

- "The ~35 other docs carrying the boilerplate convention are other phases/steps, out of scope" —
  **false as written**; re-verified: 20 narrow headings inside `phase-6-finalize` alone.
- D3 "publishes size (6 invocations, floor ≥ 4)" — the size reaches only assertion *failure* messages;
  a green run prints nothing.
- Null result "`--enabled-bots` absent from the whole tree" — true at `3c7a1cc8`, **false today**
  (`review_gate_delta.py:504` declares it, introduced by #1239), while
  `test_review_merge_invocation_contract.py:18,291` still assert no parser does.

## Gaps: 11 — 9 full, 2 partial, 0 uncovered

- **partial**: G3 (PLAN-PR-027 D2 covers the prose half; the derive-and-assert *test* clause is
  narrowed to `create-pr.md` only), G6 (PLAN-PR-027's out-of-scope excludes widening beyond
  `phase-6-finalize`/`automatic-review`, leaving three docs — including
  `workflow-pr-doctor/standards/automated-review-lifecycle.md`, squarely in this epic's review path —
  with **no** convention while invoking non-`manage-*` scripts)

## ⛔ Ownership collision — settle before emitting either plan

`030 G7` is claimed by **both** PLAN-PR-025 (ex-`510`) D3 and PLAN-PR-027 (ex-`530`) D5, for the same
three invocation sites. 510's own `Discharges` line names only `030 G5 / G8 / 120 G5`. **Sequence the
two, never pair them, and settle G7's owner first.**

## Standing facts

- ⭐⭐ **Both CI providers' `main()` returns 0 unconditionally.** `github_ops.py` and `gitlab_ops.py`
  each do dispatch → print → return 0 with no branch on `result['status']`, and `ci_base.output_error`
  prints `status: error` at `EXIT_SUCCESS` by design. **Any convention keyed on the exit code is
  structurally blind to every `ci` failure** — which is why `create-pr.md` Step 4 can mark itself
  `done` on a PR that does not exist. Verify a `ci` call by its payload `status`, never its exit code.
- ⛔ **A published null result is dated evidence, not a durable fact.** One of this run's has already
  gone stale. Re-run it at the moment of the claim.
