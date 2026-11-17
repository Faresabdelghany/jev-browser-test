# A/B: two versions of the runner

1 spec(s) x 10 repeat(s) per arm, interleaved; arm A with the runner at `runs/old-3983b35/scripts/run_test.py`, arm B with this checkout's runner. 2026-11-17T14:00:25

| spec | A ended in | B ended in | moved | confidence A | B | delta | requests A / B | wall A / B (s) |
|---|---|---|---|---:|---:|---:|---:|---:|
| exp-shadow-mdn-chrome | goal_reached x10 | goal_reached x10 | no | 0.61 | 0.51 | -0.105 ⚠ | 5 / 5 | 4.0 / 3.8 |

**0 spec(s) ended differently in every run, 0 in some runs, 1 lost more than 0.05 of median decision confidence, 0 could not be compared.**

Not the same as measured: read each moved spec before merging the change. A spec that moved in every run is the change's doing; one that moved in some runs wants more repeats (run it alone with `--repeat 10`) before it means anything. Open the two arms' traces of a moved spec side by side: the step where the operations differ is where to look.
