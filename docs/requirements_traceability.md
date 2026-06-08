# Requirements Traceability

Checked against the original RTF instruction and current local release candidate on 6 June 2026.

## Summary

Local release-candidate scope is covered and verifier-gated where it can be proven from the repository, build artifacts or Android tooling. Full Google Play publication is not complete locally because owner-controlled external actions remain: populated Play Console support/contact fields for privacy inquiries, public HTTPS privacy-policy URL, secure keystore backup, Play Console forms and required testing tracks. Those owner inputs are isolated in `play_store/owner_release_inputs.md`.

## Phase Coverage

| Phase | Requirement Area | Local Evidence | Status |
|---|---|---|---|
| Phase 1 | Product discovery: 10 ideas, evaluation, market/competitor notes, selected idea, risks, MVP/non-goals | `docs/product_decision.md` | Locally complete |
| Phase 2 | Product concept/spec: name, type, pitch, audience, core loop, screens, functions, game rules, progression, win/loss, replay value | `docs/product_spec.md` | Locally complete |
| Phase 3 | Stack decision and commands | `docs/tech_stack_decision.md`, `README.md`, `AGENTS.md` | Locally complete |
| Phase 4 | AGENTS handoff with architecture, commands, rules and done criteria | `AGENTS.md` | Locally complete |
| Phase 5 | Architecture/code: deterministic engine, persistence, navigation, no backend, no debug release leakage, no unnecessary permissions | `app/src/main`, `app/src/test`, `tools/verify_release.py`, `./tools/run_final_local_gate.py` | Locally complete |
| Phase 6 | UI/UX: design system, onboarding, home, gameplay, settings, result states, small/large screens, polish | `docs/ui_audit.md`, `play_store/screenshots/phone`, `app/src/main/java/com/qgrid/mobile/ui` | Locally complete |
| Phase 7 | Art direction and assets: prompts, manifest, icons, feature graphic, screenshots, consistency and rejected/source asset separation | `docs/art_direction.md`, `docs/asset_prompts.md`, `docs/asset_manifest.md`, `play_store/upload_manifest.md`, `tools/verify_release.py` | Locally complete |
| Phase 8 | Content audit: UI copy, game messages, level content, store copy, no placeholders; story bible not required because story/campaign is v1 non-goal | `docs/content_audit.md`, `app/src/main/res/values/strings.xml`, `docs/product_spec.md` | Locally complete |
| Phase 9 | Localization: Russian MVP strings, resource-file structure, no technical or English placeholder UI text | `app/src/main/res/values/strings.xml`, `tools/verify_release.py` | Locally complete |
| Phase 10 | Accessibility: contrast, tap targets, semantics/content descriptions, font-scale checks, compact About/privacy proof, TalkBack exploratory pass | `docs/accessibility_notes.md`, `docs/qa_artifacts`, `app/src/androidTest`, `tools/verify_release.py` | Locally complete |
| Phase 11 | Performance: app/build size, asset size, dependency scope, no heavy media, main-thread risk notes | `docs/performance_notes.md`, `tools/verify_release.py` | Locally complete |
| Phase 12 | Privacy, permissions and security: no personal data, no dangerous permissions, no internet, no analytics/ads/IAP, no committed secrets/dev URLs | `docs/privacy_and_permissions.md`, `play_store/data_safety_ru.md`, `tools/verify_release.py` | Locally complete |
| Phase 13 | Google Play readiness: target SDK, AAB, signing, listing, assets, privacy/data-safety/content-rating notes, owner inputs and manual Play actions | `docs/google_play_checklist.md`, `docs/google_play_sources.md`, `play_store`, `play_store/owner_release_inputs.md`, signed AAB | Locally complete except owner/Play Console gates |
| Phase 14 | Testing and QA: first launch, onboarding, home, game loop, settings, persistence, restart, screen sizes, compact About/privacy, TalkBack, no internet posture, emulator automation | `docs/qa_test_plan.md`, `docs/qa_artifacts`, `app/src/test`, `app/src/androidTest`, `docs/release_report.md` | Locally complete |
| Phase 15 | Documentation package | `README.md`, `AGENTS.md`, `docs`, `play_store` | Locally complete |
| Phase 16 | Release report: implementation, commands, results, failures/fixes, artifacts, risks, manual actions | `docs/release_report.md` | Locally complete |

## Final Completion Criteria

| Criterion From RTF | Evidence | Status |
|---|---|---|
| Idea selected and justified | `docs/product_decision.md` | Locally complete |
| MVP fully implemented | `app/src/main`, `app/src/test`, `app/src/androidTest`, `docs/product_spec.md` | Locally complete |
| UI/UX looks like a finished mobile product | `docs/ui_audit.md`, real screenshots in `play_store/screenshots/phone` | Locally complete |
| Code is clean and maintainable | Pure game engine, ViewModel/UI split, unit and instrumentation tests, lint success | Locally complete |
| No placeholder content | `tools/verify_release.py`, `docs/content_audit.md` | Locally complete |
| Assets are consistent | `docs/asset_manifest.md`, `play_store/upload_manifest.md`, asset verifier checks | Locally complete |
| Main scenarios are checked | `docs/qa_test_plan.md`, `docs/release_report.md`, connected tests | Locally complete |
| Release build is prepared or limitation documented | Signed `app/build/outputs/bundle/release/app-release.aab` | Locally complete |
| Google Play checklist exists | `docs/google_play_checklist.md` | Locally complete |
| Release report exists | `docs/release_report.md` | Locally complete |

## External Manual Gates

- Fill the Play Console support/contact fields used by the privacy-policy inquiry mechanism.
- Host the final privacy policy on a public HTTPS URL.
- Back up `private/signing/qgrid-upload.p12` and `keystore.properties` in an owner-controlled secure location.
- Complete Play Console app-content, data-safety, content-rating, target-audience and store-listing forms.
- Run required internal/closed testing tracks for the publisher account type.
- Use `play_store/owner_release_inputs.md` as the single owner-input checklist before Play upload.
