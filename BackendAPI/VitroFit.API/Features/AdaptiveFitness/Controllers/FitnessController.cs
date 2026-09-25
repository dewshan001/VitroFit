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
        if (input.Equipment.Any(e => e is not ("bodyweight" or "dumbbells" or "resistance_band")))
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
        if (input.PreviousWorkflowId.HasValue)
        {
            previous = await db.Workflows.SingleOrDefaultAsync(w => w.Id == input.PreviousWorkflowId && w.UserId == UserId && w.Status == "Ready");
            if (previous?.PlanJson is null) return BadRequest(new { message = "Continue from your latest ready schedule." });
            var previousPlan = FitnessJson.Read<WorkoutPlan>(previous.PlanJson);
            if (previousPlan.Week >= 4)
                return Conflict(new { message = "You have completed the four beginner schedules. Meet an instructor to continue your training." });
            if (await db.Workflows.AnyAsync(w => w.UserId == UserId && w.PreviousWorkflowId == previous.Id))
                return Conflict(new { message = "Continue from your latest schedule; this schedule already has a follow-up." });
            progress = await db.Progress.Where(p => p.WorkflowId == previous.Id)
                .Select(p => new AgentProgress(p.Day, p.Completed, p.Rpe, p.Pain)).ToListAsync();
            if (progress.Count != previousPlan.Days.Count || previousPlan.Days.Any(day => progress.All(p => p.Day != day.Day)))
                return BadRequest(new { message = "Record progress for every day in this schedule before requesting the next one." });
            if (progress.Any(p => p.Pain))
                return BadRequest(new { message = "Pain or discomfort was reported. Stop self-guided training and contact an instructor before requesting another week." });
            if (progress.Any(p => !p.Completed))
                return BadRequest(new { message = "Complete every scheduled day before requesting the next week." });
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
            previous?.PlanJson is { } json ? FitnessJson.Read<WorkoutPlan>(json) : null, progress, "");
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
        safetyNote = "This beginner schedule is not medical clearance. Stop if you feel pain or unwell. After week four, meet an instructor for a personalized program."
    };
}
