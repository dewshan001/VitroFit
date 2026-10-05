using System.Net;
using System.Net.Http.Json;
using System.Text.Json;
using Microsoft.AspNetCore.Authentication;
using Microsoft.AspNetCore.Builder;
using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.TestHost;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using VitroFit.API.Features.GymAgent;

namespace VitroFit.API.Tests;

/// <summary>/api/gyms/*: the only public route to the AI. JWT required, any role, validated, rate limited.</summary>
public sealed class GymsControllerTests : IAsyncLifetime
{
    private IHost _host = null!;
    private HttpClient _http = null!;
    private readonly FakeGymAgentClient _agent = new();
    private int _permitsPerMinute = 1000;

    public async Task InitializeAsync() => await StartAsync();

    private async Task StartAsync()
    {
        if (_host != null) await DisposeAsync();
        _host = await new HostBuilder()
            .ConfigureWebHost(web =>
            {
                web.UseTestServer();
                web.ConfigureServices(services =>
                {
                    services.AddSingleton<IGymAgentClient>(_agent);
                    services.AddControllers().AddApplicationPart(typeof(GymsController).Assembly);
                    services.AddAuthentication("Test").AddScheme<AuthenticationSchemeOptions, HeaderAuthHandler>("Test", null);
                    services.AddAuthorization();
                    services.AddGymAgentRateLimiting(_permitsPerMinute);   // same policy Program.cs registers
                });
                web.Configure(app =>
                {
                    app.UseRouting();
                    app.UseAuthentication();
                    app.UseRateLimiter();                                   // same order as Program.cs
                    app.UseAuthorization();
                    app.UseEndpoints(e => e.MapControllers());
                });
            })
            .StartAsync();
        _http = _host.GetTestClient();
    }

    public async Task DisposeAsync()
    {
        _http?.Dispose();
        if (_host != null)
        {
            await _host.StopAsync();
            _host.Dispose();
        }
    }

    private static HttpRequestMessage Post(string url, object body, string? user = null, string? role = null)
    {
        var msg = new HttpRequestMessage(HttpMethod.Post, url) { Content = JsonContent.Create(body) };
        if (user != null) msg.Headers.Add("X-Test-User", user);
        if (role != null) msg.Headers.Add("X-Test-Role", role);
        return msg;
    }

    private static readonly object Details = new { placeId = "p1", name = "FitZone" };
    private static readonly object Workouts = new { placeId = "p1", name = "FitZone", equipment = new[] { "treadmill" }, classes = Array.Empty<string>() };

    // ── authentication and roles ────────────────────────────────────────

    [Theory]
    [InlineData("/api/gyms/details")]
    [InlineData("/api/gyms/workouts")]
    public async Task Logged_out_visitors_get_401_and_never_reach_the_agent(string url)
    {
        var res = await _http.SendAsync(Post(url, url.EndsWith("details") ? Details : Workouts));
        Assert.Equal(HttpStatusCode.Unauthorized, res.StatusCode);
        Assert.Null(_agent.LastDetails);
        Assert.Null(_agent.LastWorkouts);
    }

    [Theory]
    [InlineData("User")]
    [InlineData("Trainer")]
    [InlineData("Gym_Owner")]
    [InlineData("Admin")]
    public async Task Any_signed_in_role_can_read_details_and_workouts(string role)
    {
        var d = await _http.SendAsync(Post("/api/gyms/details", Details, "7", role));
        var w = await _http.SendAsync(Post("/api/gyms/workouts", Workouts, "7", role));
        Assert.Equal(HttpStatusCode.OK, d.StatusCode);
        Assert.Equal(HttpStatusCode.OK, w.StatusCode);
    }

    [Fact]
    public async Task The_python_answer_is_passed_through_unchanged()
    {
        var res = await _http.SendAsync(Post("/api/gyms/details", Details, "7", "User"));
        using var doc = JsonDocument.Parse(await res.Content.ReadAsStringAsync());
        Assert.Equal("ai-scraped", doc.RootElement.GetProperty("source").GetString());
        Assert.Equal("treadmill", doc.RootElement.GetProperty("equipment")[0].GetString());
    }

    // ── input validation: the agent only ever sees validated data ───────

    [Fact]
    public async Task Camel_case_body_is_mapped_to_the_request_sent_upstream()
    {
        var body = new
        {
            placeId = "p9", name = "Gym", lat = 7.25, lng = 80.59, address = "A", website = "https://g.lk",
            phone = "0112223333", email = "a@g.lk", openingHours = "Mo-Su 06:00-22:00"
        };
        await _http.SendAsync(Post("/api/gyms/details", body, "7", "User"));
        var sent = _agent.LastDetails!;
        Assert.Equal(("p9", "Gym", 7.25, 80.59), (sent.PlaceId, sent.Name, sent.Lat, sent.Lng));
        Assert.Equal("Mo-Su 06:00-22:00", sent.OpeningHours);
    }

    [Theory]
    [InlineData("{\"placeId\":\"\",\"name\":\"x\"}")]
    [InlineData("{\"placeId\":\"p\"}")]
    [InlineData("{\"placeId\":\"p\",\"name\":\"x\",\"lat\":91}")]
    [InlineData("{\"placeId\":\"p\",\"name\":\"x\",\"lng\":-181}")]
    public async Task Invalid_details_requests_are_400(string json)
    {
        var msg = Post("/api/gyms/details", new { }, "7", "User");
        msg.Content = new StringContent(json, System.Text.Encoding.UTF8, "application/json");
        var res = await _http.SendAsync(msg);
        Assert.Equal(HttpStatusCode.BadRequest, res.StatusCode);
        Assert.Null(_agent.LastDetails);
    }

    [Fact]
    public async Task Oversized_text_fields_are_400()
    {
        foreach (var body in new object[]
        {
            new { placeId = new string('x', 256), name = "n" },
            new { placeId = "p", name = "n", address = new string('x', 501) },
            new { placeId = "p", name = "n", phone = new string('1', 51) },
        })
        {
            var res = await _http.SendAsync(Post("/api/gyms/details", body, "7", "User"));
            Assert.Equal(HttpStatusCode.BadRequest, res.StatusCode);
        }
        Assert.Null(_agent.LastDetails);
    }

    [Fact]
    public async Task Workout_lists_are_bounded()
    {
        var tooMany = new { placeId = "p", name = "n", equipment = Enumerable.Range(0, 61).Select(i => $"item {i}").ToArray() };
        var tooLong = new { placeId = "p", name = "n", classes = new[] { new string('x', 81) } };
        Assert.Equal(HttpStatusCode.BadRequest, (await _http.SendAsync(Post("/api/gyms/workouts", tooMany, "7", "User"))).StatusCode);
        Assert.Equal(HttpStatusCode.BadRequest, (await _http.SendAsync(Post("/api/gyms/workouts", tooLong, "7", "User"))).StatusCode);
        Assert.Null(_agent.LastWorkouts);

        var ok = new { placeId = "p", name = "n", equipment = Enumerable.Range(0, 60).Select(i => $"item {i}").ToArray() };
        Assert.Equal(HttpStatusCode.OK, (await _http.SendAsync(Post("/api/gyms/workouts", ok, "7", "User"))).StatusCode);
    }

    // ── upstream failures are mapped, never leaked ──────────────────────

    [Theory]
    [InlineData(HttpStatusCode.ServiceUnavailable)]
    [InlineData(HttpStatusCode.GatewayTimeout)]
    [InlineData(HttpStatusCode.BadGateway)]
    [InlineData(HttpStatusCode.BadRequest)]
    public async Task Agent_failures_become_problem_details_with_the_mapped_status(HttpStatusCode upstream)
    {
        _agent.Fail = new GymAgentException(upstream, "boom");
        var res = await _http.SendAsync(Post("/api/gyms/details", Details, "7", "User"));
        Assert.Equal(upstream, res.StatusCode);
        Assert.Contains("problem", res.Content.Headers.ContentType?.MediaType ?? "");
        var text = await res.Content.ReadAsStringAsync();
        Assert.DoesNotContain("Traceback", text);
    }

    // ── rate limiting ───────────────────────────────────────────────────

    [Fact]
    public async Task Users_are_limited_per_minute_and_each_user_has_their_own_allowance()
    {
        _permitsPerMinute = 3;
        await StartAsync();

        for (var i = 0; i < 3; i++)
            Assert.Equal(HttpStatusCode.OK, (await _http.SendAsync(Post("/api/gyms/details", Details, "7", "User"))).StatusCode);

        var limited = await _http.SendAsync(Post("/api/gyms/details", Details, "7", "User"));
        Assert.Equal(HttpStatusCode.TooManyRequests, limited.StatusCode);
        Assert.True(limited.Headers.Contains("Retry-After"));
        Assert.Contains("problem", limited.Content.Headers.ContentType?.MediaType ?? "");

        // another user is unaffected, and the limit covers workouts as well as details
        Assert.Equal(HttpStatusCode.OK, (await _http.SendAsync(Post("/api/gyms/details", Details, "8", "User"))).StatusCode);
        Assert.Equal(HttpStatusCode.TooManyRequests, (await _http.SendAsync(Post("/api/gyms/workouts", Workouts, "7", "User"))).StatusCode);
    }

    [Fact]
    public async Task Rejected_requests_never_reach_the_agent()
    {
        _permitsPerMinute = 1;
        await StartAsync();
        await _http.SendAsync(Post("/api/gyms/details", Details, "7", "User"));
        _agent.ResetLast();
        await _http.SendAsync(Post("/api/gyms/details", Details, "7", "User"));
        Assert.Null(_agent.LastDetails);
    }
}
