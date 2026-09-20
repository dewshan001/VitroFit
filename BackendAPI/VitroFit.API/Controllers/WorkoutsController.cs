using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using VitroFit.API.Data;
using VitroFit.API.Dtos.Timetable;

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
                .Select(w => new WorkoutDto
                {
                    Id = w.Id,
                    Name = w.Name,
                    Category = w.Category,
                    Description = w.Description
                })
                .ToListAsync();

            return Ok(workouts);
        }
    }
}
