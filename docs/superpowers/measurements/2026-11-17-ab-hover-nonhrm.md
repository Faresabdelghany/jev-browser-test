# A/B: --hover

17 spec(s) x 5 repeat(s) per arm, interleaved; arm A as the spec is, arm B with `--hover`. 2026-11-17T11:41:06

| spec | A ended in | B ended in | moved | confidence A | B | delta | requests A / B | wall A / B (s) |
|---|---|---|---|---:|---:|---:|---:|---:|
| wiki-search | article_shown x5 | article_shown x5 | no | 0.77 | 0.81 | +0.035 | 4 / 4 | 4.0 / 4.1 |
| web-form-submit | form_submitted x5 | form_submitted x5 | no | 0.98 | 0.98 | +0.000 | 8 / 8 | 3.9 / 3.7 |
| toolshop-search-cart | in_cart x5 | in_cart x5 | no | 0.93 | 0.92 | -0.010 | 11 / 10 | 8.0 / 7.8 |
| todo-add-filter | active_filtered x5 | active_filtered x5 | no | 0.91 | 0.92 | +0.010 | 8 / 8 | 3.7 / 3.7 |
| table-sort-due | undetermined:low_confidence x5 | undetermined:low_confidence x4, undetermined:blocked x1 | some runs | 0.30 | 0.38 | +0.075 | 4 / 4 | 4.5 / 4.4 |
| shop-checkout | order_complete x5 | order_complete x5 | no | 0.99 | 1 | +0.005 | 10 / 10 | 5.2 / 5.0 |
| shop-checkout-problem-account | form_error x5 | form_error x5 | no | 0.95 | 0.98 | +0.030 | 9 / 9 | 4.8 / 4.7 |
| shop-checkout-error-account | undetermined:blocked x5 | undetermined:blocked x5 | no | 0.94 | 0.94 | +0.000 | 10 / 10 | 5.2 / 5.2 |
| shop-add-second-item | bike_light_in_cart x5 | bike_light_in_cart x5 | no | 0.92 | 0.94 | +0.020 | 4 / 4 | 3.0 / 3.1 |
| notify-random | action_successful x3, action_unsuccessful x2 | action_unsuccessful x4, action_successful x1 | some runs | 0.92 | 0.92 | +0.000 | 3 / 3 | 3.2 / 3.2 |
| modal-close | modal_closed x5 | modal_closed x5 | no | 0.73 | 0.73 | +0.000 | 4 / 4 | 3.4 / 3.3 |
| menu-random | entry_missing x4, all_entries x1 | entry_missing x3, all_entries x2 | some runs | - | - | - | 2 / 2 | 2.6 / 2.5 |
| login-logout | logged_out x5 | logged_out x5 | no | 0.98 | 0.96 | -0.020 | 6 / 6 | 4.5 / 4.7 |
| load-wait | loaded x5 | loaded x5 | no | 1 | 1 | +0.000 | 7 / 7 | 7.9 / 7.9 |
| forgot-password | email_sent x5 | email_sent x5 | no | 0.99 | 1 | +0.005 | 4 / 4 | 3.5 / 3.5 |
| dynamic-controls | both_done x5 | both_done x5 | no | 0.84 | 0.91 | +0.070 | 11 / 11 | 9.3 / 9.3 |
| add-remove-elements | one_delete_left x5 | one_delete_left x5 | no | 0.95 | 0.94 | -0.010 | 5 / 5 | 3.7 / 3.5 |

**0 spec(s) ended differently in every run, 3 in some runs, 0 lost more than 0.05 of median decision confidence, 0 could not be compared.**

Not safe to make the default as measured. A spec that moved in every run is the option's doing; one that moved in some runs wants more repeats (run it alone with `--repeat 10`) before it means anything. Open the two arms' traces of a moved spec side by side: the step where the operations differ is where to look.
