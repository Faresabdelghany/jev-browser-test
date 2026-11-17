# A/B: --evidence=failures

17 spec(s) x 3 repeat(s) per arm, interleaved; arm A as the spec is, arm B with `--evidence=failures`. 2026-11-17T11:44:27

| spec | A ended in | B ended in | moved | confidence A | B | delta | requests A / B | wall A / B (s) |
|---|---|---|---|---:|---:|---:|---:|---:|
| add-remove-elements | one_delete_left x3 | one_delete_left x3 | no | 0.96 | 0.95 | -0.010 | 5 / 4 | 3.8 / 3.5 |
| dynamic-controls | both_done x3 | both_done x3 | no | 0.84 | 0.80 | -0.040 | 11 / 10 | 9.4 / 9.0 |
| forgot-password | email_sent x3 | email_sent x3 | no | 1 | 0.99 | -0.005 | 4 / 3 | 3.4 / 3.3 |
| load-wait | loaded x3 | loaded x3 | no | 1 | 1 | +0.000 | 7 / 6 | 8.0 / 7.7 |
| login-logout | logged_out x3 | logged_out x3 | no | 0.98 | 0.98 | +0.005 | 6 / 5 | 4.6 / 4.6 |
| menu-random | entry_missing x3 | all_entries x3 | **yes, every run** | - | - | - | 2 / 1 | 2.6 / 2.3 |
| modal-close | modal_closed x3 | modal_closed x3 | no | 0.72 | 0.66 | -0.060 ⚠ | 4 / 3 | 3.3 / 3.1 |
| notify-random | action_successful x3 | action_unsuccessful x3 | **yes, every run** | 0.91 | 0.91 | +0.000 | 3 / 3 | 3.2 / 3.3 |
| shop-add-second-item | bike_light_in_cart x3 | bike_light_in_cart x3 | no | 0.90 | 0.90 | +0.005 | 4 / 3 | 2.9 / 2.7 |
| shop-checkout-error-account | undetermined:blocked x3 | undetermined:blocked x3 | no | 0.93 | 0.92 | -0.010 | 10 / 10 | 5.0 / 5.1 |
| shop-checkout-problem-account | form_error x3 | form_error x3 | no | 0.94 | 0.95 | +0.010 | 9 / 9 | 4.7 / 4.8 |
| shop-checkout | order_complete x3 | order_complete x3 | no | 0.99 | 0.99 | +0.000 | 10 / 9 | 5.2 / 4.9 |
| table-sort-due | undetermined:low_confidence x3 | undetermined:low_confidence x3 | no | 0.36 | 0.30 | -0.060 ⚠ | 4 / 4 | 4.5 / 4.5 |
| todo-add-filter | active_filtered x3 | active_filtered x3 | no | 0.92 | 0.93 | +0.005 | 8 / 7 | 3.8 / 3.4 |
| toolshop-search-cart | in_cart x3 | in_cart x3 | no | 0.93 | 0.81 | -0.115 ⚠ | 11 / 10 | 8.0 / 7.5 |
| web-form-submit | form_submitted x3 | form_submitted x3 | no | 0.96 | 0.96 | -0.005 | 9 / 7 | 4.6 / 3.7 |
| wiki-search | article_shown x3 | article_shown x3 | no | 0.72 | 0.77 | +0.050 | 4 / 3 | 3.9 / 3.7 |

**2 spec(s) ended differently in every run, 0 in some runs, 3 lost more than 0.05 of median decision confidence, 0 could not be compared.**

Not safe to make the default as measured. A spec that moved in every run is the option's doing; one that moved in some runs wants more repeats (run it alone with `--repeat 10`) before it means anything. Open the two arms' traces of a moved spec side by side: the step where the operations differ is where to look.
