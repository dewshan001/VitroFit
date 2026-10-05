using VitroFit.API.Entities;

namespace VitroFit.API.Features.GymOwners
{
    /// <summary>Raised when a gym owner whose application is not approved tries to sign in.</summary>
    public sealed class GymOwnerNotApprovedException : InvalidOperationException
    {
        public GymApplicationStatus Status { get; }
        public string? Note { get; }

        public string Code => Status == GymApplicationStatus.Rejected ? "GYM_REJECTED" : "GYM_PENDING";

        public GymOwnerNotApprovedException(GymApplicationStatus status, string? note)
            : base(status == GymApplicationStatus.Rejected
                ? "Your gym application was not approved."
                : "Your gym application is awaiting admin approval. We will email you once it has been reviewed.")
        {
            Status = status;
            Note = note;
        }
    }
}
