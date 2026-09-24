# Suite seventeen non-hrm example specs at 0e2bc07, 2 workers 2026-09-24T12:56:00+03:00

**NOT ALL PASS** · 17 spec(s) × 3 repeat(s), 2 worker(s), 218.6 s wall-clock · commit `0e2bc07`

| spec | verdict | agreement | outcomes | median wall | Jev ms | requests | tokens in | confidence |
|---|---|---:|---|---:|---:|---:|---:|---:|
| `add-remove-elements` | **PASS** | 100% | one_delete_left 3/3 | 4099 ms | 1077 | 5 | 5078 | 0.96 |
| `dynamic-controls` | **FLAKY** | 67% | undetermined 2/3, both_done 1/3 | 8154 ms | 2534 | 9 | 12567 | 0.62 |
| `forgot-password` | **EXPECTED (declared result in 3/3)** | 100% | server_error 3/3 | 4141 ms | 835 | 4 | 3643 | 0.98 |
| `load-wait` | **PASS** | 100% | loaded 3/3 | 8603 ms | 1665 | 7 | 6991 | 0.96 |
| `login-logout` | **PASS** | 100% | logged_out 3/3 | 5371 ms | 1394 | 6 | 8764 | 0.955 |
| `menu-random` | **FLAKY** | 67% | all_entries 2/3, entry_missing 1/3 | 24560 ms | 297 | 2 | 2012 | None |
| `modal-close` | **PASS** | 100% | modal_closed 3/3 | 3958 ms | 811 | 4 | 3527 | 0.61 |
| `notify-random` | **BUG** | 100% | action_unsuccessful 3/3 | 10327 ms | 570 | 3 | 2840 | 0.99 |
| `shop-add-second-item` | **PASS** | 100% | bike_light_in_cart 3/3 | 3437 ms | 881 | 4 | 10333 | 0.87 |
| `shop-checkout-error-account` | **EXPECTED (declared result in 3/3)** | 100% | undetermined 3/3 | 6353 ms | 2981 | 10 | 25730 | 0.93 |
| `shop-checkout-problem-account` | **BUG** | 100% | form_error 3/3 | 5726 ms | 2300 | 9 | 22921 | 0.86 |
| `shop-checkout` | **PASS** | 100% | order_complete 3/3 | 6079 ms | 2597 | 10 | 24455 | 0.985 |
| `table-sort-due` | **EXPECTED (declared result in 3/3)** | 100% | undetermined 3/3 | 5035 ms | 1139 | 4 | 10035 | 0.35 |
| `todo-add-filter` | **PASS** | 100% | active_filtered 3/3 | 4808 ms | 2014 | 8 | 15169 | 0.925 |
| `toolshop-search-cart` | **PASS** | 100% | in_cart 3/3 | 7832 ms | 2557 | 10 | 38388 | 0.885 |
| `web-form-submit` | **PASS** | 100% | form_submitted 3/3 | 4794 ms | 2084 | 8 | 20484 | 0.975 |
| `wiki-search` | **PASS** | 100% | article_shown 3/3 | 4668 ms | 1544 | 5 | 42126 | 0.7 |

## `add-remove-elements`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | one_delete_left | pass | passed | 3519 ms | 0 | Delete | `add-remove-elements/01/result.json` |
| 2 | one_delete_left | pass | passed | 31068 ms | 0 | Delete | `add-remove-elements/02/result.json` |
| 3 | one_delete_left | pass | passed | 4099 ms | 0 | Delete | `add-remove-elements/03/result.json` |

## `dynamic-controls`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | undetermined | - | done_unverified | 8177 ms | 1 |  | `dynamic-controls/01/result.json` |
| 2 | undetermined | - | done_unverified | 8154 ms | 1 |  | `dynamic-controls/02/result.json` |
| 3 | both_done | pass | passed | 7710 ms | 0 | It's gone! | `dynamic-controls/03/result.json` |

## `forgot-password`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | server_error (expected) | bug | outcome | 3976 ms | 0 | Internal Server Error | `forgot-password/01/result.json` |
| 2 | server_error (expected) | bug | outcome | 11667 ms | 0 | Internal Server Error | `forgot-password/02/result.json` |
| 3 | server_error (expected) | bug | outcome | 4141 ms | 0 | Internal Server Error | `forgot-password/03/result.json` |

## `load-wait`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | loaded | pass | passed | 8292 ms | 0 | Hello World! | `load-wait/01/result.json` |
| 2 | loaded | pass | passed | 8603 ms | 0 | Hello World! | `load-wait/02/result.json` |
| 3 | loaded | pass | passed | 8694 ms | 0 | Hello World! | `load-wait/03/result.json` |

## `login-logout`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | logged_out | pass | passed | 5371 ms | 0 | Login Page | `login-logout/01/result.json` |
| 2 | logged_out | pass | passed | 11478 ms | 0 | Login Page | `login-logout/02/result.json` |
| 3 | logged_out | pass | passed | 5271 ms | 0 | Login Page | `login-logout/03/result.json` |

## `menu-random`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | entry_missing | bug | outcome | 24560 ms | 1 |  | `menu-random/01/result.json` |
| 2 | all_entries | pass | passed | 25921 ms | 0 |  | `menu-random/02/result.json` |
| 3 | all_entries | pass | passed | 7423 ms | 0 |  | `menu-random/03/result.json` |

## `modal-close`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | modal_closed | pass | passed | 3958 ms | 0 |  | `modal-close/01/result.json` |
| 2 | modal_closed | pass | passed | 3845 ms | 0 |  | `modal-close/02/result.json` |
| 3 | modal_closed | pass | passed | 25493 ms | 0 | If closed, it will not appear on subsequent page loads. | `modal-close/03/result.json` |

## `notify-random`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | action_unsuccessful | bug | outcome | 3694 ms | 1 | Action unsuccesful, please try again | `notify-random/01/result.json` |
| 2 | action_unsuccessful | bug | outcome | 10327 ms | 1 | Action unsuccesful, please try again | `notify-random/02/result.json` |
| 3 | action_unsuccessful | bug | outcome | 29671 ms | 1 | Action unsuccesful, please try again | `notify-random/03/result.json` |

## `shop-add-second-item`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | bike_light_in_cart | pass | passed | 3437 ms | 0 | Sauce Labs Bike Light | `shop-add-second-item/01/result.json` |
| 2 | bike_light_in_cart | pass | passed | 3379 ms | 0 | Sauce Labs Bike Light | `shop-add-second-item/02/result.json` |
| 3 | bike_light_in_cart | pass | passed | 3442 ms | 0 | Sauce Labs Bike Light | `shop-add-second-item/03/result.json` |

## `shop-checkout-error-account`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | undetermined (expected) | - | blocked | 6353 ms | 0 |  | `shop-checkout-error-account/01/result.json` |
| 2 | undetermined (expected) | - | blocked | 6252 ms | 0 |  | `shop-checkout-error-account/02/result.json` |
| 3 | undetermined (expected) | - | blocked | 6609 ms | 0 |  | `shop-checkout-error-account/03/result.json` |

## `shop-checkout-problem-account`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | form_error | bug | outcome | 5726 ms | 1 | Error: Last Name is required | `shop-checkout-problem-account/01/result.json` |
| 2 | form_error | bug | outcome | 5634 ms | 1 | Error: Last Name is required | `shop-checkout-problem-account/02/result.json` |
| 3 | form_error | bug | outcome | 5737 ms | 1 | Error: Last Name is required | `shop-checkout-problem-account/03/result.json` |

## `shop-checkout`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | order_complete | pass | passed | 6079 ms | 0 | Checkout: Complete! | `shop-checkout/01/result.json` |
| 2 | order_complete | pass | passed | 6091 ms | 0 | Checkout: Complete! | `shop-checkout/02/result.json` |
| 3 | order_complete | pass | passed | 6003 ms | 0 | Checkout: Complete! | `shop-checkout/03/result.json` |

## `table-sort-due`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | undetermined (expected) | - | low_confidence | 27737 ms | 0 |  | `table-sort-due/01/result.json` |
| 2 | undetermined (expected) | - | low_confidence | 4971 ms | 0 |  | `table-sort-due/02/result.json` |
| 3 | undetermined (expected) | - | low_confidence | 5035 ms | 0 |  | `table-sort-due/03/result.json` |

## `todo-add-filter`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | active_filtered | pass | passed | 4865 ms | 0 | 1 item left | `todo-add-filter/01/result.json` |
| 2 | active_filtered | pass | passed | 4709 ms | 0 | 1 item left | `todo-add-filter/02/result.json` |
| 3 | active_filtered | pass | passed | 4808 ms | 0 | 1 item left | `todo-add-filter/03/result.json` |

## `toolshop-search-cart`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | in_cart | pass | passed | 7832 ms | 0 | Proceed to checkout | `toolshop-search-cart/01/result.json` |
| 2 | in_cart | pass | passed | 7918 ms | 0 | Proceed to checkout | `toolshop-search-cart/02/result.json` |
| 3 | in_cart | pass | passed | 7387 ms | 0 | Proceed to checkout | `toolshop-search-cart/03/result.json` |

## `web-form-submit`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | form_submitted | pass | passed | 5406 ms | 0 | Form submitted | `web-form-submit/01/result.json` |
| 2 | form_submitted | pass | passed | 4644 ms | 0 | Form submitted | `web-form-submit/02/result.json` |
| 3 | form_submitted | pass | passed | 4794 ms | 0 | Form submitted | `web-form-submit/03/result.json` |

## `wiki-search`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | article_shown | pass | passed | 4774 ms | 0 | Playwright (software) | `wiki-search/01/result.json` |
| 2 | article_shown | pass | passed | 4633 ms | 0 | Playwright (software) | `wiki-search/02/result.json` |
| 3 | article_shown | pass | passed | 4668 ms | 0 | Playwright (software) | `wiki-search/03/result.json` |

Open a trace only for: `dynamic-controls` (flaky), `menu-random` (flaky)
