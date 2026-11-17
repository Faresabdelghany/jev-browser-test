# `hrm-leave-assign` with a date placeholder: five live runs (2026-11-17, `jev-1.14.0`, 1 at a time)

The spec typed a literal date (`2026-16-12`); a leave on a day that has passed is listed as Taken, not Scheduled. Each
run below is `python scripts/run_test.py specs/examples/hrm-leave-assign.json`, the pinned ones with `RUN_DATE` in the
environment. Traces under `runs/hrm-leave-assign/<run>/` on the machine that ran them.

| run | `leave_date` in the spec | `RUN_DATE` | date typed | ended in | requests | seconds |
|---|---|---|---|---|---:|---:|
| 20261117-134107 | `${DATE+30d+workday:yyyy-dd-mm}` | (today, 2026-11-17) | 2026-17-12 | `leave_scheduled`, pass | 25 | 31.5 |
| 20261117-134139 | `${DATE+30d+workday:yyyy-dd-mm}` | 2026-12-17 | 2027-18-01 | undetermined, `low_confidence` | 28 | 50.5 |
| 20261117-134427 | `${DATE+2d+workday:yyyy-dd-mm}` | (today) | 2026-19-11 | `leave_scheduled`, pass | 26 | 52.5 |
| 20261117-134520 | `${DATE+2d+workday:yyyy-dd-mm}` | 2026-12-17 | 2026-21-12 | `leave_scheduled`, pass | 26 | 39.2 |
| 20261117-134600 | `${DATE+2d+workday:yyyy-dd-mm}` | (today) | 2026-19-11 | `leave_scheduled`, pass | 25 | 49.7 |

130 Jev requests, 715k input tokens.

**The second run is the finding.** Thirty days ahead of 17 December is Saturday 16 January 2027, moved on to Monday the
18th. The assignment was saved ('Successfully Saved' announced before step 16), and the Leave List, filtered by
Scheduled and the employee, announced 'No Records Found': its From Date and To Date read `2026-01-01` and `2026-31-12`,
the current leave period, and the flow does not touch them. The run ended `low_confidence` (three undecided looks at
Search), not `no_records`, because `filter_scheduled` read 0.60 to 0.68, under the outcome's `requires` threshold. So
the offset has to keep the date inside the current year, and the shortest one that is safely in the future does that
on the most days: two days ahead (a margin for a runner whose clock is a day behind the demo's), on to a working day.

**What is left.** Counted over 2026 to 2035 with the demo's holidays: the date falls in the next year on the last two
days of December in most years, three in 2033, four in 2028 and 2034 (when the year ends on a weekend). On those days
the spec ends without the record, as the second run did.

**The demo's calendar**, read through its own API as Admin on 2026-11-17 (`/api/v2/leave/holidays`, `/api/v2/leave/workweek`):
work week Monday to Friday; sixteen holidays, every one recurring on its fixed day: 01-01, 03-16, 04-20, 05-18, 06-21,
06-22, 06-24, 07-01, 07-04, 07-09, 07-13, 11-11, 11-12, 12-25, 12-26, 12-28. They are the spec's `calendar.holidays`.
It is a public demo: a visitor can add one, and a run that lands on it ends `save_failed` ('No Working Days Selected').
