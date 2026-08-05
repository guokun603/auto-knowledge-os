# Knowledge Closure Gate

No task may finish unless:

- the task quartet exists: `goal.md`, `plan.md`, `preflight.md`, and `log.md`;
- preflight is `Gate: PASS` or `Gate: NEEDS-REVIEW`;
- every Preflight v2 `Required Actions` item is marked `resolved`, `needs-review`, or `rejected`;
- at least one evidence file exists and contains non-whitespace content;
- no candidate knowledge for the task remains in `candidate` or `verified` status.

`accepted` is not a pending state. Marking a candidate `accepted` publishes it to `knowledge/`
immediately, so it leaves the gate by being written down, not by being waived. Only
`needs-review` and `rejected` close a candidate without publishing it.
