# Knowledge Closure Gate

No task may finish unless:

- the task quartet exists: `goal.md`, `plan.md`, `preflight.md`, and `log.md`;
- preflight is `Gate: PASS` or `Gate: NEEDS-REVIEW`;
- every Preflight v2 `Required Actions` item is marked `resolved`, `needs-review`, or `rejected`;
- at least one evidence file exists and contains non-whitespace content;
- no candidate knowledge for the task remains in `candidate`, `verified`, or `accepted` status.
