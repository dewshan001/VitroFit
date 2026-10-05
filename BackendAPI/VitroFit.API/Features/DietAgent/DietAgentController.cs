using System.Text.RegularExpressions;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.RateLimiting;

namespace VitroFit.API.Features.DietAgent
{
    /// <summary>
    /// Public entry to the diet-plan service: <c>api/diet/*</c>. Browsers call this API (JWT checked here, per-user
    /// rate limit on the calls that start LLM work) and never the Python service itself. Requests are passed on
    /// unchanged with the caller's token, and the service's answer comes back unchanged, so the request and response
    /// shapes of the diet API are exactly what the service defines. Identity, ownership, roles and the Trainer/Admin
    /// approval rules stay enforced by the service from that token.
    /// </summary>
    [ApiController]
    [Route("api/diet")]
    [Authorize]
    [TypeFilter(typeof(DietAgentExceptionFilter))]
    [RequestSizeLimit(MaxBodyBytes)]
    public class DietAgentController : ControllerBase
    {
        /// <summary>A generous ceiling: the largest legitimate body is one day's plan (a few KB).</summary>
        public const int MaxBodyBytes = 512 * 1024;

        // Only the diet API's own routes are passed on; nothing else on the service (docs, health) is reachable through here.
        private static readonly Regex AllowedPath = new(
            @"^(generate|confirm|plans(/\d{1,10})?|approvals/pending|workflows/[0-9a-fA-F\-]{1,64}(/(trace|refine|approve|reject))?)$",
            RegexOptions.Compiled | RegexOptions.CultureInvariant);

        private readonly IDietAgentClient _agent;

        public DietAgentController(IDietAgentClient agent)
        {
            _agent = agent;
        }

        /// <summary>Starts a plan. Uses the LLM, so it is rate limited per user; the service answers at once and works in the background.</summary>
        [HttpPost("generate")]
        [EnableRateLimiting(DietAgentRateLimiting.PolicyName)]
        public Task<IActionResult> Generate(CancellationToken ct) => Forward("generate", ct);

        /// <summary>Edits a plan with a free-text instruction. Uses the LLM, so it is rate limited per user.</summary>
        [HttpPost("workflows/{id}/refine")]
        [EnableRateLimiting(DietAgentRateLimiting.PolicyName)]
        public Task<IActionResult> Refine(string id, CancellationToken ct) => Forward($"workflows/{id}/refine", ct);

        /// <summary>Everything else (progress, trace, saved plans, confirm, approvals): passed straight through.</summary>
        [AcceptVerbs("GET", "POST", "PUT", "DELETE")]
        [Route("{**path}")]
        public Task<IActionResult> Pass(string path, CancellationToken ct) => Forward(path, ct);

        private async Task<IActionResult> Forward(string path, CancellationToken ct)
        {
            if (!AllowedPath.IsMatch(path ?? string.Empty)) return NotFound();

            if (Request.ContentLength > MaxBodyBytes) return StatusCode(StatusCodes.Status413PayloadTooLarge);
            byte[]? body = null;
            if (Request.ContentLength is null or > 0)
            {
                using var buffer = new MemoryStream();
                await Request.Body.CopyToAsync(buffer, ct);
                if (buffer.Length > MaxBodyBytes) return StatusCode(StatusCodes.Status413PayloadTooLarge);
                body = buffer.ToArray();
            }

            var upstream = await _agent.ForwardAsync(
                new DietAgentRequest(
                    new HttpMethod(Request.Method),
                    $"/api/diet/{path}{Request.QueryString.Value}",
                    Request.Headers.Authorization.ToString(),
                    body,
                    Request.ContentType),
                ct);

            return new UpstreamResult(upstream);
        }

        /// <summary>Writes the service's status, content type and body back exactly as received.</summary>
        private sealed class UpstreamResult : IActionResult
        {
            private readonly DietAgentResponse _response;

            public UpstreamResult(DietAgentResponse response) => _response = response;

            public async Task ExecuteResultAsync(ActionContext context)
            {
                var http = context.HttpContext.Response;
                http.StatusCode = (int)_response.Status;
                if (_response.Body.Length == 0) return;
                http.ContentType = _response.ContentType ?? "application/json";
                http.ContentLength = _response.Body.Length;
                await http.Body.WriteAsync(_response.Body, context.HttpContext.RequestAborted);
            }
        }
    }
}
