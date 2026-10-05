using System.Security.Claims;
using System.Text.Json;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.RateLimiting;

namespace VitroFit.API.Features.GymAgent
{
    /// <summary>
    /// Equipment/classes and workout suggestions for a gym. The only public route to the AI: React and
    /// Flutter call this API, which authenticates the user, rate-limits, validates the input and only then
    /// calls the internal Python service with the shared service key. Any signed-in user may use it.
    /// </summary>
    [ApiController]
    [Route("api/gyms")]
    [Authorize]
    [EnableRateLimiting(GymAgentRateLimiting.PolicyName)]
    [TypeFilter(typeof(GymAgentExceptionFilter))]
    public class GymsController : ControllerBase
    {
        private readonly IGymAgentClient _agent;
        private readonly ILogger<GymsController> _logger;

        public GymsController(IGymAgentClient agent, ILogger<GymsController> logger)
        {
            _agent = agent;
            _logger = logger;
        }

        private string UserId =>
            User.FindFirstValue(ClaimTypes.NameIdentifier) ?? User.FindFirstValue("sub") ?? string.Empty;

        /// <summary>Equipment, classes and contact details for a gym (AI-enriched, cached, or verified by an admin).</summary>
        [HttpPost("details")]
        [ProducesResponseType(typeof(JsonElement), StatusCodes.Status200OK)]
        public async Task<IActionResult> Details([FromBody] GymDetailsRequest request, CancellationToken ct)
        {
            _logger.LogInformation("Gym details requested by user {UserId} for place {PlaceId}", UserId, request.PlaceId);
            return Ok(await _agent.GetGymDetailsAsync(request, ct));
        }

        /// <summary>Four workout suggestions based on a gym's known equipment and classes.</summary>
        [HttpPost("workouts")]
        [ProducesResponseType(typeof(JsonElement), StatusCodes.Status200OK)]
        public async Task<IActionResult> Workouts([FromBody] GymWorkoutsRequest request, CancellationToken ct)
        {
            _logger.LogInformation("Workout suggestions requested by user {UserId} for place {PlaceId}", UserId, request.PlaceId);
            return Ok(await _agent.GetGymWorkoutsAsync(request, ct));
        }
    }
}
