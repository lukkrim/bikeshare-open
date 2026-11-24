# Audits

## Own repo: batch auditor (`agent/audit.py`, Part 4)

Command: `AUDIT_MODEL=claude-opus-5-5 .venv/bin/python agent/audit.py . --out reports/audit.jsonl`
(hosted Opus, not the default local `bikeshare-coder`; see REPORT.md Attribution). One repo, 66 s wall time,
`audited 1 repos; 0 flagged -> reports/audit.jsonl`. Verdict: leakage `none`, temporal_ok, baseline_reported,
reproducible, confidence high. Before the run, `check_identity` on the raw CSV flagged `casual + registered`
(max residual 5.5e-12), and on the current feature set it returned `clean`.

Findings and responses (each fix is its own commit after the audit-run commit):

| # | Finding | Agree? | Response |
|---|---|---|---|
| 1 | Ridge-vs-persistence bootstrap in DECISIONS.md predates `cnt_roll_28` (stale 0.583 / 947) | Yes, changes a number | Rerun on the current feature set; new DECISIONS line |
| 2 | `test_beats_the_mean_baseline` scores ridge on the **test** split on every `make test`, so the Stop hook looks at test every turn | Yes, it contradicts "test touched once" | Moved to validation, compared against `baseline_mean` as the name says |
| 3 | Makefile calls bare `python`; outside `.venv` it fails or runs unpinned versions | Yes, it can change the hgb row | `PYTHON` defaults to `.venv/bin/python` when present |
| 4 | README says 14 tests; there are 19 | Yes (doc only) | Fixed |
| 5 | Same-day weather is an oracle that persistence does not get | Partly: disclosed (DECISIONS), not leakage | Kept; REPORT.md presents model scores as an upper bound under perfect weather forecasts |

## Teammate repo: `/leakage-auditor` (Exercise 3)

_To do._
