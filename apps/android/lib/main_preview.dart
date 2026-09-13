import 'package:flutter/material.dart';
import 'package:prana_mobile/preview/preview_app.dart';

/// Separate bootstrap: intentionally no Firebase, Google, mic or mobile config.
void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(const PreviewApp());
}
