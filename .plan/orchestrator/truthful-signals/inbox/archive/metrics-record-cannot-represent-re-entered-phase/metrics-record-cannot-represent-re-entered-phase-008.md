envelope_version=1
sender_type=plan
sender_id=metrics-record-cannot-represent-re-entered-phase
epic=truthful-signals
kind=candidate-lesson
created=2026-08-09T21:04:23Z

# Candidate lesson: "COMPLETE and CLOSED" is a claim about a population — and the declared blind spot that made it honest

**Source**: Q-Gate finding `a9d5ab` (3-outline), resolved `taken_into_account`, severity `error`
**Defect class**: volume-read-as-coverage / vacuous-authority
**Theme fit**: confident-signal-hides-a-caveat

## The finding

Deliverable 1 declared its consumer survey **COMPLETE and CLOSED**, stating there was no remaining
sweep-it-at-execute-time instruction for the partiality keys or the ledger columns.

Operationalizing that claim as an actual content query falsified it.
`architecture search --content --pattern _parse_dispatch_boundary_file` returned 4 files over
clean coverage (`files_scanned: 4179`, `unreadable: 0`, `truncated: false`, `elided: empty`).
Affected files listed three of them. **The fourth appeared in NO deliverable.**

And it was not an incidental mention: it held `TestParseDispatchBoundaryFile` with four in-process
tests calling the changed function directly, including `test_malformed_rows_skipped`, which drives
legacy five-column rows through **the exact `except ValueError, IndexError` branch that
deliverable 1 rewrites**. So D1's success criterion — "the reader still parses a legacy five-column
row and reports its four appended columns as unmeasured rather than as 0" — could not be verified
while its closest existing test sat outside the change set.

## The two remedies, and why the second one is the lesson

The primary remedy (add the file) was applied. But the resolution went further and replaced the
**COMPLETE-and-CLOSED prose with a published-population table**, naming per surface: the query
run, the result set, the coverage fields, and — the part worth copying —

> **one DECLARED BLIND SPOT: `.claude/skills/audit-archived-plan-retrospectives` is not
> inventory-crawled, so it was hand-swept, and phase-5 must re-read it rather than trust that row.**

That is the honest shape. `architecture search --content` is inventory-scoped: a zero result is a
trustworthy *"not in any inventoried file"*, never *"not in the tree"*. `.claude/**` sits outside
the crawl. A survey that runs the query and reports "closed" has silently converted an
inventory-scoped negative into a tree-wide one.

The same treatment was propagated to the two peer closure claims by symmetric-peer audit, and
deliverable 2 gained its own published population table plus a verified negative.

## Candidate rule

> "COMPLETE", "CLOSED", "exhaustive", "all consumers" are claims about a POPULATION. Never assert
> one in prose. Publish the table: the query, the result set, the coverage fields
> (`files_scanned` / `unreadable` / `truncated` / `elided`), and every surface the query cannot
> reach, as a DECLARED BLIND SPOT with the follow-up obligation named.

> A survey whose instrument is inventory-scoped must state the scope boundary in the same breath
> as the result. `.claude/**`, `.github/**`, and any `.gitignore`-excluded tree are outside
> `architecture search --content` and must be hand-swept and labelled as such.

Cross-reference: this is the concrete, well-handled instance of the epic's standing
"a reviewer's list of call sites is a SAMPLE, not an enumeration" rule.
