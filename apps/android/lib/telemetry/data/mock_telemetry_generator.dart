import 'dart:math' as math;
import 'package:prana_mobile/telemetry/domain/telemetry_repository.dart';

class MockTelemetryGenerator {
  TelemetrySnapshot at(Duration elapsed, DateTime timestamp) {
    final seconds = elapsed.inMilliseconds / 1000.0;
    return TelemetrySnapshot(
      speedKnots: 10.2 + math.sin(seconds / 17) * 1.8,
      depthMetres: 8.2 + math.sin(seconds / 23) * .7,
      headingDegrees: (315 + math.sin(seconds / 31) * 12) % 360,
      position: TelemetryPosition(
        10.76230 + seconds * .000012,
        106.65110 + seconds * .000017,
      ),
      timestamp: timestamp,
    );
  }
}
