# Suite seventeen non-hrm example specs at d42c243, 2 workers (rerun after the slow-navigation and busy-page fixes) 2026-09-24T12:43:55+03:00

**NOT ALL PASS** · 17 spec(s) × 3 repeat(s), 2 worker(s), 248.5 s wall-clock · commit `d42c243`

| spec | verdict | agreement | outcomes | median wall | Jev ms | requests | tokens in | confidence |
|---|---|---:|---|---:|---:|---:|---:|---:|
| `add-remove-elements` | **PASS** | 100% | one_delete_left 3/3 | 8819 ms | 1143 | 5 | 5078 | 0.96 |
| `dynamic-controls` | **FLAKY** | 67% | both_done 2/3, undetermined 1/3 | 29048 ms | 2616 | 10 | 13745 | 0.56 |
| `forgot-password` | **EXPECTED (declared result in 3/3)** | 100% | server_error 3/3 | 4353 ms | 835 | 4 | 3643 | 0.975 |
| `load-wait` | **PASS** | 100% | loaded 3/3 | 13374 ms | 1740 | 7 | 6991 | 0.96 |
| `login-logout` | **PASS** | 100% | logged_out 3/3 | 5378 ms | 1445 | 6 | 8764 | 0.94 |
| `menu-random` | **FLAKY** | 67% | all_entries 2/3, entry_missing 1/3 | 3136 ms | 271 | 2 | 2012 | None |
| `modal-close` | **PASS** | 100% | modal_closed 3/3 | 4003 ms | 920 | 4 | 3527 | 0.67 |
| `notify-random` | **FLAKY** | 67% | action_unsuccessful 2/3, action_successful 1/3 | 3746 ms | 559 | 3 | 2840 | 0.99 |
| `shop-add-second-item` | **PASS** | 100% | bike_light_in_cart 3/3 | 3476 ms | 903 | 4 | 10333 | 0.88 |
| `shop-checkout-error-account` | **EXPECTED (declared result in 3/3)** | 100% | undetermined 3/3 | 6126 ms | 2861 | 10 | 25730 | 0.93 |
| `shop-checkout-problem-account` | **BUG** | 100% | form_error 3/3 | 5653 ms | 2338 | 9 | 22921 | 0.86 |
| `shop-checkout` | **PASS** | 100% | order_complete 3/3 | 6045 ms | 2599 | 10 | 24455 | 0.98 |
| `table-sort-due` | **FLAKY (declared result in 2/3)** | 67% | undetermined 2/3, not_sorted 1/3 | 9007 ms | 1135 | 4 | 10035 | 0.38 |
| `todo-add-filter` | **PASS** | 100% | active_filtered 3/3 | 4636 ms | 1960 | 8 | 15169 | 0.925 |
| `toolshop-search-cart` | **PASS** | 100% | in_cart 3/3 | 6885 ms | 2683 | 10 | 38670 | 0.825 |
| `web-form-submit` | **PASS** | 100% | form_submitted 3/3 | 4786 ms | 1996 | 8 | 20484 | 0.97 |
| `wiki-search` | **PASS** | 100% | article_shown 3/3 | 4607 ms | 1458 | 5 | 42126 | 0.7 |

## `add-remove-elements`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | one_delete_left | pass | passed | 8819 ms | 0 | Delete | `add-remove-elements/01/result.json` |
| 2 | one_delete_left | pass | passed | 27540 ms | 0 | Delete | `add-remove-elements/02/result.json` |
| 3 | one_delete_left | pass | passed | 5433 ms | 0 | Delete | `add-remove-elements/03/result.json` |

## `dynamic-controls`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | both_done | pass | passed | 29048 ms | 0 | It's gone! | `dynamic-controls/01/result.json` |
| 2 | undetermined | - | low_confidence | 37862 ms | 1 |  | `dynamic-controls/02/result.json` |
| 3 | both_done | pass | passed | 8687 ms | 0 | It's gone! | `dynamic-controls/03/result.json` |

## `forgot-password`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | server_error (expected) | bug | outcome | 4208 ms | 0 | Internal Server Error | `forgot-password/01/result.json` |
| 2 | server_error (expected) | bug | outcome | 4353 ms | 0 | Internal Server Error | `forgot-password/02/result.json` |
| 3 | server_error (expected) | bug | outcome | 28394 ms | 0 | Internal Server Error | `forgot-password/03/result.json` |

## `load-wait`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | loaded | pass | passed | 13374 ms | 0 | Hello World! | `load-wait/01/result.json` |
| 2 | loaded | pass | passed | 8451 ms | 0 | Hello World! | `load-wait/02/result.json` |
| 3 | loaded | pass | passed | 31699 ms | 0 | Hello World! | `load-wait/03/result.json` |

## `login-logout`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | logged_out | pass | passed | 5278 ms | 0 | Login Page | `login-logout/01/result.json` |
| 2 | logged_out | pass | passed | 5378 ms | 0 | Login Page | `login-logout/02/result.json` |
| 3 | logged_out | pass | passed | 31722 ms | 0 | Login Page | `login-logout/03/result.json` |

## `menu-random`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | all_entries | pass | passed | 2882 ms | 0 |  | `menu-random/01/result.json` |
| 2 | all_entries | pass | passed | 29345 ms | 0 |  | `menu-random/02/result.json` |
| 3 | entry_missing | bug | outcome | 3136 ms | 1 |  | `menu-random/03/result.json` |

## `modal-close`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | modal_closed | pass | passed | 4003 ms | 0 |  | `modal-close/01/result.json` |
| 2 | modal_closed | pass | passed | 4055 ms | 0 | If closed, it will not appear on subsequent page loads. | `modal-close/02/result.json` |
| 3 | modal_closed | pass | passed | 3989 ms | 0 | If closed, it will not appear on subsequent page loads. | `modal-close/03/result.json` |

## `notify-random`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | action_successful | pass | passed | 30971 ms | 0 | Action successful | `notify-random/01/result.json` |
| 2 | action_unsuccessful | bug | outcome | 3746 ms | 1 | Action unsuccesful, please try again | `notify-random/02/result.json` |
| 3 | action_unsuccessful | bug | outcome | 3652 ms | 1 | Action unsuccesful, please try again | `notify-random/03/result.json` |

## `shop-add-second-item`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | bike_light_in_cart | pass | passed | 3436 ms | 0 | Sauce Labs Bike Light | `shop-add-second-item/01/result.json` |
| 2 | bike_light_in_cart | pass | passed | 3497 ms | 0 | Sauce Labs Bike Light | `shop-add-second-item/02/result.json` |
| 3 | bike_light_in_cart | pass | passed | 3476 ms | 0 | Sauce Labs Bike Light | `shop-add-second-item/03/result.json` |

## `shop-checkout-error-account`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | undetermined (expected) | - | blocked | 6217 ms | 0 |  | `shop-checkout-error-account/01/result.json` |
| 2 | undetermined (expected) | - | blocked | 6041 ms | 0 |  | `shop-checkout-error-account/02/result.json` |
| 3 | undetermined (expected) | - | blocked | 6126 ms | 0 |  | `shop-checkout-error-account/03/result.json` |

## `shop-checkout-problem-account`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | form_error | bug | outcome | 5653 ms | 1 | Error: Last Name is required | `shop-checkout-problem-account/01/result.json` |
| 2 | form_error | bug | outcome | 5551 ms | 1 | Error: Last Name is required | `shop-checkout-problem-account/02/result.json` |
| 3 | form_error | bug | outcome | 5826 ms | 1 | Error: Last Name is required | `shop-checkout-problem-account/03/result.json` |

## `shop-checkout`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | order_complete | pass | passed | 6140 ms | 0 | Checkout: Complete! | `shop-checkout/01/result.json` |
| 2 | order_complete | pass | passed | 6042 ms | 0 | Checkout: Complete! | `shop-checkout/02/result.json` |
| 3 | order_complete | pass | passed | 6045 ms | 0 | Checkout: Complete! | `shop-checkout/03/result.json` |

## `table-sort-due`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | undetermined (expected) | - | low_confidence | 9007 ms | 0 |  | `table-sort-due/01/result.json` |
| 2 | not_sorted (NOT the expected result) | bug | outcome | 14397 ms | 1 |  | `table-sort-due/02/result.json` |
| 3 | undetermined (expected) | - | low_confidence | 5434 ms | 0 |  | `table-sort-due/03/result.json` |

## `todo-add-filter`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | active_filtered | pass | passed | 4700 ms | 0 | 1 item left | `todo-add-filter/01/result.json` |
| 2 | active_filtered | pass | passed | 4535 ms | 0 | 1 item left | `todo-add-filter/02/result.json` |
| 3 | active_filtered | pass | passed | 4636 ms | 0 | 1 item left | `todo-add-filter/03/result.json` |

## `toolshop-search-cart`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | in_cart | pass | passed | 6754 ms | 0 | Proceed to checkout | `toolshop-search-cart/01/result.json` |
| 2 | in_cart | pass | passed | 6885 ms | 0 | Proceed to checkout | `toolshop-search-cart/02/result.json` |
| 3 | in_cart | pass | passed | 9795 ms | 0 | Proceed to checkout | `toolshop-search-cart/03/result.json` |

## `web-form-submit`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | form_submitted | pass | passed | 4786 ms | 0 | Form submitted | `web-form-submit/01/result.json` |
| 2 | form_submitted | pass | passed | 4648 ms | 0 | Form submitted | `web-form-submit/02/result.json` |
| 3 | form_submitted | pass | passed | 4819 ms | 0 | Form submitted | `web-form-submit/03/result.json` |

## `wiki-search`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | article_shown | pass | passed | 5060 ms | 0 |  | `wiki-search/01/result.json` |
| 2 | article_shown | pass | passed | 4607 ms | 0 | Playwright (software) | `wiki-search/02/result.json` |
| 3 | article_shown | pass | passed | 4600 ms | 0 | Playwright (software) | `wiki-search/03/result.json` |

Open a trace only for: `dynamic-controls` (flaky), `menu-random` (flaky), `notify-random` (flaky), `table-sort-due` (flaky)
