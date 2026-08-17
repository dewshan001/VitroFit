using System.IdentityModel.Tokens.Jwt;
using System.Security.Claims;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Mvc;
using VitroFit.API.Data;
using VitroFit.API.Dtos.Auth;
using VitroFit.API.Services;

namespace VitroFit.API.Controllers
{
    [ApiController]
    [Route("api/[controller]")]
    public sealed class AuthController : ControllerBase
    {
        private readonly IAuthService _authService;
        private readonly AppDbContext _dbContext;
        private readonly IImageService _imageService;

        public AuthController(IAuthService authService, AppDbContext dbContext, IImageService imageService)
        {
            _authService = authService;
            _dbContext = dbContext;
            _imageService = imageService;
        }

        [HttpPost("register")]
        public async Task<IActionResult> Register([FromBody] RegisterRequest request)
        {
            try
            {
                var (message, email) = await _authService.RegisterAsync(request);
                return Ok(new { message, email });
            }
            catch (InvalidOperationException ex)
            {
                return BadRequest(new { error = ex.Message });
            }
        }

        [HttpPost("login")]
        public async Task<IActionResult> Login([FromBody] LoginRequest request)
        {
            try
            {
                var response = await _authService.LoginAsync(request);
                return Ok(response);
            }
            catch (InvalidOperationException ex)
            {
                return BadRequest(new { error = ex.Message });
            }
        }

        [HttpPost("refresh")]
        public async Task<IActionResult> Refresh([FromBody] RefreshTokenRequest request)
        {
            try
            {
                var response = await _authService.RefreshTokenAsync(request);
                return Ok(response);
            }
            catch (InvalidOperationException ex)
            {
                return BadRequest(new { error = ex.Message });
            }
        }

        [HttpGet("me")]
        [Authorize]
        public async Task<IActionResult> GetProfile()
        {
            var userId = GetUserId();
            if (!userId.HasValue)
                return Unauthorized(new { error = "Invalid token." });

            var user = await _dbContext.Users.FindAsync(userId.Value);
            if (user == null)
                return Unauthorized(new { error = "User not found." });

            return Ok(new
            {
                Id = user.Id,
                Email = user.Email,
                FirstName = user.FirstName,
                LastName = user.LastName,
                Phone = user.Phone,
                ProfileImageUrl = user.ProfileImageUrl,
                Role = user.Role.ToString()
            });
        }

        [HttpPost("me/photo")]
        [Authorize]
        public async Task<IActionResult> UploadProfilePhoto(IFormFile file)
        {
            if (file == null || file.Length == 0)
                return BadRequest(new { error = "Please select an image file." });

            var userId = GetUserId();
            if (!userId.HasValue)
                return Unauthorized(new { error = "Invalid token." });

            var user = await _dbContext.Users.FindAsync(userId.Value);
            if (user == null)
                return Unauthorized(new { error = "User not found." });

            var oldImageUrl = user.ProfileImageUrl;

            var imageUrl = await _imageService.UploadProfileImageAsync(file.OpenReadStream(), file.FileName, file.ContentType);
            user.ProfileImageUrl = imageUrl;
            await _dbContext.SaveChangesAsync();

            if (!string.IsNullOrWhiteSpace(oldImageUrl))
            {
                try
                {
                    await _imageService.DeleteImageAsync(oldImageUrl);
                }
                catch
                {
                    // Non-critical cleanup error
                }
            }

            return Ok(new { profileImageUrl = imageUrl });
        }

        [HttpPost("change-password")]
        [Authorize]
        public async Task<IActionResult> ChangePassword([FromBody] ChangePasswordRequest request)
        {
            var userId = GetUserId();
            if (!userId.HasValue)
                return Unauthorized(new { error = "Invalid token." });

            try
            {
                await _authService.ChangePasswordAsync(userId.Value, request);
                return Ok(new { message = "Password changed successfully." });
            }
            catch (InvalidOperationException ex)
            {
                return BadRequest(new { error = ex.Message });
            }
        }

        [HttpDelete("me")]
        [Authorize]
        public async Task<IActionResult> DeleteAccount()
        {
            var userId = GetUserId();
            if (!userId.HasValue)
                return Unauthorized(new { error = "Invalid token." });

            try
            {
                await _authService.DeleteAccountAsync(userId.Value);
                return Ok(new { message = "Account deleted successfully." });
            }
            catch (InvalidOperationException ex)
            {
                return BadRequest(new { error = ex.Message });
            }
        }

        private int? GetUserId()
        {
            var userIdStr = User.FindFirstValue(ClaimTypes.NameIdentifier)
                         ?? User.FindFirstValue(JwtRegisteredClaimNames.Sub)
                         ?? User.FindFirst("sub")?.Value;

            return int.TryParse(userIdStr, out var userId) ? userId : null;
        }

        /// <summary>
        /// Step 1 of the forgot-password flow.
        /// Accepts the user's email and sends a 6-digit OTP to that address.
        /// Always returns 200 OK regardless of whether the email exists (prevents user enumeration).
        /// </summary>
        [HttpPost("forgot-password")]
        public async Task<IActionResult> ForgotPassword([FromBody] ForgotPasswordRequest request)
        {
            try
            {
                await _authService.ForgotPasswordAsync(request);

                // Return a generic message so the caller doesn't know if the email is registered.
                return Ok(new { message = "If that email is registered, an OTP has been sent." });
            }
            catch (InvalidOperationException ex)
            {
                // This can happen if the email service fails (SMTP error).
                return StatusCode(500, new { error = ex.Message });
            }
        }

        /// <summary>
        /// Step 2 of the forgot-password flow.
        /// Validates the OTP received by email and resets the account password.
        /// All active sessions (refresh tokens) are invalidated after a successful reset.
        /// </summary>
        [HttpPost("reset-password")]
        public async Task<IActionResult> ResetPassword([FromBody] ResetPasswordRequest request)
        {
            try
            {
                await _authService.ResetPasswordAsync(request);
                return Ok(new { message = "Password reset successfully. Please log in with your new password." });
            }
            catch (InvalidOperationException ex)
            {
                return BadRequest(new { error = ex.Message });
            }
        }

        /// <summary>
        /// Step 2 of the registration flow.
        /// Validates the email-verification OTP and, if valid, activates the account
        /// and returns a full AuthResponse (access + refresh tokens).
        /// </summary>
        [HttpPost("verify-email")]
        public async Task<IActionResult> VerifyEmail([FromBody] VerifyEmailRequest request)
        {
            try
            {
                var response = await _authService.VerifyEmailAsync(request);
                return Ok(response);
            }
            catch (InvalidOperationException ex)
            {
                return BadRequest(new { error = ex.Message });
            }
        }

        /// <summary>
        /// Resends the email-verification OTP for an unverified account.
        /// Always returns 200 OK regardless of whether the email exists or is already verified.
        /// </summary>
        [HttpPost("resend-verification")]
        public async Task<IActionResult> ResendVerification([FromBody] ResendVerificationRequest request)
        {
            try
            {
                await _authService.ResendVerificationAsync(request);
                return Ok(new { message = "If that email has a pending verification, a new OTP has been sent." });
            }
            catch (Exception ex)
            {
                return StatusCode(500, new { error = ex.Message });
            }
        }
    }
}
