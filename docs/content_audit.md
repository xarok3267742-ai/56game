# Content Audit

## Контентные блоки

- Onboarding rules: done.
- Home copy: done.
- Game status messages: done.
- Settings labels/descriptions: done.
- About/privacy text: done; the in-app privacy copy is split into short points and states no personal data collection, local-only progress/settings, no ads/analytics/accounts/payments/internet permissions, Android backup disabled and local deletion through Android app data clearing or uninstall.
- Level titles: deterministic `Уровень N`; level tile status copy uses `Пройден` or `Доступен`, with no locked-level wording because all 36 MVP levels are playable offline.
- Store listing, data safety notes and privacy policy draft: done in `play_store`.

## Проверка

- Видимый UI на русском.
- Lorem ipsum отсутствует.
- Английские placeholder-строки в пользовательском UI отсутствуют.
- Main UI display strings are centralized in `app/src/main/res/values/strings.xml`; `rg` found no Russian string literals in `app/src/main/java` after the localization refactor.
- Android string resources are release-gated by `tools/verify_release.py`: strings must be non-empty, Russian user-facing copy, free of placeholder/debug/test markers, and the manifest label must reference `@string/app_name`.
- Ошибки, подсказки и score labels понятны: соседняя клетка, повтор, превышение суммы, `Сумма`, `Цель`, `Осталось`.
- Button labels checked in screenshots; shortened labels avoid clipping in gameplay action bar.

## Риски

- Store listing copy готова в checklist, но её нужно финально проверить владельцу продукта перед публикацией.
