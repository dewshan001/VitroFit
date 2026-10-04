using System.Threading.RateLimiting;
using VitroFit.API.Features.GymAgent;

namespace VitroFit.API.Features.DietAgent
{
    /// <summary>
    /// Rate limit for the diet endpoints that start LLM work (generate and edit a plan). One counter per signed-in user
    /// (per IP when anonymous), the same partitioning as the gym agent. Only the policy is added here; the 429 response
    /// body is the shared one configured in <see cref="GymAgentRateLimiting"/>.
    /// </summary>
    public static class DietAgentRateLimiting
    {
        public const string PolicyName = "diet-ai";

        public static IServiceCollection AddDietAgentRateLimiting(this IServiceCollection services, int permitsPerMinute)
        {
            return services.AddRateLimiter(options =>
            {
                options.RejectionStatusCode = StatusCodes.Status429TooManyRequests;
                options.AddPolicy(PolicyName, context => RateLimitPartition.GetFixedWindowLimiter(
                    GymAgentRateLimiting.PartitionKey(context),
                    _ => new FixedWindowRateLimiterOptions
                    {
                        PermitLimit = Math.Max(1, permitsPerMinute),
                        Window = TimeSpan.FromMinutes(1),
                        QueueLimit = 0
                    }));
            });
        }
    }
}
