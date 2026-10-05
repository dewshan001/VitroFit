import 'user_profile.dart';

/// Result of verifying an email OTP: either a signed-in session, or (gym
/// owners awaiting approval) just a message and no tokens.
class VerifyEmailOutcome {
  final AuthResult? auth;
  final String? pendingMessage;

  const VerifyEmailOutcome._(this.auth, this.pendingMessage);
  factory VerifyEmailOutcome.signedIn(AuthResult auth) =>
      VerifyEmailOutcome._(auth, null);
  factory VerifyEmailOutcome.pending(String message) =>
      VerifyEmailOutcome._(null, message);

  bool get isPendingApproval => auth == null;
}

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
      accessTokenExpiresAt: DateTime.parse(
        json['accessTokenExpiresAt'] as String,
      ),
      refreshTokenExpiresAt: DateTime.parse(
        json['refreshTokenExpiresAt'] as String,
      ),
      user: UserProfile.fromJson(json['user'] as Map<String, dynamic>),
    );
  }
}
