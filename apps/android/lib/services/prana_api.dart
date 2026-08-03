import 'package:dio/dio.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'dart:typed_data';

import '../core/app_config.dart';
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
              alreadyRetried) {
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
    final response = await _dio.get<List<dynamic>>(
      '/v1/stations/$stationId/live/results',
      queryParameters: {
        'timezone_offset_minutes': timezoneOffsetMinutes,
        'limit': limit,
      },
    );
    return (response.data ?? const [])
        .map(
          (item) =>
              TranslationResult.fromMap(Map<String, dynamic>.from(item as Map)),
        )
        .toList()
      ..sort(compareTranslationChronologically);
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
}

class PranaApiFailure implements Exception {
  const PranaApiFailure(this.messageKey);

  final String messageKey;

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
            const codeKeys = {
              'STATION_NOT_PAIRED': 'error_station_not_paired',
              'STATION_REVOKED': 'error_station_revoked',
              'STATION_LIMIT_REACHED': 'error_station_limit_reached',
              'ACTIVATION_INVALID': 'error_activation_invalid',
              'STATION_ALREADY_CLAIMED': 'error_station_already_claimed',
            };
            final key = codeKeys[detail['code']?.toString()];
            if (key != null) return PranaApiFailure(key);
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
