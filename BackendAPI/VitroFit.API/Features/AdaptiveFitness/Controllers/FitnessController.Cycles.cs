using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;

namespace VitroFit.API.Features.AdaptiveFitness;

public sealed partial class FitnessController
{
    [HttpGet("workflows/{id:guid}/next-cycle")]
    public async Task<IActionResult> GetNextCycle(Guid id)
    {
        if (!await CycleStorageAvailable()) return CycleMigrationRequired();
        var chain = await Ancestors(id);
        if (chain.Count == 0) return NotFound();
        var cycle = await FindCycle(chain);
        if (cycle is null) return Ok(null);
        var progress = await db.Progress.Where(p => chain.Select(w => w.Id).Contains(p.WorkflowId) &&
            p.PerformedOn >= cycle.StartDate && p.PerformedOn <= cycle.EndDate).ToListAsync();
        var periodWorkflows = chain.Where(workflow => progress.Any(p => p.WorkflowId == workflow.Id)).ToList();
        var delta = FitnessCyclePlanner.Analyze(periodWorkflows, progress.GroupBy(p => p.WorkflowId)
            .ToDictionary(g => g.Key, g => g.ToList()), cycle.StartDate).Analysis;
        var analysis = CombineAnalysis(FitnessJson.Read<FitnessCycleAnalysis>(cycle.AnalysisJson), delta);
        return Ok(CycleDetails(cycle, analysis));
    }

    [HttpPost("workflows/{id:guid}/next-cycle")]
    public async Task<IActionResult> CreateNextCycle(Guid id, [FromBody] CycleReviewInput review)
    {
        if (!await CycleStorageAvailable()) return CycleMigrationRequired();
        if (!ModelState.IsValid) return ValidationProblem(ModelState);
        var chain = await Ancestors(id);
        var source = chain.FirstOrDefault(w => w.Id == id && w.Status == "Ready");
        if (source?.PlanJson is null) return NotFound();
        var sourcePlan = FitnessJson.Read<WorkoutPlan>(source.PlanJson);
        var existing = await db.Cycles.SingleOrDefaultAsync(c => c.UserId == UserId && c.SourceWorkflowId == id);
        if (existing is not null && existing.EndDate >= DateOnly.FromDateTime(DateTime.UtcNow)) return await GetNextCycle(id);

        var previousCycle = existing ?? await FindCycle(chain.Skip(1).ToList()) ?? await FindCycle(chain)
            ?? await db.Cycles.Where(c => c.UserId == UserId).OrderByDescending(c => c.CreatedAt).FirstOrDefaultAsync();

        var isFirstCycle = previousCycle is null && sourcePlan.Week == 4;

        if (isFirstCycle)
        {
            chain = await LoadBeginnerChain(source);
            if (chain.Count != 4) return Conflict(new { message = "The complete four-week beginner history is unavailable." });
        }
        else
        {
            // For subsequent 3-month cycles:
            // Do NOT require beginner schedules 1..4. Use the previous 3-month cycle.
            var cycleBlocks = chain.Count(w => w.PlanJson is not null && FitnessJson.Read<WorkoutPlan>(w.PlanJson).Week > 4);
            var completedByBlocks = cycleBlocks >= 12;
            var completedByDate = previousCycle is not null && previousCycle.EndDate < DateOnly.FromDateTime(DateTime.UtcNow);

            if (previousCycle is not null && !completedByBlocks && !completedByDate && existing is null && sourcePlan.Week <= 4)
            {
                return Conflict(new { message = $"This training cycle runs through {previousCycle.EndDate:yyyy-MM-dd}. Continue generating workout blocks until the cycle ends." });
            }
        }

        var progressByWorkflow = await ReadProgress(chain);
        if (chain.Any(workflow => workflow.PlanJson is not null &&
            !HasAllRecords(workflow, progressByWorkflow.GetValueOrDefault(workflow.Id) ?? [])))
            return Conflict(new { message = "Record every workout in the completed period before starting another three-month cycle." });

        if (previousCycle is not null && !isFirstCycle)
        {
            // Focus analysis on the previous 3-month cycle blocks (weeks > 4)
            var cycleWorkflows = chain.Where(w => w.PlanJson is not null && FitnessJson.Read<WorkoutPlan>(w.PlanJson).Week > 4).ToList();
            if (cycleWorkflows.Count > 0)
            {
                chain = cycleWorkflows.Take(12).ToList();
            }
        }

        var profile = await db.Profiles.FindAsync(UserId);
        if (profile is null) return BadRequest(new { message = "Save your fitness profile first." });
        if (review.AvailableWorkoutMinutes < 100 || review.AvailableDays.Any(d => d is < 1 or > 7) ||
            review.AvailableDays.Distinct().Count() != review.AvailableDays.Length ||
            review.Equipment.Any(e => e is not ("bodyweight" or "dumbbells" or "resistance_band" or "gym")))
            return BadRequest(new { message = "Choose 100–120 minutes, 3 or 4 unique available days, and supported equipment before starting this training cycle." });
        profile.Goal = review.Goal;
        profile.SessionMinutes = review.AvailableWorkoutMinutes;
        profile.Days = review.AvailableDays;
        profile.Equipment = review.Equipment.Distinct().ToArray();
        profile.UpdatedAt = DateTime.UtcNow;

        var (analysis, start, end) = FitnessCyclePlanner.Analyze(chain, progressByWorkflow);
        analysis = analysis with { Review = review };
        var cycle = new FitnessCycle { UserId = UserId, SourceWorkflowId = id,
            StartDate = start, EndDate = end, AnalysisJson = FitnessJson.Write(analysis), ScheduleJson = "[]" };
        db.Cycles.Add(cycle);
        await db.SaveChangesAsync();
        return Ok(CycleDetails(cycle, analysis));
    }

    private async Task<List<FitnessWorkflow>> Ancestors(Guid id)
    {
        var chain = new List<FitnessWorkflow>();
        var cursor = await Visible.SingleOrDefaultAsync(w => w.Id == id);
        while (cursor is not null && chain.Count < 1000)
        {
            chain.Add(cursor);
            cursor = cursor.PreviousWorkflowId is Guid previousId
                ? await Visible.SingleOrDefaultAsync(w => w.Id == previousId) : null;
        }
        return chain;
    }

    private async Task<FitnessCycle?> FindCycle(IReadOnlyList<FitnessWorkflow> newestFirst)
    {
        if (newestFirst.Count == 0) return null;
        var ids = newestFirst.Select(w => w.Id).ToArray();
        return await db.Cycles.AsNoTracking().Where(c => c.UserId == UserId && ids.Contains(c.SourceWorkflowId))
            .OrderByDescending(c => c.CreatedAt).FirstOrDefaultAsync();
    }

    private async Task<List<FitnessWorkflow>> LoadBeginnerChain(FitnessWorkflow latest)
    {
        var result = new List<FitnessWorkflow>();
        var cursor = latest;
        for (var week = 4; week >= 1; week--)
        {
            if (cursor.PlanJson is null || FitnessJson.Read<WorkoutPlan>(cursor.PlanJson).Week != week) return [];
            result.Add(cursor);
            if (week > 1)
            {
                if (cursor.PreviousWorkflowId is not Guid previousId) return [];
                cursor = await Visible.SingleOrDefaultAsync(w => w.Id == previousId && w.Status == "Ready");
                if (cursor is null) return [];
            }
        }
        result.Reverse();
        return result;
    }

    private async Task<Dictionary<Guid, List<FitnessProgress>>> ReadProgress(IReadOnlyList<FitnessWorkflow> chain)
    {
        var ids = chain.Select(w => w.Id).ToArray();
        var records = await db.Progress.Where(p => ids.Contains(p.WorkflowId)).ToListAsync();
        return records.GroupBy(p => p.WorkflowId).ToDictionary(g => g.Key, g => g.ToList());
    }

    private static bool HasAllRecords(FitnessWorkflow workflow, List<FitnessProgress> records)
    {
        if (workflow.PlanJson is null) return false;
        var days = FitnessJson.Read<WorkoutPlan>(workflow.PlanJson).Days;
        return days.All(day => records.Any(p => p.Day == day.Day));
    }

    private static FitnessCycleAnalysis CombineAnalysis(FitnessCycleAnalysis baseline, FitnessCycleAnalysis period)
    {
        var weeks = baseline.Weeks.Concat(period.Weeks).GroupBy(w => w.Week)
            .Select(g => g.Last()).OrderBy(w => w.Week).ToList();
        var effortSamples = weeks.Where(w => w.AverageRpe.HasValue && w.PlannedSessions > 0).ToList();
        double? averageRpe = effortSamples.Count == 0 ? null :
            effortSamples.Sum(w => w.AverageRpe!.Value * w.PlannedSessions) / effortSamples.Sum(w => w.PlannedSessions);
        return new(baseline.PlannedSessions + period.PlannedSessions,
            baseline.CompletedSessions + period.CompletedSessions,
            baseline.SkippedSessions + period.SkippedSessions,
            baseline.ModifiedSessions + period.ModifiedSessions,
            baseline.PainReports + period.PainReports,
            averageRpe,
            baseline.RecoveryAdjustment || period.RecoveryAdjustment,
            weeks,
            baseline.Review);
    }

    private async Task<bool> CycleStorageAvailable()
    {
        var pending = await db.Database.GetPendingMigrationsAsync();
        return !pending.Contains("20260927123000_AddAdaptiveFitnessCycles") &&
               !pending.Contains("20260927180000_AddWorkoutPainAreas");
    }

    private static IActionResult CycleMigrationRequired() => new ObjectResult(new
    {
        message = "Adaptive fitness database updates are pending. Stop the API, run `dotnet ef database update --context FitnessDbContext` from BackendAPI/VitroFit.API, then restart it."
    }) { StatusCode = StatusCodes.Status503ServiceUnavailable };

    private static FitnessCycleResponse CycleDetails(FitnessCycle cycle, FitnessCycleAnalysis? analysis = null)
    {
        analysis ??= FitnessJson.Read<FitnessCycleAnalysis>(cycle.AnalysisJson);
        return new FitnessCycleResponse(cycle.Id, cycle.SourceWorkflowId, cycle.StartDate, cycle.EndDate,
            analysis, analysis.CompletedSessions, analysis.PainReports);
    }
}
