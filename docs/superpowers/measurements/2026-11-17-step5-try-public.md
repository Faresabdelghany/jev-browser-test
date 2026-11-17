# Suite step 5 try: 17 public, 6 workers, 2 per host 2026-11-17T16:43:43+02:00

**NOT ALL PASS** · 17 spec(s) × 1 repeat(s), 6 worker(s) over 6 host(s), at most 2 at once on any, 23.7 s wall-clock · commit `4b8a5e0`

| spec | verdict | agreement | outcomes | median wall | Jev ms | requests | tokens in | confidence |
|---|---|---:|---|---:|---:|---:|---:|---:|
| `add-remove-elements` | **PASS** | 100% | one_delete_left 1/1 | 4295 ms | 870 | 5 | 5862 | 0.96 |
| `dynamic-controls` | **PASS** | 100% | both_done 1/1 | 9852 ms | 2121 | 11 | 17446 | 0.79 |
| `forgot-password` | **PASS** | 100% | email_sent 1/1 | 3473 ms | 614 | 4 | 4427 | 0.975 |
| `load-wait` | **PASS** | 100% | loaded 1/1 | 8096 ms | 1296 | 7 | 8147 | 1 |
| `login-logout` | **PASS** | 100% | logged_out 1/1 | 4563 ms | 1012 | 6 | 9770 | 0.98 |
| `menu-random` | **PASS** | 100% | all_entries 1/1 | 2344 ms | 195 | 2 | 2238 | None |
| `modal-close` | **PASS** | 100% | modal_closed 1/1 | 3276 ms | 603 | 4 | 4033 | 0.675 |
| `notify-random` | **PASS** | 100% | action_successful 1/1 | 3085 ms | 412 | 3 | 3218 | 0.92 |
| `shop-add-second-item` | **PASS** | 100% | bike_light_in_cart 1/1 | 3660 ms | 796 | 4 | 10869 | 0.905 |
| `shop-checkout-error-account` | **EXPECTED (declared result in 1/1)** | 100% | undetermined 1/1 | 5591 ms | 2033 | 10 | 26266 | 0.93 |
| `shop-checkout-problem-account` | **BUG** | 100% | form_error 1/1 | 4635 ms | 1650 | 9 | 23457 | 0.92 |
| `shop-checkout` | **PASS** | 100% | order_complete 1/1 | 5054 ms | 1904 | 10 | 24991 | 0.985 |
| `table-sort-due` | **EXPECTED (declared result in 1/1)** | 100% | undetermined 1/1 | 4521 ms | 803 | 4 | 10122 | 0.3 |
| `todo-add-filter` | **PASS** | 100% | active_filtered 1/1 | 4506 ms | 1458 | 8 | 15169 | 0.925 |
| `toolshop-search-cart` | **PASS** | 100% | in_cart 1/1 | 8659 ms | 2300 | 11 | 46201 | 0.95 |
| `web-form-submit` | **PASS** | 100% | form_submitted 1/1 | 3952 ms | 1427 | 8 | 20543 | 0.99 |
| `wiki-search` | **PASS** | 100% | article_shown 1/1 | 4118 ms | 738 | 4 | 34385 | 0.72 |

## `add-remove-elements`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | one_delete_left | pass | passed | 4295 ms | 0 | Delete | `add-remove-elements/01/result.json` |

## `dynamic-controls`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | both_done | pass | passed | 9852 ms | 0 | Add | `dynamic-controls/01/result.json` |

## `forgot-password`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | email_sent | pass | passed | 3473 ms | 0 | Your e-mail's been sent! | `forgot-password/01/result.json` |

## `load-wait`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | loaded | pass | passed | 8096 ms | 0 | Hello World! | `load-wait/01/result.json` |

## `login-logout`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | logged_out | pass | passed | 4563 ms | 0 | Login Page | `login-logout/01/result.json` |

## `menu-random`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | all_entries | pass | passed | 2344 ms | 0 |  | `menu-random/01/result.json` |

## `modal-close`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | modal_closed | pass | passed | 3276 ms | 0 |  | `modal-close/01/result.json` |

## `notify-random`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | action_successful | pass | passed | 3085 ms | 0 | Action successful | `notify-random/01/result.json` |

## `shop-add-second-item`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | bike_light_in_cart | pass | passed | 3660 ms | 0 | Sauce Labs Bike Light | `shop-add-second-item/01/result.json` |

## `shop-checkout-error-account`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | undetermined (expected) | - | blocked | 5591 ms | 0 |  | `shop-checkout-error-account/01/result.json` |

## `shop-checkout-problem-account`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | form_error | bug | outcome | 4635 ms | 1 | Error: Last Name is required | `shop-checkout-problem-account/01/result.json` |

## `shop-checkout`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | order_complete | pass | passed | 5054 ms | 0 | Checkout: Complete! | `shop-checkout/01/result.json` |

## `table-sort-due`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | undetermined (expected) | - | low_confidence | 4521 ms | 0 |  | `table-sort-due/01/result.json` |

## `todo-add-filter`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | active_filtered | pass | passed | 4506 ms | 0 | 1 item left | `todo-add-filter/01/result.json` |

## `toolshop-search-cart`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | in_cart | pass | passed | 8659 ms | 0 | Proceed to checkout | `toolshop-search-cart/01/result.json` |

## `web-form-submit`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | form_submitted | pass | passed | 3952 ms | 0 | Form submitted | `web-form-submit/01/result.json` |

## `wiki-search`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | article_shown | pass | passed | 4118 ms | 0 | Playwright (software) | `wiki-search/01/result.json` |
