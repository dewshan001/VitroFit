using System.ComponentModel.DataAnnotations;

namespace VitroFit.API.Dtos.Auth
{
    public sealed class ResendVerificationRequest
    {
        [Required]
        [EmailAddress]
        public string Email { get; set; } = string.Empty;
    }
}
