NOT GREEN: 19 of 22 specs green in 63 s (8 workers, 30 Jev requests)
  menu-random                    BUG          entry_missing  -> runs/suite/f-w8-all-assert/menu-random/01
  notify-random                  BUG          action_unsuccessful  "Action unsuccesful, please try again"  (the same without the saved path)  -> runs/suite/f-w8-all-assert/notify-random/01-without-replay
  shop-checkout-problem-account  BUG          form_error  "Error: Last Name is required"  -> runs/suite/f-w8-all-assert/shop-checkout-problem-account/01
Changed since the last rerun (2026-11-17 18:25): notify-random pass -> bug
Replay: 18 walked their saved path, 0 handed over to Jev on the way, 3 had no path to walk (first run, edited spec, or a spec that does not end in a pass), 1 red after saved steps and run again without.
Read result.json in those folders, then the trace if it does not settle it. The 19 green specs need no reading.
Report: runs/suite/f-w8-all-assert/results.md
