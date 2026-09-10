import 'package:flutter/material.dart';

/// The PRANA ELEX logo.
///
/// Both variants come from `tools/packaging/brand/prana-elex-logo.svg` through
/// `tools/packaging/generate_brand_assets.py`. Use the mark wherever the logo
/// is small; the wordmark in the lockup stops being readable below roughly
/// 128 logical pixels.
class PranaLogo extends StatelessWidget {
  const PranaLogo.mark({super.key, this.size = 52, this.color})
    : lockup = false;

  const PranaLogo.lockup({super.key, this.size = 156})
    : lockup = true,
      color = null;

  final double size;
  final bool lockup;
  final Color? color;

  @override
  Widget build(BuildContext context) => Image.asset(
    lockup ? 'assets/logo_lockup.png' : 'assets/logo_mark.png',
    key: ValueKey(lockup ? 'prana-logo-lockup' : 'prana-logo-mark'),
    width: size,
    height: lockup ? size * .72 : size,
    fit: BoxFit.contain,
    filterQuality: FilterQuality.high,
    color: color,
    colorBlendMode: color == null ? null : BlendMode.srcIn,
  );
}
