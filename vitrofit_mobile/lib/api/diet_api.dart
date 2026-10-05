import 'package:dio/dio.dart';
import '../models/diet.dart';
import 'agent_error.dart';
import 'api_client.dart';

/// A generation/refine run that ended as `failed` or `rejected`; carries the
/// agent steps completed before it stopped so the UI can explain what happened.
class DietWorkflowFailed extends AgentException {
  final List<DietStep> steps;
  DietWorkflowFailed(super.message, this.steps);
}

/// Diet agent, via the VitroFit API (`/api/diet/*`), which proxies to the
/// DietPlanService with the signed-in user's token.
class DietApi {
  DietApi({Dio? dio}) : _dio = dio ?? ApiClient.instance.dio;

  final Dio _dio;

  Future<T> _guard<T>(Future<T> Function() call) async {
    try {
      return await call();
    } on DioException catch (e) {
      throw AgentException.fromDio(e, service: 'diet service');
    }
  }

  /// Starts generating a plan. Returns the workflow id immediately; poll
  /// [workflow] for progress and the finished plan.
  Future<String> generate(DietPrefs prefs) => _guard(() async {
    final response = await _dio.post('/diet/generate', data: prefs.toJson());
    return (response.data as Map<String, dynamic>)['workflowId'].toString();
  });

  Future<DietWorkflowStatus> workflow(String id) => _guard(() async {
    final response = await _dio.get('/diet/workflows/$id');
    return DietWorkflowStatus.fromJson(response.data as Map<String, dynamic>);
  });

  /// Polls [workflow] until it reaches a terminal status, reporting each poll
  /// through [onProgress]. Returns the finished plan; throws
  /// [DietWorkflowFailed] on failure/rejection or [AgentException] on timeout.
  Future<DietPlan> pollUntilDone(
    String id, {
    void Function(DietWorkflowStatus status)? onProgress,
    Duration interval = const Duration(seconds: 2),
    Duration timeout = const Duration(seconds: 240),
  }) async {
    final deadline = DateTime.now().add(timeout);
    while (DateTime.now().isBefore(deadline)) {
      final status = await workflow(id);
      onProgress?.call(status);
      if (status.isTerminal) {
        if (status.status == 'completed') {
          return DietPlan.fromWorkflow(status.raw);
        }
        throw DietWorkflowFailed(
          status.message ?? 'Could not generate a diet plan. Please try again.',
          status.steps,
        );
      }
      await Future<void>.delayed(interval);
    }
    throw const AgentException(
      'Generating your plan is taking longer than expected. Please try again.',
    );
  }

  /// Applies a free-text edit to a freshly generated plan; poll [workflow] after.
  Future<void> refine(String workflowId, String instruction) => _guard(
    () async => _dio.post(
      '/diet/workflows/$workflowId/refine',
      data: {'instruction': instruction},
    ),
  );

  Future<List<DietPlan>> savedPlans() => _guard(() async {
    final response = await _dio.get('/diet/plans');
    return (response.data as List)
        .map((e) => DietPlan.fromSaved(e as Map<String, dynamic>))
        .toList();
  });

  Future<void> confirm(DietPrefs prefs, DietPlan plan) => _guard(
    () async => _dio.post('/diet/confirm', data: plan.toSaveJson(prefs)),
  );

  Future<void> updatePlan(int id, DietPrefs prefs, DietPlan plan) => _guard(
    () async => _dio.put('/diet/plans/$id', data: plan.toSaveJson(prefs)),
  );

  Future<void> deletePlan(int id) =>
      _guard(() async => _dio.delete('/diet/plans/$id'));

  // --- Reviewer endpoints (Trainer / Admin only; the server enforces it) ---

  Future<List<DietApprovalItem>> pendingApprovals() => _guard(() async {
    final response = await _dio.get('/diet/approvals/pending');
    return (response.data as List)
        .map((e) => DietApprovalItem.fromJson(e as Map<String, dynamic>))
        .toList();
  });

  Future<void> decide(String workflowId, {required bool approve, String? note}) =>
      _guard(
        () async => _dio.post(
          '/diet/workflows/$workflowId/${approve ? 'approve' : 'reject'}',
          queryParameters: (note != null && note.isNotEmpty)
              ? {'note': note}
              : null,
        ),
      );
}
