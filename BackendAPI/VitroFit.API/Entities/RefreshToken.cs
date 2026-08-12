using System.ComponentModel.DataAnnotations;

namespace VitroFit.API.Entities
{
    public class RefreshToken
    {
        public int Id { get; set; }

        [Required]
        public string Token { get; set; } = string.Empty;

        public DateTime ExpiresAt { get; set; }

        public DateTime CreatedAt { get; set; } = DateTime.UtcNow;

        public DateTime? RevokedAt { get; set; }

        public int UserId { get; set; }

        public User? User { get; set; }

        public bool IsActive => RevokedAt == null && DateTime.UtcNow <= ExpiresAt;
    }
}
