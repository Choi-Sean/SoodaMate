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
    kakao_rest_api_key: str = ""
    # Sign in with Apple's identityToken audience is the app's bundle id, not
    # a separate OAuth client — defaults to the real bundle id already used
    # in mobile/app.config.js, so no extra account/config is needed beyond
    # the paid Apple Developer account App Store submission already requires.
    apple_bundle_id: str = "com.soodalist.soodamate"

    gcs_bucket_name: str = "sooda-mate-photos"
    google_application_credentials: str = ""

    firebase_credentials_path: str = ""

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

    # Phase 17 — Stripe (web checkout, not in-app purchase — user explicitly
    # rejected IAP's store commission; boost/superlike credits are bought via
    # the marketing website and synced back to the account by webhook).
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    web_base_url: str = "http://localhost:8080"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def stun_url_list(self) -> list[str]:
        return [u.strip() for u in self.stun_urls.split(",") if u.strip()]


settings = Settings()
