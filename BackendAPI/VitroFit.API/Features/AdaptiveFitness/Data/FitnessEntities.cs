namespace VitroFit.API.Features.AdaptiveFitness;

public sealed class FitnessProfile
{
    public int UserId { get; set; }
    public int Age { get; set; }
    public double HeightCm { get; set; }
    public double WeightKg { get; set; }
    public string Goal { get; set; } = "general_fitness";
    public int[] Days { get; set; } = [];
    public int SessionMinutes { get; set; }
    public string[] Equipment { get; set; } = [];
    public bool ReviewRequired { get; set; }
    public DateTime UpdatedAt { get; set; } = DateTime.UtcNow;
    public ProfileInput ToInput() => new(Age, HeightCm, WeightKg, Goal, Days, SessionMinutes, Equipment, ReviewRequired);
}

public sealed class FitnessExercise
{
    public int Id { get; set; }
    public string Name { get; set; } = "";
    public string Equipment { get; set; } = "bodyweight";
    public string MuscleGroup { get; set; } = "";
    public string Instructions { get; set; } = "";
    public bool BeginnerAllowed { get; set; } = true;
    public ExerciseDto ToDto() => new(Id, Name, Equipment, MuscleGroup, Instructions, BeginnerAllowed);
}

// A plan is a versioned structured document; ownership, progress and events are relational.
public sealed class FitnessWorkflow
{
    public Guid Id { get; set; } = Guid.NewGuid();
    public int UserId { get; set; }
    public Guid RunId { get; set; } = Guid.NewGuid();
    public Guid? PreviousWorkflowId { get; set; }
    public string Status { get; set; } = "Running";
    public string CurrentStep { get; set; } = "coordinator";
    public string RequestJson { get; set; } = "{}";
    public string? PlanJson { get; set; }
    public string Summary { get; set; } = "";
    public string Feedback { get; set; } = "";
    public int Version { get; set; } = 1;
    public int RevisionCount { get; set; }
    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;
    public DateTime UpdatedAt { get; set; } = DateTime.UtcNow;
}

public sealed class FitnessEvent
{
    public long Id { get; set; }
    public Guid WorkflowId { get; set; }
    public string Step { get; set; } = "";
    public string Summary { get; set; } = "";
    public int DurationMs { get; set; }
    public string SnapshotJson { get; set; } = "{}";
    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;
}

public sealed class FitnessApproval
{
    public long Id { get; set; }
    public Guid WorkflowId { get; set; }
    public int ReviewerId { get; set; }
    public int Version { get; set; }
    public string Decision { get; set; } = "";
    public string Reason { get; set; } = "";
    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;
}

public sealed class FitnessProgress
{
    public long Id { get; set; }
    public Guid WorkflowId { get; set; }
    public int Day { get; set; }
    public bool Completed { get; set; }
    public int Rpe { get; set; }
    public bool Pain { get; set; }
    public DateOnly PerformedOn { get; set; }
    public DateTime UpdatedAt { get; set; } = DateTime.UtcNow;
}
