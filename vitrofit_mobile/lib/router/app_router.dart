import 'package:animations/animations.dart';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../screens/about_screen.dart';
import '../screens/auth/auth_screen.dart';
import '../screens/auth/forgot_password_screen.dart';
import '../screens/auth/verify_email_screen.dart';
import '../screens/main_navigation_screen.dart';
import '../screens/settings/change_password_screen.dart';
import '../screens/settings/info_screen.dart';
import '../screens/settings/personal_details_screen.dart';
import '../screens/splash_screen.dart';
import '../state/app_state.dart';

/// Wraps a screen in a Material fade-through transition, matching the web
/// app's soft page-level fade cues, for every route push/pop.
CustomTransitionPage<void> _fadeThroughPage(GoRouterState state, Widget child) {
  return CustomTransitionPage<void>(
    key: state.pageKey,
    child: child,
    transitionsBuilder: (context, animation, secondaryAnimation, child) {
      return FadeThroughTransition(
        animation: animation,
        secondaryAnimation: secondaryAnimation,
        child: child,
      );
    },
  );
}

GoRouter buildRouter(AppState appState) {
  return GoRouter(
    initialLocation: '/',
    refreshListenable: appState,
    redirect: (context, state) {
      final loc = state.matchedLocation;
      final onAuthFlow = loc.startsWith('/auth') || loc == '/verify-email' || loc == '/forgot-password';

      if (appState.authStatus == AuthStatus.initial) {
        return loc == '/' ? null : '/';
      }
      if (appState.authStatus == AuthStatus.unauthenticated) {
        return onAuthFlow ? null : '/auth';
      }
      // Authenticated.
      if (loc == '/' || onAuthFlow) return '/main';
      return null;
    },
    routes: [
      GoRoute(path: '/', pageBuilder: (context, state) => _fadeThroughPage(state, const SplashScreen())),
      GoRoute(path: '/auth', pageBuilder: (context, state) => _fadeThroughPage(state, const AuthScreen())),
      GoRoute(
        path: '/verify-email',
        pageBuilder: (context, state) =>
            _fadeThroughPage(state, VerifyEmailScreen(email: (state.extra as String?) ?? '')),
      ),
      GoRoute(
        path: '/forgot-password',
        pageBuilder: (context, state) => _fadeThroughPage(state, const ForgotPasswordScreen()),
      ),
      GoRoute(path: '/main', pageBuilder: (context, state) => _fadeThroughPage(state, const MainNavigationScreen())),
      GoRoute(path: '/main/about', pageBuilder: (context, state) => _fadeThroughPage(state, const AboutScreen())),
      GoRoute(
        path: '/main/change-password',
        pageBuilder: (context, state) => _fadeThroughPage(state, const ChangePasswordScreen()),
      ),
      GoRoute(
        path: '/main/personal-details',
        pageBuilder: (context, state) => _fadeThroughPage(state, const PersonalDetailsScreen()),
      ),
      GoRoute(
        path: '/main/notifications',
        pageBuilder: (context, state) => _fadeThroughPage(
          state,
          const InfoScreen(
            title: 'NOTIFICATION SETTINGS',
            icon: Icons.notifications_none,
            body: 'Choose what VitroFit can notify you about. These preferences are stored on this '
                'device only.',
            isTogglesDemo: true,
          ),
        ),
      ),
      GoRoute(
        path: '/main/billing',
        pageBuilder: (context, state) => _fadeThroughPage(
          state,
          const InfoScreen(
            title: 'PAYMENT & BILLING',
            icon: Icons.credit_card,
            body: 'VitroFit does not process payments in this app yet. For billing questions about '
                'your membership, reach out to our support team and we will help you directly.',
          ),
        ),
      ),
      GoRoute(
        path: '/main/support',
        pageBuilder: (context, state) => _fadeThroughPage(
          state,
          const InfoScreen(
            title: 'CUSTOMER SUPPORT',
            icon: Icons.help_outline,
            body: 'Need a hand? Email support@vitrofit.com or visit any VitroFit studio front desk and '
                'our team will sort you out.',
          ),
        ),
      ),
    ],
  );
}
