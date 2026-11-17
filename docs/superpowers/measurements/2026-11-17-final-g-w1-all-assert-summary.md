NOT GREEN: 19 of 22 specs green in 144 s (1 worker, 30 Jev requests)
  menu-random                    BUG          entry_missing  -> runs/suite/g-w1-all-assert/menu-random/01
  notify-random                  BUG          action_unsuccessful  "Action unsuccesful, please try again"  (the same without the saved path)  -> runs/suite/g-w1-all-assert/notify-random/01-without-replay
  shop-checkout-problem-account  BUG          form_error  "Error: Last Name is required"  -> runs/suite/g-w1-all-assert/shop-checkout-problem-account/01
Changed since the last rerun (2026-11-17 18:58): notify-random pass -> bug; toolshop-search-cart undetermined -> pass
Replay: 17 walked their saved path, 1 handed over to Jev on the way, 3 had no path to walk (first run, edited spec, or a spec that does not end in a pass), 1 red after saved steps and run again without.
  handed over: toolshop-search-cart at step 1: the page's fields and buttons differ from the recording (gone: checkbox "Show only eco-friendly pro… (the path resumed)
Read result.json in those folders, then the trace if it does not settle it. The 19 green specs need no reading.
Report: runs/suite/g-w1-all-assert/results.md
