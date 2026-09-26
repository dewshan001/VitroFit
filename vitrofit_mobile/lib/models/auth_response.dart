import 'user_profile.dart';

class AuthResult {
  final String accessToken;
  final String refreshToken;
  final DateTime accessTokenExpiresAt;
  final DateTime refreshTokenExpiresAt;
  final UserProfile user;

  const AuthResult({
    required this.accessToken,
    required this.refreshToken,
    required this.accessTokenExpiresAt,
    required this.refreshTokenExpiresAt,
    required this.user,
  });

  factory AuthResult.fromJson(Map<String, dynamic> json) {
    return AuthResult(
      accessToken: json['accessToken'] as String,
      refreshToken: json['refreshToken'] as String,
      accessTokenExpiresAt: DateTime.parse(json['accessTokenExpiresAt'] as String),
      refreshTokenExpiresAt: DateTime.parse(json['refreshTokenExpiresAt'] as String),
      user: UserProfile.fromJson(json['user'] as Map<String, dynamic>),
    );
  }
}
