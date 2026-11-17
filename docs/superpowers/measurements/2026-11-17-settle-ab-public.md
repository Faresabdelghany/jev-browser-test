# A/B: --settle=network

17 spec(s) x 5 repeat(s) per arm, interleaved; arm A as the spec is, arm B with `--settle=network`. 2026-11-17T16:25:30

| spec | A ended in | B ended in | moved | confidence A | B | delta | requests A / B | wall A / B (s) |
|---|---|---|---|---:|---:|---:|---:|---:|
| add-remove-elements | one_delete_left x5 | one_delete_left x5 | no | 0.96 | 0.95 | -0.010 | 5 / 5 | 3.7 / 3.6 |
| dynamic-controls | both_done x5 | both_done x5 | no | 0.84 | 0.87 | +0.030 | 11 / 11 | 9.4 / 9.2 |
| forgot-password | email_sent x5 | email_sent x5 | no | 0.99 | 1 | +0.005 | 4 / 4 | 3.6 / 3.6 |
| load-wait | loaded x5 | loaded x5 | no | 1 | 1 | +0.000 | 7 / 7 | 9.0 / 8.4 |
| login-logout | logged_out x5 | logged_out x5 | no | 0.98 | 0.98 | +0.000 | 6 / 6 | 4.8 / 4.4 |
| menu-random | entry_missing x3, all_entries x2 | all_entries x3, entry_missing x2 | some runs | - | - | - | 2 / 2 | 2.5 / 2.4 |
| modal-close | modal_closed x5 | modal_closed x5 | no | 0.71 | 0.71 | +0.005 | 4 / 4 | 3.4 / 3.4 |
| notify-random | action_successful x4, action_unsuccessful x1 | action_unsuccessful x3, action_successful x2 | some runs | 0.91 | 0.93 | +0.020 | 3 / 3 | 3.3 / 3.2 |
| shop-add-second-item | bike_light_in_cart x5 | bike_light_in_cart x5 | no | 0.91 | 0.91 | +0.000 | 4 / 4 | 3.0 / 2.9 |
| shop-checkout-error-account | undetermined:blocked x5 | undetermined:blocked x5 | no | 0.92 | 0.91 | -0.010 | 10 / 10 | 5.6 / 6.2 |
| shop-checkout-problem-account | form_error x5 | form_error x5 | no | 0.94 | 0.95 | +0.010 | 9 / 9 | 4.9 / 4.8 |
| shop-checkout | order_complete x5 | order_complete x5 | no | 0.99 | 0.99 | +0.000 | 10 / 10 | 5.2 / 4.9 |
| table-sort-due | undetermined:low_confidence x5 | undetermined:low_confidence x5 | no | 0.29 | 0.32 | +0.025 | 4 / 4 | 4.5 / 4.3 |
| todo-add-filter | active_filtered x5 | active_filtered x5 | no | 0.93 | 0.90 | -0.030 | 8 / 8 | 3.9 / 3.5 |
| toolshop-search-cart | in_cart x4, undetermined:budget_exhausted x1 | in_cart x5 | some runs | 0.65 | 0.95 | +0.300 | 11 / 7 | 8.3 / 6.1 |
| web-form-submit | form_submitted x5 | form_submitted x5 | no | 0.95 | 0.97 | +0.020 | 9 / 8 | 4.6 / 3.6 |
| wiki-search | article_shown x5 | article_shown x5 | no | 0.73 | 0.76 | +0.025 | 4 / 4 | 4.0 / 4.1 |

**0 spec(s) ended differently in every run, 3 in some runs, 0 lost more than 0.05 of median decision confidence, 0 could not be compared.**

Not safe to make the default as measured. A spec that moved in every run is the option's doing; one that moved in some runs wants more repeats (run it alone with `--repeat 10`) before it means anything. Open the two arms' traces of a moved spec side by side: the step where the operations differ is where to look.
