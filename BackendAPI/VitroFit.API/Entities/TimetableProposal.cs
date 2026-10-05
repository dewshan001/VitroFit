using System.ComponentModel.DataAnnotations;

namespace VitroFit.API.Entities
{
    public enum TimetableProposalStatus
    {
        /// <summary>Generated and waiting for a gym owner (or admin) to verify it.</summary>
        Pending = 0,
        Approved = 1,
        Rejected = 2,
        /// <summary>The user withdrew the request.</summary>
        Cancelled = 3,
        /// <summary>The user generated a newer timetable before this one was reviewed.</summary>
        Superseded = 4
    }

    /// <summary>
    /// An AI-generated weekly timetable held until a gym owner verifies it. Nothing touches the user's real
    /// <see cref="TimetableSlot"/> rows until it is approved.
    /// </summary>
    public class TimetableProposal
    {
        public int Id { get; set; }

        public int UserId { get; set; }
        public User? User { get; set; }

        /// <summary>The fitness workflow (workout plan) this timetable was built from.</summary>
        public Guid WorkflowId { get; set; }

        /// <summary>The proposed slots as JSON (day 1-7, startTime, endTime, focus, durationMinutes, description).</summary>
        [Required]
        public string SlotsJson { get; set; } = "[]";

        [MaxLength(4000)]
        public string? LongTermImpact { get; set; }

        [MaxLength(1000)]
        public string? Preferences { get; set; }

        // A snapshot of what the reviewer needs to judge the plan. Deliberately no email, phone, age or weight.
        [MaxLength(100)]
        public string Goal { get; set; } = string.Empty;
        public int DaysPerWeek { get; set; }
        public int SessionMinutes { get; set; }
        public List<string> Equipment { get; set; } = new();

        public TimetableProposalStatus Status { get; set; } = TimetableProposalStatus.Pending;

        /// <summary>The reviewer's note; required when rejecting.</summary>
        [MaxLength(500)]
        public string? ReviewNote { get; set; }

        public int? ReviewedByUserId { get; set; }

        /// <summary>Who verified it, as shown to the user (the owner's gym name, or the VitroFit team).</summary>
        [MaxLength(200)]
        public string? ReviewerName { get; set; }

        public DateTime? ReviewedAt { get; set; }

        public DateTime CreatedAt { get; set; } = DateTime.UtcNow;
    }

    /// <summary>A message shown in the user's notification bell.</summary>
    public class UserNotification
    {
        public int Id { get; set; }

        public int UserId { get; set; }
        public User? User { get; set; }

        /// <summary>Short machine-readable kind, e.g. "timetable.verified".</summary>
        [Required, MaxLength(50)]
        public string Type { get; set; } = string.Empty;

        [Required, MaxLength(150)]
        public string Title { get; set; } = string.Empty;

        [Required, MaxLength(600)]
        public string Message { get; set; } = string.Empty;

        /// <summary>Site-relative page the notification opens, e.g. "/timetable".</summary>
        [MaxLength(200)]
        public string? LinkUrl { get; set; }

        public bool IsRead { get; set; }

        public DateTime CreatedAt { get; set; } = DateTime.UtcNow;
    }
}
