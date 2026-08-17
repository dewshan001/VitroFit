using System.ComponentModel.DataAnnotations;

namespace VitroFit.API.Entities
{
    /// <summary>
    /// Represents a one-time password (OTP) record shared by two flows:
    ///   - Password reset (forgot-password → reset-password)
    ///   - Email verification (register → verify-email)
    /// The <see cref="Purpose"/> column discriminates between them.
    /// Each row stores a single 6-digit code tied to an email address.
    /// An OTP expires after a short window (e.g. 10 minutes) and can only be used once.
    /// </summary>
    public class PasswordResetOtp
    {
        /// <summary>Auto-incremented primary key.</summary>
        public int Id { get; set; }

        /// <summary>
        /// The email address this OTP was issued for.
        /// Used to look up the correct OTP record during verification/reset.
        /// </summary>
        [Required]
        [MaxLength(200)]
        public string Email { get; set; } = string.Empty;

        /// <summary>
        /// The 6-digit numeric OTP code sent to the user's inbox.
        /// Stored as a string to preserve any leading zeros.
        /// </summary>
        [Required]
        [MaxLength(6)]
        public string Code { get; set; } = string.Empty;

        /// <summary>
        /// UTC timestamp after which this OTP is considered expired and must be rejected.
        /// Typically set to CreatedAt + 10 minutes.
        /// </summary>
        public DateTime ExpiresAt { get; set; }

        /// <summary>
        /// Marks this OTP as already consumed.
        /// Once true, any further attempts with this code must be rejected
        /// to prevent replay attacks.
        /// </summary>
        public bool IsUsed { get; set; } = false;

        /// <summary>UTC timestamp when this OTP was created.</summary>
        public DateTime CreatedAt { get; set; } = DateTime.UtcNow;

        /// <summary>
        /// Discriminates between the password-reset flow and the email-verification flow.
        /// Defaults to <see cref="OtpPurpose.PasswordReset"/> for backwards compatibility
        /// with rows already in the database.
        /// </summary>
        public OtpPurpose Purpose { get; set; } = OtpPurpose.PasswordReset;

        /// <summary>
        /// Convenience property — returns true if the OTP is still valid:
        /// not yet used AND not yet expired.
        /// </summary>
        public bool IsActive => !IsUsed && DateTime.UtcNow < ExpiresAt;
    }
}

