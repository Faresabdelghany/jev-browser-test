# Suite final: w1-all-warm 2026-11-17T18:20:50+02:00

**NOT ALL PASS** · 22 spec(s) × 1 repeat(s), 1 worker(s), 170.5 s wall-clock · commit `245f690`

Replay: 15 run(s) walked their saved path to its end, 3 handed over to Jev on the way, 1 ended red after saved steps and ran again without the path (that second run is the result; 1 ended differently: `notify-random`).

| spec | verdict | agreement | outcomes | median wall | Jev ms | requests | tokens in | confidence |
|---|---|---:|---|---:|---:|---:|---:|---:|
| `add-remove-elements` | **PASS** | 100% | one_delete_left 1/1 | 2982 ms | 223 | 1 | 1344 | None |
| `dynamic-controls` | **PASS** | 100% | both_done 1/1 | 7772 ms | 240 | 1 | 1926 | None |
| `forgot-password` | **PASS** | 100% | email_sent 1/1 | 2265 ms | 200 | 1 | 1081 | None |
| `hrm-add-employee` | **BUG** | 100% | employee_id_taken 1/1 | 21967 ms | 1887 | 10 | 45062 | 0.905 |
| `hrm-admin-add-user` | **PASS** | 100% | user_listed 1/1 | 24496 ms | 494 | 1 | 11420 | None |
| `hrm-leave-assign` | **PASS** | 100% | leave_scheduled 1/1 | 39381 ms | 404 | 1 | 8581 | None |
| `hrm-login` | **PASS** | 100% | dashboard_shown 1/1 | 3393 ms | 198 | 1 | 3672 | None |
| `hrm-pim-add-employee-list` | **PASS** | 100% | employee_listed 1/1 | 21835 ms | 3198 | 14 | 90466 | 0.9 |
| `load-wait` | **PASS** | 100% | loaded 1/1 | 6599 ms | 179 | 1 | 1114 | None |
| `login-logout` | **PASS** | 100% | logged_out 1/1 | 2366 ms | 207 | 1 | 2359 | None |
| `menu-random` | **BUG** | 100% | entry_missing 1/1 | 2457 ms | 219 | 2 | 2132 | None |
| `modal-close` | **PASS** | 100% | modal_closed 1/1 | 2379 ms | 181 | 1 | 1224 | None |
| `notify-random` | **PASS** | 100% | action_successful 1/1 | 5204 ms | 413 | 3 | 3218 | 0.87 |
| `shop-add-second-item` | **PASS** | 100% | bike_light_in_cart 1/1 | 2284 ms | 197 | 1 | 2139 | None |
| `shop-checkout-error-account` | **UNDETERMINED (suggested: bug 1) (declared result in 0/1)** | 100% | undetermined 1/1 | 1762 ms | 395 | 2 | 7084 | 0.7 |
| `shop-checkout-problem-account` | **UNDETERMINED (suggested: bug 1)** | 100% | undetermined 1/1 | 1772 ms | 426 | 2 | 7086 | 0.64 |
| `shop-checkout` | **PASS** | 100% | order_complete 1/1 | 1971 ms | 204 | 1 | 2101 | None |
| `table-sort-due` | **EXPECTED (declared result in 1/1)** | 100% | undetermined 1/1 | 3592 ms | 874 | 4 | 10122 | 0.32 |
| `todo-add-filter` | **PASS** | 100% | active_filtered 1/1 | 2174 ms | 216 | 1 | 2384 | None |
| `toolshop-search-cart` | **PASS** | 100% | in_cart 1/1 | 7624 ms | 1231 | 7 | 31262 | 0.95 |
| `web-form-submit` | **PASS** | 100% | form_submitted 1/1 | 2812 ms | 190 | 1 | 1506 | None |
| `wiki-search` | **PASS** | 100% | article_shown 1/1 | 3340 ms | 407 | 1 | 14531 | None |

## `add-remove-elements`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | one_delete_left (replayed 3/3) | pass | passed | 2982 ms | 0 | Delete | `add-remove-elements/01/result.json` |

## `dynamic-controls`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | both_done (replayed 2/2) | pass | passed | 7772 ms | 0 | It's enabled! | `dynamic-controls/01/result.json` |

## `forgot-password`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | email_sent (replayed 2/2) | pass | passed | 2265 ms | 0 | Your e-mail's been sent! | `forgot-password/01/result.json` |

## `hrm-add-employee`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | employee_id_taken (replayed 0/5, Jev from step 1) | bug | outcome | 21967 ms | 1 | Employee Id already exists | `hrm-add-employee/01/result.json` |

## `hrm-admin-add-user`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | user_listed (replayed 12/12) | pass | passed | 24496 ms | 0 | jevtonmmw5w | `hrm-admin-add-user/01/result.json` |

## `hrm-leave-assign`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | leave_scheduled (replayed 15/15) | pass | passed | 39381 ms | 0 | (1) Record Found | `hrm-leave-assign/01/result.json` |

## `hrm-login`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | dashboard_shown (replayed 3/3) | pass | passed | 3393 ms | 0 | PIM | `hrm-login/01/result.json` |

## `hrm-pim-add-employee-list`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | employee_listed (replayed 0/9, Jev from step 1) | pass | passed | 21835 ms | 0 | (1) Record Found | `hrm-pim-add-employee-list/01/result.json` |

## `load-wait`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | loaded (replayed 1/1) | pass | passed | 6599 ms | 0 | Hello World! | `load-wait/01/result.json` |

## `login-logout`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | logged_out (replayed 4/4) | pass | passed | 2366 ms | 0 | Login Page | `login-logout/01/result.json` |

## `menu-random`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | entry_missing (replayed 0/0) | bug | outcome | 2457 ms | 1 |  | `menu-random/01/result.json` |

## `modal-close`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | modal_closed (replayed 1/1) | pass | passed | 2379 ms | 0 |  | `modal-close/01/result.json` |

## `notify-random`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | action_successful (without the saved path; with it: action_unsuccessful) | pass | passed | 5204 ms | 0 | Action successful | `notify-random/01-without-replay/result.json` |

## `shop-add-second-item`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | bike_light_in_cart (replayed 2/2) | pass | passed | 2284 ms | 0 | Sauce Labs Bike Light | `shop-add-second-item/01/result.json` |

## `shop-checkout-error-account`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | undetermined (NOT the expected result) | - | blocked | 1762 ms | 1 |  | `shop-checkout-error-account/01/result.json` |

## `shop-checkout-problem-account`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | undetermined | - | blocked | 1772 ms | 1 |  | `shop-checkout-problem-account/01/result.json` |

## `shop-checkout`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | order_complete (replayed 8/8) | pass | passed | 1971 ms | 0 | Thank you for your order! | `shop-checkout/01/result.json` |

## `table-sort-due`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | undetermined (expected) | - | low_confidence | 3592 ms | 0 |  | `table-sort-due/01/result.json` |

## `todo-add-filter`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | active_filtered (replayed 6/6) | pass | passed | 2174 ms | 0 | 1 item left | `todo-add-filter/01/result.json` |

## `toolshop-search-cart`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | in_cart (replayed 0/5, Jev from step 1) | pass | passed | 7624 ms | 0 | Proceed to checkout | `toolshop-search-cart/01/result.json` |

## `web-form-submit`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | form_submitted (replayed 6/6) | pass | passed | 2812 ms | 0 | Form submitted | `web-form-submit/01/result.json` |

## `wiki-search`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | article_shown (replayed 2/2) | pass | passed | 3340 ms | 0 | Playwright (software) | `wiki-search/01/result.json` |

Open a trace only for: `shop-checkout-error-account` (undetermined), `shop-checkout-problem-account` (undetermined)
