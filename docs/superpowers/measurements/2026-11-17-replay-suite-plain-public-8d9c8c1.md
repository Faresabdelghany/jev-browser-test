# Suite 0.8.0 without replay (public), 8d9c8c1 2026-11-17T15:57:28+02:00

**NOT ALL PASS** · 17 spec(s) × 1 repeat(s), 1 worker(s), 83.9 s wall-clock · commit `8d9c8c1`

| spec | verdict | agreement | outcomes | median wall | Jev ms | requests | tokens in | confidence |
|---|---|---:|---|---:|---:|---:|---:|---:|
| `add-remove-elements` | **PASS** | 100% | one_delete_left 1/1 | 3604 ms | 826 | 5 | 5862 | 0.93 |
| `dynamic-controls` | **PASS** | 100% | both_done 1/1 | 9384 ms | 2061 | 11 | 17476 | 0.85 |
| `forgot-password` | **PASS** | 100% | email_sent 1/1 | 3706 ms | 585 | 4 | 4427 | 0.99 |
| `load-wait` | **PASS** | 100% | loaded 1/1 | 8260 ms | 1158 | 7 | 8147 | 1 |
| `login-logout` | **PASS** | 100% | logged_out 1/1 | 4993 ms | 980 | 6 | 9770 | 0.99 |
| `menu-random` | **PASS** | 100% | all_entries 1/1 | 2599 ms | 196 | 2 | 2238 | None |
| `modal-close` | **PASS** | 100% | modal_closed 1/1 | 3445 ms | 639 | 4 | 4033 | 0.64 |
| `notify-random` | **PASS** | 100% | action_successful 1/1 | 3402 ms | 443 | 3 | 3218 | 0.89 |
| `shop-add-second-item` | **PASS** | 100% | bike_light_in_cart 1/1 | 3119 ms | 631 | 4 | 10869 | 0.9 |
| `shop-checkout-error-account` | **EXPECTED (declared result in 1/1)** | 100% | undetermined 1/1 | 5203 ms | 2079 | 10 | 26266 | 0.95 |
| `shop-checkout-problem-account` | **BUG** | 100% | form_error 1/1 | 4874 ms | 1595 | 9 | 23457 | 0.94 |
| `shop-checkout` | **PASS** | 100% | order_complete 1/1 | 6039 ms | 1981 | 10 | 24991 | 0.995 |
| `table-sort-due` | **EXPECTED (declared result in 1/1)** | 100% | undetermined 1/1 | 5185 ms | 811 | 4 | 10122 | 0.27 |
| `todo-add-filter` | **PASS** | 100% | active_filtered 1/1 | 3966 ms | 1611 | 8 | 15169 | 0.895 |
| `toolshop-search-cart` | **PASS** | 100% | in_cart 1/1 | 7958 ms | 2308 | 11 | 46217 | 0.96 |
| `web-form-submit` | **PASS** | 100% | form_submitted 1/1 | 3965 ms | 1531 | 8 | 20532 | 0.965 |
| `wiki-search` | **PASS** | 100% | article_shown 1/1 | 4199 ms | 756 | 4 | 34385 | 0.685 |

## `add-remove-elements`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | one_delete_left | pass | passed | 3604 ms | 0 | Delete | `add-remove-elements/01/result.json` |

## `dynamic-controls`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | both_done | pass | passed | 9384 ms | 0 | Add | `dynamic-controls/01/result.json` |

## `forgot-password`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | email_sent | pass | passed | 3706 ms | 0 | Your e-mail's been sent! | `forgot-password/01/result.json` |

## `load-wait`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | loaded | pass | passed | 8260 ms | 0 | Hello World! | `load-wait/01/result.json` |

## `login-logout`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | logged_out | pass | passed | 4993 ms | 0 | Login Page | `login-logout/01/result.json` |

## `menu-random`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | all_entries | pass | passed | 2599 ms | 0 |  | `menu-random/01/result.json` |

## `modal-close`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | modal_closed | pass | passed | 3445 ms | 0 |  | `modal-close/01/result.json` |

## `notify-random`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | action_successful | pass | passed | 3402 ms | 0 | Action successful | `notify-random/01/result.json` |

## `shop-add-second-item`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | bike_light_in_cart | pass | passed | 3119 ms | 0 | Sauce Labs Bike Light | `shop-add-second-item/01/result.json` |

## `shop-checkout-error-account`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | undetermined (expected) | - | blocked | 5203 ms | 0 |  | `shop-checkout-error-account/01/result.json` |

## `shop-checkout-problem-account`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | form_error | bug | outcome | 4874 ms | 1 | Error: Last Name is required | `shop-checkout-problem-account/01/result.json` |

## `shop-checkout`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | order_complete | pass | passed | 6039 ms | 0 | Checkout: Complete! | `shop-checkout/01/result.json` |

## `table-sort-due`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | undetermined (expected) | - | low_confidence | 5185 ms | 0 |  | `table-sort-due/01/result.json` |

## `todo-add-filter`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | active_filtered | pass | passed | 3966 ms | 0 | 1 item left | `todo-add-filter/01/result.json` |

## `toolshop-search-cart`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | in_cart | pass | passed | 7958 ms | 0 | Proceed to checkout | `toolshop-search-cart/01/result.json` |

## `web-form-submit`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | form_submitted | pass | passed | 3965 ms | 0 | Form submitted | `web-form-submit/01/result.json` |

## `wiki-search`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | article_shown | pass | passed | 4199 ms | 0 | Playwright (software) | `wiki-search/01/result.json` |
