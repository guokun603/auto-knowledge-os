# Preflight Gate

A task must have `preflight.md` with `Gate: PASS` or `Gate: NEEDS-REVIEW`.

Preflight v2 must search existing knowledge and convert matched pitfalls into `Required Actions`. These actions are task-local obligations, not decorative search results.

Each required action must be marked as one of:

- `resolved`
- `needs-review`
- `rejected`

If related risk knowledge is found, preflight should include `Discussion Routing` with `discussion_required: yes` and a discussion path. This keeps uncertain conclusions in reviewable discussion instead of publishing them as facts.
