# Suite final: w1-first 2026-11-17T18:43:32+02:00

**NOT ALL PASS** · 22 spec(s) × 1 repeat(s), 1 worker(s), 189.0 s wall-clock · commit `4e6a037`

Replay: 0 run(s) walked their saved path to its end, 0 handed over to Jev on the way.

| spec | verdict | agreement | outcomes | median wall | Jev ms | requests | tokens in | confidence |
|---|---|---:|---|---:|---:|---:|---:|---:|
| `add-remove-elements` | **PASS** | 100% | one_delete_left 1/1 | 3886 ms | 838 | 5 | 5862 | 0.96 |
| `dynamic-controls` | **PASS** | 100% | both_done 1/1 | 9270 ms | 1979 | 11 | 17471 | 0.84 |
| `forgot-password` | **PASS** | 100% | email_sent 1/1 | 3496 ms | 576 | 4 | 4427 | 0.99 |
| `hrm-add-employee` | **PASS** | 100% | employee_saved 1/1 | 28961 ms | 2875 | 15 | 56946 | 0.61 |
| `hrm-admin-add-user` | **PASS** | 100% | user_listed 1/1 | 28843 ms | 4469 | 19 | 105059 | 0.83 |
| `hrm-leave-assign` | **PASS** | 100% | leave_scheduled 1/1 | 25625 ms | 4843 | 23 | 131491 | 0.88 |
| `hrm-login` | **PASS** | 100% | dashboard_shown 1/1 | 6551 ms | 1019 | 6 | 14440 | 0.865 |
| `hrm-pim-add-employee-list` | **PASS** | 100% | employee_listed 1/1 | 17251 ms | 3711 | 17 | 99015 | 0.92 |
| `load-wait` | **PASS** | 100% | loaded 1/1 | 7901 ms | 1175 | 7 | 8147 | 1 |
| `login-logout` | **PASS** | 100% | logged_out 1/1 | 4796 ms | 990 | 6 | 9770 | 0.98 |
| `menu-random` | **BUG** | 100% | entry_missing 1/1 | 2456 ms | 200 | 2 | 2126 | None |
| `modal-close` | **PASS** | 100% | modal_closed 1/1 | 3293 ms | 657 | 4 | 4033 | 0.7 |
| `notify-random` | **BUG** | 100% | action_unsuccessful 1/1 | 3231 ms | 364 | 3 | 3268 | 0.96 |
| `shop-add-second-item` | **PASS** | 100% | bike_light_in_cart 1/1 | 3030 ms | 652 | 4 | 10869 | 0.88 |
| `shop-checkout-error-account` | **EXPECTED (declared result in 1/1)** | 100% | undetermined 1/1 | 5324 ms | 2092 | 10 | 26266 | 0.91 |
| `shop-checkout-problem-account` | **BUG** | 100% | form_error 1/1 | 4874 ms | 1642 | 9 | 23457 | 0.95 |
| `shop-checkout` | **PASS** | 100% | order_complete 1/1 | 4789 ms | 1745 | 10 | 24991 | 0.99 |
| `table-sort-due` | **EXPECTED (declared result in 1/1)** | 100% | undetermined 1/1 | 4528 ms | 867 | 4 | 10122 | 0.32 |
| `todo-add-filter` | **PASS** | 100% | active_filtered 1/1 | 4069 ms | 1535 | 8 | 15169 | 0.935 |
| `toolshop-search-cart` | **PASS** | 100% | in_cart 1/1 | 7522 ms | 1876 | 10 | 40633 | 0.82 |
| `web-form-submit` | **PASS** | 100% | form_submitted 1/1 | 5040 ms | 1608 | 9 | 23844 | 0.94 |
| `wiki-search` | **PASS** | 100% | article_shown 1/1 | 4258 ms | 749 | 4 | 34385 | 0.755 |

## `add-remove-elements`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | one_delete_left | pass | passed | 3886 ms | 0 | Delete | `add-remove-elements/01/result.json` |

## `dynamic-controls`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | both_done | pass | passed | 9270 ms | 0 | Add | `dynamic-controls/01/result.json` |

## `forgot-password`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | email_sent | pass | passed | 3496 ms | 0 | Your e-mail's been sent! | `forgot-password/01/result.json` |

## `hrm-add-employee`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | employee_saved | pass | passed | 28961 ms | 0 | Jevtest Runnertonnnbno | `hrm-add-employee/01/result.json` |

## `hrm-admin-add-user`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | user_listed | pass | passed | 28843 ms | 0 | Jevtest Usertonnohfp | `hrm-admin-add-user/01/result.json` |

## `hrm-leave-assign`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | leave_scheduled | pass | passed | 25625 ms | 0 | (1) Record Found | `hrm-leave-assign/01/result.json` |

## `hrm-login`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | dashboard_shown | pass | passed | 6551 ms | 0 | PIM | `hrm-login/01/result.json` |

## `hrm-pim-add-employee-list`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | employee_listed | pass | passed | 17251 ms | 0 | (1) Record Found | `hrm-pim-add-employee-list/01/result.json` |

## `load-wait`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | loaded | pass | passed | 7901 ms | 0 | Hello World! | `load-wait/01/result.json` |

## `login-logout`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | logged_out | pass | passed | 4796 ms | 0 | Login Page | `login-logout/01/result.json` |

## `menu-random`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | entry_missing | bug | outcome | 2456 ms | 1 |  | `menu-random/01/result.json` |

## `modal-close`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | modal_closed | pass | passed | 3293 ms | 0 |  | `modal-close/01/result.json` |

## `notify-random`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | action_unsuccessful | bug | outcome | 3231 ms | 1 | Action unsuccesful, please try again | `notify-random/01/result.json` |

## `shop-add-second-item`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | bike_light_in_cart | pass | passed | 3030 ms | 0 | Sauce Labs Bike Light | `shop-add-second-item/01/result.json` |

## `shop-checkout-error-account`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | undetermined (expected) | - | blocked | 5324 ms | 0 |  | `shop-checkout-error-account/01/result.json` |

## `shop-checkout-problem-account`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | form_error | bug | outcome | 4874 ms | 1 | Error: Last Name is required | `shop-checkout-problem-account/01/result.json` |

## `shop-checkout`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | order_complete | pass | passed | 4789 ms | 0 | Checkout: Complete! | `shop-checkout/01/result.json` |

## `table-sort-due`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | undetermined (expected) | - | low_confidence | 4528 ms | 0 |  | `table-sort-due/01/result.json` |

## `todo-add-filter`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | active_filtered | pass | passed | 4069 ms | 0 | 1 item left | `todo-add-filter/01/result.json` |

## `toolshop-search-cart`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | in_cart | pass | passed | 7522 ms | 0 | Proceed to checkout | `toolshop-search-cart/01/result.json` |

## `web-form-submit`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | form_submitted | pass | passed | 5040 ms | 0 | Form submitted | `web-form-submit/01/result.json` |

## `wiki-search`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | article_shown | pass | passed | 4258 ms | 0 | Playwright (software) | `wiki-search/01/result.json` |
