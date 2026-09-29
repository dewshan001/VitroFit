namespace VitroFit.API.Features.AdaptiveFitness;

/// <summary>Summarizes completed workout blocks. A cycle is a reporting window, never a prebuilt calendar.</summary>
public static class FitnessCyclePlanner
{
    public static (FitnessCycleAnalysis Analysis, DateOnly Start, DateOnly End) Analyze(
        IReadOnlyList<FitnessWorkflow> workflows,
        IReadOnlyDictionary<Guid, List<FitnessProgress>> progressByWorkflow,
        DateOnly? startDate = null)
    {
        var blocks = workflows.Where(w => w.PlanJson is not null)
            .OrderBy(w => FitnessJson.Read<WorkoutPlan>(w.PlanJson!).Week).ToList();
        var blockAnalysis = blocks.Select(workflow =>
        {
            var plan = FitnessJson.Read<WorkoutPlan>(workflow.PlanJson!);
            var records = progressByWorkflow.GetValueOrDefault(workflow.Id) ?? [];
            return new FitnessWeekAnalysis(plan.Week, plan.Days.Count,
                records.Count(p => p.Completed), records.Count(p => !p.Completed && !p.Pain),
                records.Count(p => p.Pain), records.Count == 0 ? null : records.Average(p => p.Rpe),
                plan.Days.Sum(day => day.Exercises.Sum(item => item.Sets * item.Repetitions)));
        }).ToList();

        var allProgress = progressByWorkflow.Values.SelectMany(x => x).ToList();
        var painCount = allProgress.Count(p => p.Pain);
        double? averageRpe = allProgress.Count == 0 ? null : allProgress.Average(p => p.Rpe);
        var analysis = new FitnessCycleAnalysis(blockAnalysis.Sum(w => w.PlannedSessions),
            blockAnalysis.Sum(w => w.CompletedSessions), blockAnalysis.Sum(w => w.SkippedSessions),
            allProgress.Count(p => p.Pain || !p.Completed), painCount, averageRpe,
            painCount > 0 || averageRpe >= 8, blockAnalysis);
        var lastDate = allProgress.Count == 0 ? DateOnly.FromDateTime(DateTime.UtcNow) : allProgress.Max(p => p.PerformedOn);
        var start = startDate ?? (lastDate.AddDays(1) > DateOnly.FromDateTime(DateTime.UtcNow)
            ? lastDate.AddDays(1) : DateOnly.FromDateTime(DateTime.UtcNow));
        return (analysis, start, start.AddMonths(3).AddDays(-1));
    }
}
