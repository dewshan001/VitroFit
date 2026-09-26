/// Mirrors .NET's `System.DayOfWeek` enum ordering (Sunday = 0 ... Saturday = 6),
/// which is what the backend serializes `Day` as and expects on write.
enum ApiDay {
  sunday,
  monday,
  tuesday,
  wednesday,
  thursday,
  friday,
  saturday;

  int get netValue => index;

  String get label {
    switch (this) {
      case ApiDay.sunday:
        return 'Sunday';
      case ApiDay.monday:
        return 'Monday';
      case ApiDay.tuesday:
        return 'Tuesday';
      case ApiDay.wednesday:
        return 'Wednesday';
      case ApiDay.thursday:
        return 'Thursday';
      case ApiDay.friday:
        return 'Friday';
      case ApiDay.saturday:
        return 'Saturday';
    }
  }

  String get shortLabel => label.substring(0, 3).toUpperCase();

  static ApiDay fromNet(int value) => ApiDay.values[value % 7];

  /// Ordered starting on Monday, for a more natural weekly view.
  static List<ApiDay> get weekOrder => const [
        ApiDay.monday,
        ApiDay.tuesday,
        ApiDay.wednesday,
        ApiDay.thursday,
        ApiDay.friday,
        ApiDay.saturday,
        ApiDay.sunday,
      ];
}

/// A time-of-day value, since the backend sends/expects TimeSpan as "HH:mm:ss".
class ApiTime implements Comparable<ApiTime> {
  final int hour;
  final int minute;

  const ApiTime(this.hour, this.minute);

  factory ApiTime.fromApiString(String value) {
    final parts = value.split(':');
    return ApiTime(int.parse(parts[0]), parts.length > 1 ? int.parse(parts[1]) : 0);
  }

  String toApiString() =>
      '${hour.toString().padLeft(2, '0')}:${minute.toString().padLeft(2, '0')}:00';

  String get label {
    final period = hour >= 12 ? 'PM' : 'AM';
    final h12 = hour % 12 == 0 ? 12 : hour % 12;
    return '${h12.toString().padLeft(2, '0')}:${minute.toString().padLeft(2, '0')} $period';
  }

  int get totalMinutes => hour * 60 + minute;

  @override
  int compareTo(ApiTime other) => totalMinutes.compareTo(other.totalMinutes);
}

class TimetableSlot {
  final int id;
  final ApiDay day;
  final ApiTime startTime;
  final ApiTime endTime;
  final String title;
  final int workoutId;
  final String workoutName;
  final String workoutCategory;

  const TimetableSlot({
    required this.id,
    required this.day,
    required this.startTime,
    required this.endTime,
    required this.title,
    required this.workoutId,
    required this.workoutName,
    required this.workoutCategory,
  });

  factory TimetableSlot.fromJson(Map<String, dynamic> json) {
    return TimetableSlot(
      id: json['id'] as int,
      day: ApiDay.fromNet(json['day'] as int),
      startTime: ApiTime.fromApiString(json['startTime'] as String),
      endTime: ApiTime.fromApiString(json['endTime'] as String),
      title: (json['title'] as String?) ?? '',
      workoutId: json['workoutId'] as int,
      workoutName: (json['workoutName'] as String?) ?? '',
      workoutCategory: (json['workoutCategory'] as String?) ?? '',
    );
  }
}
