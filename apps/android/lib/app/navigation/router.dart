import 'package:flutter/material.dart';
import 'package:prana_mobile/features/station/workspace/station_workspace_screen.dart';
import 'package:prana_mobile/features/station/workspace/station_tab.dart';
import 'package:prana_mobile/app/di/auth_providers.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import 'package:prana_mobile/features/account/account_screen.dart';
import 'package:prana_mobile/features/auth/sign_in_screen.dart';
import 'package:prana_mobile/features/auth/verify_email_screen.dart';
import 'package:prana_mobile/features/pairing/pairing_screen.dart';
import 'package:prana_mobile/features/station/list/station_list_screen.dart';

final routerProvider = Provider<GoRouter>((ref) {
  final refresh = _RouterRefresh();
  ref.listen(authStateProvider, (_, _) => refresh.changed());
  final router = GoRouter(
    refreshListenable: refresh,
    initialLocation: '/stations',
    redirect: (context, state) {
      final auth = ref.read(authStateProvider);
      if (auth.isLoading) return null;
      final signedIn = auth.value != null;
      final signingIn = state.matchedLocation == '/sign-in';
      final verifying = state.matchedLocation == '/verify-email';
      final verified = auth.value?.emailVerified == true;
      if (!signedIn && !signingIn) return '/sign-in';
      if (!signedIn) return null;
      if (!verified && !verifying) return '/verify-email';
      if (verified && (signingIn || verifying)) return '/stations';
      return null;
    },
    routes: [
      GoRoute(path: '/sign-in', builder: (_, _) => const SignInScreen()),
      GoRoute(
        path: '/verify-email',
        builder: (_, _) => const VerifyEmailScreen(),
      ),
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
        path: '/stations/:id/:tab',
        pageBuilder:
            (_, state) => MaterialPage<void>(
              key: ValueKey(
                'workspace-${ref.read(authStateProvider).value?.uid}-${state.pathParameters['id']}',
              ),
              child: StationWorkspaceScreen(
                stationId: state.pathParameters['id']!,
                page: StationPage.fromPath(state.pathParameters['tab']),
              ),
            ),
      ),
      GoRoute(path: '/account', builder: (_, _) => const AccountScreen()),
    ],
  );
  ref.onDispose(() {
    router.dispose();
    refresh.dispose();
  });
  return router;
});

class _RouterRefresh extends ChangeNotifier {
  void changed() => notifyListeners();
}
