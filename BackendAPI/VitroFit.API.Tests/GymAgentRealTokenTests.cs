using System.IdentityModel.Tokens.Jwt;
using System.Net;
using System.Net.Http.Headers;
using System.Net.Http.Json;
using System.Text;
using Microsoft.AspNetCore.Authentication.JwtBearer;
using Microsoft.AspNetCore.Builder;
using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.TestHost;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Options;
using Microsoft.IdentityModel.Tokens;
using VitroFit.API.Entities;
using VitroFit.API.Features.GymAgent;
using VitroFit.API.Services;
using VitroFit.API.Settings;

namespace VitroFit.API.Tests;

/// <summary>
/// Regression: the real login token (built by the real TokenService) validated with the same JWT
/// bearer options as Program.cs. An earlier controller read only the "sub" claim, which is absent
/// under this app's claim mapping, so every signed-in call answered 401 "Unauthorized" even for
/// admins. The header-based fake login in GymAgentControllerTests could not see that.
/// </summary>
public sealed class GymAgentRealTokenTests : IAsyncLifetime
{
    private const string Secret = "unit-test-secret-unit-test-secret-unit-test-secret-1234";

    private IHost _host = null!;
    private HttpClient _http = null!;
    private TokenService _tokens = null!;
    private readonly FakeGymAgentClient _agent = new();

    public async Task InitializeAsync()
    {
        var jwt = new JwtSettings
        {
            Secret = Secret, Issuer = "VitroFitApi", Audience = "VitroFitWeb", AccessTokenExpirationMinutes = 60
        };
        _tokens = new TokenService(Options.Create(jwt));

        // Same process-wide switch Program.cs flips before building the app.
        JwtSecurityTokenHandler.DefaultInboundClaimTypeMap.Clear();

        _host = await new HostBuilder()
            .ConfigureWebHost(web =>
            {
                web.UseTestServer();
                web.ConfigureServices(services =>
                {
                    services.AddSingleton<IGymAgentClient>(_agent);
                    services.AddControllers().AddApplicationPart(typeof(GymAgentController).Assembly);
                    services.AddAuthorization();
                    services.AddAuthentication(o =>
                    {
                        o.DefaultAuthenticateScheme = JwtBearerDefaults.AuthenticationScheme;
                        o.DefaultChallengeScheme = JwtBearerDefaults.AuthenticationScheme;
                    })
                    .AddJwtBearer(o =>
                    {
                        // Copied from Program.cs.
                        o.RequireHttpsMetadata = false;
                        o.SaveToken = true;
                        o.TokenValidationParameters = new TokenValidationParameters
                        {
                            ValidateIssuer = true,
                            ValidateAudience = true,
                            ValidateLifetime = true,
                            ValidateIssuerSigningKey = true,
                            ValidIssuer = jwt.Issuer,
                            ValidAudience = jwt.Audience,
                            IssuerSigningKey = new SymmetricSecurityKey(Encoding.UTF8.GetBytes(Secret)),
                            NameClaimType = JwtRegisteredClaimNames.Sub,
                            RoleClaimType = "http://schemas.microsoft.com/ws/2008/06/identity/claims/role"
                        };
                    });
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

    private HttpRequestMessage Req(HttpMethod method, string url, UserRole? role, int userId = 1, object? body = null)
    {
        var msg = new HttpRequestMessage(method, url);
        if (role != null)
        {
            var token = _tokens.CreateAccessToken(new User
            {
                Id = userId, FirstName = "Test", LastName = "User", Email = "t@example.com", Role = role.Value
            });
            msg.Headers.Authorization = new AuthenticationHeaderValue("Bearer", token);
        }
        if (body != null) msg.Content = JsonContent.Create(body);
        return msg;
    }

    private static readonly object Start = new { placeId = "p1", name = "FitZone" };

    [Theory]
    [InlineData(UserRole.Admin)]
    [InlineData(UserRole.Gym_Owner)]
    [InlineData(UserRole.User)]
    public async Task Signed_in_users_can_start_and_their_id_is_read_from_the_real_token(UserRole role)
    {
        var res = await _http.SendAsync(Req(HttpMethod.Post, "/api/gym-agent/workflows", role, userId: 42, body: Start));

        Assert.Equal(HttpStatusCode.Accepted, res.StatusCode);
        Assert.Equal("42", _agent.StartedBy);
    }

    [Theory]
    [InlineData(UserRole.Admin)]
    [InlineData(UserRole.Gym_Owner)]
    public async Task Admin_and_gym_owner_tokens_can_approve_with_their_real_role_and_id(UserRole role)
    {
        var res = await _http.SendAsync(
            Req(HttpMethod.Post, "/api/gym-agent/workflows/wf-1/approve", role, userId: 7, body: new { reason = "ok" }));

        Assert.Equal(HttpStatusCode.Accepted, res.StatusCode);
        var (_, decision) = Assert.Single(_agent.Decisions);
        Assert.Equal("7", decision.ActorId);
        Assert.Equal(role.ToString(), decision.ActorRole);
    }

    [Theory]
    [InlineData(UserRole.User)]
    [InlineData(UserRole.Trainer)]
    public async Task Other_real_tokens_cannot_approve(UserRole role)
    {
        var res = await _http.SendAsync(
            Req(HttpMethod.Post, "/api/gym-agent/workflows/wf-1/approve", role, body: new { reason = "ok" }));

        Assert.Equal(HttpStatusCode.Forbidden, res.StatusCode);
        Assert.Empty(_agent.Decisions);
    }

    [Fact]
    public async Task Admin_token_can_open_the_pending_queue()
    {
        var res = await _http.SendAsync(Req(HttpMethod.Get, "/api/gym-agent/workflows/pending", UserRole.Admin));
        Assert.Equal(HttpStatusCode.OK, res.StatusCode);
    }

    [Fact]
    public async Task No_token_is_401()
    {
        var res = await _http.SendAsync(Req(HttpMethod.Get, "/api/gym-agent/workflows", role: null));
        Assert.Equal(HttpStatusCode.Unauthorized, res.StatusCode);
    }
}
