using System.IdentityModel.Tokens.Jwt;
using System.Security.Claims;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using VitroFit.API.Data;
using VitroFit.API.Entities;

namespace VitroFit.API.Features.TimetableVerification
{
    public sealed class ReviewTimetableRequest
    {
        /// <summary>Optional when approving, required when rejecting.</summary>
        public string? Note { get; set; }
    }

    public sealed record TimetableProposalDto(
        int Id,
        string Status,
        IReadOnlyList<ProposedSlot> Slots,
        string? LongTermImpact,
        string? ReviewNote,
        string? ReviewerName,
        DateTime? ReviewedAt,
        DateTime CreatedAt);

    public sealed record TimetableReviewSummaryDto(
        int Id,
        string MemberName,
        string Goal,
        int DaysPerWeek,
        int SessionMinutes,
        int SlotCount,
        string Status,
        string? ReviewerName,
        DateTime? ReviewedAt,
        DateTime CreatedAt);

    /// <summary>What a reviewer may see about the member: no email, phone, age or weight.</summary>
    public sealed record TimetableReviewDetailDto(
        int Id,
        string Status,
        string MemberName,
        string Goal,
        int DaysPerWeek,
        int SessionMinutes,
        IReadOnlyList<string> Equipment,
        string? Preferences,
        string? LongTermImpact,
        IReadOnlyList<ProposedSlot> Slots,
        string? ReviewNote,
        string? ReviewerName,
        DateTime? ReviewedAt,
        DateTime CreatedAt);

    internal static class CallerId
    {
        public static int? Of(ClaimsPrincipal user)
        {
            var value = user.FindFirstValue(ClaimTypes.NameIdentifier)
                        ?? user.FindFirstValue(JwtRegisteredClaimNames.Sub)
                        ?? user.FindFirstValue("sub");
            return int.TryParse(value, out var id) ? id : null;
        }
    }

    /// <summary>The member's own view of their timetable request.</summary>
    [ApiController]
    [Route("api/timetable/proposal")]
    [Authorize]
    public sealed class TimetableProposalController : ControllerBase
    {
        private readonly AppDbContext _db;
        private readonly ITimetableReviewService _reviews;

        public TimetableProposalController(AppDbContext db, ITimetableReviewService reviews)
        {
            _db = db;
            _reviews = reviews;
        }

        /// <summary>The latest request that is waiting or was decided (null when there is none).</summary>
        [HttpGet]
        public async Task<IActionResult> Latest(CancellationToken ct)
        {
            if (CallerId.Of(User) is not int userId) return Unauthorized();

            var proposal = await _db.TimetableProposals.AsNoTracking()
                .Where(p => p.UserId == userId
                    && (p.Status == TimetableProposalStatus.Pending
                        || p.Status == TimetableProposalStatus.Approved
                        || p.Status == TimetableProposalStatus.Rejected))
                .OrderByDescending(p => p.CreatedAt)
                .FirstOrDefaultAsync(ct);

            return Ok(new { proposal = proposal == null ? null : ToDto(proposal) });
        }

        [HttpPost("{id:int}/cancel")]
        public async Task<IActionResult> Cancel(int id, CancellationToken ct)
        {
            if (CallerId.Of(User) is not int userId) return Unauthorized();
            return await _reviews.CancelAsync(userId, id, ct)
                ? Ok(new { id, status = "Cancelled" })
                : NotFound(new { error = "There is no pending request to cancel." });
        }

        internal static TimetableProposalDto ToDto(TimetableProposal p) => new(
            p.Id, p.Status.ToString(), TimetableSlotMapper.Deserialize(p.SlotsJson), p.LongTermImpact,
            p.ReviewNote, p.ReviewerName, p.ReviewedAt, p.CreatedAt);
    }

    /// <summary>The shared verification queue for approved gym owners and admins.</summary>
    [ApiController]
    [Route("api/timetable-reviews")]
    [Authorize(Roles = "Gym_Owner,Admin")]
    public sealed class TimetableReviewsController : ControllerBase
    {
        private readonly AppDbContext _db;
        private readonly ITimetableReviewService _reviews;

        public TimetableReviewsController(AppDbContext db, ITimetableReviewService reviews)
        {
            _db = db;
            _reviews = reviews;
        }

        private bool IsAdmin => User.IsInRole("Admin");

        /// <summary>Requests, newest first. ?status=Pending (default) | Approved | Rejected.</summary>
        [HttpGet]
        public async Task<IActionResult> List([FromQuery] string? status, CancellationToken ct)
        {
            if (CallerId.Of(User) is not int me) return Unauthorized();

            var wanted = TimetableProposalStatus.Pending;
            if (!string.IsNullOrWhiteSpace(status)
                && (!Enum.TryParse(status, ignoreCase: true, out wanted)
                    || wanted is TimetableProposalStatus.Cancelled or TimetableProposalStatus.Superseded))
            {
                return BadRequest(new { error = "Status must be Pending, Approved or Rejected." });
            }

            var visible = _db.TimetableProposals.AsNoTracking()
                .Where(p => IsAdmin || p.UserId != me); // owners never see their own requests

            var rows = await visible
                .Where(p => p.Status == wanted)
                .OrderByDescending(p => p.CreatedAt)
                .Take(200)
                .Select(p => new { p.Id, p.User!.FirstName, p.Goal, p.DaysPerWeek, p.SessionMinutes, p.SlotsJson, p.Status, p.ReviewerName, p.ReviewedAt, p.CreatedAt })
                .ToListAsync(ct);

            var counts = await visible
                .Where(p => p.Status == TimetableProposalStatus.Pending
                         || p.Status == TimetableProposalStatus.Approved
                         || p.Status == TimetableProposalStatus.Rejected)
                .GroupBy(p => p.Status)
                .Select(g => new { Status = g.Key, Count = g.Count() })
                .ToListAsync(ct);

            return Ok(new
            {
                items = rows.Select(r => new TimetableReviewSummaryDto(
                    r.Id, r.FirstName, r.Goal, r.DaysPerWeek, r.SessionMinutes,
                    TimetableSlotMapper.Deserialize(r.SlotsJson).Count,
                    r.Status.ToString(), r.ReviewerName, r.ReviewedAt, r.CreatedAt)),
                counts = new
                {
                    pending = counts.FirstOrDefault(c => c.Status == TimetableProposalStatus.Pending)?.Count ?? 0,
                    approved = counts.FirstOrDefault(c => c.Status == TimetableProposalStatus.Approved)?.Count ?? 0,
                    rejected = counts.FirstOrDefault(c => c.Status == TimetableProposalStatus.Rejected)?.Count ?? 0
                }
            });
        }

        [HttpGet("{id:int}")]
        public async Task<IActionResult> Get(int id, CancellationToken ct)
        {
            if (CallerId.Of(User) is not int me) return Unauthorized();

            var p = await _db.TimetableProposals.AsNoTracking()
                .Include(x => x.User)
                .SingleOrDefaultAsync(x => x.Id == id && (IsAdmin || x.UserId != me), ct);
            if (p?.User == null) return NotFound(new { error = "Request not found." });

            return Ok(new TimetableReviewDetailDto(
                p.Id, p.Status.ToString(), p.User.FirstName, p.Goal, p.DaysPerWeek, p.SessionMinutes, p.Equipment,
                p.Preferences, p.LongTermImpact, TimetableSlotMapper.Deserialize(p.SlotsJson),
                p.ReviewNote, p.ReviewerName, p.ReviewedAt, p.CreatedAt));
        }

        [HttpPost("{id:int}/approve")]
        public Task<IActionResult> Approve(int id, [FromBody] ReviewTimetableRequest? body, CancellationToken ct)
            => Decide(id, approve: true, body?.Note, ct);

        [HttpPost("{id:int}/reject")]
        public Task<IActionResult> Reject(int id, [FromBody] ReviewTimetableRequest? body, CancellationToken ct)
            => Decide(id, approve: false, body?.Note, ct);

        private async Task<IActionResult> Decide(int id, bool approve, string? note, CancellationToken ct)
        {
            if (CallerId.Of(User) is not int me) return Unauthorized();
            if (note is { Length: > 500 })
                return BadRequest(new { error = "The note must be 500 characters or fewer." });

            var result = await _reviews.ReviewAsync(id, me, approve, note, ct);
            return result.Outcome switch
            {
                ReviewOutcome.Done => Ok(new { id, status = approve ? "Approved" : "Rejected", warning = result.Warning }),
                ReviewOutcome.NotFound => NotFound(new { error = "Request not found." }),
                ReviewOutcome.Conflict => Conflict(new { error = "Someone else has already reviewed this timetable." }),
                ReviewOutcome.SelfReview => StatusCode(StatusCodes.Status403Forbidden, new { error = "You cannot verify your own timetable." }),
                ReviewOutcome.NoteRequired => BadRequest(new { error = "Please tell the member why the timetable was not verified." }),
                _ => StatusCode(StatusCodes.Status500InternalServerError)
            };
        }
    }

    public sealed record NotificationDto(int Id, string Type, string Title, string Message, string? LinkUrl, bool IsRead, DateTime CreatedAt);

    /// <summary>The bell: the signed-in user's own notifications only.</summary>
    [ApiController]
    [Route("api/notifications")]
    [Authorize]
    public sealed class NotificationsController : ControllerBase
    {
        private readonly AppDbContext _db;

        public NotificationsController(AppDbContext db)
        {
            _db = db;
        }

        [HttpGet]
        public async Task<IActionResult> List(CancellationToken ct)
        {
            if (CallerId.Of(User) is not int me) return Unauthorized();

            var items = await _db.UserNotifications.AsNoTracking()
                .Where(n => n.UserId == me)
                .OrderByDescending(n => n.CreatedAt)
                .Take(30)
                .Select(n => new NotificationDto(n.Id, n.Type, n.Title, n.Message, n.LinkUrl, n.IsRead, n.CreatedAt))
                .ToListAsync(ct);
            var unread = await _db.UserNotifications.CountAsync(n => n.UserId == me && !n.IsRead, ct);

            return Ok(new { items, unreadCount = unread });
        }

        [HttpPost("{id:int}/read")]
        public async Task<IActionResult> MarkRead(int id, CancellationToken ct)
        {
            if (CallerId.Of(User) is not int me) return Unauthorized();

            var changed = await _db.UserNotifications
                .Where(n => n.Id == id && n.UserId == me)
                .ExecuteUpdateAsync(s => s.SetProperty(n => n.IsRead, true), ct);
            return changed > 0 ? NoContent() : NotFound();
        }

        [HttpPost("read-all")]
        public async Task<IActionResult> MarkAllRead(CancellationToken ct)
        {
            if (CallerId.Of(User) is not int me) return Unauthorized();

            await _db.UserNotifications
                .Where(n => n.UserId == me && !n.IsRead)
                .ExecuteUpdateAsync(s => s.SetProperty(n => n.IsRead, true), ct);
            return NoContent();
        }
    }
}
