import os

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "local"
    secret_key: str = "dev-secret-key-not-for-production"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 30

    database_url: str = (
        "mssql+aioodbc://sa:ChangeMe123!@localhost:1433/sooda_mate"
        "?driver=ODBC+Driver+17+for+SQL+Server&Encrypt=yes&TrustServerCertificate=yes"
        "&MARS_Connection=yes&Connection+Timeout=15"
    )

    google_oauth_client_id: str = ""
    # Sign in with Apple's identityToken audience is the app's bundle id, not
    # a separate OAuth client — defaults to the real bundle id already used
    # in mobile/app.config.js, so no extra account/config is needed beyond
    # the paid Apple Developer account App Store submission already requires.
    apple_bundle_id: str = "com.soodalist.soodamate"

    # Cloudflare R2 (S3-compatible) for profile photos — chosen over GCS for
    # its zero egress fee, which matters a lot for an app that re-serves the
    # same photos on every swipe/discover/match load. Column/field names
    # (gcs_object_path, PhotoConfirmRequest.gcs_object_path, etc.) keep
    # their old "gcs_" prefix on purpose — it's just "the object's storage
    # path" now, provider-agnostic, and renaming a real DB column for pure
    # naming purity isn't worth the migration risk.
    # Full S3-compatible endpoint URL as shown on the R2 API token creation
    # screen (https://<hash>.r2.cloudflarestorage.com) — stored verbatim
    # rather than reconstructed from an account id, since the hash Cloudflare
    # puts in a token's endpoint doesn't always match the account's own
    # dashboard "Account ID" value.
    r2_endpoint_url: str = ""
    r2_access_key_id: str = ""
    r2_secret_access_key: str = ""
    r2_bucket_name: str = "sooda-mate-photos"
    # The bucket's public read base URL — either the free
    # https://pub-<hash>.r2.dev dev subdomain (enabled per-bucket under
    # Settings > Public Access) or a custom domain mapped to the bucket.
    # Photo URLs are built as f"{r2_public_url}/{object_path}".
    r2_public_url: str = ""
    # OPTIONAL second bucket with public access OFF for face-verification selfies
    # and ID-card photos (see storage_service.bucket_for). Empty = keep them in the
    # main public-read bucket as before. Create it in Cloudflare R2 (no public
    # access, no r2.dev URL), make sure the API token can read/write it, set this,
    # then move existing files with scripts/migrate_verifications_to_private_bucket.py.
    r2_private_bucket_name: str = ""

    firebase_credentials_path: str = ""

    # Google Cloud Translation v2 (https://translation.googleapis.com) — a
    # plain API key, not a service account. Powers real-time chat
    # translation (services/translation_service.py); unset means
    # translation is silently a no-op (chat still sends/receives fine,
    # just without a translated_content field), same convention as
    # push_service's unconfigured-Firebase no-op above.
    google_translate_api_key: str = ""

    cors_origins: str = "http://localhost:19006,http://localhost:8081"

    # Phase 15 — video call signaling. Public STUN needs no account; TURN is
    # an external prerequisite (Twilio/coturn/etc.), empty until provisioned.
    stun_urls: str = "stun:stun.l.google.com:19302"
    turn_url: str = ""
    turn_username: str = ""
    turn_credential: str = ""

    # Phase 16 — employment/school verification email
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from_address: str = "no-reply@soodamate.example.com"

    # Phone verification (Twilio Verify) — required at signup now that Blind
    # Chat is the app's primary flow. Empty until the user provisions a
    # Twilio account; TwilioVerifySmsVerifier.start() 503s honestly until then
    # (see sms/twilio_verify.py), same "don't pretend it works" convention as
    # smtp_host above.
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_verify_service_sid: str = ""

    # Dev-only bypass for specific whitelisted E.164 numbers, so repeated
    # manual testing doesn't burn real (billed) Twilio Verify sends. Both
    # must be set for it to do anything — empty dev_phone_bypass_code (the
    # default everywhere except a developer's own env) means phone auth
    # behaves identically for every number, listed or not. See auth_service's
    # start_phone_auth/login_or_signup_with_phone and docs/ENV_VARS.md.
    dev_phone_bypass_numbers: str = ""
    dev_phone_bypass_code: str = ""

    # Rejects internet/VoIP/virtual numbers (Google Voice, TextNow, 070, ...)
    # at signup via Twilio Lookup Line Type Intelligence (~$0.008 per new
    # number — see services/phone_screening.py). Escape hatch if it ever
    # misclassifies real carriers: set BLOCK_VOIP_PHONE_NUMBERS=false. The
    # free Korean prefix check (+82 must be a 01x mobile) stays on regardless.
    block_voip_phone_numbers: bool = True

    # Claude API (console.anthropic.com > API Keys) — powers LLM-assisted AI
    # Match ranking (llm_match_service.py). Empty means find_ai_match falls
    # back to the deterministic tag-overlap score only, same "degrade, don't
    # break" convention as every other optional integration above.
    anthropic_api_key: str = ""

    # Phase 17 — Stripe (web checkout, not in-app purchase — user explicitly
    # rejected IAP's store commission; boost/superlike credits are bought via
    # the marketing website and synced back to the account by webhook).
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    web_base_url: str = "http://localhost:8080"

    # --- Security hardening switches (all default to the safe production value;
    # the test suites relax the ones that get in the way of bulk test setup). ---

    # In-process sliding-window rate limits on auth/SMS/upload/chat/spam-prone
    # endpoints (app/core/rate_limit.py). Per-process, which is right for the
    # single Railway instance this runs on; move to Redis before scaling out.
    rate_limit_enabled: bool = True
    # How many reverse proxies sit in front of the API and append to
    # X-Forwarded-For (Railway's edge = 1). The client IP used for the per-IP
    # limits is the Nth entry from the RIGHT — entries further left are supplied
    # by the caller and can be forged.
    trusted_proxy_hops: int = 1
    # Hard cap on SMS Verify sends across the whole app per 10 minutes — the
    # backstop against SMS-pumping fraud no matter how many numbers/IPs an
    # attacker rotates through.
    sms_global_per_10min: int = 300

    # Blind Chat / AI Match require a completed selfie+ID face verification,
    # enforced here rather than only in the app's UI (a modified client or a
    # direct API call would otherwise skip it).
    require_verified_accounts: bool = True

    # Email sign-up and Google/Apple sign-in are not used by the app (phone is
    # the only sign-in it offers) but were still open to the world, which let
    # anyone create accounts that never passed phone verification or the VoIP
    # screen. /auth/login stays available for existing accounts (admin console).
    enable_legacy_auth: bool = False

    # Rewarded-ad bonus: when true the +1 daily Blind Chat match is only
    # granted by AdMob's signed server-side-verification callback (GET
    # /ads/ssv), never by the client saying "I watched it". Flip on after the
    # callback URL is set on the rewarded ad units in the AdMob console.
    ad_bonus_requires_ssv: bool = False
    # Comma-separated AdMob rewarded ad unit ids (ca-app-pub-XXXX/YYYY) that
    # are allowed to mint SSV callbacks — anyone with an AdMob account can get
    # Google to sign a callback for THEIR unit, so ours must be pinned.
    admob_rewarded_unit_ids: str = ""

    # Confirming an upload checks the file really exists, is a sane size and
    # really is an image/video (services/storage_service.check_uploaded_object).
    # Only the test suites turn this off, because they confirm placeholder paths
    # instead of uploading real files for every fixture user.
    verify_uploaded_objects: bool = True

    # Requests bigger than this are refused before parsing (413). Every real
    # request here is small — uploads go straight to R2 via presigned URLs.
    max_json_body_bytes: int = 262_144

    @property
    def is_production(self) -> bool:
        if self.app_env.strip().lower() in ("production", "prod"):
            return True
        return bool(os.getenv("RAILWAY_ENVIRONMENT_NAME") or os.getenv("RAILWAY_ENVIRONMENT"))

    @property
    def admob_rewarded_unit_id_list(self) -> list[str]:
        return [u.strip() for u in self.admob_rewarded_unit_ids.split(",") if u.strip()]

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def stun_url_list(self) -> list[str]:
        return [u.strip() for u in self.stun_urls.split(",") if u.strip()]

    @property
    def dev_phone_bypass_number_list(self) -> list[str]:
        return [n.strip() for n in self.dev_phone_bypass_numbers.split(",") if n.strip()]


settings = Settings()
