# web — 수다 데이트 marketing site

Plain HTML/CSS/JS, no build step — same convention as the sibling `centiplay-web` project.

## Local preview

Open `index.html` directly in a browser, or serve the folder with any static
file server (needed for `/`-rooted asset paths to resolve correctly):

```bash
npx serve .
```

## Structure

- `index.html` — hero, feature highlights, screenshot placeholders, download CTA
- `privacy-policy.html`, `terms.html` — real content, not placeholders; required for app store submission (Phase 11)
- `assets/` — logo/favicon (brand color `#FF4B6E`, matches `mobile/`)
- `vercel.json` — deploy config, same pattern as `centiplay-web`

## To update before real launch

- Swap the `#download` store-badge links for the real App Store / Google Play listing URLs once submitted
- Replace the phone-frame color placeholders in `#screens` with real app screenshots
- Replace the placeholder contact emails in `privacy-policy.html` / `terms.html` with real addresses
- Point `mobile/.env`'s `EXPO_PUBLIC_MARKETING_SITE_URL` at this site's real deployed domain
