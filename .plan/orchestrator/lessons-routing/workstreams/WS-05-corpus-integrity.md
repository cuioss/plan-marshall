# WS-05: manage-lessons corpus integrity

epic: lessons-routing
status: active

## Charter

Fix the defects in `manage-lessons` itself that were surfaced by running a real content sweep
(`lessons-handling-26-08-26-01`, 2026-08-26/27) against the live corpus — as opposed to defects
*in the corpus content*, which route to whichever sibling epic owns the subject.

⛔⛔ The worst finding: `manage-lessons remove` **destroyed** lesson `2026-08-25-05-001` while
returning `not_found` — the file was gone from both `list active` and `get` afterward, with **no
tombstone**, so the retirement has no audit record. This is strictly worse than the previously known
`remove` defect (which merely refuses): this one refuses **after** destroying, so a caller retrying
on `not_found` or reading it as nothing-happened is wrong unrecoverably. Unestablished: whether the
unlink precedes the metadata read, or the tombstone write fails after a successful unlink.

⛔ Five lessons from that sweep **survive and cannot be removed by any sanctioned verb** — all five
refused with `not_found` despite being live and readable: `19-001`, `19-003`, `23-13-001`,
`23-13-002`, `24-14-001`. Each subject is already carried forward in a routed inbox message, so no
content is lost, but the corpus itself cannot be cleaned of them through `manage-lessons`.

Also observed in the same run: 5 pre-existing superseded stubs are prunable via
`cleanup-superseded` (dry-run confirmed all 5 carry tombstones already) but were out of that drain's
scope — a candidate first task here rather than a finding to re-derive.

## In scope

- Root-causing and fixing the destroy-without-tombstone path in `remove`.
- Making the 5 stuck lessons removable (or explicitly, verifiably retired) through a sanctioned verb.
- Running the deferred `cleanup-superseded` pass on the 5 known-prunable stubs.
- Any other `manage-lessons` reliability defect a future content sweep surfaces — this workstream is
  the standing destination for tooling-shaped findings a sweep produces about the tool itself, not
  about lesson content.

## Out of scope

- Lesson **content** findings (those route to the sibling epic that owns the subject, per this
  epic's audience-classification mechanism — WS-01/WS-02).
- Building the routing/versioning mechanism (WS-01/WS-02/WS-03/WS-04 own that).

## Done when

`remove` cannot destroy a lesson without leaving a tombstone, the 5 stuck lessons from the
2026-08-26/27 sweep are resolved, and the 5 prunable superseded stubs are pruned.
