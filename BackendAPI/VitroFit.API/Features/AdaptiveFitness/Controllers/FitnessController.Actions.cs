using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;

namespace VitroFit.API.Features.AdaptiveFitness;

public sealed partial class FitnessController
{
    [HttpPost("workflows/{id:guid}/retry")]
    public async Task<IActionResult> Retry(Guid id)
    {
        var workflow = await db.Workflows.SingleOrDefaultAsync(w => w.Id == id && w.UserId == UserId);
        if (workflow is null) return NotFound();
        var stale = workflow.Status == "Running" && workflow.UpdatedAt < DateTime.UtcNow.AddMinutes(-3);
        if (workflow.Status != "Failed" && !stale) return Conflict(new { message = "Only failed or interrupted runs can retry." });
        if (workflow.RevisionCount >= 10) return Conflict(new { message = "Retry limit reached. Start a new request." });
        workflow.RevisionCount++; workflow.Version++; workflow.RunId = Guid.NewGuid();
        workflow.Status = "Running"; workflow.UpdatedAt = DateTime.UtcNow;
        var exercises = (await db.Exercises.OrderBy(e => e.Id).ToListAsync()).Select(e => e.ToDto()).ToList();
        var request = FitnessJson.Read<AgentRequest>(workflow.RequestJson);
        workflow.RequestJson = FitnessJson.Write(request with { RunId = workflow.RunId, Catalog = exercises });
        await db.SaveChangesAsync();
        await workflows.Run(workflow);
        return Ok(Details(workflow));
    }

    [HttpPost("workflows/{id:guid}/regenerate")]
    public async Task<IActionResult> Regenerate(Guid id)
    {
        var workflow = await db.Workflows.SingleOrDefaultAsync(w => w.Id == id && w.UserId == UserId);
        if (workflow is null) return NotFound();
        if (workflow.Status == "Running") return Conflict(new { message = "Schedule generation is already in progress." });
        if (workflow.RevisionCount >= 10) return Conflict(new { message = "Regeneration limit reached for this schedule." });
        if (await db.Workflows.AnyAsync(w => w.UserId == UserId && w.PreviousWorkflowId == workflow.Id))
            return Conflict(new { message = "You can only regenerate your latest schedule. Follow-up schedules already depend on this one." });

        workflow.RevisionCount++; workflow.Version++; workflow.RunId = Guid.NewGuid();
        workflow.Status = "Running"; workflow.PlanJson = null; workflow.UpdatedAt = DateTime.UtcNow;
        var profile = await db.Profiles.FindAsync(UserId);
        var exercises = (await db.Exercises.ToListAsync()).Select(e => e.ToDto()).ToList();
        var request = FitnessJson.Read<AgentRequest>(workflow.RequestJson);
        var updatedRequest = request with
        {
            RunId = workflow.RunId,
            Profile = profile is not null ? profile.ToInput() : request.Profile,
            Catalog = exercises.Count > 0 ? exercises : request.Catalog
        };
        workflow.RequestJson = FitnessJson.Write(updatedRequest);
        var progress = await db.Progress.Where(p => p.WorkflowId == id).ToListAsync();
        if (progress.Count > 0) db.Progress.RemoveRange(progress);
        await db.SaveChangesAsync();
        await workflows.Run(workflow);
        return Ok(Details(workflow));
    }

    [HttpPut("workflows/{id:guid}/progress")]
    public async Task<IActionResult> SaveProgress(Guid id, ProgressInput input)
    {
        var workflow = await db.Workflows.SingleOrDefaultAsync(w => w.Id == id && w.UserId == UserId && w.Status == "Ready");
        if (workflow?.PlanJson is null) return NotFound();
        var plan = FitnessJson.Read<WorkoutPlan>(workflow.PlanJson);
        if (!plan.Days.Any(d => d.Day == input.Day)) return BadRequest(new { message = "Day is not part of this plan." });
        var validAreas = new HashSet<string>(["chest", "triceps", "arms", "back", "legs", "shoulders", "core", "full body"], StringComparer.OrdinalIgnoreCase);
        var areas = (input.AffectedAreas ?? []).Select(x => x.Trim().ToLowerInvariant()).Distinct().ToArray();
        if (input.Pain && (areas.Length == 0 || areas.Any(area => !validAreas.Contains(area))))
            return BadRequest(new { message = "Choose the body area or muscle group affected by the pain." });
        if (!input.Pain && areas.Length > 0)
            return BadRequest(new { message = "Affected areas can only be saved when pain is reported." });
        var isoDay = (int)input.PerformedOn.DayOfWeek == 0 ? 7 : (int)input.PerformedOn.DayOfWeek;
        var lastCompletedDate = await db.Progress
            .Where(p => p.WorkflowId == id && p.Day != input.Day)
            .MaxAsync(p => (DateOnly?)p.PerformedOn);
        var legacyWeek = plan.Week <= 4;
        if (workflow.PreviousWorkflowId is Guid previousWorkflowId)
        {
            var previousWeekLastDate = await db.Progress
                .Where(p => p.WorkflowId == previousWorkflowId)
                .MaxAsync(p => (DateOnly?)p.PerformedOn);
            if (previousWeekLastDate > lastCompletedDate) lastCompletedDate = previousWeekLastDate;
        }
        var earliestAllowedDate = lastCompletedDate?.AddDays(1) ?? DateOnly.FromDateTime(workflow.CreatedAt);
        if (input.PerformedOn < earliestAllowedDate || (legacyWeek && isoDay != input.Day))
            return BadRequest(new { message = legacyWeek
                ? $"Choose a {System.Globalization.CultureInfo.InvariantCulture.DateTimeFormat.GetDayName((DayOfWeek)(input.Day % 7))} after the last completed session ({lastCompletedDate?.ToString("yyyy-MM-dd") ?? "schedule start"}). Future dates are allowed."
                : $"Choose a date after the last recorded workout ({lastCompletedDate?.ToString("yyyy-MM-dd") ?? "schedule start"})." });
        var record = await db.Progress.SingleOrDefaultAsync(p => p.WorkflowId == id && p.Day == input.Day);
        if (record is null) { record = new() { WorkflowId = id, Day = input.Day }; db.Progress.Add(record); }
        record.Completed = input.Completed; record.Rpe = input.Rpe; record.Pain = input.Pain;
        record.AffectedAreas = areas; record.PerformedOn = input.PerformedOn; record.UpdatedAt = DateTime.UtcNow;
        await db.SaveChangesAsync();
        return Ok(record);
    }
}
