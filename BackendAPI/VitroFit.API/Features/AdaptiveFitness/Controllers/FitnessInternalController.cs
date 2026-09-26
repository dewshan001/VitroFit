using System.Security.Cryptography;
using System.Text;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
namespace VitroFit.API.Features.AdaptiveFitness;

[ApiController, Route("api/fitness/internal"), AllowAnonymous]
[TypeFilter(typeof(FitnessExceptionFilter))]
public sealed class FitnessInternalController(FitnessDbContext db, IConfiguration configuration) : ControllerBase
{
    [HttpPost("{id:guid}/events")]
    public async Task<IActionResult> Record(Guid id, EventInput input)
    {
        var expected = configuration["FitnessAgent:ServiceKey"] ?? "";
        var supplied = Request.Headers["X-Fitness-Key"].ToString();
        if (expected.Length < 32 || !CryptographicOperations.FixedTimeEquals(
            SHA256.HashData(Encoding.UTF8.GetBytes(expected)), SHA256.HashData(Encoding.UTF8.GetBytes(supplied))))
            return Unauthorized();
        if (!await db.Workflows.AnyAsync(w => w.Id == id && w.RunId == input.RunId && w.Status == "Running")) return Conflict();
        if (await db.Events.CountAsync(e => e.WorkflowId == id) >= 100) return Conflict();
        if (input.Snapshot.ValueKind != System.Text.Json.JsonValueKind.Object || input.Snapshot.GetRawText().Length > 100000) return BadRequest();
        db.Events.Add(new() { WorkflowId = id, Step = input.Step, Summary = input.Summary,
            DurationMs = input.DurationMs, SnapshotJson = input.Snapshot.GetRawText() });
        await db.SaveChangesAsync();
        await db.Workflows.Where(w => w.Id == id && w.RunId == input.RunId && w.Status == "Running")
            .ExecuteUpdateAsync(update => update.SetProperty(w => w.CurrentStep, input.Step));
        return NoContent();
    }
}
