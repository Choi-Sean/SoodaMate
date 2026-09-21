@echo off
rem Local API for UI QA: real code + real hosted DB, but SMS is bypassed for a few
rem QA-only phone numbers (fixed code 424242) so no real Twilio SMS is ever sent.
cd /d D:\Project\dating-app\backend
set DEV_PHONE_BYPASS_NUMBERS=+821099990001,+821099990002,+821099990003,+821099990004,+821099990005,+12135550111,+12135550112
set DEV_PHONE_BYPASS_CODE=424242
rem The UI seed scripts create e-mail accounts in bulk without phone/face verification, so relax the production
rem hardening switches for this QA-only API (they default to the safe values everywhere else).
set ENABLE_LEGACY_AUTH=true
set REQUIRE_VERIFIED_ACCOUNTS=false
set RATE_LIMIT_ENABLED=false
rem QA browser uses 127.0.0.1 origins so it never shares localStorage with the developer's own localhost session
set CORS_ORIGINS=http://localhost:19006,http://localhost:8081,http://localhost:5555,http://localhost:5500,http://127.0.0.1:8081,http://127.0.0.1:5555
.venv\Scripts\python.exe -m uvicorn app.main:app --port 8002
