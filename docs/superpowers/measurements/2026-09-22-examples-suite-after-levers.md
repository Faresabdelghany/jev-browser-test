# Suite  2026-09-22T16:42:37+03:00

**NOT ALL PASS** · 10 spec(s) × 3 repeat(s), 2 worker(s), 97.4 s wall-clock · commit `188e50e`

| spec | verdict | agreement | outcomes | median wall | Jev ms | requests | tokens in | confidence |
|---|---|---:|---|---:|---:|---:|---:|---:|
| `load-wait` | **PASS** | 100% | loaded 3/3 | 12443 ms | 2751 | 8 | 8059 | 0.97 |
| `menu-random` | **FLAKY** | 67% | entry_missing 2/3, all_entries 1/3 | 3741 ms | 734 | 2 | 1893 | None |
| `modal-close` | **PASS** | 100% | modal_closed 3/3 | 5805 ms | 1589 | 5 | 4572 | 0.585 |
| `notify-random` | **FLAKY** | 67% | action_unsuccessful 2/3, action_successful 1/3 | 4492 ms | 1080 | 3 | 2692 | 0.99 |
| `shop-add-second-item` | **PASS** | 100% | bike_light_in_cart 3/3 | 4678 ms | 1816 | 5 | 12193 | 0.9 |
| `shop-checkout-error-account` | **UNDETERMINED (suggested: bug 3)** | 100% | undetermined 3/3 | 6742 ms | 3740 | 10 | 25660 | 0.94 |
| `shop-checkout-problem-account` | **BUG** | 100% | form_error 3/3 | 6209 ms | 3025 | 9 | 22740 | 0.88 |
| `shop-checkout` | **PASS** | 100% | order_complete 3/3 | 7522 ms | 3689 | 11 | 26523 | 0.98 |
| `todo-add-filter` | **PASS** | 100% | active_filtered 3/3 | 5838 ms | 2950 | 9 | 17469 | 0.93 |
| `wiki-search` | **PASS** | 100% | article_shown 3/3 | 5715 ms | 2050 | 5 | 43990 | 0.85 |

## `load-wait`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | loaded | pass | passed | 12443 ms | 0 | Hello World! | `load-wait/01/result.json` |
| 2 | loaded | pass | passed | 12474 ms | 0 | Hello World! | `load-wait/02/result.json` |
| 3 | loaded | pass | passed | 11325 ms | 0 | Hello World! | `load-wait/03/result.json` |

## `menu-random`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | all_entries | pass | passed | 4495 ms | 0 |  | `menu-random/01/result.json` |
| 2 | entry_missing | bug | outcome | 3741 ms | 1 |  | `menu-random/02/result.json` |
| 3 | entry_missing | bug | outcome | 3651 ms | 1 |  | `menu-random/03/result.json` |

## `modal-close`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | modal_closed | pass | passed | 5697 ms | 0 | If closed, it will not appear on subsequent page loads. | `modal-close/01/result.json` |
| 2 | modal_closed | pass | passed | 5848 ms | 0 | If closed, it will not appear on subsequent page loads. | `modal-close/02/result.json` |
| 3 | modal_closed | pass | passed | 5805 ms | 0 | If closed, it will not appear on subsequent page loads. | `modal-close/03/result.json` |

## `notify-random`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | action_unsuccessful | bug | outcome | 4492 ms | 1 | Action unsuccesful, please try again | `notify-random/01/result.json` |
| 2 | action_unsuccessful | bug | outcome | 4409 ms | 1 | Action unsuccesful, please try again | `notify-random/02/result.json` |
| 3 | action_successful | pass | passed | 5525 ms | 0 | Action successful | `notify-random/03/result.json` |

## `shop-add-second-item`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | bike_light_in_cart | pass | passed | 4789 ms | 0 | Sauce Labs Bike Light | `shop-add-second-item/01/result.json` |
| 2 | bike_light_in_cart | pass | passed | 4678 ms | 0 | Sauce Labs Bike Light | `shop-add-second-item/02/result.json` |
| 3 | bike_light_in_cart | pass | passed | 4658 ms | 0 | Sauce Labs Bike Light | `shop-add-second-item/03/result.json` |

## `shop-checkout-error-account`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | undetermined | - | blocked | 6477 ms | 1 |  | `shop-checkout-error-account/01/result.json` |
| 2 | undetermined | - | blocked | 6742 ms | 1 |  | `shop-checkout-error-account/02/result.json` |
| 3 | undetermined | - | blocked | 6889 ms | 1 |  | `shop-checkout-error-account/03/result.json` |

## `shop-checkout-problem-account`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | form_error | bug | outcome | 6123 ms | 1 | Error: Last Name is required | `shop-checkout-problem-account/01/result.json` |
| 2 | form_error | bug | outcome | 6209 ms | 1 | Error: Last Name is required | `shop-checkout-problem-account/02/result.json` |
| 3 | form_error | bug | outcome | 6252 ms | 1 | Error: Last Name is required | `shop-checkout-problem-account/03/result.json` |

## `shop-checkout`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | order_complete | pass | passed | 7570 ms | 0 | Checkout: Complete! | `shop-checkout/01/result.json` |
| 2 | order_complete | pass | passed | 7431 ms | 0 | Checkout: Complete! | `shop-checkout/02/result.json` |
| 3 | order_complete | pass | passed | 7522 ms | 0 | Checkout: Complete! | `shop-checkout/03/result.json` |

## `todo-add-filter`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | active_filtered | pass | passed | 6288 ms | 0 | 1 item left | `todo-add-filter/01/result.json` |
| 2 | active_filtered | pass | passed | 5717 ms | 0 | 1 item left | `todo-add-filter/02/result.json` |
| 3 | active_filtered | pass | passed | 5838 ms | 0 | 1 item left | `todo-add-filter/03/result.json` |

## `wiki-search`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | article_shown | pass | passed | 5715 ms | 0 | Playwright (software) | `wiki-search/01/result.json` |
| 2 | article_shown | pass | passed | 5418 ms | 0 | Playwright (software) | `wiki-search/02/result.json` |
| 3 | article_shown | pass | passed | 5772 ms | 0 | Playwright (software) | `wiki-search/03/result.json` |

Open a trace only for: `menu-random` (flaky), `notify-random` (flaky), `shop-checkout-error-account` (undetermined)
