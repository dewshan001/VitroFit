using System.ComponentModel.DataAnnotations;
using System.Text.Json;

namespace VitroFit.API.Features.AdaptiveFitness;

public static class FitnessJson
{
    public static readonly JsonSerializerOptions Options = new(JsonSerializerDefaults.Web);
    public static string Write<T>(T value) => JsonSerializer.Serialize(value, Options);
    public static T Read<T>(string value) => JsonSerializer.Deserialize<T>(value, Options)
        ?? throw new InvalidOperationException("Invalid stored fitness data.");
}

public sealed record ProfileInput(
    [param: Range(18, 80)] int Age,
    [param: Range(100, 250)] double HeightCm,
    [param: Range(30, 300)] double WeightKg,
    [param: Required, RegularExpression("weight_loss|muscle_building|general_fitness|strength|endurance")] string Goal,
    [param: Required, MinLength(3), MaxLength(4)] int[] Days,
    [param: Range(20, 120)] int SessionMinutes,
    [param: Required, MaxLength(20)] string[] Equipment,
    bool ReviewRequired);

public sealed record StartRequest(Guid? PreviousWorkflowId);
public sealed record ReviewRequest(
    [param: Range(1, int.MaxValue)] int Version,
    [param: Required, RegularExpression("Approve|Reject|Revise")] string Decision,
    [param: Required, MinLength(3), MaxLength(500)] string Reason);
public sealed record ProgressInput(
    [param: Range(1, 7)] int Day, bool Completed,
    [param: Range(1, 10)] int Rpe, bool Pain, DateOnly PerformedOn,
    [param: MaxLength(8)] string[]? AffectedAreas = null);
public sealed record ExerciseDto(int Id, string Name, string Equipment, string MuscleGroup,
    string Instructions, bool BeginnerAllowed);
public sealed record Prescription(int ExerciseId, int Sets, int Repetitions, int RestSeconds,
    int? AdaptedFromExerciseId = null, string? AdaptationReason = null);
public sealed record PlanDay(int Day, string Focus, int WarmupMinutes, int CooldownMinutes,
    List<Prescription> Exercises, int? DurationMinutes = null);
public sealed record WorkoutPlan(int Week, List<PlanDay> Days);
public sealed record AgentProgress(int Day, bool Completed, int Rpe, bool Pain, string[]? AffectedAreas = null, int Block = 0);
public sealed record CycleExercise(int ExerciseId, string Name, int Sets, int Repetitions, int RestSeconds);
public sealed record FitnessCycleDay(int DayNumber, DateOnly Date, string Type, string? Focus, List<CycleExercise> Exercises);
public sealed record FitnessWeekAnalysis(int Week, int PlannedSessions, int CompletedSessions, int SkippedSessions, int PainReports, double? AverageRpe, int TotalVolume);
public sealed record FitnessCycleAnalysis(int PlannedSessions, int CompletedSessions, int SkippedSessions, int ModifiedSessions,
    int PainReports, double? AverageRpe, bool RecoveryAdjustment, List<FitnessWeekAnalysis> Weeks, CycleReviewInput? Review = null);
public sealed record CycleReviewInput(
    [param: Required, MaxLength(300)] string PainOrDiscomfort,
    [param: Required, MaxLength(300)] string InjuriesOrRestrictions,
    [param: Required, MaxLength(500)] string CurrentCondition,
    [param: Required, RegularExpression("weight_loss|muscle_building|general_fitness|strength|endurance")] string Goal,
    [param: Range(100, 120)] int AvailableWorkoutMinutes,
    [param: Required, MinLength(3), MaxLength(4)] int[] AvailableDays,
    [param: Required, MinLength(1), MaxLength(20)] string[] Equipment);
public sealed record FitnessCycleResponse(Guid Id, Guid SourceWorkflowId, DateOnly StartDate, DateOnly EndDate,
    FitnessCycleAnalysis Analysis, int CompletedWorkoutDays = 0, int PainReports = 0);
public sealed record AgentRequest(Guid WorkflowId, Guid RunId, ProfileInput Profile,
    List<ExerciseDto> Catalog, WorkoutPlan? PreviousPlan, List<AgentProgress> Progress, string Feedback,
    List<AgentProgress>? History = null);
public sealed record AgentResult(string Status, WorkoutPlan? Plan, List<string> Errors, string Analysis);
public sealed record EventInput(Guid RunId,
    [param: Required, MaxLength(50)] string Step,
    [param: Required, MaxLength(1000)] string Summary,
    [param: Range(0, 120000)] int DurationMs, JsonElement Snapshot);
