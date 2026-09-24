# Suite seventeen example specs (non-hrm) at 1b69699, 2 workers: the blank-layer deferral, covered_action_confidence 0.9 2026-09-24T14:21:19+03:00

**NOT ALL PASS** · 17 spec(s) × 3 repeat(s), 2 worker(s), 307.4 s wall-clock · commit `1b69699` · **3 environment/setup failure(s)** (the browser, the start URL or a setup step failed before the flow was observed; not counted as outcomes)

| spec | verdict | agreement | outcomes | median wall | Jev ms | requests | tokens in | confidence |
|---|---|---:|---|---:|---:|---:|---:|---:|
| `add-remove-elements` | **PASS** | 100% | one_delete_left 3/3 | 7379 ms | 1104 | 5 | 5078 | 0.96 |
| `dynamic-controls` | **PASS (environment/setup failures 1/3)** | 100% | both_done 2/2 | 33090.5 ms | 2270 | 9 | 12925.5 | 0.53 |
| `forgot-password` | **EXPECTED (declared result in 3/3)** | 100% | server_error 3/3 | 6152 ms | 846 | 4 | 3643 | 0.98 |
| `load-wait` | **PASS** | 100% | loaded 3/3 | 8727 ms | 1750 | 7 | 6991 | 0.96 |
| `login-logout` | **PASS (environment/setup failures 1/3)** | 100% | logged_out 2/2 | 5326 ms | 1428.5 | 6 | 8764 | 0.942 |
| `menu-random` | **FLAKY** | 67% | all_entries 2/3, entry_missing 1/3 | 11427 ms | 318 | 2 | 2012 | None |
| `modal-close` | **PASS (environment/setup failures 1/3)** | 100% | modal_closed 2/2 | 3973 ms | 825 | 4 | 3527 | 0.657 |
| `notify-random` | **PASS** | 100% | action_successful 3/3 | 33238 ms | 561 | 3 | 2790 | 0.99 |
| `shop-add-second-item` | **PASS** | 100% | bike_light_in_cart 3/3 | 3741 ms | 895 | 4 | 10333 | 0.85 |
| `shop-checkout-error-account` | **EXPECTED (declared result in 3/3)** | 100% | undetermined 3/3 | 6515 ms | 2938 | 10 | 25730 | 0.92 |
| `shop-checkout-problem-account` | **BUG** | 100% | form_error 3/3 | 5922 ms | 2352 | 9 | 22921 | 0.89 |
| `shop-checkout` | **PASS** | 100% | order_complete 3/3 | 6888 ms | 3228 | 10 | 24455 | 0.985 |
| `table-sort-due` | **EXPECTED (declared result in 3/3)** | 100% | undetermined 3/3 | 28323 ms | 1184 | 4 | 10035 | 0.36 |
| `todo-add-filter` | **PASS** | 100% | active_filtered 3/3 | 4936 ms | 2124 | 8 | 15169 | 0.93 |
| `toolshop-search-cart` | **PASS** | 100% | in_cart 3/3 | 7324 ms | 2135 | 8 | 30366 | 0.785 |
| `web-form-submit` | **PASS** | 100% | form_submitted 3/3 | 5007 ms | 1967 | 8 | 20484 | 0.975 |
| `wiki-search` | **PASS** | 100% | article_shown 3/3 | 3748 ms | 1237 | 4 | 33909 | 0.835 |

## `add-remove-elements`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | one_delete_left | pass | passed | 5301 ms | 0 | Delete | `add-remove-elements/01/result.json` |
| 2 | one_delete_left | pass | passed | 11610 ms | 0 | Delete | `add-remove-elements/02/result.json` |
| 3 | one_delete_left | pass | passed | 7379 ms | 0 | Delete | `add-remove-elements/03/result.json` |

## `dynamic-controls`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | both_done | pass | passed | 32491 ms | 0 | It's enabled! | `dynamic-controls/01/result.json` |
| 2 | navigation failure | - | error | 33345 ms | 2 | navigation failed: TimeoutError: Page.goto: Timeout 30000ms exceeded. Call log: - navigating to "https://the-internet.he | `dynamic-controls/02/result.json` |
| 3 | both_done | pass | passed | 33690 ms | 0 | It's enabled! | `dynamic-controls/03/result.json` |

## `forgot-password`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | server_error (expected) | bug | outcome | 30057 ms | 0 | Internal Server Error | `forgot-password/01/result.json` |
| 2 | server_error (expected) | bug | outcome | 6152 ms | 0 | Internal Server Error | `forgot-password/02/result.json` |
| 3 | server_error (expected) | bug | outcome | 4162 ms | 0 | Internal Server Error | `forgot-password/03/result.json` |

## `load-wait`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | loaded | pass | passed | 8727 ms | 0 | Hello World! | `load-wait/01/result.json` |
| 2 | loaded | pass | passed | 8956 ms | 0 | Hello World! | `load-wait/02/result.json` |
| 3 | loaded | pass | passed | 8412 ms | 0 | Hello World! | `load-wait/03/result.json` |

## `login-logout`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | logged_out | pass | passed | 5290 ms | 0 | Login Page | `login-logout/01/result.json` |
| 2 | navigation failure | - | error | 33319 ms | 2 | navigation failed: TimeoutError: Page.goto: Timeout 30000ms exceeded. Call log: - navigating to "https://the-internet.he | `login-logout/02/result.json` |
| 3 | logged_out | pass | passed | 5362 ms | 0 | Login Page | `login-logout/03/result.json` |

## `menu-random`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | all_entries | pass | passed | 26053 ms | 0 |  | `menu-random/01/result.json` |
| 2 | all_entries | pass | passed | 11427 ms | 0 |  | `menu-random/02/result.json` |
| 3 | entry_missing | bug | outcome | 9677 ms | 1 |  | `menu-random/03/result.json` |

## `modal-close`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | navigation failure | - | error | 31027 ms | 2 | navigation failed: TimeoutError: Page.goto: Timeout 30000ms exceeded. Call log: - navigating to "https://the-internet.he | `modal-close/01/result.json` |
| 2 | modal_closed | pass | passed | 3952 ms | 0 | If closed, it will not appear on subsequent page loads. | `modal-close/02/result.json` |
| 3 | modal_closed | pass | passed | 3994 ms | 0 |  | `modal-close/03/result.json` |

## `notify-random`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | action_successful | pass | passed | 33238 ms | 0 | Action successful | `notify-random/01/result.json` |
| 2 | action_successful | pass | passed | 35849 ms | 0 | Action successful | `notify-random/02/result.json` |
| 3 | action_successful | pass | passed | 3806 ms | 0 | Action successful | `notify-random/03/result.json` |

## `shop-add-second-item`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | bike_light_in_cart | pass | passed | 3781 ms | 0 | Sauce Labs Bike Light | `shop-add-second-item/01/result.json` |
| 2 | bike_light_in_cart | pass | passed | 3741 ms | 0 | Sauce Labs Bike Light | `shop-add-second-item/02/result.json` |
| 3 | bike_light_in_cart | pass | passed | 3652 ms | 0 | Sauce Labs Bike Light | `shop-add-second-item/03/result.json` |

## `shop-checkout-error-account`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | undetermined (expected) | - | blocked | 6515 ms | 0 |  | `shop-checkout-error-account/01/result.json` |
| 2 | undetermined (expected) | - | blocked | 6534 ms | 0 |  | `shop-checkout-error-account/02/result.json` |
| 3 | undetermined (expected) | - | blocked | 6477 ms | 0 |  | `shop-checkout-error-account/03/result.json` |

## `shop-checkout-problem-account`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | form_error | bug | outcome | 5964 ms | 1 | Error: Last Name is required | `shop-checkout-problem-account/01/result.json` |
| 2 | form_error | bug | outcome | 5922 ms | 1 | Error: Last Name is required | `shop-checkout-problem-account/02/result.json` |
| 3 | form_error | bug | outcome | 5892 ms | 1 | Error: Last Name is required | `shop-checkout-problem-account/03/result.json` |

## `shop-checkout`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | order_complete | pass | passed | 6888 ms | 0 | Checkout: Complete! | `shop-checkout/01/result.json` |
| 2 | order_complete | pass | passed | 6339 ms | 0 | Checkout: Complete! | `shop-checkout/02/result.json` |
| 3 | order_complete | pass | passed | 7084 ms | 0 | Checkout: Complete! | `shop-checkout/03/result.json` |

## `table-sort-due`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | undetermined (expected) | - | low_confidence | 31052 ms | 0 |  | `table-sort-due/01/result.json` |
| 2 | undetermined (expected) | - | low_confidence | 26895 ms | 0 |  | `table-sort-due/02/result.json` |
| 3 | undetermined (expected) | - | low_confidence | 28323 ms | 0 |  | `table-sort-due/03/result.json` |

## `todo-add-filter`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | active_filtered | pass | passed | 5388 ms | 0 | 1 item left | `todo-add-filter/01/result.json` |
| 2 | active_filtered | pass | passed | 4863 ms | 0 | 1 item left | `todo-add-filter/02/result.json` |
| 3 | active_filtered | pass | passed | 4936 ms | 0 | 1 item left | `todo-add-filter/03/result.json` |

## `toolshop-search-cart`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | in_cart | pass | passed | 7324 ms | 0 | Proceed to checkout | `toolshop-search-cart/01/result.json` |
| 2 | in_cart | pass | passed | 5637 ms | 0 | Proceed to checkout | `toolshop-search-cart/02/result.json` |
| 3 | in_cart | pass | passed | 9615 ms | 0 | Proceed to checkout | `toolshop-search-cart/03/result.json` |

## `web-form-submit`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | form_submitted | pass | passed | 5297 ms | 0 | Form submitted | `web-form-submit/01/result.json` |
| 2 | form_submitted | pass | passed | 5007 ms | 0 | Form submitted | `web-form-submit/02/result.json` |
| 3 | form_submitted | pass | passed | 4648 ms | 0 | Form submitted | `web-form-submit/03/result.json` |

## `wiki-search`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | article_shown | pass | passed | 5135 ms | 0 |  | `wiki-search/01/result.json` |
| 2 | article_shown | pass | passed | 3748 ms | 0 | Playwright (software) | `wiki-search/02/result.json` |
| 3 | article_shown | pass | passed | 3482 ms | 0 | Playwright (software) | `wiki-search/03/result.json` |

Open a trace only for: `menu-random` (flaky)
