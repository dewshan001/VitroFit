import 'package:dio/dio.dart';
import '../models/fitness.dart';
import 'agent_error.dart';
import 'api_client.dart';

/// Fitness agent, via the VitroFit API (`/api/fitness/*`). The Python agent
/// behind it is internal and never called from the app.
class FitnessApi {
  FitnessApi({Dio? dio}) : _dio = dio ?? ApiClient.instance.dio;

  final Dio _dio;

  // Plan generation runs the agent synchronously on the server (the web app
  // allows 150 s), so the shared client's 12 s read timeout is far too short.
  static final _aiOptions = Options(
    receiveTimeout: const Duration(seconds: 150),
  );

  Future<T> _guard<T>(Future<T> Function() call) async {
    try {
      return await call();
    } on DioException catch (e) {
      throw AgentException.fromDio(e, service: 'fitness service');
    }
  }

  /// Returns null when the user has not created a profile yet (HTTP 404).
  Future<FitnessProfile?> getProfile() async {
    try {
      final response = await _dio.get('/fitness/profile');
      return FitnessProfile.fromJson(response.data as Map<String, dynamic>);
    } on DioException catch (e) {
      if (e.response?.statusCode == 404) return null;
      throw AgentException.fromDio(e, service: 'fitness service');
    }
  }

  Future<FitnessProfile> saveProfile(FitnessProfile profile) => _guard(() async {
    final response = await _dio.put('/fitness/profile', data: profile.toJson());
    return FitnessProfile.fromJson(response.data as Map<String, dynamic>);
  });

  Future<void> deleteProfile() =>
      _guard(() async => _dio.delete('/fitness/profile'));

  Future<List<FitnessExercise>> exercises() => _guard(() async {
    final response = await _dio.get('/fitness/exercises');
    return (response.data as List)
        .map((e) => FitnessExercise.fromJson(e as Map<String, dynamic>))
        .toList();
  });

  /// All of the user's workflows, newest first (follows the paging).
  Future<List<FitnessWorkflowSummary>> listWorkflows() => _guard(() async {
    final items = <FitnessWorkflowSummary>[];
    var page = 1;
    while (true) {
      final response = await _dio.get(
        '/fitness/workflows',
        queryParameters: {'page': page},
      );
      final data = response.data as Map<String, dynamic>;
      final pageItems = (data['items'] as List? ?? [])
          .map((e) => FitnessWorkflowSummary.fromJson(e as Map<String, dynamic>))
          .toList();
      items.addAll(pageItems);
      final total = (data['total'] as num?)?.toInt() ?? items.length;
      final pageSize = (data['pageSize'] as num?)?.toInt() ?? 20;
      if (pageItems.isEmpty || items.length >= total || page * pageSize >= total) {
        break;
      }
      page++;
    }
    return items;
  });

  Future<FitnessWorkflow> workflow(String id) => _guard(() async {
    final response = await _dio.get('/fitness/workflows/$id');
    return FitnessWorkflow.fromJson(response.data as Map<String, dynamic>);
  });

  Future<FitnessHistory> history(String id) => _guard(() async {
    final response = await _dio.get('/fitness/workflows/$id/history');
    return FitnessHistory.fromJson(response.data as Map<String, dynamic>);
  });

  Future<FitnessWorkflow> start({String? previousWorkflowId}) =>
      _guard(() async {
        final response = await _dio.post(
          '/fitness/workflows',
          options: _aiOptions,
          data: {'previousWorkflowId': previousWorkflowId},
        );
        return FitnessWorkflow.fromJson(response.data as Map<String, dynamic>);
      });

  Future<void> saveProgress(String workflowId, ProgressInput input) =>
      _guard(
        () async => _dio.put(
          '/fitness/workflows/$workflowId/progress',
          options: _aiOptions,
          data: input.toJson(),
        ),
      );

  Future<void> retry(String workflowId) => _guard(
    () async => _dio.post(
      '/fitness/workflows/$workflowId/retry',
      options: _aiOptions,
      data: <String, dynamic>{},
    ),
  );

  Future<FitnessWorkflow> regenerate(String workflowId) => _guard(() async {
    final response = await _dio.post(
      '/fitness/workflows/$workflowId/regenerate',
      options: _aiOptions,
      data: <String, dynamic>{},
    );
    return FitnessWorkflow.fromJson(response.data as Map<String, dynamic>);
  });

  /// The saved three-month cycle for a workflow, or null. Failures are
  /// swallowed like on the web: it is only used to decide whether a review is due.
  Future<FitnessCycle?> nextCycle(String workflowId) async {
    try {
      final response = await _dio.get('/fitness/workflows/$workflowId/next-cycle');
      final data = response.data;
      return data is Map<String, dynamic> ? FitnessCycle.fromJson(data) : null;
    } on DioException {
      return null;
    }
  }

  Future<FitnessCycle?> saveCycleReview(
    String workflowId,
    CycleReviewInput review,
  ) => _guard(() async {
    final response = await _dio.post(
      '/fitness/workflows/$workflowId/next-cycle',
      data: review.toJson(),
    );
    final data = response.data;
    return data is Map<String, dynamic> ? FitnessCycle.fromJson(data) : null;
  });
}
