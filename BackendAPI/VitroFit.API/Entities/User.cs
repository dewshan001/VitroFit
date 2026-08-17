using System.ComponentModel.DataAnnotations;

namespace VitroFit.API.Entities
{
    public class User
    {
        public int Id { get; set; }

        [Required]
        [MaxLength(100)]
        public string FirstName { get; set; } = string.Empty;

        [Required]
        [MaxLength(100)]
        public string LastName { get; set; } = string.Empty;

        [Required]
        [MaxLength(200)]
        public string Email { get; set; } = string.Empty;

        [MaxLength(30)]
        public string? Phone { get; set; }

        [MaxLength(500)]
        public string? ProfileImageUrl { get; set; }

        [Required]
        public string PasswordHash { get; set; } = string.Empty;

        public UserRole Role { get; set; } = UserRole.User;

        /// <summary>
        /// True once the user has verified their email address via OTP.
        /// Accounts with false cannot log in.
        /// </summary>
        public bool IsEmailVerified { get; set; } = false;

        public DateTime CreatedAt { get; set; } = DateTime.UtcNow;

        public ICollection<RefreshToken> RefreshTokens { get; set; } = new List<RefreshToken>();
    }
}
