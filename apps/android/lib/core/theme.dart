import 'package:flutter/material.dart';

abstract final class PranaTheme {
  static const navy = Color(0xFF0D2B4F);
  static const brandBlue = Color(0xFF123F7E);
  static const brandBlueBright = Color(0xFF4E8FD5);
  static const brandBlueSoft = Color(0xFFEAF2FB);
  static const canvas = Color(0xFFF2F7FC);
  static const surface = Color(0xFFFFFFFF);
  static const muted = Color(0xFF607983);

  static ThemeData light() {
    final scheme = ColorScheme.fromSeed(
      seedColor: brandBlue,
      brightness: Brightness.light,
      primary: brandBlue,
      onPrimary: Colors.white,
      surface: surface,
      onSurface: navy,
      error: const Color(0xFFB12F40),
    );
    return ThemeData(
      useMaterial3: true,
      colorScheme: scheme,
      scaffoldBackgroundColor: canvas,
      fontFamily: 'sans',
      appBarTheme: const AppBarTheme(
        backgroundColor: navy,
        foregroundColor: Colors.white,
        elevation: 0,
        centerTitle: false,
      ),
      cardTheme: const CardThemeData(
        color: surface,
        elevation: 0,
        margin: EdgeInsets.zero,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.all(Radius.circular(16)),
          side: BorderSide(color: Color(0xFFD4E2E5)),
        ),
      ),
      iconButtonTheme: IconButtonThemeData(
        style: IconButton.styleFrom(minimumSize: const Size(48, 48)),
      ),
      bottomSheetTheme: const BottomSheetThemeData(
        constraints: BoxConstraints(maxWidth: 720),
      ),
      inputDecorationTheme: InputDecorationTheme(
        helperMaxLines: 8,
        errorMaxLines: 8,
        filled: true,
        fillColor: surface,
        labelStyle: const TextStyle(color: muted),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(11),
          borderSide: const BorderSide(color: Color(0xFFB9CDD2)),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(11),
          borderSide: const BorderSide(color: Color(0xFFB9CDD2)),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(11),
          borderSide: const BorderSide(color: brandBlue, width: 2),
        ),
      ),
      filledButtonTheme: FilledButtonThemeData(
        style: FilledButton.styleFrom(
          backgroundColor: brandBlue,
          foregroundColor: Colors.white,
          minimumSize: const Size.fromHeight(48),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(10),
          ),
          textStyle: const TextStyle(fontWeight: FontWeight.w700),
        ),
      ),
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          foregroundColor: navy,
          minimumSize: const Size.fromHeight(48),
          side: const BorderSide(color: Color(0xFF9EBCC2)),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(10),
          ),
        ),
      ),
      floatingActionButtonTheme: const FloatingActionButtonThemeData(
        backgroundColor: brandBlue,
        foregroundColor: Colors.white,
      ),
      snackBarTheme: const SnackBarThemeData(
        behavior: SnackBarBehavior.floating,
      ),
    );
  }

  static ThemeData dark() => light().copyWith(
    brightness: Brightness.dark,
    scaffoldBackgroundColor: const Color(0xFF08141F),
    colorScheme: _darkScheme,
    textTheme:
        ThemeData(
          useMaterial3: true,
          colorScheme: _darkScheme,
          fontFamily: 'sans',
        ).textTheme,
    primaryTextTheme:
        ThemeData(
          useMaterial3: true,
          colorScheme: _darkScheme,
          fontFamily: 'sans',
        ).primaryTextTheme,
    iconTheme: IconThemeData(color: _darkScheme.onSurfaceVariant),
    listTileTheme: ListTileThemeData(
      iconColor: _darkScheme.onSurfaceVariant,
      textColor: _darkScheme.onSurface,
    ),
    canvasColor: const Color(0xFF08141F),
    cardColor: const Color(0xFF102536),
    dialogTheme: const DialogThemeData(backgroundColor: Color(0xFF102536)),
    cardTheme: const CardThemeData(
      color: Color(0xFF102536),
      elevation: 0,
      margin: EdgeInsets.zero,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.all(Radius.circular(16)),
        side: BorderSide(color: Color(0xFF345064)),
      ),
    ),
    bottomSheetTheme: const BottomSheetThemeData(
      backgroundColor: Color(0xFF102536),
      surfaceTintColor: Colors.transparent,
      constraints: BoxConstraints(maxWidth: 720),
    ),
    inputDecorationTheme: InputDecorationTheme(
      helperMaxLines: 8,
      errorMaxLines: 8,
      filled: true,
      fillColor: const Color(0xFF132A3B),
      labelStyle: const TextStyle(color: Color(0xFFABC2D0)),
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(11),
        borderSide: const BorderSide(color: Color(0xFF496579)),
      ),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(11),
        borderSide: const BorderSide(color: Color(0xFF496579)),
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(11),
        borderSide: const BorderSide(color: brandBlueBright, width: 2),
      ),
    ),
    outlinedButtonTheme: OutlinedButtonThemeData(
      style: OutlinedButton.styleFrom(
        foregroundColor: const Color(0xFFD7E8F3),
        minimumSize: const Size.fromHeight(48),
        side: const BorderSide(color: Color(0xFF66849A)),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
      ),
    ),
    dividerColor: const Color(0xFF345064),
    disabledColor: const Color(0xFF718591),
  );

  static final ColorScheme _darkScheme = ColorScheme.fromSeed(
    seedColor: brandBlueBright,
    brightness: Brightness.dark,
    primary: const Color(0xFF91C3FF),
    onPrimary: const Color(0xFF00315F),
    surface: const Color(0xFF102536),
    onSurface: const Color(0xFFE0EEF7),
    error: const Color(0xFFFFB2BA),
  );
}
