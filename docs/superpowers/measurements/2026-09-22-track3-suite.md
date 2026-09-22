# Suite track3-acceptance 2026-09-22T10:21:51+03:00

**ALL PASS** · 2 spec(s) × 5 repeat(s), 4 worker(s), 18.6 s wall-clock · commit `185a10f`

| spec | verdict | agreement | outcomes | median wall | Jev ms | requests | tokens in | confidence |
|---|---|---:|---|---:|---:|---:|---:|---:|
| `smoke-login` | **PASS** | 100% | logged_in 5/5 | 6432 ms | 1990 | 6 | 8932 | 0.96 |
| `smoke-login-badpw` | **PASS** | 100% | bad_credentials 5/5 | 6192 ms | 1972 | 6 | 9774 | 0.92 |

## `smoke-login`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | logged_in | pass | passed | 6377 ms | 0 | You logged into a secure area! | `runs/suite/track3-acceptance/smoke-login/01/result.json` |
| 2 | logged_in | pass | passed | 6432 ms | 0 | You logged into a secure area! | `runs/suite/track3-acceptance/smoke-login/02/result.json` |
| 3 | logged_in | pass | passed | 6500 ms | 0 | You logged into a secure area! | `runs/suite/track3-acceptance/smoke-login/03/result.json` |
| 4 | logged_in | pass | passed | 7234 ms | 0 | You logged into a secure area! | `runs/suite/track3-acceptance/smoke-login/04/result.json` |
| 5 | logged_in | pass | passed | 6050 ms | 0 | You logged into a secure area! | `runs/suite/track3-acceptance/smoke-login/05/result.json` |

## `smoke-login-badpw`

| # | outcome | verdict | status | wall | exit | evidence | result |
|---:|---|---|---|---:|---:|---|---|
| 1 | bad_credentials | pass | passed | 6295 ms | 0 | Your password is invalid! | `runs/suite/track3-acceptance/smoke-login-badpw/01/result.json` |
| 2 | bad_credentials | pass | passed | 5927 ms | 0 | Your password is invalid! | `runs/suite/track3-acceptance/smoke-login-badpw/02/result.json` |
| 3 | bad_credentials | pass | passed | 5740 ms | 0 | Your password is invalid! | `runs/suite/track3-acceptance/smoke-login-badpw/03/result.json` |
| 4 | bad_credentials | pass | passed | 6192 ms | 0 | Your password is invalid! | `runs/suite/track3-acceptance/smoke-login-badpw/04/result.json` |
| 5 | bad_credentials | pass | passed | 6195 ms | 0 | Your password is invalid! | `runs/suite/track3-acceptance/smoke-login-badpw/05/result.json` |
