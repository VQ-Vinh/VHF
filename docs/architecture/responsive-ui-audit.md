# Responsive UI audit and verification

Scope: PRANA Admin Web and Flutter Android only. Windows/Linux apps, runtime, API contracts and hardware remain unchanged.

## Audit before layout edits

The current UI rendering code, shared theme/widgets, templates, stylesheet, menu/dialog scripts and existing layout tests were inspected. Sizes for icons, borders, padding and skeleton placeholders are not blanket-removal targets.

| Android file | Existing sizing/scroll patterns to review |
|---|---|
| `apps/android/lib/features/account/account_screen.dart` | height:, width:, TextOverflow.ellipsis, ListView |
| `apps/android/lib/features/auth/sign_in_screen.dart` | height:, Stack( |
| `apps/android/lib/features/auth/verify_email_screen.dart` | height: |
| `apps/android/lib/features/pairing/pairing_screen.dart` | height:, ListView |
| `apps/android/lib/features/station/history/history_screen.dart` | height:, width:, ListView |
| `apps/android/lib/features/station/list/station_list_screen.dart` | height:, width:, GridView, ListView, LayoutBuilder |
| `apps/android/lib/features/station/settings/station_settings_screen.dart` | height:, width:, TextOverflow.ellipsis, ListView |
| `apps/android/lib/features/station/workspace/station_workspace_screen.dart` | width:, TextOverflow.ellipsis, Stack( |
| `apps/android/lib/features/station/shared/widgets/translation_result_card.dart` | height: |
| `apps/android/lib/features/station/radio/presentation/live_screen.dart` | height:, LayoutBuilder |
| `apps/android/lib/features/station/radio/presentation/widgets/language_strip.dart` | height:, width:, TextOverflow.ellipsis |
| `apps/android/lib/features/station/radio/presentation/widgets/live_feed.dart` | height:, width: |
| `apps/android/lib/features/station/radio/presentation/widgets/live_header.dart` | height:, width:, TextOverflow.ellipsis |
| `apps/android/lib/features/station/radio/presentation/widgets/tx/tx_live_dock.dart` | height:, width:, TextOverflow.ellipsis, FittedBox, LayoutBuilder |
| `apps/android/lib/features/station/radio/presentation/widgets/tx/tx_ptt_button.dart` | height:, width:, TextOverflow.ellipsis |
| `apps/android/lib/features/station/radio/presentation/widgets/tx/tx_review_card.dart` | height:, ListView |
| `apps/android/lib/features/station/dashboard/presentation/dashboard_tab.dart` | height:, width:, LayoutBuilder |
| `apps/android/lib/features/station/control/presentation/widgets/control_widget.dart` | height: |
| `apps/android/lib/features/station/dashboard/presentation/widgets/depth_widget.dart` | content-based |
| `apps/android/lib/features/station/dashboard/presentation/widgets/heading_widget.dart` | content-based |
| `apps/android/lib/features/station/dashboard/presentation/widgets/instrument_value.dart` | height:, width:, FittedBox |
| `apps/android/lib/features/station/control/presentation/widgets/map_widget.dart` | height: |
| `apps/android/lib/features/station/control/presentation/widgets/position_widget.dart` | content-based |
| `apps/android/lib/features/station/dashboard/presentation/widgets/speed_widget.dart` | content-based |
| `apps/android/lib/features/station/shared/widgets/status_widget.dart` | height: |
| `apps/android/lib/core/widgets.dart` | height:, width:, TextOverflow.ellipsis |

| Web file | Responsibility |
|---|---|
| `services/prana_admin/templates/audit.html` | Server-rendered page; preserve forms, routes and fields |
| `services/prana_admin/templates/base.html` | Server-rendered page; preserve forms, routes and fields |
| `services/prana_admin/templates/dashboard.html` | Server-rendered page; preserve forms, routes and fields |
| `services/prana_admin/templates/error.html` | Server-rendered page; preserve forms, routes and fields |
| `services/prana_admin/templates/plans.html` | Server-rendered page; preserve forms, routes and fields |
| `services/prana_admin/templates/stations.html` | Server-rendered page; preserve forms, routes and fields |
| `services/prana_admin/templates/station_detail.html` | Server-rendered page; preserve forms, routes and fields |
| `services/prana_admin/templates/users.html` | Server-rendered page; preserve forms, routes and fields |
| `services/prana_admin/templates/user_detail.html` | Server-rendered page; preserve forms, routes and fields |
| `services/prana_admin/static/admin.css` | Shared responsive rules |
| `services/prana_admin/static/admin.js` | Menu, confirmation and plan editing; preserve actions |

## Decisions

- Shared Flutter content caps: auth 440, forms/review 720, reading/list/live 1120, dashboard 1440 logical pixels. Local constraints and text scale determine structure; no device model branching.
- Headers must size from text. Station card aspect ratios, the Live 520-height fallback, TX block scaling, fixed input heights and ellipsis are refactor targets. Preserve lazy workspace bodies, recorder pointer ownership and controller instances.
- Map/scanner use aspect ratio. Keyboard-aware sheets have one scroll owner. Compact controls keep at least 48 logical pixels of touch area.
- Web uses mobile-first grids, wrapping actions, a scrollable off-canvas menu and locally responsive tables with column labels. Keep native table roles and one copy of form/data nodes. No overflow hiding as a repair.
- Check widths 320,375,390,400,430,768,1024,1440,1920, vi/en, 1/1.5/2 text scale; include short landscape and keyboard states. Large viewport is not a desktop-app port.

## Baseline

- Admin: 18 passed and 12 subtests; existing dependency deprecation warnings.
- Flutter: 146 passed (`build/buildapp/responsive-flutter-baseline.log`).

## Final verification

### Resulting composition

Before: feature widgets independently chose fixed AppBar heights, field heights,
Station card aspect ratios and Live/TX size fallbacks. Admin used desktop-first
grids and horizontally scrolling tables.

After:

```text
Flutter feature UI
  -> core/responsive.dart
     -> ContentFrame: bounded reading/form widths
     -> ResponsiveScaffold / ResponsiveHeader: natural-height headers
     -> AdaptiveFields: stable Flex parent, width + text-scale reflow
  -> existing controllers, providers and domain contracts (unchanged)

Admin route -> existing Jinja template -> admin.css
  -> mobile-first grid, wrapping actions, off-canvas menu
  -> container-query table rows with localized column labels
  -> existing admin.js forms and confirmation handlers (unchanged)
```

| Change | Files / responsibility |
|---|---|
| CREATE | `apps/android/lib/core/responsive.dart`, responsive screen regression matrix, this audit |
| CREATE | `tests/admin/responsive_fixtures.py`, `check_responsive.cjs`, `test_responsive_templates.py` |
| MODIFY | Android theme/common header; Auth, Account, Pairing, Station list/workspace, Dashboard/map, Live/language/TX, History and Settings presentation |
| MODIFY | Admin stylesheet and table templates; asset cache version; affected layout and packaging assertions |
| MOVE / DELETE | None in this responsive iteration; earlier workspace migration remains separate |
| KEEP | Runtime/session/controller logic, repositories, REST schemas, Admin handlers/JavaScript, dependencies, Windows/Linux applications |

Live uses a content-height scroll area instead of a synthetic 520-height fallback.
Language controls and Account rows can stack; labels can wrap. Review/picker
sheets respect keyboard insets and retain their existing state owners. Map and
scanner frames use aspect ratio. Station cards grow naturally with their text.
The HTT pointer listener remains mounted during resizing; diameter changes apply
immediately while decoration/pulse animation remains intact.

### PASS — mock, contract and local UI checks

- `dart format --output=none --set-exit-if-changed lib test`: clean.
- `flutter analyze --no-pub`: no issues.
- Full `flutter test --no-pub`: 153 passed. Final combined run is recorded in
  `build/buildapp/responsive-flutter-final.log`.
- Admin: 19 passed + 12 subtests. Two existing dependency deprecation warnings.
- Android packaging/config + conventions: 59 passed + 78 subtests. The old
  assertion requiring fixed Station card aspect ratios was replaced with the
  responsive rule. Pytest used a fresh workspace temp directory because the
  host's default pytest temp/cache directories have access restrictions.
- Web: 450 local Edge/Playwright measurements, no horizontal overflow or
  JavaScript errors. All eight rendered pages, vi/en, widths
  320/375/390/400/430/768/1024/1440/1920, text enlargement 1/1.5/2 and short
  landscape. Menu Escape, plan editing, confirmation cancellation and draft
  retention passed. Requests were restricted to local GETs; no POST or external
  request was permitted. Text enlargement scales computed font/line sizes;
  it is not a claim about native browser zoom or every browser engine.
- Flutter matrices cover the same requested widths, additional short landscape,
  vi/en and text 1/1.5/2. Auth/verification/Pairing/Account/list/review checks visit
  lazy scroll content and simulate keyboard insets. Workspace checks preserve
  runtime, single subscription, UI state, draft/TX behavior and no START/STOP.
  A held-pointer resize test verifies one start and one release.
- API 36 emulator: attached to the existing staging debug installation and hot
  restarted Dart; visually checked Station list, Dashboard and Live, including
  portrait/landscape. No APK build, release or deployment was performed.

Evidence is local/ignored under `build/buildapp/`: `responsive-*.log`,
`responsive-portrait.png`, `responsive-dashboard.png`, `responsive-landscape.png`,
`responsive-live.png`, and `responsive-web/measurements.json` plus page screenshots.

Reproduce Web verification from the repository root:

```powershell
.\.venv\backend\Scripts\python.exe -m tests.admin.responsive_fixtures
python -m http.server 8875 --bind 127.0.0.1 --directory build/buildapp/responsive-web
# In another terminal, with Playwright available (or PLAYWRIGHT_MODULE pointing to it):
node tests/admin/check_responsive.cjs
```

`BROWSER_EXECUTABLE` can select an existing browser executable. No application
dependency was added for this verification tooling.

### CHƯA KIỂM CHỨNG — Station/hardware and remaining limits

- The Station observed on the emulator was offline. RF, physical microphone/PTT,
  server TX and fresh real RX were not exercised; mock tests do not prove them.
- Physical phones, camera scanning, software keyboards from different vendors,
  Firefox/WebKit and a complete platform accessibility audit remain unverified.
- Numeric instruments intentionally retain scale-down fitting within their card;
  labels/units wrap independently. Circular HTT controls, icons, padding and
  skeleton placeholders retain meaningful bounded dimensions. Large content
  uses vertical scrolling rather than shrinking the whole UI.
