using System.Net;
using System.Net.Http.Json;
using System.Security.Claims;
using System.Text.Encodings.Web;
using Microsoft.AspNetCore.Authentication;
using Microsoft.AspNetCore.Builder;
using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.TestHost;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Logging;
using Microsoft.Extensions.Options;
using VitroFit.API.Features.GymAgent;

namespace VitroFit.API.Tests;

/// <summary>Records calls and returns canned data, so controller rules can be tested without Python.</summary>
public sealed class FakeGymAgentClient : IGymAgentClient
{
    public Dictionary<string, GymWorkflowDto> Workflows { get; } = new();
    public List<(string Id, GymDecision Decision)> Decisions { get; } = new();
    public List<(string? Status, string? RequestedBy)> Lists { get; } = new();
    public string? StartedBy { get; private set; }
    public GymAgentException? Fail { get; set; }

    public Task<StartedWorkflowDto> StartAsync(StartGymWorkflowRequest request, string requestedBy, CancellationToken ct)
    {
        if (Fail != null) throw Fail;
        StartedBy = requestedBy;
        return Task.FromResult(new StartedWorkflowDto { Id = "wf-1", Status = "Running" });
    }

    public Task<GymWorkflowDto> GetAsync(string id, CancellationToken ct)
    {
        if (Fail != null) throw Fail;
        return Workflows.TryGetValue(id, out var w)
            ? Task.FromResult(w)
            : throw new GymAgentException(HttpStatusCode.NotFound, "Workflow not found.");
    }

    public Task<IReadOnlyList<GymWorkflowEventDto>> GetEventsAsync(string id, CancellationToken ct)
        => Task.FromResult<IReadOnlyList<GymWorkflowEventDto>>(new[] { new GymWorkflowEventDto { Agent = "planner", Ok = true } });

    public Task<IReadOnlyList<GymWorkflowDto>> ListAsync(string? status, string? requestedBy, CancellationToken ct)
    {
        Lists.Add((status, requestedBy));
        return Task.FromResult<IReadOnlyList<GymWorkflowDto>>(Workflows.Values.ToList());
    }

    public Task DecideAsync(string id, GymDecision decision, CancellationToken ct)
    {
        if (Fail != null) throw Fail;
        Decisions.Add((id, decision));
        return Task.CompletedTask;
    }
}

/// <summary>Test auth: identity comes from X-Test-User / X-Test-Role headers, absent = anonymous.</summary>
public sealed class HeaderAuthHandler : AuthenticationHandler<AuthenticationSchemeOptions>
{
    public HeaderAuthHandler(IOptionsMonitor<AuthenticationSchemeOptions> options, ILoggerFactory logger, UrlEncoder encoder)
        : base(options, logger, encoder) { }

    protected override Task<AuthenticateResult> HandleAuthenticateAsync()
    {
        if (!Request.Headers.TryGetValue("X-Test-User", out var user))
            return Task.FromResult(AuthenticateResult.NoResult());

        var claims = new List<Claim> { new("sub", user.ToString()) };
        if (Request.Headers.TryGetValue("X-Test-Role", out var role))
            claims.Add(new Claim(ClaimTypes.Role, role.ToString()));

        var identity = new ClaimsIdentity(claims, "Test", "sub", ClaimTypes.Role);
        return Task.FromResult(AuthenticateResult.Success(
            new AuthenticationTicket(new ClaimsPrincipal(identity), "Test")));
    }
}

public sealed class GymAgentControllerTests : IAsyncLifetime
{
    private IHost _host = null!;
    private HttpClient _http = null!;
    private readonly FakeGymAgentClient _agent = new();

    public async Task InitializeAsync()
    {
        _host = await new HostBuilder()
            .ConfigureWebHost(web =>
            {
                web.UseTestServer();
                web.ConfigureServices(services =>
                {
                    services.AddSingleton<IGymAgentClient>(_agent);
                    services.AddControllers().AddApplicationPart(typeof(GymAgentController).Assembly);
                    services.AddAuthentication("Test").AddScheme<AuthenticationSchemeOptions, HeaderAuthHandler>("Test", null);
                    services.AddAuthorization();
                });
                web.Configure(app =>
                {
                    app.UseRouting();
                    app.UseAuthentication();
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

    private HttpRequestMessage Req(HttpMethod method, string url, string? user = null, string? role = null, object? body = null)
    {
        var msg = new HttpRequestMessage(method, url);
        if (user != null) msg.Headers.Add("X-Test-User", user);
        if (role != null) msg.Headers.Add("X-Test-Role", role);
        if (body != null) msg.Content = JsonContent.Create(body);
        return msg;
    }

    private static GymWorkflowDto Wf(string id, string requestedBy) => new()
    {
        Id = id, PlaceId = "p1", RequestedBy = requestedBy, Status = "AwaitingApproval", ApprovalStatus = "pending"
    };

    private static readonly object ValidStart = new { placeId = "p1", name = "FitZone", website = "https://fitzone.lk" };

    // ── authentication ──────────────────────────────────────────────────

    [Theory]
    [InlineData("GET", "/api/gym-agent/workflows")]
    [InlineData("GET", "/api/gym-agent/workflows/pending")]
    [InlineData("GET", "/api/gym-agent/workflows/wf-1")]
    [InlineData("GET", "/api/gym-agent/workflows/wf-1/events")]
    [InlineData("POST", "/api/gym-agent/workflows")]
    [InlineData("POST", "/api/gym-agent/workflows/wf-1/approve")]
    public async Task Anonymous_callers_get_401(string method, string url)
    {
        var res = await _http.SendAsync(Req(new HttpMethod(method), url, body: method == "POST" ? ValidStart : null));
        Assert.Equal(HttpStatusCode.Unauthorized, res.StatusCode);
    }

    // ── role-based authorization on the approval endpoints ──────────────

    [Theory]
    [InlineData("User", "approve")]
    [InlineData("Trainer", "approve")]
    [InlineData("User", "reject")]
    [InlineData("Trainer", "revise")]
    public async Task Non_approvers_cannot_decide(string role, string action)
    {
        var res = await _http.SendAsync(Req(HttpMethod.Post, $"/api/gym-agent/workflows/wf-1/{action}", "7", role, new { reason = "x" }));
        Assert.Equal(HttpStatusCode.Forbidden, res.StatusCode);
        Assert.Empty(_agent.Decisions);
    }

    [Theory]
    [InlineData("User")]
    [InlineData("Trainer")]
    public async Task Non_approvers_cannot_see_the_approval_queue(string role)
    {
        var res = await _http.SendAsync(Req(HttpMethod.Get, "/api/gym-agent/workflows/pending", "7", role));
        Assert.Equal(HttpStatusCode.Forbidden, res.StatusCode);
    }

    [Theory]
    [InlineData("Gym_Owner", "approve")]
    [InlineData("Admin", "approve")]
    [InlineData("Admin", "reject")]
    public async Task Approvers_decision_carries_identity_from_the_token(string role, string action)
    {
        var res = await _http.SendAsync(Req(HttpMethod.Post, $"/api/gym-agent/workflows/wf-1/{action}", "42", role, new { reason = "fine" }));
        Assert.Equal(HttpStatusCode.Accepted, res.StatusCode);

        var (id, decision) = Assert.Single(_agent.Decisions);
        Assert.Equal("wf-1", id);
        Assert.Equal(action, decision.Decision);
        Assert.Equal("42", decision.ActorId);
        Assert.Equal(role, decision.ActorRole);
        Assert.Equal("fine", decision.Reason);
    }

    [Fact]
    public async Task Caller_cannot_spoof_identity_through_the_body()
    {
        var body = new { reason = "ok", actorId = "1", actorRole = "Admin" };
        await _http.SendAsync(Req(HttpMethod.Post, "/api/gym-agent/workflows/wf-1/approve", "42", "Gym_Owner", body));
        var (_, decision) = Assert.Single(_agent.Decisions);
        Assert.Equal("42", decision.ActorId);
        Assert.Equal("Gym_Owner", decision.ActorRole);
    }

    [Fact]
    public async Task Revise_requires_a_reason()
    {
        var none = await _http.SendAsync(Req(HttpMethod.Post, "/api/gym-agent/workflows/wf-1/revise", "1", "Admin", new { }));
        Assert.Equal(HttpStatusCode.BadRequest, none.StatusCode);
        var blank = await _http.SendAsync(Req(HttpMethod.Post, "/api/gym-agent/workflows/wf-1/revise", "1", "Admin", new { reason = "  " }));
        Assert.Equal(HttpStatusCode.BadRequest, blank.StatusCode);
        Assert.Empty(_agent.Decisions);

        var ok = await _http.SendAsync(Req(HttpMethod.Post, "/api/gym-agent/workflows/wf-1/revise", "1", "Admin", new { reason = "add a low-impact option" }));
        Assert.Equal(HttpStatusCode.Accepted, ok.StatusCode);
    }

    [Fact]
    public async Task Overlong_reason_is_rejected()
    {
        var res = await _http.SendAsync(Req(HttpMethod.Post, "/api/gym-agent/workflows/wf-1/reject", "1", "Admin", new { reason = new string('x', 501) }));
        Assert.Equal(HttpStatusCode.BadRequest, res.StatusCode);
    }

    // ── starting ────────────────────────────────────────────────────────

    [Fact]
    public async Task Any_signed_in_user_can_start_and_is_recorded_as_requester()
    {
        var res = await _http.SendAsync(Req(HttpMethod.Post, "/api/gym-agent/workflows", "7", "User", ValidStart));
        Assert.Equal(HttpStatusCode.Accepted, res.StatusCode);
        Assert.Equal("7", _agent.StartedBy);
        Assert.NotNull(res.Headers.Location);
    }

    [Fact]
    public async Task Full_body_from_the_find_gyms_button_is_accepted()
    {
        // Exactly the fields buildVerificationRequest() (VitroFit_web) can send, in camelCase.
        var body = new
        {
            placeId = "51a1b2c3", name = "University Gymnasium", address = "Peradeniya, Sri Lanka",
            website = "https://example.lk", knownPhone = "+94 81 238 8000", knownEmail = "gym@example.lk",
            knownHours = "Mo-Su 06:00-22:00", lat = 7.2547, lng = 80.5977
        };
        var res = await _http.SendAsync(Req(HttpMethod.Post, "/api/gym-agent/workflows", "1", "Admin", body));
        Assert.Equal(HttpStatusCode.Accepted, res.StatusCode);
        Assert.Equal("1", _agent.StartedBy);
    }

    [Fact]
    public async Task Duplicate_run_conflict_reaches_the_client_as_409()
    {
        _agent.Fail = new GymAgentException(HttpStatusCode.Conflict, "A workflow for this gym is already active");
        var res = await _http.SendAsync(Req(HttpMethod.Post, "/api/gym-agent/workflows", "1", "Admin", ValidStart));
        Assert.Equal(HttpStatusCode.Conflict, res.StatusCode);
    }

    [Theory]
    [InlineData("{\"placeId\":\"\",\"name\":\"x\"}")]
    [InlineData("{\"placeId\":\"p\",\"name\":\"\"}")]
    [InlineData("{\"placeId\":\"p\",\"name\":\"x\",\"knownEmail\":\"nope\"}")]
    [InlineData("{\"placeId\":\"p\",\"name\":\"x\",\"lat\":123}")]
    public async Task Invalid_start_requests_are_400(string json)
    {
        var msg = Req(HttpMethod.Post, "/api/gym-agent/workflows", "7", "User");
        msg.Content = new StringContent(json, System.Text.Encoding.UTF8, "application/json");
        var res = await _http.SendAsync(msg);
        Assert.Equal(HttpStatusCode.BadRequest, res.StatusCode);
        Assert.Null(_agent.StartedBy);
    }

    // ── visibility ──────────────────────────────────────────────────────

    [Fact]
    public async Task Users_only_see_their_own_workflows()
    {
        _agent.Workflows["mine"] = Wf("mine", "7");
        _agent.Workflows["theirs"] = Wf("theirs", "8");

        Assert.Equal(HttpStatusCode.OK, (await _http.SendAsync(Req(HttpMethod.Get, "/api/gym-agent/workflows/mine", "7", "User"))).StatusCode);
        Assert.Equal(HttpStatusCode.NotFound, (await _http.SendAsync(Req(HttpMethod.Get, "/api/gym-agent/workflows/theirs", "7", "User"))).StatusCode);
        Assert.Equal(HttpStatusCode.NotFound, (await _http.SendAsync(Req(HttpMethod.Get, "/api/gym-agent/workflows/theirs/events", "7", "User"))).StatusCode);
    }

    [Fact]
    public async Task Approvers_can_view_any_workflow_and_events()
    {
        _agent.Workflows["theirs"] = Wf("theirs", "8");
        Assert.Equal(HttpStatusCode.OK, (await _http.SendAsync(Req(HttpMethod.Get, "/api/gym-agent/workflows/theirs", "1", "Gym_Owner"))).StatusCode);
        Assert.Equal(HttpStatusCode.OK, (await _http.SendAsync(Req(HttpMethod.Get, "/api/gym-agent/workflows/theirs/events", "1", "Admin"))).StatusCode);
    }

    [Fact]
    public async Task List_is_scoped_to_the_caller_unless_an_approver_asks_for_all()
    {
        await _http.SendAsync(Req(HttpMethod.Get, "/api/gym-agent/workflows?all=true", "7", "User"));
        await _http.SendAsync(Req(HttpMethod.Get, "/api/gym-agent/workflows?all=true", "1", "Admin"));
        await _http.SendAsync(Req(HttpMethod.Get, "/api/gym-agent/workflows/pending", "1", "Gym_Owner"));

        Assert.Equal((null, "7"), _agent.Lists[0]);          // user forced to self even with all=true
        Assert.Equal((null, null), _agent.Lists[1]);          // approver sees everything
        Assert.Equal(("AwaitingApproval", null), _agent.Lists[2]);
    }

    // ── upstream failure mapping ────────────────────────────────────────

    [Theory]
    [InlineData(HttpStatusCode.Conflict)]
    [InlineData(HttpStatusCode.ServiceUnavailable)]
    [InlineData(HttpStatusCode.BadGateway)]
    public async Task Agent_service_failures_map_to_problem_details(HttpStatusCode upstream)
    {
        _agent.Fail = new GymAgentException(upstream, "boom");
        var res = await _http.SendAsync(Req(HttpMethod.Post, "/api/gym-agent/workflows/wf-1/approve", "1", "Admin", new { }));
        Assert.Equal(upstream, res.StatusCode);
        Assert.Contains("problem", res.Content.Headers.ContentType?.MediaType ?? "");
    }
}
