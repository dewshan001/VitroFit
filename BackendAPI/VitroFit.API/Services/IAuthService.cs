using VitroFit.API.Dtos.Auth;

namespace VitroFit.API.Services
{
    public interface IAuthService
    {
        Task<AuthResponse> RegisterAsync(RegisterRequest request);
        Task<AuthResponse> LoginAsync(LoginRequest request);
        Task<AuthResponse> RefreshTokenAsync(RefreshTokenRequest request);
        Task ChangePasswordAsync(int userId, ChangePasswordRequest request);
        Task DeleteAccountAsync(int userId);
    }
}
