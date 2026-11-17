# A/B: --reuse-sessions --session-dir=runs/state/s4-sessions-public

4 spec(s) x 3 repeat(s) per arm, interleaved; arm A as the spec is, arm B with `--reuse-sessions --session-dir=runs/state/s4-sessions-public`. 2026-11-17T16:27:18

| spec | A ended in | B ended in | moved | confidence A | B | delta | requests A / B | wall A / B (s) |
|---|---|---|---|---:|---:|---:|---:|---:|
| shop-checkout | order_complete x3 | order_complete x3 | no | 0.99 | 0.99 | +0.005 | 10 / 10 | 5.1 / 5.1 |
| shop-add-second-item | bike_light_in_cart x3 | bike_light_in_cart x3 | no | 0.90 | 0.90 | +0.000 | 4 / 4 | 3.1 / 2.8 |
| shop-checkout-problem-account | form_error x3 | form_error x3 | no | 0.95 | 0.95 | +0.000 | 9 / 9 | 4.9 / 4.5 |
| shop-checkout-error-account | undetermined:blocked x3 | undetermined:blocked x3 | no | 0.89 | 0.94 | +0.050 | 10 / 10 | 5.2 / 5.0 |

**0 spec(s) ended differently in every run, 0 in some runs, 0 lost more than 0.05 of median decision confidence, 0 could not be compared.**

No spec moved and no confidence fell: over these specs the option changed nothing Jev did. That is evidence for making it the default, as strong as the specs are varied and the repeats many.
