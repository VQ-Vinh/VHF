import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:prana_mobile/data/radio/api_history_repository.dart';
import 'package:prana_mobile/domain/radio/history_repository.dart';
import 'package:prana_mobile/features/station/history/history_controller.dart';
import 'auth_providers.dart';

final historyRepositoryProvider = Provider<HistoryRepository>(
  (ref) => ApiHistoryRepository(ref.watch(apiProvider)),
);
final historyControllerProvider = Provider<HistoryController>(
  (ref) => HistoryController(ref.watch(historyRepositoryProvider)),
);
