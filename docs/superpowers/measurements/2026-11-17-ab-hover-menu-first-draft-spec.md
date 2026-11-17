# A/B: --screenshots=all --hover

1 spec(s) x 5 repeat(s) per arm, interleaved; arm A as the spec is, arm B with `--screenshots=all --hover`. 2026-11-17T11:47:02

| spec | A ended in | B ended in | moved | confidence A | B | delta | requests A / B | wall A / B (s) |
|---|---|---|---|---:|---:|---:|---:|---:|
| exp-hover-menu-plain | undetermined:assert_failed x3, back_on_jquery_ui x1, undetermined:low_confidence x1 | undetermined:assert_failed x5 | some runs | 0.42 | 0.69 | +0.270 | 11 / 5 | 9.8 / 5.7 |

**0 spec(s) ended differently in every run, 1 in some runs, 0 lost more than 0.05 of median decision confidence, 0 could not be compared.**

Not safe to make the default as measured. A spec that moved in every run is the option's doing; one that moved in some runs wants more repeats (run it alone with `--repeat 10`) before it means anything. Open the two arms' traces of a moved spec side by side: the step where the operations differ is where to look.
