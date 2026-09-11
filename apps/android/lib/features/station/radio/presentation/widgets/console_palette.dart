import 'package:flutter/material.dart';

/// Ink for the Live VHF console, in both themes.
///
/// The dark values are the console brief's. The light ones are derived from
/// PranaTheme.light rather than inverted from the dark: the brief's cyan on
/// white is 1.75:1, so the light accent is a deeper teal at 5.6:1 on the panel
/// that also carries white text at 5.6:1.
@immutable
class ConsolePalette {
  const ConsolePalette._({
    required this.background,
    required this.panel,
    required this.hairline,
    required this.accent,
    required this.onAccent,
    required this.ink,
    required this.muted,
    required this.transmit,
    required this.onTransmit,
    required this.ok,
  });

  /// Behind the whole tab.
  final Color background;

  /// Cells and strips.
  final Color panel;

  /// The rules between cells. There are no card borders or radii.
  final Color hairline;

  /// Live state, the capture cell and the channel readout.
  final Color accent;
  final Color onAccent;

  final Color ink;
  final Color muted;

  /// Held PTT and STOP CAPTURE.
  final Color transmit;
  final Color onTransmit;

  /// A healthy link, such as API READY.
  final Color ok;

  static const dark = ConsolePalette._(
    background: Color(0xFF04101C),
    panel: Color(0xFF071A2B),
    hairline: Color(0xFF123048),
    accent: Color(0xFF35D6F0),
    onAccent: Color(0xFF04101C),
    ink: Color(0xFFE0EEF7),
    muted: Color(0xFF8AA4B8),
    transmit: Color(0xFFC33F4F),
    onTransmit: Colors.white,
    ok: Color(0xFF3FD69A),
  );

  static const light = ConsolePalette._(
    background: Color(0xFFF2F7FC),
    panel: Colors.white,
    hairline: Color(0xFFD4E2E5),
    accent: Color(0xFF0B7285),
    onAccent: Colors.white,
    ink: Color(0xFF0D2B4F),
    muted: Color(0xFF607983),
    transmit: Color(0xFFB12F40),
    onTransmit: Colors.white,
    ok: Color(0xFF21835A),
  );

  static ConsolePalette of(BuildContext context) =>
      Theme.of(context).brightness == Brightness.dark ? dark : light;
}

/// Numerals and states. Falls back to the platform face until the bundled
/// family is registered, so a missing asset degrades rather than breaks.
const String consoleMono = 'RobotoMono';

/// Labels.
const String consoleLabel = 'Archivo';

/// Size that follows the width it is laid out in, like CSS clamp(), before the
/// user's text scale is applied on top by [Text].
double consoleSize(double width, double factor, double min, double max) =>
    (width * factor).clamp(min, max);

/// Small uppercase label above a readout.
TextStyle consoleCaption(ConsolePalette palette, {double size = 10}) =>
    TextStyle(
      fontFamily: consoleLabel,
      fontSize: size,
      fontWeight: FontWeight.w700,
      letterSpacing: 1.1,
      color: palette.muted,
      height: 1.2,
    );

/// A state or numeral in the console's mono face.
TextStyle consoleState(
  ConsolePalette palette, {
  double size = 12,
  Color? color,
  FontWeight weight = FontWeight.w700,
}) => TextStyle(
  fontFamily: consoleMono,
  fontSize: size,
  fontWeight: weight,
  letterSpacing: 0.8,
  color: color ?? palette.ink,
  height: 1.2,
  fontFeatures: const [FontFeature.tabularFigures()],
);

/// A captioned readout or selector on the console: a label, then a value on a
/// row at least one touch target tall. No box and no radius; the cells around
/// it are separated by hairlines instead.
///
/// The HEARD, TRANSLATE TO and TRANSMIT IN fields all use this, so the three
/// language fields keep one frame and one height as the TX dock and the RX
/// strip are laid out independently.
class ConsoleField extends StatelessWidget {
  const ConsoleField({
    super.key,
    required this.caption,
    required this.child,
    this.valueKey,
  });
  final String caption;
  final Widget child;

  /// Put on the value row, which is the part a test measures or taps.
  final Key? valueKey;

  @override
  Widget build(BuildContext context) {
    final palette = ConsolePalette.of(context);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      mainAxisSize: MainAxisSize.min,
      children: [
        Text(caption.toUpperCase(), style: consoleCaption(palette)),
        Container(
          key: valueKey,
          constraints: const BoxConstraints(minHeight: 48),
          alignment: AlignmentDirectional.centerStart,
          child: child,
        ),
      ],
    );
  }
}
