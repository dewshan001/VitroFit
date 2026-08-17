using System.ComponentModel.DataAnnotations;

namespace VitroFit.API.Dtos.Auth
{
    public sealed class VerifyEmailRequest
    {
        [Required]
        [EmailAddress]
        public string Email { get; set; } = string.Empty;

        [Required]
        [StringLength(6, MinimumLength = 6)]
        public string Otp { get; set; } = string.Empty;
    }
}
