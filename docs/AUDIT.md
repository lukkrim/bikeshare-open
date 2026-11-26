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

Repo: https://github.com/ezzz-coder/DSC180A-ma6 at `3cb583d`, cloned beside this repo (not inside it).
Diff reviewed: `46184b0..3cb583d` (unmodified starter -> `cnt_roll_28` test + feature, four seeded faults, raw-hash test).
Run: the project `leakage-auditor` subagent (Claude Opus 5.5), with an instruction not to write into their repo. It ran
their code from `git archive` copies in temp dirs with this repo's pinned `.venv`; their `.claude/` hooks and settings
were never loaded. 8 tool calls, ~92 s.

**Verdict: all five checks pass** (target leakage, temporal ordering, calendar gaps, silent row loss, baselines).
Their 18 tests pass at HEAD; row loss is exactly the bound (728 -> 672 = 28 + 28*1); none of the 15 features is
forbidden or restates `cnt`. Their documented validation deltas for `cnt_roll_28` and the seeded-fault numbers
(fault 1 ridge valid 0.9252; fault 2 at 2011-09-17, 4724.43 vs 4605.29) reproduce exactly.

Findings that change a number:

| # | Where | Finding | Agree? |
|---|---|---|---|
| 1 | `docs/DECISIONS.md:10` | "Persistence (test R^2 0.510, MAE 840) is within 0.07 R^2 of ridge" was true for the starter (ridge 0.5833). After their `cnt_roll_28`, ridge test R^2 is 0.6239, so the gap is **0.114**, not 0.07. The MAE half still holds (840.1 vs 879.3). Fix: "0.11 below ridge on test R^2 (0.510 vs 0.624); still beats it on MAE". | **Agree.** Same staleness our own audit found in our DECISIONS.md (our finding 1); the number feeds their Exercise 5 argument directly. |

Checked and **not** a finding (worth recording because I expected one):

- Raising `LAG_WARMUP` to 28 did **not** corrupt their 7-day features. Their `b8d43da` wrote `cnt_lag_7 = shift(7)` and
  `cnt_roll_7 = shift(1).rolling(7)` with literal windows, avoiding the trap we hit in Exercise 1. The auditor re-coupled
  the windows in a temp copy as a counterfactual: `cnt_lag_7` became a 28-day lag, `cnt_roll_7 == cnt_roll_28` on every
  row, and valid R^2 moved to ridge 0.6619 / hgb 0.2961 (vs the correct 0.6839 / 0.2415). Their suite catches it
  (`2 failed`: `test_rolling_mean_excludes_today`, `test_lag_7_is_seven_calendar_days`). **Agree** that it is correct.
- Their hgb numbers differ from ours (valid 0.2415 vs our 0.2266) only because they kept the starter's `max_iter=300`
  and we use library defaults. Not an error on either side, but our two reports' hgb rows will not match.

Outside the auditor's scope, noted for my teammate (no number changes): their repo commits no `reports/` directory,
and Deliverable 1 grades `reports/metrics.json`.
