# A/B: --settle=network

17 spec(s) x 5 repeat(s) per arm, interleaved; arm A as the spec is, arm B with `--settle=network`. 2026-11-17T16:57:28

| spec | A ended in | B ended in | moved | confidence A | B | delta | requests A / B | wall A / B (s) |
|---|---|---|---|---:|---:|---:|---:|---:|
| add-remove-elements | one_delete_left x5 | one_delete_left x5 | no | 0.95 | 0.96 | +0.010 | 5 / 5 | 3.7 / 3.6 |
| dynamic-controls | both_done x5 | both_done x5 | no | 0.84 | 0.80 | -0.040 | 11 / 11 | 9.6 / 9.1 |
| forgot-password | email_sent x5 | email_sent x5 | no | 1 | 1 | +0.000 | 4 / 4 | 3.5 / 3.4 |
| load-wait | loaded x5 | loaded x5 | no | 1 | 1 | +0.000 | 7 / 7 | 8.0 / 7.8 |
| login-logout | logged_out x5 | logged_out x5 | no | 0.98 | 0.98 | +0.000 | 6 / 6 | 4.7 / 4.3 |
| menu-random | all_entries x4, entry_missing x1 | all_entries x4, entry_missing x1 | no | - | - | - | 2 / 2 | 2.5 / 2.4 |
| modal-close | modal_closed x5 | modal_closed x5 | no | 0.72 | 0.71 | -0.010 | 4 / 4 | 3.3 / 3.4 |
| notify-random | action_successful x3, action_unsuccessful x2 | action_successful x3, action_unsuccessful x2 | no | 0.93 | 0.91 | -0.020 | 3 / 3 | 3.2 / 3.1 |
| shop-add-second-item | bike_light_in_cart x5 | bike_light_in_cart x5 | no | 0.91 | 0.90 | -0.015 | 4 / 4 | 3.0 / 2.9 |
| shop-checkout-error-account | undetermined:blocked x5 | undetermined:blocked x5 | no | 0.94 | 0.93 | -0.015 | 10 / 10 | 5.4 / 6.1 |
| shop-checkout-problem-account | form_error x5 | form_error x5 | no | 0.96 | 0.95 | -0.010 | 9 / 9 | 4.9 / 4.5 |
| shop-checkout | order_complete x5 | order_complete x5 | no | 0.99 | 0.99 | +0.000 | 10 / 10 | 5.2 / 4.8 |
| table-sort-due | undetermined:low_confidence x5 | undetermined:low_confidence x5 | no | 0.34 | 0.35 | +0.010 | 4 / 4 | 4.4 / 3.8 |
| todo-add-filter | active_filtered x5 | active_filtered x5 | no | 0.93 | 0.94 | +0.010 | 8 / 8 | 3.9 / 3.5 |
| toolshop-search-cart | in_cart x5 | in_cart x5 | no | 0.94 | 0.94 | +0.000 | 11 / 7 | 7.9 / 5.9 |
| web-form-submit | form_submitted x5 | form_submitted x5 | no | 0.98 | 0.98 | +0.000 | 8 / 8 | 4.1 / 3.5 |
| wiki-search | article_shown x5 | article_shown x5 | no | 0.73 | 0.74 | +0.010 | 4 / 4 | 4.1 / 3.9 |

**0 spec(s) ended differently in every run, 0 in some runs, 0 lost more than 0.05 of median decision confidence, 0 could not be compared.**

No spec moved and no confidence fell: over these specs the option changed nothing Jev did. That is evidence for making it the default, as strong as the specs are varied and the repeats many.
