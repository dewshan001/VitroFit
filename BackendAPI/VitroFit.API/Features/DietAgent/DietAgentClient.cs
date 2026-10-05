using System.Net;
using System.Net.Http.Headers;
using Microsoft.Extensions.Options;
using VitroFit.API.Settings;

namespace VitroFit.API.Features.DietAgent
{
    /// <summary>Failure talking to the diet service, already mapped to a safe HTTP status and message.</summary>
    public sealed class DietAgentException : Exception
    {
        public HttpStatusCode Status { get; }

        public DietAgentException(HttpStatusCode status, string message) : base(message)
        {
            Status = status;
        }
    }

    /// <summary>One request to pass on to the diet service, exactly as the browser sent it.</summary>
    public sealed record DietAgentRequest(
        HttpMethod Method, string PathAndQuery, string? Authorization, byte[]? Body, string? ContentType);

    /// <summary>The diet service's answer, passed back to the browser unchanged.</summary>
    public sealed record DietAgentResponse(HttpStatusCode Status, byte[] Body, string? ContentType);

    public interface IDietAgentClient
    {
        Task<DietAgentResponse> ForwardAsync(DietAgentRequest request, CancellationToken ct);
    }

    /// <summary>
    /// Typed HttpClient for the Python diet-plan service. It does not interpret the diet API: it passes the request
    /// on with the shared service key and returns the answer unchanged, so the web app sees exactly the status codes
    /// and JSON it always did. Only failures of the hop itself (unreachable, too slow, wrong key) are translated.
    /// </summary>
    public sealed class DietAgentClient : IDietAgentClient
    {
        private const int MinKeyLength = 32;
        public const string KeyHeader = "X-Diet-Agent-Key";

        private readonly HttpClient _http;
        private readonly DietAgentSettings _settings;
        private readonly ILogger<DietAgentClient> _logger;

        public DietAgentClient(HttpClient http, IOptions<DietAgentSettings> settings, ILogger<DietAgentClient> logger)
        {
            _http = http;
            _settings = settings.Value;
            _logger = logger;
        }

        public async Task<DietAgentResponse> ForwardAsync(DietAgentRequest request, CancellationToken ct)
        {
            // A key that is set but too short is a mistake, not "no key": refuse rather than quietly send a weak one.
            if (_settings.ServiceKey.Length > 0 && _settings.ServiceKey.Length < MinKeyLength)
            {
                throw new DietAgentException(HttpStatusCode.ServiceUnavailable, "The diet service is not configured correctly.");
            }

            using var message = new HttpRequestMessage(request.Method, request.PathAndQuery);
            if (_settings.ServiceKey.Length > 0) message.Headers.Add(KeyHeader, _settings.ServiceKey);
            if (!string.IsNullOrEmpty(request.Authorization)) message.Headers.TryAddWithoutValidation("Authorization", request.Authorization);
            if (request.Body is { Length: > 0 })
            {
                message.Content = new ByteArrayContent(request.Body);
                message.Content.Headers.ContentType = MediaTypeHeaderValue.TryParse(request.ContentType, out var type)
                    ? type
                    : new MediaTypeHeaderValue("application/json");
            }

            // The HttpClient itself has no timeout; each call gets this one.
            using var deadline = CancellationTokenSource.CreateLinkedTokenSource(ct);
            deadline.CancelAfter(TimeSpan.FromSeconds(Math.Max(1, _settings.TimeoutSeconds)));

            HttpResponseMessage response;
            try
            {
                response = await _http.SendAsync(message, deadline.Token);
            }
            catch (OperationCanceledException) when (!ct.IsCancellationRequested)
            {
                _logger.LogWarning("Diet service timed out for {Method} {Path}", request.Method, request.PathAndQuery);
                throw new DietAgentException(HttpStatusCode.GatewayTimeout, "The diet service took too long to respond.");
            }
            catch (HttpRequestException ex)
            {
                _logger.LogWarning(ex, "Diet service unreachable");
                throw new DietAgentException(HttpStatusCode.ServiceUnavailable, "The diet service is unavailable.");
            }

            using (response)
            {
                // The caller's token was already checked by this API, so a 401/503 from the service means our own key
                // is wrong or the service is misconfigured: an operator problem, not the user's.
                if (response.StatusCode is HttpStatusCode.Unauthorized or HttpStatusCode.ServiceUnavailable)
                {
                    _logger.LogWarning("Diet service refused the request with {Status} for {Path}", (int)response.StatusCode, request.PathAndQuery);
                    throw new DietAgentException(HttpStatusCode.BadGateway, "The diet service could not be reached securely.");
                }

                var body = await response.Content.ReadAsByteArrayAsync(deadline.Token);
                return new DietAgentResponse(response.StatusCode, body, response.Content.Headers.ContentType?.ToString());
            }
        }
    }
}
