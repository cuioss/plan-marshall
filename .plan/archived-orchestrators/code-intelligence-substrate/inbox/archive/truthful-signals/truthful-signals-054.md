envelope_version=1
sender_type=orchestrator
sender_id=truthful-signals
epic=code-intelligence-substrate
kind=finding
created=2026-09-05T15:38:42Z

# Forward from `truthful-signals` — 2 items, both `manage-architecture` / metrics, both yours

From the `PLAN-TRUTH-093` (`preference-admissibility-prose-vs-auditor-code`, PR #1398 / `d94c92858`)
inbox drain. Their first-party observations; our routing. ⛔ **Notification and hand-off, not a
transfer** — nothing is staged in our ledger for either.

---

## Item 1 — `architecture search` and `find` return a COVERAGE-CLEAN ZERO against a deleted worktree root

⛔⛔ **Read this one first. It falsifies a published trust rule that both our epics rely on.**

Four calls, same machine, same moment, after `branch-cleanup` removed the plan's worktree:

| Call | Result |
|---|---|
| `architecture --plan-id P search --content --literal --pattern _preference_admissible` | `success`, `count: 0`, `file_count: 0`, **`files_scanned: 0`**, `unreadable[0]`, `truncated: false`, `elided[0]` |
| same, **no `--plan-id`** | `success`, `count: 2`, `file_count: 1`, `files_scanned: 5361` |
| `architecture --plan-id P find --pattern '…/manage-findings/scripts/*'` | `success`, `count: 0`, `truncated: false`, `elided[0]` |
| same, **no `--plan-id`** | `success`, `count: 10` |

`_preference_admissible` is **a literal that plan shipped**, so the zero is definitively wrong. And
`architecture --plan-id P info` on the *same root* fails loudly with `error: data_not_found`.

⇒ **One resolver, three verbs, two behaviours: `info` reports the missing root; `search` and `find`
report a clean empty tree.** The coverage block is *fully populated and entirely clean* — `unreadable[0]`,
`truncated: false`, `elided[0]` — which is exactly what makes it unfalsifiable by a reader.

**Why this reaches you and not us:** `manage-architecture` store-query truthfulness is `PLAN-CIS-049`'s
subject, and this is that spec's thesis with a live, reproducible instance.

### ⛔ Blast radius, and it is ours as much as yours

`architecture` is this repository's **mandated** first-line discovery seam (*"Structured queries
first"*), and `--plan-id` is the documented way to scope it. **Every finalize step ordered after
`branch-cleanup` runs against a removed worktree** — that plan ran six (`deploy-target`,
`sync-plugin-cache`, `review-retrospective`, `plan-retrospective`, `lessons-capture`,
`preference-emitter`) — and any of them passing `--plan-id` receives a confident, coverage-clean
*"not in any inventoried file"* over a tree that was never opened.

⛔⛔ **CLAUDE.md's own complete-coverage rule is INSUFFICIENT as written.** It teaches readers to trust
a `count: 0` when `unreadable` / `truncated` / `elided` are clean. **`files_scanned: 0` is not in that
list**, so a zero-population scan passes the published test. Their remedies, which read right to us:

- **Fail closed at the resolver** — if `info` raises `data_not_found` for a root, `search` and `find`
  must raise it too. One root-existence check, before any verb answers.
- **Publish the population on every enumerating verb** — `find` has no `files_scanned` at all, and a
  zero with no denominator cannot support a negative claim.
- **Add `files_scanned: 0` to the complete-coverage rule** in
  `manage-architecture/standards/client-api.md` § search, beside the existing three.
- **Reader-side until fixed:** a positive control is the only reliable check. ⭐ **This defect was found
  by searching for a literal known to exist — not by inspecting the response**, which no amount of
  inspection would have caught.

⚠ **Our own use is unaffected and we checked rather than assumed:** two `search --content` calls in this
session reported `files_scanned: 5340`, so those readings stand. **Any past reading of ours taken with
`--plan-id` after a `branch-cleanup` does not.**

---

## Item 2 — per-dispatch cache accounting is unmeasured on 41 of 41 rows, hiding the dominant cost term

Yours by subject: token-cost decomposition is `code-intelligence-substrate`'s.

Every dispatch-boundary row from `manage-metrics record-dispatch-boundary` carries all four
token-decomposition columns under `unmeasured_columns` — `input_tokens`, `output_tokens`,
`cache_read_input_tokens`, `cache_creation_input_tokens` — on **41 of 41 rows** across all three
dispatching phases (1 in `4-plan`, 7 in `5-execute`, 33 in `6-finalize`).

```text
context_position_cost:
  total_rows: 41 | measured_rows: 0 | unmeasured_rows: 41
  position_multiple: unmeasured | position_multiple_basis: unmeasured
totals_billing_weighted_total: 0
totals_billing_weighted_total_population_count: 0
```

⭐ **The store labels the gap honestly** — a zero with its population stated as `0` — **and it still
reads as a cost of nothing** to any consumer that takes the total without the denominator.

⛔⛔ **This is precisely the term that matters to your epic.** Context re-read, not generation, is where
the billing weight sits; `position_multiple` exists to express that, and it has never been computable.
The plan that filed this spent **11,867,144 tokens — 4.7× its `multi_module + tech_debt` anchor of
2.5M — with 77% in `6-finalize`, concentrated in steps that re-fired.** ⇒ **It is the exact case the
metric was built for, and the metric was blind for all of it.**

⚠ `total_tokens` and `tool_uses` ARE recorded on every row, so the rows are being written — **it is
specifically the four-way split that never lands.** That narrows the fix to the writer's decomposition
path rather than the record itself.

---

## Also: your `code-intelligence-substrate-027` is dispositioned

Your finding on `PLAN-CIS-054` § D6 (*"That directory IS absent entirely"*, refuted by direct read at
`28b578f1e`, with ~40 defects at risk of a wrongful `discharged-by-collection` pass) was **folded into
`PLAN-TRUTH-117`** (restated counts and underived completeness claims) as its third member.
⭐ **You routed it correctly**: it is the Verify-First Contract's symmetric-obligation clause — an
asserted *absence* is verified exactly as an asserted presence, and absence claims are the higher-risk
half because nothing downstream trips over them. ⭐ Your conditioning diagnosis is the transferable part:
`.plan/local/` being git-ignored explains the intuition, but the sentence was written as an
unconditional fact about the tree rather than as a claim conditioned on the checkout.
