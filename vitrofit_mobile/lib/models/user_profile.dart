enum UserRole { user, trainer, admin, gymOwner }

UserRole _roleFromDynamic(dynamic raw) {
  if (raw is String) {
    switch (raw.trim().toLowerCase()) {
      case 'trainer':
        return UserRole.trainer;
      case 'admin':
        return UserRole.admin;
      case 'gym_owner':
      case 'gymowner':
        return UserRole.gymOwner;
      default:
        return UserRole.user;
    }
  }
  if (raw is int) {
    switch (raw) {
      case 1:
        return UserRole.trainer;
      case 2:
        return UserRole.admin;
      case 3:
        return UserRole.gymOwner;
      default:
        return UserRole.user;
    }
  }
  return UserRole.user;
}

class UserProfile {
  final int id;
  final String firstName;
  final String lastName;
  final String email;
  final String? phone;
  final String? profileImageUrl;
  final UserRole role;

  const UserProfile({
    required this.id,
    required this.firstName,
    required this.lastName,
    required this.email,
    this.phone,
    this.profileImageUrl,
    this.role = UserRole.user,
  });

  String get fullName => "$firstName $lastName".trim();

  String get initials {
    final f = firstName.isNotEmpty ? firstName[0] : '';
    final l = lastName.isNotEmpty ? lastName[0] : '';
    final initials = "$f$l".toUpperCase();
    return initials.isEmpty ? "?" : initials;
  }

  factory UserProfile.fromJson(Map<String, dynamic> json) {
    return UserProfile(
      id: json['id'] as int,
      firstName: (json['firstName'] as String?) ?? '',
      lastName: (json['lastName'] as String?) ?? '',
      email: (json['email'] as String?) ?? '',
      phone: json['phone'] as String?,
      profileImageUrl: json['profileImageUrl'] as String?,
      role: _roleFromDynamic(json['role']),
    );
  }

  UserProfile copyWith({String? profileImageUrl}) {
    return UserProfile(
      id: id,
      firstName: firstName,
      lastName: lastName,
      email: email,
      phone: phone,
      profileImageUrl: profileImageUrl ?? this.profileImageUrl,
      role: role,
    );
  }
}
