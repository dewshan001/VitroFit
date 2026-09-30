import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:vitrofit_mobile/screens/main_navigation_screen.dart';
import 'package:vitrofit_mobile/theme/app_theme.dart';
import 'package:provider/provider.dart';
import 'package:vitrofit_mobile/state/app_state.dart';

void main() {
  setUpAll(() {
    GoogleFonts.config.allowRuntimeFetching = false;
  });

  testWidgets('MainNavigationScreen smoke test', (WidgetTester tester) async {
    final originalOnError = FlutterError.onError;
    // Suppress image asset loading errors in unit tests
    FlutterError.onError = (FlutterErrorDetails details) {
      final msg = details.exception.toString();
      if (msg.contains('Unable to load asset') ||
          msg.contains('HTTP request failed')) {
        return;
      }
      print('Caught exception: $msg');
      if (originalOnError != null) {
        originalOnError(details);
      } else {
        FlutterError.presentError(details);
      }
    };

    await tester.pumpWidget(
      ChangeNotifierProvider<AppState>(
        create: (_) => AppState(),
        child: MaterialApp(
          theme: AppTheme.darkTheme,
          home: const MainNavigationScreen(),
        ),
      ),
    );

    expect(find.text('VITROFIT'), findsOneWidget);

    // Unmount all widgets to dispose of infinite animation controllers
    await tester.pumpWidget(const SizedBox());

    // Advance time to clear any pending Future.delayed timers from flutter_animate delays
    await tester.pump(const Duration(seconds: 5));

    FlutterError.onError = originalOnError;
  });
}
