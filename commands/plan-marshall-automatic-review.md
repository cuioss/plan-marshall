---
description: "Total budget (seconds) for the main-context wait for the claimed rate window to expire, which follows a rate_window_await return; defaults to 3600 to match CodeRabbit's ~hourly rate-window reset. The wait is held by phase-6-finalize item 7a, not by this step, and it is the whole wait - item 7a dispatches this step again as soon as the window has expired. When the budget is spent with the window still open, item 7a releases the claim and proceeds as the rate_window_timeout reason does, which asks the operator. Only consulted when review_rate_window_await is true."
---

Load and run the `plan-marshall-automatic-review` skill instructions, then carry out its instructions using the user input below.

User input:

$ARGUMENTS
