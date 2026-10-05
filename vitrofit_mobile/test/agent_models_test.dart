import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:vitrofit_mobile/api/agent_error.dart';
import 'package:vitrofit_mobile/api/time_agent_api.dart';
import 'package:vitrofit_mobile/models/diet.dart';
import 'package:vitrofit_mobile/models/fitness.dart';
import 'package:vitrofit_mobile/models/timetable_slot.dart';
import 'package:vitrofit_mobile/widgets/floating_nav_bar.dart';

void main() {
  group('navigation', () {
    test('bottom bar has exactly the six agent tabs in order', () {
      expect(FloatingNavBar.items.map((i) => i.label).toList(), [
        'HOME',
        'FITNESS',
        'GYM',
        'DIET',
        'TIME',
        'PROFILE',
      ]);
      expect(FloatingNavBar.items.length, NavTab.profile + 1);
    });
  });

  group('fitness models', () {
    test('profile round-trips through JSON', () {
      final json = {
        'age': 30,
        'heightCm': 180.5,
        'weightKg': 75,
        'goal': 'strength',
        'days': [5, 1, 3],
        'sessionMinutes': 60,
        'equipment': ['gym'],
        'reviewRequired': false,
      };
      final p = FitnessProfile.fromJson(json);
      expect(p.days, [1, 3, 5]); // sorted
      expect(p.toJson()['heightCm'], 180.5);
      expect(p.toJson()['goal'], 'strength');
    });

    test('workflow with plan parses week/blocks', () {
      final w = FitnessWorkflow.fromJson({
        'id': 'abc',
        'status': 'Ready',
        'version': 1,
        'createdAt': '2026-10-01T10:00:00Z',
        'summary': 'ok',
        'safetyNote': 'be safe',
        'plan': {
          'week': 6,
          'days': [
            {
              'day': 1,
              'focus': 'Upper',
              'warmupMinutes': 5,
              'cooldownMinutes': 5,
              'exercises': [
                {
                  'exerciseId': 'push_up',
                  'sets': 3,
                  'repetitions': 10,
                  'restSeconds': 60,
                },
              ],
            },
          ],
        },
      });
      expect(w.isReady, isTrue);
      expect(w.plan!.isBlock, isTrue);
      expect(w.plan!.title, 'Workout block 2');
      expect(w.plan!.days.single.exercises.single.exerciseId, 'push_up');
    });

    test('progress input only sends areas when pain is reported', () {
      const input = ProgressInput(
        day: 1,
        rpe: 6,
        completed: true,
        pain: false,
        affectedAreas: ['legs'],
        performedOn: '2026-10-05',
      );
      expect(input.toJson()['affectedAreas'], isEmpty);
    });
  });

  group('diet models', () {
    test('saved plan keeps raw meals for re-saving', () {
      final plan = DietPlan.fromSaved({
        'id': 3,
        'createdAt': '2026-10-01T10:00:00Z',
        'approvalStatus': 'approved',
        'totalCalories': 2100,
        'macros': {'protein': 150, 'carbs': 200, 'fat': 60},
        'withinTolerance': true,
        'meals': [
          {
            'type': 'breakfast',
            'label': 'Breakfast',
            'items': [
              {
                'name': 'Oats',
                'portion': '80 g',
                'calories': 300,
                'macros': {'protein': 10, 'carbs': 50, 'fat': 5},
                'extra': 'kept',
              },
            ],
          },
        ],
      });
      expect(plan.id, 3);
      expect(plan.meals.single.calories, 300);
      final body = plan.toSaveJson(DietPrefs.defaults);
      expect((body['meals'] as List).single['items'][0]['extra'], 'kept');
      expect(body['inputs']['budgetCustomAmount'], isNull);
    });

    test('pending saved plan has no content', () {
      final plan = DietPlan.fromSaved({
        'id': 9,
        'createdAt': '2026-10-01T10:00:00Z',
        'approvalStatus': 'pending',
      });
      expect(plan.isPending, isTrue);
      expect(plan.meals, isEmpty);
    });

    test('completed workflow becomes a plan, high risk requires approval', () {
      final plan = DietPlan.fromWorkflow({
        'id': 'wf1',
        'status': 'completed',
        'approvalStatus': 'pending',
        'riskLevel': 'high',
        'targets': {
          'totalCalories': 1800,
          'macros': {'protein': 120, 'carbs': 180, 'fat': 50},
        },
        'meals': [],
        'finalOutcome': {'withinTolerance': false},
        'completedSteps': [
          {'agent': 'NutritionAnalystAgent', 'step': 1},
          {'agent': 'SafetyValidatorAgent', 'verdict': 'pass', 'refine': false},
        ],
      });
      expect(plan.requiresApproval, isTrue);
      expect(plan.withinTolerance, isFalse);
      expect(plan.steps.length, 2);
      expect(plan.totalCalories, 1800);
    });
  });

  group('timetable', () {
    test('slot parses description lines', () {
      final slot = TimetableSlot.fromJson({
        'id': 1,
        'day': 1,
        'startTime': '07:00:00',
        'endTime': '08:00:00',
        'title': 'Upper',
        'workoutId': 4,
        'workoutName': 'Upper',
        'workoutCategory': 'Adaptive',
        'workoutDescription': 'Push-ups, Rows ,  Plank',
      });
      expect(slot.day, ApiDay.monday);
      expect(slot.descriptionLines, ['Push-ups', 'Rows', 'Plank']);
    });

    test('generation result counts slots', () {
      final r = TimetableGeneration.fromJson({
        'status': 'Ready',
        'longTermImpact': 'Consistent',
        'timetable': {
          'week': 1,
          'slots': [{}, {}, {}],
        },
      });
      expect(r.slotCount, 3);
      expect(r.status, 'Ready');
    });
  });

  group('AgentException', () {
    DioException err(int status, dynamic data) => DioException(
      requestOptions: RequestOptions(path: '/x'),
      response: Response(
        requestOptions: RequestOptions(path: '/x'),
        statusCode: status,
        data: data,
      ),
      type: DioExceptionType.badResponse,
    );

    test('uses message, detail and validation errors', () {
      expect(
        AgentException.fromDio(err(400, {'message': 'Failed', 'errors': ['a', 'b']})).message,
        'Failed\na\nb',
      );
      expect(AgentException.fromDio(err(422, {'detail': 'Bad meal'})).message, 'Bad meal');
    });

    test('falls back to friendly status messages', () {
      expect(AgentException.fromDio(err(503, null), service: 'diet service').message,
          contains('diet service is unavailable'));
      expect(AgentException.fromDio(err(401, null)).message, contains('sign in'));
    });
  });
}
