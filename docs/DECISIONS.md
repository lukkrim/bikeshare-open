# Decisions

One line per methodological decision: what you chose, why, and what it changed.
Agents append here via the `/new-feature` skill; you append here by hand.

- Exclude `casual`, `registered`: they sum to `cnt` exactly. Leaky model R^2 1.000 -> honest ridge 0.583.
- Exclude `cnt_2d_bfr`: a shipped 2-day lag we cannot test the alignment of. Build our own lags instead.
- Exclude `instant`, `yr`, `days_since_2011`: time indexes let a tree predict a flat constant past 2011 and a linear model extrapolate a trend we have no grounds for.
- Split 2011 / H1 2012 / H2 2012 by date. Test set touched once, after all feature work.
- Report mean and persistence baselines with every score. Persistence (test R^2 0.510, MAE 840) is within 0.07 R^2 of ridge and beats it on MAE; that caveat goes in the report.
- Trim CLAUDE.md 41 -> 35 lines: dropped per-target make descriptions (readable from Makefile), the `OK` module-output line (only relevant when writing a new module), and the GOOD/MISTY/BAD gotcha (visible in data and config.py). Kept every rule plus the 728-row, growth, and Sandy gotchas, each of which stops a specific wrong "fix".
- Step 2 data check (agent: Claude Opus 5.5, plan mode, CLAUDE.md loaded). All four facts were right and I re-checked each in pandas: 728 rows, 2011-01-03 to 2012-12-31; weather GOOD/MISTY/BAD = 463/245/20; one missing day, 2011-03-10; `casual`, `registered` flagged as leakage (sum == `cnt` on all 728 rows). No agent errors. Caveat: CLAUDE.md already states most of these facts, so this does not show the agent would find them unaided; it did compute them from the file rather than quoting.
- `cnt_2d_bfr` probe: the agent correctly called it a lag (known at prediction time, not leakage), excluded only because its alignment is unverified. It matches a 2-calendar-day lag wherever the source day is in the file; a row-based `shift(2)` would misalign across the 2011-03-10 gap.
- Keep same-day weather (`temp`, `atemp`, `hum`, `windspeed`, `weather`) but disclose: these are observed on the target day, so every score assumes a perfect next-day weather forecast. Stated in the report.
