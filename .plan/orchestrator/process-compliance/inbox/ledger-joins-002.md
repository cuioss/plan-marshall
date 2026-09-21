envelope_version=1
sender_type=plan
sender_id=ledger-joins
epic=process-compliance
kind=finding
created=2026-09-19T13:04:17Z

# Follow-on: light-lane 2-refine capture requires pr_title (plan ledger-joins)

- What: After exempted `transition --completed 2-refine`, `phase_handshake capture --phase 2-refine` refuses with `pr_title_missing` (expects `status.metadata.pr_title` from phase-2-refine Step 13).
- Rule tension: `planning.md` light-lane Step 2c pairs capture with the pre-dispatch transition; the collapsed envelope (refine-no-loop + outline + derive) has not run yet, so no Step 13 pr_title exists. Capturing inline would mean authoring a refine artifact outside the envelope.
- Action taken under prior operator approval (exempt-and-continue): file this note, then `capture --override --reason` referencing this message, so the envelope entry verify sees a row. Override is script-contracted (`--override` + `--reason`), not workflow-documented; recorded here as an explicit exemption.
- Plan state unchanged: `ledger-joins` at `3-outline` window open, `2-refine` transitioned with bare exemption, metrics `2-refine -> 3-outline` stamped.
