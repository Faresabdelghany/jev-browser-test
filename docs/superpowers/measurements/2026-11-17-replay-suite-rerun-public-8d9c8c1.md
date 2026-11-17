# Suite 0.8.0 replay, rerun (public), 8d9c8c1 2026-11-17T15:54:57+02:00

**NOT ALL PASS** · 17 spec(s) × 1 repeat(s), 1 worker(s), 79.0 s wall-clock · commit `8d9c8c1`

Replay: 13 run(s) walked their saved path to its end, 0 handed over to Jev on the way, 1 ended red after saved steps and ran again without the path (that second run is the result; 1 ended differently: `notify-random`).

| spec | verdict | agreement | outcomes | median wall | Jev ms | requests | tokens in | confidence |
|---|---|---:|---|---:|---:|---:|---:|---:|
| `add-remove-elements` | **PASS** | 100% | one_delete_left 1/1 | 2786 ms | 215 | 1 | 1344 | None |
| `dynamic-controls` | **PASS** | 100% | both_done 1/1 | 8683 ms | 215 | 1 | 1926 | None |
| `forgot-password` | **PASS** | 100% | email_sent 1/1 | 2862 ms | 223 | 1 | 1081 | None |
| `load-wait` | **PASS** | 100% | loaded 1/1 | 8648 ms | 196 | 1 | 1114 | None |
| `login-logout` | **PASS** | 100% | logged_out 1/1 | 3666 ms | 202 | 1 | 2359 | None |
| `menu-random` | **PASS** | 100% | all_entries 1/1 | 2693 ms | 189 | 1 | 1498 | None |
| `modal-close` | **PASS** | 100% | modal_closed 1/1 | 3195 ms | 197 | 1 | 1224 | None |
| `notify-random` | **PASS** | 100% | action_successful 1/1 | 8320 ms | 496 | 3 | 3218 | 0.91 |
| `shop-add-second-item` | **PASS** | 100% | bike_light_in_cart 1/1 | 2531 ms | 253 | 1 | 1960 | None |
| `shop-checkout-error-account` | **EXPECTED (declared result in 1/1)** | 100% | undetermined 1/1 | 5972 ms | 2153 | 10 | 26266 | 0.93 |
| `shop-checkout-problem-account` | **BUG** | 100% | form_error 1/1 | 5890 ms | 1816 | 9 | 23457 | 0.96 |
| `shop-checkout` | **PASS** | 100% | order_complete 1/1 | 4321 ms | 206 | 1 | 2101 | None |
| `table-sort-due` | **EXPECTED (declared result in 1/1)** | 100% | undetermined 1/1 | 4967 ms | 904 | 4 | 10122 | 0.31 |
| `todo-add-filter` | **PASS** | 100% | active_filtered 1/1 | 2828 ms | 237 | 1 | 2384 | None |
| `toolshop-search-cart` | **PASS** | 100% | in_cart 1/1 | 5718 ms | 282 | 1 | 5549 | None |
| `web-form-submit` | **PASS** | 100% | form_submitted 1/1 | 2443 ms | 214 | 1 | 1506 | None |
| `wiki-search` | **PASS** | 100% | article_shown 1/1 | 3462 ms | 338 | 1 | 16054 | None |

## `add-remove-elements`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | one_delete_left (replayed 3/3) | pass | passed | 2786 ms | 0 | Delete | `add-remove-elements/01/result.json` |

## `dynamic-controls`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | both_done (replayed 2/2) | pass | passed | 8683 ms | 0 | It's enabled! | `dynamic-controls/01/result.json` |

## `forgot-password`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | email_sent (replayed 2/2) | pass | passed | 2862 ms | 0 | Your e-mail's been sent! | `forgot-password/01/result.json` |

## `load-wait`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | loaded (replayed 1/1) | pass | passed | 8648 ms | 0 | Hello World! | `load-wait/01/result.json` |

## `login-logout`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | logged_out (replayed 4/4) | pass | passed | 3666 ms | 0 | Login Page | `login-logout/01/result.json` |

## `menu-random`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | all_entries (replayed 0/0) | pass | passed | 2693 ms | 0 |  | `menu-random/01/result.json` |

## `modal-close`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | modal_closed (replayed 1/1) | pass | passed | 3195 ms | 0 |  | `modal-close/01/result.json` |

## `notify-random`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | action_successful (without the saved path; with it: action_unsuccessful) | pass | passed | 8320 ms | 0 | Action successful | `notify-random/01-without-replay/result.json` |

## `shop-add-second-item`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | bike_light_in_cart (replayed 2/2) | pass | passed | 2531 ms | 0 | Sauce Labs Bike Light | `shop-add-second-item/01/result.json` |

## `shop-checkout-error-account`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | undetermined (expected) | - | blocked | 5972 ms | 0 |  | `shop-checkout-error-account/01/result.json` |

## `shop-checkout-problem-account`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | form_error | bug | outcome | 5890 ms | 1 | Error: Last Name is required | `shop-checkout-problem-account/01/result.json` |

## `shop-checkout`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | order_complete (replayed 8/8) | pass | passed | 4321 ms | 0 | Thank you for your order! | `shop-checkout/01/result.json` |

## `table-sort-due`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | undetermined (expected) | - | low_confidence | 4967 ms | 0 |  | `table-sort-due/01/result.json` |

## `todo-add-filter`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | active_filtered (replayed 6/6) | pass | passed | 2828 ms | 0 | 1 item left | `todo-add-filter/01/result.json` |

## `toolshop-search-cart`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | in_cart (replayed 5/5) | pass | passed | 5718 ms | 0 | Proceed to checkout | `toolshop-search-cart/01/result.json` |

## `web-form-submit`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | form_submitted (replayed 6/6) | pass | passed | 2443 ms | 0 | Form submitted | `web-form-submit/01/result.json` |

## `wiki-search`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | article_shown (replayed 2/2) | pass | passed | 3462 ms | 0 | Playwright (software) | `wiki-search/01/result.json` |
