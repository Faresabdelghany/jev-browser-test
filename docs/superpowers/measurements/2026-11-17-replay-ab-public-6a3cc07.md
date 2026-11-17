# A/B: --replay

17 spec(s) x 3 repeat(s) per arm, interleaved; arm A as the spec is, arm B with `--replay`. 2026-11-17T15:31:31

| spec | A ended in | B ended in | moved | confidence A | B | delta | requests A / B | wall A / B (s) |
|---|---|---|---|---:|---:|---:|---:|---:|
| add-remove-elements | one_delete_left x3 | one_delete_left x3 | no | 0.95 | - | - | 5 / 1 | 3.7 / 3.1 |
| dynamic-controls | both_done x3 | both_done x3 | no | 0.85 | - | - | 11 / 1 | 9.5 / 8.8 |
| forgot-password | email_sent x3 | email_sent x3 | no | 0.99 | - | - | 4 / 1 | 3.8 / 2.9 |
| load-wait | loaded x3 | loaded x3 | no | 1 | - | - | 7 / 1 | 8.1 / 7.5 |
| login-logout | logged_out x3 | logged_out x3 | no | 0.98 | - | - | 6 / 1 | 4.9 / 3.6 |
| menu-random | all_entries x3 | entry_missing x2, all_entries x1 | some runs | - | - | - | 2 / 2 | 2.5 / 3.4 |
| modal-close | modal_closed x3 | modal_closed x3 | no | 0.68 | - | - | 4 / 1 | 3.4 / 3.2 |
| notify-random | action_unsuccessful x2, action_successful x1 | action_successful x3 | some runs | 0.91 | 0.91 | +0.000 | 3 / 1 | 3.3 / 3.0 |
| shop-add-second-item | bike_light_in_cart x3 | bike_light_in_cart x3 | no | 0.90 | - | - | 4 / 1 | 3.0 / 2.3 |
| shop-checkout-error-account | undetermined:blocked x3 | undetermined:blocked x3 | no | 0.93 | 0.93 | +0.000 | 10 / 10 | 5.3 / 5.6 |
| shop-checkout-problem-account | form_error x3 | form_error x3 | no | 0.94 | 0.96 | +0.020 | 9 / 9 | 5.4 / 4.9 |
| shop-checkout | order_complete x3 | order_complete x3 | no | 0.99 | - | - | 10 / 1 | 5.1 / 3.4 |
| table-sort-due | undetermined:low_confidence x3 | undetermined:low_confidence x3 | no | 0.29 | 0.31 | +0.015 | 4 / 4 | 4.5 / 4.8 |
| todo-add-filter | active_filtered x3 | active_filtered x3 | no | 0.92 | - | - | 8 / 1 | 3.8 / 2.3 |
| toolshop-search-cart | in_cart x3 | in_cart x3 | no | 0.93 | - | - | 11 / 1 | 8.0 / 5.6 |
| web-form-submit | form_submitted x3 | form_submitted x3 | no | 0.96 | - | - | 8 / 1 | 4.0 / 2.3 |
| wiki-search | article_shown x3 | article_shown x3 | no | 0.76 | - | - | 4 / 1 | 4.2 / 3.4 |

**0 spec(s) ended differently in every run, 2 in some runs, 0 lost more than 0.05 of median decision confidence, 0 could not be compared.**

Not safe to make the default as measured. A spec that moved in every run is the option's doing; one that moved in some runs wants more repeats (run it alone with `--repeat 10`) before it means anything. Open the two arms' traces of a moved spec side by side: the step where the operations differ is where to look.
