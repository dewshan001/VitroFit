using System.IdentityModel.Tokens.Jwt;
using System.Security.Claims;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using VitroFit.API.Dtos.Auth;
using VitroFit.API.Services;

namespace VitroFit.API.Controllers
{
    [ApiController]
    [Route("api/[controller]")]
    public sealed class AuthController : ControllerBase
    {
        private readonly IAuthService _authService;

        public AuthController(IAuthService authService)
        {
            _authService = authService;
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
        public IActionResult GetProfile()
        {
            var userId = User.FindFirstValue(JwtRegisteredClaimNames.Sub) ?? string.Empty;
            var email = User.FindFirstValue(JwtRegisteredClaimNames.Email) ?? string.Empty;
            var firstName = User.FindFirstValue("firstName") ?? string.Empty;
            var lastName = User.FindFirstValue("lastName") ?? string.Empty;

            return Ok(new
            {
                Id = userId,
                Email = email,
                FirstName = firstName,
                LastName = lastName
            });
        }

        [HttpPost("change-password")]
        [Authorize]
        public async Task<IActionResult> ChangePassword([FromBody] ChangePasswordRequest request)
        {
            var userIdStr = User.FindFirstValue(JwtRegisteredClaimNames.Sub);
            if (!int.TryParse(userIdStr, out var userId))
                return Unauthorized(new { error = "Invalid token." });

            try
            {
                await _authService.ChangePasswordAsync(userId, request);
                return Ok(new { message = "Password changed successfully." });
            }
            catch (InvalidOperationException ex)
            {
                return BadRequest(new { error = ex.Message });
            }
        }
    }
}
