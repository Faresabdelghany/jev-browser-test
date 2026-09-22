# Suite examples after the speed levers and fixes 2026-09-22T18:17:18+03:00

**NOT ALL PASS** · 10 spec(s) × 3 repeat(s), 2 worker(s), 122.3 s wall-clock · commit `0a8727c`

| spec | verdict | agreement | outcomes | median wall | Jev ms | requests | tokens in | confidence |
|---|---|---:|---|---:|---:|---:|---:|---:|
| `load-wait` | **PASS** | 100% | loaded 3/3 | 11147 ms | 1912 | 7 | 6949 | 0.96 |
| `menu-random` | **FLAKY** | 67% | entry_missing 2/3, all_entries 1/3 | 3793 ms | 332 | 2 | 1893 | None |
| `modal-close` | **PASS** | 100% | modal_closed 3/3 | 4673 ms | 920 | 4 | 3506 | 0.61 |
| `notify-random` | **FLAKY** | 67% | action_successful 2/3, action_unsuccessful 1/3 | 4390 ms | 590 | 3 | 2663 | 0.99 |
| `shop-add-second-item` | **PASS** | 100% | bike_light_in_cart 3/3 | 4324 ms | 947 | 4 | 10312 | 0.885 |
| `shop-checkout-error-account` | **EXPECTED (declared result in 3/3)** | 100% | undetermined 3/3 | 7298 ms | 3408 | 10 | 25660 | 0.93 |
| `shop-checkout-problem-account` | **BUG** | 100% | form_error 3/3 | 9282 ms | 2755 | 9 | 22740 | 0.89 |
| `shop-checkout` | **PASS** | 100% | order_complete 3/3 | 11142 ms | 2957 | 10 | 24392 | 0.98 |
| `todo-add-filter` | **PASS** | 100% | active_filtered 3/3 | 8718 ms | 2807 | 8 | 15120 | 0.925 |
| `wiki-search` | **PASS** | 100% | article_shown 3/3 | 11771 ms | 1399 | 4 | 34470 | 0.835 |

## `load-wait`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | loaded | pass | passed | 11168 ms | 0 | Hello World! | `load-wait/01/result.json` |
| 2 | loaded | pass | passed | 11147 ms | 0 | Hello World! | `load-wait/02/result.json` |
| 3 | loaded | pass | passed | 10723 ms | 0 | Hello World! | `load-wait/03/result.json` |

## `menu-random`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | entry_missing | bug | outcome | 4648 ms | 1 |  | `menu-random/01/result.json` |
| 2 | all_entries | pass | passed | 3793 ms | 0 |  | `menu-random/02/result.json` |
| 3 | entry_missing | bug | outcome | 3622 ms | 1 |  | `menu-random/03/result.json` |

## `modal-close`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | modal_closed | pass | passed | 4673 ms | 0 | If closed, it will not appear on subsequent page loads. | `modal-close/01/result.json` |
| 2 | modal_closed | pass | passed | 4645 ms | 0 | If closed, it will not appear on subsequent page loads. | `modal-close/02/result.json` |
| 3 | modal_closed | pass | passed | 5075 ms | 0 | If closed, it will not appear on subsequent page loads. | `modal-close/03/result.json` |

## `notify-random`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | action_successful | pass | passed | 4345 ms | 0 | Action successful | `notify-random/01/result.json` |
| 2 | action_unsuccessful | bug | outcome | 4390 ms | 1 | Action unsuccesful, please try again | `notify-random/02/result.json` |
| 3 | action_successful | pass | passed | 4580 ms | 0 | Action successful | `notify-random/03/result.json` |

## `shop-add-second-item`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | bike_light_in_cart | pass | passed | 4387 ms | 0 | Sauce Labs Bike Light | `shop-add-second-item/01/result.json` |
| 2 | bike_light_in_cart | pass | passed | 4324 ms | 0 | Sauce Labs Bike Light | `shop-add-second-item/02/result.json` |
| 3 | bike_light_in_cart | pass | passed | 4000 ms | 0 | Sauce Labs Bike Light | `shop-add-second-item/03/result.json` |

## `shop-checkout-error-account`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | undetermined (expected) | - | blocked | 7298 ms | 0 |  | `shop-checkout-error-account/01/result.json` |
| 2 | undetermined (expected) | - | blocked | 7165 ms | 0 |  | `shop-checkout-error-account/02/result.json` |
| 3 | undetermined (expected) | - | blocked | 10786 ms | 0 |  | `shop-checkout-error-account/03/result.json` |

## `shop-checkout-problem-account`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | form_error | bug | outcome | 11258 ms | 1 | Error: Last Name is required | `shop-checkout-problem-account/01/result.json` |
| 2 | form_error | bug | outcome | 8769 ms | 1 | Error: Last Name is required | `shop-checkout-problem-account/02/result.json` |
| 3 | form_error | bug | outcome | 9282 ms | 1 | Error: Last Name is required | `shop-checkout-problem-account/03/result.json` |

## `shop-checkout`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | order_complete | pass | passed | 9226 ms | 0 | Checkout: Complete! | `shop-checkout/01/result.json` |
| 2 | order_complete | pass | passed | 11142 ms | 0 | Checkout: Complete! | `shop-checkout/02/result.json` |
| 3 | order_complete | pass | passed | 14608 ms | 0 | Checkout: Complete! | `shop-checkout/03/result.json` |

## `todo-add-filter`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | active_filtered | pass | passed | 11624 ms | 0 | 1 item left | `todo-add-filter/01/result.json` |
| 2 | active_filtered | pass | passed | 7028 ms | 0 | 1 item left | `todo-add-filter/02/result.json` |
| 3 | active_filtered | pass | passed | 8718 ms | 0 | 1 item left | `todo-add-filter/03/result.json` |

## `wiki-search`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | article_shown | pass | passed | 11771 ms | 0 | Playwright (software) | `wiki-search/01/result.json` |
| 2 | article_shown | pass | passed | 15368 ms | 0 | Playwright (software) | `wiki-search/02/result.json` |
| 3 | article_shown | pass | passed | 11532 ms | 0 | Playwright (software) | `wiki-search/03/result.json` |

Open a trace only for: `menu-random` (flaky), `notify-random` (flaky)
