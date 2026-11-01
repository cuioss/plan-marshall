# Domain content (`pm-documents`): a sentence that states a guarantee, a count or a closed list is not checked against what enforces it

Severity: **medium**. Bundle: `pm-documents` (`ref-documentation`, and the documentation review rules a code review cites). Domain-bundle content, filed under the `ingest` ruling at any severity.
Source: 9 lessons, 8 from the API-Sheriff checkout and 1 from the TokenSheriff checkout, verbatim in `lessons-routing/lessons-archive/filed-live-blockers/API-Sheriff/` and `.../TokenSheriff/`. Not re-verified against the bundle; the gap was not searched for in `pm-documents` at this sweep.

## One failure class, nine sightings (two repositories)

| Lesson | The sentence that was wrong |
|---|---|
| API `2026-10-02-12-007` | Logout "revokes tokens at the identity provider"; production binds the seam to a no-op. Four sites carried the claim; each new text copied the old documents. |
| API `2026-10-12-07-011` | Counts and lists restated by hand ("twenty-six files", "both goals", "no X exists outside Y") went stale in the same change that altered the set. Five sightings, three checks. |
| API `2026-10-13-06-001` | A guard test's scope was narrowed; the prose saying what it catches was not re-read. |
| API `2026-10-13-06-002` | "Every token carries `cnf.jkt`" while one minting path is deliberately unbound. |
| API `2026-10-13-06-003` | A user-facing example kept four configuration keys the governing ADR lists as inert. |
| API `2026-10-13-14-004` | Documentation restating validator rules, written without a drift guard until a review bot asked. |
| API `2026-10-12-16-009` | An ADR sentence dropped the second of two guard conditions. |
| API `2026-10-12-16-010` | A security bound stated in requests where the limiter counts refreshes. |
| TokenSheriff `2026-10-31-12-006` | Docs said invalid configuration fails the boot / never restarts; the code validates only enabled issuers. |

## Rule the lessons converge on

- Before keeping or writing a sentence that says a control acts, open the enforcing code path (the producer that wires the seam, not another document) and check its exact scope: enabled or disabled, startup or runtime, which paths.
- A change that adds or removes a member of a set searches for every restatement of the set's size or membership, number words included.
- A documented list that mirrors a set defined in code gets a contract test, or is not written as a closed list.
- Do not write an absence claim ("no X exists outside Y") unless a test asserts it; delete a false one rather than qualify it.
- State a bound in the unit the mechanism limits.

## Ask

Check whether `ref-documentation` or the documentation review rules already carry this; if not, add it. The sibling `lessons-routing-057` (low, "declared once" is a claim about every consumer) is the same class.
