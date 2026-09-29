using System.Net;
using System.Text;
using Microsoft.Extensions.Logging.Abstractions;
using Microsoft.Extensions.Options;
using VitroFit.API.Features.GymAgent;
using VitroFit.API.Settings;

namespace VitroFit.API.Tests;

/// <summary>
/// Feeds payloads captured from the real Python service (running on PostgreSQL) through
/// GymAgentClient, so a rename on either side breaks a test instead of the admin page.
/// Regenerate fixtures by re-running a workflow and saving store.get()/events()/list_workflows().
/// </summary>
public sealed class GymAgentContractTests
{
    private sealed class Canned : HttpMessageHandler
    {
        private readonly string _json;
        public Canned(string json) => _json = json;

        protected override Task<HttpResponseMessage> SendAsync(HttpRequestMessage request, CancellationToken ct)
            => Task.FromResult(new HttpResponseMessage(HttpStatusCode.OK)
            {
                Content = new StringContent(_json, Encoding.UTF8, "application/json")
            });
    }

    private static GymAgentClient ClientReturning(string fixture)
    {
        var json = File.ReadAllText(Path.Combine(AppContext.BaseDirectory, "Fixtures", fixture));
        var http = new HttpClient(new Canned(json)) { BaseAddress = new Uri("http://agent.test") };
        var settings = Options.Create(new GymAgentSettings { ServiceKey = new string('k', 40) });
        return new GymAgentClient(http, settings, NullLogger<GymAgentClient>.Instance);
    }

    [Fact]
    public async Task Real_workflow_detail_maps_every_field_the_admin_page_uses()
    {
        var wf = await ClientReturning("workflow_detail.json").GetAsync("x", default);

        Assert.Equal("Published", wf.Status);
        Assert.Equal("FitZone", wf.GymName);
        Assert.Equal("https://fitzone.lk", wf.Website);
        Assert.Equal("approved", wf.ApprovalStatus);
        Assert.Equal("owner-9", wf.ApprovedBy);
        Assert.Equal("Admin", wf.ApproverRole);
        Assert.Equal("Verified on site", wf.ApprovalNote);
        Assert.NotNull(wf.DecidedAt);
        Assert.NotNull(wf.CreatedAt);

        Assert.Equal("scrape", wf.Plan!.Value.GetProperty("route").GetString());
        Assert.Equal(0.85, wf.Facts!.Value.GetProperty("confidence").GetDouble());
        Assert.Equal(4, wf.Recommendations!.Value.GetProperty("workouts").GetArrayLength());
        Assert.Equal("pass", wf.ValidationResults!.Value[0].GetProperty("verdict").GetString());

        var steps = wf.CompletedSteps!.Value;
        Assert.Equal(6, steps.GetArrayLength());
        Assert.Equal("publish", steps[5].GetProperty("agent").GetString());
        Assert.Equal(2, wf.ToolResults!.Value.GetArrayLength());
        Assert.True(wf.ToolResults!.Value[0].TryGetProperty("stepId", out _));
    }

    [Fact]
    public async Task Real_timeline_maps_to_event_dtos()
    {
        var events = await ClientReturning("workflow_events.json").GetEventsAsync("x", default);

        Assert.Equal(8, events.Count);                                   // 6 steps + 2 tool calls
        Assert.Equal("planner", events[0].Agent);
        var scrape = Assert.Single(events, e => e.Tool == "scrape_gym_website");
        Assert.True(scrape.Ok);
        Assert.Equal("https://fitzone.lk", scrape.InputSummary);
        Assert.All(events, e => Assert.True(e.DurationMs >= 0));
        Assert.Equal(events.Count, events.Select(e => e.Id).Distinct().Count());
    }

    [Fact]
    public async Task Injection_guard_flags_on_tool_calls_reach_the_event_dto()
    {
        var json = """
            [{"id":1,"agent":"gym_analysis","tool":"scrape_gym_website","ok":true,"durationMs":5,"error":null,
              "flags":"OVERRIDE_INSTRUCTIONS,EXFIL_LINK","inputSummary":"https://fitzone.lk","outputSummary":null,"createdAt":null},
             {"id":2,"agent":"planner","tool":null,"ok":true,"durationMs":0,"error":null,"flags":null,
              "inputSummary":null,"outputSummary":"Plan created","createdAt":null}]
            """;
        var events = await ClientReturningJson(json).GetEventsAsync("x", default);

        Assert.Equal("OVERRIDE_INSTRUCTIONS,EXFIL_LINK", events[0].Flags);
        Assert.Null(events[1].Flags);
    }

    private static GymAgentClient ClientReturningJson(string json)
    {
        var http = new HttpClient(new Canned(json)) { BaseAddress = new Uri("http://agent.test") };
        var settings = Options.Create(new GymAgentSettings { ServiceKey = new string('k', 40) });
        return new GymAgentClient(http, settings, NullLogger<GymAgentClient>.Instance);
    }

    [Fact]
    public async Task Real_list_payload_maps_and_omits_child_rows()
    {
        var list = await ClientReturning("workflow_list.json").ListAsync(null, null, default);

        var wf = Assert.Single(list);
        Assert.Equal("FitZone", wf.GymName);
        Assert.Null(wf.CompletedSteps);   // list view does not load steps/tool calls
    }
}
