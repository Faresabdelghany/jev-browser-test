# Suite  2026-09-24T16:36:50+03:00

**NOT ALL PASS** · 17 spec(s) × 3 repeat(s), 2 worker(s), 298.4 s wall-clock · commit `b92b24f` · **3 environment/setup failure(s)** (the browser, the start URL or a setup step failed before the flow was observed; not counted as outcomes)

| spec | verdict | agreement | outcomes | median wall | Jev ms | requests | tokens in | confidence |
|---|---|---:|---|---:|---:|---:|---:|---:|
| `add-remove-elements` | **PASS (environment/setup failures 1/3)** | 100% | one_delete_left 2/2 | 5698.5 ms | 1153.5 | 5 | 5078 | 0.945 |
| `dynamic-controls` | **FLAKY (environment/setup failures 1/3)** | 50% | both_done 1/2, undetermined 1/2 | 31767.5 ms | 2889.5 | 10.5 | 15545 | 0.495 |
| `forgot-password` | **EXPECTED (declared result in 3/3)** | 100% | server_error 3/3 | 4382 ms | 902 | 4 | 3643 | 0.985 |
| `load-wait` | **PASS** | 100% | loaded 3/3 | 15029 ms | 1695 | 7 | 6991 | 0.96 |
| `login-logout` | **PASS** | 100% | logged_out 3/3 | 14006 ms | 1417 | 6 | 8764 | 0.945 |
| `menu-random` | **FLAKY (environment/setup failures 1/3)** | 50% | entry_missing 1/2, all_entries 1/2 | 24863.5 ms | 272 | 2 | 1956 | None |
| `modal-close` | **PASS** | 100% | modal_closed 3/3 | 5828 ms | 821 | 4 | 3527 | 0.6 |
| `notify-random` | **FLAKY** | 67% | action_unsuccessful 2/3, action_successful 1/3 | 4155 ms | 612 | 3 | 2840 | 0.99 |
| `shop-add-second-item` | **PASS** | 100% | bike_light_in_cart 3/3 | 4035 ms | 873 | 4 | 10869 | 0.905 |
| `shop-checkout-error-account` | **EXPECTED (declared result in 3/3)** | 100% | undetermined 3/3 | 6928 ms | 3032 | 10 | 26266 | 0.92 |
| `shop-checkout-problem-account` | **BUG** | 100% | form_error 3/3 | 6305 ms | 2305 | 9 | 23457 | 0.87 |
| `shop-checkout` | **PASS** | 100% | order_complete 3/3 | 6665 ms | 2580 | 10 | 24991 | 0.98 |
| `table-sort-due` | **EXPECTED (declared result in 3/3)** | 100% | undetermined 3/3 | 5617 ms | 1123 | 4 | 10035 | 0.38 |
| `todo-add-filter` | **PASS** | 100% | active_filtered 3/3 | 5343 ms | 2082 | 8 | 15169 | 0.91 |
| `toolshop-search-cart` | **PASS** | 100% | in_cart 3/3 | 8656 ms | 2990 | 11 | 47106 | 0.9 |
| `web-form-submit` | **PASS** | 100% | form_submitted 3/3 | 5291 ms | 2023 | 8 | 20484 | 0.975 |
| `wiki-search` | **PASS** | 100% | article_shown 3/3 | 4217 ms | 1154 | 4 | 34327 | 0.84 |

## `add-remove-elements`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | navigation failure | - | error | 31335 ms | 2 | navigation failed: TimeoutError: Page.goto: Timeout 30000ms exceeded. Call log: - navigating to "https://the-internet.he | `add-remove-elements/01/result.json` |
| 2 | one_delete_left | pass | passed | 5105 ms | 0 | Delete | `add-remove-elements/02/result.json` |
| 3 | one_delete_left | pass | passed | 6292 ms | 0 | Delete | `add-remove-elements/03/result.json` |

## `dynamic-controls`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | both_done | pass | passed | 27257 ms | 0 | It's gone! | `dynamic-controls/01/result.json` |
| 2 | navigation failure | - | error | 32712 ms | 2 | navigation failed: TimeoutError: Page.goto: Timeout 30000ms exceeded. Call log: - navigating to "https://the-internet.he | `dynamic-controls/02/result.json` |
| 3 | undetermined | - | low_confidence | 36278 ms | 1 |  | `dynamic-controls/03/result.json` |

## `forgot-password`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | server_error (expected) | bug | outcome | 9173 ms | 0 | Internal Server Error | `forgot-password/01/result.json` |
| 2 | server_error (expected) | bug | outcome | 4382 ms | 0 | Internal Server Error | `forgot-password/02/result.json` |
| 3 | server_error (expected) | bug | outcome | 4326 ms | 0 | Internal Server Error | `forgot-password/03/result.json` |

## `load-wait`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | loaded | pass | passed | 15029 ms | 0 | Hello World! | `load-wait/01/result.json` |
| 2 | loaded | pass | passed | 9149 ms | 0 | Hello World! | `load-wait/02/result.json` |
| 3 | loaded | pass | passed | 36330 ms | 0 | Hello World! | `load-wait/03/result.json` |

## `login-logout`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | logged_out | pass | passed | 29408 ms | 0 | Login Page | `login-logout/01/result.json` |
| 2 | logged_out | pass | passed | 14006 ms | 0 | Login Page | `login-logout/02/result.json` |
| 3 | logged_out | pass | passed | 5760 ms | 0 | Login Page | `login-logout/03/result.json` |

## `menu-random`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | entry_missing | bug | outcome | 25389 ms | 1 |  | `menu-random/01/result.json` |
| 2 | all_entries | pass | passed | 24338 ms | 0 |  | `menu-random/02/result.json` |
| 3 | navigation failure | - | error | 31936 ms | 2 | navigation failed: TimeoutError: Page.goto: Timeout 30000ms exceeded. Call log: - navigating to "https://the-internet.he | `menu-random/03/result.json` |

## `modal-close`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | modal_closed | pass | passed | 5828 ms | 0 | If closed, it will not appear on subsequent page loads. | `modal-close/01/result.json` |
| 2 | modal_closed | pass | passed | 4600 ms | 0 |  | `modal-close/02/result.json` |
| 3 | modal_closed | pass | passed | 28568 ms | 0 | If closed, it will not appear on subsequent page loads. | `modal-close/03/result.json` |

## `notify-random`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | action_unsuccessful | bug | outcome | 12972 ms | 1 | Action unsuccesful, please try again | `notify-random/01/result.json` |
| 2 | action_unsuccessful | bug | outcome | 4155 ms | 1 | Action unsuccesful, please try again | `notify-random/02/result.json` |
| 3 | action_successful | pass | passed | 3925 ms | 0 | Action successful | `notify-random/03/result.json` |

## `shop-add-second-item`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | bike_light_in_cart | pass | passed | 4035 ms | 0 | Sauce Labs Bike Light | `shop-add-second-item/01/result.json` |
| 2 | bike_light_in_cart | pass | passed | 3944 ms | 0 | Sauce Labs Bike Light | `shop-add-second-item/02/result.json` |
| 3 | bike_light_in_cart | pass | passed | 4057 ms | 0 | Sauce Labs Bike Light | `shop-add-second-item/03/result.json` |

## `shop-checkout-error-account`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | undetermined (expected) | - | blocked | 6938 ms | 0 |  | `shop-checkout-error-account/01/result.json` |
| 2 | undetermined (expected) | - | blocked | 6909 ms | 0 |  | `shop-checkout-error-account/02/result.json` |
| 3 | undetermined (expected) | - | blocked | 6928 ms | 0 |  | `shop-checkout-error-account/03/result.json` |

## `shop-checkout-problem-account`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | form_error | bug | outcome | 6305 ms | 1 | Error: Last Name is required | `shop-checkout-problem-account/01/result.json` |
| 2 | form_error | bug | outcome | 6218 ms | 1 | Error: Last Name is required | `shop-checkout-problem-account/02/result.json` |
| 3 | form_error | bug | outcome | 6418 ms | 1 | Error: Last Name is required | `shop-checkout-problem-account/03/result.json` |

## `shop-checkout`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | order_complete | pass | passed | 6885 ms | 0 | Checkout: Complete! | `shop-checkout/01/result.json` |
| 2 | order_complete | pass | passed | 6513 ms | 0 | Checkout: Complete! | `shop-checkout/02/result.json` |
| 3 | order_complete | pass | passed | 6665 ms | 0 | Checkout: Complete! | `shop-checkout/03/result.json` |

## `table-sort-due`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | undetermined (expected) | - | low_confidence | 30218 ms | 0 |  | `table-sort-due/01/result.json` |
| 2 | undetermined (expected) | - | low_confidence | 5617 ms | 0 |  | `table-sort-due/02/result.json` |
| 3 | undetermined (expected) | - | low_confidence | 5421 ms | 0 |  | `table-sort-due/03/result.json` |

## `todo-add-filter`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | active_filtered | pass | passed | 5640 ms | 0 | 1 item left | `todo-add-filter/01/result.json` |
| 2 | active_filtered | pass | passed | 5343 ms | 0 | 1 item left | `todo-add-filter/02/result.json` |
| 3 | active_filtered | pass | passed | 5242 ms | 0 | 1 item left | `todo-add-filter/03/result.json` |

## `toolshop-search-cart`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | in_cart | pass | passed | 7325 ms | 0 | Proceed to checkout | `toolshop-search-cart/01/result.json` |
| 2 | in_cart | pass | passed | 8656 ms | 0 | Proceed to checkout | `toolshop-search-cart/02/result.json` |
| 3 | in_cart | pass | passed | 10252 ms | 0 | Proceed to checkout | `toolshop-search-cart/03/result.json` |

## `web-form-submit`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | form_submitted | pass | passed | 5889 ms | 0 | Form submitted | `web-form-submit/01/result.json` |
| 2 | form_submitted | pass | passed | 5266 ms | 0 | Form submitted | `web-form-submit/02/result.json` |
| 3 | form_submitted | pass | passed | 5291 ms | 0 | Form submitted | `web-form-submit/03/result.json` |

## `wiki-search`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | article_shown | pass | passed | 4803 ms | 0 | Playwright (software) | `wiki-search/01/result.json` |
| 2 | article_shown | pass | passed | 4174 ms | 0 | Playwright (software) | `wiki-search/02/result.json` |
| 3 | article_shown | pass | passed | 4217 ms | 0 | Playwright (software) | `wiki-search/03/result.json` |

Open a trace only for: `dynamic-controls` (flaky), `menu-random` (flaky), `notify-random` (flaky)
