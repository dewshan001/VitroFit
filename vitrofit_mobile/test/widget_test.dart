import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:vitrofit_mobile/screens/main_navigation_screen.dart';
import 'package:vitrofit_mobile/theme/app_theme.dart';

void main() {
  setUpAll(() {
    GoogleFonts.config.allowRuntimeFetching = false;
  });

  testWidgets('MainNavigationScreen smoke test', (WidgetTester tester) async {
    // Suppress image asset loading errors in unit tests
    FlutterError.onError = (FlutterErrorDetails details) {
      if (details.exception.toString().contains('Unable to load asset') ||
          details.exception.toString().contains('HTTP request failed')) {
        return;
      }
      FlutterError.presentError(details);
    };

    await tester.pumpWidget(
      MaterialApp(
        theme: AppTheme.darkTheme,
        home: const MainNavigationScreen(),
      ),
    );

    expect(find.text('VITROFIT'), findsOneWidget);
  });
}
