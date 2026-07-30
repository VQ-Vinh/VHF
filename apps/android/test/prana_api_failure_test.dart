import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:prana_mobile/services/prana_api.dart';

void main() {
  test('maps Station API error codes to localized message keys', () {
    const expected = {
      'STATION_NOT_PAIRED': 'error_station_not_paired',
      'STATION_REVOKED': 'error_station_revoked',
      'STATION_LIMIT_REACHED': 'error_station_limit_reached',
      'ACTIVATION_INVALID': 'error_activation_invalid',
      'STATION_ALREADY_CLAIMED': 'error_station_already_claimed',
    };

    for (final entry in expected.entries) {
      final options = RequestOptions(path: '/v1/station-activations/claim');
      final error = DioException(
        requestOptions: options,
        response: Response<Map<String, dynamic>>(
          requestOptions: options,
          statusCode: 403,
          data: {
            'detail': {
              'code': entry.key,
              'message': 'Server detail must not leak into the UI',
            },
          },
        ),
        type: DioExceptionType.badResponse,
      );

      expect(
        PranaApiFailure.fromDio(error).messageKey,
        entry.value,
      );
    }
  });
}
