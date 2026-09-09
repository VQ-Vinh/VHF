import 'package:prana_mobile/telemetry/domain/telemetry_repository.dart';
import 'mock_telemetry_generator.dart';

class MockTelemetryRepository implements TelemetryRepository {
  MockTelemetryRepository({
    DateTime Function()? clock,
    this.ticks,
    this.interval = const Duration(seconds: 1),
  }) : _clock = clock ?? DateTime.now;
  final DateTime Function() _clock;
  final Duration interval;
  final Stream<DateTime> Function()? ticks;
  final _generator = MockTelemetryGenerator();
  @override
  Stream<TelemetrySnapshot> watch(String stationId) async* {
    final started = _clock();
    yield _generator.at(Duration.zero, started);
    final events = ticks?.call() ?? Stream.periodic(interval, (_) => _clock());
    yield* events.map((now) => _generator.at(now.difference(started), now));
  }
}
