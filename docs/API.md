# API Reference

Auto-generated interactive docs are always the source of truth: run the backend and open `/docs` (Swagger UI) or `/redoc`. This file is a quick human-readable index, updated as endpoints are added per phase.

## Auth (Phase 1)

| Method | Path | Body | Notes |
|---|---|---|---|
| POST | `/auth/signup` | `{email, password}` | Creates a user + email auth link, returns JWT pair |
| POST | `/auth/login` | `{email, password}` | Returns JWT pair |
| POST | `/auth/refresh` | `{refresh_token}` | Returns a new JWT pair |

All protected endpoints require `Authorization: Bearer <access_token>`.

## Auth — Google / Kakao (Phase 2)

| Method | Path | Body | Notes |
|---|---|---|---|
| POST | `/auth/google` | `{id_token}` | Verifies against Google's public certs (audience = `GOOGLE_OAUTH_CLIENT_ID`); creates or links a user |
| POST | `/auth/kakao` | `{access_token}` | Verifies via `kapi.kakao.com/v2/user/me`; creates or links a user |
| POST | `/auth/apple` | `{identity_token}` | Verifies the JWT locally against Apple's public JWKS (`https://appleid.apple.com/auth/keys`), audience = `APPLE_BUNDLE_ID`; creates or links a user. Required by Apple App Store Review Guideline 4.8 (any app offering third-party login like Google must also offer Sign in with Apple), not just a nice-to-have |

All three (plus email) return the same `TokenResponse` shape. If the provider's email matches an existing account, the new provider is linked to that account instead of creating a duplicate user.

## Profiles / Discovery / Matching (Phase 3, extended Phase 17/18)

| Method | Path | Body | Notes |
|---|---|---|---|
| GET | `/profiles/me` | — | Current user's profile + photos + credits + incognito/travel state |
| PUT | `/profiles/me` | `ProfileUpdate` | Upserts profile; `is_profile_complete` flips true once ≥1 photo exists |
| POST | `/profiles/me/photos/confirm` | `{gcs_object_path, position}` | Records a photo row after a direct-to-R2 upload |
| DELETE | `/profiles/me/photos/{photo_id}` | — | |
| POST | `/profiles/me/incognito` | `{is_incognito}` | Toggles discovery visibility; doesn't affect existing matches/likes |
| POST | `/profiles/me/travel` | `{lat, lng, duration_hours}` | Repositions the user for discovery (both as viewer and candidate) until expiry |
| DELETE | `/profiles/me/travel` | — | Clears travel mode, reverting to `location_lat`/`location_lng` |
| POST | `/uploads/presign` | `{content_type, position}` | Returns an R2 (S3-compatible) signed PUT URL; mobile uploads directly, then calls the confirm endpoint above |
| GET | `/discovery/candidates` | — | Filtered by mutual gender preference, age range, distance, excludes already-swiped/blocked/incognito; superliked-me and boosted-user ranked first |
| POST | `/interactions/like` \| `/pass` \| `/superlike` | `{to_user_id}` | Returns `{matched, match_id}`; mutual like/superlike creates a `Match` via the `sp_RecordSwipe` stored procedure. Superlike: 1 free/day, then consumes `superlike_credits`, else `402` |
| GET | `/matches` | — | Active matches for the current user; each includes `is_message_restricted`, `can_send_first_message`, `first_message_deadline` (Bumble rule, see below) |

Every `PhotoOut` (in `ProfileOut.photos` and `CandidateOut.photos`) includes a computed `url` — the public `<R2_PUBLIC_URL>/<object_path>` URL — alongside the raw `gcs_object_path`, so the client never has to construct it.

## Chat / Video call / Push / Safety (Phase 4, extended Phase 14/15)

| Method / Protocol | Path | Body | Notes |
|---|---|---|---|
| WS | `/ws/chat?token=<access_token>` | see frame types below | One connection per user (v1); delivers live to the peer if connected, else falls back to FCM push |
| GET | `/matches/{match_id}/messages` | — | REST history fallback, paginate with `?before=<ISO timestamp>&limit=` |
| GET | `/calls/ice-servers` | — | Returns STUN (always) + TURN (only if `TURN_URL` configured) — never hardcode ICE servers client-side |
| POST | `/devices/register` | `{fcm_token, platform}` | Upserts by token, so re-registering just updates platform |
| POST | `/safety/block` | `{user_id}` | Blocks are mutual — a blocked user can't swipe or message either direction |
| POST | `/safety/report` | `{user_id, reason, detail?}` | Logged to `Reports` table with `status="open"` for manual review |

**WS chat frames** (client → server): `{"type":"message","match_id","content"}`, `{"type":"read","match_id"}`, `{"type":"call_offer","match_id","sdp"}`, `{"type":"call_answer","call_id","sdp"}`, `{"type":"call_ice_candidate","call_id","candidate"}`, `{"type":"call_end","call_id","reason"?}`.

**WS chat frames** (server → client): `{"type":"message",...}`, `{"type":"read","match_id"}`, `{"type":"error","code":"first_message_restricted","match_id"}` (Bumble rule violation), `{"type":"call_offer",...}`, `{"type":"call_answer",...}`, `{"type":"call_ice_candidate",...}`, `{"type":"call_end","call_id","reason"}` (`reason` is `"hangup"` or `"peer_offline"`).

Video calls are gated only by "match still active" — independent of the Bumble first-message restriction below. Push notifications are no-op until `FIREBASE_CREDENTIALS_PATH` points at a real Firebase service account (external prerequisite, not yet created).

### Bumble first-message rule (Phase 14)

At match creation, if the pair is exactly `{male, female}`, the match is restricted to the female user with a 24h `first_message_deadline`; any other gender combination is unrestricted immediately. If the restricted user doesn't message within the deadline, the match lazily flips to inactive the next time either side touches it (no scheduler). A message sent by the wrong side gets the `first_message_restricted` error frame above instead of being delivered.

## Employment/school verification (Phase 16)

| Method | Path | Body | Notes |
|---|---|---|---|
| POST | `/verification/start` | `{kind: "work"\|"school", email}` | Sends a 6-digit code by email; rejects common personal-email domains (gmail/naver/kakao/daum/etc.); 503 if SMTP isn't configured |
| POST | `/verification/confirm` | `{kind, code}` | 15-min expiry, 5-attempt lockout; sets `Profiles.VerifiedBadge` on success |

## Payments — Stripe web checkout, not in-app purchase (Phase 17)

No native IAP anywhere — store commission was explicitly rejected. All of this is consumed from `web/shop.html`, not the mobile app directly.

| Method | Path | Body | Notes |
|---|---|---|---|
| GET | `/payments/products` | — | Product catalog (`superlike_pack_5`, `superlike_pack_20`, `boost_1` — see `PRODUCTS` in `app/services/payment_service.py`) |
| POST | `/payments/create-checkout-session` | `{product_id}` | Returns a Stripe Checkout `checkout_url`; inline `price_data`, no pre-created Stripe product/price IDs needed |
| POST | `/payments/webhook` | raw Stripe event + `Stripe-Signature` header | Grants credits on `checkout.session.completed`; idempotent via `try_insert` keyed on the Stripe event id, so redelivery never double-grants |
| GET | `/payments/balance` | — | `{superlike_credits, boost_credits, boost_active_until}` |
| POST | `/payments/activate-boost` | — | Consumes 1 boost credit, opens a 30-minute active window; `402` if no credits |

## Account (Phase 8)

| Method | Path | Notes |
|---|---|---|
| DELETE | `/account/me` | Explicitly deletes swipes/matches/blocks/reports first (MSSQL disallows multiple CASCADE paths to `Users`), then deletes the user — everything else (profile, photos, auth links, push tokens, verifications, payment transactions) cascades automatically |

## Health

| Method | Path | Notes |
|---|---|---|
| GET | `/health` | Liveness check, no auth |
