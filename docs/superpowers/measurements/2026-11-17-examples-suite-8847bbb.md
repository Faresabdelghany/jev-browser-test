# Suite seventeen non-hrm example specs at 8847bbb, 2 workers 2026-11-17T11:21:27+02:00

**NOT ALL PASS** · 17 spec(s) × 3 repeat(s), 2 worker(s), 130.9 s wall-clock · commit `8847bbb`

| spec | verdict | agreement | outcomes | median wall | Jev ms | requests | tokens in | confidence |
|---|---|---:|---|---:|---:|---:|---:|---:|
| `add-remove-elements` | **PASS** | 100% | one_delete_left 3/3 | 3755 ms | 380 | 3 | 3044 | 0.97 |
| `dynamic-controls` | **UNDETERMINED (suggested: none 3)** | 100% | undetermined 3/3 | 9755 ms | 1982 | 10 | 16067 | 0.88 |
| `forgot-password` | **PASS (declared result in 0/3)** | 100% | email_sent 3/3 | 3511 ms | 560 | 4 | 4427 | 0.98 |
| `load-wait` | **PASS** | 100% | loaded 3/3 | 7921 ms | 1191 | 7 | 8147 | 1 |
| `login-logout` | **PASS** | 100% | logged_out 3/3 | 4632 ms | 1031 | 6 | 9770 | 0.985 |
| `menu-random` | **FLAKY** | 67% | entry_missing 2/3, all_entries 1/3 | 2517 ms | 205 | 2 | 2126 | None |
| `modal-close` | **PASS** | 100% | modal_closed 3/3 | 10360 ms | 223 | 2 | 1796 | None |
| `notify-random` | **FLAKY** | 67% | action_unsuccessful 2/3, action_successful 1/3 | 3103 ms | 411 | 3 | 3268 | 0.95 |
| `shop-add-second-item` | **PASS** | 100% | bike_light_in_cart 3/3 | 2944 ms | 654 | 4 | 10869 | 0.895 |
| `shop-checkout-error-account` | **EXPECTED (declared result in 3/3)** | 100% | undetermined 3/3 | 5106 ms | 2119 | 10 | 26266 | 0.94 |
| `shop-checkout-problem-account` | **BUG** | 100% | form_error 3/3 | 4750 ms | 1706 | 9 | 23457 | 0.94 |
| `shop-checkout` | **PASS** | 100% | order_complete 3/3 | 4889 ms | 1757 | 10 | 24991 | 0.99 |
| `table-sort-due` | **EXPECTED (declared result in 3/3)** | 100% | undetermined 3/3 | 4387 ms | 835 | 4 | 10122 | 0.31 |
| `todo-add-filter` | **PASS** | 100% | active_filtered 3/3 | 3802 ms | 1443 | 8 | 15169 | 0.9 |
| `toolshop-search-cart` | **PASS** | 100% | in_cart 3/3 | 8285 ms | 2319 | 11 | 46191 | 0.94 |
| `web-form-submit` | **PASS** | 100% | form_submitted 3/3 | 4522 ms | 1592 | 9 | 23844 | 0.95 |
| `wiki-search` | **PASS** | 100% | article_shown 3/3 | 4417 ms | 799 | 4 | 34385 | 0.765 |

## `add-remove-elements`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | one_delete_left | pass | passed | 3755 ms | 0 | Delete | `add-remove-elements/01/result.json` |
| 2 | one_delete_left | pass | passed | 3755 ms | 0 | Delete | `add-remove-elements/02/result.json` |
| 3 | one_delete_left | pass | passed | 3198 ms | 0 | Delete | `add-remove-elements/03/result.json` |

## `dynamic-controls`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | undetermined | - | done_unverified | 9682 ms | 1 |  | `dynamic-controls/01/result.json` |
| 2 | undetermined | - | done_unverified | 9755 ms | 1 |  | `dynamic-controls/02/result.json` |
| 3 | undetermined | - | done_unverified | 9775 ms | 1 |  | `dynamic-controls/03/result.json` |

## `forgot-password`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | email_sent (NOT the expected result) | pass | passed | 3444 ms | 1 | Your e-mail's been sent! | `forgot-password/01/result.json` |
| 2 | email_sent (NOT the expected result) | pass | passed | 3511 ms | 1 | Your e-mail's been sent! | `forgot-password/02/result.json` |
| 3 | email_sent (NOT the expected result) | pass | passed | 3607 ms | 1 | Your e-mail's been sent! | `forgot-password/03/result.json` |

## `load-wait`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | loaded | pass | passed | 7690 ms | 0 | Hello World! | `load-wait/01/result.json` |
| 2 | loaded | pass | passed | 7921 ms | 0 | Hello World! | `load-wait/02/result.json` |
| 3 | loaded | pass | passed | 8023 ms | 0 | Hello World! | `load-wait/03/result.json` |

## `login-logout`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | logged_out | pass | passed | 4586 ms | 0 | Login Page | `login-logout/01/result.json` |
| 2 | logged_out | pass | passed | 4632 ms | 0 | Login Page | `login-logout/02/result.json` |
| 3 | logged_out | pass | passed | 4647 ms | 0 | Login Page | `login-logout/03/result.json` |

## `menu-random`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | all_entries | pass | passed | 2517 ms | 0 |  | `menu-random/01/result.json` |
| 2 | entry_missing | bug | outcome | 2527 ms | 1 |  | `menu-random/02/result.json` |
| 3 | entry_missing | bug | outcome | 2372 ms | 1 |  | `menu-random/03/result.json` |

## `modal-close`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | modal_closed | pass | passed | 2337 ms | 0 |  | `modal-close/01/result.json` |
| 2 | modal_closed | pass | passed | 12375 ms | 0 |  | `modal-close/02/result.json` |
| 3 | modal_closed | pass | passed | 10360 ms | 0 |  | `modal-close/03/result.json` |

## `notify-random`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | action_unsuccessful | bug | outcome | 3157 ms | 1 | Action unsuccesful, please try again | `notify-random/01/result.json` |
| 2 | action_successful | pass | passed | 3048 ms | 0 | Action successful | `notify-random/02/result.json` |
| 3 | action_unsuccessful | bug | outcome | 3103 ms | 1 | Action unsuccesful, please try again | `notify-random/03/result.json` |

## `shop-add-second-item`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | bike_light_in_cart | pass | passed | 3050 ms | 0 | Sauce Labs Bike Light | `shop-add-second-item/01/result.json` |
| 2 | bike_light_in_cart | pass | passed | 2944 ms | 0 | Sauce Labs Bike Light | `shop-add-second-item/02/result.json` |
| 3 | bike_light_in_cart | pass | passed | 2857 ms | 0 | Sauce Labs Bike Light | `shop-add-second-item/03/result.json` |

## `shop-checkout-error-account`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | undetermined (expected) | - | blocked | 5106 ms | 0 |  | `shop-checkout-error-account/01/result.json` |
| 2 | undetermined (expected) | - | blocked | 4954 ms | 0 |  | `shop-checkout-error-account/02/result.json` |
| 3 | undetermined (expected) | - | blocked | 5198 ms | 0 |  | `shop-checkout-error-account/03/result.json` |

## `shop-checkout-problem-account`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | form_error | bug | outcome | 4750 ms | 1 | Error: Last Name is required | `shop-checkout-problem-account/01/result.json` |
| 2 | form_error | bug | outcome | 4849 ms | 1 | Error: Last Name is required | `shop-checkout-problem-account/02/result.json` |
| 3 | form_error | bug | outcome | 4657 ms | 1 | Error: Last Name is required | `shop-checkout-problem-account/03/result.json` |

## `shop-checkout`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | order_complete | pass | passed | 4889 ms | 0 | Checkout: Complete! | `shop-checkout/01/result.json` |
| 2 | order_complete | pass | passed | 4880 ms | 0 | Checkout: Complete! | `shop-checkout/02/result.json` |
| 3 | order_complete | pass | passed | 5268 ms | 0 | Checkout: Complete! | `shop-checkout/03/result.json` |

## `table-sort-due`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | undetermined (expected) | - | low_confidence | 4387 ms | 0 |  | `table-sort-due/01/result.json` |
| 2 | undetermined (expected) | - | low_confidence | 4387 ms | 0 |  | `table-sort-due/02/result.json` |
| 3 | undetermined (expected) | - | low_confidence | 4598 ms | 0 |  | `table-sort-due/03/result.json` |

## `todo-add-filter`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | active_filtered | pass | passed | 3802 ms | 0 | 1 item left | `todo-add-filter/01/result.json` |
| 2 | active_filtered | pass | passed | 3702 ms | 0 | 1 item left | `todo-add-filter/02/result.json` |
| 3 | active_filtered | pass | passed | 3832 ms | 0 | 1 item left | `todo-add-filter/03/result.json` |

## `toolshop-search-cart`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | in_cart | pass | passed | 8285 ms | 0 | Proceed to checkout | `toolshop-search-cart/01/result.json` |
| 2 | in_cart | pass | passed | 7650 ms | 0 | Proceed to checkout | `toolshop-search-cart/02/result.json` |
| 3 | in_cart | pass | passed | 8924 ms | 0 | Proceed to checkout | `toolshop-search-cart/03/result.json` |

## `web-form-submit`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | form_submitted | pass | passed | 4705 ms | 0 | Form submitted | `web-form-submit/01/result.json` |
| 2 | form_submitted | pass | passed | 4522 ms | 0 | Form submitted | `web-form-submit/02/result.json` |
| 3 | form_submitted | pass | passed | 3679 ms | 0 | Form submitted | `web-form-submit/03/result.json` |

## `wiki-search`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | article_shown | pass | passed | 4435 ms | 0 | Playwright (software) | `wiki-search/01/result.json` |
| 2 | article_shown | pass | passed | 4417 ms | 0 | Playwright (software) | `wiki-search/02/result.json` |
| 3 | article_shown | pass | passed | 3735 ms | 0 | Playwright (software) | `wiki-search/03/result.json` |

Open a trace only for: `menu-random` (flaky), `notify-random` (flaky), `dynamic-controls` (undetermined)
