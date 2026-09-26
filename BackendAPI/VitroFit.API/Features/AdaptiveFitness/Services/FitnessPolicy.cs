namespace VitroFit.API.Features.AdaptiveFitness;

// Recheck provider output at the public API boundary before making a schedule available.
public static class FitnessPolicy
{
    public static List<string> Validate(WorkoutPlan? plan, AgentRequest request)
    {
        List<string> errors = [];
        if (plan?.Days is null || plan.Days.Count is < 1 or > 3) return ["Missing or invalid plan days."];
        if (plan.Week is < 1 or > 4) errors.Add("The self-guided beginner program is limited to four schedules.");
        if (request.Profile.ReviewRequired || request.Progress.Any(p => p.Pain)) errors.Add("Instructor or qualified health professional review required.");
        if (plan.Week != (request.PreviousPlan?.Week ?? 0) + 1) errors.Add("Invalid week.");
        if (!plan.Days.Select(d => d.Day).Order().SequenceEqual(request.Profile.Days.Order())) errors.Add("Invalid weekdays.");
        foreach (var day in plan.Days)
        {
            if (day.Exercises is null || day.Exercises.Count is < 2 or > 5) { errors.Add("Invalid exercises."); continue; }
            if (day.Focus is not ("Chest and triceps" or "Arms and back" or "Legs")) errors.Add("Invalid workout focus.");
            if (day.WarmupMinutes is < 5 or > 10 || day.CooldownMinutes is < 5 or > 10) errors.Add("Invalid warmup or cooldown.");
            if (day.Exercises.Select(x => x.ExerciseId).Distinct().Count() != day.Exercises.Count) errors.Add("Duplicate exercise.");
            double minutes = day.WarmupMinutes + day.CooldownMinutes;
            foreach (var item in day.Exercises)
            {
                var exercise = request.Catalog.SingleOrDefault(e => e.Id == item.ExerciseId);
                if (exercise is null || !exercise.BeginnerAllowed) errors.Add("Unknown or unsupported exercise.");
                else if (exercise.Equipment != "bodyweight" && !request.Profile.Equipment.Contains(exercise.Equipment)) errors.Add("Unconfirmed equipment.");
                else if (exercise is not null && !MatchesFocus(day.Focus, exercise.MuscleGroup)) errors.Add("Exercise does not match this day's workout focus.");
                if (item.Sets is < 1 or > 3 || item.Repetitions is < 6 or > 15 || item.RestSeconds is < 45 or > 120) errors.Add("Invalid workload.");
                minutes += (item.Sets * (item.Repetitions * 4.0 + item.RestSeconds) + 60) / 60;
            }
            if (minutes > request.Profile.SessionMinutes) errors.Add("Session too long.");
        }
        if (errors.Count == 0 && request.PreviousPlan is { } previous)
        {
            var allCompleted = previous.Days.All(d => request.Progress.Any(p => p.Day == d.Day && p.Completed));
            var canProgress = request.Progress.Count > 0 && allCompleted && request.Progress.All(p => p.Rpe <= 6);
            if (Volume(plan) > Volume(previous) * (canProgress ? 1.10 : 1.0)) errors.Add("Progression limit exceeded.");
            if (request.Progress.Any(p => p.Rpe >= 8) && Volume(plan) >= Volume(previous)) errors.Add("Recovery requires reduced workload.");
        }
        return errors.Distinct().ToList();
    }
    private static bool MatchesFocus(string focus, string muscleGroup) => focus switch
    {
        "Chest and triceps" => muscleGroup is "chest" or "triceps" or "upper body",
        "Arms and back" => muscleGroup is "arms" or "back",
        "Legs" => muscleGroup == "legs",
        _ => false
    };
    private static int Volume(WorkoutPlan plan) => plan.Days.Sum(d => d.Exercises.Sum(e => e.Sets * e.Repetitions));
}
