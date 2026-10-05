using System.Net;
using System.Net.Http.Json;
using System.Text.Json;
using Microsoft.Extensions.Options;
using VitroFit.API.Settings;

namespace VitroFit.API.Features.GymAgent
{
    /// <summary>Failure talking to the internal agent service, already mapped to a safe HTTP status.</summary>
    public sealed class GymAgentException : Exception
    {
        public HttpStatusCode Status { get; }

        public GymAgentException(HttpStatusCode status, string message) : base(message)
        {
            Status = status;
        }
    }

    public interface IGymAgentClient
    {
        Task<StartedWorkflowDto> StartAsync(StartGymWorkflowRequest request, string requestedBy, CancellationToken ct);
        Task<GymWorkflowDto> GetAsync(string id, CancellationToken ct);
        Task<IReadOnlyList<GymWorkflowEventDto>> GetEventsAsync(string id, CancellationToken ct);
        Task<IReadOnlyList<GymWorkflowDto>> ListAsync(string? status, string? requestedBy, CancellationToken ct);
        Task DecideAsync(string id, GymDecision decision, CancellationToken ct);
        Task<JsonElement> GetGymDetailsAsync(GymDetailsRequest request, CancellationToken ct);
        Task<JsonElement> GetGymWorkoutsAsync(GymWorkoutsRequest request, CancellationToken ct);
        Task<JsonElement> GetNearbyGymsAsync(NearbyGymsRequest request, CancellationToken ct);
        Task<JsonElement> GetMapsConfigAsync(CancellationToken ct);
    }

    /// <summary>
    /// Typed HttpClient for the Python gym-workflow service. Sends the shared service key,
    /// and turns upstream failures into GymAgentException without leaking upstream details.
    /// </summary>
    public sealed class GymAgentClient : IGymAgentClient
    {
        private const int MinKeyLength = 32;

        // The Python service takes snake_case bodies and returns camelCase.
        private static readonly JsonSerializerOptions RequestJson = new()
        {
            PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower,
            DefaultIgnoreCondition = System.Text.Json.Serialization.JsonIgnoreCondition.WhenWritingNull
        };

        private static readonly JsonSerializerOptions ResponseJson = new(JsonSerializerDefaults.Web);

        private readonly HttpClient _http;
        private readonly GymAgentSettings _settings;
        private readonly ILogger<GymAgentClient> _logger;

        public GymAgentClient(HttpClient http, IOptions<GymAgentSettings> settings, ILogger<GymAgentClient> logger)
        {
            _http = http;
            _settings = settings.Value;
            _logger = logger;
        }

        public async Task<StartedWorkflowDto> StartAsync(StartGymWorkflowRequest request, string requestedBy, CancellationToken ct)
        {
            var body = new
            {
                place_id = request.PlaceId,
                name = request.Name,
                address = request.Address,
                website = request.Website,
                known_phone = request.KnownPhone,
                known_email = request.KnownEmail,
                known_hours = request.KnownHours,
                lat = request.Lat,
                lng = request.Lng,
                requested_by = requestedBy
            };
            using var message = Build(HttpMethod.Post, "/internal/workflows", JsonContent.Create(body, options: RequestJson));
            return await SendAsync<StartedWorkflowDto>(message, ct);
        }

        public async Task<GymWorkflowDto> GetAsync(string id, CancellationToken ct)
        {
            using var message = Build(HttpMethod.Get, $"/internal/workflows/{Uri.EscapeDataString(id)}");
            return await SendAsync<GymWorkflowDto>(message, ct);
        }

        public async Task<IReadOnlyList<GymWorkflowEventDto>> GetEventsAsync(string id, CancellationToken ct)
        {
            using var message = Build(HttpMethod.Get, $"/internal/workflows/{Uri.EscapeDataString(id)}/events");
            return await SendAsync<List<GymWorkflowEventDto>>(message, ct);
        }

        public async Task<IReadOnlyList<GymWorkflowDto>> ListAsync(string? status, string? requestedBy, CancellationToken ct)
        {
            var query = new List<string>();
            if (!string.IsNullOrWhiteSpace(status)) query.Add($"status={Uri.EscapeDataString(status)}");
            if (!string.IsNullOrWhiteSpace(requestedBy)) query.Add($"requestedBy={Uri.EscapeDataString(requestedBy)}");
            var path = "/internal/workflows" + (query.Count > 0 ? "?" + string.Join("&", query) : "");
            using var message = Build(HttpMethod.Get, path);
            return await SendAsync<List<GymWorkflowDto>>(message, ct);
        }

        public async Task DecideAsync(string id, GymDecision decision, CancellationToken ct)
        {
            var body = new
            {
                decision = decision.Decision,
                reason = decision.Reason ?? string.Empty,
                actor_id = decision.ActorId,
                actor_role = decision.ActorRole
            };
            using var message = Build(
                HttpMethod.Post,
                $"/internal/workflows/{Uri.EscapeDataString(id)}/decision",
                JsonContent.Create(body, options: RequestJson));
            await SendAsync<JsonElement>(message, ct);
        }

        public async Task<JsonElement> GetGymDetailsAsync(GymDetailsRequest request, CancellationToken ct)
        {
            using var message = Build(HttpMethod.Post, "/internal/gyms/details", JsonContent.Create(request, options: RequestJson));
            return await SendAsync<JsonElement>(message, ct, AiTimeout);
        }

        public async Task<JsonElement> GetGymWorkoutsAsync(GymWorkoutsRequest request, CancellationToken ct)
        {
            using var message = Build(HttpMethod.Post, "/internal/gyms/workouts", JsonContent.Create(request, options: RequestJson));
            return await SendAsync<JsonElement>(message, ct, AiTimeout);
        }

        public async Task<JsonElement> GetNearbyGymsAsync(NearbyGymsRequest request, CancellationToken ct)
        {
            using var message = Build(HttpMethod.Post, "/internal/gyms/nearby", JsonContent.Create(request, options: RequestJson));
            return await SendAsync<JsonElement>(message, ct);
        }

        public async Task<JsonElement> GetMapsConfigAsync(CancellationToken ct)
        {
            using var message = Build(HttpMethod.Get, "/internal/gyms/maps-config");
            return await SendAsync<JsonElement>(message, ct);
        }

        private TimeSpan QuickTimeout => TimeSpan.FromSeconds(Math.Max(1, _settings.TimeoutSeconds));
        private TimeSpan AiTimeout => TimeSpan.FromSeconds(Math.Max(1, _settings.AiTimeoutSeconds));

        private HttpRequestMessage Build(HttpMethod method, string path, HttpContent? content = null)
        {
            if (_settings.ServiceKey.Length < MinKeyLength)
            {
                throw new GymAgentException(HttpStatusCode.ServiceUnavailable, "Gym agent service is not configured.");
            }

            var message = new HttpRequestMessage(method, path) { Content = content };
            message.Headers.Add("X-Gym-Agent-Key", _settings.ServiceKey);
            return message;
        }

        private async Task<T> SendAsync<T>(HttpRequestMessage message, CancellationToken ct, TimeSpan? timeout = null)
        {
            // The HttpClient itself has no timeout; each call gets its own (AI calls need far longer than status calls).
            using var deadline = CancellationTokenSource.CreateLinkedTokenSource(ct);
            deadline.CancelAfter(timeout ?? QuickTimeout);

            HttpResponseMessage response;
            try
            {
                response = await _http.SendAsync(message, deadline.Token);
            }
            catch (OperationCanceledException) when (!ct.IsCancellationRequested)
            {
                _logger.LogWarning("Gym agent service timed out for {Path}", message.RequestUri);
                throw new GymAgentException(HttpStatusCode.GatewayTimeout, "The gym agent service took too long to respond.");
            }
            catch (HttpRequestException ex)
            {
                _logger.LogWarning(ex, "Gym agent service unreachable");
                throw new GymAgentException(HttpStatusCode.ServiceUnavailable, "Gym agent service is unavailable.");
            }

            using (response)
            {
                if (!response.IsSuccessStatusCode)
                {
                    _logger.LogWarning("Gym agent service returned {Status} for {Path}", (int)response.StatusCode, message.RequestUri);
                    throw response.StatusCode switch
                    {
                        HttpStatusCode.NotFound => new GymAgentException(HttpStatusCode.NotFound, "Workflow not found."),
                        HttpStatusCode.Conflict => new GymAgentException(HttpStatusCode.Conflict, await ReadDetailAsync(response, "Workflow state conflict.")),
                        HttpStatusCode.Forbidden => new GymAgentException(HttpStatusCode.Forbidden, "Not permitted to perform this action."),
                        HttpStatusCode.UnprocessableEntity or HttpStatusCode.BadRequest => new GymAgentException(HttpStatusCode.BadRequest, "The request was rejected by the agent service."),
                        // 401 here means our own service key is wrong: an operator problem, not the caller's.
                        _ => new GymAgentException(HttpStatusCode.BadGateway, "Gym agent service failed.")
                    };
                }

                var result = await response.Content.ReadFromJsonAsync<T>(ResponseJson, deadline.Token);
                return result ?? throw new GymAgentException(HttpStatusCode.BadGateway, "Gym agent service returned an empty response.");
            }
        }

        // Only used for 409, whose detail strings are ours ("Workflow is X, not awaiting approval").
        private static async Task<string> ReadDetailAsync(HttpResponseMessage response, string fallback)
        {
            try
            {
                using var doc = await JsonDocument.ParseAsync(await response.Content.ReadAsStreamAsync());
                return doc.RootElement.TryGetProperty("detail", out var d) && d.ValueKind == JsonValueKind.String
                    ? d.GetString() ?? fallback
                    : fallback;
            }
            catch
            {
                return fallback;
            }
        }
    }
}
