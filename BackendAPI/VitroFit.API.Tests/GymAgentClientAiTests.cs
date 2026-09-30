using System.Net;
using System.Text;
using System.Text.Json;
using Microsoft.Extensions.Logging.Abstractions;
using Microsoft.Extensions.Options;
using VitroFit.API.Features.GymAgent;
using VitroFit.API.Settings;

namespace VitroFit.API.Tests;

/// <summary>The AI calls (details / workouts): request shape, service key, and per-call timeouts.</summary>
public sealed class GymAgentClientAiTests
{
    private const string Key = "0123456789abcdef0123456789abcdef";

    private sealed class SlowHandler : HttpMessageHandler
    {
        public TimeSpan Delay { get; set; } = TimeSpan.Zero;
        public HttpStatusCode Status { get; set; } = HttpStatusCode.OK;
        public string Json { get; set; } = "{\"source\":\"ai-scraped\",\"equipment\":[\"treadmill\"]}";
        public HttpRequestMessage? Last { get; private set; }
        public string? LastBody { get; private set; }

        protected override async Task<HttpResponseMessage> SendAsync(HttpRequestMessage request, CancellationToken ct)
        {
            Last = request;
            LastBody = request.Content == null ? null : await request.Content.ReadAsStringAsync(ct);
            if (Delay > TimeSpan.Zero) await Task.Delay(Delay, ct);          // honours the caller's timeout/cancellation
            return new HttpResponseMessage(Status) { Content = new StringContent(Json, Encoding.UTF8, "application/json") };
        }
    }

    private static (GymAgentClient Client, SlowHandler Handler) Make(int quickSeconds = 30, int aiSeconds = 150)
    {
        var handler = new SlowHandler();
        // Same as Program.cs: no client-wide timeout, each call brings its own.
        var http = new HttpClient(handler) { BaseAddress = new Uri("http://agent.test"), Timeout = Timeout.InfiniteTimeSpan };
        var settings = Options.Create(new GymAgentSettings { ServiceKey = Key, TimeoutSeconds = quickSeconds, AiTimeoutSeconds = aiSeconds });
        return (new GymAgentClient(http, settings, NullLogger<GymAgentClient>.Instance), handler);
    }

    private static GymDetailsRequest Gym() => new()
    {
        PlaceId = "p1", Name = "FitZone", Website = "https://fitzone.lk", OpeningHours = "Mo-Su 06:00-22:00", Lat = 7.2, Lng = 80.5
    };

    [Fact]
    public async Task Details_are_sent_to_the_internal_route_with_the_service_key_and_snake_case_body()
    {
        var (client, handler) = Make();
        var result = await client.GetGymDetailsAsync(Gym(), default);

        Assert.Equal("treadmill", result.GetProperty("equipment")[0].GetString());
        Assert.Equal(HttpMethod.Post, handler.Last!.Method);
        Assert.Equal("/internal/gyms/details", handler.Last.RequestUri!.AbsolutePath);
        Assert.Equal(Key, handler.Last.Headers.GetValues("X-Gym-Agent-Key").Single());

        using var body = JsonDocument.Parse(handler.LastBody!);
        Assert.Equal("p1", body.RootElement.GetProperty("place_id").GetString());
        Assert.Equal("Mo-Su 06:00-22:00", body.RootElement.GetProperty("opening_hours").GetString());
        Assert.Equal(7.2, body.RootElement.GetProperty("lat").GetDouble());
    }

    [Fact]
    public async Task Workouts_are_sent_to_the_internal_route()
    {
        var (client, handler) = Make();
        handler.Json = "{\"workouts\":[],\"notes\":\"\"}";
        await client.GetGymWorkoutsAsync(new GymWorkoutsRequest { PlaceId = "p1", Name = "n", Equipment = new() { "treadmill" } }, default);

        Assert.Equal("/internal/gyms/workouts", handler.Last!.RequestUri!.AbsolutePath);
        using var body = JsonDocument.Parse(handler.LastBody!);
        Assert.Equal("treadmill", body.RootElement.GetProperty("equipment")[0].GetString());
    }

    [Fact]
    public async Task A_quick_call_that_hangs_times_out_as_504()
    {
        var (client, handler) = Make(quickSeconds: 1);
        handler.Delay = TimeSpan.FromSeconds(10);
        var ex = await Assert.ThrowsAsync<GymAgentException>(() => client.GetAsync("wf-1", default));
        Assert.Equal(HttpStatusCode.GatewayTimeout, ex.Status);
    }

    [Fact]
    public async Task An_ai_call_gets_the_longer_timeout_that_a_quick_call_would_not_survive()
    {
        var (client, handler) = Make(quickSeconds: 1, aiSeconds: 10);
        handler.Delay = TimeSpan.FromSeconds(2);                              // longer than the quick timeout
        var result = await client.GetGymDetailsAsync(Gym(), default);
        Assert.Equal("ai-scraped", result.GetProperty("source").GetString());
    }

    [Fact]
    public async Task An_ai_call_that_exceeds_its_own_timeout_is_504()
    {
        var (client, handler) = Make(aiSeconds: 1);
        handler.Delay = TimeSpan.FromSeconds(10);
        var ex = await Assert.ThrowsAsync<GymAgentException>(() => client.GetGymDetailsAsync(Gym(), default));
        Assert.Equal(HttpStatusCode.GatewayTimeout, ex.Status);
    }

    [Fact]
    public async Task The_callers_own_cancellation_is_not_reported_as_a_gateway_timeout()
    {
        var (client, handler) = Make();
        handler.Delay = TimeSpan.FromSeconds(10);
        using var cts = new CancellationTokenSource(TimeSpan.FromMilliseconds(100));
        await Assert.ThrowsAnyAsync<OperationCanceledException>(() => client.GetGymDetailsAsync(Gym(), cts.Token));
    }

    [Theory]
    [InlineData(HttpStatusCode.BadGateway, HttpStatusCode.BadGateway)]           // enrichment failed upstream
    [InlineData(HttpStatusCode.UnprocessableEntity, HttpStatusCode.BadRequest)]  // upstream refused the input
    [InlineData(HttpStatusCode.Unauthorized, HttpStatusCode.BadGateway)]         // our own key is wrong: operator problem
    [InlineData(HttpStatusCode.ServiceUnavailable, HttpStatusCode.BadGateway)]
    public async Task Upstream_errors_are_mapped_without_leaking_detail(HttpStatusCode upstream, HttpStatusCode expected)
    {
        var (client, handler) = Make();
        handler.Status = upstream;
        handler.Json = "{\"detail\":\"Enrichment failed: Traceback C:\\\\secret\\\\path api_key=sk-123\"}";
        var ex = await Assert.ThrowsAsync<GymAgentException>(() => client.GetGymDetailsAsync(Gym(), default));
        Assert.Equal(expected, ex.Status);
        Assert.DoesNotContain("secret", ex.Message);
        Assert.DoesNotContain("sk-123", ex.Message);
    }
}
