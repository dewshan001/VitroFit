using System.Text.Json;
using Microsoft.EntityFrameworkCore;
using VitroFit.API.Data;
using VitroFit.API.Entities;
using VitroFit.API.Services;

namespace VitroFit.API.Features.TimetableVerification
{
    public sealed record CreateProposalInput(
        int UserId,
        Guid WorkflowId,
        JsonElement? Timetable,
        string? LongTermImpact,
        string? Preferences,
        string Goal,
        int DaysPerWeek,
        int SessionMinutes,
        IReadOnlyList<string> Equipment);

    public enum ReviewOutcome { Done, NotFound, Conflict, SelfReview, NoteRequired }

    /// <param name="Warning">Set when the decision was saved but the user's email could not be sent.</param>
    public sealed record ReviewResult(ReviewOutcome Outcome, string? Warning = null);

    public interface ITimetableReviewService
    {
        /// <summary>Holds a generated timetable for verification and tells the reviewers. Nothing is applied yet.</summary>
        Task<TimetableProposal> CreateProposalAsync(CreateProposalInput input, CancellationToken ct);

        /// <summary>Approves (applies the slots) or rejects (note required) a pending timetable and tells the user.</summary>
        Task<ReviewResult> ReviewAsync(int proposalId, int reviewerId, bool approve, string? note, CancellationToken ct);

        /// <summary>The owner of a pending proposal withdraws it. False if it is not theirs or not pending.</summary>
        Task<bool> CancelAsync(int userId, int proposalId, CancellationToken ct);
    }

    public sealed class TimetableReviewService : ITimetableReviewService
    {
        private readonly AppDbContext _db;
        private readonly IEmailService _email;
        private readonly ILogger<TimetableReviewService> _logger;

        public TimetableReviewService(AppDbContext db, IEmailService email, ILogger<TimetableReviewService> logger)
        {
            _db = db;
            _email = email;
            _logger = logger;
        }

        public async Task<TimetableProposal> CreateProposalAsync(CreateProposalInput input, CancellationToken ct)
        {
            var slots = TimetableSlotMapper.ParseSlots(input.Timetable);

            await using var transaction = await _db.Database.BeginTransactionAsync(ct);

            // Only one request per user is in the queue at a time: a newer one replaces the older.
            await _db.TimetableProposals
                .Where(p => p.UserId == input.UserId && p.Status == TimetableProposalStatus.Pending)
                .ExecuteUpdateAsync(s => s.SetProperty(p => p.Status, TimetableProposalStatus.Superseded), ct);

            var proposal = new TimetableProposal
            {
                UserId = input.UserId,
                WorkflowId = input.WorkflowId,
                SlotsJson = TimetableSlotMapper.Serialize(slots),
                LongTermImpact = Trim(input.LongTermImpact, 4000),
                Preferences = Trim(input.Preferences, 1000),
                Goal = Trim(input.Goal, 100) ?? "",
                DaysPerWeek = input.DaysPerWeek,
                SessionMinutes = input.SessionMinutes,
                Equipment = input.Equipment.ToList()
            };
            _db.TimetableProposals.Add(proposal);
            await _db.SaveChangesAsync(ct);

            // Everyone who can verify (approved gym owners and admins, never the requester) gets a bell notification.
            var reviewerIds = await _db.Users
                .Where(u => u.Id != input.UserId && u.IsEmailVerified
                    && (u.Role == UserRole.Admin
                        || (u.Role == UserRole.Gym_Owner
                            && (!_db.GymApplications.Any(a => a.UserId == u.Id)
                                || _db.GymApplications.Any(a => a.UserId == u.Id && a.Status == GymApplicationStatus.Approved)))))
                .Select(u => u.Id)
                .ToListAsync(ct);

            foreach (var reviewerId in reviewerIds)
            {
                _db.UserNotifications.Add(new UserNotification
                {
                    UserId = reviewerId,
                    Type = "timetable.review-requested",
                    Title = "New timetable to verify",
                    Message = $"A member generated a {slots.Count}-session weekly timetable for the goal \"{proposal.Goal}\". Review and verify it.",
                    LinkUrl = "/timetable-reviews"
                });
            }
            await _db.SaveChangesAsync(ct);

            await transaction.CommitAsync(ct);
            return proposal;
        }

        public async Task<ReviewResult> ReviewAsync(int proposalId, int reviewerId, bool approve, string? note, CancellationToken ct)
        {
            note = string.IsNullOrWhiteSpace(note) ? null : note.Trim();
            if (!approve && note == null) return new ReviewResult(ReviewOutcome.NoteRequired);

            var proposal = await _db.TimetableProposals.AsNoTracking()
                .Include(p => p.User)
                .SingleOrDefaultAsync(p => p.Id == proposalId, ct);
            var reviewer = await _db.Users.AsNoTracking().SingleOrDefaultAsync(u => u.Id == reviewerId, ct);
            if (proposal?.User == null || reviewer == null) return new ReviewResult(ReviewOutcome.NotFound);

            // Owners cannot verify their own timetable; an admin can (there is always someone accountable).
            if (proposal.UserId == reviewerId && reviewer.Role != UserRole.Admin)
                return new ReviewResult(ReviewOutcome.SelfReview);

            var reviewerName = await ReviewerDisplayNameAsync(reviewer, ct);
            var newStatus = approve ? TimetableProposalStatus.Approved : TimetableProposalStatus.Rejected;
            var now = DateTime.UtcNow;

            await using (var transaction = await _db.Database.BeginTransactionAsync(ct))
            {
                // Claim the decision atomically: when two reviewers act at once, exactly one wins.
                var claimed = await _db.TimetableProposals
                    .Where(p => p.Id == proposalId && p.Status == TimetableProposalStatus.Pending)
                    .ExecuteUpdateAsync(s => s
                        .SetProperty(p => p.Status, newStatus)
                        .SetProperty(p => p.ReviewNote, note)
                        .SetProperty(p => p.ReviewedByUserId, reviewerId)
                        .SetProperty(p => p.ReviewerName, reviewerName)
                        .SetProperty(p => p.ReviewedAt, now), ct);
                if (claimed == 0) return new ReviewResult(ReviewOutcome.Conflict);

                if (approve)
                {
                    await ApplyAsync(proposal.UserId, TimetableSlotMapper.Deserialize(proposal.SlotsJson), ct);
                }

                _db.UserNotifications.Add(new UserNotification
                {
                    UserId = proposal.UserId,
                    Type = approve ? "timetable.verified" : "timetable.rejected",
                    Title = approve ? "Your timetable was verified" : "Your timetable needs changes",
                    Message = approve
                        ? $"{reviewerName} verified your smart timetable. It is now your active weekly schedule."
                        : $"{reviewerName} could not verify your smart timetable. Your previous timetable is unchanged.{(note == null ? "" : " Note: " + Trim(note, 300))}",
                    LinkUrl = "/timetable"
                });
                await _db.SaveChangesAsync(ct);
                await transaction.CommitAsync(ct);
            }

            // A failed email must not undo the decision; report it so the reviewer knows.
            string? warning = null;
            try
            {
                var (subject, html) = approve
                    ? TimetableEmails.Verified(proposal.User.FirstName, reviewerName, note)
                    : TimetableEmails.Rejected(proposal.User.FirstName, reviewerName, note);
                await _email.SendAsync(proposal.User.Email, proposal.User.FirstName, subject, html);
            }
            catch (Exception ex)
            {
                _logger.LogWarning(ex, "Could not email the timetable decision for proposal {ProposalId}.", proposalId);
                warning = "The decision was saved and the member was notified in the app, but the email could not be sent.";
            }

            return new ReviewResult(ReviewOutcome.Done, warning);
        }

        public async Task<bool> CancelAsync(int userId, int proposalId, CancellationToken ct)
        {
            var changed = await _db.TimetableProposals
                .Where(p => p.Id == proposalId && p.UserId == userId && p.Status == TimetableProposalStatus.Pending)
                .ExecuteUpdateAsync(s => s.SetProperty(p => p.Status, TimetableProposalStatus.Cancelled), ct);
            return changed > 0;
        }

        /// <summary>Replaces the user's timetable with the verified slots. Runs inside the caller's transaction.</summary>
        private async Task ApplyAsync(int userId, IReadOnlyList<ProposedSlot> slots, CancellationToken ct)
        {
            var existing = await _db.TimetableSlots.Where(t => t.UserId == userId).ToListAsync(ct);
            _db.TimetableSlots.RemoveRange(existing);

            var workouts = new Dictionary<string, Workout>(StringComparer.Ordinal);
            foreach (var slot in slots)
            {
                if (!workouts.TryGetValue(slot.Focus, out var workout))
                {
                    workout = await _db.Workouts.FirstOrDefaultAsync(w => w.Name == slot.Focus, ct);
                    if (workout == null)
                    {
                        workout = new Workout { Name = slot.Focus, Category = "Adaptive", Description = slot.Description };
                        _db.Workouts.Add(workout);
                    }
                    else if (!string.IsNullOrEmpty(slot.Description))
                    {
                        workout.Description = slot.Description;
                    }
                    await _db.SaveChangesAsync(ct); // the slot needs the workout's id
                    workouts[slot.Focus] = workout;
                }

                TimetableSlotMapper.TryParseTime(slot.StartTime, out var start);
                TimetableSlotMapper.TryParseTime(slot.EndTime, out var end);
                _db.TimetableSlots.Add(new TimetableSlot
                {
                    UserId = userId,
                    WorkoutId = workout.Id,
                    Day = TimetableSlotMapper.ToDayOfWeek(slot.Day),
                    StartTime = start,
                    EndTime = end,
                    Title = slot.Focus
                });
            }
        }

        /// <summary>The owner's gym name for an owner with an application, otherwise "VitroFit Admin".</summary>
        private async Task<string> ReviewerDisplayNameAsync(User reviewer, CancellationToken ct)
        {
            if (reviewer.Role == UserRole.Gym_Owner)
            {
                var gym = await _db.GymApplications.AsNoTracking()
                    .Where(a => a.UserId == reviewer.Id)
                    .Select(a => a.GymName)
                    .FirstOrDefaultAsync(ct);
                if (!string.IsNullOrWhiteSpace(gym)) return gym;
                return $"{reviewer.FirstName} (gym owner)";
            }
            return "VitroFit Admin";
        }

        private static string? Trim(string? value, int max)
        {
            if (string.IsNullOrWhiteSpace(value)) return null;
            var trimmed = value.Trim();
            return trimmed.Length > max ? trimmed[..max] : trimmed;
        }
    }
}
