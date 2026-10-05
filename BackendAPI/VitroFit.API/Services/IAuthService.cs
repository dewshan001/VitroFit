using VitroFit.API.Dtos.Auth;

namespace VitroFit.API.Services
{
    public interface IAuthService
    {
        /// <summary>
        /// Creates an unverified account and sends a 6-digit OTP to the user's email.
        /// Returns a simple message — tokens are NOT issued until the email is verified.
        /// </summary>
        Task<(string message, string email)> RegisterAsync(RegisterRequest request);

        /// <summary>
        /// Creates a gym owner account together with a pending gym application (details, photos, licence).
        /// The owner cannot sign in until an admin approves the application. A rejected owner can call this
        /// again with the same email and password to re-apply.
        /// </summary>
        Task<RegisterGymOwnerResult> RegisterGymOwnerAsync(RegisterGymOwnerRequest request);

        Task<AuthResponse> LoginAsync(LoginRequest request);
        Task<AuthResponse> RefreshTokenAsync(RefreshTokenRequest request);
        Task ChangePasswordAsync(int userId, ChangePasswordRequest request);
        Task DeleteAccountAsync(int userId);

        /// <summary>
        /// Generates and emails a 6-digit OTP to the given address so the user can reset their password.
        /// Silently succeeds even if the email is not registered (prevents user enumeration).
        /// </summary>
        Task ForgotPasswordAsync(ForgotPasswordRequest request);

        /// <summary>
        /// Validates the OTP and, if valid, updates the user's password hash.
        /// Throws <see cref="InvalidOperationException"/> if the OTP is wrong, expired, or already used.
        /// </summary>
        Task ResetPasswordAsync(ResetPasswordRequest request);

        /// <summary>
        /// Validates the email-verification OTP and marks the account as verified. Returns a full
        /// AuthResponse (access + refresh tokens), except for gym owners whose application is not yet approved.
        /// </summary>
        Task<VerifyEmailResult> VerifyEmailAsync(VerifyEmailRequest request);

        /// <summary>
        /// Resends a fresh email-verification OTP to an unverified account.
        /// Silently succeeds if the email is not found or is already verified.
        /// </summary>
        Task ResendVerificationAsync(ResendVerificationRequest request);
    }
}
