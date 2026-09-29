using System.Security.Claims;
using System.Threading.RateLimiting;
using Microsoft.AspNetCore.RateLimiting;

namespace VitroFit.API.Features.GymAgent
{
    /// <summary>
    /// Rate limit for endpoints that can start LLM work. Partitioned per signed-in user, or per IP for
    /// anonymous callers (they are refused right after, but must not be able to hammer the limiter's neighbours).
    /// </summary>
    public static class GymAgentRateLimiting
    {
        public const string PolicyName = "gym-ai";

        public static IServiceCollection AddGymAgentRateLimiting(this IServiceCollection services, int permitsPerMinute)
        {
            return services.AddRateLimiter(options =>
            {
                options.RejectionStatusCode = StatusCodes.Status429TooManyRequests;
                options.AddPolicy(PolicyName, context => RateLimitPartition.GetFixedWindowLimiter(
                    PartitionKey(context),
                    _ => new FixedWindowRateLimiterOptions
                    {
                        PermitLimit = Math.Max(1, permitsPerMinute),
                        Window = TimeSpan.FromMinutes(1),
                        QueueLimit = 0
                    }));

                options.OnRejected = async (context, ct) =>
                {
                    if (context.Lease.TryGetMetadata(MetadataName.RetryAfter, out var retryAfter))
                    {
                        context.HttpContext.Response.Headers.RetryAfter = ((int)retryAfter.TotalSeconds).ToString();
                    }
                    await context.HttpContext.Response.WriteAsJsonAsync(
                        new
                        {
                            status = 429,
                            title = "Too many requests",
                            detail = "You are asking for gym details too quickly. Please wait a moment and try again."
                        },
                        options: null,
                        contentType: "application/problem+json",
                        cancellationToken: ct);
                };
            });
        }

        public static string PartitionKey(HttpContext context)
        {
            var user = context.User;
            if (user.Identity?.IsAuthenticated == true)
            {
                var id = user.FindFirstValue(ClaimTypes.NameIdentifier) ?? user.FindFirstValue("sub");
                if (!string.IsNullOrEmpty(id)) return $"user:{id}";
            }
            return $"ip:{context.Connection.RemoteIpAddress}";
        }
    }
}
