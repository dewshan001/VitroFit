import 'package:dio/dio.dart';
import '../models/fitness.dart';
import 'agent_error.dart';
import 'api_client.dart';

/// Result of `POST /fitness/workflows/{id}/timetable`. The generated slots are
/// NOT applied yet: the API stores them as a proposal (`PendingVerification`)
/// that a gym owner / admin must approve.
class TimetableGeneration {
  final String status; // PendingVerification (older API: Ready | ReviewRequired)
  final String longTermImpact;
  final int slotCount;
  final String? message;

  const TimetableGeneration({
    required this.status,
    required this.longTermImpact,
    required this.slotCount,
    this.message,
  });

  bool get isPendingVerification => status == 'PendingVerification';

  factory TimetableGeneration.fromJson(Map<String, dynamic> json) {
    final timetable = json['timetable'];
    final slots = timetable is Map ? timetable['slots'] : null;
    return TimetableGeneration(
      status: (json['status'] as String?) ?? '',
      longTermImpact: (json['longTermImpact'] as String?) ?? '',
      slotCount: json['slotCount'] is int
          ? json['slotCount'] as int
          : (slots is List ? slots.length : 0),
      message: json['message'] as String?,
    );
  }
}

/// One generated session inside a [TimetableProposal]. `day` is 1-7 (Mon-Sun).
class ProposalSlot {
  final int day;
  final String startTime; // HH:mm
  final String endTime;
  final String focus;
  final int durationMinutes;
  final String description;

  const ProposalSlot({
    required this.day,
    required this.startTime,
    required this.endTime,
    required this.focus,
    required this.durationMinutes,
    required this.description,
  });

  factory ProposalSlot.fromJson(Map<String, dynamic> json) => ProposalSlot(
    day: (json['day'] as num?)?.toInt() ?? 1,
    startTime: (json['startTime'] as String?) ?? '',
    endTime: (json['endTime'] as String?) ?? '',
    focus: (json['focus'] as String?) ?? '',
    durationMinutes: (json['durationMinutes'] as num?)?.toInt() ?? 0,
    description: (json['description'] as String?) ?? '',
  );
}

/// The user's latest timetable verification request (`GET /timetable/proposal`).
class TimetableProposal {
  final int id;
  final String status; // Pending | Approved | Rejected
  final List<ProposalSlot> slots;
  final String longTermImpact;
  final String? reviewNote;
  final String? reviewerName;
  final DateTime? reviewedAt;

  const TimetableProposal({
    required this.id,
    required this.status,
    required this.slots,
    required this.longTermImpact,
    this.reviewNote,
    this.reviewerName,
    this.reviewedAt,
  });

  bool get isPending => status == 'Pending';
  bool get isApproved => status == 'Approved';
  bool get isRejected => status == 'Rejected';

  factory TimetableProposal.fromJson(Map<String, dynamic> json) {
    final rawSlots = json['slots'];
    return TimetableProposal(
      id: (json['id'] as num?)?.toInt() ?? 0,
      status: (json['status'] as String?) ?? '',
      slots: rawSlots is List
          ? rawSlots
                .whereType<Map<String, dynamic>>()
                .map(ProposalSlot.fromJson)
                .toList()
          : const [],
      longTermImpact: (json['longTermImpact'] as String?) ?? '',
      reviewNote: json['reviewNote'] as String?,
      reviewerName: json['reviewerName'] as String?,
      reviewedAt: json['reviewedAt'] is String
          ? DateTime.tryParse(json['reviewedAt'] as String)
          : null,
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

  /// The latest verification request, or null if the user never made one.
  Future<TimetableProposal?> getProposal() async {
    try {
      final response = await _dio.get('/timetable/proposal');
      final data = response.data;
      final proposal = data is Map ? data['proposal'] : null;
      if (proposal is Map<String, dynamic>) {
        return TimetableProposal.fromJson(proposal);
      }
      return null;
    } on DioException catch (e) {
      throw AgentException.fromDio(e, service: 'timetable service');
    }
  }

  Future<void> cancelProposal(int id) async {
    try {
      await _dio.post('/timetable/proposal/$id/cancel');
    } on DioException catch (e) {
      throw AgentException.fromDio(e, service: 'timetable service');
    }
  }

  /// Generates a timetable proposal for [workflowId]. It replaces the user's
  /// slots only after a reviewer approves it.
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
