# A/B: --http-cache --http-cache-dir=runs/state/s4-cache-public

17 spec(s) x 3 repeat(s) per arm, interleaved; arm A as the spec is, arm B with `--http-cache --http-cache-dir=runs/state/s4-cache-public`. 2026-11-17T16:35:02

| spec | A ended in | B ended in | moved | confidence A | B | delta | requests A / B | wall A / B (s) |
|---|---|---|---|---:|---:|---:|---:|---:|
| add-remove-elements | one_delete_left x3 | one_delete_left x3 | no | 0.95 | 0.96 | +0.010 | 5 / 5 | 3.7 / 2.8 |
| dynamic-controls | both_done x3 | both_done x3 | no | 0.81 | 0.84 | +0.030 | 11 / 11 | 9.4 / 8.6 |
| forgot-password | email_sent x3 | email_sent x3 | no | 1 | 1 | +0.000 | 4 / 4 | 3.5 / 2.9 |
| load-wait | loaded x3 | loaded x3 | no | 1 | 1 | +0.000 | 7 / 7 | 8.1 / 7.2 |
| login-logout | logged_out x3 | logged_out x3 | no | 0.98 | 0.98 | +0.005 | 6 / 6 | 4.7 / 3.8 |
| menu-random | entry_missing x2, all_entries x1 | all_entries x2, entry_missing x1 | some runs | - | - | - | 2 / 2 | 2.6 / 1.7 |
| modal-close | modal_closed x3 | modal_closed x3 | no | 0.69 | 0.67 | -0.025 | 4 / 4 | 3.4 / 2.7 |
| notify-random | action_unsuccessful x2, action_successful x1 | action_successful x3 | some runs | 0.92 | 0.89 | -0.030 | 3 / 3 | 3.3 / 2.3 |
| shop-add-second-item | bike_light_in_cart x3 | bike_light_in_cart x3 | no | 0.91 | 0.91 | +0.000 | 4 / 4 | 3.1 / 2.5 |
| shop-checkout-error-account | undetermined:blocked x3 | undetermined:blocked x3 | no | 0.93 | 0.91 | -0.020 | 10 / 10 | 5.4 / 4.9 |
| shop-checkout-problem-account | form_error x3 | form_error x3 | no | 0.96 | 0.95 | -0.010 | 9 / 9 | 4.9 / 4.4 |
| shop-checkout | order_complete x3 | order_complete x3 | no | 0.99 | 0.99 | +0.000 | 10 / 10 | 5.3 / 4.7 |
| table-sort-due | undetermined:low_confidence x3 | undetermined:low_confidence x3 | no | 0.34 | 0.34 | +0.000 | 4 / 4 | 4.5 / 3.7 |
| todo-add-filter | active_filtered x3 | active_filtered x3 | no | 0.89 | 0.92 | +0.030 | 8 / 8 | 4.1 / 3.6 |
| toolshop-search-cart | in_cart x3 | in_cart x3 | no | 0.84 | 0.85 | +0.005 | 11 / 10 | 8.1 / 6.8 |
| web-form-submit | form_submitted x3 | form_submitted x3 | no | 0.96 | 0.99 | +0.025 | 9 / 8 | 4.7 / 3.4 |
| wiki-search | article_shown x3 | article_shown x3 | no | 0.77 | 0.73 | -0.040 | 4 / 4 | 3.8 / 3.6 |

**0 spec(s) ended differently in every run, 2 in some runs, 0 lost more than 0.05 of median decision confidence, 0 could not be compared.**

Not safe to make the default as measured. A spec that moved in every run is the option's doing; one that moved in some runs wants more repeats (run it alone with `--repeat 10`) before it means anything. Open the two arms' traces of a moved spec side by side: the step where the operations differ is where to look.
