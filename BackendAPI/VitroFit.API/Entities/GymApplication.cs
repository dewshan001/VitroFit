using System.ComponentModel.DataAnnotations;

namespace VitroFit.API.Entities
{
    public enum GymApplicationStatus
    {
        Pending = 0,
        Approved = 1,
        Rejected = 2
    }

    /// <summary>
    /// A gym owner's application to join the network. Created together with the owner's account;
    /// an admin must approve it before the owner can sign in.
    /// </summary>
    public class GymApplication
    {
        public int Id { get; set; }

        public int UserId { get; set; }
        public User? User { get; set; }

        [Required, MaxLength(150)]
        public string GymName { get; set; } = string.Empty;

        /// <summary>"Owner" or "Manager".</summary>
        [Required, MaxLength(20)]
        public string OwnerRole { get; set; } = "Owner";

        [Required, MaxLength(1500)]
        public string Description { get; set; } = string.Empty;

        [Required, MaxLength(300)]
        public string Address { get; set; } = string.Empty;

        [Required, MaxLength(100)]
        public string City { get; set; } = string.Empty;

        [Required, MaxLength(30)]
        public string GymPhone { get; set; } = string.Empty;

        [Required, MaxLength(200)]
        public string ContactEmail { get; set; } = string.Empty;

        [Required, MaxLength(300)]
        public string Website { get; set; } = string.Empty;

        [MaxLength(300)]
        public string? OpeningHours { get; set; }

        public List<string> Equipment { get; set; } = new();
        public List<string> Classes { get; set; } = new();
        public List<string> GymPhotoUrls { get; set; } = new();
        public List<string> EquipmentPhotoUrls { get; set; } = new();

        [MaxLength(500)]
        public string? LicenseUrl { get; set; }

        public GymApplicationStatus Status { get; set; } = GymApplicationStatus.Pending;

        /// <summary>The admin's note; required when rejecting.</summary>
        [MaxLength(500)]
        public string? ReviewNote { get; set; }

        public int? ReviewedByUserId { get; set; }
        public DateTime? ReviewedAt { get; set; }

        public DateTime CreatedAt { get; set; } = DateTime.UtcNow;
        public DateTime UpdatedAt { get; set; } = DateTime.UtcNow;
    }
}
