# A/B: --shadow-dom

1 spec(s) x 5 repeat(s) per arm, interleaved; arm A as the spec is, arm B with `--shadow-dom`. 2026-11-17T11:43:11

| spec | A ended in | B ended in | moved | confidence A | B | delta | requests A / B | wall A / B (s) |
|---|---|---|---|---:|---:|---:|---:|---:|
| exp-shadow-mdn-chrome | undetermined:done_unverified x5 | goal_reached x5 | **yes, every run** | 0.53 | 0.56 | +0.030 | 6 / 5 | 4.4 / 3.6 |

**1 spec(s) ended differently in every run, 0 in some runs, 0 lost more than 0.05 of median decision confidence, 0 could not be compared.**

Not safe to make the default as measured. A spec that moved in every run is the option's doing; one that moved in some runs wants more repeats (run it alone with `--repeat 10`) before it means anything. Open the two arms' traces of a moved spec side by side: the step where the operations differ is where to look.
