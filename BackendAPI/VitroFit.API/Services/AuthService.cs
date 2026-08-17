using Microsoft.AspNetCore.Identity;
using Microsoft.EntityFrameworkCore;
using VitroFit.API.Data;
using VitroFit.API.Dtos.Auth;
using VitroFit.API.Entities;
using VitroFit.API.Settings;

namespace VitroFit.API.Services
{
    public sealed class AuthService : IAuthService
    {
        private readonly AppDbContext _dbContext;
        private readonly IPasswordHasher<User> _passwordHasher;
        private readonly ITokenService _tokenService;
        private readonly JwtSettings _jwtSettings;
        private readonly IImageService _imageService;
        private readonly IEmailService _emailService;

        public AuthService(
            AppDbContext dbContext,
            IPasswordHasher<User> passwordHasher,
            ITokenService tokenService,
            Microsoft.Extensions.Options.IOptions<JwtSettings> jwtOptions,
            IImageService imageService,
            IEmailService emailService)
        {
            _dbContext = dbContext;
            _passwordHasher = passwordHasher;
            _tokenService = tokenService;
            _jwtSettings = jwtOptions.Value;
            _imageService = imageService;
            _emailService = emailService;
        }

        // -----------------------------------------------------------------------
        // REGISTRATION — creates an unverified account and sends an OTP
        // -----------------------------------------------------------------------
        public async Task<(string message, string email)> RegisterAsync(RegisterRequest request)
        {
            if (await _dbContext.Users.AnyAsync(u => u.Email == request.Email))
            {
                throw new InvalidOperationException("A user with this email already exists.");
            }

            var user = new User
            {
                FirstName       = request.FirstName,
                LastName        = request.LastName,
                Email           = request.Email,
                Phone           = request.Phone,
                Role            = UserRole.User,
                IsEmailVerified = false   // must verify before logging in
            };

            user.PasswordHash = _passwordHasher.HashPassword(user, request.Password);
            _dbContext.Users.Add(user);
            await _dbContext.SaveChangesAsync();

            // Send the email-verification OTP
            await SendOtpAsync(user, OtpPurpose.EmailVerification);

            return (
                message: "Account created. Please check your email for a 6-digit code to verify your address.",
                email: user.Email
            );
        }

        // -----------------------------------------------------------------------
        // LOGIN — blocked until email is verified
        // -----------------------------------------------------------------------
        public async Task<AuthResponse> LoginAsync(LoginRequest request)
        {
            var user = await _dbContext.Users.SingleOrDefaultAsync(u => u.Email == request.Email);
            if (user == null)
            {
                throw new InvalidOperationException("Invalid email or password.");
            }

            var result = _passwordHasher.VerifyHashedPassword(user, user.PasswordHash, request.Password);
            if (result == PasswordVerificationResult.Failed)
            {
                throw new InvalidOperationException("Invalid email or password.");
            }

            // Block login for unverified accounts
            if (!user.IsEmailVerified)
            {
                throw new InvalidOperationException(
                    "Please verify your email address before logging in. " +
                    "Check your inbox for the OTP, or request a new one.");
            }

            return await CreateAuthResponseAsync(user);
        }

        // -----------------------------------------------------------------------
        // REFRESH TOKEN
        // -----------------------------------------------------------------------
        public async Task<AuthResponse> RefreshTokenAsync(RefreshTokenRequest request)
        {
            var refreshToken = await _dbContext.RefreshTokens
                .Include(rt => rt.User)
                .SingleOrDefaultAsync(rt => rt.Token == request.Token);

            if (refreshToken == null || !refreshToken.IsActive || refreshToken.User == null)
            {
                throw new InvalidOperationException("Refresh token is invalid or expired.");
            }

            refreshToken.RevokedAt = DateTime.UtcNow;
            await _dbContext.SaveChangesAsync();

            return await CreateAuthResponseAsync(refreshToken.User);
        }

        // -----------------------------------------------------------------------
        // EMAIL VERIFICATION — validate OTP, mark verified, return tokens
        // -----------------------------------------------------------------------
        public async Task<AuthResponse> VerifyEmailAsync(VerifyEmailRequest request)
        {
            // Look up the most recent active email-verification OTP for this address
            var otpRecord = await _dbContext.PasswordResetOtps
                .Where(o => o.Email   == request.Email
                         && o.Code    == request.Otp
                         && o.Purpose == OtpPurpose.EmailVerification)
                .OrderByDescending(o => o.CreatedAt)
                .FirstOrDefaultAsync();

            if (otpRecord == null || !otpRecord.IsActive)
                throw new InvalidOperationException("The OTP is invalid, expired, or has already been used.");

            var user = await _dbContext.Users
                .SingleOrDefaultAsync(u => u.Email == request.Email)
                ?? throw new InvalidOperationException("No account found for this email address.");

            // Mark verified and consume the OTP
            user.IsEmailVerified = true;
            otpRecord.IsUsed     = true;

            await _dbContext.SaveChangesAsync();

            // Issue tokens — the account is now fully active
            return await CreateAuthResponseAsync(user);
        }

        // -----------------------------------------------------------------------
        // RESEND VERIFICATION OTP
        // -----------------------------------------------------------------------
        public async Task ResendVerificationAsync(ResendVerificationRequest request)
        {
            var user = await _dbContext.Users
                .SingleOrDefaultAsync(u => u.Email == request.Email);

            // Silently return if not found or already verified (prevents enumeration)
            if (user == null || user.IsEmailVerified) return;

            // Invalidate any previous verification OTPs for this email
            var existingOtps = await _dbContext.PasswordResetOtps
                .Where(o => o.Email   == request.Email
                         && o.Purpose == OtpPurpose.EmailVerification
                         && !o.IsUsed)
                .ToListAsync();

            foreach (var old in existingOtps)
                old.IsUsed = true;

            await _dbContext.SaveChangesAsync();

            await SendOtpAsync(user, OtpPurpose.EmailVerification);
        }

        // -----------------------------------------------------------------------
        // FORGOT PASSWORD
        // -----------------------------------------------------------------------
        public async Task ForgotPasswordAsync(ForgotPasswordRequest request)
        {
            // Security: do NOT reveal whether the email exists (prevents user enumeration).
            var user = await _dbContext.Users
                .SingleOrDefaultAsync(u => u.Email == request.Email);

            if (user == null) return;

            // Invalidate any previously issued, still-active password-reset OTPs
            var existingOtps = await _dbContext.PasswordResetOtps
                .Where(o => o.Email   == request.Email
                         && o.Purpose == OtpPurpose.PasswordReset
                         && !o.IsUsed)
                .ToListAsync();

            foreach (var old in existingOtps)
                old.IsUsed = true;

            await _dbContext.SaveChangesAsync();

            await SendOtpAsync(user, OtpPurpose.PasswordReset);
        }

        // -----------------------------------------------------------------------
        // RESET PASSWORD
        // -----------------------------------------------------------------------
        public async Task ResetPasswordAsync(ResetPasswordRequest request)
        {
            var otpRecord = await _dbContext.PasswordResetOtps
                .Where(o => o.Email   == request.Email
                         && o.Code    == request.Otp
                         && o.Purpose == OtpPurpose.PasswordReset)
                .OrderByDescending(o => o.CreatedAt)
                .FirstOrDefaultAsync();

            if (otpRecord == null || !otpRecord.IsActive)
                throw new InvalidOperationException("The OTP is invalid, expired, or has already been used.");

            var user = await _dbContext.Users
                .SingleOrDefaultAsync(u => u.Email == request.Email)
                ?? throw new InvalidOperationException("No account found for this email address.");

            if (request.NewPassword.Length < 6)
                throw new InvalidOperationException("New password must be at least 6 characters.");

            user.PasswordHash = _passwordHasher.HashPassword(user, request.NewPassword);
            otpRecord.IsUsed  = true;

            // Invalidate all refresh tokens to force re-login after password change
            var activeTokens = await _dbContext.RefreshTokens
                .Where(rt => rt.UserId == user.Id && rt.RevokedAt == null)
                .ToListAsync();

            foreach (var token in activeTokens)
                token.RevokedAt = DateTime.UtcNow;

            await _dbContext.SaveChangesAsync();
        }

        // -----------------------------------------------------------------------
        // CHANGE PASSWORD
        // -----------------------------------------------------------------------
        public async Task ChangePasswordAsync(int userId, ChangePasswordRequest request)
        {
            var user = await _dbContext.Users.FindAsync(userId)
                ?? throw new InvalidOperationException("User not found.");

            var result = _passwordHasher.VerifyHashedPassword(user, user.PasswordHash, request.CurrentPassword);
            if (result == PasswordVerificationResult.Failed)
                throw new InvalidOperationException("Current password is incorrect.");

            if (request.NewPassword.Length < 6)
                throw new InvalidOperationException("New password must be at least 6 characters.");

            user.PasswordHash = _passwordHasher.HashPassword(user, request.NewPassword);
            await _dbContext.SaveChangesAsync();
        }

        // -----------------------------------------------------------------------
        // DELETE ACCOUNT
        // -----------------------------------------------------------------------
        public async Task DeleteAccountAsync(int userId)
        {
            var user = await _dbContext.Users.FindAsync(userId)
                ?? throw new InvalidOperationException("User not found.");

            if (!string.IsNullOrWhiteSpace(user.ProfileImageUrl))
            {
                try
                {
                    await _imageService.DeleteImageAsync(user.ProfileImageUrl);
                }
                catch
                {
                    // Ignore errors deleting external image to ensure user account is deleted
                }
            }

            _dbContext.Users.Remove(user);
            await _dbContext.SaveChangesAsync();
        }

        // -----------------------------------------------------------------------
        // PRIVATE HELPERS
        // -----------------------------------------------------------------------

        private async Task<AuthResponse> CreateAuthResponseAsync(User user)
        {
            var accessToken  = _tokenService.CreateAccessToken(user);
            var refreshToken = _tokenService.CreateRefreshToken(user, TimeSpan.FromDays(_jwtSettings.RefreshTokenExpirationDays));

            _dbContext.RefreshTokens.Add(refreshToken);
            await _dbContext.SaveChangesAsync();

            return new AuthResponse
            {
                AccessToken           = accessToken,
                RefreshToken          = refreshToken.Token,
                AccessTokenExpiresAt  = DateTime.UtcNow.AddMinutes(_jwtSettings.AccessTokenExpirationMinutes),
                RefreshTokenExpiresAt = refreshToken.ExpiresAt,
                User = new Dtos.Auth.UserDto
                {
                    Id              = user.Id,
                    FirstName       = user.FirstName,
                    LastName        = user.LastName,
                    Email           = user.Email,
                    Phone           = user.Phone,
                    ProfileImageUrl = user.ProfileImageUrl,
                    Role            = user.Role
                }
            };
        }

        /// <summary>
        /// Generates a 6-digit OTP, persists it with the given purpose, and emails it.
        /// </summary>
        private async Task SendOtpAsync(User user, OtpPurpose purpose)
        {
            var otpCode = Random.Shared.Next(100_000, 999_999).ToString();

            var otpRecord = new PasswordResetOtp
            {
                Email     = user.Email,
                Code      = otpCode,
                ExpiresAt = DateTime.UtcNow.AddMinutes(10),
                CreatedAt = DateTime.UtcNow,
                Purpose   = purpose
            };

            _dbContext.PasswordResetOtps.Add(otpRecord);
            await _dbContext.SaveChangesAsync();

            string subject, htmlBody;

            if (purpose == OtpPurpose.EmailVerification)
            {
                subject = "VitroFit — Verify Your Email";
                htmlBody = $"""
                    <div style="font-family: Arial, sans-serif; max-width: 480px; margin: auto; padding: 32px; border: 1px solid #e0e0e0; border-radius: 8px;">
                        <h2 style="color: #1a1a2e;">Verify Your Email Address</h2>
                        <p>Hi <strong>{user.FirstName}</strong>,</p>
                        <p>Welcome to VitroFit! Use the code below to verify your email and activate your account:</p>
                        <div style="text-align: center; margin: 32px 0;">
                            <span style="font-size: 40px; font-weight: bold; letter-spacing: 12px; color: #4f46e5;">{otpCode}</span>
                        </div>
                        <p style="color: #555;">This code expires in <strong>10 minutes</strong>.</p>
                        <p style="color: #555;">If you did not create a VitroFit account, you can safely ignore this email.</p>
                        <hr style="border: none; border-top: 1px solid #e0e0e0; margin: 24px 0;"/>
                        <p style="font-size: 12px; color: #999;">VitroFit &mdash; Your Fitness Journey Starts Here</p>
                    </div>
                    """;
            }
            else
            {
                subject = "VitroFit — Password Reset OTP";
                htmlBody = $"""
                    <div style="font-family: Arial, sans-serif; max-width: 480px; margin: auto; padding: 32px; border: 1px solid #e0e0e0; border-radius: 8px;">
                        <h2 style="color: #1a1a2e;">Password Reset Request</h2>
                        <p>Hi <strong>{user.FirstName}</strong>,</p>
                        <p>We received a request to reset your VitroFit password. Use the OTP below to continue:</p>
                        <div style="text-align: center; margin: 32px 0;">
                            <span style="font-size: 40px; font-weight: bold; letter-spacing: 12px; color: #4f46e5;">{otpCode}</span>
                        </div>
                        <p style="color: #555;">This code expires in <strong>10 minutes</strong>.</p>
                        <p style="color: #555;">If you did not request a password reset, you can safely ignore this email.</p>
                        <hr style="border: none; border-top: 1px solid #e0e0e0; margin: 24px 0;"/>
                        <p style="font-size: 12px; color: #999;">VitroFit &mdash; Your Fitness Journey Starts Here</p>
                    </div>
                    """;
            }

            await _emailService.SendAsync(user.Email, user.FirstName, subject, htmlBody);
        }
    }
}
