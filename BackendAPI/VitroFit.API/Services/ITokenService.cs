using VitroFit.API.Entities;

namespace VitroFit.API.Services
{
    public interface ITokenService
    {
        string CreateAccessToken(User user);
        RefreshToken CreateRefreshToken(User user, TimeSpan lifetime);
    }
}
