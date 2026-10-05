using System.ComponentModel.DataAnnotations;
using System.Text.Json;
using System.Threading.RateLimiting;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.RateLimiting;

namespace VitroFit.API.Features.GymAgent
{
    public sealed class NearbyGymsRequest
    {
        [Range(-90, 90)] public double Lat { get; set; }
        [Range(-180, 180)] public double Lng { get; set; }
        [Range(1, 50000)] public double RadiusMeters { get; set; } = 50000;
        [Range(1, 20)] public int MaxResults { get; set; } = 20;
    }

    public static class NearbyGymsRateLimiting
    {
        public const string PolicyName = "gym-places";

        public static IServiceCollection AddNearbyGymsRateLimiting(this IServiceCollection services, int permitsPerMinute)
        {
            return services.AddRateLimiter(options => options.AddPolicy(PolicyName, context =>
                RateLimitPartition.GetFixedWindowLimiter(
                    GymAgentRateLimiting.PartitionKey(context),
                    _ => new FixedWindowRateLimiterOptions
                    {
                        PermitLimit = Math.Max(1, permitsPerMinute),
                        Window = TimeSpan.FromMinutes(1),
                        QueueLimit = 0
                    })));
        }
    }

    /// <summary>
    /// Nearby gym search for the mobile app. The Google Places key lives only in GymAgentService's .env: the app
    /// sends a location, this API forwards it (with the service key) and returns Google's response unchanged.
    /// </summary>
    [ApiController]
    [Route("api/gyms")]
    [Authorize]
    [EnableRateLimiting(NearbyGymsRateLimiting.PolicyName)]
    [TypeFilter(typeof(GymAgentExceptionFilter))]
    public class NearbyGymsController : ControllerBase
    {
        private readonly IGymAgentClient _agent;

        public NearbyGymsController(IGymAgentClient agent)
        {
            _agent = agent;
        }

        /// <summary>Gyms near a point, nearest first (Google Places API (New) response body).</summary>
        [HttpPost("nearby")]
        [ProducesResponseType(typeof(JsonElement), StatusCodes.Status200OK)]
        public async Task<IActionResult> Nearby([FromBody] NearbyGymsRequest request, CancellationToken ct)
            => Ok(await _agent.GetNearbyGymsAsync(request, ct));

        /// <summary>
        /// The Google Maps browser key from GymAgentService's .env, for the web map script. Anonymous because the
        /// map is usable signed out; the key is public in the page either way, so restrict it in Google Cloud.
        /// </summary>
        [HttpGet("maps-config")]
        [AllowAnonymous]
        [ProducesResponseType(typeof(JsonElement), StatusCodes.Status200OK)]
        public async Task<IActionResult> MapsConfig(CancellationToken ct)
            => Ok(await _agent.GetMapsConfigAsync(ct));
    }
}
