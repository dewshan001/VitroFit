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
    public sealed class WorkoutsController : ControllerBase
    {
        private readonly AppDbContext _dbContext;

        public WorkoutsController(AppDbContext dbContext)
        {
            _dbContext = dbContext;
        }

        [HttpGet]
        public async Task<IActionResult> GetWorkouts()
        {
            var workouts = await _dbContext.Workouts
                .OrderBy(w => w.Category)
                .ThenBy(w => w.Name)
                .ToListAsync();

            return Ok(workouts.Select(ToDto));
        }

        [HttpPost]
        [Authorize(Roles = "Admin")]
        public async Task<IActionResult> CreateWorkout([FromBody] UpsertWorkoutRequest request)
        {
            if (await _dbContext.Workouts.AnyAsync(w => w.Name == request.Name))
                return BadRequest(new { error = "A workout with this name already exists." });

            var workout = new Workout
            {
                Name = request.Name,
                Category = request.Category,
                Description = request.Description
            };

            _dbContext.Workouts.Add(workout);
            await _dbContext.SaveChangesAsync();

            return Ok(ToDto(workout));
        }

        [HttpPut("{id}")]
        [Authorize(Roles = "Admin")]
        public async Task<IActionResult> UpdateWorkout(int id, [FromBody] UpsertWorkoutRequest request)
        {
            var workout = await _dbContext.Workouts.FindAsync(id);
            if (workout == null)
                return NotFound(new { error = "Workout not found." });

            if (await _dbContext.Workouts.AnyAsync(w => w.Id != id && w.Name == request.Name))
                return BadRequest(new { error = "A workout with this name already exists." });

            workout.Name = request.Name;
            workout.Category = request.Category;
            workout.Description = request.Description;

            await _dbContext.SaveChangesAsync();

            return Ok(ToDto(workout));
        }

        [HttpDelete("{id}")]
        [Authorize(Roles = "Admin")]
        public async Task<IActionResult> DeleteWorkout(int id)
        {
            var workout = await _dbContext.Workouts.FindAsync(id);
            if (workout == null)
                return NotFound(new { error = "Workout not found." });

            var isInUse = await _dbContext.TimetableSlots.AnyAsync(s => s.WorkoutId == id);
            if (isInUse)
                return BadRequest(new { error = "Cannot delete a workout that is scheduled in a user's timetable." });

            _dbContext.Workouts.Remove(workout);
            await _dbContext.SaveChangesAsync();

            return Ok(new { message = "Workout deleted successfully." });
        }

        private static WorkoutDto ToDto(Workout w) => new()
        {
            Id = w.Id,
            Name = w.Name,
            Category = w.Category,
            Description = w.Description
        };
    }
}
