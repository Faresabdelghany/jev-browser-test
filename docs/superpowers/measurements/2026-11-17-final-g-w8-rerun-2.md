# Suite final: w8-rerun-2 2026-11-17T18:51:36+02:00

**NOT ALL PASS** · 22 spec(s) × 1 repeat(s), 8 worker(s) over 7 host(s), at most 2 at once on any (opensource-demo.orangehrmlive.com: 1), 80.7 s wall-clock · commit `4e6a037`

Replay: 17 run(s) walked their saved path to its end, 0 handed over to Jev on the way, 1 ended red after saved steps and ran again without the path (that second run is the result).

| spec | verdict | agreement | outcomes | median wall | Jev ms | requests | tokens in | confidence |
|---|---|---:|---|---:|---:|---:|---:|---:|
| `add-remove-elements` | **PASS** | 100% | one_delete_left 1/1 | 5200 ms | 185 | 1 | 1344 | None |
| `dynamic-controls` | **PASS** | 100% | both_done 1/1 | 9421 ms | 222 | 1 | 1926 | None |
| `forgot-password` | **PASS** | 100% | email_sent 1/1 | 3001 ms | 182 | 1 | 1081 | None |
| `hrm-add-employee` | **PASS** | 100% | employee_saved 1/1 | 13259 ms | 267 | 1 | 8918 | None |
| `hrm-admin-add-user` | **PASS** | 100% | user_listed 1/1 | 20104 ms | 419 | 1 | 12556 | None |
| `hrm-leave-assign` | **PASS** | 100% | leave_scheduled 1/1 | 23758 ms | 526 | 1 | 8377 | None |
| `hrm-login` | **PASS** | 100% | dashboard_shown 1/1 | 4847 ms | 196 | 1 | 3672 | None |
| `hrm-pim-add-employee-list` | **PASS** | 100% | employee_listed 1/1 | 18682 ms | 399 | 1 | 7534 | None |
| `load-wait` | **PASS** | 100% | loaded 1/1 | 7555 ms | 198 | 1 | 1114 | None |
| `login-logout` | **PASS** | 100% | logged_out 1/1 | 3354 ms | 204 | 1 | 2359 | None |
| `menu-random` | **BUG** | 100% | entry_missing 1/1 | 3422 ms | 194 | 2 | 2126 | None |
| `modal-close` | **PASS** | 100% | modal_closed 1/1 | 3111 ms | 181 | 1 | 1224 | None |
| `notify-random` | **PASS** | 100% | action_successful 1/1 | 2669 ms | 184 | 1 | 1428 | None |
| `shop-add-second-item` | **PASS** | 100% | bike_light_in_cart 1/1 | 2571 ms | 192 | 1 | 1960 | None |
| `shop-checkout-error-account` | **EXPECTED (declared result in 1/1)** | 100% | undetermined 1/1 | 5449 ms | 2069 | 10 | 26266 | 0.92 |
| `shop-checkout-problem-account` | **BUG** | 100% | form_error 1/1 | 4376 ms | 1584 | 9 | 23466 | 0.96 |
| `shop-checkout` | **PASS** | 100% | order_complete 1/1 | 2902 ms | 229 | 1 | 2101 | None |
| `table-sort-due` | **EXPECTED (declared result in 1/1)** | 100% | undetermined 1/1 | 4360 ms | 845 | 4 | 10122 | 0.35 |
| `todo-add-filter` | **PASS** | 100% | active_filtered 1/1 | 2839 ms | 205 | 1 | 2384 | None |
| `toolshop-search-cart` | **UNDETERMINED (suggested: none 1)** | 100% | undetermined 1/1 | 10047 ms | 1411 | 7 | 29073 | 0.81 |
| `web-form-submit` | **PASS** | 100% | form_submitted 1/1 | 3129 ms | 187 | 1 | 1506 | None |
| `wiki-search` | **PASS** | 100% | article_shown 1/1 | 3366 ms | 307 | 1 | 14531 | None |

## `add-remove-elements`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | one_delete_left (replayed 3/3) | pass | passed | 5200 ms | 0 | Delete | `add-remove-elements/01/result.json` |

## `dynamic-controls`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | both_done (replayed 2/2) | pass | passed | 9421 ms | 0 | It's enabled! | `dynamic-controls/01/result.json` |

## `forgot-password`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | email_sent (replayed 2/2) | pass | passed | 3001 ms | 0 | Your e-mail's been sent! | `forgot-password/01/result.json` |

## `hrm-add-employee`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | employee_saved (replayed 5/5) | pass | passed | 13259 ms | 0 | Jevtest Runnertono3s1p | `hrm-add-employee/01/result.json` |

## `hrm-admin-add-user`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | user_listed (replayed 13/13) | pass | passed | 20104 ms | 0 | Jevtest Usertono450u | `hrm-admin-add-user/01/result.json` |

## `hrm-leave-assign`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | leave_scheduled (replayed 15/15) | pass | passed | 23758 ms | 0 | (1) Record Found | `hrm-leave-assign/01/result.json` |

## `hrm-login`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | dashboard_shown (replayed 3/3) | pass | passed | 4847 ms | 0 | PIM | `hrm-login/01/result.json` |

## `hrm-pim-add-employee-list`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | employee_listed (replayed 9/9) | pass | passed | 18682 ms | 0 | (1) Record Found | `hrm-pim-add-employee-list/01/result.json` |

## `load-wait`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | loaded (replayed 1/1) | pass | passed | 7555 ms | 0 | Hello World! | `load-wait/01/result.json` |

## `login-logout`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | logged_out (replayed 4/4) | pass | passed | 3354 ms | 0 | Login Page | `login-logout/01/result.json` |

## `menu-random`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | entry_missing | bug | outcome | 3422 ms | 1 |  | `menu-random/01/result.json` |

## `modal-close`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | modal_closed (replayed 1/1) | pass | passed | 3111 ms | 0 |  | `modal-close/01/result.json` |

## `notify-random`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | action_successful (replayed 1/1) | pass | passed | 2669 ms | 0 | Action successful | `notify-random/01/result.json` |

## `shop-add-second-item`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | bike_light_in_cart (replayed 2/2) | pass | passed | 2571 ms | 0 | Sauce Labs Bike Light | `shop-add-second-item/01/result.json` |

## `shop-checkout-error-account`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | undetermined (expected) | - | blocked | 5449 ms | 0 |  | `shop-checkout-error-account/01/result.json` |

## `shop-checkout-problem-account`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | form_error | bug | outcome | 4376 ms | 1 | Error: Last Name is required | `shop-checkout-problem-account/01/result.json` |

## `shop-checkout`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | order_complete (replayed 8/8) | pass | passed | 2902 ms | 0 | Thank you for your order! | `shop-checkout/01/result.json` |

## `table-sort-due`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | undetermined (expected) | - | low_confidence | 4360 ms | 0 |  | `table-sort-due/01/result.json` |

## `todo-add-filter`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | active_filtered (replayed 6/6) | pass | passed | 2839 ms | 0 | 1 item left | `todo-add-filter/01/result.json` |

## `toolshop-search-cart`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | undetermined (without the saved path; with it: undetermined) | - | blocked | 10047 ms | 1 |  | `toolshop-search-cart/01-without-replay/result.json` |

## `web-form-submit`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | form_submitted (replayed 6/6) | pass | passed | 3129 ms | 0 | Form submitted | `web-form-submit/01/result.json` |

## `wiki-search`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | article_shown (replayed 2/2) | pass | passed | 3366 ms | 0 | Playwright (software) | `wiki-search/01/result.json` |

Open a trace only for: `toolshop-search-cart` (undetermined)
