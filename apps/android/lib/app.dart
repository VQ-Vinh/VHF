import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_localizations/flutter_localizations.dart';

import 'core/localization.dart';
import 'core/theme.dart';
import 'features/speech/translation_speech_host.dart';
import 'providers.dart';
import 'router.dart';

class PranaMobileApp extends ConsumerWidget {
  const PranaMobileApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final locale = ref.watch(appLocaleProvider).locale;
    return MaterialApp.router(
      title: 'PRANA ELEX',
      debugShowCheckedModeBanner: false,
      themeMode: ThemeMode.light,
      theme: PranaTheme.light(),
      darkTheme: PranaTheme.dark(),
      locale: locale,
      supportedLocales: AppText.supportedLocales,
      localeResolutionCallback: AppText.resolve,
      localizationsDelegates: const [
        GlobalMaterialLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate,
        GlobalCupertinoLocalizations.delegate,
      ],
      builder:
          (context, child) =>
              TranslationSpeechHost(child: child ?? const SizedBox.shrink()),
      routerConfig: ref.watch(routerProvider),
    );
  }
}
