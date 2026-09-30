using System.Security.Claims;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using VitroFit.API.Data;

namespace VitroFit.API.Features.AdaptiveFitness;

[ApiController, Route("api/fitness"), Authorize]
[TypeFilter(typeof(FitnessExceptionFilter))]
public sealed partial class FitnessController(FitnessDbContext db, AppDbContext appDb, FitnessWorkflowService workflows) : ControllerBase
{
    private int UserId => int.Parse(User.FindFirstValue(ClaimTypes.NameIdentifier) ?? User.FindFirstValue("sub") ?? "0");
    private IQueryable<FitnessWorkflow> Visible => db.Workflows.Where(w => w.UserId == UserId);

    [HttpGet("profile")]
    public async Task<IActionResult> Profile()
    {
        var profile = await db.Profiles.FindAsync(UserId);
        return profile is null ? NotFound(new { message = "Create your fitness profile first." }) : Ok(profile.ToInput());
    }

    [HttpPut("profile")]
    public async Task<IActionResult> SaveProfile(ProfileInput input)
    {
        if (!await appDb.Users.AnyAsync(user => user.Id == UserId)) return Unauthorized();
        if (input.Days.Any(d => d is < 1 or > 7) || input.Days.Distinct().Count() != input.Days.Length)
            return BadRequest(new { message = "Select unique weekdays from 1 to 7." });
        if (input.Equipment.Any(e => e is not ("bodyweight" or "dumbbells" or "resistance_band" or "gym")))
            return BadRequest(new { message = "Unsupported equipment." });
        var profile = await db.Profiles.FindAsync(UserId);
        if (profile is null) { profile = new() { UserId = UserId }; db.Profiles.Add(profile); }
        profile.Age = input.Age; profile.HeightCm = input.HeightCm; profile.WeightKg = input.WeightKg;
        profile.Goal = input.Goal; profile.Days = input.Days; profile.SessionMinutes = input.SessionMinutes;
        profile.Equipment = input.Equipment.Distinct().ToArray(); profile.ReviewRequired = input.ReviewRequired;
        profile.UpdatedAt = DateTime.UtcNow;
        await db.SaveChangesAsync();
        return Ok(profile.ToInput());
    }

    [HttpDelete("profile")]
    public async Task<IActionResult> DeleteProfile()
    {
        await using var transaction = await db.Database.BeginTransactionAsync();
        var workflows = await db.Workflows.Where(w => w.UserId == UserId).ToListAsync();
        db.Workflows.RemoveRange(workflows);
        var profile = await db.Profiles.FindAsync(UserId);
        if (profile is not null) db.Profiles.Remove(profile);
        await db.SaveChangesAsync();
        await transaction.CommitAsync();
        return NoContent();
    }

    [HttpGet("exercises")]
    public async Task<IActionResult> Exercises() => Ok((await db.Exercises.OrderBy(e => e.Id).ToListAsync()).Select(e => e.ToDto()));

    [HttpPost("workflows")]
    public async Task<IActionResult> Start(StartRequest input)
    {
        var profile = await db.Profiles.FindAsync(UserId);
        if (profile is null) return BadRequest(new { message = "Save your profile first." });
        FitnessWorkflow? previous = null;
        List<AgentProgress> progress = [];
        List<AgentProgress> history = [];
        var feedback = "";
        if (input.PreviousWorkflowId.HasValue)
        {
            previous = await db.Workflows.SingleOrDefaultAsync(w => w.Id == input.PreviousWorkflowId && w.UserId == UserId && w.Status == "Ready");
            if (previous?.PlanJson is null) return BadRequest(new { message = "Continue from your latest ready schedule." });
            var previousPlan = FitnessJson.Read<WorkoutPlan>(previous.PlanJson);
            var priorChain = await Ancestors(previous.Id);
            var cycle = await FindCycle(priorChain) ?? await db.Cycles.Where(c => c.UserId == UserId).OrderByDescending(c => c.CreatedAt).FirstOrDefaultAsync();

            if (previousPlan.Week == 4 && cycle is null)
            {
                var progressMap = (await db.Progress.Where(p => priorChain.Select(w => w.Id).Contains(p.WorkflowId)).ToListAsync())
                    .GroupBy(p => p.WorkflowId).ToDictionary(g => g.Key, g => g.ToList());
                var (initAnalysis, start, end) = FitnessCyclePlanner.Analyze(priorChain, progressMap);
                cycle = new FitnessCycle
                {
                    UserId = UserId,
                    SourceWorkflowId = previous.Id,
                    StartDate = start,
                    EndDate = end,
                    AnalysisJson = FitnessJson.Write(initAnalysis),
                    ScheduleJson = "[]"
                };
                db.Cycles.Add(cycle);
                await db.SaveChangesAsync();
            }

            if (previousPlan.Week > 4 && cycle is not null)
            {
                var cycleBlocks = priorChain.Count(w => w.PlanJson is not null && FitnessJson.Read<WorkoutPlan>(w.PlanJson).Week > 4);
                var cycleCompleted = (cycleBlocks > 0 && cycleBlocks % 12 == 0) || cycle.EndDate < DateOnly.FromDateTime(DateTime.UtcNow);
                if (cycleCompleted && cycle.SourceWorkflowId != previous.Id)
                    return Conflict(new { message = "Your three-month cycle is complete. Review your profile and create the next cycle before requesting another workout block." });
            }

            if (cycle is not null)
            {
                var cycleAnalysis = FitnessJson.Read<FitnessCycleAnalysis>(cycle.AnalysisJson);
                var cycleReview = cycleAnalysis.Review;
                var reviewSummary = cycleReview is null ? "" : $"Goals: {cycleReview.Goal}. Condition: {cycleReview.CurrentCondition}. Pain: {cycleReview.PainOrDiscomfort}. Restrictions: {cycleReview.InjuriesOrRestrictions}. ";
                var perfSummary = $"Previous 3-month cycle: {cycleAnalysis.CompletedSessions} completed sessions, {cycleAnalysis.PainReports} pain reports, avg RPE {cycleAnalysis.AverageRpe?.ToString("F1") ?? "N/A"}. ";
                var fullFeedback = reviewSummary + perfSummary;
                feedback = fullFeedback[..Math.Min(fullFeedback.Length, 1500)];
            }
            if (previousPlan.Week > 4 && profile.SessionMinutes < 100)
                return Conflict(new { message = "Update your available workout time to about two hours before generating this block." });
            if (await db.Workflows.AnyAsync(w => w.UserId == UserId && w.PreviousWorkflowId == previous.Id))
                return Conflict(new { message = "Continue from your latest schedule; this schedule already has a follow-up." });
            progress = await db.Progress.Where(p => p.WorkflowId == previous.Id).OrderBy(p => p.Day)
                .Select(p => new AgentProgress(p.Day, p.Completed, p.Rpe, p.Pain, p.AffectedAreas, previousPlan.Week)).ToListAsync();
            if (progress.Count != previousPlan.Days.Count || previousPlan.Days.Any(day => progress.All(p => p.Day != day.Day)))
                return BadRequest(new { message = "Record progress for every day in this schedule before requesting the next one." });
            if (progress.Any(p => !p.Completed && !p.Pain))
                return BadRequest(new { message = "Complete every scheduled day before requesting the next week." });
            var ids = priorChain.Select(w => w.Id).ToArray();
            var storedHistory = await db.Progress.Where(p => ids.Contains(p.WorkflowId)).OrderBy(p => p.PerformedOn).ToListAsync();
            history = storedHistory.Select(p => new AgentProgress(p.Day, p.Completed, p.Rpe, p.Pain,
                p.AffectedAreas, priorChain.First(w => w.Id == p.WorkflowId).PlanJson is { } planJson
                    ? FitnessJson.Read<WorkoutPlan>(planJson).Week : 0)).ToList();
        }
        else
        {
            var roots = await db.Workflows.Where(w => w.UserId == UserId && w.PreviousWorkflowId == null).ToListAsync();
            var currentProfile = FitnessJson.Write(profile.ToInput());
            var canRestartAfterSafetyPause = roots.All(w => w.Status == "ReviewRequired" &&
                FitnessJson.Write(FitnessJson.Read<AgentRequest>(w.RequestJson).Profile) != currentProfile);
            var canStartFreshAfterFailure = roots.Count < 3 && roots.All(w => w.Status == "Failed");
            if (roots.Count > 0 && !canRestartAfterSafetyPause && !canStartFreshAfterFailure)
                return Conflict(new { message = "Your beginner program has already started. Continue from your current schedule; after schedule four, meet an instructor." });
        }
        var workflow = new FitnessWorkflow { UserId = UserId, PreviousWorkflowId = previous?.Id };
        var request = new AgentRequest(workflow.Id, workflow.RunId, profile.ToInput(),
            (await db.Exercises.ToListAsync()).Select(e => e.ToDto()).ToList(),
            previous?.PlanJson is { } json ? FitnessJson.Read<WorkoutPlan>(json) : null, progress, feedback, history);
        workflow.RequestJson = FitnessJson.Write(request);
        db.Workflows.Add(workflow);
        await db.SaveChangesAsync();
        await workflows.Run(workflow);
        return Ok(Details(workflow));
    }

    [HttpGet("workflows")]
    public async Task<IActionResult> List([FromQuery] string? status, [FromQuery] int page = 1)
    {
        if (page is < 1 or > 10000) return BadRequest(new { message = "Invalid page." });
        var query = Visible.AsNoTracking();
        if (!string.IsNullOrEmpty(status)) query = query.Where(w => w.Status == status);
        var total = await query.CountAsync();
        var items = await query.OrderByDescending(w => w.CreatedAt).Skip((page - 1) * 20).Take(20)
            .Select(w => new { w.Id, w.UserId, w.Status, w.Version, w.CreatedAt, w.Summary }).ToListAsync();
        return Ok(new { items, total, page, pageSize = 20 });
    }

    [HttpGet("workflows/{id:guid}")]
    public async Task<IActionResult> Get(Guid id)
    {
        var workflow = await Visible.AsNoTracking().SingleOrDefaultAsync(w => w.Id == id);
        return workflow is null ? NotFound() : Ok(Details(workflow));
    }

    [HttpPost("workflows/{id:guid}/timetable")]
    public async Task<IActionResult> GenerateTimetable(Guid id, [FromServices] TimeManagementAgentClient timeAgent, CancellationToken cancellation)
    {
        var workflow = await db.Workflows.SingleOrDefaultAsync(w => w.Id == id && w.UserId == UserId && w.Status == "Ready");
        if (workflow?.PlanJson is null) return NotFound(new { message = "Workout plan not found or not ready." });
        var profile = await db.Profiles.FindAsync(UserId);
        if (profile is null) return BadRequest(new { message = "Profile not found." });

        var plan = FitnessJson.Read<WorkoutPlan>(workflow.PlanJson);
        var request = new TimeManagementRequest(workflow.Id, Guid.NewGuid(), plan, profile.ToInput(), "");
        
        try
        {
            var result = await timeAgent.GenerateTimetable(request, cancellation);
            if (result.Status == "Failed")
            {
                return BadRequest(new { message = "Agent failed to generate timetable", errors = result.Errors });
            }

            // Delete old timetable slots for the user
            var existingSlots = await appDb.TimetableSlots.Where(t => t.UserId == UserId).ToListAsync(cancellation);
            appDb.TimetableSlots.RemoveRange(existingSlots);

            if (result.Timetable.HasValue && result.Timetable.Value.TryGetProperty("slots", out var slotsElement))
            {
                foreach(var slotElement in slotsElement.EnumerateArray())
                {
                    var focus = slotElement.GetProperty("focus").GetString() ?? "Adaptive Workout";
                    var workout = await appDb.Workouts.FirstOrDefaultAsync(w => w.Name == focus, cancellation);
                    if (workout == null)
                    {
                        workout = new VitroFit.API.Entities.Workout { Name = focus, Category = "Adaptive" };
                        appDb.Workouts.Add(workout);
                        await appDb.SaveChangesAsync(cancellation);
                    }

                    var dayInt = slotElement.GetProperty("day").GetInt32();
                    var dayOfWeek = dayInt == 7 ? DayOfWeek.Sunday : (DayOfWeek)dayInt;
                    var startTime = slotElement.GetProperty("startTime").GetString() ?? "00:00";
                    var endTime = slotElement.GetProperty("endTime").GetString() ?? "00:00";

                    appDb.TimetableSlots.Add(new VitroFit.API.Entities.TimetableSlot
                    {
                        UserId = UserId,
                        WorkoutId = workout.Id,
                        Day = dayOfWeek,
                        StartTime = TimeSpan.Parse(startTime),
                        EndTime = TimeSpan.Parse(endTime),
                        Title = focus
                    });
                }
            }
            await appDb.SaveChangesAsync(cancellation);

            return Ok(result);
        }
        catch (Exception ex)
        {
            return StatusCode(503, new { message = "Timetable generation failed.", details = ex.Message });
        }
    }

    [HttpGet("workflows/{id:guid}/history")]
    public async Task<IActionResult> History(Guid id)
    {
        if (!await Visible.AnyAsync(w => w.Id == id)) return NotFound();
        var events = await db.Events.Where(e => e.WorkflowId == id).OrderBy(e => e.Id).ToListAsync();
        return Ok(new {
            events = events.Select(e => new {
                e.Id, e.Step, e.Summary, e.DurationMs, e.CreatedAt,
                snapshot = System.Text.Json.JsonDocument.Parse(e.SnapshotJson).RootElement.Clone()
            }),
            progress = await db.Progress.Where(p => p.WorkflowId == id).OrderBy(p => p.Day).ToListAsync()
        });
    }

    private static object Details(FitnessWorkflow w) => new {
        w.Id, w.UserId, w.Status, w.Version, w.PreviousWorkflowId, w.CurrentStep, w.Summary, w.Feedback, w.CreatedAt, w.UpdatedAt,
        plan = w.PlanJson is null ? null : FitnessJson.Read<WorkoutPlan>(w.PlanJson),
        safetyNote = "This self-guided workout is not medical clearance. Stop any movement that causes pain. Significant, worsening, or persistent pain needs qualified professional guidance."
    };
}
