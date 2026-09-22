# Suite review-fixes acceptance (9c20838) 2026-09-22T11:51:08+03:00

**ALL PASS** · 2 spec(s) × 5 repeat(s), 4 worker(s), 20.8 s wall-clock · commit `9c20838`

| spec | verdict | agreement | outcomes | median wall | Jev ms | requests | tokens in | confidence |
|---|---|---:|---|---:|---:|---:|---:|---:|
| `smoke-login` | **PASS** | 100% | logged_in 5/5 | 7461 ms | 2297 | 6 | 8932 | 0.94 |
| `smoke-login-badpw` | **PASS** | 100% | bad_credentials 5/5 | 6736 ms | 1947 | 6 | 9774 | 0.92 |

## `smoke-login`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | logged_in | pass | passed | 7402 ms | 0 | You logged into a secure area! | `/private/tmp/claude-501/-Users-fares-Downloads-jev-browser-test/a7544d31-fa57-4bc4-91e7-6a3188f7ba64/scratchpad/suite-9c20838/smoke-login/01/result.json` |
| 2 | logged_in | pass | passed | 7421 ms | 0 | You logged into a secure area! | `/private/tmp/claude-501/-Users-fares-Downloads-jev-browser-test/a7544d31-fa57-4bc4-91e7-6a3188f7ba64/scratchpad/suite-9c20838/smoke-login/02/result.json` |
| 3 | logged_in | pass | passed | 7461 ms | 0 | You logged into a secure area! | `/private/tmp/claude-501/-Users-fares-Downloads-jev-browser-test/a7544d31-fa57-4bc4-91e7-6a3188f7ba64/scratchpad/suite-9c20838/smoke-login/03/result.json` |
| 4 | logged_in | pass | passed | 7555 ms | 0 | You logged into a secure area! | `/private/tmp/claude-501/-Users-fares-Downloads-jev-browser-test/a7544d31-fa57-4bc4-91e7-6a3188f7ba64/scratchpad/suite-9c20838/smoke-login/04/result.json` |
| 5 | logged_in | pass | passed | 7530 ms | 0 | You logged into a secure area! | `/private/tmp/claude-501/-Users-fares-Downloads-jev-browser-test/a7544d31-fa57-4bc4-91e7-6a3188f7ba64/scratchpad/suite-9c20838/smoke-login/05/result.json` |

## `smoke-login-badpw`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | bad_credentials | pass | passed | 6778 ms | 0 | Your password is invalid! | `/private/tmp/claude-501/-Users-fares-Downloads-jev-browser-test/a7544d31-fa57-4bc4-91e7-6a3188f7ba64/scratchpad/suite-9c20838/smoke-login-badpw/01/result.json` |
| 2 | bad_credentials | pass | passed | 6736 ms | 0 | Your password is invalid! | `/private/tmp/claude-501/-Users-fares-Downloads-jev-browser-test/a7544d31-fa57-4bc4-91e7-6a3188f7ba64/scratchpad/suite-9c20838/smoke-login-badpw/02/result.json` |
| 3 | bad_credentials | pass | passed | 7454 ms | 0 | Your password is invalid! | `/private/tmp/claude-501/-Users-fares-Downloads-jev-browser-test/a7544d31-fa57-4bc4-91e7-6a3188f7ba64/scratchpad/suite-9c20838/smoke-login-badpw/03/result.json` |
| 4 | bad_credentials | pass | passed | 6365 ms | 0 | Your password is invalid! | `/private/tmp/claude-501/-Users-fares-Downloads-jev-browser-test/a7544d31-fa57-4bc4-91e7-6a3188f7ba64/scratchpad/suite-9c20838/smoke-login-badpw/04/result.json` |
| 5 | bad_credentials | pass | passed | 6575 ms | 0 | Your password is invalid! | `/private/tmp/claude-501/-Users-fares-Downloads-jev-browser-test/a7544d31-fa57-4bc4-91e7-6a3188f7ba64/scratchpad/suite-9c20838/smoke-login-badpw/05/result.json` |
