# Suite seventeen non-hrm example specs at 9edd768, 2 workers 2026-09-24T12:16:11+03:00

**NOT ALL PASS** · 17 spec(s) × 3 repeat(s), 2 worker(s), 240.2 s wall-clock · commit `9edd768` · **1 environment/setup failure(s)** (the browser, the start URL or a setup step failed before the flow was observed; not counted as outcomes)

| spec | verdict | agreement | outcomes | median wall | Jev ms | requests | tokens in | confidence |
|---|---|---:|---|---:|---:|---:|---:|---:|
| `add-remove-elements` | **PASS** | 100% | one_delete_left 3/3 | 4894 ms | 1073 | 5 | 5078 | 0.96 |
| `dynamic-controls` | **PASS** | 100% | both_done 3/3 | 8614 ms | 2589 | 10 | 13682 | 0.625 |
| `forgot-password` | **EXPECTED (declared result in 3/3)** | 100% | server_error 3/3 | 4211 ms | 886 | 4 | 3643 | 0.98 |
| `load-wait` | **PASS** | 100% | loaded 3/3 | 8567 ms | 1689 | 7 | 6991 | 0.96 |
| `login-logout` | **PASS (environment/setup failures 1/3)** | 100% | logged_out 2/2 | 16744.5 ms | 1522 | 6 | 8764 | 0.945 |
| `menu-random` | **FLAKY** | 67% | entry_missing 2/3, all_entries 1/3 | 3938 ms | 275 | 2 | 1900 | None |
| `modal-close` | **PASS** | 100% | modal_closed 3/3 | 4011 ms | 871 | 4 | 3527 | 0.565 |
| `notify-random` | **FLAKY** | 67% | action_successful 2/3, action_unsuccessful 1/3 | 8917 ms | 565 | 3 | 2790 | 0.99 |
| `shop-add-second-item` | **PASS** | 100% | bike_light_in_cart 3/3 | 3454 ms | 854 | 4 | 10333 | 0.875 |
| `shop-checkout-error-account` | **EXPECTED (declared result in 3/3)** | 100% | undetermined 3/3 | 6220 ms | 2887 | 10 | 25730 | 0.93 |
| `shop-checkout-problem-account` | **BUG** | 100% | form_error 3/3 | 5554 ms | 2312 | 9 | 22921 | 0.87 |
| `shop-checkout` | **PASS** | 100% | order_complete 3/3 | 5991 ms | 2646 | 10 | 24455 | 0.98 |
| `table-sort-due` | **EXPECTED (declared result in 3/3)** | 100% | undetermined 3/3 | 4988 ms | 1146 | 4 | 10035 | 0.35 |
| `todo-add-filter` | **PASS** | 100% | active_filtered 3/3 | 4686 ms | 2092 | 8 | 15169 | 0.91 |
| `toolshop-search-cart` | **PASS** | 100% | in_cart 3/3 | 7401 ms | 2303 | 9 | 33595 | 0.79 |
| `web-form-submit` | **PASS** | 100% | form_submitted 3/3 | 4870 ms | 2049 | 8 | 20484 | 0.97 |
| `wiki-search` | **PASS** | 100% | article_shown 3/3 | 5182 ms | 1605 | 5 | 42126 | 0.68 |

## `add-remove-elements`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | one_delete_left | pass | passed | 4894 ms | 0 | Delete | `add-remove-elements/01/result.json` |
| 2 | one_delete_left | pass | passed | 28452 ms | 0 | Delete | `add-remove-elements/02/result.json` |
| 3 | one_delete_left | pass | passed | 4252 ms | 0 | Delete | `add-remove-elements/03/result.json` |

## `dynamic-controls`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | both_done | pass | passed | 8418 ms | 0 | It's gone! | `dynamic-controls/01/result.json` |
| 2 | both_done | pass | passed | 8614 ms | 0 | It's gone! | `dynamic-controls/02/result.json` |
| 3 | both_done | pass | passed | 34620 ms | 0 | It's gone! | `dynamic-controls/03/result.json` |

## `forgot-password`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | server_error (expected) | bug | outcome | 4211 ms | 0 | Internal Server Error | `forgot-password/01/result.json` |
| 2 | server_error (expected) | bug | outcome | 4254 ms | 0 | Internal Server Error | `forgot-password/02/result.json` |
| 3 | server_error (expected) | bug | outcome | 4192 ms | 0 | Internal Server Error | `forgot-password/03/result.json` |

## `load-wait`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | loaded | pass | passed | 8567 ms | 0 | Hello World! | `load-wait/01/result.json` |
| 2 | loaded | pass | passed | 31833 ms | 0 | Hello World! | `load-wait/02/result.json` |
| 3 | loaded | pass | passed | 8523 ms | 0 | Hello World! | `load-wait/03/result.json` |

## `login-logout`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | logged_out | pass | passed | 27091 ms | 0 | Login Page | `login-logout/01/result.json` |
| 2 | logged_out | pass | passed | 6398 ms | 0 | Login Page | `login-logout/02/result.json` |
| 3 | navigation failure | - | error | 31682 ms | 2 | navigation failed: TimeoutError: Page.goto: Timeout 30000ms exceeded. Call log: - navigating to "https://the-internet.he | `login-logout/03/result.json` |

## `menu-random`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | all_entries | pass | passed | 26478 ms | 0 |  | `menu-random/01/result.json` |
| 2 | entry_missing | bug | outcome | 3938 ms | 1 |  | `menu-random/02/result.json` |
| 3 | entry_missing | bug | outcome | 2831 ms | 1 |  | `menu-random/03/result.json` |

## `modal-close`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | modal_closed | pass | passed | 4011 ms | 0 | If closed, it will not appear on subsequent page loads. | `modal-close/01/result.json` |
| 2 | modal_closed | pass | passed | 28410 ms | 0 | If closed, it will not appear on subsequent page loads. | `modal-close/02/result.json` |
| 3 | modal_closed | pass | passed | 3856 ms | 0 |  | `modal-close/03/result.json` |

## `notify-random`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | action_successful | pass | passed | 3724 ms | 0 | Action successful | `notify-random/01/result.json` |
| 2 | action_successful | pass | passed | 8917 ms | 0 | Action successful | `notify-random/02/result.json` |
| 3 | action_unsuccessful | bug | outcome | 28236 ms | 1 | Action unsuccesful, please try again | `notify-random/03/result.json` |

## `shop-add-second-item`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | bike_light_in_cart | pass | passed | 3672 ms | 0 | Sauce Labs Bike Light | `shop-add-second-item/01/result.json` |
| 2 | bike_light_in_cart | pass | passed | 3425 ms | 0 | Sauce Labs Bike Light | `shop-add-second-item/02/result.json` |
| 3 | bike_light_in_cart | pass | passed | 3454 ms | 0 | Sauce Labs Bike Light | `shop-add-second-item/03/result.json` |

## `shop-checkout-error-account`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | undetermined (expected) | - | blocked | 6220 ms | 0 |  | `shop-checkout-error-account/01/result.json` |
| 2 | undetermined (expected) | - | blocked | 6450 ms | 0 |  | `shop-checkout-error-account/02/result.json` |
| 3 | undetermined (expected) | - | blocked | 6205 ms | 0 |  | `shop-checkout-error-account/03/result.json` |

## `shop-checkout-problem-account`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | form_error | bug | outcome | 5846 ms | 1 | Error: Last Name is required | `shop-checkout-problem-account/01/result.json` |
| 2 | form_error | bug | outcome | 5554 ms | 1 | Error: Last Name is required | `shop-checkout-problem-account/02/result.json` |
| 3 | form_error | bug | outcome | 5534 ms | 1 | Error: Last Name is required | `shop-checkout-problem-account/03/result.json` |

## `shop-checkout`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | order_complete | pass | passed | 6253 ms | 0 | Checkout: Complete! | `shop-checkout/01/result.json` |
| 2 | order_complete | pass | passed | 5991 ms | 0 | Checkout: Complete! | `shop-checkout/02/result.json` |
| 3 | order_complete | pass | passed | 5989 ms | 0 | Checkout: Complete! | `shop-checkout/03/result.json` |

## `table-sort-due`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | undetermined (expected) | - | low_confidence | 5666 ms | 0 |  | `table-sort-due/01/result.json` |
| 2 | undetermined (expected) | - | low_confidence | 4988 ms | 0 |  | `table-sort-due/02/result.json` |
| 3 | undetermined (expected) | - | low_confidence | 4953 ms | 0 |  | `table-sort-due/03/result.json` |

## `todo-add-filter`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | active_filtered | pass | passed | 5159 ms | 0 | 1 item left | `todo-add-filter/01/result.json` |
| 2 | active_filtered | pass | passed | 4573 ms | 0 | 1 item left | `todo-add-filter/02/result.json` |
| 3 | active_filtered | pass | passed | 4686 ms | 0 | 1 item left | `todo-add-filter/03/result.json` |

## `toolshop-search-cart`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | in_cart | pass | passed | 7401 ms | 0 | Proceed to checkout | `toolshop-search-cart/01/result.json` |
| 2 | in_cart | pass | passed | 9607 ms | 0 | Proceed to checkout | `toolshop-search-cart/02/result.json` |
| 3 | in_cart | pass | passed | 7091 ms | 0 | Proceed to checkout | `toolshop-search-cart/03/result.json` |

## `web-form-submit`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | form_submitted | pass | passed | 5263 ms | 0 | Form submitted | `web-form-submit/01/result.json` |
| 2 | form_submitted | pass | passed | 4751 ms | 0 | Form submitted | `web-form-submit/02/result.json` |
| 3 | form_submitted | pass | passed | 4870 ms | 0 | Form submitted | `web-form-submit/03/result.json` |

## `wiki-search`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | article_shown | pass | passed | 5831 ms | 0 | Playwright (software) | `wiki-search/01/result.json` |
| 2 | article_shown | pass | passed | 4881 ms | 0 | Playwright (software) | `wiki-search/02/result.json` |
| 3 | article_shown | pass | passed | 5182 ms | 0 | Playwright (software) | `wiki-search/03/result.json` |

Open a trace only for: `menu-random` (flaky), `notify-random` (flaky)
