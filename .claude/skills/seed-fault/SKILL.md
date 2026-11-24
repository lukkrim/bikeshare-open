---
name: seed-fault
description: Deliberately break the pipeline to prove a test catches it, capture the real failing output, restore, and log it in docs/SEEDED_FAULTS.md. Use when asked to seed, inject, or demonstrate a fault, or to check that a test can actually go red.
allowed-tools: Read, Edit, Bash(.venv/bin/python*), Bash(make*), Bash(git diff*), Bash(git status*), Bash(git checkout -- src/*), Bash(git checkout -- tests/*), Bash(git add*), Bash(git commit*)
---

# Current state

Working tree (must be clean before seeding):
!`git status --short`

Faults already logged:
!`grep -E '^## ' docs/SEEDED_FAULTS.md 2>/dev/null || echo "(none yet)"`

# Seed a fault: $ARGUMENTS

If `$ARGUMENTS` contains `--dry-run`, do steps 1-5 only: write nothing to
`docs/`, commit nothing, and report what you would have logged.

1. **Predict first.** In one sentence, name the test you expect to go red
   and why. If you cannot name one, say so: that is a gap in the suite,
   and the most useful outcome this skill can have.

2. **Confirm green.** Run `.venv/bin/python -m pytest tests/ -q`. If it
   is already red or the tree is dirty, stop: a fault seeded on a red
   suite proves nothing.

3. **Seed the smallest change that produces the fault.**
   - Code fault (`src/`, `tests/`): edit the file in place. The
     PostToolUse leakage hook may fire and report the failure; that is
     expected evidence, not something to fix.
   - Data fault (`data/raw/`): writes there are denied. Copy the CSV to a
     temp directory, change the copy, and point the code at it in-process
     (e.g. set `tests.test_contract.RAW` or `src.config.RAW` before
     running the test). Never touch the real file.

4. **Capture the real output.** Run
   `.venv/bin/python -m pytest tests/ -q --tb=line -p no:cacheprovider`
   and keep the exact output: which tests failed, with their assertion
   messages. Do not paraphrase or trim the assertion lines. If nothing
   went red, the prediction in step 1 was wrong: report that plainly.

5. **Restore and re-verify.** `git checkout -- <file>` for code faults
   (delete the temp copy for data faults). Run the suite again and confirm
   it is green and `git status --short` shows nothing from the fault.

6. **Log it** in `docs/SEEDED_FAULTS.md` (create it with a one-line
   header if missing) as a new `## N. <short name>` section:
   - **Fault:** the exact change (a 1-3 line diff).
   - **Predicted:** the test from step 1.
   - **Caught by:** the tests that actually failed.
   - **Output:** the captured output from step 4, in a fenced block.
   - **Fix:** how it was restored.

7. **Commit** only `docs/SEEDED_FAULTS.md`, as one commit:
   `Seeded fault N: <name> (caught by <test>; fixed by reverting <file>)`.
   No co-author trailer.

A fault that no test catches is a finding, not a failure of this skill.
Record it with "Caught by: nothing" and recommend the test that would.
