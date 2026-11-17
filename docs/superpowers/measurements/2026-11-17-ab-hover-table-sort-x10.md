# A/B: --hover

1 spec(s) x 10 repeat(s) per arm, interleaved; arm A as the spec is, arm B with `--hover`. 2026-11-17T11:45:45

| spec | A ended in | B ended in | moved | confidence A | B | delta | requests A / B | wall A / B (s) |
|---|---|---|---|---:|---:|---:|---:|---:|
| table-sort-due | undetermined:low_confidence x10 | undetermined:low_confidence x9, undetermined:blocked x1 | some runs | 0.32 | 0.37 | +0.055 | 4 / 4 | 4.5 / 4.5 |

**0 spec(s) ended differently in every run, 1 in some runs, 0 lost more than 0.05 of median decision confidence, 0 could not be compared.**

Not safe to make the default as measured. A spec that moved in every run is the option's doing; one that moved in some runs wants more repeats (run it alone with `--repeat 10`) before it means anything. Open the two arms' traces of a moved spec side by side: the step where the operations differ is where to look.
