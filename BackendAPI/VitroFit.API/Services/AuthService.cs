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

        public AuthService(
            AppDbContext dbContext,
            IPasswordHasher<User> passwordHasher,
            ITokenService tokenService,
            Microsoft.Extensions.Options.IOptions<JwtSettings> jwtOptions)
        {
            _dbContext = dbContext;
            _passwordHasher = passwordHasher;
            _tokenService = tokenService;
            _jwtSettings = jwtOptions.Value;
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
                    Phone = user.Phone
                }
            };
        }
    }
}
