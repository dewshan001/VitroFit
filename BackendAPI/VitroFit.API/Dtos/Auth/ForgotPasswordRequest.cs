using System.ComponentModel.DataAnnotations;

namespace VitroFit.API.Dtos.Auth
{
    /// <summary>
    /// Request body for the forgot-password endpoint.
    /// The user supplies only their email; an OTP will be sent to that address.
    /// </summary>
    public sealed class ForgotPasswordRequest
    {
        /// <summary>The registered email address to send the OTP to.</summary>
        [Required]
        [EmailAddress]
        public string Email { get; set; } = string.Empty;
    }
}
