# Privacy Contact Handoff - RU

Этот файл помогает владельцу безопасно закрыть Play Console privacy URL and support/contact gate. Он не доказывает заполнение Play Console локально и не должен содержать реальный support email, support website URL, Play account tokens, screenshots with account data, passwords, keystore contents or private keys; do not record the actual support email or URL.

Источник: Google Play Console Help `User Data` (`https://support.google.com/googleplay/android-developer/answer/10144311?hl=en`). По этой справке all apps must post a privacy policy link in the designated field within Play Console, and the privacy policy must include developer information and a privacy point of contact or a mechanism to submit inquiries. Privacy policy must be available on an active, publicly accessible and non-geofenced URL, no PDFs, and non-editable.

## Fixed Local Privacy Facts

- App name: `Линия 56`.
- Package: `com.qgrid.mobile`.
- Hosted privacy policy URL: `https://xarok3267742-ai.github.io/56game/privacy_policy_ru.html`.
- Local privacy HTML source: `play_store/privacy_policy_ru.html`.
- Local privacy Markdown source: `play_store/privacy_policy_ru.md`.
- Current hosted URL check command: `./tools/check_privacy_policy_url.py --url https://xarok3267742-ai.github.io/56game/privacy_policy_ru.html`.
- Current hosted URL check result expected before Play Console entry: `privacy_policy_url_ok`.
- Privacy/data posture: no user data collected, no user data shared, no ads, no analytics, no accounts, no payments, no `INTERNET`, no `ACCESS_NETWORK_STATE`, Android backup disabled.

## Owner Action

1. Choose a real support contact outside this repository.
2. Enter the support contact in the Google Play listing support/contact fields.
3. Use either a support email or support website URL; do not record the actual value in this repository.
4. Enter the hosted privacy policy URL in the Play Console privacy policy field.
5. Run `./tools/check_privacy_policy_url.py --url https://xarok3267742-ai.github.io/56game/privacy_policy_ru.html` again and require `privacy_policy_url_ok`.
6. Record only safe evidence in `play_store/play_console_post_upload_evidence_ru.md`.

## Safe Evidence Phrases Accepted By Local Gate

Use one of these support/contact lines after the real Play Console field is populated:

```text
Play Console support/contact field populated: Play Console support/contact field populated with a real support contact email for privacy inquiries.
```

```text
Play Console support/contact field populated: Play Console support/contact field populated with a real support contact support website URL for privacy inquiries.
```

Use this mechanism line:

```text
Support/contact mechanism matches `play_store/privacy_policy_ru.html`: privacy policy inquiry mechanism uses the Google Play listing support contact.
```

Keep these already-recorded URL lines:

```text
Public privacy policy URL: https://xarok3267742-ai.github.io/56game/privacy_policy_ru.html.
Privacy policy URL check command returned `privacy_policy_url_ok`: privacy_policy_url_ok.
Privacy policy URL is HTTPS: yes.
Privacy policy URL is accessible without login: yes.
Privacy policy URL is not PDF: yes.
```

## Stop Conditions

Do not upload or promote the release if:

- the support/contact field is empty or uses a disposable/unmonitored contact;
- the recorded evidence contains the actual support email address or support website URL;
- the privacy policy URL is not entered in the designated Play Console field;
- `./tools/check_privacy_policy_url.py --url https://xarok3267742-ai.github.io/56game/privacy_policy_ru.html` does not return `privacy_policy_url_ok`;
- the hosted privacy page content no longer matches `play_store/privacy_policy_ru.html`;
- the hosted privacy page is a PDF, editable by readers, behind login, geofenced, or has credentials/query/fragments.
