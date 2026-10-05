import 'dart:typed_data';

import 'package:dio/dio.dart';

import 'api_client.dart';
import 'api_exception.dart';

/// Client-side limits that mirror the API's gym application validator.
class GymLimits {
  GymLimits._();

  static const int maxFileBytes = 5 * 1024 * 1024;
  static const int minPhotos = 1;
  static const int maxPhotos = 5;
  static const int maxEquipment = 30;
  static const int maxClasses = 20;
  static const int maxTagLength = 60;
}

enum SniffedKind { jpeg, png, webp, pdf, unknown }

/// Detects a file's real type from its leading bytes (not its name or MIME
/// type), matching the server's `DetectKind`.
SniffedKind sniffKind(Uint8List b) {
  if (b.length >= 3 && b[0] == 0xFF && b[1] == 0xD8 && b[2] == 0xFF) {
    return SniffedKind.jpeg;
  }
  if (b.length >= 8 &&
      b[0] == 0x89 &&
      b[1] == 0x50 &&
      b[2] == 0x4E &&
      b[3] == 0x47 &&
      b[4] == 0x0D &&
      b[5] == 0x0A &&
      b[6] == 0x1A &&
      b[7] == 0x0A) {
    return SniffedKind.png;
  }
  if (b.length >= 12 &&
      String.fromCharCodes(b.sublist(0, 4)) == 'RIFF' &&
      String.fromCharCodes(b.sublist(8, 12)) == 'WEBP') {
    return SniffedKind.webp;
  }
  if (b.length >= 5 && String.fromCharCodes(b.sublist(0, 5)) == '%PDF-') {
    return SniffedKind.pdf;
  }
  return SniffedKind.unknown;
}

/// Returns an error message, or null if the file is acceptable.
/// Photos must be JPG/PNG/WebP; the business licence may also be a PDF.
String? validateGymFile(
  Uint8List head,
  int sizeBytes, {
  required bool allowPdf,
}) {
  if (sizeBytes <= 0) return 'The file is empty.';
  if (sizeBytes > GymLimits.maxFileBytes) return 'Files must be 5 MB or smaller.';
  final kind = sniffKind(head);
  final ok =
      kind == SniffedKind.jpeg ||
      kind == SniffedKind.png ||
      kind == SniffedKind.webp ||
      (allowPdf && kind == SniffedKind.pdf);
  if (!ok) {
    return allowPdf
        ? 'Use a JPG, PNG or PDF file.'
        : 'Use a JPG, PNG or WebP image.';
  }
  return null;
}

bool isHttpsUrl(String value) {
  final uri = Uri.tryParse(value.trim());
  if (uri == null || uri.scheme != 'https') return false;
  if (uri.userInfo.isNotEmpty) return false;
  return uri.host.contains('.');
}

final RegExp gymPhoneRegex = RegExp(r'^\+?[0-9 ()-]{7,20}$');
final RegExp gymEmailRegex = RegExp(r'^[^\s@]+@[^\s@]+\.[^\s@]+$');

class GymApplication {
  final String firstName;
  final String lastName;
  final String email;
  final String phone;
  final String password;
  final String gymName;
  final String ownerRole;
  final String description;
  final String address;
  final String city;
  final String gymPhone;
  final String contactEmail;
  final String website;
  final String openingHours;
  final List<String> equipment;
  final List<String> classes;
  final List<String> gymPhotoPaths;
  final List<String> equipmentPhotoPaths;
  final String? licensePath;

  const GymApplication({
    required this.firstName,
    required this.lastName,
    required this.email,
    required this.phone,
    required this.password,
    required this.gymName,
    required this.ownerRole,
    required this.description,
    required this.address,
    required this.city,
    required this.gymPhone,
    required this.contactEmail,
    required this.website,
    required this.openingHours,
    required this.equipment,
    required this.classes,
    required this.gymPhotoPaths,
    required this.equipmentPhotoPaths,
    this.licensePath,
  });
}

class GymRegistrationResult {
  final String message;
  final String email;

  /// false when a rejected owner re-applied (no new OTP needed).
  final bool emailVerificationRequired;

  const GymRegistrationResult({
    required this.message,
    required this.email,
    required this.emailVerificationRequired,
  });
}

class GymOwnerApi {
  final Dio _dio = ApiClient.instance.dio;

  Future<GymRegistrationResult> register(GymApplication a) async {
    try {
      final form = FormData();
      void add(String k, String v) => form.fields.add(MapEntry(k, v.trim()));

      add('firstName', a.firstName);
      add('lastName', a.lastName);
      add('email', a.email);
      add('phone', a.phone);
      form.fields.add(MapEntry('password', a.password));
      add('gymName', a.gymName);
      add('ownerRole', a.ownerRole);
      add('description', a.description);
      add('address', a.address);
      add('city', a.city);
      add('gymPhone', a.gymPhone);
      add('contactEmail', a.contactEmail);
      add('website', a.website);
      add('openingHours', a.openingHours);
      for (final e in a.equipment) {
        form.fields.add(MapEntry('equipment', e));
      }
      for (final c in a.classes) {
        form.fields.add(MapEntry('classes', c));
      }
      for (final p in a.gymPhotoPaths) {
        form.files.add(MapEntry('gymPhotos', await MultipartFile.fromFile(p)));
      }
      for (final p in a.equipmentPhotoPaths) {
        form.files.add(
          MapEntry('equipmentPhotos', await MultipartFile.fromFile(p)),
        );
      }
      if (a.licensePath != null) {
        form.files.add(
          MapEntry('license', await MultipartFile.fromFile(a.licensePath!)),
        );
      }

      final response = await _dio.post(
        '/auth/register-gym-owner',
        data: form,
        options: Options(
          extra: {'skipAuth': true},
          sendTimeout: const Duration(minutes: 3),
          receiveTimeout: const Duration(minutes: 2),
        ),
      );
      final data = response.data as Map<String, dynamic>;
      return GymRegistrationResult(
        message: (data['message'] as String?) ?? 'Application submitted.',
        email: (data['email'] as String?) ?? a.email,
        emailVerificationRequired: data['emailVerificationRequired'] != false,
      );
    } on DioException catch (e) {
      throw ApiException.fromDioError(e);
    }
  }
}
