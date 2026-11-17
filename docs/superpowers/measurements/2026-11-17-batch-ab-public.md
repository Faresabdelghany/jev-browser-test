# A/B: --batch-fields

5 spec(s) x 5 repeat(s) per arm, interleaved; arm A as the spec is, arm B with `--batch-fields`. 2026-11-17T16:10:58

| spec | A ended in | B ended in | moved | confidence A | B | delta | requests A / B | wall A / B (s) |
|---|---|---|---|---:|---:|---:|---:|---:|
| shop-checkout | order_complete x5 | order_complete x5 | no | 0.99 | 0.99 | -0.005 | 10 / 8 | 5.6 / 5.1 |
| shop-checkout-problem-account | form_error x5 | form_error x5 | no | 0.96 | 0.96 | +0.000 | 9 / 7 | 5.3 / 5.4 |
| shop-checkout-error-account | undetermined:blocked x5 | undetermined:blocked x5 | no | 0.92 | 0.95 | +0.030 | 10 / 8 | 6.2 / 5.4 |
| web-form-submit | form_submitted x5 | form_submitted x5 | no | 0.95 | 0.98 | +0.030 | 9 / 7 | 5.0 / 4.0 |
| login-logout | logged_out x5 | logged_out x5 | no | 0.98 | 0.98 | +0.005 | 6 / 5 | 5.0 / 4.6 |

**0 spec(s) ended differently in every run, 0 in some runs, 0 lost more than 0.05 of median decision confidence, 0 could not be compared.**

No spec moved and no confidence fell: over these specs the option changed nothing Jev did. That is evidence for making it the default, as strong as the specs are varied and the repeats many.
