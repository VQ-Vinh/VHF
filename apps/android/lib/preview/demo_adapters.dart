import 'dart:async';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:prana_mobile/data/auth/authentication_service.dart';
import 'package:prana_mobile/domain/station/station.dart';
import 'package:prana_mobile/domain/station/station_repository.dart';
import 'package:prana_mobile/domain/radio/tx/tx_draft.dart';
import 'package:prana_mobile/domain/radio/tx/tx_repository.dart';
import 'package:prana_mobile/domain/radio/tx/tx_recorder.dart';
import 'package:prana_mobile/domain/radio/source_audio_engine.dart';
import 'package:prana_mobile/domain/radio/speech_engine.dart';
import 'package:prana_mobile/domain/radio/history_audio_engine.dart';
import 'demo_store.dart';

class DemoUser implements User {
  @override
  String get uid => 'ui-preview-user';
  @override
  String get email => 'captain@example.invalid';
  @override
  String get displayName => 'Demo Captain';
  @override
  bool get emailVerified => true;
  @override
  bool get isAnonymous => false;
  @override
  String? get photoURL => null;
  @override
  List<UserInfo> get providerData => [];
  @override
  dynamic noSuchMethod(Invocation invocation) =>
      throw UnsupportedError('No Firebase in UI Preview');
}

class DemoAuthentication implements AuthenticationService {
  DemoAuthentication({this.onSignOut});
  final void Function()? onSignOut;
  User? user = DemoUser();
  final _changes = StreamController<User?>.broadcast(sync: true);
  Stream<User?> watch() => Stream<User?>.multi((controller) {
    final sub = _changes.stream.listen(controller.addSync);
    controller.addSync(user);
    controller.onCancel = sub.cancel;
  });
  void enter() {
    user = DemoUser();
    _changes.add(user);
  }

  @override
  Future<void> signOut() async {
    user = null;
    _changes.add(null);
    onSignOut?.call();
  }

  @override
  Future<void> signIn({
    required String email,
    required String password,
  }) async => enter();
  @override
  Future<void> signUp({
    required String email,
    required String password,
  }) async => enter();
  @override
  Future<bool> signInWithGoogle() async =>
      throw UnsupportedError(
        'UI Preview — Google sign-in chưa hỗ trợ / unavailable',
      );
  @override
  Future<void> linkGoogle() async =>
      throw UnsupportedError(
        'UI Preview — Liên kết tài khoản chưa hỗ trợ / Account linking unavailable',
      );
  @override
  Future<void> sendPasswordReset(String email) async =>
      throw UnsupportedError('UI Preview — Không gửi email / No email is sent');
  @override
  Future<void> resendEmailVerification() async {}
  @override
  Future<bool> refreshEmailVerification() async => true;
  void dispose() => _changes.close();
}

class DemoStationRepository implements StationRepository {
  DemoStationRepository(this.store);
  final DemoStore store;
  Stream<T> _watch<T>(T Function() value) => Stream<T>.multi((controller) {
    store.projectionSubscriptions++;
    final sub = store.changes.stream.listen((_) => controller.addSync(value()));
    controller.addSync(value());
    controller.onCancel = () {
      store.projectionSubscriptions--;
      return sub.cancel();
    };
  });
  @override
  Stream<List<StationModel>> watchStations(String uid) =>
      _watch(() => store.stationModels);
  @override
  Stream<StationModel?> watchStation(String uid, String stationId) => _watch(
    () => store.stationModels.where((s) => s.id == stationId).firstOrNull,
  );
  @override
  Future<void> setDesiredState(
    String stationId, {
    bool? running,
    String? targetLanguage,
    String? captureMode,
    String? audioDeviceId,
    String? txAudioDeviceId,
    bool refreshCapabilities = false,
    bool retry = false,
  }) async => store.setDesired(
    stationId,
    running: running,
    targetLanguage: targetLanguage,
    captureMode: captureMode,
    audioDeviceId: audioDeviceId,
    txAudioDeviceId: txAudioDeviceId,
    refreshCapabilities: refreshCapabilities,
    retry: retry,
  );
}

class DemoRecorder implements TxRecorder {
  bool recording = false;
  bool disposed = false;
  int stopCount = 0;
  @override
  Future<void> start() async {
    if (disposed) throw StateError('Disposed recorder');
    recording = true;
  }

  @override
  Future<String> stop() async {
    if (!recording || disposed) throw StateError('Not recording');
    recording = false;
    stopCount++;
    return 'demo://recording';
  }

  @override
  Future<void> cancel() async {
    recording = false;
  }

  @override
  Future<void> dispose() async {
    disposed = true;
    recording = false;
  }
}

class DemoTxRepository implements TxRepository {
  DemoTxRepository(this.store);
  final DemoStore store;
  @override
  Future<TxDraft> processRecording(TxRecordingInput input) async {
    await Future<void>.delayed(const Duration(milliseconds: 800));
    if (store.disposed) throw StateError('Demo session ended');
    final draft = TxDraft(
      id: input.requestId,
      stationId: input.stationId,
      duration: input.duration,
      targetLanguage: input.targetLanguage,
      transcript:
          input.targetLanguage == 'vi'
              ? 'Requesting harbor entry. Vessel Prana standing by for instructions.'
              : 'Xin phép vào cảng. Tàu Prana đang chờ chỉ dẫn.',
      translation:
          input.targetLanguage == 'vi'
              ? 'Xin phép vào cảng. Tàu Prana đang chờ chỉ dẫn.'
              : 'Requesting harbor entry. Vessel Prana standing by for instructions.',
      detectedLanguage: input.targetLanguage == 'vi' ? 'en' : 'vi',
      createdAt: store.clockNow,
      outputAvailable: true,
    );
    store.drafts[draft.id] = draft;
    store.activeDrafts[input.stationId] = draft.id;
    return draft;
  }

  @override
  Future<void> confirmTransmission(TxDraft draft, String translation) async {
    if (store.disposed) return;
    if (store.drafts[draft.id]?.status != 'review_ready') return;
    store.drafts[draft.id] = draft.copyWith(
      translation: translation,
      status: 'queued',
    );
    store.confirmedAt[draft.id] = store.clockNow;
  }

  @override
  Future<void> cancelDraft(String draftId) async {
    final draft = store.drafts[draftId];
    if (draft != null) {
      store.drafts[draftId] = draft.copyWith(status: 'cancelled');
    }
    store.activeDrafts.removeWhere((_, id) => id == draftId);
  }

  @override
  Future<TxDraft> getDraft(String stationId, String draftId) async =>
      store.drafts[draftId]!;
  @override
  Future<TxDraft> retryTransmission(TxDraft draft) async {
    store.drafts[draft.id] = draft.copyWith(status: 'queued');
    store.confirmedAt[draft.id] = store.clockNow;
    return store.drafts[draft.id]!;
  }

  @override
  Future<String?> activeDraftId(String stationId) async =>
      store.activeDrafts[stationId];
  @override
  Future<void> clearActiveDraft(String stationId) async {
    store.activeDrafts.remove(stationId);
  }
}

/// Completes simulated playback on stop too; never accesses audio devices.
class DemoPlayback
    implements HistoryAudioEngine, SourceAudioEngine, SpeechEngine {
  Timer? _timer;
  Completer<void>? _completion;
  bool get playing => _completion != null;
  Future<void> _simulate() {
    stop();
    final completion = _completion = Completer<void>();
    _timer = Timer(const Duration(seconds: 2), () => stop());
    return completion.future;
  }

  @override
  Future<void> play(String stationId, String id, [String? requestId]) =>
      _simulate();
  @override
  Future<String?> resolveLocale(String preferred) async => preferred;
  @override
  Future<void> speak(String text, String locale) => _simulate();
  @override
  Future<void> stop() async {
    _timer?.cancel();
    _completion?.complete();
    _completion = null;
  }

  @override
  Future<void> clearCache() => stop();
  @override
  Future<void> dispose() => stop();
}
