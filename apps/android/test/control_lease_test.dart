import 'package:flutter_test/flutter_test.dart';
import 'package:prana_mobile/domain/station/station.dart';
import 'package:prana_mobile/features/station/radio/presentation/live_screen.dart';
import 'package:prana_mobile/runtime/vhf/live_controller.dart';

void main() {
  final now = DateTime.utc(2026, 9, 16, 12);

  StationModel station({Map<String, dynamic>? lease}) => StationModel.fromMap(
    'station-1',
    {
      'name': 'Bridge Pi',
      'platform': 'linux',
      'active': true,
      'capture_state': 'listening',
      'desired_state': {
        'running': true,
        'target_language': 'en',
        'generation': 1,
      },
      'observed_generation': 1,
      'session_id': 'session-1',
      'sequence': 1,
      'last_seen_at': now.subtract(const Duration(seconds: 2)).toIso8601String(),
      if (lease != null) 'control_lease': lease,
    },
  );

  Map<String, dynamic> lease({
    String holderKind = 'operator',
    Duration remaining = const Duration(seconds: 60),
  }) => {
    'holder_uid': 'operator-1',
    'holder_kind': holderKind,
    'holder_label': 'Ops desk',
    'expires_at': now.add(remaining).toIso8601String(),
    'epoch': 3,
  };

  group('control lease parsing', () {
    test('an absent lease leaves the owner in control', () {
      expect(station().controlLease, isNull);
      expect(station().controlHeldByOther(now), isFalse);
    });

    test('an operator lease takes control away from the owner', () {
      final model = station(lease: lease());
      expect(model.controlHeldByOther(now), isTrue);
      expect(model.controllerLabel, 'Ops desk');
    });

    test('an expired lease returns control without a server round trip', () {
      final model = station(
        lease: lease(remaining: const Duration(seconds: -1)),
      );
      expect(model.controlHeldByOther(now), isFalse);
    });

    test("the owner's own lease is not somebody else's", () {
      final model = station(lease: lease(holderKind: 'owner'));
      expect(model.controlHeldByOther(now), isFalse);
    });
  });

  group('view-only behaviour', () {
    test('view-only outranks a pending command and clears it', () async {
      final controller = LiveUxController(
        stationId: 'station-1',
        send: ({running, targetLanguage, retry = false}) async {},
      );
      await controller.setRunning(station(), true);
      expect(controller.state.phase, LiveCommandPhase.awaitingStation);

      controller.synchronize(station(lease: lease()), online: true, viewOnly: true);
      expect(controller.state.phase, LiveCommandPhase.viewOnly);
      expect(controller.state.pendingRunning, isNull);
    });

    test('releasing the lease returns the controller to idle', () {
      final controller = LiveUxController(
        stationId: 'station-1',
        send: ({running, targetLanguage, retry = false}) async {},
      );
      controller.synchronize(station(lease: lease()), online: true, viewOnly: true);
      expect(controller.state.phase, LiveCommandPhase.viewOnly);

      controller.synchronize(station(), online: true, viewOnly: false);
      expect(controller.state.phase, LiveCommandPhase.idle);
    });

    test('the start/stop toggle is locked while another client has control', () {
      expect(
        canToggleLiveStation(
          online: true,
          running: true,
          busy: false,
          commandPending: false,
          viewOnly: true,
        ),
        isFalse,
      );
      expect(
        canToggleLiveStation(
          online: true,
          running: true,
          busy: false,
          commandPending: false,
        ),
        isTrue,
      );
    });
  });
}
