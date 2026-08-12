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
                var response = await _authService.RegisterAsync(request);
                return Ok(response);
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
                ProfileImageUrl = user.ProfileImageUrl
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
    }
}
