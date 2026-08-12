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

        public AuthService(
            AppDbContext dbContext,
            IPasswordHasher<User> passwordHasher,
            ITokenService tokenService,
            Microsoft.Extensions.Options.IOptions<JwtSettings> jwtOptions,
            IImageService imageService)
        {
            _dbContext = dbContext;
            _passwordHasher = passwordHasher;
            _tokenService = tokenService;
            _jwtSettings = jwtOptions.Value;
            _imageService = imageService;
        }

        public async Task<AuthResponse> RegisterAsync(RegisterRequest request)
        {
            if (await _dbContext.Users.AnyAsync(u => u.Email == request.Email))
            {
                throw new InvalidOperationException("A user with this email already exists.");
            }

            var user = new User
            {
                FirstName = request.FirstName,
                LastName = request.LastName,
                Email = request.Email,
                Phone = request.Phone
            };

            user.PasswordHash = _passwordHasher.HashPassword(user, request.Password);
            _dbContext.Users.Add(user);
            await _dbContext.SaveChangesAsync();

            return await CreateAuthResponseAsync(user);
        }

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

            return await CreateAuthResponseAsync(user);
        }

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

        private async Task<AuthResponse> CreateAuthResponseAsync(User user)
        {
            var accessToken = _tokenService.CreateAccessToken(user);
            var refreshToken = _tokenService.CreateRefreshToken(user, TimeSpan.FromDays(_jwtSettings.RefreshTokenExpirationDays));

            _dbContext.RefreshTokens.Add(refreshToken);
            await _dbContext.SaveChangesAsync();

            return new AuthResponse
            {
                AccessToken = accessToken,
                RefreshToken = refreshToken.Token,
                AccessTokenExpiresAt = DateTime.UtcNow.AddMinutes(_jwtSettings.AccessTokenExpirationMinutes),
                RefreshTokenExpiresAt = refreshToken.ExpiresAt,
                User = new Dtos.Auth.UserDto
                {
                    Id = user.Id,
                    FirstName = user.FirstName,
                    LastName = user.LastName,
                    Email = user.Email,
                    Phone = user.Phone,
                    ProfileImageUrl = user.ProfileImageUrl
                }
            };
        }

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
    }
}
