# SooDaMate QA suite

End-to-end cases that run the real app code (in-process ASGI) against the real
hosted database and the real R2 bucket. Everything a case creates is tracked and
deleted afterwards. SMS, push notifications and SMTP are stubbed so nothing ever
reaches a real person.

```bash
cd backend
python -m qa.run core      # auth, profile, real R2 uploads, face verification + admin approve/reject, safety, admin console
python -m qa.run flow      # discovery, matching, chat (WebSocket/images/translation), blind chat, AI match, payments, calls, security
python -m qa.run static    # i18n completeness (app, website, push, products), website integrity, website<->app claim audit
QA_ONLY=ADM-004 python -m qa.run core   # re-run selected case ids (comma separated prefixes)
```

Results land in `qa/out/results_*.json`; `python backend/qa/build_report.py`
(needs `openpyxl`, use the global python) writes the Excel report to `docs/qa/`.

If a run is killed before its cleanup: `python qa/leak_audit.py <UTC start time> [--delete]`.

`ui_seed.py` + `run_backend.cmd` + `serve_web.py` prepare the browser walk-through
(RN-Web app on 127.0.0.1:8081, admin pages on 127.0.0.1:5555, QA API on :8002 with a
bypass SMS code for a few QA-only phone numbers).

Rules of the road: never point the QA suite at real users' data, never start an admin
promotion against a product that already has a real one (it supersedes it and pushes to
everyone), and never use the developer's real bypass numbers.
