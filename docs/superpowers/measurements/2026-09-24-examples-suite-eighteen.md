# Suite examples suite at 14ecee9, clean export 2026-09-24T02:40:07+03:00

**NOT ALL PASS** · 18 spec(s) × 3 repeat(s), 2 worker(s), 228.1 s wall-clock · commit `14ecee9`

| spec | verdict | agreement | outcomes | median wall | Jev ms | requests | tokens in | confidence |
|---|---|---:|---|---:|---:|---:|---:|---:|
| `add-remove-elements` | **PASS** | 100% | one_delete_left 3/3 | 9194 ms | 1501 | 5 | 5078 | 0.95 |
| `dynamic-controls` | **PASS** | 100% | both_done 3/3 | 25060 ms | 3149 | 10 | 13682 | 0.605 |
| `forgot-password` | **EXPECTED (declared result in 3/3)** | 100% | server_error 3/3 | 4386 ms | 975 | 4 | 3643 | 0.98 |
| `hrm-add-employee` | **FLAKY** | 67% | undetermined 2/3, employee_saved 1/3 | 17209 ms | 3929 | 9 | 41461 | 0.875 |
| `load-wait` | **PASS** | 100% | loaded 3/3 | 8654 ms | 2120 | 7 | 6991 | 0.97 |
| `login-logout` | **PASS** | 100% | logged_out 3/3 | 5969 ms | 1984 | 6 | 8395 | 0.95 |
| `menu-random` | **BUG** | 100% | entry_missing 3/3 | 3240 ms | 313 | 2 | 1900 | None |
| `modal-close` | **PASS** | 100% | modal_closed 3/3 | 4507 ms | 1042 | 4 | 3527 | 0.665 |
| `notify-random` | **FLAKY** | 67% | action_successful 2/3, action_unsuccessful 1/3 | 3976 ms | 756 | 3 | 2677 | 1 |
| `shop-add-second-item` | **PASS** | 100% | bike_light_in_cart 3/3 | 4477 ms | 1237 | 4 | 10333 | 0.88 |
| `shop-checkout-error-account` | **EXPECTED (declared result in 3/3)** | 100% | undetermined 3/3 | 7331 ms | 3779 | 10 | 25730 | 0.93 |
| `shop-checkout-problem-account` | **BUG** | 100% | form_error 3/3 | 6783 ms | 2819 | 9 | 22796 | 0.88 |
| `shop-checkout` | **PASS** | 100% | order_complete 3/3 | 7413 ms | 3322 | 10 | 24455 | 0.98 |
| `table-sort-due` | **FLAKY (declared result in 2/3)** | 67% | undetermined 3/3 | 10278 ms | 2374 | 7 | 18705 | 0.45 |
| `todo-add-filter` | **PASS** | 100% | active_filtered 3/3 | 5467 ms | 2250 | 8 | 15169 | 0.915 |
| `toolshop-search-cart` | **PASS** | 100% | in_cart 3/3 | 8391 ms | 3156 | 10 | 39169 | 0.895 |
| `web-form-submit` | **PASS** | 100% | form_submitted 3/3 | 5597 ms | 2564 | 8 | 20484 | 0.975 |
| `wiki-search` | **PASS** | 100% | article_shown 3/3 | 3922 ms | 1442 | 4 | 33533 | 0.84 |

## `add-remove-elements`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | one_delete_left | pass | passed | 5598 ms | 0 | Delete | `add-remove-elements/01/result.json` |
| 2 | one_delete_left | pass | passed | 12060 ms | 0 | Delete | `add-remove-elements/02/result.json` |
| 3 | one_delete_left | pass | passed | 9194 ms | 0 | Delete | `add-remove-elements/03/result.json` |

## `dynamic-controls`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | both_done | pass | passed | 25060 ms | 0 | It's gone! | `dynamic-controls/01/result.json` |
| 2 | both_done | pass | passed | 32820 ms | 0 | It's gone! | `dynamic-controls/02/result.json` |
| 3 | both_done | pass | passed | 9214 ms | 0 | It's gone! | `dynamic-controls/03/result.json` |

## `forgot-password`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | server_error (expected) | bug | outcome | 4386 ms | 0 | Internal Server Error | `forgot-password/01/result.json` |
| 2 | server_error (expected) | bug | outcome | 20709 ms | 0 | Internal Server Error | `forgot-password/02/result.json` |
| 3 | server_error (expected) | bug | outcome | 4196 ms | 0 | Internal Server Error | `forgot-password/03/result.json` |

## `hrm-add-employee`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | undetermined | - | done_unverified | 17351 ms | 1 |  | `hrm-add-employee/01/result.json` |
| 2 | employee_saved | pass | passed | 15098 ms | 0 | Jevtest Runner | `hrm-add-employee/02/result.json` |
| 3 | undetermined | - | done_unverified | 17209 ms | 1 |  | `hrm-add-employee/03/result.json` |

## `load-wait`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | loaded | pass | passed | 8776 ms | 0 | Hello World! | `load-wait/01/result.json` |
| 2 | loaded | pass | passed | 8654 ms | 0 | Hello World! | `load-wait/02/result.json` |
| 3 | loaded | pass | passed | 8563 ms | 0 | Hello World! | `load-wait/03/result.json` |

## `login-logout`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | logged_out | pass | passed | 5969 ms | 0 | You logged out of the secure area! | `login-logout/01/result.json` |
| 2 | logged_out | pass | passed | 6131 ms | 0 | You logged out of the secure area! | `login-logout/02/result.json` |
| 3 | logged_out | pass | passed | 5557 ms | 0 | You logged out of the secure area! | `login-logout/03/result.json` |

## `menu-random`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | entry_missing | bug | outcome | 3219 ms | 1 |  | `menu-random/01/result.json` |
| 2 | entry_missing | bug | outcome | 3240 ms | 1 |  | `menu-random/02/result.json` |
| 3 | entry_missing | bug | outcome | 5177 ms | 1 |  | `menu-random/03/result.json` |

## `modal-close`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | modal_closed | pass | passed | 9822 ms | 0 |  | `modal-close/01/result.json` |
| 2 | modal_closed | pass | passed | 4507 ms | 0 | If closed, it will not appear on subsequent page loads. | `modal-close/02/result.json` |
| 3 | modal_closed | pass | passed | 4136 ms | 0 | If closed, it will not appear on subsequent page loads. | `modal-close/03/result.json` |

## `notify-random`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | action_successful | pass | passed | 3893 ms | 0 | Action successful | `notify-random/01/result.json` |
| 2 | action_successful | pass | passed | 3978 ms | 0 | Action successful | `notify-random/02/result.json` |
| 3 | action_unsuccessful | bug | outcome | 3976 ms | 1 | Action unsuccesful, please try again | `notify-random/03/result.json` |

## `shop-add-second-item`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | bike_light_in_cart | pass | passed | 4983 ms | 0 | Sauce Labs Bike Light | `shop-add-second-item/01/result.json` |
| 2 | bike_light_in_cart | pass | passed | 4360 ms | 0 | Sauce Labs Bike Light | `shop-add-second-item/02/result.json` |
| 3 | bike_light_in_cart | pass | passed | 4477 ms | 0 | Sauce Labs Bike Light | `shop-add-second-item/03/result.json` |

## `shop-checkout-error-account`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | undetermined (expected) | - | blocked | 7667 ms | 0 |  | `shop-checkout-error-account/01/result.json` |
| 2 | undetermined (expected) | - | blocked | 7331 ms | 0 |  | `shop-checkout-error-account/02/result.json` |
| 3 | undetermined (expected) | - | blocked | 7073 ms | 0 |  | `shop-checkout-error-account/03/result.json` |

## `shop-checkout-problem-account`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | form_error | bug | outcome | 6551 ms | 1 | Error: Last Name is required | `shop-checkout-problem-account/01/result.json` |
| 2 | form_error | bug | outcome | 7712 ms | 1 | Error: Last Name is required | `shop-checkout-problem-account/02/result.json` |
| 3 | form_error | bug | outcome | 6783 ms | 1 | Error: Last Name is required | `shop-checkout-problem-account/03/result.json` |

## `shop-checkout`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | order_complete | pass | passed | 7688 ms | 0 | Checkout: Complete! | `shop-checkout/01/result.json` |
| 2 | order_complete | pass | passed | 7369 ms | 0 | Checkout: Complete! | `shop-checkout/02/result.json` |
| 3 | order_complete | pass | passed | 7413 ms | 0 | Checkout: Complete! | `shop-checkout/03/result.json` |

## `table-sort-due`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | undetermined (expected) | - | low_confidence | 27156 ms | 0 |  | `table-sort-due/01/result.json` |
| 2 | undetermined (expected) | - | low_confidence | 5192 ms | 0 |  | `table-sort-due/02/result.json` |
| 3 | undetermined (NOT the expected result) | - | stuck | 10278 ms | 1 |  | `table-sort-due/03/result.json` |

## `todo-add-filter`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | active_filtered | pass | passed | 5893 ms | 0 | 1 item left | `todo-add-filter/01/result.json` |
| 2 | active_filtered | pass | passed | 5408 ms | 0 | 1 item left | `todo-add-filter/02/result.json` |
| 3 | active_filtered | pass | passed | 5467 ms | 0 | 1 item left | `todo-add-filter/03/result.json` |

## `toolshop-search-cart`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | in_cart | pass | passed | 8569 ms | 0 | Proceed to checkout | `toolshop-search-cart/01/result.json` |
| 2 | in_cart | pass | passed | 8391 ms | 0 | Proceed to checkout | `toolshop-search-cart/02/result.json` |
| 3 | in_cart | pass | passed | 8104 ms | 0 | Proceed to checkout | `toolshop-search-cart/03/result.json` |

## `web-form-submit`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | form_submitted | pass | passed | 6224 ms | 0 | Form submitted | `web-form-submit/01/result.json` |
| 2 | form_submitted | pass | passed | 5549 ms | 0 | Form submitted | `web-form-submit/02/result.json` |
| 3 | form_submitted | pass | passed | 5597 ms | 0 | Form submitted | `web-form-submit/03/result.json` |

## `wiki-search`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | article_shown | pass | passed | 4792 ms | 0 | Playwright (software) | `wiki-search/01/result.json` |
| 2 | article_shown | pass | passed | 3922 ms | 0 | Playwright (software) | `wiki-search/02/result.json` |
| 3 | article_shown | pass | passed | 3911 ms | 0 | Playwright (software) | `wiki-search/03/result.json` |

Open a trace only for: `hrm-add-employee` (flaky), `notify-random` (flaky), `table-sort-due` (flaky)
