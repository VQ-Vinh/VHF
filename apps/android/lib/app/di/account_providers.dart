import 'package:prana_mobile/app/di/auth_providers.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:prana_mobile/domain/account/plan_entitlements.dart';
import 'package:prana_mobile/core/user_region.dart';

final countriesProvider = FutureProvider<List<CountryOption>>((ref) async {
  final values = await ref.watch(apiProvider).countries();
  return values.map(CountryOption.fromJson).toList();
});

final accountProvider = FutureProvider<Map<String, dynamic>>((ref) {
  final user = ref.watch(authStateProvider).value;
  if (user == null) return const <String, dynamic>{};
  return ref.watch(apiProvider).account();
});

final planEntitlementsProvider = Provider<PlanEntitlements>((ref) {
  final account = ref.watch(accountProvider).value ?? const {};
  return PlanEntitlements.fromAccount(account);
});
