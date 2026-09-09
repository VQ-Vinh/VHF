import 'package:prana_mobile/l10n/app_localizations.dart';
import 'package:prana_mobile/app/di/auth_providers.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_localizations/flutter_localizations.dart';

import 'package:prana_mobile/core/localization.dart';
import 'package:prana_mobile/core/theme.dart';
import 'package:prana_mobile/runtime/station/station_runtime_host.dart';
import 'package:prana_mobile/app/navigation/router.dart';

class PranaMobileApp extends ConsumerWidget {
  const PranaMobileApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final locale = ref.watch(appLocaleProvider).locale;
    final themeMode = ref.watch(appThemeModeProvider).themeMode;
    return MaterialApp.router(
      title: 'PRANA ELEX',
      debugShowCheckedModeBanner: false,
      themeMode: themeMode,
      theme: PranaTheme.light(),
      darkTheme: PranaTheme.dark(),
      locale: locale,
      supportedLocales: AppLocalizations.supportedLocales,
      localeResolutionCallback: resolveAppLocale,
      localizationsDelegates: const [
        AppLocalizations.delegate,
        GlobalMaterialLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate,
        GlobalCupertinoLocalizations.delegate,
      ],
      builder:
          (context, child) =>
              StationRuntimeHost(child: child ?? const SizedBox.shrink()),
      routerConfig: ref.watch(routerProvider),
    );
  }
}
