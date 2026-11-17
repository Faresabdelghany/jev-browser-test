# Suite final: w1-first 2026-11-17T18:10:40+02:00

**NOT ALL PASS** · 22 spec(s) × 1 repeat(s), 1 worker(s), 208.4 s wall-clock · commit `245f690`

Replay: 0 run(s) walked their saved path to its end, 0 handed over to Jev on the way.

| spec | verdict | agreement | outcomes | median wall | Jev ms | requests | tokens in | confidence |
|---|---|---:|---|---:|---:|---:|---:|---:|
| `add-remove-elements` | **PASS** | 100% | one_delete_left 1/1 | 3861 ms | 811 | 5 | 5862 | 0.93 |
| `dynamic-controls` | **PASS** | 100% | both_done 1/1 | 9503 ms | 2084 | 11 | 17327 | 0.85 |
| `forgot-password` | **PASS** | 100% | email_sent 1/1 | 3664 ms | 599 | 4 | 4427 | 0.98 |
| `hrm-add-employee` | **PASS** | 100% | employee_saved 1/1 | 16351 ms | 2097 | 11 | 47325 | 0.86 |
| `hrm-admin-add-user` | **PASS** | 100% | user_listed 1/1 | 27901 ms | 4506 | 19 | 103162 | 0.82 |
| `hrm-leave-assign` | **PASS** | 100% | leave_scheduled 1/1 | 24345 ms | 5593 | 23 | 133378 | 0.9 |
| `hrm-login` | **PASS** | 100% | dashboard_shown 1/1 | 8782 ms | 993 | 6 | 11882 | 0.9 |
| `hrm-pim-add-employee-list` | **PASS** | 100% | employee_listed 1/1 | 26122 ms | 4389 | 20 | 99316 | 0.93 |
| `load-wait` | **PASS** | 100% | loaded 1/1 | 7832 ms | 1175 | 7 | 8147 | 1 |
| `login-logout` | **PASS** | 100% | logged_out 1/1 | 4741 ms | 1012 | 6 | 9770 | 0.985 |
| `menu-random` | **PASS** | 100% | all_entries 1/1 | 2503 ms | 190 | 2 | 2238 | None |
| `modal-close` | **PASS** | 100% | modal_closed 1/1 | 3400 ms | 564 | 4 | 4033 | 0.625 |
| `notify-random` | **BUG** | 100% | action_unsuccessful 1/1 | 3343 ms | 427 | 3 | 3268 | 0.96 |
| `shop-add-second-item` | **PASS** | 100% | bike_light_in_cart 1/1 | 3019 ms | 615 | 4 | 10869 | 0.92 |
| `shop-checkout-error-account` | **EXPECTED (declared result in 1/1)** | 100% | undetermined 1/1 | 5217 ms | 1975 | 10 | 26266 | 0.96 |
| `shop-checkout-problem-account` | **BUG** | 100% | form_error 1/1 | 5018 ms | 1676 | 9 | 23457 | 0.95 |
| `shop-checkout` | **PASS** | 100% | order_complete 1/1 | 4933 ms | 1856 | 10 | 24991 | 0.99 |
| `table-sort-due` | **EXPECTED (declared result in 1/1)** | 100% | undetermined 1/1 | 4588 ms | 853 | 4 | 10122 | 0.3 |
| `todo-add-filter` | **PASS** | 100% | active_filtered 1/1 | 4151 ms | 1421 | 8 | 15169 | 0.905 |
| `toolshop-search-cart` | **UNDETERMINED (suggested: bug 1)** | 100% | undetermined 1/1 | 30502 ms | 2281 | 10 | 27026 | 0.74 |
| `web-form-submit` | **PASS** | 100% | form_submitted 1/1 | 4369 ms | 1561 | 8 | 20543 | 0.985 |
| `wiki-search` | **PASS** | 100% | article_shown 1/1 | 4191 ms | 1039 | 4 | 33491 | 0.775 |

## `add-remove-elements`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | one_delete_left | pass | passed | 3861 ms | 0 | Delete | `add-remove-elements/01/result.json` |

## `dynamic-controls`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | both_done | pass | passed | 9503 ms | 0 | Add | `dynamic-controls/01/result.json` |

## `forgot-password`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | email_sent | pass | passed | 3664 ms | 0 | Your e-mail's been sent! | `forgot-password/01/result.json` |

## `hrm-add-employee`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | employee_saved | pass | passed | 16351 ms | 0 | Jevtest Runnertonm40c2 | `hrm-add-employee/01/result.json` |

## `hrm-admin-add-user`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | user_listed | pass | passed | 27901 ms | 0 | jevtonm4tb8 | `hrm-admin-add-user/01/result.json` |

## `hrm-leave-assign`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | leave_scheduled | pass | passed | 24345 ms | 0 | (1) Record Found | `hrm-leave-assign/01/result.json` |

## `hrm-login`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | dashboard_shown | pass | passed | 8782 ms | 0 | PIM | `hrm-login/01/result.json` |

## `hrm-pim-add-employee-list`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | employee_listed | pass | passed | 26122 ms | 0 | (1) Record Found | `hrm-pim-add-employee-list/01/result.json` |

## `load-wait`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | loaded | pass | passed | 7832 ms | 0 | Hello World! | `load-wait/01/result.json` |

## `login-logout`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | logged_out | pass | passed | 4741 ms | 0 | Login Page | `login-logout/01/result.json` |

## `menu-random`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | all_entries | pass | passed | 2503 ms | 0 |  | `menu-random/01/result.json` |

## `modal-close`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | modal_closed | pass | passed | 3400 ms | 0 |  | `modal-close/01/result.json` |

## `notify-random`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | action_unsuccessful | bug | outcome | 3343 ms | 1 | Action unsuccesful, please try again | `notify-random/01/result.json` |

## `shop-add-second-item`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | bike_light_in_cart | pass | passed | 3019 ms | 0 | Sauce Labs Bike Light | `shop-add-second-item/01/result.json` |

## `shop-checkout-error-account`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | undetermined (expected) | - | blocked | 5217 ms | 0 |  | `shop-checkout-error-account/01/result.json` |

## `shop-checkout-problem-account`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | form_error | bug | outcome | 5018 ms | 1 | Error: Last Name is required | `shop-checkout-problem-account/01/result.json` |

## `shop-checkout`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | order_complete | pass | passed | 4933 ms | 0 | Checkout: Complete! | `shop-checkout/01/result.json` |

## `table-sort-due`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | undetermined (expected) | - | low_confidence | 4588 ms | 0 |  | `table-sort-due/01/result.json` |

## `todo-add-filter`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | active_filtered | pass | passed | 4151 ms | 0 | 1 item left | `todo-add-filter/01/result.json` |

## `toolshop-search-cart`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | undetermined | - | stuck | 30502 ms | 1 |  | `toolshop-search-cart/01/result.json` |

## `web-form-submit`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | form_submitted | pass | passed | 4369 ms | 0 | Form submitted | `web-form-submit/01/result.json` |

## `wiki-search`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | article_shown | pass | passed | 4191 ms | 0 | Playwright (software) | `wiki-search/01/result.json` |

Open a trace only for: `toolshop-search-cart` (undetermined)
