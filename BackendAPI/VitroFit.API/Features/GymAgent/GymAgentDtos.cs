using System.ComponentModel.DataAnnotations;
using System.Text.Json;

namespace VitroFit.API.Features.GymAgent
{
    /// <summary>Objective for the gym multi-agent workflow. The workflow always runs for one map place.</summary>
    public sealed class StartGymWorkflowRequest
    {
        [Required, StringLength(255, MinimumLength = 1)]
        public string PlaceId { get; set; } = string.Empty;

        [Required, StringLength(255, MinimumLength = 1)]
        public string Name { get; set; } = string.Empty;

        [StringLength(500)] public string? Address { get; set; }
        [StringLength(500)] public string? Website { get; set; }
        [StringLength(50)] public string? KnownPhone { get; set; }
        [EmailAddress, StringLength(255)] public string? KnownEmail { get; set; }
        [StringLength(255)] public string? KnownHours { get; set; }

        [Range(-90, 90)] public double? Lat { get; set; }
        [Range(-180, 180)] public double? Lng { get; set; }
    }

    /// <summary>Reviewer's note. Mandatory for "revise" so the agents know what to change.</summary>
    public sealed class ReviewRequest
    {
        [StringLength(500)]
        public string? Reason { get; set; }
    }

    /// <summary>Execution summary of one workflow, as stored by the agent service (no hidden reasoning).</summary>
    public sealed class GymWorkflowDto
    {
        public string Id { get; set; } = string.Empty;
        public string PlaceId { get; set; } = string.Empty;
        public string? GymName { get; set; }
        public string? Website { get; set; }
        public string RequestedBy { get; set; } = string.Empty;
        public string Objective { get; set; } = string.Empty;
        public string Status { get; set; } = string.Empty;
        public string ApprovalStatus { get; set; } = string.Empty;
        public string? ApprovedBy { get; set; }
        public string? ApproverRole { get; set; }
        public DateTimeOffset? DecidedAt { get; set; }
        public string? ApprovalNote { get; set; }
        public string? FinalOutcome { get; set; }
        public int RetryCount { get; set; }
        public JsonElement? Plan { get; set; }
        public JsonElement? CompletedSteps { get; set; }
        public JsonElement? ToolResults { get; set; }
        public JsonElement? Facts { get; set; }
        public JsonElement? Recommendations { get; set; }
        public JsonElement? ValidationResults { get; set; }
        public JsonElement? Errors { get; set; }
        public DateTimeOffset? CreatedAt { get; set; }
        public DateTimeOffset? UpdatedAt { get; set; }
    }

    public sealed class GymWorkflowEventDto
    {
        public int Id { get; set; }
        public string Agent { get; set; } = string.Empty;
        public string? Tool { get; set; }
        public bool Ok { get; set; }
        public int DurationMs { get; set; }
        public string? Error { get; set; }
        public string? InputSummary { get; set; }
        public string? OutputSummary { get; set; }
        public DateTimeOffset? CreatedAt { get; set; }
    }

    public sealed class StartedWorkflowDto
    {
        public string Id { get; set; } = string.Empty;
        public string Status { get; set; } = string.Empty;
    }

    /// <summary>Reviewer decision forwarded to the agent service with the verified identity of the caller.</summary>
    public sealed record GymDecision(string Decision, string? Reason, string ActorId, string ActorRole);
}
