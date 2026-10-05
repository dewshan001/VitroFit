using System.IdentityModel.Tokens.Jwt;
using System.Security.Claims;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using VitroFit.API.Data;
using VitroFit.API.Entities;
using VitroFit.API.Services;

namespace VitroFit.API.Features.GymOwners
{
    public sealed class ReviewGymApplicationRequest
    {
        /// <summary>Optional when approving, required when rejecting.</summary>
        public string? Note { get; set; }
    }

    public sealed record GymApplicationSummaryDto(
        int Id,
        string GymName,
        string City,
        string OwnerName,
        string OwnerEmail,
        string Status,
        DateTime CreatedAt);

    public sealed record GymApplicationDetailDto(
        int Id,
        string Status,
        string GymName,
        string OwnerRole,
        string Description,
        string Address,
        string City,
        string GymPhone,
        string ContactEmail,
        string Website,
        string? OpeningHours,
        IReadOnlyList<string> Equipment,
        IReadOnlyList<string> Classes,
        IReadOnlyList<string> GymPhotoUrls,
        IReadOnlyList<string> EquipmentPhotoUrls,
        string? LicenseUrl,
        string OwnerName,
        string OwnerEmail,
        string? OwnerPhone,
        bool OwnerEmailVerified,
        string? ReviewNote,
        DateTime? ReviewedAt,
        DateTime CreatedAt,
        DateTime UpdatedAt);

    /// <summary>Admin review queue for gym owner applications.</summary>
    [ApiController]
    [Route("api/admin/gym-applications")]
    [Authorize(Roles = "Admin")]
    public sealed class GymApplicationsAdminController : ControllerBase
    {
        private readonly AppDbContext _context;
        private readonly IEmailService _email;
        private readonly ILogger<GymApplicationsAdminController> _logger;

        public GymApplicationsAdminController(
            AppDbContext context, IEmailService email, ILogger<GymApplicationsAdminController> logger)
        {
            _context = context;
            _email = email;
            _logger = logger;
        }

        /// <summary>Applications, newest first. Filter with ?status=Pending|Approved|Rejected.</summary>
        [HttpGet]
        public async Task<IActionResult> List([FromQuery] string? status)
        {
            var query = _context.GymApplications.AsNoTracking().AsQueryable();

            if (!string.IsNullOrWhiteSpace(status))
            {
                if (!Enum.TryParse<GymApplicationStatus>(status, ignoreCase: true, out var parsed))
                    return BadRequest(new { error = "Status must be Pending, Approved or Rejected." });
                query = query.Where(a => a.Status == parsed);
            }

            var rows = await query
                .OrderByDescending(a => a.CreatedAt)
                .Select(a => new
                {
                    a.Id, a.GymName, a.City, a.Status, a.CreatedAt,
                    a.User!.FirstName, a.User.LastName, a.User.Email
                })
                .ToListAsync();

            var counts = await _context.GymApplications
                .GroupBy(a => a.Status)
                .Select(g => new { Status = g.Key, Count = g.Count() })
                .ToListAsync();

            return Ok(new
            {
                items = rows.Select(r => new GymApplicationSummaryDto(
                    r.Id, r.GymName, r.City, $"{r.FirstName} {r.LastName}".Trim(), r.Email, r.Status.ToString(), r.CreatedAt)),
                counts = new
                {
                    pending = counts.FirstOrDefault(c => c.Status == GymApplicationStatus.Pending)?.Count ?? 0,
                    approved = counts.FirstOrDefault(c => c.Status == GymApplicationStatus.Approved)?.Count ?? 0,
                    rejected = counts.FirstOrDefault(c => c.Status == GymApplicationStatus.Rejected)?.Count ?? 0
                }
            });
        }

        [HttpGet("{id:int}")]
        public async Task<IActionResult> Get(int id)
        {
            var application = await _context.GymApplications.AsNoTracking()
                .Include(a => a.User)
                .SingleOrDefaultAsync(a => a.Id == id);
            return application == null
                ? NotFound(new { error = "Application not found." })
                : Ok(ToDetail(application));
        }

        [HttpPost("{id:int}/approve")]
        public Task<IActionResult> Approve(int id, [FromBody] ReviewGymApplicationRequest? review)
            => Decide(id, GymApplicationStatus.Approved, review?.Note);

        [HttpPost("{id:int}/reject")]
        public Task<IActionResult> Reject(int id, [FromBody] ReviewGymApplicationRequest? review)
            => Decide(id, GymApplicationStatus.Rejected, review?.Note);

        private async Task<IActionResult> Decide(int id, GymApplicationStatus decision, string? rawNote)
        {
            var note = string.IsNullOrWhiteSpace(rawNote) ? null : rawNote.Trim();
            if (decision == GymApplicationStatus.Rejected && note == null)
                return BadRequest(new { error = "Please give the owner a reason for rejecting the application." });
            if (note is { Length: > 500 })
                return BadRequest(new { error = "The note must be 500 characters or fewer." });

            var application = await _context.GymApplications
                .Include(a => a.User)
                .SingleOrDefaultAsync(a => a.Id == id);
            if (application?.User == null)
                return NotFound(new { error = "Application not found." });

            if (application.Status == decision)
                return Conflict(new { error = $"This application is already {decision.ToString().ToLowerInvariant()}." });

            application.Status = decision;
            application.ReviewNote = note;
            application.ReviewedByUserId = CurrentUserId();
            application.ReviewedAt = DateTime.UtcNow;
            application.UpdatedAt = DateTime.UtcNow;

            await _context.SaveChangesAsync();

            // A failed email must not undo the decision; report it so the admin can follow up.
            string? emailWarning = null;
            try
            {
                var (subject, html) = decision == GymApplicationStatus.Approved
                    ? GymApplicationEmails.Approved(application.User, application)
                    : GymApplicationEmails.Rejected(application.User, application);
                await _email.SendAsync(application.User.Email, application.User.FirstName, subject, html);
            }
            catch (Exception ex)
            {
                _logger.LogWarning(ex, "Could not email the decision for gym application {ApplicationId}.", application.Id);
                emailWarning = "The decision was saved, but the notification email could not be sent.";
            }

            return Ok(new { id = application.Id, status = application.Status.ToString(), warning = emailWarning });
        }

        private int? CurrentUserId()
        {
            var value = User.FindFirstValue(ClaimTypes.NameIdentifier)
                        ?? User.FindFirstValue(JwtRegisteredClaimNames.Sub)
                        ?? User.FindFirstValue("sub");
            return int.TryParse(value, out var id) ? id : null;
        }

        private static GymApplicationDetailDto ToDetail(GymApplication a) => new(
            a.Id,
            a.Status.ToString(),
            a.GymName,
            a.OwnerRole,
            a.Description,
            a.Address,
            a.City,
            a.GymPhone,
            a.ContactEmail,
            a.Website,
            a.OpeningHours,
            a.Equipment,
            a.Classes,
            a.GymPhotoUrls,
            a.EquipmentPhotoUrls,
            a.LicenseUrl,
            $"{a.User?.FirstName} {a.User?.LastName}".Trim(),
            a.User?.Email ?? "",
            a.User?.Phone,
            a.User?.IsEmailVerified ?? false,
            a.ReviewNote,
            a.ReviewedAt,
            a.CreatedAt,
            a.UpdatedAt);
    }
}
