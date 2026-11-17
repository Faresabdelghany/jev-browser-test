NOT GREEN: 20 of 22 specs green in 127 s (1 worker, 49 Jev requests)
  hrm-add-employee               UNDETERMINED undetermined (low_confidence, suggested: test_issue)  -> runs/suite/f-w1-all-1/hrm-add-employee/01
  shop-checkout-problem-account  BUG          form_error  "Error: Last Name is required"  -> runs/suite/f-w1-all-1/shop-checkout-problem-account/01
Changed since the last rerun (2026-11-17 18:20): hrm-add-employee bug -> undetermined; menu-random bug -> pass; shop-checkout-error-account undetermined -> expected; shop-checkout-problem-account undetermined -> bug
Replay: 17 walked their saved path, 1 handed over to Jev on the way, 3 had no path to walk (first run, edited spec, or a spec that does not end in a pass), 1 red after saved steps and run again without.
  handed over: hrm-add-employee at step 1: the page's fields and buttons differ from the recording (new: button "Apply Leave", button "Assign …
Read result.json in those folders, then the trace if it does not settle it. The 20 green specs need no reading.
Report: runs/suite/f-w1-all-1/results.md
