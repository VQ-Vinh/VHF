import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:prana_mobile/core/user_region.dart';

void main() {
  setUp(() {
    FlutterSecureStorage.setMockInitialValues({});
  });

  test('region starts unset', () {
    final controller = UserRegionController(const FlutterSecureStorage());
    expect(controller.isSet, isFalse);
    expect(controller.timezoneName, isNull);
  });

  test('setting a region notifies and persists it', () async {
    final controller = UserRegionController(const FlutterSecureStorage());
    var notifications = 0;
    controller.addListener(() => notifications++);

    await controller.setRegion('VN', 'Asia/Ho_Chi_Minh');

    expect(controller.countryCode, 'VN');
    expect(controller.timezoneName, 'Asia/Ho_Chi_Minh');
    expect(controller.isSet, isTrue);
    expect(notifications, 1);
  });

  test('hydrate adopts the server value', () async {
    final controller = UserRegionController(const FlutterSecureStorage());
    await controller.setRegion('VN', 'Asia/Ho_Chi_Minh');

    await controller.hydrate(country: 'JP', timezone: 'Asia/Tokyo');

    expect(controller.countryCode, 'JP');
    expect(controller.timezoneName, 'Asia/Tokyo');
  });

  test('hydrate treats empty strings as unset', () async {
    final controller = UserRegionController(const FlutterSecureStorage());

    await controller.hydrate(country: '', timezone: '');

    expect(controller.isSet, isFalse);
    expect(controller.countryCode, isNull);
  });

  test('hydrate with an unchanged value does not notify', () async {
    final controller = UserRegionController(const FlutterSecureStorage());
    await controller.setRegion('VN', 'Asia/Ho_Chi_Minh');
    var notifications = 0;
    controller.addListener(() => notifications++);

    await controller.hydrate(country: 'VN', timezone: 'Asia/Ho_Chi_Minh');

    expect(notifications, 0);
  });

  group('CountryOption', () {
    const vietnam = CountryOption(
      code: 'VN',
      name: 'Vietnam',
      timezones: ['Asia/Ho_Chi_Minh'],
    );

    test('parses the API payload', () {
      final parsed = CountryOption.fromJson(const {
        'code': 'US',
        'name': 'United States',
        'timezones': ['America/New_York', 'America/Chicago'],
      });
      expect(parsed.code, 'US');
      expect(parsed.timezones, hasLength(2));
    });

    test('search matches name, code and zone', () {
      expect(vietnam.matches('viet'), isTrue);
      expect(vietnam.matches('VN'), isTrue);
      expect(vietnam.matches('ho_chi'), isTrue);
      expect(vietnam.matches(''), isTrue);
      expect(vietnam.matches('japan'), isFalse);
    });
  });
}
