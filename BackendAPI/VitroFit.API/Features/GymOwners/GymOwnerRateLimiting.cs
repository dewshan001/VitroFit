using System.Threading.RateLimiting;
using Microsoft.AspNetCore.RateLimiting;

namespace VitroFit.API.Features.GymOwners
{
    /// <summary>
    /// The registration endpoint is anonymous and accepts file uploads, so it is limited per client address.
    /// </summary>
    public static class GymOwnerRateLimiting
    {
        public const string PolicyName = "gym-owner-register";

        /// <summary>Five photos + five equipment photos + a licence, each up to 5 MB, plus form fields.</summary>
        public const long MaxRequestBytes = 60L * 1024 * 1024;

        public static IServiceCollection AddGymOwnerRateLimiting(this IServiceCollection services, int permitsPerHour)
        {
            return services.AddRateLimiter(options =>
            {
                options.RejectionStatusCode = StatusCodes.Status429TooManyRequests;
                options.AddPolicy(PolicyName, context => RateLimitPartition.GetFixedWindowLimiter(
                    context.Connection.RemoteIpAddress?.ToString() ?? "unknown",
                    _ => new FixedWindowRateLimiterOptions
                    {
                        PermitLimit = Math.Max(1, permitsPerHour),
                        Window = TimeSpan.FromHours(1),
                        QueueLimit = 0
                    }));
            });
        }
    }
}
