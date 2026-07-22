import 'package:flutter/material.dart';

abstract final class PranaTheme {
  static const _accent = Color(0xFF39C6B4);
  static const _surface = Color(0xFF10181D);

  static ThemeData dark() {
    final scheme = ColorScheme.fromSeed(
      seedColor: _accent,
      brightness: Brightness.dark,
      surface: _surface,
    );
    return ThemeData(
      useMaterial3: true,
      brightness: Brightness.dark,
      colorScheme: scheme,
      scaffoldBackgroundColor: const Color(0xFF091015),
      cardTheme: const CardThemeData(
        color: _surface,
        elevation: 0,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.all(Radius.circular(14)),
          side: BorderSide(color: Color(0xFF24343D)),
        ),
      ),
      inputDecorationTheme: const InputDecorationTheme(
        filled: true,
        fillColor: Color(0xFF111C22),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.all(Radius.circular(12)),
        ),
      ),
      snackBarTheme: const SnackBarThemeData(
        behavior: SnackBarBehavior.floating,
      ),
    );
  }
}
