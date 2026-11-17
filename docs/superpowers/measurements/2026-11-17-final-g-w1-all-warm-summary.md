NOT GREEN: 19 of 22 specs green in 157 s (1 worker, 50 Jev requests)
  menu-random                    BUG          entry_missing  -> runs/suite/g-w1-all-warm/menu-random/01
  shop-checkout-problem-account  BUG          form_error  "Error: Last Name is required"  -> runs/suite/g-w1-all-warm/shop-checkout-problem-account/01
  toolshop-search-cart           UNDETERMINED undetermined (blocked, suggested: bug)  (the same without the saved path)  -> runs/suite/g-w1-all-warm/toolshop-search-cart/01-without-replay
Same verdicts as the last rerun (2026-11-17 18:51).
Replay: 15 walked their saved path, 2 handed over to Jev on the way, 4 had no path to walk (first run, edited spec, or a spec that does not end in a pass), 1 red after saved steps and run again without.
  handed over: hrm-admin-add-user at step 1: the page's fields and buttons differ from the recording (new: button "Apply Leave", button "Assign … (the path resumed)
  handed over: hrm-pim-add-employee-list at step 1: the page's fields and buttons differ from the recording (new: button "Apply Leave", button "Assign … (the path resumed)
Read result.json in those folders, then the trace if it does not settle it. The 19 green specs need no reading.
Report: runs/suite/g-w1-all-warm/results.md
