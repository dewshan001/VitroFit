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
        if (workflow.RevisionCount >= 2) return Conflict(new { message = "Retry limit reached. Start a new request." });
        workflow.RevisionCount++; workflow.Version++; workflow.RunId = Guid.NewGuid();
        workflow.Status = "Running"; workflow.UpdatedAt = DateTime.UtcNow;
        var request = FitnessJson.Read<AgentRequest>(workflow.RequestJson);
        workflow.RequestJson = FitnessJson.Write(request with { RunId = workflow.RunId });
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
        var isoDay = (int)input.PerformedOn.DayOfWeek == 0 ? 7 : (int)input.PerformedOn.DayOfWeek;
        var lastCompletedDate = await db.Progress
            .Where(p => p.WorkflowId == id && p.Day != input.Day && p.Completed)
            .MaxAsync(p => (DateOnly?)p.PerformedOn);
        if (workflow.PreviousWorkflowId is Guid previousWorkflowId)
        {
            var previousWeekLastDate = await db.Progress
                .Where(p => p.WorkflowId == previousWorkflowId && p.Completed)
                .MaxAsync(p => (DateOnly?)p.PerformedOn);
            if (previousWeekLastDate > lastCompletedDate) lastCompletedDate = previousWeekLastDate;
        }
        var earliestAllowedDate = lastCompletedDate?.AddDays(1) ?? DateOnly.FromDateTime(workflow.CreatedAt);
        if (input.PerformedOn < earliestAllowedDate || isoDay != input.Day)
            return BadRequest(new { message = $"Choose a {System.Globalization.CultureInfo.InvariantCulture.DateTimeFormat.GetDayName((DayOfWeek)(input.Day % 7))} after the last completed session ({lastCompletedDate?.ToString("yyyy-MM-dd") ?? "schedule start"}). Future dates are allowed." });
        var record = await db.Progress.SingleOrDefaultAsync(p => p.WorkflowId == id && p.Day == input.Day);
        if (record is null) { record = new() { WorkflowId = id, Day = input.Day }; db.Progress.Add(record); }
        record.Completed = input.Completed; record.Rpe = input.Rpe; record.Pain = input.Pain;
        record.PerformedOn = input.PerformedOn; record.UpdatedAt = DateTime.UtcNow;
        await db.SaveChangesAsync();
        return Ok(record);
    }
}
