import 'package:dio/dio.dart';
import 'package:firebase_auth/firebase_auth.dart';

import '../core/app_config.dart';

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
      ),
    );
  }

  final FirebaseAuth _auth;
  final Dio _dio;

  Future<void> claimStation(String pairingId, String code) async {
    await _dio.post<void>(
      '/v1/station-pairings/$pairingId/claim',
      data: {'pairing_code': code.trim().toUpperCase()},
    );
  }

  Future<void> claimStationActivation(
    String setupId,
    String activationCode,
  ) async {
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
  }

  Future<void> setDesiredState(
    String stationId, {
    bool? running,
    String? targetLanguage,
    bool retry = false,
  }) async {
    await _dio.patch<void>(
      '/v1/stations/$stationId/desired-state',
      data: {
        if (running != null) 'running': running,
        if (targetLanguage != null) 'target_language': targetLanguage,
        if (retry) 'retry': true,
      },
    );
  }

  Future<Map<String, dynamic>> account() async {
    final response = await _dio.get<Map<String, dynamic>>('/v1/me');
    return response.data ?? const {};
  }

  Future<void> revokeStation(String stationId) async {
    await _dio.delete<void>('/v1/stations/$stationId');
  }
}
