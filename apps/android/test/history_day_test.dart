import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:prana_mobile/models/station.dart';

void main() {
  test('history day decodes API date', () {
    final day = StationHistoryDay.fromMap({
      'date': '2026-07-27',
      'result_count': 12,
      'first_result_at': '2026-07-26T17:05:00Z',
      'last_result_at': '2026-07-27T16:55:00Z',
      'locked': false,
    });

    expect(day.date, DateTime(2026, 7, 27));
    expect(day.apiDate, '2026-07-27');
    expect(day.resultCount, 12);
    expect(day.locked, isFalse);
  });

  test('history UI groups by day and never displays session ids', () {
    final source =
        File('lib/features/history/history_screen.dart').readAsStringSync();

    expect(source, contains("'history_day_title'"));
    expect(source, contains('day.locked'));
    expect(source, contains('TranslationResultCard'));
    expect(source, contains('enum _HistoryMode { rx, tx }'));
    expect(source, contains('_HistoryMode mode = _HistoryMode.rx'));
    expect(source, contains('txHistoryDays'));
    expect(source, contains('txHistoryDayJobs'));
    expect(source, contains('job.outputAvailable ? onPlay : null'));
    expect(source, isNot(contains("Text('TXT')")));
    expect(source, isNot(contains("Text('CSV')")));
    expect(source, isNot(contains('_export(')));
    expect(source, isNot(contains('clear_view')));
    expect(source, isNot(contains('hidden')));
    expect(source, isNot(contains('title: Text(doc.id)')));
    expect(source, isNot(contains('onSessionSelected')));
    final live = File('lib/features/live/live_screen.dart').readAsStringSync();
    expect(live, isNot(contains('?session=')));
    expect(live, isNot(contains('_HistoryModeBanner')));
  });

  test('live translations only include the current local day', () {
    TranslationResult result(String id, DateTime timestamp) =>
        TranslationResult(
          requestId: id,
          sequence: 1,
          transcript: '',
          translation: '',
          language: '',
          confidence: 0,
          timestamp: timestamp,
        );

    final now = DateTime(2026, 7, 28);
    final filtered = liveTranslationsForLocalDay([
      result('yesterday', DateTime(2026, 7, 27, 23, 59)),
      result('today', DateTime(2026, 7, 28)),
      result('tomorrow', DateTime(2026, 7, 29)),
    ], now);

    expect(filtered.map((item) => item.requestId), ['today']);
  });
}
