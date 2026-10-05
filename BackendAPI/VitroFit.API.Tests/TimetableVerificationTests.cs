using System.Net;
using System.Text.Json;
using Microsoft.AspNetCore.Authentication;
using Microsoft.AspNetCore.Builder;
using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.TestHost;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using VitroFit.API.Data;
using VitroFit.API.Entities;
using VitroFit.API.Features.TimetableVerification;
using Xunit;

namespace VitroFit.API.Tests;

public sealed class TimetableSlotMapperTests
{
    private static JsonElement Parse(string json) => JsonDocument.Parse(json).RootElement.Clone();

    private const string OneSlot =
        "{\"week\":1,\"slots\":[{\"day\":1,\"startTime\":\"07:00\",\"endTime\":\"08:30\",\"focus\":\"Chest and triceps\",\"durationMinutes\":90,\"description\":\"Bench press, Tricep dips\"}]}";

    [Fact]
    public void A_valid_timetable_is_parsed()
    {
        var slots = TimetableSlotMapper.ParseSlots(Parse(OneSlot));

        var slot = Assert.Single(slots);
        Assert.Equal(1, slot.Day);
        Assert.Equal("07:00", slot.StartTime);
        Assert.Equal("08:30", slot.EndTime);
        Assert.Equal("Chest and triceps", slot.Focus);
        Assert.Equal(90, slot.DurationMinutes);
        Assert.Equal("Bench press, Tricep dips", slot.Description);
    }

    [Theory]
    [InlineData(1, DayOfWeek.Monday)]
    [InlineData(5, DayOfWeek.Friday)]
    [InlineData(6, DayOfWeek.Saturday)]
    [InlineData(7, DayOfWeek.Sunday)]   // the agent numbers Sunday 7, .NET numbers it 0
    public void Days_map_to_dayofweek(int day, DayOfWeek expected)
    {
        Assert.Equal(expected, TimetableSlotMapper.ToDayOfWeek(day));
    }

    [Theory]
    [InlineData("{\"slots\":[]}")]
    [InlineData("{}")]
    [InlineData("{\"slots\":\"nope\"}")]
    [InlineData("[]")]
    [InlineData("{\"slots\":[{\"day\":0,\"startTime\":\"07:00\",\"endTime\":\"08:00\",\"focus\":\"x\"}]}")]
    [InlineData("{\"slots\":[{\"day\":8,\"startTime\":\"07:00\",\"endTime\":\"08:00\",\"focus\":\"x\"}]}")]
    [InlineData("{\"slots\":[{\"day\":1,\"startTime\":\"25:00\",\"endTime\":\"08:00\",\"focus\":\"x\"}]}")]
    [InlineData("{\"slots\":[{\"day\":1,\"startTime\":\"soon\",\"endTime\":\"08:00\",\"focus\":\"x\"}]}")]
    [InlineData("{\"slots\":[1,2,3]}")]
    public void Unusable_timetables_are_rejected(string json)
    {
        Assert.Throws<InvalidOperationException>(() => TimetableSlotMapper.ParseSlots(Parse(json)));
    }

    [Fact]
    public void A_missing_timetable_is_rejected()
    {
        Assert.Throws<InvalidOperationException>(() => TimetableSlotMapper.ParseSlots(null));
    }

    [Fact]
    public void A_blank_focus_gets_a_default_and_long_text_is_cut_to_the_column_size()
    {
        var longFocus = new string('f', 300);
        var longDescription = new string('d', 900);
        var json = $"{{\"slots\":[{{\"day\":2,\"startTime\":\"06:00\",\"endTime\":\"07:00\",\"focus\":\"  \"}},"
                 + $"{{\"day\":3,\"startTime\":\"06:00\",\"endTime\":\"07:00\",\"focus\":\"{longFocus}\",\"description\":\"{longDescription}\"}}]}}";

        var slots = TimetableSlotMapper.ParseSlots(Parse(json));

        Assert.Equal("Adaptive Workout", slots[0].Focus);
        Assert.Equal(TimetableSlotMapper.MaxFocusLength, slots[1].Focus.Length);
        Assert.Equal(TimetableSlotMapper.MaxDescriptionLength, slots[1].Description!.Length);
    }

    [Fact]
    public void Duration_is_worked_out_when_the_agent_omits_it()
    {
        var json = "{\"slots\":[{\"day\":1,\"startTime\":\"07:00\",\"endTime\":\"08:15\",\"focus\":\"Legs\"}]}";
        Assert.Equal(75, TimetableSlotMapper.ParseSlots(Parse(json))[0].DurationMinutes);
    }

    [Fact]
    public void Slots_survive_a_round_trip_through_storage()
    {
        var slots = TimetableSlotMapper.ParseSlots(Parse(OneSlot));
        var back = TimetableSlotMapper.Deserialize(TimetableSlotMapper.Serialize(slots));
        Assert.Equal(slots, back);
    }

    [Fact]
    public void An_absurd_number_of_slots_is_rejected()
    {
        var one = "{\"day\":1,\"startTime\":\"07:00\",\"endTime\":\"08:00\",\"focus\":\"x\"}";
        var json = "{\"slots\":[" + string.Join(",", Enumerable.Repeat(one, TimetableSlotMapper.MaxSlots + 1)) + "]}";
        Assert.Throws<InvalidOperationException>(() => TimetableSlotMapper.ParseSlots(Parse(json)));
    }
}

public sealed class TimetableEmailsTests
{
    [Fact]
    public void User_supplied_text_is_html_encoded()
    {
        var (_, html) = TimetableEmails.Rejected("<b>Sam</b>", "Gym <script>x</script>", "<img src=x onerror=alert(1)>");

        Assert.DoesNotContain("<script>", html);
        Assert.DoesNotContain("<img", html);
        Assert.DoesNotContain("<b>Sam</b>", html);
        Assert.Contains("&lt;script&gt;", html);
    }

    [Fact]
    public void The_verified_email_names_the_reviewer_and_has_no_empty_note_block()
    {
        var (subject, html) = TimetableEmails.Verified("Sam", "Iron Works", null);

        Assert.Contains("verified", subject, StringComparison.OrdinalIgnoreCase);
        Assert.Contains("Iron Works", html);
        Assert.DoesNotContain("Note from the reviewer", html);
    }

    [Fact]
    public void A_rejection_includes_the_note()
    {
        var (_, html) = TimetableEmails.Rejected("Sam", "Iron Works", "Too many leg days in a row.");
        Assert.Contains("Too many leg days in a row.", html);
    }
}

/// <summary>
/// Who may call the verification endpoints. Authorization runs before a controller is created, so the database is
/// never reached and a placeholder connection string is enough. The queue logic itself is exercised against a real
/// database in the end-to-end run.
/// </summary>
public sealed class TimetableVerificationAuthTests : IAsyncLifetime
{
    private IHost _host = null!;
    private HttpClient _http = null!;

    private sealed class UnusedReviewService : ITimetableReviewService
    {
        public Task<TimetableProposal> CreateProposalAsync(CreateProposalInput input, CancellationToken ct) => throw new NotSupportedException();
        public Task<ReviewResult> ReviewAsync(int proposalId, int reviewerId, bool approve, string? note, CancellationToken ct) => throw new NotSupportedException();
        public Task<bool> CancelAsync(int userId, int proposalId, CancellationToken ct) => throw new NotSupportedException();
    }

    public async Task InitializeAsync()
    {
        _host = await new HostBuilder()
            .ConfigureWebHost(web =>
            {
                web.UseTestServer();
                web.ConfigureServices(services =>
                {
                    services.AddDbContext<AppDbContext>(o => o.UseNpgsql("Host=127.0.0.1;Port=1;Database=unused"));
                    services.AddSingleton<ITimetableReviewService, UnusedReviewService>();
                    services.AddControllers().AddApplicationPart(typeof(TimetableReviewsController).Assembly);
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

    private HttpRequestMessage Req(HttpMethod method, string url, string? user = null, string? role = null)
    {
        var msg = new HttpRequestMessage(method, url);
        if (user != null) msg.Headers.Add("X-Test-User", user);
        if (role != null) msg.Headers.Add("X-Test-Role", role);
        if (method == HttpMethod.Post) msg.Content = new StringContent("{}", System.Text.Encoding.UTF8, "application/json");
        return msg;
    }

    [Theory]
    [InlineData("GET", "/api/timetable-reviews")]
    [InlineData("GET", "/api/timetable-reviews/1")]
    [InlineData("POST", "/api/timetable-reviews/1/approve")]
    [InlineData("POST", "/api/timetable-reviews/1/reject")]
    [InlineData("GET", "/api/timetable/proposal")]
    [InlineData("POST", "/api/timetable/proposal/1/cancel")]
    [InlineData("GET", "/api/notifications")]
    [InlineData("POST", "/api/notifications/1/read")]
    [InlineData("POST", "/api/notifications/read-all")]
    public async Task Anonymous_callers_get_401(string method, string url)
    {
        var res = await _http.SendAsync(Req(new HttpMethod(method), url));
        Assert.Equal(HttpStatusCode.Unauthorized, res.StatusCode);
    }

    [Theory]
    [InlineData("User", "GET", "/api/timetable-reviews")]
    [InlineData("Trainer", "GET", "/api/timetable-reviews")]
    [InlineData("User", "GET", "/api/timetable-reviews/1")]
    [InlineData("User", "POST", "/api/timetable-reviews/1/approve")]
    [InlineData("Trainer", "POST", "/api/timetable-reviews/1/reject")]
    public async Task Only_gym_owners_and_admins_can_use_the_review_queue(string role, string method, string url)
    {
        var res = await _http.SendAsync(Req(new HttpMethod(method), url, "7", role));
        Assert.Equal(HttpStatusCode.Forbidden, res.StatusCode);
    }
}
