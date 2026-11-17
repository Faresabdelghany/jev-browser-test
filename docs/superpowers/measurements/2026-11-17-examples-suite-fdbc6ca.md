# Suite seventeen non-hrm example specs at fdbc6ca (0.6.0, shadow DOM on by default), 1 worker 2026-11-17T12:07:30+02:00

**NOT ALL PASS** · 17 spec(s) × 3 repeat(s), 1 worker(s), 260.6 s wall-clock · commit `fdbc6ca`

| spec | verdict | agreement | outcomes | median wall | Jev ms | requests | tokens in | confidence |
|---|---|---:|---|---:|---:|---:|---:|---:|
| `add-remove-elements` | **PASS** | 100% | one_delete_left 3/3 | 3758 ms | 789 | 5 | 5862 | 0.96 |
| `dynamic-controls` | **FLAKY** | 67% | both_done 2/3, undetermined 1/3 | 9469 ms | 1865 | 10 | 15633 | 0.83 |
| `forgot-password` | **PASS** | 100% | email_sent 3/3 | 3529 ms | 556 | 4 | 4427 | 0.99 |
| `load-wait` | **PASS** | 100% | loaded 3/3 | 8088 ms | 1163 | 7 | 8147 | 1 |
| `login-logout` | **PASS** | 100% | logged_out 3/3 | 4716 ms | 940 | 6 | 9770 | 0.98 |
| `menu-random` | **PASS** | 100% | all_entries 3/3 | 2505 ms | 185 | 2 | 2238 | None |
| `modal-close` | **PASS** | 100% | modal_closed 3/3 | 3308 ms | 607 | 4 | 4033 | 0.69 |
| `notify-random` | **PASS** | 100% | action_successful 3/3 | 3262 ms | 399 | 3 | 3218 | 0.92 |
| `shop-add-second-item` | **PASS** | 100% | bike_light_in_cart 3/3 | 3000 ms | 601 | 4 | 10869 | 0.89 |
| `shop-checkout-error-account` | **EXPECTED (declared result in 3/3)** | 100% | undetermined 3/3 | 5476 ms | 2259 | 10 | 26266 | 0.91 |
| `shop-checkout-problem-account` | **BUG** | 100% | form_error 3/3 | 4823 ms | 1661 | 9 | 23457 | 0.95 |
| `shop-checkout` | **PASS** | 100% | order_complete 3/3 | 5194 ms | 1841 | 10 | 24991 | 0.99 |
| `table-sort-due` | **EXPECTED (declared result in 3/3)** | 100% | undetermined 3/3 | 4520 ms | 811 | 4 | 10122 | 0.36 |
| `todo-add-filter` | **PASS** | 100% | active_filtered 3/3 | 3833 ms | 1396 | 8 | 15169 | 0.895 |
| `toolshop-search-cart` | **PASS** | 100% | in_cart 3/3 | 10752 ms | 2411 | 11 | 44222 | 0.81 |
| `web-form-submit` | **PASS** | 100% | form_submitted 3/3 | 4636 ms | 1592 | 9 | 23844 | 0.96 |
| `wiki-search` | **PASS** | 100% | article_shown 3/3 | 3814 ms | 788 | 4 | 33491 | 0.785 |

## `add-remove-elements`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | one_delete_left | pass | passed | 3912 ms | 0 | Delete | `add-remove-elements/01/result.json` |
| 2 | one_delete_left | pass | passed | 3677 ms | 0 | Delete | `add-remove-elements/02/result.json` |
| 3 | one_delete_left | pass | passed | 3758 ms | 0 | Delete | `add-remove-elements/03/result.json` |

## `dynamic-controls`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | both_done | pass | passed | 9843 ms | 0 | Add | `dynamic-controls/01/result.json` |
| 2 | both_done | pass | passed | 9469 ms | 0 | Add | `dynamic-controls/02/result.json` |
| 3 | undetermined | - | low_confidence | 5570 ms | 1 |  | `dynamic-controls/03/result.json` |

## `forgot-password`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | email_sent | pass | passed | 3658 ms | 0 | Your e-mail's been sent! | `forgot-password/01/result.json` |
| 2 | email_sent | pass | passed | 3394 ms | 0 | Your e-mail's been sent! | `forgot-password/02/result.json` |
| 3 | email_sent | pass | passed | 3529 ms | 0 | Your e-mail's been sent! | `forgot-password/03/result.json` |

## `load-wait`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | loaded | pass | passed | 7798 ms | 0 | Hello World! | `load-wait/01/result.json` |
| 2 | loaded | pass | passed | 8197 ms | 0 | Hello World! | `load-wait/02/result.json` |
| 3 | loaded | pass | passed | 8088 ms | 0 | Hello World! | `load-wait/03/result.json` |

## `login-logout`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | logged_out | pass | passed | 4716 ms | 0 | Login Page | `login-logout/01/result.json` |
| 2 | logged_out | pass | passed | 4723 ms | 0 | Login Page | `login-logout/02/result.json` |
| 3 | logged_out | pass | passed | 4558 ms | 0 | Login Page | `login-logout/03/result.json` |

## `menu-random`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | all_entries | pass | passed | 2422 ms | 0 |  | `menu-random/01/result.json` |
| 2 | all_entries | pass | passed | 2505 ms | 0 |  | `menu-random/02/result.json` |
| 3 | all_entries | pass | passed | 2572 ms | 0 |  | `menu-random/03/result.json` |

## `modal-close`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | modal_closed | pass | passed | 3407 ms | 0 |  | `modal-close/01/result.json` |
| 2 | modal_closed | pass | passed | 3281 ms | 0 |  | `modal-close/02/result.json` |
| 3 | modal_closed | pass | passed | 3308 ms | 0 |  | `modal-close/03/result.json` |

## `notify-random`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | action_successful | pass | passed | 3378 ms | 0 | Action successful | `notify-random/01/result.json` |
| 2 | action_successful | pass | passed | 3262 ms | 0 | Action successful | `notify-random/02/result.json` |
| 3 | action_successful | pass | passed | 3136 ms | 0 | Action successful | `notify-random/03/result.json` |

## `shop-add-second-item`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | bike_light_in_cart | pass | passed | 3062 ms | 0 | Sauce Labs Bike Light | `shop-add-second-item/01/result.json` |
| 2 | bike_light_in_cart | pass | passed | 3000 ms | 0 | Sauce Labs Bike Light | `shop-add-second-item/02/result.json` |
| 3 | bike_light_in_cart | pass | passed | 2856 ms | 0 | Sauce Labs Bike Light | `shop-add-second-item/03/result.json` |

## `shop-checkout-error-account`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | undetermined (expected) | - | blocked | 5483 ms | 0 |  | `shop-checkout-error-account/01/result.json` |
| 2 | undetermined (expected) | - | blocked | 5476 ms | 0 |  | `shop-checkout-error-account/02/result.json` |
| 3 | undetermined (expected) | - | blocked | 5169 ms | 0 |  | `shop-checkout-error-account/03/result.json` |

## `shop-checkout-problem-account`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | form_error | bug | outcome | 4798 ms | 1 | Error: Last Name is required | `shop-checkout-problem-account/01/result.json` |
| 2 | form_error | bug | outcome | 4823 ms | 1 | Error: Last Name is required | `shop-checkout-problem-account/02/result.json` |
| 3 | form_error | bug | outcome | 4903 ms | 1 | Error: Last Name is required | `shop-checkout-problem-account/03/result.json` |

## `shop-checkout`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | order_complete | pass | passed | 5194 ms | 0 | Checkout: Complete! | `shop-checkout/01/result.json` |
| 2 | order_complete | pass | passed | 5203 ms | 0 | Checkout: Complete! | `shop-checkout/02/result.json` |
| 3 | order_complete | pass | passed | 5093 ms | 0 | Checkout: Complete! | `shop-checkout/03/result.json` |

## `table-sort-due`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | undetermined (expected) | - | low_confidence | 4521 ms | 0 |  | `table-sort-due/01/result.json` |
| 2 | undetermined (expected) | - | low_confidence | 4412 ms | 0 |  | `table-sort-due/02/result.json` |
| 3 | undetermined (expected) | - | low_confidence | 4520 ms | 0 |  | `table-sort-due/03/result.json` |

## `todo-add-filter`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | active_filtered | pass | passed | 4053 ms | 0 | 1 item left | `todo-add-filter/01/result.json` |
| 2 | active_filtered | pass | passed | 3833 ms | 0 | 1 item left | `todo-add-filter/02/result.json` |
| 3 | active_filtered | pass | passed | 3791 ms | 0 | 1 item left | `todo-add-filter/03/result.json` |

## `toolshop-search-cart`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | in_cart | pass | passed | 10752 ms | 0 | Proceed to checkout | `toolshop-search-cart/01/result.json` |
| 2 | in_cart | pass | passed | 8069 ms | 0 | Proceed to checkout | `toolshop-search-cart/02/result.json` |
| 3 | in_cart | pass | passed | 24267 ms | 0 | Proceed to checkout | `toolshop-search-cart/03/result.json` |

## `web-form-submit`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | form_submitted | pass | passed | 5342 ms | 0 | Form submitted | `web-form-submit/01/result.json` |
| 2 | form_submitted | pass | passed | 4636 ms | 0 | Form submitted | `web-form-submit/02/result.json` |
| 3 | form_submitted | pass | passed | 3893 ms | 0 | Received! | `web-form-submit/03/result.json` |

## `wiki-search`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | article_shown | pass | passed | 3954 ms | 0 | Playwright (software) | `wiki-search/01/result.json` |
| 2 | article_shown | pass | passed | 3476 ms | 0 | Playwright (software) | `wiki-search/02/result.json` |
| 3 | article_shown | pass | passed | 3814 ms | 0 | Playwright (software) | `wiki-search/03/result.json` |

Open a trace only for: `dynamic-controls` (flaky)
