import 'package:dio/dio.dart';
import '../models/fitness.dart';
import 'agent_error.dart';
import 'api_client.dart';

/// Result of `POST /fitness/workflows/{id}/timetable`.
class TimetableGeneration {
  final String status; // Ready | ReviewRequired
  final String longTermImpact;
  final int slotCount;

  const TimetableGeneration({
    required this.status,
    required this.longTermImpact,
    required this.slotCount,
  });

  factory TimetableGeneration.fromJson(Map<String, dynamic> json) {
    final timetable = json['timetable'];
    final slots = timetable is Map ? timetable['slots'] : null;
    return TimetableGeneration(
      status: (json['status'] as String?) ?? '',
      longTermImpact: (json['longTermImpact'] as String?) ?? '',
      slotCount: slots is List ? slots.length : 0,
    );
  }
}

/// The fitness workflow the AI timetable is built from.
class ReadyFitnessPlan {
  final String workflowId;
  final String title; // e.g. "Beginner week 2 of 4"
  const ReadyFitnessPlan({required this.workflowId, required this.title});
}

/// Time Management agent, via the VitroFit API. The agent has no endpoint of
/// its own: it turns a Ready fitness workflow's plan into a weekly timetable,
/// which the API saves as the user's timetable slots.
class TimeAgentApi {
  TimeAgentApi({Dio? dio}) : _dio = dio ?? ApiClient.instance.dio;

  final Dio _dio;

  static final _aiOptions = Options(
    receiveTimeout: const Duration(seconds: 120),
  );

  /// The newest Ready fitness workflow, or null if the user has none yet
  /// (the web app does the same: first Ready item of page 1).
  Future<ReadyFitnessPlan?> latestReadyPlan() async {
    try {
      final list = await _dio.get(
        '/fitness/workflows',
        queryParameters: {'page': 1},
      );
      final items = ((list.data as Map<String, dynamic>)['items'] as List? ?? [])
          .cast<Map<String, dynamic>>();
      final ready = items.where((w) => w['status'] == 'Ready').toList();
      if (ready.isEmpty) return null;
      final id = ready.first['id'].toString();
      var title = 'Your latest fitness plan';
      try {
        final detail = await _dio.get('/fitness/workflows/$id');
        final plan = (detail.data as Map<String, dynamic>)['plan'];
        if (plan is Map<String, dynamic>) {
          title = FitnessPlan.fromJson(plan).title;
        }
      } on DioException {
        // The title is cosmetic; generation only needs the id.
      }
      return ReadyFitnessPlan(workflowId: id, title: title);
    } on DioException catch (e) {
      throw AgentException.fromDio(e, service: 'fitness service');
    }
  }

  /// Generates the timetable for [workflowId]. On success the server replaces
  /// all of the user's existing timetable slots (manual edits included).
  Future<TimetableGeneration> generate(
    String workflowId, {
    String preferences = '',
  }) async {
    try {
      final response = await _dio.post(
        '/fitness/workflows/$workflowId/timetable',
        options: _aiOptions,
        queryParameters: {'preferences': preferences},
      );
      return TimetableGeneration.fromJson(
        response.data as Map<String, dynamic>,
      );
    } on DioException catch (e) {
      throw AgentException.fromDio(e, service: 'time management agent');
    }
  }
}
