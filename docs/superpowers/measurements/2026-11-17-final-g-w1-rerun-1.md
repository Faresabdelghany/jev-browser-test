# Suite final: w1-rerun-1 2026-11-17T18:46:00+02:00

**NOT ALL PASS** · 22 spec(s) × 1 repeat(s), 1 worker(s), 147.4 s wall-clock · commit `4e6a037`

Replay: 16 run(s) walked their saved path to its end, 1 handed over to Jev on the way.

| spec | verdict | agreement | outcomes | median wall | Jev ms | requests | tokens in | confidence |
|---|---|---:|---|---:|---:|---:|---:|---:|
| `add-remove-elements` | **PASS** | 100% | one_delete_left 1/1 | 2884 ms | 180 | 1 | 1344 | None |
| `dynamic-controls` | **PASS** | 100% | both_done 1/1 | 8730 ms | 209 | 1 | 1926 | None |
| `forgot-password` | **PASS** | 100% | email_sent 1/1 | 2901 ms | 201 | 1 | 1081 | None |
| `hrm-add-employee` | **PASS** | 100% | employee_saved 1/1 | 12488 ms | 291 | 1 | 8908 | None |
| `hrm-admin-add-user` | **PASS** | 100% | user_listed 1/1 | 20771 ms | 416 | 1 | 15087 | None |
| `hrm-leave-assign` | **PASS** | 100% | leave_scheduled 1/1 | 25955 ms | 457 | 2 | 13283 | 0.75 |
| `hrm-login` | **PASS** | 100% | dashboard_shown 1/1 | 5051 ms | 204 | 1 | 2571 | None |
| `hrm-pim-add-employee-list` | **PASS** | 100% | employee_listed 1/1 | 15004 ms | 279 | 1 | 7092 | None |
| `load-wait` | **PASS** | 100% | loaded 1/1 | 7729 ms | 214 | 1 | 1114 | None |
| `login-logout` | **PASS** | 100% | logged_out 1/1 | 3722 ms | 174 | 1 | 2359 | None |
| `menu-random` | **BUG** | 100% | entry_missing 1/1 | 2521 ms | 184 | 2 | 2126 | None |
| `modal-close` | **PASS** | 100% | modal_closed 1/1 | 3089 ms | 197 | 1 | 1224 | None |
| `notify-random` | **BUG** | 100% | action_unsuccessful 1/1 | 3257 ms | 397 | 3 | 3268 | 0.93 |
| `shop-add-second-item` | **PASS** | 100% | bike_light_in_cart 1/1 | 1940 ms | 253 | 1 | 1960 | None |
| `shop-checkout-error-account` | **EXPECTED (declared result in 1/1)** | 100% | undetermined 1/1 | 4865 ms | 1963 | 10 | 26266 | 0.91 |
| `shop-checkout-problem-account` | **BUG** | 100% | form_error 1/1 | 4486 ms | 1642 | 9 | 23457 | 0.96 |
| `shop-checkout` | **PASS** | 100% | order_complete 1/1 | 3144 ms | 425 | 1 | 2101 | None |
| `table-sort-due` | **EXPECTED (declared result in 1/1)** | 100% | undetermined 1/1 | 4602 ms | 957 | 4 | 10122 | 0.32 |
| `todo-add-filter` | **PASS** | 100% | active_filtered 1/1 | 2427 ms | 209 | 1 | 2384 | None |
| `toolshop-search-cart` | **PASS** | 100% | in_cart 1/1 | 6251 ms | 241 | 1 | 5594 | None |
| `web-form-submit` | **PASS** | 100% | form_submitted 1/1 | 2549 ms | 197 | 1 | 1506 | None |
| `wiki-search` | **PASS** | 100% | article_shown 1/1 | 3002 ms | 296 | 1 | 14531 | None |

## `add-remove-elements`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | one_delete_left (replayed 3/3) | pass | passed | 2884 ms | 0 | Delete | `add-remove-elements/01/result.json` |

## `dynamic-controls`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | both_done (replayed 2/2) | pass | passed | 8730 ms | 0 | It's enabled! | `dynamic-controls/01/result.json` |

## `forgot-password`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | email_sent (replayed 2/2) | pass | passed | 2901 ms | 0 | Your e-mail's been sent! | `forgot-password/01/result.json` |

## `hrm-add-employee`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | employee_saved (replayed 5/5) | pass | passed | 12488 ms | 0 | Jevtest Runnertonnsk6i | `hrm-add-employee/01/result.json` |

## `hrm-admin-add-user`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | user_listed (replayed 13/13) | pass | passed | 20771 ms | 0 | jevtonnt8bk | `hrm-admin-add-user/01/result.json` |

## `hrm-leave-assign`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | leave_scheduled (replayed 14/15, Jev from step 1) | pass | passed | 25955 ms | 0 | (1) Record Found | `hrm-leave-assign/01/result.json` |

## `hrm-login`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | dashboard_shown (replayed 3/3) | pass | passed | 5051 ms | 0 | PIM | `hrm-login/01/result.json` |

## `hrm-pim-add-employee-list`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | employee_listed (replayed 9/9) | pass | passed | 15004 ms | 0 | (1) Record Found | `hrm-pim-add-employee-list/01/result.json` |

## `load-wait`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | loaded (replayed 1/1) | pass | passed | 7729 ms | 0 | Hello World! | `load-wait/01/result.json` |

## `login-logout`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | logged_out (replayed 4/4) | pass | passed | 3722 ms | 0 | Login Page | `login-logout/01/result.json` |

## `menu-random`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | entry_missing | bug | outcome | 2521 ms | 1 |  | `menu-random/01/result.json` |

## `modal-close`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | modal_closed (replayed 1/1) | pass | passed | 3089 ms | 0 |  | `modal-close/01/result.json` |

## `notify-random`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | action_unsuccessful | bug | outcome | 3257 ms | 1 | Action unsuccesful, please try again | `notify-random/01/result.json` |

## `shop-add-second-item`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | bike_light_in_cart (replayed 2/2) | pass | passed | 1940 ms | 0 | Sauce Labs Bike Light | `shop-add-second-item/01/result.json` |

## `shop-checkout-error-account`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | undetermined (expected) | - | blocked | 4865 ms | 0 |  | `shop-checkout-error-account/01/result.json` |

## `shop-checkout-problem-account`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | form_error | bug | outcome | 4486 ms | 1 | Error: Last Name is required | `shop-checkout-problem-account/01/result.json` |

## `shop-checkout`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | order_complete (replayed 8/8) | pass | passed | 3144 ms | 0 | Thank you for your order! | `shop-checkout/01/result.json` |

## `table-sort-due`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | undetermined (expected) | - | low_confidence | 4602 ms | 0 |  | `table-sort-due/01/result.json` |

## `todo-add-filter`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | active_filtered (replayed 6/6) | pass | passed | 2427 ms | 0 | 1 item left | `todo-add-filter/01/result.json` |

## `toolshop-search-cart`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | in_cart (replayed 5/5) | pass | passed | 6251 ms | 0 | Proceed to checkout | `toolshop-search-cart/01/result.json` |

## `web-form-submit`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | form_submitted (replayed 6/6) | pass | passed | 2549 ms | 0 | Form submitted | `web-form-submit/01/result.json` |

## `wiki-search`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | article_shown (replayed 2/2) | pass | passed | 3002 ms | 0 | Playwright (software) | `wiki-search/01/result.json` |
