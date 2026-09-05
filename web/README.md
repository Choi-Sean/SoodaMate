# web — 수다 데이트 marketing site

Plain HTML/CSS/JS, no build step — same convention as the sibling `centiplay-web` project.

## Local preview

Open `index.html` directly in a browser, or serve the folder with any static
file server (needed for `/`-rooted asset paths to resolve correctly):

```bash
npx serve .
```

## Structure

- `index.html` — hero, feature highlights, Bumble-rule + safety sections, screenshot placeholders, download CTA (Hinge/Bumble/Tinder-inspired layout)
- `shop.html`, `shop-success.html` — Stripe Checkout for superlike/boost credits. No login of its own: reads the mobile app's JWT out of the URL (`?token=`, set when the app opens this page via `Linking.openURL`), and redirects back into the app via `sudadate://shop` on success
- `privacy-policy.html`, `terms.html` — real content, not placeholders; required for app store submission, fully translated (not just the page chrome)
- `i18n.js` — translation dictionary + language switcher for the whole site (ko/en/es/zh/ja), via `data-i18n`/`data-i18n-html` attributes
- `assets/` — logo/favicon (SooDaList family palette — warm cream/orange, navy text — matches `mobile/src/theme.ts`, not a generic pink dating-app look)
- `vercel.json` — deploy config, same pattern as `centiplay-web`

## To update before real launch

- Swap the `#download` store-badge links for the real App Store / Google Play listing URLs once submitted
- Replace the phone-frame color placeholders in `#screens` with real app screenshots
- Replace the placeholder contact emails in `privacy-policy.html` / `terms.html` with real addresses
- Point `mobile/.env`'s `EXPO_PUBLIC_MARKETING_SITE_URL` at this site's real deployed domain
- Set `WEB_BASE_URL` in `backend/.env` to this same deployed domain (used for Stripe Checkout success/cancel redirects)
