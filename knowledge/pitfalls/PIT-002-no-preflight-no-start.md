# PIT-002 No Preflight, No Start

- type: pitfall
- status: accepted
- trigger: substantial task starts without goal, plan, preflight, and known-risk scan.
- gate: `preflight.md` must contain `Gate: PASS` or `Gate: NEEDS-REVIEW`.
- mitigation: run `python -m auto_kb.cli preflight --task current --goal ...`.
