using System.ComponentModel.DataAnnotations;

namespace VitroFit.API.Dtos.Auth
{
    /// <summary>
    /// Request body for the reset-password endpoint.
    /// The user must provide their email, the OTP they received, and their desired new password.
    /// All three fields are validated together — a missing or wrong OTP will be rejected.
    /// </summary>
    public sealed class ResetPasswordRequest
    {
        /// <summary>The email address that the OTP was sent to.</summary>
        [Required]
        [EmailAddress]
        public string Email { get; set; } = string.Empty;

        /// <summary>The 6-digit OTP code received in the email.</summary>
        [Required]
        [StringLength(6, MinimumLength = 6, ErrorMessage = "OTP must be exactly 6 digits.")]
        public string Otp { get; set; } = string.Empty;

        /// <summary>
        /// The new password to set for the account.
        /// Must be at least 6 characters — same rules as registration.
        /// </summary>
        [Required]
        [MinLength(6, ErrorMessage = "New password must be at least 6 characters.")]
        public string NewPassword { get; set; } = string.Empty;
    }
}
