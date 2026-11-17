# A/B: --replay

17 spec(s) x 3 repeat(s) per arm, interleaved; arm A as the spec is, arm B with `--replay`. 2026-11-17T15:53:38

| spec | A ended in | B ended in | moved | confidence A | B | delta | requests A / B | wall A / B (s) |
|---|---|---|---|---:|---:|---:|---:|---:|
| add-remove-elements | one_delete_left x3 | one_delete_left x3 | no | 0.95 | - | - | 6 / 1 | 4.4 / 2.9 |
| dynamic-controls | both_done x3 | both_done x3 | no | 0.85 | - | - | 11 / 1 | 9.6 / 8.7 |
| forgot-password | email_sent x3 | email_sent x3 | no | 1 | - | - | 4 / 1 | 3.6 / 2.9 |
| load-wait | loaded x3 | loaded x3 | no | 1 | - | - | 7 / 1 | 8.1 / 7.5 |
| login-logout | logged_out x3 | logged_out x3 | no | 0.98 | - | - | 6 / 1 | 4.7 / 3.7 |
| menu-random | all_entries x2, entry_missing x1 | all_entries x2, entry_missing x1 | no | - | - | - | 2 / 2 | 2.4 / 2.5 |
| modal-close | modal_closed x3 | modal_closed x3 | no | 0.72 | - | - | 4 / 1 | 3.4 / 3.1 |
| notify-random | action_successful x3 | action_unsuccessful x2, action_successful x1 | some runs | 0.92 | - | - | 3 / 2 | 3.3 / 4.0 |
| shop-add-second-item | bike_light_in_cart x3 | bike_light_in_cart x3 | no | 0.91 | - | - | 4 / 1 | 3.1 / 2.3 |
| shop-checkout-error-account | undetermined:blocked x3 | undetermined:blocked x3 | no | 0.90 | 0.92 | +0.020 | 10 / 10 | 5.4 / 5.4 |
| shop-checkout-problem-account | form_error x3 | form_error x3 | no | 0.94 | 0.95 | +0.010 | 9 / 9 | 4.8 / 4.9 |
| shop-checkout | order_complete x3 | order_complete x3 | no | 0.99 | - | - | 10 / 1 | 5.2 / 3.5 |
| table-sort-due | undetermined:low_confidence x3 | undetermined:low_confidence x3 | no | 0.37 | 0.30 | -0.070 ⚠ | 4 / 4 | 4.6 / 4.7 |
| todo-add-filter | active_filtered x3 | active_filtered x3 | no | 0.93 | - | - | 8 / 1 | 4.0 / 2.5 |
| toolshop-search-cart | in_cart x3 | in_cart x3 | no | 0.92 | - | - | 11 / 1 | 8.8 / 5.6 |
| web-form-submit | form_submitted x3 | form_submitted x3 | no | 0.96 | - | - | 9 / 1 | 4.9 / 2.6 |
| wiki-search | article_shown x3 | article_shown x3 | no | 0.76 | - | - | 4 / 1 | 4.1 / 3.3 |

**0 spec(s) ended differently in every run, 1 in some runs, 1 lost more than 0.05 of median decision confidence, 0 could not be compared.**

Not safe to make the default as measured. A spec that moved in every run is the option's doing; one that moved in some runs wants more repeats (run it alone with `--repeat 10`) before it means anything. Open the two arms' traces of a moved spec side by side: the step where the operations differ is where to look.
