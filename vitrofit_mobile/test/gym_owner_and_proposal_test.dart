import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:vitrofit_mobile/api/gym_owner_api.dart';
import 'package:vitrofit_mobile/api/time_agent_api.dart';

void main() {
  group('sniffKind / validateGymFile', () {
    final jpeg = Uint8List.fromList([0xFF, 0xD8, 0xFF, 0xE0, 0, 0, 0, 0]);
    final png = Uint8List.fromList([0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A]);
    final pdf = Uint8List.fromList('%PDF-1.7'.codeUnits);
    final webp = Uint8List.fromList('RIFF0000WEBP'.codeUnits);
    final text = Uint8List.fromList('hello world!'.codeUnits);

    test('detects types from magic bytes', () {
      expect(sniffKind(jpeg), SniffedKind.jpeg);
      expect(sniffKind(png), SniffedKind.png);
      expect(sniffKind(webp), SniffedKind.webp);
      expect(sniffKind(pdf), SniffedKind.pdf);
      expect(sniffKind(text), SniffedKind.unknown);
    });

    test('photos reject pdf, licence accepts it', () {
      expect(validateGymFile(pdf, 100, allowPdf: false), isNotNull);
      expect(validateGymFile(pdf, 100, allowPdf: true), isNull);
      expect(validateGymFile(jpeg, 100, allowPdf: false), isNull);
    });

    test('rejects empty, oversized and unknown files', () {
      expect(validateGymFile(jpeg, 0, allowPdf: false), isNotNull);
      expect(
        validateGymFile(jpeg, GymLimits.maxFileBytes + 1, allowPdf: false),
        isNotNull,
      );
      expect(validateGymFile(text, 100, allowPdf: true), isNotNull);
    });
  });

  group('field validators', () {
    test('isHttpsUrl', () {
      expect(isHttpsUrl('https://gym.com'), isTrue);
      expect(isHttpsUrl('http://gym.com'), isFalse);
      expect(isHttpsUrl('https://localhost'), isFalse);
      expect(isHttpsUrl('https://user:pw@gym.com'), isFalse);
    });

    test('phone and email regexes', () {
      expect(gymPhoneRegex.hasMatch('+94 71 234 5678'), isTrue);
      expect(gymPhoneRegex.hasMatch('abc'), isFalse);
      expect(gymEmailRegex.hasMatch('a@b.co'), isTrue);
      expect(gymEmailRegex.hasMatch('a@b'), isFalse);
    });
  });

  group('timetable proposal parsing', () {
    test('parses a pending proposal', () {
      final p = TimetableProposal.fromJson({
        'id': 4,
        'status': 'Pending',
        'longTermImpact': 'Better endurance',
        'slots': [
          {
            'day': 1,
            'startTime': '07:00',
            'endTime': '08:00',
            'focus': 'Upper body',
            'durationMinutes': 60,
            'description': 'Push day',
          },
        ],
      });
      expect(p.isPending, isTrue);
      expect(p.slots.single.focus, 'Upper body');
      expect(p.reviewedAt, isNull);
    });

    test('generation response uses top-level slotCount', () {
      final g = TimetableGeneration.fromJson({
        'status': 'PendingVerification',
        'proposalId': 4,
        'slotCount': 5,
        'longTermImpact': 'x',
        'message': 'sent',
      });
      expect(g.isPendingVerification, isTrue);
      expect(g.slotCount, 5);
      expect(g.message, 'sent');
    });
  });
}
