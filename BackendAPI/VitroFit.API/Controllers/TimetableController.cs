using System.IdentityModel.Tokens.Jwt;
using System.Security.Claims;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using VitroFit.API.Data;
using VitroFit.API.Dtos.Timetable;
using VitroFit.API.Entities;

namespace VitroFit.API.Controllers
{
    [ApiController]
    [Route("api/[controller]")]
    [Authorize]
    public sealed class TimetableController : ControllerBase
    {
        private readonly AppDbContext _dbContext;

        public TimetableController(AppDbContext dbContext)
        {
            _dbContext = dbContext;
        }

        [HttpGet]
        public async Task<IActionResult> GetSlots()
        {
            var userId = GetUserId();
            if (!userId.HasValue)
                return Unauthorized(new { error = "Invalid token." });

            var slots = await _dbContext.TimetableSlots
                .Include(s => s.Workout)
                .Where(s => s.UserId == userId.Value)
                .OrderBy(s => s.Day)
                .ThenBy(s => s.StartTime)
                .ToListAsync();

            return Ok(slots.Select(ToDto));
        }

        [HttpPost]
        public async Task<IActionResult> CreateSlot([FromBody] UpsertTimetableSlotRequest request)
        {
            var userId = GetUserId();
            if (!userId.HasValue)
                return Unauthorized(new { error = "Invalid token." });

            if (request.EndTime <= request.StartTime)
                return BadRequest(new { error = "End time must be after start time." });

            var workout = await _dbContext.Workouts.FindAsync(request.WorkoutId);
            if (workout == null)
                return BadRequest(new { error = "Selected workout does not exist." });

            var slot = new TimetableSlot
            {
                UserId = userId.Value,
                Day = request.Day,
                StartTime = request.StartTime,
                EndTime = request.EndTime,
                Title = request.Title,
                WorkoutId = request.WorkoutId
            };

            _dbContext.TimetableSlots.Add(slot);
            await _dbContext.SaveChangesAsync();

            slot.Workout = workout;
            return Ok(ToDto(slot));
        }

        [HttpPut("{id}")]
        public async Task<IActionResult> UpdateSlot(int id, [FromBody] UpsertTimetableSlotRequest request)
        {
            var userId = GetUserId();
            if (!userId.HasValue)
                return Unauthorized(new { error = "Invalid token." });

            if (request.EndTime <= request.StartTime)
                return BadRequest(new { error = "End time must be after start time." });

            var slot = await _dbContext.TimetableSlots
                .FirstOrDefaultAsync(s => s.Id == id && s.UserId == userId.Value);

            if (slot == null)
                return NotFound(new { error = "Timetable slot not found." });

            var workout = await _dbContext.Workouts.FindAsync(request.WorkoutId);
            if (workout == null)
                return BadRequest(new { error = "Selected workout does not exist." });

            slot.Day = request.Day;
            slot.StartTime = request.StartTime;
            slot.EndTime = request.EndTime;
            slot.Title = request.Title;
            slot.WorkoutId = request.WorkoutId;

            await _dbContext.SaveChangesAsync();

            slot.Workout = workout;
            return Ok(ToDto(slot));
        }

        [HttpDelete("{id}")]
        public async Task<IActionResult> DeleteSlot(int id)
        {
            var userId = GetUserId();
            if (!userId.HasValue)
                return Unauthorized(new { error = "Invalid token." });

            var slot = await _dbContext.TimetableSlots
                .FirstOrDefaultAsync(s => s.Id == id && s.UserId == userId.Value);

            if (slot == null)
                return NotFound(new { error = "Timetable slot not found." });

            _dbContext.TimetableSlots.Remove(slot);
            await _dbContext.SaveChangesAsync();

            return Ok(new { message = "Timetable slot deleted successfully." });
        }

        private static TimetableSlotDto ToDto(TimetableSlot s) => new()
        {
            Id = s.Id,
            Day = s.Day,
            StartTime = s.StartTime,
            EndTime = s.EndTime,
            Title = s.Title,
            WorkoutId = s.WorkoutId,
            WorkoutName = s.Workout != null ? s.Workout.Name : string.Empty,
            WorkoutCategory = s.Workout != null ? s.Workout.Category : string.Empty
        };

        private int? GetUserId()
        {
            var userIdStr = User.FindFirstValue(ClaimTypes.NameIdentifier)
                         ?? User.FindFirstValue(JwtRegisteredClaimNames.Sub)
                         ?? User.FindFirst("sub")?.Value;

            return int.TryParse(userIdStr, out var userId) ? userId : null;
        }
    }
}
