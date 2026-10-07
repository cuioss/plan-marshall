# WS-05: A pin that cannot fail is not a pin

epic: tooling-truthfulness

## Charter

Own the source-substring test pins that assert on a module's own text rather than on its behaviour.
One is confirmed — `test_script_performs_no_settings_io` calls `inspect.getsource` and asserts
strings are absent from its own module, setting no target, driving no project and touching no
filesystem, so it fails on an innocent rename and passes for any bypass not using those literals.
`inspect.getsource` appears across EIGHT test files, and whether the rest are legitimate uses is
unknown.

⛔ **Survey first, fix second.** The deliverable count is DERIVED from what the survey finds, not
declared up front — a plan that pre-commits to fixing eight sites before knowing how many are
defects would manufacture work.

⚠️ **This workstream may belong elsewhere.** The sibling `test-quality` epic already owns
anti-vacuity work (#1430 / #1443). If the survey finds a broad class, handing it there is the
correct outcome, not a failure of this epic.

The workstream closes when every `inspect.getsource` use is either behavioural, replaced, or carries
a positive account of why source inspection is the right instrument there.
