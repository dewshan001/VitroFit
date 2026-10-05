using System.Net;
using System.Text;
using Microsoft.Extensions.Logging.Abstractions;
using Microsoft.Extensions.Options;
using VitroFit.API.Features.DietAgent;
using VitroFit.API.Settings;

namespace VitroFit.API.Tests;

public sealed class DietAgentClientTests
{
    private const string Key = "0123456789abcdef0123456789abcdef";

    private sealed class StubHandler : HttpMessageHandler
    {
        public HttpRequestMessage? Last { get; private set; }
        public string? LastBody { get; private set; }
        public Func<HttpResponseMessage> Respond { get; set; } = () => new HttpResponseMessage(HttpStatusCode.OK);
        public Exception? Throw { get; set; }
        public TimeSpan Delay { get; set; }

        protected override async Task<HttpResponseMessage> SendAsync(HttpRequestMessage request, CancellationToken ct)
        {
            Last = request;
            LastBody = request.Content == null ? null : await request.Content.ReadAsStringAsync(ct);
            if (Delay > TimeSpan.Zero) await Task.Delay(Delay, ct);
            if (Throw != null) throw Throw;
            return Respond();
        }
    }

    private static (DietAgentClient Client, StubHandler Handler) Make(string key = Key, int timeoutSeconds = 30)
    {
        var handler = new StubHandler();
        var http = new HttpClient(handler) { BaseAddress = new Uri("http://diet.test") };
        var settings = Options.Create(new DietAgentSettings { ServiceKey = key, TimeoutSeconds = timeoutSeconds });
        return (new DietAgentClient(http, settings, NullLogger<DietAgentClient>.Instance), handler);
    }

    private static HttpResponseMessage Json(HttpStatusCode code, string json)
        => new(code) { Content = new StringContent(json, Encoding.UTF8, "application/json") };

    private static DietAgentRequest Post(string path, string? body = "{\"age\":30}", string? auth = "Bearer abc")
        => new(HttpMethod.Post, path, auth, body == null ? null : Encoding.UTF8.GetBytes(body), "application/json");

    [Fact]
    public async Task Forwards_method_path_query_body_token_and_the_service_key()
    {
        var (client, handler) = Make();
        handler.Respond = () => Json(HttpStatusCode.OK, "{\"workflowId\":\"w1\"}");

        var response = await client.ForwardAsync(Post("/api/diet/generate?x=1"), default);

        Assert.Equal(HttpStatusCode.OK, response.Status);
        Assert.Equal("{\"workflowId\":\"w1\"}", Encoding.UTF8.GetString(response.Body));
        Assert.Equal(HttpMethod.Post, handler.Last!.Method);
        Assert.Equal("/api/diet/generate", handler.Last.RequestUri!.AbsolutePath);
        Assert.Equal("?x=1", handler.Last.RequestUri.Query);
        Assert.Equal("{\"age\":30}", handler.LastBody);
        Assert.Equal(Key, handler.Last.Headers.GetValues(DietAgentClient.KeyHeader).Single());
        Assert.Equal("Bearer abc", handler.Last.Headers.GetValues("Authorization").Single());
        Assert.Equal("application/json", handler.Last.Content!.Headers.ContentType!.MediaType);
    }

    [Fact]
    public async Task Without_a_configured_key_no_key_header_is_sent_so_the_service_works_as_before()
    {
        var (client, handler) = Make(key: "");

        await client.ForwardAsync(Post("/api/diet/plans", body: null), default);

        Assert.False(handler.Last!.Headers.Contains(DietAgentClient.KeyHeader));
        Assert.Null(handler.Last.Content);
    }

    [Fact]
    public async Task A_key_that_is_too_short_fails_closed_without_calling_the_service()
    {
        var (client, handler) = Make(key: "short");

        var ex = await Assert.ThrowsAsync<DietAgentException>(() => client.ForwardAsync(Post("/api/diet/plans"), default));

        Assert.Equal(HttpStatusCode.ServiceUnavailable, ex.Status);
        Assert.Null(handler.Last);
    }

    [Theory]
    [InlineData(HttpStatusCode.OK)]
    [InlineData(HttpStatusCode.NoContent)]
    [InlineData(HttpStatusCode.NotFound)]
    [InlineData(HttpStatusCode.Conflict)]
    [InlineData(HttpStatusCode.Forbidden)]
    [InlineData(HttpStatusCode.UnprocessableEntity)]
    public async Task The_services_answer_is_returned_unchanged(HttpStatusCode status)
    {
        var (client, handler) = Make();
        var body = status == HttpStatusCode.NoContent ? "" : "{\"detail\":\"Plain text the web app shows as is.\"}";
        handler.Respond = () => status == HttpStatusCode.NoContent ? new HttpResponseMessage(status) : Json(status, body);

        var response = await client.ForwardAsync(new DietAgentRequest(HttpMethod.Get, "/api/diet/plans/1", "Bearer abc", null, null), default);

        Assert.Equal(status, response.Status);
        Assert.Equal(body, Encoding.UTF8.GetString(response.Body));
    }

    [Theory]
    [InlineData(HttpStatusCode.Unauthorized)]
    [InlineData(HttpStatusCode.ServiceUnavailable)]
    public async Task A_service_that_refuses_our_own_call_is_reported_as_a_bad_gateway_not_a_user_error(HttpStatusCode upstream)
    {
        var (client, handler) = Make();
        handler.Respond = () => Json(upstream, "{\"detail\":\"Invalid or missing service key.\"}");

        var ex = await Assert.ThrowsAsync<DietAgentException>(() => client.ForwardAsync(Post("/api/diet/plans"), default));

        Assert.Equal(HttpStatusCode.BadGateway, ex.Status);
        Assert.DoesNotContain("key", ex.Message, StringComparison.OrdinalIgnoreCase);   // nothing about the upstream leaks
    }

    [Fact]
    public async Task An_unreachable_service_is_a_503()
    {
        var (client, handler) = Make();
        handler.Throw = new HttpRequestException("connection refused: secret-host:8003");

        var ex = await Assert.ThrowsAsync<DietAgentException>(() => client.ForwardAsync(Post("/api/diet/plans"), default));

        Assert.Equal(HttpStatusCode.ServiceUnavailable, ex.Status);
        Assert.DoesNotContain("secret-host", ex.Message);
    }

    [Fact]
    public async Task A_slow_service_is_a_504()
    {
        var (client, handler) = Make(timeoutSeconds: 1);
        handler.Delay = TimeSpan.FromSeconds(5);

        var ex = await Assert.ThrowsAsync<DietAgentException>(() => client.ForwardAsync(Post("/api/diet/plans"), default));

        Assert.Equal(HttpStatusCode.GatewayTimeout, ex.Status);
    }

    [Fact]
    public async Task A_caller_who_goes_away_is_not_reported_as_a_timeout()
    {
        var (client, handler) = Make();
        handler.Delay = TimeSpan.FromSeconds(5);
        using var cts = new CancellationTokenSource(TimeSpan.FromMilliseconds(50));

        await Assert.ThrowsAnyAsync<OperationCanceledException>(() => client.ForwardAsync(Post("/api/diet/plans"), cts.Token));
    }
}
