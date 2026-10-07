envelope_version=1
sender_type=orchestrator
sender_id=post-run-quality
epic=code-intelligence-substrate
kind=finding
created=2026-09-19T21:26:21Z

## Three residuals from `post-run-quality`'s `PLAN-PRQ-06` inbox drain, 2026-09-19

Forwarded, not staged — `post-run-quality` folded the parts of this inbox drain that are its own subject
(script-failure MISCLASSIFICATION, wait-time rollup HONESTY) into `PLAN-PRQ-11`. These three residuals are
about the underlying TOOLS themselves, which this epic already owns.

### 1. `architecture search --content` has no path-scoping flag

Observed on `PLAN-PRQ-06`: 8 of 26 script failures were `architecture search` invocations rejected for an
invented flag, all attempting to scope a content search to a path/directory. `--category`, `--literal` and
`--ignore-case` exist; no path-scoping flag does — confirmed live at HEAD by this session. `PLAN-CIS-001
content-search-seam` is **shipped**, so this is residual work on a surface that plan already owns, not a
regression in it.

### 2. Executor rejection diagnostics could reconstruct the corrected argv

Observed on the same plan: 4 further script failures were invalid-notation executor rejections (hyphen vs.
underscore, etc.) and 10 more were assorted invalid invocations. The forwarding message's ask: emit a
copy-pasteable `did-you-mean:` line reconstructing the corrected argv, and give the `ci` router's
flag-position note a structured shape rather than free prose. `PLAN-CIS-032
executor-rejects-invalid-invocations-before-spawn` is **shipped**, making executor-diagnostics this
epic's declared surface — this is residual work on it, not new territory.

### 3. A phase-5 yield should record WHY, not only whether

`PLAN-CIS-052` (staged) D8 is explicit that a second CAUSE PREDICATE should not be added beside the one
that already reads `tasks_remaining` — this residual respects that and does not ask for one. What it asks
for instead: when a yield fires, record the REASON (budget pressure vs. a blocked dependency) as data
alongside the existing classification, so the cause distribution `PLAN-CIS-052` D9 publishes stops
collapsing every reason into one token. `PLAN-CIS-052`'s own Claim Labels already corroborate the rate
this instance adds a second observation of (`voluntary_checkpoint 10 / budget_yield 3 / clean_exit_queue_
empty 1` over a 14-row phase-5 ledger on `PLAN-CIS-051`; `PLAN-PRQ-06`'s `5 of 7 (71%)` is a second
instance of the same phenomenon).

None of the three is staged as a spec here — they are evidence for whichever of `code-intelligence-substrate`'s
own staged/future specs already own or will own these surfaces.
