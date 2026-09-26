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
    [param: Required, MinLength(1), MaxLength(3)] int[] Days,
    [param: Range(20, 60)] int SessionMinutes,
    [param: Required, MaxLength(20)] string[] Equipment,
    bool ReviewRequired);

public sealed record StartRequest(Guid? PreviousWorkflowId);
public sealed record ReviewRequest(
    [param: Range(1, int.MaxValue)] int Version,
    [param: Required, RegularExpression("Approve|Reject|Revise")] string Decision,
    [param: Required, MinLength(3), MaxLength(500)] string Reason);
public sealed record ProgressInput(
    [param: Range(1, 7)] int Day, bool Completed,
    [param: Range(1, 10)] int Rpe, bool Pain, DateOnly PerformedOn);
public sealed record ExerciseDto(int Id, string Name, string Equipment, string MuscleGroup,
    string Instructions, bool BeginnerAllowed);
public sealed record Prescription(int ExerciseId, int Sets, int Repetitions, int RestSeconds);
public sealed record PlanDay(int Day, string Focus, int WarmupMinutes, int CooldownMinutes, List<Prescription> Exercises);
public sealed record WorkoutPlan(int Week, List<PlanDay> Days);
public sealed record AgentProgress(int Day, bool Completed, int Rpe, bool Pain);
public sealed record AgentRequest(Guid WorkflowId, Guid RunId, ProfileInput Profile,
    List<ExerciseDto> Catalog, WorkoutPlan? PreviousPlan, List<AgentProgress> Progress, string Feedback);
public sealed record AgentResult(string Status, WorkoutPlan? Plan, List<string> Errors, string Analysis);
public sealed record EventInput(Guid RunId,
    [param: Required, MaxLength(50)] string Step,
    [param: Required, MaxLength(1000)] string Summary,
    [param: Range(0, 120000)] int DurationMs, JsonElement Snapshot);
