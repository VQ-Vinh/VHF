import 'dart:math' as math;

enum MockControlMode { auto, manual }

/// Workspace-local simulation. It has no Station or telemetry write interface.
class SteeringState {
  MockControlMode mode = MockControlMode.manual;
  double angle = 0;
  double? _previousBearing;

  void selectMode(MockControlMode value) {
    endDrag();
    mode = value;
    if (value == MockControlMode.auto) angle = 0;
  }

  void adjust(double delta) {
    if (mode == MockControlMode.manual) {
      angle = (angle + delta).clamp(-180.0, 180.0);
    }
  }

  void center() {
    endDrag();
    if (mode == MockControlMode.manual) angle = 0;
  }

  void beginDrag(double bearing) {
    if (mode == MockControlMode.manual) _previousBearing = bearing;
  }

  void drag(double bearing) {
    final previous = _previousBearing;
    if (previous == null || mode != MockControlMode.manual) return;
    var delta = bearing - previous;
    while (delta > math.pi) {
      delta -= 2 * math.pi;
    }
    while (delta < -math.pi) {
      delta += 2 * math.pi;
    }
    adjust(delta * 180 / math.pi);
    _previousBearing = bearing;
  }

  void endDrag() => _previousBearing = null;
}
