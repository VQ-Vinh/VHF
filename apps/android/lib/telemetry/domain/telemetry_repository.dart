class TelemetryPosition {
  const TelemetryPosition(this.latitude, this.longitude);
  final double latitude;
  final double longitude;
}

enum TelemetrySource { mock }

class TelemetrySnapshot {
  const TelemetrySnapshot({
    required this.speedKnots,
    required this.depthMetres,
    required this.headingDegrees,
    required this.position,
    required this.timestamp,
    this.source = TelemetrySource.mock,
  });
  final double speedKnots;
  final double depthMetres;
  final double headingDegrees;
  final TelemetryPosition position;
  final DateTime timestamp;
  final TelemetrySource source;
}

abstract interface class TelemetryRepository {
  Stream<TelemetrySnapshot> watch(String stationId);
}
