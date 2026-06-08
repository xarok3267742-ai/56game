# Privacy Policy Hosting Checklist

Use this checklist before entering the privacy policy URL in Play Console.

## Files

- Source Markdown: `play_store/privacy_policy_ru.md`
- Ready-to-host HTML: `play_store/privacy_policy_ru.html`

## Required Manual Inputs

- Working support email or support website URL.
- Public HTTPS hosting location.

## Hosting Requirements

- URL must be public and accessible without login.
- URL must use HTTPS.
- URL must not include credentials, query parameters or fragments.
- URL host must be a real public domain, not a placeholder/reserved host, and DNS must resolve only to public global IP addresses.
- Page must show the app name: `Линия 56`.
- Page must include developer information and a privacy point of contact or a mechanism to submit inquiries.
- Page contact mechanism must not point to an empty placeholder.
- Page content must match the app behavior: no data collection, no sharing, no ads, no analytics, no payments, Android backup disabled.
- Hosted page text must match the current normalized text of `play_store/privacy_policy_ru.html`; do not edit the hosted copy separately.
- Hosted page must not inject scripts, trackers, iframes, cookie logic or external widgets into the policy body.

## Verification Before Play Upload

1. Open the final HTTPS URL in a clean browser profile or incognito window.
2. Confirm the page loads without authentication, cookies banner blockers, paywall or redirect loop.
3. Confirm the Google Play store listing has a working support email or support website, because the hosted policy uses that listing contact as the privacy inquiry mechanism.
4. Confirm the page text still says Android backup is disabled.
5. Run `./tools/check_privacy_policy_url.py --url <https-url>` and require `privacy_policy_url_ok`; the helper also checks valid UTF-8, HTML content, public HTTPS, no credentials/query/fragments, no placeholder/reserved host, public-global DNS resolution, non-PDF final URL, exact normalized-text match with `play_store/privacy_policy_ru.html` and no script/tracker/widget markers.
6. Add that URL to Play Console App content > Privacy Policy.

Local source preflight:

```bash
./tools/check_privacy_policy_url.py --local
```

## Current Status

Policy source text is ready to host and no longer contains a contact-replacement placeholder. Public HTTPS hosting and populated Play Console support/contact fields remain manual release blockers because they are external to the local codebase.
