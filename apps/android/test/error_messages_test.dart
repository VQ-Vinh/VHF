import 'dart:io';

import 'package:dio/dio.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:prana_mobile/core/service_messages.dart';
import 'package:prana_mobile/data/network/prana_api.dart';
import 'package:prana_mobile/l10n/app_localizations.dart';

DioException _apiError(String code, {int status = 400}) {
  final options = RequestOptions(path: '/v1/test');
  return DioException(
    requestOptions: options,
    response: Response<Map<String, dynamic>>(
      requestOptions: options,
      statusCode: status,
      data: {
        'detail': {'code': code, 'message': 'Invalid TX transition'},
      },
    ),
    type: DioExceptionType.badResponse,
  );
}

Future<BuildContext> _context(WidgetTester tester, Locale locale) async {
  late BuildContext captured;
  await tester.pumpWidget(
    MaterialApp(
      locale: locale,
      localizationsDelegates: AppLocalizations.localizationsDelegates,
      supportedLocales: AppLocalizations.supportedLocales,
      home: Builder(
        builder: (context) {
          captured = context;
          return const SizedBox();
        },
      ),
    ),
  );
  return captured;
}

void main() {
  test('server detail.message never becomes the displayed text', () {
    final failure = PranaApiFailure.fromDio(_apiError('TX_INVALID_STATE'));
    expect(failure.messageKey, 'error_request_failed');
  });

  test('errors of any type resolve to a message key, not their text', () {
    expect(
      errorMessageKey(Exception('SocketException: host')),
      'error_request_failed',
    );
    expect(
      errorMessageKey(StateError('TX_SESSION_CLOSED')),
      'error_request_failed',
    );
    expect(
      errorMessageKey(_apiError('PAIRING_EXPIRED')),
      'error_pairing_expired',
    );
    expect(
      errorMessageKey(
        FirebaseException(plugin: 'cloud_firestore', code: 'permission-denied'),
      ),
      'error_request_failed',
    );
    expect(
      errorMessageKey(
        FirebaseException(plugin: 'cloud_firestore', code: 'unavailable'),
      ),
      'error_api_unreachable',
    );
  });

  test('Station last_error codes and exception text are mapped', () {
    expect(
      stationErrorKey('AUDIO_DEVICE_UNAVAILABLE'),
      'rx_audio_input_not_found',
    );
    expect(
      stationErrorKey('SUBSCRIPTION_INACTIVE: Subscription is not active'),
      'error_subscription_inactive',
    );
    expect(
      stationErrorKey('BACKEND_TIMEOUT: ReadTimeout(httpx)'),
      'error_station_processing',
    );
    expect(
      stationErrorKey('file_not_found', fallback: 'error_segment_failed'),
      'error_segment_failed',
    );
  });

  for (final locale in const [Locale('en'), Locale('vi')]) {
    testWidgets('every mapped code has its own text (${locale.languageCode})', (
      tester,
    ) async {
      final context = await _context(tester, locale);
      final generic = localizedServiceMessage(context, 'error_request_failed');
      const codes = [
        'PAIRING_CODE_INVALID',
        'PAIRING_EXPIRED',
        'PAIRING_ALREADY_USED',
        'RATE_LIMITED',
        'STATION_OFFLINE',
        'CONTROL_LOST',
        'AUDIO_DEVICE_UNAVAILABLE',
        'SUBSCRIPTION_INACTIVE',
        'EMAIL_NOT_VERIFIED',
        'PLAN_NOT_AVAILABLE',
        'HISTORY_LOCKED',
        'SERVICE_USAGE_LIMIT_REACHED',
      ];
      for (final code in codes) {
        final key = PranaApiFailure.fromCode(code)?.messageKey;
        expect(key, isNotNull, reason: code);
        expect(localizedServiceMessage(context, key!), isNot(generic));
      }
    });

    testWidgets(
      'unknown codes never render verbatim (${locale.languageCode})',
      (tester) async {
        final context = await _context(tester, locale);
        final l10n = AppLocalizations.of(context);
        expect(
          localizedServiceMessage(context, 'Invalid TX transition'),
          l10n.errorRequestFailed,
        );
        expect(txStatusLabel(l10n, 'some_new_status'), l10n.txStatusUnknown);
        expect(txStatusLabel(l10n, 'cancelled'), isNot('cancelled'));
      },
    );
  }

  test('no screen interpolates a raw error into the UI', () {
    // Raw errors carry Dio/Firebase/exception text meant for developers.
    final forbidden = [
      RegExp(r"'\$error'"),
      RegExp(r"'\$\{snapshot\.error\}'"),
      RegExp(r"Text\((error|exception)\.toString\(\)"),
      RegExp(r"error\s*[:=]\s*(error|exception)\.toString\(\)"),
      RegExp(r"_\s*=>\s*(code|status),"),
    ];
    final offenders = <String>[];
    for (final file in Directory('lib').listSync(recursive: true)) {
      if (file is! File || !file.path.endsWith('.dart')) continue;
      final lines = file.readAsLinesSync();
      for (var i = 0; i < lines.length; i++) {
        if (forbidden.any((pattern) => pattern.hasMatch(lines[i]))) {
          offenders.add('${file.path}:${i + 1}: ${lines[i].trim()}');
        }
      }
    }
    expect(offenders, isEmpty);
  });
}
