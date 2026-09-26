import 'package:flutter/foundation.dart';
import '../api/auth_api.dart';
import '../api/timetable_api.dart';
import '../api/workouts_api.dart';
import '../api/api_client.dart';
import '../models/auth_response.dart';
import '../models/timetable_slot.dart';
import '../models/user_profile.dart';
import '../models/workout.dart';
import '../services/token_storage.dart';

enum AuthStatus { initial, authenticated, unauthenticated }

/// App-wide state: auth session, current profile, workout catalog, and the
/// signed-in user's personal timetable. A single ChangeNotifier so every
/// screen/tab reflects the same real, backend-derived state.
class AppState extends ChangeNotifier {
  final _authApi = AuthApi();
  final _workoutsApi = WorkoutsApi();
  final _timetableApi = TimetableApi();

  AuthStatus authStatus = AuthStatus.initial;
  UserProfile? currentUser;

  List<Workout> workouts = [];
  bool workoutsLoading = false;
  String? workoutsError;

  List<TimetableSlot> timetableSlots = [];
  bool timetableLoading = false;
  String? timetableError;

  bool get isLoggedIn => authStatus == AuthStatus.authenticated;

  Future<void> init() async {
    ApiClient.instance.onSessionExpired = _handleSessionExpired;

    final token = await TokenStorage.instance.accessToken;
    if (token == null) {
      authStatus = AuthStatus.unauthenticated;
      notifyListeners();
      return;
    }

    try {
      currentUser = await _authApi.me();
      authStatus = AuthStatus.authenticated;
      unawaited(refreshAll());
    } catch (_) {
      await TokenStorage.instance.clear();
      authStatus = AuthStatus.unauthenticated;
    }
    notifyListeners();
  }

  void _handleSessionExpired() {
    currentUser = null;
    authStatus = AuthStatus.unauthenticated;
    workouts = [];
    timetableSlots = [];
    notifyListeners();
  }

  Future<void> register({
    required String firstName,
    required String lastName,
    required String email,
    required String phone,
    required String password,
  }) {
    return _authApi.register(
      firstName: firstName,
      lastName: lastName,
      email: email,
      phone: phone,
      password: password,
    );
  }

  Future<void> resendVerification(String email) => _authApi.resendVerification(email);

  Future<void> verifyEmail({required String email, required String otp}) async {
    final result = await _authApi.verifyEmail(email: email, otp: otp);
    await _applyAuthResult(result);
  }

  Future<void> login({required String email, required String password}) async {
    final result = await _authApi.login(email: email, password: password);
    await _applyAuthResult(result);
  }

  Future<void> _applyAuthResult(AuthResult result) async {
    await TokenStorage.instance.save(accessToken: result.accessToken, refreshToken: result.refreshToken);
    currentUser = result.user;
    authStatus = AuthStatus.authenticated;
    notifyListeners();
    unawaited(refreshAll());
  }

  Future<void> logout() async {
    await TokenStorage.instance.clear();
    currentUser = null;
    authStatus = AuthStatus.unauthenticated;
    workouts = [];
    timetableSlots = [];
    notifyListeners();
  }

  Future<void> changePassword({required String currentPassword, required String newPassword}) {
    return _authApi.changePassword(currentPassword: currentPassword, newPassword: newPassword);
  }

  Future<void> forgotPassword(String email) => _authApi.forgotPassword(email);

  Future<void> resetPassword({required String email, required String otp, required String newPassword}) {
    return _authApi.resetPassword(email: email, otp: otp, newPassword: newPassword);
  }

  Future<void> uploadPhoto(String filePath) async {
    final url = await _authApi.uploadPhoto(filePath);
    if (currentUser != null) {
      currentUser = currentUser!.copyWith(profileImageUrl: url);
      notifyListeners();
    }
  }

  Future<void> deleteAccount() async {
    await _authApi.deleteAccount();
    await logout();
  }

  Future<void> refreshAll() async {
    await Future.wait([loadWorkouts(), loadTimetable()]);
  }

  Future<void> loadWorkouts() async {
    workoutsLoading = true;
    workoutsError = null;
    notifyListeners();
    try {
      workouts = await _workoutsApi.list();
    } catch (e) {
      workoutsError = e.toString();
    } finally {
      workoutsLoading = false;
      notifyListeners();
    }
  }

  Future<void> loadTimetable() async {
    timetableLoading = true;
    timetableError = null;
    notifyListeners();
    try {
      final slots = await _timetableApi.list();
      slots.sort((a, b) {
        final dayCompare = ApiDay.weekOrder.indexOf(a.day).compareTo(ApiDay.weekOrder.indexOf(b.day));
        if (dayCompare != 0) return dayCompare;
        return a.startTime.compareTo(b.startTime);
      });
      timetableSlots = slots;
    } catch (e) {
      timetableError = e.toString();
    } finally {
      timetableLoading = false;
      notifyListeners();
    }
  }

  Future<void> createSlot({
    required ApiDay day,
    required ApiTime startTime,
    required ApiTime endTime,
    required String title,
    required int workoutId,
  }) async {
    final slot = await _timetableApi.create(
      day: day,
      startTime: startTime,
      endTime: endTime,
      title: title,
      workoutId: workoutId,
    );
    timetableSlots = [...timetableSlots, slot]
      ..sort((a, b) {
        final dayCompare = ApiDay.weekOrder.indexOf(a.day).compareTo(ApiDay.weekOrder.indexOf(b.day));
        if (dayCompare != 0) return dayCompare;
        return a.startTime.compareTo(b.startTime);
      });
    notifyListeners();
  }

  Future<void> updateSlot({
    required int id,
    required ApiDay day,
    required ApiTime startTime,
    required ApiTime endTime,
    required String title,
    required int workoutId,
  }) async {
    final updated = await _timetableApi.update(
      id: id,
      day: day,
      startTime: startTime,
      endTime: endTime,
      title: title,
      workoutId: workoutId,
    );
    timetableSlots = timetableSlots.map((s) => s.id == id ? updated : s).toList();
    notifyListeners();
  }

  Future<void> deleteSlot(int id) async {
    await _timetableApi.delete(id);
    timetableSlots = timetableSlots.where((s) => s.id != id).toList();
    notifyListeners();
  }
}

void unawaited(Future<void> future) {}
