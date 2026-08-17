using System.ComponentModel.DataAnnotations;
using VitroFit.API.Entities;

namespace VitroFit.API.Dtos.Admin
{
    public class CreateUserRequest
    {
        [Required]
        [MaxLength(50)]
        public string FirstName { get; set; } = string.Empty;

        [Required]
        [MaxLength(50)]
        public string LastName { get; set; } = string.Empty;

        [Required]
        [EmailAddress]
        [MaxLength(100)]
        public string Email { get; set; } = string.Empty;

        [MaxLength(20)]
        public string? Phone { get; set; }

        [Required]
        [MinLength(8)]
        public string Password { get; set; } = string.Empty;

        [Required]
        public UserRole Role { get; set; }
    }
}
