# Product Decision

Checked on 4 June 2026 against the original RTF brief and current public Google Play listings.

## Goal

Create a small, realistic Android-first product for Russian-speaking/CIS users and bring it to a production-ready Google Play release candidate. The product should be simple, stable, visually finished, low-risk for Play policy, offline-first where possible, and not dependent on personal data, backend, accounts or payments.

## External Research

Public store research was used only to understand market shape, risks and differentiation. The product does not copy competitor names, brands, UI, rules, art, characters or store copy.

Observed references, rechecked on 4 June 2026:

- [Number Match - Number Games](https://play.google.com/store/apps/details?hl=en_US&id=com.easybrain.number.puzzle.game): 50M+ downloads, ads/IAP, daily/seasonal content and a data-safety posture that includes data collection/sharing. Signal: number puzzles have broad demand, but ad-heavy/data-heavy implementations create room for a calmer privacy-first alternative.
- [2248](https://play.google.com/store/apps/details?hl=en&id=com.vector.game.puzzle.numberlink): 5M+ downloads, connect-in-eight-directions number puzzle, ads/IAP and no user data collection declared. Signal: swipe/connect numeric mechanics are understandable to casual players, but «Линия 56» must avoid merge/endless-score cloning.
- [Make Ten](https://play.google.com/store/apps/details?id=com.bradellison.maketen): small minimalist sums puzzle, no ads marker visible, no data collection/sharing declared, currently a tiny install base. Signal: no-data indie numeric puzzle posture is possible, but market traction needs a sharper hook and stronger polish.
- [Match Ten - Number Puzzle](https://play.google.com/store/apps/details?hl=en_US&id=com.onet.number.free.puzzle.matchten): 1M+ downloads, ads/IAP, classic make-ten matching, weekly/daily/leaderboard-style scope and data collection/sharing declared. Signal: "make a target sum" is familiar, but pair-clearing plus live-content/economy scope is crowded and heavier than this MVP.
- [Take Ten: Match Numbers](https://play.google.com/store/apps/details?hl=en-us&id=com.shadowbiz.semechki): 1M+ downloads, ads/IAP, classic take-ten mechanics and data sharing declared. Signal: classic numeric puzzles can find audience, but generic clones and ad frustration are visible risks.

## Market Takeaways

- Numeric casual puzzles are understandable without localization-heavy content.
- The market has many match-ten, 2048-like and merge variants, so a clone would be weak.
- Users recognize line/connection interactions on grids, including diagonal movement.
- Privacy-first, no-ads, no-account positioning is a real differentiator against many larger casual puzzle listings.
- A small MVP should avoid live events, leaderboards, daily online content and economy systems.

## Scoring Rubric

Scale: 5 is best for this brief, 1 is weakest. "Backend" and "Data" are scored high when the idea does not need them.

| Idea | Clarity | Market | Build | UI | Uniqueness | Play Risk | Backend | Data | Content | Release | Monetization | Support | Total |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Линия 56 | 5 | 4 | 5 | 4 | 4 | 5 | 5 | 5 | 5 | 5 | 3 | 5 | 55 |
| Пары чисел | 5 | 4 | 5 | 3 | 2 | 5 | 5 | 5 | 5 | 5 | 3 | 5 | 52 |
| Память на иконках | 5 | 3 | 5 | 4 | 2 | 5 | 5 | 5 | 4 | 4 | 2 | 5 | 49 |
| Реакция/тайминг | 5 | 3 | 4 | 3 | 2 | 5 | 5 | 5 | 5 | 4 | 2 | 4 | 47 |
| Маршрутная головоломка | 4 | 3 | 3 | 4 | 4 | 5 | 5 | 5 | 4 | 4 | 3 | 4 | 48 |
| Мини-судоку | 4 | 4 | 3 | 4 | 2 | 5 | 5 | 5 | 3 | 3 | 3 | 4 | 45 |
| Ежедневный логический пазл | 4 | 4 | 3 | 4 | 3 | 5 | 4 | 5 | 2 | 3 | 3 | 3 | 43 |
| Словесная цепочка | 4 | 4 | 3 | 3 | 3 | 4 | 5 | 5 | 2 | 3 | 3 | 3 | 42 |
| Чек-челлендж | 5 | 3 | 4 | 3 | 3 | 4 | 5 | 4 | 2 | 3 | 2 | 3 | 41 |
| Бытовые мини-задачи | 4 | 3 | 3 | 4 | 3 | 4 | 5 | 4 | 2 | 3 | 2 | 3 | 40 |

## Candidate Notes

### 1. Линия 56

Player draws a continuous path through adjacent numbered cells and tries to reach exactly 56.

- Strengths: clear goal, compact UI, deterministic generated levels, no backend, no personal data, no heavy assets.
- Risks: must avoid feeling like a generic 2248/numberlink clone; solved through fixed target sum, no merging, no endless score chase and a calm offline structure.
- Monetization fit: optional future paid pack or "support developer" purchase, but MVP should remain no payments.
- Support complexity: low; levels are generated and tested.

### 2. Пары чисел

Player clears pairs with matching values or a target sum.

- Strengths: extremely understandable and easy to implement.
- Risks: crowded match-ten/number-match space; weaker uniqueness.
- Monetization fit: ads/IAP are common in the category, but that conflicts with the clean MVP goal.
- Support complexity: low.

### 3. Мини-судоку

Small Sudoku-like boards for short sessions.

- Strengths: proven audience and clear rules.
- Risks: generation, uniqueness validation and difficulty tuning add scope.
- Monetization fit: level packs later.
- Support complexity: medium due to puzzle validation.

### 4. Словесная цепочка

Player builds word chains from Russian words.

- Strengths: local-language fit and broad audience.
- Risks: content quality, dictionary licensing, ambiguity and moderation-like edge cases.
- Monetization fit: content packs later.
- Support complexity: medium/high because content is the product.

### 5. Память на иконках

Classic memory game with clean icon cards.

- Strengths: simple, visual, no data.
- Risks: very generic unless art direction is unusually strong.
- Monetization fit: weak for v1.
- Support complexity: low.

### 6. Реакция/тайминг

Short timing challenges with simple targets.

- Strengths: easy sessions and little content.
- Risks: less calm, more device/performance-sensitive, accessibility weaker.
- Monetization fit: weak for v1.
- Support complexity: low/medium due to tuning.

### 7. Маршрутная головоломка

Player finds a route through a grid under constraints.

- Strengths: close to a strong puzzle product.
- Risks: onboarding and solver/generator complexity higher than "Линия 56".
- Monetization fit: level packs later.
- Support complexity: medium.

### 8. Чек-челлендж

Small checklist challenges for daily habits or chores.

- Strengths: useful and simple.
- Risks: personal-data/privacy expectations and content volume.
- Monetization fit: weak without accounts/sync.
- Support complexity: medium.

### 9. Бытовые мини-задачи

Tiny practical household tasks or mini-calculators.

- Strengths: local utility angle.
- Risks: content breadth, edge cases, and lower replay value.
- Monetization fit: weak.
- Support complexity: medium.

### 10. Ежедневный логический пазл

One puzzle per day, calendar-style.

- Strengths: retention hook.
- Risks: daily content pipeline or backend expectations; more maintenance.
- Monetization fit: later premium archive.
- Support complexity: medium/high.

## Selected Idea

Selected: «Линия 56».

The game asks the player to connect neighboring cells in one continuous line so that the selected numbers add up to exactly 56.

## Why This Idea Wins

- It best matches the brief: small, realistic, offline-first, Android-first and low policy risk.
- It has a concrete hook: a fixed target number, not an endless merge score.
- It can ship with generated-but-verified levels, avoiding a large content pipeline.
- It supports a polished mobile UI with readable number tiles and a clear line path.
- It avoids backend, accounts, ads, analytics, payments and dangerous permissions.
- It differentiates from common number-match and 2248-like products by focusing on a finite calm path puzzle with a single target sum.

## Why The Others Were Not Selected

- Pair/match-ten puzzles are understandable but crowded and easy to perceive as clones.
- Mini-sudoku needs stronger generator/difficulty validation for a safe first release.
- Word chains need high-quality Russian dictionary/content work.
- Memory icons are too generic without substantial art investment.
- Reaction/timing is less aligned with calm short sessions and accessibility goals.
- Route puzzles are promising but require more complex onboarding and validation.
- Checklist/household apps need more text/content and may invite privacy expectations.
- Daily puzzles add ongoing content or backend pressure, which conflicts with the MVP.

## Target Audience

Русскоязычные Android-пользователи casual-сегмента who want a short, calm puzzle without account setup, internet dependency, ads or payments.

## Core Value Proposition

Спокойная числовая головоломка на 2-5 минут: считайте, соединяйте, собирайте 56.

## Primary User Scenario

1. User launches the app.
2. First launch shows three simple rules.
3. User starts a level.
4. User taps adjacent cells and watches the current sum and remaining value.
5. If the sum exceeds 56, user undoes or resets.
6. If the sum reaches 56, the level is saved as complete.
7. User continues to the next short level or exits; progress remains local.

## Product Risks

- **Generic puzzle risk:** mitigated by fixed target 56, line path selection and no merge/endless-score loop.
- **Difficulty risk:** mitigated by deterministic generator, unit tests for solvable paths and hint support.
- **UI readability risk:** mitigated by large tiles, short labels, responsive layout checks and screenshots from real app builds.
- **Accessibility risk:** mitigated by content descriptions, high contrast setting, font-scale checks and TalkBack exploratory QA on an API 36 Play Store AVD with Android Accessibility Suite.
- **Play policy risk:** minimized by no ads, no IAP, no accounts, no UGC, no backend and no dangerous permissions.
- **Privacy risk:** minimized by local-only progress/settings and disabled Android backup.
- **Store asset risk:** mitigated by verified Play icon, feature graphic, phone screenshots and large/tablet screenshots.

## MVP Scope

- 36 deterministic levels.
- Board sizes 5x5 and 6x6.
- Target sum 56.
- Selection path without repeats.
- Undo, reset and hint.
- Exceeded-state lock until undo/reset.
- Local progress and settings.
- Onboarding, home, levels, game, settings and about/privacy screens.
- Russian UI strings.
- Google Play handoff docs and release candidate artifacts.

## Out Of Scope For V1

- Ads.
- In-app purchases.
- Accounts.
- Analytics or crash reporting SDK.
- Backend or cloud sync.
- Daily online events.
- Leaderboards.
- User-generated content.
- Story mode.
- Complex store creatives beyond release-ready icon, feature graphic and screenshots.
- English localization beyond a future-ready structure.

## Release Decision

Proceed with «Линия 56» as the MVP and release candidate. It has the highest total score, the lowest implementation/policy risk, and the best path to a polished offline Android product within the requested scope.
