import 'dart:io';
import 'dart:typed_data';

import 'package:dio/dio.dart';
import 'package:firebase_auth/firebase_auth.dart';

import '../core/app_config.dart';
import '../features/tx/domain/tx_draft.dart';
import '../models/station.dart';

class PranaApi {
  PranaApi(this._auth)
    : _dio = Dio(
        BaseOptions(
          baseUrl: AppConfig.apiUrl,
          connectTimeout: const Duration(seconds: 15),
          receiveTimeout: const Duration(seconds: 30),
        ),
      ) {
    _dio.interceptors.add(
      InterceptorsWrapper(
        onRequest: (options, handler) async {
          final token = await _auth.currentUser?.getIdToken();
          if (token != null) options.headers['Authorization'] = 'Bearer $token';
          handler.next(options);
        },
        onError: (error, handler) async {
          final request = error.requestOptions;
          final user = _auth.currentUser;
          final alreadyRetried = request.extra['firebaseAuthRetried'] == true;
          if (error.response?.statusCode != 401 ||
              user == null ||
              alreadyRetried ||
              request.data is FormData) {
            handler.next(error);
            return;
          }

          try {
            final token = await user.getIdToken(true);
            request.extra['firebaseAuthRetried'] = true;
            request.headers['Authorization'] = 'Bearer $token';
            handler.resolve(await _dio.fetch<dynamic>(request));
          } catch (_) {
            handler.next(error);
          }
        },
      ),
    );
  }

  final FirebaseAuth _auth;
  final Dio _dio;

  Future<void> claimStation(String pairingId, String code) async {
    try {
      await _dio.post<void>(
        '/v1/station-pairings/$pairingId/claim',
        data: {'pairing_code': code.trim().toUpperCase()},
      );
    } on DioException catch (error) {
      throw PranaApiFailure.fromDio(error);
    }
  }

  Future<void> claimStationActivation(
    String setupId,
    String activationCode,
  ) async {
    try {
      await _dio.post<void>(
        '/v1/station-activations/claim',
        data: {
          'setup_id':
              setupId.replaceAll(RegExp(r'[^A-Za-z0-9]'), '').toUpperCase(),
          'activation_code':
              activationCode
                  .replaceAll(RegExp(r'[^A-Za-z0-9]'), '')
                  .toUpperCase(),
        },
      );
    } on DioException catch (error) {
      throw PranaApiFailure.fromDio(error);
    }
  }

  Future<void> setDesiredState(
    String stationId, {
    bool? running,
    String? targetLanguage,
    String? captureMode,
    String? audioDeviceId,
    String? txAudioDeviceId,
    bool refreshCapabilities = false,
    bool retry = false,
  }) async {
    try {
      await _dio.patch<void>(
        '/v1/stations/$stationId/desired-state',
        data: {
          if (running != null) 'running': running,
          if (targetLanguage != null) 'target_language': targetLanguage,
          if (captureMode != null) 'capture_mode': captureMode,
          if (audioDeviceId != null) 'audio_device_id': audioDeviceId,
          if (txAudioDeviceId != null) 'tx_audio_device_id': txAudioDeviceId,
          if (refreshCapabilities) 'refresh_capabilities': true,
          if (retry) 'retry': true,
        },
      );
    } on DioException catch (error) {
      throw PranaApiFailure.fromDio(error);
    }
  }

  Future<Map<String, dynamic>> account() async {
    final response = await _dio.get<Map<String, dynamic>>('/v1/me');
    return response.data ?? const {};
  }

  Future<bool> health() async {
    try {
      final response = await _dio.get<Map<String, dynamic>>('/health');
      return response.statusCode == 200 && response.data?['status'] == 'ok';
    } on DioException {
      return false;
    }
  }

  Future<List<Map<String, dynamic>>> plans() async {
    final response = await _dio.get<List<dynamic>>('/v1/plans');
    return (response.data ?? const [])
        .map((item) => Map<String, dynamic>.from(item as Map))
        .toList();
  }

  Future<void> selectPlan(String planId) async {
    await _dio.post<void>('/v1/subscription/select', data: {'plan_id': planId});
  }

  Future<List<Map<String, dynamic>>> devices() async {
    final response = await _dio.get<List<dynamic>>('/v1/devices');
    return (response.data ?? const [])
        .map((item) => Map<String, dynamic>.from(item as Map))
        .toList();
  }

  Future<void> revokeDevice(String deviceId) async {
    await _dio.delete<void>('/v1/devices/$deviceId');
  }

  Future<List<Map<String, dynamic>>> stations() async {
    final response = await _dio.get<List<dynamic>>('/v1/stations');
    return (response.data ?? const [])
        .map((item) => Map<String, dynamic>.from(item as Map))
        .toList();
  }

  Future<List<TranslationResult>> stationResults(
    String stationId,
    String sessionId, {
    int limit = 1000,
  }) async {
    final response = await _dio.get<List<dynamic>>(
      '/v1/stations/$stationId/sessions/$sessionId/results',
      queryParameters: {'limit': limit},
    );
    return (response.data ?? const [])
        .map(
          (item) =>
              TranslationResult.fromMap(Map<String, dynamic>.from(item as Map)),
        )
        .toList()
      ..sort(compareTranslationChronologically);
  }

  Future<List<TranslationResult>> stationLiveResults(
    String stationId, {
    required int timezoneOffsetMinutes,
    int limit = 1000,
  }) async {
    try {
      final response = await _dio.get<List<dynamic>>(
        '/v1/stations/$stationId/live/results',
        queryParameters: {
          'timezone_offset_minutes': timezoneOffsetMinutes,
          'limit': limit,
        },
      );
      return (response.data ?? const [])
          .map(
            (item) => TranslationResult.fromMap(
              Map<String, dynamic>.from(item as Map),
            ),
          )
          .toList()
        ..sort(compareTranslationChronologically);
    } on DioException catch (error) {
      throw PranaApiFailure.fromDio(error);
    }
  }

  Future<Uint8List> stationResultAudio(
    String stationId,
    String sessionId,
    String requestId,
  ) async {
    final response = await _dio.get<List<int>>(
      '/v1/stations/$stationId/sessions/$sessionId/results/$requestId/audio',
      options: Options(responseType: ResponseType.bytes),
    );
    return Uint8List.fromList(response.data ?? const <int>[]);
  }

  Future<List<StationHistoryDay>> stationHistoryDays(
    String stationId, {
    required int timezoneOffsetMinutes,
  }) async {
    final response = await _dio.get<List<dynamic>>(
      '/v1/stations/$stationId/history/days',
      queryParameters: {'timezone_offset_minutes': timezoneOffsetMinutes},
    );
    return (response.data ?? const [])
        .map(
          (item) =>
              StationHistoryDay.fromMap(Map<String, dynamic>.from(item as Map)),
        )
        .toList();
  }

  Future<List<StationHistoryDay>> txHistoryDays(
    String stationId, {
    required int timezoneOffsetMinutes,
  }) async {
    final response = await _dio.get<List<dynamic>>(
      '/v1/stations/$stationId/tx/history/days',
      queryParameters: {'timezone_offset_minutes': timezoneOffsetMinutes},
    );
    return (response.data ?? const [])
        .map(
          (item) =>
              StationHistoryDay.fromMap(Map<String, dynamic>.from(item as Map)),
        )
        .toList();
  }

  Future<List<TxDraft>> txHistoryDayJobs(
    String stationId,
    String date, {
    required int timezoneOffsetMinutes,
  }) async {
    final unique = <String, TxDraft>{};
    String? cursor;
    do {
      final response = await _dio.get<Map<String, dynamic>>(
        '/v1/stations/$stationId/tx/history/days/$date/jobs',
        queryParameters: {
          'timezone_offset_minutes': timezoneOffsetMinutes,
          'limit': 200,
          if (cursor != null) 'cursor': cursor,
        },
      );
      final data = response.data ?? const <String, dynamic>{};
      for (final value in data['items'] as List? ?? const []) {
        final draft = TxDraft.fromMap(Map<String, dynamic>.from(value as Map));
        unique[draft.id] = draft;
      }
      cursor = data['next_cursor'] as String?;
    } while (cursor != null && cursor.isNotEmpty);
    return unique.values.toList()..sort(
      (left, right) => (right.createdAt ?? DateTime(1970)).compareTo(
        left.createdAt ?? DateTime(1970),
      ),
    );
  }

  Future<Uint8List> txHistoryAudio(String stationId, String jobId) async {
    final response = await _dio.get<List<int>>(
      '/v1/stations/$stationId/tx/history/$jobId/audio',
      options: Options(responseType: ResponseType.bytes),
    );
    return Uint8List.fromList(response.data ?? const <int>[]);
  }

  Future<List<TranslationResult>> stationHistoryDayResults(
    String stationId,
    String date, {
    required int timezoneOffsetMinutes,
  }) async {
    final unique = <String, TranslationResult>{};
    String? cursor;
    do {
      final response = await _dio.get<Map<String, dynamic>>(
        '/v1/stations/$stationId/history/days/$date/results',
        queryParameters: {
          'timezone_offset_minutes': timezoneOffsetMinutes,
          'limit': 1000,
          if (cursor != null) 'cursor': cursor,
        },
      );
      final data = response.data ?? const <String, dynamic>{};
      for (final value in data['items'] as List? ?? const []) {
        final result = TranslationResult.fromMap(
          Map<String, dynamic>.from(value as Map),
        );
        unique[result.requestId] = result;
      }
      cursor = data['next_cursor'] as String?;
    } while (cursor != null && cursor.isNotEmpty);
    return unique.values.toList()..sort(compareTranslationChronologically);
  }

  Future<void> removeStation(String stationId) async {
    try {
      await _dio.delete<void>('/v1/stations/$stationId');
    } on DioException catch (error) {
      throw PranaApiFailure.fromDio(error);
    }
  }

  Future<TxDraft> createTxDraft(
    String stationId,
    String audioPath,
    String targetLanguage,
    String requestId,
  ) async {
    Future<Response<Map<String, dynamic>>> upload({
      bool refreshToken = false,
    }) async {
      final headers = <String, dynamic>{'X-Request-ID': requestId};
      if (refreshToken) {
        final token = await _auth.currentUser?.getIdToken(true);
        if (token != null) headers['Authorization'] = 'Bearer $token';
      }
      return _dio.post<Map<String, dynamic>>(
        '/v1/stations/$stationId/tx/drafts',
        data: FormData.fromMap({
          'target_language': targetLanguage,
          'audio': await MultipartFile.fromFile(
            audioPath,
            filename: File(audioPath).uri.pathSegments.last,
          ),
        }),
        options: Options(
          headers: headers,
          receiveTimeout: const Duration(seconds: 180),
        ),
      );
    }

    try {
      final response = await upload();
      return TxDraft.fromMap(response.data ?? const {});
    } on DioException catch (error) {
      if (error.response?.statusCode == 401 && _auth.currentUser != null) {
        try {
          final response = await upload(refreshToken: true);
          return TxDraft.fromMap(response.data ?? const {});
        } on DioException catch (retryError) {
          throw PranaApiFailure.fromDio(retryError);
        }
      }
      if (_isTransientUploadFailure(error)) {
        var delay = const Duration(milliseconds: 500);
        for (var attempt = 0; attempt < 5; attempt++) {
          try {
            final recovered = await txDraft(stationId, requestId);
            return recovered;
          } on PranaApiFailure catch (lookupError) {
            if (lookupError.code == 'TX_NOT_FOUND') break;
            if (lookupError.messageKey != 'error_connection_timeout' &&
                lookupError.messageKey != 'error_request_timeout' &&
                lookupError.messageKey != 'error_api_unreachable') {
              rethrow;
            }
          }
          await Future<void>.delayed(delay);
          if (delay < const Duration(seconds: 5)) delay *= 2;
        }
        try {
          final response = await upload();
          return TxDraft.fromMap(response.data ?? const {});
        } on DioException catch (retryError) {
          throw PranaApiFailure.fromDio(retryError);
        }
      }
      throw PranaApiFailure.fromDio(error);
    }
  }

  static bool _isTransientUploadFailure(DioException error) =>
      error.type == DioExceptionType.connectionTimeout ||
      error.type == DioExceptionType.sendTimeout ||
      error.type == DioExceptionType.receiveTimeout ||
      error.type == DioExceptionType.connectionError ||
      (error.response?.statusCode ?? 0) >= 500;

  Future<TxDraft> txDraft(String stationId, String draftId) async {
    try {
      final response = await _dio.get<Map<String, dynamic>>(
        '/v1/stations/$stationId/tx/drafts/$draftId',
      );
      return TxDraft.fromMap(response.data ?? const {});
    } on DioException catch (error) {
      throw PranaApiFailure.fromDio(error);
    }
  }

  Future<void> confirmTxDraft(
    String stationId,
    String draftId,
    String translation,
  ) async {
    try {
      await _dio.post<void>(
        '/v1/stations/$stationId/tx/drafts/$draftId/confirm',
        data: {'translation': translation},
      );
    } on DioException catch (error) {
      throw PranaApiFailure.fromDio(error);
    }
  }

  Future<void> cancelTxDraft(String stationId, String draftId) async {
    try {
      await _dio.delete<void>('/v1/stations/$stationId/tx/drafts/$draftId');
    } on DioException catch (error) {
      throw PranaApiFailure.fromDio(error);
    }
  }

  Future<TxDraft> retryTxDraft(String stationId, String draftId) async {
    try {
      final response = await _dio.post<Map<String, dynamic>>(
        '/v1/stations/$stationId/tx/drafts/$draftId/retry',
      );
      return TxDraft.fromMap(response.data ?? const {});
    } on DioException catch (error) {
      throw PranaApiFailure.fromDio(error);
    }
  }
}

class PranaApiFailure implements Exception {
  const PranaApiFailure(this.messageKey, {this.code, this.maxSeconds});

  final String messageKey;
  final String? code;
  final int? maxSeconds;

  factory PranaApiFailure.fromDio(DioException error) {
    switch (error.type) {
      case DioExceptionType.connectionTimeout:
        return const PranaApiFailure('error_connection_timeout');
      case DioExceptionType.sendTimeout:
      case DioExceptionType.receiveTimeout:
        return const PranaApiFailure('error_request_timeout');
      case DioExceptionType.connectionError:
        return const PranaApiFailure('error_api_unreachable');
      default:
        final data = error.response?.data;
        if (data is Map) {
          final detail = data['detail'];
          if (detail is Map) {
            final code = detail['code']?.toString();
            if (code == 'TX_AUDIO_TOO_LONG') {
              return PranaApiFailure(
                'tx_audio_too_long',
                code: code,
                maxSeconds: (detail['max_seconds'] as num?)?.toInt(),
              );
            }
            const codeKeys = {
              'STATION_NOT_PAIRED': 'error_station_not_paired',
              'STATION_REVOKED': 'error_station_revoked',
              'STATION_LIMIT_REACHED': 'error_station_limit_reached',
              'ACTIVATION_INVALID': 'error_activation_invalid',
              'STATION_ALREADY_CLAIMED': 'error_station_already_claimed',
            };
            final key = codeKeys[code];
            if (key != null) return PranaApiFailure(key, code: code);
            if (detail['message'] is String) {
              return PranaApiFailure(detail['message'] as String);
            }
          }
        }
        return const PranaApiFailure('error_request_failed');
    }
  }

  @override
  String toString() => messageKey;
}
