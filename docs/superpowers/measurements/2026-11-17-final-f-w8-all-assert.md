# Suite final: w8-all-assert 2026-11-17T18:26:40+02:00

**NOT ALL PASS** · 22 spec(s) × 1 repeat(s), 8 worker(s) over 7 host(s), at most 2 at once on any (opensource-demo.orangehrmlive.com: 1), 62.7 s wall-clock · commit `245f690`

Replay: 18 run(s) walked their saved path to its end, 0 handed over to Jev on the way, 1 ended red after saved steps and ran again without the path (that second run is the result).

| spec | verdict | agreement | outcomes | median wall | Jev ms | requests | tokens in | confidence |
|---|---|---:|---|---:|---:|---:|---:|---:|
| `add-remove-elements` | **PASS** | 100% | one_delete_left 1/1 | 2349 ms | 0 | 0 | 0 | None |
| `dynamic-controls` | **PASS** | 100% | both_done 1/1 | 8413 ms | 204 | 1 | 1935 | None |
| `forgot-password` | **PASS** | 100% | email_sent 1/1 | 1801 ms | 0 | 0 | 0 | None |
| `hrm-add-employee` | **PASS** | 100% | employee_saved 1/1 | 11706 ms | 0 | 0 | 0 | None |
| `hrm-admin-add-user` | **PASS** | 100% | user_listed 1/1 | 16903 ms | 0 | 0 | 0 | None |
| `hrm-leave-assign` | **PASS** | 100% | leave_scheduled 1/1 | 18249 ms | 0 | 0 | 0 | None |
| `hrm-login` | **PASS** | 100% | dashboard_shown 1/1 | 2886 ms | 228 | 1 | 2571 | None |
| `hrm-pim-add-employee-list` | **PASS** | 100% | employee_listed 1/1 | 12953 ms | 0 | 0 | 0 | None |
| `load-wait` | **PASS** | 100% | loaded 1/1 | 6290 ms | 0 | 0 | 0 | None |
| `login-logout` | **PASS** | 100% | logged_out 1/1 | 2055 ms | 0 | 0 | 0 | None |
| `menu-random` | **BUG** | 100% | entry_missing 1/1 | 2473 ms | 178 | 2 | 2132 | None |
| `modal-close` | **PASS** | 100% | modal_closed 1/1 | 2157 ms | 0 | 0 | 0 | None |
| `notify-random` | **BUG** | 100% | action_unsuccessful 1/1 | 4942 ms | 385 | 3 | 3268 | 0.92 |
| `shop-add-second-item` | **PASS** | 100% | bike_light_in_cart 1/1 | 2227 ms | 0 | 0 | 0 | None |
| `shop-checkout-error-account` | **EXPECTED (declared result in 1/1)** | 100% | undetermined 1/1 | 5908 ms | 1992 | 10 | 26266 | 0.93 |
| `shop-checkout-problem-account` | **BUG** | 100% | form_error 1/1 | 4239 ms | 1860 | 9 | 23466 | 0.95 |
| `shop-checkout` | **PASS** | 100% | order_complete 1/1 | 1741 ms | 0 | 0 | 0 | None |
| `table-sort-due` | **EXPECTED (declared result in 1/1)** | 100% | undetermined 1/1 | 3505 ms | 810 | 4 | 10122 | 0.29 |
| `todo-add-filter` | **PASS** | 100% | active_filtered 1/1 | 2095 ms | 0 | 0 | 0 | None |
| `toolshop-search-cart` | **PASS** | 100% | in_cart 1/1 | 5008 ms | 0 | 0 | 0 | None |
| `web-form-submit` | **PASS** | 100% | form_submitted 1/1 | 2064 ms | 0 | 0 | 0 | None |
| `wiki-search` | **PASS** | 100% | article_shown 1/1 | 2743 ms | 0 | 0 | 0 | None |

## `add-remove-elements`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | one_delete_left (replayed 3/3) | pass | passed | 2349 ms | 0 |  | `add-remove-elements/01/result.json` |

## `dynamic-controls`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | both_done (replayed 2/2) | pass | passed | 8413 ms | 0 | It's enabled! | `dynamic-controls/01/result.json` |

## `forgot-password`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | email_sent (replayed 2/2) | pass | passed | 1801 ms | 0 |  | `forgot-password/01/result.json` |

## `hrm-add-employee`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | employee_saved (replayed 5/5) | pass | passed | 11706 ms | 0 |  | `hrm-add-employee/01/result.json` |

## `hrm-admin-add-user`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | user_listed (replayed 12/12) | pass | passed | 16903 ms | 0 |  | `hrm-admin-add-user/01/result.json` |

## `hrm-leave-assign`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | leave_scheduled (replayed 15/15) | pass | passed | 18249 ms | 0 |  | `hrm-leave-assign/01/result.json` |

## `hrm-login`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | dashboard_shown (replayed 3/3) | pass | passed | 2886 ms | 0 | PIM | `hrm-login/01/result.json` |

## `hrm-pim-add-employee-list`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | employee_listed (replayed 9/9) | pass | passed | 12953 ms | 0 |  | `hrm-pim-add-employee-list/01/result.json` |

## `load-wait`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | loaded (replayed 1/1) | pass | passed | 6290 ms | 0 |  | `load-wait/01/result.json` |

## `login-logout`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | logged_out (replayed 4/4) | pass | passed | 2055 ms | 0 |  | `login-logout/01/result.json` |

## `menu-random`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | entry_missing (replayed 0/0) | bug | outcome | 2473 ms | 1 |  | `menu-random/01/result.json` |

## `modal-close`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | modal_closed (replayed 1/1) | pass | passed | 2157 ms | 0 |  | `modal-close/01/result.json` |

## `notify-random`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | action_unsuccessful (without the saved path; with it: action_unsuccessful) | bug | outcome | 4942 ms | 1 | Action unsuccesful, please try again | `notify-random/01-without-replay/result.json` |

## `shop-add-second-item`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | bike_light_in_cart (replayed 2/2) | pass | passed | 2227 ms | 0 |  | `shop-add-second-item/01/result.json` |

## `shop-checkout-error-account`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | undetermined (expected) | - | blocked | 5908 ms | 0 |  | `shop-checkout-error-account/01/result.json` |

## `shop-checkout-problem-account`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | form_error | bug | outcome | 4239 ms | 1 | Error: Last Name is required | `shop-checkout-problem-account/01/result.json` |

## `shop-checkout`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | order_complete (replayed 8/8) | pass | passed | 1741 ms | 0 |  | `shop-checkout/01/result.json` |

## `table-sort-due`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | undetermined (expected) | - | low_confidence | 3505 ms | 0 |  | `table-sort-due/01/result.json` |

## `todo-add-filter`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | active_filtered (replayed 6/6) | pass | passed | 2095 ms | 0 |  | `todo-add-filter/01/result.json` |

## `toolshop-search-cart`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | in_cart (replayed 5/5) | pass | passed | 5008 ms | 0 |  | `toolshop-search-cart/01/result.json` |

## `web-form-submit`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | form_submitted (replayed 6/6) | pass | passed | 2064 ms | 0 |  | `web-form-submit/01/result.json` |

## `wiki-search`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | article_shown (replayed 2/2) | pass | passed | 2743 ms | 0 |  | `wiki-search/01/result.json` |
