# Suite final: w8-rerun-2 2026-11-17T18:17:59+02:00

**NOT ALL PASS** · 22 spec(s) × 1 repeat(s), 8 worker(s) over 7 host(s), at most 2 at once on any (opensource-demo.orangehrmlive.com: 1), 71.3 s wall-clock · commit `245f690`

Replay: 19 run(s) walked their saved path to its end, 0 handed over to Jev on the way.

| spec | verdict | agreement | outcomes | median wall | Jev ms | requests | tokens in | confidence |
|---|---|---:|---|---:|---:|---:|---:|---:|
| `add-remove-elements` | **PASS** | 100% | one_delete_left 1/1 | 5562 ms | 203 | 1 | 1344 | None |
| `dynamic-controls` | **PASS** | 100% | both_done 1/1 | 11847 ms | 198 | 1 | 1926 | None |
| `forgot-password` | **PASS** | 100% | email_sent 1/1 | 2956 ms | 210 | 1 | 1081 | None |
| `hrm-add-employee` | **PASS** | 100% | employee_saved 1/1 | 11559 ms | 296 | 1 | 7952 | None |
| `hrm-admin-add-user` | **PASS** | 100% | user_listed 1/1 | 20990 ms | 411 | 1 | 11213 | None |
| `hrm-leave-assign` | **PASS** | 100% | leave_scheduled 1/1 | 19259 ms | 408 | 1 | 8581 | None |
| `hrm-login` | **PASS** | 100% | dashboard_shown 1/1 | 5600 ms | 194 | 1 | 4022 | None |
| `hrm-pim-add-employee-list` | **PASS** | 100% | employee_listed 1/1 | 13894 ms | 294 | 1 | 6980 | None |
| `load-wait` | **PASS** | 100% | loaded 1/1 | 7736 ms | 193 | 1 | 1114 | None |
| `login-logout` | **PASS** | 100% | logged_out 1/1 | 4166 ms | 221 | 1 | 2359 | None |
| `menu-random` | **BUG** | 100% | entry_missing 1/1 | 3653 ms | 179 | 2 | 2132 | None |
| `modal-close` | **PASS** | 100% | modal_closed 1/1 | 3129 ms | 220 | 1 | 1224 | None |
| `notify-random` | **PASS** | 100% | action_successful 1/1 | 2768 ms | 192 | 1 | 1428 | None |
| `shop-add-second-item` | **PASS** | 100% | bike_light_in_cart 1/1 | 2715 ms | 246 | 1 | 1960 | None |
| `shop-checkout-error-account` | **EXPECTED (declared result in 1/1)** | 100% | undetermined 1/1 | 6084 ms | 2706 | 10 | 26266 | 0.91 |
| `shop-checkout-problem-account` | **BUG** | 100% | form_error 1/1 | 4404 ms | 1677 | 9 | 23457 | 0.93 |
| `shop-checkout` | **PASS** | 100% | order_complete 1/1 | 2811 ms | 193 | 1 | 2101 | None |
| `table-sort-due` | **EXPECTED (declared result in 1/1)** | 100% | undetermined 1/1 | 5060 ms | 1081 | 5 | 18612 | 0.21 |
| `todo-add-filter` | **PASS** | 100% | active_filtered 1/1 | 2989 ms | 219 | 1 | 2384 | None |
| `toolshop-search-cart` | **PASS** | 100% | in_cart 1/1 | 5644 ms | 249 | 1 | 5266 | None |
| `web-form-submit` | **PASS** | 100% | form_submitted 1/1 | 3070 ms | 175 | 1 | 1506 | None |
| `wiki-search` | **PASS** | 100% | article_shown 1/1 | 3645 ms | 570 | 1 | 16054 | None |

## `add-remove-elements`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | one_delete_left (replayed 3/3) | pass | passed | 5562 ms | 0 | Delete | `add-remove-elements/01/result.json` |

## `dynamic-controls`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | both_done (replayed 2/2) | pass | passed | 11847 ms | 0 | It's enabled! | `dynamic-controls/01/result.json` |

## `forgot-password`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | email_sent (replayed 2/2) | pass | passed | 2956 ms | 0 | Your e-mail's been sent! | `forgot-password/01/result.json` |

## `hrm-add-employee`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | employee_saved (replayed 5/5) | pass | passed | 11559 ms | 0 | Jevtest Runnertonmk0ka | `hrm-add-employee/01/result.json` |

## `hrm-admin-add-user`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | user_listed (replayed 12/12) | pass | passed | 20990 ms | 0 | jevtonmkcyz | `hrm-admin-add-user/01/result.json` |

## `hrm-leave-assign`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | leave_scheduled (replayed 15/15) | pass | passed | 19259 ms | 0 | (1) Record Found | `hrm-leave-assign/01/result.json` |

## `hrm-login`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | dashboard_shown (replayed 3/3) | pass | passed | 5600 ms | 0 | PIM | `hrm-login/01/result.json` |

## `hrm-pim-add-employee-list`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | employee_listed (replayed 9/9) | pass | passed | 13894 ms | 0 | (1) Record Found | `hrm-pim-add-employee-list/01/result.json` |

## `load-wait`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | loaded (replayed 1/1) | pass | passed | 7736 ms | 0 | Hello World! | `load-wait/01/result.json` |

## `login-logout`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | logged_out (replayed 4/4) | pass | passed | 4166 ms | 0 | Login Page | `login-logout/01/result.json` |

## `menu-random`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | entry_missing (replayed 0/0) | bug | outcome | 3653 ms | 1 |  | `menu-random/01/result.json` |

## `modal-close`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | modal_closed (replayed 1/1) | pass | passed | 3129 ms | 0 |  | `modal-close/01/result.json` |

## `notify-random`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | action_successful (replayed 1/1) | pass | passed | 2768 ms | 0 | Action successful | `notify-random/01/result.json` |

## `shop-add-second-item`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | bike_light_in_cart (replayed 2/2) | pass | passed | 2715 ms | 0 | Sauce Labs Bike Light | `shop-add-second-item/01/result.json` |

## `shop-checkout-error-account`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | undetermined (expected) | - | blocked | 6084 ms | 0 |  | `shop-checkout-error-account/01/result.json` |

## `shop-checkout-problem-account`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | form_error | bug | outcome | 4404 ms | 1 | Error: Last Name is required | `shop-checkout-problem-account/01/result.json` |

## `shop-checkout`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | order_complete (replayed 8/8) | pass | passed | 2811 ms | 0 | Thank you for your order! | `shop-checkout/01/result.json` |

## `table-sort-due`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | undetermined (expected) | - | low_confidence | 5060 ms | 0 |  | `table-sort-due/01/result.json` |

## `todo-add-filter`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | active_filtered (replayed 6/6) | pass | passed | 2989 ms | 0 | 1 item left | `todo-add-filter/01/result.json` |

## `toolshop-search-cart`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | in_cart (replayed 5/5) | pass | passed | 5644 ms | 0 | Proceed to checkout | `toolshop-search-cart/01/result.json` |

## `web-form-submit`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | form_submitted (replayed 6/6) | pass | passed | 3070 ms | 0 | Form submitted | `web-form-submit/01/result.json` |

## `wiki-search`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | article_shown (replayed 2/2) | pass | passed | 3645 ms | 0 | Playwright (software) | `wiki-search/01/result.json` |
