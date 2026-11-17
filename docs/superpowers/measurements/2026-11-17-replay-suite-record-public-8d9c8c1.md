# Suite 0.8.0 replay on, first run (public), 8d9c8c1 2026-11-17T15:45:50+02:00

**NOT ALL PASS** · 17 spec(s) × 1 repeat(s), 1 worker(s), 84.7 s wall-clock · commit `8d9c8c1`

Replay: 0 run(s) walked their saved path to its end, 0 handed over to Jev on the way.

| spec | verdict | agreement | outcomes | median wall | Jev ms | requests | tokens in | confidence |
|---|---|---:|---|---:|---:|---:|---:|---:|
| `add-remove-elements` | **PASS** | 100% | one_delete_left 1/1 | 4396 ms | 849 | 5 | 5862 | 0.96 |
| `dynamic-controls` | **PASS** | 100% | both_done 1/1 | 9314 ms | 2051 | 11 | 17446 | 0.83 |
| `forgot-password` | **PASS** | 100% | email_sent 1/1 | 3634 ms | 667 | 4 | 4427 | 0.98 |
| `load-wait` | **PASS** | 100% | loaded 1/1 | 9081 ms | 1422 | 7 | 8147 | 1 |
| `login-logout` | **PASS** | 100% | logged_out 1/1 | 4642 ms | 1024 | 6 | 9770 | 0.97 |
| `menu-random` | **BUG** | 100% | entry_missing 1/1 | 2563 ms | 208 | 2 | 2126 | None |
| `modal-close` | **PASS** | 100% | modal_closed 1/1 | 3541 ms | 646 | 4 | 4033 | 0.66 |
| `notify-random` | **PASS** | 100% | action_successful 1/1 | 3386 ms | 414 | 3 | 3218 | 0.83 |
| `shop-add-second-item` | **PASS** | 100% | bike_light_in_cart 1/1 | 2941 ms | 636 | 4 | 10869 | 0.865 |
| `shop-checkout-error-account` | **EXPECTED (declared result in 1/1)** | 100% | undetermined 1/1 | 5508 ms | 2277 | 10 | 26266 | 0.91 |
| `shop-checkout-problem-account` | **BUG** | 100% | form_error 1/1 | 4862 ms | 1660 | 9 | 23457 | 0.96 |
| `shop-checkout` | **PASS** | 100% | order_complete 1/1 | 5254 ms | 2044 | 10 | 24991 | 0.985 |
| `table-sort-due` | **EXPECTED (declared result in 1/1)** | 100% | undetermined 1/1 | 4577 ms | 853 | 4 | 10122 | 0.42 |
| `todo-add-filter` | **PASS** | 100% | active_filtered 1/1 | 4184 ms | 1551 | 8 | 15169 | 0.935 |
| `toolshop-search-cart` | **PASS** | 100% | in_cart 1/1 | 8276 ms | 2265 | 11 | 46217 | 0.94 |
| `web-form-submit` | **PASS** | 100% | form_submitted 1/1 | 4284 ms | 1754 | 8 | 20532 | 0.975 |
| `wiki-search` | **PASS** | 100% | article_shown 1/1 | 4240 ms | 769 | 4 | 34385 | 0.74 |

## `add-remove-elements`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | one_delete_left | pass | passed | 4396 ms | 0 | Delete | `add-remove-elements/01/result.json` |

## `dynamic-controls`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | both_done | pass | passed | 9314 ms | 0 | Add | `dynamic-controls/01/result.json` |

## `forgot-password`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | email_sent | pass | passed | 3634 ms | 0 | Your e-mail's been sent! | `forgot-password/01/result.json` |

## `load-wait`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | loaded | pass | passed | 9081 ms | 0 | Hello World! | `load-wait/01/result.json` |

## `login-logout`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | logged_out | pass | passed | 4642 ms | 0 | Login Page | `login-logout/01/result.json` |

## `menu-random`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | entry_missing | bug | outcome | 2563 ms | 1 |  | `menu-random/01/result.json` |

## `modal-close`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | modal_closed | pass | passed | 3541 ms | 0 |  | `modal-close/01/result.json` |

## `notify-random`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | action_successful | pass | passed | 3386 ms | 0 | Action successful | `notify-random/01/result.json` |

## `shop-add-second-item`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | bike_light_in_cart | pass | passed | 2941 ms | 0 | Sauce Labs Bike Light | `shop-add-second-item/01/result.json` |

## `shop-checkout-error-account`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | undetermined (expected) | - | blocked | 5508 ms | 0 |  | `shop-checkout-error-account/01/result.json` |

## `shop-checkout-problem-account`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | form_error | bug | outcome | 4862 ms | 1 | Error: Last Name is required | `shop-checkout-problem-account/01/result.json` |

## `shop-checkout`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | order_complete | pass | passed | 5254 ms | 0 | Checkout: Complete! | `shop-checkout/01/result.json` |

## `table-sort-due`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | undetermined (expected) | - | low_confidence | 4577 ms | 0 |  | `table-sort-due/01/result.json` |

## `todo-add-filter`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | active_filtered | pass | passed | 4184 ms | 0 | 1 item left | `todo-add-filter/01/result.json` |

## `toolshop-search-cart`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | in_cart | pass | passed | 8276 ms | 0 | Proceed to checkout | `toolshop-search-cart/01/result.json` |

## `web-form-submit`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | form_submitted | pass | passed | 4284 ms | 0 | Form submitted | `web-form-submit/01/result.json` |

## `wiki-search`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | article_shown | pass | passed | 4240 ms | 0 | Playwright (software) | `wiki-search/01/result.json` |
