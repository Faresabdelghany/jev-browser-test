# A/B: --shadow-dom

17 spec(s) x 3 repeat(s) per arm, interleaved; arm A as the spec is, arm B with `--shadow-dom`. 2026-11-17T11:36:25

| spec | A ended in | B ended in | moved | confidence A | B | delta | requests A / B | wall A / B (s) |
|---|---|---|---|---:|---:|---:|---:|---:|
| add-remove-elements | one_delete_left x3 | one_delete_left x3 | no | 0.96 | 0.95 | -0.010 | 5 / 5 | 3.6 / 3.6 |
| dynamic-controls | both_done x3 | both_done x3 | no | 0.88 | 0.86 | -0.020 | 11 / 11 | 9.2 / 9.6 |
| forgot-password | email_sent x3 | email_sent x3 | no | 0.99 | 0.98 | -0.010 | 4 / 4 | 4.0 / 3.8 |
| load-wait | loaded x3 | loaded x3 | no | 1 | 1 | +0.000 | 7 / 7 | 8.0 / 8.0 |
| login-logout | logged_out x3 | logged_out x3 | no | 0.98 | 0.98 | +0.005 | 6 / 6 | 4.6 / 4.6 |
| menu-random | entry_missing x3 | entry_missing x3 | no | - | - | - | 2 / 2 | 2.5 / 2.6 |
| modal-close | modal_closed x3 | modal_closed x3 | no | - | - | - | 2 / 2 | 2.5 / 2.5 |
| notify-random | action_successful x2, action_unsuccessful x1 | action_successful x2, action_unsuccessful x1 | no | 0.93 | 0.87 | -0.060 ⚠ | 3 / 3 | 4.1 / 4.8 |
| shop-add-second-item | bike_light_in_cart x3 | bike_light_in_cart x3 | no | 0.90 | 0.90 | +0.000 | 4 / 4 | 3.0 / 2.9 |
| shop-checkout-error-account | undetermined:blocked x3 | undetermined:blocked x3 | no | 0.93 | 0.93 | +0.000 | 10 / 10 | 5.0 / 5.0 |
| shop-checkout-problem-account | form_error x3 | form_error x3 | no | 0.96 | 0.96 | +0.000 | 9 / 9 | 4.9 / 4.8 |
| shop-checkout | order_complete x3 | order_complete x3 | no | 0.99 | 0.99 | -0.005 | 10 / 10 | 5.4 / 5.6 |
| table-sort-due | undetermined:low_confidence x3 | undetermined:low_confidence x3 | no | 0.33 | 0.32 | -0.005 | 4 / 4 | 4.7 / 4.5 |
| todo-add-filter | active_filtered x3 | active_filtered x3 | no | 0.90 | 0.92 | +0.020 | 8 / 8 | 3.7 / 3.9 |
| toolshop-search-cart | in_cart x3 | in_cart x3 | no | 0.95 | 0.94 | -0.010 | 11 / 11 | 7.8 / 7.8 |
| web-form-submit | form_submitted x3 | form_submitted x3 | no | 0.98 | 0.98 | -0.005 | 8 / 9 | 3.8 / 4.5 |
| wiki-search | article_shown x3 | article_shown x3 | no | 0.74 | 0.74 | +0.005 | 4 / 4 | 4.3 / 3.9 |

**0 spec(s) ended differently in every run, 0 in some runs, 1 lost more than 0.05 of median decision confidence, 0 could not be compared.**

Not safe to make the default as measured. A spec that moved in every run is the option's doing; one that moved in some runs wants more repeats (run it alone with `--repeat 10`) before it means anything. Open the two arms' traces of a moved spec side by side: the step where the operations differ is where to look.
