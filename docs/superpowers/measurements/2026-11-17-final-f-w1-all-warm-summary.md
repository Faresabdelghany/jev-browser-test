NOT GREEN: 18 of 22 specs green in 170 s (1 worker, 58 Jev requests)
  hrm-add-employee               BUG          employee_id_taken  "Employee Id already exists"  -> runs/suite/f-w1-all-warm/hrm-add-employee/01
  menu-random                    BUG          entry_missing  -> runs/suite/f-w1-all-warm/menu-random/01
  shop-checkout-error-account    UNDETERMINED undetermined (blocked, suggested: bug)  -> runs/suite/f-w1-all-warm/shop-checkout-error-account/01
  shop-checkout-problem-account  UNDETERMINED undetermined (blocked, suggested: bug)  -> runs/suite/f-w1-all-warm/shop-checkout-problem-account/01
Changed since the last rerun (2026-11-17 18:17): hrm-add-employee pass -> bug; shop-checkout-error-account expected -> undetermined; shop-checkout-problem-account bug -> undetermined
Replay: 15 walked their saved path, 3 handed over to Jev on the way, 3 had no path to walk (first run, edited spec, or a spec that does not end in a pass), 1 red after saved steps and run again without.
  handed over: hrm-add-employee at step 1: the page's fields and buttons differ from the recording (new: button "Apply Leave", button "Assign …
  handed over: hrm-pim-add-employee-list at step 1: the page's fields and buttons differ from the recording (new: button "Apply Leave", button "Assign …
  handed over: toolshop-search-cart at step 1: the page's fields and buttons differ from the recording (gone: checkbox "Show only eco-friendly pro…
Read result.json in those folders, then the trace if it does not settle it. The 18 green specs need no reading.
Report: runs/suite/f-w1-all-warm/results.md
