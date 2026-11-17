# Suite 0.8.0 replay, rerun, verify assert (public), 8d9c8c1 2026-11-17T15:56:04+02:00

**NOT ALL PASS** · 17 spec(s) × 1 repeat(s), 1 worker(s), 67.4 s wall-clock · commit `8d9c8c1`

Replay: 14 run(s) walked their saved path to its end, 0 handed over to Jev on the way.

| spec | verdict | agreement | outcomes | median wall | Jev ms | requests | tokens in | confidence |
|---|---|---:|---|---:|---:|---:|---:|---:|
| `add-remove-elements` | **PASS** | 100% | one_delete_left 1/1 | 2657 ms | 0 | 0 | 0 | None |
| `dynamic-controls` | **PASS** | 100% | both_done 1/1 | 8556 ms | 0 | 0 | 0 | None |
| `forgot-password` | **PASS** | 100% | email_sent 1/1 | 3488 ms | 0 | 0 | 0 | None |
| `load-wait` | **PASS** | 100% | loaded 1/1 | 7351 ms | 0 | 0 | 0 | None |
| `login-logout` | **PASS** | 100% | logged_out 1/1 | 3960 ms | 0 | 0 | 0 | None |
| `menu-random` | **PASS** | 100% | all_entries 1/1 | 2015 ms | 0 | 0 | 0 | None |
| `modal-close` | **PASS** | 100% | modal_closed 1/1 | 3197 ms | 0 | 0 | 0 | None |
| `notify-random` | **PASS** | 100% | action_successful 1/1 | 2803 ms | 0 | 0 | 0 | None |
| `shop-add-second-item` | **PASS** | 100% | bike_light_in_cart 1/1 | 2014 ms | 0 | 0 | 0 | None |
| `shop-checkout-error-account` | **EXPECTED (declared result in 1/1)** | 100% | undetermined 1/1 | 5427 ms | 2123 | 10 | 26266 | 0.93 |
| `shop-checkout-problem-account` | **BUG** | 100% | form_error 1/1 | 5495 ms | 1622 | 9 | 23457 | 0.94 |
| `shop-checkout` | **PASS** | 100% | order_complete 1/1 | 3055 ms | 0 | 0 | 0 | None |
| `table-sort-due` | **EXPECTED (declared result in 1/1)** | 100% | undetermined 1/1 | 4588 ms | 898 | 4 | 10122 | 0.35 |
| `todo-add-filter` | **PASS** | 100% | active_filtered 1/1 | 2347 ms | 0 | 0 | 0 | None |
| `toolshop-search-cart` | **PASS** | 100% | in_cart 1/1 | 5214 ms | 0 | 0 | 0 | None |
| `web-form-submit` | **PASS** | 100% | form_submitted 1/1 | 2187 ms | 0 | 0 | 0 | None |
| `wiki-search` | **PASS** | 100% | article_shown 1/1 | 2998 ms | 0 | 0 | 0 | None |

## `add-remove-elements`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | one_delete_left (replayed 3/3) | pass | passed | 2657 ms | 0 |  | `add-remove-elements/01/result.json` |

## `dynamic-controls`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | both_done (replayed 2/2) | pass | passed | 8556 ms | 0 |  | `dynamic-controls/01/result.json` |

## `forgot-password`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | email_sent (replayed 2/2) | pass | passed | 3488 ms | 0 |  | `forgot-password/01/result.json` |

## `load-wait`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | loaded (replayed 1/1) | pass | passed | 7351 ms | 0 |  | `load-wait/01/result.json` |

## `login-logout`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | logged_out (replayed 4/4) | pass | passed | 3960 ms | 0 |  | `login-logout/01/result.json` |

## `menu-random`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | all_entries (replayed 0/0) | pass | passed | 2015 ms | 0 |  | `menu-random/01/result.json` |

## `modal-close`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | modal_closed (replayed 1/1) | pass | passed | 3197 ms | 0 |  | `modal-close/01/result.json` |

## `notify-random`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | action_successful (replayed 1/1) | pass | passed | 2803 ms | 0 |  | `notify-random/01/result.json` |

## `shop-add-second-item`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | bike_light_in_cart (replayed 2/2) | pass | passed | 2014 ms | 0 |  | `shop-add-second-item/01/result.json` |

## `shop-checkout-error-account`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | undetermined (expected) | - | blocked | 5427 ms | 0 |  | `shop-checkout-error-account/01/result.json` |

## `shop-checkout-problem-account`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | form_error | bug | outcome | 5495 ms | 1 | Error: Last Name is required | `shop-checkout-problem-account/01/result.json` |

## `shop-checkout`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | order_complete (replayed 8/8) | pass | passed | 3055 ms | 0 |  | `shop-checkout/01/result.json` |

## `table-sort-due`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | undetermined (expected) | - | low_confidence | 4588 ms | 0 |  | `table-sort-due/01/result.json` |

## `todo-add-filter`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | active_filtered (replayed 6/6) | pass | passed | 2347 ms | 0 |  | `todo-add-filter/01/result.json` |

## `toolshop-search-cart`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | in_cart (replayed 5/5) | pass | passed | 5214 ms | 0 |  | `toolshop-search-cart/01/result.json` |

## `web-form-submit`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | form_submitted (replayed 6/6) | pass | passed | 2187 ms | 0 |  | `web-form-submit/01/result.json` |

## `wiki-search`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | article_shown (replayed 2/2) | pass | passed | 2998 ms | 0 |  | `wiki-search/01/result.json` |
