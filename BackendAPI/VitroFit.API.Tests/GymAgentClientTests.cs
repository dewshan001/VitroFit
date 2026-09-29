using System.Net;
using System.Text;
using System.Text.Json;
using Microsoft.Extensions.Logging.Abstractions;
using Microsoft.Extensions.Options;
using VitroFit.API.Features.GymAgent;
using VitroFit.API.Settings;

namespace VitroFit.API.Tests;

public sealed class GymAgentClientTests
{
    private const string Key = "0123456789abcdef0123456789abcdef";

    private sealed class StubHandler : HttpMessageHandler
    {
        public HttpRequestMessage? Last { get; private set; }
        public string? LastBody { get; private set; }
        public Func<HttpResponseMessage> Respond { get; set; } = () => new HttpResponseMessage(HttpStatusCode.OK);
        public Exception? Throw { get; set; }
        public int Calls { get; private set; }

        protected override async Task<HttpResponseMessage> SendAsync(HttpRequestMessage request, CancellationToken ct)
        {
            Calls++;
            Last = request;
            LastBody = request.Content == null ? null : await request.Content.ReadAsStringAsync(ct);
            if (Throw != null) throw Throw;
            return Respond();
        }
    }

    private static (GymAgentClient Client, StubHandler Handler) Make(string key = Key)
    {
        var handler = new StubHandler();
        var http = new HttpClient(handler) { BaseAddress = new Uri("http://agent.test") };
        var settings = Options.Create(new GymAgentSettings { ServiceKey = key });
        return (new GymAgentClient(http, settings, NullLogger<GymAgentClient>.Instance), handler);
    }

    private static HttpResponseMessage Json(HttpStatusCode code, string json)
        => new(code) { Content = new StringContent(json, Encoding.UTF8, "application/json") };

    [Fact]
    public async Task Sends_service_key_and_snake_case_body_and_omits_nulls()
    {
        var (client, handler) = Make();
        handler.Respond = () => Json(HttpStatusCode.Accepted, "{\"id\":\"wf-9\",\"status\":\"Running\"}");

        var started = await client.StartAsync(
            new StartGymWorkflowRequest { PlaceId = "p1", Name = "FitZone", KnownPhone = "123" }, "user-5", default);

        Assert.Equal("wf-9", started.Id);
        Assert.Equal(HttpMethod.Post, handler.Last!.Method);
        Assert.Equal("/internal/workflows", handler.Last.RequestUri!.AbsolutePath);
        Assert.Equal(Key, handler.Last.Headers.GetValues("X-Gym-Agent-Key").Single());

        using var body = JsonDocument.Parse(handler.LastBody!);
        var root = body.RootElement;
        Assert.Equal("p1", root.GetProperty("place_id").GetString());
        Assert.Equal("user-5", root.GetProperty("requested_by").GetString());
        Assert.Equal("123", root.GetProperty("known_phone").GetString());
        Assert.False(root.TryGetProperty("website", out _));
    }

    [Fact]
    public async Task Decision_is_forwarded_with_actor_identity()
    {
        var (client, handler) = Make();
        handler.Respond = () => Json(HttpStatusCode.Accepted, "{}");

        await client.DecideAsync("wf 1", new GymDecision("approve", "ok", "42", "Gym_Owner"), default);

        Assert.Equal("/internal/workflows/wf%201/decision", handler.Last!.RequestUri!.AbsolutePath.Replace(" ", "%20"));
        using var body = JsonDocument.Parse(handler.LastBody!);
        Assert.Equal("approve", body.RootElement.GetProperty("decision").GetString());
        Assert.Equal("42", body.RootElement.GetProperty("actor_id").GetString());
        Assert.Equal("Gym_Owner", body.RootElement.GetProperty("actor_role").GetString());
    }

    [Fact]
    public async Task Parses_camel_case_workflow_summary()
    {
        var (client, handler) = Make();
        handler.Respond = () => Json(HttpStatusCode.OK, """
            {"id":"wf-1","placeId":"p1","requestedBy":"7","objective":"o","status":"AwaitingApproval",
             "approvalStatus":"pending","retryCount":1,"plan":{"route":"scrape"},"facts":{"equipment":["a"]},
             "createdAt":"2026-09-01T10:00:00+00:00"}
            """);

        var wf = await client.GetAsync("wf-1", default);

        Assert.Equal("AwaitingApproval", wf.Status);
        Assert.Equal("7", wf.RequestedBy);
        Assert.Equal(1, wf.RetryCount);
        Assert.Equal("scrape", wf.Plan!.Value.GetProperty("route").GetString());
        Assert.NotNull(wf.CreatedAt);
    }

    [Fact]
    public async Task Builds_list_query_from_filters()
    {
        var (client, handler) = Make();
        handler.Respond = () => Json(HttpStatusCode.OK, "[]");
        await client.ListAsync("AwaitingApproval", "7", default);
        Assert.Equal("?status=AwaitingApproval&requestedBy=7", handler.Last!.RequestUri!.Query);
    }

    [Theory]
    [InlineData(HttpStatusCode.NotFound, HttpStatusCode.NotFound)]
    [InlineData(HttpStatusCode.Conflict, HttpStatusCode.Conflict)]
    [InlineData(HttpStatusCode.Forbidden, HttpStatusCode.Forbidden)]
    [InlineData(HttpStatusCode.UnprocessableEntity, HttpStatusCode.BadRequest)]
    [InlineData(HttpStatusCode.Unauthorized, HttpStatusCode.BadGateway)]   // our key is wrong: operator issue
    [InlineData(HttpStatusCode.InternalServerError, HttpStatusCode.BadGateway)]
    public async Task Maps_upstream_status_codes(HttpStatusCode upstream, HttpStatusCode expected)
    {
        var (client, handler) = Make();
        handler.Respond = () => Json(upstream, "{\"detail\":\"Workflow is Published, not awaiting approval\"}");

        var ex = await Assert.ThrowsAsync<GymAgentException>(() => client.GetAsync("wf-1", default));

        Assert.Equal(expected, ex.Status);
    }

    [Fact]
    public async Task Bad_gateway_message_does_not_leak_upstream_body()
    {
        var (client, handler) = Make();
        handler.Respond = () => Json(HttpStatusCode.InternalServerError, "{\"detail\":\"Traceback secret path C:\\\\x\"}");
        var ex = await Assert.ThrowsAsync<GymAgentException>(() => client.GetAsync("wf-1", default));
        Assert.DoesNotContain("secret", ex.Message);
    }

    [Fact]
    public async Task Unreachable_service_is_503()
    {
        var (client, handler) = Make();
        handler.Throw = new HttpRequestException("connection refused");
        var ex = await Assert.ThrowsAsync<GymAgentException>(() => client.GetAsync("wf-1", default));
        Assert.Equal(HttpStatusCode.ServiceUnavailable, ex.Status);
    }

    [Theory]
    [InlineData("")]
    [InlineData("too-short")]
    public async Task Missing_or_short_key_fails_before_any_request(string key)
    {
        var (client, handler) = Make(key);
        var ex = await Assert.ThrowsAsync<GymAgentException>(() => client.GetAsync("wf-1", default));
        Assert.Equal(HttpStatusCode.ServiceUnavailable, ex.Status);
        Assert.Equal(0, handler.Calls);
    }
}
