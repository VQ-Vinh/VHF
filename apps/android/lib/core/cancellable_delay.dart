import 'dart:async';

/// One cancellable wait owned by a controller/repository lifecycle.
class CancellableDelay {
  Timer? _timer;
  Completer<void>? _pending;
  bool _closed = false;

  Future<void> wait(Duration duration) {
    if (_closed) return Future<void>.value();
    _finish();
    final pending = Completer<void>();
    _pending = pending;
    _timer = Timer(duration, () {
      if (!pending.isCompleted) pending.complete();
    });
    return pending.future;
  }

  void _finish() {
    _timer?.cancel();
    final pending = _pending;
    if (pending != null && !pending.isCompleted) pending.complete();
  }

  void close() {
    _closed = true;
    _finish();
  }
}
