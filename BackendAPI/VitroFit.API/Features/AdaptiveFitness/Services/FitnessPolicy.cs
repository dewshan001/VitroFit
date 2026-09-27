namespace VitroFit.API.Features.AdaptiveFitness;

// Recheck provider output at the public API boundary before making a schedule available.
public static class FitnessPolicy
{
    public static List<string> Validate(WorkoutPlan? plan, AgentRequest request)
    {
        List<string> errors = [];
        if (plan?.Days is null || plan.Days.Count is < 1 or > 4) return ["Missing or invalid plan days."];
        if (plan.Week is < 1 or > 1000) errors.Add("The workout block limit was reached.");
        if (request.Profile.ReviewRequired) errors.Add("Instructor or qualified health professional review required.");
        var legacy = plan.Week <= 4;
        if (plan.Week != (request.PreviousPlan?.Week ?? 0) + 1) errors.Add("Invalid workout block.");
        var targetCount = RecommendedWorkoutCount(request);
        var expectedDays = legacy ? request.Profile.Days.Order() : Enumerable.Range(1, targetCount).Order();
        if (!plan.Days.Select(d => d.Day).Order().SequenceEqual(expectedDays)) errors.Add("Every generated block must contain only sequential workout days.");
        if (!legacy && plan.Days.Count != targetCount) errors.Add("Generate exactly the selected 3 or 4 workout days.");
        foreach (var day in plan.Days)
        {
            if (day.Exercises is null || (legacy && day.Exercises.Count is < 2 or > 10) || (!legacy && day.Exercises.Count is < 6 or > 14)) { errors.Add(!legacy ? "Each two-hour workout day must contain between 6 and 14 exercises." : "Invalid exercises."); continue; }
            if (day.Focus is not ("Chest and triceps" or "Arms and back" or "Legs" or "Shoulders, back and core" or "Legs and biceps")) errors.Add("Invalid workout focus.");
            if (day.WarmupMinutes is < 5 or > 10 || day.CooldownMinutes is < 5 or > 10) errors.Add("Invalid warmup or cooldown.");
            if (!legacy && (day.DurationMinutes is null or < 100 or > 120)) errors.Add("Each new workout day must be approximately two hours.");
            if (day.Exercises.Select(x => x.ExerciseId).Distinct().Count() != day.Exercises.Count) errors.Add("Duplicate exercise.");
            double minutes = day.WarmupMinutes + day.CooldownMinutes;
            foreach (var item in day.Exercises)
            {
                var exercise = request.Catalog.SingleOrDefault(e => e.Id == item.ExerciseId);
                if (exercise is null || !exercise.BeginnerAllowed) errors.Add("Unknown or unsupported exercise.");
                else if (exercise.Equipment != "bodyweight" && exercise.Equipment != "gym" && !request.Profile.Equipment.Contains(exercise.Equipment)) errors.Add("Unconfirmed equipment.");
                else if (exercise is not null && !MatchesFocus(day.Focus, exercise.MuscleGroup, legacy)) errors.Add("Exercise does not match this day's workout focus.");
                if (item.Sets is < 1 or > 6 || item.Repetitions is < 6 or > 30 || item.RestSeconds is < 30 or > 180) errors.Add("Invalid workload.");
                if (!legacy && (request.History ?? request.Progress).Any(p => p.Pain &&
                    (p.AffectedAreas?.Contains("full body", StringComparer.OrdinalIgnoreCase) == true ||
                     p.AffectedAreas?.Contains(exercise?.MuscleGroup ?? "", StringComparer.OrdinalIgnoreCase) == true)))
                    errors.Add("Workout includes an exercise for a muscle group reported as painful.");
                minutes += (item.Sets * (item.Repetitions * 4.0 + item.RestSeconds) + 60) / 60;
            }
            if (legacy && minutes > request.Profile.SessionMinutes) errors.Add("Session too long.");
        }
        if (errors.Count == 0 && request.PreviousPlan is { } previous)
        {
            var allCompleted = previous.Days.All(d => request.Progress.Any(p => p.Day == d.Day && p.Completed));
            var canProgress = request.Progress.Count > 0 && allCompleted && request.Progress.All(p => p.Rpe <= 6 && !p.Pain);
            var factor = canProgress ? 1.10 : 1.0;
            if (previous.Week > 4 && plan.Week > 4)
            {
                var currentSessionVolume = Volume(plan) / Math.Max(1, plan.Days.Count);
                var previousSessionVolume = Volume(previous) / Math.Max(1, previous.Days.Count);
                if (currentSessionVolume > previousSessionVolume * factor) errors.Add("Progression limit exceeded.");
            }
        }
        return errors.Distinct().ToList();
    }
    private static bool MatchesFocus(string focus, string muscleGroup, bool legacy = true) => legacy ? (focus switch
    {
        "Chest and triceps" => muscleGroup is "chest" or "triceps" or "upper body",
        "Arms and back" => muscleGroup is "arms" or "back",
        "Legs" => muscleGroup == "legs",
        _ => false
    }) : (focus switch
    {
        "Chest and triceps" => muscleGroup is "chest" or "triceps" or "upper body" or "core" or "arms" or "full body",
        "Arms and back" or "Shoulders, back and core" => muscleGroup is "arms" or "back" or "upper body" or "core" or "chest" or "full body",
        "Legs" or "Legs and biceps" => muscleGroup is "legs" or "core" or "full body" or "arms",
        _ => true
    });
    private static int Volume(WorkoutPlan plan) => plan.Days.Sum(d => d.Exercises.Sum(e => e.Sets * e.Repetitions));

    private static int RecommendedWorkoutCount(AgentRequest request)
    {
        if (request.Profile.Days.Length < 4 || request.Progress.Any(p => p.Pain)) return 3;
        var recent = request.Progress.TakeLast(4).ToList();
        var goodPerformance = recent.Count > 0 && recent.All(p => p.Completed && p.Rpe <= 6);
        var goalAllowsFour = request.Profile.Goal is "strength" or "muscle_building" or "endurance";
        return goodPerformance && goalAllowsFour && request.Profile.SessionMinutes >= 100 ? 4 : 3;
    }
}
