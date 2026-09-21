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
python -m qa.run security2 # adversarial security suite (suite_security + suite_security2): forged tokens, IDOR, races / double-spend,
                           # rate limits, upload + path validation, blind-chat anonymity, webhook forgery, location trilateration,
                           # ad + website configuration checks
QA_ONLY=ADM-004 python -m qa.run core   # re-run selected case ids (comma separated prefixes)
```

Results land in `qa/out/results_*.json`; `python backend/qa/build_report.py`
(needs `openpyxl`, use the global python) writes the Excel report to `docs/qa/`.

Every case in the security suites asserts the SECURE behaviour, so a FAIL is a vulnerability in the code under test; run it from a
`git worktree` of an older commit to see what a fix changed. `qa/pool_probe.py <backend_dir> <port>` starts the API with a real
connection pool and checks that idle chat WebSockets don't exhaust it (creates qa-pool-* users; clean up with leak_audit).

The general suites run with the security switches relaxed (`RELAXED_FLAGS` in harness.py: no rate limits, no face-verification gate,
email sign-up allowed, placeholder upload paths accepted); suite_security turns each one back on for exactly the cases that test it.

If a run is killed before its cleanup: `python qa/leak_audit.py <UTC start time> [--delete]`.

`ui_seed.py` + `run_backend.cmd` + `serve_web.py` prepare the browser walk-through
(RN-Web app on 127.0.0.1:8081, admin pages on 127.0.0.1:5555, QA API on :8002 with a
bypass SMS code for a few QA-only phone numbers).

Rules of the road: never point the QA suite at real users' data, never start an admin
promotion against a product that already has a real one (it supersedes it and pushes to
everyone), and never use the developer's real bypass numbers.
