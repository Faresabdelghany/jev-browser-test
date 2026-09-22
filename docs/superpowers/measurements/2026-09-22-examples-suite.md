# Suite  2026-09-22T16:04:37+03:00

**NOT ALL PASS** · 10 spec(s) × 3 repeat(s), 2 worker(s), 96.9 s wall-clock · commit `b3996fa`

| spec | verdict | agreement | outcomes | median wall | Jev ms | requests | tokens in | confidence |
|---|---|---:|---|---:|---:|---:|---:|---:|
| `load-wait` | **PASS** | 100% | loaded 3/3 | 12709 ms | 3359 | 10 | 12901 | 0.94 |
| `menu-random` | **BUG** | 100% | entry_missing 3/3 | 3801 ms | 749 | 2 | 2117 | None |
| `modal-close` | **PASS** | 100% | modal_closed 3/3 | 5950 ms | 1625 | 5 | 5523 | 0.575 |
| `notify-random` | **FLAKY** | 67% | action_unsuccessful 2/3, action_successful 1/3 | 4619 ms | 1179 | 3 | 3205 | 0.99 |
| `shop-add-second-item` | **PASS** | 100% | bike_light_in_cart 3/3 | 4609 ms | 1704 | 5 | 13143 | 0.875 |
| `shop-checkout-error-account` | **UNDETERMINED (suggested: bug 3)** | 100% | undetermined 3/3 | 6520 ms | 3397 | 9 | 26151 | 0.94 |
| `shop-checkout-problem-account` | **BUG** | 100% | form_error 3/3 | 6355 ms | 3043 | 9 | 24641 | 0.87 |
| `shop-checkout` | **PASS** | 100% | order_complete 3/3 | 7572 ms | 3764 | 11 | 28911 | 0.98 |
| `todo-add-filter` | **PASS** | 100% | active_filtered 3/3 | 5925 ms | 3074 | 9 | 19349 | 0.915 |
| `wiki-search` | **PASS** | 100% | article_shown 3/3 | 5614 ms | 2094 | 5 | 47872 | 0.85 |

## `load-wait`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | loaded | pass | passed | 12710 ms | 0 |  | `load-wait/01/result.json` |
| 2 | loaded | pass | passed | 12709 ms | 0 |  | `load-wait/02/result.json` |
| 3 | loaded | pass | passed | 10320 ms | 0 |  | `load-wait/03/result.json` |

## `menu-random`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | entry_missing | bug | outcome | 3979 ms | 1 |  | `menu-random/01/result.json` |
| 2 | entry_missing | bug | outcome | 3801 ms | 1 |  | `menu-random/02/result.json` |
| 3 | entry_missing | bug | outcome | 3728 ms | 1 |  | `menu-random/03/result.json` |

## `modal-close`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | modal_closed | pass | passed | 5950 ms | 0 |  | `modal-close/01/result.json` |
| 2 | modal_closed | pass | passed | 5928 ms | 0 | If closed, it will not appear on subsequent page loads. | `modal-close/02/result.json` |
| 3 | modal_closed | pass | passed | 6028 ms | 0 | If closed, it will not appear on subsequent page loads. | `modal-close/03/result.json` |

## `notify-random`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | action_unsuccessful | bug | outcome | 4619 ms | 1 | Action unsuccesful, please try again | `notify-random/01/result.json` |
| 2 | action_successful | pass | passed | 5405 ms | 0 | Action successful | `notify-random/02/result.json` |
| 3 | action_unsuccessful | bug | outcome | 4569 ms | 1 | Action unsuccesful, please try again | `notify-random/03/result.json` |

## `shop-add-second-item`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | bike_light_in_cart | pass | passed | 4799 ms | 0 | Sauce Labs Bike Light | `shop-add-second-item/01/result.json` |
| 2 | bike_light_in_cart | pass | passed | 4609 ms | 0 | Sauce Labs Bike Light | `shop-add-second-item/02/result.json` |
| 3 | bike_light_in_cart | pass | passed | 4586 ms | 0 | Sauce Labs Bike Light | `shop-add-second-item/03/result.json` |

## `shop-checkout-error-account`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | undetermined | - | blocked | 6332 ms | 1 |  | `shop-checkout-error-account/01/result.json` |
| 2 | undetermined | - | blocked | 6520 ms | 1 |  | `shop-checkout-error-account/02/result.json` |
| 3 | undetermined | - | blocked | 6600 ms | 1 |  | `shop-checkout-error-account/03/result.json` |

## `shop-checkout-problem-account`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | form_error | bug | outcome | 6355 ms | 1 | Error: Last Name is required | `shop-checkout-problem-account/01/result.json` |
| 2 | form_error | bug | outcome | 6435 ms | 1 | Error: Last Name is required | `shop-checkout-problem-account/02/result.json` |
| 3 | form_error | bug | outcome | 6094 ms | 1 | Error: Last Name is required | `shop-checkout-problem-account/03/result.json` |

## `shop-checkout`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | order_complete | pass | passed | 7572 ms | 0 | Checkout: Complete! | `shop-checkout/01/result.json` |
| 2 | order_complete | pass | passed | 7357 ms | 0 | Checkout: Complete! | `shop-checkout/02/result.json` |
| 3 | order_complete | pass | passed | 7765 ms | 0 | Checkout: Complete! | `shop-checkout/03/result.json` |

## `todo-add-filter`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | active_filtered | pass | passed | 6242 ms | 0 | 1 item left | `todo-add-filter/01/result.json` |
| 2 | active_filtered | pass | passed | 5925 ms | 0 | 1 item left | `todo-add-filter/02/result.json` |
| 3 | active_filtered | pass | passed | 5921 ms | 0 | 1 item left | `todo-add-filter/03/result.json` |

## `wiki-search`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | article_shown | pass | passed | 5891 ms | 0 | Playwright (software) | `wiki-search/01/result.json` |
| 2 | article_shown | pass | passed | 5614 ms | 0 | Playwright (software) | `wiki-search/02/result.json` |
| 3 | article_shown | pass | passed | 5603 ms | 0 | Playwright (software) | `wiki-search/03/result.json` |

Open a trace only for: `notify-random` (flaky), `shop-checkout-error-account` (undetermined)
