using System.Net;
using System.Text;
using System.Text.Json;
using Microsoft.AspNetCore.Authentication;
using Microsoft.AspNetCore.Builder;
using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.TestHost;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using VitroFit.API.Features.DietAgent;

namespace VitroFit.API.Tests;

/// <summary>Records what the controller passes on and returns canned answers, so the proxy rules run without Python.</summary>
public sealed class FakeDietAgentClient : IDietAgentClient
{
    public List<DietAgentRequest> Requests { get; } = new();
    public Func<DietAgentRequest, DietAgentResponse> Respond { get; set; } =
        _ => new DietAgentResponse(HttpStatusCode.OK, Encoding.UTF8.GetBytes("{\"ok\":true}"), "application/json; charset=utf-8");
    public DietAgentException? Fail { get; set; }

    public Task<DietAgentResponse> ForwardAsync(DietAgentRequest request, CancellationToken ct)
    {
        if (Fail != null) throw Fail;
        Requests.Add(request);
        return Task.FromResult(Respond(request));
    }
}

public sealed class DietAgentControllerTests : IAsyncLifetime
{
    private IHost _host = null!;
    private HttpClient _http = null!;
    private readonly FakeDietAgentClient _agent = new();

    public async Task InitializeAsync()
    {
        _host = await new HostBuilder()
            .ConfigureWebHost(web =>
            {
                web.UseTestServer();
                web.ConfigureServices(services =>
                {
                    services.AddSingleton<IDietAgentClient>(_agent);
                    services.AddControllers().AddApplicationPart(typeof(DietAgentController).Assembly);
                    services.AddAuthentication("Test").AddScheme<AuthenticationSchemeOptions, HeaderAuthHandler>("Test", null);
                    services.AddAuthorization();
                    services.AddDietAgentRateLimiting(permitsPerMinute: 3);
                });
                web.Configure(app =>
                {
                    app.UseRouting();
                    app.UseAuthentication();
                    app.UseRateLimiter();
                    app.UseAuthorization();
                    app.UseEndpoints(e => e.MapControllers());
                });
            })
            .StartAsync();
        _http = _host.GetTestClient();
    }

    public async Task DisposeAsync()
    {
        _http.Dispose();
        await _host.StopAsync();
        _host.Dispose();
    }

    private static HttpRequestMessage Req(HttpMethod method, string url, string? user = "7", string? body = null, string? bearer = "token-abc")
    {
        var msg = new HttpRequestMessage(method, url);
        if (user != null) msg.Headers.Add("X-Test-User", user);
        if (bearer != null) msg.Headers.TryAddWithoutValidation("Authorization", $"Bearer {bearer}");
        if (body != null) msg.Content = new StringContent(body, Encoding.UTF8, "application/json");
        return msg;
    }

    // ── authentication ──────────────────────────────────────────────────

    [Theory]
    [InlineData("POST", "/api/diet/generate")]
    [InlineData("GET", "/api/diet/plans")]
    [InlineData("POST", "/api/diet/confirm")]
    [InlineData("PUT", "/api/diet/plans/1")]
    [InlineData("DELETE", "/api/diet/plans/1")]
    [InlineData("GET", "/api/diet/approvals/pending")]
    [InlineData("POST", "/api/diet/workflows/0a1b2c3d-0000-0000-0000-000000000000/approve")]
    [InlineData("POST", "/api/diet/workflows/0a1b2c3d-0000-0000-0000-000000000000/refine")]
    [InlineData("GET", "/api/diet/workflows/0a1b2c3d-0000-0000-0000-000000000000/trace")]
    public async Task Anonymous_callers_get_401_and_nothing_is_passed_on(string method, string url)
    {
        var res = await _http.SendAsync(Req(new HttpMethod(method), url, user: null, body: method is "POST" or "PUT" ? "{}" : null));

        Assert.Equal(HttpStatusCode.Unauthorized, res.StatusCode);
        Assert.Empty(_agent.Requests);
    }

    // ── pass-through ────────────────────────────────────────────────────

    [Theory]
    [InlineData("GET", "/api/diet/plans", "/api/diet/plans")]
    [InlineData("GET", "/api/diet/plans/12", "/api/diet/plans/12")]
    [InlineData("PUT", "/api/diet/plans/12", "/api/diet/plans/12")]
    [InlineData("DELETE", "/api/diet/plans/12", "/api/diet/plans/12")]
    [InlineData("POST", "/api/diet/confirm", "/api/diet/confirm")]
    [InlineData("GET", "/api/diet/approvals/pending", "/api/diet/approvals/pending")]
    [InlineData("GET", "/api/diet/workflows/0a1b2c3d-0000-0000-0000-000000000000", "/api/diet/workflows/0a1b2c3d-0000-0000-0000-000000000000")]
    [InlineData("GET", "/api/diet/workflows/0a1b2c3d-0000-0000-0000-000000000000/trace", "/api/diet/workflows/0a1b2c3d-0000-0000-0000-000000000000/trace")]
    [InlineData("POST", "/api/diet/workflows/0a1b2c3d-0000-0000-0000-000000000000/approve?note=ok", "/api/diet/workflows/0a1b2c3d-0000-0000-0000-000000000000/approve?note=ok")]
    [InlineData("POST", "/api/diet/workflows/0a1b2c3d-0000-0000-0000-000000000000/reject?note=no", "/api/diet/workflows/0a1b2c3d-0000-0000-0000-000000000000/reject?note=no")]
    public async Task Every_diet_route_is_passed_on_with_the_same_method_path_and_query(string method, string url, string expected)
    {
        var res = await _http.SendAsync(Req(new HttpMethod(method), url, body: method is "POST" or "PUT" ? "{\"a\":1}" : null));

        Assert.Equal(HttpStatusCode.OK, res.StatusCode);
        var forwarded = Assert.Single(_agent.Requests);
        Assert.Equal(new HttpMethod(method), forwarded.Method);
        Assert.Equal(expected, forwarded.PathAndQuery);
    }

    [Fact]
    public async Task Generate_and_refine_are_passed_on_with_the_body_and_the_callers_token()
    {
        var body = "{\"age\":30,\"dislikes\":\"onions\"}";
        await _http.SendAsync(Req(HttpMethod.Post, "/api/diet/generate", body: body, bearer: "my-jwt"));
        await _http.SendAsync(Req(HttpMethod.Post, "/api/diet/workflows/0a1b2c3d-0000-0000-0000-000000000000/refine", body: "{\"instruction\":\"swap rice\"}"));

        Assert.Equal(2, _agent.Requests.Count);
        Assert.Equal("/api/diet/generate", _agent.Requests[0].PathAndQuery);
        Assert.Equal(body, Encoding.UTF8.GetString(_agent.Requests[0].Body!));
        Assert.Equal("Bearer my-jwt", _agent.Requests[0].Authorization);
        Assert.StartsWith("application/json", _agent.Requests[0].ContentType);
        Assert.Equal("/api/diet/workflows/0a1b2c3d-0000-0000-0000-000000000000/refine", _agent.Requests[1].PathAndQuery);
    }

    [Theory]
    [InlineData(HttpStatusCode.OK, "{\"workflowId\":\"w1\",\"status\":\"running\"}")]
    [InlineData(HttpStatusCode.Conflict, "{\"detail\":\"This plan needs Trainer/Admin approval before it can be saved.\"}")]
    [InlineData(HttpStatusCode.UnprocessableEntity, "{\"detail\":\"Your dislikes note contains text that looks like an instruction to the AI.\"}")]
    [InlineData(HttpStatusCode.NotFound, "{\"detail\":\"Diet plan not found.\"}")]
    public async Task The_services_status_and_body_come_back_unchanged(HttpStatusCode status, string json)
    {
        _agent.Respond = _ => new DietAgentResponse(status, Encoding.UTF8.GetBytes(json), "application/json");

        var res = await _http.SendAsync(Req(HttpMethod.Post, "/api/diet/confirm", body: "{}"));

        Assert.Equal(status, res.StatusCode);
        Assert.Equal(json, await res.Content.ReadAsStringAsync());
        Assert.Equal("application/json", res.Content.Headers.ContentType!.MediaType);
    }

    [Fact]
    public async Task A_204_comes_back_empty()
    {
        _agent.Respond = _ => new DietAgentResponse(HttpStatusCode.NoContent, Array.Empty<byte>(), null);

        var res = await _http.SendAsync(Req(HttpMethod.Delete, "/api/diet/plans/3"));

        Assert.Equal(HttpStatusCode.NoContent, res.StatusCode);
        Assert.Empty(await res.Content.ReadAsByteArrayAsync());
    }

    // ── only the diet API is reachable ──────────────────────────────────

    [Theory]
    [InlineData("/api/diet/docs")]
    [InlineData("/api/diet/openapi.json")]
    [InlineData("/api/diet/health")]
    [InlineData("/api/diet/plans/abc")]
    [InlineData("/api/diet/plans/1/extra")]
    [InlineData("/api/diet/workflows")]
    [InlineData("/api/diet/workflows/not_a_uuid!/trace")]
    [InlineData("/api/diet/workflows/0a1b2c3d/delete")]
    [InlineData("/api/diet/generate/extra")]
    [InlineData("/api/diet/..%2Fhealth")]
    [InlineData("/api/diet/plans%2F..%2F..%2Fdocs")]
    public async Task Anything_that_is_not_a_diet_route_is_404_and_never_reaches_the_service(string url)
    {
        var res = await _http.SendAsync(Req(HttpMethod.Get, url));

        Assert.Equal(HttpStatusCode.NotFound, res.StatusCode);
        Assert.Empty(_agent.Requests);
    }

    // ── errors of the hop itself ────────────────────────────────────────

    [Theory]
    [InlineData(HttpStatusCode.ServiceUnavailable, "The diet service is unavailable.")]
    [InlineData(HttpStatusCode.GatewayTimeout, "The diet service took too long to respond.")]
    [InlineData(HttpStatusCode.BadGateway, "The diet service could not be reached securely.")]
    public async Task Hop_failures_become_problem_details_whose_detail_the_web_app_can_show(HttpStatusCode status, string message)
    {
        _agent.Fail = new DietAgentException(status, message);

        var res = await _http.SendAsync(Req(HttpMethod.Get, "/api/diet/plans"));

        Assert.Equal(status, res.StatusCode);
        using var doc = JsonDocument.Parse(await res.Content.ReadAsStringAsync());
        Assert.Equal(message, doc.RootElement.GetProperty("detail").GetString());
    }

    // ── limits ──────────────────────────────────────────────────────────

    [Fact]
    public async Task Oversized_bodies_are_refused_before_they_are_passed_on()
    {
        var huge = new string('x', DietAgentController.MaxBodyBytes + 10);

        var res = await _http.SendAsync(Req(HttpMethod.Post, "/api/diet/confirm", body: huge));

        Assert.Equal(HttpStatusCode.RequestEntityTooLarge, res.StatusCode);
        Assert.Empty(_agent.Requests);
    }

    [Fact]
    public async Task Generate_is_rate_limited_per_user_and_other_users_are_unaffected()
    {
        for (var i = 0; i < 3; i++)
        {
            var ok = await _http.SendAsync(Req(HttpMethod.Post, "/api/diet/generate", user: "7", body: "{}"));
            Assert.Equal(HttpStatusCode.OK, ok.StatusCode);
        }

        var limited = await _http.SendAsync(Req(HttpMethod.Post, "/api/diet/generate", user: "7", body: "{}"));
        var otherUser = await _http.SendAsync(Req(HttpMethod.Post, "/api/diet/generate", user: "8", body: "{}"));

        Assert.Equal(HttpStatusCode.TooManyRequests, limited.StatusCode);
        Assert.Equal(HttpStatusCode.OK, otherUser.StatusCode);
        Assert.Equal(4, _agent.Requests.Count);   // the limited call never reached the service
    }

    [Fact]
    public async Task Refine_shares_the_limit_but_reading_progress_and_saving_do_not_count()
    {
        for (var i = 0; i < 20; i++)
        {
            await _http.SendAsync(Req(HttpMethod.Get, "/api/diet/workflows/0a1b2c3d-0000-0000-0000-000000000000"));
        }
        for (var i = 0; i < 3; i++)
        {
            var ok = await _http.SendAsync(Req(HttpMethod.Post, "/api/diet/workflows/0a1b2c3d-0000-0000-0000-000000000000/refine", user: "9", body: "{}"));
            Assert.Equal(HttpStatusCode.OK, ok.StatusCode);
        }

        var limited = await _http.SendAsync(Req(HttpMethod.Post, "/api/diet/workflows/0a1b2c3d-0000-0000-0000-000000000000/refine", user: "9", body: "{}"));

        Assert.Equal(HttpStatusCode.TooManyRequests, limited.StatusCode);
    }
}
