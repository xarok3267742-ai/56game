# Play Console App Content Answers - RU

Use this file as the field-by-field Play Console handoff for App content and policy declarations. Final submission still depends on the publisher account, real privacy-policy URL and account-specific testing requirements.

## App Access

- Restricted access: No.
- Login required: No.
- Paid access required: No.
- Special hardware, invitation, membership or external account required: No.
- Notes for reviewer: The app is fully usable offline after launch. No account, password, payment, invitation, network connection or special setup is required.

## Ads

- Contains ads: No.
- Ad SDKs: None.
- Ad ID usage: No.

## Privacy Policy

- Privacy policy required: Yes.
- Enter URL only after `play_store/privacy_policy_ru.html` is hosted at a public HTTPS URL and the Play Console support/contact fields used by the policy inquiry mechanism are filled with a real support contact.
- In-app privacy access: available through the About/privacy screen.
- Policy posture: no user data collection, no sharing, no ads, no analytics, no crash reporting SDK, no accounts, no payments, Android backup disabled.

## Data Safety

- Does the app collect or share any required user data types: No.
- User data collected: none.
- User data shared: none.
- Data processed ephemerally: none.
- Data encrypted in transit: No user data is transmitted by the app.
- Users can request data deletion: Not applicable; the app has no accounts and does not collect user data.
- Local-only data: onboarding flag, completed level ids, last level id and settings for haptics, high contrast and reduced motion.
- Local deletion path: uninstall the app or clear app storage in Android settings.
- Third-party SDK data: none beyond AndroidX/Compose runtime libraries; no analytics, advertising, crash reporting or network SDKs are included.

## Content Rating

- Rating category: Games.
- Game type: Puzzle / logic / numeric puzzle.
- Violence: No.
- Fear, shock or horror: No.
- Sexual content or nudity: No.
- Crude humor: No.
- Profanity or offensive language: No.
- Drugs, alcohol or tobacco: No.
- Gambling, simulated gambling or betting: No.
- Real-money purchases or paid random items: No.
- User-generated content: No.
- User-to-user communication: No.
- Location sharing: No.
- Digital goods purchases: No.
- Online gameplay or online interaction: No.
- Notes: The app is a quiet offline numeric puzzle where the only interaction is selecting neighboring numbered cells to reach a target sum.

## Target Audience And Content

Recommended answer if the publisher does not intentionally market to children:

- Target age groups: 13-15, 16-17, 18 and over.
- Do not select: 5 and under, 6-8, 9-12.
- Designed for children: No.
- Families program: Do not enroll unless the publisher intentionally prepares a child-directed release path.
- Store listing posture: neutral general-audience puzzle copy, no child-directed claims, no characters/mascots, no school/kids wording, no ads and no purchases.

If the publisher chooses to target children under 13, this handoff is no longer sufficient: review Families policy, child safety, child-appropriate UX and any extra Play Console checks before submission.

## Financial Features

- Financial products or services: No.
- Payments, trading, lending, insurance, credit, banking, tax or money-transfer features: No.
- In-app purchases: No.

## Health Features

- Health or medical features: No.
- Health data collection: No.
- Medical advice, diagnosis or treatment: No.

## Government Features

- Government affiliation or government services: No.
- Government documents, benefits, voting or official services: No.

## AI-Generated Content

- In-app generative AI features: No.
- User-generated AI content: No.
- AI content reporting: Not applicable.
- Store creative note: `play_store/feature_graphic.png` uses a static generated background source documented in the asset manifest; this is not an in-app AI feature and does not generate user-facing content at runtime.

## App Category And Tags

- App or game: Game.
- Category: Puzzle.
- Suggested tags: puzzle, logic, numbers, offline, brain training.
- Avoid tags or claims: casino, gambling, betting, money, education for children, school, kids, multiplayer, online.

## Testing Tracks

- First upload target: Internal testing.
- Then: Closed testing if required by the publisher account type.
- Personal account created after 13 November 2023: plan for at least 12 opted-in testers for 14 continuous days before production availability.
- Production access: apply for and receive Play Console production access if required after the closed-testing criteria are met.
- Production rollout: only after Play Console policy forms, generated artifact review, privacy URL, testing track requirements and production-access status are complete. Local TalkBack exploratory QA is covered in `docs/accessibility_notes.md`.
