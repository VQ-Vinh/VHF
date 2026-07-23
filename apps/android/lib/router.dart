import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import 'features/account/account_screen.dart';
import 'features/auth/sign_in_screen.dart';
import 'features/history/history_screen.dart';
import 'features/live/live_screen.dart';
import 'features/pairing/pairing_screen.dart';
import 'features/stations/station_list_screen.dart';
import 'providers.dart';

final routerProvider = Provider<GoRouter>((ref) {
  final auth = ref.watch(authStateProvider);
  return GoRouter(
    initialLocation: '/stations',
    redirect: (context, state) {
      if (auth.isLoading) return null;
      final signedIn = auth.value != null;
      final signingIn = state.matchedLocation == '/sign-in';
      if (!signedIn && !signingIn) return '/sign-in';
      if (signedIn && signingIn) return '/stations';
      return null;
    },
    routes: [
      GoRoute(path: '/sign-in', builder: (_, _) => const SignInScreen()),
      GoRoute(path: '/stations', builder: (_, _) => const StationListScreen()),
      GoRoute(
        path: '/pair',
        builder: (_, state) => PairingScreen(initialUri: state.uri),
      ),
      GoRoute(
        path: '/activate',
        builder: (_, state) => PairingScreen(initialUri: state.uri),
      ),
      GoRoute(
        path: '/stations/:id/live',
        builder:
            (_, state) => LiveScreen(
              stationId: state.pathParameters['id']!,
              sessionId: state.uri.queryParameters['session'],
            ),
      ),
      GoRoute(
        path: '/stations/:id/history',
        builder:
            (_, state) => HistoryScreen(stationId: state.pathParameters['id']!),
      ),
      GoRoute(path: '/account', builder: (_, _) => const AccountScreen()),
    ],
  );
});
